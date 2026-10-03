#!/usr/bin/env python3
"""Writes the Emberfall Crags (zone 1) and its gate into world/map.txt, then checks it.

Layout: four lava rivers cross a 96x96 map, each with one ford, so the way north zigzags between
difficulty bands (south = Cinder Wisps, then Magma Spiders, Ash Wraiths, Basalt Golems). The meadow
gains a stone gate at the end of its north road; two blue-slime spawns that stood in front of it
move clear. Re-running replaces zone 1 and the gate; world/map.txt stays the source of truth, so
hand edits made after running this script are lost on the next run. Seeded, so the output is stable.
Use --hub-only to update the camp on the existing map without rebuilding the surrounding layout.
Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
"""
import argparse
import json
import spark_travel
import math
from pathlib import Path
import random

import mercenary_offers as mo
import progression_quests

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth
SIZE = 96
ARRIVAL = (48.0, 86.5)             # where the meadow gate drops you
RETURN_GATE = (48.0, 91.0)         # the way back
MEADOW_GATE = (54.0, 9.0)
MEADOW_ARRIVAL = (54.0, 13.5)
# (centre y, wobble, wobble phase, ford centre x): each river runs the whole width but for one ford.
RIVERS = [(68, 2.0, 0.0, 20), (52, 2.0, 1.0, 74), (36, 2.0, 2.0, 12), (20, 2.0, 3.0, 82)]
FORD = 4.2                         # half width of every ford
BANDS = [  # kind, count, y range
    ('wisp', 8, (54, 66)),
    ('spider', 7, (38, 50)),
    ('wraith', 6, (22, 34)),
    ('golem', 5, (6, 18)),
]


def quest_hub():
    """Cinderwatch is a safe staging camp south of the first lava river."""
    def npc(id, name, role, x, y, color, dialogue, offers=None, buys=False):
        return dict(id=id, name=name, role=role, x=x, y=y, color=color,
                    dialogue=dialogue, offers=offers or [], buys=buys)

    npcs = [
        npc('crags_captain', 'Captain Sera', 'Cinderwatch commander', 44, 82, '#b66c50',
            'Welcome to Cinderwatch Camp. Meet our crew, then push north through the lava fords. Wisps haunt the lowlands; spiders, wraiths and golems guard the higher crags. Return here to report your victories. '
            'No partner for the Cinderlord? Once you have taken that quest I can hire you a sword-arm of any class for 250 gold, who will fight beside you in your party until the job is done.',
            mo.offers()),
        npc('crags_scout', 'Scout Kael', 'Trail scout', 51, 78.5, '#79916d',
            'Follow the winding ash trail through each ford. I need help clearing Cinder Wisps and Magma Spiders before our supply runners can pass.'),
        npc('crags_healer', 'Sister Iona', 'Camp healer', 53, 84, '#c8b9d3',
            'Rest within the camp; enemies cannot enter. My blessing is free, and I sell Health Potions for the climb. The Ash Wraiths beyond the second ford must be laid to rest.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_mana_potion', label='Buy Mana Potion · 100 mana instantly', cost=30, item='mana_potion', tiered=True),
             dict(id='buy_health_potion', label='Buy Health Potion · 100 HP instantly', cost=30, item='health_potion', tiered=True)]),
        npc('crags_supplier', 'Quartermaster Dain', 'Supplies & bounties', 43, 86, '#b69a64',
            'Bring me materials or spare gear from the Crags. I buy loot and sell stew and satchels. Our recurring patrol contracts keep the expedition supplied.',
            [dict(id='buy_traveler_stew', label="Buy Traveler's Stew · 100 HP and mana over 8 s", cost=12, item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel · 6 extra bag slots', cost=500, bag='linen_satchel')], buys=True),
    ]
    def kill(kind, count, label):
        return dict(kind='kill', target=kind, label=label, count=count)

    def quest(id, title, npc, description, objectives, level, gold, requires=None, repeatable=False):
        # Recommended level; the XP reward is 10% of what that level needs (server test enforces it).
        return dict(id='crags_' + id, title=title, npc='crags_' + npc, description=description,
                    objectives=objectives, level=level, rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold,
                    requires='crags_' + requires if requires else None, repeatable=repeatable)

    quests = [
        quest('welcome', 'A Foothold in the Ash', 'captain',
              'Meet Scout Kael, Sister Iona and Quartermaster Dain in Cinderwatch Camp, then report to Captain Sera.',
              [dict(kind='talk', target='crags_' + id, label='Speak to ' + name, count=1)
               for id, name in [('scout', 'Scout Kael'), ('healer', 'Sister Iona'), ('supplier', 'Quartermaster Dain')]], 5, 40),
        quest('wisps', 'Lights Along the Ford', 'scout',
              'Cross the first lava ford and defeat four Cinder Wisps in the southern lowlands. Return to Kael.',
              [kill('wisp', 4, 'Defeat Cinder Wisps')], 5, 65, 'welcome'),
        quest('wisp_sweep', 'Quench the Cinders', 'scout',
              'Kael needs a thorough sweep of the lowlands. Defeat eight Cinder Wisps and return to camp.',
              [kill('wisp', 8, 'Defeat Cinder Wisps')], 6, 90, 'wisps'),
        quest('spiders', 'Silk Across the Trail', 'scout',
              'Beyond the second lava ford, Magma Spiders ambush supply runners. Defeat four and report to Kael.',
              [kill('spider', 4, 'Defeat Magma Spiders')], 6, 100, 'wisps'),
        quest('spider_sweep', 'Break the Brood', 'captain',
              'Clear seven Magma Spiders from the middle crags so the expedition can move its stores north.',
              [kill('spider', 7, 'Defeat Magma Spiders')], 7, 130, 'spiders'),
        quest('wraiths', 'Voices in the Ash', 'healer',
              'Ash Wraiths wander beyond the third ford. Lay three to rest and bring Iona news of their release.',
              [kill('wraith', 3, 'Defeat Ash Wraiths')], 7, 120, 'spiders'),
        quest('wraith_sweep', 'A Quiet Mountain', 'healer',
              'Silence six Ash Wraiths in the upper crags, then return to Sister Iona for her thanks.',
              [kill('wraith', 6, 'Defeat Ash Wraiths')], 8, 165, 'wraiths'),
        quest('golems', 'Stone Sentinels', 'captain',
              'Basalt Golems guard the heights beyond the fourth ford. Defeat two and report to Captain Sera.',
              [kill('golem', 2, 'Defeat Basalt Golems')], 9, 160, 'wraiths'),
        quest('golem_sweep', 'Crack the Basalt', 'supplier',
              'Dain cannot establish an upper supply post while the stone guardians remain. Defeat four Basalt Golems.',
              [kill('golem', 4, 'Defeat Basalt Golems')], 10, 210, 'golems'),
        quest('expedition', 'Emberfall Vanguard', 'captain',
              'Prove you can secure the entire expedition route: defeat two of every Crags enemy and report to Sera.',
              [kill(kind, 2, 'Defeat ' + label) for kind, label in
               [('wisp', 'Cinder Wisps'), ('spider', 'Magma Spiders'), ('wraith', 'Ash Wraiths'), ('golem', 'Basalt Golems')]],
              10, 250, 'golems'),
        dict(quest('cinderlord', 'Two Against the Cinderlord', 'captain',
              'The Cinderlord, a horned tyrant with a molten warhammer, guards the northeastern heights. '
              'Bring a companion: this elite is meant for two level-10 adventurers using skills and healing. '
              'Both accept this quest and damage him; stay alive and nearby when he falls. '
              'Return to Captain Sera for a guaranteed green Reinforced Moonstone Necklace, usable by every class.',
              [kill('cinderlord', 1, 'Defeat the Cinderlord (Elite · 2 players)')], 10, 200),
              group=True, rewardItem='necklace_moonstone_l10_green', recommendedPlayers=2),
        quest('bounty', 'Cinderwatch Patrol', 'supplier',
              'Defeat ten enemies anywhere in Emberfall Crags and return to Dain. This camp patrol can be repeated.',
              [kill('any', 10, 'Defeat Crags enemies')], 6, 100, 'welcome', True),
        quest('supply_route', 'Keep the Ash Road Open', 'supplier',
              'Clear three Cinder Wisps and three Magma Spiders for the next supply run. Dain offers this contract again after each turn-in.',
              [kill('wisp', 3, 'Defeat Cinder Wisps'), kill('spider', 3, 'Defeat Magma Spiders')], 7, 110, 'spiders', True),
    ]
    quests += progression_quests.for_zone('Emberfall Crags')
    objects = [
        dict(kind='tent', x=38, y=80, r=1.5, width=3, depth=2.4, color='#b76348', label='Command'),
        dict(kind='tent', x=54, y=78, r=1.5, width=3, depth=2.4, color='#817597', label='Infirmary'),
        dict(kind='stall', x=57, y=84, r=1, width=2, depth=1.5, color='#b6864d', label='Supplies'),
        dict(kind='campfire', x=48, y=82, r=.65, v=0),
        dict(kind='noticeboard', x=40, y=87.5, r=.4, width=1.3, depth=.4, label='Cinderwatch Camp'),
        dict(kind='lamp', x=38, y=85, r=.25, v=0),
        dict(kind='lamp', x=58, y=87, r=.25, v=0),
    ]
    city = dict(name='Cinderwatch Camp', x0=36, x1=60, y0=76, y1=89,
                plaza=dict(x=48, y=82), radius=3)
    return npcs, quests, objects, city


def river_y(river, x):
    y, amp, phase, _ = river
    return y + amp * math.sin(x / 9 + phase)


def dist_to_trail(trail, x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(trail, trail[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return best


def build(rng, meadow_objects):
    lava = []
    for river in RIVERS:
        ford = river[3]
        x = 0.4
        while x < SIZE:
            if abs(x - ford) > FORD:
                y = river_y(river, x) + rng.uniform(-.3, .3)
                lava.append({'kind': 'lava', 'x': round(x, 2), 'y': round(y, 2), 'r': round(rng.uniform(1.25, 1.5), 2), 'v': rng.randrange(4)})
            x += 1.3
    trail = [(48, 90), (46, 80), (32, 74), (20, river_y(RIVERS[0], 20)), (24, 60), (50, 57), (74, river_y(RIVERS[1], 74)), (66, 44),
             (40, 42), (12, river_y(RIVERS[2], 12)), (20, 28), (50, 26), (82, river_y(RIVERS[3], 82)), (76, 12), (56, 9)]
    npcs, quests, camp_objects, city = quest_hub()
    objects = list(lava) + camp_objects
    # The return gate: two posts, drawn as part of the gate itself.
    for dx in (-1.5, 1.5):
        objects.append({'kind': 'post', 'x': RETURN_GATE[0] + dx, 'y': RETURN_GATE[1], 'r': 0.45, 'v': 0})
    spawns = []
    for kind, count, (y0, y1) in BANDS:
        for _ in range(count):
            for _ in range(4000):
                x, y = rng.uniform(5, SIZE - 5), rng.uniform(y0, y1)
                if (all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2.6 for o in objects)
                        and all(math.hypot(x - s['x'], y - s['y']) > 7 for s in spawns)
                        and min(abs(x - r[3]) for r in RIVERS) > 6):
                    spawns.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind})
                    break
            else:
                raise SystemExit(f'no room for a {kind}')
    # Scenery, kept off the trail, the camp, the fords and every spawn.
    decor = [('rock', 46, .4), ('tree', 26, .42), ('bush', 20, .3), ('spire', 16, .5)]
    for kind, count, radius in decor:
        placed = 0
        for _ in range(20000):
            if placed == count:
                break
            x, y = rng.uniform(2, SIZE - 2), rng.uniform(2, SIZE - 2)
            if (dist_to_trail(trail, x, y) < 2.2 or (city['x0'] - 2 < x < city['x1'] + 2 and city['y0'] - 2 < y < city['y1'] + 2)
                    or math.hypot(x - ARRIVAL[0], y - 88) < 7
                    or any(math.hypot(x - o['x'], y - o['y']) < o['r'] + radius + 1.6 for o in objects)
                    or any(math.hypot(x - s['x'], y - s['y']) < 2.6 for s in spawns)
                    or any(abs(x - r[3]) < FORD + 2 and abs(y - river_y(r, x)) < 5 for r in RIVERS)):
                continue
            objects.append({'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': radius, 'v': rng.randrange(4)})
            placed += 1
        assert placed == count, f'only {placed} {kind}'
    zone = {
        'name': 'Emberfall Crags', 'theme': 'ember', 'size': SIZE, 'levels': [5, 10],
        'spawn': {'x': ARRIVAL[0], 'y': ARRIVAL[1]},
        'paths': [[[round(x, 1), round(y, 1)] for x, y in trail]],
        'objects': objects, 'slimes': spawns, 'npcs': npcs, 'quests': quests, 'city': city,
        'portals': [{'id': 'meadow_gate', 'name': 'the Meadow Gate', 'x': RETURN_GATE[0], 'y': RETURN_GATE[1], 'r': 1.1,
                     'to': 0, 'tx': MEADOW_ARRIVAL[0], 'ty': MEADOW_ARRIVAL[1]}],
    }
    return zone


def ensure_elite(zone):
    """Reserve a clear arena in the northeast without moving existing terrain, enemies or gates."""
    if any(s['kind'] == 'cinderlord' for s in zone['slimes']):
        return
    candidates = [(x, y) for y in range(8, 17) for x in range(76, 91)]
    candidates.sort(key=lambda p: math.hypot(p[0] - 84, p[1] - 10))
    for x, y in candidates:
        if (any(math.hypot(x - o['x'], y - o['y']) < o['r'] + 3 for o in zone['objects'])
                or any(math.hypot(x - s['x'], y - s['y']) < 11 for s in zone['slimes'])
                or any(min(math.hypot(x - p['x'], y - p['y']),
                           math.hypot(x - p['tx'], y - p['ty'])) < 11 for p in zone['portals'])):
            continue
        zone['slimes'].append(dict(x=x, y=y, kind='cinderlord'))
        if not reachable(zone):
            return
        zone['slimes'].pop()
    raise SystemExit('No reachable, clear Cinderlord arena in the northeastern heights')


def reachable(zone):
    """Grid flood fill with the player's radius: every spawn and the gate must connect to the arrival."""
    step, margin = .5, .62
    n = int(SIZE / step)
    blocked = [[False] * n for _ in range(n)]
    for j in range(n):
        for i in range(n):
            x, y = (i + .5) * step, (j + .5) * step
            if x < .7 or y < .7 or x > SIZE - .7 or y > SIZE - .7:
                blocked[j][i] = True
                continue
            blocked[j][i] = any(
                (abs(x - o['x']) < o['width'] / 2 + margin and abs(y - o['y']) < o['depth'] / 2 + margin)
                if o.get('width') and o.get('depth') else math.hypot(x - o['x'], y - o['y']) < o['r'] + margin
                for o in zone['objects'])
    start = (int(ARRIVAL[0] / step), int(ARRIVAL[1] / step))
    seen = {start}
    queue = [start]
    for i, j in queue:
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < n and (a, b) not in seen and not blocked[b][a]:
                seen.add((a, b))
                queue.append((a, b))
    targets = [(s['x'], s['y'], s['kind']) for s in zone['slimes']] + [(n['x'], n['y'], n['id']) for n in zone['npcs']] + [(RETURN_GATE[0], RETURN_GATE[1] - 2, 'gate')]
    missing = [t for t in targets if (int(t[0] / step), int(t[1] / step)) not in seen]
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hub-only', action='store_true', help='update Cinderwatch without regenerating terrain or enemy spawns')
    args = parser.parse_args()
    raw = PATH.read_text()
    meadow = json.loads(raw)
    assert json.dumps(meadow, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    if args.hub_only:
        zone = meadow['zones'][0]
        assert zone['name'] == 'Emberfall Crags', 'zone 1 must be the Crags'
        npcs, quests, objects, city = quest_hub()
        is_camp = lambda o: city['x0'] - 2 < o['x'] < city['x1'] + 2 and city['y0'] - 2 < o['y'] < city['y1'] + 2
        at = next(i for i, o in enumerate(zone['objects']) if is_camp(o))
        outside = [o for o in zone['objects'] if not is_camp(o)]
        zone['objects'] = outside[:at] + objects + outside[at:]
        zone.update(npcs=npcs, quests=quests, city=city)
        ensure_elite(zone)
        missing = reachable(zone)
        if missing:
            raise SystemExit(f'unreachable from the arrival point: {missing}')
        spark_travel.ensure(meadow)
        PATH.write_text(json.dumps(meadow, indent=2) + '\n')
        print(f'Updated Cinderwatch Camp: {len(npcs)} NPCs, {len(quests)} quests. Terrain and enemy spawns preserved. Now run node scripts/sync-world.cjs')
        return
    rng = random.Random(20261001)
    # Remove anything an earlier run added to the meadow.
    meadow['objects'] = [o for o in meadow['objects'] if o['kind'] != 'post']
    later_zones = meadow.pop('zones', [])[1:]       # zones 2+ (Rimeveil Glacier) belong to their own generators
    meadow.pop('portals', None)
    meadow['name'] = 'Greenmeadow'
    # Blue slimes that stood in front of the gate move to the nearest clear spot.
    for s in meadow['slimes']:
        if min(math.hypot(s['x'] - px, s['y'] - py) for px, py in (MEADOW_GATE, MEADOW_ARRIVAL)) < 9.5 and s['kind'] != 'beetle':
            ox, oy = s['x'], s['y']
            best = None
            for _ in range(3000):
                x, y = ox + rng.uniform(-14, 14), oy + rng.uniform(-14, 14)
                if (min(math.hypot(x - px, y - py) for px, py in (MEADOW_GATE, MEADOW_ARRIVAL)) > 10 and 4 < x < SIZE - 4 and 4 < y < 70
                        and all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2 for o in meadow['objects'])
                        and all(math.hypot(x - t['x'], y - t['y']) > 5 for t in meadow['slimes'] if t is not s)):
                    d = math.hypot(x - ox, y - oy)
                    if best is None or d < best[0]:
                        best = (d, x, y)
            assert best, 'no clear spot for a displaced spawn'
            s['x'], s['y'] = round(best[1], 2), round(best[2], 2)
    for dx in (-1.5, 1.5):
        meadow['objects'].append({'kind': 'post', 'x': MEADOW_GATE[0] + dx, 'y': MEADOW_GATE[1], 'r': 0.45, 'v': 0})
    meadow['portals'] = [{'id': 'emberfall_gate', 'name': 'the Emberfall Gate', 'x': MEADOW_GATE[0], 'y': MEADOW_GATE[1], 'r': 1.1,
                          'to': 1, 'tx': ARRIVAL[0], 'ty': ARRIVAL[1]}]
    for o in meadow['objects']:
        if o['kind'] != 'post' and math.hypot(o['x'] - MEADOW_GATE[0], o['y'] - MEADOW_GATE[1]) < o['r'] + 1.6:
            raise SystemExit(f'meadow object {o} blocks the gate')
    zone = build(rng, meadow['objects'])
    ensure_elite(zone)
    missing = reachable(zone)
    if missing:
        raise SystemExit(f'unreachable from the arrival point: {missing}')
    meadow['zones'] = [zone] + later_zones
    spark_travel.ensure(meadow)
    PATH.write_text(json.dumps(meadow, indent=2) + '\n')
    kinds = {}
    for s in zone['slimes']:
        kinds[s['kind']] = kinds.get(s['kind'], 0) + 1
    print(f"Wrote zone 1 {zone['name']}: {len(zone['objects'])} objects, spawns {kinds}. Now run node scripts/sync-world.cjs")
    if later_zones:
        print('Zones 2+ were kept, but the Crags lost their north gate: run python3 scripts/generate_rimeveil.py again.')


if __name__ == '__main__':
    main()
