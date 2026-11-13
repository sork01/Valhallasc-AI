#!/usr/bin/env python3
"""Nacrehold as an authored city on its atlas outline (zone 9 of the shapes pilot): a shield-shaped city under a quiet tide.

Owner request 2026-11-07: "for pilot. reshape nacrehold. and remake the zone and quests to fit the new shape. no fillers. keep the portals/updrafts since this
place should be inaccessible without them. the only place it should have a seamless against is rans deep." Answers to the three questions asked: keep the 120
homes and six districts; the waterfront along the Deep is open the whole way; the four other gates stand on the rim facing their neighbour.

The outline (k = 1.0, grid 248, 38,365 tiles) is a rounded shield: the Deep along its whole straight north edge (~197 tiles), Bifrost Reach down the west side,
Astralhollow at the short north-east corner, the Orrery down the long east diagonal, the Crags round the south tip. The old 176-tile square cannot sit inside it, so the
city is REBUILT (`rebuild` in zone-shapes.txt): every id of the old city stays (people, places, quests, portals), every coordinate is new.

Runs in `zone_shapes.py apply` after the Deep's design. `designOnly` (no filler, the design places its own gates) + `rebuild` (the old layout is not moved) + `seamWith`
{9: [8]}: the Deep is the ONLY seam; the Crags, Bifrost, Astralhollow and the Orrery stay portals (Bifrost is also `gateOnly`).

The plan (Nacrehold's frame, north up):
- y 20-44: the Tideway Promenade, open water along the Deep: roads, reef gardens and nothing else. Buildings, people and festival decor keep 22 tiles from the border
  (a seam draws ground, scenery and enemies of the other side, not people or decor).
- y 46-86: the civic band: Lantern Gardens (west), the Memorial, the Drowned Cathedral and its court with the three wing doors (centre), the Palace of the Gentle Tide
  (east), the Pearl Archive.
- the Grand Axis (x 128) runs from the cathedral south through the fountain plaza (128, 108) to the Crags gate on the south tip; five avenues and seven streets on a 24-tile
  lattice; 120 homes on the lots nearest the plaza, in six districts (two above the plaza, two beside it and two below).
- gates on the rim facing each neighbour: the Astralhollow road (north-east), the Orrery avenue (east), the Crags gate (south), the Bifrost stair (west).

    python3 scripts/nacre_design.py plan OUT.png     draw the plan from the current world/map.txt (read only)
"""
import copy
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

MAP = ROOT / 'world/map.txt'
OLD = ROOT / 'world/zone-shapes/preshape-09.txt'
ZONE = 9
SEAM_CLEAR = 22.0          # people, buildings and decor keep this far from the Deep border
RIM = 4.0                  # nothing stands closer than this to the outline
AX = 128                   # the Grand Axis
XS = [56, 80, 104, 128, 152, 176, 200]          # avenues
YS = [60, 84, 108, 132, 156, 180, 204]          # streets
PLAZA, PLAZA_R = (128, 108), 18
SEED = 20261107 + ZONE
DISTRICTS = ['Rosecoral Quarter', 'Azure Shells', 'Violet Reach', 'Gilded Shoals', 'Jade Current', 'Amberwake']
HOME_NAMES = ['Rosecoral', 'Azure Shells', 'Violet Reach', 'Gilded Shoals', 'Jade Current', 'Amberwake']      # the labels the old homes carried
COLORS = ['#e9acc8', '#81d6cc', '#b2b4ef', '#eccb89', '#8dbedc', '#ecb395']
REGIONS = DISTRICTS + ['Tideway Promenade', 'Cathedral Court']


def district_of(x, y):
    """0..5: two above the plaza (y < 112), two beside it, two below; west/east of the Grand Axis."""
    return (0 if y < 112 else 2 if y < 158 else 4) + (1 if x > AX else 0)


class Plan:
    def __init__(self, zone):
        from greenmeadow_design import seg_field
        self.zone = zone
        n = self.n = zone['size']
        self.F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
        self.E = ndimage.distance_transform_edt(self.F)
        self.ys, self.xs = np.mgrid[0:n, 0:n] + .5
        self.D = np.full((n, n), 1e9)
        for e in zone['shape']['edges']:
            if e['kind'] == 'shared' and e['other'] == 8:
                self.D = np.minimum(self.D, seg_field(e['points'], self.xs, self.ys))
        self.objects, self.roads = [], []
        self.boxes = []             # (x, y, hw, hh) of everything solid, for placement tests
        self.rng = random.Random(SEED)

    def ok(self, x, y, edge=RIM, seam=0.):
        i, j = int(x), int(y)
        return 0 <= i < self.n and 0 <= j < self.n and self.F[j, i] and self.E[j, i] >= edge and self.D[j, i] >= seam

    def free(self, x, y, hw, hh, gap=0.):
        for bx, by, bw, bh in self.boxes:
            if abs(x - bx) < hw + bw + gap and abs(y - by) < hh + bh + gap:
                return False
        return True

    def add(self, kind, x, y, r=.4, solid=True, **extra):
        o = dict(kind=kind, x=round(float(x), 2), y=round(float(y), 2), r=r, v=extra.pop('v', 0))
        o.update(extra)
        self.objects.append(o)
        if solid:
            hw = o.get('width', 2 * r) / 2
            hh = o.get('depth', 2 * r) / 2
            self.boxes.append((o['x'], o['y'], hw, hh))
        return o

    def rim(self, x, y, dx, dy):
        while self.F[int(y + dy * .25), int(x + dx * .25)]:
            x += dx * .25
            y += dy * .25
        return x, y

    def run(self, axis, at, around, lo_edge=4.0, seam=0.):
        """The stretch of a street (axis 'x': vertical at x = at; 'y': horizontal at y = at) that holds floor, containing `around`."""
        def good(t):
            return self.ok(at, t, lo_edge, seam) if axis == 'x' else self.ok(t, at, lo_edge, seam)
        a = b = int(around)
        while good(a - 1):
            a -= 1
        while good(b + 1):
            b += 1
        return a, b + 1


# ---- the plan -------------------------------------------------------------------------------------------------------------------------
GATES = {       # portal id: (street point to walk out from, direction out)
    'nacre_astral_gate': ((200, 44), (1, 0)),
    'path_9_15': ((180, 132), (1, 0)),
    'path_9_1': ((AX, 200), (0, 1)),
    'path_9_7': ((60, 84), (-1, 0)),
}
CIVIC = dict(cathedral=(AX, 50), palace=(176, 52), garden=(68, 52), memorial=(98, 52), archive=(164, 76), inn=(84, 144),
             stall_a=(114, 138), stall_b=(142, 138), stone=(108, 57.5))


def build(zone, margin, old):
    p = Plan(zone)
    n = p.n
    sx = {x: p.run('x', x, 108) for x in XS}

    # ---- roads: ground only
    def vroad(x, y0, y1, t=1):
        w = 3.0 if t == 2 else 2.4
        p.roads.append(dict(x0=round(x - w, 2), x1=round(x + w, 2), y0=round(y0, 2), y1=round(y1, 2), t=t))

    def hroad(y, x0, x1, t=1):
        w = 3.0 if t == 2 else 2.4
        p.roads.append(dict(x0=round(x0, 2), x1=round(x1, 2), y0=round(y - w, 2), y1=round(y + w, 2), t=t))
    gates = {}
    for pid, ((gx, gy), (dx, dy)) in GATES.items():
        rx, ry = p.rim(gx, gy, dx, dy)
        gate = (round(rx - dx * 2.0, 1), round(ry - dy * 2.0, 1))
        arrival = (round(gate[0] - dx * 6.0, 1), round(gate[1] - dy * 6.0, 1))
        assert p.ok(arrival[0], arrival[1], 2.0), f'{pid}: the arrival {arrival} is off the floor'
        gates[pid] = dict(gate=gate, arrival=arrival, walk=[dx, dy], start=(gx, gy))
    for g in gates.values():            # the way from each gate to its arrival (and a little beyond) stays clear of scenery
        (x0, y0), (x1, y1) = g['gate'], g['arrival']
        for k in range(0, 9):
            p.boxes.append((x0 + (x1 - x0) * k / 8, y0 + (y1 - y0) * k / 8, 2.2, 2.2))
    for x in XS:
        y0, y1 = sx[x]
        top = 34 if x != AX else 66
        vroad(x, max(top, y0), gates['path_9_1']['gate'][1] if x == AX else y1, 2 if x == AX else 1)
    for y in YS + [44]:
        x0, x1 = p.run('y', y, AX)
        if y == 44:
            x1 = gates['nacre_astral_gate']['gate'][0]
        if y == 84:
            x0 = gates['path_9_7']['gate'][0]
        if y == 132:
            x1 = gates['path_9_15']['gate'][0]
        hroad(y, x0, x1)
    p.roads.append(dict(x=PLAZA[0], y=PLAZA[1], r=PLAZA_R, t=2))
    p.roads.append(dict(x0=100, x1=156, y0=53, y1=66, t=2))                     # the cathedral court
    p.roads.append(dict(x0=52, x1=224, y0=31, y1=37, t=2))                      # the promenade

    # ---- civic buildings (they come first: lots and scenery keep away from them)
    C = CIVIC
    p.add('nacrefountain', *PLAZA, 2.2)
    p.add('nacrecathedral', *C['cathedral'], 0.4, width=7, depth=6)
    p.add('nacrepalace', *C['palace'], 0.4, width=7, depth=5)
    p.add('nacrearchive', *C['archive'], 0.4, width=5, depth=4)
    p.add('nacregarden', *C['garden'], 2.2)
    p.add('nacrememorial', *C['memorial'], 1.2)
    p.add('meetingstone', *C['stone'], 1.7)
    p.add('nacreinn', *C['inn'], 0.4, width=5, depth=4)
    p.add('nacrestall', *C['stall_a'], 0.4, width=2.5, depth=1.8, color='#b2b4ef')
    p.add('nacrestall', *C['stall_b'], 0.4, width=2.5, depth=1.8, color='#eccb89')

    # ---- homes: the 120 lots nearest the plaza
    lots = []
    rows = sorted({y + d for y in YS for d in (-7.5, 7.5)})
    for y in rows:
        for x in range(32, 240, 8):
            if any(abs(x - X) < 6 for X in XS) or abs(y - PLAZA[1]) < 1:
                continue
            if y < 66 or not p.ok(x, y, 6.0, SEAM_CLEAR + 2):
                continue
            if math.hypot(x - PLAZA[0], y - PLAZA[1]) < PLAZA_R + 4:
                continue
            if abs(x - AX) < 6 and y > 60:
                continue
            if not p.free(x, y, 1.7, 1.3, 3.0):
                continue
            if any(abs(x - ((r['x0'] + r['x1']) / 2)) < (r['x1'] - r['x0']) / 2 + 2.6 and abs(y - (r['y0'] + r['y1']) / 2) < (r['y1'] - r['y0']) / 2 + 2.2
                   for r in p.roads if 'x0' in r):
                continue
            lots.append((math.hypot(x - PLAZA[0], (y - PLAZA[1]) * 1.15), x, y))
    lots.sort()
    chosen = [(x, y) for _, x, y in lots[:120]]
    assert len(chosen) == 120, f'only {len(lots)} lots'
    counts = {}
    for x, y in sorted(chosen, key=lambda q: (q[1], q[0])):
        d = district_of(x, y)
        counts[d] = counts.get(d, 0) + 1
        p.add('nacrehouse', x, y, 0.4, width=3.4, depth=2.6, color=COLORS[d], v_=p.rng.randrange(4), label=f'{HOME_NAMES[d]} {len([o for o in p.objects if o["kind"] == "nacrehouse"]) + 1}', sign='live')
    p.counts = counts

    # ---- lamps at street corners, reef round the rim and in the promenade gardens
    for y in YS:
        for x in XS:
            if math.hypot(x - PLAZA[0], y - PLAZA[1]) < 22 or not p.ok(x + 3.4, y - 3.4, 5.0, SEAM_CLEAR + 2):
                continue
            if p.free(x + 3.4, y - 3.4, .2, .2, 1.0):
                p.add('pearllamp', x + 3.4, y - 3.4, .18, v_=int(x + y) % 3)
    for g in gates.values():
        for sgn in (-1, 1):
            lx, ly = g['gate'][0] - g['walk'][1] * 3.0 * sgn, g['gate'][1] + g['walk'][0] * 3.0 * sgn
            if p.ok(lx, ly, 3.0):
                p.add('pearllamp', lx, ly, .18)
    ring = [(x, y) for y in range(n) for x in range(n) if p.F[y, x] and 3.2 <= p.E[y, x] < 4.2 and p.D[y, x] >= 14]
    p.rng.shuffle(ring)
    kept = []
    for x, y in ring:
        if all(math.hypot(x - a, y - b) >= 8 for a, b in kept) and p.free(x, y, .4, .4, 2.0):
            kept.append((x, y))
    for k, (x, y) in enumerate(sorted(kept)):
        p.add('kelp' if k % 2 else 'coral', x + .5, y + .5, .4 if k % 2 else .55, v_=p.rng.randrange(4))
    p.rim_reef = len(kept)
    garden = []
    for _ in range(4000):
        x, y = p.rng.uniform(40, 232), p.rng.uniform(22, 46)
        if not p.ok(x, y, 5.0, 14.0) or abs(y - 34) < 5 or any(math.hypot(x - a, y - b) < 9 for a, b in garden):
            continue
        garden.append((x, y))
    for k, (x, y) in enumerate(sorted(garden)):
        if p.free(x, y, .6, .6, 1.5):
            p.add('coral' if k % 3 else 'kelp', x, y, .55 if k % 3 else .4, v_=p.rng.randrange(4))
    # ---- reef parks: three coral gardens on the quiet rim, where no home stands (places for the gardener's new quest)
    parks = [(44, 168), (92, 216), (140, 216)]
    for cx, cy in parks:
        assert p.ok(cx, cy, 8.0) and p.free(cx, cy, 5, 5), f'reef park at ({cx}, {cy}) is not free'
    for cx, cy in parks:
        for k in range(9):
            a = k / 9 * math.tau
            r = 4.6 if k % 2 else 2.2
            p.add('coral' if k % 3 else 'kelp', cx + math.cos(a) * r, cy + math.sin(a) * r, .55 if k % 3 else .4, v_=p.rng.randrange(4))
    p.parks = parks
    p.gates = gates
    return p


# ---- the picture ----------------------------------------------------------------------------------------------------------------------
def picture(zone, out, scale=4):
    from PIL import Image, ImageDraw
    n = zone['size']
    F = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
    im = Image.new('RGB', (n * scale, n * scale), '#06151d')
    d = ImageDraw.Draw(im)
    for y in range(n):
        for x in range(n):
            if F[y, x]:
                d.rectangle([x * scale, y * scale, (x + 1) * scale, (y + 1) * scale], fill='#1d5560')
    for r in zone.get('roads', []):
        if 'x0' in r:
            d.rectangle([r['x0'] * scale, r['y0'] * scale, r['x1'] * scale, r['y1'] * scale], fill='#a5d9d5' if r['t'] == 1 else '#bde4df')
        else:
            d.ellipse([(r['x'] - r['r']) * scale, (r['y'] - r['r']) * scale, (r['x'] + r['r']) * scale, (r['y'] + r['r']) * scale], fill='#bde4df')
    for o in zone['objects']:
        if o['kind'] == 'void':
            continue
        w, h = o.get('width', o['r'] * 2), o.get('depth', o['r'] * 2)
        col = o.get('color', {'coral': '#e07a6a', 'kelp': '#3c9a5a', 'pearllamp': '#ffe698', 'nacrefountain': '#58a8d8', 'meetingstone': '#59d9ff'}.get(o['kind'], '#8a7a9a'))
        d.rectangle([(o['x'] - w / 2) * scale, (o['y'] - h / 2) * scale, (o['x'] + w / 2) * scale, (o['y'] + h / 2) * scale], fill=col)
    for p_ in zone['portals']:
        if p_.get('seam'):
            pts = [(a * scale, b * scale) for a, b in p_['seam']['points']]
            d.line(pts, fill='#ffd36a', width=3)
        else:
            d.ellipse([(p_['x'] - 2) * scale, (p_['y'] - 2) * scale, (p_['x'] + 2) * scale, (p_['y'] + 2) * scale], outline='#ffffff', width=2)
    for npc in zone.get('npcs', []):
        d.ellipse([(npc['x'] - 1) * scale, (npc['y'] - 1) * scale, (npc['x'] + 1) * scale, (npc['y'] + 1) * scale], fill='#ffe698')
    for pl in zone.get('places', []):
        d.ellipse([(pl['x'] - pl['r']) * scale, (pl['y'] - pl['r']) * scale, (pl['x'] + pl['r']) * scale, (pl['y'] + pl['r']) * scale], outline='#ff8a8a')
    im.save(out)


# ---- people, places, quests ---------------------------------------------------------------------------------------------------------------
def settle(p, x, y, hw=.7, gap=.6, seam=SEAM_CLEAR):
    """The free point nearest (x, y): on the floor, clear of every solid piece, `seam` tiles from the Deep border."""
    for ring in range(0, 14):
        for k in range(0, 1 if ring == 0 else 8 * ring):
            a = k / max(1, 8 * ring) * math.tau
            px, py = round(x + math.cos(a) * ring, 1), round(y + math.sin(a) * ring, 1)
            if p.ok(px, py, 3.0, seam) and p.free(px, py, hw, hw, gap):
                return px, py
    raise AssertionError(f'no free spot near ({x}, {y})')


OLD_SPOTS = {       # old id -> wanted spot in the new frame (nudged to free ground)
    'nacre_envoy': (122, 213), 'nacre_healer': (176, 62), 'nacre_trader': (144, 142), 'nacre_smith': (114, 142), 'nacre_archivist': (160, 80.5),
    'banker_nacrehold': (130.5, 105.5), 'nacre_gardener': (68, 62), 'nacre_singer': (136, 104), 'nacre_warden': (128, 59),
    'nacre_innkeeper': (84, 148.5), 'nacre_lamplighter': (188, 124), 'nacre_stone': (109.7, 59.2), 'travel_nacrehold': (134, 213),
    'mailbox_9_nacrehold': (137.5, 213.5),
}
DANCE = (125, 112)
SPAWN = (128, 217)


def new_npc(id_, name, role, x, y, female, dialogue):
    i = sum(map(ord, id_))
    return dict(id=id_, name=name, role=role, x=x, y=y, color=COLORS[i % 6], offers=[], buys=False,
                look=dict(species='merfolk', female=female, tail=COLORS[i % 6], skin=['#a4dbc9', '#abd4e4', '#cdbfea'][i % 3],
                          hair=['#243e62', '#ebdbbd', '#b96289', '#43827a'][i % 4], style='long' if female else 'short'), dialogue=dialogue)


def people(p, old):
    by = {n['id']: copy.deepcopy(n) for n in old['npcs']}
    out = []
    for id_, (x, y) in OLD_SPOTS.items():
        n = by.pop(id_)
        n['x'], n['y'] = settle(p, x, y) if id_ not in ('mailbox_9_nacrehold',) else (x, y)
        out.append(n)
    for id_ in [k for k in by if k.startswith('festival_dance_')]:
        n = by.pop(id_)
        n['x'], n['y'] = DANCE
        out.append(n)
    residents = [by.pop(k) for k in sorted(by) if k.startswith('nacre_resident_')]
    assert not by, f'old people not placed: {list(by)}'
    # quiet swimmers walk a block of the lattice each: four streets, a loop of 96 tiles
    blocks = []
    for X in XS[:-1]:
        for Y in YS[:-1]:
            pts = [(X, Y), (X + 24, Y), (X + 24, Y + 24), (X, Y + 24)]
            ok = True
            for a, b in zip(pts, pts[1:] + pts[:1]):
                for k in range(0, int(math.dist(a, b) * 2) + 1):
                    x = a[0] + (b[0] - a[0]) * k / max(1, int(math.dist(a, b) * 2))
                    y = a[1] + (b[1] - a[1]) * k / max(1, int(math.dist(a, b) * 2))
                    if not p.ok(x, y, 5.0, SEAM_CLEAR + 2) or not p.free(x, y, .35, .35, .4) or math.hypot(x - PLAZA[0], y - PLAZA[1]) < 5:
                        ok = False
                        break
                if not ok:
                    break
            if ok and Y >= 84:
                blocks.append(pts)
    assert len(blocks) >= len(residents), f'only {len(blocks)} walkable blocks for {len(residents)} swimmers'
    pick = [blocks[int(k * len(blocks) / len(residents))] for k in range(len(residents))]
    for n, pts in zip(residents, pick):
        n['route'] = [[float(a), float(b)] for a, b in pts]
        n['x'], n['y'] = n['route'][0]
        out.append(n)
    harbour = new_npc('nacre_harbourmaster', 'Harbour-Warden Selke Tideline', 'Mermaid · Warden of the Tideway', *settle(p, 116, 47.5), True,
                      'The Deep begins where the promenade stops: no gate, no door, only water. Keelhaven’s boats come in over that line without a bell, and on a still night the current carries the Shallows’ lanterns up to our reefs.')
    gate = new_npc('nacre_gatewarden', 'Gatekeeper Orsa Stillfin', 'Mermaid · Keeper of the five ways', *settle(p, 120, 205), True,
                   'Five ways into Nacrehold and not one lock. We are quiet because we are hard to find: you need a gate, an updraft or a boat. I keep a ledger of every crossing.')
    out += [harbour, gate]
    return out


def places(p, old, gates):
    by = {q['id']: q for q in old['places']}
    pos = dict(nacre_garden=(70, 58), nacre_sanctuary=(176, 60), nacre_archive=(164, 81), nacre_memorial=(98, 58), nacre_cathedral=(128, 59), es_09_m=(164, 81))
    houses = [o for o in p.objects if o['kind'] == 'nacrehouse']
    for d, key in enumerate(['rose', 'azure', 'violet', 'gold', 'mint', 'amber']):
        mine = [(o['x'], o['y']) for o in houses if district_of(o['x'], o['y']) == d]
        cx, cy = sum(a for a, _ in mine) / len(mine), sum(b for _, b in mine) / len(mine)
        pos['nacre_' + key] = settle(p, cx, cy, hw=1.0, gap=.8)
    out = []
    for id_, q in by.items():
        q = dict(q)
        q['x'], q['y'] = pos[id_]
        out.append(q)
    way = {'nacre_way_crags': ('the Crags Gate', 'path_9_1'), 'nacre_way_orrery': ('the Orrery Avenue', 'path_9_15'),
           'nacre_way_astral': ('the Astralhollow Road', 'nacre_astral_gate'), 'nacre_way_bifrost': ('the Bifrost Stair', 'path_9_7')}
    out.append(dict(id='nacre_tideway', name='the Tideway', x=128.0, y=34.0, r=4))
    out.append(dict(id='nacre_plaza', name='the Fountain Plaza', x=float(PLAZA[0]), y=float(PLAZA[1] + 8), r=5))
    for id_, (name, pid) in way.items():
        g = gates[pid]
        out.append(dict(id=id_, name=name, x=g['arrival'][0], y=g['arrival'][1], r=3))
    for id_, name, (x, y) in [('nacre_reef_west', 'the West Reef', p.parks[0]), ('nacre_reef_south', 'the South Reef', p.parks[1]), ('nacre_reef_east', 'the Road Reef', p.parks[2])]:
        out.append(dict(id=id_, name=name, x=float(x), y=float(y), r=5))
    return out


LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
GOLD = {35: 1250, 36: 1350, 37: 1500, 38: 1650}


def quest(id_, title, npc, level, desc, objectives, requires):
    from quest_gear_rewards import reward_for
    q = dict(id=id_, title=title, npc=npc, description=desc, objectives=[dict(kind=k, target=t, label=l, count=1) for k, t, l in objectives],
             level=level, rewardXp=LEVELS[level - 1] // 10, rewardGold=GOLD[level], requires=requires, repeatable=False)
    r = reward_for(id_)
    if r:
        q['rewardItem'] = r
    return q


NEW_QUESTS = {'nacre_tideway', 'nacre_five_ways', 'nacre_rim_gardens', 'nacre_grand_axis'}


def quests(old):
    new = [
        quest('nacre_tideway', 'The Open Water', 'nacre_harbourmaster', 36,
              'Nacrehold has no sea-gate on its north side: the promenade simply runs out into the Deep. Walk out to the Tideway, past the reef gardens, look across at the lantern-lit Shallows, and tell Selke what the tide is doing.',
              [('visit', 'nacre_tideway', 'Walk out to the Tideway')], 'nacre_welcome'),
        quest('nacre_five_ways', 'Five Ways In', 'nacre_gatewarden', 37,
              'Every road in Nacrehold ends at a doorway to somewhere else. Orsa keeps a ledger of five: the open water of the Tideway in the north, the Astralhollow road in the north-east, the Orrery avenue in the east, the Crags gate on the south tip and the Bifrost stair in the west. Stand at each.',
              [('visit', 'nacre_tideway', 'Stand at the Tideway'), ('visit', 'nacre_way_astral', 'Stand at the Astralhollow Road'), ('visit', 'nacre_way_orrery', 'Stand at the Orrery Avenue'),
               ('visit', 'nacre_way_crags', 'Stand at the Crags Gate'), ('visit', 'nacre_way_bifrost', 'Stand at the Bifrost Stair')], 'nacre_welcome'),
        quest('nacre_rim_gardens', 'The Quiet Reefs', 'nacre_gardener', 38,
              'Pelar tends three reef gardens that no street crosses: one on the west shore, one on the south shore and one beside the Crags road. Visit each and take only memories.',
              [('visit', 'nacre_reef_west', 'Visit the West Reef'), ('visit', 'nacre_reef_south', 'Visit the South Reef'), ('visit', 'nacre_reef_east', 'Visit the Road Reef')], 'nacre_gardens'),
        quest('nacre_grand_axis', 'The Grand Axis', 'nacre_envoy', 35,
              'Lyris says every visitor walks the Grand Axis once: north from the Crags gate, round the humming fountain and on to the court before the Drowned Cathedral. Do it slowly, then tell her what you saw.',
              [('visit', 'nacre_plaza', 'Stop at the Fountain Plaza'), ('visit', 'nacre_cathedral', 'Reach the Cathedral court')], 'nacre_welcome'),
    ]
    return copy.deepcopy(old['quests']) + new


def decor(p, old, npcs, portals):
    """The five seasons' city dressing on the new streets (the old generators ran on the square, before the zone was shaped)."""
    road_lines = [r for r in p.roads if 'x0' in r]

    def street_centre(x, y):
        for r in road_lines:
            dx, dy = r['x1'] - r['x0'], r['y1'] - r['y0']
            if dy > dx * 3 and abs(x - (r['x0'] + r['x1']) / 2) < 1.4 and r['y0'] - 1 < y < r['y1'] + 1:
                return True
            if dx > dy * 3 and abs(y - (r['y0'] + r['y1']) / 2) < 1.4 and r['x0'] - 1 < x < r['x1'] + 1:
                return True
        return False
    solid = [o for o in p.objects if o['kind'] not in ('void',)]

    def inside(x, y):
        return p.ok(x, y, 3.0, SEAM_CLEAR)
    base = []
    accent = old['seasonDecor'][0]['color']

    def safe(x, y):
        if not inside(x, y):
            return False
        if any((abs(x - o['x']) < o['width'] / 2 + .7 and abs(y - o['y']) < o['depth'] / 2 + .7) if o.get('width') else math.hypot(x - o['x'], y - o['y']) < o.get('r', 0) + .7 for o in solid):
            return False
        if any(math.hypot(x - n['x'], y - n['y']) < 1.6 for n in npcs):
            return False
        if any(math.hypot(x - q['x'], y - q['y']) < 6 for q in portals if not q.get('seam')):
            return False
        return not any(math.hypot(x - d['x'], y - d['y']) < 2.5 for d in base)

    def add(kind, x, y, z=0):
        base.append(dict(kind=kind, x=round(x, 2), y=round(y, 2), z=z, r=0, v=len(base) % 3, hub='Nacrehold', color=accent))
    houses = [o for o in solid if o.get('width') and o.get('depth') and o['kind'] not in ('rampart', 'wall', 'vaultwall', 'void', 'bridge')]
    for o in houses:
        x, y = o['x'], o['y'] + o['depth'] / 2 + .2
        if inside(x, y) and all(math.hypot(x - q['x'], y - q['y']) > 6 for q in portals if not q.get('seam')):
            add('festivalWreath' if len(base) % 2 else 'festivalWeb', x, y, 76 if o['kind'] != 'stall' else 52)
        for side in (-1, 1):
            x, y = o['x'] + side * (o['width'] / 2 + .95), o['y'] + o['depth'] / 2 + .8
            if safe(x, y):
                add('festivalPumpkins' if side < 0 else 'festivalCandles', x, y)
    step = 6.5
    x0, y0 = 6, 22
    for row in range(math.ceil((p.n - y0) / step)):
        for col in range(math.ceil((p.n - x0) / step)):
            x, y = x0 + 1.5 + col * step + (row % 2) * 1.2, y0 + 1.5 + row * step
            if safe(x, y):
                add(['festivalPumpkins', 'festivalLantern', 'festivalBunting', 'festivalCandles', 'festivalScarecrow'][(row * 3 + col) % 5], x, y)
    out = {'seasonDecor': base}
    seasons = {
        'christmasDecor': ('christmas', {'festivalPumpkins': 'christmasGifts', 'festivalLantern': 'christmasLantern', 'festivalCandles': 'christmasCandles', 'festivalWreath': 'christmasWreath',
                                         'festivalWeb': 'christmasGarland', 'festivalBunting': 'christmasLights', 'festivalScarecrow': 'christmasTree'}, 'christmasGrandTree'),
        'easterDecor': ('easter', {'festivalPumpkins': 'easterFlowers', 'festivalLantern': 'easterLantern', 'festivalCandles': 'easterCandles', 'festivalWreath': 'easterWreath',
                                   'festivalWeb': 'easterGarland', 'festivalBunting': 'easterLights', 'festivalScarecrow': 'easterEgg'}, 'easterGrandEgg'),
        'solsticeDecor': ('solstice', {'festivalPumpkins': 'solsticeFlowers', 'festivalLantern': 'solsticeLantern', 'festivalCandles': 'solsticeFlowers', 'festivalWreath': 'solsticeWreath',
                                       'festivalWeb': 'solsticeGarland', 'festivalBunting': 'solsticeLights', 'festivalScarecrow': 'solsticeBirch'}, None),
        'valentineDecor': ('valentine', {'festivalPumpkins': 'valentineRoses', 'festivalLantern': 'valentineLantern', 'festivalCandles': 'valentineCandles', 'festivalWreath': 'valentineWreath',
                                         'festivalWeb': 'valentineGarland', 'festivalBunting': 'valentineLights', 'festivalScarecrow': 'valentineHeart'}, 'valentineGrandHeart'),
    }
    for key, (_, remap, grand) in seasons.items():
        color = old[key][0]['color']
        dec = []
        for i, o in enumerate(base):
            if not o.get('z') and street_centre(o['x'], o['y']):
                continue
            kind = remap[o['kind']]
            if kind == 'christmasTree' and i % 3 == 0:
                kind = 'christmasSnowman'
            dec.append(dict(o, kind=kind, color=color))
        if grand:
            cand = [o for o in dec if not o.get('z') and all(math.hypot(o['x'] - n['x'], o['y'] - n['y']) > 4 for n in npcs)
                    and all(math.hypot(o['x'] - q['x'], o['y'] - q['y']) > 10 for q in portals if not q.get('seam')) and p.free(o['x'], o['y'], 0, 0, 1.7)]
            if cand:
                centre = min(cand, key=lambda o: abs(math.hypot(o['x'] - PLAZA[0], o['y'] - PLAZA[1]) - (PLAZA_R + 4)))
                dec = [o for o in dec if o.get('z') or o is centre or math.hypot(o['x'] - centre['x'], o['y'] - centre['y']) > 4]
                centre['kind'] = grand
        out[key] = dec
    return out


def sanctuary(p, spawn_plaza):
    """The city rectangle (the band that holds the fountain) and camps: row bands of floor, so the whole shield is a sanctuary."""
    n = p.n
    rects = []
    y = 22
    bands = [(y, y + 10) for y in range(22, 232, 10)]
    for y0, y1 in bands:
        rows = [r for r in range(y0, y1) if p.F[r].any()]
        while rows:
            x0 = max(int(np.nonzero(p.F[r])[0][0]) for r in rows) + 1
            x1 = min(int(np.nonzero(p.F[r])[0][-1]) for r in rows)
            if x1 - x0 >= 20:
                rects.append((x0, x1, rows[0], rows[-1] + 1))
                break
            rows = rows[:-1]
    return rects


def design(world, margin, write=False):
    import zone_shapes as zs
    zone = world['zones'][ZONE - 1]
    old = json.loads(OLD.read_text())
    p = build(zone, margin, old)
    npcs = people(p, old)
    pls = places(p, old, p.gates)
    # ---- portals: the seam stays; the Cathedral's three doors and the four gates are placed here
    keep = [q for q in zone['portals']]
    portals = []
    doors = {'cathedral_cloister': (116, 54.6), 'cathedral_nave': (128, 55.1), 'cathedral_reliquary': (140, 54.6)}
    for q in keep:
        q = dict(q)
        if q.get('seam'):
            pass
        elif q['id'] in doors:
            q['x'], q['y'] = doors[q['id']]
        else:
            g = p.gates[q['id']]
            q.update(x=g['gate'][0], y=g['gate'][1], walk=g['walk'])
        portals.append(q)
    # ---- sanctuary
    rects = sanctuary(p, PLAZA)
    city = None
    camps = []
    for x0, x1, y0, y1 in rects:
        c = dict(name='Nacrehold', x0=x0, x1=x1, y0=y0, y1=y1)
        if x0 <= PLAZA[0] <= x1 and y0 <= PLAZA[1] <= y1 and city is None:
            city = dict(c, plaza=dict(x=PLAZA[0], y=PLAZA[1]), radius=PLAZA_R, entry=dict(x=AX, y=PLAZA[1] + 19))
        else:
            cx, cy = settle(p, (x0 + x1) / 2, (y0 + y1) / 2, seam=0.)
            camps.append(dict(c, plaza=dict(x=cx, y=cy), radius=3.5, entry=dict(x=cx, y=cy)))
    assert city is not None
    spawn = settle(p, *SPAWN)
    # ---- write
    zone['spawn'] = dict(x=spawn[0], y=spawn[1])
    zone['shape']['placeAtSpawn'] = True            # saved characters are moved to the spawn: the old square does not map onto the shield
    zone['city'] = city
    zone['camps'] = camps
    zone['roads'] = p.roads
    zone['npcs'] = npcs
    zone['places'] = pls
    zone['quests'] = quests(old)
    zone['portals'] = portals
    voids = zs.void_pieces(p.F | margin)
    for o in voids:
        o.pop('layout', None)
    zone['objects'] = voids + p.objects
    zone['paths'] = []
    zone['atlasPaths'] = []
    zone['exitRoutes'] = [dict(portal=pid, points=[list(g['gate']), list(g['arrival'])]) for pid, g in p.gates.items()]
    zone['cityEntrances'] = [dict(id=pid, portal=pid, points=[list(g['gate']), list(g['arrival']), [float(g['start'][0]), float(g['start'][1])]],
                                  axis='y' if g['walk'][0] == 0 else 'x', street=float(g['start'][0] if g['walk'][0] == 0 else g['start'][1]),
                                  width=6.0 if g['walk'][0] == 0 else 4.8) for pid, g in p.gates.items()]
    zone['futureInstance'] = dict(old['futureInstance'], x=CIVIC['cathedral'][0], y=CIVIC['cathedral'][1])
    for key, val in decor(p, old, npcs, portals).items():
        zone[key] = val
    # ---- every crossing that arrives here follows the new frame
    arrivals = {pid: g['arrival'] for pid, g in p.gates.items()}
    arrivals.update({'path_1_9': p.gates['path_9_1']['arrival'], 'path_7_9': p.gates['path_9_7']['arrival'], 'astral_nacre_gate': p.gates['nacre_astral_gate']['arrival'],
                     'path_15_9': p.gates['path_9_15']['arrival']})
    for zi, z in enumerate(world['zones'], 1):
        if zi == ZONE:
            continue
        for q in z['portals']:
            if q['to'] != ZONE or q.get('seam'):
                continue
            if q['id'] in ('path_1_9', 'path_7_9', 'astral_nacre_gate', 'path_15_9'):
                q['tx'], q['ty'] = arrivals[q['id']]
            elif q['id'].startswith('cathedral_'):
                door = doors['cathedral_cloister' if 'cloister' in q['id'] else 'cathedral_reliquary' if 'reliquary' in q['id'] else 'cathedral_nave']
                q['tx'], q['ty'] = door[0], round(door[1] + 6, 1)
    if write:
        record_mailbox(zone, ROOT / 'world/mailboxes.txt')
    stats = dict(parks=p.parks, houses=sum(1 for o in p.objects if o['kind'] == 'nacrehouse'), counts=p.counts, rim_reef=p.rim_reef, objects=len(p.objects),
                 npcs=len(npcs), places=len(pls), quests=len(zone['quests']), camps=len(camps), decor={k: len(zone[k]) for k in ('seasonDecor', 'christmasDecor', 'easterDecor', 'solsticeDecor', 'valentineDecor')})
    problems = check(zone, p, margin)
    if problems:
        raise SystemExit('Nacrehold design problems:\n  ' + '\n  '.join(problems[:40]))
    return p, stats


def record_mailbox(zone, path):
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != ZONE]
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_9_nacrehold')
    m = next(n for n in zone['npcs'] if n['id'] == 'travel_nacrehold')
    directory.append(dict(id=box['id'], zone=ZONE, hub='Nacrehold', x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def check(zone, p, margin):
    import generate_gloamfen as fen
    problems = []
    n = p.n
    spawn = (zone['spawn']['x'], zone['spawn']['y'])
    seen, _ = fen.flood(zone, spawn)
    reach = lambda x, y: bool(seen[int(y / .5), int(x / .5)])
    probes = [(q['id'], q['x'], q['y']) for q in zone['npcs'] if not q['id'].startswith('festival_dance_')]
    probes += [(q['id'], q['x'], q['y']) for q in zone['places']]
    probes += [(o['label'], o['x'], o['y'] + o['depth'] / 2 + .8) for o in zone['objects'] if o['kind'] == 'nacrehouse']
    for q in zone['portals']:
        if q.get('seam'):
            probes += [('seam ' + q['id'], x, y + 4) for x, y in q['seam']['points'][2:-2:3]]
        else:
            probes.append(('portal ' + q['id'], q['x'], q['y'] + (1.6 if q['id'].startswith('cathedral_') else 0)))
            if q['id'] in p.gates:
                probes.append(('arrival ' + q['id'], *p.gates[q['id']]['arrival']))
    problems += [f'{name} at ({x}, {y}) cannot be reached from the spawn' for name, x, y in probes if not reach(x, y)]
    for q in zone['npcs']:
        route = q.get('route', [])
        for a, b in zip(route, route[1:] + route[:1]):
            steps = max(1, int(math.dist(a, b) * 4))
            if any(not reach(*(a[j] + (b[j] - a[j]) * i / steps for j in (0, 1))) for i in range(steps + 1)):
                problems.append(f"{q['id']}'s route is blocked")
                break
    # the seam: nothing the other side cannot draw stands near it
    for o in zone['objects']:
        if o['kind'] in ('void', 'coral', 'kelp'):
            continue
        d = p.D[min(n - 1, int(o['y'])), min(n - 1, int(o['x']))]
        if d < SEAM_CLEAR:
            problems.append(f"{o['kind']} at ({o['x']}, {o['y']}) stands {d:.0f} tiles from the Deep border")
        if not p.ok(o['x'], o['y'], 2.0):
            problems.append(f"{o['kind']} at ({o['x']}, {o['y']}) is off the floor")
    for q in zone['npcs']:
        if p.D[int(q['y']), int(q['x'])] < SEAM_CLEAR and not q.get('route'):
            problems.append(f"{q['id']} stands within {SEAM_CLEAR:.0f} tiles of the Deep border")
    for key in ('seasonDecor', 'christmasDecor', 'easterDecor', 'solsticeDecor', 'valentineDecor'):
        if any(p.D[int(o['y']), int(o['x'])] < SEAM_CLEAR or not p.F[int(o['y']), int(o['x'])] for o in zone[key]):
            problems.append(f'{key} stands near the Deep border or off the floor')
    # only the Deep is a seam
    seams = [q for q in zone['portals'] if q.get('seam')]
    if [q['to'] for q in seams] != [8]:
        problems.append(f"seams to {[q['to'] for q in seams]}: Rán's Deep must be the only one")
    for q in zone['portals']:
        if q['to'] in (1, 7, 13, 15) and (q.get('seam') or 'walk' not in q):
            problems.append(f"{q['id']} must stay a walk-through portal")
    # the sanctuary covers everything a player stands on
    cover = np.zeros((n, n), bool)
    for c in [zone['city']] + zone['camps']:
        cover[int(c['y0']):int(c['y1']), int(c['x0']):int(c['x1'])] = True
    share = (cover & p.F).sum() / p.F.sum()
    if share < .93:
        problems.append(f'the sanctuary covers only {share:.0%} of the floor')
    for q in zone['npcs'] + zone['places'] + [o for o in zone['objects'] if o['kind'] == 'nacrehouse']:
        if not cover[int(q['y']), int(q['x'])]:
            problems.append(f"{q.get('id') or q.get('label')} stands outside the sanctuary")
    # void covers exactly what is not floor or margin
    cov = np.zeros((n, n), np.int16)
    for o in zone['objects']:
        if o['kind'] == 'void':
            x0, x1 = int(round(o['x'] - o['width'] / 2)), int(round(o['x'] + o['width'] / 2))
            y0, y1 = int(round(o['y'] - o['depth'] / 2)), int(round(o['y'] + o['depth'] / 2))
            cov[y0:y1, x0:x1] += 1
    open_ = p.F | margin
    if not (cov[~open_] == 1).all() or (cov[open_] != 0).any():
        problems.append('void does not cover exactly the cells that are not floor')
    houses = [o for o in zone['objects'] if o['kind'] == 'nacrehouse']
    if len(houses) != 120 or len({o['label'] for o in houses}) != 120:
        problems.append('Nacrehold must have 120 homes with unique labels')
    ids = {q['id'] for q in zone['npcs']}
    places_ = {q['id'] for q in zone['places']}
    for q in zone['quests']:
        if len('quest:accept:' + q['id']) > 32 and q['id'] in NEW_QUESTS:
            problems.append(f"{q['id']}: accept string too long")
        if q.get('npc') and q['npc'] not in ids:
            problems.append(f"{q['id']}: giver {q['npc']} is missing")
        for ob in q['objectives']:
            if ob['kind'] == 'visit' and q['id'].split('_')[0] in ('nacre', 'es') and ob['target'] not in places_:
                problems.append(f"{q['id']}: place {ob['target']} is missing")
            if ob['kind'] == 'talk' and q['id'].startswith('nacre_') and ob['target'] not in ids:
                problems.append(f"{q['id']}: person {ob['target']} is missing")
    return problems


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == 'plan':
        world = json.loads(MAP.read_text())
        zone = world['zones'][ZONE - 1]
        picture(zone, sys.argv[2])
        print('wrote', sys.argv[2])


if __name__ == '__main__':
    main()
