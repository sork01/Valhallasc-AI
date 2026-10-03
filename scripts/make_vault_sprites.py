#!/usr/bin/env python3
"""makesprites workflow for the Undervault monsters: preview | build [--replace] | export | verify.

Seven kinds share the Emberfall Crags contract (scripts/make_crag_sprites.py): one 96x96 frame, a foot anchor at (48, 90),
right-facing art (the game mirrors it) and five clips (idle 6, walk 8, attack 8, hurt 4, die 8) so client/field.js drives
them with the Ironhide's state machine: walk frames 2-4 are the hop, 5-7 the landing, attack 0-2 the windup, 3-5 the
lunge (a ranged kind releases its missile on frame 3), 6-7 the recovery.

  thrall      Vault Thrall: a skeleton in rotted rags with a cracked shield and a rusty sword (melee trash)
  archer      Bone Archer: a hooded skeleton with a quiver and a bow (ranged trash)
  acolyte     Hollow Acolyte: a skull in a violet hood and robe, a staff with a glowing orb (ranged trash)
  gatewarden  Hrolf Bonegate: an armoured skeleton jarl with horned helm, round shield and battle-axe (boss 1)
  choir       Valka, the Hollow Choir: a floating veiled lich in a teal robe who sings (boss 2)
  colossus    Ironwake: a granite construct with glowing runes (boss 3)
  hollowking  Haldor, the Hollow King: a crowned skeleton king in a ragged cape with a greatsword (boss 4)

The skeletons share one rig (two-bone IK legs and arms, a ribcage, a skull) lit from the upper left like every other kind;
the toolkit (shaded ellipsoids and capsules, a dithered ramp per material, an outline per part) comes from
make_crag_sprites.py. `build` saves ONE new 34-frame PixelFlow sprite per kind (valhallasc_vault_<kind>_all) and refuses
existing names unless --replace is given (--replace discards hand edits made in the editor). `export` reads the editor frames
back, so edits survive, and writes client/assets/vault_<kind>.png plus vault.txt. `verify` proves the atlas equals the render.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_crag_sprites as mc  # noqa: E402
from make_crag_sprites import (AX, AY, CLIPS, DITHER, H, W, XX, YY, Frame, Palette, api, capsule, ellipsoid,  # noqa: E402
                               gradient, lerp, polygon, rgba, rng_for)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
PREFIX = 'valhallasc_vault_'
KINDS = ['thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking']
RAW = ROOT / 'scripts'
BONE = {'b0': '#2b2631', 'b1': '#6d6556', 'b2': '#a59c84', 'b3': '#d8cfb4', 'b4': '#f3ecd4', 'sock': '#0c0a10'}
METAL = {'m0': '#262830', 'm1': '#555a66', 'm2': '#8a909c', 'm3': '#c4c9d2', 'm4': '#eef2f8'}
WOOD = {'wd0': '#2a1c12', 'wd1': '#4f3622', 'wd2': '#7a5a38', 'wd3': '#a0794c'}
EFFECT = {'slash': '#e6f2ff', 'dust': '#8a8478', 'dust2': '#b8b0a0'}


def palette_of(*groups, **extra):
    colors = {}
    for g in groups:
        colors.update(g)
    colors.update(extra)
    return Palette(colors)


def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def ik(a, target, l1, l2, flip=1):
    """Two-bone IK in the plane: the joint between `a` and `target` (distances l1, l2), bending to the `flip` side."""
    dx, dy = target[0] - a[0], target[1] - a[1]
    d = min(max(math.hypot(dx, dy), abs(l1 - l2) + .01), l1 + l2 - .01)
    ang = math.atan2(dy, dx)
    A = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    joint = (a[0] + l1 * math.cos(ang + flip * A), a[1] + l1 * math.sin(ang + flip * A))
    end = (a[0] + d * math.cos(ang), a[1] + d * math.sin(ang))
    return joint, end


class Rig:
    """Local coordinates: x forward (right), y UP, in units of S pixels, origin between the feet on the ground."""

    def __init__(self, f, S=1., x0=44., lift=0.):
        self.f, self.S, self.x0, self.lift = f, S, x0, lift

    def P(self, lx, ly=None):
        if ly is None:
            lx, ly = lx
        return (self.x0 + lx * self.S, AY - (ly + self.lift) * self.S)

    def limb(self, a, b, r0, r1, ramp, dither=.5, outline=True):
        self.f.paint(capsule(self.P(a), self.P(b), r0 * self.S, r1 * self.S), ramp, outline=outline, dither=dither)

    def blob(self, c, rx, ry, ramp, angle=0., dither=.55, outline=True):
        x, y = self.P(c)
        self.f.paint(ellipsoid(x, y, rx * self.S, ry * self.S, -angle), ramp, outline=outline, dither=dither)

    def poly(self, pts, name, outline=False, edge=None):
        self.f.flat(polygon([self.P(p) for p in pts]), name, outline=outline, edge=edge)

    def shaded(self, pts, ramp, lo=.2, hi=.95, outline=True, flip=False, dither=.45):
        P = [self.P(p) for p in pts]
        mask = polygon(P)
        xs, ys = [q[0] for q in P], [q[1] for q in P]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        self.f.paint(gradient(mask, x1 if flip else x0, y1, x0 if flip else x1, y0, lo, hi), ramp, outline=outline, dither=dither)

    def dots(self, pts, name):
        self.f.dots([self.P(p) for p in pts], name)

    def line(self, a, b, name, width=1):
        self.f.line(self.P(a), self.P(b), name, width)


def pose(**kw):
    base = dict(hip=(0, 29), lean=0., head=(0, 0), tilt=0., foot_n=(7, 0), foot_f=(-7, 0), hand_n=(8, 34), hand_f=(-4, 33),
                weapon=0., jaw=0., eyes='open', glow=1., arm_n_flip=1, arm_f_flip=1, torso=20., float=0.)
    base.update(kw)
    return base


def skeleton(f, p, rig, ps, style, clip, n):
    """Draws a whole figure for pose `ps`; `style` carries the per-kind parts (see the STYLE dicts below)."""
    bone = p.ramp('b0', 'b1', 'b2', 'b3', 'b4')
    darkbone = p.ramp('b0', 'b0', 'b1', 'b2', 'b3')
    cloth = p.ramp(*style['cloth']) if style.get('cloth') else bone
    hx, hy = ps['hip']
    lean = ps['lean']
    chest = (hx + math.sin(lean) * ps['torso'] * .55, hy + math.cos(lean) * ps['torso'] * .55)
    neck = (hx + math.sin(lean) * ps['torso'], hy + math.cos(lean) * ps['torso'])
    hv = rot((2.4 + ps['head'][0], 6.4 + ps['head'][1]), lean * .85 + ps['tilt'] * .5)
    head = (neck[0] + hv[0], neck[1] + hv[1])
    ax, ay = rot((1, 0), lean)
    sh_n = (neck[0] + 1.0 * ax, neck[1] - 2.8 + ay)
    sh_f = (neck[0] - 1.6 * ax, neck[1] - 2.4 - ay)
    hip_n, hip_f = (hx + 1.6, hy - 1), (hx - 1.6, hy - 1)
    L1, L2 = style.get('thigh', 14.), style.get('shin', 14.)
    arm1, arm2 = style.get('upper', 11.5), style.get('fore', 11.)
    elbow_f, hand_f = ik(sh_f, ps['hand_f'], arm1, arm2, flip=ps['arm_f_flip'])
    elbow_n, hand_n = ik(sh_n, ps['hand_n'], arm1, arm2, flip=ps['arm_n_flip'])
    arm_ramp_far = cloth if style.get('sleeve') else darkbone
    arm_ramp_near = cloth if style.get('sleeve') else bone
    if style.get('behind'):
        style['behind'](rig, p, ps, neck, (hx, hy), clip, n)
    if not style.get('robe'):
        knee_f, foot_f = ik(hip_f, ps['foot_f'], L1, L2, flip=-1)
        rig.limb(hip_f, knee_f, 2.3, 2.0, darkbone, dither=.35)
        rig.limb(knee_f, foot_f, 2.0, 1.6, darkbone, dither=.35)
        rig.blob((foot_f[0] + 2, foot_f[1] + .9), 3.6, 1.6, darkbone)
    rig.limb(sh_f, elbow_f, 1.9, 1.6, arm_ramp_far, dither=.35)
    rig.limb(elbow_f, hand_f, 1.6, 1.3, arm_ramp_far, dither=.35)
    rig.blob(hand_f, 1.7, 1.7, darkbone)
    if style.get('far_hand'):
        style['far_hand'](rig, p, ps, hand_f, elbow_f, clip, n)
    if style.get('robe'):
        style['robe'](rig, p, ps, (hx, hy), neck, chest, clip, n)
    else:
        rig.blob((hx, hy - 1.5), 5.8, 3.4, bone)
        rig.limb((hx, hy), neck, 1.6, 1.5, darkbone, dither=.3)
        rig.blob(chest, 6.8, 8.6, bone, angle=lean * .6)
        for k in (-4.5, -1.8, 1.0, 3.6):                                                 # rib gaps
            a = rig.P(chest[0] - 3.4 + math.sin(lean) * k * .3, chest[1] + k)
            b = rig.P(chest[0] + 5.2 + math.sin(lean) * k * .3, chest[1] + k - .7)
            f.line(a, b, 'b0', 1)
        if style.get('torso_gear'):
            style['torso_gear'](rig, p, ps, chest, (hx, hy), neck, clip, n)
        knee_n, foot_n = ik(hip_n, ps['foot_n'], L1, L2, flip=-1)
        rig.limb(hip_n, knee_n, 2.5, 2.1, bone, dither=.4)
        rig.limb(knee_n, foot_n, 2.1, 1.7, bone, dither=.4)
        rig.blob((knee_n[0] + .6, knee_n[1]), 2.7, 2.5, bone)
        rig.blob((foot_n[0] + 2.4, foot_n[1] + 1), 4.0, 1.8, bone)
        rig.dots([(foot_n[0] + 5.2, foot_n[1] + .4), (foot_n[0] + 6.2, foot_n[1] + .4)], 'b4')
        if style.get('skirt'):
            style['skirt'](rig, p, ps, (hx, hy), clip, n)
    # --- the head
    hd = head
    jaw = ps['jaw']
    if style.get('hood'):
        style['hood'](rig, p, ps, hd, True, clip, n)
    rig.blob(hd, 6.9, 7.1, bone, angle=ps['tilt'], dither=.55)
    rig.blob((hd[0] + 3.4, hd[1] - 3.4), 3.8, 2.6, bone, dither=.45)
    jx, jy = hd[0], hd[1] - jaw
    rig.poly([(jx + 1.4, jy - 4.6), (jx + 7.6, jy - 4.4), (jx + 7.2, jy - 6.8), (jx + 2.2, jy - 7.2)], 'b2', outline=True, edge='ol')
    rig.dots([(jx + 3, jy - 5), (jx + 4.6, jy - 5), (jx + 6.2, jy - 5)], 'b4')
    eye = style.get('eye', 'glow')
    for ex, ey in ((hd[0] + 1.0, hd[1] + .6), (hd[0] + 5.4, hd[1] + .6)):
        if ps['eyes'] == 'dead':
            rig.dots([(ex - 1, ey + 1), (ex + 1, ey - 1), (ex - 1, ey - 1), (ex + 1, ey + 1)], 'sock')
        elif ps['eyes'] == 'blink':
            rig.line((ex - 1.6, ey), (ex + 1.6, ey), 'sock', 1)
        else:
            squint = ps['eyes'] == 'angry'
            rig.blob((ex, ey), 2.3, 1.9 if squint else 2.8, p.ramp('sock', 'sock'), outline=False)
            rig.dots([(ex, ey), (ex + 1, ey)] if ps['glow'] < 1.5 else [(ex, ey), (ex + 1, ey), (ex, ey + 1), (ex + 1, ey + 1)], eye)
            if squint:
                rig.line((ex - 2.6, ey + 3.2), (ex + 2.6, ey + 1.6), 'sock', 1)
    rig.dots([(hd[0] + 3.2, hd[1] - 1.8)], 'sock')
    if style.get('hood'):
        style['hood'](rig, p, ps, hd, False, clip, n)
    if style.get('head_gear'):
        style['head_gear'](rig, p, ps, hd, clip, n)
    # --- the near arm and what it carries
    rig.limb(sh_n, elbow_n, 2.0, 1.7, arm_ramp_near, dither=.4)
    rig.limb(elbow_n, hand_n, 1.7, 1.4, arm_ramp_near, dither=.4)
    rig.blob(hand_n, 2.0, 2.0, bone)
    if style.get('shoulder'):
        style['shoulder'](rig, p, ps, sh_n, sh_f, clip, n)
    if style.get('weapon'):
        style['weapon'](rig, p, ps, hand_n, elbow_n, hand_f, clip, n)
    if style.get('front'):
        style['front'](rig, p, ps, neck, (hx, hy), clip, n)
    return dict(head=hd, neck=neck, hand_n=hand_n, hand_f=hand_f, chest=chest, hip=(hx, hy))


# ----------------------------------------------------------------------------------------------
# Shared pose generators and death
# ----------------------------------------------------------------------------------------------
def idle_wave(n, amp=.7):
    return [0, .35, .8, .6, .25, 0][n] * amp


def march(n, *, reach=9., stomp=1., lean=.04):
    """Walk frames: 0-1 crouch, 2-4 the step (the game's hop), 5-7 the landing."""
    hip_y = [-2, -3, 1, 3, 1.5, -3, -1.5, 0][n] * stomp
    foot_n = [(5, 0), (4, 0), (reach, 4), (reach + 2, 7), (reach + 1, 3), (reach, 0), (reach - 3, 0), (6, 0)][n]
    foot_f = [(-5, 0), (-5, 0), (-6, 0), (-8, 2), (-6, 0), (-8, 0), (-7, 0), (-6, 0)][n]
    return dict(hip=(0, 29 + hip_y), lean=lean + [.0, .04, .02, .0, .02, .06, .04, .02][n], foot_n=foot_n, foot_f=foot_f, tilt=[0, .05, 0, -.04, 0, .06, .04, 0][n])


def hurt_frame(n):
    """Common flinch values for hurt frame n."""
    return dict(lean=[-.32, -.24, -.1, 0][n], head=([-2, -1.5, -.5, 0][n], 0), tilt=[-.35, -.25, -.1, 0][n], jaw=[3, 2, 1, 0][n],
                glow=[2, 1.4, 1.1, 1][n], eyes='dead' if n == 0 else 'angry', hip=(0, [28, 28.4, 28.8, 29][n]))


def die_figure(f, p, style, n, S=1.):
    """Death frames 0-4 of a skeleton: a flash, a stagger, the knees give, it falls back and lies down. 5-7 are the heap."""
    if n == 0:
        ps = pose(lean=-.3, head=(-2, 0), tilt=-.35, hand_n=(8, 36), hand_f=(10, 36), weapon=1.4, eyes='dead', jaw=3, glow=2)
        skeleton(f, p, Rig(f, S, 44.), ps, style, 'die', n)
        f.whiten()
        return
    k = n - 1
    ps = pose(hip=(-[0, 1, 3, 6][k], [29, 19, 10, 6][k]), lean=[-.26, -.4, -.85, -1.35][k], head=(-1, 0), tilt=-.3,
              hand_n=[(5, 28), (2, 20), (-14, 14), (-24, 8)][k], hand_f=[(-2, 28), (-3, 18), (-16, 9), (-28, 5)][k],
              weapon=[1.2, 1.6, 2.4, 3.1][k], eyes='dead', jaw=3, glow=.3, arm_n_flip=-1, arm_f_flip=-1,
              foot_n=[(7, 0), (10, 0), (13, 3), (14, 6)][k], foot_f=[(-7, 0), (-1, 0), (6, 0), (9, 1)][k])
    skeleton(f, p, Rig(f, S, 44. + [0, 3, 8, 12][k]), ps, style, 'die', n)
    fit(f)


def bone_pile(f, p, k, x0=50., S=1., cloth=None, extra=None):
    """The heap a skeleton leaves (k = 0..2): ribs, long bones, a skull and what it carried; the glow dies out."""
    bone = p.ramp('b0', 'b1', 'b2', 'b3', 'b4')
    spread = [0, 1.5, 2.5][k] * S
    gy = AY - 2
    for (dx, dy, ex, ey, r) in [(-20, 1, -6, -2, 1.6), (4, 0, 22, -1, 1.6), (-12, -2, 6, 1, 1.5), (-1, -4, 15, -2, 1.5)]:
        a, b = (x0 + dx * S - spread * (1 if dx < 0 else -1) * .3, gy + dy), (x0 + ex * S + spread * (1 if ex > 0 else -1) * .3, gy + ey)
        f.paint(capsule(a, b, r * S, (r - .1) * S), bone, dither=.3)
        f.paint(ellipsoid(a[0], a[1], 2.4 * S, 2 * S), bone, dither=.3)
        f.paint(ellipsoid(b[0], b[1], 2.4 * S, 2 * S), bone, dither=.3)
    f.paint(ellipsoid(x0 + 1 * S, gy - 1.5, 11 * S, 3.6 * S), bone, dither=.5)                    # the pelvis and spine, flat
    for i in range(-2, 3):                                                                       # the ribcage, caved in
        f.paint(capsule((x0 - 4 * S + i * 3.4 * S, gy - 1), (x0 - 1 * S + i * 3.4 * S, gy - (9 - abs(i) * 1.6 - k * 1.5) * S), 1.2 * S, .9 * S), bone, dither=.3)
    if cloth:
        cloth(f, p, k, x0, gy)
    sk = (x0 + (15 + spread * .4) * S, gy - 3 * S)
    f.paint(ellipsoid(sk[0], sk[1], 5.8 * S, 5.3 * S, .3), bone, dither=.5)
    f.paint(ellipsoid(sk[0] + 2.8 * S, sk[1] + 2.8 * S, 3.4 * S, 2 * S), bone, dither=.4)
    f.dots([(sk[0] - 1.8 * S, sk[1] - .6), (sk[0] + 1.8 * S, sk[1] - .8)], 'sock')
    if extra:
        extra(f, p, k, x0, gy, S)
    for i in range(3 - k):                                                                       # the last of the glow rising off the pile
        f.dots([(x0 + 6 * S - i * 7 + math.sin(k + i) * 2, gy - 12 - k * 4 - i * 3)], 'mote' if 'mote' in p.names else 'b3')


def fit(f, margin=2):
    """Slides the picture sideways so nothing touches the left or right edge (a body that has fallen over)."""
    ys, xs = np.nonzero(f.a)
    if len(xs):
        if xs.min() < margin:
            f.shift(margin - int(xs.min()), 0)
        elif xs.max() > W - 1 - margin:
            f.shift(W - 1 - margin - int(xs.max()), 0)
        ys, xs = np.nonzero(f.a)
        if ys.max() > AY + 1:                                   # nothing may hang below the ground line
            f.shift(0, AY + 1 - int(ys.max()))


def arc_trail(f, pts, name, width=2):
    for a, b in zip(pts, pts[1:]):
        f.line(a, b, name, width)


def slash_trail(f, rig, n, pts, color='slash'):
    """A bright arc following the blade through attack frames 3-5."""
    upto = {3: 3, 4: 5, 5: 6}.get(n)
    if not upto:
        return
    seg = [rig.P(*pt) for pt in pts[:upto]]
    arc_trail(f, seg, color, 2)
    arc_trail(f, [(x + 1, y + 1) for x, y in seg[-3:]], 'b4', 1)


def dust_burst(f, rig, x, strength, name='dust'):
    """Ground dust thrown out of an impact at local x (strength 1 = the strike frame, then fading)."""
    gy = AY - 1
    cx = rig.P(x, 0)[0]
    for i in range(7):
        a = -math.pi * (.1 + .8 * i / 6)
        d = (5 + 6 * strength) * (.7 + .5 * ((i * 7) % 3) / 2)
        f.dots([(cx + math.cos(a) * d * 1.5, gy + math.sin(a) * d * .7 * strength)], name if i % 2 else name + '2')
    f.dots([(cx + k * 3, gy) for k in range(-4, 5)], name)


# ----------------------------------------------------------------------------------------------
# Vault Thrall: a rotted skeleton in rags with a cracked round shield and a rusty sword.
# ----------------------------------------------------------------------------------------------
THRALL = palette_of(BONE, METAL, WOOD, EFFECT, cl0='#1f2a24', cl1='#3b4a3c', cl2='#5c6e56', cl3='#8a9a78', rust='#8a4a2a', rust2='#b86a34',
                    glow='#7af0ff', mote='#9fe8f0')


def draw_sword(rig, p, ps, hand, length=21., width=1.6, metal=('m0', 'm1', 'm2', 'm3'), rust=True):
    a = ps['weapon']
    d = (math.cos(a), math.sin(a))
    tip = (hand[0] + d[0] * length, hand[1] + d[1] * length)
    rig.limb((hand[0] - d[0] * 2.4, hand[1] - d[1] * 2.4), hand, 1.3, 1.3, p.ramp('wd0', 'wd1', 'wd2'), dither=.3)
    g = (-d[1] * 3.4, d[0] * 3.4)
    c = (hand[0] + d[0] * 1.4, hand[1] + d[1] * 1.4)
    rig.limb((c[0] - g[0], c[1] - g[1]), (c[0] + g[0], c[1] + g[1]), 1.1, 1.1, p.ramp('m0', 'm1', 'm2'), dither=.3)
    rig.limb((hand[0] + d[0] * 2.4, hand[1] + d[1] * 2.4), tip, width, width * .5, p.ramp(*metal), dither=.45)
    if rust:
        for t, name in ((.3, 'rust2'), (.55, 'rust'), (.8, 'rust2')):
            rig.dots([(hand[0] + d[0] * length * t, hand[1] + d[1] * length * t)], name)


def draw_round_shield(rig, p, hand, r=9., name=('wd0', 'wd1', 'wd2', 'wd3'), boss=True, bands=True, cracked=True):
    cx, cy = hand[0] + 3.4, hand[1] + .6
    rig.blob((cx, cy), r * .74, r, p.ramp(*name), dither=.5)
    rig.blob((cx - .5, cy), r * .5, r * .75, p.ramp(*name), outline=False, dither=.35)
    if bands:
        for dy in (-r * .5, r * .5):
            rig.line((cx - r * .5, cy + dy), (cx + r * .5, cy + dy * .92), 'm1', 1)
    if boss:
        rig.blob((cx + .2, cy), 2.4, 2.6, p.ramp('m0', 'm1', 'm2', 'm3'), dither=.3)
    if cracked:
        rig.line((cx - 1, cy + r * .9), (cx + 1.5, cy + r * .2), 'wd0', 1)
        rig.line((cx + 1.5, cy + r * .2), (cx - .5, cy - r * .4), 'wd0', 1)


def thrall_torso(rig, p, ps, chest, hip, neck, clip, n):
    x, y = chest
    rig.shaded([(x - 5.8, y + 8.8), (x + 5.2, y + 8.4), (x + 6.8, y - 7.5), (x + 3.2, y - 10), (x + 1, y - 7.4), (x - 2.2, y - 10.4), (x - 6.2, y - 8.4)],
               p.ramp('cl0', 'cl1', 'cl2', 'cl3'), lo=.15, hi=.8)
    rig.line((x - 6.2, y - 3), (x + 6.8, y - 3.6), 'cl0', 1)
    rig.dots([(x + 2, y + 3), (x - 2, y), (x + 3.5, y - 1.5)], 'b0')


def thrall_skirt(rig, p, ps, hip, clip, n):
    x, y = hip
    rig.shaded([(x - 5.4, y - 1), (x + 5.8, y - 1.6), (x + 6.6, y - 9.4), (x + 3.2, y - 7.4), (x + 1, y - 11), (x - 2.2, y - 7.2), (x - 5.4, y - 9.6)],
               p.ramp('cl0', 'cl1', 'cl2'), lo=.2, hi=.8)


STYLE_THRALL = dict(
    torso_gear=thrall_torso, skirt=thrall_skirt, eye='glow',
    weapon=lambda rig, p, ps, hn, en, hf, c, n: draw_sword(rig, p, ps, hn),
    far_hand=lambda rig, p, ps, hf, ef, c, n: draw_round_shield(rig, p, hf),
)


def sword_pose(clip, n, kind_lean=0.):
    """Poses shared by the sword-and-shield skeletons (the thrall): returns (pose, extras)."""
    ex = dict(trail=False, flash=False)
    if clip == 'idle':
        w = idle_wave(n)
        ps = pose(hip=(0, 29 + w * .6), lean=.05 + w * .02, hand_n=(11, 30 + w), hand_f=(11, 34 - w * .5), weapon=.75 + w * .05,
                  head=(0, w * .4), eyes='blink' if n == 4 else 'open', glow=[1, 1.1, 1.2, 1.1, 1, .9][n], jaw=[0, 0, .3, .5, .3, 0][n])
    elif clip == 'walk':
        bob = 2 if n in (2, 3) else 0
        ps = pose(**march(n), hand_n=(10 + (2 if n in (2, 3) else -1), 30 + bob), hand_f=(11, 34 + (1 if n in (3, 4) else 0)), weapon=.7)
    elif clip == 'attack':
        lean, hand, weapon, hip_y, foot_n, foot_f = [
            (-.1, (7, 41), 1.35, 28.6, (6, 0), (-7, 0)), (-.18, (0, 51), 1.8, 28, (6, 0), (-8, 0)), (-.26, (-4, 57), 2.0, 27.4, (7, 0), (-10, 0)),
            (.05, (11, 56), 1.1, 28, (8, 0), (-9, 0)), (.34, (24, 41), -.2, 26.2, (14, 0), (-8, 0)), (.42, (27, 29), -.85, 25.4, (15, 0), (-7, 0)),
            (.26, (21, 31), -.4, 27, (11, 0), (-7, 0)), (.1, (14, 31), .35, 28.4, (8, 0), (-6, 0))][n]
        ps = pose(hip=(3 if n in (4, 5) else 0, hip_y), lean=lean, hand_n=hand, weapon=weapon, foot_n=foot_n, foot_f=foot_f,
                  hand_f=(14 if n in (4, 5) else 12, 35), eyes='angry', glow=1.6, jaw=[0, .6, 1.2, 1.4, 2, 1.4, .6, 0][n], head=(1 if n in (4, 5) else 0, 0))
        ex['trail'] = n in (3, 4, 5)
    else:  # hurt
        h = hurt_frame(n)
        ps = pose(hip=h['hip'], lean=h['lean'], head=h['head'], tilt=h['tilt'], hand_n=(10, 30 + [4, 3, 1, 0][n]), hand_f=(10, 33),
                  weapon=[1.3, 1.1, .9, .75][n], eyes=h['eyes'], jaw=h['jaw'], glow=h['glow'])
        ex['flash'] = n == 0
    return ps, ex


SWORD_ARC = [(0, 60), (8, 62), (17, 57), (24, 49), (29, 38), (30, 27)]


def thrall_pile(f, p, k, x0=50.):
    def gear(f, p, k, x0, gy, S):
        f.paint(capsule((x0 - 27, gy + 1), (x0 - 10, gy - 1), 1.3, .9), p.ramp('m0', 'm1', 'm2', 'm3'), dither=.4)
        f.paint(capsule((x0 - 28.5, gy + 1.5), (x0 - 26, gy + 1), 1.2, 1.2), p.ramp('wd0', 'wd1', 'wd2'), dither=.3)
        f.paint(ellipsoid(x0 + 25, gy - 3.4, 4.6, 6.4, -.5), p.ramp('wd0', 'wd1', 'wd2', 'wd3'), dither=.5)
        f.paint(polygon([(x0 - 14, gy), (x0 - 6, gy - 5), (x0 + 3, gy - 4), (x0 + 11, gy), (x0 + 6, gy + 1.4), (x0 - 8, gy + 1.5)]), p.ramp('cl0', 'cl1', 'cl2')[:3].tolist() and p.ramp('cl0', 'cl1', 'cl2'), dither=.3) if False else None
    bone_pile(f, p, k, x0, extra=gear)


def thrall(clip, n):
    f = Frame(THRALL)
    p = THRALL
    if clip == 'die':
        if n <= 4:
            die_figure(f, p, STYLE_THRALL, n)
        else:
            thrall_pile(f, p, n - 5)
        return f.a
    ps, ex = sword_pose(clip, n)
    rig = Rig(f, 1.1, 44.)
    skeleton(f, p, rig, ps, STYLE_THRALL, clip, n)
    if ex['trail']:
        slash_trail(f, rig, n, SWORD_ARC)
    if clip in ('idle', 'walk'):
        for k in range(2):
            u = (n / 6 + k / 2) % 1
            f.dots([(46 + math.sin(u * 7 + k * 2) * 8, 58 - u * 24 - k * 6)], 'mote')
    if ex['flash']:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Bone Archer: a hooded skeleton with a quiver and a bow. The attack clip is the draw (0-2) and the release (3).
# ----------------------------------------------------------------------------------------------
ARCHER = palette_of(BONE, METAL, WOOD, EFFECT, lt0='#2a1c14', lt1='#4a3220', lt2='#6e4a2c', lt3='#946a40', fe='#d8d0c0', fe2='#a8402c',
                    glow='#ffc24a', mote='#ffd88a')


def draw_bow(rig, p, grip, draw, nocked, hand_n):
    gx, gy = grip
    pull = 3.4 * draw
    wood = p.ramp('wd0', 'wd1', 'wd2', 'wd3')
    top, bot = (gx - 2.4 - pull, gy + 15.5), (gx - 2.4 - pull, gy - 15.5)
    pts = [top, (gx - .6 - pull * .5, gy + 9), (gx + 1.4, gy + 3.2), (gx + 1.4, gy - 3.2), (gx - .6 - pull * .5, gy - 9), bot]
    for a, b in zip(pts, pts[1:]):
        rig.limb(a, b, 1.3, 1.3, wood, dither=.3)
    rig.limb((gx + 1.4, gy + 2.6), (gx + 1.4, gy - 2.6), 1.7, 1.7, p.ramp('lt0', 'lt1', 'lt2'), dither=.3)         # the leather grip
    if draw > 0 or nocked:
        string_to = hand_n if draw > .15 else (gx - 2.4, gy)
        rig.line(top, string_to, 'fe', 1)
        rig.line(bot, string_to, 'fe', 1)
    else:
        rig.line(top, bot, 'fe', 1)
    return top, bot


def draw_arrow(rig, p, tail, grip):
    dx, dy = grip[0] + 5 - tail[0], grip[1] - tail[1]
    d = math.hypot(dx, dy) or 1
    tip = (tail[0] + dx, tail[1] + dy)
    rig.limb(tail, tip, .8, .8, p.ramp('wd1', 'wd2', 'wd3'), dither=.2, outline=False)
    rig.limb((tip[0] - dx / d * 2.2, tip[1] - dy / d * 2.2), (tip[0] + dx / d * 1.6, tip[1] + dy / d * 1.6), 1.4, .3, p.ramp('m1', 'm2', 'm3'), dither=.2)
    rig.dots([(tail[0] + dx / d * 1.2, tail[1] + dy / d * 1.2 + 1), (tail[0] + dx / d * 1.2, tail[1] + dy / d * 1.2 - 1), (tail[0] + dx / d * 2.6, tail[1] + dy / d * 2.6 + 1)], 'fe2')


def archer_hood(rig, p, ps, hd, back, clip, n):
    leather = p.ramp('lt0', 'lt1', 'lt2', 'lt3')
    if back:
        rig.blob((hd[0] - 1.8, hd[1] + .6), 7.8, 8.0, leather, angle=-.2, dither=.5)
    else:
        rig.blob((hd[0] - .3, hd[1] + 6.6), 7.7, 3.6, leather, angle=-.1, dither=.5)
        rig.line((hd[0] - 6.2, hd[1] + 3.5), (hd[0] - 6.6, hd[1] - 4), 'lt0', 1)


def archer_torso(rig, p, ps, chest, hip, neck, clip, n):
    x, y = chest
    rig.shaded([(x - 5.8, y + 8.6), (x + 5.6, y + 8.2), (x + 6.6, y - 7), (x + 3, y - 9), (x - 2, y - 9.4), (x - 6.2, y - 7.4)], p.ramp('lt0', 'lt1', 'lt2', 'lt3'), lo=.15, hi=.85)
    rig.line((x - 6.2, y - 2.6), (x + 6.6, y - 3.2), 'lt0', 1)
    rig.blob((x + 5, y - 5.2), 2.4, 2.6, p.ramp('lt0', 'lt1', 'lt2'), dither=.3)                                        # a belt pouch
    rig.line((x - 4, y + 8), (x + 4.5, y - 6), 'lt0', 1)                                                                # the quiver strap


def archer_skirt(rig, p, ps, hip, clip, n):
    x, y = hip
    rig.shaded([(x - 5.4, y - 1), (x + 5.8, y - 1.6), (x + 6, y - 7.6), (x + 2, y - 6), (x - 2, y - 8.4), (x - 5.4, y - 7)], p.ramp('lt0', 'lt1', 'lt2'), lo=.2, hi=.8)


def archer_behind(rig, p, ps, neck, hip, clip, n):
    lean = ps['lean']
    a = (neck[0] - 6.4 + math.sin(lean) * 2, neck[1] - 1.5)
    b = (hip[0] - 5.2, hip[1] + 3)
    rig.limb(a, b, 3.1, 2.7, p.ramp('lt0', 'lt1', 'lt2', 'lt3'), dither=.4)
    for dx, ddy in ((-1.2, 0), (0.4, 1.6), (1.8, -.4)):                                                                  # the fletchings
        rig.limb((a[0] + dx, a[1] + 1), (a[0] + dx - .6, a[1] + 5 + ddy), .8, .9, p.ramp('wd1', 'wd2', 'wd3'), dither=.2, outline=False)
        rig.dots([(a[0] + dx - .6, a[1] + 5.6 + ddy), (a[0] + dx - .6, a[1] + 6.8 + ddy)], 'fe2' if dx > 0 else 'fe')


def archer_far_hand(rig, p, ps, hf, ef, clip, n):
    draw = ps.get('draw', 0.)
    ps['_bow'] = draw_bow(rig, p, (hf[0] + 1.0, hf[1] + .4), draw, ps.get('nocked', False), ps['_hand_n_target'])


def archer_weapon(rig, p, ps, hn, en, hf, clip, n):
    if ps.get('nocked'):
        draw_arrow(rig, p, (hn[0] - .4, hn[1]), (hf[0] + 1, hf[1] + .4))


STYLE_ARCHER = dict(hood=archer_hood, torso_gear=archer_torso, skirt=archer_skirt, behind=archer_behind, eye='glow',
                    far_hand=archer_far_hand, weapon=archer_weapon)


def archer_pose(clip, n):
    ex = dict(flash=False, flare=False)
    if clip == 'idle':
        w = idle_wave(n)
        hn = (5, 30 + w * .4)
        ps = pose(hip=(0, 29 + w * .6), lean=.03, hand_n=hn, hand_f=(13, 33 + w * .4), head=(0, w * .4), eyes='blink' if n == 4 else 'open',
                  glow=[1, 1.1, 1.2, 1.1, 1, .9][n], jaw=[0, 0, .3, .5, .3, 0][n], draw=0., nocked=True, weapon=0.)
    elif clip == 'walk':
        bob = 2 if n in (2, 3) else 0
        hn = (4, 30 + bob)
        ps = pose(**march(n), hand_n=hn, hand_f=(13, 33 + (1 if n in (3, 4) else 0)), draw=0., nocked=True)
    elif clip == 'attack':
        draw = [.3, .7, 1., -.3, 0, 0, 0, 0][n]
        hf = [(14, 36), (16, 40), (17, 42), (17, 42), (16, 40), (15, 38), (14, 35), (13, 34)][n]
        hn = [(5, 36), (-1, 41), (-5.5, 43), (-9, 42), (-6, 40), (-1, 38), (4, 35), (5, 31)][n]
        ps = pose(hip=(0, [28.6, 28.2, 28, 28.2, 28.6, 28.8, 29, 29][n]), lean=[.0, -.04, -.08, -.1, -.04, 0, .02, .03][n], hand_n=hn, hand_f=hf,
                  eyes='angry', glow=1.7, jaw=[0, .4, .8, 1.4, 1, .6, .2, 0][n], draw=draw, nocked=n < 3 or n == 7, foot_n=(7, 0), foot_f=(-8, 0))
        ex['flare'] = n == 3
    else:
        h = hurt_frame(n)
        ps = pose(hip=h['hip'], lean=h['lean'], head=h['head'], tilt=h['tilt'], hand_n=(5, 31 + [3, 2, 1, 0][n]), hand_f=(13, 33), eyes=h['eyes'],
                  jaw=h['jaw'], glow=h['glow'], draw=0., nocked=False)
        ex['flash'] = n == 0
    ps['_hand_n_target'] = ps['hand_n']
    return ps, ex


def archer_pile(f, p, k, x0=50.):
    def gear(f, p, k, x0, gy, S):
        wood = p.ramp('wd0', 'wd1', 'wd2', 'wd3')
        f.paint(capsule((x0 - 26, gy + 1), (x0 - 15, gy - 7), 1.3, 1.3), wood, dither=.3)                   # a snapped bow
        f.paint(capsule((x0 - 14, gy - 5), (x0 - 8, gy), 1.3, 1.2), wood, dither=.3)
        for i, dx in enumerate((18, 23, 28)):
            f.paint(capsule((x0 + dx, gy + 1), (x0 + dx + 8, gy - 1 - i), .8, .8), p.ramp('wd1', 'wd2', 'wd3'), dither=.2, outline=False)
            f.dots([(x0 + dx + 8.6, gy - 1 - i)], 'm3')
        f.paint(capsule((x0 + 4, gy - 8), (x0 + 12, gy - 4), 2.8, 2.4), p.ramp('lt0', 'lt1', 'lt2', 'lt3'), dither=.4)   # the quiver
    bone_pile(f, p, k, x0, extra=gear)


def archer(clip, n):
    f = Frame(ARCHER)
    p = ARCHER
    if clip == 'die':
        if n <= 4:
            die_figure(f, p, dict(STYLE_ARCHER, far_hand=None, weapon=None), n)
        else:
            archer_pile(f, p, n - 5)
        return f.a
    ps, ex = archer_pose(clip, n)
    rig = Rig(f, 1.1, 44.)
    skeleton(f, p, rig, ps, STYLE_ARCHER, clip, n)
    if ex['flare']:                                                        # the string snaps: a spark at the bow
        gx, gy = ps['hand_f'][0] + 1, ps['hand_f'][1]
        f.dots([rig.P(gx + 6, gy), rig.P(gx + 8, gy + 1), rig.P(gx + 10, gy)], 'glow')
    if ex['flash']:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Hollow Acolyte: a skull in a violet hood and robe that hovers a hand above the floor, a staff topped by a glowing orb.
# ----------------------------------------------------------------------------------------------
ACOLYTE = palette_of(BONE, WOOD, EFFECT, rb0='#1a1030', rb1='#2e1a52', rb2='#4a2a82', rb3='#7044b8', gd0='#6a5420', gd1='#b8902c', gd2='#f0cc5c',
                     vio0='#5a24b0', vio1='#a45cff', vio2='#dcb4ff', vio3='#fff2ff', glow='#d08cff', mote='#c8a0ff', m1='#555a66', m2='#8a909c')


def acolyte_robe(rig, p, ps, hip, neck, chest, clip, n):
    robe = p.ramp('rb0', 'rb1', 'rb2', 'rb3')
    hx, hy = hip
    wave = math.sin(n * .9 + (1 if clip == 'walk' else 0)) * (1.6 if clip == 'walk' else .8)
    pts = [(neck[0] - 6, neck[1] - 2), (neck[0] + 5.4, neck[1] - 3), (hx + 7.4, hy + 1), (hx + 10.4, 1.6 + wave), (hx + 4, .2), (hx - 2, 1.4 - wave * .6), (hx - 9.4, 2.4 + wave), (hx - 7, hy + 2)]
    rig.shaded(pts, robe, lo=.12, hi=.8, dither=.5)
    for t, dx in ((.35, -4), (.6, 1), (.8, 6)):                                       # folds
        rig.line((hx + dx * .5 - 1, hy + 3), (hx + dx * 1.4, 1.2 + wave * t), 'rb0', 1)
    rig.line((hx - 6.6, hy + 2.6), (hx + 7, hy + 1.2), 'gd1', 2)                      # the sash
    rig.dots([(hx + 7, hy + 1), (hx + 7.4, hy - 1.4), (hx + 7.8, hy - 3.6)], 'gd2')
    rig.poly([(neck[0] - 4.2, neck[1] - 2.6), (neck[0] + 4.2, neck[1] - 3.2), (neck[0] + 2.8, neck[1] - 6.6), (neck[0] - 3, neck[1] - 6)], 'gd1', outline=True, edge='gd0')   # a gold collar


def acolyte_hood(rig, p, ps, hd, back, clip, n):
    robe = p.ramp('rb0', 'rb1', 'rb2', 'rb3')
    if back:
        rig.blob((hd[0] - 2.4, hd[1] - .4), 8.4, 9.0, robe, angle=-.2, dither=.5)
    else:
        rig.blob((hd[0] - .6, hd[1] + 7.4), 8.0, 3.3, robe, angle=-.1, dither=.5)
        rig.line((hd[0] + 7.2, hd[1] + 5), (hd[0] + 8.2, hd[1] - 3), 'rb1', 1)


def draw_staff(rig, p, ps, hand, glow, clip, n):
    a = ps['weapon']
    d = (math.cos(a), math.sin(a))
    base = (hand[0] - d[0] * 13, hand[1] - d[1] * 13)
    tip = (hand[0] + d[0] * 17, hand[1] + d[1] * 17)
    rig.limb(base, tip, 1.3, 1.1, p.ramp('wd0', 'wd1', 'wd2', 'wd3'), dither=.3)
    for s in (-1, 1):                                                                 # a cage of prongs round the orb
        g = (-d[1] * s, d[0] * s)
        rig.limb((tip[0] - d[0] * 2, tip[1] - d[1] * 2), (tip[0] + d[0] * 2.5 + g[0] * 3.4, tip[1] + d[1] * 2.5 + g[1] * 3.4), 1., .7, p.ramp('gd0', 'gd1', 'gd2'), dither=.3)
    c = (tip[0] + d[0] * 3, tip[1] + d[1] * 3)
    r = 2.7 + glow * 1.2
    rig.blob(c, r, r, p.ramp('vio0', 'vio1', 'vio2', 'vio3'), dither=.4)
    rig.dots([(c[0] - r * .3, c[1] + r * .3)], 'vio3')
    if glow > 1.2:                                                                    # a halo of motes
        for k in range(8):
            q = k * .785 + n * .4
            rig.dots([(c[0] + math.cos(q) * (r + 2.4), c[1] + math.sin(q) * (r + 2.4))], 'mote')
    return c, r


def acolyte_weapon(rig, p, ps, hn, en, hf, clip, n):
    ps['_orb'] = draw_staff(rig, p, ps, hn, ps['glow'], clip, n)


STYLE_ACOLYTE = dict(robe=acolyte_robe, hood=acolyte_hood, cloth=('rb0', 'rb1', 'rb2', 'rb3'), sleeve=True, eye='glow', weapon=acolyte_weapon, upper=10.5, fore=10.)


def acolyte_pose(clip, n):
    ex = dict(flash=False, burst=0)
    if clip == 'idle':
        w = idle_wave(n)
        ps = pose(hip=(0, 29 + w * .5), lean=.02, hand_n=(10, 27 + w * .4), hand_f=(5, 28 + w * .4), weapon=1.5, head=(0, w * .3), eyes='blink' if n == 4 else 'open',
                  glow=[1, 1.1, 1.2, 1.1, 1, .9][n], jaw=[0, 0, .3, .5, .3, 0][n])
    elif clip == 'walk':
        ps = pose(hip=(0, 29 + [-1, -1.5, .5, 1.5, 1, -1.5, -1, 0][n]), lean=[.04, .06, .03, .02, .03, .07, .05, .03][n], hand_n=(10, 27 + (1 if n in (2, 3) else 0)), hand_f=(5, 28), weapon=1.5, tilt=[0, .04, 0, -.03, 0, .05, .03, 0][n])
    elif clip == 'attack':
        data = [((8, 34), 1.3, .9, -.06, (4, 30)), ((7, 44), 1.2, 1.4, -.1, (3, 34)), ((6, 52), 1.1, 2., -.16, (1, 38)), ((13, 46), .25, 2.6, .1, (10, 40)),
                ((13, 44), .1, 3., .14, (10, 42)), ((14, 43), .0, 2.2, .12, (11, 40)), ((12, 38), .9, 1.4, .06, (8, 34)), ((9, 29), 1.4, 1., .02, (6, 29))][n]
        ps = pose(hip=(0, 29 + [0, .3, .6, 0, -.6, -.3, 0, 0][n]), lean=data[3], hand_n=data[0], weapon=data[1], glow=data[2], hand_f=data[4], eyes='angry',
                  jaw=[0, .6, 1.2, 2, 2.4, 1.4, .6, 0][n])
        ex['burst'] = {3: .6, 4: 1., 5: .6}.get(n, 0)
    else:
        h = hurt_frame(n)
        ps = pose(hip=h['hip'], lean=h['lean'], head=h['head'], tilt=h['tilt'], hand_n=(10, 28 + [3, 2, 1, 0][n]), hand_f=(5, 28), weapon=1.5 - [.3, .2, .1, 0][n], eyes=h['eyes'],
                  jaw=h['jaw'], glow=h['glow'])
        ex['flash'] = n == 0
    return ps, ex


def acolyte_pile(f, p, k, x0=50.):
    def gear(f, p, k, x0, gy, S):
        mask = polygon([(x0 - 19, gy + 1.4), (x0 - 10, gy - 5.5), (x0 + 2, gy - 6.5), (x0 + 12, gy - 1.5), (x0 + 12, gy + 2), (x0 - 14, gy + 2.2)])
        f.paint(gradient(mask, x0 - 19, gy + 2, x0 + 12, gy - 6, .15, .85), p.ramp('rb0', 'rb1', 'rb2', 'rb3'), dither=.45)
        f.paint(capsule((x0 - 30, gy + 1), (x0 - 12, gy - 1), 1.3, 1.1), p.ramp('wd0', 'wd1', 'wd2', 'wd3'), dither=.3)
        f.paint(ellipsoid(x0 - 32, gy - 1.5, 3, 3), p.ramp('vio0', 'vio1', 'vio2') if k < 2 else p.ramp('b0', 'b1', 'b2'), dither=.5)
    bone_pile(f, p, k, x0, extra=gear)


def acolyte(clip, n):
    f = Frame(ACOLYTE)
    p = ACOLYTE
    if clip == 'die':
        if n <= 4:
            die_robed(f, p, n)
        else:
            acolyte_pile(f, p, n - 5)
        return f.a
    ps, ex = acolyte_pose(clip, n)
    rig = Rig(f, 1.1, 44., lift=2.)
    skeleton(f, p, rig, ps, STYLE_ACOLYTE, clip, n)
    orb = ps.get('_orb')
    if ex['burst'] and orb:
        c, r = orb
        for k in range(10):
            a = k * .628 + n
            f.dots([rig.P(c[0] + math.cos(a) * (r + 3 + 4 * ex['burst']), c[1] + math.sin(a) * (r + 3 + 4 * ex['burst']))], 'vio2')
        rig.blob(c, r + 2.2 * ex['burst'], r + 2.2 * ex['burst'], p.ramp('vio0', 'vio1', 'vio2', 'vio3'), dither=.3)
    if clip == 'idle':
        for k in range(2):
            u = (n / 6 + k / 2) % 1
            f.dots([(48 + math.sin(u * 7 + k * 2) * 8, 62 - u * 22 - k * 6)], 'mote')
    if ex['flash']:
        f.whiten()
    return f.a


def die_robed(f, p, n):
    """A robed skeleton dies by crumpling: the robe sinks, the hood falls, the staff drops, the glow gutters."""
    sink = [0, 4, 11, 17, 21][n]
    ps = pose(hip=(-sink * .1, 29 - sink), lean=[-.25, -.15, -.45, -.6, -.7][n], head=(-1, -sink * .15), tilt=-.3, hand_n=(6, 22 - sink * .7), hand_f=(3, 22 - sink * .7),
              weapon=[1.3, 1.6, 2.2, 2.9, 3.1][n], eyes='dead', jaw=3, glow=[2, .8, .4, .2, .1][n])
    rig = Rig(f, 1.1, 44. + sink * .2, lift=max(0, 2 - sink * .2))
    skeleton(f, p, rig, ps, dict(STYLE_ACOLYTE, weapon=acolyte_weapon), 'die', n)
    if n == 0:
        f.whiten()


# ----------------------------------------------------------------------------------------------
# Hrolf Bonegate, the Gatewarden: an armoured skeleton jarl with a horned helm, a fur mantle, a round shield and a battle-axe.
# ----------------------------------------------------------------------------------------------
GATEWARDEN = palette_of(BONE, METAL, WOOD, EFFECT, fu0='#2a2622', fu1='#5a5248', fu2='#8a8070', fu3='#bcb2a0', rd0='#4a1418', rd1='#8a2630', rd2='#c44a4a',
                        gd1='#b8902c', gd2='#f0cc5c', glow='#ff9a3a', mote='#ffb870')


def warden_torso(rig, p, ps, chest, hip, neck, clip, n):
    x, y = chest
    steel = p.ramp('m0', 'm1', 'm2', 'm3', 'm4')
    rig.shaded([(x - 6.4, y + 8.8), (x + 6.2, y + 8.4), (x + 7.4, y - 6.4), (x + 3, y - 9.6), (x - 3, y - 9.8), (x - 7, y - 6.6)], steel, lo=.12, hi=.85, dither=.4)
    rig.line((x - 6.4, y + 1), (x + 7, y + .4), 'm0', 1)                                  # plate seams
    rig.line((x - 1, y + 8.6), (x - .6, y - 9), 'm0', 1)
    rig.dots([(x - 4.6, y + 5.6), (x + 4.4, y + 5.2), (x - 4.6, y - 5.4), (x + 4.8, y - 5.6)], 'gd2')   # rivets
    rig.poly([(x - 2.8, y - 1.4), (x + 2.8, y - 1.6), (x + 1.8, y - 4), (x - 1.8, y - 3.8)], 'rd1')     # a red sash fragment


def warden_skirt(rig, p, ps, hip, clip, n):
    x, y = hip
    steel = p.ramp('m0', 'm1', 'm2', 'm3')
    rig.shaded([(x - 6, y - .6), (x + 6.8, y - 1.2), (x + 7.4, y - 10), (x + 3, y - 8.2), (x - 1, y - 11), (x - 6.4, y - 9)], steel, lo=.1, hi=.7, dither=.5)
    for k in range(3):
        rig.line((x - 5 + k * 4, y - 2), (x - 4.4 + k * 4, y - 9), 'm0', 1)
    rig.blob((x + 1, y - 1.6), 6.6, 1.5, p.ramp('rd0', 'rd1', 'rd2'), dither=.3)                      # a belt


def warden_shoulder(rig, p, ps, sh_n, sh_f, clip, n):
    fur = p.ramp('fu0', 'fu1', 'fu2', 'fu3')
    rig.blob((sh_n[0] - .6, sh_n[1] + .8), 5.6, 4.2, fur, dither=.6)
    steel = p.ramp('m0', 'm1', 'm2', 'm3')
    rig.blob((sh_n[0] + .8, sh_n[1] + 1.2), 4.8, 3.4, steel, dither=.5)
    rig.dots([(sh_n[0] + 2, sh_n[1] + 2), (sh_n[0] - 1, sh_n[1] + 2.6)], 'gd2')
    rig.blob((sh_n[0] - 3, sh_n[1] + 3.4), 3.0, 1.4, fur, dither=.5)


def warden_helm(rig, p, ps, hd, clip, n):
    steel = p.ramp('m0', 'm1', 'm2', 'm3', 'm4')
    horn = p.ramp('b1', 'b2', 'b3', 'b4')
    for sx, curve in ((-3.4, -1), (5.2, 1)):                                              # two horns sweeping out and up
        a = (hd[0] + sx, hd[1] + 7)
        m = (hd[0] + sx + curve * 3.6, hd[1] + 10.4)
        t = (hd[0] + sx + curve * 5.2, hd[1] + 15.6)
        rig.limb(a, m, 2.0, 1.5, horn, dither=.4)
        rig.limb(m, t, 1.5, .5, horn, dither=.4)
    rig.blob((hd[0] - .2, hd[1] + 7.2), 7.6, 4.3, steel, dither=.5)                         # the dome
    rig.poly([(hd[0] - 7.4, hd[1] + 4.4), (hd[0] + 7.9, hd[1] + 3.6), (hd[0] + 7.6, hd[1] + 2.4), (hd[0] - 7.4, hd[1] + 3.2)], 'm1', outline=False)   # the brow band
    rig.line((hd[0] + 7.8, hd[1] + 3.6), (hd[0] + 8, hd[1] - 3.6), 'm2', 1)                 # the nose guard
    rig.dots([(hd[0] - 2, hd[1] + 8.6), (hd[0] + 3, hd[1] + 8.8)], 'm4')
    rig.dots([(hd[0] - 6, hd[1] + 3.8), (hd[0] + 1, hd[1] + 3.5), (hd[0] + 6, hd[1] + 3.2)], 'gd2')


def battle_axe(rig, p, ps, hand, length=25., clip=None, n=0):
    a = ps['weapon']
    d = (math.cos(a), math.sin(a))
    nx, ny = -d[1], d[0]
    base = (hand[0] - d[0] * 7, hand[1] - d[1] * 7)
    tip = (hand[0] + d[0] * length, hand[1] + d[1] * length)
    rig.limb(base, tip, 1.5, 1.4, p.ramp('wd0', 'wd1', 'wd2', 'wd3'), dither=.3)
    c = (tip[0] - d[0] * 5, tip[1] - d[1] * 5)

    def at(u, v):
        return (c[0] + d[0] * u + nx * v, c[1] + d[1] * u + ny * v)
    pts = [at(1.5 + 7.2 * math.sin(t), .8 + 10.5 * math.cos(t) ** .8) for t in [i * math.pi / 8 - math.pi / 2 for i in range(9)]]
    rig.shaded(pts, p.ramp('m0', 'm1', 'm2', 'm3', 'm4'), lo=.1, hi=.95, dither=.3)
    rig.limb(at(6.4, -.8), at(10.5, -1), 1.3, .3, p.ramp('m0', 'm1', 'm2', 'm3'), dither=.3)           # the spike on top of the head
    rig.limb(at(-5.6, .6), at(-8, 6.6), .9, .4, p.ramp('m1', 'm2', 'm3'), dither=.3)
    rig.dots([at(1.5, 9.4), at(4.4, 8.2), at(-1.4, 8.2)], 'm4')                                       # a lit cutting edge


def warden_far(rig, p, ps, hf, ef, clip, n):
    draw_round_shield(rig, p, (hf[0] + ps.get('shield', 0), hf[1]), r=11.5, name=('m0', 'm1', 'm2', 'm3'), boss=True, bands=False, cracked=False)
    cx, cy = hf[0] + ps.get('shield', 0) + 3.4, hf[1] + .6
    rig.blob((cx, cy), 5.4, 7.6, p.ramp('rd0', 'rd1', 'rd2'), outline=False, dither=.4)
    rig.blob((cx + .2, cy), 2.6, 2.8, p.ramp('m0', 'm1', 'm2', 'm3'), dither=.3)
    rig.dots([(cx - 5.6, cy + 4), (cx - 5.6, cy - 4), (cx + 6, cy + 4.4), (cx + 6, cy - 4.4)], 'gd2')


STYLE_GATEWARDEN = dict(torso_gear=warden_torso, skirt=warden_skirt, shoulder=warden_shoulder, head_gear=warden_helm, eye='glow',
                        far_hand=warden_far, weapon=lambda rig, p, ps, hn, en, hf, c, n: battle_axe(rig, p, ps, hn, 25., c, n))


def warden_pose(clip, n):
    ex = dict(flash=False, dust=0., trail=False)
    if clip == 'idle':
        w = idle_wave(n)
        ps = pose(hip=(0, 29 + w * .6), lean=.05 + w * .02, hand_n=(10, 29 + w), hand_f=(11, 34 - w * .5), weapon=1.15 + w * .04, head=(0, w * .4),
                  eyes='blink' if n == 4 else 'open', glow=[1, 1.1, 1.2, 1.1, 1, .9][n], jaw=[0, 0, .3, .5, .3, 0][n])
    elif clip == 'walk':
        ps = pose(**march(n, stomp=1.4, lean=.06), hand_n=(10, 29 + (2 if n in (2, 3) else 0)), hand_f=(11, 34), weapon=1.1)
    elif clip == 'attack':
        lean, hand, weapon, hip_y, foot_n, foot_f = [
            (-.1, (8, 40), 1.5, 28.6, (6, 0), (-7, 0)), (-.2, (3, 45), 1.85, 28, (6, 0), (-8, 0)), (-.3, (-3, 46), 2.4, 27.2, (7, 0), (-10, 0)),
            (0., (9, 47), 1.3, 28, (8, 0), (-9, 0)), (.4, (19, 35), -.75, 25.8, (14, 0), (-8, 0)), (.46, (21, 26), -1.25, 25, (15, 0), (-7, 0)),
            (.3, (18, 31), -.5, 26.6, (12, 0), (-7, 0)), (.1, (12, 31), .6, 28.4, (8, 0), (-6, 0))][n]
        ps = pose(hip=(3 if n in (4, 5) else 0, hip_y), lean=lean, hand_n=hand, weapon=weapon, foot_n=foot_n, foot_f=foot_f, hand_f=(14 if n in (4, 5) else 12, 35),
                  eyes='angry', glow=1.7, jaw=[0, .6, 1.2, 1.4, 2.2, 1.6, .8, 0][n], head=(1 if n in (4, 5) else 0, 0), shield=-3 if n in (1, 2) else 0)
        ex['dust'] = {4: 1., 5: .8, 6: .45}.get(n, 0.)
        ex['trail'] = n in (3, 4, 5)
    else:
        h = hurt_frame(n)
        ps = pose(hip=h['hip'], lean=h['lean'], head=h['head'], tilt=h['tilt'], hand_n=(10, 29 + [4, 3, 1, 0][n]), hand_f=(11, 34), weapon=1.15 + [.3, .2, .1, 0][n],
                  eyes=h['eyes'], jaw=h['jaw'], glow=h['glow'])
        ex['flash'] = n == 0
    return ps, ex


WARDEN_ARC = [(2, 50), (10, 53), (18, 48), (24, 39), (27, 30), (28, 22)]


def warden_pile(f, p, k, x0=50.):
    def gear(f, p, k, x0, gy, S):
        steel = p.ramp('m0', 'm1', 'm2', 'm3')
        f.paint(capsule((x0 - 30, gy + 1), (x0 - 10, gy - 1), 1.4, 1.2), p.ramp('wd0', 'wd1', 'wd2', 'wd3'), dither=.3)
        mask = polygon([(x0 - 31, gy - 6), (x0 - 24, gy - 9), (x0 - 22, gy), (x0 - 29, gy + 1)])
        f.paint(gradient(mask, x0 - 31, gy, x0 - 22, gy - 9, .15, .95), steel, dither=.3)
        f.paint(ellipsoid(x0 + 27, gy - 4, 5, 7.4, -.5), steel, dither=.4)
        f.paint(ellipsoid(x0 + 27.5, gy - 4, 2.4, 3.4, -.5), p.ramp('rd0', 'rd1', 'rd2'), outline=False, dither=.3)
        f.paint(ellipsoid(x0 + 21.6, gy - 6.6, 4.6, 3.2), steel, dither=.4)                      # the helm, rolled off the skull
        for hx in (-3, 3):
            f.paint(capsule((x0 + 21.6 + hx, gy - 8), (x0 + 21.6 + hx * 1.8, gy - 11), 1.4, .6), p.ramp('b1', 'b2', 'b3', 'b4'), dither=.3)
        f.paint(ellipsoid(x0 - 4, gy - 4, 6.8, 3.6), steel, dither=.4)                          # the cracked breastplate
    bone_pile(f, p, k, x0, extra=gear)


def gatewarden(clip, n):
    f = Frame(GATEWARDEN)
    p = GATEWARDEN
    if clip == 'die':
        if n <= 4:
            die_figure(f, p, STYLE_GATEWARDEN, n, S=1.12)
        else:
            warden_pile(f, p, n - 5)
        return f.a
    ps, ex = warden_pose(clip, n)
    rig = Rig(f, 1.12, 42.)
    skeleton(f, p, rig, ps, STYLE_GATEWARDEN, clip, n)
    if ex['trail']:
        slash_trail(f, rig, n, WARDEN_ARC)
    if ex['dust']:
        dust_burst(f, rig, 25, ex['dust'])
    if clip in ('idle', 'walk'):
        for k in range(2):
            u = (n / 6 + k / 2) % 1
            f.dots([(46 + math.sin(u * 7 + k * 2) * 9, 56 - u * 24 - k * 6)], 'mote')
    if ex['flash']:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Valka, the Hollow Choir: a veiled lich in a tattered teal robe, floating a hand above the stones. She sings: the attack clip is a
# song, arms rising (0-2), the voice thrown forward as rings of sound (3-5).
# ----------------------------------------------------------------------------------------------
CHOIR = palette_of(BONE, EFFECT, tl0='#0c2a30', tl1='#16505a', tl2='#23808a', tl3='#5fc0c4', sv1='#8a98a8', sv2='#d0dce8', sv3='#f4fbff',
                   vl0='#3a6a78', vl1='#7fb8c4', vl2='#c8f0f4', glow='#8af0ff', son='#bff4ff', son2='#5ac8e8', mote='#a8f4ff', m1='#555a66', m2='#8a909c', gd1='#b8902c', gd2='#f0cc5c')


def choir_robe(rig, p, ps, hip, neck, chest, clip, n):
    robe = p.ramp('tl0', 'tl1', 'tl2', 'tl3')
    hx, hy = hip
    w1 = math.sin(n * .8) * (2.2 if clip in ('walk', 'attack') else 1.2)
    w2 = math.sin(n * .8 + 1.6) * 1.4
    pts = [(neck[0] - 6.4, neck[1] - 2), (neck[0] + 5.6, neck[1] - 3), (hx + 7.8, hy + 1), (hx + 11.4, 3 + w1), (hx + 5, 1 + w2), (hx - 1, 2.6), (hx - 8, 1.4 + w1), (hx - 14.5, 5 + w2), (hx - 8.4, hy + 2)]
    rig.shaded(pts, robe, lo=.12, hi=.8, dither=.5)
    for dx in (-5, 0, 5):
        rig.line((hx + dx * .4, hy + 3), (hx + dx * 1.5, 3 + w1 * .6), 'tl0', 1)
    rig.line((hx - 7, hy + 2.6), (hx + 7.4, hy + 1.2), 'sv2', 1)                       # a silver cord
    rig.dots([(hx + 7.6, hy + .4), (hx + 8, hy - 2.4)], 'sv3')
    rig.poly([(neck[0] - 4.6, neck[1] - 2.4), (neck[0] + 4.6, neck[1] - 3.2), (neck[0] + 3.2, neck[1] - 6.8), (neck[0] - 3.6, neck[1] - 6.4)], 'sv1', outline=True, edge='tl0')
    for k in range(4):                                                                 # wisps trailing from the hem
        rig.dots([(hx - 15 - k * 2.4, 4 + math.sin(n * .8 + k) * 1.4)], 'vl1')


def choir_hood(rig, p, ps, hd, back, clip, n):
    if back:
        veil = p.ramp('vl0', 'vl1', 'vl2')
        for k, dx in enumerate((-6.6, -4.6, -2.6)):
            sway = math.sin(n * .7 + k) * .8
            rig.limb((hd[0] + dx, hd[1] + 3), (hd[0] + dx - 3.4 + sway, hd[1] - 12 - k * 1.5), 1.8, .8, veil, dither=.6, outline=False)
        rig.blob((hd[0] - 2, hd[1] + 1.4), 7.4, 8.0, p.ramp('vl0', 'vl1'), outline=False, dither=.6)


def choir_crown(rig, p, ps, hd, clip, n):
    sv = p.ramp('m1', 'm2', 'sv2', 'sv3')
    rig.poly([(hd[0] - 6.4, hd[1] + 5), (hd[0] + 6.6, hd[1] + 4.6), (hd[0] + 6.4, hd[1] + 6.4), (hd[0] - 6.4, hd[1] + 6.8)], 'sv1', outline=True, edge='tl0')
    for k, (dx, hh) in enumerate(((-5.2, 5), (-2.6, 8), (0, 6), (2.8, 9), (5.4, 5.4))):
        rig.limb((hd[0] + dx, hd[1] + 6), (hd[0] + dx - .4 + (dx > 0) * .6, hd[1] + 6 + hh), 1.2, .3, sv, dither=.3)
        rig.dots([(hd[0] + dx - .4, hd[1] + 6 + hh)], 'glow')
    rig.dots([(hd[0] - 1, hd[1] + 5.8), (hd[0] + 2.4, hd[1] + 5.6)], 'glow')


STYLE_CHOIR = dict(robe=choir_robe, hood=choir_hood, head_gear=choir_crown, cloth=('tl0', 'tl1', 'tl2', 'tl3'), sleeve=True, eye='glow', upper=10.5, fore=10.)


def choir_pose(clip, n):
    ex = dict(flash=False, song=0., rings=0)
    bob = math.sin(n * 1.05) * 1.1
    if clip == 'idle':
        w = idle_wave(n)
        ps = pose(hip=(0, 28 + w * .5), lean=.02, hand_n=(9, 30 + w * .5), hand_f=(7, 31 + w * .5), head=(0, w * .3), eyes='blink' if n == 4 else 'open',
                  glow=[1, 1.1, 1.2, 1.1, 1, .9][n], jaw=[0, .4, 1, 1.6, 1, .3][n])
        ex['lift'] = 5 + bob
        ex['song'] = [.2, .3, .5, .6, .4, .2][n]
    elif clip == 'walk':
        ps = pose(hip=(0, 28 + [-.4, -.8, .6, 1.2, .8, -.6, -.4, 0][n]), lean=[.04, .06, .08, .06, .04, .02, .03, .04][n], hand_n=(9, 30), hand_f=(7, 31), jaw=.5)
        ex['lift'] = 5 + [0, -.4, 1, 1.8, 1.2, -.2, -.4, 0][n]
    elif clip == 'attack':
        hn = [(12, 44), (17, 51), (19, 57), (22, 39), (25, 37), (23, 36), (15, 36), (10, 32)][n]
        hf = [(-5, 45), (-9, 52), (-11, 58), (19, 42), (22, 40), (20, 39), (10, 37), (7, 32)][n]
        ps = pose(hip=(0, 28 + [0, .6, 1.2, 0, -.4, -.2, 0, 0][n]), lean=[-.04, -.1, -.16, .12, .18, .12, .06, .02][n], hand_n=hn, hand_f=hf,
                  tilt=[-.1, -.2, -.28, .1, .14, .08, 0, 0][n], head=(0, [0, .5, 1, 0, 0, 0, 0, 0][n]), eyes='angry', glow=2, jaw=[2, 3.4, 4.4, 5, 5, 3.4, 1.6, .6][n])
        ex['lift'] = 6 + [0, .8, 1.6, 1, .6, .2, 0, 0][n]
        ex['song'] = [.3, .6, 1., 0, 0, 0, 0, 0][n]
        ex['rings'] = {3: 1, 4: 2, 5: 3}.get(n, 0)
    else:
        h = hurt_frame(n)
        ps = pose(hip=h['hip'], lean=h['lean'], head=h['head'], tilt=h['tilt'], hand_n=(9, 30 + [4, 3, 1, 0][n]), hand_f=(7, 31 + [4, 3, 1, 0][n]), eyes=h['eyes'], jaw=h['jaw'], glow=h['glow'])
        ex['lift'] = 5 + [3, 2, 1, 0][n]
        ex['flash'] = n == 0
    return ps, ex


def sound_rings(f, rig, mouth, count, song):
    """Arcs of sound: rings that leave the mouth and widen as they go; `song` rings hug the mouth during the windup."""
    for k in range(count):
        r = 5 + k * 5.5
        for a in range(-5, 6):
            ang = a * .2
            x, y = mouth[0] + r * 1.1 * math.cos(ang) + k * 1.5, mouth[1] - r * math.sin(ang) * 1.3
            f.dots([(x, y), (x + 1, y)], 'son' if k == count - 1 else 'son2')
    for k in range(int(song * 3)):
        a = (k - 1) * .8
        f.dots([(mouth[0] + 8 + k * 2.4, mouth[1] - 2 - math.sin(a) * 3.4)], 'son')


def choir_pile(f, p, k, x0=50.):
    def gear(f, p, k, x0, gy, S):
        mask = polygon([(x0 - 22, gy + 1.4), (x0 - 12, gy - 5.5), (x0 + 2, gy - 6.5), (x0 + 14, gy - 1.5), (x0 + 15, gy + 2), (x0 - 16, gy + 2.2)])
        f.paint(gradient(mask, x0 - 22, gy + 2, x0 + 14, gy - 6, .15, .85), p.ramp('tl0', 'tl1', 'tl2', 'tl3'), dither=.45)
        f.paint(ellipsoid(x0 + 14, gy - 8, 4.4, 1.6, .4), p.ramp('m1', 'm2', 'sv2', 'sv3'), dither=.3)         # the circlet, fallen from the skull
        for i in range(3):
            f.dots([(x0 + 11 + i * 3, gy - 9.6 - (i % 2))], 'glow')
    bone_pile(f, p, k, x0, extra=gear)


def die_choir(f, p, n):
    sink = [0, 3, 9, 15, 20][n]
    ps = pose(hip=(-sink * .1, 28 - sink), lean=[-.25, -.1, -.4, -.6, -.7][n], head=(-1, -sink * .15), tilt=-.3, hand_n=(8, 24 - sink * .7), hand_f=(5, 24 - sink * .7),
              eyes='dead', jaw=5, glow=0)
    rig = Rig(f, 1.1, 44. + sink * .2, lift=max(0, 5 - sink * .5))
    skeleton(f, p, rig, ps, STYLE_CHOIR, 'die', n)
    if n == 0:
        f.whiten()


def choir(clip, n):
    f = Frame(CHOIR)
    p = CHOIR
    if clip == 'die':
        if n <= 4:
            die_choir(f, p, n)
        else:
            choir_pile(f, p, n - 5)
        return f.a
    ps, ex = choir_pose(clip, n)
    rig = Rig(f, 1.1, 42., lift=ex['lift'])
    info = skeleton(f, p, rig, ps, STYLE_CHOIR, clip, n)
    mouth = rig.P(info['head'][0] + 6.4, info['head'][1] - 5)
    if ex['rings'] or ex['song']:
        sound_rings(f, rig, mouth, ex['rings'], ex['song'])
    if clip in ('idle', 'walk', 'attack'):
        for k in range(3):
            u = (n / 8 + k / 3) % 1
            f.dots([(46 + math.sin(u * 6 + k * 2) * 12, 62 - u * 26 - k * 5)], 'mote')
    if ex['flash']:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Haldor, the Hollow King: a tall crowned skeleton in a ragged violet cape, green fire in his eye sockets, a greatsword in both hands.
# ----------------------------------------------------------------------------------------------
HOLLOWKING = palette_of(BONE, METAL, EFFECT, cp0='#160c26', cp1='#2e1a52', cp2='#4c2c86', cp3='#7a52c0', ln0='#0e3a2a', ln1='#1f7a52', gd0='#6a5420', gd1='#b8902c', gd2='#f0cc5c',
                        gd3='#fff0a0', gn0='#0f5a2a', gn1='#2fb04a', gn2='#8aff8a', gn3='#e8ffe0', glow='#7dff7d', mote='#a8ffb0')


def king_cape(rig, p, ps, neck, hip, clip, n):
    cape = p.ramp('cp0', 'cp1', 'cp2', 'cp3')
    w = [math.sin(n * .9 + k * 1.3) * (2.4 if clip in ('walk', 'attack') else 1.4) for k in range(4)]
    pts = [(neck[0] - 2, neck[1] - 1), (neck[0] + 1, neck[1] - 3), (hip[0] - 8, hip[1] - 6 + w[0] * .4), (hip[0] - 15 + w[0], 14 + w[1]), (hip[0] - 21 + w[1], 4 + w[2]),
           (hip[0] - 13 + w[2], 1 + w[3] * .5), (hip[0] - 8, 5), (hip[0] - 3 + w[3], 1)]
    rig.shaded(pts, cape, lo=.1, hi=.75, dither=.5)
    for k in range(3):
        rig.line((neck[0] - 3 - k * 1.4, neck[1] - 6 - k * 3), (hip[0] - 12 - k * 3 + w[k], 4 + k * 2), 'cp0', 1)
    rig.line((hip[0] - 15 + w[0], 14 + w[1]), (hip[0] - 21 + w[1], 4 + w[2]), 'ln1', 1)


def king_torso(rig, p, ps, chest, hip, neck, clip, n):
    x, y = chest
    rig.line((x - 3, y + 5), (x + 4, y + 4.4), 'gd1', 1)
    rig.blob((x + .6, y + 6.8), 4.8, 1.8, p.ramp('gd0', 'gd1', 'gd2', 'gd3'), dither=.3)                         # a gold gorget
    rig.dots([(x + .6, y + 6.8)], 'gn2')
    rig.shaded([(x - 6.4, y - 7), (x + 6.8, y - 7.6), (x + 6.4, y - 11), (x + 1, y - 13), (x - 6, y - 11)], p.ramp('cp0', 'cp1', 'cp2', 'cp3'), lo=.1, hi=.7, dither=.5)   # a ragged tabard
    rig.line((x - 6.4, y - 8), (x + 6.8, y - 8.4), 'gd1', 1)
    rig.blob((x + .4, y - 8), 2.2, 2.2, p.ramp('gd0', 'gd1', 'gd2', 'gd3'), dither=.3)                           # a belt buckle
    rig.dots([(x + .4, y - 8)], 'gn2')


def king_skirt(rig, p, ps, hip, clip, n):
    x, y = hip
    rig.shaded([(x - 5.6, y - 1), (x + 6, y - 1.6), (x + 7, y - 11), (x + 2.6, y - 8.4), (x - 1, y - 12.4), (x - 5.8, y - 9.4)], p.ramp('cp0', 'cp1', 'cp2', 'cp3'), lo=.12, hi=.7, dither=.5)
    rig.line((x - 5.6, y - 9.6), (x + 7, y - 10.6), 'gd1', 1)


def king_shoulder(rig, p, ps, sh_n, sh_f, clip, n):
    steel = p.ramp('m0', 'm1', 'm2', 'm3')
    rig.blob((sh_n[0] - 1.4, sh_n[1] - 1.0), 5.0, 3.4, steel, dither=.5)
    for k, dx in enumerate((-5.4, -3.2, -1.0)):                                                                    # three spikes sweeping back
        rig.limb((sh_n[0] + dx, sh_n[1] + .4), (sh_n[0] + dx - 1.6, sh_n[1] + 4.6 + k * .6), 1.3, .3, steel, dither=.3)
    rig.dots([(sh_n[0] - 1, sh_n[1] - .6)], 'gn2')


def king_crown(rig, p, ps, hd, clip, n):
    gold = p.ramp('gd0', 'gd1', 'gd2', 'gd3')
    rig.poly([(hd[0] - 7, hd[1] + 5.2), (hd[0] + 7.2, hd[1] + 4.6), (hd[0] + 7, hd[1] + 7.2), (hd[0] - 7, hd[1] + 7.8)], 'gd1', outline=True, edge='gd0')
    for dx, hh in ((-5.6, 6), (-2.8, 9), (0, 12), (2.8, 9), (5.6, 6)):
        rig.limb((hd[0] + dx, hd[1] + 7.2), (hd[0] + dx * 1.15, hd[1] + 7.2 + hh), 1.5, .3, gold, dither=.3)
        rig.dots([(hd[0] + dx * 1.15, hd[1] + 7.2 + hh)], 'gn2')
    rig.dots([(hd[0] - 4, hd[1] + 6), (hd[0], hd[1] + 6.4), (hd[0] + 4, hd[1] + 6)], 'gn1')
    # spectral green fire licking up from the sockets
    for k, ex in enumerate((hd[0] + 1.0, hd[0] + 5.4)):
        wob = math.sin(n * 1.7 + k * 2)
        rig.limb((ex, hd[1] + 3), (ex + wob * 1.4, hd[1] + 7.4 + (n % 2)), 1.6, .3, p.ramp('gn0', 'gn1', 'gn2', 'gn3'), dither=.3, outline=False)


def greatsword(rig, p, ps, hand, length=31., clip=None, n=0):
    a = ps['weapon']
    d = (math.cos(a), math.sin(a))
    nx, ny = -d[1], d[0]
    rig.limb((hand[0] - d[0] * 5, hand[1] - d[1] * 5), hand, 1.3, 1.3, p.ramp('m0', 'm1', 'm2'), dither=.3)
    rig.blob((hand[0] - d[0] * 5.4, hand[1] - d[1] * 5.4), 2.0, 2.0, p.ramp('gd0', 'gd1', 'gd2', 'gd3'), dither=.3)
    c = (hand[0] + d[0] * 1.8, hand[1] + d[1] * 1.8)
    rig.limb((c[0] - nx * 5.2, c[1] - ny * 5.2), (c[0] + nx * 5.2, c[1] + ny * 5.2), 1.3, 1.3, p.ramp('gd0', 'gd1', 'gd2', 'gd3'), dither=.3)
    tip = (hand[0] + d[0] * length, hand[1] + d[1] * length)
    rig.limb((hand[0] + d[0] * 2.8, hand[1] + d[1] * 2.8), tip, 2.7, .6, p.ramp('m0', 'm1', 'm2', 'm3', 'm4'), dither=.4)
    mid = (hand[0] + d[0] * length * .5, hand[1] + d[1] * length * .5)
    rig.dots([(mid[0] + nx * .8, mid[1] + ny * .8), (mid[0] - nx * 3 + d[0] * 5, mid[1] - ny * 3 + d[1] * 5)], 'gn2')              # a green rune on the blade


def king_weapon(rig, p, ps, hn, en, hf, clip, n):
    greatsword(rig, p, ps, hn, 31., clip, n)


STYLE_KING = dict(behind=king_cape, torso_gear=king_torso, skirt=king_skirt, shoulder=king_shoulder, head_gear=king_crown, eye='glow', weapon=king_weapon, thigh=15., shin=15.)


def king_pose(clip, n):
    ex = dict(flash=False, wave=0, trail=False)
    if clip == 'idle':
        w = idle_wave(n)
        ps = pose(hip=(0, 31 + w * .5), lean=.03 + w * .01, hand_n=(12, 33 + w * .3), hand_f=(10, 31 + w * .3), weapon=-1.45, head=(0, w * .4),
                  eyes='blink' if n == 4 else 'open', glow=[1, 1.1, 1.2, 1.1, 1, .9][n], jaw=[0, 0, .3, .5, .3, 0][n], foot_n=(7, 0), foot_f=(-6, 0), torso=21)
    elif clip == 'walk':
        ps = pose(**march(n, stomp=1.1, lean=.05), hand_n=(12, 33 + (1 if n in (2, 3) else 0)), hand_f=(10, 31), weapon=-1.35, torso=21)
        ps['hip'] = (0, ps['hip'][1] + 2)
    elif clip == 'attack':
        data = [(-.1, (8, 44), 1.5, 30.6, (6, 0), (-7, 0)), (-.2, (3, 48), 1.9, 30, (6, 0), (-8, 0)), (-.3, (-3, 49), 2.35, 29.2, (7, 0), (-10, 0)),
                (0., (9, 49), 1.3, 30, (8, 0), (-9, 0)), (.38, (19, 35), -.7, 27.8, (14, 0), (-8, 0)), (.44, (21, 27), -1.2, 27, (15, 0), (-7, 0)),
                (.28, (17, 32), -.5, 28.6, (12, 0), (-7, 0)), (.1, (12, 33), .5, 30.4, (8, 0), (-6, 0))][n]
        ps = pose(hip=(3 if n in (4, 5) else 0, data[3]), lean=data[0], hand_n=data[1], weapon=data[2], foot_n=data[4], foot_f=data[5], eyes='angry', glow=2,
                  jaw=[0, .6, 1.2, 1.4, 2.2, 1.6, .8, 0][n], head=(1 if n in (4, 5) else 0, 0), torso=21)
        ps['hand_f'] = (data[1][0] - 2.4, data[1][1] - 1.6)
        ex['wave'] = {4: 1, 5: 2}.get(n, 0)
        ex['trail'] = n in (3, 4, 5)
    else:
        h = hurt_frame(n)
        ps = pose(hip=(0, h['hip'][1] + 2), lean=h['lean'], head=h['head'], tilt=h['tilt'], hand_n=(12, 33 + [4, 3, 1, 0][n]), hand_f=(10, 31), weapon=-1.45 + [.4, .3, .15, 0][n], eyes=h['eyes'],
                  jaw=h['jaw'], glow=h['glow'], torso=21)
        ex['flash'] = n == 0
    if clip in ('idle', 'walk', 'hurt'):
        ps['hand_f'] = (ps['hand_n'][0] - 2.4, ps['hand_n'][1] - 1.6)
    return ps, ex


KING_ARC = [(2, 52), (10, 55), (18, 50), (24, 41), (27, 32), (28, 24)]


def energy_wave(f, rig, x, y, size, name='gn2'):
    """A crescent of green energy flung forward from the blade (the Hollow King's volley)."""
    for a in range(-6, 7):
        ang = a * .16
        f.dots([rig.P(x + math.cos(ang) * size * .5 + a * .1, y + math.sin(ang) * size)], name)
        f.dots([rig.P(x + math.cos(ang) * size * .5 + a * .1 + 1, y + math.sin(ang) * size)], 'gn1')


def king_pile(f, p, k, x0=50.):
    def gear(f, p, k, x0, gy, S):
        gold = p.ramp('gd0', 'gd1', 'gd2', 'gd3')
        mask = polygon([(x0 - 22, gy + 1.4), (x0 - 12, gy - 5.5), (x0 + 2, gy - 6.5), (x0 + 14, gy - 1.5), (x0 + 15, gy + 2), (x0 - 16, gy + 2.2)])
        f.paint(gradient(mask, x0 - 22, gy + 2, x0 + 14, gy - 6, .12, .75), p.ramp('cp0', 'cp1', 'cp2', 'cp3'), dither=.45)
        f.paint(capsule((x0 - 32, gy + .5), (x0 - 8, gy - 2), 2.2, 1.0), p.ramp('m0', 'm1', 'm2', 'm3', 'm4'), dither=.4)       # the greatsword
        f.paint(capsule((x0 - 34, gy + 1), (x0 - 30, gy), 1.2, 1.2), gold, dither=.3)
        f.paint(ellipsoid(x0 + 22, gy - 3, 4.6, 2.6, .3), gold, dither=.3)                                                     # the crown, rolled away
        for i in range(4):
            f.paint(capsule((x0 + 19 + i * 2.4, gy - 4), (x0 + 19.4 + i * 2.4, gy - 8 - (i % 2) * 2), 1.0, .3), gold, dither=.3)
            f.dots([(x0 + 19.4 + i * 2.4, gy - 8 - (i % 2) * 2)], 'gn2')
    bone_pile(f, p, k, x0, extra=gear)
    f.dots([(54 + k * 3, AY - 8), (46 - k * 2, AY - 10)], 'gn1')                                                          # the green fire gutters out


def hollowking(clip, n):
    f = Frame(HOLLOWKING)
    p = HOLLOWKING
    if clip == 'die':
        if n <= 4:
            die_figure(f, p, STYLE_KING, n, S=1.06)
        else:
            king_pile(f, p, n - 5)
        return f.a
    ps, ex = king_pose(clip, n)
    rig = Rig(f, 1.06, 42.)
    skeleton(f, p, rig, ps, STYLE_KING, clip, n)
    if ex['trail']:
        slash_trail(f, rig, n, KING_ARC, 'gn3')
    if ex['wave']:
        energy_wave(f, rig, 28 + ex['wave'] * 3, 30, 11 + ex['wave'] * 2)
    if clip in ('idle', 'walk'):
        for k in range(3):
            u = (n / 6 + k / 3) % 1
            f.dots([(46 + math.sin(u * 7 + k * 2) * 10, 62 - u * 26 - k * 6)], 'mote')
    if ex['flash']:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Ironwake, the Vault Colossus: a hunched granite construct, rune-carved, with a glowing core and block fists.
# ----------------------------------------------------------------------------------------------
COLOSSUS = palette_of(g0='#14161e', g1='#262a38', g2='#3c4256', g3='#565d78', g4='#7a82a0', g5='#a8afc8', ol2='#0a0b10',
                      ru0='#0f5a74', ru1='#27b4d8', ru2='#7fe8ff', ru3='#e6fcff', mo='#4a6a50', mo2='#6e9a6a', crack='#080a10',
                      dust='#8a8478', dust2='#b8b0a0', mote='#8aeaff', sock='#05070c')
GRANITE = ('g0', 'g1', 'g2', 'g3', 'g4', 'g5')
RUBBLE = {  # part -> (x, y above ground) of its resting place in the heap
    'foot_f': (-22, 3), 'leg_f': (-14, 5), 'foot_n': (15, 3), 'leg_n': (6, 6), 'pelvis': (-3, 7), 'torso': (2, 12), 'sh_f': (-24, 5), 'arm_f': (-30, 4), 'fist_f': (-33, 4),
    'head': (20, 5), 'sh_n': (22, 7), 'arm_n': (28, 4), 'fist_n': (33, 5)}


def colossus_parts(clip, n):
    """Part positions (x from the centre column, y above the ground), plus lean, glow and effect flags for one frame."""
    P = {'foot_f': (-12, 4), 'leg_f': (-9, 30, -12, 7), 'foot_n': (11, 4), 'leg_n': (8, 30, 11, 7), 'pelvis': (0, 33), 'torso': (1, 52), 'core': (3, 52),
         'sh_f': (-18, 65), 'fist_f': (-24, 30), 'head': (7, 77), 'sh_n': (19, 64), 'fist_n': (27, 29)}
    lean, glow, eyes, lift, impact, flash, rubble = 0., 1., 'open', 0., 0., False, 0.
    if clip == 'idle':
        b = [0, .5, 1, 1, .5, 0][n]
        for k in ('torso', 'core', 'sh_f', 'sh_n', 'head'):
            P[k] = (P[k][0], P[k][1] + b)
        P['fist_n'] = (P['fist_n'][0] + [0, 0, 1, 1, 0, 0][n], P['fist_n'][1] - b * .5)
        glow = [.9, 1, 1.15, 1.2, 1.1, .95][n]
        eyes = 'blink' if n == 4 else 'open'
    elif clip == 'walk':
        lift = [0, 0, 1, 2, 1, 0, 0, 0][n]
        sw = [-1, -.5, .6, 1, .7, 0, -.8, -1][n]
        P['leg_n'] = (8 + sw * 5, 30, 11 + sw * 7, 7 + max(0, sw) * 5)
        P['foot_n'] = (11 + sw * 7, 4 + max(0, sw) * 5)
        P['leg_f'] = (-9 - sw * 5, 30, -12 - sw * 7, 7 + max(0, -sw) * 5)
        P['foot_f'] = (-12 - sw * 7, 4 + max(0, -sw) * 5)
        P['fist_n'] = (27 - sw * 3, 29)
        P['fist_f'] = (-24 + sw * 3, 30)
        lean = [1, 1, 2, 3, 2, 0, -1, 0][n]
    elif clip == 'attack':
        lean = [-2, -4, -5, 3, 8, 7, 3, 0][n]
        P['fist_n'] = [(30, 34), (28, 56), (23, 76), (30, 66), (32, 11), (32, 9), (31, 19), (29, 27)][n]
        P['fist_f'] = [(-26, 34), (-22, 56), (-16, 79), (-2, 62), (25, 11), (25, 9), (-8, 22), (-24, 28)][n]
        glow = [1.2, 1.4, 1.6, 1.6, 1.5, 1.2, 1, 1][n]
        eyes = 'angry'
        impact = {4: 1., 5: .8, 6: .4}.get(n, 0.)
        if n in (4, 5):
            for k in ('torso', 'core', 'sh_f', 'sh_n', 'head'):
                P[k] = (P[k][0] + 3, P[k][1] - 4)
            P['pelvis'] = (2, 31)
    elif clip == 'hurt':
        flash = n == 0
        lean = [-5, -3, -1, 0][n]
        glow = [1.7, 1.4, 1.15, 1][n]
        eyes = 'hurt' if n < 3 else 'angry'
    else:
        flash = n == 0
        eyes = 'dead'
        lean = [0, -3, -4, 0, 0, 0, 0, 0][n]
        rubble = [0, .1, .35, .62, .88, 1, 1, 1][n]
        glow = [1.7, 1.2, .9, .7, .5, .35, .22, .12][n]
    return P, lean, glow, eyes, lift, impact, flash, rubble


def colossus(clip, n):
    f = Frame(COLOSSUS)
    p = COLOSSUS
    P, lean, glow, eyes, lift, impact, flash, rubble = colossus_parts(clip, n)
    cx = 46
    rng = rng_for('colossus', clip, n)
    ramp = p.ramp(*GRANITE)

    def at(name, key=None):
        x, y = P[key or name][:2]
        if rubble:
            delay = {'head': 0, 'fist_n': .05, 'fist_f': .05, 'sh_n': .1, 'sh_f': .1, 'arm_n': .08, 'arm_f': .08, 'torso': .15}.get(name, .25)
            t = max(0., min(1., (rubble - delay) / (1 - delay))) ** .85
            rx, ry = RUBBLE.get(name, (x, y))
            x, y = lerp(x, rx, t), lerp(y, ry, t)
        return cx + x + lean * y / 70 * 1.5, AY - y - lift

    def paint(shape, name, dither=.6):
        f.paint(shape, ramp, dither=dither)
        mask = shape[0]
        ys, xs = np.nonzero(mask)
        if len(xs) and name in ('sh_n', 'sh_f', 'torso', 'head', 'fist_n', 'fist_f', 'pelvis'):          # hewn facets: a lit top plane and a seam or two
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            top = mask & (YY < y0 + (y1 - y0) * .3) & (XX < x0 + (x1 - x0) * .75) & (DITHER > -.2)
            f.a[top] = p['g4']
            f.a[mask & (YY > y0 + (y1 - y0) * .72) & (DITHER > .15)] = p['g1']
            seam = Image.new('L', (W, H), 0)
            d = ImageDraw.Draw(seam)
            my = y0 + (y1 - y0) * (.38 + .1 * (len(name) % 3))
            d.line([(x0 + 1, my), (x0 + (x1 - x0) * .55, my + 1), (x0 + (x1 - x0) * .7, my - 2)], fill=255, width=1)
            if name in ('torso', 'sh_n', 'sh_f'):
                d.line([(x0 + (x1 - x0) * .35, y0 + 2), (x0 + (x1 - x0) * .42, my), (x0 + (x1 - x0) * .3, y1 - 3)], fill=255, width=1)
            f.a[(np.array(seam) > 0) & mask] = p['crack']
        return shape

    def runes(shape, paths, centre, thick=1):
        if glow < .15:
            return
        img = Image.new('L', (W, H), 0)
        d = ImageDraw.Draw(img)
        for path in paths:
            d.line([(centre[0] + x, centre[1] + y) for x, y in path], fill=255, width=thick)
        mask = (np.array(img) > 0) & shape[0]
        f.a[mask] = p['ru1'] if glow < 1.1 else p['ru2']
        if glow > 1.4:
            f.a[mask & (DITHER > .1)] = p['ru3']

    # legs and feet (far first)
    shapes = {}
    for side in ('f', 'n'):
        lk, fk = f'leg_{side}', f'foot_{side}'
        top = (cx + P[lk][0] + lean * 30 / 70 * 1.5, AY - P[lk][1] - lift)
        bot = (cx + P[lk][2], AY - P[lk][3] - lift)
        if rubble:
            t = min(1., rubble * 1.2)
            bot = (lerp(bot[0], at(lk)[0], t), lerp(bot[1], at(lk)[1], t))
            top = (lerp(top[0], at(lk)[0] - 5, t), lerp(top[1], at(lk)[1], t))
        shapes[lk] = paint(capsule(top, bot, 7.4, 6.2), lk)
        shapes[fk] = paint(ellipsoid(*at(fk), 9.5, 5.2), fk)
    runes(shapes['leg_n'], [[(-2, -6), (2, 0), (-2, 5)]], at('leg_n'))
    shapes['pelvis'] = paint(ellipsoid(*at('pelvis'), 13.5, 8.5), 'pelvis')
    # arms behind the torso (far), then the torso
    sh_f = at('sh_f')
    fist_f = at('fist_f')
    shapes['arm_f'] = paint(capsule(sh_f, fist_f, 6.4, 5.4), 'arm_f')
    shapes['fist_f'] = paint(ellipsoid(*fist_f, 8.6, 7.6), 'fist_f')
    shapes['torso'] = paint(ellipsoid(*at('torso'), 19.5, 20.5, lean * .02), 'torso')
    t = at('torso')
    runes(shapes['torso'], [[(-12, -8), (-6, -2), (-12, 4)], [(10, -12), (13, -4), (8, 2)], [(-4, 14), (0, 9), (6, 14)]], t, 1)
    # the core: a crystal that burns through a crack in the chest
    cx0, cy0 = at('core')
    if glow > .15:
        gem = polygon([(cx0 + 2, cy0 - 10), (cx0 + 8, cy0 - 3), (cx0 + 6, cy0 + 8), (cx0 + 2, cy0 + 11), (cx0 - 3, cy0 + 7), (cx0 - 4, cy0 - 3)])
        heat = np.clip(.35 + .65 * (1 - np.hypot((XX - cx0 - 2) / 7, (YY - cy0 - 1) / 10)), 0, 1) * min(glow, 1.4)
        f.paint((gem & shapes['torso'][0], np.clip(heat, 0, 1)), p.ramp('ru0', 'ru1', 'ru2', 'ru3'), outline=True, edge='ol2', dither=.5)
        f.line((cx0 - 3, cy0 - 3), (cx0 + 8, cy0 - 3), 'ru0', 1)
        f.line((cx0 + 2, cy0 - 10), (cx0 + 2, cy0 + 11), 'ru0', 1)
    # moss on the shoulders
    for k, ox in ((0, -4), (1, 6)):
        mask = ellipsoid(t[0] + ox, t[1] - 13 + k * 2, 8, 2.2)[0] & shapes['torso'][0]
        f.a[mask & (DITHER > -.05)] = p['mo']
    sh_n = at('sh_n')
    shapes['sh_f'] = paint(ellipsoid(*sh_f, 10.5, 9.2), 'sh_f')
    shapes['head'] = paint(ellipsoid(*at('head'), 9.6, 8.2), 'head')
    hx, hy = at('head')
    f.a[polygon([(hx - 9, hy - 3), (hx + 11, hy - 5), (hx + 11, hy - 1), (hx - 9, hy + 1)]) & shapes['head'][0]] = p['g0']          # a heavy brow
    for k, ex in enumerate((hx + 1, hx + 8)):
        if eyes == 'dead':
            f.dots([(ex, hy + 1)], 'ru0')
        elif eyes == 'blink':
            f.dots([(ex - 1, hy + 1), (ex, hy + 1), (ex + 1, hy + 1)], 'sock')
        else:
            h = 1.2 if eyes == 'angry' else 1.8
            f.flat(ellipsoid(ex, hy + 1.2, 2.4, h)[0], 'ru2' if glow > .8 else 'ru1')
    f.line((hx + 2, hy + 6), (hx + 9, hy + 5), 'sock', 1)
    # the near arm in front
    fist_n = at('fist_n')
    arm_a = (sh_n[0], sh_n[1] + 2)
    shapes['arm_n'] = paint(capsule(arm_a, fist_n, 6.8, 5.8), 'arm_n')
    shapes['sh_n'] = paint(ellipsoid(*sh_n, 11.5, 9.8), 'sh_n')
    shapes['fist_n'] = paint(ellipsoid(*fist_n, 9.4, 8.2), 'fist_n')
    runes(shapes['arm_n'], [[(-3, -4), (2, 0), (-2, 4)]], ((arm_a[0] + fist_n[0]) / 2, (arm_a[1] + fist_n[1]) / 2))
    for fx, fy in (fist_n, fist_f):                                                                                              # knuckle cracks
        f.line((fx - 4, fy - 2), (fx - 1, fy + 1), 'crack', 1)
    # rubble effects
    if impact:
        gx = cx + 29
        for k in range(10):
            a = -math.pi * (.05 + .9 * k / 9)
            d = (5 + 7 * impact) * (.7 + .5 * ((k * 5) % 3) / 2)
            f.dots([(gx + math.cos(a) * d * 1.1, AY - 2 + math.sin(a) * d * .8)], 'dust' if k % 2 else 'dust2')
        for k in range(6):
            f.dots([(gx - 12 + k * 5 + rng.uniform(-1, 1), AY - 1)], 'ru2')
        f.a[ellipsoid(gx, AY - 1, 12 * impact + 4, 2.4)[0] & (f.a == 0)] = p['ru1']
    if rubble:
        for k in range(8 + int(rubble * 6)):
            f.dots([(cx - 34 + rng.uniform(0, 70), AY - 2 - rng.uniform(0, 7) * rubble)], 'ru2' if k % 3 == 0 else 'g4')
        fit(f, 3)
    if clip in ('idle', 'walk') and glow > .9:
        for k in range(2):
            u = (n / 6 + k / 2) % 1
            f.dots([(cx + 2 + math.sin(u * 6 + k) * 9, AY - 56 - u * 26 - k * 6)], 'mote')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Rendering and PixelFlow plumbing (same contract as scripts/make_crag_sprites.py)
# ----------------------------------------------------------------------------------------------
def build_drawers():
    out = {}
    for kind in KINDS:
        draw = globals().get(kind)
        pal = globals().get(kind.upper())
        if draw and pal:
            out[kind] = (draw, pal)
    return out


def render(kind):
    draw, _ = build_drawers()[kind]
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


def preview(kinds, out, scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames = render(kind)
        palette = build_drawers()[kind][1].hex
        for problem in bounds_report(kind, frames):
            print(f'  EDGE {kind} {problem}')
        for clip, grids in frames.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#262a36')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def ids():
    meta = ASSETS / 'vault.txt'
    return json.loads(meta.read_text()).get('sprites', {}) if meta.exists() else {}


def build(kinds, replace=False):
    meta_path = ASSETS / 'vault.txt'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    known = meta.get('sprites', {})
    clash = [k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist (ids in vault.txt). Use export to preserve edits; --replace discards them.')
    for kind in clash:
        api('delete', {'sprite_id': known[kind]})
    made = {}
    for kind in kinds:
        frames = render(kind)
        bad = bounds_report(kind, frames)
        if bad:
            raise SystemExit(f'{kind} touches the canvas edge: {bad}')
        palette = build_drawers()[kind][1].hex
        np.savez_compressed(RAW / f'vault_{kind}_raw.npz', **frames)
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
        meta_path.write_text(json.dumps(meta, indent=2) + '\n')


def export(kinds):
    meta_path = ASSETS / 'vault.txt'
    meta = json.loads(meta_path.read_text())
    saved = meta['sprites']
    clips = {}
    for kind in kinds:
        packet = api('get?sprite_id=' + saved[kind])
        sp = packet.get('sprite', packet)
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
        atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
        offset = 0
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            sheet = Image.new('RGBA', (8 * W, H), '#262a36')
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
            dest = ROOT / 'test-results/vault-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'vault_{kind}.png', optimize=True)
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': saved}
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/vault_<kind>.png and vault.txt')


def verify(kinds):
    """The exported atlas must equal the freshly rendered frames pixel for pixel."""
    for kind in kinds:
        frames = render(kind)
        palette = build_drawers()[kind][1].hex
        atlas = Image.open(ASSETS / f'vault_{kind}.png').convert('RGBA')
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * W, row * H, (n + 1) * W, (row + 1) * H))
                if np.array(cell).tobytes() != np.array(rgba(frames[clip][n], palette)).tobytes():
                    raise SystemExit(f'{kind} {clip} {n} differs from the render')
        print(kind, 'atlas is pixel-identical to the render')


if __name__ == '__main__':
    drawers = build_drawers()
    for _kind, _pair in drawers.items():
        assert len(_pair[1].hex) <= 255
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    names = [a for a in sys.argv[2:] if a in drawers] or list(drawers)
    if command == 'build':
        build(names, '--replace' in sys.argv)
    elif command == 'export':
        export(names)
    elif command == 'verify':
        verify(names)
    elif command == 'preview':
        directory = next((a for a in sys.argv[2:] if a not in drawers and not a.startswith('--')), ROOT / 'test-results/vault-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_vault_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...] | verify [kind...]')
