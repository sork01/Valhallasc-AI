#!/usr/bin/env python3
"""NPC player-style atlases through PixelFlow: preview | build | export | verify | sheet [design ...]  (NPC-PLAYER-STYLE-GENERAL)

Side by side with the old art, never over it: PixelFlow sprites `valhallasc_npcp_<design>` (the old `valhallasc_npc_*` saves and
their ids are untouched), atlases `client/assets/npcp_<design>.png`, manifest `client/assets/npcp.txt` (same contract as npc.txt, plus
per-design `amounts` for the client's skin/hair/cloth remap). Nothing reads npcp.txt until a batch is approved and wired in.
build creates only missing saves (editor work is never replaced); export always reads the saved frames back.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

import npcp_general as G
from npcp_general import core, cc, CLIPS

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'client/assets'
MANIFEST = ASSETS / 'npcp.txt'
PREFIX = 'valhallasc_npcp_'


def selected():
    return G.pick(sys.argv[2:])


def frames(key):
    out, palette = {}, None
    for clip, n in CLIPS:
        out[clip] = []
        for k in range(n):
            img, idx, palette = G.render(key, clip, k)
            out[clip].append(idx)
    return out, palette


def validate(key, data):
    for clip, rows in data.items():
        for k, grid in enumerate(rows):
            ys, xs = np.nonzero(grid)
            assert len(xs) and xs.min() > 0 and xs.max() < 95 and ys.min() > 0 and ys.max() < 95, (key, clip, k)
        assert len({g.tobytes() for g in rows}) >= 3, (key, clip, 'static')


def design_meta(key, palette):
    """Remap table: the exact exported hex of each recolourable tone, so the client can recolour per person (general designs) and find the skin for head sockets (all)."""
    d = G.DESIGNS[key]
    m = G.materials(d)
    mats = {}
    for group in ('skin', 'hair', 'cloth'):
        for i, hexc in enumerate(m[group]):
            assert hexc in palette
            mats[f'{group}{i}'] = hexc
    meta = dict(general=d['general'], name=d['name'], materials=mats)
    if d['general']:
        meta['amounts'] = {g: list(a) for g, a in G.AMOUNTS.items()}
    if d.get('tree'):
        meta['species'] = 'treefolk'
    if d.get('hover'):
        meta['species'] = 'winged'
    if d.get('tail'):
        meta['species'] = 'merfolk'
    return meta


def metadata(saved, palettes):
    clips, offset = {}, 0
    for row, (clip, count) in enumerate(CLIPS):
        clips[clip] = dict(row=row, n=count, fps={'idle': 6, 'walk': 10, 'talk': 6}[clip], editorStart=offset)
        offset += count
    return dict(frame=[96, 96], anchor=[48, 90], scale=1.4, clips=clips, sprites=saved,
                designs={k: design_meta(k, palettes[k]) for k in saved})


def pf_api():
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf
    original = pf.api

    def paced(*args, **kwargs):
        for _ in range(8):
            time.sleep(.16)
            result = original(*args, **kwargs)
            if any(e.get('code') == 'rate_limited' for e in result.get('errors', [])):
                print('PixelFlow rate limit: waiting', flush=True)
                time.sleep(10)
                continue
            return result
        raise RuntimeError('PixelFlow request window remains full')
    pf.api = paced
    return pf


def palettes_for(keys):
    out = {}
    for key in keys:
        _, _, pal = G.render(key, 'idle', 0)
        out[key] = pal
    return out


def read_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def build():
    api = pf_api()
    old = read_manifest()
    saved = dict(old.get('sprites', {}))
    existing = api.ids(PREFIX)
    for key in selected():
        if key in saved:
            continue
        data, palette = frames(key)
        validate(key, data)
        assert len(palette) <= 255 and len(set(palette)) == len(palette), (key, len(palette))
        name = PREFIX + key
        sid = existing.get(name) or api.create(name, 96, 96, 20, palette, fps=6)
        offset = 0
        for clip, count in CLIPS:
            for grid in data[clip]:
                api.draw_grid(sid, offset, 0, grid)
                offset += 1
        saved[key] = sid
        MANIFEST.write_text(json.dumps(metadata(saved, palettes_for(saved)), indent=2, ensure_ascii=False) + '\n')
        print('built', key, sid, flush=True)


def export(verify=False):
    api = pf_api()
    manifest = read_manifest()
    tops, bounds = dict(manifest.get('tops', {})), dict(manifest.get('bounds', {}))
    for key in selected():
        sp, data = api.load(manifest['sprites'][key])
        assert (sp['width'], sp['height'], len(data)) == (96, 96, 20), key
        pal = sp['palette']
        sheet = Image.new('RGBA', (768, 288))
        offset, top, box, checked = 0, 0, [96, 96, 0, 0], {}
        for row, (clip, count) in enumerate(CLIPS):
            checked[clip] = []
            for n in range(count):
                grid = data[offset][0]
                offset += 1
                checked[clip].append(grid)
                ys, xs = np.nonzero(grid)
                top = max(top, 90 - int(ys.min()))
                box = [min(box[0], int(xs.min())), min(box[1], int(ys.min())), max(box[2], int(xs.max() + 1)), max(box[3], int(ys.max() + 1))]
                sheet.alpha_composite(Image.fromarray(api.to_rgba(grid, pal)), (n * 96, row * 96))
        validate(key, checked)
        target = ASSETS / f'npcp_{key}.png'
        if verify:
            assert sheet.tobytes() == Image.open(target).convert('RGBA').tobytes(), key
            print('verified', key, flush=True)
        else:
            sheet.save(target, optimize=True)
            tops[key], bounds[key] = top, box
            print('exported', key, flush=True)
    if not verify:
        manifest.update(metadata(manifest['sprites'], palettes_for(manifest['sprites'])))
        manifest['tops'], manifest['bounds'] = tops, bounds
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')


def sheet():
    """Before / after contact sheet of the exported atlases (idle frame 0, walk 1, talk 1) at 3x."""
    from PIL import ImageDraw
    keys = selected()
    S = 3
    cols = 3
    out = Image.new('RGBA', (cols * 2 * 96 * S + 10, ((len(keys) + cols - 1) // cols) * (96 * S + 16)), (34, 48, 64, 255))
    dr = ImageDraw.Draw(out)
    for i, key in enumerate(keys):
        x, y = (i % cols) * 2 * 96 * S, (i // cols) * (96 * S + 16)
        dr.text((x + 4, y + 2), key, fill='white')
        for j, name in enumerate((f'npc_{key}.png', f'npcp_{key}.png')):
            im = Image.open(ASSETS / name).convert('RGBA').crop((0, 0, 96, 96)).resize((96 * S, 96 * S), Image.NEAREST)
            out.alpha_composite(im, (x + j * 96 * S, y + 14))
    path = ROOT / 'test-results/npcp-general'
    path.mkdir(parents=True, exist_ok=True)
    out.save(path / 'before-after.png')
    print(path / 'before-after.png')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    {'build': build, 'export': export, 'verify': lambda: export(True), 'sheet': sheet}[cmd]()
