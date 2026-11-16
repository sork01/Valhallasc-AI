"""Spawns at least R tiles from every seam (the shared border of a shaped zone with a neighbour that is crossed by walking).

Why: two frames of one seam draw the same world point from each side, and a spawn within about 20 tiles of the line is drawn on one side
only (tests/orrery-design-ui.cjs, tests/prism-design-ui.cjs). A design calls `clear_of_seams` once its spawns are placed: a spawn already
clear of every seam does not move, and each ordinary spawn that is too close moves to a cell that is clear, on the same land, off the
solid scenery and away from the other spawns. Sleepers and authored elites are NOT moved here (see `movable`). Deterministic: no random
stream is touched, so nothing else in the design changes.
"""
import math

import numpy as np

from greenmeadow_design import seg_field

CLEAR = 21.0      # tiles: the owner's rule, one more than the 20 the seam tests compare within


def seam_chains(zone):
    """The shared border runs of a shaped zone (every neighbour; the seams are cut from these)."""
    return [e['points'] for e in zone['shape']['edges'] if e['kind'] == 'shared']


def seam_distance(chains, xs, ys):
    best = np.full(np.shape(xs), 1e9)
    for c in chains:
        best = np.minimum(best, seg_field(c, xs, ys))
    return best


def clear_of_seams(slimes, zone, valid, free, n, r=CLEAR, sep=6.0, movable=None, anchor=None, pull=4.0, also=None, keep_off=()):
    """Move every ordinary spawn closer than `r` to a seam to a clear cell. `valid` is the design's own spawn mask (land, reach, road and
    reserve rules, hamlets and city excluded); `free(x, y)` says a spot is off the solid scenery. Returns [(kind, from, to)].

    `movable(s)` says which spawns may move at all: sleepers (ambush tags: dormant, drawn only once woken, and bound to their circle, place
    or quest), authored elites (their own clearance rules) and anything else the design pins stay where they are.
    `anchor` is (x, y) of a point whose distance a spawn keeps (the refuge, for families that live by distance from it): the new cell is the one
    with the lowest (move length + `pull` x change of that distance), so a family's mean distance, and the order of the families, hold.
    `also(s)` forces a movable spawn to move although it is clear of the seams, and `keep_off` is [(x, y, radius)] that no new cell may fall inside
    (the pocket round an elite that was moved)."""
    chains = seam_chains(zone)
    if not chains:
        return []
    ys, xs = np.mgrid[0:n, 0:n] + .5
    dist = seam_distance(chains, xs, ys)
    clear = valid & (dist >= r + .5)
    cells = np.argwhere(clear)
    cx, cy = cells[:, 1] + .5, cells[:, 0] + .5
    for kx, ky, kr in keep_off:
        out = np.hypot(cx - kx, cy - ky) >= kr
        cx, cy = cx[out], cy[out]
    moved = []
    for s in slimes:
        if movable is not None and not movable(s):
            continue
        if seam_distance(chains, np.array([s['x']]), np.array([s['y']]))[0] >= r and not (also is not None and also(s)):
            continue
        cost = np.hypot(cx - s['x'], cy - s['y'])
        if anchor is not None:
            cost = cost + pull * np.abs(np.hypot(cx - anchor[0], cy - anchor[1]) - math.hypot(s['x'] - anchor[0], s['y'] - anchor[1]))
        for k in np.argsort(cost, kind='stable'):
            x, y = float(cx[k]), float(cy[k])
            if not free(x, y):
                continue
            if any(t is not s and math.hypot(x - t['x'], y - t['y']) < sep for t in slimes):
                continue
            if seam_distance(chains, np.array([x]), np.array([y]))[0] < r:
                continue
            moved.append((s['kind'], (s['x'], s['y']), (x, y)))
            s['x'], s['y'] = x, y
            break
        else:
            raise AssertionError(f"no clear cell for {s['kind']} at ({s['x']}, {s['y']})")
    return moved
