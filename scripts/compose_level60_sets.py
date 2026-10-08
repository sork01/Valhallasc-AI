#!/usr/bin/env python3
"""Make FileDrop boards from real level-60 client compositor frames."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / 'test-results/moonspore-level60-sets'
CLASSES = ['warrior', 'mage', 'assassin', 'priest', 'hunter']
RARITIES = [('gray', 'SPOREWORN', '#aeb5bd'), ('green', 'MOONWOVEN', '#77dfab'),
            ('blue', 'NIGHTBLOOM', '#8db7ff'), ('purple', 'MOONCROWNED', '#d7adff')]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
W, H, GAP, PAD, HEADER = 276, 322, 10, 22, 110


def board(classes, name):
    width = PAD * 2 + 4 * W + 3 * GAP
    height = HEADER + len(classes) * (H + GAP) + PAD
    image = Image.new('RGB', (width, height), '#0b1823')
    draw = ImageDraw.Draw(image)
    title = 'LEVEL 60  /  THE MOONSPORE CANOPY'
    draw.text((PAD, 19), title, fill='#e5f6f1', font=ImageFont.truetype(BOLD, 28))
    subtitle = f'{len(classes)} {"class" if len(classes) == 1 else "classes"}  ·  four complete gear sets  ·  real in-game sprites'
    draw.text((PAD, 62), subtitle,
              fill='#9db9bb', font=ImageFont.truetype(FONT, 16))
    for row, cls in enumerate(classes):
        y = HEADER + row * (H + GAP)
        for col, (rarity, label, accent) in enumerate(RARITIES):
            x = PAD + col * (W + GAP)
            draw.rounded_rectangle((x, y, x + W - 1, y + H - 1), radius=13,
                                   fill='#152937', outline='#315260', width=2)
            draw.rounded_rectangle((x + 10, y + 10, x + W - 11, y + 49), radius=7,
                                   fill='#213c4a')
            draw.text((x + 18, y + 17), cls.upper(), fill='#e7f6f2',
                      font=ImageFont.truetype(BOLD, 17))
            label_font = ImageFont.truetype(BOLD, 11)
            label_box = draw.textbbox((0, 0), label, font=label_font)
            draw.text((x + W - 18 - (label_box[2] - label_box[0]), y + 22), label,
                      fill=accent, font=label_font)
            draw.ellipse((x + 56, y + H - 43, x + W - 56, y + H - 30), fill='#244a52')
            sprite = Image.open(FRAMES / f'{cls}-{rarity}.png').convert('RGBA')
            bounds = sprite.getbbox()
            if bounds is None:
                raise ValueError(f'Empty sprite: {cls} {rarity}')
            sprite = sprite.crop(bounds)
            scale = min(2.55, 226 / sprite.height, 240 / sprite.width)
            sprite = sprite.resize((round(sprite.width * scale), round(sprite.height * scale)), Image.Resampling.NEAREST)
            px = x + (W - sprite.width) // 2
            py = y + 56 + (226 - sprite.height)
            image.paste(sprite, (px, py), sprite)
            draw.text((x + 16, y + H - 26), f'Level 60  ·  {rarity.upper()} SET',
                      fill='#a4bec3', font=ImageFont.truetype(FONT, 12))
    target = FRAMES / name
    image.save(target, optimize=True)
    print(f'{target} ({target.stat().st_size:,} bytes)')


if __name__ == '__main__':
    board(CLASSES, 'Valhallasc_Level_60_All_Classes_Sets.png')
    for cls in CLASSES:
        board([cls], f'Valhallasc_Level_60_{cls.title()}_Sets.png')
