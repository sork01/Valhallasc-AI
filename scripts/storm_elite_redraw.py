#!/usr/bin/env python3
"""The Stormglass Flats' two new elites (zone shapes pilot): native PixelFlow sources with their own frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  lamphermit  The Lamphouse Hermit (level 63, quest): a hermit crab as big as a barn that wears a wrecked lighthouse lamphouse for a shell: a leaning stone
              drum, an iron gallery, a lantern room whose glass still burns (one pane smashed) and a copper-green roof with a lightning rod. Under it a
              low carapace of dark teal plate, four spiked walking legs a side, a great toothed crusher claw, a small snapping claw and two short armoured
              eye stalks whose pale slit-pupilled eyes sit under spiked brows. Winds up by rearing the crusher high over the shell while the tower leans
              back; the strike is a slam with the shell rocking forward and the rod discharging into the claw. Dies when its legs fold: the claw drops,
              the tower tips back onto the ground and the lamp gutters out.
  stormtusk   The Stormtusk (level 62, no quest): a stranded narwhal of black glass, hauling itself over the sand on two stout flippers; a pale scarred belly,
              glowing cracks along the back, a small sunken eye with a white slit, a mouth of needle teeth and a long spiral tusk that crackles with
              lightning. Winds up by rearing its forebody and swinging the tusk up; the strike lunges the whole body forward with the tusk levelled and
              lightning arcing off the tip. Dies when it sags onto its belly: the tusk snaps and falls, the cracks go dark one by one and the eye closes.
The manifest is client/assets/stormelites.txt. The shading helpers are copied from prism_elite_redraw.py.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import kindframe
import lapis_slime_redraw as L
from lapis_slime_redraw import (BasePainter, OUTLINE, BONE, PEARL, clamp01, curves, dying, settle, polar, mix, mixp, sm, bez, dust, old, Rig)
from astral_slime_redraw import arm_ik, taper
from moonspore_slime_redraw import fang, plate

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/storm-elites'
REGISTRY = ROOT / 'scripts/storm_elite_sources.txt'
MANIFEST = ASSETS / 'stormelites.txt'
PREFIX = 'valhallasc_storm_elite_'
KINDS = ['lamphermit', 'stormtusk']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(lamphermit=(192, 134, 80, 122), stormtusk=(192, 120, 68, 106))
SCALE = dict(lamphermit=.72, stormtusk=.6)
FLYING = ()
_mine = [
    '#10161f', '#2a3646', '#4e6178', '#8497ad', '#c2d2e0',   # STONE (the lamphouse drum)
    '#07121a', '#16303e', '#285666', '#3f8294', '#86c8d4',   # CARA (the crab's carapace)
    '#14201a', '#2c4a3a', '#4f7e62', '#86b896', '#c8ead2',   # ROOF (verdigris copper)
    '#3c2406', '#a8701a', '#ecb83a', '#fff0a0', '#ffffff',   # LAMP (the lamp and the eyes)
    '#03070c', '#0c1826', '#1a2e46', '#32506e', '#5a82a0',   # BLK (the Stormtusk's black glass)
    '#26323e', '#4e6076', '#7e92aa', '#b4c6d8', '#e6eef6',   # BELLY (its pale scarred belly)
    '#18346e', '#3470c8', '#78b4ff', '#cce8ff', '#fcfeff',   # LGT (lightning)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
STONE, CARA, ROOF, LAMP, BLK, BELLY, LGT = [_i[5 * k:5 * k + 5] for k in range(7)]


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kindframe.check_frame(*KIND_FRAMES[kind])
        self.S = SCALE.get(kind, 1.)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax + dx * self.S

    def pos(self, x, y):
        return round(self.cx + x * self.S), min(round(self.ay - y * self.S), self.ay + 4)      # nothing sinks more than four rows under the ground

    def ellipse(self, x, y, rx, ry, col):
        super().ellipse(x, y, rx * self.S, ry * self.S, col)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width * self.S)))

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        super().ball(x, y, rx * self.S, ry * self.S, ramp, ang)


# ---- shading toolkit (copied from bifrost_elite_redraw.py) ----------------------------------------------------------------------
def smooth(pts, n=5, closed=True):
    P = list(pts)
    m = len(P)
    out = []
    for i in range(m if closed else m - 1):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        if not closed:
            p0 = P[max(i - 1, 0)]
            p3 = P[min(i + 2, m - 1)]
        for k in range(n):
            t = k / n
            out.append(tuple(.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    return out


def capsule(p, q, w0, w1, caps=5):
    dx, dy = q[0] - p[0], q[1] - p[1]
    ln = math.hypot(dx, dy) or 1.
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    pts = [(p[0] + nx * w0 / 2, p[1] + ny * w0 / 2), (q[0] + nx * w1 / 2, q[1] + ny * w1 / 2)]
    for k in range(1, caps):
        a = math.pi * k / caps
        pts.append((q[0] + (nx * math.cos(a) + ux * math.sin(a)) * w1 / 2, q[1] + (ny * math.cos(a) + uy * math.sin(a)) * w1 / 2))
    pts += [(q[0] - nx * w1 / 2, q[1] - ny * w1 / 2), (p[0] - nx * w0 / 2, p[1] - ny * w0 / 2)]
    for k in range(1, caps):
        a = math.pi * k / caps
        pts.append((p[0] - (nx * math.cos(a) - ux * math.sin(a)) * w0 / 2, p[1] - (ny * math.cos(a) - uy * math.sin(a)) * w0 / 2))
    return pts


def shaded(a, pts, ramp, light=(-.6, -.8), base=.58, contrast=1., outline=OUTLINE, edge=True, grain=0.):
    P = [a.pos(*p) for p in pts]
    m = Image.new('1', (a.w, a.h), 0)
    ImageDraw.Draw(m).polygon(P, fill=1)
    mk = np.array(m, bool)
    ys, xs = np.nonzero(mk)
    if not xs.size:
        return
    cx, cy = xs.mean(), ys.mean()
    proj = (xs - cx) * light[0] + (ys - cy) * light[1]
    ext = max(1e-6, np.abs(proj).max())
    v = base + .5 * contrast * proj / ext
    thr = (((xs % 4) * 5 + (ys % 4) * 3) % 16) / 16. - .5
    v += thr * .22
    if grain:
        v += ((np.sin(xs * 12.9898 + ys * 78.233) * 43758.5453) % 1 - .5) * grain
    idx = np.clip((v * (len(ramp) - 1) + .5).astype(int), 0, len(ramp) - 1)
    arr = np.array(a.im)
    rows = np.array(ramp)[idx]
    inner = ndimage.binary_erosion(mk, iterations=1)
    arr[ys, xs] = rows
    if edge:
        rim = mk & ~inner
        ry, rx = np.nonzero(rim)
        lit = ((rx - cx) * light[0] + (ry - cy) * light[1]) > 0
        arr[ry[~lit], rx[~lit]] = ramp[0]
        if outline is not None:
            arr[ry[lit], rx[lit]] = outline
    a.im.paste(Image.fromarray(arr, 'P'), mask=Image.fromarray((mk * 255).astype(np.uint8)))


def glow(a, x, y, r, ramp, strength=1.):
    px, py = a.pos(x, y)
    R = max(1., r * a.S)
    arr = np.array(a.im)
    for yy in range(max(0, int(py - R) - 1), min(a.h, int(py + R) + 2)):
        for xx in range(max(0, int(px - R) - 1), min(a.w, int(px + R) + 2)):
            d = math.hypot(xx - px, yy - py) / R
            if d > 1:
                continue
            v = (1 - d) ** 1.4 * strength
            thr = (((xx % 4) * 5 + (yy % 4) * 3) % 16) / 16.
            if v > thr * .9 + .08:
                arr[yy, xx] = ramp[min(len(ramp) - 1, int(v * len(ramp)))]
    a.im.paste(Image.fromarray(arr, 'P'))


def tapered(a, spine, w0, w1, ramp, base=.55, contrast=1., n=None, edge=True):
    """A shape that follows a spine (list of points) from width w0 to w1."""
    n = len(spine)
    left, right = [], []
    for i, p in enumerate(spine):
        q = spine[min(i + 1, n - 1)]
        r = spine[max(i - 1, 0)]
        dx, dy = q[0] - r[0], q[1] - r[1]
        ln = math.hypot(dx, dy) or 1.
        nx, ny = -dy / ln, dx / ln
        wd = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append((p[0] + nx * wd, p[1] + ny * wd))
        right.append((p[0] - nx * wd, p[1] - ny * wd))
    shaded(a, left + right[::-1], ramp, base=base, contrast=contrast, edge=edge)


def ring_arc(a, cx, cy, rx, ry, tilt, t0, t1, col, width=1, steps=24):
    pts = []
    for k in range(steps + 1):
        t = t0 + (t1 - t0) * k / steps
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)))
    a.line(pts, col, width)
    return pts


# ---- the Lamphouse Hermit -------------------------------------------------------------------------------------------------------
def tower_pt(base, lean, u, v):
    """Tower-local (u across, v up) to world; a positive lean tips the top backward (toward -x)."""
    c, s = math.cos(lean), math.sin(lean)
    return (base[0] - v * s + u * c, base[1] + v * c + u * s)


def zig(a, p, q, col, steps=5, amp=3.5, seed=0, width=1):
    pts = [p]
    for k in range(1, steps):
        t = k / steps
        j = ((seed * 7 + k * 13) % 5 - 2) / 2.
        pts.append((p[0] + (q[0] - p[0]) * t + j * amp, p[1] + (q[1] - p[1]) * t + (-j) * amp * .5))
    pts.append(q)
    a.line(pts, col, width)


def pincers(a, hand, ang, size, op, ramp):
    """A toothed claw at `hand`, pointing along `ang`: a blocky palm, a fixed lower finger and a moving upper one that opens by `op` (0..1)."""
    c, s = math.cos(ang), math.sin(ang)
    P = lambda u, v: (hand[0] + (u * c - v * s) * size, hand[1] + (u * s + v * c) * size)
    a.ball(hand[0], hand[1], 13 * size, 11 * size, ramp, ang)
    low = [P(4, -9), P(34, -8), P(44, -2), P(30, -2), P(16, 0), P(6, -1)]
    up = [P(4, 9), P(30, 5 + op * 15), P(42, 1 + op * 11), P(26, 1 + op * 2), P(14, 1), P(6, 2)]
    plate(a, low, ramp)
    plate(a, up, ramp)
    for k in range(4):                                                     # teeth along the inner edges
        u = 16 + k * 6
        x0, y0 = P(u, -1)
        fang(a, x0, y0, 5 * size, 2.6 * size, ang + math.pi / 2 + .25, BONE)
        x1, y1 = P(u + 1, 1 + op * 3 + k * 1.2)
        fang(a, x1, y1, 5 * size, 2.6 * size, ang - math.pi / 2 - .25, BONE)


def lamphermit(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    lunge = st * 11 - w * 6 + recoil - 8
    a = Painter('lamphermit', lunge)
    sag = sm(clamp01(dn * 1.7))                                            # the legs fold first
    fall = sm(clamp01((dn - .25) * 1.4))                                   # then the tower tips back
    by = 25 + bob * .5 - w * 4 - sag * 13 - (2 if hurt else 0)             # the carapace's centre height
    out = sm(clamp01((dn - .72) * 4))                                      # the lamp has gone out
    flick = (.78 + .22 * math.sin(ph * 3.1)) * (1 - out) if clip != 'die' else max(0., (1 - dn * 1.15)) * (.8 + .2 * math.sin(n * 2.3))
    lean = .15 + w * .13 - st * .16 + fall * .62 + (.05 if hurt else 0)
    base = (-9 + fall * -4, by + 14)

    # ---- the far legs, behind the carapace
    def leg(hx, side, foot, ramp, th):
        hip = (hx, by - 5)
        knee, ft = arm_ik(hip, foot, 27, 28, 1 if side > 0 else -1)
        knee = (knee[0], max(knee[1], by - 2))                              # a knee never dips under the body line
        a.limb([hip, knee], ramp, th)
        a.limb([knee, ft], ramp, th * .8)
        a.poly([(ft[0] - 2.5, ft[1] + 1), (ft[0] + 2.5 * side, ft[1] + 1), (ft[0] + 3 * side, max(ft[1] - 5, 0.5))], BONE[2], outline=CARA[0])
    def foot_of(hx, side, k, drop):
        g = math.sin(ph + k * 1.6) if walk else 0.
        fx = hx + side * (22 - sag * 9 + g * 7)
        fy = 5 + max(0., g) * 9
        return (fx, mix(fy, 4.5, drop))
    far = [CARA[0], CARA[0], CARA[1], CARA[1], CARA[2]]
    near = [CARA[0], CARA[1], CARA[2], CARA[3], CARA[3]]
    hips = [(-36, -1, 0), (-14, -1, 1), (10, 1, 2), (30, 1, 3)]
    for hx, side, k in hips[::2]:
        leg(hx + 5, side, foot_of(hx + 5, side, k + 1, sag), far, 6)

    # ---- the lamphouse: stone drum, iron gallery, lantern room, roof and rod
    T = lambda u, v: tower_pt(base, lean, u, v)
    stone_face = [STONE[0], STONE[1], STONE[2], STONE[3], STONE[3]]
    shaded(a, [T(-26, -4), T(26, -4), T(22, 36), T(-22, 36)], stone_face, base=.55, contrast=1.1, grain=.18)
    for v in (9, 19, 29):                                                  # courses of stone
        a.line([T(-25 + v * .08, v), T(25 - v * .08, v)], STONE[1], 1)
    for u, v in ((-9, 14), (7, 25), (-4, 4)):                              # staggered joints
        a.line([T(u, v), T(u, v + 10)], STONE[1], 1)
    a.poly([T(-6, 19), T(0, 19), T(0, 29), T(-6, 29)], STONE[0])           # a dark window slit
    a.poly([T(11, 5), T(16, 5), T(16, 14), T(11, 14)], STONE[0])
    for u, v in ((-19, 9), (14, 28), (-11, 31), (20, 12)):                 # salt crust and barnacles on the stone
        a.ball(*T(u, v), 4.2, 3.2, [STONE[2], STONE[3], STONE[4], STONE[4], STONE[4]], 0)
    # the gallery: an iron ring with railing posts
    shaded(a, [T(-30, 36), T(30, 36), T(28, 40), T(-28, 40)], [CARA[0], CARA[0], CARA[1], CARA[2], CARA[2]], base=.5)
    for u in (-24, -12, 0, 12, 24):
        a.line([T(u, 40), T(u, 47)], CARA[1], 1)
    a.line([T(-27, 47), T(27, 47)], CARA[2], 1)
    # the lantern room: dark mullions round glowing panes, one pane smashed
    room = [T(-19, 40), T(19, 40), T(17, 66), T(-17, 66)]
    a.poly(room, CARA[0], outline=CARA[0])
    glass = [LAMP[0], LAMP[1], LAMP[1], LAMP[2], LAMP[2]] if flick < .25 else [LAMP[1], LAMP[2], LAMP[3], LAMP[3], LAMP[4]]
    if out > .5:
        glass = [CARA[0], CARA[0], CARA[1], CARA[1], CARA[1]]
    for k in range(3):
        u0 = -16 + k * 11
        pane = [T(u0, 43), T(u0 + 9, 43), T(u0 + 8, 63), T(u0 + 1, 63)]
        broken = (k == 2)
        if broken:                                                          # the smashed pane: jagged, dark, glass teeth left in the frame
            a.poly(pane, CARA[0])
            a.poly([T(u0 + 1, 43), T(u0 + 4, 51), T(u0 + 2, 57), T(u0 + 6, 63), T(u0 + 1, 63)], glass[1])
        else:
            shaded(a, pane, glass, light=(-.2, -.9), base=.7 * (.45 + .55 * flick), contrast=.6, edge=False)
    a.line([T(-17, 53), T(17, 53)], CARA[1], 1)
    glow(a, *T(0, 53), 30 * (.45 + .55 * flick), [LAMP[1], LAMP[2], LAMP[3], LAMP[3], LAMP[4]], .8 * flick)
    # the roof: a copper-green cone with a lightning rod
    shaded(a, [T(-23, 66), T(23, 66), T(3, 90), T(-3, 90)], [ROOF[0], ROOF[1], ROOF[2], ROOF[3], ROOF[3]], base=.5, contrast=1.1)
    a.line([T(0, 90), T(0, 112)], CARA[2], 2)
    a.ball(*T(0, 114), 2.4, 2.4, [LAMP[1], LAMP[2], LAMP[3], LAMP[3], LAMP[4]], 0)
    rod_tip = T(0, 116)

    # ---- the carapace: a low plate-armoured saddle with a spiked front rim, and the dark underside
    a.ball(0, by - 9, 45, 11, [CARA[0], CARA[0], CARA[1], CARA[1], CARA[2]], 0)
    a.ball(1, by + 1, 46, 17, [CARA[0], CARA[1], CARA[2], CARA[3], CARA[4]], .03)
    for k in range(6):                                                     # ridges of armour plate along the back
        x0 = -36 + k * 13
        a.line([(x0, by + 14 - k * .3), (x0 + 7, by + 1)], CARA[0], 1)
    for k in range(4):                                                     # spikes on the front rim
        sx = 14 + k * 8
        a.poly([(sx, by + 12 - k * 2.2), (sx + 4, by + 14 - k * 2.2), (sx + 6 + k, by + 21 - k * 2.2)], CARA[3], outline=CARA[0])
    for k in range(3):                                                     # and a few on the rear
        sx = -40 + k * 7
        a.poly([(sx, by + 9), (sx + 4, by + 11), (sx - 2, by + 17)], CARA[3], outline=CARA[0])

    # ---- the near legs
    for hx, side, k in hips[1::2]:
        leg(hx, side, foot_of(hx, side, k, sag), near, 7)

    # ---- the small claw, low in front
    sx0, sy0 = 24, by - 6
    ht = (50 + math.sin(ph * 2) * 1.6 + st * 12, by - 9 + math.sin(ph * 2 + 1) * 1.5)
    ht = mixp(ht, (48, 4), sag)
    el, hd = arm_ik((sx0, sy0), ht, 19, 19, -1)
    el = (el[0], max(el[1], 3))
    a.limb([(sx0, sy0), el], near, 5)
    a.limb([el, hd], near, 4)
    pincers(a, hd, math.atan2(hd[1] - el[1], hd[0] - el[0]) * .5, .52, .35 + .5 * abs(math.sin(ph * 2)) * (1 - dn), near)

    # ---- the crusher: raised over the shell on the wind-up, slammed down on the strike, dropped on death
    shoulder = (35, by + 5)
    idle = (76 + math.sin(ph) * 1.5, by + 9 + math.sin(ph) * 1.5)
    hand = mixp(idle, (62, by + 74), sm(w))
    hand = mixp(hand, (88, 7), sm(st))
    hand = mixp(hand, (70, 5), sag)
    if hurt:
        hand = (hand[0] - 3, hand[1] + 3)
    elbow, hand = arm_ik(shoulder, hand, 37, 37, -1)
    elbow = (elbow[0], max(elbow[1], 6))
    a.limb([shoulder, elbow], near, 12)
    a.limb([elbow, hand], near, 10)
    ang = math.atan2(hand[1] - elbow[1], hand[0] - elbow[0])
    pincers(a, hand, ang, 1.0, clamp01(.35 + w * .65 - st * .3 + (math.sin(ph) * .08 if clip == 'idle' else 0) + (.5 if hurt else 0) - sag * .6), near)
    # ---- the eye stalks and the mouthparts
    sway = math.sin(ph * 1.3) * 1.2 * (1 - dn)
    for k, (bx, tip_dx, tip_dy) in enumerate(((36, 9 + sway, 22), (27, 5 - sway, 27))):
        b = (bx, by + 16)
        tip = (bx + tip_dx + w * 2, by + 16 + tip_dy - sag * 12 - fall * 6)
        a.limb([b, ((b[0] + tip[0]) / 2 + 1, (b[1] + tip[1]) / 2), tip], near, 4)
        shut = dn > .5
        if shut:
            a.line([(tip[0] - 4, tip[1]), (tip[0] + 4, tip[1] - 1)], CARA[0], 2)
        else:
            a.ball(tip[0], tip[1], 7.6, 6.6, [LAMP[0], LAMP[1], LAMP[2], LAMP[3], LAMP[4]], 0)
            a.line([(tip[0] + .8, tip[1] - 6), (tip[0] + .8, tip[1] + 6)], OUTLINE, 2)       # a slit pupil
            a.poly([(tip[0] - 7, tip[1] + 8), (tip[0] + 6, tip[1] + 2), (tip[0] + 7, tip[1] + 6), (tip[0] - 2, tip[1] + 10)], CARA[1], outline=CARA[0])     # a spiked, scowling brow
            a.poly([(tip[0] - 7, tip[1] + 8), (tip[0] - 10, tip[1] + 13), (tip[0] - 3, tip[1] + 9)], CARA[3], outline=CARA[0])
    for k in range(4):                                                     # serrated mouthparts
        mx = 41 + k * 2.4
        a.poly([(mx, by - 3 - k * .6), (mx + 1.8, by - 3 - k * .6), (mx + .8, by - 8 - k * .6)], BONE[2], outline=CARA[0])
    # ---- the strike: the rod discharges into the slammed claw; dust on impact
    if clip == 'attack' and n in (3, 4, 5):
        zig(a, rod_tip, (hand[0] + 6, hand[1] + 10), LAMP[4], steps=7, amp=6, seed=n, width=2)
        zig(a, rod_tip, (hand[0] + 6, hand[1] + 10), LGT[2], steps=7, amp=6, seed=n + 3, width=1)
    if clip == 'attack' and n in (4, 5, 6):
        for k in range(4):
            dust(a, hand[0] - 6 + k * 8, 4 + (k % 2) * 3, 3.4 - k * .4, PEARL)
    if clip == 'attack' and n in (1, 2):                                   # sparks round the rod as the charge builds
        for k in range(3):
            zig(a, rod_tip, (rod_tip[0] + (k - 1) * 14, rod_tip[1] + 6 + k * 3), LGT[3], steps=4, amp=3, seed=n + k)
    if clip == 'idle' and n % 3 == 1:
        zig(a, rod_tip, (rod_tip[0] + 9, rod_tip[1] + 7), LGT[3], steps=3, amp=2, seed=n)
    if dn > .8:
        for k in range(3):
            dust(a, -40 + k * 30, 3 + (k % 2) * 2, 3., PEARL)
    return a


# ---- the Stormtusk -------------------------------------------------------------------------------------------------------------
def stormtusk(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    lunge = st * 18 - w * 7 + recoil - 10
    a = Painter('stormtusk', lunge)
    sag = sm(clamp01(dn * 1.7))                                            # the forebody drops first
    lie = sm(clamp01((dn - .3) * 1.5))                                     # then it lies flat on its belly
    rear = sm(w) * (1 - sm(st))                                            # the forebody rears up on the wind-up
    gait = math.sin(ph) if walk else 0.
    base = 22 + bob * .4 - sag * 9 - lie * 7 - (2 if hurt else 0)          # the height of the body line
    sway = math.sin(ph * 1.2) * 3 * (1 - lie)
    head_x = 58 + st * 8 - w * 6
    head_y = base + 14 + rear * 26 - st * 5 - sag * 8 - lie * 4
    spine = [(-72, base + 2 + sway), (-48, base + 6 + sway * .5), (-20, base + 9), (8, base + 10 + rear * 5), (34, base + 13 + rear * 14), (head_x - 6, head_y)]
    spine = [(x, max(y, 14.)) for x, y in spine]
    # ---- the far flipper, behind the body
    def flipper(root, sd, ramp):
        reach = 22 + gait * sd * 9 + st * 6 - rear * 8
        tip = (root[0] + reach, max(3.5, 2 + max(0., gait * sd) * 8 - rear * 0))
        tip = mixp(tip, (root[0] + 14, 3.5), lie)
        mid = ((root[0] + tip[0]) / 2 + 2, (root[1] + tip[1]) / 2 - 4)
        a.limb([root, mid], ramp, 11)
        a.limb([mid, tip], ramp, 8)
        a.ball(tip[0] + 2, max(tip[1], 3), 8, 3.2, ramp, 0)
    far_root = (22 + rear * 6, base - 6)
    flipper(far_root, -1, [BLK[0], BLK[0], BLK[1], BLK[2], BLK[2]])
    # ---- the tail and its flukes
    tl = spine[0]
    shaded(a, [(tl[0] + 2, tl[1] + 3), (tl[0] - 16, tl[1] + 22 + sway * .5), (tl[0] - 6, tl[1] + 5), (tl[0] - 20, tl[1] - 5 + sway), (tl[0] + 2, tl[1] - 3)], BLK, base=.5, contrast=1.1)
    # ---- the body: black glass over a pale belly
    taper_w = [10, 30, 40, 44, 40, 34]
    tapered(a, [(x, y) for x, y in spine], 12, 46, BLK, base=.52, contrast=1.15)
    belly = [(x + 2, y - 13) for x, y in spine[1:5]]
    tapered(a, belly, 12, 17, BELLY, base=.5, contrast=.8, edge=False)
    # glowing cracks along the back; they go dark one by one as it dies
    for i, (cx_, cy_, ln) in enumerate(((-56, base + 10, 14), (-30, base + 16, 20), (-4, base + 21, 18), (22, base + 24 + rear * 8, 15))):
        gone = clamp01(dn * 1.7 - i * .12)
        if gone >= 1:
            continue
        pts = [(cx_, cy_), (cx_ + 5, cy_ - ln * .4), (cx_ + 2, cy_ - ln * .6), (cx_ + 9, cy_ - ln)]
        a.line(pts, LGT[1 if gone > .5 else 2], 3)
        if gone < .5:
            a.line(pts, LGT[4], 1)
    # ---- the head: a heavy melon, a short beak of needle teeth, a sunken eye and old scars
    gape = 4.5 if (clip == 'attack' and 3 <= n <= 5) or hurt or lie > .4 else 1.2
    a.ball(head_x, head_y, 22, 18, BLK, .08)
    a.ball(head_x + 19, head_y - 6, 14, 8.5, BLK, -.12)
    a.ball(head_x + 11, head_y - 12 - gape, 14, 5, [BELLY[0], BELLY[1], BELLY[2], BELLY[3], BELLY[3]], 0)          # the lower jaw
    a.poly([(head_x + 4, head_y - 9), (head_x + 32, head_y - 7), (head_x + 30, head_y - 10 - gape), (head_x + 5, head_y - 11 - gape)], BLK[0])           # the mouth
    for k in range(7):                                                      # needle teeth, upper and lower
        tx = head_x + 8 + k * 3.4
        fang(a, tx, head_y - 9, 4.6, 1.8, -math.pi / 2 + .12, BONE)
        fang(a, tx + 1, head_y - 11 - gape, 4.6, 1.8, math.pi / 2 - .12, BONE)
    ex, ey = head_x + 7, head_y + 5
    a.ball(ex, ey, 4.8, 4, [BLK[0], BLK[0], BLK[0], BLK[1], BLK[1]], 0)    # a sunken socket
    if dn > .22:
        a.line([(ex - 3, ey), (ex + 3, ey - 1)], OUTLINE, 2)
    else:
        a.ellipse(ex, ey, 2.4, 1.2, LGT[4])                                # a white slit of an eye
        a.line([(ex - 2.5, ey), (ex + 2.5, ey)], LGT[4], 1)
        a.line([(ex + .5, ey - 1.5), (ex + .5, ey + 1.5)], OUTLINE, 1)
    a.line([(ex - 6, ey + 4), (ex + 8, ey + 1)], BLK[0], 2)                # a heavy brow
    a.line([(head_x - 8, head_y + 10), (head_x + 4, head_y - 3)], BELLY[2], 1)         # old scars
    a.line([(head_x - 4, head_y + 12), (head_x + 8, head_y - 1)], BELLY[2], 1)
    a.line([(head_x + 20, head_y - 3), (head_x + 25, head_y - 8)], BELLY[2], 1)
    near_root = (26 + rear * 8, base - 4)
    flipper(near_root, 1, [BLK[0], BLK[1], BLK[2], BLK[3], BLK[3]])
    # ---- the tusk: a long spiral of pale glass from the upper jaw; it snaps as the beast falls
    tang = .28 + rear * .5 - st * .34 + (.04 * math.sin(ph) if clip == 'idle' else 0) - lie * .15
    root = (head_x + 22, head_y + 1)
    snap = sm(clamp01((dn - .3) * 3))
    length = 72
    tip = (root[0] + math.cos(tang) * length, root[1] + math.sin(tang) * length)
    if snap < .02:
        fang(a, root[0], root[1], length, 9.4, tang, [LGT[0], LGT[2], LGT[3], LGT[3], LGT[4]])
        for k in range(1, 9):                                               # the spiral: slanted bands along the tusk
            t = k / 9.
            cx_, cy_ = root[0] + math.cos(tang) * length * t, root[1] + math.sin(tang) * length * t
            wd = 3.6 * (1 - t)
            a.line([(cx_ - wd, cy_ + wd * .4 - 1), (cx_ + wd, cy_ - wd * .6 + 1)], LGT[1], 1)
        glow(a, tip[0], tip[1], 8 + st * 7 + w * 3, LGT, 1.)
        # lightning crackles off the tip and the cracks
        arcs = 3 if clip == 'attack' and 3 <= n <= 5 else (2 if clip == 'attack' else 1)
        for k in range(arcs):
            q = (tip[0] + 8 + 9 * k, tip[1] + (-1) ** (k + n) * (6 + 6 * k))
            zig(a, tip, q, LGT[4], steps=4, amp=4, seed=n * 3 + k, width=1)
    else:
        stump = (root[0] + math.cos(tang) * 20, root[1] + math.sin(tang) * 20)
        fang(a, root[0], root[1], 20, 9.4, tang, [LGT[0], LGT[2], LGT[3], LGT[3], LGT[4]])
        fx = mix(stump[0] + 8, root[0] + 44, snap)                         # the rest falls forward and lies on the sand
        fy = mix(stump[1] + 22, 6, snap)
        a.poly([(fx - 28, fy + 3), (fx + 28, fy + 6), (fx + 28, fy + 1), (fx - 28, fy - 2)], LGT[3], outline=LGT[0])
        a.poly([(fx - 28, fy + 3), (fx - 4, fy + 5), (fx - 4, fy + 1)], LGT[2])
    if clip == 'attack' and n in (5, 6):                                    # the lunge lands: sand thrown up round the flippers
        for k in range(4):
            dust(a, 44 + k * 9, 4 + (k % 2) * 3, 3.2 - k * .4, PEARL)
    if clip == 'attack' and n in (1, 2):                                    # a flipper rakes the sand
        for k in range(3):
            dust(a, 30 + k * 7, 3 + k, 2.4, PEARL)
    if dn > .8:
        for k in range(3):
            dust(a, -44 + k * 30, 3 + (k % 2) * 2, 2.8, PEARL)
    return a


DRAW = dict(lamphermit=lamphermit, stormtusk=stormtusk)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/storm_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='storm-elite')
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
        atlas.save(ASSETS / f'stormelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'stormelites_{kind}.png').convert('RGBA')
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
