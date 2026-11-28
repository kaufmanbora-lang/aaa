#!/usr/bin/env python3
"""Build docs/data/markers.json for the GTA 6 fan map from the snapshots in tools/gta6map/data/.

  data/gtadb_landmarks.json   gtadb.org landmarks (CC BY 4.0)
  data/openmap_locations.json Open GTA 6 Map locations (fbritoferreira/gta6, CC BY 4.0) + openmap_removed.json
  data/ign_snapshot.json      facts from the IGN/MapGenie Leonida map (see snapshot_sources.py)
  data/ppx_snapshot.json      PowerPyx-derived positions (MIT, via theihtishaam's loot tracker)
  hints/*.json                Russian "where exactly" hints keyed by source id
  extras.json                 guide-sourced weapons / vehicles / secrets (make_extras.py)
  research/glitches.json      glitches that still work

All positions are stored in in-game metres. Texts shown on the site are written for this project.
"""
import argparse, collections, json, math, os, re, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from taxonomy import (GROUPS, CATS, CAT_R, IGN_CAT, OM_CAT, OM_KIND, IGN_SUB, OM_SUB, LABEL, VALUE, WORDS, SOURCES, TAG_RU, M)

ap = argparse.ArgumentParser()
ap.add_argument('--data', default=os.path.join(HERE, 'data'))
ap.add_argument('--hints', default=os.path.join(HERE, 'hints'))
ap.add_argument('--extras', default=os.path.join(HERE, 'extras.json'))
ap.add_argument('--unplaced', default=os.path.join(HERE, 'extras_skipped.json'))
ap.add_argument('--no-extras', action='store_true')
ap.add_argument('--no-cars', action='store_true', help='skip extras_cars.json (used while make_cars.py rebuilds it)')
ap.add_argument('--docs', default=os.path.join(HERE, '..', '..', 'docs'))
args = ap.parse_args()
OM_BASE = 'https://fbritoferreira.github.io/gta6/'


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower().replace("'", '').replace('’', '')).strip()


def money(s):
    vals = [int(x.replace(',', '')) for x in re.findall(r'\$?\s*([\d,]{3,})', s or '') if x.replace(',', '').isdigit()]
    return max(vals) if vals else None


def tr_value(v):
    v = v.strip()
    return VALUE.get(v, v)


def tr_list(v):
    out = []
    for x in [re.sub(r'^[-•\s]+', '', q).strip() for q in v.split('\n')]:
        if not x:
            continue
        m = re.match(r'^([A-Za-z ]+):\s*(.+)$', x)
        if m and m.group(1).strip() in WORDS:
            val = m.group(2).strip()
            out.append(f"{WORDS[m.group(1).strip()]}: {WORDS.get(val, val)}")
        else:
            out.append(WORDS.get(x, x))
    return out


# ----------------------------------------------------------------------------- marker glyph by name
VEH_KW = [
    ('heli', 'maverick volatus buzzard frogger helicopter swift supervolito havok annihilator valkyrie cargobob savage akula'),
    ('plane', 'jet jets dodo velum mammatus plane duster cuban seaplane shamal luxor titan besra hydra lazer lapwing nimbus streamer 015a'),
    ('boat', 'airboat airgator seashark speeder dinghy yacht boat shasa torlan bombora jetmax squalo tropic suntrap marquis predator speedboat'),
    ('bicycle', 'bmx scorcher bicycle fixter tribike whippet endurex'),
    ('bike', 'sanchez bati fcr zombie nightblade sovereign daemon faggio hakuchou enduro bagger manchez pcj akuma vader '
             'ruffian hexer innovation wolfsbane lectro cliffhanger bobber diabolus esskey thrust vindicator gargoyle avarus '
             'chimera defiler nemesis shotaro motorcycle bike'),
    ('tank', 'tank tanks ridgway barracks crusader rhino apc'),
    ('truck', 'phantom hauler packer mule pounder benson biff flatbed dump mixer truck'),
    ('van', 'burrito boxville youga rumpo speedo pony surfer van journey camper paradise moonbeam minivan'),
    ('pickup', 'bison sandking rancher bobcat yosemite sadler caracara pickup rebel picador slamvan guardian'),
    ('suv', 'kamacho crawler hellion parkland dubsta granger baller cavalcade landstalker patriot mesa seminole bandito '
            'injection wraith buggy riata marshall'),
    ('supercar', 'infernus tempesta thrax emerus zorrusso vitello toros itali furia cheetah turismo banshee coquette '
                 'paragon jugular carbonizzare cypher comet penumbra elegy zentorno entity adder osiris reaper tyrus '
                 'vacca bullet voltic visione autarch tezeract skyline'),
]
VEH_TYPE_ICON = {'Helicopter': 'heli', 'Riverboat': 'boat', 'Bicycle': 'bicycle', 'Chopper': 'bike', 'Superbikes': 'bike',
                 'Superbike': 'bike', 'Dirtbike': 'bike', 'Van': 'van', 'Pickup': 'pickup', 'Super': 'supercar',
                 'Supercars': 'supercar', 'Sport': 'supercar', 'Sports': 'supercar', 'SUV': 'suv', 'Off-Road': 'suv',
                 'Military': 'tank', 'Muscle': 'car', 'Sedan': 'car', 'Coupe': 'car'}


def veh_icon(name, typ=None):
    if typ and typ in VEH_TYPE_ICON:
        return VEH_TYPE_ICON[typ]
    words = set(norm(name).split())
    for ic, kws in VEH_KW:
        if words & set(kws.split()):
            return ic
    return 'car'


def weapon_icon(name, cls=''):
    t, c = ' ' + norm(name) + ' ', (cls or '').lower()
    w = set(t.split())
    if w & {'knife', 'heathen', 'hind', 'machete'} or 'нож' in c:
        return 'knife'
    if w & {'bat'} or 'бита' in c:
        return 'bat'
    if w & {'sniper', 'laird', 'super400', 'longshot', 'mediator'} or 'снайпер' in c or 'марксман' in c:
        return 'sniper'
    if w & {'shotgun', 'moreland', 'gorse', 'comshot', 'shortstraw', 'hobo'} or 'kvga' in t or 'дробовик' in c:
        return 'shotgun'
    if w & {'smg', 'vatra', 'vf5', 'vf5c', 'dsg', 'verro'} or ' w 10 ' in t or ' type 9 ' in t or 'пистолет-пулем' in c:
        return 'smg'
    if w & {'rifle', '556', 'lmg', 'fra', 'tmr', 'drifter'} or ' kz 59 ' in t or ' w 22 ' in t or 'wcr' in t or 'sms' in t \
            or any(k in c for k in ('автомат', 'винтовка', 'пулем')):
        return 'rifle'
    return 'gun'


# ----------------------------------------------------------------------------- GTADB
G = json.load(open(os.path.join(args.data, 'gtadb_landmarks.json'), encoding='utf8'))
LEAK = re.compile(r'^l\d+$')
photo_dir = os.path.join(args.docs, 'photos')
markers = []
lm_xy, lm_area, lm_name, lm_id, lm_tags, lm_photo, lm_pw = [], [], [], [], [], [], []


def lm_category(tags):
    t = set(tags)
    if 'enterable' in t:
        return 'lm_interior'
    if any(LEAK.match(x) for x in t) or 'events' in t:
        return 'lm_leak'
    if t & {'landmark', 'leisure', 'public', 'government', 'point-of-interest', '#ferriswheel', '#racetrack',
            '#police', '#hospital', '#jail', '#safehouse', '#airport', '#airbase', '#marina', '#blimp'}:
        return 'lm_sight'
    if 'hotel' in t:
        return 'lm_hotel'
    if t & {'retail', 'restaurant', 'supermarket'} or any(x.startswith('#') for x in t - {'#bus', '#train', '#metro', '#metromover'}):
        return 'lm_shop'
    if t & {'transportation', '#bus', '#train', '#metro', '#metromover'}:
        return 'lm_transport'
    if 'natural' in t:
        return 'lm_nature'
    if t & {'industrial', 'utilities', 'construction', 'agriculture', 'office'}:
        return 'lm_industry'
    if 'residential' in t:
        return 'lm_res'
    return 'lm_other'


for key, it in G.items():
    addr, xy, _igp, rl_addr, rl_ll, _rlp, tags, _color, _ts = (list(it) + [None] * 9)[:9]
    if not xy or len(xy) < 2 or not all(isinstance(v, (int, float)) for v in xy):
        continue
    tags = list(tags or [])
    parts = [p.strip() for p in (addr or '').split(',')]
    name = parts[0] if parts and parts[0] and parts[0] != '?' else None
    area = ', '.join(p for p in parts[1:] if p and p != '?')
    is_leak = any(LEAK.match(t) for t in tags) or 'events' in tags
    has_photo = (not any(LEAK.match(t) for t in tags)) and os.path.exists(os.path.join(photo_dir, f'{key}.jpg'))
    rl_name = rl_addr.split(',')[0].strip() if rl_addr and rl_addr != '?' else None
    lm_xy.append((xy[0], xy[1])); lm_area.append(area); lm_name.append(name); lm_id.append(key)
    lm_tags.append(set(tags)); lm_photo.append(has_photo)
    lm_pw.append(_igp[0] if isinstance(_igp, list) and _igp else 0)
    title = name or (f'Прототип: {rl_name}' if rl_name else f'Объект {key}')
    facts = []
    kinds = [TAG_RU[t] for t in tags if t in TAG_RU]
    if kinds:
        facts.append(['Тип', ', '.join(dict.fromkeys(kinds))])
    if rl_addr and rl_addr != '?':
        facts.append(['Прототип в реальности', rl_addr + (' (не подтверждено)' if 'unconfirmed' in tags else '')])
    v, note = 2, None
    if 'events' in tags or '//may-not-exist' in tags:
        v, note = 1, 'Известно по материалам слива 2022 года; в релизной версии может отсутствовать или отличаться.'
    elif any(LEAK.match(t) for t in tags):
        note = 'Место впервые опознано по материалам слива 2022 года (фото из слива не публикуются).'
    if not name and is_leak:
        v = min(v, 1)
    m = {'id': key, 'c': lm_category(tags), 'n': title, 'x': round(xy[0]), 'y': round(xy[1]), 'r': 1, 'a': area, 's': ['gtadb'], 'v': v}
    if facts:
        m['f'] = facts
    if note:
        m['t'] = note
    if has_photo:
        m['p'] = [f'photos/{key}.jpg']
    if is_leak:
        m['lk'] = 1
    if rl_ll and len(rl_ll) == 2 and all(isinstance(q, (int, float)) for q in rl_ll):
        m['rl'] = [round(rl_ll[0], 6), round(rl_ll[1], 6)]
    m['u'] = [['Открыть в GTADB', f'https://map.gtadb.org/#VI,{key}']]
    markers.append(m)

LM = np.array(lm_xy, dtype=np.float64)
_members, _parent = collections.defaultdict(list), set()
for (lx, ly), area in zip(lm_xy, lm_area):
    comps = [c.strip() for c in area.split(',') if c.strip()]
    for comp in comps:
        _members[comp].append((lx, ly))
    if len(comps) >= 2:
        _parent.add(comps[-1])
labels = []
for nm, pts in _members.items():
    if nm == 'Leonida' or len(nm) < 3 or '?' in nm:
        continue
    big = nm in _parent or nm.endswith('County') or nm.endswith('National Park')
    if len(pts) < (6 if big else 4):
        continue
    arr = np.array(pts)
    labels.append({'n': nm, 'x': int(np.median(arr[:, 0])), 'y': int(np.median(arr[:, 1])), 'k': 1 if big else 2, 'w': len(pts)})
labels.sort(key=lambda q: (q['k'], -q['w']))
print('GTADB landmarks placed:', len(markers), '| area labels:', len(labels))


def nearest_lm(x, y, k=6):
    d = np.hypot(LM[:, 0] - x, LM[:, 1] - y)
    idx = np.argsort(d)[:k]
    return [(int(i), float(d[i])) for i in idx]


def area_of(x, y):
    c = collections.Counter()
    for i, d in nearest_lm(x, y, 8):
        if d > 1200 or not lm_area[i]:
            continue
        c[lm_area[i]] += 1.0 / (40.0 + d)
    return c.most_common(1)[0][0] if c else ''


def near_photo(x, y, maxd=140):
    for i, d in nearest_lm(x, y, 12):
        if d > maxd:
            break
        if lm_photo[i] and lm_name[i] and lm_pw[i] >= 320:
            return {'p': f'photos/{lm_id[i]}.jpg', 'n': lm_name[i], 'd': int(round(d))}
    return None


# ----------------------------------------------------------------------------- PowerPyx-derived positions
PPX = json.load(open(os.path.join(args.data, 'ppx_snapshot.json'), encoding='utf8'))
ppx_points = [(g['x'], g['y'], g['title'], g['cat'], g['url']) for g in PPX['guides']]
missions_out = []
KIND = {'story': 'Сюжетная миссия', 'stranger': 'Встреча с незнакомцем', 'side': 'Побочная миссия', 'optional': 'Необязательное задание'}
for m in PPX['missions']:
    facts = [['Тип', KIND.get(m.get('kind'), m.get('kind') or '')]]
    if m.get('chapter') is not None:
        facts.append(['Глава', 'Пролог' if m['chapter'] == 0 else str(m['chapter'])])
    if m.get('character'):
        facts.append(['Персонаж', m['character']])
    if m.get('contact'):
        facts.append(['Кто даёт', m['contact']])
    mk = {'id': 'm-' + m['id'].replace('mission-', ''), 'c': 'mission', 'n': m['title'], 'x': round(m['x']), 'y': round(m['y']),
          'r': 3 if m.get('kind') == 'story' else 2, 'f': facts, 's': ['ppx'], 'v': 2,
          't': 'Место начала миссии (маркер на карте игры).'}
    if m.get('url'):
        mk['u'] = [['Прохождение на PowerPyx', m['url']]]
    missions_out.append(mk)

# ----------------------------------------------------------------------------- hints
TR = {}
if os.path.isdir(args.hints):
    for fn in sorted(os.listdir(args.hints)):
        if fn.endswith('.json'):
            TR.update(json.load(open(os.path.join(args.hints, fn), encoding='utf8')))
print('RU hints:', len(TR))

# ----------------------------------------------------------------------------- IGN / MapGenie snapshot
CARD_R = {'Gold': 5, 'Purple': 4, 'Silver': 3, 'Pink': 3, 'Teal': 3, 'Bronze': 2, 'Deep Red': 2, 'Standard': 1}
CARD_RU = {'Gold': 'золотая', 'Purple': 'фиолетовая', 'Silver': 'серебряная', 'Pink': 'розовая',
           'Bronze': 'бронзовая', 'Deep Red': 'тёмно-красная', 'Standard': 'стандартная', 'Teal': 'бирюзовая'}
ign_markers, derived = [], []
for row in json.load(open(os.path.join(args.data, 'ign_snapshot.json'), encoding='utf8'))['rows']:
    tname = row['t']
    cat = IGN_CAT.get(tname)
    if not cat:
        continue
    x, y, fld = row['x'], row['y'], row.get('f') or {}
    name = row['n'].strip()
    sub = IGN_SUB.get(tname)
    facts = []
    r = CAT_R[cat]
    hm = re.match(r'^Hoop (\d+)', name)
    if hm:
        name = f'Баскетбольное кольцо №{int(hm.group(1)) + 1}'
    elif name == 'ATM':
        name = 'Банкомат'
    elif name == 'ATM (Towable)':
        name = 'Банкомат (можно увезти)'
    elif name == 'Electric Vehicle Charger':
        name = 'Зарядка для электромобилей'
    elif name.startswith('Hotspot - '):
        name = 'Рыбное место: ' + name[10:]
    elif re.match(r'^Book Swap \d+$', name):
        name = 'Книгообмен №' + name.split()[-1]
    for k, v in fld.items():
        if k not in LABEL:
            continue
        v = v.strip()
        if not v or '??' in v:
            continue
        if '\n' in v or v.startswith('-'):
            lst = tr_list(v)
            if k == 'Key Valuables':
                lst = [re.sub(r' Vehicle$', ' (транспорт)', q) for q in lst]
            val = ', '.join(lst) if k != 'Route' else '; '.join(lst)
        else:
            val = tr_value(re.sub(r'\s+', ' ', v))
        lab = LABEL[k]
        if k == 'Security' and cat.startswith('veh_'):
            lab = 'Сигнализация'
        if k == 'Type' and cat in ('race', 'drone'):
            lab = 'Тип / район'
        facts.append([lab, val])
    if cat.startswith('veh_'):
        sv = money(fld.get('Sell Value'))
        typ = fld.get('Type', '')
        if sv is None:
            r = 4 if typ in ('Helicopter', 'Super', 'Supercars') else 3
        else:
            r = 5 if sv >= 15000 else 4 if sv >= 7000 else 3 if sv >= 3000 else 2 if sv >= 1500 else 1
        if cat == 'veh_randy':
            r = max(r, 4)
        if cat == 'veh_standout':
            r = max(r, 2)
    elif cat == 'card':
        var = name.split(' - ')[-1].strip()
        r = CARD_R.get(var, 2)
        if var in CARD_RU:
            facts.insert(0, ['Версия карточки', CARD_RU[var]])
    elif cat in ('bank', 'bigbank', 'jewelry', 'payday', 'pawn', 'store', 'fastfood', 'liquor'):
        tv = money(fld.get('Take Value'))
        if tv is not None:
            r = 5 if tv >= 150000 else 4 if tv >= 100000 else 3 if tv >= 20000 else 2 if tv >= 5000 else 1
    elif cat == 'gang':
        r = {'High': 4, 'Medium': 3, 'Low': 2}.get(fld.get('Security', '').strip(), 3)
    mk = {'id': 'i' + row['s'], 'c': cat, 'n': name, 'x': round(x), 'y': round(y), 'r': r, 's': ['ign'], 'v': 2}
    if sub:
        mk['sub'] = sub
    if facts:
        mk['f'] = facts
    if TR.get(row['s']):
        mk['t'] = TR[row['s']]
    mk['_fld'] = fld
    ign_markers.append(mk)
    if cat == 'gang' and fld.get('Key Valuables'):
        items = [re.sub(r'^[-•\s]+', '', q).strip() for q in fld['Key Valuables'].split('\n')]
        items = [q for q in items if q and q != 'Safe' and not q.endswith(' Vehicle')]
        for j, item in enumerate(items):
            is_watch = item.endswith('Watch')
            ang = 2 * math.pi * j / max(1, len(items)) + 0.6
            derived.append({
                'id': f"k{row['s']}-{j}", 'c': 'valuable' if is_watch else 'weapon', 'n': item,
                'x': round(x + 9 * math.cos(ang)), 'y': round(y + 9 * math.sin(ang)),
                'r': 4 if is_watch else 5, 's': ['ign'], 'v': 2,
                'sub': 'Часы' if is_watch else 'Уникальный вариант оружия',
                'f': [['Где', f"нелегальная операция «{row['n'].strip()}»" + (f" ({sub})" if sub else '')],
                      ['Охрана объекта', tr_value(fld.get('Security', '').strip() or '—')]],
                't': 'Ключевая ценность нелегальной операции: находится на территории объекта, внутри охраняемой зоны.',
                '_sec': fld.get('Security', '').strip(), '_gang': 1,
            })
print('IGN markers:', len(ign_markers), 'derived unique items:', len(derived))

# ----------------------------------------------------------------------------- Open GTA 6 Map
OM = json.load(open(os.path.join(args.data, 'openmap_locations.json'), encoding='utf8'))
rem_path = os.path.join(args.data, 'openmap_removed.json')
OM_REMOVED = {r['id'] for r in json.load(open(rem_path, encoding='utf8'))} if os.path.exists(rem_path) else set()
STOPW = {'the', 'of', 'and', 'store', 'shop', 'station', 'a', 'at', 'in', 'card', 'safe', 'atm', 'gas'}


def toks(s):
    return {t for t in norm(s).split() if t not in STOPW and len(t) > 1}


by_cat = collections.defaultdict(list)
for mk in ign_markers + derived:
    by_cat[mk['c']].append(mk)
VEHS = ('veh_standout', 'veh_randy', 'veh_moses')
FAMILY = {'veh_standout': VEHS, 'veh_randy': VEHS, 'veh_moses': VEHS, 'bank': ('bank', 'bigbank'), 'bigbank': ('bank', 'bigbank'),
          'jewelry': ('jewelry', 'pawn'), 'pawn': ('jewelry', 'pawn'), 'garage': ('garage', 'garage_buy'),
          'garage_buy': ('garage', 'garage_buy'), 'cafe': ('cafe', 'fastfood', 'bar', 'streetfood', 'club'),
          'bar': ('bar', 'cafe', 'club'), 'club': ('club', 'bar'), 'store': ('store', 'gas', 'liquor'),
          'gas': ('gas', 'store'), 'wpickup': ('weapon',)}
NAMED = set(VEHS) | {'weapon', 'valuable'}
om_markers, om_ids, om_types = [], [], {}
used_ign, n_merge, n_dup, dists = set(), 0, 0, []


def parse_om_desc(desc):
    facts, text = [], []
    for seg in [s.strip() for s in (desc or '').split(';')]:
        m = re.match(r'^([A-Z][A-Za-z \']{2,24}):\s*(.+)$', seg)
        if m and m.group(1) in LABEL:
            facts.append([m.group(1), m.group(2).strip()])
        elif seg:
            text.append(seg)
    return facts, '; '.join(text)


om_unmapped = collections.Counter()      # upstream types with no category of their own: they land in 'other buildings'
for l in OM:
    oid = l['id']
    om_ids.append(oid)
    if oid in OM_REMOVED:
        continue
    typ = l.get('type') or ''
    cat = OM_CAT[typ] if typ in OM_CAT else ('card' if typ.endswith(' card') else OM_KIND.get(l.get('kind'), 'lm_other'))
    if typ not in OM_CAT and not typ.endswith(' card') and l.get('kind') not in OM_KIND:
        om_unmapped[typ] += 1
    if cat is None:
        continue
    om_types[typ] = cat
    x, y = 32.0 * l['x'] - 16384.0, 16384.0 - 32.0 * l['y']
    name = (l.get('name') or typ).strip()
    raw_facts, text = parse_om_desc(l.get('description'))
    fd = dict(raw_facts)
    if cat == 'bank' and (fd.get('Robbery') == 'Vault' or (money(fd.get('Take value')) or 0) >= 60000):
        cat = 'bigbank'
    if cat == 'jewelry' and 'pawn' in name.lower():
        cat = 'pawn'
    if cat == 'garage' and fd.get('Price'):
        cat = 'garage_buy'
    if cat == 'veh_randy' and 'moses' in name.lower():
        cat = 'veh_moses'
    img = None
    if l.get('screenshot'):
        local = os.path.join(args.docs, 'shots', os.path.basename(l['screenshot']))
        img = {'u': ('shots/' + os.path.basename(l['screenshot'])) if os.path.exists(local) else OM_BASE + l['screenshot'],
               'c': 'Скриншот: Open GTA 6 Map'}
    best = None
    nt = toks(re.sub(r'\(.*?\)', '', name))
    for c2 in FAMILY.get(cat, (cat,)):
        for mk in by_cat.get(c2, ()):
            d = math.hypot(mk['x'] - x, mk['y'] - y)
            if d > 160:
                continue
            common = len(nt & toks(mk['n']))
            if cat in NAMED or mk['c'] in NAMED:
                ok = (common >= 2) or (common >= 1 and d <= 45) or d <= 6
            else:
                ok = d <= 14 or (common >= 1 and d <= 45) or (common >= 2 and d <= 90)
            if ok and (best is None or d < best[0]):
                best = (d, mk)
    if best and best[1]['id'] not in used_ign:
        d, mk = best
        used_ign.add(mk['id']); n_merge += 1; dists.append(d)
        mk['s'].append('om')
        mk['_om'] = oid
        if d >= 3.0:
            mk['v'] = 3      # the same thing pinned separately on two maps
        if mk['id'].startswith('k'):
            mk['x'], mk['y'] = round(x), round(y)      # the community pin marks the item itself, not just the compound
            mk['t'] = None
        if img and not mk.get('img'):
            mk['img'] = img
        if text and not mk.get('t'):
            mk['t'] = TR.get(oid) or text
            if not TR.get(oid):
                mk['_en'] = 1
        have = {f[0] for f in mk.get('f', [])}
        for k, v in raw_facts:
            if LABEL[k] not in have and k in ('Code', 'Safe code', 'Computer password', 'Set'):
                mk.setdefault('f', []).append([LABEL[k], v])
        continue
    if best and best[0] <= 5:
        n_dup += 1
        continue
    r = CAT_R[cat]
    facts = []
    for k, v in raw_facts:
        facts.append([LABEL[k], VALUE.get(v, v) if k in ('Security', 'Robbery') else v])
    sub = OM_SUB.get(typ)
    if cat == 'card':
        mset = re.match(r'^(.*?) card$', typ)
        sname = fd.get('Set') or (mset.group(1) if mset else '')
        sub = ('Набор ' + sname) if sname else None
        var = next((k for k in CARD_R if re.search(r'\b' + k + r'\b', name)), None)
        if var:
            r = CARD_R[var]
    elif cat in VEHS:
        r = 5 if 'gold' in name.lower() else 4 if veh_icon(name) in ('supercar', 'heli', 'plane') else 3
    elif cat in ('bank', 'bigbank', 'jewelry', 'payday', 'pawn', 'store', 'liquor', 'gang'):
        tv = money(fd.get('Take value'))
        if tv is not None:
            r = 5 if tv >= 150000 else 4 if tv >= 100000 else 3 if tv >= 20000 else 2 if tv >= 5000 else 1
        if cat == 'gang':
            r = max(r, {'High': 4, 'Medium': 3, 'Low': 2}.get(fd.get('Security', ''), 3))
    elif cat == 'secret':
        r = 3
    mk = {'id': 'o-' + oid, 'c': cat, 'n': name, 'x': round(x), 'y': round(y), 'r': r, 's': ['om'], 'v': 2, '_om': oid, '_omfd': fd}
    if sub:
        mk['sub'] = sub
    if facts:
        mk['f'] = facts
    if text:
        mk['t'] = TR.get(oid) or text
        if not TR.get(oid):
            mk['_en'] = 1
    if img:
        mk['img'] = img
    if l.get('area'):
        mk['a'] = l['area']
    om_markers.append(mk)
dd = np.array(dists) if dists else np.array([0.0])
print(f'Open GTA 6 Map: {len(OM)} rows -> merged into IGN points {n_merge} (median offset {np.median(dd):.1f} m, '
      f'{int((dd < 3).sum())} closer than 3 m), exact duplicates dropped {n_dup}, new markers {len(om_markers)}')

# ----------------------------------------------------------------------------- cross-verification (GTADB tags / names, PowerPyx)
GTADB_TAG = {
    'ammu': {'#guns'}, 'gas': {'#gas'}, 'spray': {"#pay'n'spray"}, 'mod': {'#modshop'}, 'bus': {'#bus'},
    'train': {'#train', '#metro', '#metromover'}, 'tattoo': {'#tattoos'}, 'hair': {'#hair'},
    'clothes': {'#clothes', '#shoes'}, 'bar': {'#bar', '#drinks'}, 'fastfood': {'#fastfood'},
    'club': {'#nightclub', '#stripclub'}, 'electronics': {'#electronics'}, 'wash': {'#carwash'},
    'contact': {'#fence'}, 'streetfood': {'#vendor', '#food'}, 'store': {'#supermarket'}, 'police': {'#police'},
    'hospital': {'#hospital'}, 'marina': {'#marina'}, 'airport': {'#airport', '#airbase'}, 'safehouse': {'#safehouse'},
}
PPX_CAT = {'bank': {'Small banks', 'Bank vaults'}, 'bigbank': {'Bank vaults', 'Small banks'}, 'payday': {'Payday loans'},
           'electronics': {'Electronics shops'}, 'pool': {'Pool'}, 'gym': {'Fitness'}, 'golf': {'Golf'}}
STOP2 = {'the', 'of', 'and', 'store', 'shop', 'station', 'big', 'bank', 'gas', 'a', 'n', 'at', 'in'}


def tokens(s):
    return {t for t in norm(s).split() if t not in STOP2 and len(t) > 1}


confirmed = 0
for mk in ign_markers + om_markers:
    x, y, cat = mk['x'], mk['y'], mk['c']
    srcs = []
    want = GTADB_TAG.get(cat)
    nt = tokens(re.sub(r'\s+[-–]\s+.*$', '', mk['n']))
    for i, d in nearest_lm(x, y, 10):
        if d > 160:
            break
        if want and d <= 70 and (lm_tags[i] & want):
            srcs.append(('gtadb', lm_id[i])); break
        if lm_name[i] and nt:
            lt = tokens(lm_name[i])
            if lt and (nt <= lt or lt <= nt) and (len(nt & lt) >= 2 or len(nt) == 1 == len(lt)):
                srcs.append(('gtadb', lm_id[i])); break
    want_p = PPX_CAT.get(cat)
    if want_p:
        for (px, py, title, pc, url) in ppx_points:
            if pc in want_p and math.hypot(px - x, py - y) <= 90:
                srcs.append(('ppx', url)); break
    if srcs:
        mk['v'] = 3
        confirmed += 1
        for k, ref in srcs:
            if k not in mk['s']:
                mk['s'].append(k)
            if k == 'ppx' and ref:
                mk.setdefault('u', []).append(['Гайд PowerPyx', ref])
            if k == 'gtadb':
                mk.setdefault('u', []).append(['Это место в GTADB', f'https://map.gtadb.org/#VI,{ref}'])
if om_unmapped:
    print('WARNING: Open GTA 6 Map types without a category (shown as other buildings) - add them to OM_CAT and OM_SUB in taxonomy.py:', dict(om_unmapped))
print('points confirmed by GTADB / PowerPyx:', confirmed)

# ----------------------------------------------------------------------------- extras (research)
extras = [] if args.no_extras or not os.path.exists(args.extras) else json.load(open(args.extras, encoding='utf8'))
cars_path = os.path.join(HERE, 'extras_cars.json')
if not args.no_extras and not args.no_cars and os.path.exists(cars_path):
    extras += json.load(open(cars_path, encoding='utf8'))
manual_path = os.path.join(HERE, 'extras_manual.json')      # finds added by hand during the daily checks (two or more sources each)
if not args.no_extras and os.path.exists(manual_path):
    extras += json.load(open(manual_path, encoding='utf8'))
_by_id = {q['id']: q for q in derived + ign_markers}
_any_id = {q['id']: q for q in derived + ign_markers + om_markers}
_by_name = collections.defaultdict(list)
for q in om_markers + derived + ign_markers:
    _by_name[norm(re.sub(r'\(.*?\)', '', q['n']))].append(q)
final_extras, n_em = [], 0
for e in extras:
    tgt = _by_id.get(e.get('merge')) if e.get('merge') else None
    if e.get('merge') and tgt is None:
        continue
    if e.get('merge_any'):
        tgt = _any_id.get(e['merge_any']) or next((q for q in final_extras if q.get('id') == e['merge_any']), None)
        if tgt is None:
            continue
    if tgt is None and e.get('c') in ('weapon', 'veh_standout', 'veh_randy') and 'x' in e and not e.get('nomerge'):
        # the same named item pinned by the community map: keep that (exact) pin and attach the guide info to it
        fam = ('weapon',) if e['c'] == 'weapon' else VEHS
        cands = [q for q in _by_name.get(norm(re.sub(r'\(.*?\)', '', e['n'])), []) if q['c'] in fam]
        cands = [q for q in cands if math.hypot(q['x'] - e['x'], q['y'] - e['y']) <= (2500 if e.get('ap') else 400)]
        if cands:
            tgt = min(cands, key=lambda q: math.hypot(q['x'] - e['x'], q['y'] - e['y']))
    if tgt is not None:
        n_em += 1
        if e.get('t') and (tgt['c'] in ('weapon', 'valuable') or not tgt.get('t') or tgt.get('_en')):
            tgt['t'] = e['t']; tgt.pop('_en', None)
        for u in e.get('u', []):
            tgt.setdefault('u', []).append(u)
        if 'web' not in tgt['s']:
            tgt['s'].append('web')
        if e.get('v', 0) >= 3 or ('om' in tgt['s'] and 'merge' not in e):
            tgt['v'] = 3
        for f in e.get('f', []):
            if f[0] not in [q[0] for q in tgt.get('f', [])] and f[0] != 'Привязка на карте':
                tgt.setdefault('f', []).append(f)
        for k, val in (e.get('fldm') or {}).items():     # values published for the base model, not this exact spawn
            tgt.setdefault('_fldm', {}).setdefault(k, val)
        for k, val in (e.get('fld') or {}).items():      # lock / alarm / tracker facts found by research
            if val and not (tgt.setdefault('_fld', {}).get(k) or '').strip('? '):
                tgt['_fld'][k] = val
                lab = 'Сигнализация' if k == 'Security' else LABEL.get(k, k)
                if lab not in [q[0] for q in tgt.get('f', [])]:
                    tgt.setdefault('f', []).append([lab, tr_value(val)])
        continue
    if 'x' not in e:
        continue
    ne = {k: v for k, v in e.items() if k not in ('aka', 'force_new', 'merge', 'merge_any', 'fld', 'nomerge') and v not in (None, [], '')}
    if e.get('fld'):
        ne['_fld'] = dict(e['fld'])
        for k, val in e['fld'].items():
            ne.setdefault('f', []).append(['Сигнализация' if k == 'Security' else LABEL.get(k, k), tr_value(val)])
    final_extras.append(ne)
print('extras: merged', n_em, 'added as new', len(final_extras))

# ----------------------------------------------------------------------------- glitches (research/glitches.json)
glitch_markers, glitch_unplaced = [], []
gp = os.path.join(HERE, 'research', 'glitches.json')
if os.path.exists(gp):
    GJ = json.load(open(gp, encoding='utf8'))
    patch = (GJ.get('patches') or [{}])[-1]
    patch_txt = f"{patch.get('version', '')} от {patch.get('date', '')}".strip(' от')
    ANCH = [('apollo aggregates', 'Vapid Rumpo'), ('donnie', "Donnie's Trailer")]

    def anchor(text):
        low = text.lower()
        for kw, nm in ANCH:
            if kw in low:
                for q in ign_markers:
                    if nm.lower() in q['n'].lower():
                        return q
        return None
    GK = {'money': 'Денежный глитч', 'duplication': 'Дюп', 'out_of_bounds': 'Выход за карту', 'safe_spot': 'Безопасная точка',
          'infinite': 'Бесконечный ресурс', 'physics': 'Физика', 'interior': 'Закрытый интерьер', 'other': 'Баг'}
    GN = [('stash bag', 'Дюп сумки с добычей (Stash Bag)'), ('character-switch', 'Глитч Apollo Aggregates: смена персонажа'), ('van drive', 'Глитч Apollo Aggregates: уехать на фургоне'),
          ('save and reload', 'Денежный глитч Apollo Aggregates: сохранение и загрузка'),
          ("donnie's payment", 'Баг: плата Донни не появляется у трейлера')]

    def glitch_name(n):
        low = n.lower()
        return next((ru for kw, ru in GN if kw in low), re.sub(r'\s*\(.*?\)', '', n).strip())
    for i, it in enumerate(list(GJ.get('items', [])) + list(GJ.get('unplaced', []))):
        if it.get('status') == 'patched':
            continue
        a = anchor(' '.join(str(it.get(k) or '') for k in ('name', 'landmark', 'spot')))
        links = [[re.sub(r'^https?://(www\.)?', '', u).split('/')[0], u] for u in (it.get('sources') or [])[:4]]
        st = it.get('status')
        if not a:
            glitch_unplaced.append({'k': 'glitch', 'n': it['name'], 't': it.get('desc_ru'), 'u': links[:2]})
            continue
        facts = [['Тип', GK.get(it.get('kind'), 'Баг')],
                 ['Статус', ('работает' if st == 'working' else 'неясно') + (f' (последний патч {patch_txt})' if patch_txt else '')]]
        if it.get('last_confirmed'):
            facts.append(['Последняя проверка', str(it['last_confirmed'])])
        ang = i * 2.1
        glitch_markers.append({
            'id': f'xg{i}', 'c': 'glitch', 'n': glitch_name(it['name']), 'r': 4 if it.get('verified') else 2,
            'x': round(a['x'] + (16 + 9 * (i // 3)) * math.cos(ang)), 'y': round(a['y'] + (16 + 9 * (i // 3)) * math.sin(ang)), 't': it.get('desc_ru'),
            'f': facts, 'u': links, 's': ['web'], 'v': 3 if it.get('verified') else 1, 'sub': GK.get(it.get('kind'), 'Баг'),
            '_gst': st,
        })
    print('glitches placed:', len(glitch_markers), 'unplaced:', len(glitch_unplaced))

# ----------------------------------------------------------------------------- "what you need" chips
# chip = [icon, colour (g ok / y caution / r hard / b info / d unknown), title, detail]
SEC_C = {'High': 'r', 'Medium': 'y', 'Low': 'g'}
SEC_RU = {'High': 'высокая', 'Medium': 'средняя', 'Low': 'низкая'}
ROB_NOTE = {'bank': 'bank', 'payday': 'bank', 'jewelry': 'jewelry', 'pawn': 'pawn', 'store': 'stickup', 'fastfood': 'stickup',
            'liquor': 'stickup', 'gang': 'gang'}


def requirements(mk):
    c, fld, fd = mk['c'], mk.get('_fld') or {}, dict(mk.get('f') or [])
    q, summary = [], None
    if c == 'veh_lux':
        q.append(['keyfob', 'y', 'Дорогие машины обычно с защитой', M['lux']])
    elif c.startswith('veh_') and re.search(r'\(остов\)|\bpart \d+/\d+|остов', mk['n'] + ' ' + (mk.get('sub') or ''), re.I):
        q.append(['scan', 'b', 'Отсканировать остов в WAiNK', M['wyman']])      # a wreck for Wyman: nothing to break into
    elif c.startswith('veh_'):
        acc, sec, trk = [('' if '?' in fld.get(k, '') else fld.get(k, '').strip()) for k in ('Access', 'Security', 'Tracker')]
        if acc == 'Unlocked':
            q.append(['lockopen', 'g', 'Двери открыты', M['unlocked']])
        elif acc == 'Locked':
            q.append(['lock', 'y', 'Заперта — нужен Slim Jim или разбить стекло', M['locked']])
        elif acc == 'Key Cloner':
            q.append(['keyfob', 'r', 'Нужен клонер ключей (Key Cloner)', M['cloner']])
        if sec == 'None':
            q.append(['alarm', 'g', 'Без сигнализации', ''])
        elif sec == 'Alarmed':
            q.append(['alarm', 'y', 'Сигнализация', M['alarm']])
        elif sec == 'Deactivated':
            q.append(['alarm', 'g', 'Сигнализация отключена', M['alarm_off']])
        if trk == 'None':
            q.append(['tracker', 'g', 'Без трекера', M['trk_none']])
        elif trk == 'Standard':
            q.append(['tracker', 'y', 'Жёлтый трекер (стандартный)', M['trk_std']])
        elif trk == 'Advanced':
            q.append(['tracker', 'r', 'Красный трекер (продвинутый)', M['trk_adv']])
        elif trk == 'Tracker':
            q.append(['tracker', 'y', 'Есть трекер (тип не указан)', M['trk_std']])
        fm = mk.get('_fldm') or {}
        if not (acc or sec or trk) and (fm.get('Access') or fm.get('Tracker')):
            ru_a = {'Unlocked': 'двери открыты', 'Locked': 'заперта (Slim Jim или стекло)', 'Key Cloner': 'нужен Key Cloner'}
            ru_t = {'None': 'без трекера', 'Standard': 'жёлтый трекер', 'Advanced': 'красный трекер'}
            parts = [ru_a[fm['Access']]] if fm.get('Access') in ru_a else []
            parts += [ru_t[fm['Tracker']]] if fm.get('Tracker') in ru_t else []
            col = 'r' if fm.get('Access') == 'Key Cloner' or fm.get('Tracker') == 'Advanced' else 'y' if fm.get('Access') == 'Locked' or fm.get('Tracker') == 'Standard' else 'g'
            q.append(['tracker' if fm.get('Tracker') else 'lock', col, 'У базовой модели: ' + ', '.join(parts), M['model_level']])
        elif not (acc or sec or trk):
            q.append(['help', 'd', 'Замок и трекер не указаны', M['trk_unknown']])
        elif acc == 'Unlocked' and sec in ('None', 'Deactivated') and trk == 'None':
            summary = 'Полностью открыта: ни замка, ни сигнализации, ни трекера.'
        elif acc and trk:
            summary = {'Unlocked': 'Двери открыты', 'Locked': 'Заперта', 'Key Cloner': 'Нужен клонер ключей'}[acc] + ', ' + \
                {'None': 'трекера нет', 'Standard': 'жёлтый трекер', 'Advanced': 'красный трекер', 'Tracker': 'есть трекер'}[trk] + '.'
        if fld.get('Cost to Register') and '?' not in fld['Cost to Register']:
            q.append(['cash', 'b', 'Регистрация: ' + fld['Cost to Register'].strip(), M['register']])
        if c == 'veh_randy':
            q.append(['handshake', 'b', 'Заказ скупщика', M['randy']])
        elif c == 'veh_moses':
            q.append(['handshake', 'b', 'Берёт Мозес', M['moses']])
    elif c == 'weapon':
        q.append(['star4', 'y', 'Уникальный вариант (золотой значок)', M['unique_weapon']])
        if 'магазин' in (mk.get('sub') or '') or fd.get('Как получить'):
            q.append(['cash', 'b', 'Продаётся в магазине', 'Купить можно только в этой оружейной.'])
        if mk.get('_gang'):
            sec = mk.get('_sec') or ''
            q.append(['shield', SEC_C.get(sec, 'y'), 'Внутри точки банды' + (f' — охрана {SEC_RU[sec]}' if sec in SEC_RU else ''), M['gang_item']])
        code = fd.get('Коды') or fd.get('Код')
        if code:
            q.append(['dialpad', 'b', 'Нужен код: ' + code, ''])
        if fd.get('Можно пропустить'):
            q.append(['alert', 'r', 'Можно пропустить навсегда', 'Доступно только во время сюжетной миссии.'])
    elif c == 'wpickup':
        q.append(['hand', 'g', 'Просто подобрать', 'Обычное оружие лежит в открытом доступе.'])
    elif c == 'valuable':
        q.append(['hand', 'y', 'Забрать на месте', 'Часы и украшения продаются скупщикам.'])
        if mk.get('_sec') in SEC_RU:
            q.append(['shield', SEC_C[mk['_sec']], 'Охрана: ' + SEC_RU[mk['_sec']], M['gang_item']])
    elif c == 'safe':
        code = fd.get('Код') or fd.get('Код сейфа') or fd.get('Коды')
        if code:
            q.append(['dialpad', 'g', 'Код: ' + code, 'Введите код на панели сейфа.'])
        else:
            q.append(['safe', 'y', 'Нужен код или взрывчатка', M['safe']])
    elif c == 'scoop':
        q.append(['saw', 'y', 'Нужен Cut-Off Tool', M['scoop']])
    elif c == 'loot':
        q.append(['hand', 'g', 'Открыть ящик', M['loot']])
    elif c == 'atmtow':
        q.append(['tow', 'y', 'Нужен эвакуатор или лебёдка', M['atm_tow']])
    elif c in ('bank', 'bigbank', 'jewelry', 'payday', 'pawn', 'store', 'fastfood', 'liquor', 'gang'):
        sec = fld.get('Security', '').strip() or (mk.get('_omfd') or {}).get('Security', '')
        if sec in SEC_RU:
            q.append(['shield', SEC_C[sec], 'Охрана: ' + SEC_RU[sec], ''])
        if fd.get('Добыча'):
            q.append(['cash', 'b', 'Добыча: ' + fd['Добыча'], ''])
        if c == 'bigbank':
            q.append(['vault', 'r', 'Хранилище — поздняя игра', M['vault']])
        else:
            q.append(['clock', 'b', 'Когда доступно', M['kitty' if 'Kitty Litter' in (mk.get('sub') or '') else ROB_NOTE[c]]])
        if c == 'gang' and fd.get('Ключевые ценности'):
            q.append(['gem', 'b', 'Ключевые ценности', fd['Ключевые ценности']])
    elif c == 'card':
        q.append(['hand', 'g', 'Подобрать на месте', M['card']])
    elif c in ('magazine', 'book', 'meteorite', 'treasure'):
        q.append(['hand', 'g', 'Подобрать на месте', M[c]])
    elif c == 'package':
        q.append(['hand', 'g', 'Подобрать на месте', M['pickup']])
    elif c == 'playlist':
        q.append(['scan', 'b', 'Скан постера в WAiNK', M['playlist']])
    elif c in ('waink_l', 'waink_c', 'waink_s'):
        q.append(['scan', 'b', 'Скан в приложении WAiNK', M['waink']])
    elif c == 'mural':
        q.append(['camera', 'b', 'Фото с отмеченной точки', M['mural']])
    elif c == 'stunt':
        q.append(['car', 'b', 'Нужен быстрый транспорт', M['stunt']])
    elif c == 'basejump':
        q.append(['parachute', 'b', 'Нужен парашют', M['basejump']])
    elif c == 'parachute':
        q.append(['hand', 'g', 'Взять парашют', 'Здесь лежит парашют.'])
    elif c == 'knife':
        q.append(['plane', 'b', 'Нужен самолёт', M['knife']])
    elif c == 'bridge':
        q.append(['plane', 'b', 'Нужен летательный аппарат', M['bridge']])
    elif c == 'garage_buy':
        q.append(['cash', 'b', 'Цена: ' + (fd.get('Цена') or 'см. в приложении'), M['garage']])
    elif c == 'race':
        if fd.get('Взнос'):
            q.append(['cash', 'b', 'Взнос: ' + fd['Взнос'], ''])
        if fd.get('Рейтинг'):
            q.append(['star', 'b', 'Рейтинг авто: ' + fd['Рейтинг'], ''])
        q.append(['clock', 'b', 'Когда доступно', M['race']])
    elif c == 'range':
        q.append(['cash', 'b', 'Пропуск и аренда', M['range']])
    elif c == 'fishing':
        q.append(['fish', 'b', 'Нужна удочка', M['fishing']])
    elif c == 'meditation':
        q.append(['meditation', 'b', 'За обоих героев', M['meditation']])
    elif c == 'event':
        q.append(['dice', 'b', 'Случайное событие', M['event']])
    elif c == 'glitch':
        st = mk.get('_gst')
        q.append(['bug', 'g' if st == 'working' else 'y', 'Баг пока работает' if st == 'working' else 'Статус неясен', M['glitch']])
    elif c == 'safehouse':
        q.append(['homelock', 'b', 'Открывается по сюжету', M['safehouse']])
    return q, summary


# ----------------------------------------------------------------------------- finish
allm = markers + ign_markers + derived + om_markers + missions_out + final_extras + glitch_markers
catset = {c[0] for c in CATS}
VAGUE_W = {'car', 'cars', 'helicopter', 'knife', 'truck', 'boat', 'plane', 'bike', 'van', 'sports', 'jet', 'jets', 'speedboat',
           'hatchback', 'airboat', 'pistol', 'rifle', 'shotgun', 'sniper', 'machete', 'bat', 'buggy', 'kayak'}
GENERIC_W = {'gt', 'rs', 'ff', 'ii', 'iii', 'classic', 'custom', 'sport', 'super', 'turbo', 'edition', 'ultimate', 'the'}


def model_keys(name):
    n = re.sub(r'\(.*?\)|"[^"]*"', ' ', name)
    w = [x.lower() for x in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", n) if x.lower() not in GENERIC_W]
    return (w[-2:][::-1] + [''])[:2] if w else ['', '']


def name_tokens(name):
    t = ' '.join(re.findall(r'[a-z0-9]+', re.sub(r'\(.*?\)', ' ', name).lower().replace("'", ''))).replace('st d', 'std')
    return [x for x in t.split() if not re.fullmatch(r'\d{2,4}', x)]


OBJ = {'veh': VEHS, 'weapon': ('weapon',)}
n_same = 0
for fam in OBJ.values():
    pool = [q for q in allm if q['c'] in fam]
    donors = collections.defaultdict(list)
    for q in pool:
        if q.get('img'):
            donors[model_keys(q['n'])[0]].append(q)
    for q in pool:
        if q.get('img') or q.get('p'):
            continue
        k1, k2 = model_keys(q['n'])
        cands = donors.get(k1) or (donors.get(k2) if k2 and fam is VEHS and len(k2) > 3 else None)
        if not cands and fam is VEHS:
            # plain base model ("Lure Predator L35P") next to a named one-off of it ("Lure Predator Cold Case L35P")
            mine = set(name_tokens(q['n']))
            sub = [d for d in pool if d.get('img') and len(mine) >= 3 and mine <= set(name_tokens(d['n']))]
            if sub:
                q['mp'] = {'u': sub[0]['img']['u'], 'n': sub[0]['n']}
                n_same += 1
                continue
        if not cands or not k1:
            continue
        make = norm(q['n']).split()[:1]
        same_make = [d for d in cands if norm(d['n']).split()[:1] == make]
        if (k1 in VAGUE_W or not donors.get(k1)) and not same_make:
            continue        # "helicopter", "car", "knife"… say nothing about the model: only trust them within one make
        d = (same_make or cands)[0]
        q['mp'] = {'u': d['img']['u'], 'n': d['n']}
        n_same += 1
print('objects given a photo of the same model:', n_same)
# official Rockstar promo shots / gameplay frames of the base model, for vehicles that still have no picture
MODEL_IMG = {k[:-4]: 'models/' + k for k in sorted(os.listdir(os.path.join(args.docs, 'models')))} if os.path.isdir(os.path.join(args.docs, 'models')) else {}
MODEL_IMG['stainer'] = MODEL_IMG.get('stanier')
n_off = 0
for q in allm:
    if q['c'] in VEHS and not (q.get('img') or q.get('p') or q.get('mp')):
        tk = set(norm(q['n']).split())
        hit = next((k for k in MODEL_IMG if k in tk and MODEL_IMG[k]), None)
        if hit:
            q['mp'] = {'u': MODEL_IMG[hit], 'n': '', 'off': 1}
            n_off += 1
print('vehicles given an official shot of the model:', n_off)
# cards that still have no picture get the name of the base model: the page looks its picture up in the GTA wikis
WQ_MAKES = {'annis', 'bf', 'benefactor', 'bottcher', 'bravado', 'buckingham', 'canis', 'camus', 'declasse', 'gallivanter', 'grotti', 'hvy', 'hauners',
            'karin', 'lapwing', 'lure', 'maibatsu', 'mammoth', 'mer-can', 'nagasaki', 'ocelot', 'pegassi', 'reynolds', 'schyster', 'taci', 'vapid',
            'western', 'albany', 'pfister', 'invetero', 'truffade', 'progen', 'piccia', 'sirius', 'shitzu', 'lcc', 'airgator', 'willard', 'emperor',
            'dundreary', 'imponte', 'obey', 'enus', 'dewbauchee', 'coil', 'cheval', 'brute', 'walter', 'granforma', 'principe', 'ascot', 'lampadati'}
WQ_VAGUE = {'helicopter', 'helicopters', 'tanks', 'tank', 'truck', 'speedboat', 'hatchback', 'car', 'cars', 'jets', 'boat', 'plane', 'seaplane',
            'buggy', 'lowrider', 'bike', 'van', 'utv', 'yacht'}
WQ_KEEP = {'300-h', '015a'}
WQ_TRIM = {'st-d', 'gt', 'rs', 'ii', 'iii', 'ff', 'std'}
WQ_FIX = {'carbos': 'Carbon RS', 'lander': 'Waste Lander', 'stainer': 'Stanier'}
WQ_WTYPE = r'(small game rifle|assault rifle|sniper rifle|heavy smg|smg|shotgun|pistol|revolver|rifle|mcd)'
WQ_WGEN = {'rocket launcher': 'Rocket Launcher', 'sticky bomb': 'Sticky Bomb', 'frag grenade': 'Grenade', 'flare gun': 'Flare Gun',
           'pump shotgun': 'Pump Shotgun', 'sniper rifle': 'Sniper Rifle', 'molotov': 'Molotov Cocktail', '.50 pistol': 'Pistol .50',
           'body armor': 'Body Armor', 'baseball bat': 'Baseball Bat', 'machete': 'Machete', 'crowbar': 'Crowbar',
           'grenade launcher': 'Grenade Launcher', 'laird 350': 'Laird 350'}
WQ_WBAD = {'gold', 'hobo', 'schafter', 'the', 'import', 'house', "hunter's", "russo's"}


def wiki_query(mk):
    name = re.sub(r'\(.*?\)|"[^"]*"', ' ', mk['n']).strip()
    if not name or re.search(r'[А-Яа-яЁё]', name):
        return None
    if mk['c'] in VEHS:
        if re.search(r'kit car', name, re.I):
            return 'Kit Car'
        if re.search(r'\bpredator\b', name, re.I):
            return 'Predator'
        w = [x for x in re.findall(r"[A-Za-z0-9&\-]+", name.replace("'", '')) if not re.fullmatch(r'\d{2,4}s?', x)]
        if w and w[0].lower() in WQ_MAKES:
            w = w[1:]
        while len(w) > 1 and w[-1].lower() not in WQ_KEEP and (re.search(r'\d', w[-1]) or w[-1].lower() in WQ_TRIM):
            w.pop()
        if not w or w[-1].lower() in WQ_VAGUE or w[-1].lower() in WQ_MAKES or len(w[-1]) < 3:
            return None
        return WQ_FIX.get(w[-1].lower(), w[-1])
    low = name.lower()
    for k, v in WQ_WGEN.items():
        if low.startswith(k):
            return v
    w = re.sub(r'\s+' + WQ_WTYPE + r'\s*$', '', name, flags=re.I).split()
    if not w:
        return None
    q = w[-1] if w[-1] in ('1922', '556') else ' '.join(w[-2:]) if re.fullmatch(r'\.?\d+', w[-1]) and len(w) > 1 else w[-1]
    return None if q.lower() in WQ_WBAD or len(q) < 3 else q


n_wq = 0
for q in allm:
    if (q['c'] in VEHS and q['c'] != 'veh_lux' or q['c'] in ('weapon', 'wpickup')) and not (q.get('img') or q.get('p') or q.get('mp')):
        wq = wiki_query(q)
        if wq:
            q['wq'] = wq
            n_wq += 1
print('cards that look the model picture up in the GTA wikis:', n_wq)
out, en_left = [], []
for mk in allm:
    assert mk['c'] in catset, mk['c']
    if not (-16000 < mk['x'] < 16000 and -16000 < mk['y'] < 16000):
        continue
    if not mk['id'].startswith('L'):
        if not mk.get('a'):
            mk['a'] = area_of(mk['x'], mk['y'])
        if not mk.get('p') and not mk.get('img') and mk['c'] not in VEHS and mk['c'] not in ('weapon', 'wpickup', 'valuable'):
            np_ = near_photo(mk['x'], mk['y'])
            if np_:
                mk['np'] = np_
        q, summary = requirements(mk)
        if q:
            mk['q'] = q
        if summary:
            mk['qs'] = summary
        if mk['c'].startswith('veh_'):
            ic = veh_icon(mk['n'], (mk.get('_fld') or {}).get('Type', '').strip())
            if ic != 'car':
                mk['ic'] = ic
        elif mk['c'] in ('weapon', 'wpickup'):
            ic = weapon_icon(mk['n'], dict(mk.get('f') or []).get('Класс', ''))
            if ic != 'gun':
                mk['ic'] = ic
        if mk.get('_en') and mk.get('t'):
            en_left.append({'id': mk.get('_om') or mk['id'], 'type': mk['c'], 'name': mk['n'], 'text': mk['t']})
            mk['en'] = 1
    for k in [k for k in mk if k.startswith('_')]:
        del mk[k]
    for k in [k for k, v in mk.items() if v in (None, '', [])]:
        del mk[k]
    out.append(mk)

counts = collections.Counter(m['c'] for m in out)
cats = [{'id': c[0], 'g': c[1], 'n': c[2], 'i': c[3], 'on': c[4], 'dr': c[5], 'count': counts.get(c[0], 0)} for c in CATS if counts.get(c[0], 0)]
unplaced = []
if os.path.exists(args.unplaced) and not args.no_extras:
    unplaced = json.load(open(args.unplaced, encoding='utf8'))
    cs = os.path.join(HERE, 'extras_cars_skipped.json')
    if os.path.exists(cs) and not args.no_cars:
        seen_n = {u['n'] for u in unplaced}
        unplaced += [u for u in json.load(open(cs, encoding='utf8')) if u['n'] not in seen_n]
data = {
    'generated': time.strftime('%Y-%m-%d'),
    'groups': [{'id': g[0], 'n': g[1]} for g in GROUPS if any(c['g'] == g[0] for c in cats)],
    'cats': cats, 'sources': SOURCES, 'labels': labels,
    'unplaced': unplaced + glitch_unplaced,
    'live': {'url': OM_BASE + 'data/locations.json', 'base': OM_BASE, 'ids': om_ids, 'types': om_types},
    'markers': out,
}
os.makedirs(os.path.join(args.docs, 'data'), exist_ok=True)
dst = os.path.join(args.docs, 'data', 'markers.json')
json.dump(data, open(dst, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
json.dump(en_left, open(os.path.join(HERE, 'untranslated.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
print('markers:', len(out), 'size: %.2f MB' % (os.path.getsize(dst) / 1e6), '| English-only hints left:', len(en_left))
print('verification:', sorted(collections.Counter(m['v'] for m in out).items()))
print('own photo:', sum(1 for m in out if m.get('p')), 'screenshot:', sum(1 for m in out if m.get('img')), 'same-model photo:', sum(1 for m in out if m.get('mp')), 'nearby photo:', sum(1 for m in out if m.get('np')))
vv = [m for m in out if m['c'] in VEHS]
print('vehicles:', len(vv), 'own photo', sum(1 for m in vv if m.get('img') or m.get('p')), 'same model', sum(1 for m in vv if m.get('mp')), 'none', sum(1 for m in vv if not (m.get('img') or m.get('p') or m.get('mp'))))
print(' | '.join(f"{c['id']} {c['count']}" for c in cats))
