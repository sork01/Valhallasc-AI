"""Archetype builders for the cel-shaded redraws of zones 28-39 (quadruped, humanoid, bird, serpent, floater, moth).

They sit on the Art/mk toolkit of cathedral_reliquary_redraw.py (see cairn_cel_redraw.py for the hand-built shapes) and
draw the same cel look: one dark outline per part, hard colour bands, big glossy eyes with a shine pixel, chibi heads.
Each builder returns a namespace of anchor points (head, hands, ...) so a kind adds its own features around it,
and `pre`/`post` callbacks draw behind/in front of the head or body. Coordinates are Art coordinates (x from the foot
anchor, y up from the ground row); the creature faces +x.
"""
import math
from types import SimpleNamespace as NS

from cathedral_reliquary_redraw import Art, lerp
from make_crag_sprites import Palette
from cel_zone_common import diamond, star, timing  # noqa: F401  (re-exported for the zone scripts)


def _lenient(self, name):
    """A tone index past the group's last tone (`sail3` when `sail` has three) falls back to the brightest tone."""
    if name not in self.names and name[-1:].isdigit():
        base = name.rstrip('0123456789')
        k = int(name[len(base):])
        while k > 0:
            k -= 1
            if f'{base}{k}' in self.names:
                return self.names[f'{base}{k}']
    if name not in self.names and f'{name}1' in self.names:   # a bare group name picks its second tone
        return self.names[f'{name}1']
    return self.names[name]


Palette.__getitem__ = _lenient


def parts(a):
    T = a.T
    if '_fixed' not in T:   # the walk/idle bobs of cel_zone_common never repeat inside a clip (the build asserts that)
        T['bob'] = timing(T['clip'], T['n'])['bob']
        T['_fixed'] = True
    return T['fall'], T['wind'], T['strike'], T['bob'], T['sw']


def burst(a, x, y, name, count=4, r=2.2, step=3, shape='star'):
    """Attack sparkles flying off to the right, kept inside the frame."""
    for k in range(count):
        px, py = min(x + k * step, 40), y - 4 + (k * 5) % 11
        if shape == 'diamond':
            diamond(a, px, py, r * .7, r, name)
        else:
            star(a, px, py, r, name)


def spark(a, name, x, y, **kw):
    if a.T['clip'] == 'attack' and a.T['n'] in (3, 4, 5):
        burst(a, x, y, name, **kw)


def mouth_open(a, x, y, w, group='mouth'):
    T = a.T
    a.e(x, y, w, 1.6 + max(T['wind'] * .4, T['strike']) * 2.6, group)


# ------------------------------------------------------------------------------------------------
def quad(a, body, belly=None, leg=None, foot=None, L=24, Hh=11, base=16, legw=3.2, stance=(-18, -9, 8, 17),
         hr=(11.4, 9.2), hdx=21, hdy=10, ox=-3, pk=.94, hgroup=None, snout=True, nose='nose', blush='blush',
         iris='iris', tail=None, pre=None, post=None, bigeye=4.4, footw=3.4, lift=5, tailpre=True, k=1.):
    """A side-on four-legged body with a big chibi head and a 3/4 face (two eyes, the far one smaller)."""
    fall, wind, strike, bob, sw = parts(a)
    T = a.T
    clip, n = T['clip'], T['n']
    L, Hh, base, legw, hdx, hdy, footw = L * k, Hh * k, base * k, legw * k, hdx * k, hdy * k, footw * k
    hr, stance = (hr[0] * k, hr[1] * k), tuple(x * k for x in stance)
    a.ox, a.pk = ox, pk
    a.lift = fall * lift
    cy = base + bob * .5 - fall * base * .25
    lunge = strike * 4 - wind * 2
    for k, lx in enumerate(stance):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 3 if clip == 'walk' else 0
        a.c((lx * .9, cy - 1), (lx + 2 + (lunge if k > 1 else 0), 3 + up), legw, legw * .7, leg or body)
        a.e(lx + 3 + (lunge if k > 1 else 0), 2 + up, footw, 1.8, foot or leg or body)
    wav = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else sw * 3
    c = NS(a=a, T=T, cy=cy, lunge=lunge, wav=wav, hx=hdx + lunge, hy=cy + hdy - wind * 2, L=L, Hh=Hh, k=k, hr=hr)
    if tail and tailpre:
        tail(c)
    a.e(-2, cy + 3, L, Hh, body)
    if belly:
        a.e(2, cy - 3, L * .64, Hh * .44, belly, out=False)
    if pre:
        pre(c)
    hx, hy = c.hx, c.hy
    a.e(hx - 4, hy + 8, 3, 3, hgroup or body)
    a.e(hx + 4, hy + 8, 3, 3, hgroup or body)
    a.e(hx, hy, hr[0], hr[1], hgroup or body)
    a.e(hx - 4, hy + 4, hr[0] * .52, 3, hgroup or body, out=False)
    if snout:
        a.e(hx + 6, hy - 3, 6.4, 4.2, belly or body)
        if nose:
            a.dot(hx + 10, hy - 1, nose, 3)
    a.eye(hx - 1.8, hy + 2.6, bigeye, iris=iris, look=(.8, .1))
    a.eye(hx + 6.4, hy + 2.4, bigeye * .82, iris=iris, look=(.9, .1))
    if blush:
        a.dot(hx - 7, hy - 2, blush, 2)
    jaw = max(wind * .5, strike) * 3
    if jaw > 1.2:
        a.line((hx + 3, hy - 6 - jaw * .5), (hx + 9, hy - 6 - jaw * .5), 'ink', 1 + int(jaw * .7))
    else:
        a.line((hx + 3, hy - 6), (hx + 8, hy - 6), 'ink', 1)
    if tail and not tailpre:
        tail(c)
    if post:
        post(c)
    return c


# ------------------------------------------------------------------------------------------------
def humanoid(a, torso, skin, leg=None, arm=None, hand=None, foot=None, w=13, legh=16, th=22, hr=(10, 10.4), robe=False,
             hem=None, pre=None, post=None, weapon=None, hdx=2, iris='iris', blush='blush', mouth='mouth', pk=1.,
             lift=5, eyes=True, armw=3.4, ox=0, handr=3.4):
    """A chibi standing figure: legs (or a robe hem), torso band, two arms (the near one swings), big head."""
    fall, wind, strike, bob, sw = parts(a)
    T = a.T
    clip, n = T['clip'], T['n']
    a.pk, a.ox = pk, ox
    a.lift = fall * lift
    b = bob * .6
    top = legh + th + b
    if robe:
        a.band([(-w * .7, top), (w * .7, top), (w * 1.05 + sw * .6, 2), (-w * 1.05 + sw * .6, 2)], torso)
        a.line((-w * .3, top - 4), (-w * .45 + sw * .4, 5), torso + '0', 2)
        if hem:
            a.e(sw * .6, 3, w * 1.05, 3, hem)
    else:
        for s in (-1, 1):
            up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
            a.c((s * w * .42, legh), (s * (w * .5 + 1), 4 + up), 3.6, 3, leg or torso)
            a.e(s * (w * .5 + 3), 2.6 + up, 4.8, 2.4, foot or leg or torso)
        a.band([(-w * .75, legh + 3), (w * .75, legh + 3), (w, top), (-w, top)], torso)
    arm = arm or torso
    hand = hand or skin
    far = (-w - 7 + sw * 1.5, top - 12 + b * .3 - fall * 6)
    a.c((-w + 1, top - 3), far, armw, armw * .9, arm)
    a.e(far[0], far[1], handr, handr, hand)
    near = (lerp(lerp(w + 6, w + 4, wind), w + 11, strike), lerp(lerp(top - 12, top + 10, wind), top - 17, strike) + b * .3)
    if clip == 'die':
        near = (lerp(w + 6, w + 12, fall), lerp(top - 12, 6, fall))
    a.c((w - 1, top - 3), near, armw + .4, armw, arm)
    hx, hy = hdx + strike * 2, top + hr[1] - 3
    c = NS(a=a, T=T, top=top, hx=hx, hy=hy, near=near, far=far, w=w, b=b, hr=hr)
    if pre:
        pre(c)
    a.e(hx, hy, hr[0], hr[1], skin)
    a.e(hx - hr[0] * .45, hy + hr[1] * .45, hr[0] * .5, 3, skin, out=False)
    if eyes:
        a.eye(hx - 4.4, hy + 1.6, 4.4, iris=iris, look=(.4, .1))
        a.eye(hx + 5.6, hy + 1.6, 4, iris=iris, look=(.8, .1))
        if blush:
            a.dot(hx - 10, hy - 3, blush, 3)
        if mouth and f'{mouth}0' in a.p.names:
            a.e(hx + 1, hy - 6, 4.4, 1.5 + max(wind * .4, strike) * 2.6, mouth)
    a.e(near[0], near[1], handr + .4, handr + .4, hand)
    if weapon:
        weapon(c)
    if post:
        post(c)
    return c


# ------------------------------------------------------------------------------------------------
def bird(a, body, belly=None, wing=None, leg='leg', claw=None, beak='beak', R=(14, 15), ox=-4, pk=.9, hr=(11.4, 10.4),
         iris='iris', blush='blush', tailn=3, tail=None, pre=None, post=None, base=32, flapamp=3, longleg=10):
    """A perched bird facing right: legs, round body, a folded or flapping wing, big head with a beak."""
    fall, wind, strike, bob, sw = parts(a)
    T = a.T
    clip, n = T['clip'], T['n']
    a.ox, a.pk = ox, pk
    a.lift = fall * 6
    flap = math.sin(n * math.pi / 3) * flapamp if clip == 'idle' else 0
    if clip == 'attack':
        flap = (-4, -9, -14, 8, 10, 4, 1, 0)[n]
    cy = base + bob * .6 - fall * 8
    c = NS(a=a, T=T, cy=cy, flap=flap)
    for k in range(tailn):
        a.c((-6, cy - 4), (-20 - k * 2 + sw * 1.5, 8 + k * 3), 3.6, 1.6, tail or body)
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 4 - 2, cy - longleg - 1), (s * 5 - 1, 5 + up), 2, 1.6, leg)
        a.e(s * 5 + 2, 3 + up, 4.6, 1.8, claw or leg)
    a.e(0, cy, R[0], R[1], body)
    if belly:
        a.e(5, cy - 3, R[0] * .55, R[1] * .62, belly, out=False)
    if pre:
        pre(c)
    wing = wing or body
    a.e(-10, cy + 1 + flap * .8, 9, 14, wing, ang=.25 - flap * .03)
    hx, hy = 8 + strike * 5 - wind * 3, cy + 20 + wind * 2 - strike * 5
    c.hx, c.hy = hx, hy
    a.e(hx, hy, hr[0], hr[1], body)
    a.e(hx - 4, hy + 4, 6, 3, body, out=False)
    jaw = max(wind * .5, strike) * 3
    a.poly([(hx + 6, hy + 3), (hx + 19, hy - 1 - jaw * .4), (hx + 6, hy - 4 - jaw)], beak + '1')
    a.line((hx + 7, hy - 1), (hx + 16, hy - 1.4), beak + '0', 1)
    a.eye(hx + .6, hy + 2.6, 4.6, iris=iris, look=(.8, .1))
    if blush:
        a.dot(hx - 5, hy - 2, blush, 2)
    if post:
        post(c)
    return c


# ------------------------------------------------------------------------------------------------
def serpent(a, skin, belly=None, mark=None, segs=7, length=30, rise=30, hr=(11.4, 8.4), iris='iris', blush='blush',
            ox=-6, pk=.94, tongue='tongue1', tail_tip=True, pre=None, post=None, thick=5, crest=None, lunge=12):
    """A low S of coils rising to a raised chibi head; the head lunges in the attack."""
    fall, wind, strike, bob, sw = parts(a)
    T = a.T
    n = T['n']
    a.ox, a.pk = ox, pk
    b = bob * .5
    wav = math.sin(n * math.pi / 3) * 2 if T['clip'] == 'idle' else sw * 2
    pts = [(-length + 0, 6), (-length * .73, 8), (-length * .4, 7), (-length * .07, 8), (length * .27, 11),
           (length * .4 + wav, rise * .65), (length * .37 + wav, rise + b)]
    for i in range(len(pts) - 1):
        r = thick + i * .5
        a.c(pts[i], pts[i + 1], r, r + .5, skin)
    if mark:
        for i in range(len(pts) - 1):
            a.dot(pts[i][0] - 1, pts[i][1] + 1, mark, 3)
    if tail_tip:
        a.c(pts[0], (pts[0][0] - 8, 4 + sw * 2), 4, 1.2, skin)
    if belly:
        a.c(pts[4], pts[5], 2.4, 2.4, belly, out=False)
    hx = length * .47 + strike * lunge - wind * 5 + wav
    hy = rise + 10 + b - strike * 12 + wind * 3 - fall * rise * .5
    c = NS(a=a, T=T, hx=hx, hy=hy, pts=pts)
    a.c(pts[-1], (hx - 2, hy - 4), thick + .6, thick + .6, skin)
    if pre:
        pre(c)
    a.e(hx, hy, hr[0], hr[1], skin)
    a.e(hx - 4, hy + 3, 6, 2.6, skin, out=False)
    a.e(hx + 6, hy - 2, 6, 4, belly or skin)
    if crest:
        for k in range(3):
            diamond(a, hx - 5 + k * 4, hy + 8, 1.8, 2.6, crest)
    a.eye(hx - 1.4, hy + 2.6, 4.2, iris=iris, look=(.8, .1))
    a.eye(hx + 6, hy + 2.4, 3.2, iris=iris, look=(.9, .1))
    if blush:
        a.dot(hx - 7, hy - 1, blush, 2)
    jaw = max(wind * .5, strike) * 3
    a.line((hx + 4, hy - 4 - jaw), (hx + 12, hy - 4 - jaw), 'ink', 1)
    if tongue:
        tl = 6 + strike * 5
        a.line((hx + 11, hy - 4 - jaw), (hx + 11 + tl, hy - 4 - jaw), tongue, 1)
        a.line((hx + 11 + tl, hy - 4 - jaw), (hx + 13 + tl, hy - 2 - jaw), tongue, 1)
        a.line((hx + 11 + tl, hy - 4 - jaw), (hx + 13 + tl, hy - 6 - jaw), tongue, 1)
    if post:
        post(c)
    return c


# ------------------------------------------------------------------------------------------------
def floater(a, body, R=(18, 18), cy=40, glow=None, iris='iris', blush='blush', hover=3, pre=None, post=None, pk=.9, ox=-2,
            eye=5., mouth='mouth', shadow='shadow'):
    """A round hovering body with one big face, bobbing; strike lunges it forward."""
    fall, wind, strike, bob, sw = parts(a)
    T = a.T
    a.pk, a.ox = pk, ox
    a.lift = fall * 8
    y = cy + bob * 1.2 + hover - fall * cy * .6
    x = strike * 6 - wind * 4
    c = NS(a=a, T=T, x=x, y=y)
    if f'{shadow}0' in a.p.names:
        a.e(x * .3, 3, R[0] * .8, 2.2, shadow, out=False)
    if pre:
        pre(c)
    a.e(x, y, R[0], R[1], body)
    a.e(x - R[0] * .3, y + R[1] * .45, R[0] * .55, R[1] * .26, body, out=False)
    a.eye(x + 1, y + 1, eye, iris=iris, look=(.7, .1))
    a.eye(x + R[0] * .5 + 1, y + 1, eye * .82, iris=iris, look=(.9, .1))
    if blush:
        a.dot(x - R[0] * .55, y - R[1] * .3, blush, 3)
    if mouth and f'{mouth}0' in a.p.names:
        a.e(x + R[0] * .3, y - R[1] * .5, 3.6, 1.2 + max(wind * .4, strike) * 2.4, mouth)
    if post:
        post(c)
    return c


# ------------------------------------------------------------------------------------------------
def wingpair(a, x, y, group, span=26, h=16, flap=0., tip='', ang=0.5):
    """Two wing blades above/behind a body point, flapping by `flap` (positive = raised)."""
    for k, s in enumerate((-1, 1)):
        up = h * (.55 + .45 * flap)
        a.e(x + s * span * .5 - 4 * k, y + up * .5, span * .42, up * .8, group, ang=s * ang * (1 - .6 * flap))


def tendrils(a, x0, y0, count, spread, length, group, r0=2.6, r1=1., sway=3.):
    """Hanging tendrils from (x0, y0), swaying with the clip phase (each one out of step with its neighbour)."""
    n = a.T['n']
    for i in range(count):
        x = x0 + (i - (count - 1) / 2) * spread
        s = math.sin(n * math.pi / 3 + i * 1.3) * sway
        mid = (x + s * .6, y0 - length * .5)
        a.c((x, y0), mid, r0, (r0 + r1) / 2, group)
        a.c(mid, (x + s, max(3, y0 - length)), (r0 + r1) / 2, r1, group)


def moth(a, body, wing, wing2=None, spot=None, R=(8, 12), hr=(9, 8.4), cy=36, span=1., iris='iris', blush='blush',
         ant='ant', glow=None, pre=None, post=None, pk=.9, ox=-3, feet=True):
    """A hovering moth seen from the side: slim body, a big head with feathery antennae, upper and lower wings that flap."""
    fall, wind, strike, bob, sw = parts(a)
    T = a.T
    clip, n = T['clip'], T['n']
    a.pk, a.ox = pk, ox
    a.lift = fall * 6
    f = math.sin(n * math.pi / 3) if clip == 'idle' else math.sin(n * math.pi / 2) if clip == 'walk' else 0
    if clip == 'attack':
        f = (-.4, -.8, -1, .9, 1, .5, .1, 0)[n]
    if clip == 'hurt':
        f = (.6, .2, -.2, 0)[n]
    if clip == 'die':
        f = (0, .4, .2, 0, -.2, -.3, -.3, -.3)[n] * (1 - fall)
    x = strike * 6 - wind * 4
    y = cy + bob * 1.4 - fall * cy * .72
    c = NS(a=a, T=T, x=x, y=y, f=f)
    wing2 = wing2 or wing
    if glow and f'{glow}0' in a.p.names:
        a.e(x - 2, y - R[1] * .5, R[0] * 1.8, R[0] * 1.8, glow, out=False)
    # back (far) wings first, then the body, then the near wings over it
    a.e(x - 10 * span, y + 9 * span + f * 5, 8 * span, 14 * span, wing, ang=.55 - f * .3)
    a.e(x - 9 * span, y - 4 - f * 3, 7 * span, 10 * span, wing2, ang=1.0 - f * .2)
    a.e(x, y, R[0], R[1], body)
    if glow:
        a.e(x - 2, y - R[1] * .45, R[0] * .7, R[1] * .5, glow)
    if pre:
        pre(c)
    a.e(x + 4 * span, y + 11 * span + f * 3.2, 11 * span, 17 * span, wing, ang=-.42 + f * .32)
    a.e(x + 4 * span, y + 14 * span + f * 3.2, 5 * span, 9 * span, wing2, ang=-.42 + f * .32, out=False)
    if spot:
        a.e(x + 4 * span, y + 16 * span + f * 3.2, 3.2 * span, 3.2 * span, spot)
    hx, hy = x + 5 + strike * 3, y + R[1] + 3
    c.hx, c.hy = hx, hy
    for s in (0, 1):
        a.c((hx + s * 4, hy + hr[1] - 2), (hx + 2 + s * 8 + sw, hy + hr[1] + 8 - s * 2), 1.6, 1, ant)
    a.e(hx, hy, hr[0], hr[1], body)
    a.e(hx - 3, hy + 3.4, hr[0] * .5, 2.6, body, out=False)
    a.eye(hx - 1.6, hy + 1.2, 4.2, iris=iris, look=(.7, .1))
    a.eye(hx + 5.4, hy + 1.2, 3.6, iris=iris, look=(.9, .1))
    if blush:
        a.dot(hx - 6, hy - 2, blush, 2)
    a.line((hx + 3, hy - 5 - max(wind * .5, strike) * 1.4), (hx + 8, hy - 5 - max(wind * .5, strike) * 1.4), 'ink', 1)
    if feet:
        for s in (-1, 1):
            a.c((x + s * 3, y - R[1] + 2), (x + s * 4 + 1, y - R[1] - 6), 1.4, 1, ant)
    if post:
        post(c)
    return c


def spider(a, body, abd, leg, R=(14, 12), hr=(10.4, 9), base=22, legspan=11, iris='iris', blush='blush', fang='fang',
           ox=-3, pk=.9, pre=None, post=None, thickness=2.6, abdx=-14):
    """A side-on spider: big abdomen at the back, a chibi head with two big eyes in front, four visible legs."""
    fall, wind, strike, bob, sw = parts(a)
    T = a.T
    clip, n = T['clip'], T['n']
    a.pk, a.ox = pk, ox
    a.lift = fall * 5
    cy = base + bob * .6 - fall * base * .45
    c = NS(a=a, T=T, cy=cy)
    for k in range(4):
        x0 = -10 + k * 7
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        kx = x0 + (k - 1.5) * 8 + strike * (3 if k > 1 else 0)
        foot = (x0 + (k - 1.5) * legspan, 3 + up)
        a.c((x0, cy), (kx, cy + 15 - fall * 9), thickness, thickness * .8, leg)
        a.c((kx, cy + 15 - fall * 9), foot, thickness * .8, thickness * .5, leg)
    if pre:
        pre(c)
    a.e(abdx, cy + 3, R[0], R[1], abd)
    a.e(abdx - 3, cy + 8, R[0] * .5, 3, abd, out=False)
    a.e(8, cy + 1, 9, 8, body)
    hx, hy = 16 + strike * 5 - wind * 2, cy + 3 - wind * 1
    c.hx, c.hy = hx, hy
    a.e(hx, hy, hr[0], hr[1], body)
    a.e(hx - 3, hy + 4, hr[0] * .5, 2.6, body, out=False)
    a.eye(hx - 1, hy + 2.6, 4.6, iris=iris, look=(.7, .1))
    a.eye(hx + 7, hy + 2.4, 3.8, iris=iris, look=(.9, .1))
    if blush:
        a.dot(hx - 6, hy - 2, blush, 2)
    g = max(wind * .5, strike) * 3
    for s in (0, 1):
        a.poly([(hx + 3 + s * 4, hy - 5), (hx + 5 + s * 4, hy - 5), (hx + 4 + s * 4 + g * .3, hy - 10 - g)], fang + '1', out=False)
    if post:
        post(c)
    return c
