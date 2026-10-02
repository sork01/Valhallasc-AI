#!/usr/bin/env python3
"""Priest: the Assassin's 2D anime cel style on the same 3D joint rig, dressed as a healer.

usage: make_priest_sprites.py preview [clip|all] [directory]   contact sheets (scratch), rows = facings
       make_priest_sprites.py build [--replace]                 render every frame, create the editable PixelFlow sprites priest_<clip>_<facing>_<pilgrim|dawn|arms|generic|trinkets>
       make_priest_sprites.py export [--local]                  PixelFlow (edits kept) -> client/assets/priest_*.png + priest_sprites.txt
       add --female to any command for the woman's body (priest_f_*, scripts/priest_f_raw/)

Seventeen independent layers, never baked together: the body, five equipment slots in two sets (armor, shoulders, gloves,
head, weapon: pilgrim/dawn, mace/sunmace) and the six class-independent pieces of generic_gear.py (Ironhide Helm and
Pauldrons, Duelist Gloves, Wayfarer Pants, Moonstone Necklace, Amber Ring). Pilgrim: a cream hood, a rope-and-crimson mantle,
wrapped mitts. Dawn: a gold sunburst diadem, sunray pauldrons, white-and-gold gloves. 160x160 frames, feet at (80,119), eight
facings, the same clips and frame counts as the Assassin (idle 6, walk 8, attack 8, hurt 4, die 8), so MageSprite composites
it unchanged. The rig (ik2, rotations, facing formula) comes from the original project's tools/make_warrior_sprites.py,
imported read-only from ../Valhalla/tools (set VALHALLA_TOOLS to move it). Frames are cached as scripts/priest_raw/*.npz
(gitignored). The pipeline (cache, preview, PixelFlow build, atlas export) is cel_common.Sheet, as for the other classes.
build refuses existing names; build --replace DISCARDS PRIEST HAND EDITS. export reads the sprites back (colour edits survive;
depth comes from the cache; added pixels take the nearest original depth). export --local skips PixelFlow.
"""
import math
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'client' / 'assets'
sys.path.insert(0, os.environ.get('VALHALLA_TOOLS', str(ROOT.parent / 'Valhalla' / 'tools')))
import make_warrior_sprites as rig  # noqa: E402
import cel_common as cc  # noqa: E402  (the `--female` switch, the torso outline and the Sheet pipeline)
import generic_gear as gg  # noqa: E402

V, unit = rig.V, rig.unit
FW = FH = 160
AX, AY, SS, PX = 80, 119, 2, 1.03
DIRS = rig.DIRS
SLOTS = {'armor': ('pilgrim', 'dawn'), 'shoulders': ('pilgrim', 'dawn', 'ironhide'), 'gloves': ('pilgrim', 'dawn', 'duelist'),
         'head': ('pilgrim', 'dawn', 'ironhide'), 'weapon': ('mace', 'sunmace'),
         'pants': ('wayfarer',), 'necklace': ('moonstone',), 'accessory': ('amber',)}
PARTS = ['body'] + [f'{slot}_{v}' for slot in cc.SLOT_ORDER for v in SLOTS.get(slot, ())]
MATS = {
    'skin': ['#92595c', '#ce9182', '#f0bfac', '#ffe0ce'],
    'hair': ['#8a6a3a', '#c9a45c', '#ecd290', '#fff4c8'],      # long pale-gold hair (the client recolours by ramp)
    'brow': ['#6a4c28', '#7e5e34', '#a98650', '#c0985a'],
    'cloth': ['#4a4048', '#76686f', '#a99a9c', '#d8c9c0'],
    'pants': ['#2a2a40', '#43476a', '#68729a', '#97a2c4'],
    'robe': ['#8c7a6e', '#c4b09c', '#ebdcc2', '#fff8e6'],       # warm ivory robe, parchment in shadow
    'dawn': ['#7f90ae', '#bccbe2', '#eef3fb', '#fdfeff'],      # cool white vestments, blue in shadow
    'gold': ['#6e4a12', '#b0801f', '#e8b840', '#fff0a0'],
    'stole': ['#5a1424', '#8f2438', '#c8465a', '#f28a94'],     # crimson tabard and tassel
    'leather': ['#2a2030', '#463a50', '#6a5a70', '#98889e'],
    'wood': ['#3a2420', '#6e4336', '#a77a56', '#d6ae82'],
    'silver': ['#3a516d', '#7791b0', '#bdcfe5', '#f2f5ff'],
    'glow': ['#d79a1a', '#ffc94a', '#ffe99a', '#fffbe0'],
    'iris': ['#2a5a8c', '#4a8cc4', '#8cc8f0', '#d8f2ff'],
    'white': ['#c0aec4', '#ded2e2', '#f6eef1', '#fffbf6'],
    'mouth': ['#5c2d45', '#86506a', '#c88493', '#e9a4ab'],
    **gg.GEAR_MATS,      # appended last, so every existing palette index keeps its value
}
PALETTE, COLOR = cc.palette_of(MATS)
DEFAULT = dict(root=(0, 0, 0), lean=1, twist=0, roll=0, sway=0, eyes='open', light=1.0,
               handL=(-9, 12, 58), handR=(12, 7, 46),
               footL=(-5, 0, 4), footR=(5, 0, 4),
               mace=(0, .06, 1), ground=False, dropped=False)
HIP, SHOULDER = 37, 66


def idle(k):
    # Upright and calm: the mace held like a sceptre, the free palm raised with a small holy light that pulses.
    a = k / 6 * math.tau
    return dict(root=(0, 0, -.3 * math.sin(a)), sway=math.sin(a), light=.85 + .3 * math.sin(a),
                handL=(-9, 12, 58 + .8 * math.sin(a)), eyes='closed' if k == 4 else 'open')


def walk(k):
    q = k / 8
    a = q * math.tau
    def foot(s, t):
        t %= 1
        return (s * 4, 8 - t * 32 if t < .5 else -8 + (t - .5) * 32,
                4 + (5 * math.sin((t - .5) * math.tau) if t >= .5 else 0))
    return dict(lean=5, roll=1.5 * math.sin(a), twist=3 * math.sin(a),
                root=(0, 0, -.5 * math.cos(a * 2)), sway=3.5 * math.sin(a), light=1 + .2 * math.sin(a * 2),
                handL=(-10, 10 - math.sin(a) * 2, 56), handR=(12, 7 + math.sin(a) * 2, 46),
                mace=(0, .08 + .08 * math.sin(a), 1),
                footL=foot(-1, q), footR=foot(1, q + .5))


def attack(k):
    # The light gathers on the free hand while the mace goes up, then the mace comes down and the light is thrown forward.
    lean = [2, -4, -8, 6, 18, 15, 8, 3][k]
    twist = [-2, -14, -24, -4, 20, 24, 10, 0][k]
    right = [(12, 7, 46), (15, -2, 62), (16, -8, 74), (12, 12, 68), (9, 24, 52), (9, 22, 42), (11, 13, 44), (12, 7, 46)][k]
    mace = [(0, .06, 1), (.1, -.3, 1), (.1, -.8, .8), (.05, .5, .85), (0, 1, -.1), (0, .85, -.55), (.1, .5, .5), (0, .06, 1)][k]
    left = [(-9, 12, 58), (-10, 13, 64), (-9, 15, 70), (-7, 20, 66), (-6, 26, 58), (-8, 20, 54), (-9, 14, 56), (-9, 12, 58)][k]
    light = [1, 1.5, 2, 1.3, .6, 0, 0, .6][k]
    f = [0, -.3, -.5, .5, 1, .65, .25, 0][k]
    return dict(lean=lean, twist=twist, root=(0, max(0, f) * 2, -.6), light=light,
                handL=left, handR=right, mace=mace, sway=-3 * f,
                footL=(-6, 4 * max(0, f), 4), footR=(6, -5 * max(0, f), 4))


def hurt(k):
    f = [.25, 1, .4, 0][k]
    return dict(lean=-12 * f, root=(0, -2 * f, 0), twist=8 * f, light=0 if k in (1, 2) else .5,
                handL=(-15, 5, 55), handR=(15, 5, 52), eyes='closed' if k < 3 else 'open', sway=-2 * f)


def die(k):
    return dict(lean=[-5, -23, -43, -66, -85, -90, -90, -90][k],
                root=(0, 8 if k >= 3 else 0, 0), eyes='closed', light=0,
                handL=(-17, 1, 50), handR=(17, 1, 49),
                footL=(-5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                footR=(5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                ground=k >= 3, dropped=k >= 2)


CLIPS = {'idle': (6, 6, idle), 'walk': (12, 8, walk), 'attack': (20, 8, attack),
         'hurt': (10, 4, hurt), 'die': (8, 8, die)}
GEAR = {
    'armor': {'none': {'name': 'Simple cloth', 'defense': 0},
              'pilgrim': {'name': 'Pilgrim robes', 'defense': 3}, 'dawn': {'name': 'Dawnweave vestments', 'defense': 5}},
    'shoulders': {'none': {'name': 'Bare shoulders', 'defense': 0},
                  'pilgrim': {'name': "Pilgrim's Mantle", 'defense': 1}, 'dawn': {'name': 'Sunray Pauldrons', 'defense': 2}},
    'gloves': {'none': {'name': 'Bare hands', 'defense': 0},
               'pilgrim': {'name': "Pilgrim's Mitts", 'defense': 1}, 'dawn': {'name': 'Dawnweave Gloves', 'defense': 2}},
    'head': {'none': {'name': 'Bare head', 'defense': 0},
             'pilgrim': {'name': "Pilgrim's Hood", 'defense': 1}, 'dawn': {'name': 'Sunburst Diadem', 'defense': 2}},
    'weapon': {'none': {'name': 'Empty hands', 'attack': 0},
               'mace': {'name': 'Oak mace', 'attack': 4}, 'sunmace': {'name': 'Sunbreaker mace', 'attack': 8}},
}


class Ink:
    """Flat cel polygons with a depth gradient along projected limbs (the Assassin's renderer)."""
    def __init__(self, psi):
        self.turn = rig.rotz(psi)
        self.color = COLOR
        self.index = np.zeros((FH * SS, FW * SS), np.uint8)
        self.z = np.full(self.index.shape, np.inf, np.float32)

    def project(self, point):
        x, y, z = self.turn @ point
        return V(AX + x * PX, AY - (y * .5 + z * math.sqrt(3) / 2) * PX), y * math.sqrt(3) / 2 - z * .5

    def poly(self, points, color, depth, outline=True, gradient=None):
        p = np.array(points, float)
        x0 = max(0, int(np.floor(p[:, 0].min() - 1.5)) * SS)
        y0 = max(0, int(np.floor(p[:, 1].min() - 1.5)) * SS)
        x1 = min(FW * SS, int(np.ceil(p[:, 0].max() + 2)) * SS)
        y1 = min(FH * SS, int(np.ceil(p[:, 1].max() + 2)) * SS)
        if x0 >= x1 or y0 >= y1:
            return
        mask = Image.new('L', (x1 - x0, y1 - y0))
        d = ImageDraw.Draw(mask)
        q = [(x * SS - x0, y * SS - y0) for x, y in p]
        d.polygon(q, fill=int(color))
        if outline:
            d.line(q + q[:1], fill=1, width=SS, joint='curve')
        idx = np.asarray(mask)
        if gradient is None:
            dep = np.full(idx.shape, depth, np.float32)
        else:
            a, b, za, zb = gradient
            yy, xx = np.mgrid[y0:y1, x0:x1] / SS
            dv = b - a
            t = np.clip(((xx - a[0]) * dv[0] + (yy - a[1]) * dv[1]) / max(float(dv @ dv), .01), 0, 1)
            dep = za + (zb - za) * t + depth
        cur = self.z[y0:y1, x0:x1]
        take = (idx > 0) & (dep <= cur + .001)
        cur[take] = dep[take]
        self.index[y0:y1, x0:x1][take] = idx[take]

    def plate(self, points, mat, tone=2, detail=False, push=0):
        proj = [self.project(p) for p in points]
        xy = [p[0] for p in proj]
        self.poly(xy, COLOR[mat][tone], np.mean([p[1] for p in proj]) - .01 + push, not detail)

    def bone(self, a, b, r1, r2, mat, zpush=0, tone=2):
        pa, za = self.project(a)
        pb, zb = self.project(b)
        direction = unit(pb - pa)
        side = V(-direction[1], direction[0])
        r1 *= PX
        r2 *= PX
        points = [pa - direction * r1 * .5 - side * r1, pa - direction * r1 * .65,
                  pa - direction * r1 * .5 + side * r1,
                  pb + side * r2, pb + direction * r2 * .45, pb - side * r2]
        grad = (pa, pb, za, zb)
        self.poly(points, COLOR[mat][tone], -max(r1, r2) * .7 + zpush, gradient=grad)
        self.poly([pa + side * r1 * .1, pa + side * r1 * .72,
                   pb + side * r2 * .72, pb + side * r2 * .1], COLOR[mat][tone - 1],
                  -max(r1, r2) * .7 + zpush - .025, False, grad)

    def resolve(self, flash=False):
        idx = self.index[SS // 2::SS, SS // 2::SS].copy()
        z = self.z[SS // 2::SS, SS // 2::SS].copy()
        if flash:
            idx[(idx > 0) & (idx != 1)] = 2
        return idx, z


def priest_pieces(inks, R, joints, H, hd, front, side):
    """Head, shoulder and glove pieces of both sets. Pilgrim: cream cloth, crimson and rope. Dawn: gold and white."""
    backview = front < -.4
    ink = inks['head_pilgrim']
    # A cloth hood round the face (closed over the back of the head from behind) with a gold-trimmed opening and a crimson cord.
    outer = [(-12.8, -9), (-13.6, 6), (-10.6, 16.4), (-4, 22), (0, 23.2), (4, 22), (10.6, 16.4), (13.6, 6), (12.8, -9)]
    inner = [(9.9, -6), (9.7, 4.6), (6.9, 9.8), (0, 11), (-6.9, 9.8), (-9.7, 4.6), (-9.9, -6)]
    back = [(-12.4, -3), (-13.6, 6), (-10.6, 16.4), (-4, 22), (0, 23.2), (4, 22), (10.6, 16.4), (13.6, 6), (12.4, -3), (9, -11.5), (0, -13.4), (-9, -11.5)]
    ink.poly([H(*q) for q in (back if backview else outer + inner)], COLOR['robe'][2], hd - (11 if backview else 7))
    ink.poly([H(*q) for q in [(13.6, 6), (10.6, 16.4), (4, 22), (0, 23.2), (2, 17), (7.5, 12.6), (11.4, 4), (12.4, -3 if backview else -9)]], COLOR['robe'][1], hd - 7.05 - (4 if backview else 0), False)
    ink.poly([H(*q) for q in [(-13.6, 6), (-10.6, 16.4), (-4, 22), (0, 23.2), (-2, 19), (-8, 14), (-11, 6)]], COLOR['robe'][3], hd - 7.04 - (4 if backview else 0), False)
    if not backview:
        ink.poly([H(*q) for q in [(-10.3, -6), (-10.2, 4.6), (-7.2, 10.2), (0, 11.5), (7.2, 10.2), (10.2, 4.6), (10.3, -6),
                                  (9.7, -6), (9.7, 4.6), (6.9, 9.8), (0, 11), (-6.9, 9.8), (-9.7, 4.6), (-9.7, -6)]], COLOR['gold'][2], hd - 7.3, False)
        for sx in (-1, 1):
            ink.poly([H(sx * 11.6, -6), H(sx * 12.8, -9), H(sx * 13.4, -14), H(sx * 12, -15.4), H(sx * 10.6, -13)], COLOR['stole'][2 if sx > 0 else 1], hd - 7.4)
    ink = inks['head_dawn']
    # A gold diadem above the circlet: seven pointed rays of rising height round a sun gem.
    xs = [-10.4, -7, -3.5, 0, 3.5, 7, 10.4]
    tops = [11.8, 15.6, 18.2, 21, 18.2, 15.6, 11.8]
    ink.poly([H(*q) for q in [(-11.2, 8.2), (-11.2, 11.6)] + [pt for x, t in zip(xs, tops) for pt in ((x - 1.7, 11.8), (x, t), (x + 1.7, 11.8))] + [(11.2, 11.6), (11.2, 8.2), (0, 10.4)]], COLOR['gold'][2], hd - 7)
    ink.poly([H(*q) for q in [(-11.2, 8.2), (-11.2, 11.6), (-8.7, 11.8), (-8.7, 9)]] + [], COLOR['gold'][3], hd - 7.05, False)
    ink.poly([H(*q) for q in [(11.2, 8.2), (11.2, 11.6), (8.5, 11.8), (6, 10.2), (0, 10.4)]], COLOR['gold'][1], hd - 7.05, False)
    if not backview:
        gx = side * 5
        ink.poly([H(gx, 18.4), H(gx + 2.8, 14.6), H(gx, 10.9), H(gx - 2.8, 14.6)], COLOR['glow'][1], hd - 7.4)
        ink.poly([H(gx, 17), H(gx + 1.5, 14.6), H(gx, 12.2), H(gx - 1.5, 14.6)], COLOR['glow'][3], hd - 7.45, False)
    for sx in (-1, 1):      # two white ribbons tipped in crimson fall behind the ears
        ink.poly([H(sx * 10.6, 9.4), H(sx * 12.2, 9.4), H(sx * 14.4, -6), H(sx * 13.8, -12), H(sx * 11.4, -6)], COLOR['dawn'][2 if sx > 0 else 1], hd - 7.1)
        ink.poly([H(sx * 14.1, -8), H(sx * 13.8, -12), H(sx * 12.6, -13.6), H(sx * 12.8, -8.6)], COLOR['stole'][2], hd - 7.15, False)
    for tier in ('pilgrim', 'dawn'):
        ink = inks['shoulders_' + tier]
        for key in 'LR':
            j = joints[key]
            sh = j['shoulder']
            sx = -1 if key == 'L' else 1
            out, upv = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            if tier == 'pilgrim':
                # A cream mantle with a crimson hem, held by a gold clasp at the collarbone.
                ink.bone(sh - out * .6 + upv * 2.8, sh + out * 5.6 - upv * 1.6, 5.2, 4.7, 'robe', -1.0, 2)
                ink.bone(sh + out * 2.8 + upv * .6, sh + out * 7.6 - upv * 3.8, 4.5, 3.8, 'robe', -1.15, 1)
                ink.bone(sh + out * 3.4 - upv * 3.2, sh + out * 7.4 - upv * 5.2, 1.5, 1.3, 'stole', -1.3, 2)
                ink.bone(sh - out * .2 + upv * 4.6, sh + out * 3.6 + upv * 2.4, 1.1, 1.0, 'gold', -1.5, 3)
            else:
                # A gold dome with a fan of sun rays and a white feathered edge.
                ink.bone(sh - out * .6 + upv * 2.6, sh + out * 5.8 - upv * 1.4, 5.0, 4.5, 'gold', -1.0, 2)
                ink.bone(sh + out * 2.6 + upv * .6, sh + out * 7.4 - upv * 3.8, 4.2, 3.6, 'dawn', -1.15, 2)
                for k_, (a_, b_, h_) in enumerate(((.2, 1.6, 8.6), (2.2, 3.4, 10.4), (4.2, 5.2, 8.2))):
                    ink.plate([sh + out * a_ + upv * 3.4, sh + out * (a_ + b_) / 2 + upv * (3.4 + h_), sh + out * (b_ + 1.4) + upv * 3.6], 'glow', 2 + (k_ == 1))
                ink.bone(sh + out * 1.4 + upv * 4.2, sh + out * 4.2 + upv * 3, 1.0, 1.0, 'gold', -1.5, 3)
    for tier in ('pilgrim', 'dawn'):
        ink = inks['gloves_' + tier]
        for key in 'LR':
            j = joints[key]
            el, hand = j['elbow'], j['hand']
            if tier == 'pilgrim':      # cream mitts bound at the wrist with leather
                ink.bone(hand + (el - hand) * .46, hand + (el - hand) * .06, 2.8, 2.5, 'robe', -.8)
                ink.bone(hand + (el - hand) * .26, hand + (el - hand) * .18, 3.2, 3.2, 'leather', -.95, 2)
                ink.bone(hand + (el - hand) * .5, hand + (el - hand) * .42, 3.1, 3.1, 'leather', -.95, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.5, 2.2, 'robe', -.9)
            else:                      # white gloves, a gold flared cuff and a sun gem on the back of the hand
                ink.bone(hand + (el - hand) * .5, hand + (el - hand) * .06, 2.8, 2.5, 'dawn', -.8)
                ink.bone(hand + (el - hand) * .54, hand + (el - hand) * .36, 3.7, 3.2, 'gold', -.95, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.5, 2.2, 'dawn', -.9)
                ink.bone(hand + R @ V(0, 1.4, .4), hand + R @ V(0, 1.7, .8), 1.1, 1.1, 'glow', -1.2, 3)


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R = rig.rotz(rig.rad(p['twist'])) @ rig.roty(rig.rad(p['roll'])) @ rig.rotx(rig.rad(-p['lean']))
    pivot, shift = V(0, 0, HIP), V(*p['root'])
    xf = lambda a: pivot + R @ (V(*a) - pivot) + shift
    joints = {}
    for sx, key in ((-1, 'L'), (1, 'R')):
        s = V(sx * cc.SHOULDER_X, 0, SHOULDER)
        elbow, hand = rig.ik2(s, V(*p['hand' + key]), 13.5, 13.5, unit(V(sx * .3, -.45, -1)))
        hip = xf((sx * cc.HIP_X, 0, HIP))
        knee, ankle = rig.ik2(hip, V(*p['foot' + key]), 17, 17, unit(V(sx * .1, 1, .1)))
        joints[key] = {'shoulder': xf(s), 'elbow': xf(elbow), 'hand': xf(hand),
                       'hip': hip, 'knee': knee, 'ankle': ankle}
    if p['ground']:
        low = min([xf((0, 0, 87))[2] - 11, *[j['ankle'][2] - 4 for j in joints.values()]])
        dz = -low
        shift += V(0, 0, dz)
        for joint in joints.values():
            for key in joint:
                joint[key] += V(0, 0, dz)
    inks = {part: Ink(psi) for part in PARTS}
    body = inks['body']

    def torso(ink, mat, halfwidth, y, bottom=38, top=67, push=0):
        for points, tone in cc.torso_panels(halfwidth, y, bottom, top):
            ink.plate([xf(q) for q in points], mat, tone, push=push)

    torso(body, 'cloth', 7.8, 3.5)
    lw = .92 if cc.FEMALE else 1.      # slimmer limbs
    body.bone(xf((0, 0, 68)), xf((0, 0, 77)), 2.2 * lw, 2.1 * lw, 'skin')
    for sx, key in ((-1, 'L'), (1, 'R')):
        j = joints[key]
        body.bone(j['hip'], j['knee'], 3.3 * lw, 2.9 * lw, 'pants')
        body.bone(j['knee'], j['ankle'], 2.7 * lw, 1.9 * lw, 'pants')
        body.bone(j['ankle'] + V(0, -1, -1.5), j['ankle'] + V(0, 4, -2), 2 * lw, 2.1 * lw, 'skin')
        body.bone(j['shoulder'], j['elbow'], 2.6 * lw, 2.1 * lw, 'skin')
        body.bone(j['elbow'], j['hand'], 2 * lw, 1.6 * lw, 'skin')
        body.bone(j['hand'] - R @ V(0, 0, 1), j['hand'] + R @ V(0, 0, 1.8), 2.2 * lw, 1.8 * lw, 'skin', -.2)

    # The holy light in the free palm: a four-point star that pulses in idle and gathers before an attack.
    if p['light'] > .05:
        lc, ld = body.project(joints['L']['hand'] + V(0, 0, 6.5))
        for r, inner, tone, outline, push in ((4.6, .34, 1, True, 6), (3.4, .38, 2, False, 6.2), (1.7, .55, 3, False, 6.4)):
            r *= p['light']
            star = [lc + V(math.sin(i * math.pi / 4), math.cos(i * math.pi / 4)) * r * (1 if i % 2 == 0 else inner * 1.6) for i in range(8)]
            body.poly(star, COLOR['glow'][tone], ld - push, outline)

    # A soft round face with big sky-blue eyes, a centre-parted fringe, long pale-gold hair and a gold sun circlet.
    hc, hd = body.project(xf((0, 0, 87)))
    up = unit(body.project(xf((0, 0, 96)))[0] - hc)
    right = V(-up[1], up[0])
    H = lambda x, y: hc + right * x + up * y
    front = -math.cos(psi + rig.rad(p['twist']))
    side = -math.sin(psi + rig.rad(p['twist']))
    skin_shape = [(-8.4, 7), (-9.8, 0), (-8.6, -6), (-4.8, -10.2), (0, -11), (4.8, -10.2), (8.6, -6), (9.8, 0), (8.4, 7), (0, 10)]
    if cc.FEMALE:      # a slightly narrower jaw and a softer chin
        skin_shape = [(-8.2, 7), (-9.3, 0), (-8, -6), (-4, -10), (0, -11.6), (4, -10), (8, -6), (9.3, 0), (8.2, 7), (0, 10)]
    body.poly([H(*q) for q in skin_shape], COLOR['skin'][2], hd - 4)
    body.poly([H(*q) for q in [(4.5, 6), (8.4, 6), (9.7, 0), (7.6, -6), (0, -10.8), (3.5, -4)]], COLOR['skin'][1], hd - 4.05, False)
    if front < -.4:
        body.poly([H(*q) for q in [(-10, 9), (-11.4, 0), (-10, -9), (-5, -13), (5, -13), (10, -9), (11.4, 0), (10, 9), (5, 14), (-5, 14)]], COLOR['hair'][2], hd - 5)
        body.poly([H(*q) for q in [(0, 1), (5, 4), (10, 4), (11.4, 0), (10, -9), (5, -13), (0, -12), (1, -5)]], COLOR['hair'][1], hd - 5.05, False)
        body.poly([H(*q) for q in [(-8, 11), (-3, 13.6), (4, 13.2), (7.5, 10.5), (2, 11.6), (-4, 11)]], COLOR['hair'][3], hd - 5.1, False)
        body.poly([H(*q) for q in [(-5, 3), (-2, 5), (-3, -6), (-6, -9)]], COLOR['hair'][3], hd - 5.12, False)
    else:
        for sx in (-1, 1):
            if abs(side) > .85 and sx * side < 0:
                continue
            ex = sx * 4.2 * max(.28, front) + side * 3.4
            ey = -2.6
            if p['eyes'] == 'closed':
                body.poly([H(ex - 2.3, ey + .7), H(ex, ey - .5), H(ex + 2.3, ey + .7), H(ex, ey + .1)], 1, hd - 5.8)
            else:
                body.poly([H(ex - 2, ey + 1.5), H(ex, ey + 2.2), H(ex + 2, ey + 1.5), H(ex + 2.2, ey - .5),
                           H(ex + 1, ey - 2), H(ex - 1, ey - 2), H(ex - 2.2, ey - .5)], COLOR['white'][2], hd - 5.3)
                body.poly([H(ex - 1.5, ey + 1.7), H(ex + 1.5, ey + 1.7), H(ex + 1.7, ey - 1.7), H(ex - 1.7, ey - 1.7)], COLOR['iris'][1], hd - 5.5, False)
                body.poly([H(ex - 1.5, ey - .3), H(ex + 1.5, ey - .3), H(ex + 1.5, ey - 1.7), H(ex - 1.5, ey - 1.7)], COLOR['iris'][2], hd - 5.52, False)
                body.poly([H(ex - .6, ey + .9), H(ex + .6, ey + .9), H(ex + .6, ey - .9), H(ex - .6, ey - .9)], 1, hd - 5.55, False)
                lid = 1. if cc.FEMALE else .72
                body.poly([H(ex - 2.4, ey + 1.1), H(ex, ey + 1.6 + .9 * lid), H(ex + 2.4, ey + 1.2), H(ex + 2.5, ey + .4), H(ex, ey + 1.6), H(ex - 2.3, ey + .3)], 1, hd - 5.6, False)
                body.poly([H(ex - 1.1, ey + 1.2), H(ex - .1, ey + 1.2), H(ex - .1, ey + .2), H(ex - 1.1, ey + .2)], COLOR['white'][3], hd - 5.7, False)
                body.poly([H(ex + .5, ey - .9), H(ex + 1.2, ey - .9), H(ex + 1.2, ey - 1.4), H(ex + .5, ey - 1.4)], COLOR['white'][3], hd - 5.7, False)
            if cc.FEMALE:
                body.poly([H(ex - 2, 2.4), H(ex, 3), H(ex + 2, 2.4), H(ex + 2, 2), H(ex, 2.6), H(ex - 2, 2)], COLOR['brow'][1], hd - 5.8, False)
            else:      # a heavier, straighter brow
                body.poly([H(ex - 2.6, 2.2), H(ex, 3.6), H(ex + 2.6, 2.8), H(ex + 2.6, 1.6), H(ex, 2.4), H(ex - 2.6, 1.0)], COLOR['brow'][0], hd - 5.8, False)
            body.poly([H(ex - 1.8, -4.5), H(ex + 1.8, -4.5), H(ex + 1.8, -5.5), H(ex - 1.8, -5.5)], COLOR['mouth'][3], hd - 5.3, False)
        nx = side * 5
        body.poly([H(nx - .3, -4.4), H(nx + .4, -5.3), H(nx + 1, -4.6)], COLOR['skin'][1], hd - 5.5, False)
        body.poly([H(nx - 1.2, -7.3), H(nx, -7.9), H(nx + 1.2, -7.3), H(nx, -7.1)], COLOR['mouth'][1], hd - 5.6, False)
        # Fringe parted in the middle, with long locks framing the cheeks.
        fringe = [(-10.8, -1), (-11.4, 7), (-8.8, 13), (0, 15.4), (8.8, 13), (11.4, 7), (10.8, -1), (9.2, 2.6), (6.6, 4.4),
                  (3.2, 6.4), (.4, 9.6), (-.8, 7.4), (-4, 4.8), (-7, 4), (-9.2, 1.8)]
        body.poly([H(*q) for q in fringe], COLOR['hair'][2], hd - 6)
        body.poly([H(*q) for q in [(1, 9.6), (3.2, 6.4), (6.6, 4.4), (9.2, 2.6), (10.8, -1), (11.4, 7), (8.8, 13), (4, 14.6)]], COLOR['hair'][1], hd - 6.05, False)
        body.poly([H(*q) for q in [(-8.4, 11), (-3, 13.8), (3, 13.9), (7, 12), (2, 12.2), (-3, 12)]], COLOR['hair'][3], hd - 6.1, False)
        for sx in (-1, 1):
            if abs(side) > .85 and sx * side < 0:
                continue
            if cc.FEMALE:
                body.poly([H(sx * q[0], q[1]) for q in [(11, 6), (12, -4), (11.4, -13), (8.4, -16), (8, -8), (8.6, 0), (9.6, 4)]], COLOR['hair'][2], hd - 6.2)
                body.poly([H(sx * q[0], q[1]) for q in [(11.6, 2), (12, -4), (11.4, -13), (10, -14), (10.4, -5)]], COLOR['hair'][1], hd - 6.25, False)
            else:      # sideburns
                body.poly([H(sx * q[0], q[1]) for q in [(10.6, 5), (11.4, -3.6), (9.6, -5.6), (9, 0)]], COLOR['hair'][2], hd - 6.2)
        if front >= -.4:      # a short pale-gold goatee
            body.poly([H(*q) for q in [(-2.8, -9), (2.8, -9), (1.6, -12.4), (0, -13.4), (-1.6, -12.4)]], COLOR['hair'][1], hd - 5.65, False)
    if front >= -.4:
        body.poly([H(*q) for q in [(-10.8, 5.6), (-6, 8.4), (0, 9.4), (6, 8.4), (10.8, 5.6), (10.8, 4.2), (6, 7), (0, 8), (-6, 7), (-10.8, 4.2)]], COLOR['gold'][2], hd - 6.4)
        gx = side * 7.5
        body.poly([H(gx, 11.2), H(gx + 2.1, 8.8), H(gx, 6.6), H(gx - 2.1, 8.8)], COLOR['glow'][2], hd - 6.5)
        body.poly([H(gx, 9.8), H(gx + .8, 8.8), H(gx, 7.8), H(gx - .8, 8.8)], COLOR['glow'][3], hd - 6.55, False)
    # Long hair falls behind the shoulders (seen from the back and sides) tied with a crimson ribbon.
    sw = p['sway']
    if cc.FEMALE:      # to the hips, with a wavy flared end
        body.plate([xf(q) for q in [(-7, -5.6, 83), (7, -5.6, 83), (9.6, -7, 66), (10.4 + sw, -8.6, 44), (8 + sw * 1.3, -9.8, 32), (4 + sw * 1.4, -9.2, 36),
                                   (.4 + sw * 1.5, -9.8, 30), (-3.6 + sw * 1.4, -9.2, 36), (-8.2 + sw * 1.3, -9.8, 31), (-9.4 + sw, -8.6, 44), (-9.6, -7, 66)]], 'hair', 1)
    else:      # a man: hair to the nape, no fall of hair down the back
        body.plate([xf(q) for q in [(-6.4, -5.6, 83), (6.4, -5.6, 83), (7.6, -7, 76), (4 + sw * .5, -8, 72), (-4 + sw * .5, -8, 72), (-7.6, -7, 76)]], 'hair', 1)
    if cc.FEMALE:
        body.plate([xf(q) for q in [(-5, -6.1, 80), (5, -6.1, 80), (6.6, -7.2, 64), (5 + sw, -8.2, 49), (1 + sw * 1.3, -8.4, 45),
                                   (-4 + sw, -8.2, 48), (-6.6, -7.2, 64)]], 'hair', 2)
        for sx in (-1, 1):
            body.plate([xf(q) for q in [(sx * 9.2, -5.4, 80), (sx * 9.8, -8.4, 70), (sx * 9, -8.8 + sw, 52), (sx * 9.4, -5.6, 58)]], 'hair', 2 if sx > 0 else 1, True)
    body.plate([xf(q) for q in [(-8.4, -6.6, 62), (8.4, -6.6, 62), (8.4, -6.7, 59.2), (-8.4, -6.7, 59.2)]], 'stole', 2)

    for key, mat in [('armor_pilgrim', 'robe'), ('armor_dawn', 'dawn')]:
        ink = inks[key]
        dawn = mat == 'dawn'
        torso(ink, mat, 8.6, 4.3, 34, 69, -1.5)
        # Long robe: a skirt that flares to a hem above the boots, swaying with the body.
        hem, wide, deep, sway = 15, 12, 8.4, p['sway'] * .8
        if p['ground']:
            wide, deep = 9.6, 6.6
        for sy in (-1, 1):
            xy = [(-8.2, sy * 4.5, 38), (8.2, sy * 4.5, 38), (wide + sway, sy * deep, hem), (-wide + sway, sy * deep, hem)]
            ink.plate([xf(q) for q in xy], mat, 3 if sy == 1 else 2, push=-3)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 8.2, -4.5, 38), (sx * 8.2, 4.5, 38),
                      (sx * wide + sway, deep, hem), (sx * wide + sway, -deep, hem)]], mat, 2, push=-3)
        # Gold hem band, front and back.
        for sy in (-1, 1):
            ink.plate([xf(q) for q in [(-wide + sway, sy * deep, hem + 3.2), (wide + sway, sy * deep, hem + 3.2),
                                      (wide + sway, sy * deep, hem), (-wide + sway, sy * deep, hem)]], 'gold', 2 if sy == 1 else 1, True, push=-3.6)
        # Belt cord.
        ink.plate([xf(q) for q in [(-8.6, 4.8, 42), (8.6, 4.8, 42), (8.4, 4.8, 39), (-8.4, 4.8, 39)]], 'leather', 2)
        ink.plate([xf(q) for q in [(-1.2, 5, 39), (1.2, 5, 39), (2, 5.3, 29), (-.4, 5.3, 28)]], 'gold', 2)
        # Wide bell sleeves with gold cuffs.
        for sx, name in ((-1, 'L'), (1, 'R')):
            j = joints[name]
            ink.bone(j['shoulder'], j['elbow'], 3.7, 3.3, mat, -.8)
            ink.bone(j['elbow'], j['hand'], 3.4, 4, mat, -.7)
            ink.bone(j['hand'] - (j['hand'] - j['elbow']) * .2, j['hand'], 3.8, 3.4, 'gold', -.9)
            ink.bone(j['knee'] + (j['ankle'] - j['knee']) * .25, j['ankle'], 3.1, 2.5, 'leather', -.8)
            ink.bone(j['ankle'] + V(0, -1, -1), j['ankle'] + V(0, 4.5, -2), 2.5, 2.5, 'leather', -.8)
        # Mantle over the shoulders, a standing fan collar behind the head, a crimson tabard front and back, a sun medallion.
        ink.plate([xf(q) for q in [(-9.5, 4.9, 71), (9.5, 4.9, 71), (11, 5.2, 60), (0, 5.5, 55), (-11, 5.2, 60)]], mat, 1)
        ink.plate([xf(q) for q in [(-9.5, -4.9, 71), (9.5, -4.9, 71), (11, -5.2, 60), (0, -5.5, 55), (-11, -5.2, 60)]], mat, 1)
        ink.plate([xf(q) for q in [(-8.6, -6.9, 70), (-13, -7, 86), (-6.5, -7.1, 91), (0, -7.2, 93), (6.5, -7.1, 91), (13, -7, 86), (8.6, -6.9, 70)]], mat, 2)
        ink.plate([xf(q) for q in [(-13, -7.1, 86), (-6.5, -7.2, 91), (0, -7.3, 93), (6.5, -7.2, 91), (13, -7.1, 86), (12.2, -7.1, 84.6), (6.4, -7.2, 89.6), (0, -7.3, 91.4), (-6.4, -7.2, 89.6), (-12.2, -7.1, 84.6)]], 'gold', 2, True)
        ink.plate([xf(q) for q in [(-4.2, 5.6, 75), (4.2, 5.6, 75), (3.2, 5.7, 70), (0, 5.9, 66), (-3.2, 5.7, 70)]], 'gold', 2)
        for sy, bulge in ((1, 1.2), (-1, 0)):
            tab = [(-3.8, sy * (5.7 + bulge * .2), 72), (3.8, sy * (5.7 + bulge * .2), 72), (4.6 + sway * .4, sy * (5.9 + bulge), 38),
                   (5.2 + sway * .6, sy * (deep + .4), hem - 3), (0 + sway * .6, sy * (deep + .5), hem - 6.5),
                   (-5.2 + sway * .6, sy * (deep + .4), hem - 3), (-4.6 + sway * .4, sy * (5.9 + bulge), 38)]
            ink.plate([xf(q) for q in tab], 'stole', 2 if sy == 1 else 1)
            for sx in (-1, 1):
                ink.plate([xf(q) for q in [(sx * 3.8, sy * 5.8, 72), (sx * 3.1, sy * 5.8, 72), (sx * 3.9 + sway * .4, sy * 6.8, 38), (sx * 4.6 + sway * .6, sy * (deep + .5), hem - 3)]], 'gold', 2, True)
        # Sun medallion on the chest: a gold disc with a white-gold core and four rays.
        for i in range(4):
            ang = i * math.pi / 2
            c, s_ = math.cos(ang), math.sin(ang)
            ink.plate([xf((-1.1 * s_ + 3.4 * c, 6.15, 62 + 1.1 * c + 3.4 * s_)), xf((1.1 * s_ + 3.4 * c, 6.15, 62 - 1.1 * c + 3.4 * s_)),
                       xf((5.6 * c, 6.15, 62 + 5.6 * s_))], 'gold', 3, True)
        ink.plate([xf((3.6 * math.cos(i / 8 * math.tau), 6.2, 62 + 3.6 * math.sin(i / 8 * math.tau))) for i in range(8)], 'gold', 2)
        ink.plate([xf((1.9 * math.cos(i / 8 * math.tau), 6.25, 62 + 1.9 * math.sin(i / 8 * math.tau))) for i in range(8)], 'glow', 3, True)
        if dawn:
            for sx in (-1, 1):
                j = joints['L' if sx < 0 else 'R']
                ink.bone(j['shoulder'], j['shoulder'] + R @ V(sx * 3, 0, -3), 3.4, 2.2, 'gold', -1.1)
            # A thin halo floating above the head.
            ring = lambda r, t: H(r * math.cos(t), 24 + r * .5 * math.sin(t))
            steps = 24
            for width, color, push in ((10.0, lambda a: 1, 0), (9.2, lambda a: COLOR['glow'][3 if math.sin(a) > 0 else 2], .1)):
                for i in range(steps):
                    a, b = i / steps * math.tau, (i + 1) / steps * math.tau
                    inner = 7.2 if width > 9.5 else 7.9
                    ink.poly([ring(width, a), ring(width, b), ring(inner, b), ring(inner, a)], color(a), hd - 7.5 - push, False)

    priest_pieces(inks, R, joints, H, hd, front, side)
    gg.draw(inks, R, xf, joints, dict(H=H, hd=hd, front=front, side=side))
    for key, sun in [('weapon_mace', False), ('weapon_sunmace', True)]:
        ink = inks[key]
        hand = joints['R']['hand']
        u = R @ unit(V(*p['mace']))
        across = R @ V(1, 0, 0)
        if p['dropped']:
            hand = V(20, -7, 3)
            u = unit(V(.6, 1, 0))
            across = unit(V(u[1], -u[0], 0))
        # The mace is gripped near its butt, so most of it stands out beyond the fist.
        butt = hand - u * 5
        neck = hand + u * (21 if sun else 19)
        ink.bone(butt, neck, 1.5, 1.5, 'gold' if sun else 'wood', -.1, 2)
        ink.bone(hand - u * 1.5, hand + u * 2.5, 1.7, 1.7, 'leather', -.12)
        c = neck + u * 4
        depth_dir = across
        rr = 5.0 if sun else 4.2
        # Flanged head: a faceted diamond with cross flanges.
        pts = []
        for i in range(8):
            t = i / 8 * math.tau
            pts.append(c + across * math.cos(t) * rr + u * math.sin(t) * rr * 1.2)
        ink.plate(pts, 'gold' if sun else 'silver', 2)
        ink.plate([c - across * rr * .8, c + u * rr * 1.1, c + across * rr * .8, c - u * rr * 1.1], 'glow' if sun else 'silver', 3, True)
        for sgn in (-1, 1):
            ink.plate([c + across * sgn * rr * .9 + u * 1.4, c + across * sgn * (rr + 2.2), c + across * sgn * rr * .9 - u * 1.4], 'gold' if sun else 'silver', 1)
        ink.plate([c + u * rr * 1.1 - across * 1, c + u * (rr + 2.8), c + u * rr * 1.1 + across * 1], 'gold' if sun else 'silver', 2)
        tail = V(0, 0, -9) + across * p['sway'] * .3
        ink.plate([neck + across * 1.3, neck - across * 1.3, neck + tail], 'stole', 2)
        ink.plate([neck + tail + across * .9, neck + tail - across * .9, neck + tail * 1.25], 'gold', 2)
        if sun:
            for t in (0, 1, 2, 3):
                ang = t * math.pi / 2 + math.pi / 4
                d = across * math.cos(ang) + u * math.sin(ang)
                n = across * -math.sin(ang) + u * math.cos(ang)
                ink.plate([c + d * rr * .9 + n * 1.3, c + d * (rr + 3.2), c + d * rr * .9 - n * 1.3], 'glow', 2)
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}



NAKED = {slot: 'none' for slot in SLOTS}
PILGRIM = {'armor': 'pilgrim', 'shoulders': 'pilgrim', 'gloves': 'pilgrim', 'head': 'pilgrim', 'weapon': 'mace'}
DAWN = {'armor': 'dawn', 'shoulders': 'dawn', 'gloves': 'dawn', 'head': 'dawn', 'weapon': 'sunmace'}
GENERIC = {'armor': 'pilgrim', 'shoulders': 'ironhide', 'gloves': 'duelist', 'head': 'ironhide', 'pants': 'wayfarer',
           'necklace': 'moonstone', 'accessory': 'amber', 'weapon': 'mace'}
SHEET = cc.Sheet(
    'priest', files='priest', pixel='priest_', mats=MATS, clips=CLIPS, slots=SLOTS, gear=GEAR, render=render_frame,
    revision=cc.revision_of([open(__file__).read(), open(gg.__file__).read()]),
    default_equip={'armor': 'pilgrim', 'shoulders': 'none', 'gloves': 'none', 'head': 'none', 'weapon': 'mace'},
    meta={'attack': {'duration': .4, 'impact': .2}, 'portrait': [57, 19, 46, 46]},
    combos=[('naked', NAKED), ('pilgrim', PILGRIM), ('dawn', DAWN), ('generic', GENERIC)])

if __name__ == '__main__':
    SHEET.cli()
