"""Seven articulated Solar Crucible creatures (six dungeon encounters + Cinder of the Crucible boss helper) in y-up coordinates."""
import math
from astral_slime_redraw import (
    OUTLINE, WHITE, BONE, PEARL, GOLD, GREEN, LEAF, TEAL,
    AZURE, SLATE, PURPLE, VIOLET, CRIMSON, MAROON, BROWN, OLIVE, PINK, CORAL, AMBER,
)


def emberling(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solar_emberling', clip, n, (0, 10), -0.34)
    cy = 24 + b - 11 * d
    hx = 3 + 18 * s - 7 * w
    hy = 30 + b + 4 * w - 2 * s - 13 * d

    # Two planted basalt-cinder legs on the ground row.
    for i, x in enumerate((-10, 10)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 4 * d, 11 + lift), (x + step - 7 * d, 3 + lift)], BROWN, 5)
        r.ball(x + step - 7 * d, 3 + lift, 6.5, 3, SLATE)

    # Blazing three-pronged solar flame crown atop the coal imp (gutters out on death).
    if d < 0.65:
        flame_s = 1 - 0.85 * d
        for k, (dx, fh, ramp) in enumerate(((-9, 18, CORAL), (0, 25, GOLD), (9, 17, AMBER))):
            sway = math.sin(ph + k) * 2.5 + 4 * s - 3 * w
            top_y = hy + 12 + (fh + 5 * w + 4 * s) * flame_s
            r.poly([
                (hx + dx - 6, hy + 9),
                (hx + dx + sway, top_y),
                (hx + dx + 6, hy + 9),
            ], ramp[3], OUTLINE)
            r.poly([
                (hx + dx - 3, hy + 10),
                (hx + dx + sway * 0.7, hy + 9 + (top_y - (hy + 9)) * 0.65),
                (hx + dx + 3, hy + 10),
            ], WHITE if ramp is GOLD else GOLD[-1])

    # Cracked basalt-and-cinder coal body: splits into two cooling cinder halves on death.
    if d < 0.35:
        r.ball(hx, hy, 17, 16, BROWN)
        r.ball(hx - 2, hy + 2, 13, 12, SLATE)
        r.ball(hx + 1, hy + 1, 9, 8, CRIMSON)
        if d < 0.65:
            r.line([(hx - 10, hy + 6), (hx, hy - 1), (hx + 10, hy + 5)], GOLD[-1], 2)
    else:
        sep = (d - 0.25) * 13
        for side in (-1, 1):
            cx_h = hx + side * sep
            cy_h = hy - 3 * d
            r.ball(cx_h, cy_h, 12, 11 * (1 - 0.28 * d), BROWN, side * 0.38 * d)
            r.ball(cx_h - side * 2, cy_h + 1, 8, 7 * (1 - 0.28 * d), SLATE, side * 0.38 * d)
            r.poly([
                (cx_h - side * 2, cy_h + 8 * (1 - 0.28 * d)),
                (cx_h + side * 5, cy_h + 1),
                (cx_h + side * 3, cy_h - 7 * (1 - 0.28 * d)),
                (cx_h - side * 2, cy_h - 5 * (1 - 0.28 * d)),
            ], OUTLINE, OUTLINE)

    # Two clawed cinder arms; near arm hurls a searing solar fireball on strike.
    r.limb([(hx - 12, hy + 2), (hx - 19 - 4 * w, hy - 2 - 5 * d), (hx - 23 - 6 * d, hy - 6 - 6 * d)], BROWN, 4)
    hand = (hx + 14 + 14 * s - 7 * w, hy + 2 + 10 * w - 4 * s - 6 * d)
    r.limb([(hx + 11, hy + 2), (hx + 15 + 5 * s, hy - 1), hand], BROWN, 4)
    r.ball(hand[0], hand[1], 4.5, 4, CRIMSON if d < 0.65 else SLATE)

    if (s > 0.05 or w > 0.2) and d < 0.65:
        reach = hx + 18 + 24 * s - 6 * w
        r.poly([(hand[0], hand[1] + 5), (reach + 8, hand[1] + 1), (hand[0], hand[1] - 5)], CORAL[3], OUTLINE)
        r.ball(reach, hand[1] + 1, 6, 5, GOLD)
        r.ellipse(reach + 1, hand[1] + 1, 3, 2.5, WHITE)

    # Scowling slanted diamond-ember eyes and fanged furnace-grate maw.
    if d < 0.65:
        for side, dx in ((-1, -5), (1, 6)):
            ex = hx + dx
            r.poly([(ex - 3, hy + 6), (ex + 3, hy + 5 - side), (ex + 3, hy + 1), (ex - 3, hy + 2)], OUTLINE)
            r.line([(ex - 2, hy + 4), (ex + 2, hy + 3 - side)], GOLD[-1], 2)
        r.line([(hx - 9, hy + 8), (hx + 1, hy + 5), (hx + 10, hy + 8)], OUTLINE, 2)
        open_m = 2 + 4 * s + 2 * w
        r.poly([(hx - 7, hy - 3), (hx + 8, hy - 3), (hx + 6, hy - 5 - open_m), (hx - 5, hy - 5 - open_m)], OUTLINE)
        r.line([(hx - 4, hy - 4 - open_m * 0.5), (hx + 5, hy - 4 - open_m * 0.5)], GOLD[-1], 2)
        for fx in (-4, 0, 4):
            r.poly([(hx + fx, hy - 3), (hx + fx + 2, hy - 3), (hx + fx + 1, hy - 6)], WHITE)
    return a


def sunmoth(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solar_sunmoth', clip, n, (0, 32), 0.68)
    x = 18 * s - 8 * w + (math.sin(ph) * 2 if clip == 'walk' else 0)
    y = 54 + b + 6 * w - 6 * s - 26 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    flap = (0.56 + 0.22 * math.sin(ph * 1.6)) if clip in ('idle', 'walk') else (0.52 + 0.45 * w - 0.22 * s)
    span = max(0.20, flap * (1 - 0.72 * d))

    # Four sunburst wings (upper golden-amber with dark solar-eclipse ocelli, lower coral-crimson flare wings).
    for side in (-1, 1):
        root = (x + side * 4, y + 2)
        wx = x + side * (12 + 33 * span)
        wy = y + 14 + 10 * w - 6 * s - 14 * d
        r.poly([
            root,
            (x + side * 9, y + 20 - 8 * d),
            (wx, wy + 12 - 6 * d),
            (wx + side * 5, wy - 7),
            (x + side * 13, y - 12),
        ], AMBER[3], OUTLINE)
        r.poly([
            root,
            (x + side * 8, y - 3),
            (wx - side * 3, wy - 9),
            (x + side * 11, y - 23 + 8 * d),
        ], CORAL[2], OUTLINE)
        r.line([root, (wx - side * 2, wy + 4)], GOLD[-1], 2)
        ox, oy = wx - side * 5, wy + 2
        r.ball(ox, oy, max(2.5, 5.5 * span), 6, SLATE)
        if d < 0.65:
            r.ellipse(ox, oy, max(1.5, 3 * span), 3.5, GOLD[-1])
            r.ellipse(ox, oy, 1.5, 2, CRIMSON[2])
        # Feathery bronze antennae droop on death.
        r.taper([(x + side * 4, y + 18), (x + side * (10 + 4 * w), y + 29 - 13 * d), (x + side * 15, y + 32 - 17 * d)], BROWN, 2, 1)

    # Segmented bronze-and-amber moth abdomen and thorax.
    r.ball(x - 3, y - 8, 8, 15 * (1 - 0.25 * d), BROWN)
    for i in range(4):
        yy = y - 16 + i * 5
        r.line([(x - 8, yy), (x + 2, yy)], OUTLINE, 2)
    r.ball(x + 1, y + 6, 9, 9, AMBER)
    r.ball(x + 3, y + 14, 8, 7, BROWN)

    # Six jointed chitin legs curl inward beneath the thorax on death.
    for side in (-1, 1):
        for j in range(3):
            ly = y + 4 - j * 5
            r.limb([(x + side * 4, ly), (x + side * (10 - 4 * d), ly - 4 + 3 * d), (x + side * (7 - 5 * d), ly - 9 + 6 * d)], BROWN, 2)

    # Slanted crimson compound eyes, hooked ivory mandibles, and coiling solar proboscis.
    for side in (-1, 1):
        ex = x + 3 + side * 5
        r.poly([(ex - 3, y + 17), (ex + 3, y + 18), (ex + 4, y + 12), (ex - 2, y + 11)], CRIMSON[1], OUTLINE)
        if d < 0.65:
            r.line([(ex - 1, y + 16), (ex + 2, y + 13)], GOLD[-1], 1)
        r.poly([(x + 3 + side * 3, y + 9), (x + 3 + side * 6, y + 9), (x + 3 + side * (4 + 3 * s), y + 4)], BONE[3], OUTLINE)

    prob_ramp = GOLD if d < 0.65 else BROWN
    r.taper([
        (x + 5, y + 10),
        (x + 12 + 12 * s - 5 * w, y + 5 + 6 * w - 2 * s - 4 * d),
        (x + 16 + 24 * s - 7 * w, y + 9 - 6 * s - 7 * d),
    ], prob_ramp, 3, 1)
    if (s > 0.05 or w > 0.2) and d < 0.65:
        r.ball(x + 16 + 24 * s - 7 * w, y + 9 - 6 * s, 4.5, 4.5, CORAL)
    return a


def guard(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solar_crucible_guard', clip, n, (0, 10), -0.40)
    cy = 28 + b - 14 * d
    hx = 3 + 7 * s - 5 * w
    hy = 52 + b - 22 * d

    # Two planted dark-iron and bronze foundry greaves on the ground row.
    for i, x in enumerate((-11, 11)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 13 + lift), (x + step - 9 * d, 3 + lift)], SLATE, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, BROWN)

    # Heavy dark-iron cuirass with bronze pauldrons and glowing furnace-grate chest ribs.
    r.poly([(-18, cy - 8), (-21, cy + 14), (-6, cy + 21), (18, cy + 14), (17, cy - 8)], SLATE[2], OUTLINE)
    r.ball(-17, cy + 13, 8, 6, BROWN)
    r.ball(16, cy + 13, 8, 6, BROWN)
    if d < 0.65:
        for yy in (-2, 4, 10):
            r.line([(-10, cy + yy), (10, cy + yy)], GOLD[-1] if yy == 4 else CORAL[3], 2)
        r.ball(1, cy + 4, 5.5, 5.5, GOLD)
    else:
        r.ball(1, cy + 4, 5.5, 5.5, SLATE)

    # Crucible cauldron helm brimming with bubbling molten gold (cools to dark slate on death).
    r.ball(hx, hy, 12, 11, SLATE)
    r.poly([(hx - 13, hy + 8), (hx + 13, hy + 8), (hx + 10, hy + 15 - 3 * d), (hx - 10, hy + 15 - 3 * d)], BROWN[2], OUTLINE)
    if d < 0.65:
        r.ellipse(hx, hy + 14, 9, 3, GOLD[-1])
        for k in (-4, 1, 5):
            r.ellipse(hx + k, hy + 16 + (n + k) % 2, 2.2, 2.2, CORAL[3])
    r.poly([(hx - 10, hy + 5), (hx + 11, hy + 5), (hx + 9, hy - 2), (hx - 8, hy - 2)], OUTLINE)
    if d < 0.65:
        for dx in (-4, 5):
            r.line([(hx + dx - 2, hy + 2), (hx + dx + 2, hy + 1)], GOLD[-1], 2)
            r.line([(hx + dx, hy + 2), (hx + dx, hy)], CRIMSON[3], 1)
    for gx in (-5, -1, 3, 7):
        r.line([(hx + gx, hy - 3), (hx + gx, hy - 8)], OUTLINE, 1)

    # Far arm braces a riveted Crucible Cauldron Shield.
    sx, sy = -24 - 4 * w + 5 * s - 6 * d, cy + 5 + 3 * w - 8 * d
    r.limb([(-14, cy + 10), (-20, cy + 5), (sx, sy)], SLATE, 5)
    r.ball(sx, sy, 10, 11, BROWN)
    r.ball(sx, sy, 6, 6, GOLD if d < 0.65 else SLATE)

    # Near arm swings the Molten Forge-Hammer.
    hand = (20 + 24 * s - 9 * w, cy + 8 + 16 * w - 7 * s - 8 * d)
    r.limb([(13, cy + 10), (18 + 8 * s, cy + 4), hand], SLATE, 5)
    ang = 0.12 - 0.50 * w + 1.22 * s + 0.80 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 24, hand[1] + vy * 24)
    r.limb([(hand[0] - vx * 10, hand[1] - vy * 10), tip], BROWN, 3)
    r.ball(tip[0], tip[1], 10, 7, SLATE, ang)
    r.ball(tip[0], tip[1], 5.5, 4, GOLD if d < 0.65 else BROWN, ang)
    return a


def ashwarden(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solar_ashwarden', clip, n, (0, 10), -0.38)
    cy = 28 + b - 14 * d
    hx = 3 + 7 * s - 5 * w
    hy = 52 + b - 22 * d

    # Two planted cinder-iron boots on the ground row.
    for i, x in enumerate((-12, 12)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 13 + lift), (x + step - 9 * d, 3 + lift)], SLATE, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, PURPLE)

    # Heavy soot-and-obsidian ash-mantle torso with glowing ember shoulder-braziers.
    r.poly([(-19, cy - 8), (-22, cy + 15), (-6, cy + 22), (19, cy + 15), (18, cy - 8)], PURPLE[1], OUTLINE)
    r.poly([(-14, cy - 7), (-16, cy + 13), (14, cy + 13), (13, cy - 7)], SLATE[2], OUTLINE)
    for side in (-1, 1):
        px = side * 18
        r.ball(px, cy + 13, 8, 6, SLATE)
        if d < 0.65:
            r.poly([(px - 4, cy + 16), (px + side * 2, cy + 24 + 3 * w), (px + 4, cy + 16)], CORAL[3], OUTLINE)
            r.ellipse(px, cy + 18, 2.5, 2.5, GOLD[-1])

    # Three-horned obsidian furnace helm with three glaring ember-slit eyes and fanged ash-grille.
    r.ball(hx, hy, 12, 11, SLATE)
    r.ball(hx, hy + 6 - 2 * d, 14, 7, PURPLE)
    for k in (-1, 0, 1):
        tx = hx + k * 6
        r.poly([(tx - 3, hy + 12 - 3 * d), (tx + k * 2, hy + 23 - 6 * d), (tx + 3, hy + 12 - 3 * d)], SLATE[3], OUTLINE)
        if d < 0.65 and k == 0:
            r.line([(tx, hy + 13), (tx, hy + 20)], GOLD[-1], 2)
    for dx, dy in ((-5, 2), (1, 5), (6, 1)):
        r.poly([(hx + dx - 2, hy + dy + 2), (hx + dx + 2, hy + dy + 2), (hx + dx + 2, hy + dy - 2), (hx + dx - 2, hy + dy - 2)], OUTLINE)
        if d < 0.65:
            r.line([(hx + dx - 1, hy + dy), (hx + dx + 1, hy + dy)], GOLD[-1] if dx == 1 else CORAL[3], 2)
    r.poly([(hx - 7, hy - 4), (hx + 8, hy - 4), (hx + 6, hy - 9 - 2 * s), (hx - 5, hy - 9 - 2 * s)], OUTLINE)
    for fx in (-4, 0, 4):
        r.poly([(hx + fx, hy - 4), (hx + fx + 2, hy - 4), (hx + fx + 1, hy - 7)], BONE[3])

    # Far arm braces an ash-iron gauntlet buckler; near arm swings the two-handed Cinder-Cleaver Greatblade.
    sx, sy = -23 - 4 * w + 4 * s - 5 * d, cy + 6 - 7 * d
    r.limb([(-15, cy + 11), (-20, cy + 6), (sx, sy)], SLATE, 5)
    r.ball(sx, sy, 8, 9, PURPLE)
    hand = (20 + 24 * s - 9 * w, cy + 9 + 16 * w - 7 * s - 8 * d)
    r.limb([(14, cy + 11), (18 + 8 * s, cy + 4), hand], SLATE, 5)
    ang = 0.14 - 0.48 * w + 1.18 * s + 0.78 * d
    vx, vy = math.sin(ang), math.cos(ang)
    nx, ny = vy, -vx
    tip = (hand[0] + vx * 28, hand[1] + vy * 28)
    r.limb([(hand[0] - vx * 8, hand[1] - vy * 8), hand], BROWN, 4)
    r.poly([
        hand,
        (hand[0] + vx * 10 + nx * 6, hand[1] + vy * 10 + ny * 6),
        tip,
        (hand[0] + vx * 8 - nx * 4, hand[1] + vy * 8 - ny * 4),
    ], SLATE[3], OUTLINE)
    if d < 0.65:
        r.line([(hand[0] + vx * 4 + nx * 3, hand[1] + vy * 4 + ny * 3), tip], GOLD[-1], 2)
        r.ball(hand[0], hand[1], 4, 4, CORAL)
    else:
        r.ball(hand[0], hand[1], 4, 4, SLATE)
    return a


def heliomancer(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solar_heliomancer', clip, n, (0, 10), -0.36)
    cy = 28 + b - 14 * d
    hx = 3 + 7 * s - 5 * w
    hy = 52 + b - 22 * d

    # Two planted bronze-shod feet under the solar vestments.
    for i, x in enumerate((-10, 10)):
        step = math.sin(ph + i * math.pi) * 3.5 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 12 + lift), (x + step - 8 * d, 3 + lift)], BROWN, 5)
        r.ball(x + step - 8 * d, 3 + lift, 6.5, 3, AMBER)

    # Radiant eight-rayed golden Sun-Disc Halo behind the head (extinguishes on death).
    if d < 0.65:
        spin = ph * 0.4 if clip in ('idle', 'walk') else (0.8 * s - 0.4 * w)
        for k in range(8):
            ang = spin + k * math.pi / 4
            r1, r2 = 13, 22 + 3 * w + 3 * s
            r.poly([
                (hx + math.cos(ang - 0.16) * r1, hy + 4 + math.sin(ang - 0.16) * r1),
                (hx + math.cos(ang) * r2, hy + 4 + math.sin(ang) * r2),
                (hx + math.cos(ang + 0.16) * r1, hy + 4 + math.sin(ang + 0.16) * r1),
            ], GOLD[3] if k % 2 == 0 else CORAL[3], OUTLINE)
        r.ball(hx, hy + 4, 14, 14, GOLD)

    # Crimson-and-amber solar vestments and bronze sun-collar.
    r.poly([(-18, cy - 9), (-21, cy + 14), (-6, cy + 21), (18, cy + 14), (17, cy - 9)], CRIMSON[2], OUTLINE)
    r.poly([(-10, cy - 8), (-12, cy + 13), (11, cy + 13), (9, cy - 8)], AMBER[2], OUTLINE)
    r.ball(-16, cy + 13, 7.5, 6, BROWN)
    r.ball(15, cy + 13, 7.5, 6, BROWN)
    r.ball(1, cy + 5, 5.5, 5.5, GOLD if d < 0.65 else BROWN)

    # Horned bronze solar miter with angular sun-mask and glaring golden-white eyes.
    r.ball(hx, hy, 11, 10, BROWN)
    r.poly([(hx - 10, hy + 6), (hx, hy + 19 - 4 * d), (hx + 10, hy + 6)], AMBER[3], OUTLINE)
    r.poly([(hx - 9, hy + 4), (hx + 10, hy + 4), (hx + 8, hy - 3), (hx - 7, hy - 3)], OUTLINE)
    if d < 0.65:
        for dx in (-4, 5):
            r.line([(hx + dx - 2, hy + 1), (hx + dx + 2, hy + 1)], WHITE, 2)
            r.ellipse(hx + dx, hy + 1, 1.5, 1.5, GOLD[-1])

    # Far arm holds a bronze Sundial Astrolabe; near arm thrusts the Sun-burst Scepter.
    sx, sy = -22 - 4 * w + 4 * s - 5 * d, cy + 6 - 7 * d
    r.limb([(-14, cy + 10), (-19, cy + 5), (sx, sy)], CRIMSON, 5)
    r.ball(sx, sy, 8, 8, AMBER)
    hand = (20 + 24 * s - 9 * w, cy + 8 + 16 * w - 7 * s - 8 * d)
    r.limb([(13, cy + 10), (18 + 8 * s, cy + 4), hand], CRIMSON, 5)
    ang = 0.12 - 0.50 * w + 1.22 * s + 0.80 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 24, hand[1] + vy * 24)
    r.limb([(hand[0] - vx * 10, hand[1] - vy * 10), tip], BROWN, 3)
    r.ball(tip[0], tip[1], 8.5, 8.5, AMBER)
    r.ball(tip[0], tip[1], 5, 5, GOLD if d < 0.65 else BROWN)
    if (s > 0.05 or w > 0.2) and d < 0.65:
        r.poly([(tip[0], tip[1] + 4), (tip[0] + 14 * s, tip[1]), (tip[0], tip[1] - 4)], GOLD[-1], OUTLINE)
    return a


def heart(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solar_heart', clip, n, (0, 28), 0.22)
    drift = math.sin(ph) * 2 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 54 + b + 6 * w - 6 * s - 22 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    spin = (ph * 0.5 if clip in ('idle', 'walk') else (1.1 * s - 0.5 * w)) * (1 - d)

    # Four orbiting dark-iron and bronze Crucible Containment Fins around the core; collapse inward and downward on death.
    for k in range(8):
        ang = spin + k * math.pi / 4
        rx_p = (22 + 4 * w) * (1 + 0.10 * d)
        ry_p = (22 + 4 * w) * (1 - 0.42 * d)
        px = x + math.cos(ang) * rx_p
        py = y + math.sin(ang) * ry_p - 4 * d
        r.ball(px, py, 7, 8 * (1 - 0.28 * d), SLATE if k % 2 == 0 else BROWN, ang + math.pi * 0.5)

    # Roaring solar corona rays while alive (extinguish on death).
    if d < 0.65:
        for k in range(6):
            ang = spin + k * math.pi / 3 + 0.3
            r1 = 18
            r2 = 31 + 5 * w + 4 * s
            r.poly([
                (x + math.cos(ang - 0.16) * r1, y + math.sin(ang - 0.16) * r1 * 0.85),
                (x + math.cos(ang) * r2, y + math.sin(ang) * r2 * 0.85),
                (x + math.cos(ang + 0.16) * r1, y + math.sin(ang + 0.16) * r1 * 0.85),
            ], GOLD[3] if k % 2 == 0 else CORAL[3], OUTLINE)

    # Heavy dark-iron Crucible Bowl cradling the blazing Solar Heart core.
    core_s = 1 - 0.30 * d
    r.ball(x, y - 5 * d, 20 * core_s, 18 * core_s, SLATE)
    r.ball(x, y + 3 * (1 - d), 16 * core_s, 15 * core_s, CRIMSON if d < 0.65 else BROWN)
    if d < 0.65:
        r.ball(x - 1, y + 4, 11, 10, GOLD)

    # Sunburst prominence cone on wind-up and strike.
    if (s > 0.05 or w > 0.2) and d < 0.65:
        reach = 22 + 26 * s - 8 * w
        r.poly([(x + 14, y + 7), (x + reach, y), (x + 14, y - 7)], GOLD[-1], OUTLINE)
        r.line([(x + 16, y), (x + reach - 3, y)], WHITE, 2)

    # Heart of the Crucible face: central diamond solar eye, two searing slit eyes and furnace-grate maw.
    if d < 0.65:
        r.poly([(x - 1, y + 9), (x + 3, y + 14), (x + 7, y + 9), (x + 3, y + 4)], OUTLINE)
        r.line([(x + 3, y + 12), (x + 3, y + 6)], WHITE, 2)
        for side, dx in ((-1, -7), (1, 9)):
            ex = x + dx
            r.poly([(ex - 4, y + 3), (ex + 4, y + 2 - side), (ex + 3, y - 2), (ex - 3, y - 1)], OUTLINE)
            r.line([(ex - 2, y + 1), (ex + 2, y)], GOLD[-1], 2)
        open_m = 3 + 5 * s + 2 * w
        r.poly([(x - 8, y - 5), (x + 10, y - 5), (x + 7, y - 6 - open_m), (x - 6, y - 6 - open_m)], OUTLINE)
        for fx in (-4, 1, 6):
            r.poly([(x + fx, y - 5), (x + fx + 2, y - 5), (x + fx + 1, y - 8)], WHITE)
    else:
        r.line([(x - 11, y + 7), (x, y - 1), (x + 11, y - 8)], OUTLINE, 2)
    return a


def cinder(setup, clip, n):
    a, r, w, s, d, ph, b = setup('solar_cinder', clip, n, (0, 10), -0.35)
    cy = 25 + b - 12 * d
    hx = 2 + 18 * s - 7 * w
    hy = 34 + b + 4 * w - 2 * s - 14 * d

    # Two planted basalt-slag pillar legs on the ground row.
    for i, x in enumerate((-12, 12)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 12 + lift), (x + step - 8 * d, 3 + lift)], SLATE, 6)
        r.ball(x + step - 8 * d, 3 + lift, 7, 3, BROWN)

    # Three-spiked slag crown and cracked basalt-coal carapace; splits into two dark rock mounds on death.
    if d < 0.35:
        for k in (-1, 0, 1):
            tx = hx + k * 8
            r.poly([(tx - 4, hy + 12), (tx + k * 2, hy + 24 + 3 * w), (tx + 4, hy + 12)], SLATE[2], OUTLINE)
        r.ball(hx, hy, 20, 18, SLATE)
        r.ball(hx - 3, hy + 2, 14, 13, BROWN)
        if d < 0.65:
            r.ball(hx + 1, hy + 1, 9, 8, CRIMSON)
            r.line([(hx - 12, hy + 7), (hx, hy), (hx + 12, hy - 6)], GOLD[-1], 2)
            r.line([(hx + 10, hy + 8), (hx, hy), (hx - 9, hy - 7)], CORAL[3], 2)
    else:
        sep = (d - 0.25) * 15
        for side in (-1, 1):
            cx_h = hx + side * sep
            cy_h = hy - 3 * d
            r.ball(cx_h, cy_h, 14, 12 * (1 - 0.28 * d), SLATE, side * 0.36 * d)
            r.ball(cx_h - side * 2, cy_h + 1, 9, 8 * (1 - 0.28 * d), BROWN, side * 0.36 * d)
            r.poly([
                (cx_h - side * 2, cy_h + 9 * (1 - 0.28 * d)),
                (cx_h + side * 6, cy_h + 1),
                (cx_h + side * 4, cy_h - 8 * (1 - 0.28 * d)),
                (cx_h - side * 2, cy_h - 6 * (1 - 0.28 * d)),
            ], OUTLINE, OUTLINE)

    # Heavy cinder-crusher arms; near arm slams forward with a ground-pound lava burst on strike.
    r.limb([(hx - 14, hy + 3), (hx - 21 - 4 * w, hy - 2 - 5 * d), (hx - 25 - 6 * d, hy - 7 - 6 * d)], SLATE, 5)
    hand = (hx + 16 + 18 * s - 8 * w, hy + 2 + 12 * w - 6 * s - 7 * d)
    r.limb([(hx + 13, hy + 3), (hx + 18 + 6 * s, hy - 1), hand], SLATE, 5)
    r.ball(hand[0], hand[1], 7, 6, BROWN)
    if d < 0.65:
        r.ball(hand[0], hand[1], 4, 3.5, GOLD if s > 0.2 else CORAL)

    # Scowling asymmetrical lava-hollow eyes and jagged slag maw.
    if d < 0.65:
        for side, dx in ((-1, -6), (1, 6)):
            ex = hx + dx
            r.poly([(ex - 3, hy + 6), (ex + 3, hy + 5 - side), (ex + 3, hy + 1), (ex - 3, hy + 2)], OUTLINE)
            r.line([(ex - 2, hy + 4), (ex + 2, hy + 3 - side)], GOLD[-1] if side > 0 else CORAL[3], 2)
        open_m = 2 + 4 * s + 2 * w
        r.poly([(hx - 8, hy - 3), (hx + 9, hy - 3), (hx + 7, hy - 5 - open_m), (hx - 6, hy - 5 - open_m)], OUTLINE)
        for fx in (-5, 0, 5):
            r.poly([(hx + fx, hy - 3), (hx + fx + 2, hy - 3), (hx + fx + 1, hy - 6)], BONE[3])
    return a
