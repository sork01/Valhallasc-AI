#!/usr/bin/env python3
"""Writes Skaldholm (zone 4, a safe walled city) and its gate in the Rimeveil summit into world/map.txt.

Skaldholm is a 160x160 city with no enemies. A wall with towers surrounds 128x128 tiles; the only way in is the Great
Gate in the south wall, reached from a forecourt where the glacier gate drops you. Inside: the Grand Avenue (north-south)
and the Trade Road (east-west) cross at a round plaza with a huge fountain; four minor streets make a grid; about a
hundred timber houses line the streets; the Steward's Hall closes the avenue in the north, the Cathedral and the Archive
stand beside its court; the Meeting Stone stands in its own court near the gate; the NW block is a garden, the NE block
an orchard; markets, a smithy, a tavern with a stage and stables fill the rest. Twenty-eight people stand about the city
and fourteen more walk loops (their positions are a pure function of the world clock, see model.rs Npc::position_at).

The Rimeveil summit gains a second gate (the Skaldholm Gate). Re-running replaces zone 4 and that gate and leaves everything
else alone. Run it after generate_rimeveil.py and generate_gloamfen.py when those are rebuilt (they leave the later
zones alone but not their own gates). Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
"""
import argparse
import json
import spark_travel
import math
from pathlib import Path
import random
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_gloamfen as fen                   # noqa: E402  (flood fill helpers and the summit constants)
import skaldholm_content as content               # noqa: E402
import undervault_layout as uv                    # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
NAME = 'Skaldholm'
GLACIER = 'Rimeveil Glacier'
SIZE = 160
ARRIVAL = (80.0, 150.0)                           # where the glacier gate drops you
RETURN_GATE = (80.0, 155.0)                       # the way back to the Rimeveil summit
FOUNTAIN = (80.0, 76.0)
WALL = dict(x0=16.0, x1=144.0, y0=12.0, y1=140.0)
GATE_HALF = 5.9                                   # the Great Gate is open between 80 +- 5.9 (towers stand outside it)
TOWER = 3.4
CITY = dict(name=NAME, x0=17, x1=143, y0=13, y1=139, plaza=dict(x=80, y=76), radius=15.5, entry=dict(x=80, y=130))
PLAZA_R, RING_R = 15.5, 19.5
STREETS_V = [48.0, 112.0]                         # minor north-south streets (4 wide)
STREETS_H = [44.0, 108.0]                         # minor east-west streets
AVENUE_W, TRADE_W, MINOR_W = 7.0, 7.0, 4.0
HOUSE_COLORS = ['#b8744e', '#667c91', '#4f7a6a', '#7a5a8c', '#c4a060', '#a8606a', '#4a8c8c', '#8a6a4a']
HOUSE_SIZES = [(3.4, 3.2), (3.4, 3.2), (3.0, 2.9), (3.8, 3.4)]
HOUSE_TARGET = 100
STREET_NAMES = {'V0': 'Lark Lane', 'V1': 'Raven Row', 'H0': 'Cooper Walk', 'H1': 'Tanner Way', 'T': 'Trade Rd', 'A': 'Grand Ave'}
GLACIER_GATE_CANDIDATES = [(gx / 2, gy / 2) for gx in range(104, 150) for gy in range(80, 126)]


class Builder:
    """Collects objects and keeps footprints from overlapping."""

    def __init__(self, rng):
        self.rng = rng
        self.objects = []
        self.shapes = []

    @staticmethod
    def shape(o):
        if o.get('width'):
            return ('r', o['x'], o['y'], o['width'] / 2, o['depth'] / 2)
        return ('c', o['x'], o['y'], o['r'])

    @staticmethod
    def hit(a, b, margin):
        if a[0] == 'c' and b[0] == 'c':
            return math.hypot(a[1] - b[1], a[2] - b[2]) < a[3] + b[3] + margin
        if a[0] == 'r' and b[0] == 'r':
            return abs(a[1] - b[1]) < a[3] + b[3] + margin and abs(a[2] - b[2]) < a[4] + b[4] + margin
        c, r = (a, b) if a[0] == 'c' else (b, a)
        dx = max(abs(c[1] - r[1]) - r[3], 0)
        dy = max(abs(c[2] - r[2]) - r[4], 0)
        return math.hypot(dx, dy) < c[3] + margin

    def free(self, o, margin=0.0):
        s = self.shape(o)
        return all(not self.hit(s, t, margin) for t in self.shapes)

    def add(self, o, margin=0.0, force=False):
        if not force and not self.free(o, margin):
            return False
        self.objects.append(o)
        self.shapes.append(self.shape(o))
        return True


def obj(kind, x, y, r=0.0, v=0, **extra):
    o = {'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': r, 'v': v}
    o.update(extra)
    return o


def building(kind, x, y, w, d, color, label, **extra):
    return obj(kind, x, y, 0, 0, width=w, depth=d, color=color, label=label, **extra)


def door(o, gap=1.5):
    """Where someone stands to greet visitors: in front of the door (the +y side)."""
    return (o['x'], o['y'] + o['depth'] / 2 + gap)


# ---- roads ---------------------------------------------------------------------------------------------------------------
def build_roads():
    r = []
    rect = lambda t, x0, y0, x1, y1: r.append(dict(t=t, x0=x0, y0=y0, x1=x1, y1=y1))
    rect(1, 80 - AVENUE_W / 2, 13, 80 + AVENUE_W / 2, 157)                      # the Grand Avenue and the approach to the gate
    rect(1, 17, 76 - TRADE_W / 2, 143, 76 + TRADE_W / 2)                         # the Trade Road
    for x in STREETS_V:
        rect(1, x - MINOR_W / 2, 13, x + MINOR_W / 2, 139)
    for y in STREETS_H:
        rect(1, 17, y - MINOR_W / 2, 143, y + MINOR_W / 2)
    r.append(dict(t=1, x=FOUNTAIN[0], y=FOUNTAIN[1], r0=PLAZA_R, r1=RING_R))      # the ring road
    r.append(dict(t=2, x=FOUNTAIN[0], y=FOUNTAIN[1], r=PLAZA_R))                  # the plaza
    r.append(dict(t=3, x=100, y=118, r=7.6))                                      # Meeting Stone court
    rect(2, 54, 21, 70, 36)                                                        # Cathedral forecourt
    rect(2, 71, 22, 89, 28)                                                        # Steward's court
    rect(2, 90, 22, 106, 35)                                                       # Archive court
    rect(2, 93, 54, 107, 68)                                                       # Guild court
    rect(3, 98, 88, 112, 102)                                                      # Gilded Lute yard
    rect(3, 24, 95, 42, 106)                                                       # smithy yard
    rect(3, 118, 116, 138, 130)                                                    # stable yard
    for (x0, y0, x1, y1) in [(22, 62, 44, 72), (52, 56, 66, 72)]:
        rect(2, x0, y0, x1, y1)
    rect(1, 26.4, 16, 28.4, 40)                                                    # garden path (N-S)
    rect(1, 18, 27, 46, 29)                                                        # garden path (E-W)
    rect(1, 120.4, 16, 122.4, 42)                                                  # orchard lane
    return r


def road_mask(roads):
    """Cells (1..3) the ground draws as street; used by the reachability check only to place scenery."""
    n = SIZE
    grid = np.zeros((n, n), dtype=np.uint8)
    xs = np.arange(n) + .5
    X, Y = np.meshgrid(xs, xs)
    for rd in roads:
        if 'x0' in rd:
            m = (X >= rd['x0']) & (X <= rd['x1']) & (Y >= rd['y0']) & (Y <= rd['y1'])
        elif 'r0' in rd:
            d = np.hypot(X - rd['x'], Y - rd['y'])
            m = (d >= rd['r0']) & (d <= rd['r1'])
        else:
            m = np.hypot(X - rd['x'], Y - rd['y']) <= rd['r']
        grid[m] = rd['t']
    return grid


# ---- walls and the gate -------------------------------------------------------------------------------------------------
def build_walls(b):
    towers = [(WALL['x0'], WALL['y0']), (WALL['x1'], WALL['y0']), (WALL['x0'], WALL['y1']), (WALL['x1'], WALL['y1']),
              (80, WALL['y0']), (WALL['x0'], 76), (WALL['x1'], 76), (80 - GATE_HALF - TOWER / 2, WALL['y1']), (80 + GATE_HALF + TOWER / 2, WALL['y1'])]
    for x, y in towers:
        b.add(building('tower', x, y, TOWER, TOWER, '#4a7a9a', ''), force=True)

    def run(x0, y0, x1, y1):
        horizontal = abs(y1 - y0) < 1e-6
        length = (x1 - x0) if horizontal else (y1 - y0)
        n = max(1, math.ceil((length - TOWER) / 6.0))
        piece = (length - TOWER) / n
        for i in range(n):
            c = (-length / 2 + TOWER / 2 + piece * (i + .5))
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            if horizontal:
                b.add(building('rampart', mx + c, my, piece + .15, 1.8, '#d7d3bc', ''), force=True)
            else:
                b.add(building('rampart', mx, my + c, 1.8, piece + .15, '#d7d3bc', ''), force=True)

    W = WALL
    gl, gr = 80 - GATE_HALF - TOWER / 2, 80 + GATE_HALF + TOWER / 2
    run(W['x0'], W['y0'], 80, W['y0'])
    run(80, W['y0'], W['x1'], W['y0'])
    run(W['x0'], W['y1'], gl, W['y1'])
    run(gr, W['y1'], W['x1'], W['y1'])
    run(W['x0'], W['y0'], W['x0'], 76)
    run(W['x0'], 76, W['x0'], W['y1'])
    run(W['x1'], W['y0'], W['x1'], 76)
    run(W['x1'], 76, W['x1'], W['y1'])
    # banners on the gate towers
    for sx in (-1, 1):
        b.add(obj('banner', 80 + sx * (GATE_HALF + 0.2), W['y1'] - 3.0, .3, 0, color='#9a2f3a' if sx < 0 else '#2f5a9a'), force=True)


# ---- the civic buildings and their furniture --------------------------------------------------------------------------------
def build_landmarks(b, places):
    cx, cy = FOUNTAIN
    b.add(obj('grandfountain', cx, cy, 6.3), force=True)
    # plaza furniture: eight lamps on the ring road, four benches and four flower beds around the basin
    for i in range(8):
        a = (i + .5) * math.pi / 4
        b.add(obj('lamp', cx + 19.0 * math.cos(a), cy + 19.0 * math.sin(a), .18))
    for i in range(4):
        a = (i + .5) * math.pi / 2 + math.pi / 4
        b.add(obj('flowers', cx + 11.2 * math.cos(a), cy + 11.2 * math.sin(a), .55, i % 3))
        for sgn in (-1, 1):
            a2 = a + sgn * .35
            b.add(building('bench', cx + 9.6 * math.cos(a2), cy + 9.6 * math.sin(a2), 1.5, .45, '', ''))
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        b.add(obj('statue', cx + 14.2 * math.cos(a), cy + 14.2 * math.sin(a), .45, i))

    # Steward's Hall at the north end of the avenue, between two towers
    hall = building('house', 80, 19, 9.0, 5.4, '#7a5a8c', "Steward's Hall", big=True)
    b.add(hall, force=True)
    places['steward'] = door(hall, 1.6)
    for sx in (-1, 1):
        b.add(building('tower', 80 + sx * 8.4, 19, TOWER, TOWER, '#7a5a8c', ''), force=True)
    # Cathedral and its court
    cath = building('chapel', 62, 27, 5.4, 4.6, '#5f7f78', 'Cathedral of the Hearth')
    b.add(cath, force=True)
    places['healer'] = door(cath, 1.5)
    places['acolyte'] = (cath['x'] + 5.2, cath['y'] + 4.4)
    # Archive
    arch = building('house', 98, 27, 6.0, 4.6, '#6a7ab0', 'Archive of Skaldholm')
    b.add(arch, force=True)
    places['librarian'] = door(arch, 1.5)
    places['scribe'] = (arch['x'] - 5.2, arch['y'] + 4.6)
    # Guildhall
    guild = building('house', 100, 58, 7.0, 5.0, '#a08040', "Merchants' Guildhall")
    b.add(guild, force=True)
    places['guildmaster'] = door(guild, 1.5)
    # The Gilded Lute and its stage
    inn = building('house', 106, 96, 6.4, 4.6, '#b8744e', 'The Gilded Lute')
    b.add(inn, force=True)
    places['innkeeper'] = door(inn, 1.5)
    places['drunk'] = (inn['x'] + 5.2, inn['y'] + 3.6)
    stage = [(98.5, 90.5), (101.5, 90.5)]
    for sx, sy in stage:
        b.add(building('bench', sx, sy, 1.5, .45, '', ''), force=True)
    places['bard'] = (100.0, 93.0)
    b.add(obj('flowers', 96.4, 93, .55, 1))
    b.add(obj('flowers', 103.6, 93, .55, 2))
    # Quill & Cauldron (alchemist) with the west market
    alch = building('house', 58, 60, 4.6, 3.8, '#4f8a7a', 'Quill & Cauldron')
    b.add(alch, force=True)
    places['alchemist'] = door(alch, 1.4)
    # Smithy
    forge = building('house', 33, 101, 4.8, 3.8, '#8a6a52', 'Emberforge')
    b.add(forge, force=True)
    places['smith'] = door(forge, 1.4)
    places['apprentice'] = (forge['x'] + 4.4, forge['y'] + 3.6)
    b.add(obj('campfire', 26.5, 100.5, .8), force=True)
    b.add(building('stall', 41.5, 98.6, 1.8, 1.2, '#8a6a52', 'Tools'), force=True)
    # Gate Watch barracks and the captain
    barr = building('house', 67.8, 128.5, 4.8, 3.8, '#58708f', 'Gate Watch')
    b.add(barr, force=True)
    places['captain'] = door(barr, 1.5)
    places['gate_guard_w'] = (75.6, 135.2)
    places['gate_guard_e'] = (84.4, 135.2)
    # Stables
    stable = building('house', 126, 121, 6.4, 4.4, '#6a8a5a', 'Stables')
    b.add(stable, force=True)
    places['stable'] = door(stable, 1.5)
    for i in range(6):
        b.add(building('wall', 118.5 + i * 2.2, 133.8, 2.2, .5, '#8a6a4a', ''), force=True)
    for i in range(4):
        b.add(building('barrels', 135 + (i % 2) * 1.2, 125 + (i // 2) * 1.2, .5, .5, '', ''), force=True)
    # The Meeting Stone court
    mx, my = 100.0, 118.0
    b.add(obj('meetingstone', mx, my, 1.7), force=True)
    for i in range(4):
        if i == 0:
            continue                                     # the south-east bench makes way for the stairs down to the Undervault
        a = i * math.pi / 2 + math.pi / 4
        b.add(building('bench', mx + 5.4 * math.cos(a), my + 5.4 * math.sin(a), 1.5, .45, '', ''), force=True)
    sx, sy = uv.STAIRS_DOWN
    for px, py in [(sx - 2.1, sy - .4), (sx + 2.1, sy - .4), (sx, sy - 2.3), (sx - 1.9, sy + 1.6), (sx + 1.9, sy + 1.6)]:   # the stairwell: posts round three sides and the two lantern pillars of the way in (the art is drawn with the portal; you step on from the south)
        b.add(obj('post', px, py, .45), force=True)
    for i in range(4):
        a = i * math.pi / 2
        b.add(obj('lamp', mx + 6.9 * math.cos(a), my + 6.9 * math.sin(a), .18), force=True)
    places['stonewarden'] = (mx - 3.0, my + 5.4)
    places['meetingstone'] = (mx + 1.7, my + 1.7)              # the Stone itself speaks (it hires fighters): straight below it on screen, so a click on the monolith reaches it
    # Markets: stalls on the north edge of the Trade Road, fronts toward the road
    stalls_w = [('Spices', '#c46760', 24), ('Cloth', '#678c9b', 30), ('Pottery', '#c4a060', 36), ('Fruit', '#7aa060', 42),
                ('Boots', '#8a6a4a', 49), ('Cheese', '#e0c060', 55)]
    stalls_e = [('Honey', '#d0a040', 105), ('Hats', '#9a6a9a', 111), ('Toys', '#c46760', 117), ('Bread', '#c4a060', 123),
                ('Lamps', '#678c9b', 129), ('Herbs', '#7aa060', 135)]
    for label, col, x in stalls_w + stalls_e:
        b.add(building('stall', x, 71.6, 1.8, 1.2, col, label), force=True)
        b.add(building('barrels', x + 1.5, 71.4, .5, .5, '', ''), force=True)
    places['cobbler'] = (49.0, 73.4)
    places['weaver'] = (30.0, 73.4)
    # plaza stalls with the people who run them
    b.add(building('stall', 71.2, 67.4, 1.8, 1.2, '#e3c18a', 'Sunrise Bakery'), force=True)
    places['baker'] = (71.2, 69.4)
    b.add(building('stall', 91.4, 79.0, 1.8, 1.2, '#6a8fa8', 'Fishmonger'), force=True)
    places['fishmonger'] = (91.4, 81.0)
    b.add(building('stall', 80.0, 95.0, 1.8, 1.2, '#e6a0b4', 'Flowers'), force=True)
    places['flowers'] = (80.0, 97.0)
    places['herald'] = (73.6, 88.4)
    b.add(building('noticeboard', 71.6, 85.8, 1.3, .4, '', 'Skaldholm'), force=True)
    places['grandfather'] = (109.4, 84.6)
    b.add(building('bench', 109.4, 82.8, 1.5, .45, '', ''), force=True)
    places['lamp_boy'] = (74.4, 100.6)
    places['washer'] = (38.5, 54.6)
    places['painter'] = (31.5, 24.8)
    b.add(obj('well', 38.5, 52.4, .7), force=True)
    return places


# ---- houses ---------------------------------------------------------------------------------------------------------------
def house_candidates(b):
    """Lots along the streets, both sides: (x, y, street key, along-street coordinate, row). Row 0 fronts the street."""
    out = []
    pitch = 5.0
    gap = 0.8

    def along(key, axis, pos, hw, lo, hi):
        t = lo
        while t <= hi:
            for side in (-1, 1):
                for row in (0, 1):
                    off = hw + gap + 1.8 + row * 5.0
                    if axis == 'v':
                        out.append((pos + side * off, t, key, t, row))
                    else:
                        out.append((t, pos + side * off, key, t, row))
            t += pitch

    for i, x in enumerate(STREETS_V):
        along('V%d' % i, 'v', x, MINOR_W / 2, 18, 136)
    for i, y in enumerate(STREETS_H):
        along('H%d' % i, 'h', y, MINOR_W / 2, 21, 140)
    along('T', 'h', 76, TRADE_W / 2, 21, 140)
    along('A', 'v', 80, AVENUE_W / 2, 20, 136)
    return out


def place_houses(b, roads_grid):
    cands = house_candidates(b)
    b.rng.shuffle(cands)
    cands.sort(key=lambda c: c[4] * 0.35 + b.rng.random())      # mostly street frontage, some second-row houses
    fx, fy = FOUNTAIN
    chosen = []
    counters = {}
    for (x, y, key, t, row) in cands:
        if len(chosen) >= HOUSE_TARGET:
            break
        # not on the plaza, the ring road, the marketplaces, courts or the parks
        if math.hypot(x - fx, y - fy) < RING_R + 5.5:
            continue
        if not (20 < x < 140 and 16 < y < 136):
            continue
        # keep the park blocks and the market strips open
        if (x < 47 and y < 43) or (x > 113 and y < 43):
            continue
        if key == 'T' and ((y < 76) or (y > 76 and 44 < x < 116)):
            continue                                       # the north edge of the Trade Road is the market
        w, d = b.rng.choice(HOUSE_SIZES)
        o = building('house', x, y, w, d, b.rng.choice(HOUSE_COLORS), '')
        if b.free(o, 0.95) and road_overlap(roads_grid, o) < 0.05:
            chosen.append((o, key, t))
            b.add(o)
    # numbers along each street, ascending
    by_street = {}
    for o, key, t in chosen:
        by_street.setdefault(key, []).append((t, o))
    for key, items in by_street.items():
        for n, (t, o) in enumerate(sorted(items, key=lambda it: (it[0], it[1]['x'], it[1]['y'])), 1):
            o['label'] = '%s %d' % (STREET_NAMES[key], n)
            o['sign'] = 'live'
    return [o for o, _, _ in chosen], cands


def road_overlap(grid, o):
    """Fraction of a footprint's cells that lie on a road (houses must stand beside streets, not on them)."""
    x0, x1 = int(o['x'] - o['width'] / 2), int(o['x'] + o['width'] / 2) + 1
    y0, y1 = int(o['y'] - o['depth'] / 2), int(o['y'] + o['depth'] / 2) + 1
    cells = grid[y0:y1, x0:x1]
    return (cells > 0).mean() if cells.size else 1.0


# ---- scenery ---------------------------------------------------------------------------------------------------------------
def scatter(b, rng, kind, count, size, region, clear, grid, v_choices=(0, 1, 2, 3), margin=0.8, road_ok=False, tries=40000):
    placed = 0
    for _ in range(tries):
        if placed == count:
            break
        x, y = rng.uniform(*region[0]), rng.uniform(*region[1])
        if not road_ok and grid[int(y), int(x)] > 0:
            continue
        o = obj(kind, x, y, size, rng.choice(v_choices))
        if clear(x, y) and b.add(o, margin):
            placed += 1
    return placed


def build_scenery(b, rng, grid, places):
    inside = lambda x, y: WALL['x0'] + 2 < x < WALL['x1'] - 2 and WALL['y0'] + 2 < y < WALL['y1'] - 2
    # lamps along the avenue and the minor streets
    for y in range(24, 138, 10):
        for sx in (-1, 1):
            if not (60 < y < 92):
                b.add(obj('lamp', 80 + sx * 4.1, y, .18), 0.4)
    for x in STREETS_V:
        for y in range(26, 138, 12):
            if all(abs(y - c) > 6 for c in [44, 76, 108]):
                b.add(obj('lamp', x + 2.5, y, .18), 0.8)
    for y in STREETS_H:
        for x in range(24, 140, 12):
            if all(abs(x - c) > 6 for c in [48, 80, 112]):
                b.add(obj('lamp', x, y - 2.5, .18), 0.8)
    for x in range(26, 140, 12):
        if all(abs(x - c) > 6 for c in [48, 80, 112]) and abs(x - 80) > 22:
            b.add(obj('lamp', x, 72.2, .18), 0.8)
    # trees lining the avenue's south half and the approach
    for y in range(96, 150, 6):
        for sx in (-1, 1):
            b.add(obj('tree', 80 + sx * 4.6, y + 2, .42, (y // 6) % 4), 0.6)
    # NW garden (Idun's Garden): lawn, hedges, flower beds, a pond-less fountain, lots of trees
    gx = ((24.0, 45.5), (14.5, 41.5))
    keep = [(31.5, 24.8), (25.2, 33), (31.0, 33), (25.2, 23), (31.0, 23), (38.5, 22), (36.5, 22)]
    clear_garden = lambda x, y: not (25.2 < x < 29.6 and y < 41) and not (26 < y < 30.4) and all(math.hypot(x - a, y - c) > 3.0 for a, c in keep)
    scatter(b, rng, 'tree', 34, .42, gx, clear_garden, grid, margin=1.0)
    scatter(b, rng, 'bush', 30, .3, gx, clear_garden, grid, margin=0.8)
    scatter(b, rng, 'flowers', 16, .55, gx, clear_garden, grid, v_choices=(0, 1, 2), margin=0.8)
    b.add(obj('fountain', 37.0, 22, 1.1), force=True)
    for (x, y) in [(25.2, 33), (31.0, 33), (25.2, 23), (31.0, 23)]:
        b.add(building('bench', x, y, 1.5, .45, '', ''), 0.2)
    # NE orchard: rows of fruit trees either side of the lane
    for iy in range(15, 41, 4):
        for ix in list(range(116, 120, 4)) + list(range(125, 141, 4)):
            b.add(obj('tree', ix + (iy % 8) * .15, iy + .5, .42, 2 + (ix // 4 + iy // 4) % 2), 0.8)
    for (x, y) in [(120.2, 19), (122.8, 27), (120.2, 35), (122.8, 40)]:
        b.add(building('bench', x, y, 1.5, .45, '', ''), 0.2)
    # courts: a few trees and flower beds
    for (x, y) in [(55, 24), (71, 24), (55, 38), (71, 38)]:
        b.add(obj('tree', x, y, .42, 3), 0.5)
    for (x, y) in [(75, 26), (85, 26), (75, 29), (85, 29)]:
        b.add(obj('flowers', x, y, .55, 1), 0.3)
    for (x, y) in [(90, 24), (106, 24), (90, 39), (106, 39)]:
        b.add(obj('tree', x, y, .42, 1), 0.5)
    for (x, y) in [(96.5, 56), (103.5, 56)]:
        b.add(obj('flowers', x, y, .55, 2), 0.3)
    # barrels and crates around the smithy and tavern
    for (x, y) in [(29.5, 103.8), (36.5, 98.5), (112.4, 98.8), (112.4, 100.2), (101.5, 98.9)]:
        b.add(building('barrels', x, y, .5, .5, '', ''), 0.3)
    # lawns between houses: the empty lots get a tree, a flower bed or a bush so no hole shows bare
    # ground outside the wall: a ring of trees and bushes, clear of the road and the portal
    outside = lambda x, y: not inside(x, y) and abs(x - 80) > 6.5
    tr = scatter(b, rng, 'tree', 170, .42, ((2, 158), (2, 158)), lambda x, y: outside(x, y) and (x < WALL['x0'] - 2.5 or x > WALL['x1'] + 2.5 or y < WALL['y0'] - 2.5 or y > WALL['y1'] + 2.5), grid, margin=1.2)
    scatter(b, rng, 'bush', 80, .3, ((2, 158), (2, 158)), lambda x, y: outside(x, y) and (x < WALL['x0'] - 2 or x > WALL['x1'] + 2 or y < WALL['y0'] - 2 or y > WALL['y1'] + 2), grid, margin=0.9)
    scatter(b, rng, 'rock', 14, .4, ((2, 158), (2, 158)), lambda x, y: outside(x, y) and (x < WALL['x0'] - 3 or x > WALL['x1'] + 3 or y < WALL['y0'] - 3 or y > WALL['y1'] + 3), grid, margin=1.0)
    return tr


def fill_empty_lots(b, cands, rng, grid):
    """Lots not taken by a house: a tree, flower bed or bush if they are free, in the blocks that are not parks."""
    n = 0
    fx, fy = FOUNTAIN
    for (x, y, key, t, row) in cands:
        if row or not (20 < x < 140 and 16 < y < 136) or math.hypot(x - fx, y - fy) < RING_R + 5.5:
            continue
        if (x < 47 and y < 43) or (x > 113 and y < 43):
            continue
        if key == 'T' and (y < 76 or 44 < x < 116):
            continue
        if grid[int(y), int(x)] > 0:
            continue
        kind = rng.choice(['tree', 'flowers', 'bush', 'tree'])
        size = {'tree': .42, 'flowers': .55, 'bush': .3}[kind]
        if b.add(obj(kind, x, y, size, rng.randrange(4)), 1.0):
            n += 1
    return n


# ---- walker routes ---------------------------------------------------------------------------------------------------------
def circle(cx, cy, r, k, a0=0.0):
    return [(cx + r * math.cos(a0 + i * 2 * math.pi / k), cy + r * math.sin(a0 + i * 2 * math.pi / k)) for i in range(k)]


def route_book():
    fx, fy = FOUNTAIN
    return dict(
        fountain=FOUNTAIN, kids_radius=7.8,
        watch_avenue=[(78.4, 131), (78.4, 98), (81.6, 98), (81.6, 131)],
        watch_trade=[(22, 74.2), (66, 74.2), (66, 77.8), (22, 77.8)],
        watch_wall=[(20.8, 24), (20.8, 66), (23.4, 66), (23.4, 24)],
        ring=circle(fx, fy, 16.9, 28),
        courier=[(92.4, 62), (92.4, 38.5), (95.4, 38.5), (95.4, 62)],
        trade_long=[(106, 74.2), (138, 74.2), (138, 77.8), (106, 77.8)],
        pilgrim=[(76.8, 44), (58, 44), (58, 38), (68, 38), (76.8, 44)],
        minstrel=[(94, 100), (94, 112), (100.5, 112), (100.5, 100)],
        garden=[(27.4, 17.5), (27.4, 38.5)],
    )


def route_clear(grid_blocked, route, step=.25):
    pts = []
    for a, b in zip(route, route[1:] + route[:1]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        pts += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n)]
    bad = [p for p in pts if grid_blocked[int(p[1] / .5), int(p[0] / .5)]]
    return bad


# ---- the glacier gate -------------------------------------------------------------------------------------------------------
def add_city_gate(meadow, rng):
    """Remove an earlier city gate, find a spot in the summit bowl, then add posts and portal and move wyrms clear."""
    glacier = next(z for z in meadow['zones'] if z['name'] == GLACIER)
    glacier['portals'] = [p for p in glacier['portals'] if p['id'] != 'city_gate']
    glacier['objects'] = [o for o in glacier['objects'] if not (o['kind'] == 'post' and o.get('city'))]
    centre = (64.0, 52.0)
    fen_gate, fen_arrival = fen.GLACIER_GATE, fen.GLACIER_ARRIVAL
    gap4 = (64.0, 37.0)
    scenery = [o for o in glacier['objects'] if o['kind'] != 'post']
    base = [(x / 2, y / 2) for x in range(90, 170) for y in range(70, 135)
            if math.hypot(x / 2 - centre[0], y / 2 - centre[1]) < 12.8
            and math.hypot(x / 2 - gap4[0], y / 2 - gap4[1]) > 8.5
            and math.hypot(x / 2 - fen_arrival[0], y / 2 - fen_arrival[1]) > 9.0
            and math.hypot(x / 2 - fen_gate[0], y / 2 - fen_gate[1]) > 5.5
            and all(math.hypot(x / 2 - o['x'], y / 2 - o['y']) > o['r'] + 2.3 for o in scenery)]
    options = []
    for gx, gy in [(x / 2, y / 2) for x in range(100, 156) for y in range(76, 126)]:
        ax, ay = gx, gy + 4.5
        if math.hypot(gx - centre[0], gy - centre[1]) > 12 or math.hypot(ax - centre[0], ay - centre[1]) > 13:
            continue
        if math.hypot(gx - fen_gate[0], gy - fen_gate[1]) < 8 or math.hypot(ax - fen_arrival[0], ay - fen_arrival[1]) < 8:
            continue
        if any(math.hypot(gx - o['x'], gy - o['y']) < o['r'] + 2.6 or math.hypot(ax - o['x'], ay - o['y']) < o['r'] + 2.0 for o in scenery):
            continue
        displaced = [s for s in glacier['slimes'] if math.hypot(s['x'] - ax, s['y'] - ay) < 10 or math.hypot(s['x'] - gx, s['y'] - gy) < 6]
        # fewest moves first; among those, the gate farthest from the walk between the last gap and the fen gate
        options.append((len(displaced), -abs(gx - 64), gx, gy, displaced))
    options.sort(key=lambda t: t[:4])
    for _, _, gx, gy, displaced in options:
        ax, ay = gx, gy + 4.5
        valid = [p for p in base if math.hypot(p[0] - ax, p[1] - ay) > 9.0 and math.hypot(p[0] - gx, p[1] - gy) > 5.5]
        others = [s for s in glacier['slimes'] if s not in displaced]
        placed = None
        for attempt in range(60):                   # nearest-first can paint itself into a corner: shuffle the order
            order = displaced[:]
            rng.shuffle(order)
            taken = [(t['x'], t['y']) for t in others]
            trial = {}
            for s in order:
                free = [p for p in valid if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 7.2 for q in taken)]
                if not free:
                    break
                p = min(free, key=lambda p: math.hypot(p[0] - s['x'], p[1] - s['y']) + rng.uniform(0, 4))
                trial[id(s)] = p
                taken.append(p)
            else:
                placed = trial
                break
        if placed is not None:
            break
    else:
        raise SystemExit('no gate position in the summit bowl lets the wyrms be re-spaced')
    for dx in (-1.5, 1.5):
        glacier['objects'].append({'kind': 'post', 'x': gx + dx, 'y': gy, 'r': 0.45, 'v': 0, 'city': True})
    glacier['portals'].append({'id': 'city_gate', 'name': 'the Skaldholm Gate', 'x': gx, 'y': gy, 'r': 1.1,
                               'to': 4, 'tx': ARRIVAL[0], 'ty': ARRIVAL[1]})
    for s in displaced:
        s['x'], s['y'] = round(placed[id(s)][0], 2), round(placed[id(s)][1], 2)
    moved = len(displaced)
    seen, _ = fen.flood(glacier, fen.GLACIER_START)
    for name, (x, y) in [('city arrival', (ax, ay)), ('city gate', (gx, gy + 2))] + [(s['kind'], (s['x'], s['y'])) for s in glacier['slimes']]:
        if not seen[int(y / .5), int(x / .5)]:
            raise SystemExit(f'Rimeveil: {name} at {x},{y} is unreachable from the camp')
    return (gx, gy), moved


# ---- assembly --------------------------------------------------------------------------------------------------------------
def build(rng):
    roads = build_roads()
    grid = road_mask(roads)
    b = Builder(rng)
    places = {}
    build_walls(b)
    build_landmarks(b, places)
    # the way out: two posts for the return gate
    for dx in (-1.5, 1.5):
        b.add(obj('post', RETURN_GATE[0] + dx, RETURN_GATE[1], 0.45), force=True)
    book = route_book()
    for key, route in book.items():                    # walkers' corridors are kept free of houses and scenery
        if isinstance(route, list):
            for a, c in zip(route, route[1:] + route[:1]):
                n = max(1, int(math.hypot(c[0] - a[0], c[1] - a[1]) / .7))
                for i in range(n):
                    b.shapes.append(('c', a[0] + (c[0] - a[0]) * i / n, a[1] + (c[1] - a[1]) * i / n, .55))
    houses, cands = place_houses(b, grid)
    assert len(houses) >= HOUSE_TARGET - 2, f'only {len(houses)} houses fit'
    trees = build_scenery(b, rng, grid, places)
    filled = fill_empty_lots(b, cands, rng, grid)

    people = content.key_people() + content.talkers() + content.walkers(book)
    for p in people:
        short = p['id'][len(content.P):]
        if short in places:
            p['x'], p['y'] = round(places[short][0], 2), round(places[short][1], 2)
    zone = {'name': NAME, 'theme': 'city', 'tagline': 'A walled city of a hundred hearths beyond the glacier', 'size': SIZE, 'spawn': {'x': ARRIVAL[0], 'y': ARRIVAL[1]}, 'paths': [],
            'roads': roads, 'objects': b.objects, 'slimes': [], 'npcs': people, 'quests': content.quests(), 'city': dict(CITY),
            'portals': [{'id': 'glacier_gate', 'name': 'the Glacier Gate', 'x': RETURN_GATE[0], 'y': RETURN_GATE[1], 'r': 1.1,
                         'to': 2, 'tx': 0.0, 'ty': 0.0},
                        {'id': 'undervault_stairs', 'name': 'the Stairs to the Undervault', 'x': uv.STAIRS_DOWN[0], 'y': uv.STAIRS_DOWN[1], 'r': 1.1,
                         'to': 5, 'tx': uv.ARRIVAL[0], 'ty': uv.ARRIVAL[1], 'look': 'stairs_down'}]}
    return zone, dict(houses=len(houses), trees=trees, filled=filled)


def check_zone(zone):
    """Every person, the arrival and the return gate must be reachable on foot from the arrival; walker routes must be clear."""
    seen, blocked = fen.flood(zone, ARRIVAL)
    missing = []
    for n in zone['npcs']:
        if n.get('route'):
            continue
        if not seen[int(n['y'] / .5), int(n['x'] / .5)]:
            missing.append(n['id'])
    for name, (x, y) in [('return gate', (RETURN_GATE[0], RETURN_GATE[1] - 2)), ('plaza', (FOUNTAIN[0] + 9.7, FOUNTAIN[1])),
                         ('stone court', (100, 123)), ('stairs', (uv.STAIRS_DOWN[0], uv.STAIRS_DOWN[1] + 1.6)), ('stairs return', uv.STAIRS_RETURN), ('orchard', (123, 28)), ('garden', (27.4, 34))]:
        if not seen[int(y / .5), int(x / .5)]:
            missing.append(name)
    soft = fen.obstacle_grid(zone, .5, margin=.35)
    bad_routes = []
    for n in zone['npcs']:
        if n.get('route'):
            route = [tuple(p) for p in n['route']]
            bad = route_clear(soft, route)
            if bad:
                bad_routes.append((n['id'], len(bad), bad[0]))
    return missing, bad_routes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    raw = PATH.read_text()
    meadow = json.loads(raw)
    assert json.dumps(meadow, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    assert len(meadow['zones']) >= 3 and meadow['zones'][2]['name'] == 'Gloamfen', 'Gloamfen must be zone 3: run generate_gloamfen.py first'
    later = meadow['zones'][4:]                       # zone 5+ (the Undervault) belongs to its own generator
    meadow['zones'] = [z for z in meadow['zones'][:3] if z['name'] != NAME]
    (gx, gy), moved = add_city_gate(meadow, random.Random(20261007))     # its own stream: it only draws numbers on the first run
    zone, stats = build(random.Random(20261008))
    zone['portals'][0].update(tx=round(gx, 2), ty=round(gy + 4.5, 2))
    missing, bad_routes = check_zone(zone)
    if missing or bad_routes:
        raise SystemExit(f'unreachable: {missing}; blocked walker routes: {bad_routes}')
    meadow['zones'].append(zone)
    assert len(meadow['zones']) == 4, 'Skaldholm must be zone 4'
    meadow['zones'] += later
    spark_travel.ensure(meadow)
    PATH.write_text(json.dumps(meadow, indent=2) + '\n')
    kinds = {}
    for o in zone['objects']:
        kinds[o['kind']] = kinds.get(o['kind'], 0) + 1
    print(f"Wrote zone 4 {zone['name']}: {len(zone['objects'])} objects {kinds}; {len(zone['npcs'])} people, {len(zone['quests'])} quests; "
          f"glacier gate at ({gx}, {gy}), {moved} wyrm spawn(s) moved. {stats}. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
