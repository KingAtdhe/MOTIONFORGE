import sys, math, bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = argv[2] if len(argv) > 2 else "SINGLE"
sc.display.shading.single_color = (0.8, 0.75, 0.7)
sc.display.shading.show_cavity = True
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 75
sc.render.resolution_x, sc.render.resolution_y = 360, 760
for i, yaw in enumerate((0, 35, 100, 200)):
    y = math.radians(yaw)
    cam.location = (4.6 * math.sin(y), -4.6 * math.cos(y), 1.05)
    cam.rotation_euler = (math.radians(87), 0, y)
    sc.render.filepath = f"{argv[1]}_{i}.png"
    bpy.ops.render.render(write_still=True)
