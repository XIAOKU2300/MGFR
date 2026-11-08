from pathlib import Path
lab=Path(__file__).resolve().parent
project=lab/'Project2'
p=project/'Assets/MGFR/Scripts/BareHands/AdaptiveHandsReview.cs'
s=p.read_text(encoding='utf8').replace('AdaptiveHandsReview','AdaptiveHandsReview2').replace('-mgfr-adaptive-review','-mgfr-adaptive-review2').replace('adaptive-integration-report.txt','adaptive-integration2-report.txt')
a='   Check(selected>=0,"select actual skirt point");'
b='''   // Mesh order begins with hair. Select a skirt probe independently of the
   // bounded mixed-surface benchmark instead of assuming a material ordering.
   if(selected<0)for(int i=0;i<vertices.Length;i+=7)
   {
    if(!groups.TryGetValue(weights[i].boneIndex0,out int group)||group!=9||weights[i].weight0<.7f)continue;
    if(query.Find(loader.Renderer.transform.TransformPoint(vertices[i]),.02f,-1,out int body,out var local))
    {selected=body;point=root.TransformPoint(local);break;}
   }
'''+a
assert s.count(a)==1
s=s.replace(a,b)
with (p.with_name('AdaptiveHandsReview2.cs')).open('x',encoding='utf8') as f:f.write(s)
p=project/'Assets/MGFR/Editor/AdaptiveHandsBuild.cs'
s=p.read_text(encoding='utf8').replace('AdaptiveHandsBuild','AdaptiveHandsBuild2').replace('Build/Windows/MGFR.exe','Build2/Windows/MGFR.exe')
with (p.with_name('AdaptiveHandsBuild2.cs')).open('x',encoding='utf8') as f:f.write(s)
