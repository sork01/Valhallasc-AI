#!/usr/bin/env python3
"""Make FileDrop cards from the live Sunward captures and exported PixelFlow sprites."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/sunward-share'
OUT.mkdir(parents=True, exist_ok=True)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def label(draw, xy, value, size, fill='#eaf2df', bold=False):
    draw.text(xy, value, font=ImageFont.truetype(BOLD if bold else FONT, size), fill=fill)


def cover(path, size):
    image = Image.open(path).convert('RGB')
    return ImageOps.fit(image, size, Image.Resampling.LANCZOS)


def chart(image, zone):
    draw = ImageDraw.Draw(image)
    x0, y0, scale = 72, 235, 4.6
    draw.rounded_rectangle((55, 213, 764, 958), radius=24, fill='#e7e0bb', outline='#b4bb82', width=5)
    def pt(x, y):
        return (x0 + x*scale, y0 + y*scale)
    for obj in zone['objects']:
        x, y = pt(obj['x'], obj['y'])
        kind = obj['kind']
        if kind == 'water':
            draw.ellipse((x-10, y-10, x+10, y+10), fill='#63b6c4')
        elif kind in ('oak_tree', 'birch_tree', 'willow_tree', 'apple_tree'):
            color = {'oak_tree':'#3d793d','birch_tree':'#a0ba68',
                     'willow_tree':'#618e65','apple_tree':'#82a944'}[kind]
            r = 5 if kind == 'oak_tree' else 3.8
            draw.ellipse((x-r, y-r, x+r, y+r), fill=color)
        elif kind == 'vale_cottage':
            draw.rectangle((x-8, y-8, x+8, y+8), fill='#ad674b', outline='#f7e3ad', width=2)
        elif kind == 'watermill':
            draw.rectangle((x-11, y-11, x+11, y+11), fill='#985a40', outline='#f7e3ad', width=2)
        elif kind == 'elder_hollow_gate':
            draw.ellipse((x-24, y-24, x+24, y+24), fill='#27593e', outline='#f3d98e', width=5)
    for path in zone['paths']:
        line = [pt(x, y) for x, y in path]
        draw.line(line, fill='#9b875e', width=23, joint='curve')
        draw.line(line, fill='#ead7a2', width=16, joint='curve')
    for obj in zone['objects']:
        if obj['kind'] == 'stone_bridge':
            x, y = pt(obj['x'], obj['y'])
            draw.rounded_rectangle((x-11, y-25, x+11, y+25), radius=4,
                                   fill='#d2bd95', outline='#756d55', width=3)
    for enemy in zone['slimes']:
        if enemy['kind'] in ('honeyjaw', 'wickerwarden'):
            x, y = pt(enemy['x'], enemy['y'])
            draw.ellipse((x-12, y-12, x+12, y+12), fill='#c2723d' if enemy['kind']=='honeyjaw' else '#9c6f3f', outline='#fff5d4', width=3)
    label(draw, (80, 880), 'MILLBRIDGE', 23, '#59482e', True)
    label(draw, (157, 362), 'OLD HONEYJAW', 17, '#684b30', True)
    label(draw, (492, 403), 'ELDER HOLLOW', 18, '#294a35', True)
    label(draw, (510, 490), 'WICKER WARDEN', 17, '#694c2e', True)


def zone_card(camp, gate):
    area = json.loads((ROOT/'world/map.txt').read_text())['zones'][19]
    image = Image.new('RGB', (1920, 1220), '#f3edd5')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1920, 170), fill='#244d3d')
    label(draw, (66, 24), 'SUNWARD VALE', 70, '#fff2c8', True)
    label(draw, (70, 110), 'LEVELS 65–70  ·  MILLBRIDGE  ·  TWO RIVER CROSSINGS  ·  THE ELDER HOLLOW', 22, '#d9e7c6')
    chart(image, area)
    draw = ImageDraw.Draw(image)
    gx, gy, gw, gh = 810, 213, 1040, 515
    image.paste(cover(gate, (gw, gh)), (gx, gy))
    draw.rectangle((gx, gy+gh-59, gx+gw, gy+gh), fill='#244d3d')
    label(draw, (gx+26, gy+gh-50), 'THE ELDER HOLLOW  ·  SEALED INSTANCE ENTRANCE', 23, '#fff2c8', True)
    cx, cy, cw, ch = 810, 760, 1040, 355
    image.paste(cover(camp, (cw, ch)), (cx, cy))
    draw.rectangle((cx, cy+ch-56, cx+cw, cy+ch), fill='#244d3d')
    label(draw, (cx+26, cy+ch-48), 'MILLBRIDGE  ·  QUESTS, SUPPLIES AND SPARK TRAVEL', 22, '#fff2c8', True)
    label(draw, (70, 998), 'Oakwood, birches, an apple orchard and a living river.', 24, '#4d6742', True)
    label(draw, (70, 1044), 'Two outdoor elites: Old Honeyjaw and the Wicker Warden.', 21, '#647057')
    label(draw, (70, 1162), 'Real game captures and original PixelFlow character art', 18, '#5f7058')
    target = OUT/'Valhalla_Sunward_Zone_Overview.png'
    image.save(target, optimize=True)
    print(target)


def cast_card():
    names = [('meadowhare','Meadow Hare','65'), ('sunbacksnail','Sunback Snail','66'),
             ('brushfox','Brush Fox','67'), ('spadebadger','Spadeclaw Badger','68'),
             ('honeyjaw','Old Honeyjaw','69 · ELITE'),
             ('wickerwarden','Wicker Warden','70 · ELITE')]
    image = Image.new('RGB', (1880, 760), '#e7e9ca')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1880, 135), fill='#244d3d')
    label(draw, (54, 17), 'THE CREATURES OF SUNWARD', 53, '#fff2c8', True)
    label(draw, (58, 92), 'Six original PixelFlow designs  ·  34 frames each  ·  idle and attack poses', 21, '#d5e6c8')
    for i, (kind, name, level) in enumerate(names):
        x = 35+i*308
        draw.rounded_rectangle((x, 164, x+291, 695), radius=18, fill='#fff8dc', outline='#7e9c65', width=3)
        atlas = Image.open(ROOT/f'client/assets/sunward_{kind}.png').convert('RGBA')
        idle = atlas.crop((0, 0, 96, 96)).resize((255, 255), Image.Resampling.NEAREST)
        attack = atlas.crop((4*96, 2*96, 5*96, 3*96)).resize((195, 195), Image.Resampling.NEAREST)
        image.paste(idle, (x+18, 204), idle)
        image.paste(attack, (x+49, 423), attack)
        label(draw, (x+17, 616), name, 19, '#315039', True)
        label(draw, (x+18, 650), 'LEVEL '+level, 17, '#ad703a' if 'ELITE' in level else '#5d8756', True)
    target = OUT/'Valhalla_Sunward_Monsters.png'
    image.save(target, optimize=True)
    print(target)


if __name__ == '__main__':
    zone_card(Path(sys.argv[1]), Path(sys.argv[2]))
    cast_card()
