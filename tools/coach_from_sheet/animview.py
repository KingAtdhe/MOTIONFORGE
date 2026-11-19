import sys, math, bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
out = argv[1]
shots = [s.split(":") for s in argv[2].split(",")]   # clip:frame:yaw:zt:dist
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = (sys.argv[-1] if sys.argv[-1] in ("SINGLE","MATERIAL","TEXTURE") else "TEXTURE")
sc.view_settings.view_transform = "Standard"
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.82, 0.82, 0.86)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH")
print("objects", [o.name for o in bpy.data.objects], "groups", len(body.vertex_groups), "tris", sum(len(p.vertices)-2 for p in body.data.polygons))
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 75
sc.render.resolution_x, sc.render.resolution_y = int(argv[3]) if len(argv) > 3 else 400, int(argv[4]) if len(argv) > 4 else 700
for i, (clip, fr, yaw, zt, dist) in enumerate(shots):
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = bpy.data.actions[clip] if clip != "rest" else None
    if clip == "rest":
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    sc.frame_set(int(fr))
    y = math.radians(float(yaw)); d = float(dist)
    cam.location = (d * math.sin(y), -d * math.cos(y), float(zt))
    cam.rotation_euler = (math.radians(90), 0, y)
    sc.render.filepath = f"{out}_{i}.png"
    bpy.ops.render.render(write_still=True)
