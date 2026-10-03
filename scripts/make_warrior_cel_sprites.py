#!/usr/bin/env python3
"""Warrior: a plate-armoured anime knight with sword and shield, in the Hunter's cel style (see cel_common.py).

usage: make_warrior_cel_sprites.py preview [clip|all] [directory]   contact sheets (scratch), rows = facings
       make_warrior_cel_sprites.py build [--replace]                 render every frame, create the editable PixelFlow sprites warrior_cel_<clip>_<facing>_<group>
       make_warrior_cel_sprites.py export [--local]                  PixelFlow (edits kept) -> client/assets/warrior_layered_*.png + warrior_layered_sprites.txt

Eleven layers: body + armor, shoulders, gloves, head (crimson, azure) + weapon (sword, royal). The weapon layers carry
the sword and the round shield on the left arm. Three more, `gm`, are the administrator's golden robe, top hat and
sword & shield (one PixelFlow group `gm`: build/export it alone with `--only gm`, so the other groups' edits stay). A broader build than the other classes (limbs x1.15). build --replace
DISCARDS WARRIOR HAND EDITS. Files keep the old warrior_layered_ names so the game's part names stay valid.
"""
import math

import numpy as np

import cel_common as cc
import generic_gear as gg
from cel_common import V, unit, rig

SLOTS = {'armor': ('crimson', 'azure', 'gm'), 'shoulders': ('crimson', 'azure', 'ironhide'), 'gloves': ('crimson', 'azure', 'duelist'),
         'head': ('crimson', 'azure', 'ironhide', 'gm'), 'weapon': ('sword', 'royal', 'gm'),
         'pants': ('wayfarer',), 'necklace': ('moonstone',), 'accessory': ('amber',)}
MATS = {
    **cc.FACE_MATS,
    **gg.GEAR_MATS,
    'hair': ['#3a2420', '#6e4336', '#a77a56', '#d6ae82'],      # the player's hair colour recolours it
    'cloth': ['#3a3a4c', '#5c5c72', '#8c8ca4', '#c0c0d4'],
    'pants': ['#2a2a38', '#44445a', '#68688a', '#9696b8'],
    'crimson': ['#5a0f1c', '#9a1f30', '#d83c4a', '#ff8a8a'],
    'azure': ['#0f2a5a', '#1f4f9a', '#3c82d8', '#8ac4ff'],
    'steel': ['#3a4658', '#6a7a92', '#aebdd2', '#eef4ff'],
    'gold': ['#6e4a12', '#b0801f', '#e8b840', '#fff0a0'],
    'leather': ['#2a1a16', '#47291f', '#6e4331', '#9a6a4c'],
    'plume': ['#7a1230', '#c22850', '#f05a7a', '#ffc0c8'],
    'wing': ['#8a9ab0', '#c4d0e0', '#f0f5ff', '#ffffee'],
    'glow': ['#0f8a96', '#2fd0d8', '#8af0ee', '#e4ffff'],
    'iris': ['#6a3410', '#b0641c', '#e8a040', '#fff0b0'],
    # the game master's golden set (appended last, so every older index keeps its value)
    'gilt': ['#8c5c12', '#d9a226', '#ffd84e', '#fff8c4'],       # polished gold
    'brocade': ['#5e3808', '#a8700f', '#d89a1c', '#f6d870'],    # deep gold for panels and shadows
    'ruby': ['#58081a', '#a8142e', '#e8344e', '#ff9ca8'],
    'pearl': ['#8c8678', '#cac4b6', '#f4f0e4', '#fffcf2'],
}
PALETTE, COLOR = cc.palette_of(MATS)
BULK = 1.15
DEFAULT = dict(root=(0, 0, 0), lean=4, twist=0, roll=0, sway=0, eyes='open',
               handL=(-13, 8, 52), handR=(13, 7, 50), footL=(-5, 0, 4), footR=(5, 0, 4),
               blade=(.12, .45, 1), shield=(-.55, 1, 0), ground=False, dropped=False)


def idle(k):
    a = k / 6 * math.tau
    return dict(root=(0, 0, -.35 * math.sin(a)), sway=math.sin(a), twist=-6,
                handL=(-13, 8, 52 + .4 * math.sin(a)),
                eyes='closed' if k == 4 else 'open')


def walk(k):
    q = k / 8
    a = q * math.tau
    def foot(s, t):
        t %= 1
        return (s * 5, 9 - t * 36 if t < .5 else -9 + (t - .5) * 36,
                4 + (6 * math.sin((t - .5) * math.tau) if t >= .5 else 0))
    return dict(lean=11, roll=2 * math.sin(a), twist=4 * math.sin(a),
                root=(0, 0, -.7 * math.cos(a * 2)), sway=3 * math.sin(a),
                handL=(-14, 4 - math.sin(a) * 2, 53), handR=(14, 5 + math.sin(a) * 3, 52),
                blade=(.12, .45 + .2 * math.sin(a), 1),
                footL=foot(-1, q), footR=foot(1, q + .5))


def attack(k):
    # Raise the sword overhead, wind up, cut down across the body on frame 4 (the impact), recover behind the shield.
    right = [(13, 7, 50), (15, 4, 68), (15, -5, 68), (13, 10, 70), (7, 24, 50), (9, 22, 44), (11, 14, 46), (13, 7, 50)][k]
    blade = [(.12, .45, 1), (.1, .2, 1), (.1, -.5, .9), (.05, .6, .85), (-.1, 1, -.15), (-.1, .9, -.4), (.1, .7, .5), (.12, .45, 1)][k]
    left = [(-13, 8, 52), (-14, 10, 56), (-15, 12, 60), (-14, 14, 58), (-12, 18, 54), (-12, 16, 52), (-13, 11, 52), (-13, 8, 52)][k]
    f = [0, -.3, -.55, .4, 1, .65, .25, 0][k]
    return dict(lean=[4, 0, -8, 8, 20, 17, 10, 4][k], twist=[-4, 10, 24, -6, -26, -22, -8, -4][k],
                root=(0, max(0, f) * 2.4, -.7 * abs(f)), handL=left, handR=right, blade=blade, sway=-3 * f,
                footL=(-6, 4 * max(0, f), 4), footR=(6, -5 * max(0, f), 4))


def hurt(k):
    f = [.25, 1, .4, 0][k]
    return dict(lean=-14 * f, root=(0, -2 * f, 0), twist=9 * f,
                handL=(-16, 7, 55), handR=(15, 5, 52), eyes='closed' if k < 3 else 'open', sway=-2 * f)


def die(k):
    return dict(lean=[-5, -23, -43, -66, -85, -90, -90, -90][k],
                root=(0, 8 if k >= 3 else 0, 0), eyes='closed',
                handL=(-17, 1, 50), handR=(17, 1, 49),
                footL=(-5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                footR=(5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                ground=k >= 3, dropped=k >= 2)


CLIPS = {'idle': (6, 6, idle), 'walk': (12, 8, walk), 'attack': (20, 8, attack),
         'hurt': (10, 4, hurt), 'die': (8, 8, die)}
GEAR = {
    'armor': {'none': {'name': 'Simple cloth', 'defense': 0},
              'crimson': {'name': 'Crimson guard', 'defense': 3}, 'azure': {'name': 'Azure guard', 'defense': 5}},
    'shoulders': {'none': {'name': 'Bare shoulders', 'defense': 0},
                  'crimson': {'name': 'Crimson Pauldrons', 'defense': 2}, 'azure': {'name': 'Azure Winged Pauldrons', 'defense': 3}},
    'gloves': {'none': {'name': 'Bare hands', 'defense': 0},
               'crimson': {'name': 'Crimson Gauntlets', 'defense': 1}, 'azure': {'name': 'Azure Gauntlets', 'defense': 2}},
    'head': {'none': {'name': 'Bare head', 'defense': 0},
             'crimson': {'name': 'Crimson Plumed Helm', 'defense': 2}, 'azure': {'name': 'Azure Winged Helm', 'defense': 3}},
    'weapon': {'none': {'name': 'Empty hands', 'attack': 0},
               'sword': {'name': 'Sword & shield', 'attack': 4}, 'royal': {'name': 'Royal sword & shield', 'attack': 8},
               'gm': {'name': 'Golden Sword & Shield', 'attack': 20}},
}
GEAR['armor']['gm'] = {'name': 'Golden Robe of the Game Master', 'defense': 12}
GEAR['head']['gm'] = {'name': 'Golden Top Hat', 'defense': 4}


def disc(centre, a1, a2, rx, ry, n=14):
    return [centre + a1 * math.cos(i / n * math.tau) * rx + a2 * math.sin(i / n * math.tau) * ry for i in range(n)]


def surface(ink, points, mat, tone=2, bias=0., outline=True):
    """A flat polygon whose depth follows its own plane (Ink.plate gives one mean depth, so a tall plate cannot hide a
    leg behind it). `bias` makes it nearer than the limbs' radius bias; details pass a slightly larger one."""
    proj = [ink.project(q) for q in points]
    xy = np.array([q[0] for q in proj], float)
    d = np.array([q[1] for q in proj], float)
    c = np.linalg.lstsq(np.c_[np.ones(len(xy)), xy], d, rcond=None)[0]
    g = np.array([c[1], c[2]])
    n = float(np.linalg.norm(g))
    if n < 1e-6:
        ink.poly(xy, ink.color[mat][tone], float(d.mean()) - bias, outline)
        return
    axis = g / n
    along = xy @ axis
    a, b = xy.mean(0) + axis * (along.min() - xy.mean(0) @ axis), xy.mean(0) + axis * (along.max() - xy.mean(0) @ axis)
    za, zb = c[0] + c[1] * a[0] + c[2] * a[1], c[0] + c[1] * b[0] + c[2] * b[1]
    ink.poly(xy, ink.color[mat][tone], -bias, outline, gradient=(a, b, za, zb))


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R, xf, joints = cc.skeleton(p)
    inks = {part: cc.Ink(psi, COLOR) for part in SHEET.parts}
    body = inks['body']
    torso = lambda ink, mat, *a: cc.torso(ink, xf, mat, *a)
    cc.base_body(body, xf, joints, R, w=1.05 if cc.FEMALE else BULK, torso_width=8.8, torso_depth=4)
    head = cc.head_frame(body, xf, psi, p, turn=.5)
    H, hd, front, side = head['H'], head['hd'], head['front'], head['side']
    sw = p['sway']
    # Short spiky hair: a swept fringe of three sharp locks, bristling crown, a short tail at the nape.
    if cc.FEMALE:
        # A long braid down the back (a swaying plait with a ribbon at the end) and a short pair of face-framing locks.
        body.plate([xf(q) for q in [(-3, -5.4, 86), (3, -5.4, 86), (5.2 + sw * 1.2, -9.4, 64), (4 + sw * 2.4, -10.8, 42), (0 + sw * 2.8, -10.8, 31), (-3.4 + sw * 2.2, -10.4, 42), (-4.6 + sw, -8.8, 66)]], 'hair', 1)
        for z_ in (72, 60, 48):
            body.plate([xf(q) for q in [(-3.4 + sw * (86 - z_) * .06, -9.6 - (86 - z_) * .02, z_ + 1.2), (3.4 + sw * (86 - z_) * .06, -9.6 - (86 - z_) * .02, z_ + 1.2), (2.4 + sw * (86 - z_) * .06, -10 - (86 - z_) * .02, z_ - 1.4), (-2.4 + sw * (86 - z_) * .06, -10 - (86 - z_) * .02, z_ - 1.4)]], 'hair', 2, True)
        body.bone(xf((-1.4 + sw * 2.8, -10.8, 32)), xf((1.4 + sw * 2.8, -10.8, 32)), 1.1, 1.1, 'plume', -.4)
        for sx_ in (-1, 1):
            body.plate([xf(q) for q in [(sx_ * 9.4, -1.2, 86), (sx_ * 11, -1.2, 80), (sx_ * 10.6, .8, 69), (sx_ * 9, .6, 68), (sx_ * 8.6, -.4, 76)]], 'hair', 2 if sx_ > 0 else 1, True)
    else:
        body.plate([xf(q) for q in [(-4, -5, 80), (4, -5, 80), (5 + sw, -8, 70), (0 + sw * 1.3, -9, 66), (-5 + sw, -8, 70)]], 'hair', 1)
    if not cc.face(body, head, p, lashes=.8):
        body.poly([H(*q) for q in [(-9.5, 8), (-10.5, 0), (-8.5, -8), (-4, -10.5), (5, -9.5), (9.5, -5), (10.5, 4), (6.5, 13), (-3, 14)]], COLOR['hair'][2], hd - 5)
    crown = [(-10.4, -4), (-11.6, 5), (-10.4, 10), (-7.6, 15), (-5.6, 14), (-3, 21), (-.4, 15.6), (2.6, 22), (4, 15.6), (8, 19), (8.4, 13), (11.6, 11), (10.8, 4), (10.4, -4),
             (8.4, 0), (7.6, 4.6), (4.6, 7.6), (1.4, 4.6), (-.8, 7), (-4, 4.6), (-7.2, 6.4), (-8.4, 1)]
    if cc.FEMALE:      # a softly swept fringe instead of the spikes
        crown = [(-10.5, -6), (-11.5, 6), (-9.5, 13), (-4, 17.4), (1, 18.8), (6, 17), (10, 13), (11.5, 6), (10.5, -6),
                 (8.6, -2), (7, 3.5), (3, 6.8), (-1, 4.4), (-5, 6.2), (-8, 3), (-9, -2)]
    body.poly([H(*q) for q in crown], COLOR['hair'][1], hd - 6)
    if cc.FEMALE:
        body.poly([H(*q) for q in [(-9, 12), (-3, 16.4), (4, 17), (9.6, 12), (9, 9), (3, 12.6), (-3, 12.4), (-8.5, 8.4)]], COLOR['hair'][2], hd - 6.1, False)
        body.poly([H(*q) for q in [(-5, 14.6), (0, 17), (4, 16), (0, 14), (-4, 12.8)]], COLOR['hair'][3], hd - 6.2, False)
    else:
        body.poly([H(*q) for q in [(-10, 10), (-7.6, 14.4), (-5.4, 13.6), (-3, 19.8), (-1, 14.6), (-6, 9)]], COLOR['hair'][2], hd - 6.1, False)
        body.poly([H(*q) for q in [(2.6, 20.4), (3.8, 15), (7.6, 17.6), (8, 13), (5, 11)]], COLOR['hair'][2], hd - 6.1, False)
        body.poly([H(*q) for q in [(-4, 13), (-2, 16), (0, 13), (-1.6, 11.6)]], COLOR['hair'][3], hd - 6.2, False)
    # Heavy brows sit above the shared eyes (a lighter, arched pair on the woman).
    if front > -.4:
        for sx in (-1, 1):
            ex = sx * 4 * max(.28, front) + side * 3.3
            if abs(side) > .85 and sx * side < 0:
                continue
            if cc.FEMALE:
                body.poly([H(ex - 2.6, 3.6), H(ex + 2.6, 4.8), H(ex + 2.2, 5.4), H(ex - 2.4, 4.2)], COLOR['brow'][1], hd - 5.9, False)
            else:
                body.poly([H(ex - 2.8, 3.2), H(ex + 2.8, 4.6), H(ex + 2.2, 5.8), H(ex - 2.6, 4.4)], COLOR['brow'][0], hd - 5.9, False)

    cuff = lambda j, f: j['hand'] + (j['elbow'] - j['hand']) * f
    for tier in ('crimson', 'azure'):
        ink = inks['armor_' + tier]
        azure = tier == 'azure'
        col = tier
        torso(ink, 'steel', 9.6, 4.9, 38, 69)
        # Surcoat: a colour tabard over the breastplate, belted, with a gold emblem; steel pectoral lines.
        ink.plate([xf(q) for q in [(-5.4, 5.3, 69), (5.4, 5.3, 69), (6, 5.5, 40), (-6, 5.5, 40)]], col, 2)
        ink.plate([xf(q) for q in [(-5.4, 5.3, 69), (-1, 5.4, 69), (-2.4, 5.5, 40), (-6, 5.5, 40)]], col, 3)
        ink.plate([xf(q) for q in [(-6.2, 5.4, 64), (6.2, 5.4, 64), (6.2, 5.4, 62.6), (-6.2, 5.4, 62.6)]], 'gold', 3, True)
        ink.plate([xf(q) for q in [(0, 5.6, 60), (2.6, 5.6, 56), (0, 5.6, 51), (-2.6, 5.6, 56)]], 'gold', 3)
        ink.plate([xf(q) for q in [(0, 5.7, 58.4), (1.2, 5.7, 56), (0, 5.7, 53.6), (-1.2, 5.7, 56)]], 'glow' if azure else 'plume', 3, True)
        # Gorget (collar plate).
        ink.bone(xf((-5.6, 0, 68.4)), xf((5.6, 0, 68.4)), 3.4, 3.4, 'steel', -1.4, 2)
        for sy in (-1, 1):
            ink.plate([xf(q) for q in [(-10, sy * 5.2, 42), (10, sy * 5.2, 42), (10, sy * 5.2, 38.4), (-10, sy * 5.2, 38.4)]], 'leather', 2 if sy > 0 else 1)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 10, -5.2, 42), (sx * 10, 5.2, 42), (sx * 10, 5.2, 38.4), (sx * 10, -5.2, 38.4)]], 'leather', 1)
        ink.plate([xf(q) for q in [(-2.6, 5.5, 42.6), (2.6, 5.5, 42.6), (2.6, 5.5, 37.8), (-2.6, 5.5, 37.8)]], 'gold', 3, True)
        # Tassets: overlapping steel skirt plates with a colour edge, longer front and back.
        s = sw * .6
        for sy, tone in ((1, 2), (-1, 1)):
            for i, x_ in enumerate((-6.4, -2.1, 2.1, 6.4)):
                top, bot = 38.4, 26.5 - (1.8 if i in (1, 2) else 0) - (3 if azure else 0)
                ink.plate([xf(q) for q in [(x_ - 2.4, sy * 5.6, top), (x_ + 2.4, sy * 5.6, top), (x_ + 2.2 + s, sy * 6.4, bot), (x_ - 2.2 + s, sy * 6.4, bot)]], 'steel', tone)
                ink.plate([xf(q) for q in [(x_ - 2.2 + s, sy * 6.4, bot + 1.7), (x_ + 2.2 + s, sy * 6.4, bot + 1.7), (x_ + 2.2 + s, sy * 6.4, bot), (x_ - 2.2 + s, sy * 6.4, bot)]], col, 2, True)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 9.6, -4.6, 38.4), (sx * 9.6, 4.6, 38.4), (sx * 11 + s, 4.2, 28), (sx * 11 + s, -4.2, 28)]], 'steel', 1)
        if azure:
            # A long cape in the tier colour, falling from the shoulders behind.
            ink.plate([xf(q) for q in [(-10, -5.6, 70), (10, -5.6, 70), (12 + s * 2, -9.6, 14), (0 + s * 3, -10.4, 9), (-12 + s * 2, -9.6, 14)]], 'azure', 1)
            ink.plate([xf(q) for q in [(-4, -5.8, 69), (4, -5.8, 69), (5 + s * 2, -9.8, 16), (-5 + s * 2, -9.8, 16)]], 'azure', 2, True)
            ink.plate([xf(q) for q in [(-12 + s * 2, -9.6, 14), (0 + s * 3, -10.4, 9), (12 + s * 2, -9.6, 14), (12 + s * 2, -9.6, 16.4), (0 + s * 3, -10.4, 11.4), (-12 + s * 2, -9.6, 16.4)]], 'gold', 2, True)
        else:
            ink.plate([xf(q) for q in [(-9, -5.6, 70), (9, -5.6, 70), (10.4 + s * 2, -8.6, 26), (-10.4 + s * 2, -8.6, 26)]], 'crimson', 1)
        # Greaves with a colour knee cop and a steel sabaton.
        for key in 'LR':
            j = joints[key]
            leg = j['ankle'] - j['knee']
            ink.bone(j['knee'] + leg * .12, j['ankle'], 3.9, 3.1, 'steel', -.8, 2)
            ink.bone(j['knee'] - leg * .05, j['knee'] + leg * .2, 4.5, 4.3, col, -1.0, 2)
            ink.bone(j['ankle'] + V(0, -1, -1), j['ankle'] + V(0, 5, -2), 3.0, 2.9, 'steel', -.8)
            ink.bone(j['ankle'] + V(0, 3.4, -1.8), j['ankle'] + V(0, 5.4, -2.1), 2.9, 2.7, 'gold' if azure else 'leather', -.9, 2)

    for tier in ('crimson', 'azure'):
        ink = inks['shoulders_' + tier]
        azure = tier == 'azure'
        for key in 'LR':
            j = joints[key]
            sh = j['shoulder']
            sx = -1 if key == 'L' else 1
            out, upv = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            ink.bone(sh - out * .6 + upv * 2.6, sh + out * 5.6 - upv * 1.4, 6.0, 5.4, 'steel', -1.0, 2)
            ink.bone(sh + out * 2.6 + upv * .8, sh + out * 8.2 - upv * 4, 5.2, 4.4, 'steel', -1.15, 1)
            ink.bone(sh + out * 2.6 + upv * .8, sh + out * 3.6 + upv * .4, 5.4, 5.4, tier, -1.3, 2)
            ink.bone(sh + out * 5.6 - upv * 2.4, sh + out * 6.6 - upv * 3, 4.8, 4.8, tier, -1.3, 2)
            if azure:
                for off in (0, 1.5):
                    ink.plate([sh + out * (3 + off) + upv * 3.4, sh + out * (4 + off * 2) + upv * 13, sh + out * (6 + off) + upv * 3.4], 'gold', 2 if off else 3)
            else:
                ink.plate([sh + out * 3.6 + upv * 3.6, sh + out * 5.4 + upv * 10, sh + out * 7 + upv * 3.4], 'steel', 3)

    for tier in ('crimson', 'azure'):
        ink = inks['gloves_' + tier]
        azure = tier == 'azure'
        for key in 'LR':
            j = joints[key]
            hand = j['hand']
            ink.bone(cuff(j, .52), hand + (j['elbow'] - hand) * .05, 3.6, 3.2, 'steel', -.85, 2)
            ink.bone(cuff(j, .52), cuff(j, .42), 4.0, 4.0, tier, -1.0, 2)
            ink.bone(hand - R @ V(0, 0, 1.2), hand + R @ V(0, 0, 2.2), 3.0, 2.7, 'steel', -.95)
            ink.bone(hand + R @ V(0, 0, .3), hand + R @ V(0, 0, .9), 1.3, 1.3, 'gold' if not azure else 'glow', -1.2, 2)

    for tier in ('crimson', 'azure'):
        ink = inks['head_' + tier]
        azure = tier == 'azure'
        # Open-faced helm: a steel dome with a brow band, cheek guards and a nose bar; crest or wings on top.
        dome = [(-11.4, -1), (-12.4, 7), (-9, 15), (-3, 19), (3, 19), (9, 15), (12.4, 7), (11.4, -1), (9, 3), (5.6, 8), (0, 9.4), (-5.6, 8), (-9, 3)]
        ink.poly([H(*q) for q in dome], COLOR['steel'][2], hd - 7)
        ink.poly([H(*q) for q in [(-12.4, 7), (-9, 15), (-3, 19), (-4, 14), (-8, 8), (-10.4, 2)]], COLOR['steel'][3], hd - 7.05, False)
        ink.poly([H(*q) for q in [(12.4, 7), (11.4, -1), (9, 3), (9.4, 9), (10, 12)]], COLOR['steel'][1], hd - 7.05, False)
        ink.poly([H(*q) for q in [(-11.8, 6.6), (11.8, 6.6), (11.4, 10), (-11.4, 10)]], COLOR[tier][2], hd - 7.2)
        ink.poly([H(*q) for q in [(-11.4, 10), (11.4, 10), (11, 11.4), (-11, 11.4)]], COLOR['gold'][2], hd - 7.25, False)
        for sx in (-1, 1):                      # cheek guards
            ink.poly([H(sx * 9.2, 3), H(sx * 12, 2), H(sx * 12.4, -7), H(sx * 9, -9), H(sx * 8.4, -2)], COLOR['steel'][1], hd - 7.1)
        if front > -.4:
            ink.poly([H(*q) for q in [(-.9, 6.6), (.9, 6.6), (1.2, -2.6), (-1.2, -2.6)]], COLOR['steel'][3], hd - 7.3)
            ink.poly([H(*q) for q in [(-1.8, 12), (0, 14.4), (1.8, 12), (0, 9.8)]], COLOR['glow' if azure else 'plume'][2], hd - 7.4)
        if azure:
            for sx in (-1, 1):                  # swept-back white wings
                wing = [(sx * 11.4, 10), (sx * 17, 15), (sx * 20.4, 22.4), (sx * 15.6, 20.4), (sx * 16.6, 26), (sx * 12, 21.4), (sx * 11.6, 27.4), (sx * 9, 17.4)]
                ink.poly([H(*q) for q in wing], COLOR['wing'][2], hd - 7.1)
                ink.poly([H(*q) for q in [(sx * 11.4, 10), (sx * 15.6, 14), (sx * 17.4, 19), (sx * 13, 16)]], COLOR['wing'][1], hd - 7.15, False)
        else:
            plume = [(-2.4, 17.6), (2.4, 17.6), (4.4, 22), (3, 27), (-2, 29.6), (-5, 25), (-6.4, 20)]
            ink.poly([H(*q) for q in plume], COLOR['plume'][2], hd - 7.1)
            ink.poly([H(*q) for q in [(2.4, 17.6), (4.4, 22), (3, 27), (.4, 28.6), (1.4, 22)]], COLOR['plume'][1], hd - 7.15, False)


    # ---- the game master's golden set ----
    ink = inks['armor_gm']
    s = sw * .6
    torso(ink, 'gilt', 9.8, 5.0, 38, 69)
    # Crossed lapels of deep gold over a pearl vest, edged in pearl, with a ruby clasp.
    ink.plate([xf(q) for q in [(-3.6, 5.5, 69), (3.6, 5.5, 69), (0, 5.6, 53)]], 'pearl', 2)
    ink.plate([xf(q) for q in [(-7, 5.4, 69), (-3.4, 5.5, 69), (4.8, 5.7, 41), (1.4, 5.7, 41)]], 'brocade', 2)
    ink.plate([xf(q) for q in [(7, 5.4, 69), (3.4, 5.5, 69), (-4.8, 5.8, 41), (-1.4, 5.8, 41)]], 'brocade', 1)
    ink.plate([xf(q) for q in [(0, 6, 64), (1.9, 6, 61.6), (0, 6, 59.2), (-1.9, 6, 61.6)]], 'ruby', 2, True)
    ink.plate([xf(q) for q in [(0, 6.1, 63), (.8, 6.1, 61.8), (0, 6.1, 60.6), (-.8, 6.1, 61.8)]], 'ruby', 3, True)
    ink.bone(xf((-5.2, 0, 69.6)), xf((5.2, 0, 69.6)), 3.5, 3.5, 'pearl', -1.4, 2)      # stand collar
    ink.bone(xf((-5.2, 0, 71)), xf((5.2, 0, 71)), 3.0, 3.0, 'gilt', -1.45, 3)
    # A long bell skirt (a six-point outline per face: top, mid, hem), split at the front over a deep-gold underskirt,
    # hemmed in pearl and ruby, with a ruby obi hiding the join at the waist.
    hem = 9
    rings = [(42, 11., 6.6), (26, 13., 10.6), (hem, 15.6, 15.8)]
    sway = lambda z: s * (42 - z) / 33
    def face_pts(sy=None, sx=None):
        """Six points round one face of the skirt: top left, top right and down the right edge, then back up the left."""
        if sy is not None:
            left = [(-wx + sway(z), sy * dy, z) for z, wx, dy in rings]
            right = [(wx + sway(z), sy * dy, z) for z, wx, dy in rings]
        else:
            left = [(sx * wx + sway(z), -dy, z) for z, wx, dy in rings]
            right = [(sx * wx + sway(z), dy, z) for z, wx, dy in rings]
        return [xf(q) for q in [left[0], right[0], right[1], right[2], left[2], left[1]]]
    B = 6.
    def face_y(z):                      # where the skirt surface is at height z (the rings, interpolated)
        for (z0, _, y0), (z1, _, y1) in zip(rings, rings[1:]):
            if z1 <= z <= z0:
                return y0 + (y1 - y0) * (z0 - z) / (z0 - z1)
        return rings[-1][2]
    for sy in (-1, 1):
        surface(ink, face_pts(sy=sy), 'gilt', 2, B)
    for sx in (-1, 1):
        surface(ink, face_pts(sx=sx), 'gilt', 1, B)
    yf = rings[-1][2]
    wx = rings[-1][1]
    def reach(z):                       # half-width of the skirt at height z
        return rings[0][1] + (13. - rings[0][1]) * (42 - z) / 16 if z > 26 else 13. + (wx - 13.) * (26 - z) / 17
    for sy in (-1, 1):                  # pleats: darker panels running from the waist to the hem
        for k_ in (-1, 1) if sy > 0 else (-2, -1, 1, 2):
            lo, hi = (k_ * .45, k_ * .62) if sy > 0 else (k_ * .2 - .08 * k_ / abs(k_) , k_ * .2 + .22 * k_ / abs(k_))
            pts = [(lo * reach(42), sy * (face_y(42) + .12), 42), (hi * reach(42), sy * (face_y(42) + .12), 42),
                   (hi * reach(hem + 4) + sway(hem), sy * (face_y(hem + 4) + .12), hem + 4), (lo * reach(hem + 4) + sway(hem), sy * (face_y(hem + 4) + .12), hem + 4)]
            surface(ink, [xf(q) for q in pts], 'gilt', 1, B + .1, False)
    surface(ink, [xf(q) for q in [(-3.6, 6.8, 42), (3.6, 6.8, 42), (6.6 + sway(hem), yf + .4, hem), (-6.6 + sway(hem), yf + .4, hem)]], 'brocade', 2, B + .1)
    for sx in (-1, 1):                  # pearl piping down both sides of the split
        surface(ink, [xf(q) for q in [(sx * 3.6, 6.9, 42), (sx * 4.3, 6.9, 42), (sx * 7.3 + sway(hem), yf + .5, hem), (sx * 6.6 + sway(hem), yf + .5, hem)]], 'pearl', 2, B + .2, False)
    for x_ in (-1, 1):                  # a woven seam on each side of the front
        surface(ink, [xf(q) for q in [(x_ * 7.2, face_y(36) + .15, 36), (x_ * 7.9, face_y(36) + .15, 36), (x_ * 12.4 + sway(hem), face_y(hem + 3) + .15, hem + 3), (x_ * 11.7 + sway(hem), face_y(hem + 3) + .15, hem + 3)]], 'brocade', 1, B + .2, False)
    def band(sy, lo, hi, mat, tone, bias):
        pts = [(-rings[-1][1] + sway(hem), sy * (face_y(lo) + .2), lo), (rings[-1][1] + sway(hem), sy * (face_y(lo) + .2), lo),
               (rings[-1][1] + sway(hem), sy * (face_y(hi) + .2), hi), (-rings[-1][1] + sway(hem), sy * (face_y(hi) + .2), hi)]
        # the face is wider at the hem than at height `hi`, so the band narrows with it
        shrink = lambda z: (rings[0][1] + (rings[-1][1] - rings[0][1]) * (42 - z) / 33) if z > 26 else (13. + (rings[-1][1] - 13.) * (26 - z) / 17)
        pts = [(-shrink(z) + sway(hem), y, z) for (_, y, z) in (pts[0], pts[3])]
        pts = [(-shrink(lo) + sway(hem), sy * (face_y(lo) + .2), lo), (shrink(lo) + sway(hem), sy * (face_y(lo) + .2), lo),
               (shrink(hi) + sway(hem), sy * (face_y(hi) + .2), hi), (-shrink(hi) + sway(hem), sy * (face_y(hi) + .2), hi)]
        surface(ink, [xf(q) for q in pts], mat, tone, bias, False)
    for sy in (-1, 1):
        band(sy, hem, hem + 3, 'pearl', 2, B + .3)
        band(sy, hem + 3, hem + 3.9, 'ruby', 2, B + .3)
        for x_ in (-11, -5.5, 0, 5.5, 11):  # gold lozenges along the hem
            y_ = sy * (face_y(hem + 1.5) + .4)
            surface(ink, [xf(q) for q in [(x_ - 1.5 + sway(hem), y_, hem + 1.5), (x_ + sway(hem), y_, hem + 2.9), (x_ + 1.5 + sway(hem), y_, hem + 1.5), (x_ + sway(hem), y_, hem + .2)]], 'gilt', 3, B + .5, False)
    for sx in (-1, 1):
        surface(ink, [xf(q) for q in [(sx * (wx + .2) + sway(hem), -yf, hem + 3), (sx * (wx + .2) + sway(hem), yf, hem + 3), (sx * (wx + .2) + sway(hem), yf, hem), (sx * (wx + .2) + sway(hem), -yf, hem)]], 'pearl', 1, B + .3, False)
    # The back carries a large embroidered ruby-and-pearl diamond.
    def back(x_, z):
        return (x_ + sway(z), -(face_y(z) + .3), z)
    surface(ink, [xf(q) for q in [back(0, 38), back(5.4, 28), back(0, 16), back(-5.4, 28)]], 'pearl', 2, B + .3, False)
    surface(ink, [xf(q) for q in [back(0, 35), back(3.8, 28), back(0, 19.4), back(-3.8, 28)]], 'ruby', 2, B + .4, False)
    surface(ink, [xf(q) for q in [back(0, 31), back(1.8, 28), back(0, 24.6), back(-1.8, 28)]], 'gilt', 3, B + .5, False)
    # A ruby obi with a gilt knot and two hanging tails.
    for sy in (-1, 1):
        ink.plate([xf(q) for q in [(-11.8, sy * 7.1, 45), (11.8, sy * 7.1, 45), (11.8, sy * 7.1, 39.6), (-11.8, sy * 7.1, 39.6)]], 'ruby', 2 if sy > 0 else 1)
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * 11.8, -7.1, 45), (sx * 11.8, 7.1, 45), (sx * 11.8, 7.1, 39.6), (sx * 11.8, -7.1, 39.6)]], 'ruby', 1)
    ink.plate([xf(q) for q in [(-11.8, 7.2, 43.6), (11.8, 7.2, 43.6), (11.8, 7.2, 43), (-11.8, 7.2, 43)]], 'gilt', 3, True)
    ink.plate([xf(q) for q in [(0, 7.5, 46.4), (3, 7.5, 42.4), (0, 7.5, 38.4), (-3, 7.5, 42.4)]], 'gilt', 2)
    ink.plate([xf(q) for q in [(0, 7.6, 44.6), (1.5, 7.6, 42.4), (0, 7.6, 40.2), (-1.5, 7.6, 42.4)]], 'ruby', 3, True)
    ink.plate([xf(q) for q in [(1.2, 7.3, 40), (4.2 + s * .5, 7.6, 40), (5.8 + sway(24), 9, 22), (2.4 + sway(24), 8.8, 25)]], 'ruby', 2)
    ink.plate([xf(q) for q in [(-1.2, 7.3, 40), (-4.2 + s * .5, 7.6, 40), (-5.8 + sway(24), 9, 25), (-2.4 + sway(24), 8.8, 28)]], 'ruby', 1)
    # Wide bell sleeves with a pearl cuff, and golden boots under the hem.
    for key in 'LR':
        j = joints[key]
        ink.bone(j['shoulder'], j['elbow'], 3.9, 3.7, 'gilt', -.8)
        ink.bone(j['elbow'], cuff(j, .3), 3.7, 5.2, 'gilt', -.75)
        ink.bone(cuff(j, .34), cuff(j, .2), 5.3, 5.5, 'pearl', -.9, 2)
        ink.bone(cuff(j, .2), cuff(j, .16), 5.5, 5.5, 'ruby', -.95, 2)
        leg = j['ankle'] - j['knee']
        ink.bone(j['knee'] + leg * .62, j['ankle'], 3.3, 2.7, 'brocade', -.8, 2)
        ink.bone(j['knee'] + leg * .6, j['knee'] + leg * .7, 3.6, 3.5, 'pearl', -.9, 2)
        ink.bone(j['ankle'] + V(0, -1, -1), j['ankle'] + V(0, 5.2, -2), 3.0, 2.9, 'gilt', -.8, 2)
        ink.bone(j['ankle'] + V(0, 4.4, -1.9), j['ankle'] + V(0, 6, -2.3), 2.7, 2.4, 'pearl', -.9, 3)

    # A golden top hat: a tall straight crown with a ruby band and gilt buckle on a wide brim, tilted a little.
    ink = inks['head_gm']
    def ellipse(cx, cy, rx, ry, n=22, lo=0., hi=math.tau):
        return [(cx + rx * math.cos(lo + (hi - lo) * i / n), cy + ry * math.sin(lo + (hi - lo) * i / n)) for i in range(n + 1)]
    ink.poly([H(*q) for q in [(-8.2, 12), (-7.4, 29), (7.4, 29), (8.2, 12)]], COLOR['gilt'][2], hd - 7)
    ink.poly([H(*q) for q in [(8.2, 12), (7.4, 29), (4.2, 29), (5, 12)]], COLOR['gilt'][1], hd - 7.05, False)
    ink.poly([H(*q) for q in [(-6.8, 12), (-6.2, 29), (-4.2, 29), (-4.8, 12)]], COLOR['gilt'][3], hd - 7.05, False)
    ink.poly([H(*q) for q in ellipse(0, 29, 7.4, 2)], COLOR['gilt'][3], hd - 7.08)
    ink.poly([H(*q) for q in ellipse(0, 29, 5.4, 1.1)], COLOR['brocade'][2], hd - 7.1, False)
    ink.poly([H(*q) for q in ellipse(0, 11.4, 13.6, 3)], COLOR['gilt'][2], hd - 7.2)
    ink.poly([H(*q) for q in ellipse(0, 10.6, 12.8, 1.8, 14, 0, math.pi)[::-1] + ellipse(0, 11.4, 13.6, 3, 14, math.pi, math.tau)[::-1]], COLOR['gilt'][1], hd - 7.25, False)
    ink.poly([H(*q) for q in ellipse(0, 12, 12.6, 1.9, 12, math.pi * .6, math.pi * 1.2)], COLOR['pearl'][3], hd - 7.3, False)
    ink.poly([H(*q) for q in [(-8.1, 14), (8.1, 14), (7.9, 19.2), (-7.9, 19.2)]], COLOR['ruby'][2], hd - 7.4)
    ink.poly([H(*q) for q in [(8.1, 14), (7.9, 19.2), (5, 19.2), (5.4, 14)]], COLOR['ruby'][1], hd - 7.45, False)
    ink.poly([H(*q) for q in [(-8.1, 19.2), (7.9, 19.2), (7.9, 20.3), (-8.1, 20.3)]], COLOR['pearl'][2], hd - 7.45, False)
    ink.poly([H(*q) for q in [(-8.2, 12.9), (8.2, 12.9), (8.1, 14), (-8.1, 14)]], COLOR['pearl'][2], hd - 7.45, False)
    if front > -.4:
        ink.poly([H(*q) for q in [(-3.2, 13.4), (3.2, 13.4), (3.2, 19.8), (-3.2, 19.8)]], COLOR['gilt'][3], hd - 7.5)
        ink.poly([H(*q) for q in [(-1.8, 14.6), (1.8, 14.6), (1.8, 18.6), (-1.8, 18.6)]], COLOR['ruby'][2], hd - 7.55, False)
        ink.poly([H(*q) for q in [(-.7, 15.6), (.7, 15.6), (.7, 17.6), (-.7, 17.6)]], COLOR['ruby'][3], hd - 7.6, False)
        star = [(r * math.sin(i * math.pi / 5), 24.4 + r * math.cos(i * math.pi / 5)) for i, r in enumerate([3.6, 1.6] * 5)]
        ink.poly([H(*q) for q in star], COLOR['pearl'][2], hd - 7.5)

    # Sword in the right hand, round shield on the left forearm.
    hand_r, hand_l = joints['R']['hand'], joints['L']['hand']
    u = R @ unit(V(*p['blade']))
    across = R @ V(1, 0, 0)
    if p['dropped']:
        hand_r, u, across = V(24, -3, 2.5), unit(V(.4, 1, 0)), V(0, 0, 1)
    shield_n = R @ unit(V(*p['shield']))
    elbow_l = joints['L']['elbow']
    centre = (elbow_l + hand_l) / 2 + shield_n * 3.6
    if p['dropped']:
        centre, shield_n = V(-20, 8, 2), V(0, 0, 1)
    a1 = unit(np_cross(shield_n, V(0, 0, 1))) if abs(shield_n[2]) < .95 else V(1, 0, 0)
    a2 = unit(np_cross(shield_n, a1))
    for key in ('weapon_sword', 'weapon_royal'):
        ink = inks[key]
        royal = key == 'weapon_royal'
        blade = 'glow' if royal else 'steel'
        length = 37 if royal else 34
        grip = hand_r - u * 4.4
        guard = hand_r + u * 2.2
        tip = guard + u * length
        ink.bone(grip, guard, 1.3, 1.3, 'leather', -.1, 2)
        ink.bone(grip - u * 1.2, grip, 1.7, 1.7, 'gold', -.12, 2)
        ink.plate([guard - across * 5.4 - u * .8, guard + across * 5.4 - u * .8, guard + across * 5 + u * 1.2, guard - across * 5 + u * 1.2], 'gold', 2)
        w = 4.0 if royal else 3.4
        ink.plate([guard + u * 1.2 - across * w, guard + u * 1.2 + across * w, tip - across * .6 + u * 0, tip + u * 3.4, tip + across * .6, ], 'steel', 3 if not royal else 3)
        ink.plate([guard + u * 1.2, guard + u * 1.2 + across * w, tip + across * .6, tip + u * 3.4], 'steel', 2, True)
        ink.plate([guard + u * 2.4, guard + u * 2.4 + across * .6, tip - u * 2, tip - u * 2 - across * .6], 'glow' if royal else 'steel', 3, True)
        if royal:
            ink.plate([guard - across * 2 + u * .2, guard + u * 3.8, guard + across * 2 + u * .2, guard - u * 2], 'glow', 3, True)
        # Shield: rim, face in the tier colour (gold on the royal), boss and a cross emblem.
        face = 'gold' if royal else 'steel'
        ink.plate(disc(centre, a1, a2, 11.6, 11.6), 'gold' if royal else 'steel', 1)
        ink.plate(disc(centre + shield_n * .8, a1, a2, 10.2, 10.2), face, 2)
        ink.plate(disc(centre + shield_n * 1.4, a1, a2, 6.8, 6.8), 'azure' if royal else 'crimson', 2, True)
        ink.plate(disc(centre + shield_n * 2.2, a1, a2, 2.4, 2.4, 8), 'gold' if not royal else 'glow', 3, True)
        ink.plate([centre + shield_n * 1.8 + a2 * 6, centre + shield_n * 1.8 + a1 * .9, centre + shield_n * 1.8 - a2 * 6, centre + shield_n * 1.8 - a1 * .9], 'gold', 3, True)

    # The game master's blade: a long gilt sword with a winged guard and ruby wrap, and a round shield with a sunburst.
    ink = inks['weapon_gm']
    grip = hand_r - u * 4.8
    guard = hand_r + u * 2.2
    tip = guard + u * 38
    base = guard + u * 1.6
    ink.bone(grip, guard, 1.4, 1.4, 'ruby', -.1, 2)
    ink.bone(grip - u * 1.8, grip, 2.2, 2.2, 'gilt', -.12, 3)
    ink.bone(grip - u * 2.7, grip - u * 2.2, 1.3, 1.3, 'ruby', -.14, 3)
    ink.plate([guard - across * 7.8 - u * .6, guard - across * 5.4 + u * 3, guard - across * 2.4 + u * .8, guard + across * 2.4 + u * .8, guard + across * 5.4 + u * 3, guard + across * 7.8 - u * .6, guard + across * 4 - u * 1.8, guard - across * 4 - u * 1.8], 'gilt', 2)
    ink.plate([guard + across * 2.4 + u * .8, guard + across * 5.4 + u * 3, guard + across * 7.8 - u * .6, guard + across * 4 - u * 1.8], 'gilt', 1, True)
    ink.plate([guard + u * 2.4, guard + across * 1.6 + u * .6, guard - u * 1.2, guard - across * 1.6 + u * .6], 'ruby', 3, True)
    ink.plate([base - across * 3.4, base + across * 3.4, tip + across * .8, tip + u * 4, tip - across * .8], 'gilt', 2)
    ink.plate([base, base + across * 3.4, tip + across * .8, tip + u * 4], 'gilt', 1, True)
    ink.plate([base + u * 1.2, base + u * 1.2 + across * .8, tip - u * 2, tip - u * 2 - across * .8], 'pearl', 3, True)
    face_n = shield_n
    ink.plate(disc(centre, a1, a2, 12.2, 12.2, 20), 'gilt', 1)
    ink.plate(disc(centre + face_n * .8, a1, a2, 10.8, 10.8, 20), 'gilt', 2)
    ink.plate(disc(centre + face_n * 1.3, a1, a2, 9.2, 9.2, 20), 'pearl', 2, True)
    ink.plate(disc(centre + face_n * 1.7, a1, a2, 7.8, 7.8, 20), 'ruby', 2, True)
    burst = [centre + face_n * 2.2 + (a1 * math.cos(i * math.pi / 8) + a2 * math.sin(i * math.pi / 8)) * (7.2 if i % 2 == 0 else 3.4) for i in range(16)]
    ink.plate(burst, 'gilt', 3, True)
    ink.plate(disc(centre + face_n * 2.7, a1, a2, 2.8, 2.8, 12), 'ruby', 3, True)
    for i in range(8):                  # studs round the rim
        t = i * math.pi / 4 + .39
        ink.plate(disc(centre + face_n * 1.1 + (a1 * math.cos(t) + a2 * math.sin(t)) * 10, a1, a2, .9, .9, 6), 'pearl', 3, True)
    gg.draw(inks, R, xf, joints, head)
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}


def np_cross(a, b):
    return V(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


NAKED = {slot: 'none' for slot in SLOTS}
CRIMSON = {'armor': 'crimson', 'shoulders': 'crimson', 'gloves': 'crimson', 'head': 'crimson', 'weapon': 'sword'}
AZURE = {'armor': 'azure', 'shoulders': 'azure', 'gloves': 'azure', 'head': 'azure', 'weapon': 'royal'}
GM = {'armor': 'gm', 'shoulders': 'none', 'gloves': 'none', 'head': 'gm', 'weapon': 'gm'}
GENERIC = {'armor': 'crimson', 'shoulders': 'ironhide', 'gloves': 'duelist', 'head': 'ironhide', 'pants': 'wayfarer',
           'necklace': 'moonstone', 'accessory': 'amber', 'weapon': 'sword'}
SHEET = cc.Sheet(
    'warrior', files='warrior_layered', pixel='warrior_cel_', mats=MATS, clips=CLIPS, slots=SLOTS, gear=GEAR, render=render_frame,
    revision=cc.revision_of([open(__file__).read(), open(gg.__file__).read()]),
    # The auto grouping would put the three gm layers into the generic and trinkets sprites and change them; this is the
    # same grouping the five older sprites already have, plus one `gm` sprite per clip and facing.
    groups={'crimson': ['body', 'armor_crimson', 'shoulders_crimson', 'gloves_crimson', 'head_crimson'],
            'azure': ['ref_body', 'armor_azure', 'shoulders_azure', 'gloves_azure', 'head_azure'],
            'arms': ['ref_body', 'weapon_sword', 'weapon_royal'],
            'generic': ['ref_body', 'pants_wayfarer', 'shoulders_ironhide', 'gloves_duelist', 'head_ironhide'],
            'trinkets': ['ref_body', 'necklace_moonstone', 'accessory_amber'],
            'gm': ['ref_body', 'armor_gm', 'head_gm', 'weapon_gm']},
    default_equip={'armor': 'crimson', 'shoulders': 'none', 'gloves': 'none', 'head': 'none', 'weapon': 'sword'},
    meta={'attack': {'duration': .42, 'impact': .21}, 'portrait': [57, 15, 46, 46]},
    combos=[('naked', NAKED), ('crimson', CRIMSON), ('azure', AZURE), ('generic', GENERIC), ('gm', GM)])

if __name__ == '__main__':
    SHEET.cli()
