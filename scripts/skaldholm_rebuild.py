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

TC = (352, 590)                 # city tile = atlas tile - TC
SIZE = 168
STRIP = (38.5, 123.5)           # old x range that stays rigid (85 wide: the north part of the L)
OLD_Y = (13.0, 139.5)
ODX, ODY = 331.5 - TC[0], 587.0 - TC[1]     # old city frame -> city frame for the strip
NEIGHBOURS = (0, 1, 2, 3)       # Greenmeadow, Crags, Rimeveil, Gloamfen
CITY = 4
SIDE = zs.SIDE / 'preshape-04.txt'
TAG = zs.TAG


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
    return (along >= 0.5) & (along <= 6.2) & (np.abs(across) <= hw + 1.0)


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
        walls = [o for o in z['objects'] if o['kind'] in ('rampart', 'tower') and o.get('layout') == TAG]
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
        back['x'], back['y'] = round(carch['x'] - wx * 3.0, 2), round(carch['y'] - wy * 3.0, 2)
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
                q['route'] = [list(mv(*p)) for p in npc['route']]
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
        p1 = [round(a['x'] + wx * 18, 2), round(a['y'] + wy * 18, 2)]
        ents.append(dict(id=back['id'], portal=back['id'], points=[p0, p1], axis='y' if wy else 'x', street=a['x'] if wy else a['y'],
                         width=7.0 if a['halfWidth'] > 5 else 4.0, opening={k: a[k] for k in ('x', 'y', 'vertical', 'halfWidth', 'towers', 'portal', 'name')}))
        paths.append([[round(a['x'] - wx * 5.5, 2), round(a['y'] - wy * 5.5, 2)], p1])
    city['cityEntrances'] = ents
    city['paths'] = paths
    city['atlasPaths'] = copy.deepcopy(paths)


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
