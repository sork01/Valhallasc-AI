#!/usr/bin/env python3
"""Emberfall Crags art, second pass (v2): Greenmeadow slime style, redrawn from scratch.

preview | build | refresh | export | verify.  Soft fire and ghosts deform; the spider shell, the basalt golem and the
Cinderlord's armour stay rigid (jointed, buckling, toppling).  Every planted foot rests exactly on the anchor
row (Painter y=0, row 90) so nothing floats; the wisp and wraith hover by nature.  The v1 sources (Beta
1.39.2) stay registered in crags_slime_v1_sources.txt.  Export preserves saved editor edits.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
from wyrd_slime_redraw import Painter, motion, mix
from deep_slime_redraw import sm, bez, taper, erase
from cloister_slime_redraw import Rig, erase_rising

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/crags-slime'
REGISTRY = ROOT/'scripts/crags_slime_sources.txt'
PREFIX = 'valhallasc_crags_slime_style_b_'
KINDS = old.KINDS
CLIPS = old.CLIPS
W = H = 96
AX, AY = 48, 90
# Same colours as v1; index zero alone is transparent.
PALETTE = ['#00000000', '#282131', '#ffffff', '#edf6e9', '#e6a0a5',
           '#90291b', '#d7471e', '#f87d28', '#ffb840', '#fff39c',
           '#252333', '#454257', '#6b6880', '#9893aa', '#cec8d6',
           '#211a3d', '#403366', '#68528f', '#9780b7', '#c2acd7',
           '#5f3e24', '#a16b32', '#dca249', '#ffe18a', '#eee3cd']
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
FIRE = [5, 6, 7, 8, 9]
ROCK = [10, 11, 12, 13, 14]
GHOST = [15, 16, 17, 18, 19]
GOLD = [20, 21, 22, 23, 24]
NAMES = dict(wisp='Fire Wisp', spider='Lava Spider', wraith='Ash Wraith',
             golem='Cinder Golem', cinderlord='Cinderlord')


ATTACK = [-1.5, -3, -4, .5, 4, 3.5, 1.5, 0]     # wind-up (negative), snap, impact, follow-through, recover


def atk(clip, n):
    """(windup, strike) in 0..1 for the attack clip; both zero for every other clip."""
    if clip != 'attack':
        return 0., 0.
    v = ATTACK[n]
    return max(0., -v)/4, max(0., v)/4


ARC = [-.35, -.7, -1, .25, 1, .95, .5, .15]      # swung props: back over the shoulder (-1) to smashed down (+1)


def arc(clip, n):
    if clip != 'attack':
        return 0., 0.
    return max(0., -ARC[n]), max(0., ARC[n])


def foot(a, x, lift, rx, ry, ramp):
    """A planted foot: integer ry and centre y = ry, so its lowest pixel is row 90 when lift is 0."""
    a.ball(x, ry+lift, rx, ry, ramp)


def specks(a, n, count, base_x, spread, top, ramp):
    """Drifting embers/ash; positions depend on n so consecutive frames always differ."""
    for k in range(count):
        x = base_x+((k*37+n*11) % spread)-spread/2
        y = 6+((n*5+k*13) % top)
        a.ellipse(x, y, 1, 1, ramp[(k+n) % len(ramp)])


# ----------------------------------------------------------------------------------------------
# Fire Wisp: a teardrop of living fire that hovers.  Tongues lick and lean, the body gutters out, falls
# as a charred ember and dies down to a glowing ash heap.
# ----------------------------------------------------------------------------------------------
def wisp(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    a = Painter(cx=44+recoil+st*9-wu*3)               # crouches back, then darts forward
    hover = 34+bob*.9+(math.sin(n*math.pi/4)*2.5 if clip == 'walk' else 0)-wu*4+st*2
    cy = mix(hover, 6, t)
    r = mix(17.5, 5, t)
    body = FIRE if t < .55 else ROCK
    lean = -st*5+wu*2+recoil*.4                         # tongues stream back on the dash
    for k, (dx, ln, w) in enumerate(((-11, 20, 8), (0, 30, 10), (11, 17, 7))):
        if fall > .85:
            break
        sway = math.sin(n*1.3+k*2.1)*3.2+lean
        ln *= (1-t)*(1-.4*wu+.12*st)
        base = (dx*.8, cy+r*.35)
        tip = (dx*1.2+sway*1.4, cy+r*.85+ln)
        mid = (dx*1.5+sway*.4, cy+r*.9+ln*.45)
        taper(a, bez(base, mid, tip), body, w*(1-t*.6), 1)
    a.ball(0, cy, r*(1-.12*wu+.14*st), r*.94*(1+.08*wu-.1*st), body)
    if st > .5:                                        # fire spat ahead of the dash
        for k in range(3):
            a.ellipse(r*1.1+5+k*5, cy+2-k*3+(n % 2)*2, 3-k*.6, 2.4-k*.4, [9, 8, 7][k])
    if t < .8:
        a.ellipse(-r*.45, cy+r*.35, max(1, 4*(1-t)), max(1, 2.2*(1-t)), 9 if t < .55 else 14)
    if fall < .7:
        a.face(1, cy+1, clip, n, .95)
    if t > .45:
        a.ball(1, 4.5, 3, 2.4, FIRE)
    if clip == 'die':
        for k in range(3):
            sx_, sy_ = 6+n*.6*k, 10+n*3.2+k*5
            if sy_ < 58:
                a.ellipse(sx_+math.sin(n+k)*2, sy_, 2.6-k*.5, 2.6-k*.5, ROCK[2-k % 2])
        specks(a, n, 4, 0, 40, 18, ROCK[2:])
    else:
        specks(a, n, 4, 0, 46, 38, [8, 9, 8, 7])
    return a


# ----------------------------------------------------------------------------------------------
# Lava Spider: round basalt shell on eight jointed legs (tetrapod gait).  On defeat the legs fold under,
# the shell drops to the floor and cracks; the glow dies.  No squash anywhere.
# ----------------------------------------------------------------------------------------------
def spider(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    w, st = atk(clip, n)
    ph = n*math.pi/4
    a = Painter(cx=43+recoil+st*6-w*2)
    by = mix(26+bob*.6+w*3-st*3, 16, t)                      # carapace centre; bottom reaches the floor when dead
    hips = (-22, -11, 0, 10)
    feet = (-26, -17, 17, 27)
    for far in (True, False):
        for k in range(4):
            hx = hips[k]+(3 if not far else -2)
            fx = feet[k]+(4 if not far else -3)
            lift, push = 0, 0
            if clip == 'walk':
                s = ph+(k % 2)*math.pi+(0 if far else math.pi)
                lift, push = max(0, math.sin(s))*5, math.cos(s)*3
            if clip == 'attack' and k >= 2:               # front legs rear up, then slam down ahead
                lift = w*11
                push = -w*5+st*(5 if k == 3 else 3)
            hip = (hx, by-1)
            knee = (fx+(1 if fx > hx else -1)*7, by+13+lift*.6+bob*.3)
            ft = (fx+push, 3+lift)
            if fall:
                knee = (mix(knee[0], fx*.95, t), mix(knee[1], by+7, t))
                ft = (mix(ft[0], hx*1.05+(8 if fx > 0 else -8), t), 3)
            ramp = ROCK[:4]+[ROCK[3]] if far else ROCK
            a.limb([hip, knee, (ft[0], ft[1]+2)], ramp, 4)
            foot(a, ft[0], ft[1]-3, 3.5, 3, ramp)
        if far:
            a.ball(-6, by, 23, 16, ROCK)             # shell
            for ex, ey, er in ((-14, 7, 3), (-3, 10, 3.4), (-20, 2, 2.4)):
                a.ball(ex, by+ey, er, er, FIRE if t < .6 else ROCK)
            a.line([(-24, by+4), (-17, by+9), (-19, by+13), (-12, by+15)], 7 if t < .6 else 11, 2)
            if t > .25:
                a.line([(-4, by+15), (-1, by+8), (-6, by+2), (-3, by-6)], 1, 2)
                a.line([(-14, by-12), (-9, by-6), (-13, by-1)], 1, 1)
    hx, hy = 15+st*5-w, by+1+w*6-st*3
    a.ball(hx, hy, 13, 12, ROCK)                    # head
    spread = 1+st*4+w*1.5                            # fangs hang from the jaw and part when it bites
    for off, sg in ((6, -1), (13, 1)):
        bx = hx+off
        a.poly([(bx-2.2, hy-9), (bx+2.2, hy-9), (bx+sg*spread*.5, hy-15-st*3)], 24)
        a.poly([(bx-1, hy-9), (bx+1, hy-9), (bx+sg*spread*.5, hy-14-st*3)], 3)
    a.face(hx+2, hy+4, clip, n, .75)
    for x in (9, 15, 21):
        a.ellipse(x+hx-15, by+15-t*3+(hy-by-1), 1, 1, 8 if t < .6 else 13)
    if clip == 'die':
        specks(a, n, 3, 0, 36, 30, ROCK[2:])
    return a


# ----------------------------------------------------------------------------------------------
# Ash Wraith: a hooded ghost on a ragged hem with a bone-grey scythe.  It drifts, and on defeat it
# rises and dissolves from the hood downwards into a few settling ash flecks.
# ----------------------------------------------------------------------------------------------
def wraith(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    ph = n*math.pi/4
    w, st = arc(clip, n)
    a = Painter(cx=36+recoil+st*2-w*1)                # leans back to raise the scythe, then sweeps forward
    cy = 31+bob*.9+(math.sin(ph)*1.8 if clip == 'walk' else 0)+t*10-w*2+st*1
    for k, (dx, ln) in enumerate(((-17, 12), (-8, 19), (1, 24), (10, 17), (18, 11))):   # ragged hem tails
        sw = math.sin(ph*(1 if clip == 'walk' else .5)+k*1.4)*2.2
        taper(a, bez((dx*.8, cy-8), (dx+sw*.4, cy-ln*.55), (dx*1.08+sw, cy-ln-6)), GHOST, 9, 2)
    a.ball(0, cy+3, 19.5, 23, GHOST)               # robe
    a.ball(-1, cy+22, 15, 13, GHOST)               # hood
    a.ball(1, cy+20, 11, 9, [15, 16, 17])           # hood shadow
    a.face(2, cy+19, clip, n, .85)
    a.ball(-18, cy+2-(2 if clip == 'attack' and lunge > 1 else 0), 6, 9, GHOST)           # far sleeve
    hand = (21-w*4+st*1, cy-1+w*13-st*5)
    ang = .22-w*.6+st*.85 if clip == 'attack' else .22
    L = 34-st*7
    base = (hand[0]-math.sin(ang)*5, hand[1]-math.cos(ang)*5)
    top = (hand[0]+math.sin(ang)*L, hand[1]+math.cos(ang)*L-6)
    if st > .6:                                       # slash arc behind the blade
        a.line([(hand[0]+math.sin(q)*(L+3), hand[1]+math.cos(q)*(L+3)-6) for q in (ang-1.0, ang-.7, ang-.35, ang)], 19, 2)
    a.line([base, top], 20, 4)
    a.line([base, top], 22, 2)
    blade = [(top[0]+3, top[1]+4), (top[0]-14, top[1]+9), (top[0]-24, top[1]+4), (top[0]-29, top[1]-6),
             (top[0]-18, top[1]-1), (top[0]-3, top[1]-3)]
    a.poly(blade, ROCK[3])
    a.line([blade[1], blade[2], blade[3]], 2, 1)
    a.ball(hand[0], hand[1], 4.5, 4.5, GHOST)
    if clip == 'die':
        erase_rising(a, max(0, min(1, fall*.93)))
        for k in range(5):                           # ash flecks settle on the floor
            y = max(1.5, mix(20+k*6, 1.5, min(1, t*1.2)))
            a.ellipse(-16+k*8+(n % 3)*2, y, 1.6, 1.6, ROCK[1+k % 3])
    else:
        specks(a, n, 4, 0, 46, 50, GHOST[2:])
    return a


# ----------------------------------------------------------------------------------------------
# Cinder Golem: basalt blocks with a molten core.  Heavy steps (one foot is always planted), a raised fist
# slam; on defeat it kneels, the head rolls off, shoulders and fists drop and the core goes dark.
# ----------------------------------------------------------------------------------------------
def golem(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    ph = n*math.pi/4
    w, st = atk(clip, n)
    a = Painter(cx=46+recoil+st*2-(1.5 if clip == 'die' and n == 0 else 0))
    ty = mix(34+bob*.5-st*4+w*1, 21, t)
    swing = math.cos(ph)*3 if clip == 'walk' else 0                          # opposing fist swing
    for sg in (-1, 1):
        sw = math.sin(ph+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift, push = max(0, sw)*3, sw*2.5
        foot(a, sg*(11+t*9)+push, lift*(1-t), 10, 6, ROCK)
        a.ball(sg*(10+t*8)+push*.5, mix(18+lift, 8, t), 8, 10 if t < .5 else 8, ROCK)
    a.ball(0, ty, 22, 20, ROCK)
    a.ellipse(-8, ty+10, 5, 2, 14)
    a.line([(-16, ty+3), (-9, ty-1), (-14, ty-8)], 7 if t < .7 else 11, 2)      # molten seams
    a.line([(15, ty+5), (10, ty-1), (14, ty-9)], 6 if t < .7 else 11, 2)
    a.ball(1, ty-3, 6, 7, FIRE if t < .7 else ROCK)                              # chest core
    a.ellipse(-1, ty-1, 2, 2, 9 if t < .7 else 13)
    for sg in (-1, 1):
        a.ball(sg*(21+t*(9 if sg < 0 else 6)), mix(ty+8, 9, t**1.2), 9, 9, ROCK)  # shoulder boulders drop
    # Both fists rise overhead, then hammer down in front of it.
    lx, rx_ = -27+w*9+st*6-t*7, 27-w*9+st*6+t*6
    ly = mix(23+swing+w*23-st*11, 11, t)
    ry_ = mix(23-swing+w*23-st*11, 11, t)
    a.ball(lx, ly, 9, 11, ROCK)
    a.ball(rx_, ry_, 9, 11, ROCK)
    a.line([(rx_-1, ry_+3), (rx_+3, ry_-3)], 7 if t < .7 else 11, 2)
    if st > .7:                                                                   # ground shock
        for sg in (-1, 1):
            a.ellipse(sg*30+st*sg*4, 2, 4, 2, ROCK[3])
            a.ellipse(sg*40+st*sg*3, 5, 2, 2, ROCK[2])
    hx, hy = t*14, mix(57+bob*.5+w*3-st*7, 13, t**1.4)
    a.ball(hx, hy, 17, 13 if t < .7 else 12, ROCK)
    a.ellipse(hx-7, hy+7, 4, 2, 14)
    a.line([(hx-14, hy+9), (hx-5, hy+11)], 11, 2)                                # heavy brow
    a.face(hx, hy-1, clip, n, 1.)
    if fall > .35:
        for k in range(4):
            r = 3+k % 2
            a.ball(-30+k*21+((n*3) % 5), r, r, r, ROCK)                          # fallen rubble on the floor
    if clip == 'die' and n >= 4:
        specks(a, n, 4, 0, 60, 26, ROCK[2:])                                     # settling dust
    return a


# ----------------------------------------------------------------------------------------------
# Cinderlord: the golem's lord in dark armour, horned helm, ember cape and warhammer.  On defeat the
# armour buckles and topples backwards, the hammer clattering down in front.
# ----------------------------------------------------------------------------------------------
def cinderlord(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    R = Rig(fall, pivot=(-12, 0), sign=1, angle=.55, lift=3, buckle=.42, start=.3)
    P = R.P
    ph = n*math.pi/4
    w, st = arc(clip, n)
    a = Painter(cx=46-6*max(w, st)+recoil+st*1-w*1)
    ty = 34+bob*.5-st*3
    swing = math.cos(ph)*3 if clip == 'walk' else 0                          # opposing fist swing
    a.poly(R.pts([(-13, ty+16), (12, ty+16), (22, 6), (-25, 6)]), FIRE[0])       # ember cape
    a.poly(R.pts([(-10, ty+14), (9, ty+14), (16, 10), (-17, 10)]), FIRE[1])
    a.line(R.pts([(-16, 15), (0, 20), (16, 13)]), 7, 2)
    for sg in (-1, 1):
        sw = math.sin(ph+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sw)*3
        fx, fy = P(sg*11+sw*2.5, 6+lift)
        foot(a, fx, fy-6, 10, 6, ROCK)
        a.ball(*P(sg*10+sw*1.2, 18+lift), 8, 10, ROCK)
    a.ball(*P(0, ty), 21, 21, ROCK)
    a.line(R.pts([(-16, ty-12), (16, ty-12)]), 22, 3)                           # belt
    a.ball(*P(1, ty-3), 5.5, 6.5, FIRE if fall < .7 else ROCK)
    a.ellipse(*P(0, ty-1), 2, 2, 9 if fall < .7 else 13)
    for sg in (-1, 1):
        px, py = P(sg*20, ty+8)
        a.ball(px, py, 9, 9, ROCK)
        a.poly([(px-sg*4, py+3), (px+sg*5, py+12), (px+sg*8, py+2)], GOLD[1])      # pauldron spike
    a.ball(*P(-27, 23+swing), 8.5, 10.5, ROCK)
    hand = P(27-w*9-st*6, 23-swing+w*25+st*12)
    a.ball(hand[0], hand[1], 8.5, 10.5, ROCK)
    if fall:                                      # warhammer: one rigid prop; it falls forward to lie on the floor
        tx, tyh = mix(33, 34, t), mix(61, 6, t**.7)
        hb = (mix(hand[0], 20, t), mix(hand[1], 3, t))
    else:                                         # hammer: cocked back over the shoulder, then smashed down ahead
        ha = .16-w*1.5+st**3*2.55
        Lh = 38-st*13
        tx, tyh = hand[0]+math.sin(ha)*Lh, hand[1]+math.cos(ha)*Lh
        hb = hand
        if st > .7:
            for k in range(3):                    # embers burst from the impact
                a.ellipse(min(tx+3+k*4, 40), 4+k*4+(n % 2)*2, 2.4-k*.5, 2.4-k*.5, [9, 8, 7][k])
    a.line([hb, (tx, tyh)], 20, 4)
    a.line([hb, (tx, tyh)], 22, 2)
    a.ball(tx, tyh, 9, 6, ROCK)
    a.line([(tx-2, tyh-4), (tx-2, tyh+4)], 23, 3)
    hx, hy = P(0, 56+bob*.5)
    a.ball(hx, hy, 16, 14, ROCK)
    for sg in (-1, 1):                                                              # curved horns
        taper(a, [(hx+sg*x, hy+y) for x, y in bez((10, 9), (24, 11), (20, 27))], GOLD, 6, 1)
    a.line([(hx-14, hy+10), (hx+14, hy+10)], 22, 3)                                # crown band
    a.poly([(hx-3, hy+12), (hx, hy+18), (hx+4, hy+12)], GOLD[3])
    a.face(hx, hy-1, clip, n, 1.)
    if clip == 'die' and n >= 5:
        specks(a, n, 3, 0, 40, 26, ROCK[2:])
    return a


DRAW = dict(wisp=wisp, spider=spider, wraith=wraith, golem=golem, cinderlord=cinderlord)


def frame(kind, clip, n):
    grid = np.array(DRAW[kind](clip, n).im)
    if kind in ('spider', 'golem', 'cinderlord'):      # rigid bodies never sink below the floor row
        low = int(np.nonzero(grid.any(axis=1))[0].max())
        if low > AY:
            grid = np.roll(grid, AY-low, axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = 3
    assert grid.any(), (kind, clip, n, 'empty')
    assert not (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()), (kind, clip, n, 'border')
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = registry()
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}      # validate every kind before saving any source
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX+kind+'_all'
        assert name not in existing, 'Unregistered source already exists: '+name
        np.savez_compressed(ROOT/f'scripts/crags_slime_{kind}_raw.npz', **data[kind])
        sid = old.api('create', dict(name=name, width=W, height=H, frames=34, layers=1, fps=10,
                                     palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2)+'\n')
        offset = 0
        for clip, grids in data[kind].items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=sid, frame=offset+n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        print(kind, sid, offset, 'frames saved', flush=True)


def refresh():
    """Rewrite the frames of the named kinds' EXISTING v2 sources from the drawers (same IDs). Overwrites editor
    edits of those kinds: only for a candidate nobody has hand-edited."""
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT/f'scripts/crags_slime_{kind}_raw.npz', **data)
        offset = 0
        for clip, grids in data.items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=saved[kind], frame=offset+n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        print('Refreshed', kind, saved[kind], offset, 'frames', flush=True)


def cel_grid(cel):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    meta = dict(frame=[W, H], anchor=[AX, AY], kinds=KINDS, clips={}, sprites=saved, tops={}, artStyle='greenmeadow-slime')
    proof, atlases = {}, {}
    for kind in KINDS:       # read and validate every saved editor source before replacing any installed file
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, 34)
        atlas = Image.new('RGBA', (8*W, 5*H))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset+n]['cels'][0]), sp['palette'])
                bounds = im.getbbox()
                assert bounds and min(bounds[:2]) > 0 and max(bounds[2:]) < 96
                atlas.alpha_composite(im, (n*W, row*H))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['tops'][kind] = int(AY-min(r['bounds'][1] for r in rows if r['clip'] == 'idle'))
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for kind, atlas in atlases.items():
        dest = ASSETS/f'crags_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'crags.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 170 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    """Compare the installed atlases directly to the saved editor frames, not to the drawers."""
    meta = json.loads((ASSETS/'crags.txt').read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        atlas = Image.open(ASSETS/f'crags_{kind}.png').convert('RGBA')
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n*W, row*H, (n+1)*W, (row+1)*H))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset+n]['cels'][0]), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def preview():
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    overview = Image.new('RGB', (len(only)*240, 5*218), '#344b40')
    d = ImageDraw.Draw(overview)
    for col, kind in enumerate(only):
        data = frames(kind)
        sheet = Image.new('RGB', (8*192, 5*218), '#344b40')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((192, 192), Image.Resampling.NEAREST)
                sheet.paste(im, (n*192, row*218), im)
                sd.text((n*192+8, row*218+194), f'{clip} {n}', fill='white')
                sd.line([(n*192, row*218+180), (n*192+192, row*218+180)], fill='#5a7a68')
            im = rgba(grids[0 if clip != 'die' else 7]).resize((192, 192), Image.Resampling.NEAREST)
            overview.paste(im, (col*240+20, row*218), im)
            d.text((col*240+20, row*218+194), f'{NAMES[kind]} / {clip}', fill='white')
        sheet.save(OUT/f'preview-{kind}.png')
    overview.save(OUT/'preview.png')
    print(OUT/'preview.png')


if __name__ == '__main__':
    {'preview': preview, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
