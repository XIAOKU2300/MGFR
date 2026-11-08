import collections,csv,json,pathlib
BASE=pathlib.Path(r'H:\MGFR\SiMotions-20261019'); OUT=pathlib.Path(r'H:\MGFR\MotionConversionResearch-20261019\mechanical-audit\focused-selection-v1'); REPORT=OUT/'focused-selection.md'; CSV=OUT/'actor-candidates.csv'
if REPORT.exists() or CSV.exists(): raise SystemExit('refuse to overwrite an existing output')
KEYS=['idle','relax','walk','wave','nod','shake','scratchhead','receive_gift','camera','tsundere','play']
EXCLUDE=['battle','cloth','hair','lookat']
CATS={'idle':'待机','relax':'放松/待机','walk':'行走','wave':'挥手/动作','nod':'点头/动作','shake':'摇头/动作','scratchhead':'挠头/动作','receive_gift':'收礼/动作','camera':'镜头/动作','tsundere':'傲娇表情/动作','play':'玩耍/动作'}
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def scan_curve(curve, attrs, sample):
 if isinstance(curve,dict):
  for k,v in curve.items():
   if k.lower()=='attribute' and isinstance(v,(str,int,float)): attrs[str(v)]+=1
   if isinstance(v,(dict,list)): scan_curve(v,attrs,sample)
 elif isinstance(curve,list):
  for x in curve: scan_curve(x,attrs,sample)
rows=[]; npc_rows=[]
for group,root,listing in [('main',BASE,BASE/'reports/clips.json'),('controller-linked',BASE/'controller-linked',BASE/'controller-linked/clips.json')]:
 for e in load(listing):
  name=e.get('name',''); d=load(root/e['decoded']);
  if group=='main' and 'npc' in name.lower(): npc_rows.append((root,e,d))
  if not name.startswith('A_actor_'): continue
  # Keep only generic jsspsi actors and controller-linked actor clips.
  if group!='controller-linked' and 'jsspsi' not in name.lower(): continue
  keys=[k for k in KEYS if k in name.lower()]
  if not keys or any(x in name.lower() for x in EXCLUDE): continue
  duration=round(float(e.get('stop',0))-float(e.get('start',0)),6)
  bmap=e.get('acl_buffers') or {}
  fields={k.lower():v for k,v in d.items()}
  add=[k for k in ('additive','isadditive') if k in name.lower() or k in fields]
  virt=[k for k in ('virtual','isvirtual') if k in name.lower() or k in fields]
  # Report only explicit markers; do not infer independent playability.
  def marker(words):
   hits=[]
   if any(w in name.lower() for w in words): hits.append('name')
   hits.extend(k for k in d if any(w in k.lower() for w in words))
   return ','.join(hits) if hits else 'not marked in name/top-level fields'
  rows.append({'name':name,'categories':'; '.join(f'{k}={CATS[k]}' for k in keys),'source_list':group,'source_bundle':e.get('source_bundle',''),'duration_seconds':duration,'additive_marker':marker(['additive']),'virtual_marker':marker(['virtual']),'acl':';'.join(sorted(bmap)) if bmap else 'none in listing','decoded':e.get('decoded',''),'bindings':len(d.get('m_ClipBindingConstant',{}).get('genericBindings',[]))})
# Aggregate m_FloatCurves across 663 main npc rows; preserve literal attribute keys only.
attrs=collections.Counter(); nonempty=0; facial=[]; curve_examples=[]
for root,e,d in npc_rows:
 curves=d.get('m_FloatCurves',[])
 if curves: nonempty+=1
 for c in curves:
  before=sum(attrs.values()); scan_curve(c,attrs,None)
  if len(curve_examples)<5 and len(curve_examples)<len(curves): curve_examples.append({'clip':d.get('m_Name',e.get('name')),'curve':c})
# Search typeID 4 binding paths and any curve text that literally identifies facial fields.
for root,e,d in npc_rows:
 for b in d.get('m_ClipBindingConstant',{}).get('genericBindings',[]):
  if b.get('typeID')==4:
   pathval=b.get('path')
   if isinstance(pathval,str) and any(w in pathval.lower() for w in ('face','eye','brow','mouth','cheek')) and len(facial)<20:
    facial.append((d.get('m_Name',e.get('name')),pathval,b.get('attribute')))
# report and CSV are new files; CSV created exclusively
with CSV.open('x',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0].keys()) if rows else ['name']); w.writeheader(); w.writerows(rows)
lines=['# Focused actor clip selection','','Mechanical name filter only. Candidate inclusion does not establish that additive or virtual clips can be played independently.','',f'- Actor candidates: {len(rows)}.',f'- Lists: {dict(collections.Counter(r["source_list"] for r in rows))}.',f'- Candidate clips with any listed ACL buffer: {sum(r["acl"]!="none in listing" for r in rows)}.',f'- Main-list `npc` rows examined for float curves: {len(npc_rows)}.',f'- Those with nonempty decoded `m_FloatCurves`: {nonempty}.',f'- Distinct literal `attribute` values in `m_FloatCurves`: {len(attrs)}.',f'- typeID 4 facial-path examples exposed as strings in generic binding records: {len(facial)}. Integer/hash path values are not interpreted as names.','', '## Candidate counts by category keyword','']
by=collections.Counter(k for r in rows for k in [part.split('=')[0] for part in r['categories'].split('; ')])
for k in KEYS: lines.append(f'- `{k}` ({CATS[k]}): {by[k]}')
lines += ['', '## Candidate list','', '| name | category keyword(s) | source list / bundle | duration (s) | additive marker | virtual marker | ACL buffer keys | binding count |','|---|---|---|---:|---|---|---|---:|']
for r in rows: lines.append(f"| `{r['name']}` | {r['categories']} | {r['source_list']} / `{r['source_bundle']}` | {r['duration_seconds']} | {r['additive_marker']} | {r['virtual_marker']} | {r['acl']} | {r['bindings']} |")
lines += ['', '## 663 `npc` rows: literal FloatCurve attribute values','','| attribute value | occurrences |','|---|---:|']
for k,n in attrs.most_common(): lines.append(f'| `{k}` | {n} |')
lines += ['', '### Representative decoded float curve objects','']
for x in curve_examples: lines.append(f"- `{x['clip']}`: `{json.dumps(x['curve'],ensure_ascii=False)[:600]}`")
lines += ['', '### typeID 4 facial path string examples','']
if facial:
 for x in facial: lines.append(f'- `{x}`')
else: lines.append('- None: matching generic binding path fields were numeric values, so no facial names were guessed from hashes.')
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('candidates',len(rows),collections.Counter(r['source_list'] for r in rows),'candidate acl',sum(r['acl']!='none in listing' for r in rows))
print('npc rows',len(npc_rows),'nonempty float curves',nonempty,'attribute values',len(attrs),'examples',attrs.most_common(20),'facial',facial[:5])
print('REPORT',REPORT,'CSV',CSV)
