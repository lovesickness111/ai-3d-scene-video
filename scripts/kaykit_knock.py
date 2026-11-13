"""Two rigged KayKit Adventurers (CC0) in a stylized room: the Knight play-knocks the Rogue's head.

Poses come from the animations shipped inside the GLBs (one NLA strip per action), so
"posing" is picking an action + a frame of it, not placing limbs by hand.

python render.py scripts/kaykit_knock.py --out output/kaykit_knock --preview
python render.py scripts/kaykit_knock.py --out output/kaykit_knock --gallery "Unarmed_Melee_Attack_Punch_A:6,10,14;Hit_A:4,8"
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_kit import mat, box, finish, room, look_at

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT/'models'/'kaykit_adventurers'
SCENE_FRAME = 100  # stills are rendered here; NLA strips are shifted so the wanted action frame lands on it


def load_character(glb_name, label):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(MODELS/f'{glb_name}.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == 'ARMATURE')
    rig.name = label
    for o in new:
        if o.type != 'MESH':
            continue
        # keep only the body parts; weapons/shields/the importer's icosphere are extra props
        wanted = o.name.startswith(glb_name+'_')
        o.hide_render = o.hide_viewport = not wanted
        if not wanted:
            o.hide_set(True)
    return rig


def set_pose(rig, action_name, action_frame):
    ad = rig.animation_data
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
        raise SystemExit(f'{rig.name}: action {action_name!r} not found')


def place(rig, loc, yaw_deg, scale=1.0):
    rig.rotation_mode = 'XYZ'  # the glTF importer leaves rigs in QUATERNION mode, where rotation_euler is ignored
    rig.location = loc
    rig.rotation_euler = (0, 0, math.radians(yaw_deg))
    rig.scale = (scale,)*3


def scene_lights(scene, focus):
    def area(name, loc, energy, size, color):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.color = energy, size, color
        o = bpy.data.objects.new(name, data)
        scene.collection.objects.link(o)
        o.location = loc
        o.visible_camera = False
        look_at(o, focus)
    fx, fy, fz = focus
    area('key', (fx+1.8, fy-2.0, fz+1.8), 900, 2.2, (1, .95, .88))
    area('fill', (fx-2.2, fy-1.8, fz+1.0), 260, 3.0, (.8, .88, 1))
    area('rim', (fx-.3, fy+1.8, fz+1.6), 320, 1.2, (1, .85, .7))
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.35, .37, .4, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    scene.world = world


def setup_render(scene, args, out):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.seed = 1
    scene.cycles.use_animated_seed = False
    scene.render.resolution_x, scene.render.resolution_y = args.res_x, args.res_y
    scene.frame_start = scene.frame_end = SCENE_FRAME
    scene.frame_set(SCENE_FRAME)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    out.mkdir(parents=True, exist_ok=True)


def render_to(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print('RENDERED', path)


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='output/kaykit_knock')
    p.add_argument('--samples', type=int, default=32)
    p.add_argument('--res-x', type=int, default=1280)
    p.add_argument('--res-y', type=int, default=720)
    p.add_argument('--preview', action='store_true', help='640x360, 8 samples')
    p.add_argument('--gallery', help='"Action:f1,f2;Action2:f3" -> Knight alone, one still per pose')
    p.add_argument('--knight', default='Unarmed_Melee_Attack_Punch_A:12', help='action:frame')
    p.add_argument('--rogue', default='Hit_A:6', help='action:frame')
    p.add_argument('--gap', type=float, default=.95, help='distance between the two characters')
    p.add_argument('--rogue-scale', type=float, default=.85, help='smaller sibling: puts the head under the fist')
    p.add_argument('--cam', default='1.4,-5.0,1.7', help='camera x,y,z')
    p.add_argument('--aim', default='0,0,0.95', help='camera target x,y,z')
    p.add_argument('--lens', type=float, default=45)
    args = p.parse_args(argv)
    if args.preview:
        args.res_x, args.res_y, args.samples = 640, 360, 8
    out = (ROOT/args.out).resolve()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M = {'floor': mat('floor', (.5, .44, .38), .75), 'wall': mat('wall', (.76, .72, .66), .9),
         'trim': mat('trim', (.9, .88, .84), .5), 'rug': mat('rug', (.55, .3, .25), .9)}
    room(M, size=8, wall_height=3.2)
    box((3.2, 2.2, .02), (0, -.2, .01), M['rug'], bevel=.01)

    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = args.lens
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    setup_render(scene, args, out)

    if args.gallery:
        knight = load_character('Knight', 'knight')
        place(knight, (0, 0, 0), 0)
        scene_lights(scene, (0, 0, .9))
        cam.location = (1.4, -4.4, 1.5)
        look_at(cam, (0, 0, 1.0))
        for spec in args.gallery.split(';'):
            action, frames = spec.split(':')
            for f in frames.split(','):
                set_pose(knight, action, int(f))
                scene.frame_set(SCENE_FRAME)
                render_to(scene, out/'gallery'/f'{action}_{int(f):02d}.png')
        return

    knight = load_character('Knight', 'knight')
    rogue = load_character('Rogue', 'rogue')
    k_action, k_frame = args.knight.split(':')
    r_action, r_frame = args.rogue.split(':')
    set_pose(knight, k_action, int(k_frame))
    set_pose(rogue, r_action, int(r_frame))
    # characters face -Y after import; turn them to face each other across X
    place(knight, (-args.gap/2, 0, 0), 90)
    place(rogue, (args.gap/2, 0, 0), -90, args.rogue_scale)
    scene_lights(scene, (0, 0, 1.0))
    cam.location = tuple(float(v) for v in args.cam.split(','))
    look_at(cam, tuple(float(v) for v in args.aim.split(',')))
    scene.frame_set(SCENE_FRAME)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    render_to(scene, out/'scene.png')


main()
