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
SPAN_GATE = (236.5, 309.5)
SPAN_RETURN = (236.5, 314.5)
SPAN_GUIDES = {'span_guide': (231.5, 309.5), 'span_chronicler': (231.5, 312.5)}
SPAN_SPUR = [[232.5, 303.5], list(SPAN_GATE)]
SPAN_DESCRIPTION = 'Take the side trail near the Lightning Spire in the Shardfields. Enter The Shattered Span and speak to Torvald, the Last Watcher.'


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


def relocate_span(zones):
    zone = zones[7]
    door = next(p for p in zone['portals'] if p['id'] == 'sky_shattered_span')
    door['x'], door['y'] = SPAN_GATE
    for portal in zones[42]['portals']:
        if portal['to'] == 7:
            portal['tx'], portal['ty'] = SPAN_RETURN
    for npc in zone['npcs']:
        if npc['id'] in SPAN_GUIDES:
            npc['x'], npc['y'] = SPAN_GUIDES[npc['id']]
        if npc['id'] == 'span_guide':
            npc['dialogue'] = npc['dialogue'].replace(
                'Beneath the west cliff of the Perch',
                'Below the Shardfields near the Lightning Spire')
    next(q for q in zone['quests'] if q['id'] == 'span_entry')['description'] = SPAN_DESCRIPTION
    if SPAN_SPUR not in zone['paths']:
        zone['paths'].append(SPAN_SPUR)


def point_at(entry):
    return entry['x'], entry['y']


def clear_path(zone, start, end):
    x, y = start
    steps = max(1, math.ceil(math.dist(start, end) * 3))
    nearby = [obj for obj in zone['objects'] if collision(obj, start, math.dist(start, end) + .8)]
    for step in range(steps + 1):
        proportion = step / steps
        point = x + (end[0] - x) * proportion, y + (end[1] - y) * proportion
        if any(collision(obj, point, .8) for obj in nearby):
            return False
    return True


def stone_position(zone, door, returns):
    centre = point_at(door)
    arrivals = [(p['tx'], p['ty']) for p in returns]
    anchors = [(p['tx'], p['ty']) for p in returns
               if not p.get('after_clear') and math.dist(centre, (p['tx'], p['ty'])) <= 12]
    if not anchors:
        anchors = [centre]
    for radius in (6, 8, 10, 12):
        for i in range(24):
            angle = i * math.tau / 24
            x = round((centre[0] + radius * math.cos(angle)) * 2) / 2
            y = round((centre[1] + radius * math.sin(angle)) * 2) / 2
            point = x, y
            if not (2 < x < zone['size']-2 and 2 < y < zone['size']-2):
                continue
            if any(math.dist(point, point_at(p)) < max(p['r'], 2.8)+2.6 for p in zone['portals']):
                continue
            if any(math.dist(point, arrival) < 2.5 for arrival in arrivals):
                continue
            if any(math.dist(point, point_at(n)) < 2.8 for n in zone['npcs']):
                continue
            if any(math.dist(point, point_at(spawn)) < 8 for spawn in zone['slimes']):
                continue
            if not any(clear_path(zone, anchor, point) for anchor in anchors):
                continue
            if any(clear_path(zone, point, (x + dx, y + dy))
                   for dx, dy in ((1.8, 0), (-1.8, 0), (0, 1.8), (0, -1.8))):
                return point
    raise ValueError(f"No safe Meeting Stone position at {door['id']} in {zone['name']}")


def install(world):
    zones = [world, *world['zones']]
    instances = {index for index, zone in enumerate(zones) if zone.get('copies') and zone.get('players')}
    if len(zones) > 41 and zones[6].get('shape'):
        relocate_barrow(zones)
    if len(zones) > 42 and zones[7].get('shape'):
        relocate_span(zones)
    for index, zone in enumerate(zones):
        instance = index in instances
        zone['npcs'] = [n for n in zone.get('npcs', [])
                        if not n['id'].startswith('dungeon_stone_')
                        and not (instance and 'Meeting Stone' in n['name'])]
        zone['objects'] = [o for o in zone['objects']
                           if o.get('label') != 'Dungeon Meeting Stone'
                           and not (instance and o['kind'] == 'meetingstone')]
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

    for index, zone in enumerate(zones):
        if index in instances:
            continue
        for door in zone.get('portals', []):
            destination = door['to']
            if destination not in instances:
                continue
            if any('Meeting Stone' in npc['name'] and not npc['id'].startswith('dungeon_stone_')
                   and math.dist(point_at(door), point_at(npc)) <= 12 for npc in zone['npcs']):
                continue
            returns = [p for p in zones[destination]['portals'] if p['to'] == index]
            x, y = stone_position(zone, door, returns)
            stone_id = f'dungeon_stone_{destination}'
            if any(npc['id'] == stone_id for npc in zone['npcs']):
                stone_id = f'{stone_id}_{door["id"]}'
            zone['npcs'].append(dict(id=stone_id, name='The Meeting Stone',
                                     role='Party summons', dialogue=STONE_DIALOGUE, x=x, y=y,
                                     color='#8e87ad', art='stone', offers=[dict(SUMMON)]))
            zone['objects'].append(dict(kind='meetingstone', x=x, y=y, r=.55, v=0, label='Dungeon Meeting Stone'))


if __name__ == '__main__':
    world = json.loads(MAP.read_text())
    install(world)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
