#!/usr/bin/env python3
"""Editable PixelFlow atlases for the Sunken Astrolabe and Thunderheart Gate."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from make_crag_sprites import AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid, polygon, rgba
from sunken_astrolabe_content import ENEMIES as ASTRO
from thunderheart_gate_content import ENEMIES as THUNDER
ENEMIES = ASTRO + THUNDER

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
    if art in ('gearling','spark'):
        # Small toothed brass wheel or a branching bolt around a bright core.
        for side in (-1,1):
            if art=='gearling':
                shape([(side*8,46),(side*27,61),(side*32,49),(side*14,36)],'gold')
                limb((side*11,22),(side*23,4),4,2)
            else:
                shape([(side*3,50),(side*28,75),(side*17,49),(side*32,31),(side*8,36)],'light')
                line((side*8,29),(side*24,9),'gold',3)
        oval(0,39,17,22,bright)
        oval(0,39,8,12,p.ramp('c1','gold','light'))
        for x in (-7,7): oval(x,50,2,3,p.ramp('ink','gold','light'))
    elif art in ('starling','ray'):
        for side in (-1,1):
            shape([(side*4,46),(side*37,70),(side*33,45),(side*13,26)],'c2')
            shape([(side*8,29),(side*38,25),(side*21,12),(side*6,19)],'gold')
            line((side*12,62),(side*32,42),'light',2)
        oval(0,42,9,22,bright)
        oval(0,63,12,10,p.ramp('c1','c3','gold'))
        for x in (-5,5): oval(x,65,2,3,p.ramp('ink','gold','light'))
    elif art in ('sentinel','guard','warden','bastion'):
        big=art in ('warden','bastion')
        for side in (-1,1):
            limb((side*11,29),(side*18,4),7 if big else 6,3)
            limb((side*16,59),(side*(28+thrust*.2),24),8 if big else 6,3)
            shape([(side*11,70),(side*28,78),(side*26,58)],'c3')
            line((side*18,20),(side*20,65),'gold',2)
        shape([(-22,17),(0,8),(22,17),(25,65),(0,77),(-25,65)],'shadow')
        oval(0,46,23 if big else 19,27,bright)
        oval(0,55,10,13,p.ramp('c1','gold','light'))
        for x in (-8,8): oval(x,62,3,3,p.ramp('ink','gold','light'))
        if big:
            for x in (-19,0,19): oval(x,78,5,6,p.ramp('c2','gold','light'))
    elif art in ('navigator','conductor'):
        for side in (-1,1):
            shape([(side*10,23),(side*35,31),(side*30,75),(side*9,64)],'c2')
            limb((side*12,44),(side*(27+thrust*.3),20),4,2)
            oval(side*30,50,6,9,p.ramp('c2','gold','light'))
        shape([(-18,14),(0,8),(18,14),(14,69),(-14,69)],'shadow')
        oval(0,51,15,22,bright)
        shape([(-18,76),(0,85),(18,76),(0,80)],'gold')
        for x in (-6,6): oval(x,59,3,4,p.ramp('ink','gold','light'))
    else: # The axial astrolabe and the living heart are circular, crowned final bosses.
        for side in (-1,1):
            shape([(side*9,24),(side*31,39),(side*25,71),(side*11,68)],'c2')
            limb((side*12,48),(side*(30+thrust*.2),24),5,2)
            line((side*20,70),(side*26,84),'light',3)
        oval(0,46,25,29,bright)
        oval(0,46,16,20,p.ramp('c1','gold','light'))
        oval(0,46,7,10,p.ramp('c2','c4','light'))
        for x in (-19,0,19):
            shape([(x-6,73),(x,82),(x+6,73)],'gold')
        line((-29,46),(29,46),'ink',2)
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
    out = ROOT / 'test-results/astrolabe-foes-preview'
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
        raise SystemExit('Usage: make_astrolabe_sprites.py preview | build | export | verify [kind...]')
