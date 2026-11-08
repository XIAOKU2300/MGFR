from pathlib import Path
import shutil,hashlib,json
lab=Path(__file__).resolve().parent
old=lab/'Project2';project=lab/'Project3';candidate=lab/'Candidate3'
assert not project.exists() and not candidate.exists()
module=Path('Assets/MGFR/RenderStyles/ZmdEndfield')
changes={}
p=module/'ZmdRenderStyle.cs';s=(old/p).read_text(encoding='utf8')
s=s.replace('Set(material,"_Mask",Existing("stylized","T_actor_jsspsi_hair_01_ST.png",true));','Set(material,"_Mask",Common("T_actor_jsspsi_hair_01_P.png",true));\n     Set(material,"_OutLineMask",Existing("stylized","T_actor_jsspsi_hair_01_ST.png",true));')
s=s.replace('Shader.SetGlobalFloat("_Global_ShadowStrength",.7f)','Shader.SetGlobalFloat("_Global_ShadowStrength",.35f)')
s=s.replace('new Color(.90f,.76f,.70f)','new Color(.94f,.83f,.78f)')
changes[p]=s
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old) in changes]
shutil.copytree(old/'Assets',project/'Assets',ignore=ignore)
shutil.copytree(old/'ProjectSettings',project/'ProjectSettings')
shutil.copytree(old/'Packages',project/'Packages')
for p,s in changes.items():
 with (project/p).open('x',encoding='utf8') as f:f.write(s)
resources=project/module/'Resources/ZmdEndfield/Data'
source=Path('H:/MGFR/【明日方舟：终末地】祀_by_茶叶味香皂_ea803c2429de15a49d2b457b9cea9738/other tex/T_actor_jsspsi_hair_01_P.png')
with (resources/'T_actor_jsspsi_hair_01_P.png.bytes').open('xb') as f:f.write(source.read_bytes())
with (resources/'.gitignore').open('x',encoding='utf8') as f:f.write('*\n!.gitignore\n')
with (lab/'hair-mask-provenance.json').open('x',encoding='utf8') as f:json.dump({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'binding':'Hair _Mask R front hair G spec B AO; ST remains outline mask'},f,indent=2,ensure_ascii=False)
shutil.copytree(project/module,candidate/module,ignore=shutil.ignore_patterns('*.meta'))
print(project)
