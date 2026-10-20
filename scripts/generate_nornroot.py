#!/usr/bin/env python3
"""Append level-25 Nornroot Barrow; reapply its Wyrdwood entrance after a parent rebuild.

python3 scripts/generate_nornroot.py [--check]
Then gear_levels.py, sync-world.cjs, build_swedish.py and a private Rust build.
Existing public zone IDs (including Arena 40) stay fixed. See docs/nornroot.md for saved-copy migration.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import generate_gloamfen as fen
import generate_undervault as vault
from mercenary_offers import offers
from nornroot_content import ENEMIES
from skaldholm_content import look

ROOT = Path(__file__).resolve().parents[1]
NAME, THEME, ZONE, PARENT, SIZE = 'Nornroot Barrow', 'nornroot', 41, 6, 112
GATE, LANDING, ARRIVAL = (84, 66), (84, 71), (56, 99)
ROOMS = [[46, 90, 68, 108], [40, 66, 72, 86], [10, 40, 36, 66],
         [76, 40, 102, 66], [44, 38, 68, 58], [39, 5, 73, 31]]
CORRIDORS = [[53, 82, 60, 94], [20, 73, 56, 80], [20, 60, 27, 78],
             [56, 73, 93, 80], [86, 60, 93, 78], [20, 44, 50, 51],
             [62, 44, 93, 51], [53, 27, 60, 42]]


def obj(kind, x, y, **kw):
    return dict(kind=kind, x=x, y=y, r=0, v=0, **kw)


def build():
    floor = np.zeros((SIZE, SIZE), bool)
    for x0, y0, x1, y1 in ROOMS + CORRIDORS:
        floor[y0:y1, x0:x1] = True
    vault.SIZE = SIZE
    walls, _ = vault.wall_pieces(floor)
    objects = [obj('norn_wall', round(x, 2), round(y, 2), width=round(w, 2), depth=round(d, 2))
               for x, y, w, d in walls]
    # Merge the rock outside playable floor into collision rectangles; no dash can escape the tomb.
    used = floor.copy()
    for y in range(SIZE):
        for x in range(SIZE):
            if used[y, x]:
                continue
            x1 = x
            while x1 < min(x+8, SIZE) and not used[y, x1]:
                x1 += 1
            y1 = y+1
            while y1 < min(y+8, SIZE) and not used[y1, x:x1].any():
                y1 += 1
            used[y:y1, x:x1] = True
            objects.append(obj('void', (x+x1)/2, (y+y1)/2, width=x1-x, depth=y1-y))
    for i, (x0, y0, x1, y1) in enumerate(ROOMS):
        for x in (x0+2, x1-2):
            objects.append(obj('norn_lamp', x, y0+3))
        objects.append(obj('norn_spindle', (x0+x1)/2, y0+2))
    objects += [obj('norn_loom', 56, 8), obj('norn_sarcophagus', 14, 44), obj('norn_sarcophagus', 98, 44)]
    spawns = []
    for cx, cy in [(56, 76), (29, 76), (83, 76), (56, 47)]:
        for kind, dx, dy in [('barrow_hound', -3, 1), ('barrow_scarab', 3, 1), ('barrow_spinner', 0, -2)]:
            spawns.append(dict(kind=kind, x=cx+dx, y=cy+dy))
    spawns += [dict(kind='barrow_doorward', x=23, y=53),
               dict(kind='barrow_threadkeeper', x=89, y=53),
               dict(kind='barrow_fatebound', x=56, y=18)]
    return dict(name=NAME, theme=THEME, tagline='Three threads, one unwritten fate.', size=SIZE,
                levels=[25, 25], min_level=25, players=5, copies=4, interior=True,
                sealedTemplate=False, final_boss='barrow_fatebound', spawn=dict(x=56, y=99),
                objects=objects, slimes=spawns, npcs=[dict(id='barrow_witness',name='Ida, the Last Witness',
                    role='Witness of the old court',x=62,y=100,color='#a5c4c6',offers=[],
                    dialogue='I remember the king before the threads took him. Arn guards the west court. Vessa keeps the east. Read the sign before you face the king.',
                    look=look('#d7c8bc','#c4b9d4','long','hood',hat_color='#6e617f'))], quests=[], city=None,
                rooms=ROOMS+CORRIDORS, paths=[[[56, 99], [56, 76], [23, 76], [23, 47],
                                            [56, 47], [89, 47], [89, 76]], [[56, 47], [56, 18]]],
                places=[dict(id='barrow_threshold', name='The Spindle Threshold', x=56, y=99, r=4)],
                portals=[dict(id='barrow_return', name='Wyrdwood', x=49, y=99, r=1.2,
                              to=PARENT, tx=LANDING[0], ty=LANDING[1], look=THEME),
                         dict(id='barrow_clear', name='The Unbound Way', x=56, y=10, r=1.2,
                              to=PARENT, tx=LANDING[0], ty=LANDING[1], look=THEME, after_clear=True)])


def install_parent(world):
    """Idempotent; called by both this generator and generate_wyrdwood.py."""
    if not any(z['name'] == NAME for z in world['zones']):
        return
    z = world['zones'][PARENT-1]
    assert z['name'] == 'Wyrdwood'
    # Open a broad approach off the existing Skuldwatch/Norn Stones road.
    line = [[96, 68], [84, 68], list(GATE)]
    z['paths'] = [p for p in z['paths'] if p != line] + [line]
    z['objects'] = [o for o in z['objects'] if not (
        fen.dist_to_trail(line, o['x'], o['y']) < 2.8 + max(o.get('r', 0), o.get('width', 0)/2, o.get('depth', 0)/2)
        or any(math.hypot(o['x']-x, o['y']-y) < 2.5+o.get('r', 0) for x,y in [LANDING, (88,68), (92,68)]))]
    # Preserve the parent's encounter counts and order: move displaced ordinary foes to nearby free ground.
    keepouts=[GATE,LANDING,(88,68),(92,68)]
    blocked=fen.obstacle_grid(z,.5,margin=.8)
    for s in z['slimes']:
        if all(math.hypot(s['x']-x,s['y']-y)>12 for x,y in keepouts):
            continue
        assert s['kind'] not in ('oakhorn','hrungnir')
        candidates=sorted((math.hypot(x-s['x'],y-s['y']),x,y)
                          for x in range(60,120) for y in range(48,70))
        for _,x,y in candidates:
            if blocked[int(y/.5),int(x/.5)]:
                continue
            if any(math.hypot(x-kx,y-ky)<=12 for kx,ky in keepouts):
                continue
            if any(q is not s and math.hypot(x-q['x'],y-q['y'])<6 for q in z['slimes']):
                continue
            s.update(x=x,y=y)
            break
        else:
            raise AssertionError('no free replacement spawn')
    z['portals'] = [p for p in z['portals'] if p['id'] != 'wyrd_nornroot'] + [
        dict(id='wyrd_nornroot', name=NAME, x=GATE[0], y=GATE[1], r=1.3,
             to=ZONE, tx=ARRIVAL[0], ty=ARRIVAL[1], look=THEME)]
    z['npcs'] = [n for n in z['npcs'] if not n['id'].startswith('barrow_')] + [
        dict(id='barrow_guide', name='Runa Threadreader', role='Barrow guide', x=88, y=68, color='#b599d6',
             dialogue='The Norn Stones have opened. Arn guards the amber hall. Free him, and the road to the loom will be yours. I can hire fighters to help you.',
             offers=offers(open_=True), look=look('#edc5a1', '#c4b49a', 'braid', 'hood', hat_color='#71618d')),
        dict(id='barrow_scribe', name='Egil Spindlekeeper', role='Keeper of the old threads', x=92, y=68, color='#bfa368',
             dialogue='Vessa has tied the dead to their old promises. Break her spell. Beyond her waits a king whose story was never written.',
             offers=[], look=look('#e0b48e', '#806653', 'short', None, None, '#806653'))]
    xp = json.loads((ROOT/'world/levels.txt').read_text())[24]//10
    quests = [
        dict(id='barrow_entry', title='Beneath the Norn Stones', npc='barrow_guide', level=25,
             description='Step into Nornroot Barrow and speak to the Last Witness. Return to Runa when you know the way.',
             objectives=[dict(kind='talk', target='barrow_witness', label='Speak to the Last Witness', count=1)],
             rewardXp=xp, rewardGold=350),
        dict(id='barrow_amber', title='The Amber Promise', npc='barrow_guide', level=25, group=True, recommendedPlayers=5,
             description='Defeat Arn, the Amber Doorward, with your party. Set his old promise free.',
             objectives=[dict(kind='kill', target='barrow_doorward', label='Free Arn, the Amber Doorward', count=1)],
             rewardXp=xp, rewardGold=1100, rewardItem='pants_wayfarer_l25_norn', rewardCount=1),
        dict(id='barrow_threads', title='A Thread Left Unbound', npc='barrow_scribe', level=25, group=True, recommendedPlayers=5,
             description='Defeat Vessa, Keeper of Threads. Her stolen threads bind the king beyond her hall. Take back the first loose end.',
             objectives=[dict(kind='kill', target='barrow_threadkeeper', label='Defeat Vessa, Keeper of Threads', count=1)],
             rewardXp=xp, rewardGold=1100, rewardItem='accessory_amber_l25_norn', rewardCount=1)]
    for q in quests:
        q.update(repeatable=False, requires=None)
    z['quests'] = [q for q in z['quests'] if not q['id'].startswith('barrow_')] + quests


def check(world):
    for index, start in [(ZONE, ARRIVAL), (PARENT, (88, 89))]:
        zone = world['zones'][index-1]
        seen, _ = fen.flood(zone, start)
        targets = zone['portals'] + zone['npcs'] + [s for s in zone['slimes'] if not s.get('ambush')]
        for p in targets:
            assert seen[int(p['y']/.5), int(p['x']/.5)], (index, p.get('id',p.get('kind')), p['x'],p['y'])
    for source in [world['zones'][PARENT-1],world['zones'][ZONE-1]]:
        for p in source['portals']:
            if p['id'] not in ('wyrd_nornroot','barrow_return','barrow_clear'):
                continue
            dst = world['zones'][p['to']-1]
            assert all(math.hypot(s['x']-p['tx'],s['y']-p['ty']) > 8 for s in dst['slimes'])
            assert all(math.hypot(q['x']-p['tx'],q['y']-p['ty']) > q['r']+1 for q in dst['portals'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT/'world/map.txt'
    world = json.loads(path.read_text())
    if not args.check:
        old = next((i for i,z in enumerate(world['zones'],1) if z['name']==NAME), None)
        assert old in (None, ZONE)
        if old is None:
            assert len(world['zones']) == ZONE-1
            world['zones'].append(build())
        else:
            world['zones'][ZONE-1] = build()
        install_parent(world)
    check(world)
    if not args.check:
        path.write_text(json.dumps(world,indent=2,ensure_ascii=False)+'\n')
        (ROOT/'world/nornroot.txt').write_text(json.dumps(ENEMIES,indent=2,ensure_ascii=False)+'\n')
        items_path=ROOT/'world/items.txt'
        items=json.loads(items_path.read_text())
        have={i['id'] for i in items}
        for e in ENEMIES:
            if e['material'] not in have:
                items.append(dict(id=e['material'],name=e['name']+' Relic',kind='material',rarity='common',sell=400 if e['boss'] else 80))
        items_path.write_text(json.dumps(items,indent=2,ensure_ascii=False)+'\n')
    print('Nornroot Barrow: zone 41, Wyrdwood entrance; arrival, portals, NPCs and every spawn reachable')


if __name__=='__main__':
    main()
