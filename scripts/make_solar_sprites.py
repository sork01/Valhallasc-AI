#!/usr/bin/env python3
"""Editable PixelFlow atlases for the Solar Crucible."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from make_crag_sprites import AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid, polygon, rgba
from solar_crucible_content import ENEMIES

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
META = ASSETS / 'cathedral.txt'
KINDS = [e['kind'] for e in ENEMIES]


def palette(enemy):
    rgb = tuple(int(enemy['color'][i:i+2], 16) for i in (1, 3, 5))
    names = {f'c{n}': '#' + ''.join(f'{min(250, round(v * factor)):02x}' for v in rgb)
             for n, factor in enumerate((.28, .48, .68, .88, 1.1))}
    names.update(ink='#4a2430', gold='#ffe59c', light='#fff8d1', silk='#f6b973', shadow='#6d3540')
    return Palette(names)


PALETTES = {e['kind']: palette(e) for e in ENEMIES}


def draw(enemy, clip, n):
    p = PALETTES[enemy['kind']]
    f = Frame(p)
    wave = math.sin(n * math.pi / 4)
    sway = wave * (3 if clip == 'walk' else 1)
    thrust = (0, 1, 3, 8, 12, 9, 4, 0)[n] if clip == 'attack' else 0
    collapse = (0, .05, .13, .24, .40, .58, .78, .94)[n] if clip == 'die' else 0
    if clip == 'hurt': sway -= (4, 3, 1, 0)[n]
    def at(x, y):
        return (48 + x + sway * y / 48 + thrust * y / 120,
                89 - y * (1 - collapse * .83) - abs(wave) * (2 if clip == 'walk' else .4))
    ramp = p.ramp('c0', 'c1', 'c2', 'c3', 'c4')
    bright = p.ramp('c1', 'c2', 'c3', 'c4')
    def oval(x,y,rx,ry,colors=ramp):
        xx,yy=at(x,y)
        f.paint(ellipsoid(xx,yy,rx*(1+collapse*.2),max(1,ry*(1-collapse*.7))),colors,dither=.3)
    def limb(a,b,width=3,tip=1.5,colors=ramp): f.paint(capsule(at(*a),at(*b),width,tip),colors,dither=.3)
    def shape(points,color): f.flat(polygon([at(x,y) for x,y in points]),color,outline=True)
    def line(a,b,color='gold',width=2): f.line(at(*a),at(*b),color,width)
    art=enemy['art']
    if art=='emberling':
        # A dancing coal held up by flame tongues and two little cinder legs.
        for side in (-1,1):
            shape([(side*8,30),(side*26,48),(side*19,57),(side*5,42)],'c3')
            shape([(side*4,25),(side*13,4),(side*20,9),(side*8,29)],'c2')
        shape([(-18,47),(-11,65),(-4,59),(0,81),(7,60),(18,50),(13,28)],'gold')
        oval(0,38,16,20,bright)
        oval(0,42,8,10,p.ramp('c1','gold','light'))
    elif art=='sunmoth':
        # Solar wings have pointed rays and dark eclipse spots.
        for side in (-1,1):
            shape([(side*5,47),(side*37,79),(side*32,49),(side*9,32)],'gold')
            shape([(side*8,32),(side*37,28),(side*27,9),(side*4,21)],'c3')
            oval(side*25,51,5,8,p.ramp('c1','shadow','gold'))
        oval(0,45,7,22,bright)
        oval(0,67,10,9,p.ramp('c1','c3','gold'))
        for side in (-1,1):limb((side*3,71),(side*10,83),2,1)
    elif art=='guard':
        # A dark iron sentinel with a molten visor and heavy hammer arms.
        for side in (-1,1):
            limb((side*14,28),(side*18,5),7,4)
            limb((side*16,54),(side*(29+thrust*.2),29),8,4)
            shape([(side*11,62),(side*29,69),(side*28,49)],'shadow')
        shape([(-23,17),(0,9),(23,17),(25,59),(0,74),(-25,59)],'shadow')
        oval(0,43,20,27,bright)
        shape([(-13,54),(13,54),(9,61),(-9,61)],'gold')
        oval(0,46,6,8,p.ramp('c1','gold','light'))
    elif art=='ashwarden':
        # Broad cinder armour with a forked furnace crown.
        for side in (-1,1):
            limb((side*12,42),(side*31,22),7,3)
            shape([(side*22,25),(side*37,8),(side*31,31)],'shadow')
            limb((side*10,23),(side*17,3),8,4)
            shape([(side*7,65),(side*24,83),(side*20,62)],'c2')
        oval(0,43,24,29,bright)
        for x in (-17,0,17):shape([(x-5,68),(x,84),(x+5,68)],'gold')
        oval(0,50,9,12,p.ramp('c1','gold','light'))
    elif art=='heliomancer':
        # A ringed sun disc floats over a thin flame staff.
        for side in (-1,1):
            shape([(side*6,49),(side*34,73),(side*28,26),(side*6,32)],'gold')
            line((side*12,48),(side*29,59),'light')
            limb((side*8,29),(side*20,5),4,2)
        shape([(-11,53),(0,84),(11,53),(0,28)],'c3')
        oval(0,52,12,23,p.ramp('c1','gold','light'))
        oval(0,52,5,13,p.ramp('shadow','c2','gold'))
    else:
        # The final core is a starburst inside an iron crucible.
        for side in (-1,1):
            shape([(side*12,25),(side*37,45),(side*29,69),(side*8,59)],'shadow')
            limb((side*13,40),(side*(29+thrust*.2),17),5,2)
            line((side*17,68),(side*23,81),'light',3)
        oval(0,46,24,29,bright)
        oval(0,46,15,20,p.ramp('c1','gold','light'))
        oval(0,46,7,11,p.ramp('c2','c4','light'))
        for x in (-19,0,19):shape([(x-6,72),(x,84),(x+6,72)],'gold')
    if clip in ('hurt','die') and n==0: f.whiten()
    return f.a


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
    out = ROOT / 'test-results/solar-foes-preview'
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
        sid = api('create', {'name': 'valhallasc_'+kind+'_all',
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
        raise SystemExit('Usage: make_blooming_sprites.py preview | build | export | verify [kind...]')
