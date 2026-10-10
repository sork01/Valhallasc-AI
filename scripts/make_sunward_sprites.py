#!/usr/bin/env python3
"""Nine editable PixelFlow sprites for Sunward Vale: six animals and three villagers.

preview makes a contact sheet; build creates fresh PixelFlow saves; export reads
editor frames without discarding changes; verify compares all exported frames.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import make_moonspore_sprites as m
from make_crag_sprites import Palette, ellipsoid, polygon, gradient

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
KINDS = ['meadowhare', 'sunbacksnail', 'brushfox', 'spadebadger',
         'honeyjaw', 'wickerwarden', 'sun_miller', 'sun_keeper', 'sun_travel']
RAMPS = {
    'meadowhare': ('#342e33', '#85694e', '#c99b69', '#eed4a1', '#fff4d4'),
    'sunbacksnail': ('#333442', '#647f69', '#a0b579', '#e2cc8e', '#f2ebbd'),
    'brushfox': ('#3d3035', '#995642', '#d57b49', '#f2b779', '#fff0c8'),
    'spadebadger': ('#2d3440', '#626c70', '#969b8b', '#e7e1c8', '#fff5dc'),
    'honeyjaw': ('#2e2730', '#584338', '#926c45', '#d4a962', '#ffe497'),
    'wickerwarden': ('#312f35', '#6b553e', '#a98454', '#d6bd78', '#fce3a2'),
    'sun_miller': ('#2f3542', '#657d78', '#9db0a0', '#e6d5ac', '#f8e6ba'),
    'sun_keeper': ('#293b32', '#567154', '#8f9c65', '#d3c39b', '#f6e8ad'),
    'sun_travel': ('#354252', '#628b8b', '#a5c3a7', '#e5cf91', '#fff3c4'),
}
PALETTES = {k: Palette(dict(ink=v[0], shadow=v[1], body=v[2],
                            light=v[3], glow=v[4], dark='#171b22',
                            white='#fff9e9', accent='#d99064'))
            for k, v in RAMPS.items()}


def fill(f, shape):
    if isinstance(shape, np.ndarray):
        shape = gradient(shape, 14, 8, 82, 81)
    f.paint(shape, f.p.ramp('ink', 'shadow', 'body', 'light'), dither=.12)


def dark(f, shape):
    if isinstance(shape, np.ndarray):
        shape = gradient(shape, 14, 8, 82, 81)
    f.paint(shape, f.p.ramp('dark', 'ink', 'shadow'), dither=.08)


def glow(f, shape):
    if isinstance(shape, np.ndarray):
        shape = gradient(shape, 14, 8, 82, 81)
    f.paint(shape, f.p.ramp('shadow', 'glow', 'white'), dither=.05)


def line(f, a, b, c='body', w=3):
    f.line(a, b, 'ol', w + 2)
    f.line(a, b, c, w)


def eye(f, x, y):
    dark(f, ellipsoid(x, y, 3, 3))
    f.dots([(x - 1, y - 1)], 'white')


def hare(f, x, y, sway, hit):
    # Tall ears, spring hindquarters, tiny front paws and cotton tail.
    fill(f, ellipsoid(x - 7, y + 64, 25, 15))
    fill(f, ellipsoid(x + 19, y + 47, 13, 12))
    fill(f, polygon([(x + 9, y + 42), (x + 8, y + 7),
                     (x + 17, y + 4), (x + 19, y + 43)]))
    fill(f, polygon([(x + 19, y + 41), (x + 27, y + 5),
                     (x + 34, y + 7), (x + 29, y + 45)]))
    line(f, (x + 13, y + 13), (x + 14, y + 35), 'accent', 2)
    line(f, (x + 27, y + 14), (x + 24, y + 34), 'accent', 2)
    fill(f, ellipsoid(x - 26, y + 65, 7, 7))
    fill(f, ellipsoid(x - 14 + sway, y + 78, 13, 5))
    fill(f, ellipsoid(x + 19 + (4 if hit else 0), y + 76, 8, 5))
    glow(f, ellipsoid(x + 31, y + 54, 5, 4))
    eye(f, x + 24, y + 45)


def snail(f, x, y, sway, hit):
    # Low wet foot, a tall spiral shell, and two independent eye stalks.
    fill(f, ellipsoid(x, y + 75, 36, 8))
    fill(f, ellipsoid(x - 9, y + 52, 24, 25))
    dark(f, ellipsoid(x - 10, y + 51, 17, 17))
    fill(f, ellipsoid(x - 8, y + 51, 12, 13))
    dark(f, ellipsoid(x - 7, y + 51, 7, 8))
    glow(f, ellipsoid(x - 6, y + 50, 3, 4))
    line(f, (x + 20, y + 70), (x + 25, y + 31 - sway), 'body', 5)
    line(f, (x + 32, y + 68), (x + 35, y + 27 + sway), 'body', 5)
    fill(f, ellipsoid(x + 26, y + 30 - sway, 7, 7))
    fill(f, ellipsoid(x + 36, y + 27 + sway, 7, 7))
    eye(f, x + 28, y + 29 - sway)
    eye(f, x + 37, y + 26 + sway)
    if hit:
        line(f, (x + 22, y + 70), (x + 43, y + 74), 'glow', 3)


def fox(f, x, y, sway, hit):
    # Long low back, two pointed ears, cream bib and a huge flagged tail.
    fill(f, polygon([(x - 19, y + 58), (x - 43, y + 38),
                     (x - 38, y + 73), (x - 14, y + 75)]))
    glow(f, polygon([(x - 43, y + 38), (x - 37, y + 54),
                     (x - 40, y + 70), (x - 34, y + 66)]))
    fill(f, ellipsoid(x - 3, y + 60, 29, 14))
    for xx in (-16, 7, 17):
        line(f, (x + xx, y + 66), (x + xx + sway, y + 81), 'shadow', 5)
    fill(f, polygon([(x + 12, y + 50), (x + 19, y + 31),
                     (x + 25, y + 37), (x + 32, y + 30),
                     (x + 38, y + 46), (x + 31, y + 61)]))
    glow(f, polygon([(x + 23, y + 54), (x + 41, y + 53),
                     (x + 29, y + 62)]))
    eye(f, x + 30, y + 43)
    if hit:
        line(f, (x + 34, y + 55), (x + 43, y + 61), 'light', 2)


def badger(f, x, y, sway, hit):
    # Barrel body, unmistakable white face stripes and shovel claws.
    fill(f, ellipsoid(x - 4, y + 62, 32, 19))
    for xx in (-22, -5, 16, 25):
        line(f, (x + xx, y + 70), (x + xx + sway, y + 82), 'ink', 8)
        for j in range(3):
            line(f, (x + xx + sway + j * 2, y + 81),
                 (x + xx + sway + j * 2 + (4 if hit else 2), y + 84), 'light', 1)
    glow(f, ellipsoid(x + 24, y + 54, 19, 12))
    dark(f, polygon([(x + 21, y + 43), (x + 28, y + 47),
                     (x + 29, y + 60), (x + 19, y + 63)]))
    dark(f, polygon([(x + 33, y + 45), (x + 39, y + 48),
                     (x + 40, y + 58), (x + 30, y + 59)]))
    dark(f, ellipsoid(x + 42, y + 59, 5, 4))
    eye(f, x + 31, y + 52)


def bear(f, x, y, sway, hit):
    # A real bear's broad hump and snout, carrying a golden hive on its back.
    fill(f, ellipsoid(x - 5, y + 47, 30, 27))
    fill(f, ellipsoid(x + 19, y + 52, 17, 20))
    for side in (-1, 1):
        fill(f, ellipsoid(x + side * 21, y + 24, 8, 8))
        line(f, (x + side * 20, y + 65),
             (x + side * (22 + (7 if hit else sway)), y + 82), 'shadow', 11)
    glow(f, ellipsoid(x - 13, y + 22, 16, 19))
    for yy in (9, 20, 31):
        line(f, (x - 25, y + yy), (x - 2, y + yy), 'shadow', 3)
    fill(f, ellipsoid(x + 29, y + 57, 14, 10))
    glow(f, ellipsoid(x + 36, y + 60, 8, 5))
    dark(f, ellipsoid(x + 42, y + 60, 4, 4))
    eye(f, x + 24, y + 44)
    for j in range(3):
        fill(f, ellipsoid(x - 20 + j * 9, y + 39, 3, 5))


def wicker(f, x, y, sway, hit):
    # A wide T-shaped scarecrow: straw hat, crossbar arms, ragged coat.
    line(f, (x, y + 83), (x, y + 27), 'shadow', 7)
    line(f, (x - 41, y + 37), (x + 41, y + 37), 'shadow', 7)
    for side in (-1, 1):
        fill(f, polygon([(x + side * 19, y + 35),
                         (x + side * (41 if hit else 36), y + 28),
                         (x + side * 42, y + 51),
                         (x + side * 21, y + 48)]))
        for j in (0, 1, 2):
            line(f, (x + side * (33 + j * 3), y + 45),
                 (x + side * (37 + j * 3), y + 59), 'light', 2)
        line(f, (x + side * 11, y + 67),
             (x + side * (16 + sway), y + 84), 'shadow', 8)
    fill(f, polygon([(x - 23, y + 34), (x + 23, y + 34),
                     (x + 31, y + 77), (x + 5, y + 68),
                     (x - 25, y + 81)]))
    for j in (-1, 0, 1):
        line(f, (x + j * 9, y + 56), (x + j * 10 + 4, y + 77), 'light', 2)
    fill(f, ellipsoid(x, y + 23, 14, 13))
    dark(f, ellipsoid(x - 5, y + 23, 3, 3))
    dark(f, ellipsoid(x + 5, y + 23, 3, 3))
    fill(f, polygon([(x - 37, y + 12), (x + 38, y + 12),
                     (x + 17, y + 4), (x - 18, y + 4)]))
    fill(f, polygon([(x - 21, y + 7), (x - 12, y - 1),
                     (x + 14, y - 1), (x + 22, y + 7)]))


def villager(f, x, y, sway, hit, role):
    # Three distinct outfits: blue apron, green forester coat, yellow travel cape.
    for side in (-1, 1):
        line(f, (x + side * 8, y + 65),
             (x + side * (9 + sway), y + 84), 'shadow', 6)
    fill(f, polygon([(x - 17, y + 32), (x + 17, y + 32),
                     (x + 22, y + 76), (x - 23, y + 76)]))
    if role == 'miller':
        glow(f, polygon([(x - 11, y + 39), (x + 11, y + 39),
                         (x + 10, y + 74), (x - 12, y + 74)]))
        line(f, (x + 19, y + 42), (x + 24, y + 69), 'shadow', 5)
        line(f, (x - 20, y + 41), (x - 25, y + 66), 'shadow', 5)
    elif role == 'keeper':
        for side in (-1, 1):
            line(f, (x + side * 19, y + 40),
                 (x + side * (24 if hit else 22), y + 68), 'body', 7)
        line(f, (x + 27, y + 80), (x + 27, y + 16), 'light', 4)
        glow(f, ellipsoid(x + 27, y + 16, 7, 6))
    else:
        fill(f, ellipsoid(x - 20, y + 58, 10, 17))
        line(f, (x + 22, y + 72), (x + 22, y + 10), 'body', 4)
        fill(f, polygon([(x + 15, y + 18), (x + 41, y + 18),
                         (x + 41, y + 31), (x + 15, y + 31)]))
    fill(f, ellipsoid(x, y + 21, 12, 14))
    eye(f, x + 5, y + 21)
    if role == 'keeper':
        fill(f, polygon([(x - 16, y + 19), (x - 10, y + 3),
                         (x + 8, y + 3), (x + 16, y + 19)]))
    else:
        fill(f, polygon([(x - 26, y + 11), (x + 26, y + 11),
                         (x + 13, y + 6), (x - 13, y + 6)]))
        fill(f, polygon([(x - 16, y + 8), (x - 12, y - 1),
                         (x + 11, y - 1), (x + 16, y + 8)]))


DRAWERS = dict(meadowhare=hare, sunbacksnail=snail, brushfox=fox,
               spadebadger=badger, honeyjaw=bear, wickerwarden=wicker,
               sun_miller=lambda f,x,y,s,h: villager(f,x,y,s,h,'miller'),
               sun_keeper=lambda f,x,y,s,h: villager(f,x,y,s,h,'keeper'),
               sun_travel=lambda f,x,y,s,h: villager(f,x,y,s,h,'travel'))
m.KINDS = KINDS
m.PALETTES = PALETTES
m.DRAWERS = DRAWERS
m.ROOT = ROOT
m.ASSETS = ASSETS


def metadata(sprites):
    meta = m.metadata(sprites)
    meta['kinds'] = KINDS
    return meta


def preview():
    for kind in KINDS:
        m.grids(kind)
    sheet = Image.new('RGB', (9 * 205 + 12, 4 * 220 + 40), '#213040')
    d = ImageDraw.Draw(sheet)
    for col, kind in enumerate(KINDS):
        for row, (clip, n) in enumerate([('idle', 2), ('attack', 4),
                                         ('hurt', 0), ('die', 6)]):
            pose = m.draw(kind, clip, n).resize((192, 192),
                                                 Image.Resampling.NEAREST)
            sheet.paste(pose, (10 + col * 205, 28 + row * 220), pose)
            d.text((10 + col * 205, 8 + row * 220),
                   f'{kind} {clip}', fill='#f8e8bd')
    out = ROOT / 'test-results/sunward-cast.png'
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print(out)


def build():
    path = ASSETS / 'sunward.txt'
    if path.exists():
        raise SystemExit('Sunward sprites already exist; export preserves edits.')
    api = m._pf()
    sprites = {}
    for kind in KINDS:
        data = m.grids(kind)
        np.savez_compressed(ROOT / 'scripts' / f'sunward_{kind}_raw.npz',
                            **{clip: np.stack(rows) for clip, rows in data.items()})
        sid = api.create('valhallasc_sunward_' + kind + '_all', 96, 96, 34,
                         PALETTES[kind].hex, fps=10)
        frame = 0
        try:
            for clip, count in m.CLIPS:
                for grid in data[clip]:
                    api.draw_grid(sid, frame, 0, grid)
                    frame += 1
        except Exception:
            api.api('delete', {'sprite_id': sid})
            raise
        sprites[kind] = sid
        path.write_text(json.dumps(metadata(sprites), indent=2) + '\n')
        print(kind, sid, flush=True)


def export(verify=False):
    api = m._pf()
    path = ASSETS / 'sunward.txt'
    sprites = json.loads(path.read_text())['sprites']
    for kind in KINDS:
        sp, frames = api.load(sprites[kind])
        assert (sp['width'], sp['height'], len(frames)) == (96, 96, 34)
        out = Image.new('RGBA', (96 * 8, 96 * len(m.CLIPS)))
        offset = 0
        for row, (clip, count) in enumerate(m.CLIPS):
            for n in range(count):
                out.alpha_composite(Image.fromarray(api.to_rgba(
                    frames[offset + n][0], sp['palette']), 'RGBA'),
                    (n * 96, row * 96))
            offset += count
        target = ASSETS / f'sunward_{kind}.png'
        if verify:
            assert out.tobytes() == Image.open(target).convert('RGBA').tobytes(), kind
        else:
            out.save(target, optimize=True)
            print('exported', kind, flush=True)
    if verify:
        print('Nine PixelFlow sprites and 306 frames verified')
    else:
        path.write_text(json.dumps(metadata(sprites), indent=2) + '\n')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if cmd == 'preview':
        preview()
    elif cmd == 'build':
        build()
    elif cmd == 'export':
        export()
    elif cmd == 'verify':
        export(True)
    else:
        raise SystemExit('preview | build | export | verify')
