from pathlib import Path
import hashlib,json,shutil
from PIL import Image,ImageDraw,ImageFont
root=Path('H:/MGFR');lab=root/'RenderLab-20261018';project=lab/'Project-v7';main=root/'unity-client'
report=(lab/'PhysicsReview-v7/physics-report.txt').read_text(encoding='utf-8-sig')
assert 'pass=True' in report
relative=[]
folder='Assets/MGFR/Scripts/PhysicsRig'
relative += [str(p.relative_to(project)).replace('\\','/') for p in (project/folder).iterdir()]
relative += [folder+'.meta']
folder='Assets/StreamingAssets/physics'
relative += [str(p.relative_to(project)).replace('\\','/') for p in (project/folder).iterdir()]
relative += [folder+'.meta']
pairs=[(project/p,main/p) for p in relative]
assert all(not dst.exists() for _,dst in pairs),'Refuse existing source overwrite'
manifest=[]
for src,dst in pairs:
 dst.parent.mkdir(parents=True,exist_ok=True)
 with src.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
 digest=hashlib.sha256(src.read_bytes()).hexdigest();assert digest==hashlib.sha256(dst.read_bytes()).hexdigest()
 manifest.append(dict(path=str(dst),sha256=digest))
with (main/'Assets/StreamingAssets/physics/.gitignore').open('x',encoding='utf8') as f:f.write('# Local data derived from the supplied PMX.\n*.json\n*.json.meta\n')
receipt=json.loads((root/'VRFIX-APPLIED-20261018.json').read_text(encoding='utf-8-sig'))
for item in receipt['files']:
 assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['afterSha256']
assert hashlib.sha256((main/'Assets/MGFR/Scripts/Character/SiCharacterLoader.cs').read_bytes()).hexdigest()=='55cb0bf284fa0929e452bedc697347a9409758667574d88c45c2c130e7ac913a'
for folder in ('Assets/MGFR/Resources','Assets/MGFR/Scripts/Rendering','Assets/MGFR/Scripts/PhysicsRig'):
 for p in (main/folder).iterdir():
  if p.suffix in ('.cs','.shader'):
   assert p.read_bytes()==(project/p.relative_to(main)).read_bytes(),str(p)
with (lab/'physics-applied.json').open('x',encoding='utf8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
for desktop in (False,True):
 name='启动MGFR渲染物理版'+('（桌面）' if desktop else '')+'.cmd'
 command='@echo off\r\nstart "" "H:\\MGFR\\RenderLab-20261018\\Project-v7\\Build\\Windows\\MGFR.exe"'+(' -mgfr-noxr' if desktop else '')+'\r\n'
 with (root/name).open('x',encoding='gbk',newline='') as f:f.write(command)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
board=Image.new('RGB',(1440,930),(30,34,39));draw=ImageDraw.Draw(board)
for index,frame in enumerate((90,210)):
 image=Image.open(lab/'PhysicsReview-v7'/f'physics-{frame:03d}.png').convert('RGB').resize((720,880))
 board.paste(image,(720*index,50));draw.text((24+index*720,10),('运动过程：正面','运动过程：后侧衣料')[index],font=font,fill='white')
board.save(lab/'完整物理-前后视图.png')
validation=dict(source_matches_final_build=True,previous_vr_and_transparency_fixes_unchanged=True,
 render_review='18 real-model same-pose old/new views, front/back/face/cloth/three lighting directions',
 physics_report=report,shader_review='Stereo instance setup and per-eye view vector; transparent skirt retains queue 3000 and ZWrite 0',
 limits='Desktop validation only; no new headset or XR GPU timing. Studio environment is an approximation, not room GI or original-game self-shadow.')
with (lab/'final-validation.json').open('x',encoding='utf8') as f:json.dump(validation,f,ensure_ascii=False,indent=2)
print('Added physics sources:',len(manifest),'files. Existing VR/cloth fixes unchanged. Final build matches main sources.')
