from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent;old=lab/'Project2';project=lab/'Project3';assert not project.exists()
p=Path('Assets/MGFR/Wardrobe/ShoeReview.cs');s=(old/p).read_text(encoding='utf8')
s=s.replace('renderer.enabled=true;Destroy(display);Destroy(snapshot);', 'renderer.enabled=true;display.SetActive(false);Destroy(display);Destroy(snapshot);')
old_check='''                report.Add(label+" "+id+" soleY="+min);
                Check(min>-.015f&&min<.025f,"foot ground gap: "+label+" "+id+" "+min);'''
new_check='''                var target=renderer.bones[side==0?7:10];
                float restAnkle=renderer.sharedMesh.bindposes[side==0?23:27].inverse.MultiplyPoint3x4(Vector3.zero).y;
                float animatedLift=renderer.transform.InverseTransformPoint(target.position).y-restAnkle;
                float contactError=min-animatedLift;
                report.Add(label+" "+id+" soleY="+min+" originalIdleFootLift="+animatedLift+" contactError="+contactError);
                Check(contactError>-.015f&&contactError<.025f,"foot contact relative to idle goal: "+label+" "+id+" "+contactError);'''
assert s.count(old_check)==1;s=s.replace(old_check,new_check)
def ignore(directory,names):return[n for n in names if (Path(directory)/n).relative_to(old)==p]
for folder in ('Assets','ProjectSettings','Packages'):shutil.copytree(old/folder,project/folder,ignore=ignore)
with (project/p).open('x',encoding='utf8') as f:f.write(s)
cache=old/'Library/PackageCache'
if cache.exists():shutil.copytree(cache,project/'Library/PackageCache')
print(project)
