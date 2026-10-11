#!/usr/bin/env python3
"""Seeded level 70–75 pinwheel festival, appended after Sunward Vale."""
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
ZONE = 21
NAME = 'The Ribbonwild'
ARRIVAL = (12, 70)
RETURN = (6, 70)
SUN_GATE = (121, 24)
SUN_ARRIVAL = (112, 26)
CENTER = (72, 67)


def obj(kind, x, y, r=0, **extra):
    return dict(kind=kind, x=round(x, 2), y=round(y, 2), r=r,
                v=extra.pop('v', 0), **extra)


def npc(key, name, role, x, y, dialogue, offers=None, buys=False, look=None):
    return dict(id='ribbon_' + key, name=name, role=role, x=x, y=y,
                color='#fff0b5', dialogue=dialogue, offers=offers or [], buys=buys,
                look=look or dict(skin='#bd8365', hair='#714d54', style='long',
                                  hat='feather', hatColor='#e0739d'))


def kill(kind, count, label):
    return dict(kind='kill', target=kind, count=count, label=label)


def talk(key, label):
    return dict(kind='talk', target='ribbon_' + key, count=1, label=label)


def visit(key, label):
    return dict(kind='visit', target='ribbon_' + key, count=1, label=label)


def bring(item, count, label):
    return dict(kind='bring', target=item, count=count, label=label)


def quest(key, title, giver, description, objectives, level, gold,
          requires=None, repeatable=False, **extra):
    return add_reward(dict(id='ribbon_' + key, title=title, npc='ribbon_' + giver,
                           description=description, objectives=objectives,
                           level=level, rewardXp=XP[level - 1] // 10,
                           rewardGold=gold,
                           requires='ribbon_' + requires if requires else None,
                           repeatable=repeatable, **extra))


def people_and_quests():
    people = [
        npc('host', 'Mira Vell', 'Jubilee host', 32, 64,
            'Four color courts and one great procession. The Pavilion waits at the far end, but its curtain is bound shut.'),
        npc('medic', 'Saffi Lark', 'Festival physician', 22, 81,
            'The best remedy is shade, water and a little music.',
            [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
             dict(id='buy_health_potion', label='Buy Health Potion', cost=30,
                  item='health_potion', tiered=True)]),
        npc('tailor', 'Tovin Tassel', 'Ribbon tailor', 38, 79,
            'My silk keeps vanishing into the geckos’ bright tails.',
            mercenary_offers.offers()),
        npc('keeper', 'Iona Bell', 'Pavilion keykeeper', 111, 58,
            'The Thousandfold Pavilion remembers every performer. None may enter while the masks still sing outside.'),
        npc('naturalist', 'Perri Finch', 'Garden naturalist', 31, 54,
            'The macaws know each petal court by heart. Watch where the yellow road meets the violet grass.'),
        npc('merchant', 'Jasper Gleam', 'Jubilee provisions', 24, 60,
            'The market buys field finds and sells stew and a spare bag.',
            [dict(id='stew', label="Buy Traveler's Stew", cost=12,
                  item='traveler_stew', tiered=True),
             dict(id='satchel', label='Buy Linen Satchel', cost=500,
                  bag='linen_satchel')], True),
        npc('stone', 'Jubilee Meeting Stone', 'Gather a party · hire fighters', 107, 76,
            'Five companions may face the masked giant. The Pavilion itself stays sealed.',
            mercenary_offers.offers(open_=True)),
    ]
    people[0]['art'] = 'ribbon_host'
    people[3]['art'] = 'ribbon_keeper'
    people[-1]['art'] = 'stone'
    quests = [
        quest('welcome', 'The Four Color Courts', 'host',
              'Meet the festival physician, tailor and garden naturalist.',
              [talk('medic', 'Meet Saffi'), talk('tailor', 'Meet Tovin'),
               talk('naturalist', 'Meet Perri')], 70, 6500),
        quest('geckos', 'Silk Tails', 'tailor',
              'The ribbon geckos have stolen spools from the pink court.',
              [kill('ribbongecko', 6, 'Defeat Ribbon Geckos')], 70, 7200, 'welcome'),
        quest('beetles', 'Lifted by Color', 'tailor',
              'Gather luminous beetle silk for a new parade banner.',
              [bring('balloon_silk', 5, 'Bring Balloon Silk')], 71, 7800, 'geckos'),
        quest('macaws', 'The Painted Flight', 'naturalist',
              'Calm the fierce macaws circling the blue court.',
              [kill('paintedmacaw', 6, 'Defeat Painted Macaws')], 72, 8400, 'beetles'),
        quest('jesters', 'A Dangerous Encore', 'host',
              'The tiny jesterlings have turned the circuit into a trap.',
              [kill('jesterling', 6, 'Defeat Jesterlings')], 73, 9100, 'macaws'),
        quest('gryphon', 'The Parade Gryphon', 'naturalist',
              'A feather-crowned gryphon has claimed the northern dance floor. Bring three friends.',
              [kill('paradegryphon', 1, 'Defeat the Parade Gryphon')], 74, 14500,
              'macaws', group=True, recommendedPlayers=3),
        quest('colossus', 'Behind the Mask', 'keeper',
              'The masked giant blocks the Pavilion. Gather five companions.',
              [kill('maskcolossus', 1, 'Defeat the Masquerade Colossus')], 75, 19000,
              'jesters', group=True, recommendedPlayers=5),
        quest('curtain', 'The Last Curtain', 'keeper',
              'Inspect the sealed pavilion and consult the Meeting Stone.',
              [visit('pavilion', 'Inspect the Thousandfold Pavilion'),
               talk('stone', 'Speak with the Meeting Stone')], 75, 11000, 'jesters'),
        quest('circuit', 'Keep the Colors Turning', 'host',
              'Keep the processional ring safe for every guest.',
              [kill('ribbongecko', 3, 'Defeat Ribbon Geckos'),
               kill('jesterling', 3, 'Defeat Jesterlings')], 70, 5600,
              'welcome', True),
    ]
    return people, quests


def dist_path(x, y, paths):
    best = 1e9
    for path in paths:
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            best = min(best, math.hypot(x-ax-t*dx, y-ay-t*dy))
    return best


def build():
    rng = random.Random(20261011)
    # A wheel, not a corridor: the processional ring has spokes into the
    # central color court, while the western market and eastern curtain anchor it.
    ring = [(72, 28), (97, 38), (108, 65), (97, 93), (72, 106),
            (46, 93), (36, 67), (46, 40), (72, 28)]
    paths = [ring, [(7, 70), (29, 70), (36, 67), (58, 67), (72, 67),
                    (88, 67), (108, 65), (119, 65)],
             [(72, 28), (72, 67), (72, 106)],
             [(46, 40), (72, 67), (97, 93)],
             [(46, 93), (72, 67), (97, 38)]]
    objects = [
        obj('grand_pavilion_gate', 120, 65, width=10, depth=5,
            place='ribbon_pavilion'),
        obj('silk_pavilion', 17, 54, width=5, depth=4, v=0),
        obj('silk_pavilion', 42, 54, width=5, depth=4, v=1),
        obj('silk_pavilion', 17, 88, width=5, depth=4, v=2),
        obj('silk_pavilion', 42, 88, width=5, depth=4, v=3),
        obj('painted_stall', 22, 50, width=3, depth=2, v=0),
        obj('painted_stall', 37, 48, width=3, depth=2, v=1),
        obj('painted_stall', 21, 91, width=3, depth=2, v=2),
        obj('painted_stall', 35, 92, width=3, depth=2, v=3),
        obj('parade_standard', 65, 20, r=.8, place='ribbon_gryphon_court'),
        obj('mask_dais', 104, 91, r=1.2, place='ribbon_mask_court'),
        obj('mosaic_disc', *CENTER, v=0),
    ]
    # Color gardens cluster by court; ornamental pieces keep the spokes open.
    for kind, count, radius in [
        ('oak_tree', 14, 1.25), ('birch_tree', 14, 1.0),
        ('apple_tree', 14, 1.0),
        ('fan_topiary', 58, .85), ('ribbon_pole', 46, .35),
        ('pinwheel', 46, .22), ('festival_bloom', 128, .10),
        ('confetti_lantern', 28, .30),
    ]:
        placed = 0
        for _ in range(100000):
            if placed == count:
                break
            x, y = rng.uniform(9, 127), rng.uniform(10, 124)
            if x < 49 and 45 < y < 96 or dist_path(x, y, paths) < (3.7 if radius>.5 else 2.7):
                continue
            if math.hypot(x-120, y-65)<13 or math.hypot(x-72,y-20)<10 or math.hypot(x-112,y-91)<11:
                continue
            if any(math.hypot(x-o['x'], y-o['y']) < radius+max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+.5 for o in objects):
                continue
            objects.append(obj(kind, x, y, radius, v=rng.randrange(4)))
            placed += 1
        assert placed == count, (kind, placed)
    # A few ordinary trees frame the grassy market without hiding the spokes.
    for kind, x, y in [('oak_tree', 12, 60), ('apple_tree', 12, 81),
                       ('birch_tree', 47, 58), ('oak_tree', 47, 85),
                       ('apple_tree', 27, 43), ('birch_tree', 30, 100)]:
        assert dist_path(x, y, paths) > 3.8
        assert all(math.hypot(x-o['x'], y-o['y']) > max(o['r'], o.get('width', 0)/2, o.get('depth', 0)/2) + 2 for o in objects)
        objects.append(obj(kind, x, y, 1.2))
    spawns = [dict(kind='paradegryphon', x=72, y=20),
              dict(kind='maskcolossus', x=112, y=91)]
    for kind, count, lo, hi in [
        ('ribbongecko',10,28,112), ('balloonbeetle',10,20,115),
        ('paintedmacaw',10,17,108), ('jesterling',10,33,111),
    ]:
        for _ in range(count):
            for _attempt in range(10000):
                x, y = rng.uniform(10,126), rng.uniform(lo,hi)
                if x<50 and 45<y<97 or math.hypot(x-ARRIVAL[0],y-ARRIVAL[1])<12:
                    continue
                if dist_path(x,y,paths)<3.1 or math.hypot(x-120,y-65)<13:
                    continue
                if any(math.hypot(x-s['x'],y-s['y'])<(13 if s['kind'] in ('paradegryphon','maskcolossus') else 6) for s in spawns):
                    continue
                if any(math.hypot(x-o['x'],y-o['y'])<max(o['r'],o.get('width',0)/2,o.get('depth',0)/2)+1.7 for o in objects):
                    continue
                spawns.append(dict(kind=kind,x=round(x,2),y=round(y,2)))
                break
            else:
                raise RuntimeError('cannot place '+kind)
    people, quests = people_and_quests()
    zone = dict(name=NAME,theme='ribbonwild',
                tagline='A vivid processional wheel of color courts, silk pavilions and painted lawns',
                size=136,levels=[70,75],spawn=dict(x=ARRIVAL[0],y=ARRIVAL[1]),
                paths=[[[x,y] for x,y in path] for path in paths],
                objects=objects,slimes=spawns,npcs=people,
                places=[dict(id='ribbon_pavilion',name='The Thousandfold Pavilion',x=113,y=65,r=4),
                        dict(id='ribbon_gryphon_court',name='The Northern Dance Floor',x=72,y=20,r=5),
                        dict(id='ribbon_mask_court',name='The Mask Court',x=111,y=91,r=5)],
                quests=quests,
                city=dict(name='Jubilee Crossroads',x0=9,x1=48,y0=45,y1=96,
                          plaza=dict(x=30,y=70),radius=7,entry=dict(x=12,y=70)),
                futureInstance=dict(name='The Thousandfold Pavilion',level=75,
                                    players=5,status='sealed',x=120,y=65,
                                    description='An immense striped silk canopy and gilded mask doors hold a sealed five-player instance.'),
                portals=[dict(id='ribbon_sun_gate',name='The Parade Arch',
                              x=RETURN[0],y=RETURN[1],r=1.2,to=20,
                              tx=SUN_ARRIVAL[0],ty=SUN_ARRIVAL[1],look='ribbonwild')])
    check(zone)
    return zone


def check(zone):
    seen,_=fen.flood(zone,ARRIVAL)
    for target in [*zone['npcs'],*zone['slimes'],*zone['portals'],
                   dict(x=113,y=65),dict(x=72,y=28),dict(x=111,y=84)]:
        assert seen[int(target['y']/.5),int(target['x']/.5)],f'unreachable: {target}'
    assert all(math.hypot(s['x']-ARRIVAL[0],s['y']-ARRIVAL[1])>=8 for s in zone['slimes'])
    for q in zone['quests']:
        assert len('quest:accept:'+q['id'])<=32,q['id']
    assert len(zone['slimes'])==42 and len(zone['quests'])==9


def open_sunward_gate(sunward):
    # The old oak is west of the new ridge track. Keep its sealed entrance
    # intact while opening a separate eastern route through decorative trees.
    line=[(105,25),(113,27),(121,24)]
    sunward['objects']=[o for o in sunward['objects']
                        if o['kind']=='elder_hollow_gate' or
                        dist_path(o['x'],o['y'],[line])>max(o.get('r',0),o.get('width',0)/2,o.get('depth',0)/2)+3.2]
    road=[[105,25],[113,27],[121,24]]
    sunward['paths']=[p for p in sunward['paths'] if p!=road]
    sunward['paths'].append(road)
    sunward['portals']=[p for p in sunward['portals'] if p['id']!='sun_ribbon_gate']
    sunward['portals'].append(dict(id='sun_ribbon_gate',name='The Parade Arch',
                                  x=SUN_GATE[0],y=SUN_GATE[1],r=1.2,
                                  to=ZONE,tx=ARRIVAL[0],ty=ARRIVAL[1],look='ribbonwild'))
    seen,_=fen.flood(sunward,(sunward['spawn']['x'],sunward['spawn']['y']))
    for x,y in [SUN_GATE,SUN_ARRIVAL]:
        assert seen[int(y/.5),int(x/.5)],(x,y)
    assert all(math.hypot(s['x']-SUN_ARRIVAL[0],s['y']-SUN_ARRIVAL[1])>=8 for s in sunward['slimes'])


def main():
    world=json.loads(MAP.read_text())
    assert world['zones'][19]['name']=='Sunward Vale'
    later=world['zones'][ZONE:]
    world['zones']=world['zones'][:ZONE-1]
    open_sunward_gate(world['zones'][19])
    world['zones'].append(build())
    if later and later[0].get('name') == 'The Tanglecrown':
        from generate_tanglecrown import open_ribbon_gate
        open_ribbon_gate(world['zones'][20])
    world['zones'].extend(later)
    spark_travel.ensure(world)
    MAP.write_text(json.dumps(world,indent=2)+'\n')
    items=json.loads(ITEMS.read_text())
    for key,name,sell in [
        ('ribbon_tail','Ribbon Gecko Tail',900),
        ('balloon_silk','Balloon Beetle Silk',960),
        ('macaw_plume','Painted Macaw Plume',1040),
        ('jester_bell','Jesterling Bell',1120),
        ('gryphon_feather','Parade Gryphon Feather',3900),
        ('masquerade_mask','Masquerade Mask',5100),
    ]:
        if not any(i['id']==key for i in items):
            items.append(dict(id=key,name=name,kind='material',rarity='common',sell=sell))
    ITEMS.write_text(json.dumps(items,indent=2)+'\n')
    print(f'{NAME}: {len(world["zones"][20]["objects"])} objects, 42 enemies, 9 quests')


if __name__=='__main__':
    main()
