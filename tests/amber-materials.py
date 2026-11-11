#!/usr/bin/env python3
"""Exported-art material checks. MUTATE_KIND replaces that death with idle and must fail."""
import json, os, sys, hashlib
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/amber-slime-original-20261111')
sys.path.insert(0, str(ROOT / 'scripts'))
import kindframe
from astral_slime_redraw import PALETTE, AMBER, GOLD, BROWN, BONE, PURPLE, CRIMSON, TEAL, PEARL
from amber_slime_redraw import KINDS, FLYING
from rollback_amber_art import without_amber
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


other = [k for k in backup_meta['kinds'] if k not in KINDS]
check(len(other) == 139 and without_amber(meta) == without_amber(backup_meta), 'all 139 unrelated Cathedral kinds and manifest fields preserved')
baseline = json.loads((BACKUP/'manifest.txt').read_text())['unrelatedAtlasHashes']
check(all(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == digest for rel,digest in baseline.items()), f'all {len(baseline)} unrelated native Cathedral atlases unchanged (borrowed aliases retain their source IDs)')
for kind in KINDS:
    w, h, ax, ay = kindframe.frame_of(meta, kind)
    check((w,h,ax,ay) == (176,172,88,164), f'{kind}: declared frame/anchor')
    att = [cell(kind,'attack',n) for n in range(8)]
    death = [cell(kind,'die',n) for n in range(8)]
    check(len({im.tobytes() for im in att}) == 8 and len({im.tobytes() for im in death}) == 8, f'{kind}: eight distinct attacks and deaths')
    lows = [bounds(im[:,:,3] > 0)[3] for im in death]
    check(lows[-1] == ay and all(a <= b for a,b in zip(lows,lows[1:])), f'{kind}: death stays on or settles monotonically onto ground')
    idle, dead = cell(kind,'idle',0), death[-1]
    if os.environ.get('MUTATE_MATERIAL') == kind:
        dead = idle.copy()  # Pass the animation contract, then challenge the material-specific assertions.
    ib, db = bounds(idle[:,:,3] > 0), bounds(dead[:,:,3] > 0)
    height = lambda box: box[3] - box[1] + 1
    width = lambda box: box[2] - box[0] + 1
    if kind == 'amber_page':
        check(height(db) < height(ib) * .8 and width(db) > width(ib), 'Page: parchment folds into a low, wider torn sheet')
        check(material(dead,BONE).sum() > 100 and material(dead,CRIMSON).sum() > 5, 'Page: paper and attached wax seal remain')
    elif kind == 'amber_moth':
        check(width(db) < width(ib) * .85, 'Moth: hinged wings fold inward')
        check(material(dead,CRIMSON).sum() == 0 and material(idle,CRIMSON).sum() > 0, 'Moth: compound eye glints extinguish')
        check(material(dead,AMBER).sum() > 100 and material(dead,BROWN).sum() > 20, 'Moth: rigid amber wings and chitin body remain')
    elif kind == 'amber_sentinel':
        check(material(dead,TEAL).sum() == 0 and material(idle,TEAL).sum() > 0, 'Sentinel: visor darkens')
        check(material(dead,GOLD).sum() > 100 and material(dead,CRIMSON).sum() > 50 and width(db) > width(ib), 'Sentinel: rigid armour and tome shield buckle sideways together')
    elif kind == 'amber_curator':
        check(height(db) < height(ib) * .85 and db[0] > ib[0], 'Curator: body topples onto its side')
        check(material(dead,BONE).sum() > 50 and material(dead,PEARL).sum() > 30 and material(dead,BROWN).sum() > 100, 'Curator: head, hair and robes remain bodily')
    elif kind == 'amber_chronicle':
        check(width(db) > width(ib) * 1.8 and height(db) < height(ib), 'Chronicle: rigid binding splits and open covers settle sideways')
        check(material(dead,CRIMSON).sum() > 100 and material(dead,BONE).sum() > 300, 'Chronicle: both leather binding and loose paper remain')
    elif kind == 'amber_memory':
        check(material(dead,PURPLE).sum() == 0 and material(idle,PURPLE).sum() > 30, 'Memory: trapped spirit dissipates completely')
        check(material(dead,AMBER).sum() > 100 and width(db) > width(ib) * 1.5 and height(db) < height(ib)*.8, 'Memory: rigid amber halves fall outward into low shards')
    elif kind == 'amber_cocoon':
        check(material(dead,BROWN).sum() == 0 and material(idle,BROWN).sum() > 30, 'Cocoon: trapped humanoid is released when the shell breaks')
        check(material(dead,AMBER).sum() > 100 and width(db) > width(ib) * 1.5 and height(db) < height(ib)*.8, 'Cocoon: split resin shells settle rigidly outward')
        check(bounds(att[4][:,:,3] > 0)[2] - bounds(att[0][:,:,3] > 0)[2] >= 10, 'Cocoon: restrained defensive resin pulse visibly extends')
print(f'amber-materials: {checks} checks')
