"""Bakes coach_normal.png: high-res displaced copy of the body (height map) -> tangent normals on the game mesh.
usage (Blender python, in the work dir): detail_bake.py [strength_m]"""
import sys, bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
STR = float(argv[0]) if argv else 0.012
bpy.ops.wm.open_mainfile(filepath="hull_uv.blend")
low = next(o for o in bpy.data.objects if o.type == "MESH")
hi = low.copy(); hi.data = low.data.copy(); hi.name = "hi"
bpy.context.collection.objects.link(hi)
sub = hi.modifiers.new("sub", "SUBSURF"); sub.levels = sub.render_levels = 2; sub.uv_smooth = "PRESERVE_BOUNDARIES"
himg = bpy.data.images.load("//coach_height.png"); himg.colorspace_settings.name = "Non-Color"
tex = bpy.data.textures.new("h", "IMAGE"); tex.image = himg; tex.extension = "EXTEND"
dis = hi.modifiers.new("dis", "DISPLACE"); dis.texture = tex; dis.texture_coords = "UV"; dis.mid_level = 0.5; dis.strength = STR
bpy.context.view_layer.objects.active = hi
for m in list(hi.modifiers):
    bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.object.shade_smooth()
RES = 2048
img = bpy.data.images.new("nrm", RES, RES, float_buffer=False)
img.colorspace_settings.name = "Non-Color"
mat = bpy.data.materials.new("bake"); mat.use_nodes = True
it = mat.node_tree.nodes.new("ShaderNodeTexImage"); it.image = img; mat.node_tree.nodes.active = it
low.data.materials.clear(); low.data.materials.append(mat)
hi.data.materials.clear(); hi.data.materials.append(bpy.data.materials.new("x"))
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 1
bpy.ops.object.select_all(action="DESELECT")
hi.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
sc.render.bake.use_selected_to_active = True
sc.render.bake.cage_extrusion = 0.012
sc.render.bake.max_ray_distance = 0.03
sc.render.bake.margin = 8
bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
img.filepath_raw = "//coach_normal.png"; img.file_format = "PNG"; img.save()
print("baked normal", RES, "hi verts", len(hi.data.vertices))
