#!/usr/bin/env python3
"""Crags art in the Greenmeadow slime style, with material-specific movement.

Soft fire/ghosts deform; spiders articulate; stone and armour stay rigid.
Native editable PixelFlow sources use a separate prefix; old sources survive.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import make_crag_sprites as old

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
REGISTRY = ROOT / 'scripts/crags_slime_sources.txt'
PREFIX = 'valhallasc_crags_slime_style_'
KINDS = old.KINDS
CLIPS = old.CLIPS
W = H = 96
AX, AY = 48, 90
# All colours are opaque RGB in PixelFlow; index zero alone is transparent.
PALETTE = ['#00000000', '#282131', '#ffffff', '#edf6e9', '#e6a0a5',
           '#90291b', '#d7471e', '#f87d28', '#ffb840', '#fff39c',
           '#252333', '#454257', '#6b6880', '#9893aa', '#cec8d6',
           '#211a3d', '#403366', '#68528f', '#9780b7', '#c2acd7',
           '#5f3e24', '#a16b32', '#dca249', '#ffe18a', '#eee3cd']
FIRE = [5, 6, 7, 8, 9]
ROCK = [10, 11, 12, 13, 14]
GHOST = [15, 16, 17, 18, 19]
GOLD = [20, 21, 22, 23, 24]
NAMES = dict(wisp='Fire Wisp', spider='Lava Spider', wraith='Ash Wraith',
             golem='Cinder Golem', cinderlord='Cinderlord')


class Painter:
    def __init__(self, cx=48, lift=0, sx=1, sy=1):
        self.im = Image.new('P', (W, H), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx, self.lift, self.sx, self.sy = cx, lift, sx, sy

    def pos(self, x, y):
        return round(self.cx + x*self.sx), round(AY-y*self.sy-self.lift)

    def ellipse(self, x, y, rx, ry, col):
        px, py = self.pos(x, y)
        rx, ry = max(1, round(rx*self.sx)), max(1, round(ry*self.sy))
        self.d.ellipse((px-rx, py-ry, px+rx, py+ry), fill=col)

    def line(self, pts, col, width=1):
        self.d.line([self.pos(*p) for p in pts], fill=col, width=width)

    def poly(self, pts, col):
        self.d.polygon([self.pos(*p) for p in pts], fill=col)

    def ball(self, x, y, rx, ry, ramp):
        px, py = self.pos(x, y)
        rx, ry = rx*self.sx, ry*self.sy
        for yy in range(max(1, math.floor(py-ry)), min(H-1, math.ceil(py+ry)+1)):
            for xx in range(max(1, math.floor(px-rx)), min(W-1, math.ceil(px+rx)+1)):
                u, v = (xx-px)/rx, (yy-py)/ry
                rr = u*u+v*v
                if rr > 1:
                    continue
                z = math.sqrt(max(0, 1-rr))
                light = max(0, min(.999, .23+.71*(-.40*u-.54*v+.74*z)))
                value = light*(len(ramp)-1)
                lo = int(value)
                threshold = ((xx % 4)*5+(yy % 4)*3) % 16/16
                shade = min(len(ramp)-1, lo+int(value-lo > threshold))
                if rr > .93 and u+v > .2:
                    shade = 0
                self.im.putpixel((xx, yy), ramp[shade])

    def face(self, x, y, clip, n, size=1, blush=True):
        dead = clip == 'die' and n >= 2
        for dx in (-6, 6):
            ex = x+dx*size
            if dead:
                self.line([(ex-2, y-2), (ex+2, y+2)], 1)
                self.line([(ex-2, y+2), (ex+2, y-2)], 1)
            elif clip == 'idle' and n == 3:
                self.line([(ex-3*size, y), (ex+3*size, y+.5)], 1, 2)
            else:
                self.ellipse(ex, y, 4.3*size, 6.5*size, 1)
                self.ellipse(ex, y+.6, 3.3*size, 5.5*size, 3)
                self.ellipse(ex+1.2, y-.3, 1.7*size, 3.5*size, 1)
                self.ellipse(ex+.5, y+2.2, .8, 1, 2)
                if clip == 'attack' and n < 3:
                    self.line([(ex-4, y+6), (ex+3, y+3)], 1, 2)
        if blush and not dead:
            self.ellipse(x-12*size, y-5, 2.5, 1.3, 4)
            self.ellipse(x+12*size, y-5, 2.5, 1.3, 4)
        self.line([(x-3, y-8), (x, y-9), (x+3, y-8)], 1)


def frame(kind, clip, n):
    walk = clip == 'walk'
    phase = n*math.pi/4
    bob = [0, 1, 2, 1, 0, -1][n] if clip == 'idle' else 0
    stride = math.sin(phase)*4 if walk else 0
    lunge = [-1, -3, -4, 2, 5, 4, 2, 0][n] if clip == 'attack' else 0
    hurt = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    death = max(0, n-1)/6 if clip == 'die' else 0
    soft = kind in ('wisp', 'wraith')
    sx, sy = 1., 1.
    if soft:
        sx = 1 + (math.sin(phase)*.035 if walk else bob*.012)
        sy = 1 - (math.sin(phase)*.04 if walk else bob*.012)
    # The stone, armour and spider shell have no whole-body squash or stretch.
    a = Painter(cx=45+lunge+hurt, lift=bob if soft else 0, sx=sx, sy=sy)

    if kind == 'wisp':
        cy = 32+ (math.sin(phase)*3 if walk else 0)-death*13
        r = 20*(1-death*.8)
        # Flickering fire tongues disappear as the ember goes out.
        for dx, dy, rad in [(-12, 19, 8), (0, 29, 9), (12, 17, 6)]:
            flick = math.sin(n*1.6+dx)*3
            a.poly([(dx-9, cy), (dx-4, cy+dy*(1-death)+flick),
                    (dx+2, cy+dy*(1-death)+8), (dx+rad, cy+5)], 7)
            a.poly([(dx-4, cy+8), (dx, cy+dy*(1-death)+2), (dx+3, cy+4)], 8)
        a.ball(0, cy, r+2, r*.88, FIRE)
        a.ellipse(-9, cy+9, max(1, 5*(1-death)), 2, 9)
        if death < .6:
            a.face(2, cy+1, clip, n)
        for k in range(3 if not death else 5):
            a.ellipse(-23+k*10, 13+(n*3+k*7) % 15, 1, 1, 8 if not death else 13)
        if death > .8:
            a = Painter()
            a.ball(0, 3, 9, 2, [10, 11, 12])
            for k in range(4):
                a.ellipse(-12+k*8, 12+((n+k)*5) % 15, 1.5, 1.5, 13)

    elif kind == 'spider':
        # Eight short jointed legs tuck under the intact shell on defeat.
        by = 22-death*9+bob*.5
        for far in (True, False):
            for k, fx in enumerate((-35, -25, 21, 32)):
                up = max(0, math.sin(phase*2+k*1.5+(1 if far else 0)))*5 if walk else 0
                hip = (-10+k*6, by)
                foot = (fx*(1-death*.5), 4+up+death*(10+k*2))
                knee = (fx*.72, by+7-death*8)
                if clip == 'attack' and k >= 2:
                    foot = (foot[0]+lunge, foot[1]+max(0, -lunge)*2)
                col = 11 if far else 12
                a.line([hip, knee, foot], 10, 6)
                a.line([hip, knee, foot], col, 4)
                a.ball(*knee, 3.5, 3.5, ROCK)
            if far:
                a.ball(-11, by+7, 21, 17, ROCK)
                a.line([(-23, by+13), (-16, by+8), (-19, by+2), (-10, by-4)], 7, 2)
                a.ellipse(-20, by+16, 4, 2, 14)
        a.ball(13, by+2, 15, 12, ROCK)
        a.face(15, by+5, clip, n, .8)
        for x in (9, 15, 21):
            a.ellipse(x, by+15, 1, 1, 8)
        for x in (11, 20):
            a.poly([(x-2, by-6), (x+2, by-6), (x+1, by-11)], 24)

    elif kind == 'wraith':
        # Hood and scythe identify the ghost; it dissipates upwards into ash.
        rise = death*18
        cy = 29+rise
        if death < .85:
            a.ball(-1, cy, 20*(1-death*.55), 21*(1-death*.4), GHOST)
            for k in range(5):
                a.ball(-16+k*8, cy-15+math.sin(n+k)*2, 6*(1-death*.7), 5, GHOST)
            a.ball(1, cy+18, 17*(1-death*.5), 16, GHOST)
            a.ball(3, cy+17, 13*(1-death*.6), 11, [15, 16, 17])
            if death < .5:
                a.face(3, cy+19, clip, n, .9)
                a.ellipse(-8, cy+29, 3, 1, 19)
            # Short scythe swings as a rigid prop and drops during dissipation.
            topx, topy = (28, 63) if lunge < 1 else (34, 44)
            if death:
                topx, topy = 29, 63-death*53
            a.line([(23, 9), (topx, topy)], 1, 4)
            a.line([(23, 9), (topx, topy)], 21, 2)
            a.poly([(topx-3, topy+3), (topx-15, topy+8),
                    (topx-23, topy+4), (topx-28, topy-5),
                    (topx-18, topy), (topx-3, topy-2)], 14)
            a.line([(topx-23, topy+3), (topx-15, topy+6), (topx-3, topy+1)], 3)
            a.ball(23, 30+rise*.3, 4, 4, GHOST)
        if death:
            arr = np.array(a.im)
            # Dissolution mask, increasingly sparse; no ghost puddle.
            yy, xx = np.indices(arr.shape)
            arr[((xx*7+yy*3) % 17) < int(death*13)] = 0
            a.im = Image.fromarray(arr, 'P')
            a.d = ImageDraw.Draw(a.im)
        for k in range(5):
            a.ellipse(-20+k*9, 14+((n*3+k*11) % 45), 1, 1, 18)

    elif kind in ('golem', 'cinderlord'):
        lord = kind == 'cinderlord'
        # Fixed-size rigid components slump/dislocate rather than flattening.
        drop = death*31
        torso_y = 33-drop*.65+bob*.5
        head_y = 56-drop+bob*.5
        sway = stride*.35
        if lord:
            a.poly([(-13, 51-drop), (12, 51-drop), (21, 7), (-24, 7)], 6)
            a.line([(-17, 14), (0, 19), (17, 12)], 8, 2)
        for side in (-1, 1):
            footx = side*(11+death*8)
            lift = max(0, side*stride) if walk else 0
            a.ball(footx, 7+lift, 10, 6, ROCK)
            a.ball(side*10, 18+lift-death*8, 8, 10, ROCK)
        a.ball(sway, torso_y, 23 if not lord else 21, 21, ROCK)
        a.ellipse(-8+sway, torso_y+11, 5, 2, 14)
        # Molten seam and chest core survive the chibi proportions.
        a.line([(-15, torso_y+4), (-9, torso_y), (-13, torso_y-6)], 7, 2)
        a.ball(1+sway, torso_y-3, 6, 7, FIRE if death < .7 else ROCK)
        a.ellipse(-1+sway, torso_y, 2, 2, 9 if death < .7 else 13)
        for side in (-1, 1):
            a.ball(side*20, torso_y+7, 9, 9, ROCK)
            if lord:
                a.poly([(side*20-4, torso_y+12), (side*25, torso_y+21),
                        (side*20+5, torso_y+11)], 22)
        # Stone fist lifts for attack, armour keeps its shape through the swing.
        fist_y = 23+max(0, -lunge)*6-death*9
        a.ball(-27-death*4, 23-death*9, 9, 11, ROCK)
        a.ball(27, fist_y, 9, 11, ROCK)
        a.line([(25, fist_y+3), (29, fist_y-4)], 7, 2)
        a.ball(-death*6, head_y, 16 if lord else 17, 14, ROCK)
        a.ellipse(-7-death*6, head_y+8, 4, 2, 14)
        if lord:
            hx = -death*6
            for side in (-1, 1):
                a.poly([(hx+side*11, head_y+8), (hx+side*22, head_y+22),
                        (hx+side*17, head_y+7)], 21)
                a.line([(hx+side*15, head_y+11), (hx+side*20, head_y+20)], 23, 2)
            a.line([(hx-14, head_y+10), (hx+14, head_y+10)], 22, 3)
            a.poly([(hx-3, head_y+12), (hx, head_y+18), (hx+4, head_y+12)], 23)
            # Compact warhammer moves as one rigid object with the hand.
            tx, ty = (31, 62) if lunge < 1 else (34, 31)
            if death:
                tx, ty = 33, 62-death*53
            a.line([(26, max(8, fist_y-7)), (tx, ty)], 20, 4)
            a.line([(26, max(8, fist_y-7)), (tx, ty)], 22, 2)
            a.ball(tx, ty, 9, 6, ROCK)
            a.line([(tx-2, ty-4), (tx-2, ty+4)], 23, 3)
            a.line([(-16, torso_y-12), (16, torso_y-12)], 22, 3)
        a.face(-death*6, head_y, clip, n, 1., blush=not death)
        if death > .4:
            for k in range(4):
                a.ball(-24+k*15, 3+(k % 2)*2, 3, 3, ROCK)
    arr = np.array(a.im)
    if clip == 'hurt' and n == 0:
        arr[arr > 0] = 3
    assert arr.any(), (kind, clip, n, 'empty')
    assert not (arr[0].any() or arr[-1].any() or arr[:, 0].any() or arr[:, -1].any()), (kind, clip, n, 'border')
    return arr


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)])
            for clip, (_, count) in CLIPS.items()}


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def build():
    saved = registry()
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX+kind+'_all'
        assert name not in existing, 'Unregistered source already exists: '+name
        data = frames(kind)  # Validate everything before creating any sprite.
        np.savez_compressed(ROOT/f'scripts/crags_slime_{kind}_raw.npz', **data)
        sid = old.api('create', {'name': name, 'width': W, 'height': H,
                 'frames': 34, 'layers': 1, 'fps': 10, 'palette': PALETTE,
                 'persist': True, 'ops': [{'op': 'set_layer', 'layer': 0, 'name': kind}]})['sprite_id']
        # Persist immediately; a failed build is recoverable without deleting sources.
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2)+'\n')
        offset = 0
        for clip, grids in data.items():
            for n, grid in enumerate(grids):
                old.api('draw', {'sprite_id': sid, 'frame': offset+n,
                    'ops': [{'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
            offset += len(grids)
        print(kind, sid, offset, 'frames saved', flush=True)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': KINDS,
            'clips': {}, 'sprites': saved, 'tops': {}, 'artStyle': 'greenmeadow-slime'}
    proof = {}
    for kind in KINDS:
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, 34)
        atlas = Image.new('RGBA', (8*W, 5*H))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                cel = sp['frames'][offset+n]['cels'][0]
                if 'rle' in cel:
                    runs = cel['rle']
                    grid = np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
                else:
                    grid = np.array(cel['grid'], dtype=np.uint8)
                im = rgba(grid, sp['palette'])
                assert im.getbbox() and min(im.getbbox()[:2]) > 0 and max(im.getbbox()[2:]) < 96
                atlas.alpha_composite(im, (n*W, row*H))
                rows.append({'clip': clip, 'n': n, 'sha256': hashlib.sha256(im.tobytes()).hexdigest(),
                             'bounds': im.getbbox()})
            offset += count
        idle = np.array(atlas)[:H, :6*W, 3]
        meta['tops'][kind] = int(AY-np.nonzero(idle.any(axis=1))[0].min())
        atlas.save(ASSETS/f'crags_{kind}.png', optimize=True)
        proof[kind] = dict(source=saved[kind], frames=rows,
            atlasSha256=hashlib.sha256((ASSETS/f'crags_{kind}.png').read_bytes()).hexdigest())
    (ASSETS/'crags.txt').write_text(json.dumps(meta, indent=2)+'\n')
    out = ROOT/'test-results/crags-slime'
    out.mkdir(parents=True, exist_ok=True)
    (out/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported five saved PixelFlow sources and health-bar tops', flush=True)


def preview():
    out = ROOT/'test-results/crags-slime'
    out.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGBA', (5*240, 5*230), '#344b40')
    d = ImageDraw.Draw(sheet)
    for col, kind in enumerate(KINDS):
        data = frames(kind)
        for row, clip in enumerate(CLIPS):
            im = rgba(data[clip][min(4, len(data[clip])-1)])
            sheet.alpha_composite(im.resize((192,192), Image.Resampling.NEAREST), (col*240+24, row*230))
            d.text((col*240+24, row*230+196), f'{NAMES[kind]} / {clip}', fill='white')
    sheet.convert('RGB').save(out/'preview.png')
    print(out/'preview.png')


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv)>1 else 'preview'
    {'preview': preview, 'build': build, 'export': export}[command]()
