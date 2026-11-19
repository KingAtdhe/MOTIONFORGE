"""UV-unwrap the hull and bake per-texel object-space position and normal (float EXR) for numpy projection."""
import sys, bpy, numpy as np
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
src, dst, RES = argv[0], argv[1], int(argv[2]) if len(argv) > 2 else 2048
bpy.ops.wm.open_mainfile(filepath=src)
ob = next(o for o in bpy.data.objects if o.type == "MESH")
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.006, area_weight=0.0, scale_to_bounds=False)
bpy.ops.object.mode_set(mode="OBJECT")
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 1
out = {}
for what in ("pos", "nor"):
    img = bpy.data.images.new(what, RES, RES, float_buffer=True, alpha=True)
    mat = bpy.data.materials.new(what)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"] if what == "pos" else tc.outputs["Normal"], em.inputs[0])
    nt.links.new(em.outputs[0], o.inputs[0])
    it = nt.nodes.new("ShaderNodeTexImage")
    it.image = img
    nt.nodes.active = it
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    sc.render.bake.margin = 0
    bpy.ops.object.bake(type="EMIT")
    a = np.array(img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)
    out[what] = a
np.savez_compressed("./bake.npz", pos=out["pos"], nor=out["nor"])
ob.data.materials.clear()
bpy.ops.wm.save_as_mainfile(filepath=dst)
print("baked", RES)
