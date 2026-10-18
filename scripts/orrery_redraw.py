"""Cel-shaded Obsidian Orrery enemies (zone 15) for make_orrery_sprites.py.

Same recipe as cathedral_reliquary_redraw.py and astral_redraw.py: hard colour bands, one dark outline per part,
big glossy eyes, chibi proportions. 96x96 frame, foot anchor (48,90), five clips.
`python3 scripts/orrery_redraw.py [kind...]` writes contact sheets to test-results/orrery-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, timing, diamond, gear_points, preview, star
from make_crag_sprites import ellipsoid

KINDS = ('bronzemantis', 'gearling', 'orbitseer', 'chronoguard', 'pendulummatron', 'epochengine')

PALETTES = {
    'bronzemantis': mk(bronze=('#4a2c1e', '#8a5a34', '#c98f50', '#f2cd82'), steel=('#3a4658', '#78889e', '#b8c8dc', '#eef6ff'),
                       glow=('#0e6a6a', '#3ad8c8', '#b6fff0'), iris='#10c8b8', dark=('#2a1c18', '#503628'),
                       blush='#ff9a78', spark='#d8fff6'),
    'gearling': mk(brass=('#3f2a18', '#8a5c2a', '#d6a043', '#ffe38a'), steel=('#38475a', '#7a8ea6', '#c0d0e2'),
                   glow=('#0e6a6a', '#3ad8c8', '#b6fff0'), iris='#15bcc8', blush='#ff9a78', oil='#2a1c18'),
    'orbitseer': mk(orb=('#17284e', '#2c5ca8', '#5eaee6', '#c0eeff'), gold=('#8c5d16', '#dba22f', '#ffe382'),
                    eyeball=('#a4b8cc', '#e0ecf6', '#fbffff'), iris='#13c4c0', beam=('#bff8ff', '#f4ffff'),
                    mote=('#6e5ac0', '#b4a0f0', '#ece4ff'), blush='#ff9ac0'),
    'chronoguard': mk(plate=('#2c3040', '#5a6078', '#9aa2bc', '#dee4f4'), brass=('#6a4414', '#c48a2c', '#f6d068'),
                      cloth=('#1c3a68', '#2e66b0', '#5aa0e6'), glow=('#9ff6ff', '#38d6ee'), iris='#16b8d8',
                      face=('#e8ddc0', '#fff8e0'), pole=('#6a5a4a', '#b09a82'), sand=('#d8a040', '#ffe08a')),
    'pendulummatron': mk(gown=('#3c1d46', '#7c3c7a', '#be6aa4', '#f2b2cc'), apron=('#cbb8a8', '#f2e6d6', '#fff6ea'),
                         skin=('#c88a78', '#f0b8a2', '#ffdcc8'), hair=('#6a6a7c', '#b4b4c8', '#eaeaf6'),
                         brass=('#6a4414', '#c48a2c', '#f6d068'), iris='#a8368c', blush='#ff8a98',
                         rod=('#8a8aa2', '#dcdcf0'), trail=('#fff0a8', '#ffffff')),
    'epochengine': mk(brass=('#3b2614', '#7a4e22', '#c68a3a', '#f6d073'), copper=('#5a2418', '#a04a2a', '#e08850'),
                      steel=('#2c3344', '#5d6e8a', '#a8b8d0'), face=('#d8c8a0', '#f4ead0', '#fff6e0'),
                      glow=('#0e6a6a', '#3ad8c8', '#b6fff0'), iris='#e8421e', steam=('#b8c4d4', '#eef4fa'),
                      blush='#ff9a78'),
}
R.PALETTES.update(PALETTES)


def gear(a, cx, cy, r, teeth, phase, group, depth=.24, out=True):
    pts = gear_points(cx, cy, r, teeth, phase, depth)
    a.band(pts, group, out=out)


# ------------------------------------------------------------------------------------------------
def bronzemantis(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('bronzemantis', clip, n, sy=1 - fall * .35)
    b = bob * .7 - fall * 6
    by = 34 + b
    # four jointed legs, two a side
    for i, (lx, dx, near) in enumerate(((-12, -9, 0), (-1, -4, 0), (-6, -9, 1), (6, 6, 1))):
        up = max(0, math.sin(n * math.pi / 2 + i * 1.7)) * 6 if clip == 'walk' else 0
        hip = (lx, by - 8)
        knee = (lx + dx * 1.2, by - 13 + fall * 10)
        foot = (lx + dx * 1.8, lerp(up, 18 + math.sin(n * 1.4 + i) * 3, fall))
        grp = 'dark' if near == 0 else 'bronze'
        a.c(hip, knee, 3.4 if near else 3, 2.8, grp)
        a.c(knee, foot, 2.8, 1.7, grp)
        a.e(foot[0] + 1, foot[1] + .5, 3, 1.6, grp)
    # abdomen with a small gear sail
    a.e(-17, by - 7, 14, 9, 'bronze')
    a.e(-20, by - 3, 8, 3.6, 'bronze', out=False)
    gear(a, -19, by + 8, 6.6, 6, n * .25 if clip != 'die' else 0, 'steel')
    a.e(-19, by + 8, 2.2, 2.2, 'bronze')
    # thorax and a small waist
    a.e(0, by + 2, 11.5, 14, 'bronze')
    a.band([(-8, by + 3), (8, by + 3), (7, by - 6), (-7, by - 6)], 'bronze', out=False)
    a.line((-8, by - 1), (8, by - 1), 'bronze0', 1)
    # scythe arms (far one folded, near one swings)
    def scythe(root, elbow, tip, blade_dir=1):
        a.c(root, elbow, 3.6, 3, 'bronze')
        a.c(elbow, tip, 3, 2.4, 'bronze')
        a.e(elbow[0], elbow[1], 3.4, 3.4, 'bronze')
        blade = [(tip[0] - 3, tip[1] + 3), (tip[0] + 4, tip[1] + 13), (tip[0] + 14, tip[1] + 11), (tip[0] + 20, tip[1] + 3),
                 (tip[0] + 12, tip[1] + 6), (tip[0] + 5, tip[1] + 4), (tip[0] + 2, tip[1] - 2)]
        a.band(blade, 'steel')
        a.line((tip[0] + 3, tip[1] + 6), (tip[0] + 14, tip[1] + 8), 'steel3', 1)
    scythe((4, by + 11), (12, by + 14), (18, by + 3), 1)
    near_e = (lerp(lerp(14, 10, wind), 18, strike), lerp(lerp(by + 17, by + 31, wind), by + 10, strike))
    near_t = (lerp(lerp(22, 14, wind), 21, strike), lerp(lerp(by + 7, by + 38, wind), by - 8, strike))
    if clip == 'die':
        near_e = (lerp(14, 8, fall), lerp(by + 17, 24, fall))
        near_t = (lerp(24, 14, fall), lerp(by + 7, 8, fall))
    scythe((6, by + 8), near_e, near_t, 1)
    # triangular head with huge glowing eyes and little antennae
    hx, hy = 9 + strike * 3, by + 24
    for s in (-1, 1):
        a.c((hx + s * 3, hy + 7), (hx + s * 8 + 2 + sw * s, hy + 18), 1, 1, 'dark')
        a.e(hx + s * 8 + 2 + sw * s, hy + 19, 1.8, 1.8, 'glow')
    a.e(hx, hy, 13, 10.5, 'bronze')
    a.poly([(hx - 7, hy - 4), (hx + 9, hy - 5), (hx + 3, hy - 13), (hx - 3, hy - 12)], 'bronze1')
    a.e(hx - 3, hy + 5, 8, 4, 'bronze', out=False)
    a.eye(hx - 4, hy + 1.6, 4.6, iris='iris', look=(.3, .1))
    a.eye(hx + 6.5, hy + 1.6, 4.2, iris='iris', look=(.7, .1))
    a.dot(hx - 8, hy - 3.4, 'blush', 2)
    jaw = max(wind * .4, strike) * 3
    a.line((hx - 1, hy - 8 - jaw), (hx + 5, hy - 8 - jaw), 'ink', 1)
    if clip == 'attack' and n in (3, 4):
        for k in range(5):
            ang = -1.1 + k * .5
            a.dot(min(30 + math.cos(ang) * 8 - (n - 3) * 2, 36), by + 4 + math.sin(ang) * 15, 'spark', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def gearling(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('gearling', clip, n, sy=1 - fall * .5)
    b = bob * .8
    spin = {'idle': 0., 'walk': n * .26, 'attack': n * .7, 'hurt': -n * .3, 'die': fall * .5}[clip]
    cx, cy = 0 + strike * 6 - wind * 3, 30 + b - fall * 8
    # feet and small hands on the sides of the gear
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 5 if clip == 'walk' else 0
        a.e(s * 9 + cx * .3, 3.5 + up, 6.8, 3.6, 'steel')
        a.c((s * 7 + cx * .3, 12), (s * 9 + cx * .3, 4 + up), 3.4, 3.2, 'steel')
    # the gear is the whole body: teeth, rim, face plate
    gear(a, cx, cy, 20, 12, spin, 'brass', depth=.2)
    a.e(cx, cy, 17.6, 17.6, 'brass')
    a.e(cx - 5, cy + 8, 9, 5, 'brass', out=False)
    for k in range(6):                                       # spokes show through as rivets on the rim
        ang = spin + k * math.pi / 3
        a.dot(cx + math.cos(ang) * 14.5, cy + math.sin(ang) * 14.5, 'steel2', 2)
    a.e(cx, cy - 1, 12.6, 12, 'steel')
    a.e(cx - 3, cy + 5, 7, 3.4, 'steel', out=False)
    a.eye(cx - 4.4, cy + 1, 4.6, iris='iris', look=(.4, .1))
    a.eye(cx + 5.6, cy + 1, 4.2, iris='iris', look=(.8, .1))
    a.dot(cx - 8.5, cy - 4, 'blush', 2)
    a.dot(cx + 9, cy - 4, 'blush', 2)
    a.line((cx - 3, cy - 6), (cx + 3, cy - 6) if clip != 'attack' else (cx + 4, cy - 8), 'ink', 1)
    # winding key on top
    a.c((cx, cy + 19), (cx + 1, cy + 28), 1.4, 1.4, 'steel')
    kx, ky = cx + 1, cy + 30
    ph = spin * 2
    a.e(kx + math.cos(ph) * 5, ky, 3.6, 3.2, 'brass')
    a.e(kx - math.cos(ph) * 5, ky, 3.6, 3.2, 'brass')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(min(26 + k * 3, 38), cy - 6 + (k * 5) % 12, 'brass3', 2)
    if clip == 'die':
        for k in range(5):
            a.e(-22 + k * 11, 3 + (k % 2) * 2, 2.6, 2.6, 'brass')
    return a.done()


# ------------------------------------------------------------------------------------------------
def orbitseer(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('orbitseer', clip, n, sy=1 - fall * .35)
    cy = 46 + bob * 1.4 - fall * 28
    flare = max(wind, strike)
    spin = n * (math.pi / 3 if clip == 'idle' else math.pi / 4) * (1 + flare)

    def ring(r_out, front):
        """A tilted golden ring: the back half or the front half (sin of the phase picks the side)."""
        for k in range(24):
            th = k * math.pi / 12
            if (math.sin(th) >= 0) != front:
                continue
            x, y = math.cos(th) * r_out, cy + math.sin(th) * r_out * .3 - math.cos(th) * 3
            a.e(x, y, 2.4, 2.4, 'gold', out=True)
    if fall < .7:
        ring(30, False)
    # sentries: two small orbs with their own eyes
    def orb(k, front):
        th = spin + k * math.pi
        if (math.sin(th) >= 0) != front or fall > .6:
            return
        x, y = math.cos(th) * 30, cy + math.sin(th) * 9 - math.cos(th) * 2
        a.e(x, y, 5.6, 5.6, 'mote')
        a.eye(x + 1, y, 2.6, iris='iris', look=(.5, 0))
    orb(0, False)
    orb(1, False)
    # the big seer: a cobalt sphere with a vast eye
    a.e(0, cy, 21, 21, 'orb')
    a.e(-8, cy + 10, 10, 6, 'orb', out=False)
    state = T['state']
    if state == 'dead':
        a.line((-9, cy - 6), (9, cy + 6), 'ink', 3)
        a.line((-9, cy + 6), (9, cy - 6), 'ink', 3)
    else:
        lid = 0 if not T['blink'] else .8
        a.e(1, cy, 14.4, 13.2 * (1 - lid), 'eyeball')
        if not lid:
            a.e(3.4, cy, 8.2, 8.2, 'orb')
            a.f.flat(ellipsoid(*a.g(3.4, cy), 6.2, 6.2 * a.sy)[0], 'iris')
            a.f.flat(ellipsoid(*a.g(4.2, cy - .2), 3.2, 3.6 * a.sy)[0], 'ink')
            a.dot(.2, cy + 3.6, 'shine', 3)
            a.dot(6.4, cy - 2.4, 'shine', 1)
        if state == 'angry':
            a.line((-13, cy + 15), (14, cy + 9), 'ink', 3)
        if state == 'hurt':
            a.line((-13, cy + 13), (12, cy + 4), 'ink', 3)
    a.dot(-14, cy - 11, 'blush', 3)
    a.dot(16, cy - 11, 'blush', 3)
    orb(0, True)
    orb(1, True)
    if fall < .7:
        ring(30, True)
    if clip == 'attack' and n in (3, 4, 5):
        w = 5 + (n - 3) * 1.5
        a.poly([(10, cy + 3), (36, cy + w), (36, cy - w), (10, cy - 3)], 'beam0', out=False)
        a.poly([(10, cy + 1.4), (36, cy + 2.4), (36, cy - 2.4), (10, cy - 1.4)], 'beam1', out=False)
        star(a, 32, cy + 8, 2.6, 'beam1')
        star(a, 36, cy - 8, 2.2, 'beam1')
    if clip == 'idle':
        for k in range(3):
            a.dot(-30 + k * 28 + (n % 2) * 2, cy + 22 - ((n * 3 + k * 4) % 12), 'mote2', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def chronoguard(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('chronoguard', clip, n, sy=1 - fall * .5)
    b = bob * .5
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 8, 22), (s * 8, 6 + up), 5, 4.4, 'plate')
        a.e(s * 8.5, 4 + up, 7.6, 4.2, 'plate')
        a.line((s * 8 - 3, 6 + up), (s * 8 + 3, 6 + up), 'brass1', 1)
    # tower shield with a clock face (far arm)
    sx, sy_ = -25 + wind * -2, 35 + b
    a.poly([(sx - 10, sy_ + 14), (sx + 10, sy_ + 14), (sx + 10, sy_ - 8), (sx, sy_ - 18), (sx - 10, sy_ - 8)], 'brass1')
    a.band([(sx - 7.5, sy_ + 11.5), (sx + 7.5, sy_ + 11.5), (sx + 7.5, sy_ - 7), (sx, sy_ - 15), (sx - 7.5, sy_ - 7)], 'cloth', out=False)
    a.e(sx, sy_ + 1, 6, 6, 'face')
    a.line((sx, sy_ + 1), (sx, sy_ + 5.5), 'ink', 1)
    a.line((sx, sy_ + 1), (sx + 3.4, sy_ - .6), 'ink', 1)
    a.c((-12, 40 + b), (sx + 6, sy_ + 2), 3.6, 3.2, 'plate')
    # barrel torso with a clock face on the chest, belt and tabard
    a.band([(-12, 24), (12, 24), (15, 16), (-15, 16)], 'cloth')
    a.e(0, 34 + b, 14.4, 12, 'plate')
    a.e(-5, 39 + b, 7, 4, 'plate', out=False)
    a.e(0, 34 + b, 7.4, 7.4, 'brass')
    a.e(0, 34 + b, 5.4, 5.4, 'face', out=False)
    a.f.flat(ellipsoid(*a.g(0, 34 + b), 5.4, 5.4 * a.sy)[0], 'face1')
    ang = n * .5 if clip in ('idle', 'walk') else n * 1.1
    a.line((0, 34 + b), (math.cos(ang) * 4, 34 + b + math.sin(ang) * 4), 'ink', 1)
    a.line((0, 34 + b), (math.cos(ang * .2 + 1) * 2.6, 34 + b + math.sin(ang * .2 + 1) * 2.6), 'ink', 1)
    a.line((-13, 27 + b), (13, 27 + b), 'brass1', 2)
    # halberd: a crescent gear blade on a long pole
    hand = (lerp(lerp(19, 15, wind), 25, strike), lerp(lerp(33, 38, wind), 35, strike))
    tilt_x = lerp(lerp(0, -4, wind), 22, strike)
    top = (min(hand[0] + 1 + tilt_x, 30), lerp(lerp(72, 74, wind), 40, strike))
    low = (hand[0] - 1 - tilt_x * .4, lerp(lerp(2, 5, wind), 33, strike))
    if clip == 'die':
        hand = (lerp(19, 28, fall), lerp(33, 8, fall))
        top = (lerp(20, 36, fall), lerp(72, 14, fall))
        low = (lerp(18, 4, fall), 3)
    a.line(low, top, 'ink', 4)
    a.line(low, top, 'pole1', 2)
    dx_, dy_ = top[0] - low[0], top[1] - low[1]
    ln = math.hypot(dx_, dy_) or 1
    ux, uy = dx_ / ln, dy_ / ln
    px, py = -uy, ux
    gx, gy = top[0] - ux * 4, top[1] - uy * 4
    gear(a, gx + px * 6, gy + py * 6, 5.6, 8, n * .5 if clip != 'die' else 0, 'brass')
    a.poly([(top[0] - px * 2, top[1] - py * 2), (top[0] + ux * 9, top[1] + uy * 9), (top[0] + px * 2, top[1] + py * 2)], 'plate2')
    a.c((10, 41 + b), hand, 4, 3.6, 'plate')
    a.e(hand[0], hand[1], 4, 3.8, 'brass')
    # pauldrons with gears
    for s in (-1, 1):
        a.e(s * 16, 42 + b, 8, 6.8, 'plate')
        gear(a, s * 16, 44 + b, 3.2, 6, n * .4 * s if clip != 'die' else 0, 'brass', out=False)
    # helm: a big visor with glowing eyes and a brass crest
    hx, hy = 1, 57 + b
    a.poly([(hx - 3, hy + 12), (hx, hy + 22), (hx + 4, hy + 12)], 'brass2')
    a.e(hx, hy, 13.6, 12, 'plate')
    a.e(hx - 4, hy + 6, 7.4, 4, 'plate', out=False)
    a.poly([(hx - 11, hy + 3), (hx + 12, hy + 3), (hx + 12, hy - 7), (hx - 11, hy - 7)], 'ink', out=False)
    state = T['state']
    for dx in (-4.8, 5.4):
        if state == 'dead':
            a.line((hx + dx - 2.4, hy - 1), (hx + dx + 2.4, hy - 5), 'glow1', 2)
            a.line((hx + dx - 2.4, hy - 5), (hx + dx + 2.4, hy - 1), 'glow1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy - 2), 3.8, 3.3 * a.sy)[0], 'glow0', outline=True)
            a.f.flat(ellipsoid(*a.g(hx + dx + .6, hy - 2.3), 2.1, 2.5 * a.sy)[0], 'iris')
            a.dot(hx + dx - 1.4, hy - .2, 'shine', 1)
    a.line((hx - 11, hy - 8), (hx + 12, hy - 8), 'brass1', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(top[0] + 7 + k * 4, 36), top[1] + k * 4 - 4, 2.4, 'sand1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def pendulummatron(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('pendulummatron', clip, n, sy=1 - fall * .55)
    sway = math.sin(n * math.pi / 3) * 1.4 if clip == 'idle' else sw * 1.6
    b = bob * .7
    # bell gown with a ring of clock numerals at the hem
    hem = [(-26, 4), (-22, 12), (-17, 3), (-11, 11), (-6, 2), (0, 11), (6, 2), (11, 11), (17, 3), (22, 12), (26, 4)]
    gown = [(-10, 42 + b), (10, 42 + b), (17, 30), (24 + sway, 14), (26 + sway * .5, 4), (-26 + sway * .5, 4), (-24, 14), (-17, 30)]
    a.band(gown, 'gown')
    a.band(hem[:] + [(26, 6), (-26, 6)], 'gown', out=False)
    for k in range(7):
        a.dot(-20 + k * 6.6 + sway * .3, 8 - (k % 2) * 3, 'brass2', 2)
    a.band([(-8, 38 + b), (8, 38 + b), (10, 22), (-10, 22)], 'apron', out=False)
    a.e(0, 41 + b, 10.6, 7.6, 'gown')
    a.line((-10, 38 + b), (10, 38 + b), 'brass1', 2)
    e = a.e
    e(0, 43 + b, 3.4, 3.4, 'brass')
    # the pendulum: rod from her hand, a great gold bob at the end
    swing = math.sin(n * math.pi / 4) * .35 if clip in ('idle', 'walk') else 0
    hand = (lerp(lerp(-21, -18, wind), 17, strike), lerp(lerp(38, 64, wind), 38, strike))
    ang = lerp(lerp(swing, -.9, wind), 1.6, strike)
    if clip == 'attack' and strike == 0 and wind == 0:
        ang = 0
    ang = ang if clip != 'hurt' else (-.5, -.35, -.15, 0)[n]
    ln = 31 if clip != 'die' else 31
    if clip == 'die':
        hand = (lerp(-21, -14, fall), lerp(38, 10, fall))
        ang = lerp(0, 1.5, fall)
    bob_p = (hand[0] + math.sin(ang) * ln, hand[1] - math.cos(ang) * ln)
    bob_p = (min(max(bob_p[0], -34), 33), max(bob_p[1], 7))
    far = (22, 35 + b)
    a.c((9, 43 + b), far, 3.4, 3, 'gown')
    a.e(far[0], far[1], 3, 3, 'skin')
    a.c((-9, 43 + b), hand, 3.6, 3, 'gown')
    a.e(hand[0], hand[1], 3, 3, 'skin')
    a.line(hand, bob_p, 'ink', 4)
    a.line(hand, bob_p, 'rod1', 2)
    if clip == 'attack' and strike > .2:
        a.line((hand[0] - 2, hand[1] + 3), (bob_p[0] - 6, bob_p[1] + 5), 'trail0', 1)
    a.e(bob_p[0], bob_p[1], 7.6, 7.6, 'brass')
    a.e(bob_p[0], bob_p[1], 4, 4, 'brass', out=True)
    a.dot(bob_p[0] - 2, bob_p[1] + 2.4, 'shine', 2)
    # head: grey side buns, a frilled mob cap, big gentle eyes behind brass spectacles
    hx, hy = 1 + sway * .3, 57 + b
    for sg in (-1, 1):
        a.e(hx + sg * 12, hy + 1, 5.6, 5.6, 'hair')
    a.e(hx, hy, 12.4, 11.6, 'skin')
    cap = [(hx - 13, hy + 2), (hx - 11, hy + 12), (hx - 5, hy + 19), (hx + 5, hy + 19), (hx + 11, hy + 12), (hx + 13, hy + 2),
           (hx + 9, hy + 5), (hx + 5, hy + 1), (hx + 1, hy + 5), (hx - 3, hy + 1), (hx - 7, hy + 5)]
    a.band(cap, 'apron')
    for k in range(5):
        a.dot(hx - 10 + k * 5, hy + 12 + (k % 2) * 2, 'apron2', 2)
    a.e(hx, hy + 14, 2.6, 2.6, 'brass', out=False)
    a.eye(hx + 2.4, hy - 2, 4.4, iris='iris')
    a.eye(hx + 10, hy - 2, 3.3, iris='iris')
    for ex, er in ((hx + 2.4, 6.6), (hx + 10, 5.4)):
        cx_, cy_ = a.g(ex, hy - 2)
        from make_crag_sprites import dilate
        mask = ellipsoid(cx_, cy_, er, er * 1.1 * a.sy)[0]
        ring = dilate(mask) & ~mask & (a.f.a == 0)
        a.f.a[ring] = a.p['brass1']
    a.dot(hx - 4, hy - 6, 'blush', 3)
    a.line((hx + 3, hy - 8), (hx + 7, hy - 7), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(bob_p[0] + 6 + k * 5, 38), bob_p[1] + 3 - k * 4, 2.4, 'trail0')
    if clip == 'die':
        for k in range(4):
            diamond(a, -22 + k * 14, max(3, 34 - fall * 31 + (k % 2) * 6), 2.2, 3.4, 'brass2' if k % 2 else 'brass1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def epochengine(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('epochengine', clip, n, sy=1 - fall * .5)
    b = bob * .8
    cy = 42 + b - fall * 6
    # steam puffs from the stack
    if clip != 'die':
        for k in range(3):
            rise = (n * 1.6 + k * 4) % 10
            a.e(-18 + k * 4 + rise * .3, 72 + rise * .6 + b, 2.4 + rise * .2, 2.2 + rise * .18, 'steam', out=False)
    # piston legs with gear feet
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 11, 22), (s * 12, 9 + up), 5.6, 5, 'steel')
        gear(a, s * 12, 7 + up, 6.8, 8, (n * .45 * s) if clip == 'walk' else 0, 'brass')
        a.e(s * 12, 7 + up, 2.6, 2.6, 'steel')
    # smokestack, bell and the clock body
    a.c((-12, cy + 20), (-14, cy + 27), 4.4, 4, 'steel')
    a.e(-14, cy + 28, 5.4, 2.4, 'steel')
    a.e(6, cy + 24, 6, 5.4, 'brass')
    a.e(6, cy + 28, 2.2, 2.2, 'brass', out=True)
    gear(a, 0, cy, 26.6, 14, n * .06 if clip in ('idle', 'walk') else n * .2, 'brass', depth=.12)
    a.e(0, cy, 24, 24, 'brass')
    a.e(-8, cy + 12, 12, 6.4, 'brass', out=False)
    a.e(0, cy - .5, 19.6, 19.6, 'face')
    for k in range(12):
        ang = k * math.pi / 6
        a.dot(math.cos(ang) * 16.2, cy - .5 + math.sin(ang) * 16.2, 'ink', 2 if k % 3 == 0 else 1)
    # eyes on the dial, hands as a stern little moustache
    a.eye(-6.2, cy + 5, 5, iris='iris', look=(.3, .1))
    a.eye(6.6, cy + 5, 5, iris='iris', look=(.8, .1))
    a.dot(-12.4, cy - 2, 'blush', 3)
    a.dot(12.4, cy - 2, 'blush', 3)
    ang = (n * .22 if clip in ('idle', 'walk') else n * .7)
    a.line((0, cy - 5), (math.cos(2.5 + ang * .3) * 8, cy - 5 + math.sin(2.5 + ang * .3) * 5), 'ink', 2)
    a.line((0, cy - 5), (math.cos(.64 - ang * .3) * 11, cy - 5 + math.sin(.64 - ang * .3) * 4), 'ink', 2)
    a.e(0, cy - 5, 2, 2, 'brass')
    # arms: pistons ending in gear fists (the near one slams)
    far = (-30, cy - 6 + sw * 2)
    a.c((-21, cy), far, 4, 3.6, 'steel')
    gear(a, far[0], far[1], 6.6, 8, n * .3 * (0 if clip == 'die' else 1), 'brass')
    a.e(far[0], far[1], 2.6, 2.6, 'steel')
    fist = (lerp(lerp(30, 26, wind), 32, strike), lerp(lerp(cy - 6, cy + 24, wind), 10, strike))
    if clip == 'die':
        fist = (lerp(30, 34, fall), lerp(cy - 6, 8, fall))
    a.c((21, cy), fist, 5, 4.4, 'steel')
    gear(a, fist[0], fist[1], 8.4, 9, n * .5 if clip == 'attack' else 0, 'brass')
    a.e(fist[0], fist[1], 3.2, 3.2, 'steel')
    if clip == 'attack' and n in (4, 5):
        for k in range(4):
            a.e(min(fist[0] + 4 + k * 2.4, 38), 3 + (k * 7) % 9 + (n - 4) * 3, 2.4, 2.4, 'steam')
    if clip == 'die':
        for k in range(5):
            gear(a, -26 + k * 13, 4 + (k % 2) * 2, 3 + k % 2, 6, k, 'brass', out=True)
    return a.done()


DRAW = dict(bronzemantis=bronzemantis, gearling=gearling, orbitseer=orbitseer, chronoguard=chronoguard,
            pendulummatron=pendulummatron, epochengine=epochengine)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/orrery-preview')
    print('ok')
