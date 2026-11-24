#!/usr/bin/env python3
"""Copy GTADB in-game landmark photos (CC BY 4.0, gtadb.org) into docs/photos/.

Landmarks tagged L1..L8 carry screenshots from unofficial (leaked) sources; GTADB
itself hides those from the public, and so do we: they are skipped.
Usage: python3 build_photos.py /path/to/gtadb.org [/path/to/docs]
"""
import json, os, re, sys
from PIL import Image

gtadb = sys.argv[1]
docs = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', '..', 'docs')
out = os.path.join(docs, 'photos')
os.makedirs(out, exist_ok=True)
landmarks = json.load(open(os.path.join(gtadb, 'map', 'data', '6', 'landmarks.json'), encoding='utf8'))
leak = re.compile(r'^l\d+$')
MAX = 960
n = skipped = 0
total = 0
for key, it in landmarks.items():
    src = os.path.join(gtadb, 'map', 'photos', '6', f'{key},ig.jpg')
    if not os.path.exists(src):
        continue
    if any(leak.match(t) for t in (it[6] or [])):
        skipped += 1
        continue
    im = Image.open(src).convert('RGB')
    if max(im.size) > MAX:
        im.thumbnail((MAX, MAX), Image.LANCZOS)
    dst = os.path.join(out, f'{key}.jpg')
    im.save(dst, 'JPEG', quality=80, optimize=True, progressive=True)
    total += os.path.getsize(dst)
    n += 1
print(f'wrote {n} photos ({total/1e6:.1f} MB), skipped {skipped} leak-sourced photos')
