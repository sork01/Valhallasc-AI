#!/usr/bin/env python3
"""Check material-specific deaths, grounding/hovering and Cathedral preservation in the exported Sunken Astrolabe atlases.

MUTATE_KIND=astro_gearling replaces its death with idle in memory (or reads MUTATE_PNG) and must fail.
"""
import json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/astrolabe-slime-original-20261111')
sys.path.insert(0, str(ROOT / 'scripts'))
import kindframe
from astral_slime_redraw import PALETTE, AMBER, GOLD, BROWN, TEAL, AZURE, SLATE, PEARL, PURPLE
from astrolabe_slime_redraw import KINDS, FLYING

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

# 3. Specific material-appropriate death checks for each of the 6 Sunken Astrolabe kinds.
kind = 'astro_gearling'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, GOLD).sum() > material(idle, GOLD).sum() * 0.75 and material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.55,
      'astro_gearling: rigid brass gear wheel and clockwork hull retain their solid area')
check(not material(dead, TEAL).any(),
      'astro_gearling: turquoise aether-core and optical glow shut off on death')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 6,
      'astro_gearling: piston legs buckle and gear hull tips lower')

kind = 'astro_starling'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, GOLD).sum() > material(idle, GOLD).sum() * 0.60 and material(dead, AMBER).sum() > material(idle, AMBER).sum() * 0.60,
      'astro_starling: rigid five-pointed golden star hull stays intact on the ground')
check(not material(dead, AZURE).any() and not material(dead, TEAL).any(),
      'astro_starling: cobalt-and-teal comet trail dissipates completely on death')

kind = 'astro_sentinel'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, SLATE).sum() > material(idle, SLATE).sum() * 0.65 and material(dead, GOLD).sum() > material(idle, GOLD).sum() * 0.65,
      'astro_sentinel: steel armour, brass orbit ring and staff retain their solid mass')
check(not material(dead, TEAL).any(),
      'astro_sentinel: turquoise chest core, orbiting bead and visor glow shut off on death')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'astro_sentinel: brass knees buckle and torso topples lower')

kind = 'astro_warden'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, AZURE).sum() > material(idle, AZURE).sum() * 0.65 and material(dead, GOLD).sum() > material(idle, GOLD).sum() * 0.65,
      'astro_warden: cobalt plate armour and gold-crossed Meridian Shield keep their area')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'astro_warden: armoured knight collapses lower onto the ground')

kind = 'astro_navigator'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, AZURE).sum() > material(idle, AZURE).sum() * 0.55 and material(dead, PEARL).sum() > material(idle, PEARL).sum() * 0.65,
      'astro_navigator: navy greatcoat and braided beard stay intact as he collapses')
check(not material(dead, TEAL).any(),
      'astro_navigator: cyan ocular monocle and spyglass lens glints go dark on death')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1] + 10,
      'astro_navigator: collapses lower into his greatcoat')

kind = 'astro_axis'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, GOLD).sum() > material(idle, GOLD).sum() * 0.55 and material(dead, SLATE).sum() > material(idle, SLATE).sum() * 0.55,
      'astro_axis: rigid brass and steel armillary rings retain their mass in the collapsed heap')
check(not material(dead, PURPLE).any() and not material(dead, TEAL).any(),
      'astro_axis: celestial core glow and orbiting star nodes extinguish on death')

print(f'astrolabe-materials: {checks} checks passed')
