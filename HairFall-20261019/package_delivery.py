from pathlib import Path
import json
import hashlib
import difflib
from PIL import Image,ImageDraw,ImageFont

lab=Path(__file__).resolve().parent;root=lab.parent
old=root/'NaturalIdle-20261019/Project5';project=lab/'Project3'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
hashes=json.loads((lab/'baseline-hashes.json').read_text(encoding='utf-8'))
assert all(sha(Path(p))==digest for p,digest in hashes.items())
motion=json.loads((lab/'Review3/hair-fall-report.json').read_text(encoding='utf-8'))
hands=json.loads((lab/'InteractionReview/motion-cloth.json').read_text(encoding='utf-8'))
assert motion['pass'] and hands['pass']
patch=[];sources={}
for p in map(Path,('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs',
                  'Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs',
                  'Assets/MGFR/Scripts/Experience/NaturalIdle/HairFallReview.cs')):
    before=(old/p).read_text(encoding='utf-8-sig') if (old/p).exists() else ''
    after=(project/p).read_text(encoding='utf-8-sig')
    patch+=difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix())
    sources[p.as_posix()]=sha(project/p)
with (lab/'hair-soft-float-final.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
with (lab/'delivery-receipt.json').open('x',encoding='utf-8') as f:
    json.dump({'project':str(project),'executable':str(project/'Build/Windows/MGFR.exe'),
        'sourceSha256':sources,'executableSha256':sha(project/'Build/Windows/MGFR.exe'),
        'previousSourceUnchanged':True,'desktopReview':motion,'interactionReview':hands,'headsetVerified':False},f,indent=2,ensure_ascii=False)

for desktop in (False,True):
    path=root/('启动MGFR柔发轻飘版'+('（桌面）' if desktop else '')+'.cmd');assert not path.exists()
    lines=['@echo off','setlocal','set "MGFR_SOFT_HAIR_ROOT=H:\\MGFR\\HairFall-20261019"',
      'set "MGFR_SOFT_HAIR_LOG=%MGFR_SOFT_HAIR_ROOT%\\play-%RANDOM%-%RANDOM%-%RANDOM%.log"']
    if desktop:lines.append('set "XR_RUNTIME_JSON=%MGFR_SOFT_HAIR_ROOT%\\desktop-no-runtime.json"')
    lines+=['echo MGFR Soft Hair: F5 skin, F6 idle, F7 physics, F10 captions, F11 rendering.',
      'start "" "%MGFR_SOFT_HAIR_ROOT%\\Project3\\Build\\Windows\\MGFR.exe" '+
      ('-mgfr-noxr ' if desktop else '')+'-mgfr-skins -mgfr-zmd -logFile "%MGFR_SOFT_HAIR_LOG%"','endlocal']
    with path.open('x',encoding='ascii',newline='') as f:f.write('\r\n'.join(lines)+'\r\n')
    print(path)

canvas=Image.new('RGB',(960,648),(28,31,36));draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
draw.text((20,12),'旧版：关节锁死，长发横撑',font=font,fill='white')
draw.text((500,12),'新版：保留弧度，适度轻飘',font=font,fill='white')
for x,p in ((0,lab/'Reference1/side-030.png'),(480,lab/'Review3/side-030.png')):
    canvas.paste(Image.open(p).convert('RGB').resize((480,600)),(x,48))
out=lab/'hair-before-after.png';assert not out.exists();canvas.save(out)
frames=[Image.open(p).convert('RGB').resize((480,600)).quantize(colors=128) for p in sorted((lab/'Review3').glob('side-*.png'))]
out=lab/'soft-hair-turn-preview.gif';assert not out.exists()
frames[0].save(out,save_all=True,append_images=frames[1:],duration=250,loop=0)
print('Final delivery ready; previous project unchanged.')
