"""Convert the 祀 PMX into the intermediate the Unity importer reads.

Usage::

    python -I convert_si.py "H:\\MGFR\\...\\祀.pmx" "H:\\MGFR\\converted\\si"

The original model directory is opened read-only; every byte this writes goes to
the output directory, which is gitignored (``/converted/`` in .gitignore).

Why this exists rather than the documented Blender route
-------------------------------------------------------

``tools/model-conversion.md`` names Blender + MMD Tools -> FBX as the only
supported path. Blender is not installed on this machine, so that route is
blocked. Rather than wait for a toolchain install, this script plus
``Assets/MGFR/Editor/SiCharacterImporter.cs`` reimplement the *intent* of that
route offline and repeatably: read the PMX directly, write an intermediate, and
build a real Unity mesh from it, leaving the original untouched. The deviation is
recorded in that document.

Outputs
-------

``si_model.json``
    Everything that is small and human-readable: names, materials, bone
    hierarchy, morph inventory, resolved texture mapping, and the measured
    evidence behind the scale and winding decisions.
``si_model.bin``
    The bulk arrays, little-endian, in a fixed order that the JSON's ``counts``
    block describes. Binary rather than JSON because 63,503 vertices x four skin
    influences through a JSON parser is slow and round-trips floats badly.
``textures/``
    The textures the materials actually reference, copied out of the read-only
    model directory.
``report.txt``
    The same summary that goes to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import sys

# ``-I`` keeps this script's directory off sys.path, and the reader is the one
# module imported from here. Putting it back keeps the script runnable in the
# isolated mode it is meant to be run in.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pmx_reader import MORPH_MATERIAL, MORPH_VERTEX, read_pmx  # noqa: E402

# ---------------------------------------------------------------------------
# Decisions, each with the evidence that settled it
# ---------------------------------------------------------------------------

#: MMD's conventional unit. MMD models are authored at roughly 20 units for a
#: 1.6 m figure, i.e. 1 unit ~ 0.08 m. This is a convention, not a measurement,
#: so the resulting height is printed and should be eyeballed against the scene.
MMD_UNIT_TO_METRE = 0.08

#: Which way round Unity winds a front-facing triangle, measured on this exact
#: editor build by ``MGFR.BatchProbe.WindingProbe`` (see tools/pmx/README.md).
#: A front face is the one whose normal points *towards* the viewer, so with a
#: counter-clockwise convention ``cross(p1 - p0, p2 - p0)`` points along the
#: outward normal. The converter measures how many PMX triangles already agree
#: with their own vertex normals and flips only if Unity disagrees with that.
UNITY_FRONT_IS_COUNTER_CLOCKWISE = True

#: The morph names the runtime drives, taken from the actual model rather than
#: guessed. Recorded here so the importer and the runtime agree on one spelling.
VOWEL_SHAPES = ["あ", "い", "う", "え", "お"]
BLINK_SHAPE = "まばたき"
CLOSED_MOUTH_SHAPE = "ん"
BLUSH_MATERIAL_MORPH = "照れ"

BINARY_MAGIC = 0x5346474D  # "MGFS" little-endian
BINARY_VERSION = 1


def classify_morph(name: str, morph_type: int) -> str:
    """Label a morph so the report says what each one is *for*.

    docs/constraints.md #5 asks for morphs to be classified one at a time rather
    than treated as an undifferentiated pile of BlendShapes, because a material
    morph animated as a BlendShape would silently do nothing while looking
    implemented.
    """
    if morph_type == MORPH_MATERIAL:
        return "material (NOT a BlendShape)"
    if morph_type != MORPH_VERTEX:
        return "non-vertex"

    if name in VOWEL_SHAPES:
        return "lip sync: vowel"
    if name == BLINK_SHAPE:
        return "lip sync/eyes: blink"
    if name == CLOSED_MOUTH_SHAPE:
        return "lip sync: closed mouth"
    if "ウィンク" in name or "ｳｨﾝｸ" in name:
        return "eyes: wink"
    if name in ("上", "下", "じと目", "ｷﾘｯ", "瞳小", "ハイライト消"):
        return "eyes: pupil/lid"
    if name in ("口角上げ", "口角下げ", "口横広げ", "口横狭め", "にっこり", "にこり",
                "にやり", "にやり２", "笑い", "ぺろっ", "てへぺろ", "ω", "ω□",
                "▲", "∧", "ワ", "あ２"):
        return "mouth: expression"
    if name in ("真面目", "怒り", "困る", "なごみ", "びっくり", "恐ろしい子！"):
        return "brows: expression"
    return "other"


def resolve_texture(model_dir: str, declared: str) -> tuple[str, str | None]:
    """Find where a texture the PMX declares actually lives.

    The model declares paths like ``textures/T_actor_jsspsi_body_01_N.png`` but
    that one is not in ``textures/`` at all — it ships in ``other tex/``. Copying
    it into ``textures/`` and calling the problem solved would hide the fact that
    the model's own paths are inconsistent, so the mapping is resolved explicitly
    and reported instead.

    Returns ``(route, absolute_path_or_None)``.
    """
    relative = declared.replace("\\", "/")
    basename = os.path.basename(relative)

    direct = os.path.join(model_dir, *relative.split("/"))
    if os.path.isfile(direct):
        return "declared path", direct

    fallback = os.path.join(model_dir, "other tex", basename)
    if os.path.isfile(fallback):
        return "other tex/ fallback", fallback

    # Last resort: the file may be in a subdirectory that does not match the
    # declared prefix. Case-insensitive because Windows paths in PMX files are
    # written by whatever tool authored them.
    wanted = basename.lower()
    for root, _dirs, files in os.walk(model_dir):
        for name in files:
            if name.lower() == wanted:
                return f"found under {os.path.relpath(root, model_dir)}", os.path.join(root, name)

    return "MISSING", None


def duplicate_texture_report(model_dir: str, declared_names: list[str]) -> list[str]:
    """Note textures that exist in both ``textures/`` and ``other tex/``.

    Several diffuse maps ship in both, at different sizes. The declared path wins
    because substituting a different file than the model asks for would be a
    silent change to the asset; but the difference is worth reporting, because it
    is the sort of thing that later reads as "the textures look wrong".
    """
    lines: list[str] = []
    primary = os.path.join(model_dir, "textures")
    other = os.path.join(model_dir, "other tex")
    if not (os.path.isdir(primary) and os.path.isdir(other)):
        return lines

    for name in sorted({os.path.basename(d.replace("\\", "/")) for d in declared_names}):
        a = os.path.join(primary, name)
        b = os.path.join(other, name)
        if os.path.isfile(a) and os.path.isfile(b):
            sa, sb = os.path.getsize(a), os.path.getsize(b)
            mark = "IDENTICAL" if sa == sb else "DIFFERENT"
            lines.append(f"  {name}: textures/={sa} B, other tex/={sb} B  -> {mark}")
    return lines


def bone_world_positions(model) -> list[tuple[float, float, float]]:
    """Accumulate PMX bone positions into model space.

    A PMX bone position is an offset from its parent, and a bone's rest pose has
    no rotation, so the world position is just the sum along the parent chain.
    That also means every bind pose is a pure translation, which the report
    asserts rather than assumes.
    """
    count = len(model.bones)
    world: list[tuple[float, float, float] | None] = [None] * count

    for start in range(count):
        if world[start] is not None:
            continue
        chain: list[int] = []
        index = start
        while index >= 0 and world[index] is None:
            if index in chain:
                raise ValueError(f"bone parent cycle at index {index}")
            chain.append(index)
            parent = model.bones[index].parent_index
            if parent >= count:
                raise ValueError(f"bone {index} has out-of-range parent {parent}")
            index = parent

        # ``index`` is now either -1 (root reached) or a bone already resolved.
        base = (0.0, 0.0, 0.0) if index < 0 else world[index]
        for bone_index in reversed(chain):
            offset = model.bones[bone_index].position
            base = (base[0] + offset[0], base[1] + offset[1], base[2] + offset[2])
            world[bone_index] = base

    return [w if w is not None else (0.0, 0.0, 0.0) for w in world]


def material_ranges(model) -> list[tuple[int, int]]:
    """``(indexStart, indexCount)`` per material, in draw order."""
    ranges: list[tuple[int, int]] = []
    start = 0
    for material in model.materials:
        ranges.append((start, material.face_index_count))
        start += material.face_index_count
    return ranges


def winding_evidence(model, flip: bool) -> tuple[float, int]:
    """Measure how many triangles agree with their own vertex normals.

    Returns ``(fraction_agreeing, triangle_count)``. A value near 1 means the PMX
    indices are already wound the way its normals imply; near 0 means they are
    the other way round. Combined with the measured Unity convention this decides
    whether the indices have to be reversed.
    """
    positions = model.positions
    normals = model.normals
    indices = model.indices
    triangles = len(indices) // 3

    agreeing = 0
    sampled = 0
    # Every 7th triangle is plenty for a ratio and keeps this instant on a
    # 73k-triangle mesh.
    for t in range(0, triangles, 7):
        i0, i1, i2 = indices[3 * t], indices[3 * t + 1], indices[3 * t + 2]
        p0, p1, p2 = positions[i0], positions[i1], positions[i2]

        ax, ay, az = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        bx, by, bz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        cx = ay * bz - az * by
        cy = az * bx - ax * bz
        cz = ax * by - ay * bx

        nx = normals[i0][0] + normals[i1][0] + normals[i2][0]
        ny = normals[i0][1] + normals[i1][1] + normals[i2][1]
        nz = normals[i0][2] + normals[i1][2] + normals[i2][2]

        if cx * nx + cy * ny + cz * nz > 0:
            agreeing += 1
        sampled += 1

    return (agreeing / sampled if sampled else 0.0), triangles


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pmx", help="path to the source .pmx (opened read-only)")
    parser.add_argument("outdir", nargs="?", default=r"H:\MGFR\converted\si",
                        help="output directory (gitignored)")
    parser.add_argument("--scale", type=float, default=MMD_UNIT_TO_METRE,
                        help="metres per PMX unit (default: the MMD convention, 0.08)")
    parser.add_argument("--flip-winding", dest="flip", action="store_true", default=None,
                        help="force reversal of the triangle winding")
    parser.add_argument("--no-flip-winding", dest="flip", action="store_false",
                        help="force leaving the triangle winding alone")
    args = parser.parse_args(argv[1:])

    pmx_path = os.path.abspath(args.pmx)
    out_dir = os.path.abspath(args.outdir)
    model_dir = os.path.dirname(pmx_path)

    report: list[str] = []

    def say(line: str = "") -> None:
        report.append(line)

    model = read_pmx(pmx_path)
    scale = args.scale

    say("祀 PMX -> Unity intermediate")
    say("=" * 64)
    say(f"source     : {pmx_path}")
    say(f"output     : {out_dir}")
    say(f"model name : {model.name!r} / {model.name_en!r}")
    say(f"counts     : {len(model.positions)} vertices, {model.triangle_count} triangles, "
        f"{len(model.materials)} materials, {len(model.bones)} bones, {len(model.morphs)} morphs")
    say()

    # ---- winding ---------------------------------------------------------

    agreement, triangle_count = winding_evidence(model, False)
    pmx_is_ccw = agreement > 0.5
    if args.flip is None:
        # Flip exactly when the PMX order disagrees with what Unity treats as
        # front-facing.
        flip = pmx_is_ccw != UNITY_FRONT_IS_COUNTER_CLOCKWISE
        decided_by = "measured"
    else:
        flip = args.flip
        decided_by = "forced on the command line"

    say("Triangle winding")
    say(f"  PMX triangles whose cross product agrees with their vertex normals: "
        f"{agreement * 100:.1f}% of {triangle_count} (sampled every 7th)")
    say(f"  => PMX indices are {'counter-clockwise' if pmx_is_ccw else 'clockwise'} relative to their normals")
    say(f"  => Unity front faces are "
        f"{'counter-clockwise' if UNITY_FRONT_IS_COUNTER_CLOCKWISE else 'clockwise'} "
        f"(measured on this editor build by MGFR.BatchProbe.WindingProbe)")
    say(f"  => reversing the indices: {'YES' if flip else 'no'}  ({decided_by})")
    say()

    # ---- textures --------------------------------------------------------

    say("Textures")
    texture_files: list[dict] = []
    copy_plan: dict[str, str] = {}
    for index, declared in enumerate(model.textures):
        route, resolved = resolve_texture(model_dir, declared)
        basename = os.path.basename(declared.replace("\\", "/"))
        entry = {
            "index": index,
            "declared": declared,
            "route": route,
            "file": basename if resolved else None,
            "bytes": os.path.getsize(resolved) if resolved else None,
        }
        texture_files.append(entry)
        say(f"  {index:>2}  {declared}")
        say(f"       -> {route}: {resolved if resolved else 'NOT FOUND'}")
        if resolved:
            existing = copy_plan.get(basename)
            if existing and existing != resolved:
                raise SystemExit(
                    f"two different textures share the basename {basename!r}: "
                    f"{existing} and {resolved}. Rename one before converting."
                )
            copy_plan[basename] = resolved
    say()

    duplicates = duplicate_texture_report(model_dir, model.textures)
    if duplicates:
        say("  Textures present in BOTH textures/ and other tex/, at different sizes.")
        say("  The declared path wins; the higher-resolution copy is left unused on purpose.")
        report.extend(duplicates)
        say()

    # ---- geometry --------------------------------------------------------

    positions = [(p[0] * scale, p[1] * scale, p[2] * scale) for p in model.positions]

    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    zs = [p[2] for p in positions]
    raw_ys = [p[1] for p in model.positions]

    say("Scale")
    say(f"  metres per PMX unit : {scale}  (MMD convention)")
    say(f"  raw height          : {max(raw_ys) - min(raw_ys):.3f} units")
    say(f"  scaled height       : {max(ys) - min(ys):.3f} m")
    say(f"  scaled bounds x     : {min(xs):.3f} .. {max(xs):.3f}")
    say(f"  scaled bounds y     : {min(ys):.3f} .. {max(ys):.3f}")
    say(f"  scaled bounds z     : {min(zs):.3f} .. {max(zs):.3f}")
    say()

    # Per-material bounds. The model's raw z reaches 13 units, which is far more
    # than a standing figure needs, so which material owns that is worth knowing
    # before blaming the converter.
    say("Per-material bounds (scaled metres), widest z first")
    ranges = material_ranges(model)
    per_material_bounds = []
    for index, (start, count) in enumerate(ranges):
        if count == 0:
            continue
        used = model.indices[start:start + count]
        mx = [positions[i][0] for i in used]
        my = [positions[i][1] for i in used]
        mz = [positions[i][2] for i in used]
        per_material_bounds.append({
            "index": index,
            "name": model.materials[index].name,
            "x": [min(mx), max(mx)],
            "y": [min(my), max(my)],
            "z": [min(mz), max(mz)],
        })
    for entry in sorted(per_material_bounds, key=lambda e: -e["z"][1])[:6]:
        say(f"  {entry['name']:<12} z {entry['z'][0]:>7.3f} .. {entry['z'][1]:>7.3f}   "
            f"x {entry['x'][0]:>7.3f} .. {entry['x'][1]:>7.3f}   y {entry['y'][0]:>7.3f} .. {entry['y'][1]:>7.3f}")
    say()

    # ---- bones -----------------------------------------------------------

    world = bone_world_positions(model)
    world_scaled = [(w[0] * scale, w[1] * scale, w[2] * scale) for w in world]

    root_bones = sum(1 for b in model.bones if b.parent_index < 0)
    ik_bones = sum(1 for b in model.bones if b.is_ik)
    say("Bones")
    say(f"  {len(model.bones)} bones, {root_bones} with no parent, {ik_bones} IK bones")
    say(f"  bind poses are pure translations (no rest rotation) by construction")
    say(f"  root bones will be placed at:")
    for index, bone in enumerate(model.bones):
        if bone.parent_index < 0:
            say(f"    [{index}] {bone.name!r} -> {world_scaled[index]}")
    say()

    # ---- morphs ----------------------------------------------------------

    say("Morphs, classified (constraint #5: one at a time, not as a pile)")
    blend_shapes = []
    material_morphs = []
    for index, morph in enumerate(model.morphs):
        kind = classify_morph(morph.name, morph.morph_type)
        if morph.morph_type == MORPH_VERTEX:
            detail = f"{len(morph.vertex_offsets)} vertices"
            blend_shapes.append({
                "index": index,
                "name": morph.name,
                "nameEn": morph.name_en,
                "panel": morph.panel,
                "classification": kind,
                "vertexCount": len(morph.vertex_offsets),
            })
        elif morph.morph_type == MORPH_MATERIAL:
            detail = f"materials {morph.material_targets}"
            material_morphs.append({
                "index": index,
                "name": morph.name,
                "panel": morph.panel,
                "classification": kind,
                "offsets": [
                    {
                        "material": off.material_index,
                        "calcMode": off.calc_mode,
                        "diffuse": list(off.diffuse),
                        "specular": list(off.specular),
                        "specularStrength": off.specular_strength,
                        "ambient": list(off.ambient),
                        "edgeColor": list(off.edge_color),
                        "edgeSize": off.edge_size,
                        "textureTint": list(off.texture_tint),
                        "sphereTint": list(off.sphere_tint),
                        "toonTint": list(off.toon_tint),
                    }
                    for off in morph.material_offsets
                ],
            })
        else:
            detail = f"{morph.other_offset_count} offsets"
        say(f"  {index:>3}  {morph.type_name:<9} {morph.name!r:<16} {kind:<28} {detail}")
    say()
    say(f"  {len(blend_shapes)} vertex morphs become real BlendShapes; "
        f"{len(material_morphs)} material morph(s) do NOT.")
    for entry in material_morphs:
        for off in entry["offsets"]:
            say(f"    {entry['name']!r} -> material {off['material']} "
                f"({model.materials[off['material']].name}) calcMode={off['calcMode']} "
                f"diffuse={off['diffuse']}")
    say()

    # ---- write -----------------------------------------------------------

    os.makedirs(out_dir, exist_ok=True)
    texture_out = os.path.join(out_dir, "textures")
    os.makedirs(texture_out, exist_ok=True)
    for basename, source in sorted(copy_plan.items()):
        shutil.copy2(source, os.path.join(texture_out, basename))

    indices = list(model.indices)
    if flip:
        for i in range(0, len(indices) - 2, 3):
            indices[i + 1], indices[i + 2] = indices[i + 2], indices[i + 1]

    bin_path = os.path.join(out_dir, "si_model.bin")
    write_binary(bin_path, model, positions, indices, world_scaled, ranges, blend_shapes, scale)

    metadata = {
        "formatVersion": 1,
        "generatedBy": "tools/pmx/convert_si.py",
        "source": {
            "pmx": pmx_path,
            "modelName": model.name,
            "modelNameEn": model.name_en,
            "comment": model.comment.strip()[:400],
        },
        "unitScale": scale,
        "coordinateNote": (
            "MMD and Unity are both left-handed, Y up, Z forward, so no axis swap is "
            "applied. UV V is flipped (v_unity = 1 - v_pmx) because PMX texture space "
            "has its origin at the top left."
        ),
        "winding": {
            "flipped": flip,
            "pmxAgreementFraction": agreement,
            "unityFrontIsCounterClockwise": UNITY_FRONT_IS_COUNTER_CLOCKWISE,
            "evidence": "MGFR.BatchProbe.WindingProbe on Unity " + "6000.3.26f1",
        },
        "counts": {
            "vertices": len(positions),
            "indices": len(indices),
            "bones": len(model.bones),
            "materials": len(model.materials),
            "textures": len(texture_files),
            "blendShapes": len(blend_shapes),
            "materialMorphs": len(material_morphs),
        },
        "boundsScaled": {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        },
        "binaryLayout": [
            "float32 x3 x vertices   positions",
            "float32 x3 x vertices   normals",
            "float32 x2 x vertices   uvs (V already flipped)",
            "uint16  x4 x vertices   bone indices",
            "float32 x4 x vertices   bone weights (normalised)",
            "uint32  x  indices      triangles",
            "float32 x16 x bones     bind poses, row-major m00..m33",
            "uint32  x2 x materials  (indexStart, indexCount)",
            "per blend shape in blendShapes order: uint32 x n vertex indices, then float32 x3 x n deltas",
        ],
        "textures": texture_files,
        "materials": [
            {
                "index": i,
                "name": m.name,
                "nameEn": m.name_en,
                "texture": m.texture_index,
                "textureFile": (texture_files[m.texture_index]["file"]
                                if 0 <= m.texture_index < len(texture_files) else None),
                "diffuse": list(m.diffuse),
                "specular": list(m.specular),
                "specularStrength": m.specular_strength,
                "ambient": list(m.ambient),
                "drawFlags": m.draw_flag,
                "isTwoSided": m.is_two_sided,
                "edgeColor": list(m.edge_color),
                "edgeSize": m.edge_size,
                "sphereMode": m.sphere_mode,
                "sharedToon": m.shared_toon,
                "toonIndex": m.toon_index,
                "faceIndexCount": m.face_index_count,
                "indexStart": ranges[i][0],
            }
            for i, m in enumerate(model.materials)
        ],
        "bones": [
            {
                "index": i,
                "name": b.name,
                "nameEn": b.name_en,
                "parent": b.parent_index,
                # Absolute model-space position, used to build the inverse bind
                # matrix. Not for setting the transform: a bone's localPosition
                # must be the parent-relative offset, which is what localScaled
                # carries. Subtracting two absolute positions would work but
                # loses precision down the deeper chains.
                "positionScaled": list(world_scaled[i]),
                "localScaled": [b.position[0] * scale, b.position[1] * scale, b.position[2] * scale],
                "deformLayer": b.deform_layer,
                "isIk": b.is_ik,
                "inheritParent": b.inherit_parent_index,
                "inheritWeight": b.inherit_weight,
            }
            for i, b in enumerate(model.bones)
        ],
        "blendShapes": blend_shapes,
        "materialMorphs": material_morphs,
        "runtimeHints": {
            "vowelShapes": VOWEL_SHAPES,
            "blinkShape": BLINK_SHAPE,
            "closedMouthShape": CLOSED_MOUTH_SHAPE,
            "blushMaterialMorph": BLUSH_MATERIAL_MORPH,
        },
    }

    json_path = os.path.join(out_dir, "si_model.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=1)

    say("Written")
    for name in sorted(os.listdir(out_dir)):
        path = os.path.join(out_dir, name)
        if os.path.isfile(path):
            say(f"  {name:<20} {os.path.getsize(path):>12,} bytes")
        else:
            count = len(os.listdir(path))
            say(f"  {name + '/':<20} {count:>12,} files")
    say()

    text = "\n".join(report)
    with open(os.path.join(out_dir, "report.txt"), "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    print(text)
    return 0


def write_binary(path, model, positions, indices, world_scaled, ranges, blend_shapes, scale) -> None:
    """Write the bulk arrays. Order and types are mirrored in the JSON metadata."""
    vertex_count = len(positions)

    with open(path, "wb") as handle:
        handle.write(struct.pack("<II", BINARY_MAGIC, BINARY_VERSION))

        handle.write(struct.pack(f"<{vertex_count * 3}f", *[c for p in positions for c in p]))
        handle.write(struct.pack(f"<{vertex_count * 3}f", *[c for n in model.normals for c in n]))

        # PMX texture space has its origin top-left, Unity's bottom-left.
        uvs = [(u, 1.0 - v) for (u, v) in model.uvs]
        handle.write(struct.pack(f"<{vertex_count * 2}f", *[c for uv in uvs for c in uv]))

        # Unity's BoneWeight needs a positive, normalised sum; a PMX vertex whose
        # weights do not add to one would otherwise skin wrong rather than loudly.
        bad_sums = 0
        bone_indices: list[int] = []
        bone_weights: list[float] = []
        for i in range(vertex_count):
            index_row = model.bone_indices[i]
            weight_row = model.bone_weights[i]
            total = sum(weight_row)
            if total <= 1e-6:
                bad_sums += 1
                weight_row = (1.0, 0.0, 0.0, 0.0)
                index_row = (max(index_row[0], 0), 0, 0, 0)
                total = 1.0
            elif abs(total - 1.0) > 1e-3:
                bad_sums += 1
            for slot in range(4):
                bone_indices.append(max(index_row[slot], 0))
                bone_weights.append(weight_row[slot] / total)

        handle.write(struct.pack(f"<{len(bone_indices)}H", *bone_indices))
        handle.write(struct.pack(f"<{len(bone_weights)}f", *bone_weights))
        handle.write(struct.pack(f"<{len(indices)}I", *indices))

        # Bind poses: bone world position is a pure translation, so the inverse
        # bind matrix is the same translation negated. Written row-major.
        bindposes: list[float] = []
        for x, y, z in world_scaled:
            bindposes.extend([1.0, 0.0, 0.0, -x,
                              0.0, 1.0, 0.0, -y,
                              0.0, 0.0, 1.0, -z,
                              0.0, 0.0, 0.0, 1.0])
        handle.write(struct.pack(f"<{len(bindposes)}f", *bindposes))

        submesh: list[int] = []
        for start, count in ranges:
            submesh.extend([start, count])
        handle.write(struct.pack(f"<{len(submesh)}I", *submesh))

        for shape in blend_shapes:
            morph = model.morphs[shape["index"]]
            offsets = morph.vertex_offsets
            handle.write(struct.pack(f"<{len(offsets)}I", *[index for index, _ in offsets]))
            handle.write(struct.pack(f"<{len(offsets) * 3}f",
                                     *[c * scale for _, delta in offsets for c in delta]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
