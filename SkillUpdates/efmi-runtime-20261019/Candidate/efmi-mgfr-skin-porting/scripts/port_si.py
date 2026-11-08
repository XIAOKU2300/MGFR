"""Fingerprint-locked reproduction of the Si swimsuit resource workflow."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys
from model_tool import read_base,emit_json,signature,verify

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def preflight(base,mod):
    profile=json.loads((HERE.parent/'references/si-profile.json').read_text(encoding='utf-8'))
    problems=[]
    if not base.is_dir() or not mod.is_dir():raise ValueError('Base and Mod directories must exist')
    m,_,_=read_base(base)
    if m['counts']!=profile['base']['counts']:problems.append('Base counts differ')
    if sha(base/'si_model.bin')!=profile['base']['binarySha256']:problems.append('Base binary differs')
    if signature(m['bones'])!=profile['base']['bonesSignature']:problems.append('Base rig/rest data differs')
    if signature(m['materials'])!=profile['base']['materialsSignature']:problems.append('Base material contract differs')
    if signature(m['blendShapes'])!=profile['base']['morphsSignature']:problems.append('Base morph contract differs')
    for rel,digest in profile['mod']['files'].items():
        relative=Path(rel)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe profile path')
        f=mod/relative
        if not f.is_file():problems.append('Missing Mod file: '+rel)
        elif sha(f)!=digest:problems.append('Changed Mod file: '+rel)
    for rel,digest in profile['base']['textures'].items():
        f=base/'textures'/rel
        if not f.is_file() or sha(f)!=digest:problems.append('Changed/missing base texture: '+rel)
    if problems:raise ValueError('Input profile does not match. Investigate before adapting a new profile:\n'+'\n'.join(problems[:12]))
    files=[base/'si_model.json',base/'si_model.bin']+[base/'textures'/rel for rel in profile['base']['textures']]+[mod/rel for rel in profile['mod']['files']]
    return {str(f.resolve()):sha(f) for f in files}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['inspect','convert']);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--mod',type=Path,required=True);ap.add_argument('--out',type=Path);ap.add_argument('--barefoot',action='store_true');args=ap.parse_args()
    if args.command=='convert':
        if args.out is None:ap.error('convert requires --out')
        if args.out.exists():raise ValueError('Output exists; choose a new directory')
        output=args.out.resolve()
        for src in (args.base.resolve(),args.mod.resolve()):
            if output==src or src in output.parents or output in src.parents:raise ValueError('Output and source directories must not overlap')
    hashes=preflight(args.base,args.mod)
    if args.command=='inspect':
        print(json.dumps(dict(profileMatched=True,readOnly=True,checkedFiles=len(hashes),profile='Si blue-white swimsuit; fixed draw ranges'),ensure_ascii=False));return 0
    output.mkdir(parents=True,exist_ok=False);(output/'stages').mkdir();(output/'logs').mkdir()
    emit_json(output/'source-hashes.json',hashes)
    log=output/'WORKLOG.md'
    with log.open('x',encoding='utf-8') as f:f.write('# Si skin conversion run\n\nStarted UTC: '+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n\nScope: independent resources; existing character not replaced.\n\n')
    def note(value):
        with log.open('a',encoding='utf-8') as f:f.write(value+'\n\n')
    def stage(name,script,*parameters):
        command=[sys.executable,str(HERE/'si_case'/script),*map(str,parameters)]
        note('Stage: '+name+'; helper: '+script)
        env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONDONTWRITEBYTECODE']='1'
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',env=env)
        with (output/'logs'/(name+'.txt')).open('x',encoding='utf-8') as f:f.write(result.stdout+'\n'+result.stderr)
        if result.returncode:
            note('FAILED: '+name+'; partial outputs preserved. See logs. No automatic retries.')
            raise RuntimeError('Stage failed: '+name+'; see '+str(output/'logs'/(name+'.txt')))
    raw=output/'stages/01-raw';atlas=output/'stages/02-atlas';clothed=output/'stages/03-swimsuit';model=output/'model'
    stage('01-raw','build_swimsuit_v1.py','--base',args.base.resolve(),'--source',args.mod.resolve(),'--out',raw)
    stage('02-atlas','finalize_swimsuit_v2.py','--input',raw,'--out',atlas)
    stage('03-swimsuit','package_swimsuit_v3.py','--input',atlas,'--out',clothed)
    if args.barefoot:
        foot=output/'stages/04-barefoot-base'
        stage('04-barefoot-base','make_barefoot_base.py','--input',clothed,'--out',foot)
        stage('05-ankle-surface','sculpt_ankle.py','--input',foot,'--out',model)
        note('Barefoot surface uses the v4 candidate method. Earlier ankles were rejected; this output still requires real render and user review.')
    else:shutil.copytree(clothed,model)
    checks=verify(model,args.base);emit_json(model/'contract-checks.json',checks)
    if not checks['allPassed']:raise RuntimeError('Model contract verification failed')
    unchanged=all(Path(path).is_file() and sha(Path(path))==digest for path,digest in hashes.items())
    if not unchanged:raise RuntimeError('An input hash changed during conversion')
    m,_,_=read_base(model)
    emit_json(model/'skin.json',dict(id='si-swimsuit-barefoot-candidate' if args.barefoot else 'si-swimsuit',name='Si blue-white swimsuit'+(' / barefoot ankle candidate' if args.barefoot else ''),format='MGFR model binary v1',entry={'json':'si_model.json','binary':'si_model.bin','textures':'textures'},counts=m['counts'],restPoseChanged=True,existingCharacterReplaced=False,visualStatus='Not rendered in this run; user visual acceptance pending',clothSimulation='Basic skinning only',materialBindings=[dict(slots=[7],albedo='textures/swimsuit_body_D.png',normalData='textures/swimsuit_body_N.png'),dict(slots=[8,10],albedo='textures/swimsuit_cloth_D.png',normalData='textures/swimsuit_cloth_N.png',sourceLightData='textures/swimsuit_cloth_L.png')]))
    with (model/'README.md').open('x',encoding='utf-8') as f:f.write('# Independent Si skin\n\nMGFR native bin/json/textures. Set dataRootOverride before Build on a new loader. No host integration was performed.\n\nUse this model\'s rest joints and inverse binds. Original costume normal/packed/emission overrides need per-skin routing. Sleeves and skirt use basic skinning.\n\nNumerical checks passed; actual Unity renders, visual acceptance, animation integration and VR are separate, pending steps.\n')
    note('Numerical model contract passed. All '+str(len(hashes))+' source file hashes unchanged. Final model: model/. Render and user visual acceptance remain pending.')
    print(json.dumps(dict(model=str(model),counts=m['counts'],sourceHashesUnchanged=unchanged,visualStatus='pending'),ensure_ascii=False));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,IndexError,AssertionError,RuntimeError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(2)
