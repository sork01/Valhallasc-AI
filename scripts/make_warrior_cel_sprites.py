#!/usr/bin/env python3
"""Warrior: a plate-armoured anime knight with sword and shield, in the Hunter's cel style (see cel_common.py).

usage: make_warrior_cel_sprites.py preview [clip|all] [directory]   contact sheets (scratch), rows = facings
       make_warrior_cel_sprites.py build [--replace]                 render every frame, create the editable PixelFlow sprites warrior_cel_<clip>_<facing>_<group>
       make_warrior_cel_sprites.py export [--local]                  PixelFlow (edits kept) -> client/assets/warrior_layered_*.png + warrior_layered_sprites.txt

Eleven layers: body + armor, shoulders, gloves, head (crimson, azure) + weapon (sword, royal). The weapon layers carry
the sword and the round shield on the left arm. A broader build than the other classes (limbs x1.15). build --replace
DISCARDS WARRIOR HAND EDITS. Files keep the old warrior_layered_ names so the game's part names stay valid.
"""
import math

import cel_common as cc
from cel_common import V, unit, rig

SLOTS = {'armor': ('crimson', 'azure'), 'shoulders': ('crimson', 'azure'), 'gloves': ('crimson', 'azure'),
         'head': ('crimson', 'azure'), 'weapon': ('sword', 'royal')}
MATS = {
    **cc.FACE_MATS,
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
               'sword': {'name': 'Sword & shield', 'attack': 4}, 'royal': {'name': 'Royal sword & shield', 'attack': 8}},
}


def disc(centre, a1, a2, rx, ry, n=14):
    return [centre + a1 * math.cos(i / n * math.tau) * rx + a2 * math.sin(i / n * math.tau) * ry for i in range(n)]


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R, xf, joints = cc.skeleton(p)
    inks = {part: cc.Ink(psi, COLOR) for part in SHEET.parts}
    body = inks['body']
    torso = lambda ink, mat, *a: cc.torso(ink, xf, mat, *a)
    cc.base_body(body, xf, joints, R, w=BULK, torso_width=8.8, torso_depth=4)
    head = cc.head_frame(body, xf, psi, p, turn=.5)
    H, hd, front, side = head['H'], head['hd'], head['front'], head['side']
    sw = p['sway']
    # Short spiky hair: a swept fringe of three sharp locks, bristling crown, a short tail at the nape.
    body.plate([xf(q) for q in [(-4, -5, 80), (4, -5, 80), (5 + sw, -8, 70), (0 + sw * 1.3, -9, 66), (-5 + sw, -8, 70)]], 'hair', 1)
    if not cc.face(body, head, p, lashes=.8):
        body.poly([H(*q) for q in [(-9.5, 8), (-10.5, 0), (-8.5, -8), (-4, -10.5), (5, -9.5), (9.5, -5), (10.5, 4), (6.5, 13), (-3, 14)]], COLOR['hair'][2], hd - 5)
    crown = [(-10.4, -4), (-11.6, 5), (-10.4, 10), (-7.6, 15), (-5.6, 14), (-3, 21), (-.4, 15.6), (2.6, 22), (4, 15.6), (8, 19), (8.4, 13), (11.6, 11), (10.8, 4), (10.4, -4),
             (8.4, 0), (7.6, 4.6), (4.6, 7.6), (1.4, 4.6), (-.8, 7), (-4, 4.6), (-7.2, 6.4), (-8.4, 1)]
    body.poly([H(*q) for q in crown], COLOR['hair'][1], hd - 6)
    body.poly([H(*q) for q in [(-10, 10), (-7.6, 14.4), (-5.4, 13.6), (-3, 19.8), (-1, 14.6), (-6, 9)]], COLOR['hair'][2], hd - 6.1, False)
    body.poly([H(*q) for q in [(2.6, 20.4), (3.8, 15), (7.6, 17.6), (8, 13), (5, 11)]], COLOR['hair'][2], hd - 6.1, False)
    body.poly([H(*q) for q in [(-4, 13), (-2, 16), (0, 13), (-1.6, 11.6)]], COLOR['hair'][3], hd - 6.2, False)
    # Heavy brows sit above the shared eyes.
    if front > -.4:
        for sx in (-1, 1):
            ex = sx * 4 * max(.28, front) + side * 3.3
            if abs(side) > .85 and sx * side < 0:
                continue
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
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}


def np_cross(a, b):
    return V(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


NAKED = {slot: 'none' for slot in SLOTS}
CRIMSON = {'armor': 'crimson', 'shoulders': 'crimson', 'gloves': 'crimson', 'head': 'crimson', 'weapon': 'sword'}
AZURE = {'armor': 'azure', 'shoulders': 'azure', 'gloves': 'azure', 'head': 'azure', 'weapon': 'royal'}
SHEET = cc.Sheet(
    'warrior', files='warrior_layered', pixel='warrior_cel_', mats=MATS, clips=CLIPS, slots=SLOTS, gear=GEAR, render=render_frame,
    revision=cc.revision_of([open(__file__).read()]),
    default_equip={'armor': 'crimson', 'shoulders': 'none', 'gloves': 'none', 'head': 'none', 'weapon': 'sword'},
    meta={'attack': {'duration': .42, 'impact': .21}, 'portrait': [57, 15, 46, 46]},
    combos=[('naked', NAKED), ('crimson', CRIMSON), ('azure', AZURE)])

if __name__ == '__main__':
    SHEET.cli()
