#!/usr/bin/env python3
"""Build or export the editable PixelFlow atlas for the Blacksmithing profession."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from make_item_sprites import index_frames, palette_of
from make_npcp_sprites import pf_api

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
SOURCE = ASSETS / 'blacksmithing-art.txt'
SIZE, COLS = 28, 9
INK = '#28222d'
METALS = [
    ('#596479', '#99afbf', '#e8eef0'), ('#873e36', '#cb6f45', '#ffc37d'),
    ('#465062', '#78899b', '#cbd5de'), ('#62577a', '#a99fb9', '#f8e8f9'),
    ('#906038', '#d5a749', '#ffe18b'), ('#284676', '#467dbb', '#a8ddff'),
    ('#346067', '#71aca2', '#c1f2c7'), ('#4b397b', '#896ab4', '#dfbffd'),
    ('#8a4738', '#df853e', '#ffe194'), ('#302f68', '#746fbe', '#f6deff'),
]
EXPERT_METALS = [
    ('#423560', '#784fa3', '#d7abf3'), ('#86502b', '#db9b45', '#fff4a8'),
    ('#285b44', '#4ca96f', '#bbf1b3'), ('#304f72', '#5fadd2', '#dcfbff'),
    ('#583e73', '#a376a8', '#ffd49b'), ('#62452f', '#bb893b', '#fff0bf'),
    ('#623e38', '#cd6747', '#ffbf83'), ('#482956', '#9e56a8', '#edbce8'),
]


def rock(draw, shade, index, vein):
    dark, metal, light = shade
    if vein:
        draw.ellipse((1, 21, 26, 26), fill='#211d27')
        draw.polygon([(2, 22), (4, 14), (8, 12), (11, 4), (20, 3), (24, 9), (26, 20), (23, 24), (7, 25)],
                     fill='#494354', outline=INK)
        draw.polygon([(4, 16), (9, 14), (13, 6), (19, 5), (22, 10), (15, 15), (10, 19)], fill='#6a6473')
        draw.polygon([(4, 21), (10, 15), (15, 15), (20, 11), (24, 13), (23, 19), (15, 20), (10, 24)],
                     fill=dark)
        draw.line([(6, 21), (11, 18), (16, 17), (22, 14)], fill=metal, width=2)
        draw.line([(12, 18), (13, 13), (16, 10)], fill=light)
        draw.polygon([(17, 19), (21, 16), (24, 18), (20, 21)], fill=metal, outline=dark)
    else:
        draw.polygon([(3, 18), (5, 9), (13, 4), (21, 5), (25, 13), (22, 23), (11, 25), (5, 23)],
                     fill=dark, outline=INK)
        draw.polygon([(6, 10), (13, 6), (20, 7), (23, 12), (19, 15), (10, 16)], fill=metal)
        draw.line([(9, 10), (14, 7), (19, 8)], fill=light, width=2)
        draw.line([(7, 18), (12, 20), (21, 16)], fill='#4d4656')
    glints = [(8, 14), (21, 12), (18, 7), (15, 14), (20, 20)]
    x, y = glints[index % len(glints)]
    draw.rectangle((x, y, x+1, y+1), fill=light)
    if index >= 5:
        draw.point((x+3, y-1), fill=light)


def icon(kind, index):
    image = Image.new('RGBA', (SIZE, SIZE))
    d = ImageDraw.Draw(image)
    if kind in ('ore', 'vein'):
        rock(d, METALS[index], index, kind == 'vein')
    elif kind == 'bar':
        dark, metal, light = METALS[index]
        d.polygon([(2, 18), (5, 11), (19, 4), (25, 8), (26, 13), (21, 20), (8, 24)],
                  fill=dark, outline=INK)
        d.polygon([(6, 12), (19, 6), (24, 9), (19, 15), (9, 20), (4, 17)], fill=metal)
        d.line([(6, 13), (19, 7), (23, 9)], fill=light, width=2)
        d.line([(11, 17), (18, 14), (20, 11)], fill=light)
    elif kind in ('pick', 'expert_pick'):
        expert = kind == 'expert_pick'
        dark, metal, light = EXPERT_METALS[index] if expert else METALS[[2, 1, 3, 5, 7][index]]
        d.line((4, 24, 19, 8), fill=INK, width=5)
        d.line((4, 24, 19, 8), fill='#9a653f', width=3)
        d.line((4, 23, 18, 8), fill='#dca670')
        d.polygon([(7, 7), (10, 4), (17, 4), (23, 9), (26, 18), (22, 14), (17, 10), (12, 8)],
                  fill=metal, outline=INK)
        d.line([(11, 5), (17, 5), (22, 9), (24, 14)], fill=light)
        d.line([(13, 14), (16, 16)], fill=dark, width=2)
        if expert:
            d.polygon([(5, 8), (11, 7), (15, 9), (13, 11), (8, 11)], fill=dark, outline=INK)
            d.ellipse((16, 6, 20, 10), fill=light, outline=dark)
            d.line([(8, 18), (11, 20)], fill=light, width=2)
            if index == 5:
                d.line([(13, 3), (17, 2), (22, 4), (25, 8)], fill=light, width=2)
    elif kind in ('plan', 'expert_plan'):
        expert = kind == 'expert_plan'
        dark, metal, light = EXPERT_METALS[index] if expert else METALS[index % len(METALS)]
        d.polygon([(6, 3), (22, 3), (25, 6), (22, 10), (21, 22), (18, 25), (3, 25), (3, 21), (6, 18)],
                  fill='#e7cca0', outline=INK)
        d.line([(9, 5), (20, 5), (18, 21), (4, 22)], fill='#94744e', width=2)
        d.line([(9, 10), (18, 10), (12, 17), (8, 17)], fill=dark, width=2)
        d.ellipse((16, 16, 24, 24), fill=metal, outline=dark)
        d.rectangle((19, 19, 21, 21), fill=light)
        if expert:
            d.polygon([(20, 17), (23, 20), (20, 23), (17, 20)], fill=light, outline=dark)
            d.line([(7, 7), (20, 7), (17, 15)], fill=metal, width=2)
        elif index >= 10:
            d.line([(7, 7), (20, 7), (17, 15)], fill='#b974aa', width=2)
    elif index == 0:
        d.polygon([(2, 18), (7, 9), (12, 9), (16, 4), (22, 7), (25, 17), (20, 23), (8, 24)],
                  fill='#4d4858', outline=INK)
        d.line([(5, 17), (9, 12), (13, 11), (18, 7), (21, 9)], fill='#827e8d', width=2)
        d.line([(10, 19), (15, 15), (21, 15)], fill='#292737', width=2)
    elif index == 1:
        for x, y in [(2, 14), (7, 8), (12, 2)]:
            d.polygon([(x,y+3),(x+10,y),(x+14,y+4),(x+12,y+9),(x+4,y+12),(x,y+8)],
                      fill='#a1714d', outline=INK)
            d.line((x+3,y+4,x+10,y+2), fill='#e3ab72')
            d.ellipse((x+7,y+4,x+12,y+8), fill='#c58d5e', outline='#744a38')
    elif index == 2:
        for x,y in [(4, 6), (9, 6), (15, 4)]:
            d.polygon([(x,y),(x+8,y+2),(x+5,y+19),(x+1,y+19),(x-2,y+15)], fill='#94583e', outline=INK)
            d.line((x+2,y+2,x-1,y+14), fill='#c78559')
    else:
        d.polygon([(4, 12),(16, 5),(24, 8),(25, 17),(17, 22),(5, 24),(2, 20)], fill='#d8c9ad', outline=INK)
        for shift in range(3):
            d.line((7+5*shift,10-2*shift, 11+5*shift,20-2*shift), fill='#f4e4c9', width=2)
        d.ellipse((3, 13, 10, 21), outline='#958f84')
    return image


def roster():
    catalog = json.loads((ROOT / 'world/blacksmithing.txt').read_text())
    plans = [r for r in catalog['recipes'] if 'plan' in r]
    expert_plan = lambda recipe: 'dropZone' in recipe or recipe['skill'] == 600
    pairs = [('ore', [t['ore'] for t in catalog['tiers']]),
             ('bar', [r['item'] for r in catalog['recipes'] if r['method'] == 'smelt']),
             ('pick', [p['item'] for p in catalog['picks'] if not p.get('expertCap')]),
             ('part', [p['id'] for p in catalog['materials'] if 'price' in p and p['id'] != 'smith_pick_1']),
             ('plan', [r['plan'] for r in plans if not expert_plan(r)]),
             ('vein', [f'vein_{i}' for i in range(len(catalog['tiers']))]),
             ('expert_pick', [p['item'] for p in catalog['picks'] if p.get('expertCap')]),
             ('expert_plan', [r['plan'] for r in plans if expert_plan(r)])]
    return [(key, kind, n) for kind, keys in pairs for n, key in enumerate(keys)]


def packed(frames):
    atlas = Image.new('RGBA', (SIZE * COLS, SIZE * math.ceil(len(frames) / COLS)))
    for n, image in enumerate(frames):
        atlas.alpha_composite(image, (n % COLS * SIZE, n // COLS * SIZE))
    return atlas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['preview', 'build', 'export', 'verify'])
    ap.add_argument('--preview', type=Path, default=Path('/tmp/valhalla-blacksmithing-art.png'))
    args = ap.parse_args()
    entries = roster()
    if args.action == 'preview':
        atlas = packed([icon(kind, n) for _, kind, n in entries])
        atlas.resize((atlas.width * 3, atlas.height * 3), Image.Resampling.NEAREST).save(args.preview)
        return
    pf = pf_api()
    sources = json.loads(SOURCE.read_text())['sources'] if SOURCE.exists() else []
    if args.action == 'build':
        existing = {key for source in sources for key in source['order']}
        missing = [entry for entry in entries if entry[0] not in existing]
        groups = [('expert_v1', missing)]
        if not sources:
            groups = [('tools_v2', missing[:29]), ('plans_and_veins_v1', missing[29:54]),
                      ('expert_v1', missing[54:])]
        for label, group in groups:
            if not group:
                continue
            name = f'valhallasc_blacksmithing_{label}'
            sprite = pf.ids(name).get(name)
            if not sprite:
                pixels = [np.array(icon(kind, n)) for _, kind, n in group]
                palette, colors = palette_of(pixels)
                ops = [dict(op='grid', frame=i, layer=0, x=0, y=0, rows=grid.tolist())
                       for i, grid in enumerate(index_frames(pixels, colors))]
                result = pf.api('create', dict(name=name, width=SIZE, height=SIZE, frames=len(group),
                                               layers=1, fps=1, palette=palette, persist=True, ops=ops))
                assert result.get('ok'), result.get('errors')
                sprite = result['sprite_id']
            sources.append(dict(sprite=sprite, order=[key for key, _, _ in group]))
        if missing:
            SOURCE.write_text(json.dumps(dict(sources=sources), indent=2) + '\n')

    order = [key for source in sources for key in source['order']]
    assert len(order) == len(entries) and set(order) == {key for key, _, _ in entries}
    frames = []
    for source in sources:
        spec, grids = pf.load(source['sprite'])
        assert (spec['width'], spec['height'], len(grids)) == (SIZE, SIZE, len(source['order']))
        frames.extend(Image.fromarray(pf.to_rgba(data[0], spec['palette'])) for data in grids)
    atlas = packed(frames)
    path = ASSETS / 'blacksmithing.png'
    if args.action == 'verify':
        assert Image.open(path).convert('RGBA').tobytes() == atlas.tobytes()
    else:
        atlas.save(path, optimize=True)
        metadata = dict(size=SIZE, cols=COLS, rows=atlas.height // SIZE,
                        at={key: [i % COLS, i // COLS] for i, key in enumerate(order)})
        (ROOT / 'client/blacksmithing-art.js').write_text(
            "'use strict';\nwindow.BLACKSMITHING_ART = " + json.dumps(metadata, separators=(',', ':')) + ';\n')
    print(f'{args.action}: {len(frames)} frames, PixelFlow IDs {[s["sprite"] for s in sources]}')


if __name__ == '__main__':
    main()
