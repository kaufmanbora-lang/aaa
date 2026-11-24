#!/usr/bin/env python3
"""Copy the GTADB "day" tile pyramid (CC BY 4.0, gtadb.org) into docs/tiles/{z}/{x}/{y}.jpg.

Uniform open-ocean tiles are skipped; the page background uses the same colour.
Usage: python3 build_tiles.py /path/to/gtadb.org [/path/to/docs]
"""
import os, re, sys, shutil
import numpy as np
from PIL import Image

src_root = os.path.join(sys.argv[1], 'maps', 'tiles', '6', 'day')
out_root = os.path.join(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'docs'), 'tiles')
WATER = np.array([47, 144, 176], dtype=np.float32)
kept = skipped = 0
total_bytes = 0
for z in range(0, 7):
    d = os.path.join(src_root, str(z))
    for f in sorted(os.listdir(d)):
        m = re.match(r'(\d+),(\d+),(\d+)\.jpg$', f)
        if not m:
            continue
        y, x = int(m.group(2)), int(m.group(3))
        p = os.path.join(d, f)
        size = os.path.getsize(p)
        if size < 2600:
            a = np.asarray(Image.open(p).convert('RGB'), dtype=np.float32)
            if a.std(axis=(0, 1)).max() < 1.5 and np.abs(a.mean(axis=(0, 1)) - WATER).max() < 4:
                skipped += 1
                continue
        dst = os.path.join(out_root, str(z), str(x))
        os.makedirs(dst, exist_ok=True)
        shutil.copyfile(p, os.path.join(dst, f'{y}.jpg'))
        kept += 1
        total_bytes += size
print(f'kept {kept} tiles ({total_bytes/1e6:.1f} MB), skipped {skipped} uniform ocean tiles')
