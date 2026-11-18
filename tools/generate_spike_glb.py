#!/usr/bin/env python3
"""
Generates app/src/main/assets/models/spike_stick_figure.glb.

PURPOSE: Phase 0 pipeline test only. It proves that the Android app can load a GLB with a
node hierarchy and play *named* animation clips through Filament. It is NOT the trainer
avatar and its motion is NOT instructional content (it has not been coach-reviewed).
The real trainer is modelled and animated in Blender in Phase 2 (docs/BLENDER_ASSET_SPEC.md).

Units: metres, +Y up, +Z towards the viewer (glTF convention). Feet rest on y = 0.
Materials use KHR_materials_unlit so the spike does not depend on lighting setup.

Usage: python3 tools/generate_spike_glb.py [output_path]
"""
import json
import math
import struct
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "app/src/main/assets/models/spike_stick_figure.glb"

# --------------------------------------------------------------------------- geometry
def unit_box():
    """24-vertex unit cube centred on the origin, with flat normals."""
    faces = [
        ((1, 0, 0), [(0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5)]),
        ((-1, 0, 0), [(-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5), (-0.5, -0.5, -0.5)]),
        ((0, 1, 0), [(-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5)]),
        ((0, -1, 0), [(-0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5)]),
        ((0, 0, 1), [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)]),
        ((0, 0, -1), [(0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5)]),
    ]
    pos, nrm, idx = [], [], []
    for n, quad in faces:
        base = len(pos)
        pos.extend(quad)
        nrm.extend([n] * 4)
        idx.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    return pos, nrm, idx


def quat_x(deg):
    h = math.radians(deg) / 2
    return (math.sin(h), 0.0, 0.0, math.cos(h))


# --------------------------------------------------------------------------- binary builder
class Bin:
    def __init__(self):
        self.data = bytearray()
        self.views = []
        self.accessors = []

    def _view(self, payload, target=None):
        while len(self.data) % 4:
            self.data.append(0)
        view = {"buffer": 0, "byteOffset": len(self.data), "byteLength": len(payload)}
        if target:
            view["target"] = target
        self.data.extend(payload)
        self.views.append(view)
        return len(self.views) - 1

    def floats(self, rows, type_, target=None, minmax=False):
        flat = [c for r in rows for c in (r if isinstance(r, (tuple, list)) else (r,))]
        view = self._view(struct.pack(f"<{len(flat)}f", *flat), target)
        acc = {"bufferView": view, "componentType": 5126, "count": len(rows), "type": type_}
        if minmax:
            width = len(rows[0]) if isinstance(rows[0], (tuple, list)) else 1
            cols = [[(r if width > 1 else (r,))[i] for r in rows] for i in range(width)]
            acc["min"] = [min(c) for c in cols]
            acc["max"] = [max(c) for c in cols]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    def indices(self, idx):
        view = self._view(struct.pack(f"<{len(idx)}H", *idx), 34963)
        self.accessors.append({"bufferView": view, "componentType": 5123, "count": len(idx), "type": "SCALAR"})
        return len(self.accessors) - 1


b = Bin()
pos, nrm, idx = unit_box()
POS = b.floats(pos, "VEC3", 34962, minmax=True)
NRM = b.floats(nrm, "VEC3", 34962)
IDX = b.indices(idx)

materials = [
    {"name": "spike_body", "pbrMetallicRoughness": {"baseColorFactor": [0.82, 0.85, 0.88, 1.0], "metallicFactor": 0.0, "roughnessFactor": 1.0},
     "extensions": {"KHR_materials_unlit": {}}},
    {"name": "spike_accent", "pbrMetallicRoughness": {"baseColorFactor": [0.43, 0.91, 0.72, 1.0], "metallicFactor": 0.0, "roughnessFactor": 1.0},
     "extensions": {"KHR_materials_unlit": {}}},
]
meshes = [
    {"name": "box_body", "primitives": [{"attributes": {"POSITION": POS, "NORMAL": NRM}, "indices": IDX, "material": 0}]},
    {"name": "box_accent", "primitives": [{"attributes": {"POSITION": POS, "NORMAL": NRM}, "indices": IDX, "material": 1}]},
]

# --------------------------------------------------------------------------- node hierarchy
nodes = []


def node(name, translation=(0, 0, 0), children=(), mesh=None, scale=None):
    n = {"name": name, "translation": list(translation)}
    if children:
        n["children"] = list(children)
    if mesh is not None:
        n["mesh"] = mesh
    if scale:
        n["scale"] = list(scale)
    nodes.append(n)
    return len(nodes) - 1


def geom(name, size, offset_y, accent=False):
    return node(name, (0, offset_y, 0), mesh=1 if accent else 0, scale=size)


HIP_Y = 0.95
THIGH, SHIN = 0.44, 0.44

# legs
leg = {}
for side, x in (("l", 0.1), ("r", -0.1)):
    foot = geom(f"foot_{side}_geo", (0.1, 0.06, 0.22), -0.04)
    ankle = node(f"ankle_{side}", (0, -SHIN, 0.04), [foot])
    shin_g = geom(f"shin_{side}_geo", (0.1, SHIN, 0.1), -SHIN / 2)
    knee = node(f"knee_{side}", (0, -THIGH, 0), [shin_g, ankle])
    thigh_g = geom(f"thigh_{side}_geo", (0.13, THIGH, 0.13), -THIGH / 2)
    hip = node(f"hip_{side}", (x, 0, 0), [thigh_g, knee])
    leg[side] = (hip, knee, ankle)

# arms
arm = {}
for side, x in (("l", 0.21), ("r", -0.21)):
    fore_g = geom(f"forearm_{side}_geo", (0.07, 0.27, 0.07), -0.135)
    elbow = node(f"elbow_{side}", (0, -0.29, 0), [fore_g])
    upper_g = geom(f"upperarm_{side}_geo", (0.08, 0.29, 0.08), -0.145)
    shoulder = node(f"shoulder_{side}", (x, 0.46, 0), [upper_g, elbow])
    arm[side] = (shoulder, elbow)

head_g = geom("head_geo", (0.2, 0.23, 0.21), 0.115, accent=True)
neck = node("neck", (0, 0.52, 0), [head_g])
torso_g = geom("torso_geo", (0.34, 0.5, 0.19), 0.25)
torso = node("torso", (0, 0.04, 0), [torso_g, neck, arm["l"][0], arm["r"][0]])
pelvis_g = geom("pelvis_geo", (0.3, 0.12, 0.18), 0.0, accent=True)
hips = node("hips", (0, HIP_Y, 0), [pelvis_g, torso, leg["l"][0], leg["r"][0]])
root = node("spike_figure_root", (0, 0, 0), [hips])

# --------------------------------------------------------------------------- animations
# Pose description: absolute leg angles about X (deg). Thigh negative = knee forward.
def pose(hip_drop, hip_back, thigh, shin_abs, torso_lean, arm_raise, elbow):
    knee_rel = shin_abs - thigh
    return {
        "hips_t": (0.0, HIP_Y - hip_drop, -hip_back),
        "thigh": thigh, "knee": knee_rel, "ankle": -shin_abs,  # keep feet flat
        "torso": torso_lean, "shoulder": arm_raise, "elbow": elbow,
    }


def solve_hip(thigh, shin_abs):
    """Hip height/back offset that keeps the ankle under its standing position."""
    t, s = math.radians(thigh), math.radians(shin_abs)
    drop = HIP_Y - (THIGH * math.cos(t) + SHIN * math.cos(s) + 0.07)
    back = THIGH * math.sin(-t) + SHIN * math.sin(-s)
    return drop, back


def squat_pose(f):
    thigh = -80 * f
    shin = 25 * f
    drop, back = solve_hip(thigh, shin)
    return pose(drop, back, thigh, shin, 35 * f, -75 * f, -10 * f)


def idle_pose(f):
    w = math.sin(f * 2 * math.pi)
    return pose(0.006 * (1 - math.cos(f * 2 * math.pi)), 0.0, 0, 0, 1.5 * w, 3 * w, -6)


def clip(name, duration, pose_fn, steps):
    times = [duration * i / steps for i in range(steps + 1)]
    poses = [pose_fn(i / steps) for i in range(steps + 1)]
    inp = b.floats(times, "SCALAR", minmax=True)
    samplers, channels = [], []

    def add(target_node, path, values, type_):
        out = b.floats(values, type_)
        samplers.append({"input": inp, "output": out, "interpolation": "LINEAR"})
        channels.append({"sampler": len(samplers) - 1, "target": {"node": target_node, "path": path}})

    add(hips, "translation", [p["hips_t"] for p in poses], "VEC3")
    add(torso, "rotation", [quat_x(p["torso"]) for p in poses], "VEC4")
    for side in ("l", "r"):
        add(leg[side][0], "rotation", [quat_x(p["thigh"]) for p in poses], "VEC4")
        add(leg[side][1], "rotation", [quat_x(p["knee"]) for p in poses], "VEC4")
        add(leg[side][2], "rotation", [quat_x(p["ankle"]) for p in poses], "VEC4")
        add(arm[side][0], "rotation", [quat_x(p["shoulder"]) for p in poses], "VEC4")
        add(arm[side][1], "rotation", [quat_x(p["elbow"]) for p in poses], "VEC4")
    return {"name": name, "samplers": samplers, "channels": channels}


def ease(f):
    return 0.5 - 0.5 * math.cos(math.pi * f)


animations = [
    clip("idle_neutral", 2.4, idle_pose, 24),
    clip("squat_down", 1.4, lambda f: squat_pose(ease(f)), 28),
    clip("squat_up", 1.4, lambda f: squat_pose(ease(1 - f)), 28),
]

# --------------------------------------------------------------------------- write GLB
while len(b.data) % 4:
    b.data.append(0)

gltf = {
    "asset": {"version": "2.0", "generator": "MOTIONFORGE tools/generate_spike_glb.py (Phase 0 test asset)"},
    "extensionsUsed": ["KHR_materials_unlit"],
    "scene": 0,
    "scenes": [{"name": "spike", "nodes": [root]}],
    "nodes": nodes,
    "meshes": meshes,
    "materials": materials,
    "animations": animations,
    "accessors": b.accessors,
    "bufferViews": b.views,
    "buffers": [{"byteLength": len(b.data)}],
}
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * ((4 - len(js) % 4) % 4)
total = 12 + 8 + len(js) + 8 + len(b.data)
glb = struct.pack("<III", 0x46546C67, 2, total)
glb += struct.pack("<II", len(js), 0x4E4F534A) + js
glb += struct.pack("<II", len(b.data), 0x004E4942) + bytes(b.data)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(glb)
print(f"wrote {OUT} ({len(glb)} bytes, {len(nodes)} nodes, {len(animations)} clips)")
