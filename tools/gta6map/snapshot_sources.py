#!/usr/bin/env python3
"""Freeze third-party inputs into small fact-only snapshots under tools/gta6map/data/.

  ign_snapshot.json  facts from the IGN/MapGenie Leonida map (id, type, name, in-game x/y and the
                     structured "Key: value" fields; the free-text location prose is NOT stored)
  ppx_snapshot.json  PowerPyx-derived positions from theihtishaam/GTA-6-Interactive-Map-and-Loot-Tracker (MIT)

Usage: snapshot_sources.py --ign <dir with markers.js, taxonomy.js> --ppx <loot tracker checkout>
                           [--mirror <dablon discovered.json>]   # adds IGN markers published after the snapshot
"""
import argparse, json, math, os, re
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--ign'); ap.add_argument('--ppx'); ap.add_argument('--mirror')
args = ap.parse_args()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(OUT, exist_ok=True)


def ign_to_game(lat, lng):
    X = (lng + 1.40625) / 1.40625 * 8192.0
    merc = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    Y = 8192.0 - merc / (2 * math.pi) * 2097152.0
    return (X - 950.0) * 4.0 - 16384.0, 16384.0 - (Y - 200.0) * 4.0


def load_js(path):
    s = open(path, encoding='utf8').read()
    return json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))


snap_path = os.path.join(OUT, 'ign_snapshot.json')
if args.ign:
    M = load_js(os.path.join(args.ign, 'markers.js')); T = load_js(os.path.join(args.ign, 'taxonomy.js'))
    tn = {t['slug']: t['name'] for g in T['groups'] for t in g['types']}
    rows = []
    for m in M:
        x, y = ign_to_game(m['lat'], m['lng'])
        parts = re.split(r'\*\*([^*]+?):\*\*', m.get('d') or '')
        fld = {}
        for i in range(1, len(parts) - 1, 2):
            k = parts[i].strip()
            if k in ('Location', 'Challenge'):
                continue
            v = re.sub(r'_[^_]+_', '', parts[i + 1]).strip()
            if v:
                fld[k] = v
        rows.append({'s': str(m['s']), 't': tn.get(m['t'], ''), 'n': m['n'].strip(), 'x': round(x, 1), 'y': round(y, 1), 'f': fld})
    json.dump({'source': 'IGN / MapGenie Leonida map', 'rows': rows}, open(snap_path, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('ign snapshot rows:', len(rows))

if args.mirror:
    snap = json.load(open(snap_path, encoding='utf8'))
    have = {r['s']: r for r in snap['rows']}
    D = json.load(open(args.mirror, encoding='utf8'))['locations']
    LABEL = {}
    pairs, new = [], []
    for d in D:
        if not d['id'].startswith('ign-'):
            continue
        sid = d['id'][4:]
        if sid in have:
            pairs.append((d['wx'], d['wy'], have[sid]['x'], have[sid]['y']))
        else:
            new.append(d)
    A = np.array(pairs, dtype=float)
    # per-axis linear fit mirror metres -> exact metres (the mirror uses its own projection of the same map)
    ax, bx = np.polyfit(A[:, 0], A[:, 2], 1); ay, by = np.polyfit(A[:, 1], A[:, 3], 1)
    res = np.hypot(ax * A[:, 0] + bx - A[:, 2], ay * A[:, 1] + by - A[:, 3])
    print(f'mirror calibration on {len(A)} shared markers: median {np.median(res):.1f} m, p95 {np.percentile(res, 95):.1f} m')
    added = 0
    for d in new:
        mm = re.search(r'^ign \d+ \((.*)\)\s*$', d.get('source', ''))
        typ = mm.group(1) if mm else ''
        name = re.sub(r'\s+—\s+.*$', '', d['name']).strip()
        snap['rows'].append({'s': d['id'][4:], 't': typ, 'n': name, 'x': round(ax * d['wx'] + bx, 1), 'y': round(ay * d['wy'] + by, 1), 'f': {}, 'via': 'mirror'})
        added += 1
    json.dump(snap, open(snap_path, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('added from mirror:', added, 'total rows:', len(snap['rows']))

if args.ppx:
    P = os.path.join(args.ppx, 'public')

    def xy(nx, ny):
        return round(nx * 13824.0 - 10240.0, 1), round(10496.0 - ny * 19456.0, 1)
    guides = []
    for g in json.load(open(os.path.join(P, 'guides.json'), encoding='utf8')):
        if isinstance(g.get('x'), (int, float)) and isinstance(g.get('y'), (int, float)):
            x, y = xy(g['x'], g['y'])
            guides.append({'x': x, 'y': y, 'title': g.get('title', ''), 'cat': g.get('subcategory') or g.get('category'), 'url': g.get('source')})
    mp = json.load(open(os.path.join(P, 'mission-positions.json'), encoding='utf8'))
    missions = []
    for m in json.load(open(os.path.join(P, 'missions.json'), encoding='utf8')):
        pos = mp.get(m['id'])
        if not pos or not isinstance(pos.get('x'), (int, float)) or not isinstance(pos.get('y'), (int, float)):
            continue
        x, y = xy(pos['x'], pos['y'])
        missions.append({'id': m['id'], 'title': m['title'], 'chapter': m.get('chapter'), 'kind': m.get('kind'),
                         'character': m.get('character'), 'contact': m.get('contact'), 'url': m.get('source'), 'x': x, 'y': y})
    json.dump({'source': 'theihtishaam/GTA-6-Interactive-Map-and-Loot-Tracker (MIT), positions registered from PowerPyx screenshots',
               'guides': guides, 'missions': missions}, open(os.path.join(OUT, 'ppx_snapshot.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('ppx guides:', len(guides), 'missions:', len(missions))
