#!/usr/bin/env python3
"""Four-city overlay, art assignments, reachability, idempotence and preservation of existing content."""
import copy
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import transmog_npcs as m
from enchanting_catalog import MASTERS as ENCHANTING_MASTERS

def main():
    world = json.loads((ROOT/'world/map.txt').read_text())
    art = json.loads((ROOT/'client/assets/npc.txt').read_text())
    before = copy.deepcopy(world)
    art_before = copy.deepcopy(art)
    all_ids = {key for key, _ in m.MASTERS.values()}
    baseline, base_art = copy.deepcopy(before), copy.deepcopy(art_before)
    for area in [baseline, *baseline['zones']]:
        area['npcs'] = [n for n in area['npcs'] if n['id'] not in all_ids]
    for key in all_ids: base_art['npcs'].pop(key)
    # Reinstall from a world without our NPCs. Other zones may evolve without changing this test's baseline.
    world, art = copy.deepcopy(baseline), copy.deepcopy(base_art)
    later_ids = {key for key, _, _ in ENCHANTING_MASTERS.values()}
    areas = [world, *world['zones']]
    later = [[npc for npc in area['npcs'] if npc['id'] in later_ids] for area in areas]
    for area in areas:
        area['npcs'] = [npc for npc in area['npcs'] if npc['id'] not in later_ids]
    m.install(world, art)
    for area, additions in zip(areas, later):
        area['npcs'].extend(additions)
    assert world == before, 'overlay already installed and idempotent'
    m.install(world, art)
    assert world == before, 'updating Transmog in place keeps later overlay ordering'
    assert art == art_before, 'art assignments already installed and idempotent'
    cleaned = copy.deepcopy(world)
    for area in [cleaned, *cleaned['zones']]:
        area['npcs'] = [n for n in area['npcs'] if n['id'] not in all_ids]
    if os.getenv('MUTATE') == 'preserve': cleaned['npcs'][0]['x'] += 1
    assert cleaned == baseline, 'existing world geometry, people, quests, waters and spawns stay unchanged'
    for key in all_ids: art['npcs'].pop(key)
    assert art == base_art, 'existing art assignments stay unchanged'
    for zone, (key, template) in m.MASTERS.items():
        area = [world, *world['zones']][zone]
        masters = [n for n in area['npcs'] if n['id'] == key]
        assert len(masters) == 1
        npc = masters[0]
        if os.getenv('MUTATE') == 'reach': npc['x'], npc['y'] = 0, 0
        assert m.clear(area, npc['x'], npc['y'], .9), f'{key}: open ground'
        assert int(npc['y'])*area['size']+int(npc['x']) in m.connected(area), f'{key}: reachable from spawn'
        assert npc['offers'] == [{'id': 'transmogrify', 'label': 'Transmogrify', 'cost': 0}]
        assert art_before['npcs'][key] == art_before['npcs'][template]
        print(f'{key}: reachable at ({npc["x"]}, {npc["y"]}) with existing local artwork')
    client = (ROOT/'client/world.js').read_text()
    assert json.loads(client.split('window.WORLD_MAP = ', 1)[1].rstrip(';\n')) == world, 'client world matches authoritative map'
    print('Transmog data: four reachable masters, idempotence, art and full world preservation passed')

if __name__ == '__main__': main()
