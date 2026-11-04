#!/usr/bin/env python3
"""Astralhollow (zone 13) slime-style native PixelFlow sources.

preview | extents | build | refresh | export | verify.
Greenmeadow glossy shading, big eyes with highlights (#fffbea) and blush, material-appropriate movement,
per-kind frame sizes (KIND_FRAMES, docs/kind-frames.md), grounded feet/bases on the anchor row in every living
and death frame (QUADRUPED-GROUNDING; flying Void Moth hovers well above the ground and falls onto the anchor
row on death), eight distinct attack frames (wind-up, strike, recovery) and eight distinct fitting death frames
per kind:
  - voidmoth: flying indigo-and-lavender moth with four scalloped star-eye wings (golden ocelli with dark
    pupils), fluffy lilac chest ruff, segmented violet abdomen and star-tipped golden antennae; banks back and
    throws its four wings high overhead with a charging starlight orb, then swoops far forward blasting a
    volley of star-motes; on death falls from mid-air onto the ground as its wings fold inward and stardust
    settles.
  - crystalwyrm: four-legged azure starglass wyrm with pale ice-blue belly scutes, dorsal amethyst crystal
    ridge, swept-back amethyst horns and four clawed feet planted on the ground row; coils back and rears its
    head and crystal crest high with jaws parted, then lunges far forward snapping its jaws and firing a stream
    of prismatic crystal shards; on death its four legs buckle and fold, its serpentine neck uncoils flat onto
    the ground and dorsal crystals fracture and scatter.
  - orbitbeetle: bronze-and-amber celestial scarab on four planted jointed leg pairs with a curved golden
    rhinoceros horn, violet under-wings beneath rigid wing-cases and a luminous golden moon orbiting overhead;
    rears back lifting its bronze wing-cases and horn high as its moon blazes overhead, then drives forward
    hurling a constellation burst; on death its shell cracks, it rolls onto its back with curled legs, and the
    orbiting moon tumbles to rest beside it on the ground.
  - eclipsedryad: sylvan dryad of emerald leaf-layers and warm bark with a black-sun eclipse halo and blazing
    golden corona behind her head, branch-antlers, rose chest-bloom and two bark root-feet; raises her branch
    arm and flaring eclipse corona high overhead, then sweeps far forward casting a volley of razor star-leaves;
    on death her eclipse halo shatters into falling embers, her bark knees buckle, leaves drift down and she
    sinks into a mound of roots and wilted foliage.
  - meteorgolem: towering meteoric violet-slate colossus with glowing molten fissures, a faceted amethyst chest
    core, jagged amethyst shoulder crystals, orbiting asteroid chips and two heavy stone feet; heaves both
    meteor fists high overhead then slams them far forward with erupting amethyst shards and shockwave sparks;
    on death its molten fissures and core go dark, orbiting chips drop, knees buckle and its separated boulder
    head, shoulders and fists slump into a rubble heap on the ground.
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
from reliquary_slime_redraw import (
    PALETTE as RELIQUARY_PALETTE, OUTLINE, WHITE, EYE_WHITE, BLUSH,
    BONE, PLATE, PURPLE, TEAL, GOLD, GREEN, FUR, BLUE, BROWN, OLIVE,
    PINK, MAROON, CORAL, PEARL, VIOLET, CRIMSON, AMBER,
    mix, mixp, rot, sm, bez, taper, foot, spark, motion, atk,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/astral-slime'
REGISTRY = ROOT / 'scripts/astral_slime_sources.txt'
MANIFEST = ASSETS / 'astral.txt'
PREFIX = 'valhallasc_astral_slime_style_'
KINDS = ['voidmoth', 'crystalwyrm', 'orbitbeetle', 'eclipsedryad', 'meteorgolem']
NAMES = dict(
    voidmoth='Void Moth',
    crystalwyrm='Crystalwyrm',
    orbitbeetle='Orbit Beetle',
    eclipsedryad='Eclipse Dryad',
    meteorgolem='Meteor Golem',
)
W = H = 96
AX, AY = 48, 90
KIND_FRAMES = dict(
    voidmoth=(132, 98, 54, 92),
    crystalwyrm=(148, 100, 60, 94),
    orbitbeetle=(140, 100, 54, 94),
    eclipsedryad=(132, 114, 52, 108),
    meteorgolem=(136, 112, 56, 106),
)
# Preserve Astralhollow's existing 10 fps clip timings across all five rows.
CLIPS = {
    'idle': (10, 6),
    'walk': (10, 8),
    'attack': (10, 8),
    'hurt': (10, 4),
    'die': (10, 8),
}

PALETTE = RELIQUARY_PALETTE[:] + [
    '#0e355c', '#1d6fa3', '#49b8de', '#96e5fa', '#e3fbff',   # 130-134 AZURE (starglass wyrm scales)
    '#183b26', '#2d6e3e', '#58b04f', '#98de68', '#daf8ab',   # 135-139 LEAF (dryad emerald foliage)
    '#201b34', '#3b335c', '#60558c', '#8e82c2', '#c6bcf0',   # 140-144 SLATE (meteoric violet-slate rock)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
AZURE = list(range(130, 135))
LEAF = list(range(135, 140))
SLATE = list(range(140, 145))


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


class Painter:
    """Round glossy shaded components on a kind-sized canvas; y is up from the ground row, x from the centre."""
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax - 2 + dx

    def pos(self, x, y):
        return round(self.cx + x), round(self.ay - y)

    def ellipse(self, x, y, rx, ry, col):
        px, py = self.pos(x, y)
        self.d.ellipse((round(px - rx), round(py - ry), round(px + rx), round(py + ry)), fill=col)

    def line(self, pts, col, width=1):
        self.d.line([self.pos(*p) for p in pts], fill=col, width=width)

    def poly(self, pts, col, outline=None):
        self.d.polygon([self.pos(*p) for p in pts], fill=col, outline=outline)

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        px, py = self.pos(x, y)
        R = max(rx, ry)
        c, s = math.cos(ang), math.sin(ang)
        for yy in range(max(0, math.floor(py - R)), min(self.h, math.ceil(py + R) + 1)):
            for xx in range(max(0, math.floor(px - R)), min(self.w, math.ceil(px + R) + 1)):
                dx, dy = xx - px, yy - py
                u, v = (dx * c - dy * s) / rx, (dx * s + dy * c) / ry
                rr = u * u + v * v
                if rr > 1:
                    continue
                z = math.sqrt(max(0, 1 - rr))
                nx, ny = u * c + v * s, -u * s + v * c
                value = max(0, min(.999, .23 + .71 * (-.40 * nx - .54 * ny + .74 * z))) * (len(ramp) - 1)
                lo = int(value)
                threshold = ((xx % 4) * 5 + (yy % 4) * 3) % 16 / 16
                shade = min(len(ramp) - 1, lo + int(value - lo > threshold))
                if rr > .93 and nx + ny > .2:
                    shade = 0
                self.im.putpixel((xx, yy), ramp[shade])

    def limb(self, points, ramp, width=5):
        self.line(points, ramp[0], width + 2)
        self.line(points, ramp[min(2, len(ramp) - 1)], width)
        for x, y in points[1:-1]:
            self.ball(x, y, width / 2, width / 2, ramp)

    def crystal(self, x, y, rx, h, ramp, tilt=0.):
        """Faceted starglass/amethyst crystal spire."""
        y = max(y, 2.)
        tip = (x + tilt, y + h)
        l0, r0 = (x - rx, y), (x + rx, y)
        lm, rm = (x - rx * .85 + tilt * .35, y + h * .55), (x + rx * .85 + tilt * .35, y + h * .55)
        mc = (x + tilt * .2, y + h * .48)
        self.poly([l0, lm, tip, rm, r0], ramp[2], outline=ramp[0])
        self.poly([l0, lm, tip, mc], ramp[3], outline=ramp[0])
        self.poly([r0, rm, tip, mc], ramp[1], outline=ramp[0])
        self.line([mc, tip], ramp[-1], 1)

    def eye(self, x, y, clip, n, size=1.0, pupil=OUTLINE):
        if clip == 'die' and n >= 2:
            self.line([(x - 2.5 * size, y - 2 * size), (x + 2.5 * size, y + 2 * size)], OUTLINE, 2)
            self.line([(x - 2.5 * size, y + 2 * size), (x + 2.5 * size, y - 2 * size)], OUTLINE, 2)
        elif clip == 'idle' and n == 3:
            self.line([(x - 3 * size, y), (x + 3 * size, y + .5)], OUTLINE, 2)
        else:
            self.ellipse(x, y, 4.4 * size, 6.2 * size, OUTLINE)
            self.ellipse(x, y + .4, 3.4 * size, 5.1 * size, EYE_WHITE)
            self.ellipse(x + 1.0 * size, y - .2, 1.7 * size, 3.3 * size, pupil)
            self.ellipse(x + .6 * size, y + 2.0 * size, 1.1, 1.1, WHITE)
            if clip == 'attack' and n < 3:
                self.line([(x - 3.8 * size, y + 5.5 * size), (x + 3.2 * size, y + 2.8 * size)], OUTLINE, 2)

    def face(self, x, y, clip, n, size=1.0, sep=5.8, mouth=True, pupil=OUTLINE):
        for dx in (-sep, sep):
            self.eye(x + dx * size, y, clip, n, size, pupil=pupil)
        if clip != 'die' or n < 2:
            self.ellipse(x - (sep + 5.5) * size, y - 4.5 * size, 2.5, 1.4, BLUSH)
            self.ellipse(x + (sep + 5.5) * size, y - 4.5 * size, 2.5, 1.4, BLUSH)
        if mouth:
            if clip == 'attack' and n in (3, 4, 5):
                self.ellipse(x + 1, y - 7.5 * size, 3.2 * size, 2.2 * size, OUTLINE)
            else:
                self.line([(x - 2.8 * size, y - 7.5 * size), (x, y - 8.5 * size), (x + 2.8 * size, y - 7.5 * size)], OUTLINE)


def arm_ik(sh, target, l1, l2, bend=1):
    dx, dy = target[0] - sh[0], target[1] - sh[1]
    d = math.hypot(dx, dy) or 1e-6
    d = min(d, l1 + l2 - .5)
    ang = math.atan2(dy, dx)
    cosb = max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
    b = math.acos(cosb) * bend
    elbow = (sh[0] + l1 * math.cos(ang + b), sh[1] + l1 * math.sin(ang + b))
    hand = (sh[0] + d * math.cos(ang), sh[1] + d * math.sin(ang))
    return elbow, hand


def biped_legs(a, ramp, ph, clip, wide, hip_y, rx, ry, w, st=0., wu=0., kneel=0.):
    for sg in (-1, 1):
        swing = math.sin(ph + (0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, swing) * 3.5
        fx = sg * wide + swing * 4.5 + (st * 6 if sg > 0 else -wu * 3)
        hip = (sg * (wide - 1), hip_y)
        knee = (sg * (wide + 1.5) + (fx - sg * wide) * .4, mix(hip_y, ry + 1, .55) + lift * .5)
        ank = (fx, ry + 1 + lift)
        if kneel:
            fx2 = sg * (wide + 6) - sg * 2
            knee = (mix(knee[0], fx2 + 7 * (1 if sg > 0 else .4), kneel), mix(knee[1], 10, kneel))
            ank = (mix(ank[0], fx2 - 3, kneel), mix(ank[1], ry + 1, kneel))
            fx = ank[0]
        a.limb([hip, knee, ank], ramp, w)
        foot(a, fx, lift if not kneel else 0, rx, ry, ramp)


# ----------------------------------------------------------------------------------------------
# 1. Void Moth (voidmoth)
#    Flying indigo-and-lavender moth with four scalloped star-eye wings, fluffy lilac chest ruff,
#    segmented violet abdomen and star-tipped golden antennae. Hovers well above the ground in
#    living clips and falls onto the ground row on death.
# ----------------------------------------------------------------------------------------------
MOTH_A = dict(
    lean=[-3, -8, -13, 4, 14, 10, 4, 0],
    by=[38, 42, 46, 37, 34, 35, 37, 38],
    flap=[.2, .75, 1.25, -.15, -.75, -.45, -.1, .0],
    orb=[0, 3.5, 6.5, 2.5, 0, 0, 0, 0],
    reach=[0, 0, 0, 14, 32, 24, 9, 0],
)
MOTH_D = dict(
    by=[38, 34, 29, 23, 18, 14, 11, 9],
    curl=[0, .14, .32, .55, .76, .90, .97, 1.0],
)


def voidmoth(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    a = Painter('voidmoth', 0)
    is_atk = clip == 'attack'
    is_die = clip == 'die'
    if is_atk:
        lean, by = MOTH_A['lean'][n], MOTH_A['by'][n]
        fl, orb, reach = MOTH_A['flap'][n], MOTH_A['orb'][n], MOTH_A['reach'][n]
        curl = 0.
    elif is_die:
        curl = MOTH_D['curl'][n]
        lean = -curl * 4
        by = MOTH_D['by'][n]
        fl = .35 - curl * 1.45
        orb, reach = 0., 0.
    else:
        lean = recoil
        by = 38 + bob * 1.2 - ([2, 1, 0, 0][n] if clip == 'hurt' else 0)
        fl = math.sin(n * math.pi / 3) * .55 if clip == 'idle' else math.sin(n * math.pi / 2) * .85 if clip == 'walk' else (.8, .4, .1, 0.)[n]
        orb, reach, curl = 0., 0., 0.

    spread = 35 - abs(fl) * 2.5 - curl * 12

    def wing_fan(s, root, a0, a1, rx, ry, sc=.08):
        pts = [root]
        for i in range(13):
            t = i / 12
            ang = math.radians(mix(a0, a1, t) + fl * 22 - curl * 28)
            r = (.74 + .26 * math.sin(math.pi * t) ** .6) * (1 - sc * (i % 2))
            pts.append((root[0] + s * math.cos(ang) * rx * r, max(2.5, root[1] + math.sin(ang) * ry * r)))
        return pts

    def wing_pt(s, root, a0, a1, rx, ry, t, r):
        ang = math.radians(mix(a0, a1, t) + fl * 22 - curl * 28)
        return (root[0] + s * math.cos(ang) * rx * r, max(3., root[1] + math.sin(ang) * ry * r))

    # Hindwings
    for s in (-1, 1):
        root = (lean + s * 4, max(4., by - 2))
        pts = wing_fan(s, root, 10, -64, spread - 3, 21)
        a.poly(pts, VIOLET[1 if s < 0 else 2], outline=VIOLET[0])
        inner = wing_fan(s, root, 14, -56, (spread - 3) * .72, 15, sc=.04)
        a.poly(inner, PEARL[1 if s < 0 else 2])
        ox, oy = wing_pt(s, root, 10, -64, spread - 3, 21, .48, .60)
        a.ball(ox, oy, 3.8, 3.8, GOLD)
        a.ellipse(ox, oy, 1.6, 1.6, OUTLINE)
        a.ellipse(ox - 1, oy + 1, .9, .9, WHITE)

    # Large scalloped forewings with golden star-eye ocelli
    for s in (-1, 1):
        root = (lean + s * 3, max(6., by + 4))
        pts = wing_fan(s, root, 114, 6, spread + (4 if is_atk and n in (3, 4, 5) and s > 0 else 0), 30)
        a.poly(pts, VIOLET[2 if s > 0 else 1], outline=VIOLET[0])
        inner = wing_fan(s, root, 108, 12, spread * .76, 22, sc=.04)
        a.poly(inner, VIOLET[3 if s > 0 else 2])
        for vt in (.45, .72):
            vp = wing_pt(s, root, 114, 6, spread, 30, vt, .75)
            a.line([root, vp], VIOLET[0], 1)
        ox, oy = wing_pt(s, root, 114, 6, spread, 30, .54, .62)
        a.ball(ox, oy, 6.2, 6.5, GOLD)
        a.ball(ox, oy, 3.8, 4.0, AMBER[2:])
        a.ellipse(ox + .4, oy - .3, 2.0, 2.2, OUTLINE)
        a.ellipse(ox - 1.4, oy + 1.8, 1.1, 1.1, WHITE)
        for k in range(3):
            px, py = wing_pt(s, root, 114, 6, spread, 30, .28 + k * .22, .86)
            a.ellipse(px, py, 1.3, 1.3, PEARL[4])

    # Plump segmented dark-indigo abdomen (kept well above ground in living clips)
    ab_y = max(5., by - 9 + curl * 4)
    a.ball(lean - 2, ab_y, 7.5, 9.5 * (1 - curl * .35), VIOLET[:4])
    for k in range(3):
        yy = ab_y + 3 - k * 4 * (1 - curl * .35)
        a.line([(lean - 7, yy), (lean + 3, yy)], VIOLET[0], 1)

    # Fluffy lavender-pearl chest ruff and chibi head
    a.ball(lean + 1, by + 2, 10.5, 9.5, PEARL)
    hx, hy = lean + 3 + (3 if is_atk and n in (4, 5) else 0), max(11., by + 14 - curl * 6)
    a.ball(hx, hy, 12.5, 11.0, PEARL)
    a.ball(hx - 4, hy + 5, 5.5, 3.0, PEARL[2:])
    a.face(hx + 1.5, hy - 1, clip, n, .82, sep=5.2, pupil=VIOLET[0])

    # Feathered golden antennae with glowing star tips
    sway = math.sin(n * math.pi / 3) * 1.5 if clip == 'idle' else math.sin(n * math.pi / 2) * 2.0 if clip == 'walk' else 0
    ant_lift = (6 if is_atk and n in (1, 2) else -3 if is_atk and n in (4, 5) else 0) - curl * 9
    for s in (-1, 1):
        ax0, ay0 = hx + s * 4.5, hy + 8.5
        ax1, ay1 = hx + s * (10.5 + sway * .5), max(5., hy + 18.5 + ant_lift)
        a.limb([(ax0, ay0), ((ax0 + ax1) / 2, ay0 + 6 + ant_lift * .5), (ax1, ay1)], GOLD, 2)
        if not is_die or n < 5:
            spark(a, ax1, ay1 + 1, AMBER[4], 3)

    # Ambient stardust motes in flight; settling motes on death
    if not is_die:
        for k in range(3):
            mx = lean - 22 + k * 21 + ((n * 2 + k) % 5)
            my = by - 8 + ((n * 3 + k * 4) % 10)
            a.ellipse(mx, my, 1.4, 1.4, PEARL[4] if k % 2 else AMBER[3])
    else:
        for k in range(5):
            mx = -22 + k * 11 + (n % 2)
            my = max(1., (24 - k * 2) * (1 - curl))
            a.ellipse(mx, my, 1.6, 1.2, PEARL[3] if k % 2 else GOLD[3])

    # Attack wind-up starlight orb & forward star-mote barrage
    if orb > 0:
        a.ball(hx + 16, hy + 6, orb, orb, GOLD)
        a.ball(hx + 16, hy + 6, orb * .6, orb * .6, PEARL[2:])
        spark(a, hx + 16, hy + 6, WHITE, 4)
    if reach > 0:
        for k in range(4):
            sx = hx + 10 + reach * (.35 + .22 * k)
            sy = hy + 2 + (k % 2) * 6 - 3
            a.ball(sx, sy, 3.6 - k * .4, 3.2 - k * .3, GOLD if k % 2 == 0 else VIOLET[1:])
            spark(a, sx + 2, sy, WHITE if k == 3 else AMBER[4], 4 if k == 3 else 3)
    return a


# ----------------------------------------------------------------------------------------------
# 2. Crystalwyrm (crystalwyrm)
#    Four-legged draconic starglass wyrm with azure scales, pale ice-blue belly scutes, dorsal
#    amethyst crystal ridge, swept-back amethyst horns and four clawed feet planted on the ground.
# ----------------------------------------------------------------------------------------------
WYRM_FAR_DX = 9
WYRM_A = dict(
    lean=[-3, -8, -13, 5, 15, 11, 4, 0],
    hdy=[3, 9, 15, 2, -3, -1, 1, 0],
    jaw=[0, 2, 5, 4, 7, 4, 1, 0],
    fstep=[0, -2, -4, 5, 8, 5, 2, 0],
    flift=[0, 3, 6, 1, 0, 0, 0, 0],
    reach=[0, 0, 0, 12, 26, 20, 7, 0],
)
WYRM_D = dict(
    by=[28, 27, 24, 21, 18, 16, 14.5, 14],
    hx=[24, 24, 25, 27, 29, 31, 33, 34],
    hy=[44, 41, 35, 28, 21, 16, 13, 11],
    ff=[0, .25, .7, 1, 1, 1, 1, 1],
    hf=[0, 0, .35, .8, 1, 1, 1, 1],
    splay=[0, 0, 0, 0, .3, .65, .9, 1],
)


def wyrm_leg(front, far, step=0., lift=0., lean=0.):
    d = WYRM_FAR_DX if far else 0
    X = (10 if front else -22) + d
    root = (X + lean * .6, 24)
    ank_y = 9 + lift * .7
    ankle = (X + (2 if front else -2) + step * .7, ank_y)
    knee = (X + (-2 if front else 5) + step * .25 + lean * .3, (root[1] + ank_y) / 2 - 1 + lift * .3)
    return [root, knee, ankle, (X + (3 if front else -1) + step, 3 + lift)]


def wyrm_leg_death(front, far, g, splay, by):
    X = (10 if front else -22) + (WYRM_FAR_DX if far else 0)
    rest = wyrm_leg(front, far)
    rest[0] = (X, by - 4)
    tuck = [(X, 0), (X + 5, 6), (X - 1, 4), (X - 5, 3)] if front else [(X, 0), (X + 7, 7), (X - 3, 5), (X - 10, 3)]
    pts = [mixp(rest[i], tuck[i], g) for i in range(4)]
    pts[0] = (X, by - 4)
    if splay:
        end = [(X, 6), (X + 8, 5), (X + 15, 4), (X + 21, 3)] if front else [(X, 6), (X - 8, 5), (X - 15, 4), (X - 21, 3)]
        pts = [mixp(pts[i], end[i], splay) for i in range(4)]
    return pts


def crystalwyrm(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    a = Painter('crystalwyrm', 0)
    is_atk = clip == 'attack'
    is_die = clip == 'die'
    if is_die:
        by = WYRM_D['by'][n]
        lean, hdy, jaw, reach = 0., 0., (2 if n < 4 else 0), 0.
        hx, hy = WYRM_D['hx'][n], WYRM_D['hy'][n]
        legs = []
        for far in (True, False):
            for front in (False, True):
                g = WYRM_D['ff'][n] if front else WYRM_D['hf'][n]
                legs.append((front, far, wyrm_leg_death(front, far, g, WYRM_D['splay'][n], by)))
    else:
        hurt = [3, 2, 1, 0][n] if clip == 'hurt' else 0
        lean = (WYRM_A['lean'][n] if is_atk else 0) + recoil
        by = 28 + bob * .7 - hurt * .5 - (2 if is_atk and n in (4, 5) else 0)
        hdy = (WYRM_A['hdy'][n] if is_atk else 0) + hurt * 1.2
        jaw = WYRM_A['jaw'][n] if is_atk else 0.
        reach = WYRM_A['reach'][n] if is_atk else 0.
        hx, hy = 24 + lean, 44 + bob * .8 + hdy
        legs = []
        for far in (True, False):
            for front in (False, True):
                ph = (0 if front else math.pi) + (math.pi if far else 0)
                sw_ = math.sin(n * math.pi / 4 + ph) if clip == 'walk' else 0
                step = sw_ * 3.0
                lift = max(0, sw_) * 3.2
                if is_atk and front:
                    step += WYRM_A['fstep'][n] * (1 if not far else .6)
                    lift += WYRM_A['flift'][n] * (1 if not far else 0)
                legs.append((front, far, wyrm_leg(front, far, step, lift, lean)))

    # Far legs
    for front, f, pts in legs:
        if f:
            a.limb(pts[:3], AZURE[:3], 3)
            a.limb(pts[2:], AZURE[:3], 2)
            a.ball(pts[3][0], pts[3][1], 3.0, 3, AZURE[:4])

    # Sweeping crystal-crested tail held well above the ground row so it never merges with the hind feet
    bx = -5 + lean * .45
    t_wave = (math.sin(n * math.pi / 3) * 2.0 if clip == 'idle' else math.sin(n * math.pi / 2) * 3.0 if clip == 'walk' else 0) * (1 - fall)
    tail_pts = [
        (bx - 15, max(12., by - 1)),
        (bx - 24, max(14., by + 4 + t_wave * .5 - fall * 6)),
        (bx - 32, max(16., by + 11 + t_wave - fall * 10)),
        (bx - 38, max(18., by + 18 + t_wave * 1.2 - fall * 13)),
    ]
    for i, (tx, ty) in enumerate(tail_pts):
        r = 8.5 - i * 1.6
        a.ball(tx, ty, r + 1.5, r, AZURE)
        if i < 3:
            a.crystal(tx - 1, ty + r - 1, 2.6 - i * .3, (8 - i * 1.5) * (1 - fall * .4), VIOLET, tilt=-2)
    a.crystal(tail_pts[-1][0] - 3, tail_pts[-1][1] + 2, 3.2, 8 * (1 - fall * .3), PEARL, tilt=-4)

    # Dorsal amethyst crystals along the back
    for i, (cx, cy, ch) in enumerate(((-15, by + 10, 11), (-4, by + 12, 13), (7, by + 11, 11))):
        a.crystal(cx + lean * .5, cy, 3.4, ch * (1 - fall * .45), VIOLET if i % 2 == 0 else PEARL, tilt=-1.5)

    # Torso barrel and pale ice-blue belly scutes
    a.ball(bx, by, 23, 13.5, AZURE)
    a.ball(bx - 6, by + 6, 10, 4, AZURE[1:])
    for k in range(4):
        sx = bx - 12 + k * 8
        a.ball(sx, max(9., by - 7), 4.8, 3.0, AZURE[2:])

    # Near legs (planted on y=0 when lift=0)
    for front, f, pts in legs:
        if not f:
            a.limb(pts[:3], AZURE, 4)
            a.limb(pts[2:], AZURE, 3)
            a.ball(pts[3][0], pts[3][1], 3.4, 3, AZURE[1:])

    # Serpentine neck chain from shoulder to head along a smooth curve
    sh = (11 + lean * .5, by + 2)
    ctrl = ((sh[0] + hx) * .5 - 4, (sh[1] + hy) * .5 + 3)
    for i, t in enumerate((.18, .38, .58, .78, .92)):
        nx = (1 - t) ** 2 * sh[0] + 2 * (1 - t) * t * ctrl[0] + t ** 2 * (hx - 2)
        ny = (1 - t) ** 2 * sh[1] + 2 * (1 - t) * t * ctrl[1] + t ** 2 * (hy - 1)
        nr = 10.0 - i * .5
        a.ball(nx, max(9., ny), nr, nr * .88, AZURE)
        a.ball(nx + 3, max(8., ny - 3), nr * .5, nr * .36, AZURE[2:])
    a.crystal(ctrl[0] - 3, max(12., ctrl[1] + 5), 2.8, 9 * (1 - fall * .4), VIOLET, tilt=-2.5)

    # Hinged lower jaw, horned head, amethyst crystal horns & big eyes
    a.ball(hx + 7, max(6., hy - 6 - jaw * .6), 8.5, 3.8, AZURE[1:])
    if jaw > 1.2:
        a.ellipse(hx + 8, max(7., hy - 4.5 - jaw * .3), 5.5, jaw * .35 + 1.2, MAROON[1])
        for fx in (hx + 5, hx + 11):
            a.poly([(fx - 1.3, hy - 3), (fx + 1.3, hy - 3), (fx, hy - 7 - jaw * .3)], WHITE, OUTLINE)
    a.ball(hx, hy, 13.5, 11.5, AZURE)
    a.ball(hx + 8.5, max(8., hy - 2.5), 8.0, 5.2, AZURE)
    a.ball(hx - 4, hy + 5, 6.0, 3.2, AZURE[1:])
    a.crystal(hx - 7, hy + 8, 3.6, 14 * (1 - fall * .25), VIOLET, tilt=-4.5)
    a.crystal(hx + 1, hy + 9, 3.0, 11 * (1 - fall * .25), PEARL, tilt=-2.5)
    a.face(hx + 2, hy + 1, clip, n, .82, sep=5.0, mouth=False, pupil=MAROON[1])
    a.ellipse(hx + 14, max(8., hy - 1.5), 1.6, 1.2, OUTLINE)

    # Wind-up throat crystal glow & strike prismatic shard barrage
    if is_atk and n in (1, 2):
        r = 3.0 + (n - 1) * 2.2
        a.ball(hx + 14, hy - 3, r, r, PEARL)
        spark(a, hx + 14, hy - 3, WHITE, 4)
    if reach > 0:
        for k in range(4):
            sx = hx + 14 + reach * (.32 + .22 * k)
            sy = hy - 3 + (k % 2) * 6 - 2
            a.crystal(sx, sy - 4, 2.8, 8.0, VIOLET if k % 2 else AZURE[1:], tilt=2)
            spark(a, sx + 2, sy, WHITE if k == 3 else PEARL[4], 4 if k == 3 else 3)

    # Death: scattered fractured amethyst shards on the ground row once the body settles
    if is_die and n >= 4:
        for k in range(3):
            sx = -20 + k * 18 + (n - 4) * (.6 if k % 2 else -.6)
            a.crystal(sx, 2., 2.6, 5.5, VIOLET if k % 2 == 0 else PEARL, tilt=2 if k % 2 else -2)
    return a


# ----------------------------------------------------------------------------------------------
# 3. Orbit Beetle (orbitbeetle)
#    Bronze-and-amber celestial scarab on four planted jointed leg tracks with a curved golden
#    rhinoceros horn, violet under-wings beneath rigid wing-cases and a golden moon orbiting
#    overhead. Rolls onto its back on death as the orbiting moon drops beside it.
# ----------------------------------------------------------------------------------------------
BEETLE_A = dict(
    lean=[-3, -7, -11, 5, 14, 10, 4, 0],
    wing=[0, 7, 14, 9, 4, 2, 0, 0],
    horn=[0, 4, 9, -2, -5, -3, -1, 0],
    fstep=[0, -2, -3, 5, 8, 5, 2, 0],
    flift=[0, 3, 5, 1, 0, 0, 0, 0],
    reach=[0, 0, 0, 12, 26, 20, 7, 0],
)
BEETLE_D = dict(
    by=[26, 25, 23, 21, 19, 18, 17, 17],
    flip=[0, .12, .32, .58, .82, .94, .98, 1.0],
)


def orbitbeetle(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    a = Painter('orbitbeetle', 0)
    is_atk = clip == 'attack'
    is_die = clip == 'die'
    if is_atk:
        lean, wlift, hlift = BEETLE_A['lean'][n], BEETLE_A['wing'][n], BEETLE_A['horn'][n]
        reach, flip = BEETLE_A['reach'][n], 0.
        by = 26 + (3 if n == 1 else 6 if n == 2 else -2 if n in (4, 5) else 0)
    elif is_die:
        by, flip = BEETLE_D['by'][n], BEETLE_D['flip'][n]
        lean, wlift, hlift, reach = -flip * 3, 0., 0., 0.
    else:
        hurt = [3, 2, 1, 0][n] if clip == 'hurt' else 0
        lean = recoil
        by = 26 + bob * .6 - hurt * .5
        wlift, hlift, reach, flip = 0., 0., 0., 0.

    # Orbiting miniature golden moon: behind shell when sin(th) < 0, in front otherwise; drops to ground on death
    th = n * (math.pi / 3 if clip == 'idle' else math.pi / 4) + .7
    if is_atk and n < 7:
        mx = lean + (-8 if n <= 2 else 18 + reach * .85)
        my = by + 35 + wlift * 1.15 - (14 if n in (4, 5) else 0)
        moon_back = False
    elif is_die:
        mx = mix(18, -32 - n * .8, flip)
        my = mix(by + 30, 5., flip ** .85)
        moon_back = False
    else:
        th0 = .7 if is_atk else th
        mx = lean + math.cos(th0) * 26
        my = by + 32 + math.sin(th0) * 5
        moon_back = math.sin(th0) < 0

    def draw_moon():
        a.ball(mx, max(5., my), 5.2, 5.2, GOLD)
        a.ellipse(mx - 1.5, max(6., my + 1.5), 1.4, 1.4, WHITE)
        a.ellipse(mx + 1.6, max(4.5, my - 1.2), 1.2, 1.0, AMBER[1])

    if moon_back:
        draw_moon()

    # Four separated leg tracks planted on y=0 in idle (X = -25, -11, +3, +17) so 4 groundRuns & 4 legTracks read cleanly
    leg_specs = [(-25, -18, True), (-11, -7, False), (3, 3, True), (17, 12, False)]

    def draw_beetle_leg(k, fx0, hx0, far):
        ph = n * math.pi / 4 + (0 if k % 2 == 0 else math.pi)
        sw_ = math.sin(ph) if clip == 'walk' else 0
        lift = max(0, sw_) * 3.5
        step = sw_ * 2.5
        if is_atk and k >= 2:
            step += BEETLE_A['fstep'][n] * (.7 if k == 2 else 1.0)
            lift += BEETLE_A['flift'][n] * (.6 if k == 2 else 1.0)
        fx = fx0 + step
        hip = (hx0 + lean * .5, by - 4)
        knee = (fx + (-4 if fx < 0 else 4), 13 + lift * .5)
        ank = (fx, 3 + lift)
        if is_die:
            # Legs buckle then curl upward above the overturned shell while the shell dome rests on y=0
            curl_knee = (hx0 * .9, by + 6 + flip * 10)
            curl_foot = (fx0 * .82 + math.sin(n + k) * 1.5, mix(3, by + 16 + (k % 2) * 4, flip))
            knee = mixp(knee, curl_knee, flip)
            ank = mixp(ank, curl_foot, flip)
        ramp = BROWN[:4] if far else BROWN
        w = 3 if far else 4
        a.limb([hip, knee, ank], ramp, w)
        if not is_die or flip < .25:
            foot(a, ank[0], ank[1] - 3, 3.0 if far else 3.4, 3, PLATE[:4])
        else:
            a.ball(ank[0], ank[1], 2.8, 2.5, PLATE[:4])

    for k, (fx0, hx0, far) in enumerate(leg_specs):
        if far:
            draw_beetle_leg(k, fx0, hx0, True)

    # Rigid bronze-and-amber domed scarab shell (rests directly on the ground when flipped on death)
    shell_y = mix(by, 15., flip)
    a.ball(lean - 3, shell_y, 24, 15, AMBER if flip < .6 else BROWN)
    a.ball(lean - 10, shell_y + (6 if flip < .5 else -4), 10, 5, AMBER[1:])
    a.line([(lean - 2, shell_y + 13), (lean - 2, max(3., shell_y - 11))], BROWN[0], 2)
    for sx, sy, sr in ((-15, 3, 2.4), (-6, 8, 2.6), (6, 5, 2.2), (-10, -4, 2.0)):
        dy = -sy if flip > .5 else sy
        a.poly([(lean + sx, shell_y + dy + sr), (lean + sx + sr, shell_y + dy),
                (lean + sx, shell_y + dy - sr), (lean + sx - sr, shell_y + dy)], GOLD[4], outline=AMBER[0])
    if is_die and n >= 2:
        a.line([(lean - 8, shell_y + 11), (lean - 2, shell_y + 3), (lean - 6, max(3., shell_y - 6))], OUTLINE, 2)

    for k, (fx0, hx0, far) in enumerate(leg_specs):
        if not far:
            draw_beetle_leg(k, fx0, hx0, False)

    # Head, curved golden rhinoceros horn, mandibles and big eyes
    hx = lean + 16 + (5 if is_atk and n in (4, 5) else 0)
    hy = max(12., shell_y - 2 + hlift * .4)
    a.ball(hx, hy, 12.5, 10.5, BROWN)
    # Tapered golden rhinoceros horn curving up from the brow
    horn_tip = (hx + 12 + (6 if is_atk and n in (4, 5) else 0), max(8., hy + 18 + hlift - flip * 14))
    horn_mid = (hx + 7, max(8., hy + 10 + hlift * .5 - flip * 7))
    taper(a, bez((hx + 2, hy + 5), horn_mid, horn_tip), GOLD, 7, 2)
    spark(a, horn_tip[0], horn_tip[1] + 1, WHITE if is_atk and n in (2, 4) else GOLD[4], 3)
    # Pincer mandibles
    spread = 2 + (4 if is_atk and n in (2, 3, 4, 5) else 0)
    for s in (-1, 1):
        a.limb([(hx + 8, max(5., hy - 5)), (hx + 16, max(4., hy - 4 - s * spread * .5))], GOLD, 2)
    a.face(hx + 1, hy + 1, clip, n, .80, sep=4.8, mouth=False, pupil=BLUE[0])

    if not moon_back:
        draw_moon()
    if reach > 0:
        for k in range(4):
            sx = hx + 14 + reach * (.3 + .22 * k)
            sy = hy + 4 + (k % 2) * 7 - 3
            spark(a, sx, sy, WHITE if k == 3 else GOLD[4], 4 if k == 3 else 3)
    return a


# ----------------------------------------------------------------------------------------------
# 4. Eclipse Dryad (eclipsedryad)
#    Sylvan dryad of emerald leaf-layers and warm bark with a black-sun eclipse halo and blazing
#    golden corona behind her head, branch-antlers, rose chest-bloom and two planted bark root-feet.
# ----------------------------------------------------------------------------------------------
DRYAD_D = dict(
    by=[36, 34, 31, 27, 22, 18, 15, 13],
    kneel=[0, .18, .45, .75, .95, 1, 1, 1],
    drop=[0, .12, .32, .58, .82, .94, 1, 1],
)


def eclipsedryad(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    w, st = atk(clip, n)
    is_atk = clip == 'attack'
    is_die = clip == 'die'
    a = Painter('eclipsedryad', recoil + (st * 5 - w * 3 if is_atk else 0))
    ph = n * math.pi / 4
    if is_die:
        by, kneel, dp = DRYAD_D['by'][n], DRYAD_D['kneel'][n], DRYAD_D['drop'][n]
    else:
        hurt = [3, 2, 1, 0][n] if clip == 'hurt' else 0
        by = 36 + bob * .5 - hurt * .5 - st * 2
        kneel = dp = 0.

    sway = math.sin(n * math.pi / 3) * 1.5 if clip == 'idle' else math.sin(ph) * 2.0 if clip == 'walk' else 0
    hx = sway * .3 + dp * 6 + (st * 4 - w * 2 if is_atk else 0)
    hy = max(15., 60 + bob * .6 - dp * 43 + (w * 4 - st * 3 if is_atk else 0))

    # Black-sun eclipse halo and blazing golden corona behind head (shatters into embers on death)
    if not is_die or n < 5:
        halo_y = hy + 3 + (w * 8 if is_atk else 0)
        flare = max(w, st) if is_atk else (.2 if clip == 'idle' and n in (1, 4) else 0.)
        rays = 8
        for k in range(rays):
            ang = k * (2 * math.pi / rays) + .25 + n * .08
            r_in = 15 * (1 - dp * .4)
            r_out = (22 + flare * 8) * (1 - dp * .45)
            p0 = (hx + math.cos(ang - .18) * r_in, max(6., halo_y + math.sin(ang - .18) * r_in))
            p1 = (hx + math.cos(ang) * r_out, max(6., halo_y + math.sin(ang) * r_out))
            p2 = (hx + math.cos(ang + .18) * r_in, max(6., halo_y + math.sin(ang + .18) * r_in))
            a.poly([p0, p1, p2], GOLD[4 if flare > .4 else 3], outline=AMBER[1])
        a.ball(hx, halo_y, 16 * (1 - dp * .4), 16 * (1 - dp * .4), GOLD)
        a.ellipse(hx, halo_y, 12 * (1 - dp * .4), 12 * (1 - dp * .4), OUTLINE)
        a.ellipse(hx - 2, halo_y + 2, 10 * (1 - dp * .4), 10 * (1 - dp * .4), SLATE[0])

    # Two bark root-feet planted on the ground row (groundRuns === 2 in idle, >= 1 in walk)
    biped_legs(a, BROWN, ph, clip, 10, 24, 7, 4, 5, st, w, kneel)

    # Scalloped emerald leaf skirt (kept at y >= 8 so the two planted bark root-feet stay cleanly separated below it)
    skirt_top = by + 4
    skirt_bot = max(6., 11 - dp * 5)
    pts = [
        (-13, skirt_top), (13, skirt_top),
        (19 + dp * 6 + sway * .4, skirt_bot + 5),
        (13 + dp * 4, skirt_bot),
        (7, skirt_bot + 5),
        (0, skirt_bot + 1),
        (-7, skirt_bot + 5),
        (-13 - dp * 4, skirt_bot),
        (-19 - dp * 6 + sway * .4, skirt_bot + 5),
    ]
    a.poly(pts, LEAF[2], outline=LEAF[0])
    for k in range(-2, 3):
        lx = k * 6
        a.poly([(lx, skirt_top - 2), (lx + 3, skirt_bot + 4), (lx, skirt_bot + 1), (lx - 3, skirt_bot + 4)],
               LEAF[3 if k % 2 == 0 else 1], outline=LEAF[0])

    # Bark-and-foliage torso with rose chest star-bloom
    a.ball(0, by + 5, 11, 10, LEAF)
    a.ball(2, by + 5, 3.8, 3.8, CORAL)
    a.ellipse(1.2, by + 6, 1.2, 1.2, WHITE)

    # Far branch arm with leaf cluster
    far_sh = (-10, by + 10)
    far_hand = (-20 - dp * 6, max(6., by - 1 + w * 6 - dp * 22))
    a.limb([far_sh, ((-15 - dp * 3), max(8., by + 5 - dp * 10)), far_hand], BROWN, 4)
    a.ball(far_hand[0], far_hand[1], 4.5, 4.0, LEAF)

    # Near branch arm and leaf-blade staff/hand (raises high on wind-up, sweeps far forward on strike)
    near_sh = (10 + st * 2 - w * 2, by + 10)
    if is_atk:
        hand = (mix(mix(18, 12, w), 32, st), mix(mix(32, 76, w), 38, st))
    elif is_die:
        hand = (mix(18, 26, dp), mix(32, 6, dp))
    else:
        hand = (18 + sway * .5, 32 + bob * .5)
    elbow, hand = arm_ik(near_sh, hand, 13, 13, 1)
    a.limb([near_sh, elbow, hand], BROWN, 4)
    # Leaf-blade fan at the hand
    blade_ang = (1.3 if w > .3 else -.1 if st > .3 else .5) * (1 - dp)
    bx1 = hand[0] + math.cos(blade_ang) * 12
    by1 = max(4., hand[1] + math.sin(blade_ang) * 12)
    px, py = -math.sin(blade_ang) * 4.5, math.cos(blade_ang) * 4.5
    a.poly([hand, (hand[0] + px, max(4., hand[1] + py)), (bx1, by1), (hand[0] - px, max(4., hand[1] - py))],
           LEAF[3], outline=LEAF[0])
    a.line([hand, (bx1, by1)], LEAF[4], 1)

    # Head, emerald leaf hair, branch antlers with glowing leaf tips, and big golden-irised eyes
    a.ball(hx - 2, hy + 2, 14.5, 13.0, LEAF)
    a.ball(hx, hy, 12.5, 11.0, LEAF[2:])
    a.poly([(hx - 11, hy + 4), (hx - 6, hy + 1), (hx - 2, hy + 6), (hx + 3, hy + 1),
            (hx + 8, hy + 6), (hx + 12, hy + 3), (hx + 11, hy + 11), (hx - 11, hy + 11)],
           LEAF[1], outline=LEAF[0])
    a.face(hx + 1.5, hy - 1.5, clip, n, .82, sep=5.0, pupil=AMBER[1])
    for s in (-1, 1):
        ax0, ay0 = hx + s * 6, hy + 10
        ax1, ay1 = hx + s * 14, max(8., hy + 22 - dp * 10)
        a.limb([(ax0, ay0), (hx + s * 10, max(8., hy + 16 - dp * 5)), (ax1, ay1)], BROWN, 2)
        a.poly([(ax1, ay1 + 4), (ax1 + 3, ay1), (ax1, max(4., ay1 - 3)), (ax1 - 3, ay1)], LEAF[4], outline=LEAF[0])

    # Strike: volley of razor star-leaves and golden eclipse sparks ahead
    if is_atk and st > .3:
        for k in range(4):
            lx = hand[0] + 10 + k * 6 + (n - 3) * 2
            ly = hand[1] + (k % 2) * 7 - 3
            a.poly([(lx - 4, ly), (lx, ly + 3), (lx + 5, ly), (lx, ly - 3)], LEAF[4 if k % 2 else 3], outline=LEAF[0])
            if k % 2 == 1:
                spark(a, lx + 2, ly + 2, GOLD[4], 3)

    # Death: falling leaves and golden corona embers settling on the ground
    if is_die and n >= 1:
        for k in range(5):
            lx = -22 + k * 11 + (n % 2) * 2
            ly = max(3., (42 - k * 4) * (1 - dp))
            a.poly([(lx - 3, ly), (lx, ly + 2.5), (lx + 3, ly), (lx, max(2., ly - 2.5))],
                   GOLD[3] if k % 2 else LEAF[3], outline=LEAF[0])
    return a


# ----------------------------------------------------------------------------------------------
# 5. Meteor Golem (meteorgolem)
#    Towering meteoric violet-slate colossus with glowing molten fissures, a faceted amethyst chest
#    core, jagged amethyst shoulder crystals, orbiting asteroid chips and two heavy stone feet.
# ----------------------------------------------------------------------------------------------
METEOR_D = dict(
    by=[36, 35, 32, 28, 24, 20, 17, 15],
    arm=[0, .12, .35, .65, .88, 1, 1, 1],
    head=[0, .06, .22, .48, .72, .92, 1, 1],
    blk=[0, 0, .16, .38, .62, .86, 1, 1],
)


def meteorgolem(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    w, st = atk(clip, n)
    is_atk = clip == 'attack'
    is_die = clip == 'die'
    a = Painter('meteorgolem', recoil + (st * 5 - w * 3 if is_atk else 0))
    ph = n * math.pi / 4
    if is_die:
        by, arm, hd, blk = METEOR_D['by'][n], METEOR_D['arm'][n], METEOR_D['head'][n], METEOR_D['blk'][n]
        kneel = sm(blk * 1.3)
    else:
        hurt = [3, 2, 1, 0][n] if clip == 'hurt' else 0
        by = 36 + bob * .5 - hurt * .5 - st * 2
        arm = hd = blk = kneel = 0.

    # Orbiting meteor chips and rising embers (drop to the floor on death)
    for k in range(3):
        th = n * (math.pi / 3 if clip == 'idle' else math.pi / 4) + k * 2.1
        if is_die:
            cx = -24 + k * 22 + blk * (4 if k % 2 else -4)
            cy = mix(48 + k * 4, 4., blk)
        else:
            cx = math.cos(th) * 30
            cy = by + 16 + math.sin(th) * 6 + k * 3 + (w * 8 if is_atk else 0)
        a.ball(cx, max(4., cy), 3.6, 3.2, SLATE)

    # Two heavy meteor-stone legs and planted boots (groundRuns === 2 in idle, >= 1 in walk)
    biped_legs(a, SLATE, ph, clip, 12, 28, 9, 5, 8, st, w, kneel)

    # Massive meteor-rock torso with molten fissures and a faceted amethyst heart-core
    tx = -blk * 3
    a.ball(tx, by, 22, 19, SLATE)
    a.ball(tx - 7, by + 8, 9, 4, SLATE[1:])
    fissure_col = AMBER[3] if (not is_die or n < 4) else SLATE[0]
    a.line([(tx - 15, by - 6), (tx - 9, by), (tx - 13, by + 6), (tx - 6, by + 10)], fissure_col, 2)
    a.line([(tx + 14, by - 7), (tx + 10, by - 1), (tx + 14, by + 6)], fissure_col, 2)
    a.crystal(tx + 1, max(8., by - 6), 6.5, 14, VIOLET if (not is_die or n < 5) else SLATE[:4], tilt=0)
    if not is_die or n < 4:
        a.ellipse(tx, by + 2, 2.5, 3.2, WHITE if is_atk and n in (1, 2, 4) else AMBER[4])

    # Shoulder boulders, amethyst shoulder spires and IK meteor fists
    lean_x, lean_y = (st * 6 - w * 3, -st * 7 + w * 3) if is_atk else (0., 0.)
    for sg in (-1, 1):
        sh = (sg * 19 - blk * (4 * sg + 2) + lean_x, by + 13 - arm * 7 + lean_y + (w * 5 if is_atk else 0))
        if is_atk:
            tgt = (mix(mix(sg * 28, sg * 12, w), sg * 14 + 18, st),
                   mix(mix(26, 92, w), 11, st))
        elif is_die:
            tgt = mixp((sg * 28, 26), (sg * (30 + arm * 6), 9), arm)
        else:
            tgt = (sg * 28, 26 + (bob if sg < 0 else 0))
        elbow, hand = arm_ik((sh[0], sh[1] - 4), tgt, 16, 16, sg)
        a.limb([(sh[0], sh[1] - 4), elbow, hand], SLATE, 7)
        a.ball(sh[0], max(10., sh[1]), 9.5, 8.5, SLATE)
        a.crystal(sh[0] + sg * 2, max(12., sh[1] + 5), 3.6, 12 * (1 - blk * .4), VIOLET, tilt=sg * 2.5)
        a.ball(hand[0], max(9., hand[1]), 9.5, 9.0, SLATE)
        a.line([(hand[0] - 4, max(9., hand[1] + 2)), (hand[0] + 3, max(7., hand[1] - 3))], fissure_col, 2)
        if is_atk and st > .4 and sg > 0:
            spark(a, hand[0] + 16, 11, WHITE, 5)
            for k in range(4):
                sx = hand[0] + 10 + k * 7
                a.crystal(sx, 5 + (k + n) % 4, 3.2, 8, VIOLET if k % 2 == 0 else AMBER, tilt=2)

    # Heavy boulder head with craggy brow, glowing eyes and jagged mouth
    hx = hd * 14 + (st * 5 - w * 2 if is_atk else 0)
    hy = max(15., 61 + bob * .4 - hd * 43 - (st * 5 if is_atk else 0) + (w * 4 if is_atk else 0))
    a.ball(hx, hy, 15.5, 13.0, SLATE)
    a.ball(hx - 5, hy + 6, 7.0, 3.5, SLATE[1:])
    a.poly([(hx - 13, hy + 5), (hx + 13, hy + 5), (hx + 11, hy + 2), (hx - 11, hy + 2)], SLATE[0])
    a.face(hx + 1, hy - 1, clip, n, .86, sep=5.6, mouth=False, pupil=AMBER[1])
    mz = [(hx - 6, max(5., hy - 7)), (hx - 3, max(4., hy - 9)), (hx, max(5., hy - 7)),
          (hx + 3, max(4., hy - 9)), (hx + 6, max(5., hy - 7))]
    a.line(mz, OUTLINE, 2)
    if is_die and n >= 2:
        a.line([(hx - 8, hy + 8), (hx - 2, hy + 2), (hx - 5, max(5., hy - 5))], OUTLINE, 2)
    return a


DRAW = dict(
    voidmoth=voidmoth,
    crystalwyrm=crystalwyrm,
    orbitbeetle=orbitbeetle,
    eclipsedryad=eclipsedryad,
    meteorgolem=meteorgolem,
)

STRICT = True
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if kind == 'voidmoth':
        # Flying Void Moth stays well above the ground in living clips and settles onto kay at the end of death.
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
    elif kind == 'voidmoth':
        if clip != 'die' and low > kay - 12:
            problem = f'voidmoth should fly well above anchor row {kay} (lowest row {low})'
        elif clip == 'die' and low > kay:
            problem = f'voidmoth death frame {n} sinks below anchor row {kay} (lowest row {low})'
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
        name = PREFIX + kind + '_all'
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/astral_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/astral_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    meta = dict(frame=[W, H], anchor=[AX, AY], kinds=KINDS, clips={}, sprites=saved, tops={}, artStyle='greenmeadow-slime')
    proof, atlases = {}, {}
    for kind in KINDS:
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
        dest = ASSETS / f'astral_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 170 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    meta = json.loads(MANIFEST.read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'astral_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW]:
        old_kf = KIND_FRAMES.get(kind)
        KIND_FRAMES[kind] = (192, 192, 96, 160)
        left = right = up = 0
        for clip, grids in frames(kind).items():
            for grid in grids:
                ys, xs = np.nonzero(grid)
                if xs.size:
                    left = max(left, 94 - int(xs.min()) + 2)
                    right = max(right, int(xs.max()) - 94 + 2)
                    up = max(up, 158 - int(ys.min()))
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


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
