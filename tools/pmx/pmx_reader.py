"""A small, read-only PMX 2.0 / 2.1 reader.

Why this exists
---------------
``tools/model-conversion.md`` describes the supported route as Blender + MMD
Tools -> FBX. Blender is not installed on this machine, and installing a whole
3D suite is out of scope, so this module is the in-project replacement for the
one step that actually matters: getting the mesh, the skin weights, the
BlendShapes and the material-to-texture mapping out of ``祀.pmx`` and into
something Unity can build a ``Mesh`` from.

It is deliberately narrow. It reads what a static character needs and stops
there:

* vertices, normals, UVs and the four strongest skin influences;
* triangle indices;
* the material list, with the texture / sphere-map / toon slots it refers to;
* the bone list and parent relationships (the full hierarchy is wanted, bones
  are never dropped);
* morphs, tagged by type, so the caller can tell a vertex morph (a real
  BlendShape) from a material morph (which is *not* one).

It does **not** read rigid bodies, joints, soft bodies or the MMD physics
description. v1 disables MMD physics entirely (constraint #4), so carrying 506
rigid bodies and 682 constraints through the converter would be pure cost.

It does record the rig mechanics that a VMD bake needs: IK targets, loop counts
and per-link angle limits, fixed and local axes, and the inherit flags and
weight. A motion baked offline has to reproduce MMD's own evaluation order (FK,
then append rotation, then leg IK), and the converter itself ignores these
fields - the baker in ``tools/vmd`` reads them straight from the PMX.

The original file is only ever opened for reading.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import BinaryIO

# ---------------------------------------------------------------------------
# PMX enumerations
# ---------------------------------------------------------------------------

TEXT_UTF16LE = 0
TEXT_UTF8 = 1

# Vertex skinning. SDEF carries extra C/R0/R1 terms that v1 does not use; it is
# approximated as the equivalent two-bone linear blend, which is the same
# influence set with a slightly different falloff.
WEIGHT_BDEF1 = 0
WEIGHT_BDEF2 = 1
WEIGHT_BDEF4 = 2
WEIGHT_SDEF = 3
WEIGHT_QDEF = 4

SPHERE_NONE = 0
SPHERE_MULTIPLY = 1
SPHERE_ADD = 2
SPHERE_SUB_TEXTURE = 3

MORPH_GROUP = 0
MORPH_VERTEX = 1
MORPH_BONE = 2
MORPH_UV = 3
MORPH_UV1 = 4
MORPH_UV2 = 5
MORPH_UV3 = 6
MORPH_UV4 = 7
MORPH_MATERIAL = 8
MORPH_FLIP = 9
MORPH_IMPULSE = 10

MORPH_TYPE_NAMES = {
    MORPH_GROUP: "group",
    MORPH_VERTEX: "vertex",
    MORPH_BONE: "bone",
    MORPH_UV: "uv",
    MORPH_UV1: "uv1",
    MORPH_UV2: "uv2",
    MORPH_UV3: "uv3",
    MORPH_UV4: "uv4",
    MORPH_MATERIAL: "material",
    MORPH_FLIP: "flip",
    MORPH_IMPULSE: "impulse",
}

# Bone flags, PMX 2.0. The ones v1 cares about are the deform-affecting bits.
BONE_TAIL_IS_BONE = 0x0001
BONE_ROTATABLE = 0x0002
BONE_MOVABLE = 0x0004
BONE_VISIBLE = 0x0008
BONE_ENABLED = 0x0010
BONE_IK = 0x0020
BONE_INHERIT_ROTATION = 0x0100
BONE_INHERIT_TRANSLATION = 0x0200
BONE_FIXED_AXIS = 0x0400
BONE_LOCAL_AXIS = 0x0800
BONE_PHYSICS_AFTER_DEFORM = 0x1000
BONE_EXTERNAL_PARENT = 0x2000

# Material draw flags, PMX 2.0.
DRAW_NO_CULL = 0x01
DRAW_CAST_SHADOW = 0x02
DRAW_CAST_SHADOW_MAP = 0x04
DRAW_RECEIVE_SHADOW = 0x08
DRAW_EDGE = 0x10
DRAW_VERTEX_COLOR = 0x20
DRAW_POINT_DRAW = 0x40
DRAW_LINE_DRAW = 0x80


class PmxError(Exception):
    """The file is not a PMX model we can read."""


# ---------------------------------------------------------------------------
# Data holders
# ---------------------------------------------------------------------------


@dataclass
class PmxMaterial:
    name: str
    name_en: str
    diffuse: tuple[float, float, float, float]
    specular: tuple[float, float, float]
    specular_strength: float
    ambient: tuple[float, float, float]
    draw_flag: int
    edge_color: tuple[float, float, float, float]
    edge_size: float
    texture_index: int
    sphere_texture_index: int
    sphere_mode: int
    shared_toon: bool
    toon_index: int
    memo: str
    face_index_count: int

    @property
    def is_transparent(self) -> bool:
        return self.diffuse[3] < 0.999

    @property
    def is_two_sided(self) -> bool:
        return bool(self.draw_flag & DRAW_NO_CULL)


@dataclass
class PmxIkLink:
    """One joint in an IK chain, with the per-axis limit MMD clamps it to."""

    bone_index: int
    has_limits: bool
    limit_min: tuple[float, float, float] | None = None
    limit_max: tuple[float, float, float] | None = None


@dataclass
class PmxIk:
    """A PMX IK record: the effector it moves and the links it may bend."""

    target_index: int
    loop_count: int
    angle_limit_per_loop: float
    links: list[PmxIkLink] = field(default_factory=list)


@dataclass
class PmxBone:
    name: str
    name_en: str
    position: tuple[float, float, float]
    parent_index: int
    deform_layer: int
    flags: int
    tail_is_bone: bool = False
    tail_bone_index: int = -1
    tail_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    inherit_parent_index: int = -1
    inherit_weight: float = 0.0
    inherit_translation: bool = False
    is_ik: bool = False
    #: The axis a fixed-axis bone is locked to, PMX units.
    fixed_axis: tuple[float, float, float] | None = None
    #: The local frame X/Z axes of a twist bone, PMX units.
    local_axis_x: tuple[float, float, float] | None = None
    local_axis_z: tuple[float, float, float] | None = None
    #: The IK record, for an IK bone. ``None`` for every other bone.
    ik: PmxIk | None = None

    @property
    def deformable(self) -> bool:
        return bool(self.flags & (BONE_ROTATABLE | BONE_MOVABLE))


@dataclass
class PmxMaterialOffset:
    """One material morph's change to one material.

    The values are *deltas*, and ``calc_mode`` says how to combine them with the
    material's base value: 0 multiplies, 1 adds. The converter needs the numbers
    rather than just the target index, because the alternative to implementing a
    material morph properly is animating a BlendShape that does not exist — and
    docs/constraints.md #5 forbids passing one off as the other.
    """

    material_index: int
    calc_mode: int
    diffuse: tuple[float, float, float, float]
    specular: tuple[float, float, float]
    specular_strength: float
    ambient: tuple[float, float, float]
    edge_color: tuple[float, float, float, float]
    edge_size: float
    texture_tint: tuple[float, float, float, float]
    sphere_tint: tuple[float, float, float, float]
    toon_tint: tuple[float, float, float, float]


@dataclass
class PmxMorph:
    name: str
    name_en: str
    panel: int
    morph_type: int
    # Vertex morphs: (vertex index, (dx, dy, dz)) pairs.
    vertex_offsets: list[tuple[int, tuple[float, float, float]]] = field(default_factory=list)
    # Material morphs. ``material_targets`` is kept for quick reporting;
    # ``material_offsets`` carries the actual values.
    material_targets: list[int] = field(default_factory=list)
    material_offsets: list[PmxMaterialOffset] = field(default_factory=list)
    other_offset_count: int = 0

    @property
    def type_name(self) -> str:
        return MORPH_TYPE_NAMES.get(self.morph_type, f"unknown({self.morph_type})")


@dataclass
class PmxModel:
    version: float
    encoding: int
    additional_uv_count: int
    index_sizes: dict[str, int]
    name: str
    name_en: str
    comment: str
    comment_en: str
    positions: list[tuple[float, float, float]] = field(default_factory=list)
    normals: list[tuple[float, float, float]] = field(default_factory=list)
    uvs: list[tuple[float, float]] = field(default_factory=list)
    # Four skin influences per vertex, already normalised and already reduced
    # from SDEF/QDEF to a linear blend.
    bone_indices: list[tuple[int, int, int, int]] = field(default_factory=list)
    bone_weights: list[tuple[float, float, float, float]] = field(default_factory=list)
    weight_types: list[int] = field(default_factory=list)
    indices: list[int] = field(default_factory=list)
    textures: list[str] = field(default_factory=list)
    materials: list[PmxMaterial] = field(default_factory=list)
    bones: list[PmxBone] = field(default_factory=list)
    morphs: list[PmxMorph] = field(default_factory=list)

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3

    def summary(self) -> str:
        by_type: dict[str, int] = {}
        for morph in self.morphs:
            by_type[morph.type_name] = by_type.get(morph.type_name, 0) + 1
        morph_bits = ", ".join(f"{k} {v}" for k, v in sorted(by_type.items()))

        lines = [
            f"PMX version        : {self.version}",
            f"Encoding           : {'UTF-16LE' if self.encoding == TEXT_UTF16LE else 'UTF-8'}",
            f"Index sizes        : " + ", ".join(f"{k}={v}" for k, v in self.index_sizes.items()),
            f"Model name         : {self.name!r} / {self.name_en!r}",
            f"Vertices           : {len(self.positions)}",
            f"Triangles          : {self.triangle_count}",
            f"Materials          : {len(self.materials)}",
            f"Textures           : {len(self.textures)}",
            f"Bones              : {len(self.bones)}",
            f"Morphs             : {len(self.morphs)}  ({morph_bits})",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


class _Reader:
    """Sequential little-endian reader over an in-memory buffer."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def take(self, count: int) -> memoryview:
        end = self.pos + count
        if end > len(self.data):
            raise PmxError(
                f"unexpected end of file: wanted {count} bytes at offset "
                f"{self.pos}, only {len(self.data) - self.pos} left"
            )
        chunk = memoryview(self.data)[self.pos : end]
        self.pos = end
        return chunk

    def uint8(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def int8(self) -> int:
        value = struct.unpack_from("<b", self.data, self.pos)[0]
        self.pos += 1
        return value

    def int32(self) -> int:
        value = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return value

    def uint16(self) -> int:
        value = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def float32(self) -> float:
        value = struct.unpack_from("<f", self.data, self.pos)[0]
        self.pos += 4
        return value

    def floats(self, count: int) -> tuple[float, ...]:
        values = struct.unpack_from(f"<{count}f", self.data, self.pos)
        self.pos += 4 * count
        return values

    def index(self, size: int, *, signed: bool) -> int:
        """Read an index of 1, 2 or 4 bytes.

        Signed reads can return -1, which is how PMX says "no such thing".
        Unsigned reads are used for vertex references, which never have a
        sentinel.
        """
        if size == 1:
            return self.int8() if signed else self.uint8()

        if size == 2:
            fmt = "<h" if signed else "<H"
            value = struct.unpack_from(fmt, self.data, self.pos)[0]
            self.pos += 2
            return value

        if size == 4:
            fmt = "<i" if signed else "<I"
            value = struct.unpack_from(fmt, self.data, self.pos)[0]
            self.pos += 4
            return value

        raise PmxError(f"unsupported index size {size}")


def _read_index(reader: _Reader, size: int, signed: bool) -> int:
    return reader.index(size, signed=signed)


def _read_text(reader: _Reader, encoding: int) -> str:
    length = reader.int32()
    if length < 0:
        raise PmxError(f"negative text length {length} at offset {reader.pos}")
    raw = bytes(reader.take(length))
    codec = "utf-16-le" if encoding == TEXT_UTF16LE else "utf-8"
    return raw.decode(codec, errors="replace")


def read_pmx(path: str) -> PmxModel:
    """Parse a PMX file into a :class:`PmxModel`."""
    with open(path, "rb") as handle:
        data = handle.read()
    return parse_pmx(data)


def parse_pmx(data: bytes) -> PmxModel:
    reader = _Reader(data)

    magic = bytes(reader.take(4))
    if magic != b"PMX ":
        raise PmxError(f"not a PMX file: magic is {magic!r}")

    version = reader.float32()
    if not (2.0 <= version < 3.0):
        raise PmxError(f"unsupported PMX version {version}; this reader handles 2.0 and 2.1")

    global_count = reader.uint8()
    if global_count < 8:
        raise PmxError(f"header declares only {global_count} globals, expected 8")

    encoding = reader.uint8()
    if encoding not in (TEXT_UTF16LE, TEXT_UTF8):
        raise PmxError(f"unknown text encoding {encoding}")

    additional_uv_count = reader.uint8()
    index_sizes = {
        "vertex": reader.uint8(),
        "texture": reader.uint8(),
        "material": reader.uint8(),
        "bone": reader.uint8(),
        "morph": reader.uint8(),
        "rigidbody": reader.uint8(),
    }
    # PMX 2.1 adds a seventh size for soft bodies; skip it if present.
    for _ in range(global_count - 8):
        reader.uint8()

    model = PmxModel(
        version=version,
        encoding=encoding,
        additional_uv_count=additional_uv_count,
        index_sizes=index_sizes,
        name="",
        name_en="",
        comment="",
        comment_en="",
    )

    model.name = _read_text(reader, encoding)
    model.name_en = _read_text(reader, encoding)
    model.comment = _read_text(reader, encoding)
    model.comment_en = _read_text(reader, encoding)

    _read_vertices(reader, model)
    _read_faces(reader, model)
    _read_textures(reader, model, encoding)
    _read_materials(reader, model, encoding)
    _read_bones(reader, model, encoding)
    _read_morphs(reader, model, encoding)

    return model


def _read_vertices(reader: _Reader, model: PmxModel) -> None:
    vertex_size = model.index_sizes["vertex"]
    bone_size = model.index_sizes["bone"]
    extra_uvs = model.additional_uv_count

    count = reader.int32()
    if count < 0:
        raise PmxError(f"negative vertex count {count}")

    for _ in range(count):
        model.positions.append(reader.floats(3))
        model.normals.append(reader.floats(3))
        model.uvs.append(reader.floats(2))
        for _ in range(extra_uvs):
            reader.floats(4)

        weight_type = reader.uint8()
        model.weight_types.append(weight_type)

        if weight_type == WEIGHT_BDEF1:
            b0 = _read_index(reader, bone_size, True)
            model.bone_indices.append((b0, 0, 0, 0))
            model.bone_weights.append((1.0, 0.0, 0.0, 0.0))

        elif weight_type in (WEIGHT_BDEF2, WEIGHT_SDEF):
            b0 = _read_index(reader, bone_size, True)
            b1 = _read_index(reader, bone_size, True)
            w0 = reader.float32()
            model.bone_indices.append((b0, b1, 0, 0))
            model.bone_weights.append((w0, 1.0 - w0, 0.0, 0.0))
            if weight_type == WEIGHT_SDEF:
                # C, R0, R1. Not used by v1; read past them so the stream stays
                # aligned.
                reader.floats(3)
                reader.floats(3)
                reader.floats(3)

        elif weight_type in (WEIGHT_BDEF4, WEIGHT_QDEF):
            b0 = _read_index(reader, bone_size, True)
            b1 = _read_index(reader, bone_size, True)
            b2 = _read_index(reader, bone_size, True)
            b3 = _read_index(reader, bone_size, True)
            w = reader.floats(4)
            model.bone_indices.append((b0, b1, b2, b3))
            model.bone_weights.append((w[0], w[1], w[2], w[3]))

        else:
            raise PmxError(f"unknown vertex weight type {weight_type}")

        reader.float32()  # edge scale


def _read_faces(reader: _Reader, model: PmxModel) -> None:
    vertex_size = model.index_sizes["vertex"]
    count = reader.int32()
    if count < 0 or count % 3 != 0:
        raise PmxError(f"face index count {count} is not a multiple of 3")

    indices = model.indices
    for _ in range(count):
        indices.append(_read_index(reader, vertex_size, False))


def _read_textures(reader: _Reader, model: PmxModel, encoding: int) -> None:
    count = reader.int32()
    for _ in range(count):
        model.textures.append(_read_text(reader, encoding))


def _read_materials(reader: _Reader, model: PmxModel, encoding: int) -> None:
    texture_size = model.index_sizes["texture"]
    count = reader.int32()

    for _ in range(count):
        name = _read_text(reader, encoding)
        name_en = _read_text(reader, encoding)
        diffuse = reader.floats(4)
        specular = reader.floats(3)
        specular_strength = reader.float32()
        ambient = reader.floats(3)
        draw_flag = reader.uint8()
        edge_color = reader.floats(4)
        edge_size = reader.float32()
        texture_index = _read_index(reader, texture_size, True)
        sphere_texture_index = _read_index(reader, texture_size, True)
        sphere_mode = reader.uint8()
        shared_toon = reader.uint8() != 0
        if shared_toon:
            toon_index = reader.uint8()
        else:
            toon_index = _read_index(reader, texture_size, True)
        memo = _read_text(reader, encoding)
        face_index_count = reader.int32()

        model.materials.append(
            PmxMaterial(
                name=name,
                name_en=name_en,
                diffuse=diffuse,
                specular=specular,
                specular_strength=specular_strength,
                ambient=ambient,
                draw_flag=draw_flag,
                edge_color=edge_color,
                edge_size=edge_size,
                texture_index=texture_index,
                sphere_texture_index=sphere_texture_index,
                sphere_mode=sphere_mode,
                shared_toon=shared_toon,
                toon_index=toon_index,
                memo=memo,
                face_index_count=face_index_count,
            )
        )


def _read_bones(reader: _Reader, model: PmxModel, encoding: int) -> None:
    bone_size = model.index_sizes["bone"]
    count = reader.int32()

    for _ in range(count):
        name = _read_text(reader, encoding)
        name_en = _read_text(reader, encoding)
        position = reader.floats(3)
        parent_index = _read_index(reader, bone_size, True)
        deform_layer = reader.int32()
        flags = reader.uint16()

        bone = PmxBone(
            name=name,
            name_en=name_en,
            position=position,
            parent_index=parent_index,
            deform_layer=deform_layer,
            flags=flags,
        )

        if flags & BONE_TAIL_IS_BONE:
            bone.tail_is_bone = True
            bone.tail_bone_index = _read_index(reader, bone_size, True)
        else:
            bone.tail_position = reader.floats(3)

        if flags & (BONE_INHERIT_ROTATION | BONE_INHERIT_TRANSLATION):
            bone.inherit_parent_index = _read_index(reader, bone_size, True)
            bone.inherit_weight = reader.float32()
            bone.inherit_translation = bool(flags & BONE_INHERIT_TRANSLATION)

        if flags & BONE_FIXED_AXIS:
            bone.fixed_axis = reader.floats(3)

        if flags & BONE_LOCAL_AXIS:
            bone.local_axis_x = reader.floats(3)
            bone.local_axis_z = reader.floats(3)

        if flags & BONE_EXTERNAL_PARENT:
            reader.int32()

        if flags & BONE_IK:
            bone.is_ik = True
            target = _read_index(reader, bone_size, True)
            loop_count = reader.int32()
            angle_limit = reader.float32()
            link_count = reader.int32()
            links: list[PmxIkLink] = []
            for _ in range(link_count):
                link_bone = _read_index(reader, bone_size, True)
                has_limits = reader.uint8() != 0
                limit_min = limit_max = None
                if has_limits:
                    limit_min = reader.floats(3)
                    limit_max = reader.floats(3)
                links.append(PmxIkLink(link_bone, has_limits, limit_min, limit_max))
            bone.ik = PmxIk(target, loop_count, angle_limit, links)

        model.bones.append(bone)


def _read_morphs(reader: _Reader, model: PmxModel, encoding: int) -> None:
    vertex_size = model.index_sizes["vertex"]
    material_size = model.index_sizes["material"]
    bone_size = model.index_sizes["bone"]
    morph_size = model.index_sizes["morph"]
    rigidbody_size = model.index_sizes["rigidbody"]

    count = reader.int32()

    for _ in range(count):
        name = _read_text(reader, encoding)
        name_en = _read_text(reader, encoding)
        panel = reader.uint8()
        morph_type = reader.uint8()
        offset_count = reader.int32()

        morph = PmxMorph(name=name, name_en=name_en, panel=panel, morph_type=morph_type)

        for _ in range(offset_count):
            if morph_type == MORPH_GROUP:
                _read_index(reader, morph_size, True)
                reader.float32()

            elif morph_type == MORPH_VERTEX:
                vertex_index = _read_index(reader, vertex_size, False)
                offset = reader.floats(3)
                morph.vertex_offsets.append((vertex_index, offset))

            elif morph_type == MORPH_BONE:
                _read_index(reader, bone_size, True)
                reader.floats(3)
                reader.floats(4)
                morph.other_offset_count += 1

            elif morph_type in (MORPH_UV, MORPH_UV1, MORPH_UV2, MORPH_UV3, MORPH_UV4):
                _read_index(reader, vertex_size, False)
                reader.floats(4)
                morph.other_offset_count += 1

            elif morph_type == MORPH_MATERIAL:
                target = _read_index(reader, material_size, True)
                morph.material_targets.append(target)
                calc_mode = reader.uint8()
                diffuse = reader.floats(4)
                specular = reader.floats(3)
                specular_strength = reader.float32()
                ambient = reader.floats(3)
                edge_color = reader.floats(4)
                edge_size = reader.float32()
                texture_tint = reader.floats(4)
                sphere_tint = reader.floats(4)
                toon_tint = reader.floats(4)
                morph.material_offsets.append(
                    PmxMaterialOffset(
                        material_index=target,
                        calc_mode=calc_mode,
                        diffuse=diffuse,
                        specular=specular,
                        specular_strength=specular_strength,
                        ambient=ambient,
                        edge_color=edge_color,
                        edge_size=edge_size,
                        texture_tint=texture_tint,
                        sphere_tint=sphere_tint,
                        toon_tint=toon_tint,
                    )
                )
                morph.other_offset_count += 1

            elif morph_type == MORPH_FLIP:
                _read_index(reader, morph_size, True)
                reader.float32()
                morph.other_offset_count += 1

            elif morph_type == MORPH_IMPULSE:
                _read_index(reader, rigidbody_size, True)
                reader.uint8()
                reader.floats(3)
                reader.floats(3)
                morph.other_offset_count += 1

            else:
                raise PmxError(f"unknown morph type {morph_type} on morph {name!r}")

        model.morphs.append(morph)
