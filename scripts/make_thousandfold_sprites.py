#!/usr/bin/env python3
"""Editable PixelFlow atlases for the six Thousandfold Pavilion encounters."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from make_crag_sprites import AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid, polygon, rgba
from thousandfold_content import ENEMIES

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
META = ASSETS / 'cathedral.txt'
KINDS = [e['kind'] for e in ENEMIES]


def palette(enemy):
    rgb = tuple(int(enemy['color'][i:i+2], 16) for i in (1, 3, 5))
    names = {f'c{n}': '#' + ''.join(f'{min(250, round(v * factor)):02x}' for v in rgb)
             for n, factor in enumerate((.28, .48, .68, .88, 1.1))}
    names.update(ink='#292842', gold='#f6d592', light='#fff1db', silk='#eee4e6', shadow='#695177')
    return Palette(names)


PALETTES = {e['kind']: palette(e) for e in ENEMIES}


def draw(enemy, clip, n):
    p = PALETTES[enemy['kind']]
    f = Frame(p)
    wave = math.sin(n * math.pi / 4)
    sway = wave * (3 if clip == 'walk' else 1)
    thrust = (0, 1, 3, 8, 12, 9, 4, 0)[n] if clip == 'attack' else 0
    collapse = (0, .05, .13, .24, .40, .58, .78, .94)[n] if clip == 'die' else 0
    if clip == 'hurt':
        sway -= (4, 3, 1, 0)[n]

    def at(x, y):
        return (48 + x + sway * y / 48 + thrust * y / 120,
                89 - y * (1 - collapse * .83) - abs(wave) * (2 if clip == 'walk' else .4))

    ramp = p.ramp('c0', 'c1', 'c2', 'c3', 'c4')
    bright = p.ramp('c1', 'c2', 'c3', 'c4')

    def oval(x, y, rx, ry, colors=ramp):
        xx, yy = at(x, y)
        f.paint(ellipsoid(xx, yy, rx * (1 + collapse * .2), max(1, ry * (1 - collapse * .7))),
                colors, dither=.3)

    def limb(a, b, width=3, tip=1.5, colors=ramp):
        f.paint(capsule(at(*a), at(*b), width, tip), colors, dither=.3)

    def shape(points, color):
        f.flat(polygon([at(x, y) for x, y in points]), color, outline=True)

    def line(a, b, color='gold', width=2):
        f.line(at(*a), at(*b), color, width)

    art = enemy['art']
    if art == 'foldling':
        # A hopping origami creature: long creased ears and a blade folded from its back.
        for side in (-1, 1):
            shape([(side*7, 48), (side*26, 78), (side*18, 43)], 'c3')
            shape([(side*12, 26), (side*24, 5), (side*4, 20)], 'c2')
            shape([(side*12, 57), (side*32, 53), (side*15, 42)], 'silk')
        shape([(-18, 24), (0, 12), (18, 24), (19, 52), (0, 68), (-19, 52)], 'c3')
        oval(0, 49, 14, 14, bright)
        for x in (-7, 7):
            oval(x, 53, 3, 3, p.ramp('ink', 'gold', 'light'))
        line((-17, 26), (19, 51), 'shadow', 2)
    elif art == 'inkmoth':
        # Ink-dark wings carry bright calligraphic loops.
        for side in (-1, 1):
            shape([(side*6, 49), (side*32, 78+wave*2), (side*37, 43), (side*13, 21)], 'ink')
            oval(side*25, 54, 8, 16, p.ramp('c1', 'c2', 'c3'))
            oval(side*26, 55, 3, 6, p.ramp('gold', 'silk', 'light'))
            line((side*6, 66), (side*16, 83), 'gold', 2)
        oval(0, 43, 9, 23)
        oval(0, 64, 12, 11, bright)
        for x in (-6, 6):
            oval(x, 65, 3, 3, p.ramp('ink', 'gold', 'light'))
        for x in (-9, 0, 9):
            line((x, 26), (x+wave*3, 8), 'c3', 2)
    elif art == 'silkguard':
        # A loom-built sentinel with shuttle arms and a broad woven shield.
        for side in (-1, 1):
            limb((side*11, 27), (side*18, 4), 7, 4)
            limb((side*18, 58), (side*(29+thrust*.1), 35), 7, 4)
            shape([(side*21, 34), (side*34, 40), (side*31, 55), (side*20, 54)], 'silk')
        shape([(-20, 16), (-23, 53), (-11, 75), (11, 75), (23, 53), (20, 16)], 'shadow')
        oval(0, 47, 19, 27, bright)
        for x in (-8, 8):
            oval(x, 58, 3, 4, p.ramp('ink', 'gold', 'light'))
        for y in (28, 39, 50):
            line((-17, y), (17, y+2), 'silk', 2)
    elif art == 'mirror':
        # Dancing glass panels fan around an angled central mask.
        for side in (-1, 1):
            shape([(side*8, 20), (side*32, 9), (side*29, 60), (side*11, 50)], 'c2')
            shape([(side*9, 49), (side*35, 76), (side*28, 40)], 'silk')
            limb((side*11, 54), (side*(31+thrust*.13), 35), 4, 2, bright)
        shape([(-16, 30), (0, 13), (16, 30), (13, 69), (0, 82), (-13, 69)], 'shadow')
        oval(0, 56, 13, 17, bright)
        for x in (-7, 7):
            oval(x, 58, 3, 5, p.ramp('ink', 'gold', 'light'))
        line((-13, 37), (13, 69), 'light', 2)
    elif art == 'weaver':
        # Six silk spindles circle a suspended spindle-shaped caster.
        for side in (-1, 1):
            for y in (24, 43, 62):
                limb((side*12, y+5), (side*35, y-5+wave*2), 4, 2, bright)
                oval(side*35, y-5, 4, 6, p.ramp('c1', 'gold', 'light'))
            shape([(side*7, 53), (side*25, 78), (side*18, 42)], 'silk')
        shape([(-17, 25), (0, 7), (17, 25), (13, 69), (0, 81), (-13, 69)], 'c2')
        oval(0, 55, 14, 20, bright)
        for x in (-7, 7):
            oval(x, 58, 3, 4, p.ramp('ink', 'gold', 'light'))
    else:
        # A huge crowned figure unfolds into eight radiant paper blades.
        for k in range(8):
            angle = math.tau*k/8 + wave*.04
            x, y = math.cos(angle), math.sin(angle)
            limb((x*19, 46+y*16), (x*37, 46+y*33), 5, 2,
                 p.ramp('shadow', 'c2', 'gold'))
        for side in (-1, 1):
            shape([(side*5, 66), (side*16, 84), (side*25, 64)], 'gold')
            limb((side*11, 25), (side*17, 4), 7, 4)
        shape([(-22, 22), (0, 8), (22, 22), (25, 60), (0, 77), (-25, 60)], 'shadow')
        oval(0, 48, 21, 27, bright)
        oval(0, 53, 9, 13, p.ramp('ink', 'gold', 'light'))
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            x, y = at(23+k*4+thrust*.2, 33+(k%2)*8)
            f.dots([(x, y)], 'gold')
    if clip in ('hurt', 'die') and n == 0:
        f.whiten()
    return f.a


# The six enemies are the cel-shaded redraw in thousandfold_cel_redraw.py (2026-10-18); the old drawer stays as `_old_draw`.
import dungeon_cel  # noqa: E402
dungeon_cel.install(globals(), 'thousandfold_cel_redraw')


def render(kind):
    enemy = next(e for e in ENEMIES if e['kind'] == kind)
    return {clip: np.stack([draw(enemy, clip, n) for n in range(count)])
            for clip, (_, count) in CLIPS.items()}


def bounds(frames):
    bad = []
    for clip, rows in frames.items():
        for n, grid in enumerate(rows):
            yy, xx = np.nonzero(grid)
            if len(xx) and (xx.min() < 1 or yy.min() < 1 or xx.max() > W-2 or yy.max() > H-2):
                bad.append(f'{clip} {n}: x {xx.min()}-{xx.max()}, y {yy.min()}-{yy.max()}')
    return bad


def preview(kinds):
    out = ROOT / 'test-results/thousandfold-preview'
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames = render(kind)
        assert not bounds(frames), (kind, bounds(frames))
        sheet = Image.new('RGBA', (W*6, H*5), '#201b31')
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(min(count, 6)):
                sheet.alpha_composite(rgba(frames[clip][n], PALETTES[kind].hex), (n*W, row*H))
        target = out / f'{kind}.png'
        sheet.resize((W*12, H*10), Image.Resampling.NEAREST).save(target)
        print(target)


def build(kinds):
    meta = json.loads(META.read_text())
    if any(k in meta['sprites'] for k in kinds):
        raise SystemExit('Sprites already exist; export preserves PixelFlow edits.')
    for kind in kinds:
        frames = render(kind)
        assert not bounds(frames), (kind, bounds(frames))
        np.savez_compressed(ROOT/f'scripts/thousandfold_{kind}_raw.npz', **frames)
        sid = api('create', {'name': 'valhallasc_thousandfold_'+kind+'_all',
                             'width': W, 'height': H, 'frames': 34, 'layers': 1,
                             'fps': 10, 'palette': PALETTES[kind].hex, 'persist': True,
                             'ops': [{'op': 'set_layer', 'layer': 0, 'name': kind}]})['sprite_id']
        offset = 0
        try:
            for clip, (_, count) in CLIPS.items():
                for n, grid in enumerate(frames[clip]):
                    api('draw', {'sprite_id': sid, 'frame': offset+n,
                                 'ops': [{'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
                offset += count
        except Exception:
            api('delete', {'sprite_id': sid})
            raise
        meta['sprites'][kind] = sid
        META.write_text(json.dumps(meta, indent=2)+'\n')
        print(kind, sid, '34 editable frames', flush=True)


def export(kinds):
    meta = json.loads(META.read_text())
    for kind in kinds:
        packet = api('get?sprite_id='+meta['sprites'][kind])
        sp = packet.get('sprite', packet)
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, 34)
        atlas = Image.new('RGBA', (8*W, 5*H))
        offset = 0
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cel = sp['frames'][offset+n]['cels'][0]
                if 'rle' in cel:
                    runs = cel['rle']
                    grid = np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
                else:
                    grid = np.array(cel['grid'], dtype=np.uint8)
                atlas.alpha_composite(rgba(grid, sp['palette']), (n*W, row*H))
            meta['clips'][clip] = {'fps': fps, 'n': count, 'row': row, 'editorStart': offset}
            offset += count
        atlas.save(ASSETS/f'cathedral_{kind}.png', optimize=True)
        meta['tops'][kind] = AY-atlas.crop((0, 0, 6*W, H)).getbbox()[1]
        if kind not in meta['kinds']:
            meta['kinds'].append(kind)
        META.write_text(json.dumps(meta, indent=2)+'\n')
        print(ASSETS/f'cathedral_{kind}.png')


def verify(kinds):
    meta = json.loads(META.read_text())
    for kind in kinds:
        frames = render(kind)
        assert not bounds(frames), (kind, bounds(frames))
        atlas = Image.open(ASSETS/f'cathedral_{kind}.png').convert('RGBA')
        assert atlas.size == (8*W, 5*H)
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                expected = rgba(frames[clip][n], PALETTES[kind].hex)
                actual = atlas.crop((n*W, row*H, (n+1)*W, (row+1)*H))
                assert np.array_equal(np.array(expected), np.array(actual)), (kind, clip, n)
        assert kind in meta['sprites'] and kind in meta['kinds']
        print(kind, '34 frames match indexed source')


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else ''
    kinds = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action == 'preview':
        preview(kinds)
    elif action == 'build':
        build(kinds)
    elif action == 'export':
        export(kinds)
    elif action == 'verify':
        verify(kinds)
    else:
        raise SystemExit('Usage: make_thousandfold_sprites.py preview | build | export | verify [kind...]')
