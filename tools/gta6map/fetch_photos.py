#!/usr/bin/env python3
"""Download in-game photos for GTADB landmarks that have none in docs/photos yet (CC BY 4.0, gtadb.org).
Landmarks tagged L1..L8 (screenshots from leaked material) are skipped."""
import io, json, os, re, sys, urllib.parse, urllib.request
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, '..', '..', 'docs', 'photos')
G = json.load(open(os.path.join(HERE, 'data', 'gtadb_landmarks.json'), encoding='utf8'))
leak = re.compile(r'^l\d+$')
BASE = 'https://raw.githubusercontent.com/rolux/gtadb.org/HEAD/map/photos/6/'
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 400
n = fail = 0
for key, it in G.items():
    if n >= limit:
        break
    if not (isinstance(it[2], list) and it[2]) or any(leak.match(t) for t in (it[6] or [])):
        continue
    dst = os.path.join(out, f'{key}.jpg')
    if os.path.exists(dst):
        continue
    try:
        raw = urllib.request.urlopen(BASE + urllib.parse.quote(f'{key},ig.jpg'), timeout=60).read()
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        if max(im.size) > 960:
            im.thumbnail((960, 960), Image.LANCZOS)
        im.save(dst, 'JPEG', quality=80, optimize=True, progressive=True)
        n += 1
    except Exception as e:      # a missing photo must never break the data update
        fail += 1
print(f'new photos: {n}, failed: {fail}')
