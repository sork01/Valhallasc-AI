#!/usr/bin/env python3
"""Rimeveil Glacier's three elites (zone shapes pilot): native PixelFlow sources, per-kind frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye face. Each kind has its own face and silhouette:
  hoarhorn   a mammoth the size of a barn under a shaggy blue-grey coat, ridged with ice shards, its tusks grown into a tangle of icicles (one snapped off),
             a heavy brow over one small red eye, the trunk lashing. Rears, then slams the head down. Dies: the knees go, the coat settles, the ice cracks.
  whitewail  a drowned-in-snow climber turned wraith: a long gaunt body in a torn white shroud, hair streaming backwards, black hollows for eyes with a pinprick
             of cyan in each, the mouth torn wide in a scream. Hovers; arms thrown wide for the shriek. Dies: folds into its own shroud on the snow.
  shardback  a glacier crab: a low domed carapace of blue crystal plates with tall shards down the spine, two stalked red eyes, two claws as big as the body.
             Raises both claws, then smashes them down together. Dies: the claws drop, the plates fall away and the legs splay flat.
Eight distinct attack and death frames each. The manifest is client/assets/rimeelites.txt. Drawing helpers come from the Lapis redo.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image

import kindframe
import lapis_slime_redraw as L
from lapis_slime_redraw import (Rig, BasePainter, OUTLINE, BONE, CRIMSON, GOLD, EYE_WHITE, PEARL, clamp01, curves, dying, settle,
                                polar, cross_eye, mix, mixp, sm, bez, taper, fang, dust, old)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/rime-elites'
REGISTRY = ROOT / 'scripts/rime_elite_sources.txt'
MANIFEST = ASSETS / 'rimeelites.txt'
PREFIX = 'valhallasc_rime_elite_'
KINDS = ['hoarhorn', 'whitewail', 'shardback']
KIND_FRAMES = dict(hoarhorn=(176, 106, 69, 99), whitewail=(138, 154, 61, 148), shardback=(168, 112, 64, 104))
FLYING = ('whitewail',)
_mine = [
    '#06182a', '#0f3a66', '#2a72b0', '#6cc0ee', '#d4f4ff',   # ICE (crystal shell, tusks, shards)
    '#161e2c', '#34445c', '#667c9a', '#a8bdd4', '#eaf3fa',   # WOOL (mammoth coat)
    '#080e1c', '#1c284a', '#42588a', '#86a8d4', '#e0f0ff',   # SHROUD (the wraith)
    '#2a0a12', '#6a1420', '#c02a30', '#f06a50', '#ffd0a0',   # BLOOD (eyes, a gaping mouth)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
ICE, WOOL, SHROUD, BLOOD = [_i[5 * k:5 * k + 5] for k in range(4)]


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kindframe.check_frame(*KIND_FRAMES[kind])
        self.S = 1.
        self.im = Image.new('P', (self.w, self.h), 0)
        from PIL import ImageDraw
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax + dx

    def pos(self, x, y):
        return round(self.cx + x), round(self.ay - y)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width)))


def slit_eye(r, x, y, w=4.2, shut=False, glow=None):
    glow = glow or BLOOD
    if shut:
        r.line([(x - w, y - .6), (x + w, y + .6)], OUTLINE, 2)
        return
    r.poly([(x - w, y - .6), (x - w * .1, y + 1.8), (x + w, y - 1.5), (x + w * .2, y - 2.6)], glow[3], outline=OUTLINE)
    r.ellipse(x + w * .2, y - .6, 1, 1.3, OUTLINE)
    r.poly([(x - w - 1.5, y + 2.8), (x + w + 1, y - .6), (x + w + 1, y + 1.8), (x - w - .5, y + 4.4)], OUTLINE)


# ---- Hoarhorn --------------------------------------------------------------------------------------------------------
def hoarhorn(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    lie = sm(clamp01((dn - .25) * 1.4))
    a = Painter('hoarhorn', st * 6 - w * 6 + recoil + lie * 3)
    base = 38 + bob * .5 - lie * 12 - fall * 2 + w * 3 - st * 1
    tilt = w * .12 - st * .05 - lie * .05
    r = Rig(a, -16, base - 10, tilt)

    def leg(x, p0, front):
        sw = math.sin(ph + p0) * 6 if clip == 'walk' else 0
        lift = max(0, math.cos(ph + p0)) * 3 if clip == 'walk' else 0
        hip = (x, base - 8)
        foot = mixp((x + sw, 3 + lift), (x + (13 if front else -13), 4), lie)
        knee = mixp((x + sw * .4, base - 20), (x + (9 if front else -9), 11), lie)
        a.limb([hip, knee, foot], [WOOL[0], WOOL[1], WOOL[2], WOOL[2], WOOL[3]], 12)
        a.ellipse(foot[0] + 2, foot[1] - 1, 9, 3.6, WOOL[0])
        a.ellipse(foot[0] + 2, foot[1], 7, 2.4, WOOL[2])

    leg(-30, 1.6, False)
    leg(14, 0, True)
    # a ragged tail of coat and a back covered in ice shards
    sweep = math.sin(ph) * 3 if clip != 'die' else 0
    tail = bez((-40, base + 2), (-52, base - 6 + sweep), (-56, base - 18 - lie * 8), 6)
    taper(a, [r.t(*p) for p in tail], [WOOL[0], WOOL[0], WOOL[1], WOOL[1], WOOL[2]], 7, 2)
    # the body: a hill of coat, the hump, a jagged skirt of fur hanging off the belly
    r.ball(-8, base, 36, 27, WOOL, -.1)
    r.ball(-20, base + 15, 20, 16, WOOL)
    for k in range(10):
        x = -40 + k * 7.6
        r.fang(x, base - 18 + abs(k - 4.5) * .8, (12 + (k % 3) * 3) * (1 - lie * .8), 7, -1.57 + math.sin(k * 2.1) * .12, WOOL)
    shards = (-36, -27, -18, -9, 0, 9, 18)
    for k, x in enumerate(shards):
        cold = clamp01(dn * 1.6 - k * .1)
        r.fang(x, base + 24 - abs(k - 2) * 1.6 + (k % 2), 13 + (k % 3) * 4 - cold * 5, 6.6, 1.45 + (k - 3) * .1 - cold * .3, ICE)
    leg(-16, 3.2, False)
    leg(28, 4.7, True)
    # the head: huge, low-slung, a trunk, a brow like a ledge, ear flapped back, tusks grown into a tangle of icicles
    hd = Rig(a, 20, base + 6, tilt + w * .2 - st * .1 - lie * .1)
    T = lambda x, y: r.t(*hd.t(x, y))
    hx, hy = 40, base + 6 - lie * 2
    # ears and neck mass
    a.ball(*T(24, hy + 6), 11, 14, WOOL, tilt)
    a.ball(*T(hx, hy), 18, 19, WOOL, tilt - .1)
    a.ball(*T(hx - 10, hy + 12), 14, 12, WOOL)
    # trunk: a thick rope of coat, swinging
    swing = math.sin(ph * 1.3) * 5 * (1 if clip != 'die' else 1 - lie)
    trunk = bez((hx + 12, hy - 2), (hx + 22 + swing + st * 12 + w * 6, hy - 18 + w * 22 + st * 4 + lie * 8), (hx + 16 + swing * 1.6 - st * 6, hy - 38 + lie * 30 + w * 10 + st * 20), 8)
    taper(a, [T(*p) for p in trunk], [WOOL[0], WOOL[1], WOOL[2], WOOL[2], WOOL[3]], 12, 5)
    a.ball(*T(*trunk[-1]), 3.4, 3, WOOL)
    # tusks: two long curves with icicles hanging from them; the near one snapped off
    big = bez((hx + 6, hy - 8), (hx + 36, hy - 24 + lie * 14 + st * 6), (hx + 40, hy + 10 + w * 10 + st * 4 + lie * 6), 9)
    taper(a, [T(*p) for p in big], ICE, 8, 2.2)
    for k, p in enumerate(big[2:8]):
        fang(a, *T(*p), 8 + (k % 3) * 3, 3.6, -1.57 + k * .22 + st * .4, ICE)
    small = bez((hx + 2, hy - 12), (hx + 24, hy - 30 + lie * 12 + st * 8), (hx + 26, hy - 18 + lie * 8 + st * 6), 5)
    taper(a, [T(*p) for p in small], ICE, 7, 3.6)
    a.poly([T(*small[-1]), T(small[-1][0] + 5, small[-1][1] + 4), T(small[-1][0] + 2, small[-1][1] - 5), T(small[-1][0] + 7, small[-1][1] - 2)], ICE[3], outline=OUTLINE)
    # the face: a ledge of brow, one small red eye sunk under it
    a.poly([T(hx + 3, hy + 9), T(hx + 24, hy + 15), T(hx + 22, hy + 21), T(hx - 2, hy + 18)], WOOL[0], outline=OUTLINE)
    ex, ey = T(hx + 12, hy + 7)
    slit_eye(a, ex, ey, 3.8, shut=dying(clip, n), glow=BLOOD)
    if clip == 'attack' and n in (4, 5):                     # ice chips thrown off the tusks on the slam
        for k in range(5):
            a.ball(*T(hx + 40 + k * 4, hy - 14 + (k % 2) * 8 - k * 2), 2.6 - k * .3, 2.2 - k * .25, ICE)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, 62 + k * 8, 5 + (k % 2) * 4, 3.2 - k * .5, PEARL)
    if dn > .45:                                            # the ice cracks as it dies
        for k in range(3):
            a.line([r.t(-30 + k * 16, base + 20), r.t(-26 + k * 16, base + 10), r.t(-32 + k * 16, base + 4)], ICE[4], 1)
    return a


# ---- Whitewail -------------------------------------------------------------------------------------------------------
def whitewail(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.05)
    sink = sm(clamp01((dn - .15) * 1.25))
    a = Painter('whitewail', st * 7 - w * 4 + recoil)
    hover = 72 + math.sin(ph * 1.6) * 3 + w * 6 - st * 5
    y0 = mix(hover, 22, sink)
    H = 1 - sink * .74                                  # the figure folds down into its own shroud on the snow
    Z = lambda dy: y0 + dy * H
    lean = -st * .22 + w * .12 - sink * .14
    r = Rig(a, 0, y0, lean)
    scream = clamp01(.15 + w * .5 + st * .9) if clip != 'die' else clamp01(.5 - dn * .5)
    head = (6, Z(50))
    # hair first: long pale strands streaming back and up, then falling when it dies
    for k in range(7):
        lift = (k - 3) * .2
        pts = [r.t(head[0] - 4, head[1] + 4 - k * .8)]
        for s in range(1, 6):
            wav = math.sin(ph * 1.4 + k + s * .9) * (3 + s) * (1 - fall)
            pts.append(r.t(head[0] - 4 - s * 9 - st * 4 + sink * s * 2, head[1] + 4 - k * 1.5 + lift * s * 4 + wav - (s * s * 1.4) * fall * .4 - s * 1.2 * sink))
        taper(a, pts, SHROUD, 3.4, .8)
    # the shroud: a long torn gown from the shoulders, flaring out; its hem is a row of tatters that stream backwards
    flare = 20 + w * 4 + st * 7 + sink * 16
    body = [(-9, Z(40)), (-flare, Z(-26)), (flare * .55, Z(-30)), (13, Z(40))]
    r.poly(body, SHROUD[1], outline=OUTLINE)
    r.poly([(-6, Z(38)), (-flare * .62, Z(-22)), (flare * .3, Z(-24)), (4, Z(38))], SHROUD[2])
    r.poly([(-2, Z(36)), (-flare * .3, Z(-18)), (2, Z(-20)), (6, Z(36))], SHROUD[3])
    for k in range(7):
        x = -flare + k * (flare * 1.55 / 6)
        wave = math.sin(ph * 1.7 + k * 1.3) * 5
        ln = (10 + (k % 3) * 6) * (1 - sink * .3)
        r.fang(x, Z(-24), ln, 7, -1.57 - .45 + wave * .03 + st * .2 + sink * (k - 3) * .12, SHROUD)
    # arms: thin and far too long, thrown wide for the scream, clawed
    for far in (True, False):
        sx, sy = (-2, Z(36)) if far else (9, Z(37))
        up = w * 1.0 - st * .1
        elbow = polar(sx, sy, -1.9 + (.5 if far else 0) + up * 1.5 + st * .8, 17 * (1 - sink * .35))
        hand = polar(*elbow, -1.2 + (.8 if far else -.1) + up * 2.2 - st * .4 + fall * 1.8 + math.sin(ph) * .08, (19 + st * 4) * (1 - sink * .35))
        col = SHROUD if far else [SHROUD[0], SHROUD[0], SHROUD[1], SHROUD[2], SHROUD[3]]
        a.limb([r.t(sx, sy), r.t(*elbow), r.t(*hand)], col, 3.6)
        for off in (-.5, -.1, .3, .7):
            r.fang(hand[0], hand[1], 8 + (off > 0) * 2, 2.6, math.atan2(hand[1] - elbow[1], hand[0] - elbow[0]) + off, BONE)
    # the head: a long gaunt skull, hollow sockets, a mouth torn open
    hx, hy = head
    a.ball(*r.t(hx, hy), 11.5, 14.5, [SHROUD[0], SHROUD[2], SHROUD[3], SHROUD[4], PEARL[4]], lean - .1)
    if dn < .8:
        for ox in (2.6, 9.4):
            a.poly([r.t(hx - 6 + ox, hy + 9), r.t(hx + 3 + ox, hy + 5), r.t(hx + 2.5 + ox, hy - 5), r.t(hx - 4 + ox, hy - 1)], OUTLINE)
            if not dying(clip, n):
                a.ellipse(*r.t(hx - 1 + ox, hy + 2), 1.5, 1.5, ICE[4])
            else:
                a.line([r.t(hx - 4 + ox, hy + 5), r.t(hx + 1 + ox, hy + 1)], PEARL[3], 1)
        # the scream: a dark oval that stretches with the cry, a few jagged teeth
        m = 3 + scream * 7
        a.poly([r.t(hx + 0, hy - 6), r.t(hx + 6, hy - 6 - m * .4), r.t(hx + 11, hy - 7 - m), r.t(hx + 5, hy - 9 - m * 1.3), r.t(hx - 2, hy - 7 - m)], OUTLINE)
        a.ellipse(*r.t(hx + 5, hy - 7 - m * .7), 1.6 + scream, .8 + scream * 1.6, BLOOD[1])
        for k in range(3):
            r.fang(hx + 1 + k * 3.2, hy - 6.5, 3 + scream * 2, 1.8, -1.57, BONE)
    if clip == 'attack' and n in (3, 4, 5, 6):          # the shriek as rings of cold, never rolling the sprite
        for k in range(2 + (n in (4, 5))):
            rad = 12 + k * 9 + (n - 3) * 5
            a.line([r.t(hx + 20 + math.cos(t) * rad * .7, hy - 6 + math.sin(t) * rad) for t in np.linspace(-.9, .9, 7)], [SHROUD[3], SHROUD[4], PEARL[4]][k % 3], 1)
    if dn > .55:                                       # what is left lies on the snow
        for k in range(4):
            dust(a, -22 + k * 14, 14 + (k % 2) * 3, 3.2 - k * .3, PEARL)
    return a


# ---- Shardback -------------------------------------------------------------------------------------------------------
def pincer(a, wx, wy, ang, gap, size, ramp):
    """A crab's claw: a heavy palm and two hooked fingers that curve towards each other; `gap` is how far apart the tips are held."""
    for sgn in (-1, 1):
        t = ang + sgn * gap * .5
        p0 = (wx + math.cos(ang) * 4, wy + math.sin(ang) * 4 + sgn * 3)
        ctrl = (wx + math.cos(t + sgn * .42) * size * .72, wy + math.sin(t + sgn * .42) * size * .72)
        tip = (wx + math.cos(t - sgn * .06) * size, wy + math.sin(t - sgn * .06) * size)
        pts = bez(p0, ctrl, tip, 7)
        taper(a, pts, [ramp[0], ramp[1], ramp[2], ramp[2], ramp[3]] if sgn > 0 else [ramp[0], ramp[0], ramp[1], ramp[2], ramp[2]], 11, 1.6)
        for k in range(1, 6, 1):
            px, py = pts[k]
            fang(a, px, py, size * .12, size * .09, t + (-sgn) * 1.5 - .1 * k * (-sgn), BONE)
    a.ball(wx + 1, wy, 11, 9.5, ramp, ang)


def shardback(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    lie = sm(clamp01((dn - .3) * 1.5))
    a = Painter('shardback', st * 5 - w * 4 + recoil)
    base = 25 + bob * .5 - lie * 11 - fall * 2 - st * 2
    # legs: three a side, jointed up and out, a spiked foot; the far ones darker and behind
    def leg(x, p0, side, far):
        sw = math.sin(ph + p0) * 5 if clip == 'walk' else 0
        lift = max(0, math.cos(ph + p0)) * 3.5 if clip == 'walk' else 0
        hip = (x, base - 5)
        reach = 22 + lie * 8
        knee = (x + side * (11 + lie * 4), base + 7 - lie * 12)
        foot = (x + side * reach + sw, 4.5 + lift)
        ramp = [ICE[0], ICE[0], ICE[1], ICE[1], ICE[2]] if far else [ICE[0], ICE[1], ICE[2], ICE[2], ICE[3]]
        a.limb([hip, knee, foot], ramp, 5.5)
        fang(a, foot[0], foot[1] + 2.5, 5, 3.2, -1.3 + side * .35, BONE)

    for x, p0, side in ((-18, .8, -1), (-2, 2.4, -1), (14, 4.0, 1)):
        leg(x - 3, p0, side, True)
    # the claws: a short heavy arm and a big open pincer; raised on the wind-up, slammed to the ground on the strike
    def claw(sx, sy, depth, far):
        lift = w * 1.0
        elbow = (sx + 10 + st * 3, sy + 6 + lift * 15 - st * 6 - lie * 9)
        wrist = (elbow[0] + 12 - st * 2 + lie * 6, elbow[1] + 3 + lift * 13 - st * 20 - lie * 4)
        wrist = (wrist[0], max(wrist[1], 12 + (1 - lie) * 2))
        ramp = [ICE[0], ICE[0], ICE[1], ICE[2], ICE[3]] if far else [ICE[0], ICE[1], ICE[2], ICE[3], ICE[4]]
        a.limb([(sx, sy), elbow, wrist], ramp, 12 if not far else 10)
        gap = .55 + w * .8 - st * .45 + (.14 if clip == 'idle' and n in (2, 3) else 0) + (.3 if clip == 'hurt' and n == 1 else 0)
        gap *= 1 - lie * .7
        ang = max(.06 - st * .3 + w * .62 - lie * .5, -.2)
        pincer(a, wrist[0], wrist[1], ang, gap, (38 if not far else 32) - lie * 4, ramp)

    claw(26, base + 8, 0, True)
    for x, p0, side in ((-26, 0, -1), (-10, 1.6, -1), (6, 3.2, 1)):
        leg(x, p0, side, False)
    # the carapace: a low dome of crystal plates, a ridge of tall shards, cracks
    a.ball(0, base + 4, 38, 21, ICE, -.05)
    a.ball(-8, base + 12, 26, 14, [ICE[0], ICE[1], ICE[2], ICE[3], ICE[3]])
    for k, (x, ln) in enumerate(((-30, 12), (-20, 19), (-9, 25), (3, 28), (15, 22), (26, 14))):
        cold = clamp01(dn * 1.7 - k * .12)
        fang(a, x, base + 17 - abs(k - 2.5) * 1.6 - lie * 2, ln * (1 - cold * .55), 8.6, 1.55 + (k - 2.5) * .09 - cold * .5, ICE)
    for k in range(3):
        a.line([(-24 + k * 18, base + 20), (-20 + k * 18, base + 11), (-26 + k * 18, base + 5)], ICE[4], 1)
    # a front plate over the mouth, mandibles, two stalked eyes
    a.poly([(24, base + 4), (40, base - 1), (42, base - 9), (28, base - 9)], ICE[1], outline=OUTLINE)
    for k in range(4):
        fang(a, 28 + k * 3.6, base - 8, 7 - k * .5, 3, -1.57 + k * .12, BONE)
    for k, (ex, ey) in enumerate(((22, base + 22), (31, base + 20))):
        sway = math.sin(ph + k * 1.7) * 1.2
        tip = (ex + 7 + sway, ey + 16 - lie * 12 + w * 3)
        a.limb([(ex, ey - 2), (ex + 3, ey + 8), tip], [ICE[0], ICE[1], ICE[1], ICE[2], ICE[2]], 3.2)
        a.ball(tip[0], tip[1] + 1, 4.2, 4.2, [OUTLINE, BLOOD[1], BLOOD[2], BLOOD[3], BLOOD[4]])
        if dying(clip, n):
            cross_eye(a, tip[0], tip[1] + 1, 2)
        else:
            a.ellipse(tip[0] + .8, tip[1] + 1.2, 1.2, 1.4, OUTLINE)
        a.poly([(tip[0] - 5, tip[1] + 4), (tip[0] + 5, tip[1] + 1.2), (tip[0] + 5, tip[1] + 3.8), (tip[0] - 4, tip[1] + 6.6)], OUTLINE)   # the scowling brow
    claw(30, base + 2, 1, False)
    if clip == 'attack' and n in (4, 5):               # chips flung off the slam
        for k in range(6):
            a.ball(46 + k * 4, 10 + (k % 3) * 6 - k * .6, 2.8 - k * .3, 2.4 - k * .25, ICE)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, 54 + k * 8, 4 + (k % 2) * 4, 3.2 - k * .5, PEARL)
    return a


DRAW = dict(hoarhorn=hoarhorn, whitewail=whitewail, shardback=shardback)
# the shared frame/preview machinery reads these names
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/rime_elite_{kind}_raw.npz'


def build():
    L.STRICT = True
    saved = registry()
    names = {s['name'] for s in old.api('list')['sprites']}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        data = frames(kind)
        name = PREFIX + kind + os.environ.get('SOURCE_SUFFIX', '')
        assert name not in names, name
        np.savez_compressed(raw(kind), **data)
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(name=name, width=kw, height=kh, frames=34, layers=1, fps=10, palette=PALETTE, persist=True,
                                     ops=[dict(op='set_layer', layer=0, name=kind)]))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, L.api_draw(sid, 0, data), 'frames saved', flush=True)


def refresh():
    L.STRICT = True
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(raw(kind), **data)
        print('Refreshed', kind, saved[kind], L.api_draw(saved[kind], 0, data), 'frames', flush=True)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    clips, off = {}, 0
    for row, (clip, (fps, count)) in enumerate(L.CLIPS.items()):
        clips[clip] = dict(fps=fps, n=count, row=row, editorStart=off)
        off += count
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='rime-elite')
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, idle = 0, []
        for row, (clip, (_, count)) in enumerate(L.CLIPS.items()):
            for n in range(count):
                im = rgba(L.cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                b = im.getbbox()
                kindframe.check_bounds(b, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                if clip == 'idle':
                    idle.append(b)
            offset += count
        meta['sprites'][kind] = saved[kind]
        meta['tops'][kind] = kindframe.top_of(idle, kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlas.save(ASSETS / f'rimeelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'rimeelites_{kind}.png').convert('RGBA')
        offset = 0
        for row, (clip, (_, count)) in enumerate(L.CLIPS.items()):
            seen = set()
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(L.cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n)
                seen.add(cell.tobytes())
            offset += count
            if clip in ('attack', 'die'):
                assert len(seen) == 8, (kind, clip, 'needs eight distinct frames', len(seen))
        print(kind, '34 editor frames equal the atlas; attack and death have eight distinct frames', flush=True)


if __name__ == '__main__':
    {'preview': L.preview, 'montage': L.montage, 'extents': L.extents, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'montage']()
