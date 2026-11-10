#!/usr/bin/env python3
"""NPC-PLAYER-STYLE sample trio: NPCs drawn by the PLAYERS' rig (cel_common: skeleton, torso, head_frame, face), so the
proportions, eyes, outline and shading are the player's, not a copy of them.

usage: npcp_sample.py sheet OUT_DIR      before/after/player contact sheet for the trio, scratch only (never writes client/)

Nothing here touches client/assets or PixelFlow: it is the owner's go/no-go picture (TODO NPC-PLAYER-STYLE-SPEC).
The rig module (make_warrior_sprites.py) lives in <worktree>/rig-tools (copied out of old-valhalla-20261107.tar.gz);
set VALHALLA_TOOLS to move it. cel_common is imported read-only; its frame constants are patched at run time for the
96x96 NPC frame, so no class sprite is re-rendered.
"""
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
os.environ.setdefault('VALHALLA_TOOLS', str(ROOT / 'rig-tools'))
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
import cel_common as cc  # noqa: E402
from cel_common import V, rig  # noqa: E402

FRAME, ANCHOR = 96, (48, 90)
PLAYER_PX = 1.03                       # the players' render scale in their 160 px cell (figure 97 px with hair)
ADULT_PX = 0.81                        # an NPC adult: 97 * .81 / 1.03 = 76 px tall, the old sentinel's 75
CLIPS = (('idle', 6), ('walk', 8), ('talk', 6))


def ramp(hexc, f=(.45, .72, 1., 1.3)):
    rgb = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
    out = []
    for k in f:
        out.append('#' + ''.join(f'{min(255, round(v * k)):02x}' if k <= 1 else f'{round(v + (255 - v) * (k - 1)):02x}' for v in rgb))
    return out


def mats(design):
    """Material ramps: the players' face set, the design's skin/hair/cloth, and shared props."""
    m = {**cc.FACE_MATS}
    m['skin'] = ramp(design['skin'], (.62, .8, 1., 1.12))
    m['hair'] = ramp(design['hair'])
    m['cloth'] = ramp(design['coat'])
    m['trim'] = ramp(design.get('trim', '#d8ad59'))
    m['pants'] = ramp(design.get('pants', '#4a3f5c'))
    m['leather'] = ramp('#8a5a3c')
    m['metal'] = ['#46516b', '#7f98ad', '#b9d3e0', '#eaf6fb']
    m['wood'] = ['#3a2218', '#6b4128', '#a8703f', '#dca66a']
    m['gold'] = ['#6e4a12', '#b0801f', '#e8b840', '#fff0a0']
    m['iris'] = ramp(design.get('iris', '#4a78b8'), (.5, .8, 1., 1.4))
    m['extra'] = ramp(design.get('extra', '#3f9aa8'))
    m['tail'] = ramp(design.get('tail', design['coat']))
    # cc.palette_of insists on unique colours across ramps; nudge duplicates
    seen = set()
    for name, r in m.items():
        for i, c in enumerate(r):
            while c in seen:
                c = '#%06x' % ((int(c[1:], 16) + 1) & 0xffffff)
            seen.add(c)
            r[i] = c
    return m


def set_frame(px, female):
    cc.FW = cc.FH = FRAME
    cc.AX, cc.AY = ANCHOR[0], ANCHOR[1] - 1
    cc.PX = px
    cc.FEMALE = female
    cc.SHOULDER_X, cc.HIP_X = (7.2, 4.7) if female else (8, 4.2)


BASE = dict(root=(0, 0, 0), lean=3, twist=0, roll=0, sway=0, eyes='open', handL=(-11, 3, 45), handR=(11, 3, 45),
            footL=(-5, 0, 4), footR=(5, 0, 4), ground=False, mouth=0)


def pose(clip, k, design):
    a = k / {'idle': 6, 'walk': 8, 'talk': 6}[clip] * math.tau
    p = dict(BASE)
    if clip == 'idle':
        p.update(root=(0, 0, -.35 * math.sin(a)), sway=math.sin(a), eyes='closed' if k == 4 else 'open')
    elif clip == 'walk':
        q = k / 8

        def foot(s, t):
            t %= 1
            return (s * 5, 9 - t * 36 if t < .5 else -9 + (t - .5) * 36, 4 + (6 * math.sin((t - .5) * math.tau) if t >= .5 else 0))
        p.update(lean=10, roll=2 * math.sin(a), twist=5 * math.sin(a), root=(0, 0, -.6 * math.cos(a * 2)), sway=3 * math.sin(a),
                 handL=(-14, -3 - math.sin(a) * 3, 52), handR=(14, 5 + math.sin(a) * 3, 53), footL=foot(-1, q), footR=foot(1, q + .5))
    else:
        g = math.sin(a)
        p.update(lean=2, twist=4 * g, sway=g, root=(0, 0, -.2 * abs(g)), handL=(-15, 12 + 3 * g, 66 + 3 * math.sin(a * 2)),
                 eyes='closed' if k == 5 else 'open', mouth=1 if k % 2 else 0)
    p.update(design.get('pose', lambda clip, k, p: {})(clip, k, p))
    return p


def hair_cap(body, head, color, front):
    H, hd = head['H'], head['hd']
    if front > -.4:
        crown = [(-10.6, -6), (-11.6, 5), (-10, 12), (-5, 16), (1, 17.4), (7, 16), (11, 11), (11.8, 4), (10.6, -6),
                 (8.6, 0), (7, 4.4), (3, 6.8), (-.4, 4.6), (-3.6, 6.4), (-7, 4.2), (-9, 0)]
    else:
        body.poly([H(*q) for q in [(-9.5, 8), (-10.5, 0), (-8.5, -8), (-4, -10.5), (5, -9.5), (9.5, -5), (10.5, 4), (6.5, 13), (-3, 14)]], color['hair'][2], hd - 5)
        crown = [(-10.6, -6), (-11.6, 5), (-10, 12), (-5, 16), (1, 17.4), (7, 16), (11, 11), (11.8, 4), (10.6, -6), (8, -2), (0, -4), (-8, -2)]
    body.poly([H(*q) for q in crown], color['hair'][1], hd - 6)
    body.poly([H(*q) for q in [(-9, 11), (-3, 15.6), (4, 16), (9.6, 11), (9, 8.4), (3, 12), (-3, 12.4), (-8.4, 8)]], color['hair'][2], hd - 6.1, False)
    body.poly([H(*q) for q in [(-5, 14.4), (0, 16.2), (4, 15.2), (0, 13.6), (-4, 12.6)]], color['hair'][3], hd - 6.2, False)


def body_layer(ink, xf, joints, R, color, legs=True, cloth='cloth', pants='pants', w=1.):
    cc.torso(ink, xf, cloth, 7.8, 3.5)
    ink.bone(xf((0, 0, 68)), xf((0, 0, 77)), 2.2 * w, 2.1 * w, 'skin')
    for key in 'LR':
        j = joints[key]
        if legs:
            ink.bone(j['hip'], j['knee'], 3.3 * w, 2.9 * w, pants)
            ink.bone(j['knee'], j['ankle'], 2.7 * w, 1.9 * w, pants)
            ink.bone(j['ankle'] + V(0, -1, -1.5), j['ankle'] + V(0, 4, -2), 2 * w, 2.1 * w, 'skin')
        ink.bone(j['shoulder'], j['elbow'], 2.6 * w, 2.1 * w, 'skin')
        ink.bone(j['elbow'], j['hand'], 2 * w, 1.6 * w, 'skin')
        ink.bone(j['hand'] - R @ V(0, 0, 1), j['hand'] + R @ V(0, 0, 1.8), 2.2 * w, 1.8 * w, 'skin', -.2)


def sleeves(ink, joints, mat, f=1.0, r=3.4):
    for key in 'LR':
        j = joints[key]
        ink.bone(j['shoulder'], j['elbow'] if f >= 1 else j['shoulder'] + (j['elbow'] - j['shoulder']) * f, r, r * .9, mat, -.8)
        if f >= 1:
            ink.bone(j['elbow'], j['elbow'] + (j['hand'] - j['elbow']) * .25, r * .9, r * .8, mat, -.75)


def boots(ink, joints, mat='leather'):
    for key in 'LR':
        j = joints[key]
        ink.bone(j['knee'] + (j['ankle'] - j['knee']) * .55, j['ankle'], 2.5, 2.3, mat, -.6)
        ink.bone(j['ankle'] + V(0, -1, -1.5), j['ankle'] + V(0, 4.4, -2), 2.6, 2.7, mat, -.65)


def belt(ink, xf, mat='leather', z0=40, z1=44.5, half=8.6, y=4.3):
    for sy in (-1, 1):
        ink.plate([xf(q) for q in [(-half, sy * y, z1), (half, sy * y, z1), (half, sy * y, z0), (-half, sy * y, z0)]], mat, 2 if sy > 0 else 1)
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * half, -y, z1), (sx * half, y, z1), (sx * half, y, z0), (sx * half, -y, z0)]], mat, 1)
    ink.plate([xf(q) for q in [(-2.2, y + .2, z1 + .5), (2.2, y + .2, z1 + .5), (2.2, y + .2, z0 - .5), (-2.2, y + .2, z0 - .5)]], 'gold', 3, True)


# ----------------------------------------------------------------------------- the three designs
def smith(ink, xf, joints, R, head, p, color):
    body_layer(ink, xf, joints, R, color, cloth='cloth')
    cc.torso(ink, xf, 'cloth', 8.4, 4.0, 40, 69)
    sleeves(ink, joints, 'cloth', .55, 3.9)
    # heavy leather apron over the tunic, with a bib and a strap round the neck
    ink.plate([xf(q) for q in [(-6.4, 4.7, 66), (6.4, 4.7, 66), (7.4, 4.9, 30), (-7.4, 4.9, 30)]], 'leather', 2)
    ink.plate([xf(q) for q in [(-6.4, 4.9, 66), (6.4, 4.9, 66), (6.4, 5.0, 56), (-6.4, 5.0, 56)]], 'leather', 3, True)
    ink.plate([xf(q) for q in [(-5.8, 4.9, 66), (-4.2, 4.9, 66), (-1.6, 4.5, 70.5), (-3.2, 4.5, 70.5)]], 'leather', 1, True)
    ink.plate([xf(q) for q in [(5.8, 4.9, 66), (4.2, 4.9, 66), (1.6, 4.5, 70.5), (3.2, 4.5, 70.5)]], 'leather', 1, True)
    belt(ink, xf, 'leather', 38.5, 42.5, 8.5, 4.35)
    boots(ink, joints)
    # goggles pushed up on the forehead
    H, hd = head['H'], head['hd']
    if head['front'] > -.4:
        ink.poly([H(-9.6, 8.2), H(9.6, 8.2), H(9.8, 6.4), H(-9.8, 6.4)], color['leather'][1], hd - 6.3, False)
        for sx in (-1, 1):
            ink.poly([H(sx * 4.6 + dx * 3.1, 9.4 + dy * 3.1) for dx, dy in [(math.cos(i / 8 * math.tau), math.sin(i / 8 * math.tau)) for i in range(8)]],
                     color['metal'][2], hd - 6.4)
            ink.poly([H(sx * 4.6 + dx * 1.9, 9.4 + dy * 1.9) for dx, dy in [(math.cos(i / 8 * math.tau), math.sin(i / 8 * math.tau)) for i in range(8)]],
                     color['extra'][3], hd - 6.5, False)
    # hammer carried upright in the right hand
    h = joints['R']['hand']
    top = h + V(1.5, 2, 15)
    ink.bone(h + V(-.5, -.5, -7), top, 1.5, 1.5, 'wood', -.5)
    ink.bone(top + V(-6.5, 0, 0), top + V(6.5, 0, 0), 5.2, 5.2, 'metal', -.7)
    ink.bone(top + V(-6, 0, 1.6), top + V(6, 0, 1.6), 1.2, 1.2, 'metal', -.9, 3)
    ink.bone(h - R @ V(0, 0, .6), h + R @ V(0, 0, 2.2), 2.4, 2.0, 'skin', -1.4)


def child(ink, xf, joints, R, head, p, color):
    body_layer(ink, xf, joints, R, color, cloth='cloth', pants='pants')
    cc.torso(ink, xf, 'cloth', 8.4, 4.0, 40, 69)
    sleeves(ink, joints, 'cloth', .6, 3.6)
    # a short skirt-smock over the hips and a ribbon at the collar
    sw = p['sway']
    for sy, tone in ((-1, 1), (1, 2)):
        ink.plate([xf(q) for q in [(-8.4, sy * 4.2, 42), (8.4, sy * 4.2, 42), (11 + sw * .8, sy * 7.4, 22), (-11 + sw * .8, sy * 7.4, 22)]], 'cloth', tone)
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * 8.4, -4.2, 42), (sx * 8.4, 4.2, 42), (sx * 11 + sw * .8, 7.4, 22), (sx * 11 + sw * .8, -7.4, 22)]], 'cloth', 1)
    ink.plate([xf(q) for q in [(-11 + sw * .8, 7.5, 24.5), (11 + sw * .8, 7.5, 24.5), (11 + sw * .8, 7.5, 22), (-11 + sw * .8, 7.5, 22)]], 'trim', 2, True)
    belt(ink, xf, 'trim', 40, 43.5, 8.4, 4.1)
    boots(ink, joints)
    ink.plate([xf(q) for q in [(-3.4, 4.6, 68), (0, 4.8, 66.4), (3.4, 4.6, 68), (0, 4.8, 69.6)]], 'extra', 3, True)
    H, hd = head['H'], head['hd']
    # pigtails with ribbons
    for sx in (-1, 1):
        ink.poly([H(sx * 9.2, 5), H(sx * 13.6 + sw * sx * .4, 1), H(sx * 15.4 + sw * .6, -9), H(sx * 12.4 + sw * .5, -15), H(sx * 10.6, -4), H(sx * 9, -1)],
                 color['hair'][1], hd - 6.4)
        ink.poly([H(sx * 9.6, 3.6), H(sx * 12.6, 3), H(sx * 12.8, 1), H(sx * 9.8, 1.2)], color['extra'][2], hd - 6.5)
    # a diamond kite on a string from the right hand
    h = joints['R']['hand']
    kite_c = h + V(26, 2, 30)
    pts = [kite_c + V(0, 0, 18), kite_c + V(11, 0, 0), kite_c + V(0, 0, -14), kite_c + V(-11, 0, 0)]
    ink.ribbon([h + V(0, 0, 1.5), h + V(8, 1, 8), h + V(18, 1.5, 14), kite_c + V(0, 0, -14)], .5, .5, 'trim', 2, outline=False)
    ink.plate(pts, 'extra', 2)
    ink.plate([pts[0], pts[1], kite_c + V(0, 0, 0.4)], 'extra', 3, True)
    ink.plate([pts[0], pts[3], kite_c + V(0, 0, 0.4)], 'extra', 1, True)
    ink.bone(h - R @ V(0, 0, .6), h + R @ V(0, 0, 2.2), 2.4, 2.0, 'skin', -1.4)


def namar(ink, xf, joints, R, head, p, color):
    """A merman captain: no legs, a curled tail, fin ears, a horned helm and a banner spear."""
    body_layer(ink, xf, joints, R, color, legs=False, cloth='cloth')
    cc.torso(ink, xf, 'cloth', 8.4, 4.0, 46, 69)
    sleeves(ink, joints, 'cloth', .45, 3.6)
    ink.plate([xf(q) for q in [(-8.4, 4.4, 69), (8.4, 4.4, 69), (6.5, 4.5, 56), (-6.5, 4.5, 56)]], 'metal', 2, True)       # scale cuirass
    for x_ in (-4, 0, 4):
        ink.plate([xf(q) for q in [(x_ - 1.3, 4.7, 66), (x_, 4.7, 64), (x_ + 1.3, 4.7, 66), (x_, 4.7, 67.6)]], 'extra', 3, True)
    sw = p['sway']
    # hips run into a long tail: a ribbon from the waist, forward over the ground and up into a fin
    tail = [xf((0, 0, 44)), xf((0, 1, 35)), xf((-1, 3, 24)), xf((-5, 5, 13)), xf((-12, 6, 7)), xf((-20, 5, 8)), xf((-25 - sw, 3, 16))]
    ink.ribbon(tail, 8.4, 2.6, 'tail', 2, -.5)
    ink.ribbon([xf((1.6, 3.4, 40)), xf((1, 4.6, 31)), xf((-1.6, 6, 21)), xf((-6, 7, 13)), xf((-12, 7.4, 9.4))], 3.2, 1.2, 'tail', 3, -.9, False)
    f0 = xf((-25 - sw, 3, 16))
    ink.plate([f0 + V(1, 0, -2), f0 + V(-5, 2, 9), f0 + V(-1.5, 2, 12), f0 + V(1, 2, 16), f0 + V(4, 2, 11), f0 + V(7, 2, 8)], 'extra', 2)
    # fin ears and a horned helm
    H, hd = head['H'], head['hd']
    for sx in (-1, 1):
        ink.poly([H(sx * 9.6, 2), H(sx * 17, 6), H(sx * 15.4, -1), H(sx * 17.4, -5), H(sx * 9.4, -4)], color['extra'][2], hd - 6.2)
        ink.poly([H(sx * 11, 1), H(sx * 15.6, 3.6), H(sx * 14.6, -2), H(sx * 10.8, -3)], color['extra'][3], hd - 6.3, False)
    helm = [(-11.4, 4), (-12.2, 9), (-9.4, 15), (-3, 18.6), (3, 18.6), (9.4, 15), (12.2, 9), (11.4, 4), (7.5, 5.4), (0, 6.4), (-7.5, 5.4)]
    ink.poly([H(*q) for q in helm], color['metal'][1], hd - 6.6)
    ink.poly([H(*q) for q in [(-9.4, 13), (-3, 17), (3, 17), (9.4, 13), (8.6, 10.4), (0, 14.4), (-8.6, 10.4)]], color['metal'][2], hd - 6.7, False)
    ink.poly([H(*q) for q in [(-1.7, 6.2), (1.7, 6.2), (1.7, 0), (-1.7, 0)]], color['metal'][2], hd - 6.7)
    for sx in (-1, 1):
        ink.poly([H(sx * 10.6, 12), H(sx * 16, 15), H(sx * 19.5, 22), H(sx * 12, 17.6)], color['gold'][2], hd - 6.8)
    # spear with a teal banner in the left hand
    h = joints['L']['hand']
    base_, tip = h + V(0, 0, -12), h + V(.5, .5, 42)
    ink.bone(base_, tip, 1.2, 1.2, 'wood', -.5)
    ink.bone(tip, tip + V(0, 0, 8), 2.2, .3, 'metal', -.7, 3)
    ink.plate([tip + V(0, 0, -4), tip + V(0, 0, -12), tip + V(-9 + sw, 1, -10), tip + V(-8 + sw, 1, -5)], 'extra', 2)
    ink.bone(h - R @ V(0, 0, .6), h + R @ V(0, 0, 2.2), 2.4, 2.0, 'skin', -1.4)


DESIGNS = {
    'smith': dict(fn=smith, female=False, px=ADULT_PX, head=1.0, coat='#b96e45', skin='#dca480', hair='#694737', pants='#4a3f5c',
                  extra='#7fb8d0', facing=('S', 'SE', 'S'), label='smith', old='smith',
                  pose=lambda clip, k, p: dict(handR=(14, 6, 46)) if clip != 'walk' else {}),
    'child': dict(fn=child, female=True, lashes=1.0, px=ADULT_PX * .68, head=1.28, coat='#dc8a79', skin='#e9bda1', hair='#ab6250', pants='#6a4a6a',
                  extra='#7e9fe0', trim='#f2d27a', facing=('S', 'SE', 'S'), label='child', old='child',
                  pose=lambda clip, k, p: dict(handR=(15, 8, 54 + (2 * math.sin(k / 6 * math.tau) if clip != 'walk' else 0))) if clip != 'walk' else {}),
    'namar': dict(fn=namar, female=False, px=ADULT_PX, head=1.0, coat='#4d7f93', skin='#cdbfea', hair='#ebdbbd', tail='#ecb395', extra='#3fa6b0',
                  facing=('S', 'S', 'S'), label='Captain Namar Deepwatch', old='special_nacre_warden',
                  pose=lambda clip, k, p: dict(handL=(-13, 7, 50), footL=(-3, 0, 4), footR=(3, 0, 4)) if clip == 'idle' else
                  ({'twist': 0, 'lean': 4, 'footL': (-3, 0, 4), 'footR': (3, 0, 4)} if clip == 'walk' else {'footL': (-3, 0, 4), 'footR': (3, 0, 4)})),
}


def render(name, clip, k):
    d = DESIGNS[name]
    set_frame(d['px'], d['female'])
    m = mats(d)
    palette, color = cc.palette_of(m)
    facing = d['facing'][[c for c, _ in CLIPS].index(clip)]
    psi = rig.psi_for(facing)
    p = pose(clip, k, d)
    R, xf, joints = cc.skeleton(p)
    ink = cc.Ink(psi, color)
    head = cc.head_frame(ink, xf, psi, p, turn=.6)
    if d['head'] != 1.0:        # the billboard head scales about its own centre (children: a bigger head on the same rig)
        hc = head['H'](0, 0)
        old = head['H']
        head['H'] = lambda x, y, old=old, hc=hc, s=d['head']: hc + (old(x, y) - hc) * s
    d['fn'](ink, xf, joints, R, head, p, color)
    # head, face and hair last, as the players draw them: nearer than the helm/collar, so they cover it
    cc.face(ink, head, p, lashes=d.get('lashes', .75))
    if p.get('mouth'):
        H, hd = head['H'], head['hd']
        nx = head['side'] * 5
        ink.poly([H(nx - 1.8, -6.6), H(nx + 1.8, -6.6), H(nx + 1.2, -9.6), H(nx - 1.2, -9.6)], color['mouth'][0], hd - 5.85, False)
    if name != 'namar':
        hair_cap(ink, head, color, head['front'])
    idx, z = ink.resolve()
    pal = np.array([tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,) if len(c) == 7 else (0, 0, 0, 0) for c in palette], np.uint8)
    pal[0] = (0, 0, 0, 0)
    return Image.fromarray(pal[idx], 'RGBA'), idx


def clipped(idx):
    return bool((idx[0] > 0).any() or (idx[-1] > 0).any() or (idx[:, 0] > 0).any() or (idx[:, -1] > 0).any())


def height(img):
    a = np.array(img)[..., 3] > 0
    ys = np.where(a.any(1))[0]
    return int(ys.min()), int(ys.max())


def sheet(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    assets = ROOT / 'client/assets'
    bg = (34, 48, 64, 255)
    S = 3
    rows = []
    for name in DESIGNS:
        d = DESIGNS[name]
        frames = {c: [render(name, c, k) for k in range(n)] for c, n in CLIPS}
        for c, fl in frames.items():
            for k, (img, idx) in enumerate(fl):
                if clipped(idx):
                    print('CLIPPED', name, c, k)
        old = Image.open(assets / f'npc_{d["old"]}.png').convert('RGBA')
        rows.append((name, frames, old))
        top, bot = height(frames['idle'][0][0])
        print(name, 'idle height', bot - top + 1, 'top', top, 'bottom', bot)
    # player reference: the mage body layer, front facing, drawn at 1.3 (players) against 1.4 (NPC atlas scale)
    mage = Image.open(assets / 'mage_body.png').convert('RGBA').crop((0, 0, 160, 160))
    W = 96 * 6 + 160
    img = Image.new('RGBA', (W * S // 1 + 40, (96 * 2 + 30) * len(rows) * S // 1), bg)
    # simple layout: per design one row: old idle f0 | new idle(0..5) | player ref
    cell = 96 * S
    sheet_img = Image.new('RGBA', (cell * 9 + 20, (cell + 24) * len(rows) + 10), bg)
    dr = ImageDraw.Draw(sheet_img)
    for r, (name, frames, old) in enumerate(rows):
        y0 = r * (cell + 24) + 10
        dr.text((6, y0 - 8), f'{DESIGNS[name]["label"]}: old | new idle, walk, talk | player (mage body, same scale)', fill='white')
        sheet_img.alpha_composite(old.crop((0, 0, 96, 96)).resize((cell, cell), Image.NEAREST), (0, y0 + 6))
        picks = [frames['idle'][0][0], frames['idle'][3][0], frames['walk'][1][0], frames['walk'][5][0], frames['talk'][1][0], frames['talk'][3][0]]
        for i, f in enumerate(picks):
            sheet_img.alpha_composite(f.resize((cell, cell), Image.NEAREST), ((i + 1) * cell, y0 + 6))
        # player drawn at its in-game ratio to NPC: 1.3 / 1.4 of the NPC atlas pixel
        ref = mage.resize((round(160 * 1.3 / 1.4 * S), round(160 * 1.3 / 1.4 * S)), Image.NEAREST)
        sheet_img.alpha_composite(ref, (7 * cell, y0 + 6 + cell - round(119 * 1.3 / 1.4 * S) - round((96 - 90) * S)))
    sheet_img.save(out / 'npcp-sample-sheet.png')
    # full clip strips per design
    for name, frames, old in rows:
        strip = Image.new('RGBA', (96 * 8 * 2, 96 * 3 * 2), bg)
        for ri, (c, n) in enumerate(CLIPS):
            for k in range(n):
                strip.alpha_composite(frames[c][k][0].resize((192, 192), Image.NEAREST), (k * 192, ri * 192))
        strip.save(out / f'npcp-{name}-clips.png')
    print('wrote', out)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'sheet':
        sheet(sys.argv[2])
    else:
        print(__doc__)
