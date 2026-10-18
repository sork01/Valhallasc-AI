"""The five mounts as primitive lists (make_mount_sprites.py renders them).

Every builder takes (clip, k, n) and returns (prims, bob): the body parts for frame k of n and how far the saddle
rises (world units) in that frame, which the client adds to the rider. Model space is documented in mount_toon.py:
origin on the ground under the saddle, +y forward, +z up. The saddle sits at x=0, y=SEAT_Y.

Style: chibi cel illustration, stout bodies, big heads, big shiny eyes (a dark iris, a pupil and two highlights).
"""
import math

import numpy as np

from mount_toon import Ell, V, cone, frame_z, ik2, limb, unit

S_, C_, TAU = math.sin, math.cos, math.tau

# ----------------------------------------------------------------------------- shared tack
LEATHER = ['#2a1710', '#4b2a1a', '#7b4a2b', '#a9703f']
GOLD = ['#6f4a0e', '#b07c1a', '#e5b02f', '#ffe27d']
BLANKET = ['#4a0f1d', '#82182b', '#b92a3c', '#e8586a']
EYE = ['#150d1c', '#150d1c', '#150d1c', '#150d1c']
WHITE = ['#f4f1ee', '#f6f3f0', '#f8f5f2', '#fbf8f5']
IRIS = ['#3a2208', '#6b3d10', '#b9741f', '#f0b14a']
FLAT = {'eye': 0, 'white': 3}
CYCLE = lambda k, n: TAU * k / n


def eyes(centre, side_x, forward, size, iris='iris', out=(1, 0, 0)):
    """Both eyes of a head: a coloured iris, a pupil and two highlights on the camera's upper left.
    `centre` is the head position, `side_x` how far each eye sits to the side, `forward` along y."""
    prims = []
    for sx in (-1, 1):
        c = V(centre[0] + sx * side_x, centre[1] + forward, centre[2])
        prims += [Ell(c, (size, size * .86, size * 1.08), iris),
                  Ell(c + V(sx * size * .28, size * .22, 0), (size * .62, size * .5, size * .74), 'eye'),
                  Ell(c, (size * .32, size * .32, size * .32), 'white', cam=(-size * .46, size * .52, size * .78)),
                  Ell(c, (size * .17, size * .17, size * .17), 'white', cam=(size * .34, -size * .3, size * .86))]
    return prims


def saddle(y, z, width=9., length=9.):
    """Blanket, saddle with a gold pommel and cantle, and a stirrup strap on each side."""
    prims = [Ell((0, y, z), (width + .6, length + 1, 2.9), 'blanket'),
             Ell((0, y - length * .1, z + 2.2), (width - 1.8, length - .5, 2.6), 'leather'),
             Ell((0, y + length * .78, z + 3.4), (2.6, 2, 2.6), 'gold'),
             Ell((0, y - length * .86, z + 3.5), (width - 2.6, 1.8, 3), 'leather')]
    for sx in (-1, 1):
        prims += [limb((sx * (width + .2), y, z + .8), (sx * (width + 1.4), y + .5, z - 8.5), 1.0, 'leather'),
                  Ell((sx * (width + 1.5), y + .5, z - 9.3), (1.7, .7, 1.7), 'gold')]
    return prims


def gait(k, n, phase=0.):
    """Position in the stride (0..1) of frame k of n."""
    return ((k / n) + phase) % 1.0


# ----------------------------------------------------------------------------- the horse
HORSE = {'coat': ['#3a190d', '#7a3c1c', '#b8672f', '#ee9d55'],
         'coat2': ['#2b1710', '#4c2a1b', '#6b4029', '#8a5a3c'],      # mane, tail, socks
         'blaze': ['#bda48e', '#dccab6', '#f1e4d4', '#fff7ea'],
         'hoof': ['#17110f', '#2a2019', '#40342b', '#5b4b3d'],
         'nose': ['#4b2b2a', '#7a4a47', '#a8706a', '#d29a92'],
         'leather': LEATHER, 'gold': GOLD, 'blanket': BLANKET, 'eye': EYE, 'white': WHITE, 'iris': IRIS}


def horse(clip, k, n):
    run = clip == 'run'
    ph = CYCLE(k, n)
    bounce = (abs(S_(ph)) * 1.8 - .5) if run else S_(CYCLE(k, n)) * .35
    z0 = bounce
    prims = []
    # barrel, chest, rump: a stout chibi body
    prims += [Ell((0, -1, 31.5 + z0), (10.2, 19, 11.2), 'coat'),
              Ell((0, 12, 32.5 + z0), (10.6, 8.8, 11.8), 'coat'),
              Ell((0, -13, 33 + z0), (10.4, 9, 11.4), 'coat'),
              Ell((0, -1, 24.5 + z0), (8.4, 16.5, 5.4), 'coat2', bias=-.06)]
    # neck and a big round head, bobbing with the stride
    nod = S_(ph * 2 + 1) * 1.4 if run else S_(CYCLE(k, n)) * .6
    neck_a, neck_b = V(0, 15, 38.5 + z0), V(0, 22.5, 50 + z0 + nod * .3)
    prims += [limb(neck_a, neck_b, 6.6, 'coat', ext=3)]
    head = V(0, 28.5, 52 + z0 + nod)
    prims += [Ell(head, (5.6, 8.4, 6.2), 'coat', frame_z_pitch(-.6)),
              Ell(head + V(0, 6.0, -5.4), (4.3, 4.6, 4.0), 'coat', frame_z_pitch(-.75)),
              Ell(head + V(0, 8.6, -7.2), (3.7, 3.4, 3.3), 'nose'),
              Ell(head + V(0, 2.8, 3.0), (1.2, 6.2, 1.0), 'blaze', frame_z_pitch(-.6), bias=.1)]
    for sx in (-1, 1):
        prims += [cone(head + V(sx * 3.4, -4.0, 4.4), head + V(sx * 4.0, -5.2, 12), 2.5, 'coat'),
                  Ell(head + V(sx * 3.5, -4.2, 6.0), (.9, 1.0, 2.6), 'nose', frame_z(V(sx * .1, -.2, 1))),
                  Ell(head + V(sx * 1.9, 8.4, -8.0), (.7, .7, .7), 'eye')]
    prims += eyes(head + V(0, 0, 1.0), 5.2, 3.0, 3.1)
    prims += [Ell(head + V(0, 6.6, -5.8), (4.6, 1.1, 4.4), 'leather', frame_z_pitch(-.75), bias=-.05),
              Ell(head + V(0, 2.2, 1.6), (5.8, 1.1, 5.6), 'leather', frame_z_pitch(-.55), bias=-.05)]
    # a full mane down the neck and a forelock, and a swishing tail
    for i in range(6):
        f = i / 5
        c = neck_a + (neck_b - neck_a) * f + V(0, -5.2 * (1 - f * .4), 4.2 + 1.4 * f)
        prims += [Ell(c, (2.4, 3.6 + 1.2 * (1 - f), 3.6), 'coat2', bias=.04)]
    prims += [Ell(head + V(0, 4.0, 6.6), (2.6, 4.2, 2.8), 'coat2')]
    sway = S_(ph * (2 if run else 1)) * (5 if run else 3)
    tail, tip = swish(V(0, -21, 37 + z0), 'tail', 3, 3.3, 'coat2', sway, rise=1.5 if run else 0, drop=4.6, length=5.0, ext=2.6)
    prims += tail + [Ell(tip + V(sway * .1, -1.6, -5.2), (2.8, 3.6, 8.4), 'coat2', frame_z_pitch(.25), bias=.04), Ell(tip + V(sway * .1 + 1.3, -1.2, -4.0), (1.6, 2.4, 6.6), 'coat', bias=.02)]
    # legs: short and thick; a trot pairs diagonal legs, the run lifts them high
    for hx, hy, off, front in ((-5.8, 12, 0, True), (5.8, 12, .5, True), (-5.8, -12.5, .5, False), (5.8, -12.5, 0, False)):
        hip = V(hx, hy, 26 + z0)
        if run:
            u = gait(k, n, off)
            swing = C_(TAU * u)
            lift = max(0, S_(TAU * u)) * (8 if front else 7)
            foot = V(hx * 1.02, hy + swing * (7 if front else 6.5), .5 + lift)
        else:
            foot = V(hx * 1.02, hy, .5)
        knee, ankle, foot = leg_ik(hip, foot, 11.8, 11.4, V(0, 1 if front else -1, 0))
        prims += [limb(hip, knee, 4.5, 'coat'), limb(knee, ankle, 3.1, 'coat'), Ell(knee, (3.5, 3.5, 3.5), 'coat'),
                  limb(ankle - V(0, 0, 4.2), ankle, 3.4, 'blaze' if hy > 0 and hx < 0 else 'coat2'),
                  Ell(foot + V(0, .8, 1.6), (3.9, 4.4, 2.8), 'hoof')]
    prims += saddle(-1.5, 41.8 + z0, 10, 9.5)
    return prims, bounce


def frame_z_pitch(angle):
    """An orientation whose local z axis points up and forward, tilted by `angle` (radians, negative = nose down) about x."""
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


# ----------------------------------------------------------------------------- shared helpers
def stride_foot(hx, hy, u, swing, lift, rest=.5, spread=1.0):
    """Foot position at stride phase u (0..1): swing back and forth along y, lifted while it travels forwards."""
    return V(hx * spread, hy + C_(TAU * u) * swing, rest + max(0, S_(TAU * u)) * lift)


def leg_ik(hip, foot, l1, l2, pole, drop=3.):
    """Knee, ankle and the foot that hangs `drop` below the ankle, so the foot stays attached when the leg is at full reach."""
    knee, ankle = ik2(hip, foot + V(0, 0, drop), l1, l2, pole)
    return knee, ankle, ankle - V(0, 0, drop)


def paw(foot, mat, toe, r=3.6, long=4.4):
    """A rounded paw or hoof with toe bumps."""
    prims = [Ell(foot + V(0, .9, 1.5), (r, long, r * .72), mat)]
    for i, dx in enumerate((-1.5, 0, 1.5)):
        prims.append(Ell(foot + V(dx * r / 3.6, long * .72, .9), (r * .24, r * .3, r * .24), toe))
    return prims


def swish(start, kind, steps, thick, mat, sway, tip=None, rise=0., drop=1.4, length=4.2, ext=.9):
    """A tail of `steps` ellipsoids curling sideways by `sway` and lifting by `rise`; the last part can be another material."""
    prims, prev = [], start
    for i in range(steps):
        f = i / max(steps - 1, 1)
        nxt = prev + V(sway * (i + 1) * .14, -length * (1 - .25 * f), -drop * (1 - f) + rise * f)
        prims.append(limb(prev, nxt, thick * (1 - .62 * f), tip if (tip and i >= steps - 2) else mat, ext=ext))
        prev = nxt
    return prims, prev


def feather(a, b, width, mat, normal, bias=0.):
    """A flat feather from a to b: width across, ~.9 thick, lying in the plane with this normal."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    z = unit(b - a)
    y = unit(normal - z * (normal @ z))
    x = np.cross(y, z)
    return Ell((a + b) / 2, (width, .95, np.linalg.norm(b - a) / 2 + .8), mat, np.stack([x, y, z], 1), bias=bias)


# ----------------------------------------------------------------------------- the sabertooth (winter court cat)
SABER = {'fur': ['#3f5472', '#6f89aa', '#a9c3dc', '#e3f0fb'],
         'fur2': ['#2c3a52', '#52698a', '#7e98b8', '#a9c0d8'],           # belly, legs, tail tip
         'stripe': ['#141c2c', '#1f2b44', '#2b3b5d', '#3b507c'],
         'fang': ['#9d9a8a', '#cbc8b8', '#ebe8d8', '#fffdf0'],
         'nose': ['#52364a', '#8a5c78', '#c789a4', '#ecb4c8'],
         'claw': ['#3c4658', '#69758c', '#a0acc0', '#d4dcea'],
         'leather': LEATHER, 'gold': GOLD, 'blanket': ['#10284a', '#1b4a86', '#2f78c0', '#69b0ea'], 'eye': EYE, 'white': WHITE,
         'iris': ['#0b3a5a', '#1c7fa8', '#58d2e8', '#b6f6ff']}


def sabertooth(clip, k, n):
    run = clip == 'run'
    ph = CYCLE(k, n)
    z0 = (S_(ph * 2) * 1.5 - .2) if run else S_(ph) * .35
    prims = []
    prims += [Ell((0, -2, 29.5 + z0), (10.2, 19.5, 10.6), 'fur'),
              Ell((0, 11.5, 31 + z0), (11.6, 9.4, 12), 'fur'),
              Ell((0, -14.5, 29 + z0), (10.8, 9.2, 10.8), 'fur'),
              Ell((0, -2, 22.5 + z0), (8.2, 17, 5), 'fur2', bias=-.06)]
    for i, y in enumerate((-17, -11, -5, 1, 7, 13)):          # stripes down the flanks, below the blanket
        for sx in (-1, 1):
            prims.append(Ell((sx * (10.0 + (1.2 if y > 9 else 0)), y, 27.5 + z0 + (i % 2) * 1.5), (1.4, 2.1, 5.6), 'stripe', frame_z(V(sx * .5, 0, 1))))
    # head low and forward on a thick neck with a pale ruff
    nod = S_(ph * 2 + .8) * 1.1 if run else S_(ph) * .5
    head = V(0, 27.5, 35 + z0 + nod)
    prims += [limb(V(0, 14, 37 + z0), V(0, 22, 38 + z0 + nod * .5), 7.6, 'fur', ext=3),
              Ell(V(0, 15.5, 36 + z0), (11, 6, 11), 'fur', bias=.08)]
    prims += [Ell(head, (9, 8.2, 8), 'fur'),
              Ell(head + V(0, 6.6, -2.6), (4.9, 4.4, 3.5), 'fur', frame_z_pitch(-.25)),
              Ell(head + V(0, 10, -1.6), (2.6, 1.7, 1.5), 'nose'),
              Ell(head + V(0, 4.8, 5.2), (1.4, 3.6, .9), 'stripe', frame_z_pitch(-.1), bias=.05)]
    for sx in (-1, 1):
        prims += [Ell(head + V(sx * 5.6, -2.8, 6.4), (2.8, 1.8, 3.1), 'fur2'), Ell(head + V(sx * 5.6, -2.0, 6.6), (1.8, 1.0, 2.0), 'nose'),
                  cone(head + V(sx * 2.4, 8.2, -3.1), head + V(sx * 2.6, 9.0, -13), 1.55, 'fang'),         # the sabres
                  Ell(head + V(sx * 2.6, 8.4, -1.2), (1.3, 1.9, 1.0), 'stripe', bias=.1)]
    prims += eyes(head + V(0, 0, 1.2), 6.0, 4.6, 3.3)
    prims += [Ell(head + V(0, 6, -3.6), (5.1, 1.5, 2.2), 'fur2', frame_z_pitch(-.3), bias=-.05)]
    # tail with a dark tip
    tail, _ = swish(V(0, -22.5, 31 + z0), 'tail', 4, 3.8, 'fur', S_(ph * (2 if run else 1)) * (5 if run else 3), tip='stripe', rise=4.5 if run else 2, drop=2.2, length=6.2, ext=2.6)
    prims += tail
    for hx, hy, off, front in ((-6.3, 11.5, 0, True), (6.3, 11.5, .5, True), (-6.3, -13.5, .5, False), (6.3, -13.5, 0, False)):
        hip = V(hx, hy, 25 + z0)
        foot = stride_foot(hx, hy, gait(k, n, off), 8.5 if front else 7.5, 6.5, spread=1.05) if run else V(hx * 1.05, hy, .5)
        knee, ankle, foot = leg_ik(hip, foot, 10.8, 10.4, V(0, -1 if front else 1, 0))
        prims += [limb(hip, knee, 5.0 if front else 4.8, 'fur'), limb(knee, ankle, 3.5, 'fur2'), Ell(knee, (3.9, 3.9, 3.9), 'fur')]
        prims += paw(foot, 'fur2', 'claw', 4.3, 5)
    prims += saddle(-2.5, 39.8 + z0, 10, 9.5)
    return prims, z0


# ----------------------------------------------------------------------------- the lizard (desert runner)
LIZARD = {'hide': ['#4b4a1c', '#837a2e', '#bfa94a', '#f0dc7a'],
          'belly': ['#8a3d12', '#c4631f', '#ee9340', '#ffcb7a'],
          'stripe': ['#2f2a12', '#4d4520', '#6b5f2c', '#8a7b3a'],
          'frill': ['#7a1d12', '#c13a1c', '#ec6a2a', '#ffb05a'],
          'claw': ['#2c2616', '#50462a', '#7e704a', '#b0a070'],
          'tongue': ['#7a1030', '#b02048', '#e0507a', '#ff90b0'],
          'leather': LEATHER, 'gold': GOLD, 'blanket': ['#5a2a08', '#9a4d12', '#d9892c', '#ffc866'], 'eye': EYE, 'white': WHITE,
          'iris': ['#6b4a00', '#c78a10', '#ffd23a', '#fff49a']}


def lizard(clip, k, n):
    run = clip == 'run'
    ph = CYCLE(k, n)
    z0 = (abs(S_(ph)) * 1.3 - .3) if run else S_(ph) * .3
    wob = S_(ph) * 1.8 if run else 0
    prims = []
    prims += [Ell((wob * .3, -1, 27.5 + z0), (11.2, 19.5, 8.8), 'hide'),
              Ell((wob * .2, 11, 28.5 + z0), (11, 8.6, 9.2), 'hide'),
              Ell((wob * .4, -14, 27.5 + z0), (11.2, 9.4, 9), 'hide'),
              Ell((wob * .3, -1, 21 + z0), (9.4, 18, 4.6), 'belly', bias=-.04)]
    for i in range(8):                                                          # a ridge of frill spikes down the back
        y = 16 - i * 4.6
        prims.append(cone(V(wob * .3, y, 33.4 + z0 - (3 if i > 5 else 0)), V(wob * .3, y - 1.2, 41 + z0 - i * .45), 2.4, 'frill'))
    for i, y in enumerate((-16, -9, -2, 5, 12)):                                # dark bars down the flanks
        for sx in (-1, 1):
            prims.append(Ell((sx * (10.4 + wob * .02), y, 29 + z0), (1.3, 2.4, 5.6), 'stripe', frame_z(V(sx * .5, 0, 1))))
    nod = S_(ph * 2 + 1) * 1.1 if run else S_(ph) * .5
    head = V(wob * .5, 28.5, 31.5 + z0 + nod)
    prims += [limb(V(0, 15, 30 + z0), head + V(0, -3, 0), 6.4, 'hide', ext=2.5),
              Ell(head, (7.4, 8.4, 6.2), 'hide'),
              Ell(head + V(0, 8.2, -1.4), (5.4, 6.4, 3.6), 'hide', frame_z_pitch(-.12)),
              Ell(head + V(0, 8, -3.6), (5, 6, 1.6), 'belly', frame_z_pitch(-.12), bias=-.04),
              Ell(head + V(wob * .1, 14, -1.2), (3.3, 1.6, 2.4), 'hide')]
    for sx in (-1, 1):
        prims += [Ell(head + V(sx * 1.7, 15, .3), (.8, .7, .6), 'eye'),
                  Ell(head + V(sx * 6.4, -1.5, 1.6), (1.2, 5, 5.4), 'frill', frame_z(V(sx * .6, 0, 1))),            # cheek frill
                  cone(head + V(sx * 4.4, -4.2, 4.6), head + V(sx * 6.2, -9.0, 8.4), 2.0, 'frill')]
    prims += eyes(head + V(0, 0, 3.2), 5.4, 3.2, 3.4)
    tail, _ = swish(V(0, -21.5, 28 + z0), 'tail', 5, 6.4, 'hide', S_(ph) * (6 if run else 3.5), tip='stripe', rise=-.2, drop=3.2, length=6.2, ext=2.4)
    prims += tail
    for hx, hy, off, front in ((-8.4, 11, 0, True), (8.4, 11, .5, True), (-8.4, -13.5, .5, False), (8.4, -13.5, 0, False)):
        hip = V(hx * .85, hy, 24 + z0)
        sx = 1 if hx > 0 else -1
        foot = stride_foot(hx, hy, gait(k, n, off), 7.5, 4.5, spread=1.62) if run else V(hx * 1.62, hy, .5)
        knee, ankle, foot = leg_ik(hip, foot, 12.4, 12.4, V(sx * 1, 0, .25), 2.2)
        prims += [limb(hip, knee, 5.2, 'hide'), limb(knee, ankle, 3.8, 'hide'), Ell(knee, (4.3, 4.3, 4.3), 'hide')]
        prims += [Ell(foot + V(0, 1, 1.2), (4.2, 4.6, 2.2), 'hide')] + [Ell(foot + V(dx, 5.2, 1.0), (.9, 1.9, .9), 'claw') for dx in (-1.9, 0, 1.9)]
    prims += saddle(-1.5, 35.4 + z0, 10, 9.5)
    return prims, z0


# ----------------------------------------------------------------------------- the raptor (feathered runner)
RAPTOR = {'skin': ['#1d4a2a', '#2f7a3c', '#58b04c', '#a4e070'],
          'belly': ['#9c6a22', '#d09a36', '#f0c860', '#fff0a0'],
          'plume': ['#7a2410', '#c4461c', '#f07a2c', '#ffc060'],
          'plume2': ['#0f3e52', '#16789a', '#2cc0d4', '#9af0f4'],
          'claw': ['#2a2014', '#4e3c24', '#8a7048', '#c8b078'],
          'beak': ['#7a5a14', '#c8942a', '#f0c84c', '#fff0a0'],
          'leather': LEATHER, 'gold': GOLD, 'blanket': ['#0d3a44', '#16707c', '#2cb0b4', '#7ae8e4'], 'eye': EYE, 'white': WHITE,
          'iris': ['#6a1a00', '#c4400a', '#ff8a1c', '#ffd070']}


def raptor(clip, k, n):
    run = clip == 'run'
    ph = CYCLE(k, n)
    z0 = (abs(S_(ph)) * 2.6 - .8) if run else S_(ph) * .5
    lean = .07 if run else 0
    prims = []
    # an upright body on two big legs; the torso tips forwards a little in the run
    prims += [Ell((0, -2, 46 + z0), (9.4, 15.5, 10.4), 'skin', frame_z_pitch(lean)),
              Ell((0, -1, 40.5 + z0), (7.8, 13, 5.6), 'belly', frame_z_pitch(lean), bias=-.03),
              Ell((0, 10.5, 49 + z0), (8.4, 8, 9.6), 'skin'),
              Ell((0, -13.5, 45 + z0), (8.6, 8.2, 9.4), 'skin')]
    # a curved neck and a big crested head with a short hooked beak
    nod = S_(ph * 2 + 1) * 1.6 if run else S_(ph + 1) * .8
    neck_a, neck_b = V(0, 12, 54 + z0), V(0, 19, 65 + z0 + nod * .4)
    prims += [limb(neck_a, neck_b, 5.2, 'skin', ext=2.5), Ell(neck_a + V(0, 1.6, -2.4), (3.6, 4, 6), 'belly', bias=-.02)]
    head = V(0, 23, 68 + z0 + nod)
    prims += [Ell(head, (6.2, 7.8, 6.4), 'skin'),
              Ell(head + V(0, 6.4, -1.6), (3.9, 5, 3.3), 'skin', frame_z_pitch(-.2)),
              cone(head + V(0, 9.2, 1.0), head + V(0, 14, -1.6), 2.6, 'beak'),
              Ell(head + V(0, 8.8, -3.4), (3.0, 4.4, 1.4), 'beak', frame_z_pitch(-.1))]
    for i, (dy, dz, ln) in enumerate(((-3, 5.0, 8), (-5.4, 4.0, 10), (-7.6, 2.4, 9), (-4.0, 6.2, 6))):         # a plume crest
        prims.append(feather(head + V(0, dy, dz), head + V(0, dy - 4.2 - ln * .5, dz + 3.6 + ln * .45 - i), 2.1, 'plume' if i % 2 == 0 else 'plume2', V(1, 0, 0)))
    prims += eyes(head + V(0, 0, 1.6), 5.6, 2.2, 3.3)
    # tiny arms
    for sx in (-1, 1):
        a = V(sx * 8.8, 11, 47 + z0)
        prims += [limb(a, a + V(sx * 2.4, 5.2, -4.2 + (S_(ph + sx) if run else 0) * 1.2), 1.8, 'skin'),
                  Ell(a + V(sx * 2.6, 6.6, -4.4), (1.4, 2, 1.1), 'claw')]
    # a long balancing tail with a plume at the end
    tail, tip = swish(V(0, -19, 46 + z0), 'tail', 3, 5.6, 'skin', S_(ph * (2 if run else 1)) * (3 if run else 2), rise=0, drop=4.4, length=6.2, ext=2.6)
    prims += tail
    for i, (sx, ln) in enumerate(((-1, 10), (1, 10), (0, 12))):
        prims.append(feather(tip, tip + V(sx * (ln * .5), -ln * .8, -ln * .1 + 3), 2.8, 'plume' if i == 2 else 'plume2', V(0, 0, 1)))
    # legs: a big thigh, a backwards-bent shin and a three-toed foot with a sickle claw
    for hx, off in ((-6.8, 0), (6.8, .5)):
        hip = V(hx, -2.5, 38 + z0)
        if run:
            u = gait(k, n, off)
            foot = V(hx * 1.02, -2.5 + C_(TAU * u) * 11, .5 + max(0, S_(TAU * u)) * 11)
        else:
            foot = V(hx * 1.02, -.5, .5)
        knee, ankle, foot = leg_ik(hip, foot, 17.5, 18.5, V(0, 1, .2), 3.2)
        prims += [limb(hip, knee, 6.1, 'skin'), limb(knee, ankle, 3.1, 'skin'), Ell(knee, (4.2, 4.2, 4.2), 'skin')]
        prims += [Ell(foot + V(0, 1.6, 1.4), (3.3, 5, 2.1), 'skin')] + [Ell(foot + V(dx * 1.6, 6.4, 1.2), (1.2, 2.6, 1.0), 'claw') for dx in (-1, 0, 1)]
    prims += saddle(-3.5, 54.8 + z0, 9, 8.5)
    return prims, z0


# ----------------------------------------------------------------------------- the gryphon (a ground-runner that spreads its wings)
GRYPHON = {'fur': ['#6a3c10', '#a8651c', '#dc9a36', '#ffd36e'],
           'plume': ['#9a9488', '#cdc8bc', '#ece8de', '#ffffff'],        # the eagle head, chest and wings
           'plume2': ['#4a2c0c', '#7e4c18', '#b4762a', '#e8a84a'],       # wing feathers' upper rows
           'tip': ['#16243e', '#26406e', '#3e66a6', '#7aa6e8'],          # wing tips and the tail tuft
           'beak': ['#8a5a08', '#d49410', '#ffc828', '#fff08a'],
           'talon': ['#5a4a1a', '#9a8030', '#d8b84a', '#fff0a0'],
           'leather': LEATHER, 'gold': GOLD, 'blanket': ['#2a0f4a', '#4e1c86', '#7a38c0', '#b278ec'], 'eye': EYE, 'white': WHITE,
           'iris': ['#6a2a00', '#d06a08', '#ffb41c', '#fff2a0']}


def wing(sx, shoulder, spread, flap, rows=7):
    """One wing. `spread` 0 (folded along the flank) to 1 (open), `flap` raises or lowers it (radians). Feathers lie in the
    wing's own plane, so the plane tilts with the flap."""
    out = unit(V(sx * C_(flap), -.18 * (1 - spread), S_(flap)))
    back = unit(V(0, -1, -.1))
    arm_dir = unit(out * spread + back * (1 - spread) + V(0, .12, .16 * (1 - spread)))
    elbow = shoulder + arm_dir * 11
    wrist_dir = unit(out * (.55 + .45 * spread) + back * (.9 - .85 * spread) + V(0, .1, .06 - .1 * flap))
    wrist = elbow + wrist_dir * 11
    normal = unit(np.cross(arm_dir, back))
    if normal[2] < 0:
        normal = -normal
    prims = [limb(shoulder, elbow, 3.6, 'plume'), limb(elbow, wrist, 3.0, 'plume')]
    tipdir = unit(wrist_dir * (.8 + .2 * spread) + back * (.35 - .3 * spread))
    for i in range(rows):                                       # primaries fan out beyond the wrist
        f = i / (rows - 1)
        d = unit(tipdir * (1 - f * .85) + back * (f * .95) + out * (0 if spread > .5 else .0))
        length = 16 - f * 4 + spread * 8
        prims.append(feather(wrist - wrist_dir * 2, wrist - wrist_dir * 2 + d * length, 2.6, 'tip' if i < 3 else 'plume2', normal, bias=-.02 * i))
    for i in range(5):                                          # secondaries trail the forearm
        f = i / 4
        base = shoulder + (elbow - shoulder) * (.2 + f * .8) if f < .5 else elbow + (wrist - elbow) * ((f - .5) * 2)
        d = unit(back * 1.0 + out * (.35 * spread) + V(0, 0, -.15))
        prims.append(feather(base, base + d * (11 + 3 * spread), 3.1, 'plume' if i % 2 else 'plume2', normal, bias=.03))
    return prims


def gryphon(clip, k, n):
    run = clip == 'run'
    ph = CYCLE(k, n)
    z0 = (S_(ph) * 1.7) if run else S_(ph) * .3
    prims = []
    prims += [Ell((0, -2, 32 + z0), (10, 19, 10.8), 'fur'),
              Ell((0, 12, 34 + z0), (11, 9.2, 12), 'plume'),
              Ell((0, -14.5, 31.5 + z0), (10.2, 9, 10.6), 'fur'),
              Ell((0, -2, 25 + z0), (8, 16, 4.8), 'plume2', bias=-.06)]
    # eagle head, thick neck ruff, hooked beak, big eyes, ear tufts
    nod = S_(ph * 2 + 1) * 1.3 if run else S_(ph + 1) * .6
    neck_a, neck_b = V(0, 15, 41 + z0), V(0, 21.5, 50 + z0 + nod * .3)
    prims += [limb(neck_a, neck_b, 6.4, 'plume', ext=3), Ell(V(0, 15.5, 42 + z0), (9.6, 5.4, 8), 'plume', bias=.05)]
    head = V(0, 27, 54 + z0 + nod)
    prims += [Ell(head, (6.8, 7.6, 6.8), 'plume'),
              Ell(head + V(0, 5.6, -.6), (4.6, 4.2, 4.0), 'plume'),
              cone(head + V(0, 8.2, 1.6), head + V(0, 15.6, -3.6), 3.5, 'beak'),
              Ell(head + V(0, 9.5, -2.6), (2.7, 4.6, 1.2), 'beak', frame_z_pitch(-.2)),
              cone(head + V(0, 8.8, 3.2), head + V(0, 13.6, -1.2), 2.2, 'beak')]
    for sx in (-1, 1):
        prims += [feather(head + V(sx * 4.0, -4.6, 5.6), head + V(sx * 6.2, -8.4, 13.4), 2.1, 'plume2', V(1, 0, 0)),
                  feather(head + V(sx * 2.4, -5.4, 4.4), head + V(sx * 3.0, -10.4, 11.4), 2.1, 'plume', V(1, 0, 0))]
    prims += eyes(head + V(0, 0, 1.8), 5.9, 3.3, 3.4)
    # eagle forelegs with scaly talons, lion hind legs with paws, a tufted lion tail
    for hx, hy, off, front in ((-6.2, 12, 0, True), (6.2, 12, .5, True), (-6.4, -13.5, .5, False), (6.4, -13.5, 0, False)):
        hip = V(hx, hy, 28 + z0)
        foot = stride_foot(hx, hy, gait(k, n, off), 8 if front else 7.5, 6.5, spread=1.06) if run else V(hx * 1.06, hy, .5)
        knee, ankle, foot = leg_ik(hip, foot, 12, 11.4, V(0, -1 if front else 1, 0))
        prims += [limb(hip, knee, 4.7 if front else 5.0, 'plume' if front else 'fur'), limb(knee, ankle, 3.0 if front else 3.5, 'talon' if front else 'fur'),
                  Ell(knee, (3.7, 3.7, 3.7), 'plume' if front else 'fur')]
        if front:
            prims += [Ell(foot + V(0, 1.4, 1.4), (3.4, 4.4, 2.1), 'talon')] + [Ell(foot + V(dx * 1.7, 5.4, .8), (.9, 2.4, .9), 'talon') for dx in (-1, 0, 1)]
        else:
            prims += paw(foot, 'fur', 'beak', 4.1, 4.8)
    tail, tip = swish(V(0, -22, 33 + z0), 'tail', 4, 3.4, 'fur', S_(ph * (2 if run else 1)) * (4 if run else 2.5), rise=4 if run else 1.5, drop=2.6, length=5.6, ext=2.4)
    prims += tail + [Ell(tip + V(0, -2.6, .5), (4.4, 5.4, 4.2), 'plume2'), Ell(tip + V(0, -5.4, .2), (3.2, 4, 3.1), 'plume')]
    # wings: folded at rest, beating in the run (the rider sits between them)
    spread = .22 + (.1 * S_(ph)) if not run else .7 + .22 * S_(ph - .6)
    flap = (S_(ph - .4) * .22 + .05) if not run else (.1 + .42 * S_(ph - .5))
    for sx in (-1, 1):
        prims += wing(sx, V(sx * 9.6, 4, 44 + z0), spread, flap)
    prims += saddle(-2.5, 43.5 + z0, 9.6, 9)
    return prims, z0


# name -> (builder, materials, flat materials, seat). seat: `raise` lifts the rider so the pelvis sits on the saddle,
# `cut` hides the rider below that world height (the legs vanish into the barrel), `shadow` is the ground shadow (rx, ry).
REGISTRY = {
    'horse': (horse, HORSE, FLAT, {'scale': 1.3, 'raise': 25, 'cut': 34, 'shadow': (34, 9), 'coat': 'coat'}),
    'raptor': (raptor, RAPTOR, FLAT, {'scale': 1.12, 'raise': 30, 'cut': 44, 'shadow': (22, 8), 'coat': 'skin'}),
    'lizard': (lizard, LIZARD, FLAT, {'scale': 1.25, 'raise': 15, 'cut': 28, 'shadow': (38, 10), 'coat': 'hide'}),
    'sabertooth': (sabertooth, SABER, FLAT, {'scale': 1.25, 'raise': 20, 'cut': 30, 'shadow': (36, 10), 'coat': 'fur'}),
    'gryphon': (gryphon, GRYPHON, FLAT, {'scale': 1.25, 'raise': 25, 'cut': 33, 'shadow': (34, 10), 'coat': 'fur'}),
}
