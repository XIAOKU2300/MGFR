from pathlib import Path
import hashlib, json, math, shutil, struct, time
import numpy as np

ROOT = Path(r"H:\MGFR\SiLLMBridge-20261020")
OUT = ROOT / "MainData"
NATIVE = ROOT.parent / "EndfieldNativeMotions-20261019"
EXPANSION = ROOT / "motion-expansion"
MODEL = NATIVE / "assets-v1" / "native-model.json"
OLD_MOTIONS = NATIVE / "motions-v5"
OLD_FACE = NATIVE / "source-face-audit-v1.json"
NEW_MOTIONS = EXPANSION / "motions"
NEW_CATALOG = EXPANSION / "catalog-extra.json"

OLD_IDS = [
    ("base_idle", "Base Idle", "idle", ["idle", "base"]),
    ("walk", "Walk", "walk", ["walk", "locomotion"]),
    ("play", "Play", "play", ["playful", "interaction"]),
    ("tsundere", "Tsundere", "tsundere", ["attitude", "dialogue"]),
    ("wave", "Wave", "greeting", ["greeting", "wave"]),
    ("idle", "Dialogue Idle", "idle", ["idle", "dialogue"]),
    ("nod", "Nod", "nod", ["acknowledgement", "head"]),
    ("shake_head", "Shake Head", "shake_head", ["refusal", "head"]),
    ("walk_and_settle", "Walk and Settle", "walk_and_settle", ["walk", "transition"]),
    ("scratch_head", "Scratch Head", "confused", ["confused", "scratch_head"]),
    ("camera_pose", "Camera Pose", "camera_pose", ["pose", "camera"]),
    ("receive_gift", "Receive Gift", "receive_gift", ["interaction", "gift"]),
    ("relaxed_idle", "Relaxed Idle", "idle", ["idle", "relaxed"]),
    ("idle_special_1", "Idle Special 1", "idle", ["idle", "variation"]),
    ("idle_special_2", "Idle Special 2", "idle", ["idle", "variation"]),
    ("walk_special", "Special Walk", "walk_special", ["walk", "variation"]),
]
NEW_IDS = [
    ("arms_crossed", "Arms Crossed", "arms_crossed", ["arms_crossed", "pose"]),
    ("ponder", "Ponder", "thinking", ["thinking", "ponder"]),
    ("point", "Point", "point", ["pointing", "gesture"]),
    ("surprised_pose", "Surprised Pose", "surprised_pose", ["surprised", "pose"]),
    ("talk_hands", "Talk Hands", "explain", ["explain", "hands"]),
    ("introduce", "Introduce", "greeting", ["greeting", "introduce"]),
    ("scratch_head_start", "Scratch Head Start", "confused", ["confused", "scratch_head", "start"]),
    ("think", "Think", "thinking", ["thinking", "think"]),
    ("relax_react", "Relax React", "relax_react", ["relax", "reaction"]),
    ("settle", "Settle to Relax", "settle", ["settle", "transition"]),
]
OLD_SOURCE_NAMES = [
    "A_actor_girl_idle_loop", "A_actor_girl_walk_loop",
    "A_actor_jsspsi_dialog_single_play", "A_actor_jsspsi_dialog_single_tsundere",
    "A_actor_jsspsi_dialog_single_wave", "A_actor_jsspsi_dialog_state_idle_loop",
    "A_actor_jsspsi_dialog_virtual_single_idle_nod", "A_actor_jsspsi_dialog_virtual_single_idle_shake",
    "A_actor_jsspsi_dialog_virtual_single_walk_m", "A_actor_jsspsi_dialog_virtual_state_scratchhead_loop",
    "A_actor_jsspsi_interact_camera_01", "A_actor_jsspsi_interact_receive_gift",
    "A_actor_jsspsi_relax_loop", "A_actor_jsspsi_relax_sp_01",
    "A_actor_jsspsi_relax_sp_02", "A_actor_jsspsi_walk_loop_sp_01",
]
NEW_SOURCE_NAMES = [
    "A_actor_jsspsi_dialog_state_chesthugging1_loop",
    "A_actor_jsspsi_dialog_state_muse_loop",
    "A_actor_jsspsi_dialog_state_point_loop",
    "A_actor_jsspsi_dialog_state_surprise_loop",
    "A_actor_jsspsi_dialog_virtual_single_idle_talkhands",
    "A_actor_jsspsi_dialog_virtual_state_introduction_loop",
    "A_actor_jsspsi_dialog_virtual_state_scratchhead_start",
    "A_actor_jsspsi_dialog_virtual_state_think1_loop",
    "A_actor_jsspsi_relax_react", "A_actor_jsspsi_idle_to_relax",
]
TARGETS = [
    ("Bip001_Pelvis", "下半身"),
    ("Bip001_Spine", "上半身"), ("Bip001_Spine1", "上半身1"), ("Bip001_Spine2", "上半身2"),
    ("Bip001_Neck", "首"), ("Bip001_Head", "頭"),
    ("Bip001_L_Clavicle", "左肩"), ("Bip001_L_UpperArm", "左腕"),
    ("Bip001_L_Forearm", "左ひじ"), ("Bip001_L_Hand", "左手首"),
    ("Bip001_R_Clavicle", "右肩"), ("Bip001_R_UpperArm", "右腕"),
    ("Bip001_R_Forearm", "右ひじ"), ("Bip001_R_Hand", "右手首"),
    ("Bip001_L_Thigh", "左足"), ("Bip001_L_Calf", "左ひざ"),
    ("Bip001_L_Foot", "左足首"), ("Bip001_L_Toe0", "左つま先"),
    ("Bip001_R_Thigh", "右足"), ("Bip001_R_Calf", "右ひざ"),
    ("Bip001_R_Foot", "右足首"), ("Bip001_R_Toe0", "右つま先"),
]

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def create_json(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")

def validate_motion(path, entry):
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f"truncated file: {path}")
    magic, bones, frames, fps = struct.unpack_from("<8sIIf", raw)
    if magic != b"ENFMOT1\0" or bones != 596 or frames != entry["frames"] or fps != entry["fps"]:
        raise ValueError(f"header mismatch: {path}")
    if len(raw) != 20 + bones * frames * 10 * 4:
        raise ValueError(f"size mismatch: {path}")
    data = np.frombuffer(raw, dtype="<f4", offset=20).reshape(frames, bones, 10)
    if not np.isfinite(data).all():
        raise ValueError(f"non-finite values: {path}")
    qnorm = np.linalg.norm(data[:, :, :4], axis=2)
    max_q_error = float(np.max(np.abs(qnorm - 1.0)))
    if max_q_error > 2e-5:
        raise ValueError(f"non-unit quaternions ({max_q_error}): {path}")
    return {"file": str(path), "bytes": len(raw), "sha256": sha256(path),
            "bones": bones, "frames": frames, "fps": fps,
            "finite": True, "max_quaternion_norm_error": max_q_error}

def main():
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite existing output directory: {OUT}")
    for p in [MODEL, OLD_MOTIONS / "manifest.json", OLD_FACE, NEW_MOTIONS / "manifest.json", NEW_CATALOG]:
        if not p.is_file():
            raise SystemExit(f"Missing required source file: {p}")

    old_manifest = load_json(OLD_MOTIONS / "manifest.json")
    new_manifest = load_json(NEW_MOTIONS / "manifest.json")
    if old_manifest.get("errors"):
        raise ValueError("Old source manifest has errors")
    if new_manifest.get("errors"):
        raise ValueError("Expansion source manifest has errors")
    old_clips = {c["name"]: c for c in old_manifest["clips"]}
    new_clips = {c["name"]: c for c in new_manifest["clips"]}
    old_faces = {c["name"]: c["moving_face_bones"] for c in load_json(OLD_FACE)["clips"]}
    new_catalog = {c["name"]: c for c in load_json(NEW_CATALOG)}
    if len(old_clips) != len(old_manifest["clips"]) or len(new_clips) != len(new_manifest["clips"]):
        raise ValueError("Duplicate source names in a source manifest")
    if len(OLD_IDS) != 16 or len(NEW_IDS) != 10:
        raise ValueError("Short ID configuration must contain 16 + 10 actions")
    if [n for n in OLD_SOURCE_NAMES if n not in old_clips] or [n for n in NEW_SOURCE_NAMES if n not in new_clips]:
        raise ValueError("One or more configured source motion names are missing")

    nodes = load_json(MODEL)["nodes"]
    node_by_name = {}
    for i, node in enumerate(nodes):
        node_by_name.setdefault(node["name"], []).append(i)
    mapping = []
    for source_name, target_name in TARGETS:
        indices = node_by_name.get(source_name, [])
        if len(indices) != 1:
            raise ValueError(f"Expected one exact source leaf {source_name}; found {len(indices)}")
        idx = indices[0]
        node = nodes[idx]
        if node.get("name") != source_name or not node.get("path", "").split("/")[-1] == source_name:
            raise ValueError(f"Non-leaf/exact-name mapping rejected: {source_name}")
        mapping.append({"source": idx, "target_name": target_name})
    if len(mapping) != 22 or len({x["source"] for x in mapping}) != 22 or len({x["target_name"] for x in mapping}) != 22:
        raise ValueError("Bone mapping is not a unique 22-entry map")

    rows = []
    for short, label, family, tags, source_name, source in [
        (cfg[0], cfg[1], cfg[2], cfg[3], src, old_clips[src]) for cfg, src in zip(OLD_IDS, OLD_SOURCE_NAMES)
    ]:
        rows.append((short, label, family, tags, source_name, source, OLD_MOTIONS / source["file"], old_faces.get(source_name, 0)))
    for cfg, source_name in zip(NEW_IDS, NEW_SOURCE_NAMES):
        short, label, family, tags = cfg
        source = new_clips[source_name]
        extra = new_catalog.get(source_name)
        if extra is None:
            raise ValueError(f"Missing expansion face catalog entry: {source_name}")
        rows.append((short, label, family, tags, source_name, source, NEW_MOTIONS / source["file"], int(extra["原版面部变化骨骼数"])))

    ids = [r[0] for r in rows]
    names = [r[4] for r in rows]
    files = [r[5]["file"] for r in rows]
    if len(rows) != 26 or len(set(ids)) != 26 or len(set(names)) != 26 or len(set(files)) != 26:
        raise ValueError("Expected 26 unique action IDs, source names, and filenames")
    if any(not label.isascii() for _, label, *_ in rows):
        raise ValueError("English labels must contain ASCII only")

    # Validate every source before creating any destination.
    source_checks = []
    for short, label, family, tags, source_name, entry, source_path, face_count in rows:
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        source_checks.append(validate_motion(source_path, entry))

    OUT.mkdir()
    motions_dir = OUT / "motions"
    motions_dir.mkdir()
    clips = []
    actions = []
    file_checks = []
    for row in rows:
        short, label, family, tags, source_name, entry, source_path, face_count = row
        dest = motions_dir / entry["file"]
        with source_path.open("rb") as src, dest.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        result = validate_motion(dest, entry)
        result["short_id"] = short
        file_checks.append(result)
        clips.append({"name": short, "source_name": source_name, "label": label,
                      "file": entry["file"], "duration": entry["duration"],
                      "frames": entry["frames"], "fps": entry["fps"], "loop": bool(entry["loop"])})
        actions.append({"name": short, "label": label, "file": entry["file"],
                        "duration": entry["duration"], "tags": tags, "family": family,
                        "callable": True, "native_face_active": face_count > 15,
                        "native_face_moving_bones": face_count})

    source_rig = {
        "source": str(MODEL),
        "format": "native-model-nodes-v1",
        "nodes": [{k: node[k] for k in ("name", "parent", "t", "q", "s", "path")} for node in nodes],
        "mapping": mapping,
        "mapping_notes": [
            "Mappings are exact source-name leaf matches only; target names are Japanese PMX骨格 names supplied for the 828-bone target project.",
            "Pelvis maps to 下半身 as a rotational anchor; do not transfer source pelvis translation.",
            "No finger mapping was added because no exact native finger-node naming survey was performed.",
            "This mapping is a handoff contract; retargeting and axis calibration remain the main project's responsibility.",
        ],
    }
    catalog = {"actions": actions}
    manifest = {"format": "ENFMOT1", "notes": [
        "26 original Endfield native-rig motions copied without conversion: 16 from motions-v5, 10 from motion-expansion.",
        "Short action IDs are the public names; source_name preserves the original native clip identifier.",
        "Motion data remains on the 596-node source rig. Retargeting to the Japanese-name 828-bone PMX target is not performed here.",
    ], "clips": clips, "errors": []}
    create_json(motions_dir / "manifest.json", manifest)
    create_json(OUT / "body-catalog.json", catalog)
    create_json(OUT / "source-rig.json", source_rig)
    receipt = {
        "status": "PASS", "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "output": str(OUT), "source_motion_count": 26, "copied_motion_count": len(file_checks),
        "old_count": 16, "expansion_count": 10, "manifest_errors": len(manifest["errors"]),
        "source_rig_node_count": len(nodes), "target_mapping_count": len(mapping),
        "target_rig": "HandCoexist-20261019 Japanese-name PMX, 828 bones; retargeting not done",
        "files": file_checks,
    }
    create_json(OUT / "NEWmain-data-receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "actions": len(clips), "nodes": len(nodes),
                      "mapping": len(mapping), "output": str(OUT)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
