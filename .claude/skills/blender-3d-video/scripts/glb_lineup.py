"""Line up GLB characters from models/ to see what a pack looks like (one still).

python render.py <skill>/scripts/glb_lineup.py --out output/lineup --preview \
    --chars "kaykit_adventurers/Knight:Idle:1,kaykit_adventurers/Barbarian:Cheer:20,quaternius_modular_men/Suit"
Entry = <models subdir>/<FileStem>[:Action[:frame]]; without an action the file's rest pose is used
(--arms-down lowers T-pose arms of Quaternius rigs).
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_lib import SCENE_FRAME, load_character, set_pose, place, arms_down, actions_of


def look_at(obj, target):
    obj.rotation_euler = (Vector(target)-Vector(obj.location)).to_track_quat('-Z', 'Y').to_euler()


def flat_material(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*[v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb], 1)
    bsdf.inputs['Roughness'].default_value = rough
    return m


def slab(size, loc, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.scale = size
    o.data.materials.append(m)
    return o


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='output/lineup')
    p.add_argument('--models', default='models')
    p.add_argument('--chars', required=True)
    p.add_argument('--spacing', type=float, default=1.0)
    p.add_argument('--arms-down', type=float, default=0.0)
    p.add_argument('--samples', type=int, default=32)
    p.add_argument('--res-x', type=int, default=1600)
    p.add_argument('--res-y', type=int, default=700)
    p.add_argument('--preview', action='store_true', help='960x420, 8 samples')
    args = p.parse_args(argv)
    if args.preview:
        args.res_x, args.res_y, args.samples = 960, 420, 8
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    slab((40, 40, .02), (0, 0, -.01), flat_material('floor', (.5, .44, .38), .75))
    slab((40, .1, 4), (0, 1.3, 2), flat_material('wall', (.76, .72, .66), .9))

    entries = [e.strip() for e in args.chars.split(',') if e.strip()]
    n = len(entries)
    for i, entry in enumerate(entries):
        parts = entry.split(':')
        rig = load_character(Path(args.models)/(parts[0]+'.glb'), f'char{i}')
        if len(parts) > 1:
            set_pose(rig, parts[1], int(parts[2]) if len(parts) > 2 else 1)
        else:
            print(f'{parts[0]}: rest pose; actions in file: {actions_of(rig) or "none"}')
        if args.arms_down:
            arms_down(rig, args.arms_down)
        place(rig, ((i-(n-1)/2)*args.spacing, 0, 0), yaw_deg=8*((n-1)/2-i))

    width = max(3.0, n*args.spacing)
    for name, loc, energy, size, color in (('key', (width*.4, -3.0, 3.0), 1400, 3.0, (1, .95, .88)),
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

    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.lens = 35
    scene.collection.objects.link(cam)
    cam.location = (0, -(width*.95+1.2), 1.4)
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
