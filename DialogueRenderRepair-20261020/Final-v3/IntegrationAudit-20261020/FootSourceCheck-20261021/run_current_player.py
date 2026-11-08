import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent
os.environ['XR_RUNTIME_JSON']=str(HERE/'disabled-xr-runtime.json')
spec=importlib.util.spec_from_file_location('acceptance',HERE.parents[2]/'test_motion.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=subprocess.Popen
def isolated(command,*args,**kwargs):
    command=list(command)+['-mgfr-native-data',str(HERE/'native-source-feet')]
    return original(command,*args,**kwargs)
module.subprocess.Popen=isolated
module.main()
