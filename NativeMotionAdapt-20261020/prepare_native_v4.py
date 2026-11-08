from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'NativeClothCoordinator-v3.cs').read_text(encoding='utf-8')
text=text.replace('  List<SwimsuitClothSolver.Capsule> body;', '  readonly List<SwimsuitClothSolver.Capsule> stepBody=new List<SwimsuitClothSolver.Capsule>();\n  List<SwimsuitClothSolver.Capsule> body;')
text=text.replace('int original=body.Count;AddAnimatedContacts();', 'int original=body.Count;stepBody.Clear();stepBody.AddRange(body);AddAnimatedContacts();')
text=text.replace('solver.Step(delta,body,handContacts,', 'solver.Step(delta,stepBody,handContacts,')
text=text.replace('iteration<2;', 'iteration<4;')
with (ROOT/'NativeClothCoordinator-v4.cs').open('x',encoding='utf-8') as f:f.write(text)
core=(ROOT/'NativeAvatarActions.cs').read_text(encoding='utf-8')
core=core.replace('   if(Array.IndexOf(args,"-mgfr-native-review")>=0)', '   if(Array.IndexOf(args,"-mgfr-native-catalog")>=0)new GameObject("Native catalog").AddComponent<NativeCatalogReview>();\n   if(Array.IndexOf(args,"-mgfr-native-review")>=0)')
with (ROOT/'NativeAvatarActions-v4.cs').open('x',encoding='utf-8') as f:f.write(core)
source=(ROOT/'build_native.py').read_text(encoding='utf-8').replace("ROOT/'NativeAvatarActions.cs'","ROOT/'NativeAvatarActions-v4.cs'").replace("ROOT/'NativeClothCoordinator.cs'","ROOT/'NativeClothCoordinator-v4.cs'").replace("ROOT/'NativeAcceptance.cs'","ROOT/'NativeAcceptance-v3.cs'")
source=source.replace("files=[", "files=[ROOT/'NativeCatalogReview.cs',")
exec(compile(source,str(ROOT/'build_native.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'build_native.py')})
