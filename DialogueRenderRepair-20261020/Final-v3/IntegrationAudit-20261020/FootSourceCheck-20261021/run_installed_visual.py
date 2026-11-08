from pathlib import Path
HERE=Path(__file__).resolve().parent
script=(HERE/'run_review.py').read_text(encoding='utf-8')
script=script.replace('ReviewPlayer/MGFR.exe','ReviewPlayer-v2/MGFR.exe')
script=script.replace("'Results'","'Results-installed'").replace('Results/result.json','Results-installed/result.json')
script=script.replace("'player.log'","'player-installed.log'").replace("'startup.log'","'startup-installed.log'")
exec(compile(script,str(HERE/'run_review.py'),'exec'),{'__file__':str(HERE/'run_review.py'),'__name__':'__main__'})
