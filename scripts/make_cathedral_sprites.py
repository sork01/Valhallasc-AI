#!/usr/bin/env python3
"""Original Cathedral sprites: preview | build [--replace] | export | verify.

Seventeen 34-frame, 96x96 editable PixelFlow sprites; export preserves edits.
Build refuses existing names. --replace discards ONLY these sprites' editor edits.
"""
import json
import math
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

import cathedral_content as C
from make_crag_sprites import (AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid, polygon, rgba)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
RAW = ROOT / 'scripts'
PREFIX = 'valhallasc_cathedral_'
KINDS = [e['kind'] for e in C.ENEMIES]

def palette(e):
    rgb = tuple(int(e['color'][i:i+2],16) for i in (1,3,5))
    colors = {}
    for n,f in enumerate([.22,.4,.65,.88,1.08]):
        colors['c'+str(n)] = '#'+''.join(f'{min(250,round(v*f)):02x}' for v in rgb)
    colors.update(b0='#362d42',b1='#8f8093',b2='#c7bacb',b3='#ede2e7',
                  gold0='#564026',gold1='#9e783e',gold2='#dfb96d',gold3='#fff0af',
                  eye='#d6fff1',socket='#0c1828',weed='#27514b',chain='#6b798e',water='#6ce0df',white='#f5f4fb')
    return Palette(colors)

PALETTES = {e['kind']:palette(e) for e in C.ENEMIES}

def draw(e,clip,n):
    p=PALETTES[e['kind']]; f=Frame(p); art=e['art']; boss=e['boss']
    sw=math.sin(n*math.pi/4); lean=0; lift=math.sin(n*math.pi/3)*1.1
    if clip=='walk': lean=sw*2; lift=abs(sw)*4
    if clip=='attack': lean=[-2,-4,-5,3,8,6,2,0][n]; lift=[0,1,2,3,1,0,0,0][n]
    if clip=='hurt': lean=[-5,-3,-1,0][n]
    death=([0,.08,.18,.35,.56,.75,.9,1][n] if clip=='die' else 0)
    ground=86
    def at(x,y): return (46+x+lean*y/60,ground-y*.9*(1-death*.8)-lift+death*2)
    ramp=p.ramp('c0','c1','c2','c3','c4'); bone=p.ramp('b0','b1','b2','b3'); gold=p.ramp('gold0','gold1','gold2','gold3')
    def blob(x,y,rx,ry,r=ramp):
        xx,yy=at(x,y); f.paint(ellipsoid(xx,yy,rx*(1+death*.3),max(1,ry*(1-death*.65))),r,dither=.4)
    def limb(a,b,r=3,r2=2,colors=ramp): f.paint(capsule(at(*a),at(*b),r,r2),colors,dither=.45)
    def poly(pts,color='c2'): f.flat(polygon([at(*xy) for xy in pts]),color,outline=True)
    def line(a,b,color='gold2',width=1): f.line(at(*a),at(*b),color,width)
    def eyes(x,y,wide=3):
        for dx in (-wide,wide):
            blob(x+dx,y,2.2,2.8,p.ramp('socket','socket','socket'))
            if death<.5:
                line((x+dx-1,y),(x+dx+1,y),'eye',1 if (clip=='idle' and n==3) else 2)
    if art=='leech':
        for k in range(9):
            x=-24+k*6; y=8+math.sin(k*.6+n*.7)*3+k*.6
            blob(x,y,6,5)
        blob(25,18,9,10); eyes(29,20,2)
        poly([(30,16),(35,14),(33,9),(28,10)],'socket')
        for k in range(3): line((29+k*2,14),(30+k*2,11),'b3')
    elif art in ('crab','spider'):
        spider=art=='spider'
        for side in (-1,1):
            for k in range(4 if spider else 3):
                a=(side*9,20+k*3); b=(side*(25+k),13+k*5+sw*2); c=(side*(32-k),3+k*3)
                limb(a,b,2.5,2); limb(b,c,2,1.3)
        blob(-4,27,18 if spider else 24,17 if spider else 13)
        blob(13,23,9,9); eyes(17,26,3)
        for side in (-1,1):
            limb((side*16,26),(side*27,36+lean*.5),4,3)
            blob(side*29,38+lean*.5,5.5,7,gold if boss else ramp)
            line((side*29,37),(side*29,43),'c0',2)
        if boss:
            for x in [-12,-5,2,9]: blob(x,40,3,3,bone)
            poly([(-9,44),(-10,55),(-4,49),(1,59),(6,49),(12,55),(10,44)],'gold2')
    elif art=='root':
        for side in (-1,1):
            limb((side*8,25),(side*22,3),6,2)
            limb((side*13,43),(side*27,29+lean),6,4)
            limb((side*27,29+lean),(side*32,17+lean),4,2)
            limb((side*10,58),(side*19,71),3,1)
        blob(0,35,16,24); blob(0,60,12,13); eyes(3,61,4)
        for k in range(5): line((-9+k*4,53),(-13+k*4,9),'weed',2)
        poly([(-9,69),(-11,78),(-5,74),(0,83),(6,73),(10,79),(11,69)],'gold1')
    else:
        robe=art in ('cantor','choir','glass','regent','seraph','hierophant','judge')
        for side in (-1,1):
            stride=sw*4*side if clip=='walk' else 0
            limb((side*7,24),(side*9+stride,8),3.5,3,bone)
            blob(side*9+stride,5,6,3.5)
        if art=='seraph':
            for side in (-1,1):
                for k in range(5):
                    poly([(side*8,52-k*2),(side*(27+k*2),73-k*8+sw*2),(side*(25+k*2),52-k*6)],'b2' if k%2 else 'c3')
        if art=='choir':
            for side in (-1,1):
                blob(side*23,51,6,8,bone); eyes(side*23+2,53,1.8)
                poly([(side*23-5,44),(side*23+5,44),(side*23+8,27),(side*23-8,27)],'c1')
                line((side*23,42),(side*23,30),'chain',2)
        blob(0,38,12 if robe else 15,16)
        if robe:
            poly([(-11,44),(10,44),(16+sw,8),(-15+sw,8)],'c2')
            for x in [-8,0,8]: line((x,40),(x+sw*2,10),'c1' if x else 'gold2',2)
        else:
            for x in [-9,0,9]: line((x,46),(x,29),'gold1',2)
            blob(0,35,6,5,gold)
        # Far arm, near arm and carried objects, each archetype has a readable silhouette.
        armY=30+lean*1.3
        limb((-10,47),(-22,30),4,3)
        limb((10,47),(23,armY),4,3)
        blob(23,armY,4,4,bone)
        if art in ('knight','chain'):
            poly([(-22,41),(-11,39),(-13,22),(-22,17),(-29,29)],'c3')
            line((-22,36),(-22,22),'gold2',2)
            line((24,armY-11),(27+lean,armY+23),'b3',3)
            line((20,armY),(30,armY),'gold2',2)
        elif art=='bell':
            poly([(21,armY+8),(29,armY+8),(34,armY-7),(16,armY-7)],'gold2')
            blob(25,armY-9,9,3,gold); line((25,armY+9),(25,armY+17),'chain',3)
        elif art=='judge':
            line((22,armY-12),(25,armY+22),'gold1',3)
            blob(25,armY+22,11,6,bone)
            line((-8,61),(12,61),'gold1',3)
        elif art=='glass':
            for k in range(5):
                x=-24+k*12; y=70+math.sin(n*.7+k)*2
                poly([(x,y+6),(x+3,y),(x,y-6),(x-3,y)],'c4')
            line((24,armY-14),(25,armY+20),'gold2',2)
            blob(25,armY+22,5,6)
        else:
            line((24,armY-15),(25,armY+24),'gold1',2)
            blob(25,armY+24,5,5,gold)
            blob(25,armY+25,2,3,p.ramp('eye','water','white'))
        # The bishop's headpiece, coral queen's antlers, marshal's chains and blind judge are distinct.
        blob(1,59,9,10,bone); eyes(4,61,3)
        if art in ('hierophant','cantor'):
            poly([(-10,62),(-10,73),(0,82 if boss else 76),(11,72),(12,62),(7,67),(-5,67)],'c3')
            line((0,74),(0,67),'gold2',2)
        if art in ('regent','chain','bell'):
            for side in (-1,1):
                limb((side*7,68),(side*15,77),2.5,1.5,gold)
                if art=='regent': limb((side*13,75),(side*19,72),1.5,1,gold)
        if art=='chain':
            for k in range(9):
                xx=-21+math.sin(k*.5)*5; yy=44-k*4
                blob(xx,yy,2.4,3,p.ramp('chain','b1','b2'))
        if art=='seraph':
            # Sun halo floats behind the brow, broken on the fallen side.
            for k in range(9):
                a=k*math.pi/6
                blob(math.cos(a)*13,61+math.sin(a)*15,1.7,1.7,gold)
        if art=='judge': line((-8,61),(12,61),'c0',4)
        if e['variant']:
            poly([(-10,67),(-15-e['variant'],50),(-12,38)],'c1')
            for k in range(e['variant']): blob(-7+k*4,48,1.5,2,gold)
    if clip=='attack' and n in (3,4,5):
        for k in range(5):
            xx,yy=at(27+math.cos(k*.7)*8,30+math.sin(k*.7)*10)
            f.dots([(xx,yy)],'water' if not boss else 'gold3')
    if death>.5:
        for k in range(6):
            blob(-18+k*7,3+(k%2)*2,2,1.5,p.ramp('water','c3','eye'))
    if clip in ('hurt','die') and n==0: f.whiten()
    return f.a

def build_drawers():
    return {e['kind']:(lambda clip,n,e=e:draw(e,clip,n),PALETTES[e['kind']]) for e in C.ENEMIES}


def render(kind):
    draw, _ = build_drawers()[kind]
    return {clip: np.array([draw(clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def bounds_report(kind, frames):
    """Every frame's bounding box against the canvas edges: nothing may touch them."""
    bad = []
    for clip, grids in frames.items():
        for n, grid in enumerate(grids):
            ys, xs = np.nonzero(grid)
            if len(xs) and (xs.min() < 1 or ys.min() < 1 or xs.max() > W - 2 or ys.max() > H - 2):
                bad.append(f'{clip} {n}: x {xs.min()}-{xs.max()}, y {ys.min()}-{ys.max()}')
    return bad


def preview(kinds, out, scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames = render(kind)
        palette = build_drawers()[kind][1].hex
        for problem in bounds_report(kind, frames):
            print(f'  EDGE {kind} {problem}')
        for clip, grids in frames.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#262a36')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def ids():
    meta = ASSETS / 'cathedral.txt'
    return json.loads(meta.read_text()).get('sprites', {}) if meta.exists() else {}


def build(kinds, replace=False):
    meta_path = ASSETS / 'cathedral.txt'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    known = meta.get('sprites', {})
    clash = [k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist (ids in cathedral.txt). Use export to preserve edits; --replace discards them.')
    for kind in clash:
        api('delete', {'sprite_id': known[kind]})
    made = {}
    for kind in kinds:
        frames = render(kind)
        bad = bounds_report(kind, frames)
        if bad:
            raise SystemExit(f'{kind} touches the canvas edge: {bad}')
        palette = build_drawers()[kind][1].hex
        np.savez_compressed(RAW / f'cathedral_{kind}_raw.npz', **frames)
        sid = api('create', {'name': PREFIX + kind + '_all', 'width': W, 'height': H,
                            'frames': sum(count for _, count in CLIPS.values()),
                            'layers': 1, 'fps': 10, 'palette': palette, 'persist': True,
                            'ops': [{'op': 'set_layer', 'layer': 0, 'name': kind}]})['sprite_id']
        made[kind] = sid
        offset = 0
        try:
            for clip, (_, count) in CLIPS.items():
                for n, grid in enumerate(frames[clip]):
                    api('draw', {'sprite_id': sid, 'frame': offset + n, 'ops': [{'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
                offset += count
            print(kind, sid, f'{offset} frames')
        except Exception:
            api('delete', {'sprite_id': sid})
            raise
        # keep a manifest as we go: `list` only shows the newest 100 sprites
        meta['sprites'] = {**meta.get('sprites', {}), **made}
        meta_path.write_text(json.dumps(meta, indent=2) + '\n')


def export(kinds):
    meta_path = ASSETS / 'cathedral.txt'
    meta = json.loads(meta_path.read_text())
    saved = meta['sprites']
    tops = meta.get('tops', {})
    clips = {}
    for kind in kinds:
        packet = api('get?sprite_id=' + saved[kind])
        sp = packet.get('sprite', packet)
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
        atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
        offset = 0
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            sheet = Image.new('RGBA', (8 * W, H), '#262a36')
            for n in range(count):
                cel = sp['frames'][offset + n]['cels'][0]
                if 'rle' in cel:
                    runs = cel['rle']
                    grid = np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
                else:
                    grid = np.array(cel['grid'], dtype=np.uint8)
                image = rgba(grid, sp['palette'])
                atlas.alpha_composite(image, (n * W, row * H))
                sheet.alpha_composite(image, (n * W, 0))
            clips[clip] = {'fps': fps, 'n': count, 'row': row, 'editorStart': offset}
            offset += count
            dest = ROOT / 'test-results/cathedral-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'cathedral_{kind}.png', optimize=True)
        tops[kind] = AY - atlas.crop((0, 0, 6 * W, H)).getbbox()[1]
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': saved, 'tops': tops}
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/cathedral_<kind>.png and cathedral.txt')


def verify(kinds):
    """The exported atlas must equal the freshly rendered frames pixel for pixel."""
    for kind in kinds:
        frames = render(kind)
        palette = build_drawers()[kind][1].hex
        atlas = Image.open(ASSETS / f'cathedral_{kind}.png').convert('RGBA')
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * W, row * H, (n + 1) * W, (row + 1) * H))
                if np.array(cell).tobytes() != np.array(rgba(frames[clip][n], palette)).tobytes():
                    raise SystemExit(f'{kind} {clip} {n} differs from the render')
        print(kind, 'atlas is pixel-identical to the render')


if __name__ == '__main__':
    drawers = build_drawers()
    for _kind, _pair in drawers.items():
        assert len(_pair[1].hex) <= 255
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    names = [a for a in sys.argv[2:] if a in drawers] or list(drawers)
    if command == 'build':
        build(names, '--replace' in sys.argv)
    elif command == 'export':
        export(names)
    elif command == 'verify':
        verify(names)
    elif command == 'preview':
        directory = next((a for a in sys.argv[2:] if a not in drawers and not a.startswith('--')), ROOT / 'test-results/cathedral-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_cathedral_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...] | verify [kind...]')
