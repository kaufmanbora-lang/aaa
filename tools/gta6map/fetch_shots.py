#!/usr/bin/env python3
"""Download screenshots of Open GTA 6 Map locations that are not in docs/shots yet.
The project publishes them for reuse in other maps (github.com/fbritoferreira/gta6)."""
import json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, '..', '..', 'docs', 'shots')
os.makedirs(out, exist_ok=True)
BASE = 'https://raw.githubusercontent.com/fbritoferreira/gta6/HEAD/public/'
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
n = fail = 0
for l in json.load(open(os.path.join(HERE, 'data', 'openmap_locations.json'), encoding='utf8')):
    s = l.get('screenshot')
    if not s or n >= limit:
        continue
    dst = os.path.join(out, os.path.basename(s))
    if os.path.exists(dst):
        continue
    try:
        raw = urllib.request.urlopen(BASE + urllib.parse.quote(s), timeout=60).read()
        if len(raw) < 500:
            raise ValueError('too small')
        open(dst, 'wb').write(raw)
        n += 1
    except Exception:
        fail += 1
print(f'new screenshots: {n}, failed: {fail}')
