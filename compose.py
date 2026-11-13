"""Turn the rendered 3D frames + timeline into the final frame sequence.

While a turn is spoken its text is drawn into the empty 3D bubble, using the
bubble's on-screen box that qa_scene.py recorded per frame in bubbles.json;
text too long for the bubble is shown as successive chunks. The words appear
as they are spoken, timed by tts.py's cues in audio/audio.json (spread over
the turn by length when there is no voice).
A turn with an `illustration` also gets a card -- title + diagram, table or
bar chart -- in the part of the frame its shot keeps free (`card` in
timeline.json). The card fades in as the camera settles into the shot and
out as it leaves.

.venv/Scripts/python.exe compose.py output/qa_demo --preview 1,2
.venv/Scripts/python.exe compose.py output/qa_demo
"""
import argparse
import json
import re
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = Path(r'C:\Windows\Fonts')
SS = 2  # supersampling: draw at 2x then downscale, PIL shapes have no anti-aliasing
CARD = (255, 255, 255)
INK = (38, 42, 51)
MUTED = (128, 132, 142)
PANEL = (246, 243, 238)
TRACK = (232, 228, 221)
NEUTRAL_BAR = (198, 194, 188)
SHADOW = (120, 108, 92)
SPEAKERS = {
    'dev': {'accent': (58, 104, 176), 'tint': (216, 228, 245)},
    'claude': {'accent': (201, 94, 52), 'tint': (251, 226, 211)},
}
FADE = (.25, .5, .75)  # a card's opacity on the frames it comes in over (and, backwards, goes out over)


@lru_cache(maxsize=None)
def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR/('segoeuib.ttf' if bold else 'segoeui.ttf')), size)


def runs(text):
    """(word, bold, space_before) triples; `**` toggles bold and may sit mid-word."""
    out, bold, space_pending = [], False, False
    for part in re.split(r'(\*\*)', text):
        if part == '**':
            bold = not bold
            continue
        for i, word in enumerate(part.split()):
            out.append((word, bold, i > 0 or space_pending or part[:1].isspace()))
        if part:
            space_pending = part[-1].isspace()
    return out


def layout(text, size, max_w):
    reg, bold = font(size), font(size, True)
    space = reg.getlength(' ')
    lines, cur, cur_w = [], [], 0.0
    for word, is_bold, gap in runs(text):
        f = bold if is_bold else reg
        w = f.getlength(word)
        if cur and gap and cur_w+space+w > max_w:
            lines.append(cur)
            cur, cur_w = [], 0.0
        x = cur_w+space if cur and gap else cur_w
        cur.append((x, word, f, is_bold))
        cur_w = x+w
    if cur:
        lines.append(cur)
    return lines


def arrow(draw, x0, x1, y, u):
    draw.line((x0, y, x1-4*u, y), fill=MUTED, width=max(2, round(3*u)))
    draw.polygon([(x1, y), (x1-10*u, y-7*u), (x1-10*u, y+7*u)], fill=MUTED)


# The card drawers fill the area (x, y, w, h) below a card's title. `u` is the
# length of one pixel of a card 640 wide: they are laid out for that size.

def draw_flow(draw, x, y, w, h, u, sp, question, answers, footer):
    """Question -> Decision Model -> every answer with its probability (the likeliest
    in the accent colour); `footer(draw, x, y, w, u, sp)` draws the strip below."""
    node_h = h*.5
    widths = (w*.3, w*.25, w*.35)
    gap = (w-sum(widths))/2
    xs = (x, x+widths[0]+gap, x+w-widths[2])
    mid, r = y+node_h/2, 18*u
    f_main, f_bold, f_small, f_pct = font(round(20*u)), font(round(22*u), True), font(round(19*u)), font(round(19*u), True)

    draw.rounded_rectangle((xs[0], y, xs[0]+widths[0], y+node_h), r, fill=PANEL)
    draw.multiline_text((xs[0]+widths[0]/2, mid), question, font=f_main, fill=INK, anchor='mm', align='center', spacing=8*u)
    draw.rounded_rectangle((xs[1], y, xs[1]+widths[1], y+node_h), r, fill=sp['accent'])
    draw.multiline_text((xs[1]+widths[1]/2, mid), 'Decision\nModel', font=f_bold, fill=CARD, anchor='mm', align='center',
                        spacing=8*u)
    draw.rounded_rectangle((xs[2], y, xs[2]+widths[2], y+node_h), r, fill=PANEL)
    x0, x1, bar_h = xs[2]+16*u, xs[2]+widths[2]-16*u, 12*u
    likeliest = max(p for _, p in answers)
    for i, (label, p) in enumerate(answers):
        ry = mid+(i-(len(answers)-1)/2)*node_h*.4
        draw.text((x0, ry-8*u), label, font=f_small, fill=INK, anchor='ls')
        draw.text((x1, ry-8*u), f'{p}%', font=f_pct, fill=INK, anchor='rs')
        draw.rounded_rectangle((x0, ry, x1, ry+bar_h), bar_h/2, fill=TRACK)
        draw.rounded_rectangle((x0, ry, x0+max(bar_h, (x1-x0)*p/100), ry+bar_h), bar_h/2,
                               fill=sp['accent'] if p == likeliest else NEUTRAL_BAR)
    for i in range(2):
        arrow(draw, xs[i]+widths[i]+gap*.2, xs[i+1]-gap*.2, mid, u)
    footer(draw, x, y+h*.64, w, u, sp)


def draw_definition(draw, x, y, w, h, u, sp):
    def kinds(draw, x, y, w, u, sp):
        f = font(round(18*u))
        draw.text((x, y), '3 kiểu câu hỏi:', font=f, fill=MUTED)
        px, py, pill_h = x, y+36*u, 42*u
        for label in ('Có / Không', 'Chọn 1 trong nhiều', 'Chấm theo thang'):
            pw = f.getlength(label)+30*u
            draw.rounded_rectangle((px, py, px+pw, py+pill_h), pill_h/2, fill=sp['tint'])
            draw.text((px+pw/2, py+pill_h/2), label, font=f, fill=INK, anchor='mm')
            px += pw+10*u

    draw_flow(draw, x, y, w, h, u, sp, 'Câu hỏi\n+ các phương án', (('Có', 92), ('Không', 8)), kinds)


def draw_raise(draw, x, y, w, h, u, sp):
    def verdict(draw, x, y, w, u, sp):
        pill_h = 60*u
        draw.rounded_rectangle((x, y, x+w, y+pill_h), pill_h/2, fill=sp['accent'])
        draw.text((x+w/2, y+pill_h/2), 'Kết quả:  KHÔNG  ·  xác suất 99%', font=font(round(25*u), True), fill=CARD, anchor='mm')
        draw.text((x+w/2, y+pill_h+26*u), 'Nhanh, rẻ, khỏi viết văn dài dòng.', font=font(round(18*u)), fill=MUTED, anchor='mm')

    draw_flow(draw, x, y, w, h, u, sp, 'Học xong,\nsếp có\ntăng lương?', (('Có', 1), ('Không', 99)), verdict)


def draw_providers(draw, x, y, w, h, u, sp):
    """Comparison table: what each provider takes as input (struck off: what it doesn't) and how much per call."""
    rows = (('Gemini', '', ('Chữ', 'Ảnh', 'Âm thanh', 'Video', 'PDF'), (), '1.000', 'câu'),
            ('OpenAI', '', ('Chữ', 'Ảnh', 'JSON'), ('Âm thanh',), '400', 'câu'),
            ('Jev', 'Tiên phong', ('Chữ', 'Ảnh'), (), '∞', 'chỉ giới hạn độ dài'))
    cols = (x, x+w*.23, x+w*.75)
    f_head, f_name, f_tag = font(round(17*u)), font(round(25*u), True), font(round(15*u), True)
    f_chip, f_num, f_note = font(round(17*u)), font(round(32*u), True), font(round(15*u))
    head_h, chip_h, chip_gap = 34*u, 32*u, 8*u
    draw.text((cols[1], y), 'Nhận đầu vào', font=f_head, fill=MUTED)
    draw.text((cols[2], y), 'Mỗi lần gọi', font=f_head, fill=MUTED)
    row_h = (h-head_h)/len(rows)
    for i, (name, tag, inputs, missing, count, note) in enumerate(rows):
        top = y+head_h+i*row_h
        mid = top+row_h/2
        draw.line((x, top, x+w, top), fill=TRACK, width=2)
        draw.text((cols[0], mid-(14*u if tag else 0)), name, font=f_name, fill=INK, anchor='lm')
        if tag:
            tw, th = f_tag.getlength(tag)+20*u, 24*u
            draw.rounded_rectangle((cols[0], mid+8*u, cols[0]+tw, mid+8*u+th), th/2, fill=sp['tint'])
            draw.text((cols[0]+tw/2, mid+8*u+th/2), tag, font=f_tag, fill=sp['accent'], anchor='mm')

        lines, cx = [[]], cols[1]
        for label in (*inputs, *missing):
            cw = f_chip.getlength(label)+22*u
            if lines[-1] and cx+cw > cols[2]-14*u:
                lines.append([])
                cx = cols[1]
            lines[-1].append((cx, cw, label))
            cx += cw+chip_gap
        cy = mid-(len(lines)*chip_h+(len(lines)-1)*chip_gap)/2
        for line in lines:
            for cx, cw, label in line:
                if label in missing:
                    draw.rounded_rectangle((cx, cy, cx+cw, cy+chip_h), chip_h/2, outline=TRACK, width=2)
                    draw.text((cx+cw/2, cy+chip_h/2), label, font=f_chip, fill=MUTED, anchor='mm')
                    draw.line((cx+8*u, cy+chip_h/2, cx+cw-8*u, cy+chip_h/2), fill=MUTED, width=2)
                else:
                    draw.rounded_rectangle((cx, cy, cx+cw, cy+chip_h), chip_h/2, fill=PANEL)
                    draw.text((cx+cw/2, cy+chip_h/2), label, font=f_chip, fill=INK, anchor='mm')
            cy += chip_h+chip_gap

        draw.text((cols[2], mid-8*u), count, font=f_num, fill=INK, anchor='lm')
        draw.text((cols[2], mid+26*u), note, font=f_note, fill=MUTED, anchor='lm')


def hbar_chart(draw, x, y, w, h, u, sp, rows, vmax, caption, highlight, footer=''):
    """Single-series horizontal bars: one highlighted row in accent, the rest neutral.
    rows: (label, value, value_text, side_note). Values labelled in ink -- a
    video has no tooltip to read them from."""
    f, fb, fs = font(round(21*u)), font(round(21*u), True), font(round(17*u))
    draw.text((x, y), caption, font=fs, fill=MUTED)
    top, bottom = y+40*u, y+h-(60*u if footer else 0)
    row_h = (bottom-top)/len(rows)
    label_w = max(fb.getlength(r[0]) for r in rows)+14*u
    value_w = max(fb.getlength(r[2]) for r in rows)+10*u
    side_w = max((fs.getlength(r[3]) for r in rows if r[3]), default=0)
    bar_x0 = x+label_w
    bar_x1 = x+w-value_w-(side_w+14*u if side_w else 0)
    bar_t = min(row_h*.5, 34*u)
    radius = min(4*SS, bar_t/2)  # 4px rounded data-end after the downscale
    draw.line((bar_x0, top, bar_x0, bottom), fill=TRACK, width=2)
    for i, (label, value, value_text, side) in enumerate(rows):
        cy = top+row_h*(i+.5)
        is_hl = label == highlight
        color = sp['accent'] if is_hl else NEUTRAL_BAR
        end = bar_x0+(bar_x1-bar_x0)*value/vmax
        draw.text((x, cy), label, font=fb if is_hl else f, fill=INK, anchor='lm')
        draw.rounded_rectangle((bar_x0, cy-bar_t/2, end, cy+bar_t/2), radius, fill=color)
        draw.rectangle((bar_x0, cy-bar_t/2, bar_x0+radius, cy+bar_t/2), fill=color)  # square end on the baseline
        draw.text((end+8*u, cy), value_text, font=fb if is_hl else f, fill=INK, anchor='lm')
        if side:
            draw.text((x+w, cy), side, font=fs, fill=MUTED, anchor='rm')
    if footer:
        pill_h = 40*u
        pw = fs.getlength(footer)+32*u
        draw.rounded_rectangle((x, y+h-pill_h, x+pw, y+h), pill_h/2, fill=sp['tint'])
        draw.text((x+pw/2, y+h-pill_h/2), footer, font=fs, fill=INK, anchor='mm')


def draw_pricing(draw, x, y, w, h, u, sp):
    rows = (('Gemini', .10, '0,10 $', ''), ('OpenAI', .10, '0,10 $', ''), ('Jev', .042, '0,042 $', ''))
    hbar_chart(draw, x, y, w, h, u, sp, rows, .12, 'USD cho 1 triệu token đầu vào (thấp hơn = rẻ hơn)', 'Jev',
               footer='Cả 3: không tính tiền phần trả lời')


def draw_benchmark(draw, x, y, w, h, u, sp):
    rows = (('Drex Max', 72.6, '72,6', ''), ('Jev', 66.2, '66,2', '92 ms / việc'),
            ('Gemini', 66.0, '66,0', '211 ms / việc'), ('OpenAI', 60.3, '60,3', ''))
    hbar_chart(draw, x, y, w, h, u, sp, rows, 80, 'Điểm chấm độc lập (cao hơn = tốt hơn) và thời gian mỗi việc', 'Jev')


ILLUSTRATIONS = {  # name in conversation.json -> (card title, drawer)
    'definition': ('Decision API làm gì?', draw_definition),
    'providers': ('3 ông làm Decision API', draw_providers),
    'pricing': ('Giá: rẻ như cho', draw_pricing),
    'benchmark': ('Điểm Artificial Analysis', draw_benchmark),
    'raise': ('Sếp có tăng lương không?', draw_raise),
}


def card_layer(turn, H):
    """The illustration card of a turn -- white panel, title, drawing -- with its soft
    shadow on a transparent layer: (layer, margin around the card's box turn['card'])."""
    x0, y0, x1, y1 = turn['card']
    w, h = (x1-x0)*SS, (y1-y0)*SS
    u, sp = w/640, SPEAKERS[turn['speaker']]
    title, drawer = ILLUSTRATIONS[turn['illustration']]
    card = Image.new('RGBA', (w, h), (*CARD, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((0, 0, w-1, h-1), 26*u, fill=(*CARD, 255))
    pad = 30*u
    draw.rounded_rectangle((pad, pad, pad+44*u, pad+6*u), 3*u, fill=sp['accent'])
    draw.text((pad, pad+16*u), title, font=font(round(30*u), True), fill=INK)
    top = pad+80*u
    drawer(draw, pad, top, w-2*pad, h-pad-top, u, sp)
    card = card.resize((x1-x0, y1-y0), Image.LANCZOS)

    margin = round(H*.06)
    layer = Image.new('RGBA', (card.width+2*margin, card.height+2*margin), (*SHADOW, 0))
    shadow = Image.new('L', layer.size, 0)
    shadow.paste(card.getchannel('A'), (margin, margin+round(H*.012)))
    layer.putalpha(shadow.point(lambda v: v*80//255).filter(ImageFilter.GaussianBlur(H*.016)))
    layer.alpha_composite(card, (margin, margin))
    return layer, margin


def card_frames(turns):
    """{frame: (turn index, opacity)}: a card is up while its turn is spoken, comes in
    over the last frames of the camera's move into the shot and goes out over the
    first frames after the turn."""
    shown = {}
    for i, turn in enumerate(turns):
        if 'card' not in turn:
            continue
        for k, opacity in enumerate(FADE):
            if turn['voice_frame']-len(FADE)+k >= turn['frame_start']:
                shown[turn['voice_frame']-len(FADE)+k] = (i, opacity)
            shown[turn['frame_end']+len(FADE)-k] = (i, opacity)
        for frame in range(turn['voice_frame'], turn['frame_end']+1):
            shown[frame] = (i, 1)
    return shown


def bubble_text_area(box):
    """The rectangle inscribed in the bubble's ellipse (with margin), from its screen bbox."""
    x0, y0, x1, y1 = box
    return (x1-x0)*.64, (y1-y0)*.58


def bubble_chunks(text, box, H):
    """[(lines, line_h)] shown one after another in the bubble. Largest font that
    fits; text too long for a readable size is split at sentence ends."""
    box_w, box_h = bubble_text_area(box)
    min_size, max_size = max(10, round(H*.03)), round(H*.05)

    def fit(t):
        for size in range(max(min_size, min(max_size, round(box_h*.4))), min_size-1, -1):
            line_h = round(size*1.3)
            lines = layout(t, size, box_w)
            if len(lines)*line_h <= box_h:
                return lines, line_h
        return None

    whole = fit(text)
    if whole:
        return [whole]
    pieces, cur = [], ''
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        trial = f'{cur} {sentence}'.strip()
        if cur and fit(trial) is None:
            pieces.append(cur)
            cur = sentence
        else:
            cur = trial
    pieces.append(cur)
    chunks = []
    for piece in pieces:
        fitted = fit(piece)
        if fitted:
            chunks.append(fitted)
            continue
        line_h = round(min_size*1.3)  # one over-long sentence: split its lines at the minimum size
        per = max(1, int(box_h//line_h))
        lines = layout(piece, min_size, box_w)
        chunks.extend((lines[i:i+per], line_h) for i in range(0, len(lines), per))
    return chunks


def char_weight(lines):
    return sum(len(word) for line in lines for _, word, _, _ in line)


def timed(chunks, cues, seconds):
    """The chunks with each word tagged with the second it is spoken at:
    [(lines of (x, word, font, is_bold, second), line_h)]. cues: tts.py's
    [[characters shown before the word, second], ...]; without a voice the
    words are spread over the turn's `seconds` by character count."""
    total = sum(char_weight(lines) for lines, _ in chunks)
    offsets = [c for c, _ in cues or ()]
    out, shown = [], 0
    for lines, line_h in chunks:
        timed_lines = []
        for line in lines:
            timed_lines.append([])
            for x, word, f, is_bold in line:
                when = cues[bisect_right(offsets, shown)-1][1] if cues else .85*seconds*shown/total
                timed_lines[-1].append((x, word, f, is_bold, when))
                shown += len(word)
        out.append((timed_lines, line_h))
    return out


def chunk_at(chunks, now):
    """The chunk on screen at `now`: it stays until the next one's first word is spoken."""
    started = [chunk for chunk in chunks if chunk[0][0][0][4] <= now]
    return started[-1] if started else chunks[0]


def draw_bubble_chunk(img, box, lines, line_h, sp, now):
    """The words spoken by `now`, each at its place in the full chunk -- the text
    follows the voice without the lines reflowing."""
    cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
    draw = ImageDraw.Draw(img)
    y = cy-len(lines)*line_h/2
    for line in lines:
        last_x, last_word, last_f = line[-1][:3]
        line_w = last_x+last_f.getlength(last_word)
        for lx, word, f, is_bold, when in line:
            if when <= now:
                draw.text((cx-line_w/2+lx, y), word, font=f, fill=sp['accent'] if is_bold else INK)
        y += line_h


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', help='e.g. output/qa_demo')
    parser.add_argument('--preview', default='',
                        help='comma-separated turn indices: only write each one\'s bubble chunks, fully spoken, to cards/')
    parser.add_argument('--fps', type=int, default=12, help='must match the render (qa_scene.py --fps)')
    parser.add_argument('--frames', default='', help='comma-separated frame numbers: only composite these')
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    turns = json.loads((run_dir/'timeline.json').read_text(encoding='utf-8'))
    frames_dir = run_dir/'frames'
    H = Image.open(next(frames_dir.glob('frame_*.png'))).height
    boxes = json.loads((run_dir/'bubbles.json').read_text())
    audio_path = run_dir/'audio'/'audio.json'  # written by tts.py: when each word is spoken
    audio = json.loads(audio_path.read_text(encoding='utf-8')) if audio_path.exists() else {}

    def spoken_frames(turn):
        """The turn's frames that have a recorded bubble box (a partial render has only some)."""
        return [f for f in range(turn['voice_frame'], turn['frame_end']+1) if str(f) in boxes]

    @lru_cache(maxsize=None)
    def chunks_of(i):
        """Timed chunks; the camera holds while a turn is spoken, so any of its boxes fits them all."""
        chunks = bubble_chunks(turns[i]['text'], boxes[str(spoken_frames(turns[i])[0])], H)
        return timed(chunks, audio.get(str(i), {}).get('cues'), (turns[i]['frame_end']-turns[i]['voice_frame']+1)/args.fps)

    @lru_cache(maxsize=None)
    def faded_card(i, opacity):
        layer, margin = card_layer(turns[i], H)
        layer.putalpha(layer.getchannel('A').point(lambda v: round(v*opacity)))
        return layer, margin

    def picture(frame, card=None, text=None):
        """Rendered `frame` with a card (turn index, opacity) and bubble text
        (turn index, chunk, seconds into the voice) drawn on it."""
        img = Image.open(frames_dir/f'frame_{frame:04d}.png').convert('RGB')
        if card:
            i, opacity = card
            layer, margin = faded_card(i, opacity)
            x0, y0 = turns[i]['card'][:2]
            img.paste(layer, (x0-margin, y0-margin+round((1-opacity)*H*.03)), layer)  # it rises into place
        if text:
            i, chunk, now = text
            draw_bubble_chunk(img, boxes[str(frame)], *chunk, SPEAKERS[turns[i]['speaker']], now)
        return img

    if args.preview:
        cards_dir = run_dir/'cards'
        cards_dir.mkdir(exist_ok=True)
        for i in (int(v) for v in args.preview.split(',')):
            sample = spoken_frames(turns[i])[0]  # previews usually have only a few frames rendered: one serves every chunk
            for k, chunk in enumerate(chunks_of(i)):
                path = cards_dir/f'turn_{i:02d}_{k+1}.png'
                picture(sample, (i, 1) if 'card' in turns[i] else None, (i, chunk, float('inf'))).save(path)
                print('wrote', path)
        return

    out_dir = run_dir/'frames_composited'
    out_dir.mkdir(exist_ok=True)
    if not args.frames:  # a shorter timeline must not leave the last run's tail for make_video to pick up
        for stale in out_dir.glob('frame_*.png'):
            if int(stale.stem[-4:]) > turns[-1]['frame_end']:
                stale.unlink()
    cards = card_frames(turns)
    speaking = {f: i for i, turn in enumerate(turns) for f in range(turn['voice_frame'], turn['frame_end']+1)}
    for f in sorted(int(v) for v in args.frames.split(',')) if args.frames else range(1, turns[-1]['frame_end']+1):
        text = None
        if f in speaking:
            i = speaking[f]
            now = (f-turns[i]['voice_frame']+1)/args.fps  # a word shows on the frame it starts in
            text = (i, chunk_at(chunks_of(i), now), now)
        picture(f, cards.get(f), text).save(out_dir/f'frame_{f:04d}.png', compress_level=1)
    print('wrote', out_dir)


if __name__ == '__main__':
    main()
