using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace MGFR.GesturePanel {
 public sealed class PanelControl {
  public string key,label,detail;public bool on,disabled,toggle;public float hold;
  public Rect rect;public Transform transform;public MeshRenderer face;public PanelLabel title,caption;
 }
 public sealed class PanelLabel:MonoBehaviour {
  static Font font;static Material ink;static bool subscribed;static Shader shader;static int atlasVersion;
  static readonly HashSet<char> glyphs=new HashSet<char>();static bool glyphsChanged;
  string value="";float height=.018f,width=.3f;Color color;Mesh mesh;MeshRenderer view;bool dirty;
  static readonly List<PanelLabel> labels=new List<PanelLabel>();
  public static void Configure(Shader textShader){shader=textShader;}
  void Awake(){
   if(font==null){font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",72);ink=new Material(shader){name="Hand panel font atlas"};ink.renderQueue=3010;}
   if(!subscribed){Font.textureRebuilt+=Atlas;subscribed=true;}
   mesh=new Mesh{name="Spatial panel text"};gameObject.AddComponent<MeshFilter>().sharedMesh=mesh;view=gameObject.AddComponent<MeshRenderer>();view.sharedMaterial=ink;view.shadowCastingMode=ShadowCastingMode.Off;view.receiveShadows=false;labels.Add(this);
  }
  static void Atlas(Font changed){if(changed==font){atlasVersion++;foreach(var label in labels)if(label!=null)label.dirty=true;}}
  public void Set(string text,float h,float maxWidth,Color tint){if(value==text&&height==h&&width==maxWidth&&color==tint)return;value=text;height=h;width=maxWidth;color=tint;foreach(char ch in text)if(glyphs.Add(ch))glyphsChanged=true;dirty=true;}
  // Request the complete live vocabulary before rebuilding any UVs. A new page
  // can repack the dynamic atlas, invalidating every previously generated mesh.
  public static void FlushAll(){
   if(font==null)return;
   if(glyphsChanged){font.RequestCharactersInTexture(new string(new List<char>(glyphs).ToArray()),72,FontStyle.Normal);glyphsChanged=false;}
   for(int pass=0;pass<4;pass++){int version=atlasVersion;foreach(var label in labels)if(label!=null&&label.dirty)label.Rebuild();if(version==atlasVersion)break;}
   ink.mainTexture=font.material.mainTexture;
  }
  public void Rebuild(){
   if(mesh==null||font==null)return;int version=atlasVersion;
   var generator=new TextGenerator();var settings=new TextGenerationSettings{font=font,fontSize=72,fontStyle=FontStyle.Normal,color=color,lineSpacing=1,richText=false,scaleFactor=1,textAnchor=TextAnchor.MiddleLeft,generationExtents=new Vector2(3000,200),pivot=new Vector2(0,.5f),horizontalOverflow=HorizontalWrapMode.Overflow,verticalOverflow=VerticalWrapMode.Overflow,updateBounds=true};
   generator.Populate(value,settings);var input=generator.verts;var vertices=new List<Vector3>();var uv=new List<Vector2>();var colors=new List<Color32>();var triangles=new List<int>();float scale=height/72;
   float actual=generator.GetPreferredWidth(value,settings)*scale;if(actual>width)scale*=width/actual;
   for(int i=0;i+3<input.Count;i+=4){int first=vertices.Count;for(int k=0;k<4;k++){var v=input[i+k];vertices.Add(new Vector3(v.position.x*scale,v.position.y*scale,0));uv.Add(v.uv0);colors.Add(v.color);}triangles.AddRange(new[]{first,first+1,first+2,first+2,first+3,first});}
   mesh.Clear();mesh.SetVertices(vertices);mesh.SetUVs(0,uv);mesh.SetColors(colors);mesh.SetTriangles(triangles,0);mesh.RecalculateBounds();ink.mainTexture=font.material.mainTexture;dirty=version!=atlasVersion;
  }
  void OnDestroy(){labels.Remove(this);if(mesh!=null)Destroy(mesh);if(labels.Count==0&&font!=null){Font.textureRebuilt-=Atlas;subscribed=false;Destroy(ink);Destroy(font);ink=null;font=null;}}
 }

 public sealed class GesturePanelVisual:MonoBehaviour {
  public const float Width=.68f,Height=.48f,SurfaceZ=-.024f;
  public readonly List<PanelControl> Controls=new List<PanelControl>();
  public bool Visible=>panel!=null&&panel.gameObject.activeSelf;public bool Settled=>Visible&&reveal>=1;
  public Transform Panel=>panel;public int Page {get;private set;}
  public float Reveal=>reveal;public string FeedbackText {get;private set;}="";
  Transform panel,progressRoot,progressFill;PanelLabel feedback,progressLabel;Material surface;Shader shader;float reveal;bool closing;Vector3 finalPosition;Quaternion finalRotation;
  static readonly Color Ink=new Color(.026f,.050f,.070f),Muted=new Color(.20f,.28f,.33f),Accent=new Color(.008f,.27f,.38f);
  public void Initialize(Shader materialShader,Shader textShader){
   shader=materialShader;PanelLabel.Configure(textShader);surface=new Material(shader){name="Spatial panel ceramic"};
   panel=new GameObject("Hand-summoned touch panel").transform;panel.SetParent(transform,false);
   Box("Anodized chassis",panel,new Vector3(0,0,.006f),Width+.009f,Height+.009f,.018f,.014f,new Color(.065f,.105f,.14f));
   Box("Ceramic face",panel,Vector3.zero,Width,Height,.016f,.012f,new Color(.84f,.89f,.92f));
   Box("Inset header rule",panel,new Vector3(0,.143f,-.009f),.60f,.0011f,.001f,0,new Color(.36f,.48f,.54f));
   Text(panel,"角色控制",new Vector3(-.294f,.183f,-.012f),.029f,.46f,Ink);
   feedback=Text(panel,"握拳唤出 · 食指触控",new Vector3(-.294f,.156f,-.012f),.012f,.53f,Muted);
   progressRoot=new GameObject("Fist hold indicator").transform;progressRoot.SetParent(transform,false);
   Box("Hold track",progressRoot,Vector3.zero,.16f,.005f,.002f,.001f,new Color(.10f,.17f,.21f));
   progressFill=Box("Hold fill",progressRoot,new Vector3(-.079f,0,-.002f),.158f,.004f,.002f,.001f,new Color(.4f,.87f,.95f)).transform;
   progressLabel=Text(progressRoot,"保持握拳",new Vector3(-.079f,.017f,-.003f),.015f,.19f,Color.white);
   progressRoot.gameObject.SetActive(false);panel.gameObject.SetActive(false);
  }
  public void Show(Vector3 position,Quaternion rotation){finalPosition=position;finalRotation=rotation;panel.SetPositionAndRotation(position,rotation);panel.localScale=Vector3.one*.92f;panel.gameObject.SetActive(true);reveal=0;closing=false;SetFeedback("松开拳头后，用食指触控");}
  public void Hide(){if(Visible)closing=true;progressRoot.gameObject.SetActive(false);}
  public void SetFeedback(string text){FeedbackText=text;feedback.Set(text,.012f,.53f,Muted);}
  public void ShowProgress(Vector3 position,Quaternion rotation,float amount){
   progressRoot.gameObject.SetActive(amount>.12f&&!Visible);if(amount<=.12f||Visible)return;
   progressRoot.SetPositionAndRotation(position,rotation);progressFill.localScale=new Vector3(Mathf.Max(.002f,amount),1,1);progressFill.localPosition=new Vector3(-.079f+.079f*amount,0,-.002f);
  }
  void Update(){if(!Visible)return;float delta=Time.unscaledDeltaTime/.35f;reveal=Mathf.Clamp01(reveal+(closing?-delta:delta));float eased=1-Mathf.Pow(1-reveal,3);
   panel.SetPositionAndRotation(finalPosition-Vector3.up*(.04f*(1-eased)),finalRotation*Quaternion.Euler(-8*(1-eased),0,0));panel.localScale=Vector3.one*Mathf.Lerp(.92f,1,eased);
   if(closing&&reveal<=0)panel.gameObject.SetActive(false);
  }
  void LateUpdate(){PanelLabel.FlushAll();}
  public void SetControls(int page,List<PanelControl> controls){
   Page=page;foreach(var old in Controls)if(old.transform!=null)Destroy(old.transform.gameObject);Controls.Clear();
   foreach(var item in controls){
    var root=new GameObject("Touch control "+item.key).transform;root.SetParent(panel,false);root.localPosition=new Vector3(item.rect.center.x,item.rect.center.y,-.018f);item.transform=root;
    item.face=Box("Tactile key",root,Vector3.zero,item.rect.width,item.rect.height,.012f,.004f,BaseColor(item)).GetComponent<MeshRenderer>();
    float labelY=string.IsNullOrEmpty(item.detail)?0:.010f;float fontSize=item.rect.height>.05f?.020f:.016f;
    item.title=Text(root,item.label,new Vector3(-item.rect.width*.5f+.015f,labelY,-.007f),fontSize,item.rect.width-.035f,TextColor(item));
    if(!string.IsNullOrEmpty(item.detail))item.caption=Text(root,item.detail,new Vector3(-item.rect.width*.5f+.015f,-.017f,-.0072f),.0125f,item.rect.width-.035f,item.disabled?new Color(.34f,.40f,.43f):Muted);
    if(item.toggle){var tint=item.on?Accent:new Color(.43f,.51f,.55f);Box("Switch state",root,new Vector3(item.rect.width*.5f-.025f,.017f,-.0075f),.012f,.004f,.001f,.001f,tint);}
    Controls.Add(item);
   }
   PanelLabel.FlushAll();
  }
  static Color BaseColor(PanelControl item)=>item.disabled?new Color(.74f,.79f,.82f):item.on?new Color(.65f,.84f,.88f):new Color(.94f,.96f,.97f);
  static Color TextColor(PanelControl item)=>item.disabled?new Color(.32f,.39f,.43f):Ink;
  public int Hit(Vector2 point){for(int i=0;i<Controls.Count;i++){var c=Controls[i];if(!c.disabled&&c.rect.Contains(point))return i;}return -1;}
  public void PresentTouch(int hovered,float compression){foreach(var item in Controls){bool selected=hovered>=0&&hovered<Controls.Count&&Controls[hovered]==item;var position=item.transform.localPosition;position.z=Mathf.Lerp(position.z,-.018f+(selected?.005f*compression:0),1-Mathf.Exp(-Time.unscaledDeltaTime*35));item.transform.localPosition=position;item.face.sharedMaterial.SetColor("_Color",selected?Color.Lerp(BaseColor(item),new Color(.48f,.76f,.83f),.35f+.25f*compression):BaseColor(item));}}
  public void ForceSettleForReview(){reveal=1;closing=false;panel.SetPositionAndRotation(finalPosition,finalRotation);panel.localScale=Vector3.one;}
  PanelLabel Text(Transform parent,string value,Vector3 position,float height,float width,Color tint){var go=new GameObject("Panel label");go.transform.SetParent(parent,false);go.transform.localPosition=position;var text=go.AddComponent<PanelLabel>();text.Set(value,height,width,tint);return text;}
  GameObject Box(string name,Transform parent,Vector3 position,float width,float height,float depth,float chamfer,Color tint){
   var go=new GameObject(name);go.transform.SetParent(parent,false);go.transform.localPosition=position;var mesh=Chamfered(width,height,depth,chamfer);go.AddComponent<MeshFilter>().sharedMesh=mesh;var renderer=go.AddComponent<MeshRenderer>();renderer.sharedMaterial=new Material(surface){name=name};renderer.sharedMaterial.SetColor("_Color",tint);renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=false;go.AddComponent<PanelOwnedGeometry>();return go;
  }
  public static Mesh Chamfered(float width,float height,float depth,float cut){
   float x=width*.5f,y=height*.5f,c=Mathf.Min(cut,Mathf.Min(x,y)*.4f);var outline=new[]{new Vector2(-x+c,-y),new Vector2(x-c,-y),new Vector2(x,-y+c),new Vector2(x,y-c),new Vector2(x-c,y),new Vector2(-x+c,y),new Vector2(-x,y-c),new Vector2(-x,-y+c)};
   var positions=new List<Vector3>();var indices=new List<int>();
   void Triangle(Vector3 a,Vector3 b,Vector3 d){int i=positions.Count;positions.Add(a);positions.Add(b);positions.Add(d);indices.Add(i);indices.Add(i+1);indices.Add(i+2);}
   for(int i=0;i<8;i++){int n=(i+1)%8;var a=new Vector3(outline[i].x,outline[i].y,-depth*.5f);var b=new Vector3(outline[n].x,outline[n].y,-depth*.5f);var d=a+Vector3.forward*depth;var e=b+Vector3.forward*depth;Triangle(new Vector3(0,0,-depth*.5f),b,a);Triangle(new Vector3(0,0,depth*.5f),d,e);Triangle(a,b,e);Triangle(e,d,a);}
   var mesh=new Mesh{name="Chamfered spatial control"};mesh.SetVertices(positions);mesh.SetTriangles(indices,0);mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;
  }
  void OnDestroy(){if(panel!=null)Destroy(panel.gameObject);if(progressRoot!=null)Destroy(progressRoot.gameObject);if(surface!=null)Destroy(surface);}
 }
 public sealed class PanelOwnedGeometry:MonoBehaviour {void OnDestroy(){var filter=GetComponent<MeshFilter>();if(filter!=null&&filter.sharedMesh!=null)Destroy(filter.sharedMesh);var renderer=GetComponent<MeshRenderer>();if(renderer!=null&&renderer.sharedMaterial!=null)Destroy(renderer.sharedMaterial);}}
}
