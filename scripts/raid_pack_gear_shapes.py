"""Original class-neutral Cinderwork pieces: articulated kiln gaiters,
an open crucible pendant and a square clamp ring. No stock gear drawers.
"""
import math
import numpy as np
import cel_common as cc
import gear_shapes as rig
from cel_common import V, unit

MATS={
    'cinder_iron':['#202833','#3d4b58','#718897','#bfd2d9'],
    'cinder_ember':['#6a2926','#b8482c','#f39145','#ffe19a'],
    'cinder_basalt':['#22202c','#433b50','#77617e','#b29ab3'],
    'cinder_cloth':['#272b38','#414958','#697683','#adb9c2'],
}
PALETTE,COLOR=cc.palette_of({**rig.MATS,**MATS})
I,E,B,S='cinder_iron','cinder_ember','cinder_basalt','cinder_cloth'

def render(cls,theme,kind,gender,clip,facing,k):
    _,ink,p,Q,xf,j,h=rig.pose(cls,gender,clip,facing,k);ink.color=COLOR
    u,a=Q@V(0,0,1),Q@V(1,0,0)
    if kind=='pants':
        for side,key in [(-1,'L'),(1,'R')]:
            hip,knee,ankle=j[key]['hip'],j[key]['knee'],j[key]['ankle']
            v=unit(ankle-knee)
            ink.bone(hip,knee,4.9,4.4,S,-.9);ink.bone(knee,ankle,4.5,3.8,S,-.9)
            # Three overlapping offset diamond louvres, with real negative gaps.
            for n in range(3):
                c=knee+v*(n*5-2)+Q@V(0,3,0)
                ink.plate([c-a*5-v*3,c+a*4-v*5,c+a*7+v*2,c-a*3+v*6],I,2)
                ink.plate([c-a*3-v,c+a*3-v*3,c+a*4+v,c-a*2+v*3],E,2)
            ink.bone(ankle+Q@V(0,-2,-1),ankle+Q@V(0,7,-2),4.8,3.4,B,-1.3)
    elif kind=='necklace':
        ink.ribbon([xf(q) for q in [(-6,4,71),(-5,8,64),(0,10,58),(5,8,64),(6,4,71)]],1.2,1.2,I,3,-2)
        c=xf((0,11,55))
        # Crucible arms surround a freely hanging ember; the centre stays open.
        for side in [-1,1]:
            ink.plate([c+a*side*2-u*5,c+a*side*7-u,c+a*side*6+u*7,
                c+a*side*3+u*6,c+a*side*4,c+a*side-u*3],I,2)
        ink.plate([c-u*3,c-a*2,c+u*4,c+a*2],E,3)
    elif kind=='accessory':
        c=j['L']['hand']+Q@V(0,4,1)
        # Square clamp, open in the middle, with an off-centre basalt tooth.
        for v0,v1 in [((-4,-3),(4,-3)),((4,-3),(4,4)),((4,4),(-4,4)),((-4,4),(-4,-3))]:
            ink.bone(c+a*v0[0]+u*v0[1],c+a*v1[0]+u*v1[1],1.2,1.2,I,-2)
        ink.plate([c-a*2+u*3,c-a*3+u*7,c+a*2+u*8,c+a*4+u*4],B,2)
        ink.bone(c+u*4,c+a+u*6,.9,.9,E,-3,3)
    else:raise ValueError(kind)
    return ink.resolve(clip in ('hurt','die') and k==0)
