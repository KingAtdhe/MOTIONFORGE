"""Preview rendering helpers (Cycles CPU, works headless). Used for visual QA only."""
import math
import bpy
from mathutils import Vector


def setup_scene(resolution=(480, 640), samples=24):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("preview_world") if scene.world is None else scene.world
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.16, 0.17, 0.18, 1)
    bg.inputs[1].default_value = 0.9
    # key + fill lights
    for name, loc, energy in (("key", (-2.2, -3.0, 3.2), 900), ("fill", (2.5, -2.0, 1.8), 350), ("rim", (0.5, 3.0, 2.8), 500)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy
        light.size = 2.0
        obj = bpy.data.objects.new(name, light)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        direction = Vector((0, 0, 1.0)) - Vector(loc)
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    # floor
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "preview_floor"
    fm = bpy.data.materials.new("preview_floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.055, 0.06, 1)
    floor.data.materials.append(fm)
    cam_data = bpy.data.cameras.new("preview_cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("preview_cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return cam


def aim_camera(cam, yaw_deg, distance=4.6, target=(0, 0, 0.9), height=1.05):
    yaw = math.radians(yaw_deg)
    # yaw 0 = front of character (character faces -Y)
    cam.location = (target[0] + distance * math.sin(yaw), target[1] - distance * math.cos(yaw), height)
    direction = Vector(target) - Vector(cam.location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
