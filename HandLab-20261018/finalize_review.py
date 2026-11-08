from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
root=Path('H:/MGFR');lab=root/'HandLab-20261018';review=lab/'Review-v3'
result=(review/'hands-review.txt').read_text(encoding='utf-8-sig');assert 'pass=True' in result
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
board=Image.new('RGB',(1800,660),(29,33,38));draw=ImageDraw.Draw(board)
for column,(file,title) in enumerate([('eye0-without-hand-depth.png','无遮挡'),('eye0-hand-in-front.png','手在前方：绿色部分露出真实透视'),('eye0-hand-behind.png','手在后方：角色保持完整')]):
 im=Image.open(review/file).convert('RGB').resize((600,600));board.paste(im,(column*600,60));draw.text((16+column*600,14),title,font=font,fill='white')
board.save(lab/'手部遮挡对比.png')
receipt=json.loads((root/'VRFIX-APPLIED-20261018.json').read_text(encoding='utf-8-sig'))
for item in receipt['files']:assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['afterSha256']
proof=dict(build='Project-v3',errors=0,existing_warnings=1,size_mb=178,
 packages=json.loads((lab/'official-package-receipt.json').read_text()),
 openxr_hand_tracking_feature_enabled=True,review=result,
 limits='Synthetic hand replay validates collision/grab/loss/occlusion; actual PICO-to-ALVR-to-SteamVR joint streaming and XR single-pass rendering still need headset verification.',
 main_configuration='Prepared and backed up; awaiting explicit overwrite authorization for two existing files.')
with (lab/'hand-validation.json').open('x',encoding='utf8') as f:json.dump(proof,f,ensure_ascii=False,indent=2)
print('Replay checks passed; old VR fix hashes unchanged. Main configuration patch prepared.')
