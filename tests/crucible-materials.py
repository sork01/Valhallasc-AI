#!/usr/bin/env python3
"""Check material-specific deaths, grounding/hovering and Cathedral preservation in the exported Solar Crucible atlases.

MUTATE_KIND=solar_emberling replaces its death with idle in memory (or reads MUTATE_PNG) and must fail.
"""
import json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/crucible-slime-original-20261111')
sys.path.insert(0, str(ROOT / 'scripts'))
import kindframe
from astral_slime_redraw import PALETTE, AMBER, GOLD, BROWN, SLATE, PURPLE, CRIMSON, CORAL
from crucible_slime_redraw import KINDS, FLYING

meta = json.loads((ROOT / 'client/assets/cathedral.txt').read_text())
backup_meta = json.loads((BACKUP / 'client/assets/cathedral.txt').read_text())
checks = 0


def check(value, label):
    global checks
    assert value, label
    checks += 1
    print(f'{checks}: {label}')


def cell(kind, clip, n):
    mutate_kind = os.environ.get('MUTATE_KIND')
    mutate_png = os.environ.get('MUTATE_PNG')
    if mutate_kind == kind and mutate_png:
        atlas = Image.open(mutate_png).convert('RGBA')
        w, h = atlas.width // 8, atlas.height // 5
        row = meta['clips'][clip]['row']
        return np.array(atlas.crop((n * w, row * h, (n + 1) * w, (row + 1) * h)))
    if mutate_kind == kind and clip == 'die':
        clip, n = 'idle', 0
    w, h, _, _ = kindframe.frame_of(meta, kind)
    atlas = Image.open(ROOT / f'client/assets/cathedral_{kind}.png').convert('RGBA')
    row = meta['clips'][clip]['row']
    return np.array(atlas.crop((n * w, row * h, (n + 1) * w, (row + 1) * h)))


def material(im, ramp):
    colors = np.array([list(bytes.fromhex(PALETTE[i][1:])) for i in ramp])
    return (im[:, :, None, :3] == colors).all(-1).any(-1) & (im[:, :, 3] > 0)


def bounds(mask):
    ys, xs = np.nonzero(mask)
    assert len(ys), 'Material vanished'
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


# 1. Shared Cathedral manifest preservation (139 unrelated kinds + fallback frame + clip rates).
other_kinds = [k for k in backup_meta['kinds'] if k not in KINDS]
check(len(other_kinds) == 139, f'cathedral.txt preserves all 139 other kinds ({len(other_kinds)})')
check(
    all(meta['sprites'].get(k) == backup_meta['sprites'].get(k) and meta['tops'].get(k) == backup_meta['tops'].get(k) for k in other_kinds),
    'all 139 unrelated Cathedral sprite IDs and health-bar tops are untouched',
)
check(
    (tuple(meta['frame']), tuple(meta['anchor'])) == ((96, 96), (48, 90)),
    'fallback Cathedral 96x96 frame and (48, 90) anchor preserved',
)

# 2. Per-kind frame geometry, distinct animations, grounding/hovering, and material death checks.
for kind in KINDS:
    w, h, ax, ay = kindframe.frame_of(meta, kind)
    check((w, h, ax, ay) == (176, 172, 88, 164), f'{kind}: 176x172 frame and (88, 164) anchor')
    atk_hashes = {cell(kind, 'attack', n).tobytes() for n in range(8)}
    die_hashes = {cell(kind, 'die', n).tobytes() for n in range(8)}
    check(len(atk_hashes) == 8 and len(die_hashes) == 8, f'{kind}: 8 distinct attack and 8 distinct death frames')
    lows_die = [bounds(cell(kind, 'die', n)[:, :, 3] > 0)[3] for n in range(8)]
    if kind in FLYING:
        idle_low = bounds(cell(kind, 'idle', 0)[:, :, 3] > 0)[3]
        check(idle_low <= ay - 12, f'{kind}: hovers well above anchor row {ay} in idle (lowest={idle_low})')
        check(lows_die[-1] == ay and all(a <= b for a, b in zip(lows_die, lows_die[1:])),
              f'{kind}: flying death descends monotonically onto anchor row {ay}')
    else:
        for clip, count in (('idle', 6), ('walk', 8), ('attack', 8), ('hurt', 4), ('die', 8)):
            assert all(bounds(cell(kind, clip, n)[:, :, 3] > 0)[3] == ay for n in range(count)), (kind, clip)
        check(True, f'{kind}: rests on anchor row {ay} across all 34 frames')

# 3. Specific material-appropriate death checks for each of the 7 Solar Crucible kinds.
kind = 'solar_emberling'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(idle, GOLD).sum() >= 25 and material(dead, GOLD).sum() == 0,
      'solar_emberling: blazing solar flame crown gutters out completely on death')
ib = bounds(material(idle, BROWN) | material(idle, SLATE))
db = bounds(material(dead, BROWN) | material(dead, SLATE))
check((db[2] - db[0]) > (ib[2] - ib[0]) * 1.15 and bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 14,
      'solar_emberling: basalt coal shell splits wider and lower across the ground row')

kind = 'solar_sunmoth'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(idle, GOLD).sum() >= 30 and material(dead, GOLD).sum() < material(idle, GOLD).sum() * 0.45,
      'solar_sunmoth: eclipse-eye glints, compound eyes and solar proboscis extinguish on death')
ib = bounds(material(idle, AMBER) | material(idle, CORAL))
db = bounds(material(dead, AMBER) | material(dead, CORAL))
check((db[2] - db[0]) < (ib[2] - ib[0]) * 0.60 and material(dead, BROWN).sum() > material(idle, BROWN).sum() * 0.65,
      'solar_sunmoth: sunburst wings fold inward while solid chitin thorax and abdomen remain intact')

kind = 'solar_crucible_guard'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(idle, GOLD).sum() >= 30 and material(dead, GOLD).sum() == 0,
      'solar_crucible_guard: bubbling molten helm, furnace ribs and hammer core cool and go dark on death')
check(material(dead, SLATE).sum() > material(idle, SLATE).sum() * 0.70 and bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'solar_crucible_guard: dark-iron armour, cauldron shield and hammer slump lower onto the ground row')

kind = 'solar_ashwarden'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check((material(idle, GOLD) | material(idle, CORAL)).sum() >= 20 and (material(dead, GOLD) | material(dead, CORAL)).sum() == 0,
      'solar_ashwarden: shoulder ember-braziers, visor slits and greatblade magma edge extinguish on death')
check((material(dead, SLATE) | material(dead, PURPLE)).sum() > (material(idle, SLATE) | material(idle, PURPLE)).sum() * 0.70 and bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'solar_ashwarden: obsidian helm, ash-mantle and greatblade slump lower onto the ground row')

kind = 'solar_heliomancer'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(idle, GOLD).sum() >= 80 and material(dead, GOLD).sum() == 0,
      'solar_heliomancer: radiant sun-disc halo and scepter solar core extinguish on death')
check((material(dead, CRIMSON) | material(dead, AMBER) | material(dead, BROWN)).sum() > (material(idle, CRIMSON) | material(idle, AMBER) | material(idle, BROWN)).sum() * 0.70 and bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'solar_heliomancer: solar vestments, miter and scepter collapse into a low heap on the ground row')

kind = 'solar_heart'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check((material(idle, GOLD) | material(idle, CORAL)).sum() >= 80 and (material(dead, GOLD) | material(dead, CORAL)).sum() == 0,
      'solar_heart: roaring solar corona and blazing core extinguish on death')
check((material(dead, SLATE) | material(dead, BROWN)).sum() > (material(idle, SLATE) | material(idle, BROWN)).sum() * 0.65 and bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 18,
      'solar_heart: dark-iron crucible bowl and containment fins collapse onto the ground row')

kind = 'solar_cinder'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check((material(idle, GOLD) | material(idle, CORAL) | material(idle, CRIMSON)).sum() >= 40 and (material(dead, GOLD) | material(dead, CORAL) | material(dead, CRIMSON)).sum() == 0,
      'solar_cinder: internal magma fissures and lava-hollow eyes gutter out on death')
ib = bounds(material(idle, SLATE) | material(idle, BROWN))
db = bounds(material(dead, SLATE) | material(dead, BROWN))
check((db[2] - db[0]) > (ib[2] - ib[0]) * 1.15 and bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 12,
      'solar_cinder: basalt-slag carapace splits wider and lower across the ground row')

print(f'crucible-materials: {checks} checks passed')
