#!/usr/bin/env python3
"""Check material-specific deaths, grounding/hovering and Cathedral preservation in the exported Thunderheart Gate atlases.

MUTATE_KIND=thunder_spark replaces its death with idle in memory (or reads MUTATE_PNG) and must fail.
"""
import json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/thunderheart-slime-original-20261111')
sys.path.insert(0, str(ROOT / 'scripts'))
import kindframe
from astral_slime_redraw import PALETTE, AMBER, GOLD, BROWN, TEAL, AZURE, SLATE, PEARL, PURPLE, VIOLET
from thunderheart_slime_redraw import KINDS, FLYING

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


# 1. Shared Cathedral manifest preservation (140 unrelated kinds + fallback frame + clip rates).
other_kinds = [k for k in backup_meta['kinds'] if k not in KINDS]
check(len(other_kinds) == 140, f'cathedral.txt preserves all 140 other kinds ({len(other_kinds)})')
check(
    all(meta['sprites'].get(k) == backup_meta['sprites'].get(k) and meta['tops'].get(k) == backup_meta['tops'].get(k) for k in other_kinds),
    'all 140 unrelated Cathedral sprite IDs and health-bar tops are untouched',
)
check(
    (tuple(meta['frame']), tuple(meta['anchor'])) == ((96, 96), (48, 90)),
    'fallback Cathedral 96x96 frame and (48, 90) anchor preserved',
)

# 2. Per-kind frame geometry, distinct animations, grounding/hovering.
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

# 3. Specific material-appropriate death checks for each of the 6 Thunderheart Gate kinds.
kind = 'thunder_spark'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.65 and material(dead, SLATE).sum() > material(idle, SLATE).sum() * 0.65,
      'thunder_spark: bronze-and-slate storm-capacitor shell stays intact as it lands on the ground')
check(not material(dead, TEAL).any() and not material(dead, GOLD).any(),
      'thunder_spark: forked golden lightning prongs and teal plasma arcs discharge completely on death')

kind = 'thunder_ray'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, AZURE).sum() > material(idle, AZURE).sum() * 0.60 and material(dead, PEARL).sum() > material(idle, PEARL).sum() * 0.60,
      'thunder_ray: cobalt manta body and pearl belly plates stay intact on the ground')
check(not material(dead, TEAL).any() and not material(dead, GOLD).any(),
      'thunder_ray: golden lightning tail-barb and wing-vein charge extinguish on death')

kind = 'thunder_guard'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, SLATE).sum() > material(idle, SLATE).sum() * 0.65 and material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.65,
      'thunder_guard: slate armour, tower shield and bronze trim retain their solid mass')
check(not material(dead, TEAL).any(),
      'thunder_guard: storm-mace core and visor glow shut off on death')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'thunder_guard: knees buckle and armoured guard collapses lower')

kind = 'thunder_conductor'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, PURPLE).sum() > material(idle, PURPLE).sum() * 0.55 and material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.65,
      'thunder_conductor: violet conductor coat and shoulder copper Tesla coils stay intact')
check(not material(dead, TEAL).any(),
      'thunder_conductor: Tesla coil arcs, eye glare and staff discharge extinguish on death')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'thunder_conductor: collapses lower into his conductor coat')

kind = 'thunder_bastion'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, SLATE).sum() > material(idle, SLATE).sum() * 0.65 and material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.65,
      'thunder_bastion: basalt-slate fortress stone, crenellations and pylon hammer retain their solid mass')
check(not material(dead, TEAL).any(),
      'thunder_bastion: turquoise storm-furnace chest core and furnace-slit eyes shut off on death')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'thunder_bastion: stone pillar legs buckle and fortress torso slumps lower')

kind = 'thunder_heart'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, SLATE).sum() > material(idle, SLATE).sum() * 0.55 and material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.55,
      'thunder_heart: steel and bronze stormgate containment rings retain their mass in the collapsed heap')
check(not material(dead, TEAL).any() and not material(dead, GOLD).any(),
      'thunder_heart: orbiting golden lightning pylons and stormgate arcs extinguish on death')

print(f'thunderheart-materials: {checks} checks passed')
