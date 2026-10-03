#!/usr/bin/env python3
"""Writes Rimeveil Glacier (zone 2, levels 10-15) and its gate in the Emberfall Crags into world/map.txt.

Layout: a 128x128 glacier built as a spiral. Four rings of ice walls (radius 48, 37, 26, 15 around the
centre) each have one gap, alternating south / north / south / north, so the way in winds round the
mountain half a turn per band: Rime Crabs on the outer shelf, Frostfang Wolves, Glacier Yetis, and
the Rime Wyrms in the summit bowl. Rimeward Camp (safe quest hub, five NPCs, thirteen quests) sits
south of the outer wall, beside the gate back to the Crags.

The Crags gain a stone gate at the north end of their trail; golem spawns and scenery that stood in
front of it move clear. Re-running replaces zone 2 and that gate and leaves the rest of the map alone
(generate_crags.py keeps zones 2 and up when it rebuilds zone 1, but loses the Crags gate: run this again).
Use --hub-only to update the camp on the existing map without rebuilding the glacier.
Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
"""
import argparse
import json
import math
from pathlib import Path
import random

import progression_quests

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth
NAME = 'Rimeveil Glacier'
SIZE = 128
CENTER = (64.0, 52.0)
RINGS = [48.0, 37.0, 26.0, 15.0]                 # outer wall first
GAPS = [90.0, -90.0, 90.0, -90.0]                # degrees: 90 = south, -90 = north (y runs down)
WALL_R = 1.35                                    # wall disc radius; discs overlap into a solid ridge
GAP_HALF = 4.3                                   # half width of every gap
ARRIVAL = (64.0, 118.5)                          # where the Crags gate drops you
RETURN_GATE = (64.0, 123.0)                      # the way back
CRAGS_GATE = (56.0, 5.5)                         # at the north end of the Crags trail
CRAGS_ARRIVAL = (56.0, 10.0)
CRAGS_START = (48.0, 86.5)                       # the Crags arrival camp, for the reachability check
BANDS = [  # kind, count, (outer ring index, inner ring index or None for the summit bowl)
    ('crab', 9, (0, 1)),
    ('wolf', 8, (1, 2)),
    ('yeti', 6, (2, 3)),
    ('wyrm', 4, (3, None)),
]


def quest_hub():
    """Rimeward Camp is a safe staging camp south of the outer ice wall."""
    def npc(id, name, role, x, y, color, dialogue, offers=None, buys=False):
        return dict(id=id, name=name, role=role, x=x, y=y, color=color,
                    dialogue=dialogue, offers=offers or [], buys=buys)

    npcs = [
        npc('rime_warden', 'Warden Halvard', 'Glacier warden', 60, 114, '#6f93b8',
            'Welcome to Rimeward Camp. The glacier winds up in four rings, each with a single gap on the far side from the last. Crabs on the shelf, wolves in the second ring, yetis in the third, and something old in the summit bowl. Report back here.'),
        npc('rime_tracker', 'Huntress Brynja', 'Tracker', 67, 110.5, '#a89678',
            'Walk the packed-snow trail and the gaps find you. I need the shelf crabs thinned and the wolf packs broken before the sledges can climb. Do not stand still in the gaps; everything wakes there.'),
        npc('rime_healer', 'Brother Eirik', 'Camp healer', 69, 116, '#d3deea',
            'Warm yourself inside the camp; nothing hostile may cross the line. My blessing is free, and I sell Health Potions for the climb. The yetis in the third ring have been tearing up our cairns.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_mana_potion', label='Buy Mana Potion · 100 mana instantly', cost=30, item='mana_potion', tiered=True),
             dict(id='buy_health_potion', label='Buy Health Potion · 100 HP instantly', cost=30, item='health_potion', tiered=True)]),
        npc('rime_trader', 'Trader Skadi', 'Supplies & bounties', 59, 118, '#b88f5a',
            'Bring me shells, pelts, horns and scales and I will pay for them. I sell stew and satchels, and my patrol contracts never run out.',
            [dict(id='buy_traveler_stew', label="Buy Traveler's Stew · 100 HP and mana over 8 s", cost=12, item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel · 6 extra bag slots', cost=500, bag='linen_satchel')], buys=True),
        npc('rime_loremaster', 'Loremaster Ylva', 'Glacier scholar', 73, 112, '#a58cc4',
            'The ice here is older than the Crags and it is not quiet. I chart every footprint I can reach. Something coils in the summit bowl and breathes the cold out through the rings. Help me learn what it is.'),
    ]

    def kill(kind, count, label):
        return dict(kind='kill', target=kind, label=label, count=count)

    def quest(id, title, npc, description, objectives, level, gold, requires=None, repeatable=False):
        # Recommended level; the XP reward is 10% of what that level needs (server test enforces it).
        return dict(id='rime_' + id, title=title, npc='rime_' + npc, description=description,
                    objectives=objectives, level=level, rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold,
                    requires='rime_' + requires if requires else None, repeatable=repeatable)

    def talk(id, name):
        return dict(kind='talk', target='rime_' + id, label='Speak to ' + name, count=1)

    quests = [
        quest('welcome', 'Into the White', 'warden',
              'Meet Huntress Brynja, Brother Eirik, Trader Skadi and Loremaster Ylva in Rimeward Camp, then report to Warden Halvard.',
              [talk('tracker', 'Huntress Brynja'), talk('healer', 'Brother Eirik'),
               talk('trader', 'Trader Skadi'), talk('loremaster', 'Loremaster Ylva')], 10, 200),
        quest('crabs', 'Shells on the Ice', 'tracker',
              'Pass the first gap in the outer wall and defeat five Rime Crabs on the shelf. Return to Brynja.',
              [kill('crab', 5, 'Defeat Rime Crabs')], 10, 220, 'welcome'),
        quest('crab_sweep', 'Crack the Shoreline', 'tracker',
              'The shelf crabs keep breeding under the ice. Defeat ten of them so the sledge road stays open.',
              [kill('crab', 10, 'Defeat Rime Crabs')], 11, 250, 'crabs'),
        quest('wolves', 'Howls in the Whiteout', 'tracker',
              'Through the north gap the Frostfang Wolves hunt in packs. Defeat four and report to Brynja.',
              [kill('wolf', 4, 'Defeat Frostfang Wolves')], 12, 300, 'crabs'),
        quest('wolf_pack', 'Break the Pack', 'warden',
              'Defeat eight Frostfang Wolves in the second ring so the scouts can cross it alive.',
              [kill('wolf', 8, 'Defeat Frostfang Wolves')], 12, 340, 'wolves'),
        quest('thaw', 'Thaw for the Lost', 'healer',
              'Lost climbers lie frozen in the lower rings. Clear six Rime Crabs and four Frostfang Wolves from around them.',
              [kill('crab', 6, 'Defeat Rime Crabs'), kill('wolf', 4, 'Defeat Frostfang Wolves')], 13, 380, 'wolves'),
        quest('yetis', 'Footprints the Size of Barrels', 'loremaster',
              'Glacier Yetis roam the third ring, past the southern gap. Defeat three and bring Ylva their count.',
              [kill('yeti', 3, 'Defeat Glacier Yetis')], 13, 400, 'wolves'),
        quest('yeti_herd', 'Thin the Herd', 'healer',
              'The yetis have torn up three cairns. Defeat six Glacier Yetis and Eirik will rebuild them.',
              [kill('yeti', 6, 'Defeat Glacier Yetis')], 14, 450, 'yetis'),
        quest('wyrm', 'The Thing in the Summit', 'loremaster',
              'Cross the last gap into the summit bowl and defeat two Rime Wyrms. Ylva needs to know whether the cold stops.',
              [kill('wyrm', 2, 'Defeat Rime Wyrms')], 15, 500, 'yetis'),
        quest('wyrm_hunt', 'Wyrmslayer', 'warden',
              'Halvard wants the bowl cleared for good. Defeat four Rime Wyrms and report back.',
              [kill('wyrm', 4, 'Defeat Rime Wyrms')], 15, 550, 'wyrm'),
        quest('vanguard', 'Heart of the Glacier', 'warden',
              'Prove you can hold the whole spiral: defeat two of every glacier monster and report to Halvard.',
              [kill(kind, 2, 'Defeat ' + label) for kind, label in
               [('crab', 'Rime Crabs'), ('wolf', 'Frostfang Wolves'), ('yeti', 'Glacier Yetis'), ('wyrm', 'Rime Wyrms')]],
              15, 600, 'wyrm'),
        quest('bounty', 'Rimeward Patrol', 'trader',
              'Defeat ten enemies anywhere on Rimeveil Glacier and return to Skadi. This patrol can be repeated.',
              [kill('any', 10, 'Defeat glacier enemies')], 11, 220, 'welcome', True),
        quest('supply_route', 'Keep the Sledge Road Open', 'trader',
              'Clear three Rime Crabs and three Frostfang Wolves for the next sledge. Skadi offers this contract again after each turn-in.',
              [kill('crab', 3, 'Defeat Rime Crabs'), kill('wolf', 3, 'Defeat Frostfang Wolves')], 12, 280, 'crabs', True),
    ]
    quests += progression_quests.for_zone('Rimeveil Glacier')
    objects = [
        dict(kind='tent', x=54, y=112, r=1.5, width=3, depth=2.4, color='#4f7fa8', label='Command'),
        dict(kind='tent', x=70, y=110, r=1.5, width=3, depth=2.4, color='#7a6fa3', label='Infirmary'),
        dict(kind='stall', x=73, y=116, r=1, width=2, depth=1.5, color='#a87a45', label='Supplies'),
        dict(kind='campfire', x=64, y=114, r=.65, v=0),
        dict(kind='noticeboard', x=56, y=119.5, r=.4, width=1.3, depth=.4, label='Rimeward Camp'),
        dict(kind='lamp', x=54, y=117, r=.25, v=0),
        dict(kind='lamp', x=74, y=119, r=.25, v=0),
    ]
    city = dict(name='Rimeward Camp', x0=52, x1=76, y0=108, y1=121, plaza=dict(x=64, y=114), radius=3)
    return npcs, quests, objects, city


def polar(radius, degrees):
    a = math.radians(degrees)
    return CENTER[0] + radius * math.cos(a), CENTER[1] + radius * math.sin(a)


def ring_wobble(k, degrees):
    """A little irregularity so the walls are not perfect circles."""
    return .55 * math.sin(math.radians(degrees) * 3 + k * 1.7)


def gap_point(k):
    return polar(RINGS[k], GAPS[k])


def dist_to_trail(trail, x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(trail, trail[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return best


def build_trail():
    """The packed-snow trail: camp, outer gap, then half a turn round each band, gap to gap."""
    trail = [RETURN_GATE, (64.0, 112.0), gap_point(0)]
    start = GAPS[0]
    for k in range(3):
        r = (RINGS[k] + RINGS[k + 1]) / 2
        sweep = GAPS[k + 1]
        # Same sense of rotation all the way in: degrees only decrease.
        end = sweep if sweep < start else sweep - 360
        steps = max(8, int((start - end) / 8))
        for i in range(steps + 1):
            deg = start + (end - start) * i / steps
            trail.append(polar(r, deg))
        trail.append(gap_point(k + 1))
        start = end
    trail.append(CENTER)
    return [(round(x, 1), round(y, 1)) for x, y in trail]


def build(rng):
    objects = []
    gaps = [gap_point(k) for k in range(4)]
    for k, radius in enumerate(RINGS):
        circumference = 2 * math.pi * radius
        n = int(circumference / 1.7)
        for i in range(n):
            deg = 360 * i / n
            x, y = polar(radius + ring_wobble(k, deg), deg)
            if math.hypot(x - gaps[k][0], y - gaps[k][1]) < GAP_HALF:
                continue
            objects.append({'kind': 'ice', 'x': round(x, 2), 'y': round(y, 2), 'r': WALL_R, 'v': rng.randrange(4)})
    # The return gate: two posts, drawn as part of the gate itself.
    for dx in (-1.5, 1.5):
        objects.append({'kind': 'post', 'x': RETURN_GATE[0] + dx, 'y': RETURN_GATE[1], 'r': 0.45, 'v': 0})
    npcs, quests, camp_objects, city = quest_hub()
    objects += camp_objects
    # The summit: a crown of ice spires round the middle of the bowl.
    for i in range(8):
        x, y = polar(6.5, i * 45 + 20)
        objects.append({'kind': 'spire', 'x': round(x, 2), 'y': round(y, 2), 'r': .55, 'v': i % 4})
    trail = build_trail()

    def near_gap(x, y, d):
        return any(math.hypot(x - gx, y - gy) < d for gx, gy in gaps)

    spawns = []
    for kind, count, (outer, inner) in BANDS:
        for _ in range(count):
            for _ in range(6000):
                if inner is None:
                    deg, radius = rng.uniform(-180, 180), math.sqrt(rng.uniform(0, 1)) * (RINGS[3] - 3.5)
                else:
                    deg, radius = rng.uniform(-180, 180), rng.uniform(RINGS[inner] + 3.4, RINGS[outer] - 3.4)
                x, y = polar(radius, deg)
                if (all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2.3 for o in objects)
                        and all(math.hypot(x - s['x'], y - s['y']) > 7 for s in spawns)
                        and not near_gap(x, y, 8.5)):
                    spawns.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind})
                    break
            else:
                raise SystemExit(f'no room for a {kind}')
    # Scenery: dense pines in the outskirts, fewer boulders, shrubs and ice crystals inside the bands.
    def radius_of(x, y):
        return math.hypot(x - CENTER[0], y - CENTER[1])

    decor = [  # kind, count, size, region test
        ('tree', 130, .42, lambda x, y: radius_of(x, y) > RINGS[0] + 4),
        ('rock', 36, .4, lambda x, y: radius_of(x, y) > RINGS[0] + 3),
        ('bush', 26, .3, lambda x, y: radius_of(x, y) > RINGS[0] + 3),
        ('spire', 14, .5, lambda x, y: radius_of(x, y) > RINGS[0] + 3),
        ('rock', 8, .4, lambda x, y: RINGS[1] + 3 < radius_of(x, y) < RINGS[0] - 3),
        ('bush', 6, .3, lambda x, y: RINGS[1] + 3 < radius_of(x, y) < RINGS[0] - 3),
        ('spire', 5, .5, lambda x, y: RINGS[1] + 3 < radius_of(x, y) < RINGS[0] - 3),
        ('tree', 5, .42, lambda x, y: RINGS[1] + 3 < radius_of(x, y) < RINGS[0] - 3),
        ('rock', 7, .4, lambda x, y: RINGS[2] + 3 < radius_of(x, y) < RINGS[1] - 3),
        ('bush', 5, .3, lambda x, y: RINGS[2] + 3 < radius_of(x, y) < RINGS[1] - 3),
        ('spire', 5, .5, lambda x, y: RINGS[2] + 3 < radius_of(x, y) < RINGS[1] - 3),
        ('rock', 5, .4, lambda x, y: RINGS[3] + 3 < radius_of(x, y) < RINGS[2] - 3),
        ('bush', 4, .3, lambda x, y: RINGS[3] + 3 < radius_of(x, y) < RINGS[2] - 3),
        ('spire', 4, .5, lambda x, y: RINGS[3] + 3 < radius_of(x, y) < RINGS[2] - 3),
        ('rock', 4, .4, lambda x, y: 9 < radius_of(x, y) < RINGS[3] - 3.5),
        ('bush', 3, .3, lambda x, y: 9 < radius_of(x, y) < RINGS[3] - 3.5),
    ]
    for kind, count, size, inside in decor:
        placed = 0
        for _ in range(30000):
            if placed == count:
                break
            x, y = rng.uniform(2, SIZE - 2), rng.uniform(2, SIZE - 2)
            if (not inside(x, y) or dist_to_trail(trail, x, y) < 2.4
                    or (city['x0'] - 3 < x < city['x1'] + 3 and city['y0'] - 3 < y < city['y1'] + 3)
                    or math.hypot(x - ARRIVAL[0], y - 120) < 7
                    or near_gap(x, y, 6)
                    or any(math.hypot(x - o['x'], y - o['y']) < o['r'] + size + 1.5 for o in objects)
                    or any(math.hypot(x - s['x'], y - s['y']) < 2.8 for s in spawns)):
                continue
            objects.append({'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': size, 'v': rng.randrange(4)})
            placed += 1
        assert placed == count, f'only {placed} {kind}'
    return {
        'name': NAME, 'theme': 'frost', 'size': SIZE, 'levels': [10, 15],
        'spawn': {'x': ARRIVAL[0], 'y': ARRIVAL[1]},
        'paths': [[[x, y] for x, y in trail]],
        'objects': objects, 'slimes': spawns, 'npcs': npcs, 'quests': quests, 'city': city,
        'portals': [{'id': 'crags_gate', 'name': 'the Crags Gate', 'x': RETURN_GATE[0], 'y': RETURN_GATE[1], 'r': 1.1,
                     'to': 1, 'tx': CRAGS_ARRIVAL[0], 'ty': CRAGS_ARRIVAL[1]}],
    }


def unreachable(zone, start, targets):
    """Grid flood fill with the player's radius: every target must connect to the start."""
    size, step, margin = zone['size'], .5, .62
    n = int(size / step)
    blocked = [[False] * n for _ in range(n)]
    for j in range(n):
        for i in range(n):
            x, y = (i + .5) * step, (j + .5) * step
            if x < .7 or y < .7 or x > size - .7 or y > size - .7:
                blocked[j][i] = True
                continue
            blocked[j][i] = any(
                (abs(x - o['x']) < o['width'] / 2 + margin and abs(y - o['y']) < o['depth'] / 2 + margin)
                if o.get('width') and o.get('depth') else math.hypot(x - o['x'], y - o['y']) < o['r'] + margin
                for o in zone['objects'])
    seen = {(int(start[0] / step), int(start[1] / step))}
    queue = list(seen)
    for i, j in queue:
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < n and (a, b) not in seen and not blocked[b][a]:
                seen.add((a, b))
                queue.append((a, b))
    return [t for t in targets if (int(t[0] / step), int(t[1] / step)) not in seen]


def glacier_targets(zone):
    return ([(s['x'], s['y'], s['kind']) for s in zone['slimes']] + [(n['x'], n['y'], n['id']) for n in zone['npcs']]
            + [(RETURN_GATE[0], RETURN_GATE[1] - 2, 'gate'), (CENTER[0], CENTER[1], 'summit')])


def add_crags_gate(meadow, rng):
    """Remove an earlier gate, clear the ground in front of the new one, then add posts, path and portal."""
    crags = meadow['zones'][0]
    assert crags['name'] == 'Emberfall Crags', 'zone 1 must be the Crags'
    gate_x = [CRAGS_GATE[0] - 1.5, CRAGS_GATE[0] + 1.5]
    crags['objects'] = [o for o in crags['objects'] if not (o['kind'] == 'post' and abs(o['y'] - CRAGS_GATE[1]) < .01)]
    crags['portals'] = [p for p in crags['portals'] if p['id'] != 'rimeveil_gate']
    crags['paths'][0] = [pt for pt in crags['paths'][0] if pt != [56, 6.2]]
    # Scenery on the gate or its approach goes.
    crags['objects'] = [o for o in crags['objects'] if o['kind'] in ('lava', 'post') or not (
        math.hypot(o['x'] - CRAGS_GATE[0], o['y'] - CRAGS_GATE[1]) < o['r'] + 2.4
        or math.hypot(o['x'] - CRAGS_ARRIVAL[0], o['y'] - CRAGS_ARRIVAL[1]) < o['r'] + 2.4)]
    for x in gate_x:
        crags['objects'].append({'kind': 'post', 'x': x, 'y': CRAGS_GATE[1], 'r': 0.45, 'v': 0})
    crags['paths'][0].append([56, 6.2])
    crags['portals'].append({'id': 'rimeveil_gate', 'name': 'the Rimeveil Gate', 'x': CRAGS_GATE[0], 'y': CRAGS_GATE[1], 'r': 1.1,
                             'to': 2, 'tx': ARRIVAL[0], 'ty': ARRIVAL[1]})
    # Golems standing in front of the gate move to the nearest clear spot 10+ units from the arrival.
    moved = 0
    for s in crags['slimes']:
        if math.hypot(s['x'] - CRAGS_ARRIVAL[0], s['y'] - CRAGS_ARRIVAL[1]) < 10:
            ox, oy = s['x'], s['y']
            best = None
            for _ in range(4000):
                x, y = ox + rng.uniform(-12, 12), oy + rng.uniform(-12, 12)
                if (math.hypot(x - CRAGS_ARRIVAL[0], y - CRAGS_ARRIVAL[1]) > 10.5 and 6 < y < 18 and 5 < x < 91
                        and all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2.6 for o in crags['objects'])
                        and all(math.hypot(x - t['x'], y - t['y']) > 7 for t in crags['slimes'] if t is not s)):
                    d = math.hypot(x - ox, y - oy)
                    if best is None or d < best[0]:
                        best = (d, x, y)
            assert best, 'no clear spot for a displaced spawn'
            s['x'], s['y'] = round(best[1], 2), round(best[2], 2)
            moved += 1
    missing = unreachable(crags, CRAGS_START, [(CRAGS_ARRIVAL[0], CRAGS_ARRIVAL[1], 'arrival'), (CRAGS_GATE[0], CRAGS_GATE[1] + 2, 'gate')]
                          + [(s['x'], s['y'], s['kind']) for s in crags['slimes']])
    if missing:
        raise SystemExit(f'Crags: unreachable from the camp: {missing}')
    return moved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hub-only', action='store_true', help='update Rimeward Camp without rebuilding the glacier')
    args = parser.parse_args()
    raw = PATH.read_text()
    meadow = json.loads(raw)
    assert json.dumps(meadow, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    if args.hub_only:
        zone = next(z for z in meadow['zones'] if z['name'] == NAME)
        npcs, quests, objects, city = quest_hub()
        zone['objects'] = [o for o in zone['objects']
                           if not (city['x0'] - 2 < o['x'] < city['x1'] + 2 and city['y0'] - 2 < o['y'] < city['y1'] + 2)] + objects
        zone.update(npcs=npcs, quests=quests, city=city)
        missing = unreachable(zone, ARRIVAL, glacier_targets(zone))
        if missing:
            raise SystemExit(f'unreachable from the arrival point: {missing}')
        PATH.write_text(json.dumps(meadow, indent=2) + '\n')
        print(f'Updated Rimeward Camp: {len(npcs)} NPCs, {len(quests)} quests. Terrain and enemy spawns preserved. Now run node scripts/sync-world.cjs')
        return
    later = meadow['zones'][2:]       # zones after the glacier (Gloamfen) survive a rebuild; re-run generate_gloamfen.py for its gate
    meadow['zones'] = [z for z in meadow['zones'][:2] if z['name'] != NAME]
    moved = add_crags_gate(meadow, random.Random(20261003))   # its own stream: it only draws numbers on the first run
    zone = build(random.Random(20261004))
    missing = unreachable(zone, ARRIVAL, glacier_targets(zone))
    if missing:
        raise SystemExit(f'unreachable from the arrival point: {missing}')
    meadow['zones'].append(zone)
    assert len(meadow['zones']) == 2, 'Rimeveil must be zone 2'
    meadow['zones'] += later
    PATH.write_text(json.dumps(meadow, indent=2) + '\n')
    kinds = {}
    for s in zone['slimes']:
        kinds[s['kind']] = kinds.get(s['kind'], 0) + 1
    print(f"Wrote zone 2 {zone['name']}: {len(zone['objects'])} objects, spawns {kinds}; Crags gate added, {moved} golem spawn(s) moved. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
