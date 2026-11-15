"""Download CC0 GLB packs (KayKit, Quaternius mirror, Kenney) from GitHub into models/<pack>/
(for the three.js pipeline pass --models <project>/assets).

python fetch_assets.py --list
python fetch_assets.py kaykit_adventurers quaternius_modular_men
python fetch_assets.py --mirror-folders                       # list every folder of the Quaternius mirror
python fetch_assets.py --mirror house_interior_pack --only "Chair_|Houseplant_"
python fetch_assets.py kaykit_furniture --models D:/other/project/models

Only urllib + the public GitHub API (no token, 60 requests/hour). Corporate proxies that break TLS for
kenney.nl / poly.pizza / itch.io do not affect github.com; do not disable certificate checks to work around them.
"""
import argparse
import json
import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github+json'}
MIRROR = 'trebeljahr/quaternius-showcase'   # 33 Quaternius packs as GLB; rigs kept, animations stripped

# pack id -> (repo, regex over repo paths to download, extra files such as licenses)
PACKS = {
    'kaykit_adventurers': ('KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0',
                           r'Characters/gltf/[^/]+\.(glb|png)$', ['LICENSE.txt']),
    'kaykit_skeletons': ('KayKit-Game-Assets/KayKit-Character-Pack-Skeletons-1.0',
                         r'Characters/gltf/[^/]+\.(glb|png)$', ['LICENSE.txt']),
    'kaykit_furniture': ('KayKit-Game-Assets/KayKit-Furniture-Bits-1.0', r'/gltf/[^/]+\.(gltf|bin|png)$', ['LICENSE.txt']),
    'kaykit_city': ('KayKit-Game-Assets/KayKit-City-Builder-Bits-1.0', r'/gltf/[^/]+\.(gltf|bin|png)$', ['LICENSE.txt']),
    'kaykit_space': ('KayKit-Game-Assets/KayKit-Space-Base-Bits-1.0', r'/gltf/[^/]+\.(gltf|bin|png)$', ['LICENSE.txt']),
    'kaykit_restaurant': ('KayKit-Game-Assets/KayKit-Restaurant-Bits-1.0', r'/gltf/[^/]+\.(gltf|bin|png)$', ['LICENSE.txt']),
    'kaykit_dungeon': ('KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0', r'/gltf/[^/]+\.(gltf|bin|png)$', ['LICENSE.txt']),
    'kaykit_halloween': ('KayKit-Game-Assets/KayKit-Halloween-Bits-1.0', r'/gltf/[^/]+\.(gltf|bin|png)$', ['LICENSE.txt']),
    'quaternius_modular_men': (MIRROR, r'^public/glb/modular_men/.*\.glb$', ['LICENSES.md']),
    'quaternius_modular_women': (MIRROR, r'^public/glb/modular_women/.*\.glb$', ['LICENSES.md']),
    'quaternius_house_interior': (MIRROR, r'^public/glb/house_interior_pack/.*\.glb$', ['LICENSES.md']),
    'quaternius_cyberpunk': (MIRROR, r'^public/glb/cyberpunk_pack/.*\.glb$', ['LICENSES.md']),
    'quaternius_modular_sci_fi': (MIRROR, r'^public/glb/modular_sci_fi/.*\.glb$', ['LICENSES.md']),
    'quaternius_street': (MIRROR, r'^public/glb/street_pack/.*\.glb$', ['LICENSES.md']),
    'kenney_platformer': ('KenneyNL/Starter-Kit-3D-Platformer', r'^models/character\.glb$', ['LICENSE.md']),
    # full Kenney library mirror (CC0): 4,812 GLB in 49 kits under 3d/<kit>/ -- see 3d/kits.tsv for the kit slugs
    'kenney_furniture': ('shorepine/kenney', r'^3d/furniture/.*\.glb$', ['README.md', '3d/kits.tsv']),
    'kenney_food': ('shorepine/kenney', r'^3d/food/.*\.glb$', ['README.md']),
    'kenney_nature': ('shorepine/kenney', r'^3d/nature/.*\.glb$', ['README.md']),
    # Quaternius Universal Base Characters [Standard] (CC0, only the Superhero bodies in the free tier) + the
    # Universal Animation Library clips on a UE-mannequin rig; textures named *_png.png are referenced by the gltf
    'quaternius_ubc_ual': ('NafisRayan/Animate-Rigged-Humanoid-No-Blender',
                           r'(Base Characters/Godot - UE/|Hairstyles/Rigged to Head Bone/glTF|Unreal-Godot/UAL[12]_Standard\.glb)',
                           ['Universal Base Characters[Standard]/Universal Base Characters[Standard]/License_Standard.txt']),
}


def api(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
        return json.loads(r.read().decode())


def raw(repo, branch, path):
    url = f'https://raw.githubusercontent.com/{repo}/{branch}/{urllib.parse.quote(path)}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=180) as r:
        return r.read()


def repo_files(repo):
    branch = api(f'https://api.github.com/repos/{repo}')['default_branch']
    tree = api(f'https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1')
    if tree.get('truncated'):
        print(f'warning: file list of {repo} truncated', file=sys.stderr)
    return branch, [t['path'] for t in tree['tree'] if t['type'] == 'blob']


def download(repo, pattern, extras, dest, only=None):
    branch, paths = repo_files(repo)
    matched = [p for p in paths if re.search(pattern, p)]
    if not matched:
        raise SystemExit(f'nothing matched {pattern!r} in {repo}')
    wanted = [p for p in matched if re.search(only, p.split('/')[-1])] if only else matched
    if not wanted:
        names = ', '.join(sorted(p.split('/')[-1] for p in matched))
        raise SystemExit(f'--only {only!r} matched none of: {names}')
    dest.mkdir(parents=True, exist_ok=True)
    for p in wanted+[e for e in extras if e in paths]:
        target = dest/p.split('/')[-1]
        if target.exists():
            continue
        data = raw(repo, branch, p)
        target.write_bytes(data)
        print(f'  {target.name:34s} {len(data)//1024:6d} KB')
    print(f'{dest}: {len(wanted)} files')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('packs', nargs='*', help='pack ids (see --list)')
    ap.add_argument('--models', default='models', help='destination root (default ./models)')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--mirror-folders', action='store_true', help='list folders of the Quaternius mirror')
    ap.add_argument('--mirror', help='download one mirror folder, e.g. house_interior_pack')
    ap.add_argument('--only', help='regex on file names to narrow a download')
    args = ap.parse_args()
    root = Path(args.models)

    if args.list:
        for name, (repo, pattern, _) in PACKS.items():
            print(f'{name:28s} {repo}  [{pattern}]')
        return
    if args.mirror_folders:
        _, paths = repo_files(MIRROR)
        counts = {}
        for p in paths:
            if p.startswith('public/glb/') and p.endswith('.glb'):
                counts[p.split('/')[2]] = counts.get(p.split('/')[2], 0)+1
        for folder, n in sorted(counts.items()):
            print(f'{n:5d}  {folder}')
        return
    if args.mirror:
        dest = 'quaternius_'+re.sub(r'_pack$', '', args.mirror)   # same folder as the pack ids above
        download(MIRROR, rf'^public/glb/{re.escape(args.mirror)}/.*\.glb$', ['LICENSES.md'], root/dest, args.only)
    for name in args.packs:
        if name not in PACKS:
            raise SystemExit(f'unknown pack {name!r}; use --list')
        repo, pattern, extras = PACKS[name]
        download(repo, pattern, extras, root/name, args.only)
    if not (args.packs or args.mirror):
        ap.print_help()


if __name__ == '__main__':
    main()
