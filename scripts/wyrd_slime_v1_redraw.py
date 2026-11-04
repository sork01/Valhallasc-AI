#!/usr/bin/env python3
"""Wyrdwood slime-style PixelFlow art: preview | build | legs | export.

Separate source names preserve previous art. Rigid armour and animal anatomy
move by joints/rotation, never universal squash or a shared puddle death.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/wyrd-slime'
REGISTRY = ROOT/'scripts/wyrd_slime_v1_sources.txt'
PREFIX = 'valhallasc_wyrd_slime_style_'
KINDS = ['boar','crow','troll','weaver','ram','oakhorn','hrungnir']
NAMES = dict(boar='Rotfang Boar',crow='Gallowcrow',troll='Mosshide Troll',weaver='Wyrdweaver',ram='Stormram',oakhorn='Oakhorn',hrungnir='Hrungnir')
W = H = 96
AX, AY = 48, 90
CLIPS = old.CLIPS
PALETTE = ['#00000000', '#22222f', '#ffffff', '#fffbea', '#eda0ad',
           '#534b42', '#8c8065', '#bdb093', '#e7dab5', '#fff4d7',
           '#252c40', '#4e5e7c', '#8094b3', '#b8d2e8', '#eaf6ff',
           '#281943', '#50327f', '#8158b8', '#b494e3', '#e4d0ff',
           '#103641', '#226578', '#42a4b1', '#8ae4e8', '#dcffff',
           '#5b3b22', '#98602c', '#cb963c', '#f2cd6a', '#fff3ae',
           '#163e29', '#2b7846', '#55ba73', '#a3e9ae', '#e2ffe8',
           '#40201f', '#7a3334', '#b95154', '#e98c83', '#ffd0ae']
BONE=list(range(5,10))
PLATE=list(range(10,15))
PURPLE=list(range(15,20))
TEAL=list(range(20,25))
GOLD=list(range(25,30))
GREEN=list(range(30,35))
RED=list(range(35,40))
ICE=TEAL


class Painter:
    """Round shaded components, upper-left light and large slime-like eyes."""
    def __init__(self, cx=46, lift=0):
        self.im = Image.new('P', (W, H), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx, self.lift = cx, lift

    def pos(self, x, y):
        return round(self.cx+x), round(AY-y-self.lift)

    def ellipse(self, x, y, rx, ry, col):
        px, py = self.pos(x, y)
        self.d.ellipse((round(px-rx), round(py-ry), round(px+rx), round(py+ry)), fill=col)

    def line(self, pts, col, width=1):
        self.d.line([self.pos(*p) for p in pts], fill=col, width=width)

    def poly(self, pts, col):
        self.d.polygon([self.pos(*p) for p in pts], fill=col)

    def ball(self, x, y, rx, ry, ramp):
        px, py = self.pos(x, y)
        for yy in range(max(0, math.floor(py-ry)), min(H, math.ceil(py+ry)+1)):
            for xx in range(max(0, math.floor(px-rx)), min(W, math.ceil(px+rx)+1)):
                u, v = (xx-px)/rx, (yy-py)/ry
                rr = u*u+v*v
                if rr > 1:
                    continue
                z = math.sqrt(max(0, 1-rr))
                value = max(0, min(.999, .23+.71*(-.40*u-.54*v+.74*z)))*(len(ramp)-1)
                lo = int(value)
                threshold = ((xx%4)*5+(yy%4)*3)%16/16
                shade = min(len(ramp)-1, lo+int(value-lo > threshold))
                if rr > .93 and u+v > .2:
                    shade = 0
                self.im.putpixel((xx, yy), ramp[shade])

    def limb(self, points, ramp, width=5):
        self.line(points, ramp[0], width+2)
        self.line(points, ramp[min(2, len(ramp)-1)], width)
        for x, y in points[1:-1]:
            self.ball(x, y, width/2, width/2, ramp)

    def eye(self, x, y, clip, n, size=1):
        if clip == 'die' and n >= 2:
            self.line([(x-2, y-2), (x+2, y+2)], 1, 2)
            self.line([(x-2, y+2), (x+2, y-2)], 1, 2)
        elif clip == 'idle' and n == 3:
            self.line([(x-3*size, y), (x+3*size, y+.5)], 1, 2)
        else:
            self.ellipse(x, y, 4.3*size, 6.4*size, 1)
            self.ellipse(x, y+.5, 3.3*size, 5.3*size, 3)
            self.ellipse(x+1, y-.2, 1.6*size, 3.4*size, 1)
            self.ellipse(x+.7, y+2.2, 1, 1, 2)
            if clip == 'attack' and n < 3:
                self.line([(x-4, y+6), (x+3, y+3)], 1, 2)

    def face(self, x, y, clip, n, size=1):
        for dx in (-6, 6):
            self.eye(x+dx*size, y, clip, n, size)
        if clip != 'die' or n < 2:
            self.ellipse(x-12*size, y-5, 2.5, 1.3, 4)
            self.ellipse(x+12*size, y-5, 2.5, 1.3, 4)
        self.line([(x-3, y-8), (x, y-9), (x+3, y-8)], 1)

    def crystal(self, x, y, height=10, width=3, tilt=0):
        self.poly([(x-width, y), (x+tilt, y+height), (x+width, y)], ICE[0])
        self.poly([(x-width+1, y+1), (x+tilt, y+height-2), (x, y+1)], ICE[3])
        self.line([(x, y+2), (x+tilt, y+height-3)], ICE[4])


def motion(clip, n):
    stride = math.sin(n*math.pi/4)*4 if clip=='walk' else 0
    bob = [0,1,2,1,0,-1][n] if clip=='idle' else 0
    lunge = [-1,-2,-4,1,4,3,1,0][n] if clip=='attack' else 0
    recoil = [-3,-2,1,0][n] if clip=='hurt' else 0
    fall = [0,.06,.19,.36,.57,.78,.94,1][n] if clip=='die' else 0
    return stride,bob,lunge,recoil,fall



def mix(a,b,t): return a+(b-a)*t

PALETTE += ['#33201d','#65402b','#9b6541','#ca9361','#f2c993']
BROWN=list(range(40,45))
PALETTE += ['#34455c','#6c88a4','#a8c6db','#d6eafa','#f4fcff',
            '#141627','#292d50','#4b5079','#7a82a4','#afb8d6']
FUR=list(range(45,50))
FEATHER=list(range(50,55))


def tusk(a,x,y,fall=0):
    a.poly([(x-3,y-3),(x+3,y+5),(x+2,y-2)],5)
    a.poly([(x-2,y-2),(x+2,y+4),(x+1,y-2)],9)


def animal(clip,n,kind):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=45+recoil+lunge*.6)
    stag=kind=='oakhorn';ram=kind=='ram'
    ramp=FUR if ram else BROWN
    leglen=21 if stag else 16
    y=leglen+15+bob*.35-fall*(leglen-1)
    # All upper legs sit behind the barrel: the belly masks their roots.
    # Far limbs are darker, narrower and land higher on the perspective plane.
    for far in (True,False):
        leg_ramp = ramp[:3] if far else ramp
        width = (3 if stag else 4) if not far else 2
        for front in (False,True):
            depth = 5 if far else 0
            phase = (0 if front else math.pi)+(math.pi if far else 0)
            swing = math.sin(n*math.pi/4+phase) if clip=='walk' else 0
            step = swing*(3.5 if stag else 3)
            lift = max(0,swing)*(4 if stag else 3)
            base = 4+(3 if far else 0)
            # Separate shoulder and haunch anchors, with a forward stifle and
            # backward hock on hind legs. Four hooves have distinct idle x's.
            if front:
                root=(9+depth,y-4)
                knee=(7+depth+step*.25,y-13)
                ankle=(12+depth+step*.7,10+lift*.7)
                foot=(13+depth+step,base+lift)
                folded=[(9+depth,12),(15+depth,8),(10+depth,6),(18+depth,base)]
            else:
                root=(-21+depth,y-3)
                knee=(-14+depth+step*.25,y-12)
                ankle=(-23+depth+step*.7,10+lift*.7)
                foot=(-22+depth+step,base+lift)
                folded=[(-21+depth,12),(-12+depth,8),(-23+depth,6),(-19+depth,base)]
            points=[root,knee,ankle,foot]
            points=[(mix(x,fx,fall),mix(yy,fy,fall))
                    for (x,yy),(fx,fy) in zip(points,folded)]
            # A tapered upper thigh, shaped knee and slender lower shin keep
            # boars/rams compact while retaining Oakhorn's longer deer legs.
            a.limb(points[:3],leg_ramp,width)
            a.limb(points[2:],leg_ramp,max(2,width-1))
            if not far:
                a.ball(*points[0],5 if front else 7,8 if front else 9,ramp)
            hoof_ramp=PLATE[:3] if ram else BROWN[:3]
            a.ball(*points[-1],3.5 if not far else 2.8,2 if not far else 1.7,hoof_ramp)
    a.ball(-5,y,23,14 if stag else 16,ramp)
    a.ball(-13,y+7,10,4,ramp[1:])
    # Tapered tail is jointed and curved, ending in a pointed tip.
    tail=[(-25,y+4),(-32,y+8+math.sin(n)*1.2),(-34,y+4),(-31,y+2)]
    a.line(tail,ramp[0],3);a.line(tail[:-1],ramp[2],1)
    if kind=='boar':
        for j in range(6):
            x=-23+j*6
            a.poly([(x,y+11),(x+2,y+21-j%2*3),(x+7,y+13)],25)
        for x,dy in [(-17,3),(-5,8),(5,2)]:
            a.ball(x,y+dy,3.5,3,GREEN)
    if ram:
        for j in range(7):
            a.ball(-23+j*6,y+8+(j%2)*3,7,7,FUR)
        for j in range(3):a.ball(-21+j*13,y-2,7,6,FUR)
    if stag:
        a.ball(-4,y+7,15,6,GREEN)
        a.line([(-17,y+8),(-5,y+12),(10,y+8)],28,1)
    hx=22+fall*3;hy=y+7+(8 if stag else 0)-fall*(11 if stag else 4)
    if stag:
        a.limb([(10,y+2),(13,y+15-fall*9),(hx-5,hy)],BROWN,9)
    a.ball(hx,hy,13,12,ramp)
    a.ball(hx-5,hy+6,6,3,ramp[1:])
    if ram:
        # Solid curled horns; the storm flicker fades after the body falls.
        for sign,off in [(-1,-6),(1,7)]:
            xx=hx+off;yy=hy+9
            a.ball(xx,yy,8,8,GOLD)
            a.ball(xx+sign,yy-1,4.5,4.5,PLATE)
            a.line([(xx-3,yy+4),(xx+3,yy+4)],27,1)
        if clip!='die' or n<5:
            a.line([(-12,y+18),(-8,y+24),(-3,y+19),(1,y+26)],23 if n%2 else 24,1)
    if stag:
        # Branching oak antlers: full tapered branches, leaves shed independently.
        for sg in (-1,1):
            base=(hx+sg*6,hy+9)
            trunk=[base,(hx+sg*11,hy+19),(hx+sg*9,hy+29)]
            a.limb(trunk,BROWN,3)
            a.line([(hx+sg*10,hy+19),(hx+sg*19,hy+26)],26,3)
            a.line([(hx+sg*11,hy+23),(hx+sg*16,hy+32)],28,2)
            for j,(dx,dy) in enumerate([(sg*19,26),(sg*9,29),(sg*16,32)]):
                leafx=hx+dx-(fall*10*(j+1)/3);leafy=hy+dy-fall*(8+j*8)
                a.ball(leafx,leafy,4,2.7,RED if j%2 else GOLD)
        if clip=='die':
            for j in range(3):a.ellipse(-23+j*13+fall*4, max(4,38-j*4-n*4),2,1,28 if j%2 else 38)
    # ears and face sit in front of the antlers/horns.
    if not ram:
        a.poly([(hx-10,hy+6),(hx-13,hy+18),(hx-2,hy+10)],ramp[1])
        a.poly([(hx+3,hy+9),(hx+9,hy+16),(hx+9,hy+5)],ramp[2])
    a.face(hx+1,hy,clip,n,.73)
    a.ball(hx+6,hy-7,8,4.8,PLATE if ram else (RED if kind=='boar' else BONE))
    a.ellipse(hx+10,hy-6,1.1,1,1)
    if kind=='boar':
        tusk(a,hx+2,hy-8,fall);tusk(a,hx+12,hy-8,fall)
    if clip=='die' and n>=3:
        # Fallen animal: closed eyes and folded legs, no puddle or body scaling.
        a.line([(hx-6,hy),(hx-1,hy-1)],1,2)
    return a


def boar(clip,n): return animal(clip,n,'boar')
def ram(clip,n): return animal(clip,n,'ram')
def oakhorn(clip,n): return animal(clip,n,'oakhorn')


def crow(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    y=39+bob*.8-fall*23
    flap=math.sin(n*math.pi/4)*13 if clip=='walk' else bob*2
    if clip=='attack':flap=[6,14,19,-10,-15,-8,0,3][n]
    # Rigid feathers pivot around wing joints; death folds them over the body.
    for far in (True,False):
        wingx=-17 if far else -3
        wy=y+5 if far else y-1
        tipx=-31+fall*17;tipy=y+20+flap*(1-fall)-fall*15
        if far:
            for j in range(4):
                a.poly([(-12,y+3),(-34+j*2,y-5+j*4),(-25+j*2,y-10+j*4)],50+j%3)
        a.poly([(wingx,wy),(tipx,tipy),(tipx-4,tipy-6),(tipx+1,tipy-7),(tipx-2,tipy-13),(tipx+4,tipy-11),(tipx+4,tipy-17),(wingx+9,wy-6)],50)
        a.ball(wingx-4,wy+1,10,7,FEATHER)
        if far:a.ball(0,y,18,15,FEATHER)
    for sg in (-1,1):
        foot=(sg*5+fall*sg*7,y-20+fall*10)
        a.limb([(sg*4,y-10),(sg*4,y-16),foot],GOLD,2)
        a.line([(foot[0]-3,foot[1]-1),(foot[0]+4,foot[1]-1)],27,2)
    hx=15+max(0,lunge);hy=y+10-fall*5
    a.ball(hx,hy,12,12,FEATHER)
    for j in range(3):a.poly([(hx-9+j*6,hy+8),(hx-12+j*7,hy+20-j*2),(hx-3+j*5,hy+8)],51)
    a.eye(hx+2,hy+1,clip,n,1)
    a.ellipse(hx-5,hy-5,2.5,1.5,4)
    gap=max(0,lunge)*.7
    a.poly([(hx+8,hy-1),(hx+23,hy-5),(hx+9,hy-5)],27)
    a.poly([(hx+9,hy-6-gap),(hx+21,hy-6-gap),(hx+9,hy-9-gap)],28)
    # Bone charm remains a solid object when the bird lands.
    a.line([(0,y-8),(2,y-17)],26,1);a.ball(2,y-18,3,2,BONE)
    if clip=='die':
        for j in range(3):
            x=-25+j*13+n*.5;yy=max(6,42-j*3-n*5)
            a.poly([(x-2,yy),(x+2,yy+4),(x+3,yy+1),(x,yy-2)],52+j%2)
    return a


def troll(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    y=35+bob*.4-fall*15
    for sg in (-1,1):
        foot=(sg*(11+fall*7)+stride*sg,5+max(0,stride*sg)*(1-fall))
        a.limb([(sg*10,y-7),(sg*(12+fall*6),17-fall*8),foot],GREEN,8)
        a.ball(*foot,9,4,GREEN)
    a.poly([(-16,y-2),(16,y-2),(19,y-14),(-18,y-14)],25)
    a.ball(0,y,22,20,GREEN);a.ball(-8,y+10,9,5,GREEN[1:])
    for sg in (-1,1):
        a.ball(sg*18,y+10,10,8,GREEN)
        hand=(sg*(29+fall*4),24-fall*15+(max(0,lunge)*3 if sg>0 else bob))
        a.limb([(sg*18,y+11),(sg*25,y-1),hand],GREEN,7)
        a.ball(*hand,8,7,GREEN)
        if sg>0:
            # Club pivots and lands as a rigid length of wood.
            angle=1.1+lunge*.14-fall*1.1
            end=(hand[0]-math.cos(angle)*20,hand[1]+math.sin(angle)*20)
            a.limb([hand,end],BROWN,7);a.ball(*end,9,6,BROWN)
    hx=-fall*10;hy=57+bob*.4-fall*36
    a.ball(hx,hy,16,14,GREEN);a.ball(hx-6,hy+7,8,3,GREEN[1:])
    a.ball(hx+1,hy+11,14,4,GREEN[:4]);a.face(hx,hy,clip,n,1)
    tusk(a,hx+5,hy-9);tusk(a,hx-6,hy-9)
    # Living moss and mushroom follow the head; death wilts their stems.
    a.limb([(hx-7,hy+12),(hx-9-fall*4,hy+23-fall*7)],GREEN,2)
    for j in range(3):a.ball(hx-12+j*4,hy+23+3*(j%2)-fall*(7+j),3,2.5,GREEN)
    a.limb([(hx+7,hy+11),(hx+8+fall*5,hy+19-fall*9)],BONE,2)
    a.ball(hx+8+fall*5,hy+20-fall*9,6,3,RED);a.ellipse(hx+7+fall*5,hy+21-fall*9,1.5,1,3)
    return a


def weaver(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=45+recoil)
    y=38+bob*.5-fall*24
    hem=5+abs(stride)*.3
    # Cloth drapes into folds; the head and hands fall into the settling robe.
    a.poly([(-13,y+13),(13,y+13),(25+fall*6,hem),(13,hem+2),(3,hem),(-10,hem+2),(-25-fall*5,hem)],15)
    a.poly([(-11,y+11),(-4,y+8),(-7,hem+2),(-22-fall*4,hem+3)],17)
    a.poly([(5,y+10),(11,y+9),(19+fall*3,hem+3),(8,hem+1)],16)
    for sg in (-1,1):a.line([(sg*8,y+4),(sg*14,hem+3)],18,1)
    hx=fall*8;hy=62+bob*.5-fall*40
    a.ball(hx,hy,15,13,PURPLE)
    a.poly([(hx-13,hy+4),(hx-7,hy+23),(hx+3,hy+14),(hx+13,hy+3)],16)
    a.ball(hx,hy-1,11,9,PURPLE[:2]);a.face(hx,hy-1,clip,n,.85)
    a.line([(hx-13,hy+6),(hx+11,hy+7)],28,2)
    hands=[]
    for sg in (-1,1):
        h=(sg*(22+fall*7)+lunge*.6,37+math.sin(n*.8+sg)*2-fall*28)
        a.limb([(sg*11,y+11),(sg*18,y+4),h],PURPLE,5);a.ball(*h,5,4,BONE);hands.append(h)
    # Golden thread unravels and drops as separate strands, not a shrinking blob.
    left,right=hands
    for j in range(4 if clip!='die' else max(0,6-n)):
        a.line([left,(-4+j*4,24-fall*17-j*2),right],27+j%2,1)
    if clip=='die' and n>=2:
        for j in range(4):
            x=-22+j*14;y2=max(4,42-j*3-n*4)
            a.line([(x,y2),(x+4,y2-3),(x+7,y2-1)],28,1)
    # Drop spindle rotates independently and settles beside the robe.
    h=right;angle=.8-fall*1.8
    end=(h[0]+math.sin(angle)*10,h[1]-math.cos(angle)*10)
    a.line([h,end],26,2);a.ball(*end,5,3,GOLD)
    return a


def hrungnir(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    # Staged giant failure: rune fades, blocks separate, head and shoulders settle.
    slump=max(0,(fall-.12)/.88)
    a=Painter(cx=46+recoil)
    y=36+bob*.3-slump*19
    for sg in (-1,1):
        foot=(sg*(12+slump*9)+stride*sg,5+max(0,stride*sg)*(1-slump))
        a.limb([(sg*11,y-6),(sg*(15+slump*6),19-slump*8),foot],PLATE,9)
        a.ball(*foot,10,5,PLATE)
    a.ball(0,y,22,20,PLATE);a.ball(-6,y+11,8,5,PLATE[1:])
    a.poly([(-9,y+6),(0,y+13),(10,y+5),(0,y-10)],21 if n<4 or clip!='die' else 10)
    for sg in (-1,1):
        lift=max(0,lunge)*3 if sg>0 else bob
        hand=(sg*(29+slump*5),28+lift*(1-slump)-slump*17)
        a.limb([(sg*19,y+11),(sg*(27+slump*4),y),hand],PLATE,9)
        a.ball(*hand,10,9,PLATE);a.ball(sg*(19+slump*7),y+15-slump*6,11,8,PLATE)
        a.poly([(sg*19-4,y+20),(sg*19,y+31),(sg*19+4,y+20)],22)
        a.line([(sg*19,y+21),(sg*19,y+28)],24,1)
    hx=slump*11;hy=63+bob*.3-slump*42
    a.ball(hx,hy,16,14,PLATE);a.ball(hx-6,hy+8,7,3,PLATE[1:]);a.face(hx,hy,clip,n,.95)
    # Horned stone crown and electric beard identify the giant through the death.
    for sg in (-1,1):
        a.poly([(hx+sg*8,hy+10),(hx+sg*17,hy+19),(hx+sg*16,hy+7)],12)
        a.poly([(hx+sg*9,hy+10),(hx+sg*16,hy+17),(hx+sg*14,hy+9)],14)
    a.poly([(hx-3,hy+12),(hx,hy+23),(hx+4,hy+12)],22)
    for j in range(max(0,5-n) if clip=='die' else 5):
        x=hx-9+j*4
        a.line([(x,hy-7),(x-2,hy-13),(x+2,hy-12),(x,hy-19-j%2*3)],23+j%2,2)
    if clip=='die':
        a.line([(-9,y+14),(-4,y+8),(-9,y+3),(2,y-7)],10,2)
        if n>=2:
            for j in range(5):
                x=-26+j*13+(n-2)*(.6 if j%2 else -.6);yy=max(4,42-j%2*10-(n-2)*6)
                a.poly([(x-4,yy),(x-1,yy+5),(x+4,yy+3),(x+3,yy-3)],11+j%3)
        if n>=4:a.line([(hx-10,hy+7),(hx-3,hy+2),(hx-7,hy-5)],10,2)
    return a


DRAW=dict(boar=boar,crow=crow,troll=troll,weaver=weaver,ram=ram,oakhorn=oakhorn,hrungnir=hrungnir)
def frame(kind, clip, n):
    a = DRAW[kind](clip,n)
    arr = np.array(a.im)
    if clip=='hurt' and n==0:
        arr[arr>0]=3
    assert arr.any(), (kind,clip,n,'empty')
    assert not (arr[0].any() or arr[-1].any() or arr[:,0].any() or arr[:,-1].any()), (kind,clip,n,'border')
    return arr


def rgba(grid, palette=PALETTE):
    return old.rgba(grid,palette)


def frames(kind):
    return {clip:np.array([frame(kind,clip,n) for n in range(count)])
            for clip,(_,count) in CLIPS.items()}


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    existing = {s['name']:s['sprite_id'] for s in old.api('list')['sprites']}
    # Validate every kind before saving any source.
    data = {kind:frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source',kind,saved[kind],flush=True)
            continue
        name = PREFIX+kind+'_all'
        assert name not in existing, 'Unregistered source already exists: '+name
        np.savez_compressed(ROOT/f'scripts/wyrd_slime_v1_{kind}_raw.npz',**data[kind])
        sid=old.api('create',dict(name=name,width=W,height=H,frames=34,layers=1,fps=10,
            palette=PALETTE,persist=True,ops=[dict(op='set_layer',layer=0,name=kind)]))['sprite_id']
        print('Created native source',kind,sid,flush=True)
        offset=0
        for clip,grids in data[kind].items():
            for n,grid in enumerate(grids):
                old.api('draw',dict(sprite_id=sid,frame=offset+n,
                    ops=[dict(op='grid',rows=grid.tolist(),x=0,y=0,layer=0)]))
            offset+=len(grids)
        saved[kind]=sid
        REGISTRY.write_text(json.dumps(saved,indent=2)+'\n')
        print(kind,sid,offset,'frames saved',flush=True)



def repair_legs():
    """Create three corrected sources; retain the earlier candidate IDs for rollback."""
    history_path=ROOT/'scripts/wyrd_slime_leg_sources.txt'
    saved=json.loads(REGISTRY.read_text())
    history=(json.loads(history_path.read_text()) if history_path.exists() else
             dict(previous={k:saved[k] for k in ('boar','ram','oakhorn')},corrected={}))
    data={kind:frames(kind) for kind in ('boar','ram','oakhorn')}
    for kind in data:
        if kind in history['corrected']:
            assert saved[kind]==history['corrected'][kind]
            print('Preserving corrected leg source',kind,saved[kind],flush=True)
            continue
        sid=old.api('create',dict(name=PREFIX+kind+'_anatomical_legs_all',width=W,height=H,
            frames=34,layers=1,fps=10,palette=PALETTE,persist=True,
            ops=[dict(op='set_layer',layer=0,name=kind)]))['sprite_id']
        offset=0
        for clip,grids in data[kind].items():
            for n,grid in enumerate(grids):
                old.api('draw',dict(sprite_id=sid,frame=offset+n,
                    ops=[dict(op='grid',rows=grid.tolist(),x=0,y=0,layer=0)]))
            offset+=len(grids)
        history['corrected'][kind]=sid
        history_path.write_text(json.dumps(history,indent=2)+'\n')
        saved[kind]=sid
        REGISTRY.write_text(json.dumps(saved,indent=2)+'\n')
        np.savez_compressed(ROOT/f'scripts/wyrd_slime_v1_{kind}_raw.npz',**data[kind])
        print(kind,sid,'34 corrected leg frames saved',flush=True)


def export():
    saved=json.loads(REGISTRY.read_text())
    assert set(saved)==set(KINDS)
    meta=dict(frame=[W,H],anchor=[AX,AY],kinds=KINDS,clips={},sprites=saved,
              tops={},artStyle='greenmeadow-slime')
    proof={}
    # Read and validate all saved editor sources before replacing candidate files.
    atlases={}
    for kind in KINDS:
        sp=old.api('get?sprite_id='+saved[kind])['sprite']
        assert (sp['width'],sp['height'],len(sp['frames']))==(W,H,34)
        atlas=Image.new('RGBA',(8*W,5*H));offset=0;rows=[]
        for row,(clip,(fps,count)) in enumerate(CLIPS.items()):
            meta['clips'][clip]=dict(fps=fps,n=count,row=row,editorStart=offset)
            for n in range(count):
                cel=sp['frames'][offset+n]['cels'][0]
                if 'rle' in cel:
                    runs=cel['rle'];grid=np.repeat(np.array(runs[1::2],dtype=np.uint8),runs[0::2]).reshape(H,W)
                else:
                    grid=np.array(cel['grid'],dtype=np.uint8)
                im=rgba(grid,sp['palette']);bounds=im.getbbox()
                assert bounds and min(bounds[:2])>0 and max(bounds[2:])<96
                atlas.alpha_composite(im,(n*W,row*H))
                rows.append(dict(clip=clip,n=n,sha256=hashlib.sha256(im.tobytes()).hexdigest(),bounds=bounds))
            offset+=count
        meta['tops'][kind]=int(AY-min(r['bounds'][1] for r in rows if r['clip']=='idle'))
        atlases[kind]=atlas
        proof[kind]=dict(source=saved[kind],frames=rows)
    for kind,atlas in atlases.items():
        dest=ASSETS/f'wyrd_{kind}.png';atlas.save(dest,optimize=True)
        proof[kind]['atlasSha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'wyrd.txt').write_text(json.dumps(meta,indent=2)+'\n')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('Exported 238 saved PixelFlow frames and derived health-bar tops.',flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames, not drawers."""
    meta=json.loads((ASSETS/'wyrd.txt').read_text())
    saved=json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind]==saved[kind]
        sp=old.api('get?sprite_id='+saved[kind])['sprite']
        atlas=Image.open(ASSETS/f'wyrd_{kind}.png').convert('RGBA');offset=0
        for row,(clip,(_,count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cel=sp['frames'][offset+n]['cels'][0]
                if 'rle' in cel:
                    runs=cel['rle'];grid=np.repeat(np.array(runs[1::2],dtype=np.uint8),runs[0::2]).reshape(H,W)
                else:
                    grid=np.array(cel['grid'],dtype=np.uint8)
                cell=atlas.crop((n*W,row*H,(n+1)*W,(row+1)*H))
                assert cell.tobytes()==rgba(grid,sp['palette']).tobytes(),(kind,clip,n,'editor mismatch')
            offset+=count
        print(kind,'34 saved editor frames equal exported atlas',flush=True)


def preview():
    OUT.mkdir(parents=True,exist_ok=True)
    overview=Image.new('RGB',(len(KINDS)*240,5*218),'#344b40');d=ImageDraw.Draw(overview)
    for col,kind in enumerate(KINDS):
        data=frames(kind)
        sheet=Image.new('RGB',(8*192,5*218),'#344b40');sd=ImageDraw.Draw(sheet)
        for row,(clip,grids) in enumerate(data.items()):
            for n,grid in enumerate(grids):
                im=rgba(grid).resize((192,192),Image.Resampling.NEAREST)
                sheet.paste(im,(n*192,row*218),im)
                sd.text((n*192+8,row*218+194),f'{clip} {n}',fill='white')
            im=rgba(grids[0 if clip!='die' else 7]).resize((192,192),Image.Resampling.NEAREST)
            overview.paste(im,(col*240+20,row*218),im)
            d.text((col*240+20,row*218+194),f'{NAMES[kind]} / {clip}',fill='white')
        sheet.save(OUT/f'preview-{kind}.png')
    overview.save(OUT/'preview.png');print(OUT/'preview.png')


if __name__=='__main__':
    {'preview':preview,'build':build,'legs':repair_legs,'export':export,'verify':verify}[sys.argv[1] if len(sys.argv)>1 else 'preview']()
