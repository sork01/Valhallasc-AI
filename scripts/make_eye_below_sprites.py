#!/usr/bin/env python3
"""Original Eye Below enemies: preview | build [--replace] | export | verify.

Each 96x96, 34-frame sprite remains editable in PixelFlow. The shared
cathedral atlas contract lets the existing client animator drive every clip.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from eye_below_content import ENEMIES
from make_crag_sprites import AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid, polygon, rgba

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
META = ASSETS / 'cathedral.txt'
KINDS = [e['kind'] for e in ENEMIES]
PREFIX = 'valhallasc_eye_below_'


def palette(enemy):
    rgb = tuple(int(enemy['color'][i:i+2], 16) for i in (1, 3, 5))
    names = {}
    for n, factor in enumerate((.26, .45, .67, .86, 1.08)):
        names[f'c{n}'] = '#' + ''.join(f'{min(250, round(v*factor)):02x}' for v in rgb)
    names.update(iris='#f3dfaa', pupil='#102439', white='#d9f6ed', metal='#8d9da0',
                 coral='#c88774', glow='#76f1dc', shadow='#252b42')
    return Palette(names)


PALETTES = {e['kind']: palette(e) for e in ENEMIES}


def draw(enemy, clip, n):
    p = PALETTES[enemy['kind']]
    f = Frame(p)
    art = enemy['art']
    wave = math.sin(n * math.pi / 4)
    sway = wave * (3 if clip == 'walk' else 1.2)
    thrust = (0, 1, 3, 8, 12, 9, 4, 0)[n] if clip == 'attack' else 0
    collapse = (0, .05, .13, .24, .40, .58, .78, .94)[n] if clip == 'die' else 0
    if clip == 'hurt': sway -= (4, 3, 1, 0)[n]

    def at(x, y):
        return (48 + x + sway * y / 48 + thrust * y / 100,
                89 - y * (1 - collapse * .83) - abs(wave) * (2 if clip == 'walk' else .5))

    ramp = p.ramp('c0', 'c1', 'c2', 'c3', 'c4')
    bright = p.ramp('c1', 'c2', 'c3', 'c4')
    def oval(x, y, rx, ry, colors=ramp):
        xx, yy = at(x, y)
        f.paint(ellipsoid(xx, yy, rx * (1 + collapse*.25), max(1, ry * (1-collapse*.7))), colors, dither=.32)
    def limb(a, b, wide=3, thin=2, colors=ramp):
        f.paint(capsule(at(*a), at(*b), wide, thin), colors, dither=.35)
    def shape(points, color):
        f.flat(polygon([at(x, y) for x, y in points]), color, outline=True)
    def line(a, b, color='c4', width=2):
        f.line(at(*a), at(*b), color, width)
    def eye(x, y, rx=9, ry=6):
        oval(x, y, rx+2, ry+2, p.ramp('c1', 'c2', 'c3'))
        oval(x+1, y, rx, ry, p.ramp('c2', 'white', 'white'))
        oval(x+2, y, max(2, rx*.37), ry*.85, p.ramp('pupil', 'pupil', 'pupil'))
        if collapse < .55:
            oval(x, y+2, 1.4, 1.4, p.ramp('iris', 'iris', 'iris'))

    if art == 'drifter':
        for k in range(6):
            x = -19+k*7
            limb((x, 23), (x+wave*3, 4+(k%2)*4), 3, 1.2, bright)
        oval(0, 33, 22, 21)
        shape([(-22, 36),(-15, 61),(4, 67),(22, 52),(21, 33)], 'c3')
        oval(-5, 45, 15, 11)
        eye(6, 47, 9, 7)
        for x in (-15, -5, 9, 17): line((x, 35), (x+2, 27), 'glow', 1)
    elif art == 'lurker':
        for side in (-1, 1):
            for k in range(3):
                limb((side*9, 19+k*7), (side*(24+k*2), 13+k*9+wave*2), 4, 2)
                limb((side*(24+k*2), 13+k*9+wave*2), (side*(30+k), 4+k*2), 2.5, 1)
        oval(-3, 23, 23, 16)
        shape([(-24,28),(-20,47),(-6,38),(6,52),(14,38),(26,35),(18,17)], 'c2')
        oval(17, 23, 12, 9, bright)
        eye(16, 27, 7, 5)
        for x in range(-18, 15, 7): shape([(x,33),(x+4,46),(x+7,33)], 'metal')
        for x in (18,23,28): line((x,17),(x+3,11),'white',1)
    elif art == 'adept':
        for side in (-1, 1):
            limb((side*8, 28), (side*(17+thrust*.2), 9), 3.5, 2)
            oval(side*18+thrust*.2, 7, 5, 3)
        shape([(-13,47),(12,47),(19,8),(-19,8)], 'c2')
        for side in (-1, 1):
            limb((side*10, 44),(side*(24+thrust*.3), 31+wave*2),4,2,bright)
            oval(side*(25+thrust*.3),31+wave*2,5,6,p.ramp('c1','glow','white'))
        shape([(-17,49),(-11,67),(0,73),(13,66),(18,49),(12,40),(-12,40)], 'c3')
        eye(1, 52, 8, 6)
        line((-8,22),(8,22),'glow',2)
    elif art == 'warden':
        for side in (-1, 1):
            limb((side*12, 31),(side*16, 5),6,4)
            oval(side*17,5,9,4,p.ramp('c0','metal','metal'))
            limb((side*18,58),(side*(31+thrust*.2),32),8,5)
            oval(side*(31+thrust*.2),31,8,11,p.ramp('c1','metal','iris'))
        shape([(-17,10),(-23,42),(-17,65),(0,75),(18,64),(24,42),(16,10)],'c2')
        shape([(-15,35),(-12,58),(0,66),(13,57),(15,35)],'metal')
        eye(2, 54, 11, 7)
        for y in (19,29,40): line((-15,y),(15,y),'c4',2)
        shape([(-10,67),(-4,82),(3,72),(8,82),(13,67)],'iris')
    elif art == 'sibyl':
        for side in (-1, 1):
            shape([(side*6,35),(side*17,29),(side*(24+wave*3),3),(side*(15+wave*2),12)],'c2')
            limb((side*10,48),(side*(27+thrust*.15),36),4,2,bright)
            oval(side*(27+thrust*.15),36,7,9,p.ramp('c1','glow','white'))
        shape([(-15,13),(-17,46),(-9,58),(10,58),(18,44),(16,13),(0,4)],'c3')
        oval(0,62,16,15)
        for x in (-8,0,8): eye(x, 62, 3.5, 3)
        shape([(-20,69),(-10,80),(0,73),(10,80),(20,69),(10,59),(-10,59)],'c2')
        for x in (-14,14): line((x,27),(x+wave*4,10),'glow',2)
    else:  # The Unblinking Eye: a floating iris, radial glass blades and trailing roots.
        for k in range(10):
            angle = math.tau*k/10 + wave*.045
            a=(math.cos(angle)*24,43+math.sin(angle)*23)
            b=(math.cos(angle)*34,43+math.sin(angle)*34)
            limb(a,b,4,1.2,p.ramp('c0','c2','iris'))
        for k in range(5):
            x=-17+k*9
            limb((x,24),(x+wave*4,3+(k%2)*5),4,1.4)
        oval(0,45,27,29,p.ramp('c0','c1','c2','c3','c4'))
        eye(2,47,21,19)
        oval(5+wave*3,47,6,18,p.ramp('pupil','pupil','pupil'))
        for side in (-1,1): shape([(side*19,69),(side*6,79),(0,73),(side*14,61)],'c4')
        line((-20,35),(20,35),'iris',2)
    if clip == 'attack' and n in (3,4,5):
        for k in range(4):
            x, y = at(25+k*3+thrust*.4, 37+(k%2)*8)
            f.dots([(x,y)], 'glow')
    if clip == 'die' and n >= 5:
        for k in range(5):
            oval(-18+k*9, 2+(k%2)*2, 2, 1.5, p.ramp('glow','c4','white'))
    if clip in ('hurt','die') and n == 0:
        f.whiten()
    return f.a


# The six enemies are the cel-shaded redraw in eye_below_cel_redraw.py (2026-10-18); the old drawer stays as `_old_draw`.
import dungeon_cel  # noqa: E402
dungeon_cel.install(globals(), 'eye_below_cel_redraw')


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
    out = ROOT / 'test-results/eye-below-preview'
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames=render(kind)
        assert not bounds(frames), (kind,bounds(frames))
        sheet=Image.new('RGBA',(W*6,H*5),'#152638')
        for row,(clip,(_,count)) in enumerate(CLIPS.items()):
            for n in range(min(count,6)):
                sheet.alpha_composite(rgba(frames[clip][n],PALETTES[kind].hex),(n*W,row*H))
        sheet.resize((W*12,H*10),Image.Resampling.NEAREST).save(out/f'{kind}.png')
        print(out/f'{kind}.png')


def build(kinds, replace=False):
    meta=json.loads(META.read_text())
    known=meta.get('sprites',{})
    clash=[k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist; export preserves editor changes. --replace discards only these Eye Below sprites.')
    for kind in clash:
        api('delete',{'sprite_id':known[kind]})
    for kind in kinds:
        frames=render(kind)
        assert not bounds(frames),(kind,bounds(frames))
        np.savez_compressed(ROOT/f'scripts/eye_below_{kind}_raw.npz',**frames)
        sid=api('create',{'name':PREFIX+kind+'_all','width':W,'height':H,
                          'frames':34,'layers':1,'fps':10,'palette':PALETTES[kind].hex,
                          'persist':True,'ops':[{'op':'set_layer','layer':0,'name':kind}]})['sprite_id']
        offset=0
        try:
            for clip,(_,count) in CLIPS.items():
                for n,grid in enumerate(frames[clip]):
                    api('draw',{'sprite_id':sid,'frame':offset+n,
                                'ops':[{'op':'grid','rows':grid.tolist(),'x':0,'y':0,'layer':0}]})
                offset+=count
        except Exception:
            api('delete',{'sprite_id':sid})
            raise
        meta['sprites'][kind]=sid
        META.write_text(json.dumps(meta,indent=2)+'\n')
        print(kind,sid,'34 editable frames')


def export(kinds):
    meta=json.loads(META.read_text())
    for kind in kinds:
        packet=api('get?sprite_id='+meta['sprites'][kind]);sp=packet.get('sprite',packet)
        assert (sp['width'],sp['height'],len(sp['frames']))==(W,H,34)
        atlas=Image.new('RGBA',(8*W,5*H))
        offset=0
        for row,(clip,(fps,count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cel=sp['frames'][offset+n]['cels'][0]
                if 'rle' in cel:
                    runs=cel['rle'];grid=np.repeat(np.array(runs[1::2],dtype=np.uint8),runs[0::2]).reshape(H,W)
                else: grid=np.array(cel['grid'],dtype=np.uint8)
                atlas.alpha_composite(rgba(grid,sp['palette']),(n*W,row*H))
            meta['clips'][clip]={'fps':fps,'n':count,'row':row,'editorStart':offset}
            offset+=count
        atlas.save(ASSETS/f'cathedral_{kind}.png',optimize=True)
        meta['tops'][kind]=AY-atlas.crop((0,0,6*W,H)).getbbox()[1]
        if kind not in meta['kinds']: meta['kinds'].append(kind)
        META.write_text(json.dumps(meta,indent=2)+'\n')
        print(ASSETS/f'cathedral_{kind}.png')


def verify(kinds):
    meta=json.loads(META.read_text())
    for kind in kinds:
        frames=render(kind)
        assert not bounds(frames),(kind,bounds(frames))
        atlas=Image.open(ASSETS/f'cathedral_{kind}.png').convert('RGBA')
        assert atlas.size==(8*W,5*H)
        for row,(clip,(_,count)) in enumerate(CLIPS.items()):
            for n in range(count):
                expected=rgba(frames[clip][n],PALETTES[kind].hex)
                actual=atlas.crop((n*W,row*H,(n+1)*W,(row+1)*H))
                assert np.array_equal(np.array(expected),np.array(actual)),(kind,clip,n)
        assert kind in meta['sprites'] and kind in meta['kinds']
        print(kind,'34 frames match indexed source')


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else ''
    kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='preview': preview(kinds)
    elif action=='build': build(kinds,'--replace' in sys.argv[2:])
    elif action=='export': export(kinds)
    elif action=='verify': verify(kinds)
    else: raise SystemExit('Usage: make_eye_below_sprites.py preview | build [--replace] | export | verify [kind...]')
