"""Line up static GLB props on a floor for a quick look.

python render.py scripts/props_lineup.py --out output/props --preview --dir models/quaternius_props
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_kit import mat, box, look_at

ROOT = Path(__file__).resolve().parents[1]


def load_prop(glb_path, label):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type == 'MESH' and o.name.startswith('Icosphere'):
            o.hide_render = o.hide_viewport = True
            o.hide_set(True)
    roots = [o for o in new if o.parent is None and not (o.type == 'MESH' and o.name.startswith('Icosphere'))]
    holder = bpy.data.objects.new(label, None)
    bpy.context.scene.collection.objects.link(holder)
    for r in roots:
        r.parent = holder
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in new if o.type == 'MESH' and not o.hide_render for c in o.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return holder, lo, hi


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='output/props')
    p.add_argument('--dir', required=True)
    p.add_argument('--gap', type=float, default=.35)
    p.add_argument('--samples', type=int, default=32)
    p.add_argument('--res-x', type=int, default=1800)
    p.add_argument('--res-y', type=int, default=600)
    p.add_argument('--preview', action='store_true')
    args = p.parse_args(argv)
    if args.preview:
        args.res_x, args.res_y, args.samples = 1200, 400, 8
    out = (ROOT/args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M = {'floor': mat('floor', (.5, .44, .38), .75), 'wall': mat('wall', (.76, .72, .66), .9)}
    box((60, 60, .02), (0, 0, -.01), M['floor'])
    box((60, .1, 6), (0, 2.0, 3), M['wall'])

    files = sorted((ROOT/args.dir).glob('*.glb'))
    x = 0.0
    labels = []
    for f in files:
        holder, lo, hi = load_prop(f, f.stem)
        w = hi.x-lo.x
        holder.location = (x-lo.x, -lo.y-(hi.y-lo.y)/2, -lo.z)
        labels.append((f.stem, x+w/2, round(w, 2), round(hi.y-lo.y, 2), round(hi.z-lo.z, 2)))
        x += w+args.gap
    total = x-args.gap
    for holder in (o for o in scene.objects if o.type == 'EMPTY' and o.parent is None):
        holder.location.x -= total/2
    for name, cx, w, d, h in labels:
        print(f'PROP {name:22s} w={w} d={d} h={h}')

    for name, loc, energy, size, color in (('key', (total*.3, -4, 4), 2500, 4, (1, .95, .88)),
                                           ('fill', (-total*.3, -5, 2), 900, 6, (.8, .88, 1))):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.color = energy, size, color
        o = bpy.data.objects.new(name, data)
        scene.collection.objects.link(o)
        o.location = loc
        o.visible_camera = False
        look_at(o, (0, 0, .6))
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.35, .37, .4, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    scene.world = world

    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = 35
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0, -(total*.95+1.5), 1.6)
    look_at(cam, (0, 0, .7))
    scene.camera = cam

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.seed = 1
    scene.render.resolution_x, scene.render.resolution_y = args.res_x, args.res_y
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    scene.render.filepath = str(out/'props.png')
    bpy.ops.render.render(write_still=True)
    print('RENDERED', out/'props.png')


main()
