#!/usr/bin/env python3
"""Build, export or verify the Tidekin's eight fin and gill drawings in PixelFlow."""

import math

from PIL import Image, ImageDraw

from race_art import ANCHOR, SIZE, export_race_atlas

NAME = 'valhallasc_tidekin_fins_and_gills'
PALETTE = [
    '#00000000', '#163035', '#285659', '#38767a', '#539992',
    '#81b8a8', '#a9d6bd', '#dfefe4', '#9ad1bc', '#f1f3df',
]


def artwork(direction):
    angle = direction * math.pi / 4
    front, turn = math.cos(angle), -math.sin(angle)
    fins = Image.new('L', (SIZE, SIZE))
    draw = ImageDraw.Draw(fins)
    for side in sorted((-1, 1), key=lambda side: side * turn):
        near = side * turn
        root = side * (7.7 + abs(front) * 1.7) + 2.5 * turn
        spread = .63 + abs(front) * .34 + near * .15

        def point(x, y):
            return (round(ANCHOR[0] + root + side * x * spread),
                    round(ANCHOR[1] + y - near * 1.3))

        def plate(points, ink, outline=None):
            draw.polygon([point(x, y) for x, y in points], ink, outline=outline)

        # A hooked upper ray and two torn-looking lower lobes give the ear its silhouette.
        plate([(-2, -1), (1, -7), (6, -9), (12, -14), (11, -9),
               (14, -10), (12, -5), (13, -4), (9, 0), (8, 4),
               (4, 3), (1, 6), (-2, 3)], 3 if near < -.3 else 4, 1)
        plate([(1, 1), (4, -5), (10, -10), (8, -5), (12, -7),
               (9, -3), (11, -3), (7, 0), (7, 3), (4, 2), (2, 4)],
              4 if near < -.3 else 5)
        for ray in [(10, -10), (11, -6), (10, -3), (6, 2)]:
            draw.line([point(1, 2), point(*ray)], 3, width=1)
        draw.line([point(4, -5), point(9, -9), point(11, -11)], 6)
        draw.point(point(8, -8), 7 if near >= -.3 else 6)

    gills = Image.new('L', (SIZE, SIZE))
    draw = ImageDraw.Draw(gills)
    for side in (-1, 1):
        if front < -.2 or side * turn < -.55:
            continue
        x = ANCHOR[0] + round(4.5 * side + 2 * turn)
        y = ANCHOR[1] + 2
        # Three short, curved slits step down the jaw.
        draw.line([(x + side, y + 1), (x + 3 * side, y)], 9, width=1)
        draw.line([(x, y + 4), (x + 2 * side, y + 3), (x + 3 * side, y + 2)], 7, width=1)
        draw.line([(x - side, y + 6), (x + side, y + 5)], 8, width=1)
    return fins, gills


if __name__ == '__main__':
    export_race_atlas('tidekin', NAME, PALETTE, artwork)
