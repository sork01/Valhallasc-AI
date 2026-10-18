"""Cel-shaded Undervault enemies (zone 5) for make_vault_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes (glowing
sockets for the dead), chibi proportions. 96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/vault_cel_redraw.py [kind...]` writes contact sheets to test-results/vault-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, crystal, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking')

BONE = ('#7a7462', '#b8b29a', '#e8e2cc', '#fffbea')
PALETTES = {
    'thrall': mk(bone=BONE, cloth=('#2a3a2a', '#4a6a3e', '#7aa458'), wood=('#4a3220', '#7a5634', '#b08454'),
                 iron=('#3a4252', '#7a869c', '#c0cce0'), glow=('#b8ffb0', '#5ae85a'), iris='#38d838',
                 blade=('#6a7690', '#b8c6dc', '#f0f6ff'), rag=('#3a2a1e', '#6a4a30')),
    'archer': mk(bone=BONE, hood=('#2e2418', '#5a4430', '#8a6a46'), wood=('#4a3220', '#7a5634', '#c08a54'),
                 glow=('#ffe8b0', '#ffc23a'), iris='#ffb61e', cord=('#d8d0b8', '#fff7e6'),
                 fletch=('#a83a2a', '#e86a4a'), rag=('#3a2a1e', '#6a4a30')),
    'acolyte': mk(robe=('#1c1036', '#3c2270', '#6a44b4', '#a888f0'), bone=BONE, gold=('#7a4f12', '#c98f28', '#f6d467'),
                  glow=('#f0dcff', '#b46cff'), iris='#c88aff', orb=('#4a1a8a', '#9a50e0', '#e0b8ff', '#f8ecff'),
                  staff=('#4a3220', '#8a6a48')),
    'gatewarden': mk(bone=BONE, mail=('#2c3444', '#586882', '#98a8c4', '#d8e4f6'), horn=('#8a826a', '#d2cab0', '#fff6dc'),
                     cloth=('#6a1c1c', '#a83030', '#e05a4a'), iron=('#3a4252', '#7a869c', '#c0cce0'),
                     wood=('#4a3220', '#7a5634', '#b08454'), glow=('#ffd2b0', '#ff7a3a'), iris='#ff6a2a',
                     shield=('#d8d0b8', '#fff1d0')),
    'choir': mk(gown=('#0e3a4a', '#1f7a8e', '#52bcc8', '#b0f0f0'), skin=('#a8d2e0', '#dff4fa', '#fbffff'),
                hair=('#3a6aa0', '#78b0e0', '#c4e6ff'), crown=('#8a98b0', '#d4deee', '#fbfeff'),
                iris='#2a8ad8', note=('#ffffff', '#bfeaff'), mouth=('#4a1c3c', '#d8588a'), blush='#ff9ac0',
                wisp=('#5ac0d0', '#a8eef0')),
    'colossus': mk(steel=('#262c3c', '#4a5670', '#8294b4', '#c8d6ee'), core=('#0e4a7a', '#2a9ae0', '#8ae0ff', '#e8fbff'),
                   rust=('#4a2a1c', '#7a4a30', '#a8683e'), bolt=('#7a869c', '#c0cce0'), glow=('#d8fbff', '#58d8ff'),
                   iris='#20b8f0', steam=('#aab6c8', '#e6eef8')),
    'hollowking': mk(bone=BONE, armor=('#14221a', '#2e4a38', '#54805c', '#8ac290'), gold=('#7a4f12', '#c98f28', '#f6d467', '#fff0a0'),
                     cape=('#2a1450', '#4c2a8a', '#7a52c4'), flame=('#1a8a3a', '#46e06c', '#c8fcd2'),
                     glow=('#d0ffd8', '#4ae870'), iris='#38e86a', blade=('#4a7a5a', '#a8e8b8', '#f0fff4'),
                     haft=('#4a3220', '#8a6a48')),
}
R.PALETTES.update(PALETTES)


def socket(a, x, y, r, iris='iris', state=None):
    """A dark eye socket with a glowing, shiny iris (a big glossy eye for the undead)."""
    state = state or a.T['state']
    cx, cy = a.g(x, y)
    if state == 'dead':
        a.f.line((cx - r + 1, cy - r + 1), (cx + r - 1, cy + r - 1), 'ink', 2)
        a.f.line((cx - r + 1, cy + r - 1), (cx + r - 1, cy - r + 1), 'ink', 2)
        return
    if a.T['blink'] and state == 'open':
        a.f.line((cx - r, cy), (cx + r, cy), 'ink', 2)
        return
    a.f.flat(ellipsoid(cx, cy, r, r * 1.12)[0], 'ink', outline=True)
    a.f.flat(ellipsoid(cx + .5, cy + .3, r * .64, r * .8)[0], iris)
    a.f.dots([(cx - r * .25, cy - r * .35), (cx - r * .25 + 1, cy - r * .35)], 'shine')
    if state == 'angry':
        a.f.line((cx - r - 1, cy - r * 1.4), (cx + r + 1, cy - r * .7), 'ink', 2)


def skull(a, hx, hy, r=12.4, jaw=0.):
    a.e(hx + 3, hy - 7 - jaw, 7.4, 3.2, 'bone')
    a.e(hx, hy, r, r * .92, 'bone')
    a.e(hx - 4, hy + 5, r * .55, 3.4, 'bone', out=False)
    for k in range(4):
        a.line((hx + 0 + k * 2.6, hy - 6.6 - jaw), (hx + 0 + k * 2.6, hy - 9 - jaw), 'ink', 1)


def legs(a, t, s=1., group='bone'):
    for sg in (-1, 1):
        up = max(0, sg * math.sin(a.T['n'] * math.pi / 2)) * 4 if a.T['clip'] == 'walk' else 0
        a.c((sg * 5 * s, 22), (sg * 5 * s, 5 + up), 2.6, 2.2, group)
        a.e(sg * 5.4 * s, 3 + up, 5.2, 2.6, group)


def ribs(a, cx, cy, w, h, fall=0.):
    a.e(cx, cy, w, h, 'bone')
    a.e(cx - w * .3, cy + h * .4, w * .5, h * .3, 'bone', out=False)
    for k in range(3):
        a.line((cx - w * .8, cy + h * .35 - k * h * .45), (cx + w * .8, cy + h * .35 - k * h * .45), 'ink', 1)
    a.line((cx, cy + h * .8), (cx, cy - h * .8), 'ink', 1)


# ------------------------------------------------------------------------------------------------
def thrall(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('thrall', clip, n, sy=1 - fall * .5)
    b = bob * .5
    legs(a, T, 1.15)
    a.band([(-11, 24), (11, 24), (13, 14), (-13, 14)], 'cloth')
    # round shield on the far arm
    sx, sy_ = -22 + wind * -2, 34 + b
    a.e(sx, sy_, 10.6, 11.6, 'wood')
    a.e(sx, sy_, 3.4, 3.4, 'iron')
    a.line((sx - 9, sy_), (sx + 9, sy_), 'iron1', 1)
    a.c((-9, 40 + b), (sx + 6, sy_ + 2), 2.8, 2.6, 'bone')
    ribs(a, 0, 34 + b, 10.4, 9.6)
    a.line((-11, 26 + b), (11, 26 + b), 'rag1', 2)
    hand = (lerp(lerp(17, 14, wind), 24, strike), lerp(lerp(33, 40, wind), 33, strike))
    ang = lerp(lerp(1.4, 1.95, wind), .15, strike)
    if clip == 'die':
        hand = (lerp(17, 22, fall), lerp(33, 8, fall))
        ang = lerp(1.4, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    tip = (min(hand[0] + dx * 24, 34), min(hand[1] + dy * 24, 70))
    a.line(hand, tip, 'ink', 5)
    a.line(hand, tip, 'blade1', 3)
    a.line((hand[0] - dy * 4, hand[1] + dx * 4), (hand[0] + dy * 4, hand[1] - dx * 4), 'iron1', 2)
    a.c((9, 40 + b), hand, 2.8, 2.6, 'bone')
    a.e(hand[0], hand[1], 3, 3, 'bone')
    for sg in (-1, 1):
        a.e(sg * 12.5, 41 + b, 4.6, 4, 'iron')
    skull(a, 1, 56 + b, 12.4, max(wind * .5, strike) * 3)
    socket(a, -3.6, 58.4 + b, 4.1)
    socket(a, 6.4, 58.4 + b, 3.8)
    a.dot(-9, 52 + b, 'rag1', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(tip[0] + 4 + k * 4, 37), tip[1] - 2 + k * 4, 2.4, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def archer(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('archer', clip, n, sy=1 - fall * .5)
    b = bob * .5
    legs(a, T, 1.1)
    # quiver on the back
    a.c((-12, 30 + b), (-17, 46 + b), 3.4, 3.4, 'wood')
    for k in range(3):
        a.line((-17 + k * 1.8, 47 + b), (-18 + k * 2.4, 52 + b), 'fletch1', 2)
    a.band([(-11, 26), (11, 26), (14, 12), (-14, 12)], 'hood')
    ribs(a, 0, 34 + b, 9.6, 9)
    # bow arm: the bow is a big recurve held forward, drawn back on the wind-up
    draw = max(wind, 0)
    bx = lerp(20, 24, strike)
    by_ = 40 + b
    if clip == 'die':
        bx, by_ = lerp(20, 24, fall), lerp(40, 25, fall)
    a.c((8, 41 + b), (bx, by_), 2.8, 2.6, 'bone')
    top, bot = (bx + 3, by_ + 22), (bx + 3, by_ - 22)
    mid = (bx + 8 - draw * 0, by_)
    for p, q in ((top, mid), (mid, bot)):
        a.line(p, q, 'ink', 5)
        a.line(p, q, 'wood1', 3)
    nock = (bx - 6 - draw * 8, by_)
    a.line(top, nock, 'cord0', 1)
    a.line(bot, nock, 'cord0', 1)
    if clip == 'attack' and n < 3 or (clip == 'attack' and n == 3):
        a.line(nock, (bx + 12, by_), 'wood2', 1)
    if clip == 'attack' and n in (4, 5, 6):
        ax_ = min(bx + 12 + (n - 4) * 7, 36)
        a.line((ax_ - 14, by_), (ax_, by_), 'ink', 3)
        a.line((ax_ - 14, by_), (ax_, by_), 'wood2', 1)
        a.poly([(ax_, by_ + 2.4), (ax_ + 5, by_), (ax_, by_ - 2.4)], 'cord1')
    a.e(bx, by_, 3, 3, 'bone')
    a.c((-9, 41 + b), (-15, 33 + b + wind * 4), 2.8, 2.6, 'bone')
    # hooded skull
    hx, hy = 1, 56 + b
    a.poly([(hx - 12, hy + 4), (hx - 20, hy - 6), (hx - 9, hy - 3)], 'hood1')
    a.e(hx, hy, 13.8, 13.2, 'hood')
    a.e(hx - 4, hy + 6, 7, 4, 'hood', out=False)
    a.f.flat(ellipsoid(*a.g(hx + 2.4, hy - 2), 9.4, 8.6 * a.sy)[0], 'ink')
    socket(a, hx - 1.8, hy - .6, 3.8)
    socket(a, hx + 7.4, hy - .6, 3.4)
    a.line((hx - 11, hy + 3), (hx + 12, hy + 3), 'hood0', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def acolyte(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('acolyte', clip, n, sy=1 - fall * .55)
    sway = math.sin(n * math.pi / 3) * 1.4 if clip == 'idle' else sw * 1.8
    b = bob * .6
    hem = [(-21, 3), (-16, 10), (-12, 2), (-6, 10), (0, 2), (6, 10), (12, 2), (17, 10), (21, 3)]
    robe = [(-9, 48 + b), (9, 48 + b), (15, 30), (21 + sway, 10)] + hem[::-1][:0] + [(22 + sway * .5, 4), (-22 + sway * .5, 4), (-21, 10), (-15, 30)]
    a.band(robe, 'robe')
    a.band([(-18 + sway * .3, 5), (-12, 11), (-6, 4), (0, 11), (6, 4), (12, 11), (19, 5)], 'robe', out=False)
    a.line((-12, 33 + b), (12, 33 + b), 'gold1', 2)
    a.poly([(0, 33 + b), (3, 30 + b), (0, 27 + b), (-3, 30 + b)], 'gold2')
    # staff with a glowing orb, raised on the wind-up and thrust forward
    hand = (lerp(lerp(18, 14, wind), 22, strike), lerp(lerp(34, 44, wind), 34, strike))
    sx = hand[0]
    top = (sx + lerp(lerp(2, -3, wind), 8, strike), lerp(lerp(68, 74, wind), 60, strike))
    low = (sx - 1, 3)
    if clip == 'die':
        hand = (lerp(18, 22, fall), lerp(34, 8, fall))
        top = (lerp(20, 36, fall), lerp(68, 12, fall))
        low = (lerp(17, 6, fall), 3)
    top = (min(top[0], 30), top[1])
    a.line(low, top, 'ink', 4)
    a.line(low, top, 'staff1', 2)
    a.e(top[0], top[1] + 4, 6.2, 6.2, 'orb')
    a.dot(top[0] - 2, top[1] + 6, 'shine', 2)
    a.c((9, 44 + b), hand, 3.8, 3.4, 'robe')
    a.e(hand[0], hand[1], 3, 3, 'bone')
    far = (-19, 36 + b)
    a.c((-9, 44 + b), far, 3.8, 3.4, 'robe')
    a.e(far[0], far[1], 3, 3, 'bone')
    # hood around a pale skull with violet eyes
    hx, hy = 1 + sway * .3, 59 + b
    a.poly([(hx - 12, hy + 3), (hx - 21 - sway, hy + 12), (hx - 6, hy + 10)], 'robe1')
    a.e(hx, hy, 14, 13, 'robe')
    a.e(hx - 4, hy + 6, 8, 4.4, 'robe', out=False)
    a.e(hx + 3, hy - 1.5, 10, 9.2, 'bone')
    a.e(hx + 1, hy - 4.6, 6, 2.6, 'bone', out=False)
    socket(a, hx - .4, hy - .6, 3.8)
    socket(a, hx + 8.6, hy - .6, 3.4)
    for k in range(4):
        a.line((hx - 1 + k * 2.8, hy - 8), (hx - 1 + k * 2.8, hy - 10), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(top[0] + 7 + k * 4, 37), top[1] - 6 + k * 3, 2.6, 'orb2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def gatewarden(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('gatewarden', clip, n, sy=1 - fall * .5)
    b = bob * .5
    for sg in (-1, 1):
        up = max(0, sg * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((sg * 8, 22), (sg * 8, 6 + up), 4.8, 4.2, 'mail')
        a.e(sg * 8.6, 4 + up, 7.4, 4, 'iron')
    # round shield with a red cross
    sx, sy_ = -25 + wind * -2, 36 + b
    a.e(sx, sy_, 12.4, 13.4, 'wood')
    a.e(sx, sy_, 9.4, 10.4, 'shield', out=False)
    a.line((sx, sy_ - 9), (sx, sy_ + 9), 'cloth1', 3)
    a.line((sx - 8, sy_), (sx + 8, sy_), 'cloth1', 3)
    a.e(sx, sy_, 3, 3, 'iron')
    a.c((-12, 41 + b), (sx + 6, sy_ + 2), 3.6, 3.2, 'mail')
    a.band([(-12, 25), (12, 25), (15, 15), (-15, 15)], 'cloth')
    a.e(0, 35 + b, 14.4, 12, 'mail')
    a.e(-5, 40 + b, 7.4, 4.2, 'mail', out=False)
    for k in range(3):
        a.line((-9, 31 + b + k * 4), (9, 31 + b + k * 4), 'mail0', 1)
    a.line((-14, 27 + b), (14, 27 + b), 'iron0', 2)
    # axe: long haft with a broad bearded blade
    hand = (lerp(lerp(19, 15, wind), 25, strike), lerp(lerp(34, 42, wind), 34, strike))
    ang = lerp(lerp(1.5, 2.0, wind), .2, strike)
    if clip == 'die':
        hand = (lerp(19, 24, fall), lerp(34, 8, fall))
        ang = lerp(1.5, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 14, hand[1] - dy * 14)
    top = (min(hand[0] + dx * 24, 24), min(hand[1] + dy * 24, 72))
    a.line(base, top, 'ink', 4)
    a.line(base, top, 'wood1', 2)
    px, py = dy, -dx
    blade = [(top[0] - dx * 8, top[1] - dy * 8), (top[0] + px * 13 - dx * 11, top[1] + py * 13 - dy * 11),
             (top[0] + px * 14 + dx * 6, top[1] + py * 14 + dy * 6), (top[0] + dx * 3, top[1] + dy * 3)]
    a.band(blade, 'iron')
    a.c((10, 42 + b), hand, 4.2, 3.8, 'mail')
    a.e(hand[0], hand[1], 4, 3.8, 'bone')
    for sg in (-1, 1):
        a.e(sg * 16, 44 + b, 7.8, 6.8, 'mail')
        a.dot(sg * 16 - 1, 47 + b, 'iron2', 2)
    # skull under a horned helm
    hx, hy = 1, 58 + b
    for sg in (-1, 1):
        a.poly([(hx + sg * 11, hy + 5), (hx + sg * 20, hy + 15), (hx + sg * 15, hy + 22), (hx + sg * 8, hy + 8)], 'horn1')
    skull(a, hx, hy - 1, 12.6, max(wind * .5, strike) * 3)
    a.e(hx, hy + 6, 13.6, 7.2, 'iron')
    a.poly([(hx - 3, hy + 3), (hx + 3, hy + 3), (hx + 2, hy - 7), (hx - 2, hy - 7)], 'iron1', out=False)
    socket(a, hx - 4.6, hy - 1.4, 3.8)
    socket(a, hx + 5.6, hy - 1.4, 3.4)
    a.line((hx - 13, hy + 2), (hx + 13, hy + 2), 'iron0', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(top[0] + 8 + k * 4, 37), top[1] - 6 + k * 4, 2.4, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def choir(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('choir', clip, n, sy=1 - fall * .55)
    a.lift = 5 + bob * 1.2 - fall * 5
    sway = math.sin(n * math.pi / 3) * 1.8 if clip == 'idle' else sw * 2
    # long hair streaming behind and a gown that dissolves into wisps
    hx, hy = 2 + sway * .3, 55
    a.band([(hx - 13, hy + 6), (hx + 6, hy + 8), (hx + 8, hy - 20), (hx + 4 - sway, hy - 36), (hx - 8 - sway, hy - 30),
            (hx - 18, hy - 16)], 'hair')
    rag = [-1, 1, 0, -1, 1][n % 5]
    hem = [(-21, 2), (-16, 9 + rag), (-12, 1), (-7, 10), (-2, 2), (4, 10 - rag), (9, 1), (14, 9), (19, 2)]
    gown = [(-9, 47), (9, 47), (15, 32), (21 + sway, 12)] + [(22 + sway * .5, 3), (-22 + sway * .5, 3), (-21, 12), (-15, 32)]
    a.band(gown, 'gown')
    a.band([(-19 + sway * .3, 4), (-14, 10 + rag), (-9, 3), (-4, 10), (1, 3), (6, 10 - rag), (11, 3), (16, 9), (20, 4)], 'gown', out=False)
    a.band([(-9, 44), (9, 44), (11, 36), (-11, 36)], 'skin', out=False) if False else None
    for k in range(4):
        a.dot(-14 + k * 9 + sway * .3, 1 + (k % 2) * 5, 'wisp1', 2)
    a.e(0, 41, 10, 7.4, 'gown')
    a.line((-10, 38), (10, 38), 'crown1', 2)
    # arms spread to sing; notes fly on the attack
    open_ = max(wind, strike)
    for sg in (-1, 1):
        hand = (sg * lerp(18, 25, open_), lerp(36, 46, open_) + (sg > 0) * strike * -4)
        a.c((sg * 9, 43), hand, 3.4, 2.9, 'gown')
        a.e(hand[0], hand[1], 3, 3, 'skin')
    # face
    a.e(hx, hy, 12.4, 11.6, 'skin')
    a.poly([(hx - 13, hy + 5), (hx - 8, hy - 3), (hx - 3, hy + 6), (hx + 2, hy - 2), (hx + 7, hy + 6), (hx + 13, hy - 1),
            (hx + 14, hy + 11), (hx - 14, hy + 11)], 'hair1')
    for k, (dx, h) in enumerate(((-8, 6), (-4, 9), (0, 12), (4, 9), (8, 6))):
        crystal(a, hx + dx, hy + 9, 2.2, h, 'crown', tilt=dx * .2)
    a.eye(hx + 2.4, hy - 2.4, 4.4, iris='iris')
    a.eye(hx + 10, hy - 2.4, 3.3, iris='iris')
    a.dot(hx - 4, hy - 6.4, 'blush', 3)
    o = max(wind * .6, strike) * 3
    a.e(hx + 5.6, hy - 7.6 - o * .4, 2.4 + o * .4, 1.4 + o, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            x = min(hx + 18 + k * 5 + (n - 3) * 2, 38)
            a.e(x, hy - 2 + (k % 2) * 8 - k, 2.2, 2.2, 'note')
            a.line((x + 2, hy - 2 + (k % 2) * 8 - k), (x + 2, hy + 4 + (k % 2) * 8 - k), 'note0', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def colossus(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('colossus', clip, n, sy=1 - fall * .45)
    b = bob * .8
    if clip != 'die':
        for k in range(3):
            rise = (n * 1.7 + k * 4) % 11
            a.e(-16 + k * 3 + rise * .3, 66 + b + rise * .7, 2.4 + rise * .2, 2.2 + rise * .18, 'steam', out=False)
    for sg in (-1, 1):
        up = max(0, math.sin(n * math.pi / 2 + (0 if sg < 0 else math.pi))) * 5 if clip == 'walk' else 0
        a.c((sg * 11, 20), (sg * 11 + fall * sg * 4, 7 + up), 8 * (1 - fall * .5), 8.6 * (1 - fall * .55), 'steel')
        a.e(sg * 11 + fall * sg * 5, 4 + up, 10.6, 4.6, 'steel')
        a.dot(sg * 11 - 2, 12 + up, 'bolt0', 2)
    a.c((-19, 42 + b), (-30 - fall * 3, 27 - fall * 14), 7, 6.6, 'steel')
    a.e(-31 - fall * 3, 23 - fall * 12, 9.6, 8.8, 'steel')
    a.e(0, 34 + b - fall * 8, 23, 19, 'steel')
    a.e(-8, 42 + b - fall * 8, 10, 6, 'steel', out=False)
    for k in range(3):
        a.line((-16, 26 + b + k * 6), (16, 26 + b + k * 6), 'steel0', 1)
    a.e(0, 35 + b - fall * 8, 8.4, 9.4, 'steel')
    if fall < .6:
        crystal(a, 0, 28 + b, 5.4, 16, 'core', tilt=0)
    for (x, y) in ((-14, 40), (14, 40), (-14, 24), (14, 24)):
        a.dot(x, y + b, 'bolt1', 2)
    for sg in (-1, 1):
        a.e(sg * 18, 48 + b - fall * 9, 9, 7.2, 'steel')
        a.e(sg * 18, 53 + b - fall * 9, 3.8, 1.8, 'steel0', out=False) if False else None
        a.dot(sg * 18 - 1, 50 + b - fall * 9, 'bolt1', 2)
    hx = lerp(0, -9, fall)
    hy = lerp(59 + b, 13, fall)
    a.e(hx, hy, 12.4, 10.8, 'steel')
    a.e(hx - 4, hy + 5, 6, 3.4, 'steel', out=False)
    a.poly([(hx - 10, hy + 3), (hx + 10, hy + 3), (hx + 10, hy - 6), (hx - 10, hy - 6)], 'ink', out=False)
    state = T['state']
    for dx in (-4.4, 4.8):
        if state == 'dead':
            a.line((hx + dx - 2.4, hy - 1), (hx + dx + 2.4, hy - 5), 'glow1', 2)
            a.line((hx + dx - 2.4, hy - 5), (hx + dx + 2.4, hy - 1), 'glow1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy - 2), 3.4, 3.1 * a.sy)[0], 'glow0', outline=True)
            a.f.flat(ellipsoid(*a.g(hx + dx + .6, hy - 2.3), 1.8, 2 * a.sy)[0], 'iris')
            a.dot(hx + dx - 1.4, hy - .6, 'shine', 1)
    a.line((hx, hy + 11), (hx, hy + 18), 'bolt1', 2)
    fist = (lerp(lerp(30, 26, wind), 32, strike), lerp(lerp(26, 74, wind), 9, strike))
    if clip == 'die':
        fist = (lerp(30, 27, fall), lerp(26, 8, fall))
    a.c((19, 42 + b - fall * 8), fist, 7.4, 6.8, 'steel')
    a.e(fist[0], fist[1], 10.6, 9.6, 'steel')
    a.e(fist[0] - 3, fist[1] + 4, 5, 2.8, 'steel', out=False)
    a.line((fist[0] + 2, fist[1] - 3), (fist[0] + 3, fist[1] - 8), 'core1', 1) if fall < .6 else None
    if clip == 'attack' and n in (4, 5):
        for k in range(5):
            a.e(min(33 + k * 1.8, 36), 4 + (k * 7) % 9 + (n - 4) * 3, 2.4, 2.4, 'steam' if k % 2 else 'steel')
    if clip == 'die':
        for k in range(5):
            a.e(-22 + k * 11, 5 + (k % 2) * 2, 4.2 - k % 2, 3, 'steel' if k % 2 else 'rust')
    return a.done()


# ------------------------------------------------------------------------------------------------
def hollowking(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('hollowking', clip, n, sy=1 - fall * .5)
    b = bob * .5
    flow = math.sin(n * math.pi / 3) * 1.6 if clip == 'idle' else sw * 2
    a.band([(-9, 52 + b), (9, 52 + b), (17 + flow, 30), (22 + flow * 1.4, 6), (-22 + flow, 6), (-17, 30)], 'cape')
    a.band([(-21 + flow, 6), (-14, 12), (-8, 5), (-2, 11), (4, 5), (10, 11), (16, 5), (22 + flow, 6)], 'cape', out=False)
    for sg in (-1, 1):
        up = max(0, sg * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((sg * 7, 22), (sg * 7, 6 + up), 4.4, 3.8, 'armor')
        a.e(sg * 7.6, 4 + up, 7, 3.8, 'armor')
        a.line((sg * 7 - 3, 12 + up), (sg * 7 + 3, 12 + up), 'gold1', 1)
    a.band([(-11, 25), (11, 25), (13, 16), (-13, 16)], 'gold')
    a.e(0, 36 + b, 13.4, 11.4, 'armor')
    a.e(-4, 41 + b, 7, 4, 'armor', out=False)
    a.poly([(0, 43 + b), (4, 36 + b), (0, 29 + b), (-4, 36 + b)], 'flame1', edge='gold1')
    a.line((-13, 28 + b), (13, 28 + b), 'gold1', 2)
    # green-flamed sword
    hand = (lerp(lerp(18, 14, wind), 25, strike), lerp(lerp(34, 42, wind), 34, strike))
    ang = lerp(lerp(1.5, 2.0, wind), .2, strike)
    far = (-20, 36 + b)
    a.c((-11, 43 + b), far, 3.6, 3.2, 'armor')
    a.e(far[0], far[1], 3.4, 3.4, 'bone')
    if clip == 'die':
        hand = (lerp(18, 24, fall), lerp(34, 8, fall))
        ang = lerp(1.5, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 5, hand[1] - dy * 5)
    tip = (min(hand[0] + dx * 28, 28), min(hand[1] + dy * 28, 70))
    a.line(base, tip, 'ink', 6)
    a.line(base, tip, 'blade1', 4)
    a.line(base, tip, 'blade2', 1)
    a.line((hand[0] - dy * 6, hand[1] + dx * 6), (hand[0] + dy * 6, hand[1] - dx * 6), 'gold1', 3)
    a.c((10, 43 + b), hand, 3.8, 3.4, 'armor')
    a.e(hand[0], hand[1], 3.6, 3.4, 'bone')
    for sg in (-1, 1):
        a.e(sg * 15, 44 + b, 7.6, 6.4, 'armor')
        a.poly([(sg * 15 - 3, 47 + b), (sg * 15 + sg * 2, 56 + b), (sg * 15 + 4, 47 + b)], 'gold2')
    hx, hy = 1, 54 + b
    skull(a, hx, hy, 12.4, max(wind * .5, strike) * 3)
    socket(a, hx - 3.6, hy + 1.4, 4.1)
    socket(a, hx + 6.4, hy + 1.4, 3.8)
    # crown with green flames
    a.band([(hx - 12, hy + 8), (hx + 12, hy + 8), (hx + 12, hy + 13), (hx - 12, hy + 13)], 'gold')
    for k, (dx_, h) in enumerate(((-9, 5), (-3, 8), (3, 7), (9, 5))):
        a.poly([(hx + dx_ - 2.4, hy + 13), (hx + dx_, hy + 13 + h), (hx + dx_ + 2.4, hy + 13)], 'gold2')
        a.e(hx + dx_, hy + 15 + h + math.sin(n + k) * 1.2, 2.2, 2.8, 'flame')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(tip[0] + 5 + k * 4, 34), tip[1] - 3 + k * 4, 2.4, 'glow0')
    return a.done()


DRAW = dict(thrall=thrall, archer=archer, acolyte=acolyte, gatewarden=gatewarden, choir=choir, colossus=colossus,
            hollowking=hollowking)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def drawer(kind):
    return lambda clip, n: draw(kind, clip, n)


DRAWERS = {k: (drawer(k), PALETTES[k]) for k in KINDS}

if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/vault-cel-preview')
    print('ok')
