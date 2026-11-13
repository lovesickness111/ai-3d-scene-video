"""Q&A video: dev and the Claude mascot talk through a conversation.json script.

Every turn is a 3D shot on the speaker with an empty chat bubble; the bubble's
on-screen box goes to bubbles.json and compose.py draws the text into it in 2D
(3D text was unreadable at video sizes), word by word as it is spoken.
Two views per speaker: "talk" (face + bubble) and, for a turn with an
`illustration`, "explain" -- the speaker and a smaller bubble move aside and
compose.py puts the picture on a card in the part of the frame left free
(`card` in timeline.json).
Before a turn in another shot the camera glides over in silence; while a turn
is spoken it holds, the speaker's mouth follows the voice and the face reacts
as sentences start. Those are a few fixed poses and every glide between the
same two shots is the same, so most frames repeat an already rendered picture
and are copied instead of rendered.
With <out>/audio/audio.json present (run tts.py first) each turn lasts as long
as its voice; make_video.py then lays the voices under the frames.

python render.py scripts/qa_scene.py --out output/qa_demo --samples 32
"""
import argparse
import json
import math
import shutil
import sys
import time
import wave
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _scene_lib import (  # noqa: E402
    build_materials, room, painting, desk, programmer, mascot, group, bubble,
    toggle, key_pose, hold, shot_face, lights,
)

SUNSET = [('disc', 'art_terra', .3, .15, .26, 0), ('rect', 'art_mustard', 0, -.6, 1, .4),
          ('rect', 'art_navy', 0, -.82, 1, .18)]
BLOCKS = [('rect', 'art_sage', -.3, .45, .55, .4), ('disc', 'art_mustard', .3, .05, .28, 0),
          ('rect', 'art_terra', .1, -.55, .7, .3)]
ARCH = [('disc', 'art_navy', 0, .15, .36, 0), ('rect', 'art_navy', 0, -.275, .72, .425),
        ('disc', 'art_mustard', 0, .15, .17, 0)]
DOTS = [('disc', 'art_terra', -.25, .25, .3, 0), ('disc', 'art_sage', .25, -.2, .3, 0),
        ('rect', 'art_mustard', 0, -.8, .8, .1)]

# per (speaker, view): the camera framing (shot_face), the bubble (place on the speaker's head, size)
# and for "explain" the part of the frame kept free for the illustration card (x0, y0, x1, y1 as fractions)
SHOTS = {
    ('dev', 'talk'): {'camera': dict(offset=(0, -.01, .15), lens=38, dist=2.0, side=(.72, .70, .3)),
                      'bubble': dict(loc=(.50, -.05, .24), scale=1.7)},
    ('dev', 'explain'): {'camera': dict(offset=(0, -.01, .15), lens=38, dist=2.3, side=(.72, .70, .3), low=.12, aside=.25),
                         'bubble': dict(loc=(.08, -.05, .58), scale=1.9),
                         'card': (.47, .1, .97, .82)},
    ('claude', 'talk'): {'camera': dict(lens=40, dist=1.7, side=(.9, -.6, .35), low=.15),
                         'bubble': dict(loc=(.13, -.02, .30), scale=1.5)},
    ('claude', 'explain'): {'camera': dict(lens=40, dist=1.9, side=(.9, -.6, .35), low=.14, aside=.24),
                            'bubble': dict(loc=(.03, -.02, .40), scale=1.3),
                            'card': (.47, .1, .97, .82)},
}
# the poses a face part steps between (key_pose arguments); the first is its rest pose
FACE_POSES = {
    'dev': {'mouth': {'closed': {}, 'half': dict(scale=(.92, 1, 1.6), lift=-.006),
                      'open': dict(scale=(.85, 1, 2.2), lift=-.012)},
            'eyes': {'rest': {}, 'blink': dict(scale=(1.1, 1, .15))},
            'brows': {'rest': {}, 'up': dict(lift=.012)}},
    'claude': {'mouth': {'closed': dict(hidden=True), 'half': {}, 'open': dict(scale=(1.15, 1, 2.3), lift=-.006)},
               'eyes': {'rest': {}, 'wide': dict(scale=(1.15, 1, 1.3)), 'blink': dict(scale=(1.25, 1, .16))}},
}
EMPHASIS = {'dev': ('brows', 'up'), 'claude': ('eyes', 'wide')}  # how a speaker opens a sentence


def hang_paintings(M):
    """Placed where the two close-ups have bare wall: clear of the speaker and their bubble."""
    painting(M, (-1.55, -3.75, 1.22), 90, (1.3, .75), SUNSET)  # dev shot, left of his head
    painting(M, (-1.15, -4.95, 1.25), 180, (.5, .65), BLOCKS)  # dev shot, far wall at the left edge
    painting(M, (-1.55, .33, 1.3), 90, (.5, .65), ARCH)        # Claude shot, between the dev and the bubble
    painting(M, (.3, 1.25, 1.28), 0, (.5, .6), DOTS)           # Claude shot, right of the bubble


def shot_of(turn):
    """(speaker, view): "explain" when the turn has an illustration to show, else "talk"."""
    return turn['speaker'], 'explain' if turn.get('illustration') else 'talk'


def speech_frames(turn, i, audio, fps):
    """How long a turn is spoken for: its recorded voice plus a short breath,
    or a reading-speed guess when there is no audio."""
    if not audio:
        return max(1, round(max(1.8, len(turn['text'])/14)*fps))
    if str(i) not in audio:
        raise SystemExit(f'audio.json has no turn {i}: run tts.py for this conversation first')
    return math.ceil((audio[str(i)]['seconds']+.25)*fps)


def schedule(turns, fps, audio, move, size):
    """Give every turn its frames, `frame_start`..`frame_end`. The voice and the bubble
    start at `voice_frame`: after frame_start when the camera first has to glide over
    from another shot. Returns the last frame."""
    frame, prev = 1, None
    for i, turn in enumerate(turns):
        shot = shot_of(turn)
        turn['frame_start'] = frame
        turn['voice_frame'] = frame+(round(move*fps) if prev not in (None, shot) else 0)
        turn['frame_end'] = turn['voice_frame']+speech_frames(turn, i, audio, fps)-1
        if 'card' in SHOTS[shot]:
            turn['card'] = [round(v*size[k % 2]) for k, v in enumerate(SHOTS[shot]['card'])]
        frame, prev = turn['frame_end']+1, shot
    return frame-1


def build_bubbles(M, anchors, turns):
    """One bubble per shot, hidden except while a turn in that shot is spoken
    (a bubble per turn would make every turn its own picture and defeat the
    held-frame reuse in main). Returns [(root, body, [(first frame, last frame), ...])]."""
    bubbles = {}
    for turn in turns:
        shot = shot_of(turn)
        if shot not in bubbles:
            bubbles[shot] = (*bubble(M, parent=anchors[shot[0]], **SHOTS[shot]['bubble']), [])
        bubbles[shot][2].append((turn['voice_frame'], turn['frame_end']))
    return list(bubbles.values())


def apply_visibility(bubbles, overall_end):
    for root, _, spans in bubbles:
        toggle(root, 1, True)
        for start, end in spans:
            toggle(root, start, False)
            if end < overall_end:
                toggle(root, end+1, True)


def screen_box(scene, cam, obj):
    """Pixel bbox (x0, y0, x1, y1; y down) of obj's bounding box as seen by cam."""
    W, H = scene.render.resolution_x, scene.render.resolution_y
    pts = [world_to_camera_view(scene, cam, obj.matrix_world @ Vector(c)) for c in obj.bound_box]
    xs, ys = [p.x*W for p in pts], [(1-p.y)*H for p in pts]
    return [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]


def play_conversation(cam, anchors, turns):
    """The camera holds a turn's shot while it is spoken; the eased move from the
    previous shot fills the silent frames before it."""
    for turn in turns:
        shot_face(cam, anchors[turn['speaker']], **SHOTS[shot_of(turn)]['camera'])
        hold(cam, turn['voice_frame'])
        hold(cam, turn['frame_end'])


def mouth_levels(wav_path, fps):
    """For every video frame of a voice clip, how far the mouth opens: closed in
    silence, else open on the frames louder than the half second around them and
    half open on the others -- it flaps with the syllables instead of hanging open."""
    with wave.open(str(wav_path), 'rb') as wav:
        rate = wav.getframerate()
        samples = np.abs(np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float32))
    hop = rate//100
    level = samples[:len(samples)//hop*hop].reshape(-1, hop).mean(axis=1)  # loudness every 10 ms
    level /= np.percentile(level, 95)

    def mean(start, end):
        a = max(0, round(start*100))
        return float(level[a:max(a+1, round(end*100))].mean()) if a < len(level) else 0.0

    levels = []
    for k in range(math.ceil(len(level)/100*fps)):
        now, around = mean(k/fps, (k+1)/fps), mean(k/fps-.17, k/fps+.25)
        levels.append('closed' if now < .08 else 'open' if now >= around else 'half')
    return levels


def face_tracks(turns, fps, audio, audio_dir, last_frame):
    """The pose of every face part on every frame, {speaker: {part: [pose name per frame]}}:
    the speaker's mouth follows the voice, each sentence opens with the speaker's
    emphasis (dev: raised brows, Claude: wide eyes) and they blink in the pause before it.
    Everyone is back at rest when a turn ends, so the camera moves all look alike."""
    tracks = {speaker: {part: [next(iter(poses))]*(last_frame+1) for part, poses in parts.items()}
              for speaker, parts in FACE_POSES.items()}
    for i, turn in enumerate(turns):
        track, start = tracks[turn['speaker']], turn['voice_frame']
        if audio:
            levels, beats = mouth_levels(audio_dir/f'turn_{i:02d}.wav', fps), audio[str(i)]['beats']
        else:
            levels, beats = [('half', 'open', 'half', 'closed')[k % 4] for k in range(turn['frame_end']-start-3)], [0]
        track['mouth'][start:start+len(levels)] = levels
        part, pose = EMPHASIS[turn['speaker']]
        for n, beat in enumerate(beats):
            frame = start+round(beat*fps)
            if n and track['mouth'][frame-2] == 'closed':
                track['eyes'][frame-2] = 'blink'
            for f in range(frame, min(frame+4, turn['frame_end'])):
                track[part][f] = pose
    return tracks


def animate_faces(faces, tracks):
    """Key every face part into its pose on the frames where the pose changes."""
    for speaker, parts in faces.items():
        for part, objs in parts.items():
            track = tracks[speaker][part]
            for frame in range(1, len(track)):
                if frame == 1 or track[frame] != track[frame-1]:
                    for obj in objs:
                        key_pose(obj, frame, **FACE_POSES[speaker][part][track[frame]])


def picture_state(scene):
    """Everything that changes the picture from frame to frame in this scene.
    The render seed is fixed, so two frames in the same state render identically."""
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
    parser.add_argument('--conversation', default='conversation.json')
    parser.add_argument('--out', default='output/qa_demo')
    parser.add_argument('--engine', choices=('eevee', 'cycles'), default='cycles')
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--fps', type=int, default=12)
    parser.add_argument('--res-x', type=int, default=960)
    parser.add_argument('--res-y', type=int, default=540)
    parser.add_argument('--move', type=float, default=.65, help='seconds the camera takes from one shot to the next')
    parser.add_argument('--turns', type=int, default=0, help='limit to first N turns (0 = all)')
    parser.add_argument('--preview', action='store_true', help='render only frame 1')
    parser.add_argument('--only-frames', default='', help='comma-separated frame numbers, skip the rest')
    parser.add_argument('--dry-run', action='store_true',
                        help='render nothing: write timeline.json and count the pictures a render would need')
    args = parser.parse_args(argv)

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    turns = json.loads(Path(args.conversation).resolve().read_text(encoding='utf-8'))
    if args.turns:
        turns = turns[:args.turns]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M = build_materials()
    room(M)
    hang_paintings(M)
    desk(M)
    p, head, face_dev = programmer(M, (-.05, -.85, 0), 112, 22)
    c, face_claude = mascot(M, (.42, -.16, .75), 30, 1.25)
    anchors = {'dev': head, 'claude': group('mascot_face', (0, -.06, .14), parent=c)}
    lights(scene)
    bpy.context.view_layer.update()  # make matrix_world (anchor_world) reflect the transforms above

    cam_data = bpy.data.cameras.new('cam')
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    configure_render(scene, args)

    audio_path = out/'audio'/'audio.json'  # written by tts.py
    audio = json.loads(audio_path.read_text(encoding='utf-8')) if audio_path.exists() else None
    print('turn lengths from', audio_path if audio else 'text length (no audio.json)')
    last_frame = schedule(turns, args.fps, audio, args.move, (args.res_x, args.res_y))
    bubbles = build_bubbles(M, anchors, turns)
    apply_visibility(bubbles, last_frame)
    play_conversation(cam, anchors, turns)
    animate_faces({'dev': face_dev, 'claude': face_claude},
                  face_tracks(turns, args.fps, audio, audio_path.parent, last_frame))

    frame_end = 1 if args.preview else last_frame
    scene.frame_start, scene.frame_end, scene.render.fps = 1, frame_end, args.fps
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))

    timeline_path = out/'timeline.json'
    timeline_path.write_text(json.dumps(turns, ensure_ascii=False, indent=2), encoding='utf-8')

    frames_dir = out/'frames'
    frames_dir.mkdir(exist_ok=True)
    if not args.only_frames:  # a shorter timeline must not leave the last run's tail for make_video to pick up
        for stale in frames_dir.glob('frame_*.png'):
            if int(stale.stem[-4:]) > frame_end:
                stale.unlink()
    boxes_path = out/'bubbles.json'
    boxes = json.loads(boxes_path.read_text()) if args.only_frames and boxes_path.exists() else {}
    started = time.monotonic()
    frame_range = [int(f) for f in args.only_frames.split(',')] if args.only_frames else range(1, frame_end+1)
    rendered = {}  # picture state -> frame file: most of a turn is a held pose, render it once
    for frame in frame_range:
        scene.frame_set(frame)
        for _, body, spans in bubbles:
            if any(start <= frame <= end for start, end in spans):
                boxes[str(frame)] = screen_box(scene, cam, body)
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
        print('DRY RUN:', len(rendered), 'pictures to render,', len(frame_range)-len(rendered), 'held copies; first frames:',
              ','.join(str(int(path.stem[-4:])) for path in rendered.values()))
        return
    boxes_path.write_text(json.dumps(boxes))
    print('RENDERED', len(rendered), 'frames,', len(frame_range)-len(rendered), 'held copies, into', frames_dir)


main()
