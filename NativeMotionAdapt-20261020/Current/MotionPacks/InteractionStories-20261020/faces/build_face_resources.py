import json, hashlib
from pathlib import Path
root=Path(r'H:\MGFR')
out=root/'NativeMotionAdapt-20261020/Current/MotionPacks/InteractionStories-20261020/faces'
if any(out.iterdir()): raise SystemExit('Refusing non-empty faces directory')
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name,obj):
    p=out/name
    with p.open('x',encoding='utf-8',newline='\n') as f: json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n')
models=[root/'NativeMotionAdapt-20261020/Current/Player/MGFR_Data/StreamingAssets/si/si_model.json',root/'NativeMotionAdapt-20261020/Current/Player/MGFR_Data/StreamingAssets/skins/si-swimsuit-barefoot-ankle-v4/si_model.json',root/'NativeMotionAdapt-20261020/Current/Player/MGFR_Data/StreamingAssets/skins/si-swimsuit-shoes/si_model.json']
model_data=[load(p) for p in models]
shape_sets=[{x['name'] for x in m['blendShapes']} for m in model_data]
common=sorted(set.intersection(*shape_sets))
allowed={'真面目','困る','なごみ','びっくり','にこり','笑い','口角上げ','口角下げ','にやり','にっこり'}
if not allowed.issubset(set(common)): raise SystemExit('Some projection blend names are not present in all three models')
source=root/'SiLLMBridge-20261020/emotion-expansion/source'
candidates=load(root/'NativeMotionAdapt-20261020/Current/MotionPacks/InteractionStories-20261020/face-candidates.json')
report=load(root/'NativeMotionAdapt-20261020/Current/MotionPacks/InteractionStories-20261020/face-hunt-report.json')
manifest=load(root/'SiLLMBridge-20261020/emotion-expansion/source/source-manifest.json')
old_expr=load(root/'SiLLMBridge-20261020/MainData/expressions.json')
by_name={x['name']:x for x in candidates}
by_manifest={o['name']:{'source_path':rec['path'],'sha256':o['sha256']} for rec in manifest for o in rec['objects']}
by_report={x['name']:x for x in report['presets']}
selected_names=['data_facialmorph_emotion_afraidl','data_facialmorph_emotion_afraids','data_facialmorph_emotion_confidencea','data_facialmorph_emotion_puzzlea','data_facialmorph_emotion_relaxa','data_facialmorph_emotion_tsunderea','data_facialmorph_emotion_worrieda','data_facialmorph_emotion_shya','data_facialmorph_emotion_favoura','data_facialmorph_emotion_surprisedsa','data_facialmorph_emotion_happys','data_facialmorph_emotion_thinkcloseeyesa']
selected=[]
for name in selected_names:
    c=by_name[name]; fn=Path(c['file']).name; raw=load(source/fn); meta=by_manifest[name]; r=by_report[name]
    if not r['native_controls_all_compatible']: raise SystemExit('Incompatible preset selected: '+name)
    selected.append({'name':name,'source_file':fn,'source_path':meta['source_path'],'source_file_path':c['file'],'source_sha256':meta['sha256'],'ctrl_weights':c['controls'],'native_controls_all_compatible':r['native_controls_all_compatible'],'new_unique_preset':r['new_unique_preset'],'aliases_same_nonzero_signature':r['aliases_same_nonzero_signature'],'pose':raw['_pose']})
def weights(*pairs):
    result=[{'name':n,'weight':float(v)} for n,v in pairs]
    if any(x['name'] not in common or not 0<x['weight']<=0.25 for x in result): raise SystemExit('Invalid projection weight')
    return result
def pose(name,emotion,label,sources,ws):
    return {'name':name,'emotion':emotion,'label':label,'source_kind':'native_preset_compatibility_projection','source_native_presets':sources,'projection_note':'手工温和投影；仅使用两套skin共同支持的当前PMX形态名，不直接执行原生97脸骨姿势。','weights':ws}
P=[]
def add(*args): P.append(pose(*args))
add('neutral_relax_story','neutral','neutral / relaxed story',['data_facialmorph_emotion_relaxa','data_facialmorph_emotion_confidencea'],weights(('なごみ',.10),('真面目',.035)))
add('neutral_easy_content','neutral','neutral / easy content',['data_facialmorph_emotion_relaxa'],weights(('なごみ',.14),('にこり',.07),('口角上げ',.04)))
add('neutral_soft_attention','neutral','neutral / soft attention',['data_facialmorph_emotion_relaxa','data_facialmorph_emotion_confidencea'],weights(('真面目',.06),('なごみ',.07)))
add('happy_headpat_received','happy','happy / headpat received',['data_facialmorph_emotion_favoura','data_facialmorph_emotion_happys'],weights(('にこり',.17),('なごみ',.09),('口角上げ',.05)))
add('happy_quiet_pleased','happy','happy / quiet pleased',['data_facialmorph_emotion_favoura','data_facialmorph_emotion_relaxa'],weights(('にこり',.12),('なごみ',.10),('笑い',.035)))
add('happy_gentle_smile','happy','happy / gentle smile',['data_facialmorph_emotion_happys','data_facialmorph_emotion_favoura'],weights(('にこり',.20),('口角上げ',.07)))
add('shy_headpat','shy','shy / headpat',['data_facialmorph_emotion_tsunderea','data_facialmorph_emotion_shya'],weights(('困る',.13),('にこり',.10),('口角上げ',.035)))
add('shy_bashful_smile','shy','shy / bashful smile',['data_facialmorph_emotion_tsunderea','data_facialmorph_emotion_shya'],weights(('困る',.09),('にこり',.14),('口角上げ',.06)))
add('shy_restrained','shy','shy / restrained',['data_facialmorph_emotion_tsunderea','data_facialmorph_emotion_shya'],weights(('困る',.14),('なごみ',.06),('にやり',.025)))
add('thinking_puzzle_soft','thinking','thinking / puzzled',['data_facialmorph_emotion_puzzlea'],weights(('困る',.12),('真面目',.05)))
add('thinking_considering_gently','thinking','thinking / considering',['data_facialmorph_emotion_puzzlea','data_facialmorph_emotion_confidencea'],weights(('真面目',.11),('困る',.06)))
add('thinking_unsure','thinking','thinking / unsure',['data_facialmorph_emotion_puzzlea','data_facialmorph_emotion_worrieda'],weights(('困る',.14),('なごみ',.035)))
add('sad_worried_soft','sad','sad / gently worried',['data_facialmorph_emotion_worrieda'],weights(('困る',.16),('口角下げ',.045)))
add('sad_concerned_listening','sad','sad / concerned',['data_facialmorph_emotion_worrieda','data_facialmorph_emotion_afraids'],weights(('困る',.13),('真面目',.045),('口角下げ',.035)))
add('sad_small_uncertainty','sad','sad / small uncertainty',['data_facialmorph_emotion_afraids','data_facialmorph_emotion_worrieda'],weights(('困る',.12),('びっくり',.045)))
add('surprised_mild_notice','surprised','surprised / mild notice',['data_facialmorph_emotion_afraids','data_facialmorph_emotion_surprisedsa'],weights(('びっくり',.11),('困る',.045)))
add('surprised_warmly_curious','surprised','surprised / warmly curious',['data_facialmorph_emotion_afraidl','data_facialmorph_emotion_surprisedsa'],weights(('びっくり',.15),('なごみ',.035)))
add('surprised_soft_question','surprised','surprised / soft question',['data_facialmorph_emotion_afraids','data_facialmorph_emotion_surprisedsa','data_facialmorph_emotion_puzzlea'],weights(('びっくり',.08),('困る',.07),('真面目',.025)))
add('affection_relaxed_nearby','affection','affection / relaxed nearby',['data_facialmorph_emotion_relaxa','data_facialmorph_emotion_favoura'],weights(('なごみ',.13),('にこり',.11),('口角上げ',.035)))
add('affection_warm_response','affection','affection / warm response',['data_facialmorph_emotion_favoura','data_facialmorph_emotion_happys'],weights(('にこり',.16),('なごみ',.09)))
add('affection_trusting','affection','affection / trusting',['data_facialmorph_emotion_relaxa','data_facialmorph_emotion_confidencea'],weights(('なごみ',.12),('真面目',.04),('にこり',.08)))
allowed_categories={'neutral','happy','sad','angry','surprised','shy','thinking','affection'}
if {x['emotion'] for x in old_expr['poses']}!=allowed_categories: raise SystemExit('Existing category schema mismatch')
write('expressions-additions.json',{'poses':P})
write('native-presets.json',{'format':'interaction-story-native-presets-v1','description':'原游戏预设控制权重与_pose解析证据，仅供追溯和未来适配；当前运行时不消费97骨姿势。','presets':selected})
model_hashes=[{'path':str(p.relative_to(root)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'blendshape_count':len(m['blendShapes'])} for p,m in zip(models,model_data)]
proof={'generator':'只读源数据检查 + 手工兼容投影','source_files':['NativeMotionAdapt-20261020/Current/MotionPacks/InteractionStories-20261020/face-candidates.json','NativeMotionAdapt-20261020/Current/MotionPacks/InteractionStories-20261020/face-hunt-report.json','SiLLMBridge-20261020/emotion-expansion/source/source-manifest.json','SiLLMBridge-20261020/emotion-expansion/expand_emotions.py (仅检查，未运行)','SiLLMBridge-20261020/MainData/expressions.json'],'skin_models':model_hashes,'common_blendshapes':common,'projection_blendshapes_used':sorted({w['name'] for p in P for w in p['weights']}),'excluded_blendshape_classes':['lip sync: vowel','lip sync: closed mouth','lip sync/eyes: blink','eyes: wink','eyes: pupil/lid'],'native_pose_method':'保留源JSON的_pose控制组作为证据；未转换或接入97骨姿势。','new_unique_compatible_native_preset_count':sum(x['new_unique_preset'] and x['native_controls_all_compatible'] for x in selected),'selected_native_preset_count':len(selected),'projected_pose_count':len(P),'projected_pose_emotions':sorted({p['emotion'] for p in P}),'all_projection_names_in_all_three_models':True,'no_zero_or_out_of_range_weights':all(0<w['weight']<=.25 for p in P for w in p['weights']),'aliases_retained':True}
write('provenance.json',proof)
pet={'format':'head-pet-suggestions-v1','scope':'仅动作与表情建议数据；不接入检测引擎，不定义触发器或运行时行为。','actions':[{'action':'gentle_head_pat','pose_names':['happy_headpat_received','shy_headpat','affection_relaxed_nearby'],'suggestion':'轻柔摸头后短暂选择温和开心或害羞表情。'},{'action':'close_and_reassure','pose_names':['affection_warm_response','sad_concerned_listening','neutral_relax_story'],'suggestion':'靠近安慰时选亲近或放松表情。'},{'action':'unexpected_attention','pose_names':['surprised_mild_notice','surprised_warmly_curious','surprised_soft_question'],'suggestion':'轻微惊讶后过渡到好奇或放松表情。'},{'action':'gentle_teasing','pose_names':['shy_bashful_smile','shy_restrained','thinking_unsure'],'suggestion':'轻度调侃后选择害羞或犹豫表情。'}],'constraints':['建议仅作为动作与表情数据；没有检测阈值、事件监听或执行代码。','输出权重是温和形态投影，不能还原原生游戏脸部形态。']}
write('head-pet-suggestions.json',pet)
for p in out.glob('*.json'): load(p)
print(json.dumps({'out':str(out),'files':sorted(p.name for p in out.iterdir()),'new_unique_native_presets':proof['new_unique_compatible_native_preset_count'],'selected_native_presets':len(selected),'projection_variants':len(P),'categories':proof['projected_pose_emotions']},ensure_ascii=False,indent=2))
