"""Six articulated Thunderheart Gate creatures in y-up coordinates; props follow their grips."""
import math
from astral_slime_redraw import (
    OUTLINE, WHITE, BONE, PEARL, GOLD, GREEN, LEAF, TEAL,
    AZURE, SLATE, PURPLE, VIOLET, CRIMSON, MAROON, BROWN, OLIVE, PINK, CORAL, AMBER,
)


def spark(setup, clip, n):
    a, r, w, s, d, ph, b = setup('thunder_spark', clip, n, (0, 26), 0.32)
    drift = math.sin(ph) * 2.5 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 52 + b + 6 * w - 6 * s - 20 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    spin = (ph if clip in ('idle', 'walk') else (1.3 * s - 0.6 * w)) * (1 - d)
    # Seven forked lightning prongs and crackling teal plasma arcs; discharge and vanish on death.
    if d < 0.65:
        fade = 1 - d / 0.65
        for k in range(7):
            ang = spin + k * 2 * math.pi / 7
            r1 = 15
            r2 = (28 if k % 2 == 0 else 23) * fade
            x1, y1 = x + math.cos(ang - 0.18) * r1, y + math.sin(ang - 0.18) * r1
            x2, y2 = x + math.cos(ang) * r2, y + math.sin(ang) * r2
            x3, y3 = x + math.cos(ang + 0.18) * r1, y + math.sin(ang + 0.18) * r1
            r.poly([(x1, y1), (x2, y2), (x3, y3)], GOLD[3 if k % 2 == 0 else 2], OUTLINE)
            if k % 2 == 0:
                r.line([(x, y), (x2, y2)], TEAL[-1], 1)
    # Heavy bronze-and-slate storm-capacitor shell: stays intact as it falls to the ground on death.
    for side in (-1, 1):
        r.poly([
            (x + side * 12, y + 12 * (1 - 0.2 * d)),
            (x + side * 19, y + 18 * (1 - 0.25 * d)),
            (x + side * 16, y + 6 * (1 - 0.2 * d)),
        ], AMBER[2], OUTLINE)
    r.ball(x, y, 16, 15 * (1 - 0.22 * d), AMBER)
    r.ball(x, y, 12, 11 * (1 - 0.22 * d), SLATE)
    if d < 0.65:
        r.ball(x - 2, y + 2, 8, 7, GOLD)
    # Forked lightning lance on attack wind-up and strike.
    if s > 0.05 or w > 0.2:
        reach = 20 + 26 * s - 6 * w
        r.poly([(x + 12, y + 5), (x + reach, y + 2), (x + 12, y - 4)], GOLD[-1], OUTLINE)
        r.line([(x + 14, y), (x + reach - 2, y + 2)], TEAL[-1], 2)
    # Three jagged lightning-slit eyes and a snarling zig-zag maw.
    r.poly([(x - 1, y + 7), (x + 2, y + 12), (x + 5, y + 7), (x + 2, y + 3)], OUTLINE)
    if d < 0.65:
        r.line([(x + 2, y + 10), (x + 2, y + 5)], TEAL[-1], 1)
    for side, dx in ((-1, -6), (1, 7)):
        ex = x + dx
        r.poly([(ex - 4, y + 3), (ex + 3, y + 2 - side), (ex + 3, y - 2), (ex - 3, y - 1)], OUTLINE)
        if d < 0.65:
            r.line([(ex - 2, y + 1), (ex + 2, y)], TEAL[-1], 2)
    open_m = (2 + 4 * s + 2 * w) * (1 - 0.6 * d)
    r.poly([(x - 7, y - 4), (x + 8, y - 4), (x + 6, y - 6 - open_m), (x - 5, y - 6 - open_m)], OUTLINE)
    for fx in (-4, 1, 5):
        r.poly([(x + fx, y - 4), (x + fx + 2, y - 4), (x + fx + 1, y - 7)], WHITE)
    return a


def ray(setup, clip, n):
    a, r, w, s, d, ph, b = setup('thunder_ray', clip, n, (0, 22), 0.18)
    drift = math.sin(ph) * 2.5 if clip == 'walk' else 0
    flap = (math.sin(ph) * 10 if clip in ('idle', 'walk') else (14 * w - 12 * s)) * (1 - 0.9 * d)
    curl = d
    x = 12 + 8 * s - 5 * w + drift
    y = 58 + b + 5 * w - 2 * s - 28 * d + (math.cos(ph) * 1.5 if clip == 'walk' else 0)

    # 1. Smooth 9-point sinuous S-curve whip-tail streaming behind (-x) from the rear of the manta disc.
    tail_pts = []
    for k in range(9):
        u = k / 8.0
        tx = x - 15 - u * (32 - 5 * curl) - 3 * w * u + 5 * s * u
        wave = math.sin(ph - u * 3.6) * (1.5 + 4.0 * u) if clip in ('idle', 'walk') else (math.sin(u * 3.14) * (7 * w - 5 * s))
        ty = y + 2 - 2 * u + wave * (1 - curl) - 3 * curl * u
        tail_pts.append((tx, ty))
    r.taper(tail_pts, AZURE, 5, 1.5)
    t_end = tail_pts[-1]
    if d < 0.65:
        r.poly([(t_end[0] - 6, t_end[1] + 2), (t_end[0] + 3, t_end[1] + 5), (t_end[0] + 1, t_end[1] - 4)], GOLD[-1], OUTLINE)
    else:
        r.poly([(t_end[0] - 5, t_end[1] + 1), (t_end[0] + 2, t_end[1] + 3), (t_end[0], t_end[1] - 3)], SLATE[2], OUTLINE)

    # 2. Far (upper-back) swept triangular manta wing with curved leading and trailing edges.
    far_tip = (x - 16 - 4 * curl, y + 35 + flap * 0.8 - 13 * curl)
    r.poly([
        (x + 16, y + 7 - 2 * curl),
        (x + 5, y + 19 + flap * 0.35 - 5 * curl),
        (x - 5, y + 29 + flap * 0.6 - 9 * curl),
        far_tip,
        (x - 20, y + 22 + flap * 0.45 - 7 * curl),
        (x - 21, y + 11 + flap * 0.2 - 4 * curl),
        (x - 16, y + 3 - curl),
    ], AZURE[1], OUTLINE)
    r.poly([
        (x + 12, y + 7 - 2 * curl),
        (x + 2, y + 17 + flap * 0.3 - 5 * curl),
        (far_tip[0] + 3, far_tip[1] - 4),
        (x - 16, y + 12 + flap * 0.25 - 4 * curl),
        (x - 12, y + 4 - curl),
    ], AZURE[2], None)
    vein_col = (GOLD[-1] if s > 0.2 else GOLD[3]) if d < 0.65 else SLATE[2]
    r.line([(x + 8, y + 7 - curl), (x - 4, y + 18 + flap * 0.4 - 5 * curl), (far_tip[0] + 3, far_tip[1] - 3)], vein_col, 2)
    if d < 0.65:
        r.ball(x - 4, y + 18 + flap * 0.4, 2.5, 2.5, TEAL)

    # 3. Characteristic paired manta cephalic horn-lobes curving forward (+x) at the front of the head.
    r.poly([
        (x + 15, y + 8 - curl),
        (x + 26 + 3 * s, y + 12 - 3 * curl),
        (x + 31 + 3 * s, y + 8 - 2 * curl),
        (x + 25 + 3 * s, y + 5 - 2 * curl),
        (x + 17, y + 3 - curl),
    ], AZURE[2], OUTLINE)
    r.poly([
        (x + 14, y - 3 + curl),
        (x + 25 + 3 * s, y - 3 + curl),
        (x + 30 + 3 * s, y - 5 + 2 * curl),
        (x + 24 + 3 * s, y - 9 + 3 * curl),
        (x + 13, y - 8 + 2 * curl),
    ], AZURE[2], OUTLINE)

    # 4. Seamless central diamond manta body & pale pearl ventral gill-plate underside.
    r.poly([
        (x - 18, y + 4 - curl),
        (x + 4, y + 12 - 2 * curl),
        (x + 22, y + 4 - curl),
        (x + 19, y - 8 + 2 * curl),
        (x - 2, y - 12 + 3 * curl),
        (x - 18, y - 4 + curl),
    ], AZURE[2], OUTLINE)
    r.poly([
        (x - 12, y - 3 + curl),
        (x + 19, y - 1),
        (x + 16, y - 8 + 2 * curl),
        (x - 4, y - 11 + 2 * curl),
    ], PEARL[2], OUTLINE)
    for gx in (-2, 3, 8, 13):
        r.line([(x + gx, y - 4 + curl), (x + gx + 2, y - 8 + 2 * curl)], AZURE[0], 1)

    # 5. Violet dorsal spine crest and fierce storm-lit manta eye + brow.
    r.poly([
        (x - 13, y + 5 - curl),
        (x + 6, y + 9 - 2 * curl),
        (x + 17, y + 4 - curl),
        (x + 4, y + 1 - curl),
    ], VIOLET[2], None)
    ex, ey = x + 13, y + 2 - curl
    r.poly([(ex - 5, ey + 4), (ex + 5, ey + 2), (ex + 4, ey - 3), (ex - 4, ey - 2)], OUTLINE)
    if d < 0.65:
        r.poly([(ex - 3, ey + 2), (ex + 3, ey + 1), (ex + 2, ey - 1), (ex - 2, ey - 1)], TEAL[-1] if s > 0.2 else GOLD[-1])
    r.line([(ex - 5, ey + 4), (ex + 5, ey + 2)], AZURE[0], 2)

    # 6. Near (lower-front) swept triangular manta wing with broad root matching the far wing.
    near_tip = (x - 14 - 3 * curl, y - 31 + flap * 0.55 + 12 * curl)
    r.poly([
        (x + 7, y - 4 + curl),
        (x, y - 15 + flap * 0.25 + 5 * curl),
        (x - 6, y - 24 + flap * 0.45 + 9 * curl),
        near_tip,
        (x - 20, y - 20 + flap * 0.35 + 8 * curl),
        (x - 20, y - 10 + flap * 0.18 + 4 * curl),
        (x - 15, y - 2 + curl),
    ], AZURE[2], OUTLINE)
    r.poly([
        (x + 5, y - 5 + curl),
        (x - 1, y - 15 + flap * 0.25 + 5 * curl),
        (near_tip[0] + 2, near_tip[1] + 4),
        (x - 16, y - 12 + flap * 0.2 + 4 * curl),
        (x - 11, y - 3 + curl),
    ], AZURE[3], None)
    r.line([(x + 4, y - 5 + curl), (x - 4, y - 16 + flap * 0.3 + 5 * curl), (near_tip[0] + 2, near_tip[1] + 3)], vein_col, 2)
    if d < 0.65:
        r.ball(x - 4, y - 15 + flap * 0.3, 2.5, 2.5, TEAL)

    # 7. Storm-orb charging between the cephalic horn-lobes on wind-up and jagged lightning bolt on strike.
    if w > 0.15 and d == 0:
        orb_r = int(round(3 + 4 * w))
        r.ball(x + 30, y + 2, orb_r, orb_r, GOLD)
        r.ball(x + 30, y + 2, max(2, orb_r - 2), max(2, orb_r - 2), TEAL)
    if s > 0.05 and d == 0:
        reach = int(round(14 + 24 * s))
        bx0, by0 = x + 28, y + 1
        pts = [(bx0, by0), (bx0 + reach * 0.35, by0 + 5), (bx0 + reach * 0.68, by0 - 4), (bx0 + reach, by0 + 1)]
        r.line(pts, GOLD[-1], 4)
        r.line(pts, TEAL[-1], 2)
    return a


def guard(setup, clip, n):
    a, r, w, s, d, ph, b = setup('thunder_guard', clip, n, (0, 10), -0.40)
    cy = 28 + b - 14 * d
    hx = 3 + 7 * s - 5 * w
    hy = 52 + b - 22 * d
    # Two planted slate-and-iron greaves on the ground row.
    for i, x in enumerate((-11, 11)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 13 + lift), (x + step - 9 * d, 3 + lift)], SLATE, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, AMBER)
    # Heavy slate cuirass with azure storm-tabard and brass lightning ribs.
    r.poly([(-18, cy - 8), (-21, cy + 14), (-6, cy + 21), (18, cy + 14), (17, cy - 8)], SLATE[2], OUTLINE)
    r.poly([(-8, cy + 12), (9, cy + 12), (7, cy - 8), (-7, cy - 8)], AZURE[1], OUTLINE)
    for yy in (-2, 6, 13):
        r.line([(-14, cy + yy), (14, cy + yy)], GOLD[1], 2)
    r.ball(-17, cy + 12, 8, 6, SLATE)
    r.ball(16, cy + 12, 8, 6, SLATE)
    # Angular slate barbute helm with golden lightning-rod crest, glaring crimson eye-slits and iron grill.
    r.poly([(hx - 3, hy + 9), (hx + 1, hy + 25 - 6 * d), (hx + 5, hy + 9)], GOLD[2], OUTLINE)
    r.ball(hx, hy, 12, 11, SLATE)
    r.poly([(hx - 11, hy + 5), (hx + 12, hy + 5), (hx + 10, hy - 2), (hx - 9, hy - 2)], OUTLINE)
    if d < 0.65:
        for dx in (-4, 5):
            r.line([(hx + dx - 2, hy + 2), (hx + dx + 2, hy + 1)], TEAL[-1], 2)
    r.poly([(hx - 8, hy - 3), (hx + 9, hy - 3), (hx + 7, hy - 9), (hx - 6, hy - 9)], SLATE[1], OUTLINE)
    for gx in (-4, 0, 4):
        r.line([(hx + gx, hy - 4), (hx + gx, hy - 8)], OUTLINE, 1)
    # Far arm braces a hexagonal Slatebound Tower Shield emblazoned with a golden lightning bolt.
    sx, sy = -24 - 4 * w + 5 * s - 6 * d, cy + 5 + 3 * w - 8 * d
    r.limb([(-14, cy + 10), (-20, cy + 5), (sx, sy)], SLATE, 5)
    r.poly([
        (sx - 11, sy + 14), (sx, sy + 18), (sx + 11, sy + 14),
        (sx + 11, sy - 12), (sx, sy - 17), (sx - 11, sy - 12),
    ], SLATE[2], OUTLINE)
    r.poly([(sx - 2, sy + 12), (sx + 4, sy + 2), (sx, sy + 2), (sx + 3, sy - 11), (sx - 4, sy - 1), (sx, sy - 1)], GOLD[3], OUTLINE)
    # Near arm swings the flanged Storm-Mace (teal electric core shuts off on death).
    hand = (20 + 24 * s - 9 * w, cy + 8 + 16 * w - 7 * s - 8 * d)
    r.limb([(13, cy + 10), (18 + 8 * s, cy + 4), hand], SLATE, 5)
    ang = 0.12 - 0.50 * w + 1.22 * s + 0.80 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 24, hand[1] + vy * 24)
    r.limb([(hand[0] - vx * 10, hand[1] - vy * 10), tip], AMBER, 3)
    r.ball(tip[0], tip[1], 9, 9, SLATE)
    r.ball(tip[0], tip[1], 5, 5, TEAL if d < 0.65 else SLATE)
    return a


def conductor(setup, clip, n):
    a, r, w, s, d, ph, b = setup('thunder_conductor', clip, n, (0, 10), -0.36)
    cy = 28 + b - 13 * d
    hx = 2 + 7 * s - 5 * w
    hy = 53 + b - 21 * d
    hem = math.sin(ph) * 3 if clip == 'walk' else b * 0.4
    # Planted boots and copper-hemmed violet storm-conductor greatcoat.
    for i, x in enumerate((-10, 10)):
        step = math.sin(ph + i * math.pi) * 3.5 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4 if clip == 'walk' else 0
        r.ball(x + step, 3 + lift, 6, 3, BROWN)
    r.poly([(-19 - 4 * d, 3), (-14, cy + 15), (14, cy + 15), (20 + 4 * d, 3), (hem, 5)], PURPLE[1], OUTLINE)
    r.ball(0, cy + 2, 14, 17 * (1 - 0.32 * d), PURPLE)
    r.line([(-16, 6), (16, 6)], AMBER[2], 3)
    # Two copper Tesla coils mounted on the shoulders; teal arcs bridge them while alive.
    for side in (-1, 1):
        cx_c = side * 16 + (3 * s - 2 * w) * 0.4
        cy_c = cy + 16 - 4 * d
        r.ball(cx_c, cy_c, 7, 10, AMBER)
        r.line([(cx_c - 5, cy_c + 3), (cx_c + 5, cy_c + 3)], GOLD[3], 2)
        r.line([(cx_c - 5, cy_c - 2), (cx_c + 5, cy_c - 2)], GOLD[3], 2)
        if d < 0.65:
            r.ball(cx_c, cy_c + 9, 4, 4, TEAL)
    # Wild shock-white hair and gaunt scarred face with blazing eyes and sneering fanged mouth.
    r.ball(hx - 3, hy + 8 - 2 * d, 15, 12, PEARL)
    for k, ang_h in enumerate((1.1, 1.55, 2.0, 2.45)):
        px_h = hx - 2 + math.cos(ang_h) * 18
        py_h = hy + 6 + math.sin(ang_h) * (15 - 3 * d)
        r.poly([(hx - 6 + k * 3, hy + 8), (px_h, py_h), (hx - 1 + k * 3, hy + 8)], PEARL[3], OUTLINE)
    r.ball(hx, hy, 11, 11, BONE)
    for side, dx in ((-1, -5), (1, 5)):
        ex = hx + dx
        r.poly([(ex - 4, hy + 3), (ex + 3, hy + 2 - side), (ex + 3, hy - 2), (ex - 3, hy - 1)], OUTLINE)
        if d < 0.65:
            r.line([(ex - 2, hy + 1), (ex + 2, hy)], TEAL[-1], 2)
    r.poly([(hx - 5, hy - 4), (hx + 6, hy - 4), (hx + 5, hy - 8 - 3 * s), (hx - 4, hy - 8 - 3 * s)], MAROON[0], OUTLINE)
    for fx in (-3, 2):
        r.poly([(hx + fx, hy - 4), (hx + fx + 2, hy - 4), (hx + fx + 1, hy - 7)], WHITE)
    # Far arm holds a coppertuning capacitor fork; near arm thrusts the Lightning Rod Staff.
    sx, sy = -20 - 4 * w + 4 * s - 5 * d, cy + 7 - 7 * d
    r.limb([(-12, cy + 11), (-17, cy + 6), (sx, sy)], PURPLE, 4)
    r.ball(sx, sy, 6, 6, AMBER)
    hand = (19 + 24 * s - 9 * w, cy + 10 + 15 * w - 6 * s - 7 * d)
    r.limb([(12, cy + 11), (17 + 7 * s, cy + 5), hand], PURPLE, 4)
    ang = 0.14 - 0.48 * w + 1.18 * s + 0.75 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 25, hand[1] + vy * 25)
    r.limb([(hand[0] - vx * 10, hand[1] - vy * 10), tip], AMBER, 3)
    r.ball(tip[0], tip[1], 7, 7, GOLD)
    if d < 0.65:
        r.ball(tip[0], tip[1], 4.5, 4.5, TEAL)
        if s > 0.05 or w > 0.2:
            r.poly([tip, (tip[0] + 14 * s + 4, tip[1] + 5), (tip[0] + 8 * s, tip[1] - 6)], TEAL[-1], OUTLINE)
    return a


def bastion(setup, clip, n):
    a, r, w, s, d, ph, b = setup('thunder_bastion', clip, n, (0, 10), -0.44)
    cy = 29 + b - 15 * d
    hx = 3 + 7 * s - 5 * w
    hy = 54 + b - 24 * d
    # Massive basalt-slate pillar legs with bronze ankle bands planted on the ground row.
    for i, x in enumerate((-13, 13)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 6 * d, 14 + lift), (x + step - 10 * d, 3 + lift)], SLATE, 7)
        r.ball(x + step - 10 * d, 3 + lift, 8, 3, AMBER)
    # Fortress torso with crenellated turret pauldrons and a turquoise storm-furnace core (shuts off on death).
    r.poly([(-22, cy - 9), (-26, cy + 16), (-7, cy + 23), (22, cy + 16), (20, cy - 9)], SLATE[2], OUTLINE)
    for side in (-1, 1):
        px = side * 22
        r.ball(px, cy + 14, 10, 8, SLATE)
        for m in (-4, 4):
            r.poly([(px + m - 2, cy + 18), (px + m + 2, cy + 18), (px + m + 2, cy + 24), (px + m - 2, cy + 24)], AMBER[2], OUTLINE)
    r.ball(2, cy + 5, 8, 8, AMBER)
    r.ball(2, cy + 5, 5, 5, TEAL if d < 0.65 else SLATE)
    # Crenellated fortress head with a brass lightning spire, three vertical furnace-slit eyes and portcullis jaw.
    r.poly([(hx - 14, hy - 8), (hx - 15, hy + 11), (hx + 15, hy + 11), (hx + 14, hy - 8)], SLATE[2], OUTLINE)
    for k in range(-12, 13, 8):
        r.poly([(hx + k, hy + 10), (hx + k + 5, hy + 10), (hx + k + 5, hy + 17 - 3 * d), (hx + k, hy + 17 - 3 * d)], SLATE[3], OUTLINE)
    r.poly([(hx - 2, hy + 15), (hx + 1, hy + 26 - 6 * d), (hx + 4, hy + 15)], AMBER[3], OUTLINE)
    for dx in (-6, 1, 8):
        r.poly([(hx + dx - 2, hy + 5), (hx + dx + 2, hy + 5), (hx + dx + 2, hy - 1), (hx + dx - 2, hy - 1)], OUTLINE)
        if d < 0.65:
            r.line([(hx + dx, hy + 4), (hx + dx, hy)], TEAL[-1], 2)
    r.poly([(hx - 10, hy - 3), (hx + 11, hy - 3), (hx + 10, hy - 9), (hx - 9, hy - 9)], AMBER[1], OUTLINE)
    for gx in (-6, -1, 4, 8):
        r.line([(hx + gx, hy - 4), (hx + gx, hy - 8)], OUTLINE, 1)
    # Far arm braces a heavy iron-and-brass bastion bulwark; near arm slams a colossal Pylon Hammer.
    sx, sy = -27 - 4 * w + 4 * s - 6 * d, cy + 5 - 8 * d
    r.limb([(-18, cy + 11), (-24, cy + 5), (sx, sy)], SLATE, 6)
    r.ball(sx, sy, 10, 13, AMBER)
    r.ball(sx, sy, 6, 9, SLATE)
    hand = (23 + 23 * s - 9 * w, cy + 8 + 17 * w - 8 * s - 8 * d)
    r.limb([(17, cy + 11), (21 + 8 * s, cy + 4), hand], SLATE, 6)
    ang = 0.15 - 0.52 * w + 1.25 * s + 0.82 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 24, hand[1] + vy * 24)
    r.limb([(hand[0] - vx * 10, hand[1] - vy * 10), tip], AMBER, 4)
    r.poly([
        (tip[0] - 11, tip[1] - 10), (tip[0] + 12, tip[1] - 10),
        (tip[0] + 12, tip[1] + 10), (tip[0] - 11, tip[1] + 10),
    ], SLATE[2], OUTLINE)
    r.ball(tip[0], tip[1], 5, 5, TEAL if d < 0.65 else AMBER)
    return a


def heart(setup, clip, n):
    a, r, w, s, d, ph, b = setup('thunder_heart', clip, n, (0, 28), 0.25)
    drift = math.sin(ph) * 2 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 54 + b + 6 * w - 6 * s - 22 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    spin = (ph if clip in ('idle', 'walk') else (1.4 * s - 0.6 * w)) * (1 - d)
    # Two intersecting steel-and-bronze stormgate containment rings; collapse outward into a ring heap on death.
    for k, (rx, ry, ang0, ramp) in enumerate((
        (33, 14, 0.22, SLATE),
        (27, 23, -0.85, AMBER),
    )):
        ang = (ang0 + math.sin(spin + k) * 0.18) * (1 - 0.65 * d)
        ry_d = ry * (1 - 0.55 * d)
        cx_r = x + (k * 2 - 1) * 6 * d
        cy_r = y - 4 * d
        r.ball(cx_r, cy_r, rx, max(5, ry_d), ramp, ang)
        if d < 0.72:
            r.ball(cx_r, cy_r, max(4, rx - 5), max(3, ry_d - 4), PURPLE if k == 0 else VIOLET, ang)
    # Faceted violet-and-purple Heart of the Stormgate crystal with three crown spires; drains on death.
    core_scale = 1 - 0.35 * d
    for k in (-1, 0, 1):
        sx = x + k * 9
        sy = y + (25 if k == 0 else 20) * core_scale
        r.poly([(sx - 4, y + 10 * core_scale), (sx, sy), (sx + 4, y + 10 * core_scale)], PURPLE[3], OUTLINE)
    r.ball(x, y, 19 * core_scale, 20 * core_scale, PURPLE)
    r.ball(x - 2, y + 3, 12 * core_scale, 13 * core_scale, VIOLET if d < 0.65 else SLATE)
    # Four orbiting golden lightning pylons and stormgate lance on attack; extinguish on death.
    if d < 0.65:
        for k in range(4):
            ang = spin + k * math.pi * 0.5
            px = x + math.cos(ang) * 31
            py = y + math.sin(ang) * 15
            r.poly([(px - 3, py + 7), (px + 3, py + 7), (px, py - 8)], GOLD[3], OUTLINE)
            r.ball(px, py, 3.5, 3.5, TEAL)
    if s > 0.05 or w > 0.2:
        reach = 22 + 26 * s - 8 * w
        r.poly([(x + 14, y + 6), (x + reach, y), (x + 14, y - 6)], GOLD[-1], OUTLINE)
        if d < 0.65:
            r.line([(x + 16, y), (x + reach - 3, y)], TEAL[-1], 2)
    # Stormgate face on the crystal core: diamond third eye, two jagged V-slit eyes and crystal-fanged maw.
    if d < 0.75:
        r.poly([(x - 1, y + 9), (x + 3, y + 14), (x + 7, y + 9), (x + 3, y + 4)], OUTLINE)
        if d < 0.65:
            r.line([(x + 3, y + 12), (x + 3, y + 6)], TEAL[-1], 2)
        for side, dx in ((-1, -7), (1, 9)):
            ex = x + dx
            r.poly([(ex - 4, y + 3), (ex + 4, y + 2 - side), (ex + 3, y - 2), (ex - 3, y - 1)], OUTLINE)
            if d < 0.65:
                r.line([(ex - 2, y + 1), (ex + 2, y)], TEAL[-1], 2)
        open_m = 3 + 5 * s + 2 * w
        r.poly([(x - 8, y - 5), (x + 10, y - 5), (x + 7, y - 6 - open_m), (x - 6, y - 6 - open_m)], OUTLINE)
        for fx in (-4, 1, 6):
            r.poly([(x + fx, y - 5), (x + fx + 2, y - 5), (x + fx + 1, y - 8)], WHITE)
    return a
