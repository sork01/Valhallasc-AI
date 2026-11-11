#!/usr/bin/env python3
"""Yearwheel: sixteen original, editable PixelFlow enemy remakes (spring, summer, autumn, winter).
preview [KIND...] | extents [KIND...] | build | refresh KIND... | export | verify
The eight season NPCs (year_*_keeper / year_*_travel) and the separately authored Equinox Stag are preserved.
"""
import json, math, os, sys, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
import lapis_slime_redraw as L
from astral_slime_redraw import (Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BONE, PEARL, AZURE, FUR, SLATE, GOLD, TEAL, VIOLET, CRIMSON, GREEN, BROWN,
                                 PINK, CORAL, AMBER, PURPLE, mix, mixp, sm, bez)
from moonspore_slime_redraw import slit
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
OUT=ROOT/'test-results/yearwheel-slime'
REGISTRY=ROOT/'scripts/yearwheel_slime_sources.txt'
MANIFEST=ASSETS/'yearwheel.txt'
PREFIX='valhallasc_yearwheel_slime_'
KINDS=['brooknewt','bloomtortoise','petalchimera','rainseraph','sundarter','glasslion','sunwheel','firephoenix','acornmimic','lanternowl','harvestreaper','ambermantis','snowstoat','rimesaber','snowgiant','longnightwyrm']
NAMES=dict(zip(KINDS,['Brook Newt','Bloom Tortoise','Petal Chimera','Rain Seraph','Sun Dart','Glass Lion','Sunwheel','Fire Phoenix','Acorn Mimic','Lantern Owl','Harvest Reaper','Amber Mantis','Snow Stoat','Rime Saber','Snow Giant','Longnight Wyrm']))
VILLAGERS=[f'year_{s}_{r}' for s in ('sp','su','au','wi') for r in ('keeper','travel')]
# Extra ramps for this zone (base ramps come from the shared palette).
PALETTE=PALETTE[:]
for _name,_colors in {
    'ORANGE':['#4e1a0e','#a2401a','#e8742a','#ffb046','#ffe6a0'],
    'TAUPE':['#2a211d','#584538','#8a7258','#bba484','#eadcc0'],
    'MOSS':['#22300f','#4a6a1e','#82a63c','#bfdc6c','#effab0'],
}.items():
    globals()[_name]=list(range(len(PALETTE),len(PALETTE)+len(_colors)))
    PALETTE.extend(_colors)
assert len(PALETTE)<=256 and len(set(PALETTE))==len(PALETTE)
W=H=96
AX,AY=48,90
# Wide kinds get 192x160 (30,720 px), tall ones 176x172 (30,272 px): both under PixelFlow's per-frame cap.
WIDE=('brooknewt','bloomtortoise','petalchimera','sundarter','glasslion','rimesaber','snowstoat','longnightwyrm','ambermantis')
KIND_FRAMES={k:((192,160,96,152) if k in WIDE else (176,172,88,164)) for k in KINDS}
# Idle size of the OLD art (width, height at 96 px frames): the new idle should land close to it.
OLD_IDLE=dict(brooknewt=(76,28),sundarter=(75,42),acornmimic=(57,62),snowstoat=(76,34),bloomtortoise=(75,48),petalchimera=(80,54),rainseraph=(58,63),glasslion=(69,43),sunwheel=(57,67),firephoenix=(62,69),lanternowl=(51,63),harvestreaper=(60,57),ambermantis=(47,69),rimesaber=(70,51),snowgiant=(65,59),longnightwyrm=(71,51))
SCALE=dict(brooknewt=.72,bloomtortoise=.78,petalchimera=.80,rainseraph=.9,sundarter=.66,glasslion=.64,sunwheel=.9,firephoenix=.85,acornmimic=1.0,lanternowl=1.0,harvestreaper=.95,ambermantis=.72,snowstoat=.68,rimesaber=.72,snowgiant=.72,longnightwyrm=.68)
CLIPS={'idle':(10,6),'walk':(10,8),'attack':(10,8),'hurt':(10,4),'die':(10,8)}
FLYING=('rainseraph','sunwheel','firephoenix','lanternowl')
STRICT=not os.environ.get('YW_LAX')
BAD=[]
LOWEST={}
def kind_frame(kind): return kindframe.check_frame(*KIND_FRAMES[kind])
def origin(kind): return kind_frame(kind)[1]-57         # raw drawing origin row: 57 px of room below it for tipped poses
class Painter(BasePainter):
    """Leave raw space below the origin for tipped poses, before grounding."""
    def __init__(self,kind):
        self.w,self.h,self.ax,self.ay=kind_frame(kind)
        self.S=SCALE[kind]
        self.im=Image.new('P',(self.w,self.h),0)
        self.d=ImageDraw.Draw(self.im)
        self.cx=self.ax
        self.ay=origin(kind)
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

#KINDS-BEGIN
BAYER=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])
def fade(a,f):
    """Ordered-dither dissolve of everything drawn so far; f=1 leaves nothing."""
    arr=np.array(a.im);h,w=arr.shape
    ys,xs=np.mgrid[0:h,0:w]
    arr[(BAYER[ys%4,xs%4]/16.0)<f]=0
    a.im=Image.fromarray(arr);a.d=ImageDraw.Draw(a.im)
def drop(r,x,y,sz,col=None):
    r.poly([(x,y+sz*1.7),(x-sz*.85,y),(x,y-sz),(x+sz*.85,y)],col or AZURE[3],OUTLINE)

def eye(r,x,y,shape,col,size=3.6):
    """Per-creature eye shapes, drawn at a rig-transformed point (col is a ramp)."""
    X,Y=r.t(x,y);a=r.a
    if shape=='goat':       # amber eye with a horizontal bar pupil
        a.ellipse(X,Y,size+1.5,size*.8+1.4,OUTLINE);a.ellipse(X,Y,size,size*.8,col[3])
        a.poly([(X-size*.8,Y+1),(X+size*.8,Y+1),(X+size*.8,Y-1),(X-size*.8,Y-1)],OUTLINE);a.ellipse(X-size*.4,Y+size*.4,.9,.8,WHITE)
    elif shape=='crystal':  # faceted diamond
        a.poly([(X-size-1.2,Y),(X,Y+size*.95+1.2),(X+size+1.2,Y),(X,Y-size*.95-1.2)],OUTLINE)
        a.poly([(X-size,Y),(X,Y+size*.9),(X+size,Y),(X,Y-size*.9)],col[2])
        a.poly([(X-size*.5,Y),(X,Y+size*.55),(X+size*.3,Y)],col[4])
    elif shape=='hollow':   # pale empty glow under a heavy slanted brow
        a.ellipse(X,Y,size+1.5,size*.7+1.4,OUTLINE);a.ellipse(X,Y,size,size*.7,col[4])
        a.line([(X-size-1,Y+size*.7+2.5),(X+size+1,Y-size*.15)],OUTLINE,2)
    elif shape=='bead':     # reptile eye: round, vertical pupil, brow ridge
        a.ellipse(X,Y,size+1.4,size+1.4,OUTLINE);a.ellipse(X,Y,size,size,col[3])
        a.line([(X,Y-size*.9),(X,Y+size*.9)],OUTLINE,1);a.line([(X-size-1,Y+size+1.5),(X+size,Y+size-.5)],col[0],2)
    elif shape=='round':    # big owl/bird eye with a heavy brow
        a.ellipse(X,Y,size+1.5,size+1.5,OUTLINE);a.ellipse(X,Y,size,size,col[3])
        a.ellipse(X,Y,size*.45,size*.45,OUTLINE);a.ellipse(X-size*.3,Y+size*.3,.9,.9,WHITE)
        a.line([(X-size-1.5,Y+size+1),(X+size+1.5,Y+size-1.5)],OUTLINE,2)
    elif shape=='tri':      # jack-o-lantern triangle
        a.poly([(X-size-1.2,Y-size*.7-1),(X+size+1.2,Y-size*.7-1),(X,Y+size+1.4)],OUTLINE)
        a.poly([(X-size,Y-size*.7),(X+size,Y-size*.7),(X,Y+size)],col[3])
    elif shape=='orb':      # blank glowing orb
        a.ellipse(X,Y,size+1.4,size+1.4,OUTLINE);a.ellipse(X,Y,size,size,col[4]);a.ellipse(X,Y,size*.55,size*.55,col[2])
    elif shape=='dot':      # coal dot
        a.ellipse(X,Y,size,size,OUTLINE);a.ellipse(X-.7,Y+.7,.8,.8,WHITE)
    elif shape=='star':     # four-point star glint
        a.poly([(X-size-1,Y),(X,Y+size*.8),(X+size+1,Y),(X,Y-size*.8)],OUTLINE)
        a.line([(X-size,Y),(X+size,Y)],col[4],1);a.line([(X,Y-size*.7),(X,Y+size*.7)],col[3],1)

def brooknewt(clip,n):
    a,r,w,s,d,ph,b=setup('brooknewt',clip,n,(0,10),-.07)
    cy=21+b-9*d-3*w
    sway=math.sin(ph)*(1-d)
    tl=[(-20,cy-1),(-32,cy-3+sway*3-4*d),(-45,cy-6-sway*4-9*d),(-58,cy-5+sway*3-12*d)]
    r.taper(tl,GREEN,10,2)
    for i in range(3):   # fin crest along the tail
        (x0,y0),(x1,y1)=tl[i],tl[i+1]
        r.poly([(x0,y0+5),((x0+x1)/2-1,y0+15-3*i),(x1,y1+4)],AZURE[2],OUTLINE)
    for i,x in enumerate((-16,-7,10,19)):
        sw=math.sin(ph+i*1.7)*5 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.7))*4 if clip=='walk' else 0
        fx=x+6+sw+(9*s if i>=2 else 0)+11*d*(1 if i>=2 else -1)
        fy=2+up+2*d
        r.limb([(x,cy-5),(x+6+5*d,cy-11+3*d),(fx,fy+3)],GREEN,5.5)
        r.ball(fx+2,fy+1,6.5,2.8,GREEN)
        for j in range(3):r.line([(fx+4+j*2,fy+1),(fx+7+j*2,fy)],GREEN[0],1)
    r.ball(-2,cy,25,11.5,GREEN)
    r.ball(1,cy-5,19,5,ORANGE)
    r.ball(-2,cy+6,19,4.2,TEAL,-.05)
    for x in (-13,-3,8):r.ellipse(x,cy+6,2.3,1.7,AZURE[3])
    for x in (-14,-6,2,10):r.poly([(x-3,cy+10),(x+1,cy+18),(x+4,cy+10)],AZURE[2],OUTLINE)
    hx,hy=26+12*s-15*w,cy+1-6*d+3*w
    r.limb([(16,cy),(hx-6,hy)],GREEN,13)
    for k in range(3):   # feathery red gills sweeping back
        gy=hy+3+k*4-2*d
        r.line([(hx-8,gy),(hx-17-2*math.sin(ph+k),gy+7-k*2)],CRIMSON[3],2)
        r.ball(hx-18-2*math.sin(ph+k),gy+7-k*2,2.2,2.2,ORANGE)
    gap=1.5+8*s+4*w+5*d
    r.poly([(hx+1,hy-4),(hx+19,hy-4),(hx+20,hy-6-gap),(hx,hy-6-gap*.5)],CRIMSON[0])
    r.poly([(hx-2,hy-5-gap*.5),(hx+20,hy-6-gap),(hx+19,hy-10-gap),(hx-1,hy-10-gap*.5)],ORANGE[2],OUTLINE)
    for x in (hx+8,hx+13,hx+18):r.fang(x,hy-6-gap,3+3*s,2.2,1.57,BONE)
    r.ball(hx,hy,13,8.5,GREEN)
    r.ball(hx+10,hy-1,9,5.2,GREEN)
    for x in (hx+8,hx+15):r.fang(x,hy-4,3+3*s,2.2,-1.57,BONE)
    r.ellipse(hx+17,hy+1,1.2,1,OUTLINE)
    if d>.3:
        r.line([(hx-1,hy+6),(hx+7,hy+4)],OUTLINE,2)
        if d>.55:r.line([(hx+18,hy-6-gap),(hx+24,hy-10-gap)],CRIMSON[3],2)
    else:slit(r.a,*r.t(hx+4,hy+5),4.2,2.9,AMBER,GREEN[3])
    return a

def bloomtortoise(clip,n):
    a,r,w,s,d,ph,b=setup('bloomtortoise',clip,n,(0,14),-.10)
    cy=24+b-3*w-9*d+6*s
    shell_x=-3*w+7*s
    for i,x in enumerate((-22,-10,13,25)):
        sw=math.sin(ph+i*1.9)*4 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.9))*3 if clip=='walk' else 0
        fx=x+sw+5*s*(i>=2)+(12*d if i>=2 else -12*d)
        r.limb([(x+shell_x,cy-8),(x+shell_x+2+4*d,9+up),(fx,3+up)],GREEN,10)
        r.ball(fx+2,2+up,7,3.3,GREEN)
        for j in range(3):r.line([(fx+4+j*2,3+up),(fx+6+j*2,1+up)],BONE[3],1)
    r.ball(-2+shell_x,cy+6,34,23,BROWN,-.05)          # the rigid shell
    r.line([(-30+shell_x,cy-1),(32+shell_x,cy-1)],BROWN[0],2)
    for i,(x,y) in enumerate(((-18,12),(-4,16),(12,13),(-26,2),(22,3),(-8,2),(6,3))):
        r.poly([(x-7+shell_x,cy+y),(x+shell_x,cy+y+6),(x+7+shell_x,cy+y),(x+6+shell_x,cy+y-6),(x-6+shell_x,cy+y-6)],BROWN[2] if i%2 else BROWN[1])
        r.line([(x-6+shell_x,cy+y-6),(x+shell_x,cy+y+6)],BROWN[0],1)
    if d>.35:   # the shell cracks
        r.line([(-16+shell_x,cy+25),(-9+shell_x,cy+14),(-14+shell_x,cy+8),(-5+shell_x,cy-1)],OUTLINE,2)
        r.line([(10+shell_x,cy+22),(5+shell_x,cy+11),(11+shell_x,cy+4)],OUTLINE,2)
    wilt=min(1,d*1.6)
    for k,(x,y,rr) in enumerate(((-16,28,7),(-3,32,8),(11,28,7),(-26,19,5.5),(20,20,5.5))):
        fy=cy+y-14*wilt*(k%2+1)*.6; fx=x+shell_x-5*wilt*(k-2)*.4
        for j in range(5):
            ang=j*1.2566+.4+k
            r.ball(fx+math.cos(ang)*rr*.85,fy+math.sin(ang)*rr*.85,rr*.55,rr*.55,PINK if wilt<.5 else CORAL)
        r.ball(fx,fy,rr*.42,rr*.42,GOLD)
    hx,hy=36+16*s-17*w,cy-1-3*s-7*d
    hs=1-.5*w
    r.limb([(24+shell_x,cy-2),(hx-8,hy)],GREEN,12*hs+2)
    r.ball(hx,hy,12*hs+3,9*hs+2,GREEN)
    r.ball(hx+9*hs,hy-3,9*hs+1,5*hs+1,GREEN)
    gap=1+6*s
    r.poly([(hx+2,hy-5),(hx+18*hs+2,hy-5),(hx+17*hs+2,hy-7-gap),(hx+1,hy-7-gap*.5)],OUTLINE)
    r.line([(hx+2,hy-5),(hx+18*hs+2,hy-5)],BONE[2],2)
    for x in (hx+9,hx+15):r.fang(x,hy-4,3,2,-1.57,BONE)
    r.poly([(hx-5,hy+6),(hx+7,hy+9),(hx+9,hy+4)],BROWN[1],OUTLINE)   # heavy brow
    if d>.3:r.line([(hx+1,hy+3),(hx+8,hy+2)],OUTLINE,2)
    else:slit(r.a,*r.t(hx+4,hy+3),3.4,2.4,GOLD,BROWN[1])
    return a

def petalchimera(clip,n):
    a,r,w,s,d,ph,b=setup('petalchimera',clip,n,(8,18),-.22)
    cy=27+b-6*w-12*d
    for i,x in enumerate((-22,-12,12,22)):
        sw=math.sin(ph+i*1.9)*5 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.9))*5 if clip=='walk' else 0
        reach=14*s if i>=2 else -3*w
        fx=x+4+sw+reach+(6*d if i>=2 else -6*d)
        r.limb([(x,cy-2),(x+3+5*d,14-2*d+up),(fx,4+up+4*d)],PINK,7)
        r.ball(fx+2,3+up+4*d,6.5,3.2,PINK)
        for j in range(3):r.fang(fx+3+j*2,2+up+4*d,3+3*s,1.6,-.2,BONE)
    tl=[(-26,cy+3),(-40,cy+8+math.sin(ph)*(1-d)*3),(-48,cy+20-10*d),(-42,cy+33-20*d)]  # the snake tail
    r.taper(tl,GREEN,8,5)
    tx,ty=tl[-1]
    r.ball(tx+1,ty+1,6,4.6,GREEN)
    r.poly([(tx+5,ty-1),(tx+13+8*s,ty-2),(tx+5,ty+2)],CRIMSON[2],OUTLINE)
    if d<.4:slit(r.a,*r.t(tx+1,ty+3),1.9,1.2,AMBER,GREEN[1])
    r.ball(-4,cy,29,13,PINK)
    r.ball(0,cy-6,22,5,PINK[::-1][:5] if False else FUR)
    for x in (-18,-6,6):r.ball(x,cy+9,7,5.5,CORAL)                   # petal ridge along the back
    hx,hy=26+15*s-8*w,cy+7-4*d
    for k in range(9):    # petal mane behind the face
        ang=.55+k*.62+math.sin(ph+k)*.04*(1-d)
        mx,my=hx-4+math.cos(ang)*17,hy+math.sin(ang)*17
        r.ball(mx,my,8,5.5,CORAL if k%2 else PINK,ang)
    r.ball(hx,hy,15,14,PINK)
    r.ball(hx+9,hy-4,8,6,FUR)
    r.ball(hx+15,hy-1,3.2,2.6,CRIMSON)
    gap=1+9*s+3*w
    r.poly([(hx+4,hy-7),(hx+20,hy-7),(hx+17,hy-9-gap),(hx+3,hy-9-gap*.6)],CRIMSON[0])
    r.poly([(hx+3,hy-8-gap*.6),(hx+18,hy-9-gap),(hx+14,hy-13-gap),(hx+3,hy-12-gap*.6)],PINK[2],OUTLINE)
    for x in (hx+8,hx+14):r.fang(x,hy-7,5,3,-1.57,BONE)
    for k,x in enumerate((hx-3,hx+5)):r.taper([(x,hy+11),(x-5,hy+21+2*k),(x-14,hy+22+2*k)],GOLD,6,1)   # curled goat horns
    if d>.35:
        r.line([(hx+1,hy+3),(hx+9,hy+4)],OUTLINE,2)
    else:
        eye(r,hx+5,hy+4,'goat',GOLD,4.6)
    if clip in('die','idle') and n in(3,4,5,6):   # petals drift loose
        for k in range(4):r.ball(-10+k*14+n*2,cy-4-(k*7+n*5)%27*(d>0),3,1.8,PINK)
    return a

def rainseraph(clip,n):
    a,r,w,s,d,ph,b=setup('rainseraph',clip,n,(0,50),0)
    hov=49+b*1.4+4*w-3*s
    flap=math.sin(ph)*(1-d)*.07-.35*w+.3*s
    for back in (1,0):    # two wings of long feathers
        for i in range(6):
            ang=(1.9-i*.2+flap*(1 if back else .7))+(.3 if back else 0)
            L=35-i*2.6
            ox=-7-3*back
            r.taper([(ox,hov+14),(ox+math.cos(ang)*L,hov+14+math.sin(ang)*L*.8-(3 if back else 0))],AZURE if back else FUR,6-i*.5,1.2)
    r.ball(0,hov+3,13.5,18,AZURE)                                      # robe
    r.poly([(-8,hov-9),(8,hov-9),(2,hov-30),(-3,hov-24)],AZURE[1],OUTLINE)
    r.line([(-6,hov+10),(-4,hov-6),(-1,hov-18)],AZURE[4],1)
    r.poly([(-9,hov+14),(9,hov+14),(8,hov+10),(-8,hov+10)],PEARL[1],OUTLINE)
    hx,hy=2+3*s,hov+27
    for k in range(4):                                               # sharp rain-drop hair
        r.poly([(hx-7+k*3,hy+8),(hx-12+k*4.5-2*math.sin(ph+k)*(1-d),hy+22+k%2*3),(hx-3+k*3,hy+9)],AZURE[2],OUTLINE)
    r.ball(hx-7,hy+3,11,12,AZURE)                                    # long swept hair
    for k in range(3):r.taper([(hx-9,hy+6-k*4),(hx-17-k*2,hy-2-k*5),(hx-20-k*2,hy-14-k*6)],AZURE,5,1)
    r.ball(hx+1,hy-1,11,11.5,FUR)
    r.poly([(hx+3,hy-9),(hx+13,hy-3),(hx+4,hy-14)],FUR[2],OUTLINE)       # sharp chin
    r.poly([(hx-9,hy+9),(hx+11,hy+10),(hx+8,hy+3),(hx+2,hy+7),(hx-2,hy+2)],AZURE[2],OUTLINE)   # jagged fringe
    halo=[(hx+math.cos(k*.5236)*12,hy+17+math.sin(k*.5236)*3.6) for k in range(13)]
    r.line(halo,GOLD[3],2)
    if d>.3 or (clip=='hurt' and n==0):
        r.line([(hx-3,hy+1),(hx+7,hy+3)],OUTLINE,2)
    else:
        eye(r,hx+7,hy,'orb',AZURE,3.4);eye(r,hx-1,hy+1,'orb',AZURE,2.5)
        r.line([(hx-5,hy+6),(hx+11,hy+2.5)],AZURE[0],2)               # stern brow
        r.line([(hx+4,hy-7),(hx+11,hy-6)],AZURE[0],1)
        r.fang(hx+8,hy-6,3,2,-1.57,BONE)
    hand=(12+13*s-6*w,hov+14+8*w-5*s)
    r.limb([(5,hov+16),(9+4*s,hov+14+4*w),hand],AZURE,5)
    r.ball(hand[0]+1,hand[1],3.2,3.2,FUR)
    ox,oy=hand[0]+5,hand[1]+3
    if d<.5:
        r.ball(ox,oy,5+3*w,5+3*w,AZURE,0)
        r.ball(ox-1,oy+1,2,2,FUR)
    if s>.15:
        for k in range(7):
            dx=ox+4+k*5.5*s+(k%2)*3
            dy=oy-2-k*3.5*s-(k%3)*2.5
            drop(r,dx,dy,2+.5*(k%3))
    if clip=='die':
        fade(a,min(1,d*1.08)) if n<7 else fade(a,1)
        pl=max(0,d-.45)*2
        for k in range(8):
            fx=-24+k*7+(k%3)*3
            drop(r,fx,max(5,hov+10-(d*70+k*9))*(1 if n<7 else 0)+5,1.8+.4*(k%2)) if n<7 else None
        if d>.55:r.ball(0,5,6+16*pl,3,AZURE)
    return a
def sundarter(clip,n):
    a,r,w,s,d,ph,b=setup('sundarter',clip,n,(0,14),-.10)
    cy=27+b-12*d-4*w
    sway=math.sin(ph)*(1-d)
    tl=[(-20,cy-2),(-34,cy-3+sway*3-6*d),(-50,cy-8-sway*4-12*d),(-66,cy-12+sway*3-14*d)]
    r.taper(tl,AMBER,8,1.5)
    for i,x in enumerate((-15,-6,12,20)):
        sw=math.sin(ph+i*1.9)*6 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.9))*5 if clip=='walk' else 0
        fx=x+4+sw+(10*s if i>=2 else -3*w)+9*d*(1 if i>=2 else -1)
        r.limb([(x,cy-4),(x-3+7*(i>=2)-3*d,cy-13+3*d),(fx,3+up+3*d)],AMBER,5)
        r.ball(fx+2,2+up+3*d,5.5,2.5,AMBER)
        for j in range(3):r.line([(fx+4+j*1.5,2+up+3*d),(fx+6+j*1.5,1+up+3*d)],BONE[3],1)
    r.ball(-2,cy,26,10.5,AMBER)
    r.ball(1,cy-5,20,4.8,GOLD)
    sail=1-.55*d
    pts=[(-17,cy+8),(-18,cy+22*sail),(-13,cy+14),(-9,cy+30*sail),(-4,cy+16),(1,cy+33*sail),(6,cy+16),(11,cy+27*sail),(14,cy+11)]
    r.poly(pts,CRIMSON[2] if d<.5 else CRIMSON[1],OUTLINE)
    r.poly([(-14,cy+10),(-9,cy+26*sail),(-5,cy+12),(1,cy+28*sail),(6,cy+12),(10,cy+22*sail),(11,cy+10)],ORANGE[2] if d<.5 else ORANGE[1])
    for x in (-9,1,11):r.line([(x-1,cy+10),(x+(1 if x>0 else -1),cy+26*sail)],GOLD[3],1)
    hx,hy=27+14*s-9*w,cy+9-3*w-9*d
    r.limb([(15,cy+2),(hx-6,hy-2)],AMBER,11)
    r.ball(hx,hy,10.5,8,AMBER)
    gap=1.5+8*s+4*w+4*d
    r.poly([(hx,hy-3),(hx+20,hy-3),(hx+21,hy-5-gap),(hx-1,hy-5-gap*.5)],CRIMSON[0])
    r.poly([(hx-2,hy-4-gap*.5),(hx+21,hy-5-gap),(hx+19,hy-8-gap),(hx-1,hy-8-gap*.5)],GOLD[2],OUTLINE)
    r.poly([(hx+5,hy+6),(hx+22,hy-1),(hx+20,hy-4),(hx+6,hy-5)],AMBER[2],OUTLINE)       # wedge snout
    for x in (hx+10,hx+16):r.fang(x,hy-4,3+3*s,2,-1.57,BONE)
    for k in range(3):r.poly([(hx-6-k*3,hy+4),(hx-14-k*4,hy+7+k*2),(hx-7-k*3,hy-1)],CRIMSON[2],OUTLINE)
    if d>.3:r.line([(hx+1,hy+5),(hx+9,hy+3)],OUTLINE,2)
    else:eye(r,hx+6,hy+4,'bead',GOLD,3.2)
    return a

def glasslion(clip,n):
    a,r,w,s,d,ph,b=setup('glasslion',clip,n,(6,18),-.20)
    cy=27+b-5*w-13*d
    for i,x in enumerate((-23,-12,11,22)):
        sw=math.sin(ph+i*1.9)*5 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.9))*5 if clip=='walk' else 0
        reach=(16*s+4*w*(-1)) if i>=2 else -3*w
        up2=(10*s if i==3 else 0)
        fx=x+4+sw+reach+(7*d if i>=2 else -7*d)
        r.limb([(x,cy-3),(x+3+5*d,15-2*d+up),(fx,4+up+up2+4*d)],AMBER,7)
        r.ball(fx+2,3+up+up2+4*d,6.2,3,AMBER)
        for j in range(3):r.fang(fx+3+j*2,2+up+up2+4*d,3+2*s,1.5,-.2,BONE)
    tl=[(-26,cy+3),(-38,cy+2+math.sin(ph)*(1-d)*3),(-48,cy+8-6*d)]
    r.taper(tl,AMBER,6,4)
    for k in range(3):                                                  # crystal tuft
        tx,ty=tl[-1];r.poly([(tx-2,ty),(tx+3+k*3,ty+8+k*4-5*d),(tx+4,ty-1)],TEAL[3],OUTLINE)
    r.ball(-4,cy,28,11.5,AMBER)
    r.ball(0,cy-6,21,4.6,GOLD)
    hx,hy=26+16*s-9*w,cy+8-4*d
    shards=[(2.9,20,9),(2.45,24,10),(2.0,26,11),(1.55,27,11),(1.1,25,10.5),(.65,22,9.5),(.2,19,8.5),(3.3,17,8)]
    for k,(ang,L,wd) in enumerate(shards):
        loose=d*(k%3+1)*3
        bx,by=hx-3+math.cos(ang)*8,hy+math.sin(ang)*8
        tx,ty=hx-3+math.cos(ang)*(8+L)+loose*(k%2*2-1),hy+math.sin(ang)*(8+L)-loose*2
        nx,ny=-math.sin(ang)*wd/2,math.cos(ang)*wd/2
        r.poly([(bx+nx,by+ny),(tx,ty),(bx-nx,by-ny)],TEAL[2] if k%2 else AZURE[2],OUTLINE)
        r.poly([(bx+nx*.35,by+ny*.35),(bx+(tx-bx)*.78+nx*.1,by+(ty-by)*.78+ny*.1),(bx-nx*.1,by-ny*.1)],AZURE[4])
    r.ball(hx,hy,12,11.5,AMBER)
    r.ball(hx+13,hy-4,12,5.6,GOLD)
    r.ball(hx+23,hy-2,3.2,2.6,CRIMSON)
    gap=1+10*s+3*w
    r.poly([(hx+4,hy-7),(hx+20,hy-7),(hx+17,hy-9-gap),(hx+3,hy-9-gap*.6)],CRIMSON[0])
    r.poly([(hx+3,hy-8-gap*.6),(hx+18,hy-9-gap),(hx+14,hy-13-gap),(hx+3,hy-12-gap*.6)],AMBER[2],OUTLINE)
    for x in (hx+8,hx+14):r.fang(x,hy-7,5,3,-1.57,BONE)
    if d>.35:r.line([(hx+1,hy+3),(hx+9,hy+4)],OUTLINE,2)
    else:eye(r,hx+6,hy+4,'crystal',AZURE,4.4)
    return a

def sunwheel(clip,n):
    a,r,w,s,d,ph,b=setup('sunwheel',clip,n,(0,34),0)
    R=18
    hov=40+b*1.5-sm(min(1,d*1.15))*(40-R-4)
    cx=-8*w+17*s
    ramp=GOLD if d<.2 else (ORANGE if d<.45 else (BROWN if d<.7 else TAUPE))
    rays=ORANGE if d<.2 else (BROWN if d<.5 else TAUPE)
    spin=ph*.6+ (w*-1.2+s*2.4)+d*3
    for k in range(14):
        ang=spin+k*6.2832/14
        L=(11+6*w+7*s)*(1 if d<.45 else max(.25,1-d))+(k%2)*4
        L*=1-.65*max(0,-math.sin(ang))          # rays pointing down stay short, so the disc can hover low
        bx,by=cx+math.cos(ang)*(R-1),hov+math.sin(ang)*(R-1)
        tx,ty=cx+math.cos(ang)*(R+L),hov+math.sin(ang)*(R+L)
        nx,ny=-math.sin(ang)*4.5,math.cos(ang)*4.5
        r.poly([(bx+nx,by+ny),(tx,ty),(bx-nx,by-ny)],rays[2] if k%2 else rays[3],OUTLINE)
    r.ball(cx,hov,R,R,ramp)
    r.ball(cx,hov,R-5,R-5,rays,0)
    r.ball(cx-2,hov+1,R-8,R-8,ramp,0)
    ex=cx+4+6*s
    if d>.3:
        for sgn in (-1,1):cross_x=ex-1+sgn*8;r.line([(cross_x-3,hov+5),(cross_x+3,hov-1)],OUTLINE,2);r.line([(cross_x-3,hov-1),(cross_x+3,hov+5)],OUTLINE,2)
        r.line([(ex-9,hov-9),(ex,hov-7),(ex+9,hov-9)],OUTLINE,2)
    else:
        for sgn in (-1,1):slit(r.a,*r.t(ex-1+sgn*7,hov+4),3.6,2.6,CRIMSON,ramp[3],side=-sgn,slant=.8)
        gap=3+6*s
        r.poly([(ex-9,hov-5),(ex+9,hov-5),(ex+7,hov-8-gap),(ex-7,hov-8-gap)],CRIMSON[0],OUTLINE)
        for x in (-6,-2,2,6):r.fang(ex+x,hov-5,3,2.4,-1.57,BONE)
        for x in (-4,0,4):r.fang(ex+x,hov-8-gap,3,2.4,1.57,BONE)
    if d<.4:   # a scorch of flame trails below the disc
        for k in range(4):
            fx=cx-9+k*6;fl=4+2*math.sin(ph+k)+2*s
            r.poly([(fx-2.5,hov-R+3),(fx+(k-1.5)*1.5,hov-R-fl),(fx+2.5,hov-R+3)],ORANGE[3],OUTLINE)
    if d>.6:r.ball(cx,hov-R+1,R*.8,3,TAUPE)
    return a

def firephoenix(clip,n):
    a,r,w,s,d,ph,b=setup('firephoenix',clip,n,(0,34),-1.0)
    hov=26+30*(1-sm(min(1,d*1.1)))+b*1.4+3*w-2*s
    ramp=ORANGE if d<.35 else (BROWN if d<.65 else TAUPE)
    fl=GOLD if d<.35 else (ORANGE if d<.65 else TAUPE)
    flap=math.sin(ph)*(1-d)*.25-.5*w+.5*s+.4*d
    for back in (1,0):    # wings of flame-tipped quills
        for i in range(7):
            ang=1.45-i*.2+flap*(1 if back else .7)+(.25 if back else 0)
            L=34-i*2.5+(0 if back else 3)
            ox=-4-6*back
            tip=(ox+math.cos(ang)*L*(1-.4*d),hov+10+math.sin(ang)*L*.85*(1-.5*d))
            r.taper([(ox,hov+8),tip],ramp if back else ORANGE if d<.35 else ramp,6-i*.4,1.2)
            r.ball(tip[0],tip[1],2.8,2.8,fl)
    for k in range(3):    # tail flames
        ang=3.55+k*.35+math.sin(ph+k)*.1*(1-d)
        tx,ty=-12+math.cos(ang)*(30-k*3)*(1-.3*d),hov-6+math.sin(ang)*(24-k*2)
        r.taper([(-10,hov-2),(-14+(tx+10)*.5,hov-4+(ty-hov+4)*.5+3),(tx,ty)],CRIMSON if d<.65 else TAUPE,8,1.5)
        r.ball(tx,ty,3,3,fl)
    r.ball(0,hov+4,15,17,ramp)
    r.ball(3,hov-1,9,11,fl)
    for x,y in ((-4,-14),(3,-17)):r.fang(x,hov+y,9,5,-1.57+x*.04,GOLD)       # talons tucked
    hx,hy=9+15*s-7*w,hov+25-3*s
    r.limb([(3,hov+14),(hx-3,hy-5)],ramp,10)
    for k in range(3):    # flame crest
        ang=1.2+k*.4+math.sin(ph+k)*.1*(1-d)
        L=17-k*2.5
        r.taper([(hx-2,hy+6),(hx-2+math.cos(ang)*L*.55,hy+6+math.sin(ang)*L*.6),(hx-2+math.cos(ang)*L,hy+6+math.sin(ang)*L)],CRIMSON if d<.65 else TAUPE,5,1)
    r.ball(hx,hy,10,10,ramp)
    gap=1+6*s+2*w
    r.poly([(hx+5,hy-1),(hx+22,hy-3-gap*.5),(hx+6,hy-3-gap)],GOLD[2],OUTLINE)       # hooked beak, two halves
    r.poly([(hx+5,hy-3-gap),(hx+23,hy-4-gap*.5),(hx+25,hy-8-gap),(hx+6,hy-5-gap)],GOLD[3],OUTLINE) if False else None
    r.poly([(hx+5,hy+1),(hx+22,hy-1+gap*0),(hx+17,hy+4),(hx+5,hy+5)],GOLD[3],OUTLINE)
    if d>.35:r.line([(hx,hy+4),(hx+8,hy+3)],OUTLINE,2)
    else:eye(r,hx+4,hy+5,'round',GOLD,3.2)
    if s>.3:
        for k in range(6):
            fx,fy=hx+24+k*6*s,hy-3-(k%3)*2.5
            r.ball(fx,fy,3.4-k*.2,2.8-k*.15,ORANGE)
            r.ball(fx+1,fy,1.8,1.5,GOLD)
    return a

def acornmimic(clip,n):
    a,r,w,s,d,ph,b=setup('acornmimic',clip,n,(0,0),0)
    hop=max(0,math.sin(ph))*3 if clip=='walk' else 0
    cx=-5*w+9*s+4*d
    base=10+hop+b*.6-3*w
    open_=max(w,s)*.9+(.35 if clip=='idle' and n in(2,3) else 0)
    # legs: two stubby roots
    for i,x in enumerate((-8,8)):
        sw=math.sin(ph+i*3.14)*3.5 if clip=='walk' else 0
        r.limb([(cx+x,base+4),(cx+x+sw*.5+4*d*(i*2-1),5+max(0,sw)),(cx+x+sw+5*d*(i*2-1),2)],BROWN,5)
        r.ball(cx+x+sw+2+5*d*(i*2-1),2,5,2.3,BROWN)
    sep=18*d
    if d>.45:   # rigid shell: the nut splits into two halves
        r.ball(cx-sep*.6,base+14-6*d,14,17,BROWN,.25)
        r.ball(cx+sep*.9,base+10-9*d,13,15,BROWN,-.3)
        r.ellipse(cx-sep*.6+3,base+18-6*d,6,8,BONE[3])
        r.line([(cx-sep*.1,base+26-6*d),(cx+sep*.1,base+4-6*d)],OUTLINE,1)
    else:
        r.ball(cx,base+13,15.5,18,BROWN)
        r.ball(cx+1,base+9,10,9,BROWN[::1] if False else BROWN)
        # mouth cavity under the lifted cap
        if open_>.05:
            r.ellipse(cx,base+22+2*open_,13,3+8*open_,CRIMSON[0])
            r.ball(cx+1,base+20,6,3+3*open_,CRIMSON,0)
            for k in range(-3,4):r.poly([(cx+k*3.6-1.6,base+22),(cx+k*3.6+1.6,base+22),(cx+k*3.6,base+22-4-2*open_)],BONE[4],OUTLINE)
        else:
            r.line([(cx-12,base+22),(cx+12,base+22)],OUTLINE,2)
            for k in range(-3,4):r.poly([(cx+k*3.6-1.5,base+22),(cx+k*3.6+1.5,base+22),(cx+k*3.6,base+19)],BONE[4])
    # cap hinged at the back
    hd=d if d>.3 else 0
    ang=open_*.85+(.95*d)
    rc=L.Rig(a,cx-11,base+25,ang,lift=0)
    ccx=cx+(-26*d if d>.45 else 0)
    rc.ball(ccx,base+30-10*d,17,10.5,TAUPE)
    rc.ellipse(ccx,base+24-10*d,17.5,3,TAUPE[1])
    for k in range(5):rc.line([(ccx-12+k*6,base+31-10*d),(ccx-11+k*6,base+27-10*d)],TAUPE[0],1)
    rc.taper([(ccx,base+38-10*d),(ccx+1,base+44-10*d),(ccx+5,base+49-10*d)],MOSS,3.5,1.5)
    rc.ball(ccx+7,base+49-10*d,5,3.2,MOSS,.3)
    if d>.3:
        r.line([(cx+2,base+17),(cx+10,base+15)],OUTLINE,2);r.line([(cx-8,base+16),(cx-2,base+16)],OUTLINE,2)
    else:
        for sg in (-1,1):slit(r.a,*r.t(cx+sg*6.5+2,base+17),3.4,2.3,AMBER,TAUPE[2],side=-sg,slant=.9)
    for sg in (-1,1):   # stubby twig arms
        r.line([(cx+sg*15,base+12),(cx+sg*(20+8*s*(sg>0)),base+6+12*w-2*s)],BROWN[0],3)
    return a

def lanternowl(clip,n):
    a,r,w,s,d,ph,b=setup('lanternowl',clip,n,(0,34),-.5)
    hov=26+18*(1-sm(min(1,d*1.1)))+b*1.4+3*w-3*s
    ramp=TAUPE
    glow=1-min(1,d*1.6)
    flap=math.sin(ph)*(1-d)*.22-.45*w+.55*s+.35*d
    for back in (1,0):
        for i in range(6):
            ang=1.15-i*.19+flap*(1 if back else .7)+(.22 if back else 0)
            L=30-i*2.6
            ox=-5-5*back
            tip=(ox+math.cos(ang)*L*(1-.35*d),hov+8+math.sin(ang)*L*.8*(1-.4*d))
            r.taper([(ox,hov+6),tip],ramp,6.5-i*.4,1.4)
    r.ball(0,hov+4,14,17,ramp)
    r.ball(4,hov,9,12,BONE)
    for k in range(3):r.poly([(1+k*4,hov+8-k*4),(4+k*4,hov+2-k*4),(7+k*4,hov+8-k*4)],TAUPE[2],OUTLINE)
    # lantern hanging from the talon on a cord
    lx,ly=4+13*s-4*w,hov-23+6*d
    r.fang(0,hov-11,8,4,-1.5,GOLD)
    r.line([(2,hov-13),(lx,ly+9)],TAUPE[0],1)
    for k,col in enumerate(((AMBER if glow>.4 else TAUPE),)):
        pass
    r.poly([(lx-5,ly+9),(lx+5,ly+9),(lx+4,ly-5),(lx-4,ly-5)],AMBER[1] if glow>.2 else TAUPE[1],OUTLINE)
    r.ball(lx,ly+2,3.6,5,GOLD if glow>.4 else TAUPE,0)
    r.line([(lx-5,ly+9),(lx+5,ly+9)],BROWN[1],2);r.line([(lx-4,ly-5),(lx+4,ly-5)],BROWN[1],2)
    if glow>.3:
        for k in range(4):r.ball(lx+(k-1.5)*3,ly+2+((ph*3+k*2)%5),1.2+glow,1.2+glow,GOLD,0)
    hx,hy=7+10*s-5*w,hov+22
    for sg in (-1,1):r.poly([(hx+sg*6,hy+8),(hx+sg*10,hy+18),(hx+sg*2,hy+10)],TAUPE[2],OUTLINE)   # ear tufts
    r.ball(hx,hy,13,11,ramp)
    r.ball(hx+3,hy-1,10,8.5,BONE)
    gap=1+4*s
    r.poly([(hx+7,hy-2),(hx+19,hy-4-gap),(hx+7,hy-8-gap)],GOLD[2],OUTLINE)
    if d>.4:
        r.line([(hx-2,hy+3),(hx+4,hy+2)],OUTLINE,2);r.line([(hx+5,hy+2),(hx+11,hy+1)],OUTLINE,2)
    else:
        for sg in (-1,1):eye(r,hx+sg*4.8+3,hy+2,'round',GOLD,4.3)
    return a

def harvestreaper(clip,n):
    a,r,w,s,d,ph,b=setup('harvestreaper',clip,n,(0,0),0)
    H=1-.72*d
    cy=0+b*.5
    walk=math.sin(ph)*3 if clip=='walk' else 0
    for sg in (-1,1):    # feet under the robe
        r.ball(sg*6+walk*sg*.7,2,5,2.5,TAUPE)
    hem=8+12*d
    r.poly([(-17-6*d,2),(17+6*d,2),(11,hem+22*H),(0,hem+34*H),(-11,hem+22*H)],VIOLET[2],OUTLINE)
    r.ball(0,2+24*H,13+5*d,18*H+2,VIOLET)
    r.line([(-8,hem+4),(-3,hem+22*H),(-6,hem+28*H)],VIOLET[4],1)
    for k in range(4):r.line([(-12+k*8,3),(-11+k*8,9)],VIOLET[0],1)   # ragged hem
    ty=2+36*H+b*1.6
    hx,hy=2+2*s-3*w+5*d,ty+8-4*d
    r.ball(hx,hy-4,9.5,10,AMBER)       # lantern-pumpkin face under the straw hat
    for sg in (-1,1):
        if d>.4:r.line([(hx+sg*4-2,hy-3),(hx+sg*4+2,hy-5)],OUTLINE,2)
        else:eye(r,hx+sg*4.3,hy-1,'tri',GOLD,2.9)
    r.poly([(hx-6,hy-8),(hx-3,hy-11),(hx,hy-8),(hx+3,hy-11),(hx+6,hy-8),(hx+4,hy-6),(hx-4,hy-6)],OUTLINE)
    for k in range(4):r.poly([(hx-5+k*3.2,hy-8),(hx-3.6+k*3.2,hy-6),(hx-5+k*3.2+1.5,hy-8)],BONE[4])
    r.ellipse(hx,hy+4+3*d,16,2.5,GOLD[1])                   # hat brim, tipped as it falls
    r.ball(hx,hy+7+3*d,9,6,GOLD)
    for k in range(5):r.line([(hx-12+k*6,hy+3+3*d),(hx-15+k*7.5,hy-2+3*d)],GOLD[3],1)   # straw spills
    # scythe arm
    sh=(6,ty-4)
    ang=-.9+w*2.2-s*2.7+d*1.6+math.sin(ph)*.05*(1-d)    # raised behind the head, then down across the body
    hand=(sh[0]+9*math.cos(ang+1.2),sh[1]+9*math.sin(ang+1.2))
    r.limb([sh,(sh[0]+5,sh[1]-5*H),hand],VIOLET,5)
    r.ball(hand[0],hand[1],3,3,AMBER)
    pa=ang+1.2+(.55 if True else 0)
    ex,ey=hand[0]+math.cos(pa)*26,hand[1]+math.sin(pa)*26
    bx,by=hand[0]-math.cos(pa)*10,hand[1]-math.sin(pa)*10
    r.line([(bx,by),(ex,ey)],BROWN[1],3)
    bl=[(ex,ey),(ex+math.cos(pa-1.7)*22,ey+math.sin(pa-1.7)*22),(ex+math.cos(pa-1.7)*22+math.cos(pa)*-6,ey+math.sin(pa-1.7)*22-math.sin(pa)*6),(ex-math.cos(pa)*7,ey-math.sin(pa)*7)]
    r.poly(bl,SLATE[3],OUTLINE)
    r.line([(bl[0][0],bl[0][1]),(bl[1][0],bl[1][1])],WHITE,1)
    r.limb([(-8,ty-5),(-12,ty-12*H),(-7-3*s,ty-14*H)],VIOLET,4)
    return a

def ambermantis(clip,n):
    a,r,w,s,d,ph,b=setup('ambermantis',clip,n,(0,26),-.30)
    cy=34+b-6*w-14*d
    for i,x in enumerate((-13,-4,6)):
        sw=math.sin(ph+i*2.1)*5 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*2.1))*5 if clip=='walk' else 0
        r.limb([(x,cy-4),(x-5+sw-8*d,cy-14+up*.3),(x-6+sw-10*(1 if i%2 else -1)*d+(1 if i%2 else -1)*5,3+up)],AMBER,3.2)
    r.taper([(-14,cy+2),(-28,cy+6),(-42,cy+3-6*d),(-48,cy-4-8*d)],AMBER,12,3)      # abdomen
    r.ball(-30,cy+5,13,9,AMBER,.15)
    for k in range(3):r.line([(-24-k*6,cy+11-k),(-24-k*6,cy-1)],AMBER[0],1)
    wy=1-d
    r.poly([(-14,cy+6),(-37,cy+16*wy+2),(-40,cy+11*wy),(-22,cy+4)],GOLD[3],OUTLINE)     # folded wing case
    r.ball(0,cy+4,13,10,AMBER)                                                      # thorax
    r.ball(4,cy+16,7.5,12,AMBER,-.4)
    hx,hy=10+7*s-4*w,cy+30
    r.poly([(hx-9,hy+3),(hx+9,hy+4),(hx+4,hy-10),(hx-4,hy-10)],AMBER[2],OUTLINE)
    for sg in (-1,1):
        r.ball(hx+sg*8+1,hy+1,5,5.5,GOLD,0)
        if d<.4:r.ellipse(hx+sg*8+2,hy+1,1.6,2.6,CRIMSON[0])
    r.line([(hx-3,hy+8),(hx-9,hy+17+math.sin(ph)*2)],AMBER[0],1);r.line([(hx+3,hy+8),(hx+9,hy+17+math.sin(ph+1)*2)],AMBER[0],1)
    r.poly([(hx-3,hy-8),(hx+3,hy-8),(hx,hy-13-4*s)],CRIMSON[2],OUTLINE)    # mandibles
    # raptorial claws: folded (idle), cocked back (wind-up), slashing forward (strike)
    for k,sg in enumerate((-1,1)):
        reach=s*26-w*6
        e=(14+sg*2-4*w+reach*.55,cy+20+10*w-4*s)
        t=(e[0]+8+reach+d*(-10),e[1]-(14-10*w)+(4-14*s)-14*d)
        r.limb([(6,cy+14),e,t],AMBER,4.5)
        bl=[t,(t[0]+14,t[1]-3*(1-s)-4*s),(t[0]+9,t[1]-9+12*s),(t[0]-3,t[1]+4)]
        r.poly(bl,GOLD[3] if d<.7 else AMBER[2],OUTLINE)
        r.line([bl[0],bl[1]],WHITE,1)
    return a

def snowstoat(clip,n):
    a,r,w,s,d,ph,b=setup('snowstoat',clip,n,(6,12),-.12)
    arch=5*w+0*s
    cy=17+b-6*d+arch*.5
    sway=math.sin(ph)*(1-d)
    tl=[(-26,cy),(-40,cy+2+sway*3),(-52,cy+5-4*d),(-62,cy+2+sway*2-6*d)]
    r.taper(tl,FUR,9,5)
    r.ball(*tl[-1],6,5.5,SLATE,0) if False else r.ball(tl[-1][0],tl[-1][1],6,5.5,[SLATE[0],SLATE[0],SLATE[1],SLATE[1],SLATE[2]])
    for i,x in enumerate((-20,-10,12,22)):
        sw=math.sin(ph+i*1.8)*5 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.8))*4 if clip=='walk' else 0
        fx=x+5+sw+(13*s if i>=2 else -3*w)+8*d*(1 if i>=2 else -1)
        r.limb([(x,cy-3),(x+3+4*d,8+up),(fx,2.5+up+3*d)],FUR,5.5)
        r.ball(fx+2,2+up+3*d,5,2.4,FUR)
        for j in range(3):r.fang(fx+3+j*1.6,1.6+up+3*d,2.5,1.2,-.2,BONE)
    r.ball(-4,cy+arch*.3,32,10.5,FUR)
    r.ball(0,cy-5,25,4.4,FUR[::1] if False else PEARL)
    for k in range(7):r.ball(-26+k*8,cy+8+arch*.3,5,4,FUR)           # fluffed winter coat
    hx,hy=29+15*s-10*w,cy+4+arch-5*d
    r.limb([(18,cy+2),(hx-6,hy)],FUR,12)
    r.ball(hx,hy,12,9.5,FUR)
    r.ball(hx+10,hy-2,9,5.5,FUR)
    r.ball(hx+17,hy,2.6,2.2,SLATE)
    for sg in (-4,2):r.poly([(hx+sg-4,hy+7),(hx+sg,hy+15),(hx+sg+4,hy+7)],FUR[2],OUTLINE)
    gap=1+9*s+3*w
    r.poly([(hx+3,hy-5),(hx+18,hy-5),(hx+16,hy-7-gap),(hx+2,hy-7-gap*.6)],CRIMSON[0])
    r.poly([(hx+1,hy-7-gap*.6),(hx+16,hy-7-gap),(hx+13,hy-11-gap),(hx+1,hy-10-gap*.6)],FUR[2],OUTLINE)
    for x in (hx+7,hx+12):r.fang(x,hy-5,5,2.6,-1.57,BONE)
    if d>.3:r.line([(hx,hy+3),(hx+8,hy+3)],OUTLINE,2)
    else:slit(r.a,*r.t(hx+5,hy+3),3.6,2.5,CRIMSON,FUR[3],slant=1.0)
    return a

def rimesaber(clip,n):
    a,r,w,s,d,ph,b=setup('rimesaber',clip,n,(6,18),-.22)
    cy=29+b-6*w-14*d
    for i,x in enumerate((-23,-12,12,23)):
        sw=math.sin(ph+i*1.9)*5 if clip=='walk' else 0
        up=max(0,math.sin(ph+i*1.9))*5 if clip=='walk' else 0
        reach=(17*s-4*w) if i>=2 else -3*w
        up2=(11*s if i==3 else 0)
        fx=x+4+sw+reach+(7*d if i>=2 else -7*d)
        r.limb([(x,cy-3),(x+3+5*d,15-2*d+up),(fx,4+up+up2+4*d)],FUR,8)
        r.ball(fx+2,3+up+up2+4*d,7,3.3,FUR)
        for j in range(3):r.fang(fx+4+j*2,2+up+up2+4*d,3.5+2*s,1.6,-.2,AZURE)
    tl=[(-28,cy+3),(-40,cy+7+math.sin(ph)*(1-d)*3),(-46,cy+3-5*d)]
    r.taper(tl,FUR,7,4)
    r.ball(-4,cy,30,13,FUR)
    r.ball(0,cy-6,22,5,PEARL)
    for k in range(5):r.poly([(-24+k*9-3,cy+10),(-24+k*9,cy+10+4),(-24+k*9+3,cy+10)],AZURE[1])
    for k in range(4):                               # frost spikes along the shoulders
        r.poly([(-14+k*8-4,cy+12),(-14+k*8,cy+22-k*2),(-14+k*8+4,cy+12)],AZURE[3],OUTLINE)
    for k in range(5):r.line([(-18+k*8,cy+11),(-16+k*8,cy-4)],AZURE[1],2)      # ice stripes
    hx,hy=27+16*s-9*w,cy+7-4*d
    r.ball(hx,hy,16,11,FUR)
    r.ball(hx+12,hy-3,9,8,PEARL)
    r.ball(hx+19,hy,3.6,3,SLATE)
    r.poly([(hx-4,hy+8),(hx+15,hy+3),(hx+15,hy+7),(hx-3,hy+12)],AZURE[1],OUTLINE)
    for k,x in enumerate((hx-3,hx+5)):r.poly([(x-3,hy+11),(x+1,hy+21+3*k),(x+4,hy+11)],AZURE[2],OUTLINE)   # ear spikes
    gap=1+11*s+3*w
    r.poly([(hx+4,hy-7),(hx+20,hy-7),(hx+17,hy-9-gap),(hx+3,hy-9-gap*.6)],CRIMSON[0])
    r.poly([(hx+3,hy-8-gap*.6),(hx+18,hy-9-gap),(hx+14,hy-13-gap),(hx+3,hy-12-gap*.6)],FUR[2],OUTLINE)
    r.fang(hx+10,hy-6,17+4*s,5.5,-1.6,AZURE)        # the great sabre fangs
    r.fang(hx+16,hy-6,14+3*s,4.5,-1.5,AZURE)
    if d>.35:r.line([(hx+1,hy+3),(hx+9,hy+4)],OUTLINE,2)
    else:eye(r,hx+5,hy+4,'hollow',AZURE,4.6)
    return a

def snowgiant(clip,n):
    a,r,w,s,d,ph,b=setup('snowgiant',clip,n,(0,20),0)
    k=1-.35*d
    sag=14*d
    walk=math.sin(ph)*4 if clip=='walk' else 0
    for sg in (-1,1):    # legs and boots
        lx=sg*9+(walk*sg)+7*d*sg
        r.limb([(sg*8,24-sag),(lx,12-sag*.5),(lx+2,5)],FUR,10)
        r.ball(lx+3,4,9,4,BROWN)
    top=26+b*.5-sag
    r.ball(0,top+14*k,19,17*k+3,FUR)          # fur coat
    r.ball(0,top+8*k,15,11*k,SLATE)           # mail
    r.poly([(-17,top+4),(17,top+4),(15,top-4),(-15,top-4)],BROWN[1],OUTLINE)
    for q in range(-2,3):r.line([(q*6,top+4),(q*6,top-4)],BROWN[3],1)
    hx,hy=3+4*s-3*w+6*d,top+37*k-4*d
    r.ball(hx,hy,12,11,FUR)
    r.ball(hx+2,hy-3,9,6,PEARL)                # beard
    for sg in (-1,1):                          # horned helm
        r.poly([(hx+sg*10,hy+5),(hx+sg*21,hy+16),(hx+sg*13,hy+17),(hx+sg*8,hy+9)],BONE[3],OUTLINE)
    r.poly([(hx-12,hy+4),(hx+12,hy+4),(hx+9,hy+13),(hx-9,hy+13)],SLATE[2],OUTLINE)
    if d>.4:r.line([(hx-5,hy),(hx+8,hy-1)],OUTLINE,2)
    else:
        for sg in (-1,1):eye(r,hx+sg*5.5+1,hy+1,'dot',AZURE,2.4)
        r.line([(hx-5,hy-6),(hx+7,hy-5)],OUTLINE,2)
    sh=(10,top+26*k)
    ang=.6+w*1.4-s*3.1+d*(-.5)
    hand=(sh[0]+9+5*math.cos(ang),sh[1]-3+14*math.sin(ang))
    r.limb([sh,(sh[0]+9,sh[1]-3),hand],FUR,8)
    r.ball(hand[0],hand[1],5,5,BROWN)
    sa=ang+(.1)
    bx,by=hand[0]-math.cos(sa)*8,hand[1]-math.sin(sa)*8
    ex,ey=hand[0]+math.cos(sa)*30,hand[1]+math.sin(sa)*30
    r.line([(bx,by),(ex,ey)],BROWN[1],5)
    r.ball(ex+math.cos(sa)*6,ey+math.sin(sa)*6,11,11,AZURE)            # ice club head
    r.ball(ex+math.cos(sa)*6-2,ey+math.sin(sa)*6+2,5,5,FUR)
    for q in range(3):
        aa=sa+1.2+q*.8
        r.poly([(ex+math.cos(sa)*6+math.cos(aa)*8,ey+math.sin(sa)*6+math.sin(aa)*8),(ex+math.cos(sa)*6+math.cos(aa)*16,ey+math.sin(sa)*6+math.sin(aa)*16),(ex+math.cos(sa)*6+math.cos(aa+.4)*8,ey+math.sin(sa)*6+math.sin(aa+.4)*8)],AZURE[3],OUTLINE)
    r.limb([(-10,top+26*k),(-19,top+18*k),(-16,top+10*k)],FUR,8)
    r.ball(-16,top+9*k,5,5,BROWN)
    if d>.55:   # slumped into a drift
        r.ball(-4,4,20,5+4*(1-d),PEARL)
    return a

def longnightwyrm(clip,n):
    a,r,w,s,d,ph,b=setup('longnightwyrm',clip,n,(0,14),-.05)
    sway=math.sin(ph)*(1-d)
    pts=[(-52+14*d,6),(-44+8*d,14-4*d+sway*2),(-30,10),(-14,16-5*d),(2,10+sway*2),(16,16-6*d)]
    # coils release along the floor in death
    r.taper(pts,VIOLET,13,10)
    for i,(x,y) in enumerate(pts[1:],1):
        r.poly([(x-4,y+9),(x,y+16-i%2*3),(x+4,y+9)],PURPLE[3],OUTLINE)        # dorsal crest
        r.ellipse(x+1,y+4,1.6,1.6,GOLD[4]) ; r.ellipse(x-5,y+1,1.2,1.2,AZURE[4])    # stars across the scales
    ln=[(16,14-6*d),(24,22-8*d+4*w),(28,34-14*d+6*w-4*s)]
    hx,hy=30+18*s-10*w,38+b-22*d+10*w-6*s
    r.taper([pts[-1],(24,20-6*d),(20-7*w,30+8*w-12*d),(hx-8,hy-6)],VIOLET,12,9)
    r.ball(hx,hy,13,10,VIOLET)
    r.ball(hx+11,hy-3,10,6,PURPLE)
    gap=2+11*s+4*w+4*d
    r.poly([(hx+2,hy-4),(hx+22,hy-5),(hx+22,hy-7-gap),(hx+1,hy-7-gap*.5)],CRIMSON[0])
    r.poly([(hx,hy-6-gap*.5),(hx+22,hy-7-gap),(hx+19,hy-11-gap),(hx+1,hy-10-gap*.5)],PURPLE[2],OUTLINE)
    for x in (hx+8,hx+14,hx+20):r.fang(x,hy-5,5+2*s,2.4,-1.57,BONE)
    for x in (hx+10,hx+17):r.fang(x,hy-7-gap,4,2.2,1.57,BONE)
    for sg in range(3):
        r.poly([(hx-6-sg*4,hy+4),(hx-13-sg*6,hy+12+sg*3),(hx-9-sg*4,hy+1)],VIOLET[2],OUTLINE)   # night crest
        r.ellipse(hx-10-sg*5,hy+8+sg*2.5,1.4,1.4,GOLD[4])
    if d>.35:r.line([(hx+2,hy+3),(hx+10,hy+4)],OUTLINE,2)
    else:eye(r,hx+6,hy+3,'star',AZURE,4.4)
    return a


#KINDS-END
DRAW={k:globals()[k] for k in KINDS if k in globals()}
def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    clipped = bool(grid.any() and (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()))   # BEFORE the roll hides it
    if grid.any():
        LOWEST[kind] = max(LOWEST.get(kind, -999), int(np.nonzero(grid.any(axis=1))[0].max()) - kay)
    if kind in FLYING:
        grid = np.roll(grid, kay - origin(kind), axis=0)
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
    missing = [k for k in KINDS if k not in DRAW]
    assert not missing, 'not drawn yet: ' + ', '.join(missing)
    data = {kind: frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX + kind + '_all' + os.environ.get('SOURCE_SUFFIX', '')  # a frame-size change needs a NEW source
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/yearwheel_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/yearwheel_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'yearwheel_{kind}.png'


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
    print('Exported 544 saved PixelFlow frames and derived health-bar tops.', flush=True)


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



def chosen():
    names=[k for k in sys.argv[2:] if k in KINDS]
    return names or [k for k in KINDS if k in DRAW]
def preview():
    OUT.mkdir(parents=True,exist_ok=True)
    ks=chosen()
    poses=[('idle',0),('walk',2),('attack',2),('attack',4),('attack',6),('hurt',1),('die',2),('die',4),('die',7)]
    zoom=int(os.environ.get('YW_ZOOM','2'))
    rows=[]
    for k in ks:
        ims=[rgba(frame(k,c,n)) for c,n in poses]
        box=None
        for im in ims:
            b=im.getbbox()
            if b:box=b if box is None else (min(box[0],b[0]),min(box[1],b[1]),max(box[2],b[2]),max(box[3],b[3]))
        pad=3
        box=(max(0,box[0]-pad),max(0,box[1]-pad),box[2]+pad,box[3]+pad)
        rows.append([im.crop(box).resize(((box[2]-box[0])*zoom,(box[3]-box[1])*zoom),Image.NEAREST) for im in ims])
    cw=max(r[0].width for r in rows); ch=max(r[0].height for r in rows)
    perrow=int(os.environ.get('YW_COLS','5')); nrow=-(-len(poses)//perrow)
    sheet=Image.new('RGBA',(perrow*cw,len(ks)*nrow*ch),'#243346')
    pen=ImageDraw.Draw(sheet)
    for y,(k,r) in enumerate(zip(ks,rows)):
        for x,im in enumerate(r):sheet.alpha_composite(im,((x%perrow)*cw,(y*nrow+x//perrow)*ch))
        pen.text((4,y*nrow*ch+2),NAMES[k],fill='white')
    path=OUT/('poses-'+'-'.join(ks)+'.png')
    sheet.save(path)
    print(path,sheet.size)
def extents():
    for kind in chosen():
        data=frames(kind)
        b=Image.fromarray(data['idle'][0]).getbbox()
        ow,oh=OLD_IDLE[kind]
        print(f"{kind:14s} idle {b[2]-b[0]}x{b[3]-b[1]} (old {ow}x{oh}) raw lowest vs anchor {LOWEST[kind]}",flush=True)
    assert not BAD, BAD[:8]

if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    {'preview':preview,'extents':extents,'build':build,'refresh':refresh,'export':export,'verify':verify}[cmd]()
