using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;

namespace MGFR.Wardrobe
{
    [Serializable] public sealed class WardrobeAnchor
    { public int vertex; public float[] position, normal, boneWeights; public int[] boneIndices; }
    [Serializable] public sealed class WardrobePart
    {
        public string id, label, indexFile, indexSha256, clothOwner;
        public int materialSlot, indexCount, triangleCount;
        public WardrobeAnchor[] anchors;
        public float gripRadiusMetres, pullDistanceMetres, snapRadiusMetres, snapAngleDegrees;
        public float[] pullDirectionLocal;
        public bool requiresClothOwnershipHandoff, requiresFootPoseTransition;
    }
    [Serializable] public sealed class WardrobeProfile
    {
        public int schemaVersion, vertexCount, materialCount, indexCount, boneCount, blendShapeCount;
        public string id, triangleBufferSha256, positionBufferSha256;
        public WardrobePart[] parts;
    }

    // Optional host bridge for simulated cloth. A host must suspend that part's
    // simulation/grabs and provide its CURRENT geometry before detaching it.
    public interface IWardrobeDeformationOwner
    {
        bool TrySuspendPart(string id, out Vector3[] currentVerticesInModelSpace);
        void ResumePart(string id);
    }
    // Shoes require a separate host-owned rest/bind/ground-contact transition.
    public interface IWardrobeFootPoseOwner
    {
        bool CanChangeShoe(string partId, bool equipped);
        void ShoeStateChanged(string partId, bool equipped);
    }

    /// <summary>
    /// Explicit integration API, not a hand controller. It preserves every vertex,
    /// UV, bone weight, bind and morph; only a privately cloned triangle list changes.
    /// </summary>
    public sealed class WardrobeAdapter : IDisposable
    {
        public WardrobeProfile Profile { get; private set; }
        public bool SimulatedClothActive { get; set; }
        public IWardrobeDeformationOwner ClothOwner { get; set; }
        public IWardrobeFootPoseOwner FootPoseOwner { get; set; }
        public event Action<string, bool> Changed;
        readonly Dictionary<string, int[]> indices = new Dictionary<string, int[]>();
        readonly Dictionary<string, GameObject> detached = new Dictionary<string, GameObject>();
        readonly Dictionary<string, WardrobePart> parts = new Dictionary<string, WardrobePart>();
        SkinnedMeshRenderer renderer; Mesh original, working; int[][] originalTriangles;
        bool disposed;

        public WardrobeAdapter(SkinnedMeshRenderer target, string profileDirectory)
        {
            if (target == null || target.sharedMesh == null) throw new ArgumentException("Missing wardrobe mesh");
            renderer = target; original = target.sharedMesh;
            Profile = JsonUtility.FromJson<WardrobeProfile>(File.ReadAllText(Path.Combine(profileDirectory,"wardrobe.json")));
            if (Profile.schemaVersion != 1 || original.vertexCount != Profile.vertexCount ||
                original.subMeshCount != Profile.materialCount || renderer.bones.Length != Profile.boneCount ||
                original.blendShapeCount != Profile.blendShapeCount) throw new InvalidDataException("Wardrobe model contract mismatch");
            originalTriangles = new int[original.subMeshCount][];
            var flat = new List<int>();
            for (int s=0;s<original.subMeshCount;s++) { originalTriangles[s]=original.GetTriangles(s); flat.AddRange(originalTriangles[s]); }
            if (flat.Count != Profile.indexCount || Hash(IntBytes(flat.ToArray())) != Profile.triangleBufferSha256 ||
                Hash(PositionBytes(original.vertices)) != Profile.positionBufferSha256)
                throw new InvalidDataException("Wrong model revision, or another renderer already stripped/deformed the mesh");
            var owned = new HashSet<string>();
            foreach (var part in Profile.parts)
            {
                if (part.materialSlot<0 || part.materialSlot>=original.subMeshCount || part.indexCount%3!=0)
                    throw new InvalidDataException("Invalid garment material/count");
                byte[] bytes=File.ReadAllBytes(Inside(profileDirectory,part.indexFile));
                if (bytes.Length!=part.indexCount*4 || Hash(bytes)!=part.indexSha256) throw new InvalidDataException("Garment triangle fingerprint mismatch");
                var tri=new int[part.indexCount];Buffer.BlockCopy(bytes,0,tri,0,bytes.Length);
                var available=new HashSet<string>();int[] source=originalTriangles[part.materialSlot];
                for(int i=0;i<source.Length;i+=3) available.Add(Key(part.materialSlot,source,i));
                for(int i=0;i<tri.Length;i+=3)
                {
                    string key=Key(part.materialSlot,tri,i);
                    if(!available.Contains(key)||!owned.Add(key)) throw new InvalidDataException("Garment overlap or foreign triangle");
                }
                foreach(var anchor in part.anchors)
                    if(anchor.vertex<0||anchor.vertex>=original.vertexCount) throw new InvalidDataException("Invalid garment anchor");
                parts.Add(part.id,part);indices.Add(part.id,tri);
            }
            working=UnityEngine.Object.Instantiate(original);working.name=original.name+" wardrobe private clone";
            renderer.sharedMesh=working;
        }
        static string Key(int slot,int[] t,int i)=>slot+":"+t[i]+","+t[i+1]+","+t[i+2];
        static byte[] IntBytes(int[] values) { var b=new byte[values.Length*4];Buffer.BlockCopy(values,0,b,0,b.Length);return b; }
        static byte[] PositionBytes(Vector3[] values)
        {
            var f=new float[values.Length*3];for(int i=0;i<values.Length;i++){f[i*3]=values[i].x;f[i*3+1]=values[i].y;f[i*3+2]=values[i].z;}
            var b=new byte[f.Length*4];Buffer.BlockCopy(f,0,b,0,b.Length);return b;
        }
        static string Hash(byte[] bytes)
        { using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant(); }
        static string Inside(string root,string relative)
        {
            if(string.IsNullOrEmpty(relative)||Path.IsPathRooted(relative))throw new InvalidDataException("Invalid part path");
            string prefix=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
            string path=Path.GetFullPath(Path.Combine(prefix,relative));
            if(!path.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Part path leaves profile");return path;
        }
        void Own()
        {
            if(disposed)throw new ObjectDisposedException(nameof(WardrobeAdapter));
            if(renderer.sharedMesh!=working)throw new InvalidOperationException("Mesh ownership changed; rebind after skin/style/cloth change");
        }
        public bool IsEquipped(string id)=>parts.ContainsKey(id)&&!detached.ContainsKey(id);
        public WardrobePart GetPart(string id)=>parts[id];
        public Vector3 AnchorWorld(string id,int anchor=0)
        {
            Own();var a=parts[id].anchors[anchor];Vector3 p=original.vertices[a.vertex];
            var w=original.boneWeights[a.vertex];var bind=original.bindposes;var bones=renderer.bones;
            return (bones[w.boneIndex0].localToWorldMatrix*bind[w.boneIndex0]).MultiplyPoint3x4(p)*w.weight0+
                (bones[w.boneIndex1].localToWorldMatrix*bind[w.boneIndex1]).MultiplyPoint3x4(p)*w.weight1+
                (bones[w.boneIndex2].localToWorldMatrix*bind[w.boneIndex2]).MultiplyPoint3x4(p)*w.weight2+
                (bones[w.boneIndex3].localToWorldMatrix*bind[w.boneIndex3]).MultiplyPoint3x4(p)*w.weight3;
        }
        public bool TryDetach(string id,out GameObject piece,out string reason)
        {
            Own();piece=null;reason="";
            if(!parts.TryGetValue(id,out var part)){reason="Unsupported garment";return false;}
            if(detached.ContainsKey(id)){reason="Already detached";return false;}
            if(part.requiresFootPoseTransition&&(FootPoseOwner==null||!FootPoseOwner.CanChangeShoe(id,false)))
            {reason="Shoe needs host foot-pose transition";return false;}
            Vector3[] clothVertices=null;bool suspended=false;
            if(part.requiresClothOwnershipHandoff&&SimulatedClothActive)
            {
                if(ClothOwner==null||!ClothOwner.TrySuspendPart(id,out clothVertices)){reason="Cloth owner must hand off this part first";return false;}
                suspended=true;
                if(clothVertices==null||clothVertices.Length!=original.vertexCount)
                {ClothOwner.ResumePart(id);reason="Cloth owner returned incompatible geometry";return false;}
            }
            Mesh baked=null;GameObject go=null;
            try
            {
                baked=new Mesh();renderer.BakeMesh(baked);
                if(clothVertices!=null)baked.vertices=clothVertices;
                for(int s=0;s<baked.subMeshCount;s++)baked.SetTriangles(s==part.materialSlot?indices[id]:Array.Empty<int>(),s,false);
                go=new GameObject(part.label+" detached");go.transform.SetParent(renderer.transform,false);
                go.AddComponent<MeshFilter>().sharedMesh=baked;go.AddComponent<MeshRenderer>().sharedMaterials=renderer.sharedMaterials;
                detached.Add(id,go);Rebuild();
                if(part.requiresFootPoseTransition)FootPoseOwner?.ShoeStateChanged(id,false);Changed?.Invoke(id,false);piece=go;return true;
            }
            catch
            {
                detached.Remove(id);Rebuild();
                if(go!=null)ReleaseObject(go);if(baked!=null)ReleaseObject(baked);
                if(suspended)ClothOwner.ResumePart(id);throw;
            }
        }
        public bool TryEquip(string id,out string reason)
        {
            Own();reason="";
            if(!detached.TryGetValue(id,out var go)){reason="Part is not detached";return false;}
            var part=parts[id];
            if(part.requiresFootPoseTransition&&(FootPoseOwner==null||!FootPoseOwner.CanChangeShoe(id,true)))
            {reason="Shoe needs host foot-pose transition";return false;}
            detached.Remove(id);Rebuild();
            var mesh=go.GetComponent<MeshFilter>().sharedMesh;ReleaseObject(go);ReleaseObject(mesh);
            if(part.requiresClothOwnershipHandoff&&SimulatedClothActive)ClothOwner?.ResumePart(id);
            if(part.requiresFootPoseTransition)FootPoseOwner?.ShoeStateChanged(id,true);
            Changed?.Invoke(id,true);return true;
        }
        void Rebuild()
        {
            var hidden=new HashSet<string>();
            foreach(var id in detached.Keys){int s=parts[id].materialSlot;var t=indices[id];for(int i=0;i<t.Length;i+=3)hidden.Add(Key(s,t,i));}
            for(int s=0;s<originalTriangles.Length;s++)
            {
                var originalList=originalTriangles[s];var visible=new List<int>(originalList.Length);
                for(int i=0;i<originalList.Length;i+=3)if(!hidden.Contains(Key(s,originalList,i)))
                {visible.Add(originalList[i]);visible.Add(originalList[i+1]);visible.Add(originalList[i+2]);}
                working.SetTriangles(visible,s,false);
            }
            working.bounds=original.bounds;
        }
        static void ReleaseObject(UnityEngine.Object obj)
        {
            if(obj==null)return;
            if(Application.isPlaying)UnityEngine.Object.Destroy(obj);else UnityEngine.Object.DestroyImmediate(obj);
        }
        public void Dispose()
        {
            if(disposed)return;
            if(renderer!=null&&renderer.sharedMesh==working)renderer.sharedMesh=original;
            foreach(var p in detached)
            {
                if(parts[p.Key].requiresClothOwnershipHandoff&&SimulatedClothActive)ClothOwner?.ResumePart(p.Key);
                var go=p.Value;if(go==null)continue;var mesh=go.GetComponent<MeshFilter>().sharedMesh;
                ReleaseObject(go);ReleaseObject(mesh);
            }
            detached.Clear();if(working!=null)ReleaseObject(working);disposed=true;
        }
    }
}
