"""Eight articulated Seed Vault creatures in y-up coordinates; props follow their grips."""
import math
from astral_slime_redraw import (
    OUTLINE, WHITE, BONE, PEARL, GOLD, GREEN, LEAF, TEAL,
    AZURE, SLATE, PURPLE, VIOLET, CRIMSON, MAROON, BROWN, OLIVE, PINK, CORAL, AMBER,
)


def mote(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_mote', clip, n, (0, 22))
    drift = math.sin(ph) * 2.5 if clip == 'walk' else 0
    x = 20 * s - 9 * w + drift
    y = 50 + b + 6 * w - 6 * s - 16 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    # In death the rigid seed husk splits along its seam into two tilted halves on the ground.
    if d < 0.35:
        r.taper([(x, y - 11), (x - 3 + drift * 0.5, y - 19), (x - 5, y - 23)], BROWN, 3, 1)
        r.ball(x, y, 15 + 2 * s, 18 - 2 * d, AMBER)
        r.ball(x - 3, y + 4, 8, 10, GOLD)
        r.line([(x + 1, y + 15), (x + 3, y + 3), (x + 1, y - 14)], BROWN[0], 2)
    else:
        sep = (d - 0.25) * 14
        for side in (-1, 1):
            hx = x + side * sep
            hy = y - 4 * d
            r.taper([(hx, hy - 7 * (1 - 0.3 * d)), (hx - side * 3, hy - 20 * (1 - 0.35 * d))], BROWN, 2, 1)
            r.ball(hx, hy, 11, 13 * (1 - 0.35 * d), AMBER, side * 0.45 * d)
            r.poly([
                (hx - side * 2, hy + 10 * (1 - 0.3 * d)),
                (hx + side * 6, hy + 4),
                (hx + side * 4, hy - 9 * (1 - 0.3 * d)),
                (hx - side * 3, hy - 7 * (1 - 0.3 * d)),
            ], BROWN[0], OUTLINE)
    # Twin sprout leaves on top: rear back on wind-up, slash forward on strike, wilt flat on death.
    stem_top = (x + 6 * s - 4 * w + 8 * d, y + 25 * (1 - 0.55 * d) + 5 * w - 4 * s)
    r.limb([(x, y + 14 * (1 - 0.45 * d)), stem_top], GREEN, 2)
    for side, ang0 in ((-1, 0.55), (1, -0.35)):
        lx = stem_top[0] + side * (11 + 4 * w) + (10 * s if side > 0 else 3 * s)
        ly = stem_top[1] + (6 + 5 * w - 6 * s) * (1 - 0.85 * d) - 4 * d
        r.ball((stem_top[0] + lx) * 0.5, (stem_top[1] + ly) * 0.5, 7, 3.5, LEAF, ang0 * (1 - d))
        r.line([stem_top, (lx, ly)], GREEN[0], 1)
    if d < 0.7:
        # Slanted triangular seed-slit eyes under an angry husk brow, plus a split fanged mouth.
        for side, dx in ((-1, -5), (1, 6)):
            ex = x + dx
            r.poly([(ex - 4, y + 5), (ex + 4, y + 3 - side), (ex + 3, y - 1), (ex - 3, y)], GOLD[-1], OUTLINE)
            r.line([(ex, y + 4), (ex, y)], BROWN[0], 2)
        r.line([(x - 10, y + 8), (x + 1, y + 4), (x + 11, y + 8)], BROWN[0], 2)
        open_m = 2 + 4 * s + 2 * w
        r.poly([(x - 6, y - 5), (x + 8, y - 4), (x + 6, y - 5 - open_m), (x - 4, y - 6 - open_m)], BROWN[0], OUTLINE)
        for fx in (-2, 4):
            r.poly([(x + fx, y - 5), (x + fx + 2, y - 5), (x + fx + 1, y - 8)], BONE[-1])
    return a


def amberwing(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_amberwing', clip, n, (0, 34), 0.85)
    x = 20 * s - 8 * w + (math.sin(ph) * 2 if clip == 'walk' else 0)
    y = 54 + b + 6 * w - 6 * s - 26 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    flap = (0.55 + 0.22 * math.sin(ph * 1.6)) if clip in ('idle', 'walk') else (0.52 + 0.45 * w - 0.20 * s)
    span = max(0.18, flap * (1 - 0.75 * d))
    # Four layered amber and honey-gold wings with dark crimson-centered ocelli.
    for side in (-1, 1):
        root = (x + side * 4, y + 2)
        wx = x + side * (12 + 34 * span)
        wy = y + 14 + 10 * w - 6 * s - 14 * d
        r.poly([
            root,
            (x + side * 10, y + 20 - 8 * d),
            (wx, wy + 12 - 6 * d),
            (wx + side * 6, wy - 8),
            (x + side * 14, y - 14),
        ], AMBER[2], OUTLINE)
        r.poly([
            root,
            (x + side * 9, y - 4),
            (wx - side * 3, wy - 10),
            (x + side * 11, y - 24 + 8 * d),
        ], GOLD[2], OUTLINE)
        r.line([root, (wx - side * 2, wy + 4)], BROWN[0], 2)
        ox, oy = wx - side * 5, wy + 2
        r.ball(ox, oy, max(2.5, 5.5 * span), 6, BROWN)
        r.ellipse(ox, oy, max(1.5, 3 * span), 3.5, GOLD[-1])
        r.ellipse(ox, oy, 1.5, 2, CRIMSON[1])
        # Feathery antennae droop on death.
        r.taper([(x + side * 4, y + 18), (x + side * (10 + 4 * w), y + 30 - 14 * d), (x + side * 15, y + 33 - 18 * d)], BROWN, 2, 1)
    # Segmented honey-amber abdomen and furry thorax.
    r.ball(x - 3, y - 8, 8, 15 * (1 - 0.25 * d), AMBER)
    for i in range(4):
        yy = y - 16 + i * 5
        r.line([(x - 8, yy), (x + 2, yy)], BROWN[0], 2)
    r.ball(x + 1, y + 6, 9, 9, BROWN)
    r.ball(x + 3, y + 14, 8, 7, AMBER)
    # Six jointed legs curl inward beneath the thorax on death.
    for side in (-1, 1):
        for j in range(3):
            ly = y + 4 - j * 5
            r.limb([(x + side * 4, ly), (x + side * (10 - 4 * d), ly - 4 + 3 * d), (x + side * (7 - 5 * d), ly - 9 + 6 * d)], BROWN, 2)
    # Faceted crimson compound eyes, sharp mandibles, and a coiling golden proboscis.
    for side in (-1, 1):
        ex = x + 3 + side * 5
        r.poly([(ex - 3, y + 17), (ex + 3, y + 18), (ex + 4, y + 12), (ex - 2, y + 11)], CRIMSON[1], OUTLINE)
        if d < 0.7:
            r.line([(ex - 1, y + 16), (ex + 2, y + 13)], GOLD[-1], 1)
        r.poly([(x + 3 + side * 3, y + 9), (x + 3 + side * 6, y + 9), (x + 3 + side * (4 + 3 * s), y + 4)], BONE[3], OUTLINE)
    r.taper([
        (x + 5, y + 10),
        (x + 12 + 12 * s - 5 * w, y + 5 + 6 * w - 2 * s),
        (x + 16 + 24 * s - 7 * w, y + 9 - 6 * s),
    ], GOLD, 3, 1)
    return a


def rootguard(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_rootguard', clip, n, (0, 10), -0.42)
    cy = 28 + b - 15 * d
    hx = 3 + 8 * s - 5 * w
    hy = 52 + b - 24 * d
    for i, x in enumerate((-11, 11)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 6 * d, 13 + lift), (x + step - 10 * d, 3 + lift)], BROWN, 6)
        r.ball(x + step - 10 * d, 3 + lift, 7, 3, BROWN)
    # Broad bark-plate torso with a glowing golden sap-core on the chest.
    r.poly([(-18, cy - 8), (-21, cy + 14), (-6, cy + 21), (18, cy + 14), (17, cy - 8)], BROWN[2], OUTLINE)
    for yy in (-2, 6, 13):
        r.line([(-15, cy + yy), (14, cy + yy - 1)], BROWN[0], 2)
    r.ball(2, cy + 6, 6, 7 * (1 - 0.3 * d), GOLD if d < 0.65 else BROWN)
    if d > 0.2:
        r.line([(-7, cy + 16), (0, cy + 6), (-4, cy - 5)], OUTLINE, 2)
    # Carved bark war-helm with three upright leaf-blades, yellow vertical slit eyes and wooden tusks.
    for k, lx in enumerate((-7, 0, 7)):
        r.ball(hx + lx, hy + 15 + (2 if k == 1 else 0) - 5 * d, 3.5, 7 * (1 - 0.4 * d), LEAF, (k - 1) * 0.35)
    r.ball(hx, hy, 13, 11, BROWN)
    r.poly([(hx - 13, hy + 5), (hx + 13, hy + 5), (hx + 10, hy + 10), (hx - 10, hy + 10)], OLIVE[1], OUTLINE)
    for dx in (-5, 6):
        r.poly([(hx + dx - 3, hy + 4), (hx + dx + 3, hy + 3), (hx + dx + 2, hy - 2), (hx + dx - 3, hy - 1)], OUTLINE)
        if d < 0.65:
            r.line([(hx + dx, hy + 3), (hx + dx, hy - 1)], GOLD[-1], 2)
    r.poly([(hx - 9, hy - 4), (hx + 10, hy - 4), (hx + 8, hy - 10), (hx - 7, hy - 10)], BROWN[1], OUTLINE)
    for tx in (-6, 6):
        r.poly([(hx + tx - 2, hy - 5), (hx + tx + 2, hy - 5), (hx + tx + 1, hy - 1)], BONE[3], OUTLINE)
    # Far arm holds a rigid ribbed root-buckler shield.
    sx = -26 - 4 * w + 5 * s - 6 * d
    sy = cy + 6 + 5 * w - 10 * d
    r.limb([(-15, cy + 11), (-22, cy + 5), (sx, sy)], BROWN, 5)
    r.ball(sx, sy, 12, 15, BROWN, 0.4 * d)
    r.ball(sx, sy, 8, 10, OLIVE, 0.4 * d)
    for dx in (-5, 0, 5):
        r.line([(sx + dx, sy + 10), (sx + dx, sy - 10)], BROWN[0], 1)
    # Near arm swings a heavy knotted heartroot club with a sap-amber head.
    hand = (22 + 23 * s - 10 * w, cy + 8 + 18 * w - 9 * s - 8 * d)
    r.limb([(14, cy + 11), (19 + 8 * s, cy + 3), hand], BROWN, 5)
    ang = 0.10 - 0.55 * w + 1.25 * s + 0.85 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 26, hand[1] + vy * 26)
    r.taper([(hand[0] - vx * 6, hand[1] - vy * 6), tip], BROWN, 4, 7)
    r.ball(tip[0], tip[1], 8, 7, BROWN)
    r.ball(tip[0] + 2, tip[1] + 2, 4, 4, AMBER if d < 0.7 else BROWN)
    r.ball(tip[0] - 3, tip[1] + 5, 3, 5, LEAF)
    return a


def warden(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_warden', clip, n, (0, 10), -0.38)
    cy = 27 + b - 13 * d
    hx = 2 + 7 * s - 5 * w
    hy = 52 + b - 22 * d
    hem = math.sin(ph) * 3 if clip == 'walk' else b * 0.4
    if clip == 'walk':
        hy += math.cos(ph) * 1.2
    # Concentric tree-ring halo behind the shoulders and head; stays rigid as it tips.
    rx, ry = hx - 3 - 5 * d, hy + 2 - 4 * d
    r.ball(rx, ry, 20, 20, GOLD)
    r.ball(rx, ry, 14, 14, BROWN)
    r.ball(rx, ry, 9, 9, AMBER)
    # Two planted wooden feet under the golden-bark robe.
    for i, x in enumerate((-10, 10)):
        step = math.sin(ph + i * math.pi) * 3.5 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4 if clip == 'walk' else 0
        r.ball(x + step, 3 + lift, 6, 3, BROWN)
    r.poly([(-17 - 5 * d, 3), (-11, cy + 14), (12, cy + 14), (18 + 5 * d, 3), (hem, 5)], AMBER[2], OUTLINE)
    r.ball(0, cy + 2, 13, 17 * (1 - 0.35 * d), AMBER)
    for yy in (-6, 2, 10):
        r.line([(-12, cy + yy), (12, cy + yy)], BROWN[1], 2)
    # Hooded wooden mask with three glowing emerald ring-eyes and a stern carved scowl.
    r.ball(hx, hy, 12, 13, BROWN)
    r.ball(hx + 2, hy - 1, 9, 10, BONE)
    r.poly([(hx - 1, hy + 9), (hx + 3, hy + 13), (hx + 7, hy + 9), (hx + 3, hy + 5)], GREEN[1], OUTLINE)
    if d < 0.65:
        r.ellipse(hx + 3, hy + 9, 1.5, 2.5, LEAF[-1])
    for dx in (-3, 7):
        r.poly([(hx + dx - 3, hy + 2), (hx + dx + 3, hy + 4), (hx + dx + 2, hy), (hx + dx - 2, hy - 1)], GREEN[0], OUTLINE)
        if d < 0.65:
            r.ellipse(hx + dx, hy + 2, 1.5, 1.5, LEAF[-1])
    r.line([(hx - 2, hy - 5), (hx + 3, hy - 3), (hx + 7, hy - 6)], OUTLINE, 2)
    # Far arm carries a rigid concentric tree-ring buckler.
    sx = -22 - 4 * w + 4 * s - 5 * d
    sy = cy + 6 - 8 * d
    r.limb([(-11, cy + 11), (-18, cy + 6), (sx, sy)], AMBER, 4)
    r.ball(sx, sy, 11, 11, GOLD)
    r.ball(sx, sy, 7, 7, BROWN)
    r.ball(sx, sy, 3.5, 3.5, AMBER)
    # Near arm wields the Ring Staff; raises high on wind-up and thrusts far forward on strike.
    hand = (20 + 24 * s - 9 * w, cy + 10 + 15 * w - 6 * s - 7 * d)
    r.limb([(11, cy + 11), (16 + 8 * s, cy + 4), hand], AMBER, 4)
    ang = 0.08 - 0.45 * w + 1.15 * s + 0.75 * d
    vx, vy = math.sin(ang), math.cos(ang)
    head_pt = (hand[0] + vx * 22, hand[1] + vy * 22)
    r.limb([(hand[0] - vx * 16, hand[1] - vy * 16), head_pt], BROWN, 3)
    r.ball(head_pt[0], head_pt[1], 9, 9, GOLD)
    r.ball(head_pt[0], head_pt[1], 5, 5, BROWN)
    r.ball(head_pt[0], head_pt[1], 3, 3, LEAF if d < 0.7 else BROWN)
    return a


def germinator(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_germinator', clip, n, (0, 12), -0.18)
    cy = 34 + b + 4 * w - 4 * s - 16 * d
    lean = 10 * s - 5 * w
    # Four jointed vine-stalk legs planted on the ground row; wilt outward on death.
    for i, x in enumerate((-22, -8, 8, 22)):
        step = math.sin(ph + i * math.pi * 0.5) * 3.5 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi * 0.5)) * 4.5 if clip == 'walk' else 0
        foot_x = x + step + (4 * d if x >= 0 else -4 * d)
        knee_x = (x * 0.6 + foot_x) * 0.5 + lean * 0.4
        r.limb([(x * 0.55 + lean, cy - 8), (knee_x, 15 + lift - 5 * d), (foot_x, 3 + lift)], GREEN, 5)
        r.ball(foot_x, 3 + lift, 5, 3, LEAF)
    # Two barbed whip-vines coil high on wind-up and lash far ahead on strike.
    for side in (-1, 1):
        vx = lean + side * (22 + 6 * w) + (26 * s if side > 0 else 10 * s)
        vy = cy + 6 + 18 * w - 10 * s - 12 * d
        r.taper([
            (lean + side * 14, cy - 2),
            (vx, vy),
            (vx + (16 * s if side > 0 else -8), vy + 8 * w - 8 * s - 6 * d),
        ], GREEN, 5, 2)
    # Crown of seven carnivorous magenta petals around the upper bulb; wilt outward on death.
    for k in range(7):
        ang = math.pi * (0.12 + 0.76 * k / 6)
        px = lean + math.cos(ang) * (18 + 3 * w + 5 * d)
        py = cy + 12 * (1 - 0.3 * d) + math.sin(ang) * (16 + 4 * w) * (1 - 0.35 * d)
        r.ball(px, py, 6, 9 * (1 - 0.25 * d), PINK, (ang - math.pi * 0.5) * (1 - 0.5 * d))
        r.line([(lean + math.cos(ang) * 10, cy + 10 * (1 - 0.3 * d)), (px, py)], CORAL[1], 1)
    # Bulbous green pod body with dark vertical ribs and a golden brow stigma.
    r.ball(lean, cy, 22 + 3 * d, 20 * (1 - 0.32 * d), LEAF)
    for dx in (-11, 0, 11):
        r.line([(lean + dx, cy + 14 * (1 - 0.3 * d)), (lean + dx * 0.8, cy - 14 * (1 - 0.3 * d))], GREEN[0], 2)
    r.ball(lean + 2, cy + 15 * (1 - 0.3 * d), 5, 5, GOLD if d < 0.7 else BROWN)
    # Four hunter eyes in an arc and a wide thorn-toothed carnivorous maw.
    for dx, dy, sz in ((-10, 6, 3), (-2, 8, 4), (7, 8, 4), (14, 5, 3)):
        ex, ey = lean + dx, cy + dy * (1 - 0.3 * d)
        r.poly([(ex - sz, ey + 2), (ex + sz, ey + 3), (ex + sz - 1, ey - 2), (ex - sz + 1, ey - 2)], VIOLET[0], OUTLINE)
        if d < 0.65:
            r.ellipse(ex + 1, ey, 1.2, 1.5, GOLD[-1])
    gap = (4 + 6 * s + 3 * w) * (1 - 0.5 * d)
    my = cy - 5 * (1 - 0.2 * d)
    r.poly([
        (lean - 12, my + 2),
        (lean + 15, my + 2),
        (lean + 13, my - gap - 3),
        (lean - 10, my - gap - 3),
    ], MAROON[0], OUTLINE)
    for tx in (-8, -2, 4, 10):
        r.poly([(lean + tx, my + 2), (lean + tx + 3, my + 2), (lean + tx + 1, my - 2)], WHITE)
        r.poly([(lean + tx - 1, my - gap - 3), (lean + tx + 2, my - gap - 3), (lean + tx, my - gap + 1)], BONE[-1])
    return a


def worldseed(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_worldseed', clip, n, (0, 14), -0.12)
    cy = 38 + b + 5 * w - 5 * s - 18 * d
    lean = 12 * s - 6 * w
    # Four massive dark-root pillars planted on the ground row; splay outward on death.
    for i, x in enumerate((-23, -8, 8, 23)):
        step = math.sin(ph + i * math.pi * 0.5) * 3.5 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi * 0.5)) * 4 if clip == 'walk' else 0
        fx = x + step + (6 * d if x >= 0 else -6 * d)
        r.limb([(x * 0.6 + lean, cy - 12), ((x + fx) * 0.5 + lean * 0.4, 15 + lift - 5 * d), (fx, 3 + lift)], BROWN, 6)
        r.ball(fx, 3 + lift, 6, 3, BROWN)
    # Two heavy sweeping root-tendril arms on the flanks.
    for side in (-1, 1):
        tx = lean + side * (24 + 6 * w) + (28 * s if side > 0 else 10 * s)
        ty = cy + 2 + 16 * w - 12 * s - 10 * d
        r.taper([(lean + side * 16, cy - 4), (tx, ty), (tx + side * 8 + 12 * s, ty + 8 * w - 8 * s - 6 * d)], BROWN, 6, 2)
    # Ancient golden-brown Worldseed shell: splits apart into two cracked halves on death.
    if d < 0.35:
        r.ball(lean, cy + 4, 22, 26, AMBER)
        r.ball(lean - 5, cy + 10, 12, 16, GOLD)
    else:
        sep = (d - 0.25) * 15
        for side in (-1, 1):
            hx = lean + side * sep
            hy = cy + 2 - 4 * d
            r.ball(hx, hy, 15, 21 * (1 - 0.32 * d), AMBER, side * 0.38 * d)
            r.poly([
                (hx - side * 2, hy + 16 * (1 - 0.3 * d)),
                (hx + side * 7, hy + 3),
                (hx + side * 5, hy - 14 * (1 - 0.3 * d)),
                (hx - side * 3, hy - 12 * (1 - 0.3 * d)),
            ], BROWN[0], OUTLINE)
    # Blazing golden-white vertical fissure and glaring central fissure-eye + two side slit eyes; gutters out on death.
    if d < 0.75:
        r.poly([
            (lean - 2, cy + 24),
            (lean + 5, cy + 10),
            (lean - 4, cy - 2),
            (lean + 4, cy - 14),
            (lean - 1, cy - 4),
            (lean - 7, cy + 10),
        ], GOLD[-1] if s > 0.3 else GOLD[3], OUTLINE)
        # Central blazing fissure eye and two flanking slit eyes.
        r.poly([(lean - 4, cy + 12), (lean + 6, cy + 12), (lean + 3, cy + 4), (lean - 2, cy + 4)], WHITE, OUTLINE)
        r.line([(lean + 1, cy + 11), (lean + 1, cy + 5)], CRIMSON[1], 2)
        for dx, dy in ((-11, 5), (12, 5)):
            r.poly([(lean + dx - 3, cy + dy + 2), (lean + dx + 3, cy + dy + 1), (lean + dx + 2, cy + dy - 2), (lean + dx - 2, cy + dy - 1)], GOLD[-1], OUTLINE)
            r.line([(lean + dx, cy + dy + 1), (lean + dx, cy + dy - 1)], BROWN[0], 1)
        # Jagged furnace-maw in the lower shell.
        r.poly([(lean - 8, cy - 7), (lean + 10, cy - 6), (lean + 7, cy - 13 - 4 * s), (lean - 6, cy - 13 - 4 * s)], BROWN[0], OUTLINE)
        r.ellipse(lean + 1, cy - 10, 4, 2, GOLD[3])
    # World-sprout crowning the apex of the shell; wilts down as the shell splits.
    top_x = lean + 4 * s - 3 * w + 8 * d
    top_y = cy + 30 * (1 - 0.45 * d) + 4 * w
    r.limb([(lean, cy + 24 * (1 - 0.4 * d)), (top_x, top_y + 8 * (1 - 0.6 * d))], GREEN, 3)
    for side, ang0 in ((-1, 0.5), (1, -0.4)):
        lx = top_x + side * 12 + 6 * s
        ly = top_y + (9 - 10 * d)
        r.ball((top_x + lx) * 0.5, (top_y + ly) * 0.5, 8, 4, LEAF, ang0 * (1 - d))
    return a


def sprout(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_sprout', clip, n, (0, 10), 0.62)
    cy = 23 + b + 3 * w - 3 * s - 9 * d
    lean = 14 * s - 6 * w
    # Two stubby dark-root legs trotting along; stay planted in idle.
    for i, x in enumerate((-8, 8)):
        step = math.sin(ph + i * math.pi) * 3.5 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x + lean * 0.4, cy - 6), (x + step + 5 * d, 9 + lift), (x + step + 7 * d, 3 + lift)], BROWN, 4)
        r.ball(x + step + 7 * d, 3 + lift, 5, 3, BROWN)
    # Two clawed root-arms that slash forward on strike.
    for side in (-1, 1):
        ax = lean + side * 12 + (14 * s if side > 0 else -4 * w)
        ay = cy + 2 + 10 * w - 5 * s - 4 * d
        r.limb([(lean + side * 10, cy + 2), (ax, ay)], BROWN, 3)
        r.poly([(ax, ay + 2), (ax + side * 5, ay), (ax, ay - 3)], BONE[3], OUTLINE)
    # Plump golden-amber acorn body with a rough dark-bark acorn cupola cap.
    r.ball(lean, cy + 6, 15, 17 * (1 - 0.22 * d), AMBER)
    r.poly([
        (lean - 16, cy + 13),
        (lean - 12, cy + 22),
        (lean + 12, cy + 22),
        (lean + 16, cy + 13),
        (lean, cy + 10),
    ], BROWN[1], OUTLINE)
    for dx in (-9, -3, 3, 9):
        r.line([(lean + dx, cy + 20), (lean + dx - 2, cy + 13)], BROWN[0], 1)
    # Glowing vertical shell crack and a fierce single cyclops slit-eye under a V-brow.
    r.line([(lean + 2, cy + 14), (lean + 4, cy + 5), (lean + 1, cy - 5)], GOLD[3] if d < 0.7 else BROWN[0], 2)
    if d < 0.7:
        r.poly([(lean - 4, cy + 8), (lean + 8, cy + 8), (lean + 6, cy + 1), (lean - 2, cy + 1)], GOLD[-1], OUTLINE)
        r.line([(lean + 2, cy + 7), (lean + 2, cy + 2)], CRIMSON[0], 2)
        r.line([(lean - 7, cy + 11), (lean + 2, cy + 7), (lean + 10, cy + 11)], BROWN[0], 2)
        r.poly([(lean - 4, cy - 3), (lean + 7, cy - 3), (lean + 5, cy - 7 - 3 * s), (lean - 2, cy - 7 - 3 * s)], BROWN[0], OUTLINE)
        r.poly([(lean + 1, cy - 7 - 3 * s), (lean + 4, cy - 7 - 3 * s), (lean + 2, cy - 4)], BONE[-1])
    # Top twin-leaf sprout.
    sx, sy = lean + 3 * s - 2 * w, cy + 22
    r.limb([(sx, sy), (sx + 4 * d, sy + 9 * (1 - 0.5 * d))], GREEN, 2)
    for side in (-1, 1):
        r.ball(sx + side * 7 + 4 * s, sy + 10 * (1 - 0.55 * d), 6, 3, LEAF, side * 0.4 * (1 - d))
    return a


def treant(setup, clip, n):
    a, r, w, s, d, ph, b = setup('seed_treant', clip, n, (0, 10), -0.36)
    cy = 27 + b - 14 * d
    hx = 2 + 7 * s - 5 * w
    hy = 50 + b - 22 * d
    # Two planted bark-trunk legs.
    for i, x in enumerate((-11, 11)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 5), (x + step * 0.5 - 5 * d, 12 + lift), (x + step - 9 * d, 3 + lift)], BROWN, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, BROWN)
    # Stocky bark torso with a mossy green belly and golden heart-wood knot.
    r.ball(0, cy + 4, 17, 17 * (1 - 0.28 * d), BROWN)
    r.ball(2, cy + 2, 10, 9 * (1 - 0.25 * d), GREEN)
    r.ball(3, cy + 2, 4.5, 4.5, GOLD if d < 0.7 else BROWN)
    if d > 0.2:
        r.line([(-6, cy + 15), (1, cy + 5), (-3, cy - 5)], OUTLINE, 2)
    # Gnarled bark head with a wreath of pink cherry-blossoms, mossy brow, and triangular green eyes.
    r.ball(hx, hy, 13, 11, BROWN)
    for k in range(6):
        ang = math.pi * (0.08 + 0.84 * k / 5)
        bx = hx + math.cos(ang) * 13 + (3 * d if k > 2 else -3 * d)
        by = hy + 5 + math.sin(ang) * 9 * (1 - 0.45 * d) - 5 * d
        r.ball(bx, by, 4.5, 4.5, PINK)
        r.ellipse(bx, by, 1.5, 1.5, GOLD[-1])
    r.limb([(hx - 11, hy + 5), (hx + 1, hy + 2), (hx + 12, hy + 5)], GREEN, 3)
    for dx in (-4, 6):
        r.poly([(hx + dx - 3, hy + 2), (hx + dx + 3, hy + 2), (hx + dx, hy - 2)], OUTLINE)
        if d < 0.65:
            r.ellipse(hx + dx, hy + 1, 1.5, 1.5, LEAF[-1])
    r.poly([(hx - 6, hy - 5), (hx + 8, hy - 5), (hx + 6, hy - 9), (hx - 4, hy - 9)], OUTLINE)
    for tx in (-3, 3):
        r.poly([(hx + tx, hy - 9), (hx + tx + 2, hy - 9), (hx + tx + 1, hy - 6)], BONE[2])
    # Far arm has a heavy mossy gauntlet fist.
    fx = -22 - 4 * w + 4 * s - 5 * d
    fy = cy + 4 - 8 * d
    r.limb([(-14, cy + 10), (-19, cy + 6), (fx, fy)], BROWN, 5)
    r.ball(fx, fy, 7, 7, GREEN)
    # Near arm swings a blossom-studded bark club.
    hand = (21 + 22 * s - 9 * w, cy + 8 + 17 * w - 8 * s - 7 * d)
    r.limb([(14, cy + 10), (18 + 8 * s, cy + 3), hand], BROWN, 5)
    ang = 0.12 - 0.52 * w + 1.22 * s + 0.82 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 24, hand[1] + vy * 24)
    r.taper([(hand[0] - vx * 5, hand[1] - vy * 5), tip], BROWN, 4, 7)
    r.ball(tip[0], tip[1], 7, 6, BROWN)
    for k in range(4):
        ca = k * math.pi * 0.5 + 0.3
        r.ball(tip[0] + math.cos(ca) * 6, tip[1] + math.sin(ca) * 5, 3.5, 3.5, PINK)
    r.ball(tip[0], tip[1], 3, 3, GOLD)
    return a
