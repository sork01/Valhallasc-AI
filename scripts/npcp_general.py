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
    m['hair'] = ramp(s['hair'], AMOUNTS['hair'])
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
        P([(-1.6, 20), (1.6, 20), (2.6, 24), (0, 26.4), (-2.6, 24)], 'trim', 2, 7.2)
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


def render(name, clip, k):
    spec = SPECS[name]
    child = name == 'child'
    set_frame(CHILD_PX if child else ADULT_PX, False)
    c_ = materials(dict(spec, skin=skin_of(spec), hair=hair_of(spec), pants=PANTS.get(name, '#4a3f5c'), accent=ACCENT.get(name, '#7fb8d0'), trim=TRIM.get(name, '#e0b85c')))
    palette, color = cc.palette_of(c_)
    facing = ('S', 'SE', 'S')[[x for x, _ in CLIPS].index(clip)]
    psi = rig.psi_for(facing)
    p = core.pose(clip, k, {})
    p.update(HOLD.get(spec['prop'], {}) if clip != 'walk' or spec['prop'] in ('hammer', 'kite', 'bow', 'spear', 'staff', 'lantern', 'cane', 'saw', 'reins', 'lyre', 'scales', 'bottle', 'mug', 'fish', 'spool', 'alembic', 'trumpet') else {})
    if spec['prop'] in TWO and clip == 'walk':
        p.update(HOLD[spec['prop']])
    if spec['build'] == 'stooped':
        p['lean'] += 10
    if clip == 'talk' and spec['prop'] not in TWO:
        side = 'handR' if spec['prop'] != 'palette' else 'handL'
        p[side] = (15, 12 + 3 * math.sin(k / 6 * math.tau), 66)
    R, xf, joints = cc.skeleton(p)
    ink = cc.Ink(psi, color)
    head = cc.head_frame(ink, xf, psi, p, turn=.6)
    if child:
        hc, old = head['H'](0, 0), head['H']
        head['H'] = lambda x, y, old=old, hc=hc: hc + (old(x, y) - hc) * 1.28
    outfit(ink, xf, joints, R, p, color, dict(OUTFITS[name], pants='pants'))
    extras(name, ink, xf, joints, R, p, color, head)
    cc.face(ink, head, p, lashes=1.0 if child else .5)
    if p.get('mouth'):
        H, hd = head['H'], head['hd']
        nx = head['side'] * 5
        ink.poly([H(nx - 1.8, -6.6), H(nx + 1.8, -6.6), H(nx + 1.2, -9.6), H(nx - 1.2, -9.6)], color['mouth'][0], hd - 5.85, False)
    if spec['hat'] != 'hood':
        hair(ink, head, color, spec['hair'], p, low=spec['hat'] in ('cap',))
    elif head['front'] > -.4:
        H, hd = head['H'], head['hd']
        ink.poly([H(*q) for q in [(-8.4, 9), (0, 11.4), (8.4, 9), (9, 6.6), (0, 8.6), (-9, 6.6)]], color['hair'][1], hd - 6, False)
    if spec['hair'] == 'beard' and spec['hat'] == 'hood':
        hair_beard = None
    if name in ('elder', 'scholar') and head['front'] > -.4:
        H, hd = head['H'], head['hd']
        for sx in (-1, 1):
            ex = sx * 4 * max(.28, head['front']) + head['side'] * 3.3
            outer, inner = circle(ex, -1, 3.8, 3.4, 12), circle(ex, -1, 2.9, 2.5, 12)
            for i in range(12):      # a thin rim, so the eye stays visible behind the lens
                j = (i + 1) % 12
                ink.poly([H(*outer[i]), H(*outer[j]), H(*inner[j]), H(*inner[i])], color['trim'][2], hd - 6.5, False)
        ink.poly([H(-1.6, -.4), H(1.6, -.4), H(1.6, .4), H(-1.6, .4)], color['trim'][1], hd - 6.5, False)
    hat(ink, head, color, spec['hat'], p)
    PROPS[spec['prop']](ink, xf, joints, R, p, color)
    if spec['hair'] == 'beard' and head['front'] > -.4:
        pass
    idx, z = ink.resolve()
    pal = np.array([tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,) if len(h) == 7 else (0, 0, 0, 0) for h in palette], np.uint8)
    pal[0] = (0, 0, 0, 0)
    return Image.fromarray(pal[idx], 'RGBA'), idx, palette


PANTS = dict(sentinel='#3a4560', physician='#7a8f9a', smith='#4a3f5c', baker='#8a6a4a', innkeeper='#5a3f4a', merchant='#4a3a66', ranger='#4a5a3f', scholar='#3a3a5c',
             herald='#3a3a4a', gardener='#6a5a3a', fisher='#3a4a5a', weaver='#5a3a5a', courier='#5a4a3a', pilgrim='#5a4e3e', bard='#4a3a66', child='#6a4a6a', elder='#4a5566',
             painter='#5a4636', carpenter='#5a4636', alchemist='#3a5a55', steward='#4a3a52', stablehand='#5a4630', lamplighter='#3a4558', banker='#3a4558')
ACCENT = dict(sentinel='#d8a040', physician='#c2584f', smith='#7fb8d0', baker='#e8c86a', innkeeper='#e8d8b0', merchant='#e0a040', ranger='#c9433f', scholar='#e0c070', herald='#f0c050',
              gardener='#e56f8a', fisher='#cfe1ec', weaver='#e8c25a', courier='#c9433f', pilgrim='#a05a3a', bard='#f0c050', child='#7e9fe0', elder='#c25a4a',
              painter='#d65a6a', carpenter='#d0a05a', alchemist='#7fe0c0', steward='#d8b0e0', stablehand='#a05a3a', lamplighter='#f0b040', banker='#d8b040')
TRIM = dict(sentinel='#e0b85c', child='#f2d27a')


def check(names):
    bad = 0
    for name in names or list(SPECS):
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


def preview(out, names):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    names = names or list(SPECS)
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
            dr.text((x + 4, y + 2), name, fill='white')
        sheet.save(out / f'npcp-general-{part // (cols * 2) + 1}.png')
    print('wrote', out)


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'check':
        check(sys.argv[2:])
    elif len(sys.argv) >= 3 and sys.argv[1] == 'preview':
        preview(sys.argv[2], sys.argv[3:])
    else:
        print(__doc__)
