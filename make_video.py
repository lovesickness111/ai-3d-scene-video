"""Assemble a PNG frame sequence into an MP4 using ffmpeg, optionally with
the voices from tts.py laid under it (each turn's wav starts on the turn's
`voice_frame`, as recorded in the run's timeline.json).

python make_video.py output/demo_programmer_mascot/frames --fps 12 --out output/demo_programmer_mascot/video.mp4
python make_video.py output/qa_demo/frames_composited --fps 12 --out output/qa_demo/video.mp4 --voices output/qa_demo
"""
import argparse
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path


def find_ffmpeg():
    path = shutil.which('ffmpeg')
    if not path:
        raise SystemExit('ffmpeg not found in PATH')
    return path


def voice_track(run_dir, fps, track_path):
    """One wav for the whole video out of <run_dir>/audio/turn_XX.wav (all in the same format)."""
    turns = json.loads((run_dir/'timeline.json').read_text(encoding='utf-8'))
    track, params = bytearray(), None
    for i, turn in enumerate(turns):
        if 'insert' in turn:  # generated video spliced in here: no voice of ours
            continue
        with wave.open(str(run_dir/'audio'/f'turn_{i:02d}.wav'), 'rb') as wav:
            params = params or wav.getparams()
            start = round((turn['voice_frame']-1)/fps*wav.getframerate())*wav.getsampwidth()*wav.getnchannels()
            data = wav.readframes(wav.getnframes())
        track.extend(bytes(max(0, start-len(track))))  # silence up to the frame this turn's voice starts on
        track[start:start+len(data)] = data
    with wave.open(str(track_path), 'wb') as wav:
        wav.setparams(params)
        wav.writeframes(bytes(track))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('frames_dir')
    parser.add_argument('--fps', type=int, required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--pattern', default='frame_%04d.png')
    parser.add_argument('--voices', help='run directory holding timeline.json and audio/turn_XX.wav')
    args = parser.parse_args()

    frames_dir = Path(args.frames_dir).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    command = [find_ffmpeg(), '-y', '-framerate', str(args.fps), '-i', str(frames_dir/args.pattern)]
    audio = []
    if args.voices:
        track_path = out.with_name(out.stem+'_voices.wav')
        voice_track(Path(args.voices).resolve(), args.fps, track_path)
        command += ['-i', str(track_path)]
        audio = ['-c:a', 'aac', '-b:a', '160k']
    command += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', *audio, '-movflags', '+faststart', str(out)]
    sys.exit(subprocess.call(command))


if __name__ == '__main__':
    main()
