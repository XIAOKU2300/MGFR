using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;

namespace MGFR.Dialogue
{
 /// <summary>Small binocular camera-relative transcript, rendered above scene depth.</summary>
 public sealed class CameraChatOverlay:MonoBehaviour
 {
  const float Width=1120,Scale=.00055f,Distance=1.25f;
  const int BodySize=42,LineStep=52;
  readonly TextGenerator generator=new TextGenerator();
  readonly List<Vector3> vertices=new List<Vector3>();readonly List<Vector2> uv=new List<Vector2>();
  readonly List<Color32> colors=new List<Color32>();readonly List<int> triangles=new List<int>();
  Font font;Material textMaterial,backMaterial;Mesh textMesh,backMesh;MeshRenderer textRenderer,backRenderer;
  DialogueClient client;Camera view;bool dirty=true,preview,shown=true;float nextRefresh;
  string user="",reply="",lastState="";float panelHeight;int roleGlyphs;
  public bool Visible=>shown;
  public string DisplayedUser=>user;public string DisplayedReply=>reply;
  public int RoleGlyphQuads=>roleGlyphs;
  public float AngularWidth=>Mathf.Atan(Width*Scale/2/Distance)*2*Mathf.Rad2Deg;
  public float AngularHeight=>Mathf.Atan(panelHeight*Scale/Distance)*Mathf.Rad2Deg;
  public Vector3 CameraOffset=>new Vector3(0,-.14f,Distance);

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(SceneManager.GetActiveScene().name==SiCharacterBootstrap.SceneName)
    new GameObject("Conversation subtitles").AddComponent<CameraChatOverlay>();
  }
  void Awake()
  {
   font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",BodySize);
   var shader=Shader.Find("MGFR/ChatOverlay");
   textMaterial=new Material(shader);backMaterial=new Material(shader);backMaterial.mainTexture=Texture2D.whiteTexture;
   textMesh=new Mesh{name="Chat glyphs"};backMesh=new Mesh{name="Chat background"};
   textMesh.MarkDynamic();backMesh.MarkDynamic();
   backRenderer=MakeRenderer("Transcript scrim",backMesh,backMaterial,32750);
   textRenderer=MakeRenderer("Transcript text",textMesh,textMaterial,32760);
   Font.textureRebuilt+=OnFontRebuilt;
  }
  MeshRenderer MakeRenderer(string name,Mesh mesh,Material material,int order)
  {
   var child=new GameObject(name);child.transform.SetParent(transform,false);
   child.AddComponent<MeshFilter>().sharedMesh=mesh;
   var renderer=child.AddComponent<MeshRenderer>();renderer.sharedMaterial=material;renderer.sortingOrder=order;
   renderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;renderer.receiveShadows=false;return renderer;
  }
  void OnFontRebuilt(Font changed){if(changed==font)dirty=true;}
  void LateUpdate()
  {
   if(Input.GetKeyDown(KeyCode.F10)){shown=!shown;backRenderer.enabled=textRenderer.enabled=shown;}
   backMaterial.SetFloat("_OpaquePanel",MGFR.Rendering.MrMaterialPolicy.Active?1:0);
   var camera=Camera.main;
   if(camera!=null&&camera!=view){view=camera;transform.SetParent(camera.transform,false);transform.localPosition=CameraOffset;transform.localRotation=Quaternion.identity;transform.localScale=Vector3.one*Scale;dirty=true;}
   if(!preview)
   {
    if(client==null)client=FindAnyObjectByType<DialogueClient>();
    if(client!=null)
    {
     var state=client.IsSpeaking?"正在说话":client.ServerState;
     if(user!=client.LastAsrText||reply!=client.ReplyText||state!=lastState)
     {user=client.LastAsrText;reply=client.ReplyText;lastState=state;dirty=true;}
    }
   }
   if(dirty&&shown&&Time.unscaledTime>=nextRefresh){nextRefresh=Time.unscaledTime+.05f;Rebuild();}
  }
  public void ShowReview(string recognized,string response)
  {preview=true;user=recognized;reply=response;lastState="正在说话";Rebuild();}
  public void SetVisible(bool value){shown=value;backRenderer.enabled=textRenderer.enabled=value;}
  string Status()
  {
   switch(lastState){case "listening":return "正在听";case "recognizing":return "识别中";case "thinking":return "正在想";case "speaking":return "回复中";case "正在说话":return lastState;case "error":return "连接异常";default:return "等待对话";}
  }
  List<string> Wrap(string content,int limit)
  {
   var rows=new List<string>();var row=new StringBuilder();int width=0;
   foreach(char ch in content)
   {
    if(ch=='\r')continue;
    if(ch=='\n'){rows.Add(row.ToString());row.Clear();width=0;continue;}
    font.GetCharacterInfo(ch,out CharacterInfo glyph,BodySize,FontStyle.Normal);
    int advance=glyph.advance;
    if(width+advance>Width-208&&row.Length>0){rows.Add(row.ToString());row.Clear();width=0;}
    row.Append(ch);width+=advance;
   }
   if(row.Length>0)rows.Add(row.ToString());
   if(rows.Count>limit){rows=rows.GetRange(rows.Count-limit,limit);rows[0]="…"+rows[0];}
   return rows;
  }
  void Rebuild()
  {
   string own=string.IsNullOrEmpty(user)?"说句话吧，识别后会显示在这里。":user;
   string answer=string.IsNullOrEmpty(reply)?(string.IsNullOrEmpty(user)?"我在听。":"…"):reply;
   font.RequestCharactersInTexture("你：祀：…对话"+own+answer+Status(),BodySize,FontStyle.Normal);
   font.RequestCharactersInTexture("对话  ·  "+Status(),28,FontStyle.Normal);
   var userRows=Wrap(own,2);var replyRows=Wrap(answer,3);
   vertices.Clear();uv.Clear();colors.Clear();triangles.Clear();
   AddText("对话  ·  "+Status(),32,-16,28,new Color(.82f,.89f,.92f));
   float y=-62;
   roleGlyphs=AddText("你",32,y,BodySize,new Color(.78f,.9f,1));
   foreach(var row in userRows){AddText(row,128,y,BodySize,new Color(.78f,.9f,1));y-=LineStep;}
   y-=12;
   roleGlyphs+=AddText("祀",32,y,BodySize,new Color(.98f,.98f,.94f));
   foreach(var row in replyRows){AddText(row,128,y,BodySize,new Color(.98f,.98f,.94f));y-=LineStep;}
   panelHeight=-y+12;
   textMesh.Clear();textMesh.SetVertices(vertices);textMesh.SetUVs(0,uv);textMesh.SetColors(colors);textMesh.SetTriangles(triangles,0);textMesh.RecalculateBounds();
   textMaterial.mainTexture=font.material.mainTexture;
   backMesh.Clear();backMesh.vertices=new[]{new Vector3(-Width/2,0,0),new Vector3(Width/2,0,0),new Vector3(Width/2,-panelHeight,0),new Vector3(-Width/2,-panelHeight,0)};
   backMesh.uv=new[]{Vector2.zero,Vector2.right,Vector2.one,Vector2.up};backMesh.triangles=new[]{0,1,2,2,3,0};
   var shade=new Color(.025f,.034f,.043f,.89f);backMesh.colors=new[]{shade,shade,shade,shade};backMesh.RecalculateBounds();dirty=false;
  }
  int AddText(string text,float x,float y,int size,Color color)
  {
   int initialVertices=vertices.Count;
   var settings=new TextGenerationSettings{font=font,fontSize=size,fontStyle=FontStyle.Normal,color=color,lineSpacing=1,richText=false,scaleFactor=1,textAnchor=TextAnchor.UpperLeft,generationExtents=new Vector2(Width,600),pivot=new Vector2(0,1),horizontalOverflow=HorizontalWrapMode.Overflow,verticalOverflow=VerticalWrapMode.Overflow,updateBounds=true};
   generator.Populate(text,settings);var points=generator.verts;
   for(int i=0;i+3<points.Count;i+=4)
   {
    int offset=vertices.Count;
    for(int k=0;k<4;k++){var point=points[i+k];vertices.Add(new Vector3(point.position.x+x-Width/2,point.position.y+y,-1));uv.Add(point.uv0);colors.Add(point.color);}
    triangles.Add(offset);triangles.Add(offset+1);triangles.Add(offset+2);triangles.Add(offset+2);triangles.Add(offset+3);triangles.Add(offset);
   }
   return (vertices.Count-initialVertices)/4;
  }
  void OnDestroy()
  {
   Font.textureRebuilt-=OnFontRebuilt;Destroy(textMaterial);Destroy(backMaterial);Destroy(textMesh);Destroy(backMesh);Destroy(font);
  }
 }
}
