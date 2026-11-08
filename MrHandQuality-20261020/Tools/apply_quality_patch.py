from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]/'Project/Assets/MGFR'
def edit(rel, fn):
    p=ROOT/rel
    before=p.read_text(encoding='utf-8-sig');after=fn(before)
    if after==before:raise RuntimeError('No change: '+rel)
    p.write_text(after,encoding='utf-8')
def replace(text,old,new):
    if old not in text:raise RuntimeError('Expected source not found: '+old[:95])
    return text.replace(old,new)

def guard(t):
    t=replace(t,'(F10 compare)','(Ctrl+Shift+F7 compare)')
    t=replace(t,'if (Input.GetKeyDown(KeyCode.F10))','if ((Input.GetKey(KeyCode.LeftControl)||Input.GetKey(KeyCode.RightControl)) && (Input.GetKey(KeyCode.LeftShift)||Input.GetKey(KeyCode.RightShift)) && Input.GetKeyDown(KeyCode.F7))')
    t=replace(t,'void OnEnable() { Camera.onPreCull += BeforeCamera; }','void OnEnable() { Requested = !Has("-mgfr-mr-original"); Camera.onPreCull += BeforeCamera; }')
    t=replace(t,'F10 compares original.','Ctrl+Shift+F7 compares desktop materials and AA.')
    t=replace(t,'if (!apply) return;','MrMaterialPolicy.SetActive(apply);\n            if (!apply) return;')
    t=replace(t,'if (!Applied) return;','MrMaterialPolicy.SetActive(false);\n            if (!Applied) return;')
    return t
edit('Scripts/Rendering/MrChromaEdgeGuard.cs',guard)
edit('Scripts/Character/SiCharacterLoader.cs',lambda t:replace(t,'materials[i] = material;','MGFR.Rendering.MrMaterialPolicy.Register(material, i);\n                materials[i] = material;'))
edit('RenderStyles/ZmdEndfield/ZmdRenderStyle.cs',lambda t:replace(t,'Set(material,"_AlphaClip",index==10?.001f:0);','MrMaterialPolicy.InheritDesktop(material, original);\n    Set(material,"_AlphaClip",index==10?.001f:0);').replace('ZmdMaterials[index]=material;','MrMaterialPolicy.Register(material,index);ZmdMaterials[index]=material;'))
edit('Skins/ZmdSkinBinding.cs',lambda t:replace(t,'material.renderQueue = source.renderQueue;','material.renderQueue = source.renderQueue;\n                        MGFR.Rendering.MrMaterialPolicy.InheritDesktop(material, source);').replace('skinVariants.Add(appearance, variant);','MGFR.Rendering.MrMaterialPolicy.RegisterArray(variant.current);\n                MGFR.Rendering.MrMaterialPolicy.RegisterArray(variant.zmd);\n                skinVariants.Add(appearance, variant);'))
edit('Scripts/Dialogue/CameraChatOverlay.cs',lambda t:replace(t,'var camera=Camera.main;','backMaterial.SetFloat("_OpaquePanel",MGFR.Rendering.MrMaterialPolicy.Active?1:0);\n   var camera=Camera.main;'))
edit('Shaders/ChatOverlay.shader',lambda t:replace(t,'Properties {','Properties { _OpaquePanel("MR opaque background",Float)=0 ').replace('sampler2D _MainTex;','sampler2D _MainTex;float _OpaquePanel;').replace('return color;','color.a=lerp(color.a,1,_OpaquePanel);return color;'))

def source(t):
    t=replace(t,'public readonly bool[] Observed=new bool[26];public int ObservedCount;','public readonly bool[] Observed=new bool[26];public int ObservedCount;\n  public readonly float[] LastValidTime=new float[26];\n  public readonly JointSampleSource[] JointSource=new JointSampleSource[26];\n  public readonly JointRadiusSource[] RadiusSource=new JointRadiusSource[26];\n  public int UnityFrame; public double ReceivedAt; public string UpdatePhase="unknown";')
    t=replace(t,'Array.Clear(Observed,0,26);','Array.Clear(Observed,0,26);Array.Clear(JointSource,0,26);Array.Clear(LastValidTime,0,26);Array.Clear(RadiusSource,0,26);')
    t=replace(t,'static void CopyFrame','public static void CopyFrame')
    t=replace(t,'Array.Copy(from.Valid,to.Valid,26);','Array.Copy(from.LastValidTime,to.LastValidTime,26);Array.Copy(from.JointSource,to.JointSource,26);Array.Copy(from.RadiusSource,to.RadiusSource,26);\n   to.UnityFrame=from.UnityFrame;to.ReceivedAt=from.ReceivedAt;to.UpdatePhase=from.UpdatePhase;\n   Array.Copy(from.Valid,to.Valid,26);')
    t=replace(t,'readonly HandFrame raw=new HandFrame();','readonly HandFrame raw=new HandFrame();\n  readonly HandSampleQuality[] quality={new HandSampleQuality(),new HandSampleQuality()};\n  public readonly float[] LastBeforeRender={-100,-100};\n  readonly HandFrame diagnosticRaw=new HandFrame();\n  HandTrackingDiagnostics diagnostics;\n  public int RejectedJoints=>quality[0].Rejected+quality[1].Rejected;\n  public int Relocations=>quality[0].Relocations+quality[1].Relocations;')
    t=replace(t,'void Start(){origin=Camera.main.transform.parent;}','void Start(){origin=Camera.main!=null?Camera.main.transform.parent:null;diagnostics=gameObject.AddComponent<HandTrackingDiagnostics>();}\n  public void InvalidateHand(int h) {NativeFrames[h].Clear();RenderFrames[h].Clear();filters[h].Reset();quality[h].Reset();if(!controllerPose[h])Frames[h].Clear();}\n  public void ExpireRender(float now) {for(int h=0;h<2;h++)if(now-RenderFrames[h].Timestamp>.06f)RenderFrames[h].Clear();}')
    t=replace(t,'{NativeFrames[h].Clear();filters[h].Reset();if(!controllerPose[h])Frames[h].Clear();}','{InvalidateHand(h);}')
    t=replace(t,'RenderFrames[h].Timestamp>.1f','RenderFrames[h].Timestamp>.06f')
    t=replace(t,'f.Clear();RenderFrames[h].Clear();filters[h].Reset();if(!controllerPose[h])Frames[h].Clear();return;','InvalidateHand(h);return;')
    t=replace(t,'if(!updated){MissingUpdates++;return;}','if(!updated){MissingUpdates++;if(type==XRHandSubsystem.UpdateType.BeforeRender)RenderFrames[h].Clear();return;}')
    t=replace(t,'raw.Radius[i]=joint.TryGetRadius(out float r)&&r>0&&float.IsFinite(r)?Mathf.Clamp(r,.004f,.025f):0;','bool measured=joint.TryGetRadius(out float r)&&float.IsFinite(r)&&r>=.002f&&r<=.03f;\n    raw.Radius[i]=measured?r:0;raw.RadiusSource[i]=measured?JointRadiusSource.Device:JointRadiusSource.Unknown;')
    t=replace(t,'raw.Radius[i]=Mathf.Clamp(width*(i<2?.24f:i==5||i==10||i==15||i==20||i==25?.10f:.135f),.004f,.025f);','{raw.Radius[i]=Mathf.Clamp(width*(i<2?.24f:i==5||i==10||i==15||i==20||i==25?.10f:.135f),.004f,.025f);raw.RadiusSource[i]=JointRadiusSource.PalmEstimate;}')
    t=replace(t,'if(type==XRHandSubsystem.UpdateType.Dynamic)\n   {filters[h].Process','sample.ReceivedAt=now;sample.UnityFrame=Time.frameCount;sample.UpdatePhase=type.ToString();\n   if(diagnostics!=null&&diagnostics.Capturing)CopyFrame(sample,diagnosticRaw);\n   if(quality[h].Filter(sample)){filters[h].Reset();NativeFrames[h].Clear();if(!controllerPose[h])Frames[h].Clear();RenderFrames[h].Clear();return;}\n   if(type==XRHandSubsystem.UpdateType.BeforeRender)LastBeforeRender[h]=sample.Timestamp;\n   if(type==XRHandSubsystem.UpdateType.Dynamic)\n   {filters[h].Process')
    t=replace(t,'UpdateRenderFrame(h,sample,NativeFrames[h]);','UpdateRenderFrame(h,sample,NativeFrames[h]);\n   if(diagnostics!=null&&diagnostics.Capturing)diagnostics.Capture(h,diagnosticRaw,NativeFrames[h],RenderFrames[h]);')
    start=t.index('   var wrist=observed.Joints[1];var inverse=Quaternion.Inverse(stable.Joints[1].rotation);')
    end=t.index('\n  public void PublishControllerFrame',start)
    t=t[:start]+'''   target.ReceivedAt=observed.ReceivedAt;target.UnityFrame=observed.UnityFrame;target.UpdatePhase=observed.UpdatePhase;
   for(int i=0;i<26;i++)if(observed.Valid[i])
   {
    target.Joints[i]=observed.Joints[i];target.Radius[i]=observed.Radius[i];target.Valid[i]=target.Observed[i]=true;
    target.LastValidTime[i]=observed.LastValidTime[i];target.JointSource[i]=observed.JointSource[i];target.RadiusSource[i]=observed.RadiusSource[i];
    target.ValidCount++;target.ObservedCount++;
   }
   // Never reconstruct a missing visual tip from a filtered physics pose.
   target.Tracked=target.ValidCount>=8&&target.Valid[1];
  }
'''+t[end:]
    return t
edit('Scripts/BareHands/HandJointSource.cs',source)
edit('Scripts/BareHands/HandPoseStabilizer.cs',lambda t:replace(t,'result.Radius[i]=radii[i]*SizeGain;','result.Radius[i]=radii[i]*SizeGain;\n    result.LastValidTime[i]=(float)lastSeen[i];result.JointSource[i]=observed?JointSampleSource.SDK:JointSampleSource.Held;\n    result.RadiusSource[i]=raw.RadiusSource[i];').replace('result.Clear();result.Timestamp=raw.Timestamp;','result.Clear();result.Timestamp=raw.Timestamp;result.ReceivedAt=raw.ReceivedAt;result.UnityFrame=raw.UnityFrame;result.UpdatePhase=raw.UpdatePhase;'))

def interaction(t):
    t=replace(t,'Source.BeforeRenderData+=RefreshDepth;','Source.BeforeRenderData+=RefreshDepth;\n   Application.onBeforeRender+=RefreshDepth;')
    t=replace(t,'void RefreshDepth()','[BeforeRenderOrder(20000)]\n  void RefreshDepth()')
    t=replace(t,'for(int h=0;h<2;h++)DepthMeshes[h].Update(Source.RenderFrames[h],OcclusionEnabled);','if(!Source.Replay)Source.ExpireRender(Time.unscaledTime);\n   for(int h=0;h<2;h++)DepthMeshes[h].Update(Source.RenderFrames[h],OcclusionEnabled);')
    t=replace(t,'if(Source!=null)Source.BeforeRenderData-=RefreshDepth;','Application.onBeforeRender-=RefreshDepth;\n   if(Source!=null)Source.BeforeRenderData-=RefreshDepth;')
    return t
edit('Scripts/BareHands/BareHandInteraction.cs',interaction)
edit('Scripts/XrDeviceFollower.cs',lambda t:replace(t,'void BeforeRender()','[BeforeRenderOrder(-20000)]\n        void BeforeRender()'))

def depth(t):
    t=replace(t,'readonly HandOcclusionEnvelope envelope;','readonly HandOcclusionEnvelope envelope; readonly int handIndex;\n  readonly HandFrame calibrated=new HandFrame();\n  public float LastRenderMilliseconds {get;private set;}')
    t=replace(t,'Object=UnityEngine.Object.Instantiate','handIndex=hand;\n   Object=UnityEngine.Object.Instantiate')
    t=replace(t,'envelope=new HandOcclusionEnvelope(material);','envelope=new HandOcclusionEnvelope(material,hand);\n   AnatomicalOcclusion=Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-hand-skeleton")<0;')
    t=replace(t,'bool active=show&&f.Tracked;if(Object.activeSelf!=active)Object.SetActive(active);','var started=System.Diagnostics.Stopwatch.GetTimestamp();\n   HandVisualCalibration.Apply(handIndex,f,calibrated);f=calibrated;\n   bool active=show&&f.Tracked;if(Object.activeSelf!=active)Object.SetActive(active);')
    t=replace(t,'Renderer.enabled=!AnatomicalOcclusion;','LastRenderMilliseconds=(float)((System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000.0/System.Diagnostics.Stopwatch.Frequency);\n   Renderer.enabled=!AnatomicalOcclusion&&f.ValidCount==26;')
    return t
edit('Scripts/BareHands/HandDepthMesh.cs',depth)

def envelope(t):
    t=replace(t,'public HandOcclusionEnvelope(Material material)','readonly int handIndex;\n  readonly bool legacy=System.Array.IndexOf(System.Environment.GetCommandLineArgs(),"-mgfr-hand-envelope-original")>=0;\n  public HandOcclusionEnvelope(Material material,int hand=0)')
    t=replace(t,'Object=new GameObject','handIndex=hand;\n   Object=new GameObject')
    t=replace(t,'bool active=show&&f.Tracked&&f.Valid[1]&&f.Valid[7]&&f.Valid[12]&&f.Valid[17]&&f.Valid[22];','bool active=show&&f.Tracked&&f.Valid[1];')
    t=replace(t,'float axial=first?-Mathf.Cos(angle)*ra:Mathf.Sin(angle)*rb;','bool tip=b==5||b==10||b==15||b==20||b==25;\n     float extension=legacy?rb:tip?Mathf.Min(rb*.25f,.002f)*HandVisualCalibration.Settings(handIndex).tipLength[HandVisualCalibration.Finger(b)]:rb*.45f;\n     float axial=first?-Mathf.Cos(angle)*(legacy?ra:ra*.45f):Mathf.Sin(angle)*extension;')
    t=replace(t,'float radial=first?Mathf.Sin(angle)*ra:Mathf.Cos(angle)*rb;','float radial=first?Mathf.Sin(angle)*ra:Mathf.Cos(angle)*(legacy?rb:Mathf.Min(rb,ra*.94f));')
    t=replace(t,'var wrist=f.Joints[1].position;var left=f.Joints[7].position;var right=f.Joints[22].position;','if(!f.Valid[0]||!f.Valid[7]||!f.Valid[12]||!f.Valid[17]||!f.Valid[22])\n   {for(int k=Segments*SegmentVertices;k<vertices.Length;k++)vertices[k]=f.Joints[1].position;Mesh.vertices=vertices;Mesh.RecalculateBounds();return;}\n   var wrist=f.Joints[1].position;var left=f.Joints[7].position;var right=f.Joints[22].position;')
    t=replace(t,'float halfThickness=Mathf.Clamp(radii[0]*.65f,.008f,.020f);','var calibration=HandVisualCalibration.Settings(handIndex);\n   float halfThickness=Mathf.Clamp(radii[0]*.65f,.008f,.020f)*calibration.palmThickness;')
    t=replace(t,'Vector3 centerPalm=Vector3.zero;int start=Segments*SegmentVertices;','var midpoint=(left+right)*.5f;\n   for(int k=0;k<6;k++){var d=outline[k]-midpoint;outline[k]+=across*Vector3.Dot(d,across)*(calibration.palmWidth-1);}\n   Vector3 centerPalm=Vector3.zero;int start=Segments*SegmentVertices;')
    return t
edit('Scripts/BareHands/HandOcclusionEnvelope.cs',envelope)

# Same coverage threshold in forward color, outlines and shadow/depth passes.
props='\n        _MrCoverage("MR semantic coverage",Float)=0\n        _MrCutoff("MR cutout threshold",Range(0,1))=0.18\n'
for rel,anchor,expr in [
 ('Shaders/MgfrCharacter.shader','fixed4 c = tex * _Color;','c.a'),
 ('Resources/MgfrStylized.shader','float4 tex=tex2D(_MainTex,i.uv);float4 base=tex*_Color;','base.a'),
 ('Resources/MgfrEndfieldClothing.shader','float4 base=tex2D(_MainTex,i.uv)*_Color;','base.a')]:
 def shader(t,anchor=anchor,expr=expr):
  t=re.sub(r'(Properties\s*\{)',lambda m:m[1]+props,t,count=1)
  t=t.replace('#include "UnityCG.cginc"','#include "UnityCG.cginc"\n   float _MrCoverage,_MrCutoff;')
  t=replace(t,anchor,anchor+'\n    if(_MrCoverage>.5){clip('+expr+'-_MrCutoff);'+expr+'=1;}')
  t=t.replace('clip(alpha-.55);','clip(alpha-(_MrCoverage>.5?_MrCutoff:.55));')
  return t
 edit(rel,shader)
for name in ['ZmdHair','ZmdCloth','ZmdSkin','ZmdFace']:
 rel='RenderStyles/ZmdEndfield/Resources/ZmdEndfield/'+name+'.shader'
 def shader(t,name=name):
  t=re.sub(r'(Properties\s*\{)',lambda m:m[1]+props,t,count=1)
  # shared include declares the coverage uniforms for every pass.
  if name in ['ZmdHair','ZmdCloth']:
   t=replace(t,'clip(alpha - _AlphaClip);','clip(alpha - _AlphaClip);\n                if(_MrCoverage>.5){clip(alpha-_MrCutoff);alpha=1;}')
  return t
 edit(rel,shader)
edit('RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdCharUtils.cginc',lambda t:replace(t,'#include "ZmdBuiltInCompat.cginc"','#include "ZmdBuiltInCompat.cginc"\nfloat _MrCoverage,_MrCutoff;').replace('clip(alpha - _AlphaClip);','clip(alpha - (_MrCoverage>.5?_MrCutoff:_AlphaClip));'))
print('Applied bounded source patch')
