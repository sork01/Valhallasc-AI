#!/usr/bin/env python3
"""Check material-specific deaths, grounding/hovering and Cathedral preservation in the exported Seed Vault atlases.

MUTATE_KIND=seed_mote replaces its death with idle in memory (or reads MUTATE_PNG) and must fail.
"""
import json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/seedvault-slime-original-20261111')
sys.path.insert(0, str(ROOT / 'scripts'))
import kindframe
from astral_slime_redraw import PALETTE, AMBER, GOLD, BROWN, LEAF, GREEN, PINK, BONE
from seedvault_slime_redraw import KINDS, FLYING

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


# 1. Shared Cathedral manifest preservation (138 unrelated kinds + fallback frame + clip rates).
other_kinds = [k for k in backup_meta['kinds'] if k not in KINDS]
check(len(other_kinds) == 138, f'cathedral.txt preserves all 138 other kinds ({len(other_kinds)})')
for k in other_kinds:
    check(meta['sprites'].get(k) == backup_meta['sprites'].get(k), f'preserved sprite ID for {k}') if False else None
check(
    all(meta['sprites'].get(k) == backup_meta['sprites'].get(k) and meta['tops'].get(k) == backup_meta['tops'].get(k) for k in other_kinds),
    'all 138 unrelated Cathedral sprite IDs and health-bar tops are untouched',
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

# 3. Specific material-appropriate death checks for each of the 8 Seed Vault kinds.
for kind in ('seed_mote', 'seed_worldseed'):
    idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
    ib = bounds(material(idle, AMBER))
    db = bounds(material(dead, AMBER))
    check((db[2] - db[0]) > (ib[2] - ib[0]) * 1.15 and (db[3] - db[1]) < (ib[3] - ib[1]) * 0.85,
          f'{kind}: rigid seed shell splits wider and lower across the ground instead of vanishing')

kind = 'seed_amberwing'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
ib = bounds(material(idle, AMBER) | material(idle, GOLD))
db = bounds(material(dead, AMBER) | material(dead, GOLD))
check((db[2] - db[0]) < (ib[2] - ib[0]) * 0.60 and material(dead, BROWN).sum() > material(idle, BROWN).sum() * 0.50,
      'seed_amberwing: wings fold inward on death while retaining solid chitin mass')

kind = 'seed_rootguard'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, BROWN).sum() > material(idle, BROWN).sum() * 0.7,
      'seed_rootguard: bark armor, shield and club retain solid wooden mass')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'seed_rootguard: topples downward on death')

kind = 'seed_warden'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(0.75 < material(dead, GOLD).sum() / material(idle, GOLD).sum() < 1.25,
      'seed_warden: rigid concentric gold rings and staff head keep their area')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'seed_warden: collapses lower as the robe settles')

kind = 'seed_germinator'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, PINK).sum() > material(idle, PINK).sum() * 0.5 and material(dead, LEAF).sum() > material(idle, LEAF).sum() * 0.55,
      'seed_germinator: carnivorous petals and pod body wilt down without dissolving')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 12,
      'seed_germinator: pod sinks low between splayed vine-legs on death')

kind = 'seed_sprout'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.65 and material(dead, BROWN).sum() > material(idle, BROWN).sum() * 0.65,
      'seed_sprout: acorn cap and seed hull stay solid as it topples')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 8,
      'seed_sprout: topples lower onto its side on death')

kind = 'seed_treant'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, BROWN).sum() > material(idle, BROWN).sum() * 0.65 and material(dead, PINK).sum() > material(idle, PINK).sum() * 0.55,
      'seed_treant: bark trunk and blossom crown stay intact as it falls')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'seed_treant: trunk settles lower on death')

print(f'seedvault-materials: {checks} checks passed')
