"""New progression equipment silhouettes fitted to the existing cel character rigs.

Each of the six levels has its own outline and construction; rarity only recolors it. Cathedral shapes are separate.
These functions draw equipment only. They never replace the body, its poses or the original equipment artwork.
"""
import importlib
import math
import numpy as np
import cel_common as cc
from cel_common import V, unit

MATS = {
    'cloth': ['#172838', '#294358', '#496981', '#7899b1'],
    'metal': ['#394052', '#646f8a', '#a0b2ce', '#e2eafa'],
    'trim': ['#49382b', '#82633e', '#c4a573', '#f7dfab'],
    'gem': ['#153b45', '#286b7e', '#58b7c5', '#c1f8f3'],
    'leather': ['#201e2a', '#393547', '#625770', '#9587ab'],
    'veil': ['#232c44', '#414d71', '#737fa5', '#aeb7d5'],
}
PALETTE, COLOR = cc.palette_of(MATS)
MODULES = dict(assassin='make_assassin_cel_sprites', warrior='make_warrior_cel_sprites',
               mage='make_mage_cel_sprites', priest='make_priest_sprites', hunter='make_hunter_cel_sprites')
DESIGNS = {
    'L25': dict(index=0, hem=30, cape=0, collar=3, spikes=1),
    'L30': dict(index=1, hem=23, cape=24, collar=8, spikes=2),
    'L35': dict(index=2, hem=36, cape=0, collar=5, spikes=0),
    'L40': dict(index=3, hem=20, cape=34, collar=11, spikes=3),
    'L45': dict(index=4, hem=28, cape=20, collar=6, spikes=4),
    'L50': dict(index=5, hem=16, cape=39, collar=13, spikes=2),
    'cloister': dict(index=6, hem=21, cape=42, collar=6, spikes=0),
    'reliquary': dict(index=7, hem=32, cape=15, collar=10, spikes=3),
    'nave': dict(index=8, hem=15, cape=44, collar=15, spikes=4),
}


def variant(theme):
    return 'regear' + theme.lower()


def pose(cls, gender, clip, facing, k):
    cc.FEMALE = gender == 'female'
    cc.SHOULDER_X, cc.HIP_X = (7.2, 4.7) if cc.FEMALE else (8, 4.2)
    module = importlib.import_module(MODULES[cls])
    p = {**module.DEFAULT, **module.CLIPS[clip][2](k)}
    R, xf, joints = cc.skeleton(p)
    # Priest uses a different elbow pole; preserve its original sleeves and mace grip alignment.
    if cls == 'priest':
        for sx, key in ((-1, 'L'), (1, 'R')):
            elbow, hand = cc.rig.ik2(V(sx * cc.SHOULDER_X, 0, cc.SHOULDER), V(*p['hand' + key]),
                                    13.5, 13.5, unit(V(sx * .3, -.45, -1)))
            joints[key]['elbow'], joints[key]['hand'] = xf(elbow), xf(hand)
    ink = cc.Ink(cc.rig.psi_for(facing), COLOR)
    head = cc.head_frame(ink, xf, cc.rig.psi_for(facing), p, turn=1.0 if cls == 'assassin' else .3)
    return module, ink, p, R, xf, joints, head


def poly(ink, xf, points, material='metal', tone=2, detail=False):
    ink.plate([xf(q) for q in points], material, tone, detail)


def jewel(ink, centre, across, up, size=2.5):
    ink.plate([centre + up * size, centre + across * size, centre - up * size, centre - across * size], 'trim', 2)
    ink.plate([centre + up * (size - .7), centre + across * (size - .7), centre - up * (size - .7), centre - across * (size - .7)], 'gem', 3, True)


def armor(ink, cls, d, p, R, xf, joints):
    ix = d['index']; caster = cls in ('mage', 'priest')
    w = 10.2 if cls == 'warrior' else 9.3 if caster else 8.8
    mat = 'metal' if cls == 'warrior' else 'cloth' if caster else 'leather'
    cc.torso(ink, xf, mat, w, 5.1, 37, 70)
    # Six distinct chest constructions: lamellar, crossing straps, scaled, shell, segmented, star cuirass.
    if ix in (0, 2, 4):
        for row in range(3 + ix % 3):
            z = 64 - row * 6
            for sx in (-1, 1):
                poly(ink, xf, [(sx * .8, 5.4, z + 3), (sx * (w - 1), 5.4, z + 1),
                              (sx * (w - 1), 5.5, z - 3), (sx * 2, 5.5, z - 4)], 'metal' if ix == 2 else mat, 2)
    else:
        poly(ink, xf, [(-w + 1, 5.4, 66), (0, 6.2, 70), (w - 1, 5.4, 66),
                      (w - 2, 5.5, 54), (0, 6.1, 49 - ix % 4), (-w + 2, 5.5, 54)], 'metal', 2)
        for sx in (-1, 1):
            poly(ink, xf, [(sx, 6.3, 65), (sx * (w - 2), 5.8, 61), (sx * 2, 6.3, 54)], 'trim', 3)
    # High segmented collar; a long split coat replaces the old scarf-and-tunic outline.
    collar = d['collar']
    for sx in (-1, 1):
        poly(ink, xf, [(sx * 3.1, 4.6, 68), (sx * 8, 2.3, 70 + collar),
                      (sx * 11, -2, 71 + collar * .4), (sx * 9, -4.5, 68), (sx * 4, -4, 68)], mat, 2)
        hem = max(9, d['hem'] - (7 if caster else 0))
        # Rear and side coat tails, with different corner cuts at every level.
        wind = p['sway'] * .75
        poly(ink, xf, [(sx * 5, -5.5, 42), (sx * (w + 1), -5.5, 43),
                      (sx * (w + 5 + ix % 3) + wind, -8, hem + 5),
                      (sx * (w + 1) + wind, -8.5, hem - ix % 4),
                      (sx * 5 + wind, -6.5, hem + 6)], 'cloth' if caster else mat, 2)
        poly(ink, xf, [(sx * (w + .8), -5.7, 40), (sx * (w + 1.8), -5.7, 40),
                      (sx * (w + 6 + ix % 3) + wind, -8.2, hem + 5),
                      (sx * (w + 4 + ix % 3) + wind, -8.2, hem + 6)], 'trim', 2, True)
    if d['cape']:
        bottom = 72 - d['cape']
        poly(ink, xf, [(-11, -6, 72), (11, -6, 72), (18 + p['sway'], -11, bottom + 10),
                      (8 + p['sway'] * 1.4, -12, bottom), (0, -10, bottom + 7),
                      (-9 + p['sway'], -12, bottom + 2), (-18 + p['sway'], -10, bottom + 13)], 'veil', 1)
    for key in 'LR':
        j = joints[key]
        ink.bone(j['shoulder'], j['elbow'], 3.7 if cls == 'warrior' else 3.1, 2.8, mat, -.9, 2)
        if caster:
            ink.bone(j['elbow'], j['hand'] + (j['elbow'] - j['hand']) * .4, 4.8, 4.3, 'cloth', -.65, 2)
    poly(ink, xf, [(-8, 5.8, 43), (8, 5.8, 43), (8, 5.8, 38), (-8, 5.8, 38)], 'trim', 2)
    jewel(ink, xf((0, 6.2, 59 if caster else 40)), R @ V(1, 0, 0), R @ V(0, 0, 1), 3.4)


def headgear(ink, cls, d, head):
    H, hd, back = head['H'], head['hd'] - (4 if head['front'] < -.4 else 0), head['front'] < -.4
    ix = d['index']
    if cls in ('assassin', 'hunter'):
        if ix == 0:
            # The first progression tier is an open bramble visor, deliberately unlike the closed level-50 hood:
            # a low brow rail, two leaf-like cheek guards and a split crown leave the original hair visible.
            brow = [(-13, 3), (-10, 8), (-3, 10), (0, 8), (4, 10), (12, 7), (14, 2), (8, 0), (0, 2), (-8, 0)]
            ink.poly([H(*q) for q in brow], COLOR['leather'][2], hd - 7)
            ink.poly([H(-13, 3), H(-17, -8), H(-10, -5), H(-7, 1)], COLOR['metal'][2], hd - 7.2)
            ink.poly([H(13, 3), H(17, -7), H(10, -5), H(7, 1)], COLOR['metal'][2], hd - 7.2)
            if back:
                ink.poly([H(-12, 4), H(-8, 13), H(-2, 9), H(0, 16), H(5, 9), H(12, 13), H(13, 4)], COLOR['veil'][1], hd - 7)
            else:
                ink.poly([H(-7, 1), H(0, -2), H(8, 1), H(6, -6), H(0, -8), H(-6, -6)], COLOR['veil'][1], hd - 7.6)
                ink.poly([H(-4, 8), H(0, 16), H(4, 8), H(0, 11)], COLOR['trim'][2], hd - 7.8, True)
            ink.poly([H(-2, 14), H(0, 23), H(2, 14)], COLOR['gem'][3], hd - 7.9)
            return
        # Full hood and lower mask; unlike both starter brow bands/circlets.
        top = 22 + ix * .7
        outer = [(-14, -6), (-15, 9), (-10, top - 3), (-3, top + 2), (4, top), (12, top - 8), (15, 8), (14, -6)]
        inner = [(10, -3), (10, 5), (6, 10), (0, 12), (-6, 10), (-10, 5), (-10, -3)]
        ink.poly([H(*q) for q in (outer + [(-8, -9), (0, -11), (8, -9)] if back else outer + inner)], COLOR['veil'][2], hd - 7)
        ink.poly([H(*q) for q in [(-14, 5), (-10, top - 3), (-3, top + 2), (-2, top - 2), (-9, top - 6), (-11, 4)]], COLOR['metal'][2], hd - 7.2)
        if not back:
            ink.poly([H(*q) for q in [(-9, -3), (0, -6), (9, -3), (8, -10), (0, -12), (-8, -10)]], COLOR['cloth'][1], hd - 7.6)
            ink.poly([H(*q) for q in [(-7, -5), (0, -7), (7, -5), (0, -9)]], COLOR['trim'][2], hd - 7.8, False)
    elif cls == 'warrior':
        top = 20 + ix * .8
        outer = [(-14, -10), (-15, 8), (-10, 19), (0, top), (10, 19), (15, 8), (14, -10), (9, -13), (8, 4), (0, 9), (-8, 4), (-9, -13)]
        ink.poly([H(*q) for q in (outer[:7] + [(0, -9)] if back else outer)], COLOR['metal'][2], hd - 7)
        if not back:
            ink.poly([H(*q) for q in [(-10, 1), (10, 1), (8, -3), (-8, -3)]], COLOR['cloth'][0], hd - 7.4)
            ink.poly([H(*q) for q in [(-1, 7), (1, 7), (2, -8), (0, -11), (-2, -8)]], COLOR['trim'][2], hd - 7.5)
    else:
        # Tall split mitre for Priest, broad folded spell hat for Mage.
        width = 12 + ix * .8
        priest_top = 27 + ix * .25
        shape = ([(-width, 3), (-10, 22), (-5, priest_top), (0, priest_top - 9), (5, priest_top), (10, 22), (width, 3)] if cls == 'priest' else
                 [(-17 - ix * .6, 5), (-13, 9), (-9, 24), (-4, 28 + ix * .7), (9, 27), (6, 19), (12, 11), (17 + ix * .6, 5), (5, 8), (-5, 8)])
        ink.poly([H(*q) for q in shape], COLOR['cloth'][2], hd - 7)
        ink.poly([H(*q) for q in [(-12, 5), (12, 5), (10, 9), (-10, 9)]], COLOR['trim'][2], hd - 7.2)
    # Tier signatures: every class changes its crown profile as well as its color.
    style = ix % 6
    if style == 0:
        ink.poly([H(-3, 18), H(0, 31), H(3, 18)], COLOR['metal'][2], hd - 7.5)
    elif style == 1:
        ink.poly([H(-11, 12), H(-16, 22), H(-8, 19), H(0, 14), H(8, 19), H(16, 22), H(11, 12)], COLOR['trim'][2], hd - 7.5)
    elif style == 2:
        ink.poly([H(-8, 17), H(-4, 28), H(0, 21), H(4, 28), H(8, 17), H(0, 13)], COLOR['gem'][2], hd - 7.5)
    elif style == 3:
        ink.poly([H(-14, 9), H(-11, 24), H(-4, 18), H(0, 27), H(5, 18), H(12, 24), H(14, 9)], COLOR['metal'][3], hd - 7.5)
    elif style == 4:
        ink.poly([H(-12, 14), H(-2, 28), H(0, 30), H(-4, 15)], COLOR['gem'][2], hd - 7.5)
        ink.poly([H(12, 14), H(2, 28), H(0, 30), H(4, 15)], COLOR['gem'][2], hd - 7.5)
    else:
        ink.poly([H(-9, 16), H(-5, 25), H(0, 18), H(5, 25), H(9, 16), H(0, 12)], COLOR['veil'][2], hd - 7.5)
    # Different crests: thorn, sail, scallop, pearl, coral, star, kelp, prism, abyss.
    for n in range(d['spikes']):
        x = (n - (d['spikes'] - 1) / 2) * 5
        ink.poly([H(x - 2, 19), H(x + (1 if ix % 2 else -1), 29 + n % 2 * 4), H(x + 2, 19)], COLOR['metal'][2], hd - 7.4)
    if not back:
        ink.poly([H(0, 18), H(3, 14), H(0, 11), H(-3, 14)], COLOR['gem'][3], hd - 7.9)


def shoulders(ink, cls, d, R, joints):
    ix = d['index']
    style = ix % 6
    # Give every class a readable shoulder silhouette before the tier-specific trim:
    # assassin blades, warrior shields, mage crescents, priest mantles, hunter leaf fins.
    if cls == 'assassin':
        for sx, key in ((-1, 'L'), (1, 'R')):
            sh = joints[key]['shoulder']; out, up = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            reach = [7, 10, 8, 13, 9, 11][style]; crown = [3, 7, 1, 5, 9, 4][style]
            ink.plate([sh + out * 1 + up * (2 + style % 3), sh + out * reach + up * crown,
                       sh + out * (reach - 2) - up * (2 + style % 2), sh + out * 1 - up * 3], 'leather', 2)
            if style in (1, 3, 5):
                ink.plate([sh + out * 3 + up * 2, sh + out * (reach + 3) + up * 2,
                           sh + out * (reach - 1) - up * 2], 'metal', 3, True)
            else:
                ink.bone(sh + out * 2, sh + out * reach + up * 2, 1.1, .8, 'metal', -1.3, 2)
        return
    if cls == 'warrior':
        for sx, key in ((-1, 'L'), (1, 'R')):
            sh = joints[key]['shoulder']; out, up = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            reach = [10, 14, 12, 16, 11, 15][style]; high = [6, 10, 8, 4, 12, 7][style]
            ink.plate([sh + out * 0 + up * high, sh + out * reach + up * (high + 2),
                       sh + out * (reach + 3) - up * 1, sh + out * 5 - up * 7,
                       sh + out * 0 - up * 3], 'metal', 2)
            ink.plate([sh + out * 4 + up * (high - 1), sh + out * (reach + 1) + up * high,
                       sh + out * (reach - 3) + up * 1], 'trim', 3, True)
        return
    if cls == 'mage':
        for sx, key in ((-1, 'L'), (1, 'R')):
            sh = joints[key]['shoulder']; out, up = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            reach = [8, 12, 10, 15, 9, 13][style]; high = [5, 9, 13, 4, 11, 7][style]
            ink.bone(sh + out * 1 + up * 2, sh + out * reach + up * high, 2.2, 1.5, 'cloth', -.8, 2)
            ink.bone(sh + out * 3 + up * (high - 2), sh + out * (reach + 2) + up * (high - 4), 1.2, 1.0, 'gem', -1.1, 2)
            if style in (2, 4): ink.plate([sh + out * 2 + up * 3, sh + out * reach + up * 2, sh + out * (reach - 2) - up * 2], 'trim', 2, True)
        return
    if cls == 'priest':
        for sx, key in ((-1, 'L'), (1, 'R')):
            sh = joints[key]['shoulder']; out, up = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            reach = [9, 12, 10, 14, 11, 15][style]; high = [4, 8, 11, 6, 13, 9][style]
            ink.plate([sh + out * 0 + up * high, sh + out * reach + up * (high + 2),
                       sh + out * (reach + 2) - up * 4, sh + out * 2 - up * 7], 'cloth', 2)
            ink.bone(sh + out * 2 + up * 2, sh + out * reach + up * 1, 1.4, 1.1, 'trim', -1.2, 2)
            if style in (1, 3, 5): ink.bone(sh + out * 4, sh + out * (reach + 1) + up * 4, .9, .9, 'gem', -1.5, 2)
        return
    if cls == 'hunter':
        for sx, key in ((-1, 'L'), (1, 'R')):
            sh = joints[key]['shoulder']; out, up = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            reach = [8, 13, 10, 15, 9, 12][style]; high = [6, 10, 4, 12, 8, 14][style]
            ink.plate([sh + out * 0 + up * 4, sh + out * reach + up * high,
                       sh + out * (reach - 3) - up * 4, sh + out * 2 - up * 3], 'leather', 2)
            ink.plate([sh + out * 4 + up * 3, sh + out * (reach + 2) + up * 1,
                       sh + out * (reach - 2) - up * 2], 'gem', 2, True)
        return
    for sx, key in ((-1, 'L'), (1, 'R')):
        sh = joints[key]['shoulder']; out, up = R @ V(sx, 0, 0), R @ V(0, 0, 1)
        width = (8 if cls == 'warrior' else 6) + ix % 3
        for row in range(2 + ix % 2):
            c = sh + out * (row * 2 + 1) - up * (row * 2)
            ink.plate([c - out * 2 + up * 5, c + out * width + up * (4 + ix % 3),
                       c + out * (width + 2) - up * 3, c + out * 2 - up * 5], 'metal', 2)
            ink.bone(c + up * 4, c + out * width + up * (3 + ix % 3), .85, .85, 'trim', -1.6, 3)
        for n in range(d['spikes']):
            c = sh + out * (n * 2 + 1)
            ink.plate([c + up * 4, c + out * (2 + n % 2) + up * (10 + ix % 3), c + out * 3 + up * 3], 'gem' if ix in (3, 7) else 'metal', 3)
        jewel(ink, sh + out * 4 + up * 3 + R @ V(0, 2, 0), out, up, 2)


def gloves(ink, cls, d, R, joints):
    for key in 'LR':
        hand, el = joints[key]['hand'], joints[key]['elbow']; u = unit(hand - el); side = R @ V(1, 0, 0)
        ink.bone(hand + (el - hand) * .68, hand + (el - hand) * .05, 3.3, 2.8, 'metal' if cls == 'warrior' else 'leather', -.9, 2)
        ink.bone(hand + (el - hand) * .68, hand + (el - hand) * .51, 4.1 + d['index'] * .23, 3.6, 'trim', -1.25, 2)
        ink.plate([hand - side * 3, hand + side * 3, hand + u * (4.5 + d['index'] * .55), hand + u * 6 - side * 2], 'metal', 2)
        jewel(ink, hand + R @ V(0, 2.4, 1), side, R @ V(0, 0, 1), 1.8)


def pants(ink, d, R, joints):
    for sx, key in ((-1, 'L'), (1, 'R')):
        j = joints[key]
        ink.bone(j['hip'], j['knee'], 4.6, 3.8, 'cloth', -.5)
        ink.bone(j['knee'], j['ankle'], 3.8, 3.1, 'leather', -.6)
        for n in range(2 + d['index'] % 3):
            c = j['knee'] + (j['ankle'] - j['knee']) * (n * .17 + .05)
            ink.bone(c, c + (j['ankle'] - j['knee']) * .12, 3.9, 3.7, 'metal', -.85, 2)
        ink.bone(j['ankle'] + V(0, -1, -1), j['ankle'] + V(0, 5 + d['index'] % 2, -2), 3.1, 2.4, 'leather', -1.1)
        jewel(ink, j['knee'] + R @ V(0, 4, 0), R @ V(1, 0, 0), R @ V(0, 0, 1), 2.2)


def necklace(ink, d, R, xf):
    chain = [(-6, 3, 70), (-5, 6.4, 65), (0, 7.2, 57), (5, 6.4, 65), (6, 3, 70)]
    for a, b in zip(chain, chain[1:]):
        ink.bone(xf(a), xf(b), .85, .85, 'trim', -2, 2)
    c = xf((0, 7.6, 57)); side, up = R @ V(1, 0, 0), R @ V(0, 0, 1)
    jewel(ink, c, side, up, 3.4 + d['index'] * .17)
    for sx in (-1, 1):
        ink.plate([c + side * sx * 3, c + side * sx * (6 + d['index'] % 3) + up * 3, c + side * sx * 4 - up * 3], 'metal', 2)


def accessory(ink, d, R, joints):
    c = joints['L']['hand']; up, side = R @ V(0, 0, 1), R @ V(1, 0, 0)
    ink.bone(c - up * .3, c + up * 1.7, 3.1, 3, 'trim', -2.1, 2)
    jewel(ink, c + R @ V(0, 3.5, 1.6), side, up, 2.0 + d['index'] * .45)
    for n in range(1 + d['index'] // 3):
        ink.bone(c + up * (-.8 - n * .8), c + up * (-.5 - n * .8), 2.8, 2.8, 'metal', -2.2, 2)


def weapon(ink, cls, d, p, R, xf, joints):
    ix = d['index']; style = ix % 6; dropped = p['dropped']
    if cls == 'hunter':
        centre, axis = joints['L']['hand'], R @ unit(V(*p['bow']))
        face = unit(centre - joints['R']['hand']) if p['draw'] else R @ unit(V(*p['aim']))
        if dropped: centre, axis, face = V(-21, 8, 3), unit(V(.3, 1, 0)), V(0, 0, 1)
        axis = unit(axis - face * (axis @ face)); half = [18, 23, 20, 26, 19, 24][style]
        pts = [centre + axis * (t * half) + face * ((1 - t * t) * (5 + ix % 3) - abs(t) ** 3 * 2) for t in np.linspace(-1, 1, 9)]
        ink.ribbon(pts, 1.5, 1.5, 'metal', 2, -.5)
        for end in (pts[0], pts[-1]):
            ink.plate([end - face * 2, end + axis * 4, end + face * 4, end + face * 2 - axis * 3], 'gem', 3)
            nock = joints['R']['hand'] if p['draw'] and not dropped else centre - face * 2
            ink.ribbon([end, nock], .5, .5, 'trim', 3, -.7, False)
        ink.bone(centre - axis * 4, centre + axis * 4, 2, 2, 'leather', -1)
        if p['arrow'] and not dropped:
            u = unit(centre - joints['R']['hand']); tip = joints['R']['hand'] + u * 34
            ink.bone(joints['R']['hand'], tip, .55, .55, 'trim', -.5)
            ink.plate([tip + u * 4, tip + axis * 2, tip - axis * 2], 'metal', 3)
        if not dropped:
            a, b = xf((6, -8, 46)), xf((-4, -8, 74)); ink.bone(a, b, 4, 4, 'leather', -.5)
            for n in range(3): ink.bone(b + R @ V(n - 1, 0, 0), b + R @ V(n - 1, 0, 9 + n), .7, .7, 'trim', -.5)
        return
    names = 'LR' if cls == 'assassin' else 'R' if cls in ('warrior', 'priest') else 'L'
    for n, key in enumerate(names):
        hand = joints[key]['hand']; direction = p['blade' + key] if cls == 'assassin' else p[{'warrior': 'blade', 'priest': 'mace', 'mage': 'staff'}[cls]]
        u, across = R @ unit(V(*direction)), R @ V(1, 0, 0)
        if dropped: hand, u = V((n * 2 - 1) * 21, -8, 3), unit(V(.4, 1, 0)); across = unit(V(u[1], -u[0], 0))
        if cls in ('mage', 'priest'):
            # Nave staves keep the cathedral silhouette while staying inside the mage attack rig's
            # tight male frame; the longer level tiers use the full reach.
            length = (28 if ix == 8 else 32 + ix * .5) if cls == 'mage' else 24 + ix * .4
            end = hand + u * length
            ink.bone(hand - u * (24 if cls == 'mage' else 4), end, 1.6, 1.3, 'leather', -.2)
            ink.bone(hand + u * 5, hand + u * 7, 2.5, 2.5, 'trim', -.6)
            size = 6.5 + ix * .35
            jewel(ink, end, across, u, size)
            for sx in (-1, 1):
                ink.plate([end - u * size, end + across * sx * (size + 3), end + u * (size + 2), end + across * sx * 3], 'metal', 2)
            if cls == 'priest':
                ink.bone(end - u * 5, end + u * 6, 6 + ix % 2, 6, 'metal', -.5)
                jewel(ink, end + R @ V(0, 6, 0), across, u, 4)
                if style in (1, 4): ink.plate([end + u * 5, end + across * 8, end - u * 2, end - across * 8], 'trim', 2, True)
            elif style in (0, 2, 5):
                ink.plate([end + u * 5, end + across * (5 + style), end - u * 2, end - across * (5 + style)], 'gem', 2, True)
            return
        # Broad hooked twin daggers, or a notched longsword; never the starter straight blades.
        guard, length = hand + u * 4, ([19, 25, 21, 28, 23, 27][style] if cls == 'assassin' else [29, 37, 33, 41, 31, 39][style])
        end = hand + u * length
        ink.bone(hand - u * 3, guard, 1.5, 1.5, 'leather', -.3)
        ink.plate([guard - across * 5, guard + across * 5, guard + u * 3 + across * 3, guard + u * 3 - across * 3], 'trim', 2)
        if cls == 'assassin':
            # A tapering curved point reads as a dagger rather than a flat-ended cleaver.
            ink.plate([guard - across * 2, guard + u * 7 - across * (4 + ix * .2),
                       end - u * 3 - across * 2, end + u * 3 + across * 2,
                       end - u * 5 + across * (4 + ix * .25), end - u * 8 + across * 2,
                       guard + u * 3 + across * 2, guard + across * 2], 'metal', 2)
            if style in (2, 5): ink.plate([guard + u * 5, guard + across * 7, guard + u * 9, guard - across * 2], 'gem', 2, True)
        else:
            ink.plate([guard - across * 2, guard + u * 6 - across * (4.5 + ix * .27), end - across * 2,
                       end + across * (5 if ix in (5, 8) else 1), end - u * 5 + across * 4,
                       guard + u * 3 + across * 3, guard + across * 2], 'metal', 2)
        ink.plate([guard + u * 2, end - u * 2, end + across * 1.1, guard + u * 4 + across * 1.1], 'gem', 3, True)
        if ix in (5, 8):
            for z in (7, 13): ink.plate([guard + u * z - across * 3, guard + u * (z + 2) - across * 6, guard + u * (z + 4) - across * 3], 'metal', 2)
    if cls == 'warrior':
        c = (joints['L']['elbow'] + joints['L']['hand']) / 2 + R @ V(0, 3, 0); a, b = R @ V(1, 0, 0), R @ V(0, 0, 1)
        if dropped: c, a, b = V(-21, 8, 2), V(1, 0, 0), V(0, 1, 0)
        points = [(-9, 12), (9, 12), (12, 5), (9, -8), (0, -17 - ix % 3), (-9, -8), (-12, 5)]
        ink.plate([c + a * x + b * y for x, y in points], 'metal', 2)
        ink.plate([c + a * x * .7 + b * y * .7 + R @ V(0, 1, 0) for x, y in points], 'cloth', 2)
        jewel(ink, c + R @ V(0, 2, 0), a, b, 6)


def render(cls, theme, kind, gender, clip, facing, k):
    module, ink, p, R, xf, joints, head = pose(cls, gender, clip, facing, k)
    d = DESIGNS[theme]
    if kind == 'armor': armor(ink, cls, d, p, R, xf, joints)
    elif kind == 'headgear': headgear(ink, cls, d, head)
    elif kind == 'shoulders': shoulders(ink, cls, d, R, joints)
    elif kind == 'gloves': gloves(ink, cls, d, R, joints)
    elif kind == 'weapon': weapon(ink, cls, d, p, R, xf, joints)
    elif kind == 'pants': pants(ink, d, R, joints)
    elif kind == 'necklace': necklace(ink, d, R, xf)
    elif kind == 'accessory': accessory(ink, d, R, joints)
    else: raise ValueError(kind)
    return ink.resolve(clip in ('hurt', 'die') and k == 0)
