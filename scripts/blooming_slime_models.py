"""Six articulated Blooming Labyrinth creatures in y-up coordinates; props follow their grips."""
import math
from astral_slime_redraw import (
    OUTLINE, WHITE, BONE, PEARL, GOLD, GREEN, LEAF, TEAL,
    AZURE, SLATE, PURPLE, VIOLET, CRIMSON, MAROON, BROWN, OLIVE, PINK, CORAL, AMBER,
)


def spore(setup, clip, n):
    a, r, w, s, d, ph, b = setup('bloom_spore', clip, n, (0, 26), 0.28)
    drift = math.sin(ph) * 2.5 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 52 + b + 6 * w - 6 * s - 20 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    spin = (ph * 0.6 if clip in ('idle', 'walk') else (0.9 * s - 0.5 * w)) * (1 - d)

    # Trailing green root-tendrils beneath the floating spore capsule; splay outward on death.
    for side in (-1, 1):
        tx = x + side * (8 + 5 * d)
        ty = y - 16 + 4 * d
        r.taper([(x + side * 5, y - 8), (tx, ty), (tx + side * (5 + 4 * d), ty - 9 + 5 * d)], GREEN, 3, 1.5)

    # Six translucent magenta-and-coral glass petals around the capsule; flare on wind-up, wilt on death.
    for k in range(6):
        ang = spin + k * math.pi / 3
        rad = (15 + 4 * w + 2 * s) * (1 - 0.15 * d)
        px = x + math.cos(ang) * rad + (side_sign := (1 if math.cos(ang) >= 0 else -1)) * 4 * d
        py = y + math.sin(ang) * rad * (1 - 0.45 * d) - 3 * d
        r.ball(px, py, 6, 8 * (1 - 0.25 * d), PINK if k % 2 == 0 else CORAL, ang + math.pi * 0.5)
        r.line([(x + math.cos(ang) * 7, y + math.sin(ang) * 7 * (1 - 0.35 * d)), (px, py)], PEARL[3], 1)

    # Violet-and-purple crystalline spore bulb: splits into two cracked glass halves on death.
    if d < 0.35:
        r.ball(x, y, 14, 16, PURPLE)
        r.ball(x - 2, y + 3, 9, 11, VIOLET)
        if d < 0.65:
            r.ball(x, y + 2, 6, 7, GOLD)
    else:
        sep = (d - 0.25) * 12
        for side in (-1, 1):
            hx = x + side * sep
            hy = y - 3 * d
            r.ball(hx, hy, 10, 12 * (1 - 0.3 * d), PURPLE, side * 0.4 * d)
            r.ball(hx - side * 2, hy + 2, 6, 7 * (1 - 0.3 * d), VIOLET, side * 0.4 * d)
            r.poly([
                (hx - side * 2, hy + 9 * (1 - 0.3 * d)),
                (hx + side * 5, hy + 2),
                (hx + side * 3, hy - 8 * (1 - 0.3 * d)),
                (hx - side * 2, hy - 6 * (1 - 0.3 * d)),
            ], OUTLINE, OUTLINE)

    # Focused golden-and-pink prism-spore lance on wind-up and strike.
    if (s > 0.05 or w > 0.2) and d < 0.65:
        reach = 18 + 26 * s - 6 * w
        r.poly([(x + 11, y + 5), (x + reach, y + 1), (x + 11, y - 4)], PINK[3], OUTLINE)
        r.line([(x + 13, y + 1), (x + reach - 3, y + 1)], GOLD[-1], 2)
        r.ball(x + reach - 2, y + 1, 3.5, 3.5, TEAL)

    # Fierce diamond prism-cyclops eye under an angry V-brow and a thorn-toothed spore maw.
    if d < 0.65:
        r.poly([(x - 5, y + 8), (x + 1, y + 13), (x + 7, y + 8), (x + 1, y + 2)], OUTLINE)
        r.poly([(x - 3, y + 8), (x + 1, y + 11), (x + 5, y + 8), (x + 1, y + 4)], GOLD[-1])
        r.line([(x + 1, y + 11), (x + 1, y + 4)], TEAL[-1], 2)
        r.line([(x - 8, y + 11), (x + 1, y + 7), (x + 9, y + 11)], OUTLINE, 2)
        open_m = 2 + 4 * s + 2 * w
        r.poly([(x - 6, y - 4), (x + 7, y - 4), (x + 5, y - 6 - open_m), (x - 4, y - 6 - open_m)], OUTLINE)
        for fx in (-3, 1, 4):
            r.poly([(x + fx, y - 4), (x + fx + 2, y - 4), (x + fx + 1, y - 7)], WHITE)
    return a


def moth(setup, clip, n):
    a, r, w, s, d, ph, b = setup('bloom_moth', clip, n, (0, 32), 0.72)
    x = 18 * s - 8 * w + (math.sin(ph) * 2 if clip == 'walk' else 0)
    y = 54 + b + 6 * w - 6 * s - 26 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    flap = (0.56 + 0.22 * math.sin(ph * 1.6)) if clip in ('idle', 'walk') else (0.52 + 0.45 * w - 0.22 * s)
    span = max(0.20, flap * (1 - 0.72 * d))

    # Four stained-glass petal wings (upper magenta-pink, lower azure-prism) with golden eye-spots while alive.
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
        ], PINK[2], OUTLINE)
        r.poly([
            root,
            (x + side * 8, y - 3),
            (wx - side * 3, wy - 9),
            (x + side * 11, y - 23 + 8 * d),
        ], AZURE[2], OUTLINE)
        r.line([root, (wx - side * 2, wy + 4)], PEARL[3], 2)
        ox, oy = wx - side * 5, wy + 2
        r.ball(ox, oy, max(2.5, 5.5 * span), 6, PURPLE)
        if d < 0.65:
            r.ellipse(ox, oy, max(1.5, 3 * span), 3.5, GOLD[-1])
            r.ellipse(ox, oy, 1.5, 2, TEAL[-1])
        # Feathery violet antennae droop on death.
        r.taper([(x + side * 4, y + 18), (x + side * (10 + 4 * w), y + 29 - 13 * d), (x + side * 15, y + 32 - 17 * d)], PURPLE, 2, 1)

    # Segmented violet-and-purple moth abdomen and thorax.
    r.ball(x - 3, y - 8, 8, 15 * (1 - 0.25 * d), PURPLE)
    for i in range(4):
        yy = y - 16 + i * 5
        r.line([(x - 8, yy), (x + 2, yy)], OUTLINE, 2)
    r.ball(x + 1, y + 6, 9, 9, VIOLET)
    r.ball(x + 3, y + 14, 8, 7, PURPLE)

    # Six jointed chitin legs curl inward beneath the thorax on death.
    for side in (-1, 1):
        for j in range(3):
            ly = y + 4 - j * 5
            r.limb([(x + side * 4, ly), (x + side * (10 - 4 * d), ly - 4 + 3 * d), (x + side * (7 - 5 * d), ly - 9 + 6 * d)], PURPLE, 2)

    # Slanted compound eyes, hooked ivory mandibles, and coiling prism proboscis.
    for side in (-1, 1):
        ex = x + 3 + side * 5
        r.poly([(ex - 3, y + 17), (ex + 3, y + 18), (ex + 4, y + 12), (ex - 2, y + 11)], CRIMSON[1], OUTLINE)
        if d < 0.65:
            r.line([(ex - 1, y + 16), (ex + 2, y + 13)], GOLD[-1], 1)
        r.poly([(x + 3 + side * 3, y + 9), (x + 3 + side * 6, y + 9), (x + 3 + side * (4 + 3 * s), y + 4)], BONE[3], OUTLINE)

    prob_ramp = GOLD if d < 0.65 else PURPLE
    r.taper([
        (x + 5, y + 10),
        (x + 12 + 12 * s - 5 * w, y + 5 + 6 * w - 2 * s - 4 * d),
        (x + 16 + 24 * s - 7 * w, y + 9 - 6 * s - 7 * d),
    ], prob_ramp, 3, 1)
    if (s > 0.05 or w > 0.2) and d < 0.65:
        r.ball(x + 16 + 24 * s - 7 * w, y + 9 - 6 * s, 4, 4, TEAL)
    return a


def guard(setup, clip, n):
    a, r, w, s, d, ph, b = setup('bloom_guard', clip, n, (0, 10), -0.40)
    cy = 28 + b - 14 * d
    hx = 3 + 7 * s - 5 * w
    hy = 52 + b - 22 * d

    # Two planted living-vine and glass greaves on the ground row.
    for i, x in enumerate((-11, 11)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 13 + lift), (x + step - 9 * d, 3 + lift)], GREEN, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, AZURE)

    # Faceted azure-glass cuirass overgrown with knotted green vines and rose-petal shoulder guards.
    r.poly([(-18, cy - 8), (-21, cy + 14), (-6, cy + 21), (18, cy + 14), (17, cy - 8)], AZURE[2], OUTLINE)
    for k in (-10, 0, 10):
        r.line([(k - 3, cy - 7), (k + 3, cy + 15)], GREEN[1], 2)
    r.ball(-17, cy + 13, 8, 6, PINK)
    r.ball(16, cy + 13, 8, 6, PINK)
    r.ball(2, cy + 5, 6, 6, GOLD if d < 0.65 else AZURE)

    # Vineglass barbute helm with a 3-petal rose crest, glaring golden/teal visor eyes and thorn grill.
    for k in (-1, 0, 1):
        r.ball(hx + k * 6, hy + 14 + (2 if k == 0 else 0) - 4 * d, 3.5, 6 * (1 - 0.3 * d), PINK, k * 0.4)
    r.ball(hx, hy, 12, 11, AZURE)
    r.poly([(hx - 11, hy + 5), (hx + 12, hy + 5), (hx + 10, hy - 2), (hx - 9, hy - 2)], OUTLINE)
    if d < 0.65:
        for dx in (-4, 5):
            r.line([(hx + dx - 2, hy + 2), (hx + dx + 2, hy + 1)], GOLD[-1], 2)
            r.line([(hx + dx, hy + 2), (hx + dx, hy)], TEAL[-1], 1)
    r.poly([(hx - 8, hy - 3), (hx + 9, hy - 3), (hx + 7, hy - 9), (hx - 6, hy - 9)], GREEN[1], OUTLINE)
    for gx in (-4, 0, 4):
        r.line([(hx + gx, hy - 4), (hx + gx, hy - 8)], OUTLINE, 1)

    # Far arm braces a six-petalled Rose-Glass Buckler Shield.
    sx, sy = -24 - 4 * w + 5 * s - 6 * d, cy + 5 + 3 * w - 8 * d
    r.limb([(-14, cy + 10), (-20, cy + 5), (sx, sy)], GREEN, 5)
    for k in range(6):
        ang = k * math.pi / 3
        r.ball(sx + math.cos(ang) * 7, sy + math.sin(ang) * 7, 5, 6, PINK, ang + math.pi * 0.5)
    r.ball(sx, sy, 5, 5, AZURE)

    # Near arm swings the Vineglass Morning-Star Mace (golden/teal core shuts off on death).
    hand = (20 + 24 * s - 9 * w, cy + 8 + 16 * w - 7 * s - 8 * d)
    r.limb([(13, cy + 10), (18 + 8 * s, cy + 4), hand], GREEN, 5)
    ang = 0.12 - 0.50 * w + 1.22 * s + 0.80 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 24, hand[1] + vy * 24)
    r.limb([(hand[0] - vx * 10, hand[1] - vy * 10), tip], GREEN, 3)
    r.ball(tip[0], tip[1], 9, 9, AZURE)
    r.ball(tip[0], tip[1], 5, 5, TEAL if d < 0.65 else AZURE)
    return a


def thornkeeper(setup, clip, n):
    a, r, w, s, d, ph, b = setup('bloom_thornkeeper', clip, n, (0, 10), -0.38)
    cy = 28 + b - 14 * d
    hx = 3 + 7 * s - 5 * w
    hy = 52 + b - 22 * d

    # Two planted gnarled-root and vine boots on the ground row.
    for i, x in enumerate((-12, 12)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 13 + lift), (x + step - 9 * d, 3 + lift)], GREEN, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, BROWN)

    # Heavy dark-bark torso wrapped in thorny crimson briar vines.
    r.poly([(-19, cy - 8), (-22, cy + 15), (-6, cy + 22), (19, cy + 15), (18, cy - 8)], BROWN[2], OUTLINE)
    for yy in (-3, 5, 12):
        r.line([(-16, cy + yy), (16, cy + yy - 1)], GREEN[1], 2)
    for side in (-1, 1):
        px = side * 18
        r.ball(px, cy + 13, 8, 6, BROWN)
        r.poly([(px - 3, cy + 16), (px + side * 4, cy + 24 - 4 * d), (px + 3, cy + 16)], CRIMSON[2], OUTLINE)

    # Wide-brimmed bark hat crowned with three crimson briar horns, three asymmetric knothole eyes, and fanged snarl.
    r.ball(hx, hy, 12, 11, BROWN)
    r.ball(hx, hy + 8 - 2 * d, 17, 4, BROWN)
    r.ball(hx, hy + 13 - 3 * d, 10, 6, BROWN)
    for k in (-1, 0, 1):
        tx = hx + k * 6
        r.poly([(tx - 3, hy + 15 - 3 * d), (tx + k * 2, hy + 24 - 6 * d), (tx + 3, hy + 15 - 3 * d)], CRIMSON[2], OUTLINE)
    for dx, dy in ((-5, 2), (1, 5), (6, 1)):
        r.poly([(hx + dx - 2, hy + dy + 2), (hx + dx + 2, hy + dy + 2), (hx + dx + 2, hy + dy - 2), (hx + dx - 2, hy + dy - 2)], OUTLINE)
        if d < 0.65:
            r.line([(hx + dx - 1, hy + dy), (hx + dx + 1, hy + dy)], GOLD[-1] if dx != 1 else TEAL[-1], 2)
    r.poly([(hx - 7, hy - 4), (hx + 8, hy - 4), (hx + 6, hy - 9 - 2 * s), (hx - 5, hy - 9 - 2 * s)], OUTLINE)
    for fx in (-4, 0, 4):
        r.poly([(hx + fx, hy - 4), (hx + fx + 2, hy - 4), (hx + fx + 1, hy - 7)], WHITE)

    # Far arm braces a briar-thorn buckler; near arm swings giant crossed steel Garden Shears.
    sx, sy = -23 - 4 * w + 4 * s - 5 * d, cy + 6 - 7 * d
    r.limb([(-15, cy + 11), (-20, cy + 6), (sx, sy)], BROWN, 5)
    r.ball(sx, sy, 8, 9, CRIMSON)
    hand = (20 + 24 * s - 9 * w, cy + 9 + 16 * w - 7 * s - 8 * d)
    r.limb([(14, cy + 11), (18 + 8 * s, cy + 4), hand], BROWN, 5)
    ang = 0.14 - 0.48 * w + 1.18 * s + 0.78 * d
    vx, vy = math.sin(ang), math.cos(ang)
    pivot = (hand[0] + vx * 8, hand[1] + vy * 8)
    r.limb([(hand[0] - vx * 8, hand[1] - vy * 8), pivot], BROWN, 4)
    spread = (0.38 * w + 0.06 * (1 - s)) * (1 - 0.7 * d)
    for side, ramp in ((-1, SLATE), (1, PEARL)):
        ba = ang + side * (0.14 + spread)
        bvx, bvy = math.sin(ba), math.cos(ba)
        nx, ny = bvy * side, -bvx * side
        tip = (pivot[0] + bvx * 24, pivot[1] + bvy * 24)
        r.poly([
            pivot,
            (pivot[0] + bvx * 10 + nx * 5, pivot[1] + bvy * 10 + ny * 5),
            tip,
            (pivot[0] + bvx * 6 - nx * 2, pivot[1] + bvy * 6 - ny * 2),
        ], ramp[3], OUTLINE)
    r.ball(pivot[0], pivot[1], 3.5, 3.5, CRIMSON)
    return a


def mirror(setup, clip, n):
    a, r, w, s, d, ph, b = setup('bloom_mirror', clip, n, (0, 28), 0.24)
    drift = math.sin(ph) * 2 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 54 + b + 6 * w - 6 * s - 22 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)

    # Trailing green briar vines beneath the hovering mirror frame.
    for side in (-1, 1):
        tx = x + side * (10 + 5 * d)
        ty = y - 22 + 6 * d
        r.taper([(x + side * 6, y - 12), (tx, ty), (tx + side * (5 + 4 * d), ty - 10 + 6 * d)], GREEN, 3.5, 1.5)

    # Ten rose-glass petals around the gothic mirror rim; flare on wind-up, droop on death.
    for k in range(10):
        ang = k * math.pi / 5 + (0.08 * math.sin(ph) if clip in ('idle', 'walk') else 0)
        rx_p = (21 + 3 * w) * (1 + 0.08 * d)
        ry_p = (23 + 3 * w) * (1 - 0.38 * d)
        px = x + math.cos(ang) * rx_p
        py = y + math.sin(ang) * ry_p - 3 * d
        r.ball(px, py, 5.5, 7 * (1 - 0.25 * d), PINK if k % 2 == 0 else CORAL, ang + math.pi * 0.5)

    # Ornate rose-frame and reflective cobalt-and-pearl mirror glass pane.
    r.ball(x, y, 20, 22 * (1 - 0.32 * d), PINK)
    r.ball(x, y, 15, 17 * (1 - 0.32 * d), AZURE)
    r.ball(x - 3, y + 4 * (1 - 0.3 * d), 7, 9 * (1 - 0.32 * d), PEARL)

    # Refracted golden-and-teal prism lance on attack wind-up and strike.
    if (s > 0.05 or w > 0.2) and d < 0.65:
        reach = 22 + 26 * s - 7 * w
        r.poly([(x + 12, y + 6), (x + reach, y + 1), (x + 12, y - 5)], GOLD[-1], OUTLINE)
        r.line([(x + 14, y + 1), (x + reach - 3, y + 1)], TEAL[-1], 2)

    # Mirror face: tall vertical reflection-slit eyes and shard-toothed grin; cracks spiderweb on death.
    if d < 0.65:
        for side, dx in ((-1, -5), (1, 6)):
            ex = x + dx
            r.poly([(ex - 3, y + 7), (ex + 3, y + 6 - side), (ex + 3, y - 1), (ex - 3, y)], OUTLINE)
            r.line([(ex, y + 5), (ex, y)], TEAL[-1], 2)
            r.ellipse(ex, y + 3, 1.5, 1.5, GOLD[-1])
        open_m = 2 + 4 * s + 2 * w
        r.poly([(x - 7, y - 4), (x + 8, y - 4), (x + 6, y - 6 - open_m), (x - 5, y - 6 - open_m)], OUTLINE)
        for fx in (-4, 0, 4):
            r.poly([(x + fx, y - 4), (x + fx + 2, y - 4), (x + fx + 1, y - 7)], WHITE)
    else:
        r.line([(x - 10, y + 9), (x, y), (x + 11, y - 8)], OUTLINE, 2)
        r.line([(x + 9, y + 8), (x, y), (x - 8, y - 7)], OUTLINE, 2)
    return a


def heart(setup, clip, n):
    a, r, w, s, d, ph, b = setup('bloom_heart', clip, n, (0, 28), 0.22)
    drift = math.sin(ph) * 2 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 54 + b + 6 * w - 6 * s - 22 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    spin = (ph * 0.5 if clip in ('idle', 'walk') else (1.1 * s - 0.5 * w)) * (1 - d)

    # Four writhing green labyrinth root-vines beneath the heart.
    for k, sx in enumerate((-14, -5, 5, 14)):
        sway = math.sin(ph + k) * 3 * (1 - d)
        r.taper([(x + sx * 0.6, y - 10), (x + sx + sway, y - 22 + 5 * d), (x + sx * 1.2 + sway, y - 30 + 9 * d)], GREEN, 4, 1.5)

    # Eight layered rose-glass lotus petals and छह ivory glass thorns around the heart; wilt outward on death.
    for k in range(8):
        ang = spin + k * math.pi / 4
        rx_p = (21 + 4 * w) * (1 + 0.12 * d)
        ry_p = (22 + 4 * w) * (1 - 0.42 * d)
        px = x + math.cos(ang) * rx_p
        py = y + math.sin(ang) * ry_p - 4 * d
        r.ball(px, py, 7, 9 * (1 - 0.28 * d), PINK if k % 2 == 0 else CORAL, ang + math.pi * 0.5)
    for k in range(6):
        ang = spin + k * math.pi / 3 + 0.4
        r1 = 18 * (1 - 0.2 * d)
        r2 = (30 + 4 * w) * (1 - 0.25 * d)
        r.poly([
            (x + math.cos(ang - 0.14) * r1, y + math.sin(ang - 0.14) * r1 * (1 - 0.35 * d)),
            (x + math.cos(ang) * r2, y + math.sin(ang) * r2 * (1 - 0.4 * d) - 3 * d),
            (x + math.cos(ang + 0.14) * r1, y + math.sin(ang + 0.14) * r1 * (1 - 0.35 * d)),
        ], PEARL[3], OUTLINE)

    # Faceted crimson-and-rose Heart of the Labyrinth crystal core.
    core_s = 1 - 0.32 * d
    r.ball(x, y, 18 * core_s, 19 * core_s, CRIMSON)
    r.ball(x - 2, y + 3, 12 * core_s, 13 * core_s, PINK)

    # Four orbiting golden-and-teal prism motes and Prism Bounce beam on attack; extinguish on death.
    if d < 0.65:
        for k in range(4):
            ang = spin + k * math.pi * 0.5
            px = x + math.cos(ang) * 30
            py = y + math.sin(ang) * 15
            r.poly([(px - 3, py + 6), (px + 3, py + 6), (px, py - 7)], GOLD[3], OUTLINE)
            r.ball(px, py, 3, 3, TEAL)
    if (s > 0.05 or w > 0.2) and d < 0.65:
        reach = 22 + 26 * s - 8 * w
        r.poly([(x + 14, y + 6), (x + reach, y), (x + 14, y - 6)], GOLD[-1], OUTLINE)
        r.line([(x + 16, y), (x + reach - 3, y)], TEAL[-1], 2)

    # Labyrinth Heart face: diamond third eye, two jagged V-slit eyes and crystal-thorn maw.
    if d < 0.65:
        r.poly([(x - 1, y + 9), (x + 3, y + 14), (x + 7, y + 9), (x + 3, y + 4)], OUTLINE)
        r.line([(x + 3, y + 12), (x + 3, y + 6)], GOLD[-1], 2)
        for side, dx in ((-1, -7), (1, 9)):
            ex = x + dx
            r.poly([(ex - 4, y + 3), (ex + 4, y + 2 - side), (ex + 3, y - 2), (ex - 3, y - 1)], OUTLINE)
            r.line([(ex - 2, y + 1), (ex + 2, y)], TEAL[-1], 2)
        open_m = 3 + 5 * s + 2 * w
        r.poly([(x - 8, y - 5), (x + 10, y - 5), (x + 7, y - 6 - open_m), (x - 6, y - 6 - open_m)], OUTLINE)
        for fx in (-4, 1, 6):
            r.poly([(x + fx, y - 5), (x + fx + 2, y - 5), (x + fx + 1, y - 8)], WHITE)
    else:
        r.line([(x - 10, y + 8), (x, y), (x + 10, y - 7)], OUTLINE, 2)
    return a
