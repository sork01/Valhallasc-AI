"""Pose-fitted silhouettes for the nine level-75–99 dungeon reward sets."""
import colorsys
import numpy as np

import cel_common as cc
from cel_common import V, unit
import gear_shapes as base

# Back, crown and weapon outlines are deliberately different for each origin.
# Coordinates are local to the shared character rig, so every clip and facing
# keeps the original weapon grip, body depth and ground anchor.
STYLES = {
    'pavilion': dict(hue=43, back=[(5, 69), (16, 82), (27, 75), (20, 62), (29, 47), (8, 48)],
                     crown=[(-19, 15), (-12, 28), (-5, 19), (0, 27), (5, 19), (12, 28), (19, 15), (0, 12)],
                     weapon=[(-14, 13), (-15, 24), (0, 20), (15, 24), (14, 13), (0, 8)], shoulder=(22, 12)),
    'rain': dict(hue=196, back=[(5, 68), (14, 77), (22, 71), (27, 58), (18, 53), (22, 36), (7, 42)],
                 crown=[(-17, 12), (-12, 24), (-6, 16), (0, 29), (6, 16), (12, 24), (17, 12), (0, 10)],
                 weapon=[(-12, 12), (-8, 22), (0, 27), (8, 22), (12, 12), (0, 7)], shoulder=(20, 19)),
    'seed': dict(hue=118, back=[(5, 64), (17, 77), (27, 73), (30, 62), (23, 48), (12, 43), (7, 51)],
                 crown=[(-15, 15), (-8, 27), (0, 21), (8, 27), (15, 15), (0, 8)],
                 weapon=[(-13, 13), (-7, 23), (0, 28), (7, 23), (13, 13), (0, 6)], shoulder=(23, 15)),
    'astro': dict(hue=32, back=[(6, 67), (15, 77), (27, 73), (32, 59), (24, 48), (18, 57), (9, 43)],
                  crown=[(-18, 13), (-9, 19), (0, 29), (9, 19), (18, 13), (7, 11), (0, 4), (-7, 11)],
                  weapon=[(-14, 12), (-9, 20), (0, 25), (9, 20), (14, 12), (0, 5)], shoulder=(24, 10)),
    'thunder': dict(hue=266, back=[(5, 70), (16, 82), (12, 65), (30, 75), (20, 50), (30, 52), (9, 34)],
                    crown=[(-17, 12), (-11, 27), (-5, 20), (0, 28), (6, 17), (14, 25), (18, 11), (0, 7)],
                    weapon=[(-15, 12), (-5, 27), (-4, 15), (11, 24), (4, 10), (0, 4)], shoulder=(27, 18)),
    'bloom': dict(hue=326, back=[(4, 66), (14, 81), (26, 79), (31, 64), (25, 47), (10, 40), (7, 53)],
                  crown=[(-19, 14), (-13, 27), (-5, 20), (0, 29), (5, 20), (13, 27), (19, 14), (0, 9)],
                  weapon=[(-15, 13), (-12, 23), (0, 28), (12, 23), (15, 13), (0, 8)], shoulder=(24, 16)),
    'solar': dict(hue=18, back=[(5, 70), (18, 83), (27, 78), (23, 65), (33, 56), (20, 47), (10, 38)],
                  crown=[(-18, 12), (-13, 24), (-6, 19), (0, 29), (6, 19), (13, 24), (18, 12), (0, 8)],
                  weapon=[(-16, 12), (-12, 23), (0, 29), (12, 23), (16, 12), (0, 5)], shoulder=(28, 14)),
    'amber': dict(hue=39, back=[(5, 70), (15, 82), (27, 75), (27, 59), (19, 55), (25, 37), (7, 42)],
                  crown=[(-17, 13), (-12, 27), (-3, 24), (0, 28), (8, 21), (16, 25), (18, 12), (0, 7)],
                  weapon=[(-13, 11), (-10, 26), (0, 22), (11, 27), (14, 12), (0, 5)], shoulder=(21, 17)),
    'solstice': dict(hue=219, back=[(5, 69), (15, 81), (28, 81), (21, 68), (33, 53), (19, 40), (8, 47)],
                     crown=[(-19, 10), (-14, 25), (-7, 28), (0, 17), (7, 28), (14, 25), (19, 10), (0, 6)],
                     weapon=[(-17, 12), (-12, 25), (1, 28), (13, 20), (7, 9), (0, 5)], shoulder=(26, 20)),
}
ROLES = ('cloth', 'metal', 'trim', 'gem', 'leather', 'veil')
ROLE_TONES = {
    'cloth': (0, .44, (.12, .22, .35, .56)),
    'metal': (18, .36, (.17, .31, .49, .71)),
    'trim': (54, .56, (.18, .32, .50, .73)),
    'gem': (116, .73, (.15, .29, .48, .75)),
    'leather': (-34, .36, (.13, .24, .37, .59)),
    'veil': (76, .36, (.14, .28, .44, .67)),
}
THEME_HUES = {
    'pavilion': (45, 49, 8, 6, 30, 50),
    'rain': (200, 204, 235, 182, 207, 190),
    'seed': (127, 93, 43, 103, 62, 129),
    'astro': (218, 42, 35, 195, 34, 204),
    'thunder': (267, 258, 49, 189, 273, 250),
    'bloom': (328, 336, 72, 154, 340, 302),
    'solar': (15, 25, 43, 48, 20, 7),
    'amber': (28, 31, 26, 18, 22, 37),
    'solstice': (225, 207, 199, 180, 230, 214),
}
PALETTES = {}


def palette(theme):
    if theme not in PALETTES:
        mats = {}
        for role, hue in zip(ROLES, THEME_HUES[theme]):
            _, saturation, lights = ROLE_TONES[role]
            colors = []
            for light in lights:
                rgb = colorsys.hls_to_rgb(hue / 360, light, saturation)
                colors.append('#' + ''.join(f'{round(c * 255):02x}' for c in rgb))
            mats[theme + '_' + role] = colors
        PALETTES[theme] = cc.palette_of({**base.MATS, **mats})
    return PALETTES[theme]


def recolor(indices, theme):
    _, color = palette(theme)
    mapping = np.arange(len(palette(theme)[0]), dtype=np.uint8)
    for role in ROLES:
        mapping[base.COLOR[role]] = color[theme + '_' + role]
    return mapping[indices]


def adorn(ink, theme, cls, kind, p, R, xf, joints, head):
    spec = STYLES[theme]
    _, color = palette(theme)
    metal, trim, gem, veil = (theme + '_' + role for role in ('metal', 'trim', 'gem', 'veil'))
    up, side = R @ V(0, 0, 1), R @ V(1, 0, 0)
    if kind == 'armor':
        for sx in (-1, 1):
            ink.plate([xf((sx * x, -7 - x * .14, z)) for x, z in spec['back']], veil, 2)
            ink.plate([xf((sx * x, -7.4 - x * .14, z - 3))
                       for x, z in spec['back'][:4]], metal, 2, True)
        c = xf((0, 7.2, 58))
        reach = 7 + (spec['hue'] % 4)
        ink.plate([c + up * 10, c + side * reach + up * 2,
                   c + side * 6 - up * 7, c - up * 10,
                   c - side * 6 - up * 7, c - side * reach + up * 2], trim, 3)
        ink.plate([c + up * 5, c + side * 4, c - up * 5, c - side * 4], gem, 3)
        if theme in ('astro', 'solar', 'solstice'):
            for sx in (-1, 1):
                ink.bone(c + side * sx * 4, c + side * sx * 11 + up * 8,
                         1.2, .8, gem, -2, 3)
        if theme == 'pavilion':
            for sx in (-1, 1):
                for n in range(3):
                    ink.plate([xf((sx * 7, -8, 65)), xf((sx * (22 + n * 3), -12, 80 - n * 10)),
                               xf((sx * (26 + n * 3), -12, 70 - n * 10)), xf((sx * 10, -8, 55))],
                              veil, 3 if n % 2 else 2)
        elif theme == 'astro':
            for sx in (-1, 1):
                ink.plate([xf((sx * 10, -9, 80)), xf((sx * 31, -12, 69)),
                           xf((sx * 28, -12, 46)), xf((sx * 13, -9, 39))], trim, 3)
                ink.plate([xf((sx * 14, -10, 73)), xf((sx * 24, -12, 67)),
                           xf((sx * 22, -12, 52)), xf((sx * 15, -9, 48))], veil, 1)
        elif theme == 'solar':
            for sx in (-1, 1):
                for n in range(3):
                    ink.plate([xf((sx * 8, -8, 64)),
                               xf((sx * (24 + n * 4), -12, 82 - n * 15)),
                               xf((sx * 15, -9, 55 - n * 5))], trim, 3)
        elif theme == 'amber':
            for sx in (-1, 1):
                ink.plate([xf((sx * 11, -8, 73)), xf((sx * 29, -11, 76)),
                           xf((sx * 29, -11, 42)), xf((sx * 11, -8, 39))], veil, 3)
                ink.plate([xf((sx * 14, -9, 69)), xf((sx * 26, -12, 70)),
                           xf((sx * 26, -12, 48)), xf((sx * 14, -9, 46))], trim, 3, True)
    elif kind == 'headgear':
        H, hd = head['H'], head['hd'] - 8.3
        ink.poly([H(x, y) for x, y in spec['crown']], color[metal][3], hd)
        ink.poly([H(-6, 9), H(0, 17), H(6, 9), H(0, 3)], color[gem][3], hd - .2)
        if theme in ('rain', 'seed', 'bloom', 'solar'):
            for sx in (-1, 1):
                ink.poly([H(sx * 9, 16), H(sx * 17, 24), H(sx * 12, 11)], color[trim][3], hd - .1)
        if theme == 'solar':
            for sx in (-1, 1):
                ink.poly([H(sx * 12, 17), H(sx * 20, 27), H(sx * 17, 13)], color[metal][3], hd - .1)
        elif theme == 'amber':
            for sx in (-1, 1):
                ink.poly([H(sx * 10, 15), H(sx * 17, 28), H(sx * 19, 14)], color[trim][3], hd - .1)
    elif kind == 'shoulders':
        reach, high = spec['shoulder']
        for sx, key in ((-1, 'L'), (1, 'R')):
            sh = joints[key]['shoulder']; out = side * sx
            ink.plate([sh + out * 2 + up * 5, sh + out * (reach - 8) + up * high,
                       sh + out * reach + up * (high - 3), sh + out * (reach - 2) - up * 7,
                       sh + out * 5 - up * 5], metal, 3)
            ink.plate([sh + out * 6 + up * 6, sh + out * (reach - 5) + up * (high - 2),
                       sh + out * (reach - 6) - up * 2], gem, 3, True)
            if theme in ('thunder', 'solar', 'solstice'):
                ink.bone(sh + out * 8 + up * 4, sh + out * (reach - 1) + up * (high + 3),
                         1.4, .8, trim, -2, 3)
    elif kind == 'gloves':
        width = 4 + list(STYLES).index(theme) % 3
        for key in 'LR':
            hand, elbow = joints[key]['hand'], joints[key]['elbow']
            line = unit(elbow - hand)
            across = side * (-1 if key == 'L' else 1)
            c = hand + line * 7
            ink.plate([c - across * width, c + line * (12 + width) - across * width,
                       c + line * (10 + width) + across * width,
                       c + across * width], metal, 3)
            for n in (-1, 0, 1):
                ink.bone(c + across * (n * 3), c - line * 4 + across * (n * 4),
                         1.2, .8, gem, -2, 3)
    elif kind == 'weapon':
        keys = 'LR' if cls == 'assassin' else 'L' if cls in ('mage', 'hunter') else 'R'
        for key in keys:
            hand = joints[key]['hand']
            ink.plate([hand + side * x + up * z for x, z in spec['weapon']], metal, 3)
            ink.plate([hand + up * 9, hand + side * 4 + up * 14,
                       hand + up * 20, hand - side * 4 + up * 14], gem, 3)
            if theme in ('pavilion', 'bloom', 'amber'):
                for sx in (-1, 1):
                    ink.bone(hand + up * 11, hand + up * 23 + side * sx * 10,
                             1.0, .8, trim, -2, 3)
    elif kind == 'pants':
        reach = 4 + list(STYLES).index(theme) % 4
        for key in 'LR':
            knee, ankle = joints[key]['knee'], joints[key]['ankle']
            line = unit(ankle - knee)
            for n in range(3):
                c = knee + line * (2 + n * 4)
                ink.plate([c - side * reach, c + line * (3 + n),
                           c + side * reach, c - line * 2], metal, 3)
    elif kind in ('necklace', 'accessory'):
        c = xf((0, 7.6, 58)) if kind == 'necklace' else joints['L']['hand'] + R @ V(0, 3.5, 1.6)
        radius = 6 if kind == 'accessory' else 4
        ink.plate([c + up * radius, c + side * radius,
                   c - up * radius, c - side * radius], trim, 3)
        ink.plate([c + up * (radius - 2), c + side * (radius - 2),
                   c - up * (radius - 2), c - side * (radius - 2)], gem, 3)


def render(cls, theme, kind, gender, clip, facing, frame):
    _, ink, p, R, xf, joints, head = base.pose(cls, gender, clip, facing, frame)
    ink.color = palette(theme)[1]
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
