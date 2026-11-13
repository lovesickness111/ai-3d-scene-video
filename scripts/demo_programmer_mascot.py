"""Stylized still: a programmer chatting with an orange blocky Claude-style mascot.

python render.py scripts/demo_programmer_mascot.py --out output/demo_programmer_mascot
"""
import argparse
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_kit import linear, mat, finish, box, ball, cyl, limb, group, room, look_at, lights as kit_lights


def desk(M):
    box((1.6, .7, .05), (0, 0, .725), M['wood'], bevel=.01)
    for x in (-.75, .75):
        for y in (-.3, .3):
            box((.05, .05, .7), (x, y, .35), M['metal'])
    lap = group('laptop', (-.2, -.05, .75), 8)
    box((.34, .24, .018), (0, 0, .009), M['alu'], lap, bevel=.004)
    box((.3, .1, .002), (0, -.03, .019), M['dark'], lap)
    hinge = group('lid', (0, .12, .018), 0, lap)
    hinge.rotation_euler.x = math.radians(-14)
    box((.34, .012, .23), (0, 0, .115), M['alu'], hinge, bevel=.004)
    box((.31, .002, .2), (0, -.0065, .115), M['screen'], hinge)
    rng = random.Random(7)
    code_colors = [M['code_a'], M['code_b'], M['code_c']]
    for i in range(10):
        w = rng.uniform(.05, .2)
        indent = rng.choice((0, .02, .04))
        box((w, .002, .008), (-.13+indent+w/2, -.009, .2-i*.017), rng.choice(code_colors), hinge)
    mug = group('mug', (.2, .18, .75))
    cyl(.04, .1, (0, 0, .05), M['mug'], mug)
    cyl(.034, .002, (0, 0, .098), M['coffee'], mug)
    bpy.ops.mesh.primitive_torus_add(major_radius=.026, minor_radius=.007, location=(.045, 0, .05),
                                     rotation=(math.radians(90), 0, 0))
    finish(bpy.context.active_object, M['mug'], mug, smooth=True)
    pot = group('plant', (-.65, .18, .75))
    cyl(.06, .11, (0, 0, .055), M['pot'], pot)
    for dx, dy, dz, r in ((0, 0, .17, .07), (.04, .02, .21, .05), (-.04, -.01, .22, .055), (.0, .03, .26, .045)):
        ball(r, (dx, dy, dz), M['leaf'], pot)


def programmer(M, loc, yaw, head_yaw):
    p = group('programmer', loc, yaw, scale=1.0)
    p.rotation_mode = 'XYZ'
    box((.48, .46, .07), (0, .02, .44), M['chair'], p, bevel=.02)
    box((.46, .06, .52), (0, .26, .8), M['chair'], p, bevel=.025, rot=(math.radians(-8), 0, 0))
    cyl(.03, .32, (0, .02, .25), M['metal'], p)
    cyl(.28, .03, (0, .02, .06), M['metal'], p)
    box((.36, .3, .16), (0, .04, .55), M['jeans'], p, bevel=.05)
    for s in (-1, 1):
        limb((s*.1, .02, .56), (s*.11, -.38, .56), .075, M['jeans'], p)
        limb((s*.11, -.4, .54), (s*.115, -.43, .12), .062, M['jeans'], p)
        box((.11, .22, .07), (s*.115, -.48, .045), M['shoe'], p, bevel=.025)
    box((.42, .26, .5), (0, .05, .87), M['hoodie'], p, bevel=.09, rot=(math.radians(-6), 0, 0))
    for s in (-1, 1):
        limb((s*.04, -.08, 1.04), (s*.045, -.095, .9), .006, M['string'], p)
    bpy.ops.mesh.primitive_torus_add(major_radius=.1, minor_radius=.04, location=(0, .05, 1.1))
    finish(bpy.context.active_object, M['hoodie'], p, smooth=True)
    cyl(.05, .12, (0, .03, 1.15), M['skin'], p)

    h = group('head', (0, .03, 1.15), head_yaw, p)
    ball(.13, (0, -.01, .15), M['skin'], h, scale=(1, 1, 1.08))
    ball(.136, (0, .02, .2), M['hair'], h, scale=(1.02, 1, .82))
    ball(.06, (.03, -.09, .245), M['hair'], h, scale=(1.4, .8, .5))
    for s in (-1, 1):
        ball(.03, (s*.13, -.01, .15), M['skin'], h, scale=(.6, 1, 1))
        ball(.016, (s*.046, -.128, .165), M['dark'], h)
        bpy.ops.mesh.primitive_torus_add(major_radius=.032, minor_radius=.0055, location=(s*.047, -.143, .165),
                                         rotation=(math.radians(90), 0, 0))
        finish(bpy.context.active_object, M['frame'], h, smooth=True)
        box((.002, .1, .006), (s*.08, -.09, .17), M['frame'], h)
    box((.03, .006, .006), (0, -.146, .168), M['frame'], h)
    ball(.02, (0, -.145, .13), M['skin'], h)
    ball(.022, (0, -.122, .09), M['mouth'], h, scale=(1.2, .5, .6))

    limb((.22, .04, 1.03), (.25, -.04, .8), .055, M['hoodie'], p)
    limb((.25, -.04, .8), (.15, -.3, .66), .05, M['hoodie'], p)
    ball(.045, (.14, -.35, .65), M['skin'], p)
    limb((-.22, .04, 1.03), (-.28, -.08, .82), .055, M['hoodie'], p)
    limb((-.28, -.08, .82), (-.22, -.32, .98), .05, M['hoodie'], p)
    ball(.045, (-.21, -.36, 1.01), M['skin'], p, scale=(.8, .6, 1.1))
    return p, h


def mascot(M, loc, yaw, scale):
    c = group('mascot', loc, yaw, scale=scale)
    for x in (-.095, -.035, .035, .095):
        box((.035, .045, .05), (x, 0, .025), M['clawd'], c, bevel=.004)
    box((.26, .13, .15), (0, 0, .125), M['clawd'], c, bevel=.01)
    for s in (-1, 1):
        box((.05, .07, .045), (s*.152, 0, .13), M['clawd'], c, bevel=.006)
        box((.022, .01, .042), (s*.055, -.066, .15), M['dark'], c, bevel=.003)
    return c


def bubble(M, loc):
    b = group('bubble', loc)
    ball(.12, (0, 0, 0), M['bubble'], b, scale=(1.5, .25, 1))
    bpy.ops.mesh.primitive_cone_add(radius1=.04, depth=.09, location=(-.06, 0, -.12),
                                    rotation=(0, math.radians(200), 0))
    finish(bpy.context.active_object, M['bubble'], b, smooth=True)
    for i, x in enumerate((-.07, 0, .07)):
        ball(.018, (x, -.035, 0), M['code_c' if i == 1 else 'dark'], b)
    return b


def sway(obj, data_path, amplitude, period_frames, phase=0.0, index=-1, offset=0.0):
    """Smooth continuous sine motion via a driver (no keyframe judder, exact every frame)."""
    fcurve = obj.driver_add(data_path, index) if index >= 0 else obj.driver_add(data_path)
    drv = fcurve.driver
    drv.type = 'SCRIPTED'
    var = drv.variables.new()
    var.name = 'frame'
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'SCENE'
    var.targets[0].id = bpy.context.scene
    var.targets[0].data_path = 'frame_current'
    drv.expression = f'{offset}+{amplitude}*sin(frame/{period_frames}*6.28318+{phase})'


def idle_motion(programmer_root, head, mascot_root, bubble_root):
    sway(mascot_root, 'location', .012, 36, index=2, offset=mascot_root.location.z)
    sway(mascot_root, 'rotation_euler', math.radians(3), 40, phase=1.0, index=2,
         offset=mascot_root.rotation_euler.z)
    sway(head, 'rotation_euler', math.radians(4), 60, index=0, offset=head.rotation_euler.x)
    sway(programmer_root, 'rotation_euler', math.radians(1.5), 90, phase=.6, index=2,
         offset=programmer_root.rotation_euler.z)
    sway(bubble_root, 'scale', .07, 14, offset=1.0, index=0)
    sway(bubble_root, 'scale', .07, 14, offset=1.0, index=1)
    sway(bubble_root, 'scale', .07, 14, offset=1.0, index=2)


def hold(obj, frame, interpolation='BEZIER'):
    obj.keyframe_insert('location', frame=frame)
    obj.keyframe_insert('rotation_euler', frame=frame)
    if obj.animation_data is None:
        return
    for fcurve in obj.animation_data.action.fcurves:
        kp = fcurve.keyframe_points[-1]
        if kp.co.x == frame:
            kp.interpolation = interpolation
            kp.easing = 'EASE_IN_OUT'


def animate_camera(cam, frame_end):
    """3 beats: wide hold -> slow eased push-in -> hold -> hard cut to close hold.

    Kept deliberately simple for a low-fps draft: almost no continuous motion,
    a single short eased push, and one instant cut (cuts read as smooth at any
    fps since there is no interpolation to alias).
    """
    shots = [
        (1, (2.6, -0.9, 1.5), (.2, -.45, .92)),
        (round(frame_end*.31), (2.6, -0.9, 1.5), (.2, -.45, .92)),
        (round(frame_end*.44), (1.7, -0.55, 1.35), (.25, -.35, .95)),
        (round(frame_end*.82), (1.7, -0.55, 1.35), (.25, -.35, .95)),
    ]
    for frame, loc, target in shots:
        cam.location = loc
        look_at(cam, target)
        hold(cam, frame)
    cut_frame = round(frame_end*.82)+1
    cam.location, cam.rotation_euler = (1.7, -0.55, 1.35), cam.rotation_euler.copy()
    look_at(cam, (.25, -.35, .95))
    hold(cam, cut_frame, interpolation='CONSTANT')
    cam.location = (1.35, -0.65, 1.15)
    look_at(cam, (.42, -.16, .9))
    hold(cam, cut_frame+1)
    hold(cam, frame_end)


def lights(scene):
    kit_lights(scene)
    lamp = bpy.data.lights.new('desk_glow', 'POINT')
    lamp.energy, lamp.color, lamp.shadow_soft_size = 25, (1, .7, .45), .2
    o = bpy.data.objects.new('desk_glow', lamp)
    scene.collection.objects.link(o)
    o.location = (.45, .1, 1.05)


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='output/demo_programmer_mascot')
    parser.add_argument('--engine', choices=('eevee', 'cycles'), default='cycles')
    parser.add_argument('--samples', type=int, default=24)
    parser.add_argument('--duration', type=float, default=8.0, help='seconds of video')
    parser.add_argument('--fps', type=int, default=12)
    parser.add_argument('--res-x', type=int, default=960)
    parser.add_argument('--res-y', type=int, default=540)
    parser.add_argument('--preview', action='store_true', help='render only frame 1, ignore --duration')
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M = {
        'floor': mat('floor', (.52, .45, .38), .7), 'wall': mat('wall', (.78, .75, .69), .9),
        'trim': mat('trim', (.9, .88, .84), .5), 'wood': mat('wood', (.62, .45, .3), .45),
        'metal': mat('metal', (.2, .2, .22), .35, metal=.8), 'alu': mat('alu', (.72, .73, .75), .3, metal=.9),
        'dark': mat('dark', (.03, .03, .035), .4), 'screen': mat('screen', (.08, .12, .2), .2, emit=1.5),
        'code_a': mat('code_a', (.45, .75, 1), emit=4), 'code_b': mat('code_b', (.95, .6, .45), emit=4),
        'code_c': mat('code_c', (.6, .9, .55), emit=4), 'mug': mat('mug', (.93, .92, .9), .25),
        'coffee': mat('coffee', (.18, .09, .04), .1), 'pot': mat('pot', (.72, .42, .3), .7),
        'leaf': mat('leaf', (.25, .5, .25), .6), 'chair': mat('chair', (.16, .17, .2), .6),
        'jeans': mat('jeans', (.17, .25, .42), .8), 'shoe': mat('shoe', (.92, .92, .9), .5),
        'hoodie': mat('hoodie', (.28, .36, .3), .85), 'string': mat('string', (.9, .9, .88), .6),
        'skin': mat('skin', (.89, .7, .56), .55), 'hair': mat('hair', (.12, .08, .06), .7),
        'frame': mat('frame', (.06, .06, .07), .3), 'mouth': mat('mouth', (.45, .18, .16), .5),
        'clawd': mat('clawd', (.84, .38, .2), .55), 'bubble': mat('bubble', (.97, .96, .93), .4),
    }
    room(M)
    desk(M)
    p, head = programmer(M, (-.05, -.85, 0), 112, 22)
    c = mascot(M, (.42, -.16, .75), 30, 1.25)
    b = bubble(M, (.5, -.22, 1.2))
    b.rotation_euler.z = math.radians(72)
    lights(scene)

    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = 38
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    frame_end = 1 if args.preview else max(2, round(args.duration*args.fps))
    scene.frame_start, scene.frame_end, scene.render.fps = 1, frame_end, args.fps
    animate_camera(cam, frame_end)
    idle_motion(p, head, c, b)

    if args.engine == 'cycles':
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True
        scene.cycles.seed = 1
        scene.cycles.use_animated_seed = False
    else:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.eevee.taa_render_samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = args.res_x, args.res_y
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))

    frames_dir = out/'frames'
    frames_dir.mkdir(exist_ok=True)
    started = time.monotonic()
    for frame in range(scene.frame_start, scene.frame_end+1):
        scene.frame_set(frame)
        scene.render.filepath = str(frames_dir/f'frame_{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'frame {frame}/{frame_end} ({time.monotonic()-started:.1f}s elapsed)')
    print('RENDERED', frame_end, 'frames into', frames_dir)


main()
