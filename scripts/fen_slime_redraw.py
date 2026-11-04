#!/usr/bin/env python3
"""Gloamfen art, second pass (v2): Greenmeadow slime style, redrawn from scratch.

preview | build | refresh | export | verify.  Rigid armour/bark and animal anatomy move by joints and rotation, never by
universal squash.  Every planted foot rests exactly on the anchor row (Painter y=0), so nothing floats.  Each kind has
eight distinct attack frames (wind-up, strike, recovery) and eight distinct death frames.  Every kind has its own frame
size (KIND_FRAMES, docs/kind-frames.md) so a lashing tongue, a lunging jaw, a raised sword, a rearing head and raised
fists fit.  The v1 sources (Beta 1.39.4) stay registered in fen_slime_v1_sources.txt.  Export preserves editor edits.
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
from cloister_slime_redraw import Rig

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/fen-slime'
REGISTRY = ROOT/'scripts/fen_slime_sources.txt'
PREFIX = 'valhallasc_fen_slime_style_b_'
KINDS = ['toad', 'croc', 'knight', 'hydra', 'gloomroot']
NAMES = dict(toad='Fen Toad', croc='Mire Crocodile', knight='Drowned Knight', hydra='Mire Hydra', gloomroot='Gloomroot Colossus')
W = H = 96                       # zone-wide frame (manifest fallback)
AX, AY = 48, 90
# kind -> (w, h, ax, ay); the anchor's y is the ground row, its x the creature's centre (+2).
KIND_FRAMES = dict(toad=(112, 96, 44, 90), croc=(120, 96, 56, 90), knight=(120, 108, 56, 102),
                   hydra=(128, 108, 50, 102), gloomroot=(112, 116, 52, 110))
CLIPS = old.CLIPS


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Same colours as v1; index zero alone is transparent.
PALETTE = ['#00000000', '#182c25', '#ffffff', '#f7fff0', '#eda0ad',
           '#263d16', '#496b25', '#7ca83c', '#b5d85f', '#ecfca6',
           '#283e36', '#4c7869', '#7bb7a0', '#b8e5cd', '#e5fff0',
           '#543522', '#825432', '#b5844d', '#ddb77b', '#f5dfad',
           '#183f49', '#287989', '#53b8bd', '#9ce7dc', '#e1fff2',
           '#3f193e', '#833c83', '#c36cb7', '#eca7cd', '#ffe4ef',
           '#115647', '#2ab592', '#8bf4cf', '#d1fff0', '#f2fff9']
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
SKIN = [5, 6, 7, 8, 9]
PLATE = [10, 11, 12, 13, 14]
BARK = [15, 16, 17, 18, 19]
TEAL = [20, 21, 22, 23, 24]
PURPLE = [25, 26, 27, 28, 29]
GLOW = [30, 31, 32, 33, 34]
BELLY = [16, 17, 18, 19]
LIGHT_PLATE = [11, 12, 13, 14]
EYE_WHITE = 3          # colour-exact eye-white palette index (#f7fff0)


def mix(a, b, t):
    return a+(b-a)*t


def rot(x, y, ang):
    """Rotate (x, y) counter-clockwise (y up) by ang radians."""
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

    def tail(self, points, ramp, radius):
        """A continuous curved silhouette narrowing to one visible pointed tip (the owner's Gloamfen tail rule)."""
        points = np.asarray(points, dtype=float)
        samples = []
        for t in np.linspace(0, 1, 33):
            u = 1-t
            centre = u**3*points[0]+3*u*u*t*points[1]+3*u*t*t*points[2]+t**3*points[3]
            tangent = 3*u*u*(points[1]-points[0])+6*u*t*(points[2]-points[1])+3*t*t*(points[3]-points[2])
            normal = np.array([-tangent[1], tangent[0]])/np.linalg.norm(tangent)
            samples.append((centre, normal, radius*(1-t)**.9))

        def band(lo, hi, inset=0):
            left = [tuple(c+normal*max(0, r-inset)*lo) for c, normal, r in samples]
            right = [tuple(c+normal*max(0, r-inset)*hi) for c, normal, r in reversed(samples)]
            return left+right
        self.poly(band(-1, 1), ramp[0])
        self.poly(band(-1, 1, .8), ramp[2])
        self.poly(band(.25, 1, 1), ramp[1])
        self.poly(band(-.8, -.15, 1), ramp[3])

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

    def face(self, x, y, clip, n, size=1, ang=0.0):
        """Two big eyes, blush and a mouth; with `ang` the whole face turns about (x, y)."""
        def at(dx, dy):
            rx_, ry_ = rot(dx, dy, ang)
            return x+rx_, y+ry_
        for dx in (-6, 6):
            self.eye(*at(dx*size, 0), clip, n, size)
        if clip != 'die' or n < 2:
            self.ellipse(*at(-12*size, -5), 2.5, 1.3, 4)
            self.ellipse(*at(12*size, -5), 2.5, 1.3, 4)
        self.line([at(-3, -8), at(0, -9), at(3, -8)], 1)


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
    """(windup, strike) in 0..1 for the attack clip; both zero for every other clip."""
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


def spin(c, ang, to):
    """Point map: rotate rest-pose points about `c` by `ang`, then carry the centre to `to`."""
    def T(x, y):
        dx, dy = rot(x-c[0], y-c[1], ang)
        return to[0]+dx, to[1]+dy
    return T


def quad_leg(a, front, far, ph, clip, st, wu, cy, fx, x_front, x_back, ramp, hind_knee, thick, splay=0.):
    """One leg of a four-legged animal: root under the barrel, a bent joint, a tapered shin, a planted foot.
    Gait is diagonal; the swing foot lifts, its partner stays on the ground row."""
    s = ph+(0 if front else math.pi)+(math.pi if far else 0)
    swing = math.sin(s) if clip == 'walk' else 0
    step, lift = swing*3.5, max(0, swing)*3.5
    depth = 5 if far else 0
    if front:
        x0 = x_front+depth+fx
        root, knee = (x0, cy-4), (x0-2+step*.25, cy-10)
        ft = x0+3+step+(st*3 if clip == 'attack' else 0)
    else:
        x0 = x_back+depth+fx
        root, knee = (x0, cy-4), (x0+hind_knee+step*.25, cy-10-wu*2)
        ft = x0-3+step-(wu*1.5 if clip == 'attack' else 0)
    ft += (1 if front else -1)*9*splay                    # a fallen animal's legs splay out along the ground
    knee = (knee[0]+(1 if front else -1)*5*splay, knee[1]-3*splay)
    ankle = (ft-(1 if front else -1), 6+lift*.8-2*splay)
    a.limb([root, knee, ankle], ramp, thick)
    foot(a, ft+3, lift, 6 if not far else 5, 3, ramp)
    return root


# ----------------------------------------------------------------------------------------------
# Fen Toad: a squat frog.  It crouches and puffs its throat, lashes a long sticky tongue out and snaps it back.  The
# walk is a waddle (a forefoot and a hind foot are always planted).  On defeat the legs go limp and it tips over
# backwards onto its back, feet in the air.
# ----------------------------------------------------------------------------------------------
def toad(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    a = Painter('toad', recoil+st*6-wu*4)
    ph = n*math.pi/4
    hurt = [3, 2, 1, 0][n] if clip == 'hurt' else 0
    cy0 = 23+bob*.5-wu*6-hurt+(math.sin(ph*2)*.8 if clip == 'walk' else 0)
    ang = 3.0*t
    half = math.hypot(24*math.sin(ang), 17*math.cos(ang))
    cy = mix(cy0, half, t)
    T = spin((-2, cy0), ang, (-2, cy))

    def legs(far):
        off = -4 if far else 0
        s = ph+(math.pi if far else 0)
        h_lift = max(0, math.sin(s))*4 if clip == 'walk' else 0
        f_lift = max(0, -math.sin(s))*3.5 if clip == 'walk' else 0
        hx = -15+off-(math.sin(s)*3 if clip == 'walk' else 0)
        hip, knee = (-14+off, cy0-1), (-22+off, cy0-4)
        ankle = (hx, 6+h_lift)
        fx_ = 22+off+(math.sin(s+math.pi)*2 if clip == 'walk' else 0)+(st*3 if clip == 'attack' else 0)
        shoulder, elbow, wrist = (14+off, cy0-2), (18+off, cy0-9+hurt*.5), (fx_, 6+f_lift)
        if t:
            ankle = (mix(ankle[0], hip[0]+16, t*.7), mix(ankle[1], cy0-8, t*.7))
            wrist = (mix(wrist[0], shoulder[0]+9, t*.6), mix(wrist[1], cy0-8, t*.6))
        pts = [T(*p) for p in (hip, knee, ankle)]
        a.ball(*T(-15+off, cy0-4), 11, 10, SKIN, ang)
        a.limb(pts, SKIN, 5)
        if t:
            a.ball(*pts[2], 5, 3, SKIN, ang)
        else:
            foot(a, hx+3, h_lift, 9, 3, SKIN)
        fp = [T(*p) for p in (shoulder, elbow, wrist)]
        a.limb(fp, SKIN, 4)
        if t:
            a.ball(*fp[2], 4, 3, SKIN, ang)
        else:
            foot(a, fx_+1, f_lift, 6, 3, SKIN)

    legs(True)
    a.ball(*T(-2, cy0), 24, 17, SKIN, ang)
    a.ball(*T(1, cy0-8), 17, 7, BELLY, ang)
    for x, y in [(-16, 7), (-9, 11), (-4, 5), (-18, 0), (-10, -2)]:
        a.ball(*T(x, cy0+y), 2.5, 2, SKIN, ang)
    legs(False)
    hx, hy = 15-wu*3+st*4, cy0+6
    gape = (1.5*wu+6*st) if clip == 'attack' else max(0, 1-fall*3)
    if clip == 'attack':                                   # the throat sac puffs while the tongue is cocked
        a.ball(*T(hx+3, hy-9), 8+wu*5, 6+wu*3, BELLY, ang)
    a.ball(*T(hx+2, hy-8-gape), 15, 4, BARK, ang)
    if gape > 1.2:
        a.ball(*T(hx+5, hy-6), 11, 3+gape, PURPLE, ang)
        if st:                                             # a long sticky tongue lashes out and snaps back
            length = 4+st*22
            mouth = (hx+8, hy-6)
            tip = (mouth[0]+length, mouth[1]+1+st*2)
            taper(a, [T(*p) for p in bez(mouth, (mouth[0]+length*.5, mouth[1]+3+st*4), tip, 9)], PURPLE, 7, 5)
            a.ball(*T(*tip), 5.5, 5, PURPLE, ang)
            a.ellipse(tip[0]-1, tip[1]+1, 1.4, 1.4, 29)
    a.ball(*T(hx, hy), 17, 12, SKIN, ang)
    for x in (hx-7, hx+6):
        a.ball(*T(x, hy+10), 7, 8, SKIN, ang)
        a.eye(*T(x, hy+11), clip, n, .9)
    a.ellipse(*T(hx-10, hy-3), 2.5, 1.5, 4)
    a.line([T(hx-9, hy-6), T(hx, hy-8), T(hx+12, hy-6)], 1)
    if clip == 'die' and n >= 4:
        motes(a, n, 3, 0, 50, 26, SKIN[2:], floor=14)
    return a


# ----------------------------------------------------------------------------------------------
# Mire Crocodile: a long armoured reptile.  It rears back with the jaws open, lunges forward and snaps them shut, the
# tail whipping the other way.  Four splayed legs (roots under the barrel, a bent joint, planted feet, diagonal gait).
# On defeat the body sinks, the legs splay out flat, the jaw drops open and the tail slumps to the ground.
# ----------------------------------------------------------------------------------------------
def croc(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = fall
    wu, st = atk(clip, n)
    a = Painter('croc', recoil)
    ph = n*math.pi/4
    fx = st*7-wu*5
    hurt = [2, 1, 0, 0][n] if clip == 'hurt' else 0
    cy0 = mix(20+bob*.7-hurt, 15, t)                          # on defeat the body sinks to the ground
    tail_wave = (math.sin(n*math.pi/3)*3 if clip in ('idle', 'walk') else (wu*4-st*5))*(1-t)
    a.tail([(-12+fx, cy0+1), (-26+fx, mix(cy0+1, 6, t)), (-33+fx, mix(cy0+5+tail_wave, 5, t)), (-39+fx, mix(cy0+10+tail_wave, 4, t))], SKIN, 6)
    for x in (-29, -21, -13, -5, 3):
        a.poly([(x-3+fx, cy0+8), (x+fx, cy0+16), (x+4+fx, cy0+8)], 7)
    for far in (True, False):
        for front in (False, True):
            quad_leg(a, front, far, ph, clip, st, wu, cy0, fx, 9, -17, SKIN, 6, 5, t)
        if far:
            a.ball(-4+fx, cy0, 23, 12, SKIN)
            a.ball(-2+fx, cy0-6, 17, 5, BELLY)
    for front in (False, True):                              # near haunch and shoulder lie over the barrel
        a.ball((9 if front else -17)+fx+(7 if front else -7)*t, cy0-3, 6, 7, SKIN)
    hx, hy = 19+fx+st*2, cy0+5+wu*7-st*2-t*5
    gape = [5, 9, 13, 13, 1, 1, 3, 2][n] if clip == 'attack' else (2+5*t if clip == 'die' else 0)
    a.ball(hx+7, hy-6-gape, 14, 4, BARK)
    if gape > 1.5:
        a.ball(hx+8, hy-4-gape*.5, 12, 3+gape*.4, PURPLE)
    for x in (hx, hx+6, hx+12):                               # teeth hang below the upper jaw, outlined
        a.poly([(x-2, hy-5-gape), (x, hy-1-gape), (x+2, hy-5-gape)], 2, 1)
    a.ball(hx, hy, 12, 10, SKIN)
    a.ball(hx+10, hy-2+gape*.25, 12, 5, SKIN)
    a.ellipse(hx+19, hy+gape*.25, 2, 1, 1)
    a.ball(hx-2, hy+9, 6, 6, SKIN)
    a.eye(hx-2, hy+10, clip, n, .95)
    a.ellipse(hx+1, hy-3, 2, 1, 4)
    if clip == 'attack' and st > .5:                         # the water sprays off the snap
        for k in range(3):
            a.ellipse(hx+22+k*4, hy-1+k*3-st*2, 1.2, 1.2, 24)
    if clip == 'die' and n >= 4:
        motes(a, n, 3, 0, 50, 24, SKIN[2:], floor=16)
    return a


# ----------------------------------------------------------------------------------------------
# Drowned Knight: rigid sea-green plate.  It raises the sword up and back, brings it down in an arc with a trail of
# sea-green light, and recovers.  On defeat the knees buckle, the suit slumps forward, the helmet rolls off, the sword
# and shield clatter down and the motes fade.
# ----------------------------------------------------------------------------------------------
def knight(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = arc(clip, n)
    R = Rig(fall, pivot=(10, 0), sign=-1, angle=.5, lift=0, buckle=.5, start=.25)
    P = R.P
    lean = st*5-wu*3
    a = Painter('knight', recoil+lean*.5)
    ph = n*math.pi/4
    hurt = [2, 1, 0, 0][n] if clip == 'hurt' else 0
    torso = 35+bob*.6-hurt
    hy = 60+bob*.6-hurt
    for sign in (-1, 1):                                      # planted rigid greaves, feet exactly on the ground row
        sw = math.sin(ph+(0 if sign > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sw)*3.5
        hip, knee, ankle = (sign*7, 25), (sign*(8+(st*3 if sign > 0 else 0))+sw*2, 15), (sign*9+sw*5, 6+lift)
        pts = R.pts([hip, knee, ankle])
        a.limb(pts, PLATE, 6)
        if fall:
            a.ball(pts[2][0], pts[2][1], 9, 5, PLATE)
        else:
            foot(a, sign*9+sw*5, lift, 9, 5, PLATE)
    sx, sy = -25-fall*3-wu*2+st*1, 36+bob-fall*22          # shield on the left arm
    sxp, syp = P(sx, sy)
    if fall < .5:
        a.limb(R.pts([(-13, torso+4), (sx+5, sy)]), PLATE, 5)
        a.ball(sxp, syp, 11, 14, PLATE)
        a.ball(sxp, syp, 7, 9, TEAL)
        a.ellipse(sxp-2, syp+3, 3, 3, 14)
    else:                                                     # the shield slides down and leans on the ground
        g = sm((fall-.5)/.5)
        a.ball(mix(sxp, -34, g), mix(syp, 14, g), 11, 14, PLATE, -.9*g)
        a.ball(mix(sxp, -34, g), mix(syp, 14, g), 7, 9, TEAL, -.9*g)
    def sword():
        shoulder = P(14, torso+5)                                 # sword arm follows the swing arc
        if clip == 'attack':
            base = mix(mix(1.0, 1.25, wu), -.35, st)
            reach = mix(17, 24, wu)
            hand = (shoulder[0]+reach*math.cos(base), shoulder[1]+reach*math.sin(base))
            sword_ang = mix(mix(1.35, 1.8, wu), -.62, st)
        else:
            hand = P(24, 32+bob)
            sword_ang = 1.35-fall*1.6
        if fall:                                                  # dropped: the sword clatters flat on the ground
            g = sm((fall-.2)/.6)
            hand = (mix(hand[0], 33, g), mix(hand[1], 5, g))
            sword_ang = mix(sword_ang, .05, g)
        elbow = ((shoulder[0]+hand[0])/2+4, (shoulder[1]+hand[1])/2-3)
        if fall < .4:
            a.limb([shoulder, elbow, hand], PLATE, 5)
        a.ball(*hand, 5, 5, PLATE)
        dx, dy = math.cos(sword_ang), math.sin(sword_ang)
        length = 28
        tip = (hand[0]+dx*length, hand[1]+dy*length)
        if clip == 'attack' and st > .4:                          # a trail of sea-green light follows the blade
            for k in range(1, 6):
                ang_k = sword_ang+k*.32
                r_ = max(1, 3.2-k*.45)
                a.ellipse(hand[0]+math.cos(ang_k)*(length-3), hand[1]+math.sin(ang_k)*(length-3), r_, r_, GLOW[min(4, 1+k % 4)])
        a.line([(hand[0]-dx*4, hand[1]-dy*4), tip], 10, 6)
        a.line([hand, tip], 13, 4)
        a.line([(hand[0]-4*dy, hand[1]+4*dx), (hand[0]+4*dy, hand[1]-4*dx)], 17, 3)
    behind = clip == 'attack' and wu > .2 and not st
    if behind:
        sword()
    tx, ty = P(0, torso)
    a.ball(tx, ty, 16, 15, PLATE)
    a.line(R.pts([(-11, torso-5), (11, torso-5)]), 16, 2)
    a.ball(*P(-6, torso+6), 5, 3, LIGHT_PLATE)
    for x in (-15, 15):
        px, py = P(x, torso+9)
        a.ball(px, py, 8, 7, PLATE)
        a.ellipse(px, py+2, 3, 2, 7)
    hxp, hyp = P(1, hy)                                       # head: stays on until the collapse, then rolls clear
    roll = sm((fall-.3)/.7)
    hxp, hyp = mix(hxp, 42, roll), mix(hyp, 11, roll)
    hang = 1.2*roll
    a.ball(hxp, hyp, 15, 14, PLATE, hang)
    a.ball(hxp-5, hyp+6, 6, 3, LIGHT_PLATE, hang)

    def at(x, y):
        rx_, ry_ = rot(x, y, hang)
        return hxp+rx_, hyp+ry_
    a.poly([at(-13, 2), at(13, 2), at(12, -7), at(-12, -7)], 1)
    for x in (-6, 6):
        a.eye(*at(x, -1), clip, n, .8)
    if fall < .6:
        a.ellipse(hxp-12, hyp-6, 2, 1, 4)
    for x, h in [(-5, 8), (1, 12), (6, 7)]:
        a.limb([at(x, 12), at(x-3+roll*7, 12+h*(1-roll*.8))], SKIN, 3)
    if not behind:
        sword()
    if clip == 'die' and n >= 2:
        a.line(R.pts([(-7, torso+9), (-2, torso+4), (-5, torso-1), (4, torso-7)]), 10, 2)
        for k in range(max(0, 7-n)):
            a.ellipse(-16+k*7, torso*(1-.5*R.tb)+18+(n-2)*2+k % 2*3, 1, 1, GLOW[1+k % 4])
    return a


# ----------------------------------------------------------------------------------------------
# Mire Hydra: a teal body with three necks.  The side heads draw back, the central head rears and strikes forward and
# down with open jaws, the right head snaps a beat later.  Four legs with planted feet.  On defeat the necks drop at
# different times and the heads lie across the intact body.
# ----------------------------------------------------------------------------------------------
def hydra(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    a = Painter('hydra', recoil+st*3-wu*2)
    ph = n*math.pi/4
    hurt = [2, 1, 0, 0][n] if clip == 'hurt' else 0
    cy = 20-fall*5-hurt+bob*.4
    tail_wave = (math.sin(n*math.pi/3)*3 if clip in ('idle', 'walk') else (wu*3-st*4))*(1-t)
    a.tail([(-13, cy), (-25, cy-1), (-33, cy+3+tail_wave), (-40, cy+10+tail_wave)], TEAL, 6)
    for j, x in enumerate((-19, -6, 9, 20)):                  # roots under the barrel, bent joint, planted feet, diagonal gait
        s = ph+(0 if j % 2 else math.pi)
        swing = math.sin(s) if clip == 'walk' else 0
        step, lift = swing*3, max(0, swing)*3.5
        root, knee = (x, cy-3), (x+(4 if j < 2 else -3)+step*.3, cy-9)
        ft = x+3+step
        a.limb([root, knee, (ft-1, 7+lift*.8+fall*3)], TEAL, 5)
        foot(a, ft+2, lift, 6, 3, TEAL)
    a.ball(-2, cy, 26, 13, TEAL)
    a.ball(1, cy-6, 18, 5, [7, 8, 9])
    for x in (-19, -10, 0, 10):
        a.poly([(x-4, cy+10), (x, cy+20), (x+5, cy+10)], 26)
    late = max(0., ATTACK[n-1])/4 if clip == 'attack' and n > 0 else 0.
    heads = [(-16, -22, 51, 11, 0), (3, 0, 66, 13, .24), (17, 23, 48, 11, .12)]
    for j, (root, hx0, hy0, size, delay) in enumerate(heads):
        f = max(0, min(1, (fall-delay)/(1-delay)))
        sway = math.sin(n*math.pi/3+j)*2 if clip in ('idle', 'walk') else 0
        hx, hy = hx0+sway+f*(9 if j == 0 else -8 if j == 1 else 3), hy0+bob*.4-f*(hy0-14-j*3)
        gape = 0.
        lunge = 0.
        if clip == 'attack':
            if j == 1:                                        # central head: rears back and up, strikes forward and down
                hx += -9*wu+32*st
                hy += 10*wu-26*st
                gape, lunge = st*11+wu*3, st
            elif j == 0:                                      # left head draws back
                hx += -3*wu-2*st
                hy += -5*wu
            else:                                             # right head snaps a beat later
                hx += -6*wu+12*late
                hy += -2*wu-8*late
                gape, lunge = late*8+wu*3, late
        base = (root, cy+6)
        ctrl = (mix(root, hx, .25)-3, max(cy+6, hy-6)+10*(1-lunge*.9))
        for nx, ny in bez(base, ctrl, (hx-2, hy-5), 26):           # a chain of shaded balls: a round tube
            a.ball(nx, ny, 5.5, 5.5, SKIN)
        for x_ in (-5, 3):
            a.poly([(hx+x_-3, hy+size-2), (hx+x_-1, hy+size+7), (hx+x_+3, hy+size-2)], 26)
        a.ball(hx+5, hy-7-gape, 9, 3, BARK)
        if gape > 1.5:
            a.ball(hx+6, hy-4, 7, 2+gape*.5, PURPLE)
        a.ball(hx, hy, size, size*.85, SKIN)
        a.ball(hx+7, hy-3, 7, 4, SKIN)
        if gape > 1.5:
            for sx in (hx+4, hx+9):                            # fangs over the jaw, outlined
                a.poly([(sx-1.6, hy-7-gape*.4), (sx+1.6, hy-7-gape*.4), (sx, hy-10-gape*.5)], 2, 1)
        a.eye(hx-1, hy+2, clip, n, .8 if j == 1 else .7)
        a.ellipse(hx-6, hy-4, 2, 1, 4)
        a.ellipse(hx+12, hy-1, 1, 1, 1)
    if clip == 'attack' and st > .5:
        for k in range(3):
            a.ellipse(26+st*34+k*4, 18+k*2, 1.2, 1.2, 24)
    if clip == 'die' and n >= 4:
        motes(a, n, 3, 0, 50, 24, TEAL[2:], floor=24)
    return a


# ----------------------------------------------------------------------------------------------
# Gloomroot Colossus: rigid bark.  It lifts both fists overhead, hammers them down (roots burst from the ground) and
# recovers.  On defeat the knees buckle, the trunk splits and slumps, branches drop, the heart goes out and the moss
# wilts.
# ----------------------------------------------------------------------------------------------
def gloomroot(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = atk(clip, n)
    R = Rig(fall, pivot=(0, 0), sign=1, angle=.4, lift=0, buckle=.4, start=.3)
    P = R.P
    lean = st*5-wu*3
    a = Painter('gloomroot', recoil+lean*.4)
    ph = n*math.pi/4
    hurt = [2, 1, 0, 0][n] if clip == 'hurt' else 0
    torso = 37+bob*.5-wu*1-st*2-hurt
    for sign in (-1, 1):                                       # legs and root toes planted on the ground row
        sw = math.sin(ph+(0 if sign > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sw)*3.5
        fx_ = sign*(11+fall*3)+sw*3*sign
        pts = R.pts([(sign*10, torso-10), (sign*13, 17), (fx_, 7+lift)])
        a.limb(pts, BARK, 10)
        if fall:
            a.ball(pts[2][0], pts[2][1]-1, 9, 5, BARK)
        else:
            foot(a, fx_, lift, 9, 5, BARK)
            for k in range(3):                                 # root toes rest on the ground row too
                foot(a, fx_+(k-1)*8, lift, 3, 3, BARK)
    sh_r, sh_l = P(18, torso+7), P(-18, torso+7)               # arms: rest / both fists overhead / hammered down / slack
    rest_r, rest_l = (29, 23+bob), (-30, 23+bob)
    up_r, up_l = (14, 91), (-12, 89)
    down_r, down_l = (36, 9), (28, 9)
    hr = (mix(mix(rest_r[0], up_r[0], wu), down_r[0], st), mix(mix(rest_r[1], up_r[1], wu), down_r[1], st))
    hl = (mix(mix(rest_l[0], up_l[0], wu), down_l[0], st), mix(mix(rest_l[1], up_l[1], wu), down_l[1], st))
    if fall:
        hr = P(mix(29, 33, fall), mix(23, 9, fall))
        hl = P(mix(-30, -26, fall), mix(23, 9, fall))
    if st > .5:                                                # roots burst from the ground beside the fists
        for k in range(4):
            bx = 30+k*7+(n % 2)
            a.poly([(bx-3, 0), (bx+(k % 2)*2-1, 10+k % 3*3+st*4), (bx+3, 0)], BARK[1], BARK[0])
            a.poly([(bx-1, 1), (bx+(k % 2)*2-1, 8+k % 3*3+st*3), (bx+1, 1)], BARK[3])

    def arm(sh, h, sg):
        mid = ((sh[0]+h[0])/2+sg*5*(1-.6*(wu+st)), (sh[1]+h[1])/2-3)
        a.limb(bez(sh, mid, h, 4), BARK, 9)
        a.ball(*h, 10, 9, BARK)
    arm(sh_l, hl, -1)
    tx, ty = P(0, torso)
    a.ball(tx, ty, 22, 20, BARK)
    for x in (-13, -5, 5, 13):
        a.line(R.pts([(x, torso-11), (x-2, torso+11)]), 15, 2)
    a.ball(*P(1, torso), 8, 10, [15, 16, 17])
    if fall < .9:
        a.ball(*P(1, torso+1), 5, 7, GLOW[:max(2, 5-int(fall*4))])
        if fall < .2:
            a.ellipse(*P(0, torso+4), 1, 2, 3)
    for x in (-17, 17):
        px, py = P(x, torso+12)
        a.ball(px, py, 9, 8, BARK)
        a.ball(px, py+4, 8, 4, SKIN)
    hxp, hyp = P(lean*.3, 63+bob*.4-wu*2-st*5-hurt)
    roll = sm((fall-.4)/.6)
    hxp, hyp = mix(hxp, 12, roll), mix(hyp, 13, roll)
    a.ball(hxp, hyp, 16, 14, BARK)
    a.ball(hxp-4, hyp+9, 13, 6, SKIN)
    a.face(hxp, hyp, clip, n, .85)
    for x, y in [(-7, 17), (6, 16)]:
        stalk = (hxp+x, hyp+y-4-fall*3)
        a.limb([(hxp+x, hyp+10), stalk], BARK, 3)
        a.ball(stalk[0]-fall*3, stalk[1]+3, 6, 3, PURPLE)
        a.ellipse(stalk[0]-2, stalk[1]+4, 1, 1, 3)
    arm(sh_r, hr, 1)
    if clip == 'die':
        if n >= 2:
            a.line(R.pts([(-5, torso+17), (0, torso+10), (-3, torso+1), (5, torso-10)]), 15, 3)
        for k in range(5):                                      # heavy branch pieces fall and settle
            x = -23+k*10+(n-1)*(1 if k % 2 else -1)*.6
            y = max(4, 54-k % 3*10-n*5)
            a.poly([(x-2, y+4), (x+3, y-2), (x, y-5)], 7 if n < 4 else 6)
    if clip == 'attack' and wu > .5:
        motes(a, n, 3, 0, 60, 30, GLOW[2:], floor=60)
    return a


DRAW = dict(toad=toad, croc=croc, knight=knight, hydra=hydra, gloomroot=gloomroot)


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
        np.savez_compressed(ROOT/f'scripts/fen_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT/f'scripts/fen_slime_{kind}_raw.npz', **data)
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
        dest = ASSETS/f'fen_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'fen.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 170 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    """Compare the installed atlases directly to the saved editor frames, not to the drawers."""
    meta = json.loads((ASSETS/'fen.txt').read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS/f'fen_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n*kw, row*kh, (n+1)*kw, (row+1)*kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset+n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


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
    {'preview': preview, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
