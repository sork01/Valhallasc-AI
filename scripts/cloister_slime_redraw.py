#!/usr/bin/env python3
"""Flooded Cloister (Drowned Cathedral wing 1) slime-style native PixelFlow sources; preview | build | export | verify.

Greenmeadow shading and eyes, material-appropriate motion and a death that fits each kind: armour buckles and
topples, the cantor's robe crumples empty, the leech goes limp, the bell cracks and tips, the Mournsister dissolves,
the root abbot splits and wilts, the Choirmother swoons while her singers pop, the Bound Singer drifts away.
Every grounded foot, hem or base rests exactly on the anchor row (y=0 on the Painter, row 90), so nothing floats.

`cathedral.txt` is SHARED by 146 kinds: export replaces only this module's eight `sprites`/`tops` entries and asserts
that the rest of the manifest is unchanged. `tidetemplar` and `tidecantor` are also spawned in the Coral Reliquary and
the Grand Nave, so those zones inherit the new art for those two kinds.
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
from wyrd_slime_v1_redraw import Painter, motion, mix
from deep_slime_redraw import (PALETTE as DEEP, sm, bez, taper, erase, rot, BAYER,
                               TEAL, BLUE, BROWN, GOLD, BONE, GREEN, PLATE, FUR, PURPLE, OLIVE, RAG, BONE as BN)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/cloister-slime'
REGISTRY = ROOT/'scripts/cloister_slime_sources.txt'
MANIFEST = ASSETS/'cathedral.txt'
PREFIX = 'valhallasc_cloister_slime_style_'
KINDS = ['tidetemplar', 'tidecantor', 'tideleech', 'bellkeeper', 'mournsister', 'rootabbot', 'choirmother', 'choirsinger']
NAMES = dict(tidetemplar='Tide Templar', tidecantor='Tide Cantor', tideleech='Tide Leech', bellkeeper='Bellkeeper',
             mournsister='Mourning Sister', rootabbot='Root Abbot', choirmother='Choirmother', choirsinger='Bound Singer')
W = H = 96
AX, AY = 48, 90
KIND_FRAMES = {}   # kind -> (w, h, ax, ay); empty = every kind on the zone-wide frame (docs/kind-frames.md, scripts/kindframe.py)


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


CLIPS = old.CLIPS
PALETTE = DEEP[:] + ['#5a1f38', '#a8456e', '#e07a9a', '#f6b0c4', '#ffe4ec',      # 95-99 rose hair
                     '#2e0f1c', '#6a2038', '#a63a56', '#d8708a', '#ffb0be']      # 100-104 maroon
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
PINK = list(range(95, 100))
MAROON = list(range(100, 105))
OUTLINE, WHITE, CREAM, BLUSH = 1, 2, 3, 4


class Rig:
    """Rigid body: knees/hips drop (buckle), then the whole piece topples about a pivot and rests on the floor."""
    def __init__(self, f, pivot=(-6, 0), sign=1, angle=1.45, lift=10, buckle=.28, start=.35):
        self.pivot, self.angle0, self.buckle = pivot, sign*angle, buckle
        self.tb = sm(f/(start+.25))
        self.tt = sm((f-start)/(1-start))
        self.angle = self.angle0*self.tt
        self.lift = lift*self.tt

    def P(self, x, y):
        y = y*(1-self.buckle*self.tb)
        px, py = self.pivot
        c, s = math.cos(self.angle), math.sin(self.angle)
        dx, dy = x-px, y-py
        return (px+dx*c-dy*s, py+dx*s+dy*c+self.lift)

    def pts(self, seq):
        return [self.P(*p) for p in seq]


def sparkle(a, x, y, col=TEAL[4]):
    a.line([(x-2, y), (x+2, y)], col, 1)
    a.line([(x, y-2), (x, y+2)], col, 1)


def erase_rising(a, f):
    """Dissolve from the top down: the head goes first, the base last; at f=1 nothing drawn so far remains."""
    arr = np.array(a.im)
    for y in range(H):
        h = max(0, min(1, (AY-y)/62))
        p = max(0, min(1, f*1.8-(1-h)*.8))
        for x in range(W):
            if arr[y, x] and BAYER[y % 4][x % 4]/16 < p:
                arr[y, x] = 0
    a.im = Image.fromarray(arr, 'P')
    a.d = ImageDraw.Draw(a.im)


# ----------------------------------------------------------------------------------------------
# Tide Templar: a fish-knight in rigid teal armour. Joints swing, the trident thrusts; on death the legs
# buckle and the whole suit topples backwards, trident clattering down.
# ----------------------------------------------------------------------------------------------
def templar(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    R = Rig(fall, pivot=(0, 0), sign=-1, angle=.62, lift=0, buckle=.5, start=.3)
    P = R.P
    a = Painter(cx=38+recoil+(lunge*.3 if clip == 'attack' else 0)+R.tt*2)
    hy = 44+bob*.4
    # white fin crest behind the helmet
    a.poly(R.pts([(-8, hy+4), (-20, hy+10), (-22, hy-1), (-17, hy-9), (-8, hy-6)]), BONE[2])
    a.line(R.pts([(-9, hy+2), (-19, hy+6)]), BONE[3], 1)
    a.line(R.pts([(-9, hy-2), (-19, hy-3)]), BONE[1], 1)
    # legs: planted feet sit exactly on the floor
    for sg in (-1, 1):
        sw = math.sin(n*math.pi/4+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sw)*3
        hip, knee, foot = (sg*5, 18), (sg*5+sw*2.5, 10+lift*.5), (sg*6+sw*4+1, 3+lift)
        a.limb(R.pts([hip, knee, foot]), TEAL if sg > 0 else TEAL[:4], 5)
        fx, fy = P(*foot)
        fy = max(3, fy)
        a.ball(fx+1.5, fy, 6, 3, TEAL if sg > 0 else TEAL[:4])
        a.line([(fx-2, fy+2), (fx+5, fy+2)], GOLD[2], 1)
    # kilt and torso
    a.poly(R.pts([(-9, 20), (9, 20), (12, 9), (-12, 9)]), MAROON[2])
    a.poly(R.pts([(-9, 20), (-2, 20), (-3, 9), (-12, 9)]), MAROON[1])
    for dx in (-5, 1, 7):
        a.line(R.pts([(dx, 19), (dx*1.25, 10)]), MAROON[4], 1)
    a.ball(*P(0, 29), 12, 10.5, TEAL)
    a.line(R.pts([(-11, 21), (11, 21)]), GOLD[2], 2)
    a.ball(*P(0, 21), 3, 2.6, GOLD)
    for sg in (-1, 1):
        a.ball(*P(sg*13, 35), 4.4, 4.4, GOLD)
    # far arm
    sh, el, hand = P(-12, 32), P(-17, 27-lunge*.2), P(-18, 21+(1.5 if clip == 'hurt' else 0))
    a.limb([sh, el, hand], TEAL[:4], 4)
    a.ball(*hand, 3.2, 3.2, BONE)
    # head: helmet with a gold horn, big eyes
    a.ball(*P(1, hy), 12, 10.5, TEAL)
    hx, hy2 = P(1, hy)
    a.poly(R.pts([(3, hy+9), (12, hy+19), (8, hy+8)]), GOLD[1])
    a.poly(R.pts([(4, hy+9), (11, hy+17), (8, hy+9)]), GOLD[3])
    a.face(hx, hy2-1, clip, n, .75)
    # right arm + trident (thrust forward on attack)
    ang = [.12, .0, -.25, .6, 1.15, 1.05, .6, .16][n] if clip == 'attack' else .12+(.1 if clip == 'hurt' else 0)
    hand = (21+(lunge*1.3 if clip == 'attack' else 0), 28+(5 if clip == 'attack' and n in (1, 2) else 0))
    sh = (11, 33)
    a.limb(R.pts([sh, ((sh[0]+hand[0])/2+1, (sh[1]+hand[1])/2-2), hand]), TEAL, 4)
    drop = sm(fall/.65) if clip == 'die' else 0
    if drop > 0:                                # the hand lets go: the trident clatters to the floor ahead of the body
        hand = (mix(hand[0], 16, drop), mix(hand[1], 3, drop))
        ang = mix(ang, 1.52, drop)
    d = (math.sin(ang), math.cos(ang))
    nrm = (-d[1], d[0])
    base = (hand[0]-d[0]*9, hand[1]-d[1]*9)
    tip = (hand[0]+d[0]*19, hand[1]+d[1]*19)
    T = (lambda pts: list(pts)) if drop > 0 else R.pts
    a.line(T([base, tip]), BROWN[0], 4)
    a.line(T([base, tip]), BROWN[2], 2)
    for off in (-5, 0, 5):
        s0 = (tip[0]+nrm[0]*off*(1 if off else 0), tip[1]+nrm[1]*off)
        s1 = (s0[0]+d[0]*(8 if off == 0 else 5), s0[1]+d[1]*(8 if off == 0 else 5))
        a.line(T([s0, s1]), GOLD[0], 3)
        a.line(T([s0, s1]), GOLD[3], 1)
    a.line(T([(tip[0]-nrm[0]*5, tip[1]-nrm[1]*5), (tip[0]+nrm[0]*5, tip[1]+nrm[1]*5)]), GOLD[2], 2)
    if drop == 0:
        a.ball(*P(*hand), 3.6, 3.6, BONE)
    if clip == 'attack' and 4 <= n <= 5:
        for k in range(3):
            tx, ty = P(tip[0]+d[0]*5+k*1.5, tip[1]+d[1]*5+(k-1)*4)
            sparkle(a, tx, ty, TEAL[4])
    if clip == 'die' and fall > .55:
        for k in range(3):
            sparkle(a, -2+k*9, 12+(k % 2)*3, TEAL[3])
    return a


# ----------------------------------------------------------------------------------------------
# Tide Cantor: a hooded robe with bead chains. The robe flows and the chains whip; on death the robe crumples
# empty onto the floor, the hood sinks into it and the beads scatter.
# ----------------------------------------------------------------------------------------------
def cantor(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    a = Painter(cx=42+recoil)
    sway = math.sin(n*math.pi/4)*1.6 if clip == 'walk' else 0
    h = mix(1, .34, t)
    hw = mix(15, 24, t)
    top = 33*h
    a.poly([(-8+sway*.4, top), (8+sway*.4, top), (hw, 0), (-hw, 0)], BLUE[1])
    a.poly([(-8+sway*.4, top), (-1, top), (-2, 0), (-hw, 0)], BLUE[0])
    for dx, col in ((-7, BLUE[0]), (2, BLUE[2]), (9, BLUE[0])):
        a.line([(dx*.45+sway*.4, top-2), (dx*mix(1, 1.5, t), 1)], col, 1)
    a.line([(-hw+1, 2), (hw-1, 2)], GOLD[2], 2)
    a.ball(0, 27*h+1, 11, 10*h+1, BLUE)
    if clip == 'die' and fall > .3:      # wrinkles of the empty cloth
        for k, dx in enumerate((-10, -2, 8)):
            a.line([(dx, 9*h+4), (dx+3+k, 4), (dx+6, 7*h)], BLUE[3 if k % 2 else 0], 1)
    a.line([(-11, 18*h), (11, 18*h)], GOLD[2], 2)
    a.ball(0, 18*h, 3, 2.6, GOLD)
    # sleeves, hands and bead chains
    hands = []
    for sg in (-1, 1):
        ph = n*math.pi/4+(0 if sg > 0 else math.pi)
        hx = sg*(19 if clip != 'die' else mix(19, 24, t))+(math.sin(ph)*2 if clip == 'walk' else 0)
        hy = mix(23+bob*.5, 3, t)
        if clip == 'attack':
            hx = sg*(19+[0, 1, 2, 7, 10, 8, 4, 1][n]*(1 if sg > 0 else .3))
            hy = 23+[0, 3, 7, 3, -1, -2, 0, 0][n]*(1 if sg > 0 else .4)
        hands.append((hx, hy, sg))
        a.limb([(sg*9, 31*h), (sg*14, 27*h-1), (hx, hy)], BLUE[:4] if sg < 0 else BLUE, 5)
        a.ball(hx, hy, 3.6, 3.6, BONE)
    for hx, hy, sg in hands:
        beads = 6
        for k in range(1, beads+1):
            s = k/beads
            if clip == 'attack' and sg > 0 and n >= 3:
                bx, by = hx+k*3.5, hy-1-math.sin(s*math.pi)*3
            elif clip == 'die':
                sc = sm(max(0, (fall-.25)/.75))
                bx, by = hx+sg*(k*1.8)*(.2+sc), 1.8+(k % 2)*1.2*sc if sc > .15 else hy-k*3.6
                by = mix(hy-k*3.4, 2, min(1, sc*1.8))
            else:
                swing = math.sin(n*.9+k*.5+sg)*1.2 if clip != 'attack' else 0
                bx, by = hx+sg*(1.5+swing)+sg*math.sin(s*3)*1.6, max(2, hy-k*3.3)
            a.ball(bx, max(1.8, by), 1.9, 1.9, PLATE)
    # hood and face
    hy = mix(45+bob*.4, 11, t)
    hx = mix(0, 9, t)
    a.ball(hx, hy, 12.5, mix(11, 7.5, t), BLUE)
    a.ball(hx+1, hy-1, 8.6, mix(7.6, 5, t), BONE)
    if t < .5:
        a.face(hx+1, hy+mix(0, -3, t*2), clip, n, .7)
        if clip == 'attack' and 2 <= n <= 5:
            a.ellipse(hx+1, hy-5.5, 2.4, 1.8, 1)
    else:
        a.eye(hx-1, hy, 'die', 6, .6)
    a.ball(hx, hy+mix(10, 5, t), 3.5, 3, GOLD)
    if clip == 'attack' and 3 <= n <= 5:
        for k in range(3):
            sparkle(a, 24+k*5+(n-3)*4, 34+k*4, TEAL[4])
    return a


# ----------------------------------------------------------------------------------------------
# Tide Leech: a soft segmented crawler. It inches along in a wave, rears and bites; on death it goes limp and flat.
# ----------------------------------------------------------------------------------------------
def leech(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    a = Painter(cx=42+recoil)
    N = 9
    rear = 1-t
    head_x = 25+(lunge*1.1 if clip == 'attack' else 0)+(-recoil*.5 if clip == 'hurt' else 0)
    head_y = mix(18+bob*.7+(4 if clip == 'attack' and n in (1, 2) else 0)+(-3 if clip == 'attack' and n in (4, 5) else 0), 8, t)
    segs = []
    waves = [max(0, math.sin(n*math.pi/4-i*.85))*3.6 if clip == 'walk' else 0 for i in range(N)]
    floor = min(waves)                           # at least one segment is always flat on the ground
    for i in range(N):
        s = i/(N-1)
        r = 5.6+3.4*math.sin(math.pi*min(1, s*1.05))
        x = mix(-27+i*6.0, -30+i*6.6, t)
        ry = max(2, round(mix(r, r*.5, t)))          # integer radius: the lowest pixel row is then exactly the floor
        wave = waves[i]-floor
        rise = (head_y-12)*sm((i-4.5)/3.8)*rear if i > 4 else 0
        y = ry+wave+max(0, rise)
        segs.append((x, y, mix(r, r*1.2, t), ry))
    for i, (x, y, rx, ry) in enumerate(segs):
        a.ball(x, y, rx, ry, GREEN)
        a.ellipse(x+rx*.28, y-ry*.45, rx*.55, ry*.42, BONE[3])           # pale belly band
        a.line([(x-rx*.5, y+ry*.7), (x+rx*.2, y+ry*.9)], GREEN[3], 1)
    # head
    hx, hy = head_x, head_y
    a.ball(hx, hy, 11, mix(10, 6.5, t), GREEN)
    gape = 2+max(0, lunge)*1.5 if clip == 'attack' else 1.5
    if clip == 'die':
        gape = 2+3*t
    # open mouth with teeth, a red throat
    a.ball(hx+8, hy-3, 6.5, 4.2+gape*.7, MAROON)
    for k in range(3):
        a.poly([(hx+4+k*3, hy-1.5+gape*.4), (hx+5.5+k*3, hy-4+gape*.4), (hx+7+k*3, hy-1.5+gape*.4)], BONE[4])
    if t < .9:
        a.eye(hx-1, hy+3, clip, n, .78)
        a.ellipse(hx-8, hy-1, 2.2, 1.2, BLUSH)
    if clip == 'die' and fall > .6:
        a.line([(hx-4, hy+1), (hx, hy+1)], OUTLINE, 1)
    if clip == 'attack' and 3 <= n <= 5:
        a.poly([(hx+16, hy-2), (hx+22, hy-5), (hx+20, hy+1)], TEAL[3])
    return a


# ----------------------------------------------------------------------------------------------
# Bellkeeper: a rigid teal bell on gold feet with a hammer. The bell tilts as it walks and rings when it strikes;
# on death cracks run through it, chips fly off, the hammer drops and the bell telescopes down into a dented heap.
# ----------------------------------------------------------------------------------------------
def bellkeeper(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    slump = sm(fall/.8)
    a = Painter(cx=38+recoil)
    tilt = math.sin(n*math.pi/4)*2.4 if clip == 'walk' else math.sin(n*math.pi/3)*1.2 if clip == 'idle' else 0
    h = mix(1, .46, slump)
    base_y = mix(8, 5, slump)
    if fall < .5:
        for sg in (-1, 1):
            sw = math.sin(n*math.pi/4+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
            a.ball(sg*11+sw*3, 3+max(0, sw)*3, 4.2, 3, GOLD)
    top = base_y+22*h
    a.poly([(-19, base_y), (19, base_y), (13+tilt*.3, top), (-13+tilt*.3, top)], TEAL[1])
    a.poly([(-19, base_y), (-6, base_y), (-5, top), (-13+tilt*.3, top)], TEAL[0])
    a.ball(tilt*.3, base_y+23*h, mix(14, 17, slump), 13*h+1, TEAL)
    a.ball(0, base_y, 20, 5, GOLD)
    if clip == 'die':
        a.line([(10, base_y+4), (10, base_y-4)], OUTLINE, 2)              # the rim breaks
    wy = mix(base_y+19, 9, slump)
    a.ball(1+tilt*.2, wy, 10.5, 10.5, BONE)
    a.face(1+tilt*.2, wy, clip, n, .62)
    if clip != 'die':
        a.line([(-4, 42), (3, 43), (8, 41)], TEAL[4], 1)
        for k in range(3):
            a.ball(-12+k*12, 12, 2, 2, GOLD)
    a.ball(tilt*.4, base_y+38*h+1, 4*mix(1, 1.15, slump), 4*mix(1, .8, slump), GOLD)
    # hammer: handle + head, swung overhead then smashed down
    if clip == 'attack':
        ang = [.35, -.3, -.9, .05, 1.0, 1.25, 1.1, .6][n]
        hand = (21+[0, -2, -3, 2, 5, 6, 5, 2][n], 26+[0, 5, 10, 8, 0, -4, -2, 2][n])
    else:
        ang = .35+(.15 if clip == 'hurt' else 0)+(math.sin(n*math.pi/3)*.07 if clip == 'idle' else 0)
        hand = (23, 25+bob*.6)
    if clip == 'die':
        drop = sm(fall/.5)
        ang = mix(.35, 1.55, drop)
        hand = (mix(23, 16, drop), mix(25, 3, drop))
    d = (math.sin(ang), math.cos(ang))
    nrm = (-d[1], d[0])
    tip = (hand[0]+d[0]*16, hand[1]+d[1]*16)
    base = (hand[0]-d[0]*7, hand[1]-d[1]*7)
    if clip != 'die' or fall < .3:
        a.limb([(15, 31), ((15+hand[0])/2, (31+hand[1])/2+2), hand], TEAL, 4)
    a.line([base, tip], BROWN[0], 4)
    a.line([base, tip], BROWN[2], 2)
    head = [(tip[0]+nrm[0]*7+d[0]*5, tip[1]+nrm[1]*7+d[1]*5), (tip[0]-nrm[0]*7+d[0]*5, tip[1]-nrm[1]*7+d[1]*5),
            (tip[0]-nrm[0]*7-d[0]*5, tip[1]-nrm[1]*7-d[1]*5), (tip[0]+nrm[0]*7-d[0]*5, tip[1]+nrm[1]*7-d[1]*5)]
    a.poly(head, PLATE[1])
    a.line([head[0], head[1]], PLATE[4], 1)
    a.line([head[2], head[3]], PLATE[0], 1)
    if clip != 'die' or fall < .3:
        a.ball(*hand, 3.6, 3.6, BONE)
    if clip == 'attack' and n in (4, 5, 6):
        k = n-4
        for sg in (-1, 1):
            a.line([(tip[0]+sg*(7+k*2)*(1 if sg < 0 else .6), 3), (tip[0]+sg*(11+k*2)*(1 if sg < 0 else .6), 5)], PLATE[4], 1)
        a.line([(-23-k*2, 34), (-27-k*2, 38)], GOLD[3], 1)
        a.line([(-25-k*2, 28), (-30-k*2, 28)], GOLD[3], 1)
    # cracks spreading through the bell, then chips flying off
    if clip == 'die' or (clip == 'hurt' and n >= 2):
        c = min(1, fall*2.4) if clip == 'die' else .35
        zig = [(1, 40), (-3, 35), (2, 30), (-4, 25), (1, 19), (-3, 14), (2, 9)]
        zig = [(x, base_y+(y-8)*h) for x, y in zig]
        cut = max(2, int(len(zig)*c))
        a.line(zig[:cut], OUTLINE, 2)
        if cut > 3:
            a.line([(x+8, y-2) for x, y in zig[1:cut]], OUTLINE, 1)
    if clip == 'die':
        for k, (x0, y0, vx, vy) in enumerate(((-12, 26, -15, 18), (10, 30, 17, 22), (0, 36, 5, 28))):
            sp = max(0, min(1, (fall-.12-k*.07)/.4))
            if sp > 0:
                x, y = x0+vx*sp*1.4, max(2, y0+vy*sp-40*sp*sp)
                a.poly([(x-3, y), (x+3, y+1), (x, y+4)], TEAL[2])
                a.line([(x-3, y), (x, y+4)], TEAL[4], 1)
    if clip == 'die' and fall > .55:
        for k, dx in enumerate((-14, 4, 16)):         # dust drifts up off the dented bell
            a.ellipse(dx+math.sin(k*2+fall*5)*2, 11+(fall-.55)*22+k*4, 1.2, 1.0, BONE[3])
    return a


# ----------------------------------------------------------------------------------------------
# Mourning Sister: a veiled ghost with a lantern. Her veil trails along the floor; on death the lantern falls,
# goes dark and she dissolves.
# ----------------------------------------------------------------------------------------------
def sister(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    a = Painter(cx=43+recoil)
    sway = math.sin(n*math.pi/4)*2 if clip == 'walk' else math.sin(n*math.pi/3)*.7
    h = mix(1, .62, t)
    top = (46+bob*.4)*h
    # tattered hem: points all reach the floor
    tips = [(-18, 0), (-12, 3), (-6, 0), (0, 3), (6, 0), (12, 3), (18, 0)]
    veil = [(-8+sway*.3, top-2), (8+sway*.3, top-2), (14+sway*.6, 26*h), (20+sway, 3)]
    for k, (tx, ty) in enumerate(tips[::-1]):
        veil.append((tx*mix(1, 1.15, t)+sway*.7*(1-k/7), max(0, ty+(math.sin(n*.9+k)*1.2 if clip != 'die' else 0))))
    veil += [(-20+sway, 3), (-14+sway*.6, 26*h)]
    a.poly(veil, FUR[2])
    a.poly([(-8+sway*.3, top-2), (0, top-2), (-1, 3), (-9, 0), (-20+sway, 3), (-14+sway*.6, 26*h)], FUR[1])
    for dx in (-8, 2, 10):
        a.line([(dx*.5+sway*.3, 34*h), (dx*1.1+sway*.8, 5)], FUR[3] if dx > 0 else FUR[0], 1)
    a.ball(0, 27*h, 10.5, 10*h, FUR[:4])
    # lantern arm
    hx = 19+(lunge*.8 if clip == 'attack' else 0)
    hy = 24+(7 if clip == 'attack' and 2 <= n <= 5 else 0)+bob*.3
    if clip == 'die':
        hy = mix(24, 11, sm(fall/.6))
        hx = mix(19, 22, t)
    a.limb([(8, 32*h), (14, 28*h), (hx, hy)], FUR, 4)
    a.ball(hx, hy, 3.4, 3.4, BONE)
    lamp = hy-6
    glow = 1 if clip != 'die' else max(0, 1-fall*2.5)
    if glow > 0:
        a.ellipse(hx, lamp, 8+(4 if clip == 'attack' and 3 <= n <= 5 else 0), 8, TEAL[1])
    a.line([(hx, hy-1), (hx, lamp+4)], GOLD[0], 1)
    a.poly([(hx-4, lamp+3), (hx+4, lamp+3), (hx+5, lamp-5), (hx-5, lamp-5)], GOLD[1])
    a.ball(hx, lamp-1, 3.2, 3.2, TEAL if glow > .2 else PLATE)
    a.line([(hx-3, lamp+3), (hx+3, lamp+3)], GOLD[3], 1)
    # head under the veil, with a rose
    hy2 = mix(46+bob*.4, 29, t)
    a.ball(0, hy2, 13, 12*h**.5, FUR)
    a.ball(1, hy2-2, 8.6, 7.8, BONE)
    if t < .6:
        a.face(1, hy2-1, clip, n, .68)
    else:
        a.eye(1, hy2-1, 'die', 6, .6)
    a.ball(-2, hy2+11, 3.6, 3.2, PINK)
    a.ellipse(-2.5, hy2+11.5, 1.4, 1.4, PINK[4])
    if clip == 'attack' and 3 <= n <= 5:
        for k in range(4):
            a.ellipse(hx+3+k*3, lamp-3-k*2+(n-3)*(-3), 1.4, 1.8, TEAL[3])
    if clip == 'die':
        erase_rising(a, max(0, (fall-.15)/.8))
        a.ball(hx, 3, 3.5, 3, PLATE)            # the dark lantern is all that stays
        a.poly([(hx-3, 5), (hx+3, 5), (hx+2.5, 8), (hx-2.5, 8)], GOLD[1])
        for k in range(int(fall*4)):
            a.ellipse(-14+k*9, 12+k*5+fall*10, 1.4, 1.8, TEAL[3])
    return a


# ----------------------------------------------------------------------------------------------
# Root Abbot: a wooden monk in a leaf hood with a tentacle beard. Legs step, arms slam roots up from the floor;
# on death the trunk cracks and splits lengthwise into two logs that fall apart, the hood drops on top and every
# leaf wilts.
# ----------------------------------------------------------------------------------------------
def abbot(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    wilt = fall > .45
    LEAF = OLIVE if wilt else GREEN
    split = sm((fall-.3)/.55) if clip == 'die' else 0
    a = Painter(cx=43+recoil)
    dying = clip == 'die'
    # legs with root toes (they buckle first and then vanish under the falling logs)
    if split < .7:
        for sg in (-1, 1):
            sw = math.sin(n*math.pi/4+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
            lift = max(0, sw)*3
            hipy = mix(21, 11, sm(fall/.4))
            hip, knee, foot = (sg*8, hipy), (sg*11+sw*2, mix(12, 8, t)+lift*.5), (sg*12+sw*4, 3+lift)
            if dying:
                foot = (sg*mix(12, 16, t), 3)
            ramp = BROWN if sg > 0 else BROWN[:4]
            a.limb([hip, knee, foot], ramp, 8)
            a.ball(foot[0]+1, foot[1], 7, 3, ramp)
            for k, dx in enumerate((-6, 0, 6)):
                a.poly([(foot[0]+dx-1.5, foot[1]-1), (foot[0]+dx+(k-1)*2+2, 0), (foot[0]+dx+3, foot[1]-1)], BROWN[1])
    # arms: branches ending in knuckles (they flop onto the floor when it dies)
    for sg in (-1, 1):
        hx = sg*26
        hy = 25+bob*.3
        if clip == 'attack':
            up = [4, 14, 24, 17, -17, -19, -14, -4][n]
            hy = 25+up if sg > 0 else 25+up*.8
            hx = sg*(24+[0, -3, -5, 0, 8, 12, 9, 2][n]*(1 if sg > 0 else .6))
        if dying:
            hx = sg*mix(26, 33, t)
            hy = mix(25, 4, sm(fall/.7))
        if clip == 'walk':
            hy += math.sin(n*math.pi/4+(math.pi if sg > 0 else 0))*2
        sy = mix(36, 12, split)
        a.limb([(sg*13, sy), (sg*(19+((hx-sg*26)*.2)), (sy+hy)/2+3), (hx, hy)], BROWN if sg > 0 else BROWN[:4], 8)
        a.ball(hx, hy, 5, 5, BROWN)
        for k in range(3):
            a.line([(hx+sg*2, hy+2-k*2), (hx+sg*(6+k), hy+3-k*3)], BROWN[0], 2)
    # trunk: one piece while alive; a crack opens, then two logs fall outward
    if not dying or fall < .3:
        a.ball(0, 31+bob*.3, 16, 15, BROWN)
        if dying:
            c = min(1, fall/.25)
            a.line([(1, 45), (-2, 39), (2, 33), (-1, 26)][:max(2, int(4*c))], OUTLINE, 2)
        a.ellipse(0, 28+bob*.3, 6.5, 6.5, LEAF[1])
        a.ellipse(-1.5, 29.5, 2.4, 2.4, LEAF[4])
        a.line([(-16, 23), (16, 23)], LEAF[1], 2)
        for dx in (-11, 0, 10):
            a.poly([(dx-2, 22), (dx+3, 26), (dx+2, 21)], LEAF[3])
    else:
        for sg in (-1, 1):
            th = .08+split*1.42
            b = (sg*(5+split*4), 6)
            top = (b[0]-sg*30*math.sin(th), b[1]+30*math.cos(th)*mix(1, .9, split))
            ramp = BROWN if sg > 0 else BROWN[:4]
            a.line([b, top], ramp[0], 13)
            a.line([b, top], ramp[2], 11)
            a.line([(b[0]-sg*2, b[1]+2), (top[0]-sg*2, top[1]-2)], ramp[3], 2)
            a.ball(*top, 6, 6, ramp)
            a.ellipse(top[0], top[1], 3, 3, ramp[1])
            if split > .2:
                a.poly([(top[0]-3, top[1]-4), (top[0]+sg*1, top[1]-9), (top[0]+3, top[1]-4)], BROWN[3])   # splinters
    # head with hood and beard: it drops onto the logs
    drop = sm(fall/.85)
    hy = mix(47+bob*.4, 20, drop)
    hx = mix(0, 4, drop)
    a.ball(hx, hy, 10.5, 9.5, BROWN)
    for j, dx in enumerate((-7, -2.5, 2.5, 7)):
        sw = math.sin(n*.8+j*1.1)*2 if not dying else 0
        path = bez((hx+dx, hy-6), (hx+dx*1.4+sw, hy-15*(1-t*.4)), (hx+dx*1.7+sw*1.3, hy-23*(1-t*.55)), 6)
        path = [(x, max(1.5, y)) for x, y in path]
        taper(a, path, LEAF, 5, 2)
    a.ball(hx, hy+9, 11.5, 6.5, LEAF)
    a.ellipse(hx+1, hy+15, 4, 2.4, LEAF[3])
    a.face(hx, hy+1, clip, n, .72)
    if clip == 'attack' and 4 <= n <= 6:
        k = n-4
        for dx in (14, 24, 34):
            a.poly([(dx-3, 0), (dx+k, 8+k*3), (dx+3, 0)], BROWN[1])
            a.poly([(dx-1, 1), (dx+k, 7+k*3), (dx+1, 1)], BROWN[3])
    if dying:
        for j in range(int(fall*7)):
            a.poly([(-26+j*7, 14-j % 3*3), (-23+j*7, 17-j % 3*3), (-21+j*7, 13-j % 3*3)], OLIVE[2])
    return a


# ----------------------------------------------------------------------------------------------
# Choirmother: a robed matriarch with rose hair, a crown and a hem of pearls, ringed by singing ghosts.
# In death the singers pop one by one while she swoons and the robe pools around her.
# ----------------------------------------------------------------------------------------------
def mother(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    t = sm(fall)
    a = Painter(cx=45+recoil)
    sway = math.sin(n*math.pi/4)*1.5 if clip == 'walk' else 0
    h = mix(1, .5, t)
    hw = mix(19, 27, t)
    top = 36*h
    # hair bun behind the head
    hx = mix(0, 11, t)
    hy = mix(50+bob*.4, 17, sm(fall/.9))
    a.ball(hx-2, hy+6, 12, 12, PINK)
    for sg in (-1, 1):
        a.ball(hx+sg*13, hy-3, 4.5, 6.5, PINK)
    a.poly([(-9+sway*.3, top), (9+sway*.3, top), (hw, 0), (-hw, 0)], TEAL[1])
    a.poly([(-9+sway*.3, top), (-1, top), (-2, 0), (-hw, 0)], TEAL[0])
    for dx in (-9, 3, 11):
        a.line([(dx*.4+sway*.3, top-3), (dx*mix(1.4, 1.8, t), 3)], TEAL[3] if dx > 0 else TEAL[0], 1)
    a.ball(0, 30*h+1, 12, 11*h+1, TEAL)
    a.line([(-12, 19*h), (12, 19*h)], GOLD[2], 3)
    a.ball(0, 19*h, 3.2, 3.2, GOLD)
    scatter = sm(max(0, (fall-.3)/.6))
    for k in range(-4, 5):
        px = k*hw/4.4
        py = 2+(abs(k) % 2)*0
        if clip == 'die' and abs(k) % 2:
            px *= mix(1, 1.3, scatter)
        a.ball(px, 2, 2.2, 2, BONE)
    # arms (open hands) and the chorus
    for sg in (-1, 1):
        hxp = sg*(21+(lunge*1.2 if clip == 'attack' and sg > 0 else 0))
        hyp = mix(30+bob*.4+(math.sin(n*math.pi/4+sg)*1.5 if clip == 'walk' else 0), 8, t)
        if clip == 'attack':
            hyp += [0, 3, 6, 6, 2, 0, 0, 0][n]
        a.limb([(sg*10, 37*h), (sg*16, 34*h), (hxp, hyp)], TEAL if sg > 0 else TEAL[:4], 5)
        a.ball(hxp, hyp, 3.6, 3.6, BONE)
    # face under a crown
    a.ball(hx, hy, 11.5, 10.5, BONE)
    a.face(hx, hy-1, clip, n, .75)
    if clip == 'attack' and 1 <= n <= 5:
        a.ellipse(hx, hy-7, 3, 2.4+(n % 2), 1)
    cy = hy+10+(t*-5)
    for dx, hh in ((-6, 6), (0, 9), (6, 6)):
        a.poly([(hx+dx-3, cy), (hx+dx, cy+hh), (hx+dx+3, cy)], GOLD[2])
    a.line([(hx-8, cy), (hx+8, cy)], GOLD[1], 2)
    a.ellipse(hx, cy+4, 1.7, 1.7, PINK[3])
    # four singers
    spots = [(-30, 52), (-26, 34), (30, 54), (27, 36)]
    for i, (sx, sy) in enumerate(spots):
        life = 1
        if clip == 'die':
            life = (fall-.12*(i+1))/.12
        if life <= -0 and clip == 'die':
            life = 0
        if clip == 'die' and life >= 1:
            continue
        bobs = math.sin(n*math.pi/3+i*1.7)*2 if clip != 'die' else 0
        sx2, sy2 = sx, sy+bobs
        if clip == 'attack':
            fwd = [0, 0, 2, 4, 8, 10, 6, 2][n]
            sx2 = sx+(fwd if sx > 0 else fwd*.4)
        if clip == 'die' and life > 0:
            for k in range(5):
                ang = k*1.26+i
                sparkle(a, sx2+math.cos(ang)*(4+life*10), sy2+math.sin(ang)*(4+life*10), TEAL[4 if k % 2 else 3])
            continue
        a.ball(sx2, sy2, 6.5, 6.5, FUR)
        a.poly([(sx2-3, sy2-5), (sx2+3, sy2-5), (sx2, sy2-11)], FUR[2])
        a.ellipse(sx2-2, sy2+1, 1.1, 1.7, 1)
        a.ellipse(sx2+2.5, sy2+1, 1.1, 1.7, 1)
        if clip == 'attack' or n % 2:
            a.ellipse(sx2+.3, sy2-2.5, 1.1, 1.3, 1)
    return a


# ----------------------------------------------------------------------------------------------
# Bound Singer: a small pale ghost dragging a chain and iron ball. On death it drifts apart from the top down
# into rising motes; only the iron ball is left on the floor.
# ----------------------------------------------------------------------------------------------
def singer(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    a = Painter(cx=46+recoil+(math.sin(n*math.pi/4)*2 if clip == 'walk' else 0))
    hop = max(0, math.sin(n*math.pi/4))*3 if clip == 'walk' else bob*.5
    y = 16+hop+(min(1, fall*3)*3 if clip == 'die' else 0)         # it lifts a little as it starts to drift
    # wisp tail that always reaches the floor
    a.poly([(-9, y-3), (9, y-3), (4, 0), (-2, 2), (-8, 0)], FUR[1])
    a.ball(0, y+2, 13, 12, FUR)
    a.ball(0, y+4, 9.5, 7, FUR[1:])
    # arms and the chain to the iron ball
    handx, handy = 14, y-1
    if clip == 'attack':
        handx = 14+[0, -1, -2, 6, 14, 12, 5, 1][n]
        handy = y-1+[0, 4, 8, 3, -3, -2, 0, 0][n]
    a.ball(-14, y-2, 3.5, 3.5, FUR)
    a.ball(handx, handy, 3.6, 3.6, FUR)
    bx, by = -20+(-lunge*1.5 if clip == 'attack' else 0), 5
    if clip == 'attack' and n >= 3:
        bx, by = 12+[0, 0, 0, 20, 30, 26, 14, 4][n], 5+[0, 0, 0, 8, 4, 0, 0, 0][n]
    pts = bez((handx, handy), ((handx+bx)/2, min(handy, by)-4), (bx, by+2), 5)
    for px, py in pts[1:-1]:
        a.ball(px, max(1.5, py), 1.7, 1.7, PLATE)
    a.ball(bx, by, 5, 5, PLATE)

    a.face(0, y+4, clip, n, .75)
    if clip != 'die':
        # sung note
        if (clip == 'attack' and n in (2, 3, 4)) or (clip == 'idle' and n in (1, 2, 3)):
            nx, ny = 16+n, y+15+n
            a.ellipse(nx, ny, 2.4, 1.8, 1)
            a.line([(nx+2, ny), (nx+2, ny+7), (nx+5, ny+5)], 1, 1)
    else:
        f = fall
        # puff out, then disperse from the top down; the ball and chain stay
        erase_rising(a, max(0, min(1, (f-.05)/.85)))
        a.ball(bx, by, 5, 5, PLATE)
        for k, (mx, my) in enumerate(((-8, 14), (3, 22), (10, 12), (-3, 30), (7, 33), (-11, 26))):
            vis = sm(f*1.6-k*.12)*(1 if k < 3 else 1-sm((f-.7-k*.03)/.3))
            if vis > .05:
                sparkle(a, mx+math.sin(k)*3, my+f*(10+k*3), TEAL[4 if k % 2 else 3])
    return a


DRAW = dict(tidetemplar=templar, tidecantor=cantor, tideleech=leech, bellkeeper=bellkeeper, mournsister=sister,
            rootabbot=abbot, choirmother=mother, choirsinger=singer)


def frame(kind, clip, n):
    grid = np.array(DRAW[kind](clip, n).im)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = 3
    if os.environ.get('CLOISTER_LOOSE'):
        ys, xs = np.nonzero(grid)
        if not grid.any() or min(xs.min(), ys.min()) <= 0 or xs.max() >= W-1 or ys.max() >= H-1:
            print('BOUNDS', kind, clip, n, (xs.min(), ys.min(), xs.max(), ys.max()) if grid.any() else 'empty')
        return grid
    assert grid.any(), (kind, clip, n, 'empty')
    assert not (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()), (kind, clip, n, 'border')
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    existing = {sp['name']: sp['sprite_id'] for sp in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}      # validate every kind before saving any source
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX+kind+'_all'
        assert name not in existing, 'Unregistered source already exists: '+name
        np.savez_compressed(ROOT/f'scripts/cloister_slime_{kind}_raw.npz', **data[kind])
        sid = old.api('create', dict(name=name, width=W, height=H, frames=34, layers=1, fps=10,
                                     palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]))['sprite_id']
        print('Created native source', kind, sid, flush=True)
        offset = 0
        for clip, grids in data[kind].items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=sid, frame=offset+n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2)+'\n')
        print(kind, sid, offset, 'frames saved', flush=True)


def refresh():
    """Rewrite the frames of the named kinds' EXISTING saved sources from the drawers (same IDs). This overwrites
    editor edits of those kinds, so use it only while the art is still a candidate nobody has hand-edited."""
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = json.loads(REGISTRY.read_text())
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT/f'scripts/cloister_slime_{kind}_raw.npz', **data)
        offset = 0
        for clip, grids in data.items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=saved[kind], frame=offset+n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        print('Refreshed', kind, saved[kind], offset, 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    """Replace the eight Cloister atlases and ONLY their `sprites`/`tops` entries in the shared cathedral.txt."""
    saved = json.loads(REGISTRY.read_text())
    assert set(saved) == set(KINDS)
    meta = json.loads(MANIFEST.read_text())
    before = json.loads(MANIFEST.read_text())
    proof, atlases, tops = {}, {}, {}
    for kind in KINDS:       # read and validate every saved editor source before replacing any installed file
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset = 0
        rows = []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip] == dict(fps=fps, n=count, row=row, editorStart=offset), 'clip layout changed'
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset+n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n*kw, row*kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        tops[kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    meta = kindframe.merge_kind_entries(meta, KINDS, saved, tops, {k: kind_frame(k) for k in KINDS if k in KIND_FRAMES})
    # shared manifest: everything except these eight entries must be untouched
    for key in meta:
        if key in ('sprites', 'tops', 'kindFrames'):
            assert {k: v for k, v in (meta.get(key) or {}).items() if k not in KINDS} == {k: v for k, v in (before.get(key) or {}).items() if k not in KINDS}
            if key != 'kindFrames': assert list(meta[key]) == list(before[key]), 'key order changed'
        else:
            assert meta[key] == before[key], key
    for kind, atlas in atlases.items():
        dest = ASSETS/f'cathedral_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 272 saved PixelFlow frames; shared cathedral.txt changed only for', ', '.join(KINDS), flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames, not drawers."""
    meta = json.loads(MANIFEST.read_text())
    saved = json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS/f'cathedral_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n*kw, row*kh, (n+1)*kw, (row+1)*kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset+n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def preview():
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    overview = Image.new('RGB', (len(only)*240, 5*218), '#2b4a52')
    d = ImageDraw.Draw(overview)
    for col, kind in enumerate(only):
        data = frames(kind)
        sheet = Image.new('RGB', (8*192, 5*218), '#2b4a52')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((192, 192), Image.Resampling.NEAREST)
                sheet.paste(im, (n*192, row*218), im)
                sd.line([(n*192+60, row*218+180), (n*192+132, row*218+180)], fill='#e8a0e0')
                sd.text((n*192+8, row*218+194), f'{clip} {n}', fill='white')
            im = rgba(grids[0 if clip != 'die' else 7]).resize((192, 192), Image.Resampling.NEAREST)
            overview.paste(im, (col*240+20, row*218), im)
            d.text((col*240+20, row*218+194), f'{NAMES[kind]} / {clip}', fill='white')
        sheet.save(OUT/f'preview-{kind}.png')
    overview.save(OUT/'preview.png')
    print(OUT/'preview.png')


if __name__ == '__main__':
    {'preview': preview, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
