#!/usr/bin/env python3
"""The Emberfall Crags as an authored map (zone 1 of the shapes pilot): no filler land, the whole outline used.

Runs in `zone_shapes.py apply` after the seams, the Skaldholm vault and the wall exist, so the outline, the borders and every crossing
stay exactly as they were. It replaces all loose scenery, every spawn and the trails with the plan below, traced from the owner's
painted atlas (client/assets/world-atlas-painted.png; tile = painted px * 2048/1758 - shape.T): four lava rivers stepping the land
into terraces, the snow-capped peaks, the pale roads along the ledges, the fire pit in the south and the cut quarry block in the south-west.

Fixed, never touched: Cinderwatch Camp and its people, the spawn point, the Ember Grave Cross and its sleeper, the Empty Seat circle,
the seam portals, the gates, the vault, the wall, the void.

    python3 scripts/crags_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import crags_content as content  # noqa: E402
from greenmeadow_design import Designer, Grid, fbm, ground_spans, seg_field  # noqa: E402
MAP = ROOT / 'world/map.txt'

# ---- the plan -------------------------------------------------------------------------------------------------------
REGIONS = {
    'shelf':    dict(name='The Cinderwatch Shelf', seeds=[(156, 222), (118, 218), (200, 222), (235, 228)]),
    'flats':    dict(name='The Sunpit Flats', seeds=[(186, 275), (172, 320), (205, 300), (150, 262)]),
    'quarry':   dict(name='The Anvil Quarries', seeds=[(122, 300), (100, 322), (128, 278), (90, 290)]),
    'wallfoot': dict(name='The Wallfoot', seeds=[(30, 240), (35, 300), (60, 270), (60, 225)]),
    'slopes':   dict(name='The Red Slopes', seeds=[(262, 285), (300, 272), (250, 320), (335, 240), (290, 245)]),
    'reach':    dict(name='The Hearth Reach', seeds=[(305, 200), (325, 160), (300, 150), (270, 195)]),
    'horned':   dict(name='The Horned Terrace', seeds=[(235, 165), (260, 160), (225, 185)]),
    'steps':    dict(name='The Long Steps', seeds=[(60, 165), (105, 155), (155, 165), (190, 165), (120, 170)]),
    'highfire': dict(name='Highfire Ridge', seeds=[(70, 92), (115, 95), (165, 100), (140, 110)]),
    'crown':    dict(name='The Ashen Crown', seeds=[(90, 40), (140, 35), (60, 62), (160, 55)]),
    'spurs':    dict(name='The Steaming Spurs', seeds=[(30, 110), (30, 150), (22, 180)]),
    'glass':    dict(name='The Glass Barrens', seeds=[(245, 110), (300, 112), (328, 125)]),
}

ROADS = [
    # the Long Terrace, the pale road of the painting, from the west pass to the Orrery gate
    [(92, 240), (125, 234), (159, 228), (210, 228), (259, 229), (276, 212), (285, 190), (305, 186), (324.5, 183.5), (342.5, 183.5)],
    [(156, 213), (156, 228)],
    # north from the camp, over the third river, to the Steps road
    [(156, 198), (157, 176), (154, 150)],
    # the Steps road, under the second river
    [(52, 165), (102, 162), (154, 150), (197, 152), (232, 166), (262, 176), (285, 190)],
    # the west pass: Terrace to Steps round the head of the fourth river, over the third
    [(92, 240), (70, 222), (52, 205), (52, 165)],
    # the Spurs road along the glacier side
    [(52, 165), (34, 150), (28, 125), (40, 100), (66, 92), (89, 89)],
    # up over the second river to Highfire Ridge, then north to the Wyrdwood gate
    [(102, 162), (100, 140), (103, 116), (95, 100), (89, 89), (92, 70), (89.5, 53.5), (89.5, 35.5)],
    # Highfire road, to Nacrehold
    [(89, 89), (119, 103), (150, 100), (192, 102), (207.5, 104), (207.5, 100.5), (206.5, 100.5), (206.5, 94.5)],
    # Ashford's ford
    [(197, 152), (197, 132), (192, 102)],
    # north again to the Bifrost gate, over the first river
    [(150, 100), (150, 72), (153, 50), (156.5, 29.5), (156.5, 20.5), (154.5, 20.5), (154.5, 13.5)],
    # the Glass Barrens road: Nacrehold's gate east along the border, and down over the ford to Lasthearth
    [(207.5, 104), (207.5, 111.5)],
    [(207.5, 104), (240, 110), (276, 110), (304, 112), (320, 111)],
    [(276, 110), (276, 150), (285, 190)],
    # the Skaldholm road and the Quarry way
    [(3.5, 277.5), (21.5, 277.5), (60, 276), (88, 275)],
    [(92, 240), (88, 275), (82, 312), (90, 328), (118, 336)],
    [(88, 275), (122, 284), (142, 288), (142, 312), (172, 324)],
    # the quarry floor
    [(122, 284), (112, 312)],
    # down from the Shelf over the fourth river to the Sunpit and the Slopes
    [(180, 228), (180, 244), (182, 262), (186, 284)],
    [(142, 288), (186, 284), (232, 288), (280, 285)],
    [(259, 229), (268, 246), (270, 262), (280, 285), (300, 282), (322, 262)],
    [(280, 285), (256, 304), (228, 318)],
]

# (control points, half width). Traced from the painting; each stops short of the seams, where nothing but this side draws lava.
RIVERS = [
    ([(50, 58), (70, 56), (95, 57), (109, 64), (132, 67), (160, 74)], 3.0),
    ([(66, 122), (92, 118), (132, 122), (165, 130), (202, 134), (228, 130), (275, 125), (345, 127)], 3.6),
    ([(32, 196), (59, 189), (105, 180), (145, 179), (179, 187), (212, 199), (246, 202)], 3.6),
    ([(95, 255), (125, 249), (165, 243), (205, 245), (245, 258), (272, 262), (312, 255), (332, 250)], 3.4),
]
PIT = (186, 306, 20, 15)   # the Sunpit: a lake of fire on the flats
FORD = 4.2                 # half width of a crossing

# Peaks of the painting (foot of the mountain), with their size.
PEAKS = [(80, 70, 6), (22, 76, 4), (139, 95, 5), (169, 72, 4.5), (77, 112, 6), (25, 122, 5), (44, 148, 5.5), (110, 139, 5.5), (35, 165, 4.5), (117, 177, 5),
         (19, 184, 4), (215, 145, 5), (234, 162, 5.5), (209, 185, 5), (252, 194, 4.5), (289, 200, 5), (68, 234, 5), (116, 235, 4.5), (160, 234, 4.5), (274, 248, 5),
         (75, 298, 4.5), (136, 312, 5), (134, 327, 4.5), (194, 292, 5), (262, 282, 6), (230, 319, 6), (320, 102, 4)]

HAMLETS = {
    'anvilrest':  dict(name='Anvilrest', x=118, y=290, hw=15, hh=10),
    'ashford':    dict(name='Ashford', x=197, y=152, hw=14, hh=10),
    'lasthearth': dict(name='Lasthearth', x=305, y=204, hw=14, hh=11),
}

# Hunting grounds: difficulty comes from which kind stands where (wisp 5, spider 7, wraith 8, golem 10). It climbs north and east from the Flats.
SPAWNS = {
    'shelf':    {'wisp': 26, 'spider': 4},
    'flats':    {'wisp': 30},
    'quarry':   {'wisp': 20, 'spider': 6},
    'wallfoot': {'wisp': 16, 'spider': 14},
    'slopes':   {'spider': 34, 'wisp': 8},
    'reach':    {'spider': 8, 'wraith': 18},
    'horned':   {'wraith': 20, 'golem': 4},
    'steps':    {'wraith': 26, 'spider': 10},
    'highfire': {'golem': 28, 'wraith': 6},
    'crown':    {'golem': 26},
    'spurs':    {'golem': 14, 'wraith': 10},
    'glass':    {'wraith': 12, 'golem': 8},
}

R = {'tree': .42, 'bush': .30, 'rock': .40, 'spire': .55, 'ew_basalt': 1.1, 'ew_vent': .8, 'ew_warmstone': 0, 'cairn_boulder': 1.3,
     'cairn_pebble': 0, 'bones': 0, 'crag_peak': 5}
GROUND = {'ash': 1, 'scree': 2, 'terrace': 3, 'black': 4, 'quarry': 5, 'crust': 6, 'steam': 7}


class Crags(Designer):
    TAG, SEED = 'crags_design_v1', 20261107

    def plan(self):
        return REGIONS, ROADS, R

    def scatter(self, kinds, count, where, gap=.65, road=2.6):
        # the zone is big: a thinner hand keeps it about the size of Greenmeadow's object list
        return super().scatter(kinds, int(count * .7), where, gap, road)

    def smooth(self, pts, step):
        """A Catmull-Rom curve through the control points, sampled about every `step` tiles."""
        p = [pts[0]] + list(pts) + [pts[-1]]
        out = []
        for i in range(1, len(p) - 2):
            a, b, c, d = (np.array(q, float) for q in p[i - 1:i + 3])
            n = max(int(np.linalg.norm(c - b) / step), 1)
            for k in range(n):
                t = k / n
                out.append(.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t ** 3))
        out.append(np.array(pts[-1], float))
        return out

    def lava_at(self, x, y, r):
        self.add('lava', x, y, r=round(float(r), 2), solid=False)
        self.grid.add(round(float(x), 2), round(float(y), 2), r)

    def river(self, pts, half):
        """Overlapping circles, with a ford wherever a road crosses: the channel is continuous terrain on the client."""
        line = self.smooth(pts, 1.5)
        total = len(line)
        gaps = 0
        run = 0
        for i, (x, y) in enumerate(line):
            end = min(i, total - 1 - i)
            taper = min(1, .35 + end / 9)
            wob = 1 + (fbm(self.noise, x, y, .09) - .5) * .7
            r = half * wob * taper
            ix, iy = int(y), int(x)
            if not self.floor[ix, iy]:
                continue
            if self.road[ix, iy] < FORD + r:
                run += 1
                continue
            if run:
                assert run < 14, f'a road runs along the river at {x:.0f},{y:.0f}: {run} samples'
                gaps += 1
                run = 0
            self.lava_at(x, y, r)
            self.block_disc(x, y, r + 1.4)
        return gaps

    def lake(self, cx, cy, rx, ry):
        step = 3.2
        y = cy - ry
        row = 0
        while y <= cy + ry:
            x = cx - rx + (step / 2 if row % 2 else 0)
            while x <= cx + rx:
                wob = 1 + (fbm(self.noise, x, y, .12) - .5) * .5
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= wob and self.road[int(y), int(x)] > 6:
                    self.lava_at(x, y, 3.1)
                x += step
            y += step * .866
            row += 1
        self.block_disc(cx, cy, max(rx, ry) + 2)

    def peak(self, x, y, size):
        # the painted spot, or the nearest ground that leaves the roads, the rivers and everything fixed clear of the mountain's foot
        clear = self.floor & (self.road > size + 2) & (self.lava > size + 1.5)
        near = ~self.blocked & clear & self.inner
        disc = np.hypot(self.xs - x, self.ys - y)
        for j, i in sorted(np.argwhere(near & (disc < 26)).tolist(), key=lambda c: disc[c[0], c[1]]):
            if not (self.blocked & (np.hypot(self.xs - i - .5, self.ys - j - .5) < size + 1)).any():
                x, y = i + .5, j + .5
                break
        else:
            raise AssertionError(f'no room for the peak at {x},{y}')
        self.add('crag_peak', x, y, r=size, v=0 if size <= 4.5 else 1 if size <= 5 else 2)
        self.block_disc(x, y, size + 1.2)

    def ring(self, centre, radius, n, kind, **extra):
        for k in range(n):
            a = k / n * math.tau + .3
            x, y = centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius
            if self.road[int(y), int(x)] > 2.4:
                self.add(kind, x, y, **extra)

    def build(self):
        w = self.w
        city = w['city']
        self.ground = np.zeros((self.n, self.n), np.uint8)
        self.block(city['x0'] - 3, city['y0'] - 3, city['x1'] + 3, city['y1'] + 3)
        kept = []
        for o in w['objects']:
            inside = city['x0'] - 1 <= o['x'] <= city['x1'] + 1 and city['y0'] - 1 <= o['y'] <= city['y1'] + 2.5
            if o['kind'] in ('void', 'rampart', 'tower') or (inside and o['kind'] not in ('lava',)):
                kept.append(o)
                if o['kind'] != 'void' and o['r'] + o.get('width', 0) > 0:
                    self.grid.add(o['x'], o['y'], max(o['r'], o.get('width', 0) / 2))
        for p in w['places'] + w['crosses']:
            self.block_disc(p['x'], p['y'], 5)
        for p in w['portals']:
            if not p.get('seam'):
                self.block_disc(p['x'], p['y'], 9)
                self.block_disc(p['x'] - p.get('walk', (0, 0))[0] * 8, p['y'] - p.get('walk', (0, 0))[1] * 8, 9)
        self.block_disc(w['spawn']['x'], w['spawn']['y'], 5)
        self.blocked |= self.seam < 2.5
        for _, x, y in content.ELITES:
            self.block_disc(x, y, 7)
        for _, x, y, _ in content.AMBUSH:
            self.block_disc(x, y, 2)
        for p in content.PLACES:
            self.block_disc(p['x'], p['y'], 3)
        for h in HAMLETS.values():
            self.block(h['x'] - h['hw'] - 2, h['y'] - h['hh'] - 2, h['x'] + h['hw'] + 2, h['y'] + h['hh'] + 2)

        fords = sum(self.river(*r) for r in RIVERS)
        self.fords = fords
        self.lake(*PIT)
        self.lava = np.full((self.n, self.n), 1e9)
        for o in self.objects:
            if o['kind'] == 'lava':
                r = int(o['r'] + 12)
                y0, y1, x0, x1 = max(int(o['y']) - r, 0), int(o['y']) + r, max(int(o['x']) - r, 0), int(o['x']) + r
                sub = np.hypot(self.xs[y0:y1, x0:x1] - o['x'], self.ys[y0:y1, x0:x1] - o['y']) - o['r']
                self.lava[y0:y1, x0:x1] = np.minimum(self.lava[y0:y1, x0:x1], sub)
        for x, y, s in PEAKS:
            self.peak(x, y, s)
        content.dress(self, HAMLETS)
        self.lay_ground()
        self.lay_regions()
        return kept + self.objects

    def lay_ground(self):
        """Ground classes beside plain ash. None within 16-30 tiles of a seam: the other side blends toward plain Crags ground."""
        G, g = GROUND, self.ground
        far = self.seam > 16 + fbm(self.noise, self.xs, self.ys, .09) * 14
        for name, cls in (('flats', 'ash'), ('slopes', 'scree'), ('wallfoot', 'black'), ('quarry', 'quarry'), ('spurs', 'steam'), ('glass', 'black'),
                          ('shelf', 'terrace'), ('steps', 'terrace'), ('horned', 'scree'), ('reach', 'terrace'), ('highfire', 'scree'), ('crown', 'ash')):
            g[self.mask(name) & far] = G[cls]
        rough = (fbm(self.noise, self.xs, self.ys, .14) - .5) * 5
        g[self.floor & far & (self.lava + rough < 5)] = G['crust']

    def lay_regions(self):
        dense = fbm(self.noise, self.xs + 200, self.ys + 300, .05)
        m = self.mask

        # The Shelf: burnt orchards of char trees round the camp, stone walls of a farm that gave up.
        self.scatter(['tree', 'tree', 'bush', 'tree'], 300, m('shelf') & (dense > .45), gap=1.1)
        self.scatter(['rock', 'rock', 'cairn_pebble', 'bush'], 420, m('shelf'), gap=1)
        self.scatter(['ew_warmstone'], 40, m('shelf'), gap=4)

        # The Sunpit Flats: pale ash, vents and spires round the fire pit.
        self.scatter(['ew_vent'], 26, m('flats') & (self.lava < 24), gap=6)
        self.scatter(['spire', 'spire', 'ew_basalt'], 110, m('flats'), gap=3)
        self.scatter(['rock', 'bones', 'cairn_pebble'], 420, m('flats'), gap=1.2)

        # The Anvil Quarries: a cut block of stone, walled by basalt columns, with spoil heaps and cut stone lying where it was left.
        for y in range(272, 335, 3):
            for x in (98, 150):
                if self.road[y, x] > 3:
                    self.add('ew_basalt', x + self.rng.uniform(-.4, .4), y + self.rng.uniform(-.4, .4), r=1.1)
        for x in range(100, 150, 3):
            for y in (334,):
                if self.road[y, x] > 3:
                    self.add('ew_basalt', x, y + self.rng.uniform(-.4, .4), r=1.1)
        forge = (104, 318)
        for dx, dy, k in ((-5, -2, 'cf_bellows'), (6, -3, 'cf_anvil'), (6, 3, 'cf_anvil')):
            self.add(k, forge[0] + dx, forge[1] + dy, r=.7)
        self.scatter(['cairn_boulder', 'rock', 'rock'], 300, m('quarry'), gap=1.4)
        self.scatter(['ew_basalt', 'spire'], 120, m('quarry'), gap=2.4)
        self.scatter(['cairn_pebble'], 220, m('quarry'), gap=.8)

        # The Wallfoot: black sand and blown thorn under Skaldholm's wall.
        self.scatter(['tree', 'bush', 'bush'], 240, m('wallfoot') & (dense > .4), gap=1.1)
        self.scatter(['rock', 'cairn_pebble', 'bones'], 420, m('wallfoot'), gap=1.1)

        # The Red Slopes: scree and spider-holes down to the Canopy, the Red Stair of cut steps.
        stair = (300, 282)
        self.block_disc(*stair, 8)
        self.ring(stair, 6, 8, 'ew_basalt', r=1.1)
        self.scatter(['spire', 'ew_basalt'], 240, m('slopes') & (dense > .46), gap=2)
        self.scatter(['rock', 'rock', 'bush', 'tree'], 620, m('slopes'), gap=1.1)

        # The Hearth Reach: the last burnt woods before the stars.
        self.scatter(['tree', 'tree', 'tree'], 280, m('reach') & (dense > .42), gap=1)
        self.scatter(['rock', 'bush', 'cairn_pebble'], 360, m('reach'), gap=1.1)

        # The Horned Terrace: peaks, spires and the Cinderlord's ring of basalt.
        self.ring((246, 160), 10, 12, 'ew_basalt', r=1.1)
        self.add('ew_vent', 246, 152, r=.8)
        self.scatter(['spire', 'spire', 'ew_basalt'], 150, m('horned'), gap=2)
        self.scatter(['rock', 'bones'], 260, m('horned'), gap=1.1)

        # The Long Steps: ledge after ledge, with the Giants' Forge in the middle.
        fx, fy = 112, 150
        self.block_disc(fx, fy, 9)
        self.add('cf_anvil', fx, fy, r=2.2, scale=3)
        self.add('cf_furnace', fx - 6, fy - 3, r=1.6)
        self.add('cf_furnace', fx + 6, fy + 3, r=1.6)
        self.ring((fx, fy), 8, 10, 'ew_basalt', r=1.1)
        self.scatter(['tree', 'bush', 'tree'], 240, m('steps') & (dense > .5), gap=1.2)
        self.scatter(['spire', 'ew_basalt'], 110, m('steps'), gap=3)
        self.scatter(['rock', 'rock', 'cairn_pebble'], 620, m('steps'), gap=1.1)

        # Highfire Ridge: bare rock and boulders the golems pass for, the dead beacon at the top.
        bx, by = 122, 92
        self.block_disc(bx, by, 8)
        self.add('cairn_signal', bx, by - 3, r=1.1)
        self.ring((bx, by), 6.5, 6, 'brazier', r=.4)
        self.scatter(['cairn_boulder'], 110, m('highfire'), gap=3.5)
        self.scatter(['rock', 'rock', 'spire'], 620, m('highfire'), gap=1.1)

        # The Ashen Crown: the old cone north of the last river, ash and basalt, Ashwing's roost of bones at the top.
        rx, ry = 112, 32
        self.ring((rx, ry), 7, 12, 'bones')
        self.scatter(['ew_basalt', 'spire'], 170, m('crown') & (dense > .44), gap=2)
        self.scatter(['rock', 'bones', 'tree'], 460, m('crown'), gap=1.2)

        # The Steaming Spurs: where the glacier comes down on hot rock. Vents and wet stone.
        vx, vy = 36, 140
        self.block_disc(vx, vy, 6)
        self.ring((vx, vy), 5, 6, 'ew_vent', r=.8)
        self.scatter(['ew_vent'], 26, m('spurs'), gap=7)
        self.scatter(['rock', 'rock', 'cairn_boulder', 'bush'], 430, m('spurs'), gap=1.2)

        # The Glass Barrens: black glass and sharp spires, where an old lava flow cooled on the sand.
        self.scatter(['spire', 'spire', 'ew_basalt'], 130, m('glass'), gap=2.2)
        self.scatter(['rock', 'cairn_pebble', 'bones'], 300, m('glass'), gap=1)

    # ---- spawns -----------------------------------------------------------------------------------------------------
    def spawns(self):
        rng, w = self.rng, self.w
        tags = {t for *_, t in content.AMBUSH}
        kept = [s for s in w['slimes'] if s.get('ambush') and s['ambush'] not in tags]
        out = list(kept) + [dict(kind=k, x=x, y=y, ambush=t) for k, x, y, t in content.AMBUSH]
        for k, x, y in content.ELITES:
            out.append({'x': x, 'y': y, 'kind': k})
        keep = self.blocked.copy()
        for h in HAMLETS.values():
            keep[max(h['y'] - h['hh'] - 10, 0):h['y'] + h['hh'] + 11, max(h['x'] - h['hw'] - 10, 0):h['x'] + h['hw'] + 11] = True
        city = w['city']
        keep[city['y0'] - 8:city['y1'] + 9, city['x0'] - 8:city['x1'] + 9] = True
        solid = Grid()
        for o in self.objects:
            solid.add(o['x'], o['y'], max(o['r'], (o.get('width', 0) + o.get('depth', 0)) / 4))
        for name, kinds in SPAWNS.items():
            pool = [k for k, c in kinds.items() for _ in range(c)]
            rng.shuffle(pool)
            pts = np.argwhere(self.mask(name) & self.inner & self.reach & ~keep & (self.road > 3.5) & (self.seam > 7))
            sep, placed, tries = 11.0, 0, 0
            while placed < len(pool) and tries < 40000:
                tries += 1
                if tries % 8000 == 0:
                    sep *= .85
                j, i = pts[rng.randrange(len(pts))]
                x, y = round(i + rng.random(), 2), round(j + rng.random(), 2)
                if any(math.hypot(x - s['x'], y - s['y']) < sep for s in out) or not solid.free(x, y, .8, .5):
                    continue
                out.append({'x': x, 'y': y, 'kind': pool[placed], 'layout': self.TAG})
                placed += 1
            assert placed == len(pool), f'{name}: placed {placed} of {len(pool)} spawns'
        # ordinary enemies first: code and tests take the zone's first spawn as a plain enemy
        ordinary = [t for t in out if t.get('layout') == self.TAG]
        ordinary.sort(key=lambda t: t['kind'] != 'wisp')
        return ordinary + [t for t in out if t.get('layout') != self.TAG]


def design(world, write=False):
    zone = world['zones'][0]
    d = Crags(zone)
    objects = d.build()
    solid = d.solid_mask(objects)
    s = zone['spawn']
    seen = d.reachable(solid, (int(s['x']), int(s['y'])))
    d.reach = seen
    zone['slimes'] = d.spawns()
    zone['objects'] = objects
    zone['paths'] = [[list(p) for p in road] for road in ROADS]
    zone['atlasPaths'] = []
    zone['groundSpans'] = ground_spans(d.ground, d.floor)
    zone['regions'] = dict(names=[r['name'] for r in REGIONS.values()], spans=ground_spans(d.region + 1, d.floor))
    content.install(zone, HAMLETS)
    if write:
        content.record_mailboxes(zone, HAMLETS, ROOT / 'world/mailboxes.txt')
    # checks: the map must hold together as a map
    open_cells = d.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    assert lost < open_cells.sum() * .01, f'{lost} open cells are cut off from the spawn'
    for t in zone['slimes']:
        assert d.floor[int(t['y']), int(t['x'])], f'spawn off land {t}'
        assert seen[int(t['y']), int(t['x'])], f'unreachable spawn {t}'
    prefix = ('anvil_', 'ford_', 'hearth_', 'travel_anvilrest', 'travel_ashford', 'travel_lasthearth', 'mailbox_1_anvilrest', 'mailbox_1_ashford', 'mailbox_1_lasthearth')
    for n in zone['npcs']:
        if n['id'].startswith(prefix):
            assert seen[int(n['y']), int(n['x'])], f"unreachable npc {n['id']}"
    for p in zone['places']:
        assert seen[int(p['y']), int(p['x'])], f"unreachable place {p['id']}"
    for p in zone['portals']:
        if not p.get('seam'):
            a = p['x'] - p.get('walk', (0, 0))[0] * 4, p['y'] - p.get('walk', (0, 0))[1] * 4
            assert seen[int(a[1]), int(a[0])], f"gate cut off {p['id']}"
    bad = set()
    for road in ROADS + [r['points'] for r in zone['exitRoutes']]:   # the painted exit markings are roads too
        for a, b in zip(road, road[1:]):
            for k in range(int(math.dist(a, b)) + 1):
                x = a[0] + (b[0] - a[0]) * k / max(math.dist(a, b), 1)
                y = a[1] + (b[1] - a[1]) * k / max(math.dist(a, b), 1)
                assert d.floor[int(y), int(x)], f'road leaves the land at {x:.0f},{y:.0f}'
                c = zone['city']
                inside = c['x0'] - 1 <= x <= c['x1'] + 1 and c['y0'] - 1 <= y <= c['y1'] + 3
                if not inside and solid[int(y), int(x)]:
                    bad.add((int(x), int(y)))
    assert not bad, f'something stands on the road at {sorted(bad)}'
    seam_lava = min((d.seam[int(o['y']), int(o['x'])] - o['r'] for o in objects if o['kind'] == 'lava'), default=99)
    assert seam_lava > 16, f'lava {seam_lava:.1f} tiles from a seam: the other side would not draw it'
    stats = dict(objects=len([o for o in objects if o['kind'] != 'void']), lava=len([o for o in objects if o['kind'] == 'lava']), fords=d.fords, spawns=len(zone['slimes']), lost=lost,
                 land=int(d.floor.sum()), reachable=int(seen.sum()), seam_lava=round(float(seam_lava), 1))
    return d, stats


def plan_picture(zone, d, out, scale=3):
    from PIL import Image, ImageDraw
    n = d.n
    pal = {0: (70, 54, 48), 1: (150, 140, 128), 2: (150, 80, 44), 3: (176, 112, 60), 4: (44, 40, 46), 5: (168, 150, 120), 6: (58, 40, 36), 7: (110, 120, 126)}
    a = np.zeros((n, n, 3), np.uint8)
    a[:] = (28, 44, 74)
    for k, c in pal.items():
        a[(d.ground == k) & d.floor] = c
    im = Image.fromarray(a).resize((n * scale, n * scale), Image.NEAREST)
    g = ImageDraw.Draw(im)
    for road in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in road], fill=(236, 214, 160), width=scale)
    col = {'lava': (245, 96, 32), 'rock': (120, 120, 124), 'cairn_boulder': (170, 170, 170), 'spire': (210, 210, 220), 'ew_basalt': (70, 70, 90), 'tree': (30, 24, 24), 'bush': (70, 60, 40),
           'ew_vent': (255, 200, 90), 'crag_peak': (235, 235, 245), 'bones': (225, 220, 200), 'cairn_pebble': (110, 110, 110)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        r = max(o['r'] * scale, 1)
        c = col.get(o['kind'], (255, 255, 255))
        g.ellipse([o['x'] * scale - r, o['y'] * scale - r, o['x'] * scale + r, o['y'] * scale + r], fill=c)
    kc = {'wisp': (255, 230, 70), 'spider': (80, 200, 255), 'wraith': (190, 130, 255), 'golem': (255, 70, 40)}
    for s in zone['slimes']:
        c = kc.get(s['kind'], (255, 255, 255))
        g.rectangle([s['x'] * scale - 2, s['y'] * scale - 2, s['x'] * scale + 2, s['y'] * scale + 2], fill=c, outline=(0, 0, 0))
    c = zone['city']
    g.rectangle([c['x0'] * scale, c['y0'] * scale, c['x1'] * scale, c['y1'] * scale], outline=(255, 255, 255), width=2)
    for h in HAMLETS.values():
        g.rectangle([(h['x'] - h['hw']) * scale, (h['y'] - h['hh']) * scale, (h['x'] + h['hw']) * scale, (h['y'] + h['hh']) * scale], outline=(255, 255, 255), width=2)
        g.text((h['x'] * scale - 20, h['y'] * scale), h['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for r in REGIONS.values():
        sx, sy = r['seeds'][0]
        g.text((sx * scale, sy * scale - 14), r['name'], fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for p in content.PLACES:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(120, 255, 180), stroke_width=2, stroke_fill=(0, 0, 0))
    im.save(out)


def main():
    world = json.loads(MAP.read_text())
    d, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][0], d, sys.argv[2])


if __name__ == '__main__':
    main()
