from pathlib import Path
import shutil
lab=Path('H:/MGFR/HandLab-20261018');old=lab/'Project-v9';project=lab/'Project-v10';source=lab/'Sources/v10'
relative=Path('Assets/MGFR/Scripts/BareHands/HandJointSource.cs');text=(old/relative).read_text(encoding='utf8')
text=text.replace('Transform origin;float nextScan;','Transform origin;float nextScan;\n  public bool PredictVisual=true;\n  readonly HandRenderPrediction[] visualPrediction={new HandRenderPrediction(),new HandRenderPrediction()};')
text=text.replace('   if(Replay)return;\n   if(Time.unscaledTime', '''   if(Replay)return;
   if(Input.GetKeyDown(KeyCode.F10)){PredictVisual=!PredictVisual;foreach(var p in visualPrediction)p.Reset();Debug.Log("[MGFR hand response] visualPrediction="+PredictVisual+" horizonMs=18; F10 compare");}
   if(Time.unscaledTime''')
text=text.replace('RenderFrames[h].Clear();filters[h].Reset();','RenderFrames[h].Clear();filters[h].Reset();visualPrediction[h].Reset();')
text=text.replace('UpdateRenderFrame(h,raw,f);','UpdateRenderFrame(h,raw,f);\n   if(PredictVisual)visualPrediction[h].Apply(RenderFrames[h],Time.realtimeSinceStartupAsDouble);')
with (source/'HandJointSource.cs').open('x',encoding='utf8') as file:file.write(text)
def ignore(path,names):return ['HandJointSource.cs'] if Path(path).name=='BareHands' else []
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for path in source.iterdir():
 folder='Editor' if path.name.endswith('Build.cs') else 'Scripts/BareHands'
 target=project/'Assets/MGFR'/folder/path.name
 with path.open('rb') as reader,target.open('xb') as writer:shutil.copyfileobj(reader,writer)
print(project)
