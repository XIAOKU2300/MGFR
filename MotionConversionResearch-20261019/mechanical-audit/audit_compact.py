import collections,json,pathlib,struct
BASE=pathlib.Path(r'H:\MGFR\SiMotions-20261019'); OUT=pathlib.Path(r'H:\MGFR\MotionConversionResearch-20261019\mechanical-audit'); REPORT=OUT/'mechanical-audit-compact.md'
FMT=struct.Struct('<8sBHIIff'); BUFS=['RootMotionBufferData','FloatBufferData','TransformBufferData']
if REPORT.exists(): raise SystemExit(f'refuse overwrite: {REPORT}')
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def ranges(nums):
 nums=sorted(set(nums)); out=[]
 for n in nums:
  if not out or n>out[-1][1]+1: out.append([n,n])
  else: out[-1][1]=n
 return ','.join(str(a) if a==b else f'{a}-{b}' for a,b in out) or '(empty)'
def ixtext(ix): return ranges(ix)
sets={}; lines=['# Mechanical clip audit (compact)','', '机械字段统计；所有 decoded JSON 显式以 UTF-8 读取。无语义推断。对 RootMotion/Float/Transform buffer 各仅读首 27 字节并按 `<8sBHIIff` 解包。','']
for group,root,listing in [('main',BASE,BASE/'reports'/'clips.json'),('controller-linked',BASE/'controller-linked',BASE/'controller-linked'/'clips.json')]:
 entries=load(listing); rows=[]; tuple_occ=collections.Counter(); tuple_clip=collections.Counter(); ixsets=collections.Counter(); schemas=collections.Counter(); headers=collections.defaultdict(collections.Counter); binding_counts=collections.Counter()
 for e in entries:
  d=load(root/e['decoded']); binds=d.get('m_ClipBindingConstant',{}).get('genericBindings',[]); hist=collections.Counter((x.get('typeID'),x.get('customType'),x.get('attribute')) for x in binds)
  tuple_occ.update(hist); tuple_clip.update(hist.keys()); binding_counts[len(binds)]+=1
  ix=tuple(i for i,x in enumerate(binds) if x.get('typeID')==95 and x.get('customType')==8); ixsets[ix]+=1
  acl=d.get('m_AclCompressedBuffer'); schema=tuple(sorted(acl)) if isinstance(acl,dict) else type(acl).__name__; schemas[schema]+=1
  bmap=e.get('acl_buffers',{})
  for kind in BUFS:
   buf=bmap.get(kind); val='no-buffer'
   if buf:
    bp=root/buf['path']
    if bp.is_file():
     raw=bp.read_bytes()[:27]
     if len(raw)==27:
      v=FMT.unpack(raw); val=(v[0].hex(),*v[1:5],v[5],v[6])
     else: val=f'short:{len(raw)}'
    else: val='missing-file'
   headers[kind][val]+=1
  rows.append({'name':e.get('name',d.get('m_Name','')),'bindings':len(binds),'hist':hist,'ix':ix,'schema':schema})
 sets[group]=rows
 print(group,'clips',len(entries),'tuples',len(tuple_occ),'schema variants',len(schemas),'index sets',len(ixsets))
 lines += [f'## {group} ({len(entries)} clips)','',f'- distinct full binding distributions: {len(collections.Counter(tuple(sorted((str(k),v) for k,v in r["hist"].items())) for r in rows))}; genericBindings count range: {min(binding_counts)}..{max(binding_counts)}; modal counts: `{binding_counts.most_common(8)}`.','- `m_AclCompressedBuffer` schemas: '+ '; '.join(f'{n} clips: `{",".join(s)}`' for s,n in schemas.items()),'','### Generic binding tuples (tuple = typeID/customType/attribute; total occurrences / clips containing tuple)','','| tuple | occurrences | clips |','|---|---:|---:|']
 for k,n in sorted(tuple_occ.items(),key=lambda x:(str(x[0]))): lines.append(f'| `{k}` | {n} | {tuple_clip[k]} |')
 lines += ['','### Animator (typeID=95, customType=8) binding index sets; zero-based positions','','| index set, compact ranges | clips |','|---|---:|']
 for ix,n in sorted(ixsets.items(),key=lambda x:(-x[1],x[0])): lines.append(f'| `{ixtext(ix)}` | {n} |')
 lines += ['','### Buffer first-27-byte header variants','','| buffer | header (magic hex, fields in struct order) | clips |','|---|---|---:|']
 for kind in BUFS:
  for value,n in headers[kind].items(): lines.append(f'| {kind} | `{value}` | {n} |')
 lines += ['','Representative clips (3):']
 for r in rows[:3]: lines.append(f'- `{r["name"]}`: {r["bindings"]} bindings; Animator 95/8 indices `{ixtext(r["ix"])}`; schema key count {len(r["schema"])}.')
 lines += ['']
# cross-list requested actor cohort
actors=[r for rs in sets.values() for r in rs if r['name'].startswith('A_actor_')]; ixcount=collections.Counter(r['ix'] for r in actors); sigcount=collections.Counter(tuple(sorted((str(k),v) for k,v in r['hist'].items())) for r in actors); bindcount=collections.Counter(r['bindings'] for r in actors)
lines += ['## Cross-list A_actor_* cohort','','- Count: '+str(len(actors))+' (main '+str(sum(r['name'].startswith('A_actor_') for r in sets['main']))+'; controller-linked '+str(sum(r['name'].startswith('A_actor_') for r in sets['controller-linked']))+').',f'- Uniform complete binding distribution: {len(sigcount)==1} (distinct distributions {len(sigcount)}); uniform genericBindings count: {len(bindcount)==1} (counts {dict(bindcount)}).',f'- Uniform Animator 95/8 index set: {len(ixcount)==1} (distinct index sets {len(ixcount)}).','', '| Animator index set, compact ranges | clips |','|---|---:|']
for ix,n in sorted(ixcount.items(),key=lambda x:(-x[1],x[0])): lines.append(f'| `{ixtext(ix)}` | {n} |')
# name-only special buckets, keep categories disjoint by exact name prefix then literal keyword counts
allrows=[r for rs in sets.values() for r in rs]; names=[r['name'] for r in allrows];
lines += ['','## Name-only cohorts (no semantic inference)','',f'- `A_actor_*`: {sum(n.startswith("A_actor_") for n in names)}.',f'- names containing `npc`: {sum("npc" in n.lower() for n in names)}.',f'- names containing `monster`: {sum("monster" in n.lower() for n in names)}.',f'- names containing `face`, `expression`, `emot`, or `facial`: {sum(any(w in n.lower() for w in ("face","expression","emot","facial")) for n in names)}.',f'- Total listed rows (overlap across inventories retained): {len(allrows)}.','']
# print small useful summary
print('ACTORS',len(actors),'distinct full binding distributions',len(sigcount),'distinct binding counts',dict(bindcount),'distinct index sets',len(ixcount))
for g,rs in sets.items():
 names=[r['name'] for r in rs]; print('NAME_BUCKETS',g,'A_actor',sum(n.startswith('A_actor_') for n in names),'npc',sum('npc' in n.lower() for n in names),'monster',sum('monster' in n.lower() for n in names))
with REPORT.open('x',encoding='utf-8',newline='\n') as f: f.write('\n'.join(lines)+'\n')
print('REPORT',REPORT)
