using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;

namespace MGFR.Rendering
{
 [DefaultExecutionOrder(1900)]
 public sealed class SiEndfieldClothing:MonoBehaviour
 {
  public bool IsReady {get;private set;}
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(SceneManager.GetActiveScene().name==SiCharacterBootstrap.SceneName)
    new GameObject("Si Endfield clothing").AddComponent<SiEndfieldClothing>();
  }
  IEnumerator Start()
  {
   SiStylizedRenderer renderer;
   while((renderer=FindAnyObjectByType<SiStylizedRenderer>())==null||!renderer.IsReady)yield return null;
   var shader=Resources.Load<Shader>("MgfrEndfieldClothing");
   var diffuse=Load("T_actor_common_cloth_04_RD.png");
   var warm=Load("T_actor_common_cloth_04_RS.png");var cool=Load("T_actor_common_cloth_02_RS.png");
   var e1=Load("T_actor_jsspsi_cloth_01_E.png");var e2=Load("T_actor_jsspsi_cloth_02_E.png");
   var cube=StudioEnvironment();
   foreach(int index in new[]{8,9,10})
   {
    // Mutate the styled instances, so the existing F6 original/styled switch
    // remains coherent. Original materials and transparent depth state survive.
    var m=renderer.Loader.Materials[index];int queue=m.renderQueue;
    m.shader=shader;m.renderQueue=queue;
    m.SetTexture("_DiffuseRamp",diffuse);m.SetTexture("_SpecularRamp",index==9?cool:warm);
    m.SetTexture("_EmissionMap",index==9?e2:e1);m.SetTexture("_StudioCube",cube);
    m.SetFloat("_Metallic",1);m.SetFloat("_SmoothnessScale",.9f);m.SetFloat("_OcclusionStrength",.8f);
    m.SetFloat("_SpecStrength",index==10?.35f:.75f);m.SetFloat("_ReflectionStrength",index==10?.25f:.65f);
    m.SetFloat("_EmissionStrength",.45f);m.SetFloat("_RampStrength",.65f);m.SetFloat("_SpecRampFresnel",0);
    m.SetColor("_AmbientColor",new Color(.3f,.32f,.35f));
   }
   IsReady=true;
   Debug.Log("[MGFR Endfield] cloth 8/9/10: P=metal/spec/AO/smoothness, RD + 2D RS + emission + studio IBL; alpha depth preserved");
  }
  static Texture2D Load(string file)
  {
   var t=new Texture2D(2,2,TextureFormat.RGBA32,true,false);
   t.LoadImage(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"endfield",file)),true);
   t.name=file;t.wrapMode=TextureWrapMode.Clamp;t.filterMode=FilterMode.Trilinear;return t;
  }
  static Cubemap StudioEnvironment()
  {
   const int size=64;
   var cube=new Cubemap(size,TextureFormat.RGBAHalf,true);cube.name="Procedural studio, not room GI";
   var key=new Vector3(-.4f,.65f,-.6f).normalized;var fill=new Vector3(.7f,.2f,.5f).normalized;
   for(int face=0;face<6;face++)
   {
    var pixels=new Color[size*size];
    for(int y=0;y<size;y++)for(int x=0;x<size;x++)
    {
     float u=2*(x+.5f)/size-1,v=2*(y+.5f)/size-1;Vector3 d;
     switch(face)
     {
      case 0:d=new Vector3(1,-v,-u);break;case 1:d=new Vector3(-1,-v,u);break;
      case 2:d=new Vector3(u,1,v);break;case 3:d=new Vector3(u,-1,-v);break;
      case 4:d=new Vector3(u,-v,1);break;default:d=new Vector3(-u,-v,-1);break;
     }
     d.Normalize();var c=Color.Lerp(new Color(.09f,.095f,.11f),new Color(.38f,.42f,.48f),d.y*.5f+.5f);
     c+=new Color(.95f,.86f,.72f)*Mathf.Pow(Mathf.Max(0,Vector3.Dot(d,key)),22);
     c+=new Color(.3f,.38f,.48f)*Mathf.Pow(Mathf.Max(0,Vector3.Dot(d,fill)),14);
     c.a=1;pixels[y*size+x]=c;
    }
    cube.SetPixels(pixels,(CubemapFace)face);
   }
   cube.Apply(true,true);cube.filterMode=FilterMode.Trilinear;return cube;
  }
 }
}
