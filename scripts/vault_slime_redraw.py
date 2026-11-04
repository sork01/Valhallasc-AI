#!/usr/bin/env python3
"""Undervault art, second pass (v2): Greenmeadow slime style, redrawn from scratch.

preview | extents | build | refresh | export | verify.  Rigid armour/stone and skeleton anatomy move by joints, never by
universal squash.  Every planted foot (and every robe/gown hem) rests exactly on the anchor row (Painter y=0), so nothing
floats.  Each kind has eight distinct attack frames (wind-up, strike, recovery) and eight distinct death frames, and its own
frame size where the art needs one (KIND_FRAMES, docs/kind-frames.md).  The v1 sources (Beta 1.39.5) stay registered in
vault_slime_v1_sources.txt.  Export preserves editor edits.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
from deep_slime_redraw import sm, bez, taper

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/vault-slime'
REGISTRY = ROOT/'scripts/vault_slime_sources.txt'
PREFIX = 'valhallasc_vault_slime_style_b_'
KINDS = ['thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking']
NAMES = dict(thrall='Vault Thrall', archer='Bone Archer', acolyte='Hollow Acolyte',
             gatewarden='Hrolf Bonegate', choir='Valka, the Hollow Choir',
             colossus='Ironwake', hollowking='Haldor, the Hollow King')
W = H = 96                       # zone-wide frame (manifest fallback)
AX, AY = 48, 90
# kind -> (w, h, ax, ay); the anchor's y is the ground row, its x the creature's centre (+2).  Measured with `extents`.
KIND_FRAMES = dict(thrall=(114, 92, 43, 86), archer=(114, 88, 42, 82), acolyte=(116, 104, 37, 98), gatewarden=(124, 102, 47, 96),
                   choir=(104, 96, 48, 90), colossus=(126, 114, 52, 108), hollowking=(114, 98, 39, 92))
CLIPS = old.CLIPS


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Same colours as v1; index zero alone is transparent.
PALETTE = ['#00000000', '#22222f', '#ffffff', '#fffbea', '#eda0ad',
           '#534b42', '#8c8065', '#bdb093', '#e7dab5', '#fff4d7',
           '#252c40', '#4e5e7c', '#8094b3', '#b8d2e8', '#eaf6ff',
           '#281943', '#50327f', '#8158b8', '#b494e3', '#e4d0ff',
           '#103641', '#226578', '#42a4b1', '#8ae4e8', '#dcffff',
           '#5b3b22', '#98602c', '#cb963c', '#f2cd6a', '#fff3ae',
           '#163e29', '#2b7846', '#55ba73', '#a3e9ae', '#e2ffe8',
           '#40201f', '#7a3334', '#b95154', '#e98c83', '#ffd0ae']
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
BONE = list(range(5, 10))
PLATE = list(range(10, 15))
PURPLE = list(range(15, 20))
TEAL = list(range(20, 25))
GOLD = list(range(25, 30))
GREEN = list(range(30, 35))
RED = list(range(35, 40))
ICE = TEAL
EYE_WHITE = 3          # colour-exact eye-white palette index (#fffbea)


def mix(a, b, t):
    return a+(b-a)*t


def mixp(p, q, t):
    return (mix(p[0], q[0], t), mix(p[1], q[1], t))


def rot(x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return x*c-y*s, x*s+y*c


class Painter:
    """Round shaded components on a kind-sized canvas; y is up from the ground row, x from the centre column."""
    def __init__(self, kind, dx=0):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax-2+dx

    def pos(self, x, y):
        return round(self.cx+x), round(self.ay-y)

    def ellipse(self, x, y, rx, ry, col):
        px, py = self.pos(x, y)
        self.d.ellipse((round(px-rx), round(py-ry), round(px+rx), round(py+ry)), fill=col)

    def line(self, pts, col, width=1):
        self.d.line([self.pos(*p) for p in pts], fill=col, width=width)

    def poly(self, pts, col, outline=None):
        self.d.polygon([self.pos(*p) for p in pts], fill=col, outline=outline)

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        """A shaded ellipsoid; `ang` turns the ellipse counter-clockwise on screen, the light stays upper-left."""
        px, py = self.pos(x, y)
        R = max(rx, ry)
        c, s = math.cos(ang), math.sin(ang)
        for yy in range(max(0, math.floor(py-R)), min(self.h, math.ceil(py+R)+1)):
            for xx in range(max(0, math.floor(px-R)), min(self.w, math.ceil(px+R)+1)):
                dx, dy = xx-px, yy-py
                u, v = (dx*c-dy*s)/rx, (dx*s+dy*c)/ry
                rr = u*u+v*v
                if rr > 1:
                    continue
                z = math.sqrt(max(0, 1-rr))
                nx, ny = u*c+v*s, -u*s+v*c
                value = max(0, min(.999, .23+.71*(-.40*nx-.54*ny+.74*z)))*(len(ramp)-1)
                lo = int(value)
                threshold = ((xx % 4)*5+(yy % 4)*3) % 16/16
                shade = min(len(ramp)-1, lo+int(value-lo > threshold))
                if rr > .93 and nx+ny > .2:
                    shade = 0
                self.im.putpixel((xx, yy), ramp[shade])

    def limb(self, points, ramp, width=5):
        self.line(points, ramp[0], width+2)
        self.line(points, ramp[min(2, len(ramp)-1)], width)
        for x, y in points[1:-1]:
            self.ball(x, y, width/2, width/2, ramp)

    def eye(self, x, y, clip, n, size=1):
        if clip == 'die' and n >= 2:
            self.line([(x-2, y-2), (x+2, y+2)], 1, 2)
            self.line([(x-2, y+2), (x+2, y-2)], 1, 2)
        elif clip == 'idle' and n == 3:
            self.line([(x-3*size, y), (x+3*size, y+.5)], 1, 2)
        else:
            self.ellipse(x, y, 4.3*size, 6.4*size, 1)
            self.ellipse(x, y+.5, 3.3*size, 5.3*size, EYE_WHITE)
            self.ellipse(x+1, y-.2, 1.6*size, 3.4*size, 1)
            self.ellipse(x+.7, y+2.2, 1, 1, 2)
            if clip == 'attack' and n < 3:
                self.line([(x-4, y+6), (x+3, y+3)], 1, 2)

    def face(self, x, y, clip, n, size=1):
        for dx in (-6, 6):
            self.eye(x+dx*size, y, clip, n, size)
        if clip != 'die' or n < 2:
            self.ellipse(x-12*size, y-5, 2.5, 1.3, 4)
            self.ellipse(x+12*size, y-5, 2.5, 1.3, 4)
        self.line([(x-3, y-8), (x, y-9), (x+3, y-8)], 1)


def motion(clip, n):
    phase = n*math.pi/4
    stride = math.sin(phase) if clip == 'walk' else 0
    bob = [0, 1, 2, 1, 0, -1][n]*.5 if clip == 'idle' else 0
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    fall = [0, .06, .19, .36, .57, .78, .94, 1][n] if clip == 'die' else 0
    return stride, bob, recoil, fall


ATTACK = [-1.5, -3, -4, .5, 4, 3.5, 1.5, 0]     # wind-up (negative), snap, impact, follow-through, recover
ARC = [-.35, -.7, -1, .25, 1, .95, .5, 0]      # swung props: back over the shoulder (-1) to smashed down (+1)


def atk(clip, n):
    if clip != 'attack':
        return 0., 0.
    v = ATTACK[n]
    return max(0., -v)/4, max(0., v)/4


def arc(clip, n):
    if clip != 'attack':
        return 0., 0.
    return max(0., -ARC[n]), max(0., ARC[n])


def foot(a, x, lift, rx, ry, ramp):
    """A planted foot: integer ry and centre y = ry, so its lowest pixel is the ground row when lift is 0."""
    a.ball(x, ry+lift, rx, ry, ramp)


def motes(a, n, count, base_x, spread, top, ramp, floor=3):
    """Drifting motes; positions depend on n so consecutive frames always differ."""
    for k in range(count):
        a.ellipse(base_x+((k*37+n*11) % spread)-spread/2, floor+((n*5+k*13) % top), 1, 1, ramp[(k+n) % len(ramp)])


def ring_arc(a, x, y, r, col, a0=-.85, a1=.85, width=2):
    a.line([(x+r*math.cos(t), y+r*math.sin(t)) for t in np.linspace(a0, a1, 9)], col, width)


SW = [(.3, 0), (.65, 0), (1, 0), (1, .55), (0, 1), (0, .9), (0, .45), (0, 0)]   # (toward the raised pose, toward the slammed pose)


def sw(clip, n):
    """Keyframe weights of a swung prop: frames 0-2 rise, 3 is mid-swing, 4-5 the impact, 6-7 the recovery to rest."""
    return SW[n] if clip == 'attack' else (0., 0.)


def swp(w, rest, up, down):
    return mixp(mixp(rest, up, w[0]), down, w[1])


def hurtof(clip, n):
    return [3, 2, 1, 0][n] if clip == 'hurt' else 0


# ----------------------------------------------------------------------------------------------
# shared parts
# ----------------------------------------------------------------------------------------------
def skull(a, x, y, clip, n, size=1):
    # Oversized glossy bone dome, separate jaw and four readable teeth.
    a.ball(x+2*size, y-10*size, 9*size, 4*size, BONE)
    a.ball(x, y, 17*size, 15*size, BONE)
    a.ball(x-5*size, y+7*size, 7*size, 3*size, BONE[1:])
    a.face(x, y-1*size, clip, n, size)
    a.poly([(x-1, y-7*size), (x+2, y-5*size), (x+4, y-8*size)], 1)
    for j in range(4):
        tx = x+(-4+j*3)*size
        a.line([(tx, y-10*size), (tx, y-13*size)], 5)


def ribs(a, y, fall=0, spread=1):
    a.limb([(0, y-9), (0, y+11)], BONE, 4)
    for j in range(3):
        yy = y+8-j*6
        for sign in (-1, 1):
            dx = sign*(3+fall*(5+j*3))*spread
            a.limb([(dx, yy), (dx+sign*7, yy-2-fall*j*2), (dx+sign*8, yy-4-fall*j*2)], BONE, 3)
    a.ball(0, y-11, 8, 4, BONE)


def legs(a, ph, clip, fall, armour=False, spread=0, st=0., wu=0., sink=13):
    """Two legs: hip, knee, ankle and a foot whose lowest pixel is the ground row.  Walk lifts one foot at a time; an
    attack steps the front foot forward and braces the rear one; on defeat the legs fold and splay."""
    ramp = PLATE if armour else BONE
    rx, ry = (8, 4) if armour else (6, 3)
    for sign in (-1, 1):
        sw = math.sin(ph+(0 if sign > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sw)*3.5
        fx = sign*8+sw*5+(st*5 if sign > 0 else -wu*2)
        if fall:
            fx = sign*(8+fall*spread)
        hip = (sign*6, 25-fall*sink)
        knee = (sign*(8+fall*spread*.7)+(fx-sign*8)*.4, 15-fall*8)
        ank = (fx, ry+1+lift)
        a.limb([hip, knee, ank], ramp, 5 if armour else 3)
        foot(a, fx, lift, rx, ry, ramp)


def shield(a, x, y, fall=0, large=False):
    r = 12 if large else 10
    a.ball(x, y, r, r+1, PLATE)
    a.ball(x, y, r-3, r-2, RED if large else GOLD)
    a.line([(x-r+3, y), (x+r-3, y)], PLATE[0], 2)
    a.line([(x, y-r+3), (x, y+r-3)], PLATE[0], 2)
    a.ball(x, y, 3, 3, PLATE)
    if fall > .5:
        a.line([(x-5, y+7), (x-2, y+1), (x+5, y-5)], 1)


def sword(a, hand, angle, length=25, royal=False):
    dx, dy = math.cos(angle), math.sin(angle)
    tip = (hand[0]+dx*length, hand[1]+dy*length)
    a.line([(hand[0]-dx*5, hand[1]-dy*5), tip], PLATE[0], 6)
    a.line([hand, tip], GREEN[3] if royal else PLATE[3], 3)
    a.line([(hand[0]-5*dy, hand[1]+5*dx), (hand[0]+5*dy, hand[1]-5*dx)], GOLD[2], 3)
    a.ball(*hand, 4, 4, BONE)
    return tip


def slash_trail(a, hand, angle, length, cols, steps=5):
    """Bright crescent dots where the blade has just been (the swing runs towards smaller angles)."""
    for k in range(1, steps+1):
        ak = angle+k*.34
        r = max(1, 3.4-k*.5)
        a.ellipse(hand[0]+math.cos(ak)*(length-3), max(r, hand[1]+math.sin(ak)*(length-3)), r, r, cols[k % len(cols)])


def spark(a, x, y, col=2, r=3):
    y = max(y, r)
    a.line([(x-r, y), (x+r, y)], col, 1)
    a.line([(x, y-r), (x, y+r)], col, 1)
    a.line([(x-r+1, y-r+1), (x+r-1, y+r-1)], col, 1)
    a.line([(x-r+1, y+r-1), (x+r-1, y-r+1)], col, 1)


def axe(a, hand, angle):
    dx, dy = math.cos(angle), math.sin(angle)
    top = (hand[0]+dx*24, hand[1]+dy*24)
    a.line([(hand[0]-dx*10, hand[1]-dy*10), top], 25, 5)
    a.line([(hand[0]-dx*10, hand[1]-dy*10), top], 27, 2)

    def p(x, y):
        return (top[0]+x*dx-y*dy, top[1]+x*dy+y*dx)
    a.poly([p(-5, 1), p(-8, 10), p(3, 12), p(7, 4), p(2, 0)], 10)
    a.poly([p(-4, 2), p(-6, 8), p(2, 10), p(5, 4)], 13)
    a.ball(*hand, 4, 4, BONE)
    return top


# ----------------------------------------------------------------------------------------------
# Vault Thrall: a skeleton in a green loincloth with a short sword and a round shield.  It lifts the sword up and back
# over its skull, steps in and chops down in an arc while the shield thrusts forward.  On defeat the skull drops and
# rolls clear, the ribs spread, the sword and shield clatter down and loose bones lie about.
# ----------------------------------------------------------------------------------------------
def thrall(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = arc(clip, n)
    hurt = hurtof(clip, n)
    a = Painter('thrall', recoil+st*6-wu*3)
    ph = n*math.pi/4
    legs(a, ph, clip, fall, spread=10, st=st, wu=wu)
    y = 34+bob-fall*22-hurt*.5-st*2
    a.poly([(-11, 25-fall*13), (11, 25-fall*13), (15, 13), (4, 17), (-3, 12), (-13, 15)], 31)
    ribs(a, y, fall)
    sx, sy = -24-fall*3+st*5, 33-fall*24+wu*4
    a.limb([(-9, y+7), (-19+st*3, y), (sx, sy)], BONE, 3)
    shield(a, sx, sy, fall)
    sh = (9, y+7)
    w = sw(clip, n)
    hand = swp(w, (21, 32), (27, 61), (35, 38)) if clip == 'attack' else (21, 32-fall*23)
    ang = swp(w, (1.55, 0), (1.95, 0), (-.85, 0))[0] if clip == 'attack' else 1.55-fall*1.4
    elbow = ((sh[0]+hand[0])/2+4, (sh[1]+hand[1])/2-3)
    a.limb([sh, elbow, hand], BONE, 3)
    hx, hy = 1+fall*15-wu*2+st*3, 58+bob*.4-fall*46-st*3
    skull(a, hx, hy, clip, n, .95)
    if fall > .25:
        a.line([(hx-7, hy+5), (hx, hy), (hx-1, hy-5)], 5)
    tip = sword(a, hand, ang, 23)
    if clip == 'attack' and st > .3:
        slash_trail(a, hand, ang, 23, [13, 14, 2], 5)
        if st > .8:
            spark(a, tip[0]+1, tip[1], 2, 3)
    if clip == 'die' and n >= 3:
        for j in range(3):
            a.limb([(-22+j*14, 4+j % 2*2), (-14+j*14, 5+j % 2)], BONE, 2)
    return a


# ----------------------------------------------------------------------------------------------
# Bone Archer: a skeleton with golden hair, a quiver and a long bow.  It nocks an arrow, draws the string right back
# with the whole body leaning away, looses it (the bow kicks forward and the arrow flies out) and lowers the bow.  On
# defeat the bow drops flat, the arrows spill and the skeleton collapses.
# ----------------------------------------------------------------------------------------------
def archer(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    # draw: how far the string is pulled; fly: where the arrow is after the release
    draw = [5, 10, 16, 0, 0, 0, 0, 1][n] if clip == 'attack' else 1
    fly = {3: 0, 4: 12, 5: 22}.get(n) if clip == 'attack' else None
    lean = -[1, 3, 5, -1, 0, 0, 0, 0][n] if clip == 'attack' else 0
    a = Painter('archer', recoil+lean)
    ph = n*math.pi/4
    legs(a, ph, clip, fall, spread=6)
    y = 33+bob*.8-fall*21-hurt*.5
    a.limb([(-12, y-4), (-18, y+16)], GOLD, 6)
    for k in range(3):
        xx = -20+k*4-fall*8
        yy = y+19+fall*3
        a.line([(xx, yy-13), (xx+fall*8, yy+3)], 8, 1)
        a.poly([(xx-2, yy+3), (xx+1, yy+8), (xx+3, yy+3)], 37)
    a.poly([(-10, y-8), (10, y-8), (13, 11), (-14, 13)], 26)
    ribs(a, y, fall, spread=.8)
    hx = -fall*12-(draw-1)*.3
    hy = 57+bob*.5-fall*43-hurt*.5
    a.ball(hx, hy+2, 20, 19, GOLD)
    a.poly([(hx-17, hy), (hx-24, hy-11), (hx-12, hy-8)], 26)
    skull(a, hx+2, hy-2, clip, n, .86)
    a.line([(hx-16, hy+8), (hx+16, hy+8)], 26, 3)
    bx, by = 24, 38-fall*22
    # The rigid bow rotates flat and drops on defeat; the string relaxes after the release.
    kick = {3: .34, 4: .2, 5: .08}.get(n, 0) if clip == 'attack' else 0
    angle = fall*1.1-kick

    def bowp(px, py):
        c, s = math.cos(angle), math.sin(angle)
        return (bx+px*c-py*s, by+px*s+py*c)
    top, mid, bot = bowp(0, 22), bowp(8, 0), bowp(0, -22)
    a.limb([top, mid, bot], GOLD, 3)
    nock = bowp(-draw, 0)
    a.line([top, nock, bot], 8, 1)
    hand = bowp(4, 0)
    a.limb([(8, y+6), (15, y+8), hand], BONE, 3)
    a.limb([(-7, y+5), (-11+(draw-1)*.2, y+1), nock], BONE, 3)
    if clip == 'attack':
        if n <= 3:                                              # the arrow lies nocked along the bow
            tail = nock
            head = (bx+13, by)
        elif fly is not None:                                   # in flight
            head = (bx+13+fly, by)
            tail = (head[0]-18, by)
        else:
            tail = head = None
        if tail:
            a.line([tail, head], 5, 3)
            a.line([tail, head], 9, 1)
            for sg in (-1, 1):
                a.line([(tail[0], by+sg), (tail[0]+4, by+sg*4)], 37, 2)
            a.poly([(head[0]+6, by), (head[0]-1, by+4), (head[0]-1, by-4)], 14, 1)
            if n >= 4:                                          # a streak behind the shot
                a.line([(tail[0]-10, by), (tail[0]-3, by)], 14, 1)
    if fall > .3:
        for j in range(3):
            a.limb([(-25+j*9, 5+j % 2*3), (-15+j*9, 7+j % 2*3)], BONE, 2)
    return a


# ----------------------------------------------------------------------------------------------
# Hollow Acolyte: a skull in a deep purple hood, robed, with a golden staff and orb.  It raises the staff, the orb swells
# with gathering motes, then thrusts it forward and the orb leaves as a bolt.  On defeat the robe settles, the staff
# falls and the hood slumps.  The hem rests on the ground.
# ----------------------------------------------------------------------------------------------
BOLT = {3: (5, 7), 4: (14, 6), 5: (24, 4.5), 6: (30, 2.5)}


def acolyte(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = atk(clip, n)
    hurt = hurtof(clip, n)
    if clip == 'walk':
        bob = [0, 2, 3, 2, 0, -1, -2, -1][n]*.5
    a = Painter('acolyte', recoil+st*4-wu*3)
    y = 31+bob*.6-fall*19-hurt*.5
    sway = stride*1.5
    wide = 1+fall*.3
    # Cloth drapes and settles while the skull and staff remain solid; the lowest hem point rests on the ground row.
    a.poly([(-10, y+12), (10, y+12), ((17+sway)*wide, 7), (21*wide, 3), (9*wide, 5), (0, 0), (-12*wide, 4), ((-19+sway)*wide, 1)], 15)
    a.poly([(-8, y+10), (7, y+10), (13*wide, 8), (-12*wide, 8)], 17)
    a.poly([(-7, y+10), (-2, y+12), (-6, 10), (-13*wide, 8)], 18)
    for x in (-9, 0, 9):
        a.line([(x, y), (x*1.4*wide, 5)], 16, 2)
    a.line([(-11, y-2), (11, y-2)], 27, 2)
    hx, hy = 1-fall*11-wu*2+st*3, 57+bob*.5-fall*35+wu*2-st*2-hurt*.5
    a.ball(hx, hy+2, 21, 20, PURPLE)
    skull(a, hx+2, hy-1, clip, n, .88)
    a.line([(hx-16, hy+10), (hx+16, hy+10)], 16, 3)
    if clip == 'attack':
        w = sw(clip, n)
        hand = swp(w, (23, 34), (15, 46), (31, 36))
        top = swp(w, (25, 70), (13, 82), (40, 58))
        vec = (top[0]-hand[0], top[1]-hand[1])
        bottom = (hand[0]-vec[0]*.85, max(2, hand[1]-vec[1]*.85))
    elif clip == 'die':
        hand = (23, 34-fall*25)
        top = (mix(25, 37, fall), mix(70, 14, fall))
        bottom = (mix(22, 3, fall), 5)
    else:
        hand = (23, 34)
        top = (25, 70)
        bottom = (21.5, 3.5)
    a.limb([(9, y+6), (17, y+1), hand], PURPLE, 5)
    a.line([bottom, top], 25, 5)
    a.line([bottom, top], 27, 2)
    a.ball(*hand, 4, 4, BONE)
    orb = 7+wu*3
    a.ball(top[0], top[1], orb, orb+1, GOLD)
    if fall < .9:
        a.ball(top[0], top[1]+1, orb-2, orb-1, PURPLE)
        a.ellipse(top[0]-1, top[1]+3, 2, 2, 19)
    if clip == 'attack':
        if wu:                                                  # motes gather into the swelling orb
            for k in range(3):
                t = n*.9+k*2.1
                r = 12+wu*3
                a.ellipse(top[0]+math.cos(t)*r, top[1]+math.sin(t)*r*.8, 1.5, 1.5, PURPLE[3+k % 2])
        if n in BOLT:
            d, r = BOLT[n]
            bxp, byp = top[0]+d, top[1]-d*.15
            for k in range(1, 4):                               # the bolt's tail
                a.ellipse(bxp-k*(d*.35+2), byp+k*.4, max(1, r-k*1.3), max(1, r-k*1.3), PURPLE[1+k % 2])
            a.ball(bxp, byp, r, r, PURPLE)
            a.ellipse(bxp-r*.3, byp+r*.3, max(1, r*.3), max(1, r*.3), 2)
    if clip == 'die':
        for j in range(max(0, 7-n)):
            a.ellipse(-20+j*8, 35+n*3+j % 2*4, 1, 1, 18)
        if n >= 3:
            a.limb([(9, 7), (21, 5)], BONE, 3)
    return a


# ----------------------------------------------------------------------------------------------
# Hrolf Bonegate: a horned skeleton in plate with a red shield and a great axe.  He raises the axe high behind his
# helmet, steps in and brings it down in a heavy arc.  On defeat the armour drops, the helmet slumps, the axe and shield
# fall and a few bones lie beside the plate.
# ----------------------------------------------------------------------------------------------
def gatewarden(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = arc(clip, n)
    hurt = hurtof(clip, n)
    a = Painter('gatewarden', recoil+st*6-wu*3)
    ph = n*math.pi/4
    legs(a, ph, clip, fall, armour=True, spread=10, st=st, wu=wu)
    y = 36+bob*.6-fall*22-hurt*.5-st*2
    a.poly([(-13, y), (13, y), (19, 8), (0, 13), (-17, 7)], 36)
    a.ball(0, y, 17, 16, PLATE)
    a.ball(-5, y+7, 6, 3, PLATE[1:])
    a.line([(-12, y-8), (12, y-8)], 27, 3)
    for sign in (-1, 1):
        a.ball(sign*(17+fall*5), y+8-fall*3, 9, 8, PLATE)
    sx, sy = -26-fall*2+st*4, 35-fall*23+wu*3
    a.limb([(-13, y+5), (-22+st*3, y), (sx, sy)], PLATE, 5)
    shield(a, sx, sy, fall, True)
    hx, hy = 2+fall*13-wu*2+st*3, 62+bob*.6-fall*43-st*3
    skull(a, hx, hy-2, clip, n, .95)
    a.ball(hx, hy+8, 18, 9, PLATE)
    a.line([(hx-17, hy+4), (hx+17, hy+4)], 27, 2)
    for sign in (-1, 1):
        a.limb([(hx+sign*14, hy+10), (hx+sign*23, hy+15-fall*6), (hx+sign*22, hy+23-fall*10)], BONE, 4)
    sh = (13, y+6)
    w = sw(clip, n)
    hand = swp(w, (24, 34), (29, 66), (36, 34)) if clip == 'attack' else (24-fall*17, 34-fall*21)
    ang = swp(w, (1.6, 0), (1.95, 0), (-.8, 0))[0] if clip == 'attack' else 1.6-fall*1.8
    elbow = ((sh[0]+hand[0])/2+4, (sh[1]+hand[1])/2-3)
    a.limb([sh, elbow, hand], PLATE, 6)
    top = axe(a, hand, ang)
    if clip == 'attack' and st > .3:
        slash_trail(a, hand, ang, 28, [13, 14, 2], 5)
        if st > .8:
            spark(a, top[0]+4, top[1]-3, 2, 4)
    if n >= 2 and clip == 'die':
        a.line([(-7, y+11), (0, y+3), (-3, y-6)], 10, 2)
        a.limb([(-12, 9), (-21, 5)], BONE, 3)
    return a


# ----------------------------------------------------------------------------------------------
# Valka, the Hollow Choir: a teal spirit in a veil and gown, floating just above a hem that rests on the ground.  She
# throws her head back with her arms spread, then sings: bright rings of sound expand forward from her open mouth.  On
# defeat the face and veil dissolve upward, the notes scatter and only the settled gown and diadem lie on the ground.
# ----------------------------------------------------------------------------------------------
RINGS = {3: [(8, .9)], 4: [(10, .9), (20, .8)], 5: [(14, .8), (26, .7), (38, .5)], 6: [(30, .5), (42, .35)]}


def dissolve(a, f, top, bottom=0):
    """Ordered-dither erase from the top down: pixels higher than `bottom` go first; the gown's base stays."""
    arr = np.array(a.im)
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    for yy in range(arr.shape[0]):
        up = a.ay-yy
        if up <= bottom:
            continue
        h = max(0., min(1., (up-bottom)/max(1., top-bottom)))
        p = max(0., min(1., f*1.5-(1-h)*.55))
        for xx in range(arr.shape[1]):
            if arr[yy, xx] and bayer[yy % 4][xx % 4]/16 < p:
                arr[yy, xx] = 0
    a.im = Image.fromarray(arr, 'P')
    a.d = ImageDraw.Draw(a.im)


def choir(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = atk(clip, n)
    hurt = hurtof(clip, n)
    a = Painter('choir', recoil+st*3-wu*3)
    floaty = math.sin(n*math.pi/3)*1.5 if clip in ('idle', 'walk') else 0
    y = 36+floaty-fall*22-hurt*.5
    sway = stride*2
    # Veil and gown remain cloth; the lowest hem point rests on the ground row, only the spirit above it floats.
    scal = [3, 0, 4, 1, 4, 0, 3, 1]
    hem = [scal[(k+int(floaty > 0)) % 8] for k in range(8)]
    wide = 1+fall*.35
    a.poly([(-12, y+14), (12, y+14), ((20+sway)*wide, hem[0]+4), (13*wide, hem[1]), (6*wide, hem[2]+3), (-3*wide, 0),
            (-12*wide, hem[4]+3), ((-21+sway)*wide, hem[5])], 20)
    a.poly([(-9, y+11), (7, y+13), (13*wide, hem[3]+5), (-12*wide, hem[6]+4)], 22)
    a.poly([(-8, y+10), (-3, y+10), (-7*wide, hem[7]+6), (-14*wide, hem[6]+4)], 23)
    for sign in (-1, 1):                                          # arms: resting, spread up for the song, slack on defeat
        rest = (sign*25, y+5)
        up = (sign*(31+wu*3), y+19+wu*8)
        hand = mixp(mixp(rest, up, wu), (sign*(24+st*4), y+9-st*2), st) if clip == 'attack' else (sign*25, y+5-fall*6)
        a.limb([(sign*10, y+8), (sign*(21+wu*4), y+3+wu*7), hand], TEAL, 6)
        a.ball(*hand, 5, 5, TEAL)
    hy = 61+floaty+fall*2-hurt*.5+wu*3-st*2
    hxo = -wu*2+st*2
    if fall < .85:
        a.ball(hxo, hy+4, 21, 20, TEAL)
        skull(a, 1+hxo, hy, clip, n, .9)
        a.poly([(-19+hxo, hy+7), (-18+hxo, hy-18), (-11+hxo, hy-12), (-12+hxo, hy+13)], 23)
        a.poly([(17+hxo, hy+13), (20+hxo, hy-17), (13+hxo, hy-12), (12+hxo, hy+10)], 23)
        # Silver diadem leaves the eye line clear.
        a.line([(-16+hxo, hy+14), (16+hxo, hy+14)], 13, 3)
        for x in (-10, 0, 10):
            a.poly([(x-3+hxo, hy+14), (x+hxo, hy+21), (x+3+hxo, hy+14)], 14)
        if clip == 'attack' and wu+st > 0:                        # the open mouth: a dark oval over the skull's jaw
            r = 2+wu*2+st*3
            a.ellipse(2+hxo, hy-9, r, r+1, 1)
            a.ellipse(2+hxo, hy-8.5, max(1, r-1.2), max(1, r-.5), 4)
    if clip == 'attack' and n in RINGS:
        mx, my = 4+hxo, hy-8
        for r, k in RINGS[n]:                                      # rings of sound travel forward from the mouth
            ring_arc(a, mx, my, r, TEAL[4] if k > .6 else TEAL[3], width=2 if k > .6 else 1)
            ring_arc(a, mx, my, r-3, TEAL[2], width=1)
    if clip == 'die':
        # Progressive gaps dissolve the spirit upward, not the solid gown below it.
        dissolve(a, fall, 82, 14)
        for j in range(max(0, 7-n)):
            x = -24+j*8
            y2 = 55+n*3+(j % 2)*7
            a.line([(x, y2), (x+3, y2+4)], 23, 2)
        if n >= 5:                                                # the diadem lies on the ground at the end
            a.line([(-9, 3), (-3, 4), (3, 3), (9, 4)], 14, 3)
    else:
        for j in range(2 if clip != 'attack' else 3):
            x = -30+j*28
            y2 = 55+(n*3+j*11) % 21
            a.line([(x, y2), (x, y2+7), (x+4, y2+6)], 23, 1)
            a.ellipse(x-2, y2, 2, 1, 24)
    return a


# ----------------------------------------------------------------------------------------------
# Ironwake: a stone colossus with a teal gem heart.  Both fists rise over its head, then hammer down into the ground
# with a shower of rock and dust.  On defeat the gem cracks, the stone blocks separate and fall and the head slumps.
# ----------------------------------------------------------------------------------------------
def colossus(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = atk(clip, n)
    hurt = hurtof(clip, n)
    a = Painter('colossus', recoil+st*5-wu*3)
    ph = n*math.pi/4
    y = 39+bob*.6-fall*21-st*2-hurt*.5
    # Fixed-size solid components: cracks grow, then blocks separate and fall.
    for sign in (-1, 1):
        swing = math.sin(ph+(0 if sign > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, swing)*3.5
        fx = sign*(12+fall*7)+swing*4
        a.limb([(sign*10, y-9), (sign*(14+fall*5), 18-fall*7), (fx, 7+lift)], PLATE, 10)
        foot(a, fx, lift, 11, 6, PLATE)
    # arms: rest / both fists overhead / slammed down / slack on defeat
    w = sw(clip, n)
    rest = {1: (30, 26+bob), -1: (-30, 26+bob)}
    up = {1: (17, 96), -1: (-13, 94)}
    down = {1: (40, 10), -1: (24, 10)}
    elb = {1: ((27, y-3), (38, 70), (32, 30)), -1: ((-27, y-3), (-38, 68), (-30, 28))}
    hands, elbows = {}, {}
    for sign in (-1, 1):
        if clip == 'attack':
            hands[sign] = swp(w, rest[sign], up[sign], down[sign])
            elbows[sign] = swp(w, *elb[sign])
        else:
            hands[sign] = (sign*(30+fall*4), 26+bob*(1-fall)-fall*15)
            elbows[sign] = (sign*(27+fall*4), y-3)
    if st > .5:                                                   # rock bursts up beside the fists and dust rolls out
        for k in range(4):
            bxp = 28+k*7
            a.poly([(bxp-3, 0), (bxp+(k % 2)*2-1, 6+k % 3*3+st*4), (bxp+3, 0)], PLATE[1], PLATE[0])
        for k in range(3):
            a.ellipse(44+k*6, 14+k*7+(n % 2), 2.5, 2.5, 12+k % 2)
        for k in range(3):
            a.ellipse(48+k*5, 4+k % 2*2, 3+k, 3, 14)

    def arm(sign):
        hand, sh = hands[sign], (sign*19, y+8)
        for px_, py_ in bez(sh, elbows[sign], hand, 9):             # a round tube: a chain of shaded stones
            a.ball(px_, py_, 5.5, 5.5, PLATE)
        a.ball(*hand, 10, 10, PLATE)
        for k in range(2):
            a.ellipse(hand[0]-3+k*3, hand[1]+4-k*3, 1, 1, 13)
    a.ball(0, y, 23, 20, PLATE)
    a.ball(-8, y+10, 8, 5, PLATE[1:])
    a.ball(1, y, 10, 12, PLATE[:2])
    a.ball(1, y+1, 6, 8, TEAL if fall < .75 else PLATE[:3])
    if fall < .7:
        a.line([(-2, y+3), (3, y+3), (0, y-3)], 24, 2)
    for sign in (-1, 1):
        arm(sign)
        a.ball(sign*(20+fall*6), y+13, 11, 10, PLATE)
    hx, hy = -fall*10-wu*1+st*3, 65+bob*.5-fall*43-st*5-hurt*.5
    a.ball(hx, hy, 17, 15, PLATE)
    a.ball(hx-5, hy+7, 6, 3, PLATE[1:])
    a.face(hx, hy, clip, n, .9)
    a.poly([(hx-9, hy+12), (hx-7, hy+20), (hx-2, hy+13)], 12)
    if clip == 'die':
        a.line([(-5, y+17), (-1, y+9), (-6, y+1), (4, y-10)], 10, 2)
        if n >= 2:
            for j in range(4):
                x = -22+j*14+(n-2)*(.7 if j % 2 else -.7)
                yy = max(5, 35+j % 2*9-(n-2)*6)
                a.poly([(x-3, yy+4), (x+4, yy+2), (x+3, yy-3), (x-4, yy-2)], 12+j % 2)
        if n >= 5:
            a.line([(hx-11, hy+5), (hx-2, hy+1), (hx-6, hy-7)], 10, 2)
    return a


# ----------------------------------------------------------------------------------------------
# Haldor, the Hollow King: a crowned skeleton in a purple cape with green armour and a green-bladed sword.  He raises the
# sword high behind the crown while green light gathers, steps in and cuts down with a long bright trail.  On defeat the
# crown tumbles away first, then the skeleton collapses in a delayed cascade.
# ----------------------------------------------------------------------------------------------
def hollowking(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = arc(clip, n)
    hurt = hurtof(clip, n)
    # Crown failure precedes the skeleton: a delayed, theatrical bone cascade.
    bodyfall = max(0, (fall-.12)/.88)
    a = Painter('hollowking', recoil+st*6-wu*3)
    ph = n*math.pi/4
    y = 36+bob*.6-bodyfall*25-hurt*.5-st*2
    a.poly([(-16, y+15), (15, y+14), (24+bodyfall*7, 6), (10, 9), (0, 4), (-14, 8), (-27-bodyfall*4, 5)], 15)
    a.poly([(-14, y+13), (-8, y+11), (-17, 9), (-25, 7)], 17)
    a.line([(-16, y+14), (-26-bodyfall*4, 6)], 27, 2)
    legs(a, ph, clip, bodyfall, armour=True, spread=12, sink=16, st=st, wu=wu)
    ribs(a, y, bodyfall, spread=1.2)
    for sign in (-1, 1):
        a.ball(sign*(17+bodyfall*5), y+9-bodyfall*5, 9, 8, GREEN)
        a.line([(sign*12, y+11), (sign*18, y+13)], 28, 2)
    hx, hy = 2+bodyfall*14-wu*2+st*3, 61+bob*.6-bodyfall*44-st*3
    skull(a, hx, hy, clip, n, 1.04)
    # The crown is a rigid object; after frame 2 it tumbles away from the skull.
    cxp, cyp = mix(hx, -21, fall), mix(hy+6, 14, fall)
    tilt = -fall*1.2
    c, s = math.cos(tilt), math.sin(tilt)

    def cp(px, py):
        return (cxp+px*c-py*s, cyp+px*s+py*c)
    a.poly([cp(-15, 0), cp(-17, 12), cp(-8, 7), cp(0, 16), cp(8, 7), cp(17, 12), cp(15, 0)], 25)
    a.poly([cp(-13, 2), cp(-14, 10), cp(-7, 5), cp(0, 13), cp(7, 5), cp(14, 10), cp(13, 2)], 28)
    a.ball(*cp(0, 5), 3, 3, GREEN)
    sh = (14, y+6)
    w = sw(clip, n)
    hand = swp(w, (24, 33), (28, 62), (35, 36)) if clip == 'attack' else (24-bodyfall*16, 33-bodyfall*18)
    ang = swp(w, (1.65, 0), (1.95, 0), (-.8, 0))[0] if clip == 'attack' else 1.65-bodyfall*1.9
    elbow = ((sh[0]+hand[0])/2+4, (sh[1]+hand[1])/2-3)
    a.limb([sh, elbow, hand], GREEN, 6)
    other = (-25-bodyfall*3+st*2, 30-bodyfall*21)
    a.limb([(-14, y+7), (-23, y), other], GREEN, 5)
    a.ball(*other, 5, 5, BONE)
    if clip == 'attack' and wu:                                   # green light gathers around the raised blade
        for k in range(4):
            t = n*.8+k*1.6
            a.ellipse(hand[0]+math.cos(t)*9-6, hand[1]+16+math.sin(t)*11, 1.5, 1.5, GREEN[2+k % 3])
    tip = sword(a, hand, ang, 26, True)
    if clip == 'attack' and st > .3:
        slash_trail(a, hand, ang, 26, [33, 34, 32], 6)
        if st > .8:
            spark(a, tip[0]+1, tip[1], 34, 4)
    if clip == 'die':
        for j in range(max(0, 7-n)):
            a.poly([(-18+j*6, 67-n*4), (-17+j*6, 71-n*4), (-14+j*6, 66-n*4)], 32)
        if n >= 3:
            for j in range(3):
                a.limb([(-13+j*12, 10-j % 2*3), (-20+j*12, 6)], BONE, 3)
    return a


DRAW = dict(thrall=thrall, archer=archer, acolyte=acolyte, gatewarden=gatewarden,
            choir=choir, colossus=colossus, hollowking=hollowking)


STRICT = True       # preview sets this False so problems are listed instead of stopping the sheet
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if clip == 'die':                                       # a fallen body rests on the ground: never sunk, never floating
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size:
            grid = np.roll(grid, kay-int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = 3
    problem = None
    if not grid.any() or grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any():
        problem = 'empty or touches the border'
    elif clip != 'die' and int(np.nonzero(grid.any(axis=1))[0].max()) != kay:
        problem = f'lowest row {int(np.nonzero(grid.any(axis=1))[0].max())} != anchor row {kay}'
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
            old.api('draw', dict(sprite_id=sid, frame=offset+n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
        offset += len(grids)
    return offset


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = registry()
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}      # validate every kind before saving any source
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX+kind+'_all'
        assert name not in existing, 'Unregistered source already exists: '+name
        np.savez_compressed(ROOT/f'scripts/vault_slime_{kind}_raw.npz', **data[kind])
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(name=name, width=kw, height=kh, frames=34, layers=1, fps=10,
                                     palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2)+'\n')
        print(kind, sid, api_draw(sid, 0, data[kind]), 'frames saved', flush=True)


def refresh():
    """Rewrite the frames of the named kinds' EXISTING v2 sources from the drawers (same IDs and same frame size).
    Overwrites editor edits of those kinds: only for a candidate nobody has hand-edited."""
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT/f'scripts/vault_slime_{kind}_raw.npz', **data)
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
    for kind in KINDS:       # read and validate every saved editor source before replacing any installed file
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset+n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n*kw, row*kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for kind, atlas in atlases.items():
        dest = ASSETS/f'vault_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'vault.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 238 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    """Compare the installed atlases directly to the saved editor frames, not to the drawers."""
    meta = json.loads((ASSETS/'vault.txt').read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS/f'vault_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n*kw, row*kh, (n+1)*kw, (row+1)*kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset+n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    """Measure how far each kind's art reaches from its anchor, on a large scratch canvas, to choose KIND_FRAMES."""
    global STRICT
    STRICT = False
    for kind in KINDS:
        KIND_FRAMES[kind] = (192, 192, 96, 160)
        left = right = up = 0
        for clip, grids in frames(kind).items():
            for grid in grids:
                ys, xs = np.nonzero(grid)
                if xs.size:
                    left, right, up = max(left, 94-int(xs.min())+2), max(right, int(xs.max())-94+2), max(up, 158-int(ys.min()))
        print(f'{kind}: left {left} right {right} up {up}  ->  suggested ax {left+4}, w {left+4+right+5}, ay {up+4}, h {up+4+6}')
        del KIND_FRAMES[kind]


def preview():
    global STRICT
    STRICT = False
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    for kind in only:
        kw, kh, _, kay = kind_frame(kind)
        data = frames(kind)
        sheet = Image.new('RGB', (8*kw*2, 5*(kh*2+26)), '#344b40')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((kw*2, kh*2), Image.Resampling.NEAREST)
                sheet.paste(im, (n*kw*2, row*(kh*2+26)), im)
                sd.text((n*kw*2+8, row*(kh*2+26)+kh*2+4), f'{clip} {n}', fill='white')
                gy = row*(kh*2+26)+kay*2+2
                sd.line([(n*kw*2, gy), (n*kw*2+kw*2, gy)], fill='#5a7a68')
        sheet.save(OUT/f'preview-{kind}.png')
        print(OUT/f'preview-{kind}.png')
    print('Frame problems:', BAD or 'none')


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
