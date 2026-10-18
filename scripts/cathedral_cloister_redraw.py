"""Cel-shaded Flooded Cloister enemies for make_cathedral_sprites.py.

One fixed 96x96 foot anchor and five procedural clips per kind.  All shapes
are flat indexed colours so PixelFlow retains the editable source exactly.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from make_crag_sprites import Palette


KINDS = ('tidetemplar', 'tidecantor', 'tideleech', 'bellkeeper',
         'mournsister', 'rootabbot', 'choirmother')

# Distinct material ramps, chosen against the dark Cloister floor.
SCHEMES = {
    'tidetemplar': ('#125b67', '#198d94', '#3cd6ca', '#c3fff0', '#efad49', '#fff0ab', '#dce9db'),
    'tidecantor': ('#145b87', '#247eb0', '#55cbee', '#c1f6ff', '#e7a854', '#ffe3a5', '#e8f5ec'),
    'tideleech': ('#235a45', '#329466', '#70d788', '#c6fbaa', '#f6a361', '#ffe5ae', '#e1f6d7'),
    'bellkeeper': ('#225a61', '#318a8b', '#72d9c6', '#dcfff1', '#c66d42', '#ffe49b', '#e4efe6'),
    'mournsister': ('#315479', '#5c95bb', '#a2dcea', '#e9fbf7', '#bd7097', '#ffe0bd', '#f5f6ed'),
    'rootabbot': ('#334c38', '#52805a', '#89bf75', '#cfebb0', '#c18751', '#f5d68b', '#e6efd2'),
    'choirmother': ('#205971', '#287e91', '#55d1c4', '#beffed', '#d09c5d', '#fff0a7', '#f3f5dc'),
}


def palette(kind):
    dark, mid, light, shine, metal, gold, skin = SCHEMES[kind]
    return Palette(dict(dark=dark, mid=mid, light=light, shine=shine,
                        metal=metal, gold=gold, skin=skin,
                        face='#182841', eye='#fff9cb', iris='#10e6d2',
                        shade='#34415a', red='#fa698b', foam='#e1ffff'))


PALETTES = {kind: palette(kind) for kind in KINDS}


def draw(kind, clip, n):
    p = PALETTES[kind]
    im = Image.new('P', (96, 96), 0)
    d = ImageDraw.Draw(im)
    wave = math.sin(n * math.pi / 3)
    gait = wave * 4 if clip == 'walk' else 0
    lift = abs(wave) * 3 if clip == 'walk' else math.sin(n * math.pi / 3) if clip == 'idle' else 0
    strike = (0, -3, -5, 2, 7, 4, 1, 0)[n] if clip == 'attack' else 0
    recoil = (-4, -2, 2, 0)[n] if clip == 'hurt' else 0
    fall = (0, .04, .10, .25, .43, .60, .73, .82)[n] if clip == 'die' else 0
    lean = strike + recoil

    def xy(x, y):
        return (round(48 + .82 * (x + lean * y / 70)),
                round(88 - .88 * y * (1 - fall) - lift + fall * 2))

    def poly(points, fill, edge=True):
        pts = [xy(*v) for v in points]
        d.polygon(pts, fill=p[fill])
        if edge:
            d.line(pts + pts[:1], fill=p['ol'], width=2, joint='curve')

    def ell(x, y, rx, ry, fill, edge=True):
        a = xy(x-rx, y+ry); b = xy(x+rx, y-ry)
        box = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        d.ellipse(box, fill=p[fill], outline=p['ol'] if edge else None, width=2)

    def line(points, color, width=2, edge=False):
        pts = [xy(*v) for v in points]
        if edge:
            d.line(pts, fill=p['ol'], width=width+2, joint='curve')
        d.line(pts, fill=p[color], width=width, joint='curve')

    def face(x, y, spread=5, mouth=True):
        # Three-pixel eyes keep the expression at native game size.
        for side in (-1, 1):
            ell(x+side*spread, y+2, 2, 3, 'face', False)
            ell(x+side*spread+1, y+3, 1, 1, 'eye', False)
        if mouth:
            line([(x-3,y-5),(x+3,y-5)], 'face', 2)

    if kind == 'tidetemplar':
        # Broad shield and coral-plumed helm distinguish this soldier from every caster.
        for side in (-1, 1):
            ell(side*(10+gait*side), 7, 7, 5, 'dark')
            poly([(side*9,10),(side*(12+gait*side),10),(side*(11+gait*side),26),(side*6,27)], 'mid')
        poly([(-16,25),(14,25),(19,58),(8,65),(-13,61)], 'dark')
        poly([(-12,30),(12,30),(15,55),(-10,58)], 'mid', False)
        poly([(-11,42),(10,42),(12,52),(-8,55)], 'light')
        line([(-8,45),(8,45)], 'shine', 2)
        poly([(-14,58),(-19,41),(-12,32),(-5,49)], 'light')
        poly([(10,61),(24,54),(31,23),(25,19),(8,38)], 'dark')
        poly([(11,57),(24,51),(27,26),(14,36)], 'mid', False)
        line([(17,50),(26,31)], 'shine', 2)
        ell(1,67,13,11,'dark'); ell(3,66,9,7,'skin',False)
        face(4,67,4)
        poly([(-12,71),(-18,64),(-17,77),(-7,81),(6,80),(16,74),(8,69)], 'light')
        poly([(-7,79),(-4,85),(0,80),(4,85),(8,79)], 'metal')
        line([(-8,81),(8,81)], 'shine', 2)
        # The forked tide spear surges forward during attack.
        sx = 29 + (8 if clip == 'attack' and n in (3,4,5) else 0)
        line([(sx-3,9),(sx-5,73)], 'metal', 3, True)
        poly([(sx-11,71),(sx-7,81),(sx-4,76),(sx,85),(sx+3,76),(sx+7,81),(sx+10,71)], 'gold')

    elif kind == 'tidecantor':
        # Narrow blue songbird silhouette: wing sleeves, glass lyre, tall hood.
        for side in (-1,1):
            poly([(side*10,45),(side*(22+gait),40),(side*28,24),(side*13,33)], 'dark')
            poly([(side*12,43),(side*(21+gait),37),(side*24,29),(side*12,37)], 'light', False)
        poly([(-14,44),(14,44),(19,10),(5,4),(-17,10)], 'dark')
        poly([(-12,42),(11,42),(15,11),(-12,12)], 'mid', False)
        for x in (-7,0,7):
            line([(x,39),(x+2+wave,12)], 'light', 2)
        poly([(-14,64),(-8,78),(0,87),(10,77),(14,64),(7,69),(-7,69)], 'light')
        ell(0,62,10,10,'skin'); face(1,63,4)
        poly([(-12,63),(-11,73),(-2,69),(8,73),(13,63)], 'dark')
        line([(-12,73),(0,78),(13,73)], 'shine', 2)
        # Suspended lyre is much wider than the old orb staff.
        lx=27+(5 if clip=='attack' and n in (3,4,5) else 0)
        poly([(lx-8,54),(lx-11,68),(lx-5,77),(lx+4,77),(lx+11,68),(lx+8,54)], 'metal')
        poly([(lx-5,57),(lx-7,67),(lx-3,73),(lx+3,73),(lx+7,67),(lx+5,57)], 'face', False)
        for x in (-3,0,3): line([(lx+x,59),(lx+x,72)], 'shine',1)
        ell(lx,78,4,4,'foam')

    elif kind == 'tideleech':
        # Upright lamprey, coiling upward into a large toothed suction mouth.
        bend=wave*3 + strike*.6
        poly([(-26,6),(-23,20),(-15,31),(-10,49),(1,57),(10,49),(13,31),(27,22),(30,11),
              (19,14),(8,24),(1,33),(-6,24),(-13,10)], 'dark')
        poly([(-23,8),(-18,22),(-11,29),(-6,47),(3,51),(9,42),(10,31),(23,19),(25,13),
              (15,18),(4,28),(-1,36),(-8,21),(-12,8)], 'mid',False)
        for k in range(5):
            x=-20+k*5
            line([(x,10+k*3),(x+4,12+k*3)], 'light',2)
        for k in range(4):
            line([(12+k*4,24-k*2),(15+k*4,19-k*2)],'light',2)
        ell(bend,56,18,18,'dark')
        ell(bend,59,14,13,'light',False)
        ell(bend+3,58,11,10,'face')
        ell(bend+4,57,7,7,'red',False)
        ell(bend+4,56,4,4,'face',False)
        for a in range(0,360,45):
            t=math.radians(a)
            x=bend+3+9*math.cos(t); y=58+8*math.sin(t)
            ell(x,y,2,3,'eye',False)
        for x in (-11,8): ell(x+bend,76,3,3,'eye')
        for x in (-17,14):
            poly([(x,68),(x-5,64),(x-4,72)],'metal')

    elif kind == 'bellkeeper':
        # Bell-shaped iron torso, a suspended cathedral bell and a heavy mallet.
        for side in (-1,1):
            ell(side*(11+gait*side),7,8,6,'dark')
            poly([(side*8,10),(side*(14+gait*side),11),(side*15,31),(side*6,32)],'mid')
        poly([(-15,30),(14,30),(20,55),(12,70),(-11,70),(-21,54)],'dark')
        poly([(-12,32),(11,32),(16,56),(10,65),(-9,65),(-16,54)],'mid',False)
        poly([(-16,49),(16,49),(18,56),(10,61),(-11,61),(-18,55)],'metal')
        line([(-12,55),(12,55)],'gold',3)
        ell(0,43,7,8,'gold'); ell(0,43,4,4,'face',False)
        poly([(-18,67),(-12,76),(-2,82),(10,79),(17,70),(10,65),(-12,65)],'light')
        ell(0,67,12,10,'face');face(2,68,5)
        poly([(-9,77),(-5,84),(1,88),(7,82),(11,76)],'metal')
        # Huge left bell, animated by a pendulum swing.
        bx=-29+(wave*2 if clip in ('walk','idle') else strike)
        line([(bx,48),(bx,72)],'gold',3,True)
        poly([(bx-8,46),(bx+8,46),(bx+14,31),(bx-14,31)],'metal')
        line([(bx-11,36),(bx+11,36)],'gold',3)
        ell(bx,27,5,3,'gold')
        mx=31+(8 if clip=='attack' and n in (3,4) else 0)
        line([(mx-5,20),(mx+1,68)],'metal',4,True)
        ell(mx+1,68,10,6,'gold')

    elif kind == 'mournsister':
        # Pale veil, exposed expressive face, dark mourning dress and tear lantern.
        for side in (-1,1):
            poly([(side*8,45),(side*(19+gait),42),(side*27,16),(side*12,25)],'mid')
            line([(side*12,37),(side*23,19)],'shine',2)
        poly([(-11,50),(11,50),(20,5),(4,8),(-18,6)],'dark')
        poly([(-7,43),(9,43),(13,12),(-12,11)],'mid',False)
        for x in (-9,-2,6): line([(x,38),(x+2,13)],'light',2)
        ell(0,65,11,13,'skin');face(1,66,4,False)
        for x in (-3,5):line([(x,62),(x,55)],'iris',1)
        poly([(-13,68),(-16,80),(-6,87),(7,87),(17,77),(14,66),(8,73),(-8,73)],'shine')
        poly([(-14,69),(-5,78),(8,77),(14,69),(9,81),(-4,82)],'light',False)
        line([(-13,79),(13,79)],'foam',2)
        lx=25+(6 if clip=='attack' and n in (3,4,5) else 0)
        line([(15,45),(lx,57)],'skin',4,True)
        line([(lx,56),(lx,38)],'metal',2)
        poly([(lx-7,38),(lx+7,38),(lx+10,27),(lx-10,27)],'metal')
        ell(lx,33,6,7,'iris',False);ell(lx-2,36,2,3,'foam',False)

    elif kind == 'rootabbot':
        # Kelpwood colossus: roots, wide branch arms and a glowing heart knot.
        for side in (-1,1):
            poly([(side*6,27),(side*16,25),(side*24,5),(side*8,7)],'dark')
            poly([(side*10,27),(side*16,22),(side*20,8),(side*12,9)],'mid',False)
            poly([(side*8,51),(side*23,57),(side*35,31),(side*29,25),(side*17,42)],'dark')
            poly([(side*12,49),(side*23,52),(side*30,30),(side*27,31),(side*18,44)],'light',False)
            for k in range(3):
                line([(side*(28+k*2),31),(side*(33+k*2),24-k*4)],'metal',2)
        poly([(-19,24),(18,24),(19,59),(10,69),(-12,68),(-21,53)],'dark')
        poly([(-15,29),(14,29),(15,57),(6,63),(-12,60)],'mid',False)
        for x in (-12,-5,3,10): line([(x,55),(x+3,28)],'light',2)
        ell(0,48,9,11,'metal');ell(1,50,5,7,'iris',False)
        ell(0,67,15,13,'dark');ell(1,67,11,8,'mid',False)
        face(2,69,5,False)
        poly([(-15,72),(-25,80),(-20,86),(-8,80),(-3,88),(3,80),(14,85),(23,78),(14,70)],'light')
        line([(-19,82),(-26,87)],'metal',3)

    elif kind == 'choirmother':
        # Royal bell gown, radiant halo and two distinct floating choir masks.
        for side in (-1,1):
            mx=side*(27+wave*2); my=56+wave*2
            poly([(side*9,60),(side*21,64),(mx,49),(side*13,44)],'light')
            ell(mx,my,9,11,'dark')
            ell(mx,my+1,6,8,'skin',False)
            ell(mx+side*3,my+2,2,2,'eye',False)
            line([(mx-3,my-5),(mx+3,my-5)],'red',2)
            line([(side*12,44),(mx,my-2)],'gold',2)
        poly([(-13,48),(13,48),(23,5),(9,9),(0,4),(-10,9),(-22,6)],'dark')
        poly([(-10,44),(11,44),(18,10),(8,12),(0,8),(-8,13),(-17,10)],'mid',False)
        for x in (-10,0,10): line([(x,42),(x+wave*2,12)],'shine',2)
        poly([(-14,50),(14,50),(17,67),(9,71),(-10,70)],'light')
        ell(0,68,10,10,'skin');face(2,69,4)
        poly([(-13,72),(-18,80),(-8,88),(0,84),(9,88),(18,79),(13,72),(7,78),(-7,78)],'gold')
        ell(0,83,4,4,'iris',False)
        # A broken concentric halo has clear pixels between its segments.
        for k in range(12):
            a=math.pi*k/6
            x=math.cos(a)*17; y=67+math.sin(a)*18
            if abs(x)<12 and y<70: continue
            ell(x,y,2,3,'shine',False)

    if clip == 'attack' and n in (3,4,5):
        for k in range(3):
            ell(34+k*3,36+k*8,2,2,'foam',False)
    if clip == 'hurt' and n == 0 or clip == 'die' and n == 0:
        a=np.array(im)
        a[a>0]=p['flash']
        return a
    return np.array(im)
