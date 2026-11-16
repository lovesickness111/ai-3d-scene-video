"""Re-speak the turns of a run whose reading fails reading_check.py: a non-northern accent, or a word
both judges hear misread, skipped or added (English terms included).

Checks every clip (or --turns), and for each failing turn deletes the wav and its raw engine audio,
speaks it again with tts.py and checks again, up to --tries times. Prints one line per attempt; exits 1
if a turn still fails. A failure that survives every try is usually the script or pronunciation.json,
not luck: fix the respelling instead of retrying more.

.venv/Scripts/python.exe respeak_check.py conversation_lessons_1.json output/lessons_1
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from reading_check import check_turn
from tts import ROOT, VOICES, load_env, load_pronunciation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('conversation')
    ap.add_argument('run', help='run directory holding audio/')
    ap.add_argument('--turns', default='', help='comma-separated turn indices (default: all)')
    ap.add_argument('--tries', type=int, default=4)
    ap.add_argument('--engine', default='gemini')
    ap.add_argument('--voice', action='append', default=[], metavar='SPEAKER=NAME', help='passed on to tts.py')
    ap.add_argument('--style', action='append', default=[], metavar='SPEAKER=TEXT', help='passed on to tts.py')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    load_env()
    py, audio = sys.executable, Path(args.run)/'audio'
    script = json.loads(Path(args.conversation).read_text(encoding='utf-8'))
    pronunciation = load_pronunciation(ROOT/'pronunciation.json')
    turns = [int(v) for v in args.turns.split(',')] if args.turns else [i for i, t in enumerate(script) if 'insert' not in t]
    failed = []
    for t in turns:
        for attempt in range(1, args.tries+1):
            r = check_turn(t, script[t]['text'], audio/f'turn_{t:02d}.wav', pronunciation)
            last = attempt == args.tries
            print(f"turn {t} try {attempt}: accent {r['accents']} both {r['both']} one {r['one']}"
                  f"{'' if r['ok'] or last else '  -> re-speak'}")
            if r['ok']:
                break
            if last:
                failed.append(t)
                break
            m = json.loads((audio/'audio.json').read_text(encoding='utf-8'))[str(t)]
            cfg = VOICES[args.engine][m['speaker']]
            raw_key = hashlib.sha1(json.dumps([args.engine, m.get('voice', cfg['voice']), m.get('style', cfg.get('style')), m['spoken']]).encode()).hexdigest()
            for p in (audio/f'turn_{t:02d}.wav', audio/'raw'/f'{raw_key}.wav'):
                p.unlink(missing_ok=True)
            extra = [x for v in args.voice for x in ('--voice', v)] + [x for s in args.style for x in ('--style', s)]
            subprocess.run([py, 'tts.py', args.conversation, '--out', args.run, '--turns', str(t), '--engine', args.engine] + extra,
                           check=True, capture_output=True)
    if failed:
        print('still failing:', failed)
        sys.exit(1)


if __name__ == '__main__':
    main()
