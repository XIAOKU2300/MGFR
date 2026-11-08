"""Use the installed latest voice health/start logic; never copy its credentials."""
from pathlib import Path
import importlib.util,sys,datetime,subprocess,types

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'SpeechNatural-20261019/VoiceRepair/launch_voice_v6.py'
def main():
 sys.dont_write_bytecode=True
 sys.path.insert(0,str(SOURCE.parent))
 spec=importlib.util.spec_from_file_location('mgfr_installed_voice_launcher',SOURCE)
 installed=importlib.util.module_from_spec(spec);spec.loader.exec_module(installed)
 installed.PLAYER=ROOT/'Build/Windows-final/MGFR.exe'
 installed.DELIVERY=ROOT/'Review/LaunchLogs';installed.DELIVERY.mkdir(parents=True,exist_ok=True)
 (installed.DELIVERY/'VoiceRepair').mkdir(exist_ok=True)
 if not installed.PLAYER.is_file():raise RuntimeError('Candidate player is missing')
 original_popen=subprocess.Popen
 def candidate_process(args,**kwargs):
  if args and Path(args[0])==installed.PLAYER:
   args=list(args)+['-mgfr-hand-calibration',str(ROOT/'hand-calibration-v1.json')]+sys.argv[1:]
  return original_popen(args,**kwargs)
 installed.subprocess=types.SimpleNamespace(Popen=candidate_process,CREATE_NO_WINDOW=subprocess.CREATE_NO_WINDOW)
 # ensure_service's worker still runs SOURCE (__file__), preserving installed imports.
 installed.main()
if __name__=='__main__':
 try:main()
 except Exception as error:
  print('MGFR candidate startup did not complete ('+type(error).__name__+'). Existing services were preserved.',file=sys.stderr);raise SystemExit(1)
