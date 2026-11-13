#!/usr/bin/env python3
"""Assign the approved missing NPC art, preserving gameplay and every old identity."""
import hashlib
import json
import shutil
from pathlib import Path
import make_npcp_sprites as maker
import npcp_named as named

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'


def people():
    world = json.loads((ROOT / 'world/map.txt').read_text())
    return [n for z in [world] + world['zones'] for n in z.get('npcs', [])
            if n.get('art') not in ('mailbox', 'stone', 'scenery', 'spirit_guide')
            and 'meeting stone' not in n['name'].lower()]


def assign():
    old_path, fresh_path = ASSETS/'npc.txt', ASSETS/'npcp.txt'
    old, fresh = json.loads(old_path.read_text()), json.loads(fresh_path.read_text())
    original = json.loads(json.dumps(old))
    plan = json.loads((ROOT/'docs/npc-named-plan.txt').read_text())
    # These four reuse looks are aliases of corrected, editable native designs.
    for key, source in named.REUSE_ALIASES.items():
        fresh['sprites'][key] = fresh['sprites'][source]
        fresh['designs'][key] = maker.design_meta(key, maker.palettes_for([key])[key])
        fresh['tops'][key], fresh['bounds'][key] = fresh['tops'][source], fresh['bounds'][source]
        shutil.copy2(ASSETS/f'npcp_{source}.png', ASSETS/f'npcp_{key}.png')
    for p in plan['people']:
        key = p['designKey'] if p['classification'] == 'named' else (
            'reuse_treefolk_' if p.get('requiredSpecies') == 'treefolk' else 'reuse_') + p['reuse']
        assert key in fresh['sprites'] and (ASSETS/f'npcp_{key}.png').is_file(), (p['id'], key)
        identity = dict(p['identity'])
        species = fresh['designs'][key].get('species')
        if species:
            identity['species'] = species
        if species == 'treefolk' and p['classification'] == 'generic':
            # The species change is visual: bark/leaf ramps replace human skin/hair.
            variant = int(hashlib.sha256(p['id'].encode()).hexdigest()[:8], 16) % 4
            identity['skin'] = ['#ad8057', '#926a49', '#b58e65', '#8f7357'][variant]
            identity['hair'] = ['#507a43', '#658a52', '#397c60', '#7a934d'][variant]
        entry = dict(art=key, identity=identity, color=p['color'])
        if p['id'] in old['npcs']:
            assert old['npcs'][p['id']] == entry, ('Existing assignment differs', p['id'])
        old['npcs'][p['id']] = entry
    assert set(old['npcs']) == {n['id'] for n in people()}
    for key, value in original.items():
        if key != 'npcs':
            assert old[key] == value, key
    for key, value in original['npcs'].items():
        assert old['npcs'][key] == value, key
    fresh_path.write_text(json.dumps(fresh, ensure_ascii=False, indent=2)+'\n')
    old_path.write_text(json.dumps(old, ensure_ascii=False, indent=2)+'\n')
    print(f'{len(old["npcs"])} actual people assigned; 148 named + 121 role reuses; existing identities retained')


if __name__ == '__main__':
    assign()
