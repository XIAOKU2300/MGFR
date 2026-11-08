from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'MotionRepair-20261020/run_network.py').read_text(encoding='utf-8')
source=source.replace("'release-v1/Player/MGFR.exe'","'native-v3/Player/MGFR.exe'")
exec(compile(source,str(Path(__file__).resolve()),'exec'),{'__name__':'__main__','__file__':str(Path(__file__).resolve())})
