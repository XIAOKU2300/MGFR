"""Extract and bake original Si emotion presets into fixed native poses.

Outputs are exclusive-create only. Game input trees and the native motion
reference directory are read-only inputs.
"""
from pathlib import Path
import base64, hashlib, json, math, struct, sys, zlib
import numpy as np
from scipy.spatial.transform import Rotation

OUT = Path(__file__).resolve().parent
if any(p.name not in {"source", "motions", "expand_emotions.py"} for p in OUT.iterdir()):
    raise SystemExit(f"Refusing non-empty output directory: {OUT}")
SOURCE = OUT / "source"
MOTIONS = OUT / "motions"
for d in (SOURCE, MOTIONS):
    if not d.is_dir() or any(d.iterdir()):
        raise SystemExit(f"Refusing existing/non-empty output subdirectory: {d}")
ROOT = Path(r"H:\MGFR\EndfieldNativeMotions-20261019")
WORK = Path(r"H:\MGFR\work\si-animation-20261019")
sys.path.insert(0, str(WORK))
from extract_verified import connect, read_payload
from bundle_reader import Helper, read_bundle
from typetree_reader import tree_objects, read_object
from map_si_resources import string

def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# Resolve candidate paths through StringPathHash, manifest bundle index, and
# one exact VFS row. Never select an asset from its filename alone.
raw = next((WORK / "probe-payloads").glob("*_StringPathHash.bin")).read_bytes()
start, count = struct.unpack_from("<II", raw)
if start != 8 + count * 24: raise ValueError("Unsupported StringPathHash table")
selected = {}; cursor = start
for _ in range(count):
    n = struct.unpack_from("<I", raw, cursor)[0]
    path = string(raw, cursor)
    if path.lower().startswith("assets/beyond/dynamicassets/gamedata/skeletalmorph/skeletalmorphanim/emotion/") and path.lower().endswith(".asset"):
        selected[cursor-start] = {"path": path}
    cursor += n + 6
if cursor != len(raw): raise ValueError("StringPathHash trailing bytes")
path_hashes = {}
for i in range(count):
    offset, n = struct.unpack_from("<II", raw, 8 + i * 8)
    for j in range(n):
        _, h, p = struct.unpack_from("<IQI", raw, offset + j * 16)
        if p in selected: path_hashes.setdefault(h, []).append(selected[p])

data = (WORK / "verified-payloads/manifest-decoded.bin").read_bytes()
tables=[]; cursor=156
for width in (32, 56, 48):
    size,n=struct.unpack_from("<II",data,cursor)
    if size != 4+n*width: raise ValueError("Manifest table width mismatch")
    tables.append((cursor+8,n,width)); cursor += size+4
payload=cursor+4; asset_start,asset_count,_=tables[0]; asset_values=asset_start+asset_count*8
bundle_start,bundle_count,_=tables[2]
db=connect(); codec=Helper("BrotliServer.dll"); cipher=Helper("OfflineDecoder.dll")
records=[]; seen=set()
try:
    for i in range(asset_count):
        h,ptr,bundle,size,padding=struct.unpack_from("<QIIII",data,asset_values+i*24)
        if h not in path_hashes: continue
        p=payload+ptr; length=struct.unpack_from("<I",data,p)[0]
        actual=codec.decode(data[p+4:p+4+length]).decode("utf-16-le")
        matches=[x for x in path_hashes[h] if x["path"].lower()==actual.lower()]
        if len(matches)!=1: continue
        bundle_row=bundle_start+bundle*48
        ordinal,pointer,*_=struct.unpack_from("<6I",data,bundle_row)
        if ordinal!=bundle: raise ValueError("Bundle ordinal mismatch")
        bundle_name=string(data,payload+pointer)
        if bundle_name in seen: continue
        seen.add(bundle_name)
        rows=list(db.execute("select * from files where layer=? and name=?",("Persistent","Data/Bundles/Windows/"+bundle_name)))
        if len(rows)!=1: raise ValueError(f"Expected one VFS row for {bundle_name}, got {len(rows)}")
        packed=read_payload(rows[0]); nodes=read_bundle(packed,cipher)
        record={"path":actual,"bundle":bundle_name,"bundle_sha256":sha(packed),"vfs_md5":rows[0]["md5"],"vfs_md5_verified":True,"objects":[]}
        for cab,blob in nodes:
            if ".resS" in cab: continue
            for obj in tree_objects(blob):
                if obj["class_id"] != 114: continue
                value=read_object(obj)
                if not isinstance(value,dict) or "_pose" not in value: continue
                name=Path(actual).stem+"_"+str(obj["path_id"])+".json"
                dest=SOURCE/name
                write_json(dest,value)
                record["objects"].append({"class":obj["class_id"],"name":value.get("m_Name"),"file":name,"sha256":sha(dest.read_bytes())})
        records.append(record)
finally:
    codec.close(); cipher.close(); db.close()
if not records: raise ValueError("No exact original emotion assets decoded")
write_json(SOURCE/"source-manifest.json",records)

# Load original character mapping/rest contract.
model=json.loads((ROOT/"assets-v1/native-model.json").read_text(encoding="utf-8"))
avatar=json.loads((ROOT/"face-sources-v1/native-face-avatar-decoded.json").read_text(encoding="utf-8"))
data=avatar["data"]; refs={x["rid"]:x["data"] for x in avatar["references"]["RefIds"]}
mapping={n:refs[r["rid"]] for n,r in zip(data["morphMappingNames"],data["morphMappingCfgs"])}
lookup={zlib.crc32(n["name"].encode())&0xffffffff:i for i,n in enumerate(model["nodes"])}
base={b["boneNameHash"]&0xffffffff:b for b in data["basePoseConfig"]}
if len(base)!=97 or any(k not in lookup for k in base): raise ValueError("Face skeleton must map all 97 controls")
def v(o): return np.array([o[c] for c in "xyz"],dtype=np.float64)
def q(e): return Rotation.from_euler("xyz",np.asarray(e,dtype=float)*[1,-1,-1],degrees=True).as_quat()
errors=[np.degrees((Rotation.from_quat(q(v(b["rotation"]))).inv()*Rotation.from_quat(model["nodes"][lookup[k]]["q"])).magnitude()) for k,b in base.items()]
if max(errors)>.003: raise ValueError(f"Native rest pose mismatch: {max(errors)} degrees")

category_terms={"sad":["sad","cry","tear","sorrow"],"angry":["angry","anger","mad","rage"],"surprised":["surpris","shock","astonish"],"shy":["shy","embarrass","bashful"],"happy":["happy","smile","joy","laugh"],"thinking":["think","ponder"],"affection":["favour","affection","love","fond"],"neutral":["neutral","normal"]}
presets=[]; seen_weights={}
for rec in records:
    for obj in rec["objects"]:
        value=json.loads((SOURCE/obj["file"]).read_text(encoding="utf-8"))
        byctrl={}
        for key,items in value.get("_pose",{}).items():
            if isinstance(items,list):
                for item in items:
                    if isinstance(item,dict) and "_ctrlName" in item and "_value" in item:
                        n=item["_ctrlName"]; w=float(item["_value"])
                        byctrl[n]=byctrl.get(n,0.0)+w
        if not byctrl: continue
        missing=sorted(n for n,w in byctrl.items() if abs(w)>1e-12 and n not in mapping)
        if missing: continue
        if not any(abs(w)>1e-12 for w in byctrl.values()): continue
        key=tuple(sorted((n,round(w,10)) for n,w in byctrl.items() if abs(w)>1e-12))
        if key in seen_weights: continue
        seen_weights[key]=obj["file"]
        stem=Path(rec["path"]).stem.lower()
        # Some original names encode intent with suffixes, so classify from
        # both the exact path and Unity object name.
        search=stem+" "+str(value.get("m_Name","")).lower()
        categories=[c for c,terms in category_terms.items() if c!="neutral" and any(t in search for t in terms)]
        if not categories: continue
        presets.append({"source_face":obj["file"],"source_path":rec["path"],"label":value.get("m_Name",stem),"weights":byctrl,"categories":categories})

# Existing v5 presets count as available variants but are not copied or
# re-counted as new discoveries.
existing={"happy":[("happy_soft","face_happys.motion","Soft happy"),("happy","face_happym.motion","Happy"),("happy_big","face_happyl.motion","Big smile"),("happy_squint","face_happysquinta.motion","Squint smile")],"shy":[("shy","face_shya.motion","Shy")],"affection":[("affection","face_favoura.motion","Affection")]}
manifest={"format":"ENFMOT1","clips":[]}; catalog={c:[] for c in category_terms}
for emotion,items in existing.items():
    for variant,file,label in items:
        src=ROOT/"motions-v5"/file
        if not src.is_file(): continue
        catalog[emotion].append({"name":variant,"file":"../motions/"+file,"label":label,"existing":True})

# Generate a 2-frame fixed pose on the full model skeleton. First frame is the
# pose consumed by runtime; duplicate second frame keeps standard clip framing.
node_count=len(model["nodes"]); clips_written=[]; source_changes={}
for candidate in presets:
    cats=candidate["categories"]
    # Assign the most semantically specific category using the priority order.
    emotion=next((c for c in ("sad","angry","surprised","shy","happy","thinking","affection") if c in cats),None)
    if emotion is None: continue
    stem=Path(candidate["source_face"]).stem.replace("data_facialmorph_emotion_","")
    name=f"face_{emotion}_{stem}"
    if any(x["name"]==name for x in clips_written): continue
    delta={k:[np.zeros(3),np.zeros(3),np.zeros(3)] for k in base}
    for ctrl,weight in candidate["weights"].items():
        if abs(weight)<1e-12: continue
        for bone in mapping[ctrl]["bones"]:
            k=bone["boneNameHash"]&0xffffffff
            if k not in base: raise ValueError(f"Mapped control bone absent from 97 cfg: {k:08x}")
            delta[k][0]+=v(bone["position"])*weight
            delta[k][1]+=v(bone["rotation"])*weight
            delta[k][2]+=v(bone["scale"])*weight
    values=np.zeros((2,node_count,10),dtype=np.float64)
    # Rest skeleton from model; source cfg gives explicit face rest rotations.
    for i,node in enumerate(model["nodes"]):
        values[:,i,:4]=node["q"]; values[:,i,4:7]=node["t"]; values[:,i,7:10]=node["s"]
    changed=[]
    for k,b in base.items():
        i=lookup[k]; dp,dr,ds=delta[k]
        values[:,i,:4]=q(v(b["rotation"])+dr)
        values[:,i,4:7]=v(b["position"])+dp
        values[:,i,7:10]=v(b["scale"])+ds
        if np.linalg.norm(dp)+np.linalg.norm(dr)+np.linalg.norm(ds)>1e-8: changed.append(model["nodes"][i]["name"])
    if not np.isfinite(values).all(): raise ValueError(f"Non-finite pose: {name}")
    norms=np.linalg.norm(values[:,:,:4],axis=2)
    if not np.allclose(norms,1.0,atol=2e-5): raise ValueError(f"Invalid quaternion norm: {name}")
    # Require a real change from neutral and deduplicate identical baked poses.
    if not changed: continue
    pose_key=np.round(values[0],6).tobytes()
    if pose_key in source_changes: continue
    source_changes[pose_key]=name
    file=name+".motion"; path=MOTIONS/file
    with path.open("xb") as f:
        f.write(struct.pack("<8sIIf",b"ENFMOT1\0",node_count,2,60))
        f.write(values.astype("<f4").tobytes())
    clip={"name":name,"label":candidate["label"],"file":file,"frames":2,"fps":60,"duration":1/60,"emotion":emotion,"variant":stem,"source_face":candidate["source_path"],"changed_face_bones":len(changed)}
    manifest["clips"].append(clip); clips_written.append(clip)
    catalog[emotion].append({"name":stem,"file":"../motions/"+file,"label":candidate["label"],"source_face":candidate["source_path"],"changed_face_bones":len(changed),"existing":False})

# Neutral option is the exact cfg base pose baked onto the original skeleton.
neutral=np.zeros((2,node_count,10),dtype=np.float64)
for i,node in enumerate(model["nodes"]): neutral[:,i,:4]=node["q"]; neutral[:,i,4:7]=node["t"]; neutral[:,i,7:10]=node["s"]
neutral_name="face_neutral.motion"
with (MOTIONS/neutral_name).open("xb") as f:
    f.write(struct.pack("<8sIIf",b"ENFMOT1\0",node_count,2,60)); f.write(neutral.astype("<f4").tobytes())
neutral_clip={"name":"face_neutral","label":"Neutral","file":neutral_name,"frames":2,"fps":60,"duration":1/60,"emotion":"neutral","variant":"baseCfg","source_face":"native-face-avatar-decoded.json","changed_face_bones":0}
manifest["clips"].append(neutral_clip)
catalog["neutral"].append({"name":"neutral","file":"../motions/"+neutral_name,"label":"Neutral","existing":False})
write_json(MOTIONS/"manifest.json",manifest)
write_json(OUT/"catalog-emotions.json",{"emotions":[{"name":c,"variants":catalog[c]} for c in ("sad","happy","angry","surprised","shy","thinking","affection","neutral")]})

report={"candidate_assets":len(records),"decoded_emotion_objects":sum(len(r["objects"]) for r in records),"usable_distinct_presets":len(clips_written),"categories":{},"rest_rotation_max_error_degrees":max(errors),"face_bones":len(base),"model_nodes":node_count,"all_weights_mapped":True,"output_clips":len(manifest["clips"])}
for c,variants in catalog.items(): report["categories"][c]={"available_variants":len(variants),"new_variants":sum(not x.get("existing",False) for x in variants),"variants":[x["name"] for x in variants]}
write_json(OUT/"validation-report.json",report)
print(json.dumps(report,ensure_ascii=False,indent=2))
