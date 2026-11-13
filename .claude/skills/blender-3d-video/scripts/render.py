"""Run a scene script in headless Blender.

python render.py scripts/demo_programmer_mascot.py --out output/demo_programmer_mascot --samples 48
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_blender():
    candidates = []
    if os.environ.get('BLENDER_PATH'):
        candidates.append(Path(os.environ['BLENDER_PATH']))
    candidates.extend(sorted((ROOT/'tools').glob('blender-4.5.*-windows-x64/blender.exe'), reverse=True))
    if shutil.which('blender'):
        candidates.append(Path(shutil.which('blender')))
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit('Blender 4.5 not found: put it in tools/ or set BLENDER_PATH')


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    script, extra = Path(sys.argv[1]).resolve(), sys.argv[2:]
    command = [str(find_blender()), '--background', '--factory-startup', '--python-exit-code', '1',
               '--python', str(script), '--', *extra]
    sys.exit(subprocess.call(command, cwd=ROOT))


if __name__ == '__main__':
    main()
