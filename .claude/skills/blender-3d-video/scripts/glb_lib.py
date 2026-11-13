"""bpy helpers for rigged/static GLB packs (KayKit, Quaternius mirror). Import inside Blender only.

    sys.path.insert(0, '<this dir>'); from glb_lib import *
    rig = load_character('models/kaykit_adventurers/Knight.glb', 'knight')
    set_pose(rig, 'Hit_B', 3)                 # pick a frame of a shipped animation (KayKit)
    arms_down(rig, 72)                        # Quaternius mirror has no animations: lower the T-pose arms
    place(rig, (-.4, 0, 0), yaw_deg=90)       # moves the holder empty, never the imported transforms
    holder, lo, hi = load_prop('models/quaternius_house_interior/Chair_1.glb', 'chair', scale=.5)
"""
import math

import bpy
from mathutils import Vector

SCENE_FRAME = 100  # stills render here; set_pose shifts NLA strips so the wanted animation frame lands on it


def _import(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def _hide(o):
    o.hide_render = o.hide_viewport = True
    o.hide_set(True)


def _holder(new, label):
    """Parent the imported top-level objects to a fresh empty; the importer's Y-up fix stays untouched."""
    holder = bpy.data.objects.new(label, None)
    bpy.context.scene.collection.objects.link(holder)
    for o in new:
        if o.parent is None and not o.hide_render:
            o.parent = holder
    return holder


def load_character(path, label, keep_prefix=None):
    """Import a rigged GLB. Keeps meshes named <FileStem>_* (body parts), hides weapons/Icosphere.
    Returns the armature; its holder empty is in rig['holder']."""
    path = str(path)
    new = _import(path)
    rig = next(o for o in new if o.type == 'ARMATURE')
    rig.name = label
    stem = path.replace('\\', '/').split('/')[-1].rsplit('.', 1)[0]
    prefix = keep_prefix or stem.split('_')[0]+'_'
    for o in new:
        if o.type == 'MESH' and not o.name.startswith(prefix):
            _hide(o)
    holder = _holder(new, label+'_holder')
    rig['holder'] = holder.name
    return rig


def holder_of(rig):
    return bpy.data.objects[rig['holder']]


def place(rig_or_holder, loc, yaw_deg=0.0, scale=1.0):
    h = holder_of(rig_or_holder) if rig_or_holder.type == 'ARMATURE' else rig_or_holder
    h.location = loc
    h.rotation_euler = (0, 0, math.radians(yaw_deg))
    h.scale = (scale,)*3
    return h


def actions_of(rig):
    ad = rig.animation_data
    if ad is None:
        return []
    return sorted({t.strips[0].action.name.split('.')[0] for t in ad.nla_tracks if t.strips})


def set_pose(rig, action_name, action_frame, scene_frame=SCENE_FRAME):
    """Freeze `rig` at frame `action_frame` of `action_name` when the scene is at `scene_frame`."""
    ad = rig.animation_data
    if ad is None or not ad.nla_tracks:
        raise ValueError(f'{rig.name}: file has no animations; pose bones by hand (arms_down) instead')
    ad.action = None
    found = False
    for track in ad.nla_tracks:
        strip = track.strips[0]
        hit = strip.action.name.split('.')[0] == action_name and not found
        track.mute = not hit
        if hit:
            found = True
            strip.frame_start = scene_frame-action_frame
            strip.frame_end = strip.frame_start+(strip.action_frame_end-strip.action_frame_start)
            strip.extrapolation = 'HOLD'
            strip.blend_type = 'REPLACE'
    if not found:
        raise ValueError(f'{rig.name}: no action {action_name!r}; have {actions_of(rig)}')


def play_action(rig, action_name, at_frame):
    """For videos: start `action_name` at scene frame `at_frame` and hold its last pose afterwards.
    Call once per rig; chain several actions by calling set_pose-style strip edits yourself if needed."""
    ad = rig.animation_data
    ad.action = None
    for track in ad.nla_tracks:
        strip = track.strips[0]
        hit = strip.action.name.split('.')[0] == action_name
        track.mute = not hit
        if hit:
            strip.frame_start = at_frame
            strip.frame_end = at_frame+(strip.action_frame_end-strip.action_frame_start)
            strip.extrapolation = 'HOLD'
            return strip
    raise ValueError(f'{rig.name}: no action {action_name!r}')


def arms_down(rig, degrees=72):
    """Quaternius rigs rest in a T-pose: rotate UpperArm.L/R about local X (negative = down, both sides)."""
    for name in ('UpperArm.L', 'UpperArm.R'):
        pb = rig.pose.bones.get(name)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (math.radians(-degrees), 0, 0)


def bone_rotate(rig, bone, xyz_deg):
    """Manual posing for un-animated rigs; find axes by rendering 640x360 stills, one axis at a time."""
    pb = rig.pose.bones[bone]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = tuple(math.radians(v) for v in xyz_deg)


def world_bounds(objects):
    corners = [o.matrix_world @ Vector(c) for o in objects if o.type == 'MESH' and not o.hide_render for c in o.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return lo, hi


def load_prop(path, label, scale=1.0, on_floor=True):
    """Import a static GLB (furniture, computers). Quaternius interior props need scale≈0.5.
    Returns (holder, lo, hi) with lo/hi the world bounds after scaling."""
    new = _import(str(path))
    for o in new:
        if o.type == 'MESH' and o.name.startswith('Icosphere'):
            _hide(o)
    holder = _holder(new, label)
    holder.scale = (scale,)*3
    bpy.context.view_layer.update()
    lo, hi = world_bounds(new)
    if on_floor:
        holder.location = (-(lo.x+hi.x)/2, -(lo.y+hi.y)/2, -lo.z)
        bpy.context.view_layer.update()
        lo, hi = world_bounds(new)
    return holder, lo, hi
