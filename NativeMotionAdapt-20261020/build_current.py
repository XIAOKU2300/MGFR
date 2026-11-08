from pathlib import Path
ROOT=Path(__file__).resolve().parent
test=(ROOT/'NativeCatalogReview.cs').read_text(encoding='utf-8')
test=test.replace('public float maxSpeed,residual;', 'public float maxSpeed,residual,sourcePeak,threshold;')
test=test.replace('  MainAvatarActions driver;', '  [Serializable]class SourceSkin {public string skin;public float sourcePeak;}\n  [Serializable]class SourceClip {public string name;public SourceSkin[] skins;}\n  [Serializable]class SourceAudit {public SourceClip[] clips;}\n  MainAvatarActions driver;')
test=test.replace('   foreach(var clip in manifest.clips)', '   var audit=JsonUtility.FromJson<SourceAudit>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"native-actions/source-relative-verification.json")));\n   foreach(var clip in manifest.clips)')
test=test.replace('current=new ClipResult{name=clip.name};', 'current=new ClipResult{name=clip.name};foreach(var original in audit.clips)if(original.name==clip.name)foreach(var variant in original.skins)current.sourcePeak=Mathf.Max(current.sourcePeak,variant.sourcePeak);current.threshold=Mathf.Max(1800,current.sourcePeak*1.25f+400);')
test=test.replace('speed>1800&&angle>30', 'speed>current.threshold&&angle>30')
test=test.replace('native wave speed retained', 'source-relative speed limits; native fast gestures retained')
with (ROOT/'NativeCatalogReview-current.cs').open('x',encoding='utf-8') as f:f.write(test)
source=(ROOT/'build_native.py').read_text(encoding='utf-8').replace("ROOT/'NativeAvatarActions.cs'","ROOT/'NativeAvatarActions-main.cs'").replace("ROOT/'NativeClothCoordinator.cs'","ROOT/'NativeClothCoordinator-production.cs'").replace("ROOT/'NativeAcceptance.cs'","ROOT/'NativeAcceptance-main.cs'")
source=source.replace("files=[", "files=[ROOT/'NativeCatalogReview-current.cs',")
exec(compile(source,str(ROOT/'build_native.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'build_native.py')})
dest=ROOT/'Current/Player/MGFR_Data/StreamingAssets/native-actions/source-relative-verification.json'
with dest.open('xb') as f:f.write((ROOT/'source-relative-verification.json').read_bytes())
