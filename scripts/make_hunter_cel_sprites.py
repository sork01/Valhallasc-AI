"""Hunter: a bow-and-quiver ranger in the Assassin/Priest 2D anime cel style, on the same 3D joint rig.

usage: make_hunter_cel_sprites.py preview [clip|all] [directory]   contact sheets (scratch), rows = facings
       make_hunter_cel_sprites.py build [--replace]                 render every frame, create the editable PixelFlow sprites hunter_<clip>_<facing>_<group>
       make_hunter_cel_sprites.py export [--local]                  PixelFlow (edits kept) -> client/assets/hunter_*.png + hunter_sprites.txt

Eleven independent layers, never baked together: the body plus five equipment slots in two tiers each
(armor, shoulders, gloves, head, weapon; scout and warden). The weapon layers also carry the quiver and the nocked
arrow, so an unarmed hunter has neither. 160x160 frames, feet at (80,119), eight facings, the Assassin's clips and
frame counts (idle 6, walk 8, attack 8, hurt 4, die 8), so MageSprite composites it. The rig (ik2, rotations, facing
formula) comes from the original project's tools/make_warrior_sprites.py, imported read-only from ../Valhalla/tools
(set VALHALLA_TOOLS to move it). Frames are cached as scripts/hunter_raw/*.npz (gitignored, regenerated in minutes).
PixelFlow: 5 layers x 160x160 x 8 frames is the 1,048,576-cell limit, so each clip and facing is three sprites,
hunter_<clip>_<facing>_scout (body + the four scout pieces), _warden (a reference copy of the body + the four warden
pieces) and _bows (the body reference + both bows). `ref_body` layers are read-only context and ignored on export.
build refuses existing names; build --replace DISCARDS HUNTER HAND EDITS. export reads the sprites back (colour edits
survive; depth comes from the cache; added pixels take the nearest original depth). export --local skips PixelFlow.
"""
import math
import sys

import numpy as np

import cel_common as cc
from cel_common import V, unit, rig, FW, FH

SLOTS = {'armor': ('scout', 'warden'), 'shoulders': ('scout', 'warden'), 'gloves': ('scout', 'warden'),
         'head': ('scout', 'warden'), 'weapon': ('shortbow', 'wardenbow')}
TIERS = SLOTS['armor']
MATS = {
    **cc.FACE_MATS,
    'hair': ['#3a1f1c', '#6b3a2a', '#a8643e', '#e0a070'],      # chestnut; the player's hair colour recolours it
    'cloth': ['#4c5a50', '#7e9186', '#bccabd', '#e8f0e0'],     # cream-sage undershirt
    'pants': ['#3a2f2a', '#5a4a40', '#80695a', '#a88f7a'],
    'green': ['#1f4a2c', '#2f7a3f', '#58b04e', '#a6e07a'],     # scout: leaf green
    'moss': ['#3a4a1c', '#667a2c', '#98b248', '#cfe27a'],      # scout cape
    'emerald': ['#0f3a40', '#1b6a68', '#2fa593', '#7ae6c8'],   # warden: deep teal
    'tan': ['#4a2e1a', '#7a4e2c', '#b87e48', '#e8b878'],
    'umber': ['#2a1a16', '#47291f', '#6e4331', '#9a6a4c'],
    'copper': ['#6a3414', '#b05a22', '#e89040', '#ffd078'],
    'silver': ['#35485e', '#6e87a3', '#b4c9de', '#f0f6ff'],
    'fur': ['#8a8aa0', '#bcc0d4', '#e6e9f4', '#fdfdff'],
    'wood': ['#3a2218', '#6b4128', '#a8703f', '#dca66a'],
    'glow': ['#0f8a96', '#2fd0d8', '#8af0ee', '#e4ffff'],      # warden gems and bow inlay
    'feather': ['#8a1f2a', '#d2394a', '#ff7a70', '#ffc4a8'],
    'iris': ['#1f5a3c', '#2f9a5c', '#74d27a', '#d4ffb8'],
}
PALETTE, COLOR = cc.palette_of(MATS)
DEFAULT = dict(root=(0, 0, 0), lean=4, twist=0, roll=0, sway=0, eyes='open',
               handL=(-12, 7, 52), handR=(12, 3, 48),
               footL=(-5, 0, 4), footR=(5, 0, 4),
               bow=(-.1, .3, 1), aim=(0, 1, 0), draw=False, arrow=False, ground=False, dropped=False)
HIP, SHOULDER = 37, 66


def local(point, twist):
    """A hand target given in the world (what the shot should look like), as the twisted body's local frame wants it."""
    return tuple(rig.rotz(-rig.rad(twist)) @ V(*point))


def idle(k):
    a = k / 6 * math.tau
    return dict(root=(0, 0, -.35 * math.sin(a)), sway=math.sin(a), twist=-8,
                handL=local((-12, 8, 52 + .5 * math.sin(a)), -8), handR=local((12, 2, 48), -8),
                eyes='closed' if k == 4 else 'open')


def walk(k):
    q = k / 8
    a = q * math.tau
    def foot(s, t):
        t %= 1
        return (s * 5, 9 - t * 36 if t < .5 else -9 + (t - .5) * 36,
                4 + (6 * math.sin((t - .5) * math.tau) if t >= .5 else 0))
    return dict(lean=15, roll=2 * math.sin(a), twist=5 * math.sin(a),
                root=(0, 0, -.65 * math.cos(a * 2)), sway=3 * math.sin(a),
                handL=(-13, 3 - math.sin(a) * 3, 53), handR=(14, -5 + math.sin(a) * 3, 52),
                bow=(-.1, .3 - .25 * math.sin(a), 1),
                footL=foot(-1, q), footR=foot(1, q + .5))


def attack(k):
    # Reach back to the quiver, nock, draw to the cheek, loose on frame 4 (the impact), follow through and lower.
    twist = [-8, -14, -26, -34, -30, -18, -10, -8][k]
    left = [(-12, 8, 52), (-11, 14, 58), (-8, 24, 64), (-8, 28, 67), (-8, 29, 68), (-9, 25, 63), (-11, 15, 56), (-12, 8, 52)][k]
    right = [(12, 2, 48), (14, -8, 66), (5, 11, 66), (5, 3, 74), (13, -5, 73), (15, -2, 62), (13, 2, 54), (12, 2, 48)][k]
    bow = [(-.1, .3, 1), (-.05, .2, 1), (0, .08, 1), (.02, 0, 1), (.02, 0, 1), (0, .1, 1), (-.05, .2, 1), (-.1, .3, 1)][k]
    f = [0, -.3, -.55, -1, .3, .6, .25, 0][k]
    return dict(lean=[4, 2, -3, -9, 0, 6, 6, 4][k], twist=twist, root=(0, 0, -.5 * abs(f)),
                handL=local(left, twist), handR=local(right, twist), bow=bow, sway=3 * f,
                draw=k in (2, 3), arrow=k in (2, 3),
                footL=(-6, 4 * max(0, f) - 2, 4), footR=(6, -5 + 4 * max(0, -f), 4))


def hurt(k):
    f = [.25, 1, .4, 0][k]
    return dict(lean=-14 * f, root=(0, -2 * f, 0), twist=9 * f,
                handL=(-14, 6, 54), handR=(15, 5, 52), eyes='closed' if k < 3 else 'open', sway=-2 * f,
                bow=(-.3 * f, .3, 1))


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
              'scout': {'name': "Scout's Jerkin", 'defense': 3}, 'warden': {'name': 'Wildwarden Coat', 'defense': 5}},
    'shoulders': {'none': {'name': 'Bare shoulders', 'defense': 0},
                  'scout': {'name': "Scout's Mantle", 'defense': 1}, 'warden': {'name': 'Wildwarden Pauldrons', 'defense': 2}},
    'gloves': {'none': {'name': 'Bare hands', 'defense': 0},
               'scout': {'name': "Scout's Bracers", 'defense': 1}, 'warden': {'name': 'Wildwarden Gauntlets', 'defense': 2}},
    'head': {'none': {'name': 'Bare head', 'defense': 0},
             'scout': {'name': 'Feathered Headband', 'defense': 1}, 'warden': {'name': 'Wolfhood', 'defense': 2}},
    'weapon': {'none': {'name': 'Empty hands', 'attack': 0},
               'shortbow': {'name': "Hunter's Shortbow", 'attack': 4}, 'wardenbow': {'name': 'Wildwarden Longbow', 'attack': 8}},
}


def bow_points(c, axis, face, half, bulge, n=8):
    """Limb centreline: the grip at c is the farthest point from the archer, the tips curve back towards them."""
    pts = []
    for i in range(n + 1):
        t = -1 + 2 * i / n
        pts.append(c + axis * half * t - face * bulge * t * t)
    return pts


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R, xf, joints = cc.skeleton(p)
    inks = {part: cc.Ink(psi, COLOR) for part in SHEET.parts}
    body = inks['body']
    torso = lambda ink, mat, *a: cc.torso(ink, xf, mat, *a)
    cc.base_body(body, xf, joints, R)
    # The Hunter's own head: upswept green eyes, two cheek stripes, a swept fringe with an anime ring highlight and
    # a high ponytail. The head turns only a third as far as the body, so an archer keeps their eyes on the target.
    head = cc.head_frame(body, xf, psi, p)
    H, hd, front, side = head['H'], head['hd'], head['front'], head['side']
    if not cc.face(body, head, p, paint=('feather', 1)):
        body.poly([H(*q) for q in [(-9.5, 8), (-10.5, 0), (-8.5, -8), (-4, -10.5), (5, -9.5), (9.5, -5), (10.5, 4), (6.5, 13), (-3, 14)]], COLOR['hair'][2], hd - 5)
        body.poly([H(*q) for q in [(-8, 6), (-2, 9), (4, 8), (8, 3), (4, 5), (-3, 5.5)]], COLOR['hair'][3], hd - 5.05, False)
    crown = [(-10.5, -6), (-11.5, 6), (-9.5, 13), (-3, 17), (4, 17), (10, 13), (11.5, 6), (10.5, -6),
             (8.5, -2), (7, 3.5), (3, 6.5), (-1, 4.6), (-5, 5.8), (-8, 3), (-9, -2)]
    body.poly([H(*q) for q in crown], COLOR['hair'][1], hd - 6)
    body.poly([H(*q) for q in [(-9, 12), (-3, 15.5), (4, 15), (9.5, 11), (9, 8), (3, 11.5), (-3, 12), (-8.5, 8)]], COLOR['hair'][2], hd - 6.1, False)
    body.poly([H(*q) for q in [(-6, 14), (-1, 15.4), (3, 14.6), (-1, 13.2), (-5, 12.2)]], COLOR['hair'][3], hd - 6.2, False)
    body.poly([H(*q) for q in [(1, 6.4), (3, 6.4), (7, 3.6), (9.5, -5), (8, -1.5), (5, 2.6)]], COLOR['hair'][2], hd - 6.1, False)
    # High ponytail on a coral ribbon, swinging with the body.
    sw = p['sway']
    body.plate([xf(q) for q in [(-2.4, -6, 91), (2.4, -6, 91), (7 + sw * 1.2, -11, 70), (3 + sw * 2, -12, 54), (-1 + sw * 1.4, -10.5, 63), (-4 + sw, -9, 74)]], 'hair', 1)
    body.plate([xf(q) for q in [(-.8, -6.4, 90), (1.6, -6.4, 90), (4.6 + sw * 1.2, -11.3, 70), (2 + sw * 1.8, -11.6, 60), (.4 + sw, -9.8, 72)]], 'hair', 2, True)
    body.bone(xf((-1.8, -6.2, 90.5)), xf((1.8, -6.2, 90.5)), 1.1, 1.1, 'feather', -.4)

    def cape(ink, mat, lining, longer, trim):
        hem = 12 if longer else 22
        lateral = p['sway'] * 1.4
        ink.plate([xf(q) for q in [(-11, -5.4, 71), (3, -5.4, 71), (7 + lateral, -8.8, hem + 5), (-5 + lateral * 1.4, -9.4, hem - 1), (-13 + lateral, -8.6, hem + 7)]], mat, 1)
        ink.plate([xf(q) for q in [(-6, -5.6, 70), (-1, -5.6, 70), (2 + lateral * .8, -8.9, hem + 8), (-3 + lateral * 1.2, -9.2, hem + 3)]], mat, 2, True)
        ink.plate([xf(q) for q in [(-11, -5.4, 71), (3, -5.4, 71), (3.4 + lateral * .3, -5.6, 62), (-11.5, -5.6, 62)]], lining, 1, True)
        if trim:
            ink.plate([xf(q) for q in [(-5 + lateral * 1.4, -9.4, hem - 1), (7 + lateral, -8.8, hem + 5), (6.6 + lateral, -8.8, hem + 8),
                                      (-5.2 + lateral * 1.4, -9.4, hem + 2.5), (-12.6 + lateral, -8.6, hem + 10), (-13 + lateral, -8.6, hem + 7)]], 'fur', 2, True)

    def tails(ink, mat, trimmat, longer):
        # Anime tunic tails: a long point at the front and back, shorter side flaps, asymmetric (left longer).
        s = p['sway'] * .6
        for sy, tone in ((1, 2), (-1, 1)):
            ink.plate([xf(q) for q in [(-5.2, sy * 5.1, 39), (5.2, sy * 5.1, 39), (1.2 + s, sy * 6.4, 21 if longer else 24), (-1.8 + s, sy * 6.4, 20 if longer else 23)]], mat, tone)
        for sx, hemz in ((-1, 22), (1, 28)):
            ink.plate([xf(q) for q in [(sx * 8.6, -4.5, 39), (sx * 8.6, 4.5, 39), (sx * (10.8 + .3 * abs(s)) + s * .4, 3.8, hemz - (2 if longer else 0)), (sx * (11.3) + s * .4, -3.2, hemz + 2 - (2 if longer else 0))]], mat, 2)
            ink.plate([xf(q) for q in [(sx * 10.8 + s * .4, 3.8, hemz + 2), (sx * 11.3 + s * .4, -3.2, hemz + 4), (sx * 11.2 + s * .4, -3.2, hemz + 1.4), (sx * 10.7 + s * .4, 3.8, hemz - .6)]], trimmat, 2, True)

    for tier in TIERS:
        ink = inks['armor_' + tier]
        warden = tier == 'warden'
        cloth, trim, strap = ('emerald', 'silver', 'umber') if warden else ('green', 'copper', 'tan')
        torso(ink, cloth, 8.8, 4.5, 38.5, 68.5)
        # Cream undershirt V at the neck, then a standing collar (scout) or a fur ruff (warden).
        ink.plate([xf(q) for q in [(-3.4, 4.7, 69), (3.4, 4.7, 69), (0, 4.8, 57)]], 'cloth', 3)
        if warden:
            ink.bone(xf((-5.6, 0, 68.5)), xf((5.6, 0, 68.5)), 3.4, 3.4, 'fur', -1.4, 2)
            ink.bone(xf((-5.2, 1.4, 69.8)), xf((5.2, 1.4, 69.8)), 2.4, 2.4, 'fur', -1.9, 3)
        else:
            ink.plate([xf(q) for q in [(-5, 5.1, 70.5), (-2, 5.1, 70.5), (-.8, 5.1, 66), (-4.8, 5.1, 66.5)]], cloth, 3)
            ink.plate([xf(q) for q in [(5, 5.1, 70.5), (2, 5.1, 70.5), (.8, 5.1, 66), (4.8, 5.1, 66.5)]], cloth, 2)
        # Baldric across the chest with a buckle, belt, buckle and a hip pouch.
        ink.plate([xf(q) for q in [(-7.6, 5.0, 68.5), (-4, 5.0, 68.5), (8, 5.0, 42), (4.4, 5.0, 42)]], strap, 2)
        ink.plate([xf(q) for q in [(-.6, 5.2, 57.6), (1.8, 5.2, 55.6), (.6, 5.2, 53.8), (-1.8, 5.2, 55.8)]], trim, 3, True)
        for sy in (-1, 1):
            ink.plate([xf(q) for q in [(-9.2, sy * 4.8, 42), (9.2, sy * 4.8, 42), (9.2, sy * 4.8, 38.2), (-9.2, sy * 4.8, 38.2)]], strap, 2 if sy > 0 else 1)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 9.2, -4.8, 42), (sx * 9.2, 4.8, 42), (sx * 9.2, 4.8, 38.2), (sx * 9.2, -4.8, 38.2)]], strap, 1)
        ink.plate([xf(q) for q in [(-2.3, 5.2, 42.4), (2.3, 5.2, 42.4), (2.3, 5.2, 37.8), (-2.3, 5.2, 37.8)]], trim, 3, True)
        ink.plate([xf(q) for q in [(5, 5.1, 40), (9.8, 5.1, 40), (9.8, 5.1, 32), (5, 5.1, 32)]], 'tan' if not warden else 'umber', 2)
        ink.plate([xf(q) for q in [(9.9, -1, 40), (9.9, 5, 40), (9.9, 5, 32), (9.9, -1, 32)]], 'tan' if not warden else 'umber', 1)
        ink.plate([xf(q) for q in [(5.4, 5.3, 40), (9.4, 5.3, 40), (9.4, 5.3, 37.6), (5.4, 5.3, 37.6)]], trim, 2, True)
        tails(ink, cloth, trim, warden)
        cape(ink, 'umber' if warden else 'moss', 'emerald' if warden else 'green', warden, warden)
        # Tall boots with a folded cuff (copper, or white fur on the warden) and a toe cap.
        for key in 'LR':
            j = joints[key]
            ink.bone(j['knee'] + (j['ankle'] - j['knee']) * .08, j['ankle'], 3.5, 2.8, 'umber', -.8)
            ink.bone(j['knee'] + (j['ankle'] - j['knee']) * .06, j['knee'] + (j['ankle'] - j['knee']) * .32, 4.1, 3.9, 'fur' if warden else 'tan', -1.0, 3 if warden else 2)
            ink.bone(j['ankle'] + V(0, -1, -1), j['ankle'] + V(0, 5, -2), 2.7, 2.6, 'umber', -.8)
            ink.bone(j['ankle'] + V(0, 3, -1.8), j['ankle'] + V(0, 5.2, -2.1), 2.7, 2.5, 'copper' if not warden else 'silver', -.9)

    for tier in TIERS:
        ink = inks['shoulders_' + tier]
        warden = tier == 'warden'
        for sx, key in ((-1, 'L'), (1, 'R')):
            j = joints[key]
            sh, el = j['shoulder'], j['elbow']
            out, upv = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            if warden:
                ink.bone(sh - out * .8 + upv * 2.4, sh + out * 5.4 - upv * 1.2, 5.2, 4.7, 'silver', -1.0, 2)
                ink.bone(sh + out * 2.4 + upv * 1.2, sh + out * 7 - upv * 3.6, 4.4, 3.8, 'silver', -1.15, 1)
                ink.bone(sh - out * 1.2 + upv * 3.2, sh + out * 2.2 + upv * 3.4, 3.6, 3.6, 'fur', -1.5, 3)
                ink.bone(sh + out * 3.4 - upv * 2.8, sh + out * 6.6 - upv * 5, 1.6, 1.3, 'glow', -1.4, 2)
                ink.plate([sh + out * 5 + upv * 1.5, sh + out * 8.4 + upv * 5.4, sh + out * 3.2 + upv * 3.6], 'silver', 3)
            elif sx < 0:
                # Bow arm: a layered leather pauldron with copper rivets and a coral feather spray.
                ink.bone(sh - out * .6 + upv * 2.4, sh + out * 5 - upv * 1.2, 4.6, 4.1, 'tan', -1.0, 2)
                ink.bone(sh + out * 2.6 + upv * .8, sh + out * 6.8 - upv * 3.6, 4.2, 3.7, 'tan', -1.15, 1)
                ink.bone(sh - out * .2 + upv * 4.2, sh + out * 4.2 + upv * 2.2, .9, .9, 'copper', -1.4, 2)
                for off, h in ((0, 9), (1.6, 7.4), (-1.6, 6.6)):
                    ink.plate([sh + out * (1.6 + off) + upv * 3, sh + out * (3 + off * 1.6) + upv * (4 + h), sh + out * (4 + off) + upv * 3.6], 'feather', 2 if off >= 0 else 1)
            else:
                ink.bone(sh - out * .4 + upv * 2.2, sh + out * 4.4 - upv * 1.2, 3.8, 3.4, 'tan', -1.0, 2)
                ink.bone(sh + out * 1.2 + upv * 3.4, sh + out * 3.4 + upv * 2.6, .9, .9, 'copper', -1.3, 2)

    for tier in TIERS:
        ink = inks['gloves_' + tier]
        warden = tier == 'warden'
        for key in 'LR':
            j = joints[key]
            el, hand = j['elbow'], j['hand']
            if warden:
                ink.bone(hand + (el - hand) * .66, hand + (el - hand) * .08, 3.1, 2.8, 'silver', -.8)
                ink.bone(hand + (el - hand) * .66, hand + (el - hand) * .52, 3.4, 3.4, 'emerald', -.95, 2)
                ink.bone(hand + (el - hand) * .3, hand + (el - hand) * .22, 3.3, 3.3, 'emerald', -.95, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.5, 2.2, 'silver', -.9)
                ink.bone(hand + R @ V(0, 0, .2) + (el - hand) * .1, hand + R @ V(0, 0, .6) + (el - hand) * .02, 1.1, 1.1, 'glow', -1.2, 2)
            else:
                ink.bone(hand + (el - hand) * .46, hand + (el - hand) * .06, 2.8, 2.5, 'tan', -.8)
                ink.bone(hand + (el - hand) * .46, hand + (el - hand) * .36, 3.1, 3.1, 'copper', -.95, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.4, 2.1, 'umber', -.9)

    for tier in TIERS:
        ink = inks['head_' + tier]
        warden = tier == 'warden'
        backview = front < -.4
        if not warden:
            # Leaf-green headband with a copper boss, and a coral feather swept back on the far side.
            band = [(-10.9, 3.2), (-11.4, 7.6), (-7, 11), (0, 12), (7, 11), (11.4, 7.6), (10.9, 3.2), (7, 6.3), (0, 7.3), (-7, 6.3)]
            ink.poly([H(*q) for q in band], COLOR['green'][2], hd - 7)
            ink.poly([H(*q) for q in [(-10.9, 3.2), (-9.4, 3.9), (0, 7.3), (9.4, 3.9), (10.9, 3.2), (7, 6.3), (0, 7.3), (-7, 6.3)]], COLOR['green'][1], hd - 7.05, False)
            if not backview:
                ink.poly([H(*q) for q in [(-2, 9.7), (0, 11.4), (2, 9.7), (0, 8)]], COLOR['copper'][2], hd - 7.2)
            fx = 9.8 if abs(side) < .35 else -math.copysign(9.8, side)
            sgn = 1 if fx > 0 else -1
            leaf = [(fx, 6.5), (fx + 3.4 * sgn, 11), (fx + 6.4 * sgn, 17.5), (fx + 5.4 * sgn, 25.5), (fx + 1.2 * sgn, 20.5), (fx - 1.4 * sgn, 13)]
            ink.poly([H(*q) for q in leaf], COLOR['feather'][2], hd - 7.4)
            ink.poly([H(*q) for q in [(fx, 6.5), (fx + 3.4 * sgn, 11), (fx + 6.4 * sgn, 17.5), (fx + 5.4 * sgn, 25.5), (fx + 4 * sgn, 18), (fx + 2 * sgn, 12)]], COLOR['feather'][1], hd - 7.45, False)
            ink.poly([H(*q) for q in [(fx + .4 * sgn, 7), (fx + 4.8 * sgn, 22.5), (fx + 5.3 * sgn, 22.5), (fx + 1 * sgn, 7)]], COLOR['feather'][3], hd - 7.5, False)
        else:
            # Wolf hood: a fur-trimmed arch round the face (closed over the back of the head), two pointed ears.
            outer = [(-12.8, -4.5), (-13.4, 8), (-9.6, 16.4), (0, 20), (9.6, 16.4), (13.4, 8), (12.8, -4.5)]
            inner = [(9.2, -2), (8.8, 5.5), (5.2, 9.8), (0, 11), (-5.2, 9.8), (-8.8, 5.5), (-9.2, -2)]
            ink.poly([H(*q) for q in (outer if backview else outer + inner)], COLOR['emerald'][2], hd - 7)
            ink.poly([H(*q) for q in [(-13.4, 8), (-9.6, 16.4), (0, 20), (-1, 17), (-8, 12.6), (-10.4, 6)]], COLOR['emerald'][3], hd - 7.05, False)
            ink.poly([H(*q) for q in [(13.4, 8), (12.8, -4.5), (9.4, -2), (9.6, 3), (11.4, 10)]], COLOR['emerald'][1], hd - 7.05, False)
            if not backview:
                teeth = []
                for i in range(8):
                    x0 = -9.2 + i * 2.3
                    teeth += [(x0, 11.6 - abs(i - 3.5) * .55 - .4), (x0 + 1.15, 8.7 - abs(i - 3.5) * .55)]
                trimrow = [(-9.4, -2.5), (-9.6, 6)] + [(-9.2 + i * 2.3, 11.8 - abs(i - 3.5) * .6) for i in range(9)] + [(9.6, 6), (9.4, -2.5)]
                ink.poly([H(*q) for q in trimrow] + [H(*q) for q in [(9.2, -2), (8.8, 5.5), (5.2, 9.8), (0, 11), (-5.2, 9.8), (-8.8, 5.5), (-9.2, -2)]], COLOR['fur'][2], hd - 7.4)
            for ex_ in (-1, 1):
                ink.poly([H(ex_ * 5.2, 17.4), H(ex_ * 11.8, 18.2), H(ex_ * 11.2, 27.5), H(ex_ * 8, 22.6)], COLOR['emerald'][2], hd - 7.2)
                ink.poly([H(ex_ * 6.6, 18.4), H(ex_ * 10.4, 19), H(ex_ * 10.4, 24.4), H(ex_ * 8.2, 21.6)], COLOR['feather'][1], hd - 7.3, False)
            if not backview:
                ink.poly([H(*q) for q in [(-1.8, 14.8), (0, 17.6), (1.8, 14.8), (0, 13)]], COLOR['glow'][2], hd - 7.5)

    # Weapon layers: the bow (grip in the left hand, string to the right when drawn), the quiver and the arrow.
    hand_l, hand_r = joints['L']['hand'], joints['R']['hand']
    axis = R @ unit(V(*p['bow']))
    if p['dropped']:
        centre, axis, face = V(-22, 9, 3), unit(V(.3, 1, 0)), V(0, 0, 1)
    else:
        centre = hand_l
        face = unit(hand_l - hand_r) if p['draw'] else R @ unit(V(*p['aim']))
        axis = unit(axis - face * (axis @ face))
    for key, long in (('weapon_shortbow', False), ('weapon_wardenbow', True)):
        ink = inks[key]
        half, bulge = (27, 7.5) if long else (22, 6.5)
        pts = bow_points(centre, axis, face, half, bulge)
        wood, tipmat = ('wood', 'silver') if long else ('wood', 'copper')
        ink.ribbon(pts[:5], 1.0, 1.7, wood, 2, -.2)
        ink.ribbon(pts[4:], 1.7, 1.0, wood, 2, -.2)
        if long:
            ink.ribbon([pts[0] + (pts[1] - pts[0]) * t for t in (.05, .5)] + [pts[1] + (pts[2] - pts[1]) * .5], .35, .5, 'glow', 2, -.55, False)
            ink.ribbon([pts[-1] + (pts[-2] - pts[-1]) * t for t in (.05, .5)] + [pts[-2] + (pts[-3] - pts[-2]) * .5], .35, .5, 'glow', 2, -.55, False)
        ink.bone(centre - axis * 3.6, centre + axis * 3.6, 1.9, 1.9, 'umber' if long else 'tan', -1.1, 2)
        for tip, nxt in ((pts[0], pts[1]), (pts[-1], pts[-2])):
            ink.bone(tip, tip + unit(nxt - tip) * 2.6, 1.4, 1.2, tipmat, -.5, 2)
            ink.plate([tip - face * 1.2, tip - face * 3.2 + unit(tip - nxt) * 1.8, tip + face * .6], tipmat, 3, True)
        nock = hand_r if p['draw'] else (pts[0] + pts[-1]) / 2
        for end in (pts[0], pts[-1]):
            ink.ribbon([end, (end + nock) / 2, nock], .45, .45, 'white', 2, -.3, False)
        if p['arrow'] and not p['dropped']:
            dirv = unit(centre - nock)
            tip = nock + dirv * 36
            perp = unit(np.cross(dirv, V(0, 0, 1)))
            ink.ribbon([nock, (nock + tip) / 2, tip], .5, .5, 'wood', 3, -.35, False)
            ink.plate([tip + dirv * 4.4, tip + perp * 1.6 - dirv * .3, tip - perp * 1.6 - dirv * .3], 'silver', 3)
            for sgn in (-1, 1):
                ink.plate([nock + dirv * .6, nock + dirv * 6.4, nock + dirv * 6.4 + perp * 2.4 * sgn, nock + perp * 2.6 * sgn - dirv * .6], 'feather', 2)
        # Quiver on the back, its strap over the chest's far side, three fletched arrows poking out.
        qb, qt = xf((4.4, -7.2, 49)), xf((-3.2, -8.2, 72))
        ink.bone(qb, qt, 3.4, 3.1, 'umber', -.5, 1 if not long else 2)
        ink.bone(qt - (qt - qb) * .08, qt, 3.7, 3.7, tipmat, -.7, 2)
        for dx, dz, c in ((-1.2, 0, 'feather'), (1.6, 1.4, 'feather'), (.2, .6, 'white')):
            top = qt + R @ V(dx, .4, 7.6 + dz)
            ink.bone(qt + R @ V(dx, .2, 0), top, .55, .55, 'wood', -.2, 3)
            ink.plate([top, top + R @ V(1.8, 0, -1.4), top + R @ V(1.5, 0, -5.2), top + R @ V(0, 0, -4)], c, 2)
        ink.plate([xf(q) for q in [(7.4, -5.0, 68.5), (4, -5.0, 68.5), (-8, -5.0, 42), (-4.4, -5.0, 42)]], 'umber', 1)
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}


NAKED = {slot: 'none' for slot in SLOTS}
SCOUT = {'armor': 'scout', 'shoulders': 'scout', 'gloves': 'scout', 'head': 'scout', 'weapon': 'shortbow'}
WARDEN = {'armor': 'warden', 'shoulders': 'warden', 'gloves': 'warden', 'head': 'warden', 'weapon': 'wardenbow'}
SHEET = cc.Sheet(
    'hunter', files='hunter', pixel='hunter_', mats=MATS, clips=CLIPS, slots=SLOTS, gear=GEAR, render=render_frame,
    revision=cc.revision_of([open(__file__).read()]),
    default_equip={'armor': 'scout', 'shoulders': 'none', 'gloves': 'none', 'head': 'none', 'weapon': 'shortbow'},
    meta={'attack': {'duration': .4, 'impact': .2}, 'portrait': [57, 15, 46, 46]},
    combos=[('naked', NAKED), ('scout', SCOUT), ('warden', WARDEN)])

if __name__ == '__main__':
    SHEET.cli()
