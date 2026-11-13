"""Line up several KayKit GLB characters side by side, each in a chosen animation frame.

python render.py scripts/kaykit_lineup.py --out output/kaykit_lineup --preview \
    --chars "kaykit_adventurers/Knight:Idle:1,kaykit_adventurers/Mage:Cheer:20"
Entry format: <models subdir>/<GlbName>[:Action[:frame]] ; name prefix of body meshes = GlbName before '_'.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_kit import mat, box, room, look_at

ROOT = Path(__file__).resolve().parents[1]
SCENE_FRAME = 100


def load_character(glb_path, label):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == 'ARMATURE')
    rig.name = label
    prefix = glb_path.stem.split('_')[0]+'_'
    for o in new:
        if o.type == 'MESH':
            wanted = o.name.startswith(prefix)
            o.hide_render = o.hide_viewport = not wanted
            if not wanted:
                o.hide_set(True)
    # Never touch the imported transforms (the importer may store the Y-up -> Z-up fix as a
    # rotation on the rig or a RootNode); move/turn the whole character through a holder empty.
    top = rig
    while top.parent is not None:
        top = top.parent
    holder = bpy.data.objects.new(label+'_holder', None)
    bpy.context.scene.collection.objects.link(holder)
    top.parent = holder
    rig['holder'] = holder.name
    return rig


def arms_down(rig, degrees, axis='Z'):
    """Rest poses of un-animated GLBs are usually T/A-poses; swing the upper arms down.
    Bone names cover both KayKit (upperarm.l) and Quaternius (UpperArm.L) rigs."""
    idx = 'XYZ'.index(axis.upper())
    # Quaternius rigs: local X is the "swing down" axis and both arms share its sign
    sides = (('l', -1), ('r', -1)) if idx == 0 else (('l', 1), ('r', -1))
    for side, sign in sides:
        for name in (f'upperarm.{side}', f'UpperArm.{side.upper()}'):
            pb = rig.pose.bones.get(name)
            if pb:
                pb.rotation_mode = 'XYZ'
                rot = [0.0, 0.0, 0.0]
                rot[idx] = math.radians(sign*degrees)
                pb.rotation_euler = rot


def set_pose(rig, action_name, action_frame):
    ad = rig.animation_data
    if ad is None or not ad.nla_tracks:
        print(f'{rig.name}: no animations in file, keeping rest pose')
        return
    ad.action = None
    found = False
    for track in ad.nla_tracks:
        strip = track.strips[0]
        hit = strip.action.name.split('.')[0] == action_name and not found
        track.mute = not hit
        if hit:
            found = True
            strip.frame_start = SCENE_FRAME-action_frame
            strip.frame_end = strip.frame_start+(strip.action_frame_end-strip.action_frame_start)
            strip.extrapolation = 'HOLD'
            strip.blend_type = 'REPLACE'
    if not found:
        names = sorted({t.strips[0].action.name.split('.')[0] for t in ad.nla_tracks})
        raise SystemExit(f'{rig.name}: action {action_name!r} not found; have {names}')


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='output/kaykit_lineup')
    p.add_argument('--chars', required=True)
    p.add_argument('--spacing', type=float, default=1.1)
    p.add_argument('--arms-down', type=float, default=0.0, help='degrees to rotate upper arms down (for rest-pose GLBs)')
    p.add_argument('--arms-axis', default='Z', help='local bone axis for --arms-down (X, Y or Z)')
    p.add_argument('--yaw', type=float, default=0.0, help='extra yaw for every character (fix files that face +Y)')
    p.add_argument('--cam-h', type=float, default=1.4)
    p.add_argument('--samples', type=int, default=32)
    p.add_argument('--res-x', type=int, default=1600)
    p.add_argument('--res-y', type=int, default=700)
    p.add_argument('--preview', action='store_true')
    args = p.parse_args(argv)
    if args.preview:
        args.res_x, args.res_y, args.samples = 960, 420, 8
    out = (ROOT/args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M = {'floor': mat('floor', (.5, .44, .38), .75), 'wall': mat('wall', (.76, .72, .66), .9),
         'trim': mat('trim', (.9, .88, .84), .5)}
    # floor + back wall only: a side wall would hide the characters at the ends of the line
    box((30, 30, .02), (0, 0, -.01), M['floor'])
    box((30, .1, 4), (0, 1.3, 2), M['wall'])
    box((30, .02, .12), (0, 1.24, .06), M['trim'])

    entries = [e.strip() for e in args.chars.split(',') if e.strip()]
    n = len(entries)
    for i, entry in enumerate(entries):
        parts = entry.split(':')
        rel, action, frame = parts[0], (parts[1] if len(parts) > 1 else 'Idle'), int(parts[2]) if len(parts) > 2 else 1
        rig = load_character(ROOT/'models'/(rel+'.glb'), f'char{i}')
        set_pose(rig, action, frame)
        if args.arms_down:
            arms_down(rig, args.arms_down, args.arms_axis)
        holder = bpy.data.objects[rig['holder']]
        holder.location = ((i-(n-1)/2)*args.spacing, 0, 0)
        holder.rotation_euler = (0, 0, math.radians(args.yaw+8*((n-1)/2-i)))  # fan slightly toward the camera

    width = max(3.0, n*args.spacing)
    for name, loc, energy, size, color in (
            ('key', (width*.4, -3.0, 3.0), 1400, 3.0, (1, .95, .88)),
            ('fill', (-width*.4, -3.2, 1.6), 500, 4.0, (.8, .88, 1)),
            ('rim', (0, 2.0, 2.8), 500, 2.0, (1, .85, .7))):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.color = energy, size, color
        o = bpy.data.objects.new(name, data)
        scene.collection.objects.link(o)
        o.location = loc
        o.visible_camera = False
        look_at(o, (0, 0, .9))
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.35, .37, .4, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    scene.world = world

    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = 35
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    dist = width*.95+1.2
    cam.location = (0, -dist, args.cam_h)
    look_at(cam, (0, 0, .95))
    scene.camera = cam

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.seed = 1
    scene.render.resolution_x, scene.render.resolution_y = args.res_x, args.res_y
    scene.view_settings.view_transform = 'AgX'
    scene.frame_start = scene.frame_end = SCENE_FRAME
    scene.frame_set(SCENE_FRAME)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    scene.render.filepath = str(out/'lineup.png')
    bpy.ops.render.render(write_still=True)
    print('RENDERED', out/'lineup.png')


main()
