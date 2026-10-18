#!/usr/bin/env python3
"""One share sheet from the exported Astralhollow, Prismwaste and Obsidian Orrery atlases (17 enemies)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/zones13-15-redraw/Valhalla_Astralhollow_Prismwaste_Orrery_Enemy_Sprites.png'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ZONES = [
    ('astral', 'ASTRALHOLLOW', 'Zone 13 · levels 40-45', '#10303a', '#0a2029', '#8fe8d0', [
        ('voidmoth', 'Void Moth', 'ORDINARY'), ('crystalwyrm', 'Crystalwyrm', 'ORDINARY'),
        ('orbitbeetle', 'Orbit Beetle', 'ORDINARY'), ('eclipsedryad', 'Eclipse Dryad', 'ORDINARY'),
        ('meteorgolem', 'Meteor Golem', 'ORDINARY')]),
    ('prism', 'THE PRISMWASTE', 'Zone 14 · levels 45-50', '#3a3248', '#262034', '#ffd9a0', [
        ('miragejackal', 'Mirage Jackal', 'ORDINARY'), ('shardscarab', 'Shard Scarab', 'ORDINARY'),
        ('glassharrier', 'Glass Harrier', 'ORDINARY'), ('prismsentinel', 'Prism Sentinel', 'ORDINARY'),
        ('mirrorqueen', 'The Mirror Queen', 'BOSS'), ('sunshard', 'The Sunshard', 'BOSS')]),
    ('orrery', 'THE OBSIDIAN ORRERY', 'Zone 15 · levels 50-55', '#2c2a3c', '#1b1a29', '#f0c878', [
        ('bronzemantis', 'Bronze Mantis', 'ORDINARY'), ('gearling', 'Gearling', 'ORDINARY'),
        ('orbitseer', 'Orbit Seer', 'ORDINARY'), ('chronoguard', 'Chronoguard', 'ORDINARY'),
        ('pendulummatron', 'The Pendulum Matron', 'BOSS'), ('epochengine', 'The Epoch Engine', 'BOSS')]),
]
CARD_W, CARD_H, GAP, COLS = 408, 506, 18, 6
HEAD = 96


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def frame(atlas, row, col, scale):
    tile = atlas.crop((col * 96, row * 96, (col + 1) * 96, (row + 1) * 96))
    return tile.resize((96 * scale, 96 * scale), Image.Resampling.NEAREST)


def main():
    width = COLS * CARD_W + (COLS + 1) * GAP
    band = HEAD + CARD_H + GAP
    height = 120 + len(ZONES) * band + 40
    canvas = Image.new('RGB', (width, height), '#14141e')
    d = ImageDraw.Draw(canvas)
    d.text((GAP * 2, 24), 'ENEMY REDRAW · ZONES 13-15', font=font(48, True), fill='#f4f1ff')
    d.text((GAP * 2 + 2, 84), '17 enemies · cel-shaded · idle, walk, attack, hurt and die · editable in PixelFlow',
           font=font(20), fill='#b9b4d4')
    y = 130
    for tag, title, sub, card_bg, band_bg, accent, cast in ZONES:
        d.rectangle((0, y, width, y + HEAD + CARD_H + GAP - 4), fill=band_bg)
        d.text((GAP * 2, y + 16), title, font=font(34, True), fill=accent)
        d.text((GAP * 2 + 2, y + 58), sub, font=font(19), fill='#d6d2e8')
        for i, (kind, name, rank) in enumerate(cast):
            x = GAP + i * (CARD_W + GAP)
            top = y + HEAD
            d.rounded_rectangle((x, top, x + CARD_W, top + CARD_H), radius=18, fill=card_bg, outline=accent, width=3)
            d.text((x + 18, top + 14), name, font=font(22, True), fill='#f7f5ff')
            d.text((x + 19, top + 46), rank, font=font(15, True), fill=accent if rank == 'BOSS' else '#a9a6c4')
            atlas = Image.open(ROOT / f'client/assets/{tag}_{kind}.png').convert('RGBA')
            big = frame(atlas, 0, 0, 3)
            canvas.paste(big, (x + (CARD_W - 288) // 2, top + 68), big)
            d.line((x + 18, top + 366, x + CARD_W - 18, top + 366), fill=accent, width=2)
            for j, (label, clip, col) in enumerate((('WALK', 1, 2), ('ATTACK', 2, 4), ('HURT', 3, 1), ('DIE', 4, 3))):
                px = x + 12 + j * 96
                pose = frame(atlas, clip, col, 1)
                canvas.paste(pose, (px, top + 376), pose)
                d.text((px + 6, top + 476), label, font=font(13, True), fill='#c9c6e2')
        y += band
    d.text((GAP * 2, height - 32), '96 × 96 source frames · shared foot anchor · 34 frames per enemy',
           font=font(16), fill='#8c88a8')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, optimize=True)
    print(OUT, canvas.size)


if __name__ == '__main__':
    main()
