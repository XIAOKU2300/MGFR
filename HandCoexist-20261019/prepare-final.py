from pathlib import Path
lab=Path(__file__).resolve().parent
s=(lab/'prepare.py').read_text(encoding='utf-8')
a="s=once(s,'f.Clear();RenderFrames[h].Clear();return;}',"
b="s=once(s,'f.Clear();RenderFrames[h].Clear();filters[h].Reset();return;}',"
assert s.count(a)==1
exec(compile(s.replace(a,b),str(lab/'prepare.py'),'exec'),{'__file__':str(lab/'prepare.py'),'__name__':'__main__'})
