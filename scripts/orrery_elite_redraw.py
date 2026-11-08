#!/usr/bin/env python3
"""The Obsidian Orrery's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  mainspringwyrm  The Mainspring Wyrm (level 53, no quest): a serpent of brass cog-discs strung on a wound spring, rearing from a coil on the ground, an
                  obsidian shard for a head with a jaw of cog-teeth and one slit eye of amber light, a back of black glass spines. Winds up by drawing
                  the neck back into a tight S and the spring tightening; the strike is a lunge down and forward, the neck unwinding to full length.
                  Dies when the spring snaps: the spark runs down the coil, the discs lose their string and roll apart one by one, the head drops last
                  and the eye goes dark.
The manifest is client/assets/orreryelites.txt. The shading helpers are copied from astral_elite_redraw.py.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import kindframe
import lapis_slime_redraw as L
from lapis_slime_redraw import (BasePainter, OUTLINE, BONE, PEARL, clamp01, curves, dying, settle, polar, mix, mixp, sm, bez, dust, old, Rig)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/orrery-elites'
REGISTRY = ROOT / 'scripts/orrery_elite_sources.txt'
MANIFEST = ASSETS / 'orreryelites.txt'
PREFIX = 'valhallasc_orrery_elite_'
KINDS = ['mainspringwyrm']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(mainspringwyrm=(192, 160, 76, 152))
SCALE = dict(mainspringwyrm=.62)
FLYING = ()
_mine = [
    '#05060c', '#141826', '#2a3046', '#4a5470', '#7a86a8',   # GLASS (the obsidian head and spines)
    '#2a1a06', '#7a4c14', '#c8922a', '#f0c860', '#fff4b8',   # BRASS (the cog-discs and teeth)
    '#3a1004', '#a8340c', '#f07018', '#ffb040', '#fff0c0',   # AMBER (the eye, the spark, the glow)
    '#0e1018', '#2c3040', '#586070', '#98a0b4', '#d8dcec',   # STEEL (the spring, the hubs)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
GLASS, BRASS, AMBER, STEEL = [_i[5 * k:5 * k + 5] for k in range(4)]


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kindframe.check_frame(*KIND_FRAMES[kind])
        self.S = SCALE.get(kind, 1.)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax + dx * self.S

    def pos(self, x, y):
        return round(self.cx + x * self.S), min(round(self.ay - y * self.S), self.ay + 4)      # nothing sinks more than four rows under the ground

    def ellipse(self, x, y, rx, ry, col):
        super().ellipse(x, y, rx * self.S, ry * self.S, col)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width * self.S)))

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        super().ball(x, y, rx * self.S, ry * self.S, ramp, ang)


# ---- shading toolkit (copied from bifrost_elite_redraw.py) ----------------------------------------------------------------------
def smooth(pts, n=5, closed=True):
    P = list(pts)
    m = len(P)
    out = []
    for i in range(m if closed else m - 1):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        if not closed:
            p0 = P[max(i - 1, 0)]
            p3 = P[min(i + 2, m - 1)]
        for k in range(n):
            t = k / n
            out.append(tuple(.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    return out


def capsule(p, q, w0, w1, caps=5):
    dx, dy = q[0] - p[0], q[1] - p[1]
    ln = math.hypot(dx, dy) or 1.
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    pts = [(p[0] + nx * w0 / 2, p[1] + ny * w0 / 2), (q[0] + nx * w1 / 2, q[1] + ny * w1 / 2)]
    for k in range(1, caps):
        a = math.pi * k / caps
        pts.append((q[0] + (nx * math.cos(a) + ux * math.sin(a)) * w1 / 2, q[1] + (ny * math.cos(a) + uy * math.sin(a)) * w1 / 2))
    pts += [(q[0] - nx * w1 / 2, q[1] - ny * w1 / 2), (p[0] - nx * w0 / 2, p[1] - ny * w0 / 2)]
    for k in range(1, caps):
        a = math.pi * k / caps
        pts.append((p[0] - (nx * math.cos(a) - ux * math.sin(a)) * w0 / 2, p[1] - (ny * math.cos(a) - uy * math.sin(a)) * w0 / 2))
    return pts


def shaded(a, pts, ramp, light=(-.6, -.8), base=.58, contrast=1., outline=OUTLINE, edge=True, grain=0.):
    P = [a.pos(*p) for p in pts]
    m = Image.new('1', (a.w, a.h), 0)
    ImageDraw.Draw(m).polygon(P, fill=1)
    mk = np.array(m, bool)
    ys, xs = np.nonzero(mk)
    if not xs.size:
        return
    cx, cy = xs.mean(), ys.mean()
    proj = (xs - cx) * light[0] + (ys - cy) * light[1]
    ext = max(1e-6, np.abs(proj).max())
    v = base + .5 * contrast * proj / ext
    thr = (((xs % 4) * 5 + (ys % 4) * 3) % 16) / 16. - .5
    v += thr * .22
    if grain:
        v += ((np.sin(xs * 12.9898 + ys * 78.233) * 43758.5453) % 1 - .5) * grain
    idx = np.clip((v * (len(ramp) - 1) + .5).astype(int), 0, len(ramp) - 1)
    arr = np.array(a.im)
    rows = np.array(ramp)[idx]
    inner = ndimage.binary_erosion(mk, iterations=1)
    arr[ys, xs] = rows
    if edge:
        rim = mk & ~inner
        ry, rx = np.nonzero(rim)
        lit = ((rx - cx) * light[0] + (ry - cy) * light[1]) > 0
        arr[ry[~lit], rx[~lit]] = ramp[0]
        if outline is not None:
            arr[ry[lit], rx[lit]] = outline
    a.im.paste(Image.fromarray(arr, 'P'), mask=Image.fromarray((mk * 255).astype(np.uint8)))


def glow(a, x, y, r, ramp, strength=1.):
    px, py = a.pos(x, y)
    R = max(1., r * a.S)
    arr = np.array(a.im)
    for yy in range(max(0, int(py - R) - 1), min(a.h, int(py + R) + 2)):
        for xx in range(max(0, int(px - R) - 1), min(a.w, int(px + R) + 2)):
            d = math.hypot(xx - px, yy - py) / R
            if d > 1:
                continue
            v = (1 - d) ** 1.4 * strength
            thr = (((xx % 4) * 5 + (yy % 4) * 3) % 16) / 16.
            if v > thr * .9 + .08:
                arr[yy, xx] = ramp[min(len(ramp) - 1, int(v * len(ramp)))]
    a.im.paste(Image.fromarray(arr, 'P'))


def tapered(a, spine, w0, w1, ramp, base=.55, contrast=1., n=None, edge=True):
    """A shape that follows a spine (list of points) from width w0 to w1."""
    n = len(spine)
    left, right = [], []
    for i, p in enumerate(spine):
        q = spine[min(i + 1, n - 1)]
        r = spine[max(i - 1, 0)]
        dx, dy = q[0] - r[0], q[1] - r[1]
        ln = math.hypot(dx, dy) or 1.
        nx, ny = -dy / ln, dx / ln
        wd = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append((p[0] + nx * wd, p[1] + ny * wd))
        right.append((p[0] - nx * wd, p[1] - ny * wd))
    shaded(a, left + right[::-1], ramp, base=base, contrast=contrast, edge=edge)


def ring_arc(a, cx, cy, rx, ry, tilt, t0, t1, col, width=1, steps=24):
    pts = []
    for k in range(steps + 1):
        t = t0 + (t1 - t0) * k / steps
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)))
    a.line(pts, col, width)
    return pts


def spine_points(clip, n, w, st, dn, ph, bob, recoil):
    """The centre line of the body, head first: a coil on the ground that rears into an S-neck, drawn back on the wind-up and thrown out on the strike."""
    back = w * .95
    out = st
    head = (56 - back * 34 + out * 40, 108 + bob * .6 + back * 16 - out * 66)
    neck2 = (26 - back * 24 + out * 26, 126 + bob * .4 + back * 12 - out * 46)
    neck3 = (-6 - back * 12 + out * 10, 100 + back * 6 - out * 30)
    body1 = (-30 + back * 4 - out * 6, 62 - out * 14)
    body2 = (-58 + out * 4, 34 - out * 4)
    coil1 = (-92, 16)
    coil2 = (-104, 26)
    coil3 = (-84, 36)
    coil4 = (-62, 24)
    pts = [head, neck2, neck3, body1, body2, coil1, coil2, coil3, coil4]
    if clip == 'walk':                                                  # a slither: the wave runs down the body
        pts = [(x, y + math.sin(ph - i * .75) * (5 if i < 5 else 2)) for i, (x, y) in enumerate(pts)]
    elif clip == 'idle':
        pts = [(x + math.sin(ph + i * .5) * 1.5, y + math.sin(ph * 1.0 + i * .6) * 2.2) for i, (x, y) in enumerate(pts)]
    return pts


def resample(path, count):
    """`count` points at equal arc length along a smoothed path."""
    pts = smooth(path, 8, closed=False)
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    out = []
    for k in range(count):
        want = total * k / (count - 1)
        acc = 0.
        for i, s_ in enumerate(seg):
            if acc + s_ >= want or i == len(seg) - 1:
                t = (want - acc) / (s_ or 1.)
                out.append(mixp(pts[i], pts[i + 1], max(0., min(1., t))))
                break
            acc += s_
    return out


def cog(a, x, y, r, spin, ramp, lit=1.):
    """One brass disc: a toothed rim, a face with a dark hub and a bright axle pin."""
    teeth = 10
    outer = []
    for i in range(teeth * 2):
        ang = spin + i * math.pi / teeth
        rr = r * (1.0 if i % 2 == 0 else .78)
        outer.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
    shaded(a, outer, ramp, base=.55 * lit + .15, contrast=1.1)
    a.ball(x, y, r * .58, r * .58, ramp[1:4] if lit > .2 else STEEL[:3])
    a.ball(x, y, r * .3, r * .3, GLASS[:3])
    a.ball(x - r * .08, y + r * .08, max(1.2, r * .12), max(1.2, r * .12), STEEL[3:])


# ---- the Mainspring Wyrm --------------------------------------------------------------------------------------------------------
def mainspringwyrm(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    lunge = st * 3 - w * 6 + recoil
    a = Painter('mainspringwyrm', lunge)
    dying_ = clip == 'die' or (clip == 'hurt' and n == 1)
    undone = sm(clamp01(dn * 1.1))                                      # how far the spring has let go
    path = spine_points(clip, n, w, st, dn, ph, bob, recoil)
    COUNT = 12
    centres = resample(path, COUNT)                                     # head first
    radii = [15, 17, 18, 18, 17, 16, 15, 14, 12, 10, 8, 6]
    # the segments fall one by one in the death: tail first, so the head is the last thing standing
    fall = []
    for i in range(COUNT):
        delay = (COUNT - 1 - i) / (COUNT - 1) * .55
        fall.append(sm(clamp01((undone * 1.45 - delay) * 1.8)))
    # --- the wound spring through the middle of the body, drawn first so the discs sit on it
    spring = [(c[0], c[1]) for c in centres]
    for k in range(len(spring) - 1):
        if fall[k] < .05 and fall[k + 1] < .05:
            a.line([spring[k], spring[k + 1]], STEEL[1], 5)
            a.line([spring[k], spring[k + 1]], STEEL[3], 2)
    # --- the back: black glass spines along the upper side of the neck and body
    for i in range(1, COUNT - 3):
        cx_, cy_ = centres[i]
        nx, ny = centres[i - 1][0] - centres[i + 1][0], centres[i - 1][1] - centres[i + 1][1]
        ln = math.hypot(nx, ny) or 1.
        ux, uy = -ny / ln, nx / ln
        if uy < 0:
            ux, uy = -ux, -uy
        gone = fall[i]
        tip = (cx_ + ux * (radii[i] + 15 - gone * 8), cy_ + uy * (radii[i] + 15 - gone * 8))
        base1 = (cx_ + ux * radii[i] * .7 - uy * 5, cy_ + uy * radii[i] * .7 + ux * 5)
        base2 = (cx_ + ux * radii[i] * .7 + uy * 5, cy_ + uy * radii[i] * .7 - ux * 5)
        pos0 = (0, 0)
        if gone < .85:
            shaded(a, [base1, tip, base2], GLASS, base=.62, contrast=1.0)
    # --- the discs, tail to head, each rolling off the string as it falls
    placed = list(centres)
    for i in range(COUNT - 1, -1, -1):
        cx_, cy_ = centres[i]
        r = radii[i]
        f = fall[i]
        gx = cx_ + (-28 + i * 7 + math.sin(i * 2.3) * 14) * f              # the disc rolls off the line of the body
        gy = r * .9 + 1
        px_ = cx_ * (1 - f) + gx * f
        py_ = cy_ * (1 - f) + gy * f + math.sin(f * math.pi) * 14 * (1 - f)
        placed[i] = (px_, py_)
        spin = ph * (1 if i % 2 else -1) * 1.1 + i * .4 + f * (3 + i * .5)
        if clip == 'attack':
            spin += (st * 2.2 - w * 1.4) * (1 if i % 2 else -1)
        lit = 1. - undone * .6
        cog(a, px_, py_, r, spin, BRASS, lit)
    # --- the head: an obsidian shard with a cog-tooth jaw and a single amber slit eye, set on the first disc
    hx, hy = placed[0]
    ang = (-.35 * st + .22 * w) + (undone * -1.15)                          # the head dips on the strike, lifts a little on the wind-up and drops dead
    gape = (w * 1.0 + st * .5) if clip == 'attack' else (.35 + .08 * math.sin(ph) if clip == 'idle' else (.15 if walk else (.5 if clip == 'hurt' and n == 1 else undone * .3)))
    HS = 1.22
    def rot(p):
        x, y = p[0] * HS, p[1] * HS
        return hx + x * math.cos(ang) - y * math.sin(ang), hy + x * math.sin(ang) + y * math.cos(ang)
    low_open = gape * .5
    def lowrot(p):
        x, y = p
        c, s = math.cos(-low_open), math.sin(-low_open)
        return rot((x * c - (y + 4) * s, x * s + (y + 4) * c - 4))
    # lower jaw first (behind), brass plate with teeth
    jaw = [lowrot(p) for p in [(-6, -4), (16, -9), (44, -8), (50, -3), (30, 0), (4, 2)]]
    shaded(a, jaw, BRASS, base=.42, contrast=.9)
    for k in range(5):
        tx = 10 + k * 8
        p0, p1 = lowrot((tx, -2)), lowrot((tx + 5, -2))
        tip = lowrot((tx + 2.5, 6 + gape * 4))
        a.poly([p0, p1, tip], BRASS[4])
    # the throat: a dark gap with amber light
    if gape > .12:
        shaded(a, [rot((2, 0)), rot((50, 1)), lowrot((50, -1)), lowrot((2, -1))], AMBER, base=.18, contrast=.4, edge=False)
    skull = [rot(p) for p in [(-14, -6), (-12, 12), (4, 20), (28, 18), (52, 7), (58, 1), (44, -1), (10, -2)]]
    shaded(a, skull, GLASS, base=.6, contrast=1.1)
    for k in range(5):                                                  # upper teeth: cogs cut into the jaw line
        tx = 8 + k * 9
        p0, p1 = rot((tx, 0)), rot((tx + 6, 0))
        tip = rot((tx + 3, -7 - gape * 3))
        a.poly([p0, p1, tip], BRASS[3])
    for k, (bx, by, bl) in enumerate(((-4, 14, 26), (6, 18, 30), (16, 18, 24))):      # three swept-back glass horns
        shaded(a, [rot((bx, by)), rot((bx + 8, by - 2)), rot((bx - bl, by + bl * .55))], GLASS, base=.7 - k * .05, contrast=.9)
    ex, ey = rot((30, 9))
    if dying_ and n >= 2:
        a.line([(ex - 3, ey), (ex + 3, ey)], OUTLINE, 1)
    else:
        glow(a, ex, ey, 9 + w * 3 + st * 5, AMBER, .85)
        a.poly([(ex - 6, ey + 1), (ex + 5, ey - 2), (ex + 6, ey + 1), (ex - 5, ey + 3)], AMBER[3])
        a.line([(ex - 5, ey + 1), (ex + 5, ey - 1)], AMBER[4], 1)
    a.line([rot((14, 12)), rot((36, 10))], OUTLINE, 2)                  # a hard brow over the slit
    if dying_ and 1 <= n <= 4:                                          # the spring snaps: a spark runs down the coil
        for k in range(4):
            sx, sy = centres[min(COUNT - 1, 3 + k * 2)]
            glow(a, sx, sy, 8 - k, AMBER, .9)
    if clip == 'attack' and n in (5, 6):                                # the lunge lands: dust and a flash on the ground
        for k in range(4):
            dust(a, 70 + k * 10, 4 + (k % 2) * 3, 3.4 - k * .5, PEARL)
    if dn > .75:
        for k in range(4):
            dust(a, -60 + k * 26, 3 + (k % 2) * 2, 2.8, PEARL)
    return a


DRAW = dict(mainspringwyrm=mainspringwyrm)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/orrery_elite_{kind}_raw.npz'


def build():
    L.STRICT = True
    saved = registry()
    names = {s['name'] for s in old.api('list')['sprites']}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        data = frames(kind)
        name = PREFIX + kind + os.environ.get('SOURCE_SUFFIX', '')
        assert name not in names, name
        np.savez_compressed(raw(kind), **data)
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(name=name, width=kw, height=kh, frames=34, layers=1, fps=10, palette=PALETTE, persist=True,
                                     ops=[dict(op='set_layer', layer=0, name=kind)]))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, L.api_draw(sid, 0, data), 'frames saved', flush=True)


def refresh():
    L.STRICT = True
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(raw(kind), **data)
        print('Refreshed', kind, saved[kind], L.api_draw(saved[kind], 0, data), 'frames', flush=True)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    clips, off = {}, 0
    for row, (clip, (fps, count)) in enumerate(L.CLIPS.items()):
        clips[clip] = dict(fps=fps, n=count, row=row, editorStart=off)
        off += count
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='orrery-elite')
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, idle = 0, []
        for row, (clip, (_, count)) in enumerate(L.CLIPS.items()):
            for n in range(count):
                im = rgba(L.cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                b = im.getbbox()
                kindframe.check_bounds(b, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                if clip == 'idle':
                    idle.append(b)
            offset += count
        meta['sprites'][kind] = saved[kind]
        meta['tops'][kind] = kindframe.top_of(idle, kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlas.save(ASSETS / f'orreryelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'orreryelites_{kind}.png').convert('RGBA')
        offset = 0
        for row, (clip, (_, count)) in enumerate(L.CLIPS.items()):
            seen = set()
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(L.cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n)
                seen.add(cell.tobytes())
            offset += count
            if clip in ('attack', 'die'):
                assert len(seen) == 8, (kind, clip, 'needs eight distinct frames', len(seen))
        print(kind, '34 editor frames equal the atlas; attack and death have eight distinct frames', flush=True)


if __name__ == '__main__':
    {'preview': L.preview, 'montage': L.montage, 'extents': L.extents, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'montage']()
