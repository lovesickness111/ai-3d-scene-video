"""Turn a single photo + depth map into a short 3D parallax video.

python render.py scripts/photo_parallax.py --photo Example_2D_Image.jpeg \
    --depth output/photo_test/depth.png --out output/photo_test --samples 32
"""
import argparse
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


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


def build_photo_plane(photo_path, depth_path, depth_strength, invert_depth):
    img = bpy.data.images.load(str(photo_path))
    w, h = img.size
    aspect = w / h

    long_edge = 220
    if aspect >= 1:
        x_sub, y_sub = long_edge, max(2, round(long_edge / aspect))
    else:
        x_sub, y_sub = max(2, round(long_edge * aspect)), long_edge

    bpy.ops.mesh.primitive_grid_add(x_subdivisions=x_sub, y_subdivisions=y_sub, size=2)
    obj = bpy.context.active_object
    obj.scale = (aspect, 1, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # Rotate (unapplied) so the flat grid's normal (local Z, the Displace axis)
    # points along world Y -- toward/away from the camera -- instead of up.
    obj.rotation_euler = (math.radians(90), 0, 0)

    mat = bpy.data.materials.new('photo')
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out_node = nt.nodes.new('ShaderNodeOutputMaterial')
    emit = nt.nodes.new('ShaderNodeEmission')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nt.links.new(tex.outputs['Color'], emit.inputs['Color'])
    nt.links.new(emit.outputs['Emission'], out_node.inputs['Surface'])
    obj.data.materials.append(mat)

    depth_img = bpy.data.images.load(str(depth_path))
    depth_img.colorspace_settings.name = 'Non-Color'
    depth_tex = bpy.data.textures.new('depth', 'IMAGE')
    depth_tex.image = depth_img
    disp = obj.modifiers.new('depth', 'DISPLACE')
    disp.texture = depth_tex
    disp.texture_coords = 'UV'
    disp.direction = 'Z'
    disp.mid_level = 0.5
    disp.strength = -depth_strength if invert_depth else depth_strength

    return obj, aspect


def animate_camera(cam, aspect, frame_end, pan, push_in):
    fov_h = 2 * math.atan(cam.data.sensor_width / (2 * cam.data.lens))
    margin = 0.94
    distance = aspect / math.tan(fov_h / 2) / margin

    cam.location = (-pan, -distance, 0)
    look_at(cam, (0, 0, 0))
    hold(cam, 1)
    cam.location = (pan, -distance * (1 - push_in), 0)
    look_at(cam, (0, 0, 0))
    hold(cam, frame_end)


def lights(scene):
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
    scene.world = world


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--photo', required=True)
    parser.add_argument('--depth', required=True)
    parser.add_argument('--out', default='output/photo_parallax')
    parser.add_argument('--engine', choices=('eevee', 'cycles'), default='cycles')
    parser.add_argument('--samples', type=int, default=24)
    parser.add_argument('--duration', type=float, default=5.0, help='seconds of video')
    parser.add_argument('--fps', type=int, default=12)
    parser.add_argument('--res-x', type=int, default=960)
    parser.add_argument('--depth-strength', type=float, default=0.07)
    parser.add_argument('--invert-depth', action='store_true', help='flip near/far relief')
    parser.add_argument('--pan', type=float, default=0.12, help='lateral camera shift, world units')
    parser.add_argument('--push-in', type=float, default=0.08, help='fraction of distance to dolly in')
    parser.add_argument('--preview', action='store_true', help='render only frame 1, ignore --duration')
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.view_settings.view_transform = 'Standard'

    plane, aspect = build_photo_plane(Path(args.photo).resolve(), Path(args.depth).resolve(),
                                       args.depth_strength, args.invert_depth)

    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = 50
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    frame_end = 1 if args.preview else max(2, round(args.duration*args.fps))
    scene.frame_start, scene.frame_end, scene.render.fps = 1, frame_end, args.fps
    animate_camera(cam, aspect, frame_end, args.pan, args.push_in)
    lights(scene)

    res_y = round(args.res_x / aspect)
    scene.render.resolution_x, scene.render.resolution_y = args.res_x, res_y

    if args.engine == 'cycles':
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True
        scene.cycles.seed = 1
        scene.cycles.use_animated_seed = False
    else:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.eevee.taa_render_samples = args.samples

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
