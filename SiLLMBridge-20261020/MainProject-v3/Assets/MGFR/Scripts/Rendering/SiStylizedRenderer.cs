using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;
using MGFR.Experience;

namespace MGFR.Rendering
{
 [DefaultExecutionOrder(1800)]
 public sealed class SiStylizedRenderer:MonoBehaviour
 {
  public bool IsReady {get;private set;}
  public bool Stylized {get;private set;}=true;
  public SiCharacterLoader Loader {get;private set;}
  Material[] original,styled;
  Transform head,body;
  readonly Dictionary<string,Texture2D> textures=new Dictionary<string,Texture2D>();
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(SceneManager.GetActiveScene().name==SiCharacterBootstrap.SceneName)
    new GameObject("Si stylized rendering").AddComponent<SiStylizedRenderer>();
  }
  IEnumerator Start()
  {
   while((Loader=FindAnyObjectByType<SiCharacterLoader>())==null||!Loader.IsReady||FindAnyObjectByType<IdleMotionPlayer>()==null)
    yield return null;
   // ExperienceBootstrap has completed its one-time rest/bind correction.
   yield return null;
   head=Loader.Renderer.bones[17];body=Loader.Renderer.bones[13];
   var mesh=Loader.Renderer.sharedMesh;mesh.RecalculateTangents();
   original=(Material[])Loader.Materials.Clone();styled=new Material[original.Length];
   var shader=Resources.Load<Shader>("MgfrStylized");
   if(shader==null)throw new System.InvalidOperationException("Stylized shader was not included in this build");
   for(int i=0;i<original.Length;i++)
   {
    var material=new Material(original[i]);material.shader=shader;material.name=original[i].name+"_stylized";
    material.renderQueue=original[i].renderQueue;
    Configure(material,i);styled[i]=material;
   }
   QualitySettings.antiAliasing=4;Camera.main.allowMSAA=true;
   SetStylized(true);IsReady=true;
   Debug.Log("[MGFR render] 14 material variants ready, RG normals + face SDF + layered hair sheen; F6 compare");
  }
  Texture2D Load(string file,bool linear=true)
  {
   if(textures.TryGetValue(file,out var cached))return cached;
   var texture=new Texture2D(2,2,TextureFormat.RGBA32,true,linear);
   texture.LoadImage(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"stylized",file)),true);
   texture.name=file;texture.wrapMode=TextureWrapMode.Repeat;texture.filterMode=FilterMode.Trilinear;texture.anisoLevel=4;
   textures.Add(file,texture);return texture;
  }
  void Configure(Material m,int i)
  {
   m.SetFloat("_Brightness",1.05f);m.SetFloat("_NormalY",-1);
   m.SetFloat("_ShadowThreshold",.51f);m.SetFloat("_Softness",.16f);
   m.SetFloat("_SpecStrength",.45f);m.SetFloat("_Roughness",.65f);m.SetFloat("_MatCapStrength",.24f);
   m.SetColor("_ShadowTint",new Color(.62f,.7f,.79f));m.SetColor("_LightTint",new Color(1.02f,1f,.96f));
   m.SetColor("_OutlineTint",new Color(.14f,.18f,.2f,.48f));m.SetFloat("_OutlineWidth",.0004f);
   m.SetFloat("_Kind",3);m.SetTexture("_MatCap",Load("T_actor_common_matcap_08_D.png",false));
   switch(i)
   {
    case 0:
     m.SetFloat("_Kind",0);m.SetFloat("_NormalStrength",.12f);m.SetFloat("_Brightness",1.15f);
     m.SetFloat("_SpecStrength",.10f);m.SetFloat("_MatCapStrength",0);m.SetFloat("_OutlineWidth",0);
     m.SetColor("_ShadowTint",new Color(.89f,.78f,.75f));m.SetColor("_LightTint",new Color(1.03f,1f,.98f));
     m.SetTexture("_NormalData",Load("T_actor_jsspsi_face_01_N.png"));
     m.SetTexture("_FaceSDF",Load("T_actor_common_female_face_01_SDF.png"));
     m.SetTexture("_FaceMask",Load("T_actor_jsspsi_face_01_ST.png"));break;
    case 1:case 2:
     m.SetFloat("_Kind",5);m.SetFloat("_SpecStrength",.06f);m.SetFloat("_Brightness",1.03f);
     m.SetFloat("_MatCapStrength",0);m.SetFloat("_OutlineWidth",0);break;
    case 7:
     m.SetFloat("_Kind",1);m.SetFloat("_NormalStrength",.20f);m.SetFloat("_SpecStrength",.21f);
     m.SetFloat("_Roughness",.8f);m.SetFloat("_MatCapStrength",.015f);m.SetFloat("_Brightness",1.1f);
     m.SetColor("_ShadowTint",new Color(.8f,.63f,.61f));
     m.SetTexture("_NormalData",Load("T_actor_jsspsi_body_01_N.png"));break;
    case 8:case 10:
     m.SetFloat("_NormalStrength",.4f);m.SetFloat("_HasPacked",1);
     m.SetTexture("_NormalData",Load("T_actor_jsspsi_cloth_01_N.png"));
     m.SetTexture("_PackedData",Load("T_actor_jsspsi_cloth_01_P.png"));
     if(i==10){m.SetFloat("_OutlineWidth",0);m.SetFloat("_SpecStrength",.16f);m.SetFloat("_MatCapStrength",.02f);}
     break;
    case 9:
     m.SetFloat("_NormalStrength",.32f);m.SetFloat("_HasPacked",1);m.SetFloat("_Roughness",.48f);
     m.SetTexture("_NormalData",Load("T_actor_jsspsi_cloth_02_N.png"));
     m.SetTexture("_PackedData",Load("T_actor_jsspsi_cloth_02_P.png"));break;
    case 12:
     m.SetFloat("_Kind",2);m.SetFloat("_NormalStrength",.26f);m.SetFloat("_SpecStrength",.75f);
     m.SetFloat("_Roughness",.55f);m.SetFloat("_Brightness",1.04f);m.SetFloat("_MatCapStrength",.08f);
     m.SetFloat("_OutlineWidth",.00035f);m.SetFloat("_ShadowThreshold",.58f);m.SetFloat("_Softness",.14f);
     m.SetColor("_ShadowTint",new Color(.68f,.77f,.78f));
     m.SetTexture("_NormalData",Load("T_actor_jsspsi_hair_01_HN.png"));
     m.SetTexture("_HairSpec",Load("T_actor_jsspsi_hair_01_ST.png"));break;
    default:
     m.SetFloat("_Kind",7);m.SetFloat("_OutlineWidth",0);break;
   }
  }
  public void SetStylized(bool value)
  {
   Stylized=value;var selected=value?styled:original;
   for(int i=0;i<selected.Length;i++)Loader.Materials[i]=selected[i];
   Loader.Renderer.sharedMaterials=selected;
  }
  void LateUpdate()
  {
   if(!IsReady)return;
   Shader.SetGlobalVector("_SiHeadForward",head.TransformDirection(Vector3.back));
   Shader.SetGlobalVector("_SiHeadRight",head.TransformDirection(Vector3.right));
   Shader.SetGlobalVector("_SiHeadUp",head.up);Shader.SetGlobalVector("_SiBodyUp",body.up);
   if(Input.GetKeyDown(KeyCode.F6))SetStylized(!Stylized);
  }
 }
}
