#!/usr/bin/env python3
"""Undervault slime-style PixelFlow art: preview | build | export.

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
OUT = ROOT/'test-results/vault-slime'
REGISTRY = ROOT/'scripts/vault_slime_sources.txt'
PREFIX = 'valhallasc_vault_slime_style_'
KINDS = ['thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking']
NAMES = dict(thrall='Vault Thrall', archer='Bone Archer', acolyte='Hollow Acolyte',
             gatewarden='Hrolf Bonegate', choir='Valka, the Hollow Choir',
             colossus='Ironwake', hollowking='Haldor, the Hollow King')
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



def mix(a,b,t):
    return a+(b-a)*t


def skull(a,x,y,clip,n,size=1):
    # Oversized glossy bone dome, separate jaw and four readable teeth.
    a.ball(x+2*size,y-10*size,9*size,4*size,BONE)
    a.ball(x,y,17*size,15*size,BONE)
    a.ball(x-5*size,y+7*size,7*size,3*size,BONE[1:])
    a.face(x,y-1*size,clip,n,size)
    a.poly([(x-1,y-7*size),(x+2,y-5*size),(x+4,y-8*size)],1)
    for j in range(4):
        tx=x+(-4+j*3)*size
        a.line([(tx,y-10*size),(tx,y-13*size)],5)


def ribs(a,y,fall=0,spread=1):
    a.limb([(0,y-9),(0,y+11)],BONE,4)
    for j in range(3):
        yy=y+8-j*6
        for sign in (-1,1):
            dx=sign*(3+fall*(5+j*3))*spread
            a.limb([(dx,yy),(dx+sign*7,yy-2-fall*j*2),
                    (dx+sign*8,yy-4-fall*j*2)],BONE,3)
    a.ball(0,y-11,8,4,BONE)


def legs(a,stride,fall,armour=False,spread=0):
    ramp=PLATE if armour else BONE
    for sign in (-1,1):
        step=stride*sign*(1-fall)
        foot=(sign*(8+fall*spread)+step,5+max(0,step))
        a.limb([(sign*6,25-fall*13),(sign*(8+fall*spread*.7),15-fall*8),foot],ramp,5 if armour else 3)
        a.ball(*foot,8 if armour else 6,4 if armour else 3,ramp)


def shield(a,x,y,fall=0,large=False):
    r=12 if large else 10
    a.ball(x,y,r,r+1,PLATE)
    a.ball(x,y,r-3,r-2,RED if large else GOLD)
    a.line([(x-r+3,y),(x+r-3,y)],PLATE[0],2)
    a.line([(x,y-r+3),(x,y+r-3)],PLATE[0],2)
    a.ball(x,y,3,3,PLATE)
    if fall>.5:a.line([(x-5,y+7),(x-2,y+1),(x+5,y-5)],1)


def sword(a,hand,angle,length=25,royal=False):
    dx,dy=math.cos(angle),math.sin(angle)
    tip=(hand[0]+dx*length,hand[1]+dy*length)
    a.line([(hand[0]-dx*5,hand[1]-dy*5),tip],PLATE[0],6)
    a.line([hand,tip],GREEN[3] if royal else PLATE[3],3)
    a.line([(hand[0]-5*dy,hand[1]+5*dx),(hand[0]+5*dy,hand[1]-5*dx)],GOLD[2],3)
    a.ball(*hand,4,4,BONE)


def thrall(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    legs(a,stride,fall,spread=10)
    y=34+bob*.35-fall*22
    a.poly([(-11,25-fall*13),(11,25-fall*13),(15,13),(4,17),(-3,12),(-13,15)],31)
    ribs(a,y,fall)
    sx,sy=-24-fall*3,33-fall*24
    a.limb([(-9,y+7),(-19,y), (sx,sy)],BONE,3)
    shield(a,sx,sy,fall)
    hand=(21+max(0,lunge),32-lunge*1.2-fall*23)
    a.limb([(9,y+7),(15,y),hand],BONE,3)
    sword(a,hand,1.55-lunge*.18-fall*1.4,23)
    skull(a,1+fall*15,58+bob*.4-fall*46,clip,n,.95)
    if fall>.25:
        a.line([(-6+fall*15,63-fall*46),(1+fall*15,58-fall*46),(0+fall*15,53-fall*46)],5)
    return a


def archer(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=45+recoil)
    legs(a,stride,fall,spread=6)
    y=33+bob*.4-fall*21
    a.limb([(-12,y-4),(-18,y+16)],GOLD,6)
    for k in range(3):
        xx=-20+k*4-fall*8
        yy=y+19+fall*3
        a.line([(xx,yy-13),(xx+fall*8,yy+3)],8,1)
        a.poly([(xx-2,yy+3),(xx+1,yy+8),(xx+3,yy+3)],37)
    a.poly([(-10,y-8),(10,y-8),(13,11),(-14,13)],26)
    ribs(a,y,fall,spread=.8)
    hx=-fall*12;hy=57+bob*.4-fall*43
    a.ball(hx,hy+2,20,19,GOLD)
    a.poly([(hx-17,hy),(hx-24,hy-11),(hx-12,hy-8)],26)
    skull(a,hx+2,hy-2,clip,n,.86)
    a.line([(hx-16,hy+8),(hx+16,hy+8)],26,3)
    bx=24+max(0,lunge)*.5;by=38-fall*22
    # Rigid bow rotates flat and drops; the string relaxes after release.
    angle=fall*1.1;c,s=math.cos(angle),math.sin(angle)
    def bowp(x,y):return (bx+x*c-y*s,by+x*s+y*c)
    top,mid,bot=bowp(0,22),bowp(8,0),bowp(0,-22)
    a.limb([top,mid,bot],GOLD,3)
    draw=[2,6,10,0,0,0,0,0][n] if clip=='attack' else 1
    nock=bowp(-draw,0)
    a.line([top,nock,bot],8,1)
    hand=bowp(4,0)
    a.limb([(8,y+6),(15,y+8),hand],BONE,3)
    a.limb([(-7,y+5),(-11,y+1),nock],BONE,3)
    if clip=='attack' and n in (3,4,5):
        tx=30+(n-3)*3
        a.line([(tx-15,by),(tx+5,by)],8,1)
        a.poly([(tx+5,by),(tx+1,by+2),(tx+1,by-2)],13)
    if fall>.3:
        for j in range(3):
            a.limb([(-25+j*9,5+j%2*3),(-15+j*9,7+j%2*3)],BONE,2)
    return a


def acolyte(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    if clip=='walk':bob=[0,2,3,2,0,-1,-2,-1][n]
    a=Painter(cx=44+recoil)
    y=31+bob*.4-fall*19
    # Cloth drapes and settles while the skull and staff remain solid.
    sway=stride*.3
    a.poly([(-10,y+12),(10,y+12),(17+sway,8),(21,4),(9,6),(0,3),(-12,6),(-19+sway,4)],15)
    a.poly([(-8,y+10),(7,y+10),(13,7),(-12,7)],17)
    a.poly([(-7,y+10),(-2,y+12),(-6,9),(-13,7)],18)
    for x in (-9,0,9):a.line([(x,y),(x*1.4,8)],16,2)
    a.line([(-11,y-2),(11,y-2)],27,2)
    hx=1-fall*11;hy=57+bob*.5-fall*35
    a.ball(hx,hy+2,21,20,PURPLE)
    skull(a,hx+2,hy-1,clip,n,.88)
    a.line([(hx-16,hy+10),(hx+16,hy+10)],16,3)
    hand=(23+max(0,lunge),34-fall*25)
    a.limb([(9,y+6),(17,y+1),hand],PURPLE,5)
    a.ball(*hand,4,4,BONE)
    top=(mix(25,37,fall)-max(0,-lunge)*.7,mix(70,14,fall))
    bottom=(mix(22,3,fall),5)
    a.line([bottom,top],25,5);a.line([bottom,top],27,2)
    a.ball(*top,7,8,GOLD)
    if fall<.9:
        a.ball(top[0],top[1]+1,5,6,PURPLE)
        a.ellipse(top[0]-1,top[1]+3,2,2,19)
    if clip=='attack' and n in (3,4,5):
        a.ball(37,top[1]-4,5,5,PURPLE)
    if clip=='die':
        for j in range(max(0,7-n)):
            a.ellipse(-20+j*8,35+n*3+j%2*4,1,1,18)
        if n>=3:a.limb([(9,7),(21,5)],BONE,3)
    return a


def axe(a,hand,angle):
    dx,dy=math.cos(angle),math.sin(angle)
    top=(hand[0]+dx*24,hand[1]+dy*24)
    a.line([(hand[0]-dx*10,hand[1]-dy*10),top],25,5)
    a.line([(hand[0]-dx*10,hand[1]-dy*10),top],27,2)
    def p(x,y):return (top[0]+x*dx-y*dy,top[1]+x*dy+y*dx)
    a.poly([p(-5,1),p(-8,10),p(3,12),p(7,4),p(2,0)],10)
    a.poly([p(-4,2),p(-6,8),p(2,10),p(5,4)],13)
    a.ball(*hand,4,4,BONE)


def gatewarden(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    legs(a,stride,fall,armour=True,spread=10)
    y=36+bob*.3-fall*22
    a.poly([(-13,y),(13,y),(19,8),(0,13),(-17,7)],36)
    a.ball(0,y,17,16,PLATE)
    a.ball(-5,y+7,6,3,PLATE[1:])
    a.line([(-12,y-8),(12,y-8)],27,3)
    for sign in (-1,1):a.ball(sign*(17+fall*5),y+8-fall*3,9,8,PLATE)
    sx,sy=-26-fall*2,35-fall*23
    a.limb([(-13,y+5),(-22,y), (sx,sy)],PLATE,5)
    shield(a,sx,sy,fall,True)
    hx=2+fall*13;hy=62+bob*.4-fall*43
    skull(a,hx,hy-2,clip,n,.95)
    a.ball(hx,hy+8,18,9,PLATE)
    a.line([(hx-17,hy+4),(hx+17,hy+4)],27,2)
    for sign in (-1,1):
        a.limb([(hx+sign*14,hy+10),(hx+sign*23,hy+15-fall*6),(hx+sign*22,hy+23-fall*10)],BONE,4)
    hand=(24+max(0,lunge)-fall*17,34-lunge*1.5-fall*21)
    a.limb([(13,y+6),(22,y+1),hand],PLATE,6)
    axe(a,hand,1.6-lunge*.18-fall*1.8)
    if n>=2 and clip=='die':
        a.line([(-7,y+11),(0,y+3),(-3,y-6)],10,2)
        a.limb([(-12,9),(-21,5)],BONE,3)
    return a


def choir(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    floaty=math.sin(n*math.pi/3)*2 if clip in ('idle','walk') else 0
    y=36+floaty-fall*22
    # Veil and gown remain cloth; spectral face separates into rising ribbons.
    sway=stride*.5
    hem=8+floaty*(1-fall)
    a.poly([(-12,y+14),(12,y+14),(20+sway,hem+3),(13,hem),(6,hem+4),(-3,hem),(-12,hem+4),(-21+sway,hem)],20)
    a.poly([(-9,y+11),(7,y+13),(13,hem+4),(-12,hem+3)],22)
    a.poly([(-8,y+10),(-3,y+10),(-7,hem+6),(-14,hem+4)],23)
    for sign in (-1,1):
        hand=(sign*(25+max(0,lunge)*.7),y+5+max(0,lunge)*2-fall*6)
        a.limb([(sign*10,y+8),(sign*21,y+3),hand],TEAL,6)
        a.ball(*hand,5,5,TEAL)
    hy=61+floaty+fall*2
    if fall<.85:
        a.ball(0,hy+4,21,20,TEAL)
        skull(a,1,hy,clip,n,.9)
        a.poly([(-19,hy+7),(-18,hy-18),(-11,hy-12),(-12,hy+13)],23)
        a.poly([(17,hy+13),(20,hy-17),(13,hy-12),(12,hy+10)],23)
        # Silver diadem leaves the eye line clear.
        a.line([(-16,hy+14),(16,hy+14)],13,3)
        for x in (-10,0,10):a.poly([(x-3,hy+14),(x,hy+21),(x+3,hy+14)],14)
        if clip=='attack':
            a.ellipse(2,hy-9,3,3+max(0,lunge)*.6,15)
    if clip=='die':
        # Progressive gaps dissolve the spirit, not the solid robe below it.
        for j in range(n):
            yy=round(AY-(hy-17+j*6))
            a.d.rectangle((20,yy,75,yy+1+int(n>3)),fill=0)
        for j in range(max(0,7-n)):
            x=-24+j*8;y2=55+n*3+(j%2)*7
            a.line([(x,y2),(x+3,y2+4)],23,2)
        if n>=5:
            a.line([(-15,18),(-8,13),(1,15),(11,11)],23,3)
    else:
        for j in range(2 if clip!='attack' else 3):
            x=-30+j*28;y2=55+(n*3+j*11)%21
            a.line([(x,y2),(x,y2+7),(x+4,y2+6)],23,1)
            a.ellipse(x-2,y2,2,1,24)
    return a


def colossus(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    y=39+bob*.3-fall*21
    # Fixed-size solid components: cracks grow, then blocks separate and fall.
    for sign in (-1,1):
        step=stride*sign
        foot=(sign*(12+fall*7)+step*(1-fall),7+max(0,step)*(1-fall))
        a.limb([(sign*10,y-9),(sign*(14+fall*5),18-fall*7),foot],PLATE,10)
        a.ball(*foot,11,6,PLATE)
    a.ball(0,y,23,20,PLATE)
    a.ball(-8,y+10,8,5,PLATE[1:])
    a.ball(1,y,10,12,PLATE[:2])
    a.ball(1,y+1,6,8,TEAL if fall<.75 else PLATE[:3])
    if fall<.7:a.line([(-2,y+3),(3,y+3),(0,y-3)],24,2)
    for sign in (-1,1):
        hx=sign*(30+fall*4)
        lift=[0,8,15,23,3,-2,-1,0][n] if clip=='attack' and sign>0 else bob
        hand=(hx,26+lift*(1-fall)-fall*15)
        a.limb([(sign*19,y+8),(sign*(27+fall*4),y-3),hand],PLATE,11)
        a.ball(*hand,10,10,PLATE)
        a.ball(sign*(20+fall*6),y+13,11,10,PLATE)
        for k in range(2):a.ellipse(sign*20+k*2,y+16-k*5,1,1,13)
    hx=-fall*10;hy=65+bob*.3-fall*43
    a.ball(hx,hy,17,15,PLATE)
    a.ball(hx-5,hy+7,6,3,PLATE[1:])
    a.face(hx,hy,clip,n,.9)
    a.poly([(hx-9,hy+12),(hx-7,hy+20),(hx-2,hy+13)],12)
    if clip=='die':
        a.line([(-5,y+17),(-1,y+9),(-6,y+1),(4,y-10)],10,2)
        if n>=2:
            for j in range(4):
                x=-22+j*14+(n-2)*(.7 if j%2 else -.7)
                yy=max(5,35+j%2*9-(n-2)*6)
                a.poly([(x-3,yy+4),(x+4,yy+2),(x+3,yy-3),(x-4,yy-2)],12+j%2)
        if n>=5:
            a.line([(hx-11,hy+5),(hx-2,hy+1),(hx-6,hy-7)],10,2)
    return a


def hollowking(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    # Crown failure precedes the skeleton: a delayed, theatrical bone cascade.
    bodyfall=max(0,(fall-.12)/.88)
    a=Painter(cx=46+recoil)
    y=36+bob*.3-bodyfall*25
    a.poly([(-16,y+15),(15,y+14),(24+bodyfall*7,6),(10,9),(0,4),(-14,8),(-27-bodyfall*4,5)],15)
    a.poly([(-14,y+13),(-8,y+11),(-17,9),(-25,7)],17)
    a.line([(-16,y+14),(-26-bodyfall*4,6)],27,2)
    legs(a,stride,bodyfall,armour=True,spread=12)
    ribs(a,y,bodyfall,spread=1.2)
    for sign in (-1,1):
        a.ball(sign*(17+bodyfall*5),y+9-bodyfall*5,9,8,GREEN)
        a.line([(sign*12,y+11),(sign*18,y+13)],28,2)
    hx=2+bodyfall*14;hy=61+bob*.4-bodyfall*44
    skull(a,hx,hy,clip,n,1.04)
    # The crown is a rigid object; after frame2 it tumbles away from the skull.
    cx=mix(hx,-21,fall);cy=mix(hy+6,14,fall)
    tilt=-fall*1.2;c,s=math.cos(tilt),math.sin(tilt)
    def cp(x,y):return (cx+x*c-y*s,cy+x*s+y*c)
    a.poly([cp(-15,0),cp(-17,12),cp(-8,7),cp(0,16),cp(8,7),cp(17,12),cp(15,0)],25)
    a.poly([cp(-13,2),cp(-14,10),cp(-7,5),cp(0,13),cp(7,5),cp(14,10),cp(13,2)],28)
    gem=cp(0,5);a.ball(*gem,3,3,GREEN)
    hand=(24+max(0,lunge)-bodyfall*16,33-lunge*1.3-bodyfall*18)
    a.limb([(14,y+6),(21,y+1),hand],GREEN,6)
    sword(a,hand,1.65-lunge*.2-bodyfall*1.9,26,True)
    other=(-25-bodyfall*3,30-bodyfall*21)
    a.limb([(-14,y+7),(-23,y),other],GREEN,5);a.ball(*other,5,5,BONE)
    if clip=='die':
        for j in range(max(0,7-n)):
            a.poly([(-18+j*6,67-n*4),(-17+j*6,71-n*4),(-14+j*6,66-n*4)],32)
        if n>=3:
            for j in range(3):a.limb([(-13+j*12,10-j%2*3),(-20+j*12,6)],BONE,3)
    return a


DRAW=dict(thrall=thrall,archer=archer,acolyte=acolyte,gatewarden=gatewarden,
          choir=choir,colossus=colossus,hollowking=hollowking)


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
        np.savez_compressed(ROOT/f'scripts/vault_slime_{kind}_raw.npz',**data[kind])
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
        dest=ASSETS/f'vault_{kind}.png';atlas.save(dest,optimize=True)
        proof[kind]['atlasSha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'vault.txt').write_text(json.dumps(meta,indent=2)+'\n')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('Exported 238 saved PixelFlow frames and derived health-bar tops.',flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames, not drawers."""
    meta=json.loads((ASSETS/'vault.txt').read_text())
    saved=json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind]==saved[kind]
        sp=old.api('get?sprite_id='+saved[kind])['sprite']
        atlas=Image.open(ASSETS/f'vault_{kind}.png').convert('RGBA');offset=0
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
    {'preview':preview,'build':build,'export':export,'verify':verify}[sys.argv[1] if len(sys.argv)>1 else 'preview']()
