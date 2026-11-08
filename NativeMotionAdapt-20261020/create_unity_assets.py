from pathlib import Path
import subprocess
import json
ROOT=Path(__file__).resolve().parent
project=ROOT/'UnityAssets-v1'
project.mkdir(exist_ok=False)
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(text)
write(project/'Packages/manifest.json',json.dumps({'dependencies':{'com.unity.modules.animation':'1.0.0','com.unity.modules.jsonserialize':'1.0.0'}}))
write(project/'ProjectSettings/ProjectVersion.txt','m_EditorVersion: 6000.3.26f1\n')
code=r'''using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
[Serializable]public class NativeAssetBone {public string name;public int parent;}
[Serializable]public class NativeAssetModel {public NativeAssetBone[] bones;}
public static class NativeAssetExporter {
 public static void Export(){
  string root=Directory.GetParent(Application.dataPath).Parent.FullName;
  string modelPath=Path.Combine(root,"../converted/si/si_model.json");
  var model=JsonUtility.FromJson<NativeAssetModel>(File.ReadAllText(modelPath));var names=new string[model.bones.Length];var used=new HashSet<string>();
  for(int i=0;i<names.Length;i++){names[i]=model.bones[i].name;if(!used.Add(names[i]))names[i]+="_"+i;}
  string[] properties={"localPosition.x","localPosition.y","localPosition.z","localRotation.x","localRotation.y","localRotation.z","localRotation.w"};int total=0;
  foreach(string skin in new[]{"swimsuit","original"}){
   Directory.CreateDirectory(Path.Combine(Application.dataPath,"NativeClips",skin));AssetDatabase.Refresh();
   foreach(string file in Directory.GetFiles(Path.Combine(root,"bake-all-v1/Baked",skin),"*.hpose"))using(var r=new BinaryReader(File.OpenRead(file))){
    if(r.ReadInt32()!=0x45535048)throw new Exception("Pose format");int count=r.ReadInt32(),frames=r.ReadInt32();float fps=r.ReadSingle();var ids=new int[count];for(int i=0;i<count;i++)ids[i]=r.ReadInt32();var values=new float[count,7,frames];
    for(int f=0;f<frames;f++)for(int i=0;i<count;i++)for(int c=0;c<7;c++)values[i,c,f]=r.ReadSingle();
    string name=Path.GetFileNameWithoutExtension(file),asset="Assets/NativeClips/"+skin+"/"+name+".anim";if(File.Exists(Path.Combine(Directory.GetParent(Application.dataPath).FullName,asset)))throw new Exception("Existing asset refused");
    var clip=new AnimationClip{name=name,legacy=true,frameRate=fps,wrapMode=name=="idle"?WrapMode.Loop:WrapMode.ClampForever};
    for(int i=0;i<count;i++){
     int id=ids[i];string path=names[id];for(int p=model.bones[id].parent;p>=0;p=model.bones[p].parent)path=names[p]+"/"+path;path="Bones/"+path;
     for(int f=1;f<frames;f++){float dot=0;for(int c=3;c<7;c++)dot+=values[i,c,f]*values[i,c,f-1];if(dot<0)for(int c=3;c<7;c++)values[i,c,f]=-values[i,c,f];}
     for(int c=0;c<7;c++){bool constant=true;for(int f=1;f<frames;f++)if(Mathf.Abs(values[i,c,f]-values[i,c,0])>.000001f){constant=false;break;}
      var keys=new Keyframe[constant?2:frames];for(int k=0;k<keys.Length;k++){int f=constant?k*(frames-1):k;float tangent=constant?0:(values[i,c,Mathf.Min(f+1,frames-1)]-values[i,c,Mathf.Max(f-1,0)])*fps/(f==0||f==frames-1?1:2);keys[k]=new Keyframe(f/fps,values[i,c,f],tangent,tangent);}clip.SetCurve(path,typeof(Transform),properties[c],new AnimationCurve(keys));
     }
    }
    clip.EnsureQuaternionContinuity();AssetDatabase.CreateAsset(clip,asset);total++;
   }
  }
  AssetDatabase.SaveAssets();Debug.Log("NATIVE_UNITY_ASSETS_EXPORTED count="+total);
  string report=Path.Combine(root,"UnityAssets-v1/asset-export.txt");using(var w=new StreamWriter(new FileStream(report,FileMode.CreateNew)))w.WriteLine("Standard Unity AnimationClip assets: "+total+"; two skin reference poses; 58 body/finger/deformation bones.");
 }
}
'''
write(project/'Assets/Editor/NativeAssetExporter.cs',code)
log=project/'export.log'
args=[str(ROOT.parent/'Editor/Unity.exe'),'-batchmode','-nographics','-projectPath',str(project),'-executeMethod','NativeAssetExporter.Export','-quit','-logFile',str(log)]
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
child=subprocess.Popen(args,startupinfo=startup)
try:code=child.wait(timeout=180)
except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned Unity asset export timed out') from None
print('UNITY_ASSET_EXPORT_EXIT',code,flush=True)
if (project/'asset-export.txt').exists():print((project/'asset-export.txt').read_text(encoding='utf-8-sig'))
else:print(log.read_text(encoding='utf-8-sig',errors='replace')[-5000:])
