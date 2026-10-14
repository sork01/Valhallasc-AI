"""Check every completed level-25–50 and Cathedral gear source and client mapping."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text())


state = read('docs/gear-redesign-state.txt')
art = read('world/gear-art.txt')
items = {item['id']: item for item in read('world/items.txt')}
icons = read('client/assets/items.txt')['at']
metadata = {}
names = {'warrior': 'warrior_layered', 'assassin': 'assassin', 'mage': 'mage',
         'priest': 'priest', 'hunter': 'hunter'}

assert len(state['tasks']) == 252
assert {task['id'] for task in state['tasks']} <= set(art)
for task in state['tasks']:
    job = task['id']
    record = art[job]
    assert task['done'] and record['kind'] == task['kind'], job
    assert record['icon']['id'] and all(record['classes'][cls] for cls in record['classes']), job
    assert all((ROOT / file).is_file() for file in record['files']), job
    assert any(file.endswith('.png') and 'gear_icon_' in file for file in record['files']), job
    item = items[task['item']]
    assert item['kind'] == task['kind'] and item['art'] == record['variant'], job
    assert item['id'] in icons, job
    for cls in record['classes']:
        assert all(record['classes'][cls][clip] for clip in ('idle', 'walk', 'attack', 'hurt', 'die')), job
        for suffix in ('', '_f'):
            name = f'client/assets/{names[cls]}{suffix}_sprites.txt'
            if name not in metadata:
                metadata[name] = read(name)
            slot = 'head' if task['kind'] == 'headgear' else task['kind']
            assert f'{slot}_{record["variant"]}' in metadata[name]['parts'], (job, cls, suffix)

print('252 gear redesign pieces have source art, both-body atlas parts, catalog and icons')

high = read('docs/high-gear-state.txt')['tasks']
assert len(high) == 224
assert all(task['done'] for task in high[:196])
completed_high = [task for task in high if task['done']]
for task in completed_high:
    job = task['id']
    record = art[job]
    assert record['kind'] == task['kind'] and record['icon']['id'], job
    assert all((ROOT / file).is_file() for file in record['files']), job
    assert any('gear_icon_' in file for file in record['files']), job
    item = items[task['item']]
    assert item['art'] == record['variant'] and item['kind'] == task['kind'], job
    assert item['id'] in icons, job
    for cls in record['classes']:
        assert all(record['classes'][cls][clip] for clip in ('idle', 'walk', 'attack', 'hurt', 'die')), job
        for suffix in ('', '_f'):
            name = f'client/assets/{names[cls]}{suffix}_sprites.txt'
            if name not in metadata:
                metadata[name] = read(name)
            slot = 'head' if task['kind'] == 'headgear' else task['kind']
            assert f'{slot}_{record["variant"]}' in metadata[name]['parts'], (job, cls, suffix)

print(f'{len(completed_high)} high-level pieces have source art, both-body atlas parts, catalog and icons')

dungeon = read('docs/dungeon-gear-state.txt')['tasks']
assert len(dungeon) == 55
for task in dungeon:
    if not task['done']:
        continue
    job = task['id']
    record = art[job]
    assert record['kind'] == task['kind'] and record['icon']['id'], job
    assert all((ROOT / file).is_file() for file in record['files']), job
    item = items[task['item']]
    assert item['source'] == {'vault': 'undervault', 'moonwell': 'moonwell'}[task['group']], job
    assert item['art'] == record['variant'] and item['kind'] == task['kind'], job
    assert item['id'] in icons, job
    for cls in record['classes']:
        assert all(record['classes'][cls][clip] for clip in ('idle', 'walk', 'attack', 'hurt', 'die')), job
        for suffix in ('', '_f'):
            name = f'client/assets/{names[cls]}{suffix}_sprites.txt'
            if name not in metadata:
                metadata[name] = read(name)
            slot = 'head' if task['kind'] == 'headgear' else task['kind']
            assert f'{slot}_{record["variant"]}' in metadata[name]['parts'], (job, cls, suffix)

print(f'{sum(task["done"] for task in dungeon)} dungeon pieces have source art, both-body atlas parts, catalog and icons')

for task in [t for t in high if t['group'] == 'L95'] + dungeon:
    record = art[task['id']]
    assert task['done'] and record.get('female'), task['id']
    for cls in record['classes']:
        assert all(record['female'][cls][clip] and all(chunk['id'] for chunk in record['female'][cls][clip])
                   for clip in ('idle', 'walk', 'attack', 'hurt', 'die')), (task['id'], cls)
        name = f'client/assets/{names[cls]}_f_sprites.txt'
        meta = metadata.get(name) or read(name)
        slot = 'head' if task['kind'] == 'headgear' else task['kind']
        assert meta['gearSprites'][f'{slot}_{record["variant"]}'] == record['female'][cls], (task['id'], cls)

print('83 new sets have editable PixelFlow records for both bodies and every animation')
