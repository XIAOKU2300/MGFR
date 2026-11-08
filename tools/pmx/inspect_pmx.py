"""Read a PMX file and print what is in it.

Usage::

    python -I inspect_pmx.py "H:\\MGFR\\...\\祀.pmx"

This is the sanity check for the reader. ``tools/model-conversion.md`` records
static counts for this model (about 73,000 triangles, 14 materials, 828 bones,
41 morphs, of which ``照れ`` is a material morph). If the numbers printed here
do not match, the reader is wrong and nothing downstream can be trusted, so the
counts are the point of the exercise rather than a nicety.
"""

from __future__ import annotations

import os
import sys

# ``-I`` keeps the script's own directory off sys.path, and this module is the
# one place the reader is imported from. Putting it back explicitly keeps the
# script runnable under isolation, which is how it is meant to be run against a
# file that came from outside the project.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pmx_reader import MORPH_MATERIAL, MORPH_VERTEX, read_pmx  # noqa: E402

# What the project's own notes say this model contains.
EXPECTED = {
    "triangles": 73000,
    "materials": 14,
    "bones": 828,
    "morphs": 41,
    "vertex_morphs": 40,
    "material_morphs": 1,
}


def main(argv: list[str]) -> int:
    # The model is Japanese, so its material, bone and morph names are not
    # encodable in this console's GBK codepage and printing them raises
    # UnicodeEncodeError part-way through the report. That would look like a
    # parse failure when it is only a display problem, so pin stdout here
    # rather than relying on the caller. It cannot be done with an environment
    # variable: the documented invocation uses ``-I``, which implies ``-E`` and
    # makes Python ignore PYTHONIOENCODING.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

    if len(argv) != 2:
        print(__doc__)
        return 2

    path = argv[1]
    model = read_pmx(path)

    print(model.summary())
    print()

    print(f"Comment starts: {model.comment.strip().splitlines()[0][:60] if model.comment.strip() else '(empty)'}")
    print()

    print("Materials")
    print("  idx  faces   alpha  cull  sphere  name")
    offset = 0
    for index, material in enumerate(model.materials):
        faces = material.face_index_count // 3
        print(
            f"  {index:>3}  {faces:>6}  {material.diffuse[3]:>5.2f}  "
            f"{'yes' if material.is_two_sided else ' no'}  "
            f"{material.sphere_mode:>6}  {material.name}"
        )
        offset += material.face_index_count
    print(f"  material face indices total: {offset} (mesh has {len(model.indices)})")
    print()

    print("Morphs")
    for index, morph in enumerate(model.morphs):
        detail = ""
        if morph.morph_type == MORPH_VERTEX:
            detail = f"{len(morph.vertex_offsets)} vertices"
        elif morph.morph_type == MORPH_MATERIAL:
            detail = f"materials {morph.material_targets}"
        elif morph.other_offset_count:
            detail = f"{morph.other_offset_count} offsets"
        print(f"  {index:>3}  {morph.type_name:<9} {morph.name!r}  {detail}")
    print()

    print("Bones (first 20)")
    for index, bone in enumerate(model.bones[:20]):
        print(f"  {index:>3}  parent {bone.parent_index:>4}  layer {bone.deform_layer}  {bone.name!r}")
    print(f"  ... {len(model.bones)} total")
    print()

    print("Textures referenced by materials")
    used: dict[int, list[str]] = {}
    for material in model.materials:
        for slot, name in (("base", material.texture_index), ("sphere", material.sphere_texture_index)):
            if name >= 0:
                used.setdefault(name, []).append(f"{material.name}:{slot}")
    for index in sorted(used):
        rel = model.textures[index] if index < len(model.textures) else "(out of range)"
        print(f"  {index:>3}  {rel}   <- {', '.join(used[index])}")
    print()

    # A single triangle's worth of positions, to confirm the coordinate scale
    # and handedness rather than assuming them.
    xs = [p[0] for p in model.positions]
    ys = [p[1] for p in model.positions]
    zs = [p[2] for p in model.positions]
    print("Bounds (raw PMX units)")
    print(f"  x {min(xs):>9.3f} .. {max(xs):>9.3f}")
    print(f"  y {min(ys):>9.3f} .. {max(ys):>9.3f}   height {max(ys) - min(ys):.3f}")
    print(f"  z {min(zs):>9.3f} .. {max(zs):>9.3f}")
    print()

    print("Against tools/model-conversion.md")
    actual = {
        "triangles": model.triangle_count,
        "materials": len(model.materials),
        "bones": len(model.bones),
        "morphs": len(model.morphs),
        "vertex_morphs": sum(1 for m in model.morphs if m.morph_type == MORPH_VERTEX),
        "material_morphs": sum(1 for m in model.morphs if m.morph_type == MORPH_MATERIAL),
    }
    ok = True
    for key, expected in EXPECTED.items():
        got = actual[key]
        if key in ("triangles", "materials", "bones", "morphs"):
            good = abs(got - expected) <= max(2, expected * 0.02)
        else:
            good = got == expected
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'}  {key:<16} expected ~{expected}, got {got}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
