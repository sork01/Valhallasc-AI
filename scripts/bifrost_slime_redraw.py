#!/usr/bin/env python3
"""Bifrost Reach art, second pass (v2): Greenmeadow slime style, redrawn from scratch.

preview | extents | build | refresh | export | verify.  Jointed wolf anatomy, faceted crystal, manta fins, empty plate
armour and hinged eagle feathers move by joints, never by universal squash.  Every planted paw, crystal foot, manta tail
tip, armoured boot and eagle talon rests exactly on the anchor row (Painter y=0), so nothing floats (QUADRUPED-GROUNDING).
Each kind has eight distinct attack frames (wind-up, strike, recovery) and eight distinct death frames, and its own frame
size where the art needs one (KIND_FRAMES, docs/kind-frames.md).  The v1 sources (Beta 1.39.8) stay registered in
bifrost_slime_v1_sources.txt.  Export preserves editor edits.
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
from wyrd_slime_v1_redraw import PALETTE as BASE_PALETTE

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/bifrost-slime'
REGISTRY = ROOT/'scripts/bifrost_slime_sources.txt'
PREFIX = 'valhallasc_bifrost_slime_style_b_'
KINDS = ['galehound', 'prismgolem', 'skyray', 'einherjar', 'thunderroc']
NAMES = dict(galehound='Galehound', prismgolem='Prism Golem', skyray='Skyray',
             einherjar='Hollow Einherjar', thunderroc='Thunderroc')
W = H = 96                       # zone-wide frame (manifest fallback)
AX, AY = 48, 90
# kind -> (w, h, ax, ay); the anchor's y is the ground row, its x the creature's centre (+2).  Measured with `extents`.
KIND_FRAMES = dict(
    galehound=(124, 76, 54, 70),
    prismgolem=(120, 102, 52, 96),
    skyray=(120, 74, 52, 68),
    einherjar=(120, 102, 46, 96),
    thunderroc=(130, 82, 47, 76),
)
CLIPS = old.CLIPS


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Keep the exact 65-colour v1 palette and ramp exports so deep_slime_redraw.py stays compatible.
PALETTE = BASE_PALETTE[:] + [
    '#223d73', '#426cc1', '#78a8ee', '#badcff', '#edf7ff',
    '#6a3318', '#a85c29', '#da9347', '#f5c878', '#fff0c3',
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
BONE = list(range(5, 10))
PLATE = list(range(10, 15))
PURPLE = list(range(15, 20))
TEAL = list(range(20, 25))
GOLD = list(range(25, 30))
GREEN = list(range(30, 35))
RED = list(range(35, 40))
FUR = list(range(45, 50))
FEATHER = list(range(50, 55))
BLUE = list(range(55, 60))
BROWN = list(range(60, 65))
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


def sm(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)


def bez(p0, p1, p2, k=9):
    return [((1-s)**2*p0[0]+2*(1-s)*s*p1[0]+s*s*p2[0], (1-s)**2*p0[1]+2*(1-s)*s*p1[1]+s*s*p2[1])
            for s in (i/k for i in range(k+1))]


def taper(a, pts, ramp, w0, w1):
    """Tentacle/tail: dark outline pass, body pass, thin highlight; width eases from w0 to w1."""
    last = len(pts)-1
    for i in range(last):
        a.line([pts[i], pts[i+1]], ramp[0], max(1, round(mix(w0, w1, i/last)+2)))
    for i in range(last):
        a.line([pts[i], pts[i+1]], ramp[2], max(1, round(mix(w0, w1, i/last))))
    for i in range(0, last, 1):
        w = mix(w0, w1, i/last)
        if w >= 4:
            a.line([(pts[i][0]-w*.18, pts[i][1]+w*.18), (pts[i+1][0]-w*.18, pts[i+1][1]+w*.18)], ramp[3], 1)


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


def bolt(a, x, y, s=1.):
    y = max(y, 8*s)
    a.poly([(x-2*s, y+7*s), (x+2*s, y+7*s), (x, y+1*s), (x+4*s, y+2*s),
            (x-1*s, y-7*s), (x, y-1*s), (x-4*s, y-2*s)], 28)
    a.line([(x, y+5*s), (x-1*s, y), (x+1*s, y)], 29, 1)


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


def biped_legs(a, ramp, ph, clip, wide, hip_y, rx, ry, w, st=0., wu=0., kneel=0.):
    """Hip, knee and boot; the boot's lowest pixel is the ground row.  Walk lifts one boot at a time; an attack steps the
    front boot forward and braces the rear; on defeat the knees fold under and the shins tuck."""
    for sg in (-1, 1):
        swing = math.sin(ph+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, swing)*3.5
        fx = sg*wide+swing*5+(st*7 if sg > 0 else -wu*3)
        hip = (sg*(wide-1), hip_y)
        knee = (sg*(wide+2)+(fx-sg*wide)*.4, mix(hip_y, ry+1, .55)+lift*.5)
        ank = (fx, ry+1+lift)
        if kneel:
            fx2 = sg*(wide+6)-sg*2
            knee = (mix(knee[0], fx2+8*(1 if sg > 0 else .4), kneel), mix(knee[1], 11, kneel))
            ank = (mix(ank[0], fx2-4, kneel), mix(ank[1], ry+2, kneel))
            fx = ank[0]
        a.limb([hip, knee, ank], ramp, w)
        foot(a, fx, lift if not kneel else 0, rx, ry, ramp)


# ----------------------------------------------------------------------------------------------
# 1. Galehound: a four-legged wolf of wind-torn cloud with lightning in its flank.
#    All four paws rest on the ground row (FAR_DX = 6 separates the four lower legs).
#    Attack: coils back with head raised and jaws parting, then lunges forward with a lightning bite and recovers.
#    Death: front legs fold, then hind legs fold, body and head settle onto the ground, lightning expires.
# ----------------------------------------------------------------------------------------------
FAR_DX = 6
HOUND_A = dict(
    lean=[-3, -7, -11, 5, 13, 9, 4, 0],
    hdy=[2, 6, 10, 0, -3, -2, 0, 0],
    hang=[0, .1, .2, -.05, -.25, -.15, -.05, 0],
    jaw=[0, 1, 2.5, 4, 5, 3, 1, 0],
    fstep=[0, -2, -4, 5, 8, 5, 2, 0],
    flift=[0, 3, 5, 1, 0, 0, 0, 0],
    drop=[0, 1, 3, 0, 2, 1, 0, 0],
)
HOUND_D = dict(
    by=[30, 29, 26, 22, 19, 17, 15.5, 15],
    hx=[22, 22, 23, 24, 25, 26, 27, 28],
    hy=[37, 36, 32, 26, 20, 16, 13.5, 12],
    ff=[0, .2, .7, 1, 1, 1, 1, 1],
    hf=[0, 0, .3, .8, 1, 1, 1, 1],
    splay=[0, 0, 0, 0, .3, .65, .9, 1],
)


def hound_leg_rest(front, far, step=0., lift=0., lean=0.):
    d = FAR_DX if far else 0
    X = (9 if front else -21)+d
    root = (X+lean*.8, 26)
    ank_y = 9+lift*.7
    ankle = (X+(3 if front else -2)+step*.7, ank_y)
    knee = (X+(-2 if front else 7)+step*.25+lean*.4, (root[1]+ank_y)/2-1+lift*.3)
    return [root, knee, ankle, (X+(4 if front else -1)+step, 3+lift)]


def hound_leg_death(front, far, g, splay, by):
    X = (9 if front else -21)+(FAR_DX if far else 0)
    rest = hound_leg_rest(front, far)
    rest[0] = (X, by-5)
    tuck = [(X, 0), (X+6, 6), (X-1, 4), (X-6, 3)] if front else [(X, 0), (X+9, 7), (X-4, 5), (X-13, 3)]
    pts = [mixp(rest[i], tuck[i], g) for i in range(4)]
    pts[0] = (X, by-5)
    if splay:
        end = [(X, 7), (X+9, 5), (X+17, 4), (X+25, 3)] if front else [(X, 7), (X-9, 5), (X-17, 4), (X-24, 3)]
        pts = [mixp(pts[i], end[i], splay) for i in range(4)]
    return pts


def galehound(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    a = Painter('galehound', 0)
    if die:
        by = HOUND_D['by'][n]
        lean, hdy, hang, jaw = 0., 0., 0., 0.
        hx, hy = HOUND_D['hx'][n], HOUND_D['hy'][n]
        legs = []
        for far in (True, False):
            for front in (False, True):
                g = HOUND_D['ff'][n] if front else HOUND_D['hf'][n]
                legs.append((front, far, hound_leg_death(front, far, g, HOUND_D['splay'][n], by)))
    else:
        lean = (HOUND_A['lean'][n] if atk else 0)+recoil
        by = 30+bob*.7-(HOUND_A['drop'][n] if atk else 0)-hurt*.6
        hdy = (HOUND_A['hdy'][n] if atk else 0)+hurt*1.4
        hang = (HOUND_A['hang'][n] if atk else 0)+.1*hurt
        jaw = HOUND_A['jaw'][n] if atk else 0.
        hx, hy = 22+lean, by+7+hdy
        legs = []
        for far in (True, False):
            for front in (False, True):
                ph = (0 if front else math.pi)+(math.pi if far else 0)
                sw_ = math.sin(n*math.pi/4+ph) if clip == 'walk' else 0
                step = sw_*3
                lift = max(0, sw_)*3
                if atk and front:
                    step += HOUND_A['fstep'][n]*(1 if not far else .6)
                    lift += HOUND_A['flift'][n]*(1 if not far else 0)
                if atk and not front and not far:
                    step -= lean*.15
                legs.append((front, far, hound_leg_rest(front, far, step, lift, lean)))

    for far in (True, False):
        for front, f, pts in legs:
            if f == far:
                ramp = FUR[:3] if far else FUR
                w = 3 if far else 4
                a.limb(pts[:3], ramp, w)
                a.limb(pts[2:], ramp, max(2, w-1))
                a.ball(pts[3][0], pts[3][1], 3 if far else 3.5, 3, PLATE[:3] if far else PLATE[:4])

    # Flowing tapered cloud tail, kept well above the ground row so it never merges with the hind paws.
    bx = -5+lean*.5
    for j in range(3):
        tx = bx-19-j*4
        ty = max(8, by+4+j*3+math.sin(n*.8+j)*1.2*(1-fall)-fall*j*3)
        a.ball(tx, ty, 6.5-j, 3.8-j*.6, FUR)
        a.poly([(tx-2, ty+3), (tx-8, ty+2+j), (tx-4, ty-2)], 47+j % 2)

    a.ball(bx, by, 23, 14, FUR)
    a.ball(bx-8, by+7, 10, 4, FUR[1:])
    for j in range(4):
        x = bx-18+j*9
        a.poly([(x, by+10), (x+2, by+20-j % 2*3), (x+11, by+11)], 46+j % 3)
        a.ball(x+4, by+11, 5.5, 3.5, FUR)

    a.ball(12+lean*.6, by+2, 11, 11, FUR)         # shoulder keeps the head joined to the barrel
    a.ball(hx, hy, 14, 13, FUR, hang)
    a.ball(hx-5, hy+6, 6, 3, FUR[1:])
    a.poly([(hx-11, hy+7), (hx-12, hy+24), (hx-1, hy+12)], 46)
    a.poly([(hx+3, hy+10), (hx+9, hy+21), (hx+11, hy+5)], 47)
    a.poly([(hx-9, hy+11), (hx-10, hy+19), (hx-5, hy+12)], 48)
    a.face(hx+1, hy, clip, n, .78)
    a.ball(hx+7, hy-7-jaw*.3, 8, 4.5, FUR)
    a.ellipse(hx+11, hy-5-jaw*.2, 2, 1.5, 10)
    if jaw > .5:
        for sx in (hx+4, hx+11):
            a.poly([(sx-1.5, hy-9), (sx+1.5, hy-9), (sx, hy-13-jaw*.3)], 9, 1)
    if clip != 'die' or n < 4:
        bolt(a, bx-7, by+4, .65)
        bolt(a, bx+8, by+6, .5)
    if atk and n in (4, 5):
        spark(a, hx+16, hy-5, 29, 5)
        a.line([(hx+14, hy-2), (hx+22, hy+2), (hx+19, hy+6), (hx+27, hy+9)], 28, 2)
        dust(a, hx-2, n, 3, FUR)
    return a


# ----------------------------------------------------------------------------------------------
# 2. Prism Golem: faceted purple crystal brute with rainbow shards and crystal fists.
#    Attack: leans back and raises both crystal fists high overhead, then slams them into the ground with rainbow shards.
#    Death: knees buckle, cracks spread across the crystal, rainbow shards fall to the ground and the body slumps.
# ----------------------------------------------------------------------------------------------
def shard(a, x, y, rx, ry, ramp):
    y = max(y, ry+2)
    a.poly([(x-rx, y), (x-rx*.55, y+ry), (x+rx*.4, y+ry*.9), (x+rx, y-ry*.15), (x+rx*.35, y-ry), (x-rx*.55, y-ry*.8)], ramp[0])
    a.ball(x, y, rx*.78, ry*.77, ramp)
    a.poly([(x-rx*.55, y+ry*.6), (x-rx*.15, y+ry*.8), (x+rx*.25, y+ry*.5), (x-rx*.15, y+ry*.35)], ramp[-1])


GOLEM_D = dict(
    by=[36, 35, 33, 29, 25, 21, 18, 16],
    arm=[0, .1, .35, .65, .88, 1, 1, 1],
    head=[0, .05, .2, .45, .7, .9, 1, 1],
    blk=[0, 0, .15, .35, .6, .85, 1, 1],
)


def prismgolem(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    wu, st = arc(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    a = Painter('prismgolem', recoil+(st*4-wu*3 if atk else 0))
    ph = n*math.pi/4
    if die:
        by, arm, hd, blk = GOLEM_D['by'][n], GOLEM_D['arm'][n], GOLEM_D['head'][n], GOLEM_D['blk'][n]
        kneel = sm(blk*1.3)
    else:
        by = 36+bob*.4-hurt*.5-st*2
        arm = hd = blk = kneel = 0.

    biped_legs(a, PURPLE, ph, clip, 12, 28, 9, 5, 8, st, wu, kneel)
    shard(a, -blk*3, by, 21, 20, PURPLE)
    for j, ramp in enumerate((GOLD, TEAL, BLUE)):
        shard(a, -10+j*10-blk*2, by+2-j % 2*6, 5, 8, ramp)

    w = sw(clip, n)
    lean_x, lean_y = (st*6-wu*3, -st*8+wu*2) if atk else (0, 0)
    for sg in (-1, 1):
        sh = (sg*18-blk*(4*sg+2)+lean_x, by+14-arm*7+lean_y+(wu*5 if atk else 0))
        if atk:
            tgt = swp(w, (sg*28, 26), (sg*12, 92), (sg*14+14, 11))
        elif die:
            tgt = mixp((sg*28, 26), (sg*(30+arm*7), 10), arm)
        else:
            tgt = (sg*28, 26+(bob if sg < 0 else 0))
        elbow, hand = arm_ik((sh[0], sh[1]-4), tgt, 16, 16, sg)
        a.limb([(sh[0], sh[1]-4), elbow, hand], PURPLE, 7)
        shard(a, hand[0], max(10, hand[1]), 9, 9, TEAL if sg > 0 else BLUE)
        shard(a, sh[0], max(11, sh[1]+1), 10, 9, PURPLE)
        a.poly([(sh[0]-4, sh[1]+6), (sh[0], sh[1]+17), (sh[0]+4, sh[1]+6)], 23 if sg > 0 else 58)
        if atk and st > .4 and sg > 0:
            spark(a, hand[0]+14, 10, 29, 5)
            for k, ramp in enumerate((GOLD, TEAL, BLUE)):
                shard(a, hand[0]+10+k*7, 7+(k+n) % 4, 4, 5, ramp)

    hx = hd*13+(st*5-wu*2 if atk else 0)
    hy = 62+bob*.4-hd*42-(st*6 if atk else 0)+(wu*4 if atk else 0)
    if die:
        hy = max(hy, 16)
    shard(a, hx, hy, 16, 15, PURPLE)
    a.face(hx, hy, clip, n, .9)
    for j, ramp in enumerate((GOLD, TEAL, BLUE)):
        shard(a, hx-9+j*9, hy+14+4*(j % 2), 3, 7, ramp)
    if die:
        a.line([(-9, by+12), (-3, by+6), (-7, by), (4, max(4, by-8))], 15, 2)
        if n >= 2:
            for j, ramp in enumerate((TEAL, GOLD, BLUE, PURPLE)):
                shard(a, -26+j*17+(n-2)*(.6 if j % 2 else -.6), max(7, 38-j % 2*7-(n-2)*6), 4, 5, ramp)
        if n >= 4:
            a.line([(hx-10, hy+7), (hx-3, hy+2), (hx-7, max(4, hy-6))], 15, 2)
    return a


# ----------------------------------------------------------------------------------------------
# 3. Skyray: a flying storm-blue manta ray with smooth triangular pectoral fins (no ground-dragging tail).
#    Hovers well above the ground in idle, walk, attack and hurt.
#    Attack: banks back high in the air with both fins swept up and a lightning orb charging between its horns,
#    then swoops forward and lashes a jagged lightning bolt ahead.
#    Death: falls from mid-air onto the ground as its pectoral fins curl inward and lightning expires.
# ----------------------------------------------------------------------------------------------
RAY_A = dict(
    lean=[-2, -6, -10, 4, 11, 7, 2, 0],
    by=[32, 35, 38, 30, 28, 29, 31, 32],
    flap=[4, 12, 18, -4, -10, -6, -2, 0],
    orb=[0, 3, 6, 2, 0, 0, 0, 0],
    reach=[0, 0, 0, 12, 26, 20, 6, 0],
)
RAY_D = dict(
    by=[32, 29, 25, 20, 15, 11, 9, 8],
    curl=[0, .12, .3, .55, .78, .92, .98, 1],
)


def skyray(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    a = Painter('skyray', 0)
    if atk:
        lean, by, flap, orb, reach = RAY_A['lean'][n], RAY_A['by'][n], RAY_A['flap'][n], RAY_A['orb'][n], RAY_A['reach'][n]
        curl = 0.
    elif die:
        lean, by, flap, orb, reach, curl = -fall*3, RAY_D['by'][n], (1-RAY_D['curl'][n])*4, 0, 0, RAY_D['curl'][n]
    else:
        lean = recoil
        by = 32+bob*1.2-hurt*.5
        flap = math.sin(n*math.pi/4)*9 if clip == 'walk' else bob*1.8
        orb, reach, curl = 0, 0, 0.

    # Smooth triangular pectoral fins flapping together in flight
    for far in (True, False):
        sg = 1 if far else -1
        tipx = lean+sg*(36-curl*14)
        tipy = max(2, by+8+flap*(1-curl)-curl*10)
        a.poly([(lean+sg*6, by+11), (lean+sg*20, by+14), (tipx, tipy), (tipx-sg*4, max(1, tipy-4)),
                (lean+sg*22, max(2, by-10+curl*4)), (lean+sg*5, max(2, by-8))], 55 if far else 56)
        a.poly([(lean+sg*7, by+8), (lean+sg*21, by+10), (tipx-sg*4, max(2, tipy-1)),
                (lean+sg*20, max(3, by-5)), (lean+sg*7, max(3, by-6))], 56 if far else 57)
        a.line([(lean+sg*10, by+5), (lean+sg*20, by+2), (tipx-sg*5, max(2, tipy-2))], 58, 1)

    # Aerial whipping tail trailing behind in flight (staying high above the ground, settling with the body on death)
    sway = (math.sin(n*math.pi/4)*4 if clip == 'walk' else bob*1.5)*(1-curl)
    t_root = (lean-9, max(4, by-6))
    t_mid = (lean-23-curl*2, max(3, by-16+sway*.4+curl*9))
    t_tip = (lean-38+sway*.5-curl*3, max(2, by-12-sway*1.1+curl*6))
    taper(a, bez(t_root, t_mid, t_tip), BLUE, 5, 1)

    a.poly([(lean-12, by+7), (lean, by+17), (lean+15, by+8), (lean+12, max(2, by-9)),
            (lean, max(1, by-12)), (lean-12, max(2, by-8))], 55)
    a.ball(lean, by+2, 14, 12, BLUE)
    a.ball(lean-4, by+8, 6, 3, BLUE[1:])
    a.face(lean+2, by+3, clip, n, .78)
    # Cephalic horn-fins
    for sg in (-1, 1):
        a.poly([(lean+sg*6, by+8), (lean+14+sg*4, by+15-curl*5), (lean+18+sg*3, by+10-curl*5), (lean+11+sg*3, by+5)], 57)
    for x, dy in [(-5, 11), (5, 12), (0, -6)]:
        a.ellipse(lean+x, max(2, by+dy), 1.4, 1, 59)
    if clip != 'die' or n < 4:
        bolt(a, lean-2, max(7, by-4), .45)
    if orb > 0:
        a.ball(lean+19, by+6, orb, orb, GOLD)
        spark(a, lean+19, by+6, 29, 4)
    if reach > 0:
        bx0, by0 = lean+18, by+5
        pts = [(bx0, by0), (bx0+reach*.35, by0+5), (bx0+reach*.65, by0-4), (bx0+reach, by0+2)]
        a.line(pts, 28, 3)
        a.line(pts, 29, 1)
        spark(a, bx0+reach, by0+2, 29, 5)
    return a


# ----------------------------------------------------------------------------------------------
# 4. Hollow Einherjar: dead hero in rigid plate armour with horned helm, round shield, broadsword and teal spirit fire.
#    Attack: braces back and raises the broadsword high overhead behind the helm, then steps in and chops down in an arc.
#    Death: spirit wisps rise and vanish while the visor goes dark, knees buckle, empty plate collapses and sword drops flat.
# ----------------------------------------------------------------------------------------------
EINH_D = dict(
    by=[36, 35, 32, 28, 23, 19, 16.5, 15],
    kneel=[0, .15, .45, .8, 1, 1, 1, 1],
    drop=[0, .1, .3, .6, .85, .95, 1, 1],
)


def einherjar(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    wu, st = arc(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    a = Painter('einherjar', recoil+(st*5-wu*3 if atk else 0))
    ph = n*math.pi/4
    if die:
        by, kneel, dp = EINH_D['by'][n], EINH_D['kneel'][n], EINH_D['drop'][n]
    else:
        by = 36+bob*.4-hurt*.5-st*2
        kneel = dp = 0.

    biped_legs(a, PLATE, ph, clip, 10, 27, 8, 4, 6, st, wu, kneel)
    a.poly([(-13, by+8), (13, by+8), (19+dp*5, 7), (-19-dp*5, 7)], 16)
    a.ball(0, by, 16, 17, PLATE)
    a.ball(-5, by+9, 7, 3, PLATE[1:])
    a.line([(-9, by-6), (9, by-6)], 27, 3)
    a.poly([(-4, by+5), (0, by+10), (4, by+5), (0, by-1)], 22 if not die or n < 4 else 11)
    for sg in (-1, 1):
        a.ball(sg*(15+dp*4), by+12-dp*5, 9, 6, PLATE)

    # Far arm and round shield
    sx, sy = -23-dp*6+st*4-wu*2, max(15, 29+bob*.4-dp*14+wu*3)
    a.limb([(-13, by+10), (-21, by+1), (sx, sy)], PLATE, 5)
    a.ball(sx, sy, 11, 13, PLATE)
    a.ball(sx, sy, 8, 10, GOLD)
    a.line([(sx, sy-8), (sx, sy+8)], 13, 2)
    a.line([(sx-6, sy), (sx+6, sy)], 13, 2)

    # Near arm and broadsword
    w = sw(clip, n)
    sh = (13+st*3-wu*2, by+10)
    if atk:
        tgt = swp(w, (23, 29), (16, 76), (36, 22))
        ang = swp(w, (1.35, 0), (2.05, 0), (-.45, 0))[0]
    elif die:
        tgt = mixp((23, 29), (28, 8), dp)
        ang = mix(1.35, .05, dp)
    else:
        tgt = (23, 29+bob*.4)
        ang = 1.35
    elbow, hand = arm_ik(sh, tgt, 13, 13, 1)
    a.limb([sh, elbow, hand], PLATE, 5)
    a.ball(*hand, 5, 4, PLATE)
    dx, dy = math.cos(ang), math.sin(ang)
    end = (hand[0]+dx*24, max(5, hand[1]+dy*24))
    a.line([(hand[0]-dy*5, hand[1]+dx*5), (hand[0]+dy*5, hand[1]-dx*5)], 28, 3)
    a.limb([hand, end], PLATE, 3)
    if atk and st > .3:
        for k in range(1, 6):
            ak = ang+k*.32
            r = max(1, 3.2-k*.45)
            a.ellipse(hand[0]+math.cos(ak)*21, max(r+2, hand[1]+math.sin(ak)*21), r, r, [23, 24, 2][k % 3])
        if st > .8:
            spark(a, end[0]+2, end[1], 24, 4)

    hx = dp*11+(st*4-wu*2 if atk else 0)
    hy = max(15, 60+bob*.4-dp*44-(st*4 if atk else 0)+(wu*3 if atk else 0))
    a.ball(hx, hy, 15, 14, PLATE)
    a.ball(hx, hy-2, 11, 10, TEAL if not die or n < 4 else PLATE[:2])
    if not die or n < 5:
        a.face(hx, hy-1, clip, n, .85)
    a.poly([(hx-14, hy+2), (hx-13, hy+13), (hx+12, hy+13), (hx+14, hy+2),
            (hx+5, hy+5), (hx, hy+9), (hx-5, hy+5)], 12)
    a.line([(hx, hy+12), (hx, hy-4)], 14, 2)
    for sg in (-1, 1):
        a.poly([(hx+sg*10, hy+10), (hx+sg*20, hy+19), (hx+sg*19, hy+8), (hx+sg*12, hy+5)], 7)
        a.line([(hx+sg*12, hy+10), (hx+sg*18, hy+16)], 9, 2)
    if not die:
        a.poly([(hx-5, hy+14), (hx-3, hy+22+bob), (hx+2, hy+18), (hx+6, hy+14)], 22)
        a.poly([(hx-2, hy+15), (hx-1, hy+20+bob), (hx+3, hy+15)], 24)
    elif n < 6:
        for j in range(3):
            xx = hx-10+j*9+math.sin(n+j)*2
            yy = min(84, hy+16+n*6+j*3)
            a.poly([(xx-2, yy-3), (xx, yy+5), (xx+3, yy), (xx+1, yy-3)], 22+j % 3)
    return a


# ----------------------------------------------------------------------------------------------
# 5. Thunderroc: huge storm eagle with hinged blue wing feathers, brown breast, white head and golden talons on the ground.
#    Attack: leans back with both feathered wings thrown high overhead, then lunges forward snapping its golden beak and
#    firing a jagged lightning bolt ahead.
#    Death: pitches down onto its breast, wings fold along the ground, one golden talon curls up, feathers fall and
#    lightning expires.
# ----------------------------------------------------------------------------------------------
def feather_wing(a, sx, sy, ang, spread, ramp, length=24, far=False):
    openness = max(0., min(1., (ang+2.6)/3.6))
    length = length*(1+.45*openness)
    spread = spread*(1+.8*openness)
    tips = []
    for k in range(5):
        th = ang+(k-2)*spread
        L = length+(k % 2)*3-abs(k-2)
        tips.append((th, (sx+L*math.cos(th), max(3., sy+L*math.sin(th)))))
    a.poly([(sx, sy)]+[t for _, t in tips], ramp[1], outline=ramp[0])
    for th, tip in tips:
        px, py = -math.sin(th), math.cos(th)
        wd = 5.5+openness*1.8
        a.poly([(sx+px*wd, max(3., sy+py*wd)), tip, (sx-px*wd, max(3., sy-py*wd))],
               ramp[1 if far else 2], outline=ramp[0])
        a.line([(sx+px*1.5, max(3., sy+py*1.5)), tip], ramp[3 if not far else 2], 1)
    a.ball(sx, sy, 9, 8, ramp)


ROC_A = dict(
    lean=[-2, -6, -9, 5, 11, 7, 2, 0],
    drop=[1, 3, 2, 0, 6, 4, 1, 0],
    hx=[16, 11, 7, 22, 31, 29, 21, 16],
    hy=[14, 18, 22, 12, 4, 6, 11, 14],
    wing=[-2.1, -.3, 1.45, .4, -.7, -1.3, -2.0, -2.5],
    gap=[0, 1, 5, 2, 7, 4, 0, 0],
)
ROC_D = dict(
    by=[30, 29, 26, 23, 20, 17.5, 16, 15],
    hx=[16, 15, 16, 18, 21, 23, 24, 24],
    hy=[14, 13, 10, 6, 1, -2, -3, -3],
    wing=[-2.5, -1.1, .1, -.3, -1.0, -1.7, -2.5, -2.9],
    lean=[0, 1, 1, 2, 3, 4, 4, 4],
)


def thunderroc(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    hurt = hurtof(clip, n)
    atk = clip == 'attack'
    die = clip == 'die'
    a = Painter('thunderroc', 0)
    if atk:
        lean, drop, (ox, oy), wang, gap = (ROC_A['lean'][n], ROC_A['drop'][n],
                                           (ROC_A['hx'][n], ROC_A['hy'][n]), ROC_A['wing'][n], ROC_A['gap'][n])
    elif die:
        lean, drop, (ox, oy), wang, gap = (ROC_D['lean'][n], 30-ROC_D['by'][n],
                                           (ROC_D['hx'][n], ROC_D['hy'][n]), ROC_D['wing'][n], 0)
    else:
        lean, drop, (ox, oy), wang, gap = (recoil, 0, (16, 14),
                                           -2.5+(math.sin(n*math.pi/4)*.22 if clip == 'walk' else bob*.12), 0)
        if clip == 'hurt':
            drop, (ox, oy), wang = -hurt*.6, (16-hurt, 14+hurt*1.5), -2.5+hurt*.45
    by = 30+bob*.8-drop+abs(stride)*.8

    # Two golden talons planted on the ground row; in death one stiff talon curls up.
    for sg in (-1, 1):
        sgs = math.sin(n*math.pi/4+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sgs)*3.5
        fx = sg*7+sgs*2.5+(lean*.35 if atk else 0)
        if die and n >= 3:
            fx = sg*7+4
            if sg > 0:
                a.limb([(sg*5+lean*.5, by-8), (sg*9, by+2), (sg*13+fall*3, by+10)], GOLD, 3)
                a.line([(sg*13+fall*3-2, by+10), (sg*13+fall*3+3, by+13)], 27, 2)
                continue
        a.limb([(sg*5+lean*.5, by-10), (sg*6+lean*.2, (by-10)*.48+lift*.5), (fx, 2+lift)], GOLD, 3)
        foot(a, fx, lift, 5, 2, GOLD)

    feather_wing(a, -10+lean*.5, by+4, wang+.45, .21, BLUE, 22, far=True)
    for j in range(3):
        a.poly([(-9+lean*.5, by-5), (-26+j*5+lean*.3, max(3, by-18+fall*10)),
                (-16+j*5+lean*.3, max(3, by-19+fall*10)), (4+lean*.5, by-5)], 61+j % 2)
    a.ball(0+lean*.5, by, 19, 16, BROWN)
    a.ball(-5+lean*.5, by+9, 9, 4, BROWN[1:])

    hx, hy = ox+lean*.5, max(14., by+oy)
    a.limb([(8+lean*.5, by+5), ((8+hx)/2+lean*.2, by+7+oy*.3), (hx-3, hy-2)], FUR, 10)
    a.ball(hx, hy, 14, 13, FUR)
    a.ball(hx-4, hy+7, 7, 3, FUR[1:])
    for j in range(3):
        a.poly([(hx-11+j*5, hy+8), (hx-18+j*6, hy+23-j*2), (hx-3+j*5, hy+10)], 55+j % 3)
    a.eye(hx+2, hy, clip, n, 1.05)
    a.ellipse(hx-5, hy-5, 2.5, 1.5, 4)
    a.poly([(hx+8, hy-1+gap*.3), (hx+23, max(3., hy-5+gap*.1)), (hx+18, max(3., hy-10)),
            (hx+14, max(3., hy-6)), (hx+8, max(3., hy-6))], 27)
    a.poly([(hx+9, max(3., hy-7-gap*.6)), (hx+18, max(3., hy-9-gap*.8)), (hx+9, max(3., hy-10-gap*.6))], 28)

    feather_wing(a, -3+lean*.5, by+1, wang, .21, BLUE, 25)
    if not die or n < 4:
        bolt(a, -22+lean*.4+fall*6, max(10, by+10), .65)
        bolt(a, 2+lean*.4, max(10, by+2), .65)
    if atk and n in (4, 5):
        pts = [(hx+20, hy-4), (hx+28, hy-1), (hx+25, hy-7), (hx+35, hy-3)]
        a.line(pts, 28, 3)
        a.line(pts, 29, 1)
        spark(a, hx+35, hy-3, 29, 5)
        dust(a, hx+12, n, 3, GOLD)
    if die and n >= 1:
        for j in range(3):
            xx = -24+j*16+n*.6
            yy = max(4, 46-j*4-n*5)
            a.poly([(xx-2, yy), (xx+1, yy+6), (xx+3, yy+2), (xx, yy-3)], 57+j % 2)
    return a


DRAW = dict(galehound=galehound, prismgolem=prismgolem, skyray=skyray,
            einherjar=einherjar, thunderroc=thunderroc)

STRICT = True       # preview sets this False so problems are listed instead of stopping the sheet
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if clip == 'die':                                       # a fallen body rests on the ground: never sunk, never floating
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and (kind != 'skyray' or n == 7 or int(rows.max()) > kay):
            grid = np.roll(grid, kay-int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = 3
    problem = None
    low = int(np.nonzero(grid.any(axis=1))[0].max()) if grid.any() else -1
    if not grid.any() or grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any():
        problem = 'empty or touches the border'
    elif kind == 'skyray':
        if clip != 'die' and low > kay-12:
            problem = f'skyray should fly well above anchor row {kay} (lowest row {low})'
        elif clip == 'die' and low > kay:
            problem = f'skyray death frame {n} sinks below anchor row {kay} (lowest row {low})'
    elif clip != 'die' and low != kay:
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
        np.savez_compressed(ROOT/f'scripts/bifrost_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT/f'scripts/bifrost_slime_{kind}_raw.npz', **data)
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
        dest = ASSETS/f'sky_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'sky.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 170 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    """Compare the installed atlases directly to the saved editor frames, not to the drawers."""
    meta = json.loads((ASSETS/'sky.txt').read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS/f'sky_{kind}.png').convert('RGBA')
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
