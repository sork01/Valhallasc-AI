#!/usr/bin/env python3
"""Writes Gloamfen (zone 3, levels 15-20) and its gate in the Rimeveil summit into world/map.txt.

Layout: a 128x128 dusk fen. The boardwalk town Lanternmere fills the north strip. A thicket ridge (R1) closes the
strip except for one gap in the west; below it a black lake (Gloam Mere) sits in the middle with a hydra island and a
causeway from its east shore. Three more ridges make the route a C round the lake, west bank -> south shore -> east
bank -> causeway, each with one gap:
  R1 (y=37, gap west)        town strip -> west bank:   Fen Toads        (level 15)
  R2 (y=93, gap by the lake) west bank -> south shore:  Mire Crocodiles  (level 17)
  R3 (SE of the lake, gap)   south shore -> east bank:  Drowned Knights  (level 18, among ruined columns)
  causeway mouth             east bank -> the island:   Mire Hydras      (level 20)
R4 (x=66, no gap) joins R1 to the lake so the north fen cannot short-cut the west bank to the east bank.
Lanternmere (safe quest hub: seven NPCs, sixteen quests) has the return gate on its north edge.

The Rimeveil summit gains a gate at the centre of the bowl; wyrm spawns near its arrival point move clear.
Re-running replaces zone 3 and that gate and leaves everything else alone. Use --hub-only to update the town
without rebuilding the fen. Afterwards: node scripts/sync-world.cjs, then rebuild Rust.
"""
import argparse
import json
import spark_travel
import math
from pathlib import Path
import random

import mercenary_offers as mo
import progression_quests

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth
NAME = 'Gloamfen'
GLACIER = 'Rimeveil Glacier'
SIZE = 128
ARRIVAL = (64.0, 9.0)                            # where the glacier gate drops you
RETURN_GATE = (64.0, 4.5)                        # the way back to the Rimeveil summit
GLACIER_GATE = (64.0, 50.0)                      # in the centre of the summit bowl
GLACIER_ARRIVAL = (64.0, 54.5)
GLACIER_START = (64.0, 118.5)                    # the glacier arrival camp, for the reachability check
LAKE = (66.0, 76.0)
ISLAND_R = 9.8
WATER_R, WATER_STEP = 2.3, 2.6
THICKET_R, THICKET_STEP = 1.3, 1.6
GAP_HALF = 4.3
R1_Y, R2_Y, R4_X = 37.0, 93.0, 66.0
GAPS = [(18.0, 37.0), (40.0, 93.0), (92.0, 113.0)]      # R1, R2, R3 gap centres
MOUTH = (88.5, 76.0)                                      # where the causeway leaves the east shore
TOWN = dict(name='Lanternmere', x0=40, x1=88, y0=6, y1=31, plaza=dict(x=64, y=19), radius=3.2)
BANDS = [  # kind, count, region index (0 west bank, 1 south shore, 2 east bank, 3 island), min spacing
    ('toad', 10, 0, 7.),
    ('croc', 9, 1, 7.),
    ('knight', 8, 2, 7.),
    ('hydra', 4, 3, 6.),
]
TRAIL = [RETURN_GATE, (64.0, 9.0), (64.0, 19.0), (64.0, 31.0), (58.0, 34.0), (30.0, 34.0), (18.0, 37.0),
         (16.0, 46.0), (13.0, 58.0), (20.0, 70.0), (28.0, 82.0), (36.0, 90.0), (40.0, 93.0), (44.0, 98.0),
         (56.0, 108.0), (72.0, 112.0), (92.0, 113.0), (99.0, 106.0), (101.0, 92.0), (96.0, 80.0), MOUTH,
         (76.0, 76.0), LAKE]


def lake_radius(theta):
    return 23.0 + 2.6 * math.sin(2 * theta + 1.1) + 1.8 * math.sin(3 * theta + .4)


def in_lake(x, y, grow=0.0):
    dx, dy = x - LAKE[0], y - LAKE[1]
    return math.hypot(dx, dy) < lake_radius(math.atan2(dy, dx)) + grow


def quest_hub():
    """Lanternmere: a boardwalk town with a hall, an inn, a market and seven people with work for you."""
    def npc(id, name, role, x, y, color, dialogue, offers=None, buys=False):
        return dict(id='fen_' + id, name=name, role=role, x=x, y=y, color=color,
                    dialogue=dialogue, offers=offers or [], buys=buys)

    npcs = [
        npc('reeve', 'Reeve Osric', 'Town reeve', 78, 16.5, '#7a6aa8',
            'Lanternmere keeps its lanterns lit all night, and every night the dark fen takes a few more. Toads on the west bank, crocodiles along the south shore, drowned knights among the ruins in the east, and something with many heads out on the island. Speak to everyone in town, then report to me. '
            'The Gloomroot in the south-east corner takes five. Once you have taken that quest I can hire you the fighters you lack: choose any classes, 250 gold each, and they join your party until the job is done.',
            mo.offers()),
        npc('lamplighter', 'Lamplighter Wren', 'Keeper of the lanterns', 75.5, 22.8, '#c89a4a',
            'I trim one hundred and twelve wicks a night. The toads sing the fog in, and fog puts the flames out. Thin the choir and the boardwalk stays bright.'),
        npc('healer', 'Sister Maren', 'Lantern Hall healer', 50, 16.8, '#e4e0d4',
            'Come in out of the damp. My blessing costs nothing and I sell Health Potions for the road. The drowned knights wander the ruins because nobody laid them to rest.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_mana_potion', label='Buy Mana Potion · 100 mana instantly', cost=30, item='mana_potion', tiered=True),
             dict(id='buy_health_potion', label='Buy Health Potion · 100 HP instantly', cost=30, item='health_potion', tiered=True)]),
        npc('trader', 'Trader Torvald', 'Boggoods & bounties', 57, 22.4, '#9a7a52',
            'Glands, hides, gauntlets and fangs: I buy them all, and I pay better than the guild in the city. I sell stew and satchels, and my patrol contracts never run out.',
            [dict(id='buy_traveler_stew', label="Buy Traveler's Stew · 100 HP and mana over 8 s", cost=12, item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel · 6 extra bag slots', cost=500, bag='linen_satchel')], buys=True),
        npc('ranger', 'Ranger Tilda', 'Fen ranger', 70, 25.2, '#5f8a62',
            'Follow the planks and stay on them. The west bank is toad country, the south shore belongs to the crocodiles, and the lake takes anyone who steps off the boards. Every ridge has one gap: find it.'),
        npc('scholar', 'Scholar Pell', 'Scholar of the ruins', 52.5, 21.6, '#a88ac0',
            'There was a fort on the east bank before the mere rose. Its garrison still stands watch, knee-deep in the shallows. And the island in the middle: nobody who went to see it has come back to say what lives there.'),
        npc('ferryman', 'Ferryman Odd', 'Ferryman', 58.2, 25.6, '#6a8fa8',
            'I ran the ferry across the mere for forty years, until the island woke up. Now the causeway on the east shore is the only way across, and I will not walk it. Clear the road and I will owe you a ride.'),
    ]

    def kill(kind, count, label):
        return dict(kind='kill', target=kind, label=label, count=count)

    def talk(id, name):
        return dict(kind='talk', target='fen_' + id, label='Speak to ' + name, count=1)

    def quest(id, title, npc, description, objectives, level, gold, requires=None, repeatable=False):
        # Recommended level; the XP reward is 10% of what that level needs (server test enforces it).
        return dict(id='fen_' + id, title=title, npc='fen_' + npc, description=description,
                    objectives=objectives, level=level, rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold,
                    requires='fen_' + requires if requires else None, repeatable=repeatable)

    quests = [
        quest('welcome', 'Lights on the Water', 'reeve',
              'Meet Lamplighter Wren, Sister Maren, Trader Torvald, Ranger Tilda, Scholar Pell and Ferryman Odd, then report to Reeve Osric.',
              [talk('lamplighter', 'Lamplighter Wren'), talk('healer', 'Sister Maren'), talk('trader', 'Trader Torvald'),
               talk('ranger', 'Ranger Tilda'), talk('scholar', 'Scholar Pell'), talk('ferryman', 'Ferryman Odd')], 15, 300),
        quest('toads', 'The Choir in the Reeds', 'ranger',
              'Leave town by the gap in the western thicket and defeat five Fen Toads on the west bank. Return to Tilda.',
              [kill('toad', 5, 'Defeat Fen Toads')], 15, 320, 'welcome'),
        quest('toad_sweep', 'Hush the Marsh', 'ranger',
              'The toads sing louder every night. Defeat ten Fen Toads so the boardwalk lanterns survive until dawn.',
              [kill('toad', 10, 'Defeat Fen Toads')], 16, 360, 'toads'),
        quest('relight', 'Wicks and Fog', 'lamplighter',
              'Wren cannot keep the western lanterns lit through the fog the toads breed. Defeat six Fen Toads for her.',
              [kill('toad', 6, 'Defeat Fen Toads')], 16, 380, 'toads'),
        quest('crocs', 'Teeth in the Shallows', 'ranger',
              'Past the second gap, near the lake, the Mire Crocodiles patrol the south shore. Defeat four and tell Tilda what you saw.',
              [kill('croc', 4, 'Defeat Mire Crocodiles')], 17, 420, 'toads'),
        quest('croc_hunt', 'Hides for the Dike', 'reeve',
              'The reeve wants the south shore safe for the dike crews. Defeat eight Mire Crocodiles.',
              [kill('croc', 8, 'Defeat Mire Crocodiles')], 17, 460, 'crocs'),
        quest('ferry', 'The Ferry Line', 'ferryman',
              'Odd needs the western bank and the southern shore quiet before he will pole a boat again. Clear five Fen Toads and three Mire Crocodiles.',
              [kill('toad', 5, 'Defeat Fen Toads'), kill('croc', 3, 'Defeat Mire Crocodiles')], 17, 440, 'crocs'),
        quest('knights', 'The Garrison That Stayed', 'scholar',
              'Through the third gap the old fort\'s garrison still keeps watch, drowned and rusted. Defeat three Drowned Knights and bring Pell their number.',
              [kill('knight', 3, 'Defeat Drowned Knights')], 18, 520, 'crocs'),
        quest('rest', 'Lay Them to Rest', 'healer',
              'Sister Maren will say the words if you can give the dead their peace. Defeat six Drowned Knights.',
              [kill('knight', 6, 'Defeat Drowned Knights')], 19, 580, 'knights'),
        quest('drowned_watch', 'The Drowned Watch', 'lamplighter',
              'Crocodiles on the shore, knights in the ruins: Wren wants both thinned before she lights the eastern lamps. Defeat four of each.',
              [kill('croc', 4, 'Defeat Mire Crocodiles'), kill('knight', 4, 'Defeat Drowned Knights')], 19, 600, 'knights'),
        quest('hydra', 'Many Heads', 'scholar',
              'Cross the east-shore causeway to the island and defeat two Mire Hydras. Pell must know what lives there.',
              [kill('hydra', 2, 'Defeat Mire Hydras')], 20, 700, 'knights'),
        quest('hydra_hunt', 'Hydrabane', 'reeve',
              'Osric wants the island cleared for good. Defeat four Mire Hydras and report back.',
              [kill('hydra', 4, 'Defeat Mire Hydras')], 20, 760, 'hydra'),
        quest('vanguard', 'Heart of the Mere', 'reeve',
              'Prove you can hold the whole fen: defeat two of every Gloamfen monster and report to Osric.',
              [kill(kind, 2, 'Defeat ' + label) for kind, label in
               [('toad', 'Fen Toads'), ('croc', 'Mire Crocodiles'), ('knight', 'Drowned Knights'), ('hydra', 'Mire Hydras')]],
              20, 820, 'hydra'),
        # The elite quest: group-credited kills, a guaranteed blue (rare) ring, five players recommended.
        dict(quest('gloomroot', 'Five Against the Gloomroot', 'reeve',
              'In the far south-eastern corner of the fen, past the third gap and along the dark shore, a drowned willow has grown into a giant: '
              'the Gloomroot Colossus, its heart burning cyan. It crushes a lone hero in a few blows, and two do not do much better. '
              'Bring four companions, five adventurers of level 20 with someone to hold it, someone to heal and the rest to hit hard. '
              'All five accept this quest and damage the Colossus; stay alive and close when it falls. '
              'Return to Reeve Osric for a guaranteed blue Celestial Amber Ring, usable by every class.',
              [kill('gloomroot', 1, 'Defeat the Gloomroot Colossus (Elite · 5 players)')], 20, 1500, 'hydra'),
             group=True, rewardItem='accessory_amber_l20_blue', recommendedPlayers=5),
        quest('bounty', 'Boardwalk Patrol', 'trader',
              'Defeat ten enemies anywhere in Gloamfen and return to Torvald. This patrol can be repeated.',
              [kill('any', 10, 'Defeat fen enemies')], 16, 340, 'welcome', True),
        quest('supplies', 'Keep the Plank Road Open', 'trader',
              'Clear three Fen Toads and three Mire Crocodiles for the next supply cart. Torvald offers this contract again after each turn-in.',
              [kill('toad', 3, 'Defeat Fen Toads'), kill('croc', 3, 'Defeat Mire Crocodiles')], 17, 400, 'toads', True),
        quest('deep_patrol', 'The Deep Patrol', 'ferryman',
              'Odd pays for every Drowned Knight and every hydra that stays down. Defeat four Drowned Knights and one Mire Hydra. Repeatable.',
              [kill('knight', 4, 'Defeat Drowned Knights'), kill('hydra', 1, 'Defeat a Mire Hydra')], 19, 650, 'knights', True),
    ]
    house = lambda x, y, color, label: dict(kind='house', x=x, y=y, r=0, v=0, width=3.4, depth=3.2, color=color, label=label)
    quests += progression_quests.for_zone('Gloamfen')
    objects = [
        dict(kind='chapel', x=50, y=13, r=0, v=0, width=3.4, depth=3.2, color='#5f7f78', label='Lantern Hall'),
        house(78, 13, '#7a5a8c', "Reeve's House"),
        house(49, 25, '#b8744e', 'The Drowned Lantern'),
        house(79, 25, '#667c91', "Lamplighter's Loft"),
        house(58, 29, '#4f7a6a', 'Ferry House'),
        house(70, 29, '#8a6a4a', 'Ranger Lodge'),
        dict(kind='fountain', x=64, y=19, r=1.1, v=0),
        dict(kind='stall', x=57, y=20, r=0, v=0, width=1.8, depth=1.2, color='#678c9b', label='Market'),
        dict(kind='stall', x=71, y=20, r=0, v=0, width=1.8, depth=1.2, color='#c4a060', label='Fishmonger'),
        dict(kind='noticeboard', x=58, y=11, r=.4, width=1.3, depth=.4, label='Lanternmere'),
        dict(kind='bench', x=60, y=22.6, r=0, v=0, width=1.5, depth=.45),
        dict(kind='bench', x=68, y=22.6, r=0, v=0, width=1.5, depth=.45),
    ]
    for x, y in [(64, 12), (64, 15.5), (64, 23.5), (64, 27), (53, 10), (75, 10), (44, 21), (84, 21), (54, 30), (74, 31),
                 (46, 15), (82, 17)]:
        objects.append(dict(kind='lamp', x=x, y=y, r=.18, v=0))
    return npcs, quests, objects, dict(TOWN)


def polar_points(points):
    return [(round(x, 1), round(y, 1)) for x, y in points]


def ridge(points, rng, gap=None, gap_half=GAP_HALF):
    """Thicket discs along a polyline, every THICKET_STEP, skipping the gap."""
    out = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        length = math.hypot(bx - ax, by - ay)
        n = max(1, int(length / THICKET_STEP))
        for i in range(n + 1):
            if out and i == 0:
                continue
            t = i / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            x += .35 * math.sin(y * 1.9 + x * .7)
            y += .35 * math.cos(x * 1.7 - y * .5)
            if gap and math.hypot(x - gap[0], y - gap[1]) < gap_half:
                continue
            out.append({'kind': 'thicket', 'x': round(x, 2), 'y': round(y, 2), 'r': THICKET_R, 'v': rng.randrange(4)})
    return out


def lake_edge_point(x=None, y=None):
    """Where a straight scan along a line first enters the lake: x given scans y from the top, y given scans x from the west."""
    if x is not None:
        yy = R1_Y
        while not in_lake(x, yy, -1.0):
            yy += .1
        return x, yy
    xx = 20.0
    while not in_lake(xx, y, -1.0):
        xx += .1
    return xx, y


def build_lake(rng):
    objects = []
    corridor_y = LAKE[1]
    row = 0
    y = LAKE[1] - 30
    while y < LAKE[1] + 30:
        x = LAKE[0] - 30 + (WATER_STEP / 2 if row % 2 else 0)
        while x < LAKE[0] + 30:
            d = math.hypot(x - LAKE[0], y - LAKE[1])
            # centre inside the blob; the island and the causeway stay dry (discs have radius WATER_R)
            if in_lake(x, y) and d > ISLAND_R + WATER_R * .35 and not (x > LAKE[0] and abs(y - corridor_y) < 3.8):
                objects.append({'kind': 'water', 'x': round(x, 2), 'y': round(y, 2), 'r': WATER_R, 'v': rng.randrange(4)})
            x += WATER_STEP
        y += WATER_STEP * .866
        row += 1
    return objects


def obstacle_grid(zone, step=.5, margin=.62, extra=()):
    n = int(zone['size'] / step)
    blocked = np.zeros((n, n), dtype=bool)
    ii = (np.arange(n) + .5) * step
    X, Y = np.meshgrid(ii, ii)
    blocked |= (X < .7) | (Y < .7) | (X > zone['size'] - .7) | (Y > zone['size'] - .7)
    for o in list(zone['objects']) + list(extra):
        if o.get('width') and o.get('depth'):
            hx, hy = o['width'] / 2 + margin, o['depth'] / 2 + margin
            i0, i1 = int((o['x'] - hx) / step) - 1, int((o['x'] + hx) / step) + 2
            j0, j1 = int((o['y'] - hy) / step) - 1, int((o['y'] + hy) / step) + 2
            sub = (np.abs(X[max(j0, 0):j1, max(i0, 0):i1] - o['x']) < hx) & (np.abs(Y[max(j0, 0):j1, max(i0, 0):i1] - o['y']) < hy)
        else:
            reach = o['r'] + margin
            i0, i1 = int((o['x'] - reach) / step) - 1, int((o['x'] + reach) / step) + 2
            j0, j1 = int((o['y'] - reach) / step) - 1, int((o['y'] + reach) / step) + 2
            sub = np.hypot(X[max(j0, 0):j1, max(i0, 0):i1] - o['x'], Y[max(j0, 0):j1, max(i0, 0):i1] - o['y']) < reach
        blocked[max(j0, 0):j1, max(i0, 0):i1] |= sub
    return blocked


def flood(zone, start, closed=(), step=.5):
    """Cells (i, j) a player can reach from `start`; `closed` is a list of (x, y, r) discs that act as extra walls."""
    blocked = obstacle_grid(zone, step, extra=[{'x': x, 'y': y, 'r': r} for x, y, r in closed])
    n = blocked.shape[0]
    si, sj = int(start[0] / step), int(start[1] / step)
    assert not blocked[sj, si], f'start {start} is blocked'
    seen = np.zeros_like(blocked)
    seen[sj, si] = True
    queue = [(si, sj)]
    for i, j in queue:
        for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= a < n and 0 <= b < n and not seen[b, a] and not blocked[b, a]:
                seen[b, a] = True
                queue.append((a, b))
    return seen, blocked


def regions(zone):
    """Cell sets of the town strip, west bank, south shore, east bank and island, found by closing each choke in turn."""
    g1, g2, g3 = GAPS
    seals = [[(g1[0], g1[1], GAP_HALF + .5)], [(g2[0], g2[1], GAP_HALF + .5)], [(g3[0], g3[1], GAP_HALF + .5)],
             [(MOUTH[0], MOUTH[1], 3.0)]]
    reach = [flood(zone, ARRIVAL, s)[0] for s in seals]
    full = flood(zone, ARRIVAL)[0]
    town = reach[0]
    west = reach[1] & ~reach[0]
    south = reach[2] & ~reach[1]
    east = reach[3] & ~reach[2]
    island = full & ~reach[3]
    return [town, west, south, east, island], full


def dist_to_trail(trail, x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(trail, trail[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return best


def build(rng):
    objects = []
    # The lake, then the ridges that make the route a C round it.
    objects += build_lake(rng)
    objects += ridge([(1.0, R1_Y), (127.0, R1_Y)], rng, GAPS[0])
    r2_end = lake_edge_point(y=R2_Y)
    objects += ridge([(1.0, R2_Y), r2_end], rng, GAPS[1])
    r3_start = None
    for theta in np.linspace(.3, 1.2, 200):               # the lake's south-east shoreline
        d = lake_radius(theta)
        r3_start = (LAKE[0] + (d - .5) * math.cos(theta), LAKE[1] + (d - .5) * math.sin(theta))
        if r3_start[0] > 79 and r3_start[1] > 88:
            break
    objects += ridge([r3_start, (92.0, 99.0), (92.0, 127.0)], rng, GAPS[2])
    objects += ridge([(R4_X, R1_Y), lake_edge_point(x=R4_X)], rng)
    # The gate back to the Rimeveil summit: two posts, drawn as part of the gate itself.
    for dx in (-1.5, 1.5):
        objects.append({'kind': 'post', 'x': RETURN_GATE[0] + dx, 'y': RETURN_GATE[1], 'r': 0.45, 'v': 0})
    npcs, quests, town_objects, city = quest_hub()
    objects += town_objects
    # Ruins on the east bank (a ring of broken columns) and the drowned gate at the causeway mouth.
    for i in range(10):
        a = i / 10 * 2 * math.pi
        objects.append({'kind': 'spire', 'x': round(108 + 6.5 * math.cos(a), 2), 'y': round(66 + 6.5 * math.sin(a), 2), 'r': .55, 'v': i % 4})
    for dy in (-3.4, 3.4):
        objects.append({'kind': 'spire', 'x': MOUTH[0] + .5, 'y': MOUTH[1] + dy, 'r': .55, 'v': 1})
    for i in range(6):                                    # standing stones on the island
        a = i / 6 * 2 * math.pi + .3
        objects.append({'kind': 'spire', 'x': round(LAKE[0] + 6.2 * math.cos(a), 2), 'y': round(LAKE[1] + 6.2 * math.sin(a), 2), 'r': .55, 'v': (i + 2) % 4})
    trail = polar_points(TRAIL)
    zone = {'name': NAME, 'theme': 'fen', 'size': SIZE, 'levels': [15, 20],
            'spawn': {'x': ARRIVAL[0], 'y': ARRIVAL[1]}, 'paths': [[[x, y] for x, y in trail]],
            'objects': objects, 'slimes': [], 'npcs': npcs, 'quests': quests, 'city': city,
            'portals': [{'id': 'summit_gate', 'name': 'the Summit Gate', 'x': RETURN_GATE[0], 'y': RETURN_GATE[1], 'r': 1.1,
                         'to': 2, 'tx': GLACIER_ARRIVAL[0], 'ty': GLACIER_ARRIVAL[1]}]}
    parts, full = regions(zone)
    names = ['town', 'west bank', 'south shore', 'east bank', 'island']
    for part, name in zip(parts, names):
        assert part.sum() > 400, f'region {name} is empty ({part.sum()} cells): a ridge or the lake leaks'
    # Spawns: each kind inside its own region, clear of scenery, apart from each other and from every choke.
    chokes = GAPS + [MOUTH]
    spawns = []
    step = .5
    for kind, count, k, spacing in BANDS:
        cells = [tuple(c) for c in np.argwhere(parts[k + 1]).tolist()]   # a list: random.shuffle corrupts numpy rows
        rng.shuffle(cells)
        placed = 0
        for j, i in cells:
            x, y = (i + .5) * step, (j + .5) * step
            if (4 < x < SIZE - 4 and 4 < y < SIZE - 4
                    and all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2.3 for o in objects if not o.get('width'))
                    and all(math.hypot(x - s['x'], y - s['y']) > spacing for s in spawns)
                    and all(math.hypot(x - cx, y - cy) > 8.5 for cx, cy in chokes)
                    and (kind != 'knight' or math.hypot(x - 108, y - 66) < 22)
                    and (kind != 'hydra' or math.hypot(x - LAKE[0], y - LAKE[1]) < ISLAND_R - 2)   # on the island, not the causeway
                    and not (kind in ('toad', 'croc') and dist_to_trail(trail, x, y) > 30)):
                spawns.append({'x': round(x, 2), 'y': round(y, 2), 'kind': kind})
                placed += 1
                if placed == count:
                    break
        if placed != count:
            raise SystemExit(f'no room for {count} {kind}: placed {placed}')
    # Scenery: willows and reeds everywhere dry, crowded in the town strip, sparse in the bands.
    def region_of(x, y):
        for k, part in enumerate(parts):
            if part[int(y / step), int(x / step)]:
                return k
        return None

    decor = [  # kind, count per region [town, west, south, east, island], size
        ('tree', [70, 34, 24, 30, 0], .42),
        ('bush', [40, 24, 20, 20, 3], .3),
        ('rock', [10, 12, 10, 10, 3], .4),
        ('spire', [3, 6, 6, 4, 0], .5),
    ]
    for kind, counts, size in decor:
        for k, count in enumerate(counts):
            placed = 0
            for _ in range(40000):
                if placed == count:
                    break
                x, y = rng.uniform(2, SIZE - 2), rng.uniform(2, SIZE - 2)
                if (region_of(x, y) != k or dist_to_trail(trail, x, y) < 2.4
                        or (TOWN['x0'] - 3 < x < TOWN['x1'] + 3 and TOWN['y0'] - 3 < y < TOWN['y1'] + 3)
                        or math.hypot(x - RETURN_GATE[0], y - RETURN_GATE[1]) < 5
                        or any(math.hypot(x - cx, y - cy) < 6 for cx, cy in chokes)
                        or any(math.hypot(x - o['x'], y - o['y']) < o['r'] + size + 1.5 for o in objects if not o.get('width'))
                        or any(math.hypot(x - s['x'], y - s['y']) < 2.8 for s in spawns)):
                    continue
                objects.append({'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': size, 'v': rng.randrange(4)})
                placed += 1
            assert placed == count, f'only {placed} {kind} in region {k}'
    zone['slimes'] = spawns
    return zone


def glacier_targets(zone):
    return ([(s['x'], s['y'], s['kind']) for s in zone['slimes']] + [(n['x'], n['y'], n['id']) for n in zone['npcs']])


ELITE = 'gloomroot'
DECOR = ('tree', 'bush', 'rock', 'spire')


def ensure_elite(zone):
    """The Gloomroot Colossus's hollow: the clearest ground in the fen far from every other spawn and every choke
    (the south-eastern corner of the east bank). Scenery is cleared round it, so nothing else moves."""
    if any(s['kind'] == ELITE for s in zone['slimes']):
        return
    from scipy import ndimage as ndi
    east = regions(zone)[0][3]
    bare = dict(zone, objects=[o for o in zone['objects'] if o['kind'] not in DECOR])
    clearance = ndi.distance_transform_edt(~obstacle_grid(bare)) * .5
    best = None
    for j, i in np.argwhere(east & (clearance >= 10)).tolist():
        x, y = (i + .5) * .5, (j + .5) * .5
        if not (7 < x < SIZE - 7 and 7 < y < SIZE - 7):
            continue
        score = min(min(math.hypot(x - s['x'], y - s['y']) for s in zone['slimes']),
                    min(math.hypot(x - cx, y - cy) for cx, cy in GAPS + [MOUTH]))
        if best is None or score > best[0]:
            best = (score, round(x, 1), round(y, 1))
    if best is None:
        raise SystemExit('No clear ground for the Gloomroot Colossus in the east bank')
    _, x, y = best
    zone['objects'] = [o for o in zone['objects'] if not (o['kind'] in DECOR and math.hypot(o['x'] - x, o['y'] - y) < 9.5 + o['r'])]
    zone['slimes'].append(dict(x=x, y=y, kind=ELITE))


def fen_unreachable(zone):
    seen, _ = flood(zone, ARRIVAL)
    step = .5
    targets = glacier_targets(zone) + [(RETURN_GATE[0], RETURN_GATE[1] + 2, 'gate'), (LAKE[0], LAKE[1], 'island centre')]
    return [t for t in targets if not seen[int(t[1] / step), int(t[0] / step)]]


def add_summit_gate(meadow, rng):
    """Remove an earlier gate, clear the ground in front of the new one, then add posts, portal and move wyrms clear."""
    glacier = next(z for z in meadow['zones'] if z['name'] == GLACIER)
    gate_x = [GLACIER_GATE[0] - 1.5, GLACIER_GATE[0] + 1.5]
    glacier['objects'] = [o for o in glacier['objects'] if not (o['kind'] == 'post' and abs(o['y'] - GLACIER_GATE[1]) < .01)]
    glacier['portals'] = [p for p in glacier['portals'] if p['id'] != 'fen_gate']
    glacier['objects'] = [o for o in glacier['objects'] if o['kind'] in ('ice', 'post') or not (
        math.hypot(o['x'] - GLACIER_GATE[0], o['y'] - GLACIER_GATE[1]) < o['r'] + 2.4
        or math.hypot(o['x'] - GLACIER_ARRIVAL[0], o['y'] - GLACIER_ARRIVAL[1]) < o['r'] + 2.4)]
    for x in gate_x:
        glacier['objects'].append({'kind': 'post', 'x': x, 'y': GLACIER_GATE[1], 'r': 0.45, 'v': 0})
    glacier['portals'].append({'id': 'fen_gate', 'name': 'the Gloamfen Gate', 'x': GLACIER_GATE[0], 'y': GLACIER_GATE[1], 'r': 1.1,
                               'to': 3, 'tx': ARRIVAL[0], 'ty': ARRIVAL[1]})
    centre, gap4 = (64.0, 52.0), (64.0, 37.0)
    moved = 0
    for s in glacier['slimes']:
        if math.hypot(s['x'] - GLACIER_ARRIVAL[0], s['y'] - GLACIER_ARRIVAL[1]) < 10:
            ox, oy = s['x'], s['y']
            best = None
            for _ in range(8000):
                x, y = ox + rng.uniform(-14, 14), oy + rng.uniform(-14, 14)
                if (math.hypot(x - centre[0], y - centre[1]) < 11.5
                        and math.hypot(x - GLACIER_ARRIVAL[0], y - GLACIER_ARRIVAL[1]) > 10
                        and math.hypot(x - gap4[0], y - gap4[1]) > 8.5
                        and math.hypot(x - GLACIER_GATE[0], y - GLACIER_GATE[1]) > 5
                        and all(math.hypot(x - o['x'], y - o['y']) > o['r'] + 2.3 for o in glacier['objects'])
                        and all(math.hypot(x - t['x'], y - t['y']) > 7 for t in glacier['slimes'] if t is not s)):
                    d = math.hypot(x - ox, y - oy)
                    if best is None or d < best[0]:
                        best = (d, x, y)
            assert best, 'no clear spot for a displaced wyrm'
            s['x'], s['y'] = round(best[1], 2), round(best[2], 2)
            moved += 1
    seen, _ = flood(glacier, GLACIER_START)
    step = .5
    for name, (x, y) in [('arrival', GLACIER_ARRIVAL), ('gate', (GLACIER_GATE[0], GLACIER_GATE[1] + 2))] + [
            (s['kind'], (s['x'], s['y'])) for s in glacier['slimes']]:
        if not seen[int(y / step), int(x / step)]:
            raise SystemExit(f'Rimeveil: {name} at {x},{y} is unreachable from the camp')
    return moved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hub-only', action='store_true', help='update Lanternmere without rebuilding the fen')
    args = parser.parse_args()
    raw = PATH.read_text()
    meadow = json.loads(raw)
    assert json.dumps(meadow, indent=2) + '\n' == raw, 'map.txt is not in the canonical 2-space JSON layout'
    if args.hub_only:
        zone = next(z for z in meadow['zones'] if z['name'] == NAME)
        npcs, quests, objects, city = quest_hub()
        zone['objects'] = [o for o in zone['objects']
                           if not (city['x0'] - 2 < o['x'] < city['x1'] + 2 and city['y0'] - 2 < o['y'] < city['y1'] + 2
                                   and o['kind'] in ('house', 'chapel', 'fountain', 'stall', 'noticeboard', 'bench', 'lamp'))] + objects
        zone.update(npcs=npcs, quests=quests, city=city)
        ensure_elite(zone)
        missing = fen_unreachable(zone)
        if missing:
            raise SystemExit(f'unreachable from the arrival point: {missing}')
        spark_travel.ensure(meadow)
        PATH.write_text(json.dumps(meadow, indent=2) + '\n')
        print(f'Updated Lanternmere: {len(npcs)} NPCs, {len(quests)} quests. Terrain and enemy spawns preserved. Now run node scripts/sync-world.cjs')
        return
    later = meadow['zones'][3:]       # zones after Gloamfen (Skaldholm) survive a rebuild; re-run generate_skaldholm.py for its glacier gate
    meadow['zones'] = [z for z in meadow['zones'][:3] if z['name'] != NAME]
    moved = add_summit_gate(meadow, random.Random(20261005))   # its own stream: it only draws numbers on the first run
    zone = build(random.Random(20261006))
    ensure_elite(zone)
    missing = fen_unreachable(zone)
    if missing:
        raise SystemExit(f'unreachable from the arrival point: {missing}')
    meadow['zones'].append(zone)
    assert len(meadow['zones']) == 3, 'Gloamfen must be zone 3'
    meadow['zones'] += later
    spark_travel.ensure(meadow)
    PATH.write_text(json.dumps(meadow, indent=2) + '\n')
    kinds = {}
    for s in zone['slimes']:
        kinds[s['kind']] = kinds.get(s['kind'], 0) + 1
    print(f"Wrote zone 3 {zone['name']}: {len(zone['objects'])} objects, spawns {kinds}; summit gate added, {moved} wyrm spawn(s) moved. Now run node scripts/sync-world.cjs")


if __name__ == '__main__':
    main()
