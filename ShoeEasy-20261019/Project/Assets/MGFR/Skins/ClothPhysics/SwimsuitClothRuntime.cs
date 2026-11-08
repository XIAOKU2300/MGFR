using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.BareHands;
using MGFR.Wardrobe;

namespace MGFR.Skins.ClothPhysics
{
    [DefaultExecutionOrder(1400)]
    public sealed class SwimsuitClothRuntime : MonoBehaviour
    {
        SiSkinSwitcher skins;BareHandInteraction hands;
        Mesh visual;MeshRenderer clothRenderer;GameObject clothObject;
        Vector3[] vertices;int[] sourceIds;Transform[] cachedBones;Matrix4x4[] cachedBinds;
        readonly Matrix4x4[] drivers=new Matrix4x4[4];
        readonly int[] driverBones={32,58,15,13};
        readonly Dictionary<Mesh,Mesh> stripped=new Dictionary<Mesh,Mesh>();
        readonly Dictionary<Mesh,Mesh> fullMeshes=new Dictionary<Mesh,Mesh>();
        readonly HandPinchState[] pinch={new HandPinchState(),new HandPinchState()};
        readonly bool[] blocked={true,true};
        readonly List<SwimsuitClothSolver.Capsule> body=new List<SwimsuitClothSolver.Capsule>();
        readonly List<SwimsuitClothSolver.Capsule>[] handCapsules={new List<SwimsuitClothSolver.Capsule>(),new List<SwimsuitClothSolver.Capsule>()};
        readonly Func<int,bool> ownsHand;
        Vector3 previousRoot;bool wasActive;float nextSummary;
        public SwimsuitClothSolver Solver {get;private set;}
        public bool Active=>skins!=null&&skins.IsReady&&skins.CurrentId=="swimsuit";
        public bool IsReady=>Solver!=null;
        public float LastMilliseconds {get;private set;}
        public SwimsuitClothRuntime(){ownsHand=OwnsHand;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-skins")>=0)
                new GameObject("Swimsuit independent cloth simulation").AddComponent<SwimsuitClothRuntime>();
        }
        IEnumerator Start()
        {
            while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||
                  (hands=FindAnyObjectByType<BareHandInteraction>())==null||!hands.IsReady)yield return null;
            hands.ExternalClothGrab=ownsHand;
        }
        bool OwnsHand(int hand)=>(WardrobeLiveRuntime.Instance!=null&&WardrobeLiveRuntime.Instance.OwnsHand(hand))||(Active&&Solver!=null&&Solver.Grips[hand].particle>=0);
        void Build()
        {
            var source=skins.CurrentAppearance.Mesh;
            cachedBones=skins.Loader.Renderer.bones;cachedBinds=source.bindposes;
            if(source.vertexCount!=76308||source.subMeshCount!=14)
                throw new InvalidOperationException("Swimsuit cloth profile requires v4 with appended shoes.");
            var triangles=source.GetTriangles(10);var map=new Dictionary<int,int>();var ids=new List<int>();
            for(int i=0;i<triangles.Length;i++)
            {
                int id=triangles[i];if(!map.ContainsKey(id)){map.Add(id,ids.Count);ids.Add(id);}
                triangles[i]=map[id];
            }
            wardrobeMap=map;wardrobeTriangles=(int[])triangles.Clone();
            sourceIds=ids.ToArray();var rest=source.vertices;var normals=source.normals;var uv=source.uv;var tangents=source.tangents;
            var positions=new Vector3[ids.Count];var n=new Vector3[ids.Count];var u=new Vector2[ids.Count];var t=new Vector4[ids.Count];
            for(int i=0;i<ids.Count;i++)
            {
                int id=ids[i];if(id<57681||id>=73377)throw new InvalidOperationException("Unexpected cloth part index.");
                positions[i]=rest[id];n[i]=normals[id];u[i]=uv[id];t[i]=tangents[id];
            }
            visual=new Mesh{name="Dynamic swimsuit sleeves frill skirt"};visual.MarkDynamic();
            visual.vertices=positions;visual.normals=n;visual.uv=u;visual.tangents=t;visual.triangles=triangles;
            vertices=new Vector3[positions.Length];
            clothObject=new GameObject("Simulated swimsuit cloth");clothObject.transform.SetParent(skins.Loader.transform,false);
            clothObject.AddComponent<MeshFilter>().sharedMesh=visual;clothRenderer=clothObject.AddComponent<MeshRenderer>();
            clothRenderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.TwoSided;clothRenderer.receiveShadows=true;
            UpdateDrivers();
            Solver=new SwimsuitClothSolver(positions,sourceIds,triangles,Mathf.Abs(skins.Loader.transform.lossyScale.x),drivers);
            Debug.Log($"[Swimsuit cloth] ready: {Solver.Particles.Length} particles, {Solver.ConstraintCount} XPBD links, sleeves/frill/skirt; hand capsules and pinch traction.");
        }
        Dictionary<int,int> wardrobeMap;
        int[] wardrobeTriangles;
        public Mesh FullRenderMesh
        {
            get {var current=skins.Loader.Renderer.sharedMesh;return fullMeshes.TryGetValue(current,out var full)?full:current;}
        }
        public int VisibleClothTriangles=>visual!=null?visual.triangles.Length/3:0;
        public void SetWardrobeMesh(Mesh full)
        {
            if(!stripped.TryGetValue(full,out var without))
            {
                without=Instantiate(full);without.name=full.name+" wardrobe + separate XPBD";
                stripped.Add(full,without);fullMeshes.Add(without,full);
            }
            for(int s=0;s<full.subMeshCount;s++)without.SetTriangles(s==10?Array.Empty<int>():full.GetTriangles(s),s,false);
            skins.Loader.ReplaceSkinMesh(without);
        }
        public void ReleaseWardrobeMesh(Mesh full)
        {
            if(!stripped.TryGetValue(full,out var without))return;
            if(skins!=null&&skins.Loader!=null&&skins.Loader.Renderer!=null&&skins.Loader.Renderer.sharedMesh==without)
            {
                // Find the current style's unmodified complete source, not the adapter clone.
                skins.Style.SetActive(skins.Style.Active);
            }
            stripped.Remove(full);fullMeshes.Remove(without);Destroy(without);
        }
        static int WardrobeGroup(string id)=>id=="sleeve_left"?0:id=="sleeve_right"?1:id=="chest_frill"?2:id=="cover_skirt"?3:-1;
        public bool TryWardrobeVertex(int source,out Vector3 world)
        {
            world=Vector3.zero;
            if(vertices==null||wardrobeMap==null||!wardrobeMap.TryGetValue(source,out var index))return false;
            world=skins.Loader.transform.TransformPoint(vertices[index]);return true;
        }
        void SetWardrobeGroup(int group,bool shown)
        {
            Solver.EnabledGroups[group]=shown;Solver.ResetGroup(group);
            var t=new List<int>(wardrobeTriangles.Length);
            for(int i=0;i<wardrobeTriangles.Length;i+=3)
                if(Solver.EnabledGroups[Solver.RenderGroupForVertex(wardrobeTriangles[i])])
                {t.Add(wardrobeTriangles[i]);t.Add(wardrobeTriangles[i+1]);t.Add(wardrobeTriangles[i+2]);}
            visual.SetTriangles(t,0,false);
        }
        public bool SuspendWardrobePart(string id,out Vector3[] all)
        {
            all=null;int group=WardrobeGroup(id);if(group<0||Solver==null||!Active)return false;
            var baked=new Mesh();skins.Loader.Renderer.BakeMesh(baked);all=baked.vertices;Destroy(baked);
            for(int i=0;i<sourceIds.Length;i++)all[sourceIds[i]]=vertices[i];
            SetWardrobeGroup(group,false);return true;
        }
        public void ResumeWardrobePart(string id)
        {int group=WardrobeGroup(id);if(group>=0&&Solver!=null)SetWardrobeGroup(group,true);}
        void UpdateDrivers()
        {
            var bones=cachedBones;var bind=cachedBinds;
            for(int i=0;i<4;i++)drivers[i]=bones[driverBones[i]].localToWorldMatrix*bind[driverBones[i]];
        }
        void EnsureMainMesh()
        {
            var mesh=skins.Loader.Renderer.sharedMesh;
            if(fullMeshes.ContainsKey(mesh))return;
            if(!stripped.TryGetValue(mesh,out var without))
            {
                without=Instantiate(mesh);without.name=mesh.name+" (cloth rendered separately)";
                without.SetTriangles(Array.Empty<int>(),10,false);stripped.Add(mesh,without);fullMeshes.Add(without,mesh);
            }
            skins.Loader.ReplaceSkinMesh(without);
        }
        public bool Manual;
        void LateUpdate(){if(!Manual)Tick(Time.deltaTime);}
        public void Tick(float delta)
        {
            if(skins==null||!skins.IsReady||hands==null||!hands.IsReady)return;
            if(!Active)
            {
                if(clothObject!=null)clothObject.SetActive(false);
                if(wasActive&&Solver!=null){Solver.Release(0);Solver.Release(1);ResetPinches();}
                wasActive=false;return;
            }
            long started=System.Diagnostics.Stopwatch.GetTimestamp();
            if(Solver==null)Build();
            EnsureMainMesh();UpdateDrivers();Solver.SetTargets(drivers);
            if(!wasActive||Vector3.Distance(previousRoot,skins.Loader.transform.position)>.3f)
            {Solver.Reset();ResetPinches();}
            previousRoot=skins.Loader.transform.position;wasActive=true;clothObject.SetActive(true);
            clothObject.layer=skins.Loader.gameObject.layer;
            if(clothRenderer.sharedMaterial!=skins.Loader.Materials[10])clothRenderer.sharedMaterial=skins.Loader.Materials[10];
            UpdateGrabs(delta);BuildContacts();
            if(hands.Physics.Simulate)
            {
                float gust=.35f+.25f*Mathf.Sin(Time.time*1.7f);
                var wind=skins.Loader.transform.TransformDirection(new Vector3(gust,.07f,Mathf.Sin(Time.time*.8f)*.25f));
                Solver.Step(delta,body,handCapsules,wind);
            }
            else Solver.Reset();
            Solver.WriteVertices(drivers,skins.Loader.transform.worldToLocalMatrix,vertices);
            visual.vertices=vertices;visual.RecalculateNormals();visual.RecalculateTangents();visual.RecalculateBounds();
            LastMilliseconds=(System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000f/System.Diagnostics.Stopwatch.Frequency;
            if(Time.unscaledTime>nextSummary)
            {nextSummary=Time.unscaledTime+5;Debug.Log($"[Swimsuit cloth] simulated={hands.Physics.Simulate}; offset={Solver.MaximumOffset:F3}m; grips={Solver.Grips[0].particle},{Solver.Grips[1].particle}; contacts={Solver.Contacts}; cpu={LastMilliseconds:F2}ms");}
        }
        void UpdateGrabs(float dt)
        {
            for(int h=0;h<2;h++)
            {
                if(WardrobeLiveRuntime.Instance!=null&&WardrobeLiveRuntime.Instance.OwnsHand(h)){pinch[h].Reset();blocked[h]=true;continue;}
                var frame=hands.Source.Frames[h];bool tracked=hands.PreferBareHands&&frame.Tracked;
                if(!tracked||!hands.Physics.Simulate)
                {Solver.Release(h);pinch[h].Reset();blocked[h]=true;continue;}
                bool closed=pinch[h].Update(frame,dt);
                if(!closed)
                {
                    Solver.Release(h);
                    if(frame.CanStartPinch&&Vector3.Distance(frame.Joints[5].position,frame.Joints[10].position)>
                        Mathf.Clamp(frame.Radius[5]+frame.Radius[10],.009f,.032f)+.020f*frame.Scale)blocked[h]=false;
                }
                if(Solver.Grips[h].particle<0&&pinch[h].CanAcquire&&!blocked[h]&&hands.GrabbedBody[h]<0)
                    Solver.Grab(h,frame.PinchPoint,Mathf.Clamp(.035f*frame.Scale,.03f,.05f));
                if(Solver.Grips[h].particle>=0)
                {
                    var point=Solver.Particles[Solver.Grips[h].particle].position;
                    if(Vector3.Distance(point,frame.PinchPoint)>.30f)
                    {Solver.Release(h);blocked[h]=true;}
                    else{Solver.MoveGrip(h,frame.PinchPoint);hands.GrabStatus[h]="泳装布料抓取中";}
                }
            }
        }
        void ResetPinches(){for(int h=0;h<2;h++){pinch[h].Reset();blocked[h]=true;}}
        void BuildContacts()
        {
            body.Clear();var b=cachedBones;float scale=Mathf.Abs(skins.Loader.transform.lossyScale.x);
            AddBody(b[13].position,b[15].position,.095f*scale);
            AddBody(b[21].position,b[22].position,.064f*scale);AddBody(b[25].position,b[26].position,.064f*scale);
            AddBody(b[22].position,b[23].position,.044f*scale);AddBody(b[26].position,b[27].position,.044f*scale);
            AddBody(b[32].position,b[35].position,.032f*scale);AddBody(b[58].position,b[61].position,.032f*scale);
            for(int h=0;h<2;h++)
            {
                handCapsules[h].Clear();var f=hands.Source.Frames[h];if(!hands.PreferBareHands||!f.Tracked)continue;
                for(int i=2;i<5;i++)AddHand(h,f,i,i+1);
                for(int finger=0;finger<4;finger++)for(int joint=0;joint<4;joint++)AddHand(h,f,6+finger*5+joint,7+finger*5+joint);
                if(f.Valid[0])handCapsules[h].Add(new SwimsuitClothSolver.Capsule{a=f.Joints[0].position,b=f.Joints[0].position,radius=.028f});
            }
        }
        void AddBody(Vector3 a,Vector3 b,float r)=>body.Add(new SwimsuitClothSolver.Capsule{a=a,b=b,radius=r+.004f});
        void AddHand(int h,HandFrame frame,int a,int b)
        {
            if(!frame.Valid[a]||!frame.Valid[b])return;
            handCapsules[h].Add(new SwimsuitClothSolver.Capsule{a=frame.Joints[a].position,b=frame.Joints[b].position,
                radius=Mathf.Clamp((frame.Radius[a]+frame.Radius[b])*.5f,.005f,.02f)+.002f});
        }
        void OnDestroy()
        {
            if(hands!=null&&hands.ExternalClothGrab==ownsHand)hands.ExternalClothGrab=null;
            if(skins!=null&&skins.IsReady&&skins.Style!=null&&skins.Loader!=null&&skins.Loader.Renderer!=null)
            {
                var current=skins.Loader.Renderer.sharedMesh;
                if(fullMeshes.TryGetValue(current,out var full))skins.Loader.ReplaceSkinMesh(full);
            }
            foreach(var mesh in stripped.Values)Destroy(mesh);
            if(visual!=null)Destroy(visual);if(clothObject!=null)Destroy(clothObject);
        }
    }
}
