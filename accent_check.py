"""Ask Gemini audio models about voice clips I can't listen to: which regional
Vietnamese accent each has (default), or what exactly was read (--transcribe,
to check numbers and English words). Needs the same .env as tts.py.

.venv/Scripts/python.exe accent_check.py output/qa_demo/audio/turn_*.wav
.venv/Scripts/python.exe accent_check.py --transcribe output/voice_test/google_free_vi.wav

The pipeline step is reading_check.py (accent and how every word, English terms included, was
read against the script); this file holds the request it uses and stays for quick one-off questions.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from tts import load_env

MODELS = ('gemini-3.8-flash', 'gemini-3.1-pro-preview')
PROMPTS = {
    'accent': ('This clip is a Vietnamese text-to-speech voice. Decide which regional accent the speaker has: '
               '"northern" (Hanoi), "central" (Hue / Nghe An), "southern" (Saigon), or "foreign" (non-native). '
               'Judge only from what you hear: how d / gi / r and v are pronounced, final -t and -n, '
               'whether the hoi and nga tones are distinct, vowel quality. Reply as JSON: '
               '{"accent": "...", "confidence": 0..1, "cues": "the specific words you heard and how they were pronounced"}'),
    'transcribe': ('This clip is a Vietnamese text-to-speech voice reading text that may mix Vietnamese with numbers, '
                   'symbols and English words. Write down exactly what you hear, syllable by syllable, in Vietnamese '
                   'spelling; for words read in English write them in English. Do not correct or normalise anything. '
                   'Reply as JSON: {"transcript": "..."}'),
}


def ask(path, model, prompt):
    base = os.environ.get('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/').rstrip('/')
    body = {'contents': [{'parts': [{'inlineData': {'mimeType': 'audio/wav',
                                                    'data': base64.b64encode(Path(path).read_bytes()).decode()}},
                                    {'text': prompt}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0}}
    request = urllib.request.Request(f'{base}/v1beta/models/{model}:generateContent', json.dumps(body).encode(),
                                     {'Content-Type': 'application/json', 'x-goog-api-key': os.environ['GEMINI_API_KEY']})
    try:
        reply = json.load(urllib.request.urlopen(request, timeout=180))
        answer = json.loads(''.join(p.get('text', '') for p in reply['candidates'][0]['content']['parts']))
        return answer[0] if isinstance(answer, list) else answer
    except urllib.error.HTTPError as e:
        return {'error': f'HTTP {e.code}: {e.read().decode(errors="replace")[:200]}'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('clips', nargs='+', help='.wav files')
    parser.add_argument('--transcribe', action='store_true', help='write out what was read instead of judging the accent')
    parser.add_argument('--models', default=','.join(MODELS))
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding='utf-8')
    load_env()
    prompt = PROMPTS['transcribe' if args.transcribe else 'accent']
    for path in args.clips:
        for model in args.models.split(','):
            r = ask(path, model, prompt)
            if args.transcribe:
                print(f"{Path(path).name:28} {model:24} {r.get('transcript') or r}")
            else:
                print(f"{Path(path).name:28} {model:24} {str(r.get('accent', r.get('error'))):9} "
                      f"{r.get('confidence', '')}  {str(r.get('cues', ''))[:150]}")


if __name__ == '__main__':
    main()
