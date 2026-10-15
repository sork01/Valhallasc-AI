"""Pose-fitted abyssal eye and living oak equipment for two later dungeons."""
import numpy as np

import cel_common as cc
from cel_common import V, unit
import gear_shapes as base

# The two themes append indexed colours; prior progression and dungeon palettes
# retain their indices and all saved PixelFlow cels remain editable.
EXTRA_MATS = {
    'eye_cloth': ['#161b30', '#252b4b', '#414d78', '#798bb2'],
    'eye_metal': ['#30213f', '#563672', '#8c59ab', '#c293db'],
    'eye_trim': ['#32243c', '#654667', '#b4749b', '#efa8b9'],
    'eye_gem': ['#273746', '#396d80', '#65bdd0', '#c5f8fb'],
    'eye_leather': ['#211d2d', '#393044', '#665171', '#a17aa1'],
    'eye_veil': ['#1a2239', '#334260', '#596e95', '#a6bbd2'],
    'elder_cloth': ['#263127', '#405b39', '#6c8751', '#b3c880'],
    'elder_metal': ['#352b27', '#604b37', '#93704c', '#c9aa72'],
    'elder_trim': ['#3b3325', '#71613c', '#ad9753', '#f0da91'],
    'elder_gem': ['#164a3c', '#338262', '#6ac48a', '#d2f5ac'],
    'elder_leather': ['#28271e', '#4b422d', '#796342', '#b99b64'],
    'elder_veil': ['#1e332b', '#355544', '#638765', '#a5bc83'],
}
PALETTE, COLOR = cc.palette_of({**base.MATS, **EXTRA_MATS})
ROLES = ('cloth', 'metal', 'trim', 'gem', 'leather', 'veil')


def recolor(indices, theme):
    mapping = np.arange(len(PALETTE), dtype=np.uint8)
    for role in ROLES:
        mapping[base.COLOR[role]] = COLOR[f'{theme}_{role}']
    return mapping[indices]


def adorn(ink, theme, cls, kind, p, R, xf, joints, head):
    """Silhouette geometry stays on the existing skeleton in every pose and turn."""
    eye = theme == 'eye'
    metal, trim, gem, veil = (f'{theme}_{role}' for role in ('metal', 'trim', 'gem', 'veil'))
    up, side = R @ V(0, 0, 1), R @ V(1, 0, 0)
    if kind == 'armor':
        if eye:
            # A giant iris on the chest, with long broken fins along the back.
            for sx in (-1, 1):
                ink.plate([xf(q) for q in [(sx * 5, -6, 64), (sx * 13, -9, 78),
                                            (sx * 24, -12, 84), (sx * 16, -10, 55)]], veil, 2)
                ink.plate([xf(q) for q in [(sx * 6, -7, 45), (sx * 17, -11, 50),
                                            (sx * 23, -12, 30), (sx * 9, -7, 33)]], metal, 2)
            c = xf((0, 7.1, 59))
            ink.plate([c + up * 9, c + side * 10, c - up * 9, c - side * 10], trim, 3)
            ink.plate([c + up * 6, c + side * 6, c - up * 6, c - side * 6], gem, 2)
            ink.plate([c + up * 4, c + side * 3, c - up * 4, c - side * 3], metal, 3)
        else:
            # Forking roots and leaf plates carry the green core across the torso.
            for sx in (-1, 1):
                ink.bone(xf((sx * 2, 6.8, 67)), xf((sx * 7, 7.0, 45)),
                         1.3, 2.0, metal, -2, 3)
                ink.plate([xf(q) for q in [(sx * 6, 7, 64), (sx * 13, 6, 68),
                                            (sx * 10, 7, 55), (sx * 3, 7, 53)]], gem, 2)
                ink.plate([xf(q) for q in [(sx * 5, -7, 41), (sx * 19, -10, 37),
                                            (sx * 22, -11, 20), (sx * 10, -8, 28)]], veil, 2)
            ink.plate([xf(q) for q in [(0, 7.3, 67), (5, 7.5, 60), (0, 7.7, 50),
                                        (-5, 7.5, 60)]], trim, 3)
    elif kind == 'headgear':
        H, hd = head['H'], head['hd'] - 8.4
        if eye:
            # Tall split antennae frame a single obvious pupil.
            for sx in (-1, 1):
                ink.poly([H(sx * 6, 18), H(sx * 9, 27), H(sx * 16, 29),
                          H(sx * 13, 23), H(sx * 11, 13)], COLOR[metal][3], hd)
            ink.poly([H(-7, 9), H(0, 17), H(7, 9), H(0, 2)], COLOR[trim][3], hd - .2)
            ink.poly([H(-4, 9), H(0, 13), H(4, 9), H(0, 5)], COLOR[gem][3], hd - .3)
        else:
            # Branching antlers and a leaf crown, visibly unlike ordinary helms.
            for sx in (-1, 1):
                ink.poly([H(sx * 5, 17), H(sx * 9, 25), H(sx * 16, 29),
                          H(sx * 14, 24), H(sx * 23, 27), H(sx * 14, 21),
                          H(sx * 12, 13)], COLOR[metal][3], hd)
                ink.poly([H(sx * 10, 20), H(sx * 17, 24), H(sx * 14, 18)], COLOR[gem][3], hd - .1)
            ink.poly([H(-5, 14), H(0, 23), H(5, 14), H(0, 10)], COLOR[trim][3], hd - .2)
    elif kind == 'shoulders':
        for sx, key in ((-1, 'L'), (1, 'R')):
            sh = joints[key]['shoulder']; out = side * sx
            if eye:
                ink.plate([sh + out * 2 + up * 5, sh + out * 17 + up * 21,
                           sh + out * 25 + up * 12, sh + out * 19 - up * 6,
                           sh + out * 5 - up * 4], metal, 3)
                ink.plate([sh + out * 6 + up * 7, sh + out * 16 + up * 15,
                           sh + out * 17 + up * 2], gem, 3, True)
            else:
                for n in (0, 1):
                    ink.bone(sh + out * (3 + n * 5),
                             sh + out * (19 + n * 5) + up * (18 - n * 7),
                             3.4, 1.2, metal, -2, 3)
                ink.plate([sh + out * 6 + up * 5, sh + out * 17 + up * 12,
                           sh + out * 22 + up * 3, sh + out * 10 - up * 5], gem, 2)
    elif kind == 'gloves':
        for key in 'LR':
            hand, elbow = joints[key]['hand'], joints[key]['elbow']
            line = unit(elbow - hand)
            across = side * (-1 if key == 'L' else 1)
            c = hand + line * 7
            ink.plate([c - across * 5, c + line * 11 - across * 6,
                       c + line * 14 + across * 7, c + across * 6], metal, 3)
            for n in (-1, 0, 1):
                end = c - line * (4 if eye else 2) + across * (n * 4)
                ink.bone(c + across * (n * 3), end, 1.3, .8, gem if eye else trim, -2, 3)
    elif kind == 'weapon':
        keys = 'LR' if cls == 'assassin' else 'L' if cls in ('mage', 'hunter') else 'R'
        for key in keys:
            hand = joints[key]['hand']
            if eye:
                for sx in (-1, 1):
                    ink.plate([hand + up * 7, hand + up * 21 + side * sx * 12,
                               hand + up * 18 + side * sx * 4], metal, 3)
                ink.plate([hand + up * 19, hand + side * 7 + up * 14,
                           hand + up * 9, hand - side * 7 + up * 14], gem, 3)
            else:
                ink.bone(hand + up * 3, hand + up * 21, 3.2, 1.1, metal, -2, 3)
                for sx in (-1, 1):
                    ink.plate([hand + up * 11, hand + up * 23 + side * sx * 13,
                               hand + up * 14 + side * sx * 8], gem, 3)
    elif kind == 'pants':
        for key in 'LR':
            knee, ankle = joints[key]['knee'], joints[key]['ankle']
            line = unit(ankle - knee)
            for n in range(3):
                c = knee + line * (n * 4 + 2)
                ink.plate([c - side * 5, c + line * 3, c + side * 5,
                           c - line * 2], metal if eye else gem, 3)
    elif kind in ('necklace', 'accessory'):
        c = xf((0, 7.6, 58)) if kind == 'necklace' else joints['L']['hand'] + R @ V(0, 3.5, 1.6)
        radius = 6 if kind == 'accessory' else 4
        ink.plate([c + up * radius, c + side * radius, c - up * radius,
                   c - side * radius], metal, 3)
        ink.plate([c + up * (radius - 2), c + side * (radius - 2),
                   c - up * (radius - 2), c - side * (radius - 2)], gem, 3)


def render(cls, theme, kind, gender, clip, facing, frame):
    _, ink, p, R, xf, joints, head = base.pose(cls, gender, clip, facing, frame)
    ink.color = COLOR
    design = base.DESIGNS[theme]
    if kind == 'armor': base.armor(ink, cls, design, p, R, xf, joints)
    elif kind == 'headgear': base.headgear(ink, cls, design, head)
    elif kind == 'shoulders': base.shoulders(ink, cls, design, R, joints)
    elif kind == 'gloves': base.gloves(ink, cls, design, R, joints)
    elif kind == 'weapon': base.weapon(ink, cls, design, p, R, xf, joints)
    elif kind == 'pants': base.pants(ink, design, R, joints)
    elif kind == 'necklace': base.necklace(ink, design, R, xf)
    elif kind == 'accessory': base.accessory(ink, design, R, joints)
    else: raise ValueError(kind)
    adorn(ink, theme, cls, kind, p, R, xf, joints, head)
    indices, depth = ink.resolve(clip in ('hurt', 'die') and frame == 0)
    return recolor(indices, theme), depth
