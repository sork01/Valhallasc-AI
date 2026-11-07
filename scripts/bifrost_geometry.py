"""The floor of Bifrost Reach as the owner's painted atlas shows it (zone 7 of the shapes pilot): six floating islands and the rainbow
bridges between them, traced from the painting. Pure geometry: bifrost_design.py lays the zone on it.

Tile = painted px * 2048/1758 - T (zone_shapes: k = 1.0), T = shape.T. The painting shows a cloud ring round a purple sky with six green islands
joined by pink rainbow ribbons and four pink landing pads; `islands()` reads the green out of the picture (colour classes, closing, opening,
a gaussian smooth, so the silhouettes are the painter's), the bridges and pads below are authored on top of the same picture:

    python3 scripts/bifrost_geometry.py OUT.png       draw the floor (read only)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

# island id -> (name, a tile inside the painted island that picks the component)
ISLANDS = {
    'nw': ('Windward Meadow', (105, 123)),
    'north': ('the Hall of the Fallen', (157, 65)),
    'ne': ("the Roc's Eyrie", (262, 96)),
    'hub': ("Heimdall's Perch", (190, 195)),
    'se': ('the Stormcrown', (294, 252)),
    'south': ('the Shardfields', (232, 303)),
}
BRIDGE_W = 5.0

# Pads: where an updraft opens. Each is an ellipse (cx, cy, rx, ry) of bridge floor.
PADS = {
    'stormrift': (108, 181, 19, 13),      # the Wyrdwood's Stormrift, the painted ring pad in the south-west
    'pylon': (195, 100, 28, 12),          # the broken pylon in the heart of the Reach (two pink bars and an orb)
    'maelstrom': (292, 186, 11, 9),       # the orb in the east: Rán's Deep
    'nacre': (324, 300, 9, 8),            # the south-east pad: Nacrehold
    'crags': (227, 333, 9, 7),            # the Shardfields' southern tip: the Cragsfall updraft
}
# Bridges: id -> list of points (diagonals allowed, the painted ribbons arc)
BRIDGES = {
    'b_pad_nw': [(96, 168), (96, 158)],                         # the Stormrift pad up onto Windward Meadow
    'b_pad_hub': [(126, 184), (140, 186)],                      # the Stormrift pad east to the Perch's island
    'b_hub_pylon': [(205, 164), (205, 108)],                    # the Perch north along the painted sliver to the pylon
    'b_pylon_nw': [(172, 103), (158, 103)],                     # the pylon west to Windward Meadow
    'b_pylon_ne': [(217, 103), (230, 108)],                     # the pylon east to the Roc's Eyrie
    'b_pylon_north': [(190, 96), (190, 86), (168, 86)],         # the pylon north to the Hall of the Fallen
    'b_north_ne': [(176, 67), (208, 64), (236, 53), (266, 51)],  # the long painted ribbon over the top
    'b_hub_south': [(203, 232), (203, 280)],                    # the Perch south to the Shardfields
    'b_hub_se': [(232, 226), (234, 254), (264, 254)],           # the painted L: the Perch to the Stormcrown
    'b_south_se': [(250, 306), (298, 310), (298, 282)],         # the Shardfields east to the Stormcrown
    'b_ne_maelstrom': [(276, 166), (284, 178)],                 # the Eyrie's southern tail to the Rán's Deep pad
    'b_maelstrom_se': [(292, 193), (292, 220)],                 # that pad south to the Stormcrown
    'b_se_nacre': [(312, 282), (322, 296)],                     # the Stormcrown's tip to the Nacrehold pad
}


def tiles(shape_T, size, img, ps):
    ys, xs = np.mgrid[0:size, 0:size]
    px = np.clip(((xs + .5 + shape_T[0]) * ps).astype(int), 0, img.shape[1] - 1)
    py = np.clip(((ys + .5 + shape_T[1]) * ps).astype(int), 0, img.shape[0] - 1)
    return img[py, px].astype(int)


def thick(points, width, n):
    """Cells within width/2 of a polyline (diagonals allowed)."""
    ys, xs = np.mgrid[0:n, 0:n]
    cx, cy = xs + .5, ys + .5
    d = np.full((n, n), 1e9)
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        dx, dy = bx - ax, by - ay
        t = np.clip(((cx - ax) * dx + (cy - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
        d = np.minimum(d, np.hypot(cx - ax - t * dx, cy - ay - t * dy))
    return d <= width / 2


def ellipse(cx, cy, rx, ry, n, seed=0):
    ys, xs = np.mgrid[0:n, 0:n]
    dx, dy = (xs + .5 - cx) / rx, (ys + .5 - cy) / ry
    th = np.arctan2(dy, dx)
    lump = 1 + .06 * np.sin(3 * th + seed) + .04 * np.sin(5 * th + seed * 1.7)
    return np.hypot(dx, dy) <= lump


def islands(shape_T, size, floor):
    """name -> boolean mask, read from the painted atlas (see the module docstring)."""
    from PIL import Image
    img = np.array(Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB'))
    import atlas_geography
    atlas, _ = atlas_geography.generate()
    ps = img.shape[1] / atlas['width']
    rgb = tiles(shape_T, size, img, ps)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    green = (g > r + 12) & (g > b - 6) & (g > 110) & floor
    m = ndimage.binary_closing(green, iterations=3)
    m = ndimage.binary_opening(m, iterations=2)
    m = ndimage.binary_fill_holes(m)
    lab, _ = ndimage.label(m)
    out = {}
    for key, (name, (x, y)) in ISLANDS.items():
        c = lab[y, x]
        assert c, f'{name}: nothing green at ({x}, {y})'
        comp = (lab == c).astype(float)
        comp = ndimage.gaussian_filter(comp, 2.2) > .5            # the painter's silhouette, minus the pixel noise
        comp &= floor
        out[key] = comp
    return out


def masks(shape_T, size, floor):
    """(walkable, bridge cells, {island: mask}, {pad: mask}, {bridge: mask})."""
    isl = islands(shape_T, size, floor)
    pads = {k: ellipse(*v, size, seed=i) for i, (k, v) in enumerate(PADS.items())}
    brs = {k: thick(p, BRIDGE_W, size) for k, p in BRIDGES.items()}
    land = np.zeros((size, size), bool)
    for m in isl.values():
        land |= m
    span = np.zeros((size, size), bool)
    for m in list(pads.values()) + list(brs.values()):
        span |= m
    walk = land | span
    lands = list(isl.values()) + list(pads.values())
    for k, m in brs.items():
        grown = ndimage.binary_dilation(m, iterations=1)
        assert sum(bool((grown & mm).any()) for mm in lands) >= 2, f'bridge {k} does not join two pieces of land'
    return walk, span & ~land, isl, pads, brs


if __name__ == '__main__':
    import zone_shapes as zs
    from PIL import Image
    cfg = zs.config()
    atlas = zs.Atlas()
    old = json.loads((ROOT / 'world/zone-shapes/preshape-07.txt').read_text())
    g = zs.shape_geometry(cfg, atlas, 7, old)
    walk, span, isl, pads, brs = masks(g['T'], g['size'], g['floor'])
    n = g['size']
    img = np.zeros((n, n, 3), np.uint8)
    img[g['floor']] = (40, 20, 70)
    img[walk] = (60, 200, 90)
    img[span] = (255, 120, 210)
    lab, k = ndimage.label(walk)
    print('walkable', int(walk.sum()), 'bridges', int(span.sum()), 'components', k)
    for key, m in isl.items():
        print(key, int(m.sum()))
    Image.fromarray(img).resize((n * 2, n * 2), Image.NEAREST).save(sys.argv[1])
