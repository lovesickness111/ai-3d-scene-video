"""Speak each turn of a conversation into <out>/audio/turn_XX.wav, plus
audio.json with what was actually read, how long each turn lasts and when
each word is spoken (so the on-screen text can follow the voice).

English words and tricky numbers are first rewritten into Vietnamese syllables
from pronunciation.json (Claude -> "cờ lau"); a Vietnamese voice mangles them
otherwise. Every voice is then sped up to --speed (1.2: the voices as
synthesised were too slow) with the pitch kept. What the engine returned is kept
in audio/raw/ by content, so changing speed, pitch or an effect only re-runs
ffmpeg; a turn is re-spoken only when its spoken text or voice changes.

Engines: `gemini` calls the Gemini TTS model named in .env (GEMINI_API_KEY,
GEMINI_TTS_MODEL, GEMINI_BASE_URL); `piper` runs offline on CPU (voices in
models/piper, fetched once with `python -m piper.download_voices --data-dir
models/piper <voice>`); `edge` uses Microsoft Edge's online voices and needs
speech.platform.bing.com reachable; `gtranslate` is Google Translate's free
read-aloud voice (no key, one Vietnamese voice, unofficial endpoint).

.venv/Scripts/python.exe tts.py conversation.json --out output/qa_demo
.venv/Scripts/python.exe tts.py conversation.json --out output/voice_test --turns 0,9 --voice dev=vi-vn-tutor-4
"""
import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PIPER_DIR = ROOT/'models'/'piper'
# pitch: 1.0 = as recorded, applied after synthesis; style: spoken-delivery direction (gemini only)
VOICES = {
    # custom voices stored in the API key's project, made with voice_remix.py: "Riko" (en-us-riko,
    # male) and "Kore" (female) remixed to a northern (Hanoi) accent. The stock voices have no fixed
    # Vietnamese accent -- Riko reads southern, Kore drifts between northern and southern per call.
    'gemini': {'dev': {'voice': 'voice_8dt3hau7h3iq', 'pitch': 1.0, 'style': 'relaxed and casual, joking with a close friend'},
               'claude': {'voice': 'voice_v9whx7m5fzs0', 'pitch': 1.0, 'style': 'playful and cheeky'},
               # the boss (lessons clip 2): a native Vietnamese library voice (62-year-old professor) that holds a
               # northern accent on its own, read with no style (remixes of English voices kept drifting southern)
               'boss': {'voice': 'vi-vn-tutor-2', 'pitch': 1.0, 'style': ''}},
    # vais1000 is the only Piper vi_VN voice that knows the tone marks current espeak emits;
    # 25hours_single and vivos drop them ("Missing phoneme from id map") and speak toneless
    'piper': {'dev': {'voice': 'vi_VN-vais1000-medium', 'pitch': 1.0},
              'claude': {'voice': 'vi_VN-vais1000-medium', 'pitch': 1.15}},
    'edge': {'dev': {'voice': 'vi-VN-NamMinhNeural', 'pitch': 1.0},
             'claude': {'voice': 'vi-VN-NamMinhNeural', 'pitch': 1.25}},
    # Google Translate has a single Vietnamese voice (northern, female) and no style control:
    # the speakers are told apart by pitch only. It reads numbers, dates, %, $, @, & itself,
    # but unknown names (Jev) still need pronunciation.json. Requests over ~200 characters are
    # refused, so speak_gtranslate sends the text sentence by sentence.
    'gtranslate': {'dev': {'voice': 'vi', 'pitch': 0.9},
                   'claude': {'voice': 'vi', 'pitch': 1.1}},
}
GTRANSLATE_MAX_CHARS = 190
DEFAULT_SPEED = 1.2  # playback rate of every voice, pitch preserved (ffmpeg atempo)
EFFECTS = {  # ffmpeg audio filters applied to Claude's voice
    'none': '',
    'robot_light': 'aecho=0.8:0.85:9|18:0.5|0.3',  # two very short echoes: metallic ring, words stay clear
    'robot': "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75",  # flat monotone
}


def load_env(path=ROOT/'.env'):
    """KEY=VALUE lines into os.environ; variables already set in the real environment win."""
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        m = re.match(r'([A-Za-z_]\w*)\s*=\s*(.*?)\s*$', line)
        if m:
            os.environ.setdefault(m.group(1), m.group(2).strip('"\''))


def load_pronunciation(path):
    raw = json.loads(path.read_text(encoding='utf-8'))
    table = {k.lower(): v for k, v in raw.items()}
    longest_first = sorted(raw, key=len, reverse=True)  # "Decision API" before "Decision"
    # acronyms match only in capitals: "AI" must not rewrite the Vietnamese "ai" (who)
    pattern = re.compile(r'(?<!\w)(' + '|'.join(re.escape(k) if k.isupper() else f'(?i:{re.escape(k)})'
                                                for k in longest_first) + r')(?!\w)')
    return table, pattern


def spoken(text, pronunciation):
    table, pattern = pronunciation
    text = text.replace('**', '').replace('"', '')
    return pattern.sub(lambda m: table[m.group(1).lower()], text)


def speak_gemini(text, cfg, raw_path):
    """Interactions API: the text is read verbatim, so delivery direction must go in
    the speech_metadata annotation -- written into the text it gets spoken aloud."""
    base = os.environ.get('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/').rstrip('/')
    body = {'model': os.environ['GEMINI_TTS_MODEL'],
            'input': [{'type': 'user_input', 'content': [{
                'type': 'text', 'text': text,
                # no style at all when empty: Google's guide says most turns need none, and extra text adds drift
                **({'annotations': [{'type': 'speech_metadata', 'style': cfg['style']}]} if cfg.get('style') else {})}]}],
            'response_format': {'type': 'audio'},
            'generation_config': {'speech_config': [{'voice': cfg['voice']}]}}
    request = urllib.request.Request(
        f'{base}/v1beta/interactions', json.dumps(body).encode(),
        {'Content-Type': 'application/json', 'x-goog-api-key': os.environ['GEMINI_API_KEY']})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            reply = json.load(response)
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Gemini HTTP {e.code}: {e.read().decode(errors="replace")[:800]}')
    audio = [c for step in reply['steps'] if step['type'] == 'model_output'
             for c in step['content'] if c['type'] == 'audio']
    raw_path.write_bytes(base64.b64decode(audio[-1]['data']))  # a complete WAV file


def speak_piper(text, cfg, raw_path, _loaded={}):
    from piper import PiperVoice
    voice = cfg['voice']
    if voice not in _loaded:
        _loaded[voice] = PiperVoice.load(str(PIPER_DIR/f'{voice}.onnx'))
    with wave.open(str(raw_path), 'wb') as wav:
        _loaded[voice].synthesize_wav(text, wav)


def speak_edge(text, cfg, raw_path):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, cfg['voice']).save(str(raw_path)))


def gtranslate_chunks(text, limit=GTRANSLATE_MAX_CHARS):
    """The text in pieces the endpoint accepts: whole sentences where they fit, else clauses, else words."""
    chunks, cur = [], ''
    for piece in re.split(r'(?<=[.!?;:])\s+', text):
        while len(piece) > limit:  # one over-long sentence: break it at a comma, or the last space
            cut = max(piece.rfind(', ', 0, limit), piece.rfind(' ', 0, limit))
            chunks.append(piece[:cut].strip())
            piece = piece[cut:].strip()
        if cur and len(cur)+1+len(piece) > limit:
            chunks.append(cur)
            cur = piece
        else:
            cur = f'{cur} {piece}'.strip()
    return chunks+[cur] if cur else chunks


def speak_gtranslate(text, cfg, raw_path):
    """MP3 pieces straight from Google Translate's read-aloud endpoint, concatenated
    (MPEG frames join cleanly; ffmpeg re-encodes the result into the final wav)."""
    data = bytearray()
    for chunk in gtranslate_chunks(text):
        query = urllib.parse.urlencode({'ie': 'UTF-8', 'q': chunk, 'tl': cfg['voice'], 'client': 'tw-ob'})
        request = urllib.request.Request(f'https://translate.google.com/translate_tts?{query}',
                                         headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data += response.read()
        except urllib.error.HTTPError as e:
            raise SystemExit(f'Google Translate TTS HTTP {e.code} for {len(chunk)} characters: {chunk[:60]}...')
    raw_path.write_bytes(data)


ENGINES = {'gemini': (speak_gemini, '.wav'), 'piper': (speak_piper, '.wav'), 'edge': (speak_edge, '.mp3'),
           'gtranslate': (speak_gtranslate, '.mp3')}


def seconds(wav_path):
    with wave.open(str(wav_path), 'rb') as wav:
        return wav.getnframes()/wav.getframerate()


def speech_span(wav_path, min_pause=.18):
    """(first sound, last sound, [(pause start, pause end), ...]) in seconds."""
    with wave.open(str(wav_path), 'rb') as wav:
        rate = wav.getframerate()
        samples = np.abs(np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float32))
    hop = rate//100
    level = samples[:len(samples)//hop*hop].reshape(-1, hop).mean(axis=1)
    loud = np.flatnonzero(level > .06*np.percentile(level, 95))
    gaps = np.flatnonzero(np.diff(loud) > min_pause*100)
    return loud[0]/100, (loud[-1]+1)/100, [((loud[g]+1)/100, loud[g+1]/100) for g in gaps]


CLAUSE_END, SENTENCE_END = set(',.!?:;—'), set('.!?:;')


def syllables_read(text, words, pronunciation):
    """How many syllables the voice reads for each of `words` (regex matches in `text`):
    one per Vietnamese word, the rewritten form for what pronunciation.json rewrites
    ("API" is three), numbers digit by digit with their unit ("92" = chín mươi hai)."""
    table, pattern = pronunciation
    rewrites = [(m.start(), m.end(), len(table[m.group(1).lower()].split())) for m in pattern.finditer(text)]
    counts = []
    for word in words:
        count, rest = 0, word.group()
        for start, end, rewritten in rewrites:
            if start < word.end() and word.start() < end:  # a rewritten phrase can span several words: share it between them
                count += rewritten/sum(1 for w in words if start < w.end() and w.start() < end)
                a, b = max(0, start-word.start()), min(len(rest), end-word.start())
                rest = rest[:a]+' '*(b-a)+rest[b:]
        for part in re.findall(r'[^\W_]+', rest):
            count += (sum(1+(k < len(part)-1) for k, digit in enumerate(part) if digit != '0') or 1) if part.isdigit() else 1
        counts.append(count)
    return counts


def word_cues(text, pronunciation, wav_path):
    """When each word of the on-screen text is spoken, so the text can follow the voice.
    Returns (cues, beats): cues = [[characters on screen before the word, seconds], ...]
    counting neither spaces nor `**`; beats = the seconds at which a sentence starts.

    The TTS gives no timestamps. Vietnamese is syllable-timed, so the pauses heard
    in the audio are matched to gaps between words such that every stretch of
    speech runs at about the same pace in syllables per second, preferring gaps
    at punctuation. The words of a stretch are then spread evenly over it.
    The off-punctuation cost was tuned on the qa_demo voices against a transcript
    of every stretch: 46 of 49 pauses land in the right gap, the rest a word or two off."""
    words = list(re.finditer(r'\S+', text))
    n = len(words)
    syllables = syllables_read(text, words, pronunciation)
    shown = [word.group().replace('**', '') for word in words]
    last_char = [word.rstrip('"')[-1:] for word in shown]
    chars = np.concatenate([[0], np.cumsum([len(word) for word in shown])])
    before = np.concatenate([[0], np.cumsum(syllables)])  # syllables read before each word

    first, last, heard = speech_span(wav_path)
    heard = sorted(sorted(heard, key=lambda h: h[0]-h[1])[:n-1])  # at most one pause per gap: the longest ones
    stretches = list(zip([first, *(h[1] for h in heard)], [*(h[0] for h in heard), last]))
    pace = before[-1]/sum(b-a for a, b in stretches)  # syllables per second
    # cost[k][j]: the best fit of the first j words into the first k stretches
    cost = np.full((len(stretches)+1, n+1), np.inf)
    cost[0][0] = 0
    split = np.zeros(cost.shape, dtype=int)
    for k, (a, b) in enumerate(stretches, 1):
        for j in range(k, n+1):
            fit = cost[k-1][:j]+np.log(np.maximum(before[j]-before[:j], .25)/((b-a)*pace))**2
            split[k][j] = i = int(np.argmin(fit))
            at_punctuation = j == n or last_char[j-1] in CLAUSE_END
            cost[k][j] = fit[i]+(0 if at_punctuation else .2)
    times, j = np.zeros(n), n
    for k in range(len(stretches), 0, -1):
        i, (a, b) = split[k][j], stretches[k-1]
        times[i:j] = a+(before[i:j]-before[i])/max(before[j]-before[i], 1e-9)*(b-a)
        j = i
    cues = [[int(chars[i]), round(float(times[i]), 2)] for i in range(n)]
    beats = [cues[i][1] for i in range(n) if i == 0 or last_char[i-1] in SENTENCE_END]
    return cues, beats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('conversation')
    parser.add_argument('--out', required=True, help='run directory, e.g. output/qa_demo')
    parser.add_argument('--engine', choices=sorted(ENGINES), default='gemini')
    parser.add_argument('--voice', action='append', default=[], metavar='SPEAKER=NAME',
                        help='override a speaker\'s voice, e.g. --voice dev=vi-vn-tutor-4')
    parser.add_argument('--style', action='append', default=[], metavar='SPEAKER=TEXT',
                        help="override a speaker's delivery direction; empty (--style dev=) sends none")
    parser.add_argument('--claude-fx', choices=sorted(EFFECTS), default='none')
    parser.add_argument('--speed', type=float, default=DEFAULT_SPEED, help='rate every voice is sped up to, pitch kept')
    parser.add_argument('--pronunciation', default=str(ROOT/'pronunciation.json'))
    parser.add_argument('--turns', default='', help='comma-separated turn indices (default: all)')
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding='utf-8')  # the Windows console codepage can't print Vietnamese
    load_env()
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('ffmpeg not found in PATH')
    turns = json.loads(Path(args.conversation).read_text(encoding='utf-8'))
    pronunciation = load_pronunciation(Path(args.pronunciation))
    voices = {speaker: dict(cfg) for speaker, cfg in VOICES[args.engine].items()}
    for override in args.voice:
        speaker, name = override.split('=', 1)
        voices[speaker]['voice'] = name
    for override in args.style:
        speaker, style = override.split('=', 1)
        voices[speaker]['style'] = style
    audio_dir = Path(args.out).resolve()/'audio'
    raw_dir = audio_dir/'raw'  # what each engine returned, 44.1 kHz mono, by content: filters re-run from here
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = audio_dir/'audio.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    # what has been spoken before, by content: a turn keeps its audio when the script around it moves
    cached = {entry['key']: (entry, (audio_dir/f'turn_{int(i):02d}.wav').read_bytes())
              for i, entry in manifest.items() if (audio_dir/f'turn_{int(i):02d}.wav').exists()}
    speak, raw_ext = ENGINES[args.engine]

    for i in ([int(v) for v in args.turns.split(',')] if args.turns else range(len(turns))):
        turn = turns[i]
        if 'insert' in turn:  # a stretch of generated video (boss walks in), no voice
            continue
        text = spoken(turn['text'], pronunciation)
        cfg = dict(voices[turn['speaker']])
        if turn.get('style'):  # a line can ask for its own delivery ("serious, explaining to his boss")
            cfg['style'] = turn['style']
        filters = [f"rubberband=pitch={cfg['pitch']}"] if cfg['pitch'] != 1.0 else []
        if args.speed != 1.0:
            filters.append(f'atempo={args.speed}')
        if turn['speaker'] == 'claude' and EFFECTS[args.claude_fx]:
            filters.append(EFFECTS[args.claude_fx])
        raw_key = hashlib.sha1(json.dumps([args.engine, cfg['voice'], cfg.get('style'), text]).encode()).hexdigest()
        key = hashlib.sha1(json.dumps([raw_key, filters]).encode()).hexdigest()
        wav_path = audio_dir/f'turn_{i:02d}.wav'
        raw_wav = raw_dir/f'{raw_key}.wav'
        if key in cached:  # same voice, text and filters as a turn already made: its cues still hold
            manifest[str(i)] = dict(cached[key][0])
            wav_path.write_bytes(cached[key][1])
            print(f'turn {i}: cached')
        else:
            if raw_wav.exists():
                spoke = 'raw cached'
            else:
                spoke = f'[{cfg["voice"]}]  {text}'
                engine_path = audio_dir/f'_engine{raw_ext}'
                speak(text, cfg, engine_path)
                subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', str(engine_path),
                                '-ar', '44100', '-ac', '1', str(raw_wav)], check=True)
                engine_path.unlink()
            command = [ffmpeg, '-y', '-loglevel', 'error', '-i', str(raw_wav)]
            if filters:
                command += ['-af', ','.join(filters)]
            subprocess.run(command + [str(wav_path)], check=True)
            manifest[str(i)] = {'key': key, 'speaker': turn['speaker'], 'voice': cfg['voice'], 'style': cfg.get('style'),
                                'seconds': round(seconds(wav_path), 2), 'spoken': text}
            manifest[str(i)]['cues'], manifest[str(i)]['beats'] = word_cues(turn['text'], pronunciation, wav_path)
            print(f"turn {i}: {manifest[str(i)]['seconds']}s  {spoke}")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
