# Model conversion — 祀, offline, PMX → binary

This is the **only** supported path from the source model to something Unity can
load. There is no runtime PMX import in v1: the runtime must not depend on an MMD
importer, and the conversion has to be a repeatable, inspectable step rather than
something that happens at startup.

The route is a direct PMX reader, not Blender. Blender plus MMD Tools was the
original plan and it is not what is installed on this machine, so the conversion
is done by `tools/pmx/`, which reads the PMX itself and writes a binary the
client loads. That also removes the FBX round trip that morph names would have
had to survive.

```
祀.pmx  ──tools/pmx/convert_si.py──▶  converted/si/si_model.bin
                                      converted/si/si_model.json
                                      converted/si/textures/
                                      converted/si/report.txt
```

## Ground rules

- **The original model is never modified.** `祀.pmx` and both texture folders stay
  exactly as downloaded. Every conversion product goes to `converted/`, which is
  gitignored.
- **Do not delete bones or simplify the mesh for performance.** The static counts
  below are large, but "large" is not the same as "the bottleneck". Measure first;
  optimise the thing that is actually slow.
- **Conversion products are never committed.** See `docs/asset-policy.md`. The
  client copies them into `StreamingAssets/si/`, which is gitignored too.

## How to run it

```powershell
python -I tools/pmx/convert_si.py "<path to 祀.pmx>" H:\MGFR\converted\si
```

`python -I` matters: it implies `-E` and `-s`, so the script cannot pick up
anything from the user site directory or from `PYTHONPATH` while it is reading a
large untrusted binary.

Then, in Unity, `MGFR > Copy Character Data` moves the result into
`Assets/StreamingAssets/si/`. The client reads it from there at runtime.

`tools/pmx/inspect_pmx.py` dumps a model without converting it, which is what the
counts below were read from.

## Static model facts

Read from the source PMX and confirmed again from the model the client builds:

| Property | Value |
|---|---|
| Vertices | 63,503 |
| Triangles | 73,037 |
| Materials | 14 |
| Bones | 828 |
| Morphs in the source | 41 (40 vertex morphs + one material morph) |
| Blend shapes in Unity | **40** |
| Material morphs in Unity | **1** |
| Rigid bodies | 506 |
| Joints / constraints | 682 |
| Height | 1.793 m, feet at y = 0 |
| Runtime rendering | **verified in Unity**, desktop only |

## Physics

**The MMD physics simulation is disabled entirely**, and the bones are not
deleted. 506 rigid bodies and 682 constraints are a full cloth and hair solver;
running it in v1 is out of scope and would dominate the frame budget. The
converter writes the bone hierarchy and skips the rigid bodies and constraints,
so nothing in the client ever ticks a physics step. The counts are still reported
in `report.txt` so the omission is visible rather than silent.

## Morph classification — done individually, not in bulk

The count of 41 morphs is not the count of usable BlendShapes. The expression
morph `照れ` is a **material** morph: it drives material properties and does not
become a BlendShape at all. It is not faked as one. The client reports 40 blend
shapes and one material morph, and `6` on the keyboard toggles the material morph
rather than pretending to be a shape.

| Group | Morphs | State |
|---|---|---|
| Blink | `まばたき` | present, blend shape index **5** |
| Vowels | `あ` `い` `う` `え` `お` | present, `あ` at index **0** |
| Expression | `照れ` | material morph, not a blend shape |
| Rest | the remaining vertex morphs | present, unused in v1 |

The indices above are recorded rather than assumed: the client looks shapes up by
name through `FindBlendShape` and reports what it found. An FBX round trip is
what would normally renumber these, and the direct route removes that risk
entirely — the names and the order are the model's own.

## Textures — the missing normal map

`textures/T_actor_jsspsi_body_01_N.png` is referenced by the model but **absent**
from `textures/`. A file with the same name exists in `other tex/`.

It is mapped **explicitly** in the converter, by name, and the material receives
it. Not a fuzzy path match, not copied into `textures/` to make the problem go
away, and not left without a normal map to accept flat shading. `report.txt`
records which texture each material slot resolved to, so the mapping can be
checked without opening the model.

Two consequences of the format that are handled in the converter and worth
knowing: the UV origin differs from Unity's, so V is flipped once at conversion
time; and PMX front faces are clockwise, so the winding is reversed to Unity's
counter-clockwise.

## Transparent and semi-transparent areas

Hair strands, eyelashes and semi-transparent clothing are the risky ones, because
the chroma-key background (constraint #3) can wrongly key out thin, partially
transparent geometry. The materials come across with their alpha modes intact.

This has **not** been checked in the headset. The desktop preview composites
differently and will not show the problem, so the check is still owed and is
listed as such.

## What this document does not cover

Emotion morphs, motion capture, physics, and multiple characters are all out of
scope for v1 (`docs/architecture.md`). Do not build them into the conversion; the
cost of carrying them is paid every frame.
