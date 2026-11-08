"""Named test entrypoints; every run creates a fresh report directory."""
from pathlib import Path
import argparse
import datetime
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('case',choices=['continuity','catalog','network','native']);args=parser.parse_args()
    if args.case=='native':
        player=ROOT.parent/'EndfieldNativeMotions-20261019/Playable-v2/SiNativePreview.exe'
        return subprocess.call([str(player)],cwd=player.parent)
    if args.case=='continuity':
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        cmd=[sys.executable,'-B',str(ROOT/'run_review.py'),'release-v1','--output','continuity-'+stamp]
    else:cmd=[sys.executable,'-B',str(ROOT/('run_'+args.case+'.py'))]
    return subprocess.call(cmd,cwd=ROOT)
if __name__=='__main__':raise SystemExit(main())
