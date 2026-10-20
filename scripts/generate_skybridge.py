#!/usr/bin/env python3
"""Append level-30 The Shattered Span; reapply its Bifrost Reach entrance after a parent rebuild.

python3 scripts/generate_skybridge.py [--check]
Then gear_levels.py, sync-world.cjs, build_swedish.py and a private Rust build.
Existing public zone IDs (including Arena 40 and Nornroot Barrow 41) stay fixed.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import generate_gloamfen as fen
import generate_undervault as vault
from mercenary_offers import offers
from skybridge_content import ENEMIES
from skaldholm_content import look

ROOT = Path(__file__).resolve().parents[1]
NAME, THEME, ZONE, PARENT, SIZE = 'The Shattered Span', 'skybridge', 42, 7, 112
GATE, LANDING, ARRIVAL = (58, 128), (58, 133), (56, 99)
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
    objects = [obj('span_wall', round(x, 2), round(y, 2), width=round(w, 2), depth=round(d, 2))
               for x, y, w, d in walls]
    # Merge the sky-void outside playable floor into collision rectangles; no dash can escape the span.
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
    for x0, y0, x1, y1 in ROOMS:
        for x in (x0+2, x1-2):
            objects.append(obj('span_brazier', x, y0+3))
        objects.append(obj('span_prism', (x0+x1)/2, y0+2))
    objects += [obj('span_arch', 56, 8), obj('span_obelisk', 14, 44), obj('span_obelisk', 98, 44)]
    spawns = []
    for cx, cy in [(56, 76), (29, 76), (83, 76), (56, 47)]:
        for kind, dx, dy in [('span_lynx', -3, 1), ('span_sentinel', 3, 1), ('span_caster', 0, -2)]:
            spawns.append(dict(kind=kind, x=cx+dx, y=cy+dy))
    spawns += [dict(kind='span_warden', x=23, y=53),
               dict(kind='span_weaver', x=89, y=53),
               dict(kind='span_archon', x=56, y=18)]
    return dict(name=NAME, theme=THEME, tagline='Seven broken arches above the storm.', size=SIZE,
                levels=[30, 30], min_level=30, players=5, copies=4, interior=True,
                sealedTemplate=False, final_boss='span_archon', spawn=dict(x=56, y=99),
                objects=objects, slimes=spawns, npcs=[dict(id='span_witness', name='Torvald, the Last Watcher',
                    role='Watcher of the broken arch', x=62, y=100, color='#86d8f0', offers=[],
                    dialogue='The middle arch fell when the bridge broke, and Vaelor still guards the keystone as if Asgard were answering. Torstein holds the western toll-gate; Sunniva bends the eastern light. Read the keystone tablet before you challenge the Archon.',
                    look=look('#e0b48e', '#d6e4f0', 'short', 'helm', hat_color='#5888a8'))], quests=[], city=None,
                rooms=ROOMS+CORRIDORS, paths=[[[56, 99], [56, 76], [23, 76], [23, 47],
                                            [56, 47], [89, 47], [89, 76]], [[56, 47], [56, 18]]],
                places=[dict(id='span_threshold', name='The Rainbow Threshold', x=56, y=99, r=4)],
                portals=[dict(id='span_return', name='Bifrost Reach', x=49, y=99, r=1.2,
                              to=PARENT, tx=LANDING[0], ty=LANDING[1], look=THEME),
                         dict(id='span_clear', name='The Mended Arch', x=56, y=10, r=1.2,
                              to=PARENT, tx=LANDING[0], ty=LANDING[1], look=THEME, after_clear=True)])


def install_parent(world):
    """Idempotent; called by both this generator and generate_bifrost.py."""
    if not any(z['name'] == NAME for z in world['zones']):
        return
    z = world['zones'][PARENT-1]
    assert z['name'] == 'Bifrost Reach'
    line = [[74, 135], [62, 135], list(LANDING), list(GATE)]
    z['paths'] = [p for p in z['paths'] if p != line] + [line]
    scenery_kinds = {'skypine', 'prism', 'column', 'skyrock', 'cloudpuff'}
    z['objects'] = [o for o in z['objects'] if not (
        o['kind'] in scenery_kinds and (
            fen.dist_to_trail(line, o['x'], o['y']) < 2.8 + o.get('r', 0)
            or any(math.hypot(o['x']-x, o['y']-y) < 3.0 + o.get('r', 0)
                   for x, y in [GATE, LANDING, (62, 127), (62, 131)])))]
    z['portals'] = [p for p in z['portals'] if p['id'] != 'sky_shattered_span'] + [
        dict(id='sky_shattered_span', name=NAME, x=GATE[0], y=GATE[1], r=1.3,
             to=ZONE, tx=ARRIVAL[0], ty=ARRIVAL[1], look=THEME)]
    z['npcs'] = [n for n in z['npcs'] if not n['id'].startswith('span_')] + [
        dict(id='span_guide', name='Valkyrie Astrid Bridgeward', role='Keeper of the Shattered Span', x=62, y=127, color='#82d4f2',
             dialogue='Beneath the west cliff of the Perch hangs the Shattered Span, the oldest arch of the Bifrost. Torstein still demands the bridge-toll from anyone who crosses. Take a party, or hire fighters from me, and break his watch.',
             offers=offers(open_=True), look=look('#edc5a1', '#e8d088', 'braid', 'helm', hat_color='#5b88b8')),
        dict(id='span_chronicler', name='Soren Shardkeeper', role='Chronicler of the old bridge', x=62, y=131, color='#d49cf0',
             dialogue='Sunniva weaves the broken light of the eastern gallery into blinding spears, and beyond her stands Archon Vaelor himself. Reclaim the span and the bridge-ward relics are yours.',
             offers=[], look=look('#c89a72', '#b8c8e0', 'short', 'hood', hat_color='#725898'))]
    xp = json.loads((ROOT/'world/levels.txt').read_text())[29]//10
    quests = [
        dict(id='span_entry', title='Across the Shattered Span', npc='span_guide', level=30,
             description='Enter The Shattered Span from the west edge of Heimdall\'s Perch and speak to Torvald, the Last Watcher.',
             objectives=[dict(kind='talk', target='span_witness', label='Speak to Torvald, the Last Watcher', count=1)],
             rewardXp=xp, rewardGold=420),
        dict(id='span_toll', title="The Keeper's Toll", npc='span_guide', level=30, group=True, recommendedPlayers=5,
             description='Defeat Torstein, Keeper of the Toll, in the west gallery of The Shattered Span with your party.',
             objectives=[dict(kind='kill', target='span_warden', label='Defeat Torstein, Keeper of the Toll', count=1)],
             rewardXp=xp, rewardGold=1350, rewardItem='pants_wayfarer_l30_span', rewardCount=1),
        dict(id='span_spectrum', title='Threads of the Broken Rainbow', npc='span_chronicler', level=30, group=True, recommendedPlayers=5,
             description='Defeat Sunniva, the Spectrum Weaver, in the east gallery of The Shattered Span and claim her prismatic ring.',
             objectives=[dict(kind='kill', target='span_weaver', label='Defeat Sunniva, the Spectrum Weaver', count=1)],
             rewardXp=xp, rewardGold=1350, rewardItem='accessory_amber_l30_span', rewardCount=1)]
    for q in quests:
        q.update(repeatable=False, requires=None)
    z['quests'] = [q for q in z['quests'] if not q['id'].startswith('span_')] + quests


def check(world):
    for index, start in [(ZONE, ARRIVAL), (PARENT, (80, 146))]:
        zone = world['zones'][index-1]
        seen, _ = fen.flood(zone, start)
        targets = zone['portals'] + zone['npcs'] + [s for s in zone['slimes'] if not s.get('ambush')]
        for p in targets:
            assert seen[int(p['y']/.5), int(p['x']/.5)], (index, p.get('id', p.get('kind')), p['x'], p['y'])
    for source in [world['zones'][PARENT-1], world['zones'][ZONE-1]]:
        for p in source['portals']:
            if p['id'] not in ('sky_shattered_span', 'span_return', 'span_clear'):
                continue
            dst = world['zones'][p['to']-1]
            assert all(math.hypot(s['x']-p['tx'], s['y']-p['ty']) > 8 for s in dst['slimes'])
            assert all(math.hypot(q['x']-p['tx'], q['y']-p['ty']) > q['r']+1 for q in dst['portals'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT/'world/map.txt'
    world = json.loads(path.read_text())
    if not args.check:
        old = next((i for i, z in enumerate(world['zones'], 1) if z['name'] == NAME), None)
        assert old in (None, ZONE)
        if old is None:
            assert len(world['zones']) == ZONE-1
            world['zones'].append(build())
        else:
            world['zones'][ZONE-1] = build()
        install_parent(world)
    check(world)
    if not args.check:
        path.write_text(json.dumps(world, indent=2, ensure_ascii=False)+'\n')
        (ROOT/'world/skybridge.txt').write_text(json.dumps(ENEMIES, indent=2, ensure_ascii=False)+'\n')
        items_path = ROOT/'world/items.txt'
        items = json.loads(items_path.read_text())
        by_id = {i['id']: i for i in items}
        for e in ENEMIES:
            entry = dict(id=e['material'], name=e['name']+' Relic', kind='material', rarity='common', sell=520 if e['boss'] else 110)
            if e['material'] in by_id:
                by_id[e['material']].update(entry)
            else:
                items.append(entry)
        items_path.write_text(json.dumps(items, indent=2, ensure_ascii=False)+'\n')
    print('The Shattered Span: zone 42, Bifrost Reach entrance; arrival, portals, NPCs and every spawn reachable')


if __name__ == '__main__':
    main()
