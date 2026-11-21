#!/usr/bin/env python3
"""Create editable PixelFlow sprites and export the Alchemy atlas."""
import argparse
import colorsys
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from make_item_sprites import index_frames, palette_of
from make_npcp_sprites import pf_api

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
SOURCE = ASSETS / 'alchemy-art.txt'
SIZE, COLS = 32, 9
INK = '#262034'
HUES = [46, 8, 193, 34, 123, 284, 322, 167, 221, 50, 31, 275, 245, 35,
        340, 359, 103, 181, 204, 305, 39, 5]
STATS = dict(damage=5, ward=221, healing=155, speed=302, health=34)


def color(hue, s, v):
    return tuple(round(n * 255) for n in colorsys.hsv_to_rgb((hue % 360) / 360, s, v))


def plant(draw, x, y, bottom, index):
    hue = HUES[index]
    leaf = color(115 + index * 3, .57, .60)
    petal = color(hue, .60, .95)
    shadow = color(hue - 13, .75, .62)
    glint = color(hue + 8, .26, 1)
    draw.line((x - 1, bottom, x, y), fill='#243739', width=3)
    draw.line((x, bottom, x, y), fill=leaf, width=2)
    mid = (y + bottom) // 2
    draw.polygon([(x, mid+2), (x-5, mid-4), (x-6, mid), (x-2, mid+4)], fill=leaf, outline=INK)
    draw.polygon([(x, mid+3), (x+5, mid-1), (x+6, mid+1), (x+2, mid+5)], fill=leaf, outline=INK)
    shape = index % 5
    if shape == 0:
        for dx, dy in [(0,-3),(-3,0),(3,0),(-2,3),(2,3)]:
            draw.ellipse((x+dx-2, y+dy-2, x+dx+2, y+dy+2), fill=petal, outline=shadow)
    elif shape == 1:
        draw.ellipse((x-5, y-4, x+5, y+4), fill=petal, outline=shadow)
        draw.line((x-4,y+2,x+4,y+2), fill=shadow)
    elif shape == 2:
        draw.polygon([(x-5,y-3),(x-2,y-2),(x,y-6),(x+2,y-2),(x+5,y-3),(x+4,y+3),(x,y+5),(x-4,y+3)],
                     fill=petal, outline=shadow)
    elif shape == 3:
        draw.polygon([(x,y-7),(x+3,y-3),(x+5,y),(x+3,y+3),(x,y+5),(x-4,y+3),(x-5,y),(x-2,y-3)],
                     fill=petal, outline=shadow)
        draw.line((x,y-5,x-2,y+3), fill=glint)
    else:
        for dx, dy in [(-3,2),(3,1),(0,-3)]:
            draw.ellipse((x+dx-3,y+dy-3,x+dx+3,y+dy+2), fill=petal, outline=shadow)
    draw.ellipse((x-2,y-2,x+2,y+1), fill=glint)
    draw.point((x+1,y), fill=shadow)


def bottle(draw, flask, hue, filled):
    glass, reflection = '#537784', '#c9eff4'
    neck, widest = (4, 12) if flask else (3, 8)
    profile = [(16-neck,7),(16+neck,7),(16+neck,12),(16+widest,19),
               (16+widest,24),(16+widest-4,28),(20-widest,28),(16-widest,24),
               (16-widest,19),(16-neck,12)]
    draw.polygon(profile, fill=glass, outline=INK)
    if filled:
        liquid = color(hue, .66, .92)
        draw.polygon([(18-widest,19),(14,20),(20,18),(14+widest,19),(14+widest,24),
                      (11+widest,26),(21-widest,26),(18-widest,24)], fill=liquid)
        draw.line((19-widest,21,14+widest,21), fill=color(hue,.32,1))
        draw.point((19,24), fill=reflection)
    draw.line([(16-neck+1,9), (16-neck+1,13), (18-widest,20), (18-widest,23)], fill=reflection, width=2)
    draw.rounded_rectangle((14-neck,4,18+neck,8), 1, fill='#9f673f' if filled else reflection, outline=INK)


def frame(kind, value):
    image = Image.new('RGBA', (SIZE, SIZE))
    draw = ImageDraw.Draw(image)
    if kind == 'patch':
        draw.ellipse((2,23,30,30), fill='#23372f', outline='#172823')
        draw.ellipse((5,22,27,27), fill='#385849')
        plant(draw, 8, 15, 26, value)
        plant(draw, 24, 17, 27, value)
        plant(draw, 16, 10, 28, value)
    elif kind == 'flower':
        plant(draw, 20, 12, 28, value)
        plant(draw, 12, 10, 26, value)
    elif kind in ('brew', 'empty'):
        flask, hue = value
        bottle(draw, flask, hue, kind == 'brew')
    else:
        hue = value
        draw.polygon([(5,5),(25,4),(27,8),(24,13),(23,24),(19,28),(5,28),(3,24),(6,19)], fill='#edcf9a', outline=INK)
        for offset in [10, 14, 18]:
            draw.line((9,offset,21-offset//6,offset-1), fill='#a88263', width=2)
        draw.ellipse((17,18,27,28), fill=color(hue,.62,.82), outline=INK)
        draw.ellipse((20,20,24,24), outline=color(hue,.33,1))
    return image


def roster():
    catalog = json.loads((ROOT / 'world/alchemy.txt').read_text())
    flowers = [(f['item'], 'flower', i) for i, f in enumerate(catalog['flowers'])]
    patches = [(f"patch_{f['item']}", 'patch', i) for i, f in enumerate(catalog['flowers'])]
    brews = [(r['item'], 'brew', (r['flask'], STATS[r['stat']] + i * 8)) for i, r in enumerate(catalog['recipes'])]
    formulas = [(r['formula'], 'formula', STATS[r['stat']]) for r in catalog['recipes'] if r.get('formula')]
    containers = [(s['item'], 'empty', (i == 1, 0)) for i, s in enumerate(catalog['supplies'])]
    return flowers + patches + brews + formulas + containers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'export', 'verify'))
    args = parser.parse_args()
    entries = roster()
    pf = pf_api()
    if args.action == 'build' and not SOURCE.exists():
        sources = []
        for offset in range(0, len(entries), 24):
            group = entries[offset:offset + 24]
            name = f'valhallasc_alchemy_{offset//24 + 1}_v1'
            sprite = pf.ids(name).get(name)
            if not sprite:
                pixels = [np.array(frame(kind, value)) for _, kind, value in group]
                palette, colors = palette_of(pixels)
                ops = [dict(op='grid', frame=i, layer=0, x=0, y=0, rows=grid.tolist())
                       for i, grid in enumerate(index_frames(pixels, colors))]
                result = pf.api('create', dict(name=name, width=SIZE, height=SIZE, frames=len(group),
                                               layers=1, fps=1, palette=palette, persist=True, ops=ops))
                if not result.get('ok'):
                    raise RuntimeError(result.get('errors'))
                sprite = result['sprite_id']
            sources.append(dict(sprite=sprite, order=[key for key, _, _ in group]))
        SOURCE.write_text(json.dumps(sources, indent=2) + '\n')

    sources = json.loads(SOURCE.read_text())
    order = [key for source in sources for key in source['order']]
    assert order == [key for key, _, _ in entries]
    rows = math.ceil(len(entries) / COLS)
    atlas = Image.new('RGBA', (SIZE * COLS, SIZE * rows))
    keys = {}
    for source in sources:
        spec, grids = pf.load(source['sprite'])
        assert (spec['width'], spec['height'], len(grids)) == (SIZE, SIZE, len(source['order']))
        for key, data in zip(source['order'], grids, strict=True):
            index = len(keys)
            col, row = index % COLS, index // COLS
            atlas.alpha_composite(Image.fromarray(pf.to_rgba(data[0], spec['palette'])), (col * SIZE, row * SIZE))
            keys[key] = [col, row]
    path = ASSETS / 'alchemy.png'
    if args.action == 'verify':
        assert Image.open(path).convert('RGBA').tobytes() == atlas.tobytes()
    else:
        atlas.save(path, optimize=True)
        metadata = dict(size=SIZE, cols=COLS, rows=rows, at=keys)
        encoded = json.dumps(metadata, separators=(',', ':'))
        (ROOT / 'client/alchemy-art.js').write_text(f"'use strict';\nwindow.ALCHEMY_ART = {encoded};\n")
    print(f'{len(keys)} Alchemy atlas cells from {len(sources)} editable PixelFlow sprites')


if __name__ == '__main__':
    main()
