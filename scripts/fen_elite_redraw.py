#!/usr/bin/env python3
"""Gloamfen's two new elites (zone shapes pilot): native PixelFlow sources, per-kind frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye face. Each kind has its own face and silhouette:
  bellowmaw    a bull toad the size of a boat: a warty olive back studded with glowing orange glands, two bulging eyes with horizontal slit pupils under heavy brow
               ridges, a mouth full of fangs and a throat sac that swells with the bellow. Rears up and fills the sac, then lunges with the mouth gaping and the tongue
               lashing out in a ring of sound. Dies: the sac empties, the legs give way, the tongue lolls and the eyes cross.
  rustmarshal  a drowned garrison captain in rusted plate: barnacled pauldrons, a cage helm with two cyan slits for eyes, kelp for a tabard, a dead lantern at the belt
               and a barnacled ship's anchor on a chain for a weapon. Swings the anchor back over the head, then slams it down. Dies: the knees go, the plate falls
               in on itself, the anchor drops and the eyes go out.
Eight distinct attack and death frames each. The manifest is client/assets/fenelites.txt. Drawing helpers come from the Lapis redo.
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
OUT = ROOT / 'test-results/fen-elites'
REGISTRY = ROOT / 'scripts/fen_elite_sources.txt'
MANIFEST = ASSETS / 'fenelites.txt'
PREFIX = 'valhallasc_fen_elite_'
KINDS = ['bellowmaw', 'rustmarshal']
KIND_FRAMES = dict(bellowmaw=(164, 80, 50, 74), rustmarshal=(146, 145, 58, 138))
FLYING = ()
_mine = [
    '#0e1a0a', '#26421a', '#4a7a28', '#86b240', '#c8e070',   # MOSS (the toad's hide)
    '#3a1406', '#8a3a10', '#d8741c', '#f4b840', '#fff0a0',   # SAC (glowing glands, the throat sac)
    '#2a2a14', '#6a6a34', '#a8a860', '#d4d494', '#f2f2c8',   # BELLY (pale underside)
    '#1c0c08', '#4e2414', '#8a4a24', '#c07a3c', '#e8b068',   # PLATE (rusted iron)
    '#10141c', '#2a3444', '#566478', '#8ea0b4', '#cfdce8',   # STEEL (cold plate, chain)
    '#032a2e', '#0a6e74', '#28c4c0', '#8af0e0', '#e8fff8',   # WISP (the captain's eyes and lantern)
    '#08181a', '#143a38', '#26665a', '#4a9a7a', '#8ac8a0',   # KELP (tabard, crest streamers)
    '#2a0a12', '#6a1420', '#c02a30', '#f06a50', '#ffd0a0',   # BLOOD (mouth, tongue)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
MOSS, SAC, BELLY, PLATE, STEEL, WISP, KELP, BLOOD = [_i[5 * k:5 * k + 5] for k in range(8)]


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


# ---- Bellowmaw -------------------------------------------------------------------------------------------------------
def bellowmaw(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    lie = sm(clamp01((dn - .25) * 1.4))
    flinch = 1 if clip == 'die' and n == 1 else 0                                  # the first beat of the death: thrown back, mouth open
    a = Painter('bellowmaw', st * 7 - w * 5 + recoil + lie * 3 - flinch * 3)
    walk = clip == 'walk'
    base = 24 + bob * .6 + w * 6 - st * 4 - lie * 14 - fall * 2                # belly height over the ground
    tilt = -w * .05 + st * .05 + lie * .04
    r = Rig(a, 0, base, tilt)
    puff = clamp01(w * 1.05 + (.22 if clip == 'idle' and n in (2, 3, 4) else 0) + flinch * .5) * (1 - lie)      # the throat sac
    gape = clamp01(w * .5 + st * 1.1 + (.35 if clip == 'hurt' and n == 0 else 0)) * (1 - lie * .5) + lie * .35
    dark = [MOSS[0], MOSS[0], MOSS[1], MOSS[1], MOSS[2]]

    def arm(x, far):
        reach = 9 + w * 3 - st * 4 + lie * 8
        sw = math.sin(ph + (0 if far else math.pi)) * 5 if walk else 0
        lift = max(0, math.cos(ph + (0 if far else math.pi))) * 3 if walk else 0
        hip = (x, base + 2)
        elbow = (x + 7 + sw * .5 - lie * 5, max(base - 9 - lie * 2, 7))
        hand = (x + reach + sw + lie * 12, 3 + lift)
        ramp = dark if far else MOSS
        a.limb([hip, elbow, hand], ramp, 10)
        for k in (-1, 0, 1):
            a.ellipse(hand[0] + 4 + k * 3.4, hand[1] - .5 - abs(k) * .4, 3, 1.8, ramp[2])           # webbed fingers

    def hind(x, p0, far):
        sw = math.sin(ph + p0) * 6 if walk else 0
        lift = max(0, math.cos(ph + p0)) * 4 if walk else 0
        ramp = dark if far else MOSS
        heel = (x - 13 + sw - lie * 8, 5 + lift)
        toe = (x + 14 + sw + lie * 10, 4.5 + lift)
        a.limb([(x - 2, max(base - 3, 8)), (x - 15 + sw * .5, max(base * .5, 7)), heel], ramp, 9)
        a.limb([heel, (x + 1 + sw, 6 + lift), toe], ramp, 6)
        a.ball(x - 1, max(base + 3, 16), 17, 15 - lie * 3, ramp, .2)
        for k in (-1, 0, 1):
            a.ellipse(toe[0] + 3 + k * 3, toe[1] - .3, 3, 1.6, ramp[2])

    arm(18, True)
    hind(-22, 2.4, True)
    # the body: a heavy hill, a pale belly, a back studded with warts, a few of them burning orange
    body_ry = 24 - lie * 8
    r.ball(-2, max(base + 6, body_ry + 1), 41, body_ry, MOSS, -.06)
    r.ball(4, max(base - 7, 12), 32, 11 - lie * 3, BELLY)
    r.ball(-16, base + 23, 12, 6, [MOSS[1], MOSS[2], MOSS[3], MOSS[3], MOSS[4]], .1)
    for k in range(15):
        x = -37 + k * 4.9
        top = base + 6 + 24 * math.sqrt(max(0., 1 - ((x + 2) / 41) ** 2))
        rad = 2.2 + (k % 4) * .55
        if k % 3 == 1:
            r.ball(x, top - 1.5, rad + .6, rad + .6, SAC)
        else:
            r.ball(x, top - 2 - (k % 3), rad, rad * .8, [MOSS[1], MOSS[2], MOSS[3], MOSS[3], MOSS[4]])
    for k in range(5):                                                         # the dark blotches of the flank
        r.ellipse(-30 + k * 12, base + 3 + (k % 2) * 6, 3.6, 2.6, MOSS[0])
    hind(-22, 0, False)
    # the throat sac: nothing at rest, a bright blister when it bellows
    if puff > .04 or lie > .3:
        s = max(puff, lie * .35)
        sry = 5 + s * 14 - lie * 3
        sx, sy = 36 + s * 4, max(base - 6 - s * 4, sry + 1.5)
        a.ball(sx, sy, 8 + s * 17, sry, SAC)
        for k in range(4):
            a.line([(sx - 6 + k * 4, sy + 3 * s), (sx - 3 + k * 4, sy - 5 * s), (sx - 7 + k * 5, sy - 9 * s)], SAC[1], 1)
    # the head: wide and flat, two bulging eyes, a heavy brow, a mouth full of teeth
    hd = Rig(a, 24, base + 8, tilt + w * .2 - st * .08 - lie * .12)
    T = lambda x, y: r.t(*hd.t(x, y))
    hx, hy = 40, base + 10
    a.ball(*T(hx - 6, hy + 3), 17, 13, MOSS, tilt)
    jaw_tip = (hx + 23, hy - 4 - gape * 18)
    a.poly([T(hx - 8, hy + 3), T(hx + 26, hy + 2.6), T(*jaw_tip), T(hx - 8, hy - 5)], BLOOD[1] if gape > .1 else OUTLINE, outline=OUTLINE)
    a.limb([T(hx - 8, hy - 3), T(hx + 8, hy - 5 - gape * 9), T(*jaw_tip)], [MOSS[0], MOSS[1], MOSS[2], MOSS[2], MOSS[3]], 7)
    a.ball(*T(hx + 12, hy + 5), 20, 8.6, MOSS, tilt)
    for k in range(7):                                                         # teeth, top and bottom
        fang(a, *T(hx + 1 + k * 3.8, hy + 2.2), 4.2 - (k % 2), 2.2, -1.57 + hd.phi, BONE)
        fang(a, *T(hx + 3 + k * 3.4, hy - 4.6 - gape * (4 + k * 2)), 4 - (k % 2), 2.2, 1.57 + hd.phi, BONE)
    if st > .15 or lie > .5:
        tl = st * 34 + lie * 8
        tg = bez((hx + 2, hy - 3 - gape * 5), (hx + 22 + st * 14, hy - 3 - gape * 5 + 6 - lie * 14), (hx + 28 + tl, max(hy - 7 - gape * 9 - lie * 10 + st * 2, 5 - base + base)), 10)
        taper(a, [T(*p) for p in tg], BLOOD, 6, 3)
    for k, (ex, ey, er) in enumerate(((hx - 4, hy + 15, 7.2), (hx + 12, hy + 14, 6.6))):
        a.ball(*T(ex, ey), er, er, MOSS)
        a.ball(*T(ex + .8, ey - .6), er * .82, er * .78, SAC)
        if dying(clip, n):
            cross_eye(a, *T(ex + .8, ey - .6), 2.4)
        else:
            a.ellipse(*T(ex + 1, ey - .6), 4.4, 1.3, OUTLINE)                    # the slit pupil, flat
            a.ellipse(*T(ex - 1.6, ey + 1.6), 1.1, .9, SAC[4])
        a.poly([T(ex - er - 1, ey + er * .5), T(ex + er + 1.4, ey + er * .1 - k * .6), T(ex + er + 1.4, ey + er * .1 + 2.6), T(ex - er - 1, ey + er * .5 + 4)], MOSS[0], outline=OUTLINE)   # the heavy brow, over the eye
    a.ellipse(*T(hx + 29, hy + 6), 1.4, 1, OUTLINE)
    for k in range(2):
        fang(a, *T(hx - 10 + k * 15, hy + 20), 7, 3.6, 1.57 + k * .35 - .3 + hd.phi, MOSS)
    arm(22, False)
    if clip == 'attack' and n in (4, 5, 6):                                    # the bellow: rings of sound
        for k in range(3):
            c = T(hx + 28, hy - 6)
            pts = [(c[0] + math.cos(t) * (9 + k * 8 + (n - 4) * 3), c[1] + math.sin(t) * (7 + k * 6 + (n - 4) * 2)) for t in np.linspace(-.9, .9, 9)]
            a.line(pts, SAC[4] if k % 2 else SAC[3], 1)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, 10 + k * 14, 4 + (k % 2) * 3, 3.2 - k * .5, PEARL)
    return a


# ---- Rustmarshal -----------------------------------------------------------------------------------------------------
def rustmarshal(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.05)
    lie = sm(clamp01((dn - .2) * 1.3))
    a = Painter('rustmarshal', st * 7 - w * 6 + recoil + lie * 5)
    walk = clip == 'walk'
    hip = 43 + bob * .5 - lie * 24 - fall * 2 + w * 1.5 - st * 3
    lean = -w * .09 + st * .13 + lie * .55
    R = Rig(a, 0, hip, lean)
    dark = [STEEL[0], STEEL[0], STEEL[1], STEEL[1], STEEL[2]]
    lit = [STEEL[0], STEEL[1], STEEL[1], STEEL[2], STEEL[3]]

    def leg(x, p0, far):
        sw = math.sin(ph + p0) * 7 if walk else 0
        lift = max(0, math.cos(ph + p0)) * 5 if walk else 0
        if clip == 'attack':
            sw = (st * 5 if x > 0 else -st * 3) - w * 3
        foot = (x + sw + lie * (11 if x > 0 else -9), 3 + lift)
        knee = (x + 4 + sw * .4 + lie * (7 if x > 0 else 1), hip * .5 + lift * .5 - lie * 3)
        ramp = dark if far else lit
        a.limb([(x, hip), knee, foot], ramp, 10)
        a.ball(knee[0] + 1, knee[1], 6.4, 6, [PLATE[0], PLATE[1], PLATE[2], PLATE[2], PLATE[3]] if not far else dark)
        a.ellipse(foot[0] + 3, foot[1] + 1.2, 9, 3.6, PLATE[0])
        a.ellipse(foot[0] + 4, foot[1] + 2, 7, 2.4, PLATE[2] if not far else PLATE[1])
        for k in range(3):
            a.ball(foot[0] - 1 + k * 4, foot[1] + 4, 1.4, 1.2, BONE)

    leg(-5, 0, True)
    # the weapon's pose: the anchor hangs, swings back over the head on the wind-up, slams the ground on the strike
    hand_idle, hand_up, hand_dn = (27, hip + 8), (-12, hip + 70), (33, hip + 20)
    hand = mixp(mixp(hand_idle, hand_up, w), hand_dn, st)
    if clip == 'idle':
        hand = (hand[0] + math.sin(ph) * 1.2, hand[1] + math.cos(ph) * .8)
    anc_idle, anc_up, anc_dn = (33, 12 + math.sin(ph * .7) * 1.2), (-30, hip + 66), (52, 28)
    anc = mixp(mixp(anc_idle, anc_up, w), anc_dn, st)
    if lie:
        hand = (24 + lie * 10, hip + 4)
        anc = (46 + lie * 12, 6)
    far_arm = [(-8, hip + 36), (-16, hip + 22 - lie * 8), (-10 + lie * 4, hip + 8 - lie * 6)]
    a.limb([R.t(*far_arm[0]), R.t(*far_arm[1]), R.t(*far_arm[2])], dark, 7)
    # the lantern at the far hand: a dead cage, a cyan coal inside it while the captain stands
    lx, ly = R.t(far_arm[2][0] - 2, far_arm[2][1] - 9)
    a.line([R.t(*far_arm[2]), (lx, ly + 3)], PLATE[0], 1)
    a.ball(lx, ly, 3.8, 4.4, [PLATE[0], PLATE[0], PLATE[1], PLATE[2], PLATE[2]] if dn > .3 else [OUTLINE, WISP[1], WISP[2], WISP[3], WISP[4]])
    a.line([(lx - 3.8, ly), (lx + 3.8, ly)], PLATE[0], 1)
    a.line([(lx, ly - 4.4), (lx, ly + 4.4)], PLATE[0], 1)
    # the torso: a barnacled breastplate, a tabard of kelp, a belt of chain
    R.poly([(-11, hip + 6), (13, hip + 5), (14, hip - 16 - (n % 2)), (9, hip - 12), (5, hip - 21), (0, hip - 13), (-5, hip - 20), (-10, hip - 12), (-13, hip - 17)], KELP[1], outline=OUTLINE)
    R.poly([(-4, hip + 5), (3, hip + 4), (4, hip - 12), (-2, hip - 9)], KELP[2])
    R.ball(1, hip + 23, 15.5, 22, [PLATE[0], PLATE[1], PLATE[1], PLATE[2], PLATE[2]], -.03)
    R.ball(6, hip + 29, 8, 12, [PLATE[1], PLATE[1], PLATE[2], PLATE[2], PLATE[3]])
    R.poly([(-6, hip + 30), (3, hip + 33), (4, hip + 22), (-5, hip + 20)], STEEL[1], outline=OUTLINE)
    R.line([(-14, hip + 10), (-4, hip + 7), (6, hip + 8), (15, hip + 11)], STEEL[2], 3)
    for k in range(9):
        R.ellipse(-12 + k * 3.2, hip + 8.5 - (k % 2) * 1.4, 1.5, 1.3, STEEL[3])
    for k, (bx, by, rr) in enumerate(((-8, 28, 2.2), (-5, 33, 1.7), (6, 20, 2), (9, 33, 1.5), (-9, 16, 1.4), (2, 13, 1.7))):
        R.ball(bx, hip + by, rr, rr * .8, BONE)
    leg(6, math.pi, False)
    # the head and pauldrons: a bascinet with a barred face guard, two cyan slits, rusted horns, kelp streaming from the crest
    hd = Rig(a, 2, hip + 44, lean * .6 - w * .1 + st * .12 + lie * .3)
    T = lambda x, y: R.t(*hd.t(x, y))
    R.ball(-9, hip + 38, 9.4, 8, STEEL, .2)
    for k in range(4):
        sway = math.sin(ph * 1.3 + k) * 2.2 if clip in ('idle', 'walk') else -st * 4
        tg = bez((-4, hip + 62), (-12 - k * 3 + sway, hip + 62 - k * 2 - lie * 12), (-22 - k * 5 + sway * 1.6, hip + 52 - k * 4 - lie * 20), 6)
        taper(a, [T(*p) for p in tg], KELP, 3.2, .8)
    a.ball(*T(2, hip + 56), 11, 12.5, STEEL, lean)
    a.poly([T(5, hip + 63), T(21, hip + 56), T(22, hip + 45), T(11, hip + 43), T(3, hip + 46)], STEEL[2], outline=OUTLINE)
    a.poly([T(9, hip + 55.5), T(21, hip + 53), T(21, hip + 48.5), T(9, hip + 50.5)], OUTLINE)
    for k in range(4):
        a.line([T(8 + k * 4.2, hip + 44.4), T(8 + k * 4.2, hip + 56)], STEEL[1], 1)
    for ex in (12.5, 17.8):
        gx, gy = T(ex, hip + 52)
        if dying(clip, n, 2):
            a.line([(gx - 2, gy), (gx + 2, gy)], OUTLINE, 1)
        else:
            a.ellipse(gx, gy, 3, 2.1, WISP[1])
            a.ellipse(gx, gy, 2, 1.2, WISP[4])
    for k, (x0, s0) in enumerate(((-3, 1.), (7, .8))):
        hn = bez((x0, hip + 63), (x0 + 6 * s0, hip + 76), (x0 + 20 * s0, hip + 74), 7)
        taper(a, [T(*p) for p in hn], [PLATE[0], PLATE[1], PLATE[2], PLATE[3], BONE[3]], 5, 1)
    R.ball(14, hip + 39, 11, 9.4, STEEL, -.2)
    for k in range(4):
        R.fang(8 + k * 4.2, hip + 46.5 - (k % 2) * 1.2, 6, 3, .9 - k * .4, BONE)
    # the near arm and the anchor on its chain
    shoulder = R.t(14, hip + 36)
    elbow = (shoulder[0] + 9 + st * 5 - w * 14, shoulder[1] - 9 + w * 14 - lie * 6)
    a.limb([shoulder, elbow, hand], lit, 8)
    a.ball(*hand, 5, 4.6, [PLATE[0], PLATE[1], PLATE[2], PLATE[2], PLATE[3]])
    ch = bez(hand, ((hand[0] + anc[0]) / 2, min(hand[1], anc[1]) - 12 - w * 6 + st * 10), anc, 12)
    for k, p in enumerate(ch[1:-1]):
        a.ball(p[0], p[1], 2.6, 2.0 + (k % 2) * .6, STEEL if k % 2 else [STEEL[0], STEEL[1], STEEL[2], STEEL[2], STEEL[3]])
    ang = math.atan2(anc[1] - ch[-2][1], anc[0] - ch[-2][0])
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    tip = (anc[0] + dx * 24, anc[1] + dy * 24)
    a.ball(anc[0], anc[1], 4.2, 4.2, [STEEL[0], STEEL[1], STEEL[2], STEEL[3], STEEL[4]])
    a.limb([anc, tip], [STEEL[0], STEEL[1], STEEL[2], STEEL[3], STEEL[3]], 7)
    cb = (anc[0] + dx * 7, anc[1] + dy * 7)
    a.limb([(cb[0] + nx * 12, cb[1] + ny * 12), (cb[0] - nx * 12, cb[1] - ny * 12)], [STEEL[0], STEEL[1], STEEL[2], STEEL[2], STEEL[3]], 5)
    for s in (-1, 1):
        a.poly([tip, (tip[0] - dx * 13 + nx * s * 14, tip[1] - dy * 13 + ny * s * 14), (tip[0] - dx * 6 + nx * s * 5, tip[1] - dy * 6 + ny * s * 5)], STEEL[2], outline=OUTLINE)
        a.ellipse(tip[0] - dx * 8 + nx * s * 8, tip[1] - dy * 8 + ny * s * 8, 1.8, 1.5, BONE[3])
    if clip == 'attack' and n in (4, 5):                                       # splinters and silt thrown by the slam
        for k in range(5):
            a.ball(anc[0] + 8 + k * 4, 12 + (k % 2) * 7 - k * .8, 2.6 - k * .3, 2.2 - k * .25, PLATE)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, anc[0] + 6 + k * 8, 4 + (k % 2) * 3, 3.2 - k * .5, PEARL)
    if clip == 'idle' and n in (1, 4):                                         # water running off the plate
        for k in range(2):
            a.ellipse(-2 + k * 16, hip - 14 + (n % 3) * 2, 1.2, 1.6, WISP[2])
    return a


DRAW = dict(bellowmaw=bellowmaw, rustmarshal=rustmarshal)
# the shared frame/preview machinery reads these names
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/fen_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='fen-elite')
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
        atlas.save(ASSETS / f'fenelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'fenelites_{kind}.png').convert('RGBA')
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
