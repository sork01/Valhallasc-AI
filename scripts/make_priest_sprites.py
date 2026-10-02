#!/usr/bin/env python3
"""Priest: the Assassin's 2D anime cel style on the same 3D joint rig, dressed as a healer.

usage: make_priest_sprites.py preview [clip|all] [directory]   contact sheets (scratch), rows = facings
       make_priest_sprites.py build [--replace]                 render every frame, create the editable PixelFlow sprites priest_<clip>_<facing>
       make_priest_sprites.py export [--local]                  PixelFlow (edits kept) -> client/assets/priest_*.png + priest_sprites.txt

Five independent layers (body, two robes, two maces); equipment is never baked into the body. 160x160 frames,
feet at (80,119), eight facings, the same clips and frame counts as the Assassin (idle 6, walk 8, attack 8,
hurt 4, die 8), so MageSprite composites it unchanged. The rig (ik2, rotations, facing formula) comes from the
original project's tools/make_warrior_sprites.py, imported read-only from ../Valhalla/tools (set VALHALLA_TOOLS
to move it). Frames are cached as scripts/priest_raw/*.npz (gitignored, regenerated in a few minutes).
PixelFlow: one sprite per clip and facing (5 layers x 160x160 x 8 frames = the 1,048,576-cell limit), body visible,
equipment layers hidden. build refuses existing names; build --replace DISCARDS PRIEST HAND EDITS. export reads the
sprites back (colour edits survive; depth comes from the cache; added pixels take the nearest original depth).
export --local skips PixelFlow and writes the atlas from the cache.
"""
import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys

import time

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'client' / 'assets'
CACHE = Path(__file__).resolve().parent / 'priest_raw'
sys.path.insert(0, os.environ.get('VALHALLA_TOOLS', str(ROOT.parent / 'Valhalla' / 'tools')))
import make_warrior_sprites as rig  # noqa: E402

V, unit = rig.V, rig.unit
FW = FH = 160
AX, AY, SS, PX = 80, 119, 2, 1.03
DIRS = rig.DIRS
PARTS = ['body', 'armor_pilgrim', 'armor_dawn', 'weapon_mace', 'weapon_sunmace']
MATS = {
    'skin': ['#92595c', '#ce9182', '#f0bfac', '#ffe0ce'],
    'hair': ['#151a30', '#293451', '#465278', '#7985ac'],
    'brow': ['#171526', '#242037', '#332946', '#443750'],
    'cloth': ['#4a4048', '#76686f', '#a99a9c', '#d8c9c0'],
    'pants': ['#2a2a40', '#43476a', '#68729a', '#97a2c4'],
    'robe': ['#7a7490', '#aaa3bf', '#dcd6e8', '#fffaf4'],       # ivory robe, lavender in shadow
    'dawn': ['#a08a8e', '#d4bdb4', '#fbeadb', '#fffefc'],      # warm white vestments
    'gold': ['#6e4a12', '#b0801f', '#e8b840', '#fff0a0'],
    'stole': ['#4a2a6e', '#7a4aa6', '#b585d8', '#e6c4ff'],     # violet stole, the Assassin's scarf recoloured
    'leather': ['#2a2030', '#463a50', '#6a5a70', '#98889e'],
    'wood': ['#3a2420', '#6e4336', '#a77a56', '#d6ae82'],
    'silver': ['#3a516d', '#7791b0', '#bdcfe5', '#f2f5ff'],
    'glow': ['#d79a1a', '#ffc94a', '#ffe99a', '#fffbe0'],
    'iris': ['#6a4a1c', '#a7762c', '#e0b050', '#fff0b0'],
    'white': ['#c0aec4', '#ded2e2', '#f6eef1', '#fffbf6'],
    'mouth': ['#5c2d45', '#86506a', '#c88493', '#e9a4ab'],
}
PALETTE = ['#00000000', '#18182a', '#ffffff'] + [c for r in MATS.values() for c in r]
assert len(PALETTE) == len(set(PALETTE)) and len(PALETTE) <= 255
COLOR = {name: [3 + 4 * i + k for k in range(4)] for i, name in enumerate(MATS)}
DEFAULT = dict(root=(0, 0, 0), lean=4, twist=0, roll=0, sway=0, eyes='open',
               handL=(-13, 6, 50), handR=(13, 3, 48),
               footL=(-5, 0, 4), footR=(5, 0, 4),
               mace=(.1, .3, 1), ground=False, dropped=False)
HIP, SHOULDER = 37, 66


def idle(k):
    a = k / 6 * math.tau
    return dict(root=(0, 0, -.35 * math.sin(a)), sway=math.sin(a),
                handL=(-13, 6, 50 + .5 * math.sin(a)), eyes='closed' if k == 4 else 'open')


def walk(k):
    q = k / 8
    a = q * math.tau
    def foot(s, t):
        t %= 1
        return (s * 5, 9 - t * 36 if t < .5 else -9 + (t - .5) * 36,
                4 + (6 * math.sin((t - .5) * math.tau) if t >= .5 else 0))
    return dict(lean=15, roll=2 * math.sin(a), twist=5 * math.sin(a),
                root=(0, 0, -.65 * math.cos(a * 2)), sway=3 * math.sin(a),
                handL=(-14, -4 - math.sin(a) * 3, 53), handR=(14, -5 + math.sin(a) * 3, 52),
                mace=(.1, .3 - .25 * math.sin(a), 1),
                footL=foot(-1, q), footR=foot(1, q + .5))


def attack(k):
    # Raise the mace, bring it down in front on frame 4 (the impact), the free hand blessing forward.
    lean = [6, -4, -8, 8, 20, 17, 10, 5][k]
    twist = [-4, -16, -26, -4, 22, 26, 10, 0][k]
    right = [(13, 3, 48), (15, -6, 64), (16, -10, 74), (12, 12, 68), (9, 24, 52), (9, 22, 42), (11, 13, 44), (13, 3, 48)][k]
    mace = [(.1, .3, 1), (.1, -.3, 1), (.1, -.8, .8), (.05, .5, .85), (0, 1, -.1), (0, .85, -.55), (.1, .5, .5), (.1, .3, 1)][k]
    left = [(-13, 6, 50), (-12, 12, 62), (-10, 18, 70), (-8, 20, 66), (-8, 22, 60), (-10, 16, 54), (-12, 9, 51), (-13, 6, 50)][k]
    f = [0, -.3, -.5, .5, 1, .65, .25, 0][k]
    return dict(lean=lean, twist=twist, root=(0, max(0, f) * 2, -.6),
                handL=left, handR=right, mace=mace, sway=-3 * f,
                footL=(-6, 4 * max(0, f), 4), footR=(6, -5 * max(0, f), 4))


def hurt(k):
    f = [.25, 1, .4, 0][k]
    return dict(lean=-14 * f, root=(0, -2 * f, 0), twist=9 * f,
                handL=(-16, 5, 55), handR=(15, 5, 52), eyes='closed' if k < 3 else 'open', sway=-2 * f)


def die(k):
    return dict(lean=[-5, -23, -43, -66, -85, -90, -90, -90][k],
                root=(0, 8 if k >= 3 else 0, 0), eyes='closed',
                handL=(-17, 1, 50), handR=(17, 1, 49),
                footL=(-5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                footR=(5, 9 if k >= 3 else 0, 10 if k >= 3 else 4),
                ground=k >= 3, dropped=k >= 2)


CLIPS = {'idle': (6, 6, idle), 'walk': (12, 8, walk), 'attack': (20, 8, attack),
         'hurt': (10, 4, hurt), 'die': (8, 8, die)}
ARMOR_ITEMS = {'none': {'name': 'Simple cloth', 'part': None, 'defense': 0},
               'pilgrim': {'name': 'Pilgrim robes', 'part': 'armor_pilgrim', 'defense': 3},
               'dawn': {'name': 'Dawnweave vestments', 'part': 'armor_dawn', 'defense': 5}}
WEAPON_ITEMS = {'none': {'name': 'Empty hands', 'part': None, 'attack': 0},
                'mace': {'name': 'Oak mace', 'part': 'weapon_mace', 'attack': 4},
                'sunmace': {'name': 'Sunbreaker mace', 'part': 'weapon_sunmace', 'attack': 8}}


class Ink:
    """Flat cel polygons with a depth gradient along projected limbs (the Assassin's renderer)."""
    def __init__(self, psi):
        self.turn = rig.rotz(psi)
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

    def plate(self, points, mat, tone=2, detail=False):
        proj = [self.project(p) for p in points]
        xy = [p[0] for p in proj]
        self.poly(xy, COLOR[mat][tone], np.mean([p[1] for p in proj]) - .01, not detail)

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


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R = rig.rotz(rig.rad(p['twist'])) @ rig.roty(rig.rad(p['roll'])) @ rig.rotx(rig.rad(-p['lean']))
    pivot, shift = V(0, 0, HIP), V(*p['root'])
    xf = lambda a: pivot + R @ (V(*a) - pivot) + shift
    joints = {}
    for sx, key in ((-1, 'L'), (1, 'R')):
        s = V(sx * 8, 0, SHOULDER)
        elbow, hand = rig.ik2(s, V(*p['hand' + key]), 13.5, 13.5, unit(V(sx, -.2, -.3)))
        hip = xf((sx * 4.2, 0, HIP))
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

    def torso(ink, mat, halfwidth, y, bottom=38, top=67):
        for sy in (-1, 1):
            pts = [(-halfwidth, sy * y, top), (halfwidth, sy * y, top),
                   (halfwidth * .72, sy * y, 49), (halfwidth * .84, sy * y, bottom),
                   (-halfwidth * .84, sy * y, bottom), (-halfwidth * .72, sy * y, 49)]
            ink.plate([xf(q) for q in pts], mat, 2 if sy == 1 else 1)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * halfwidth, -y, top), (sx * halfwidth, y, top),
                      (sx * halfwidth * .84, y, bottom), (sx * halfwidth * .84, -y, bottom)]], mat, 1)

    torso(body, 'cloth', 7.8, 3.5)
    body.bone(xf((0, 0, 68)), xf((0, 0, 77)), 2.2, 2.1, 'skin')
    for sx, key in ((-1, 'L'), (1, 'R')):
        j = joints[key]
        body.bone(j['hip'], j['knee'], 3.3, 2.9, 'pants')
        body.bone(j['knee'], j['ankle'], 2.7, 1.9, 'pants')
        body.bone(j['ankle'] + V(0, -1, -1.5), j['ankle'] + V(0, 4, -2), 2, 2.1, 'skin')
        body.bone(j['shoulder'], j['elbow'], 2.6, 2.1, 'skin')
        body.bone(j['elbow'], j['hand'], 2, 1.6, 'skin')
        body.bone(j['hand'] - R @ V(0, 0, 1), j['hand'] + R @ V(0, 0, 1.8), 2.2, 1.8, 'skin', -.2)

    # Face and hair are the Assassin's: oriented to the head's projected axis, almond eyes, angular fringe.
    hc, hd = body.project(xf((0, 0, 87)))
    up = unit(body.project(xf((0, 0, 96)))[0] - hc)
    right = V(-up[1], up[0])
    H = lambda x, y: hc + right * x + up * y
    front = -math.cos(psi + rig.rad(p['twist']))
    side = -math.sin(psi + rig.rad(p['twist']))
    skin_shape = [(-8, 7), (-9.5, 1), (-8.4, -5), (-4.3, -10), (0, -11.3), (4.3, -10), (8.4, -5), (9.5, 1), (8, 7), (0, 10)]
    body.poly([H(*q) for q in skin_shape], COLOR['skin'][2], hd - 4)
    body.poly([H(*q) for q in [(4, 6), (8, 6), (9, 0), (7, -6), (0, -11), (3, -4)]], COLOR['skin'][1], hd - 4.05, False)
    if front < -.4:
        body.poly([H(*q) for q in [(-9, 8), (-10, 0), (-8, -8), (-4, -10), (5, -9), (9, -5), (10, 4), (6, 12), (-3, 13)]], COLOR['hair'][1], hd - 5)
    else:
        for sx in (-1, 1):
            if abs(side) > .85 and sx * side < 0:
                continue
            ex = sx * 4 * max(.28, front) + side * 3.3
            ey = -1.3
            if p['eyes'] == 'closed':
                body.poly([H(ex - 2.3, ey), H(ex, ey - .6), H(ex + 2.3, ey + .5)], 1, hd - 5.8)
            else:
                body.poly([H(ex - 2.6, ey + .6), H(ex - 1.2, ey + 2), H(ex + 2.4, ey + 1.1),
                           H(ex + 2, ey - 1.8), H(ex - .4, ey - 2)], COLOR['white'][2], hd - 5.3)
                body.poly([H(ex - .5, ey + 1.5), H(ex + 1.2, ey + 1), H(ex + 1.1, ey - 1.6), H(ex - .6, ey - 1.6)], COLOR['iris'][2], hd - 5.5, False)
                body.poly([H(ex - .1, ey + .8), H(ex + .5, ey + .8), H(ex + .5, ey - 1.2), H(ex - .1, ey - 1.2)], 1, hd - 5.55, False)
                body.poly([H(ex - 2.9, ey + 1.6), H(ex - 1, ey + 2.5), H(ex + 2.6, ey + 1.6), H(ex + 2.3, ey + .8)], 1, hd - 5.6, False)
                body.poly([H(ex - .7, ey + .7), H(ex + .1, ey + .7), H(ex + .1, ey + 1.4), H(ex - .7, ey + 1.4)], COLOR['white'][3], hd - 5.7, False)
            body.poly([H(ex - 2.1, 3), H(ex + 2, 3.3), H(ex + 1.7, 3.8), H(ex - 1.9, 3.5)], COLOR['brow'][0], hd - 5.8, False)
        nx = side * 5
        body.poly([H(nx, -3.7), H(nx + .6, -5), H(nx + 1.5, -4.3)], COLOR['skin'][1], hd - 5.5, False)
        body.poly([H(nx - 1, -7.4), H(nx + 1.2, -7.3), H(nx + .6, -7.8)], COLOR['mouth'][1], hd - 5.6, False)
    crown = [(-10, 2), (-11, 8), (-8, 12), (-9, 15), (-3, 13), (1, 16), (3, 13),
             (8, 14), (8, 11), (11, 8), (10, 2), (8, -3), (6, 2), (4, -1), (1, 6), (-2, 1), (-5, 6), (-8, -2)]
    body.poly([H(*q) for q in crown], COLOR['hair'][1], hd - 6)
    for wedge in [[(-8, 10), (-2, 12), (-4, 6), (-8, 3)], [(-1, 12), (3, 13), (6, 7), (2, 7)], [(6, 11), (9, 8), (8, 3)]]:
        body.poly([H(*q) for q in wedge], COLOR['hair'][2], hd - 6.1, False)
    body.poly([H(*q) for q in [(-6, 11), (-2, 12), (-3, 10), (-6, 8)]], COLOR['hair'][3], hd - 6.2, False)
    body.plate([xf(q) for q in [(-3, -5, 79), (2, -5, 79), (4 + p['sway'], -8, 65),
                               (1 + p['sway'] * 1.5, -10, 59), (-1 + p['sway'], -9, 65)]], 'hair', 1)

    for key, mat in [('armor_pilgrim', 'robe'), ('armor_dawn', 'dawn')]:
        ink = inks[key]
        dawn = mat == 'dawn'
        torso(ink, mat, 8.6, 4.3, 34, 69)
        # Long robe: a skirt that flares to a hem above the boots, swaying with the body.
        hem, wide, deep, sway = 15, 12, 8.4, p['sway'] * .8
        for sy in (-1, 1):
            xy = [(-8.2, sy * 4.5, 38), (8.2, sy * 4.5, 38), (wide + sway, sy * deep, hem), (-wide + sway, sy * deep, hem)]
            ink.plate([xf(q) for q in xy], mat, 3 if sy == 1 else 2)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 8.2, -4.5, 38), (sx * 8.2, 4.5, 38),
                      (sx * wide + sway, deep, hem), (sx * wide + sway, -deep, hem)]], mat, 2)
        # Gold hem band, front and back.
        for sy in (-1, 1):
            ink.plate([xf(q) for q in [(-wide + sway, sy * deep, hem + 3.2), (wide + sway, sy * deep, hem + 3.2),
                                      (wide + sway, sy * deep, hem), (-wide + sway, sy * deep, hem)]], 'gold', 2 if sy == 1 else 1, True)
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
        # Mantle over the shoulders and a violet stole down the front (the Assassin's scarf, kept).
        ink.plate([xf(q) for q in [(-9.5, 4.9, 71), (9.5, 4.9, 71), (11, 5.2, 60), (0, 5.5, 55), (-11, 5.2, 60)]], mat, 1)
        ink.plate([xf(q) for q in [(-9.5, -4.9, 71), (9.5, -4.9, 71), (11, -5.2, 60), (0, -5.5, 55), (-11, -5.2, 60)]], mat, 1)
        ink.plate([xf(q) for q in [(-4.2, 5.6, 75), (4.2, 5.6, 75), (3.2, 5.7, 70), (0, 5.9, 66), (-3.2, 5.7, 70)]], 'gold', 2)
        stole = [(-3.2, 5.7, 73), (3.2, 5.7, 73), (3.6 + sway * .4, 5.9 + 1.2, 38), (3.8 + sway * .6, deep + .4, hem - 3),
                 (-3.8 + sway * .6, deep + .4, hem - 3), (-3.6 + sway * .4, 5.9 + 1.2, 38)]
        ink.plate([xf(q) for q in stole], 'stole', 2)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 3.2, 5.8, 73), (sx * 2.5, 5.8, 73), (sx * 2.9 + sway * .4, 6.8, 38), (sx * 3.6 + sway * .6, deep + .5, hem - 3)]], 'gold', 2, True)
        # Sun emblem on the chest: a small gold cross over the stole.
        ink.plate([xf(q) for q in [(-.8, 6, 66), (.8, 6, 66), (.8, 6, 52), (-.8, 6, 52)]], 'gold', 3, True)
        ink.plate([xf(q) for q in [(-3.8, 6, 61.5), (3.8, 6, 61.5), (3.8, 6, 59.2), (-3.8, 6, 59.2)]], 'gold', 3, True)
        if dawn:
            for sx in (-1, 1):
                j = joints['L' if sx < 0 else 'R']
                ink.bone(j['shoulder'], j['shoulder'] + R @ V(sx * 3, 0, -3), 3.4, 2.2, 'gold', -1.1)
            # A thin halo floating above the head.
            ring = lambda r, t: H(r * math.cos(t), 19 + r * .5 * math.sin(t))
            steps = 24
            for width, color, push in ((10.0, lambda a: 1, 0), (9.2, lambda a: COLOR['glow'][2 if math.sin(a) > 0 else 1], .1)):
                for i in range(steps):
                    a, b = i / steps * math.tau, (i + 1) / steps * math.tau
                    inner = 7.2 if width > 9.5 else 7.9
                    ink.poly([ring(width, a), ring(width, b), ring(inner, b), ring(inner, a)], color(a), hd - 7.5 - push, False)

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
        neck = hand + u * (19 if sun else 16)
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
        if sun:
            for t in (0, 1, 2, 3):
                ang = t * math.pi / 2 + math.pi / 4
                d = across * math.cos(ang) + u * math.sin(ang)
                n = across * -math.sin(ang) + u * math.cos(ang)
                ink.plate([c + d * rr * .9 + n * 1.3, c + d * (rr + 3.2), c + d * rr * .9 - n * 1.3], 'glow', 2)
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}


REVISION = hashlib.sha256((json.dumps([MATS, DEFAULT, PX, SS]) + ''.join(
    inspect.getsource(f) for f in (Ink, render_frame, idle, walk, attack, hurt, die))).encode()
    + Path(rig.__file__).read_bytes()).hexdigest()


def read_frame(clip, facing, k):
    path = CACHE / f'{clip}_{facing}_{k}.npz'
    valid = False
    if path.exists():
        with np.load(path) as saved:
            valid = 'revision' in saved and str(saved['revision']) == REVISION
    if not valid:
        CACHE.mkdir(exist_ok=True)
        parts = render_frame(clip, facing, k)
        np.savez_compressed(path, revision=REVISION,
                            **{f'{n}_index': d[0] for n, d in parts.items()},
                            **{f'{n}_depth': d[1].astype(np.float32) for n, d in parts.items()})
    with np.load(path) as saved:
        return {name: (saved[f'{name}_index'], saved[f'{name}_depth']) for name in PARTS}


def composite(parts, armor, weapon):
    best = np.full((FH, FW), np.inf)
    out = np.zeros((FH, FW), np.uint8)
    for part in ['body'] + ([f'armor_{armor}'] if armor != 'none' else []) + ([f'weapon_{weapon}'] if weapon != 'none' else []):
        idx, depth = parts[part]
        take = (idx > 0) & (depth <= best)
        out[take], best[take] = idx[take], depth[take]
    return out


PAL = np.array([[int(c[j:j + 2], 16) for j in (1, 3, 5)] + [0 if i == 0 else 255] for i, c in enumerate(PALETTE)], np.uint8)
rgba = lambda idx: Image.fromarray(PAL[idx], 'RGBA')
COMBOS = [('none', 'none'), ('pilgrim', 'mace'), ('dawn', 'sunmace')]


def preview(clips, out):
    out.mkdir(parents=True, exist_ok=True)
    for clip in clips:
        n = CLIPS[clip][1]
        for armor, weapon in COMBOS:
            sheet = Image.new('RGBA', (FW * n, FH * 8), '#487048')
            for di, facing in enumerate(DIRS):
                for k in range(n):
                    parts = read_frame(clip, facing, k)
                    for part, (idx, z) in parts.items():
                        if (idx[0] > 0).any() or (idx[-1] > 0).any() or (idx[:, 0] > 0).any() or (idx[:, -1] > 0).any():
                            raise ValueError(f'clipped {clip}/{facing}/{k}/{part}')
                    sheet.alpha_composite(rgba(composite(parts, armor, weapon)), (k * FW, di * FH))
                    ImageDraw.Draw(sheet).text((k * FW + 3, di * FH + 3), f'{facing} {k}', fill='white')
            sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).save(out / f'priest_{clip}_{armor}.png')
        print('preview', clip, 'eight facings; no clipped parts', flush=True)
    compare = Image.new('RGBA', (FW * 6, FH), '#487048')
    compare.alpha_composite(Image.open(ASSETS / 'assassin_body.png').crop((0, 0, FW, FH)), (0, 0))
    for j, (a, b) in enumerate(COMBOS, 1):
        compare.alpha_composite(rgba(composite(read_frame('idle', 'S', 0), a, b)), (j * FW, 0))
        compare.alpha_composite(rgba(composite(read_frame('idle', 'SE', 2), a, b)), ((j + 3 if j < 3 else 0) * FW, 0)) if j < 3 else None
    compare.resize((compare.width * 3, compare.height * 3), Image.Resampling.NEAREST).save(out / 'priest_comparison.png')


def pixel_name(clip, facing):
    return f'priest_{clip}_{facing.lower()}'


def pixel_api():
    sys.path.insert(0, os.path.expanduser('~/.claude/skills/makesprites'))
    import pf
    original = pf.api
    def retry(*args, **kwargs):
        for attempt in range(25):
            result = original(*args, **kwargs)
            if not any(e.get('code') == 'rate_limited' for e in result.get('errors', [])):
                return result
            time.sleep(5)
        raise RuntimeError('PixelFlow request limit did not clear')
    pf.api = retry
    return pf


def pixel_ids(pf):
    manifest = CACHE / 'editor_ids.txt'
    ids = json.loads(manifest.read_text()) if manifest.exists() else {}
    ids.update(pf.ids('priest_'))
    return ids


def build(replace=False):
    pf = pixel_api()
    existing = pf.ids('priest_')
    if existing and not replace:
        raise SystemExit('priest sprites already exist; use export to keep edits, or build --replace to discard them.')
    for sid in existing.values():
        response = pf.api('delete', {'sprite_id': sid})
        assert response.get('ok') or any(e.get('code') == 'not_found' for e in response.get('errors', [])), response
    created, ids = [], {}
    try:
        for clip, (fps, n, _) in CLIPS.items():
            assert FW * FH * len(PARTS) * n <= 1048576
            for facing in DIRS:
                name = pixel_name(clip, facing)
                sid = pf.create(name, FW, FH, n, PALETTE, fps=fps, layers=len(PARTS),
                                layer_ops=[{'op': 'set_layer', 'layer': i, 'name': part, 'visible': part == 'body'}
                                           for i, part in enumerate(PARTS)])
                created.append(sid); ids[name] = sid
                for k in range(n):
                    parts = read_frame(clip, facing, k)
                    result = pf.api('draw', {'sprite_id': sid, 'frame': k, 'ops': [
                        {'op': 'grid', 'rows': parts[part][0].astype(int).tolist(), 'x': 0, 'y': 0, 'layer': li}
                        for li, part in enumerate(PARTS)]})
                    assert result.get('ok'), result
                    time.sleep(.12)
                print(name, sid, flush=True)
    except BaseException:
        for sid in created:
            pf.api('delete', {'sprite_id': sid})
        raise
    CACHE.mkdir(exist_ok=True)
    (CACHE / 'editor_ids.txt').write_text(json.dumps(ids, indent=2) + '\n')


def export(local=False):
    pf = None if local else pixel_api()
    ids = {} if local else pixel_ids(pf)
    meta_clips = {clip: {'row0': ci * 8, 'n': n, 'fps': fps} for ci, (clip, (fps, n, _)) in enumerate(CLIPS.items())}
    size = (FW * 8, FH * 8 * len(CLIPS))
    atlases = {part: Image.new('RGBA', size) for part in PARTS}
    depths = {part: Image.new('RGB', size, (255, 255, 0)) for part in PARTS}
    for clip, (_, n, _) in CLIPS.items():
        for di, facing in enumerate(DIRS):
            edited = None
            if not local:
                sp, frames = pf.load(ids[pixel_name(clip, facing)])
                assert (sp['width'], sp['height']) == (FW, FH) and len(frames) == n
                assert [layer['name'] for layer in sp['layers']] == PARTS
                edited = (sp['palette'], frames)
            for k in range(n):
                raw = read_frame(clip, facing, k)
                x, y = k * FW, (meta_clips[clip]['row0'] + di) * FH
                for li, part in enumerate(PARTS):
                    depth = raw[part][1].copy()
                    if edited:
                        idx = edited[1][k][li]
                        picture = Image.fromarray(pf.to_rgba(idx, edited[0]), 'RGBA')
                        added = (idx > 0) & ~np.isfinite(depth)
                        if added.any():
                            nearest = ndi.distance_transform_edt(~np.isfinite(depth), return_distances=False, return_indices=True)
                            depth[added] = depth[tuple(nearest)][added]
                    else:
                        idx = raw[part][0]
                        picture = rgba(idx)
                    opaque = idx > 0
                    encoded = np.full((FH, FW), 65535, np.uint16)
                    encoded[opaque] = np.clip(np.round((depth[opaque] + 512) * 64), 0, 65534).astype(np.uint16)
                    rgb = np.zeros((FH, FW, 3), np.uint8)
                    rgb[..., 0], rgb[..., 1] = encoded >> 8, encoded & 255
                    atlases[part].paste(picture, (x, y))
                    depths[part].paste(Image.fromarray(rgb, 'RGB'), (x, y))
        print('export', clip, flush=True)
    for part in PARTS:
        atlases[part].save(ASSETS / f'priest_{part}.png', optimize=True)
        depths[part].save(ASSETS / f'priest_{part}_depth.png', optimize=True)
    meta = {'frame': [FW, FH], 'anchor': [AX, AY], 'dirs': DIRS, 'clips': meta_clips,
            'parts': {part: {'png': f'priest_{part}.png', 'depth': f'priest_{part}_depth.png'} for part in PARTS},
            'equipment': {'armor': ARMOR_ITEMS, 'weapon': WEAPON_ITEMS},
            'defaultEquipment': {'armor': 'pilgrim', 'weapon': 'mace'},
            'sprites': ids, 'ramps': MATS,
            'depth': {'encoding': 'R*256+G', 'offset': 512, 'scale': 64, 'near': 'smaller'},
            'facing': 'Same eight-direction formula and foot anchor as assassin_sprites.txt',
            'attack': {'duration': .4, 'impact': .2},
            'style': '2D Korean RPG anime cel illustration', 'portrait': [57, 15, 46, 46],
            'editing': 'One PixelFlow sprite per clip and facing (priest_<clip>_<facing>), body visible, equipment hidden. build --replace discards edits.'}
    (ASSETS / 'priest_sprites.txt').write_text(json.dumps(meta, indent=2) + '\n')
    print('exported five parts and five depth maps', size, flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['preview', 'build', 'export'])
    ap.add_argument('clip', nargs='?', default='all', choices=['all'] + list(CLIPS))
    ap.add_argument('directory', nargs='?', default='/tmp/valhalla-priest-preview')
    ap.add_argument('--replace', action='store_true')
    ap.add_argument('--local', action='store_true')
    args = ap.parse_args()
    if args.command == 'preview':
        preview(list(CLIPS) if args.clip == 'all' else [args.clip], Path(args.directory))
    elif args.command == 'build':
        build(args.replace)
    else:
        export(args.local)
