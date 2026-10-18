#!/usr/bin/env python3
"""One share sheet from the exported Moonspore, Moonwell, Stormglass, Sunward and Ribbonwild atlases (31 enemies)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/zones16-21-redraw/Valhalla_Moonspore_Moonwell_Stormglass_Sunward_Ribbonwild_Enemy_Sprites.png'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ZONES = [
    ('moonspore', 'THE MOONSPORE CANOPY', 'Zone 16 · levels 55-60', '#1c3a34', '#12251f', '#b8ffae', [
        ('glowcapgrazer', 'Glowcap Grazer', 'ORDINARY'), ('silkwing', 'Silkwing', 'ORDINARY'),
        ('rootlurker', 'Rootlurker', 'ORDINARY'), ('lanternwraith', 'Lantern Wraith', 'ORDINARY'),
        ('mireheart', 'The Mireheart', 'BOSS'), ('silverwidow', 'The Silver Widow', 'BOSS'),
        ('nightbloom', 'The Nightbloom', 'BOSS')]),
    ('moonwell', 'THE MOONWELL', 'Zone 18 · level 60 instance', '#1c3a52', '#12263a', '#9af2d7', [
        ('dew_moth', 'Dew Moth', 'ORDINARY'), ('lumen_eel', 'Lumen Eel', 'ORDINARY'),
        ('rootbell', 'Rootbell', 'ORDINARY'), ('tideglass_heron', 'The Tideglass Heron', 'BOSS'),
        ('hourpetal_stag', 'The Hourpetal Stag', 'BOSS'), ('moonskein_weaver', 'The Moonskein Weaver', 'BOSS'),
        ('moonwell_echo', 'The Moonwell Echo', 'BOSS')]),
    ('stormglass', 'THE STORMGLASS SHORE', 'Zone 19 · levels 60-65', '#1e3250', '#121f36', '#9cefff', [
        ('saltclaw', 'Saltclaw', 'ORDINARY'), ('stormgull', 'Stormgull', 'ORDINARY'),
        ('glassray', 'Glassray', 'ORDINARY'), ('breakersentinel', 'Breaker Sentinel', 'ORDINARY'),
        ('maelstromheart', 'The Maelstrom Heart', 'BOSS')]),
    ('sunward', 'SUNWARD VALE', 'Zone 20 · levels 65-70', '#3a3a24', '#25251a', '#ffe497', [
        ('meadowhare', 'Meadow Hare', 'ORDINARY'), ('sunbacksnail', 'Sunback Snail', 'ORDINARY'),
        ('brushfox', 'Brush Fox', 'ORDINARY'), ('spadebadger', 'Spadeclaw Badger', 'ORDINARY'),
        ('honeyjaw', 'Old Honeyjaw', 'BOSS'), ('wickerwarden', 'The Wicker Warden', 'BOSS')]),
    ('ribbonwild', 'THE RIBBONWILD', 'Zone 21 · levels 70-75', '#3a2c4a', '#251b34', '#ffc4e8', [
        ('ribbongecko', 'Ribbon Gecko', 'ORDINARY'), ('balloonbeetle', 'Balloon Beetle', 'ORDINARY'),
        ('paintedmacaw', 'Painted Macaw', 'ORDINARY'), ('jesterling', 'Jesterling', 'ORDINARY'),
        ('paradegryphon', 'The Parade Gryphon', 'BOSS'), ('maskcolossus', 'The Masquerade Colossus', 'BOSS')]),
]
CARD_W, CARD_H, GAP, COLS = 408, 506, 18, 7
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
    d.text((GAP * 2, 24), 'ENEMY REDRAW · ZONES 16-21', font=font(48, True), fill='#f4f1ff')
    d.text((GAP * 2 + 2, 84), '31 enemies · cel-shaded · idle, walk, attack, hurt and die · editable in PixelFlow',
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
            path = ROOT / f'client/assets/{tag}_{kind}.png'
            atlas = Image.open(path if path.exists() else ROOT / f'client/assets/{kind}.png').convert('RGBA')
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
