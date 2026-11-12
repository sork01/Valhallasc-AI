"""Six articulated Sunken Astrolabe creatures in y-up coordinates; props follow their grips."""
import math
from astral_slime_redraw import (
    OUTLINE, WHITE, BONE, PEARL, GOLD, GREEN, LEAF, TEAL,
    AZURE, SLATE, PURPLE, VIOLET, CRIMSON, MAROON, BROWN, OLIVE, PINK, CORAL, AMBER,
)


def gearling(setup, clip, n):
    a, r, w, s, d, ph, b = setup('astro_gearling', clip, n, (0, 10), -0.42)
    cy = 28 + b - 12 * d
    lean = 10 * s - 5 * w
    spin = (ph if clip in ('idle', 'walk') else (1.2 * s - 0.6 * w)) * (1 - d)
    # Two jointed bronze piston-legs with cog-feet planted on the ground row.
    for i, x in enumerate((-10, 10)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x + lean * 0.4, cy - 8), (x + step * 0.5 - 5 * d, 13 + lift), (x + step - 8 * d, 3 + lift)], BROWN, 5)
        r.ball(x + step - 8 * d, 3 + lift, 6, 3, AMBER)
    # Smaller counter-rotating bronze shoulder cog; detaches beside the hull on death.
    cx2 = lean - 16 - 6 * d
    cy2 = cy + 12 - 16 * d
    r.ball(cx2, cy2, 9, 9, BROWN)
    r.ball(cx2, cy2, 5, 5, GOLD)
    # 9-toothed outer brass gear wheel and bevelled clockwork body.
    for k in range(9):
        ang = spin + k * 2 * math.pi / 9
        tx = lean + math.cos(ang) * 21
        ty = cy + math.sin(ang) * 21 * (1 - 0.22 * d)
        r.ball(tx, ty, 4, 4, GOLD, ang)
    r.ball(lean, cy, 18, 18 * (1 - 0.22 * d), AMBER)
    r.ball(lean - 2, cy + 2, 13, 13 * (1 - 0.22 * d), GOLD)
    # Turquoise aether-core lens in the lower belly; gutters out on death.
    r.ball(lean + 1, cy - 8, 5, 4, TEAL if d < 0.65 else SLATE)
    # Glaring cyan-slit optical lenses in dark sockets and a saw-toothed brass jaw.
    for side, dx in ((-1, -5), (1, 6)):
        ex, ey = lean + dx, cy + 4
        r.poly([(ex - 4, ey + 3), (ex + 4, ey + 2 - side), (ex + 3, ey - 2), (ex - 3, ey - 2)], OUTLINE)
        if d < 0.65:
            r.line([(ex - 2, ey + 1), (ex + 2, ey)], TEAL[-1], 2)
    r.line([(lean - 10, cy + 8), (lean + 1, cy + 4), (lean + 11, cy + 8)], BROWN[0], 2)
    open_m = (2 + 4 * s + 2 * w) * (1 - 0.6 * d)
    r.poly([(lean - 7, cy - 2), (lean + 8, cy - 2), (lean + 7, cy - 4 - open_m), (lean - 6, cy - 4 - open_m)], BROWN[0], OUTLINE)
    for tx in (-4, 0, 4):
        r.poly([(lean + tx, cy - 2), (lean + tx + 2, cy - 2), (lean + tx + 1, cy - 5)], BONE[3])
    # Near arm swings a spinning brass saw-cog blade forward on strike.
    hand = (lean + 16 + 22 * s - 8 * w, cy + 2 + 12 * w - 6 * s - 6 * d)
    r.limb([(lean + 10, cy + 2), hand], BROWN, 4)
    r.ball(hand[0], hand[1], 8, 8, GOLD)
    r.ball(hand[0], hand[1], 4, 4, TEAL if d < 0.65 else BROWN)
    return a


def starling(setup, clip, n):
    a, r, w, s, d, ph, b = setup('astro_starling', clip, n, (0, 26), 0.35)
    drift = math.sin(ph) * 2.5 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 52 + b + 6 * w - 6 * s - 20 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    # Streaming cobalt-and-teal comet tail behind the star; dissipates completely on death.
    if d < 0.65:
        fade = 1 - d / 0.65
        for k in range(4):
            tx = x - 14 - k * 8 - 4 * s + 4 * w
            ty = y + 4 - k * 3 + math.sin(ph + k) * 2
            rx = max(2.0, (9 - k * 1.8) * fade)
            ry = max(1.8, (6 - k * 1.1) * fade)
            r.ball(tx, ty, rx, ry, AZURE if k % 2 == 0 else TEAL)
    # Rigid five-pointed golden star hull: stays intact as it lands on the ground.
    pts = []
    rot = 0.18 * s - 0.12 * w + 0.35 * d
    for k in range(10):
        ang = math.pi / 2 + k * math.pi / 5 + rot
        rad = (24 if k % 2 == 0 else 11)
        pts.append((x + math.cos(ang) * rad, y + math.sin(ang) * rad * (1 - 0.25 * d)))
    r.poly(pts, GOLD[2], OUTLINE)
    r.ball(x, y, 13, 12 * (1 - 0.22 * d), GOLD)
    r.ball(x - 2, y + 3, 7, 6 * (1 - 0.22 * d), AMBER)
    # Stellar lance beam on attack wind-up/strike.
    if s > 0.05 or w > 0.2:
        reach = 18 + 24 * s - 6 * w
        r.poly([(x + 10, y + 4), (x + reach, y + 1), (x + 10, y - 4)], TEAL[-1] if s > 0.3 else GOLD[-1], OUTLINE)
    # Three sharp crimson-and-violet stellar slit eyes and a fanged maw.
    r.poly([(x - 1, y + 9), (x + 2, y + 13), (x + 5, y + 9), (x + 2, y + 5)], CRIMSON[1], OUTLINE)
    for side, dx in ((-1, -5), (1, 6)):
        ex = x + dx
        r.poly([(ex - 4, y + 3), (ex + 3, y + 2 - side), (ex + 3, y - 2), (ex - 3, y - 1)], VIOLET[0], OUTLINE)
        if d < 0.65:
            r.line([(ex - 1, y + 2), (ex + 2, y)], GOLD[-1], 1)
    r.poly([(x - 5, y - 4), (x + 7, y - 4), (x + 5, y - 8 - 3 * s), (x - 4, y - 8 - 3 * s)], MAROON[0], OUTLINE)
    for fx in (-2, 3):
        r.poly([(x + fx, y - 4), (x + fx + 2, y - 4), (x + fx + 1, y - 7)], WHITE)
    return a


def sentinel(setup, clip, n):
    a, r, w, s, d, ph, b = setup('astro_sentinel', clip, n, (0, 10), -0.40)
    cy = 28 + b - 14 * d
    hx = 3 + 7 * s - 5 * w
    hy = 52 + b - 22 * d
    # Brass orbit ring behind the shoulders and head, with an orbiting teal planet bead.
    ox, oy = hx - 2 - 4 * d, hy + 2 - 4 * d
    r.ball(ox, oy, 19, 19, GOLD)
    r.ball(ox, oy, 13, 13, SLATE)
    ang_orb = (ph if clip in ('idle', 'walk') else (1.4 * s - 0.5 * w)) * (1 - d)
    if d < 0.7:
        r.ball(ox + math.cos(ang_orb) * 16, oy + math.sin(ang_orb) * 16, 4, 4, TEAL)
    # Two planted brass greaves on the ground row.
    for i, x in enumerate((-11, 11)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 13 + lift), (x + step - 9 * d, 3 + lift)], AMBER, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, GOLD)
    # Steel clockwork breastplate with brass ribs and a turquoise aether core (shuts off on death).
    r.poly([(-17, cy - 8), (-20, cy + 14), (-5, cy + 20), (17, cy + 14), (16, cy - 8)], SLATE[2], OUTLINE)
    for yy in (-3, 5, 12):
        r.line([(-14, cy + yy), (13, cy + yy)], GOLD[1], 2)
    r.ball(2, cy + 5, 6, 6, TEAL if d < 0.6 else SLATE)
    # Domed steel helm with a single glaring cyan cyclops visor-slit and brass mandible grill.
    r.ball(hx, hy, 12, 11, SLATE)
    r.poly([(hx - 11, hy + 4), (hx + 12, hy + 4), (hx + 10, hy - 1), (hx - 9, hy - 1)], OUTLINE)
    if d < 0.65:
        r.line([(hx - 7, hy + 2), (hx + 9, hy + 2)], TEAL[-1], 2)
        r.ellipse(hx + 3, hy + 2, 2.5, 2, WHITE)
    r.poly([(hx - 8, hy - 3), (hx + 9, hy - 3), (hx + 7, hy - 9), (hx - 6, hy - 9)], GOLD[1], OUTLINE)
    for gx in (-4, 0, 4):
        r.line([(hx + gx, hy - 4), (hx + gx, hy - 8)], OUTLINE, 1)
    # Far arm holds a brass-rimmed steel buckler.
    sx, sy = -23 - 4 * w + 4 * s - 5 * d, cy + 6 - 8 * d
    r.limb([(-14, cy + 10), (-20, cy + 5), (sx, sy)], AMBER, 5)
    r.ball(sx, sy, 10, 12, GOLD)
    r.ball(sx, sy, 6, 8, SLATE)
    # Near arm wields the Orrery Staff topped with a ringed astrolabe sphere.
    hand = (20 + 24 * s - 9 * w, cy + 9 + 16 * w - 7 * s - 8 * d)
    r.limb([(13, cy + 10), (18 + 8 * s, cy + 4), hand], AMBER, 5)
    ang = 0.10 - 0.50 * w + 1.20 * s + 0.80 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 24, hand[1] + vy * 24)
    r.limb([(hand[0] - vx * 12, hand[1] - vy * 12), tip], GOLD, 3)
    r.ball(tip[0], tip[1], 8, 8, GOLD)
    r.ball(tip[0], tip[1], 4.5, 4.5, TEAL if d < 0.65 else SLATE)
    return a


def warden(setup, clip, n):
    a, r, w, s, d, ph, b = setup('astro_warden', clip, n, (0, 10), -0.38)
    cy = 29 + b - 14 * d
    hx = 3 + 8 * s - 5 * w
    hy = 53 + b - 22 * d
    # Flowing navy meridian cape behind the knight.
    r.poly([(-18, cy + 15), (-28 - 4 * w, cy - 8 - 4 * d), (-12, 4)], AZURE[0], OUTLINE)
    # Two planted cobalt-and-gold sabatons on the ground row.
    for i, x in enumerate((-12, 12)):
        step = math.sin(ph + i * math.pi) * 4 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4.5 if clip == 'walk' else 0
        r.limb([(x, cy - 6), (x + step * 0.5 - 5 * d, 14 + lift), (x + step - 9 * d, 3 + lift)], AZURE, 6)
        r.ball(x + step - 9 * d, 3 + lift, 7, 3, GOLD)
    # Heavy cobalt plate cuirass with a golden meridian cross on the chest.
    r.poly([(-19, cy - 8), (-22, cy + 15), (-6, cy + 22), (19, cy + 15), (18, cy - 8)], AZURE[2], OUTLINE)
    r.line([(1, cy + 18), (1, cy - 6)], GOLD[2], 3)
    r.line([(-13, cy + 6), (14, cy + 6)], GOLD[2], 3)
    r.ball(-18, cy + 13, 8, 6, GOLD)
    r.ball(17, cy + 13, 8, 6, GOLD)
    # Crested meridian war-helm with a tall golden astrolabe spike and glaring T-visor.
    r.poly([(hx - 3, hy + 10), (hx + 1, hy + 26 - 6 * d), (hx + 5, hy + 10)], GOLD[2], OUTLINE)
    r.ball(hx, hy, 13, 12, AZURE)
    r.poly([(hx - 11, hy + 5), (hx + 12, hy + 5), (hx + 10, hy - 2), (hx - 9, hy - 2)], OUTLINE)
    if d < 0.65:
        for dx in (-4, 5):
            r.line([(hx + dx - 2, hy + 2), (hx + dx + 2, hy + 1)], GOLD[-1], 2)
    r.line([(hx + 1, hy + 6), (hx + 1, hy - 8)], GOLD[2], 2)
    # Far arm carries the round gold-rimmed cobalt Meridian Shield with a raised golden cross.
    sx, sy = -25 - 4 * w + 5 * s - 6 * d, cy + 6 + 4 * w - 9 * d
    r.limb([(-15, cy + 11), (-21, cy + 6), (sx, sy)], AZURE, 5)
    r.ball(sx, sy, 13, 15, GOLD)
    r.ball(sx, sy, 9, 11, AZURE)
    r.line([(sx, sy + 10), (sx, sy - 10)], GOLD[-1], 2)
    r.line([(sx - 8, sy), (sx + 8, sy)], GOLD[-1], 2)
    # Near arm drives the steel Meridian Lance far forward on strike.
    hand = (21 + 24 * s - 9 * w, cy + 8 + 16 * w - 8 * s - 7 * d)
    r.limb([(14, cy + 11), (19 + 8 * s, cy + 4), hand], AZURE, 5)
    ang = 0.12 - 0.50 * w + 1.25 * s + 0.80 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 28, hand[1] + vy * 28)
    r.taper([(hand[0] - vx * 10, hand[1] - vy * 10), tip], PEARL, 5, 1)
    r.ball(hand[0], hand[1], 5, 4, GOLD)
    return a


def navigator(setup, clip, n):
    a, r, w, s, d, ph, b = setup('astro_navigator', clip, n, (0, 10), -0.36)
    cy = 28 + b - 13 * d
    hx = 2 + 7 * s - 5 * w
    hy = 52 + b - 21 * d
    hem = math.sin(ph) * 3 if clip == 'walk' else b * 0.4
    # Two planted boots beneath the brass-buttoned navy navigator greatcoat.
    for i, x in enumerate((-10, 10)):
        step = math.sin(ph + i * math.pi) * 3.5 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + i * math.pi)) * 4 if clip == 'walk' else 0
        r.ball(x + step, 3 + lift, 6, 3, BROWN)
    r.poly([(-18 - 4 * d, 3), (-13, cy + 14), (13, cy + 14), (19 + 4 * d, 3), (hem, 5)], AZURE[1], OUTLINE)
    r.ball(0, cy + 2, 14, 17 * (1 - 0.32 * d), AZURE)
    r.line([(-13, cy - 2), (13, cy - 2)], GOLD[2], 3)
    for yy in (3, 9, 14):
        r.ellipse(3, cy + yy * (1 - 0.3 * d), 1.8, 1.8, GOLD[-1])
    # Head with scowling face, glowing cyan brass ocular lens, braided silver-grey beard and brown tricorn hat.
    r.ball(hx, hy, 11, 11, BONE)
    # Braided silver-grey beard hanging down over the chest.
    r.taper([(hx + 1, hy - 4), (hx + 3 + 3 * s, hy - 14 + 4 * d), (hx + 4 + 4 * d, hy - 22 + 8 * d)], PEARL, 7, 2)
    # Left eye: angry dark scar-slit; right eye: brass ocular monocle with cyan lens.
    r.poly([(hx - 6, hy + 3), (hx - 1, hy + 2), (hx - 1, hy - 1), (hx - 6, hy - 1)], OUTLINE)
    if d < 0.65:
        r.line([(hx - 5, hy + 1), (hx - 2, hy + 1)], GOLD[-1], 1)
    r.ball(hx + 5, hy + 2, 5, 5, GOLD)
    r.ball(hx + 5, hy + 2, 3, 3, TEAL if d < 0.65 else SLATE)
    r.line([(hx - 3, hy - 5), (hx + 4, hy - 4)], OUTLINE, 2)
    # Wide-brimmed brown tricorn hat with a golden astrolabe cockade.
    r.poly([(hx - 17, hy + 7), (hx, hy + 19 - 4 * d), (hx + 18, hy + 7), (hx + 12, hy + 5), (hx - 12, hy + 5)], BROWN[2], OUTLINE)
    r.ball(hx + 2, hy + 11 - 2 * d, 3.5, 3.5, GOLD)
    # Far arm holds a brass sextant frame.
    sx, sy = -20 - 4 * w + 4 * s - 5 * d, cy + 6 - 7 * d
    r.limb([(-11, cy + 11), (-17, cy + 6), (sx, sy)], AZURE, 4)
    r.poly([(sx, sy + 8), (sx - 8, sy - 6), (sx + 6, sy - 6)], GOLD[2], OUTLINE)
    # Near arm raises and extends the telescoping brass spyglass-cannon on strike.
    hand = (19 + 23 * s - 8 * w, cy + 10 + 14 * w - 6 * s - 7 * d)
    r.limb([(11, cy + 11), (16 + 7 * s, cy + 5), hand], AZURE, 4)
    ang = 0.15 - 0.45 * w + 1.10 * s + 0.70 * d
    vx, vy = math.sin(ang), math.cos(ang)
    tip = (hand[0] + vx * 22, hand[1] + vy * 22)
    r.taper([(hand[0] - vx * 6, hand[1] - vy * 6), tip], GOLD, 4, 6)
    r.ball(tip[0], tip[1], 5, 5, TEAL if d < 0.65 else SLATE)
    return a


def axis(setup, clip, n):
    a, r, w, s, d, ph, b = setup('astro_axis', clip, n, (0, 28), 0.25)
    drift = math.sin(ph) * 2 if clip == 'walk' else 0
    x = 18 * s - 8 * w + drift
    y = 54 + b + 6 * w - 6 * s - 22 * d + (math.cos(ph) * 2 if clip == 'walk' else 0)
    spin = (ph if clip in ('idle', 'walk') else (1.4 * s - 0.6 * w)) * (1 - d)
    # Three intersecting tilted brass-and-steel armillary rings; collapse outward into a nested ring heap on death.
    for k, (rx, ry, ang0, ramp) in enumerate((
        (32, 13, 0.15, GOLD),
        (26, 24, 1.05, SLATE),
        (29, 18, -0.65, AMBER),
    )):
        ang = (ang0 + math.sin(spin + k) * 0.18) * (1 - 0.65 * d)
        ry_d = ry * (1 - 0.55 * d)
        cx_r = x + (k - 1) * 6 * d
        cy_r = y - 4 * d
        r.ball(cx_r, cy_r, rx, max(5, ry_d), ramp, ang)
        if d < 0.75:
            r.ball(cx_r, cy_r, max(4, rx - 5), max(3, ry_d - 4), AZURE if k == 1 else PURPLE, ang)
    # Central celestial sphere: blazing cobalt-and-violet in life, drains and shrinks as the rings collapse on death.
    core_scale = 1 - 0.48 * d
    r.ball(x, y, 18 * core_scale, 18 * core_scale, AZURE if d < 0.7 else SLATE)
    if d < 0.7:
        r.ball(x - 3, y + 4, 10 * core_scale, 10 * core_scale, PURPLE)
    # Orbiting star nodes and meridian spear on attack.
    if d < 0.65:
        for k in range(4):
            ang = spin + k * math.pi * 0.5
            sx = x + math.cos(ang) * 30
            sy = y + math.sin(ang) * 15
            r.ball(sx, sy, 3.5, 3.5, TEAL if k % 2 else GOLD)
    if s > 0.05 or w > 0.2:
        reach = 22 + 26 * s - 8 * w
        r.poly([(x + 14, y + 5), (x + reach, y), (x + 14, y - 5)], GOLD[-1], OUTLINE)
    # Cosmic face on the core: diamond golden third eye, two angled slit eyes and a jagged celestial rift maw.
    if d < 0.75:
        r.poly([(x - 1, y + 9), (x + 3, y + 14), (x + 7, y + 9), (x + 3, y + 4)], GOLD[-1], OUTLINE)
        for side, dx in ((-1, -7), (1, 9)):
            ex = x + dx
            r.poly([(ex - 4, y + 3), (ex + 4, y + 2 - side), (ex + 3, y - 2), (ex - 3, y - 1)], OUTLINE)
            r.line([(ex - 2, y + 1), (ex + 2, y)], TEAL[-1], 2)
        open_m = 3 + 5 * s + 2 * w
        r.poly([(x - 8, y - 5), (x + 10, y - 5), (x + 7, y - 6 - open_m), (x - 6, y - 6 - open_m)], OUTLINE)
        for fx in (-4, 1, 6):
            r.poly([(x + fx, y - 5), (x + fx + 2, y - 5), (x + fx + 1, y - 8)], GOLD[-1])
    return a
