#!/usr/bin/env python3
"""Mage: a long-haired anime spellcaster in the Hunter's cel style on the shared joint rig (see cel_common.py).

usage: make_mage_cel_sprites.py preview [clip|all] [directory]   contact sheets (scratch), rows = facings
       make_mage_cel_sprites.py build [--replace]                 render every frame, create the editable PixelFlow sprites mage_cel_<clip>_<facing>_<group>
       make_mage_cel_sprites.py export [--local]                  PixelFlow (edits kept) -> client/assets/mage_*.png + mage_sprites.txt

Eleven layers: body + armor, shoulders, gloves, head (apprentice, runic) + weapon (ash staff, crystal staff). The
weapon layers carry the whole staff and its glowing head. build --replace DISCARDS MAGE HAND EDITS (the old painted
mage sprites, prefix mage_256_, are a different set and are never touched). 160x160 frames like the other classes.
"""
import math

import cel_common as cc
from cel_common import V, unit, rig

SLOTS = {'armor': ('apprentice', 'runic'), 'shoulders': ('apprentice', 'runic'), 'gloves': ('apprentice', 'runic'),
         'head': ('apprentice', 'runic'), 'weapon': ('ash', 'crystal')}
MATS = {
    **cc.FACE_MATS,
    'hair': ['#4a2a68', '#7a52a0', '#ac78c4', '#dcb4ec'],
    'cloth': ['#3a3860', '#605e90', '#9a98c8', '#d4d2f0'],
    'pants': ['#1c2038', '#30365a', '#4e5a86', '#7a88b4'],
    'azure': ['#1c3a78', '#2e62b8', '#5a9af0', '#a8d0ff'],     # apprentice robes
    'indigo': ['#241848', '#44307e', '#6e52b8', '#a88cf0'],    # runic vestments
    'gold': ['#6e4a12', '#b0801f', '#e8b840', '#fff0a0'],
    'ivory': ['#9a8a7a', '#c9bca8', '#f0e6d0', '#fffcf0'],
    'umber': ['#2a1a16', '#47291f', '#6e4331', '#9a6a4c'],
    'wood': ['#3a2218', '#6b4128', '#a8703f', '#dca66a'],
    'silver': ['#35485e', '#6e87a3', '#b4c9de', '#f0f6ff'],
    'rune': ['#2a40a0', '#4a8af0', '#90d8ff', '#f0ffff'],      # crystal, orb and rune glow
    'iris': ['#2a2a78', '#4a4ad0', '#8aa0ff', '#e0ecff'],
}
PALETTE, COLOR = cc.palette_of(MATS)
DEFAULT = dict(root=(0, 0, 0), lean=3, twist=0, roll=0, sway=0, eyes='open',
               handL=(-12, 6, 49), handR=(13, 6, 50), footL=(-5, 0, 4), footR=(5, 0, 4),
               staff=(.02, .05, 1), butt=48, flare=0., ground=False, dropped=False)


def idle(k):
    a = k / 6 * math.tau
    return dict(root=(0, 0, -.35 * math.sin(a)), sway=math.sin(a), flare=.2 + .2 * math.sin(a),
                handL=(-12, 6, 49 + .5 * math.sin(a)), eyes='closed' if k == 4 else 'open')


def walk(k):
    q = k / 8
    a = q * math.tau
    def foot(s, t):
        t %= 1
        return (s * 5, 9 - t * 36 if t < .5 else -9 + (t - .5) * 36,
                4 + (6 * math.sin((t - .5) * math.tau) if t >= .5 else 0))
    return dict(lean=13, roll=2 * math.sin(a), twist=5 * math.sin(a),
                root=(0, 0, -.6 * math.cos(a * 2)), sway=3 * math.sin(a), flare=.3,
                handL=(-14, -3 - math.sin(a) * 3, 52), handR=(14, 5 + math.sin(a) * 3, 53),
                staff=(.02, .12 + .18 * math.sin(a), 1), butt=30,
                footL=foot(-1, q), footR=foot(1, q + .5))


def attack(k):
    # Raise the staff, draw it back, bring it forward and loose a spell on frame 4 (the impact), hold, lower.
    left = [(-12, 6, 49), (-10, 16, 62), (-12, 4, 72), (-6, 22, 66), (-4, 27, 62), (-6, 24, 60), (-10, 14, 54), (-12, 6, 49)][k]
    right = [(13, 6, 50), (14, 10, 66), (13, -2, 62), (12, 14, 58), (12, 20, 54), (12, 19, 53), (13, 12, 54), (13, 6, 50)][k]
    staff = [(.02, .05, 1), (.02, .2, 1), (.02, -.35, 1), (.02, .45, .9), (.02, .7, .75), (.02, .65, .78), (.02, .35, .95), (.02, .05, 1)][k]
    f = [0, -.3, -.55, .4, 1, .7, .25, 0][k]
    return dict(lean=[3, 0, -6, 6, 13, 10, 6, 3][k], twist=[0, -8, -14, 8, 18, 14, 6, 0][k],
                root=(0, max(0, f) * 1.6, -.5 * abs(f)), handL=left, handR=right, staff=staff, butt=24,
                flare=[.2, .6, 1.1, 1.3, 2.2, 1.6, .8, .2][k], sway=-3 * f,
                footL=(-6, 3 * max(0, f), 4), footR=(6, -4 * max(0, f), 4))


def hurt(k):
    f = [.25, 1, .4, 0][k]
    return dict(lean=-14 * f, root=(0, -2 * f, 0), twist=9 * f, flare=.5 * f,
                handL=(-16, 5, 56), handR=(15, 5, 54), eyes='closed' if k < 3 else 'open', sway=-2 * f,
                staff=(.02, -.3 * f, 1), butt=26)


def die(k):
    return dict(lean=[-5, -23, -43, -66, -85, -90, -90, -90][k],
                root=(0, 8 if k >= 3 else 0, 0), eyes='closed',
                handL=(-17, 1, 50), handR=(17, 1, 49), butt=26,
                footL=(-5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                footR=(5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                ground=k >= 3, dropped=k >= 2)


CLIPS = {'idle': (6, 6, idle), 'walk': (12, 8, walk), 'attack': (20, 8, attack),
         'hurt': (10, 4, hurt), 'die': (8, 8, die)}
GEAR = {
    'armor': {'none': {'name': 'Simple cloth', 'defense': 0},
              'apprentice': {'name': 'Apprentice robes', 'defense': 2}, 'runic': {'name': 'Runic vestments', 'defense': 5}},
    'shoulders': {'none': {'name': 'Bare shoulders', 'defense': 0},
                  'apprentice': {'name': "Apprentice's Capelet", 'defense': 1}, 'runic': {'name': 'Runic Pauldrons', 'defense': 2}},
    'gloves': {'none': {'name': 'Bare hands', 'defense': 0},
               'apprentice': {'name': "Apprentice's Gloves", 'defense': 1}, 'runic': {'name': 'Runic Gloves', 'defense': 2}},
    'head': {'none': {'name': 'Bare head', 'defense': 0},
             'apprentice': {'name': "Apprentice's Hat", 'defense': 1}, 'runic': {'name': 'Runic Archmage Hat', 'defense': 2}},
    'weapon': {'none': {'name': 'Empty hands', 'attack': 0},
               'ash': {'name': 'Ash staff', 'attack': 4}, 'crystal': {'name': 'Crystal staff', 'attack': 9}},
}


def ring(centre, a1, a2, rx, ry, n=10, phase=0.):
    return [centre + a1 * math.cos(i / n * math.tau + phase) * rx + a2 * math.sin(i / n * math.tau + phase) * ry for i in range(n)]


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R, xf, joints = cc.skeleton(p)
    inks = {part: cc.Ink(psi, COLOR) for part in SHEET.parts}
    body = inks['body']
    torso = lambda ink, mat, *a: cc.torso(ink, xf, mat, *a)
    cc.base_body(body, xf, joints, R)
    head = cc.head_frame(body, xf, psi, p, turn=.6)
    H, hd, front, side = head['H'], head['hd'], head['front'], head['side']
    sw = p['sway']
    # Long hair: a back sheet to the waist, blunt bangs with two long face-framing locks, a glossy ring highlight.
    body.plate([xf(q) for q in [(-6.5, -5, 84), (6.5, -5, 84), (9 + sw * .6, -8.6, 60), (8 + sw, -9.6, 40), (0 + sw * 1.2, -10.4, 36), (-8 + sw, -9.6, 40), (-9 + sw * .6, -8.6, 60)]], 'hair', 1)
    body.plate([xf(q) for q in [(-3, -5.4, 82), (3, -5.4, 82), (4.4 + sw * .8, -9.6, 58), (3 + sw * 1.2, -10.2, 42), (-1 + sw, -10, 50)]], 'hair', 2, True)
    if not cc.face(body, head, p):
        body.poly([H(*q) for q in [(-9.5, 8), (-10.5, 0), (-8.5, -8), (-4, -10.5), (5, -9.5), (9.5, -5), (10.5, 4), (6.5, 13), (-3, 14)]], COLOR['hair'][2], hd - 5)
        body.poly([H(*q) for q in [(-8, 6), (-2, 9), (4, 8), (8, 3), (4, 5), (-3, 5.5)]], COLOR['hair'][3], hd - 5.05, False)
    crown = [(-11, -13), (-12.2, 5), (-10, 13), (-3, 17.5), (4, 17.5), (10.4, 13), (12.2, 5), (11, -13),
             (9.4, -2), (9.4, 5.4), (5, 5.8), (1, 4.2), (-1, 5.6), (-5, 5.2), (-9.4, 5.4), (-9.4, -2)]
    body.poly([H(*q) for q in crown], COLOR['hair'][1], hd - 6)
    body.poly([H(*q) for q in [(-9.5, 12), (-3, 16), (4, 15.6), (10, 11), (9.4, 8), (3, 12), (-3, 12.6), (-9, 8)]], COLOR['hair'][2], hd - 6.1, False)
    body.poly([H(*q) for q in [(-6, 14.4), (-1, 15.8), (4, 15), (0, 13.6), (-5, 12.6)]], COLOR['hair'][3], hd - 6.2, False)
    body.poly([H(*q) for q in [(-11.4, 4), (-9.6, 4), (-9.2, -10), (-10.4, -13)]], COLOR['hair'][2], hd - 6.1, False)

    cuffs = lambda j, f: j['hand'] + (j['elbow'] - j['hand']) * f
    for tier in ('apprentice', 'runic'):
        ink = inks['armor_' + tier]
        runic = tier == 'runic'
        col, trim = ('indigo', 'gold') if runic else ('azure', 'ivory')
        torso(ink, col, 8.6, 4.3, 40, 69)
        ink.plate([xf(q) for q in [(-3.6, 4.6, 69), (3.6, 4.6, 69), (0, 4.7, 56)]], 'ivory', 3)
        if runic:
            ink.plate([xf(q) for q in [(-6.4, -4.6, 69), (6.4, -4.6, 69), (8.6, -5.4, 80), (-8.6, -5.4, 80)]], col, 1)
            ink.plate([xf(q) for q in [(-8.6, -5.4, 80), (8.6, -5.4, 80), (8, -5.4, 78), (-8, -5.4, 78)]], 'gold', 3, True)
        ink.bone(xf((-5.4, 1.2, 69)), xf((5.4, 1.2, 69)), 2.5, 2.5, trim, -1.2, 3)
        # Robe skirt: apprentice to the knee, runic to the shin with the front split open and a trailing back.
        hem, wide, deep, s = (10, 12.6, 8.6, sw * .9) if runic else (21, 11.6, 8, sw * .9)
        for sy, tone in ((-1, 1), (1, 2)):
            if runic and sy > 0:
                for sx in (-1, 1):
                    ink.plate([xf(q) for q in [(sx * 8.2, 4.6, 40), (sx * 1.6, 4.8, 40), (sx * 2.6 + s, 6, hem), (sx * wide + s, deep, hem + 1)]], col, 2)
            else:
                ink.plate([xf(q) for q in [(-8.2, sy * 4.6, 40), (8.2, sy * 4.6, 40), (wide + s, sy * deep, hem), (-wide + s, sy * deep, hem)]], col, tone)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 8.2, -4.6, 40), (sx * 8.2, 4.6, 40), (sx * wide + s, deep, hem), (sx * wide + s, -deep, hem)]], col, 1)
        for sy in (-1, 1):
            ink.plate([xf(q) for q in [(-wide + s, sy * deep, hem + 2.6), (wide + s, sy * deep, hem + 2.6), (wide + s, sy * deep, hem), (-wide + s, sy * deep, hem)]], trim, 2 if sy > 0 else 1, True)
        if runic:
            for x_ in (-6, -2, 2, 6):
                ink.plate([xf(q) for q in [(x_ - 1.2 + s, deep * .85, hem + 7), (x_ + s, deep * .85, hem + 9.6), (x_ + 1.2 + s, deep * .85, hem + 7), (x_ + s, deep * .85, hem + 4.6)]], 'rune', 3, True)
            ink.plate([xf(q) for q in [(0, 5.2, 66), (2, 5.2, 62), (0, 5.2, 58), (-2, 5.2, 62)]], 'rune', 3, True)
        # Sash with a gold buckle and two hanging tails.
        for sy in (-1, 1):
            ink.plate([xf(q) for q in [(-9, sy * 4.8, 44.5), (9, sy * 4.8, 44.5), (9, sy * 4.8, 40), (-9, sy * 4.8, 40)]], 'umber', 2 if sy > 0 else 1)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 9, -4.8, 44.5), (sx * 9, 4.8, 44.5), (sx * 9, 4.8, 40), (sx * 9, -4.8, 40)]], 'umber', 1)
        ink.plate([xf(q) for q in [(-2.2, 5, 45), (2.2, 5, 45), (2.2, 5, 39.6), (-2.2, 5, 39.6)]], 'gold', 3, True)
        ink.plate([xf(q) for q in [(2.2, 5.1, 43), (5.6 + s * .4, 5.3, 43), (6.4 + s * .6, 6.6, 24), (3.4 + s * .6, 6.4, 27)]], trim if not runic else 'rune', 2)
        ink.plate([xf(q) for q in [(-2.2, 5.1, 43), (-5, 5.3, 43), (-5.8 + s * .6, 6.4, 30), (-3.2 + s * .6, 6.4, 33)]], trim if not runic else 'rune', 1)
        # Bell sleeves to mid-forearm with a cuff, then boots (short and brown, or tall indigo with a gold cuff).
        for key in 'LR':
            j = joints[key]
            ink.bone(j['shoulder'], j['elbow'], 3.6, 3.3, col, -.8)
            ink.bone(j['elbow'], cuffs(j, .35), 3.3, 4.3, col, -.75)
            ink.bone(cuffs(j, .5), cuffs(j, .35), 4.1, 4.3, trim, -.9, 3)
            leg = j['ankle'] - j['knee']
            ink.bone(j['knee'] + leg * (.1 if runic else .5), j['ankle'], 3.2, 2.6, col if runic else 'umber', -.8, 2 if runic else 2)
            if runic:
                ink.bone(j['knee'] + leg * .1, j['knee'] + leg * .24, 3.7, 3.5, 'gold', -.95, 2)
            ink.bone(j['ankle'] + V(0, -1, -1), j['ankle'] + V(0, 4.5, -2), 2.6, 2.6, 'umber', -.8)

    for tier in ('apprentice', 'runic'):
        ink = inks['shoulders_' + tier]
        runic = tier == 'runic'
        if not runic:
            # Capelet: a short ivory-edged cape over the shoulders, front and back, with soft puffs.
            for sy, tone in ((-1, 1), (1, 2)):
                ink.plate([xf(q) for q in [(-10.4, sy * 5, 70.5), (10.4, sy * 5, 70.5), (12, sy * 5.6, 60), (0, sy * 6.2, 56.5), (-12, sy * 5.6, 60)]], 'azure', tone)
                ink.plate([xf(q) for q in [(-12, sy * 5.6, 60), (0, sy * 6.2, 56.5), (12, sy * 5.6, 60), (12, sy * 5.6, 62.2), (0, sy * 6.2, 58.7), (-12, sy * 5.6, 62.2)]], 'ivory', 2 if sy > 0 else 1, True)
            for sx in (-1, 1):
                ink.plate([xf(q) for q in [(sx * 10.4, -5, 70.5), (sx * 10.4, 5, 70.5), (sx * 12, 5.6, 60), (sx * 12, -5.6, 60)]], 'azure', 1)
            for key in 'LR':
                j = joints[key]
                out = R @ V(1 if key == 'R' else -1, 0, 0)
                ink.bone(j['shoulder'] + R @ V(0, 0, 2.6), j['shoulder'] + out * 4.2 - R @ V(0, 0, 1), 4.2, 3.8, 'azure', -1.0, 2)
        else:
            for key in 'LR':
                j = joints[key]
                sh = j['shoulder']
                out = R @ V(1 if key == 'R' else -1, 0, 0)
                upv = R @ V(0, 0, 1)
                ink.bone(sh - out * .6 + upv * 2.6, sh + out * 5 - upv * 1.2, 4.8, 4.3, 'gold', -1.0, 2)
                ink.bone(sh + out * 2.6 + upv * .8, sh + out * 7 - upv * 3.4, 4.1, 3.5, 'indigo', -1.15, 2)
                # A floating crystal shard above each shoulder.
                c0 = sh + out * 4.4 + upv * 8.5
                ink.plate([c0 + upv * 6.4, c0 + out * 2.4, c0 - upv * 3.4, c0 - out * 2.4], 'rune', 2)
                ink.plate([c0 + upv * 6.4, c0 + out * 2.4, c0 + upv * 1, c0 - out * .2], 'rune', 3, True)

    for tier in ('apprentice', 'runic'):
        ink = inks['gloves_' + tier]
        runic = tier == 'runic'
        for key in 'LR':
            j = joints[key]
            hand = j['hand']
            if runic:
                ink.bone(cuffs(j, .4), hand + (j['elbow'] - hand) * .05, 3.0, 2.6, 'gold', -.85, 2)
                ink.bone(cuffs(j, .4), cuffs(j, .3), 3.3, 3.3, 'indigo', -.95, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.5, 2.2, 'gold', -.9)
                ink.bone(hand + (j['elbow'] - hand) * .16, hand + (j['elbow'] - hand) * .1, 3.0, 3.0, 'rune', -1.05, 2)
            else:
                ink.bone(cuffs(j, .3), hand + (j['elbow'] - hand) * .04, 2.7, 2.4, 'ivory', -.85, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.4, 2.1, 'ivory', -.9)
                ink.bone(cuffs(j, .17), cuffs(j, .1), 2.9, 2.9, 'gold', -1.0, 2)

    for tier in ('apprentice', 'runic'):
        ink = inks['head_' + tier]
        runic = tier == 'runic'
        col, band = ('indigo', 'gold') if runic else ('azure', 'gold')
        wide, tip = (19, 34) if runic else (16, 33)
        lean = 9 if runic else 7                      # the tip flops sideways
        brim = [(-wide, 8.6), (-wide * .75, 12.6), (0, 14.4), (wide * .75, 12.6), (wide, 8.6), (wide * .72, 9), (0, 10.2), (-wide * .72, 9)]
        cone = [(-9.6, 12.6), (9.6, 12.6), (7.4, 22), (3.6, 31), (lean * .4, tip - 6), (-lean, tip - 4), (-lean * .6, tip - 10), (-5.4, 31), (-8, 22)]
        ink.poly([H(*q) for q in cone], COLOR[col][2], hd - 7)
        ink.poly([H(*q) for q in [(-9.6, 12.6), (-8, 22), (-5.4, 31), (-lean * .6, tip - 10), (-lean, tip - 4), (-lean * .4, 30), (-5, 22), (-6.6, 14)]], COLOR[col][3], hd - 7.05, False)
        ink.poly([H(*q) for q in [(9.6, 12.6), (7.4, 22), (3.6, 31), (lean * .4, tip - 6), (2, 30), (5.4, 22), (6.6, 14)]], COLOR[col][1], hd - 7.05, False)
        ink.poly([H(*q) for q in brim], COLOR[col][1], hd - 7.2)
        ink.poly([H(*q) for q in [(-9.8, 12.2), (9.8, 12.2), (9.4, 15.6), (-9.4, 15.6)]], COLOR[band][2], hd - 7.3)
        if front > -.4:
            ink.poly([H(*q) for q in [(-2, 13.8), (0, 16.4), (2, 13.8), (0, 11.4)]], COLOR['rune'][2], hd - 7.4)
        if runic:
            ink.poly([H(*q) for q in [(-lean + 1, tip - 14), (-lean - 3, tip - 10), (-lean + .5, tip - 7), (-lean - 1.6, tip - 10.6)]], COLOR['gold'][3], hd - 7.4, False)
            cx, cy = -lean - 10, tip - 7
            star = [(cx + r * math.sin(i * math.pi / 5), cy + r * math.cos(i * math.pi / 5)) for i, r in enumerate([4.6, 1.9] * 5)]
            ink.poly([H(*q) for q in star], COLOR['gold'][2], hd - 7.5)

    # Staff: grip in the right hand, planted or carried; the head glows and flares when a spell goes off.
    hand = joints['R']['hand']
    u = R @ unit(V(*p['staff']))
    across = R @ V(1, 0, 0)
    butt_len = p['butt']
    if p['dropped']:
        hand, u, across, butt_len = V(24, -4, 2.5), unit(V(.4, 1, 0)), V(0, 0, 1), 30
    butt = hand - u * butt_len
    top = hand + u * 36
    for key in ('weapon_ash', 'weapon_crystal'):
        ink = inks[key]
        crystal = key == 'weapon_crystal'
        flare = p['flare']
        ink.bone(butt, top, 1.4, 1.2, 'silver' if crystal else 'wood', -.1, 2)
        ink.bone(hand - u * 2.4, hand + u * 3.2, 1.8, 1.8, 'umber', -.12)
        if crystal:
            for t in (.3, .62):
                ink.bone(butt + (top - butt) * t, butt + (top - butt) * t + u * 1.8, 1.8, 1.8, 'gold', -.15, 2)
            c = top + u * 6
            for sgn in (-1, 1):                  # three claws hold a tall diamond
                ink.plate([top - across * 1.2 * sgn, top + across * 5 * sgn + u * 6, top + across * 3.2 * sgn + u * 9], 'gold', 2)
            ink.plate([c + u * 7, c + across * 3.4, c - u * 3.6, c - across * 3.4], 'rune', 2)
            ink.plate([c + u * 7, c + across * 3.4, c + u * 1, c - across * .4], 'rune', 3, True)
            glow, size = 'rune', 3.2 + flare * 2.6
        else:
            c = top + u * 4.5
            ink.plate(ring(c, across, u, 3.8, 4.6, 10), 'wood', 2)
            ink.plate(ring(c, across, u, 2.4, 3.0, 8), 'rune', 3, True)
            ink.plate([top - across * 1, top + across * 5 + u * 3, top + across * 3 + u * 6], 'wood', 1)
            glow, size = 'rune', 2.2 + flare * 2.2
        # Spell glow: a four-point star around the head that grows with the flare.
        for ang in (0, math.pi / 2):
            d, n = across * math.cos(ang) + u * math.sin(ang), -across * math.sin(ang) + u * math.cos(ang)
            ink.plate([c + d * size * 1.9, c + n * .9, c - d * size * 1.9, c - n * .9], glow, 3, True)
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}


NAKED = {slot: 'none' for slot in SLOTS}
APPRENTICE = {'armor': 'apprentice', 'shoulders': 'apprentice', 'gloves': 'apprentice', 'head': 'apprentice', 'weapon': 'ash'}
RUNIC = {'armor': 'runic', 'shoulders': 'runic', 'gloves': 'runic', 'head': 'runic', 'weapon': 'crystal'}
SHEET = cc.Sheet(
    'mage', files='mage', pixel='mage_cel_', mats=MATS, clips=CLIPS, slots=SLOTS, gear=GEAR, render=render_frame,
    revision=cc.revision_of([open(__file__).read()]),
    default_equip={'armor': 'apprentice', 'shoulders': 'none', 'gloves': 'none', 'head': 'none', 'weapon': 'ash'},
    meta={'attack': {'duration': .56, 'impact': .28}, 'portrait': [57, 15, 46, 46]},
    combos=[('naked', NAKED), ('apprentice', APPRENTICE), ('runic', RUNIC)])

if __name__ == '__main__':
    SHEET.cli()
