#!/usr/bin/env python3
"""Turn the web-research lists (tools/gta6map/research/*.json) into map markers.

Text guides give no coordinates, so every item is anchored to a place that already exists
in the map data (same building / operation / store) or, failing that, to its district
(flagged as approximate). Items without a usable location are left out and listed.

Usage: python3 make_extras.py --markers docs/data/markers.json --ign <ign data dir> --out extras.json
(markers.json must be built WITHOUT --extras first)
"""
import argparse, json, math, os, re, sys
from urllib.parse import urlparse

ap = argparse.ArgumentParser()
ap.add_argument('--markers', required=True)
ap.add_argument('--ign', required=True)
ap.add_argument('--out', required=True)
args = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(args.markers, encoding='utf8'))
MK = D['markers']


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower().replace("'", '').replace('’', '')).strip()


STOP = set('the of and a in at on to for near with from by is are an or its it this that inside outside behind next front '
           'store shop house hotel motel garage bank station gas bar club park island key bay beach north south east west '
           'northern southern eastern western county city safe marina airport tower bridge warehouse apartments building '
           'center lake river point side part area road street ave avenue blvd drive illegal operation operations'.split())


def toks(s):
    return {t for t in norm(s).split() if len(t) > 2 and t not in STOP}


# ---- gazetteer: IGN marker names (+ original English location text) and named GTADB landmarks
LABELSET = {norm(l['n']) for l in D['labels']}
gaz = []
s = open(os.path.join(args.ign, 'markers.js'), encoding='utf8').read()
IGN = json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))
ign_loc = {}
for m in IGN:
    loc = re.search(r'\*\*Location:\*\*\s*(.+?)(\n\n|\*\*|$)', m.get('d') or '', re.S)
    ign_loc['i' + str(m['s'])] = loc.group(1).strip() if loc else ''
SKIPC = {'atm', 'atmtow', 'charger', 'bus', 'hoop', 'fishing', 'bridge', 'stunt', 'knife', 'basejump', 'mission', 'drone'}
GENERIC = {'parking lot', 'radio tower', 'main gate', 'ammu nation', 'boardwalk', 'tunnel', 'hospital', 'hangar', 'fence',
           'airfield', 'car park', 'catalan bay', 'randy', 'moses', 'kenton', 'pete', 'crosstown', 'dalton island', 'draper island', 'tequesta'}
for m in MK:
    if m['id'].startswith('i') and m['c'] not in SKIPC:
        n = norm(m['n'])
        gaz.append((n, m, 3))
        for part in re.split(r'\s+[-–]\s*', m['n']):
            if len(norm(part).split()) >= 2 and norm(part) not in LABELSET:
                gaz.append((norm(part), m, 3))
    elif m['id'].startswith('L') and not m['n'].startswith(('Прототип', 'Объект')):
        n = norm(re.sub(r'\([^)]*\)', '', m['n']))
        if len(n.split()) >= 2:
            gaz.append((n, m, 1))
gaz = [g for g in gaz if len(g[0]) >= 6 and g[0] not in GENERIC]
LABELS = sorted(D['labels'], key=lambda q: (-q['k'], q['w']))   # district-level first, most specific first


def find_place(text):
    t = ' ' + norm(text) + ' '
    best = None
    for n, m, w in gaz:
        if ' ' + n + ' ' in t:
            sc = len(n) + w * 4
            if best is None or sc > best[0]:
                best = (sc, m)
    return best[1] if best else None


def find_area(text):
    t = ' ' + norm(text) + ' '
    for lb in LABELS:
        if lb['n'].endswith('County'):
            continue
        if ' ' + norm(lb['n']) + ' ' in t:
            return lb
    return None


def links(urls, n=4):
    out, seen = [], set()
    for u in urls or []:
        try:
            host = urlparse(u).netloc.replace('www.', '')
        except Exception:
            continue
        if not host or host in seen:
            continue
        seen.add(host)
        out.append([host, u])
        if len(out) >= n:
            break
    return out


CLS = [('assault rifle', 'Автомат'), ('sniper', 'Снайперская винтовка'), ('marksman', 'Марксманская винтовка'),
       ('smg', 'Пистолет-пулемёт'), ('lmg', 'Пулемёт'), ('shotgun', 'Дробовик'), ('revolver', 'Револьвер'),
       ('pistol', 'Пистолет'), ('rifle', 'Винтовка'), ('launcher', 'Гранатомёт'), ('knife', 'Нож'), ('bat', 'Бита'),
       ('melee', 'Холодное оружие'), ('thrown', 'Метательное')]


def cls_ru(c):
    c = str(c or '')
    low = c.lower()
    ru = next((r for k, r in CLS if k in low), None)
    var = re.search(r'([A-Z][\w&\-\.\' ]+?)\s+variant', c)
    if not ru:
        return None
    return ru + (' · вариант ' + var.group(1).strip() if var else '')


def codes_ru(c):
    c = str(c or '').strip()
    return c if (c and len(c) <= 60 and re.search(r'\d', c)) else None


def by_text(needle):
    """first IGN marker whose name contains the needle"""
    for m in MK:
        if m['id'].startswith('i') and needle.lower() in m['n'].lower():
            return m
    raise KeyError(needle)


def at(x, y, ap=0, where=None):
    return {'x': x, 'y': y, 'ap': ap, 'where': where}


def A(needle, ap=0, dx=0, dy=0):
    m = by_text(needle)
    return {'x': m['x'] + dx, 'y': m['y'] + dy, 'ap': ap, 'where': m['n']}


# ---- hand anchors (file, index) -> placement; None = no usable location, leave out
MAN = {
    ('weapons', 0): A("Dr Sheehan's Airboat"),                  # abandoned crab research outpost, Pelican Valley
    ('weapons', 1): A('Griffin Villa Range', ap=1, dx=-140, dy=-140),
    ('weapons', 15): at(-5702, -1628, 1, 'секретный бункер в болотах на северо-западе Grassrivers (район Big Pine)'),
    ('weapons', 42): at(-5690, -1640, 1, 'секретный бункер в болотах на северо-западе Grassrivers (район Big Pine)'),
    ('weapons', 43): at(207, 5281, 0, 'Presidential Bunker, Sharktooth Island'),
    ('weapons', 45): None, ('weapons', 46): None, ('weapons', 47): None, ('weapons', 48): None,
    ('weapons', 49): A("Donnie's Trailer", ap=1),
    ('weapons', 53): None, ('weapons', 68): None, ('weapons', 71): None, ('weapons', 80): None, ('weapons', 92): None,
    ('weapons', 67): A('Woodhatch'),
    ('weapons', 27): at(-6321, -5148, 1, 'Bobcat Bight, северо-запад Bobcat Key'),
    ('secrets', 5): A("Dr Sheehan's Airboat"),
    ('secrets', 10): A('Killtelligence Provisions', ap=1, dy=250),
    ('secrets', 11): None,
    ('secrets', 12): A('Circles of Hell Youga'),
    ('secrets', 13): A('Thrillbilly Mud Club - Air Time', ap=1, dx=-350, dy=350),
    ('secrets', 14): at(-2756, 8831, 0, 'Hyde Island'),
    ('secrets', 15): A('Bluegrass Antenna Mast Base Jump'),
    ('secrets', 20): A('Halloween House'),
    ('secrets', 23): at(-5000, 3800, 1, 'к северо-востоку от Starlet Motel, Frogswater'),
    ('secrets', 24): A("Howe Dairy Farm's Big Udder"),
    ('secrets', 34): None, ('secrets', 4): None,
    ('secrets', 43): A('Mount Kalaga Base Jump'),
    ('secrets', 44): A('Mount Kalaga Base Jump', ap=1, dx=120, dy=-90),
    ('secrets', 45): A('Mount Kalaga Base Jump', ap=1, dx=-110, dy=80),
    ('secrets', 50): A("IAA's Friends of Freedom"),
    ('secrets', 51): at(207, 5281, 0, 'Presidential Bunker, Sharktooth Island'),
    ('secrets', 52): at(-5702, -1628, 1, 'секретный бункер в болотах на северо-западе Grassrivers (район Big Pine)'),
    ('secrets', 58): A('Vapid Rumpo'),
    ('secrets', 67): None, ('secrets', 68): None, ('secrets', 69): None, ('secrets', 72): None,
    ('secrets', 70): A('Abismo Key Carcass', ap=1),
    ('secrets', 73): A('Belpoint Lighthouse', ap=1),
    ('secrets', 87): A('Richardson Jewelry & Diamonds'),
    ('secrets', 89): A('Gellhorn Raceway - Introduction', ap=1),
    ('secrets', 94): None, ('secrets', 95): None,
    ('vehicles', 20): A('Crimson Palms Base Jump', ap=1),
    ('vehicles', 40): None, ('vehicles', 41): None, ('vehicles', 58): None,
    ('weapons', 59): A('Pawn & Gun - Port Gellhorn'),
    ('vehicles', 31): None,   # same car as IGN "Declasse Ghosts Exposed Parkland" (merged by name)
}
R_RAR = {'legendary': 5, 'epic': 4, 'rare': 3}
extras, skipped = [], []
veh = [m for m in MK if m['c'].startswith('veh_')]
wep = [m for m in MK if m['c'] in ('weapon', 'valuable') and m['id'].startswith('k')]


def op_of(m):
    f = dict(m.get('f') or [])
    mm = re.search(r'«(.+?)»', f.get('Где', ''))
    return mm.group(1) if mm else ''


def place(kind, i, it, strong):
    key = (kind, i)
    if key in MAN:
        return MAN[key]
    m = find_place(strong)
    if m:
        vague = m['id'].startswith('L') and norm(m['n']).split()[-1] in ('bay', 'key', 'island', 'lake', 'bight', 'strait', 'river', 'beach')
        return {'x': m['x'], 'y': m['y'], 'ap': 1 if vague else 0, 'where': m['n']}
    area = str(it.get('area') or '')
    lb = find_area(area)
    if lb and re.search(r'\b(north|south|east|west|north-east|north-west|south-east|south-west) of\b|\bnear\b|\boff\b|\boutside\b|\bbetween\b|\baround\b', area.lower()):
        lb = None
    if lb:
        return {'x': lb['x'], 'y': lb['y'], 'ap': 1, 'where': 'район ' + lb['n']}
    return None


# ------------------------------------------------------------------ weapons
W = json.load(open(os.path.join(HERE, 'research', 'weapons.json'), encoding='utf8'))['items']
n_merge = 0
for i, it in enumerate(W):
    name = it['name'].strip()
    if 'ordinary weapon' in str(it.get('rarity')):
        continue
    nt = toks(name) | {t for t in norm(name).split() if re.search(r'\d', t)}
    cands = [m for m in wep if nt and nt <= (toks(m['n']) | set(norm(m['n']).split()))]
    store = 'store-exclusive' in str(it.get('rarity'))
    facts = []
    if cls_ru(it.get('class')):
        facts.append(['Класс', cls_ru(it.get('class'))])
    if store:
        facts.append(['Как получить', 'продаётся только в этом магазине'])
    if it.get('missable'):
        facts.append(['Можно пропустить', 'да — доступно только во время миссии'])
    if codes_ru(it.get('codes')):
        facts.append(['Коды', codes_ru(it.get('codes'))])
    if it.get('conflict'):
        facts.append(['Расхождение в гайдах', 'источники называют разные места — проверьте оба варианта'])
    e = {'n': name, 'c': 'weapon', 'r': 5, 't': it.get('desc_ru'), 'u': links(it.get('sources')), 'f': facts,
         'sub': 'Уникальный вариант оружия' + (' · продаётся в магазине' if store else '')}
    if cands:
        m = cands[0]
        agree = bool(toks(op_of(m)) & toks(str(it.get('landmark')) + ' ' + str(it.get('spot'))))
        e.update({'merge': m['id'], 'v': 3 if agree else 2})
        if not agree:
            e['f'] = facts + [['Расхождение', f"карта IGN относит предмет к операции «{op_of(m)}»"]]
            e['t'] = None
        extras.append(e); n_merge += 1
        continue
    p = place('weapons', i, it, ' | '.join(str(it.get(k) or '') for k in ('landmark', 'spot')))
    if not p:
        skipped.append({'k': 'weapon', 'n': name, 't': it.get('desc_ru'), 'u': links(it.get('sources'), 2)})
        continue
    ang = (i * 2.4) % 6.283
    e.update({'id': f'xw{i}', 'x': round(p['x'] + 11 * math.cos(ang)), 'y': round(p['y'] + 11 * math.sin(ang)),
              'v': (3 if it.get('verified') else 1) if not p['ap'] else (1 if it.get('verified') else 0), 's': ['web']})
    if p['ap']:
        e['ap'] = 1
    if p.get('where'):
        e['f'] = [['Привязка на карте', p['where']]] + facts
    extras.append(e)
print('weapons: merged', n_merge, 'new', sum(1 for e in extras if e.get('id', '').startswith('xw')))

# ------------------------------------------------------------------ vehicles
V = json.load(open(os.path.join(HERE, 'research', 'vehicles.json'), encoding='utf8'))['items']
nm = nn = 0
for i, it in enumerate(V):
    name = it['name'].strip()
    if 'not stated' in name or 'exact' in name:
        skipped.append({'k': 'vehicle', 'n': name, 't': it.get('desc_ru'), 'u': links(it.get('sources'), 2)}); continue
    base = re.sub(r'\(.*?\)', '', name).strip()
    nt = set(norm(base).split())
    loc_text = ' '.join(str(it.get(k) or '') for k in ('landmark', 'spot', 'area'))
    best = None
    for m in veh:
        mt = set(norm(m['n']).split())
        if not (nt <= mt or mt <= nt):
            continue
        sc = len(toks(loc_text) & (toks(ign_loc.get(m['id'], '')) | toks(m.get('a', ''))))
        if best is None or sc > best[0]:
            best = (sc, m)
    u = links(it.get('sources'))
    facts = []
    if it.get('conditions'):
        pass
    if it.get('conflict'):
        facts.append(['Расхождение в гайдах', 'встречаются и другие места появления — см. источники'])
    if best and (best[0] >= 1 or len([m for m in veh if set(norm(m['n']).split()) == nt]) == 1 and best[0] >= 0 and not it.get('landmark')):
        e = {'merge': best[1]['id'], 'n': name, 'c': best[1]['c'], 'u': u, 'v': 3 if best[0] >= 1 else 2, 'f': facts}
        extras.append(e); nm += 1
        continue
    if best and best[0] == 0:
        # same model known to IGN at another place: keep IGN marker, add this as an alternative spawn if it can be placed
        pass
    p = place('vehicles', i, it, ' | '.join(str(it.get(k) or '') for k in ('landmark', 'spot')))
    if not p or (p['ap'] and not it.get('verified')):
        skipped.append({'k': 'vehicle', 'n': name, 't': it.get('desc_ru'), 'u': links(it.get('sources'), 2)}); continue
    r = R_RAR.get(it.get('rarity'), 3)
    f2 = [['Привязка на карте', p['where']]] if p.get('where') else []
    if it.get('guide_label'):
        f2.append(['В гайдах', it['guide_label']])
    e = {'id': f'xv{i}', 'n': name, 'c': 'veh_randy' if 'Randy' in str(it.get('guide_label')) else 'veh_standout', 'r': r,
         'x': round(p['x'] + 12), 'y': round(p['y'] - 12), 't': it.get('desc_ru'), 'u': u, 'f': f2 + facts, 's': ['web'],
         'v': (3 if it.get('verified') else 1) if not p['ap'] else 1, 'force_new': 1,
         'sub': 'По гайдам игроков'}
    if p['ap']:
        e['ap'] = 1
    extras.append(e); nn += 1
print('vehicles: merged', nm, 'new', nn)

# ------------------------------------------------------------------ secrets
S = json.load(open(os.path.join(HERE, 'research', 'secrets.json'), encoding='utf8'))['items']
KIND = {'easter_egg': 'Пасхалка', 'mystery': 'Загадка', 'hidden_place': 'Скрытое место', 'treasure': 'Тайник / клад',
        'code_puzzle': 'Код / головоломка', 'reference': 'Отсылка', 'random_event': 'Случайное событие',
        'leak_confirmed': 'Было в сливе 2022', 'trailer_location': 'Место из трейлера'}
SEC_RU = {
    0: 'Похищение НЛО — начало цепочки «Alien Dreams»', 1: 'Лаборатория пришельцев («Зона 51»)',
    3: 'Скунсовая обезьяна (снежный человек)', 5: 'Гигантский краб-мутант и заброшенная крабовая станция',
    8: 'Маяк St. Lucia: призраки смотрителей, корабль-призрак и Проклятый нож',
    9: 'Отель Marbelle с привидениями (отсылка к Silent Hill) и сейф', 10: 'Ла Йорона — призрак женщины на туманной дороге',
    12: 'Дом «Circles of Hell» — начало битвы с Сатаной', 13: 'Адский костёр и трон', 14: 'Охота на острове Hyde Island',
    15: 'Буквальная пасхалка: гнездо с крашеными яйцами на радиомачте', 16: 'Квартира Декстера Моргана (Trinity Apartments)',
    17: 'Cool Dog — спасение пса на гидроцикле и Собачий остров', 18: 'Яхта Майкла из GTA V',
    20: 'Машина «Охотников за привидениями» — Declasse Ghosts Exposed Parkland', 21: 'Блок Марио и Луиджи («Super Mario Bong»)',
    22: 'Стена «Looney Tunes» — нарисованный тоннель', 23: 'Красный Халк на ферме McKittrick', 24: 'Тутси — говорящая корова',
    26: 'Наклейка Love Fist в мотеле Starlet', 28: 'Книга «Lethal by Design: A Liberty City Memoir»',
    29: 'Вестерн о ковбое из Нью-Остина (отсылка к Red Dead)', 30: 'Дом в Belville с фото из San Andreas и гараж конспиролога',
    35: 'Дом — место преступления в духе «Лица со шрамом»', 42: 'Отель Ocean View — привет из GTA: Vice City',
    43: 'Каменный круг на вершине Mount Kalaga', 44: 'Место падения метеорита у вершины Mount Kalaga',
    46: 'Monument of Leonidan Supremacy — неразгаданный монумент', 50: 'Хосе Бермудес на памятнике Friends of Freedom',
    51: 'Бункер президента на Sharktooth Island', 52: 'Второй президентский бункер у Big Pine',
    54: 'Mile Zero Air Station — закрытая военная база', 57: 'Derelict Spy Vessel — брошенное шпионское судно',
    58: 'Фабрика плюшевых мишек (склад Apollo Aggregates)', 59: 'Разбившийся самолёт, записка пилота и яхта UNDAUNTED',
    61: 'Золотой АК — KZ-59 «La Polilla Negra»', 63: 'Exotic Animals Front — тайник за стеной с попугаем',
    64: 'Сейф в доме Джейсона', 70: 'Затонувший корабль Nuestra Señora de la Ética Laxa', 73: 'Место для дайвинга Belpoint Strait',
    75: 'Сейф в офисе Kingpin Bowling', 76: 'Сейф Brooks Boatworks', 77: 'Сейф мотеля La Cascara',
    78: 'Сейф в офисе Delights Cabaret', 79: 'Коды миссии «Lab Fees»: дверь лаборатории и Brian\'s Lockup',
    80: 'Дверь Janjak\'s Garage', 85: 'Сейф Nova Auto Junkyard', 86: 'Сейф ломбарда Casa de Empeño',
    87: 'Сейф Richardson Jewelry', 88: 'Сейф Donovan Banks & Co.', 92: 'Машина в контейнере: Progen Purple Drank Emerus',
    93: 'Thrillbilly Mud Club — место из трейлера',
}
ICON = {'mystery': 'ghost', 'treasure': 'chest', 'code_puzzle': 'safe'}
ns = 0
for i, it in enumerate(S):
    if it.get('status') in ('debunked', 'unconfirmed'):
        skipped.append({'k': 'fake' if it.get('status') == 'debunked' else 'rumor', 'n': it['name'], 't': it.get('desc_ru'), 'u': links(it.get('sources'), 2)}); continue
    p = place('secrets', i, it, ' | '.join(str(it.get(k) or '') for k in ('landmark', 'spot')))
    if not p or (p['ap'] and not it.get('verified')):
        skipped.append({'k': 'secret', 'n': it['name'], 't': it.get('desc_ru'), 'u': links(it.get('sources'), 2)}); continue
    facts = [['Тип', KIND.get(it.get('kind'), 'Секрет')]]
    if p.get('where'):
        facts.append(['Привязка на карте', p['where']])
    if codes_ru(it.get('codes')):
        facts.append(['Коды', codes_ru(it.get('codes'))])
    if it.get('status') == 'disputed':
        facts.append(['Статус', 'существует, но источники расходятся в деталях'])
    if it.get('status') == 'unsolved':
        facts.append(['Статус', 'загадка не разгадана'])
    ver = bool(it.get('verified'))
    ang = (i * 1.7) % 6.283
    e = {'id': f'xs{i}', 'n': SEC_RU.get(i) or re.sub(r'\s*\(.*?\)\s*$', '', it['name']).strip(), 'c': 'secret', 'r': 4 if ver else 2,
         'x': round(p['x'] + 14 * math.cos(ang)), 'y': round(p['y'] + 14 * math.sin(ang)), 't': it.get('desc_ru'),
         'u': links(it.get('sources')), 'f': facts, 's': ['web'], 'sub': KIND.get(it.get('kind'), 'Секрет'),
         'v': (3 if ver else 1) if not p['ap'] else (1 if ver else 0), 'force_new': 1}
    if i in SEC_RU:
        e['f'].append(['Название в гайдах', re.sub(r'\s*\(.*?\)\s*$', '', it['name']).strip()])
    if it.get('kind') in ICON:
        e['ic'] = ICON[it['kind']]
    if p['ap']:
        e['ap'] = 1
    extras.append(e); ns += 1
print('secrets placed:', ns)
json.dump(extras, open(args.out, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
json.dump(skipped, open(os.path.splitext(args.out)[0] + '_skipped.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('total extras', len(extras), 'skipped', len(skipped))
for e in extras:
    if 'id' in e:
        w = dict(e.get('f') or []).get('Привязка на карте', '')
        print(f"  {e['id']:6s} v{e['v']} {'~' if e.get('ap') else ' '} {e['n'][:38]:38s} @ {w[:60]}")
