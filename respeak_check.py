"""Re-speak the turns of a run whose voice the accent judges do not both hear as northern.

Runs accent_check.py on every clip (or --turns), and for each failing turn deletes the
wav and its raw engine audio, speaks it again with tts.py and checks again, up to --tries
times. Prints one line per attempt; exits 1 if a turn still fails.

.venv/Scripts/python.exe respeak_check.py conversation_lessons_1.json output/lessons_1
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tts import VOICES


def judge(py, wav):
    out = subprocess.run([py, 'accent_check.py', str(wav)], capture_output=True, text=True, encoding='utf-8').stdout
    return [line.split()[2] for line in out.splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('conversation')
    ap.add_argument('run', help='run directory holding audio/')
    ap.add_argument('--turns', default='', help='comma-separated turn indices (default: all)')
    ap.add_argument('--tries', type=int, default=4)
    ap.add_argument('--engine', default='gemini')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    py, audio = sys.executable, Path(args.run)/'audio'
    manifest = json.loads((audio/'audio.json').read_text(encoding='utf-8'))
    turns = [int(v) for v in args.turns.split(',')] if args.turns else sorted(int(k) for k in manifest)
    failed = []
    for t in turns:
        for attempt in range(1, args.tries+1):
            verdicts = judge(py, audio/f'turn_{t:02d}.wav')
            ok = verdicts.count('northern') == len(verdicts) >= 1
            print(f'turn {t} try {attempt}: {verdicts}{"" if ok else "  -> re-speak"}')
            if ok:
                break
            m = json.loads((audio/'audio.json').read_text(encoding='utf-8'))[str(t)]
            cfg = VOICES[args.engine][m['speaker']]
            raw_key = hashlib.sha1(json.dumps([args.engine, cfg['voice'], cfg.get('style'), m['spoken']]).encode()).hexdigest()
            for p in (audio/f'turn_{t:02d}.wav', audio/'raw'/f'{raw_key}.wav'):
                p.unlink(missing_ok=True)
            subprocess.run([py, 'tts.py', args.conversation, '--out', args.run, '--turns', str(t), '--engine', args.engine],
                           check=True, capture_output=True)
        else:
            failed.append(t)
    if failed:
        print('still not northern:', failed)
        sys.exit(1)


if __name__ == '__main__':
    main()
