"""Check the player loaded by the existing MGFR entry; no microphone or paid LLM."""
from pathlib import Path
import datetime,json,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PLAYER=HERE/'Final-v3/Player/MGFR.exe'

def main():
    output=HERE/'Logs'/('stereo-check-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    output.mkdir(parents=True,exist_ok=False)
    command=[str(PLAYER),'-batchmode','-mgfr-noxr','-force-d3d11','-screen-width','900','-screen-height','700','-mgfr-structured-voice','-mgfr-avatar-data',str(ROOT/'SiLLMBridge-20261020/MainData'),'-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-action-port','1','-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-mgfr-stability-review','-mgfr-stability-out',str(output/'result.json'),'-logFile',str(output/'player.log')]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    process=subprocess.Popen(command,cwd=PLAYER.parent,startupinfo=startup)
    try:code=process.wait(timeout=170)
    except subprocess.TimeoutExpired:
        process.terminate();process.wait(timeout=10)
        print('验证超时；报告：',output)
        return 6
    with (output/'exit.json').open('x',encoding='utf-8') as stream:json.dump({'pid':process.pid,'exitCode':code,'exitHex':f'0x{code&0xffffffff:08X}'},stream,indent=2)
    path=output/'result.json'
    result=json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}
    print('双眼与稳定性检查：'+('通过' if code==0 and result.get('pass') else '未通过'))
    print('报告：',output)
    return 0 if code==0 and result.get('pass') else 5

if __name__=='__main__':raise SystemExit(main())
