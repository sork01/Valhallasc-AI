#!/usr/bin/env python3
"""The 24 general NPC designs in the player style (NPC-PLAYER-STYLE-GENERAL), drawn with the players' rig.

usage: npcp_general.py preview OUT_DIR [design ...]   contact sheets (scratch; never writes client/)

Core (frame patching, rig body, palette helpers) lives in npcp_sample.py. A design is data: an outfit spec, a hair style,
a hat, a prop and a pose tweak. Skin, hair and cloth are three recolourable materials (4 tones each, `AMOUNTS`), so the
298 people who share a design keep their own skin/hair/cloth through the client's per-design remap.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import npcp_sample as core
from npcp_sample import cc, rig, V, ramp, set_frame, FRAME, ANCHOR, CLIPS

ROOT = Path(__file__).resolve().parent.parent
PLAN = json.loads((ROOT / 'docs/npc-art-plan.txt').read_text())
SPECS = {k: v for k, v in PLAN['designs'].items() if v.get('general')}
# Remap amounts the client applies to the identity colour, one list per material (see client/npc-art.js `amounts`).
AMOUNTS = dict(skin=(.62, .82, 1., 1.2), hair=(.5, .75, 1., 1.3), cloth=(.45, .7, 1., 1.45))
ADULT_PX, CHILD_PX = core.ADULT_PX, core.ADULT_PX * .68


def circle(cx, cy, rx, ry=None, n=10, a0=0.):
    ry = rx if ry is None else ry
    return [(cx + rx * math.cos(a0 + i / n * math.tau), cy + ry * math.sin(a0 + i / n * math.tau)) for i in range(n)]


def materials(spec, identity=None):
    s = dict(spec)
    m = {**cc.FACE_MATS}
    m['skin'] = ramp(s['skin'], AMOUNTS['skin'])
    m['hair'] = ramp(s['hairc'], AMOUNTS['hair'])
    m['cloth'] = ramp(s['coat'], AMOUNTS['cloth'])
    m['trim'] = ramp(s.get('trim', '#e0b85c'), (.5, .75, 1., 1.3))
    m['pants'] = ramp(s.get('pants', '#4a3f5c'))
    m['leather'] = ramp('#8a5a3c')
    m['metal'] = ['#46516b', '#7f98ad', '#b9d3e0', '#eaf6fb']
    m['wood'] = ['#3a2218', '#6b4128', '#a8703f', '#dca66a']
    m['gold'] = ['#6e4a12', '#b0801f', '#e8b840', '#fff0a0']
    m['cream'] = ['#9c8e79', '#cbbd9f', '#f1e4c8', '#fff8e6']
    m['glass'] = ['#27657c', '#4a9db0', '#8fdcd4', '#d6fff4']
    m['leaf'] = ['#285948', '#3d8460', '#6fb878', '#b4e69a']
    m['iris'] = ramp('#4a78b8', (.5, .8, 1., 1.4))
    m['accent'] = ramp(s.get('accent', '#7fb8d0'))
    m['hatc'] = ramp(s.get('hatc') or s['coat'], AMOUNTS['cloth'])
    m['tail'] = ramp(s.get('tail') or s['coat'], (.5, .75, 1., 1.3))
    m['orn'] = ramp(s.get('orn', '#e0b85c'), (.5, .75, 1., 1.3))
    seen = set()
    for r in m.values():
        for i, c in enumerate(r):
            while c in seen:
                c = '#%06x' % ((int(c[1:], 16) + 1) & 0xffffff)
            seen.add(c)
            r[i] = c
    return m


# ------------------------------------------------------------------------------------------------ hair and hats
def hair(ink, head, c, style, p, low=False):
    H, hd, front = head['H'], head['hd'], head['front']
    sw = p['sway']
    if front <= -.4:
        ink.poly([H(*q) for q in [(-9.5, 8), (-10.5, 0), (-8.5, -8), (-4, -10.5), (5, -9.5), (9.5, -5), (10.5, 4), (6.5, 13), (-3, 14)]], c['hair'][2], hd - 5)
    top = {'shaved': 11.5, 'crop': 14, 'spikes': 14}.get(style, 17.4)
    crown = [(-10.6, -6), (-11.6, 5), (-10, 11), (-5, top - 1.4), (1, top), (7, top - 1.4), (11, 11), (11.8, 4), (10.6, -6)]
    if front > -.4:
        crown += [(8.6, 0), (7, 4.4), (3, 6.8), (-.4, 4.6), (-3.6, 6.4), (-7, 4.2), (-9, 0)] if style not in ('shaved',) else [(8.8, 4), (0, 7.4), (-8.8, 4)]
    else:
        crown += [(8, -2), (0, -4), (-8, -2)]
    ink.poly([H(*q) for q in crown], c['hair'][1], hd - 6)
    ink.poly([H(*q) for q in [(-9, 11), (-3, top - 1.8), (4, top - 1.4), (9.6, 11), (9, 8.4), (3, 12), (-3, 12.4), (-8.4, 8)]], c['hair'][2], hd - 6.1, False)
    ink.poly([H(*q) for q in [(-5, top - 3), (0, top - 1.2), (4, top - 2.2), (0, top - 3.8), (-4, top - 4.8)]], c['hair'][3], hd - 6.2, False)
    side = lambda sx, pts, col=1, dz=6.05: ink.poly([H(sx * a, b) for a, b in pts], c['hair'][col], hd - dz, False)
    for sx in (-1, 1):
        side(sx, [(10.4, 3), (11.4, -4), (9.4, -6), (8.8, 0)])         # sideburns
    if style == 'braid':
        for sx in (-1, 1):
            for i in range(7):
                y = -4 - i * 3.4
                ink.poly([H(sx * (11.5 + math.sin(i + sw * .3)), y + 2.4), H(sx * 14.4, y), H(sx * (11.5 + math.sin(i + sw * .3)), y - 2.4), H(sx * 9.4, y)],
                         c['hair'][1 + i % 2], hd - 6.3)
    elif style == 'ponytail':
        ink.poly([H(*q) for q in [(9, 6), (15 + sw, 1), (17 + sw, -10), (15 + sw, -22), (12, -9), (10, -2)]], c['hair'][1], hd - 6.3)
        ink.poly([H(*q) for q in [(9.6, 5), (13, 5.4), (13.6, 2.6), (10, 2)]], c['trim'][2], hd - 6.4)
    elif style == 'long':
        for sx in (-1, 1):
            ink.poly([H(sx * 9.4, 8), H(sx * 13, 4), H(sx * 14 + sw * sx * .3, -12), H(sx * 12, -22), H(sx * 8.6, -17), H(sx * 9.4, -4)], c['hair'][1], hd - 6.3)
    elif style == 'waves':
        for sx in (-1, 1):
            ink.poly([H(sx * 9.4, 9), H(sx * 13.6, 6), H(sx * 12.6, -1), H(sx * 15, -6), H(sx * 11, -9), H(sx * 9.4, -2)], c['hair'][1], hd - 6.3)
        ink.poly([H(*q) for q in [(-10, 12), (2, 19), (10, 14), (13.4, 12), (6, 15.4), (-4, 16)]], c['hair'][2], hd - 6.3, False)
    elif style == 'curls':
        for i, (x, y) in enumerate([(-10.5, 9), (-12, 1), (-11, -6), (10.5, 9), (12, 1), (11, -6), (-5, 16), (4, 17), (0, 17.6)]):
            ink.poly([H(x + dx, y + dy) for dx, dy in circle(0, 0, 3.4, 3.2, 8)], c['hair'][1 + (i % 2)], hd - 6.3)
    elif style == 'bun':
        by = 20.6 if not low else 5
        bx = 0 if not low else 13.4
        ink.poly([H(bx + x, y + by) for x, y in circle(0, 0, 5.2, 4.6, 10)], c['hair'][1], hd - 6.3)
        ink.poly([H(bx + x - 1.2, y + by + 1) for x, y in circle(0, 0, 2.4, 2, 8)], c['hair'][3], hd - 6.4, False)
    elif style == 'pigtails':
        for sx in (-1, 1):
            ink.poly([H(sx * 9.2, 5), H(sx * 13.6 + sw * sx * .4, 1), H(sx * 15.4 + sw * .6, -9), H(sx * 12.4 + sw * .5, -15), H(sx * 10.6, -4), H(sx * 9, -1)], c['hair'][1], hd - 6.4)
            ink.poly([H(sx * 9.6, 3.6), H(sx * 12.6, 3), H(sx * 12.8, 1), H(sx * 9.8, 1.2)], c['accent'][2], hd - 6.5)
    elif style == 'beard':
        ink.poly([H(*q) for q in [(-9.6, -3.6), (-10, -9), (-6, -16), (0, -19.6), (6, -16), (10, -9), (9.6, -3.6), (5, -6.6), (0, -7.6), (-5, -6.6)]], c['hair'][1], hd - 5.7)
        ink.poly([H(*q) for q in [(-5, -8), (0, -11), (5, -8), (3, -16), (0, -18), (-3, -16)]], c['hair'][2], hd - 5.8, False)
        ink.poly([H(*q) for q in [(-3.4, -5.4), (3.4, -5.4), (2, -7), (-2, -7)]], c['hair'][1], hd - 5.9, False)   # moustache
    elif style == 'spikes':
        for i, x in enumerate((-9, -4.5, 0, 4.5, 9)):
            ink.poly([H(x - 3, 12), H(x + .4 * (x), 20 + (i % 2) * 3.4 + (3 if i == 2 else 0)), H(x + 3, 12)], c['hair'][1 + i % 2], hd - 6.3)


def hat(ink, head, c, kind, p):
    H, hd, front = head['H'], head['hd'], head['front']
    sw = p['sway']
    P = lambda pts, mat, tone=2, dz=7, ol=True: ink.poly([H(*q) for q in pts], c[mat][tone], hd - dz, ol)
    if kind == 'helm':
        P([(-12, 2), (-12.4, 9), (-9.6, 16), (-3.4, 20), (3.4, 20), (9.6, 16), (12.4, 9), (12, 2), (8, 4.4), (0, 5.4), (-8, 4.4)], 'cloth', 1)
        P([(-9.6, 14), (-3, 18.4), (3, 18.4), (9.6, 14), (8.8, 11), (0, 15), (-8.8, 11)], 'cloth', 3, 7.1, False)
        P([(-2, 5.4), (2, 5.4), (1.6, -2), (-1.6, -2)], 'metal', 2, 7.2)
        P([(-1.6, 20), (1.6, 20), (2.2, 21.8), (0, 23), (-2.2, 21.8)], 'trim', 2, 7.2)
    elif kind == 'veil':
        P([(-11.6, 5), (-12.6, 12), (-8, 19), (0, 21), (8, 19), (12.6, 12), (11.6, 5), (14, -10), (13, -26), (9, -22), (9.6, -4), (8, 4), (0, 7), (-8, 4), (-9.6, -4), (-9, -22), (-13, -26), (-14, -10)], 'cloth', 3, 6.9)
        P([(-12, 8), (0, 16), (12, 8), (8.6, 12), (0, 19), (-8.6, 12)], 'cloth', 2, 7.0, False)
    elif kind == 'goggles':
        if front > -.4:
            P([(-9.6, 8.6), (9.6, 8.6), (9.8, 6.8), (-9.8, 6.8)], 'leather', 1, 7)
            for sx in (-1, 1):
                P([(sx * 4.6 + x, 10 + y) for x, y in circle(0, 0, 3.2, 3.2, 8)], 'metal', 2, 7.1)
                P([(sx * 4.6 + x, 10 + y) for x, y in circle(0, 0, 2, 2, 8)], 'accent', 3, 7.2, False)
    elif kind == 'toque':
        P([(-9.6, 12), (9.6, 12), (9.4, 16), (-9.4, 16)], 'cream', 1, 7)
        for x, y, r in [(-6, 18.4, 4.6), (6, 18.4, 4.6), (0, 20.4, 5.2), (0, 17.6, 6.6)]:
            P(circle(x, y, r, r * .92, 12), 'cream', 2, 7.1)
        P(circle(-2.4, 22, 2.2, 1.6, 8), 'cream', 3, 7.2, False)
    elif kind == 'ribbon':
        P([(8, 14), (14.6, 19), (14.6, 9), (8, 14)], 'accent', 2, 7.2)
        P([(8, 14), (1.4, 19), (1.4, 9)], 'accent', 3, 7.2)
        P(circle(8, 14, 1.8, 1.8, 6), 'accent', 1, 7.3, False)
    elif kind == 'turban':
        P([(-11.8, 6), (-12.4, 12), (-8, 18.4), (0, 21), (8, 18.4), (12.4, 12), (11.8, 6), (7, 8.6), (0, 9.6), (-7, 8.6)], 'cloth', 2, 7)
        for i, y in enumerate((9, 12.6, 16.2)):
            P([(-12.2 + i * .6, y), (0, y + 4.4 - i * .8), (12.2 - i * .6, y), (12.4 - i * .6, y - 1.8), (0, y + 2.2), (-12.4 + i * .6, y - 1.8)], 'cloth', 3 if i % 2 == 0 else 1, 7.05, False)
        P(circle(0, 16.4, 3, 3, 8), 'trim', 3, 7.2)
        P(circle(0, 16.4, 1.4, 1.4, 6), 'accent', 3, 7.3, False)
    elif kind == 'feather':
        P([(-11, 5), (-11.4, 11), (-6, 17), (3, 18), (11.6, 12), (11, 5), (6, 7), (0, 8.4), (-6, 7)], 'cloth', 1, 7)
        P([(-8, 13), (-2, 16.6), (6, 16), (9.4, 11), (4, 13.6), (-4, 13)], 'cloth', 2, 7.1, False)
        P([(6, 14), (10, 18), (13, 22), (11 + sw * .3, 25), (9, 20.4), (8, 17)], 'leaf', 2, 7.2)
        P([(8, 16.6), (10.6, 19.6), (11.2, 22), (9.8, 20)], 'leaf', 3, 7.3, False)
    elif kind == 'cap':
        P([(-11, 5), (-11.4, 11), (-6, 16.6), (3, 17.6), (11.4, 12), (11, 5), (6, 7.4), (0, 8.6), (-6, 7.4)], 'cloth', 1, 7)
        P([(-6, 14), (0, 16.6), (6, 15), (9.6, 11), (4, 12.6), (-3, 12.4)], 'cloth', 2, 7.1, False)
        P([(-11.6, 6.4), (11.6, 6.4), (12.6, 4.4), (-12.6, 4.4)], 'leather', 2, 7.15)
    elif kind == 'beret':
        P(circle(3, 16, 13, 5.6, 14, .3), 'cloth', 2, 7)
        P(circle(1, 17.6, 8, 3, 10, .3), 'cloth', 3, 7.1, False)
        P([(2, 21), (2, 24.6), (4, 24), (4, 21)], 'cloth', 1, 7.2)
    elif kind == 'straw':
        P(circle(0, 11.6, 19.4, 5.6, 16), 'gold', 2, 7)
        P([(-9.6, 12), (-8, 20), (0, 24), (8, 20), (9.6, 12)], 'gold', 3, 7.1)
        P([(-9.8, 12.4), (9.8, 12.4), (9.6, 15), (-9.6, 15)], 'accent', 2, 7.2)
        P(circle(7, 14, 2.2, 2.2, 6), 'trim', 3, 7.3, False)
    elif kind == 'beanie':
        P([(-11.6, 5), (-12, 12), (-6.4, 18.4), (0, 20), (6.4, 18.4), (12, 12), (11.6, 5), (7, 7.4), (0, 8.4), (-7, 7.4)], 'cloth', 2, 7)
        P([(-11.8, 5.4), (11.8, 5.4), (12, 9.6), (-12, 9.6)], 'cloth', 1, 7.1)
        P(circle(0, 21.6, 3, 3, 8), 'cloth', 3, 7.2)
    elif kind == 'scarf':
        P([(-9, -9), (9, -9), (10, -13), (-10, -13)], 'accent', 2, 6.6)
        P([(-4, -10), (4, -10), (7 + sw, -34), (1 + sw, -36)], 'accent', 3, 6.65)
        P([(5, -10), (9, -12), (13 + sw, -30), (7 + sw, -32)], 'accent', 1, 6.7)
    elif kind == 'hood':
        P([(-13, 0), (-14.4, 12), (-9, 21), (0, 25), (9, 21), (14.4, 12), (13, 0), (14.6, -14), (10, -18), (9, 6), (0, 11), (-9, 6), (-10, -18), (-14.6, -14)], 'cloth', 1, 3.5)
        P([(-10, 14), (-4, 21), (4, 21), (10, 14), (9, 8), (0, 12), (-9, 8)], 'cloth', 2, 3.6, False)
    elif kind == 'band':
        P([(-11.4, 7.6), (11.4, 7.6), (11.4, 10.4), (-11.4, 10.4)], 'accent', 2, 7)
        P([(-11, 8.4), (11, 8.4), (11, 9.2), (-11, 9.2)], 'accent', 3, 7.1, False)
    elif kind == 'crown':
        hat_crown(ink, head, c, p)
    elif kind == 'circlet':
        P([(-10.6, 9.6), (-5, 12.6), (0, 13.4), (5, 12.6), (10.6, 9.6), (10.4, 11.8), (0, 15.6), (-10.4, 11.8)], 'trim', 2, 7)
        P([(0, 17), (-2.2, 14), (0, 11.6), (2.2, 14)], 'accent', 3, 7.2)


# ------------------------------------------------------------------------------------------------ outfit
def outfit(ink, xf, joints, R, p, c, o):
    """Torso, sleeves, skirt/coat, belt and boots from a spec dict."""
    sw = p['sway']
    mat = o.get('mat', 'cloth')
    core.body_layer(ink, xf, joints, R, c, legs=o.get('legs', True), cloth=mat, pants=o.get('pants', 'pants'))
    cc.torso(ink, xf, mat, o.get('half', 8.5), 4.0, 40, 69)
    skirt = o.get('skirt')
    if skirt:
        hem, wide, deep = skirt
        wm = o.get('skirt_mat', mat)
        for sy, tone in ((-1, 1), (1, 2)):
            ink.plate([xf(q) for q in [(-8.4, sy * 4.2, 42), (8.4, sy * 4.2, 42), (wide + sw * .8, sy * deep, hem), (-wide + sw * .8, sy * deep, hem)]], wm, tone)
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 8.4, -4.2, 42), (sx * 8.4, 4.2, 42), (sx * wide + sw * .8, deep, hem), (sx * wide + sw * .8, -deep, hem)]], wm, 1)
        if o.get('hem_trim'):
            ink.plate([xf(q) for q in [(-wide + sw * .8, deep + .1, hem + 2.4), (wide + sw * .8, deep + .1, hem + 2.4), (wide + sw * .8, deep + .1, hem), (-wide + sw * .8, deep + .1, hem)]], o['hem_trim'], 2, True)
    core.sleeves(ink, joints, o.get('sleeve_mat', mat), o.get('sleeve', 1.0), o.get('sleeve_r', 3.4))
    if o.get('belt'):
        core.belt(ink, xf, o['belt'], 38.5, 42.5, 8.5, 4.35)
    if o.get('boots', 'leather') and o.get('legs', True):
        core.boots(ink, joints, o.get('boots', 'leather'))
    if o.get('collar'):
        ink.plate([xf(q) for q in [(-4.4, 4.5, 69), (0, 4.9, 65.6), (4.4, 4.5, 69), (0, 4.7, 70.4)]], o['collar'], 3, True)


def cape(ink, xf, joints, p, c, mat='cloth', hem=18, wide=12, hood=False):
    sw = p['sway']
    ink.plate([xf(q) for q in [(-9, -5, 70), (9, -5, 70), (wide + sw, -8.6, hem), (-wide + sw, -8.6, hem)]], mat, 1)
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * 9, -4.8, 70), (sx * 9.4, 3, 66), (sx * wide + sw, 0, hem + 2), (sx * wide + sw, -8, hem)]], mat, 1)


def hand_cover(ink, joints, R, who='L'):
    h = joints[who]['hand']
    ink.bone(h - R @ V(0, 0, .6), h + R @ V(0, 0, 2.2), 2.4, 2.0, 'skin', -1.6)


def line3(ink, a, b, r, mat, z=-.5, tone=2):
    ink.bone(a, b, r, r, mat, z, tone)


# ------------------------------------------------------------------------------------------------ props (held in the L hand: the screen's right)
def prop_spear(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    tip = h + V(0, 0, 40)
    line3(ink, h + V(0, 0, -16), tip, 1.3, 'wood')
    ink.plate([tip + V(-4, 0, 0), tip + V(0, 0, 11), tip + V(4, 0, 0)], 'metal', 3)
    ink.plate([tip + V(1.2, 0, -3), tip + V(11, 0, -7 + p['sway']), tip + V(1.2, 0, -14)], 'accent', 2)
    hand_cover(ink, joints, R)


def prop_bottle(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    cx = h + V(0, 2, 9)
    ink.plate([cx + V(x, 0, z) for x, z in circle(0, 0, 6.4, 6.4, 10)], 'glass', 2)
    ink.plate([cx + V(x, 0, z) for x, z in circle(-1.6, 1.6, 2.2, 2.2, 6)], 'glass', 3, True)
    line3(ink, cx + V(0, 0, 4), cx + V(0, 0, 11), 2, 'glass')
    line3(ink, cx + V(0, 0, 11), cx + V(0, 0, 13.4), 2.4, 'wood')
    hand_cover(ink, joints, R)


def prop_mug(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    line3(ink, h + V(0, 1, 1), h + V(0, 1, 11), 3.8, 'gold', -1.4)
    line3(ink, h + V(0, 1, 11), h + V(0, 1, 13), 3.8, 'cream', -1.45, 3)
    ink.ribbon([h + V(-3.4, 1, 9), h + V(-7, 1, 8), h + V(-7, 1, 3), h + V(-3.4, 1, 2)], 1, 1, 'gold', 2, -1.5, False)
    hand_cover(ink, joints, R)


def prop_scales(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    line3(ink, h + V(0, 0, -6), h + V(0, 0, 26), 1.1, 'gold')
    line3(ink, h + V(-12, 0, 24), h + V(12, 0, 24), .9, 'gold')
    for sx in (-1, 1):
        t = h + V(sx * 12, 0, 24)
        ink.ribbon([t, t + V(sx * 1.6, 0, -9)], .35, .35, 'gold', 1, -.4, False)
        ink.plate([t + V(sx * 5.6, 0, -11), t + V(sx * -5.6, 0, -11), t + V(0, 0, -14)], 'gold', 2)
    hand_cover(ink, joints, R)


def prop_bow(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    pts = [h + V(1.5 + 7 * math.sin(i / 8 * math.pi), 0, -26 + i * 7.4) for i in range(9)]
    ink.ribbon(pts, 1.4, 1.4, 'wood', 2, -.6)
    ink.ribbon([pts[0], pts[-1]], .25, .25, 'cream', 3, -.7, False)
    hand_cover(ink, joints, R)


def prop_trumpet(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    a, b = h + V(2, 4, 4), h + V(-12, 7, 14)
    line3(ink, a, b, 1.8, 'gold', -1.2)
    ink.plate([b + V(0, 0, -2.4), b + V(-7, 2, -6.5), b + V(-7, 2, 7.5), b + V(0, 0, 2.4)], 'gold', 3)
    hand_cover(ink, joints, R)


def prop_flowers(ink, xf, joints, R, p, c):
    h = (joints['L']['hand'] + joints['R']['hand']) / 2
    b = h + V(0, 5, 3)
    ink.plate([b + V(-12, 0, 2), b + V(12, 0, 2), b + V(9, 0, -10), b + V(-9, 0, -10)], 'wood', 2)
    ink.plate([b + V(-12, 0, 2), b + V(12, 0, 2), b + V(12, 0, 0), b + V(-12, 0, 0)], 'wood', 3, True)
    for i, (x, z) in enumerate([(-8, 8), (-3, 12), (3, 10), (8, 7), (0, 6), (-5, 5)]):
        line3(ink, b + V(x * .4, 0, 2), b + V(x, 0, z), .5, 'leaf', -.5)
        ink.plate([b + V(x + dx, .5, z + dz) for dx, dz in circle(0, 0, 3.4, 3.4, 8)], ('accent', 'trim', 'cloth')[i % 3], 3)


def prop_fish(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    line3(ink, h + V(0, 0, 4), h + V(-1, 0, -3), .5, 'cream', -.5)
    f = h + V(-2, 1, -9)
    ink.plate([f + V(x * 1.0, 0, z * 1.8) for x, z in circle(0, 0, 4.2, 4.2, 10)], 'metal', 3)
    ink.plate([f + V(x * .9, 0, z * 1.1 - 3) for x, z in circle(0, 0, 3.2, 3.2, 8)], 'metal', 2, True)
    ink.plate([f + V(0, 0, -7), f + V(-4, 0, -12), f + V(4, 0, -12)], 'metal', 1)
    ink.plate([f + V(x, .5, 3) for x, z in circle(0, 0, .8, .8, 4)], 'metal', 0, True)
    hand_cover(ink, joints, R)


def prop_spool(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    line3(ink, h + V(0, 0, -10), h + V(0, 0, 26), .9, 'wood')
    ink.plate([h + V(x * 1.0, 0, z * 1.5 + 12) for x, z in circle(0, 0, 4.6, 4.6, 10)], 'accent', 2)
    ink.plate([h + V(x - 1.2, .5, z * 1.5 + 13) for x, z in circle(0, 0, 1.8, 1.8, 6)], 'accent', 3, True)
    ink.ribbon([h + V(0, 0, 18), h + V(-7 - p['sway'], 2, 14), h + V(-9, 3, 4)], .35, .35, 'accent', 2, -.6, False)
    hand_cover(ink, joints, R)


def prop_satchel(ink, xf, joints, R, p, c):
    ink.ribbon([xf((-8, 3.4, 68)), xf((0, 4.8, 54)), xf((9.4, 5, 40))], 1.3, 1.3, 'leather', 2, -1.2)
    ink.plate([xf(q) for q in [(7, 4.6, 46), (16, 4.6, 46), (16, 4.8, 28), (7, 4.8, 28)]], 'leather', 2)
    ink.plate([xf(q) for q in [(7, 5.0, 46), (16, 5.0, 46), (15, 5.0, 40), (8, 5.0, 40)]], 'leather', 3, True)
    ink.plate([xf(q) for q in [(10, 5.2, 41), (13, 5.2, 41), (13, 5.2, 38.6), (10, 5.2, 38.6)]], 'gold', 3, True)


def prop_staff(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    line3(ink, h + V(0, 0, -16), h + V(0, 0, 56), 1.4, 'wood')
    ink.plate([h + V(x, 0, 56 + z) for x, z in circle(0, 0, 2.6, 2.6, 8)], 'trim', 3)
    # bedroll across the back and shoulders
    ink.bone(xf((-9, -7, 62)), xf((9, -7, 66)), 3.4, 3.4, 'leather', 1, 2)
    hand_cover(ink, joints, R)


def prop_lyre(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    b = h + V(0, 3, 3)
    frame = [b + V(-9, 0, 4), b + V(-12, 0, 16), b + V(-7, 0, 26), b + V(0, 0, 22), b + V(7, 0, 26), b + V(12, 0, 16), b + V(9, 0, 4), b + V(0, 0, -2)]
    ink.ribbon(frame, 1.7, 1.7, 'gold', 2, -1.2)
    for x in (-5, -1.6, 1.6, 5):
        line3(ink, b + V(x, 0, 21), b + V(x * .7, 0, 2), .2, 'cream', -1.3, 3)
    hand_cover(ink, joints, R)


def prop_cane(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    line3(ink, h + V(0, 0, 8), h + V(0, 0, -(h[2] - 1)), 1.3, 'wood', -.5)
    ink.ribbon([h + V(0, 0, 8), h + V(-1, 0, 14), h + V(-6, 0, 16), h + V(-9, 0, 11)], 1.3, 1.3, 'wood', 2, -.5)
    hand_cover(ink, joints, R)


def prop_palette(ink, xf, joints, R, p, c):
    h = joints['R']['hand']
    b = h + V(0, 3, 4)
    ink.plate([b + V(x * 1.4, 0, z) for x, z in circle(0, 0, 7.4, 5.4, 10)], 'wood', 2)
    for i, m in enumerate(('accent', 'trim', 'cloth', 'leaf')):
        ink.plate([b + V(-4.6 + i * 3.1, .5, 1.6 - (i % 2) * 2.4 + dz) for _, dz in circle(0, 0, 1.2, 1.2, 4)], m, 3, True)
    ink.plate([b + V(x * .6 - 2, .5, z - 3.4) for x, z in circle(0, 0, 1.6, 1.6, 6)], 'wood', 0, True)
    hand_cover(ink, joints, R, 'R')
    h2 = joints['L']['hand']
    line3(ink, h2 + V(0, 0, -6), h2 + V(1.6, 0, 22), .8, 'wood', -.5)
    ink.plate([h2 + V(1, 0, 22), h2 + V(2.4, 0, 22), h2 + V(1.8, 0, 28)], 'accent', 3)
    hand_cover(ink, joints, R, 'L')


def prop_saw(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    a, b = h + V(0, 0, -2), h + V(3, 0, -34)
    ink.plate([a + V(-2.6, 0, 0), a + V(2.6, 0, 0), b + V(3.4, 0, 0), b + V(-3.4, 0, 0)], 'metal', 2)
    for i in range(9):
        t = a + (b - a) * (i / 9.)
        ink.plate([t + V(3, 0, 0), t + V(5.6, 0, -2), t + V(3, 0, -4)], 'metal', 3, True)
    ink.bone(h + V(-2, 0, 4), h + V(2, 0, -2), 2.2, 2.2, 'wood', -.8)
    hand_cover(ink, joints, R)


def prop_alembic(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    cx = h + V(0, 2, 8)
    ink.plate([cx + V(x, 0, z) for x, z in circle(0, 0, 6.4, 6.4, 10)], 'glass', 2)
    ink.plate([cx + V(x, 0, z - 2) for x, z in circle(0, 0, 4.2, 3.2, 8)], 'accent', 2, True)
    line3(ink, cx + V(0, 0, 5), cx + V(0, 0, 12), 1.8, 'glass')
    ink.ribbon([cx + V(0, 0, 12), cx + V(9, 0, 16), cx + V(15, 0, 12), cx + V(15, 0, 4), cx + V(11, 0, -1)], 1.1, 1.1, 'glass', 2, -.6)
    ink.plate([cx + V(x + 11, 0, z - 4) for x, z in circle(0, 0, 2.4, 2.4, 6)], 'glass', 3)
    hand_cover(ink, joints, R)


def prop_scroll(ink, xf, joints, R, p, c):
    h = (joints['L']['hand'] + joints['R']['hand']) / 2
    b = h + V(0, 6, 2)
    ink.plate([b + V(-13, 0, -7), b + V(13, 0, -7), b + V(13, 0, 8), b + V(-13, 0, 8)], 'cream', 2)
    ink.bone(b + V(-13, 0, -8), b + V(-13, 0, 9), 2.6, 2.6, 'cream', -.5, 3)
    ink.bone(b + V(13, 0, -8), b + V(13, 0, 9), 2.6, 2.6, 'cream', -.5, 3)
    for z in (2, -1.4, -4.8):
        line3(ink, b + V(-9, 0, z), b + V(7, 0, z - .3), .2, 'leather', -.6, 1)
    ink.plate([b + V(-.8, .2, 8), b + V(.8, .2, 8), b + V(.8, .2, -7), b + V(-.8, .2, -7)], 'accent', 2, True)


def prop_book(ink, xf, joints, R, p, c):
    h = (joints['L']['hand'] + joints['R']['hand']) / 2
    b = h + V(0, 6, 3)
    ink.plate([b + V(-11, 0, -6.4), b + V(11, 0, -6.4), b + V(11, 0, 6.4), b + V(-11, 0, 6.4)], 'leather', 1)
    ink.plate([b + V(-10, .3, -5.2), b + V(-.5, .3, -5.6), b + V(-.5, .3, 5.6), b + V(-10, .3, 5.2)], 'cream', 3)
    ink.plate([b + V(.5, .3, -5.6), b + V(10, .3, -5.2), b + V(10, .3, 5.2), b + V(.5, .3, 5.6)], 'cream', 2)
    for z in (3, 0, -3):
        line3(ink, b + V(-8.6, .4, z), b + V(-2.4, .4, z), .2, 'leather', -.6, 1)
        line3(ink, b + V(2.4, .4, z), b + V(8.6, .4, z), .2, 'leather', -.6, 1)


def prop_bread(ink, xf, joints, R, p, c):
    h = (joints['L']['hand'] + joints['R']['hand']) / 2
    b = h + V(0, 6, 1)
    ink.plate([b + V(-16, -7, 0), b + V(16, -7, 0), b + V(16, 7, 0), b + V(-16, 7, 0)], 'wood', 2)
    for x in (-10, -3.4, 3.4, 10):
        ink.bone(b + V(x - 2.4, 0, 4), b + V(x + 2.4, 0, 4), 3.6, 3.6, 'gold', -.6)
        ink.plate([b + V(x - 1.2, -3, 6.4), b + V(x + 1.4, -3, 6.8), b + V(x, -3, 7.8)], 'gold', 3, True)


def prop_chest(ink, xf, joints, R, p, c):
    h = (joints['L']['hand'] + joints['R']['hand']) / 2
    b = h + V(0, 6, -1)
    ink.plate([b + V(-12, 0, -8), b + V(12, 0, -8), b + V(12, 0, 8), b + V(-12, 0, 8)], 'wood', 2)
    ink.plate([b + V(-12, 0, 3), b + V(12, 0, 3), b + V(12, 0, 8), b + V(-12, 0, 8)], 'wood', 3, True)
    for x in (-9, 9):
        ink.plate([b + V(x - 1, .3, -8), b + V(x + 1, .3, -8), b + V(x + 1, .3, 8), b + V(x - 1, .3, 8)], 'gold', 2, True)
    ink.plate([b + V(-2, .4, 4), b + V(2, .4, 4), b + V(2, .4, -1), b + V(-2, .4, -1)], 'gold', 3, True)
    # ledger tucked under the right arm
    j = joints['R']
    ink.plate([j['elbow'] + V(-3, 0, -2), j['elbow'] + V(3, 0, -2), j['elbow'] + V(3, 1, -13), j['elbow'] + V(-3, 1, -13)], 'cream', 2)


def prop_reins(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    for i, (dx, dz) in enumerate(((-9, -4), (-12, -9))):
        ink.ribbon([h + V(0, 0, 0), h + V(dx * .5, 1 + i, dz * .3), h + V(dx, 2 + i, dz), h + V(dx * .6 + p['sway'], 2 + i, dz - 8)], .8, .8, 'leather', 2 - i, -.6)
    ink.bone(h + V(-4, 1, -14), h + V(-11, 2, -13), 1.8, 1.8, 'metal', -.6)
    hand_cover(ink, joints, R)


def prop_lantern(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    top = h + V(0, 0, 56)
    line3(ink, h + V(0, 0, -16), top, 1.3, 'wood')
    ink.ribbon([top, top + V(-5, 0, 3), top + V(-9, 0, -2)], 1, 1, 'wood', 2, -.5)
    l = top + V(-9, 0, -5)
    ink.plate([l + V(-4, 0, 2), l + V(4, 0, 2), l + V(4.4, 0, -9), l + V(-4.4, 0, -9)], 'gold', 2)
    ink.plate([l + V(-2.6, .3, .8), l + V(2.6, .3, .8), l + V(3, .3, -7.6), l + V(-3, .3, -7.6)], 'trim', 3, True)
    ink.plate([l + V(-5, 0, 3), l + V(5, 0, 3), l + V(0, 0, 7)], 'gold', 1)
    hand_cover(ink, joints, R)


def prop_hammer(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    top = h + V(-1.5, 2, 15)
    line3(ink, h + V(.5, .5, -7), top, 1.5, 'wood', -.5)
    ink.bone(top + V(-6.5, 0, 0), top + V(6.5, 0, 0), 5.2, 5.2, 'metal', -.7)
    ink.bone(top + V(-6, 0, 1.6), top + V(6, 0, 1.6), 1.2, 1.2, 'metal', -.9, 3)
    hand_cover(ink, joints, R)


def prop_kite(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    kc = h + V(-26, 2, 30)
    pts = [kc + V(0, 0, 18), kc + V(11, 0, 0), kc + V(0, 0, -14), kc + V(-11, 0, 0)]
    ink.ribbon([h + V(0, 0, 1.5), h + V(-8, 1, 8), h + V(-18, 1.5, 14), kc + V(0, 0, -14)], .5, .5, 'trim', 2, outline=False)
    ink.plate(pts, 'accent', 2)
    ink.plate([pts[0], pts[1], kc + V(0, 0, .4)], 'accent', 3, True)
    ink.plate([pts[0], pts[3], kc + V(0, 0, .4)], 'accent', 1, True)
    hand_cover(ink, joints, R)


PROPS = dict(hammer=prop_hammer, kite=prop_kite, spear=prop_spear, bottle=prop_bottle, mug=prop_mug, scales=prop_scales, bow=prop_bow, trumpet=prop_trumpet,
             flowers=prop_flowers, fish=prop_fish, spool=prop_spool, satchel=prop_satchel, staff=prop_staff, lyre=prop_lyre,
             cane=prop_cane, palette=prop_palette, saw=prop_saw, alembic=prop_alembic, scroll=prop_scroll, book=prop_book,
             bread=prop_bread, chest=prop_chest, reins=prop_reins, lantern=prop_lantern)
# Hand poses that fit each prop; 'two' props are held in front of the chest in both hands.
HOLD = dict(hammer=dict(handL=(-14, 6, 46)), kite=dict(handL=(-15, 8, 54)), spear=dict(handL=(-12, 5, 46)), bottle=dict(handL=(-12, 9, 44)), mug=dict(handL=(-12, 12, 46)), scales=dict(handL=(-14, 6, 48)),
            bow=dict(handL=(-13, 4, 54)), trumpet=dict(handL=(-8, 12, 62)), fish=dict(handL=(-13, 5, 48)), spool=dict(handL=(-12, 6, 46)),
            staff=dict(handL=(-12, 5, 46)), lyre=dict(handL=(-12, 10, 52)), cane=dict(handL=(-13, 5, 44)), saw=dict(handL=(-13, 4, 44)),
            alembic=dict(handL=(-12, 10, 46)), reins=dict(handL=(-13, 8, 42)), lantern=dict(handL=(-12, 5, 46)),
            flowers=dict(handL=(-10, 14, 42), handR=(10, 14, 42)), scroll=dict(handL=(-9, 14, 46), handR=(9, 14, 46)),
            book=dict(handL=(-9, 14, 49), handR=(9, 14, 49)), bread=dict(handL=(-9, 14, 41), handR=(9, 14, 41)),
            chest=dict(handL=(-9, 14, 41), handR=(9, 14, 41)), palette=dict(handR=(12, 12, 48), handL=(-12, 4, 46)), satchel={})
TWO = {'flowers', 'scroll', 'book', 'bread', 'chest'}


# ------------------------------------------------------------------------------------------------ the 24 designs
def mk(**kw):
    return kw


OUTFITS = dict(
    sentinel=dict(sleeve=.8, belt='leather', pants_mat='pants', boots='metal', collar='metal', half=9.2),
    physician=dict(skirt=(14, 12.4, 8.4), hem_trim='trim', sleeve=1, belt='trim', collar='cream'),
    smith=dict(sleeve=.55, sleeve_r=3.9, belt='leather'),
    baker=dict(sleeve=.7, belt='cream', skirt=(26, 10.6, 6.6), skirt_mat='cream'),
    innkeeper=dict(skirt=(12, 14.4, 9.4), hem_trim='cream', sleeve=.55, sleeve_r=4.4, belt='leather'),
    merchant=dict(skirt=(10, 13.4, 9), hem_trim='trim', sleeve=1, sleeve_r=4.2, belt='trim'),
    ranger=dict(sleeve=1, belt='leather', skirt=(30, 10.8, 6.4)),
    scholar=dict(skirt=(8, 11.8, 8), sleeve=1, sleeve_r=3.8, belt='leather', hem_trim='leather'),
    herald=dict(sleeve=.9, belt='trim', skirt=(30, 10, 6.4), hem_trim='trim'),
    gardener=dict(sleeve=.7, belt='leather', skirt=(30, 10, 6.4), skirt_mat='leaf'),
    fisher=dict(sleeve=1, belt='leather', skirt=(26, 10.4, 6.6)),
    weaver=dict(skirt=(14, 12, 8.4), sleeve=.8, belt='leather', hem_trim='accent'),
    courier=dict(sleeve=1, belt='leather', skirt=(34, 9.6, 5.8)),
    pilgrim=dict(skirt=(10, 11.6, 8), sleeve=1, belt='leather'),
    bard=dict(sleeve=.9, belt='trim', skirt=(34, 9.4, 5.6)),
    child=dict(skirt=(22, 11, 7.4), sleeve=.6, sleeve_r=3.6, belt='trim', hem_trim='trim'),
    elder=dict(skirt=(14, 10.8, 7.2), sleeve=1, belt='leather'),
    painter=dict(skirt=(20, 11.4, 7.6), sleeve=.85, belt='accent', hem_trim='accent'),
    carpenter=dict(sleeve=.45, sleeve_r=3.8, belt='leather', skirt=(34, 9.4, 5.6), skirt_mat='leather'),
    alchemist=dict(skirt=(22, 12, 8), sleeve=1, belt='leather', hem_trim='accent'),
    steward=dict(skirt=(10, 10.6, 7.2), sleeve=1, belt='trim', hem_trim='trim', collar='trim'),
    stablehand=dict(sleeve=.6, sleeve_r=3.8, belt='leather', boots='leather'),
    lamplighter=dict(skirt=(8, 11.6, 8), sleeve=1, belt='leather'),
    banker=dict(sleeve=1, belt='gold', skirt=(32, 9.6, 5.8), collar='cream'),
)


def extras(name, ink, xf, joints, R, p, c, head):
    """Garment details beyond the shared outfit: aprons, capes, vests, pennants."""
    sw = p['sway']
    apron = lambda mat, z_top=66, z_hem=30, wide=7.4: [
        ink.plate([xf(q) for q in [(-6.4, 4.7, z_top), (6.4, 4.7, z_top), (wide, 4.9, z_hem), (-wide, 4.9, z_hem)]], mat, 2),
        ink.plate([xf(q) for q in [(-6.4, 4.9, z_top), (6.4, 4.9, z_top), (6.4, 5.0, z_top - 10), (-6.4, 5.0, z_top - 10)]], mat, 3, True)]
    if name in ('smith', 'carpenter', 'innkeeper', 'baker', 'stablehand'):
        apron('leather' if name != 'baker' and name != 'innkeeper' else 'cream', 66 if name != 'innkeeper' else 56, 24 if name == 'innkeeper' else 30)
    if name == 'sentinel':
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 8.6, 3.6, 69), (sx * 12, 0, 66), (sx * 12, -3.6, 69), (sx * 8.6, -3.6, 71)]], 'metal', 3)
        ink.plate([xf(q) for q in [(-5, 4.8, 66), (5, 4.8, 66), (3, 4.9, 44), (-3, 4.9, 44)]], 'trim', 2, True)
    if name in ('fisher', 'lamplighter', 'pilgrim', 'physician'):
        cape(ink, xf, joints, p, c, 'cloth', 18 if name != 'physician' else 14, 12.6)
    if name == 'stooped_cape':
        pass
    if name == 'scholar':
        ink.plate([xf(q) for q in [(-9, 3.4, 69), (9, 3.4, 69), (10.4, 3.6, 58), (-10.4, 3.6, 58)]], 'cloth', 1, True)
    if name == 'herald':
        ink.plate([xf(q) for q in [(-5.6, 4.9, 68), (5.6, 4.9, 68), (4, 5.4, 30), (0, 5.8, 25), (-4, 5.4, 30)]], 'trim', 2)
        ink.plate([xf(q) for q in [(-2, 5.1, 66), (2, 5.1, 66), (2, 5.5, 34), (-2, 5.5, 34)]], 'cloth', 3, True)
    if name == 'bard':
        ink.plate([xf(q) for q in [(-6.6, 4.8, 68), (-1.4, 4.8, 68), (-1, 4.9, 46), (-7, 4.9, 46)]], 'trim', 2, True)
        ink.plate([xf(q) for q in [(6.6, 4.8, 68), (1.4, 4.8, 68), (1, 4.9, 46), (7, 4.9, 46)]], 'trim', 2, True)
    if name == 'banker':
        for z in (62, 56, 50):
            ink.plate([xf(q) for q in [(-.8, 4.9, z + 1), (.8, 4.9, z + 1), (.8, 4.9, z - 1), (-.8, 4.9, z - 1)]], 'gold', 3, True)
        ink.plate([xf(q) for q in [(-6, 4.8, 69), (-.4, 4.8, 66), (-.4, 4.8, 42), (-6.6, 4.8, 42)]], 'accent', 2, True)
    if name == 'gardener':
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 6.4, 4.8, 66), (sx * 3.6, 4.8, 66), (sx * 3.6, 4.9, 46), (sx * 6.4, 4.9, 46)]], 'leaf', 3, True)
    if name == 'ranger':
        ink.plate([xf(q) for q in [(-9, -5, 70), (9, -5, 70), (10 + sw, -8, 36), (-10 + sw, -8, 36)]], 'leaf', 1)
    if name == 'courier':
        pass
    if name == 'painter':
        for x, z, m in ((-3, 56, 'accent'), (3, 48, 'trim'), (-4, 38, 'leaf')):
            ink.plate([xf((x + dx, 5.0, z + dz)) for dx, dz in circle(0, 0, 1.4, 1.4, 5)], m, 3, True)
    if name == 'alchemist':
        for x, z, m in ((-4, 56, 'accent'), (3, 46, 'glass')):
            ink.plate([xf((x + dx, 5.0, z + dz)) for dx, dz in circle(0, 0, 1.6, 1.6, 5)], m, 3, True)
        ink.plate([xf(q) for q in [(-8, 4.6, 40), (8, 4.6, 40), (0, 4.8, 28)]], 'accent', 1, True)
    if name == 'carpenter':
        ink.plate([xf(q) for q in [(6, 5.0, 42), (13, 5.0, 40), (12, 5.1, 30), (6, 5.1, 32)]], 'leather', 3, True)
    if name == 'steward':
        ink.plate([xf(q) for q in [(-10.4, -4.8, 72), (10.4, -4.8, 72), (13 + sw, -8, 30), (-13 + sw, -8, 30)]], 'cloth', 1)
    if name == 'merchant':
        for sx in (-1, 1):
            ink.plate([xf(q) for q in [(sx * 1, 4.8, 69), (sx * 8.4, 4.8, 66), (sx * 11, 4.9, 30), (sx * 2, 4.9, 30)]], 'cloth', 3 if sx > 0 else 1, True)
    if name == 'elder':
        pass


def skin_of(spec):
    return ['#dca480', '#b87d58', '#e9bda1', '#a66a51'][spec['index'] % 4]


def hair_of(spec):
    return ['#694737', '#e4d6ae', '#353d62', '#ab6250', '#475b51', '#75638d'][spec['index'] % 6]



# ------------------------------------------------------------------------------------------------ more props (specials)
def _ball(ink, centre, r, mat, tone=2, hi=True):
    ink.plate([centre + V(x, 0, z) for x, z in circle(0, 0, r, r, 10)], mat, tone)
    if hi:
        ink.plate([centre + V(x - r * .3, .4, z + r * .3) for x, z in circle(0, 0, r * .35, r * .35, 6)], mat, 3, True)


def prop_pearl(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    _ball(ink, h + V(0, 2, 8), 4.4, 'cream', 3)
    hand_cover(ink, joints, R)


def prop_orb(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    _ball(ink, h + V(0, 2, 9), 6, 'glass', 2)
    ink.plate([h + V(x, .8, z + 9) for x, z in circle(0, 0, 3.2, 3.2, 8)], 'accent', 3, True)
    hand_cover(ink, joints, R)


def prop_seed(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    ink.plate([h + V(x * .8, 0, z * 1.3 + 8) for x, z in circle(0, 0, 4.4, 4.4, 10)], 'leaf', 2)
    ink.plate([h + V(x - 1, .4, z + 10) for x, z in circle(0, 0, 1.4, 1.4, 6)], 'leaf', 3, True)
    ink.ribbon([h + V(0, 0, 12), h + V(1, 0, 17), h + V(5, 0, 19)], .6, .4, 'leaf', 2, -.5, False)
    hand_cover(ink, joints, R)


def prop_grain(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    for i, x in enumerate((-4, -2, 0, 2, 4)):
        top = h + V(x * 1.6, 0, 20 + (i % 2) * 3)
        line3(ink, h + V(x * .3, 0, -3), top, .5, 'gold', -.5)
        for j in range(4):
            ink.plate([top + V(x * .1 - 1.2, .3, -j * 2.4), top + V(x * .1 + 1.2, .3, -j * 2.4 - .8), top + V(x * .1, .3, -j * 2.4 + 1.6)], 'trim', 3, True)
    ink.bone(h + V(-4, 1, -2), h + V(4, 1, -2), 1.5, 1.5, 'accent', -.8)
    hand_cover(ink, joints, R)


def prop_fan(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    pts = [h + V(0, 1, 4)] + [h + V(-14 * math.cos(a), 1, 4 + 14 * math.sin(a)) for a in (.2, .55, .9, 1.25, 1.57, 1.9, 2.25, 2.6, 2.95)]
    ink.plate(pts, 'accent', 2)
    for a in (.55, 1.25, 1.9, 2.6):
        line3(ink, h + V(0, 1.4, 4), h + V(-14 * math.cos(a), 1.4, 4 + 14 * math.sin(a)), .25, 'trim', -.6, 3)
    hand_cover(ink, joints, R)


def prop_key(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    line3(ink, h + V(0, 0, -6), h + V(0, 0, 18), 1.1, 'gold')
    ink.plate([h + V(x, 0, z + 21) for x, z in circle(0, 0, 4, 4, 10)], 'gold', 2)
    ink.plate([h + V(x, .3, z + 21) for x, z in circle(0, 0, 1.8, 1.8, 6)], 'gold', 0, True)
    for z, w in ((-4, 4), (0, 3)):
        line3(ink, h + V(0, 0, z), h + V(-w, 0, z), 1, 'gold', -.4)
    hand_cover(ink, joints, R)


def prop_tablet(ink, xf, joints, R, p, c):
    h = (joints['L']['hand'] + joints['R']['hand']) / 2
    b = h + V(0, 6, 3)
    ink.plate([b + V(-9, 0, -9), b + V(9, 0, -9), b + V(9, 0, 9), b + V(-9, 0, 9)], 'metal', 1)
    ink.plate([b + V(-7.6, .3, -7.6), b + V(7.6, .3, -7.6), b + V(7.6, .3, 7.6), b + V(-7.6, .3, 7.6)], 'metal', 2, True)
    for z in (4, 0, -4):
        line3(ink, b + V(-5, .4, z), b + V(5, .4, z), .3, 'accent', -.6, 3)


def prop_waterjug(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    cx = h + V(0, 2, -2)
    ink.plate([cx + V(x * 1.0, 0, z * 1.15 - 4) for x, z in circle(0, 0, 6.6, 6.6, 12)], 'accent', 2)
    ink.plate([cx + V(x - 2, .4, z - 2) for x, z in circle(0, 0, 2, 2, 6)], 'accent', 3, True)
    line3(ink, cx + V(0, 0, 2), cx + V(0, 0, 6), 3, 'accent', -.3, 1)
    line3(ink, h + V(0, 0, 2), cx + V(0, 0, 6), .7, 'leather', -.5)
    hand_cover(ink, joints, R)


def prop_compass(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    cx = h + V(0, 3, 8)
    ink.plate([cx + V(x, 0, z) for x, z in circle(0, 0, 5.6, 5.6, 12)], 'gold', 2)
    ink.plate([cx + V(x, .4, z) for x, z in circle(0, 0, 4, 4, 12)], 'cream', 3, True)
    ink.plate([cx + V(0, .8, 4), cx + V(1.2, .8, 0), cx + V(0, .8, -4), cx + V(-1.2, .8, 0)], 'accent', 2, True)
    hand_cover(ink, joints, R)


def prop_bell(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    sw = math.sin(p['sway'])
    ink.plate([h + V(-3, 0, 4), h + V(3, 0, 4), h + V(6.4, 0, -2), h + V(-6.4, 0, -2)], 'gold', 2)
    ink.plate([h + V(-6.8, 0, -2), h + V(6.8, 0, -2), h + V(6.8, 0, -4), h + V(-6.8, 0, -4)], 'gold', 3, True)
    ink.plate([h + V(sw * 1.4 - 1, .4, -4), h + V(sw * 1.4 + 1, .4, -4), h + V(sw * 1.4, .4, -7)], 'metal', 2, True)
    hand_cover(ink, joints, R)


def prop_telescope(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    a, b = h + V(2, 2, 4), h + V(-12, 6, 26)
    line3(ink, a, b, 2.4, 'leather', -1.0)
    line3(ink, a + (b - a) * .55, b, 2.8, 'gold', -1.1)
    ink.bone(b - (b - a) * .03, b + (b - a) * .03, 3.3, 3.3, 'metal', -1.2, 3)
    hand_cover(ink, joints, R)


def prop_harpoon(ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    tip = h + V(0, 0, 40)
    line3(ink, h + V(0, 0, -16), tip, 1.3, 'wood')
    ink.plate([tip + V(-3, 0, 0), tip + V(0, 0, 11), tip + V(3, 0, 0)], 'metal', 3)
    for sx in (-1, 1):
        ink.plate([tip + V(sx * 1, 0, 2), tip + V(sx * 6, 0, -1), tip + V(sx * 2, 0, 5)], 'metal', 2)
    ink.ribbon([tip + V(0, 0, -6), tip + V(-4, 1, -14), tip + V(-2, 1, -22)], .4, .4, 'cream', 2, -.5, False)
    hand_cover(ink, joints, R)


PROPS.update(pearl=prop_pearl, orb=prop_orb, seed=prop_seed, grain=prop_grain, fan=prop_fan, key=prop_key, tablet=prop_tablet,
             waterjug=prop_waterjug, compass=prop_compass, bell=prop_bell, telescope=prop_telescope, harpoon=prop_harpoon)
HOLD.update(pearl=dict(handL=(-10, 12, 48)), orb=dict(handL=(-10, 12, 50)), seed=dict(handL=(-10, 12, 50)), grain=dict(handL=(-13, 7, 44)),
            fan=dict(handL=(-13, 8, 52)), key=dict(handL=(-12, 8, 46)), tablet=dict(handL=(-9, 14, 46), handR=(9, 14, 46)),
            waterjug=dict(handL=(-13, 6, 48)), compass=dict(handL=(-9, 12, 52)), bell=dict(handL=(-11, 9, 54)),
            telescope=dict(handL=(-10, 11, 50)), harpoon=dict(handL=(-12, 5, 46)))
TWO.add('tablet')


# ------------------------------------------------------------------------------------------------ merfolk
def merfolk_tail(ink, xf, p, c):
    sw = p['sway']
    tail = [xf((0, 0, 44)), xf((0, 1, 35)), xf((-1, 3, 24)), xf((-5, 5, 13)), xf((-12, 6, 7)), xf((-20, 5, 8)), xf((-25 - sw, 3, 16))]
    ink.ribbon(tail, 8.4, 2.6, 'tail', 2, -.5)
    ink.ribbon([xf((1.6, 3.4, 40)), xf((1, 4.6, 31)), xf((-1.6, 6, 21)), xf((-6, 7, 13)), xf((-12, 7.4, 9.4))], 3.2, 1.2, 'tail', 3, -.9, False)
    f0 = xf((-25 - sw, 3, 16))
    ink.plate([f0 + V(1, 0, -2), f0 + V(-5, 2, 9), f0 + V(-1.5, 2, 12), f0 + V(1, 2, 16), f0 + V(4, 2, 11), f0 + V(7, 2, 8)], 'tail', 1)
    ink.plate([f0 + V(1, .4, 0), f0 + V(-3, 2.4, 9), f0 + V(0, 2.4, 11), f0 + V(3, 2.4, 8)], 'tail', 3, True)


def fins(ink, head, c):
    H, hd = head['H'], head['hd']
    for sx in (-1, 1):
        ink.poly([H(sx * 9.6, 2), H(sx * 17, 6), H(sx * 15.4, -1), H(sx * 17.4, -5), H(sx * 9.4, -4)], c['tail'][1], hd - 6.2)
        ink.poly([H(sx * 11, 1), H(sx * 15.6, 3.6), H(sx * 14.6, -2), H(sx * 10.8, -3)], c['tail'][3], hd - 6.3, False)


def hat_crown(ink, head, c, p):
    H, hd = head['H'], head['hd']
    ink.poly([H(*q) for q in [(-10.6, 9), (-10.6, 15), (-6, 12.6), (-3, 19), (0, 13.4), (3, 19), (6, 12.6), (10.6, 15), (10.6, 9)]], c['trim'][2], hd - 7)
    for x in (-6, 0, 6):
        ink.poly([H(x + dx, 15.2 + dy) for dx, dy in circle(0, 0, 1.2, 1.2, 5)], c['accent'][3], hd - 7.2, False)


# ------------------------------------------------------------------------------------------------ ornaments (region material)
def _orn_wings(ink, xf, joints, R, p, c, head, d):
    """Large feathered wings behind the shoulders: three tiers of overlapping feathers fanning out from the shoulder, wider as the wearer flaps or talks."""
    spread = .5 + .5 * math.sin(p.get('flap', 0))
    for sx in (-1, 1):
        ru, rv = 8., 67.
        for tier, (n, length, tone, y) in enumerate(((7, 31, 1, -10.4), (6, 24, 2, -10.0), (5, 15, 3, -9.6))):
            for i in range(n):
                f = i / (n - 1)
                phi = math.radians(84 - f * (84 + 6 + 24 * spread))           # from straight up to out and a little down
                du, dv = math.cos(phi), math.sin(phi)
                nu, nv = -dv, du
                w = 3.9 if length > 20 else 3.3
                ln = length * (1 - .18 * f)
                base, mid, tip = (ru, rv), (ru + du * ln * .55, rv + dv * ln * .55), (ru + du * ln, rv + dv * ln)
                pts = [(base[0] + nu * w, base[1] + nv * w), (mid[0] + nu * w * 1.25, mid[1] + nv * w * 1.25), tip,
                       (mid[0] - nu * w * 1.25, mid[1] - nv * w * 1.25), (base[0] - nu * w, base[1] - nv * w)]
                ink.plate([xf((sx * u, y, v)) for u, v in pts], 'orn', tone, tier > 0)
        ink.plate([xf(q) for q in [(sx * 7, -9.4, 74), (sx * 15, -9.8, 72), (sx * 17, -9.8, 63), (sx * 7, -9.4, 59)]], 'orn', 3, True)


def _orn_coral(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for sx, base in ((1, (12, 8)), (-1, (-12, 6))):
        bx, by = base
        for dx, dy in ((0, 0), (3.2 * sx, 3.6), (-2.4 * sx, 5.4)):
            ink.poly([H(bx + dx - .9, by + dy), H(bx + dx + .9, by + dy), H(bx + dx * 1.3 + sx * 2, by + dy + 9), H(bx + dx * 1.3 + sx * 1, by + dy + 9.4)], c['orn'][2], hd - 7.3, False)
        ink.poly([H(bx + x, by + 10 + z) for x, z in circle(0, 0, 1.8, 1.8, 6)], c['orn'][3], hd - 7.4, False)
    ink.plate([xf(q) for q in [(8.6, 3, 69), (13, 0, 66), (12, -3, 71), (8.6, -3, 72)]], 'orn', 2)


def _star(ink, H, hd, x, y, r, c, dz=7.5):
    ink.poly([H(x + r * a, y + r * b) for a, b in [(0, 1), (.28, .28), (1, 0), (.28, -.28), (0, -1), (-.28, -.28), (-1, 0), (-.28, .28)]], c, hd - dz, False)


def _orn_stars(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for x, y, r in ((-17, 12, 3), (17, 14, 2.4), (-15, -4, 2), (16, -2, 3)):
        _star(ink, H, hd, x, y, r, c['orn'][3])
    for x, z in ((-4, 58), (3, 50), (-2, 42)):
        ink.plate([xf((x + dx, 4.95, z + dz)) for dx, dz in [(0, 1.6), (.5, .5), (1.6, 0), (.5, -.5), (0, -1.6), (-.5, -.5), (-1.6, 0), (-.5, .5)]], 'orn', 3, True)


def _orn_crystal(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for x, y, h in ((-13, 6, 11), (13, 8, 13), (-16, -1, 8)):
        ink.poly([H(x - 2, y), H(x, y + h), H(x + 2, y), H(x, y - 3)], c['orn'][2], hd - 7.3)
        ink.poly([H(x - .4, y), H(x, y + h), H(x + 2, y)], c['orn'][3], hd - 7.4, False)
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * 9, 0, 70), (sx * 12, 0, 80), (sx * 14, 0, 70), (sx * 11, 0, 64)]], 'orn', 2)


def _gear(ink, H, hd, cx, cy, r, mat, c, dz):
    n = 8
    pts = []
    for i in range(n):
        a0 = i / n * math.tau
        for da, rr in ((-.16, r), (-.08, r * 1.28), (.08, r * 1.28), (.16, r)):
            pts.append(H(cx + rr * math.cos(a0 + da * math.pi), cy + rr * math.sin(a0 + da * math.pi)))
    ink.poly(pts, c[mat][2], hd - dz)
    ink.poly([H(cx + x, cy + y) for x, y in circle(0, 0, r * .45, r * .45, 8)], c[mat][1], hd - dz - .1, False)


def _orn_gears(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    _gear(ink, H, hd, 0, 8, 10, 'orn', c, -1.5)
    _gear(ink, H, hd, 15, -4, 4.4, 'orn', c, 7.3)
    ink.plate([xf(q) for q in [(-9, -6, 68), (9, -6, 68), (9, -6, 54), (-9, -6, 54)]], 'orn', 1)


def _orn_mushroom(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for sx, (x, y, r) in ((1, (12, 10, 5)), (-1, (-13, 4, 3.6))):
        ink.poly([H(x - 1, y - 4), H(x + 1, y - 4), H(x + .8, y), H(x - .8, y)], c['cream'][2], hd - 7.3)
        ink.poly([H(x + q, y + .8 + w * .9) for q, w in [(-r, 0), (-r * .8, r * .7), (0, r * 1.1), (r * .8, r * .7), (r, 0)]], c['orn'][2], hd - 7.4)
        ink.poly([H(x + dx, y + 2 + dy) for dx, dy in circle(0, 0, 1, 1, 5)], c['cream'][3], hd - 7.5, False)
    ink.plate([xf(q) for q in [(9, 2, 70), (14, 0, 68), (13, -2, 72), (9, -2, 74)]], 'orn', 2)


def _orn_rings(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for tilt, rx, ry, m in ((.35, 21, 6, 3), (-.35, 17, 5, 2)):
        outer = circle(0, 8, rx, ry, 16)
        inner = circle(0, 8, rx - 1.6, ry - 1.2, 16)
        for i in range(16):
            j = (i + 1) % 16
            pts = [H(outer[i][0], outer[i][1] + tilt * outer[i][0] * .3), H(outer[j][0], outer[j][1] + tilt * outer[j][0] * .3),
                   H(inner[j][0], inner[j][1] + tilt * inner[j][0] * .3), H(inner[i][0], inner[i][1] + tilt * inner[i][0] * .3)]
            behind = outer[i][1] > 8
            ink.poly(pts, c['orn'][m], hd - (-1.8 if behind else 7.6), False)


def _orn_wheat(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for sx, x in ((1, 11), (-1, -12)):
        ink.poly([H(x - .5, 6), H(x + .5, 6), H(x * 1.2 + .5, 20), H(x * 1.2 - .5, 20)], c['orn'][1], hd - 7.3, False)
        for j in range(4):
            ink.poly([H(x * (1 + .04 * j) + dx, 12 + j * 2.6 + dy) for dx, dy in circle(0, 0, 1.4, 2, 6)], c['orn'][3], hd - 7.4, False)


def _orn_ribbons(ink, xf, joints, R, p, c, head, d):
    sw = p['sway']
    for sx in (-1, 1):
        pts = [xf((sx * 9, 0, 68)), xf((sx * 12, 2, 54)), xf((sx * 11 + sw, 4, 40)), xf((sx * 14 + sw * 2, 6, 28)), xf((sx * 11 + sw * 2, 7, 16))]
        ink.ribbon(pts, 1.6, 1.0, 'orn', 2, -1.4)


def _orn_orchid(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for cx, cy, r in ((10, 12, 3.4), (14, 6, 2.6)):
        for i in range(5):
            a = i / 5 * math.tau
            ink.poly([H(cx + r * .9 * math.cos(a) + x, cy + r * .9 * math.sin(a) + y) for x, y in circle(0, 0, r * .6, r * .6, 6)], c['orn'][2], hd - 7.4)
        ink.poly([H(cx + x, cy + y) for x, y in circle(0, 0, r * .4, r * .4, 6)], c['accent'][3], hd - 7.5, False)


def _orn_branches(ink, xf, joints, R, p, c, head, d, mat='wood'):
    H, hd = head['H'], head['hd']
    for sx in (-1, 1):
        for pts in ([(sx * 6, 14), (sx * 9, 18.4), (sx * 8, 22)], [(sx * 8, 17), (sx * 13, 19), (sx * 16, 21.6)], [(sx * 8, 15.4), (sx * 13, 13.4), (sx * 17, 14.6)]):
            for (a, b), (e, f) in zip(pts, pts[1:]):
                ink.poly([H(a - 1.1, b), H(a + 1.1, b), H(e + .7, f), H(e - .7, f)], c[mat][2], hd - 7.3, False)
        for x, y in ((sx * 8, 22), (sx * 16, 21.6), (sx * 17, 14.6)):
            ink.poly([H(x + dx, y + dy) for dx, dy in circle(0, 0, 2.2, 1.6, 6)], c['leaf'][2], hd - 7.4)


def _orn_antler(ink, xf, joints, R, p, c, head, d):
    _orn_branches(ink, xf, joints, R, p, c, head, d, mat='cream')


def _orn_leaf(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for x, y, a in ((11, 12, 0), (14, 8, 1), (-12, 10, 2)):
        ink.poly([H(x + 4 * math.cos(a) * u, y + 4 * math.sin(a) * u + w) for u, w in ((0, 0), (.5, 1.8), (1, 0), (.5, -1.8))], c['leaf'][2], hd - 7.4)


def _orn_veil(ink, xf, joints, R, p, c, head, d):
    sw = p['sway']
    ink.plate([xf(q) for q in [(-8, -5.4, 74), (8, -5.4, 74), (11 + sw, -9, 12), (-11 + sw, -9, 12)]], 'orn', 2)


def _orn_fur(ink, xf, joints, R, p, c, head, d):
    ink.bone(xf((-9.4, 0, 70)), xf((9.4, 0, 70)), 3.8, 3.8, 'orn', -1.5, 3)
    ink.bone(xf((-9.4, 1.4, 70)), xf((9.4, 1.4, 70)), 2.4, 2.4, 'orn', -1.6, 2)


def _orn_slate(ink, xf, joints, R, p, c, head, d):
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * 7, 1, 72), (sx * 14, 0, 70), (sx * 15, 0, 62), (sx * 9, 1, 60)]], 'orn', 2)
        ink.plate([xf(q) for q in [(sx * 8, 1.2, 70), (sx * 13, 1, 68), (sx * 13.4, 1, 64)]], 'orn', 3, True)


def _orn_season(ink, xf, joints, R, p, c, head, d):
    H, hd = head['H'], head['hd']
    for i in range(9):
        a = math.pi * (.1 + i / 8 * .8)
        ink.poly([H(15 * math.cos(a) + x, 9 + 11 * math.sin(a) + 3 + y) for x, y in circle(0, 0, 1.8, 1.8, 5)], c['orn'][2 + i % 2], hd - 7.5, False)


def _orn_rope(ink, xf, joints, R, p, c, head, d):
    ink.ribbon([xf((-8, 4.6, 68)), xf((0, 5.2, 56)), xf((8.6, 5.2, 44))], 1.5, 1.5, 'orn', 2, -1.5)
    ink.ribbon([xf((-7, 4.8, 66)), xf((1, 5.4, 55)), xf((9, 5.4, 43))], .7, .7, 'orn', 3, -1.6, False)


def _orn_chains(ink, xf, joints, R, p, c, head, d):
    for sx in (-1, 1):
        for i in range(7):
            ink.plate([xf((sx * 8 + dx * .6, 4.9, 40 - i * 3.4 + dz * .6)) for dx, dz in circle(0, 0, 1.4, 1.7, 6)], 'metal', 2 + (i % 2), True)
    ink.ribbon([xf((-8, 4.8, 70)), xf((0, 5.2, 58)), xf((8, 5.2, 46))], .8, .8, 'metal', 2, -1.5)


def _orn_braid(ink, xf, joints, R, p, c, head, d):
    for i in range(6):
        ink.plate([xf((8.6 + dx * .5, 3 + dy * .1, 70 - i * 3 + dz)) for dx, dy, dz in [(0, 0, 0), (2, 0, .8), (2, 0, -1.2), (0, 0, -2)]], 'orn', 2 + i % 2, True)


ORNAMENTS = dict(wings=_orn_wings, coral=_orn_coral, stars=_orn_stars, crystal=_orn_crystal, gears=_orn_gears, mushroom=_orn_mushroom, rings=_orn_rings,
                 wheat=_orn_wheat, ribbons=_orn_ribbons, orchid=_orn_orchid, branches=_orn_branches, antler=_orn_antler, leaf=_orn_leaf, veil=_orn_veil,
                 fur=_orn_fur, slate=_orn_slate, season=_orn_season, rope=_orn_rope, chains=_orn_chains, braid=_orn_braid)
ORN_COLOR = dict(wings='#eef6ff', coral='#ff8f7a', stars='#ffe58a', crystal='#9fe8ff', gears='#d8a85a', mushroom='#e86a8a', rings='#f0d070', wheat='#e8c860',
                 ribbons='#ff9ab0', orchid='#d890e8', branches='#6a4a30', antler='#cfc0a0', leaf='#6fb878', veil='#9fe8dc', fur='#f4f8ff', slate='#8a94a2',
                 season='#e8c860', rope='#c8a870', chains='#8a94a8', braid='#c8a870')


def treefolk(ink, xf, joints, R, p, c, head):
    """Bark and moss over the player body: root toes, bark plates and moss on the shoulders, cracks on the cheeks, a branch crown."""
    H, hd = head['H'], head['hd']
    for key in 'LR':
        j = joints[key]
        a = j['ankle'] + V(0, .6, -1.2)
        for dx, dy in ((-4, 2), (0, 3.2), (4, 2), (-3, -2.6), (3, -2.6)):
            ink.bone(a + V(dx * .2, dy * .2, 0), a + V(dx, dy, -.2), 1.4, .5, 'wood', -.4, 1)
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * 7, 1, 72), (sx * 13.4, 0, 70), (sx * 14, 0, 64), (sx * 8.4, 1, 62)]], 'wood', 2)
        ink.plate([xf(q) for q in [(sx * 7.6, 1.2, 72.4), (sx * 12, 1, 71), (sx * 11, 1, 68), (sx * 8, 1.2, 68.6)]], 'leaf', 2, True)
        j = joints['L' if sx > 0 else 'R']
        ink.bone(j['elbow'] + (j['hand'] - j['elbow']) * .15, j['elbow'] + (j['hand'] - j['elbow']) * .6, 2.3, 2.0, 'wood', -1.2, 1)
    if head['front'] > -.4:
        for sx in (-1, 1):
            ink.poly([H(sx * 6.4, 2), H(sx * 7.4, 1.4), H(sx * 5.6, -3.6), H(sx * 4.8, -3)], c['wood'][0], hd - 5.9, False)
            ink.poly([H(sx * 7, -3.6), H(sx * 8, -4.2), H(sx * 6.2, -8), H(sx * 5.4, -7.4)], c['wood'][0], hd - 5.9, False)
    _orn_branches(ink, xf, joints, R, p, c, head, {})
    ink.plate([xf(q) for q in [(-5, 4.8, 58), (-1, 4.8, 60), (-2, 4.9, 52), (-6, 4.9, 53)]], 'leaf', 2, True)


def render(key, clip, k):
    d = DESIGNS[key]
    name, child = d['arch'], d['arch'] == 'child'
    female = bool(d.get('female'))
    set_frame(CHILD_PX if child else ADULT_PX, female)
    c_ = materials(d)
    palette, color = cc.palette_of(c_)
    chat = dict(color, cloth=color['hatc']) if d.get('hatc') else color
    facing = ('S', 'SE', 'S')[[x for x, _ in CLIPS].index(clip)]
    psi = rig.psi_for(facing)
    p = core.pose(clip, k, {})
    prop = d['prop']
    if clip != 'walk' or prop in WALK_HOLD:
        p.update(HOLD.get(prop, {}))
    if prop in TWO and clip == 'walk':
        p.update(HOLD[prop])
    if d['build'] == 'stooped':
        p['lean'] += 10
    if clip == 'talk' and prop not in TWO:
        side = 'handR' if prop != 'palette' else 'handL'
        p[side] = (15, 12 + 3 * math.sin(k / 6 * math.tau), 66)
    if d.get('hover'):
        p['flap'] = k / (8 if clip == 'walk' else 6) * math.tau * (2 if clip == 'walk' else 1)
        rz = p['root'][2] + 3.4 + .9 * math.sin(p['flap'])
        p['root'] = (p['root'][0], p['root'][1], rz)
        p['footL'], p['footR'] = (-4, -1, 5), (4, 2, 4)
    if d.get('tail'):
        for f in ('footL', 'footR'):
            p[f] = (-3 if f == 'footL' else 3, 0, 4)
        p['lean'] = min(p['lean'], 6)
    R, xf, joints = cc.skeleton(p)
    ink = cc.Ink(psi, color)
    head = cc.head_frame(ink, xf, psi, p, turn=.6)
    if child:
        hc, old = head['H'](0, 0), head['H']
        head['H'] = lambda x, y, old=old, hc=hc: hc + (old(x, y) - hc) * 1.28
    spec = dict(OUTFITS[name], pants='pants')
    if d.get('tail'):
        spec.update(legs=False, boots=None)
        if spec.get('skirt'):
            spec['skirt'] = (max(spec['skirt'][0], 38), spec['skirt'][1] * .8, spec['skirt'][2] * .8)
    outfit(ink, xf, joints, R, p, color, spec)
    if d.get('tail'):
        merfolk_tail(ink, xf, p, color)
    extras(name, ink, xf, joints, R, p, color, head)
    if d.get('tree'):
        treefolk(ink, xf, joints, R, p, color, head)
    cc.face(ink, head, p, lashes=1.0 if child else (1.3 if female else .5))
    if p.get('mouth'):
        H, hd = head['H'], head['hd']
        nx = head['side'] * 5
        ink.poly([H(nx - 1.8, -6.6), H(nx + 1.8, -6.6), H(nx + 1.2, -9.6), H(nx - 1.2, -9.6)], color['mouth'][0], hd - 5.85, False)
    if d['hat'] != 'hood':
        hair(ink, head, color, d['hair'], p, low=d['hat'] in ('cap',))
    elif head['front'] > -.4:
        H, hd = head['H'], head['hd']
        ink.poly([H(*q) for q in [(-8.4, 9), (0, 11.4), (8.4, 9), (9, 6.6), (0, 8.6), (-9, 6.6)]], color['hair'][1], hd - 6, False)
    if name in ('elder', 'scholar') and head['front'] > -.4:
        H, hd = head['H'], head['hd']
        for sx in (-1, 1):
            ex = sx * 4 * max(.28, head['front']) + head['side'] * 3.3
            outer, inner = circle(ex, -1, 3.8, 3.4, 12), circle(ex, -1, 2.9, 2.5, 12)
            for i in range(12):      # a thin rim, so the eye stays visible behind the lens
                j = (i + 1) % 12
                ink.poly([H(*outer[i]), H(*outer[j]), H(*inner[j]), H(*inner[i])], color['trim'][2], hd - 6.5, False)
        ink.poly([H(-1.6, -.4), H(1.6, -.4), H(1.6, .4), H(-1.6, .4)], color['trim'][1], hd - 6.5, False)
    if d.get('tail'):
        fins(ink, head, color)
    hat(ink, head, chat, d['hat'], p)
    PROPS[prop](ink, xf, joints, R, p, color)
    if d.get('ornament'):
        ORNAMENTS[d['ornament']](ink, xf, joints, R, p, color, head, d)
    idx, z = ink.resolve()
    pal = np.array([tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,) if len(h) == 7 else (0, 0, 0, 0) for h in palette], np.uint8)
    pal[0] = (0, 0, 0, 0)
    return Image.fromarray(pal[idx], 'RGBA'), idx, palette


WALK_HOLD = ('hammer', 'kite', 'bow', 'spear', 'staff', 'lantern', 'cane', 'saw', 'reins', 'lyre', 'scales', 'bottle', 'mug', 'fish', 'spool', 'alembic', 'trumpet',
             'pearl', 'orb', 'seed', 'waterjug', 'fan', 'key', 'compass', 'bell', 'telescope', 'harpoon', 'grain')


PANTS = dict(sentinel='#3a4560', physician='#7a8f9a', smith='#4a3f5c', baker='#8a6a4a', innkeeper='#5a3f4a', merchant='#4a3a66', ranger='#4a5a3f', scholar='#3a3a5c',
             herald='#3a3a4a', gardener='#6a5a3a', fisher='#3a4a5a', weaver='#5a3a5a', courier='#5a4a3a', pilgrim='#5a4e3e', bard='#4a3a66', child='#6a4a6a', elder='#4a5566',
             painter='#5a4636', carpenter='#5a4636', alchemist='#3a5a55', steward='#4a3a52', stablehand='#5a4630', lamplighter='#3a4558', banker='#3a4558')
ACCENT = dict(sentinel='#d8a040', physician='#c2584f', smith='#7fb8d0', baker='#e8c86a', innkeeper='#e8d8b0', merchant='#e0a040', ranger='#c9433f', scholar='#e0c070', herald='#f0c050',
              gardener='#e56f8a', fisher='#cfe1ec', weaver='#e8c25a', courier='#c9433f', pilgrim='#a05a3a', bard='#f0c050', child='#7e9fe0', elder='#c25a4a',
              painter='#d65a6a', carpenter='#d0a05a', alchemist='#7fe0c0', steward='#d8b0e0', stablehand='#a05a3a', lamplighter='#f0b040', banker='#d8b040')
TRIM = dict(sentinel='#e0b85c', child='#f2d27a')


# ------------------------------------------------------------------------------------------------ the registry: 24 general + 140 special designs
def _build_registry():
    out, by_notes = {}, {}
    for name, spec in SPECS.items():
        by_notes[spec['notes']] = name
        out[name] = dict(arch=name, name=spec['name'], general=True, prop=spec['prop'], build=spec['build'], hat=spec['hat'], hair=spec['hair'], coat=spec['coat'],
                         skin=skin_of(spec), hairc=hair_of(spec), pants=PANTS.get(name, '#4a3f5c'), accent=ACCENT.get(name, '#7fb8d0'), trim=TRIM.get(name, '#e0b85c'),
                         hatc=None, tail=None, ornament=None, female=False)
    for key, v in PLAN['designs'].items():
        if v.get('general'):
            continue
        arch = by_notes[v['notes']]
        ident = v.get('identity', {})
        merfolk = ident.get('species') == 'merfolk' or v['build'] == 'merfolk'
        orn = v.get('ornament')
        out[key] = dict(arch=arch, name=v['name'], general=False, prop=v['prop'], build=v['build'], hat=v['hat'], hair=v['hair'], coat=v['coat'],
                        skin=ident.get('skin', skin_of(v)), hairc=ident.get('hair', hair_of(v)), pants=PANTS.get(arch, '#4a3f5c'), accent=ACCENT.get(arch, '#7fb8d0'),
                        trim=TRIM.get(arch, '#e0b85c'), hatc=ident.get('hatColor'), tail=ident.get('tail') if merfolk else None, ornament=orn,
                        orn=(v['coat'] if orn == 'season' else ORN_COLOR.get(orn, '#e0b85c')) if orn else None, female=bool(ident.get('female')))
    bark, leafc = ['#b08c62', '#a07c54', '#bd9a6e', '#946f4a'], ['#5f9a4a', '#4f8a3e', '#79b25a', '#6aa04a']
    tree = {k for k in out if k.startswith('special_heart_')} | {'special_travel_veyrroot'}
    for i, key in enumerate(sorted(tree)):
        out[key].update(tree=True, skin=bark[i % 4], hairc=leafc[i % 4], ornament=None, orn='#79b25a')
    for key, d in out.items():
        if d.get('ornament') == 'wings':
            d.update(hover=True, orn=_blend(d['coat'], '#ffffff', .62))
    return out


def _blend(a, b, t):
    ra, rb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * t):02x}' for x, y in zip(ra, rb))


DESIGNS = _build_registry()
GENERAL = list(SPECS)
SPECIAL = [k for k in DESIGNS if k not in SPECS]


def pick(args):
    """Design keys for CLI args: names, 'general', 'special', 'all', or a special group prefix such as 'nacre'."""
    if not args:
        return GENERAL
    out = []
    for a in args:
        if a == 'general':
            out += GENERAL
        elif a == 'special':
            out += SPECIAL
        elif a == 'all':
            out += list(DESIGNS)
        elif a in DESIGNS:
            out.append(a)
        else:
            out += [k for k in SPECIAL if k.startswith('special_' + a)]
    return out


def check(names):
    bad = 0
    for name in names or GENERAL:
        for clip, n in CLIPS:
            sigs = set()
            for k in range(n):
                img, idx, _ = render(name, clip, k)
                sigs.add(idx.tobytes())
                a = np.array(img)[..., 3] > 0
                ys, xs = np.where(a)
                if core.clipped(idx) or ys.min() < 1 or ys.max() > 94 or xs.min() < 1 or xs.max() > 94:
                    print('CLIP', name, clip, k, (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())))
                    bad += 1
            if len(sigs) < 3:
                print('STATIC', name, clip, len(sigs))
                bad += 1
    print('check done, problems:', bad)


TAG = 'general'


def preview(out, names):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    global TAG
    TAG = sys.argv[3] if len(sys.argv) > 3 else 'general'
    names = names or GENERAL
    S, cols, cellw = 3, 6, 96 * 3
    bg = (34, 48, 64, 255)
    for part in range(0, len(names), cols * 2):
        grp = names[part:part + cols * 2]
        sheet = Image.new('RGBA', (cols * 96 * S, ((len(grp) + cols - 1) // cols) * (96 * S + 16)), bg)
        dr = ImageDraw.Draw(sheet)
        for i, name in enumerate(grp):
            img, idx, _ = render(name, 'idle', 0)
            if core.clipped(idx):
                print('CLIPPED', name)
            x, y = (i % cols) * 96 * S, (i // cols) * (96 * S + 16)
            sheet.alpha_composite(img.resize((96 * S, 96 * S), Image.NEAREST), (x, y + 14))
            dr.text((x + 4, y + 2), name.replace('special_', ''), fill='white')
        sheet.save(out / f'npcp-{TAG}-{part // (cols * 2) + 1}.png')
    print('wrote', out)


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'check':
        check(pick(sys.argv[2:]))
    elif len(sys.argv) >= 3 and sys.argv[1] == 'preview':
        preview(sys.argv[2], pick(sys.argv[3:]))
    else:
        print(__doc__)
