from pathlib import Path
ROOT=Path(__file__).resolve().parent
output=ROOT/'bake-all-source-v1';output.mkdir(exist_ok=False)
text=(ROOT/'AvatarBake.cs').read_text(encoding='utf-8')
text=text.replace('try{Bake();}', 'try{string top=output;foreach(string skin in new[]{"swimsuit","original"}){if(!skins.TrySelect(skin))throw new Exception("Skin not available");loader=skins.Loader;output=Path.Combine(top,skin);Directory.CreateDirectory(output);Bake();}}')
text=text.replace('   foreach(var clip in manifest.clips){', '   foreach(int id in new[]{738,739,740,742,743,744})if(!ids.Contains(id))ids.Add(id);\n   foreach(var clip in manifest.clips){')
text=text.replace('    if(clip.name!="idle"&&clip.name!="wave"&&clip.name!="talk_hands"&&clip.name!="think"&&clip.name!="arms_crossed")continue;', '')
text=text.replace('target.pose.SetHumanPose(ref pose);', 'target.pose.SetHumanPose(ref pose);\n      int[] aux={738,739,740,742,743,744},main={25,26,27,21,22,23};for(int k=0;k<aux.Length;k++)target.bones[aux[k]].localRotation=target.bones[main[k]].localRotation;')
with (output/'AvatarBake.cs').open('x',encoding='utf-8') as f:f.write(text)
source=(ROOT/'build_probe.py').read_text(encoding='utf-8')
source=source.replace("'avatar-probe-v1'","'bake-all-v1'").replace("ROOT/'AvatarBake.cs'","ROOT/'bake-all-source-v1/AvatarBake.cs'")
exec(compile(source,str(ROOT/'build_probe.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'build_probe.py')})
