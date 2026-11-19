"""Orthographic front/side/back renders of the object in a .blend at the sheet's pixel scale, for overlay checks.
usage: ortho.py file.blend outprefix [solid|material]"""
import sys, math, numpy as np, bpy
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
pref, mode = argv[1], (argv[2] if len(argv) > 2 else "solid")
d = np.load("./hull.npz")
PX = float(d["px"])
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT" if mode == "solid" else "FLAT"
sc.display.shading.color_type = "SINGLE" if mode == "solid" else "TEXTURE"
sc.display.shading.single_color = (1, 1, 1)
sc.display.shading.background_type = "VIEWPORT" if False else "WORLD"
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (0, 0, 0)
sc.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
H = 1.76
cam.data.ortho_scale = H
res_y = int(round(H / PX))
sc.render.resolution_y = res_y
sc.render.resolution_x = res_y
sc.render.resolution_percentage = 100
for name, yaw in (("front", 0), ("side", -90), ("back", 180)):
    y = math.radians(yaw)
    cam.location = (8 * math.sin(y), -8 * math.cos(y), H / 2 - 0.01)
    cam.rotation_euler = (math.radians(90), 0, y)
    sc.render.filepath = f"{pref}_{name}.png"
    bpy.ops.render.render(write_still=True)
