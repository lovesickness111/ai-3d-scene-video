"""Generate a short video between two rendered keyframes with Gemini Omni (gemini-omni-1.2-flash), for the
moves the three.js rig can't do -- the boss walking into the room and out again. The first and last frames
are stills of the same shot (shoot.mjs --still ... --without boss), so the clip starts and ends on frames the
render already has; splice_insert.py drops it into the run's frames.

Costs money (Paid tier, ~$0.07 per second at 720p): say so before running it.

.venv/Scripts/python.exe omni_clip.py --first a.png --last b.png --seconds 8 --out output/x/omni/enter.mp4 \\
    --prompt "Static camera. A man in a dark suit walks in from the bottom left and stops beside the desk..."
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tts import load_env

MODEL = 'gemini-omni-1.2-flash'


def call(method, url, body=None, timeout=900):
    request = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                     {'Content-Type': 'application/json', 'x-goog-api-key': os.environ['GEMINI_API_KEY']},
                                     method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Gemini HTTP {e.code}: {e.read().decode(errors="replace")[:1200]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--first', required=True, help='first frame (png/jpg)')
    ap.add_argument('--last', help='last frame: with both, Omni interpolates between them (3-10 s)')
    ap.add_argument('--prompt', required=True, help='English: what moves, and that the camera and style stay put')
    ap.add_argument('--seconds', type=int, default=8)
    ap.add_argument('--resolution', default='720p', choices=['360p', '720p', '1080p', '4k'])
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    load_env()
    base = os.environ.get('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/').rstrip('/')

    def image(path):
        mime = 'image/png' if path.lower().endswith('.png') else 'image/jpeg'
        return {'type': 'image', 'mime_type': mime, 'data': base64.b64encode(Path(path).read_bytes()).decode()}

    parts = [image(args.first)] + ([image(args.last)] if args.last else []) + [{'type': 'text', 'text': args.prompt}]
    body = {'model': MODEL, 'input': parts, 'store': False,
            'response_format': {'type': 'video', 'aspect_ratio': '16:9', 'resolution': args.resolution,
                                'duration': f'{args.seconds}s'}}
    started = time.time()
    reply = json.loads(call('POST', f'{base}/v1beta/interactions', body))
    videos = [c for step in reply.get('steps', []) if step.get('type') == 'model_output'
              for c in step.get('content', []) if c.get('type') == 'video']
    if not videos:
        raise SystemExit('no video in the reply: ' + json.dumps(reply)[:1200])
    v = videos[-1]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if v.get('data'):
        out.write_bytes(base64.b64decode(v['data']))
    else:  # delivered as a file: wait for it, then download
        name = v['uri'].split('/v1beta/')[-1] if '/v1beta/' in v['uri'] else v['uri']
        for _ in range(120):
            state = json.loads(call('GET', f'{base}/v1beta/{name}')).get('state')
            if state in ('ACTIVE', 'FAILED'):
                break
            time.sleep(5)
        out.write_bytes(call('GET', f'{base}/v1beta/{name}:download?alt=media'))
    usage = reply.get('usage') or reply.get('usage_metadata') or {}
    print(f'wrote {out} ({out.stat().st_size // 1024} KB) in {time.time() - started:.0f}s', json.dumps(usage)[:300])


if __name__ == '__main__':
    main()
