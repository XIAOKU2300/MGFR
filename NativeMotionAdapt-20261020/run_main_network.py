from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT.parent/'MotionRepair-20261020/run_network.py').read_text(encoding='utf-8').replace("'release-v1/Player/MGFR.exe'","'Main/Player/MGFR.exe'")
exec(compile(source,str(Path(__file__).resolve()),'exec'),{'__name__':'__main__','__file__':str(Path(__file__).resolve())})
