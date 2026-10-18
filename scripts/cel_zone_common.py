"""Shared helpers for the cel-shaded redraws of zones 13-15 (astral_redraw, prism_redraw, orrery_redraw).

They sit on the Art/mk/timing toolkit of cathedral_reliquary_redraw.py (hard bands, dark outlines, big glossy
eyes). Coordinates are Art coordinates: x from the foot anchor (48), y up from the ground row (90).
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cathedral_reliquary_redraw as R
from make_crag_sprites import AX, AY, CLIPS, H, W, rgba

ROOT = Path(__file__).resolve().parents[1]


def timing(clip, n):
    """The shared animation curves with idle/walk bobs that never repeat inside a clip (the build asserts that
    nearly every frame of a clip differs)."""
    T = R.timing(clip, n)
    if clip == 'idle':
        T['bob'] = 1.1 * (1 - math.cos(2 * math.pi * n / 6 + .45))
    elif clip == 'walk':
        T['bob'] = abs(math.sin(n * math.pi / 4 + .3)) * 2
    return T


def star(a, x, y, r, name, thin=.3):
    """A four-point sparkle."""
    t = r * thin
    a.poly([(x, y + r), (x + t, y + t), (x + r, y), (x + t, y - t), (x, y - r), (x - t, y - t), (x - r, y),
            (x - t, y + t)], name, out=False)


def diamond(a, x, y, w, h, name, out=False):
    a.poly([(x, y + h), (x + w, y), (x, y - h), (x - w, y)], name, out=out)


def circle_ring(a, x, y, r_out, r_in, ring, inner):
    """A flat disc `inner` inside a ring `ring` (a corona or halo)."""
    from make_crag_sprites import ellipsoid
    cx, cy = a.g(x, y)
    a.f.flat(ellipsoid(cx, cy, r_out, r_out * a.sy)[0], ring, outline=True)
    a.f.flat(ellipsoid(cx, cy, r_in, r_in * a.sy)[0], inner)


def crystal(a, x, y, w, h, group, tilt=0., out=True):
    """A hexagonal crystal standing on (x, y): two flat faces and a pointed top."""
    top = (x + tilt, y + h)
    a.band([(x - w, y), (x - w * .8, y + h * .62), top, (x + w * .8, y + h * .62), (x + w, y)], group, out=out)
    a.line((x - w * .35, y + h * .15), (x - w * .1 + tilt * .5, y + h * .72), group + '3' if f'{group}3' in a.p.names
           else group + '2', 1)


def gear_points(cx, cy, r, teeth, phase=0., depth=.22):
    pts = []
    for k in range(teeth * 4):
        ang = phase + k * math.pi / (teeth * 2)
        rr = r * (1 + depth) if k % 4 in (0, 1) else r
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    return pts


def preview(kinds, palettes, draw, out, bg='#2c3a44', scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        hexes = palettes[kind].hex
        for clip, (_, count) in CLIPS.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), bg)
            d = ImageDraw.Draw(sheet)
            for n in range(count):
                grid = draw(kind, clip, n)
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, hexes), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                ys, xs = np.nonzero(grid)
                if len(xs) and (xs.min() < 1 or ys.min() < 1 or xs.max() > W - 2 or ys.max() > H - 2):
                    print(f'  EDGE {kind} {clip} {n} x {xs.min()}-{xs.max()} y {ys.min()}-{ys.max()}')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(
                out / f'{kind}_{clip}.png')
    line = Image.new('RGBA', (len(kinds) * W, H), bg)
    for i, kind in enumerate(kinds):
        line.alpha_composite(rgba(draw(kind, 'idle', 0), palettes[kind].hex), (i * W, 0))
    line.resize((line.width * 3, line.height * 3), Image.Resampling.NEAREST).save(out / 'lineup.png')
    # one contact sheet with a pose from every clip, for a quick look
    poses = (('idle', 0), ('walk', 2), ('attack', 2), ('attack', 4), ('hurt', 1), ('die', 3), ('die', 7))
    sheet = Image.new('RGBA', (len(poses) * W, len(kinds) * H), bg)
    for r, kind in enumerate(kinds):
        for c, (clip, n) in enumerate(poses):
            sheet.alpha_composite(rgba(draw(kind, clip, n), palettes[kind].hex), (c * W, r * H))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).save(out / 'poses.png')


def mku(**groups):
    """`mk` that nudges a repeated hex by one blue step instead of asserting (shared golds and shines across groups)."""
    seen = set(R.BASE.values())
    out = {}
    for name, value in groups.items():
        vals = [value] if isinstance(value, str) else list(value)
        fixed = []
        for c in vals:
            while c.lower() in seen:
                c = '#%02x%02x%02x' % (int(c[1:3], 16), int(c[3:5], 16), (int(c[5:7], 16) + 1) % 256)
            seen.add(c.lower())
            fixed.append(c)
        out[name] = fixed[0] if isinstance(value, str) else tuple(fixed)
    return R.mk(**out)
