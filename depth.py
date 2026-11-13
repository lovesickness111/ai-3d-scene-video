"""Estimate a depth map for a single photo (plain Python, not Blender).

.venv/Scripts/python.exe depth.py Example_2D_Image.jpeg --out output/photo_test/depth.png
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps
from transformers import pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image')
    parser.add_argument('--out', required=True)
    parser.add_argument('--model', default='depth-anything/Depth-Anything-V2-Small-hf')
    parser.add_argument('--invert', action='store_true', help='flip near/far if the result looks backwards')
    args = parser.parse_args()

    image = Image.open(args.image).convert('RGB')
    estimator = pipeline(task='depth-estimation', model=args.model, device=-1)
    depth_img = estimator(image)['depth']
    if args.invert:
        depth_img = ImageOps.invert(depth_img.convert('L'))

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    depth_img.save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
