#!/usr/bin/env python3
"""The Moonspore Canopy (zone 16) redo: seven native PixelFlow sources with per-kind frames.

preview | extents | build | refresh <kinds> | export | verify

Owner direction (2026-11-04): every enemy must look UNIQUE and MEAN. The last zones all shared one face (a big round
glossy eye with a highlight, plus blush), so here each kind has its own face and silhouette: slit and angular eyes,
fangs, scowls, hollow sockets, no blush. Shaded volume (`plate`/`ball`/`taper`), props at least four pixels thick,
no floating glyphs, eight distinct attack frames (wind-up, strike, recovery) and eight distinct death frames per kind.
The original cel-shaded art is kept in /media/raid/valhallasc-data/moonspore-slime-original-20261104
(`scripts/rollback_moonspore_art.py`).

  - glowcapgrazer: hunched boar-beast of mossy hide with a ridge of glowing toadstool caps on its back, a heavy scowling
    wedge head with a bone brow, burning slit eyes and two upturned tusks; lowers its head and gores forward in a spore
    cloud; dies by buckling, rolling onto its side with its caps wilting and shrivelling.
  - silkwing: death's-head moth with pale tattered razor wings, a skull mark on its thorax, red slit eyes, hooked
    mandibles and feathered antennae; hovers, throws its wings up and dives in a slashing sweep shedding scales; dies
    by folding its wings and spiralling to the ground, then curling up.
  - rootlurker: hunched root-thing of gnarled bark with long clawed arms, antler branches and a knothole face with
    burning slit eyes and a jagged splinter-tooth mouth; rears up and rakes both claws down as roots burst from the ground;
    dies by splintering: the limbs split off and the trunk slumps into a heap of logs.
  - lanternwraith: hovering hooded wraith with a black void hood, two narrow green slit eyes, a ragged tapering cloak and
    a skeletal hand holding a hooked lantern; lifts the lantern and hurls a ghostfire orb; dies as the cloak unravels upward
    into wisps and the lantern drops to the ground.
  - mireheart: bog-toad elite, hulking, with a heavy-lidded scowl, a wide fanged mouth, thorny rib roots around an exposed
    pulsing heart and a long whipping tongue; crouches and lashes the tongue out, then slams down; dies as the heart goes
    dark and the body deflates and sags over.
  - silverwidow: giant black-violet spider elite with a silver crescent mark, six unequal burning eyes, dripping fangs and
    eight thick jointed legs; rears on its hind legs with its fangs raised then drives forward in a lunging bite with a web
    spray; dies by curling its legs inward and flipping onto its back.
  - nightbloom: carnivorous flower elite: a hooded plum bloom with thorn-lined jaw petals and two lime slit eyes, vine
    whips and root feet; rears the head back and snaps down with the vines lashing; dies by wilting, the stem withering
    and the head dropping, petals scattering.
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
from astral_slime_redraw import (
    Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BLUSH,
    BONE, PLATE, PURPLE, TEAL, GOLD, GREEN, FUR, BLUE, BROWN, OLIVE, PINK, MAROON, CORAL, PEARL, VIOLET, CRIMSON,
    AMBER, AZURE, SLATE, mix, mixp, rot, sm, bez, taper, foot, arm_ik,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/moonspore-slime'
REGISTRY = ROOT / 'scripts/moonspore_slime_sources.txt'
MANIFEST = ASSETS / 'moonspore.txt'
PREFIX = 'valhallasc_moonspore_slime_style_'
KINDS = ['glowcapgrazer', 'silkwing', 'rootlurker', 'lanternwraith', 'mireheart', 'silverwidow', 'nightbloom']
NAMES = dict(zip(KINDS, ['Glowcap Grazer', 'Silkwing', 'Rootlurker', 'Lantern Wraith', 'The Mireheart', 'The Silver Widow', 'The Nightbloom']))
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    glowcapgrazer=(154, 75, 52, 69),
    silkwing=(117, 114, 52, 108),
    rootlurker=(122, 103, 46, 97),
    lanternwraith=(125, 112, 37, 106),
    mireheart=(185, 82, 49, 76),
    silverwidow=(179, 100, 60, 94),
    nightbloom=(98, 105, 36, 99),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('silkwing', 'lanternwraith')
PALETTE = PALETTE[:] + [
    '#0f2418', '#244a2e', '#437f46', '#7fb85c', '#c4eb92',   # MOSS (swamp hide, leaves)
    '#08323a', '#126a68', '#27b096', '#76ecc0', '#d6fff0',   # SPORE (glowing caps)
    '#34081a', '#781a3c', '#c0345c', '#f06c8c', '#ffc2d0',   # HEART (raw red flesh)
    '#2a0a34', '#661a78', '#b43acb', '#ee78f0', '#ffd0fb',   # ORCHID (widow glow, bloom magenta)
    '#2a0e30', '#5a1a58', '#963078', '#d05aa0', '#f8a8d0',   # PLUM (nightbloom petals)
    '#18110d', '#3c2a1e', '#68482e', '#9a7446', '#d0aa6e',   # BARK
    '#06060e', '#101022', '#1c1c38', '#2c2c52', '#444478',   # VOID (wraith hood and cloak)
    '#114a28', '#2e9c46', '#78e65a', '#c2ff98', '#f2ffe0',   # GHOSTFIRE
    '#1a1424', '#34283f', '#56486a', '#7e6e98', '#aa9cc4',   # WEB (widow body greys)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
_n = len(PALETTE) - 45
MOSS, SPORE, HEART, ORCHID, PLUM, BARK, VOID, GHOST, WEBGREY = [list(range(_n + 5 * i, _n + 5 * i + 5)) for i in range(9)]


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Art scale per kind (1.0 = the coordinates written in the draw functions); judged on an in-game screenshot.
SCALE = dict(glowcapgrazer=.8, silkwing=.65, rootlurker=.82, lanternwraith=.75, mireheart=.86, silverwidow=.72, nightbloom=.76)


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


def curves(clip, n):
    """Explicit animation beats: ready, anticipate, wind-up, release, impact, follow, recoil, recover."""
    wind = [0, .48, 1, .35, 0, 0, .08, 0][n] if clip == 'attack' else 0
    strike = [0, 0, 0, .50, 1, .72, .28, 0][n] if clip == 'attack' else 0
    dead = sm(n / 7) if clip == 'die' else 0
    phase = n * math.pi / (3 if clip == "idle" else 4) + (.35 if clip == "idle" else 0)
    bob = math.sin(phase) * (1.2 if clip == "idle" else 2 if clip == "walk" else .9 if clip == "attack" else 0)
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    return wind, strike, dead, phase, bob, recoil


def plate(a, pts, ramp, k=.78):
    """A shaded polygon: dark rim, mid body, lit upper-left panel and a bright core, never a flat fill."""
    a.poly(pts, ramp[1], outline=ramp[0])
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    a.poly([(cx + (x - cx) * k - .8, cy + (y - cy) * k + .8) for x, y in pts], ramp[2])
    a.poly([(cx + (x - cx) * k * .55 - 1.6, cy + (y - cy) * k * .55 + 1.6) for x, y in pts], ramp[3])


def blob(a, x, y, rx, ry, ramp, ang=0.):
    """A ball with a clean dark rim (the shading terminator is the rim)."""
    a.ball(x, y, rx, ry, ramp, ang)


def fang(a, x, y, length, width, ang, ramp=BONE):
    """A tapering tusk/fang: base at (x, y), tip along ang (radians, 0 = +x, pi/2 = up)."""
    tx, ty = x + math.cos(ang) * length, y + math.sin(ang) * length
    nx, ny = -math.sin(ang) * width / 2, math.cos(ang) * width / 2
    a.poly([(x + nx, y + ny), (tx, ty), (x - nx, y - ny)], ramp[2], outline=ramp[0])
    a.poly([(x + nx * .3, y + ny * .3), (tx - (tx - x) * .15, ty - (ty - y) * .15), (x + nx * .7 - (tx - x) * .05, y + ny * .7)], ramp[4])


def slit(a, x, y, w, h, glow, lid, side=1, shut=False, slant=.55, pupil=True):
    """An angry slit eye: a glowing lens cut by a heavy brow lid that slopes down towards the nose.
    side +1 = the outer end is at +x, -1 = at -x."""
    if shut:
        a.line([(x - w, y - h * .3), (x + w, y + h * .1)], OUTLINE, 2)
        return
    a.ellipse(x, y, w + 1.6, h + 1.6, OUTLINE)
    a.ellipse(x, y, w, h, glow[3])
    a.ellipse(x - side * .6, y - h * .15, w * .62, h * .6, glow[4])
    if pupil:
        a.line([(x, y - h * .9), (x, y + h * .9)], glow[0], 1)
    top = y + h + 1.5
    ew = w + 1.5
    a.poly([(x - side * ew, top), (x + side * ew, top), (x + side * ew, y + h * .15),
            (x - side * ew, y - h * slant)], lid)
    a.line([(x - side * ew, y - h * slant), (x + side * ew, y + h * .15)], OUTLINE, 1)


def dust(a, x, y, r, ramp=PEARL):
    a.ball(x, y, r, r * .8, ramp)



# KINDS-START

def cap(a, bx, by, x, y, r, tilt=0., wilt=0., pulse=1., spots=1):
    """A glowing toadstool: pale stem from (bx, by) up to the cap, glowing gill ring, spotted dome."""
    r = r * pulse * (1 - .38 * wilt)
    y -= wilt * r * .5
    taper(a, [mixp((bx, by), (x, y - r * .2), i / 4) for i in range(5)], BONE, max(4, r * .5), max(4, r * .4))
    a.ellipse(x, y - r * .22, r * .96, r * .3, SPORE[0])
    a.ellipse(x, y - r * .2, r * .86, r * .22, SPORE[4] if wilt < .6 else SPORE[2])
    a.ball(x, y + r * .08, r, r * .66, SPORE if wilt < .7 else [SPORE[0], SPORE[0], SPORE[1], SPORE[1], SPORE[2]], tilt - wilt * .5)
    for i in range(spots):
        a.ellipse(x - r * .4 + i * r * .55, y + r * (.32 - .1 * (i % 2)), max(1.5, r * .13), max(1.2, r * .1), GOLD[4])


def glowcapgrazer(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    lunge = st * 20 - w * 9 + recoil
    a = Painter('glowcapgrazer', lunge * .6)
    dn = d
    cy = mix(33 + bob * .5 - w * 2 + st * 1, 15, sm(dn * 1.4))
    far = [MOSS[0], MOSS[0], MOSS[1], MOSS[2], MOSS[3]]
    pulse = 1 + .07 * math.sin(ph * 2) * (1 - dn)
    flare = w * .8 + st * .5
    # legs: far pair first, then near pair; on death they stiffen and splay out sideways
    for k, (hx, shade) in enumerate(((-24, far), (16, far), (-10, MOSS), (28, MOSS))):
        swing = math.sin(ph + (k % 2) * math.pi) if clip == 'walk' else 0
        lift = max(0, swing) * 5
        hip = (hx, cy - 9)
        foot_x = hx + swing * 7 + (st * 6 if hx > 0 else 0)
        stand = (foot_x, lift + 3)
        dead = (hx + (14 if hx > 0 else -12) * (1 + .3 * (k % 2)), 6 + (k % 2) * 10 + 8)
        tip = mixp(stand, dead, dn)
        knee = (mix(hip[0], tip[0], .45) + 5 * (1 - dn), mix(hip[1], tip[1], .5))
        a.limb([hip, knee, tip], shade, 8)
        if dn < .6:
            foot(a, tip[0] + 2, max(0, tip[1] - 3), 8, 4, shade)
    # ridge of spines and glowing caps
    for i, sx in enumerate((-30, -20, -6, 8, 22)):
        fang(a, sx, cy + 17 - abs(sx) * .12, 8 + (i % 2) * 3, 6, math.pi / 2 + .25 - sx * .01 - dn * .6, BONE)
    caps = ((-20, 22, 11), (-1, 25, 15), (20, 19, 10))
    for (cx0, ch, cr) in caps:
        cap(a, cx0, cy + 12, cx0 + flare * 3 + math.sin(ph + cx0) * (1 + 0 * dn), cy + 12 + ch * (1 - .45 * dn) + flare * 3, cr,
            tilt=-.15 + st * .3 - w * .25, wilt=sm(dn * 1.2), pulse=pulse, spots=2)
    # body: barrel with darker belly and pale patches
    squash = 1 - .3 * dn
    a.ball(-2, cy, 36, 23 * squash, MOSS)
    a.ellipse(-4, cy - 12 * squash, 26, 6 * squash, MOSS[1])
    for px, py, pr in ((-18, 8, 5), (8, 11, 4), (-4, -5, 4)):
        a.ellipse(px, cy + py * squash, pr, pr * .7, MOSS[3])
    # tail stub with a tiny cap
    a.limb([(-34, cy + 2), (-44, cy + 8 - dn * 5)], MOSS, 6)
    cap(a, -44, cy + 8, -47, cy + 15 - dn * 8, 5, wilt=sm(dn), pulse=pulse, spots=1)
    # head: heavy wedge on a thick neck, bone brow, scowling slit eyes, upturned tusks and a snout
    hx = 50 + st * 15 - w * 8 - dn * 6
    hy = cy + 3 + w * 11 - st * 14 - dn * 17
    a.limb([(26, cy + 6), (mix(26, hx, .6), mix(cy + 6, hy, .6) + 1), (hx - 6, hy)], MOSS, 16)
    a.ball(hx - 3, hy + 1, 18, 14, MOSS)
    a.ball(hx + 14, hy - 3, 12, 9, [MOSS[1], MOSS[2], MOSS[3], MOSS[3], MOSS[4]])
    a.ellipse(hx + 22, hy - 1, 2.4, 1.8, OUTLINE)
    # lower jaw, a row of teeth and two tusks
    a.ball(hx + 8, hy - 9, 15, 6, [MOSS[0], MOSS[1], MOSS[1], MOSS[2], MOSS[3]])
    for tx in (4, 10, 16):
        fang(a, hx + tx, hy - 5.5, 3.5, 2.6, math.pi / 2, BONE)
    for dx, ln in ((3, 15), (13, 11)):
        fang(a, hx + dx, hy - 8, ln, 6, 1.2 - st * .6 + w * .3 + dn * .5, BONE)
    # bone brow ridge over the eyes
    plate(a, [(hx - 10, hy + 11), (hx + 11, hy + 8), (hx + 12, hy + 12), (hx - 4, hy + 15)], BONE, .8)
    for ex, ey, ew, eh, sd in ((hx + 6, hy + 3, 4.4, 3.2, 1), (hx - 7, hy + 4, 3.2, 2.5, -1)):
        slit(a, ex, ey, ew, eh, GOLD, MOSS[1], sd, shut=(clip == 'die' and n >= 2) or (clip == 'hurt' and n == 1), slant=.5)
    # ear leaf frills
    a.poly([(hx - 12, hy + 8), (hx - 25, hy + 14 - dn * 6), (hx - 17, hy + 1)], MOSS[3], outline=MOSS[0])
    # spore cloud
    if st > .25 or (clip == 'die' and n in (3, 4, 5, 6)):
        for i in range(6):
            s_x = hx + 6 + i * 6 * (1 if st > .25 else 0) + math.sin(n + i) * 4
            s_y = cy + 20 + (i % 3) * 7 + st * 6 - dn * 10
            dust(a, s_x if st > .25 else -20 + i * 8, s_y if st > .25 else cy + 28 + i * 3 + n, 2 + (i % 3), SPORE if i % 2 else GOLD)
    return a


def wing(a, rx, ry, side, theta, L, Wd, ramp, eye=None, tatter=1.):
    """A tattered moth wing: shaded jagged plate hinged at (rx, ry); theta is degrees above horizontal, outward."""
    th = math.radians(theta)
    base = [(0, 0), (.22 * L, .5 * Wd), (.55 * L, .62 * Wd), (.86 * L, .36 * Wd), (L, .05 * Wd),
            (.9 * L, -.18 * Wd * tatter), (.8 * L, -.1 * Wd), (.74 * L, -.5 * Wd * tatter), (.6 * L, -.3 * Wd),
            (.5 * L, -.72 * Wd * tatter), (.36 * L, -.4 * Wd), (.24 * L, -.7 * Wd * tatter), (.1 * L, -.3 * Wd)]
    pts = []
    for u, v in base:
        x, y = rot(u, v, th)
        pts.append((rx + side * x, ry + y))
    plate(a, pts, ramp, .84)
    for u, v in ((.55, .62), (.8, .3), (.45, -.1), (.35, -.55)):
        x, y = rot(u * L, v * Wd, th)
        a.line([(rx, ry), (rx + side * x, ry + y)], ramp[0], 1)
    if eye:
        x, y = rot(.5 * L, .12 * Wd, th)
        slit(a, rx + side * x, ry + y, 4.8, 3.6, eye, ramp[1], side, slant=.5)


def silkwing(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    dx = st * 22 - w * 6 + recoil
    a = Painter('silkwing', dx)
    by = mix(84 + bob * 1.2 + w * 8 - st * 7, 18, sm(dn) ** 1.3)
    flap = math.sin(ph * (2.0 if clip == 'walk' else 1.1))
    up = 38 + 26 * flap if clip in ('idle', 'walk') else 38
    if clip == 'attack':
        up = mix(mix(38, 82, w), -34, st)
    if clip == 'hurt':
        up = [70, 20, 52, 40][n]
    low = up - 38
    if clip == 'die':
        up = mix(mix(40, 98, min(1, dn * 2.5)), -22, sm(max(0, dn - .45) * 1.8))
        low = up - 30 * (1 - dn)
    shrink = 1 - .3 * dn
    for sd in (-1, 1):
        wing(a, sd * 6, by - 2, sd, low, 40 * shrink, 22, AZURE, tatter=1 - dn * .5)
    # legs, abdomen
    for sd in (-1, 1):
        a.limb([(sd * 5, by - 8), (sd * 13 - sd * dn * 6, by - 16 + dn * 5), (sd * 9 - sd * dn * 4, by - 29 + dn * 17)], BONE, 4)
    curl = dn * 1.2 + w * .2
    prev = (0, by - 12)
    for i in range(5):
        ax_ = prev[0] + math.sin(curl * (i + 1)) * 3 + math.sin(ph + i) * (.6 if clip != 'die' else 0)
        ay_ = prev[1] - math.cos(curl * (i + 1) * .9) * 7.5
        r_ = 9.5 - i * 1.4
        a.ball(ax_, ay_, r_, 6.2, PLATE if i % 2 else BONE)
        prev = (ax_, ay_)
    # thorax with a pale ruff and the skull mark
    a.ball(0, by, 14, 18, FUR)
    for sd in (-1, 1):
        a.poly([(sd * 6, by + 14), (sd * 15, by + 12), (sd * 9, by + 22)], FUR[3], outline=FUR[0])
    a.ellipse(0, by + 3, 7, 7.4, BONE[0])
    a.ellipse(0, by + 3.4, 6, 6.4, BONE[4])
    a.poly([(-3.5, by - 3), (3.5, by - 3), (2.6, by - 7), (-2.6, by - 7)], BONE[4], outline=BONE[0])
    for sx in (-2.6, 2.6):
        a.ellipse(sx, by + 4.4, 2, 2.4, OUTLINE)
    a.poly([(0, by + 1.2), (-1.2, by - .8), (1.2, by - .8)], OUTLINE)
    for tx in (-1.6, 0, 1.6):
        a.line([(tx, by - 4), (tx, by - 6.4)], BONE[0], 1)
    # head with red slit eyes, mandibles and feathered antennae
    hy = by + 24 - dn * 2
    a.ball(0, hy, 11, 9, PLATE)
    for sd in (-1, 1):
        a.poly([(sd * 8, hy + 5), (sd * 14, hy + 8), (sd * 11, hy - 3)], PLATE[3], outline=PLATE[0])
        slit(a, sd * 5.2, hy + 1.5, 4, 3, CORAL, PLATE[1], sd, shut=(clip == 'die' and n >= 2) or (clip == 'hurt' and n == 1), slant=.6)
        fang(a, sd * 3.4, hy - 6, 10 + st * 3 + w * 0, 4.6, -math.pi / 2 - sd * (.3 + st * .3 + w * .1), BONE)
        ant = bez((sd * 5, hy + 7), (sd * 10, hy + 22 - dn * 8 + w * 4), (sd * 24 + sd * dn * 4, hy + 24 - dn * 14 + w * 4), 7)
        a.line(ant, PLATE[0], 4)
        a.line(ant, PLATE[3], 2)
        for k in range(1, 6):
            px, py = ant[k]
            a.line([(px, py), (px + sd * 5, py - 4)], PLATE[3], 2)
            a.line([(px, py), (px + sd * 6, py + 3)], PLATE[3], 2)
    # upper wings: tattered blades with a glaring false eye each
    for sd in (-1, 1):
        wing(a, sd * 8, by + 8, sd, up, 64 * shrink, 34, AZURE, eye=CRIMSON if dn < .5 else None, tatter=1 - dn * .5)
    if st > .3:
        for sd in (-1, 1):
            a.line(bez((sd * 28, by + 30), (sd * 56, by + 10 - st * 12), (sd * 66, by - 20), 7), BONE[4], 3)
        for i in range(6):
            dust(a, -30 + i * 12, by - 28 - (i % 3) * 8 - st * 4, 2.2 + (i % 2), AZURE if i % 2 else PEARL)
    if clip == 'die' and 2 <= n <= 6:
        for i in range(5):
            dust(a, -22 + i * 11 + math.sin(n + i) * 3, by - 20 - i * 3 - n * 2, 2 + (i % 2), PEARL)
    return a


def claw(a, x, y, spread, length, ang, ramp=BONE):
    for k in (-1, 0, 1):
        fang(a, x, y, length - abs(k) * 2, 4.4, ang + k * spread, ramp)


def log(a, x, y, rx, ry, ang=0., end=True):
    """A broken bark log: shaded cylinder with pale sawn ends."""
    a.ball(x, y, rx, ry, BARK, ang)
    if end:
        for sg in (-1, 1):
            ex, ey = x + math.cos(ang) * rx * sg * .92, y + math.sin(ang) * rx * sg * .92
            a.ellipse(ex, ey, ry * .55, ry * .8, BONE[0])
            a.ellipse(ex, ey, ry * .38, ry * .6, BONE[3])


def rootlurker(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('rootlurker', recoil + st * 8 - w * 4)
    far = [BARK[0], BARK[0], BARK[1], BARK[2], BARK[3]]
    hunch = 1 - w * .7 + st * .35
    ty = mix(52 + bob * .6 + w * 6 - st * 4, 20, sm(dn * 1.3))
    tx = mix(-4 + st * 8, -10, dn)
    # legs: thick bark limbs with root-claw feet; they buckle and drop out on death
    for k, (hx, shade) in enumerate(((-10, far), (8, BARK))):
        swing = math.sin(ph + k * math.pi) if clip == 'walk' else 0
        lift = max(0, swing) * 5
        hip = (hx + tx * .3, ty - 12)
        fx = hx + swing * 8 + (st * 8 if hx > 0 else 0)
        tip = mixp((fx, 2 + lift), (hx - 8 + k * 24, 4), dn)
        knee = (mix(hip[0], tip[0], .5) + 7 * (1 - dn), mix(hip[1], tip[1], .55))
        a.limb([hip, knee, tip], shade, 11)
        gy = max(0., tip[1] - 2)
        a.poly([(tip[0] - 9, gy), (tip[0] + 13, gy), (tip[0] + 10, gy + 5), (tip[0] - 7, gy + 5)], shade[2], outline=shade[0])
        for cdx, ca in ((-5, 2.5), (1, 1.7), (7, .9)):
            fang(a, tip[0] + cdx * .6, tip[1] + 3, 8, 4.4, ca * .45 - .2, shade)
    # far arm, then body, head, near arm
    def arm(sd, shade):
        sh = (tx + 6 + sd * 2, ty + 12)
        rest = (30 + sd * 5, 22 + (3 if sd else 0) + (math.sin(ph) * 3 if clip == 'idle' else 0))
        hand = mixp(rest, (14 + sd * 6, 104 - st * 20), w)
        hand = mixp(hand, (46 + sd * 6, 8), st)
        if clip == 'walk':
            hand = (hand[0] + math.sin(ph + sd * 2) * 8, hand[1] + 3)
        if dn:
            hand = mixp(hand, (50 + sd * 22, 6), sm(min(1, dn * 2.5)))
        elbow, hand = arm_ik(sh, hand, 30, 30, bend=-1 if sd == 0 else 1)
        return sh, elbow, hand, shade
    far_arm = arm(0, far)
    if dn < .3:
        sh, el, ha, sdc = far_arm
        a.limb([sh, el, ha], sdc, 9)
        claw(a, ha[0], ha[1] - 1, .5, 13, -1.2 + w * .8 - st * .3, sdc)
    # torso: hunched trunk with moss and thorn spikes along the spine
    split = sm(max(0, dn - .15) * 1.4)
    a.ball(tx - split * 8, ty, 21, 25 * (1 - .25 * dn), BARK, -.25 * hunch)
    a.ball(tx - 2 - split * 8, ty - 10, 15, 12 * (1 - .2 * dn), [BARK[0], BARK[1], BARK[2], BARK[2], BARK[3]])
    for i, (sx, sy) in enumerate(((-18, 14), (-14, 4), (-18, -6), (-8, 20))):
        fang(a, tx + sx - split * 8, ty + sy, 11 + (i % 2) * 3, 6, math.pi - .35 + i * .35 - dn * .5, BONE)
    for mx, my, mr in ((-6, 10, 6), (6, -8, 5), (-12, -10, 5)):
        a.ball(tx + mx - split * 8, ty + my, mr, mr * .7, MOSS)
    if split > .2:
        a.line([(tx + 1, ty + 22), (tx - 3, ty + 8), (tx + 3, ty - 4), (tx - 2, ty - 20)], BONE[3], 3)
    # near arm
    sh, el, ha, sdc = arm(1, BARK)
    if dn < .55:
        a.limb([sh, el, ha], BARK, 10)
        claw(a, ha[0], ha[1] - 1, .5, 14, -1.2 + w * .8 - st * .3, BARK)
    # head: low and forward, knothole face with burning slit eyes and a jagged mouth
    hx = tx + 22 + st * 6 - w * 2 + dn * 6
    hy = ty + 10 - hunch * 0 + w * 7 - st * 8 - dn * 26
    if dn > .6:
        hx = mix(hx, 36, (dn - .6) * 2.5)
    a.ball(hx, hy, 15, 14, BARK)
    a.ball(hx + 5, hy - 2, 10, 9, VOID)
    # antler branches with leaves
    for sd, (bx, by_) in enumerate(((-6, 12), (6, 13))):
        pts = bez((hx + bx, hy + by_), (hx + bx - 6 + sd * 10, hy + by_ + 16 - dn * 8), (hx + bx - 12 + sd * 22, hy + by_ + 26 - dn * 12), 6)
        a.line(pts, BARK[0], 6)
        a.line(pts, BARK[3], 4)
        tipx, tipy = pts[-1]
        a.line([(pts[3][0], pts[3][1]), (pts[3][0] + 9, pts[3][1] + 8 - dn * 4)], BARK[2], 4)
        a.ball(tipx, tipy, 4, 3, MOSS)
    plate(a, [(hx - 8, hy + 8), (hx + 14, hy + 3), (hx + 15, hy + 8), (hx - 2, hy + 14)], BARK, .8)
    shut = (clip == 'die' and n >= 3) or (clip == 'hurt' and n == 1)
    slit(a, hx + 10, hy + 1, 4.6, 3.2, AMBER, VOID[1], 1, shut=shut, slant=.55)
    slit(a, hx + 1, hy + 2, 3.4, 2.6, AMBER, VOID[1], -1, shut=shut, slant=.55)
    # mouth: a crooked row of splinter teeth
    jaw = w * 3 + st * 5 + 2
    a.ellipse(hx + 9, hy - 7, 8, 3 + jaw * .6, OUTLINE)
    for i in range(5):
        fang(a, hx + 3 + i * 3.3, hy - 4.5, 4 + (i % 2) * 2, 2.8, math.pi * 1.5 + (i - 2) * .12, BONE)
    for i in range(4):
        fang(a, hx + 4.5 + i * 3.5, hy - 9.5 - jaw * .5, 3.5 + (i % 2) * 2, 2.8, math.pi / 2 + (i - 1.5) * .12, BONE)
    # strike: bark spikes burst from the ground in front of the claws
    if st > .15:
        for i in range(5):
            fang(a, 36 + i * 9, 0, 10 + st * 20 - abs(i - 2) * 3, 8, math.pi / 2 + .12 * (i - 2), BARK)
    # death: broken limbs and logs on the ground
    if dn > .2:
        g = sm(min(1, (dn - .2) * 1.5))
        log(a, mix(-6, -20, g), mix(ty - 22, 8, g), 17, 8, mix(-.4, .08, g))
        log(a, mix(10, 12, g), mix(ty - 8, 9, g), 15, 7.5, mix(.5, -.15, g))
        log(a, 48 + g * 6, 6, 15, 6.4, .1)
        log(a, -34 + g * 4, 6, 13, 6, -.05)
        a.ball(-10, 14 * g + 6, 6, 4, MOSS)
        if dn > .5:
            for i in range(4):
                fang(a, -30 + i * 20, 13, 7, 3.5, math.pi * (.35 + i * .13), BONE)
    return a


CLOAK = [VOID[1], SLATE[0], SLATE[1], SLATE[2], SLATE[3]]


def lantern(a, x, y, flame, fade=1.):
    """A hooked iron lantern: chain, frame, glass and a ghostfire flame."""
    a.line([(x, y + 14), (x, y + 2)], PLATE[1], 3)
    a.poly([(x - 8, y + 2), (x + 8, y + 2), (x + 6, y - 20), (x - 6, y - 20)], PLATE[1], outline=OUTLINE)
    a.ball(x, y - 9, 5.5 * flame, 7.5 * flame, GHOST if fade > .4 else [GHOST[0]] * 5)
    for sx in (-8, 8):
        a.line([(x + sx, y + 2), (x + sx * .75, y - 20)], PLATE[3], 2)
    a.poly([(x - 9, y - 19), (x + 9, y - 19), (x, y - 25)], PLATE[2], outline=OUTLINE)
    a.ellipse(x, y - 21, 10, 2.2, PLATE[0])


def lanternwraith(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('lanternwraith', recoil + st * 6 - w * 4)
    sway = math.sin(ph) * (1 - dn)
    y0 = 40 + bob * 1.5 + w * 3 - st * 3
    lean = -w * 6 + st * 9 + sway * 2
    rags = sm(dn * 1.2)
    # cloak body: tall hooded robe flaring to a ragged hem of wisps; it unravels upward on death
    top = 80 - rags * 24
    left = [(-14 + lean * .6, top), (-27 + lean * .3, y0 + 40 * (1 - rags * .4)), (-33, y0 + 8 + 10 * rags)]
    right = [(26 + sway * 2, y0 + 8 + 12 * rags), (24, y0 + 40 * (1 - rags * .4)), (13 + lean * .6, top)]
    hem = []
    for i in range(7):
        t = i / 6
        hx_ = mix(-33, 26, t) + math.sin(ph + i * 1.7) * 3 * (1 - dn)
        hy_ = y0 - 2 - ((i * 5) % 11) - 3 * math.sin(ph + i) * (1 - dn) + rags * (16 + 5 * (i % 3))
        hem.append((hx_ + (lean * -.2), hy_))
        if i < 6:
            hem.append((mix(-33, 26, (i + .5) / 6), y0 + 14 + (i % 2) * 5 - rags * 8))
    outline = left + hem[::-1] + right
    plate(a, outline, CLOAK, .86)
    # long wisps rising off the hem on death
    for i in range(6):
        if dn > .12:
            bx = -28 + i * 11
            h_ = rags * (36 + 14 * (i % 3))
            pts = bez((bx, y0 + 4), (bx + 8 * math.sin(i + n), y0 + 4 + h_ * .5), (bx + 12 * math.sin(i * 2 + n * .7), y0 + 4 + h_), 6)
            taper(a, pts, CLOAK, 6 - rags * 2, 2)
    # hood and the void face
    hood_h = 28 * (1 - rags * .85)
    htop = (4 + lean * 1.1, top + hood_h + 4)
    plate(a, [(-17 + lean * .5, top - 4), (-16 + lean * .5, top + 14 * (1 - rags)), htop, (16 + lean * .6, top + 14 * (1 - rags)), (16 + lean * .6, top - 4)], CLOAK, .8)
    fx = 6 + lean * .8
    fy = top + 10 - rags * 4
    a.ball(fx, fy, 11, 14 * (1 - rags * .4), VOID)
    shut = (clip == 'die' and n >= 2) or (clip == 'hurt' and n == 1)
    slit(a, fx + 5, fy + 3, 4.6, 2.4, GHOST, VOID[2], 1, shut=shut, slant=1.1, pupil=False)
    slit(a, fx - 3, fy + 4, 3.6, 2, GHOST, VOID[2], -1, shut=shut, slant=1.1, pupil=False)
    if not shut:
        for i in range(5):
            fang(a, fx - 5 + i * 3.1, fy - 6.2, 3.8 + (i % 2) * 1.6, 2.4, math.pi / 2 if i % 2 else -math.pi / 2, BONE)
        a.line([(fx - 6, fy - 6), (fx + 8, fy - 6.5)], BONE[0], 1)
    # arm and lantern
    sh = (12 + lean, top - 12)
    rest = (34, top - 30 + sway * 2)
    raised = (22 + lean, top + 36)
    thrown = (52, top - 6)
    hand = mixp(mixp(rest, raised, w), thrown, st)
    if dn:
        hand = mixp(hand, (30, 14), sm(min(1, dn * 1.7)))
    el, hand = arm_ik(sh, hand, 24, 24, bend=-1)
    if dn < .75:
        a.limb([sh, el, hand], BONE, 6)
        claw(a, hand[0] + 2, hand[1], .55, 8, 0.2, BONE)
    ly = hand[1] - 10 if dn < .5 else mix(hand[1] - 10, 22, sm((dn - .5) * 2))
    lx = hand[0] + 2
    lantern(a, lx, ly + 20 - dn * 6, 1 + w * .5 + st * .25 - dn * .6, fade=1 - dn)
    if dn < .85:
        # the far, empty hand: three long claws
        fx2 = -26 + lean * .3
        a.limb([(-20 + lean * .4, top - 14), (-30, top - 34), (fx2 - 2, top - 46 + sway * 3)], BONE[:1] + BONE[1:], 6)
        claw(a, fx2 - 2, top - 47 + sway * 3, .5, 9, -1.55, BONE)
    # ghostfire orb on the throw
    if st > .1:
        ox = mix(60, 94, st)
        a.ball(ox, top - 6, 9, 9, GHOST)
        for i in range(4):
            a.ball(ox - 14 - i * 8, top - 6 + (i % 2) * 3, 5.5 - i, 4.5 - i * .6, GHOST)
    if w > .5:
        a.ball(lx, ly + 22, 8 * w, 9 * w, GHOST)
    return a


def mireheart(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('mireheart', recoil + st * 6 - w * 5)
    beat = 1 + .09 * math.sin(ph * 2.2) * (1 - dn) + w * .25 + st * .12
    cy = mix(38 + bob * .7 - w * 7, 20, sm(dn * 1.2))
    sag = dn
    far = [MOSS[0], MOSS[0], MOSS[1], MOSS[2], MOSS[3]]
    # hind legs: fat folded thighs with webbed feet
    for k, (lx, shade) in enumerate(((-30, far), (-12, MOSS))):
        lift = max(0, math.sin(ph + k * math.pi)) * 5 if clip == 'walk' else 0
        a.ball(lx, cy - 8 - sag * 4, 16, 14 * (1 - .3 * sag), shade)
        fx = mix(lx + 12, lx + 20 + k * 6, sag)
        a.ball(fx, 5 + lift * .5 - sag * 0, 14, 5, shade)
        for t in range(3):
            fang(a, fx + 8 + t * 2, 4 + lift * .3, 6, 4, -.3 + t * .35 + .1, shade)
    # far arm
    sh = (14, cy + 10)
    for sd, shade in ((0, far), (1, MOSS)):
        reach = mixp((32 + sd * 8, 6), (40 + sd * 6, cy - 4), w * .6)
        reach = mixp(reach, (50 + sd * 8, 4), st * .5)
        reach = mixp(reach, (30 + sd * 24, 10), sm(dn))
        el = ((sh[0] + reach[0]) / 2 + 6, (sh[1] + reach[1]) / 2 - 2)
        if sd == 0 or dn < .8:
            a.limb([(sh[0] - 2 * sd, sh[1]), el, reach], shade, 11)
            for t in range(3):
                a.ball(reach[0] + 3 + t * 4, reach[1] - 1, 4.2, 3.2, shade)
    # body: huge squat bog toad with warts and a pale belly
    a.ball(-2, cy, 40, 32 * (1 - .22 * sag), MOSS)
    a.ball(8, cy - 12, 24, 14 * (1 - .22 * sag), [MOSS[1], MOSS[2], MOSS[3], MOSS[3], MOSS[4]])
    for wx, wy, wr in ((-26, 20, 5), (-14, 26, 4), (-34, 4, 4), (-20, 6, 3.5), (6, 28, 4)):
        a.ball(wx, cy + wy * (1 - .2 * sag), wr, wr * .8, [MOSS[1], MOSS[2], MOSS[3], MOSS[3], MOSS[4]])
    # exposed pulsing heart in a cage of thorny rib roots
    hx0, hy0 = 10, cy + 2
    heart_r = 14 * beat * (1 - .3 * sag)
    a.ellipse(hx0, hy0, heart_r + 7, heart_r + 8, BARK[0])
    heart = HEART if dn < .5 else [HEART[0], HEART[0], HEART[0], HEART[1], HEART[1]]
    a.ball(hx0, hy0, heart_r, heart_r * 1.05, heart)
    a.ball(hx0 - 5, hy0 + 5, heart_r * .35, heart_r * .3, [HEART[2], HEART[3], HEART[4], HEART[4], WHITE] if dn < .5 else heart)
    for i in range(6):
        ang = math.pi / 2 + (i - 2.5) * .55
        bx_, by_ = hx0 + math.cos(ang) * (heart_r + 7), hy0 + math.sin(ang) * (heart_r + 8)
        a.limb([(bx_ + math.cos(ang) * 4, by_ + math.sin(ang) * 4), (bx_ - math.cos(ang) * 8 * .6, by_ - math.sin(ang) * 8 * .6)], BARK, 4)
        fang(a, bx_, by_, 9, 4.4, ang + (.4 if i % 2 else -.4), BONE)
    # head: wide flat toad head, eye bulbs under heavy lids, huge fanged mouth
    jawo = w * 7 + st * 10 + dn * 3
    hx, hy = 34 + st * 8 - w * 3, cy + 26 + w * 5 - st * 6 - sag * 18
    a.ball(hx, hy, 26, 15, MOSS)
    a.ball(hx + 6, hy - 11 - jawo * .5, 24, 7, [MOSS[0], MOSS[1], MOSS[1], MOSS[2], MOSS[3]])
    a.ellipse(hx + 10, hy - 5 - jawo * .3, 22, 3 + jawo * .5, OUTLINE)
    for i in range(7):
        fang(a, hx - 8 + i * 5.6, hy - 5.5 - jawo * .15, 5 + (i % 2) * 2.4, 3.4, math.pi * 1.5 + (i - 3) * .09, BONE)
        fang(a, hx - 6 + i * 5.6, hy - 10.5 - jawo * .45, 4.6 + (i % 2) * 2.2, 3.2, math.pi / 2 + (i - 3) * .09, BONE)
    tl = [0, 0, 10, 38, 70, 52, 24, 0][n] if clip == 'attack' else 0
    tl = max(tl, 12 if dn > .4 else 0) if clip == 'die' else tl
    if tl:
        mx_, my_ = hx + 22, hy - 7 - jawo * .3
        tip = (mx_ + tl, my_ - tl * .12 * (1 - sag) - sag * 8)
        pts = [mixp((mx_, my_), tip, i / 6) for i in range(7)]
        pts = [(x, y + math.sin(i * .9) * 2.5 * (tl / 60)) for i, (x, y) in enumerate(pts)]
        taper(a, pts, HEART, 7, 8)
        if tl > 30:
            a.ball(tip[0] + 2, tip[1], 8, 7, HEART)
            for t in (-1, 1):
                fang(a, tip[0] + 4, tip[1], 8, 4, t * .8, BONE)
    # eyes on bulging lids above the brow
    for ex, ey, ew, eh, sd in ((hx + 12, hy + 12, 6.4, 4.4, 1), (hx - 6, hy + 14, 5, 3.6, -1)):
        a.ball(ex, ey - 2, ew + 4, eh + 5, MOSS)
        slit(a, ex, ey, ew, eh, CORAL, MOSS[0], sd, shut=(clip == 'die' and n >= 3) or (clip == 'hurt' and n == 1), slant=.7)
    # thorny vines draped on the back
    for i in range(4):
        fang(a, -30 + i * 14, cy + 28 - i * 1.5 - sag * 12, 12 + (i % 2) * 5, 7, math.pi / 2 + .25 - i * .12 - sag * .4, BARK)
    if dn > .55:
        for i in range(4):
            a.ball(-24 + i * 14 + sag * 3, 5 + (i % 2) * 4, 6, 3.2, MOSS)
    return a


def silverwidow(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    flip = sm(max(0., dn - .3) / .7)
    lunge = st * 30 - w * 6 + recoil
    a = Painter('silverwidow', lunge * .7)
    rear = w * 18 - st * 4                       # the front of the body rears up on the hind legs
    cy = mix(38 + bob * .7, 15, sm(dn * 1.3))
    far = [WEBGREY[0], WEBGREY[0], WEBGREY[1], WEBGREY[2], WEBGREY[3]]
    near = [WEBGREY[0], WEBGREY[1], WEBGREY[2], WEBGREY[3], WEBGREY[4]]
    coxa = [-30, -10, 14, 32]
    feet = [-66, -38, 30, 62]
    for side, shade, off in ((0, far, 7), (1, near, 0)):
        for k in range(4):
            swing = math.sin(ph + (k + side) * math.pi / 2 * 2) if clip == 'walk' else 0
            lift = max(0, swing) * 9
            front = k >= 2
            hip = (coxa[k] + off * .5, cy + 4 + (rear * .6 if front else 0))
            fx = feet[k] + off + swing * 6 + (st * 10 if front else 0)
            foot_ = (fx, lift + 1)
            if front and clip == 'attack':
                foot_ = mixp(foot_, (mix(fx, 36 + k * 10, .5) + st * 20, 54 + w * 38 + (k - 2) * 8), max(w, st) * .9)
            curl = (hip[0] * .3 + (k - 1.5) * 5 + off, cy + 30 + 8 * (k % 2) + flip * 6)
            foot_ = mixp(foot_, curl, flip)
            knee = (mix(hip[0], foot_[0], .38), max(cy + 36 + (k % 2) * 5 + 8 * w * front, foot_[1] + 30))
            knee = (knee[0], mix(knee[1], cy + 40 + flip * 8, flip))
            a.limb([hip, knee, foot_], shade, 7)
            a.ball(knee[0], knee[1], 4.2, 4.2, WEBGREY if side else far)
            a.ellipse(foot_[0], foot_[1] + 1, 3, 1.8, WEBGREY[4])
            fang(a, foot_[0], foot_[1] + 1, 7, 4, -math.pi / 2 + (.4 if front else -.4), BONE)
    # abdomen with the silver crescent mark (the underside shows once it has flipped)
    abx, aby = -34 - st * 4, cy + 10 - rear * .3 - flip * 0
    a.ball(abx, aby, 29, 25 * (1 - .15 * dn), WEBGREY)
    if flip < .55:
        a.ellipse(abx + 2, aby + 6, 12, 14, PEARL[3])
        a.ellipse(abx + 6, aby + 6, 11, 13, WEBGREY[2])
        a.ellipse(abx + 3, aby + 6, 8.4, 9.6, WEBGREY[2])
        a.ellipse(abx - 4, aby + 5, 6, 10, PEARL[4])
        a.ellipse(abx + 8, aby + 5, 10, 14, WEBGREY[2])
    else:
        a.ball(abx, aby - 4, 20, 12, BONE)
        a.line([(abx - 14, aby - 4), (abx + 14, aby - 4)], BONE[0], 2)
    for i in range(7):
        ang = .5 + i * .38
        fang(a, abx + math.cos(ang) * 26, aby + math.sin(ang) * 22, 6, 3.2, ang, WEBGREY[3:] + [WEBGREY[4]] * 2 if False else PLATE)
    # cephalothorax and head
    cx_, cy_ = 14 + st * 4, cy + 8 + rear * .5
    a.ball(cx_, cy_, 22, 17, WEBGREY)
    a.ball(cx_ + 20, cy_ + 2, 13, 11, WEBGREY)
    a.poly([(cx_ + 6, cy_ + 14), (cx_ + 30, cy_ + 12), (cx_ + 32, cy_ + 17), (cx_ + 10, cy_ + 20)], PLATE[1], outline=OUTLINE)
    # six unequal burning eyes
    shut = (clip == 'die' and n >= 2) or (clip == 'hurt' and n == 1)
    slit(a, cx_ + 28, cy_ + 5, 4.8, 3.4, ORCHID, WEBGREY[0], 1, shut=shut, slant=.7)
    slit(a, cx_ + 18, cy_ + 9, 3.8, 2.8, ORCHID, WEBGREY[0], -1, shut=shut, slant=.7)
    for ex, ey, er in ((cx_ + 24, cy_ + 12, 2.2), (cx_ + 13, cy_ + 13, 1.8), (cx_ + 32, cy_ + 11, 1.8), (cx_ + 8, cy_ + 9, 1.5)):
        if not shut:
            a.ellipse(ex, ey, er + 1, er + 1, OUTLINE)
            a.ellipse(ex, ey, er, er, ORCHID[3])
            a.ellipse(ex - .4, ey + .4, er * .5, er * .5, ORCHID[4])
    # fangs with venom, pedipalps
    gape = w * 4 + st * 5
    for dx, sd in ((cx_ + 26, 1), (cx_ + 33, 1)):
        a.limb([(dx, cy_ - 6), (dx + 2, cy_ - 9 - gape * .5)], PLATE, 6)
        fang(a, dx + 2, cy_ - 9 - gape * .5, 14 + st * 3, 6, -math.pi / 2 + (.25 - st * .15) * (1 if dx > cx_ + 28 else -1) - gape * .03, BONE)
    if clip != 'die' or n < 3:
        a.ball(cx_ + 33, cy_ - 22 - gape - ph * 0 + (n % 3), 1.8, 2.4, GREEN)
    a.limb([(cx_ + 16, cy_ - 8), (cx_ + 30, cy_ - 20 - gape * .3)], WEBGREY, 5)
    # silk spray on the strike
    if st > .2:
        for i in range(5):
            ang = -.35 + i * .2
            pts = bez((cx_ + 36, cy_ - 8), (cx_ + 36 + 36 * st * math.cos(ang), cy_ - 8 + 14 * math.sin(ang)),
                      (cx_ + 36 + 78 * st * math.cos(ang), cy_ - 8 + 36 * math.sin(ang) - 8), 6)
            a.line(pts, WEBGREY[4], 3)
            a.ball(pts[-1][0], pts[-1][1], 3, 3, PEARL)
    return a


def nightbloom(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('nightbloom', recoil + st * 4 - w * 6)
    wilt = sm(dn)
    sway = math.sin(ph) * (1 - dn)
    # root feet and a thick thorny stem that arches back and then snaps forward; on death it withers and bows
    foot_x = [-14, 12]
    for k, fx in enumerate(foot_x):
        swing = math.sin(ph + k * math.pi) * 6 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + k * math.pi)) * 4 if clip == 'walk' else 0
        for j in range(3):
            pts = bez((fx * .4, 22), (fx + swing + (j - 1) * 6, 8 + lift), (fx + swing + (j - 1) * 14, 1 + lift * .3), 5)
            taper(a, pts, BARK, 8 - j, 4)
    bend = -w * 18 + st * 24 + sway * 3 + wilt * 38
    sag = wilt * 46
    stem = bez((0, 20), (-6 + bend * .2, 54 - sag * .3), (6 + bend, 92 - sag), 8)
    taper(a, stem, MOSS, 12, 9)
    for i in range(1, 7, 2):
        px, py = stem[i]
        fang(a, px + 4, py, 11, 6, .5 - wilt * .8, BONE)
        fang(a, px - 4, py + 6, 10, 6, math.pi - .5 + wilt * .8, BONE)
    # leaves
    for i, (lx, ly, ang) in enumerate(((-6, 38, 2.5), (8, 52, .5))):
        px, py = stem[2 + i]
        a.poly([(px, py), (px + math.cos(ang - wilt * (.9 if i else -.9)) * 22, py + math.sin(ang) * 10 - wilt * 6),
                (px + math.cos(ang) * 8, py + math.sin(ang) * 18 - wilt * 10)], MOSS[2], outline=MOSS[0])
    # vine whips: thorny arms that lash out on the strike and hang limp when dead
    hx, hy = stem[-1]
    for sd, shade in ((-1, [MOSS[0], MOSS[0], MOSS[1], MOSS[2], MOSS[3]]), (1, MOSS)):
        sh = stem[4]
        rest = (sh[0] + sd * 24, sh[1] - 12 - wilt * 20 + sway * 2)
        up = (sh[0] + sd * 18, sh[1] + 34)
        lash = (sh[0] + sd * 14 + 38 * (sd > 0), sh[1] - 38)
        tip = mixp(mixp(rest, up, w), lash, st)
        if dn:
            tip = mixp(tip, (sh[0] + sd * 26, 4), wilt)
        mid = ((sh[0] + tip[0]) / 2 + sd * 6, (sh[1] + tip[1]) / 2 + 10 - st * 10)
        pts = bez(sh, mid, tip, 8)
        taper(a, pts, shade, 8, 4)
        for i in range(2, 8, 2):
            fang(a, pts[i][0], pts[i][1], 7, 4, math.pi / 2 + sd * .8, BONE)
        a.ball(tip[0], tip[1], 5, 5, MOSS)
    # head: a hooded plum bloom with a thorn-lined jaw petal
    hy2 = hy + 4
    hx2 = hx + st * 8 + 4
    tilt = -.5 * w + .4 * st + wilt * 1.2
    gape = 6 + w * 12 + st * 4
    jaw = gape * (1 - wilt * .9)
    # back petals (fan behind the head)
    for i in range(5):
        ang = math.pi / 2 + (i - 2) * .55 + tilt * .5 - wilt * 1.3 * (1 if i > 2 else -1) * .4
        petal_len = 26 * (1 - wilt * .35)
        a.ball(hx2 + math.cos(ang) * 14, hy2 + 4 + math.sin(ang) * 14, 11, petal_len * .5, PLUM, ang - math.pi / 2)
    # lower jaw petals with thorn teeth
    for sd in (-1, 1):
        a.ball(hx2 + sd * 10 + 4, hy2 - 10 - jaw * .7, 12, 7, PLUM, sd * -.35)
    for i in range(6):
        fang(a, hx2 - 11 + i * 4.6 + 4, hy2 - 8 - jaw * .5, 6 + (i % 2) * 2.6, 3.4, math.pi / 2, BONE)
    # face disc: dark throat, brow petals and two lime slit eyes
    a.ball(hx2 + 4, hy2 + 2, 18, 15, PLUM, tilt * .4)
    a.ellipse(hx2 + 4, hy2 - 5 - jaw * .3, 13, 3 + jaw * .5, MAROON[0])
    for i in range(6):
        fang(a, hx2 - 8 + i * 4.6 + 4, hy2 - 3.6 - jaw * .1, 5 + (i % 2) * 2, 3.2, -math.pi / 2, BONE)
    shut = (clip == 'die' and n >= 2) or (clip == 'hurt' and n == 1)
    slit(a, hx2 + 12, hy2 + 8, 5.4, 3.4, GHOST, PLUM[0], 1, shut=shut, slant=.9)
    slit(a, hx2 - 3, hy2 + 9, 4.4, 2.8, GHOST, PLUM[0], -1, shut=shut, slant=.9)
    plate(a, [(hx2 - 10, hy2 + 14), (hx2 + 18, hy2 + 14), (hx2 + 22, hy2 + 22), (hx2 - 14, hy2 + 22)], PLUM, .8)
    # golden pollen crown
    for i in range(5):
        a.ball(hx2 - 8 + i * 6, hy2 + 24 - abs(i - 2) * 1.6 - wilt * 6, 3, 3, GOLD)
    # falling petals on death
    if dn > .25:
        for i in range(6):
            a.ball(-30 + i * 14 + math.sin(n + i) * 4, mix(hy2 - 10, 5 + (i % 2) * 5, min(1, dn * 1.3 + i * .04)), 6, 3, PLUM)
    return a


# KINDS-END

DRAW = {k: globals()[k] for k in KINDS if k in globals()}


STRICT = True
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if kind in FLYING:
        # Flying Silkwing and Lantern Wraith hover well above the ground while alive and settle onto kay at the end of death.
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
        np.savez_compressed(ROOT / f'scripts/moonspore_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/moonspore_slime_{kind}_raw.npz', **data)
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
        dest = ASSETS / f'moonspore_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 238 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    meta = json.loads(MANIFEST.read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'moonspore_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    """Measure each kind's art on a scratch canvas: pass A (anchor x 96) gives the left reach, pass B (anchor x 40) the right."""
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW]:
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


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
