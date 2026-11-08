using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using MGFR.Character;
using MGFR.Rendering;

namespace MGFR.RenderStyles.ZmdEndfield
{
 [DefaultExecutionOrder(2100)]
 public sealed partial class ZmdRenderStyle:MonoBehaviour
 {
  public bool IsReady {get;private set;}
  public bool Active {get;private set;}
  public SiCharacterLoader Loader {get;private set;}
  public Material[] ZmdMaterials {get;private set;}
  public Material[] PreviousMaterials {get;private set;}
  SiStylizedRenderer legacy;Mesh previousMesh,zmdMesh;Transform head;Light key;
  LightShadows previousShadows;float previousBias,previousNormalBias,previousNear;
  LightShadowResolution previousResolution;ShadowQuality previousShadowQuality;float previousShadowDistance;
  DepthTextureMode previousDepth;bool legacyEnabled,previousReceive;ShadowCastingMode previousCasting;
  readonly Dictionary<string,Texture2D> textures=new Dictionary<string,Texture2D>();Cubemap studio;
  static bool Has(string value)=>Array.IndexOf(Environment.GetCommandLineArgs(),value)>=0;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(SceneManager.GetActiveScene().name==SiCharacterBootstrap.SceneName&&(Has("-mgfr-zmd")||Has("-mgfr-zmd-review")||Has("-mgfr-skins")))
    new GameObject("ZMD Endfield optional render style").AddComponent<ZmdRenderStyle>();
  }
  IEnumerator Start()
  {
   SiEndfieldClothing clothing;
   while((legacy=FindAnyObjectByType<SiStylizedRenderer>())==null||!legacy.IsReady||
    (clothing=FindAnyObjectByType<SiEndfieldClothing>())==null||!clothing.IsReady)yield return null;
   yield return null;
   Loader=legacy.Loader;head=Loader.Renderer.bones[17];
   PreviousMaterials=(Material[])Loader.Renderer.sharedMaterials.Clone();MrMaterialPolicy.RegisterArray(PreviousMaterials);ZmdMaterials=(Material[])PreviousMaterials.Clone();
   previousMesh=Loader.Renderer.sharedMesh;zmdMesh=UnityEngine.Object.Instantiate(previousMesh);
   zmdMesh.name="Si ZMD optional smooth outline mesh";PrepareOutlineNormals(zmdMesh);
   legacyEnabled=legacy.enabled;
   previousReceive=Loader.Renderer.receiveShadows;previousCasting=Loader.Renderer.shadowCastingMode;
   foreach(var light in FindObjectsByType<Light>(FindObjectsSortMode.None))if(light.type==LightType.Directional){key=light;break;}
   if(key!=null){previousShadows=key.shadows;previousBias=key.shadowBias;previousNormalBias=key.shadowNormalBias;previousNear=key.shadowNearPlane;previousResolution=key.shadowResolution;}
   previousShadowQuality=QualitySettings.shadows;previousShadowDistance=QualitySettings.shadowDistance;
   if(Camera.main!=null)previousDepth=Camera.main.depthTextureMode;
   studio=StudioEnvironment();
   foreach(int index in new[]{0,7,8,9,10,12})
   {
    string kind=index==0?"Face":index==7?"Skin":index==12?"Hair":"Cloth";
    var shader=Resources.Load<Shader>("ZmdEndfield/Zmd"+kind);
    if(shader==null||!shader.isSupported)throw new InvalidOperationException("ZMD shader missing or unsupported: "+kind);
    var original=PreviousMaterials[index];var material=new Material(shader){name=original.name+"_ZMD",renderQueue=original.renderQueue};
    Set(material,"_BaseColor",original.GetTexture("_MainTex"));Set(material,"_Color",original.HasProperty("_Color")?original.GetColor("_Color"):Color.white);
    foreach(string p in new[]{"_Cull","_SrcBlend","_DstBlend","_ZWrite"})if(original.HasProperty(p))Set(material,p,original.GetFloat(p));
    Set(material,"_ZmdExposure",1f);Set(material,"_ZmdNormalScale",1f);
    MrMaterialPolicy.InheritDesktop(material, original);
    Set(material,"_AlphaClip",index==10?.001f:0);
    Set(material,"_OutLine",index==0?.035f:index==7?.055f:index==12?.055f:.065f);
    Set(material,"_OutLineColor",index==0?new Color(.74f,.51f,.43f):index==7?new Color(.56f,.40f,.37f):new Color(.32f,.37f,.40f));
    Set(material,"_ShadowColor",index<=7?new Color(1,.89f,.87f):new Color(.66f,.74f,.84f));Set(material,"_ShadowStrength",.45f);
    Set(material,"_RampStrength",.65f);
    if(index==0)
    {
     Set(material,"_SDF",Existing("stylized","T_actor_common_female_face_01_SDF.png",true));
     Set(material,"_ColorMask",Common("T_actor_common_female_face_01_cm_M.png",true));
     Set(material,"_LipSpecMask",Common("T_actor_common_face_01_hl_M.png",true));
     Set(material,"_DiffuseRamp",Common("T_actor_common_face_01_RD.png",false));
     Set(material,"_DarkColor",new Color(.99f,.82f,.78f));Set(material,"_SecondColor",new Color(.98f,.91f,.88f));
     Set(material,"_SoftShadow",.40f);Set(material,"_SpecularIntensity",.65f);Set(material,"_SpecularColor",Color.white);
    }
    else if(index==7)
    {
     Set(material,"_NormalMap",Existing("stylized","T_actor_jsspsi_body_01_N.png",true));
     Set(material,"_ZmdNormalScale",.22f);Set(material,"_DiffuseRamp",Common("T_actor_common_body_01_RD.png",false));
     Set(material,"_DarkColor",new Color(1f,.97f,.95f));Set(material,"_SecondColor",new Color(1f,.98f,.97f));
     Set(material,"_DarkIntensity",1.8f);Set(material,"_FresnelIntensity",.5f);Set(material,"_FresnelPower",3f);
     Set(material,"_SpecularIntensity",.14f);Set(material,"_SpecShininese",24f);Set(material,"_AO_Offset",.1f);
    }
    else if(index==12)
    {
     Set(material,"_Normal",Existing("stylized","T_actor_jsspsi_hair_01_HN.png",true));
     Set(material,"_Mask",Common("T_actor_jsspsi_hair_01_P.png",true));
     Set(material,"_OutLineMask",Existing("stylized","T_actor_jsspsi_hair_01_ST.png",true));
     Set(material,"_HairLine",Common("T_actor_common_hairline_03_M.png",true));
     material.SetTextureScale("_HairLine",new Vector2(5,1.43f));material.SetTextureOffset("_HairLine",new Vector2(2.39f,0));
     Set(material,"_Aniso",Common("T_actor_common_hairst_01_ST.png",true));
     Set(material,"_DiffuseRamp",Common("T_actor_common_hair_01_RD.png",false));
     Set(material,"_Color",new Color(.92f,.94f,.93f));Set(material,"_SecondColor",new Color(.91f,.95f,.94f));
     Set(material,"_NormalStrength",.38f);Set(material,"_TopLightOffset",-.40f);Set(material,"_TopLightIntensity",2.1f);
     Set(material,"_TopLightColor",new Color(.88f,1,.95f));
     Set(material,"_SpecularOffset",.68f);Set(material,"_SpecularIntensity",4.6f);Set(material,"_SpecularColor",new Color(.75f,.86f,.94f));
     Set(material,"_AnisoNoise",-.01f);Set(material,"_AnisoOffset",.58f);Set(material,"_AnisoPosition",.2f);
     Set(material,"_AnisoShininess",220f);Set(material,"_CutOffset",-.10f);Set(material,"_AO_Offset",.04f);
     Set(material,"_EnvSpecularIntensity",.24f);Set(material,"_EnvSmoothness",.5f);Set(material,"_EnvSpecularColor",new Color(.6f,.7f,.76f));
    }
    else
    {
     string group=index==9?"02":"01";
     Set(material,"_NormalMap",Existing("stylized","T_actor_jsspsi_cloth_"+group+"_N.png",true));
     Set(material,"_MOR",Existing("stylized","T_actor_jsspsi_cloth_"+group+"_P.png",true));
     Set(material,"_Emission",Existing("endfield","T_actor_jsspsi_cloth_"+group+"_E.png",false));
     Set(material,"_DiffuseRamp",Existing("endfield","T_actor_common_cloth_04_RD.png",false));
     Set(material,"_TintColor",Color.white);Set(material,"_NormalStrength",index==9?.65f:.45f);
     Set(material,"_Metallic",-.08f);Set(material,"_Roughness",.17f);Set(material,"_Roughness_Metal",-.15f);
     Set(material,"_Roughness_Contrast",1.10f);Set(material,"_Roughness_Metal_Contrast",1.10f);Set(material,"_AO_Offset",.06f);
     Set(material,"_SpecShininese",96f);Set(material,"_SpecularIntensity",index==10?.75f:1.8f);
     Set(material,"_EnvSpecularIntensity",index==10?.18f:.45f);Set(material,"_EnvSpecularColor",new Color(.70f,.77f,.83f));
     Set(material,"_EmissionIntensity",.45f);Set(material,"_EmissionColor",Color.white);Set(material,"_GradientColor",new Color(.69f,.74f,.80f));
     Set(material,"_GradientMinY",.12f);Set(material,"_GradientMaxY",1.25f);
    }
    MrMaterialPolicy.Register(material,index);ZmdMaterials[index]=material;
   }
   IsReady=true;CacheOriginalAppearance();SetActive(true);
   Debug.Log("[MGFR ZMD] Ready: independently ported face SDF, skin soft light, cloth MOR, dual-normal anisotropic hair, smooth UV7 outlines and shadow/depth rim. F11 toggles preserved current style. Current render sources untouched.");
  }
  static void Set(Material m,string name,float value){if(m.HasProperty(name))m.SetFloat(name,value);}
  static void Set(Material m,string name,Color value){if(m.HasProperty(name))m.SetColor(name,value);}
  static void Set(Material m,string name,Texture value){if(m.HasProperty(name)&&value!=null)m.SetTexture(name,value);}
  Texture2D Common(string file,bool linear)
  {return Load("common/"+file,()=>Resources.Load<TextAsset>("ZmdEndfield/Data/"+file).bytes,linear);}
  Texture2D Existing(string folder,string file,bool linear)
  {return Load(folder+"/"+file,()=>File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,folder,file)),linear);}
  Texture2D Load(string name,Func<byte[]> bytes,bool linear)
  {
   if(textures.TryGetValue(name,out var found))return found;
   var t=new Texture2D(2,2,TextureFormat.RGBA32,true,linear){name=name,wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Trilinear,anisoLevel=4};
   if(!t.LoadImage(bytes(),true))throw new InvalidOperationException("Cannot load "+name);textures.Add(name,t);return t;
  }
  public void SetActive(bool value)
  {
   if(!IsReady||legacy==null||Loader==null||Loader.Renderer==null)return;Active=value;legacy.enabled=value||SkinSwitchingEnabled?false:legacyEnabled;
   Loader.ReplaceSkinMesh(value?zmdMesh:previousMesh);
   var materials=value?ZmdMaterials:PreviousMaterials;
   for(int i=0;i<materials.Length;i++)Loader.Materials[i]=materials[i];Loader.Renderer.sharedMaterials=materials;
   Loader.Renderer.receiveShadows=value||previousReceive;Loader.Renderer.shadowCastingMode=value?ShadowCastingMode.TwoSided:previousCasting;
   QualitySettings.shadows=value?ShadowQuality.All:previousShadowQuality;QualitySettings.shadowDistance=value?8:previousShadowDistance;
   if(key!=null)
   {key.shadows=value?LightShadows.Soft:previousShadows;key.shadowBias=value?.015f:previousBias;key.shadowNormalBias=value?.08f:previousNormalBias;key.shadowNearPlane=value?.1f:previousNear;key.shadowResolution=value?LightShadowResolution.VeryHigh:previousResolution;}
   if(Camera.main!=null)Camera.main.depthTextureMode=value?previousDepth|DepthTextureMode.Depth:previousDepth;
   if(value)UpdateGlobals();
  }
  void LateUpdate()
  {if(!IsReady)return;if(Input.GetKeyDown(KeyCode.F11))SetActive(!Active);if(Active||SkinSwitchingEnabled)UpdateGlobals();}
  void UpdateGlobals()
  {
   if(key!=null){Shader.SetGlobalVector("_ZmdMainLightDirection",-key.transform.forward);Shader.SetGlobalVector("_ZmdMainLightColor",(Vector4)(key.color*key.intensity));}
   Shader.SetGlobalVector("_ZmdAmbientColor",new Vector4(.30f,.32f,.35f,1));
   Vector3 forward=head.TransformDirection(Vector3.back),right=head.right,up=head.up;
   Shader.SetGlobalVector("_HeadForward",forward);Shader.SetGlobalVector("_HeadRight",right);Shader.SetGlobalVector("_HeadUp",up);Shader.SetGlobalVector("_HeadPosition",head.position);
   var face=ZmdMaterials[0];face.SetVector("_HeadForward",forward);face.SetVector("_HeadRight",right);face.SetVector("_HeadUp",up);
   Shader.SetGlobalVector("_SiHeadForward",forward);Shader.SetGlobalVector("_SiHeadRight",right);Shader.SetGlobalVector("_SiHeadUp",up);
   Shader.SetGlobalVector("_SiBodyUp",Loader.Renderer.bones[13].up);
   Shader.SetGlobalTexture("_ZmdStudioCube",studio);Shader.SetGlobalFloat("_Global_EnableRimLight",1);
   Shader.SetGlobalFloat("_Global_ShadowStrength",.35f);Shader.SetGlobalFloat("_Global_OffsetMul",.0025f);
   Shader.SetGlobalFloat("_Global_Threshold",.035f);Shader.SetGlobalFloat("_Global_Smooth",.012f);
   Shader.SetGlobalColor("_Global_RimLightColor",new Color(.77f,.89f,1));Shader.SetGlobalFloat("_Global_RimIntensity",.45f);Shader.SetGlobalFloat("_Global_RimLightBrightness",.65f);
   Shader.SetGlobalColor("_Global_InnerRimColor",new Color(.77f,.84f,.88f));Shader.SetGlobalFloat("_Global_InnerRimPower",5);
   Shader.SetGlobalFloat("_Global_InnerRimIntensity",.35f);Shader.SetGlobalFloat("_Global_InnerRimBrightness",.5f);Shader.SetGlobalFloat("_Global_InnerRimBias",0);
   Shader.SetGlobalVector("_Global_RimLightDirection",new Vector3(-.55f,.6f,-.5f));Shader.SetGlobalFloat("_Global_RimLightSoftness",.55f);Shader.SetGlobalFloat("_Global_RimLightOffset",-.1f);
  }
  void OnGUI()
  {if(IsReady&&!Has("-mgfr-zmd-review"))GUI.Label(new Rect(18,Screen.height-38,520,28),Active?"F11  渲染：ZMD 终末地风格":"F11  渲染：保留的当前风格");}
  static void PrepareOutlineNormals(Mesh mesh)
  {
   var vertices=mesh.vertices;var normals=mesh.normals;var tangents=mesh.tangents;var triangles=mesh.triangles;
   var areas=new float[vertices.Length];var buckets=new Dictionary<Vector3Int,List<int>>();
   for(int t=0;t<triangles.Length;t+=3)
   {int a=triangles[t],b=triangles[t+1],c=triangles[t+2];float area=Vector3.Cross(vertices[b]-vertices[a],vertices[c]-vertices[a]).magnitude;areas[a]+=area;areas[b]+=area;areas[c]+=area;}
   Vector3Int Key(Vector3 p)=>new Vector3Int(Mathf.RoundToInt(p.x*100000),Mathf.RoundToInt(p.y*100000),Mathf.RoundToInt(p.z*100000));
   for(int i=0;i<vertices.Length;i++){var k=Key(vertices[i]);if(!buckets.TryGetValue(k,out var list)){list=new List<int>();buckets[k]=list;}list.Add(i);}
   var uv=new List<Vector4>(vertices.Length);
   for(int i=0;i<vertices.Length;i++)
   {
    var n=normals[i].normalized;var sum=Vector3.zero;
    foreach(int other in buckets[Key(vertices[i])])if(Vector3.Dot(n,normals[other])>.2f)sum+=normals[other]*Mathf.Max(areas[other],1e-8f);
    var smooth=sum.sqrMagnitude>1e-12f?sum.normalized:n;var tangent=(Vector3)tangents[i];var bitangent=Vector3.Cross(n,tangent)*tangents[i].w;
    uv.Add(new Vector4(Vector3.Dot(smooth,tangent),Vector3.Dot(smooth,bitangent),Vector3.Dot(smooth,n),0));
   }
   mesh.SetUVs(7,uv);
  }
  static Cubemap StudioEnvironment()
  {
   const int size=64;var cube=new Cubemap(size,TextureFormat.RGBAHalf,true){name="ZMD local studio IBL"};
   var key=new Vector3(-.4f,.65f,-.6f).normalized;var fill=new Vector3(.7f,.2f,.5f).normalized;
   for(int face=0;face<6;face++)
   {
    var pixels=new Color[size*size];
    for(int y=0;y<size;y++)for(int x=0;x<size;x++)
    {
     float u=2*(x+.5f)/size-1,v=2*(y+.5f)/size-1;Vector3 d;
     switch(face){case 0:d=new Vector3(1,-v,-u);break;case 1:d=new Vector3(-1,-v,u);break;case 2:d=new Vector3(u,1,v);break;case 3:d=new Vector3(u,-1,-v);break;case 4:d=new Vector3(u,-v,1);break;default:d=new Vector3(-u,-v,-1);break;}
     d.Normalize();var c=Color.Lerp(new Color(.075f,.085f,.10f),new Color(.38f,.42f,.46f),d.y*.5f+.5f);
     c+=new Color(.95f,.86f,.72f)*Mathf.Pow(Mathf.Max(0,Vector3.Dot(d,key)),22);c+=new Color(.3f,.38f,.48f)*Mathf.Pow(Mathf.Max(0,Vector3.Dot(d,fill)),14);c.a=1;pixels[y*size+x]=c;
    }
    cube.SetPixels(pixels,(CubemapFace)face);
   }
   cube.Apply(true,true);cube.filterMode=FilterMode.Trilinear;return cube;
  }
  void OnDestroy()
  {
   if(IsReady&&Loader!=null&&legacy!=null)SetActive(false);
   DisposeSkinVariants();
   foreach(var t in textures.Values)Destroy(t);if(studio!=null)Destroy(studio);
  }
 }
}
