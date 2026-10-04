#!/usr/bin/env python3
"""makesprites workflow for the Ran's Deep monsters: preview | build [--replace] | export | verify | view.

Six kinds share the Emberfall Crags contract (scripts/make_crag_sprites.py): one 96x96 frame, a foot anchor at (48, 90),
right-facing art (the game mirrors it) and five clips (idle 6, walk 8, attack 8, hurt 4, die 8) so client/field.js drives them
with the Ironhide's state machine: walk frames 2-4 are the hop, 5-7 the landing, attack 0-2 the windup, 3-5 the lunge, 6-7 the
recovery.

  draugr     Drowned Draugr    (L35)  a sailor drowned long ago: bloated grey-green flesh, barnacles, weed for hair, a rusted axe
  angler     Lantern Angler    (L36)  a walking anglerfish with a glowing lure on a stalk; the lure flares before it shoots a bead
  moray      Gnashing Moray    (L37)  a ship-long eel that coils in the coral and strikes
  siren      Siren             (L38)  Ran's handmaiden: a pale singer with a fishtail and streaming hair, hovering as she sings
  shellback  Shellback         (L39)  a house-sized sea turtle with a drowned ship's plank growing out of its shell; pounds the ground
  kraken     The Kraken        (L40)  the elite: a great violet mantle with two yellow eyes and a ring of tentacles
  hvitserk   Hvitserk          (L37)  elite: the drowned captain of Naglfar, a draugr in a navy coat and tricorn (a quest)
  ghostmaw   Ghostmaw          (L39)  elite: a pale, huge moray that guards the deepest corridors (no quest)

The biped and quadruped rigs of make_wyrd_sprites.py carry the draugr and the shellback; the other four are bespoke.
`build` saves ONE new 34-frame PixelFlow sprite per kind (valhallasc_deep_<kind>_all) and refuses existing names unless --replace
is given (it discards editor edits). `export` reads the editor frames back, so edits survive, and writes
client/assets/deep_<kind>.png plus deep.txt.
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
from make_wyrd_sprites import (biped_gait, chain_paint, draw_biped, draw_quad, dust, eye_dead, eyes_on, fit,  # noqa: E402
                               ik, quad_gait, smooth, thread)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
PREFIX = 'valhallasc_deep_'
KINDS = ['draugr', 'angler', 'moray', 'siren', 'shellback', 'kraken', 'hvitserk', 'ghostmaw']
RAW = ROOT / 'scripts'


def strand(f, pts, name, width=2, outline=True):
    """A drooping line (weed, hair): an outline underneath, then the colour."""
    if outline:
        for a, b in zip(pts, pts[1:]):
            f.line(a, b, 'ol', width + 2)
    for a, b in zip(pts, pts[1:]):
        f.line(a, b, name, width)


def bubbles(f, rng, x, y, amount, name='bub'):
    for _ in range(int(amount)):
        f.dots([(x + rng.uniform(-8, 8), y - rng.uniform(0, 18))], name)


# ----------------------------------------------------------------------------------------------
# Drowned Draugr: a sailor who never came up. Bloated grey-green flesh, barnacles, weed for hair and beard, a rusted boarding axe.
# ----------------------------------------------------------------------------------------------
DRAUG = Palette({
    'sk0': '#14242e', 'sk1': '#27434d', 'sk2': '#456a70', 'sk3': '#6a9490', 'sk4': '#9ac8c0', 'sk5': '#cfeee4',
    'far0': '#0c171d', 'far1': '#18292f', 'far2': '#27414a', 'cl0': '#1c1c16', 'cl1': '#3a3a2c', 'cl2': '#5e5c44',
    'wd0': '#1a3a24', 'wd1': '#2e6a3a', 'wd2': '#58a050', 'wd3': '#98d070', 'bn0': '#8a8672', 'bn1': '#c8c3ac', 'bn2': '#f0ecdc',
    'ru0': '#3a1c10', 'ru1': '#7a3a1a', 'ru2': '#b8662c', 'wood0': '#2c1e12', 'wood1': '#5a4028', 'ir0': '#2c3038', 'ir1': '#586070', 'ir2': '#a0acb8',
    'eye': '#e8fff8', 'glow': '#6affd2', 'socket': '#050b10', 'mouth': '#0a1216', 'tooth': '#d8d4bc', 'bub': '#cdeef4', 'dust': '#6a8e94',
})


def _recolour(base, edits):
    colours = {k: v for k, v in zip(base.names, base.hex)}
    return Palette({**{name: base.hex[i] for name, i in base.names.items() if name not in ('clear', 'ol', 'flash')}, **edits})


CAPT = _recolour(DRAUG, {'sk0': '#10202c', 'sk1': '#1f3a4a', 'sk2': '#3a5c6e', 'sk3': '#5c8494', 'sk4': '#8cb4c0', 'cl0': '#0c1426', 'cl1': '#1c2c4a', 'cl2': '#34508a',
                         'gold': '#e0b43a', 'hat': '#14101c', 'glow': '#ffd86a', 'eye': '#fff4d0'})


def draugr(clip, n, pal=None, captain=False):
    pal = pal or DRAUG
    f = Frame(pal)
    p = pal
    rng = rng_for('draugr', clip, n)
    g = biped_gait(clip, n)
    glow = g['glow']
    HEAD_AT = (11, -25)

    def back(c):
        # weed hanging from the shoulders, swaying as it drifts
        x0, y0 = c.at(-5, -19)
        sway = g['sway'] + math.sin(n * .9) * 2 + g['dx'] * -.15
        for k, ln in enumerate((24, 17)):
            pts = smooth([(x0 - k * 3, y0 + k), (x0 - 4 - k * 2 - sway * .4, y0 + ln * .4), (x0 - 6 - k * 3 - sway, y0 + ln * .75), (x0 - 5 - k * 3 - sway * 1.4, y0 + ln)], 10)
            strand(f, pts, 'wd1' if k == 0 else 'wd0', 2)
            f.dots([pts[-1]], 'wd3')

    def barnacles(points):
        for x, y in points:
            f.dots([(x, y), (x + 1, y), (x, y + 1), (x - 1, y)], 'bn1')
            f.dots([(x, y - 1)], 'bn2')
            f.dots([(x + 1, y + 1)], 'bn0')

    def deco_torso(c):
        # a rotten tunic hanging in rags, a rope belt, barnacles where the flesh meets the sea
        x0, y0 = c.at(0, -14)
        rag = math.sin(n * .8) * 1.2
        tunic = polygon([(x0 - 8, y0), (x0 + 9, y0 + 1), (x0 + 8, y0 + 18), (x0 + 5, y0 + 15 + rag), (x0 + 2, y0 + 21), (x0 - 1, y0 + 16), (x0 - 4, y0 + 20 + rag), (x0 - 7, y0 + 15)])
        f.a[mc.dilate(tunic) & ~tunic] = p['ol']
        f.a[tunic] = p['cl1']
        f.line((x0 - 6, y0 + 4), (x0 + 6, y0 + 6), 'cl2', 1)
        f.line((x0 - 5, y0 + 12), (x0 + 2, y0 + 13), 'cl0', 1)
        bx, by = c.at(0, 2)
        f.line((bx - 8, by), (bx + 9, by + 1), 'wood0', 2)
        f.dots([(bx + 2, by + 2), (bx + 2, by + 3)], 'wood1')
        barnacles([c.at(6, -18), c.at(-1, -10), c.at(5, -3), c.at(-6, 0)])
        if captain:                                                          # gold epaulettes and a buckle on a navy coat
            f.dots([c.at(7, -19), c.at(8, -19), c.at(-5, -19), c.at(-6, -19), c.at(2, 2), c.at(3, 2)], 'gold')
        for k in range(3):                                                   # a rib showing through the tear
            f.line((x0 + 3 + k * 1, y0 + 1 + k * 3), (x0 + 8, y0 + 2 + k * 3), 'sk5', 1)

    def head(c):
        hx, hy = c.at(HEAD_AT[0], HEAD_AT[1])
        hx += g['hx']
        hy += g['hy'] + g['lie'] * 2
        neck = capsule(c.at(HEAD_AT[0] - 5, HEAD_AT[1] + 7), (hx, hy + 2), 5.2, 4.6)
        skull = ellipsoid(hx, hy, 7.4, 7.8, c.ang * .4)
        jaw_o = g['jaw'] * 3.6
        jaw = ellipsoid(hx + 2.2, hy + 6.2 + jaw_o, 5.4, 2.8, c.ang * .3)
        if g['jaw'] > .1:
            f.flat(ellipsoid(hx + 3, hy + 6 + jaw_o * .6, 4.2, 1.2 + jaw_o * .5)[0], 'mouth', outline=True)
        chain_paint(f, [neck, skull], p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4'), dither=.5)
        f.paint(jaw, p.ramp('sk0', 'sk1', 'sk2', 'sk3'), outline=True, dither=.4)
        f.dots([(hx + 1.5 + k * 1.8, hy + 4.6 + jaw_o * .3) for k in range(3)], 'tooth')
        # sunken eyes with a cold green glow
        f.flat(ellipsoid(hx + 3.4, hy - .6, 3.2, 3.4)[0], 'socket')
        if g['eyes'] == 'dead':
            eye_dead(f, hx + 3.6, hy - .6, 'glow')
        elif g['eyes'] == 'blink':
            f.line((hx + 1.4, hy - .6), (hx + 5, hy - .6), 'glow', 1)
        else:
            f.dots([(hx + 2.8, hy - .8), (hx + 4.4, hy - .8)], 'glow' if glow < 1.3 else 'eye')
        # weed for hair, streaming back, and a beard under the chin
        for k in range(5):
            sx, sy = hx - 5 + k * 2, hy - 6 - (k % 2)
            sw = g['sway'] + math.sin(n * 1.1 + k) * 1.6
            pts = smooth([(sx, sy), (sx - 3 - sw * .3, sy + 6), (sx - 7 - sw, sy + 13 + k), (sx - 8 - sw * 1.3, sy + 19 + k)], 8)
            strand(f, pts, ['wd1', 'wd2', 'wd0'][k % 3], 1)
        if captain:                                                          # a tricorn hat, black with a gold band
            hat = polygon([(hx - 10, hy - 4), (hx - 6, hy - 9), (hx - 1, hy - 15), (hx + 5, hy - 9), (hx + 10, hy - 4), (hx + 3, hy - 6), (hx - 4, hy - 6)])
            f.a[mc.dilate(hat) & ~hat] = p['ol']
            f.a[hat] = p['hat']
            f.line((hx - 8, hy - 5), (hx + 8, hy - 5), 'gold', 1)
            f.dots([(hx, hy - 10)], 'gold')
        for k in range(3):
            sx, sy = hx + 1 + k * 2, hy + 8 + jaw_o
            pts = smooth([(sx, sy), (sx - 1, sy + 4), (sx - 3 - g['sway'] * .3, sy + 9 + k * 2)], 6)
            strand(f, pts, 'wd1', 1)

    def hand(c, near, far):
        # the far hand is a bare claw; the near hand swings a rusted boarding axe
        fx, fy = far
        f.paint(ellipsoid(fx, fy, 4.4, 4), p.ramp('far0', 'far1', 'far2'), dither=.3)
        for k in range(3):
            f.line((fx + 1 + k * 1.6, fy + 2), (fx + 2 + k * 1.8, fy + 6), 'far2', 1)
        hx, hy = near
        f.paint(ellipsoid(hx, hy, 4.2, 3.8), p.ramp('sk0', 'sk1', 'sk2', 'sk3'), dither=.3)
        rel = g['arm_n']
        a = math.atan2(rel[1], rel[0])
        if clip == 'attack' and n in (3, 4, 5):
            a = [.9, 1.5, 1.1][n - 3]
        elif clip == 'attack' and n < 3:
            a = [-1.6, -2.4, -2.9][n]
        else:
            a = -1.15 + (a + 1.2) * .25
        d = (math.cos(a), math.sin(a))
        perp = (-d[1], d[0])
        tip = (hx + d[0] * 17, hy + d[1] * 17)
        f.line((hx - d[0] * 3, hy - d[1] * 3), tip, 'ol', 5)
        f.line((hx - d[0] * 3, hy - d[1] * 3), tip, 'wood1', 3)
        head_pts = [(tip[0] - d[0] * 4 + perp[0] * 8, tip[1] - d[1] * 4 + perp[1] * 8), (tip[0] + d[0] * 3 + perp[0] * 6, tip[1] + d[1] * 3 + perp[1] * 6),
                    (tip[0] + d[0] * 4, tip[1] + d[1] * 4), (tip[0] - d[0] * 4 - perp[0] * 1, tip[1] - d[1] * 4 - perp[1] * 1)]
        blade = polygon(head_pts)
        f.a[mc.dilate(blade) & ~blade] = p['ol']
        f.a[blade] = p['ir1']
        f.line(head_pts[0], head_pts[1], 'ir2', 1)
        f.dots([((head_pts[2][0] + head_pts[3][0]) / 2, (head_pts[2][1] + head_pts[3][1]) / 2)], 'ru1')
        f.dots([(tip[0] - perp[0] * 2, tip[1] - perp[1] * 2), (tip[0] + perp[0] * 3, tip[1] + perp[1] * 3 - 1)], 'ru2')

    def after(c, near, far):
        if g['slam'] > 0:
            bubbles(f, rng, near[0] + 6, AY - 1, 10 * g['slam'])
            dust(f, rng, near[0] + 6, g['slam'] * .6, 'dust')

    return draw_biped(f, p, g, dict(
        leg_h=28, leg=(14.5, 14.5), thick=.95, arm=(13.5, 13.5), arm_r=(4.8, 4.0, 3.4), shoulder=(7, -17), torso=(11.5, 14), torso_at=(2, -12), torso_tilt=.2,
        pelvis=(9.5, 7.5), head_at=HEAD_AT,
        body=['sk0', 'sk1', 'sk2', 'sk3', 'sk4'], far=['far0', 'far1', 'far2'], near=['sk0', 'sk1', 'sk2', 'sk3', 'sk4'],
        back=back, deco_torso=deco_torso, head=head, hand=hand, after=after))


def hvitserk(clip, n):
    return draugr(clip, n, CAPT, captain=True)


# ----------------------------------------------------------------------------------------------
# Shellback: a sea turtle the size of a house. A domed shell of drowned-ship timber and barnacle, a beaked head, club feet.
# ----------------------------------------------------------------------------------------------
SHELL = Palette({
    'sk0': '#16241c', 'sk1': '#2c4434', 'sk2': '#4a6a54', 'sk3': '#7a9a74', 'sk4': '#a8c498',
    'far0': '#0f1a14', 'far1': '#1c2c22', 'far2': '#2e4636', 'bel0': '#5a6a4a', 'bel1': '#7e8e62', 'bel2': '#a4b484',
    'sh0': '#18283a', 'sh1': '#2a4a5c', 'sh2': '#486a76', 'sh3': '#789a98', 'sh4': '#a8c8c0', 'rm0': '#5a4a2c', 'rm1': '#9a865a',
    'sm': '#0a141a', 'bn0': '#8a8672', 'bn1': '#c8c3ac', 'bn2': '#f0ecdc', 'wd0': '#1a3a24', 'wd1': '#2e6a3a', 'wd2': '#58a050', 'wd3': '#98d070',
    'wood0': '#2c1e12', 'wood1': '#5a4028', 'wood2': '#86603a', 'bk0': '#4a3c1e', 'bk1': '#b8a060', 'bk2': '#ecdcaa',
    'eye': '#ffd860', 'eye2': '#fff4b8', 'socket': '#0a120e', 'mouth': '#3a1620', 'tongue': '#b8485a', 'hf0': '#0e1618', 'hf1': '#223034',
    'dust': '#6a8e94', 'bub': '#cdeef4', 'nail': '#d8d4bc',
})


def shellback(clip, n):
    f = Frame(SHELL)
    p = SHELL
    g = quad_gait(clip, n)
    rng = rng_for('shellback', clip, n)
    if clip == 'attack':                                              # rear up on the hind legs, then come down with a slam
        g['tilt'] = [-.05, -.13, -.22, .06, .1, .05, 0, 0][n]
        g['lift'] = [0, 2, 5, 0, 0, 0, 0, 0][n]
        g['crouch'] = [1, 2, 2, 0, 0, 1, 0, 0][n]
        g['hy'] = [0, -1, -3, 2, 3, 1, 0, 0][n]
        g['ht'] = [-.05, -.15, -.3, .15, .3, .1, 0, 0][n]
        g['dx'] = [-1, -2, -2, 2, 5, 4, 1, 0][n]

    def tail(c):
        x, y = c.at(-27, 9)
        f.paint(ellipsoid(x, y, 6, 3.4, c.ang), p.ramp('far0', 'far1', 'far2', 'sk2'), dither=.4)

    def deco_back(c):
        # the shell: a tall dome, a pale timber rim, seams in a loose hexagonal pattern, barnacles, weed and a snapped ship's plank
        shell = ellipsoid(*c.at(0, -6), 27, 22, c.ang)
        rim = ellipsoid(*c.at(1, 7), 28, 6, c.ang)
        f.a[mc.dilate(shell[0] | rim[0]) & ~(shell[0] | rim[0])] = p['ol']
        f.paint(rim, p.ramp('rm0', 'rm1', 'sk3'), outline=False, dither=.4)
        f.paint((shell[0], shell[1]), p.ramp('sh0', 'sh1', 'sh2', 'sh3', 'sh4'), outline=False, dither=.5)
        for pts in ([(-18, -4), (-10, -16), (0, -20)], [(-10, -16), (-3, -4), (-4, 5)], [(0, -20), (10, -16), (16, -4)], [(10, -16), (3, -4), (-3, -4)], [(3, -4), (4, 5)], [(16, -4), (22, 4)], [(-18, -4), (-24, 3)]):
            q = [c.at(x, y) for x, y in pts]
            for a, b in zip(q, q[1:]):
                f.line(a, b, 'sm', 1)
        for k, (ox, oy) in enumerate([(-14, -9), (2, -14), (12, -9), (-6, -1), (8, 0), (-20, 1), (19, 1)]):
            x, y = c.at(ox, oy)
            f.dots([(x, y), (x + 1, y), (x, y + 1), (x - 1, y + 1), (x + 2, y + 1)], 'bn1')
            f.dots([(x, y - 1), (x + 1, y)], 'bn2')
        for k, (ox, ln) in enumerate([(-9, 13), (-1, 18), (9, 12)]):                  # weed on top, swaying
            x0, y0 = c.at(ox, -24 + abs(ox) * .25)
            sw = math.sin(n * .9 + k * 1.7) * 2
            pts = smooth([(x0, y0), (x0 - 2 + sw * .4, y0 - ln * .4), (x0 + 1 + sw, y0 - ln * .75), (x0 - 1 + sw * 1.3, y0 - ln)], 8)
            strand(f, pts, ['wd1', 'wd2', 'wd0'][k], 2)
            f.dots([pts[-1]], 'wd3')
        px, py = c.at(-11, -16)                                                       # the plank
        plank = polygon([(px - 3, py + 2), (px + 1, py - 3), (px + 17, py - 20), (px + 21, py - 17), (px + 5, py + 4), (px + 1, py + 5)])
        f.a[mc.dilate(plank) & ~plank] = p['ol']
        f.a[plank] = p['wood1']
        f.line((px + 1, py - 1), (px + 18, py - 18), 'wood2', 1)
        f.dots([(px + 14, py - 12), (px + 8, py - 5)], 'wood0')

    def head(c):
        lie = g['lie']
        hx0, hy0 = c.at(30, 0)
        hc = (hx0 + g['hx'] + 1, hy0 + g['hy'] + 1 + lie * 3)
        ht = g['ht'] * .6
        neck = capsule(c.at(20, 1), hc, 7.2, 5.6)
        skull = ellipsoid(hc[0] + 2, hc[1], 8, 6.2, ht)
        snout_c = (hc[0] + 8 * math.cos(ht), hc[1] + 8 * math.sin(ht) + 1.4)
        snout = ellipsoid(snout_c[0], snout_c[1], 6.4, 3.4, ht)
        jaw_open = g['jaw'] * 4.4
        jaw = ellipsoid(snout_c[0] - 1, snout_c[1] + 3.4 + jaw_open, 5.8, 2.2 + jaw_open * .15, ht)
        if g['jaw'] > .1:
            f.flat(ellipsoid(snout_c[0] - 1, snout_c[1] + 2.4 + jaw_open * .6, 5, 1.2 + jaw_open * .5)[0], 'mouth', outline=True)
            f.flat(ellipsoid(snout_c[0] - 2, snout_c[1] + 3 + jaw_open, 3, 1)[0], 'tongue')
        chain_paint(f, [neck, skull], p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4'), dither=.5)
        f.paint(jaw, p.ramp('sk0', 'sk1', 'sk2', 'sk3'), outline=True, dither=.4)
        f.paint(snout, p.ramp('sk1', 'sk2', 'sk3', 'sk4'), outline=True, dither=.4)
        beak = polygon([(snout_c[0] + 2, snout_c[1] - 2.4), (snout_c[0] + 9, snout_c[1] + 1.6 + jaw_open * .2), (snout_c[0] + 2, snout_c[1] + 3)])
        f.a[mc.dilate(beak) & ~beak] = p['ol']
        f.a[beak] = p['bk1']
        f.line((snout_c[0] + 3, snout_c[1] - 1.4), (snout_c[0] + 8, snout_c[1] + .8), 'bk2', 1)
        f.dots([(snout_c[0] + 5, snout_c[1] - 1)], 'bk0')
        eyes_on(f, g, hc[0] + 4, hc[1] - 2, 'eye', brow='sk0', size=2.6)
        for k in range(3):                                                           # wrinkles on the neck
            f.line((hc[0] - 6 + k * 3, hc[1] + 3), (hc[0] - 5 + k * 3, hc[1] + 7), 'sk1', 1)

    def deco_front(c):
        if clip == 'attack' and n in (3, 4, 5):
            x = c.bx + 24 + g['dx'] * .5
            dust(f, rng, x, [0, 0, 0, .5, 1, .7][n], 'dust')
            bubbles(f, rng, x, AY - 2, 8 * [0, 0, 0, .5, 1, .7][n])

    return draw_quad(f, p, g, dict(
        height=14, leg=(8, 8), thick=1.35, barrel=(20, 11), rump=(14, 9), hump=(6, -3, 9, 7), feet=[-16, 14, -8, 21],
        body=['sk0', 'sk1', 'sk2', 'sk3'], belly=['bel0', 'bel1', 'bel2'], far=['far0', 'far1', 'far2'],
        near=['sk0', 'sk1', 'sk2', 'sk3', 'sk4'], hoof=['hf0', 'hf1'], tail=tail, deco_back=deco_back, deco_front=deco_front, head=head))


# ----------------------------------------------------------------------------------------------
# Lantern Angler: a walking anglerfish. A bulb of dark flesh, a mouth of needles, fins for feet and a glowing lure on a stalk.
# ----------------------------------------------------------------------------------------------
ANGLER = Palette({
    'bd0': '#0c1c2e', 'bd1': '#173a52', 'bd2': '#2f5a78', 'bd3': '#5a8aa6', 'bd4': '#8cb8c8', 'bl0': '#566a78', 'bl1': '#8aa0a8', 'bl2': '#c8dcdc',
    'fn0': '#102a40', 'fn1': '#265068', 'fn2': '#4e8098', 'far0': '#08141f', 'far1': '#10283a', 'far2': '#1c405a',
    'lu0': '#168080', 'lu1': '#44e4cc', 'lu2': '#b4fff0', 'lu3': '#fdfffc', 'tooth': '#f4f0dc', 'tooth2': '#a8a284',
    'eye': '#f8e47a', 'eye2': '#fffbd0', 'socket': '#04080f', 'mouth': '#3a0e1c', 'tongue': '#c8505e', 'spine': '#6aa0b8', 'bub': '#cdeef4', 'dust': '#5a8494',
})


def angler(clip, n):
    f = Frame(ANGLER)
    p = ANGLER
    rng = rng_for('angler', clip, n)
    g = quad_gait(clip, n)
    lie = g['lie']
    flare = [0, 0, 0, 0, 0, 0][n % 6] if clip == 'idle' else 0.
    lure = 1.
    gape = g['jaw']
    if clip == 'idle':
        lure = [1, 1.1, 1.25, 1.1, 1, .95][n]
    elif clip == 'walk':
        lure = [1, 1, 1.1, 1.2, 1.1, 1, 1, 1][n]
    elif clip == 'attack':
        lure = [1.3, 1.7, 2.2, 2.6, 2.1, 1.4, 1.1, 1][n]       # the lure swells in the windup, then flashes
        gape = [0, .2, .5, 1., .8, .3, 0, 0][n]
    elif clip == 'hurt':
        lure = [.5, .7, .9, 1][n]
    elif clip == 'die':
        lure = [.6, .5, .4, .3, .2, .15, .1, 0][n]
    bx = 43 + g['dx'] * .8
    by = AY - 26 - g['lift'] + g['crouch'] * .6 + lie * 8
    tilt = g['tilt'] * .6 - lie * 1.2
    cx_ = (bx, by)

    def at(x, y):
        a, b = rotate(x, y, -tilt)
        return bx + a, by + b

    ground = AY - 1
    # tail fan, behind the body
    tw = math.sin(n * 1.0 + (1.5 if clip == 'walk' else 0)) * (3 if clip in ('walk', 'attack') else 1.5) * (1 - lie)
    tb = at(-17, 2)
    fan = polygon([tb, at(-27, -11 + tw), at(-31, -3 + tw * .6), at(-31, 7 + tw * .4), at(-26, 14 + tw * .2)])
    f.a[mc.dilate(fan) & ~fan] = p['ol']
    f.paint((fan, gradient(fan, *tb, *at(-31, 0))[1]), p.ramp('fn0', 'fn1', 'fn2'), outline=False, dither=.4)
    for k in range(5):
        f.line(tb, at(-29, -9 + k * 5 + tw * (1 - k * .15)), 'fn2', 1)
    # far fin-leg
    def fin_leg(hip, foot, ramp, big=1.):
        knee = ik(hip, foot, 8, 8, 1)
        f.paint(capsule(hip, knee, 3.8 * big, 2.6 * big), ramp, dither=.35)
        f.paint(capsule(knee, foot, 2.6 * big, 2 * big), ramp, dither=.35)
        f.paint(ellipsoid(foot[0] + 1.5, foot[1] - .5, 5 * big, 1.9), ramp, dither=.3)
        for k in (-1, 0, 1):
            f.line((foot[0] + 1.5 + k * 3, foot[1]), (foot[0] + 3 + k * 4, foot[1] - 1), 'fn0', 1)
    feet = [(bx - 7 + g['fx'][0], ground - g['fl'][0] - lie * 12), (bx + 8 + g['fx'][2], ground - g['fl'][2] - lie * 14)]
    fin_leg(at(-4, 9), feet[0], p.ramp('far0', 'far1', 'far2'))
    # body: a big round bulb, pale belly, spines along the back
    body = ellipsoid(*at(0, 0), 21, 16.5, tilt)
    belly = ellipsoid(*at(2, 9), 15, 6, tilt)
    f.a[mc.dilate(body[0]) & ~body[0]] = p['ol']
    f.paint(body, p.ramp('bd0', 'bd1', 'bd2', 'bd3', 'bd4'), outline=False, dither=.5)
    f.paint((belly[0] & body[0], np.clip(belly[1] * .8 + .1, 0, 1)), p.ramp('bl0', 'bl1', 'bl2'), outline=False, dither=.4)
    for k in range(7):
        t = k / 6
        sx, sy = at(lerp(-15, 8, t), lerp(-6, -15.5, math.sin(t * math.pi * .55)))
        tri = polygon([(sx - 1.6, sy + 1), (sx - .5, sy - 5 - (k % 2) * 2), (sx + 1.8, sy + 1)])
        f.a[mc.dilate(tri) & ~tri] = p['ol']
        f.a[tri] = p['spine']
    for k in range(10):                                           # speckles of bioluminescence
        x, y = at(-14 + rng.uniform(0, 26), -8 + rng.uniform(0, 12))
        if k % 3 == 0:
            f.dots([(x, y)], 'lu0')
    fin_leg(at(6, 9), feet[1], p.ramp('fn0', 'fn1', 'fn2', 'bd3'))
    # pectoral fin on the flank
    px, py = at(-2, 3)
    fl = math.sin(n * .9) * 1.5
    pect = polygon([(px, py - 3), (px - 9, py + 3 + fl), (px - 6, py + 9 + fl), (px + 2, py + 4)])
    f.a[mc.dilate(pect) & ~pect] = p['ol']
    f.a[pect] = p['fn2']
    # head end: a huge mouth full of needles, a big pale eye, the lure stalk over it
    hx, hy = at(15, -2)
    open_ = gape * 8
    top = ellipsoid(hx + 3, hy - 1 - open_ * .35, 9.5, 7.4, tilt - .15 * gape)
    low = ellipsoid(hx + 3, hy + 6 + open_ * .65, 9.5, 5.6, tilt + .12 * gape)
    inside = ellipsoid(hx + 5, hy + 3 + open_ * .15, 8, 2.4 + open_ * .5)
    f.flat(inside[0], 'mouth', outline=True)
    if gape > .15:
        f.flat(ellipsoid(hx + 5, hy + 5 + open_ * .45, 4.6, 1.2 + open_ * .1)[0], 'tongue')
    f.paint(low, p.ramp('bd0', 'bd1', 'bd2', 'bd3'), outline=True, dither=.4)
    f.paint(top, p.ramp('bd0', 'bd1', 'bd2', 'bd3', 'bd4'), outline=True, dither=.4)
    for k in range(6):                                            # needle teeth, uppers pointing down, lowers pointing up
        tx = hx - 1 + k * 2.6
        f.line((tx, hy + 1 + open_ * .1 - 1), (tx + .6, hy + 5 + open_ * .1), 'tooth', 1)
        f.line((tx + 1, hy + 6 + open_ * .5 + 1), (tx + .6, hy + 2 + open_ * .45), 'tooth2' if k % 2 else 'tooth', 1)
    ex, ey = hx + 3, hy - 5 - open_ * .3
    eyes = g['eyes']
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    elif eyes == 'blink':
        f.line((ex - 3, ey), (ex + 3, ey), 'socket', 1)
    else:
        f.flat(ellipsoid(ex, ey, 4, 4)[0], 'eye', outline=True)
        f.flat(ellipsoid(ex + 1, ey, 1.8, 2.4)[0], 'socket')
        f.dots([(ex + 2, ey - 1)], 'eye2')
    # the stalk: arches from the forehead over the snout to the bulb
    sx0, sy0 = at(8, -14)
    arch = 10 + (4 if clip == 'attack' and n < 3 else 0) - (7 if clip == 'attack' and n in (3, 4) else 0)
    reach = 20 + (6 if clip == 'attack' and n in (3, 4) else 0) - (7 if clip == 'attack' and n < 3 else 0) + g['hx'] * .5
    bulb = (sx0 + reach, sy0 - arch + 14 + math.sin(n * 1.1) * 1.3 + (6 if lie else 0))
    stalk = smooth([(sx0, sy0), (sx0 + 3, sy0 - arch * 1.5), (sx0 + reach * .6, sy0 - arch * 1.4 - 3), bulb], 14)
    for a, b in zip(stalk, stalk[1:]):
        f.line(a, b, 'ol', 3)
    for a, b in zip(stalk, stalk[1:]):
        f.line(a, b, 'bd3', 1)
    r = 2.6 + lure * 1.4
    halo = ellipsoid(bulb[0], bulb[1], r + 4.5, r + 4.5)[0]
    ring = halo & ~ellipsoid(bulb[0], bulb[1], r + 1.5, r + 1.5)[0]
    f.a[ring & (DITHER_MASK)] = p['lu0']
    f.flat(ellipsoid(bulb[0], bulb[1], r, r)[0], 'lu1', outline=True, edge='lu0')
    f.flat(ellipsoid(bulb[0] - .6, bulb[1] - .6, r * .55, r * .55)[0], 'lu2')
    f.dots([(bulb[0] - 1, bulb[1] - 1)], 'lu3')
    if g['flash']:
        f.whiten()
    return fit(f.a, floor=AY + 2)


DITHER_MASK = (np.add.outer(np.arange(H), np.arange(W)) % 2 == 0)


# ----------------------------------------------------------------------------------------------
# Gnashing Moray: an eel as long as a longship, coiled in an S, olive and yellow with dark mottling and a spined ridge down its back.
# ----------------------------------------------------------------------------------------------
MORAY = Palette({
    'mo0': '#1c2a16', 'mo1': '#2f4a24', 'mo2': '#5a7a3a', 'mo3': '#92aa52', 'mo4': '#d8e888', 'bl0': '#a89a58', 'bl1': '#d0c47a', 'bl2': '#f0e8a8',
    'dor0': '#3a5a22', 'dor1': '#7a9a3a', 'spot': '#141c10', 'tooth': '#f6f2dc', 'tooth2': '#b0aa88', 'eye': '#ffe85a', 'eye2': '#fffbc8',
    'socket': '#06080a', 'mouth': '#4a1018', 'tongue': '#b8485a', 'gill': '#e0b050', 'bub': '#cdeef4', 'dust': '#6a8e94',
})


GHOST = _recolour(MORAY, {'mo0': '#26323c', 'mo1': '#4e6472', 'mo2': '#8099a8', 'mo3': '#b4cad6', 'mo4': '#ecf8fc', 'bl0': '#9aaab0', 'bl1': '#c4d4d8', 'bl2': '#f2fafa',
                          'dor0': '#3a5668', 'dor1': '#7aa0b4', 'spot': '#18222a', 'eye': '#ff6a6a', 'eye2': '#ffd8d0', 'gill': '#a0d0e0'})


def moray(clip, n, pal=None):
    pal = pal or MORAY
    f = Frame(pal)
    p = pal
    rng = rng_for('moray', clip, n)
    amp, phase, rise, jaw, lunge, eyes, flash, lying, stretch = 7., n * .9, 20., 0., 0., 'open', False, 0., 1.
    if clip == 'idle':
        amp, phase, rise = 7., n * 1.05, 21 + [0, .8, 1.6, .8, 0, -.6][n]
        eyes = 'blink' if n == 3 else 'open'
        jaw = [0, .15, .3, .15, 0, 0][n]
    elif clip == 'walk':                                          # slither: bigger waves, the body travels
        amp, phase, rise, jaw = 9., n * 1.4, [18, 17, 19, 21, 19, 17, 18, 18][n], [0, 0, .2, .3, .2, 0, 0, 0][n]
        lunge = [0, 1, 3, 4, 2, 0, -1, 0][n]
    elif clip == 'attack':                                        # coil back, strike, recover
        amp = [8, 10, 12, 3, 1, 3, 6, 7][n]
        rise = [20, 16, 12, 18, 10, 14, 19, 20][n]
        lunge = [-1, -4, -7, 4, 9, 7, 2, 0][n]
        jaw = [0, .2, .5, 1., 1., .5, .1, 0][n]
        stretch = [1, .9, .8, 1.1, 1.18, 1.1, 1, 1][n]
        phase = [0, .4, .8, 1.5, 1.5, 1.2, 1., .9][n]
        eyes = 'angry'
    elif clip == 'hurt':
        amp, rise, lunge = [12, 10, 8, 7][n], [14, 16, 18, 20][n], [-6, -4, -2, 0][n]
        jaw = [.7, .4, .1, 0][n]
        phase = [.5, 1.0, 1.5, 1.9][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead'
        lying = [0, .1, .3, .55, .8, 1, 1, 1][n]
        amp = [10, 12, 11, 9, 7, 5, 4, 4][n]
        rise = [14, 8, 4, 2, 1, 0, 0, 0][n]
        jaw = [.6, .9, .6, .4, .3, .3, .3, .3][n]
        lunge = [-4, -6, -6, -6, -6, -6, -6, -6][n]
        phase = [.5, 1.2, 2, 2.6, 3.0, 3.2, 3.2, 3.2][n]
    N = 22
    # the spine: from the tail (left, on the floor) to the head (right, raised); an S-curve whose waves travel along it
    pts = []
    for i in range(N):
        s = i / (N - 1)
        x = 12 + s * 50 * stretch + lunge * s ** 1.6
        wave = math.sin(s * 7.4 - phase) * amp * (1 - lying * .55) * (.4 + s * .6)
        y = AY - 8 - rise * (s ** 1.6) * (1 - lying) + wave * (1 - lying * .3) * .85
        pts.append((x, min(y, AY - 4 + (0 if not lying else 2)) if lying else y))
    if lying:
        pts = [(x, AY - 5 - (math.sin(i / 3 + phase) * 2.5 * (1 - i / N * .3))) for i, (x, y) in enumerate(pts)]
    radius = [1.6 + 3.7 * math.sin(min(1, (i + 3) / (N * .7)) * math.pi * .5) + (1.5 if i > N - 4 else 0) for i in range(N)]
    discs = [ellipsoid(x, y, r, r * .92) for (x, y), r in zip(pts, radius)]
    # dorsal ridge: a ragged fin along the back
    union = np.zeros((H, W), bool)
    for sh in discs:
        union |= sh[0]
    ridge = []
    for i in range(1, N - 2):
        x, y = pts[i]
        h = 3.2 + (i % 2) * 1.6 + math.sin(i * .6 + n) * .6
        ridge.append((x, y - radius[i] * .8 - h * (1 - lying * .8)))
    fin_poly = polygon([(pts[1][0], pts[1][1] - radius[1] * .6)] + ridge + [(pts[N - 3][0], pts[N - 3][1] - radius[N - 3] * .6)])
    f.a[mc.dilate(fin_poly) & ~fin_poly] = p['ol']
    f.a[fin_poly] = p['dor1']
    for i in range(2, N - 3, 2):
        f.line((pts[i][0], pts[i][1] - radius[i] * .7), ridge[i - 1], 'dor0', 1)
    f.a[mc.dilate(union) & ~union] = p['ol']
    for i, sh in enumerate(discs):
        f.paint(sh, p.ramp('mo0', 'mo1', 'mo2', 'mo3', 'mo4'), outline=False, dither=.5)
        if i % 2 == 0 and i > 1:                                  # mottling and a pale belly stripe
            x, y = pts[i]
            f.dots([(x - 1, y - 1), (x + 1, y + 1)], 'spot')
            f.dots([(x + 1, y + radius[i] * .7)], 'bl1')
    hx, hy = pts[-1]
    prev = pts[-3]
    ang = math.atan2(hy - prev[1], hx - prev[0])
    c, s = math.cos(ang), math.sin(ang)
    P = lambda u, v: (hx + u * c - v * s, hy + u * s + v * c)
    open_ = jaw * 9
    up = polygon([P(-3, -6.5), P(5, -8.5), P(14, -3.5 - open_ * .45), P(17, -.5 - open_ * .3), P(-2, 1)])
    low = polygon([P(-2, 1), P(17, 0 + open_ * .5), P(13, 4 + open_ * .85), P(2, 8 + open_ * .4), P(-3, 6)])
    f.flat(polygon([P(0, -2), P(13, -1 - open_ * .2), P(12, 1 + open_ * .5), P(0, 3)]), 'mouth', outline=True)
    if jaw > .15:
        f.flat(ellipsoid(*P(8, 2 + open_ * .3), 3.4, 1.1)[0], 'tongue')
    for shape, ramp in ((low, ('mo0', 'mo1', 'bl0', 'bl1')), (up, ('mo0', 'mo1', 'mo2', 'mo3'))):
        f.a[mc.dilate(shape) & ~shape] = p['ol']
        f.paint((shape, gradient(shape, *P(0, -8), *P(0, 8))[1]), p.ramp(*ramp), outline=False, dither=.4)
    for k in range(6):                                            # fangs
        u = 1 + k * 2
        f.line(P(u, 1 - open_ * .05 - 1), P(u + .3, 4.2 + open_ * .1), 'tooth', 1)
        f.line(P(u + 1, 1 + open_ * .5 + .5), P(u + .6, -2 + open_ * .25), 'tooth2' if k % 2 else 'tooth', 1)
    ex, ey = P(5, -3.6)
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    elif eyes == 'blink':
        f.line((ex - 2, ey), (ex + 2, ey), 'socket', 1)
    else:
        f.flat(ellipsoid(ex, ey, 2.6, 2.6)[0], 'eye', outline=True)
        f.line((ex, ey - 2), (ex, ey + 2), 'socket', 1)
        if eyes == 'angry':
            f.line((ex - 3, ey - 3.2), (ex + 3, ey - 1.6), 'mo0', 1)
    f.dots([P(-1.5, 2.5), P(-1.5, 4.5)], 'gill')
    if clip == 'attack' and n in (3, 4):
        bubbles(f, rng, hx + 10, hy, 7)
    if flash:
        f.whiten()
    return fit(f.a, floor=AY + 2)


def ghostmaw(clip, n):
    return moray(clip, n, GHOST)


# ----------------------------------------------------------------------------------------------
# Siren: Ran's handmaiden. A pale singer with streaming hair and a fishtail, hovering in the water; she sings in rings of rose light.
# ----------------------------------------------------------------------------------------------
SIREN = Palette({
    'sk0': '#2a4a6a', 'sk1': '#5a86a6', 'sk2': '#98bcd4', 'sk3': '#cce2f0', 'sk4': '#f0f8ff', 'far0': '#1a3248', 'far1': '#3a5e7a', 'far2': '#6a92ae',
    'hr0': '#1a1040', 'hr1': '#3a2a7a', 'hr2': '#6a4ab8', 'hr3': '#a888f0', 'sc0': '#0e4a5a', 'sc1': '#1f8a96', 'sc2': '#58d0c8', 'sc3': '#c8fff0',
    'fn0': '#6a1a5a', 'fn1': '#c0449a', 'fn2': '#ff9ae0', 'eye': '#ffb8f0', 'eye2': '#ffffff', 'socket': '#1a0a2a', 'mouth': '#5a1030',
    'sg0': '#ff6ad2', 'sg1': '#ffb8ee', 'sg2': '#fffefd', 'pearl': '#fff4f0', 'pearl2': '#d8bcc8', 'bub': '#cdeef4',
})


def siren(clip, n):
    f = Frame(SIREN)
    p = SIREN
    rng = rng_for('siren', clip, n)
    cx, cy = 46., 44.
    bob = 0.; sway = 0.; arms = 0.; mouth = 0.; song = 0.; eyes = 'open'; flash = False; fall = 0.; tail_wave = 0.; lean = 0.; dx = 0.
    if clip == 'idle':
        bob = [0, -1, -2, -1, 0, 1][n]; tail_wave = n * 1.05; sway = [0, .5, 1, .5, 0, -.5][n]; eyes = 'blink' if n == 3 else 'open'
    elif clip == 'walk':
        bob = [0, -1, -3, -4, -3, -1, 0, 1][n]; tail_wave = n * 1.5; lean = .12; dx = [0, 1, 2, 3, 2, 1, 0, 0][n]; sway = 1.5
    elif clip == 'attack':
        arms = [.2, .5, .9, 1., .9, .5, .2, 0][n]
        mouth = [0, .3, .7, 1., 1., .6, .2, 0][n]
        song = [0, 0, .4, 1., 1.6, 2.2, 2.6, 0][n]
        bob = [0, -1, -2, -3, -3, -2, -1, 0][n]; dx = [0, -1, -2, 1, 2, 1, 0, 0][n]; tail_wave = n * 1.8; lean = [-.05, -.1, -.14, .05, .08, .05, 0, 0][n]
    elif clip == 'hurt':
        dx = [-5, -3, -1, 0][n]; lean = [-.25, -.15, -.05, 0][n]; bob = [-2, -1, 0, 0][n]; flash = n == 0
        eyes = 'hurt' if n < 3 else 'open'; mouth = [.8, .5, .2, 0][n]; tail_wave = n * 2.2; sway = [3, 2, 1, 0][n]
    elif clip == 'die':
        flash = n == 0; eyes = 'dead'
        fall = [0, .1, .3, .55, .8, 1, 1, 1][n]
        dx = [0, -2, -4, -5, -6, -6, -6, -6][n]
        lean = [0, -.2, -.5, -.8, -1.1, -1.35, -1.45, -1.45][n]
        mouth = [.8, .6, .3, .1, 0, 0, 0, 0][n]; tail_wave = [0, 1, 1.6, 2, 2.2, 2.2, 2.2, 2.2][n]; sway = [2, 1.5, 1, .5, 0, 0, 0, 0][n]
    cx += dx
    cy += bob + fall * (AY - 17 - cy)

    def at(x, y):
        a, b = rotate(x, y, -lean)
        return cx + a, cy + b

    # tail: from the hips, curving down and back, ending in a fan fin
    hip = at(-2, 14)
    tpts = smooth([hip, at(-6, 22), at(-12 - sway, 28 + math.sin(tail_wave) * 3), at(-17 - sway, 31 + math.sin(tail_wave + 1) * 5), at(-22 - sway, 29 + math.sin(tail_wave + 2) * 6)], 14)
    discs = [ellipsoid(x, y, lerp(7, 2.2, i / 13), lerp(6.4, 2, i / 13)) for i, (x, y) in enumerate(tpts)]
    fin_c = tpts[-1]
    fin = polygon([tpts[-2], (fin_c[0] - 8, fin_c[1] - 9 + math.sin(tail_wave + 1) * 2), (fin_c[0] - 12, fin_c[1] - 1), (fin_c[0] - 9, fin_c[1] + 8 + math.sin(tail_wave) * 2), tpts[-1]])
    f.a[mc.dilate(fin) & ~fin] = p['ol']
    f.a[fin] = p['fn1']
    for k in range(4):
        f.line(tpts[-2], (fin_c[0] - 9 - k * .5, fin_c[1] - 8 + k * 5), 'fn2', 1)
    chain_paint(f, discs, p.ramp('sc0', 'sc1', 'sc2', 'sc3'), dither=.45)
    for i, (x, y) in enumerate(tpts[:10]):                        # scales: little arcs
        if i % 2 == 0:
            f.dots([(x - 1, y), (x + 1, y + 1), (x, y - 2)], 'sc3')
    # far arm
    sh_far, sh_near = at(-4, -4), at(5, -3)
    up = arms
    def arm(sh, ramp, far):
        hand = at(8 + up * 6 + (0 if far else 3), -4 - up * 13 + (3 if far else 5) * (1 - up) + (1 if far else 0))
        elbow = ik(sh, hand, 8, 8, -1)
        f.paint(capsule(sh, elbow, 2.8, 2.2), ramp, dither=.35)
        f.paint(capsule(elbow, hand, 2.2, 1.8), ramp, dither=.35)
        f.paint(ellipsoid(hand[0], hand[1], 2.4, 2.2), ramp, dither=.3)
        return hand
    arm(sh_far, p.ramp('far0', 'far1', 'far2'), True)
    # hair first (behind): a long wave streaming to the left
    hc = at(3, -17)
    for k in range(7):
        sw = math.sin(n * .9 + k * 1.3) * 2 + sway
        base = (hc[0] - 6 + k * 1.6, hc[1] - 5 + (k % 3))
        pts = smooth([base, (base[0] - 7, base[1] + 2 - sw * .3), (base[0] - 15 - sw, base[1] + 8 + sw), (base[0] - 21 - sw * 1.3, base[1] + 18 + k % 3 * 2), (base[0] - 22 - sw, base[1] + 27 - k)], 12)
        strand(f, pts, ['hr1', 'hr2', 'hr3', 'hr1'][k % 4], 2)
    # torso: pale skin, a scaled top, a pearl at the throat
    torso = ellipsoid(*at(0, 2), 8.2, 12.5, lean)
    waist = ellipsoid(*at(-1, 11), 6.6, 5.8, lean)
    f.a[mc.dilate(torso[0] | waist[0]) & ~(torso[0] | waist[0])] = p['ol']
    f.paint(torso, p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4'), outline=False, dither=.5)
    f.paint(waist, p.ramp('sk0', 'sk1', 'sk2', 'sk3'), outline=False, dither=.4)
    top = ellipsoid(*at(1, -1), 8.6, 6.2, lean)
    f.paint((top[0] & torso[0], top[1]), p.ramp('sc0', 'sc1', 'sc2', 'sc3'), outline=False, dither=.5)
    for k in range(5):
        x, y = at(-4 + k * 2.2, -3 + (k % 2) * 3)
        f.dots([(x, y)], 'sc3')
    px, py = at(2, -8)
    f.dots([(px, py), (px + 1, py), (px, py + 1)], 'pearl')
    # head
    head = ellipsoid(*hc, 6.6, 7.4, lean)
    neck = capsule(at(0, -9), hc, 3, 2.8)
    chain_paint(f, [neck, head], p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4'), dither=.45)
    for k in range(4):                                            # fringe over the brow, and a long forelock
        x0, y0 = hc[0] - 4 + k * 2.2, hc[1] - 6
        strand(f, smooth([(x0, y0), (x0 - 1, y0 + 4), (x0 - 4, y0 + 9 + k)], 6), ['hr2', 'hr3'][k % 2], 1, outline=False)
    ex, ey = hc[0] + 2.4, hc[1] - .5
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    elif eyes == 'blink':
        f.line((ex - 2, ey), (ex + 2, ey), 'socket', 1)
    elif eyes == 'hurt':
        f.dots([(ex - 1, ey - 1), (ex, ey), (ex + 1, ey + 1), (ex + 1, ey - 1), (ex - 1, ey + 1)], 'socket')
    else:
        f.flat(ellipsoid(ex, ey, 2.4, 2.1)[0], 'socket')
        f.dots([(ex, ey), (ex + 1, ey)], 'eye')
    if mouth > 0:
        f.flat(ellipsoid(hc[0] + 4, hc[1] + 3.8, 1.6 + mouth, .8 + mouth * 2.2)[0], 'mouth', outline=True)
    else:
        f.line((hc[0] + 3, hc[1] + 4), (hc[0] + 5.6, hc[1] + 3.6), 'mouth', 1)
    near_hand = arm(sh_near, p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4'), False)
    # the song: rings of rose light leaving her mouth, widening
    if song > 0:
        for k in range(3):
            r = 4 + k * 5 + song * 2.6
            cxs, cys = hc[0] + 9 + k * 4 + song * 2, hc[1] + 3
            ring = ellipsoid(cxs, cys, r * .55, r)[0] & ~ellipsoid(cxs, cys, r * .55 - 1.6, r - 1.6)[0] & (cxs - 1 <= XXg)
            f.a[ring & (np.add.outer(np.arange(H), np.arange(W)) % (2 if k else 1) == 0)] = p['sg1' if k == 0 else 'sg0']
        f.dots([(hc[0] + 10 + song * 2, hc[1] + 3)], 'sg2')
    if flash:
        f.whiten()
    return fit(f.a, floor=AY + 2)


XXg = np.tile(np.arange(W) + .5, (H, 1))


# ----------------------------------------------------------------------------------------------
# The Kraken: a great violet mantle over two yellow eyes and a ring of tentacles; two long arms rise and slam down.
# ----------------------------------------------------------------------------------------------
KRAKEN = Palette({
    'kr0': '#150c28', 'kr1': '#2c1a50', 'kr2': '#4a2c80', 'kr3': '#7a54b8', 'kr4': '#a888e0', 'kr5': '#d0c0f4',
    'far0': '#0e0820', 'far1': '#1c1038', 'far2': '#2e1c58', 'suck': '#e8d0f0', 'suck2': '#fff0f8', 'sp0': '#c04a90', 'sp1': '#ff8ac8',
    'eye': '#ffe040', 'eye2': '#fff8b0', 'socket': '#050210', 'beak0': '#3a2a1a', 'beak1': '#9a7a4a', 'ink': '#0a0618', 'bio': '#6affd8',
    'dust': '#6a5a9a', 'bub': '#cdeef4',
})


def kraken(clip, n):
    f = Frame(KRAKEN)
    p = KRAKEN
    rng = rng_for('kraken', clip, n)
    bx, by = 38., AY - 30.
    mantle_dy, mantle_lean, up, slam, eyes, flash, die, wave, dx = 0., -.45, 0., 0., 'open', False, 0., n * .9, 0.
    if clip == 'idle':
        mantle_dy = [0, -.5, -1, -.5, 0, .5][n]; eyes = 'blink' if n == 3 else 'open'
    elif clip == 'walk':
        mantle_dy = [0, -1, -3, -4, -2, 0, 1, 0][n]; wave = n * 1.6; dx = [0, 1, 2, 3, 2, 1, 0, 0][n]
    elif clip == 'attack':
        up = [.4, .8, 1., -.3, -.6, -.3, 0, 0][n]
        slam = [0, 0, 0, .5, 1., .7, .3, 0][n]
        mantle_lean = [-.5, -.6, -.7, -.2, -.1, -.3, -.4, -.45][n]
        dx = [-1, -2, -3, 3, 6, 4, 1, 0][n]; mantle_dy = [0, -1, -3, 1, 3, 1, 0, 0][n]; eyes = 'angry'; wave = n * 2
    elif clip == 'hurt':
        dx = [-4, -3, -1, 0][n]; mantle_lean = [-.8, -.65, -.5, -.45][n]; mantle_dy = [2, 1, 0, 0][n]; flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'; wave = n * 2.4
    elif clip == 'die':
        flash = n == 0; eyes = 'dead'
        die = [0, .1, .3, .5, .7, .85, 1, 1][n]
        dx = [0, -2, -3, -4, -4, -4, -4, -4][n]; mantle_lean = -.45 - die * .5; wave = n * .5
    bx += dx
    by += mantle_dy + die * 12
    c, s = math.cos(mantle_lean), math.sin(mantle_lean)

    def M(x, y):
        a, b = rotate(x, y, -mantle_lean)
        return bx + a, by + b

    ground = AY - 1

    def tentacle(root, tip, curl, base_r, ramp, far=False, rise=0., suckers=True):
        """A chain of discs from the root to a tip on the floor, bowed by `curl` and rippling with `wave`."""
        m = 11
        pts = []
        for i in range(m):
            t = i / (m - 1)
            x = lerp(root[0], tip[0], t) + math.sin(t * 3.2 + wave) * 2.2 * t * (1 - die * .7)
            y = lerp(root[1], tip[1], t) - math.sin(t * math.pi) * curl - rise * math.sin(t * math.pi * .8)
            pts.append((x, min(y, ground - 1.4)))
        discs = [ellipsoid(x, y, lerp(base_r, 1.5, (i / (m - 1)) ** .8), lerp(base_r, 1.5, (i / (m - 1)) ** .8) * .9) for i, (x, y) in enumerate(pts)]
        chain_paint(f, discs, ramp, dither=.5)
        if suckers:
            for i in range(2, m - 1, 2):
                x, y = pts[i]
                f.dots([(x, y + lerp(base_r, 1.5, i / (m - 1)) * .55)], 'suck')
        return pts

    root_far, root_near = M(6, 10), M(14, 12)
    far = [(-24, 12), (-5, 6), (24, 8)]
    # far tentacles (darker, behind)
    for k, (tx, c_) in enumerate([(-22, 8), (-6, 5), (22, 9)]):
        tentacle((bx - 4 + k * 5, by + 16), (bx + tx * 1.05 + 6, ground - 1 - k % 2), c_, 5.2, p.ramp('far0', 'far1', 'far2'), far=True)
    # the mantle: a tall dome, spots of light along its back
    mantle = ellipsoid(*M(-2, -14), 19.5, 26, mantle_lean)
    skirt = ellipsoid(*M(2, 8), 20, 9.5, mantle_lean * .4)
    f.a[mc.dilate(mantle[0] | skirt[0]) & ~(mantle[0] | skirt[0])] = p['ol']
    f.paint(mantle, p.ramp('kr0', 'kr1', 'kr2', 'kr3', 'kr4', 'kr5'), outline=False, dither=.5)
    f.paint(skirt, p.ramp('kr0', 'kr1', 'kr2', 'kr3', 'kr4'), outline=False, dither=.5)
    for k in range(9):
        x, y = M(-14 + k * 2.2 + rng.uniform(-1, 1), -30 + (k % 3) * 8 + rng.uniform(0, 8))
        f.dots([(x, y), (x + 1, y)], 'sp1' if k % 2 else 'sp0')
    for k in range(5):
        x, y = M(-12 + k * 3.8, -20 + math.sin(k) * 5)
        f.dots([(x, y)], 'bio')
    # near tentacles on the floor
    near = [(-30, 8), (-14, 6), (6, 4), (30, 10)]
    for k, (tx, c_) in enumerate(near):
        rise_ = 3 * math.sin(wave + k * 1.7) * (1 if clip in ('walk', 'idle') else .4)
        tentacle((bx + 6 + k * 5, by + 18), (bx + tx * 1.0 + 18, ground - 0.5 - (k % 2)), c_, 6.2, p.ramp('kr0', 'kr1', 'kr2', 'kr3', 'kr4'), rise=rise_)
    # two long arms that rise and slam
    for k, side in enumerate((0, 1)):
        root = M(10 + side * 7, 6)
        if clip == 'attack':
            high = (root[0] - 6 + side * 6, root[1] - 42 - up * 8 + side * 3)
            low_ = (bx + 28 + slam * 12 + side * 9, ground - 1)
            if up >= 0:
                tip = (lerp(root[0] + 10 + side * 7, high[0], up), lerp(root[1] + 8, high[1], up))
            else:
                tip = (lerp(low_[0] - 8, low_[0], -up * 1.6), lerp(root[1] + 8, low_[1], min(1, -up * 1.8 + .2)))
        else:
            tip = (bx + 26 + side * 9, ground - 1)
        tentacle(root, tip, 7 if clip != 'attack' else 3, 6.4, p.ramp('kr0', 'kr1', 'kr2', 'kr3', 'kr4', 'kr5'), rise=0 if clip == 'attack' else 2)
    # head: a bulge with two huge eyes and a beak
    head = ellipsoid(*M(16, 0), 12.5, 10.5, mantle_lean * .5)
    f.paint(head, p.ramp('kr0', 'kr1', 'kr2', 'kr3', 'kr4'), outline=True, dither=.45)
    beak = polygon([M(24, 4), M(31, 9 + (1 if clip == 'attack' and n in (3, 4) else 0)), M(23, 11)])
    f.a[mc.dilate(beak) & ~beak] = p['ol']
    f.a[beak] = p['beak1']
    f.dots([M(26, 7)], 'beak0')
    for (ex_, ey_, r_) in ((19, -3.5, 5.2), (11, -5, 3.8)):
        ex, ey = M(ex_, ey_)
        if eyes == 'dead':
            eye_dead(f, ex, ey)
        elif eyes == 'blink':
            f.line((ex - r_, ey), (ex + r_, ey), 'socket', 1)
        else:
            f.flat(ellipsoid(ex, ey, r_, r_ * .92)[0], 'eye', outline=True)
            f.flat(ellipsoid(ex + 1, ey, 1.4, r_ * .8)[0], 'socket')
            f.dots([(ex - 1, ey - 2)], 'eye2')
            if eyes == 'angry':
                f.line((ex - r_, ey - r_ - 1), (ex + r_, ey - r_ + 1 + (1 if ex_ > 15 else 0)), 'kr0', 2)
    if slam > 0:
        x = bx + 38 + slam * 8
        dust(f, rng, x, slam, 'dust')
        bubbles(f, rng, x, AY - 2, 12 * slam)
        for k in range(-4, 5):
            f.dots([(x + k * 4, AY - 1 - abs(k) % 2)], 'ink')
    if die >= .5:                                                  # a cloud of ink spreads round the body
        for k in range(int(26 * die)):
            f.dots([(bx + rng.uniform(-30, 34), AY - 2 - rng.uniform(0, 10) * die)], 'ink')
    if flash:
        f.whiten()
    return fit(f.a, floor=AY + 2)


# ----------------------------------------------------------------------------------------------
# Rendering and PixelFlow plumbing (same contract as scripts/make_crag_sprites.py)
# ----------------------------------------------------------------------------------------------
_PAIRS = {'draugr': ('draugr', 'DRAUG'), 'angler': ('angler', 'ANGLER'), 'moray': ('moray', 'MORAY'), 'siren': ('siren', 'SIREN'),
          'shellback': ('shellback', 'SHELL'), 'kraken': ('kraken', 'KRAKEN'), 'hvitserk': ('hvitserk', 'CAPT'), 'ghostmaw': ('ghostmaw', 'GHOST')}
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
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#0e3048')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def meta_path():
    return ASSETS / 'deep.txt'


def build(kinds, replace=False):
    path = meta_path()
    meta = json.loads(path.read_text()) if path.exists() else {}
    known = meta.get('sprites', {})
    clash = [k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist (ids in deep.txt). Use export to preserve edits; --replace discards them.')
    for kind in clash:
        api('delete', {'sprite_id': known[kind]})
    made = {}
    for kind in kinds:
        frames = render(kind)
        bad = bounds_report(kind, frames)
        if bad:
            raise SystemExit(f'{kind} touches the canvas edge: {bad}')
        palette = DRAWERS[kind][1].hex
        np.savez_compressed(RAW / f'deep_{kind}_raw.npz', **frames)
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
            sheet = Image.new('RGBA', (8 * W, H), '#0e3048')
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
            dest = ROOT / 'test-results/deep-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'deep_{kind}.png', optimize=True)
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': saved}
    path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/deep_<kind>.png and deep.txt')


def verify(kinds):
    """The exported atlas must equal the freshly rendered frames pixel for pixel."""
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        atlas = Image.open(ASSETS / f'deep_{kind}.png').convert('RGBA')
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
    sheet = Image.new('RGBA', (len(cells) * W, H + 12), '#0e3048')
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
        directory = next((a for a in sys.argv[2:] if a not in DRAWERS and not a.startswith('--')), ROOT / 'test-results/deep-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_deep_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...] | verify [kind...] | view kind out.png clip:n ...')
