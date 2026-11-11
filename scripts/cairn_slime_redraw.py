#!/usr/bin/env python3
"""Cairnspine: seven original, editable PixelFlow enemy remakes.
preview | extents | build | refresh KIND... | export | verify
Shared NPC art and the separately authored Avalanche Bear are preserved.
"""
import json, math, os, sys, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
import lapis_slime_redraw as L
from astral_slime_redraw import Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BONE, PEARL, AZURE, FUR, SLATE, GOLD, TEAL, VIOLET, CRIMSON, GREEN, BROWN
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
OUT=ROOT/'test-results/cairn-slime'
REGISTRY=ROOT/'scripts/cairn_slime_sources.txt'
MANIFEST=ASSETS/'cairn.txt'
PREFIX='valhallasc_cairn_slime_'
KINDS=['screeferret','stoneibex','slateraven','ridgeadder','cairnbehemoth','whitebarktitan','stormcondor']
NAMES=dict(zip(KINDS,['Scree Ferret','Stone Ibex','Slate Raven','Ridge Adder','Cairn Behemoth','Whitebark Titan','Storm Condor']))
VILLAGERS=['cairn_warden','cairn_surveyor','cairn_stonesinger','cairn_grovekeeper','cairn_windseer','cairn_travel']
# Zone-specific ramps retain the original russet / slate / white-bark identities.
PALETTE=PALETTE[:]
for _name,_colors in {
    'SLATE':['#18212d','#384351','#657180','#99a8b5','#d3dce2'],
    'FUR':['#564537','#927b5e','#baa484','#dfd0ac','#fff3d5'],
    'BROWN':['#332820','#644532','#956443','#c18b5b','#edd1a0'],
    'BONE':['#494138','#837660','#c0ac8c','#ead7b6','#fff8de'],
    'PEARL':['#4c5051','#8b9090','#c7c9bf','#e7e8db','#fffef0'],
    'TEAL':['#292b18','#55562a','#8e934a','#bbc078','#ece4b1'],
    'AZURE':['#111e33','#273e5b','#42658a','#7795b9','#becfe5'],
    'GOLD':['#493414','#88631e','#c39230','#efc55b','#fff0a8'],
}.items():
    globals()[_name]=list(range(len(PALETTE),len(PALETTE)+len(_colors)))
    PALETTE.extend(_colors)
assert len(PALETTE)<=256 and len(set(PALETTE))==len(PALETTE)
W=H=96
AX,AY=48,90
KIND_FRAMES={k:(176,172,88,164) for k in KINDS}
SCALE=dict(screeferret=.85,stoneibex=.80,slateraven=.75,ridgeadder=.95,cairnbehemoth=.90,whitebarktitan=.70,stormcondor=.70)
CLIPS={'idle':(10,6),'walk':(10,8),'attack':(10,8),'hurt':(10,4),'die':(10,8)}
FLYING=('slateraven','stormcondor')
STRICT=True
BAD=[]
LOWEST={}
def kind_frame(kind): return kindframe.check_frame(*KIND_FRAMES[kind])
class Painter(BasePainter):
    """Leave raw space below the origin for tipped poses, before grounding."""
    def __init__(self,kind):
        self.w,self.h,self.ax,self.ay=kind_frame(kind)
        self.S=SCALE[kind]
        self.im=Image.new('P',(self.w,self.h),0)
        self.d=ImageDraw.Draw(self.im)
        self.cx=self.ax
        self.ay=115
    def pos(self,x,y):return round(self.cx+x*self.S),round(self.ay-y*self.S)
    def ellipse(self,x,y,rx,ry,col):super().ellipse(x,y,rx*self.S,ry*self.S,col)
    def line(self,pts,col,width=1):super().line(pts,col,max(1,round(width*self.S)))
    def ball(self,x,y,rx,ry,ramp,ang=0.):super().ball(x,y,rx*self.S,ry*self.S,ramp,ang)

def beats(clip,n):
    wind=(.10,.58,1.,.38,0,0,0,0)[n] if clip=='attack' else 0
    strike=(0,0,0,.68,1.,.58,.20,.025)[n] if clip=='attack' else 0
    death=(0,.08,.22,.40,.60,.78,.92,1.)[n] if clip=='die' else 0
    phase=n*math.pi/4+.31
    bob=(1-math.cos(n*math.pi/3+.3))*.55 if clip=='idle' else 0
    return wind,strike,death,phase,bob

def setup(kind,clip,n,pivot,angle):
    a=Painter(kind);w,s,d,ph,b=beats(clip,n)
    r=L.Rig(a,*pivot,angle*d+((-.10,-.04,.035,.01)[n] if clip=='hurt' else 0))
    return a,r,w,s,d,ph,b

def closed(r,x,y,size=3):r.line([(x-size,y),(x+size,y-1)],OUTLINE,2)

def screeferret(clip,n):
    a,r,w,s,d,ph,b=setup('screeferret',clip,n,(0,16),-.14)
    cy=19+b-4*w-8*d
    r.taper([(-23,cy),(-34,cy+5-5*d),(-44,cy+9-10*d+math.sin(ph)*(1-d)*2)],BROWN,7,1)
    for i,x in enumerate((-18,-8,11,20)):
        step=math.sin(ph+i*2.1)*4 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*2.1))*4 if clip=='walk' else 0
        r.limb([(x,cy),(x+3+6*d,10+up),(x+4+step+10*s-8*d,3+up+5*d)],BROWN,4)
        r.ball(x+6+step+10*s-8*d,2+up+5*d,5,2.3,FUR)
        for j in range(2):r.line([(x+8+step+j*2+10*s-8*d,2+up+5*d),(x+10+step+j*2+10*s-8*d,1+up+5*d)],BONE[-2],1)
    r.ball(-3,cy,24,11,BROWN)
    r.ball(0,cy-4,18,5,FUR)
    for x,h in [(-18,6),(-9,8),(0,6)]:
        r.ball(x,cy+10,5,h,SLATE,-.4)
        r.line([(x-2,cy+12),(x+1,cy+15)],SLATE[-1],1)
    hx,hy=24+14*s-6*w,cy+6
    r.limb([(16,cy),(hx-5,hy)],BROWN,12)
    for x in (hx-6,hx+3):
        r.poly([(x-4,hy+5),(x-3,hy+16),(x+4,hy+10)],BROWN[2],OUTLINE)
        r.poly([(x-2,hy+9),(x-2,hy+13),(x+1,hy+10)],FUR[2])
    r.ball(hx,hy,12,10,BROWN)
    r.ball(hx+9,hy-3,10,4.5,FUR)
    r.poly([(hx-9,hy+6),(hx+8,hy+4),(hx+8,hy-1),(hx-7,hy+1)],SLATE[0])
    ex,ey=hx+3,hy+3
    if d>.3:closed(r,ex,ey)
    else:
        r.ball(ex,ey,3.3,2.4,GOLD);r.ellipse(ex+1,ey,1,1.8,OUTLINE);r.ellipse(ex,ey+1,1,1,WHITE)
        r.line([(ex-5,ey+4),(ex+3,ey+1)],OUTLINE,2)
    r.ball(hx+17,hy-2,2,2,SLATE)
    # Upper muzzle and lower jaw share a hinge; the open bite is a filled cavity.
    gap=2+6*s+2*w
    r.poly([(hx+2,hy-5),(hx+17,hy-5),(hx+13,hy-5-gap),(hx+1,hy-6-gap)],OUTLINE)
    r.limb([(hx+1,hy-5),(hx+12,hy-6-gap)],FUR,3)
    for xx in (hx+7,hx+13):r.poly([(xx-1,hy-5),(xx+2,hy-5),(xx,hy-9)],BONE[-1])
    return a

def stoneibex(clip,n):
    a,r,w,s,d,ph,b=setup('stoneibex',clip,n,(0,24),-.62)
    cy=27+b+5*w-10*d
    for i,x in enumerate((-17,-8,11,19)):
        swing=math.sin(ph+i*1.8)*5 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.8))*5 if clip=='walk' else 0
        r.limb([(x,cy),(x+3+9*d,14+up),(x+4+swing+8*s-9*d,4+up+8*d)],BROWN,4)
        r.ball(x+5+swing+8*s-9*d,3+up+8*d,4,3,SLATE)
    r.ball(-3,cy+2,24,14,FUR)
    r.ball(-8,cy+9,18,7,BROWN)
    r.taper([(-25,cy+5),(-31,cy+13),(-32,cy+16)],FUR,5,1)
    # Head and curved horns move as a connected neck rig in the headbutt.
    hx,hy=22+17*s-6*w,cy+15+5*w-12*s
    r.limb([(12,cy+5),(hx-3,hy-5),(hx,hy)],FUR,12)
    for dx in (-6,4):
        pts=[(hx+dx,hy+9),(hx+dx-4,hy+23),(hx+dx-14,hy+31),(hx+dx-22,hy+28),(hx+dx-23,hy+22)]
        r.taper(pts,BONE,7,2)
        for i in range(1,4):
            px,py=pts[i];r.line([(px-2,py-2),(px+2,py+1)],BROWN[1],1)
    r.ball(hx,hy,12,13,FUR,.14)
    r.ball(hx+7,hy-7,8,7,BROWN)
    r.poly([(hx-6,hy-8),(hx-5,hy-20),(hx+2,hy-16),(hx+3,hy-8)],FUR[1],OUTLINE)
    r.limb([(hx-9,hy+3),(hx-20,hy+8)],FUR,4)
    if d>.3:closed(r,hx+3,hy+4)
    else:
        r.ball(hx+3,hy+4,4,3,GOLD)
        r.line([(hx,hy+4),(hx+6,hy+4)],OUTLINE,2)
        r.ellipse(hx+1,hy+6,1,1,WHITE)
        r.line([(hx-2,hy+9),(hx+7,hy+6)],BROWN[0],3)
    r.line([(hx+9,hy-7),(hx+14,hy-7)],OUTLINE,2)
    return a

def slateraven(clip,n):
    a,r,w,s,d,ph,b=setup('slateraven',clip,n,(0,36),-.82)
    cy=50+b+8*w-5*s-27*d
    flap=math.sin(ph)*5 if clip in ('walk','idle') else 12*w-9*s
    # Compact feather fans sweep behind the narrow head, unlike the condor's frontal span.
    for side in (-1,1):
        root=(-7,cy+7)
        tip=(-30-side*7-12*w+14*d,cy+11+flap+side*8-18*d)
        r.poly([root,(-17,cy+26+flap),(tip[0]-8,tip[1]),(-24,cy-3)],SLATE[0],OUTLINE)
        for j in range(4):
            r.ball(tip[0]+j*4,tip[1]-j*4,4,12-j,SLATE,-.65+d*.6)
    r.taper([(-10,cy-9),(-24,cy-14),(-31-6*d,cy-16)],SLATE,10,2)
    for x in (-5,6):
        r.limb([(x,cy-10),(x+4,cy-19),(x+11*s+6*d,cy-23)],GOLD,2)
        for j in range(3):r.line([(x+11*s+6*d,cy-23),(x+11*s+6*d+j*3-3,cy-27)],GOLD[2],1)
    r.ball(0,cy,15,18,SLATE,-.25)
    r.ball(4,cy+3,8,10,SLATE)
    r.line([(-8,cy+7),(-3,cy+1),(3,cy-2)],AZURE[2],2)
    r.line([(-7,cy+9),(-1,cy+4),(4,cy+2)],AZURE[3],1)
    hx,hy=12+17*s-7*w,cy+17+3*w-10*s
    r.limb([(4,cy+7),(hx-3,hy-4)],SLATE,12)
    r.ball(hx,hy,11,10,SLATE,-.2)
    r.poly([(hx-8,hy+7),(hx-3,hy+16),(hx+4,hy+9)],SLATE[1],OUTLINE)
    r.poly([(hx+7,hy+2),(hx+23,hy-1),(hx+17,hy-7-3*s),(hx+8,hy-4)],SLATE[3],OUTLINE)
    if d>.35:closed(r,hx+5,hy+5)
    else:
        r.poly([(hx-1,hy+7),(hx+8,hy+5),(hx+7,hy+1),(hx+1,hy+2)],GOLD[2],OUTLINE)
        r.ellipse(hx+5,hy+4,1,2,OUTLINE);r.ellipse(hx+3,hy+5,1,1,WHITE)
    r.line([(hx+10,hy-3),(hx+19,hy-3-2*s)],OUTLINE,1)
    return a

def ridgeadder(clip,n):
    a,r,w,s,d,ph,b=setup('ridgeadder',clip,n,(0,14),-.10)
    # Coils release by moving their joints along the floor; the snake never rotates upright.
    sway=math.sin(ph)*2*(1-d)
    pts=[(-30-9*d,6),(-20-5*d,14-6*d),(-3,9),(20+10*d,8),(27+9*d,18-10*d),(9,23-15*d),(-12,20-9*d),(-18,10)]
    r.taper(pts,TEAL,9,5)
    r.taper([(-27,7),(-37,5),(-41,7+sway)],TEAL,5,1)
    for i,(x,y) in enumerate(pts[1:-1]):
        r.poly([(x-3,y+2),(x,y+5),(x+4,y+1),(x+6,y+3)],BROWN[1])
        r.line([(x-3,y+2),(x,y+5),(x+4,y+1)],GOLD[1],1)
    hx,hy=14+21*s-8*w,36+b+8*w-25*d
    r.taper([(-15,12),(-14-5*w,28-18*d),(hx-8,hy-5),(hx,hy)],TEAL,9,11)
    r.ball(hx,hy,14,10,TEAL)
    r.poly([(hx-10,hy+7),(hx+3,hy+14),(hx+13,hy+5)],TEAL[2],OUTLINE)
    gap=2+11*s+4*w
    r.poly([(hx-3,hy-3),(hx+14,hy-3),(hx+11,hy-7-gap),(hx-5,hy-5-gap)],OUTLINE)
    r.limb([(hx-5,hy-3),(hx+2,hy-8-gap),(hx+12,hy-6-gap)],PEARL,4)
    for x in (hx+3,hx+10):r.fang(x,hy-3,5+5*s,3,.05,BONE)
    if d>.45:closed(r,hx+5,hy+5)
    else:
        r.ball(hx+5,hy+5,4,3,GOLD);r.line([(hx+6,hy+3),(hx+6,hy+8)],OUTLINE,2);r.ellipse(hx+4,hy+6,1,1,WHITE)
    if clip in ('idle','attack') and n in (1,2,4):
        r.line([(hx+14,hy-5),(hx+22,hy-5-gap/2),(hx+25,hy-3-gap/2)],CRIMSON[3],1)
        r.line([(hx+22,hy-5-gap/2),(hx+25,hy-7-gap/2)],CRIMSON[3],1)
    return a

def cairnbehemoth(clip,n):
    a,r,w,s,d,ph,b=setup('cairnbehemoth',clip,n,(0,26),-.17)
    cy=35+b+6*w-17*d
    for side in (-1,1):
        swing=math.sin(ph+(0 if side<0 else math.pi))*4 if clip=='walk' else 0
        r.ball(side*(14+8*d),10+swing*.4+8*d,9,10,SLATE)
        r.ball(side*(15+11*d)+swing,4+5*d,12,5,SLATE)
    r.ball(0,cy,25,22,SLATE)
    r.poly([(-18,cy+9),(-7,cy+18),(14,cy+15),(20,cy-2),(5,cy-13),(-17,cy-6)],SLATE[2],OUTLINE)
    r.poly([(-17,cy+8),(-6,cy+16),(10,cy+13),(0,cy+4)],SLATE[3])
    r.line([(-10,cy+13),(-5,cy+4),(-10,cy-3),(1,cy-9)],SLATE[0],2)
    for side in (-1,1):
        sh=(side*23,cy+8)
        hand=(side*(31+10*s+9*d),20+30*w-13*s-9*d)
        r.limb([sh,(side*(32+6*d),cy-2+15*w-12*s),hand],SLATE,10)
        r.ball(*sh,12,12,SLATE)
        r.ball(*hand,13,11,SLATE,.15*side)
        for j in range(3):r.line([(hand[0]-7+j*6,hand[1]+2),(hand[0]-7+j*6,hand[1]-5)],SLATE[0],1)
    hx,hy=1+8*s-4*w,cy+22-6*d
    r.ball(hx,hy,16,14,SLATE)
    r.poly([(hx-15,hy+5),(hx-8,hy+18),(hx+8,hy+17),(hx+16,hy+5)],SLATE[2],OUTLINE)
    for side in (-1,1):
        x=hx+side*7
        r.poly([(x-5,hy+3),(x+5,hy+3),(x+4,hy-2),(x-4,hy-2)],SLATE[0])
        if d<.7:r.line([(x-3,hy+1),(x+2,hy+1)],GOLD[3] if d<.3 else GOLD[1],2)
        r.line([(x-5,hy+7),(x+5,hy+5*side)],SLATE[1],4)
    r.poly([(hx-8,hy-7),(hx+9,hy-7),(hx+6,hy-11),(hx-5,hy-10)],OUTLINE)
    for x,y in [(-23,cy+17),(23,cy+17),(-8,cy-7)]:
        r.ball(x,y,5,2,GREEN)
    if clip=='die':
        # Solid slabs separate and settle at different rates, without rubber scaling.
        for i in range(3):r.ball(-29+i*27+d*(i-1)*8,4+4*(1-d)+i%2,5+d*2,4,SLATE,.2*i)
    return a

def whitebarktitan(clip,n):
    a,r,w,s,d,ph,b=setup('whitebarktitan',clip,n,(0,20),-1.05)
    cy=39+b+3*w-8*d
    for side in (-1,1):
        step=math.sin(ph+(0 if side<0 else math.pi))*4 if clip=='walk' else 0
        r.limb([(side*9,cy-13),(side*(11+8*d),15+4*d),(side*(13+10*d)+step,4+7*d)],BROWN,7)
        for j in range(3):r.taper([(side*(13+10*d)+step,5+7*d),(side*(17+j*3+10*d)+step,2+7*d)],BROWN,4,1)
    r.ball(0,cy,18,26,PEARL,.05)
    r.poly([(-11,cy+19),(-3,cy+26),(9,cy+20),(9,cy-20),(-6,cy-24),(-12,cy-9)],PEARL[2],OUTLINE)
    # Torn bark exposes dark grain; asymmetric branches keep the titan narrow.
    for x,y in [(-8,cy+18),(5,cy+8),(-6,cy-3),(7,cy-16)]:
        r.line([(x-3,y),(x+3,y-1)],SLATE[0],2)
        r.line([(x-2,y-3),(x+1,y-3)],SLATE[1],1)
    r.poly([(-4,cy+2),(2,cy+8),(6,cy),(2,cy-14),(-3,cy-18),(-7,cy-8)],BROWN[1],BROWN[0])
    r.line([(-2,cy+2),(1,cy-4),(-2,cy-12)],BROWN[0],1)
    for side in (-1,1):
        hx=side*25+20*s-7*w
        hy=cy+2+18*w-13*s+(4 if side<0 else -4)
        r.limb([(side*12,cy+14),(side*21,cy+4+13*w),(hx,hy)],PEARL,6)
        for j in range(3):
            r.taper([(hx,hy),(hx+side*(9+j*3)+8*s,hy+8-j*6),(hx+side*(12+j*3)+8*s,hy+5-j*7)],BROWN,4,1)
    hx,hy=2+6*s-3*w,cy+26
    r.ball(hx,hy,15,15,PEARL)
    # Slanted torn sockets sit under heavy bark brows. No round owl face.
    for side in (-1,1):
        x=hx+side*6
        r.poly([(x-side*5,hy+3),(x+side*6,hy+9),(x+side*5,hy+1),(x-side*3,hy-1)],BROWN[0],SLATE[0])
        if d<.5:
            r.line([(x-side,hy+3),(x+side*2,hy+4)],GREEN[-2],1)
        r.limb([(x-side*5,hy+6),(x+side*6,hy+11)],PEARL,4)
    r.line([(hx-8,hy-7),(hx-4,hy-9),(hx,hy-7),(hx+4,hy-9),(hx+8,hy-6)],BROWN[0],2)
    for side,h in [(-1,22),(1,14)]:
        x=hx+side*7
        r.taper([(x,hy+11),(x+side*7,hy+21),(x+side*12,hy+11+h)],PEARL,5,1)
        r.taper([(x+side*7,hy+21),(x+side*17,hy+23)],BROWN,3,1)
        for j in range(3):r.ball(x+side*(11+j*3),hy+14+h-j*3,4,2,GREEN,.4*side)
    return a

def stormcondor(clip,n):
    a,r,w,s,d,ph,b=setup('stormcondor',clip,n,(0,39),.64)
    cy=59+b+9*w-9*s-36*d
    flap=math.sin(ph)*4 if clip in ('idle','walk') else 18*w-11*s
    spread=1-.62*d
    for side in (-1,1):
        root=(side*9,cy+8)
        r.poly([root,(side*(25*spread),cy+21+flap),(side*(38*spread),cy+16+flap),(side*(31*spread),cy-5),(side*10,cy-8)],AZURE[1],OUTLINE)
        for j in range(5):
            x=side*(22+j*4)*spread;y=cy+6+flap*(.5+j*.1)-j*3
            r.ball(x,y,4,13-j*.5,AZURE,side*(.15+.18*j)-side*d*.4)
            r.line([(x-side,y+5),(x+side,y-7)],SLATE[3],1)
    r.taper([(-2,cy-10),(0,cy-25),(6,cy-29)],AZURE,10,3)
    r.ball(0,cy,14,17,AZURE)
    for x in (-7,8):
        r.limb([(x,cy-10),(x+9*s,cy-19),(x+14*s+7*d,cy-24)],GOLD,3)
        for j in range(3):r.fang(x+14*s+7*d+j*3-3,cy-24,5,1.7,.4,BONE)
    hx,hy=6+12*s-5*w,cy+24+3*w-4*s
    r.limb([(1,cy+9),(hx-3,hy-7),(hx,hy)],CRIMSON,9)
    for j in range(7):
        ang=j*math.pi/6;r.ball(2+math.cos(ang)*12,cy+12+math.sin(ang)*6,5,5,PEARL)
    r.ball(hx,hy,11,12,CRIMSON)
    r.poly([(hx-9,hy+8),(hx-5,hy+17),(hx+2,hy+15),(hx+1,hy+8)],AZURE[0],OUTLINE)
    # Large shaded hooked beak with a curved lower tip, separate from the raven's narrow bill.
    r.ball(hx+11,hy-1,9,5,GOLD,-.2)
    r.poly([(hx+13,hy+1),(hx+21,hy-4),(hx+17,hy-11),(hx+15,hy-5)],GOLD[2],OUTLINE)
    r.line([(hx+10,hy-4),(hx+17,hy-5-3*s)],OUTLINE,1)
    if d>.35:closed(r,hx+4,hy+5)
    else:
        r.ball(hx+4,hy+5,3.6,3,AZURE);r.ellipse(hx+5,hy+5,1,2,OUTLINE);r.ellipse(hx+3,hy+6,1,1,WHITE)
        r.line([(hx-2,hy+10),(hx+8,hy+7)],AZURE[0],3)
    return a
DRAW={k:globals()[k] for k in KINDS}
def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    clipped = bool(grid.any() and (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()))   # BEFORE the roll hides it
    if grid.any():
        LOWEST[kind] = max(LOWEST.get(kind, -999), int(np.nonzero(grid.any(axis=1))[0].max()) - kay)
    if kind in FLYING:
        grid = np.roll(grid, kay - 115, axis=0)
        # Flyers hover well above the ground while alive and settle onto kay at the end of death.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and clip == 'die' and (n == 7 or int(rows.max()) > kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    else:
        # Grounded kinds rest their lowest pixel exactly on the anchor row in every living and death frame.
        while grid.any() and int((grid[int(np.nonzero(grid.any(axis=1))[0].max())] != 0).sum()) <= 2:
            grid[int(np.nonzero(grid.any(axis=1))[0].max())] = 0          # a 1-2 pixel sliver below the feet is a rasteriser stray
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and (clip == 'die' or int(rows.max()) != kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    problem = 'drawn past the canvas edge before the ground roll (clipped)' if clipped else None
    low = int(np.nonzero(grid.any(axis=1))[0].max()) if grid.any() else -1
    if not grid.any() or grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any():
        problem = 'empty or touches the border'
    elif kind in FLYING:
        if clip != 'die' and low > kay - 12:
            problem = f'flying kind should hover well above anchor row {kay} (lowest row {low})'
        elif clip == 'die' and low > kay:
            problem = f'flying death frame {n} sinks below anchor row {kay} (lowest row {low})'
    elif low != kay:
        problem = f'lowest row {low} != anchor row {kay}'
    if problem:
        BAD.append((kind, clip, n, problem))
        assert not STRICT, (kind, clip, n, problem)
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def api_draw(sid, offset, data):
    for clip, grids in data.items():
        for n, grid in enumerate(grids):
            old.api('draw', dict(sprite_id=sid, frame=offset + n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
        offset += len(grids)
    return offset


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = registry()
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX + kind + '_all' + os.environ.get('SOURCE_SUFFIX', '')  # a frame-size change needs a NEW source
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/cairn_slime_{kind}_raw.npz', **data[kind])
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(
            name=name, width=kw, height=kh, frames=34, layers=1, fps=10,
            palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]
        ))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, api_draw(sid, 0, data[kind]), 'frames saved', flush=True)


def refresh():
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/cairn_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'cairn_{kind}.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    live = json.loads(MANIFEST.read_text())
    assert all(k in live['kinds'] for k in VILLAGERS), 'villager entries missing'
    villagers = {k: (live['sprites'][k], live['tops'][k]) for k in VILLAGERS}
    meta = json.loads(json.dumps(live))
    proof, atlases = {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip] == dict(fps=fps, n=count, row=row, editorStart=offset), clip
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['sprites'][kind] = saved[kind]
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for k in VILLAGERS:   # the villager NPCs must come out exactly as they went in
        assert (meta['sprites'][k], meta['tops'][k]) == villagers[k] and k not in (meta.get('kindFrames') or {})
    for kind, atlas in atlases.items():
        dest = atlas_path(kind)
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 238 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    saved = registry()
    for kind in KINDS:
        meta = json.loads(MANIFEST.read_text())
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(atlas_path(kind)).convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)



def preview():
    OUT.mkdir(parents=True,exist_ok=True)
    poses=[('idle',0),('attack',2),('attack',4),('die',3),('die',7)]
    sheet=Image.new('RGBA',(len(poses)*176,len(KINDS)*200),'#243346')
    pen=ImageDraw.Draw(sheet)
    for y,k in enumerate(KINDS):
        for x,(clip,n) in enumerate(poses):sheet.alpha_composite(rgba(frame(k,clip,n)),(x*176,y*200))
        pen.text((4,y*200+180),NAMES[k],fill='white')
    sheet.save(OUT/'poses.png')
    print(OUT/'poses.png')
def extents():
    for kind in KINDS:
        data=frames(kind)
        boxes={c:[Image.fromarray(f).getbbox() for f in rows] for c,rows in data.items()}
        print(kind, 'idle',boxes['idle'][0], 'raw lowest vs anchor',LOWEST[kind],flush=True)
    assert not BAD, BAD

if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    {'preview':preview,'extents':extents,'build':build,'refresh':refresh,'export':export,'verify':verify}[cmd]()
