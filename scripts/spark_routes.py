#!/usr/bin/env python3
"""Spark Travel links, rebuilt from the finished geography. Runs last in sync-world.

Earlier generators and zone designs each wrote `travelLinks` for the layout they knew
(a line of hubs, then one zone's seams at a time). This overlay replaces every list
with one rule, so the network always matches the crossings that exist now:

  * two stations in the same zone are linked (a straight flight over the zone);
  * for every crossing between two zones, every station of either zone is linked to
    the station nearest the crossing on the other side, and the two zones' main hubs
    are linked to each other.

A leg is flown station -> crossing -> station, so every link has a crossing by
construction. The server picks the fastest route over these links (travel.rs).

  spark_routes.py            rewrite world/map.txt
  spark_routes.py --check    fail when map.txt is not already in this state
  spark_routes.py --report   print the network and how direct its routes are
"""
import heapq
import json
import math
import sys
from pathlib import Path

MAP = Path(__file__).resolve().parents[1] / 'world/map.txt'


def stations(zones):
    return {i: [n for n in z.get('npcs', []) if n.get('travelStop')]
            for i, z in enumerate(zones) if any(n.get('travelStop') for n in z.get('npcs', []))}


def hub(zone, mine):
    """The station of the zone's own city; a zone with one station has no other choice."""
    city = zone.get('city')
    inside = [n for n in mine if city and city['x0'] <= n['x'] <= city['x1'] and city['y0'] <= n['y'] <= city['y1']]
    return inside[0] if inside else mine[0] if len(mine) == 1 else None


def crossings(zones, by_zone, i, j):
    return [p for p in zones[i]['portals'] if p['to'] == j and not p.get('after_clear')]


def links(zones):
    by_zone = stations(zones)
    pairs = set()
    for mine in by_zone.values():
        pairs |= {(a['id'], b['id']) for a in mine for b in mine if a['id'] < b['id']}
    for i, mine in by_zone.items():
        for j, theirs in by_zone.items():
            if i == j:
                continue
            for p in crossings(zones, by_zone, i, j):
                # A one-way door is no flight path: the return leg needs its own crossing.
                if not crossings(zones, by_zone, j, i):
                    continue
                b = min(theirs, key=lambda n: (math.hypot(n['x'] - p['tx'], n['y'] - p['ty']), n['id']))
                # Every station of this zone reaches the far side's nearest station in one leg
                # (the other direction of the loop does the same from the far side).
                pairs |= {tuple(sorted((n['id'], b['id']))) for n in mine}
                ha, hb = hub(zones[i], mine), hub(zones[j], theirs)
                if ha and hb:
                    pairs.add(tuple(sorted((ha['id'], hb['id']))))
    return by_zone, pairs


def apply(world):
    zones = [world] + world.get('zones', [])
    by_zone, pairs = links(zones)
    order = {n['id']: (i, k) for i, mine in by_zone.items() for k, n in enumerate(mine)}
    for mine in by_zone.values():
        for n in mine:
            n['travelLinks'] = sorted((b if a == n['id'] else a for a, b in pairs if n['id'] in (a, b)),
                                      key=order.get)
    return len(order), len(pairs)


def leg(zones, where, a, b):
    """Flight length of one leg in tiles, as travel.rs flies it."""
    (za, na), (zb, nb) = where[a], where[b]
    if za == zb:
        return math.hypot(na['x'] - nb['x'], na['y'] - nb['y'])
    return min((math.hypot(na['x'] - p['x'], na['y'] - p['y']) + math.hypot(p['tx'] - nb['x'], p['ty'] - nb['y'])
                for p in zones[za]['portals'] if p['to'] == zb and not p.get('after_clear')), default=None)


def fastest(zones, where, graph, start):
    best, queue = {start: (0., 0)}, [(0., 0, start)]
    while queue:
        length, legs, at = heapq.heappop(queue)
        if (length, legs) > best[at]:
            continue
        for other in graph[at]:
            step = leg(zones, where, at, other)
            if step is not None and (length + step, legs + 1) < best.get(other, (math.inf, 0)):
                best[other] = (length + step, legs + 1)
                heapq.heappush(queue, (length + step, legs + 1, other))
    return best


def report(world):
    zones = [world] + world.get('zones', [])
    by_zone = stations(zones)
    where = {n['id']: (i, n) for i, mine in by_zone.items() for n in mine}
    graph = {id_: [l for l in n['travelLinks']] for id_, (_, n) in where.items()}
    # The yardstick: a network where every pair of stations in neighbouring zones is linked.
    dense = {id_: set(l) for id_, l in graph.items()}
    for i, mine in by_zone.items():
        for j, theirs in by_zone.items():
            if i != j and crossings(zones, by_zone, i, j) and crossings(zones, by_zone, j, i):
                for a in mine:
                    dense[a['id']] |= {b['id'] for b in theirs}
    ratios, legs, missing = [], [], 0
    for a in where:
        ours, ideal = fastest(zones, where, graph, a), fastest(zones, where, dense, a)
        for b in where:
            if a == b:
                continue
            if b not in ours:
                missing += 1
                continue
            ratios.append((ours[b][0] / max(ideal[b][0], 1e-9), a, b))
            legs.append(ours[b][1])
    ratios.sort()
    print(f'{len(where)} stations, {sum(map(len, graph.values())) // 2} links, {missing} unreachable pairs')
    print(f'legs: mean {sum(legs) / len(legs):.2f}, most {max(legs)}')
    print('flight length against a fully linked network: '
          f'median {ratios[len(ratios) // 2][0]:.3f}, 95% {ratios[len(ratios) * 95 // 100][0]:.3f}, worst {ratios[-1][0]:.3f} ({ratios[-1][1]} -> {ratios[-1][2]})')


def main():
    world = json.loads(MAP.read_text())
    if '--report' in sys.argv:
        return report(world)
    before = json.dumps(world, indent=2, ensure_ascii=False) + '\n'
    count, pairs = apply(world)
    after = json.dumps(world, indent=2, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        assert before == after, 'world/map.txt has stale Spark Travel links: run scripts/spark_routes.py'
    else:
        MAP.write_text(after)
    print(f'Spark Travel: {count} stations, {pairs} links')


if __name__ == '__main__':
    main()
