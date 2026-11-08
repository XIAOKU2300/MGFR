from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
# Generate the new candidate without overwriting the current application or any
# earlier source artifact. The measured anchor survives a provider dropout.
source=(lab/'prepare.py').read_text(encoding='utf-8')
old="    shutil.copyfile(p,target)"
new="""    content=p.read_text(encoding='utf-8')
    if p.name=='RoomFloorPlacement.cs':
        token='            if (now - stableSince < .35f) return false;'
        assert content.count(token)==1
        content=content.replace(token,token+'\\n            if (Placed && Measured && !floor) return false;')
    with target.open('x',encoding='utf-8',newline='\\n') as output:output.write(content)"""
assert source.count(old)==1
exec(compile(source.replace(old,new),str(lab/'prepare.py'),'exec'),{'__file__':str(lab/'prepare.py'),'__name__':'__main__'})
