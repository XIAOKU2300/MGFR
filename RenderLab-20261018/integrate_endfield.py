from pathlib import Path
import hashlib,json,shutil
from PIL import Image,ImageDraw,ImageFont
root=Path('H:/MGFR');lab=root/'RenderLab-20261018';project=lab/'Project-v3';main=root/'unity-client'
relative=['Assets/MGFR/Resources/MgfrEndfieldClothing.shader','Assets/MGFR/Scripts/Rendering/SiEndfieldClothing.cs']
relative += [p+'.meta' for p in relative]
relative += [str(p.relative_to(project)).replace('\\','/') for p in (project/'Assets/StreamingAssets/endfield').iterdir()]
relative += ['Assets/StreamingAssets/endfield.meta']
pairs=[(project/p,main/p) for p in relative]
assert all(not dst.exists() for _,dst in pairs)
receipt=[]
for src,dst in pairs:
 dst.parent.mkdir(parents=True,exist_ok=True)
 with src.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
 receipt.append(dict(path=str(dst),sha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
for folder in ('stylized','endfield'):
 with (main/f'Assets/StreamingAssets/{folder}/.gitignore').open('x',encoding='utf8') as f:f.write('*.png\n*.png.meta\n')
with (lab/'endfield-applied.json').open('x',encoding='utf8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
board=Image.new('RGB',(1440,1490),(30,34,39));draw=ImageDraw.Draw(board)
for row,pose in enumerate(('face','cloth')):
 for col,variant in enumerate(('before','after')):
  image=Image.open(lab/'Review-v3'/f'L0-{pose}-{variant}.png').convert('RGB').resize((720,720))
  board.paste(image,(col*720,50+row*720))
draw.text((24,10),'原版',font=font,fill='white');draw.text((744,10),'新材质：脸部 / 衣料与配饰',font=font,fill='white')
board.save(lab/'渲染对比-终末地材质.png')
print('Added',len(pairs),'files, no existing source overwritten')
