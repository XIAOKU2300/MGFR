from pathlib import Path
import shutil
lab=Path('H:/MGFR/HandLab-20261018');old=lab/'Project-v7';project=lab/'Project-v8';source=lab/'Sources/v8';source.mkdir()
path=Path('Assets/MGFR/Scripts/BareHands/HandPoseStabilizer.cs');text=(old/path).read_text(encoding='utf8')
text=text.replace('readonly float[] length=new float[26];','readonly float[] length=new float[26],radii=new float[26];\n  public const float SizeGain=1.05f;')
text=text.replace('if(observed)result.Radius[i]=raw.Radius[i];','if(observed)radii[i]=raw.Radius[i];\n    result.Radius[i]=radii[i]*SizeGain;')
text=text.replace('   result.Tracked=', '   var anchor=result.Joints[1].position;\n   for(int i=0;i<26;i++)if(result.Valid[i])result.Joints[i].position=anchor+(result.Joints[i].position-anchor)*SizeGain;\n   result.Tracked=')
changes={path:text}
path=Path('Assets/MGFR/Scripts/BareHands/HandDepthMesh.cs');changes[path]=(old/path).read_text(encoding='utf8').replace(')*1.08f;',')*1.04f;')
path=Path('Assets/MGFR/Editor/StabilizedHandsBuild.cs');text=(old/path).read_text(encoding='utf8')
text=text.replace('   Debug.Log($"[MGFR hand stability checks]', '''   filter.Reset();var curled=Raw(Vector3.zero);
   for(int i=8;i<=10;i++){curled.Joints[i].position=curled.Joints[i-1].position+Quaternion.Euler(75,0,0)*Vector3.up*.025f;curled.Joints[i].rotation=Quaternion.Euler(75,0,0);}
   for(int frame=0;frame<36;frame++){filter.Process(curled,output,t+.3+frame/72d);}
   if(Vector3.Distance(output.Joints[10].position,curled.Joints[10].position*HandPoseStabilizer.SizeGain)>.008f)throw new Exception("Curled finger did not follow");
   Debug.Log($"[MGFR hand stability checks]''')
text=text.replace('boneLengthStable=True','boneLengthStable=True curledFingerFollows=True sizeGain=1.05');changes[path]=text
names={p.name for p in changes}
def ignore(path,items):return [n for n in items if n in names]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for relative,text in changes.items():
    with (source/relative.name).open('x',encoding='utf8') as file:file.write(text)
    with (project/relative).open('x',encoding='utf8') as file:file.write(text)
print(project)
