#!/usr/bin/env python3
"""makesprites workflow: preview | build [--replace] | export.

Build saves one NEW valhallasc_ironhide_all sprite in PixelFlow (34 frames). It refuses
existing names unless --replace is given; --replace discards their hand edits.
Export reads editor frames back so edits survive. No original Valhalla art is touched.
Needs numpy/Pillow; build/export also need PixelFlow and its local agent key.
"""
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import urllib.request
import urllib.error

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
W, H, AX, AY = 72, 64, 36, 60
PREFIX = 'valhallasc_ironhide_'
PALETTE = ['#00000000', '#171e2b', '#324658', '#58758a', '#8aafbf',
           '#d8e9e6', '#79472b', '#bf8548', '#f4cb78', '#e7523e', '#fff0bc']
CLIPS = {'idle': (6, 6), 'walk': (10, 8), 'attack': (12, 8),
         'hurt': (10, 4), 'die': (8, 8)}


def frame(clip, n):
    """Fixed foot anchor, right facing; a steel shell, six legs and a bronze horn."""
    im = Image.new('P', (W, H), 0)
    d = ImageDraw.Draw(im)
    lean, lift, squash = 0, 0, 1
    if clip == 'idle':
        lift = [0, 1, 2, 1, 0, 0][n]
    elif clip == 'walk':
        lift = [0, 0, 2, 5, 3, 0, 0, 0][n]
    elif clip == 'attack':
        lean = [-1, -3, -4, 2, 5, 6, 2, 0][n]
        lift = [0, 0, 0, 3, 5, 0, 0, 0][n]
        squash = [.95, .9, .85, 1.05, 1, .9, .95, 1][n]
    elif clip == 'hurt':
        lean = [-4, -2, -1, 0][n]
    elif clip == 'die':
        lean = -min(n, 4)
        squash = max(.28, 1 - max(0, n - 1) * .14)
    cx, cy = AX - 3 + lean, AY - 19 - lift
    ry = round(13 * squash)
    dead = clip == 'die' and n >= 2
    if dead:
        cy = AY - ry - 4
    # Far legs, then body, then near legs: the silhouette stays articulated.
    stride = math.sin(n * math.pi / 2) * 3 if clip == 'walk' else 0
    for side in (-1, 1):
        for k in range(3):
            lx = cx - 12 + k * 10
            phase = stride * (-1 if k == 1 else 1)
            ly = cy + (3 if side == 1 else -5)
            tip = (round(lx + phase - 4), AY - (2 if side == 1 else 10))
            knee = (round(lx - 7), ly + 7)
            if dead:
                knee, tip = (lx - 3, min(AY - 1, cy + 6)), (lx + 2, min(AY - 1, cy + 7))
            d.line([(lx, ly), knee, tip], fill=1, width=4)
            d.line([(lx, ly), knee, tip], fill=7 if side == 1 else 6, width=2)
    d.ellipse((cx - 19, cy - ry, cx + 15, cy + ry), fill=1)
    d.ellipse((cx - 17, cy - ry + 2, cx + 13, cy + ry - 2), fill=2)
    d.ellipse((cx - 16, cy - ry + 2, cx + 11, cy + ry - 5), fill=3)
    d.ellipse((cx - 13, cy - ry + 3, cx + 7, cy + 1), fill=4)
    d.arc((cx - 14, cy - ry + 3, cx + 8, cy + ry - 4), 195, 290, fill=5, width=2)
    # Split wing plates and a bronze band make a readable armored beetle.
    d.line([(cx - 15, cy + 2), (cx + 11, cy - 3)], fill=1, width=2)
    d.arc((cx - 7, cy - ry, cx + 2, cy + ry), 260, 95, fill=7, width=2)
    for x, y in ((cx - 10, cy + 6), (cx + 5, cy + 5), (cx - 6, cy - 8)):
        d.rectangle((x, y, x + 1, y + 1), fill=8)
    hx, hy = cx + 16, min(cy + 4, AY - 8) if dead else cy + 4
    d.ellipse((hx - 7, hy - 8, hx + 7, hy + 8), fill=1)
    d.ellipse((hx - 5, hy - 6, hx + 5, hy + 6), fill=6)
    d.ellipse((hx - 5, hy - 6, hx + 3, hy + 2), fill=7)
    # Long forward horn lifts during anticipation and drives the lunge.
    horn_y = hy - (10 if clip == 'attack' and n < 3 else 4)
    d.polygon([(hx + 1, hy - 5), (hx + 7, horn_y), (hx + 11, horn_y - 9),
               (hx + 11, horn_y + 1), (hx + 6, hy + 1)], fill=1)
    d.polygon([(hx + 3, hy - 4), (hx + 8, horn_y), (hx + 10, horn_y - 5),
               (hx + 9, horn_y + 1), (hx + 5, hy - 1)], fill=8)
    if dead:
        d.line([(hx - 1, hy - 1), (hx + 3, hy + 3)], fill=1, width=1)
        d.line([(hx + 3, hy - 1), (hx - 1, hy + 3)], fill=1, width=1)
    elif clip == 'idle' and n == 3:
        d.line([(hx - 1, hy), (hx + 3, hy)], fill=9, width=1)
    else:
        d.rectangle((hx - 1, hy - 1, hx + 3, hy + 1), fill=1)
        d.rectangle((hx, hy - 1, hx + 2, hy), fill=9)
        d.point((hx + 1, hy - 1), fill=10)
    # A brief impact spark and white hurt/death flash.
    if clip == 'attack' and n == 5:
        d.line([(W - 6, hy - 11), (W - 6, hy - 3)], fill=10)
        d.line([(W - 10, hy - 7), (W - 2, hy - 7)], fill=10)
    arr = np.array(im)
    if (clip in ('hurt', 'die')) and n == 0:
        arr[arr > 1] = 10
    if clip == 'hurt' and n == 1:
        arr[(arr == 2) | (arr == 3)] = 4
    return arr


def rgba(grid, palette=PALETTE):
    colors = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] +
                       [0 if n == 0 else 255] for n, c in enumerate(palette)], dtype=np.uint8)
    return Image.fromarray(colors[grid])


def preview(frames, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for clip, grids in frames.items():
        sheet = Image.new('RGBA', (8 * W, H + 12), '#466e46')
        d = ImageDraw.Draw(sheet)
        for n, grid in enumerate(grids):
            sheet.alpha_composite(rgba(grid), (n * W, 0))
            d.line([(n * W + AX - 2, AY), (n * W + AX + 2, AY)], fill='#eabce1')
            d.text((n * W + 2, H), f'{clip} {n}', fill='white')
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).save(out / f'{clip}.png')


def api(route, body=None):
    env = Path(os.environ.get('PIXELFLOW_ENV', '/home/serveperry/webserver/www/pixelflow/.env'))
    key = re.search(r'^PIXELFLOW_API_KEY=(\S+)', env.read_text(), re.M).group(1)
    base = os.environ.get('PIXELFLOW_API_URL', 'https://localhost/pixelflow/api/sprites/')
    req = urllib.request.Request(base + route, None if body is None else json.dumps(body).encode(),
                                 {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
        raise RuntimeError(result.get('errors', result.get('error', 'PixelFlow request failed'))) from None
    if result.get('ok') is False:
        raise RuntimeError(result.get('errors', 'PixelFlow request failed'))
    return result


def ids():
    return {s['name']: s['sprite_id'] for s in api('list')['sprites'] if s['name'].startswith(PREFIX)}


def build(replace=False):
    existing = ids()
    if existing and not replace:
        raise SystemExit('Sprites already exist. Use export to preserve edits; --replace discards them.')
    if replace:
        for sid in existing.values():
            api('delete', {'sprite_id': sid})
    frames = {clip: np.array([frame(clip, n) for n in range(count)])
              for clip, (_, count) in CLIPS.items()}
    np.savez_compressed(ROOT / 'scripts/ironhide_raw.npz', **frames)
    sid = api('create', {'name': PREFIX + 'all', 'width': W, 'height': H,
                        'frames': sum(count for _, count in CLIPS.values()),
                        'layers': 1, 'fps': 10, 'palette': PALETTE, 'persist': True,
                        'ops': [{'op': 'set_layer', 'layer': 0, 'name': 'ironhide'}]})['sprite_id']
    offset = 0
    try:
        for clip, (_, count) in CLIPS.items():
            for n, grid in enumerate(frames[clip]):
                api('draw', {'sprite_id': sid, 'frame': offset + n, 'ops': [
                    {'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
            print(clip, sid, f'frames {offset}–{offset + count - 1}')
            offset += count
    except Exception:
        api('delete', {'sprite_id': sid})
        raise


def export():
    saved, clips = ids(), {}
    packet = api('get?sprite_id=' + saved[PREFIX + 'all'])
    sp = packet.get('sprite', packet)
    assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
    atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
    offset = 0
    for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
        sheet = Image.new('RGBA', (8 * W, H), '#466e46')
        for n in range(count):
            cel = sp['frames'][offset + n]['cels'][0]
            if 'rle' in cel:
                runs = cel['rle']
                grid = np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
            else:
                grid = np.array(cel['grid'], dtype=np.uint8)
            image = rgba(grid, sp['palette'])
            atlas.alpha_composite(image, (n * W, row * H))
            sheet.alpha_composite(image, (n * W, 0))
        clips[clip] = {'fps': fps, 'n': count, 'row': row, 'editorStart': offset}
        offset += count
        dest = ROOT / 'test-results/ironhide-export'
        dest.mkdir(parents=True, exist_ok=True)
        sheet.resize((sheet.width * 2, H * 2), Image.Resampling.NEAREST).save(dest / f'{clip}.png')
    atlas.save(ASSETS / 'ironhide.png', optimize=True)
    (ASSETS / 'ironhide.txt').write_text(json.dumps({'frame': [W, H], 'anchor': [AX, AY],
        'kinds': ['beetle'], 'clips': clips, 'sprites': saved}, indent=2) + '\n')
    print('Exported client/assets/ironhide.png and ironhide.txt from PixelFlow')


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if command == 'build':
        build('--replace' in sys.argv)
    elif command == 'export':
        export()
    elif command == 'preview':
        preview({c: [frame(c, n) for n in range(count)] for c, (_, count) in CLIPS.items()},
                sys.argv[2] if len(sys.argv) > 2 else ROOT / 'test-results/ironhide-preview')
    else:
        raise SystemExit('Usage: make_ironhide_sprites.py preview [directory] | build [--replace] | export')
