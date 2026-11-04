#!/usr/bin/env python3
"""Grand Nave (Drowned Cathedral wing 3, zone 12) slime-style native PixelFlow sources.

preview | extents | build | refresh | export | verify.
Greenmeadow glossy shading, big eyes with highlights (#fffbea) and blush, material-appropriate movement,
per-kind frame sizes (KIND_FRAMES, docs/kind-frames.md), grounded feet/bases on the anchor row in every living
and death frame (QUADRUPED-GROUNDING), eight distinct attack frames (wind-up, strike, recovery) and eight
distinct fitting death frames per kind:
  - abysszealot: hunched deep-indigo robed zealot in a tall pointed cowl swinging a golden chain censer burning
    with violet abyssal flame; whirls the censer high overhead then whips it far forward in a burst of abyssal
    fire; on death the censer clatters flat as its flame gutters out and the empty robe crumples on the floor.
  - chainmarshal: Vargast, heavy dark-steel and gold plated juggernaut bound in crossed chains with a chest
    padlock, spiked pauldrons, horned helm and a massive iron ship-anchor on a chain; heaves the anchor high
    overhead then slams it far forward with shockwave sparks; on death his armoured legs buckle, the anchor and
    chains crash flat and his steel plate collapses into a low heap.
  - starseraph: Astrael, fallen seraph in a star-spangled lavender gown with four feathered wings, broken golden
    halo and crystal tear; spreads her wings and starlight orb high overhead then sweeps forward to loose a
    blazing shooting-star volley; on death her halo shatters to the floor, her four wings fold and droop, and
    she sinks into a peaceful pool of starlit cloth and feathers.
  - tidejudicator: monumental slate-and-parchment robed judge with a brow blindfold band, golden judicial crown,
    tilting Balance Scales of the Tide and a massive iron-and-gold gavel; raises the gavel high overhead as the
    scales flare then slams it down far ahead with a verdict shockwave; on death the scales spill onto the floor,
    the gavel drops flat, the crown slips and the heavy robes collapse low.
  - hierophant: High Hierophant Vael, Heart of the Tide, in royal-violet and gold cathedral vestments with a
    glowing cyan Tide-Heart on his chest, flowing silver beard, tall papal mitre and golden Tide-Orb crosier;
    hoists the crosier high above his mitre with a cresting tidal halo then sweeps a surging torrent of tide
    orbs forward; on death the Tide-Heart cracks and dims, the crosier and mitre tumble to the floor, and his
    vestments crumple low.

`client/assets/cathedral.txt` is shared by 146 kinds: export replaces ONLY these five kinds' `sprites`, `tops`
and `kindFrames` entries and asserts that all other 141 kinds (including Flooded Cloister's `tidetemplar` and
`tidecantor`, which also spawn in Grand Nave, and Coral Reliquary's six kinds) are untouched.
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
from reliquary_slime_redraw import (
    PALETTE, OUTLINE, WHITE, EYE_WHITE, BLUSH,
    BONE, PLATE, PURPLE, TEAL, GOLD, GREEN, FUR, BLUE, BROWN, OLIVE,
    PINK, MAROON, CORAL, PEARL, VIOLET, CRIMSON, AMBER,
    mix, mixp, rot, sm, bez, taper, foot, spark, motion, atk,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/nave-slime'
REGISTRY = ROOT / 'scripts/nave_slime_sources.txt'
MANIFEST = ASSETS / 'cathedral.txt'
PREFIX = 'valhallasc_nave_slime_style_'
KINDS = ['abysszealot', 'chainmarshal', 'starseraph', 'tidejudicator', 'hierophant']
NAMES = dict(
    abysszealot='Abyssal Zealot',
    chainmarshal='Vargast, Marshal of the Drowned Chains',
    starseraph='Astrael, the Fallen Tide Seraph',
    tidejudicator='The Blind Tide Judicator',
    hierophant='High Hierophant Vael, Heart of the Tide',
)
W = H = 96
AX, AY = 48, 90
KIND_FRAMES = dict(
    abysszealot=(128, 104, 52, 98),
    chainmarshal=(136, 112, 54, 106),
    starseraph=(136, 114, 56, 108),
    tidejudicator=(136, 112, 56, 106),
    hierophant=(136, 116, 54, 110),
)
CLIPS = old.CLIPS


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


class Painter:
    """Round glossy shaded components on a kind-sized canvas; y is up from the ground row, x from the centre."""
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax - 2 + dx

    def pos(self, x, y):
        return round(self.cx + x), round(self.ay - y)

    def ellipse(self, x, y, rx, ry, col):
        px, py = self.pos(x, y)
        self.d.ellipse((round(px - rx), round(py - ry), round(px + rx), round(py + ry)), fill=col)

    def line(self, pts, col, width=1):
        self.d.line([self.pos(*p) for p in pts], fill=col, width=width)

    def poly(self, pts, col, outline=None):
        self.d.polygon([self.pos(*p) for p in pts], fill=col, outline=outline)

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        px, py = self.pos(x, y)
        R = max(rx, ry)
        c, s = math.cos(ang), math.sin(ang)
        for yy in range(max(0, math.floor(py - R)), min(self.h, math.ceil(py + R) + 1)):
            for xx in range(max(0, math.floor(px - R)), min(self.w, math.ceil(px + R) + 1)):
                dx, dy = xx - px, yy - py
                u, v = (dx * c - dy * s) / rx, (dx * s + dy * c) / ry
                rr = u * u + v * v
                if rr > 1:
                    continue
                z = math.sqrt(max(0, 1 - rr))
                nx, ny = u * c + v * s, -u * s + v * c
                value = max(0, min(.999, .23 + .71 * (-.40 * nx - .54 * ny + .74 * z))) * (len(ramp) - 1)
                lo = int(value)
                threshold = ((xx % 4) * 5 + (yy % 4) * 3) % 16 / 16
                shade = min(len(ramp) - 1, lo + int(value - lo > threshold))
                if rr > .93 and nx + ny > .2:
                    shade = 0
                self.im.putpixel((xx, yy), ramp[shade])

    def limb(self, points, ramp, width=5):
        self.line(points, ramp[0], width + 2)
        self.line(points, ramp[min(2, len(ramp) - 1)], width)
        for x, y in points[1:-1]:
            self.ball(x, y, width / 2, width / 2, ramp)

    def eye(self, x, y, clip, n, size=1.):
        if clip == 'die' and n >= 2:
            self.line([(x - 2, y - 2), (x + 2, y + 2)], 1, 2)
            self.line([(x - 2, y + 2), (x + 2, y - 2)], 1, 2)
        elif clip == 'idle' and n == 3:
            self.line([(x - 3 * size, y), (x + 3 * size, y + .5)], 1, 2)
        else:
            self.ellipse(x, y, 4.3 * size, 6.4 * size, 1)
            self.ellipse(x, y + .5, 3.3 * size, 5.3 * size, EYE_WHITE)
            self.ellipse(x + 1, y - .2, 1.6 * size, 3.4 * size, 1)
            self.ellipse(x + .7, y + 2.2, 1, 1, 2)
            if clip == 'attack' and n < 3:
                self.line([(x - 4, y + 6), (x + 3, y + 3)], 1, 2)

    def face(self, x, y, clip, n, size=1.):
        for dx in (-6, 6):
            self.eye(x + dx * size, y, clip, n, size)
        if clip != 'die' or n < 2:
            self.ellipse(x - 11 * size, y - 5, 2.5, 1.3, BLUSH)
            self.ellipse(x + 11 * size, y - 5, 2.5, 1.3, BLUSH)
        self.line([(x - 3, y - 8), (x, y - 9), (x + 3, y - 8)], 1)


def chain_links(a, p0, p1, sag=4., count=6, ramp=PLATE, r=2.0):
    for k in range(count + 1):
        s = k / count
        cx = mix(p0[0], p1[0], s)
        cy = max(2.5, mix(p0[1], p1[1], s) - math.sin(s * math.pi) * sag)
        a.ball(cx, cy, r, r, ramp)


# ----------------------------------------------------------------------------------------------
# 1. Abyssal Zealot (`abysszealot`): hunched deep-indigo/violet ragged robe and tall pointed cowl with gold
#    trim and bone clasp, big staring glossy eyes and blush under the hood, swinging a golden chain censer
#    burning with violet-and-teal abyssal flame.
#    Attack: whirls and hoists the burning censer high overhead on its chain, then whips it far forward in a
#    blazing arc of violet flame before recovering.
#    Death: the chain censer clatters flat onto the floor as its flame gutters out, and the empty robe and
#    pointed cowl crumple into a folded heap on the floor while abyssal motes dissipate upward.
# ----------------------------------------------------------------------------------------------
def abysszealot(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    sway = math.sin(ph) * 2.2 if clip == 'walk' else math.sin(n * math.pi / 3) * 1.0 if clip == 'idle' else 0
    a = Painter('abysszealot', recoil + st * 4 - wu * 2)

    h = mix(1.0, .30, t)
    hw = round(mix(18, 27, t))
    top = 42 * h + bob * .4 * (1 - t)

    # Hunched ragged violet robe with gold trim resting solidly on y=0
    a.poly([(-11 + sway * .3, top), (11 + sway * .3, top), (hw, 0), (-hw, 0)], VIOLET[1], outline=OUTLINE)
    a.poly([(-11 + sway * .3, top), (-1, top), (-2, 0), (-hw, 0)], VIOLET[0])
    a.line([(-hw + 1, 0), (hw - 1, 0)], OUTLINE, 1)
    a.line([(-hw + 3, 3), (hw - 3, 3)], GOLD[2], 2)
    for dx in (-10, 0, 10):
        a.line([(dx * .5 + sway * .3, top - 3), (dx * mix(1.2, 1.6, t), 2)], VIOLET[3] if dx >= 0 else VIOLET[0], 1)

    # Upper mantle and golden rune belt
    a.ball(1, 32 * h + 2, 12, 10 * h + 1, VIOLET)
    a.line([(-12, 20 * h + 2), (12, 20 * h + 2)], GOLD[2], 2)
    a.ball(1, 20 * h + 2, 3.2, 2.8, GOLD)

    # Far arm holding spare chain links
    a.limb([(-9, 36 * h), (-16, 28 * h), (-19 - wu * 2, mix(22, 4, t))], VIOLET[:4], 4)
    a.ball(-19 - wu * 2, mix(22, 4, t), 3.2, 3.2, BONE)

    # Tall pointed abyssal cowl and shadowed face with big glossy eyes & blush
    hx = mix(2, 9, t) + sway * .3
    hy = mix(51 + bob * .5 + wu * 2 - st * 1, 13, t)
    cowl_top = (hx - 3 - sway * .4 - t * 8, hy + mix(23, 6, t))
    a.poly([(hx - 14, hy - 5), (hx - 12, hy + 8), cowl_top, (hx + 12, hy + 8), (hx + 14, hy - 5)],
           VIOLET[2], outline=OUTLINE)
    a.ball(hx, hy, 12, mix(10.5, 7, t), VIOLET)
    a.ball(hx + 1, hy - 1, 9.2, mix(8.5, 5.5, t), PURPLE[:4])
    a.ball(cowl_top[0], cowl_top[1], 2.6, 2.6, GOLD)
    a.face(hx + 2, hy - 1, clip, n, .78)

    # Right arm and golden chain censer (hoisted high overhead clear of the face on wind-up, whipped far forward on strike)
    hand_x = mix(mix(17, 20, wu), 25, st)
    hand_y = mix(mix(33 + bob * .4, 58, wu), 36, st)
    swing = (math.sin(n * math.pi / 3) * 3 if clip == 'idle' else math.sin(ph) * 4 if clip == 'walk' else 0)
    cx_c = mix(mix(20 + swing, 22, wu), 46, st)
    cy_c = mix(mix(16, 72, wu), 31, st)
    if clip == 'die':
        drop = sm(fall / .55)
        hand_x, hand_y = mix(17, 20, drop), mix(33, 5, drop)
        cx_c, cy_c = mix(20, 32, drop), mix(16, 6, drop)
    if clip != 'die' or fall < .4:
        a.limb([(10, 36 * h), ((10 + hand_x) / 2 + 2, (36 * h + hand_y) / 2), (hand_x, hand_y)], VIOLET, 4)
        a.ball(hand_x, hand_y, 3.4, 3.4, BONE)

    chain_links(a, (hand_x, hand_y), (cx_c, cy_c), sag=mix(3.5, .5, max(wu, st)) * (1 - t), count=5, ramp=PLATE, r=1.8)
    a.ball(cx_c, max(6, cy_c), 6.5, 6, GOLD)
    a.line([(cx_c - 6, max(6, cy_c)), (cx_c + 6, max(6, cy_c))], GOLD[4], 2)

    # Abyssal flame rising from the censer (flares on wind-up and strike, gutters out on death)
    flame_scale = (1 - sm(max(0, (fall - .1) / .5))) if clip == 'die' else (1 + .35 * max(wu, st))
    if flame_scale > .15:
        fh = 10 * flame_scale
        fy = max(7, cy_c + 4)
        a.poly([(cx_c - 4.5, fy), (cx_c - 2, fy + fh * .7), (cx_c + 1, fy + fh),
                (cx_c + 4, fy + fh * .6), (cx_c + 4.5, fy)], PEARL[3], outline=OUTLINE)
        a.ball(cx_c, fy + 2, 3.5 * flame_scale, 3.5 * flame_scale, TEAL if st > .3 else VIOLET)
    if clip == 'attack' and st > .45:
        for k in range(3):
            fx = cx_c + 8 + k * 4.5
            fy = max(8, cy_c + (k - 1) * 6)
            a.ball(fx, fy, 3.2 - k * .3, 3.2 - k * .3, PEARL if k % 2 else VIOLET)
            spark(a, fx + 2, fy + 2, TEAL[4], 2)
    if clip == 'die' and .1 < fall < .85:
        for k in range(4):
            mx = -12 + k * 9 + (n % 2) * 2
            my = 10 + k * 5 + n * 3
            a.ellipse(mx, my, 2, 2, PEARL[3] if k % 2 else VIOLET[3])
    return a


# ----------------------------------------------------------------------------------------------
# 2. Vargast, Marshal of the Drowned Chains (`chainmarshal`): heavy dark-steel and gold plated juggernaut
#    strapped with crossed iron chains and a golden chest padlock, spiked pauldrons, horned great-helm with
#    open visor showing glossy eyes and blush, and a massive iron ship-anchor swung on a chain.
#    Attack: heaves the massive iron ship-anchor high above his horned helm, then hurls and slams it far
#    forward onto the floor with taut chain links and shockwave sparks before recovering.
#    Death: armoured legs buckle outward, the iron anchor and chains crash flat ahead, his horned helm tips
#    forward, and the chain-bound steel plate collapses into a low heap on the floor.
# ----------------------------------------------------------------------------------------------
def chainmarshal(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    a = Painter('chainmarshal', recoil + st * 4 - wu * 3)
    by = mix(32 + bob * .5 + wu * 2 - st * 2, 14, t)

    # Two heavy plated legs: at least one boot always rests on y=0 (ground row)
    for sg in (-1, 1):
        sw = math.sin(ph + (0 if sg > 0 else math.pi)) if clip == 'walk' else 0
        lift = max(0, sw) * 4.0 * (1 - t)
        fx = sg * 9 + sw * 4 + (st * 4 if sg > 0 else -wu * 2)
        if t > 0:
            fx = sg * (9 + t * 9)
            lift = 0
        hip = (sg * 7, by - 6)
        knee = (mix(hip[0], fx, .55) + sg * 2, max(6, by - 14 + lift * .4 - t * 4))
        ramp = PLATE[:4] if sg < 0 else PLATE
        a.limb([hip, knee, (fx, lift + 4)], ramp, 6)
        a.ball(knee[0], knee[1], 4.2, 4, GOLD)
        foot(a, fx, lift, 6.5, 4, ramp)

    # Far arm with manacle fist and hanging chain loop
    lh_x, lh_y = -20 - wu * 2, mix(by + 2, 5, t)
    a.limb([(-12, by + 12), (-17, by + 6), (lh_x, lh_y)], PLATE[:4], 5)
    a.ball(lh_x, lh_y, 4.5, 4.5, GOLD)
    chain_links(a, (lh_x, max(3, lh_y - 2)), (lh_x - 6, max(3, lh_y - 16 * (1 - t * .7))), sag=3 * (1 - t), count=4, ramp=PLATE, r=1.8)

    # Barrel steel cuirass, rust kilt, crossed chains and golden chest padlock
    a.poly([(-14, by - 2), (14, by - 2), (17 + t * 4, max(3, by - 13)), (-17 - t * 4, max(3, by - 13))],
           CRIMSON[1], outline=OUTLINE)
    a.ball(0, by + 6, 17, mix(15, 10, t), PLATE)
    if t > .4:
        foot(a, 0, 0, 11, 3, PLATE)
    a.line([(-13, by + 15), (13, max(4, by - 3))], BONE[2], 3)
    a.line([(13, by + 15), (-13, max(4, by - 3))], BONE[2], 3)
    a.ball(0, by + 6, 5, 5.5, GOLD)
    a.ellipse(0, by + 5, 1.5, 2, OUTLINE)

    # Spiked pauldrons
    for sg in (-1, 1):
        px, py = sg * 16, by + 15 * (1 - t * .3)
        a.ball(px, py, 7.5, 5.5, PLATE)
        for dx in (-3, 1, 4):
            a.poly([(px + dx - 2, py + 4), (px + dx + sg, py + 10 * (1 - t * .3)), (px + dx + 2, py + 4)],
                   GOLD[3], outline=OUTLINE)

    # Horned great-helm with open visor showing glossy eyes and blush
    hx = 2 + st * 2 - wu * 1 + t * 4
    hy = mix(by + 25, 16, t)
    a.ball(hx, hy, 13, 11.5, PLATE)
    for sg in (-1, 1):
        a.poly([(hx + sg * 8, hy + 6), (hx + sg * 16, hy + 16 * (1 - t * .3)), (hx + sg * 12, hy + 4)],
               GOLD[3], outline=OUTLINE)
    a.line([(hx - 10, hy + 6), (hx + 11, hy + 6)], GOLD[2], 2)
    a.face(hx + 2, hy - 1, clip, n, .78)

    # Right arm and massive iron ship-anchor on a chain (heaved high overhead clear of the face on wind-up, slammed far ahead on strike)
    rh_x = mix(mix(20, 21, wu), 26, st)
    rh_y = mix(mix(by + 6, by + 34, wu), by + 4, st)
    ax_c = mix(mix(26, 22, wu), 48, st)
    ay_c = mix(mix(18, by + 46, wu), 15, st)
    ang = mix(mix(0.0, .35, wu), 1.15, st)
    if clip == 'die':
        drop = sm(fall / .55)
        rh_x, rh_y = mix(20, 22, drop), mix(by + 6, 6, drop)
        ax_c, ay_c = mix(26, 38, drop), mix(18, 7, drop)
        ang = mix(0.0, 1.45, drop)
    a.limb([(13, by + 11), ((13 + rh_x) / 2 + 2, (by + 11 + rh_y) / 2), (rh_x, rh_y)], PLATE, 5)
    a.ball(rh_x, rh_y, 4.5, 4.5, GOLD)
    chain_links(a, (rh_x, rh_y), (ax_c, ay_c + 6), sag=mix(2.5, .4, max(wu, st)) * (1 - t), count=4, ramp=BONE, r=2.0)

    # Draw the ship anchor: shank, stock crossbar, crown and twin flukes
    d = (math.sin(ang), -math.cos(ang))
    nrm = (-d[1], d[0])
    top_a = (ax_c - d[0] * 8, max(4, ay_c - d[1] * 8))
    bot_a = (ax_c + d[0] * 9, max(4, ay_c + d[1] * 9))
    a.ball(top_a[0], top_a[1], 3.2, 3.2, GOLD)
    a.line([top_a, bot_a], PLATE[0], 5)
    a.line([top_a, bot_a], PLATE[3], 3)
    a.line([(top_a[0] - nrm[0] * 6, max(3, top_a[1] - nrm[1] * 6)),
            (top_a[0] + nrm[0] * 6, max(3, top_a[1] + nrm[1] * 6))], GOLD[2], 3)
    for sg in (-1, 1):
        fluke_mid = (bot_a[0] + nrm[0] * sg * 8 - d[0] * 2, max(4, bot_a[1] + nrm[1] * sg * 8 - d[1] * 2))
        fluke_tip = (bot_a[0] + nrm[0] * sg * 11 - d[0] * 7, max(4, bot_a[1] + nrm[1] * sg * 11 - d[1] * 7))
        taper(a, [bot_a, fluke_mid, fluke_tip], PLATE, 5, 2)
    if clip == 'attack' and st > .45:
        for k in range(4):
            spark(a, ax_c + 8 + k * 4, 5 + (k % 2) * 5 + (n - 3) * 2, TEAL[4] if k % 2 else GOLD[4], 3)
    return a


# ----------------------------------------------------------------------------------------------
# 3. Astrael, the Fallen Tide Seraph (`starseraph`): four broad feathered seraph wings (two pearl, two violet),
#    star-spangled lavender gown brushing the floor, pale lavender hair, crystal tear, broken golden halo,
#    and a radiant starlight orb.
#    Attack: spreads all four feathered wings high overhead and lifts the starlight orb, then sweeps wings and
#    hands forward to loose a blazing volley of golden shooting stars before recovering.
#    Death: her broken golden halo shatters to the floor, her four feathered wings fold and droop downward, and
#    she sinks peacefully into a pool of star-spangled cloth and feathers on the floor.
# ----------------------------------------------------------------------------------------------
def starseraph(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    sway = math.sin(ph) * 2 if clip == 'walk' else math.sin(n * math.pi / 3) * 1.2 if clip == 'idle' else 0
    flap = math.sin(n * math.pi / 3) * 4 if clip == 'idle' else math.sin(ph) * 5 if clip == 'walk' else 0
    a = Painter('starseraph', recoil + st * 4 - wu * 2)

    h = mix(1.0, .32, t)
    hw = round(mix(19, 29, t))
    top = 44 * h + bob * .4 * (1 - t)

    # Four feathered seraph wings behind the shoulders (curved angel wings: spread high on wind-up, sweep forward on strike, fold low on death)
    wing_lift = wu * 18 - st * 4 - t * 24
    wing_fwd = st * 10 - wu * 2
    for side in (-1, 1):
        for k in range(5):
            ang = math.radians(44 - k * 14) + (flap + wing_lift) * .018
            ln = (34 - k * 2.5) * mix(1.0, .65, t)
            bx, by_ = side * 7, 44 * h + 4
            tx = bx + side * math.cos(ang) * ln + (wing_fwd if side > 0 else -wing_fwd * .3)
            ty = max(4, by_ + math.sin(ang) * ln + wing_lift * .75 - k * 2.5)
            mx = mix(bx, tx, .52)
            my = max(5, mix(by_, ty, .52) + 8 * (1 - t * .5))
            taper(a, [(bx, by_), (mx, my), (tx, ty)], PEARL if k % 2 == 0 else VIOLET, 6, 2)

    # Star-spangled lavender gown with trailing ribbons resting on y=0
    a.poly([(-10 + sway * .3, top), (10 + sway * .3, top), (hw, 0), (-hw, 0)], VIOLET[2], outline=OUTLINE)
    a.poly([(-10 + sway * .3, top), (-1, top), (-2, 0), (-hw, 0)], VIOLET[1])
    a.line([(-hw + 1, 0), (hw - 1, 0)], OUTLINE, 1)
    a.line([(-hw + 2, 2), (hw - 2, 2)], GOLD[3], 2)
    for sx, sy in ((-5, 28), (5, 22), (-2, 12), (7, 9)):
        spark(a, sx + sway * .4, max(4, sy * h), GOLD[4], 2)

    # Bodice and golden sash
    a.ball(0, 36 * h + 2, 11, 10 * h + 1, VIOLET)
    a.line([(-10, 26 * h + 2), (10, 26 * h + 2)], GOLD[2], 2)
    a.ball(0, 26 * h + 2, 3, 3, PEARL)

    # Head, pale lavender hair, glossy eyes, blush, and crystal tear
    hx = mix(2, 8, t) + sway * .3
    hy = mix(56 + bob * .5 + wu * 2 - st * 1, 15, t)
    a.poly([(hx - 12, hy + 4), (hx - 19, max(4, hy - 14 * h)), (hx - 11, max(3, hy - 26 * h)), (hx - 3, max(4, hy - 10 * h))],
           PEARL[2], outline=OUTLINE)
    a.ball(hx, hy, 12, 11, PEARL)
    a.poly([(hx - 12, hy + 4), (hx - 7, hy + 11), (hx + 4, hy + 9), (hx + 12, hy + 9), (hx + 7, hy + 3)],
           VIOLET[3], outline=OUTLINE)
    a.face(hx + 1, hy - 1, clip, n, .76)
    a.ellipse(hx + 6, max(4, hy - 5), 1.5, 2.2, TEAL[4])

    # Broken golden star-halo (rises high on wind-up, shatters to the floor on death)
    halo_drop = sm(max(0, (fall - .15) / .65)) if clip == 'die' else 0
    for k in range(7):
        if k == 3:
            continue
        ha = math.radians(15 + k * 25)
        ox = mix(hx + math.cos(ha) * 14, -18 + k * 6, halo_drop)
        oy = mix(hy + 13 + math.sin(ha) * 5 + wu * 11, 3, halo_drop)
        a.ball(ox, max(3, oy), 2.2, 2.2, GOLD)

    # Hands and radiant starlight orb/volley (lifted high clear of the face on wind-up, swept far forward on strike)
    a.limb([(-8, 40 * h), (-15, 34 * h), (-17 - wu * 3, mix(30 + wu * 12, 5, t))], PEARL, 4)
    rh_x = mix(mix(18, 21, wu), 30, st)
    rh_y = mix(mix(34 + bob * .4, 66, wu), 38, st)
    if clip == 'die':
        rh_x, rh_y = mix(18, 22, t), mix(34, 5, t)
    a.limb([(9, 40 * h), ((9 + rh_x) / 2 + 2, (40 * h + rh_y) / 2), (rh_x, rh_y)], PEARL, 4)
    orb_x = mix(mix(23, 24, wu), 45, st)
    orb_y = mix(mix(38 + bob * .5, 82, wu), 40, st)
    if clip == 'die':
        orb_x, orb_y = mix(23, 28, t), mix(38, 4, t)
    if t < .75:
        r_orb = 5.5 * (1 - t * .6)
        a.ball(orb_x, max(5, orb_y), r_orb, r_orb, GOLD if st > .3 else PEARL)
        spark(a, orb_x, max(6, orb_y), WHITE, 4)
    if clip == 'attack' and st > .4:
        for k in range(3):
            sx = orb_x + 7 + k * 5
            sy = max(8, orb_y + (k - 1) * 7)
            a.ball(sx, sy, 3.2 - k * .3, 3.2 - k * .3, GOLD if k % 2 == 0 else PEARL)
            spark(a, sx + 2, sy, WHITE, 3)
    return a


# ----------------------------------------------------------------------------------------------
# 4. The Blind Tide Judicator (`tidejudicator`): monumental parchment-and-slate robed judge with gold-bordered
#    vestments on y=0, golden judicial crown, pale silk blindfold band across the brow with trailing knot and
#    stern glossy eyes + blush gleaming beneath, golden Balance Scales of the Tide in his left hand, and a
#    massive iron-and-gold Gavel in his right hand.
#    Attack: raises the massive iron-and-gold gavel high overhead as the scales flare, then brings the gavel
#    crashing down far ahead with a golden verdict shockwave before recovering.
#    Death: the balance scales tip and spill onto the floor to the left, the heavy gavel drops flat ahead, the
#    golden crown slips askew, and the monumental judicial robes collapse low on the floor.
# ----------------------------------------------------------------------------------------------
def tidejudicator(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    sway = math.sin(ph) * 1.8 if clip == 'walk' else math.sin(n * math.pi / 3) * .8 if clip == 'idle' else 0
    a = Painter('tidejudicator', recoil + st * 4 - wu * 2)

    h = mix(1.0, .33, t)
    hw = round(mix(21, 30, t))
    top = 46 * h + bob * .4 * (1 - t)

    # Monumental parchment-and-slate judicial robe resting on y=0
    a.poly([(-11 + sway * .3, top), (11 + sway * .3, top), (hw, 0), (-hw, 0)], BONE[2], outline=OUTLINE)
    a.poly([(-11 + sway * .3, top), (-1, top), (-2, 0), (-hw, 0)], BONE[1])
    a.poly([(-4, top), (4, top), (5, 0), (-5, 0)], GOLD[2], outline=OUTLINE)
    a.line([(-hw + 1, 0), (hw - 1, 0)], OUTLINE, 1)
    a.line([(-hw + 2, 3), (hw - 2, 3)], GOLD[3], 2)

    # Upper mantle and golden judicial collar
    a.ball(0, 38 * h + 2, 13, 11 * h + 1, BONE)
    a.poly([(-13, 44 * h + 2), (13, 44 * h + 2), (9, 34 * h + 2), (-9, 34 * h + 2)], GOLD[2], outline=OUTLINE)
    a.ball(0, 39 * h + 2, 3.5, 3.5, TEAL)

    # Left arm holding the golden Balance Scales of the Tide (spills to the floor on death)
    sc_x = mix(-20 - wu * 2, -25, t)
    sc_y = mix(38 + bob * .4 + wu * 5, 11, t)
    a.limb([(-11, 41 * h), (-16, 39 * h), (sc_x, max(4, sc_y))], BONE[:4], 4)
    a.ball(sc_x, max(4, sc_y), 3.4, 3.4, PEARL)
    tilt = (math.sin(n * math.pi / 3) * 2.2 if clip == 'idle' else math.sin(ph) * 2.5 if clip == 'walk' else wu * 3 - st * 3) * (1 - t)
    a.line([(sc_x - 9, max(4, sc_y + 6 + tilt)), (sc_x + 9, max(4, sc_y + 6 - tilt))], GOLD[3], 2)
    for sgn, tl in ((-1, tilt), (1, -tilt)):
        px = sc_x + sgn * 8
        py = max(10, sc_y + 6 + tl)
        pan_y = max(3, py - 8 * (1 - t * .6))
        a.line([(px, py), (px - 3, pan_y), (px + 3, pan_y), (px, py)], GOLD[1], 1)
        a.ball(px, pan_y, 4.5, 2.2, GOLD)

    # Stern head, brow blindfold band with trailing knot, glossy eyes + blush, and golden judicial crown
    hx = mix(2, 9, t) + sway * .3
    hy = mix(57 + bob * .5 + wu * 2 - st * 1, 15, t)
    a.ball(hx, hy, 12.5, 11, PEARL)
    a.face(hx + 2, hy - 2, clip, n, .76)
    # Pale silk blindfold band worn across the brow/upper bridge with trailing knot
    a.poly([(hx - 13, hy + 3), (hx + 13, hy + 3), (hx + 13, hy + 8), (hx - 13, hy + 8)], PEARL[4], outline=OUTLINE)
    a.poly([(hx - 12, hy + 6), (hx - 21, hy + 3 + sway * .5), (hx - 17, hy - 2)], PEARL[3], outline=OUTLINE)
    a.ball(hx + 3, hy + 5.5, 2.6, 2.6, GOLD)
    # Golden judicial crown (slips to the floor on death)
    c_drop = sm(max(0, (fall - .2) / .65)) if clip == 'die' else 0
    cx_c, cy_c = mix(hx, -14, c_drop), mix(hy + 9, 4, c_drop)
    a.poly([(cx_c - 10, cy_c), (cx_c + 10, cy_c), (cx_c + 8, cy_c + 9 * (1 - c_drop * .3)),
            (cx_c, cy_c + 12 * (1 - c_drop * .3)), (cx_c - 8, cy_c + 9 * (1 - c_drop * .3))],
           GOLD[2], outline=OUTLINE)

    # Right arm and massive iron-and-gold Gavel (raised high overhead clear of the face on wind-up, slammed far ahead on strike)
    rh_x = mix(mix(19, 21, wu), 28, st)
    rh_y = mix(mix(36 + bob * .4, 68, wu), 20, st)
    ang = mix(mix(.35, .08, wu), 1.48, st)
    if clip == 'die':
        drop = sm(fall / .55)
        rh_x, rh_y = mix(19, 23, drop), mix(36, 5, drop)
        ang = mix(.35, 1.54, drop)
    if clip != 'die' or fall < .4:
        a.limb([(11, 41 * h), ((11 + rh_x) / 2 + 2, (41 * h + rh_y) / 2), (rh_x, rh_y)], BONE, 4)
        a.ball(rh_x, rh_y, 3.5, 3.5, PEARL)
    d = (math.sin(ang), math.cos(ang))
    nrm = (-d[1], d[0])
    shaft_base = (rh_x - d[0] * 6, max(3, rh_y - d[1] * 6))
    head_c = (rh_x + d[0] * 18, max(7, rh_y + d[1] * 18))
    a.line([shaft_base, head_c], GOLD[0], 4)
    a.line([shaft_base, head_c], GOLD[3], 2)
    for sg in (-1, 1):
        gx = head_c[0] + nrm[0] * sg * 6
        gy = max(6, head_c[1] + nrm[1] * sg * 6)
        a.ball(gx, gy, 6.5, 5.5, PLATE)
        a.ball(gx, gy, 3.5, 3.0, GOLD)
    a.ball(head_c[0], head_c[1], 5.5, 5.5, GOLD)
    if clip == 'attack' and st > .45:
        for k in range(4):
            spark(a, head_c[0] + 10 + k * 4, 6 + (k % 2) * 5 + (n - 3) * 2, GOLD[4] if k % 2 == 0 else TEAL[4], 3)
    return a


# ----------------------------------------------------------------------------------------------
# 5. High Hierophant Vael, Heart of the Tide (`hierophant`): grand royal-violet and gold cathedral vestments
#    on y=0 with golden orphrey band, glowing cyan Tide-Heart gem on his chest, flowing silver-white beard,
#    tall ceremonial gold-and-violet papal mitre with cross, glossy eyes + blush, and a tall golden Crosier
#    Staff topped with a swirling Tide Orb.
#    Attack: hoists the golden Tide-Orb crosier high above his mitre with a cresting tidal halo, then sweeps
#    it far forward unleashing a surging torrent of cyan tide orbs and cathedral sparks before recovering.
#    Death: the Tide-Heart gem cracks and dims, the golden crosier clatters flat ahead, the tall mitre tumbles
#    off beside him, and his grand violet vestments crumple into a sunken mantle on the floor.
# ----------------------------------------------------------------------------------------------
def hierophant(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    sway = math.sin(ph) * 2.0 if clip == 'walk' else math.sin(n * math.pi / 3) * 1.0 if clip == 'idle' else 0
    a = Painter('hierophant', recoil + st * 4 - wu * 2)

    h = mix(1.0, .33, t)
    hw = round(mix(22, 31, t))
    top = 46 * h + bob * .4 * (1 - t)

    # Grand royal-violet cathedral vestments with golden orphrey resting on y=0
    a.poly([(-12 + sway * .3, top), (12 + sway * .3, top), (hw, 0), (-hw, 0)], VIOLET[2], outline=OUTLINE)
    a.poly([(-12 + sway * .3, top), (-1, top), (-2, 0), (-hw, 0)], VIOLET[1])
    a.poly([(-4, top), (4, top), (5, 0), (-5, 0)], GOLD[2], outline=OUTLINE)
    a.line([(-hw + 1, 0), (hw - 1, 0)], OUTLINE, 1)
    a.line([(-hw + 2, 3), (hw - 2, 3)], GOLD[3], 2)
    for k in range(-4, 5):
        a.ball(k * hw / 4.8, 3, 2, 2, TEAL if k % 2 == 0 else PEARL)

    # Mantle and glowing cyan Tide-Heart gem on the chest (cracks and dims on death)
    a.ball(0, 38 * h + 2, 13, 11 * h + 1, VIOLET)
    a.poly([(-14, 45 * h + 2), (14, 45 * h + 2), (11, 36 * h + 2), (-11, 36 * h + 2)], GOLD[2], outline=OUTLINE)
    a.ball(0, 33 * h + 2, 5.5, 5.5, TEAL if t < .55 else PLATE)
    if t < .55:
        a.ellipse(-1.5, 33 * h + 3.5, 2, 2, WHITE)
    else:
        a.line([(-3, 33 * h + 5), (2, 33 * h + 2), (-2, 33 * h - 2)], OUTLINE, 2)

    # Far arm raised in benediction
    lh_x = -18 - wu * 3 + st * 2
    lh_y = mix(36 + wu * 8, 5, t)
    a.limb([(-11, 42 * h), (-15, 38 * h), (lh_x, lh_y)], VIOLET, 4)
    a.ball(lh_x, lh_y, 3.5, 3.5, PEARL)

    # Head, flowing silver-white beard below the chin, glossy eyes and blush
    hx = mix(2, 9, t) + sway * .3
    hy = mix(56 + bob * .5 + wu * 2 - st * 1, 15, t)
    a.ball(hx, hy, 12, 11, BONE)
    by_top = max(5, hy - 8)
    by_tip = max(3, hy - 22 * (1 - t * .5))
    a.poly([(hx - 8, by_top), (hx + 9, by_top), (hx + 7, max(3, (by_top + by_tip) / 2)),
            (hx + 1 + sway * .3, by_tip), (hx - 6, max(3, (by_top + by_tip) / 2))],
           PEARL[3], outline=OUTLINE)
    a.face(hx + 2, hy + 1, clip, n, .76)

    # Tall ceremonial gold-and-violet papal mitre (tumbles off beside him on death)
    m_drop = sm(max(0, (fall - .18) / .65)) if clip == 'die' else 0
    mx = mix(hx, -19, m_drop)
    my = mix(hy + 9, 3, m_drop)
    mh = 18 * (1 - m_drop * .35)
    a.poly([(mx - 10, my), (mx + 10, my), (mx + 8, my + mh * .6), (mx, my + mh), (mx - 8, my + mh * .6)],
           VIOLET[3], outline=OUTLINE)
    a.poly([(mx - 6, my + 1), (mx + 6, my + 1), (mx + 5, my + mh * .55), (mx, my + mh - 2), (mx - 5, my + mh * .55)],
           GOLD[3])
    a.line([(mx, my + 3), (mx, my + mh - 3)], GOLD[0], 2)
    a.line([(mx - 3, my + mh * .5), (mx + 3, my + mh * .5)], GOLD[0], 2)

    # Right arm and golden Tide-Orb Crosier (hoisted high above mitre clear of the face on wind-up, swept far forward on strike)
    rh_x = mix(mix(20, 22, wu), 30, st)
    rh_y = mix(mix(34 + bob * .4, 68, wu), 36, st)
    ang = mix(mix(.12, .02, wu), 1.25, st)
    if clip == 'die':
        drop = sm(fall / .55)
        rh_x, rh_y = mix(20, 25, drop), mix(34, 5, drop)
        ang = mix(.12, 1.53, drop)
    if clip != 'die' or fall < .4:
        a.limb([(11, 42 * h), ((11 + rh_x) / 2 + 2, (42 * h + rh_y) / 2), (rh_x, rh_y)], VIOLET, 4)
        a.ball((11 + rh_x) / 2 + 2, (42 * h + rh_y) / 2, 4, 3.5, GOLD)
    d = (math.sin(ang), math.cos(ang))
    base = (rh_x - d[0] * 12, max(3, rh_y - d[1] * 12))
    tip = (rh_x + d[0] * 22, max(7, rh_y + d[1] * 22))
    a.line([base, tip], GOLD[0], 4)
    a.line([base, tip], GOLD[3], 2)
    a.ball(tip[0], tip[1], 7, 7, TEAL if t < .65 else PLATE)
    a.ball(tip[0], tip[1], 4, 4, PEARL if t < .65 else PLATE[:4])
    if t < .65:
        a.ellipse(tip[0] - 2, tip[1] + 2, 2, 2, WHITE)
    if clip != 'die' or fall < .4:
        a.ball(rh_x, rh_y, 3.5, 3.5, BONE)
    if clip == 'attack' and st > .45:
        for k in range(3):
            wx = tip[0] + 7 + k * 5
            wy = max(8, tip[1] + (k - 1) * 7)
            a.ball(wx, wy, 3.5 - k * .3, 3.5 - k * .3, TEAL if k % 2 == 0 else PEARL)
            spark(a, wx + 2, wy + 2, GOLD[4], 3)
    return a


DRAW = dict(
    abysszealot=abysszealot,
    chainmarshal=chainmarshal,
    starseraph=starseraph,
    tidejudicator=tidejudicator,
    hierophant=hierophant,
)


def frame(kind, clip, n):
    kw, kh, _, _ = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    if os.environ.get('NAVE_LOOSE'):
        ys, xs = np.nonzero(grid)
        if not grid.any() or min(xs.min(), ys.min()) <= 0 or xs.max() >= kw - 1 or ys.max() >= kh - 1:
            print('BOUNDS', kind, clip, n, (xs.min(), ys.min(), xs.max(), ys.max()) if grid.any() else 'empty')
        return grid
    assert grid.any(), (kind, clip, n, 'empty')
    assert not (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()), (kind, clip, n, 'border')
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def extents():
    """Measure bounds, ground row contact, leg runs, and attack wind-up/strike/recovery for all five kinds."""
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        data = frames(kind)
        lows = set()
        for clip, grids in data.items():
            for n, g in enumerate(grids):
                ys, xs = np.nonzero(g)
                lows.add(int(ys.max()))
        idle = data['idle']
        att = data['attack']
        die = data['die']
        idle_top = min(int(np.nonzero(g)[0].min()) for g in idle)
        idle_right = max(int(np.nonzero(g)[1].max()) for g in idle)
        idle0_ys, idle0_xs = np.nonzero(idle[0])
        att2_ys, att2_xs = np.nonzero(att[2])
        att4_ys, att4_xs = np.nonzero(att[4])
        att7_ys, att7_xs = np.nonzero(att[7])
        rises = idle_top - int(att2_ys.min())
        reach = int(att4_xs.max()) - idle_right
        rec = (int(att7_ys.min()) - int(idle0_ys.min()),
               int(att7_xs.min()) - int(idle0_xs.min()),
               int(att7_xs.max()) - int(idle0_xs.max()))

        def runs_at(g, y):
            row = g[y] > 0
            r, prev = 0, False
            for v in row:
                if v and not prev:
                    r += 1
                prev = bool(v)
            return r

        idle_gr = [runs_at(g, kay) for g in idle]
        walk_gr = [runs_at(g, kay) for g in data['walk']]
        att_hashes = len({g.tobytes() for g in att})
        die_hashes = len({g.tobytes() for g in die})
        whites = int((idle[0] == EYE_WHITE).sum())
        print(f'{kind:15s} frame={kw}x{kh} ay={kay} lows={sorted(lows)} rises={rises} reach={reach} '
              f'rec={rec} att={att_hashes}/8 die={die_hashes}/8 whites={whites} idleGR={idle_gr} walkGR={walk_gr}')


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    existing = {sp['name']: sp['sprite_id'] for sp in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        kw, kh, _, _ = kind_frame(kind)
        name = PREFIX + kind + '_all'
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/nave_slime_{kind}_raw.npz', **data[kind])
        sid = old.api('create', dict(
            name=name, width=kw, height=kh, frames=34, layers=1, fps=10,
            palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]
        ))['sprite_id']
        print('Created native source', kind, sid, f'{kw}x{kh}', flush=True)
        offset = 0
        for clip, grids in data[kind].items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=sid, frame=offset + n,
                                     ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, offset, 'frames saved', flush=True)


def refresh():
    """Rewrite the frames of the named kinds' existing saved sources from the drawers."""
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = json.loads(REGISTRY.read_text())
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/nave_slime_{kind}_raw.npz', **data)
        offset = 0
        for clip, grids in data.items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=saved[kind], frame=offset + n,
                                     ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        print('Refreshed', kind, saved[kind], offset, 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    """Replace the five Grand Nave atlases and ONLY their `sprites`/`tops`/`kindFrames` entries in cathedral.txt."""
    saved = json.loads(REGISTRY.read_text())
    assert set(saved) == set(KINDS)
    meta = json.loads(MANIFEST.read_text())
    before = json.loads(MANIFEST.read_text())
    proof, atlases, tops = {}, {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset = 0
        rows = []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip] == dict(fps=fps, n=count, row=row, editorStart=offset), 'clip layout changed'
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        tops[kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frame=[kw, kh, kax, kay], frames=rows)
    meta = kindframe.merge_kind_entries(meta, KINDS, saved, tops, {k: kind_frame(k) for k in KINDS if k in KIND_FRAMES})
    for key in meta:
        if key in ('sprites', 'tops', 'kindFrames'):
            assert {k: v for k, v in (meta.get(key) or {}).items() if k not in KINDS} == \
                   {k: v for k, v in (before.get(key) or {}).items() if k not in KINDS}
            if key != 'kindFrames':
                assert list(meta[key]) == list(before[key]), 'key order changed'
        else:
            assert meta[key] == before[key], key
    for kind, atlas in atlases.items():
        dest = ASSETS / f'cathedral_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 170 saved PixelFlow frames; shared cathedral.txt changed only for', ', '.join(KINDS), flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames."""
    meta = json.loads(MANIFEST.read_text())
    saved = json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'cathedral_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh),
                                              sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def preview():
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    for kind in only:
        kw, kh, kax, kay = kind_frame(kind)
        data = frames(kind)
        sheet = Image.new('RGB', (8 * kw * 2, 5 * (kh * 2 + 24)), '#241e38')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((kw * 2, kh * 2), Image.Resampling.NEAREST)
                x, y = n * kw * 2, row * (kh * 2 + 24)
                sheet.paste(im, (x, y), im)
                sd.line([(x, y + kay * 2 + 1), (x + kw * 2, y + kay * 2 + 1)], fill='#e8a0e0')
                sd.text((x + 6, y + kh * 2 + 2), f'{kind} {clip} {n}', fill='white')
        sheet.save(OUT / f'preview-{kind}.png')
    print('Wrote previews to', OUT)


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1]]()
