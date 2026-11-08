import collections, json, pathlib, struct, sys

BASE = pathlib.Path(r'H:\MGFR\SiMotions-20261019')
OUT = pathlib.Path(r'H:\MGFR\MotionConversionResearch-20261019\mechanical-audit')
REPORT = OUT / 'mechanical-audit.md'
SCRIPT = OUT / 'audit.py'
if REPORT.exists():
    raise SystemExit(f'refusing to overwrite existing report: {REPORT}')
if SCRIPT.exists():
    raise SystemExit(f'refusing to overwrite existing script: {SCRIPT}')

GROUPS = [('main', BASE, BASE / 'reports' / 'clips.json'),
          ('controller-linked', BASE / 'controller-linked', BASE / 'controller-linked' / 'clips.json')]
FMT = struct.Struct('<8sBHIIff')

def jread(path):
    return json.loads(path.read_text(encoding='utf-8'))

def t(v):
    return tuple(v.get(k) for k in ('typeID', 'customType', 'attribute'))

allrows=[]
for group, root, listing in GROUPS:
    entries=jread(listing)
    counts=collections.Counter()
    special=collections.Counter()
    signatures=collections.Counter()
    schema=collections.Counter()
    headers=collections.Counter()
    missing=[]
    rows=[]
    for e in entries:
        p=root/e['decoded']
        d=jread(p)
        bindings=d.get('m_ClipBindingConstant',{}).get('genericBindings',[])
        dist=collections.Counter(t(x) for x in bindings)
        for k,v in dist.items(): counts[k]+=v
        ix=tuple(i for i,b in enumerate(bindings) if b.get('typeID')==95 and b.get('customType')==8)
        special[ix]+=1
        signatures[tuple(sorted(dist.items()))]+=1
        acl=d.get('m_AclCompressedBuffer')
        schema[tuple(sorted(acl.keys())) if isinstance(acl,dict) else type(acl).__name__]+=1
        buff=e.get('acl_buffers',{}).get('RootMotionBufferData')
        head='no-buffer'
        if buff:
            bp=root/buff['path']
            if bp.is_file():
                raw=bp.read_bytes()[:FMT.size]
                if len(raw)==FMT.size:
                    vals=FMT.unpack(raw)
                    head=(vals[0].hex(),*vals[1:5],vals[5],vals[6])
                else: head=f'short:{len(raw)}'
            else: head='missing-file'
        headers[head]+=1
        row={'group':group,'name':e.get('name',d.get('m_Name','')),'path':str(p),'bindings':len(bindings),'binding_distribution':dict((str(k),v) for k,v in dist.items()),'anim95_custom8_indices':ix,'acl_schema':sorted(acl.keys()) if isinstance(acl,dict) else type(acl).__name__,'rootmotion_head':head}
        rows.append(row); allrows.append(row)
    print('\nGROUP',group,'clips',len(entries),'type tuples',len(counts),'binding signatures',len(signatures),'schema variants',len(schema),'headers',len(headers))
    print('tuple counts',counts.most_common())
    print('anim95 custom8 index sets',special.most_common())
    print('schemas',schema.most_common())
    print('root headers top',headers.most_common(12))
    print('examples',[(r['name'],r['bindings'],r['anim95_custom8_indices'],r['acl_schema']) for r in rows[:3]])

# named cohort counts, overlap and uniformity by actual binding-distribution signature
bygroup=collections.defaultdict(list)
for r in allrows: bygroup[r['group']].append(r)
lines=['# Mechanical clip audit','', 'Read-only UTF-8 JSON inventory; no conversion semantics inferred. RootMotion header reads are limited to first 27 bytes (`<8sBHIIff`).', '']
for group, rows in bygroup.items():
    lines += [f'## {group}: {len(rows)} clips','']
    tup=collections.Counter()
    ixsets=collections.Counter()
    schemas=collections.Counter()
    heads=collections.Counter()
    sig=collections.Counter()
    for r in rows:
        for k,v in r['binding_distribution'].items(): tup[k]+=v
        ixsets[r['anim95_custom8_indices']]+=1
        schemas[tuple(r['acl_schema']) if isinstance(r['acl_schema'],list) else r['acl_schema']]+=1
        heads[str(r['rootmotion_head'])]+=1
        sig[tuple(sorted(r['binding_distribution'].items()))]+=1
    lines += ['### Generic binding tuple totals', '', '| typeID | customType | attribute | bindings |','|---:|---:|---:|---:|']
    for k,n in sorted(tup.items()):
        typ,custom,attr=eval(k,{'__builtins__':{}},{})
        lines.append(f'| {typ} | {custom} | {attr} | {n} |')
    lines += ['', '### Animator typeID=95, customType=8: binding index sets','', '| indices (zero-based) | clips |','|---|---:|']
    for ix,n in sorted(ixsets.items(),key=lambda x:(-x[1],x[0])): lines.append(f'| `{ix}` | {n} |')
    lines += ['', f'ACL schema variants: `{dict(schemas)}`. Distinct complete per-clip binding distributions: {len(sig)}.', '', 'RootMotion first-27-byte header variants (hex magic, then unpacked values):']
    for h,n in heads.most_common(): lines.append(f'- `{h}`: {n} clips')
    # representative clips, one per common schema/binding shape
    lines += ['', 'Representative clips:']
    for r in rows[:3]: lines.append(f"- `{r['name']}`: {r['bindings']} genericBindings; Animator 95/8 indices `{r['anim95_custom8_indices']}`; ACL keys `{r['acl_schema']}`; root header `{r['rootmotion_head']}`")
    lines += ['']
# A_actor* cohorts and requested special buckets, based solely on names.
for group, rows in bygroup.items():
    actors=[r for r in rows if r['name'].startswith('A_actor_')]
    others=[r for r in rows if not r['name'].startswith('A_actor_')]
    by_ix=collections.Counter(r['anim95_custom8_indices'] for r in actors)
    by_bind=collections.Counter(tuple(sorted(r['binding_distribution'].items())) for r in actors)
    monsters=[r for r in others if any(x in r['name'].lower() for x in ('monster','boss','enemy'))]
    expr=[r for r in rows if any(x in r['name'].lower() for x in ('expression','face','facial','emoji'))]
    lines += [f'## Named cohorts: {group}', '', f'- `A_actor_*`: {len(actors)} clips; Animator 95/8 index-set variants: {dict(by_ix)}; full binding-distribution variants: {len(by_bind)}.', f'- Non-`A_actor_*`: {len(others)} clips.', f'- Monster/boss/enemy name matches among non-actor names: {len(monsters)}.', f'- Expression/face/facial/emoji name matches: {len(expr)}.', '']
# pooled results
lines += ['## Pooled totals and examples','', f'- Total listed clips: {len(allrows)}.', f'- A_actor clips across both inventories: {sum(r["name"].startswith("A_actor_") for r in allrows)}.', '- Inventory overlap is not deduplicated; both lists are reported as supplied.', '', 'Examples (up to 5):']
for r in allrows[:5]: lines.append(f"- `{r['group']}` / `{r['name']}` — {r['bindings']} bindings; indices `{r['anim95_custom8_indices']}`; header `{r['rootmotion_head']}`")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\nREPORT',REPORT)
