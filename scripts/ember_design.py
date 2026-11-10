#!/usr/bin/env python3
"""Emberwake Caldera as an authored map (zone 45 of the shapes pilot): no filler land, the whole outline used.

Owner request 2026-11-08: "for pilot. reshape emberwake caldera. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the
Stormglass Flats (north) and the Moonspore Canopy (west), keep the three elites, three outposts. The Obsidian Orrery (north-west) and the Ribbonwild (east) stay walk-in
rim gates; the Chained Forge door and its camp move whole.

The outline at k = 1.0 is grid 400 with 90,795 land tiles against the old 160 square's 25,600, and it has a south coast. The painting shows a great crater north-west of the
middle, a glowing river across the whole zone from the Canopy border to the Ribbonwild, a cold crater and a hot one in the south, painted chain roads and many peaks.
The zone keeps its own style: basalt, chains, lava, lanterns and the warm stones of the first forge.

Runs in `zone_shapes.py apply` after the Stormglass Flats' design. The zone is `designOnly` (zone-shapes.txt, `seamWith {45: [16, 19]}`): it keeps the outline floor
(`shapeFloor`), takes no filler and places its own gates (`place_portals` skips it). The Flats' approved design ran unchanged with its south gate as a phantom (only the
spawns within 7 tiles of the new seam went); the Canopy is a filler zone (`zone_shapes.trim_late_seam`). The borders to the Flats and the Canopy are reserved from `shape.edges`
runs: no art-less object or person within 20 tiles, no spawn within 22, no loose scenery within 2.5, no lava within 17 (a seam neighbour draws no lava).

Fixed, moved as a rigid block from `world/zone-shapes/preshape-45.txt` (the old layout): the Nine-Chain Door, its tablet, the Voice below and the Meeting Stone with
Orri, the seal and the echo. Every person, place, portal and quest keeps its id.

    python3 scripts/ember_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import copy
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ember_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, drop_near_seam, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-45.txt'

ZONE = 45
D_DOOR = content.D_DOOR
DOOR = (322.0, 76.0)             # the Nine-Chain Door (old 133,20)
DOOR_ARR = (316.0, 81.0)         # where the raid's way out arrives (old 127,25)
SPAWN = (228.0, 91.0)            # Chainrest's own entry
ES25 = (322.0, 126.0)            # The Guest at the Last Door (Empty Seat chapter 25)
CALDERA = (163.0, 100.0)
HOT = (253.0, 266.0)
QUENCH = (140.0, 278.0)
CAUSEWAY = (190.0, 226.5)
RIM = 3

REGIONS = {
    'verge':     dict(name='The Ash Verge', seeds=[(180, 46), (262, 52), (330, 62), (150, 56)]),
    'bellows':   dict(name='The Bellows Crater', seeds=[(163, 100), (140, 100), (186, 100)]),
    'rim':       dict(name='The Caldera Rim', seeds=[(160, 62), (118, 122), (202, 128), (160, 140), (205, 90)]),
    'slopes':    dict(name='The Cinder Slopes', seeds=[(92, 96), (76, 150), (64, 72), (104, 56)]),
    'links':     dict(name='The Broken Links', seeds=[(128, 196), (104, 196), (152, 184)]),
    'reach':     dict(name='The Molten Reach', seeds=[(104, 238), (152, 240), (214, 232), (262, 218), (310, 202), (338, 192)]),
    'steppe':    dict(name='The Glass Steppe', seeds=[(288, 142), (330, 150), (268, 112), (344, 112)]),
    'door':      dict(name='The Door Terraces', seeds=[(316, 90), (340, 70), (298, 92)]),
    'flats':     dict(name='Chainrest Flats', seeds=[(228, 90), (198, 70), (262, 82), (242, 132)]),
    'quench':    dict(name='The Quenched Basin', seeds=[(140, 278), (118, 262), (160, 300)]),
    'ember':     dict(name='The Ember Crater', seeds=[(253, 266), (285, 262), (224, 284)]),
    'shore':     dict(name='The Black Shore', seeds=[(210, 330), (156, 350), (124, 372), (262, 322)]),
    'slagbanks': dict(name='The Slag Banks', seeds=[(104, 300), (112, 332), (186, 300), (214, 296)]),
    'fold':      dict(name='The Slagfold', seeds=[(296, 238), (298, 278), (262, 238)]),
}

# the roads follow the painting (tile coordinates); the gate roads are added by `roads()` from the gate points
R1 = [(120, 30), (120, 66), (112, 71), (100, 77), (98, 100), (98, 160), (98, 182), (84, 184)]
R2 = [(230, 38), (227, 52), (226, 80), (226, 207)]
R3 = [(316, 84), (316, 96), (310, 104), (300, 117), (283, 140), (267, 157), (250, 167), (233, 177), (223, 183), (207, 193), (200, 203), (193, 214), (190, 226),
      (190, 237), (182, 239), (167, 242), (147, 245), (130, 248), (113, 258), (103, 272), (93, 288), (90, 296)]
R4 = [(190, 237), (190, 302), (185, 312), (182, 322), (182, 331)]
R5 = [(100, 332), (210, 332)]
R6 = [(190, 243), (240, 240), (292, 226)]
RIVER = [(93, 218), (105, 225), (127, 230), (153, 231), (180, 229), (200, 224), (227, 218), (253, 209), (283, 198), (310, 189), (337, 181), (366, 176)]

R = {'ew_basalt': .85, 'ew_obsidian': .8, 'ew_slag': .9, 'ew_ashtree': .5, 'ew_cone': 5.2, 'ew_link': 1.4, 'ew_vent': .8, 'ew_lantern': .3, 'ew_shackle': 2.2, 'ew_lava': 0,
     'ew_hut': 0, 'tent': 1.5}
CONE_R = [4.6, 5.2, 6.1]
GROUND = {'ash': 1, 'cinder': 2, 'glass': 3, 'basalt': 4, 'scorch': 5, 'crater': 6, 'quench': 7, 'pale': 8, 'sand': 9, 'slag': 10}
REGION_GROUND = {'verge': 'pale', 'bellows': 'crater', 'rim': 'basalt', 'slopes': 'ash', 'links': 'basalt', 'reach': 'slag', 'steppe': 'glass', 'door': 'scorch', 'flats': 'ash',
                 'quench': 'quench', 'ember': 'crater', 'shore': 'sand', 'slagbanks': 'cinder', 'fold': 'glass'}

# scenery per 1000 land tiles of the region
DENSITY = {
    'verge':     [('ew_slag', 5), ('ew_obsidian', 2), ('ew_ashtree', 3)],
    'bellows':   [('ew_obsidian', 5), ('ew_vent', 2), ('ew_basalt', 2)],
    'rim':       [('ew_basalt', 6), ('ew_obsidian', 3), ('ew_slag', 3)],
    'slopes':    [('ew_ashtree', 5), ('ew_slag', 5), ('ew_basalt', 3)],
    'links':     [('ew_slag', 6), ('ew_basalt', 4), ('ew_link', 1.2)],
    'reach':     [('ew_slag', 8), ('ew_vent', 1.5), ('ew_obsidian', 2)],
    'steppe':    [('ew_obsidian', 7), ('ew_basalt', 3), ('ew_ashtree', 2)],
    'door':      [('ew_basalt', 5), ('ew_slag', 3)],
    'flats':     [('ew_slag', 3), ('ew_ashtree', 3), ('ew_obsidian', 2)],
    'quench':    [('ew_vent', 3), ('ew_obsidian', 6), ('ew_slag', 2)],
    'ember':     [('ew_slag', 6), ('ew_vent', 2), ('ew_basalt', 3)],
    'shore':     [('ew_slag', 4), ('ew_obsidian', 2), ('ew_ashtree', 1.5)],
    'slagbanks': [('ew_slag', 7), ('ew_basalt', 4), ('ew_ashtree', 2)],
    'fold':      [('ew_slag', 6), ('ew_obsidian', 4), ('ew_basalt', 2)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): ashbacks by the north gate, then glasswings, slagjaws and rams
SPAWN_DENSITY = {
    'verge':     {'ew_ashback': 1.8},
    'flats':     {'ew_ashback': 2.0, 'ew_glasswing': .6},
    'slopes':    {'ew_ashback': 1.6, 'ew_glasswing': 1.3},
    'links':     {'ew_glasswing': 1.2, 'ew_slagjaw': 1.6},
    'rim':       {'ew_glasswing': 1.0, 'ew_slagjaw': 1.6},
    'bellows':   {'ew_slagjaw': 1.3, 'ew_cinderhorn': 1.6},
    'reach':     {'ew_slagjaw': 1.9, 'ew_cinderhorn': .6},
    'steppe':    {'ew_glasswing': 1.3, 'ew_slagjaw': 1.3, 'ew_cinderhorn': .6},
    'door':      {'ew_slagjaw': 1.1, 'ew_cinderhorn': 1.5},
    'quench':    {'ew_slagjaw': 2.1, 'ew_glasswing': .8},
    'ember':     {'ew_cinderhorn': 2.1, 'ew_slagjaw': .8},
    'shore':     {'ew_glasswing': 1.9, 'ew_ashback': 1.0},
    'slagbanks': {'ew_slagjaw': 1.6, 'ew_ashback': .8},
    'fold':      {'ew_cinderhorn': 1.8, 'ew_glasswing': 1.0},
}
# volcano cones where the painting shows its peaks: x, y, size (0-2)
CONES = [(50, 75, 2), (150, 26, 1), (285, 84, 2), (332, 128, 1), (238, 142, 1), (160, 153, 0), (198, 166, 1), (62, 112, 0), (240, 306, 1), (92, 238, 1), (114, 214, 0),
         (306, 162, 0), (208, 46, 0), (326, 214, 0), (160, 322, 0), (72, 292, 0)]


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def moved(o, dx, dy):
    q = dict(o)
    q['x'] = round(o['x'] + dx, 2)
    q['y'] = round(o['y'] + dy, 2)
    return q


def gates(F):
    """The rim gates stand 2.5 tiles in from the last land cell, arrival six tiles inside: id -> (x, y, walk, arrival). The Flats and Canopy borders are seams (no gate)."""
    out = {}
    x = 118
    y0 = int(np.nonzero(F[:, x])[0].min())
    out['atlas_45_15'] = (x + .5, y0 + 2.5, (0, -1), (x + .5, y0 + 8.5))
    y = 130
    x1 = int(np.nonzero(F[y])[0].max())
    out['path_45_21'] = (x1 - 2.5, y + .5, (1, 0), (x1 - 8.5, y + .5))
    return out


def roads(G):
    nor, rib = G['atlas_45_15'], G['path_45_21']
    return [R1, R2, R3, R4, R5, R6,
            [(nor[0], nor[1]), nor[3], (120, 30)],
            [(rib[0], rib[1]), rib[3], (320, 136), (283, 140)]]


class Emberwake(Designer):
    TAG, SEED = 'ember_design_v1', 20261108
    LATE_SEAMS = {21, 15}   # the Ribbonwild's and the Orrery's seams arrived after this design was approved (2026-11-08): the masks stay as they were (the phantom gates path_45_21 and atlas_45_15 keep their discs and their roads)

    def __init__(self, world, old):
        self.old = old
        self.G = gates(np.array([[c == '#' for c in row] for row in world['shapeFloor']]))
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        # the borders to the Flats (19) and the Canopy (16) are seams: nothing the other side cannot draw stands near them
        self.reserve = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] in (16, 19):
                self.reserve = np.minimum(self.reserve, seg_field(e['points'], self.xs, self.ys))
        self.coast = np.full((self.n, self.n), 1e9)
        for e in world['shape']['edges']:
            if e['kind'] == 'coast':
                self.coast = np.minimum(self.coast, seg_field(e['points'], self.xs, self.ys))
        self.lava = []

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.reserve[iy, ix] > 3
                and self.grid.free(x, y, R.get(kind, .5) if r is None else r, .3))

    def rim_ring(self, centre, rx, ry, kind, gaps, step=3.2, rot=0.):
        """A ring of tall columns round a crater, open at `gaps` (centre angle in degrees, half width in degrees; 90 is south)."""
        k = 0
        n = int(math.tau * (rx + ry) / 2 / step)
        for i in range(n):
            a = i / n * math.tau + rot
            deg = math.degrees(a) % 360
            if any(min(abs(deg - c), 360 - abs(deg - c)) < half for c, half in gaps):
                continue
            x, y = centre[0] + math.cos(a) * rx, centre[1] + math.sin(a) * ry
            if self.ok(x, y, kind, lane=2.0):
                self.add(kind, x, y)
                k += 1
        return k

    def fill(self, name, kinds, gap=.8, road=2.8):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per / 1000))
            tall = kind in ('ew_basalt', 'ew_obsidian', 'ew_link')
            placed += self.scatter([kind], k, self.mask(name) & (self.reserve > 3.5), gap=1.3 if tall else gap, road=3.6 if tall else road)
        return placed

    def lake(self, cx, cy, rx, ry, step=2.6, rad=3.0):
        """A lava lake: a union of lava circles (solid); the client paints the molten ground from them."""
        y = cy - ry
        row = 0
        while y <= cy + ry:
            x = cx - rx + (step / 2 if row % 2 else 0)
            while x <= cx + rx:
                wob = 1 + (fbm(self.noise, x, y, .2) - .5) * .5
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= wob and self.floor[int(y), int(x)]:
                    self.add('ew_lava', x, y, r=round(rad + (fbm(self.noise, x * 1.3, y * 1.3, .3) - .5) * 1.2, 2), v=0)
                    self.lava.append(self.objects[-1])
                x += step
            y += step * .866
            row += 1
        self.block_disc(cx, cy, max(rx, ry) + 3)

    def river(self):
        """The glowing river from the Canopy end to the Ribbonwild: circles of varying radius along the painted path, broken at the causeway."""
        pts = dense_points(RIVER, 1.4)
        for x, y in pts:
            if not (0 <= int(x) < self.n and 0 <= int(y) < self.n and self.floor[int(y), int(x)]):
                continue
            if math.dist((x, y), CAUSEWAY) < 8.5:
                continue
            r = round(4.3 + (fbm(self.noise, x, y, .09) - .5) * 2.6, 2)
            self.add('ew_lava', x, y, r=r, v=0)
            self.lava.append(self.objects[-1])
        self.block_disc(*CAUSEWAY, 9)

    def take_hub(self):
        """The Door, its tablet, the Voice below and the Meeting Stone, moved as a rigid block."""
        out = []
        dx, dy = D_DOOR
        for o in self.old['objects']:
            if o['kind'] in ('ew_door', 'meetingstone', 'ew_tablet', 'ew_echo'):
                q = moved(o, dx, dy)
                q['layout'] = self.TAG
                out.append(q)
                self.grid.add(q['x'], q['y'], max(q['r'], q.get('width', 0) / 2))
        return out

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        w = self.w
        self.fixed = self.take_hub()
        self.ground = np.zeros((self.n, self.n), np.uint8)
        for o in w['objects']:
            if o['kind'] == 'void':
                self.fixed.append(o)
        for p in w['places']:
            self.block_disc(p['x'], p['y'], 5)
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.blocked |= self.reserve < 2.5
        for h in content.HAMLETS.values():
            assert self.floor[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        self.pins = []
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 9)
            self.pins.append((x, y, 9))
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3.5)
        content.dress(self, content.HAMLETS)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        # the river first (the lava circles are the collision), then the two lava lakes
        self.river()
        self.lake(CALDERA[0], CALDERA[1] - 8, 19, 6)
        self.lake(HOT[0], HOT[1] - 8, 11, 5, rad=2.8)
        # the great crater and the hot crater: rings of basalt columns open at the roads and the elites' approaches; the cold crater a ring of obsidian
        self.rim_ring(CALDERA, 41, 22, 'ew_basalt', [(90, 12), (180, 9), (0, 9), (270, 9)], rot=.1)
        self.rim_ring(HOT, 31, 18, 'ew_basalt', [(270, 14), (90, 11), (180, 8), (0, 8)], rot=.2)
        self.rim_ring(QUENCH, 23, 14, 'ew_obsidian', [(270, 15), (0, 15), (90, 15)], rot=.15)
        # the volcano cones where the painting shows its peaks
        self.skipped_cones = []
        for cx, cy, v in CONES:
            r = CONE_R[v]
            if self.ok(cx, cy, 'ew_cone', lane=r + 3, r=r) and self.reserve[int(cy), int(cx)] > 12:
                self.add('ew_cone', cx, cy, r=r, v=v)
            else:
                self.skipped_cones.append((cx, cy))
        # the First Shackle: two shackles and three half-buried links round Chainmaw's ground
        for kind, dx, dy in (('ew_shackle', -10, -5), ('ew_shackle', 11, 7), ('ew_link', -4, 9), ('ew_link', 6, -9), ('ew_link', 14, -2)):
            ex, ey = content.ELITES[0][1] + dx, content.ELITES[0][2] + dy
            if self.ok(ex, ey, kind, lane=2.0):
                self.add(kind, ex, ey, v=0)
        # chain lamps along the roads every 34 tiles, on alternate sides
        for road in (R1, R2, R3, R4):
            pts = dense_points(road, 1.0)
            for i in range(14, len(pts) - 6, 34):
                x, y = pts[i]
                nx, ny = pts[min(i + 1, len(pts) - 1)][0] - pts[i - 1][0], pts[min(i + 1, len(pts) - 1)][1] - pts[i - 1][1]
                ln = math.hypot(nx, ny) or 1
                side = 1 if (i // 34) % 2 else -1
                lx, ly = x - ny / ln * 3.4 * side, y + nx / ln * 3.4 * side
                if self.ok(lx, ly, 'ew_lantern', lane=2.0) and self.reserve[int(ly), int(lx)] > 22:
                    self.add('ew_lantern', lx, ly, v=0)
        # the hold circles and the elites' rings: a low ring of slag marks where each stands
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'ew_slag', rot=.4)
        for _, x, y in content.ELITES:
            self.ring_of((x, y), 5.5, 6, 'ew_slag', rot=.7)

    def ring_of(self, centre, radius, n, kind, rot=.3, **extra):
        k = 0
        for i in range(n):
            a = i / n * math.tau + rot
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.ok(x, y, kind):
                self.add(kind, x, y, **extra)
                k += 1
        return k

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        tall = ('ew_basalt', 'ew_obsidian', 'ew_cone', 'ew_link')
        self.objects[:] = [o for o in self.objects if not (o['kind'] in tall and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        # the sand of the black shore to the water's edge, the bank of cooled slag along the river, the crater floors, the quenched basin
        g[self.floor & (self.coast < 20)] = GROUND['sand']
        near = np.full((self.n, self.n), 1e9)
        for o in self.lava:
            if self.lava_dropped(o):
                continue
            near = np.minimum(near, np.hypot(self.xs - o['x'], self.ys - o['y']) - o['r'])
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        g[self.floor & (near < 6 + rough * .5)] = GROUND['slag']
        for (cx, cy, rx, ry, cls) in ((CALDERA[0], CALDERA[1], 36, 18, 'crater'), (HOT[0], HOT[1], 27, 14, 'crater'), (QUENCH[0], QUENCH[1], 20, 12, 'quench')):
            g[self.floor & (((self.xs - cx) / rx) ** 2 + ((self.ys - cy) / ry) ** 2 < 1 + rough * .02)] = GROUND[cls]

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
        for s in self.old['slimes']:
            if str(s.get('ambush', '')).startswith('empty-seat:'):
                out.append(dict(s, x=round(ES25[0] + 2, 2), y=ES25[1]))
        out += [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in content.HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        solid = Grid()
        for o in self.fixed + self.objects:
            if o['kind'] != 'void':
                solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
        self.short = {}
        self.counts = {}
        for name, kinds in SPAWN_DENSITY.items():
            area = int(self.mask(name).sum())
            pool = [k for k, per in kinds.items() for _ in range(max(1, int(area * per / 1000)))]
            self.counts[name] = len(pool)
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.reserve > 22))      # a spawn is placed up to a cell off the cell's centre: 4.4 keeps it 3.4+ tiles from every road (tests/seam-roads.py); 22 keeps a calm strip along both seams
            if not len(pts):
                self.short[name] = len(pool)
                continue
            sep, placed, tries = 12.0, 0, 0
            while placed < len(pool) and tries < 40000:
                tries += 1
                if tries % 8000 == 0:
                    sep *= .85
                j, i = pts[rng.randrange(len(pts))]
                x, y = round(i + rng.random() * .98, 2), round(j + rng.random() * .98, 2)
                if any(math.hypot(x - s['x'], y - s['y']) < sep for s in out) or not solid.free(x, y, .6, .15) or self.lava_near(x, y) < 3:
                    continue
                out.append({'x': x, 'y': y, 'kind': pool[placed], 'layout': self.TAG})
                placed += 1
            if placed < len(pool):
                self.short[name] = len(pool) - placed
        ordinary = [t for t in out if t.get('layout') == self.TAG]
        ordinary.sort(key=lambda t: t['kind'] != 'ew_ashback')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]

    def lava_dropped(self, o):
        """The Ribbonwild's seam (late): a seam neighbour draws no lava, so the river's circles within 17 tiles of it are not kept (the masks and the scatter were made with them)."""
        return self.seam_late[min(max(int(o['y']), 0), self.n - 1), min(max(int(o['x']), 0), self.n - 1)] - o['r'] < 18      # 18: the field is read at the cell centre, the test measures the exact point

    def lava_near(self, x, y):
        return min((math.hypot(x - o['x'], y - o['y']) - o['r'] for o in self.lava if abs(o['x'] - x) < 12 and abs(o['y'] - y) < 12), default=1e9)


# ---- moving the old people, places and portals ---------------------------------------------------------------------------
def shifted_state(zone, old, G):
    """Chainrest, the Door camp, the people, the places and the gates in the new frame."""
    dx, dy = D_DOOR
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    by = {n['id']: n for n in zone['npcs']}
    for n in old['npcs']:
        t = by.get(n['id'])
        if not t:
            continue
        if n['id'] in content.HUB_NPCS:
            hn, ox, oy = content.HUB_NPCS[n['id']]
            h = content.HAMLETS[hn]
            t['x'], t['y'] = h['x'] + ox, h['y'] + oy
        elif n['id'] in content.DOOR_NPCS:
            t['x'], t['y'] = round(n['x'] + dx, 2), round(n['y'] + dy, 2)
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    for p in zone['places']:
        o = next((q for q in old['places'] if q['id'] == p['id']), None)
        if p['id'] == 'es_25_m':
            p['x'], p['y'] = ES25
        elif p['id'] in ('es_26_m', 'ew_door'):
            p['x'], p['y'] = round(o['x'] + dx, 2), round(o['y'] + dy, 2)
        elif p['id'] == 'ew_road':
            p['x'], p['y'] = 226.0, 62.0
        elif p['id'] == 'ew_causeway':
            p['x'], p['y'] = CAUSEWAY
    for p in zone['portals']:
        if p.get('seam'):           # the Flats and Canopy seams (zone_shapes.make_seams): their line is the border, not a gate
            continue
        if p['id'] == 'ew_raid':
            p['x'], p['y'] = round(133 + dx, 2), round(24 + dy, 2)
            continue
        gx, gy, walk, arr = G[p['id']]
        p['x'], p['y'] = round(gx, 2), round(gy, 2)
        p['walk'] = list(walk)


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of Emberwake, both ways, as compact_atlas.sync_travel_links does."""
    zones = [world] + world['zones']
    masters = lambda z: [n for n in z.get('npcs', []) if n.get('travelStop')]
    for i, z in enumerate(zones):
        for p in z['portals']:
            if p['to'] == i or ZONE not in (i, p['to']):
                continue
            mine, other = masters(z), masters(zones[p['to']])
            if not mine or not other:
                continue
            a = min(mine, key=lambda n: math.hypot(n['x'] - p['x'], n['y'] - p['y']))
            b = min(other, key=lambda n: math.hypot(n['x'] - p['tx'], n['y'] - p['ty']))
            if b['id'] not in a['travelLinks']:
                a['travelLinks'].append(b['id'])
            if a['id'] not in b['travelLinks']:
                b['travelLinks'].append(a['id'])


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F)
    shifted_state(zone, old, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Emberwake(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    late_seams = [t for t in sorted(Emberwake.LATE_SEAMS) if any(p.get('seam') and p['to'] == t for p in zone['portals'])]
    if late_seams:      # the Ribbonwild's (east) and the Orrery's (north-west) seams (2026-11-08) replaced rim gates: only the spawns within 7 tiles of them and the lava circles within 17 go
        d.late_dropped = sum(drop_near_seam(zone, d, t) for t in late_seams)
        before = len(objects)
        objects = [o for o in objects if not (o['kind'] == 'ew_lava' and d.lava_dropped(o))]
        d.lava = [o for o in d.lava if not d.lava_dropped(o)]
        d.late_dropped += before - len(objects)
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}      # the Ribbonwild's seam replaced the east rim gate: its line is the border, not a gate
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items() if g not in seamed]
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, content.HAMLETS)
    # every crossing that arrives here follows the new frame: the Orrery's and the Ribbonwild's gates, and the raid's two ways out (the seams carry their own shift)
    arrivals = {'atlas_15_45': G['atlas_45_15'][3], 'path_21_45': G['path_45_21'][3], 'cf_return': DOOR_ARR, 'cf_clear': DOOR_ARR}
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
    # the five new masters join the Spark network of their neighbours: compact_atlas links the master nearest a portal with the one nearest its arrival, but ran before
    # the design made them, and a global re-run would rewrite every other pilot zone's links, so only the links across Emberwake's own portals are added
    link_travel(world)
    if write:
        content.record_mailboxes(zone, content.HAMLETS, ROOT / 'world/mailboxes.txt')
    problems = check(zone, d, solid, seen, G)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']), lava=len(d.lava), skipped_cones=d.skipped_cones,
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('ew_basalt', 'ew_obsidian', 'ew_slag', 'ew_ashtree', 'ew_cone', 'ew_vent', 'ew_link', 'ew_lantern')})
    if problems:
        if os.environ.get('EMBER_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')


def check(zone, d, solid, seen, G):
    problems = []
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    if not (lost < open_cells.sum() * .02):
        problems.append(f'{lost} open cells are cut off from the spawn')
    for t in zone['slimes']:
        if not d.floor[int(t['y']), int(t['x'])]:
            problems.append(f'spawn off land {t}')
        if not seen[int(t['y']), int(t['x'])]:
            problems.append(f'unreachable spawn {t}')
        if d.reserve[int(t['y']), int(t['x'])] <= 7:
            problems.append(f'spawn within 7 tiles of a seam {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
        if walk and not seen[int(gy - walk[1] * 3), int(gx - walk[0] * 3)]:
            problems.append(f'gate {g} is blocked from the inside')
    raid = next(q for q in zone['portals'] if q['id'] == 'ew_raid')
    if not seen[int(raid['y'] + 2), int(raid['x'])]:
        problems.append('the Nine-Chain Door is cut off')
    # the causeway is the one crossing of the river besides the west end: both banks reachable
    for name, (x, y) in (('Glasshold', (292, 226 + 8)), ('Cinderquay', (186, 312)), ('the Ember Crater', (253, 248))):
        if not seen[int(y), int(x)]:
            problems.append(f'{name} is cut off')
    bad = set()
    for road in d.ROADLIST + [r['points'] for r in zone['exitRoutes']]:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                if not d.floor[int(y), int(x)]:
                    problems.append(f'road leaves the land at {x:.0f},{y:.0f}')
                inside = any(c['x0'] - 1 <= x <= c['x1'] + 1 and c['y0'] - 1 <= y <= c['y1'] + 3 for c in [zone['city']] + zone['camps'])
                if not inside and solid[int(y), int(x)]:
                    bad.add((int(x), int(y)))
    if bad:
        problems.append(f'something stands on the road at {sorted(bad)[:12]}')
    # lava stands 17+ tiles from both seams: a seam neighbour draws no lava
    for o in d.lava:
        if d.reserve[min(max(int(o['y']), 0), d.n - 1), min(max(int(o['x']), 0), d.n - 1)] - o['r'] < 17:
            problems.append(f"lava within 17 tiles of a seam at {o['x']},{o['y']}")
            break
    # the late seams (the Ribbonwild's, the Orrery's): no lava within 17 tiles of them and no art-less object within 20 (a seam neighbour draws neither)
    at_late = lambda o: d.seam_late[min(max(int(o['y']), 0), d.n - 1), min(max(int(o['x']), 0), d.n - 1)]
    if any(at_late(o) - o['r'] < 17 for o in d.lava):
        problems.append('lava within 17 tiles of a late seam')
    near_late = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o['kind'] in ARTLESS and at_late(o) < 20]
    if near_late:
        problems.append(f'art-less objects within 20 tiles of a late seam: {near_late[:5]}')
    # an elite stands clear of everything a player walks to: awareness plus 3 tiles from every road, place and person, and from every hub and gate
    walked = [(q, 'road') for road in d.ROADLIST for q in dense_points(road)]
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places']] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs']]
    walked += [((q['x'], q['y']), f"portal {q['id']}") for q in zone['portals'] if not q.get('seam')]
    for kind, ex, ey in content.ELITES:
        near = min(((math.dist((ex, ey), q), what) for q, what in walked), key=lambda t: t[0])
        if near[0] < content.AWARENESS[kind] + 3:
            problems.append(f'{kind} stands {near[0]:.1f} tiles from a {near[1]}: its awareness is {content.AWARENESS[kind]:.0f}')
        for c in [zone['city']] + zone['camps']:
            gap = math.hypot(max(c['x0'] - ex, 0, ex - c['x1']), max(c['y0'] - ey, 0, ey - c['y1']))
            if gap < content.AWARENESS[kind] + 3:
                problems.append(f'{kind} stands {gap:.1f} tiles from a hub')
        for gname, (gx, gy, walk, arr) in G.items():
            if math.dist((ex, ey), (gx, gy)) < 20:
                problems.append(f'{kind} stands near the gate {gname}')
    popping = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o['kind'] in ARTLESS and d.reserve[int(o['y']), int(o['x'])] < 20]
    if popping:
        problems.append(f'art-less objects within the camera reach of a seam pop in on crossing: {popping[:5]}')
    loose = [(o['kind'], o['x'], o['y']) for o in zone['objects'] if o.get('layout') == d.TAG and o['kind'] not in ('void', 'ew_lava') and d.reserve[int(o['y']), int(o['x'])] < 2.5]
    if loose:
        problems.append(f'loose scenery within 2.5 tiles of a seam: {loose[:5]}')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    names = list(REGIONS)
    want = {'ew_chainmaw': 'links', 'ew_bellows': 'bellows', 'ew_crown': 'ember'}
    for kind, ex, ey in content.ELITES:
        if names[int(d.region[int(ey), int(ex)])] != want[kind]:
            problems.append(f'{kind} stands in {names[int(d.region[int(ey), int(ex)])]}')
    for h in content.HAMLETS.values():
        if not h.get('block') and d.reserve[int(h['y']), int(h['x'])] < 20 + h['hw']:
            problems.append(f"{h['name']} stands within 20 tiles of a seam")
    return problems


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    T = zone['shape']['T']
    s = 1758 / 2048
    atlas = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
    x0, y0 = int(round(T[0] * s)), int(round(T[1] * s))
    bg = atlas.crop((x0, y0, x0 + int(n * s), y0 + int(n * s))).resize((n * scale, n * scale), Image.LANCZOS)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (20, 20, 30)), .5)
    pal = {1: (90, 80, 90), 2: (140, 70, 60), 3: (60, 80, 120), 4: (110, 110, 120), 5: (150, 90, 50), 6: (160, 50, 40), 7: (80, 110, 150), 8: (170, 165, 160), 9: (50, 50, 55), 10: (190, 80, 30)}
    a = np.array(bg)
    for k, c in pal.items():
        m = np.kron((d.ground == k) & d.floor, np.ones((scale, scale), bool))
        a[m] = (a[m] * .45 + np.array(c) * .55).astype(np.uint8)
    out_mask = np.kron(~d.floor, np.ones((scale, scale), bool))
    a[out_mask] = (a[out_mask] * .35).astype(np.uint8)
    im = Image.fromarray(a)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(250, 220, 120), width=scale)
    col = {'ew_basalt': (200, 200, 210), 'ew_obsidian': (110, 150, 230), 'ew_slag': (150, 110, 90), 'ew_ashtree': (90, 90, 90), 'ew_cone': (230, 120, 70), 'ew_vent': (230, 230, 120),
           'ew_link': (240, 200, 90), 'ew_lantern': (255, 255, 160), 'ew_lava': (255, 120, 20), 'ew_shackle': (255, 255, 255), 'ew_door': (255, 90, 90)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('ew_slag', 'ew_ashtree') else 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'ew_ashback': (240, 120, 120), 'ew_glasswing': (120, 220, 255), 'ew_slagjaw': (240, 240, 120), 'ew_cinderhorn': (230, 100, 230)}
    for s_ in zone['slimes']:
        c = kc.get(s_['kind'], (255, 20, 20))
        g.rectangle([s_['x'] * scale - 2, s_['y'] * scale - 2, s_['x'] * scale + 2, s_['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    for camp in [zone['city']] + zone['camps']:
        g.rectangle([camp['x0'] * scale, camp['y0'] * scale, camp['x1'] * scale, camp['y1'] * scale], outline=(255, 160, 0), width=2)
        g.text((camp['plaza']['x'] * scale - 20, camp['plaza']['y'] * scale + 40), camp['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for r in REGIONS.values():
        sx, sy = r['seeds'][0]
        g.text((sx * scale - 20, sy * scale - 14), r['name'], fill=(240, 240, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    for p in zone['places']:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(120, 255, 160), stroke_width=1, stroke_fill=(0, 0, 0))
    for p in zone['portals']:
        if p.get('seam'):
            g.line([(x * scale, y * scale) for x, y in p['seam']['points']], fill=(255, 60, 255), width=3)
            continue
        g.ellipse([p['x'] * scale - 6, p['y'] * scale - 6, p['x'] * scale + 6, p['y'] * scale + 6], outline=(255, 60, 60), width=3)
        g.text((p['x'] * scale + 8, p['y'] * scale - 6), p['name'], fill=(255, 120, 120), stroke_width=1, stroke_fill=(0, 0, 0))
    for kind, ex, ey in content.ELITES:
        g.ellipse([ex * scale - 8, ey * scale - 8, ex * scale + 8, ey * scale + 8], outline=(255, 0, 0), width=3)
        g.text((ex * scale + 10, ey * scale - 6), kind, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    im.save(out)


def main():
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
