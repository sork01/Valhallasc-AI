#!/usr/bin/env python3
"""Build, export or verify the eight Mothkin head attachments in PixelFlow."""

import argparse
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / 'client/assets/mothkin.png'
NAME = 'valhallasc_mothkin_antennae_and_markings'
SIZE = 48
ANCHOR = (24, 36)
PALETTE = [
    '#00000000', '#23172f', '#664b75', '#a285aa', '#e6cce0',
    '#fff0df', '#f0dfd0', '#cfb4d5',
]


def artwork(direction):
    """Two feathered antennae and the visible cheek markings in this facing."""
    angle = direction * math.pi / 4
    facing, turn = math.cos(angle), -math.sin(angle)
    antennae = Image.new('L', (SIZE, SIZE))
    draw = ImageDraw.Draw(antennae)
    for side in sorted((-1, 1), key=lambda side: side * turn):
        # The far comb contracts into profile and sits behind the near comb.
        near = side * turn
        root = side * (5.2 * abs(facing) + 1.6) + 3.4 * turn
        spread = .66 + .34 * abs(facing) + .17 * near

        def point(x, y):
            return (round(ANCHOR[0] + root + side * x * spread),
                    round(ANCHOR[1] + y + (1 - near) * .9) + 1)

        def plate(points, tone, outline=None):
            draw.polygon([point(x, y) for x, y in points], tone, outline=outline)

        plate([(-1.3, -10), (0, -16), (2, -22), (5, -27), (7, -28),
               (5, -22), (3, -16), (1, -10)], 2, 1)
        plate([(1, -17), (0, -21), (1, -26), (3, -25), (3, -30),
               (6, -29), (7, -34), (10, -34), (10, -30), (14, -31),
               (12, -27), (14, -27), (11, -23), (12, -22), (7, -19),
               (6, -17), (3, -15)], 3 if near < -.5 else 4, 1)
        draw.line([point(2, -16), point(5, -23), point(9, -32)], 2, width=1)
        for start, end in [((4, -21), (10, -24)), ((5, -24), (11, -27)), ((7, -27), (11, -29))]:
            draw.line([point(*start), point(*end)], 3, width=1)
        draw.line([point(2, -19), point(2, -24)], 5 if near >= -.5 else 4)

    markings = Image.new('L', (SIZE, SIZE))
    draw = ImageDraw.Draw(markings)
    for side in (-1, 1):
        if facing < -.2 or side * turn < -.6:
            continue
        x, y = ANCHOR[0] + round(side * 5.8 + turn * 1.4), ANCHOR[1] + 3
        draw.line([(x, y), (x + 3 * side, y - 2)], 6, width=2)
        draw.line([(x + side, y + 3), (x + 3 * side, y + 2)], 7, width=1)
        draw.point((x - side, y + 2), 5)
    return antennae, markings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'export', 'verify'])
    args = parser.parse_args()
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf

    sprite_id = pf.ids(NAME).get(NAME)
    if args.action == 'build' and sprite_id is None:
        operations = [
            dict(op='grid', frame=direction, layer=layer, x=0, y=0,
                 rows=np.asarray(image).tolist())
            for direction in range(8)
            for layer, image in enumerate(artwork(direction))
        ]
        sprite_id = pf.create(NAME, SIZE, SIZE, 8, PALETTE, layers=2, layer_ops=operations)
    if sprite_id is None:
        parser.error(f'Run build first to create {NAME}.')
    sprite, frames = pf.load(sprite_id)
    assert (sprite['width'], sprite['height'], len(frames)) == (SIZE, SIZE, 8)
    atlas = Image.new('RGBA', (SIZE * 8, SIZE * 2))
    for direction, layers in enumerate(frames):
        assert len(layers) == 2 and np.any(layers[0]), direction
        for layer, grid in enumerate(layers):
            image = Image.fromarray(pf.to_rgba(grid, sprite['palette']))
            atlas.paste(image, (direction * SIZE, layer * SIZE))
    if args.action == 'verify':
        with Image.open(ATLAS) as exported:
            assert np.array_equal(np.asarray(atlas), np.asarray(exported.convert('RGBA')))
    else:
        atlas.save(ATLAS, optimize=True)
    print(f'{args.action}: {sprite_id}, eight facings and two layers')


if __name__ == '__main__':
    main()
