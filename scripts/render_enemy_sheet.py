#!/usr/bin/env python3
"""One share sheet of a zone's exported enemy atlases: python3 scripts/render_enemy_sheet.py <zone number> [...].

Writes test-results/enemy-sheets/Valhalla_<Zone>_Enemy_Sprites.png (zones 1-8 of the cel-shaded redraw)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/enemy-sheets'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ZONES = {
    1: ('crags', 'Emberfall Crags', 'Zone 1 · levels 5-10', '#3a2a2e', '#251a1d', '#ffb066', [
        ('wisp', 'Cinder Wisp', 0), ('spider', 'Magma Spider', 0), ('wraith', 'Ash Wraith', 0),
        ('golem', 'Basalt Golem', 0), ('cinderlord', 'The Cinderlord', 1)]),
    2: ('rime', 'Rimeveil Glacier', 'Zone 2 · levels 10-15', '#243a4c', '#16232f', '#9fe0ff', [
        ('crab', 'Rime Crab', 0), ('wolf', 'Frostfang Wolf', 0), ('yeti', 'Glacier Yeti', 0), ('wyrm', 'Rime Wyrm', 0)]),
    3: ('fen', 'Gloamfen', 'Zone 3 · levels 15-20', '#2a3a2e', '#18241d', '#b6e86a', [
        ('toad', 'Fen Toad', 0), ('croc', 'Mire Crocodile', 0), ('knight', 'Drowned Knight', 0),
        ('hydra', 'Mire Hydra', 0), ('gloomroot', 'Gloomroot Colossus', 1)]),
    5: ('vault', 'The Undervault', 'Zone 5 · dungeon, level 20', '#2e2e3e', '#1c1c28', '#c9b8ff', [
        ('thrall', 'Vault Thrall', 0), ('archer', 'Bone Archer', 0), ('acolyte', 'Hollow Acolyte', 0),
        ('gatewarden', 'Hrolf Bonegate', 1), ('choir', 'Valka, the Hollow Choir', 1),
        ('colossus', 'Ironwake, the Vault Colossus', 1), ('hollowking', 'Haldor, the Hollow King', 1)]),
    6: ('wyrd', 'Wyrdwood', 'Zone 6 · levels 20-30', '#2c3a2c', '#1a241a', '#ffd25a', [
        ('boar', 'Rotfang Boar', 0), ('crow', 'Gallowcrow', 0), ('troll', 'Mosshide Troll', 0), ('weaver', 'Wyrdweaver', 0),
        ('ram', 'Stormram', 0), ('oakhorn', 'Oakhorn', 1), ('hrungnir', 'Hrungnir', 1)]),
    7: ('sky', 'Bifrost Reach', 'Zone 7 · levels 30-35', '#2c3050', '#191c33', '#a8f0ff', [
        ('galehound', 'Galehound', 0), ('prismgolem', 'Prism Golem', 0), ('skyray', 'Skyray', 0),
        ('einherjar', 'Hollow Einherjar', 0), ('thunderroc', 'Thunderroc', 0)]),
    8: ('deep', "Rán's Deep", 'Zone 8 · levels 35-40', '#1c3a4a', '#10242e', '#9ffff0', [
        ('draugr', 'Drowned Draugr', 0), ('angler', 'Lantern Angler', 0), ('moray', 'Gnashing Moray', 0),
        ('siren', 'Siren', 0), ('shellback', 'Shellback', 0), ('kraken', 'The Kraken', 1),
        ('hvitserk', 'Hvitserk the Drowned', 1), ('ghostmaw', 'Ghostmaw', 1)]),
}
CARD_W, CARD_H, GAP = 408, 506, 18


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def frame(atlas, row, col, scale):
    tile = atlas.crop((col * 96, row * 96, (col + 1) * 96, (row + 1) * 96))
    return tile.resize((96 * scale, 96 * scale), Image.Resampling.NEAREST)


def sheet(zone):
    tag, title, sub, card_bg, band_bg, accent, cast = ZONES[zone]
    cols = min(len(cast), 4) if len(cast) in (4, 8) else min(len(cast), 5) if len(cast) <= 5 else 4
    rows = (len(cast) + cols - 1) // cols
    width = cols * CARD_W + (cols + 1) * GAP
    head = 110
    height = head + rows * (CARD_H + GAP) + 50
    canvas = Image.new('RGB', (width, height), band_bg)
    d = ImageDraw.Draw(canvas)
    d.text((GAP * 2, 18), title.upper(), font=font(40, True), fill=accent)
    d.text((GAP * 2 + 2, 70), f'{sub} · {len(cast)} enemies · cel-shaded · idle, walk, attack, hurt and die',
           font=font(19), fill='#d6d2e8')
    for i, (kind, name, boss) in enumerate(cast):
        x = GAP + (i % cols) * (CARD_W + GAP)
        top = head + (i // cols) * (CARD_H + GAP)
        d.rounded_rectangle((x, top, x + CARD_W, top + CARD_H), radius=18, fill=card_bg, outline=accent, width=3)
        d.text((x + 18, top + 14), name, font=font(22 if len(name) < 24 else 18, True), fill='#f7f5ff')
        d.text((x + 19, top + 46), 'BOSS / ELITE' if boss else 'ORDINARY', font=font(15, True),
               fill=accent if boss else '#a9a6c4')
        atlas = Image.open(ROOT / f'client/assets/{tag}_{kind}.png').convert('RGBA')
        big = frame(atlas, 0, 0, 3)
        canvas.paste(big, (x + (CARD_W - 288) // 2, top + 68), big)
        d.line((x + 18, top + 366, x + CARD_W - 18, top + 366), fill=accent, width=2)
        for j, (label, clip, col) in enumerate((('WALK', 1, 2), ('ATTACK', 2, 4), ('HURT', 3, 1), ('DIE', 4, 3))):
            px = x + 12 + j * 96
            pose = frame(atlas, clip, col, 1)
            canvas.paste(pose, (px, top + 376), pose)
            d.text((px + 6, top + 476), label, font=font(13, True), fill='#c9c6e2')
    d.text((GAP * 2, height - 34), '96 × 96 source frames · shared foot anchor · 34 frames per enemy',
           font=font(16), fill='#8c88a8')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"Valhalla_{title.replace(' ', '_').replace(chr(39), '').replace('á', 'a')}_Enemy_Sprites.png"
    canvas.save(path, optimize=True)
    print(path, canvas.size)


if __name__ == '__main__':
    for z in sys.argv[1:] or ZONES:
        sheet(int(z))
