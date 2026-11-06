#!/usr/bin/env python3
"""Greenmeadow's three elites (zone shapes pilot): native PixelFlow sources, per-kind frames.

preview | montage | build | refresh <kinds> | export | verify

Owner rule (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye face. Each kind has its own face and silhouette:
  oldtusker     a hump-backed boar with a ridge of bramble bristles, huge upcurved tusks, one red slit eye, the other scarred shut.
                Paws and drops its head, then gores upward. Dies: the forelegs buckle, it drops and rolls onto its side.
  tidecrusher      a barnacled crab with one crusher claw bigger than its body, stalked slit eyes, working mouthparts.
                Raises the claw high and slams it into the sand. Dies: rigid shell, so the shell cracks, the legs fold, the claw drops.
  orchardqueen  a giant hornet: black and amber abdomen, a long stinger, a faceted red eye mass, hooked mandibles, a thorn crown.
                Hovers; curls the abdomen under and stabs. Dies: the wings stop, it curls up and falls to the ground.
Eight distinct attack and death frames each. The manifest is client/assets/greenmeadow.txt. Drawing helpers come from the Lapis redo.
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
OUT = ROOT / 'test-results/meadow-elites'
REGISTRY = ROOT / 'scripts/meadow_elite_sources.txt'
MANIFEST = ASSETS / 'greenmeadow.txt'
PREFIX = 'valhallasc_meadow_elite_'
KINDS = ['oldtusker', 'tidecrusher', 'orchardqueen']
KIND_FRAMES = dict(oldtusker=(176, 112, 68, 104), tidecrusher=(186, 134, 76, 124), orchardqueen=(160, 188, 86, 178))
FLYING = ('orchardqueen',)
_mine = [
    '#120a08', '#2a1812', '#44291e', '#62402c', '#8a6548',   # HIDE (boar)
    '#100a10', '#2a1c24', '#4c3540', '#745866', '#a08a94',   # THORN (bristles, dark horn)
    '#0c2422', '#1c4a44', '#2f7a6a', '#5cae94', '#a8e0c4',   # SHELL (crab, sea-green)
    '#3a0e10', '#7a2018', '#b84a22', '#e08a3a', '#f8c878',   # CLAW (rust-orange crusher)
    '#2a2420', '#5a5044', '#8e8470', '#c4bca4', '#f0ead4',   # BARNACLE
    '#0c0a12', '#1c1826', '#322c40', '#50485e', '#7a7290',   # CHITIN (hornet black)
    '#4a2a04', '#a06408', '#e0a010', '#f8d040', '#fff4a0',   # WASP (amber bands)
    '#8ad4e8', '#b0e4f0', '#d0f0f8', '#e8f8fc', '#f8feff',   # WING
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
HIDE, THORN, SHELL, CLAW, BARN, CHITIN, WASP, WING = [_i[5 * k:5 * k + 5] for k in range(8)]


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
    glow = glow or CRIMSON
    if shut:
        r.line([(x - w, y - .6), (x + w, y + .6)], OUTLINE, 2)
        return
    r.poly([(x - w, y - .6), (x - w * .1, y + 1.8), (x + w, y - 1.5), (x + w * .2, y - 2.6)], glow[3], outline=OUTLINE)
    r.ellipse(x + w * .2, y - .6, 1, 1.3, OUTLINE)
    r.poly([(x - w - 1.5, y + 2.8), (x + w + 1, y - .6), (x + w + 1, y + 1.8), (x - w - .5, y + 4.4)], OUTLINE)


# ---- Old Tusker ---------------------------------------------------------------------------------------------------
def oldtusker(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    lie = sm(clamp01((dn - .3) * 1.5))
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('oldtusker', st * 13 - w * 7 + recoil)
    base = 34 + bob * .6 - lie * 7 - fall * 3 - w * 2.5 + abs(gait) * .8
    r = Rig(a, -2, 12, -w * .12 + st * .15 + fall * .10 - lie * .06)

    def leg(x, ramp, phase, front):
        sw = math.sin(ph + phase) * 7 if clip == 'walk' else 0
        hip = (x, base - 8)
        fx = x + sw - (w * 4 if front else 0) + (st * 6 if front else -st * 3)
        fy = 2.5 + max(0, math.cos(ph + phase)) * 3 if clip == 'walk' else 2.5
        fold = lie if not front else clamp01(fall * 1.5)
        foot = mixp((fx, fy), (x + (14 if front else -14) * lie, 3.5 + 3 * lie), fold)
        knee = mixp(((hip[0] + foot[0]) / 2 + (2.5 if front else -3), (hip[1] + foot[1]) / 2), (x + 4, base - 13), fold * .7)
        a.limb([r.t(*hip), r.t(*knee) if fold < .5 else knee, foot], ramp, 8)
        a.ball(foot[0] + 1, foot[1] - .4, 4.6, 2.6, THORN)

    # far legs
    leg(-22, [HIDE[0], HIDE[0], HIDE[1], HIDE[2], HIDE[2]], 1.6, False)
    leg(14, [HIDE[0], HIDE[0], HIDE[1], HIDE[2], HIDE[2]], 0, True)
    # tail: a short bristled whip
    tail = bez((-32, base + 7), (-42, base + 12 + math.sin(ph) * 2), (-45, base + 2 - fall * 6), 7)
    tw = settle(r, tail, lie, -1, .2)
    taper(a, tw, HIDE, 3.4, 1.2)
    fang(a, *tw[-1], 5, 3.4, 3.6, THORN)
    # body: heavy rump, a great shoulder hump
    r.ball(-13, base + 2, 23, 19, HIDE, -.1)
    r.ball(12, base + 7, 21, 21, HIDE, -.25)
    r.ball(-4, base - 9, 22, 8, [HIDE[1], HIDE[2], HIDE[3], HIDE[3], HIDE[4]])
    # old scars across the flank
    for x0, y0 in ((-16, base + 6), (-9, base + 9), (-22, base + 1)):
        r.line([(x0, y0), (x0 + 8, y0 - 7)], HIDE[4], 1)
    # bramble ridge along the spine, tallest on the hump; it stands up in the wind-up
    for k in range(13):
        t = k / 12
        x = mix(-32, 26, t)
        y = base + 16 + math.sin(t * math.pi) * 13 - (6 if t > .85 else 0)
        ln = (9 + 8 * math.sin(t * math.pi) + (k % 2) * 3) * (1 + w * .3) * (1 - lie * .35)
        r.fang(x, y, ln, 5.4, 1.75 - t * .5 + (k % 3 - 1) * .13, THORN)
    leg(-16, HIDE, 3.2, False)
    leg(21, HIDE, 4.7, True)
    # head: low and wedge-shaped, the snout swings up on the strike
    hx, hy = 34 + st * 3, base - 1 - w * 8 + st * 6 - lie * 2
    h = L.HeadRig(a, hx, hy, 1.38, phi=-w * .18 + st * .42 - fall * .22, cx=hx - 8, cy=hy)
    h.ball(hx - 3, hy + 1, 15, 13, HIDE, -.2)
    h.poly([(hx - 12, hy + 12), (hx - 17, hy + 22 + w * 2), (hx - 5, hy + 13)], HIDE[1], outline=HIDE[0])     # torn ear
    h.poly([(hx - 12.5, hy + 14), (hx - 14.5, hy + 19), (hx - 9, hy + 14)], CRIMSON[1])
    h.ball(hx + 13, hy - 5, 11, 8, HIDE, -.1)
    h.ball(hx + 22, hy - 5.5, 4.6, 5.4, [HIDE[2], HIDE[3], HIDE[3], HIDE[4], HIDE[4]])
    h.ellipse(hx + 24, hy - 4.2, 1, 1.4, OUTLINE)
    h.ellipse(hx + 23.6, hy - 7.2, 1, 1.3, OUTLINE)
    gape = 4 if st > .4 or (clip == 'hurt' and n == 1) or (clip == 'die' and 1 <= n <= 3) else 1.2
    h.poly([(hx + 2, hy - 8), (hx + 20, hy - 9.4), (hx + 15, hy - 11 - gape), (hx + 3, hy - 11 - gape * .6)], CRIMSON[0], outline=OUTLINE)
    h.poly([(hx + 3, hy - 10.4 - gape * .6), (hx + 14, hy - 10.8 - gape), (hx + 14, hy - 13 - gape), (hx + 2, hy - 13 - gape * .6)], HIDE[1], outline=HIDE[0])
    # tusks: the far one, then the near one, long and hooked upward
    far = [h.t(*p) for p in bez((hx + 12, hy - 9), (hx + 25, hy - 13), (hx + 29, hy + 9), 8)]
    taper(a, far, [BONE[0], BONE[1], BONE[2], BONE[2], BONE[3]], 5.5, 1)
    near = [h.t(*p) for p in bez((hx + 9, hy - 10), (hx + 24, hy - 17), (hx + 24, hy + 13), 9)]
    taper(a, near, BONE, 7.5, 1)
    # one red slit, the other scarred shut
    shut = dying(clip, n)
    slit_eye(h, hx + 4, hy + 4.5, 5, shut=shut)
    h.line([(hx - 3, hy + 11), (hx + 7, hy - 3)], HIDE[4], 1)
    if st > .6 and clip == 'attack':
        for k in range(3):
            dust(a, 48 + k * 7, 5 + (k % 2) * 4, 3.2 - k * .5, PEARL)
    if clip == 'attack' and n in (1, 2):
        for k in range(2):
            dust(a, 10 - k * 9, 4 + k * 2, 2.8, PEARL)
    return a


# ---- Tidecrusher -----------------------------------------------------------------------------------------------------
def tidecrusher(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    lie = sm(clamp01((dn - .25) * 1.45))
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('tidecrusher', gait * 2 + recoil)
    base = 31 + bob * .5 - lie * 18 + w * 2 - st * 3
    cracked = clip == 'die' and n >= 2

    def leg(side, k):
        hip = (side * (22 + k * 3), base - 2 - k)
        lift = max(0, math.sin(ph + k * 1.5 + (0 if side > 0 else 2))) * 5 if clip == 'walk' else 0
        knee = (side * (43 + k * 6 - lie * 8), base + 15 - k * 5 - lie * 8)
        foot = (side * (37 + k * 9), 2.5 + lift)
        foot = mixp(foot, (side * (30 + k * 5), 12 + k * 3), clamp01(lie * 1.15))
        ramp = [SHELL[0], SHELL[0], SHELL[1], SHELL[2], SHELL[2]] if k % 2 else SHELL
        a.limb([hip, knee], ramp, 5.4 - k * .3)
        taper(a, [knee, mixp(knee, foot, .55), foot], ramp, 5, 1)

    for k in (2, 1, 0):
        leg(-1, k)
        leg(1, k)
    # left feeding claw: small, picks at things
    fx, fy = -27 + math.sin(ph) * 2, base + 9
    a.limb([(-19, base + 2), (-29, base + 4), (fx - 3, fy)], SHELL, 5)
    a.ball(fx - 5, fy + 2, 5.6, 4, CLAW)
    fang(a, fx - 8, fy + 3, 6, 3, 2.5, CLAW)
    # carapace: broad, ridged, armoured, not a round ball
    pts = [(-30, base + 2), (-24, base + 16), (-10, base + 22), (10, base + 22), (24, base + 16), (30, base + 2), (22, base - 10), (-22, base - 10)]
    a.poly(pts, SHELL[1], outline=OUTLINE)
    a.poly([(-25, base + 4), (-20, base + 14), (-8, base + 19), (8, base + 19), (20, base + 14), (25, base + 4)], SHELL[2])
    a.poly([(-18, base + 10), (-8, base + 16), (6, base + 16), (14, base + 11), (0, base + 9)], SHELL[3])
    for x in (-27, -18, 18, 27):                                    # rim spikes
        fang(a, x, base + 9 + (5 if abs(x) < 20 else 0), 6, 4, 1.57 + x * .018, SHELL)
    for x, y, rr in ((-12, base + 15, 3.4), (-5, base + 18, 2.6), (9, base + 14, 3.6), (16, base + 10, 2.4), (-18, base + 8, 2.6), (2, base + 12, 2.2)):
        a.ball(x, y, rr, rr * .8, BARN)
        a.ellipse(x, y + .3, rr * .35, rr * .3, OUTLINE)
    if cracked:                                                     # the shell splits and a plate slips
        crack = [(-5, base + 22), (-1, base + 13), (-6, base + 6), (0, base - 2), (-3, base - 9)]
        a.line(crack, OUTLINE, 2)
        a.line([(-1, base + 13), (9, base + 9)], OUTLINE, 1)
        if n >= 5:
            a.poly([(1, base + 21), (12, base + 19), (14, base + 13), (4, base + 12)], SHELL[1], outline=OUTLINE)
    # underside and mouth: working mandibles and teeth
    a.poly([(-14, base - 2), (14, base - 2), (9, base - 11), (-9, base - 11)], BARN[1], outline=OUTLINE)
    gape = 2 + (2.5 if st > .3 or w > .6 else math.sin(ph * 2) * .8)
    a.poly([(-9, base - 4), (9, base - 4), (6, base - 5 - gape), (-6, base - 5 - gape)], CRIMSON[0], outline=OUTLINE)
    for x in (-6, -3, 0, 3, 6):
        a.poly([(x - 1.2, base - 4), (x + 1.2, base - 4), (x, base - 7 - (x % 2))], BONE[4], outline=BONE[0])
    # stalk eyes: narrow, hateful, fall limp in death
    for s in (-1, 1):
        ex, ey = s * 8 + 3, base + 31 - w * 2 - lie * 13
        sway = math.sin(ph + s) * 1.2
        a.limb([(s * 7 + 2, base + 18), (ex + sway + s * lie * 7, ey - lie * 3)], SHELL, 3.2)
        a.ball(ex + sway + s * lie * 7, ey, 5, 3.4, BARN)
        rr = Rig(a, 0, 0, 0)
        slit_eye(rr, ex + sway + s * lie * 7, ey, 3.4, shut=dying(clip, n), glow=GOLD)
    # the crusher: nearly as big as the body; raised overhead on the wind-up, slammed into the sand on the strike
    rest = ((39, base - 7), (49, base + 3), 1.05)
    wind = ((36, base + 13), (31, base + 29), 1.5)
    hit = ((42, base - 3), (53, 21), -.5)
    down = ((38, base - 12), (49, 15), .12)
    pose = [mixp(rest[i], wind[i], clamp01(w)) if i < 2 else mix(rest[i], wind[i], clamp01(w)) for i in range(3)]
    pose = [mixp(pose[i], hit[i], st) if i < 2 else mix(pose[i], hit[i], st) for i in range(3)]
    pose = [mixp(pose[i], down[i], lie) if i < 2 else mix(pose[i], down[i], lie) for i in range(3)]
    elbow, wrist, ang = pose
    a.limb([(22, base - 1), elbow, wrist], CLAW, 8)
    wx, wy = wrist
    r = Rig(a, wx, wy, ang)
    openj = .22 + w * .55 + (.16 if clip == 'idle' and n in (2, 3) else 0) - st * .22 - lie * .1
    # lower finger first, then the palm, then the big hooked upper finger
    bx, by = r.t(wx + 15, wy - 5)
    bot = Rig(a, bx, by, ang - openj * .7)
    bot.poly([(bx - 3, by + 4), (bx + 9, by + 4), (bx + 24, by + 3), (bx + 13, by - 5), (bx - 3, by - 6)], CLAW[1], outline=OUTLINE)
    for k in range(3):
        bot.fang(bx + 2 + k * 6, by + 4, 4.2, 3.2, 1.57, BONE)
    r.ball(wx + 9, wy, 15, 12, CLAW, -.1)
    r.ball(wx + 4, wy - 4, 7, 5, [CLAW[1], CLAW[2], CLAW[2], CLAW[3], CLAW[3]])
    tx, ty = r.t(wx + 15, wy + 6)
    top = Rig(a, tx, ty, ang + openj)
    top.poly([(tx - 5, ty + 6), (tx + 12, ty + 8), (tx + 27, ty + 3), (tx + 35, ty - 6), (tx + 22, ty - 3), (tx + 8, ty - 5), (tx - 5, ty - 5)], CLAW[2], outline=OUTLINE)
    top.poly([(tx - 1, ty + 4), (tx + 12, ty + 5), (tx + 23, ty + 2), (tx + 11, ty)], CLAW[4])
    for k in range(4):
        top.fang(tx + 3 + k * 6, ty - 4, 4.8, 3.4, -1.57, BONE)
    for x, y, rr2 in ((5, 7, 2.6), (12, 8, 2), (1, -3, 1.8)):
        a.ball(*r.t(wx + x, wy + y), rr2, rr2 * .8, BARN)
    if clip == 'attack' and n in (4, 5):
        for k in range(4):
            dust(a, wx + 24 + k * 6, 4 + (k % 2) * 5, 3.4 - k * .4, PEARL)
    return a


# ---- The Orchard Queen --------------------------------------------------------------------------------------------
def orchardqueen(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.05)
    dead = clip == 'die'
    a = Painter('orchardqueen', st * 14 - w * 6 + recoil + fall * 14)
    hover = 60 + math.sin(ph * 2) * 2.4 + w * 26 + math.sqrt(st) * 32
    y0 = mix(hover, 32, fall)
    tilt = -st * .28 + w * .28 - fall * .16
    r = Rig(a, 0, y0, tilt)
    curl = w * .75 + st * 1.75 + fall * .12

    # wings: four thin blades, a beat per frame, folded and still in death
    beat = (n % 3) * .55 if clip != 'die' else 0
    for ang, ln, wd, ramp_i in ((2.05 - beat, 54, 13, 0), (2.5 - beat * .7, 40, 10, 1), (1.7 + beat * .6, 46, 11, 2), (2.3 + beat * .4, 34, 9, 1)):
        ang = mix(ang, 3.05, fall)
        ln *= 1 - fall * .25
        base_pt = (-1, y0 + 12)
        tip = polar(*base_pt, ang, ln)
        nx, ny = math.cos(ang + 1.57) * wd / 2, math.sin(ang + 1.57) * wd / 2
        mid = mixp(base_pt, tip, .62)
        pts = [base_pt, (mid[0] + nx, mid[1] + ny), tip, (mid[0] - nx, mid[1] - ny)]
        a.poly([r.t(*p) for p in pts], WING[ramp_i], outline=CHITIN[3])
        a.line([r.t(*base_pt), r.t(*mixp(base_pt, tip, .9))], CHITIN[2], 1)

    # abdomen: segments along a curve that swings forward under the body for the sting
    seg, x, y, ang = [], -6, y0 - 2, math.pi + .18
    for k in range(6):
        rr = [13, 15, 13.5, 11, 8, 5][k]
        seg.append((x, y, rr, ang))
        ang += curl * .36 + .04
        x += math.cos(ang) * rr * .92
        y += math.sin(ang) * rr * .92
    for k in reversed(range(6)):
        x, y, rr, ang = seg[k]
        r.ball(x, y, rr, rr * .9, WASP if k % 2 == 0 else CHITIN, ang)
        if k % 2 == 0:                                  # a black chevron cut into each amber band
            r.poly([polar(x, y, ang + 1.3, rr * .9), polar(x, y, ang, rr * .25), polar(x, y, ang - 1.3, rr * .9), polar(x, y, ang + math.pi, rr * .2)], CHITIN[1])
    x, y, rr, ang = seg[-1]
    r.fang(*polar(x, y, ang, rr * .5), 19 + st * 9, 6.4, ang, BONE)
    if clip == 'attack' and n in (4, 5):
        tipx, tipy = r.t(*polar(x, y, ang, rr * .5 + 24))
        a.ball(tipx, tipy, 2.6, 2.2, WASP)

    # thorax: armoured, hairy
    r.ball(4, y0 + 2, 15, 14, CHITIN, -.2)
    r.ball(1, y0 + 8, 9, 6, WASP, -.2)
    for k in range(6):
        r.line([(-6 + k * 3.4, y0 + 15.5 - abs(k - 2.5) * .8), (-7.4 + k * 3.4, y0 + 19.5 - abs(k - 2.5))], WASP[1], 1)
    # legs: hooked, reaching forward as she strikes, folded tight in death
    for k, (lx, reach) in enumerate(((10, 15), (3, 8), (-4, 1))):
        knee = (lx + 7 + st * 6 - fall * 3, y0 - 15 + fall * 6)
        foot = (lx + reach + st * 13 - fall * 10, y0 - 26 + st * 7 + fall * 16 + math.sin(ph + k) * 1.6)
        r.limb([(lx, y0 - 8), knee], CHITIN, 3.6)
        taper(a, [r.t(*knee), r.t(*mixp(knee, foot, .55)), r.t(*foot)], CHITIN, 3, 1)
        r.line([foot, (foot[0] + 3.4, foot[1] - 2.2)], WASP[3], 1)

    # head: wide and angular, a faceted red eye mass, antennae laid back, hooked mandibles, a crown of thorns
    hx, hy = 23 + st * 3, y0 + 5 - st * 1.5
    h = L.HeadRig(a, 0, y0, 1.4, phi=tilt, cx=hx - 8, cy=hy)
    for s, ramp in ((-1, THORN), (1, WASP)):             # mandibles behind the face
        op = 3.5 + (w * 3.5) + st * 2
        h.poly([(hx + 7, hy - 6), (hx + 14, hy - 5 + s * (op + 2.2)), (hx + 21, hy - 8 + s * op), (hx + 12, hy - 7 + s * op * .3)], ramp[3], outline=OUTLINE)
    h.ball(hx, hy, 11.5, 10.5, CHITIN, -.1)
    h.poly([(hx + 1, hy + 9), (hx + 11, hy + 4), (hx + 12, hy - 3), (hx + 3, hy - 4), (hx - 3, hy + 2)], CRIMSON[3], outline=OUTLINE)
    if dying(clip, n):
        cross_eye(h, hx + 5, hy + 2, 3)
    else:
        for i in range(4):                               # facets
            for j in range(3):
                if (i + j) % 3 == 0:
                    h.ellipse(hx + 1.6 + i * 2.5 - j * .4, hy - 1.4 + j * 2.8 + i * .2, .7, .7, CRIMSON[4])
        h.poly([(hx - 4, hy + 8), (hx + 12, hy + 3), (hx + 12, hy + 6), (hx - 2, hy + 11)], OUTLINE)
    for k, off in enumerate((-.5, -.1, .3, .7)):         # thorn crown
        h.fang(hx - 3 + k * 3.2, hy + 9.5, 7 + (k % 2) * 3, 3, 1.5 - off * .8, WASP)
    for s in (0, 1):
        ant = bez((hx + 2 + s * 3, hy + 10), (hx - 8 + s * 4, hy + 24 - fall * 12), (hx - 19 + s * 6, hy + 21 - fall * 16), 7)
        a.line([h.t(*p) for p in ant], OUTLINE, 2)
    return a


DRAW = dict(oldtusker=oldtusker, tidecrusher=tidecrusher, orchardqueen=orchardqueen)
# the shared frame/preview machinery reads these names
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/meadow_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='meadow-elite')
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
        atlas.save(ASSETS / f'greenmeadow_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'greenmeadow_{kind}.png').convert('RGBA')
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
    {'preview': L.preview, 'montage': L.montage, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'montage']()
