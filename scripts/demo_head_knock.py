"""Stylized still: two standing characters, one play-knocking the other's head.

python render.py scripts/demo_head_knock.py --out output/demo_head_knock
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_kit import mat, finish, box, ball, cyl, limb, group, room, look_at, lights


def figure(M, name, loc, yaw, *, lean, knee, hoodie, pants, hair, mouth, head_pitch, skin='skin'):
    """Local convention (matches character_kit style): -Y = front, +X = right, +Z = up."""
    f = group(name, loc, yaw)
    hip_z = .78 - knee*.1
    for s in (-1, 1):
        limb((s*.1, 0, hip_z), (s*.105, .02, hip_z-.38), .065, M[pants], f)
        limb((s*.105, .02, hip_z-.38), (s*.11, .02-knee*.12, .06), .055, M[pants], f)
        box((.11, .2, .07), (s*.11, -.02-knee*.1, .035), M['shoe'], f, bevel=.02)
    box((.3, .26, .18), (0, 0, hip_z), M[pants], f, bevel=.04)

    torso = group('torso', (0, 0, hip_z+.09), 0, f)
    torso.rotation_euler.x = math.radians(lean)
    box((.34, .25, .42), (0, 0, .2), M[hoodie], torso, bevel=.08)
    bpy.ops.mesh.primitive_torus_add(major_radius=.1, minor_radius=.038, location=(0, 0, .4))
    finish(bpy.context.active_object, M[hoodie], torso, smooth=True)
    cyl(.05, .09, (0, 0, .44), M[skin], torso)

    head = group('head', (0, 0, .48), 0, torso)
    head.rotation_euler.x = math.radians(head_pitch)
    ball(.13, (0, -.01, .13), M[skin], head, scale=(1, 1, 1.08))
    ball(.136, (0, .015, .17), M[hair], head, scale=(1.02, 1, .85))
    for s in (-1, 1):
        ball(.03, (s*.13, -.01, .13), M[skin], head, scale=(.6, 1, 1))
        ball(.013, (s*.055, -.125, .145), M['dark'], head)
    ball(.018, (0, -.145, .11), M[skin], head)
    ball(.022, (0, -.122, .075), M[mouth], head, scale=(1.2, .5, .6))
    return f, torso, head


def knocker_arms(M, f, shoulder_local, fist_local, hoodie, skin):
    # relaxed left arm, straight down (torso-attached, lean is small so this is close enough)
    limb((-.17, -.02, 1.23), (-.2, -.1, .97), .048, M[hoodie], f)
    ball(.04, (-.2, -.12, .93), M[skin], f)
    # raised/windup right arm: shoulder -> raised elbow -> fist resting on the target head
    elbow = ((shoulder_local[0]+fist_local[0])/2, (shoulder_local[1]+fist_local[1])/2-.08,
             max(shoulder_local[2], fist_local[2])+.1)
    limb(shoulder_local, elbow, .048, M[hoodie], f)
    limb(elbow, fist_local, .042, M[skin], f)
    ball(.05, fist_local, M[skin], f)


def victim_arms(M, torso, hoodie, skin):
    for s in (-1, 1):
        limb((s*.17, -.02, .36), (s*.16, -.16, .5), .046, M[hoodie], torso)
        limb((s*.16, -.16, .5), (s*.11, -.26, .55), .04, M[skin], torso)
        ball(.044, (s*.1, -.28, .56), M[skin], torso)


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='output/demo_head_knock')
    parser.add_argument('--engine', choices=('eevee', 'cycles'), default='cycles')
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--res-x', type=int, default=1280)
    parser.add_argument('--res-y', type=int, default=720)
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M = {
        'floor': mat('floor', (.52, .45, .38), .7), 'wall': mat('wall', (.8, .77, .71), .9),
        'trim': mat('trim', (.9, .88, .84), .5),
        'shoe': mat('shoe', (.92, .92, .9), .5), 'dark': mat('dark', (.03, .03, .035), .4),
        'skin': mat('skin', (.89, .7, .56), .55),
        'hoodie_a': mat('hoodie_a', (.75, .46, .14), .8), 'pants_a': mat('pants_a', (.22, .22, .25), .8),
        'hair_a': mat('hair_a', (.08, .06, .05), .7), 'mouth_grin': mat('mouth_grin', (.5, .16, .12), .5),
        'hoodie_b': mat('hoodie_b', (.24, .42, .46), .8), 'pants_b': mat('pants_b', (.3, .28, .36), .8),
        'hair_b': mat('hair_b', (.32, .2, .1), .7), 'mouth_ouch': mat('mouth_ouch', (.55, .2, .18), .5),
    }
    room(M, size=8, wall_height=3.4)

    knocker_f, knocker_t, knocker_h = figure(
        M, 'knocker', (-.34, 0, 0), 90, lean=14, knee=0, hoodie='hoodie_a', pants='pants_a',
        hair='hair_a', mouth='mouth_grin', head_pitch=10)

    victim_f, victim_t, victim_h = figure(
        M, 'victim', (.4, 0, 0), -90, lean=32, knee=.4, hoodie='hoodie_b', pants='pants_b',
        hair='hair_b', mouth='mouth_ouch', head_pitch=18)
    victim_arms(M, victim_t, 'hoodie_b', 'skin')

    bpy.context.view_layer.update()
    head_top_world = victim_h.matrix_world.translation+Vector((0, 0, .11))
    fist_local = knocker_f.matrix_world.inverted() @ head_top_world
    shoulder_local = (.17, -.02, 1.23)
    knocker_arms(M, knocker_f, shoulder_local, tuple(fist_local), 'hoodie_a', 'skin')

    lights(scene)

    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = 42
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.55, -2.3, 1.2)
    look_at(cam, (0.05, 0, 1.0))
    scene.camera = cam

    if args.engine == 'cycles':
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True
        scene.cycles.seed = 1
    else:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.eevee.taa_render_samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = args.res_x, args.res_y
    scene.render.filepath = str(out/'scene.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    bpy.ops.render.render(write_still=True)
    print('RENDERED', out/'scene.png')


main()
