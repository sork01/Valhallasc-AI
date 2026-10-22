"""Five original cloth constructions fitted to every existing cel rig and pose.

The shoulder seam is body-local. Lower rows have delayed cloth sway and drag;
all panels use interpolated camera depth, including the dying body's rotation.
"""
import math
import numpy as np
import cel_common as cc
import gear_shapes as rigs

STYLES = ('travel', 'hooded', 'mantle', 'clasp', 'ember')
PALETTE, COLOR = cc.palette_of({
    'cloth': ['#18263b', '#304c6f', '#587faa', '#a0c9dd'],
    'lining': ['#30203b', '#59405f', '#927193', '#c9a8bd'],
    'trim': ['#513b28', '#98713d', '#d4aa60', '#ffe1a1'],
})

def surface(ink, vertices, material, tone=2, bias=0, outline=True):
    projected = [ink.project(v) for v in vertices]
    xy = np.array([v[0] for v in projected]); depths = np.array([v[1] for v in projected])
    slope = np.linalg.lstsq(np.c_[np.ones(len(xy)), xy], depths, rcond=None)[0]
    g = slope[1:]; norm = float(np.linalg.norm(g))
    if norm < 1e-6:
        ink.poly(xy, COLOR[material][tone], float(depths.mean()) + bias, outline)
        return
    axis = g / norm; along = xy @ axis; centre = xy.mean(0)
    a = centre + axis * (along.min() - centre @ axis)
    b = centre + axis * (along.max() - centre @ axis)
    za = slope[0] + a @ g; zb = slope[0] + b @ g
    ink.poly(xy, COLOR[material][tone], bias, outline, (a, b, za, zb))

def render(cls, gender, style, clip, facing, k):
    module, _, p, R, xf, joints, head = rigs.pose(cls, gender, clip, facing, k)
    ink = cc.Ink(cc.rig.psi_for(facing), COLOR)
    n = module.CLIPS[clip][1]; phase = 2 * math.pi * k / n
    length = {'travel': 31, 'hooded': 41, 'mantle': 48, 'clasp': 43, 'ember': 47}[style]
    width = {'travel': 15, 'hooded': 18, 'mantle': 22, 'clasp': 20, 'ember': 23}[style]
    moving = clip == 'walk'; dying = clip == 'die'
    gain = 3.6 if moving else 2.2 if clip == 'attack' else .65
    # At rest the hem stays below the shoulders; walk drag is always behind the wearer.
    def point(u, v, front=False):
        lag = math.sin(phase - v * 1.8)
        sway = gain * lag * v * v
        back = -6.2 - v * (7 + (5 if moving else 0)) - math.sin(u * math.pi * 3) * (1.1 + v)
        if front: back = 6.4
        z = 68 - length * v + math.cos(phase * 2 - v) * v * (.9 if moving else .3)
        if style == 'ember': z -= (2 if int((u + 1) * 4) % 2 else -2) * v ** 6
        if style == 'clasp': z += abs(u) * v ** 4 * 5
        if style == 'travel': z += abs(u) * v ** 3 * 3
        q = xf((u * (9.5 + (width - 9.5) * v) + sway, back, z))
        # A fallen cloak rests on the ground with its wearer, rather than crossing it.
        if dying: q[2] = max(1.5, q[2])
        return q
    us = np.linspace(-1, 1, 9); vs = np.linspace(0, 1, 7)
    for row in range(len(vs)-1):
        for col in range(len(us)-1):
            u0,u1=us[col:col+2];v0,v1=vs[row:row+2]
            # Fold bands, with a contrasting sewn hem and outer binding.
            mat = 'trim' if (row == 5 or col in (0,7)) and style in ('mantle','clasp','ember') else 'cloth'
            tone = (1,2,2,3,2,1,2,2)[col]
            surface(ink,[point(u0,v0),point(u1,v0),point(u1,v1),point(u0,v1)],mat,tone,outline=False)
    # Narrow shoulder yokes wrap around the sides. They leave hands and chest open.
    for side in (-1,1):
        surface(ink,[xf((side*4,-6.8,69.3)),xf((side*10.7,-5.2,69)),
            xf((side*11.6,3.8,65)),xf((side*6.6,6.4,64)),xf((side*5.1,4.8,68))], 'cloth',2,bias=-.4)
    # A single clasp at the throat is visible from the front, without covering the face.
    surface(ink,[xf((-2.2,6.7,67)),xf((0,7,69)),xf((2.2,6.7,67)),xf((0,7,65))],'trim',3,bias=-.5)
    if style == 'hooded':
        # A folded hood on the nape; does not replace the wearer's hair or headgear.
        surface(ink,[xf((-6.8,-7,74)),xf((0,-10,77)),xf((6.8,-7,74)),
                     xf((4.8,-10,65)),xf((0,-13,62)),xf((-4.8,-10,65))],'lining',2,bias=-.3)
    if style == 'ember':
        for u in (-.75,-.25,.25,.75):
            surface(ink,[point(u-.045,.5),point(u+.045,.5),point(u+.06,.94),point(u,.86),point(u-.06,.94)],'lining',3,bias=-.12,outline=False)
    return ink.resolve(flash=clip == 'hurt' and k == 0)
