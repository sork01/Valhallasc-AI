#!/usr/bin/env python3
"""The Stormglass Shore (zone 19, index 18 in map.txt) redo: five native PixelFlow sources with per-kind frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner direction (2026-11-04): every enemy must look UNIQUE and MEAN, with no shared round-eye-plus-blush face. Each
kind builds its own face with its own routine: stalked bulb eyes with a red bar pupil over serrated mandibles
(saltclaw), one hooked-beak raptor with a lightning-white slit eye (stormgull), hollow blade sockets in a glass
wedge head (glassray), a single cyclops lantern slit in a barnacled stone helm (breakersentinel), and one huge
half-open bloodshot eye in a sealed heart (maelstromheart, the zone's "sealed eye beneath the sea"). Shaded volume
(`plate`/`ball`/`taper`), props at least four pixels thick, eight distinct attack frames (wind-up, strike, recovery)
and eight distinct death frames per kind. Storm effects are attached to the body (arcs along feathers/limbs), never
loose glyphs. The original cel-shaded art is kept in /media/raid/valhallasc-data/stormglass-slime-original-20261104
(`scripts/rollback_stormglass_art.py`).
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
from moonspore_slime_redraw import (
    PALETTE as BASE_PALETTE, plate, blob, fang, dust, curves,
    BARK, VOID, GHOST,
)
from astral_slime_redraw import (
    Painter as BasePainter, OUTLINE, WHITE, EYE_WHITE,
    BONE, PLATE, PURPLE, TEAL, GOLD, GREEN, FUR, BLUE, BROWN, OLIVE, PINK, MAROON, CORAL, PEARL, VIOLET, CRIMSON,
    AMBER, AZURE, SLATE, mix, mixp, rot, sm, bez, taper, foot, arm_ik,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/stormglass-slime'
REGISTRY = ROOT / 'scripts/stormglass_slime_sources.txt'
PREFIX = 'valhallasc_stormglass_slime_style_'
KINDS = ['saltclaw', 'stormgull', 'glassray', 'breakersentinel', 'maelstromheart']
NAMES = dict(zip(KINDS, ['Saltclaw', 'Stormgull', 'Glassray', 'Breakersentinel', 'Maelstromheart']))
MANIFEST = ASSETS / 'stormglass.txt'
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    saltclaw=(100, 62, 46, 56),
    stormgull=(85, 80, 42, 74),
    glassray=(113, 77, 56, 71),
    breakersentinel=(120, 93, 41, 87),
    maelstromheart=(102, 70, 51, 64),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('stormgull', 'glassray', 'maelstromheart')
PALETTE = BASE_PALETTE[:] + [
    '#082428', '#1a545a', '#38949a', '#78d0c0', '#c4f4e4',   # SHELL (brine-teal crab carapace)
    '#46565e', '#889ca4', '#c2d0d2', '#eaf2f0', '#fcfffd',   # SALT (encrusted crystals)
    '#0a1024', '#223458', '#566f9c', '#a0b8d6', '#e6f0fb',   # STORM (gull plumage)
    '#1c3c82', '#4c8ee0', '#8cdcff', '#d2f6ff', '#f4feff',   # BOLT (lightning)
    '#03203a', '#0c5684', '#26a0c2', '#74dcda', '#d4fff4',   # SEAGLASS (the ray)
    '#121a22', '#36464f', '#667c86', '#98b0b0', '#d2e0d8',   # STONE (the sentinel)
    '#58563f', '#989678', '#c8c6a6', '#e6e4c8', '#fafae4',   # BARNACLE
    '#2a1608', '#683a1c', '#a6622a', '#d6984e', '#f4cc86',   # RUST (anchor iron)
    '#12062a', '#381456', '#782a88', '#c05ab0', '#f0a0d6',   # HEART (bruised flesh)
    '#08143c', '#1a3a88', '#3870ca', '#7eb2ee', '#d0eafe',   # TIDE (vortex water)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
_n = len(BASE_PALETTE)
SHELL, SALT, STORM, BOLT, SEAGLASS, STONE, BARNACLE, RUST, HEART, TIDE = [list(range(_n + 5 * i, _n + 5 * i + 5)) for i in range(10)]


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Art scale per kind (1.0 = the coordinates written in the draw functions); judged on an in-game screenshot.
SCALE = dict(saltclaw=.52, stormgull=.54, glassray=.56, breakersentinel=.62, maelstromheart=.52)


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.S = SCALE.get(kind, 1.)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax - 2 + dx * self.S

    def pos(self, x, y):
        return round(self.cx + x * self.S), round(self.ay - y * self.S)

    def ellipse(self, x, y, rx, ry, col):
        super().ellipse(x, y, rx * self.S, ry * self.S, col)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width * self.S)))

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        super().ball(x, y, rx * self.S, ry * self.S, ramp, ang)


def polar(x, y, ang, r):
    return x + math.cos(ang) * r, y + math.sin(ang) * r


def dying(clip, n, first=2):
    return (clip == 'die' and n >= first) or (clip == 'hurt' and n == 1)


def shard(a, x, y, length, width, ang, ramp):
    """A kite-shaped shard centred near (x, y), pointing along ang."""
    nx, ny = -math.sin(ang), math.cos(ang)
    tip = polar(x, y, ang, length * .62)
    tail = polar(x, y, ang, -length * .38)
    sh = polar(x, y, ang, length * .12)
    plate(a, [tip, (sh[0] + nx * width / 2, sh[1] + ny * width / 2), tail, (sh[0] - nx * width / 2, sh[1] - ny * width / 2)], ramp, .7)


def finger(a, x, y, ang, length, width, bend, ramp, teeth=0, tooth=BONE):
    """A tapering pincer finger from (x, y) along ang, curving by `bend` radians over its length, inner teeth on the left."""
    pts_l, pts_r, mids = [], [], []
    for i in range(6):
        t = i / 5
        ang_t = ang + bend * t * t
        px, py = polar(x, y, ang + bend * t * .5, length * t)
        w = width * (1 - .86 * t) * .5 + .3
        nx, ny = -math.sin(ang_t), math.cos(ang_t)
        pts_l.append((px + nx * w, py + ny * w))
        pts_r.append((px - nx * w, py - ny * w))
        mids.append((px, py, nx, ny, w))
    plate(a, pts_l + pts_r[::-1], ramp, .7)
    for i in range(teeth):
        px, py, nx, ny, w = mids[1 + i * 4 // max(1, teeth) if teeth > 1 else 2]
        s = 1 if bend >= 0 else -1
        a.poly([(px + nx * w, py + ny * w), (px + nx * (w + 3.2), py + ny * (w + 3.2) + 1), (px + nx * w - math.cos(ang) * 3, py + ny * w - math.sin(ang) * 3)], tooth[2], outline=tooth[0])


def pincer(a, x, y, ang, length, width, open_, ramp, teeth=3, palm=1.):
    """A crab claw: a palm ball plus a fixed lower finger and a hinged upper finger opening by open_ radians."""
    a.ball(x, y, width * .62 * palm, width * .52 * palm, ramp, ang)
    bx, by = polar(x, y, ang, width * .3)
    finger(a, bx, by, ang - .10 - open_ * .35, length, width * .95, .22, ramp, teeth, SALT)
    finger(a, bx, by, ang + .10 + open_ * .65, length * .94, width * .85, -.26, ramp, teeth, SALT)


# KINDS-START

def salt_cluster(a, x, y, s, tilt=0.):
    """A fist of salt crystals growing out of the carapace."""
    for dx, h, t in ((-6, 15, -.5), (0, 22, 0.05), (6, 16, .55), (-2, 11, -.2), (3, 10, .3)):
        a.crystal(x + dx * s, y, 3.2 * s, h * s, SALT, tilt + t * 8)


def saltclaw(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('saltclaw', recoil * 1.4 + st * 22)
    fold = dn
    by = (23 + bob * .6 - st * 9) * (1 - .5 * fold)          # carapace centre height
    # legs: three jointed pairs on each side, they buckle inward and curl as it dies
    for side in (-1, 1):
        for i in range(3):
            swing = math.sin(ph + i * 2.1 + (0 if side > 0 else math.pi)) if clip == 'walk' else 0
            lift = max(0, swing) * 6
            hip = (side * (14 + i * 6), by - 3 - i * 1.5)
            knee = (side * (37 + i * 8 - fold * 12), by + 15 - i * 3 - fold * 12 + lift * .6)
            ft = (side * (45 + i * 10 + swing * 3 - fold * 26), 1.2 + lift - fold * (-1.6 + i * .4))
            if dn:
                ft = (ft[0] - side * fold * 4, 1.2 + fold * (i % 2))
            a.limb([hip, knee, ft], SHELL, 5)
            a.poly([(ft[0] - 1, ft[1] + 1.5), (ft[0] + side * 3, ft[1]), (ft[0] - 1, ft[1] - 1)], SALT[2])
    # claws: a small serrated cutter on the left, a huge salt-knuckled crusher on the right
    lift_l = bob * .5
    cut_t = (-50 - st * 16, by + 4 + lift_l + w * 10 + st * 2)
    cut_open = .45 + w * .5 - fold * .3
    crush_rest = (53, by + 6)
    crush_wind = (24, by + 56)
    crush_strike = (24, 3.5)
    ct = mixp(mixp(crush_rest, crush_wind, w), crush_strike, st)
    crush_open = .5 + w * .55 - st * .45
    if dn:
        ct = mixp(ct, (58, 4.5), fold)
        cut_t = mixp(cut_t, (-56, 4.), fold)
        crush_open = .1 + fold * .5
        cut_open = .2 + fold * .4
    for side, tgt, op, big in ((-1, cut_t, cut_open, .78), (1, ct, crush_open, 1.25)):
        sh = (side * 25, by + 2)
        el, hd = arm_ik(sh, tgt, 24, 22, bend=-side if tgt[1] > sh[1] else side)
        taper(a, [sh, el, hd], CRIMSON if big > 1 else SHELL, 8 * big, 6.5 * big)
        a.ball(el[0], el[1], 5.2 * big, 5.2 * big, CRIMSON if big > 1 else SHELL)
        ang = math.atan2(tgt[1] - el[1], tgt[0] - el[0])
        if side > 0 and dn:
            ang = -.5
        pincer(a, hd[0], hd[1], ang, 22 * big, 17 * big, op, CRIMSON if big > 1 else SHELL, 3, 1.05)
        if big > 1:
            for k in range(3):
                a.crystal(hd[0] - 3 + k * 4, hd[1] + 6, 1.9, 6 + (k % 2) * 3, SALT, k * 1.5 - 1.5)
    # carapace with a ridge of salt, side spines and a cracked brine skin
    a.ball(0, by, 33, 18 * (1 - .3 * fold), SHELL, .0)
    a.ball(0, by - 7, 28, 8, SHELL)
    for side in (-1, 1):
        for k in range(3):
            fang(a, side * (21 + k * 3.5), by + 4 - k * 4.5, 9 - k, 3.8, (.7 + k * .25) if side > 0 else math.pi - (.7 + k * .25), SALT)
    if dn < .35:
        salt_cluster(a, 0 - 2, by + 11 * (1 - .4 * fold), 1.0 - fold * .4, .0)
    else:
        for k, dx in enumerate((-12, -3, 7, 14)):
            a.crystal(dx, by + 5 - fold * 4, 3, 6 + (k % 2) * 3, SALT, dx * .1)
    for k, (x0, y0) in enumerate(((-14, by + 3), (9, by + 7), (19, by - 2))):
        a.ball(x0, y0, 2.8, 2.4, SALT)
    if dn > .55:
        u = (dn - .55) / .45
        a.poly([(-1 - u * 2, by + 14), (4 + u * 4, by + 12), (1 + u * 5, by + 1), (6 + u * 3, by - 7), (-2 - u * 4, by - 4), (-4 - u * 5, by + 5)], OUTLINE)
    cracks = max(0, (dn - .12) / .88)
    if cracks > 0:
        pts = [(-18, by + 8), (-8, by + 2), (-12, by - 4), (2, by - 7), (9, by - 1), (20, by + 5)]
        a.line(pts[:2 + int(cracks * 4.99)], OUTLINE, 2)
        a.line([(0, by + 9), (4, by + 2), (-1, by - 3)][:1 + int(cracks * 2.99)], OUTLINE, 2)
    # face: two stalked bulb eyes with a red bar pupil, and serrated side-opening mandibles
    for side in (-1, 1):
        base = (side * 8, by + 10)
        tipp = (side * 11 + side * st * 2, by + 25 - fold * 14 - w * 3 + (3 if side > 0 else 0) + bob * .4)
        if dn:
            tipp = (side * (15 + fold * 6), by + 12 - fold * 9)
        taper(a, [base, mixp(base, tipp, .5), tipp], SHELL, 7, 5)
        a.ball(tipp[0], tipp[1], 7, 7, SALT)
        if dying(clip, n):
            a.line([(tipp[0] - 3.5, tipp[1] + 2), (tipp[0] + 3.5, tipp[1] - 2)], OUTLINE, 2)
            a.line([(tipp[0] - 3.5, tipp[1] - 2), (tipp[0] + 3.5, tipp[1] + 2)], OUTLINE, 2)
        else:
            a.poly([(tipp[0] - 5, tipp[1] + 1.8), (tipp[0] + 5, tipp[1] + 1.8), (tipp[0] + 5, tipp[1] - 1.8), (tipp[0] - 5, tipp[1] - 1.8)], OUTLINE)
            a.poly([(tipp[0] - 3.2, tipp[1] + .8), (tipp[0] + 3.2, tipp[1] + .8), (tipp[0] + 3.2, tipp[1] - .8), (tipp[0] - 3.2, tipp[1] - .8)], CRIMSON[3] if (clip == 'attack' and 2 <= n <= 4) else CORAL[2])
            a.line([(tipp[0] - 5, tipp[1] + 5), (tipp[0] + 5, tipp[1] + 3.6)], SHELL[0], 2)
            for vx in (-5, 5):
                a.line([(tipp[0] + vx * .9, tipp[1] + 1.6), (tipp[0] + vx * .5, tipp[1] + 4)], CRIMSON[2], 1)
    gap = 3.5 + w * 3 + st * 6 + (2 if clip == 'hurt' and n == 1 else 0) + fold * 3
    a.ellipse(0, by - 7.5, 6 + gap * .5, 4.2, OUTLINE)
    for side in (-1, 1):
        jaw = [(side * 3, by - 5), (side * (4 + gap), by - 9), (side * (7 + gap), by - 14 + dn * 3), (side * (3.2 + gap), by - 11.5)]
        plate(a, jaw, SALT, .6)
        for k in range(3):
            a.poly([(side * (4 + gap + k * .9), by - 8.5 - k * 1.5), (side * (2.2 + gap * .7 + k * .5), by - 10.5 - k * 1.4), (side * (4 + gap + k * .9), by - 11 - k * 1.4)], OUTLINE)
    if clip == 'die' and n >= 4:
        for i in range(2 * (n - 3)):
            a.crystal(-30 + i * 5 + (i % 3) * 2, 2 + (i % 2) * 2, 1.4 + (i % 2) * .6, 4 + (i % 3) * 2, SALT, (i % 3 - 1) * 2)
    if st > .5:
        for i in range(7):
            q = (14 + i * 3 + st * 4, 3 + (i % 3) * 3.5)
            a.crystal(q[0], q[1], 1.1, 3.4, SALT, (i % 3 - 1) * 2)
    return a


def feather(a, x, y, ang, length, width, ramp, rag=0.):
    """A long pointed flight feather from (x, y) along ang, shaded; rag notches the trailing edge."""
    nx, ny = -math.sin(ang), math.cos(ang)
    pts_l, pts_r = [], []
    for i, (t, hw) in enumerate(((0, .5), (.3, 1.), (.62, .9), (.86, .5), (1., 0.))):
        px, py = polar(x, y, ang, length * t)
        pts_l.append((px + nx * width * hw * .5, py + ny * width * hw * .5))
        j = 1 + rag * (.45 if i % 2 else -.1)
        pts_r.append((px - nx * width * hw * .5 * j, py - ny * width * hw * .5 * j))
    plate(a, pts_l + pts_r[::-1][1:], ramp, .72)
    return polar(x, y, ang, length)


def bolt_along(a, p0, p1, n, amp=2.2, col=None, wid=1):
    """A lightning arc hugging the line p0->p1, zigzag seeded by n so each frame crackles differently."""
    col = BOLT[3] if col is None else col
    pts = [p0]
    for i in range(1, 6):
        t = i / 6
        j = ((i * 7 + n * 5) % 5 - 2) * amp * .5
        px, py = mixp(p0, p1, t)
        pts.append((px - (p1[1] - p0[1]) / max(1., math.hypot(p1[0] - p0[0], p1[1] - p0[1])) * j,
                    py + (p1[0] - p0[0]) / max(1., math.hypot(p1[0] - p0[0], p1[1] - p0[1])) * j))
    pts.append(p1)
    a.line(pts, BOLT[1], wid + 1)
    a.line(pts, col, wid)


def stormgull(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    fall = sm(dn * 1.15)
    DIE = clip == 'die'
    a = Painter('stormgull', recoil * 1.2 + st * 12 - w * 6 + dn * 6)
    hover = 64 + math.sin(ph) * (3.2 if clip != 'attack' else 1.2)
    cy = hover * (1 - fall * .93) + w * 8 - st * 4
    pitch = -.55 * st + .35 * w + (.1 if clip == 'hurt' else 0) * (n % 2)
    if DIE:
        cy = [64, 60, 50, 38, 25, 16, 11, 10][n]
        pitch = [0, -.3, -.7, -1.0, -1.1, -.8, -.3, -.12][n]
    cp, sp = math.cos(pitch), math.sin(pitch)

    def T(x, y):
        return x * cp - y * sp, cy + x * sp + y * cp

    flap = math.sin(ph * (1.6 if clip == 'walk' else 1.3)) if clip in ('idle', 'walk') else (1.2 if clip == 'attack' and n < 3 else -.2) * (1 if clip == 'attack' else 0)
    if clip == 'attack':
        flap = [.2, .6, 1.3, .9, -1.0, -.7, -.2, .1][n]
    if clip == 'hurt':
        flap = [-.6, 1.3, .2, -.4][n]
    wing_fold = 0 if not DIE else [0, 0, .1, .35, .6, .7, .85, .95][n]
    # far wing, darker, behind the body
    for wing, (rx, ry, shade, sgn) in enumerate(((-2, 4, 0, 1), (0, 5, 1, 1))):
        root = T(rx - 3 + wing * 4, ry)
        th0 = 2.0 - wing * .35 + flap * .72 + (-.5 * st) + pitch
        if DIE:
            th0 = (1.5 + wing * .1 if n < 3 else 1.9 + wing_fold * 1.2 - wing * .2) + pitch * (.5 if n < 5 else 0)
        if clip == 'attack' and st:
            th0 = 3.3 - wing * .3 + pitch * .2
        ramp = STORM if wing else [STORM[0], STORM[0], STORM[1], STORM[2], STORM[3]]
        arcs = []
        for i in range(8):
            ang = th0 + i * (.10 + wing_fold * .02) + (.1 if wing == 0 else 0)
            ln = (62 - i * 3.2) * (1 - .3 * wing_fold) * (1 if wing else .9)
            tip = feather(a, root[0], root[1], ang, ln, 14, ramp, rag=.6)
            if i in (0, 3, 6) and wing:
                arcs.append((polar(root[0], root[1], ang, ln * .35), tip))
        if wing and not dying(clip, n, 3):
            for k, (p0, p1) in enumerate(arcs):
                bolt_along(a, p0, p1, n + k * 2, 2.0, BOLT[4] if (clip == 'attack' and 3 <= n <= 5) else BOLT[3])
    # tail fan
    tb = T(-13, -1)
    for i in range(4):
        feather(a, tb[0], tb[1], math.pi + pitch + .25 - i * .17 + (dn * .5), 24 - i * 2, 7, STORM, rag=.4)
    # talons: tucked while hovering, thrust forward on the strike
    for k in (0, 1):
        hip = T(-1 + k * 6, -7)
        reach = (4 + k * 3 + st * 22 - w * 4, -17 + st * 5 + w * 5 + (dn * 5))
        kn = T(2 + k * 5 + reach[0] * .6, -13 + reach[1] * .3)
        ft = T(reach[0] + k * 4, reach[1])
        a.limb([hip, kn, ft], BONE, 3)
        for t in (-1, 0, 1):
            fang(a, ft[0], ft[1], 6 + st * 3, 2.6, (-1.2 + t * .5 + pitch) if not dying(clip, n, 3) else -.6 + t * .5, BONE)
    # body
    bp = T(0, 0)
    BODY = [STORM[0], STORM[1], STORM[1], STORM[2], STORM[3]]
    a.ball(bp[0], bp[1], 18, 11, BODY, pitch)
    bell = T(2, -5)
    a.ball(bell[0], bell[1], 12, 5, [STORM[1], STORM[2], STORM[3], STORM[3], STORM[4]], pitch)
    # neck and head with a dark mask, hooked serrated beak and a jagged-bolt eye
    nk = T(14, 5 + w * 2)
    hd = T(22 + st * 2 - w * 3, 8 + w * 4 - st * 3)
    taper(a, [nk, mixp(nk, hd, .5), hd], BODY, 12, 9)
    hang = pitch + .1
    a.ball(hd[0], hd[1], 9, 7.6, BODY, hang)
    a.ellipse(hd[0] + 1.5, hd[1] + 1.2, 8, 6.2, OUTLINE)
    ex, ey = hd[0] + 2.4, hd[1] + 1.6
    if dying(clip, n):
        a.line([(ex - 3, ey + 2), (ex + 3, ey - 2)], BOLT[0], 2)
        a.line([(ex - 3, ey - 2), (ex + 3, ey + 2)], BOLT[0], 2)
    else:
        bolt = [(ex - 5, ey + 5.4), (ex - .6, ey + 5.4), (ex - 2.7, ey + .6), (ex + 5.4, ey + .9), (ex + 1.2, ey - 5.7), (ex + 2.1, ey - 1.2), (ex - 5.4, ey - 1.2)]
        a.poly(bolt, BOLT[4] if not (clip == 'attack' and 2 <= n <= 5) else WHITE, outline=BOLT[1])
    # hooked beak, jaw gapes in the wind-up and on the strike
    gape = .1 + w * .45 + st * .5 + (.3 if clip == 'hurt' and n == 1 else 0) + dn * .35
    bx0, by0 = hd[0] + 6, hd[1] - 1.5
    cb, sb = math.cos(hang), math.sin(hang)

    def BK(x, y, g=0.):
        r = g + 0.
        c2, s2 = math.cos(hang + r), math.sin(hang + r)
        return bx0 + x * c2 - y * s2, by0 + x * s2 + y * c2

    up = [BK(-2, 4, gape * .4), BK(10, 3.2, gape * .5), BK(21, .4, gape * .5), BK(26, -6, gape * .5), BK(22.5, -2.6, gape * .5), BK(12, -2.2, gape * .4), BK(-2, -1.6, gape * .4)]
    lo = [BK(-2, -1.6, 0), BK(12, -2.2, -gape * .6), BK(20, -4.6, -gape), BK(11, -5.6, -gape * .7), BK(-2, -4.8, 0)]
    plate(a, lo, RUST, .6)
    plate(a, up, RUST, .6)
    for k in range(4):
        a.poly([BK(7 + k * 3.4, -2.3, gape * .4), BK(8.6 + k * 3.4, -5.2 - gape * 3, 0), BK(10 + k * 3.4, -2.3, gape * .4)], OUTLINE)
    return a


def glassray(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    DIE = clip == 'die'
    a = Painter('glassray', recoil * 1.5)
    hov = 72 + (math.sin(ph) * 3 if clip in ('idle', 'walk') else 0) + w * 6 - st * 5
    if DIE:
        hov = [72, 68, 60, 48, 33, 18, 9, 6][n]
    flap = math.sin(ph * 1.2) * .8 if clip in ('idle', 'walk') else 0
    if clip == 'attack':
        flap = [0, .5, 1, .5, -1.0, -.8, -.2, .12][n]
    if clip == 'hurt':
        flap = [-.5, 1., .2, -.3][n]
    if DIE:
        flap = [0, .4, .8, .3, -.4, -.3, -.2, -.1][n]
    shat = 0 if not DIE else [0, 0, .1, .3, .5, .7, .9, 1][n]
    # tail: a whip of glass ending in a barbed stinger
    base = (0, hov - 15)
    rest, wind, strike = (7, hov - 36), (-18, hov + 36), (3, hov - 34)
    tip_t = mixp(mixp(rest, wind, w), strike, st)
    if clip == 'idle' or clip == 'walk':
        tip_t = (tip_t[0] + math.sin(ph) * 5, tip_t[1])
    c1 = mixp((12, hov - 28), (-26, hov + 6), w)
    c1 = mixp(c1, (30, hov + 18), st)
    if DIE:
        tip_t = mixp(tip_t, (18, 3), sm(dn * 1.4))
        c1 = mixp(c1, (-6, 14), sm(dn))
    if shat < .8:
        tail = bez(base, c1, tip_t, 8)
        taper(a, tail, SEAGLASS, 7, 3.5)
        ta = math.atan2(tail[-1][1] - tail[-2][1], tail[-1][0] - tail[-2][0])
        shard(a, tail[-1][0], tail[-1][1], 15, 8, ta, SEAGLASS)
        shard(a, tail[-2][0] - 2, tail[-2][1] + 1, 10, 6, ta + .9, SEAGLASS)
        shard(a, tail[-2][0] + 2, tail[-2][1] + 1, 10, 6, ta - .9, SEAGLASS)
    # wings: three glass panes per side that crack apart and fall when it dies
    sp_ = 1 + .3 * st
    for side in (-1, 1):
        ty = hov + 4 + flap * 18
        Tp = [(side * 11, hov + 8), (side * 28 * sp_, hov + 11 + flap * 9), (side * 45 * sp_, hov + 8 + flap * 14), (side * 59 * sp_, ty)]
        Bp = [(side * 11, hov - 9), (side * 28 * sp_, hov - 7 + flap * 8), (side * 43 * sp_, hov - 8 + flap * 12)]
        panels = [[Tp[0], Tp[1], Bp[1], Bp[0]], [Tp[1], Tp[2], Bp[2], Bp[1]], [Tp[2], Tp[3], Bp[2]]]
        for i, pn in enumerate(panels):
            off = (0, 0)
            if shat:
                u = sm(shat)
                off = (side * u * (6 + i * 7), -u * (hov - 3) * (.75 + i * .12) * (1 if shat > .25 else shat * 3))
                if shat > .85:
                    off = (side * (8 + i * 11), -hov + 3 - i * 1.5)
            pts = [(x + off[0], y + off[1]) for x, y in pn]
            plate(a, pts, SEAGLASS, .74 - i * .06)
            a.line([pts[0], pts[1]] if i == 0 else [pts[0], pts[1]], SEAGLASS[4], 1)
            if i == 1 and shat < .2:
                a.line([(pts[0][0], pts[0][1] - 3), (pts[1][0] - side * 6, pts[1][1] - 2)], SEAGLASS[0], 1)
        if clip == 'attack' and 3 <= n <= 5:
            a.line([Tp[1], Tp[2], Tp[3]], WHITE, 1)
    # head: a wedge of glass with swept horns, a row of cold ocelli and a toothed maw
    hx, hy = 0, hov + (0 if not shat else -shat * 4)
    if shat < .98:
        for side in (-1, 1):
            plate(a, [(side * 8, hy + 12), (side * 22, hy + 30 + w * 5), (side * 20, hy + 8), (side * 14, hy + 2)], SEAGLASS, .66)
        plate(a, [(0, hy + 19), (18, hy + 8), (11, hy - 10), (0, hy - 24), (-11, hy - 10), (-18, hy + 8)], SEAGLASS, .8)
        a.line([(0, hy + 18), (0, hy - 6)], SEAGLASS[4], 1)
        dead = dying(clip, n)
        for side in (-1, 1):
            # an angular slit under a heavy brow shard, slanting down towards the nose, plus a pin ocellus beside it
            sx = lambda x: side * x
            a.poly([(sx(2.5), hy + 5), (sx(16), hy + 10.5), (sx(16.5), hy + 7), (sx(14), hy + 1), (sx(5), hy - 1.5)], OUTLINE)
            if not dead:
                hot = BOLT[4] if (clip == 'attack' and 2 <= n <= 5) else SEAGLASS[4]
                a.poly([(sx(4.8), hy + 3.4), (sx(13.5), hy + 6.8), (sx(13), hy + 3.6), (sx(7), hy + .4)], hot)
                a.ellipse(sx(10), hy + 11.5, 1.4, 1.4, hot)
            else:
                a.line([(sx(5), hy + 4), (sx(14), hy + 6)], SEAGLASS[1], 2)
        jaw = 2.5 + w * 3 + st * 6 + dn * 5
        a.poly([(-11, hy - 8), (11, hy - 8), (7, hy - 13 - jaw), (0, hy - 16 - jaw), (-7, hy - 13 - jaw)], OUTLINE)
        for k in range(-3, 4):
            ln = 5.4 - abs(k) * .6
            a.poly([(k * 2.9 - 1.5, hy - 8.4), (k * 2.9, hy - 8.4 - ln - jaw * .4), (k * 2.9 + 1.5, hy - 8.4)], SEAGLASS[4], outline=SEAGLASS[0])
        if dn > .1:
            a.line([(-4, hy + 17), (2, hy + 7), (-3, hy - 1), (4, hy - 14)][:1 + int(dn * 4)], OUTLINE, 2)
    else:
        for i in range(7):
            shard(a, -20 + i * 7, 4 + (i % 2) * 2, 11, 8, 1 + i * .9, SEAGLASS)
    if shat > .5:
        for i in range(5):
            shard(a, -30 + i * 14, 3 + (i % 3), 10, 7, i * 1.7, SEAGLASS)
    return a


def barnacles(a, x, y, spread, count, sc=1.):
    """A crust of barnacles: small pale cones in a cluster."""
    for i in range(count):
        ox = ((i * 5) % 7 - 3) * spread / 3
        oy = ((i * 3) % 5 - 2) * spread / 4
        r = (2.6 + (i % 3) * .7) * sc
        a.ball(x + ox, y + oy, r, r * .9, BARNACLE)
        a.ellipse(x + ox, y + oy + r * .2, r * .3, r * .2, BARNACLE[0])


def anchor(a, hand, ang, length=72):
    """A rusted ship's anchor held at the ring end, flukes at the far end."""
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    butt = (hand[0] - ux * length * .22, hand[1] - uy * length * .22)
    tip = (hand[0] + ux * length * .78, hand[1] + uy * length * .78)
    a.line([butt, tip], RUST[0], 11)
    a.line([butt, tip], RUST[2], 7)
    a.line([(butt[0] - nx, butt[1] - ny), (tip[0] - nx, tip[1] - ny)], RUST[3], 1)
    st_ = (tip[0] - ux * 12, tip[1] - uy * 12)
    a.line([(st_[0] - nx * 14, st_[1] - ny * 14), (st_[0] + nx * 14, st_[1] + ny * 14)], RUST[0], 9)
    a.line([(st_[0] - nx * 14, st_[1] - ny * 14), (st_[0] + nx * 14, st_[1] + ny * 14)], RUST[3], 6)
    for sg in (-1, 1):
        pts = [tip, (tip[0] + nx * sg * 13 - ux * 3, tip[1] + ny * sg * 13 - uy * 3), (tip[0] + nx * sg * 24 - ux * 15, tip[1] + ny * sg * 24 - uy * 15),
               (tip[0] + nx * sg * 11 - ux * 15, tip[1] + ny * sg * 11 - uy * 15), (tip[0] + nx * sg * 5 - ux * 5, tip[1] + ny * sg * 5 - uy * 5)]
        plate(a, pts + [(tip[0] + ux * 6, tip[1] + uy * 6)], RUST, .66)
    a.ellipse(butt[0] - ux * 2, butt[1] - uy * 2, 5.2, 5.2, RUST[2])
    a.ellipse(butt[0] - ux * 2, butt[1] - uy * 2, 2.6, 2.6, OUTLINE)
    return tip


def breakersentinel(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    DIE = clip == 'die'
    a = Painter('breakersentinel', recoil * 1.2 + st * 24)
    fold = sm(dn * 1.5) if not DIE else [0, .12, .3, .55, .8, 1., 1., 1.][n]
    dead = dying(clip, n)
    hs = 1 - .5 * fold - .13 * st
    gy = lambda y: y * hs
    rubble = DIE and n >= 5
    # legs: stone pillars with slab feet, they buckle as it dies
    for k, hx in enumerate((-14, 14)):
        swing = math.sin(ph + k * math.pi) if clip == 'walk' else 0
        lift = max(0, swing) * 5
        top = 32 * hs
        if not rubble:
            sh = hx + swing * 4 * (1 - fold)
            plate(a, [(sh - 9, lift + 6), (sh + 9, lift + 6), (hx + 8, top), (hx - 8, top)], STONE, .7)
            plate(a, [(sh - 12, lift), (sh + 12, lift), (sh + 11, lift + 7), (sh - 11, lift + 7)], STONE, .7)
            barnacles(a, sh + (3 if k else -3), lift + 15 * hs, 8, 3, .8)
    # torso and hip girdle of mortared stone, barnacle crust and a chain of kelp
    if not rubble:
        torso = [(-27, gy(32) + bob * .5), (27, gy(32) + bob * .5), (35, gy(68) + bob * .5), (-35, gy(68) + bob * .5)]
        plate(a, torso, STONE, .78)
        for k in range(3):
            yy = gy(40 + k * 9)
            a.line([(-24 - k * 2, yy), (26 + k * 2, yy + 1)], STONE[0], 1)
        a.line([(-6, gy(34)), (-7, gy(64))], STONE[0], 1)
        barnacles(a, -17, gy(52), 12, 5, 1)
        barnacles(a, 20, gy(44), 10, 4, .9)
        for kx in (-26, -10, 14):
            taper(a, [(kx, gy(62)), (kx - 1, gy(50) - fold * 3), (kx + 1 + math.sin(ph + kx) * 1.5, gy(37))], GREEN, 4, 2)
        if clip == 'hurt' and n == 1:
            a.line([(-12, gy(60)), (-2, gy(50)), (-10, gy(42))], OUTLINE, 2)
    # arms: the left slab fist braces, the right hauls the anchor
    big = (anchor if not rubble else None)
    if not rubble:
        sh_l, sh_r = (-37, gy(62)), (37, gy(62))
        tl = mixp((-46, gy(30)), (-40, gy(46)), st * .6 + w * .2)
        el, hd = arm_ik(sh_l, tl, 20, 20, bend=1)
        taper(a, [sh_l, el, hd], STONE, 12, 10)
        a.ball(hd[0], hd[1], 8, 7.5, STONE)
        barnacles(a, hd[0], hd[1] + 3, 5, 2, .7)
        aim_rest = 1.62
        grip_rest, grip_wind, grip_strike = (49, gy(40)), (44, gy(86)), (26, gy(30))
        grip = mixp(mixp(grip_rest, grip_wind, w), grip_strike, st)
        th = mix(mix(aim_rest, 2.2, w), -1.15, st)
        if DIE:
            grip = mixp(grip_rest, (62, 7), fold)
            th = mix(aim_rest, .12, fold)
        er, hr = arm_ik(sh_r, grip, 21, 22, bend=-1)
        anchor(a, hr, th)
        taper(a, [sh_r, er, hr], STONE, 13, 11)
        a.ball(hr[0], hr[1], 8.5, 8, STONE)
    # pauldrons crowned with barnacles
    if not rubble:
        for sx in (-37, 37):
            a.ball(sx, gy(66), 13, 10, STONE)
            barnacles(a, sx, gy(72), 9, 4, .9)
    # head: a stone helm with a heavy brow and a single horizontal lantern slit; no round eyes
    hyb = gy(68) - fold * 6 + bob * .4
    if rubble:
        hyb = 11 - (n - 5) * 1.6
    hx0 = 0 if not rubble else -10 - (n - 5) * 3
    hdw = 16
    plate(a, [(hx0 - hdw, hyb), (hx0 + hdw, hyb), (hx0 + hdw + 2, hyb + 21), (hx0 - hdw - 2, hyb + 21)], STONE, .74)
    plate(a, [(hx0 - hdw - 4, hyb + 20), (hx0 + hdw + 4, hyb + 20), (hx0 + hdw - 2, hyb + 28), (hx0 - hdw + 2, hyb + 28)], STONE, .66)
    for k, bxx in enumerate((-12, -4, 4, 12)):
        fang(a, hx0 + bxx, hyb + 26, 8 + (k % 2) * 3, 4.6, 1.57 + (bxx * .03), BARNACLE)
    slit_y = hyb + 12
    a.poly([(hx0 - 13, slit_y + 1.5), (hx0 + 13, slit_y + 1.5), (hx0 + 11, slit_y - 4), (hx0 - 11, slit_y - 4)], OUTLINE)
    for sg in (-1, 1):
        a.poly([(hx0 + sg * 15, slit_y + 7), (hx0 + sg * 2, slit_y + 2.5), (hx0 + sg * 15, slit_y + 3)], STONE[0])
    if not dead:
        glow = WHITE if (clip == 'attack' and 2 <= n <= 5) else GOLD[4]
        a.poly([(hx0 - 11.5, slit_y + .4), (hx0 + 11.5, slit_y + .4), (hx0 + 9.5, slit_y - 2.8), (hx0 - 9.5, slit_y - 2.8)], glow)
        for bxx in (-6, 0, 6):
            a.line([(hx0 + bxx, slit_y + .6), (hx0 + bxx, slit_y - 3)], OUTLINE, 1)
    a.line([(hx0 - 7, hyb + 4), (hx0 + 7, hyb + 4)], STONE[0], 1)
    for bxx in (-6, -2, 2, 6):
        a.line([(hx0 + bxx, hyb + 1.5), (hx0 + bxx, hyb + 4)], STONE[0], 1)
    if clip == 'die' and n >= 3:
        a.line([(hx0 - 6, hyb + 25), (hx0 - 1, hyb + 15), (hx0 - 5, hyb + 6)], OUTLINE, 2)
    # rubble heap: stone blocks and popped barnacles, the anchor lying across it
    if rubble:
        sp = 1 + (n - 5) * .09
        for i, (bx, by_, rx, ry) in enumerate(((-24, 5, 12, 7), (-2, 4, 16, 8), (20, 5, 13, 7), (34, 3, 8, 5), (-34, 3, 8, 5), (8, 11, 11, 7), (-14, 12, 9, 6))):
            a.ball(bx * sp, by_ - (n - 5) * .6 * (i % 2), rx, ry - (n - 5) * .5 * (i % 2), STONE, i * .4)
        for i in range(n - 4):
            a.ball(-40 + i * 17, 2, 2.6, 2, BARNACLE)
        barnacles(a, 14, 16, 18, 5, 1)
        grip = (60, 6)
        anchor(a, (30, 12 - (n - 5)), .1 - (n - 5) * .06)
    return a


def vortex_ring(a, cx, cy, R, ry, tilt, spin, half, thorn, n, wid=6, flat=0.):
    """One tilted ring of storm water with thorns of glass growing out of it. half=0: far side (drawn behind), 1: near side."""
    pts = []
    for i in range(0, 25):
        t = (0 if half == 0 else math.pi) + i * math.pi / 24
        x, y = R * math.cos(t), ry * math.sin(t)
        c, s = math.cos(tilt), math.sin(tilt)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    a.line(pts, TIDE[0], wid + 2)
    a.line(pts, TIDE[2] if half else TIDE[1], wid)
    a.line([(x, y + 1) for x, y in pts], TIDE[3] if half else TIDE[2], max(1, wid // 3))
    if thorn > 0:
        for k in range(7):
            t = spin + k * 2 * math.pi / 7
            if (math.sin(t) >= 0) != (half == 0):
                continue
            x, y = R * math.cos(t), ry * math.sin(t)
            c, s = math.cos(tilt), math.sin(tilt)
            px, py = cx + x * c - y * s, cy + x * s + y * c
            out = math.atan2(py - cy, px - cx)
            shard(a, px + math.cos(out) * thorn * .3, py + math.sin(out) * thorn * .3, thorn, 8, out, SEAGLASS)


def maelstromheart(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    DIE = clip == 'die'
    a = Painter('maelstromheart', recoil * 1.5)
    hov = 69 + (math.sin(ph) * 3 if clip in ('idle', 'walk') else 0)
    if DIE:
        hov = [69, 66, 58, 46, 33, 21, 15, 13][n]
    beat = (1 + .05 * math.sin(ph * 2) * (1 - dn)) + .09 * w + .06 * st
    spin = ph * (1.0 if clip != 'attack' else 2.4) + n * (.5 if clip == 'attack' else 0)
    ring1 = 52 - w * 17 + st * 12 - (dn * 8 if DIE else 0)
    thorn = 15 + w * 3 + st * 12
    flatten = sm(dn * 1.2) if DIE else 0
    openness = .12 + w * .55 + st * .95 - (dn * .3)
    if clip == 'hurt':
        openness = [.9, .5, .25, .15][n]
    if DIE:
        openness = [.15, .6, .35, .12, 0, 0, 0, 0][n]
    dark = DIE and n >= 3
    FL = [HEART[0], HEART[0], HEART[1], HEART[1], HEART[2]] if dark else HEART
    cx = 0
    rings = ((ring1, 14 - flatten * 8, .16, spin), (ring1 * .78, 12 - flatten * 7, -.55, -spin * 1.3))
    # far halves of the rings
    if not (DIE and n >= 6):
        for R, ry, tilt, sp in rings:
            vortex_ring(a, cx, hov - flatten * 6, R, ry, tilt * (1 - flatten), sp, 0, thorn if not DIE else thorn * (1 - flatten), n)
    # the heart: two lobes, a ventricle ending in a point, and torn vessels on top
    hy = hov - flatten * 4
    ventr = [(-21 * beat, hy - 6), (21 * beat, hy - 6), (11, hy - 26 * beat), (0, hy - 38 * beat), (-11, hy - 26 * beat)]
    for sg in (-1, 1):
        taper(a, [(sg * 6, hy + 20), (sg * 10 + sg * st * 3, hy + 33), (sg * 7 + sg * 4, hy + 45 + math.sin(ph + sg) * 1.5)], FL, 8, 6)
        a.ellipse(sg * 7 + sg * 4, hy + 45 + math.sin(ph + sg) * 1.5, 3.6, 2.2, OUTLINE)
    plate(a, ventr, FL, .8)
    a.ball(0, hy + 1, 25 * beat, 22 * beat, FL, .1)
    a.ball(-14 * beat, hy + 15 * beat, 14 * beat, 12 * beat, FL)
    a.ball(14 * beat, hy + 16 * beat, 14 * beat, 12 * beat, FL)
    for k, (vx0, vy0, vx1, vy1) in enumerate(((-20, hy + 14, -9, hy + 3), (18, hy + 10, 9, hy - 6), (-6, hy - 12, -2, hy - 26), (11, hy - 10, 6, hy - 20))):
        a.line([(vx0, vy0), (vx1, vy1)], HEART[0] if not dark else HEART[0], 2)
    # the sealed eye: lids stitched shut, the stitches snap as it wakes
    ew, eh = 17, 2 + openness * 11
    ey = hy + 1
    a.ellipse(0, ey, ew + 2.5, eh + 3, OUTLINE)
    if openness > .02:
        a.ellipse(0, ey, ew, eh, BONE[4])
        iris = TIDE[3] if not (clip == 'attack' and 2 <= n <= 5) else TIDE[4]
        ir = min(eh, 7.5)
        a.ellipse(0, ey, ir, eh, iris)
        a.ellipse(0, ey, 2.4 + (0 if openness > .5 else 0), max(1., eh - .5), OUTLINE)
        for vx in (-16, -15, 15, 16):
            a.line([(vx, ey + (vx % 3) - 1), (vx * .55, ey + (vx % 2) * 1.2)], CRIMSON[1], 1)
    else:
        a.line([(-ew, ey), (ew, ey)], OUTLINE, 3)
    # lids: heavy flesh folds above and below, stitches across while sealed
    a.ellipse(0, ey + eh + 2.4, ew + 3.5, 2.8, FL[2])
    a.ellipse(0, ey - eh - 2.4, ew + 3.5, 2.8, FL[1])
    if openness < .55 and not DIE:
        for k, sx in enumerate((-12, -6, 0, 6, 12)):
            a.line([(sx - 1.5, ey + 4.5 + eh * .3), (sx + 1.5, ey - 4.5 - eh * .3)], BONE[2], 1)
    if DIE and n >= 4:
        a.line([(-ew, ey), (ew, ey)], OUTLINE, 3)
    # near halves of the rings, and a storm arc bridging them on the strike
    for R, ry, tilt, sp in rings:
        vortex_ring(a, cx, hov - flatten * 6, R, ry, tilt * (1 - flatten), sp, 1, thorn if not DIE else thorn * (1 - flatten), n)
    if clip == 'attack' and 3 <= n <= 5:
        for k in range(3):
            ang_ = spin + k * 2.1
            p0 = (ring1 * .62 * math.cos(ang_), hov + ring1 * .12 * math.sin(ang_) + 4)
            p1 = (ring1 * .98 * math.cos(ang_), hov + ring1 * .16 * math.sin(ang_) + 4)
            bolt_along(a, p0, p1, n + k, 3, BOLT[4])
    if DIE and n >= 5:
        for i, r in enumerate((20, 31, 43)):
            r = r + (n - 5) * 5
            pts = [(r * math.cos(t * math.pi / 12), 3 + r * .13 * math.sin(t * math.pi / 12)) for t in range(25)]
            a.line(pts, TIDE[2 if i < 2 else 1], 2)
    return a


DRAW = {k: globals()[k] for k in KINDS if k in globals()}
STRICT = True
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if kind in FLYING:
        # Flyers hover well above the ground while alive and settle onto kay at the end of death.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and clip == 'die' and (n == 7 or int(rows.max()) > kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    else:
        # Grounded kinds rest their lowest pixel exactly on the anchor row in every living and death frame.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and (clip == 'die' or int(rows.max()) != kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    problem = None
    low = int(np.nonzero(grid.any(axis=1))[0].max()) if grid.any() else -1
    if not grid.any() or grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any():
        problem = 'empty or touches the border'
    elif kind in FLYING:
        if clip != 'die' and low > kay - 12:
            problem = f'flying kind should hover well above anchor row {kay} (lowest row {low})'
        elif clip == 'die' and low > kay:
            problem = f'flying death frame {n} sinks below anchor row {kay} (lowest row {low})'
    elif low != kay:
        problem = f'lowest row {low} != anchor row {kay}'
    if problem:
        BAD.append((kind, clip, n, problem))
        assert not STRICT, (kind, clip, n, problem)
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def api_draw(sid, offset, data):
    for clip, grids in data.items():
        for n, grid in enumerate(grids):
            old.api('draw', dict(sprite_id=sid, frame=offset + n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
        offset += len(grids)
    return offset


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = registry()
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX + kind + '_all' + os.environ.get('SOURCE_SUFFIX', '')  # a frame-size change needs a NEW source
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/stormglass_slime_{kind}_raw.npz', **data[kind])
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(
            name=name, width=kw, height=kh, frames=34, layers=1, fps=10,
            palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]
        ))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, api_draw(sid, 0, data[kind]), 'frames saved', flush=True)


def refresh():
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/stormglass_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'stormglass_{kind}.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    metas = {MANIFEST: dict(frame=[W, H], anchor=[AX, AY], kinds=list(KINDS), clips={}, sprites={k: saved[k] for k in KINDS}, tops={}, artStyle='greenmeadow-slime')}
    proof, atlases = {}, {}
    for kind in KINDS:
        meta = metas[MANIFEST]
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for kind, atlas in atlases.items():
        dest = atlas_path(kind)
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    for path, meta in metas.items():
        path.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 170 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    saved = registry()
    for kind in KINDS:
        meta = json.loads(MANIFEST.read_text())
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(atlas_path(kind)).convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    """Measure each kind's art on a scratch canvas: pass A (anchor x 100) gives the left reach, pass B (anchor x 36) the right."""
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW and (len(sys.argv) < 3 or k in sys.argv[2:])]:
        old_kf = KIND_FRAMES.get(kind)
        left = right = up = 0
        for axs in (100, 36):
            KIND_FRAMES[kind] = (192, 192, axs, 186)
            for clip, grids in frames(kind).items():
                for grid in grids:
                    ys, xs = np.nonzero(grid)
                    if not xs.size:
                        continue
                    assert (xs.min() > 0 if axs == 100 else xs.max() < 191) and ys.min() > 0, (kind, clip, 'scratch canvas clipped', axs)
                    if axs == 100:
                        left = max(left, axs - 2 - int(xs.min()) + 2)
                        up = max(up, 184 - int(ys.min()))
                    else:
                        right = max(right, int(xs.max()) - (axs - 2) + 2)
        print(f'{kind}: left {left} right {right} up {up}  ->  suggested ax {left+4}, w {left+4+right+5}, ay {up+4}, h {up+4+6}')
        if old_kf:
            KIND_FRAMES[kind] = old_kf
        else:
            del KIND_FRAMES[kind]


def preview():
    global STRICT
    STRICT = False
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or [k for k in KINDS if k in DRAW]
    for kind in only:
        kw, kh, _, kay = kind_frame(kind)
        data = frames(kind)
        sheet = Image.new('RGB', (8 * kw * 2, 5 * (kh * 2 + 26)), '#221f33')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((kw * 2, kh * 2), Image.Resampling.NEAREST)
                sheet.paste(im, (n * kw * 2, row * (kh * 2 + 26)), im)
                sd.text((n * kw * 2 + 8, row * (kh * 2 + 26) + kh * 2 + 4), f'{clip} {n}', fill='white')
                gy = row * (kh * 2 + 26) + kay * 2 + 2
                sd.line([(n * kw * 2, gy), (n * kw * 2 + kw * 2, gy)], fill='#5c5284')
        sheet.save(OUT / f'preview-{kind}.png')
        print(OUT / f'preview-{kind}.png')
    print('Frame problems:', BAD or 'none')


def montage():
    """A compact review sheet in the scratchpad: idle, walk, hurt, 8 attack and 8 death frames at 1.5x, cropped to the art."""
    global STRICT
    STRICT = False
    dest = Path(os.environ.get('MONTAGE_DIR', OUT))
    dest.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or [k for k in KINDS if k in DRAW]
    for kind in only:
        data = frames(kind)
        picks = [('idle', 0), ('idle', 3), ('walk', 2), ('hurt', 1)] + [('attack', i) for i in range(8)] + [('die', i) for i in range(8)]
        ims = [rgba(data[c][i]) for c, i in picks]
        box = None
        for im in ims:
            b = im.getbbox()
            if b:
                box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
        pad = 3
        box = (max(0, box[0] - pad), max(0, box[1] - pad), box[2] + pad, box[3] + pad)
        cw, ch = box[2] - box[0], box[3] - box[1]
        sc = float(os.environ.get('MONTAGE_SCALE', 1.5))
        cols = 5
        rows_n = (len(picks) + cols - 1) // cols
        sheet = Image.new('RGB', (int(cols * cw * sc), int(rows_n * (ch * sc + 14))), '#221f33')
        sd = ImageDraw.Draw(sheet)
        for k, ((c, i), im) in enumerate(zip(picks, ims)):
            x, y = int((k % cols) * cw * sc), int((k // cols) * (ch * sc + 14))
            tile = im.crop(box).resize((int(cw * sc), int(ch * sc)), Image.Resampling.NEAREST)
            sheet.paste(tile, (x, y), tile)
            sd.text((x + 3, y + int(ch * sc) + 1), f'{c} {i}', fill='white')
        sheet.save(dest / f'montage-{kind}.png')
        print(dest / f'montage-{kind}.png', sheet.size)
    print('Frame problems:', BAD or 'none')


if __name__ == '__main__':
    {'preview': preview, 'montage': montage, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
