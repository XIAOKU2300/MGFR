from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'PreviewProject-v1';OUT.mkdir(exist_ok=False)
def write(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:f.write(s)
for name,sub in [('NativeMotionPlayer.cs','Runtime'),('NativePreview.shader','Runtime'),('NativePreviewBuild.cs','Editor')]:
 write(OUT/'Assets'/sub/name,(ROOT/name).read_text(encoding='utf-8'))
shutil.copytree(Path('H:/MGFR/HandCoexist-20261019/Project/ProjectSettings'),OUT/'ProjectSettings')
write(OUT/'Packages/manifest.json',json.dumps({'dependencies':{f'com.unity.modules.{n}':'1.0.0' for n in ['imageconversion','jsonserialize','animation','imgui','inputlegacy']}}))
assets=ROOT/'assets-v1';model=json.loads((assets/'native-model.json').read_text(encoding='utf-8'));textureids={t['pathId']:t['file'] for t in model['textures']};materials=[]
for row in model['materials']:
 if '_lod_' in row['name']:continue
 p=row['properties']['m_SavedProperties'];env=next(e['second'] for e in p['m_TexEnvs'] if e['first']=='_BaseMap');texture=textureids.get(env['m_Texture']['m_PathID'])
 if texture is None:raise ValueError(row['name'])
 materials.append({'name':row['name'],'texture':texture,'scale':[env['m_Scale'][c] for c in 'xy'],'offset':[env['m_Offset'][c] for c in 'xy'],'color':[1,1,1,1],'cutoff':.05 if 'hair' in row['name'] else 0,'transparent':False})
write(assets/'preview-materials.json',json.dumps({'materials':materials},indent=2))
print(OUT)
