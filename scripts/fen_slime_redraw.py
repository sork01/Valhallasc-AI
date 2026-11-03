#!/usr/bin/env python3
"""Gloamfen slime-style PixelFlow art: preview | build | export.

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
OUT = ROOT/'test-results/fen-slime'
REGISTRY = ROOT/'scripts/fen_slime_sources.txt'
PREFIX = 'valhallasc_fen_slime_style_'
KINDS = ['toad', 'croc', 'knight', 'hydra', 'gloomroot']
NAMES = dict(toad='Fen Toad', croc='Mire Crocodile', knight='Drowned Knight', hydra='Mire Hydra', gloomroot='Gloomroot Colossus')
W = H = 96
AX, AY = 48, 90
CLIPS = old.CLIPS
PALETTE = ['#00000000', '#182c25', '#ffffff', '#f7fff0', '#eda0ad',
           '#263d16', '#496b25', '#7ca83c', '#b5d85f', '#ecfca6',
           '#283e36', '#4c7869', '#7bb7a0', '#b8e5cd', '#e5fff0',
           '#543522', '#825432', '#b5844d', '#ddb77b', '#f5dfad',
           '#183f49', '#287989', '#53b8bd', '#9ce7dc', '#e1fff2',
           '#3f193e', '#833c83', '#c36cb7', '#eca7cd', '#ffe4ef',
           '#115647', '#2ab592', '#8bf4cf', '#d1fff0', '#f2fff9']
SKIN = [5, 6, 7, 8, 9]
PLATE = [10, 11, 12, 13, 14]
BARK = [15, 16, 17, 18, 19]
TEAL = [20, 21, 22, 23, 24]
PURPLE = [25, 26, 27, 28, 29]
GLOW = [30, 31, 32, 33, 34]
ICE = TEAL


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

    def tail(self, points, ramp, radius):
        """A continuous curved silhouette narrows to one visible pointed tip."""
        points=np.asarray(points,dtype=float)
        samples=[]
        for t in np.linspace(0,1,33):
            u=1-t
            centre=u**3*points[0]+3*u*u*t*points[1]+3*u*t*t*points[2]+t**3*points[3]
            tangent=3*u*u*(points[1]-points[0])+6*u*t*(points[2]-points[1])+3*t*t*(points[3]-points[2])
            normal=np.array([-tangent[1],tangent[0]])/np.linalg.norm(tangent)
            samples.append((centre,normal,radius*(1-t)**.9))
        def band(lo,hi,inset=0):
            left=[tuple(c+normal*max(0,r-inset)*lo) for c,normal,r in samples]
            right=[tuple(c+normal*max(0,r-inset)*hi) for c,normal,r in reversed(samples)]
            return left+right
        self.poly(band(-1,1),ramp[0])
        self.poly(band(-1,1,.8),ramp[2])
        self.poly(band(.25,1,1),ramp[1])
        self.poly(band(-.8,-.15,1),ramp[3])

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


def toad(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    hop=[0,1,7,12,10,4,0,0][n] if clip=='walk' else 0
    a=Painter(cx=44+lunge*.6+recoil, lift=hop+fall*8)
    cy=23+bob*.4
    # A living animal: bent hind legs and small forefeet; no melting geometry.
    for far in (True,False):
        off=-4 if far else 0
        knee=(-22+off,cy-3+fall*6)
        foot=(-15+off-stride*(1-fall),5+fall*18)
        a.ball(-15+off,cy-4,11,10,SKIN)
        a.limb([(-14+off,cy),knee,foot],SKIN,5)
        a.ball(*foot,9,3,SKIN)
        hand=(22+off+stride*.4,5+fall*20)
        a.limb([(14+off,cy-2),(18+off,cy-9+fall*6),hand],SKIN,4)
        a.ball(*hand,6,3,SKIN)
        if far:
            a.ball(-2,cy,24,17,SKIN)
            a.ball(1,cy-8,17,7,[16,17,18,19])
            for x,y in [(-16,7),(-9,11),(-4,5),(-18,0),(-10,-2)]:
                a.ball(x,cy+y,2.5,2,SKIN)
    hx,hy=15,cy+6
    gape=max(0,lunge)*1.1
    a.ball(hx+2,hy-8-gape,15,4,BARK)
    if gape:
        a.ball(hx+5,hy-6,11,3+gape,PURPLE)
        if n in (3,4,5):
            a.limb([(hx+6,hy-6),(33,hy-7),(min(40,33+lunge*2),hy-5)],PURPLE,3)
    a.ball(hx,hy,17,12,SKIN)
    for x in (hx-7,hx+6):
        a.ball(x,hy+10,7,8,SKIN)
        a.eye(x,hy+11,clip,n,.9)
    a.ellipse(hx-10,hy-3,2.5,1.5,4)
    a.line([(hx-9,hy-6),(hx,hy-8),(hx+12,hy-6)],1)
    if clip=='die':
        # Legs tuck; the whole animal tips backwards, belly intact.
        a.im=a.im.rotate([0,5,17,34,57,80,102,116][n],
            resample=Image.Resampling.NEAREST,center=a.pos(0,cy))
    return a


def croc(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=44+lunge*.5+recoil,lift=fall*10)
    cy=20+bob*.35-fall*3
    tail=math.sin(n*math.pi/3)*3 if clip in ('idle','walk') else -lunge
    a.tail([(-12,cy+1),(-26,cy+1),(-33,cy+5+tail*(1-fall)),
            (-39,cy+10+tail*(1-fall))],SKIN,6)
    for x in (-29,-21,-13,-5,3):
        a.poly([(x-3,cy+8),(x,cy+16),(x+4,cy+8)],7)
    for far in (True,False):
        for j,x in enumerate((-17,9)):
            step=stride*(-1 if (j+far)%2 else 1)
            foot=(x+5+step*(1-fall)+fall*5,5+abs(step)*.4+fall*8)
            a.limb([(x,cy),(x+3,cy-7),foot],SKIN,5)
            a.ball(*foot,7,3,SKIN)
        if far:
            a.ball(-4,cy,23,12,SKIN)
            a.ball(-2,cy-6,17,5,[16,17,18,19])
    hx,hy=19+max(0,lunge)*.4,cy+5
    gape=[0,2,6,10,1,0,0,0][n] if clip=='attack' else 0
    a.ball(hx+7,hy-6-gape,14,4,BARK)
    if gape:
        a.ball(hx+8,hy-4-gape*.5,12,3+gape*.4,PURPLE)
    for x in (hx,hx+6,hx+12):
        a.poly([(x-2,hy-5-gape),(x,hy-1-gape),(x+2,hy-5-gape)],3)
    a.ball(hx,hy,12,10,SKIN)
    a.ball(hx+10,hy-2,12,5,SKIN)
    a.ellipse(hx+19,hy,2,1,1)
    a.ball(hx-2,hy+9,6,6,SKIN)
    a.eye(hx-2,hy+10,clip,n,.95)
    a.ellipse(hx+1,hy-3,2,1,4)
    if clip=='die':
        # The scaled animal's feet fold and its long body rolls onto its flank.
        a.im=a.im.rotate(-[0,2,7,13,21,30,38,43][n],
            resample=Image.Resampling.NEAREST,center=a.pos(0,19))
    return a


def knight(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    # Separate rigid armour pieces slide apart as the drowned magic goes out.
    torso=35+bob*.5-fall*17
    for sign in (-1,1):
        step=stride*sign
        foot=(sign*(9+fall*9),6+max(0,step)*(1-fall))
        a.limb([(sign*7,25-fall*10),(sign*(8+fall*6),15-fall*5),foot],PLATE,6)
        a.ball(*foot,9,5,PLATE)
    sx,sy=-25-fall*3,36-fall*22+bob
    a.limb([(-13,torso+4),(sx+5,sy)],PLATE,5)
    a.ball(sx,sy,11,14,PLATE)
    a.ball(sx,sy,7,9,TEAL)
    a.ellipse(sx-2,sy+3,3,3,14)
    a.ball(0,torso,16,15,PLATE)
    a.line([(-11,torso-5),(11,torso-5)],16,2)
    a.ball(-6,torso+6,5,3,[11,12,13,14])
    for x in (-15,15):
        a.ball(x,torso+9,8,7,PLATE)
        a.ellipse(x,torso+11,3,2,7)
    hy=60+bob*.5-fall*43
    hx=1+fall*15
    a.ball(hx,hy,15,14,PLATE)
    a.ball(hx-5,hy+6,6,3,[11,12,13,14])
    a.poly([(hx-13,hy+2),(hx+13,hy+2),(hx+12,hy-7),(hx-12,hy-7)],1)
    for x in (hx-6,hx+6):
        a.eye(x,hy-1,clip,n,.8)
    if fall<.6:
        a.ellipse(hx-12,hy-6,2,1,4)
    for x,h in [(-5,8),(1,12),(6,7)]:
        a.limb([(hx+x,hy+12),(hx+x-3+fall*7,hy+12+h*(1-fall*.8))],SKIN,3)
    hand=(24+max(0,lunge),32-lunge*2-fall*22)
    a.limb([(14,torso+5),(20,torso-1),hand],PLATE,5)
    a.ball(*hand,5,5,PLATE)
    angle=1.4-lunge*.25-fall*1.6
    dx,dy=math.cos(angle),math.sin(angle)
    tip=(min(40,hand[0]+dx*26),hand[1]+dy*26)
    a.line([(hand[0]-dx*4,hand[1]-dy*4),tip],10,6)
    a.line([hand,tip],13,4)
    a.line([(hand[0]-4*dy,hand[1]+4*dx),(hand[0]+4*dy,hand[1]-4*dx)],17,3)
    if clip=='die' and n>=2:
        a.line([(-7,torso+9),(-2,torso+4),(-5,torso-1),(4,torso-7)],10,2)
        # Fading sea-green motes, not a deforming metal body.
        for k in range(max(0,7-n)):
            a.ellipse(-16+k*7,torso+18+(n-2)*2+k%2*3,1,1,32)
    return a


def hydra(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    cy=20-fall*5
    tail_wave=math.sin(n*math.pi/3)*3 if clip in ('idle','walk') else -lunge*.5
    a.tail([(-13,cy),(-25,cy-1),(-33,cy+3+tail_wave*(1-fall)),
            (-40,cy+10+tail_wave*(1-fall))],TEAL,6)
    for j,x in enumerate((-19,-6,9,20)):
        step=stride*(-1 if j%2 else 1)
        a.limb([(x,cy),(x+step,10),(x+4+step,5+abs(step)*.5+fall*3)],TEAL,5)
        a.ball(x+4+step,5+abs(step)*.5+fall*3,6,3,TEAL)
    a.ball(-2,cy,26,13,TEAL)
    a.ball(1,cy-6,18,5,[7,8,9])
    for x in (-19,-10,0,10):
        a.poly([(x-4,cy+10),(x,cy+20),(x+5,cy+10)],26)
    # Each neck fails at its own time: left, right, then the central head.
    for j,(root,hx,hy,size,delay) in enumerate([
        (-16,-22,51,11,0), (3,0,66,13,.24), (17,23,48,11,.12)]):
        f=max(0,min(1,(fall-delay)/(1-delay)))
        sway=math.sin(n*math.pi/3+j)*2 if clip in ('idle','walk') else 0
        hx=hx+sway+f*(9 if j==0 else -8 if j==1 else 3)
        hy=hy+bob*.4-f*(hy-14-j*3)
        if j==1:
            hx+=max(0,lunge)*2;hy-=max(0,lunge)
        a.limb([(root,cy+4),(root-3,cy+17-f*15),(hx-2,hy-5)],SKIN,8)
        a.line([(root+2,cy+4),(root+1,cy+14-f*13),(hx,hy-8)],9,3)
        for x in (-5,3):
            a.poly([(hx+x-3,hy+size-2),(hx+x-1,hy+size+7),(hx+x+3,hy+size-2)],26)
        gape=max(0,lunge) if j==1 else 0
        a.ball(hx+5,hy-7-gape,9,3,BARK)
        if gape:
            a.ball(hx+6,hy-4,7,2+gape,PURPLE)
        a.ball(hx,hy,size,size*.85,SKIN)
        a.ball(hx+7,hy-3,7,4,SKIN)
        a.eye(hx-1,hy+2,clip,n,.8 if j==1 else .7)
        a.ellipse(hx-6,hy-4,2,1,4)
        a.ellipse(hx+12,hy-1,1,1,1)
    return a


def gloomroot(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    torso=37+bob*.3-fall*16
    for sign in (-1,1):
        foot=(sign*(11+fall*6)+stride*sign,6+max(0,stride*sign)*(1-fall))
        a.limb([(sign*10,torso-10),(sign*13,15-fall*5),foot],BARK,10)
        for k in range(3):
            a.limb([foot,(foot[0]+(k-1)*7,3+k%2)],BARK,3)
    left=(-30-fall*2,23-fall*9+bob)
    a.limb([(-18,torso+6),(-27,torso),left],BARK,9)
    a.ball(*left,9,9,BARK)
    a.ball(0,torso,22,20,BARK)
    for x in (-13,-5,5,13):
        a.line([(x,torso-11),(x-2,torso+11)],15,2)
    a.ball(1,torso,8,10,[15,16,17])
    if fall<.9:
        a.ball(1,torso+1,5,7,GLOW[:max(2,5-int(fall*4))])
        if fall<.2:a.ellipse(0,torso+4,1,2,3)
    for x in (-17,17):
        a.ball(x,torso+12,9,8,BARK)
        a.ball(x,torso+16,8,4,SKIN)
    hy=63+bob*.4-fall*38
    hx=-fall*9
    a.ball(hx,hy,16,14,BARK)
    a.ball(hx-4,hy+9,13,6,SKIN)
    a.face(hx,hy,clip,n,.85)
    for x,y in [(-7,17),(6,16)]:
        stalk=(hx+x,hy+y-4-fall*3)
        a.limb([(hx+x,hy+10),stalk],BARK,3)
        a.ball(stalk[0]-fall*3,stalk[1]+3,6,3,PURPLE)
        a.ellipse(stalk[0]-2,stalk[1]+4,1,1,3)
    armup=[0,10,24,27,0,-4,-2,0][n] if clip=='attack' else bob
    hand=(29+max(0,lunge),23+armup*(1-fall)-fall*13)
    a.limb([(18,torso+7),(26,torso+2),hand],BARK,10)
    a.ball(*hand,10,9,BARK)
    if clip=='die':
        # Dry trunk splits, heavy branches drop, moss and leaves wilt downward.
        if n>=2:
            a.line([(-5,torso+17),(0,torso+10),(-3,torso+1),(5,torso-10)],15,3)
        for k in range(5):
            x=-23+k*10+(n-1)*(1 if k%2 else -1)*.6
            y=max(4,54-k%3*10-n*5)
            a.poly([(x-2,y+4),(x+3,y-2),(x,y-5)],7 if n<4 else 6)
        if n>=3:
            for k in range(3):
                a.limb([(-17+k*14,14-(n-3)),(-20+k*14,5)],BARK,3)
    return a


DRAW=dict(toad=toad,croc=croc,knight=knight,hydra=hydra,gloomroot=gloomroot)

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
        np.savez_compressed(ROOT/f'scripts/fen_slime_{kind}_raw.npz',**data[kind])
        sid=old.api('create',dict(name=name,width=W,height=H,frames=34,layers=1,fps=10,
            palette=PALETTE,persist=True,ops=[dict(op='set_layer',layer=0,name=kind)]))['sprite_id']
        saved[kind]=sid
        REGISTRY.write_text(json.dumps(saved,indent=2)+'\n')
        offset=0
        for clip,grids in data[kind].items():
            for n,grid in enumerate(grids):
                old.api('draw',dict(sprite_id=sid,frame=offset+n,
                    ops=[dict(op='grid',rows=grid.tolist(),x=0,y=0,layer=0)]))
            offset+=len(grids)
        print(kind,sid,offset,'frames saved',flush=True)



def repair_tails():
    """Create two corrected sources; retain the earlier candidate IDs for rollback."""
    history_path=ROOT/'scripts/fen_slime_tail_sources.txt'
    saved=json.loads(REGISTRY.read_text())
    history=(json.loads(history_path.read_text()) if history_path.exists() else
             dict(previous={k:saved[k] for k in ('croc','hydra')},corrected={}))
    data={kind:frames(kind) for kind in ('croc','hydra')}
    for kind in data:
        if kind in history['corrected']:
            assert saved[kind]==history['corrected'][kind]
            print('Preserving corrected tail source',kind,saved[kind],flush=True)
            continue
        sid=old.api('create',dict(name=PREFIX+kind+'_tapered_tail_all',width=W,height=H,
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
        np.savez_compressed(ROOT/f'scripts/fen_slime_{kind}_raw.npz',**data[kind])
        print(kind,sid,'34 corrected tail frames saved',flush=True)


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
        dest=ASSETS/f'fen_{kind}.png';atlas.save(dest,optimize=True)
        proof[kind]['atlasSha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'fen.txt').write_text(json.dumps(meta,indent=2)+'\n')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('Exported 170 saved PixelFlow frames and derived health-bar tops.',flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames, not drawers."""
    meta=json.loads((ASSETS/'fen.txt').read_text())
    saved=json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind]==saved[kind]
        sp=old.api('get?sprite_id='+saved[kind])['sprite']
        atlas=Image.open(ASSETS/f'fen_{kind}.png').convert('RGBA');offset=0
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
    {'preview':preview,'build':build,'export':export,'verify':verify,'tails':repair_tails}[sys.argv[1] if len(sys.argv)>1 else 'preview']()
