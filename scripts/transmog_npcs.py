#!/usr/bin/env python3
"""Add four reachable Transmog Masters after shaping; preserve every existing world entry."""
import argparse
import copy
import json
import math
from pathlib import Path
from compact_atlas import connected
from spirit_guides import clear

ROOT = Path(__file__).resolve().parents[1]
MASTERS = {
    4: ('city_transmog', 'city_smith'),
    9: ('nacre_transmog', 'nacre_smith'),
    17: ('asterion_transmog', 'asterion_smith'),
    24: ('hw_transmog', 'hw_smith'),
}
DIALOGUE = 'Every piece you have owned leaves a memory. Choose a new appearance for your equipment slots. Changing or hiding a look costs a little money; returning to your real gear is free.'


def install(world, art):
    areas = [world, *world['zones']]
    for zone, (key, template) in MASTERS.items():
        area = areas[zone]
        area['npcs'] = [n for n in area['npcs'] if n['id'] != key]
        source = next(n for n in area['npcs'] if n['id'] == template)
        reachable = connected(area)
        candidates = [(source['x'] + r * math.cos(k * math.tau / 16),
                       source['y'] + r * math.sin(k * math.tau / 16))
                      for r in (4, 5, 6, 7, 8) for k in range(16)]
        def safe(p):
            x, y = p
            return (int(y) * area['size'] + int(x) in reachable and clear(area, x, y, 1)
                    and all(math.hypot(x - n['x'], y - n['y']) >= 2.5 for n in area['npcs'])
                    and all(math.hypot(x - n['x'], y - n['y']) >= n.get('r', 1) + 3 for n in area['portals']))
        pos = next((p for p in candidates if safe(p)), None)
        if pos is None:
            raise ValueError(f'No reachable Transmog Master position in {area["name"]}')
        npc = dict(id=key, name='Transmog Master', role='Equipment appearances', x=round(pos[0], 3), y=round(pos[1], 3),
                   color=source['color'], look=copy.deepcopy(source['look']), dialogue=DIALOGUE,
                   offers=[dict(id='transmogrify', label='Transmogrify', cost=0)], buys=False)
        area['npcs'].append(npc)
        art['npcs'][key] = copy.deepcopy(art['npcs'][template])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path, art_path = ROOT/'world/map.txt', ROOT/'client/assets/npc.txt'
    world, art = json.loads(path.read_text()), json.loads(art_path.read_text())
    install(world, art)
    for p, value in [(path, world), (art_path, art)]:
        text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
        if args.check:
            if p.read_text() != text: raise SystemExit(f'Transmog Master overlay is stale: {p.name}')
        else:
            p.write_text(text)
    print('Transmog Masters in Skaldholm, Nacrehold, Asterion and Veyrroot Heartwood')


if __name__ == '__main__':
    main()
