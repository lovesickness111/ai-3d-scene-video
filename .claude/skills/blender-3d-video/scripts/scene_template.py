"""Starting point for a new headless Blender scene: a room, the mascot, a two-shot
camera move, and the render loop that renders each distinct picture once.

Copy next to scene_lib.py, rename, replace build() and shots(). Flags are the
ones every scene script in the pipeline shares, so render.py / compose.py /
make_video.py work unchanged.

python render.py scripts/scene_template.py --out output/template --dry-run
python render.py scripts/scene_template.py --out output/template --samples 8 --res-x 640 --res-y 360 --only-frames 1,18,36
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene_lib import build_materials, room, desk, mascot, group, hold, shot_face, lights  # noqa: E402


def build(M):
    """Everything in the scene; returns the objects the camera will aim at."""
    room(M)
    desk(M)
    c, face = mascot(M, (.42, -.16, .75), 30, 1.25)
    return {'claude': group('mascot_face', (0, -.06, .14), parent=c)}


def shots(cam, anchors, fps):
    """Two framings held, with an eased move between them. Returns the last frame."""
    shot_face(cam, anchors['claude'], lens=40, dist=1.7, side=(.9, -.6, .35), low=.15)
    hold(cam, 1)
    hold(cam, fps)                       # hold 1 s
    shot_face(cam, anchors['claude'], lens=40, dist=1.9, side=(.9, -.6, .35), low=.14, aside=.24)
    hold(cam, fps+8)                     # 8 frames of eased move
    hold(cam, 3*fps)
    return 3*fps


def picture_state(scene):
    """Everything that changes the picture between frames; same state -> same render (fixed seed)."""
    return (scene.camera.data.lens,
            *((o.name, o.hide_render, *(round(v, 6) for row in o.matrix_world for v in row)) for o in scene.objects))


def configure_render(scene, args):
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


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='output/template')
    parser.add_argument('--engine', choices=('eevee', 'cycles'), default='cycles')
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--fps', type=int, default=12)
    parser.add_argument('--res-x', type=int, default=1280)
    parser.add_argument('--res-y', type=int, default=720)
    parser.add_argument('--preview', action='store_true', help='render only frame 1')
    parser.add_argument('--only-frames', default='', help='comma-separated frame numbers, skip the rest')
    parser.add_argument('--dry-run', action='store_true', help='render nothing, count the pictures a render would need')
    args = parser.parse_args(argv)

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M = build_materials()
    anchors = build(M)
    lights(scene)
    bpy.context.view_layer.update()  # matrix_world is stale until this

    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    configure_render(scene, args)
    last_frame = shots(cam, anchors, args.fps)

    frame_end = 1 if args.preview else last_frame
    scene.frame_start, scene.frame_end, scene.render.fps = 1, frame_end, args.fps
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    (out/'timeline.json').write_text(json.dumps([{'frame_start': 1, 'voice_frame': 1, 'frame_end': frame_end}]))

    frames_dir = out/'frames'
    frames_dir.mkdir(exist_ok=True)
    started = time.monotonic()
    frame_range = [int(f) for f in args.only_frames.split(',')] if args.only_frames else range(1, frame_end+1)
    rendered = {}  # picture state -> frame file
    for frame in frame_range:
        scene.frame_set(frame)
        path = frames_dir/f'frame_{frame:04d}.png'
        state = picture_state(scene)
        if args.dry_run:
            rendered.setdefault(state, path)
            continue
        if state in rendered:
            shutil.copy2(rendered[state], path)
        else:
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            rendered[state] = path
        print(f'frame {frame}/{frame_end} ({time.monotonic()-started:.1f}s elapsed)')
    if args.dry_run:
        print('DRY RUN:', len(rendered), 'pictures to render,', len(frame_range)-len(rendered), 'held copies')
        return
    print('RENDERED', len(rendered), 'frames,', len(frame_range)-len(rendered), 'held copies, into', frames_dir)


main()
