"""Check how each voice clip of a run was read, since I can't listen: the Gemini audio judges get the
script line and the syllables every English/technical term should sound like (pronunciation.json),
and report the accent, how each term came out, and any word skipped, added or misread.

A turn fails when a judge hears a non-northern accent or both judges flag the same word; a word only
one judge flags is a warning for a human to listen to. The last table shows how each term was heard
in every turn, to catch a term the voice reads one way here and another way there. The full report
goes to <run>/audio/reading_check.json.

.venv/Scripts/python.exe reading_check.py conversation_lessons_1.json output/lessons_1 [--turns 1,7]
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from accent_check import MODELS, ask
from tts import ROOT, load_env, load_pronunciation

PROMPT = '''This clip is a Vietnamese text-to-speech voice that should have a northern (Hanoi) accent.
It should read this script line:
"{text}"
{terms}{loose}
Listen carefully and reply as JSON:
{{"accent": "northern" | "central" | "southern" | "foreign",
  "transcript": "exactly what you hear, in Vietnamese spelling",
  "terms": [{{"term": "...", "heard": "how it was actually pronounced", "ok": true | false}}],
  "problems": [{{"word": "...", "heard": "...", "issue": "skipped" | "added" | "misread" | "wrong tone" | "read in English"}}]}}
"terms" has one entry per listed term; a term is ok when it sounds like the syllables given (a slightly
different tone is fine). "problems" lists every other word of the script that was skipped, misread or
said with the wrong tone, every word added that is not in the script, and numbers read wrongly; leave it
empty when the line was read as written. Normal northern speech is not a problem: r, d and gi all sound
like "z", and a sentence-final particle may shift its tone (nha / nhá / nhé, à / ạ).'''


# a Vietnamese syllable written without diacritics ("ai", "cho", "sang"): initial, vowels, final
VIET_SYLLABLE = re.compile(r'(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdghklmnprstvx])?[aeiouy]+(ch|ng|nh|[cmnpt])?', re.IGNORECASE)


def terms_in(text, pronunciation):
    """the respelled terms of a line, and the words left as written that are not Vietnamese ("clip", "Dev")"""
    table, pattern = pronunciation
    found = [(m.group(1), table[m.group(1).lower()]) for m in pattern.finditer(text)]
    rest = pattern.sub(' ', text)
    loose = sorted({w for w in re.findall(r'(?<!\w)[A-Za-z]+(?:\.[A-Za-z]+)*(?!\w)', rest) if not VIET_SYLLABLE.fullmatch(w)})
    return list(dict.fromkeys(found)), loose


def check_turn(i, text, wav, pronunciation, models=MODELS):
    text = text.replace('**', '')
    found, loose = terms_in(text, pronunciation)
    prompt = PROMPT.format(
        text=text,
        terms=('The English/technical terms were respelled for the voice and should sound like:\n'
               + '\n'.join(f'- "{w}" -> "{s}"' for w, s in found) + '\n') if found else '',
        loose=(f'These words were left as written, list them in "terms" too with how they were read: '
               f'{", ".join(loose)}\n') if loose else '')
    answers = {m: ask(wav, m, prompt) for m in models}
    flags = {}
    for m, a in answers.items():
        flags[m] = {t.get('term', '').lower() for t in a.get('terms', []) if t.get('ok') is False}
        flags[m] |= {p.get('word', '').lower() for p in a.get('problems', [])}
    accents = [a.get('accent', a.get('error', '?')) for a in answers.values()]
    both = set.intersection(*flags.values()) if flags else set()
    one = set.union(*flags.values()) - both if flags else set()
    ok = all(a == 'northern' for a in accents) and not both
    return {'turn': i, 'ok': ok, 'accents': accents, 'both': sorted(both), 'one': sorted(one),
            'terms': [w for w, _ in found] + loose, 'answers': answers}


def heard_table(results):
    """term -> {heard form -> [turns]}, merged over judges"""
    table = defaultdict(lambda: defaultdict(set))
    for r in results:
        for a in r['answers'].values():
            for t in a.get('terms', []):
                table[t.get('term', '?')][str(t.get('heard', '?')).lower()].add(r['turn'])
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('conversation')
    ap.add_argument('run', help='run directory holding audio/')
    ap.add_argument('--turns', default='', help='comma-separated turn indices (default: all)')
    ap.add_argument('--models', default=','.join(MODELS))
    ap.add_argument('--pronunciation', default=str(ROOT/'pronunciation.json'))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    load_env()
    turns_text = json.loads(Path(args.conversation).read_text(encoding='utf-8'))
    pronunciation = load_pronunciation(Path(args.pronunciation))
    audio = Path(args.run)/'audio'
    turns = [int(v) for v in args.turns.split(',')] if args.turns else [i for i, t in enumerate(turns_text) if 'insert' not in t]
    results = []
    for i in turns:
        r = check_turn(i, turns_text[i]['text'], audio/f'turn_{i:02d}.wav', pronunciation, args.models.split(','))
        results.append(r)
        print(f"turn {i:2}  {'ok  ' if r['ok'] else 'FAIL'}  accent {','.join(map(str, r['accents']))}"
              + (f"  both: {', '.join(r['both'])}" if r['both'] else '')
              + (f"  one judge: {', '.join(r['one'])}" if r['one'] else ''))
    print('\nhow each term was heard (turns):')
    for term, forms in sorted(heard_table(results).items(), key=lambda kv: kv[0].lower()):
        print(f"  {term:16} " + ' | '.join(f"{h} {sorted(ts)}" for h, ts in forms.items()))
    (audio/'reading_check.json').write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    if not all(r['ok'] for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
