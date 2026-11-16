"""Put a generated clip (omni_clip.py) into a rendered run: the frames of the conversation's
{"insert": name} turn are replaced by the clip resampled to the run's fps and size, and the first and
last few frames are blended with the rendered frames next to them, so a keyframe Omni drew slightly
differently does not jump. The clip's own audio is dropped (the voices are laid by make_video.py).

Run after the full shoot.mjs capture, before make_video.py:
.venv/Scripts/python.exe splice_insert.py output/lessons_2b boss_enter output/lessons_2b/omni/enter.mp4 --start 1.5 --blend 4
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run', help='run directory with timeline.json and frames/')
    ap.add_argument('insert', help='name of the insert turn')
    ap.add_argument('clip', help='mp4 from omni_clip.py')
    ap.add_argument('--start', type=float, default=0, help='seconds into the clip to start from (skip a slow lead-in)')
    ap.add_argument('--fps', type=int, default=12)
    ap.add_argument('--blend', type=int, default=3, help='frames blended into the render at each end')
    args = ap.parse_args()
    run = Path(args.run)
    turns = json.loads((run/'timeline.json').read_text(encoding='utf-8'))
    turn = next(t for t in turns if t.get('insert') == args.insert)
    first, last = turn['voice_frame'], turn['frame_end']
    frames = run/'frames'
    size = Image.open(frames/f'frame_{first:04d}.png').size
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(args.start), '-i', args.clip, '-an', '-vf',
                        f'fps={args.fps},scale={size[0]}:{size[1]}:flags=lanczos', f'{tmp}/c_%04d.png'], check=True)
        clip = sorted(Path(tmp).glob('c_*.png'))
        n = last - first + 1
        print(f'{args.insert}: frames {first}-{last} ({n}), clip has {len(clip)} at {args.fps} fps')
        before = frames/f'frame_{first - 1:04d}.png'
        after = frames/f'frame_{last + 1:04d}.png'
        before = Image.open(before).convert('RGB') if before.exists() else None
        after = Image.open(after).convert('RGB') if after.exists() else None
        for i in range(n):
            im = Image.open(clip[min(i, len(clip) - 1)]).convert('RGB')
            if before and i < args.blend:  # ease from the last rendered frame into the clip
                im = Image.blend(before, im, (i + 1) / (args.blend + 1))
            if after and n - 1 - i < args.blend:  # and out of it into the next rendered frame
                im = Image.blend(im, after, (args.blend - (n - 1 - i)) / (args.blend + 1))
            im.save(frames/f'frame_{first + i:04d}.png')
        shutil.copy(args.clip, run/f'{args.insert}.mp4')


if __name__ == '__main__':
    main()
