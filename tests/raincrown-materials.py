"""Check material-specific deaths in the exported atlas, independently of the model renderer.

MUTATE_KIND=rain_crown_droplet replaces its death with idle in memory and must fail.
"""
import json
import os
from pathlib import Path
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import kindframe
from astral_slime_redraw import PALETTE, AZURE, GOLD, TEAL, PEARL, SLATE, GREEN

meta = json.loads((ROOT / 'client/assets/cathedral.txt').read_text())
checks = 0


def check(value, label):
    global checks
    assert value, label
    checks += 1
    print(f'{checks}: {label}')


def cell(kind, clip, n):
    if os.environ.get('MUTATE_KIND') == kind and clip == 'die':
        clip, n = 'idle', 0
    w, h, _, _ = kindframe.frame_of(meta, kind)
    atlas = Image.open(ROOT / f'client/assets/cathedral_{kind}.png').convert('RGBA')
    row = meta['clips'][clip]['row']
    return np.array(atlas.crop((n*w, row*h, (n+1)*w, (row+1)*h)))


def material(im, ramp):
    colors = np.array([list(bytes.fromhex(PALETTE[i][1:])) for i in ramp])
    return (im[:, :, None, :3] == colors).all(-1).any(-1) & (im[:, :, 3] > 0)


def bounds(mask):
    ys, xs = np.nonzero(mask)
    assert len(ys), 'Material vanished'
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


for kind in ('rain_crown_droplet', 'rain_crown_sovereign'):
    idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
    iw, dw = material(idle, AZURE), material(dead, AZURE)
    ib, db = bounds(iw), bounds(dw)
    check(db[3]-db[1] < (ib[3]-ib[1])*.6 and db[2]-db[0] > (ib[2]-ib[0])*1.3,
          f'{kind}: water drains to a wider, shallow splash')
    ig, dg = material(idle, GOLD), material(dead, GOLD)
    check(.8 < dg.sum()/ig.sum() < 1.2, f'{kind}: rigid gold crown retains its area')
    gb = bounds(dg)
    check(gb[3] >= db[1]-2 and gb[1] < db[1], f'{kind}: crown rests against its water, with no support gap')
    lows = [bounds(cell(kind, 'die', n)[:, :, 3] > 0)[3] for n in range(8)]
    check(all(0 <= b-a <= 10 for a, b in zip(lows, lows[1:])), f'{kind}: death descends continuously without a last-frame jump')

kind = 'rain_crown_oracle'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, GREEN).sum() > material(idle, GREEN).sum()*.5,
      'Oracle retains jade skin and cloth instead of dissolving')
check(bounds(dead[:, :, 3] > 0)[1] >= bounds(idle[:, :, 3] > 0)[1]+8,
      'Oracle buckles down as the robe settles')

kind = 'rain_crown_guard'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
for ramp, label in ((TEAL, 'umbrella shield'), (PEARL, 'spearhead')):
    check(.8 < material(dead, ramp).sum()/material(idle, ramp).sum() < 1.2,
          f'Guard rigid {label} keeps its area through the fall')

kind = 'rain_crown_gatekeeper'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, SLATE).sum() > material(idle, SLATE).sum()*.65,
      'Gatekeeper retains solid stone and iron mass')
check(not material(dead, AZURE).any(), 'Gatekeeper water jets stop at death')
check(bounds(material(dead, SLATE))[3] == kindframe.frame_of(meta, kind)[3],
      'Gatekeeper stone corpse itself rests on the ground, without a jet as false support')

kind = 'rain_crown_sibyl'
idle, dead = cell(kind, 'idle', 0), cell(kind, 'die', 7)
check(material(dead, PEARL).sum() < material(idle, PEARL).sum()*.4,
      'Sibyl pale cloud disperses as her body settles')
check(not material(dead, AZURE).any(), 'Sibyl rain stops at death')
check(bounds(dead[:, :, 3] > 0)[3] == kindframe.frame_of(meta, kind)[3],
      'Sibyl corpse lands on the anchor row')
print(f'raincrown-materials: {checks} checks')
