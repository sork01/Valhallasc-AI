#!/usr/bin/env python3
"""Generate Astralhollow, the level 40–45 overworld beyond Nacrehold.

An overgrown impact basin: living starglass groves, observatory ruins, five
original enemy families, a lantern-lit sanctuary and a gate beside the arrival.
Re-running is idempotent and preserves all other zones.
"""
import argparse
import json
import math
import random
from pathlib import Path

import generate_gloamfen as fen
import spark_travel
from quest_gear_rewards import add_reward

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
NAME = 'Astralhollow'
ZONE = 13
SIZE = 128
ARRIVAL = (64, 116)
RETURN = (64, 120)
CITY_ZONE = 8  # zero-based Nacrehold entry in world['zones']
CITY_PUBLIC_ZONE = 9
CITY_GATE = (166, 24)
CITY_ARRIVAL = (166, 32)
XP = json.loads((ROOT / 'world/levels.txt').read_text())


def obj(kind, x, y, r, v=0, **extra):
    out = {'kind': kind, 'x': round(x, 2), 'y': round(y, 2), 'r': r, 'v': v}
    out.update(extra)
    return out


def npc(id_, name, role, x, y, dialogue, offers=None, buys=False):
    return {'id': 'astral_' + id_, 'name': name, 'role': role, 'x': x, 'y': y,
            'color': '#b9a4ff', 'offers': offers or [], 'buys': buys,
            'look': {'hair': '#d9d1ff', 'skin': '#e7c8b0', 'style': 'long'}, 'dialogue': dialogue}


def content():
    people = [
        npc('steward', 'Seren Starwatcher', 'Astral steward · Quest giver', 53, 115,
            'The stars fell here before the city was built. Now the hollow is waking. Help me chart what survived the descent.'),
        npc('healer', 'Ilyra Nightbloom', 'Sanctuary keeper', 75, 115,
            'The crystal remembers every wound, but it does not have to remember yours. Rest beneath the observatory lantern.',
            [{'id': 'blessing', 'label': 'Receive a healing blessing', 'cost': 0, 'heal': 10000},
             {'id': 'buy_health_potion', 'label': 'Buy Health Potion · 100 HP instantly', 'cost': 30, 'item': 'health_potion', 'tiered': True}]),
        npc('scholar', 'Vey Orison', 'Keeper of the star charts', 57, 111,
            'Every piece of starglass holds a direction. The wyrms have swallowed the old charts; bring their singing scales to my lens.'),
        npc('gardener', 'Thalia Moonroot', 'Astral gardener', 71, 111,
            'These flowers grew from the crater, not the soil. I need moth wings to learn what lets them bloom under an alien sky.'),
        npc('warden', 'Orun Nightshield', 'Trail warden', 55, 121,
            'The trails branch around the impact rings. Keep the beetles and dryads from the observatory lamps.'),
        npc('trader', 'Pell of the Nine Lights', 'Provisioner and material buyer', 73, 121,
            'A warm meal and a little glasslight go farther than bravery in the upper basin. I buy what the creatures leave behind.',
            [{'id': 'buy_traveler_stew', 'label': "Buy Traveler's Stew · 100 HP and mana over 8 s", 'cost': 12, 'item': 'traveler_stew', 'tiered': True},
             {'id': 'satchel', 'label': 'Buy Linen Satchel · 6 extra bag slots', 'cost': 500, 'bag': 'linen_satchel'}], True),
    ]
    def talk(target, label): return {'kind': 'talk', 'target': 'astral_' + target, 'label': label, 'count': 1}
    def kill(target, label, count): return {'kind': 'kill', 'target': target, 'label': label, 'count': count}
    def bring(target, label, count): return {'kind': 'bring', 'target': target, 'label': label, 'count': count}
    def quest(id_, title, giver, description, objectives, level, gold, requires=None, repeatable=False):
        return add_reward({'id': 'astral_' + id_, 'title': title, 'npc': 'astral_' + giver, 'description': description,
                'objectives': objectives, 'level': level, 'rewardXp': XP[level - 1] // 10,
                'rewardGold': gold, 'requires': 'astral_' + requires if requires else None, 'repeatable': repeatable})
    quests = [
        quest('welcome', 'A Map of Falling Stars', 'steward', 'Meet the observatory keepers before you take the trail.',
              [talk('healer', 'Speak with Ilyra Nightbloom'), talk('scholar', 'Speak with Vey Orison'), talk('warden', 'Speak with Orun Nightshield')], 40, 300),
        quest('moths', 'Ink the Void', 'steward', 'The first constellation is hidden behind a cloud of hungry Void Moths.',
              [kill('voidmoth', 'Defeat Void Moths', 6)], 40, 420, 'welcome'),
        quest('wyrms', 'The Crystal Remembers', 'steward', 'Break the singing Crystalwyrms and report what their scales reveal.',
              [kill('crystalwyrm', 'Defeat Crystalwyrms', 6)], 41, 520, 'moths'),
        quest('beetles', 'The Orbit Breakers', 'warden', 'The bronze beetles knock the waystones out of alignment.',
              [kill('orbitbeetle', 'Defeat Orbit Beetles', 6)], 42, 580, 'wyrms'),
        quest('dryads', 'Roots of the Eclipse', 'gardener', 'The dryads have begun to shade the living flowers with their black suns.',
              [kill('eclipsedryad', 'Defeat Eclipse Dryads', 6)], 43, 620, 'beetles'),
        quest('golems', 'The Last Falling Stone', 'scholar', 'The crater core still walks. Stop the meteor golems before they reach the sanctuary.',
              [kill('meteorgolem', 'Defeat Meteor Golems', 5)], 45, 800, 'dryads'),
        quest('garden', 'A Garden Under Strange Stars', 'gardener', 'Bring Void Wings so Thalia can coax the night flowers to seed.',
              [bring('voidwing', 'Bring Void Wings', 4)], 40, 410, 'welcome'),
        quest('lens', 'A Lens of Singing Glass', 'scholar', 'Crystalwyrm scales refract the lost constellation. Bring Vey enough to restore the lens.',
              [bring('astral_scale', 'Bring Astral Scales', 4)], 41, 480, 'wyrms'),
        quest('watch', 'The Warden\'s Round', 'warden', 'Walk the living trail and report to the keeper of the garden.',
              [talk('gardener', 'Speak with Thalia Moonroot'), talk('trader', 'Speak with Pell of the Nine Lights')], 42, 350, 'welcome'),
        quest('survey', 'A New Constellation', 'steward', 'Chart the whole basin by defeating each of its deeper guardians.',
              [kill('orbitbeetle', 'Defeat Orbit Beetles', 4), kill('eclipsedryad', 'Defeat Eclipse Dryads', 4), kill('meteorgolem', 'Defeat Meteor Golems', 2)], 44, 900, 'golems'),
        quest('patrol', 'Keep the Observatory Lit', 'warden', 'The starstones dim whenever monsters gather. Keep the route clear.',
              [kill('voidmoth', 'Defeat Void Moths', 3), kill('crystalwyrm', 'Defeat Crystalwyrms', 3)], 40, 500, 'welcome', True),
        quest('fragments', 'Gather the Fallen Light', 'scholar', 'Thin the deeper guardians to keep the star chart from splintering again.',
              [kill('eclipsedryad', 'Defeat Eclipse Dryads', 3), kill('meteorgolem', 'Defeat Meteor Golems', 2)], 44, 700, 'golems', True),
    ]
    return people, quests


def clear(x, y, objects, margin=1.0):
    return 5 < x < SIZE - 5 and 5 < y < SIZE - 5 and all(
        math.hypot(x - o['x'], y - o['y']) >= o['r'] + margin for o in objects
    )


def build():
    rng = random.Random(20261021)
    objects = []
    # Broken impact rings with deliberately open lanes: the middle path and two
    # sweeping side trails stay broad enough for travel and combat.
    for band, y in enumerate((22, 42, 62, 82, 101)):
        for i in range(27):
            x = 7 + i * 4.4 + (band % 2) * 1.4
            if 55 <= x <= 73 or (band % 2 == 0 and 18 <= x <= 25) or (band % 2 and 101 <= x <= 109):
                continue
            ry = y + 2.2 * math.sin(i * .8 + band) + rng.uniform(-.6, .6)
            objects.append(obj('crystal', x, ry, rng.uniform(.72, 1.12), rng.randrange(4)))

    # The observatory court and its luminous waymarkers are the first landmarks
    # on arrival. The return portal is four steps in front of the landing point.
    objects.extend([
        obj('observatory', 64, 106, 2.2, width=5, depth=4),
        obj('starwell', 64, 112, .9),
        obj('astralhouse', 51, 108, 1.8, width=3.2, depth=3.0),
        obj('astralhouse', 77, 108, 1.8, width=3.2, depth=3.0),
    ])
    for x, y in ((54, 111), (74, 111), (54, 120), (74, 120), (61.8, 120), (66.2, 120)):
        objects.append(obj('astrolamp', x, y, .35, rng.randrange(4)))
    for x, y in ((39, 91), (89, 91), (29, 68), (99, 68), (37, 43), (91, 43), (64, 18)):
        objects.append(obj('obelisk', x, y, .9, rng.randrange(4)))

    # Living groves and fallen starstone are placed after the landmarks. Leave
    # the sanctuary, gate, walkable trail and spawn positions clear.
    trails = [[(64, 116), (64, 94), (66, 75), (62, 55), (64, 35), (64, 12)],
              [(64, 94), (37, 86), (24, 69), (37, 47), (64, 35)],
              [(64, 94), (93, 85), (107, 65), (90, 45), (64, 35)]]
    def trail_distance(x, y):
        best = 999
        for trail in trails:
            for (ax, ay), (bx, by) in zip(trail, trail[1:]):
                dx, dy = bx - ax, by - ay
                t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
                best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
        return best
    for kind, count, radius in [('astraltree', 100, .52), ('starstone', 90, .45),
                                ('astralshrub', 70, .28), ('starbloom', 55, .17)]:
        placed = 0
        for _ in range(30000):
            if placed == count:
                break
            x, y = rng.uniform(6, 122), rng.uniform(7, 121)
            if (45 < x < 83 and y > 104) or trail_distance(x, y) < 2.7:
                continue
            if any(math.hypot(x - nx, y - ny) < 3.5 for nx, ny in ((53, 115), (75, 115), (76, 119))):
                continue
            if clear(x, y, objects, radius + .5):
                objects.append(obj(kind, x, y, radius, rng.randrange(4)))
                placed += 1
        assert placed == count, (kind, placed)

    # Five bands, with the deepest family at the north observatory.
    spawns = []
    bands = [
        ('voidmoth', 12, 102, 18),
        ('crystalwyrm', 10, 84, 24),
        ('orbitbeetle', 10, 65, 27),
        ('eclipsedryad', 9, 45, 27),
        ('meteorgolem', 7, 24, 26),
    ]
    for kind, count, y, spread in bands:
        for _ in range(count):
            for _attempt in range(1000):
                x = rng.uniform(15, 113)
                sy = rng.uniform(y - spread / 2, y + spread / 2)
                if math.hypot(x - ARRIVAL[0], sy - ARRIVAL[1]) < 13 or (45 < x < 83 and sy > 103):
                    continue
                if all(math.hypot(x - s['x'], sy - s['y']) >= 6 for s in spawns) and clear(x, sy, objects, .7):
                    spawns.append({'kind': kind, 'x': round(x, 2), 'y': round(sy, 2)})
                    break
            else:
                raise RuntimeError(f'could not place {kind}')

    path = [[x, y] for x, y in trails[0]]
    people, quests = content()
    zone = {
        'name': NAME,
        'theme': 'astral',
        'tagline': 'Where fallen stars remember the shape of the sky',
        'size': SIZE,
        'levels': [40, 45],
        'spawn': {'x': ARRIVAL[0], 'y': ARRIVAL[1]},
        'paths': [path] + [[[x, y] for x, y in trail] for trail in trails[1:]],
        'objects': objects,
        'slimes': spawns,
        'npcs': people,
        'places': [],
        'quests': quests,
        'city': {'name': 'Astralhollow', 'x0': 45, 'x1': 83, 'y0': 106, 'y1': 124, 'plaza': {'x': 64, 'y': 116}, 'radius': 5, 'entry': {'x': 64, 'y': 120}},
        'portals': [{
            'id': 'astral_nacre_gate', 'name': 'The Nacrehold Starway',
            'x': RETURN[0], 'y': RETURN[1], 'r': 1.2,
            'to': CITY_PUBLIC_ZONE, 'tx': CITY_ARRIVAL[0], 'ty': CITY_ARRIVAL[1], 'look': 'astral',
        }],
    }
    check(zone)
    return zone


def check(zone):
    seen, _ = fen.flood(zone, ARRIVAL)
    assert seen[int(RETURN[1] / .5), int(RETURN[0] / .5)], 'return gate is unreachable'
    assert RETURN[1] > ARRIVAL[1] and math.dist(RETURN, ARRIVAL) <= 4.5, 'return gate must be in front of the arrival plaza'
    for npc_ in zone['npcs']:
        assert seen[int(npc_['y'] / .5), int(npc_['x'] / .5)], f'{npc_["id"]} is unreachable'
    for s in zone['slimes']:
        assert seen[int(s['y'] / .5), int(s['x'] / .5)], f'{s} is unreachable'
        assert math.hypot(s['x'] - ARRIVAL[0], s['y'] - ARRIVAL[1]) >= 8, f'{s} too close to arrival'
        assert all(math.hypot(s['x'] - t['x'], s['y'] - t['y']) >= 6 for t in zone['slimes'] if t is not s)
    assert all(5 < p['x'] < SIZE - 5 and 5 < p['y'] < SIZE - 5 for p in zone['slimes'])
    assert len(zone['objects']) >= 400 and {o['kind'] for o in zone['objects']} >= {'astraltree', 'starstone', 'crystal', 'starbloom', 'astralshrub', 'observatory', 'astrolamp'}


def open_city_gate(city, world):
    city['objects'] = [o for o in city['objects'] if math.hypot(o['x'] - CITY_GATE[0], o['y'] - CITY_GATE[1]) > o['r'] + 3]
    city['objects'] += [obj('post', CITY_GATE[0] - 1.5, CITY_GATE[1], .45), obj('post', CITY_GATE[0] + 1.5, CITY_GATE[1], .45)]
    city['portals'] = [p for p in city.get('portals', []) if p['id'] != 'nacre_astral_gate']
    city['portals'].append({'id': 'nacre_astral_gate', 'name': 'The Astralhollow Starway', 'x': CITY_GATE[0], 'y': CITY_GATE[1], 'r': 1.2, 'to': ZONE, 'tx': ARRIVAL[0], 'ty': ARRIVAL[1], 'look': 'astral'})




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plot')
    args = parser.parse_args()
    world = json.loads(PATH.read_text())
    zone = build()
    later = world['zones'][ZONE:] if len(world['zones']) >= ZONE else []
    world['zones'] = world['zones'][:ZONE - 1]
    assert len(world['zones']) == ZONE - 1, f'expected zone {ZONE}, found {len(world["zones"]) + 1}'
    open_city_gate(world['zones'][CITY_ZONE], world)
    # Remove the temporary alternate entrance if an earlier development run added it.
    world['zones'][3]['portals'] = [p for p in world['zones'][3].get('portals', []) if p['id'] != 'skald_astral_gate']
    world['zones'].append(zone)
    world['zones'].extend(later)
    if any(z.get('name') == 'The Prismwaste' for z in later):
        from generate_prismwaste import open_astral_gate
        open_astral_gate(world['zones'][ZONE - 1])
    spark_travel.ensure(world)
    PATH.write_text(json.dumps(world, indent=2) + '\n')
    if args.plot:
        from PIL import Image, ImageDraw
        im = Image.new('RGB', (SIZE * 4, SIZE * 4), '#10152d')
        d = ImageDraw.Draw(im)
        for p in zone['paths']:
            d.line([(x * 4, y * 4) for x, y in p], fill='#d7bd72', width=16)
        for o in zone['objects']:
            c = '#83e7ff' if o['kind'] == 'crystal' else '#52608b' if o['kind'] == 'starstone' else '#3d734b'
            r = max(.4, o['r']) * 4
            d.ellipse((o['x'] * 4 - r, o['y'] * 4 - r, o['x'] * 4 + r, o['y'] * 4 + r), fill=c)
        for s in zone['slimes']:
            d.ellipse((s['x'] * 4 - 12, s['y'] * 4 - 12, s['x'] * 4 + 12, s['y'] * 4 + 12), outline='#ffcf66', width=2)
        im.save(args.plot)
    print(f'Wrote {NAME} as zone {ZONE}: {len(zone["objects"])} objects, {len(zone["slimes"])} enemies')


if __name__ == '__main__':
    main()
