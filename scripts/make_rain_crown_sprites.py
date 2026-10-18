#!/usr/bin/env python3
"""Editable PixelFlow atlases for the six Rain Crown Temple encounters."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from make_crag_sprites import AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid, polygon, rgba
from rain_crown_content import ENEMIES

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
META = ASSETS / 'cathedral.txt'
KINDS = [e['kind'] for e in ENEMIES]


def palette(enemy):
    rgb = tuple(int(enemy['color'][i:i+2], 16) for i in (1, 3, 5))
    names = {f'c{n}': '#' + ''.join(f'{min(250, round(v * factor)):02x}' for v in rgb)
             for n, factor in enumerate((.28, .48, .68, .88, 1.1))}
    names.update(ink='#174346', gold='#e9e5a5', light='#e4fff2', silk='#b9ead6', shadow='#32646b')
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
    if art == 'droplet':
        # A single rain spirit with a crown of three suspended jade drops.
        for side in (-1, 1):
            oval(side*19, 35+wave*2, 5, 13, p.ramp('c1','c3','light'))
            line((side*12,37),(side*26,27),'gold',2)
        shape([(-19,26),(-16,51),(0,78),(16,51),(19,26),(0,9)],'c2')
        oval(0,43,16,22,bright)
        for x in (-7,7): oval(x,51,3,4,p.ramp('ink','gold','light'))
        for x,y in [(-11,72),(0,78),(11,72)]: oval(x,y,4,7,p.ramp('c2','gold','light'))
    elif art == 'oracle':
        # A veiled jade seer with a crescent canopy and rain staffs.
        for side in (-1,1):
            shape([(side*8,31),(side*28,14),(side*25,69),(side*9,56)],'c2')
            limb((side*15,58),(side*(29+thrust*.2),30),4,2,bright)
            line((side*31,18),(side*31,74),'gold',2)
        shape([(-20,20),(0,8),(20,20),(14,66),(-14,66)],'shadow')
        oval(0,50,15,22,bright)
        shape([(-26,72),(0,80),(26,72),(18,67),(-18,67)],'gold')
        for x in (-7,7): oval(x,57,3,4,p.ramp('ink','gold','light'))
    elif art in ('guard','gatekeeper'):
        # Floodgate stone armour, a broad shield and pronged helm.
        wide=art=='gatekeeper'
        for side in (-1,1):
            limb((side*12,30),(side*17,4),7,4)
            limb((side*17,57),(side*(30+thrust*.1),33),7,4)
            shape([(side*22,32),(side*36,38),(side*32,67),(side*20,59)],'c2')
            shape([(side*11,65),(side*17,84),(side*25,67)],'gold')
        shape([(-22,18),(0,8),(22,18),(25,57),(0,73),(-25,57)],'shadow')
        oval(0,44,22 if wide else 18,27,bright)
        for x in (-8,8): oval(x,58,3,4,p.ramp('ink','gold','light'))
        for y in (29,42): line((-17,y),(17,y+2),'gold',2)
    elif art=='sibyl':
        # A floating oracle surrounded by a fourfold water halo.
        for side in (-1,1):
            shape([(side*10,22),(side*32,15),(side*34,66),(side*10,56)],'c2')
            for y in (28,48,69): oval(side*33,y,5,8,p.ramp('c1','gold','light'))
        shape([(-18,22),(0,7),(18,22),(14,72),(-14,72)],'shadow')
        oval(0,51,14,22,bright)
        for x in (-7,7): oval(x,58,3,5,p.ramp('ink','gold','light'))
        shape([(-20,75),(-10,85),(0,79),(10,85),(20,75)],'gold')
    else:
        # The Rain Crown rises from eight radiating streams.
        for k in range(8):
            angle=math.tau*k/8+wave*.04
            x,y=math.cos(angle),math.sin(angle)
            limb((x*19,45+y*15),(x*37,45+y*32),5,2,p.ramp('c1','c3','gold'))
        for side in (-1,1):
            shape([(side*8,66),(side*18,85),(side*28,68)],'gold')
            limb((side*12,25),(side*18,4),7,4)
        shape([(-23,20),(0,7),(23,20),(24,62),(0,78),(-24,62)],'shadow')
        oval(0,48,22,28,bright)
        oval(0,53,10,13,p.ramp('ink','gold','light'))
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            x, y = at(23+k*4+thrust*.2, 33+(k%2)*8)
            f.dots([(x, y)], 'gold')
    if clip in ('hurt', 'die') and n == 0:
        f.whiten()
    return f.a


# The six enemies are the cel-shaded redraw in rain_crown_cel_redraw.py (2026-10-18); the old drawer stays as `_old_draw`.
import dungeon_cel  # noqa: E402
dungeon_cel.install(globals(), 'rain_crown_cel_redraw')


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
    out = ROOT / 'test-results/rain-crown-preview'
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
        np.savez_compressed(ROOT/f'scripts/{kind}_raw.npz', **frames)
        sid = api('create', {'name': 'valhallasc_rain_crown_'+kind+'_all',
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
        raise SystemExit('Usage: make_rain_crown_sprites.py preview | build | export | verify [kind...]')
