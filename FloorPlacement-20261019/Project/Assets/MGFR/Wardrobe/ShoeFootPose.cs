using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.Skins;
using UnityEngine;

namespace MGFR.Wardrobe
{
    [Serializable] public sealed class ShoeMorphInfo {public string name,file;public int side;}
    [Serializable] public sealed class ShoePoseInfo {public int vertexCount;public float height;public ShoeMorphInfo[] morphs;}
    [DefaultExecutionOrder(850)]
    public sealed class ShoeFootPose : MonoBehaviour,IWardrobeFootPoseOwner
    {
        public static ShoeFootPose Instance {get;private set;}
        public bool Active=>skins!=null&&skins.IsReady&&skins.CurrentId=="swimsuit"&&skins.CurrentAppearance.Mesh.vertexCount==config.vertexCount;
        public bool Ready=>config!=null&&Active;
        public bool Manual;
        public readonly float[] Weights={1,1};
        public float Height=>config!=null?config.height:0;
        public float AppliedBodyLift {get;private set;}
        SiSkinSwitcher skins;ShoePoseInfo config;Vector3[][] delta,normal;
        Transform centre;Vector3 injected;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-shoes")>=0)new GameObject("Independent shoe foot pose").AddComponent<ShoeFootPose>();}
        IEnumerator Start()
        {
            Instance=this;
            while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady)yield return null;
            string path=Path.Combine(Application.streamingAssetsPath,"skins/si-swimsuit-shoes");
            config=JsonUtility.FromJson<ShoePoseInfo>(File.ReadAllText(Path.Combine(path,"foot-pose.json")));
            delta=new Vector3[2][];normal=new Vector3[2][];
            for(int h=0;h<2;h++)
            {
                byte[] bytes=File.ReadAllBytes(Path.Combine(path,config.morphs[h].file));
                if(bytes.Length!=config.vertexCount*24)throw new InvalidDataException("Shoe morph layout mismatch");
                float[] values=new float[bytes.Length/4];Buffer.BlockCopy(bytes,0,values,0,bytes.Length);
                delta[h]=new Vector3[config.vertexCount];normal[h]=new Vector3[config.vertexCount];
                for(int i=0;i<config.vertexCount;i++)
                {delta[h][i]=new Vector3(values[i*3],values[i*3+1],values[i*3+2]);int j=config.vertexCount*3+i*3;normal[h][i]=new Vector3(values[j],values[j+1],values[j+2]);}
            }
            centre=skins.Loader.Renderer.bones[5];
        }
        public void UndoLift()
        {if(centre!=null)centre.localPosition-=injected;injected=Vector3.zero;AppliedBodyLift=0;}
        void LateUpdate(){if(!Manual)Tick(Time.deltaTime);}
        public void Tick(float dt)
        {
            UndoLift();if(!Ready)return;
            skins.Style.VisitShoeMeshes(EnsureMorphs);
            var live=WardrobeLiveRuntime.Instance;
            for(int h=0;h<2;h++)
            {
                float target=live!=null&&live.IsReady?(live.IsEquipped(h==0?"shoe_left":"shoe_right")?1:0):1;
                Weights[h]=Mathf.MoveTowards(Weights[h],target,Mathf.Clamp(dt,0,.05f)/.28f);
            }
            var renderer=skins.Loader.Renderer;EnsureMorphs(renderer.sharedMesh);
            for(int h=0;h<2;h++)renderer.SetBlendShapeWeight(renderer.sharedMesh.GetBlendShapeIndex(config.morphs[h].name),Weights[h]*100);
            AppliedBodyLift=Height*Mathf.Min(Weights[0],Weights[1]);
            injected=Vector3.up*AppliedBodyLift;centre.localPosition+=injected;
        }
        void EnsureMorphs(Mesh mesh)
        {
            if(mesh==null||mesh.vertexCount!=config.vertexCount)return;
            for(int h=0;h<2;h++)if(mesh.GetBlendShapeIndex(config.morphs[h].name)<0)
                mesh.AddBlendShapeFrame(config.morphs[h].name,100,delta[h],normal[h],null);
        }
        public bool CanChangeShoe(string partId,bool equipped)=>Ready&&(partId=="shoe_left"||partId=="shoe_right");
        public void ShoeStateChanged(string partId,bool equipped){}
        void OnDestroy(){UndoLift();if(Instance==this)Instance=null;}
    }
}
