from pathlib import Path
ROOT=Path(__file__).resolve().parent
# Reuse the new-output-only build procedure; substitute the probe and its arguments in memory.
source=(ROOT/'build_probe.py').read_text(encoding='utf-8')
source=source.replace("'avatar-probe-v1'","'playback-probe-v1'").replace("'AvatarBake.cs'","'NativePlaybackProbe.cs'")
source=source.replace("'-mgfr-avatar-bake'","'-mgfr-native-probe'").replace("'-mgfr-bake-out',str(out)","'-mgfr-probe-out',str(out),'-mgfr-baked',str(ROOT/'avatar-probe-v1/Baked')")
source=source.replace("out/'avatar-report.txt'","out/'result.json'")
exec(compile(source,str(ROOT/'build_probe.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'build_probe.py')})
