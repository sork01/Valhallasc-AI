#!/usr/bin/env python3
"""Install hire and summon services after the final zone shapes."""
import json
import math
from pathlib import Path

from mercenary_offers import offers

MAP = Path(__file__).resolve().parents[1] / 'world/map.txt'
SUMMON = dict(id='summon_party', label='Summon party members', cost=0)
STONE_DIALOGUE = 'Use this stone to invite your party members to join you here.'
GATE = (143, 169.5)
RETURN = (144.5, 175)
GUIDES = {'barrow_guide': (140.5, 174.5), 'barrow_scribe': (149, 176.5)}
SPUR = [[140, 184], [144.5, 179.5], list(RETURN), list(GATE)]


def collision(o, point, margin=.4):
    x, y = point
    if o.get('width') and o.get('depth'):
        return abs(x-o['x']) < o['width']/2+margin and abs(y-o['y']) < o['depth']/2+margin
    return math.dist(point, (o['x'], o['y'])) < o.get('r', 0)+margin


def road_distance(point, road):
    def segment(a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = dx*dx + dy*dy
        t = min(1, max(0, ((point[0]-a[0])*dx + (point[1]-a[1])*dy)/length)) if length else 0
        return math.dist(point, (a[0]+dx*t, a[1]+dy*t))
    return min(segment(a, b) for a, b in zip(road, road[1:]))


def relocate_barrow(zones):
    zone = zones[6]
    door = next(p for p in zone['portals'] if p['id'] == 'wyrd_nornroot')
    door['x'], door['y'] = GATE
    for p in zones[41]['portals']:
        if p['to'] == 6:
            p['tx'], p['ty'] = RETURN
    for npc in zone['npcs']:
        if npc['id'] in GUIDES:
            npc['x'], npc['y'] = GUIDES[npc['id']]
    roads = [road for road in zone['paths'] if road != SPUR]
    assert min(road_distance(GATE, road) for road in roads) >= 8
    seats = [GATE, RETURN, *GUIDES.values()]
    zone['objects'] = [o for o in zone['objects'] if not (
        o['kind'] in ('pine', 'rock', 'bush')
        and (road_distance((o['x'], o['y']), SPUR) < o.get('r', 0)+.9
             or any(collision(o, xy, 1.2) for xy in seats))
    )]
    for spawn in zone['slimes']:
        if any(math.dist((spawn['x'], spawn['y']), xy) < 7 for xy in seats):
            assert spawn['kind'] == 'weaver' and not spawn.get('ambush'), spawn
            alternate = (132.5, 190.5)
            assert not any(collision(o, alternate, .7) for o in zone['objects'])
            assert all(math.dist(alternate, (s['x'], s['y'])) >= 3 for s in zone['slimes'] if s is not spawn)
            spawn['x'], spawn['y'] = alternate
    zone['paths'] = roads + [SPUR]


def stone_position(zone):
    sx, sy = zone['spawn']['x'], zone['spawn']['y']
    for dx, dy in ((-3, 0), (3, 0), (-3, 2), (3, 2), (0, -3), (-4, -2), (4, -2), (0, 6)):
        x, y = sx+dx, sy+dy
        if not (2 < x < zone['size']-2 and 2 < y < zone['size']-2):
            continue
        if any(collision(o, (sx+dx*t/20, sy+dy*t/20), .8)
               for t in range(21) for o in zone['objects']):
            continue
        if any(math.dist((x,y), (p['x'], p['y'])) < p['r']+2.8 for p in zone['portals']):
            continue
        if any(math.dist((x,y), (n['x'], n['y'])) < 2.6 for n in zone['npcs']):
            continue
        if any(math.dist((x,y), (s['x'], s['y'])) < 9 for s in zone['slimes']):
            continue
        return x, y
    raise ValueError(f"No safe Meeting Stone position in {zone['name']}")


def install(world):
    zones = [world, *world['zones']]
    if len(zones) > 41 and zones[6].get('shape'):
        relocate_barrow(zones)
    for index, zone in enumerate(zones):
        instance = zone.get('copies', 0) > 0 and bool(zone.get('players'))
        if instance:
            zone['npcs'] = [n for n in zone['npcs'] if n['id'] != f'dungeon_stone_{index}']
            zone['objects'] = [o for o in zone['objects'] if o.get('label') != 'Dungeon Meeting Stone']
        for npc in zone.get('npcs', []):
            meeting = 'Meeting Stone' in npc['name']
            old = npc.get('offers', [])
            if instance or meeting or any(o.get('merc') and (o.get('open') or o.get('raid')) for o in old):
                npc['offers'] = [o for o in old if not o.get('merc')]
            if meeting:
                npc['offers'] = [o for o in npc['offers'] if o['id'] != SUMMON['id']] + [dict(SUMMON)]
                npc['dialogue'] = STONE_DIALOGUE
            if npc['id'] == 'barrow_guide':
                npc['dialogue'] = npc['dialogue'].replace(' I can hire fighters to help you.', '')
            if npc['id'] == 'span_guide':
                npc['dialogue'] = npc['dialogue'].replace('Take a party, or hire fighters from me, and break his watch.',
                                                           'The Repair Smith inside hires fighters to help you break his watch.')
            if npc['id'] == 'cf_quartermaster':
                npc['dialogue'] = ('Hire your missing fighters from the Repair Smith. Ten fighters must pass the inner gate together. '
                                   'If you fall, your fighters wake with you at the last rally mark.')
        if not instance:
            continue
        smith = next(n for n in zone['npcs'] if n['id'] == f'dungeon_repair_{index}')
        smith['dialogue'] = 'I can hire fighters for this run and repair your gear. Dungeon repairs cost four times the town price.'
        hire = offers(open_=not zone.get('raid'))
        if zone.get('raid'):
            for offer in hire[:-1]:
                offer['raid'] = True
        smith['offers'].extend(hire)
        x, y = stone_position(zone)
        zone['npcs'].append(dict(id=f'dungeon_stone_{index}', name='The Meeting Stone', role='Party summons',
                                 dialogue=STONE_DIALOGUE, x=x, y=y, color='#8e87ad', art='stone', offers=[dict(SUMMON)]))
        zone['objects'].append(dict(kind='meetingstone', x=x, y=y, r=.55, v=0, label='Dungeon Meeting Stone'))


if __name__ == '__main__':
    world = json.loads(MAP.read_text())
    install(world)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
