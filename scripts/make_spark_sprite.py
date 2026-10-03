#!/usr/bin/env python3
"""Spark Travel, makesprites workflow: preview | build [--replace] | export.

build --replace discards only this spark's PixelFlow edits; export reads the saved sprite back.
64x64, centre anchor (32,32), twelve frames at 12 fps, transparent indexed art.
"""
import json
import math
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'scripts/spark_raw.npz'
META = ROOT / 'client/assets/spark.txt'
PALETTE = ['#00000000', '#254c78', '#428fae', '#5bcfcf', '#a2f1da', '#f7cc65', '#ffe6a0', '#fff9dc', '#ffffff']
N, COUNT = 64, 12


def frames():
    result = []
    for k in range(COUNT):
        im = Image.new('L', (N, N), 0)
        d = ImageDraw.Draw(im)
        t = k / COUNT * math.tau
        # The tail is left; the game rotates the entire sprite into its direction of flight.
        d.polygon([(7, 32), (23, 24), (35, 23), (46, 32), (34, 41), (23, 39)], fill=1)
        d.polygon([(10, 32), (24, 28), (36, 25), (43, 32), (33, 38), (24, 35)], fill=2)
        d.polygon([(15, 32), (31, 28), (38, 31), (31, 36)], fill=3)
        for j in range(9):
            f = (j / 9 + k / COUNT) % 1
            x = round(32 - 22 * f)
            y = round(32 + math.sin(f * 13 + j * 2.4) * (3 + 10 * f))
            d.rectangle((x, y, x + 1, y + 1), fill=4 if j % 2 else 6)
        radius = 8 + round(math.sin(t) * 1.3)
        d.ellipse((32-radius, 32-radius, 32+radius, 32+radius), fill=3)
        d.ellipse((26, 26, 38, 38), fill=5)
        d.ellipse((28, 27, 36, 36), fill=6)
        r = 12 + round(2 * math.cos(t))
        d.polygon([(32, 32-r), (35, 29), (32+r, 32), (35, 35), (32, 32+r), (29, 35), (32-r, 32), (29, 29)], fill=7)
        d.polygon([(32, 24), (34, 30), (40, 32), (34, 34), (32, 40), (30, 34), (24, 32), (30, 30)], fill=8)
        for j in range(4):
            a = t + j * math.tau / 4
            x, y = round(32 + math.cos(a)*22), round(32 + math.sin(a)*21)
            r = 2 if (k + j) % 3 else 3
            d.line((x-r, y, x+r, y), fill=6, width=1)
            d.line((x, y-r, x, y+r), fill=7, width=1)
            d.point((x,y),fill=8)
        result.append(np.asarray(im))
    return result


def pf_module():
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf
    return pf


def sheet(grids, palette):
    rgb = np.array([[int(h[i:i+2],16) for i in (1,3,5)] + [0 if k == 0 else 255] for k,h in enumerate(palette)], np.uint8)
    return Image.fromarray(np.concatenate([rgb[g] for g in grids], axis=1))


def main():
    command = sys.argv[1] if len(sys.argv)>1 else 'preview'
    if command == 'preview':
        grids = frames()
        np.savez_compressed(RAW, frames=np.array(grids), palette=np.array(PALETTE))
        art = sheet(grids, PALETTE).resize((N*COUNT*2, N*2), Image.Resampling.NEAREST)
        bg = Image.new('RGBA', art.size, '#355847'); bg.alpha_composite(art)
        bg.save(ROOT / 'test-results/spark-preview.png')
        print('Preview: test-results/spark-preview.png')
    elif command == 'build':
        pf = pf_module()
        old = json.loads(META.read_text()).get('sprite') if META.exists() else None
        if old and '--replace' not in sys.argv:
            sys.exit('Spark already exists; export preserves edits, build --replace discards them.')
        if old: pf.api('delete', {'sprite_id': old})
        grids = frames()
        sid = pf.create('valhallasc_spark_travel',N,N,COUNT,PALETTE,fps=12)
        META.write_text(json.dumps(dict(size=N,anchor=[32,32],frames=COUNT,fps=12,sprite=sid),indent=2)+'\n')
        for k,grid in enumerate(grids): pf.draw_grid(sid,k,0,grid)
        print('Editable: /pixelflow/?sprite='+sid)
    elif command == 'export':
        pf = pf_module()
        meta = json.loads(META.read_text())
        sp,grids = pf.load(meta['sprite'])
        assert len(grids)==COUNT and sp['width']==N and sp['height']==N
        sheet([g[0] for g in grids], sp['palette']).save(ROOT/'client/assets/spark.png')
        print('Exported client/assets/spark.png from PixelFlow')
    else: sys.exit('Use preview, build or export')


if __name__ == '__main__': main()
