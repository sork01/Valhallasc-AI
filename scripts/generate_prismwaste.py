#!/usr/bin/env python3
"""Build the level 45-50 Prismwaste beyond Astralhollow. Idempotent."""
import json
import math
import random
from pathlib import Path

import generate_gloamfen as fen
import spark_travel
from quest_gear_rewards import add_reward

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
ZONE = 14
SIZE = 128
ARRIVAL = (64, 116)
RETURN = (64, 120)
ASTRAL_GATE = (64, 12)
ASTRAL_ARRIVAL = (64, 21)
NAME = 'The Prismwaste'


def obj(kind, x, y, r, v=0, **extra):
    return dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r, v=v, **extra)


def npc(id_, name, role, x, y, dialogue, offers=None, buys=False):
    return dict(id='prism_' + id_, name=name, role=role, x=x, y=y,
                color='#f4c486', dialogue=dialogue, offers=offers or [], buys=buys,
                look=dict(hair='#d6af88', skin='#dcbba0', style='short'))


def quest(id_, title, giver, description, objectives, level, gold, requires=None,
          repeatable=False, **extra):
    return add_reward(dict(id='prism_' + id_, title=title, npc='prism_' + giver,
                           description=description, objectives=objectives, level=level,
                           rewardXp=LEVELS[level - 1] // 10, rewardGold=gold,
                           requires='prism_' + requires if requires else None,
                           repeatable=repeatable, **extra))


def kill(kind, count, label):
    return dict(kind='kill', target=kind, count=count, label=label)


def bring(item, count, label):
    return dict(kind='bring', target=item, count=count, label=label)


def talk(person, label):
    return dict(kind='talk', target='prism_' + person, count=1, label=label)


def content():
    import mercenary_offers as mo
    people = [
        npc('keeper', 'Mara Vey', 'Keeper of the Last Shade', 54, 114,
            'The waste reflects every star but gives no shade. Meet the refuge crew before crossing the first mirror ridge.'),
        npc('healer', 'Sela Dawnglass', 'Healer', 74, 114,
            'Sit in the shadow of the awning. I can set broken bones, even when the glass remembers them.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_health_potion', label='Buy Health Potion', cost=30,
                  item='health_potion', tiered=True)]),
        npc('scout', 'Tarin Glassrunner', 'Ridge scout', 55, 121,
            'The jackals hunt reflections. The harriers hunt the things that cast them. I need both trails cleared.',
            mo.offers()),
        npc('scholar', 'Asha of the Lens', 'Mirror scholar', 73, 121,
            'At the far ridge two enormous things move: the Queen inside the mirrors and the Sunshard at the broken crown. Bring allies.',
            mo.offers()),
        npc('trader', 'Pell Ashcoin', 'Provisioner and material buyer', 69, 109,
            'I buy every fragment the waste gives up. The glass is worth more than gold to the lens makers.',
            [dict(id='buy_traveler_stew', label="Buy Traveler's Stew", cost=12,
                  item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel', cost=500, bag='linen_satchel')], True),
    ]
    quests = [
        quest('welcome', 'The Last Shade', 'keeper', 'Meet the crew under the canvas awning.',
              [talk('healer', 'Speak with Sela'), talk('scout', 'Speak with Tarin'),
               talk('scholar', 'Speak with Asha')], 45, 1000),
        quest('jackals', 'What the Mirrors Hunt', 'scout', 'Thin the packs that pursue travellers along the southern ridge.',
              [kill('miragejackal', 6, 'Defeat Mirage Jackals')], 45, 1200, 'welcome'),
        quest('scarabs', 'A Thousand Broken Lenses', 'keeper', 'The glass scarabs are eating the trail markers.',
              [kill('shardscarab', 6, 'Defeat Shard Scarabs')], 46, 1300, 'jackals'),
        quest('wings', 'Sharp as Sunlight', 'scout', 'Bring wings for a wind gauge before the next sandstorm.',
              [bring('harrier_pinions', 5, 'Bring Harrier Pinions')], 47, 1450, 'scarabs'),
        quest('harriers', 'The Sky in Pieces', 'scout', 'Drive the glass harriers away from the upper pass.',
              [kill('glassharrier', 6, 'Defeat Glass Harriers')], 47, 1500, 'scarabs'),
        quest('sentinels', 'The Broken Watch', 'scholar', 'The old prism sentinels still guard an observatory that no longer exists.',
              [kill('prismsentinel', 5, 'Defeat Prism Sentinels')], 48, 1700, 'harriers'),
        quest('queen', 'The Queen Behind the Glass', 'scout', 'A reflected queen leads the jackals from the western mirror court. Bring a group.',
              [kill('mirrorqueen', 1, 'Defeat the Mirror Queen')], 49, 2500, 'sentinels',
              group=True, recommendedPlayers=3),
        quest('sunshard', 'Crown of the White Sun', 'scholar', 'At the northern crown, the Sunshard is burning the sky white. Bring a full group.',
              [kill('sunshard', 1, 'Defeat the Sunshard')], 50, 3800, 'sentinels',
              group=True, recommendedPlayers=5),
        quest('survey', 'A Map of Both Skies', 'keeper', 'Prove the route from the refuge to the crown is safe.',
              [kill('miragejackal', 3, 'Defeat Mirage Jackals'),
               kill('shardscarab', 3, 'Defeat Shard Scarabs'),
               kill('glassharrier', 3, 'Defeat Glass Harriers'),
               kill('prismsentinel', 3, 'Defeat Prism Sentinels')], 50, 2400, 'sentinels'),
        quest('patrol', 'Keep the Shade Standing', 'keeper', 'Clear the paths nearest the refuge.',
              [kill('miragejackal', 4, 'Defeat Mirage Jackals'),
               kill('shardscarab', 4, 'Defeat Shard Scarabs')], 45, 1000, 'welcome', True),
    ]
    return people, quests


def dist_to_path(x, y, paths):
    best = 999.
    for path in paths:
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0., min(1., ((x-ax)*dx + (y-ay)*dy) / (dx*dx + dy*dy)))
            best = min(best, math.hypot(x-ax-dx*t, y-ay-dy*t))
    return best


def build():
    rng = random.Random(20261008)
    paths = [
        [(64,116),(64,100),(48,88),(32,75),(52,62),(79,50),(95,35),(64,14)],
        [(64,100),(86,88),(102,72),(79,50)],
        [(48,88),(24,60),(31,40),(64,14)],
    ]
    objects = []
    # Three broken, staggered mirror ridges. Their broad gaps remain visible on the trail.
    for y, gap in ((89,64),(62,32),(37,94)):
        for i in range(5,123,4):
            if abs(i-gap) < 11:
                continue
            objects.append(obj('mirrorwall', i, y + 1.1*math.sin(i*.3+y), 1.05, i % 4))
    objects += [obj('shade_tent', 64, 110, 2.0, width=5, depth=4),
                obj('lens_pillar', 64, 106, .75),
                obj('lens_pillar', 61, 120, .45), obj('lens_pillar', 67, 120, .45),
                obj('broken_crown', 64, 9, 1.4)]
    for kind, count, radius in [('sunspire',100,.8),('glassstone',85,.55),('saltbrush',85,.25)]:
        placed = 0
        for _ in range(35000):
            if placed == count:
                break
            x,y = rng.uniform(6,122),rng.uniform(6,122)
            if (46 < x < 82 and y > 103) or dist_to_path(x,y,paths) < 3.0:
                continue
            if any(math.hypot(x-o['x'],y-o['y']) < radius+o['r']+1.25 for o in objects):
                continue
            objects.append(obj(kind,x,y,radius,rng.randrange(4)))
            placed += 1
        assert placed == count, (kind,placed)
    spawns = []
    # Two isolated elite courts, more than a pull radius from the ordinary hunt trail.
    fixed = [('mirrorqueen', 17, 48), ('sunshard', 64, 19)]
    for kind,x,y in fixed:
        assert all(math.hypot(x-o['x'],y-o['y']) > o['r']+2 for o in objects)
        spawns.append(dict(kind=kind,x=x,y=y))
    for kind,count,lo,hi in [('miragejackal',11,91,103),('shardscarab',10,68,83),
                             ('glassharrier',10,46,59),('prismsentinel',9,23,35)]:
        for _ in range(count):
            for _attempt in range(3000):
                x,y=rng.uniform(10,118),rng.uniform(lo,hi)
                if (46 < x < 82 and y > 103) or math.hypot(x-64,y-116)<12:
                    continue
                if any(math.hypot(x-s['x'],y-s['y'])<(14 if s['kind'] in ('mirrorqueen','sunshard') else 6) for s in spawns):
                    continue
                if any(math.hypot(x-o['x'],y-o['y'])<o['r']+1.1 for o in objects):
                    continue
                spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)))
                break
            else:
                raise RuntimeError(f'cannot place {kind}')
    people, quests = content()
    zone = dict(name=NAME, theme='prismwaste', tagline='Where a second sky breaks beneath your feet',
                size=SIZE, levels=[45,50], spawn=dict(x=64,y=116),
                paths=[[[x,y] for x,y in path] for path in paths], objects=objects,
                slimes=spawns, npcs=people, places=[], quests=quests,
                city=dict(name='The Last Shade',x0=47,x1=81,y0=105,y1=124,
                          plaza=dict(x=64,y=114),radius=5,entry=dict(x=64,y=120)),
                portals=[dict(id='prism_astral_gate',name='The Starbreak',x=64,y=120,r=1.2,
                              to=13,tx=ASTRAL_ARRIVAL[0],ty=ASTRAL_ARRIVAL[1],look='prismwaste')])
    check(zone)
    return zone


def check(zone):
    seen,_ = fen.flood(zone,ARRIVAL)
    for x,y,label in [(RETURN[0],RETURN[1],'return gate'),(17,48,'Queen'),(64,19,'Sunshard')]:
        assert seen[int(y/.5),int(x/.5)], f'{label} unreachable'
    for entry in zone['slimes']+zone['npcs']:
        assert seen[int(entry['y']/.5),int(entry['x']/.5)], f'{entry} unreachable'
    for s in zone['slimes']:
        assert math.hypot(s['x']-64,s['y']-116)>8
    assert len(zone['objects'])>=300 and len(zone['slimes'])==42


def open_astral_gate(astral):
    astral['objects'] = [o for o in astral['objects'] if
                         math.hypot(o['x']-64,o['y']-12)>o['r']+3 and
                         not (10<=o['y']<=23 and abs(o['x']-64)<o['r']+2.5)]
    astral['slimes'] = [s for s in astral['slimes'] if math.hypot(s['x']-64,s['y']-ASTRAL_ARRIVAL[1])>9]
    astral['portals'] = [p for p in astral['portals'] if p['id']!='astral_prism_gate']
    astral['portals'].append(dict(id='astral_prism_gate',name='The Starbreak',x=64,y=12,r=1.2,
                                  to=ZONE,tx=64,ty=116,look='prismwaste'))


def main():
    world=json.loads(MAP.read_text())
    later=world['zones'][ZONE:]
    world['zones']=world['zones'][:ZONE-1]
    assert len(world['zones'])==ZONE-1
    zone=build()
    open_astral_gate(world['zones'][12])
    world['zones'].append(zone)
    world['zones'].extend(later)
    if any(z.get('name')=='The Obsidian Orrery' for z in later):
        from generate_orrery import open_prism_gate
        open_prism_gate(world['zones'][ZONE-1])
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    print(f'{NAME}: {len(zone["objects"])} objects, {len(zone["slimes"])} enemies, {len(zone["quests"])} quests')


if __name__=='__main__':
    main()
