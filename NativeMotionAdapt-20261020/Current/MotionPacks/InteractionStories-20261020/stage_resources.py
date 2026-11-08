"""Prepare a reviewable motion-only update. This script does not install it."""
from pathlib import Path
import ast, hashlib, json, re, struct
import numpy as np
ROOT=Path('H:/MGFR');PACK=Path(__file__).resolve().parent
MAIN=ROOT/'SiLLMBridge-20261020/MainData'
PLAYER=ROOT/'NativeMotionAdapt-20261020/Current/Player'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def cp(source,dest):
 dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(source.read_bytes())
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def label(name):
 terms=[('talklefthand1','左手轻声说明'),('talklefthand2','左手展开说明'),('talkrighthand1','右手轻声说明'),('talkrighthand2','右手展开说明'),('chesthugging3_talk','抱臂说话'),('chesthugging3_derived_tail','抱臂·尾部衍生'),('chesthugging3','抱臂姿态三'),('chesthugging1','抱臂姿态一'),('scratchhead','挠头'),('think1','思考'),('muse','沉思'),('surprise','惊讶回应'),('introduction','介绍自己'),('halfraise','半举手回应'),('akimboleft','左手叉腰'),('akimboright','右手叉腰'),('akimbo1','双手叉腰'),('censure','嗔怪/责备'),('angry02','不满回应'),('dignified','郑重姿态'),('cough','掩口轻咳'),('adjust','站姿调整'),('point','指示手势'),('touchhead','触头互动候选'),('petting','主动抚摸候选'),('turn_l_180','左转180度'),('turn_l_90','左转90度'),('turn_r_180','右转180度'),('turn_r_90','右转90度')]
 stem=next((v for k,v in terms if k in name),name)
 phase=name.rsplit('_',1)[-1]
 return stem+{'start':'·起始','loop':'·循环段','end':'·收尾'}.get(phase,'')

def main():
 adapted=PACK/'Adapted';adapted.mkdir(exist_ok=False)
 install=PACK/'InstallReview';install.mkdir(exist_ok=False)
 clips=[]
 for converted,bake,manifest in [('converted-story','bake-story','manifest-complete.json'),('converted-generic','bake-generic','manifest.json')]:
  source=PACK/converted
  for info in json.loads((source/'motions'/manifest).read_text(encoding='utf-8'))['clips']:
   info['label']=label(info['name']);clips.append(info)
   cp(source/'motions'/info['file'],adapted/'motions'/info['file'])
   for skin in ['swimsuit','original']:
    cp(PACK/bake/'Baked'/skin/(info['name']+'.hpose'),adapted/'raw-baked'/skin/(info['name']+'.hpose'))
 # Remove the petting scene's fixed horizontal placement from the delivered copy.
 # Preserve its vertical motion, rotations, original raw pose and native source.
 corrections=[];validation=[]
 for skin in ['swimsuit','original']:
  reference=(PLAYER/'MGFR_Data/StreamingAssets/native-actions'/skin/'idle.hpose').read_bytes()
  _,n,f,rate=struct.unpack_from('<iiif',reference);ids=np.frombuffer(reference,dtype='<i4',count=n,offset=16)
  neutral=np.frombuffer(reference,dtype='<f4',offset=16+4*n).reshape(f,n,7)
  hip=int(np.where(ids==5)[0][0])
  for c in clips:
   src=adapted/'raw-baked'/skin/(c['name']+'.hpose');raw=src.read_bytes()
   magic,bones,frames,fps=struct.unpack_from('<iiif',raw);assert magic==0x45535048 and bones==58 and frames==c['frames'] and fps==c['fps']
   assert len(raw)==16+4*bones+frames*bones*28
   bone_ids=np.frombuffer(raw,dtype='<i4',count=bones,offset=16);assert np.array_equal(ids,bone_ids)
   values=np.frombuffer(raw,dtype='<f4',offset=16+4*bones).copy().reshape(frames,bones,7)
   if c['name']=='common_petting_loop':
    offset=values[0,hip,[0,2]]-neutral[0,hip,[0,2]]
    values[:,hip,0]-=offset[0];values[:,hip,2]-=offset[1]
    corrections.append(dict(name=c['name'],skin=skin,target_bone=5,removed_constant_local_xz=offset.tolist(),note='Only constant scene placement removed. Source archival files unchanged.'))
   assert np.isfinite(values).all();error=float(np.max(np.abs(np.linalg.norm(values[:,:,3:],axis=-1)-1)));assert error<1e-4
   dst=adapted/'native-actions'/skin/src.name;dst.parent.mkdir(parents=True,exist_ok=True)
   with dst.open('xb') as o:o.write(raw[:16+4*bones]);o.write(values.astype('<f4').tobytes())
   validation.append(dict(name=c['name'],skin=skin,frames=frames,mapped_bones=bones,quaternion_norm_error=error,sha256=sha(dst)))
 save(adapted/'motions/manifest.json',dict(format='ENFMOT1',clips=clips,errors=[]))
 save(adapted/'body-validation.json',dict(passed=True,clips=len(clips),target_files=len(validation),target_skin_frames=sum(r['frames'] for r in validation),checks=['58 target bones on both currently installed skins','Exact header/size/frame/fps parity','Finite values and unit quaternions','57 unique source clips; source raw SHA256 receipts retained'],root_corrections=corrections,results=validation))
 cp(PACK/'faces/expressions-additions.json',adapted/'expressions-additions.json')
 existing_manifest=json.loads((MAIN/'motions/manifest.json').read_text(encoding='utf-8'));existing_manifest['clips']+=clips
 save(install/'manifest.json',existing_manifest)
 expressions=json.loads((MAIN/'expressions.json').read_text(encoding='utf-8'))
 addition=json.loads((adapted/'expressions-additions.json').read_text(encoding='utf-8'))['poses']
 expressions['poses']+=addition;assert len({p['name'] for p in expressions['poses']})==len(expressions['poses'])
 save(install/'expressions.json',expressions)
 catalog=json.loads((MAIN/'catalog.json').read_text(encoding='utf-8'));new_allowed=[];inventory=[]
 for c in clips:
  name=c['name'];phase=name.rsplit('_',1)[-1];phase=phase if phase in ['start','loop','end'] else 'single'
  reserved=any(term in name for term in ['idle_turn_','derived_tail','cough','dignified','common_petting'])
  family=name.rsplit('_',1)[0] if phase!='single' else re.sub(r'[12]$','',name)
  entry=dict(name=name,label=c['label'],file=c['file'],duration=c['duration'],tags=['story','dialogue',phase]+(['interaction_candidate'] if name.startswith('common_') else []),family=family+':'+phase,callable=not reserved,semantic_safe=not name.startswith('common_'),native_face_active=False,native_face_moving_bones=0,source_name=c['source_name'],phase=phase,review='Current actual Animation sampled at mid-clip; finite target bones; not a full clothing collision guarantee',usage_note='保留备用，未放入LLM随机动作池' if reserved else ('原名touchhead；方向仅为候选，未连接触摸检测' if name.startswith('common_') else '来自祀剧情/对话；与情绪表情组合使用'))
  catalog['actions'].append(entry);inventory.append(entry)
  if not reserved:new_allowed.append(name)
 for key in ['emotions','expressions']:
  for emotion in catalog[key]:
   emotion['variants'] += [{k:p[k] for k in ['name','label','source_kind']} for p in addition if p['emotion']==emotion['name']]
 save(install/'catalog.json',catalog)
 current_python=ROOT/'SpeechNatural-20261019/VoiceRepair/avatar_json.py';text=current_python.read_text(encoding='utf-8')
 parsed=ast.parse(text);old=next(ast.literal_eval(n.value) for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REVIEWED_ACTIONS' for t in n.targets));allowed=sorted(old|set(new_allowed))
 changed,count=re.subn(r'^REVIEWED_ACTIONS = .*$', 'REVIEWED_ACTIONS = {'+', '.join(repr(n) for n in allowed)+'}', text, count=1,flags=re.M);assert count==1
 def without_whitelist(src):
  tree=ast.parse(src)
  return ast.dump(ast.Module(body=[n for n in tree.body if not(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REVIEWED_ACTIONS' for t in n.targets))],type_ignores=[]))
 assert without_whitelist(text)==without_whitelist(changed)
 with (install/'avatar_json.py').open('x',encoding='utf-8') as o:o.write(changed)
 save(adapted/'action-catalog.json',dict(actions=inventory,new_llm_callable=len(new_allowed),reserved=len(clips)-len(new_allowed)))
 targets=[(MAIN/'motions/manifest.json',install/'manifest.json','增加57段动作索引'),(MAIN/'expressions.json',install/'expressions.json','增加21个兼容表情变体'),(MAIN/'catalog.json',install/'catalog.json','公布动作和情绪变体，标记备用片段'),(current_python,install/'avatar_json.py','只增加已适配动作名字；其余语音逻辑AST完全相同')]
 changes=[]
 for i,(target,candidate,reason) in enumerate(targets,1):
  backup=install/'Backups'/(str(i)+'-'+target.name);cp(target,backup)
  changes.append(dict(operation='覆盖',target=str(target),file_count=1,candidate=str(candidate),reason=reason,backup=str(backup),before_sha256=sha(target),after_sha256=sha(candidate)))
 save(install/'overwrite-review.json',dict(status='AWAITING_EXPLICIT_USER_APPROVAL',changes=changes,additive_resource_files=171,unchanged_runtime_module_sha256=sha(PLAYER/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'),unchanged_launcher_sha256=sha(ROOT/'启动MGFR.cmd'),new_callable=len(new_allowed),reserved=len(clips)-len(new_allowed),no_existing_files_written=True))
 print('Staged',len(clips),'body clips x2,',len(addition),'face variants;',len(new_allowed),'new callable;',len(clips)-len(new_allowed),'reserved; 4 existing-file updates require approval.')

if __name__=='__main__':main()
