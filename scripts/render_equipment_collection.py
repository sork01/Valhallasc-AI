"""Render one poster of every distinct class equipment look from shipped atlases.

Usage: python3 scripts/render_equipment_collection.py [output.png]
The catalog decides which art belongs to a set; PNG/depth atlases decide the pixels.
"""
import json
from functools import lru_cache
from pathlib import Path
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'docs/equipment-sets-level-1-99.png'
ITEMS = json.loads((ROOT / 'world/items.txt').read_text())
CLASSES = [('warrior', 'Warrior', 'warrior_layered', '#d8aa68'),
           ('mage', 'Mage', 'mage', '#79b9e4'),
           ('assassin', 'Assassin', 'assassin', '#b7a0d9'),
           ('priest', 'Priest', 'priest', '#e2d59d'),
           ('hunter', 'Hunter', 'hunter', '#9ac78f')]
SLOTS = [('armor', 'armor'), ('pants', 'pants'), ('shoulders', 'shoulders'),
         ('gloves', 'gloves'), ('headgear', 'head'), ('necklace', 'necklace'),
         ('accessory', 'accessory'), ('weapon', 'weapon')]
# The first two entries have different starter shapes. Levels 5–20 repeat these
# two looks; level 55 repeats 50. Later boss items reuse starter art.
SETS = [
    ('1–20', 'Starter', 1, None, 'common'),
    ('1–20', 'Starter upgrade', 1, None, 'uncommon'),
    ('20', 'Undervault', 20, 'undervault', None),
    ('25', 'Progression', 25, None, 'common'),
    ('30', 'Progression', 30, None, 'common'),
    ('35', 'Progression', 35, None, 'common'),
    ('40', 'Progression', 40, None, 'common'),
    ('40', 'Cathedral Cloister', 40, 'cathedral_cloister', None),
    ('45', 'Progression', 45, None, 'common'),
    ('45', 'Cathedral Reliquary', 45, 'cathedral_reliquary', None),
    ('50–55', 'Progression', 50, None, 'common'),
    ('50', 'Cathedral Nave', 50, 'cathedral_nave', None),
    ('60', 'Progression', 60, None, 'common'),
    ('60', 'Moonwell', 60, 'moonwell', None),
    *[(str(level), 'Progression', level, None, 'common') for level in (65, 70, 75, 80, 85, 90)],
    ('95–99', 'Progression', 95, None, 'common'),
]
METADATA = {name: json.loads((ASSETS / f'{stem}_sprites.txt').read_text())
            for name, _, stem, _ in CLASSES}
# Keep these four-tone color ramps equal to DUNGEON_PALETTES in magesprite.js.
DUNGEON_PALETTES = {
    'regearvault': ['#071d25', '#164d57', '#36bcb0', '#b7fff0'],
    'regearcloister': ['#342d25', '#7e7049', '#d3bf7f', '#fff5c8'],
    'regearreliquary': ['#2a193a', '#71396e', '#ca64aa', '#ffe0ef'],
    'regearnave': ['#381d1d', '#a64425', '#ee993d', '#fff0aa'],
    'regearmoonwell': ['#22284b', '#56569a', '#aaa3db', '#f0e8ff'],
}


def item_for(cls, kind, level, source, rarity):
    candidates = [item for item in ITEMS if item.get('class') == cls and item['kind'] == kind
                  and item.get('requiredLevel') == level and item.get('source') == source]
    if rarity:
        candidates = [item for item in candidates if item.get('rarity') == rarity]
    if len(candidates) != 1:
        raise ValueError(f'Expected one {cls}/{kind} level {level} source {source} rarity {rarity}: {len(candidates)}')
    return candidates[0]


def art_for(cls, kind, level, source, rarity):
    selected = [item for item in ITEMS if item.get('class') == cls and item['kind'] == kind
                and item.get('requiredLevel') == level and item.get('source') == source
                and (not rarity or item.get('rarity') == rarity)]
    if not selected and cls is None and source:
        # Undervault has no exclusive necklace; show the highest ordinary one available.
        return art_for(None, kind, max(n for n in (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 65, 70, 75, 80, 85, 90, 95) if n <= level), None, 'common')
    if not selected:
        raise ValueError(f'Missing {cls}/{kind} level {level} source {source} rarity {rarity}')
    if source and len(selected) != 1:
        raise ValueError(f'Ambiguous special piece: {cls}/{kind}/{source}')
    item = selected[0]
    return item.get('art') or item['variant']


@lru_cache(maxsize=1100)
def part_frame(cls, part):
    meta = METADATA[cls]
    files = meta['parts'].get(part)
    if not files:
        raise ValueError(f'Missing atlas layer: {cls}/{part}')
    fw, fh = meta['frame']
    row = meta['clips']['idle']['row0']
    box = (0, row * fh, fw, (row + 1) * fh)
    with Image.open(ASSETS / files['png']) as atlas:
        rgba = np.asarray(atlas.crop(box).convert('RGBA')).copy()
    with Image.open(ASSETS / files['depth']) as atlas:
        depth = np.asarray(atlas.crop(box).convert('RGB')).astype(np.uint16)
    return rgba, depth[:, :, 0] * 256 + depth[:, :, 1]


def figure(cls, level, source, rarity):
    color, nearest = part_frame(cls, 'body')
    color = color.copy()
    nearest = np.where(color[:, :, 3] > 0, nearest, 65535).copy()
    chosen = []
    for kind, slot in SLOTS:
        variant = art_for(cls if kind in ('armor', 'shoulders', 'gloves', 'headgear', 'weapon') else None,
                          kind, level, source, rarity)
        part = f'{slot}_{variant}'
        pixels, depth = part_frame(cls, part)
        if variant in DUNGEON_PALETTES:
            pixels = pixels.copy()
            palette = np.array([[int(c[n:n + 2], 16) for n in (1, 3, 5)]
                                for c in DUNGEON_PALETTES[variant]], dtype=np.float32)
            rgb = pixels[:, :, :3].astype(np.float32)
            light = np.clip(((rgb[:, :, 0] * .25 + rgb[:, :, 1] * .65 + rgb[:, :, 2] * .1)
                             / 255 - .1) / .82 * 3, 0, 2.999)
            index = np.floor(light).astype(np.uint8)
            mix = (light - index)[:, :, None]
            pixels[:, :, :3] = np.rint(palette[index] * (1 - mix) + palette[index + 1] * mix).astype(np.uint8)
        nearer = (pixels[:, :, 3] > 0) & (depth <= nearest)
        color[nearer] = pixels[nearer]
        nearest[nearer] = depth[nearer]
        chosen.append(part)
    image = Image.fromarray(color, 'RGBA')
    if not image.getbbox():
        raise ValueError(f'Blank figure: {cls}/{level}/{source}')
    return image, chosen


def font(size, bold=False):
    file = '/usr/share/fonts/truetype/dejavu/DejaVuSans' + ('-Bold' if bold else '') + '.ttf'
    return ImageFont.truetype(file, size)


def main():
    node = '/home/serveperry/.nvm/versions/node/v20.20.2/bin/node'
    env = {**os.environ, 'NODE_PATH': '/home/serveperry/webserver/www/dybase2/node_modules'}
    subprocess.run([node, 'scripts/render_dungeon_marks.cjs'], cwd=ROOT, env=env, check=True)
    marks = {name: Image.open(ROOT / 'test-results/dungeon-marks' / (name + '.png')).convert('RGBA')
             for name in ('regearvault', 'regearcloister', 'regearreliquary', 'regearnave', 'regearmoonwell')}
    source_mark = {'undervault': 'regearvault', 'cathedral_cloister': 'regearcloister',
                   'cathedral_reliquary': 'regearreliquary', 'cathedral_nave': 'regearnave',
                   'moonwell': 'regearmoonwell'}
    left, col, top, row = 228, 322, 176, 286
    width, height = left + 5 * col + 30, top + len(SETS) * row + 122
    poster = Image.new('RGB', (width, height), '#101923')
    draw = ImageDraw.Draw(poster)
    draw.text((34, 24), 'VALHALLA', font=font(43, True), fill='#f1d395')
    draw.text((36, 78), 'EQUIPMENT SETS  •  LEVELS 1–99', font=font(21, True), fill='#d9e5ea')
    draw.text((36, 116), 'One colorway per distinct worn look  ·  male character sprites  ·  real game atlases',
              font=font(16), fill='#93a7b3')
    for n, (_, name, _, accent) in enumerate(CLASSES):
        x = left + n * col
        draw.rounded_rectangle((x + 6, 147, x + col - 8, 168), radius=8, fill=accent)
        draw.text((x + 16, 145), name.upper(), font=font(23, True), fill='#14212b')
    evidence = []
    for index, (levels, label, level, source, rarity) in enumerate(SETS):
        y = top + index * row
        special = source is not None
        draw.rounded_rectangle((18, y + 5, width - 18, y + row - 7), radius=14,
                               fill='#1d2d39' if special else ('#17242f' if index % 2 else '#1b2a35'),
                               outline='#997d58' if special else '#334655', width=2)
        draw.text((36, y + 31), 'LV ' + levels, font=font(25, True), fill='#f2d394')
        draw.text((36, y + 74), label, font=font(17, True), fill='#bfcfd6')
        if special:
            draw.text((36, y + 105), 'DUNGEON SET', font=font(11, True), fill='#a99170')
        row_evidence = {'level': levels, 'set': label, 'classes': {}}
        for n, (cls, name, _, accent) in enumerate(CLASSES):
            image, chosen = figure(cls, level, source, rarity)
            x = left + n * col + 20
            if special:
                # Render the same animated silhouette mark that MageSprite.draw
                # paints in the live game, behind the actual equipment layers.
                image = image.resize((240, 240), Image.Resampling.NEAREST)
                scene = Image.alpha_composite(marks[source_mark[source]], image.crop((10, 1, 230, 201)))
                image = scene.resize((280, 254), Image.Resampling.NEAREST)
                poster.paste(image, (x, y + 15), image)
            else:
                # Preserve a common scale and baseline. The atlas includes weapon reach.
                image = image.crop((0, 0, 160, 132)).resize((280, 231), Image.Resampling.NEAREST)
                poster.paste(image, (x, y + 23), image)
            draw.line((x + 20, y + 259, x + 260, y + 259), fill=accent, width=2)
            row_evidence['classes'][cls] = chosen
        evidence.append(row_evidence)
        print(f'{index + 1}/{len(SETS)} {levels} {label}', flush=True)
    footer = top + len(SETS) * row + 22
    draw.text((32, footer), 'Repeated art is grouped: levels 5–20 use the starter shapes; level 55 uses level 50 art.',
              font=font(15), fill='#b8c9d0')
    draw.text((32, footer + 27), 'Dungeon marks use the live game renderer. The 95 set remains wearable through 99.',
              font=font(15), fill='#b8c9d0')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    poster.save(OUT, optimize=True)
    OUT.with_suffix('.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'{OUT} — {width} × {height}, {len(SETS) * len(CLASSES)} figures', flush=True)


if __name__ == '__main__':
    main()
