#!/usr/bin/env python3
"""Ran's Deep slime-style native PixelFlow sources; preview | build | export | verify.

Greenmeadow shading and eyes, material-appropriate motion and a death that fits
each creature: undead fall apart, soft sea creatures deflate or dissolve, the
shell tips over. Every grounded foot rests exactly on the anchor row (y=0 on the
Painter, row 90), so nothing floats. Export preserves saved editor edits.
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
from wyrd_slime_v1_redraw import Painter, motion, mix
from bifrost_slime_redraw import PALETTE as P0, BLUE, BROWN, FUR, PLATE, PURPLE, TEAL, GOLD, BONE
GREEN = list(range(30, 35))

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/deep-slime'
REGISTRY = ROOT/'scripts/deep_slime_sources.txt'
PREFIX = 'valhallasc_deep_slime_style_b_'
KINDS = ['draugr', 'angler', 'moray', 'siren', 'shellback', 'kraken', 'hvitserk', 'ghostmaw']
NAMES = dict(draugr='Drowned Draugr', angler='Lantern Angler', moray='Gnashing Moray', siren='Siren',
             shellback='Shellback', kraken='The Kraken', hvitserk='Hvitserk', ghostmaw='Ghostmaw')
W = H = 96
AX, AY = 48, 90
CLIPS = old.CLIPS
PALETTE = P0[:] + ['#14242e', '#27434d', '#456a70', '#6a9490', '#9ac8c0',      # 65-69 drowned grey-green flesh
                   '#2a2c10', '#55581f', '#8a8e32', '#bcc255', '#e8ee8c',      # 70-74 olive hide
                   '#6b4670', '#a878a8', '#d6a8cf', '#f2d0e4', '#fff0f6',      # 75-79 pale lilac skin
                   '#3a1c10', '#7a3a1a', '#b8662c', '#e08e4a', '#ffc27a',      # 80-84 rust
                   '#1c1c16', '#3a3a2c', '#5e5c44', '#8a8668', '#bdb894',      # 85-89 rotten rags
                   '#0a1022', '#18284a', '#2c4678', '#4a6cb0', '#8aaae0']      # 90-94 captain's navy
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
DRAUG = list(range(65, 70))
OLIVE = list(range(70, 75))
SKIN = list(range(75, 80))
RUST = list(range(80, 85))
RAG = list(range(85, 90))
NAVY = list(range(90, 95))
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def sm(t):
    t = max(0, min(1, t))
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


def erase(a, f):
    """Ordered-dither dissolve: at f=1 nothing is left of what was drawn so far."""
    arr = np.array(a.im)
    for y in range(H):
        for x in range(W):
            if arr[y, x] and BAYER[y % 4][x % 4]/16 < f:
                arr[y, x] = 0
    a.im = Image.fromarray(arr, 'P')
    a.d = ImageDraw.Draw(a.im)


def bubble(a, x, y, r):
    a.ellipse(x, y, r, r, TEAL[3])
    a.ellipse(x, y, r-1, r-1, 0)
    a.ellipse(x-r*.3, y+r*.3, 1, 1, 2)


def rot(points, angle, ox=0, oy=0):
    c, s = math.cos(angle), math.sin(angle)
    return [(ox+x*c-y*s, oy+x*s+y*c) for x, y in points]


# ----------------------------------------------------------------------------------------------
# Drowned Draugr and Hvitserk (the captain): the dead fall apart; barnacles, weed, ribs and hat scatter.
# ----------------------------------------------------------------------------------------------
def sailor(clip, n, captain=False):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    f = fall
    t = sm(f)
    a = Painter(cx=42+recoil*.8)
    m = lambda s, e: mix(s, e, t)
    coat = NAVY if captain else RAG
    # cape / hanging weed behind the shoulders
    if captain:
        sway = math.sin(n*.8)*1.5 if clip != 'die' else 0
        a.poly([(m(-9, -22), m(40, 4)), (m(9, 8), m(40, 4)), (m(14, 16), m(8, 2)), (m(-3, 0), m(8+sway, 2)), (m(-15, -6), m(10, 3))], NAVY[0])
        a.poly([(m(-8, -20), m(38, 4)), (m(6, 6), m(38, 4)), (m(10, 14), m(10, 3)), (m(-10, -3), m(10, 3))], NAVY[1])
    else:
        for k, ln in enumerate((22, 15)):
            sw = math.sin(n*.9+k)*2 if clip != 'die' else 0
            pts = [(m(-8-k*3, -20-k*4), m(38-k*2, 3)), (m(-13-k*4+sw, -26-k*6), m(30-ln*.3, 7)),
                   (m(-14-k*3+sw*1.4, -22-k*4), m(max(8, 24-ln*.6), 6+k)), (m(-14-k*3+sw*1.6, -26-k*5), m(max(6, 17-ln*.9), 5+k*2))]
            a.line(pts, GREEN[0], 6)
            a.line(pts, GREEN[2], 4)
            a.line(pts[:2], GREEN[3], 1)
    # legs: planted feet sit with their bottom exactly on row 90
    for sg in (-1, 1):
        swing = math.sin(n*math.pi/4+(0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        step = swing*3
        lift = max(0, swing)*3
        hip = (m(sg*4, -14-sg*2), m(17, 6))
        knee = (m(sg*5+step*.5, -20-sg*3), m(10+lift*.5, 8-sg))
        foot = (m(sg*6+step, -29-sg*4), m(3+lift, 3 if sg > 0 else 4))
        ramp = DRAUG if sg > 0 else DRAUG[:4]+[DRAUG[3]]
        a.limb([hip, knee, foot], ramp, 5)
        a.ball(foot[0]+1, foot[1], 6, 3, RAG if not captain else PLATE)
    # arms: the far arm hangs; the near arm swings the axe / cutlass
    hand_r = (m(24+lunge*.5, 6), m(25+max(0, -lunge)*.8, 4))
    a.limb([(m(-11, -16), m(34, 8)), (m(-14, -22), m(26, 6)), (m(-13, -26), m(19, 3))], DRAUG[:4]+[DRAUG[3]], 4)
    a.ball(m(-13, -26), m(19, 3), 3.4, 3.4, DRAUG)
    # torso (a bloated tunic or a navy coat), belt, barnacles
    tc = (m(0, -8), m(27, 9))
    a.ball(tc[0], tc[1], m(11, 16), m(12, 7), coat)
    a.line([(tc[0]-m(10, 14), tc[1]-m(3, 1)), (tc[0]+m(10, 14), tc[1]-m(3, 1))], GOLD[1] if captain else BROWN[0], 2)
    for bx, by in ((6, 5), (-5, 8), (3, -2), (-7, -3)):
        a.ellipse(tc[0]+bx*m(1, 1.3), tc[1]+by*m(1, .4), 1.7, 1.7, BONE[3])
        a.ellipse(tc[0]+bx*m(1, 1.3)-.4, tc[1]+by*m(1, .4)+.5, .8, .8, BONE[4])
    if captain:
        for sg in (-1, 1):
            a.ball(tc[0]+sg*m(10, 14), tc[1]+m(5, 3), 3.6, 3, GOLD)
        a.line([(tc[0], tc[1]+m(10, 5)), (tc[0], tc[1]-m(10, 4))], GOLD[1], 1)
    a.limb([(tc[0]+m(10, 5), m(34, 7)), (m(20+lunge*.3, 8), m(30, 6)), hand_r], DRAUG, 4)
    if clip == 'die':
        # ribs and loose barnacles drop out of the ruined body and scatter on the sea floor
        for j, (bx, by) in enumerate(((8, 6), (-4, 9), (13, 2))):
            p = sm((f-.2-j*.08)/.4)
            if p > 0:
                px, py = tc[0]+bx*(1+p*1.2), mix(tc[1]+by, 3, p)
                a.line([(px-3, py), (px+3, py+1)], BONE[3], 2)
                a.ellipse(px+3, py+1, 1.4, 1.4, BONE[4])
    # head with weed hair (draugr) or tricorn and white beard (captain)
    hx = m(0, 14)+recoil*.3
    hy = m(47+bob*.4, 10)+(math.sin(f*math.pi)*10 if clip == 'die' else 0)
    if clip == 'attack':
        hx += lunge*.4
    if captain:
        a.ball(hx, hy-m(9, 4), m(9, 11), m(7, 5), BONE)
    a.ball(hx, hy, 13, m(12, 9), DRAUG)
    if not captain:
        for j, (dx, hgt) in enumerate(((-9, 9), (-4, 13), (2, 12), (7, 9), (11, 5))):
            sw = math.sin(n*.7+j)*1.2 if clip != 'die' else 0
            a.poly([(hx+dx-3, hy+9), (hx+dx+sw, hy+9+hgt*m(1, .5)), (hx+dx+3, hy+9)], GREEN[1 if j % 2 else 2])
    a.face(hx, hy+1, clip, n, .8)
    if captain:
        a.ball(hx, hy-m(7, 3), 8, m(5, 4), BONE)                    # beard re-laid over the chin; the mouth line stays visible
        a.line([(hx-3, hy-m(5, 2)), (hx, hy-m(6, 3)), (hx+3, hy-m(5, 2))], 1)
        hat = (m(hx, hx+14), m(hy+11, 8))
        # the tricorn lifts off and tumbles away on death
        k = m(1, .55)
        a.poly([(hat[0]-18, hat[1]+1), (hat[0]-13, hat[1]+9*k), (hat[0]-5, hat[1]+5*k), (hat[0]-6, hat[1]-2*k)], PLATE[0])
        a.poly([(hat[0]+18, hat[1]+1), (hat[0]+13, hat[1]+9*k), (hat[0]+5, hat[1]+5*k), (hat[0]+6, hat[1]-2*k)], PLATE[0])
        a.ball(hat[0], hat[1]+3*k, 10, 7*k, PLATE)
        a.line([(hat[0]-16, hat[1]+2), (hat[0]-8, hat[1]+4*k), (hat[0]+8, hat[1]+4*k), (hat[0]+16, hat[1]+2)], GOLD[2], 1)
        a.ellipse(hat[0]+8, hat[1]+4*k, 2.2, 2.2, GOLD[4])
    # weapon: rusted axe (draugr) or cutlass (captain), swung from the hand
    ang = .25+lunge*.22 + (1.45-(.25+lunge*.22))*t
    hand = hand_r
    d = (math.sin(ang), math.cos(ang))
    tip = (hand[0]+d[0]*(24-8*t), hand[1]+d[1]*(24-8*t))
    base = (hand[0]-d[0]*6, hand[1]-d[1]*6)
    a.line([base, tip], BROWN[0], 4)
    a.line([base, tip], BROWN[2], 2)
    if captain:
        a.line([hand, (hand[0]+d[0]*24, hand[1]+d[1]*24)], PLATE[3], 2)
        a.line([(hand[0]-d[1]*5, hand[1]+d[0]*5), (hand[0]+d[1]*5, hand[1]-d[0]*5)], GOLD[2], 2)
    else:
        nx, ny = -d[1], d[0]
        blade = [(tip[0]-d[0]*6, tip[1]-d[1]*6), (tip[0]+nx*9-d[0]*4, tip[1]+ny*9-d[1]*4), (tip[0]+nx*7+d[0]*5, tip[1]+ny*7+d[1]*5), (tip[0]+d[0]*3, tip[1]+d[1]*3)]
        a.poly(blade, RUST[1])
        a.line([blade[1], blade[2]], RUST[3], 1)
    a.ball(*hand, 3.6, 3.6, DRAUG)
    if clip == 'attack' and 3 <= n <= 5:
        a.line([(hand[0]+d[0]*8-4, hand[1]+d[1]*8+3), (hand[0]+d[0]*8+4, hand[1]+d[1]*8-5)], BONE[4], 1)
    return a


def draugr(clip, n):
    return sailor(clip, n, False)


def hvitserk(clip, n):
    return sailor(clip, n, True)


# ----------------------------------------------------------------------------------------------
# Lantern Angler: swims on the spot; the lure flares before a bead is spat, dies out, then it rolls belly-up and sinks.
# ----------------------------------------------------------------------------------------------
def angler(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    f = fall
    t = sm(f)
    a = Painter(cx=42+recoil)
    flip = f > .45
    y = mix(30+bob*.8, 28, t)
    wag = math.sin(n*math.pi/4)*5 if clip == 'walk' else bob*1.5
    if clip == 'die':
        wag = (1-t)*3
    s = -1 if flip else 1                       # fins flip below the body once it rolls over
    # tail fin and dorsal fin
    a.poly([(-18, y), (-31, y+11*s+wag), (-27, y), (-31, y-11*s+wag), (-18, y-3)], BLUE[1])
    a.poly([(-26, y+wag*.4), (-30, y+8*s+wag), (-24, y+1)], BLUE[3])
    a.poly([(-8, y+15*s), (0, y+(26 if s > 0 else 22)*s-wag*.4), (9, y+14*s)], BLUE[1])
    # pectoral fin
    a.poly([(-1, y-2), (-14, y-11-wag*.4), (-6, y-14), (4, y-5)], BLUE[2])
    # lure: flares before the bead is spat, goes dark when it dies
    stalk = [(8, y+15), (16, y+27), (27, y+30)]
    if flip:
        stalk = bez((8, y+14), (24, y+17), (33, 7), 4)
    a.line(stalk, BLUE[0], 3)
    a.line(stalk, BONE[2], 1)
    lure = TEAL if clip != 'die' or n < 1 else PLATE
    if clip == 'die' and n == 1:
        lure = GOLD
    flare = clip == 'attack' and n <= 4
    r = 7 if flare else 5.5
    if flare or (clip != 'die' and n % 2 == 0):
        a.ellipse(stalk[-1][0], stalk[-1][1], r+4, r+4, TEAL[1] if lure is TEAL else PLATE[1])
    a.ball(stalk[-1][0], stalk[-1][1], r, r, lure)
    if flare:
        for dx, dy in ((10, 4), (-9, 7), (3, 11)):
            a.line([(stalk[-1][0]+dx*.6, stalk[-1][1]+dy*.6), (stalk[-1][0]+dx, stalk[-1][1]+dy)], TEAL[4], 1)
    # body and belly
    a.ball(0, y, 23, 17, BLUE)
    belly_y = y-9*s
    a.ball(3, belly_y, 17, 8, BONE if flip else BLUE[1:])
    # jaw: opens wide on attack, hangs open and slack in death
    gap = 2+max(0, lunge)*2 if clip == 'attack' else 2
    if clip == 'die':
        gap = 2+4*t
    a.poly([(11, y-1), (27, y+1), (26, y-6-gap), (12, y-8-gap)], 1)
    a.ball(16, y-9-gap, 11, 5, BLUE)
    for j in range(4):
        a.poly([(13+j*4, y-1), (15+j*4, y-5), (17+j*4, y-1)], 3)
        a.poly([(14+j*4, y-9-gap+4), (16+j*4, y-9-gap+8), (18+j*4, y-9-gap+4)], 3)
    a.eye(10, y+6, clip, n, .9)
    a.ellipse(18, y+1, 2.5, 1.3, 4)
    if clip == 'attack' and 3 <= n <= 5:
        a.ball(33+(n-3)*3, y-3-gap*.5, 3, 3, TEAL)
    if clip == 'die':
        for j in range(3):
            bubble(a, 18+j*6, y+14+n*3+j*5-t*4, 2+j % 2)
    return a


# ----------------------------------------------------------------------------------------------
# Moray and Ghostmaw: eels on the sea floor. The moray goes limp and settles; the Ghostmaw's flesh dissolves to a skeleton and wisps.
# ----------------------------------------------------------------------------------------------
def eel(clip, n, ghost=False):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    f = fall
    t = sm(f)
    L = 52 if ghost else 52
    a = Painter(cx=(39 if ghost else 40)+recoil)
    ramp = TEAL if ghost else GREEN
    belly = BONE if ghost else OLIVE
    N = 16
    phase = (n/6*2*math.pi) if clip == 'idle' else (n/8*2*math.pi) if clip == 'walk' else n/4*math.pi
    amp = (3 if clip == 'idle' else 6 if clip == 'walk' else 3.5)*(1-t)
    hl = (12 if ghost else 10)+bob*.9                       # how high the head is carried
    reach = 0
    if clip == 'attack':
        hl = [14, 20, 24, 8, 3, 5, 8, 9][n]
        reach = [-2, -4, -5, 2, 3, 2, 1, 0][n]
    if clip == 'hurt':
        hl = 9+[4, 8, 5, 2][n]
        reach = [-2, -3, -1, 0][n]
    if clip == 'die':
        hl += [0, 7, 5, 3, 1, 0, 0, 0][n]        # a last convulsion before it goes limp
    hl *= (1-t)
    pts = []
    for i in range(N):
        s = i/(N-1)
        r = 2.8+(10.6 if ghost else 8.9)*math.sin(min(1, s*1.15)*math.pi/2)
        wave = amp*(.5+.5*math.sin(2*math.pi*1.1*s-phase))
        x = mix(-L*.55, L*.45, s)+reach*sm((s-.5)/.5)
        yy = r+wave+hl*sm((s-.5)/.5)**1.4
        if clip == 'die':
            # limp: the coil settles into a gentle S lying on the floor
            yy = r+(2.5*math.sin(2*math.pi*1.1*s-2.2)+2.5)*t*.6+(1-t)*(wave+hl*sm((s-.5)/.5)**1.4)
        pts.append((x, yy, r))
    spikes = []
    for i in range(1, N-1):
        x, yy, r = pts[i]
        h = (6 if ghost else 4.5)*(1-t*.8)
        if i % 3 == 0:
            spikes.append((x, yy+r*.8, h))
    for x, yy, h in spikes:
        if ghost:
            a.crystal(x, yy-1, height=h+2, width=2.6, tilt=-1)
        else:
            a.poly([(x-3, yy-1), (x-1, yy+h), (x+3, yy-1)], GREEN[3])
    for x, yy, r in pts[:-1]:
        a.ball(x, yy, r*1.18, r, ramp)
        a.ellipse(x+.5, yy-r*.55, r*.75, r*.32, belly[2] if ghost else belly[3])
    # stripes / bands along the back
    for i in range(3, N-2, 3):
        x, yy, r = pts[i]
        a.line([(x-1, yy+r*.9), (x+1, yy+r*.3)], ramp[0], 1)
    hx, hy, hr = pts[-1]
    hr = hr+1.0
    a.ball(hx, hy, hr*1.2, hr, ramp)
    gap = 1.5
    if clip == 'attack':
        gap = [2, 4, 6, 12, 9, 5, 3, 2][n]
    if clip == 'die':
        gap = 2+9*t
    jy = max(5+gap*.5, 0)
    a.poly([(hx+3, hy+3), (hx+hr+7, hy+1), (hx+hr+6, hy-2), (hx+3, hy-4)], ramp[2])
    a.poly([(hx+3, hy-4), (hx+hr+5, hy-3-gap*.4), (hx+hr+4, max(2, hy-6-gap)), (hx+1, max(2, hy-8-gap*.6))], 1)
    a.ball(hx+3, max(4, hy-7-gap), 9, 4, ramp)
    for j in range(3):
        a.poly([(hx+5+j*4, hy-3), (hx+7+j*4, hy-6), (hx+9+j*4, hy-3)], 3)
        a.poly([(hx+5+j*4, max(2, hy-9-gap)+3), (hx+7+j*4, max(2, hy-9-gap)+7), (hx+9+j*4, max(2, hy-9-gap)+3)], 3)
    a.eye(hx+2, hy+3, clip, n, .85)
    a.ellipse(hx+6, hy-1, 2.2, 1.2, 4)
    if clip == 'attack' and 3 <= n <= 5:
        a.line([(hx+hr+8, hy), (hx+hr+11, hy+3)], 3, 1)
    if clip == 'die' and n >= 6 and not ghost:
        a.ellipse(hx+hr+2+(n-5)*1.5, max(2, hy-6-gap), 3+(n-6)*2, 1.6, 4)      # the tongue lolls out
    if ghost:
        if clip == 'die':
            # flesh dissolves in a dither, leaving a skeleton and rising wisps
            erase(a, min(1, f*1.15))
            sp = [(x, yy) for x, yy, r in pts]
            if f > .2:
                a.line([(x, yy) for x, yy in sp], BONE[3], 2)
                for x, yy in sp[1:-1:1]:
                    a.line([(x, yy), (x+1, max(1, yy-5))], BONE[2], 1)
                    a.line([(x, yy), (x-1, max(1, yy+3))], BONE[2], 1)
                a.ball(hx+2, hy, 9, 7, BONE)
                a.poly([(hx+8, hy-1), (hx+hr+5, hy-1), (hx+hr+4, max(2, hy-5-gap*.5)), (hx+4, max(2, hy-5))], BONE[3])
                a.ellipse(hx+2, hy+1, 2.4, 2.4, 1)
            for j in range(4):
                wx = -20+j*13+math.sin(n+j)*3
                wy = 12+f*46+j*5
                if wy < 82:
                    a.poly([(wx-2, wy), (wx, wy+6), (wx+2, wy), (wx, wy-3)], TEAL[3+j % 2])
    return a


def moray(clip, n):
    return eel(clip, n, False)


def ghostmaw(clip, n):
    return eel(clip, n, True)


# ----------------------------------------------------------------------------------------------
# Siren: Ran's handmaiden. She sings in the air; when she dies she dissolves into sea foam and bubbles.
# ----------------------------------------------------------------------------------------------
def siren(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    f = fall
    t = sm(f)
    a = Painter(cx=44+recoil)
    hv = (12+bob*1.1)*(1-t)+2
    sway = math.sin(n*math.pi/4)*3 if clip == 'walk' else bob
    # tail: a curving fish tail that ends in a two-lobed fin
    tail = bez((0, hv+22), (-24, hv+14+sway*.4), (-14, hv+1), 9)
    taper(a, tail, PURPLE, 16, 6)
    ex, ey = tail[-1]
    a.poly([(ex+1, ey+1), (ex-13, ey-8+sway), (ex-9, ey+3), (ex-15, ey+15-sway), (ex+3, ey+9)], PURPLE[2])
    a.poly([(ex, ey+1), (ex-10, ey-5+sway), (ex-6, ey+3)], PURPLE[3])
    for j in range(4):
        a.ellipse(tail[2+j][0]+1, tail[2+j][1]+1, 1.6, 1.6, PURPLE[4])
    # hair behind the head, streaming with the current
    a.ball(-6, hv+51, 16, 15, BLUE)
    for j in range(3):
        sg = math.sin(n*.8+j)*2.5 if clip != 'die' else 0
        a.poly([(-14+j*5, hv+46), (-24-j*2+sg, hv+30-j*3), (-17+j*5+sg, hv+25-j*3), (-8+j*5, hv+44)], BLUE[1+j % 2])
    # torso and shell top
    a.ball(0, hv+33, 10, 11, SKIN)
    a.ball(-4.5, hv+36, 5.5, 5.5, PURPLE)
    a.ball(4.5, hv+36, 5.5, 5.5, PURPLE)
    # arms: folded in idle, flung wide when she sings
    sing = clip == 'attack' and 1 <= n <= 6
    for sg in (-1, 1):
        hand = (sg*(19 if sing else 6), hv+(47 if sing else 29)+(max(0, lunge)*.6 if sg > 0 else 0))
        a.limb([(sg*8, hv+38), (sg*(13 if sing else 9), hv+(42 if sing else 31)), hand], SKIN, 4)
        a.ball(*hand, 3, 3, SKIN)
    # head, pearl, face
    a.ball(0, hv+53, 13, 12, SKIN)
    a.ball(10, hv+63, 3, 3, BONE)
    a.face(0, hv+53, clip, n, .9)
    if sing:
        a.ellipse(0, hv+45, 3.2, 3.6, 1)
        a.ellipse(0, hv+45, 2.2, 2.6, 4)
        for j, (nx, ny) in enumerate(((26, 62), (35, 50), (-30, 58))):
            a.ellipse(nx, hv+ny-(n % 3)*2, 2.4, 2, GOLD[2])
            a.line([(nx+2, hv+ny-(n % 3)*2), (nx+2, hv+ny+7-(n % 3)*2)], GOLD[2], 1)
    if clip == 'die':
        erase(a, min(1, f*1.15))
        # foam pooling on the sea floor and bubbles rising from where she was
        for j, (bx, rx, ry) in enumerate(((-16, 6, 4), (-6, 8, 5), (6, 9, 4), (17, 6, 3))):
            if f > .15+j*.08:
                a.ball(bx, ry, rx*min(1, f*1.4), ry, BONE)
        for j in range(5):
            by = 10+f*40+j*6
            if by < 80:
                bubble(a, -14+j*8+math.sin(n+j)*2, by, 2+j % 2)
        if f > .5:
            a.ball(0, 7, 3, 3, GOLD)                # the pearl is what remains
    return a


# ----------------------------------------------------------------------------------------------
# Shellback: rigid shell on stout legs. Death: head and legs pull in, then the whole shell tips over onto its side.
# ----------------------------------------------------------------------------------------------
def shellback(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    f = fall
    pull = sm(f/.5)
    tip = sm((f-.45)/.55)
    a = Painter(cx=44+recoil)
    sy = 30+bob*.5
    if clip == 'attack':
        sy += [0, 1.5, 3, -2, -4, -1, 0, 0][n]            # rears up, then slams down
    sy = mix(sy, 19, pull)                                  # with the legs drawn in, the shell rests on the sea floor
    sy = mix(sy, 17, tip)
    sx = 5*tip
    # plank growing out of the shell (drawn first: it sticks up behind the dome)
    plank = [(-3, 0), (3, 0), (4, 19), (-2, 21)]
    pa = mix(.42, 1.5, tip)
    pivot = (mix(-12, -14, tip), mix(sy+11, 5, tip))
    pts = rot(plank, pa, *pivot)
    a.poly(pts, BROWN[1])
    a.line([pts[0], pts[3]], BROWN[0], 1)
    a.line([pts[1], pts[2]], BROWN[3], 1)
    a.ellipse(*rot([(0, 13)], pa, *pivot)[0], 1.4, 1.4, 5)
    # legs: near pair and far pair, every near foot flat on row 90
    for far in (True, False):
        for k, hx in enumerate((-15, 17)):
            ph = (0 if k == 0 else math.pi)+(math.pi/2 if far else 0)
            swing = math.sin(n*math.pi/4+ph) if clip == 'walk' else 0
            lift = max(0, swing)*3
            if clip == 'attack' and k == 1:
                lift += max(0, -lunge)*2.2
            hipx = hx+(5 if far else 0)-(0 if k == 0 else 3)
            foot = (hipx+swing*2.5, (4 if not far else 4)+lift)
            ry = 4 if not far else 3
            foot = (foot[0], ry+lift+(1 if far else 0))
            if pull > 0:
                foot = (mix(foot[0], hipx*.5, pull), mix(foot[1], 16, pull))
            if tip > .3:
                continue
            a.limb([(hipx, 15), (hipx+swing, 9+lift*.5), foot], OLIVE, 7 if not far else 6)
            a.ball(foot[0]+1, foot[1], 7 if not far else 6, ry, OLIVE)
            if foot[1] < 10:
                a.line([(foot[0]-1, foot[1]+ry-1), (foot[0]+4, foot[1]+ry-1)], OLIVE[3], 1)
    # head and neck: retract and hide as the shell takes over
    ext = 1-pull
    hx = mix(20, 31+(lunge*.5 if clip == 'attack' else 0), ext)
    hy = 22+bob*.4+(2 if clip == 'attack' and n in (3, 4) else 0)
    if clip == 'hurt':
        hx -= [2, 5, 3, 1][n]
    if tip < .6:
        a.limb([(20, 25), (mix(22, 26, ext), 25), (hx, hy)], OLIVE, 8)
        a.ball(hx, hy, 10, 9, OLIVE)
        a.poly([(hx+6, hy+2), (hx+16, hy-1), (hx+14, hy-5), (hx+6, hy-5)], GOLD[2])
        a.poly([(hx+7, hy-5), (hx+14, hy-5), (hx+12, hy-8), (hx+7, hy-8)], GOLD[1])
        a.eye(hx+1, hy+3, clip, n, .9)
        a.ellipse(hx-6, hy-2, 2.4, 1.3, 4)
    # the dome: dark plates and a lighter rim, a weed tuft and a few barnacles
    a.ball(sx, sy, 28, mix(18, 16, tip), GREEN)
    for hxp, hyp in ((-14, 3), (0, 8), (14, 3), (-6, -6), (8, -6)):
        a.ellipse(sx+hxp, sy+hyp*mix(1, .6, tip), 6, 4.2*mix(1, .6, tip), GREEN[3])
        a.ellipse(sx+hxp, sy+hyp*mix(1, .6, tip), 5, 3.2*mix(1, .6, tip), GREEN[2])
    for bx, by in ((-20, -2), (20, 0), (4, 14)):
        a.ellipse(sx+bx, sy+by*mix(1, .6, tip), 1.8, 1.6, BONE[3])
    tuft = sy+mix(17, 13, tip)
    for j, (dx, hh) in enumerate(((-7, 9), (-2, 14), (3, 12), (8, 8))):
        sw = math.sin(n*.8+j)*1.2 if clip != 'die' else 0
        a.poly([(sx-9+j*5-3, tuft), (sx+dx+sw, tuft+hh*.6), (sx-9+j*5+3, tuft)], GREEN[3 if j % 2 else 4])
    if tip > .25:
        # the shell has rolled onto its side: the pale belly plate faces out with the dark opening and a limp head
        k = sm((tip-.25)/.75)
        a.ball(15, sy, 13*k, 16*mix(1, .85, tip)*k, BONE)
        a.ellipse(16, sy-1, 8*k, 11*k, 1)
        hx2, hy2 = 33, 7
        a.ball(hx2, hy2, 9*k, 7*k, OLIVE)
        if k > .5:
            a.eye(hx2+1, hy2+1, 'die', 6, .7)
            a.poly([(hx2+5, hy2-1), (hx2+12, hy2-2), (hx2+10, hy2-5), (hx2+5, hy2-6)], GOLD[2])
    if clip == 'attack' and n in (4, 5):
        for dx in (-3, 5, 12):
            a.ellipse(26+dx, 3+(n-4)*2, 3-(n-4), 2, BONE[3])
    return a


# ----------------------------------------------------------------------------------------------
# The Kraken: a violet mantle on stubby tentacles. It deflates on death; the tentacles go slack and splay.
# ----------------------------------------------------------------------------------------------
def kraken(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    f = fall
    t = sm(f)
    a = Painter(cx=44+recoil)
    ry = mix(21, 10, t)
    rx = mix(21, 26, t)
    my = mix(46+bob*.7, ry+6, t)
    roots = [(-16, 0), (-10, 0), (-3, 0), (4, 0), (11, 0), (18, 0)]
    for i, (rxp, _) in enumerate(roots):
        ph = i*math.pi/3
        swing = math.sin(n*math.pi/4+ph) if clip == 'walk' else math.sin(n*math.pi/3+ph)*.25 if clip == 'idle' else 0
        tipx = rxp*1.7+swing*4
        tipy = 2+max(0, swing)*4
        mid_y = 22
        if clip == 'attack' and i >= 4:
            wu = [8, 16, 20, 0, -2, 4, 6, 8][n]
            tipx = rxp*1.7+[-4, -8, -10, 7, 10, 7, 4, 0][n]
            tipy = 2+max(0, wu)*1.6
        if clip == 'hurt':
            tipx += [-3, -2, -1, 0][n]
        if clip == 'die':
            tipx = mix(tipx, rxp*1.9+(4 if i > 2 else -4)*t, t)
            tipy = mix(tipy, 2, t)
            mid_y = mix(22, 11+(i % 2)*3, t)
        root = (rxp*.8, my-ry*.55)
        ctrl = (rxp*1.5+(tipx-rxp*1.7)*.4, mid_y+(my-ry-mid_y)*.0)
        path = bez(root, ctrl, (tipx, tipy), 9)
        taper(a, path, PURPLE, 8, 3)
        for s in (.45, .7):
            px, py = path[int(s*9)]
            a.ellipse(px+.5, py, 1.4, 1.2, PURPLE[4])
    # mantle: glossy, with darker spots and a pale crown
    a.ball(0, my, rx, ry, PURPLE)
    for sx, sy_, r in ((-12, 12, 3.2), (10, 14, 2.6), (-4, 19, 2), (16, 6, 2)):
        a.ellipse(sx*mix(1, 1.2, t), my+sy_*mix(1, .4, t), r, r*.8, PURPLE[1])
    a.ellipse(-7, my+ry*.62, 8, 3, PURPLE[4])
    a.face(0, my+1, clip, n, 1.0)
    a.poly([(-3, my-8*mix(1, .6, t)), (3, my-8*mix(1, .6, t)), (0, my-14*mix(1, .6, t))], BROWN[2])
    a.poly([(-2, my-9*mix(1, .6, t)), (2, my-9*mix(1, .6, t)), (0, my-12*mix(1, .6, t))], BROWN[3])
    if clip == 'attack' and 3 <= n <= 5:
        for dx in (22, 30, 38):
            a.ellipse(dx+(n-3)*2, 3, 3, 2, TEAL[3])
    if clip == 'die' and f > .5:
        for j in range(3):
            bubble(a, -12+j*12, 28+f*26+j*7, 2+j % 2)
    return a


DRAW = dict(draugr=draugr, angler=angler, moray=moray, siren=siren, shellback=shellback, kraken=kraken, hvitserk=hvitserk, ghostmaw=ghostmaw)


def frame(kind, clip, n):
    grid = np.array(DRAW[kind](clip, n).im)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = 3
    if os.environ.get('DEEP_LOOSE'):
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
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}      # validate every kind before saving any source
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX+kind+'_all'
        assert name not in existing, 'Unregistered source already exists: '+name
        np.savez_compressed(ROOT/f'scripts/deep_slime_{kind}_raw.npz', **data[kind])
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


def cel_grid(cel):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    saved = json.loads(REGISTRY.read_text())
    assert set(saved) == set(KINDS)
    meta = dict(frame=[W, H], anchor=[AX, AY], kinds=KINDS, clips={}, sprites=saved, tops={}, artStyle='greenmeadow-slime')
    proof = {}
    atlases = {}
    for kind in KINDS:       # read and validate every saved editor source before replacing any installed file
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, 34)
        atlas = Image.new('RGBA', (8*W, 5*H))
        offset = 0
        rows = []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset+n]['cels'][0]), sp['palette'])
                bounds = im.getbbox()
                assert bounds and min(bounds[:2]) > 0 and max(bounds[2:]) < 96
                atlas.alpha_composite(im, (n*W, row*H))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['tops'][kind] = int(AY-min(r['bounds'][1] for r in rows if r['clip'] == 'idle'))
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for kind, atlas in atlases.items():
        dest = ASSETS/f'deep_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'deep.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print('Exported 272 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames, not drawers."""
    meta = json.loads((ASSETS/'deep.txt').read_text())
    saved = json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id='+saved[kind])['sprite']
        atlas = Image.open(ASSETS/f'deep_{kind}.png').convert('RGBA')
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n*W, row*H, (n+1)*W, (row+1)*H))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset+n]['cels'][0]), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
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
                sd.text((n*192+8, row*218+194), f'{clip} {n}', fill='white')
            im = rgba(grids[0 if clip != 'die' else 7]).resize((192, 192), Image.Resampling.NEAREST)
            overview.paste(im, (col*240+20, row*218), im)
            d.text((col*240+20, row*218+194), f'{NAMES[kind]} / {clip}', fill='white')
        sheet.save(OUT/f'preview-{kind}.png')
    overview.save(OUT/'preview.png')
    print(OUT/'preview.png')


if __name__ == '__main__':
    {'preview': preview, 'build': build, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
