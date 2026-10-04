#!/usr/bin/env python3
"""makesprites workflow for the Bifrost Reach monsters: preview | build [--replace] | export | verify | view.

Five kinds share the Emberfall Crags contract (scripts/make_crag_sprites.py): one 96x96 frame, a foot anchor at (48, 90),
right-facing art (the game mirrors it) and five clips (idle 6, walk 8, attack 8, hurt 4, die 8) so client/field.js drives them
with the Ironhide's state machine: walk frames 2-4 are the hop, 5-7 the landing, attack 0-2 the windup, 3-5 the lunge, 6-7 the
recovery.

  galehound   Galehound       (L30)  a lean wolf of wind-torn cloud with lightning in its veins; a very fast charge
  prismgolem  Prism Golem     (L31)  a hunched brute of broken Bifrost crystal, rainbow caught in every facet; slams
  skyray      Skyray          (L32)  a manta of storm cloud that hovers and spits lightning
  einherjar   Hollow Einherjar (L33) a dead hero in rusted mail with a round shield and a notched sword, a cold fire in the helm
  thunderroc  Thunderroc      (L35)  a huge storm eagle that dives with lightning crackling along its wings

The two rigs of make_wyrd_sprites.py (a side-on quadruped and a hunched biped) carry the galehound, the golem and the einherjar;
the ray and the roc are bespoke. `build` saves ONE new 34-frame PixelFlow sprite per kind (valhallasc_sky_<kind>_all) and
refuses existing names unless --replace is given (it discards editor edits). `export` reads the editor frames back, so edits
survive, and writes client/assets/sky_<kind>.png plus sky.txt.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_crag_sprites as mc  # noqa: E402
from make_crag_sprites import (AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid,  # noqa: E402
                               gradient, lerp, polygon, rgba, rng_for, rotate)
from make_wyrd_sprites import (biped_gait, bolt_path, chain_paint, draw_biped, draw_quad, dust, eye_dead, eyes_on, fit,  # noqa: E402
                               ik, quad_gait, smooth, thread)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
PREFIX = 'valhallasc_sky_'
KINDS = ['galehound', 'prismgolem', 'skyray', 'einherjar', 'thunderroc']
RAW = ROOT / 'scripts'


def zigzag(f, rng, a, b, name, jag=2., steps=4, width=1):
    pts = bolt_path(rng, a, b, jag, steps)
    for u, v in zip(pts, pts[1:]):
        f.line(u, v, name, width)
    return pts


# ----------------------------------------------------------------------------------------------
# Galehound: a lean wolf of wind-torn cloud. Pale fur, a slate underbelly, lightning in the veins, a tail that is mostly weather.
# ----------------------------------------------------------------------------------------------
GALE = Palette({
    'fur0': '#2a3550', 'fur1': '#46567a', 'fur2': '#7088b0', 'fur3': '#a6bad8', 'fur4': '#d4e2f2', 'fur5': '#f6fbff',
    'far0': '#1a2238', 'far1': '#2c3856', 'far2': '#445479', 'bel0': '#5a6a90', 'bel1': '#8294b8', 'bel2': '#b4c4de',
    'zap0': '#2a73d6', 'zap1': '#5fc4ff', 'zap2': '#b8f0ff', 'zap3': '#f4fdff', 'fang': '#fffbe8', 'fang0': '#b8b090',
    'eye': '#fff27a', 'eye2': '#ffffff', 'socket': '#0a0e1c', 'mouth': '#3a1424', 'tongue': '#d8506a', 'nostril': '#10142a',
    'hoof': '#161c30', 'hoof2': '#2c3652', 'wisp2': '#e4eefa',
})


def galehound(clip, n):
    f = Frame(GALE)
    p = GALE
    g = quad_gait(clip, n)
    rng = rng_for('galehound', clip, n)
    glow = g['glow']

    def tail(c):
        # a long tail of drifting cloud: a chain of discs that thins out
        tb = c.at(-19, -4)
        lag = g['tail'] * 5
        pts = smooth([tb, (tb[0] - 7, tb[1] - 4 - lag), (tb[0] - 13, tb[1] - 11 - lag * 1.4 + math.sin(n * 1.1) * 2), (tb[0] - 15, tb[1] - 19 - lag * .6 + math.cos(n * 1.3) * 2)], 12)
        discs = []
        for i, (x, y) in enumerate(pts):
            r = lerp(5.4, 2.0, i / (len(pts) - 1))
            discs.append(ellipsoid(x, y, r, r * .85))
        union = np.zeros((H, W), bool)
        for sh in discs:
            union |= sh[0]
        f.a[mc.dilate(union) & ~union] = p['ol']
        for i, sh in enumerate(discs):
            f.paint(sh, p.ramp('fur2', 'fur3', 'fur4', 'wisp2'), outline=False, dither=.5)

    def deco_back(c):
        # wind-swept ridge of fur, all combed backwards
        for sweep in (0, 1):
            for k in range(8):
                t = k / 7
                sx, sy = c.at(lerp(-16, 12, t), lerp(-10, -12, math.sin(t * math.pi * .9)))
                h = 5 + 2.2 * math.sin(t * math.pi) + (k % 2)
                lean = 3.5 + g['shake'] * (1 if k % 2 else -1)
                tri = polygon([(sx - 2, sy + 1), (sx - lean, sy - h), (sx + 2.5, sy + 1)])
                if sweep == 0:
                    f.a[mc.dilate(tri) & ~tri] = p['ol']
                else:
                    f.a[tri] = p['fur4' if k % 2 else 'fur3']
        # lightning in the veins along the flank
        a = c.at(-8, 0)
        for _ in range(1 + int(glow > 1.2)):
            b = (a[0] + 11, a[1] + rng.uniform(-3, 4))
            pts = bolt_path(rng, a, b, 1.5, 4)
            for u, v in zip(pts, pts[1:]):
                f.line(u, v, 'zap1' if glow < 1.3 else 'zap2', 1)

    def head(c):
        lie = g['lie']
        hx0, hy0 = c.at(19, -4)
        head_c = (hx0 + 3 + g['hx'], hy0 + 1 + g['hy'] + lie * 2)
        ht = .25 + g['ht']
        neck = capsule(c.at(11, -3), head_c, 8.2, 6.6)
        skull = ellipsoid(head_c[0] + 1, head_c[1], 8.2, 7, ht)
        snout_c = (head_c[0] + 9.5 * math.cos(ht), head_c[1] + 9.5 * math.sin(ht) + 1.5)
        snout = ellipsoid(snout_c[0], snout_c[1], 7.6, 3.8, ht)
        jaw_c = (head_c[0] + 7 * math.cos(ht) - g['jaw'], head_c[1] + 5.6 + g['jaw'] * 4.2)
        jaw = ellipsoid(jaw_c[0] + 2, jaw_c[1], 7.4, 2.6, ht * .6 + g['jaw'] * .35)
        if g['jaw'] > .1:
            mouth = ellipsoid(snout_c[0] - 1, snout_c[1] + 2.8 + g['jaw'] * 1.5, 6.4, 1.6 + g['jaw'] * 2.2, ht)
            f.flat(mouth[0], 'mouth', outline=True)
            f.flat(ellipsoid(snout_c[0], snout_c[1] + 3.8 + g['jaw'] * 2, 3, 1.2)[0], 'tongue')
        # two ears, then the head over their roots
        for ox, tilt_ in ((-3, -.1), (3, .15)):
            ear = polygon([(head_c[0] + ox - 3, head_c[1] - 5), (head_c[0] + ox - 2 + tilt_ * 6 - g['shake'] * 2, head_c[1] - 15), (head_c[0] + ox + 3, head_c[1] - 5)])
            f.a[mc.dilate(ear) & ~ear] = p['ol']
            f.a[ear] = p['fur2' if ox < 0 else 'fur3']
        chain_paint(f, [neck, skull], p.ramp('fur0', 'fur1', 'fur2', 'fur3', 'fur4'), dither=.5)
        f.paint(jaw, p.ramp('far1', 'fur1', 'fur2', 'fur3'), outline=True, dither=.4)
        f.paint(snout, p.ramp('fur1', 'fur2', 'fur4', 'fur5'), outline=True, dither=.4)
        f.dots([(snout_c[0] + 7, snout_c[1] - 1), (snout_c[0] + 7, snout_c[1])], 'nostril')
        if g['jaw'] > .1 or clip == 'attack':
            for fx_ in (snout_c[0] - 2, snout_c[0] + 3):
                f.line((fx_, snout_c[1] + 2.4), (fx_ + .5, snout_c[1] + 5 + g['jaw'] * 2), 'fang', 1)
        eyes_on(f, g, head_c[0] + 4, head_c[1] - 2, 'eye', brow='fur0', size=2.4)

    return draw_quad(f, p, g, dict(
        height=30, leg=(12, 12), thick=.85, barrel=(19, 11), rump=(13, 11), hump=(10, -4, 10, 9), feet=[-10, 13, -4, 18],
        body=['fur0', 'fur1', 'fur2', 'fur3', 'fur4', 'fur5'], belly=['bel0', 'bel1', 'bel2'], far=['far0', 'far1', 'far2'],
        near=['fur0', 'fur1', 'fur2', 'fur3', 'fur4'], hoof=['hoof', 'hoof2'], tail=tail, deco_back=deco_back, deco_front=lambda c: None, head=head))


# ----------------------------------------------------------------------------------------------
# Prism Golem: a piece of the broken Bifrost that walks. Pale crystal with rainbow caught in every facet.
# ----------------------------------------------------------------------------------------------
PRISM = Palette({
    'cr0': '#2a2a5e', 'cr1': '#4a4a9a', 'cr2': '#7a80c8', 'cr3': '#a8b4e8', 'cr4': '#d4e0fa', 'cr5': '#f6faff',
    'far0': '#1c1c42', 'far1': '#303470', 'far2': '#4c54a0', 'bel0': '#8a96d0', 'bel1': '#b4c0ec', 'bel2': '#e0eafc',
    'rr': '#ff4a6a', 'ro': '#ff9a3a', 'ry': '#ffe45a', 'rg': '#4aeaa0', 'rb': '#4ab8ff', 'rv': '#b46aff',
    'core0': '#7a2aa0', 'core1': '#e064ff', 'core2': '#ffd8ff', 'eye': '#ffffff', 'socket': '#10102a', 'mouth': '#1a1038',
    'dust': '#b8c0e8', 'nail': '#f0f6ff', 'shard': '#cfe0ff',
})
RAINBOW = ['rr', 'ro', 'ry', 'rg', 'rb', 'rv']


def prismgolem(clip, n):
    f = Frame(PRISM)
    p = PRISM
    rng = rng_for('prismgolem', clip, n)
    g = biped_gait(clip, n)
    glow = g['glow']
    HEAD_AT = (13, -27)

    def facet(points, tone, edge='cr0'):
        poly = polygon(points)
        f.a[mc.dilate(poly) & ~poly] = p['ol']
        f.a[poly] = p[tone]

    def back(c):
        # crystal spines on the back of the shoulders
        for k, (ox, oy, h) in enumerate([(-9, -22, 14), (-4, -26, 17), (2, -28, 13)]):
            x, y = c.at(ox, oy)
            facet([(x - 3, y + 6), (x + 1 - g['sway'], y - h), (x + 4, y + 6)], 'cr2' if k % 2 else 'cr1')
            f.line((x + 1, y + 4), (x + 1 - g['sway'], y - h + 3), 'cr4', 1)
            f.dots([(x + 1 - g['sway'], y - h + 1)], RAINBOW[(k * 2 + n // 2) % 6])

    def deco_torso(c):
        # facets across the chest: slabs with a rainbow edge and a glowing core
        for k, (ox, oy, w, h, tone) in enumerate([(-6, -14, 8, 9, 'rb'), (4, -17, 9, 9, 'cr3'), (-1, -6, 8, 8, 'rv'), (8, -8, 6, 7, 'cr2')]):
            x, y = c.at(ox, oy)
            poly = polygon([(x - w / 2, y - h * .2), (x, y - h / 2), (x + w / 2, y - h * .1), (x + w * .3, y + h / 2), (x - w * .4, y + h / 2)])
            f.a[mc.dilate(poly) & ~poly] = p['ol']
            f.a[poly] = p[tone]
            f.line((x - w / 2, y - h * .2), (x, y - h / 2), 'cr5', 1)
            f.line((x, y - h / 2), (x + w / 2, y - h * .1), RAINBOW[(k + n // 3) % 6], 1)
        core = c.at(3, -8)
        f.flat(ellipsoid(core[0], core[1], 3.4 * glow, 3.8 * glow)[0], 'core1', outline=True, edge='core0')
        f.dots([core], 'core2')
        # rainbow caught in the cracks
        for k in range(3):
            a = c.at(-8 + k * 8, -4 + (k % 2) * 6)
            f.dots([a, (a[0] + 1, a[1] + 1)], RAINBOW[(k * 2 + n) % 6])

    def head(c):
        hx, hy = c.at(HEAD_AT[0], HEAD_AT[1])
        hx += g['hx']
        hy += g['hy'] + g['lie'] * 2
        skull = ellipsoid(hx, hy, 8.4, 7.6, c.ang * .5)
        jaw = ellipsoid(hx + 3, hy + 5.4 + g['jaw'] * 3, 6.6, 3.2, c.ang * .3)
        neck = capsule(c.at(HEAD_AT[0] - 6, HEAD_AT[1] + 6), (hx, hy), 6.4, 5.6)
        if g['jaw'] > .1:
            f.flat(ellipsoid(hx + 4, hy + 5.6 + g['jaw'] * 2, 5.6, 1.4 + g['jaw'] * 2)[0], 'mouth', outline=True)
        # a crown of three crystal horns
        for k, (ox, h) in enumerate([(-4, 13), (0, 17), (5, 12)]):
            facet([(hx + ox - 3, hy - 5), (hx + ox + 1 - g['sway'] * .5, hy - 5 - h), (hx + ox + 3, hy - 5)], 'cr3' if k == 1 else 'cr2')
        chain_paint(f, [neck, skull], p.ramp('cr0', 'cr1', 'cr2', 'cr3', 'cr4'), dither=.5)
        f.paint(jaw, p.ramp('cr0', 'cr1', 'cr2', 'cr3'), outline=True, dither=.4)
        eyes_on(f, g, hx + 4, hy - 1, 'eye', brow=None, size=2.4)

    def hand(c, near, far):
        for (hx, hy), ramp in ((far, p.ramp('far0', 'far1', 'far2')), (near, p.ramp('cr0', 'cr1', 'cr2', 'cr3', 'cr4'))):
            fist = ellipsoid(hx, hy, 6.2, 5.4)
            f.paint(fist, ramp, dither=.4)
            f.dots([(hx + 3, hy + 3), (hx + 4, hy - 1), (hx - 2, hy + 3)], 'nail')
            for k in range(3):
                x0 = hx - 3 + k * 3
                facet([(x0 - 1.5, hy - 3), (x0 + .5, hy - 8 - (k % 2) * 2), (x0 + 2, hy - 3)], 'cr3')

    def after(c, near, far):
        if g['slam'] > 0:
            x = max(near[0], far[0])
            dust(f, rng, x, g['slam'], 'dust')
            for k in range(-3, 4):
                f.dots([(x + k * 4, AY - 2 - abs(k) % 2 * 2)], RAINBOW[(k + 3) % 6])

    return draw_biped(f, p, g, dict(
        leg_h=27, leg=(14.5, 14.5), thick=1.05, arm=(16, 16), arm_r=(5.4, 4.5, 3.8), shoulder=(8, -19), torso=(14, 16), torso_at=(3, -13), torso_tilt=.25,
        pelvis=(10.5, 8), head_at=(13, -27),
        body=['cr0', 'cr1', 'cr2', 'cr3', 'cr4', 'cr5'], far=['far0', 'far1', 'far2'], near=['cr0', 'cr1', 'cr2', 'cr3', 'cr4'],
        back=back, deco_torso=deco_torso, head=head, hand=hand, after=after))


# ----------------------------------------------------------------------------------------------
# Hollow Einherjar: a dead hero who never reached Valhalla. Rusted mail, a round shield, a notched sword, cold blue fire in the helm.
# ----------------------------------------------------------------------------------------------
EINH = Palette({
    'mail0': '#1a1e26', 'mail1': '#2c323e', 'mail2': '#464e5e', 'mail3': '#6a7486', 'mail4': '#98a3b6', 'mail5': '#c8d0de',
    'far0': '#10131a', 'far1': '#1c2029', 'far2': '#2c323f', 'rust0': '#3a1c10', 'rust1': '#7a3a1a', 'rust2': '#b8662c',
    'cloak0': '#1a2a3a', 'cloak1': '#2a4258', 'cloak2': '#40647e', 'wood0': '#3a2a1c', 'wood1': '#6a4c2e', 'wood2': '#9a7448',
    'gold0': '#6a5416', 'gold1': '#c8a032', 'gold2': '#f6dc7a', 'fire0': '#1a5aa0', 'fire1': '#4ac0ff', 'fire2': '#c8f4ff',
    'blade0': '#586070', 'blade1': '#9aa6ba', 'blade2': '#e0e8f4', 'socket': '#06080e', 'eye': '#a8f0ff', 'mouth': '#0c0f16',
    'dust': '#8a93a8', 'bone': '#d8d2bc', 'bone2': '#f0ead8', 'nail': '#c8c2ac',
})


def einherjar(clip, n):
    f = Frame(EINH)
    p = EINH
    rng = rng_for('einherjar', clip, n)
    g = biped_gait(clip, n)
    glow = g['glow']
    HEAD_AT = (11, -24)

    def back(c):
        # a tattered cloak hanging from the shoulders
        x0, y0 = c.at(-4, -19)
        sway = g['sway'] + math.sin(n * .9) * 1.2 + g['dx'] * -.15
        cloak = polygon([(x0 - 2, y0), (x0 + 5, y0 + 1), (x0 - 9 - sway, y0 + 22), (x0 - 14 - sway, y0 + 25), (x0 - 12 - sway, y0 + 19), (x0 - 17 - sway, y0 + 21), (x0 - 12, y0 + 8)])
        f.a[mc.dilate(cloak) & ~cloak] = p['ol']
        f.a[cloak] = p['cloak1']
        f.line((x0, y0 + 1), (x0 - 10 - sway, y0 + 22), 'cloak2', 1)

    def deco_torso(c):
        # a mail shirt: scale rows, a rust-red tunic beneath, a belt with a gold buckle
        for k, (ox, oy, rx, ry) in enumerate([(2, -14, 9, 5), (3, -8, 9.5, 4), (-2, -3, 8, 3.4)]):
            ring = ellipsoid(*c.at(ox, oy), rx, ry, c.ang * .6)
            f.paint(ring, p.ramp('mail1', 'mail2', 'mail3', 'mail4'), outline=False, dither=.5)
            x, y = c.at(ox, oy)
            for j in range(-3, 4):
                f.dots([(x + j * 2.6, y + 1 + (j % 2))], 'mail1')
        x0, y0 = c.at(0, 5)
        tunic = polygon([(x0 - 8, y0), (x0 + 9, y0 + 1), (x0 + 7, y0 + 11), (x0 + 2, y0 + 9), (x0 - 2, y0 + 12), (x0 - 7, y0 + 9)])
        f.a[mc.dilate(tunic) & ~tunic] = p['ol']
        f.a[tunic] = p['rust1']
        f.line((x0 - 7, y0 + 7), (x0 + 6, y0 + 8), 'rust0', 1)
        f.line((x0 - 8, y0 + 1), (x0 + 9, y0 + 2), 'wood0', 2)
        f.dots([(x0 + 1, y0 + 1)], 'gold2')

    def head(c):
        hx, hy = c.at(HEAD_AT[0], HEAD_AT[1])
        hx += g['hx']
        hy += g['hy'] + g['lie'] * 2
        neck = capsule(c.at(HEAD_AT[0] - 5, HEAD_AT[1] + 7), (hx, hy + 2), 5.2, 4.8)
        helm = ellipsoid(hx, hy, 7.6, 7.2, c.ang * .4)
        chain_paint(f, [neck, helm], p.ramp('mail0', 'mail1', 'mail2', 'mail3', 'mail4'), dither=.45)
        # a nasal bar and a dark face with blue fire in the eyes
        face = ellipsoid(hx + 3.2, hy + 1.4, 3.8, 4.6)
        f.flat(face[0], 'socket')
        f.line((hx + 5.6, hy - 5), (hx + 5.8, hy + 4), 'mail3', 1)
        f.line((hx - 7, hy - 1), (hx + 7, hy - 2.5), 'gold1', 1)
        if g['eyes'] == 'dead':
            eye_dead(f, hx + 3.6, hy + .4, 'fire0')
        elif g['eyes'] == 'blink':
            f.line((hx + 1.4, hy + .6), (hx + 5, hy + .6), 'fire0', 1)
        else:
            f.dots([(hx + 2.6, hy + .4), (hx + 4.6, hy + .4)], 'fire1' if glow < 1.3 else 'fire2')
        if g['jaw'] > .1:
            f.flat(ellipsoid(hx + 3.4, hy + 4.4 + g['jaw'] * 1.6, 2.6, .8 + g['jaw'] * 1.6)[0], 'mouth')
        # a cold flame licking up from the helm, and two small wings of horn
        for k, ox in enumerate((-2, 1, 4)):
            h = 5 + 3 * math.sin(n * 1.3 + k * 2) + 3 * (glow - 1)
            tri = polygon([(hx + ox - 1.8, hy - 6), (hx + ox + .4, hy - 6 - h), (hx + ox + 2, hy - 6)])
            f.a[tri] = p['fire1' if k == 1 else 'fire0']
        for sgn, ox in ((-1, -6), (1, 5)):
            horn = smooth([(hx + ox, hy - 3), (hx + ox + sgn * 4, hy - 7), (hx + ox + sgn * 5, hy - 12)], 6)
            for a, b in zip(horn, horn[1:]):
                f.line(a, b, 'ol', 4)
            for a, b in zip(horn, horn[1:]):
                f.line(a, b, 'bone2' if sgn > 0 else 'bone', 2)

    def hand(c, near, far):
        # the far hand carries the round shield, the near hand the sword
        sx, sy = far
        shield = ellipsoid(sx + 3, sy - 1, 8.6, 9.2)
        f.paint(shield, p.ramp('wood0', 'wood1', 'wood2'), outline=True, dither=.4)
        f.line((sx - 3, sy - 1), (sx + 9, sy - 1), 'mail3', 1)
        f.line((sx + 3, sy - 9), (sx + 3, sy + 7), 'mail3', 1)
        f.flat(ellipsoid(sx + 3, sy - 1, 2.8, 2.8)[0], 'gold1', outline=True, edge='gold0')
        f.dots([(sx + 2, sy - 2)], 'gold2')
        hx, hy = near
        grip = ellipsoid(hx, hy, 3.6, 3.4)
        f.paint(grip, p.ramp('mail1', 'mail2', 'mail3'), dither=.3)
        # the blade continues the line of the arm, pointing mostly up and forward, tipping forward in the swing
        rel = g['arm_n']
        a = math.atan2(rel[1], rel[0])
        if clip == 'attack' and n in (3, 4, 5):
            a = [.9, 1.5, 1.1][n - 3]
        elif clip == 'attack' and n < 3:
            a = [-1.6, -2.4, -2.9][n]
        else:
            a = -1.15 + (a + 1.2) * .25
        ln = 21
        tip = (hx + math.cos(a) * ln, hy + math.sin(a) * ln)
        guard_a = a + math.pi / 2
        gx0, gy0 = hx + math.cos(a) * 3.4, hy + math.sin(a) * 3.4
        f.line((hx - math.cos(a) * 3, hy - math.sin(a) * 3), (gx0, gy0), 'ol', 5)
        f.line((hx, hy), tip, 'ol', 5)
        f.line((hx, hy), tip, 'blade1', 3)
        f.line((hx + math.cos(a) * 3, hy + math.sin(a) * 3 - 1), (tip[0], tip[1] - 1), 'blade2', 1)
        f.line((gx0 - math.cos(guard_a) * 4, gy0 - math.sin(guard_a) * 4), (gx0 + math.cos(guard_a) * 4, gy0 + math.sin(guard_a) * 4), 'gold1', 2)
        f.dots([(hx + math.cos(a) * 12 + math.cos(guard_a), hy + math.sin(a) * 12 + math.sin(guard_a))], 'ol')   # a notch

    def after(c, near, far):
        if g['slam'] > 0:
            x = near[0] + 6
            f.dots([(x + k * 3, AY - 1) for k in range(-3, 4)], 'dust')
            dust(f, rng, x, g['slam'] * .7)

    return draw_biped(f, p, g, dict(
        leg_h=28, leg=(14.5, 14.5), thick=.78, arm=(13.5, 13.5), arm_r=(4.2, 3.6, 3.0), shoulder=(7, -17), torso=(10.5, 13.5), torso_at=(2, -12), torso_tilt=.15,
        pelvis=(8.5, 7), head_at=(11, -24),
        body=['mail0', 'mail1', 'mail2', 'mail3', 'mail4'], far=['far0', 'far1', 'far2'], near=['mail0', 'mail1', 'mail2', 'mail3', 'mail4'],
        back=back, deco_torso=deco_torso, head=head, hand=hand, after=after))



# ----------------------------------------------------------------------------------------------
# Skyray: a manta of storm cloud, pale underneath, slate on top, lightning veined through its wings. It hovers and spits bolts.
# ----------------------------------------------------------------------------------------------
RAY = Palette({
    'top0': '#161c34', 'top1': '#262f55', 'top2': '#3e4c82', 'top3': '#5f74b4', 'top4': '#8ea6dc',
    'und0': '#6a7ca8', 'und1': '#9eb0d4', 'und2': '#d2def2', 'und3': '#f2f8ff',
    'far0': '#0e1226', 'far1': '#1a2140', 'far2': '#2c3868', 'zap0': '#2a73d6', 'zap1': '#5fc4ff', 'zap2': '#b8f0ff', 'zap3': '#f4fdff',
    'eye': '#fff27a', 'eye2': '#ffffff', 'socket': '#070a16', 'mouth': '#2a1030', 'spike': '#d6e2f6', 'orb0': '#2a8ae0', 'orb1': '#9ee4ff',
})


def skyray(clip, n):
    f = Frame(RAY)
    p = RAY
    rng = rng_for('skyray', clip, n)
    cx, cy = 46., 50.
    flap = [0, .3, .6, .9, .6, .3][n % 6] if clip == 'idle' else .45          # 0..1 wing up
    bob = [0, -1, -2, -1, 0, 1][n % 6] if clip == 'idle' else 0
    head_up, orb, glow, eyes, flash, fall, dx = 0., 0., 1., 'open', False, 0., 0.
    if clip == 'walk':
        flap = [.2, .0, .5, 1., .7, .2, .1, .3][n]
        bob = [0, 1, -2, -5, -3, 1, 1, 0][n]
    elif clip == 'attack':
        flap = [.5, .7, .9, .1, .0, .3, .5, .5][n]
        head_up = [0, 2, 4, -1, -2, 0, 0, 0][n]
        orb = [.0, .4, 1., .0, .0, .0, .0, .0][n]
        dx = [-1, -2, -3, 3, 5, 3, 1, 0][n]
        bob = [0, -1, -2, 0, 1, 0, 0, 0][n]
        glow = [1.1, 1.3, 1.5, 1.5, 1.3, 1.1, 1, 1][n]
        eyes = 'angry'
    elif clip == 'hurt':
        flap = [1., .8, .5, .3][n]
        dx = [-5, -3, -1, 0][n]
        bob = [-3, -2, -1, 0][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
        glow = [1.5, 1.3, 1.1, 1][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead'
        fall = [0, .1, .3, .55, .8, 1, 1, 1][n]
        flap = [1., .9, .6, .4, .25, .1, 0, 0][n]
        dx = [0, -2, -3, -4, -4, -4, -4, -4][n]
        glow = [1.5, 1.1, .9, .7, .5, .3, .2, .1][n]
    cx += dx
    cy += bob + fall * (AY - 20 - cy)
    lying = fall >= 1
    tilt = .08 + fall * .1

    def at(x, y):
        a, b = rotate(x, y, -tilt)
        return cx + a, cy + b

    def wing(root_front, root_back, tip, lead_bulge, trail_dip, ramp, shade_from):
        mid_lead = ((root_front[0] + tip[0]) / 2 + lead_bulge[0], (root_front[1] + tip[1]) / 2 + lead_bulge[1])
        mid_trail = ((root_back[0] + tip[0]) / 2 + trail_dip[0], (root_back[1] + tip[1]) / 2 + trail_dip[1])
        pts = smooth([root_front, mid_lead, tip, mid_trail, root_back], 26)
        mask = polygon(pts)
        f.a[mc.dilate(mask) & ~mask] = p['ol']
        f.paint((mask, gradient(mask, tip[0], tip[1], shade_from[0], shade_from[1])[1]), ramp, outline=False, dither=.5)
        return mask, pts

    spread = 1 - flap * .55                                           # wings foreshorten as they beat up
    # tail: a long whip trailing behind (left), flicking at its tip
    tb = at(-17, 0)
    flick = math.sin(n * 1.2) * 3 if not lying else 0
    tail = smooth([tb, at(-23, 2 + flick * .3), at(-28, -1 - flick * .6), at(-32, 3 + flick * .6)], 14)
    for u, v in zip(tail, tail[1:]):
        f.line(u, v, 'ol', 4)
    for k, (u, v) in enumerate(zip(tail, tail[1:])):
        f.line(u, v, 'top2' if k % 3 else 'top1', 2)
    f.dots([tail[-1]], 'zap2')
    # far wing: swept up and back, darker
    far_tip = at(-13, -17 * spread - 2 - flap * 3)
    wing(at(10, -1), at(-15, -1), far_tip, (3, -3), (-2, 2), p.ramp('far0', 'far1', 'far2', 'top1'), at(4, -1))
    # body: a flat diamond of cloud
    body = ellipsoid(*at(0, 0), 20, 7.4, tilt)
    f.a[mc.dilate(body[0]) & ~body[0]] = p['ol']
    f.paint(body, p.ramp('top1', 'top2', 'top3', 'top4'), outline=False, dither=.5)
    # near wing: sweeps down and back, tip dragging low
    near_tip = at(-14, 19 * spread + 2 - flap * 2)
    wing(at(11, 2), at(-15, 1), near_tip, (3, 4), (-3, -3), p.ramp('top0', 'top1', 'top2', 'top3', 'top4'), at(2, 2))
    # rim light along the leading edge, lightning veins across the wing
    f.line(at(11, 3), at(-1 + 0, 10 * spread + 2), 'top4', 1)
    for k in range(2 + int(glow > 1.2) * 2):
        a0 = at(2 - k * 4, 2 + k)
        b0 = (a0[0] - rng.uniform(4, 8), a0[1] + rng.uniform(3, 8) * spread)
        zig = bolt_path(rng, a0, b0, 1.4, 3)
        for u, v in zip(zig, zig[1:]):
            f.line(u, v, 'zap1' if glow < 1.3 else 'zap2', 1)
    # head: a blunt nose with two horn-fins, the eyes on top
    hx, hy = at(17 + head_up * .2, -1 - head_up * .8)
    for sgn in (-1, 1):
        horn = polygon([(hx - 2, hy + sgn * 4), (hx + 11, hy + sgn * 8 - 2), (hx + 2, hy + sgn * 1)])
        f.a[mc.dilate(horn) & ~horn] = p['ol']
        f.a[horn] = p['top3'] if sgn < 0 else p['top2']
    skull = ellipsoid(hx, hy, 8.5, 6.4, tilt)
    f.paint(skull, p.ramp('top1', 'top2', 'top3', 'top4', 'und1'), dither=.4)
    mouth = ellipsoid(hx + 7, hy + 3, 3, 1.4 + (1.8 if orb > 0 else 0))
    f.flat(mouth[0], 'mouth')
    ex, ey = hx + 2, hy - 2
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    else:
        f.flat(ellipsoid(ex, ey, 2.8, 2.5)[0], 'socket')
        f.dots([(ex + 1, ey), (ex, ey - 1), (ex + 1, ey - 1), (ex + 2, ey)], 'eye')
    # the charge: an orb of lightning at the mouth, then two bolts
    if orb > 0:
        r = 2 + 5 * orb
        f.flat(ellipsoid(hx + 10 + r * .5, hy + 3, r, r)[0], 'orb0', outline=True, edge='zap0')
        f.flat(ellipsoid(hx + 10 + r * .5, hy + 3, r * .55, r * .55)[0], 'orb1')
        f.dots([(hx + 10 + r * .5, hy + 3)], 'zap3')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(2):
            x0, y0 = hx + 10, hy + 3
            tipx = x0 + 5 + (n - 3) * 4 + k * 3
            zig = bolt_path(rng, (x0, y0), (tipx, y0 + (k - .5) * 9 + 3), 2.4, 5)
            for u, v in zip(zig, zig[1:]):
                f.line(u, v, 'zap2', 1)
            f.dots([zig[-1]], 'zap3')
    if flash:
        f.whiten()
    return fit(f.a, floor=AY + 2)


# ----------------------------------------------------------------------------------------------
# Thunderroc: a storm eagle the size of a house. Slate and gold plumage, a hooked beak, lightning running along its wings.
# ----------------------------------------------------------------------------------------------
ROC = Palette({
    'pl0': '#141a2c', 'pl1': '#26304c', 'pl2': '#44547c', 'pl3': '#7088b4', 'pl4': '#b4c8e4', 'sheen': '#e0a82a', 'sheen2': '#ffe27a',
    'far0': '#0c101c', 'far1': '#181f34', 'far2': '#2c3858', 'beak0': '#6a4a14', 'beak1': '#c4902a', 'beak2': '#f6d870',
    'eye': '#fff27a', 'eye2': '#ffffff', 'socket': '#06080e', 'claw': '#e8dcb0', 'leg': '#a8801e', 'mouth': '#4a1420',
    'dart': '#5fc4ff', 'dart2': '#e8fbff', 'bd0': '#2a1a10', 'bd1': '#4c2e18', 'bd2': '#7a4c24', 'bd3': '#a86e34', 'bd4': '#d09a52',
    'hd0': '#6a7690', 'hd1': '#a0acc4', 'hd2': '#d4dcea', 'hd3': '#f6faff',
})


def thunderroc(clip, n):
    f = Frame(ROC)
    p = ROC
    rng = rng_for('thunderroc', clip, n)
    flap = [-1.9, -1.3, -.6, 0., -.6, -1.3][n % 6] if clip == 'idle' else 0.
    cx, cy = 45., 53.
    tilt, head_dx, head_dy, beak, wing, eyes, flash, glow, fall = .25, 0., 0., 0., flap, 'open', False, 1., 0.
    spread = .24
    if clip == 'walk':
        cy += [0, 1, -2, -4, -2, 1, 1, 0][n]
        wing = [-1.4, -.6, -2.1, -1.8, -.4, .1, -.6, -1.2][n]
        tilt = [.25, .3, .1, 0., .1, .3, .3, .25][n]
    elif clip == 'attack':
        cx += [-2, -4, -5, 4, 7, 5, 1, 0][n]
        wing = [-1.9, -2.3, -2.5, -.2, .3, -.6, -1.3, -1.7][n]
        spread = [.24, .22, .2, .3, .32, .28, .24, .24][n]
        head_dx = [-1, -3, -4, 4, 6, 3, 1, 0][n]
        head_dy = [0, 1, 2, 1, 2, 1, 0, 0][n]
        beak = [0, 0, .2, 1, .8, .3, 0, 0][n]
        tilt = [.3, .45, .55, .05, -.1, .1, .2, .25][n]
        eyes = 'angry'
        glow = 1.3
    elif clip == 'hurt':
        cx += [-5, -3, -1, 0][n]
        wing = [-2.3, -1.9, -1.3, -1.][n]
        tilt = [.6, .45, .3, .25][n]
        head_dx = [-3, -2, -1, 0][n]
        beak = [.8, .5, .2, 0][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead'
        fall = [0, 0, .2, .5, .8, 1, 1, 1][n]
        wing = [-1.4, -2.4, -2.6, -2.2, -1.8, -1.2, -.6, -.4][n]
        tilt = [.3, .6, 1., 1.3, 1.5, 1.57, 1.57, 1.57][n]
        beak = [.5, .9, .8, .5, .4, .4, .4, .4][n]
        cx += [0, -2, -4, -5, -6, -6, -6, -6][n]
    cy += fall * (AY - 13 - cy) + (math.sin(n * 1.0) * 1.2 if clip == 'idle' else 0)
    if clip == 'idle':
        cy += [0, -1, -2, -1, 0, 1][n]
    lying = fall >= 1

    def at(dx, dy):
        x, y = rotate(dx, dy, -tilt * (.2 if not fall else 0))
        return cx + x, cy + y

    # far wing, legs, tail, body, near wing, head: back to front
    def wing_draw(shoulder, ramp, length, scale=1.):
        sx, sy = shoulder
        base_angle = wing
        feathers = []
        for k in range(8):
            a = base_angle + (k - 3.5) * spread * scale
            ln = length * (.62 + .38 * math.sin((k + 1) / 9 * math.pi))
            tip = (sx + math.cos(a + math.pi) * ln * (-1), sy + math.sin(a + math.pi) * ln * (-1))
            feathers.append(tip)
        # a wing sweeps back (to the left) from the shoulder: angle 0 = straight back, negative = raised
        feathers = [(sx - math.cos(base_angle + (k - 3.5) * spread * scale) * ln, sy + math.sin(base_angle + (k - 3.5) * spread * scale) * ln)
                    for k, ln in [(k, length * (.62 + .38 * math.sin((k + 1) / 9 * math.pi))) for k in range(8)]]
        union = np.zeros((H, W), bool)
        shapes = [capsule((sx, sy), tip, 3.6, 1.2) for tip in feathers]
        for sh in shapes:
            union |= sh[0]
        f.a[mc.dilate(union) & ~union] = p['ol']
        for k, sh in enumerate(shapes):
            f.paint(sh, ramp, outline=False, dither=.3)
        cov = ellipsoid(sx - 4, sy, 7, 4.5, base_angle * .5)
        f.paint(cov, ramp, outline=True, dither=.4)

    if not lying:
        wing_draw(at(-2, -8), p.ramp('far0', 'far1', 'far2'), 31, 1.0)
        # tail: three long feathers
        tb = at(-10, 1)
        for k, a in enumerate((.35, .1, -.15)):
            tip = (tb[0] - 14 * math.cos(a + tilt * .5) - 3, tb[1] + 14 * math.sin(a + tilt * .5) + 8)
            f.line(tb, tip, 'ol', 5)
        for k, a in enumerate((.35, .1, -.15)):
            tip = (tb[0] - 14 * math.cos(a + tilt * .5) - 3, tb[1] + 14 * math.sin(a + tilt * .5) + 8)
            f.line(tb, tip, 'pl1' if k % 2 else 'pl2', 3)
        # legs and claws, with the rope
        for lx, near in ((at(1, 6), False), (at(5, 6), True)):
            foot = (lx[0] + 3 + (2 if beak > .5 else 0), lx[1] + 12)
            f.line(lx, foot, 'ol', 4)
            f.line(lx, foot, 'leg', 2)
            for d in (-3, 0, 3):
                f.line(foot, (foot[0] + 4 + d * .5, foot[1] + 3 + abs(d) * .2), 'claw', 2)
    body = ellipsoid(*at(0, 0), 16.5, 10.5, .3 + (tilt - .25) * .5 if not fall else tilt)
    f.paint(body, p.ramp('bd0', 'bd1', 'bd2', 'bd3', 'bd4'), dither=.5)
    # an iridescent sheen along the back
    sheen = ellipsoid(*at(-1, -5), 11, 3.4, .2)
    f.paint((sheen[0] & body[0], sheen[1] * .6), p.ramp('bd2', 'sheen', 'sheen2'), outline=False, dither=.5)
    # a ruff of ragged neck feathers
    for k in range(5):
        a = .5 + k * .5
        x0, y0 = at(8, -2)
        tri = polygon([(x0 + math.cos(a) * 4, y0 - math.sin(a) * 4), (x0 + math.cos(a + .15) * 10 - 2, y0 - math.sin(a + .15) * 10 + 1), (x0 + math.cos(a + .5) * 4, y0 - math.sin(a + .5) * 4)])
        f.a[mc.dilate(tri) & ~tri] = p['ol']
        f.a[tri] = p['hd1' if k % 2 else 'hd2']
    # head and beak
    hxy = at(15 + head_dx, -9 + head_dy)
    neck = capsule(at(8, -3), hxy, 7.8, 6.6)
    skull = ellipsoid(hxy[0], hxy[1], 7.8, 7.0, .2)
    chain_paint(f, [neck, skull], p.ramp('hd0', 'hd1', 'hd2', 'hd3'), dither=.4)
    bx0, by0 = hxy[0] + 4, hxy[1] - 1
    upper = polygon([(bx0, by0 - 4), (bx0 + 10, by0 - 1 - beak * 1.5), (bx0 + 14, by0 + 4 - beak * 1.5), (bx0 + 12, by0 + 8 - beak * 1.5), (bx0 + 10, by0 + 4 - beak), (bx0 + 3, by0 + 2 - beak)])
    lower = polygon([(bx0 + 2, by0 + 3 + beak * 2), (bx0 + 9, by0 + 5 + beak * 5), (bx0 + 3, by0 + 6 + beak * 3)])
    if beak > .1:
        f.flat(polygon([(bx0 + 2, by0 + 1), (bx0 + 9, by0 + 3 + beak), (bx0 + 3, by0 + 5 + beak * 3)]), 'mouth')
    f.a[mc.dilate(lower) & ~lower] = p['ol']
    f.a[lower] = p['beak0']
    f.a[mc.dilate(upper) & ~upper] = p['ol']
    f.paint((upper, gradient(upper, bx0, by0 - 3, bx0 + 8, by0 + 4)[1]), p.ramp('beak0', 'beak1', 'beak2'), outline=False, dither=.3)
    f.dots([(bx0 + 12, by0 + 6 - beak)], 'beak0')
    ex, ey = hxy[0] + 2, hxy[1] - 2
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    elif n == 3 and clip == 'idle':
        f.line((ex - 2, ey), (ex + 2, ey), 'socket', 1)
    else:
        f.flat(ellipsoid(ex, ey, 2.4, 2.2)[0], 'socket')
        f.dots([(ex + 1, ey), (ex, ey - 1), (ex + 1, ey - 1)], 'eye')
    if not lying:
        wing_draw(at(-1, -9), p.ramp('pl0', 'pl1', 'pl2', 'pl3', 'pl4'), 33, 1.05)
    else:
        # dead: wings spread flat on the ground either side
        for sgn, ramp in ((-1, p.ramp('far0', 'far1', 'far2')), (1, p.ramp('pl0', 'pl1', 'pl2', 'pl3'))):
            for k in range(7):
                tip = (cx + sgn * (6 + k * 3.6) - 2, AY - 3 - k * .2 + abs(k - 3) * .3)
                f.line((cx - 2, AY - 9), tip, 'ol', 4)
            for k in range(7):
                tip = (cx + sgn * (6 + k * 3.6) - 2, AY - 3 - k * .2 + abs(k - 3) * .3)
                f.line((cx - 2, AY - 9), tip, 'pl1' if k % 2 else 'pl2', 2)
    if not lying:
        for k in range(1 + int(glow > 1.2) + int(clip == 'attack')):
            a0 = at(-4 - k * 5, -12 - k * 2)
            b0 = (a0[0] - rng.uniform(6, 14), a0[1] - rng.uniform(4, 14))
            zig = bolt_path(rng, a0, b0, 2.2, 4)
            for u, v in zip(zig, zig[1:]):
                f.line(u, v, 'dart2' if glow > 1.2 else 'dart', 1)
    if clip == 'attack' and n in (3, 4, 5):
        zig = bolt_path(rng, (hxy[0] + 8, hxy[1] + 6), (hxy[0] + 14 + (n - 3) * 6, AY - 4), 3.5, 6)
        for u, v in zip(zig, zig[1:]):
            f.line(u, v, 'dart2', 1)
    if flash:
        f.whiten()
    return fit(f.a, floor=AY + 2)


# ----------------------------------------------------------------------------------------------
# Rendering and PixelFlow plumbing (same contract as scripts/make_crag_sprites.py)
# ----------------------------------------------------------------------------------------------
_PAIRS = {'galehound': ('galehound', 'GALE'), 'prismgolem': ('prismgolem', 'PRISM'), 'skyray': ('skyray', 'RAY'), 'einherjar': ('einherjar', 'EINH'),
          'thunderroc': ('thunderroc', 'ROC')}
DRAWERS = {k: (globals()[fn], globals()[pal]) for k, (fn, pal) in _PAIRS.items() if fn in globals() and pal in globals()}
for _kind, _pair in DRAWERS.items():
    assert len(_pair[1].hex) <= 255


def render(kind):
    draw, _ = DRAWERS[kind]
    return {clip: np.array([draw(clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def bounds_report(kind, frames):
    """Every frame's bounding box against the canvas edges: nothing may touch them."""
    bad = []
    for clip, grids in frames.items():
        for n, grid in enumerate(grids):
            ys, xs = np.nonzero(grid)
            if len(xs) and (xs.min() < 1 or ys.min() < 1 or xs.max() > W - 2 or ys.max() > H - 2):
                bad.append(f'{clip} {n}: x {xs.min()}-{xs.max()}, y {ys.min()}-{ys.max()}')
    return bad


def top_report(kind, frames):
    """The topmost pixel of the idle frames: the health bar's `top` in client/field.js."""
    tops = []
    for grid in frames['idle']:
        ys, _ = np.nonzero(grid)
        tops.append(AY - int(ys.min()))
    return min(tops), max(tops)


def preview(kinds, out, scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        for problem in bounds_report(kind, frames):
            print(f'  EDGE {kind} {problem}')
        print(f'  {kind}: idle top {top_report(kind, frames)}')
        for clip, grids in frames.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#243048')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def meta_path():
    return ASSETS / 'sky.txt'


def build(kinds, replace=False):
    path = meta_path()
    meta = json.loads(path.read_text()) if path.exists() else {}
    known = meta.get('sprites', {})
    clash = [k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist (ids in sky.txt). Use export to preserve edits; --replace discards them.')
    for kind in clash:
        api('delete', {'sprite_id': known[kind]})
    made = {}
    for kind in kinds:
        frames = render(kind)
        bad = bounds_report(kind, frames)
        if bad:
            raise SystemExit(f'{kind} touches the canvas edge: {bad}')
        palette = DRAWERS[kind][1].hex
        np.savez_compressed(RAW / f'sky_{kind}_raw.npz', **frames)
        sid = api('create', {'name': PREFIX + kind + '_all', 'width': W, 'height': H,
                            'frames': sum(count for _, count in CLIPS.values()),
                            'layers': 1, 'fps': 10, 'palette': palette, 'persist': True,
                            'ops': [{'op': 'set_layer', 'layer': 0, 'name': kind}]})['sprite_id']
        made[kind] = sid
        offset = 0
        try:
            for clip, (_, count) in CLIPS.items():
                for n, grid in enumerate(frames[clip]):
                    api('draw', {'sprite_id': sid, 'frame': offset + n, 'ops': [{'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
                offset += count
            print(kind, sid, f'{offset} frames')
        except Exception:
            api('delete', {'sprite_id': sid})
            raise
        # keep a manifest as we go: `list` only shows the newest 100 sprites
        meta['sprites'] = {**meta.get('sprites', {}), **made}
        path.write_text(json.dumps(meta, indent=2) + '\n')


def export(kinds):
    path = meta_path()
    meta = json.loads(path.read_text())
    saved = meta['sprites']
    clips = {}
    for kind in kinds:
        packet = api('get?sprite_id=' + saved[kind])
        sp = packet.get('sprite', packet)
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
        atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
        offset = 0
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            sheet = Image.new('RGBA', (8 * W, H), '#243048')
            for n in range(count):
                cel = sp['frames'][offset + n]['cels'][0]
                if 'rle' in cel:
                    runs = cel['rle']
                    grid = np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
                else:
                    grid = np.array(cel['grid'], dtype=np.uint8)
                image = rgba(grid, sp['palette'])
                atlas.alpha_composite(image, (n * W, row * H))
                sheet.alpha_composite(image, (n * W, 0))
            clips[clip] = {'fps': fps, 'n': count, 'row': row, 'editorStart': offset}
            offset += count
            dest = ROOT / 'test-results/sky-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'sky_{kind}.png', optimize=True)
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': saved}
    path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/sky_<kind>.png and sky.txt')


def verify(kinds):
    """The exported atlas must equal the freshly rendered frames pixel for pixel."""
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        atlas = Image.open(ASSETS / f'sky_{kind}.png').convert('RGBA')
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * W, row * H, (n + 1) * W, (row + 1) * H))
                if np.array(cell).tobytes() != np.array(rgba(frames[clip][n], palette)).tobytes():
                    raise SystemExit(f'{kind} {clip} {n} differs from the render')
        print(kind, 'atlas is pixel-identical to the render')


def view(kind, picks, out, scale=4):
    """A throwaway contact strip of chosen frames (clip:n ...) at `scale` on the dark ground."""
    palette = DRAWERS[kind][1].hex
    draw, _ = DRAWERS[kind]
    cells = []
    for pick in picks:
        clip, n = pick.split(':')
        cells.append((pick, draw(clip, int(n))))
    sheet = Image.new('RGBA', (len(cells) * W, H + 12), '#243048')
    d = ImageDraw.Draw(sheet)
    for i, (label, grid) in enumerate(cells):
        sheet.alpha_composite(rgba(grid, palette), (i * W, 0))
        d.line([(i * W + AX - 3, AY), (i * W + AX + 3, AY)], fill='#eabce1')
        d.text((i * W + 2, H), label, fill='white')
    sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out)


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    names = [a for a in sys.argv[2:] if a in DRAWERS] or list(DRAWERS)
    if command == 'build':
        build(names, '--replace' in sys.argv)
    elif command == 'export':
        export(names)
    elif command == 'verify':
        verify(names)
    elif command == 'view':
        view(names[0], [a for a in sys.argv[3:] if ':' in a and not a.startswith('/')], next(a for a in sys.argv[2:] if a.endswith('.png')))
    elif command == 'preview':
        directory = next((a for a in sys.argv[2:] if a not in DRAWERS and not a.startswith('--')), ROOT / 'test-results/sky-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_sky_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...] | verify [kind...] | view kind out.png clip:n ...')
