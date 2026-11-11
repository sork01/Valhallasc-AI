"""Articulated paper, chitin, armour, cloth, binding, spirit and resin; y-up local coordinates."""
import math
from astral_slime_redraw import OUTLINE, WHITE, BONE, PEARL, GOLD, AMBER, BROWN, CRIMSON, SLATE, PURPLE, TEAL


def page(setup, clip, n):
    a, r, w, s, d, ph, b = setup('amber_page', clip, n, (0, 24), -.25)
    x, y = 14 * s - 7 * w, 53 + b + 5 * w - 3 * s - 25 * d
    # A flexible sheet folds along its centre, rather than a rigid book flattening.
    fold = 1 - .72 * d
    for side in (-1, 1):
        xx = x + side * (9 + 8 * d)
        r.poly([(x, y + 24 * fold), (xx + side * 8, y + 21 * fold),
                (xx + side * 9, y - 20 * fold), (x, y - 22 * fold)], BONE[2], OUTLINE)
        r.poly([(x, y + 21 * fold), (xx + side * 5, y + 18 * fold),
                (xx + side * 6, y - 17 * fold), (x, y - 19 * fold)], BONE[4])
    # Curled upper-right corner, lower serrated edge and attached ink strokes.
    r.poly([(x + 17, y + 21 * fold), (x + 8, y + 20 * fold), (x + 16, y + 12 * fold)], GOLD[2], OUTLINE)
    if d < .8:
        for j in range(3):
            r.line([(x - 11, y + 14 - j * 4), (x + 6, y + 13 - j * 4)], BROWN[1], 1)
        r.poly([(x - 13, y + 4), (x - 2, y), (x - 10, y - 4)], OUTLINE)
        r.poly([(x + 2, y + 1), (x + 13, y + 6), (x + 11, y - 3)], OUTLINE)
        r.ellipse(x - 7, y, 1.3, 1.5, GOLD[4])
        r.ellipse(x + 8, y + 1, 1.3, 1.5, GOLD[4])
        r.line([(x - 7, y - 9), (x, y - 6), (x + 8, y - 10)], OUTLINE, 2)
    r.ball(x - 8, y - 15 * fold, 4, 4, CRIMSON)
    # Paper's corner uncoils into a slicing ribbon, always attached at the edge.
    tipx = x + 19 + 32 * s - 6 * w
    r.poly([(x + 14, y - 8 * fold), (tipx, y + 4 + 16 * w - 6 * s),
            (tipx - 2, y - 3 + 16 * w - 6 * s), (x + 15, y - 15 * fold)], BONE[3], OUTLINE)
    if d > .2:
        for j in range(3):
            r.poly([(x - 15 + j * 14, y - 5), (x - 6 + j * 14, y - 10),
                    (x - 12 + j * 14, y - 14 - j)], BONE[2], OUTLINE)
    return a


def moth(setup, clip, n):
    a, r, w, s, d, ph, b = setup('amber_moth', clip, n, (0, 24), -.18)
    x, y = 15 * s - 7 * w, 54 + b + 5 * w - 5 * s - 18 * d
    flap = math.sin(ph) * .13 if clip in ('walk', 'idle') else .15 * w - .3 * s
    span = 1 - .72 * d
    # Four sharply pointed translucent wings, hinged at the thorax.
    for side in (-1, 1):
        for lower in (False, True):
            wingy = -14 if lower else 13
            tip = (x + side * (12 + 27 * span), y + wingy + (8 if not lower else -3) + flap * 20)
            pts = [(x + side * 4, y + 7), (x + side * (18 + 8 * span), y + 24 if not lower else y - 3),
                   tip, (x + side * (10 + 9 * span), y - 14 if lower else y - 2)]
            r.poly(pts, AMBER[2 if lower else 3], OUTLINE)
            r.line([(x + side * 5, y + 5), tip], GOLD[0], 2)
            r.poly([(x + side * (15 + 10 * span), y + wingy + 4),
                    (x + side * (23 + 10 * span), y + wingy),
                    (x + side * (17 + 10 * span), y + wingy - 5)], BROWN[1])
    for j in range(3):
        for side in (-1, 1):
            start = (x + side * 4, y + 3 - j * 5)
            r.limb([start, (x + side * (12 - 5 * d), y - j * 5),
                    (x + side * (15 - 11 * d), y - 10 - j * 4 + 11 * d)], BROWN, 2)
    for j in range(4):
        r.ball(x - 1, y - 6 - j * 5, 6 - j * .7, 4, AMBER)
    r.ball(x, y + 5, 8, 12, BROWN)
    r.ball(x + 1, y + 17, 10, 8, GOLD)
    for side in (-1, 1):
        r.line([(x + side * 4, y + 22), (x + side * 11, y + 33), (x + side * 15, y + 29)], BROWN[1], 2)
        # Compound eye facets in asymmetrical long pointed sockets.
        r.poly([(x + side * 2, y + 19), (x + side * 10, y + 24),
                (x + side * 9, y + 12)], OUTLINE)
        if d < .75:
            for j in range(3):
                r.ellipse(x + side * (5 + j % 2 * 2), y + 16 + j * 2, 1, 1, CRIMSON[3])
    r.taper([(x + 7, y + 13), (x + 15 + 8 * s, y + 9 + 8 * w),
             (x + 20 + 30 * s, y + 5 - 8 * s)], AMBER, 3, 1)
    return a


def sentinel(setup, clip, n):
    a, r, w, s, d, ph, b = setup('amber_sentinel', clip, n, (0, 5), -1.05)
    x, y = 13 * s - 7 * w, 32 + b + 4 * w - 18 * d
    # Rigid greaves bend at their knee joints; no scaled/squashed armour.
    for j, side in enumerate((-1, 1)):
        step = math.sin(ph + j * math.pi) * 4 if clip == 'walk' else 0
        foot = (x + side * 11 + step + side * 6 * d, 4)
        r.limb([(x + side * 8, y - 8), (foot[0], 15 - 7 * d), foot], BROWN, 6)
        r.ball(*foot, 9, 4, GOLD)
    r.ball(x, y + 5, 19, 22, BROWN)
    r.poly([(x - 17, y + 21), (x + 17, y + 21), (x + 14, y - 8),
            (x, y - 15), (x - 14, y - 8)], AMBER[2], OUTLINE)
    r.poly([(x - 9, y + 17), (x, y + 23), (x + 9, y + 17), (x, y - 7)], GOLD[3], OUTLINE)
    r.ball(x, y + 33, 14, 15, BROWN)
    r.poly([(x - 14, y + 40), (x, y + 48), (x + 14, y + 40),
            (x + 10, y + 22), (x - 10, y + 22)], GOLD[2], OUTLINE)
    # One continuous narrow visor, never a pair of generic round eyes.
    r.poly([(x - 11, y + 36), (x, y + 31), (x + 12, y + 36), (x + 8, y + 29), (x - 7, y + 29)], OUTLINE)
    if d < .7:
        r.line([(x - 8, y + 33), (x, y + 30), (x + 9, y + 33)], TEAL[3], 2)
    for side in (-1, 1):
        r.ball(x + side * 20, y + 16, 9, 8, BROWN)
    # Far arm holds a leather-bound tome shield, near hand grips the key-spear.
    shield = (x - 24 - 6 * w, y + 2 - 7 * d)
    r.limb([(x - 18, y + 12), shield], BROWN, 5)
    r.poly([(shield[0] - 11, shield[1] + 17), (shield[0] + 10, shield[1] + 19),
            (shield[0] + 10, shield[1] - 15), (shield[0] - 11, shield[1] - 17)], CRIMSON[1], OUTLINE)
    r.line([(shield[0] - 6, shield[1] + 14), (shield[0] - 6, shield[1] - 12)], GOLD[3], 2)
    r.ball(*shield, 5, 6, GOLD)
    hand = (x + 23 + 18 * s - 7 * w, y + 2 + 12 * w - 6 * d)
    r.limb([(x + 18, y + 12), (x + 22, y + 5), hand], BROWN, 5)
    r.line([(hand[0] - 5, hand[1] - 16), (hand[0] + 7 + 15 * s, hand[1] + 28 - 18 * s)], GOLD[1], 4)
    end = (hand[0] + 7 + 15 * s, hand[1] + 28 - 18 * s)
    r.ball(*end, 6, 7, GOLD)
    r.ellipse(*end, 3, 3.5, OUTLINE)
    r.poly([(end[0] - 3, end[1] - 4), (end[0] + 7, end[1] - 7),
            (end[0] + 6, end[1] - 13), (end[0] - 4, end[1] - 10)], AMBER[3], OUTLINE)
    return a


def curator(setup, clip, n):
    a, r, w, s, d, ph, b = setup('amber_curator', clip, n, (0, 5), -1.05)
    x, y = 12 * s - 7 * w, 37 + b + 5 * w - 20 * d
    for j, side in enumerate((-1, 1)):
        step = math.sin(ph + j * math.pi) * 4 if clip == 'walk' else 0
        r.limb([(x + side * 6, y - 18), (x + side * 9 + step, 6)], BROWN, 4)
        r.ball(x + side * 10 + step, 4, 8, 4, BROWN)
    r.poly([(x - 13, y + 15), (x + 12, y + 15), (x + 22 + 5 * d, 9),
            (x - 23 - 5 * d, 9)], BROWN[1], OUTLINE)
    r.poly([(x - 8, y + 13), (x + 6, y + 13), (x + 10, 11), (x - 13, 11)], GOLD[1])
    r.line([(x - 17, 10), (x + 18, 10)], GOLD[3], 2)
    r.ball(x, y + 21, 15, 16, BONE)
    # Swept white hair and a long hooked nose set the human face apart.
    r.poly([(x - 15, y + 19), (x - 19, y + 34), (x - 11, y + 43),
            (x + 7, y + 43), (x + 17, y + 32), (x + 8, y + 35), (x - 10, y + 32)], PEARL[3], OUTLINE)
    r.poly([(x + 3, y + 29), (x + 14, y + 18), (x + 2, y + 16)], BONE[2], OUTLINE)
    for side in (-1, 1):
        xx = x + side * 7
        r.line([(xx - 5, y + 29 - side * 2), (xx + 4, y + 27 + side * 2)], OUTLINE, 2)
        r.line([(xx - 5, y + 24), (xx - 3, y + 19), (xx + 3, y + 19), (xx + 5, y + 24)], GOLD[1], 1)
        if d < .8:
            r.ellipse(xx, y + 24, 1.2, 1, OUTLINE)
    r.line([(x - 3, y + 12), (x + 6, y + 13)], OUTLINE, 2)
    far = (x - 22, y - 2 - 6 * d)
    r.limb([(x - 12, y + 7), far], BROWN, 6)
    r.ball(*far, 5, 4, BONE)
    r.ball(x - 13, y - 10, 5, 5, GOLD)
    for j in range(3):
        r.line([(x - 16 + j * 3, y - 13), (x - 16 + j * 3, y - 21)], GOLD[2], 2)
    hand = (x + 23 + 18 * s - 5 * w, y + 3 + 14 * w - 7 * d)
    r.limb([(x + 11, y + 8), (x + 18, y + 4), hand], BROWN, 6)
    r.ball(*hand, 5, 4, BONE)
    r.line([(hand[0] - 3, hand[1] - 7), (hand[0] + 8, hand[1] + 17)], GOLD[1], 2)
    r.poly([(hand[0] + 3, hand[1] + 8), (hand[0] + 4, hand[1] + 28),
            (hand[0] + 14, hand[1] + 20), (hand[0] + 8, hand[1] + 12)], PEARL[3], OUTLINE)
    if s > .1:
        for j in range(3):
            r.ball(hand[0] + 7 + j * 7 * s, hand[1] + 4 - j * 4, 3 - j * .4, 2.5, PURPLE)
    return a


def chronicle(setup, clip, n):
    a, r, w, s, d, ph, b = setup('amber_chronicle', clip, n, (0, 20), -.2)
    x, y = 15 * s - 6 * w, 58 + b + 5 * w - 5 * s - 16 * d
    # Separate, rigid covers open about the binding. Paper falls out as it breaks.
    spread = 1 + .5 * w + .7 * s
    # Covers are rigid rectangles rotated onto their sides; leaves detach separately.
    if d > 0:
        for side in (-1, 1):
            cx, cy = x + side * (14 + 20 * d), y - 16 * d
            angle = side * 1.3 * d
            def pt(dx, dy):
                return (cx + dx * math.cos(angle) - dy * math.sin(angle), cy + dx * math.sin(angle) + dy * math.cos(angle))
            r.poly([pt(-13, 25), pt(13, 25), pt(13, -25), pt(-13, -25)], CRIMSON[1], OUTLINE)
            r.poly([pt(-10, 22), pt(10, 22), pt(10, -22), pt(-10, -22)], BONE[3], OUTLINE)
            for j in range(5):
                r.line([pt(-8, 15 - j * 7), pt(8, 15 - j * 7)], BROWN[0], 1)
            r.line([pt(-13, 23), pt(13, 23)], GOLD[2], 2)
        r.ball(x, y - 16 * d, 8, 29, CRIMSON, d * 1.35)
        if d < .8:
            r.ball(x + 1, y + 7 - 16 * d, 9, 8, CRIMSON)
        for j in range(3):
            xx, yy = x + (j - 1) * (12 + 15 * d), y - 28 - 5 * d + j * 2
            r.poly([(xx - 7, yy + 4), (xx + 8, yy + 2), (xx + 10, yy - 3), (xx - 7, yy - 1)], BONE[3], OUTLINE)
        return a
    for side in (-1, 1):
        edge = x + side * 25 * spread
        r.poly([(x, y + 25), (edge, y + 19 - 12 * d),
                (edge, y - 22 - 7 * d), (x, y - 27)], CRIMSON[1], OUTLINE)
        for j in range(4):
            ey = y + 18 - j * 3
            r.poly([(x + side * 2, ey), (edge - side * 3, ey - 5),
                    (edge - side * 3, y - 18 - j - 7 * d), (x + side * 2, y - 23 - j)], BONE[2 + j % 2], OUTLINE)
        r.line([(edge, y + 19 - 12 * d), (edge, y - 22 - 7 * d)], GOLD[2], 3)
        for j in range(3):
            r.line([(x + side * 7, y + 10 - j * 7), (edge - side * 8, y + 5 - j * 7 - 10 * d)], BROWN[0], 1)
    r.ball(x, y, 8, 29, CRIMSON)
    r.line([(x - 5, y + 18), (x + 5, y + 18)], GOLD[3], 2)
    r.line([(x - 5, y - 18), (x + 5, y - 18)], GOLD[3], 2)
    # A wax-seal cyclops with a vertical torn-paper pupil and page-tooth maw.
    r.ball(x + 1, y + 7, 12, 10, CRIMSON)
    r.poly([(x - 5, y + 13), (x + 6, y + 12), (x + 3, y - 1), (x - 2, y - 2)], OUTLINE)
    if d < .8:
        r.line([(x + 1, y + 10), (x + 2, y + 2)], GOLD[4], 2)
    r.poly([(x - 12, y - 7), (x + 14, y - 5), (x + 11, y - 17), (x - 9, y - 18)], OUTLINE)
    for j in range(6):
        xx = x - 9 + j * 4
        r.poly([(xx, y - 7), (xx + 3, y - 7), (xx + 1, y - 13 - j % 2 * 2)], BONE[3])
    if d > .1:
        for j in range(3):
            xx = x + (j - 1) * (12 + 15 * d)
            yy = y - 28 - 5 * d + j * 2
            r.poly([(xx - 7, yy + 4), (xx + 8, yy + 2), (xx + 10, yy - 3), (xx - 7, yy - 1)], BONE[3], OUTLINE)
    return a


def memory(setup, clip, n):
    a, r, w, s, d, ph, b = setup('amber_memory', clip, n, (0, 24))
    x, y = 14 * s - 7 * w, 56 + b + 4 * w - 4 * s - 13 * d
    # Faceted amber reliquary, not a soft blob. Its two halves split rigidly.
    for side in (-1, 1):
        xx = x + side * 12 * d
        cy = y - 28
        angle = -side * 1.16 * d
        def pt(dx, dy):
            return (xx + dx * math.cos(angle) - dy * math.sin(angle), cy + dx * math.sin(angle) + dy * math.cos(angle))
        r.poly([pt(0, 58), pt(side * 21, 41), pt(side * 18, 10), pt(0, 0), pt(-side * 3, 26)], AMBER[2], OUTLINE)
        r.poly([pt(side * 3, 51), pt(side * 15, 39), pt(side * 10, 16), pt(side * 3, 10)], GOLD[3])
        r.poly([pt(side * 15, 39), pt(side * 21, 41), pt(side * 18, 10), pt(side * 10, 16)], AMBER[3])
        r.line([pt(side * 3, 51), pt(side * 15, 39)], GOLD[4], 2)
    # The trapped spirit evaporates upwards; the hard amber remains as debris.
    if d < .85:
        spirit = 1 - .6 * d
        sy = y + 7 + 22 * d
        r.ball(x, sy + 8, 10 * spirit, 13 * spirit, PURPLE)
        r.poly([(x - 8 * spirit, sy), (x + 9 * spirit, sy),
                (x + 10, sy - 19 * spirit), (x + 3, sy - 14 * spirit),
                (x - 5, sy - 23 * spirit), (x - 11, sy - 15 * spirit)], PURPLE[2], OUTLINE)
        for side in (-1, 1):
            xx = x + side * 4
            r.poly([(xx - 2, sy + 9), (xx, sy + 14), (xx + 2, sy + 8), (xx, sy + 5)], OUTLINE)
            if d < .6:
                r.ellipse(xx, sy + 8, 1, 1.5, TEAL[4])
        reach = x + 22 + 29 * s - 7 * w
        r.taper([(x + 6, sy - 2), (x + 15, sy + 3 + 9 * w), (reach, sy - 5)], PURPLE, 6 * spirit, 2)
        for j in range(3):
            r.line([(reach, sy - 5), (reach + 6, sy - 10 + j * 4)], PURPLE[3], 2)
    if d > .1:
        for j in range(4):
            xx = x - 27 + j * 18
            r.poly([(xx - 5, y - 27), (xx + j % 2 * 4, y - 33 - j), (xx + 6, y - 25)], AMBER[3], OUTLINE)
    return a


def cocoon(setup, clip, n):
    a, r, w, s, d, ph, b = setup('amber_cocoon', clip, n, (0, 10))
    x, y = 0, 31 + b + 2 * w - 11 * d
    # Amber Stasis captures a friend. The figure is humanoid and vanishes freed.
    for side in (-1, 1):
        xx = x + side * 12 * d
        cy = y - 28
        angle = -side * 1.16 * d
        def pt(dx, dy):
            return (xx + dx * math.cos(angle) - dy * math.sin(angle), cy + dx * math.sin(angle) + dy * math.cos(angle))
        r.poly([pt(0, 60), pt(side * 22, 38), pt(side * 24, 14), pt(0, 0), pt(-side * 3, 24)], AMBER[2], OUTLINE)
        r.poly([pt(side * 4, 50), pt(side * 15, 37), pt(side * 16, 17), pt(side * 3, 9)], GOLD[3])
    if d < .78:
        r.ball(x - 3, y + 12, 7, 8, BROWN)
        r.ball(x, y - 3, 10, 13, BROWN, -.3)
        r.limb([(x - 5, y + 2), (x + 8, y - 4), (x + 4, y + 8)], BROWN, 3)
        r.limb([(x - 5, y - 12), (x + 7, y - 13), (x + 10, y - 5)], BROWN, 4)
        r.line([(x - 6, y + 12), (x - 2, y + 10)], GOLD[3], 1)
    # A restrained defensive resin pulse, never a weapon attack by the prisoner.
    for side in (-1, 1):
        if d > .15:
            continue
        end = x + side * (28 + 20 * s - 5 * w)
        r.poly([(x + side * (18 + 18 * d), y + 3), (end, y + 8 + 8 * w),
                (x + side * (20 + 18 * d), y - 5)], AMBER[3], OUTLINE)
    r.ball(-12 - 17 * d, 3, 9, 3, AMBER)
    r.ball(12 + 17 * d, 3, 10, 3, AMBER)
    return a
