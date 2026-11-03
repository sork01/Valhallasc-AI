"""Focused world audit and byte stability; no gameplay or balance simulation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from compact_atlas import clear, connected


def load():
    return json.loads((ROOT / 'world/map.txt').read_text())


def strip(value):
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if not k.startswith('solstice')}
    if isinstance(value, list):
        rows = [strip(v) for v in value if not isinstance(v, dict) or not (
            v.get('season') == 'solstice' or v.get('kind') == 'birchcrown'
            or str(v.get('id', '')).startswith('solstice'))]
        # Owning generators remove/reappend their quests/hosts; IDs, not list order, identify them.
        if rows and all(isinstance(v, dict) and 'id' in v for v in rows):
            return sorted(rows, key=lambda v: str(v['id']))
        return rows
    return value


original = json.loads(subprocess.check_output(['git', 'show', '94a9fc6:world/map.txt'], cwd=ROOT))
world = load()
assert strip(original) == strip(world), 'Existing world content must remain semantically identical'
areas = [world, *world['zones']]
assert len(areas) == 47
counts = {}
for z, area in enumerate(areas):
    decor = area.get('solsticeDecor', [])
    assert bool(decor) == (z in [0, 4, 9, 17])
    if not decor:
        continue
    counts[area['name']] = len(decor)
    hub = area['city']
    assert len(decor) >= 20
    assert {'solsticePole','solsticeTable','solsticeBirch','solsticeFlowers','solsticeGarland','solsticeWreath'} <= {o['kind'] for o in decor}
    assert all(hub['x0'] < o['x'] < hub['x1'] and hub['y0'] < o['y'] < hub['y1'] for o in decor)
    poles = [o for o in decor if o['kind'] == 'solsticePole']
    assert len(poles) == 1
    pole = poles[0]
    assert clear(area, (pole['x'], pole['y']), (pole['x'], pole['y']), 2.5)
    assert int(pole['y']) * area['size'] + int(pole['x']) in connected(area)
    assert all(o is pole or o.get('z') or (o['x']-pole['x'])**2+(o['y']-pole['y'])**2 > 16 for o in decor)
    assert all(o.get('r', 0) == 0 for o in decor)
quests = [q for a in areas for q in a['quests'] if q.get('season') == 'solstice']
assert len(quests) == 5 and len({q['id'] for q in quests}) == 5
levels = json.loads((ROOT / 'world/levels.txt').read_text())
assert all(q['rewardXp'] == levels[q['level']-1]//10 for q in quests)
assert sum(q.get('seasonCadence') == 'daily' for q in quests) == 1
assert len(next(q for q in quests if q['id'] == 'solstice_hunt')['givers']) == 4
meta = json.loads((ROOT / 'client/assets/mounts_sprites.txt').read_text())
baseline = json.loads(subprocess.check_output(['git', 'show', '94a9fc6:client/assets/mounts_sprites.txt'], cwd=ROOT))
assert all(meta['mounts'][k] == v for k, v in baseline['mounts'].items())
assert len(meta['mounts']['sunwoven']['sprites']) == 16
assert len(set(meta['mounts']['sunwoven']['sprites'].values())) == 16
# Full sync must reproduce both the source and every generated client artifact byte for byte.
node = '/home/serveperry/.nvm/versions/node/v20.20.2/bin/node'
def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ['world', 'client'] for p in (ROOT / directory).glob('*') if p.is_file()}
subprocess.run([node, 'scripts/sync-world.cjs'], cwd=ROOT, check=True, capture_output=True)
first = hashes()
subprocess.run([node, 'scripts/sync-world.cjs'], cwd=ROOT, check=True, capture_output=True)
second = hashes()
assert first == second, [k for k in first if first[k] != second[k]]
assert strip(original) == strip(load())
result = dict(nonSolsticeDifferences=0, zones=len(areas), decorations=counts, byteStable=True,
              sourceAndGeneratedHashes=second)
(ROOT / 'test-results/solstice-data.json').write_text(json.dumps(result, indent=2)+'\n')
print('solstice-data: preserved world and old mount sources; four clear/reachable city poles; five quests; two full syncs byte-stable')
