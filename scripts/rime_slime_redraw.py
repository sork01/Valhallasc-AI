#!/usr/bin/env python3
"""Rimeveil Glacier art, second pass (v2): Greenmeadow slime style, redrawn from scratch.

preview | build | refresh | export | verify.  Rigid shells and animal anatomy move by joints and rotation, never by
universal squash.  Every planted foot, paw and coil rests exactly on the anchor row (Painter y=0), so nothing floats.
Each kind has eight distinct attack frames (wind-up, strike, recovery: ATTACK curve) and eight distinct death frames.
The yeti, wolf and wyrm have their own frame sizes (KIND_FRAMES, docs/kind-frames.md) so a raised fist, a pounce and
a sprawled coil fit.  The v1 sources (Beta 1.39.1) stay registered in rime_slime_v1_sources.txt.  Export preserves
saved editor edits.
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
OUT = ROOT/'test-results/rime-slime'
REGISTRY = ROOT/'scripts/rime_slime_sources.txt'
PREFIX = 'valhallasc_rime_slime_style_b_'
KINDS = ['crab', 'wolf', 'yeti', 'wyrm']
NAMES = dict(crab='Rime Crab', wolf='Frost Wolf', yeti='Yeti', wyrm='Rime Wyrm')
W = H = 96                       # zone-wide frame
AX, AY = 48, 90
# kind -> (w, h, ax, ay); a kind equal to the zone-wide frame gets no kindFrames entry.  The anchor's y is the ground
# row; the anchor's x is the creature's centre.
KIND_FRAMES = dict(crab=(112, 96, 52, 90), wolf=(112, 96, 52, 90), yeti=(112, 112, 56, 106), wyrm=(144, 96, 56, 90))
CLIPS = old.CLIPS


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Same colours as v1; index zero alone is transparent.
PALETTE = ['#00000000', '#23324a', '#ffffff', '#edf6f7', '#eda7bc',
           '#16466f', '#2779a9', '#55b7d7', '#9ce4f0', '#defaff',
           '#526784', '#839db9', '#b2c9db', '#dce9ee', '#fafcf4',
           '#28608c', '#559ac0', '#8bcce0', '#c8f0f3', '#f0ffff',
           '#2b416c', '#5282bb', '#87bee4', '#c1e5f8', '#f2fbff',
           '#3f314b', '#98567a', '#cf89ab', '#f3c0cd', '#fff0db']
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
SHELL = [5, 6, 7, 8, 9]
FUR = [10, 11, 12, 13, 14]
FACE = [15, 16, 17, 18, 19]
ICE = [20, 21, 22, 23, 24]
MOUTH = [25, 26, 27, 28, 29]
LIGHT_FUR = [11, 12, 13, 14]
EYE_WHITE = 3          # colour-exact eye-white palette index (#edf6f7); the frost ramps are also near-white


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

    def poly(self, pts, col):
        self.d.polygon([self.pos(*p) for p in pts], fill=col)

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        """A shaded ellipsoid; `ang` turns the ellipse counter-clockwise on screen, the light stays upper-left."""
        px, py = self.pos(x, y)
        R = max(rx, ry)
        c, s = math.cos(ang), math.sin(ang)
        for yy in range(max(0, math.floor(py-R)), min(self.h, math.ceil(py+R)+1)):
            for xx in range(max(0, math.floor(px-R)), min(self.w, math.ceil(px+R)+1)):
                dx, dy = xx-px, yy-py                       # screen offset, y down
                u, v = (dx*c-dy*s)/rx, (dx*s+dy*c)/ry       # ellipse-local
                rr = u*u+v*v
                if rr > 1:
                    continue
                z = math.sqrt(max(0, 1-rr))
                nx, ny = u*c+v*s, -u*s+v*c                   # normal turned back to screen
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

    def face(self, x, y, clip, n, size=1, ang=0.0):
        """Two big eyes, blush and a mouth; with `ang` the whole face turns about (x, y) (a head lying down)."""
        def at(dx, dy):
            rx_, ry_ = rot(dx, dy, ang)
            return x+rx_, y+ry_
        for dx in (-6, 6):
            self.eye(*at(dx*size, 0), clip, n, size)
        if clip != 'die' or n < 2:
            self.ellipse(*at(-12*size, -5), 2.5, 1.3, 4)
            self.ellipse(*at(12*size, -5), 2.5, 1.3, 4)
        self.line([at(-3, -8), at(0, -9), at(3, -8)], 1)

    def crystal(self, x, y, height=10, width=3, tilt=0, ang=0.0):
        """An ice shard standing on (x, y); `ang` turns it about its base (-pi/2 points it right)."""
        def at(dx, dy):
            rx_, ry_ = rot(dx, dy, ang)
            return x+rx_, y+ry_
        self.poly([at(-width, 0), at(tilt, height), at(width, 0)], ICE[0])
        self.poly([at(-width+1, 1), at(tilt, height-2), at(0, 1)], ICE[3])
        self.line([at(0, 2), at(tilt, height-3)], ICE[4])


def motion(clip, n):
    phase = n*math.pi/4
    stride = math.sin(phase)*4 if clip == 'walk' else 0
    bob = [0, 1, 1, 0, -1, 0][n] if clip == 'idle' else 0
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    fall = [0, .06, .19, .36, .57, .78, .94, 1][n] if clip == 'die' else 0
    return stride, bob, recoil, fall


ATTACK = [-1.5, -3, -4, .5, 4, 3.5, 1.5, 0]     # wind-up (negative), snap, impact, follow-through, recover


def atk(clip, n):
    """(windup, strike) in 0..1 for the attack clip; both zero for every other clip."""
    if clip != 'attack':
        return 0., 0.
    v = ATTACK[n]
    return max(0., -v)/4, max(0., v)/4


def foot(a, x, lift, rx, ry, ramp):
    """A planted foot: integer ry and centre y = ry, so its lowest pixel is the ground row when lift is 0."""
    a.ball(x, ry+lift, rx, ry, ramp)


def flakes(a, n, count, base_x, spread, top, ramp, floor=2):
    """Drifting frost motes; positions depend on n so consecutive frames always differ."""
    for k in range(count):
        a.ellipse(base_x+((k*37+n*11) % spread)-spread/2, floor+((n*5+k*13) % top), 1, 1, ramp[(k+n) % len(ramp)])


# ----------------------------------------------------------------------------------------------
# Rime Crab: a rigid domed carapace on eight jointed legs (tetrapod gait) with two claws.  It rears its claws up and
# open, then slams and pinches them shut.  On defeat the legs curl in, the carapace tips over backwards and ends on its
# back with the legs curled in the air and the claws slack on the ice.
# ----------------------------------------------------------------------------------------------
def crab(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    a = Painter('crab', recoil+st*2-wu*2+10*t)
    ph = n*math.pi/4
    cy0 = 27+bob*.6-wu*2-st*2
    ang = 3.0*t                                    # counter-clockwise: the shell rolls over backwards onto its back
    half = math.hypot(23*math.sin(ang), 15*math.cos(ang))
    cy = mix(cy0, half, t)

    def T(x, y):                                   # shell-local rest point -> screen, turned with the carapace
        dx, dy = rot(x+2, y-cy0, ang)
        return -2+dx, cy+dy

    def legs(far):
        for k in range(4):
            x = -18+k*11+(-2 if far else 0)
            d = -1 if k < 2 else 1
            swing = ph+(k % 2)*math.pi+(0 if far else math.pi)
            lift = max(0, math.sin(swing))*4 if clip == 'walk' else 0
            push = math.cos(swing)*2.5 if clip == 'walk' else 0
            base = 6 if far else 3
            hip = (x, cy0-5)
            knee = (x+d*8.5, cy0-9)
            ft = (x+d*13+push+(d*st*2 if clip == 'attack' else 0), base+lift)   # braced stance as the claws slam
            knee = (mix(knee[0], x+d*6, t), mix(knee[1], cy0-13, t))
            ft = (mix(ft[0], x+d*2, t), mix(ft[1], cy0-17, t))
            pts = [hip, knee, ft]
            if t:
                pts = [T(*p) for p in pts]
            ramp = ICE if far else SHELL
            a.limb([pts[0], pts[1], (pts[2][0], pts[2][1]+2)], ramp, 3)
            if t:
                a.ball(pts[2][0], pts[2][1], 2.5, 2.5, ramp)
            else:
                foot(a, pts[2][0], pts[2][1]-3, 3, 3, ramp)

    def claw(cx_, cy_, far):
        ramp = ICE if far else SHELL
        if clip == 'die':                          # claws go slack and rest on the ice (the front is now behind)
            fx, fy = (-27, 6) if far else (-33, 7)
            cx_, cy_ = mix(cx_, fx, t), mix(cy_, fy, t)
        openness = 3+wu*7-st*3 if clip == 'attack' else (3+bob if not fall else max(0, 3-n))
        phi = (wu*.9-st*.5) if clip == 'attack' else ang        # pincers point up when raised, down when slamming
        shoulder = T(12, cy0)
        a.limb([shoulder, (mix(shoulder[0], cx_, .5), mix(shoulder[1], cy_, .5)+3), (cx_, cy_)], ramp, 5)
        a.ball(cx_, cy_, 8, 7, ramp)
        for sgn in (1, -1):                         # two curved, tapering pincers that meet at the tips
            p0 = rot(5, sgn*3, phi)
            p1 = rot(12, sgn*(3.5+openness*.65), phi)
            p2 = rot(17, sgn*(.8+openness*.3), phi)
            taper(a, bez((cx_+p0[0], cy_+p0[1]), (cx_+p1[0], cy_+p1[1]), (cx_+p2[0], cy_+p2[1])), ramp, 5, 1)

    far_c = (mix(mix(27, 31, wu), 40, st), mix(mix(34, 58, wu), 24, st))
    near_c = (mix(mix(26, 36, wu), 34, st), mix(mix(15, 46, wu), 12, st))
    legs(True)
    claw(*far_c, True)
    for x, h in [(-15, 12), (-5, 16), (6, 11)]:
        bx, by = T(x, cy0+10)
        a.crystal(bx, by, h*(1-min(1, t*1.7)), 4*(1-min(1, t*1.7)*.5), -2, ang)
    a.ball(-2, cy, 23, 15, SHELL, ang)
    a.line([T(*p) for p in [(-20, cy0-5), (-10, cy0-10), (4, cy0-11), (16, cy0-6)]], 6, 2)
    ex, ey = T(-10, cy0+7)
    a.ellipse(ex, ey, 6, 2, 9)
    for x in (-11, -2, 6):
        dx_, dy_ = T(x, cy0+3+(x % 3))
        a.ellipse(dx_, dy_, 1, 1, 9)
    legs(False)
    for x, y in [(14, cy0+17), (25, cy0+15)]:
        shrink = 1-.75*t                           # the eye stalks draw in as the shell goes over
        base = T(x-4, cy0+7)
        tip = T(x-4+4*shrink, cy0+7+(y-4-cy0-7)*shrink)
        a.limb([base, tip], SHELL, 3)
        a.eye(*T(x-4+4*shrink, cy0+7+(y-cy0-7)*shrink), clip, n, .88)
    if not fall:
        a.ellipse(24, cy0+4, 2, 1, 4)
    claw(*near_c, False)
    if clip == 'die':
        for k in range(3):                            # shell chips fall to the ice
            a.ellipse(-14+k*12+(n % 3)*2, max(2, 34-n*5-k*3), 1.5, 1.5, SHELL[3-k % 2])
    elif clip == 'attack' and st > .55:               # frost bursts where the claws slam
        for k in range(3):
            a.crystal(near_c[0]+10+k*5, 2, 6+k*2, 2.2, 1)
    return a


# ----------------------------------------------------------------------------------------------
# Frostfang Wolf: four jointed legs (shoulder and haunch roots hidden under the barrel, bent hock, tapered shins, four
# paws separated in depth, diagonal gait).  It crouches back, pounces with open jaws and recovers.  On defeat the legs
# fold, the body sinks to the ice and it ends on its side with its legs stiff.
# ----------------------------------------------------------------------------------------------
def wolf(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    a = Painter('wolf', recoil)
    ph = n*math.pi/4
    fx = st*4-wu*4                                       # body shift: crouches back, then springs forward
    cy = mix(28+bob*.4-wu*5+st*3, 14, t)
    u1, u2 = sm(fall/.6), sm((fall-.6)/.4)               # fold the legs, then stretch them out stiff
    tail_wave = math.sin(n*math.pi/3)*3 if clip in ('idle', 'walk') else (-st*5+wu*2)
    tip = (-37+fx, cy+13-t*(cy+13)*.8+tail_wave*.4)
    taper(a, bez((-19+fx, cy+2), (-29+fx, cy+6+tail_wave*(1-t)-t*6), tip), FUR, 8, 1)
    a.crystal(tip[0]+1, tip[1]-1, 7, 2.5, -2, 1.1)

    def leg(front, far):
        depth = 5 if far else 0
        s = ph+(0 if front else math.pi)+(math.pi if far else 0)
        swing = math.sin(s) if clip == 'walk' else 0
        step, lift = swing*3.5, max(0, swing)*4
        base = 3+(3 if far else 0)
        if front:
            root, knee, ankle, ft = (9+depth+fx, cy-4), (7+depth+fx+step*.25, cy-13), (12+depth+step*.7, 10+lift*.7), (13+depth+step, base+lift)
            if clip == 'attack':                        # crouch: elbows out; pounce: forelegs reach up and forward
                ft = (ft[0]-wu*2+st*17, base+st*(17 if not far else 13))
                ankle = (ankle[0]+st*10, 10+st*13)
                knee = (knee[0]+st*6, cy-13+st*4)
            stiff = [(24+depth, cy+2), (30+depth, cy+3), (36+depth, cy+5+(2 if far else 0)), (40+depth, cy+7)]
            fold = [(9+depth, 12), (15+depth, 8), (10+depth, 6), (18+depth, base)]
        else:
            root, knee, ankle, ft = (-21+depth+fx, cy-3), (-14+depth+fx+step*.25, cy-12), (-23+depth+step*.7, 10+lift*.7), (-22+depth+step, base+lift)
            if clip == 'attack':                        # hind legs coil, then drive: hock extends, paw stays planted
                knee = (knee[0]-wu*2+st*8, cy-12-wu*3)
                ankle = (ankle[0]-wu*3-st*4, 10+wu*1)
                ft = (ft[0]-wu*1-st*5, base)
            stiff = [(-27+depth, cy+1), (-33+depth, cy+3), (-38+depth, cy+6+(2 if far else 0)), (-42+depth, cy+8)]
            fold = [(-21+depth, 12), (-12+depth, 8), (-23+depth, 6), (-19+depth, base)]
        pts = [root, knee, ankle, ft]
        pts = [(mix(p[0], q[0], u1), mix(p[1], q[1], u1)) for p, q in zip(pts, fold)]
        pts = [(mix(p[0], q[0], u2), mix(p[1], q[1], u2)) for p, q in zip(pts, stiff)]
        ramp = ICE if far else FUR
        a.limb(pts[:3], ramp, 4 if not far else 3)
        a.limb(pts[2:], ramp, 3 if not far else 2)
        if not far and not u2:
            a.ball(*pts[0], 5 if front else 7, 8 if front else 9, FUR)
        if u2 > .3:
            a.ball(pts[3][0], pts[3][1], 3, 3, FUR)
        else:
            foot(a, pts[3][0], pts[3][1]-3, 4, 3, FUR if not far else ICE)

    for far in (True, False):
        for front in (False, True):
            leg(front, far)
        if far:
            a.ball(-5+fx, cy, 22, 14, FUR)
            a.ball(-3+fx, cy-6, 15, 6, LIGHT_FUR)
            for x, h in [(-17, 7), (-8, 10), (0, 8)]:
                a.crystal(x+fx, cy+12, h, 3, -3)
            a.ball(13+fx, cy+2, 12, 14, FUR)
    reach = st*7-wu*6
    hx, hy = 19+fx+reach, cy+16+bob*.4*(1-t)-wu*5-st*3-t*(cy+16-13)
    for x, tilt in [(hx-7, -2), (hx+3, 3)]:
        a.poly([(x-5, hy+5), (x+tilt, hy+22-t*5), (x+6, hy+6)], 10)
        a.poly([(x-2, hy+8), (x+tilt, hy+18-t*4), (x+3, hy+8)], 22)
    a.ball(hx, hy, 14, 12, FUR)
    jaw = wu*3+st*8 if clip == 'attack' else 0
    a.ball(hx+9, hy-7-jaw, 10, 4, LIGHT_FUR)
    if jaw > .5:
        a.ball(hx+10, hy-5, 7, 3+jaw*.6, MOUTH)
        for sx in (hx+6, hx+13):                      # fangs hang from the upper jaw
            a.poly([(sx-1.4, hy-4), (sx+1.4, hy-4), (sx, hy-7-jaw*.3)], 2)
    a.ball(hx+8, hy-3, 10, 5, FUR)
    a.ellipse(hx+16, hy-2, 3, 2, 1)
    a.eye(hx-3, hy+2, clip, n, 1)
    a.eye(hx+7, hy+2, clip, n, .8)
    if fall < .2:
        a.ellipse(hx-8, hy-6, 2, 1, 4)
    a.line([(hx+5, hy-8), (hx+12, hy-9)], 1)
    if clip == 'attack' and st > .5:                  # frost spray along the bite
        for k in range(2):
            a.crystal(hx+18+k*3, hy-4+k*4, 4+k, 1.8, 1, -1.2)
    if clip == 'die' and n >= 4:
        flakes(a, n, 3, 0, 44, 24, ICE[2:])
    return a


# ----------------------------------------------------------------------------------------------
# Glacier Yeti: heavy furred legs, long arms.  It leans back and throws both fists overhead, then hammers them down
# into the ice.  On defeat the knees buckle, the body tips over sideways like a felled tree, the head lolls and the
# arms go slack.
# ----------------------------------------------------------------------------------------------
def yeti(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    wu, st = atk(clip, n)
    uk, ub = sm(fall/.4), sm((fall-.25)/.75)             # knees buckle first, then the body goes over
    phi = 1.5*ub
    a = Painter('yeti', recoil+st*3-wu*3+12*ub)
    ph = n*math.pi/4
    ty0 = 36+bob*.6+wu*2-st*5
    tx0 = st*5-wu*4+(math.cos(ph)*1.5 if clip == 'walk' else 0)     # torso leans back for the wind-up, forward for the blow
    ty, tx = mix(mix(ty0, 24, uk), 22, ub), mix(tx0, -14, ub)

    def G(x, y):                                            # upper-body rest point -> where the tipping body carries it
        dx, dy = rot(x-tx0, y-ty0, phi)
        return tx+dx, ty+dy

    for sg in (-1, 1):                                      # legs
        sw = math.sin(ph+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sw)*3.5
        hip, knee, ft = (sg*10+tx0*.5, ty0-9), (sg*(10+st*3), 13-st*3), (sg*(12+st*4)+sw*2, 5+lift)
        k_, f_ = G(sg*(10-5*ub), ty0-22), G(sg*(12-6*ub), ty0-31)        # the legs go over with the body
        kk = (mix(knee[0], k_[0], ub), mix(knee[1], k_[1], ub))
        ff = (mix(ft[0], f_[0], ub), mix(ft[1], f_[1], ub))
        a.limb([G(*hip), kk, ff], FUR, 9)
        a.ball(*ff, 10, 5, FUR)

    def hand(sg):                                          # rest / overhead / slammed / slack targets
        rest = (sg*29, 20+(stride*.4 if sg < 0 else 0))
        up = (sg*21, 90)
        down = (sg*18, 14)
        h = (mix(mix(rest[0], up[0], wu), down[0], st), mix(mix(rest[1], up[1], wu), down[1], st))
        slack = (-6, 8) if sg < 0 else (-2, 46)
        g = G(*rest)
        return (mix(h[0], mix(g[0], slack[0], .6), ub), mix(h[1], mix(g[1], slack[1], .6), ub))

    def arm(sg, hnd):
        shoulder = G(sg*17+tx0, ty0+6)
        mid = ((shoulder[0]+hnd[0])/2+sg*7*(1-.5*st)*(1-ub), (shoulder[1]+hnd[1])/2-4*(1-ub)+2*ub)
        a.limb(bez(shoulder, mid, hnd, 4), FUR, 11)
        a.ball(*hnd, 10.5, 10, FUR)

    if st > .55:                                            # ground-pound: ice erupts on both sides of the feet
        for sg in (-1, 1):
            for bx, hgt in ((27, 14), (34, 9), (41, 15), (47, 8)):
                a.crystal(sg*bx+(n % 2), 1, hgt, 3.2, 1)
    if not st:
        arm(-1, hand(-1))
    a.ball(*G(tx0, ty0), 23, 21, FUR)
    a.ball(*G(-3+tx0, ty0-5), 13, 11, LIGHT_FUR)
    for x in (-16, -8, 0, 8, 16):
        a.poly([G(x+tx0-4, ty0-12), G(x+tx0, ty0-23), G(x+tx0+5, ty0-12)], 11)
    hx0, hy0 = tx0+st*7-wu*2, ty0+25-st*9+wu*2+bob*.6
    hx, hy = G(hx0, hy0)
    hy -= 6*ub                                              # the head lolls down onto the ice
    for x, tilt in [(-9, -4), (8, 4)]:
        bx, by = G(hx0+x, hy0+10)
        a.crystal(bx, by-6*ub, 12, 4, tilt, phi)
    a.ball(hx, hy, 16, 15, FUR)
    fdx, fdy = rot(1, -2, phi)
    a.ball(hx+fdx, hy+fdy, 13, 10, FACE)
    a.face(hx+1, hy, clip, n, .9, phi)
    for x in (-5, 8):                                      # tusks stay on the blue face, turned with the head
        l, r_, tp = rot(x-2, -8, phi), rot(x+2, -8, phi), rot(x, -15, phi)
        a.poly([(hx+1+l[0], hy+l[1]), (hx+1+r_[0], hy+r_[1]), (hx+1+tp[0], hy+tp[1])], 3)
    for sg in (-1, 1):
        sx, sy = G(sg*18+tx0, ty0+11)
        if st and sg < 0:
            arm(-1, hand(-1))
        if sg > 0:
            arm(1, hand(1))
        a.ball(sx, sy, 9, 9, FUR)
        a.crystal(sx, sy+6*(1-ub), 9, 3, sg*2, phi)
    if clip == 'die' and n >= 4:
        flakes(a, n, 3, 0, 60, 30, ICE[2:])
    return a


# ----------------------------------------------------------------------------------------------
# Rime Wyrm: three heavy coils, a swan neck and a crested head, a tapering tail.  It draws back, strikes forward with
# frost breath and coils up again.  On defeat the coils slide apart onto the ice and the head drops beside them.
# ----------------------------------------------------------------------------------------------
def wyrm(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    a = Painter('wyrm', recoil)
    wave = ((math.sin(n*math.pi/4)*3+math.cos(n*math.pi/4)*1.5) if clip == 'walk' else math.sin(n*math.pi/3)*2 if clip == 'idle' else 0)*(1-t)
    spread = [-24, 2, 22]
    flat = [10, 13, 10]
    lean = -wu*8+st*4
    pos = []
    for k, (x, y, rx, ry) in enumerate([(0, 10, 26, 10), (1, 23, 22, 10), (-2, 36, 17, 10)]):
        pos.append((mix(x+wave*k*.4+lean*k*.5, spread[k], t), mix(y-wu*k*.6, flat[k], t), rx, ry))
    tx0 = pos[0][0]+16                                      # tail tapers to a point, no blunt cap
    tail_tip = (tx0+24, mix(26+wave*.8-st*3, 14, t))
    taper(a, bez((tx0, 10), (tx0+16, 5), tail_tip), SHELL, 7, 1)
    for k, (xx, yy, rx, ry) in enumerate(pos):
        a.ball(xx, yy, rx, ry, SHELL)
        a.ball(xx+2, yy-3, rx*.7, 4, FACE)
        for j in range(3):
            a.crystal(xx-rx*.6+j*7, yy+7, 6+j % 2*3, 2.5, -2)
    rest, back, fwd, drop = (6+wave, 58+bob), (-14, 62), (40, 28), (37, 12)
    hx = mix(mix(mix(rest[0], back[0], wu), fwd[0], st), drop[0], t)
    hy = mix(mix(mix(rest[1], back[1], wu), fwd[1], st), drop[1], t)
    base = (pos[2][0]+1, pos[2][1]+5)
    ctrl = (mix(base[0], hx-4, .35+st*.15)-3, max(base[1], hy)+14*(1-t)*(1-st*.88)+t*8)
    for nx, ny in bez(base, ctrl, (hx-3, hy-5), 14):          # the neck is a chain of shaded balls: a round tube, no flat ribbon
        a.ball(nx, ny, 6.4, 6.4, SHELL)
    for x, h, tilt in [(-12, 12, -4), (-5, 17, -1), (3, 13, 3)]:
        a.crystal(hx+x, hy+8, h*(1-t*.5), 3, tilt)
    jaw = (1+wu*5+st*8) if clip == 'attack' else max(0, 1-fall*2)
    a.ball(hx+8, hy-8-jaw, 10, 4, FACE)
    if jaw > 1:
        a.ball(hx+9, hy-5, 8, jaw+1, MOUTH)
        for sx in (hx+6, hx+13):
            a.poly([(sx-1.5, hy-5), (sx+1.5, hy-5), (sx, hy-9-jaw*.25)], 2)
    a.ball(hx, hy, 15, 12, SHELL)
    a.ball(hx+9, hy-3, 11, 6, SHELL)
    a.ellipse(hx+17, hy-2, 2, 1, 1)
    a.face(hx+1, hy+2, clip, n, .8)
    if clip == 'attack' and n in (3, 4, 5):
        grow = {3: .55, 4: 1, 5: .9}[n]                    # frost breath: a cone of puffs and shards ahead of the jaws
        for k in range(3):
            a.ball(hx+21+k*7.5*grow, hy-8+k*1.2, (2.6+k*1.8)*grow, (2.4+k*1.5)*grow, ICE[1:])
        for k in range(3):
            a.crystal(hx+24+k*6*grow, hy-3+k*2.2, (7+k*2)*grow, 2.4, 1, -1.2)
    if clip == 'die' and n >= 3:
        for k in range(3):
            a.ellipse(-30+k*22+(n-3)*(k-1)*2, max(2, 34-(n-3)*5-k*3), 1, 1, ICE[2+k % 2])
    return a


DRAW = dict(crab=crab, wolf=wolf, yeti=yeti, wyrm=wyrm)


STRICT = True       # preview sets this False so overruns are listed instead of stopping the sheet
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if clip == 'die':                                       # a fallen body rests on the ice: never sunk, never floating
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size:
            grid = np.roll(grid, kay-int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = 3
    ok = grid.any() and not (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any())
    if not ok:
        BAD.append((kind, clip, n))
    assert ok or not STRICT, (kind, clip, n, 'empty or touches the border')
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
        np.savez_compressed(ROOT/f'scripts/rime_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT/f'scripts/rime_slime_{kind}_raw.npz', **data)
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
        dest = ASSETS/f'rime_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'rime.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 136 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    """Compare the installed atlases directly to the saved editor frames, not to the drawers."""
    meta = json.loads((ASSETS/'rime.txt').read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS/f'rime_{kind}.png').convert('RGBA')
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
    print('Frames empty or touching the border:', BAD or 'none')


if __name__ == '__main__':
    {'preview': preview, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
