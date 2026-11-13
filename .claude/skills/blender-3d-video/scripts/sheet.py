"""Tile PNGs into one labeled contact sheet (run with .venv python; needs Pillow).

.venv/Scripts/python.exe sheet.py output/x/gallery/*.png --out output/x/sheet.png --cols 4
"""
import argparse
import glob
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser()
    p.add_argument('images', nargs='+')
    p.add_argument('--out', required=True)
    p.add_argument('--cols', type=int, default=4)
    p.add_argument('--width', type=int, default=427, help='tile width; height keeps aspect')
    args = p.parse_args()
    paths = sorted(Path(f) for pattern in args.images for f in glob.glob(pattern))
    if not paths:
        raise SystemExit('no images matched')
    tiles = []
    for path in paths:
        im = Image.open(path).convert('RGB')
        h = round(im.height*args.width/im.width)
        tiles.append((path.stem, im.resize((args.width, h), Image.LANCZOS)))
    tw, th = args.width, tiles[0][1].height
    label_h = 18
    cols = min(args.cols, len(tiles))
    rows = -(-len(tiles)//cols)
    sheet = Image.new('RGB', (cols*tw, rows*(th+label_h)), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(tiles):
        x, y = (i % cols)*tw, (i//cols)*(th+label_h)
        sheet.paste(im, (x, y+label_h))
        draw.text((x+4, y+2), name, fill=(240, 240, 240))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print('SHEET', args.out, f'{len(tiles)} tiles')


if __name__ == '__main__':
    main()
