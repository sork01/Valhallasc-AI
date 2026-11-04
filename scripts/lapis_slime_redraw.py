#!/usr/bin/env python3
"""The Lapis Erg (zone 25) enemy redo: six native PixelFlow sources with per-kind frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner direction (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye-plus-blush face (the old Lapis art gave
every kind googly round eyes and blush). Each kind has its own face routine: narrow glaring beads under a notched brow
with two chisel incisors bared (sandhopper), pinned-back ears over amber slits in a dark mask with a snarl of fangs
(dunefennec), a ridge of six unequal amber eyes over hooked chelicerae (glassscorpion), a raw red slit eye under a
hooked beak with a ruff of white feathers (sunvulture), a carved stone mask with two hollow cyan pits and a cracked
mouth (dunecolossus), and a hard magenta slit under a cruel brow ridge over a long hooked beak (mirageroc). No blush
anywhere. Effects are attached to the body, never loose glyphs. Shaded volume, eight distinct attack frames (wind-up,
strike, recovery) and eight distinct death frames per kind. The six enemies share `lapis.txt` with five NPCs
(`lapis_keeper`, `lapis_cartographer`, `lapis_warden`, `lapis_seer`, `lapis_travel`): export merges only the six enemy
entries and never touches the NPCs. Original cel-shaded art: /media/raid/valhallasc-data/lapis-slime-original-20261104
(`scripts/rollback_lapis_art.py`).
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
    Painter as BasePainter, PALETTE as BASE_PALETTE, OUTLINE, WHITE, EYE_WHITE,
    BONE, PEARL, CRIMSON, CORAL, AMBER, GOLD, GREEN, TEAL, OLIVE, BROWN, PINK, VIOLET, PURPLE, AZURE, FUR, SLATE,
    mix, mixp, rot, sm, bez, taper, foot, arm_ik,
)
from moonspore_slime_redraw import curves as _curves, plate, blob, fang, dust

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/lapis-slime'
REGISTRY = ROOT / 'scripts/lapis_slime_sources.txt'
PREFIX = 'valhallasc_lapis_slime_style_'
KINDS = ['sandhopper', 'dunefennec', 'glassscorpion', 'sunvulture', 'dunecolossus', 'mirageroc']
NAMES = dict(zip(KINDS, ['Sandhopper', 'Dune Fennec', 'Glass Scorpion', 'Sun Vulture', 'The Dune Colossus', 'The Mirage Roc']))
VILLAGERS = ['lapis_keeper', 'lapis_cartographer', 'lapis_warden', 'lapis_seer', 'lapis_travel']
MANIFEST = ASSETS / 'lapis.txt'
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    sandhopper=(103, 60, 56, 54),
    dunefennec=(95, 64, 48, 58),
    glassscorpion=(127, 65, 58, 59),
    sunvulture=(97, 70, 42, 64),
    dunecolossus=(137, 120, 59, 114),
    mirageroc=(143, 153, 69, 147),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('mirageroc',)
PALETTE = BASE_PALETTE[:] + [
    '#2a1608', '#6a3f1c', '#b0793a', '#e0b070', '#fbe3b0',   # SAND (sandhopper, fennec, colossus body)
    '#3a2410', '#8a5a30', '#d9a468', '#f5d49a', '#fff4d8',   # CREAM (fennec fur, vulture ruff)
    '#1c1620', '#3e3440', '#6e5e64', '#a89484', '#d8c8b0',   # STONE (colossus rock, warm grey)
    '#2a0a3a', '#6a1a7a', '#b04ac8', '#e08cf0', '#ffd0ff',   # MIRAGE (roc shimmer)
    '#03283a', '#0a7a9a', '#30c8e8', '#9af0ff', '#e8ffff',   # GLOW (colossus eyes, glass-scorpion glints)
    '#160a14', '#341c2c', '#5a3548', '#855468', '#b4828e',   # PLUM (vulture plumage)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
assert len(PALETTE) <= 256, 'palette exceeds the indexed limit'
_n = len(BASE_PALETTE)
SAND, CREAM, STONE, MIRAGE, GLOW, PLUM = [list(range(_n + 5 * i, _n + 5 * i + 5)) for i in range(6)]


def curves(clip, n):
    """The shared beats, with the walk phase offset so no two of the eight walk frames mirror each other exactly."""
    w, st, d, ph, bob, recoil = _curves(clip, n)
    if clip == 'walk':
        ph += .45
    return w, st, d, ph, bob, recoil


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Art scale per kind (1.0 = the coordinates written in the draw functions); judged on an in-game screenshot.
SCALE = dict(sandhopper=1.0, dunefennec=1.0, glassscorpion=1.05, sunvulture=1.15, dunecolossus=1.4, mirageroc=1.25)


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


def clamp01(t):
    return 0. if t < 0 else (1. if t > 1 else t)


def polar(x, y, ang, r):
    return x + math.cos(ang) * r, y + math.sin(ang) * r


def dying(clip, n, first=2):
    return (clip == 'die' and n >= first) or (clip == 'hurt' and n == 1)


def cross_eye(a, x, y, r=2.6):
    a.line([(x - r, y - r), (x + r, y + r)], OUTLINE, 2)
    a.line([(x - r, y + r), (x + r, y - r)], OUTLINE, 2)


def brow(a, x0, y0, x1, y1, thick, ramp):
    """A heavy angled brow slab from (x0, y0) to (x1, y1)."""
    a.poly([(x0, y0), (x1, y1), (x1, y1 - thick), (x0, y0 - thick * .7)], ramp[0])
    a.line([(x0, y0 - thick * .2), (x1, y1 - thick * .2)], ramp[1], 1)


def teeth(a, x0, x1, y, size, ramp=BONE, down=True, n=None):
    """A row of small triangular teeth between x0 and x1 hanging from (down) or rising from (not down) the line y."""
    n = n or max(2, int(abs(x1 - x0) / 2.6))
    for i in range(n):
        x = mix(x0, x1, (i + .5) / n)
        tip = y - size * (1 - .35 * (i % 2)) if down else y + size * (1 - .35 * (i % 2))
        a.poly([(x - 1.15, y), (x + 1.15, y), (x, tip)], ramp[4], outline=ramp[0])


class Rig:
    """Draw body-local parts rotated by phi (radians, counter-clockwise, y up) about a pivot, so a whole creature can tumble."""

    def __init__(self, a, px, py, phi, lift=0.):
        self.a, self.px, self.py, self.phi, self.lift = a, px, py, phi, lift

    def t(self, x, y):
        c, s = math.cos(self.phi), math.sin(self.phi)
        dx, dy = x - self.px, y - self.py
        return self.px + dx * c - dy * s, self.py + dx * s + dy * c + self.lift

    def ball(self, x, y, rx, ry, ramp, ang=0.):
        self.a.ball(*self.t(x, y), rx, ry, ramp, ang + self.phi)

    def ellipse(self, x, y, rx, ry, col):
        pts = [self.t(x + math.cos(k * .5236) * rx, y + math.sin(k * .5236) * ry) for k in range(12)]
        self.a.poly(pts, col)

    def poly(self, pts, col, outline=None):
        self.a.poly([self.t(*p) for p in pts], col, outline=outline)

    def line(self, pts, col, width=1):
        self.a.line([self.t(*p) for p in pts], col, width)

    def limb(self, pts, ramp, width=5):
        self.a.limb([self.t(*p) for p in pts], ramp, width)

    def taper(self, pts, ramp, w0, w1):
        taper(self.a, [self.t(*p) for p in pts], ramp, w0, w1)

    def fang(self, x, y, length, width, ang, ramp=BONE):
        fang(self.a, *self.t(x, y), length, width, ang + self.phi, ramp)



class HeadRig(Rig):
    """A Rig that also enlarges everything drawn through it by `hs` about the pivot: big, menacing heads on small bodies."""

    def __init__(self, a, px, py, hs=1.3, phi=0., lift=0., cx=None, cy=None):
        super().__init__(a, px, py, phi, lift)
        self.hs = hs
        self.cx, self.cy = (px if cx is None else cx), (py if cy is None else cy)    # the point the head is enlarged about

    def t(self, x, y):
        return Rig.t(self, self.cx + (x - self.cx) * self.hs, self.cy + (y - self.cy) * self.hs)

    def ball(self, x, y, rx, ry, ramp, ang=0.):
        Rig.ball(self, x, y, rx * self.hs, ry * self.hs, ramp, ang)

    def ellipse(self, x, y, rx, ry, col):
        Rig.ellipse(self, x, y, rx * self.hs, ry * self.hs, col)

    def fang(self, x, y, length, width, ang, ramp=BONE):
        Rig.fang(self, x, y, length * self.hs, width * self.hs, ang, ramp)

    def eyes_out(self, x, y, r=2.4):
        self.line([(x - r, y - r), (x + r, y + r)], OUTLINE, 2)
        self.line([(x - r, y + r), (x + r, y - r)], OUTLINE, 2)

# KINDS-START
# KINDS-HERE
# --- sandhopper
def sandhopper(clip, n):
    """Sandhopper: a hunched sand-coloured jerboa on huge hind legs with a long tufted tail. Mean: tall notched ears pinned
    back, narrow glaring beads under a dark brow slab, two chisel incisors bared. It coils, then springs claws-first with
    the jaws open; when it dies it is thrown over backwards onto its back with the hind legs kicking up."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.08)
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('sandhopper', st * 9 - w * 3 + recoil * .6)
    base = 21 - w * 6 + bob * .7 + (abs(gait) * 2 if clip == 'walk' else 0) - (3 if clip == 'hurt' and n == 1 else 0)
    r = Rig(a, -5, 5, fall * 1.75 - st * .22 + w * .14, 0)
    fur, belly = SAND, CREAM
    dark = [SAND[0], SAND[0], SAND[1], SAND[2], SAND[2]]
    # tail: long and thin, ending in a dark tuft; it whips with the spring and goes slack in death
    sw = math.sin(ph * 1.2) * 2.5 * (1 - fall) + st * 5
    tail = bez((-9, base - 2), (-26, base - 6 + sw - fall * 6), (-38 - st * 6, base + 6 + sw * 1.6 - fall * 16), 10)
    r.taper(tail, dark, 3.4, 1.4)
    tx, ty = tail[-1]
    r.ball(tx - 1, ty, 4.4, 3, [STONE[0], STONE[1], STONE[2], STONE[3], STONE[3]], -.3)
    # far legs
    ext = st * 1. + (.4 if clip == 'walk' and gait > 0 else 0.) * (1 - st)
    kick = fall * (1 + math.sin(n * 2.4) * .3)
    def hind(sd, ramp):
        hip = (-4 + sd, base - 3)
        knee = (mix(-12, -9, ext) + sd, mix(base - 9, base - 5, ext))
        foot = (mix(-4 + sd * 2 - gait * 3 * sd, -22, ext), mix(1.5, base - 1, ext))
        foot = mixp(foot, (-15 + sd * 3, base + 12 + math.sin(n * 2.6 + sd) * 3), kick)
        r.limb([hip, knee, foot], ramp, 4.6 if sd > 0 else 4)
        r.ball(foot[0] + 3, foot[1], 5, 1.9, ramp, -.15 - kick)
        for c in (0, 1, 2):
            r.line([(foot[0] + 7, foot[1] + (c - 1) * .9), (foot[0] + 9 + st * 2, foot[1] + (c - 1) * 1.2)], BONE[4], 1)
    hind(-1, dark)
    # body
    r.ball(0, base, 10.8, 9.6, fur, -.25)
    r.ball(3.4, base - 2.6, 6.6, 5.6, belly, -.15)
    for k in range(4):                                         # dark dorsal speckle bands
        r.line([(-6 + k * 2.6, base + 8.4 - k * .6), (-4.4 + k * 2.6, base + 5.6 - k * .6)], SAND[1], 1)
    hind(1, fur)
    # near forearm: small clawed arm that reaches on the strike
    sh = (6, base + 1.5)
    paw = (11 + st * 11 - w * 2, base - 4 + st * 3 - w * 3 + fall * 8)
    r.limb([sh, mixp(sh, paw, .55), paw], fur, 3.2)
    for c in (-1, 0, 1):
        r.line([paw, (paw[0] + 3.4 + st * 1.6, paw[1] - 1 + c * 1.5)], BONE[4], 1)
    # head
    hx, hy = 11.5 + st * 3, base + 9.5 - w * 1.2
    ang = -.1 - st * .12
    for sd in (-1, 1):                                          # tall ears swept back, notched rims, dark linings
        e0 = (hx - 2 + sd * 1.6, hy + 4)
        ear = [(e0[0], e0[1]), (e0[0] - 9 - w * 2 - sd * 1.2, e0[1] + 12 - w * 3), (e0[0] - 3.2, e0[1] + 13.6 - w * 3), (e0[0] + 3, e0[1] + 2)]
        r.poly(ear, (fur[2] if sd > 0 else fur[1]), outline=fur[0])
        r.poly([mixp(ear[0], ear[1], .3), mixp(ear[1], ear[2], .55), mixp(ear[3], ear[2], .45)], PINK[1] if sd > 0 else PINK[0])
        r.line([ear[2], mixp(ear[2], ear[1], .3)], fur[0], 1)  # a notch bitten out of the rim
    r.ball(hx, hy, 8.6, 7.2, fur, ang)
    r.ball(hx + 6.4, hy - 2.6, 5, 3.6, belly, ang)                # muzzle
    r.ellipse(hx + 10.8, hy - 1.2, 1.5, 1.2, STONE[0])             # nose
    gape = 3.2 if (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or fall > .4 else .6
    r.poly([(hx + 3, hy - 4.2), (hx + 11, hy - 3.6), (hx + 9.4, hy - 6.4 - gape), (hx + 3.4, hy - 6.6 - gape)], CRIMSON[0])
    for sd in (0, 1):                                           # two chisel incisors, bared
        x = hx + 8 + sd * 1.9
        r.poly([(x - .9, hy - 3.8), (x + .9, hy - 3.8), (x + .8, hy - 7.6 - gape * .4), (x - .8, hy - 7.6 - gape * .4)], BONE[4], outline=BONE[0])
    ex, ey = hx + 4.6, hy + 1.8
    if dying(clip, n):
        r.line([(ex - 1.8, ey - 1.8), (ex + 1.8, ey + 1.8)], OUTLINE, 2)
        r.line([(ex - 1.8, ey + 1.8), (ex + 1.8, ey - 1.8)], OUTLINE, 2)
    else:
        r.poly([(ex - 3, ey - .8), (ex, ey + 1.2), (ex + 3, ey - .2), (ex + 2.4, ey - 1.8), (ex - 1.6, ey - 2)], GOLD[3])
        r.ellipse(ex + .8, ey - .5, .9, 1, OUTLINE)
        r.poly([(ex - 3.8, ey + 2.8), (ex + 3.6, ey + .4), (ex + 3.6, ey + 2.2), (ex - 2.8, ey + 4.2)], SAND[0])   # glaring brow slab
    return a

# --- dunefennec
def dunefennec(clip, n):
    """Dune fennec: a lean cream desert fox with enormous ears and a brush tail. Mean: ears flat back, a dark mask with
    narrow amber slits under hard brows, the lip drawn up off long fangs. It drops into a stalking crouch, then lunges with
    the jaws wide; when it dies it slumps forward onto its chest, then rolls onto its side with the ears limp."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = dn
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('dunefennec', st * 10 - w * 5 + recoil * .6)
    low = w * 5 + fall * 8
    base = 24 - low + bob * .6
    roll = sm((dn - .45) * 2) * 1.35                           # rolls onto its side late in the fall
    r = Rig(a, 0, 4, -fall * .5 + st * .12 + roll * .6 - w * .1, 0)
    fur, belly = CREAM, [CREAM[2], CREAM[3], CREAM[4], BONE[3], BONE[4]]
    far = [CREAM[0], CREAM[0], CREAM[1], CREAM[2], CREAM[2]]
    mask = [SAND[0], SAND[0], SAND[1], SAND[2], SAND[2]]
    # brush tail
    sw = math.sin(ph * 1.1) * 2.5 * (1 - fall)
    tail = bez((-12, base + 1), (-26, base + 6 + sw - fall * 7), (-34 - st * 3, base - 2 + sw * 1.5 - fall * 12), 9)
    r.taper(tail, fur, 5.4, 3.2)
    r.ball(tail[-1][0] - 1, tail[-1][1], 4.2, 3.2, mask, .3)       # dark tip
    # legs: four long thin legs; diagonal gait, folded and splayed in death
    def leg(x, sd, ramp, front):
        s = gait * sd * (1 if front else -1)
        hip = (x, base - 5)
        reach = st * (12 if front else -8) + (w * (-4 if front else 3))
        knee = (x + s * 4 + reach * .5, base - 12 + fall * 3)
        foot = (x + s * 7 + reach + fall * sd * 4, 1.4 + max(0, s) * 3 * (clip == 'walk') + fall * 4 * (1 + sd * .3))
        r.limb([hip, knee, foot], ramp, 3.5)
        r.ball(foot[0] + 1.6, foot[1], 2.8, 1.6, ramp, 0)
    leg(-8, -1, far, False); leg(7, -1, far, True)
    # body: long lean barrel
    r.ball(-1, base, 12.6, 8.6, fur, -.06)
    r.ball(1.4, base - 3, 9, 5, belly, -.04)
    r.ball(-4, base + 5, 7, 3, [CREAM[1], CREAM[2], CREAM[3], CREAM[4], CREAM[4]], -.1)   # lit back
    leg(-6, 1, fur, False); leg(9, 1, fur, True)
    # head, low and forward in a stalk
    hx, hy = 13 + st * 5 - w * 3 + fall * 2, base + 7 - w * 2 - fall * 6
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or fall > .45
    # enormous ears: broad triangles, upright at rest, laid flat back in the stalk and the strike, limp in death
    for sd in (-1, 1):
        e0 = (hx - 2.4 + sd * 2.4, hy + 5)
        lay = clamp01(w * .9 + st * 1. + fall * .6)
        tip = (e0[0] - 4 - lay * 15, e0[1] + 19 - lay * 12 - fall * 6)
        ear = [(e0[0] - 5, e0[1] - .5), (e0[0] + 5, e0[1] - .5), tip]
        r.poly(ear, (fur[2] if sd > 0 else far[2]), outline=fur[0])
        r.poly([(e0[0] - 2.4, e0[1] + .8), (e0[0] + 2.6, e0[1] + .8), mixp((e0[0], e0[1]), tip, .72)], PINK[2] if sd > 0 else PINK[1])
    r.ball(hx, hy, 9.4, 7.4, fur, -.08)
    r.ball(hx + 7.6, hy - 2.6, 6.4, 3.8, belly, -.06)                # muzzle
    r.ball(hx - 1, hy + 1, 8.4, 3.2, mask, -.2) if not dying(clip, n) else None
    r.ellipse(hx + 13.6, hy - 1.2, 1.7, 1.4, STONE[0])               # nose
    gape = 4 if open_ else .7
    r.poly([(hx + 3, hy - 4), (hx + 14, hy - 3.2), (hx + 12.2, hy - 6.6 - gape), (hx + 3.6, hy - 7.2 - gape)], CRIMSON[0])
    r.poly([(hx + 7.6, hy - 6.2 - gape), (hx + 12, hy - 6 - gape), (hx + 11, hy - 8.2 - gape)], CRIMSON[2])      # tongue
    for x, l in ((hx + 13, 3.4), (hx + 10.2, 2.4), (hx + 7.4, 2)):    # upper fangs bared by the snarl
        r.poly([(x - 1, hy - 3.4), (x + 1, hy - 3.4), (x + .2, hy - 3.4 - l - gape * .5)], BONE[4], outline=BONE[0])
    for x in (hx + 12.2, hx + 8.6):                                     # lower fangs
        r.poly([(x - 1, hy - 6.2 - gape), (x + 1, hy - 6.2 - gape), (x + .4, hy - 3.8 - gape * .2)], BONE[3], outline=BONE[0])
    ex, ey = hx + 5.2, hy + 1.8
    if dying(clip, n):
        r.line([(ex - 2, ey - 1.6), (ex + 2, ey + 1.6)], OUTLINE, 2)
        r.line([(ex - 2, ey + 1.6), (ex + 2, ey - 1.6)], OUTLINE, 2)
    else:
        r.poly([(ex - 3.8, ey - .6), (ex, ey + 1.6), (ex + 3.8, ey + .2), (ex + 3, ey - 1.8), (ex - 1.6, ey - 1.9)], AMBER[3])
        r.ellipse(ex + .6, ey - .1, .6, 1.4, OUTLINE)                  # a slit pupil
        r.poly([(ex - 4.6, ey + 3.4), (ex + 4.6, ey + .6), (ex + 4.6, ey + 2.6), (ex - 3.4, ey + 5)], SAND[0])   # hard brow
    return a


# --- glassscorpion
def glassscorpion(clip, n):
    """Glass scorpion: a rigid blue glass shell, two heavy claws and a segmented tail ending in a glowing amber sting.
    Mean: a ridge of six unequal amber eyes on the carapace over hooked chelicerae. It cocks the tail over its back, then
    stabs forward over its head with the claws spread; when it dies the shell cracks, the tail drops and it tips over
    onto its back with the legs curling in (rigid: nothing squashes, the cracks stay on the body)."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = dn
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('glassscorpion', st * 6 - w * 4 + recoil * .6)
    base = 11 + bob * .4 - w * 1.2
    flip = sm((dn - .1) * 1.25)                                  # tips over backwards onto its back (0..1)
    r = Rig(a, -2, 2, flip * 3.05 + recoil * -.02, 0)
    shell = AZURE
    deep = [AZURE[0], AZURE[0], AZURE[1], AZURE[2], AZURE[2]]
    glass = [TEAL[0], TEAL[1], TEAL[2], TEAL[3], TEAL[4]]
    # legs: four pairs, jointed, scuttling in alternate pairs; they curl up and in during death
    for k in range(4):
        for sd, ramp in ((-1, deep), (1, shell)):
            s = math.sin(ph * 2 + k * 1.3 + (sd > 0) * 3.14) * (1 if clip == 'walk' else .25)
            x0 = -8 + k * 5.6
            curl = fall * (1.2 + k * .2)
            hip = (x0, base + 1)
            knee = (x0 + sd * 3 + 2 * s, base + 8 - curl * 3)
            foot = (x0 + sd * 7 + 4 * s - curl * 6 * sd, 1.2 + max(0, s) * 2 + curl * 6)
            r.limb([hip, knee, foot], ramp, 2.6)
    # the tail: five segments curving up over the back, then forward in the strike
    cock = w * 1. - st * 1.
    base_pt = (-14, base + 3)
    tail = []
    for i in range(6):
        t = i / 5
        ang = mix(1.0, 2.35, t) - fall * (.9 + t * .5) + cock * (.7 * t) - st * (1.6 * t)
        px = base_pt[0] + sum(math.cos(mix(1.0, 2.35, j / 5) - fall * (.9 + j / 5 * .5) + cock * (.7 * j / 5) - st * (1.6 * j / 5)) * -5.2 for j in range(i))
        py = base_pt[1] + sum(math.sin(mix(1.0, 2.35, j / 5) - fall * (.9 + j / 5 * .5) + cock * (.7 * j / 5) - st * (1.6 * j / 5)) * 5.2 for j in range(i))
        tail.append((px, py))
    for i, p in enumerate(tail):
        rad = 4.6 - i * .45
        r.ball(p[0], p[1], rad, rad, shell if i % 2 else glass, -.2)
    sx, sy = tail[-1]
    dir_ = math.atan2(tail[-1][1] - tail[-2][1], tail[-1][0] - tail[-2][0])
    r.poly([polar(sx, sy, dir_ + 1.5, 2.6), polar(sx, sy, dir_, 8.5), polar(sx, sy, dir_ - 1.5, 2.6)], GOLD[3], outline=AMBER[0])   # glowing sting
    r.ball(sx, sy, 3.6, 3.6, [AMBER[0], AMBER[1], GOLD[2], GOLD[3], GOLD[4]], 0)
    # body
    r.ball(0, base, 14, 7.4, shell, -.04)
    r.ball(-2, base + 2.4, 9.4, 3.8, glass, -.05)               # lit dorsal plates
    for k in range(4):                                           # carapace plate seams
        r.line([(-9 + k * 4.6, base + 6.8), (-9 + k * 4.6 + 1.2, base - 3)], deep[0], 1)
    # claws on jointed arms: they open wide and snap
    open_ = w * 7 + st * 3 + (3 if clip == 'hurt' and n == 1 else 0)
    for sd, ramp in ((-1, deep), (1, shell)):
        sh = (12, base + 1 + sd * 2.4)
        elbow = (22 + st * 6 + w * -4, base + 4 + sd * 5 + w * 3 - fall * 4)
        wrist = (30 + st * 10 + w * -5, base + 2 + sd * 6 + w * 2 - st * 3 - fall * 4)
        r.limb([sh, elbow, wrist], ramp, 4.2)
        r.ball(wrist[0] + 1, wrist[1], 5.6, 4.8, ramp, -.1)                      # the palm
        r.poly([(wrist[0] + 2, wrist[1] + 3.4), (wrist[0] + 13, wrist[1] + 3 + open_ * .5), (wrist[0] + 12, wrist[1] + .4 + open_ * .25), (wrist[0] + 4, wrist[1] - .4)], ramp[3], outline=ramp[0])   # upper jaw
        r.poly([(wrist[0] + 2, wrist[1] - 3.2), (wrist[0] + 12.6, wrist[1] - 3 - open_ * .45), (wrist[0] + 11, wrist[1] - .2), (wrist[0] + 4, wrist[1] + .6)], ramp[2], outline=ramp[0])   # lower jaw
    # head end: hooked chelicerae and the ridge of eyes
    r.ball(13, base + 1, 6.2, 5.2, shell, -.1)
    for sd in (-1, 1):
        r.poly([(15, base - 2.2 + sd * 1.6), (19.5, base - 4.6 + sd * 1.8), (21.4, base - 8.4 + sd * 1.2), (18.4, base - 5.6 + sd * 1.2), (14.4, base - 1.2 + sd * 1.6)], BONE[3], outline=BONE[0])
    if dying(clip, n):
        for sd in (0, 1):
            r.line([(12 + sd * 4 - 1.6, base + 3.6), (12 + sd * 4 + 1.6, base + 6.8)], OUTLINE, 2)
    else:
        for i, (ex, ey, er) in enumerate(((11, base + 5, 1.7), (14.6, base + 4.4, 1.4), (16.4, base + 1.6, 1.1), (9, base + 3.6, 1.2), (12.8, base + 2.2, 1), (17.8, base + 3.6, .9))):
            r.ellipse(ex, ey, er + .8, er + .8, AMBER[0])
            r.ellipse(ex, ey, er, er, GOLD[3] if i % 2 else AMBER[3])
        r.poly([(8.4, base + 7.6), (18.4, base + 5.4), (18.4, base + 6.6), (9, base + 9)], deep[0])    # brow ridge
    # cracks spreading over the shell as it dies: they stay on the body
    if fall > .2:
        for k, (x0, y0, x1, y1) in enumerate(((-2, base + 6, 3, base - 1), (-9, base + 4, -5, base - 4), (5, base + 6, 9, base))):
            if fall > .2 + k * .12:
                r.line([(x0, y0), ((x0 + x1) / 2 + 1.4, (y0 + y1) / 2), (x1, y1)], WHITE, 1)
    return a

# --- sunvulture
def sunvulture(clip, n):
    """Sun vulture: a hunched plum-brown carrion bird with a bald raw-pink head, a white ruff and a gold sun mark on the
    breast. Mean: a hard brow ridge over a small red slit eye, a deep-hooked beak and a wrinkled bare throat. It hunches
    with the wings half open, then throws them wide and rips down with the neck stretched; when it dies the wings crumple
    out to the sides and it pitches forward onto its breast with the head down."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = dn
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('sunvulture', st * 7 - w * 4 + recoil * .6)
    spread = clamp01(w * .65 + st * 1. + fall * .75 + (.35 if clip == 'hurt' and n == 1 else 0))
    base = 29 - w * 2 + bob * .5 - fall * 5
    r = Rig(a, 3, 8, -fall * 1.25 + st * .12 - w * .06, 0)
    feather = [PLUM[0], PLUM[1], PLUM[2], PLUM[3], PLUM[3]]
    dark = [PLUM[0], PLUM[0], PLUM[1], PLUM[2], PLUM[2]]
    skin = CORAL
    # tail feathers fanned behind
    for k in range(3):
        ang = 3.5 - k * .24 + math.sin(ph) * .05 * (1 - fall)
        tip = polar(-8, base - 6, ang, 21 - k * 1.5)
        r.poly([(-8, base - 3 - k), tip, (-8, base - 9 + k)], feather[2 - (k == 1)], outline=feather[0])
    # legs: thick, scaled, three forward toes and a back talon, striding in the walk
    for sd, ramp in ((-1, dark), (1, [GOLD[0], AMBER[1], AMBER[2], GOLD[2], GOLD[3]])):
        s = gait * sd
        hip = (-1 + sd * 2, base - 9)
        knee = (2 + sd * 3 + s * 5, base - 16)
        foot = (1 + sd * 3 + s * 9, 2 + max(0, s) * 4 + fall * 3)
        r.limb([hip, knee, foot], ramp, 3.4)
        for t in (-1, 0, 1):
            r.line([(foot[0], foot[1]), (foot[0] + 6 + (st * 2), foot[1] - 1 + t * 1.6)], BONE[4], 1)
        r.line([(foot[0], foot[1]), (foot[0] - 3, foot[1] + 1)], BONE[4], 1)
    # body, ruff, breast
    r.ball(-1, base, 12.6, 11.4, feather, -.3)
    r.ball(5, base - 3, 6.6, 7.4, [CREAM[0], CREAM[1], CREAM[2], CREAM[3], CREAM[3]], -.1)
    r.ball(5.2, base - 1.2, 3.2, 3.2, GOLD, 0)                          # the sun mark: a disc with eight short rays
    for k in range(8):
        ra = k * .785
        r.line([(5.2 + math.cos(ra) * 3.8, base - 1.2 + math.sin(ra) * 3.8), (5.2 + math.cos(ra) * 5.4, base - 1.2 + math.sin(ra) * 5.4)], GOLD[3], 1)
    # the wing: folded along the body at rest, a fan of long feathers when spread
    sh = (-1, base + 6)
    for k in range(6):
        ang = mix(-2.5 + k * .1, 1.5 - k * .32, spread)
        ln = mix(14 + k * 1.1, 17 + k * 3.2, spread)
        tip = polar(sh[0], sh[1], ang, ln)
        mid = polar(sh[0], sh[1], ang + .14, ln * .55)
        r.poly([sh, polar(sh[0], sh[1], ang + .24, ln * .55), tip, polar(sh[0], sh[1], ang - .24, ln * .55)], feather[1 + (k % 2)], outline=feather[0])
        r.line([polar(sh[0], sh[1], ang, ln * .3), tip], feather[3], 1)
    r.ball(-.5, base + 3.4, 8.4, 6.4, feather, -.6)                      # the wing's upper arm
    # neck and head
    hx, hy = 14.5 + st * 11 - w * 4 + fall * 3, base + 13 - st * 10 + w * 3 - fall * 12
    ruffx, ruffy = 7.6, base + 9
    neck = bez((ruffx, ruffy), (ruffx + 4 + st * 4, ruffy + 7 - st * 5 + w * 2), (hx - 1.6, hy - 2.8), 8)
    r.taper(neck, skin, 5.4, 4.2)
    for k, (px, py) in enumerate(neck[1:6]):                              # throat wrinkles
        r.line([(px - 1.4, py - .6), (px + 1.4, py + .6)], skin[0], 1)
    r.ball(ruffx, ruffy, 6.8, 4.4, [CREAM[1], CREAM[2], CREAM[3], CREAM[4], CREAM[4]], -.3)   # the white ruff
    r.ball(hx, hy, 5.8, 5.2, skin, .1)
    gape = 2.6 if (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or fall > .4 else .3
    r.poly([(hx + 2, hy - 1.6 - gape), (hx + 10.6, hy - 2.4 - gape * .8), (hx + 8, hy - 4.6 - gape), (hx + 2.4, hy - 3.2 - gape)], GOLD[1], outline=AMBER[0])     # lower mandible
    r.poly([(hx + 2.4, hy + 1.8), (hx + 8, hy + 1.6), (hx + 12.4, hy - 1.4), (hx + 11, hy - 4.6), (hx + 9.2, hy - 1.8), (hx + 3, hy - 1.6)], GOLD[3], outline=AMBER[0])   # hooked upper beak
    r.ellipse(hx + 6.4, hy + .2, .8, .8, AMBER[0])                                    # nostril
    ex, ey = hx + 1.8, hy + 1.2
    if dying(clip, n):
        r.line([(ex - 1.8, ey - 1.8), (ex + 1.8, ey + 1.8)], OUTLINE, 2)
        r.line([(ex - 1.8, ey + 1.8), (ex + 1.8, ey - 1.8)], OUTLINE, 2)
    else:
        r.poly([(ex - 2.6, ey - .4), (ex, ey + 1.2), (ex + 2.8, ey - .2), (ex + 2, ey - 1.4), (ex - 1.4, ey - 1.6)], CRIMSON[3])
        r.ellipse(ex + .5, ey - .3, .6, 1, OUTLINE)
        r.poly([(ex - 3.4, ey + 3.2), (ex + 3.8, ey + .4), (ex + 3.8, ey + 2.2), (ex - 2.6, ey + 4.6)], skin[0])   # hard brow ridge
    return a


# --- dunecolossus
def blk(a, cx, cy, hw, hh, ramp, tilt=0., cham=2.4):
    """A shaded chamfered stone block centred on (cx, cy), tilted by `tilt` radians."""
    c, s = math.cos(tilt), math.sin(tilt)
    pts = [(-hw + cham, -hh), (hw - cham, -hh), (hw, -hh + cham), (hw, hh - cham), (hw - cham, hh), (-hw + cham, hh), (-hw, hh - cham), (-hw, -hh + cham)]
    plate(a, [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts], ramp)


def dunecolossus(clip, n):
    """Dune Colossus (elite): a giant of sand-coloured stone blocks, lapis inlay and gold trim, with a head sunk between
    the shoulders. Mean: a carved stone mask, two hollow cyan pits, a cracked mouth dragged down at both corners. It
    lifts both fists overhead and hammers them down in front; when it dies it does not collapse like a slime: the head
    drops first, the arms break off, then the torso and legs shatter and slump into a heap of blocks."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = dn
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('dunecolossus', recoil * .6)
    sand = SAND
    stone = STONE
    inlay = AZURE
    def drop(i, k=1.7):
        return sm((fall - i * .07) * k)
    # chunk: (standing centre, size, heap centre, heap tilt)
    lift = lambda sd: max(0., gait * sd) * 4
    # legs and feet
    for sd, i, ramp in ((-1, 0, stone), (1, 1, sand)):
        d = drop(i)
        x0 = 9 * sd + gait * sd * 2
        blk(a, mixp((x0, 3 + lift(sd)), (14 * sd, 3), d)[0], mixp((x0, 3 + lift(sd)), (14 * sd, 3), d)[1], 9.6, 3.2, ramp, 0)   # foot
        cx, cy = mixp((x0, 15 + lift(sd)), (7 * sd, 9), d)
        blk(a, cx, cy, 6.8, 10.4 - d * 3.4, ramp, d * sd * .45)
        r_ = blk
        a.line([(cx - 4, cy + 2), (cx + 3, cy - 3)], ramp[0], 1) if d > .35 else None   # cracks as it breaks
    # hips and torso
    d = drop(2)
    cx, cy = mixp((0, 27), (-1, 15), d)
    blk(a, cx, cy, 14.5, 6.6 - d * 1.6, sand, -d * .22)
    for k in range(3):                                                                    # lapis belt studs
        a.ellipse(cx - 7 + k * 7, cy + .4, 1.6, 1.6, inlay[3])
    d = drop(3)
    tx, ty = mixp((0, 46 + bob * .6 - w * 3 + st * -2), (4, 22), d)
    tl = d * .5 - st * .05 + w * .04
    cs, sn = math.cos(tl), math.sin(tl)
    tv = 1 - d * .32
    tpts = [(-20, 11 * tv), (20, 11 * tv), (16, 2), (12, -13 * tv), (-12, -13 * tv), (-16, 2)]
    plate(a, [(tx + x * cs - y * sn, ty + x * sn + y * cs) for x, y in tpts], [sand[0], sand[1], sand[2], sand[3], sand[3]])
    if d < .6:
        a.poly([(tx - 11, ty + 9), (tx + 11, ty + 9), (tx + 7, ty - 4), (tx, ty - 8), (tx - 7, ty - 4)], inlay[2], outline=inlay[0])    # a lapis breastplate
        a.poly([(tx - 7, ty + 8), (tx + 4, ty + 8), (tx, ty), (tx - 5, ty - 2)], inlay[3])
    for k in range(3):                                                                    # horizontal strata and chips
        a.line([(tx - 14 + k * 2, ty - 9 + k * 7), (tx + 13 - k * 2, ty - 9 + k * 7)], sand[0], 1)
    a.line([(tx + 8, ty + 10), (tx + 11, ty + 3), (tx + 9, ty - 4)], sand[0], 1)
    a.ellipse(tx, ty - 1, 3, 3, GOLD[3]) if d < .7 else None                              # gold sun-stud
    # arms: shoulder -> elbow -> fist; hanging at rest, overhead on the wind-up, hammering down on the strike
    for sd, i in ((-1, 4), (1, 5)):
        d = drop(i, 1.9)
        sh = (sd * 19, tx and ty + 8)
        hang = (sd * 24 + gait * sd * 3, 13 + (3 if sd < 0 else 0))
        up = (sd * 15, 92)
        slam = (sd * 8 + 20, 7)
        tgt = mixp(mixp(hang, up, w), slam, st)
        e = arm_ik(sh, tgt, 17, 17, 1 if sd > 0 else -1)
        elbow, hand = e
        hand = mixp(hand, (sd * 33 + 7, 4), d)
        elbow = mixp(elbow, (sd * 27, 12), d)
        if d < .5:
            a.limb([sh, elbow, hand], [sand[0], sand[1], sand[2], sand[3], sand[3]], 11)
            a.ball(sh[0], sh[1], 9, 8, [stone[0], stone[1], stone[2], stone[3], stone[3]], 0)         # shoulder boulder
            for t in (.3, .6):
                a.ellipse(mix(sh[0], elbow[0], t) , mix(sh[1], elbow[1], t), 3.6, 1.2, inlay[2])     # lapis arm bands
        else:
            blk(a, elbow[0], elbow[1], 8, 4.6, sand, d * sd * .7)
        a.ball(hand[0], hand[1], 11, 10, [sand[0], sand[1], sand[2], sand[3], sand[4]], 0)             # the fist
        for k in (-1, 0, 1):
            a.line([(hand[0] - 5, hand[1] - 1 + k * 3.2), (hand[0] + 4, hand[1] - 1 + k * 3.2)], sand[0], 1)
        if clip == 'attack' and n in (4, 5):                                                          # sand thrown up where the fists land
            for k in range(4):
                a.ball(hand[0] + (k - 1.5) * 6, 3 + (n == 4) * 3 + k % 2 * 3, 3.4, 3, PEARL if False else [sand[1], sand[2], sand[3], sand[4], sand[4]], 0)
    if clip == 'die' and 3 <= n <= 6:                                                          # sand and grit settling out of the broken heap
        for k in range(5):
            rr = max(1.6, (4.6 - (n - 3) * .9) - k % 2)
            a.ball(-22 + k * 11 + (n - 3) * 1.2, 5 + k % 3 * 2.2 + (n - 3) * 1.4, rr, rr * .8, [sand[1], sand[2], sand[3], sand[4], sand[4]], 0)
    # head: sunk between the shoulders; it drops into the rubble first
    d = drop(.0, 2.4) if fall else 0
    hx, hy = mixp((3 + st * 4, 66 + bob * .6 - w * 3 - st * 5), (15, 11), d)
    blk(a, hx, hy, 9.6, 8.4, [stone[0], stone[1], stone[2], stone[3], stone[4]], -d * .7, 3)
    if d < .55:
        a.poly([(hx - 9, hy + 5), (hx + 9, hy + 5), (hx + 7, hy + 9.4), (hx - 7, hy + 9.4)], stone[0])   # heavy brow shelf
    if dying(clip, n):
        a.line([(hx - 5, hy + 2), (hx - 1, hy - 2)], OUTLINE, 2)
        a.line([(hx - 5, hy - 2), (hx - 1, hy + 2)], OUTLINE, 2)
        a.line([(hx + 2, hy + 2), (hx + 6, hy - 2)], OUTLINE, 2)
        a.line([(hx + 2, hy - 2), (hx + 6, hy + 2)], OUTLINE, 2)
    else:
        for ex in (hx - 3.6, hx + 4.4):                                                              # two hollow cyan pits
            a.ellipse(ex, hy + 1.4, 3.4, 3.2, stone[0])
            a.ellipse(ex, hy + 1.2, 2.2, 2.2, GLOW[3])
            a.ellipse(ex + .4, hy + 1.6, 1, 1, GLOW[4])
    mx = hx + .4
    a.poly([(mx - 5.4, hy - 3.2), (mx + 5.4, hy - 3.6), (mx + 6.6, hy - 6.6), (mx + 3, hy - 5.4), (mx, hy - 6.4), (mx - 3, hy - 5.4), (mx - 6.6, hy - 6.4)], stone[0])   # a cracked mouth dragged down at the corners
    for k in range(4):
        a.line([(mx - 3.6 + k * 2.4, hy - 3.4), (mx - 3.6 + k * 2.4, hy - 5.2)], BONE[3], 1)
    return a

# --- mirageroc
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.


def mirageroc(clip, n):
    """Mirage Roc (elite, hovers): a vast blue-feathered bird with a gold breast, an orange crest and wing fringes that
    shimmer magenta. Mean: a cruel brow ridge over a hard magenta slit eye, a long deep-hooked beak. It beats its wings
    up and back, then dives with the talons forward and the beak wide; a mirage cannot fall like a bird: when it dies the
    wings go slack, the whole body breaks into drifting heat-haze bands and dithers away as it sinks, and only a few
    feathers and gold sparks reach the ground."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = dn
    a = Painter('mirageroc', st * 12 - w * 7 + recoil)
    flap = math.sin(ph * 1.5) if clip in ('idle', 'walk') else (1. if clip == 'attack' and n in (1, 2) else (-.7 if clip == 'attack' and n in (3, 4, 5) else (.2 if clip == 'hurt' else .6)))
    if clip == 'attack':
        flap = [.5, .9, 1, .4, -.8, -.5, -.1, .5][n]
    flap = flap * (1 - fall) - fall * .8
    base = 62
    lift = bob * 1.5 - fall * 38 + w * 3 - st * 4
    pitch = -st * .45 + w * .14 - fall * .5 + recoil * .03
    r = Rig(a, 0, base, pitch, lift)
    blue = [AZURE[0], AZURE[1], AZURE[2], AZURE[3], AZURE[3]]
    deep = [AZURE[0], AZURE[0], AZURE[1], AZURE[2], AZURE[2]]
    gold = [AMBER[0], AMBER[2], GOLD[2], GOLD[3], GOLD[4]]
    # the long tail
    for k in range(5):
        ang = 3.14 + (k - 2) * .17 + math.sin(ph) * .05 * (1 - fall) - fall * .5
        tip = polar(-14, base - 2, ang, 30 - abs(k - 2) * 2.6)
        r.poly([(-12, base + 1 - k * .5), tip, (-12, base - 5 + k * .5)], blue[1 + (k % 2)], outline=blue[0])
        r.ellipse(tip[0] + 1.8, tip[1], 2, 2, MIRAGE[2])
    # far wing
    sh = (1, base + 7)
    def wing(ramp, spread_k, tipcol):
        angc = mix(4.0, 1.55, (flap + 1) / 2)
        for k in range(8):
            ang = angc + (k - 3.5) * .15 * (1 + spread_k)
            ln = 34 + (3.5 - abs(k - 3.5)) * 2.6 - fall * 8
            tip = polar(sh[0], sh[1], ang, ln)
            mid1 = polar(sh[0], sh[1], ang + .09, ln * .5)
            mid2 = polar(sh[0], sh[1], ang - .09, ln * .5)
            r.poly([sh, polar(sh[0], sh[1], ang + .2, ln * .55), tip, polar(sh[0], sh[1], ang - .2, ln * .55)], ramp[1 + (k % 2)], outline=ramp[0])
            r.line([polar(sh[0], sh[1], ang, ln * .3), tip], ramp[3], 1)
            r.ellipse(tip[0] - math.cos(ang) * 1.6, tip[1] - math.sin(ang) * 1.6, 2.2, 2.2, tipcol)   # shimmering fringe
    wing(deep, .1, MIRAGE[1])
    # talons hang below the belly and reach forward on the strike
    for sd, ramp in ((-1, gold), (1, [GOLD[1], GOLD[2], GOLD[3], GOLD[4], GOLD[4]])):
        hip = (-2 + sd * 3, base - 8)
        foot = (1 + sd * 3 + st * 20 - w * 3, base - 16 - st * 2 + w * 2 + sd * .6)
        r.limb([hip, mixp(hip, foot, .5), foot], ramp, 3.2)
        for t in (-1, 0, 1):
            tip = (foot[0] + 3.4 + st * 2, foot[1] - 4 + t * 2.6 - st * 2)
            r.line([foot, tip], BONE[4], 2)
    # body
    r.ball(0, base, 17.4, 11, gold, -.1)
    r.ball(4, base - 2.6, 10.6, 6.6, [GOLD[1], GOLD[2], GOLD[3], GOLD[4], BONE[4]], -.08)
    for k in range(5):
        r.line([(-6 + k * 4, base + 9), (-4 + k * 4, base + 3)], AMBER[0], 1)
    r.ball(-4, base + 6, 11, 4.6, blue, -.12)                    # blue mantle across the back
    wing(blue, 0., MIRAGE[3])
    # neck and head
    hx, hy = 21 + st * 11 - w * 4 + fall * 2, base + 7 - st * 11 + w * 3 - fall * 6
    neck = bez((11, base + 3), (16 + st * 6, base + 9 - st * 4 + w * 2), (hx - 3, hy - 1.6), 8)
    r.taper(neck, gold, 8.4, 5.6)
    for sd in range(3):                                           # orange crest swept back
        c0 = (hx - 2 - sd * 1.5, hy + 4.6)
        tip = polar(c0[0], c0[1], 2.2 - sd * .35 + math.sin(ph) * .06 - fall * .3, 11 - sd * 1.6)
        r.poly([(c0[0] - 2.4, c0[1] - 1), tip, (c0[0] + 2.6, c0[1] - 1)], [AMBER[0], AMBER[1], AMBER[2], GOLD[2], GOLD[3]][1 + sd % 2], outline=AMBER[0])
    r.ball(hx, hy, 7.4, 6.4, gold, .1)
    gape = 3.2 if (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or fall > .3 else .5
    r.poly([(hx + 3, hy - 2.2 - gape), (hx + 15, hy - 3.6 - gape * .8), (hx + 9.4, hy - 5.8 - gape), (hx + 3, hy - 4.2 - gape)], GOLD[0], outline=AMBER[0])                  # lower mandible
    r.poly([(hx + 2.6, hy + 2.4), (hx + 10, hy + 2.2), (hx + 16.4, hy - 1.4), (hx + 14.6, hy - 6), (hx + 12, hy - 2.6), (hx + 3.4, hy - 2)], GOLD[3], outline=AMBER[0])            # hooked upper beak
    ex, ey = hx + 2.6, hy + 1.4
    if dying(clip, n):
        r.line([(ex - 2, ey - 1.8), (ex + 2, ey + 1.8)], OUTLINE, 2)
        r.line([(ex - 2, ey + 1.8), (ex + 2, ey - 1.8)], OUTLINE, 2)
    else:
        r.poly([(ex - 3, ey - .4), (ex, ey + 1.4), (ex + 3.4, ey - .2), (ex + 2.4, ey - 1.6), (ex - 1.6, ey - 1.8)], MIRAGE[3])
        r.ellipse(ex + .6, ey - .2, .7, 1.1, OUTLINE)
        r.poly([(ex - 4, ey + 3.4), (ex + 4.4, ey + .6), (ex + 4.4, ey + 2.6), (ex - 3, ey + 5.2)], blue[0])    # cruel brow ridge
    # dissipation: horizontal heat-haze bands slide sideways and an ordered dither eats the body away
    if clip == 'die' and n >= 2:
        arr = np.array(a.im)
        h_, w_ = arr.shape
        out = np.zeros_like(arr)
        for y in range(h_):
            sh_ = int(round(math.sin(y * .55 + n * 1.7) * 3.2 * fall))
            row = np.roll(arr[y], sh_)
            out[y] = row
        yy, xx = np.mgrid[0:h_, 0:w_]
        keep = BAYER[yy % 4, xx % 4] > (fall ** 1.1) * 1.08 - .08 * (n < 4)
        out = np.where(keep, out, 0).astype(np.uint8)
        a.im = Image.fromarray(out, 'P')
        a.d = ImageDraw.Draw(a.im)
        if n >= 6:                                               # what reaches the ground: a few feathers and gold sparks
            late = n - 6                                          # the last feathers settle and one spark winks out
            for k, (fx, ang) in enumerate(((-9, .25), (-1, -.15), (7, .35), (14, -.3), (-16, -.4))):
                tip = polar(fx + late * (1 - k % 2 * 2) * .8, 2, ang - late * .12 * (1 + k % 2), 9 - k - late * 1.2)
                a.poly([(fx - 1, 1.4), tip, (fx + 1.6, 1.4)], blue[2 + k % 2], outline=blue[0])
            for fx in ((-5, 3, 10) if late == 0 else (3,)):
                a.ellipse(fx, 3 + (fx % 3), 1.2, 1.2, GOLD[3])
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
        np.savez_compressed(ROOT / f'scripts/lapis_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/lapis_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'lapis_{kind}.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    live = json.loads(MANIFEST.read_text())
    assert live['kinds'][-5:] == VILLAGERS, 'villager entries moved'
    villagers = {k: (live['sprites'][k], live['tops'][k]) for k in VILLAGERS}
    meta = json.loads(json.dumps(live))
    meta['artStyle'] = 'lapis-slime'
    proof, atlases = {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip] == dict(fps=fps, n=count, row=row, editorStart=offset), clip
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['sprites'][kind] = saved[kind]
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for k in VILLAGERS:   # the villager NPCs must come out exactly as they went in
        assert (meta['sprites'][k], meta['tops'][k]) == villagers[k] and k not in (meta.get('kindFrames') or {})
    for kind, atlas in atlases.items():
        dest = atlas_path(kind)
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames and derived health-bar tops.', flush=True)


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
    """Measure each kind's art on a scratch canvas: pass A (anchor x 100) gives the left reach, pass B (anchor x 92) the right."""
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW and (len(sys.argv) < 3 or k in sys.argv[2:])]:
        old_kf = KIND_FRAMES.get(kind)
        left = right = up = 0
        for axs in (100, 92):
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
