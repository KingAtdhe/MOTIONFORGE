"""MOTIONFORGE trainer rig: one humanoid armature with stable bone names (see BONES)."""
import bpy
from mathutils import Vector

from trainer_body import J

# name: (head, tail, parent, deform)
def bone_table():
    t = {
        "root": (Vector((0, 0, 0)), Vector((0, 0.0, 0.25)), None, False),
        "hips": (J["pelvis"], J["spine"], "root", True),
        "spine": (J["spine"], J["chest"], "hips", True),
        "chest": (J["chest"], J["neck"], "spine", True),
        "neck": (J["neck"], J["head"], "chest", True),
        "head": (J["head"], J["head_top"], "neck", True),
    }
    for s in ("L", "R"):
        t[f"shoulder_{s}"] = (J[f"shoulder_{s}"], J[f"upper_arm_{s}"], "chest", True)
        t[f"upper_arm_{s}"] = (J[f"upper_arm_{s}"], J[f"forearm_{s}"], f"shoulder_{s}", True)
        t[f"forearm_{s}"] = (J[f"forearm_{s}"], J[f"hand_{s}"], f"upper_arm_{s}", True)
        t[f"hand_{s}"] = (J[f"hand_{s}"], J[f"hand_tip_{s}"], f"forearm_{s}", True)
        t[f"thigh_{s}"] = (J[f"thigh_{s}"], J[f"shin_{s}"], "hips", True)
        t[f"shin_{s}"] = (J[f"shin_{s}"], J[f"foot_{s}"], f"thigh_{s}", True)
        t[f"foot_{s}"] = (J[f"foot_{s}"], J[f"toe_{s}"], f"shin_{s}", True)
    return t


BONES = list(bone_table().keys())


def build_armature():
    arm_data = bpy.data.armatures.new("trainer_rig")
    arm = bpy.data.objects.new("trainer_rig", arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    table = bone_table()
    for name, (head, tail, _, deform) in table.items():
        eb = arm_data.edit_bones.new(name)
        eb.head, eb.tail = head, tail
        eb.roll = 0.0
        eb.use_deform = deform
    for name, (_, _, parent, _) in table.items():
        if parent:
            eb = arm_data.edit_bones[name]
            eb.parent = arm_data.edit_bones[parent]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def skin(body, parts, arm):
    """Automatic (heat) weights for the body; rigid binding for head, hands and shoes; then join."""
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    rigid = {"trainer_head": "head", "trainer_hair": "head"}
    for s in ("L", "R"):
        rigid[f"trainer_hand_{s}"] = f"hand_{s}"
        rigid[f"trainer_shoe_{s}"] = f"foot_{s}"
    for part in parts:
        group = part.vertex_groups.new(name=rigid[part.name])
        group.add(range(len(part.data.vertices)), 1.0, "REPLACE")

    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "trainer_avatar"
    body.data.name = "trainer_avatar"
    return body
