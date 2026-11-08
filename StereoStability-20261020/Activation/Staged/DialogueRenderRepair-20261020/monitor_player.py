"""Keep an exit record for the existing player without restarting it."""
from pathlib import Path
import argparse,datetime,json,subprocess,sys,time

def write_new(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command:raise ValueError('Player command missing')
    args.log.parent.mkdir(parents=True,exist_ok=True)
    stem=args.log.with_suffix('')
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    timer=time.monotonic()
    try:
        child=subprocess.Popen(command,cwd=Path(command[0]).resolve().parent,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        write_new(Path(str(stem)+'-process.json'),{'pid':child.pid,'startedUtc':started,'player':command[0],'playerLog':str(args.log)})
        code=child.wait()
        write_new(Path(str(stem)+'-exit.json'),{'pid':child.pid,'startedUtc':started,'endedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-timer,'exitCode':code,'exitHex':f'0x{code&0xffffffff:08X}','exitClass':'normal' if code==0 else 'abnormal','playerLog':str(args.log)})
        return 0
    except Exception as error:
        write_new(Path(str(stem)+'-monitor-error.json'),{'errorType':type(error).__name__,'startedUtc':started})
        return 1

if __name__=='__main__':raise SystemExit(main())
