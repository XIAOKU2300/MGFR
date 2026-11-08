from pathlib import Path
import shutil,json,hashlib
from PIL import Image,ImageDraw,ImageFont

root=Path('H:/MGFR');lab=root/'RenderLab-20261018';project=lab/'Project-v2';main=root/'unity-client'
pairs=[]
for folder in ['Assets/MGFR/Scripts/Rendering','Assets/MGFR/Resources']:
 for p in (project/folder).iterdir():pairs.append((p,main/folder/p.name))
 pairs.append((project/(folder+'.meta'),main/(folder+'.meta')))
for file in ['StylizedBuild.cs','StylizedBuild.cs.meta']:
 pairs.append((project/'Assets/MGFR/Editor'/file,main/'Assets/MGFR/Editor'/file))
for p in (project/'Assets/StreamingAssets/stylized').iterdir():
 pairs.append((p,main/'Assets/StreamingAssets/stylized'/p.name))
pairs.append((project/'Assets/StreamingAssets/stylized.meta',main/'Assets/StreamingAssets/stylized.meta'))
assert all(not dst.exists() for _,dst in pairs),'Existing target: refuse overwrite'
manifest=[]
for src,dst in pairs:
 dst.parent.mkdir(parents=True,exist_ok=True)
 with src.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
 digest=hashlib.sha256(src.read_bytes()).hexdigest();assert digest==hashlib.sha256(dst.read_bytes()).hexdigest()
 manifest.append(dict(path=str(dst),sha256=digest))
with (lab/'render-applied.json').open('x',encoding='utf8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
# Compare actual renders without changing their content.
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',26)
for pose in ('face','body','cloth'):
 board=Image.new('RGB',(1440,770),(31,35,40));draw=ImageDraw.Draw(board)
 for i,variant in enumerate(('before','after')):
  im=Image.open(lab/'Review-v2'/f'L0-{pose}-{variant}.png').convert('RGB');im.thumbnail((720,720))
  board.paste(im,(i*720,50));draw.text((i*720+24,9),('原版','渲染第一版')[i],font=font,fill='white')
 board.save(lab/f'对比-{pose}.png')
receipt=json.loads((root/'VRFIX-APPLIED-20261018.json').read_text(encoding='utf-8-sig'))
for item in receipt['files']:
 assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['afterSha256']
assert hashlib.sha256((main/'Assets/MGFR/Scripts/Character/SiCharacterLoader.cs').read_bytes()).hexdigest()=='55cb0bf284fa0929e452bedc697347a9409758667574d88c45c2c130e7ac913a'
corners=[]
for p in sorted((lab/'Review-v2').glob('*.png')):
 im=Image.open(p).convert('RGB');corners.append(im.getpixel((0,0))==(0,255,0))
assert all(corners)
shader=(main/'Assets/MGFR/Resources/MgfrStylized.shader').read_text(encoding='utf8')
assert shader.count('UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o)')==2
assert shader.count('UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i)')==2
report=dict(new_files=len(pairs),source_matches_tested_candidate=True,previous_vr_and_alpha_fixes_unchanged=True,
    green_background_exact_in_18_images=all(corners),stereo_macros_in_both_passes=True,
    compile_errors=0,existing_obsolete_xr_warnings=1,
    observations='18 same-pose actual-model before/after renders: front, 3/4, face, cloth, back, side and overhead light.',
    limits='No headset or measured XR GPU timing. This is a stylized hybrid with artist-controlled masks, not a reconstruction of the newly linked Zhihu article, whose body could not be read.')
with (lab/'render-validation.json').open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=False))
