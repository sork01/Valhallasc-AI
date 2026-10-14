"""Distinct rigged Undervault and Moonwell equipment layers and their indexed palettes."""
import numpy as np

import cel_common as cc
from cel_common import V, unit
import gear_shapes as base

# Append colours without changing the indices of the existing progression art.
EXTRA_MATS = {
    'vault_cloth': ['#222d38', '#394958', '#61717c', '#a3aeb0'],
    'vault_metal': ['#293742', '#536370', '#87949b', '#c6ccbf'],
    'vault_trim': ['#35343c', '#66616a', '#a39d96', '#e0dbc4'],
    'vault_gem': ['#073f47', '#10757b', '#31b6ae', '#a9f1df'],
    'vault_leather': ['#25272f', '#44444c', '#747179', '#aca7a0'],
    'vault_veil': ['#252f40', '#405264', '#6b8091', '#b3c6c6'],
    'moon_cloth': ['#26364e', '#445a7e', '#7987b2', '#bdcbe0'],
    'moon_metal': ['#44566b', '#77949e', '#b3d3cd', '#e8f2da'],
    'moon_trim': ['#715e73', '#af91a9', '#e5c4c2', '#f8e8ad'],
    'moon_gem': ['#185b68', '#378e9b', '#88d6c7', '#c9fff0'],
    'moon_leather': ['#29384d', '#4b5878', '#777aaa', '#b4afd1'],
    'moon_veil': ['#383954', '#655a87', '#9b86ae', '#d6c4dc'],
}
PALETTE, COLOR = cc.palette_of({**base.MATS, **EXTRA_MATS})
ROLES = ('cloth', 'metal', 'trim', 'gem', 'leather', 'veil')


def recolor(indices, theme):
    mapping = np.arange(len(PALETTE), dtype=np.uint8)
    prefix = 'vault_' if theme == 'vault' else 'moon_'
    for role in ROLES:
        mapping[base.COLOR[role]] = COLOR[prefix + role]
    return mapping[indices]


def adorn(ink, theme, cls, kind, p, R, xf, joints, head):
    """Draw recognizable bone/rune or petal/moon details on the original pose rig."""
    vault = theme == 'vault'
    prefix = 'vault_' if vault else 'moon_'
    metal, trim, gem = prefix + 'metal', prefix + 'trim', prefix + 'gem'
    if kind == 'armor':
        if vault:
            # A visible ribcage over the breastplate, with a cold ward rune.
            for z in (64, 59, 54):
                for sx in (-1, 1):
                    ink.plate([xf(q) for q in [(0, 6.3, z - 1), (sx * 7, 6.3, z + 1),
                                                (sx * 9, 5.4, z - 1), (sx * 1, 6.4, z - 2)]], metal, 3)
            ink.bone(xf((0, 6.6, 66)), xf((0, 6.8, 48)), 1.2, 1.2, trim, -1.8, 3)
            ink.plate([xf(q) for q in [(0, 7, 61), (2.3, 7, 58), (0, 7, 54), (-2.3, 7, 58)]], gem, 3)
        else:
            # Overlapping lily petals and a crescent brooch follow the turning torso.
            for sx in (-1, 1):
                ink.plate([xf(q) for q in [(sx * 1, 6.5, 67), (sx * 9, 5.7, 65),
                                            (sx * 6, 6, 48), (sx * 1, 6.7, 54)]], metal, 2)
                ink.plate([xf(q) for q in [(sx * 1, 6.8, 65), (sx * 6, 6.1, 63),
                                            (sx * 3, 6.6, 57)]], gem, 3, True)
            ink.plate([xf(q) for q in [(-3.5, 7, 59), (0, 7.2, 63), (3.5, 7, 59),
                                        (0, 7.3, 60)]], trim, 3)
    elif kind == 'headgear':
        H, hd = head['H'], head['hd'] - 8.2
        if vault:
            for sx in (-1, 1):
                ink.poly([H(sx * 5, 20), H(sx * 8, 31), H(sx * 10, 24)], COLOR[metal][3], hd)
            ink.poly([H(-3, 15), H(0, 22), H(3, 15), H(0, 12)], COLOR[gem][3], hd - .1)
        else:
            ink.poly([H(-8, 21), H(-4, 30), H(3, 33), H(10, 27), H(6, 26),
                      H(1, 29), H(-4, 27)], COLOR[trim][3], hd)
            ink.poly([H(-2, 20), H(0, 24), H(2, 20), H(0, 17)], COLOR[gem][3], hd - .1)
    elif kind == 'shoulders':
        for sx, key in ((-1, 'L'), (1, 'R')):
            shoulder = joints[key]['shoulder']; out, up = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            if vault:
                ink.plate([shoulder + out * 5 + up * 2, shoulder + out * 15 + up * 13,
                           shoulder + out * 11 + up * 2, shoulder + out * 5 - up * 2], metal, 3)
                ink.bone(shoulder + out * 5, shoulder + out * 10 + up * 5, 1.2, .8, gem, -2, 3)
            else:
                ink.plate([shoulder + out * 2 + up * 4, shoulder + out * 11 + up * 13,
                           shoulder + out * 15 + up * 5, shoulder + out * 8 - up * 2], metal, 3)
                ink.plate([shoulder + out * 4 + up * 4, shoulder + out * 10 + up * 8,
                           shoulder + out * 12 + up * 2], gem, 3, True)
    elif kind == 'gloves':
        for key in 'LR':
            hand, elbow = joints[key]['hand'], joints[key]['elbow']
            up, across = unit(elbow - hand), R @ V(1, 0, 0)
            c = hand + up * 7
            for sx in (-1, 1):
                ink.plate([c + across * sx * 2, c + across * sx * (5 if vault else 7) + up * 6,
                           c + up * 10], metal if vault else gem, 3)
            ink.bone(c, c + up * 10, 1.0, .7, gem if vault else trim, -2, 3)
    elif kind == 'weapon':
        keys = 'LR' if cls == 'assassin' else 'L' if cls in ('mage', 'hunter') else 'R'
        for key in keys:
            hand = joints[key]['hand']; up = R @ V(0, 0, 1); side = R @ V(1, 0, 0)
            # A cage or crescent at the grip leaves the existing pose and projectile timing intact.
            if vault:
                for sx in (-1, 1):
                    ink.plate([hand + up * 7, hand + up * 15 + side * sx * 8,
                               hand + up * 12 + side * sx * 4], metal, 3)
                ink.plate([hand + up * 11, hand + side * 3 + up * 7,
                           hand + up * 3, hand - side * 3 + up * 7], gem, 3)
            else:
                ink.plate([hand + up * 8 - side * 8, hand + up * 18,
                           hand + up * 8 + side * 8, hand + up * 11,
                           hand + up * 15, hand + up * 11 - side * 4], trim, 3)
                ink.plate([hand + up * 9 - side * 2, hand + up * 13,
                           hand + up * 9 + side * 2], gem, 3)
    elif kind == 'pants':
        for key in 'LR':
            knee, ankle = joints[key]['knee'], joints[key]['ankle']; line = unit(ankle - knee)
            for n in (1, 2, 3):
                c = knee + line * (n * 3)
                ink.bone(c, c + line * 1.2, 4.3 if vault else 3.5, 3.4, metal, -1.5, 3)
    elif kind in ('necklace', 'accessory'):
        c = xf((0, 7.6, 57)) if kind == 'necklace' else joints['L']['hand'] + R @ V(0, 3.5, 1.6)
        side, up = R @ V(1, 0, 0), R @ V(0, 0, 1)
        if vault:
            ink.plate([c + up * 4, c + side * 4, c - up * 4, c - side * 4], metal, 3)
            ink.plate([c + up * 2, c + side * 2, c - up * 2, c - side * 2], gem, 3)
        else:
            ink.plate([c - side * 4, c + up * 5, c + side * 4,
                       c + up * 2, c, c - side * 1], trim, 3)
            ink.plate([c + up * 2, c + side * 2, c - up * 2, c - side * 2], gem, 3)


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
