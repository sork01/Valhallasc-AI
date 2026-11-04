#!/usr/bin/env python3
"""The Prismwaste: six native PixelFlow slime-style sources, per-kind frames and fitting motion.

preview | extents | build | refresh <kinds> | export | verify
All attacks have eight distinct wind-up/strike/recovery poses. Rigid materials retain their shape;
four jackal paws are separately planted; flying harrier and sunshard settle onto the ground on death.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
from astral_slime_redraw import (
    Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BLUSH,
    PLATE, TEAL, GOLD, FUR, BLUE, BROWN, PINK, PEARL, VIOLET, AMBER,
    AZURE, SLATE, mix, mixp, rot, sm, bez, taper, foot, spark, motion, atk, arm_ik, biped_legs,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/prism-slime'
REGISTRY = ROOT / 'scripts/prism_slime_sources.txt'
MANIFEST = ASSETS / 'prism.txt'
PREFIX = 'valhallasc_prism_slime_style_'
KINDS = ['miragejackal', 'shardscarab', 'glassharrier', 'prismsentinel', 'mirrorqueen', 'sunshard']
NAMES = dict(zip(KINDS, ['Mirage Jackal', 'Shard Scarab', 'Glass Harrier', 'Prism Sentinel', 'Mirror Queen', 'Sunshard']))
W = H = 96
AX, AY = 48, 90
KIND_FRAMES = dict(
    miragejackal=(152, 104, 60, 98),
    shardscarab=(148, 108, 62, 102),
    glassharrier=(160, 124, 66, 118),
    prismsentinel=(168, 136, 62, 130),
    mirrorqueen=(164, 140, 62, 134),
    sunshard=(160, 140, 64, 134),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('glassharrier', 'sunshard')
PALETTE = PALETTE[:] + ['#583d4a', '#926451', '#c99771', '#efc29b', '#ffe6bd']
SAND = list(range(len(PALETTE)-5, len(PALETTE)))
RAINBOW = [PINK[3], GOLD[3], TEAL[3], VIOLET[3]]


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax - 2 + dx


def curves(clip, n):
    """Explicit animation beats: ready, anticipate, wind-up, release, impact, follow, recoil, recover."""
    wind = [0, .48, 1, .35, 0, 0, .08, 0][n] if clip == 'attack' else 0
    strike = [0, 0, 0, .50, 1, .72, .28, 0][n] if clip == 'attack' else 0
    dead = sm(n / 7) if clip == 'die' else 0
    phase = n * math.pi / (3 if clip == 'idle' else 4)
    bob = math.sin(phase) * (1.2 if clip == 'idle' else 2 if clip == 'walk' else 0)
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    return wind, strike, dead, phase, bob, recoil


def diamond(a, x, y, rx, ry, ramp):
    a.poly([(x-rx,y),(x,y+ry),(x+rx,y),(x,y-ry)], ramp[2], outline=ramp[0])
    a.poly([(x-rx+1,y),(x,y+ry-1),(x,y)], ramp[3])
    a.line([(x,y+ry-2),(x,y-ry+2)], ramp[-1])


def miragejackal(clip, n):
    w, st, d, ph, bob, recoil = curves(clip,n)
    a = Painter('miragejackal', recoil + st*13-w*5)
    by = 26 + bob*.55 + w*5 - d*12
    # Four separate jointed legs, far paws offset by 8 px from near paws.
    for far in (True, False):
        for side in (-1, 1):
            hipx = -19 if side<0 else 13
            fx = hipx + (8 if far else 0)
            swing = math.sin(ph+(math.pi if far != (side<0) else 0)) if clip=='walk' else 0
            lift = max(0,swing)*4*(1-d)
            fx += swing*3 + st*(3 if side>0 else -2)
            hip=(hipx,by-3)
            knee=(mix(hipx+(5 if side<0 else -2),fx+side*8,d), mix(15+bob*.2,8,d)+lift*.4)
            ankle=(mix(fx,fx+side*6,d),5+lift)
            a.limb([hip,knee,ankle], SAND if not far else BROWN, 4)
            foot(a, ankle[0],lift,3.5,3,SAND if not far else BROWN)
        if far:
            # Tail sweeps back into a rigid axial crystal; no hook or dangling vertical gem.
            tx,ty=-39-d*2,mix(by+20+w*3,4,d)
            tail=bez((-24,by+3),(-34,mix(by+12+w*2,9,d)),(tx,ty),12)
            taper(a,tail,SAND,7,3)
            # One fixed faceted prism rotates as a whole only when the fallen tail settles.
            angle=mix(2.15,math.pi,d)
            ux,uy=math.cos(angle),math.sin(angle)
            vx,vy=-uy,ux
            def crystal_point(length,width):
                return tx+ux*length+vx*width,ty+uy*length+vy*width
            base_left,base_right=crystal_point(-1,2.5),crystal_point(-1,-2.5)
            shoulder_left,shoulder_right=crystal_point(4,3.5),crystal_point(4,-3.5)
            tip=crystal_point(11,0)
            ridge=crystal_point(4,0)
            a.poly([base_left,shoulder_left,tip,shoulder_right,base_right],TEAL[2],outline=TEAL[0])
            a.poly([base_left,shoulder_left,tip,ridge],TEAL[4],outline=TEAL[0])
            a.poly([base_right,shoulder_right,tip,ridge],TEAL[1],outline=TEAL[0])
            a.line([crystal_point(0,0),ridge,tip],TEAL[3],1)
            a.ball(-7,by,25,13,SAND,ang=-d*.20)
            a.ball(-4,by-5,17,6,PEARL)
            for k,x in enumerate((-20,-12,-4,4)):
                a.line([(x,by+11),(x-3,by+3)],RAINBOW[k],3)
    hx=23+st*12-w*6
    hy=mix(43+bob*.5+w*16-st*5,14,d)
    # Neck follows the head through anticipation and bite, so the head never detaches.
    a.limb([(10,by+4),(hx-5,hy-8),(hx,hy-2)], SAND, 13)
    # Ears fold to the side rather than disappearing on death.
    a.ball(hx,hy,13,12,SAND,ang=-d*.3)
    for off,height in ((-8,22),(2,25)):
        ex=hx+off
        a.poly([(ex-4,hy+7),(ex-5-d*8,hy+height*(1-d*.68)),(ex+5,hy+9)],SAND[2],outline=SAND[0])
        a.poly([(ex-1,hy+10),(ex-3-d*7,hy+(height-4)*(1-d*.58)),(ex+2,hy+11)],PINK[3])
    jaw=st*6
    a.limb([(hx+4,hy-2),(hx+6,hy-6-jaw),(hx+13,hy-7-jaw)],SAND,4)
    a.ball(hx+12,hy-7-jaw,9,4,PEARL)
    if st>.3:
        a.ellipse(hx+13,hy-5-jaw*.5,6,2+jaw*.4,OUTLINE)
    a.ball(hx+12,hy-2,10,5,SAND[1:])
    a.ellipse(hx+20,hy-1,3,2,OUTLINE)
    a.face(hx+2,hy+2,clip,n,.78,sep=5.1,mouth=False,pupil=TEAL[0])
    if st>.3:
        for xx in (hx+9,hx+16):
            a.poly([(xx-1,hy-5),(xx+2,hy-5),(xx+1,hy-9)],WHITE,outline=OUTLINE)
        spark(a,hx+28,hy-4,TEAL[4],4)
    return a


def shardscarab(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('shardscarab',recoil+st*8-w*3)
    by=24+bob*.45+w*11-d*7
    # Six legs retain rigid shell proportions; death lifts and curls the feet as the shell tips.
    for far in (True,False):
        for i,x in enumerate((-22,-4,15)):
            fx=x+(-9 if i==0 else 8 if i==2 else 0)+(5 if far else 0)
            swing=math.sin(ph+(i%2)*math.pi+(math.pi if far else 0)) if clip=='walk' else 0
            lift=max(0,swing)*4
            hip=(x,by-5)
            knee=(mix(fx-3,fx*.72,d),mix(12,by+9,d))
            end=(mix(fx,fx*.6,d),mix(3+lift,by+9-i*2,d))
            a.limb([hip,knee,end],VIOLET,3)
            if not d:
                foot(a,end[0],lift,3,2,VIOLET)
        if far:
            a.ball(-4,by,28,16,TEAL,ang=d*math.pi*.85)
            # Fan is connected to the actual carapace in every frame.
            for i,x in enumerate((-21,-10,1,12)):
                a.crystal(x,mix(by+10,4,d),3.5,mix(14+(i%3)*5+w*14,5,d),VIOLET,tilt=(i-1.5)*(3+w*5+d*8))
            a.line([(-5,by+14),(-5,by-10)],TEAL[0],2)
            for x in (-19,10):
                a.line([(x,by+8),(x+3,by-4)],TEAL[4],1)
            if d:
                a.line([(-18,by+8),(-8,by+2),(-12,by-4),(0,by-9)],OUTLINE,2)
    hx=22+st*13-w*2
    hy=by-2-d*2
    a.ball(hx,hy,12,10,VIOLET)
    for sg in (-1,1):
        pts=bez((hx+7,hy-5+sg*2),(hx+22,hy-5+sg*(5+st*4)),(hx+18,hy-11+sg*3),8)
        taper(a,pts,GOLD,4,1)
    a.face(hx,hy+1,clip,n,.78,sep=5,mouth=False,pupil=PINK[0])
    for i in range(3):
        a.crystal(hx-4+i*4,hy+7,1.8,6+(i==1)*3,GOLD)
    if st>.3:
        for k in range(3):
            diamond(a,hx+26+k*6,hy+8+(k%2)*8,2.5,5,VIOLET)
    if d>.15:
        for k in range(4):
            diamond(a,-26+k*14,mix(30,3+(k%2),d),3,3,TEAL)
    return a


def glassharrier(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('glassharrier',recoil+st*18-w*6)
    by=mix(52+bob+w*9-st*7,12,d)
    # Each feather is a connected, tapered shard. The wings bank high on anticipation, sweep down on strike.
    for far in (True,False):
        sh=(-6,by+6)
        flap=math.sin(ph)*.13 if clip in ('idle','walk') else 0
        angle=(2.35 if far else 2.05)+flap-w*.95+st*.75+d*.55
        ln=40 if far else 45
        for k in range(5):
            ang=angle+(k-2)*.14
            le=ln-abs(k-2)*4
            tip=(sh[0]+math.cos(ang)*le, max(4,sh[1]+math.sin(ang)*le*(1-d*.9)))
            mid=mixp(sh,tip,.55)
            px,py=-math.sin(ang)*4,math.cos(ang)*4
            a.poly([sh,(mid[0]+px,mid[1]+py),tip,(mid[0]-px,mid[1]-py)],AZURE[2 if k%2 else 3],outline=AZURE[0])
            a.line([sh,tip],AZURE[4],1)
        if far:
            for k in range(3):
                a.poly([(-12,by-4),(-30-k*3,max(3,by-16-k*3)),(-6,by-8)],VIOLET[2+k%2],outline=VIOLET[0])
            a.ball(0,by,16,12,VIOLET,ang=-st*.35+d*.35)
            a.ball(5,by-4,10,6,PEARL)
    hx=13+st*12-w*4
    hy=by+13+w*5-d*5
    a.limb([(7,by+5),(hx-5,hy-5),(hx,hy)],VIOLET,10)
    a.ball(hx,hy,12,11,VIOLET)
    a.face(hx+2,hy,clip,n,.75,sep=5,mouth=False,pupil=AZURE[0])
    a.poly([(hx+9,hy-1),(hx+24,hy-4),(hx+19,hy-11),(hx+16,hy-7),(hx+10,hy-6)],GOLD[3],outline=GOLD[0])
    a.poly([(hx+13,hy-7),(hx+18,hy-9-st*4),(hx+10,hy-9-st*3)],GOLD[2],outline=GOLD[0])
    for k in range(3):
        a.crystal(hx-7+k*5,hy+8,2,9+(k==1)*4,AZURE,tilt=-2)
    for sg in (-1,1):
        hip=(sg*5,by-7)
        ankle=(sg*6+st*22,mix(by-20+st*5,4,d))
        a.limb([hip,ankle],GOLD,2)
        for k in (-1,0,1):
            a.line([ankle,(ankle[0]+k*3+2,max(2,ankle[1]-4))],GOLD[0],2)
    if st>.3:
        for k in range(3):
            diamond(a,hx+25+k*6,max(13,hy-15+k*5),2,5,AZURE)
    if d>.1:
        for k in range(4):
            diamond(a,-29+k*14,mix(42,3,d),2,3,AZURE)
    return a


def prismsentinel(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('prismsentinel',recoil+st*7-w*2)
    by=39+bob*.5-d*24
    biped_legs(a,PLATE,ph,clip,10,27,7,4,6,st,w,d)
    # Kite shield braces behind the torso, then tips onto the floor.
    sx=-27-d*7
    sy=mix(37+bob,9,d)
    a.limb([(-12,by+6),(sx+5,sy)],PLATE,5)
    a.poly([(sx-10,sy+14*(1-d*.6)),(sx+10,sy+14*(1-d*.6)),(sx+9,sy-4),(sx, max(2,sy-17*(1-d))),(sx-9,sy-4)],PLATE[2],outline=PLATE[0])
    diamond(a,sx,sy,7,12*(1-d*.6),TEAL)
    for i,col in enumerate(RAINBOW):
        a.line([(sx-5+i*3,sy+7),(sx-3+i*3,sy-5)],col,1)
    a.ball(0,by,16,14,PLATE)
    a.poly([(-13,by-10),(13,by-10),(17,max(5,by-23)),(-17,max(5,by-23))],VIOLET[2],outline=VIOLET[0])
    diamond(a,0,by+1,5,8,TEAL)
    # Spear rotates as a rigid staff from high guard through draw-back to full forward thrust.
    hand=(mix(mix(21,9,w),35,st),mix(mix(39,66,w),41,st))
    if clip=='die': hand=mixp((21,39),(25,6),d)
    angle=mix(mix(1.42,1.95,w),.05,st)
    if clip=='die': angle=mix(1.42,.025,d)
    direction=(math.cos(angle),math.sin(angle))
    base=(hand[0]-direction[0]*28,max(2,hand[1]-direction[1]*28))
    tip=(hand[0]+direction[0]*35,max(5,hand[1]+direction[1]*35))
    a.line([base,tip],OUTLINE,5)
    a.line([base,tip],GOLD[2],3)
    a.poly([(tip[0]-direction[1]*4,tip[1]+direction[0]*4),
            (tip[0]+direction[0]*14,tip[1]+direction[1]*14),
            (tip[0]+direction[1]*4,tip[1]-direction[0]*4)],TEAL[3],outline=TEAL[0])
    a.line([tip,(tip[0]+direction[0]*11,tip[1]+direction[1]*11)],WHITE,1)
    sh=(12,by+9)
    elbow,hand2=arm_ik(sh,hand,17,17,1)
    # Staff hand stays on the staff; arm length follows reachable IK target.
    a.limb([sh,elbow,hand],PLATE,5)
    a.ball(*hand,5,4,GOLD)
    for sg in (-1,1):
        a.ball(sg*17,by+10,9,7,PLATE)
        a.crystal(sg*17,by+14,3,11*(1-d*.5),TEAL,tilt=sg*2)
    hx=d*13
    hy=mix(66+bob*.5,16,d)
    a.ball(hx,hy,15,13,PLATE)
    a.poly([(hx-12,hy+3),(hx+13,hy+3),(hx+13,hy-8),(hx-12,hy-8)],SLATE[0],outline=OUTLINE)
    a.face(hx+1,hy-1,clip,n,.84,sep=5.5,mouth=False,pupil=TEAL[0])
    for k in range(4):
        a.crystal(hx-8+k*5,hy+9,2.5,10+(k==1)*6,TEAL,tilt=k-1.5)
    a.line([(hx-12,hy-9),(hx+12,hy-9)],GOLD[3],2)
    if st>.3: spark(a,tip[0]+16,tip[1],WHITE,4)
    if d>.2: a.line([(-10,by+8),(0,by+3),(-3,by-7)],OUTLINE,2)
    return a


def mirrorqueen(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('mirrorqueen',recoil)
    by=mix(43+bob*.5,12,d)
    hx=2+st*3
    hy=mix(69+bob*.5+w*3,21,d)
    # Long hair and glossy violet gown retain their mass and gather into fabric folds on death.
    a.ball(hx-4,hy-8,18,22*(1-d*.4),VIOLET)
    hem=31+d*9
    a.poly([(-11,by+5),(11,by+5),(19,by-13),(hem,4),
            (hem-3,1),(15,3),(5,1),(-6,2),(-19,1),(-hem,3),(-18,by-13)],VIOLET[2],outline=VIOLET[0])
    for x in (-21,-11,0,11,21):
        a.poly([(x*.3,by+2),(x+4,4),(x-3,3)],VIOLET[3 if x<0 else 1],outline=VIOLET[0])
        diamond(a,x*.85,max(6,by*.38),2.5,4,PEARL)
    a.ball(0,by+3,12,9,VIOLET)
    a.line([(-11,by),(11,by)],GOLD[3],2)
    diamond(a,0,by+6,4,5,TEAL)
    # Orbiting mirror fragments gather overhead, flare forward, then all settle on death.
    for k in range(5):
        th=(0 if clip=='attack' and n==7 else ph)+k*2*math.pi/5
        ox=mix(math.cos(th)*33,-22+k*11,d)
        oy=mix(48+math.sin(th)*9+w*22,4,d)
        diamond(a,ox,oy,3,5 if d<.8 else 3,PEARL)
    hand=(mix(mix(-24,-8,w),32,st),mix(mix(48,89,w),62,st))
    if clip=='die': hand=mixp((-24,48),(-25,8),d)
    qshoulder=(-9,by+8)
    qelbow,hand=arm_ik(qshoulder,hand,23,23,-1)
    a.limb([qshoulder,qelbow,hand],VIOLET,5)
    a.ball(*hand,4,3.5,PEARL)
    a.limb([(10,by+9),(20,by+3),(25,max(7,by-3))],VIOLET,5)
    a.ball(25,max(7,by-3),4,3,PEARL)
    # Mirror remains physical through the death, rotating down and cracking rather than vanishing.
    ang=d*math.pi*.46
    mx,my=hand[0]+math.sin(ang)*10,hand[1]+math.cos(ang)*15
    a.line([hand,(mx,my)],GOLD[2],3)
    a.ball(mx,my,8,11,GOLD,ang=ang)
    a.ball(mx,my,6,8,AZURE,ang=ang)
    a.line([(mx-3,my+5),(mx+3,my-4)],WHITE,2)
    if d>.2: a.line([(mx-3,my+4),(mx+1,my),(mx-2,my-4)],OUTLINE,1)
    a.ball(hx,hy,14,13,PEARL)
    a.poly([(hx-14,hy+4),(hx-7,hy+12),(hx-2,hy+3),(hx+5,hy+10),(hx+14,hy+4),(hx+13,hy+13),(hx-13,hy+13)],VIOLET[1],outline=VIOLET[0])
    a.face(hx+1,hy-1,clip,n,.91,sep=5.5,pupil=PINK[0])
    # Crown drops beside the pooled gown.
    crownx=mix(hx,31,d)
    crowny=mix(hy+11,4,d)
    a.line([(crownx-12,crowny),(crownx+12,crowny)],GOLD[3],2)
    for k in range(5):
        a.crystal(crownx-10+k*5,max(2,crowny),2,6+(2-abs(2-k))*4,PEARL,tilt=k-2)
    if st>.3:
        end=mx+53
        a.poly([(mx+7,my+4),(end,my+13),(end,my-11),(mx+7,my-4)],GOLD[4],outline=GOLD[1])
        a.poly([(mx+7,my+1),(end,my+5),(end,my-3),(mx+7,my-1)],WHITE)
        for k in range(3): spark(a,mx+19+k*13,my+9-(k%2)*18,TEAL[4],3)
    return a


def sunshard(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('sunshard',recoil)
    cy=mix(57+bob+w*7,21,d)
    # Solar rays extinguish progressively; remaining rigid crystal fragments fall into grounded rubble.
    ray_power=1-sm(max(0,d-.1)/.7)
    for k in range(12):
        if ray_power<=.01: break
        th=k*math.pi/6+(0 if clip=='attack' and n==7 else ph)*.12
        ri=19
        le=(36 if k%2==0 else 30)+w*13
        tip=(math.cos(th)*le*ray_power,cy+math.sin(th)*le*ray_power)
        a.poly([(math.cos(th-.13)*ri,cy+math.sin(th-.13)*ri),tip,
                (math.cos(th+.13)*ri,cy+math.sin(th+.13)*ri)],AMBER[3 if k%2 else 2],outline=AMBER[0])
    if d<.85:
        diamond(a,0,cy,19,29,AMBER)
        diamond(a,-3,cy+5,12,18,GOLD)
        a.face(0,cy+6,clip,n,.91,sep=6,pupil=AMBER[0])
        if d>.08: a.line([(-9,cy+21),(-2,cy+12),(-6,cy+2),(4,cy-7),(0,cy-22)],OUTLINE,2)
    # Detached fists are intentional for this elemental; they fall as separate crystals on death.
    for sg in (-1,1):
        fx=sg*32 + (st*30 if sg>0 else -w*8)
        fy=cy-11+w*37-st*(16 if sg<0 else 2)
        if clip=='die':
            fx=mix(sg*32,sg*38,d)
            fy=mix(46,8,d)
        diamond(a,fx,max(8,fy),9,10,AMBER if d<.65 else BROWN)
        a.line([(fx-3,fy+3),(fx+1,fy-3)],GOLD[4] if d<.65 else BROWN[1],2)
    if st>.3:
        for k in range(3): spark(a,75+k*5,cy-7+k*5,GOLD[4],3)
    if d>0:
        for k in range(7):
            x=-28+k*9+(n%2)*.5
            y=mix(48+(k%3)*7,3+(k%2),d)
            diamond(a,x,y,4+(k%2),4,AMBER if d<.6 else BROWN)
    return a


DRAW = dict(miragejackal=miragejackal,shardscarab=shardscarab,glassharrier=glassharrier,
            prismsentinel=prismsentinel,mirrorqueen=mirrorqueen,sunshard=sunshard)

STRICT = True
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if kind in FLYING:
        # Flying Void Moth stays well above the ground in living clips and settles onto kay at the end of death.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and clip == 'die' and (n == 7 or int(rows.max()) > kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    else:
        # Grounded kinds rest their lowest pixel exactly on the anchor row in every living and death frame.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and (clip == 'die' or int(rows.max()) != kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    problem = None
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
        name = PREFIX + kind + '_all'
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/prism_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/prism_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    meta = dict(frame=[W, H], anchor=[AX, AY], kinds=KINDS, clips={}, sprites=saved, tops={}, artStyle='greenmeadow-slime')
    proof, atlases = {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for kind, atlas in atlases.items():
        dest = ASSETS / f'prism_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    meta = json.loads(MANIFEST.read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'prism_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW]:
        old_kf = KIND_FRAMES.get(kind)
        KIND_FRAMES[kind] = (192, 192, 96, 160)
        left = right = up = 0
        for clip, grids in frames(kind).items():
            for grid in grids:
                ys, xs = np.nonzero(grid)
                if xs.size:
                    left = max(left, 94 - int(xs.min()) + 2)
                    right = max(right, int(xs.max()) - 94 + 2)
                    up = max(up, 158 - int(ys.min()))
        print(f'{kind}: left {left} right {right} up {up}  ->  suggested ax {left+4}, w {left+4+right+5}, ay {up+4}, h {up+4+6}')
        if old_kf:
            KIND_FRAMES[kind] = old_kf
        else:
            del KIND_FRAMES[kind]


def preview():
    global STRICT
    STRICT = False
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or [k for k in KINDS if k in DRAW]
    for kind in only:
        kw, kh, _, kay = kind_frame(kind)
        data = frames(kind)
        sheet = Image.new('RGB', (8 * kw * 2, 5 * (kh * 2 + 26)), '#221f33')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((kw * 2, kh * 2), Image.Resampling.NEAREST)
                sheet.paste(im, (n * kw * 2, row * (kh * 2 + 26)), im)
                sd.text((n * kw * 2 + 8, row * (kh * 2 + 26) + kh * 2 + 4), f'{clip} {n}', fill='white')
                gy = row * (kh * 2 + 26) + kay * 2 + 2
                sd.line([(n * kw * 2, gy), (n * kw * 2 + kw * 2, gy)], fill='#5c5284')
        sheet.save(OUT / f'preview-{kind}.png')
        print(OUT / f'preview-{kind}.png')
    print('Frame problems:', BAD or 'none')


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
