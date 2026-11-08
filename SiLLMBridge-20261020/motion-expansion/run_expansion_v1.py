from pathlib import Path
import hashlib, json, math, struct, subprocess, sys, time

HERE = Path(__file__).resolve().parent
NATIVE = Path(r"H:\MGFR\EndfieldNativeMotions-20261019")
PYTHON = Path(r"C:\Program Files\Python312\python.exe")
SOLVER = HERE / "solve_native_body_expansion_v1.py"
PREPARE = HERE / "prepare_native_motion_expansion_v1.py"
BODY_OUT = HERE / "body-solved-v2"
MOTION_OUT = HERE / "motions"
CATALOG = HERE / "catalog-extra.json"
RESULT = HERE / "execution-result-v1.json"
LOG = HERE / "execution-log-v1.txt"
SELECTION = json.loads((HERE / "selection-v1.json").read_text(encoding="utf-8"))
DESCRIPTIONS = {
 "A_actor_jsspsi_dialog_virtual_state_introduction_loop": "角色处于介绍交流状态的循环身体动作；名称只说明状态，不保证含口型或特定台词。",
 "A_actor_jsspsi_dialog_virtual_single_idle_talkhands": "带手部动作的对话身体片段；具体手势以动作数据为准。",
 "A_actor_jsspsi_dialog_virtual_state_think1_loop": "思考状态循环动作；不推断具体情绪或视线方向。",
 "A_actor_jsspsi_dialog_virtual_state_scratchhead_start": "挠头动作的起始片段，适合短促困惑或迟疑反应；只包含起始段。",
 "A_actor_jsspsi_dialog_state_surprise_loop": "惊讶状态循环身体动作；名称不代表额外粒子或表情控制。",
 "A_actor_jsspsi_dialog_state_chesthugging1_loop": "抱臂姿势循环动作；身体姿态按原始动作保留。",
 "A_actor_jsspsi_dialog_state_point_loop": "指向状态循环动作；具体指向方向不根据名字推定。",
 "A_actor_jsspsi_dialog_state_muse_loop": "沉思状态循环动作；名称不保证出现特定面部表情。",
 "A_actor_jsspsi_relax_react": "放松相关的反应片段；作为单次反应播放较合适。",
 "A_actor_jsspsi_idle_to_relax": "从站立闲置进入放松状态的过渡动作。",
}
TAGS = SELECTION["labels"]

def refuse_existing_outputs():
    existing = [str(p) for p in [BODY_OUT, MOTION_OUT, CATALOG, RESULT, LOG] if p.exists()]
    if existing:
        raise SystemExit("Refusing to overwrite existing output(s): " + ", ".join(existing))
    if not PYTHON.is_file():
        raise SystemExit("Configured Python executable not found: " + str(PYTHON))

def run_one(script):
    proc = subprocess.run([str(PYTHON), "-X", "utf8", str(script)], cwd=str(HERE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    log_parts.append("$ " + str(script.name) + "\n" + proc.stdout + proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"{script.name} failed with exit code {proc.returncode}")
    return proc.stdout

refuse_existing_outputs()
started = time.perf_counter()
log_parts = []
run_one(SOLVER)
prepare_stdout = run_one(PREPARE)
manifest_path = MOTION_OUT / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest.get("errors"):
    raise RuntimeError("Manifest contains conversion errors")
expected = set(SELECTION["selected_names"])
actual = {c["name"] for c in manifest.get("clips", [])}
if actual != expected:
    raise RuntimeError(f"Manifest clip set mismatch: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
checks = []
for clip in manifest["clips"]:
    path = MOTION_OUT / clip["file"]
    raw = path.read_bytes()
    if len(raw) < 20:
        raise RuntimeError("Truncated motion: " + str(path))
    magic, bones, frames, fps = struct.unpack_from("<8sIIf", raw)
    expected_bytes = 20 + bones * frames * 10 * 4
    values = memoryview(raw)[20:]
    if magic != b"ENFMOT1\0" or bones != 596 or frames != clip["frames"] or len(raw) != expected_bytes:
        raise RuntimeError("Motion header/size validation failed: " + clip["name"])
    import numpy as np
    arr = np.frombuffer(values, dtype="<f4")
    if not np.isfinite(arr).all():
        raise RuntimeError("Non-finite motion data: " + clip["name"])
    checks.append({"name": clip["name"], "bone_count": bones, "frames": frames, "fps": fps, "finite": True, "bytes": len(raw)})

catalog = []
for c in manifest["clips"]:
    meta = TAGS[c["name"]]
    catalog.append({
        "name": c["name"], "label": meta["label"], "中文说明": DESCRIPTIONS[c["name"]],
        "语义tags": meta["tags"], "duration": c["duration"], "loop": c["loop"],
        "原版面部变化骨骼数": c["moving_face_bones"],
        "原版面部通道数": c["source_facial_component_tracks_checked"],
        "file": c["file"],
    })
with CATALOG.open("x", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)
with LOG.open("x", encoding="utf-8") as f:
    f.write("\n".join(log_parts))
result = {
 "status": "PASS", "selected_count": len(checks), "manifest_errors": len(manifest.get("errors", [])),
 "all_motions_finite": True, "bone_count_per_motion": 596,
 "clips": checks, "catalog": str(CATALOG), "manifest": str(manifest_path),
 "solver_script_sha256": hashlib.sha256(SOLVER.read_bytes()).hexdigest(),
 "prepare_script_sha256": hashlib.sha256(PREPARE.read_bytes()).hexdigest(),
 "elapsed_seconds": round(time.perf_counter() - started, 3),
}
with RESULT.open("x", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
