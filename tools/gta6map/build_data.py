#!/usr/bin/env python3
"""Build docs/data/markers.json for the GTA 6 fan map.

Inputs (all optional except GTADB):
  --gtadb   checkout of github.com/rolux/gtadb.org        (landmarks, CC BY 4.0)
  --ign     folder with markers.js / taxonomy.js exported from the IGN/MapGenie Leonida map
  --ppx     checkout of theihtishaam/GTA-6-Interactive-Map-and-Loot-Tracker (MIT; PowerPyx-derived positions)
  --tr      folder with out_*.json: Russian location hints keyed by IGN location id
  --extras  JSON file with hand-resolved markers (research: weapons, vehicles, secrets)
  --docs    output site folder

Only facts are taken from third-party maps (names, positions, numeric attributes);
texts shown on the site are written for this project.
"""
import argparse, collections, json, math, os, re, time
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--gtadb', required=True)
ap.add_argument('--ign')
ap.add_argument('--ppx')
ap.add_argument('--tr')
ap.add_argument('--extras')
ap.add_argument('--docs', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs'))
args = ap.parse_args()

# ----------------------------------------------------------------------------- taxonomy
GROUPS = [
    ('rare', 'Редкое и ценное'),
    ('collect', 'Коллекционные предметы'),
    ('stunt', 'Трюки'),
    ('rob', 'Ограбления'),
    ('crime', 'Криминал'),
    ('veh', 'Транспорт и сервис'),
    ('shop', 'Магазины и услуги'),
    ('food', 'Еда и бары'),
    ('act', 'Развлечения и спорт'),
    ('race', 'Гонки'),
    ('story', 'Сюжет (спойлеры)'),
    ('place', 'Места и здания'),
]
# id, group, name, icon, default-on
CATS = [
    ('weapon', 'rare', 'Уникальное оружие', 'gun', 1),
    ('veh_standout', 'rare', 'Редкий транспорт (Standout)', 'car', 1),
    ('veh_randy', 'rare', 'Элитные авто для Рэнди', 'supercar', 1),
    ('veh_moses', 'rare', 'Авто для Мозеса', 'pickup', 1),
    ('valuable', 'rare', 'Часы и ценности', 'gem', 1),
    ('safe', 'rare', 'Сейфы', 'safe', 1),
    ('secret', 'rare', 'Секреты и пасхалки', 'eye', 1),
    ('card', 'collect', 'Коллекционные карточки', 'card', 1),
    ('waink_l', 'collect', 'WAiNK: достопримечательности', 'camera', 1),
    ('waink_c', 'collect', 'WAiNK: диковинки', 'camera', 1),
    ('waink_s', 'collect', 'WAiNK: скульптуры', 'camera', 1),
    ('magazine', 'collect', 'Журналы', 'book', 1),
    ('book', 'collect', 'Книгообмен', 'book', 1),
    ('playlist', 'collect', 'Уникальные плейлисты', 'music', 1),
    ('mural', 'collect', 'Муралы 1010', 'brush', 1),
    ('stunt', 'stunt', 'Уникальные прыжки', 'jump', 1),
    ('basejump', 'stunt', 'Бейс-джампинг', 'parachute', 0),
    ('knife', 'stunt', 'Пролёты ребром (Knife Flight)', 'plane', 0),
    ('bridge', 'stunt', 'Пролёты под мостами', 'bridge', 0),
    ('bigbank', 'rob', 'Крупные банки с хранилищем', 'vault', 1),
    ('bank', 'rob', 'Банки', 'bank', 1),
    ('jewelry', 'rob', 'Ювелирные магазины', 'ring', 1),
    ('payday', 'rob', 'Микрозаймы', 'cash', 0),
    ('pawn', 'rob', 'Ломбарды', 'cash', 0),
    ('atmtow', 'rob', 'Банкоматы, которые можно увезти', 'atm', 0),
    ('store', 'rob', 'Круглосуточные магазины', 'shop', 0),
    ('fastfood', 'rob', 'Фастфуд', 'burger', 0),
    ('liquor', 'rob', 'Алкомаркеты', 'bottle', 0),
    ('gang', 'crime', 'Нелегальные операции банд', 'skull', 1),
    ('contact', 'crime', 'Контакты и скупщики', 'handshake', 1),
    ('garage_buy', 'veh', 'Гаражи на продажу', 'garage', 1),
    ('garage', 'veh', 'Гаражи', 'garage', 0),
    ('spray', 'veh', "Pay 'n' Spray", 'spray', 0),
    ('mod', 'veh', 'Тюнинг-ателье', 'wrench', 0),
    ('gas', 'veh', 'Заправки', 'fuel', 0),
    ('wash', 'veh', 'Автомойки', 'drop', 0),
    ('charger', 'veh', 'Зарядки для электромобилей', 'bolt', 0),
    ('rental', 'veh', 'Прокат транспорта', 'key', 0),
    ('bus', 'veh', 'Автобусные остановки', 'bus', 0),
    ('train', 'veh', 'Станции поездов и метро', 'train', 0),
    ('ferry', 'veh', 'Паромы', 'anchor', 0),
    ('ammu', 'shop', 'Ammu-Nation и оружейные', 'ammo', 1),
    ('clothes', 'shop', 'Одежда и обувь', 'shirt', 0),
    ('hair', 'shop', 'Салоны красоты', 'scissors', 0),
    ('tattoo', 'shop', 'Тату-салоны', 'tattoo', 0),
    ('electronics', 'shop', 'Электроника', 'phone', 0),
    ('atm', 'shop', 'Банкоматы', 'atm', 0),
    ('gym', 'shop', 'Спортзалы', 'dumbbell', 0),
    ('club', 'shop', 'Клубы', 'disco', 0),
    ('cafe', 'food', 'Кафе и еда навынос', 'cup', 0),
    ('bar', 'food', 'Бары', 'glass', 0),
    ('streetfood', 'food', 'Уличная еда', 'hotdog', 0),
    ('hoop', 'act', 'Баскетбольные кольца', 'ball', 0),
    ('golf', 'act', 'Гольф и мини-гольф', 'golf', 0),
    ('pool', 'act', 'Бильярд', 'pool', 0),
    ('range', 'act', 'Тиры', 'target', 0),
    ('arcade', 'act', 'Аркадные автоматы', 'joystick', 0),
    ('fishing', 'act', 'Рыбные места', 'fish', 0),
    ('race', 'race', 'Гонки и испытания', 'flag', 0),
    ('drone', 'race', 'Гонки дронов', 'drone', 0),
    ('mission', 'story', 'Сюжетные миссии', 'mission', 0),
    ('lm_sight', 'place', 'Достопримечательности', 'star', 0),
    ('lm_interior', 'place', 'Здания с интерьером', 'door', 0),
    ('lm_leak', 'place', 'Места из сливов 2022', 'leak', 0),
    ('lm_hotel', 'place', 'Отели', 'bed', 0),
    ('lm_shop', 'place', 'Магазины и рестораны (GTADB)', 'shop', 0),
    ('lm_transport', 'place', 'Транспорт и мосты (GTADB)', 'road', 0),
    ('lm_nature', 'place', 'Природные объекты', 'tree', 0),
    ('lm_industry', 'place', 'Промзоны и офисы', 'factory', 0),
    ('lm_res', 'place', 'Жилые дома', 'home', 0),
    ('lm_other', 'place', 'Прочие здания', 'building', 0),
]
IGN_CAT = {
    'Standout Vehicle': 'veh_standout', 'Randy Vehicle': 'veh_randy', 'Moses Vehicle': 'veh_moses',
    'Safe': 'safe', 'Jack of Hearts': 'card', 'Delights': 'card', 'Nine1Nine': 'card',
    'Landmark': 'waink_l', 'Curiosity': 'waink_c', 'Sculpture': 'waink_s',
    'Magazine': 'magazine', 'Book Swap': 'book', 'Unique Playlist': 'playlist', '1010 Mural': 'mural',
    'Stunt Jump': 'stunt', 'Base Jump': 'basejump', 'Knife Flight': 'knife', 'Under the Bridge': 'bridge',
    'Bank': 'bank', 'Big Bank': 'bigbank', 'Payday Loans': 'payday',
    'Low-End Jewelry Store': 'jewelry', 'High-End Jewelry Store': 'jewelry', 'Pawn Shop': 'pawn',
    'ATM (Towable)': 'atmtow', 'Convenience Store': 'store', 'Fast Food': 'fastfood', 'Liquor Store': 'liquor',
    'Kingfishers': 'gang', 'Kolt & Associates': 'gang', 'M7': 'gang', 'La Polilla Negra': 'gang',
    'Final Chapter': 'gang', 'San4San': 'gang', 'PTT Youngin$': 'gang', 'The Guardia Brothers': 'gang',
    'Criminals': 'gang', 'Contact': 'contact',
    "Pay 'N' Spray": 'spray', 'Mod Shop': 'mod', 'Gas Station': 'gas', 'Car Wash': 'wash',
    'Electric Charger': 'charger', 'Bus Stop': 'bus', 'Train Station': 'train', 'Ferry Terminal': 'ferry',
    'Rental Vehicle': 'rental', 'Purchasable Garage': 'garage_buy', 'Garage': 'garage',
    'Ammu-Nation': 'ammu', 'Casual & Street': 'clothes', 'Sportswear': 'clothes', 'Formal': 'clothes',
    'Souvenir & Swimwear': 'clothes', 'Thrift': 'clothes', 'Footwear': 'clothes',
    'Hair & Beauty': 'hair', 'Tattoos': 'tattoo', 'Electronics': 'electronics', 'ATM': 'atm',
    'Gym': 'gym', 'Club': 'club', 'Cafes & Takeout': 'cafe', 'Bar': 'bar', 'Street Food': 'streetfood',
    'Basketball Hoop': 'hoop', 'Golf Course': 'golf', 'Mini-Golf Course': 'golf', 'Pool Table': 'pool',
    'Shooting Range': 'range', 'Arcade Machine': 'arcade', 'Fishing Hotspot': 'fishing',
    'Racing Introduction': 'race', 'Racing Challenge': 'race', 'Thrillbilly Mud Club': 'race',
    'Animal Crackers': 'race', "Hit 'n' Run VC": 'race', 'Hamlet Boone Speedway': 'race',
    'Ambrosia Raceway': 'race', 'Gellhorn Raceway': 'race', 'Top Fun Drones': 'drone',
}
# subtitle shown under the name for some IGN types
IGN_SUB = {
    'Jack of Hearts': 'Набор Jack of Hearts', 'Delights': 'Набор Delights', 'Nine1Nine': 'Набор Nine1Nine',
    'Low-End Jewelry Store': 'Недорогой ювелирный', 'High-End Jewelry Store': 'Элитный ювелирный',
    'Kingfishers': 'Банда Kingfishers', 'Kolt & Associates': 'Банда Kolt & Associates', 'M7': 'Банда M7',
    'La Polilla Negra': 'Банда La Polilla Negra', 'Final Chapter': 'Банда Final Chapter',
    'San4San': 'Банда San4San', 'PTT Youngin$': 'Банда PTT Youngin$',
    'The Guardia Brothers': 'Банда The Guardia Brothers', 'Criminals': 'Независимые преступники',
    'Casual & Street': 'Повседневная одежда', 'Sportswear': 'Спортивная одежда', 'Formal': 'Деловая одежда',
    'Souvenir & Swimwear': 'Сувениры и купальники', 'Thrift': 'Секонд-хенд', 'Footwear': 'Обувь',
    'Golf Course': 'Гольф-клуб', 'Mini-Golf Course': 'Мини-гольф',
    'Racing Introduction': 'Знакомство с гонками', 'Racing Challenge': 'Испытание',
    'Thrillbilly Mud Club': 'Thrillbilly Mud Club', 'Animal Crackers': 'Animal Crackers',
    "Hit 'n' Run VC": "Hit 'n' Run VC", 'Hamlet Boone Speedway': 'Boone Speedway',
    'Ambrosia Raceway': 'Ambrosia Raceway', 'Gellhorn Raceway': 'Gellhorn Raceway',
}
LABEL = {
    'Access': 'Двери', 'Security': 'Охрана', 'Tracker': 'Трекер', 'Sell Value': 'Цена продажи',
    'Cost to Register': 'Регистрация', 'Type': 'Тип', 'Era': 'Эпоха', 'Seats': 'Мест',
    'Storage': 'Багажник', 'Body Condition': 'Состояние кузова', 'Features': 'На месте есть',
    'Take Value': 'Добыча', 'Things to Steal': 'Что можно украсть', 'Key Valuables': 'Ключевые ценности',
    'Price': 'Цена', 'Parking Spots': 'Мест в гараже', 'Medals': 'Медали', 'Book': 'Книга',
    'Drop-off Prices': 'Цены скупки', 'Route': 'Маршруты', 'Specialist': 'Специалист', 'Style': 'Стиль',
    'Specialty': 'Специализация', 'Race Number': 'Номер гонки', 'Par Time': 'Контрольное время',
    'Reward': 'Награда', 'Max Payout': 'Макс. выплата', 'Laps': 'Кругов', 'Racers': 'Гонщиков',
    'Buy In': 'Взнос', 'Rating': 'Рейтинг', 'Rental Car': 'Аренда авто', 'Vehicle Rental': 'Аренда авто',
    'Inventory': 'Ассортимент', 'Cost': 'Стоимость', 'Class': 'Классы оружия',
    'Membership Cost': 'Абонемент', 'Vehicle': 'Транспорт', 'Track Marshal': 'Маршал трассы',
    'Time to beat': 'Время для победы', 'Waiver': 'Допуск',
}
VALUE = {
    'Locked': 'Заперто', 'Unlocked': 'Открыто', 'Key Cloner': 'Нужен клонер ключей', 'None': 'Нет',
    'Alarmed': 'Сигнализация', 'Deactivated': 'Отключена', 'Standard': 'Стандартный', 'Advanced': 'Продвинутый',
    'Tracker': 'Есть', 'Low': 'Низкая', 'Medium': 'Средняя', 'High': 'Высокая',
    'Muscle': 'Маслкар', 'Pickup': 'Пикап', 'Van': 'Фургон', 'Super': 'Суперкар', 'Supercars': 'Суперкары',
    'SUV': 'Внедорожник (SUV)', 'Off-Road': 'Внедорожный', 'Sedan': 'Седан', 'Coupe': 'Купе',
    'Bicycle': 'Велосипед', 'Chopper': 'Чоппер', 'Superbikes': 'Спортбайк', 'Superbike': 'Спортбайк',
    'Riverboat': 'Аэролодка', 'Sport': 'Спорткар', 'Sports': 'Спорткар', 'Dirtbike': 'Кроссовый мотоцикл',
    'Helicopter': 'Вертолёт', 'Military': 'Военная техника', 'Time Trial': 'Гонка на время',
    'Stunt Run': 'Трюковой заезд', 'Dirt Track': 'Грунтовая трасса', 'Street Race': 'Уличная гонка',
    'Demolition Race': 'Гонка на выживание', 'Poor': 'Плохое', 'Fair': 'Среднее', 'Good': 'Хорошее',
    'Excellent': 'Отличное', 'Pristine': 'Идеальное', 'Rentals Only': 'Только прокатный',
}
WORDS = {
    'ATM': 'банкомат', 'Bar': 'бар', 'Pool Table': 'бильярд', 'Arcade Cabinet': 'аркадный автомат',
    'Changing Room': 'примерочная', 'Food': 'еда', 'Cash Drawer': 'касса', 'Safe': 'сейф', 'Vault': 'хранилище',
    'Nail Tech': 'маникюр', 'Makeup': 'макияж', 'Gold': 'Золото', 'Silver': 'Серебро', 'Bronze': 'Бронза',
    'Narcotics': 'Наркотики', 'Jewelry': 'Украшения', 'Marked Bills': 'Меченые купюры',
    'Very Low': 'очень низкие', 'Low': 'низкие', 'Medium': 'средние', 'High': 'высокие', 'Very High': 'очень высокие',
}
SOURCES = {
    'ign': {'n': 'Интерактивная карта IGN / MapGenie', 'u': 'https://www.ign.com/maps/gta-6/leonida'},
    'gtadb': {'n': 'GTADB — база сообщества (CC BY 4.0)', 'u': 'https://map.gtadb.org/'},
    'ppx': {'n': 'PowerPyx (гайды и прохождения)', 'u': 'https://www.powerpyx.com/'},
    'web': {'n': 'Гайды и публикации игроков', 'u': ''},
}


def ign_to_game(lat, lng):
    """IGN/MapGenie pseudo lat/lng -> in-game metres.

    Their tile square is the same 32768 m frame as GTADB's, shifted by (950, 200) px
    at 4 m/px; verified by image correlation of the two tile pyramids.
    """
    X = (lng + 1.40625) / 1.40625 * 8192.0
    merc = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    Y = 8192.0 - merc / (2 * math.pi) * 2097152.0
    return (X - 950.0) * 4.0 - 16384.0, 16384.0 - (Y - 200.0) * 4.0


def load_js(path):
    s = open(path, encoding='utf8').read()
    return json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower()).strip()


def money(s):
    m = re.findall(r'\$?\s*([\d,]{3,})', s or '')
    vals = [int(x.replace(',', '')) for x in m if x.replace(',', '').isdigit()]
    return max(vals) if vals else None


def tr_value(v):
    v = v.strip()
    if v in VALUE:
        return VALUE[v]
    return v


def tr_list(v):
    items = [re.sub(r'^[-•\s]+', '', x).strip() for x in v.split('\n')]
    items = [x for x in items if x]
    out = []
    for x in items:
        m = re.match(r'^([A-Za-z ]+):\s*(.+)$', x)
        if m and m.group(1).strip() in WORDS:
            val = m.group(2).strip()
            out.append(f"{WORDS[m.group(1).strip()]}: {WORDS.get(val, val)}")
        else:
            out.append(WORDS.get(x, x))
    return out


# ----------------------------------------------------------------------------- GTADB
G = json.load(open(os.path.join(args.gtadb, 'map', 'data', '6', 'landmarks.json'), encoding='utf8'))
LEAK = re.compile(r'^l\d+$')
photo_dir = os.path.join(args.docs, 'photos')
markers = []
lm_xy, lm_area, lm_name, lm_id, lm_tags, lm_photo = [], [], [], [], [], []
TAG_RU = {
    'hotel': 'отель', 'residential': 'жилое здание', 'retail': 'торговля', 'transportation': 'транспорт',
    'natural': 'природный объект', 'industrial': 'промышленный объект', 'leisure': 'досуг',
    'government': 'госучреждение', 'utilities': 'коммунальный объект', 'landmark': 'достопримечательность',
    'public': 'общественное место', 'restaurant': 'ресторан', 'construction': 'стройка', 'office': 'офис',
    'agriculture': 'сельское хозяйство', 'supermarket': 'супермаркет', 'enterable': 'есть интерьер',
    'events': 'из списка событий (слив 2022)', 'point-of-interest': 'интересное место',
    '#bus': 'автобус', '#gas': 'заправка', '#supermarket': 'супермаркет', '#train': 'поезд', '#marina': 'марина',
    '#airport': 'аэропорт', '#hair': 'парикмахерская', '#clothes': 'одежда', '#metromover': 'метромувер',
    '#fence': 'скупщик', '#guns': 'оружейный', '#food': 'еда', '#vendor': 'торговец', '#tennis': 'теннис',
    '#metro': 'метро', '#safehouse': 'убежище', '#racetrack': 'гоночная трасса', '#modshop': 'тюнинг',
    '#police': 'полиция', '#hospital': 'больница', '#bar': 'бар', '#electronics': 'электроника',
    '#shoes': 'обувь', '#stripclub': 'стрип-клуб', '#nightclub': 'ночной клуб', "#pay'n'spray": "Pay 'n' Spray",
    '#jail': 'тюрьма', '#fastfood': 'фастфуд', '#tattoos': 'тату', '#drinks': 'напитки', '#blimp': 'дирижабль',
    '#carwash': 'автомойка', '#airbase': 'авиабаза', '#ferriswheel': 'колесо обозрения',
}


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
    addr, xy, _igp, rl_addr, rl_ll, _rlp, tags, _color, _ts = (it + [None] * 9)[:9]
    if not xy or len(xy) < 2 or not all(isinstance(v, (int, float)) for v in xy):
        continue
    tags = [t for t in (tags or [])]
    parts = [p.strip() for p in (addr or '').split(',')]
    name = parts[0] if parts and parts[0] and parts[0] != '?' else None
    area = ', '.join(p for p in parts[1:] if p and p != '?')
    is_leak = any(LEAK.match(t) for t in tags) or 'events' in tags
    has_photo = (not any(LEAK.match(t) for t in tags)) and os.path.exists(os.path.join(photo_dir, f'{key}.jpg'))
    rl_name = None
    if rl_addr and rl_addr != '?':
        rl_name = rl_addr.split(',')[0].strip()
    lm_xy.append((xy[0], xy[1])); lm_area.append(area); lm_name.append(name); lm_id.append(key)
    lm_tags.append(set(tags)); lm_photo.append(has_photo)
    cat = lm_category(tags)
    title = name or (f'Прототип: {rl_name}' if rl_name else f'Объект {key}')
    facts = []
    kinds = [TAG_RU[t] for t in tags if t in TAG_RU]
    if kinds:
        facts.append(['Тип', ', '.join(dict.fromkeys(kinds))])
    if rl_addr and rl_addr != '?':
        facts.append(['Прототип в реальности', rl_addr + (' (не подтверждено)' if 'unconfirmed' in tags else '')])
    v = 2
    note = None
    if 'events' in tags or '//may-not-exist' in tags:
        v = 1
        note = 'Известно по материалам слива 2022 года; в релизной версии может отсутствовать или отличаться.'
    elif any(LEAK.match(t) for t in tags):
        note = 'Место впервые опознано по материалам слива 2022 года (фото из слива не публикуются).'
    if not name:
        v = min(v, 1) if is_leak else v
    m = {'id': key, 'c': cat, 'n': title, 'x': round(xy[0]), 'y': round(xy[1]), 'r': 1, 'a': area, 's': ['gtadb'], 'v': v}
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

# ---- area labels drawn on the map (medians of GTADB landmark positions per area name)
_members = collections.defaultdict(list)
_parent = set()
for (lx, ly), area in zip(lm_xy, lm_area):
    comps = [c.strip() for c in area.split(',') if c.strip()]
    for j, comp in enumerate(comps):
        _members[comp].append((lx, ly))
        if j > 0 or len(comps) == 1:
            pass
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
print('area labels:', len(labels), [q['n'] for q in labels if q['k'] == 1])
print('GTADB landmarks placed:', len(markers))


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
        if lm_photo[i]:
            return {'p': f'photos/{lm_id[i]}.jpg', 'n': lm_name[i] or 'здание рядом', 'd': int(round(d))}
    return None


# ----------------------------------------------------------------------------- PowerPyx-derived positions
ppx_points = []   # (x, y, title, category, url)
missions_out = []
if args.ppx:
    P = os.path.join(args.ppx, 'public')

    def ppx_xy(nx, ny):
        return nx * 13824.0 - 10240.0, 10496.0 - ny * 19456.0
    for g in json.load(open(os.path.join(P, 'guides.json'), encoding='utf8')):
        if isinstance(g.get('x'), (int, float)) and isinstance(g.get('y'), (int, float)):
            x, y = ppx_xy(g['x'], g['y'])
            ppx_points.append((x, y, g.get('title', ''), g.get('subcategory') or g.get('category'), g.get('source')))
    ms = json.load(open(os.path.join(P, 'missions.json'), encoding='utf8'))
    mp = json.load(open(os.path.join(P, 'mission-positions.json'), encoding='utf8'))
    KIND = {'story': 'Сюжетная миссия', 'stranger': 'Встреча с незнакомцем', 'side': 'Побочная миссия', 'optional': 'Необязательное задание'}
    for m in ms:
        pos = mp.get(m['id'])
        if not pos or not isinstance(pos.get('x'), (int, float)) or not isinstance(pos.get('y'), (int, float)):
            continue
        x, y = ppx_xy(pos['x'], pos['y'])
        facts = [['Тип', KIND.get(m.get('kind'), m.get('kind') or '')]]
        if m.get('chapter') is not None:
            facts.append(['Глава', 'Пролог' if m['chapter'] == 0 else str(m['chapter'])])
        if m.get('character'):
            facts.append(['Персонаж', m['character']])
        if m.get('contact'):
            facts.append(['Кто даёт', m['contact']])
        mk = {'id': 'm-' + m['id'].replace('mission-', ''), 'c': 'mission', 'n': m['title'], 'x': round(x), 'y': round(y),
              'r': 3 if m.get('kind') == 'story' else 2, 'f': facts, 's': ['ppx'], 'v': 2,
              't': 'Место начала миссии (маркер на карте игры).'}
        if m.get('source'):
            mk['u'] = [['Прохождение на PowerPyx', m['source']]]
        missions_out.append(mk)
    print('PowerPyx guide points:', len(ppx_points), 'missions placed:', len(missions_out))

# ----------------------------------------------------------------------------- IGN / MapGenie
TR = {}
if args.tr:
    for fn in sorted(os.listdir(args.tr)):
        if re.match(r'out_\d+\.json$', fn):
            TR.update(json.load(open(os.path.join(args.tr, fn), encoding='utf8')))
    print('RU hints:', len(TR))

GTADB_TAG = {
    'ammu': {'#guns'}, 'gas': {'#gas'}, 'spray': {"#pay'n'spray"}, 'mod': {'#modshop'}, 'bus': {'#bus'},
    'train': {'#train', '#metro', '#metromover'}, 'tattoo': {'#tattoos'}, 'hair': {'#hair'},
    'clothes': {'#clothes', '#shoes'}, 'bar': {'#bar', '#drinks'}, 'fastfood': {'#fastfood'},
    'club': {'#nightclub', '#stripclub'}, 'electronics': {'#electronics'}, 'wash': {'#carwash'},
    'contact': {'#fence'}, 'streetfood': {'#vendor', '#food'}, 'store': {'#supermarket'},
}
PPX_CAT = {
    'bank': {'Small banks', 'Bank vaults'}, 'bigbank': {'Bank vaults', 'Small banks'}, 'payday': {'Payday loans'},
    'electronics': {'Electronics shops'}, 'pool': {'Pool'}, 'gym': {'Fitness'}, 'golf': {'Golf'},
}
CARD_R = {'Gold': 5, 'Purple': 4, 'Silver': 3, 'Pink': 3, 'Bronze': 2, 'Deep Red': 2, 'Standard': 1}
CARD_RU = {'Gold': 'золотая', 'Purple': 'фиолетовая', 'Silver': 'серебряная', 'Pink': 'розовая',
           'Bronze': 'бронзовая', 'Deep Red': 'тёмно-красная', 'Standard': 'стандартная'}
BASE_R = {
    'safe': 3, 'waink_l': 3, 'waink_c': 3, 'waink_s': 3, 'magazine': 3, 'book': 3, 'playlist': 3, 'mural': 3,
    'stunt': 2, 'basejump': 2, 'knife': 2, 'bridge': 1, 'contact': 3, 'garage_buy': 2, 'ammu': 3,
    'race': 2, 'drone': 2, 'club': 2, 'golf': 2, 'range': 2,
}
ign_markers = []
derived = []
if args.ign:
    M = load_js(os.path.join(args.ign, 'markers.js'))
    T = load_js(os.path.join(args.ign, 'taxonomy.js'))
    tn = {t['slug']: t['name'] for g in T['groups'] for t in g['types']}
    for m in M:
        tname = tn.get(m['t'])
        cat = IGN_CAT.get(tname)
        if not cat:
            continue
        x, y = ign_to_game(m['lat'], m['lng'])
        d = m.get('d') or ''
        parts = re.split(r'\*\*([^*]+?):\*\*', d)
        fld = {}
        for i in range(1, len(parts) - 1, 2):
            fld[parts[i].strip()] = parts[i + 1].strip()
        name = m['n'].strip()
        sub = IGN_SUB.get(tname)
        facts = []
        r = BASE_R.get(cat, 1)
        # ---- names for generic markers
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
        # ---- facts
        for k, v in fld.items():
            if k in ('Location', 'Challenge') or k not in LABEL:
                continue
            v = re.sub(r'_[^_]+_', '', v).strip()
            if not v or '??' in v:
                continue
            if '\n' in v or v.startswith('-'):
                lst = tr_list(v)
                if k == 'Key Valuables':
                    lst = [re.sub(r' Vehicle$', ' (транспорт)', q) for q in lst]
                    lst = ['сейф' if q == 'сейф' else q for q in lst]
                val = ', '.join(lst) if k != 'Route' else '; '.join(lst)
            else:
                val = tr_value(re.sub(r'\s+', ' ', v))
            lab = LABEL[k]
            if k == 'Security' and cat.startswith('veh_'):
                lab = 'Сигнализация'
            if k == 'Type' and cat in ('race', 'drone'):
                lab = 'Тип / район'
            facts.append([lab, val])
        # ---- rarity
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
        mk = {'id': 'i' + str(m['s']), 'c': cat, 'n': name, 'x': round(x), 'y': round(y), 'r': r, 's': ['ign'], 'v': 2}
        if sub:
            mk['sub'] = sub
        if facts:
            mk['f'] = facts
        hint = TR.get(str(m['s']))
        if hint:
            mk['t'] = hint
        mk['_t'] = tname
        mk['_fld'] = fld
        ign_markers.append(mk)
        # ---- derived unique items of illegal operations
        if cat == 'gang' and fld.get('Key Valuables'):
            items = [re.sub(r'^[-•\s]+', '', q).strip() for q in fld['Key Valuables'].split('\n')]
            items = [q for q in items if q and q != 'Safe' and not q.endswith(' Vehicle')]
            for j, item in enumerate(items):
                is_watch = item.endswith('Watch')
                ang = 2 * math.pi * j / max(1, len(items)) + 0.6
                derived.append({
                    'id': f"k{m['s']}-{j}", 'c': 'valuable' if is_watch else 'weapon', 'n': item,
                    'x': round(x + 9 * math.cos(ang)), 'y': round(y + 9 * math.sin(ang)),
                    'r': 4 if is_watch else 5, 's': ['ign'], 'v': 2,
                    'sub': 'Часы' if is_watch else 'Уникальный вариант оружия',
                    'f': [['Где', f"нелегальная операция «{m['n'].strip()}»" + (f" ({sub})" if sub else '')],
                          ['Охрана объекта', tr_value(fld.get('Security', '').strip() or '—')]],
                    't': 'Ключевая ценность нелегальной операции: находится на территории объекта, точное место — внутри охраняемой зоны.',
                    '_op': m['n'].strip(),
                })
    print('IGN markers:', len(ign_markers), 'derived unique items:', len(derived))

# ----------------------------------------------------------------------------- cross-verification
lm_norm = [norm(n) if n else '' for n in lm_name]
STOP = {'the', 'of', 'and', 'store', 'shop', 'station', 'big', 'bank', 'gas', 'a', 'n', 'at', 'in'}


def tokens(s):
    return {t for t in norm(s).split() if t not in STOP and len(t) > 1}


confirmed = 0
for mk in ign_markers:
    x, y, cat = mk['x'], mk['y'], mk['c']
    srcs = []
    near = nearest_lm(x, y, 10)
    want = GTADB_TAG.get(cat)
    nt = tokens(re.sub(r'\s+[-–]\s+.*$', '', mk['n']))
    for i, d in near:
        if d > 160:
            break
        if want and d <= 70 and (lm_tags[i] & want):
            srcs.append(('gtadb', lm_id[i])); break
        if lm_norm[i] and nt and d <= 160:
            lt = tokens(lm_name[i])
            if lt and (nt <= lt or lt <= nt) and len(nt & lt) >= 1 and (len(nt & lt) >= 2 or len(nt) == 1 == len(lt)):
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
print('IGN markers confirmed by an independent source:', confirmed)

# ----------------------------------------------------------------------------- extras (research)
extras = []
if args.extras and os.path.exists(args.extras):
    extras = json.load(open(args.extras, encoding='utf8'))
    print('extras:', len(extras))

# merge research info into derived weapon markers when names match
by_name = collections.defaultdict(list)
for d in derived + ign_markers:
    by_name[norm(d['n'])].append(d)
final_extras = []
for e in extras:
    tgt = None
    for key in [norm(e['n'])] + [norm(a) for a in e.get('aka', [])]:
        if key in by_name:
            cands = [q for q in by_name[key] if q['c'] == e['c'] or (e['c'].startswith('veh') and q['c'].startswith('veh'))]
            if cands:
                tgt = cands[0]; break
    if tgt is not None and not e.get('force_new'):
        if e.get('t'):
            tgt['t'] = e['t'] if tgt['c'] in ('weapon', 'valuable') or not tgt.get('t') else tgt['t']
        for u in e.get('u', []):
            tgt.setdefault('u', []).append(u)
        if 'web' not in tgt['s']:
            tgt['s'].append('web')
        if e.get('v', 0) >= 2:
            tgt['v'] = 3
        for f in e.get('f', []):
            if f[0] not in [q[0] for q in tgt.get('f', [])]:
                tgt.setdefault('f', []).append(f)
        if e.get('img') and not tgt.get('img'):
            tgt['img'] = e['img']
        continue
    if 'x' not in e:
        continue
    final_extras.append({k: v for k, v in e.items() if k not in ('aka', 'force_new')})
print('extras merged into existing markers:', len(extras) - len(final_extras), 'added as new:', len(final_extras))

# ----------------------------------------------------------------------------- finish
allm = markers + ign_markers + derived + missions_out + final_extras
catset = {c[0] for c in CATS}
out = []
for mk in allm:
    assert mk['c'] in catset, mk['c']
    if not (-16000 < mk['x'] < 16000 and -16000 < mk['y'] < 16000):
        continue
    if not mk.get('a') and not mk['id'].startswith('L'):
        mk['a'] = area_of(mk['x'], mk['y'])
    if not mk.get('p') and not mk['id'].startswith('L'):
        np_ = near_photo(mk['x'], mk['y'])
        if np_:
            mk['np'] = np_
    for k in [k for k in mk if k.startswith('_')]:
        del mk[k]
    if not mk.get('a'):
        mk.pop('a', None)
    out.append(mk)

counts = collections.Counter(m['c'] for m in out)
cats = [{'id': c[0], 'g': c[1], 'n': c[2], 'i': c[3], 'on': c[4], 'count': counts.get(c[0], 0)} for c in CATS if counts.get(c[0], 0)]
data = {
    'generated': time.strftime('%Y-%m-%d'),
    'groups': [{'id': g[0], 'n': g[1]} for g in GROUPS if any(c['g'] == g[0] for c in cats)],
    'cats': cats,
    'sources': SOURCES,
    'labels': labels,
    'markers': out,
}
os.makedirs(os.path.join(args.docs, 'data'), exist_ok=True)
dst = os.path.join(args.docs, 'data', 'markers.json')
json.dump(data, open(dst, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print('markers:', len(out), 'size: %.2f MB' % (os.path.getsize(dst) / 1e6))
print('verification:', sorted(collections.Counter(m['v'] for m in out).items()))
print('with own photo:', sum(1 for m in out if m.get('p')), 'with nearby photo:', sum(1 for m in out if m.get('np')))
for c in cats:
    print(f"  {c['count']:5d}  {c['id']:13s} {c['n']}")
