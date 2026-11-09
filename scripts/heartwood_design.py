#!/usr/bin/env python3
"""Heartwood (zone 24) as the main city inside the world-tree, an authored map on the shapes pilot.

Owner request 2026-11-09: "remake and reshape heartwood. it should be the main city in the big tree. like a main city like skaldholm. people live in there." and "the buildings in
heartwood should be buildings that could be found inside a big tree". Heartwood has no outline on the atlas (it is nested inside the Veyrroot), so its floor is authored: the hollow of the
trunk, a disc of radius 98 on a 208 grid, black outside (`shapeFloor`, `void` collision, theme `heartwood`). The city is built round the Living Pith at its centre: three ring roads (radius 30,
58, 84) and eight spokes, the Great Axis from the Hollow Arch (south) to the door of the Seed Vault (north), six districts (Seed Court, Amberleaf Hollows, Sap Market, Loomrow, Hollowgate,
Greenrow), about 120 burl-pod homes and the services of a main city (bank, steward with the Arena, smith, healer, trader, inn, Meeting Stone, Spark master, mailbox). Every building is grown or
carved wood (client/heartwoodart.js), drawn isometrically.

Runs in `zone_shapes.py apply` after the Veyrroot's design. The old 96 square is saved once in `world/zone-shapes/preshape-24.txt` and every run rebuilds from it (the old people, places, the Seed
Vault door and every old quest keep their ids). `zone_shapes.unshape` does not touch it (it has no atlas outline): the sidecar is the source.

    python3 scripts/heartwood_design.py plan OUT.png      draw the plan (read only; VEYR_WORLD=<cached shaped world> to use a cache)
"""
import copy
import json
import math
import os
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import heartwood_content as content  # noqa: E402
from zone_shapes import erode, floor_rows, void_pieces  # noqa: E402
MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-24.txt'

ZONE, VEYRROOT, VAULT = 24, 23, 33
N = 208
C = (104.0, 104.0)
RF = 98.0                    # the floor: a disc of this radius
RIM = 5.5                    # nothing stands closer than this to the rim
SEED = 20261111
RINGS = (30, 58, 84)
GATE = (104.0, 189.5)        # the Hollow Arch's portal (south), in front of the opening of its free-standing arch: the way in from the Veyrroot
GATE_ARRIVAL = (104.0, 195.0)    # you arrive in front of the arch and walk round it into the city
DOOR = (104.0, 21.0)         # the Seed Vault's portal (north), in front of its door wall
DOOR_ARRIVAL = (104.0, 28.0)
SPAWN = (104.0, 170.0)

# civic buildings: kind, centre, width x depth (door on the +y wall); the front is where the person who works there stands
CIVIC = {
    'vault':    dict(kind='heartwood_vault', x=104, y=17, w=10, d=3, extra=dict(place='heart_seed_door', open=True)),
    'chapel':   dict(kind='seed_chapel', x=80, y=38, w=5.4, d=5.4),
    'library':  dict(kind='amber_library', x=140, y=44, w=8, d=6, extra=dict(label='Amber Library')),
    'inn':      dict(kind='heart_burl_tall', x=152, y=88, w=5.2, d=4.2, extra=dict(label='The Amber Cup')),
    'loom':     dict(kind='root_loom', x=146, y=156, w=5, d=3.4),
    'forge':    dict(kind='pith_forge', x=128, y=172, w=6, d=5),
    'carver':   dict(kind='heart_burl_tall', x=170, y=134, w=5.2, d=4.2, extra=dict(label="Rootwright's Hollow")),
    'watch':    dict(kind='heart_burl_tall', x=74, y=164, w=5.2, d=4.2, extra=dict(label='Watch House')),
    'steward':  dict(kind='heart_burl_tall', x=36, y=90, w=5.4, d=4.4, extra=dict(label="Steward's Hollow")),
    'bank':     dict(kind='heart_burl_tall', x=36, y=118, w=5.4, d=4.4, extra=dict(label='The Hollow Vault')),
    'infirmary': dict(kind='heart_burl_tall', x=46, y=140, w=5.2, d=4.2, extra=dict(label='Infirmary')),
}
STALLS = [(166, 96), (174, 96), (182, 96), (166, 112), (174, 112), (182, 112)]       # the Sap Market, either side of the east spoke

# where each person stands (x, y): in front of their building, on a road or beside the Living Pith
SPOTS = {
    'steward': (36, 95.5), 'banker': (36, 123.5), 'smith': (128, 176.5), 'healer': (46, 145.5), 'trader': (174, 99.5), 'inn': (152, 92.8), 'stone': (88.2, 172.5),
    'captain': (74, 169.2), 'gate_a': (98, 178.5), 'gate_b': (110, 178.5), 'lamplighter': (104, 90), 'weaver': (146, 161), 'logwarden': (68, 81), 'bellringer': (116, 46),
    'sorter': (94, 54), 'storyteller': (112, 112), 'baker': (178, 99.5), 'tapper': (96, 26), 'gardener': (60, 62), 'glassblower': (140, 49.5), 'courier': (104, 174), 'pilgrim': (112, 166),
    'kid_a': (96, 112), 'kid_b': (112, 96), 'kid_c': (98, 96), 'kid_d': (110, 114), 'archivist': (146, 49.5), 'carver': (170, 139.5), 'oracle': (104, 116), 'custodian': (96, 26),
    'mailbox': (118.5, 174.5), 'spark': (117, 171),
}
MEMORY = (92.0, 118.0)       # the Empty Seat's memory (old es_20_m): beside the Living Pith

# the six districts and the Living Pith by the angle of a point from the centre (degrees, y down: 0 east, 90 south)
REGIONS = ['The Living Pith', 'Seed Court', 'Amberleaf Hollows', 'Sap Market', 'Loomrow', 'Hollowgate', 'Greenrow']
HOME_COUNT = 130
HOME_ROWS = (37, 52, 65, 79, 44.5, 72, 89)
HOME_W, HOME_D = 4.6, 3.8


def region_of(x, y):
    dx, dy = x - C[0], y - C[1]
    if math.hypot(dx, dy) < 20:
        return 0
    a = math.degrees(math.atan2(dy, dx)) % 360
    for k, lo, hi in ((1, 247.5, 292.5), (2, 292.5, 337.5), (4, 22.5, 67.5), (5, 67.5, 112.5)):
        if lo <= a < hi:
            return k
    if a >= 337.5 or a < 22.5:
        return 3
    return 6


def ring_points(r, n=96, gap=None):
    """A ring road as a closed polyline; `gap` (degrees) leaves the ring open round the Hollow Arch in the south."""
    pts = [(C[0] + r * math.cos(i / n * math.tau), C[1] + r * math.sin(i / n * math.tau)) for i in range(n + 1)]
    if gap is None:
        return pts
    keep = [p for p in pts if abs(((math.degrees(math.atan2(p[1] - C[1], p[0] - C[0])) % 360) - 90 + 180) % 360 - 180) > gap]
    k = max(range(len(keep) - 1), key=lambda i: math.dist(keep[i], keep[i + 1]))
    return keep[k + 1:] + keep[1:k + 1]       # open at the widest step, so the polyline does not jump across the gap


def roads():
    out = [ring_points(r, gap=14 if r == 84 else None) for r in RINGS]
    for k in range(8):
        if k == 2:
            continue                     # south: the Great Axis below runs to the Hollow Arch instead
        a = k * math.pi / 4
        r0, r1 = 19, 84
        end = (C[0] + r1 * math.cos(a), C[1] + r1 * math.sin(a))
        out.append([(C[0] + r0 * math.cos(a), C[1] + r0 * math.sin(a)), end])
    out.append([(104, 122), (104, 181)])         # the Great Axis, south: Living Pith to the Hollow Arch
    out.append([(84, 185.5), (92, 190.5), (104, 192)])      # the two ends of the Rim Walk meet in front of the arch
    out.append([(124, 185.5), (116, 190.5), (104, 192)])
    out.append([(104, 86), (104, 28)])           # north: to the Seed Vault's door
    return [[(round(x, 2), round(y, 2)) for x, y in p] for p in out]


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def road_dist(p, rds):
    return min(seg_dist(p, a, b) for r in rds for a, b in zip(r, r[1:]))


class City:
    def __init__(self):
        self.ys, self.xs = np.mgrid[0:N, 0:N] + .5
        self.floor = np.hypot(self.xs - C[0], self.ys - C[1]) <= RF
        self.roads = roads()
        self.objects = []
        self.rects = []              # (x0, y0, x1, y1): everything that stands on the ground, for overlap tests
        self.rng = random.Random(SEED)
        self.homes = 0

    def inside(self, x, y, margin=RIM):
        return math.hypot(x - C[0], y - C[1]) <= RF - margin

    def rect_free(self, x, y, w, d, gap):
        x0, y0, x1, y1 = x - w / 2 - gap, y - d / 2 - gap, x + w / 2 + gap, y + d / 2 + gap
        return not any(x0 < b[2] and x1 > b[0] and y0 < b[3] and y1 > b[1] for b in self.rects)

    def put(self, kind, x, y, w=0, d=0, r=0, reserve=True, gap=0., **extra):
        o = dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r, v=extra.pop('v', self.rng.randrange(4)), **extra)
        if w:
            o['width'], o['depth'] = w, d
        o['layout'] = 'heartwood_design_v1'
        self.objects.append(o)
        if reserve:
            hw, hd = (w / 2, d / 2) if w else (max(r, .3), max(r, .3))
            self.rects.append((x - hw - gap, y - hd - gap, x + hw + gap, y + hd + gap))
        return o

    def build(self, places, spots):
        # the Living Pith, its lamps and a ring of benches
        self.put('heartwood_core', *C, r=0, reserve=False)
        self.rects.append((C[0] - 8, C[1] - 8, C[0] + 8, C[1] + 8))
        for i in range(12):
            a = i / 12 * math.tau + .1309
            x, y = C[0] + 21 * math.cos(a), C[1] + 21 * math.sin(a)
            self.put('heart_lamp', x, y, r=.3)
        for i in range(8):
            a = i / 8 * math.tau + .39
            self.put('root_bench', C[0] + 13 * math.cos(a), C[1] + 13 * math.sin(a), w=1.8, d=.6, r=0)
        # civic buildings
        for key, b in CIVIC.items():
            self.put(b['kind'], b['x'], b['y'], b['w'], b['d'], gap=2.2, **b.get('extra', {}))
        for x, y in STALLS:
            self.put('heart_stall', x, y, 3, 2, gap=1.2)
        # the Meeting Stone, the Hollow Arch and the Seed Vault's door
        self.put('meetingstone', 86.3, 170.6, r=1.7, gap=1.5)
        self.put('hollow_arch', GATE[0], GATE[1] - 3.0, w=6, d=2, gap=1.5)
        # the Dew Bell and the founders' burl
        self.put('heartwood_column', 118, 42, r=.5, gap=1.5)
        self.put('heart_burl_tall', 60, 76, HOME_W + .6, HOME_D + .4, v=2, label="The Founders' Burl", gap=2.0)
        # keep every place and person clear
        for p in places:
            self.rects.append((p['x'] - p.get('r', 4) - .5, p['y'] - p.get('r', 4) - .5, p['x'] + p.get('r', 4) + .5, p['y'] + p.get('r', 4) + .5))
        for sx, sy in spots.values():
            self.rects.append((sx - 1.6, sy - 1.6, sx + 1.6, sy + 1.6))
        for pt in (GATE, GATE_ARRIVAL, DOOR, DOOR_ARRIVAL, SPAWN):
            self.rects.append((pt[0] - 3, pt[1] - 3, pt[0] + 3, pt[1] + 3))
        self.homes_rows()
        self.decor()

    def homes_rows(self):
        cand = []
        for r in HOME_ROWS:
            n = int(math.tau * r / (HOME_W + 2.8))
            for i in range(n):
                a = (i + .5 * (HOME_ROWS.index(r) % 2)) / n * math.tau
                x, y = C[0] + r * math.cos(a), C[1] + r * math.sin(a)
                cand.append((r, x, y))
        cand.sort(key=lambda t: (HOME_ROWS.index(t[0]), t[1] * 7 % 5))      # row by row in HOME_ROWS order, a little shuffled along each
        for r, x, y in cand:
            if self.homes >= HOME_COUNT:
                break
            if not self.inside(x, y, RIM + 2):
                continue
            if road_dist((x, y), self.roads) < 5.0:
                continue
            if math.hypot(x - C[0], y - C[1]) < 24:
                continue
            if not self.rect_free(x, y, HOME_W, HOME_D, 1.3):
                continue
            tall = (self.homes % 5 == 3)
            self.put('heart_burl_tall' if tall else 'heart_burl', x, y, HOME_W + (.4 if tall else 0), HOME_D + (.3 if tall else 0), v=self.rng.randrange(4), gap=1.3)
            self.homes += 1

    def decor(self):
        # sap-lamps along the three rings, 2.4 tiles outside the road
        for r in RINGS:
            n = int(math.tau * r / 13)
            for i in range(n):
                a = i / n * math.tau + .07
                x, y = C[0] + (r + 2.6) * math.cos(a), C[1] + (r + 2.6) * math.sin(a)
                if self.inside(x, y) and self.rect_free(x, y, .6, .6, .6) and road_dist((x, y), self.roads) > 1.9:
                    self.put('heart_lamp', x, y, r=.3, gap=.4)
        # living columns where the spokes meet the middle ring
        for k in range(8):
            a = k * math.pi / 4 + math.pi / 8
            x, y = C[0] + 62 * math.cos(a), C[1] + 62 * math.sin(a)
            if self.rect_free(x, y, 1, 1, .6):
                self.put('heartwood_column', x, y, r=.65, gap=.6)
        # gardens of glow-caps and moss between the homes
        for kind, count, r in (('epiphyte_garden', 90, .25), ('leaf_lantern', 50, .12), ('hanging_pod', 24, .75)):
            placed = 0
            for _ in range(60000):
                if placed >= count:
                    break
                a, rr = self.rng.random() * math.tau, math.sqrt(self.rng.random()) * (RF - 8)
                x, y = C[0] + rr * math.cos(a), C[1] + rr * math.sin(a)
                if rr < 22 or road_dist((x, y), self.roads) < 3.0 or not self.rect_free(x, y, r * 2, r * 2, .9):
                    continue
                self.put(kind, x, y, r=r, gap=.5)
                placed += 1


def solid_mask(objects):
    solid = ~np.array([[True] * N] * N)
    ys, xs = np.mgrid[0:N, 0:N] + .5
    for o in objects:
        if o['kind'] == 'void':
            continue
        w, d = o.get('width', 0), o.get('depth', 0)
        if w and d:
            solid |= (abs(xs - o['x']) < w / 2 + .3) & (abs(ys - o['y']) < d / 2 + .3)
        elif o['r'] > 0:
            solid |= np.hypot(xs - o['x'], ys - o['y']) < o['r'] + .3
    return solid


def flood(solid, floor, start):
    seen = np.zeros((N, N), bool)
    q = deque([start])
    seen[start[1], start[0]] = True
    while q:
        x, y = q.popleft()
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < N and 0 <= b < N and floor[b, a] and not solid[b, a] and not seen[b, a]:
                seen[b, a] = True
                q.append((a, b))
    return seen


# ---- people, places, quests ----------------------------------------------------------------------------------------------
def places_in_frame(old):
    pts = {p['id']: dict(p) for p in content.PLACES}
    # the rings: points on each ring away from the spokes (22.5 degrees past a spoke), in the Greenrow side
    for pid, r in (('hw_ring_inner', 30), ('hw_ring_mid', 58), ('hw_ring_outer', 84)):
        a = math.radians(202.5)
        pts[pid].update(x=round(C[0] + r * math.cos(a), 1), y=round(C[1] + r * math.sin(a), 1))
    pts['hw_rim_walk'].update(x=round(C[0] + 84 * math.cos(math.pi / 4), 1), y=round(C[1] + 84 * math.sin(math.pi / 4), 1))
    pts['hw_bell'].update(x=121, y=47)
    pts['hw_founders'].update(x=60, y=82.5)
    pts['hw_d_gate'].update(x=104, y=160)
    pts['hw_d_green'].update(x=54, y=104 - 0)
    pts['hw_d_sap'].update(x=166, y=104)
    pts['hw_d_amber'].update(x=146, y=68)
    pts['heart_seed_door'].update(x=104, y=26)
    return list(pts.values())


def make_people(world, old, spots):
    z23 = world['zones'][VEYRROOT - 1]
    by23 = {n['id']: n for n in z23['npcs']}
    skald = {n['id']: n for n in world['zones'][3]['npcs']}
    import add_repair_offers, arena_quests, stat_reset_npcs
    bank = dict(id='bank', label='Open the bank', cost=0)
    offers = {
        'hw_steward': [dict(stat_reset_npcs.OFFER), dict(arena_quests.OFFER)],
        'banker_heartwood': [bank],
        'hw_smith': [copy.deepcopy(next(o for o in skald['city_smith']['offers'] if o['id'] == 'fitting')), dict(add_repair_offers.OFFER)],
        'hw_healer': copy.deepcopy(by23['heart_healer']['offers']),
        'hw_trader': copy.deepcopy(by23['heart_trader']['offers']),
        'hw_innkeeper': copy.deepcopy(skald['city_innkeeper']['offers']),
        'hw_stone': copy.deepcopy(by23['heart_stone']['offers']),
    }
    out = []
    for p, spot in content.PEOPLE:
        n = copy.deepcopy(p)
        if n.get('art') is None:
            n.pop('art', None)
        n['x'], n['y'] = spots[spot]
        n['offers'] = offers.get(n['id'], [])
        if n['id'] == 'hw_trader':
            n['buys'] = True
        out.append(n)
    hub = copy.deepcopy(by23['travel_veyrroot'])
    hub.update(id='travel_heartwood', x=spots['spark'][0], y=spots['spark'][1], travelStop=content.NAME, travelLinks=['travel_veyrroot'], name='Travel Master Fenn', role='Heartwood courier · Spark Travel')
    out.append(hub)
    return out


def design(world, write=False):
    zone = world['zones'][ZONE - 1]
    if not OLD.exists():
        OLD.write_text(json.dumps(zone, indent=1, ensure_ascii=False) + '\n')           # the old 96 square, saved once: every later run rebuilds from it
    old = json.loads(OLD.read_text())
    places = places_in_frame(old)
    spots = dict(SPOTS)
    for p in places:
        if p['id'] == 'heart_seed_door':
            p['x'], p['y'] = 104, 26
    city = City()
    city.build(places + [dict(id='es', x=MEMORY[0], y=MEMORY[1], r=3)], spots)
    people = make_people(world, old, spots)
    # the old people keep their ids; their words follow the new city
    old_npcs = []
    for n in copy.deepcopy(old['npcs']):
        if n['id'] in content.OLD_PEOPLE:
            n['x'], n['y'] = spots[content.OLD_PEOPLE[n['id']]]
            n.update(copy.deepcopy(content.NPC_UPDATES.get(n['id'], {})))
            old_npcs.append(n)
        else:
            raise AssertionError(f"unplaced old person {n['id']}")
    npcs = old_npcs + people
    voids = void_pieces(city.floor)
    objects = [o for o in city.objects] + voids
    # the zone
    zone.clear()
    import arena_quests
    arena = [arena_quests.quest('heart', 'hw_steward', lv) for lv in arena_quests.LEVELS]
    quests = copy.deepcopy(old['quests'])
    zone.update(name='Veyrroot Heartwood', theme='heartwood', tagline=content.TAGLINE, size=N, levels=[80, 80], spawn=dict(x=SPAWN[0], y=SPAWN[1]), objects=objects, slimes=[], npcs=npcs,
                places=[], quests=quests,
                city=dict(name=content.NAME, x0=4, x1=N - 4, y0=4, y1=N - 4, plaza=dict(x=C[0], y=C[1]), radius=18, entry=dict(x=GATE_ARRIVAL[0], y=GATE_ARRIVAL[1])),
                camps=[], futureInstance=dict(copy.deepcopy(old['futureInstance']), x=104, y=17),
                portals=[], exitRoutes=[], atlasPaths=[])
    for p in old['places']:
        if p['id'] == 'es_20_m':
            places.append(dict(p, x=MEMORY[0], y=MEMORY[1]))
    zone['places'] = places
    for p in old['portals']:
        p = dict(p)
        if p['id'] == 'hollow_canopy_gate':
            p.update(x=GATE[0], y=GATE[1])
        elif p['id'] == 'heart_seed_gate':
            p.update(x=DOOR[0], y=DOOR[1])
        else:
            raise AssertionError(f"unplaced old portal {p['id']}")
        zone['portals'].append(p)
    zone['paths'] = [[[round(a, 2), round(b, 2)] for a, b in r] for r in city.roads]
    zone['exitRoutes'] = [dict(portal='hollow_canopy_gate', points=[[GATE[0], GATE[1]], [GATE_ARRIVAL[0], GATE_ARRIVAL[1]]]), dict(portal='heart_seed_gate', points=[[DOOR[0], DOOR[1]], [DOOR_ARRIVAL[0], DOOR_ARRIVAL[1]]])]
    region = np.zeros((N, N), int)
    for y in range(N):
        for x in range(N):
            if city.floor[y, x]:
                region[y, x] = region_of(x + .5, y + .5)
    from greenmeadow_design import ground_spans
    zone['regions'] = dict(names=REGIONS, spans=ground_spans(region + 1, city.floor))
    zone['regionsFirst'] = True                 # the HUD names the district, not the city (client/field.js areaName)
    zone['shapeFloor'] = floor_rows(city.floor)
    zone['shapeEdge'] = [' ' * N for _ in range(N)]
    zone['shape'] = dict(rule='authored', k=1.0, offset=[0, 0], core=N, bbox=[196, 196], T=[0, 0], outline=[], edges=[], neighbours=[], placeAtSpawn=True)
    content.install_quests(zone, arena)
    # every crossing that arrives here follows the new frame: the arch's way in and the Seed Vault's ways out
    arrivals = {'canopy_hollow_gate': GATE_ARRIVAL, 'seed_vault_return': DOOR_ARRIVAL, 'seed_vault_exit': DOOR_ARRIVAL}
    found = set()
    for zi in range(len(world['zones'])):
        for p in world['zones'][zi]['portals']:
            if p['to'] == ZONE and p['id'] in arrivals:
                p['tx'], p['ty'] = arrivals[p['id']]
                found.add(p['id'])
    # the Spark network: Heartwood's master and the Rootfoot master link both ways
    for n in z23_npcs(world):
        if n['id'] == 'travel_veyrroot' and 'travel_heartwood' not in n['travelLinks']:
            n['travelLinks'].append('travel_heartwood')
    if write:
        record_mailboxes(zone, ROOT / 'world/mailboxes.txt')
    problems = check(world, zone, city, found)
    stats = dict(objects=len([o for o in objects if o['kind'] != 'void']), homes=city.homes, npcs=len(npcs), quests=len(zone['quests']), places=len(zone['places']), land=int(city.floor.sum()),
                 voids=len(voids))
    if problems:
        if os.environ.get('HEART_LAX'):
            print(len(problems), 'problems:', *problems[:40], sep='\n  ')
        else:
            raise AssertionError('\n'.join(problems[:40]))
    return city, stats


OLD_ARRIVALS = {'canopy_hollow_gate': (48, 80), 'seed_vault_return': (48, 22), 'seed_vault_exit': (48, 22)}


def unshape(world):
    """Put the old 96 square back (every sync-world starts with it, so the overlays and the Empty Seat see the layout they were written for): the zone from `preshape-24.txt` and the arrivals
    of the crossings that come here. The Veyrroot's own restore (zone_shapes.unshape) already brought back the arch's arrival."""
    zone = world['zones'][ZONE - 1]
    if not OLD.exists() or zone.get('shape', {}).get('rule') != 'authored':
        return False
    old = json.loads(OLD.read_text())
    zone.clear()
    zone.update(old)
    for z in world['zones']:
        for p in z['portals']:
            if p['to'] == ZONE and p['id'] in OLD_ARRIVALS:
                p['tx'], p['ty'] = OLD_ARRIVALS[p['id']]
        for n in z.get('npcs', []):
            if n['id'] == 'travel_veyrroot' and 'travel_heartwood' in n.get('travelLinks', []):
                n['travelLinks'].remove('travel_heartwood')
    return True


def z23_npcs(world):
    return world['zones'][VEYRROOT - 1]['npcs']


def record_mailboxes(zone, path):
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != ZONE]
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_24_veyrroot_heartwood')
    master = next(n for n in zone['npcs'] if n['id'] == 'travel_heartwood')
    directory.append(dict(id=box['id'], zone=ZONE, hub=content.NAME, x=box['x'], y=box['y'], anchor=dict(x=master['x'], y=master['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def check(world, zone, city, found):
    problems = []
    objects = zone['objects']
    solid = solid_mask(objects) | ~city.floor
    seen = flood(solid, city.floor, (int(SPAWN[0]), int(SPAWN[1])))
    for n in zone['npcs']:
        if not city.floor[int(n['y']), int(n['x'])]:
            problems.append(f"{n['id']} stands off the floor")
        elif not seen[int(n['y']), int(n['x'])]:
            problems.append(f"{n['id']} is cut off at {n['x']},{n['y']}")
    for p in zone['places']:
        r = int(p.get('r', 2) + 1)
        if not seen[max(int(p['y']) - r, 0):int(p['y']) + r + 1, max(int(p['x']) - r, 0):int(p['x']) + r + 1].any():
            problems.append(f"place {p['id']} is cut off")
        if not city.floor[int(p['y']), int(p['x'])]:
            problems.append(f"place {p['id']} is off the floor")
    for p in zone['portals']:
        if not seen[int(p['y']), int(p['x'])]:
            problems.append(f"portal {p['id']} is cut off")
    for need in ('canopy_hollow_gate', 'seed_vault_return', 'seed_vault_exit'):
        if need not in found:
            problems.append(f'no incoming portal {need} found to re-aim')
    for tx, ty in (GATE_ARRIVAL, DOOR_ARRIVAL, SPAWN):
        if not seen[int(ty), int(tx)]:
            problems.append(f'arrival {tx},{ty} is cut off')
    # open ground: almost everything reachable
    open_cells = city.floor & ~solid
    lost = int((open_cells & ~seen).sum())
    if lost > open_cells.sum() * .03:
        problems.append(f'{lost} open cells are cut off')
    # roads must not run through a building
    for road in city.roads:
        for a, b in zip(road, road[1:]):
            L = math.dist(a, b)
            for k in range(int(L) + 1):
                x, y = a[0] + (b[0] - a[0]) * k / max(L, 1), a[1] + (b[1] - a[1]) * k / max(L, 1)
                if city.floor[int(y), int(x)] and solid[int(y), int(x)]:
                    problems.append(f'something stands on the road at {x:.0f},{y:.0f}')
                    break
    homes = [o for o in objects if o['kind'] in ('heart_burl', 'heart_burl_tall') and not o.get('label')]
    if len(homes) < 100:
        problems.append(f'only {len(homes)} homes')
    ids = [n['id'] for n in zone['npcs']]
    if len(set(ids)) != len(ids):
        problems.append('duplicate person ids')
    for q in zone['quests']:
        if not any(n['id'] == q['npc'] for n in zone['npcs']):
            problems.append(f"quest {q['id']} is given by {q['npc']}, who is not here")
        for o in q['objectives']:
            if o['kind'] == 'talk' and not any(n['id'] == o['target'] for z in [world] + world['zones'] for n in z.get('npcs', [])):
                problems.append(f"quest {q['id']}: nobody called {o['target']}")
            if o['kind'] == 'visit' and not any(p['id'] == o['target'] for p in zone['places']):
                problems.append(f"quest {q['id']}: no place {o['target']}")
    # buildings stay on the floor and inside the rim
    for o in objects:
        if o['kind'] != 'void' and math.hypot(o['x'] - C[0], o['y'] - C[1]) > RF - 2.5:
            problems.append(f"{o['kind']} at {o['x']},{o['y']} is on the rim")
    return problems


def plan_picture(zone, city, out, scale=4):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (N * scale, N * scale), (20, 13, 7))
    g = ImageDraw.Draw(im)
    for y in range(0, N):
        for x in range(0, N):
            if city.floor[y, x]:
                g.rectangle([x * scale, y * scale, (x + 1) * scale, (y + 1) * scale], fill=(92, 66, 40) if (x + y) % 2 else (98, 72, 44))
    for r in zone['paths']:
        g.line([(x * scale, y * scale) for x, y in r], fill=(236, 206, 140), width=scale * 2)
    col = {'heart_burl': (176, 138, 90), 'heart_burl_tall': (210, 170, 110), 'heart_stall': (110, 190, 110), 'amber_library': (255, 200, 90), 'pith_forge': (255, 120, 50), 'root_loom': (230, 130, 200),
           'seed_chapel': (180, 220, 140), 'heartwood_vault': (255, 255, 160), 'hollow_arch': (255, 255, 255), 'heart_lamp': (255, 240, 150), 'epiphyte_garden': (90, 190, 140)}
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        w = o.get('width', 0) or max(o['r'] * 2, 1)
        d = o.get('depth', 0) or max(o['r'] * 2, 1)
        g.rectangle([(o['x'] - w / 2) * scale, (o['y'] - d / 2) * scale, (o['x'] + w / 2) * scale, (o['y'] + d / 2) * scale], fill=col.get(o['kind'], (150, 200, 150)))
    for n in zone['npcs']:
        g.ellipse([n['x'] * scale - 3, n['y'] * scale - 3, n['x'] * scale + 3, n['y'] * scale + 3], fill=(255, 60, 60))
    for p in zone['places']:
        g.text((p['x'] * scale, p['y'] * scale), '* ' + p['name'], fill=(120, 255, 160))
    for p in zone['portals']:
        g.ellipse([p['x'] * scale - 7, p['y'] * scale - 7, p['x'] * scale + 7, p['y'] * scale + 7], outline=(255, 60, 60), width=3)
    im.save(out)


def main():
    src = os.environ.get('VEYR_WORLD')
    world = json.loads(Path(src).read_text() if src else MAP.read_text())
    city, stats = design(world)
    print(stats)
    if len(sys.argv) > 2 and sys.argv[1] == 'plan':
        plan_picture(world['zones'][ZONE - 1], city, sys.argv[2])


if __name__ == '__main__':
    main()
