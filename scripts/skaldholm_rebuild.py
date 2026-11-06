#!/usr/bin/env python3
"""Skaldholm rebuild (docs/skaldholm-rebuild.md): the city is made in the middle of the four neighbours' walls.

Runs at the very END of `zone_shapes.py apply`, after the four neighbours are shaped, walled and designed, so their walls, floors and
vault pockets are exactly what they were (asserted below). The old square city is the SOURCE (sidecar world/zone-shapes/preshape-04.txt,
saved at the start of `apply`, restored by `unshape`); this step builds the new city from it:

  * one frame: city tile = atlas tile - TC, grid SIZE (TC and SIZE are fixed here; the neighbours use atlas tile - shape.T),
  * the ground is the L the neighbours leave (their floors and walls are fixed), plus the pocket in front of each door,
  * the old strip x STRIP of the square moves rigidly (ODX, ODY); what stood outside it goes to the south band (`band_*`),
  * the city has NO wall of its own: beyond the L there is void collision, and the neighbours' walls are drawn through their
    vault regions (client/field.js); each vault's `shift` is now simply T_neighbour - TC, the arches stand in the doorways.
"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zone_shapes as zs  # noqa: E402

TC = (352, 584)                 # city tile = atlas tile - TC (the portals stand 3 tiles outside the arches: all inside the grid)
SIZE = 184
STRIP = (38.5, 123.5)           # old x range that stays rigid (85 wide: the north part of the L)
OLD_Y = (13.0, 139.5)
ODX, ODY = 331.5 - TC[0], 587.0 - TC[1]     # old city frame -> city frame for the strip
DB = 590 - TC[1]                # the band's hand-placed rows were laid out for TC y 590
NEIGHBOURS = (0, 1, 2, 3)       # Greenmeadow, Crags, Rimeveil, Gloamfen
CITY = 4
SIDE = zs.SIDE / 'preshape-04.txt'
TAG = zs.TAG
EAST_WALL_X = 456            # atlas: the Crags' east wall (x 456.2, y 599-727) carries on straight down to Greenmeadow's wall
EAST_WALL_Y0 = 720          # (the Crags' door alcove at y ~663 reaches past x 456: only the wing below it is cut)


def mv(x, y):
    return round(x + ODX, 2), round(y + ODY, 2)


def in_strip(x, y):
    return STRIP[0] <= x < STRIP[1] and OLD_Y[0] <= y < OLD_Y[1]


# ---- sidecar -------------------------------------------------------------------------------------------------------------
def incoming(world):
    """Portals of zones that are not neighbours of the city, arriving in it: their arrival is in the city's frame."""
    out = {}
    for zi in range(1 + len(world['zones'])):
        if zi in NEIGHBOURS or zi == CITY:
            continue
        for p in zs.zone_of(world, zi).get('portals', []):
            if p['to'] == CITY and 'tx' in p:
                out.setdefault(str(zi), {})[p['id']] = [p['tx'], p['ty']]
    return out


def save_sidecar(world):
    """Before anything of `apply` touches the city (the neighbours' build_walls edits its back portals)."""
    zone = zs.zone_of(world, CITY)
    assert zone['name'] == 'Skaldholm' and 'shape' not in zone, 'the city is already rebuilt: run unshape first'
    SIDE.write_text(json.dumps(dict(view=zs.get_view(world, CITY), incoming=incoming(world)), indent=1, ensure_ascii=False) + '\n')


def restore(world):
    """`unshape`: put the old square city and the portals that arrive in it back (after the neighbours' shift_incoming(-1))."""
    zone = zs.zone_of(world, CITY)
    if 'shape' not in zone:
        return
    side = json.loads(SIDE.read_text())
    zs.set_view(world, CITY, side['view'])
    for zi, ps in side['incoming'].items():
        for p in zs.zone_of(world, int(zi)).get('portals', []):
            if p['id'] in ps and p['to'] == CITY:
                p['tx'], p['ty'] = ps[p['id']]


# ---- the L ---------------------------------------------------------------------------------------------------------------
def pocket_cells(zone, gate, arch):
    """The cells of the land pocket a neighbour adds beyond its wall in front of the door (see zone_shapes.build_walls)."""
    n = zone['size']
    wx, wy = gate['walk']
    px, py = -wy, wx
    hw = gate['vault_half']
    ys, xs = np.mgrid[0:n, 0:n]
    dx, dy = xs + .5 - arch['x'], ys + .5 - arch['y']
    along, across = dx * wx + dy * wy, dx * px + dy * py
    # from 3.5 tiles beyond the arch (an alcove through the wall opening: you arrive at the arch line and must be able to turn round) to the pocket's end
    return ((along >= 0.5) & (along <= 6.2) & (np.abs(across) <= hw + 1.0)) | ((along >= -3.5) & (along < 0.5) & (np.abs(across) <= hw - 1.0))


def city_floor(world):
    """(floor, owned): `floor` = the city's ground in the city grid, `owned[z]` = the neighbour floors in atlas cells."""
    X0, Y0, W, H = 340, 570, 220, 240
    occ = np.zeros((H, W), bool)
    pocket = np.zeros((H, W), bool)
    for i in NEIGHBOURS:
        z = zs.zone_of(world, i)
        T = z['shape']['T']
        fl = np.array([[c == '#' for c in row] for row in z['shapeFloor']])
        ys, xs = np.nonzero(fl)
        for y, x in zip(ys + T[1] - Y0, xs + T[0] - X0):
            if 0 <= y < H and 0 <= x < W:
                occ[y, x] = True
        gate = next(p for p in z['portals'] if p['to'] == CITY and 'vault' in p)
        arch = next(a for a in z['exitArches'] if a['portal'] == gate['id'])
        pk = pocket_cells(z, gate, arch)
        ys, xs = np.nonzero(pk)
        for y, x in zip(ys + T[1] - Y0, xs + T[0] - X0):
            if 0 <= y < H and 0 <= x < W:
                pocket[y, x] = True
    seen = np.zeros((H, W), bool)
    stack = [(420 - X0, 690 - Y0)]
    seen[stack[0][1], stack[0][0]] = True
    while stack:
        a, b = stack.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            u, v = a + da, b + db
            assert 0 <= u < W and 0 <= v < H, 'the four walls do not enclose the city'
            if not seen[v, u] and not occ[v, u]:
                seen[v, u] = True
                stack.append((u, v))
    land = seen | pocket
    land[EAST_WALL_Y0 - Y0:, EAST_WALL_X - X0:] = False        # the right wing is not the city: its wall runs straight down from the Crags' to Greenmeadow's
    floor = np.zeros((SIZE, SIZE), bool)
    ys, xs = np.nonzero(land)
    for y, x in zip(ys + Y0 - TC[1], xs + X0 - TC[0]):
        assert 0 <= y < SIZE and 0 <= x < SIZE, f'the city ground leaves the grid at {(x, y)}'
        floor[y, x] = True
    return floor


# ---- what the neighbours must keep ---------------------------------------------------------------------------------------
def neighbour_fingerprint(world):
    out = {}
    for i in NEIGHBOURS:
        z = zs.zone_of(world, i)
        walls = [o for o in z['objects'] if o['kind'] in ('rampart', 'tower') and o.get('layout') == TAG] if i != 0 else []     # (Greenmeadow's wall is trimmed below, on purpose)
        out[i] = hashlib.sha256(json.dumps([walls, z['shapeFloor'], z['shape'].get('vaultRegions')], sort_keys=True).encode()).hexdigest()
    return out


# ---- the rebuild ---------------------------------------------------------------------------------------------------------
def rebuild(world):
    city = zs.zone_of(world, CITY)
    assert city['name'] == 'Skaldholm' and 'shape' not in city
    before = neighbour_fingerprint(world)
    old = copy.deepcopy(city)
    floor = city_floor(world)
    n = SIZE

    # -- frames: every vault's shift is the difference of the frames; the arches stand in the doorways
    for i in NEIGHBOURS:
        z = zs.zone_of(world, i)
        T = z['shape']['T']
        shift = [T[0] - TC[0], T[1] - TC[1]]
        gate = next(p for p in z['portals'] if p['to'] == CITY and 'vault' in p)
        arch = next(a for a in z['exitArches'] if a['portal'] == gate['id'])
        back = next(p for p in city['portals'] if p['to'] == i)
        carch_old = next(a for a in old['exitArches'] if a['portal'] == back['id'])
        wx, wy = gate['walk']
        assert [wx, wy] == [-back['walk'][0], -back['walk'][1]]
        gate['vault'] = shift
        gate['tx'], gate['ty'] = round(gate['x'] + shift[0], 2), round(gate['y'] + shift[1], 2)
        carch = dict(carch_old, x=round(arch['x'] + shift[0], 2), y=round(arch['y'] + shift[1], 2))
        city['exitArches'] = [a for a in city['exitArches'] if a['portal'] != back['id']] + [carch]
        back['x'], back['y'] = round(carch['x'] - wx * 1.0, 2), round(carch['y'] - wy * 1.0, 2)     # beyond the arch is the neighbour's ground and the walker stops at the arch line: a vault crosses from 3 tiles before its portal
        back['vault'] = [-shift[0], -shift[1]]
        back['tx'], back['ty'] = round(back['x'] - shift[0], 2), round(back['y'] - shift[1], 2)

    # -- the ground and the void beyond it
    city['size'] = n
    city['objects'] = []
    move_content(city, old)
    for p in city['portals']:
        if p['id'] == 'undervault_stairs':
            p['x'], p['y'] = mv(p['x'], p['y'])
    for zi in range(1 + len(world['zones'])):
        if zi in NEIGHBOURS or zi == CITY:
            continue
        for p in zs.zone_of(world, zi).get('portals', []):
            if p['to'] == CITY and 'tx' in p:
                p['tx'], p['ty'] = mv(p['tx'], p['ty'])
    open_hall_lane(city)
    place_band(city, old, floor)
    east_wall(world, city)
    quiet_lobe(world)
    city['objects'].extend(zs.void_pieces(floor))
    city['shapeFloor'] = zs.floor_rows(floor)
    city['shapeEdge'] = edge_rows(world, floor)
    ys, xs = np.nonzero(floor)
    city['shape'] = dict(rule='rebuild', k=1.0, offset=[0, 0], core=old['size'], bbox=[int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)],
                         T=list(TC), outline=[], edges=[], neighbours=list(NEIGHBOURS))
    city['city'] = dict(old['city'], x0=int(xs.min()), x1=int(xs.max()) + 1, y0=int(ys.min()), y1=int(ys.max()) + 1)
    c = city['city']
    c['plaza'] = dict(zip('xy', mv(old['city']['plaza']['x'], old['city']['plaza']['y'])))
    # -- the city's own streets from each door
    entrances(city)
    south = next(p for p in city['portals'] if p['to'] == 0)
    north = next(p for p in city['portals'] if p['to'] == 2)
    c['entry'] = dict(x=round(south['x'], 2), y=round(south['y'] - 6, 2))
    city['spawn'] = dict(x=round(c['plaza']['x'], 2), y=round(c['plaza']['y'] + 25.0, 2))
    settle_npcs(city)
    import compact_atlas as ca
    ca.exit_routes(city)
    check_city(city, floor)

    after = neighbour_fingerprint(world)
    assert before == after, f'the neighbours changed: {[i for i in NEIGHBOURS if before[i] != after[i]]}'
    print(f"skaldholm rebuilt: {int(floor.sum())} tiles of ground, grid {n}, strip shift ({ODX}, {ODY}), "
          f"{sum(1 for o in city['objects'] if o['kind'] == 'house')} houses")
    return floor


def edge_rows(world, floor):
    """Beside the L the ground belongs to the neighbour that owns it: one letter per neighbour (index into shape.neighbours)."""
    owner = {}
    for i in NEIGHBOURS:
        z = zs.zone_of(world, i)
        T = z['shape']['T']
        for y, row in enumerate(z['shapeFloor']):
            for x, ch in enumerate(row):
                if ch == '#':
                    owner[(x + T[0] - TC[0], y + T[1] - TC[1])] = chr(ord('A') + NEIGHBOURS.index(i))
    band = zs.dilate(floor, zs.EDGE_BAND) & ~floor
    return [''.join(owner.get((x, y), ' ') if band[y, x] else ' ' for x in range(SIZE)) for y in range(SIZE)]


def move_content(city, old):
    """Everything of the old square that stays in the strip, translated; the rest is `band_*` (placed by skaldholm_band)."""
    keep = lambda o: in_strip(o['x'], o['y'])
    ring = lambda o: o['kind'] in ('rampart', 'tower') and not in_strip(o['x'], o['y'])
    for o in old['objects']:
        if keep(o) and not ring(o):
            city['objects'].append(dict(o, x=mv(o['x'], o['y'])[0], y=mv(o['x'], o['y'])[1]))
    roads = []
    for r in old['roads']:
        if 'x0' in r:
            x0, x1, y1 = max(r['x0'], STRIP[0]), min(r['x1'], STRIP[1]), min(r['y1'], OLD_Y[1])
            if x1 > x0 and r['y0'] < OLD_Y[1]:
                a, b = mv(x0, r['y0'])
                c, d = mv(x1, y1)
                roads.append(dict(r, x0=a, y0=b, x1=c, y1=d))
        elif in_strip(r['x'], r['y']):
            a, b = mv(r['x'], r['y'])
            roads.append(dict(r, x=a, y=b))
    city['roads'] = roads
    npcs = []
    for npc in old['npcs']:
        if in_strip(npc['x'], npc['y']):
            q = dict(npc)
            q['x'], q['y'] = mv(npc['x'], npc['y'])
            if q.get('route'):
                q['route'] = [list(mv(min(max(p[0], STRIP[0] + 1.0), STRIP[1] - 1.0), p[1])) for p in npc['route']]
            npcs.append(q)
    city['npcs'] = npcs
    city['places'] = [dict(p, **dict(zip('xy', mv(p['x'], p['y'])))) for p in old['places'] if in_strip(p['x'], p['y'])]
    for key in ('seasonDecor', 'christmasDecor', 'easterDecor', 'solsticeDecor', 'valentineDecor'):
        city[key] = [dict(o, **dict(zip('xy', mv(o['x'], o['y'])))) for o in old.get(key, []) if in_strip(o['x'], o['y'])]


def entrances(city):
    """cityEntrances, paths, atlasPaths: from each door straight in along its street (the doors are fixed by the neighbours)."""
    ents, paths = [], []
    for a in city['exitArches']:
        back = next(p for p in city['portals'] if p['id'] == a['portal'])
        wx, wy = -back['walk'][0], -back['walk'][1]
        p0 = [back['x'], back['y']]
        reach = 11 if back['to'] == 3 else 18     # West Street ends at Lark Lane
        p1 = [round(a['x'] + wx * reach, 2), round(a['y'] + wy * reach, 2)]
        pts = [p0, p1]
        ents.append(dict(id=back['id'], portal=back['id'], points=pts, axis='y' if wy else 'x', street=a['x'] if wy else a['y'],
                         width=7.0 if a['halfWidth'] > 5 else 4.0, opening={k: a[k] for k in ('x', 'y', 'vertical', 'halfWidth', 'towers', 'portal', 'name')}))
        paths.append([[round(a['x'] - wx * 5.5, 2), round(a['y'] - wy * 5.5, 2)]] + pts[1:])
    city['cityEntrances'] = ents
    city['paths'] = paths
    city['atlasPaths'] = copy.deepcopy(paths)


# ---- the Steward's Hall and the north door -----------------------------------------------------------------------------------
def open_hall_lane(city):
    """The Rimeveil door lands on the Grand Avenue, and the Steward's Hall used to close the avenue there: its two flank towers go and the hall
    steps aside to the east (the free ground where the east tower stood), so the main road runs from the door straight down."""
    gone = [o for o in city['objects'] if o['kind'] == 'tower' and any(abs(o['x'] - mv(tx, 19)[0]) < .1 and abs(o['y'] - mv(tx, 19)[1]) < .1 for tx in (71.6, 88.4))]
    assert len(gone) == 2, 'the hall towers moved'
    city['objects'] = [o for o in city['objects'] if o not in gone]
    hall = next(o for o in city['objects'] if o['kind'] == 'house' and o.get('label') == "Steward's Hall")
    others = [footprint(o) for o in city['objects'] if o is not hall and o['kind'] != 'void']
    for nx in (68.4, 69.4, 70.4, 71.4, 72.4):
        q = dict(hall, x=nx)
        b = footprint(q)
        if not any(b[0] - .4 < c[2] and b[2] + .4 > c[0] and b[1] - .4 < c[3] and b[3] + .4 > c[1] for c in others):
            hall['x'] = nx
            return
    raise AssertionError("the Steward's Hall found no place beside the avenue")


# ---- the south band ------------------------------------------------------------------------------------------------------
def footprint(o):
    if o.get('width'):
        return o['x'] - o['width'] / 2, o['y'] - o['depth'] / 2, o['x'] + o['width'] / 2, o['y'] + o['depth'] / 2
    r = max(o.get('r', 0.5) or 0.5, 0.4)
    return o['x'] - r, o['y'] - r, o['x'] + r, o['y'] + r


class Lots:
    """Free-ground test for placing things: on the floor, off every object, off every street (yards are placed on purpose)."""

    def __init__(self, city, floor):
        self.floor = floor
        self.solid = [footprint(o) for o in city['objects'] if o['kind'] != 'void']
        self.streets = [(r['x0'], r['y0'], r['x1'], r['y1']) for r in city['roads'] if 'x0' in r and r['t'] == 1]
        self.discs = [(r['x'], r['y'], r['r1']) for r in city['roads'] if 'x0' not in r and r['t'] == 1]

    def on_floor(self, b):
        x0, y0, x1, y1 = b
        return all(0 <= int(y) < SIZE and 0 <= int(x) < SIZE and self.floor[int(y), int(x)]
                   for x in (x0, (x0 + x1) / 2, x1) for y in (y0, (y0 + y1) / 2, y1))

    def free(self, o, margin=0.5, streets=True):
        x0, y0, x1, y1 = footprint(o)
        b = (x0 - margin, y0 - margin, x1 + margin, y1 + margin)
        if not self.on_floor((x0, y0, x1, y1)):
            return False
        if any(b[0] < q[2] and b[2] > q[0] and b[1] < q[3] and b[3] > q[1] for q in self.solid):
            return False
        if streets:
            if any(b[0] < q[2] and b[2] > q[0] and b[1] < q[3] and b[3] > q[1] for q in self.streets):
                return False
            if any(math.hypot(max(abs(o['x'] - d[0]) - (x1 - x0) / 2, 0), max(abs(o['y'] - d[1]) - (y1 - y0) / 2, 0)) < d[2] for d in self.discs):
                return False
        return True

    def add(self, o, **kw):
        if not self.free(o, **kw):
            return False
        self.solid.append(footprint(o))
        return True


# where the strip leftovers go: (old x range, old y range) -> new origin of that group's old top-left corner (city frame)
SMITHY = dict(old=(17.0, 38.5, 93.0, 108.0), to=(19.5, 153.0 + DB))      # campfire, forge props, smith and apprentice
STABLE = dict(old=(123.5, 143.0, 114.0, 131.0), to=(84.0, 152.0 + DB))  # the stables, its wall pieces and barrels
GARDEN = dict(old=(17.0, 38.5, 13.0, 30.0), to=(63.0, 152.0 + DB))       # (east of the main street's road to the south door)       # the NW garden: fountain, benches, flowers, gardener, painter
MARKET = dict(old=(17.0, 143.0, 70.0, 75.0), to=None)               # the Trade Road's stall rows: only the stalls and barrels move


def in_box(o, g):
    x0, x1, y0, y1 = g['old']
    return x0 <= o['x'] < x1 and y0 <= o['y'] < y1


def place_band(city, old, floor):
    lots = Lots(city, floor)
    moved = []              # (old x, old y, dx, dy): decor follows the piece it belongs to
    street_y = 148.0 + DB
    city['roads'].append(dict(t=1, x0=18.0, y0=street_y - 2.0, x1=104.0, y1=street_y + 2.0))       # Southgate Street
    new_streets = [(18.0, street_y - 2.0, 104.0, street_y + 2.0)]
    lots.streets.append(new_streets[0])
    for p in city['portals']:
        if p['to'] == 0:    # the road up from the Greenmeadow door
            city['roads'].append(dict(t=1, x0=p['x'] - 2.0, y0=street_y, x1=p['x'] + 2.0, y1=p['y'] + 2.0))
            new_streets.append((p['x'] - 2.0, street_y, p['x'] + 2.0, p['y'] + 2.0))
            lots.streets.append(new_streets[-1])
        if p['to'] == 3:    # West Street: from the Gloamfen door to Lark Lane
            a = next(a for a in city['exitArches'] if a['portal'] == p['id'])
            city['roads'].append(dict(t=1, x0=a['x'], y0=a['y'] - 2.0, x1=29.5, y1=a['y'] + 2.0))
            new_streets.append((a['x'], a['y'] - 2.0, 29.5, a['y'] + 2.0))
            lots.streets.append(new_streets[-1])
    # the avenue and the two minor streets run on down to Southgate Street
    for r in list(city['roads']):
        if 'x0' in r and r['t'] == 1 and abs(r['y1'] - mv(0, 139)[1]) < .6 and r['y0'] < 40:
            r['y1'] = street_y - 2.0
    # the streets as they are now (the avenue and the two lanes reach Southgate Street): no house may stand on any of them
    lots.streets = [(r['x0'], r['y0'], r['x1'], r['y1']) for r in city['roads'] if 'x0' in r and r['t'] == 1]
    # strip houses that stand in the new West Street or the hall lane go to the band like the rest
    pend = []
    stay = []
    fresh = list(new_streets)                               # Southgate Street, the road from the south door, West Street
    for o in city['objects']:
        if o['kind'] == 'house' and o['width'] <= 4.5 and o not in pend:
            sq = footprint(o)
            if any(sq[0] < q[2] and sq[2] > q[0] and sq[1] < q[3] and sq[3] > q[1] for q in fresh):
                pend.append(o)
                continue
        stay.append(o)
    city['objects'] = stay
    lots.solid = [footprint(o) for o in city['objects'] if o['kind'] != 'void']

    def shift_group(g):
        return g['to'][0] - g['old'][0], g['to'][1] - g['old'][2]

    groups = {'smithy': SMITHY, 'stable': STABLE, 'garden': GARDEN}
    placed_npcs = []
    for name, g in groups.items():
        dx, dy = shift_group(g)
        for o in old['objects']:
            if in_box(o, g) and o['kind'] not in ('tree', 'bush', 'rampart', 'tower', 'house'):
                q = dict(o, x=round(o['x'] + dx, 2), y=round(o['y'] + dy, 2))
                if lots.free(q, margin=0.2, streets=False):
                    city['objects'].append(q)
                    lots.solid.append(footprint(q))
                    moved.append((o['x'], o['y'], dx, dy))
        for o in old['objects']:
            if in_box(o, g) and o['kind'] == 'house' and o['width'] > 4.5:       # the smith's house and the stables
                q = dict(o, x=round(o['x'] + dx, 2), y=round(o['y'] + dy, 2))
                assert lots.add(q, margin=0.2, streets=False), f"{o.get('label')} does not fit its yard"
                city['objects'].append(q)
                moved.append((o['x'], o['y'], dx, dy))
        for npc in old['npcs']:
            if in_box(npc, g) and npc['id'] != 'city_watch_wall':      # the wall watch gets its own beat below
                q = dict(npc, x=round(npc['x'] + dx, 2), y=round(npc['y'] + dy, 2))
                if q.get('route'):
                    q['route'] = [[round(a + dx, 2), round(b + dy, 2)] for a, b in npc['route']]
                    if npc['id'] == 'city_gardener':        # the garden is shorter here: a walk along its path
                        q['route'] = [[q['x'], 155.0 + DB], [q['x'], 162.5 + DB]]
                        q['y'] = 155.0 + DB
                city['npcs'].append(q)
                placed_npcs.append(q['id'])
        x0, x1, y0, y1 = g['old']
        for r in old['roads']:      # yard paving and garden paths that lie in the group
            if 'x0' in r and r['t'] in (2, 3) and x0 - 1 <= r['x0'] and r['x1'] <= x1 + 6 and y0 <= r['y0'] and r['y1'] <= y1 + 1:
                city['roads'].append(dict(r, x0=round(r['x0'] + dx, 2), x1=round(r['x1'] + dx, 2), y0=round(r['y0'] + dy, 2), y1=round(r['y1'] + dy, 2)))
    # market stalls and barrels of the Trade Road's outer ends: along the new Market Row beside Southgate Street
    mx = 42.0
    for o in old['objects']:
        if o['kind'] in ('stall', 'barrels') and 70 < o['y'] < 73 and not in_strip(o['x'], o['y']):
            q = dict(o, x=round(mx + (0.7 if o['kind'] == 'barrels' else 0.0), 2), y=round((155.5 if o['kind'] == 'stall' else 156.8) + DB, 2))
            if lots.free(q, margin=0.2, streets=False):
                city['objects'].append(q)
                lots.solid.append(footprint(q))
                moved.append((o['x'], o['y'], q['x'] - o['x'], q['y'] - o['y']))
            if o['kind'] == 'stall':
                mx += 3.0
    for npc in old['npcs']:         # the weaver sold at those stalls
        if npc['id'] == 'city_weaver':
            city['npcs'].append(dict(npc, x=round(mx - 5.0, 2), y=157.6 + DB))
            placed_npcs.append(npc['id'])
    # the houses that stood outside the strip, and any pushed out of a new street, along Southgate Street (doors face south)
    plain = [o for o in old['objects'] if o['kind'] == 'house' and not in_strip(o['x'], o['y']) and 17 <= o['x'] <= 143 and 13 <= o['y'] <= 139 and o['width'] <= 4.5] + pend
    slots = []
    for row_y in (142.4 + DB, 152.6 + DB, 157.4 + DB, 162.2 + DB, 166.6 + DB):
        x = 20.5
        while x < 103:
            slots.append((round(x, 2), row_y))
            x += 4.8
    left = []
    for h in plain:
        for sx, sy in slots:
            q = dict(h, x=sx, y=sy)
            if lots.add(q, margin=0.9):
                city['objects'].append(q)
                moved.append((h['x'], h['y'], q['x'] - h['x'], q['y'] - h['y']))
                break
        else:
            left.append(h)
    assert not left, f'{len(left)} houses found no lot in the band'
    # NPCs that patrolled the old outer walls
    for npc in old['npcs']:
        if npc['id'] == 'city_watch_trade':
            y0, y1 = mv(0, 74.2)[1], mv(0, 77.8)[1]
            q = dict(npc, x=21.0, y=y0)
            q['route'] = [[21.0, y0], [45.5, y0], [45.5, y1], [21.0, y1]]
            city['npcs'].append(q)
            placed_npcs.append(npc['id'])
        if npc['id'] == 'city_watch_wall':
            q = dict(npc)
            q['route'] = [[22.0, 138.0 + DB], [70.0, 138.0 + DB], [70.0, 140.2 + DB], [22.0, 140.2 + DB]]
            q['x'], q['y'] = 22.0, 138.0 + DB
            city['npcs'].append(q)
            placed_npcs.append(npc['id'])
    # seasonal decor follows the piece it belonged to (within 6 tiles of one that moved), the rest of the outside is dropped
    for key in ('seasonDecor', 'christmasDecor', 'easterDecor', 'solsticeDecor', 'valentineDecor'):
        for o in old.get(key, []):
            if in_strip(o['x'], o['y']):
                continue
            near = min(moved, key=lambda m: math.hypot(m[0] - o['x'], m[1] - o['y']), default=None)
            if near and math.hypot(near[0] - o['x'], near[1] - o['y']) <= 6:
                city[key].append(dict(o, x=round(o['x'] + near[2], 2), y=round(o['y'] + near[3], 2)))
    for key in ('seasonDecor', 'christmasDecor', 'easterDecor', 'solsticeDecor', 'valentineDecor'):      # decor stands on the city's ground, never beyond it
        city[key] = [o for o in city[key] if 0 <= int(o['y']) < SIZE and 0 <= int(o['x']) < SIZE and floor[int(o['y']), int(o['x'])]]
    missing = {n['id'] for n in old['npcs']} - {n['id'] for n in city['npcs']}
    assert not missing, f'NPCs without a place: {sorted(missing)}'


def settle_npcs(city):
    """A person who stands in a wall's margin or inside a house after the move steps to the nearest ground a walker can reach."""
    import compact_atlas as ca
    prev = ca.connected(city)
    for npc in city['npcs']:
        if npc.get('route') or int(npc['y']) * SIZE + int(npc['x']) in prev:
            continue
        best = None
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                x, y = int(npc['x']) + dx + .5, int(npc['y']) + dy + .5
                if int(y) * SIZE + int(x) in prev and (best is None or math.hypot(x - npc['x'], y - npc['y']) < best[0]):
                    best = (math.hypot(x - npc['x'], y - npc['y']), x, y)
        assert best, f"{npc['id']} has no reachable ground within 5 tiles"
        npc['x'], npc['y'] = round(best[1], 2), round(best[2], 2)


WING = (456, 504, 733, 758)    # atlas x0, x1, y0, y1: the old right-hand wing, now Greenmeadow's ground (its top 6 rows toward the Crags stay a cliff)


def prepare(world, margins):
    """Runs after the neighbours' walls are built and BEFORE their designs (so Greenmeadow's design fills what it is given):
      * Greenmeadow's wall stops at the city's east wall, and the wing east of it becomes Greenmeadow's land;
      * the south-west corner is a corner: Gloamfen's west wall stops at Greenmeadow's wall line, Greenmeadow's wall starts at it."""
    import numpy as np
    trim_greenmeadow_flank(world)
    z = zs.zone_of(world, 0)
    T = z['shape']['T']
    n = z['size']
    floor = np.array([[c == '#' for c in row] for row in z['shapeFloor']])
    new = np.zeros_like(floor)
    for y in range(WING[2], WING[3]):
        for x in range(WING[0], WING[1]):
            yy, xx = y - T[1], x - T[0]
            if 0 <= yy < n and 0 <= xx < n and not floor[yy, xx]:
                new[yy, xx] = True
    for i in (1, 2, 3):      # nobody else owns these cells
        o = zs.zone_of(world, i)
        To = o['shape']['T']
        ys, xs = np.nonzero(new)
        assert not any(0 <= y + T[1] - To[1] < o['size'] and 0 <= x + T[0] - To[0] < o['size'] and o['shapeFloor'][y + T[1] - To[1]][x + T[0] - To[0]] == '#' for y, x in zip(ys, xs)), f'zone {i} owns part of the wing'
    floor |= new
    z['shapeFloor'] = zs.floor_rows(floor)
    z['objects'] = [o for o in z['objects'] if o['kind'] != 'void'] + zs.void_pieces(floor | margins[0])
    letter = chr(ord('A') + z['shape']['neighbours'].index(CITY))
    near = zs.dilate(new, zs.EDGE_BAND) & ~floor
    rows = [list(r) for r in z['shapeEdge']]
    for yy in range(n):
        for xx in range(n):
            if floor[yy, xx]:
                rows[yy][xx] = ' '
            elif near[yy, xx] and rows[yy][xx] == letter:
                rows[yy][xx] = 'l'          # outer land: the cliff between the wing and the Crags
    z['shapeEdge'] = [''.join(r) for r in rows]
    cut = EAST_WALL_X - T[0]
    for reg in z['shape'].get('vaultRegions', []):        # the vault's regions end at the city's east wall
        for key in ('city', 'land', 'strip'):
            pts = reg[key]
            for k in range(0, len(pts), 2):
                pts[k] = min(pts[k], cut)
    print(f"greenmeadow wing: {int(new.sum())} tiles of land")
    # the south-west corner: Gloamfen's wall must not run on past Greenmeadow's wall line, and Greenmeadow's wall must not start inside Gloamfen's
    fen = zs.zone_of(world, 3)
    Tf = fen['shape']['T']
    wall_y = next(o['y'] + T[1] for o in z['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG)
    fen['objects'] = [o for o in fen['objects'] if not (o['kind'] in ('rampart', 'tower') and o.get('layout') == TAG and o['y'] + Tf[1] > wall_y + 3.0)]
    first = min((o for o in z['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG), key=lambda o: o['x'])
    first['x'] = round(first['x'] + 2.7, 2)       # (the designs see this geometry; `south_west_corner` finishes the corner after them, so no design draw changes)
    print("south-west corner squared: Gloamfen wall pieces beyond Greenmeadow's wall line removed")


def south_west_corner(world, margins):
    """The corner is one structure in all three zones (owner, 2026-11-06: "the wall is broken" where Greenmeadow, Gloamfen and Skaldholm meet).
    Runs AFTER the designs (their random draws follow the geometry they see: finishing the corner earlier reshuffled 215 spawns).
    * Gloamfen's last rampart ends at the south face of Greenmeadow's wall (it ran 1.2 tiles past it) and Greenmeadow's first rampart fills exactly
      from the corner tower to its neighbour (the old +2.7 shift stacked it 2.8 tiles over the next piece);
    * the corner tower is a piece of BOTH neighbours, so each zone draws it itself (a ghost of the city's copy was suppressed beside the rampart);
    * below the corner Gloamfen's land (x < 370) and Greenmeadow's (x >= 370) meet along a 6.4-tile straight border that had no wall and no seam
      (a dead end): the 0-3 seam now starts at the corner, with Gloamfen's edge cells beyond it relabelled as Greenmeadow's."""
    z, fen = zs.zone_of(world, 0), zs.zone_of(world, 3)
    T, Tf = z['shape']['T'], fen['shape']['T']
    wall_y = next(o['y'] + T[1] for o in z['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG)
    face = round(wall_y + 0.9, 2)                          # the south face of Greenmeadow's wall (depth 1.8)
    walls = [o for o in fen['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG]
    last = max(walls, key=lambda o: o['y'])
    wall_x = last['x'] + Tf[0]
    top = last['y'] + Tf[1] - last['depth'] / 2
    last['y'] = round((top + face) / 2 - Tf[1], 2)
    last['depth'] = round(face - top, 2)
    ramps = sorted((o for o in z['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG), key=lambda o: o['x'])
    first, second = ramps[0], ramps[1]
    left = wall_x + 1.7 - 0.1                              # under the tower (3.4 wide)
    right = second['x'] + T[0] - second['width'] / 2 + 0.1
    first['x'], first['width'] = round((left + right) / 2 - T[0], 2), round(right - left, 2)
    tower = dict(kind='tower', r=0, v=0, width=3.4, depth=3.4, color='#4a7a9a', label='', layout=TAG)
    z['objects'].append(dict(tower, x=round(wall_x - T[0], 2), y=round(wall_y - T[1], 2)))
    fen['objects'].append(dict(tower, x=round(wall_x - Tf[0], 2), y=round(wall_y - Tf[1], 2)))
    # the seam: both frames' border is the straight line x = BORDER_X from the corner down to the old start (370, 765)
    bx = wall_x + 1.1                                      # 370.0: Gloamfen's floor ends at x 369, Greenmeadow's starts at 370
    assert abs(bx - 370.0) < 0.05, bx
    seam_f = next(p for p in fen['portals'] if p.get('seam') and p['to'] == 0)['seam']
    seam_g = next(p for p in z['portals'] if p.get('seam') and p['to'] == 3)['seam']
    assert seam_f['points'][0] == [370.0 - Tf[0], 765.0 - Tf[1]] and seam_g['points'][-1] == [370.0 - T[0], 765.0 - T[1]], 'the 0-3 seam no longer starts at (370, 765)'
    seam_f['points'].insert(0, [round(370.0 - Tf[0], 2), round(face - Tf[1], 2)])
    seam_g['points'].append([round(370.0 - T[0], 2), round(face - T[1], 2)])
    gl = [[c == '#' for c in row] for row in z['shapeFloor']]
    rows = [list(r) for r in fen['shapeEdge']]
    a, c = chr(ord('A') + fen['shape']['neighbours'].index(0)), chr(ord('A') + fen['shape']['neighbours'].index(CITY))
    n = 0
    for yy, row in enumerate(rows):
        for xx, ch in enumerate(row):
            ax, ay = xx + Tf[0], yy + Tf[1]
            if ch == c and ay >= face and 0 <= ay - T[1] < len(gl) and 0 <= ax - T[0] < len(gl[0]) and gl[ay - T[1]][ax - T[0]]:
                row[xx] = a
                n += 1
    fen['shapeEdge'] = [''.join(r) for r in rows]
    # land runs SEAM_MARGIN past the new stretch of seam (the walker steps over the line and the server moves it): rebuild both zones' voids
    import numpy as np
    for zone, zi, T_ in ((z, 0, T), (fen, 3, Tf)):
        floor = np.array([[c == '#' for c in row] for row in zone['shapeFloor']])
        n = floor.shape[0]
        ys, xs = np.mgrid[0:n, 0:n]
        ax, ay = xs + .5 + T_[0], ys + .5 + T_[1]
        t = np.clip((ay - face) / (765.0 - face), 0, 1)
        grown = np.hypot(ax - 370.0, ay - (face + t * (765.0 - face))) <= zs.SEAM_MARGIN
        margins[zi] = margins[zi] | (grown & ~floor & (ay >= face))      # never north of the corner: there stands the wall
        zone['objects'] = [o for o in zone['objects'] if o['kind'] != 'void'] + zs.void_pieces(floor | margins[zi])
    print(f"south-west corner: seam extended to y {face}, {n} Gloamfen edge cells now Greenmeadow's, tower in both neighbours")


def sw_corner_tower(world, city):
    zg = zs.zone_of(world, 0)
    zf = zs.zone_of(world, 3)
    wall_y = next(o['y'] + zg['shape']['T'][1] for o in zg['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG)
    wall_x = next(o['x'] + zf['shape']['T'][0] for o in zf['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG)
    city['objects'].append(dict(kind='tower', x=round(wall_x - TC[0], 2), y=round(wall_y - TC[1], 2), r=0, v=0, width=3.4, depth=3.4, color='#4a7a9a', label='', layout='skaldholm_east_wall'))


def trim_greenmeadow_flank(world):
    """Greenmeadow's wall used to run on past the city's east wall and turn north in a leg (the right-hand wing of the old L). It stops at the
    corner now: everything east of x 457 goes."""
    z = zs.zone_of(world, 0)
    T = z['shape']['T']
    gone = [o for o in z['objects'] if o['kind'] in ('rampart', 'tower') and o.get('layout') == TAG and o['x'] + T[0] > EAST_WALL_X + 1.0]
    z['objects'] = [o for o in z['objects'] if o not in gone]
    print(f'greenmeadow flank trimmed: {len(gone)} wall pieces east of the corner')
    return len(gone)


def east_wall(world, city):
    """The city's east wall: the Crags' (x 456.2, ends in a tower at y 727) straight on down to Greenmeadow's wall (y 757.7), in the city's own pieces,
    with a corner tower; the wing east of it is void. Nothing else of the city is walled by the city."""
    zc = zs.zone_of(world, 1)
    zg = zs.zone_of(world, 0)
    tc = [o for o in zc['objects'] if o['kind'] == 'tower' and o.get('layout') == TAG and abs(o['x'] + zc['shape']['T'][0] - 456.2) < .3 and o['y'] + zc['shape']['T'][1] > 720]
    assert tc, "the Crags' wall no longer ends in a tower at (456.2, 727)"
    gy = next(o['y'] + zg['shape']['T'][1] for o in zg['objects'] if o['kind'] == 'rampart' and o.get('layout') == TAG)
    x = round(456.2 - TC[0], 2)
    y0, y1 = round(tc[0]['y'] + zc['shape']['T'][1] - TC[1], 2), round(gy - TC[1], 2)
    y = y0 + 4.6
    n = 0
    while y < y1 - 3.4:
        city['objects'].append(dict(kind='rampart', x=x, y=round(y, 2), r=0, v=0, width=1.8, depth=5.8, color='#d7d3bc', label='', layout='skaldholm_east_wall'))
        y += 5.9
        n += 1
    city['objects'].append(dict(kind='tower', x=x, y=y1, r=0, v=0, width=3.4, depth=3.4, color='#4a7a9a', label='', layout='skaldholm_east_wall'))
    return n + 1


def quiet_lobe(world):
    """The wing is nobody's ground: the neighbours must not draw it as Skaldholm's cobbles; their edge band there is plain outer land."""
    for i in (0, 1):
        z = zs.zone_of(world, i)
        T = z['shape']['T']
        letter = chr(ord('A') + z['shape']['neighbours'].index(CITY))
        rows = [list(r) for r in z['shapeEdge']]
        for yy, row in enumerate(rows):
            for xx, ch in enumerate(row):
                if ch == letter and xx + T[0] >= EAST_WALL_X and EAST_WALL_Y0 - 2 <= yy + T[1] <= 760:
                    row[xx] = 'l'
        z['shapeEdge'] = [''.join(r) for r in rows]


def check_city(city, floor):
    """Everything stands on ground, and a flood fill over the collision reaches the doors, the stairs, the spawn, every NPC and the place."""
    import compact_atlas as ca
    on = lambda x, y: 0 <= int(y) < SIZE and 0 <= int(x) < SIZE and floor[int(y), int(x)]
    for key in ('npcs', 'places'):
        bad = [(o['id'], o['x'], o['y']) for o in city[key] if not on(o['x'], o['y'])]
        assert not bad, f'{key} off the ground: {bad}'
    assert on(city['spawn']['x'], city['spawn']['y'])
    assert on(city['city']['entry']['x'], city['city']['entry']['y'])
    prev = ca.connected(city)
    unreachable = []
    doors = {a['portal']: a for a in city['exitArches']}
    for kind, items in (('portal', city['portals']), ('npc', city['npcs']), ('place', city['places'])):
        for o in items:
            x, y = o['x'], o['y']
            if o.get('id') in doors:        # a door's portal stands at the arch line: three tiles inward is the street
                a = doors[o['id']]
                x, y = a['x'] - o['walk'][0] * 3.0, a['y'] - o['walk'][1] * 3.0
            if int(y) * SIZE + int(x) not in prev:
                unreachable.append((kind, o.get('id'), x, y))
    assert not unreachable, f'not reachable on foot from the spawn: {unreachable}'
    for o in city['npcs']:
        for a, b in zip(o.get('route', []), o.get('route', [])[1:]):
            assert on(*a) and on(*b), f"{o['id']}: route leaves the ground: {a} {on(*a)} {b} {on(*b)}"
            assert ca.clear(city, a, b, .3), f"{o['id']}: route {a}->{b} is blocked"


# ---- plan picture (read-only): python3 scripts/skaldholm_rebuild.py plan OUT.png ------------------------------------------
def plan(path):
    from PIL import Image, ImageDraw
    world = json.loads((zs.ROOT / 'world/map.txt').read_text())
    city = zs.zone_of(world, CITY)
    assert 'shape' in city, 'run sync-world / zone_shapes apply first'
    sc = 6
    im = Image.new('RGB', (SIZE * sc, SIZE * sc), (24, 24, 24))
    d = ImageDraw.Draw(im)
    for y, row in enumerate(city['shapeFloor']):
        for x, ch in enumerate(row):
            if ch == '#':
                d.rectangle([x * sc, y * sc, x * sc + sc - 1, y * sc + sc - 1], fill=(62, 92, 62))
    for r in city['roads']:
        if 'x0' in r:
            d.rectangle([r['x0'] * sc, r['y0'] * sc, r['x1'] * sc, r['y1'] * sc], fill=(130, 120, 100) if r['t'] == 1 else (160, 150, 120))
        else:
            rr = r.get('r', r.get('r1'))
            d.ellipse([(r['x'] - rr) * sc, (r['y'] - rr) * sc, (r['x'] + rr) * sc, (r['y'] + rr) * sc], fill=(150, 140, 110))
    col = {'house': (184, 116, 78), 'tree': (30, 110, 30), 'bush': (40, 130, 40), 'lamp': (255, 255, 0), 'tower': (255, 255, 255), 'rampart': (210, 210, 210)}
    for o in city['objects']:
        if o['kind'] == 'void':
            continue
        c = col.get(o['kind'], (200, 60, 200))
        if o.get('width'):
            d.rectangle([(o['x'] - o['width'] / 2) * sc, (o['y'] - o['depth'] / 2) * sc, (o['x'] + o['width'] / 2) * sc, (o['y'] + o['depth'] / 2) * sc], fill=c, outline=(0, 0, 0))
        else:
            rr = max(o.get('r', 1), .6)
            d.ellipse([(o['x'] - rr) * sc, (o['y'] - rr) * sc, (o['x'] + rr) * sc, (o['y'] + rr) * sc], fill=c)
    for n_ in city['npcs']:
        d.ellipse([n_['x'] * sc - 4, n_['y'] * sc - 4, n_['x'] * sc + 4, n_['y'] * sc + 4], fill=(0, 200, 255))
    for a in city['exitArches']:
        hw = a['halfWidth']
        if a['vertical']:
            d.line([a['x'] * sc, (a['y'] - hw) * sc, a['x'] * sc, (a['y'] + hw) * sc], fill=(255, 0, 255), width=4)
        else:
            d.line([(a['x'] - hw) * sc, a['y'] * sc, (a['x'] + hw) * sc, a['y'] * sc], fill=(255, 0, 255), width=4)
    for p in city['portals']:
        d.ellipse([p['x'] * sc - 5, p['y'] * sc - 5, p['x'] * sc + 5, p['y'] * sc + 5], outline=(255, 128, 0), width=2)
    im.save(path)
    print('plan ->', path)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'plan':
        plan(sys.argv[2])
    else:
        sys.exit(__doc__)
