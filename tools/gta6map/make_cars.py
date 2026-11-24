#!/usr/bin/env python3
"""Turn the vehicle research (research/collector_cars.json, research/car_spots.json, research/vehicle_locks.json)
into extras_cars.json for build_data.py.

Guides give no coordinates, so each car is anchored to a place that is already on the map (same building,
business or street) or, failing that, to its district (flagged approximate). Only finds that at least two
independent sources agree on are pinned; the rest go to extras_cars_skipped.json.

Usage: build markers.json without car extras first:  build_data.py --no-cars ; make_cars.py ; build_data.py
"""
import json, math, os, re, unicodedata
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, '..', '..', 'docs', 'data', 'markers.json'), encoding='utf8'))
MK = D['markers']
VEH = [m for m in MK if m['c'].startswith('veh_')]


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', s.lower().replace("'", '')).strip()


def links(urls, n=4):
    out, seen = [], set()
    for u in urls or []:
        host = urlparse(u).netloc.replace('www.', '')
        if host and host not in seen:
            seen.add(host); out.append([host, u])
        if len(out) >= n:
            break
    return out


# ---- gazetteer of named places already on the map
STRIP = r"\s+(base jump|knife flight|stunt jump|bridge|main bar|bar|helipad|food store|gas|big bank|bank)$"
PRE = r"^(safe|pool|office safe|garage safe|locked safe|pay n spray|top fun drones|opponent pool)\s+"
LABELS = sorted(D['labels'], key=lambda q: (-q['k'], q['w']))
LABELSET = {norm(l['n']) for l in LABELS}
GENERIC = {'parking lot', 'radio tower', 'main gate', 'car park', 'ammu nation', 'vice city', 'ocean beach', 'key lento',
           'port gellhorn', 'gas station', 'police station', 'fire station', 'the y', 'xero gas station', 'xero gas',
           'scoop shipping container', 'scoop container', 'construction site', 'peninsula', 'leonida keys', 'saint attaway islands',
           'illegal goods store', 'grassrivers cafe deli', 'warehouse', 'containers', 'hangar', 'airstrip', 'garage', 'marina'}
gaz = {}
for m in MK:
    if m['c'] in ('atm', 'atmtow', 'charger', 'bus', 'hoop', 'fishing', 'mission', 'drone', 'event', 'loot', 'card', 'streetart') \
            or m['c'].startswith('veh_') or m['n'].startswith(('Прототип', 'Объект')):
        continue
    names = {norm(re.sub(r'\(.*?\)', '', m['n']))}
    for part in re.split(r'\s+[-–]\s+', m['n']):
        names.add(norm(part))
    for n in list(names):
        n2 = re.sub(STRIP, '', re.sub(PRE, '', n))
        names.add(n2)
    for n in names:
        if len(n) >= 7 and n not in LABELSET and n not in GENERIC and (len(n.split()) >= 2 or len(n) >= 9):
            gaz.setdefault(n, m)


def find_place(text):
    t = ' ' + norm(text) + ' '
    best = None
    for n, m in gaz.items():
        if ' ' + n + ' ' in t and (best is None or len(n) > len(best[0])):
            best = (n, m)
    return best[1] if best else None


def find_area(text):
    t = ' ' + norm(text) + ' '
    for lb in LABELS:
        if not lb['n'].endswith('County') and ' ' + norm(lb['n']) + ' ' in t:
            return lb
    return None


def at(x, y, where, ap=0):
    return {'x': x, 'y': y, 'where': where, 'ap': ap}


def A(needle, ap=0, dx=0, dy=0, where=None):
    for m in MK:
        if needle.lower() in m['n'].lower():
            return {'x': m['x'] + dx, 'y': m['y'] + dy, 'where': where or m['n'], 'ap': ap}
    raise KeyError(needle)


def MID(name):
    return next(m['id'] for m in VEH if norm(m['n']) == norm(name))


def MG(name, where=''):
    m = next(m for m in VEH if norm(m['n']) == norm(name))
    return {'merge': m['id'], 'x': m['x'], 'y': m['y'], 'where': where or m.get('a', ''), 'ap': 0}


# hand anchors: ('c', index) = collector_cars.json, ('s', index) = car_spots.json; None = cannot be placed
MAN = {
    ('c', 5): {'x': 1731, 'y': 740, 'where': 'многоэтажная парковка на Fig Street, Ocean Beach', 'ap': 1, 'nomerge': 1},
    ('c', 7): at(1700, 1300, 'у магазина BITE на Atlantic Ave, севернее Ocean Beach', 1),
    ('c', 9): A('Bravado Banshee', where='Sweetbay Inn, East Buckley Dr, Capri') if False else None,
    ('c', 15): at(-7150, 620, 'богатые дома на севере Capri', 1), ('c', 16): at(-7180, 560, 'богатые дома на севере Capri', 1),
    ('c', 19): at(-7100, 480, 'общественные парковки на севере Capri', 1),
    ('c', 21): at(794, 464, 'у домов на Starfish Island', 1),
    ('c', 24): A('Delamore Bridge', ap=1, where='особняк на Delamore Drive, Leaf Links'),
    ('c', 62): at(430, -420, 'контейнер в Port Vice City', 1),
    ('s', 11): at(1700, -1400, 'парковка за Dalton Island Club', 1),
    ('s', 19): at(520, 2640, 'причалы Leaf Links Country Club', 1),
    ('s', 23): at(-7120, 540, 'богатый район на севере Capri', 1),
    ('s', 25): {'x': 1731, 'y': 740, 'where': 'многоэтажная парковка на Fig Street, Ocean Beach', 'ap': 1, 'nomerge': 1},
    ('s', 27): A('Shore Dr - A', ap=1, where='парковка у пляжа вдоль Shore Drive'),
    ('s', 43): None, ('s', 45): None, ('s', 36): None, ('s', 35): None, ('s', 18): None,
    ('c', 12): {'merge': 'o-standout-vehicle-224', 'x': 455, 'y': 1375, 'where': 'Vespucci Island', 'ap': 0},
    ('s', 9): {'merge': 'o-standout-vehicle-224', 'x': 455, 'y': 1375, 'where': 'Vespucci Island', 'ap': 0},
    ('s', 1): {'merge': 'o-standout-vehicle-101', 'x': 899, 'y': 643, 'where': 'Starfish Island', 'ap': 0},
    ('c', 13): A('Serena - Gold', where='вилла на Palladia Ln, Peacock Estates'),
    ('s', 21): A('Serena - Gold', where='вилла на Palladia Ln, Peacock Estates'),
    ('c', 59): A('Declasse Caliente Picador', where='контейнерная площадка Breakwater Quarry'),
    ('c', 60): A('Gellhorn Raceway - Introduction', ap=1, where='огороженная площадка у северного края Gellhorn Raceway'),
    ('c', 54): A('Status Auto Resort', where='Status Auto Imports, Bayside'),
    ('s', 34): A('Status Auto Resort', where='автосалон Status Auto Imports'),
    ('s', 49): A('Southwind Helipad', ap=1, where='причал у Sherwin Boatworks, Southwind'),
    ('c', 38): A('Leonida State Prison', ap=1, where='ферма к северу от Leonida State Prison'),
    ('c', 4): at(-560, 1290, 'NE 3rd St, Vice City', 1), ('s', 38): at(-560, 1290, 'NE 3rd St, Vice City', 1),
    ('c', 2): MG('Pegassi Vitello'), ('s', 47): MG('Pegassi Vitello'),
    ('c', 66): MG('Maibatsu Penumbra FF (Paul Walker tribute)'), ('s', 8): MG('Maibatsu Penumbra FF (Paul Walker tribute)'),
    ('c', 29): MG("BF '77 Bandito"), ('c', 58): MG('Declasse Caliente Picador'),
    ('c', 48): MG("Vapid Wyman's '67 Dominator Buggy"), ('c', 52): MG('Annis Venturas BLVD Elegy'),
    ('c', 32): A("Sarena's Bargain Store", ap=1, where="трейлерный парк на Tanglewood Lane, севернее Sarena's Bargain Store"),
    ('c', 33): A('Stash House', ap=1, where='дом на Gellhorn Ave напротив Stash House'),
    ('c', 45): A('Guns Aplenty!', ap=1, where='за автомастерской Donnies Auto Repair, Watson Bay'),
    ('c', 46): A('Casanova Island Bridge', ap=1, where='подъезд к особняку на Casanova Island'),
    ('c', 39): A('Wyatt Motors', ap=1, where='гараж у заправки Xero рядом с Wyatt Motors, Ambrosia'),
    ('c', 8): at(-1406, 2925, 'особняк в Belville', 1),
}
R_LIST = {'randy': ('veh_randy', 'Заказ Рэнди'), 'moses': ('veh_moses', 'Заказ Мозеса'), 'wyman': ('veh_randy', 'Заказ Уаймана (остов для восстановления)'),
          'reward': ('veh_standout', 'Бесплатная / наградная машина'), 'container': ('veh_standout', 'Машина в контейнере'),
          'other': ('veh_standout', 'Бесплатная редкая машина')}
ATTR = {'access': ('Access', {'Unlocked', 'Locked', 'Key Cloner'}), 'security': ('Security', {'None', 'Alarmed', 'Deactivated'}),
        'tracker': ('Tracker', {'None', 'Standard', 'Advanced'})}


def fld_of(it):
    f = {}
    for k, (label, ok) in ATTR.items():
        v = it.get(k)
        if isinstance(v, str) and v.strip() in ok:
            f[label] = v.strip()
    return f


def tokens(name, keep_paren=True):
    n = name if keep_paren else re.sub(r'\(.*?\)', ' ', name)
    n = re.sub(r'—.*$', ' ', n)
    return [t for t in norm(n).split() if not re.fullmatch(r'\d{2,4}s?', t) and t not in ('wreck', 'the', 'motorcycle')]


def identity(research, marker):
    """0 = different cars, 2 = same name, 1 = marker name is contained in the research name (incl. its notes in brackets)"""
    rb, rf, mt = tokens(research, False), set(tokens(research)), tokens(marker)
    if not rb or not mt:
        return 0
    if set(rb) == set(tokens(marker, False)) or set(rb) == set(mt):
        return 2
    mb = tokens(marker, False)
    if len(rb) >= 3 and len(mb) >= 3 and rb[1:] == mb[1:]:
        return 2          # same variant and model, make spelled differently
    return 1 if set(mt) <= rf and mt[-1] in rf else 0


created, used = [], {}


def existing(name, p):
    if not p:
        return None
    if p.get('merge'):
        return next((m for m in VEH if m['id'] == p['merge']), None)
    nomerge = p.get('nomerge')
    for (cn, cx, cy, ce) in created:
        idn = max(identity(name, cn), identity(cn, name))
        dist = math.hypot(cx - p['x'], cy - p['y'])
        if (idn == 2 and dist <= 600) or (idn >= 1 and dist <= 250) or (idn >= 1 and len(tokens(cn, False)) >= 2 and 'wreck' not in cn and dist <= 3000):
            return ce
    if nomerge:
        return None
    c = [(identity(name, m['n']), math.hypot(m['x'] - p['x'], m['y'] - p['y']), m) for m in VEH]
    c = [q for q in c if q[0]]
    exact = [q for q in c if q[0] == 2]
    if len(exact) == 1 and (exact[0][1] <= 4500 or len(tokens(name, False)) >= 3):
        prev = used.get(exact[0][2]['id'])
        if not prev or math.hypot(prev[0] - p['x'], prev[1] - p['y']) <= 300:
            used[exact[0][2]['id']] = (p['x'], p['y'])
            return exact[0][2]
        return None
    rad = 1600 if p['ap'] else 700
    c = [q for q in c if q[1] <= rad]
    if not c:
        return None
    best = min(c, key=lambda q: (-q[0], q[1]))[2]
    prev = used.get(best['id'])
    if prev and math.hypot(prev[0] - p['x'], prev[1] - p['y']) > 300:
        return None          # same model wanted at a clearly different place: a separate spawn
    used[best['id']] = (p['x'], p['y'])
    return best


ALIAS = [('status auto', lambda: A('Status Auto Resort', where='автосалон Status Auto Imports, Bayside')),
         ('sherwin boatworks', lambda: A('Southwind Helipad', ap=1, where='у Sherwin Boatworks, Southwind')),
         ('fig street', lambda: at(1731, 740, 'многоэтажная парковка на Fig Street, Ocean Beach', 1)),
         ('dalton island club', lambda: at(1700, -1400, 'парковка за Dalton Island Club', 1)),
         ('apollo aggregates', lambda: A('Vapid Rumpo', where='склад Apollo Aggregates')),
         ('crosstown police', lambda: A("Pegassi '96 Infernus", where='паркинг полиции в Crosstown')),
         ('boundary road', lambda: at(-3300, -4700, 'взлётная полоса у Boundary Road, Mariana County', 1))]
NEAR = r'(from|near|north of|south of|east of|west of|north west of|south west of|north east of|south east of|opposite|behind|next to|beside|outside|across from|by the)\s+(the\s+)?'


def place(kind, i, text, area):
    if (kind, i) in MAN:
        return MAN[(kind, i)]
    low = norm(text)
    for kw, fn in ALIAS:
        if kw in low:
            return fn()
    m = find_place(text)
    if m:
        key = norm(re.sub(r'\(.*?\)', '', m['n']))
        vague = bool(re.search(NEAR + re.escape(key.split()[0]), low))
        return {'x': m['x'], 'y': m['y'], 'where': ('рядом с ' if vague else '') + m['n'], 'ap': 1 if vague else 0}
    lb = find_area(area) or find_area(text)
    if lb:
        return {'x': lb['x'], 'y': lb['y'], 'where': 'район ' + lb['n'], 'ap': 1}
    return None


extras, skipped, report = [], [], []
seq = 0


def emit(kind, i, name, cat, sub, it, p, verified, r=4, extra_facts=()):
    global seq
    fld = fld_of(it)
    ex = existing(name, p)
    u = links(it.get('sources'))
    if ex is not None and 'merge_any' not in ex and ex.get('force_new'):
        ex.setdefault('u', []).extend([q for q in u if q not in ex['u']][:2])     # same car reported twice in the research
        report.append(f"dup   {name[:34]:34s} (already added in this run)")
        return
    if ex:
        e = {'merge_any': ex['id'], 'n': name, 'c': ex['c'], 'u': u, 'v': 3 if verified else 2, 'fld': fld, 'f': []}
        if it.get('conditions') and len(str(it['conditions'])) < 5:
            pass
        extras.append(e)
        report.append(f"merge {name[:34]:34s} -> {ex['n'][:34]} [{ex['id']}]")
        return
    if not verified or not p:
        skipped.append({'k': 'vehicle', 'n': name, 't': it.get('desc_ru'), 'u': u[:2]})
        report.append(f"skip  {name[:34]:34s} ({'no place' if not p else 'one source'})")
        return
    seq += 1
    ang = seq * 2.4
    facts = [['Привязка на карте', p['where']]] + list(extra_facts)
    if it.get('conflict'):
        facts.append(['Расхождение в гайдах', 'встречаются и другие места появления — см. источники'])
    e = {'id': f'xc{kind}{i}-{seq}', 'n': re.sub(r'\s*(—|\().*$', '', name).strip() + (' (остов)' if 'wreck' in name else ''), 'c': cat, 'r': r, 'sub': sub,
         'x': round(p['x'] + 13 * math.cos(ang)), 'y': round(p['y'] + 13 * math.sin(ang)), 't': it.get('desc_ru'), 'u': u,
         'f': facts, 's': ['web'], 'v': 3, 'fld': fld, 'force_new': 1}
    if p['ap']:
        e['ap'] = 1
    extras.append(e)
    created.append((name, p['x'], p['y'], e))
    report.append(f"new   {name[:34]:34s} @ {p['where'][:40]}{' ~' if p['ap'] else ''}")


# ------------------------------------------------------------------ collector lists
CJ = json.load(open(os.path.join(HERE, 'research', 'collector_cars.json'), encoding='utf8'))['items']
for i, it in enumerate(CJ):
    name = str(it.get('name') or '').strip()
    cat, sub = R_LIST.get(it.get('list'), ('veh_standout', 'Редкая машина'))
    text = f"{it.get('place_detail') or ''} | {it.get('island_or_district') or ''}"
    p = place('c', i, text, str(it.get('island_or_district') or ''))
    facts = []
    if it.get('payout') and len(str(it['payout'])) < 60:
        facts.append(['Выплата', str(it['payout'])])
    emit('c', i, name, cat, sub, it, p, bool(it.get('verified')), r=4 if it.get('list') in ('randy', 'reward') else 3, extra_facts=facts)

# ------------------------------------------------------------------ regional sweeps (same record shape as the collector lists)
for fn in sorted(os.listdir(os.path.join(HERE, 'research'))):
    if not re.match(r'cars_region_\d+\.json$', fn):
        continue
    RJ = json.load(open(os.path.join(HERE, 'research', fn), encoding='utf8')).get('items', [])
    tag = 'r' + re.search(r'\d+', fn).group(0)
    for i, it in enumerate(RJ):
        name = str(it.get('name') or '').strip()
        if not name or re.search(r'not named|not stated|unknown model', name, re.I):
            continue
        text = f"{it.get('place_detail') or ''} | {it.get('island_or_district') or ''}"
        p = place(tag, i, text, str(it.get('island_or_district') or ''))
        emit(tag, i, name, 'veh_standout', 'Редкая машина (по гайдам)', it, p, bool(it.get('verified')), r=3)

# ------------------------------------------------------------------ car spots
SJ = json.load(open(os.path.join(HERE, 'research', 'car_spots.json'), encoding='utf8'))['items']
for i, it in enumerate(SJ):
    vehicles = [str(v) for v in (it.get('vehicles') or [])]
    text = f"{it.get('place_detail') or ''} | {it.get('place_island') or ''}"
    p = place('s', i, text, str(it.get('place_island') or ''))
    named = [v for v in vehicles if not re.search(r'not named|not stated|random|several|luxury|expensive|tuned cars|commercial', v, re.I)]
    kind = str(it.get('kind'))
    if kind == 'fixed_spawn' and named:
        for v in named:
            emit('s', i, re.sub(r'\s+with\s.*$', '', v).strip(), 'veh_standout', 'Редкая машина (по гайдам)', it, p, bool(it.get('verified')))
        continue
    # a place where expensive cars are parked rather than one specific car
    if not it.get('verified') or not p:
        skipped.append({'k': 'vehicle', 'n': 'Дорогие машины: ' + str(it.get('place_island')), 't': it.get('desc_ru'), 'u': links(it.get('sources'), 2)})
        report.append(f"skip  spot {i} {str(it.get('place_island'))[:30]} ({'no place' if not p else 'one source'})")
        continue
    seq += 1
    boats = bool(re.search(r'yacht|boat|watercraft', ' '.join(vehicles), re.I))
    helis = bool(re.search(r'helicopter|plane', ' '.join(vehicles), re.I))
    models = [re.sub(r'\s*\(.*$', '', v).strip() for v in named][:8]
    facts = [['Привязка на карте', p['where']]]
    if models:
        facts.append(['Какие машины видели', ', '.join(models)])
    facts.append(['Тип места', {'parking_lot_random': 'парковка — машины меняются', 'dealership': 'автосалон', 'traffic': 'в потоке и у входов',
                               'mission_only': 'связано с заданием', 'fixed_spawn': 'постоянное место'}.get(kind, kind)])
    e = {'id': f'xl{i}', 'n': 'Дорогие машины: ' + p['where'].replace('район ', ''), 'c': 'veh_lux', 'r': 4,
         'x': round(p['x']), 'y': round(p['y']), 't': it.get('desc_ru'), 'u': links(it.get('sources')), 'f': facts, 's': ['web'], 'v': 3,
         'sub': 'Яхты и катера' if boats else 'Вертолёты и самолёты' if helis else 'Суперкары и люкс', 'force_new': 1,
         'ic': 'boat' if boats else 'heli' if helis else 'supercar'}
    if p['ap']:
        e['ap'] = 1
    extras.append(e)
    report.append(f"lux   spot {i} @ {p['where'][:44]}{' ~' if p['ap'] else ''} : {', '.join(models)[:50]}")

# ------------------------------------------------------------------ lock / tracker facts found for cars already on the map
lp = os.path.join(HERE, 'research', 'vehicle_locks.json')
n_lock = 0
if os.path.exists(lp):
    LJ = json.load(open(lp, encoding='utf8'))
    for v in LJ.get('vehicles', []):
        fld = fld_of(v)
        for k_src, label in (('sell_value', 'Sell Value'), ('register_cost', 'Cost to Register')):
            val = v.get(k_src)
            if isinstance(val, str) and re.search(r'\d', val):
                fld[label] = val if val.startswith('$') else '$' + val
            elif isinstance(val, (int, float)) and val > 0:
                fld[label] = '${:,}'.format(int(val))
        if not fld:
            continue
        targets = [m for m in VEH if norm(m['n']) == norm(v.get('name'))]
        if v.get('area'):
            near = [m for m in targets if norm(v['area']).split()[:1] == norm(m.get('a', '')).split()[:1]]
            targets = near or targets
        key = 'fld' if v.get('basis') == 'exact' else 'fldm'
        for m in targets[:1]:
            extras.append({'merge_any': m['id'], 'n': m['n'], 'c': m['c'], 'u': links(v.get('sources'), 3), 'v': 2, key: fld, 'f': []})
            n_lock += 1
    json.dump(LJ.get('rules', []), open(os.path.join(HERE, 'research', 'vehicle_rules.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)

json.dump(extras, open(os.path.join(HERE, 'extras_cars.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
json.dump(skipped, open(os.path.join(HERE, 'extras_cars_skipped.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('\n'.join(report))
print(f"\ncar extras: {len(extras)} (new {sum(1 for e in extras if 'id' in e)}, merged {sum(1 for e in extras if 'merge_any' in e)}, "
      f"lock facts {n_lock}), skipped {len(skipped)}")
