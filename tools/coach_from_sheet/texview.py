import sys, math, bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
ob = next(o for o in bpy.data.objects if o.type == "MESH")
img = bpy.data.images.load(argv[1])
mat = bpy.data.materials.new("albedo"); mat.use_nodes = True
nt = mat.node_tree; bs = nt.nodes["Principled BSDF"]
it = nt.nodes.new("ShaderNodeTexImage"); it.image = img
nt.links.new(it.outputs[0], bs.inputs["Base Color"])
ob.data.materials.clear(); ob.data.materials.append(mat)
bpy.ops.object.shade_smooth()
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "TEXTURE"
sc.view_settings.view_transform = "Standard"
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.82, 0.82, 0.86)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
yaws = [float(v) for v in (argv[3].split(",") if len(argv) > 3 else "0,35,90,180".split(","))]
zt, dist, lens = (float(argv[4]), float(argv[5]), float(argv[6])) if len(argv) > 6 else (0.88, 4.6, 75)
w, h = (int(argv[7]), int(argv[8])) if len(argv) > 8 else (360, 760)
sc.render.resolution_x, sc.render.resolution_y = w, h
cam.data.lens = lens
for i, yaw in enumerate(yaws):
    y = math.radians(yaw)
    cam.location = (dist * math.sin(y), -dist * math.cos(y), zt)
    cam.rotation_euler = (math.radians(90), 0, y)
    sc.render.filepath = f"{argv[2]}_{i}.png"
    bpy.ops.render.render(write_still=True)
