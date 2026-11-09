#!/usr/bin/env python3
"""The Veyrroot Canopy as an authored, WILD map (zone 23 of the shapes pilot): no filler land, the whole outline used, seamless against the Tanglecrown and the Lapis Erg.

Owner request 2026-11-09: "for pilot. reshape veyroot. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the Tanglecrown AND the Lapis Erg (Sunward
Vale stays a gate), **Veyrroot is wild with enemies** (it was a peaceful city; Heartwood becomes the main city), three outposts, keep the old quests. The Hollow Arch at the foot of the Great Tree leads
to Heartwood.

The outline at k = 1.0 is grid 352 with 64,756 land tiles (the old square held 16,384): a wide wedge. The Lapis Erg lies along its whole north side (the seam), the Tanglecrown along the south-west
(the seam), Sunward Vale along the west and a coast on the east. The painting shows teal canopy masses cut by pale trails, a big sandy glade in the west and the Great Tree on a round green clearing
in the middle-south. The zone keeps its own style: the existing worldtree scenery (buttress roots, hanging pods, lantern vines, epiphyte gardens) plus a few wild kinds (`client/veyrrootart.js`).

Runs in `zone_shapes.py apply` after the Lapis Erg's design. The zone is `designOnly` + `rebuild` (zone-shapes.txt): the old 128 square is not moved, everything is made here from
`world/zone-shapes/preshape-23.txt` (the old people, places, quests and the Hollow Arch keep their ids).

    python3 scripts/veyrroot_design.py plan OUT.png     draw the plan from the cached shaped world (read only)
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
import veyrroot_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, drop_near_seam, fbm, ground_spans, is_seam_portal, late_targets, seg_field, step_back_artless  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-23.txt'

ZONE = 23
SUNWARD, TANGLE, LAPIS, HEARTWOOD = 20, 22, 25, 24
HAM = content.HAMLETS
SPAWN = (HAM['rootfoot']['x'] - HAM['rootfoot']['hw'] + 4.5, HAM['rootfoot']['y'] + .5)     # Rootfoot's own entry, inside the west side of the city
TANGLE_X, LAPIS_X = 118.5, 191.5    # where the approved zones' roads end on the border (the Tanglecrown's gate at x 184.5, the Lapis Erg's at x 135.5), in this zone's frame
SEAM_SPAWN, SEAM_LOOSE, SEAM_PEOPLE = 10.0, 3.0, 22.0

REGIONS = {
    'sunstair':   dict(name='The Moss Stair', seeds=[(70, 118), (58, 152), (84, 140), (40, 200)]),
    'glade':      dict(name='The Sunlit Glade', seeds=[(100, 200), (130, 214), (120, 184), (88, 218)]),
    'gardens':    dict(name='The Hanging Gardens', seeds=[(118, 150), (100, 128), (140, 150)]),
    'hive':       dict(name='The Hive Canopy', seeds=[(138, 100), (118, 108), (160, 84), (104, 98)]),
    'twinroots':  dict(name='The Twin Roots', seeds=[(240, 86), (222, 68), (262, 100), (282, 74)]),
    'stairreach': dict(name='The Rootstair Reach', seeds=[(200, 98), (186, 120), (214, 122)]),
    'rise':       dict(name='The Sunleaf Rise', seeds=[(252, 146), (240, 174), (270, 132)]),
    'eastroots':  dict(name='The Eastern Roots', seeds=[(312, 118), (300, 150), (322, 90), (330, 70)]),
    'coast':      dict(name='The Bark Coast', seeds=[(300, 200), (318, 168), (292, 236), (304, 262)]),
    'heart':      dict(name='The Heart Clearing', seeds=[(210, 220), (188, 240), (232, 240), (212, 256)]),
    'sapflats':   dict(name='The Amber Sap Flats', seeds=[(204, 272), (240, 284), (262, 266)]),
    'fernbreak':  dict(name='The Fernbreak', seeds=[(140, 250), (166, 268), (110, 232)]),
    'tangleverge': dict(name='The Tangle Verge', seeds=[(118, 274), (74, 254), (30, 232), (176, 290)]),
    'lapisverge': dict(name='The Lapis Verge', seeds=[(190, 62), (150, 68), (240, 60), (110, 76), (300, 66)]),
}
GROUND = {'canopy': 1, 'loam': 2, 'litter': 3, 'glade': 4, 'amber': 5, 'bark': 6, 'fern': 7, 'shade': 8, 'teal': 9}
REGION_GROUND = {'sunstair': 'fern', 'glade': 'glade', 'gardens': 'teal', 'hive': 'litter', 'twinroots': 'bark', 'stairreach': 'loam', 'rise': 'canopy', 'eastroots': 'bark', 'coast': 'litter',
                 'heart': 'canopy', 'sapflats': 'amber', 'fernbreak': 'shade', 'tangleverge': 'fern', 'lapisverge': 'litter'}

R = {'vr_canopy_tree': 1.25, 'vr_fernbank': .2, 'vr_amber_bloom': .1, 'vr_moss_stone': .8, 'buttress_root': 1.2, 'hanging_pod': .75, 'leaf_lantern': .12, 'epiphyte_garden': .25,
     'canopy_market': 1.1, 'suspended_garden': 1.2, 'banyan_lodge': 2.2, 'worldheart_trunk': 9}
TALL = ('vr_canopy_tree', 'buttress_root')

# scenery per 1000 land tiles of the region (x DENSITY_SCALE)
DENSITY_SCALE = 1.0
DENSITY = {
    'sunstair':   [('vr_canopy_tree', 7), ('vr_fernbank', 8), ('epiphyte_garden', 4), ('vr_moss_stone', 2), ('buttress_root', 1.5)],
    'glade':      [('vr_fernbank', 7), ('vr_amber_bloom', 7), ('vr_moss_stone', 2), ('vr_canopy_tree', 1.2), ('leaf_lantern', 1)],
    'gardens':    [('epiphyte_garden', 7), ('vr_fernbank', 7), ('hanging_pod', 3), ('vr_canopy_tree', 4), ('leaf_lantern', 2)],
    'hive':       [('vr_canopy_tree', 8), ('hanging_pod', 5), ('leaf_lantern', 4), ('epiphyte_garden', 4), ('buttress_root', 2)],
    'twinroots':  [('buttress_root', 5), ('vr_canopy_tree', 5), ('vr_fernbank', 5), ('vr_moss_stone', 3), ('hanging_pod', 2)],
    'stairreach': [('vr_canopy_tree', 7), ('leaf_lantern', 4), ('hanging_pod', 3), ('vr_fernbank', 6), ('epiphyte_garden', 3)],
    'rise':       [('vr_canopy_tree', 6), ('vr_fernbank', 6), ('leaf_lantern', 3), ('epiphyte_garden', 4), ('hanging_pod', 2)],
    'eastroots':  [('buttress_root', 6), ('vr_canopy_tree', 5), ('vr_moss_stone', 4), ('vr_fernbank', 4)],
    'coast':      [('vr_canopy_tree', 4), ('vr_fernbank', 7), ('vr_moss_stone', 3), ('vr_amber_bloom', 3), ('buttress_root', 2)],
    'heart':      [('vr_fernbank', 6), ('vr_amber_bloom', 5), ('leaf_lantern', 3), ('epiphyte_garden', 3), ('vr_canopy_tree', 2.5)],
    'sapflats':   [('vr_amber_bloom', 8), ('vr_moss_stone', 4), ('vr_fernbank', 4), ('vr_canopy_tree', 2.5), ('buttress_root', 1.5)],
    'fernbreak':  [('vr_fernbank', 12), ('vr_canopy_tree', 6), ('vr_moss_stone', 2), ('epiphyte_garden', 3)],
    'tangleverge': [('vr_canopy_tree', 6), ('vr_fernbank', 8), ('epiphyte_garden', 3), ('hanging_pod', 2)],
    'lapisverge': [('vr_canopy_tree', 5), ('vr_fernbank', 6), ('vr_moss_stone', 3), ('vr_amber_bloom', 3)],
}
# spawns per 1000 land tiles (a spawn has no level: difficulty comes from which kind stands where): lemurs in the west and the gardens, beetles in the glade and on the sap flats,
# hornets in the north and the hive canopy, bark mimics in the east and round the tree
SPAWN_SCALE = 1.0
SPAWN_DENSITY = {
    'sunstair':   {'mosslemur': 2.4},
    'glade':      {'sapbeetle': 2.6, 'mosslemur': .8},
    'gardens':    {'mosslemur': 3.2, 'lanternhornet': .6},
    'hive':       {'lanternhornet': 3.4, 'mosslemur': .6},
    'twinroots':  {'lanternhornet': 2.0, 'barkmimic': 1.4},
    'stairreach': {'lanternhornet': 2.4, 'mosslemur': .6},
    'rise':       {'lanternhornet': 1.6, 'barkmimic': 1.2},
    'eastroots':  {'barkmimic': 3.6},
    'coast':      {'barkmimic': 2.4, 'sapbeetle': .8},
    'heart':      {'barkmimic': 1.0},
    'sapflats':   {'sapbeetle': 3.8},
    'fernbreak':  {'sapbeetle': 1.8, 'mosslemur': 1.6},
    'tangleverge': {'sapbeetle': 1.4, 'mosslemur': 1.0},
    'lapisverge': {'lanternhornet': 1.4, 'barkmimic': .8},
}


def dense_points(path, step=2.0):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        k = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def border_y(zone, other, x):
    """y of this zone's shared border with `other` at column x (the run is monotonic in x)."""
    pts = max([e for e in zone['shape']['edges'] if e['kind'] == 'shared' and e['other'] == other], key=lambda e: len(e['points']))['points']
    for a, b in zip(pts, pts[1:]):
        if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
            return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
    raise AssertionError(f'no border column {x}')


def gates(F, zone):
    """Sunward's rim gate stands 2.5 tiles in from the last land cell, arrival six tiles inside; the two seams have no gate, only the crossing the roads aim at: id -> (x, y, walk, arrival)."""
    out = {}
    y = 130
    x0 = int(np.nonzero(F[y])[0].min())
    out['path_23_20'] = (x0 + 2.5, y + .5, (-1, 0), (x0 + 8.5, y + .5))
    yt = border_y(zone, TANGLE, TANGLE_X)
    out['canopy_jungle_gate'] = (TANGLE_X, round(yt, 2), (0, 1), (TANGLE_X, round(yt - 6.5, 2)))
    yl = border_y(zone, LAPIS, LAPIS_X)
    out['canopy_lapis_gate'] = (LAPIS_X, round(yl, 2), (0, -1), (LAPIS_X, round(yl + 6.5, 2)))
    return out


def roads(G):
    sun, tg, lp = G['path_23_20'], G['canopy_jungle_gate'], G['canopy_lapis_gate']
    west = [(sun[0], sun[1]), sun[3], (62, 142), (80, 156), (96, 172), (108, 182), (114, 196), (126, 208), (152, 224), (178, 234), (188, 241)]
    south = [(tg[0], tg[1] - 1.2), tg[3], (120, 258), (130, 242), (144, 226), (152, 224)]
    north = [(230, 226), (242, 205), (246, 176), (252, 152), (242, 128), (224, 112), (217, 106), (214, 98), (213, 89), (207, 82), (200, 70), lp[3], (lp[0], lp[1] + 1.2)]
    east = [(232, 244), (258, 238), (280, 224), (296, 206)]
    link = [(252, 152), (272, 164), (288, 180), (298, 186)]
    garden = [(108, 182), (110, 168), (114, 156), (118, 150)]
    hive = [(216, 101), (214, 107), (204, 108), (190, 105), (170, 108), (154, 118)]
    flats = [(202, 258), (202, 264), (204, 270)]
    eroots = [(298, 186), (300, 172), (304, 156)]
    twin = [(216, 100), (228, 92), (240, 86)]
    return [west, south, north, east, link, garden, hive, flats, eroots, twin]


class Veyrroot(Designer):
    TAG, SEED = 'veyrroot_design_v1', 20261110
    LATE_SEAMS = {20}       # Sunward Vale's seam arrived after this design was approved (2026-11-09): the masks stay as they were (the rim gate keeps its discs and its road)

    def __init__(self, world, old):
        self.old = old
        self.F = np.array([[c == '#' for c in row] for row in world['shapeFloor']])
        self.G = gates(self.F, world)
        self.ROADLIST = roads(self.G)
        super().__init__(world)
        self.pooled = np.full((self.n, self.n), 1e9)

    def plan(self):
        return REGIONS, self.ROADLIST, R

    # ---- helpers ---------------------------------------------------------------------------------------------------------
    def ok(self, x, y, kind, lane=2.4, r=None):
        ix, iy = int(x), int(y)
        return (0 <= ix < self.n and 0 <= iy < self.n and self.inner[iy, ix] and not self.blocked[iy, ix] and self.road[iy, ix] > lane and self.seam[iy, ix] > SEAM_LOOSE
                and self.grid.free(x, y, R.get(kind, .5) if r is None else r, .3))

    def ring_of(self, centre, radius, n, kind, rot=.3, gaps=(), **extra):
        k = 0
        for i in range(n):
            a = i / n * math.tau + rot
            deg = math.degrees(a) % 360
            if any(min(abs(deg - c), 360 - abs(deg - c)) < half for c, half in gaps):
                continue
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.ok(x, y, kind, lane=2.0):
                self.add(kind, x, y, **extra)
                k += 1
        return k

    def fill(self, name, kinds, gap=.8, road=2.8):
        area = int(self.mask(name).sum())
        placed = 0
        for kind, per in kinds:
            k = max(1, int(area * per * DENSITY_SCALE / 1000))
            tall = kind in TALL
            placed += self.scatter([kind], k, self.mask(name) & (self.seam > SEAM_LOOSE), gap=1.6 if tall else gap, road=3.4 if tall else road)
        return placed

    def block_cells(self, mask):
        self.blocked |= mask

    # ---- the plan --------------------------------------------------------------------------------------------------------
    def build(self):
        self.ground = np.zeros((self.n, self.n), np.uint8)
        self.fixed = [o for o in self.w['objects'] if o['kind'] == 'void']
        for g, (gx, gy, walk, arr) in self.G.items():
            self.block_disc(gx, gy, 9)
            self.block_disc(arr[0], arr[1], 9)
        self.block_disc(*SPAWN, 5)
        self.block_disc(*content.TREE, 12)
        self.block_disc(*content.ARCH, 7)
        for h in HAM.values():
            assert self.F[h['y'] - h['hh'] - 2:h['y'] + h['hh'] + 3, h['x'] - h['hw'] - 2:h['x'] + h['hw'] + 3].all(), f"{h['name']} stands off the land"
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 9)
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 3.6)
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3.5)
        self.block_disc(*content.MEMORY, 3.5)
        self.add('worldheart_trunk', *content.TREE, r=9, v=0)
        self.add('hollow_arch', content.ARCH[0], content.ARCH[1] - 1.8, r=0, v=0, width=6, depth=2, place='heart_hollow')      # behind the portal: the way in and out runs south of it
        content.dress(self, HAM)
        self.landmarks()
        self.lay_regions()
        self.lay_ground()
        self.clear_glades()
        return self.fixed + self.objects

    def landmarks(self):
        ex = {k: (x, y) for k, x, y in content.ELITES}
        # a ring of buttress roots round the Lantern Queen's hive and the Heartbark Colossus's grove (open on one side), a ring of lantern vines round the sap golem's pan
        self.ring_of(ex['lanternqueen'], 19, 16, 'buttress_root', rot=.2, gaps=[(40, 40)])
        self.ring_of(ex['barkcolossus'], 18, 18, 'vr_canopy_tree', rot=.5, gaps=[(225, 40)])
        self.ring_of(ex['ambergolem'], 17, 18, 'vr_moss_stone', rot=.1, gaps=[(150, 40)])
        # lantern vines in pairs either side of the north road (the Lantern Walk)
        pts = dense_points(self.ROADLIST[2], 1.0)
        for i in range(8, len(pts) - 4, 12):
            x, y = pts[i]
            side = 1 if (i // 12) % 2 else -1
            if self.ok(x + side * 3.4, y, 'leaf_lantern', lane=2.4):
                self.add('leaf_lantern', x + side * 3.4, y)
        # a low ring of ferns round every hold circle
        for p in content.PLACES:
            if p.get('waves'):
                self.ring_of((p['x'], p['y']), 6.5, 8, 'vr_fernbank', rot=.4)

    def clear_glades(self):
        """Tall scenery in front of an elite hides it: a glade of 12 tiles round each."""
        spots = [(x, y) for _, x, y in content.ELITES]
        self.objects[:] = [o for o in self.objects if not (o['kind'] in TALL and o.get('layout') == self.TAG and any(math.hypot(o['x'] - x, o['y'] - y) < 12 for x, y in spots))]

    def lay_ground(self):
        g = self.ground
        for name, cls in REGION_GROUND.items():
            g[self.mask(name)] = GROUND[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 6
        ex = {k: (x, y) for k, x, y in content.ELITES}
        g[self.floor & (np.hypot(self.xs - content.TREE[0], self.ys - content.TREE[1]) < 20 + rough)] = GROUND['teal']          # the green clearing round the Great Tree
        g[self.floor & (np.hypot(self.xs - ex['ambergolem'][0], self.ys - ex['ambergolem'][1]) < 13 + rough)] = GROUND['amber']
        g[self.floor & (np.hypot(self.xs - ex['lanternqueen'][0], self.ys - ex['lanternqueen'][1]) < 12 + rough)] = GROUND['litter']
        g[self.floor & (np.hypot(self.xs - ex['barkcolossus'][0], self.ys - ex['barkcolossus'][1]) < 12 + rough)] = GROUND['bark']
        g[self.floor & (self.coast < 8 + rough * .5)] = GROUND['loam']

    def lay_regions(self):
        for name in REGIONS:
            self.fill(name, DENSITY[name])
        for o in self.objects:
            if o['kind'] in TALL and o.get('layout') == self.TAG and 'v' not in o:
                o['v'] = self.rng.randrange(4)

    # ---- spawns ------------------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        out = []
        out += [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in HAM.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        solid = Grid()
        for o in self.fixed + self.objects:
            if o['kind'] != 'void':
                solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
        self.short = {}
        self.counts = {}
        for name, kinds in SPAWN_DENSITY.items():
            area = int(self.mask(name).sum())
            pool = [k for k, per in kinds.items() for _ in range(max(1, int(area * per * SPAWN_SCALE / 1000)))]
            self.counts[name] = len(pool)
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 4.4) & (self.seam > SEAM_SPAWN))      # 4.4 keeps a spawn 3.4+ tiles from every road
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
                if any(math.hypot(x - s['x'], y - s['y']) < sep for s in out) or not solid.free(x, y, .6, .15):
                    continue
                out.append({'x': x, 'y': y, 'kind': pool[placed], 'layout': self.TAG})
                placed += 1
            if placed < len(pool):
                self.short[name] = len(pool) - placed
        ordinary = [t for t in out if t.get('layout') == self.TAG]
        ordinary.sort(key=lambda t: t['kind'] != 'mosslemur')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]

    @property
    def coast(self):
        if not hasattr(self, '_coast'):
            self._coast = np.full((self.n, self.n), 1e9)
            for e in self.w['shape']['edges']:
                if e['kind'] == 'coast':
                    self._coast = np.minimum(self._coast, seg_field(e['points'], self.xs, self.ys))
        return self._coast


# ---- the old people, places and portals in the new frame ------------------------------------------------------------------
def restore_and_shift(zone, old, G):
    """A rebuild zone starts empty: bring the old people, places and portals back from the sidecar and put them in the new frame."""
    zone['spawn'] = dict(x=SPAWN[0], y=SPAWN[1])
    links = {n['id']: list(n.get('travelLinks', [])) for n in zone['npcs'] if n.get('travelStop')}       # the Spark links the Tanglecrown's and the Lapis Erg's designs added to the placeholder master earlier in this run
    zone['npcs'] = copy.deepcopy(old['npcs'])
    for n in zone['npcs']:
        if n.get('travelStop') and n['id'] in links:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + links[n['id']]))
    zone['places'] = copy.deepcopy(old['places'])
    zone['quests'] = copy.deepcopy(old['quests'])
    for n in zone['npcs']:
        if n['id'] in content.HUB_NPCS:
            hn, ox, oy = content.HUB_NPCS[n['id']]
            h = content.HAMLETS[hn]
            n['x'], n['y'] = h['x'] + ox, h['y'] + oy
        elif n['id'] in content.ROOTFOOT_PEOPLE:
            h = content.HAMLETS['rootfoot']
            n['x'], n['y'] = h['x'] + content.ROOTFOOT_PEOPLE[n['id']][0], h['y'] + content.ROOTFOOT_PEOPLE[n['id']][1]
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    mine = {p['id']: p for p in content.PLACES}
    for p in zone['places']:
        if p['id'] in mine:
            p['x'], p['y'], p['r'] = mine[p['id']]['x'], mine[p['id']]['y'], mine[p['id']]['r']
        elif p['id'] == 'es_19_m':
            p['x'], p['y'] = content.MEMORY
        else:
            raise AssertionError(f"unplaced old place {p['id']}")
    keep = []
    for p in zone['portals']:
        if p.get('seam'):          # the Tanglecrown's and the Lapis Erg's seams (zone_shapes.make_seams): their line is the border, not a gate; aim_seams stands them where the roads cross
            keep.append(p)
        elif p['id'] == 'canopy_hollow_gate':
            p['x'], p['y'] = content.ARCH[0], content.ARCH[1]
            keep.append(p)
        else:
            gx, gy, walk, arr = G[p['id']]
            p['x'], p['y'] = round(gx, 2), round(gy, 2)
            p['walk'] = list(walk)
            keep.append(p)
    zone['portals'] = keep


def aim_seams(world, zone, G):
    """Both seam portals of each seam stand where the roads cross (the seam road pass weighs the portals' points, and quest arrows aim at them): on the border at the column where the
    approved neighbour's road ends."""
    out = {}
    for gid, other in (('canopy_jungle_gate', TANGLE), ('canopy_lapis_gate', LAPIS)):
        mine = next(p for p in zone['portals'] if p.get('seam') and p['to'] == other)
        theirs = next(p for p in world['zones'][other - 1]['portals'] if p.get('seam') and p['to'] == ZONE)
        gx, gy, walk, arr = G[gid]
        sh = mine['seam']['shift']
        mine['x'], mine['y'], mine['tx'], mine['ty'] = round(gx, 2), round(gy, 2), round(gx + sh[0], 2), round(gy + sh[1], 2)
        theirs['x'], theirs['y'], theirs['tx'], theirs['ty'] = mine['tx'], mine['ty'], mine['x'], mine['y']
        out[gid] = (mine['x'], mine['y'])
    return out


def link_travel(world):
    """Add (never strip) the Spark links across every portal into or out of the Veyrroot, both ways, as compact_atlas.sync_travel_links does."""
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


def add_elite_choices(zone):
    from late_quests import CLASSES, SLOTS, gear
    for q in zone['quests']:
        if q['id'] in ('veyr_queen', 'veyr_colossus'):
            q['rewardChoices'] = {cls: [gear(q['level'], slot, cls, 'rare') for slot in SLOTS] for cls in CLASSES}


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    G = gates(F, zone)
    restore_and_shift(zone, old, G)
    aim_seams(world, zone, G)
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn (zone_shapes_migrate.py): the zone was rebuilt
    d = Veyrroot(zone, old)
    objects = d.build()
    solid = d.solid_mask(objects)
    seen = d.reachable(solid, (int(SPAWN[0]), int(SPAWN[1])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    d.late_dropped = d.late_moved = 0
    late = late_targets(zone, 20)
    if late:      # Sunward Vale's seam (2026-11-09) replaced a rim gate: only the spawns within 7 tiles of it and the loose scenery within 2.5 go, and the art-less objects within 20 step back (below)
        for t in late:
            d.late_dropped += drop_near_seam(zone, d, t)
        loose = [o for o in objects if o.get('layout') == d.TAG and o['kind'] != 'void' and d.seam_late[min(max(int(o['y']), 0), d.n - 1), min(max(int(o['x']), 0), d.n - 1)] < 2.5]
        objects = [o for o in objects if o not in loose]
        d.late_dropped += len(loose)
    zone['objects'] = objects
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in road] for road in d.ROADLIST]
    zone['atlasPaths'] = []
    zone['levels'] = [80, 84]
    seamed = {p['id'] for p in zone['portals'] if p.get('seam')}
    zone['exitRoutes'] = [dict(portal=g, points=[[round(gx, 2), round(gy, 2)], [round(arr[0], 2), round(arr[1], 2)]]) for g, (gx, gy, walk, arr) in G.items() if g not in seamed]
    arch = next(p for p in zone['portals'] if p['id'] == 'canopy_hollow_gate')
    zone['exitRoutes'].append(dict(portal='canopy_hollow_gate', points=[[content.ARCH[0], content.ARCH[1]], [content.ARCH_ARRIVAL[0], content.ARCH_ARRIVAL[1]]]))
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(world, zone, HAM, old)
    add_elite_choices(zone)
    for t in late:      # after the people stand in their final places: the art-less objects within 20 tiles of Sunward Vale's seam step back (see greenmeadow_design.step_back_artless)
        d.late_moved += step_back_artless(zone, zone['objects'], d, t)
    # every crossing that arrives here follows the new frame: Sunward's gate and Heartwood's way back (the two seams carry their own shift)
    arrivals = {'path_20_23': G['path_23_20'][3], 'hollow_canopy_gate': content.ARCH_ARRIVAL}
    found = set()
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals and not p.get('seam'):
                p['tx'], p['ty'] = round(arrivals[p['id']][0], 2), round(arrivals[p['id']][1], 2)
                found.add(p['id'])
    link_travel(world)
    zones_ = [world] + world['zones']
    masters = {n['id']: n for z in zones_[:47] for n in z.get('npcs', []) if n.get('travelStop')}
    for n in zones_[ZONE].get('npcs', []):
        if n.get('travelStop'):
            for other in n['travelLinks']:
                assert other in masters and n['id'] in masters[other]['travelLinks'], f"Spark link {n['id']} -> {other} is not reciprocal"
    if write:
        content.record_mailboxes(zone, HAM, ROOT / 'world/mailboxes.txt')
    problems = check(world, zone, d, solid, seen, G, found)
    stats = dict(short=d.short, objects=len([o for o in objects if o['kind'] != 'void']), spawns=len(zone['slimes']), land=int(d.floor.sum()), reachable=int(seen.sum()),
                 quests=len(zone['quests']), npcs=len(zone['npcs']),
                 kinds={k: sum(1 for o in objects if o['kind'] == k) for k in ('vr_canopy_tree', 'vr_fernbank', 'vr_amber_bloom', 'vr_moss_stone', 'buttress_root', 'hanging_pod', 'leaf_lantern', 'epiphyte_garden')})
    if problems:
        if os.environ.get('VEYR_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return d, stats


ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')


def check(world, zone, d, solid, seen, G, found):
    problems = []
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    if not (lost < open_cells.sum() * .03):
        problems.append(f'{lost} open cells are cut off from the spawn')
    for t in zone['slimes']:
        if not d.floor[int(t['y']), int(t['x'])]:
            problems.append(f'spawn off land {t}')
        if not seen[int(t['y']), int(t['x'])]:
            problems.append(f'unreachable spawn {t}')
        if t.get('layout') == d.TAG and d.seam[int(t['y']), int(t['x'])] <= SEAM_SPAWN:
            problems.append(f'spawn within {SEAM_SPAWN:.0f} tiles of a seam {t}')
    for n in zone['npcs']:
        if not seen[int(n['y']), int(n['x'])]:
            problems.append(f"unreachable npc {n['id']} at {n['x']},{n['y']}")
        if d.seam[int(n['y']), int(n['x'])] < SEAM_PEOPLE:
            problems.append(f"npc {n['id']} stands within {SEAM_PEOPLE:.0f} tiles of a seam (a plain seam draws no people)")
    for o in zone['objects']:
        if o['kind'] in ARTLESS and d.seam[int(o['y']), int(o['x'])] < SEAM_PEOPLE:
            problems.append(f"art-less {o['kind']} within {SEAM_PEOPLE:.0f} tiles of a seam at {o['x']},{o['y']}")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"unreachable place {p['id']}")
        if not d.floor[int(p['y']), int(p['x'])]:
            problems.append(f"place {p['id']} off land")
    for g, (gx, gy, walk, arr) in G.items():
        if not seen[int(arr[1]), int(arr[0])]:
            problems.append(f'gate cut off {g}')
    sun = G['path_23_20']
    if not seen[int(sun[1] - sun[2][1] * 3), int(sun[0] - sun[2][0] * 3)]:
        problems.append('Sunward gate is blocked from the inside')
    arch = next(q for q in zone['portals'] if q['id'] == 'canopy_hollow_gate')
    if not seen[int(content.ARCH_ARRIVAL[1]), int(content.ARCH_ARRIVAL[0])]:
        problems.append('the Hollow Arch arrival is cut off')
    for need in ('path_20_23', 'hollow_canopy_gate'):
        if need not in found and not is_seam_portal(world, need):
            problems.append(f'no incoming portal {need} found to re-aim')
    # an elite stands clear of everything a player walks to: awareness plus 3 tiles from every road, place and person, and from every hub and gate
    walked = [(q, 'road') for road in d.ROADLIST for q in dense_points(road)]
    walked += [((q['x'], q['y']), f"place {q['id']}") for q in zone['places']] + [((n['x'], n['y']), f"npc {n['id']}") for n in zone['npcs']]
    walked += [((q['x'], q['y']), f"portal {q['id']}") for q in zone['portals']]
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
        if not d.floor[int(ey), int(ex)]:
            problems.append(f'{kind} stands off the land')
    if sum(d.short.values()) > 12:
        problems.append(f'regions short of spawns: {d.short}')
    for p in zone['places']:
        if p.get('waves') and d.road[int(p['y']), int(p['x'])] < 4:
            problems.append(f"hold circle {p['id']} stands on a road")
    for k, x, y, tag in content.AMBUSH:
        if d.road[int(y), int(x)] < 3.4 or not d.floor[int(y), int(x)] or not seen[int(y), int(x)]:
            problems.append(f'ambush sleeper {tag} at {x},{y} stands on a road or off the land')
    bad = set()
    for road in d.ROADLIST + [r['points'] for r in zone['exitRoutes']]:
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                if not d.floor[int(y), int(x)]:
                    problems.append(f'road leaves the land at {x:.0f},{y:.0f}')
                if solid[int(y), int(x)]:             # no exemption inside a camp: a road never runs through a tent, a fire or a stone there either (tests/seam-roads.py)
                    bad.add((int(x), int(y)))
    if bad:
        problems.append(f'something stands on the road at {sorted(bad)[:12]}')
    return problems


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    T = zone['shape']['T']
    s = 1758 / 2048
    atlas = Image.open(ROOT / 'client/assets/world-atlas-painted.png').convert('RGB')
    x0, y0 = int(round(T[0] * s)), int(round(T[1] * s))
    bg = atlas.crop((x0, y0, x0 + int(n * s), y0 + int(n * s))).resize((n * scale, n * scale), Image.LANCZOS)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (20, 30, 20)), .35)
    pal = {1: (40, 130, 80), 2: (150, 110, 60), 3: (200, 170, 70), 4: (235, 215, 150), 5: (230, 150, 40), 6: (130, 90, 60), 7: (90, 190, 90), 8: (20, 70, 50), 9: (60, 190, 170)}
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
    col = {'vr_canopy_tree': (30, 110, 60), 'vr_fernbank': (120, 200, 90), 'vr_amber_bloom': (255, 190, 60), 'vr_moss_stone': (140, 150, 130), 'buttress_root': (140, 100, 60),
           'hanging_pod': (150, 210, 120), 'leaf_lantern': (255, 240, 150), 'epiphyte_garden': (90, 190, 140), 'worldheart_trunk': (213, 174, 110)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1.5 if o['kind'] in ('vr_fernbank', 'vr_amber_bloom', 'leaf_lantern') else 1)
        c = col.get(o['kind'], (255, 200, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'mosslemur': (200, 220, 140), 'sapbeetle': (230, 170, 80), 'lanternhornet': (250, 240, 120), 'barkmimic': (200, 150, 110)}
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
        g.ellipse([p['x'] * scale - 6, p['y'] * scale - 6, p['x'] * scale + 6, p['y'] * scale + 6], outline=(255, 60, 60), width=3)
        g.text((p['x'] * scale + 8, p['y'] * scale - 6), p['name'], fill=(255, 120, 120), stroke_width=1, stroke_fill=(0, 0, 0))
    for kind, ex, ey in content.ELITES:
        g.ellipse([ex * scale - 8, ey * scale - 8, ex * scale + 8, ey * scale + 8], outline=(255, 0, 0), width=3)
        g.text((ex * scale + 10, ey * scale - 6), kind, fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    im.save(out)


def main():
    src = os.environ.get('VEYR_WORLD')       # a cached shaped world (JSON), else the current map
    world = json.loads(Path(src).read_text() if src else MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], d, sys.argv[2])


if __name__ == '__main__':
    main()
