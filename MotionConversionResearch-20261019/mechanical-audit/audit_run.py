import collections, json, pathlib, struct
BASE=pathlib.Path(r'H:\MGFR\SiMotions-20261019'); OUT=pathlib.Path(r'H:\MGFR\MotionConversionResearch-20261019\mechanical-audit'); REPORT=OUT/'mechanical-audit.md'
if REPORT.exists(): raise SystemExit(f'refusing to overwrite {REPORT}')
FMT=struct.Struct('<8sBHIIff')
GROUPS=[('main',BASE,BASE/'reports'/'clips.json'),('controller-linked',BASE/'controller-linked',BASE/'controller-linked'/'clips.json')]
def read(p): return json.loads(p.read_text(encoding='utf-8'))
rows_by={}; lines=['# Mechanical clip audit','','Read-only UTF-8 JSON inventory. No conversion semantics inferred. RootMotion header reads only the first 27 bytes (`<8sBHIIff`).','']
for group,root,listing in GROUPS:
    entries=read(listing); rows=[]; tuples=collections.Counter(); ixsets=collections.Counter(); schemas=collections.Counter(); heads=collections.Counter(); signatures=collections.Counter()
    for e in entries:
        p=root/e['decoded']; d=read(p); bindings=d.get('m_ClipBindingConstant',{}).get('genericBindings',[])
        dist=collections.Counter((b.get('typeID'),b.get('customType'),b.get('attribute')) for b in bindings)
        tuples.update(dist); ix=tuple(i for i,b in enumerate(bindings) if b.get('typeID')==95 and b.get('customType')==8); ixsets[ix]+=1
        acl=d.get('m_AclCompressedBuffer'); schema=tuple(sorted(acl)) if isinstance(acl,dict) else type(acl).__name__; schemas[schema]+=1
        buf=e.get('acl_buffers',{}).get('RootMotionBufferData'); head='no-buffer'
        if buf:
            bp=root/buf['path']
            if bp.is_file():
                raw=bp.read_bytes()[:FMT.size]
                if len(raw)==FMT.size:
                    v=FMT.unpack(raw); head=(v[0].hex(),*v[1:5],v[5],v[6])
                else: head=f'short:{len(raw)}'
            else: head='missing-file'
        heads[head]+=1; sig=tuple(sorted((str(k),v) for k,v in dist.items())); signatures[sig]+=1
        rows.append({'name':e.get('name',d.get('m_Name','')),'bindings':len(bindings),'ix':ix,'schema':schema,'head':head,'dist':dist})
    rows_by[group]=rows
    print('GROUP',group,'clips',len(entries),'binding variants',len(signatures),'schemas',schemas)
    print('TUPLES',tuples.most_common()); print('IDX',ixsets.most_common()); print('HEADS',heads.most_common(20))
    lines += [f'## {group}: {len(rows)} clips','','### genericBindings tuple totals','','| typeID | customType | attribute | count |','|---:|---:|---:|---:|']
    for (typ,custom,attr),n in sorted(tuples.items(),key=lambda x:(str(x[0]))): lines.append(f'| {typ} | {custom} | {attr} | {n} |')
    lines += ['','### Animator typeID=95, customType=8 zero-based index sets','','| index set | clips |','|---|---:|']
    for ix,n in sorted(ixsets.items(),key=lambda x:(-x[1],x[0])): lines.append(f'| `{ix}` | {n} |')
    lines += ['',f'ACL schema variants: `{dict(schemas)}`. Distinct complete generic binding distributions: {len(signatures)}.','', 'RootMotion header variants (hex magic, remaining unpacked fields):']
    for h,n in heads.most_common(): lines.append(f'- `{h}`: {n} clips')
    lines += ['','Representative clips:']
    for r in rows[:3]: lines.append(f"- `{r['name']}`: {r['bindings']} genericBindings; indices `{r['ix']}`; schema `{r['schema']}`; header `{r['head']}`")
    actors=[r for r in rows if r['name'].startswith('A_actor_')]; non=[r for r in rows if not r['name'].startswith('A_actor_')]
    a_ix=collections.Counter(r['ix'] for r in actors); a_sig=collections.Counter(tuple(sorted((str(k),v) for k,v in r['dist'].items())) for r in actors)
    monster=[r for r in non if any(x in r['name'].lower() for x in ('monster','boss','enemy'))]
    expr=[r for r in rows if any(x in r['name'].lower() for x in ('expression','face','facial','emoji'))]
    lines += ['',f'### Name cohorts','',f'- `A_actor_*`: {len(actors)} clips; index-set distribution `{dict(a_ix)}`; distinct binding distributions {len(a_sig)}.',f'- Non-`A_actor_*`: {len(non)} clips.',f'- Monster/boss/enemy name matches within non-actor clips: {len(monster)}.',f'- Expression/face/facial/emoji name matches: {len(expr)}.','']
    print('ACTORS',len(actors),'actor idx',a_ix,'actor sig count',len(a_sig),'nonactor',len(non),'monster matches',len(monster),'expressions',len(expr))
lines += ['## Representative clips (up to five per inventory)','']
for group,rows in rows_by.items():
    for r in rows[:5]: lines.append(f"- `{group}` / `{r['name']}` — {r['bindings']} bindings; indices `{r['ix']}`; schema `{r['schema']}`; header `{r['head']}`")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('REPORT',REPORT)
