#!/usr/bin/env python3
"""Extract the glyph paths used by the map from @mdi/svg (Material Design Icons, Apache-2.0)
into docs/data/icons.json. Usage: python3 build_icons.py /path/to/node_modules/@mdi/svg/svg [docs]
"""
import json, os, re, sys

src = sys.argv[1]
docs = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs')
ICONS = {
    # map glyphs: key used in build_data.py CATS -> mdi icon name
    'gun': 'pistol', 'car': 'car-side', 'supercar': 'car-sports', 'pickup': 'car-pickup', 'gem': 'watch',
    'safe': 'safe', 'eye': 'eye', 'card': 'cards-playing', 'camera': 'camera', 'book': 'book-open-variant',
    'music': 'music', 'brush': 'brush', 'jump': 'motorbike', 'parachute': 'parachute', 'plane': 'airplane',
    'bridge': 'bridge', 'vault': 'safe-square', 'bank': 'bank', 'ring': 'diamond-stone', 'cash': 'cash',
    'atm': 'atm', 'shop': 'store', 'burger': 'hamburger', 'bottle': 'bottle-wine', 'skull': 'skull',
    'handshake': 'handshake', 'garage': 'garage', 'spray': 'spray', 'wrench': 'wrench', 'fuel': 'gas-station',
    'drop': 'car-wash', 'bolt': 'ev-station', 'key': 'car-key', 'bus': 'bus', 'train': 'train', 'anchor': 'ferry',
    'ammo': 'ammunition', 'shirt': 'tshirt-crew', 'scissors': 'content-cut', 'tattoo': 'needle',
    'phone': 'cellphone', 'dumbbell': 'dumbbell', 'disco': 'glass-cocktail', 'cup': 'coffee', 'glass': 'beer',
    'hotdog': 'food-hot-dog', 'ball': 'basketball', 'golf': 'golf', 'pool': 'billiards', 'target': 'target',
    'joystick': 'gamepad-variant', 'fish': 'fish', 'flag': 'flag-checkered', 'drone': 'quadcopter',
    'mission': 'map-marker-star', 'star': 'star', 'door': 'door-open', 'leak': 'incognito', 'bed': 'bed',
    'road': 'road-variant', 'tree': 'palm-tree', 'factory': 'factory', 'home': 'home', 'building': 'office-building',
    'heli': 'helicopter', 'boat': 'sail-boat', 'bike': 'motorbike', 'bicycle': 'bicycle', 'truck': 'truck',
    'van': 'van-utility', 'ufo': 'ufo', 'ghost': 'ghost', 'chest': 'treasure-chest', 'alien': 'alien',
    # interface glyphs
    'ui-filter': 'filter-variant', 'ui-search': 'magnify', 'ui-close': 'close', 'ui-plus': 'plus',
    'ui-minus': 'minus', 'ui-check': 'check', 'ui-info': 'information', 'ui-share': 'share-variant',
    'ui-image': 'image-search', 'ui-layers': 'layers', 'ui-home': 'crosshairs-gps', 'ui-pin': 'map-marker',
    'ui-link': 'link-variant', 'ui-copy': 'content-copy', 'ui-down': 'chevron-down', 'ui-eyeoff': 'eye-off',
    'ui-help': 'help-circle', 'ui-alert': 'alert-circle', 'ui-tag': 'tag',
}
out = {}
for key, name in ICONS.items():
    svg = open(os.path.join(src, name + '.svg'), encoding='utf8').read()
    m = re.search(r'<path d="([^"]+)"', svg)
    out[key] = m.group(1)
os.makedirs(os.path.join(docs, 'data'), exist_ok=True)
dst = os.path.join(docs, 'data', 'icons.json')
json.dump(out, open(dst, 'w', encoding='utf8'), separators=(',', ':'))
print('icons:', len(out), 'bytes:', os.path.getsize(dst))
