#!/usr/bin/env python3
"""Seeded Sunward Vale, levels 65–70. Run after generate_stormglass.py.

The Elder Hollow is a deliberately sealed future instance under one ancient oak.
The rest of the valley is a green river landscape of ordinary trees and fields.
"""
import json
import math
import random
from pathlib import Path

import generate_gloamfen as fen
import mercenary_offers
import spark_travel
from quest_gear_rewards import add_reward

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ITEMS = ROOT / 'world/items.txt'
XP = json.loads((ROOT / 'world/levels.txt').read_text())
ZONE = 20
ARRIVAL = (13, 106)
RETURN = (7, 106)
SHORE_GATE = (121, 70)
SHORE_ARRIVAL = (113, 64)
NAME = 'Sunward Vale'


def obj(kind, x, y, r=0, **extra):
    return dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r,
                v=extra.pop('v', 0), **extra)


def npc(key, name, role, x, y, dialogue, offers=None, buys=False, look=None):
    return dict(id='sun_' + key, name=name, role=role, x=x, y=y,
                color='#ffe6a5', dialogue=dialogue, offers=offers or [], buys=buys,
                look=look or dict(skin='#b98b69', hair='#6e4c32', style='short',
                                  hat='straw', hatColor='#d6bb70'))


def kill(kind, count, label):
    return dict(kind='kill', target=kind, count=count, label=label)


def talk(who, label):
    return dict(kind='talk', target='sun_' + who, count=1, label=label)


def visit(where, label):
    return dict(kind='visit', target='sun_' + where, count=1, label=label)


def bring(item, count, label):
    return dict(kind='bring', target=item, count=count, label=label)


def quest(key, title, giver, description, objectives, level, gold,
          requires=None, repeatable=False, **extra):
    return add_reward(dict(id='sun_' + key, title=title, npc='sun_' + giver,
                           description=description, objectives=objectives,
                           level=level, rewardXp=XP[level - 1] // 10,
                           rewardGold=gold,
                           requires='sun_' + requires if requires else None,
                           repeatable=repeatable, **extra))


def people_and_quests():
    folk = [
        npc('miller', 'Ada Bell', 'Millbridge miller', 31, 102,
            'The Stormglass road ends at my wheat field. Come in from the wind and follow the river where the oaks begin.',
            look=dict(skin='#ae765b', hair='#643b2f', style='long', hat='straw', hatColor='#e2c67e')),
        npc('medic', 'Marta Fenwick', 'Village herbalist', 22, 115,
            'The sun is warm, but a wounded traveler still needs thyme and clean bandages.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_health_potion', label='Buy Health Potion', cost=30,
                  item='health_potion', tiered=True)]),
        npc('carpenter', 'Bram Wicket', 'Bridge carpenter', 40, 111,
            'I repair both bridges each spring. I cannot work while badgers are digging beneath their posts.',
            mercenary_offers.offers(),
            look=dict(skin='#9d7558', hair='#3f342a', style='short', hat='straw', hatColor='#aa8659')),
        npc('guide', 'Pip Rowan', 'Orchard guide', 44, 96,
            'There is a quick path through the west oakwood and a gentle one past the apple trees. Both reach the old crown.',
            look=dict(skin='#b78865', hair='#a84e39', style='short', hat='straw', hatColor='#caa65f')),
        npc('trader', 'Hettie Cobb', 'Millbridge provisions', 33, 119,
            'I buy what the woods leave you. Take a stew and sit where the mill wheel turns.',
            [dict(id='stew', label="Buy Traveler's Stew", cost=12,
                  item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel', cost=500,
                  bag='linen_satchel')], True),
        npc('keeper', 'Rowan Alder', 'Elder Hollow keeper', 101, 29,
            'The old oak is older than the village. Its roots form a stair, but the door below is still bound shut.',
            look=dict(skin='#835e4b', hair='#d2c39b', style='long', hat='hood', hatColor='#568054')),
        npc('stone', 'Millbridge Meeting Stone', 'Gather a party · hire fighters', 91, 29,
            'The stone gathers companions for 250 gold each. The Elder Hollow remains sealed.',
            mercenary_offers.offers(open_=True)),
    ]
    folk[0]['art'] = 'sun_miller'
    folk[5]['art'] = 'sun_keeper'
    folk[-1]['art'] = 'stone'
    quests = [
        quest('welcome', 'A Place at the Mill', 'miller',
              'Meet the herbalist, bridge carpenter and orchard guide of Millbridge.',
              [talk('medic', 'Meet Marta'), talk('carpenter', 'Meet Bram'),
               talk('guide', 'Meet Pip')], 65, 5200),
        quest('hares', 'Hares in the Hay', 'carpenter',
              'The unusually bold meadow hares are chewing through the south field.',
              [kill('meadowhare', 6, 'Drive off Meadow Hares')], 65, 5800, 'welcome'),
        quest('snails', 'The Orchard Shells', 'guide',
              'Bring the striped shells left by the huge snails among the apple trees.',
              [bring('sunback_shell', 5, 'Bring Sunback Shells')], 66, 6200, 'hares'),
        quest('foxes', 'Red Tails at Dusk', 'guide',
              'The foxes have grown fierce along the far riverbank.',
              [kill('brushfox', 6, 'Drive off Brush Foxes')], 67, 6800, 'snails'),
        quest('badgers', 'Under the Bridge', 'carpenter',
              'Keep the badgers from undermining the old bridge.',
              [kill('spadebadger', 5, 'Defeat Spadeclaw Badgers')], 68, 7400, 'foxes'),
        quest('honeyjaw', 'Old Honeyjaw', 'guide',
              'A bear with a wild hive on its back has claimed the north oakwood. Bring friends.',
              [kill('honeyjaw', 1, 'Defeat Old Honeyjaw')], 69, 11600,
              'foxes', group=True, recommendedPlayers=3),
        quest('warden', 'The Wicker Warden', 'keeper',
              'A towering scarecrow guards the Elder Hollow. Gather five companions.',
              [kill('wickerwarden', 1, 'Defeat the Wicker Warden')], 70, 14800,
              'badgers', group=True, recommendedPlayers=5),
        quest('roots', 'Below the Elder Crown', 'keeper',
              'Study the sealed stair and consult the Meeting Stone. The descent awaits another expedition.',
              [visit('elder_hollow', 'Inspect the Elder Hollow'),
               talk('stone', 'Speak with the Meeting Stone')], 70, 9000, 'badgers'),
        quest('patrol', 'Keep the Meadows Clear', 'miller',
              'Walk the grassland and keep the village paths clear.',
              [kill('meadowhare', 3, 'Drive off Meadow Hares'),
               kill('brushfox', 3, 'Drive off Brush Foxes')], 65, 4600,
              'welcome', True),
    ]
    return folk, quests


def distance_to_path(x, y, paths):
    best = 999
    for path in paths:
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def river_y(x):
    return 70 + 5 * math.sin((x - 15) / 17)


def build():
    rng = random.Random(20261010)
    # A true fork: the west trail crosses at the mill, while the orchard track
    # crosses farther east; the routes meet in the old oakwood.
    paths = [
        [(7, 106), (31, 102), (42, 88), (48, 75), (48, 57), (29, 44),
         (34, 29), (63, 27), (83, 34), (105, 25)],
        [(31, 102), (60, 103), (81, 100), (96, 82), (96, 65),
         (94, 48), (83, 34)],
        [(48, 57), (66, 55), (94, 48)],
    ]
    objects = [
        obj('vale_cottage', 18, 103, width=5, depth=4, v=0),
        obj('vale_cottage', 42, 101, width=5, depth=4, v=1),
        obj('vale_cottage', 19, 123, width=5, depth=4, v=2),
        obj('vale_cottage', 45, 123, width=5, depth=4, v=0),
        obj('watermill', 34, 78, width=6, depth=4),
        obj('stone_bridge', 48, round(river_y(48), 2), v=0),
        obj('stone_bridge', 96, round(river_y(96), 2), v=1),
        obj('elder_hollow_gate', 106, 19, width=9, depth=4,
            place='sun_elder_hollow'),
        obj('wild_hive', 26, 28, r=1.1, place='sun_honeywood'),
        obj('wicker_post', 108, 41, r=.9, place='sun_wicker_field'),
    ]
    # The river is real collision water. Two broad gaps beneath painted bridges
    # leave clear, testable crossings for players and NPC paths.
    for x in range(12, 119, 2):
        if min(abs(x - 48), abs(x - 96)) < 6:
            continue
        objects.append(obj('water', x, river_y(x), 1.7))
    # Orchard rows and a loose grove are visually regular trees, not crystals,
    # pylons or monster-shaped rocks.
    for row in range(4):
        for col in range(7):
            x, y = 55 + col * 8, 86 + row * 8
            if distance_to_path(x, y, paths) > 4.5 and math.hypot(x - 96, y - 65) > 7:
                objects.append(obj('apple_tree', x, y, .9, v=(row + col) % 3))
    for kind, count, radius in [('oak_tree', 82, 1.0),
                                 ('birch_tree', 55, .68),
                                 ('willow_tree', 18, .85),
                                 ('hawthorn_bush', 70, .34),
                                 ('wildflowers', 95, .12),
                                 ('haystack', 14, .58)]:
        placed = 0
        for _ in range(80000):
            if placed == count:
                break
            x, y = rng.uniform(7, 121), rng.uniform(7, 121)
            if (x < 52 and y > 87) or distance_to_path(x, y, paths) < (4.4 if radius > .5 else 3.1):
                continue
            if abs(y - river_y(x)) < 4.1:
                continue
            if math.hypot(x - 106, y - 19) < 12 or math.hypot(x - 26, y - 34) < 10 or math.hypot(x - 107, y - 44) < 10:
                continue
            if any(math.hypot(x - o['x'], y - o['y']) < radius + max(o['r'], o.get('width', 0) / 2,
                                                                     o.get('depth', 0) / 2) + .65
                   for o in objects):
                continue
            objects.append(obj(kind, x, y, radius, v=rng.randrange(4)))
            placed += 1
        assert placed == count, (kind, placed)
    spawns = [dict(kind='honeyjaw', x=26, y=34),
              dict(kind='wickerwarden', x=107, y=45)]
    for kind, count, lo, hi in [('meadowhare', 10, 86, 111),
                                ('sunbacksnail', 10, 75, 108),
                                ('brushfox', 10, 35, 65),
                                ('spadebadger', 10, 25, 74)]:
        for _ in range(count):
            for _attempt in range(8000):
                x, y = rng.uniform(10, 118), rng.uniform(lo, hi)
                if (x < 53 and y > 88) or math.hypot(x - ARRIVAL[0], y - ARRIVAL[1]) < 12:
                    continue
                if math.hypot(x - 106, y - 19) < 12 or math.hypot(x - 26, y - 34) < 13 or math.hypot(x - 107, y - 45) < 13:
                    continue
                if distance_to_path(x, y, paths) < 3.3 or abs(y - river_y(x)) < 4:
                    continue
                if any(math.hypot(x - s['x'], y - s['y']) <
                       (13 if s['kind'] in ('honeyjaw', 'wickerwarden') else 6)
                       for s in spawns):
                    continue
                if any(math.hypot(x - o['x'], y - o['y']) <
                       max(o['r'], o.get('width', 0) / 2,
                           o.get('depth', 0) / 2) + 1.7 for o in objects):
                    continue
                spawns.append(dict(kind=kind, x=round(x, 2), y=round(y, 2)))
                break
            else:
                raise RuntimeError('cannot place ' + kind)
    people, quests = people_and_quests()
    zone = dict(name=NAME, theme='sunward',
                tagline='A green river valley of old oaks, apple rows, and a door beneath the roots',
                size=128, levels=[65, 70],
                spawn=dict(x=ARRIVAL[0], y=ARRIVAL[1]),
                paths=[[[x, y] for x, y in path] for path in paths],
                objects=objects, slimes=spawns, npcs=people,
                places=[dict(id='sun_elder_hollow', name='The Elder Hollow',
                             x=106, y=19, r=6),
                        dict(id='sun_honeywood', name='Honeywood Clearing',
                             x=26, y=28, r=4),
                        dict(id='sun_wicker_field', name='The Wicker Field',
                             x=108, y=41, r=4)],
                quests=quests,
                city=dict(name='Millbridge', x0=9, x1=51, y0=88, y1=125,
                          plaza=dict(x=31, y=106), radius=6,
                          entry=dict(x=13, y=106)),
                futureInstance=dict(name='The Elder Hollow', level=70,
                                    players=5, status='sealed', x=106, y=19,
                                    description='A vast split oak frames a sunlit root stair to a sealed five-player descent.'),
                portals=[dict(id='sun_stormglass_gate', name='The Sunward Cut',
                              x=RETURN[0], y=RETURN[1], r=1.2,
                              to=19, tx=SHORE_ARRIVAL[0], ty=SHORE_ARRIVAL[1],
                              look='sunward')])
    check(zone)
    return zone


def check(zone):
    seen, _ = fen.flood(zone, ARRIVAL)
    for target in [*zone['npcs'], *zone['slimes'], *zone['portals'],
                   dict(x=106, y=25), dict(x=48, y=72), dict(x=96, y=62)]:
        assert seen[int(target['y'] / .5), int(target['x'] / .5)], f'unreachable: {target}'
    assert all(math.hypot(s['x'] - ARRIVAL[0], s['y'] - ARRIVAL[1]) >= 8
               for s in zone['slimes'])
    for q in zone['quests']:
        assert len('quest:accept:' + q['id']) <= 32, q['id']
    assert len(zone['slimes']) == 42 and len(zone['quests']) == 9


def open_shore_gate(shore):
    shore['objects'] = [o for o in shore['objects']
                        if not (o['x'] > 109 and 63 < o['y'] < 77)]
    road = [[101, 70], [113, 70], [121, 70]]
    shore['paths'] = [p for p in shore['paths'] if p != road]
    shore['paths'].append(road)
    shore['portals'] = [p for p in shore['portals']
                        if p['id'] not in ('stormglass_wake_gate', 'stormglass_sun_gate')]
    shore['portals'].append(dict(id='stormglass_sun_gate',
                                 name='The Sunward Cut', x=SHORE_GATE[0],
                                 y=SHORE_GATE[1], r=1.2, to=ZONE,
                                 tx=ARRIVAL[0], ty=ARRIVAL[1], look='sunward'))
    seen, _ = fen.flood(shore, (shore['spawn']['x'], shore['spawn']['y']))
    assert seen[int(SHORE_GATE[1] / .5), int(SHORE_GATE[0] / .5)]
    assert seen[int(SHORE_ARRIVAL[1] / .5), int(SHORE_ARRIVAL[0] / .5)]
    assert all(math.hypot(s['x'] - SHORE_ARRIVAL[0], s['y'] - SHORE_ARRIVAL[1]) >= 8
               for s in shore['slimes'])


def main():
    world = json.loads(MAP.read_text())
    assert world['zones'][18]['name'] == 'The Stormglass Shore'
    later = world['zones'][ZONE:]
    world['zones'] = world['zones'][:ZONE - 1]
    open_shore_gate(world['zones'][18])
    world['zones'].append(build())
    world['zones'].extend(later)
    if any(z.get('name') == 'The Ribbonwild' for z in later):
        from generate_ribbonwild import open_sunward_gate
        open_sunward_gate(world['zones'][ZONE - 1])
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world, indent=2) + '\n')
    items = json.loads(ITEMS.read_text())
    obsolete = {'embercoil_scale', 'cinderwing_membrane', 'magnetite_plate',
                'stormforged_core', 'ashglass_heart', 'regent_spark'}
    items = [i for i in items if i['id'] not in obsolete]
    for key, name, sell in [('hare_whisker', 'Meadow Hare Whisker', 670),
                            ('sunback_shell', 'Sunback Shell', 710),
                            ('fox_tail_tuft', 'Brush Fox Tail Tuft', 760),
                            ('badger_claw', 'Spadeclaw Badger Claw', 830),
                            ('honeyjaw_comb', 'Honeyjaw Comb', 2700),
                            ('wicker_heart', 'Wicker Heart', 3400)]:
        if not any(i['id'] == key for i in items):
            items.append(dict(id=key, name=name, kind='material',
                              rarity='common', sell=sell))
    ITEMS.write_text(json.dumps(items, indent=2) + '\n')
    print(f'{NAME}: {len(world["zones"][19]["objects"])} objects, '
          '42 enemies, 9 quests')


if __name__ == '__main__':
    main()
