#!/usr/bin/env python3
"""The five Reborn auras as one editable PixelFlow sprite (REBIRTH-ART, docs/rebirth.md).

A ground mark under the feet of a reborn character, one look per rebirth tier (bronze, silver, gold, cyan, rose-white).
96x40 frames, four shimmer frames per tier, tier = row. Nothing here is a filter or a gradient the browser must
recompute: the client draws one cached atlas cell per actor. `preview` writes test-results/rebirth-auras.png on the
grounds of the game, `build` makes the PixelFlow sprite (it discards hand edits), `export` reads it back into
client/assets/rebirth.png + rebirth.txt, `verify` compares them.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
W, H = 96, 40
CX, CY = 48, 19.5
FRAMES = 4
FPS = 5
# (name, dark, mid, light) per tier; the same hues as the name colours in client/rebirth.js
TIERS = [
    ('bronze', '#6d3f1d', '#b87333', '#f0b27a'),
    ('silver', '#5c6773', '#b9c4d0', '#f4f8ff'),
    ('gold', '#8a6a10', '#f2c230', '#fff1a0'),
    ('cyan', '#0c6a78', '#3dd9e8', '#d2fbff'),
    ('rose', '#9a4a66', '#ff9fc2', '#fff0f6'),
]
PALETTE = ['#00000000']
for _, *shades in TIERS:
    PALETTE += shades
PALETTE.append('#ffffff')
WHITE = len(PALETTE) - 1
assert len(set(PALETTE)) == len(PALETTE)


def shade(tier, level):
    """Palette index of a tier's dark (0), mid (1) or light (2) shade."""
    return 1 + tier * 3 + level


def plot(grid, x, y, color, size=1):
    for dx in range(size):
        for dy in range(size):
            px, py = int(round(x)) + dx - size // 2, int(round(y)) + dy - size // 2
            if 0 <= px < W and 0 <= py < H:
                grid[py, px] = color


def point(scale, angle, rx=42., ry=15.):
    return CX + rx * scale * math.cos(angle), CY + ry * scale * math.sin(angle)


def ring(grid, scale, color, dash=0, phase=0., thickness=2, rx=42., ry=15.):
    """An ellipse on the ground; `dash` > 0 breaks it into that many arcs of half length."""
    steps = 720
    for i in range(steps):
        a = i / steps * math.tau
        if dash and int((a + phase) / math.tau * dash * 2) % 2:
            continue
        x, y = point(scale, a, rx, ry)
        plot(grid, x, y, color, thickness)


def spokes(grid, count, inner, outer, color, phase=0.):
    for k in range(count):
        a = phase + k / count * math.tau
        for s in np.linspace(inner, outer, 14):
            x, y = point(s, a)
            plot(grid, x, y, color)


def sparkle(grid, x, y, color, big=False):
    plot(grid, x, y, WHITE)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        plot(grid, x + dx, y + dy, color)
    if big:
        for dx, dy in ((2, 0), (-2, 0)):
            plot(grid, x + dx, y + dy, color)


def wash(grid, tier, scale=.98, rx=42., ry=15.):
    """A sparse dither of the tier's dark shade inside the ring (one pixel in four), so the mark reads on any ground at game scale."""
    yy, xx = np.mgrid[0:H, 0:W]
    inside = ((xx - CX) / (rx * scale)) ** 2 + ((yy - CY) / (ry * scale)) ** 2 <= 1
    grid[inside & (xx % 2 == 0) & (yy % 2 == 0)] = shade(tier, 0)


def draw(tier, n):
    g = np.zeros((H, W), dtype=np.uint8)
    wash(g, tier)
    dark, mid, light = shade(tier, 0), shade(tier, 1), shade(tier, 2)
    turn = n / FRAMES
    if tier == 0:       # one clean ring and four diamonds that take turns to glint
        ring(g, 1.0, dark, thickness=4)
        ring(g, 1.0, mid)
        for k in range(4):
            a = k / 4 * math.tau
            x, y = point(1.0, a)
            plot(g, x, y, mid, 5)
            plot(g, x, y, light, 3 if (k + n) % 4 == 0 else 1)
    elif tier == 1:     # a ring, a dotted inner ring that turns, six rune ticks
        ring(g, 1.0, dark, thickness=4)
        ring(g, 1.0, mid)
        ring(g, .72, mid, dash=18, phase=turn * math.tau / 18 * 2)
        spokes(g, 6, .84, 1.08, light, phase=turn * math.tau / 6)
    elif tier == 2:     # petals: eight short arcs round a ring, lit in turn, and a faint inner ring
        ring(g, .86, dark, thickness=4)
        ring(g, .86, mid)
        ring(g, .52, dark)
        for k in range(8):
            a = k / 8 * math.tau
            lit = (k + n * 2) % 8 < 2
            for s in np.linspace(-.17, .17, 12):
                x, y = point(.97 + .07 * math.cos(s * 9), a + s)
                plot(g, x, y, light if lit else mid, 2)
    elif tier == 3:     # a four-point star over two rings, sparks orbiting
        ring(g, 1.0, dark, thickness=4)
        ring(g, 1.0, mid)
        ring(g, .64, mid, dash=24, phase=-turn * math.tau / 24 * 2)
        for k in range(4):
            a = k / 4 * math.tau
            for s in np.linspace(.2, 1.1, 30):
                x, y = point(s, a)
                plot(g, x, y, light if s < .9 else mid)
        for k in range(3):
            x, y = point(.82, turn * math.tau + k / 3 * math.tau)
            sparkle(g, x, y, light)
    else:               # three rings, twelve rays and a bright orbiting sparkle: the crown of the ladder
        ring(g, 1.02, dark, thickness=4)
        ring(g, 1.02, mid)
        ring(g, .76, light, dash=12, phase=turn * math.tau / 12 * 2)
        ring(g, .5, mid)
        spokes(g, 8, .58, .94, light if n % 2 else mid, phase=turn * math.tau / 8)
        for k in range(4):
            x, y = point(1.02, turn * math.tau + k / 4 * math.tau)
            sparkle(g, x, y, light, big=True)
        plot(g, CX, CY, WHITE, 3)
    return g


def grids():
    data = [[draw(t, n) for n in range(FRAMES)] for t in range(len(TIERS))]
    for t, frames in enumerate(data):
        assert len({f.tobytes() for f in frames}) == FRAMES, (t, 'duplicate frames')
        for n, f in enumerate(frames):
            ys, xs = np.nonzero(f)
            assert len(xs) and xs.min() > 0 and xs.max() < W - 1 and ys.min() > 0 and ys.max() < H - 1, (t, n, 'touches the edge')
    assert len({f.tobytes() for row in data for f in row}) == len(TIERS) * FRAMES, 'two tiers look alike'
    return data


def rgba(grid):
    colors = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] + [int(c[7:9], 16) if len(c) == 9 else 255] for c in PALETTE], dtype=np.uint8)
    return Image.fromarray(colors[grid], 'RGBA')


def metadata(sprite):
    return dict(frame=[W, H], anchor=[W // 2, H // 2], tiers=len(TIERS), frames=FRAMES, fps=FPS,
                names=[t[0] for t in TIERS], sprite=sprite)


def _pf():
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf
    return pf


GROUNDS = [('grass', '#5f8f4a'), ('sand', '#d9c58f'), ('snow', '#e9f0f5'), ('stone', '#7d7f86'), ('water', '#3d79a8'), ('dark', '#241f2b')]


def preview():
    data = grids()
    cell_w, cell_h = W * 2, H * 2
    sheet = Image.new('RGB', (FRAMES * cell_w + 10, len(GROUNDS) * len(TIERS) * cell_h + 10), '#444')
    for gi, (_, col) in enumerate(GROUNDS):
        for t in range(len(TIERS)):
            for n in range(FRAMES):
                tile = Image.new('RGB', (cell_w, cell_h), col)
                img = rgba(data[t][n]).resize((cell_w, cell_h), Image.Resampling.NEAREST)
                tile.paste(img, (0, 0), img)
                sheet.paste(tile, (5 + n * cell_w, 5 + (gi * len(TIERS) + t) * cell_h))
    out = ROOT / 'test-results/rebirth-auras.png'
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print(out)


def build(replace=False):
    path = ASSETS / 'rebirth.txt'
    api = _pf()
    if path.exists():
        if not replace:
            raise SystemExit('Rebirth sprite already exists; export preserves edits, build --replace discards them.')
        api.api('delete', {'sprite_id': json.loads(path.read_text())['sprite']})
    data = grids()
    np.savez_compressed(ROOT / 'scripts/rebirth_raw.npz', frames=np.stack([np.stack(row) for row in data]))
    sid = api.create('valhallasc_rebirth', W, H, len(TIERS) * FRAMES, PALETTE, fps=FPS)
    try:
        frame = 0
        for row in data:
            for grid in row:
                api.draw_grid(sid, frame, 0, grid)
                frame += 1
    except Exception:
        api.api('delete', {'sprite_id': sid})
        raise
    path.write_text(json.dumps(metadata(sid), indent=2) + '\n')
    print('rebirth', sid)


def export(verify=False):
    api = _pf()
    path = ASSETS / 'rebirth.txt'
    sid = json.loads(path.read_text())['sprite']
    sp, frames = api.load(sid)
    assert (sp['width'], sp['height'], len(frames)) == (W, H, len(TIERS) * FRAMES)
    out = Image.new('RGBA', (W * FRAMES, H * len(TIERS)))
    for t in range(len(TIERS)):
        for n in range(FRAMES):
            out.alpha_composite(Image.fromarray(api.to_rgba(frames[t * FRAMES + n][0], sp['palette']), 'RGBA'), (n * W, t * H))
    target = ASSETS / 'rebirth.png'
    if verify:
        assert out.tobytes() == Image.open(target).convert('RGBA').tobytes(), 'rebirth'
        print('Rebirth PixelFlow atlas verified')
    else:
        out.save(target, optimize=True)
        print('exported rebirth')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if cmd == 'preview':
        preview()
    elif cmd == 'build':
        build('--replace' in sys.argv)
    elif cmd == 'export':
        export()
    elif cmd == 'verify':
        export(True)
    else:
        raise SystemExit('preview | build | export | verify')
