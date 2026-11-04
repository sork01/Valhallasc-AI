#!/usr/bin/env python3
"""Wyrdwood art, second pass (v2): Greenmeadow slime style, redrawn from scratch.

preview | extents | build | refresh | export | verify.  Rigid armour/stone, animal anatomy and cloth move by joints, never
by universal squash.  Every planted hoof, talon, boot and robe hem rests exactly on the anchor row (Painter y=0), so
nothing floats (QUADRUPED-GROUNDING).  Each kind has eight distinct attack frames (wind-up, strike, recovery) and eight
distinct death frames, and its own frame size where the art needs one (KIND_FRAMES, docs/kind-frames.md).  The v1
sources (Beta 1.39.7) stay registered in wyrd_slime_v1_sources.txt.  Export preserves editor edits.
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
OUT = ROOT/'test-results/wyrd-slime'
REGISTRY = ROOT/'scripts/wyrd_slime_sources.txt'
PREFIX = 'valhallasc_wyrd_slime_style_b_'
KINDS = ['boar', 'crow', 'troll', 'weaver', 'ram', 'oakhorn', 'hrungnir']
NAMES = dict(boar='Rotfang Boar', crow='Gallowcrow', troll='Mosshide Troll', weaver='Wyrdweaver', ram='Stormram',
             oakhorn='Oakhorn', hrungnir='Hrungnir')
W = H = 96                       # zone-wide frame (manifest fallback)
AX, AY = 48, 90
# kind -> (w, h, ax, ay); the anchor's y is the ground row, its x the creature's centre (+2).  Measured with `extents`.
KIND_FRAMES = dict(boar=(110, 74, 47, 68), crow=(124, 76, 50, 70), troll=(144, 112, 52, 106), weaver=(144, 98, 45, 92),
                   ram=(130, 74, 56, 68), oakhorn=(124, 104, 45, 98), hrungnir=(132, 108, 58, 102))
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
           '#40201f', '#7a3334', '#b95154', '#e98c83', '#ffd0ae',
           '#33201d', '#65402b', '#9b6541', '#ca9361', '#f2c993',
           '#34455c', '#6c88a4', '#a8c6db', '#d6eafa', '#f4fcff',
           '#141627', '#292d50', '#4b5079', '#7a82a4', '#afb8d6']
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
BONE = list(range(5, 10))
PLATE = list(range(10, 15))
PURPLE = list(range(15, 20))
TEAL = list(range(20, 25))
GOLD = list(range(25, 30))
GREEN = list(range(30, 35))
RED = list(range(35, 40))
BROWN = list(range(40, 45))
FUR = list(range(45, 50))
FEATHER = list(range(50, 55))
ICE = TEAL
EYE_WHITE = 3          # colour-exact eye-white palette index (#fffbea)


def mix(a, b, t):
    return a+(b-a)*t


def mixp(p, q, t):
    return (mix(p[0], q[0], t), mix(p[1], q[1], t))


def rot(x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return x*c-y*s, x*s+y*c


def rotpts(points, ang, ox=0., oy=0.):
    return [(ox+rot(x-ox, y-oy, ang)[0], oy+rot(x-ox, y-oy, ang)[1]) for x, y in points]


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


def hurtof(clip, n):
    return [3, 2, 1, 0][n] if clip == 'hurt' else 0


def foot(a, x, lift, rx, ry, ramp):
    """A planted foot: integer ry and centre y = ry, so its lowest pixel is the ground row when lift is 0."""
    a.ball(x, ry+lift, rx, ry, ramp)


def spark(a, x, y, col=2, r=3):
    y = max(y, r)
    a.line([(x-r, y), (x+r, y)], col, 1)
    a.line([(x, y-r), (x, y+r)], col, 1)
    a.line([(x-r+1, y-r+1), (x+r-1, y+r-1)], col, 1)
    a.line([(x-r+1, y+r-1), (x+r-1, y-r+1)], col, 1)


def dust(a, x, n, count=4, col=BONE):
    """Little puffs lifted off the ground row; positions depend on n so consecutive frames differ."""
    for k in range(count):
        a.ellipse(x+k*5+n*2, 2+(k*3+n) % 5, 2, 2, col[(k+n) % len(col)])


# ----------------------------------------------------------------------------------------------
# The three four-legged animals share a skeleton (shoulder and haunch roots hidden under the barrel, forward stifle,
# backward hock, tapered shin, a hoof whose lowest pixel is the ground row) but each has its own attack and its own death.
# Both far hooves rest on the SAME row as the near ones (0 px higher): the far pair is darker and shifted right, never
# lifted, because any lift reads as floating (QUADRUPED-GROUNDING).
# ----------------------------------------------------------------------------------------------
Q = dict(boar=dict(bb=15, rx=23, ry=16, ramp=BROWN, hoof=BROWN[:3], w=4, fw=3, ankle=9),
         ram=dict(bb=15, rx=23, ry=16, ramp=FUR, hoof=PLATE[:3], w=4, fw=3, ankle=9),
         oakhorn=dict(bb=22, rx=23, ry=14, ramp=BROWN, hoof=BROWN[:3], w=3, fw=2, ankle=10))


FAR_DX = 6      # the far pair stands this much to the right: enough that near and far lower legs never merge into one pole


def leg_rest(sp, front, far, step=0., lift=0., lean=0.):
    d = FAR_DX if far else 0
    X = (9 if front else -21)+d
    root = (X+lean*.8, sp['bb']+11 if sp['bb'] < 20 else sp['bb']+9)
    ank_y = sp['ankle']+lift*.7
    ankle = (X+(3 if front else -2)+step*.7, ank_y)
    knee = (X+(-2 if front else 7)+step*.25+lean*.4, (root[1]+ank_y)/2-1+lift*.3)
    return [root, knee, ankle, (X+(4 if front else -1)+step, 3+lift)]


def draw_leg(a, sp, pts, far, hoof=True):
    ramp = sp['ramp'][:3] if far else sp['ramp']
    w = sp['fw'] if far else sp['w']
    a.limb(pts[:3], ramp, w)
    a.limb(pts[2:], ramp, max(2, w-1))
    if hoof:
        foot(a, pts[3][0], pts[3][1]-3, 3 if far else 3.5, 3, sp['hoof'])
    else:
        a.ball(pts[3][0], pts[3][1], 3 if far else 3.5, 3, sp['hoof'])


def tusk(a, x, y, ang=0.):
    pts = rotpts([(x-3, y-3), (x+3, y+5), (x+2, y-2)], ang, x, y-3)
    a.poly(pts, 5)
    pts = rotpts([(x-2, y-2), (x+2, y+4), (x+1, y-2)], ang, x, y-3)
    a.poly(pts, 9)


# per-frame attack tables (index = frame): body lean, head rise, head angle, front-foot step/lift, body drop
BOAR_A = dict(lean=[-3, -6, -8, 3, 10, 7, 3, 0], hdy=[-1, -4, -7, -6, -8, 6, 2, 0], tusk=[0, 0, 0, -.2, -.5, 1.0, .5, 0],
              fstep=[0, -3, -5, 6, 7, 4, 1, 0], flift=[0, 4, 0, 2, 0, 0, 0, 0], drop=[0, 2, 4, 1, 3, 0, 0, 0])
RAM_A = dict(lean=[-3, -7, -11, 6, 13, 9, 4, 0], hdy=[3, 8, 13, 0, -3, -2, 0, 0], hang=[0, .12, .25, -.1, -.35, -.2, -.05, 0],
             flift=[0, 4, 5, 0, 0, 0, 0, 0], drop=[0, 2, 4, 0, 2, 1, 0, 0], fstep=[0, -1, -2, 4, 6, 3, 1, 0])
STAG_A = dict(theta=[.74, .55, .30, 1.15, 1.5, 1.05, .85, .74], lean=[0, -2, -4, 3, 6, 4, 1, 0], drop=[0, 0, 1, 0, 2, 1, 0, 0],
              fstep=[0, -1, -2, 3, 5, 3, 1, 0], flift=[0, 2, 3, 0, 0, 0, 0, 0])
ATK = dict(boar=BOAR_A, ram=RAM_A, oakhorn=STAG_A)
THETA0 = .74       # the stag's resting neck angle (from vertical, towards the front)

# death tables.  by = body centre height; head (hx, hy); `ff`/`hf` blend the front/hind legs from standing to tucked (kneeling /
# sitting), `fin` from there to the kind's final pose: legs up (boar, rolled onto its back), legs splayed flat (ram), none (stag,
# which stays kneeling with its head sinking to the ground).
BOAR_D = dict(by=[31, 30, 27, 23, 20, 17.5, 16.5, 16], hx=[22, 22, 23, 24, 25, 26, 27, 27], hy=[38, 37, 33, 27, 22, 18, 15, 13],
              ff=[0, 0, .6, 1, 1, 1, 1, 1], hf=[0, 0, 0, .4, 1, 1, 1, 1], fin=[0, 0, 0, 0, .25, .55, .85, 1])
RAM_D = dict(by=[31, 31, 28, 24, 20, 17, 16, 16], hx=[22, 23, 22, 22, 23, 25, 27, 28], hy=[38, 41, 36, 31, 25, 19, 14, 12],
             ff=[0, 0, 0, .3, .8, 1, 1, 1], hf=[0, 0, .7, 1, 1, 1, 1, 1], fin=[0, 0, 0, 0, .3, .65, .9, 1])
STAG_D = dict(by=[36, 35, 33, 30, 26, 22, 18.5, 16], theta=[.74, .8, 1.0, 1.3, 1.55, 1.75, 1.85, 1.9], ff=[0, .3, .8, 1, 1, 1, 1, 1],
              hf=[0, 0, 0, .4, .8, 1, 1, 1], fin=[0] * 8)
DEATH = dict(boar=BOAR_D, ram=RAM_D, oakhorn=STAG_D)


def leg_x(front, far):
    return (9 if front else -21)+(FAR_DX if far else 0)


def tucked(front, far):
    """Kneeling (front) or sitting (hind) leg: absolute points, every hoof centre at height 3 so it rests on the ground row."""
    X = leg_x(front, far)
    if front:
        return [(X, 0), (X+6, 6), (X-1, 4), (X-6, 3)]
    return [(X, 0), (X+9, 7), (X-4, 5), (X-13, 3)]


def final_pose(kind, front, far, by):
    X = leg_x(front, far)
    if kind == 'boar':                                   # on its back, hooves in the air
        if front:
            return [(X, by), (X+4, by+9), (X+2, by+17), (X+5, by+24)]
        return [(X, by), (X-3, by+9), (X-1, by+17), (X-5, by+23)]
    if kind == 'ram':                                    # flat on its belly, forelegs forward, hind legs back
        if front:
            return [(X, 7), (X+9, 5), (X+17, 4), (X+25, 3)]
        return [(X, 7), (X-9, 5), (X-17, 4), (X-24, 3)]
    return None


def leg_death(sp, front, far, g, fin, by, kind):
    X = leg_x(front, far)
    rest = leg_rest(sp, front, far)
    rest[0] = (X, by-5)
    tuck = tucked(front, far)
    pts = [mixp(rest[i], tuck[i], g) for i in range(4)]
    pts[0] = (X, by-5)
    end = final_pose(kind, front, far, by)
    if end and fin:
        pts = [mixp(pts[i], end[i], fin) for i in range(4)]
    return pts


def pose(kind, clip, n):
    sp = Q[kind]
    bb, ry = sp['bb'], sp['ry']
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    atk = clip == 'attack'
    A = ATK[kind]
    P = dict(lean=0., by=bb+ry+bob*.7, hang=0., tusk=0., theta=THETA0, legs=[], hdy=0.)
    if clip == 'die':
        D = DEATH[kind]
        P['by'] = D['by'][n]
        P['lean'] = 0.
        if kind == 'oakhorn':
            P['theta'] = D['theta'][n]
        else:
            P['hx'], P['hy'] = D['hx'][n], D['hy'][n]
        for far in (True, False):
            for front in (False, True):
                ff = D['ff'][n] if front else D['hf'][n]
                P['legs'].append((front, far, leg_death(sp, front, far, ff, D['fin'][n], P['by'], kind)))
        return P
    P['lean'] = (A['lean'][n] if atk else 0)+(recoil if clip == 'hurt' else 0)
    P['by'] -= (A['drop'][n] if atk else 0)+hurt*.6
    if atk and kind == 'oakhorn':
        P['theta'] = A['theta'][n]
    if clip == 'hurt':
        P['hdy'] = hurt*1.4
        P['hang'] = .12*hurt
    if atk and kind == 'boar':
        P['hdy'] = A['hdy'][n]
        P['tusk'] = A['tusk'][n]
    if atk and kind == 'ram':
        P['hdy'] = A['hdy'][n]
        P['hang'] = A['hang'][n]
    for far in (True, False):
        for front in (False, True):
            ph = (0 if front else math.pi)+(math.pi if far else 0)
            sw = math.sin(n*math.pi/4+ph) if clip == 'walk' else 0
            step = sw*(3.5 if kind == 'oakhorn' else 3)
            lift = max(0, sw)*(4 if kind == 'oakhorn' else 3)
            if atk and front:
                step += A['fstep'][n]*(1 if not far else .6)
                lift += A['flift'][n]*(1 if not far else 0)
            if atk and not front and not far:
                step -= A['lean'][n]*.15
            P['legs'].append((front, far, leg_rest(sp, front, far, step, lift, P['lean'])))
    return P


def quad(kind, clip, n):
    sp = Q[kind]
    ramp, rx, ry = sp['ramp'], sp['rx'], sp['ry']
    P = pose(kind, clip, n)
    stride, bob, recoil, fall = motion(clip, n)
    by, lean = P['by'], P['lean']
    a = Painter(kind, 0)
    dead_late = clip == 'die' and n >= 4
    for far in (True, False):
        for front, f, pts in P['legs']:
            if f == far:
                draw_leg(a, sp, pts, far)
    bx = -5+lean*.5
    a.ball(bx, by, rx, ry, ramp)
    a.ball(bx-8, by+7, 10, 4, ramp[1:])
    tail_y = by+4
    tail = [(bx-20, tail_y), (bx-27, tail_y+4+math.sin(n)*1.2), (bx-29, tail_y), (bx-26, tail_y-2)]
    a.line(tail, ramp[0], 3)
    a.line(tail[:-1], ramp[2], 1)
    ANIMAL[kind](a, sp, clip, n, P)
    return a


def draw_leg(a, sp, pts, far):
    ramp = sp['ramp'][:3] if far else sp['ramp']
    w = sp['fw'] if far else sp['w']
    a.limb(pts[:3], ramp, w)
    a.limb(pts[2:], ramp, max(2, w-1))
    hx, hy = pts[3]
    a.ball(hx, hy, 3 if far else 3.5, 3, sp['hoof'])


def head(a, sp, clip, n, hx, hy, hang=0.):
    ramp = sp['ramp']
    a.ball(hx, hy, 13, 12, ramp, hang)
    a.ball(hx-5, hy+6, 6, 3, ramp[1:])
    return ramp


def boar_art(a, sp, clip, n, P):
    by, lean = P['by'], P['lean']
    flipped = clip == 'die' and n >= 5
    if flipped:                                          # on its back: the pale belly faces up, no bristles or moss
        a.ball(-5, by+5, 17, 7, BROWN[2:])
    else:
        for j in range(6):
            x = -23+j*6+lean*.5
            a.poly([(x, by+11), (x+2, by+21-j % 2*3), (x+7, by+13)], 25)
        for x, dy in [(-17, 3), (-5, 8), (5, 2)]:
            a.ball(x+lean*.5, by+dy, 3.5, 3, GREEN)
    a.ball(12+lean*.6, by+2, 11, 11, sp['ramp'])         # shoulder: joins the head to the barrel at every head height
    hx = P.get('hx', 22+lean)
    hy = P.get('hy', by+7+P['hdy'])
    head(a, sp, clip, n, hx, hy, P['hang'])
    a.poly([(hx-10, hy+6), (hx-13, hy+18), (hx-2, hy+10)], BROWN[1])
    a.poly([(hx+3, hy+9), (hx+9, hy+16), (hx+9, hy+5)], BROWN[2])
    a.face(hx+1, hy, clip, n, .73)
    a.ball(hx+6, hy-7, 8, 4.8, RED)
    a.ellipse(hx+10, hy-6, 1.1, 1, 1)
    ta = P['tusk']
    tusk(a, hx+2, hy-8, ta)
    tusk(a, hx+12, hy-8, ta)
    if clip == 'attack' and n in (4, 5, 6):
        dust(a, hx-4+(n-4)*2, n, 4)
    if clip == 'attack' and n == 4:
        spark(a, hx+14, hy-9, 2, 3)


def ram_art(a, sp, clip, n, P):
    by, lean = P['by'], P['lean']
    for j in range(7):
        a.ball(-23+j*6+lean*.5, by+8+(j % 2)*3, 7, 7, FUR)
    for j in range(3):
        a.ball(-21+j*13+lean*.5, by-2, 7, 6, FUR)
    a.ball(12+lean*.6, by+2, 11, 11, sp['ramp'])
    hx = P.get('hx', 22+lean)
    hy = P.get('hy', by+7+P['hdy'])
    hang = P['hang']
    head(a, sp, clip, n, hx, hy, hang)
    for sign, off in [(-1, -6), (1, 7)]:
        ox, oy = rot(off, 9, hang)
        a.ball(hx+ox, hy+oy, 8, 8, GOLD)
        a.ball(hx+ox+sign, hy+oy-1, 4.5, 4.5, PLATE)
        a.line([(hx+ox-3, hy+oy+4), (hx+ox+3, hy+oy+4)], 27, 1)
    if clip != 'die' or n < 5:
        a.line([(-12+lean*.5, by+18), (-8+lean*.5, by+24), (-3+lean*.5, by+19), (1+lean*.5, by+26)], 23 if n % 2 else 24, 1)
    a.face(hx+1, hy, clip, n, .73)
    a.ball(hx+6, hy-7, 8, 4.8, PLATE)
    a.ellipse(hx+10, hy-6, 1.1, 1, 1)
    if clip == 'attack' and n in (4, 5):
        tip = (hx+18, hy+4)
        spark(a, tip[0], tip[1], 24, 5)
        a.line([(tip[0]+2, tip[1]+6), (tip[0]+7, tip[1]+10), (tip[0]+5, tip[1]+14), (tip[0]+11, tip[1]+17)], 23, 1)
        a.line([(tip[0]+3, tip[1]-3), (tip[0]+10, tip[1]-6), (tip[0]+8, tip[1]-10)], 24, 1)


def oak_art(a, sp, clip, n, P):
    by, lean = P['by'], P['lean']
    a.ball(-4+lean*.5, by+7, 15, 6, GREEN)
    a.line([(-17+lean*.5, by+8), (-5+lean*.5, by+12), (10+lean*.5, by+8)], 28, 1)
    th = P['theta']
    N = (10+lean*.6, by+2)
    L = 17.7
    hx, hy = N[0]+L*math.sin(th), N[1]+L*math.cos(th)
    if clip == 'die':                                   # a lowered head rests on the ground in front
        hy = max(hy, 12.5)
    tilt = -(th-THETA0)
    a.limb([N, (mix(N[0], hx, .5)+2, mix(N[1], hy, .5)+2), (hx-4, hy-1)], BROWN, 9)
    head(a, sp, clip, n, hx, hy, 0)
    # antlers: rotated with the neck angle, leaves shed independently
    for sg in (-1, 1):
        local = [(sg*6, 9), (sg*11, 19), (sg*9, 29)]
        tr = [(hx+x, hy+y) for x, y in rotpts(local, tilt, 0, 0)]
        a.limb(tr, BROWN, 3)
        b1 = rotpts([(sg*10, 19), (sg*19, 26)], tilt, 0, 0)
        b2 = rotpts([(sg*11, 23), (sg*16, 32)], tilt, 0, 0)
        a.line([(hx+x, hy+y) for x, y in b1], 26, 3)
        a.line([(hx+x, hy+y) for x, y in b2], 28, 2)
        for j, (dx, dy) in enumerate(rotpts([(sg*19, 26), (sg*9, 29), (sg*16, 32)], tilt, 0, 0)):
            if clip == 'die' and n >= 2+j+(sg > 0)*2:        # shed leaves drop to the ground one by one
                fall_n = n-(2+j+(sg > 0)*2)
                lx = hx+dx-sg*(3+fall_n*2)
                ly = max(3, hy+dy-(fall_n+1)**2*3)
                a.ball(lx, ly, 4, 2.7, RED if j % 2 else GOLD)
            else:
                a.ball(hx+dx, hy+dy, 4, 2.7, RED if j % 2 else GOLD)
    a.poly([(hx-10, hy+6), (hx-13, hy+18), (hx-2, hy+10)], BROWN[1])
    a.poly([(hx+3, hy+9), (hx+9, hy+16), (hx+9, hy+5)], BROWN[2])
    a.face(hx+1, hy, clip, n, .73)
    a.ball(hx+6, hy-7, 8, 4.8, BONE)
    a.ellipse(hx+10, hy-6, 1.1, 1, 1)



# ----------------------------------------------------------------------------------------------
# shared swing keyframes (club, fists): frames 0-2 rise, 3 mid-swing, 4-5 impact, 6-7 recovery
# ----------------------------------------------------------------------------------------------
ATTACK = [-1.5, -3, -4, .5, 4, 3.5, 1.5, 0]
ARC = [-.35, -.7, -1, .25, 1, .95, .5, 0]
SW = [(.3, 0), (.65, 0), (1, 0), (1, .55), (0, 1), (0, .9), (0, .45), (0, 0)]


def arc(clip, n):
    if clip != 'attack':
        return 0., 0.
    return max(0., -ARC[n]), max(0., ARC[n])


def sw(clip, n):
    return SW[n] if clip == 'attack' else (0., 0.)


def swp(w, rest, up, down):
    return mixp(mixp(rest, up, w[0]), down, w[1])


def feather_wing(a, sx, sy, ang, spread, ramp, length=24, far=False):
    """A fan of five tapered primaries from the shoulder (sx, sy); ang = direction of the middle feather, CCW from +x.
    An open wing (pointing up or forward) is longer and fans wider than a folded one."""
    openness = max(0., min(1., (ang+2.6)/3.6))
    length = length*(1+.55*openness)
    spread = spread*(1+.9*openness)
    tips = []
    for k in range(5):
        th = ang+(k-2)*spread
        L = length+(k % 2)*3-abs(k-2)
        tips.append((th, (sx+L*math.cos(th), max(1.5, sy+L*math.sin(th)))))
    a.poly([(sx, sy)]+[t for _, t in tips], ramp[1], outline=ramp[0])           # the wing's membrane, so a spread wing is solid
    for th, tip in tips:
        px, py = -math.sin(th), math.cos(th)
        wd = 5.5+openness*2
        a.poly([(sx+px*wd, sy+py*wd), tip, (sx-px*wd, sy-py*wd)], ramp[1 if far else 2], outline=ramp[0])
        a.line([(sx+px*1.5, sy+py*1.5), tip], ramp[3 if not far else 2], 1)
    a.ball(sx, sy, 8, 7, ramp)


# ----------------------------------------------------------------------------------------------
# Gallowcrow: a dark crow on gold talons.  It crouches and cranes back with both wings thrown up, stabs its beak down at the
# ground in front with the wings sweeping forward, snaps, and settles.  On defeat it tips forward beak-first, one wing
# stretches flat along the ground, a talon sticks up and loose feathers drift down.
# ----------------------------------------------------------------------------------------------
CROW_A = dict(lean=[-2, -5, -7, 4, 9, 6, 2, 0], drop=[1, 4, 3, 0, 9, 6, 2, 0], hx=[15, 10, 6, 20, 30, 29, 21, 15],
              hy=[10, 15, 19, 8, -5, -3, 5, 10], wing=[-2.1, -.4, 1.5, .5, -.7, -1.3, -2.0, -2.6], gap=[0, 0, 5, 0, 7, 3, 0, 0])
CROW_D = dict(by=[28, 27, 25, 22, 19, 16.5, 15.5, 15], hx=[15, 14, 15, 17, 20, 22, 23, 23], hy=[10, 10, 8, 4, -1, -4, -5, -5],
              wing=[-2.6, -1.0, .2, -.2, -.9, -1.6, -2.6, -3.0], lean=[0, 1, 1, 2, 3, 4, 4, 4])


def crow(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    a = Painter('crow', 0)
    atk = clip == 'attack'
    die = clip == 'die'
    if atk:
        lean, drop, (ox, oy), wang, gap = CROW_A['lean'][n], CROW_A['drop'][n], (CROW_A['hx'][n], CROW_A['hy'][n]), CROW_A['wing'][n], CROW_A['gap'][n]
    elif die:
        lean, drop, (ox, oy), wang, gap = CROW_D['lean'][n], 28-CROW_D['by'][n], (CROW_D['hx'][n], CROW_D['hy'][n]), CROW_D['wing'][n], 0
    else:
        lean, drop, (ox, oy), wang, gap = recoil, 0, (15, 10), -2.6+(math.sin(n*math.pi/4)*.18 if clip == 'walk' else bob*.1), 0
        if clip == 'hurt':
            drop, (ox, oy), wang = -hurt*.6, (15-hurt, 10+hurt*1.5), -2.6+hurt*.45
    by = 28+bob*.8-drop+abs(stride)*.8
    # talons: planted, one lifts in the walk; on defeat one stiff leg points up
    for sg in (-1, 1):
        sgs = math.sin(n*math.pi/4+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sgs)*3.5
        fx = sg*5+sgs*2.5+(lean*.35 if atk else 0)
        if die and n >= 3:
            fx = sg*5+4
            if sg > 0:                                        # stiff leg in the air
                a.limb([(sg*4+lean*.5, by-8), (sg*7, by+2), (sg*11+fall*3, by+9)], GOLD, 2)
                a.line([(sg*11+fall*3-2, by+9), (sg*11+fall*3+3, by+12)], 27, 2)
                continue
        a.limb([(sg*4+lean*.5, by-9), (sg*4+lean*.2, (by-9)*.45+lift*.5), (fx, 2+lift)], GOLD, 2)
        foot(a, fx, lift, 4, 2, GOLD)
    # far wing then body then near wing
    feather_wing(a, -9+lean*.5, by+2, wang+.5, .21, FEATHER, 21, far=True)
    a.ball(0+lean*.5, by, 18, 15, FEATHER)
    a.ball(-5+lean*.5, by+9, 9, 4, FEATHER[1:])
    a.line([(0+lean*.5, by-8), (2+lean*.5, max(4, by-17))], 26, 1)
    a.ball(2+lean*.5, max(3, by-18), 3, 2, BONE)
    hx, hy = ox+lean*.5, by+oy
    hy = max(hy, 13.5) if (die or atk) else hy
    a.limb([(8+lean*.5, by+4), ((8+hx)/2+lean*.2, by+6+oy*.3), (hx-3, hy-2)], FEATHER, 9)
    a.ball(hx, hy, 12, 12, FEATHER)
    for j in range(3):
        a.poly([(hx-9+j*6, hy+8), (hx-12+j*7, hy+20-j*2), (hx-3+j*5, hy+8)], 51)
    a.eye(hx+2, hy+1, clip, n, 1)
    a.ellipse(hx-5, hy-5, 2.5, 1.5, 4)
    a.poly([(hx+8, hy-1+gap*.4), (hx+23, max(1.2, hy-5+gap*.2)), (hx+9, hy-5)], 27)
    a.poly([(hx+9, max(1.2, hy-6-gap)), (hx+21, max(1.2, hy-6-gap*1.4)), (hx+9, max(1.2, hy-9-gap))], 28)
    feather_wing(a, -3+lean*.5, by-1, wang, .21, FEATHER, 24)
    if atk and n in (4, 5):
        dust(a, hx+12, n, 3)
    if die:
        for j in range(3):                                    # loose feathers drift down and lie on the ground
            if n >= 2+j:
                fn = n-(2+j)
                fx = -26+j*14+fn*1.5*(1 if j % 2 else -1)
                fy = max(3, 40-fn*9-j*3)
                a.poly([(fx-3, fy), (fx+3, fy+3), (fx+4, fy+1), (fx, fy-2)], 52+j % 2)
    return a


# ----------------------------------------------------------------------------------------------
# bipeds
# ----------------------------------------------------------------------------------------------
def biped_legs(a, ramp, ph, clip, fall, wide, hip_y, rx, ry, w, st=0., wu=0., kneel=0.):
    """Hip, knee and boot; the boot's lowest pixel is the ground row.  Walk lifts one boot at a time; an attack steps the
    front boot forward and braces the rear; on defeat the knees fold under and the shins tuck."""
    for sg in (-1, 1):
        swing = math.sin(ph+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, swing)*3.5
        fx = sg*wide+swing*5+(st*7 if sg > 0 else -wu*3)
        hip = (sg*(wide-1), hip_y-fall*0)
        knee = (sg*(wide+2)+(fx-sg*wide)*.4, mix(hip_y, ry+1, .55)+lift*.5)
        ank = (fx, ry+1+lift)
        if kneel:
            fx2 = sg*(wide+6)-sg*2
            knee = (mix(knee[0], fx2+8*(1 if sg > 0 else .4), kneel), mix(knee[1], 11, kneel))
            ank = (mix(ank[0], fx2-4, kneel), mix(ank[1], ry+2, kneel))
            fx = ank[0]
        a.limb([hip, knee, ank], ramp, w)
        foot(a, fx, lift if not kneel else 0, rx, ry, ramp)


def arm_ik(sh, target, l1, l2, bend=1):
    """Two constant-length segments from the shoulder towards the target; a target beyond reach is pulled in."""
    dx, dy = target[0]-sh[0], target[1]-sh[1]
    d = math.hypot(dx, dy) or 1e-6
    d = min(d, l1+l2-.5)
    ang = math.atan2(dy, dx)
    cosb = max(-1, min(1, (l1*l1+d*d-l2*l2)/(2*l1*d)))
    b = math.acos(cosb)*bend
    elbow = (sh[0]+l1*math.cos(ang+b), sh[1]+l1*math.sin(ang+b))
    hand = (sh[0]+d*math.cos(ang), sh[1]+d*math.sin(ang))
    return elbow, hand


def club(a, hand, angle, length=21):
    dx, dy = math.cos(angle), math.sin(angle)
    end = (hand[0]+dx*length, hand[1]+dy*length)
    end = (end[0], max(end[1], 6))
    a.limb([hand, end], BROWN, 6)
    a.ball(end[0]+dx*3, max(end[1]+dy*3, 7), 9, 7, BROWN)
    a.ball(end[0]+dx*3-2, max(end[1]+dy*3, 7)+2, 3, 2, BROWN[2:])
    return end


# ----------------------------------------------------------------------------------------------
# Mosshide Troll: a moss-green brute with tusks and a club.  It heaves the club up behind its head, steps in and smashes
# it down on the ground in front (dust and chips fly), then drags it back.  On defeat the knees buckle, the club slips
# from its hand and it slumps forward onto its fists while the moss and mushroom wilt.
# ----------------------------------------------------------------------------------------------
TROLL_D = dict(by=[35, 34, 31, 27, 23, 20, 18, 17], hx=[0, 1, 3, 7, 12, 17, 20, 22], hy=[57, 56, 52, 45, 38, 32, 28, 26],
               kneel=[0, .1, .5, .9, 1, 1, 1, 1], hand=[0, .1, .4, .6, .8, .9, 1, 1])


def troll(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    wu, st = arc(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    a = Painter('troll', recoil+st*4-wu*3 if not die else 0)
    ph = n*math.pi/4
    if die:
        D = TROLL_D
        by, hx, hy, kneel, hd = D['by'][n], D['hx'][n], D['hy'][n], D['kneel'][n], D['hand'][n]
    else:
        by = 35+bob*.8-hurt*.5-st*2
        hx, hy = st*6-wu*3, 57+bob*.8-st*5-hurt*.6
        kneel, hd = 0., 0.
    biped_legs(a, GREEN, ph, clip, 0, 11, 28, 9, 4, 8, st, wu, kneel)
    a.poly([(-16, by-2), (16, by-2), (19, by-14), (-18, by-14)], 25)
    a.ball(hx*.4, by, 22, 20, GREEN)
    a.ball(hx*.4-8, by+10, 9, 5, GREEN[1:])
    w = sw(clip, n)
    lean_x, lean_y = (st*7-wu*3, -st*8+wu*2) if atk else (0, 0)
    for sg in (-1, 1):
        sh = (sg*18+hx*.4+lean_x, by+11+lean_y)
        a.ball(sh[0], sh[1]-1, 10, 8, GREEN)
        if sg > 0:
            if atk:
                tgt = swp(w, (29, 24), (19, 72), (40, 14))
            elif die:
                tgt = mixp((29, 24), (36, 5+hd*3), hd)
            else:
                tgt = (29, 24+bob)
        else:
            if atk:
                tgt = swp(w, (-29, 24), (-32, 38), (-33, 20))
            elif die:
                tgt = mixp((-29, 24), (-36, 5), hd)
            else:
                tgt = (-29, 24+bob)
        elbow, hand = arm_ik(sh, tgt, 15, 15, sg)
        a.limb([sh, elbow, hand], GREEN, 7)
        a.ball(*hand, 8, 7, GREEN)
        if sg > 0:
            if atk:
                ang = swp(w, (1.1, 0), (2.0, 0), (-.5, 0))[0]
                end = club(a, hand, ang)
                if st > .4:
                    dust(a, end[0]-6, n, 4)
                    a.line([(end[0]+6, 1), (end[0]+14, 3), (end[0]+12, 6)], 1, 1)
            elif die:
                club(a, (mix(hand[0], 44, hd), mix(hand[1], 6, hd)), mix(1.1, -.04, hd))
            else:
                club(a, hand, 1.1)
    a.ball(hx, hy, 16, 14, GREEN)
    a.ball(hx-6, hy+7, 8, 3, GREEN[1:])
    a.ball(hx+1, hy+11, 14, 4, GREEN[:4])
    a.face(hx, hy, clip, n, 1)
    tusk(a, hx+5, hy-9)
    tusk(a, hx-6, hy-9)
    # living moss and mushroom follow the head; defeat wilts the stems and drops the cap
    wilt = fall
    a.limb([(hx-7, hy+12), (hx-9-wilt*5, hy+23-wilt*9)], GREEN, 2)
    for j in range(3):
        a.ball(hx-12+j*4-wilt*4, hy+23+3*(j % 2)-wilt*(9+j*2), 3, 2.5, GREEN)
    cap_drop = wilt*(hy+20-5)*(1 if die and n >= 5 else 0)
    a.limb([(hx+7, hy+11), (hx+8+wilt*6, hy+19-wilt*8)], BONE, 2)
    a.ball(hx+8+wilt*7, max(5, hy+20-wilt*10-cap_drop*.2), 6, 3, RED)
    return a


# ----------------------------------------------------------------------------------------------
# Wyrdweaver: a hooded spinner in a violet robe, golden thread between its hands and a spindle.  It draws both hands back
# with the thread taut, then lashes the spindle out on its thread (the thread snakes after it) and reels it in.  On
# defeat the hood drops into the robe, which settles in folds, while the thread unravels and the spindle drops.
# ----------------------------------------------------------------------------------------------
WEAVE_A = dict(lh=[(-22, 40), (-28, 46), (-32, 53), (-30, 50), (-26, 44), (-24, 42), (-23, 41), (-22, 40)],
               rh=[(22, 37), (26, 44), (30, 52), (30, 46), (34, 38), (32, 38), (26, 38), (22, 37)],
               lean=[-1, -3, -4, 3, 6, 4, 1, 0], sp=[0, 0, 0, 14, 44, 40, 20, 0])


def weaver(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    lean = (WEAVE_A['lean'][n] if atk else 0)+recoil
    a = Painter('weaver', 0)
    y = 38+bob*.5-hurt*.5
    top = y
    if die:
        top = 38-fall*24
        y = top
    sway = math.sin(n*math.pi/4)*2 if clip == 'walk' else 0
    hem = 0
    # the robe is planted on the ground row; only what is above it moves
    w = 25+fall*7
    a.poly([(-13+lean*.5, y+13), (13+lean*.5, y+13), (w+sway, hem), (-w-fall*3+sway, hem)], 15)       # a flat hem on the ground row
    a.line([(-w-fall*3+sway+1, hem+1), (w+sway-1, hem+1)], 16, 1)
    a.poly([(-11+lean*.5, y+11), (-4+lean*.5, y+8), (-7, hem+2), (-22-fall*4, hem+1)], 17)
    a.poly([(5+lean*.5, y+10), (11+lean*.5, y+9), (19+fall*3, hem+2), (8, hem+1)], 16)
    for sg in (-1, 1):
        a.line([(sg*8+lean*.5, y+4), (sg*14, hem+3)], 18, 1)
    hx, hy = fall*8+lean*.8, 62+bob*.5-fall*40-hurt*.5
    if die:
        hy = max(hy, 13)
    a.ball(hx, hy, 15, 13, PURPLE)
    a.poly([(hx-13, hy+4), (hx-7, hy+23), (hx+3, hy+14), (hx+13, hy+3)], 16)
    a.ball(hx, hy-1, 11, 9, PURPLE[:2])
    a.face(hx, hy-1, clip, n, .85)
    a.line([(hx-13, hy+6), (hx+11, hy+7)], 28, 2)
    hands = []
    for sg in (-1, 1):
        if atk:
            h = (WEAVE_A['lh'] if sg < 0 else WEAVE_A['rh'])[n]
        else:
            h = (sg*(22+fall*7)+lean*.6, 37+math.sin(n*.8+sg)*2-fall*28)
        a.limb([(sg*11+lean*.5, y+11), (sg*18+lean*.5, y+4), h], PURPLE, 5)
        a.ball(*h, 5, 4, BONE)
        hands.append(h)
    left, right = hands
    # golden thread between the hands
    for j in range(0 if (atk and n >= 3) else (4 if clip != 'die' else max(0, 6-n))):
        a.line([left, (-4+j*4+(right[0]+left[0])/2*0, mix((left[1]+right[1])/2, 24, .5)-fall*17-j*2), right], 27+j % 2, 1)
    if die and n >= 2:
        for j in range(4):
            x = -22+j*14
            y2 = max(3, 42-j*3-n*4)
            a.line([(x, y2), (x+4, y2-3), (x+7, y2-1)], 28, 1)
    # spindle on its own thread: in the attack it is cast out and reeled back
    if atk:
        reach = WEAVE_A['sp'][n]
        sp_pos = (right[0]+reach, right[1]-reach*.12+(-2 if n == 4 else 0))
        if reach:
            a.line(bez(right, (right[0]+reach*.5, right[1]+6-reach*.1), sp_pos, 8), 27, 1)
            for k in range(3):
                a.ellipse(sp_pos[0]+4+k*3, sp_pos[1]+k*2-1, 1, 1, 29)
        ang = 1.5
        a.line([sp_pos, (sp_pos[0]+4, sp_pos[1]-9)], 26, 2)
        a.ball(sp_pos[0]+4, sp_pos[1]-10, 5, 3, GOLD)
        if n == 4:
            spark(a, sp_pos[0]+8, sp_pos[1]-3, 29, 4)
    else:
        ang = .8-fall*1.8
        end = (right[0]+math.sin(ang)*10, right[1]-math.cos(ang)*10)
        if die and n >= 3:
            end = (right[0]+8, 4)
            right = (right[0]+8, 8)
        a.line([right, end], 26, 2)
        a.ball(end[0], max(3, end[1]), 5, 3, GOLD)
    return a


# ----------------------------------------------------------------------------------------------
# Hrungnir: a stone giant with a glowing rune, horned crown and a lightning beard.  It raises both fists over its head,
# leans back, then slams them down in front (the beard flares and lightning crawls along the ground), and heaves back up.
# On defeat the rune fades, cracks open, the arms drop, the head topples and the body collapses into separate blocks.
# ----------------------------------------------------------------------------------------------
GIANT_D = dict(by=[36, 36, 35, 34, 30, 25, 20, 17], rune=[1, 1, .5, 0, 0, 0, 0, 0], arm=[0, 0, .2, .6, .9, 1, 1, 1],
               head=[0, 0, .1, .3, .6, .85, 1, 1], block=[0, 0, 0, .2, .5, .8, 1, 1])


def hrungnir(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    wu, st = arc(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    a = Painter('hrungnir', recoil+(st*3-wu*3 if atk else 0))
    ph = n*math.pi/4
    if die:
        D = GIANT_D
        by, rune, arm, hd, blk = D['by'][n], D['rune'][n], D['arm'][n], D['head'][n], D['block'][n]
        kneel = sm(blk*1.4)
    else:
        by = 36+bob*.5-hurt*.5-st*2
        rune, arm, hd, blk, kneel = 1., 0., 0., 0., 0.
    if not die:
        biped_legs(a, PLATE, ph, clip, 0, 12, 29, 10, 5, 9, st, wu)
    else:
        biped_legs(a, PLATE, ph, clip, 0, 12, 29, 10, 5, 9, 0, 0, kneel)
    a.ball(blk*-4, by, 22, 20, PLATE)
    a.ball(blk*-4-6, by+11, 8, 5, PLATE[1:])
    rc = 21 if rune > .5 else 10
    if rune > 0:
        a.poly([(-9-blk*4, by+6), (0-blk*4, by+13), (10-blk*4, by+5), (0-blk*4, by-10)], rc)
    w = sw(clip, n)
    lean_x, lean_y = (st*6-wu*3, -st*9+wu*2) if atk else (0, 0)
    for sg in (-1, 1):
        sh = (sg*19-blk*(5*sg+2)+lean_x, by+15-arm*8+lean_y+(wu*6 if atk else 0))
        if atk:
            tgt = swp(w, (sg*29, 28), (sg*10, 96), (sg*14+12, 12))
        elif die:
            tgt = mixp((sg*29, 28), (sg*(32+arm*8), 7), arm)
        else:
            tgt = (sg*29, 28+(bob if sg < 0 else 0))
        elbow, hand = arm_ik((sh[0], sh[1]-4), tgt, 17, 17, sg)
        a.limb([(sh[0], sh[1]-4), elbow, hand], PLATE, 9)
        a.ball(*hand, 10, 9, PLATE)
        a.ball(sh[0], sh[1], 11, 8, PLATE)
        a.poly([(sh[0]-4, sh[1]+5), (sh[0], sh[1]+16), (sh[0]+4, sh[1]+5)], 22)
        if atk and st > .5 and sg > 0:
            for k in range(5):
                a.ellipse(hand[0]+12+k*5, 2+(k*3+n) % 4, 2.5, 2.2, PLATE[(k+n) % 5])
    hx = hd*14+(st*5-wu*2 if atk else 0)
    hy = 63+bob*.4-hd*40-(st*7 if atk else 0)+(wu*4 if atk else 0)
    if die:
        hy = max(hy, 14)
        if hd > .5:
            hx = 14+hd*10
    a.ball(hx, hy, 16, 14, PLATE)
    a.ball(hx-6, hy+8, 7, 3, PLATE[1:])
    a.face(hx, hy, clip, n, .95)
    for sg in (-1, 1):
        a.poly([(hx+sg*8, hy+10), (hx+sg*17, hy+19), (hx+sg*16, hy+7)], 12)
        a.poly([(hx+sg*9, hy+10), (hx+sg*16, hy+17), (hx+sg*14, hy+9)], 14)
    a.poly([(hx-3, hy+12), (hx, hy+23), (hx+4, hy+12)], 22 if rune > .5 else 10)
    beard = 5
    flare = 1.0+(.5 if atk and st > .5 else 0)
    for j in range(max(0, 5-n) if die else beard):
        x = hx-9+j*4
        a.line([(x, hy-7), (x-2, hy-13*flare), (x+2, hy-12*flare), (x, hy-(19+j % 2*3)*flare)], 23+j % 2, 2)
    if die and n >= 1:
        a.line([(-9-blk*4, by+14), (-4-blk*4, by+8), (-9-blk*4, by+3), (2-blk*4, by-7)], 10, 2)
        if n >= 3:
            for j in range(5):
                x = -26+j*13+(n-3)*(1.2 if j % 2 else -1.2)
                yy = max(4, 42-j % 2*10-(n-3)*8)
                a.poly([(x-4, yy), (x-1, yy+5), (x+4, yy+3), (x+3, yy-3)], 11+j % 3)
    if atk and st > .5:                                     # lightning crawls along the ground in front of the fists
        a.line([(14, 3), (22, 6), (28, 2), (36, 7), (44, 3)], 23 if n % 2 else 24, 2)
    return a


DRAW = dict(boar=lambda c, n: quad('boar', c, n), ram=lambda c, n: quad('ram', c, n), oakhorn=lambda c, n: quad('oakhorn', c, n),
            crow=crow, troll=troll, weaver=weaver, hrungnir=hrungnir)
ANIMAL = dict(boar=boar_art, ram=ram_art, oakhorn=oak_art)


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
        np.savez_compressed(ROOT/f'scripts/wyrd_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT/f'scripts/wyrd_slime_{kind}_raw.npz', **data)
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
        dest = ASSETS/f'wyrd_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'wyrd.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 238 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    """Compare the installed atlases directly to the saved editor frames, not to the drawers."""
    meta = json.loads((ASSETS/'wyrd.txt').read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS/f'wyrd_{kind}.png').convert('RGBA')
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
    for kind in [k for k in KINDS if k in DRAW]:
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
    only = [k for k in sys.argv[2:] if k in KINDS] or [k for k in KINDS if k in DRAW]
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
