import collections,json,pathlib,struct
B=pathlib.Path(r'H:\MGFR\SiMotions-20261019'); O=pathlib.Path(r'H:\MGFR\MotionConversionResearch-20261019\mechanical-audit'); OUT=O/'audit-final.md'; F=struct.Struct('<8sBHIIff'); KINDS=['RootMotionBufferData','FloatBufferData','TransformBufferData']
if OUT.exists(): raise SystemExit('refuse overwrite')
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def cr(nums):
 s=sorted(set(nums)); a=[]
 for n in s:
  if not a or n>a[-1][1]+1:a.append([n,n])
  else:a[-1][1]=n
 return ','.join(str(x) if x==y else f'{x}-{y}' for x,y in a) or '(empty)'
groups=[('main',B,B/'reports/clips.json'),('controller-linked',B/'controller-linked',B/'controller-linked/clips.json')]; R={}; L=['# Mechanical clip audit summary','','UTF-8 JSON reads; no semantic interpretation. For each buffer type, only bytes 0..26 are read and unpacked as `<8sBHIIff`; magic is counted separately from remaining fields.','']
for name,root,listing in groups:
 entries=read(listing); rows=[]; tuples=collections.Counter(); cliptypes=collections.Counter(); schemas=collections.Counter(); hdr={k:collections.Counter() for k in KINDS}; bcounts=collections.Counter(); avail={k:collections.Counter() for k in KINDS}
 for e in entries:
  d=read(root/e['decoded']); bs=d.get('m_ClipBindingConstant',{}).get('genericBindings',[]); dist=collections.Counter((x.get('typeID'),x.get('customType'),x.get('attribute')) for x in bs); tuples.update(dist); cliptypes.update(dist.keys()); bcounts[len(bs)]+=1
  acl=d.get('m_AclCompressedBuffer'); schemas[tuple(sorted(acl)) if isinstance(acl,dict) else type(acl).__name__]+=1
  for k in KINDS:
   bf=e.get('acl_buffers',{}).get(k); value='no-buffer'
   if bf:
    p=root/bf['path']
    if p.is_file():
     raw=p.read_bytes()[:27]
     if len(raw)==27:
      z=F.unpack(raw); value=(z[1],z[2],z[3],z[4],z[5],z[6]); avail[k]['read']+=1
     else: value=f'short:{len(raw)}'; avail[k]['short']+=1
    else:value='missing'; avail[k]['missing']+=1
   else:avail[k]['absent']+=1
   hdr[k][value]+=1
  ix=tuple(i for i,x in enumerate(bs) if x.get('typeID')==95 and x.get('customType')==8)
  rows.append({'name':e.get('name',d.get('m_Name','')),'n':len(bs),'dist':dist,'ix':ix,'schema':tuple(sorted(acl)) if isinstance(acl,dict) else type(acl).__name__})
 R[name]=rows
 L += [f'## {name}: {len(rows)} clips','',f'- GenericBindings count: min {min(bcounts)}, max {max(bcounts)}; full binding-count histogram `{dict(sorted(bcounts.items()))}`.',f'- m_AclCompressedBuffer schemas: `{dict(schemas)}`.',f'- Distinct per-clip typeID/customType/attribute distributions: {len(set(tuple(sorted((str(k),v) for k,v in r["dist"].items())) for r in rows))}.','', '### Type tuple counts','','| typeID/customType/attribute | binding occurrences | clips containing tuple |','|---|---:|---:|']
 for k,n in sorted(tuples.items(),key=lambda x:str(x[0])):L.append(f'| `{k}` | {n} | {cliptypes[k]} |')
 ixsets=collections.Counter(r['ix'] for r in rows)
 L+=['','### Animator 95/8 zero-based genericBindings index sets','','| indices (contiguous ranges) | clips |','|---|---:|']
 for ix,n in sorted(ixsets.items(),key=lambda x:(-x[1],x[0])):L.append(f'| `{cr(ix)}` | {n} |')
 L+=['','### 27-byte buffer header fields (excluding 8-byte magic)','', 'Unpacked fields shown as `(B,H,I,I,f,f)`; exact 8-byte magic varies per buffer and is omitted from grouping.','']
 for k in KINDS:
  L += [f'**{k}**: {dict(avail[k]) or {"absent":len(rows)}}', '', '| remaining header fields | clips |','|---|---:|']
  for v,n in hdr[k].most_common():L.append(f'| `{v}` | {n} |')
 L+=['','Representative clips:']
 for r in rows[:3]:L.append(f'- `{r["name"]}`: {r["n"]} bindings; Animator 95/8 indices `{cr(r["ix"])}`; schema keys {len(r["schema"])}.')
 L.append('')
actors=[r for rs in R.values() for r in rs if r['name'].startswith('A_actor_')]; full=collections.Counter(tuple(sorted((str(k),v) for k,v in r['dist'].items())) for r in actors); count=collections.Counter(r['n'] for r in actors); aix=collections.Counter(r['ix'] for r in actors)
L+=['## Cross-list A_actor_* cohort','','- Total 338 clips: main 133, controller-linked 205.',f'- Uniform full typeID/customType/attribute distribution: {len(full)==1}; distinct distributions {len(full)}.',f'- Uniform total genericBindings count: {len(count)==1}; counts frequency `{count.most_common(15)}`.',f'- Uniform Animator 95/8 index set: {len(aix)==1}; distinct index sets {len(aix)}.','', '| Animator 95/8 index set, ranges | clips |','|---|---:|']
for ix,n in sorted(aix.items(),key=lambda x:(-x[1],x[0])):L.append(f'| `{cr(ix)}` | {n} |')
allnames=[r['name'] for rs in R.values() for r in rs]
L+=['','## Name-based separate cohorts','','| literal name criterion | clips |','|---|---:|',f'| starts `A_actor_` | {sum(n.startswith("A_actor_") for n in allnames)} |',f'| contains `npc` | {sum("npc" in n.lower() for n in allnames)} |',f'| contains `monster` | {sum("monster" in n.lower() for n in allnames)} |',f'| contains `face`, `expression`, `emot`, or `facial` | {sum(any(w in n.lower() for w in ("face","expression","emot","facial")) for n in allnames)} |','', 'Inventory rows are not deduplicated across the two lists.']
with OUT.open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(L)+'\n')
print('actor count',len(actors),'full patterns',len(full),'binding-count varieties',len(count),'index-set variants',len(aix))
for name,rs in R.items():print(name,'clip count',len(rs),'binding tuples',len(collections.Counter(k for r in rs for k in r['dist'])))
print('report',OUT)
