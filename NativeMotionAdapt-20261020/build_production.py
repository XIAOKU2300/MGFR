from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'NativeClothCoordinator-main.cs').read_text(encoding='utf-8')
text=text.replace('   Add(bones[13].position+side,bones[15].position+side,.066f);Add(bones[13].position-side,bones[15].position-side,.066f);', '   // Keep the established fitted chest capsule. Inflating its shoulder width\n   // pushes this costume\'s neckline above its attachment line.')
with (ROOT/'NativeClothCoordinator-production.cs').open('x',encoding='utf-8') as f:f.write(text)
source=(ROOT/'build_native.py').read_text(encoding='utf-8').replace("ROOT/'NativeAvatarActions.cs'","ROOT/'NativeAvatarActions-main.cs'").replace("ROOT/'NativeClothCoordinator.cs'","ROOT/'NativeClothCoordinator-production.cs'").replace("ROOT/'NativeAcceptance.cs'","ROOT/'NativeAcceptance-main.cs'")
source=source.replace("files=[", "files=[ROOT/'NativeCatalogReview.cs',")
exec(compile(source,str(ROOT/'build_native.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'build_native.py')})
