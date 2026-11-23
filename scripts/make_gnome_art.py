#!/usr/bin/env python3
"""Build, export or verify the Obsidian Orrery Gnome's brasswork in PixelFlow."""

import math

from PIL import Image, ImageDraw

from race_art import ANCHOR, SIZE, export_race_atlas

NAME = 'valhallasc_gnome_orrery_brasswork'
PALETTE = [
    '#00000000', '#251b2d', '#594033', '#a16d39', '#d5a653',
    '#f5c979', '#a4d4ba', '#9f6349', '#eab666',
]


def artwork(direction):
    angle = direction * math.pi / 4
    front, turn = math.cos(angle), -math.sin(angle)
    brasswork = Image.new('L', (SIZE, SIZE))
    draw = ImageDraw.Draw(brasswork)
    for side in sorted((-1, 1), key=lambda side: side * turn):
        near = side * turn
        x = ANCHOR[0] + round(side * (12.8 + 2.8 * abs(front)) + 1.5 * turn)
        y = ANCHOR[1] - 2 - round(near * 1.5)
        width = .8 + .2 * near
        # The small brass ratchet is worn against a dark leather temple band.
        draw.line([(x - side * 9, y - 7), (x - side * 1, y - 5), (x, y)], 1, width=3)
        draw.line([(x - side * 8, y - 7), (x - side * 1, y - 5)], 3, width=1)
        teeth = []
        for tooth in range(8):
            for step, radius in [(0, 5.8), (.35, 5.8), (.35, 4.5), (1, 4.5)]:
                pitch = (tooth + step) * math.tau / 8
                teeth.append((round(x + width * radius * math.cos(pitch)),
                              round(y + radius * math.sin(pitch))))
        draw.polygon(teeth, 3 if near < -.55 else 4, outline=1)
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=2, outline=3)
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=6 if near > -.55 else 3)
        draw.point((x - 2, y - 4), 5)
    marks = Image.new('L', (SIZE, SIZE))
    draw = ImageDraw.Draw(marks)
    if front > .2:
        for side in (-1, 1):
            x = ANCHOR[0] + round(5 * side + 2 * turn)
            y = ANCHOR[1] + 3
            draw.line([(x + 2 * side, y - 1), (x + side, y + 1), (x, y + 1)], 8)
            draw.point((x, y + 2), 7)
    return brasswork, marks


if __name__ == '__main__':
    export_race_atlas('gnome', NAME, PALETTE, artwork)
