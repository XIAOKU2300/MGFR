from pathlib import Path
from PIL import Image, ImageDraw

lab=Path(__file__).resolve().parents[1]
review=lab/'ReviewSupplement'
entries=[('barefoot_v4-01-equipped.png','Equipped'),
    ('barefoot_v4-02-detached-cover_skirt.png','Cover skirt detached'),
    ('barefoot_v4-03-all-accessories-off.png','Accessories removed; swimsuit stays'),
    ('barefoot_v4-back.png','Back'),('barefoot_v4-side.png','Side'),
    ('barefoot_v4-grip-anchors.png','Grip anchors (orange)')]
result=Image.new('RGB',(990,900),'#282d35');draw=ImageDraw.Draw(result)
for i,(name,title) in enumerate(entries):
    im=Image.open(review/name).convert('RGB');im.thumbnail((330,420))
    x,y=(i%3)*330,(i//3)*450
    draw.text((x+10,y+10),title,fill='white');result.paste(im,(x+(330-im.width)//2,y+30))
with (lab/'preview.png').open('xb') as f:result.save(f,format='PNG')
print(lab/'preview.png')
