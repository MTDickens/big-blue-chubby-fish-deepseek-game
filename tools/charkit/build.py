"""Build character GLBs.  usage: python3 tools/charkit/build.py [name ...]   (default: all)"""
import importlib
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

ALL = ['bluefish']


def main(names):
    for name in names or ALL:
        t0 = time.time()
        mod = importlib.import_module(f'tools.charkit.characters.{name}')
        out = os.path.join(ROOT, 'assets', 'characters', f'{name}.glb')
        stats = mod.build(out)
        tris = sum(stats.values())
        print(f'{name}: {tris} tris, {os.path.getsize(out) / 1024:.0f} KB, {time.time() - t0:.1f}s')
        for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
            print(f'   {k:18s} {v}')


if __name__ == '__main__':
    main(sys.argv[1:])
