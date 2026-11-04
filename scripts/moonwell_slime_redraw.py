#!/usr/bin/env python3
"""The Moonwell (zone 18 in the docs, index 17 in map.txt) redo: seven native PixelFlow sources with per-kind frames.

preview | extents | build | refresh <kinds> | export | verify

Owner direction (2026-11-04): every enemy must look UNIQUE and MEAN, with no shared round-eye-plus-blush face.
Here every kind builds its own face with its own routine (no `slit()` reuse, no blush anywhere): faceted compound
eyes (dew_moth), blind milky eyes under a bone brow (lumen_eel), two pinpoint lights inside the dark of a bell
(rootbell), a cold slit-pupil raptor eye (tideglass_heron), hollow skull sockets (hourpetal_stag), one vertical seam
eye over a stitched mouth (moonskein_weaver), and angular shard sockets over a glowing fissure (moonwell_echo).
Shaded volume (`plate`/`ball`/`taper`), props at least four pixels thick, eight distinct attack frames (wind-up,
strike, recovery) and eight distinct death frames per kind. The original cel-shaded art is kept in
/media/raid/valhallasc-data/moonwell-slime-original-20261104 (`scripts/rollback_moonwell_art.py`).

Two manifests are kept, exactly as before: `moonwell.txt` (the Echo, atlas `moonwell_echo.png`) and
`moonwell_garden.txt` (the other six, atlases `moonwell_<kind>.png`), so `field.js` needs no change.

  - dew_moth (hovers): a dew-drop mosquito-moth: a glassy teardrop abdomen hangs under a furred thorax, four swept
    blade wings with dew-beads at the tips, faceted compound eyes, a long needle proboscis and comb antennae; rears
    back, then dives and stabs with the needle in a spray of dew; dies as the abdomen bursts, the wings fold, and it
    drops into a puddle.
  - lumen_eel (hovers): a long anglerfish-eel with a hooked lure bulb on a stalk, blind milky eyes under a bone brow,
    an underslung jaw of needle teeth and a lateral row of glowing lights; coils into a tight S, then darts with the
    jaw wide and the lure flaring; dies as the lights go out and it sinks limp to the ground, jaw open.
  - rootbell: a weathered bronze bell held up on gnarled roots, a seedling on the crown, a dark mouth under the rim
    with two pinpoint lights, root-teeth and a swinging clapper tongue; rears up and slams the bell down in a clang
    ring; dies as cracks run through the bell, it topples onto its side and the seedling wilts.
  - tideglass_heron (elite): a gaunt glass-feathered heron on stilt legs with a dagger beak, a slit-pupil eye and a
    crest of shards; coils its neck, then spears forward in a spray of glass; dies by shattering into a heap of shards.
  - hourpetal_stag (elite): a lean violet stag with a skull face, hollow sockets, bared fangs, scythe antlers tipped
    with petals and an hourglass on its flank; lowers its antlers and gores forward; dies on its knees, then on its
    side as the sand runs out of the hourglass and the petals fall.
  - moonskein_weaver (elite): a tall stilt-legged puppeteer: a thread-wound spindle body, hood and porcelain mask
    with one vertical seam eye and a stitched mouth, four needle arms and a ring of orbiting beads; crosses its arms
    back, then thrusts all four needles; dies as the thread unravels and it collapses into a tangle, mask on top.
  - moonwell_echo (boss, hovers): a cracked mirror wraith: a shard-faced mask with angular hollow sockets and a
    glowing fissure grin, orbiting mirror shards and a hanging cloak of shards; draws its shards in, then hurls
    them; dies as the face splits, the shards burst outward and fall into a glittering heap.
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
    PALETTE as BASE_PALETTE, plate, blob, fang, dust, claw, curves,
    MOSS, SPORE, HEART, ORCHID, PLUM, BARK, VOID, GHOST, WEBGREY,
)
from astral_slime_redraw import (
    Painter as BasePainter, OUTLINE, WHITE, EYE_WHITE,
    BONE, PLATE, PURPLE, TEAL, GOLD, GREEN, FUR, BLUE, BROWN, OLIVE, PINK, MAROON, CORAL, PEARL, VIOLET, CRIMSON,
    AMBER, AZURE, SLATE, mix, mixp, rot, sm, bez, taper, foot, arm_ik,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/moonwell-slime'
REGISTRY = ROOT / 'scripts/moonwell_slime_sources.txt'
PREFIX = 'valhallasc_moonwell_slime_style_'
KINDS = ['dew_moth', 'lumen_eel', 'rootbell', 'tideglass_heron', 'hourpetal_stag', 'moonskein_weaver', 'moonwell_echo']
NAMES = dict(zip(KINDS, ['Dew Moth', 'Lumen Eel', 'Rootbell', 'Tideglass Heron', 'Hourpetal Stag', 'Moonskein Weaver', 'Moonwell Echo']))
# The Echo keeps its own manifest and file name (field.js loads `assets/moonwell_echo.png` by name); the others share one.
MANIFESTS = {'moonwell_echo': ASSETS / 'moonwell.txt'}
GARDEN = ASSETS / 'moonwell_garden.txt'
for _k in KINDS:
    MANIFESTS.setdefault(_k, GARDEN)
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    dew_moth=(100, 90, 39, 84),
    lumen_eel=(128, 77, 55, 71),
    rootbell=(103, 63, 41, 57),
    tideglass_heron=(138, 83, 48, 77),
    hourpetal_stag=(147, 100, 43, 94),
    moonskein_weaver=(87, 83, 35, 77),
    moonwell_echo=(168, 115, 74, 109),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('dew_moth', 'lumen_eel', 'moonwell_echo')
PALETTE = BASE_PALETTE[:] + [
    '#0a3550', '#1a7494', '#48bcd6', '#98e6f2', '#e4ffff',   # DEW (glassy water: moth abdomen, puddle)
    '#241c3a', '#483c70', '#7c70ae', '#b4aad6', '#e4def6',   # MOTH (furred silver-lilac)
    '#04212b', '#0c4654', '#188892', '#3cbcb2', '#98f0d6',   # EEL (deep teal skin)
    '#261608', '#5c3c16', '#a06e2a', '#d4a64e', '#f4de8c',   # BRONZE (the bell)
    '#14304a', '#3a7c98', '#80c6d0', '#c2eeec', '#f2ffff',   # GLASS (heron feathers)
    '#1a1230', '#3a2a60', '#6650a0', '#9886cc', '#cdc0ee',   # STAG (violet hide)
    '#070b1e', '#1a2850', '#425f98', '#8eb6d6', '#e0f4ff',   # MIRROR (the Echo)
    '#1a182c', '#423e5c', '#7a7698', '#b8b4d2', '#eeecf8',   # THREAD (the weaver's cloth and thread)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
_n = len(BASE_PALETTE)
DEW, MOTH, EEL, BRONZE, GLASS, STAG, MIRROR, THREAD = [list(range(_n + 5 * i, _n + 5 * i + 5)) for i in range(8)]


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Art scale per kind (1.0 = the coordinates written in the draw functions); judged on an in-game screenshot.
SCALE = dict(dew_moth=.62, lumen_eel=.64, rootbell=.56, tideglass_heron=.64, hourpetal_stag=.72, moonskein_weaver=.56, moonwell_echo=.74)


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


def rotp(pts, ang, ox=0., oy=0.):
    c, s = math.cos(ang), math.sin(ang)
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in pts]


def polar(x, y, ang, r):
    return x + math.cos(ang) * r, y + math.sin(ang) * r


def blade(a, x, y, ang, length, width, ramp, tatter=0., k=.74):
    """A pointed leaf/blade hinged at (x, y) and pointing along ang; the trailing edge may be ragged."""
    prof = [(0, .35), (.28, 1.), (.55, .92), (.8, .55), (1., 0.)]
    left, right = [], []
    for i, (t, hw) in enumerate(prof):
        px, py = polar(x, y, ang, length * t)
        nx, ny = -math.sin(ang), math.cos(ang)
        j = 1 + tatter * (.3 if i % 2 else -.1)
        left.append((px + nx * width * hw * .5, py + ny * width * hw * .5))
        right.append((px - nx * width * hw * .5 * j, py - ny * width * hw * .5 * j))
    plate(a, left + right[::-1][1:], ramp, k)


def shard(a, x, y, length, width, ang, ramp):
    """A kite-shaped glass shard centred near (x, y), pointing along ang."""
    nx, ny = -math.sin(ang), math.cos(ang)
    tip = polar(x, y, ang, length * .62)
    tail = polar(x, y, ang, -length * .38)
    sh = polar(x, y, ang, length * .12)
    plate(a, [tip, (sh[0] + nx * width / 2, sh[1] + ny * width / 2), tail, (sh[0] - nx * width / 2, sh[1] - ny * width / 2)], ramp, .7)


def dying(clip, n, first=2):
    return (clip == 'die' and n >= first) or (clip == 'hurt' and n == 1)


# KINDS-START

def facet_eye(a, x, y, r, shut=False, tilt=0.):
    """A faceted compound eye: an angular hexagon with a grid of lit cells and a hot pin of light (dew_moth only)."""
    if shut:
        a.line([(x - r, y - r * .4), (x + r, y + r * .1)], OUTLINE, 2)
        return
    hexa = [polar(x, y, tilt + i * math.pi / 3, r * (1.0 if i % 2 else .86)) for i in range(6)]
    a.poly([polar(x, y, tilt + i * math.pi / 3, r * (1.0 if i % 2 else .86) + 1.4) for i in range(6)], OUTLINE)
    a.poly(hexa, DEW[2])
    for i in range(3):
        a.poly([(x, y), hexa[i * 2], hexa[(i * 2 + 1) % 6]], DEW[3 + (i % 2)])
    a.poly([(x, y), hexa[4], hexa[5]], DEW[1])
    for i in range(6):
        a.line([(x, y), hexa[i]], DEW[1], 1)
    a.ellipse(x - r * .25, y + r * .25, max(1.3, r * .22), max(1.3, r * .22), DEW[4])


def dew_moth(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('dew_moth', recoil + st * 12 - w * 7)
    flap = math.sin(ph * 2.0) * (1 - dn) if clip in ('idle', 'walk') else 0
    if clip == 'attack':
        flap = [.2, .6, 1.0, .1, -.9, -.4, .2, .5][n]
    hy = 69 + bob * 2.5 + w * 4 - st * 4 - dn * 54
    base = hy
    b = .95 + w * .5 - st * .45 + dn * .3       # abdomen hangs this far below the horizontal behind the thorax
    h = .32 - st * .5 + w * .35 - dn * .5       # head direction
    C = (0, base)
    tail = polar(C[0], C[1], math.pi + b, 22)
    # far wings (behind the body), then the abdomen
    wing_a = 2.05 + flap * .45 + dn * .9 + w * .2 - st * .3
    low_a = 3.3 + flap * .3 + dn * .4 - st * .25
    root = (C[0] - 2, C[1] + 6)
    for far, off in ((True, -.9), (False, 0)):
        k = [MOTH[0], MOTH[0], MOTH[1], MOTH[2], MOTH[3]] if far else MOTH
        blade(a, root[0] + (3 if far else 0), root[1], low_a + (.4 if far else 0), 32 * (1 - dn * .25), 15, k, tatter=1, k=.8)
        wa = wing_a + (off if far else 0)
        blade(a, root[0] + (3 if far else 0), root[1] + 1, wa, 46 * (1 - dn * .3), 22, k, tatter=1, k=.8)
        tp = polar(root[0], root[1] + 1, wa, 46 * (1 - dn * .3) * .98)
        mp = polar(root[0], root[1] + 1, wa, 46 * (1 - dn * .3) * .5)
        a.ellipse(mp[0], mp[1], 4.5, 2.4, k[4])     # a moon-spot on the wing
        a.ball(tp[0], tp[1], 4.4, 4.4, DEW)          # the dew bead at the tip
    # the dew-drop abdomen: a glassy teardrop hanging behind the thorax; it bursts on death
    if dn < .5:
        sw = 1 + .06 * math.sin(ph * 2) * (1 - dn) + st * .08
        axis = b + math.pi
        for i in range(3):
            q = mixp(C, tail, .3 + i * .18)
            a.ball(q[0], q[1], 8 - i * .8, 7 - i * .8, MOTH, axis)
        a.ball(tail[0], tail[1], 12 * sw, 15 * sw, DEW, axis + math.pi / 2 - .0)
        a.ellipse(tail[0] - 4, tail[1] + 5, 2.4, 3.6, DEW[4])
        a.ellipse(tail[0] + 3, tail[1] - 6, 1.8, 1.4, DEW[3])
        tip = polar(tail[0], tail[1], axis, 17)
        a.poly([polar(tail[0], tail[1], axis + .5, 9), tip, polar(tail[0], tail[1], axis - .5, 9)], PLATE[2], outline=OUTLINE)
    else:
        for i in range(9):
            q = (tail[0] + (i - 4) * 4.2 * (dn - .3) * 2.2, tail[1] - 6 - dn * 30 + (i % 3) * 5 - (i % 2) * 6)
            a.ball(q[0], max(4., q[1]), 3.4 - (i % 3) * .6, 3.4 - (i % 3) * .6, DEW)
    # thorax, fringe, head, eyes, needle and mandibles
    a.ball(C[0], C[1], 10, 9, MOTH, .3)
    for i in range(4):
        q = polar(C[0], C[1], math.pi * (.45 + i * .22), 9)
        a.poly([q, polar(q[0], q[1], math.pi * (.55 + i * .22) + .3, 6), polar(q[0], q[1], math.pi * (.35 + i * .22), 5)], MOTH[3], outline=MOTH[0])
    for i in range(3):   # hooked forelegs
        s = polar(C[0], C[1] - 5, -.5 - i * .4 + dn * .8, 7)
        t = polar(s[0], s[1], -1.2 - i * .3 + (w - st) * .4, 12)
        a.line([s, t], MOTH[0], 3)
        a.line([t, polar(t[0], t[1], -.3 - i * .3, 5)], MOTH[0], 3)
    Hh = polar(C[0], C[1], h, 16)
    a.ball(Hh[0], Hh[1], 11, 10, MOTH, h)
    shut = dying(clip, n)
    facet_eye(a, Hh[0] + 2.5, Hh[1] + 1.5, 8.2, shut, .2)
    facet_eye(a, Hh[0] - 7, Hh[1] + 3.5, 5.4, shut, .5)
    a.line([(Hh[0] - 11, Hh[1] + 11), (Hh[0] + 11, Hh[1] + 6.5)], MOTH[0], 3)   # a heavy brow
    nd = h - .45 - st * .1
    n0 = polar(Hh[0], Hh[1], h - .2, 8)
    reach = 22 + st * 20 + w * -4
    n1 = polar(n0[0], n0[1], nd, reach)
    a.poly([polar(n0[0], n0[1], nd + 1.57, 2.6), n1, polar(n0[0], n0[1], nd - 1.57, 2.6)], PLATE[3], outline=OUTLINE)
    for sd in (-1, 1):
        m = polar(Hh[0], Hh[1], h - .5 + sd * .55, 8)
        fang(a, m[0], m[1], 8, 3.4, nd + sd * .5 + (.25 if st > .3 else 0), BONE)
    # comb antennae
    for sd, ln in ((1, 22), (-1, 17)):
        ab = polar(Hh[0], Hh[1], h + 1.1 + sd * .2, 8)
        pts = bez(ab, polar(ab[0], ab[1], h + 1.9, 10), polar(ab[0], ab[1], h + 2.5 + math.sin(ph) * .15 + sd * .25, ln), 5)
        a.line(pts, MOTH[0], 2)
        for q in pts[1:]:
            a.line([q, (q[0] - 1.5, q[1] + 4)], MOTH[3], 1)
    # dew spray on the stab; a puddle once it has dropped
    if st > .2:
        for i in range(6):
            q = polar(n1[0], n1[1], nd + (i - 2.5) * .4, 6 + i * 3 * st)
            a.ball(q[0], q[1], 2.6 - (i % 3) * .5, 2.6 - (i % 3) * .5, DEW)
    if clip == 'die' and n >= 5:
        pw = (n - 4) * 9
        a.ellipse(C[0] - 20, 3, pw, 3, DEW[2])
        a.ellipse(C[0] - 22, 4, pw * .6, 1.8, DEW[4])
    return a


def lure(a, x, y, glow, big=1.):
    a.ball(x, y, 6.5 * big, 6.5 * big, SPORE)
    a.ellipse(x - 1.2, y + 1.6, 2.6 * big, 2.2 * big, SPORE[4])
    for k in range(6):
        q = polar(x, y, k * 1.047 + glow * 3, 9 * big + glow * 3)
        a.ellipse(q[0], q[1], 1.2, 1.2, SPORE[3])


def lumen_eel(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    lp = (.35 + n / 7 * 2 * math.pi) if clip == 'attack' else ph      # lure and fin phase: the attack closes a full cycle
    a = Painter('lumen_eel', recoil + st * 18 - w * 10)
    lit = 1 - sm(dn * 1.5)
    amp = (8 + 4 * w) * (1 - dn) * (1 - st * .7)          # the S curve
    hy = 60 + bob * 2 - dn * 48 + w * 3
    ramp = EEL if lit > .2 else [EEL[0], EEL[0], EEL[1], EEL[1], EEL[2]]
    # spine: a long S of overlapping segments from the head (right) to a forked tail (left)
    N = 11
    spine = []
    for i in range(N):
        t = i / (N - 1)
        x = 34 - t * 84 + w * 14 * t - st * 8 * t
        wph = (.35 * 1.2 + n / 7 * 2 * math.pi) if clip == 'attack' else ph * (2 if clip == 'walk' else 1.2)   # the attack wave closes a full cycle: recovery equals idle 0
        y = hy + math.sin(wph + t * 5.2) * amp * (.3 + t)
        y -= dn * t * 8 + st * (1 - t) * -4
        if clip == 'die':
            y = mix(y, 8 + (1 - t) * 4 + math.sin(t * 6) * 3, sm(dn * 1.3))
        spine.append((x, y))
    fin_ang = 2.9
    # tail fin: a ragged forked blade
    t0, t1 = spine[-1], spine[-2]
    ta = math.atan2(t0[1] - t1[1], t0[0] - t1[0])
    for sd in (-1, 1):
        blade(a, t0[0], t0[1], ta + sd * .55, 24, 12, EEL, tatter=1, k=.75)
    # dorsal spines along the back
    for i in range(1, N - 2):
        q = spine[i]
        if i % 2 == 0:
            a.poly([(q[0] - 5, q[1] + 6), (q[0] - 8 - w * 2, q[1] + 18 + (i % 3) * 3 - dn * 8), (q[0] + 3, q[1] + 7)], EEL[2], outline=EEL[0])
    # body segments, tail first so the head overlaps
    for i in range(N - 1, 0, -1):
        t = i / (N - 1)
        q = spine[i]
        r = 5.5 + 8 * math.sin(min(1, (1 - t) * 1.25) * 1.45)
        a.ball(q[0], q[1], r + 1.5, r, ramp, math.atan2(spine[i - 1][1] - q[1], spine[i - 1][0] - q[0]))
        if i % 2 == 1 and lit > .1:
            a.ellipse(q[0] + 1, q[1] - r * .35, 2.3, 2.3, SPORE[3] if lit > .6 else SPORE[1])
            a.ellipse(q[0] + 1, q[1] - r * .35, 1.1, 1.1, SPORE[4] if lit > .6 else SPORE[2])
    # head: a heavy wedge with an underslung jaw of needle teeth, bone brow and blind milky eyes
    hp = spine[0]
    ang = math.atan2(spine[0][1] - spine[1][1], spine[0][0] - spine[1][0])
    gape = .15 + st * .75 + w * .05 + (.2 if clip == 'die' and n < 3 else 0) + (.55 if clip == 'die' and n >= 3 else 0)
    hx, hy2 = hp
    a.ball(hx + 3, hy2 + 1, 16, 11, ramp, ang)
    jaw = polar(hx + 2, hy2 - 3, ang - gape, 20)
    a.poly([(hx - 6, hy2 - 2), jaw, polar(jaw[0], jaw[1], ang - gape + 2.0, 5), (hx - 4, hy2 - 9)], ramp[1], outline=OUTLINE)
    a.poly([(hx - 5, hy2 - 3), polar(hx - 5, hy2 - 3, ang - gape, 19), polar(hx, hy2, ang + .1, 17)], OUTLINE)
    for i in range(7):                     # needle teeth, upper and lower
        u = polar(hx + 2, hy2 + 2, ang - .02, 6 + i * 2.6)
        a.poly([(u[0] - 1.4, u[1]), (u[0] + .8, u[1] - 7 - (i % 2) * 2), (u[0] + 1.4, u[1])], BONE[3], outline=BONE[0])
        v = polar(hx + 2, hy2 - 3, ang - gape, 5 + i * 2.5)
        a.poly([(v[0] - 1.4, v[1]), (v[0] + .6, v[1] + 6 + (i % 2) * 2), (v[0] + 1.4, v[1])], BONE[3], outline=BONE[0])
    # blind eyes: two dead white ovals with no pupil under a heavy bony brow plate
    brow = [(hx - 4, hy2 + 11), (hx + 16, hy2 + 8), (hx + 20, hy2 + 3), (hx + 4, hy2 + 5)]
    plate(a, brow, BONE, .8)
    if not dying(clip, n):
        for ex, ey, er in ((hx + 11, hy2 + 3.5, 3.4), (hx + 2, hy2 + 5, 2.6)):
            a.ellipse(ex, ey, er + 1.2, er * .7 + 1.2, OUTLINE)
            a.ellipse(ex, ey, er, er * .7, PEARL[1])
            a.ellipse(ex - 1, ey + .5, er * .45, er * .28, PEARL[3])
            a.line([(ex - er * .8, ey - .5), (ex + er * .8, ey + .8)], PEARL[0], 1)
    else:
        a.line([(hx + 7, hy2 + 4), (hx + 14, hy2 + 3)], OUTLINE, 2)
    # the hooked lure stalk
    base = (hx - 3, hy2 + 10)
    tipx, tipy = hx + 24 + st * 12 - w * 6, hy2 + 30 - st * 14 + math.sin(lp) * 2 * (1 - dn) - w * 3
    if clip == 'die':
        tipy = mix(tipy, hy2 + 6, sm(dn * 1.4))
        tipx = mix(tipx, hx + 8, sm(dn))
    pts = bez(base, (hx - 6, hy2 + 36), (tipx, tipy), 8)
    taper(a, pts, ramp, 4, 2)
    if lit > .15:
        lure(a, tipx, tipy - 4, math.sin(lp) * .5, 1 + st * .5 + w * .3)
    else:
        a.ball(tipx, tipy - 3, 4.4, 4.4, [EEL[0]] * 2 + [EEL[1]] * 3)
    # pectoral fins
    f0 = spine[2]
    a.poly([(f0[0] + 2, f0[1] - 6), (f0[0] - 12, f0[1] - 18 - math.sin(lp) * 2), (f0[0] + 9, f0[1] - 11)], EEL[2], outline=EEL[0])
    # drifting motes
    if lit > .3:
        for i in range(5):
            q = (-30 + i * 19 + math.sin(n + i) * 4, hy - 16 - (i * 7 + n * 3) % 20)
            a.ellipse(q[0], q[1], 1.6, 1.6, SPORE[3])
    return a


def bell_pts(h, rw, rim):
    """Outline of a flared bell standing on the origin: shoulder dome, waist, flared rim."""
    return [(-rw * .28, h), (rw * .28, h), (rw * .6, h * .86), (rw * .72, h * .55),
            (rw * .8, h * .28), (rw + rim, 0), (-rw - rim, 0),
            (-rw * .8, h * .28), (-rw * .72, h * .55), (-rw * .6, h * .86)]


def rootbell(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('rootbell', recoil + st * 6 - w * 3)
    tilt = -sm(max(0, dn - .12) * 1.25) * 1.5                   # topples forward onto its right side
    lift = max(0., (22 + bob * .8 + w * 9 - st * 14) * (1 - sm(dn * 1.5)))   # the bell hangs this far off the ground on its roots
    hgt, rw, rim = 52, 27, 5
    piv = (rw + rim, lift)

    def T(x, y):
        """A point in bell space (bell standing on its rim) to canvas space."""
        px, py = x, y + lift
        if not tilt:
            return px, py
        return rotp([(px, py)], tilt, piv[0], piv[1])[0]

    def TP(pts):
        return [T(x, y) for x, y in pts]

    # roots: four gnarled legs that hold the bell up and shuffle; on death they curl and wither
    dead_col = [BARK[0], BARK[0], BARK[1], BARK[1], BARK[2]]
    for k, (hx, sd) in enumerate(((-24, 0), (-9, 1), (9, 1), (25, 0))):
        swing = math.sin(ph + (k % 2) * math.pi) if clip == 'walk' else 0
        out = 1 if hx > 0 else -1
        foot_x = hx + out * (7 + 5 * sd * 0) + swing * 6 + st * (8 if hx > 0 else -2)
        top = mixp(T(hx * .85, 5), (hx * .7 + 6, 9 + (k % 2) * 4), sm(dn * 2))
        top = (top[0], max(top[1], 3.))
        tip = (foot_x * (1 + dn * .3) * (1 - dn * .45), 1.5 + max(0, swing) * 5 * (1 - dn))
        knee = (mix(top[0], tip[0], .35) + out * 6 * (1 - dn), mix(top[1], tip[1], .5) + 6 - dn * 4)
        col = BARK if dn < .6 else dead_col
        taper(a, bez(top, knee, tip, 5), col, 8 - sd * 1.5, 4)
        px0, py0 = tip[0] + out * 1.5, max(0., tip[1] - 1.5)
        a.poly([(px0 - 6, py0), (px0 + 6, py0), (px0 + 4.5, py0 + 3.4), (px0 - 4.5, py0 + 3.4)], col[2], outline=col[0])   # a flat gripping pad on the ground
        for j in range(3):
            q = (tip[0] + (j - 1) * 4.5 + out * 1.5, 2.2)
            a.line([tip, q], col[1], 3)
    # the bell body: a shaded polygon plus a lit shoulder and verdigris stains
    plate(a, TP(bell_pts(hgt, rw, rim)), BRONZE, .82)
    for px, py, pr in ((-14, 44, 5), (11, 30, 4.5), (-20, 22, 4), (17, 46, 3.4)):
        q = T(px, py)
        a.ball(q[0], q[1], pr, pr * .7, TEAL, tilt)
    q = T(-11, 44)
    a.ellipse(q[0], q[1], 2.6, 5, BRONZE[4])
    # two gold bands: the lip, and a girdle
    plate(a, TP([(-rw - rim + .5, 0), (rw + rim - .5, 0), (rw + rim - 1, 5), (-rw - rim + 1, 5)]), GOLD, .8)
    plate(a, TP([(-rw * .78, hgt * .5), (rw * .78, hgt * .5), (rw * .8, hgt * .5 + 5), (-rw * .8, hgt * .5 + 5)]), GOLD, .8)
    # a dark visor and a toothed maw: two pinpoint lights hide in the dark, no lids, no highlights, no blush
    alive = not dying(clip, n)
    gap = 10 + st * 6 + w * 2 + (3 if clip == 'die' and n < 3 else 0)
    vis = [(-17, 31), (17, 31), (14, 37), (-14, 37)]
    a.poly(TP(vis), OUTLINE)
    mouth_top, mouth_bot = 20, 20 - gap * .55
    zig = [(-21, mouth_top)]
    for i in range(1, 8):
        zig.append((-21 + i * 6, mouth_top - (4.5 if i % 2 else 0) - (1.5 if i % 2 else 0)))
    zig.append((21, mouth_top))
    zig_b = [(21, mouth_bot)] + [(21 - i * 6, mouth_bot + (4 if i % 2 else 0)) for i in range(1, 8)] + [(-21, mouth_bot)]
    a.poly(TP(zig + zig_b), OUTLINE)
    for i in range(7):
        tx = -18 + i * 6
        q0 = T(tx, mouth_top + .5)
        q1 = T(tx + 3, mouth_top - 6.5 - st * 3)
        q2 = T(tx + 6, mouth_top + .5)
        a.poly([q0, q1, q2], BONE[3], outline=BONE[0])
        r0 = T(tx + 3, mouth_bot - .5)
        r1 = T(tx + 6, mouth_bot + 5 + st * 2)
        r2 = T(tx + 9, mouth_bot - .5)
        a.poly([r0, r1, r2], BONE[2], outline=BONE[0])
    if alive:
        for ex in (-8, 8):
            q = T(ex, 34)
            a.ellipse(q[0], q[1], 2.4, 1.6, GOLD[3])
            a.ellipse(q[0], q[1], 1.1, .8, WHITE)
    # the clapper tongue swings out of the mouth
    if dn < .5:
        cl = (math.sin(ph) * 5 * (1 - dn) + st * 20 - w * 5, -5 - st * 2 - w * 2)
        base = T(0, 8)
        cp = T(cl[0], cl[1])
        taper(a, [base, mixp(base, cp, .5), cp], BARK, 6, 4)
        a.ball(cp[0], cp[1] - 2, 6, 6.5, BRONZE if (n % 2 == 0 or clip != 'idle') else GOLD, tilt)
    # seedling on the crown that wilts on death
    sx, sy = T(0, hgt)
    wilt = sm(dn * 1.2)
    a.line([(sx, sy - 2), (sx + 1 - tilt * 2, sy + 7)], MOSS[1], 3)
    for sd in (-1, 1):
        lf = [(sx + 1, sy + 7), (sx + sd * 13, sy + 14 - wilt * 12 + math.sin(ph) * 1.2 * sd), (sx + sd * 17, sy + 8 - wilt * 12), (sx + sd * 6, sy + 4)]
        plate(a, lf, MOSS if wilt < .5 else [MOSS[0], MOSS[0], MOSS[1], MOSS[1], MOSS[2]], .7)
    # the clang ring when it slams down
    if st > .25:
        for i, r in enumerate((26, 40, 54)):
            for sd in (-1, 1):
                q = (sd * (r + st * 10), 8 + i * 3)
                a.line([(q[0], q[1] - 7), (q[0] + sd * 3, q[1]), (q[0], q[1] + 7)], GOLD[3] if i == 0 else GOLD[2], 3)
    # cracks run up the bell on death
    if clip == 'die' and n >= 1:
        for i, (cx0, ln) in enumerate(((-9, 30), (12, 24), (-1, 40))[:max(1, min(3, n))]):
            pts = [T(cx0, 2), T(cx0 + 3, 2 + ln * .4), T(cx0 - 2, 2 + ln * .7), T(cx0 + 2, 2 + ln)]
            a.line(pts, OUTLINE, 2)
    return a


GLASSLEG = [GLASS[0], GLASS[1], GLASS[1], GLASS[2], GLASS[3]]


def tideglass_heron(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('tideglass_heron', recoil + st * 10 - w * 6)
    sink = sm(dn * 1.6)
    hipy = (50 + bob * .8) * (1 - .78 * sink)
    # stilt legs with reversed ankles and three forward talons; they fold outward when it falls
    for k, hx in enumerate((-9, 6)):
        swing = math.sin(ph + k * math.pi) if clip == 'walk' else 0
        lift = max(0, swing) * 8
        fx = hx + swing * 8 + (st * 8 if k else -st * 4)
        ankle = (hx - 6 + swing * 3, 26 * (1 - .7 * sink) + lift * .5)
        foot_p = (fx + 3, 1.5 + lift)
        if dn:
            foot_p = mixp(foot_p, (hx + (24 if k else -22), 2.), sink)
            ankle = mixp(ankle, (hx + (11 if k else -13), 8.), sink)
        a.limb([(hx, hipy - 4), ankle, foot_p], GLASSLEG, 5)
        claw(a, foot_p[0] + 1, foot_p[1] + 1.5, .45, 9, .05, BONE)
    by = hipy + 8
    # tail plumes streaming back, then the body and layered feather shards
    for i in range(4):
        shard(a, -34 - i * 4, by + 4 - i * 5 - dn * 6, 38 - i * 3, 9, math.pi + .2 + i * .17 + math.sin(ph + i) * .05 * (1 - dn), GLASS)
    shatter = dn > .28
    if not shatter:
        a.ball(-4, by + 6, 27, 14, GLASS, -.3 + st * .15)
    else:
        u = sm((dn - .28) / .72)
        for i in range(9):
            o = (-26 + i * 6, by + 6 + ((i * 5) % 9) - 3)
            e = (o[0] + (i - 4) * 5 + (7 if i > 4 else -7), 4 + (i % 3) * 4)
            q = mixp(o, e, u)
            shard(a, q[0], q[1], 22, 11, i * 1.3 + dn * 2.6, GLASS)
    if not shatter:
        for i in range(5):
            shard(a, 2 - i * 8, by + 8 - i * 2.2, 23, 11, math.pi + .12 + i * .06, GLASS)
    # neck: a double S that coils in the wind-up and spears forward on the strike
    sh = (16, by + 11)
    idle = (30, by + 42 + bob)
    wind = (4, by + 34)
    strike = (66, by - 4)
    Hd = mixp(mixp(idle, wind, w), strike, st)
    if dn:
        Hd = mixp(Hd, (46, 8.), sm(dn * 1.3))
    M = mixp(sh, Hd, .5)
    c1 = (sh[0] - 10 - w * 6 + st * 14, sh[1] + 16 - dn * 14)
    c2 = (M[0] + 14 + w * 4 - st * 6, M[1] + 14 - st * 20 - dn * 18)
    neck = bez(sh, c1, M, 6)[:-1] + bez(M, c2, Hd, 6)
    taper(a, neck, GLASS, 10, 6.5)
    ba = -.15 - st * .5 + w * .3 - sink * .5
    # head, crest of shards, slit-pupil eye under a scowling brow, dagger beak
    for i, (an, ln) in enumerate(((2.6, 22), (2.9, 18), (3.3, 15))):
        shard(a, Hd[0] - 6 + math.cos(an) * 6, Hd[1] + 3 + math.sin(an) * 5, ln, 6.5, an + ba * .5, GLASS)
    a.ball(Hd[0], Hd[1], 10, 7.2, GLASS, ba)
    ex, ey = Hd[0] + 3, Hd[1] + 2
    if not dying(clip, n):
        a.ellipse(ex, ey, 4.2, 3.6, OUTLINE)
        a.ellipse(ex, ey, 3.2, 2.7, GOLD[3])
        a.line([(ex, ey - 2.6), (ex, ey + 2.6)], OUTLINE, 2)
        a.poly([(ex - 5, ey + 4.5), (ex + 5.5, ey + .5), (ex + 5.5, ey + 3.4), (ex - 4, ey + 7.5)], GLASS[0])
    else:
        a.line([(ex - 3, ey + 1), (ex + 3, ey - 1)], OUTLINE, 2)
    base = polar(Hd[0], Hd[1], ba, 8)
    nx, ny = -math.sin(ba), math.cos(ba)
    tip = polar(base[0], base[1], ba, 30 + st * 4)
    gap = .06 + st * .12 + (.15 if clip == 'attack' and n in (2, 3) else 0)
    tipl = polar(base[0], base[1], ba - gap, 27 + st * 4)
    plate(a, [(base[0] - nx * 1, base[1] - ny * 1), tipl, (base[0] - nx * 4.5, base[1] - ny * 4.5)], GOLD, .7)
    plate(a, [(base[0] + nx * 3.6, base[1] + ny * 3.6), tip, (base[0] - nx * 1.2, base[1] - ny * 1.2)], GOLD, .7)
    # a spray of glass when it spears
    if st > .3:
        for i in range(6):
            q = polar(tip[0], tip[1], ba + (i - 2.5) * .55, 5 + i * 3 * st)
            shard(a, q[0], q[1], 8, 4.2, ba + (i - 2.5) * .8, GLASS)
    return a


def hourpetal_stag(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('hourpetal_stag', recoil + st * 16 - w * 8)
    sink = sm(dn * 1.3)
    cy = (49 + bob * .6) * (1 - .6 * sink)
    far = [STAG[0], STAG[0], STAG[1], STAG[2], STAG[3]]
    # four thin legs with planted hooves; the forelegs buckle first on death, then it rolls onto its side
    for k, (hx, shade, front) in enumerate(((-14, far, False), (12, far, True), (-27, STAG, False), (25, STAG, True))):
        swing = math.sin(ph + (k % 2) * math.pi) if clip == 'walk' else 0
        lift = max(0, swing) * 6
        hip = (hx, cy - 8)
        fx = hx + swing * 8 + (st * 10 if front else 0)
        tip = (fx, lift + 1.5)
        if dn:
            tip = mixp(tip, (hx + (17 if front else -15) + (k % 2) * 6, 3. + (k % 2) * 2), sink)
        knee = (mix(hip[0], tip[0], .45) + (6 if front else -7), mix(hip[1], tip[1], .5) + 2)
        a.limb([hip, knee, tip], shade, 5)
        foot(a, tip[0] + 1.5, max(0, tip[1] - 2.5), 4.6, 3, [BONE[0], BONE[1], BONE[1], BONE[2], BONE[3]])
    # body with bony ridge and ribs
    a.ball(-2, cy, 33, 14.5, STAG, -.08)
    for i in range(4):
        fang(a, -22 + i * 10, cy + 12, 6 + (i % 2) * 2, 4.4, math.pi / 2 + .2, BONE)
    for i in range(4):
        a.line(bez((-8 + i * 7, cy + 8), (-5 + i * 7, cy), (-9 + i * 7, cy - 8), 4), STAG[0], 1)
    a.limb([(-32, cy + 3), (-42, cy - 2 - dn * 4)], STAG, 5)
    # the hourglass on the flank: the sand runs down and out on death
    f = max(0., 1 - dn * 1.15)
    hx0, hy0 = -3, cy
    a.poly([(hx0 - 7, hy0 + 10), (hx0 + 7, hy0 + 10), (hx0 + 1, hy0), (hx0 + 7, hy0 - 10), (hx0 - 7, hy0 - 10), (hx0 - 1, hy0)], GLASS[2], outline=GOLD[1])
    a.poly([(hx0 - 5, hy0 + 8.5), (hx0 + 5, hy0 + 8.5), (hx0 + 5 * (1 - f), hy0 + 8.5 - 7 * f), (hx0 - 5 * (1 - f), hy0 + 8.5 - 7 * f)], GOLD[3])
    a.poly([(hx0 - 5, hy0 - 8.5), (hx0 + 5, hy0 - 8.5), (hx0, hy0 - 8.5 + 7.5 * (1 - f))], GOLD[3])
    if 0 < f < 1:
        a.line([(hx0, hy0 + 1), (hx0, hy0 - 6)], GOLD[4], 1)
    a.line([(hx0 - 8, hy0 + 10), (hx0 + 8, hy0 + 10)], GOLD[2], 2)
    a.line([(hx0 - 8, hy0 - 10), (hx0 + 8, hy0 - 10)], GOLD[2], 2)
    # neck and the skull head: it lowers its antlers to gore
    sh = (23, cy + 6)
    idle = (42, cy + 22 + bob * .5)
    wind = (34, cy + 28)
    strike = (66, cy + 6)
    H_ = mixp(mixp(idle, wind, w), strike, st)
    if dn:
        H_ = mixp(H_, (56, 9.), sm(dn * 1.2))
    mid = mixp(sh, H_, .5)
    taper(a, [sh, (mid[0] - 4, mid[1] + 3), H_], STAG, 18, 11)
    ha = -.32 - st * .5 + w * .28 - sink * .45
    # antlers: designed in head-local space, rotated with the head; the petals fall off on death
    def A(p):
        return rotp([(H_[0] + p[0], H_[1] + p[1])], ha + .35 - st * 1.05 + w * .1, H_[0], H_[1])[0]
    for far_side in (True, False):
        sd = 1 if far_side else -1       # the far antler leans forward, the near one back
        shade = [BONE[0], BONE[0], BONE[1], BONE[2], BONE[3]] if far_side else BONE
        beam = [A((-2 + sd * 2, 7)), A((-3 + sd * 9, 20)), A((-9 + sd * 14, 33)), A((-10 + sd * 20, 42))]
        taper(a, beam, shade, 6.5, 3)
        for i, (t, ang_, ln) in enumerate(((.38, 1.2, 14), (.66, .75, 15), (1.0, .35, 13))):
            q = bez(beam[0], beam[1], beam[2], 3)
            b0 = A((mix(-2 + sd * 2, -10 + sd * 20, t) - 2 + sd * (t * 2), 7 + 35 * t))
            t0 = polar(b0[0], b0[1], ang_ + ha - st * 1.05 + (0 if far_side else .5), ln)
            taper(a, [b0, mixp(b0, t0, .5), t0], shade, 4.6, 2)
            fall = sm(dn * 1.5)
            px, py = t0[0] + (i - 1) * fall * 10, max(5., t0[1] - fall * (t0[1] - 5 - i * 2))
            r = 4.8 if not far_side else 4
            for q in range(4):
                pa = q * 1.57 + .5 + fall * 3
                a.ball(px + math.cos(pa) * r * .7, py + math.sin(pa) * r * .6, r * .6, r * .5, PINK)
            a.ball(px, py, r * .6, r * .5, GOLD)
    # the skull: cranium, long muzzle, bare jaw with fangs, hollow sockets (no eyes at all)
    a.ball(H_[0], H_[1], 13, 9.5, BONE, ha)
    mz = polar(H_[0], H_[1], ha, 15)
    a.ball(mz[0], mz[1], 11.5, 6, BONE, ha)
    gap = .12 + st * .35 + w * .1
    jw = polar(H_[0] - 1, H_[1] - 2, ha - gap, 13)
    a.ball(jw[0], jw[1] - 1, 10.5, 3.6, [BONE[0], BONE[0], BONE[1], BONE[2], BONE[3]], ha - gap)
    for i in range(5):
        u = polar(mz[0], mz[1], ha, -7 + i * 4.2)
        a.poly([(u[0] - 1.2, u[1] - 4), (u[0], u[1] - 4 - 4.5), (u[0] + 1.4, u[1] - 4)], BONE[4], outline=BONE[0])
        v = polar(jw[0], jw[1], ha - gap, -6 + i * 4.2)
        a.poly([(v[0] - 1.2, v[1] + 1.5), (v[0] + .2, v[1] + 1.5 + 4), (v[0] + 1.4, v[1] + 1.5)], BONE[4], outline=BONE[0])
    nose = polar(mz[0], mz[1], ha, 9)
    a.ellipse(nose[0], nose[1] + 1.5, 1.4, 1, OUTLINE)
    # hollow sockets: pure dark, with a pinprick of gold deep inside while it lives
    s1 = polar(H_[0], H_[1], ha + .55, 8)
    s2 = polar(H_[0], H_[1], ha + 1.75, 6.5)
    for sp, rr in ((s1, 4.6), (s2, 3.4)):
        a.poly([(sp[0] - rr, sp[1] + rr * .2), (sp[0] + rr * .4, sp[1] + rr), (sp[0] + rr, sp[1] - rr * .7), (sp[0] - rr * .3, sp[1] - rr)], OUTLINE)
        if not dying(clip, n):
            a.ellipse(sp[0] + .5, sp[1], .9, .9, GOLD[3])
    a.line([(s1[0] - 5, s1[1] + 5.4), (s1[0] + 5.5, s1[1] + 2.6)], BONE[0], 2)   # brow ridge
    # falling sand and petals on death
    if clip == 'die' and n >= 3:
        for i in range(6):
            a.ellipse(hx0 + math.sin(n + i) * 2, max(3., hy0 - 6 - (i * 7 + n * 4) % 38), 1.3, 1.3, GOLD[3])
    return a


def moonskein_weaver(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('moonskein_weaver', recoil + st * 8 - w * 5)
    sink = sm(dn * 1.5)
    hipy = (46 + bob * .6) * (1 - .82 * sink)
    cloth = [THREAD[0], THREAD[1], THREAD[2], THREAD[3], THREAD[4]]
    # two long digitigrade legs that fold in on death
    for k, hx in enumerate((-8, 7)):
        swing = math.sin(ph + k * math.pi) if clip == 'walk' else 0
        lift = max(0, swing) * 7
        foot_p = (hx + swing * 8 + 3 + st * 5 * k, 1.5 + lift)
        knee = (hx + 11 * (1 - sink), hipy * .52 + 2)
        if dn:
            foot_p = mixp(foot_p, (hx + (18 if k else -17), 3.), sink)
        a.limb([(hx, hipy), knee, foot_p], cloth, 5)
        foot(a, foot_p[0] + 2, max(0, foot_p[1] - 2.5), 6, 3, cloth)
    # the spindle body wound with silver thread: it thins and slumps as the thread unravels
    sc = 1 - .72 * sink
    prof = [(-4, 2), (-15, 14), (-18, 24), (-12, 36), (-5, 46), (5, 46), (12, 36), (18, 24), (15, 14), (4, 2)]
    pts = [(x * (1 - .25 * sink), hipy + y * sc) for x, y in prof]
    plate(a, pts, THREAD, .8)
    for i in range(8):
        yy = 4 + i * 5.2
        half = 5 + 12 * math.sin(min(1, (yy + 2) / 48) * math.pi) ** .8
        a.line([(-half * .9, hipy + yy * sc), (half * .9, hipy + (yy + 3.6) * sc)], THREAD[4], 2)
        a.line([(-half * .9, hipy + (yy - 1.4) * sc), (half * .9, hipy + (yy + 2.2) * sc)], THREAD[0], 1)
    for fy in (2, 46):   # the gold flanges of the spindle
        a.ball(0, hipy + fy * sc, 12, 3.6, GOLD)
    top = hipy + 46 * sc
    # the ring of beads: back half behind the hood, front half in front
    hcx, hcy = 3, top + 24 * sc
    beads = []
    for i in range(7):
        t = i * 2 * math.pi / 7 + ph * (-.9 if clip != 'attack' else -1.8) * (1 - sink) + .3
        beads.append((hcx + 24 * math.cos(t), hcy + 3 + 6 * math.sin(t), math.sin(t)))
    for bx, by_, z in beads:
        if z < 0 and sink < .6:
            a.ball(bx, by_ - 2, 3.6, 3.6, GOLD)
    # hood, then the porcelain mask with one seam eye and a stitched mouth
    hood = [(-14, top + 2), (-13, top + 18), (-4, top + 32), (4, top + 40 - sink * 6), (13, top + 24), (14, top + 14), (13, top + 2)]
    hood = [(x, y - (top + 2) * sink * .25) for x, y in hood]
    plate(a, hood, [THREAD[0], THREAD[0], THREAD[1], THREAD[2], THREAD[3]], .78)
    mx, my = 5, hood[1][1] + 4
    a.ball(mx, my + 3, 10, 13, BONE)
    shut = dying(clip, n)
    a.line([(mx + 2.4, my + 9), (mx + 2.4, my + 1)], OUTLINE, 4)
    if not shut:
        a.line([(mx + 2.4, my + 8), (mx + 2.4, my + 2)], GOLD[3] if (st > .3 or w > .3) else GOLD[2], 2)
        a.line([(mx + 2.4, my + 6.5), (mx + 2.4, my + 3.5)], GOLD[4], 1)
    a.line([(mx - 3, my + 9), (mx + 1, my + 3)], BONE[0], 1)       # hairline cracks in the porcelain
    a.line([(mx + 7, my - 3), (mx + 4, my + 1)], BONE[0], 1)
    if st > .3:     # the stitches snap: a ragged open mouth of needle teeth
        a.poly([(mx - 3, my - 6), (mx + 8, my - 5), (mx + 6, my - 10), (mx - 2, my - 10)], OUTLINE)
        for i in range(4):
            fang(a, mx - 2 + i * 3, my - 5, 3, 1.8, math.pi / 2 if i % 2 else -math.pi / 2, BONE)
    else:
        a.line([(mx - 3, my - 6), (mx + 8, my - 6)], OUTLINE, 1)
        for i in range(4):
            sx = mx - 2 + i * 3
            a.line([(sx - 1, my - 8), (sx + 1, my - 4)], OUTLINE, 1)
            a.line([(sx - 1, my - 4), (sx + 1, my - 8)], OUTLINE, 1)
    for bx, by_, z in beads:
        if z >= 0 and sink < .6:
            a.ball(bx, by_ - 2, 3.6, 3.6, GOLD)
    # four needle arms; they cross behind it on the wind-up and all four thrust on the strike
    def needle(h, ang, ln):
        t = polar(h[0], h[1], ang, ln)
        nx, ny = -math.sin(ang), math.cos(ang)
        a.poly([(h[0] + nx * 1.8, h[1] + ny * 1.8), t, (h[0] - nx * 1.8, h[1] - ny * 1.8)], PLATE[4], outline=OUTLINE)
        a.ball(h[0], h[1], 3.4, 3.4, cloth)
        return t
    spec = (
        # shoulder, rest hand, wind-up hand, strike hand, needle length
        ((10, hipy + 38 * sc), (28, hipy + 30 * sc), (-6, hipy + 48 * sc), (58, hipy + 38 * sc), 30),
        ((11, hipy + 22 * sc), (26, hipy + 8 * sc), (-12, hipy + 30 * sc), (62, hipy + 22 * sc), 28),
        ((-9, hipy + 38 * sc), (-27, hipy + 30 * sc), (-28, hipy + 66 * sc), (44, hipy + 48 * sc), 24),
        ((-10, hipy + 22 * sc), (-26, hipy + 8 * sc), (-34, hipy + 52 * sc), (40, hipy + 12 * sc), 24),
    )
    for k, (sh, rest, windp, strikep, ln) in enumerate(spec):
        hand = mixp(mixp((rest[0], rest[1] + math.sin(ph + k) * 2), windp, w), strikep, st)
        if dn:
            hand = mixp(hand, (sh[0] + (22 if k % 2 == 0 else -22) + k * 3, 4.), sm(dn * 1.4))
        bend = -1 if k < 2 else 1
        el, hand = arm_ik(sh, hand, 17, 17, bend=bend)
        a.limb([sh, el, hand], cloth, 4.4)
        ang_ = math.atan2(hand[1] - el[1], hand[0] - el[0]) * (1 - sink) + (-.15 + k * .03) * sink
        t = needle(hand, ang_, ln)
        if dn < .9 and st < .2 and w < .3 and k % 2 == 0:   # a short loop of thread from the needle eye
            q = bez(t, (t[0] - 2, t[1] - 8), (t[0] - 5 + k * 3, t[1] - 14), 4)
            a.line(q, THREAD[4], 2)
    # unravelled thread heaps on the ground, the mask rolling to rest on top
    if dn > .2:
        k = sm((dn - .2) / .8)
        for i in range(7):
            a.ball(-26 + i * 9, 4 + (i % 2) * 2, 9 * k + 1, 3.6 * k + 1, THREAD, 0)
        a.ball(22 * k - 4, 5 + 5 * k, 7 * k + 1, 4.4 * k + 1, THREAD, .3)
    return a


def moonwell_echo(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    dn = d
    a = Painter('moonwell_echo', recoil + st * 6 - w * 4)
    cy = 92 + bob * 3 + w * 3 - sm(dn) * 66
    split = sm((dn - .25) * 1.6)
    glow = SPORE
    cold = [MIRROR[0], MIRROR[0], MIRROR[1], MIRROR[2], MIRROR[3]]
    # the hanging cloak of long shards below the face
    for i in range(-3, 4):
        base = (i * 9 + math.sin(ph + i) * 2 * (1 - dn), cy - 20 - abs(i) * 3.5)
        e = (base[0] + i * 4 * dn * 3, 5 + abs(i) % 2 * 4)
        q = mixp(base, e, sm(dn * 1.2)) if dn else base
        shard(a, q[0], q[1] - 16 * (1 - sm(dn)), 38 - abs(i) * 4, 11, -math.pi / 2 + i * .06 + dn * i * .3, MIRROR)
    # orbiting shards: behind the face first, then in front; contract on the wind-up, hurled on the strike
    orb = []
    for i in range(6):
        t = -ph * .9 + i * math.pi / 3 + (.6 if clip == 'attack' else 0)
        rx_ = 52 * (1 - w * .45)
        x0, y0 = rx_ * math.cos(t), cy + 6 + 16 * math.sin(t)
        if st > 0:
            x0 = mix(x0, 30 + (i % 3) * 14 + st * 34, st)
            y0 = mix(y0, cy + (i - 2.5) * 10, st)
        if dn > 0:
            bx, by_ = x0 + math.cos(i * 2.1 + 1) * dn * 34, y0 + math.sin(i * 1.7) * dn * 12
            x0, y0 = bx, max(5. + (i % 3) * 3, by_ - dn * dn * (y0 + 8))
        ang_ = 0. if st > .4 else t + math.pi / 2 + dn * i
        orb.append((x0, y0, math.sin(t), 20 + (i % 3) * 6, ang_))
    for x0, y0, z, L, ang_ in orb:
        if z < 0:
            shard(a, x0, y0, L, 9, ang_, MIRROR)
    # the face: a cracked mirror mask that splits in two on death
    F_l = [(-18, 36), (-4, 46), (3, 42), (1, -6), (2, -28), (-14, -18), (-24, 4)]
    F_r = [(3, 42), (14, 38), (24, 12), (17, -14), (2, -28), (1, -6)]
    if split < .02:
        plate(a, [(x, cy + y) for x, y in F_l + F_r[1:]], MIRROR, .82)
    else:
        for half, sd in ((F_l, -1), (F_r, 1)):
            plate(a, [(x + sd * split * 22, cy + y - split * split * 10) for x, y in half], MIRROR, .82)
    # facets and cracks
    a.line([(-14, cy + 30), (-4, cy + 6), (6, cy + 22)], MIRROR[3], 1)
    a.line([(10, cy + 32), (4, cy + 10)], MIRROR[4], 1)
    ncr = 1 + int(dn * 6) + (2 if clip == 'hurt' else 0)
    cr = [((2, cy - 6), (-12, cy - 14), (-20, cy - 6)), ((2, cy + 4), (14, cy + 20), (22, cy + 14)), ((-4, cy + 14), (-18, cy + 22), (-22, cy + 8)),
          ((6, cy - 2), (16, cy - 12), (14, cy - 24)), ((-2, cy + 24), (-4, cy + 34), (-14, cy + 36)), ((8, cy + 26), (10, cy + 38), (2, cy + 44))]
    for pts_ in cr[:ncr]:
        a.line(list(pts_), OUTLINE, 1)
    # angular hollow sockets with a cold pin of light, and a glowing fissure grin
    if split < .6:
        ox = split * 22
        shut = dying(clip, n)
        for sk, (sx, sy) in enumerate(((-9, cy + 14), (9, cy + 13))):
            r = 7.4 - sk * 1.8
            a.poly([(sx - r, sy + r * .9), (sx + r * .9, sy + r * .5 + sk), (sx - r * .2, sy - r * .9)], VOID[0], outline=OUTLINE)
            if not shut:
                a.poly([(sx - 1, sy + 1), (sx + 2.2, sy + .6), (sx, sy - 1.8)], glow[4])
        gape = 1.5 + 5 * w + 8 * st
        g = [(-14, cy - 6)]
        for i in range(1, 8):
            g.append((-14 + i * 4, cy - 6 + (3 if i % 2 else -2) - gape * (.5 if i % 2 else 0)))
        g.append((14, cy - 7))
        lower = [(14, cy - 7)] + [(14 - i * 4, cy - 8 - gape - (2 if i % 2 else -1)) for i in range(1, 8)] + [(-14, cy - 7)]
        a.poly(g + lower, glow[1] if shut else glow[3], outline=glow[0])
        if gape > 4:     # the mouth yawns open: a black maw rimmed with glowing, jagged teeth
            a.poly(g + lower, OUTLINE)
            a.line(g, glow[4], 2)
            a.line(lower, glow[3], 2)
    for x0, y0, z, L, ang_ in orb:
        if z >= 0:
            shard(a, x0, y0, L, 9, ang_, MIRROR)
    # glints
    if dn < .3 and clip != 'hurt':
        gx, gy = -16 + ((n * 7 + 3) % 5) * 6, cy + 32 - (n % 3) * 9
        a.line([(gx - 2, gy), (gx + 2, gy)], MIRROR[4], 1)
        a.line([(gx, gy - 2), (gx, gy + 2)], MIRROR[4], 1)
    return a


# KINDS-END

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
        np.savez_compressed(ROOT / f'scripts/moonwell_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/moonwell_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'moonwell_{kind}.png' if kind != 'moonwell_echo' else ASSETS / 'moonwell_echo.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    metas = {}
    for path, kinds in ((MANIFESTS['moonwell_echo'], ['moonwell_echo']), (GARDEN, [k for k in KINDS if k != 'moonwell_echo'])):
        metas[path] = dict(frame=[W, H], anchor=[AX, AY], kinds=kinds, clips={}, sprites={k: saved[k] for k in kinds}, tops={}, artStyle='greenmeadow-slime')
    proof, atlases = {}, {}
    for kind in KINDS:
        meta = metas[MANIFESTS[kind]]
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
    print('Exported 238 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    saved = registry()
    for kind in KINDS:
        meta = json.loads(MANIFESTS[kind].read_text())
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
