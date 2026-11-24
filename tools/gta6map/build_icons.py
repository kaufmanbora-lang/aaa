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
    'suv': 'car-estate', 'tank': 'tank', 'knife': 'knife-military', 'bat': 'baseball-bat', 'bug': 'bug', 'dice': 'dice-5',
    'container': 'train-car-container', 'package': 'package-variant-closed', 'meteor': 'meteor', 'bottle2': 'bottle-tonic',
    'palette': 'palette', 'police': 'police-badge', 'homelock': 'home-lock', 'airport': 'airport', 'hospital': 'hospital-box',
    'paw': 'paw', 'meditation': 'meditation',
    # "what you need" symbols
    'lock': 'lock', 'lockopen': 'lock-open-variant', 'keyfob': 'key-wireless', 'alarm': 'alarm-light', 'tracker': 'radar',
    'shield': 'shield-half-full', 'tow': 'tow-truck', 'scan': 'cellphone-screenshot', 'saw': 'saw-blade', 'dialpad': 'dialpad',
    'clock': 'clock-outline', 'alert': 'alert', 'hand': 'hand-coin', 'star4': 'star-four-points', 'help': 'help-circle',
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
# original long-gun silhouettes (MDI only ships a pistol)
out.update({
    'smg': 'M3 8.6H17.2V9.6H21.5V11H17.2V12.4H13.6V18.6H11V12.4H9L8.3 15.6H5.9L6.5 12.4H3Z',
    'rifle': 'M1.5 9.2H5.2L6 8.4H13.2V9.2H22.5V10.6H18.4V11.8H14.8L13.6 16.8H11.2L12 11.8H9.6L9 13.8H7L7.3 11.8H5.2L3 14.6H1.5Z',
    'shotgun': 'M1.5 10.2L5.6 9H22.5V10.3H21.6V11.6H14V12.8H8.6V11.8H6.4L3.8 14.8L1.5 14.2Z',
    'sniper': 'M1 10.4L4.6 9.8V9.2H8V7.4H14.2V9.2H23V10.3H15.4V11.3L16.6 14.8L15.5 15.1L14.2 11.6H9.8L9 14.4H7L7.5 11.6H5.6L3 13.8L1 13.3Z',
})
os.makedirs(os.path.join(docs, 'data'), exist_ok=True)
dst = os.path.join(docs, 'data', 'icons.json')
json.dump(out, open(dst, 'w', encoding='utf8'), separators=(',', ':'))
print('icons:', len(out), 'bytes:', os.path.getsize(dst))
