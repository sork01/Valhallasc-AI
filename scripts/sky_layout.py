"""The plan of Bifrost Reach (zone 7, levels 30-35): pure geometry and constants shared by generate_bifrost.py (which
writes the zone) and generate_wyrdwood.py (which writes the Stormrift that leads here).

160x160 tiles, y growing southwards. A chain of floating islands over open sky, joined by rainbow-shard bridges: only the
islands and the bridges are floor, everything else is void (the zone lists the floor as row runs and the void as
rectangles the server collides with). The Stormrift lands you on the Perch (the hub, south); the ring west and east
(Windward Meadow with the galehounds, the Shardfields with the prism golems) joins at the Stormcrown (skyrays), then the
road climbs north-west to the Hall of the Fallen (einherjar) and across a long bridge to the Roc's Eyrie (thunderrocs).
Two small islets carry the first ward and a lookout spire.
"""
import math

import numpy as np

NAME = 'Bifrost Reach'
SIZE = 160
LEVELS = [30, 35]

# --- gates -------------------------------------------------------------------------------------------------------------
GATE = (80.0, 151.5)                       # the Stormrift: the way back down to the Wyrdwood
ARRIVAL = (80.0, 146.0)                    # where the Wyrdwood's Stormrift sets you down
WYRD_GATE = (24.0, 9.0)                    # the portal in the Wyrdwood's summit court (zone 6)
WYRD_ARRIVAL = (24.0, 14.0)                # where Bifrost Reach sets you down in the Wyrdwood

# --- islands: id, name, centre, half sizes, shape seed ------------------------------------------------------------------
ISLANDS = {
    'perch': dict(name="Heimdall's Perch", cx=80, cy=135, rx=30, ry=22, seed=1),
    'windward': dict(name='Windward Meadow', cx=30, cy=106, rx=22, ry=16, seed=2),
    'shards': dict(name='the Shardfields', cx=130, cy=106, rx=22, ry=16, seed=3),
    'crown': dict(name='the Stormcrown', cx=80, cy=80, rx=25, ry=18, seed=4),
    'hall': dict(name='the Hall of the Fallen', cx=38, cy=46, rx=26, ry=19, seed=5),
    'eyrie': dict(name="the Roc's Eyrie", cx=120, cy=32, rx=25, ry=18, seed=6),
    'ward': dict(name='the Windward Ward', cx=12, cy=72, rx=9, ry=8, seed=7),
    'spire': dict(name='the Lightning Spire', cx=148, cy=72, rx=9, ry=8, seed=8),
}
# --- bridges: id, polyline of integer points (axis-aligned legs), width in tiles ------------------------------------------
BRIDGE_W = 4
BRIDGES = {
    'b_west': [(56, 134), (30, 134), (30, 118)],           # the Perch to Windward Meadow
    'b_east': [(104, 134), (130, 134), (130, 118)],        # the Perch to the Shardfields
    'b_wcrown': [(46, 106), (66, 106), (66, 92)],          # Windward Meadow to the Stormcrown
    'b_scrown': [(114, 106), (94, 106), (94, 92)],         # the Shardfields to the Stormcrown
    'b_hall': [(62, 76), (36, 76), (36, 60)],              # the Stormcrown to the Hall of the Fallen
    'b_eyrie': [(50, 40), (120, 40)],                      # the Hall of the Fallen to the Roc's Eyrie (long)
    'b_ward': [(16, 96), (12, 96), (12, 78)],              # Windward Meadow to the Windward Ward
    'b_spire': [(144, 96), (148, 96), (148, 78)],          # the Shardfields to the Lightning Spire
}

# --- named places: `visit` and `hold` objectives ---------------------------------------------------------------------------
# A ward's `waves` are (seconds of progress, tag): the tag names the sleeping ambushers the generator places around it.
PLACES = [
    dict(id='sky_windcairn', name='the Windcairn', x=22.0, y=108.0, r=4.0),
    dict(id='sky_spire', name='the Lightning Spire', x=148.0, y=70.0, r=4.5),
    dict(id='sky_pylon', name='the Bifrost Pylon', x=80.0, y=80.0, r=4.5),
    dict(id='sky_hallgate', name='the Hall Gate', x=50.0, y=46.0, r=4.0),
    dict(id='sky_ward_wind', name='the Windward Ward', x=12.0, y=71.0, r=4.5),
    dict(id='sky_ward_vigil', name="the Fallen's Vigil", x=30.0, y=50.0, r=4.5),
    dict(id='sky_ward_last', name='the Last Ward', x=122.0, y=30.0, r=4.5),
]
# ward id -> (waves: (at second, tag suffix, kind, count)); the ambushers stand 6-11 tiles from the ward
WARDS = {
    'sky_ward_wind': [(15, 'a', 'galehound', 1), (40, 'b', 'galehound', 1)],
    'sky_ward_vigil': [(10, 'a', 'einherjar', 1), (40, 'b', 'einherjar', 1), (65, 'c', 'skyray', 1)],
    'sky_ward_last': [(8, 'a', 'thunderroc', 2), (50, 'b', 'prismgolem', 2), (90, 'c', 'thunderroc', 2)],
}

# --- spawn bands: kind, count, min spacing, islands the band lives on ---------------------------------------------------------
BANDS = [
    ('galehound', 8, 7.0, ['windward']),
    ('prismgolem', 8, 7.5, ['shards']),
    ('skyray', 10, 8.0, ['crown']),
    ('einherjar', 10, 7.5, ['hall']),
    ('thunderroc', 9, 8.5, ['eyrie']),
]


def island_radius_factor(theta, seed):
    """A smooth, lumpy outline: 1 +- about 15 %."""
    return (1 + .09 * math.sin(2 * theta + seed * 1.7) + .06 * math.sin(3 * theta + seed * 2.9)
            + .04 * math.sin(5 * theta + seed * .6))


def island_mask(isl):
    ii = np.arange(SIZE) + .5
    X, Y = np.meshgrid(ii, ii)
    dx, dy = (X - isl['cx']) / isl['rx'], (Y - isl['cy']) / isl['ry']
    d = np.hypot(dx, dy)
    theta = np.arctan2(dy, dx)
    lump = np.vectorize(lambda t: island_radius_factor(t, isl['seed']))(theta)
    return d <= lump


def bridge_mask(points):
    m = np.zeros((SIZE, SIZE), bool)
    h = BRIDGE_W // 2
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        x0, x1 = min(ax, bx) - h, max(ax, bx) + h
        y0, y1 = min(ay, by) - h, max(ay, by) + h
        m[y0:y1, x0:x1] = True
    return m


def masks():
    """(floor, bridges): boolean grids at one tile; bridges are the floor cells that belong to a bridge and no island."""
    isl = np.zeros((SIZE, SIZE), bool)
    for i in ISLANDS.values():
        isl |= island_mask(i)
    br = np.zeros((SIZE, SIZE), bool)
    for pts in BRIDGES.values():
        br |= bridge_mask(pts)
    return isl | br, br & ~isl, isl


def island_of(isl_mask_by_id, x, y):
    for k, m in isl_mask_by_id.items():
        if m[int(y), int(x)]:
            return k
    return None
