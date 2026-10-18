#!/usr/bin/env python3
"""Make one share sheet from the seven exported Grand Nave atlases."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/nave-redraw/Valhalla_Grand_Nave_Enemy_Sprites.png'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CAST = [
    ('abysszealot', 'Abyssal Zealot', 'ORDINARY', '#b57bff'),
    ('tidetemplar', 'Drowned Templar', 'ORDINARY', '#69dacc'),
    ('tidecantor', 'Bound Cantor', 'ORDINARY', '#70d7f4'),
    ('chainmarshal', 'Vargast · Marshal of Chains', 'BOSS', '#98a6c0'),
    ('starseraph', 'Astrael · Fallen Tide Seraph', 'BOSS', '#a8a0f0'),
    ('tidejudicator', 'The Blind Tide Judicator', 'BOSS', '#e0c46a'),
    ('hierophant', 'Vael · Heart of the Tide', 'BOSS', '#9fe4ff'),
]


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def frame(atlas, row, col, side):
    tile = atlas.crop((col*96, row*96, (col+1)*96, (row+1)*96))
    return tile.resize((side, side), Image.Resampling.NEAREST)


def main():
    canvas = Image.new('RGB', (1856, 1700), '#132d37')
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, 1856, 142), fill='#0b2731')
    d.text((55, 27), 'THE GRAND NAVE', font=font(57, True), fill='#e6fff3')
    d.text((58, 96), 'Seven enemies · cel-shaded · idle, walk, attack, hurt and die · editable in PixelFlow',
           font=font(20), fill='#a4d9d5')
    for i, (kind, name, rank, accent) in enumerate(CAST):
        col, row = i % 4, i // 4
        x, y = 40 + col*454, 171 + row*746
        d.rounded_rectangle((x, y, x+432, y+721), radius=19,
                            fill='#203b45', outline=accent, width=3)
        d.text((x+18, y+16), name, font=font(22, True), fill='#f2fbf7')
        d.text((x+19, y+49), rank, font=font(16, True), fill=accent)
        atlas = Image.open(ROOT / f'client/assets/cathedral_{kind}.png').convert('RGBA')
        big = frame(atlas, 0, 0, 288)
        canvas.paste(big, (x+72, y+78), big)
        d.line((x+18, y+380, x+414, y+380), fill=accent, width=2)
        samples = [('WALK', 1, 2), ('ATTACK', 2, 4), ('HURT', 3, 1), ('DIE', 4, 6)]
        for j, (label, clip, index) in enumerate(samples):
            sx = x+22+(j%2)*204
            sy = y+395+(j//2)*150
            pose = frame(atlas, clip, index, 132)
            canvas.paste(pose, (sx+35, sy), pose)
            d.text((sx+4, sy+127), label, font=font(15, True), fill='#b7e3d7')
    d.text((49, 1660), '96 × 96 source frames · shared foot anchor · 34 frames per enemy',
           font=font(18), fill='#b5d5d1')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
