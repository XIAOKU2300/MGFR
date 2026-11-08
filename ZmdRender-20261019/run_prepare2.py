from pathlib import Path
lab=Path(__file__).resolve().parent
script=(lab/'prepare.py').read_text(encoding='utf8').replace("lab/'Candidate'","lab/'Candidate2'").replace("lab/'Project1'","lab/'Project2'").replace("'utf8-sig'","'utf-8-sig'")
a="write(candidate/module/name,(lab/'Source'/name).read_text(encoding='utf8'))"
b="write(candidate/module/name,(lab/'Source'/name).read_text(encoding='utf8').replace('ShadowResolution previousResolution','LightShadowResolution previousResolution').replace('if(IsReady&&Loader!=null)SetActive(false);','if(IsReady&&Loader!=null&&legacy!=null)SetActive(false);'))"
assert script.count(a)==1
exec(compile(script.replace(a,b),str(lab/'prepare.py'),'exec'),{'__file__':str(lab/'prepare.py'),'__name__':'__main__'})
