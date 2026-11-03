#!/usr/bin/env python3
"""Rimeveil slime-style PixelFlow art: preview | build | export.

Separate source names preserve previous art. Rigid shells and animal anatomy
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
OUT = ROOT/'test-results/rime-slime'
REGISTRY = ROOT/'scripts/rime_slime_sources.txt'
PREFIX = 'valhallasc_rime_slime_style_'
KINDS = ['crab', 'wolf', 'yeti', 'wyrm']
NAMES = dict(crab='Rime Crab', wolf='Frost Wolf', yeti='Yeti', wyrm='Rime Wyrm')
W = H = 96
AX, AY = 48, 90
CLIPS = old.CLIPS
PALETTE = ['#00000000', '#23324a', '#ffffff', '#edf6f7', '#eda7bc',
           '#16466f', '#2779a9', '#55b7d7', '#9ce4f0', '#defaff',
           '#526784', '#839db9', '#b2c9db', '#dce9ee', '#fafcf4',
           '#28608c', '#559ac0', '#8bcce0', '#c8f0f3', '#f0ffff',
           '#2b416c', '#5282bb', '#87bee4', '#c1e5f8', '#f2fbff',
           '#3f314b', '#98567a', '#cf89ab', '#f3c0cd', '#fff0db']
SHELL = [5, 6, 7, 8, 9]
FUR = [10, 11, 12, 13, 14]
FACE = [15, 16, 17, 18, 19]
ICE = [20, 21, 22, 23, 24]
MOUTH = [25, 26, 27, 28, 29]


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
    phase = n*math.pi/4
    stride = math.sin(phase)*4 if clip == 'walk' else 0
    bob = [0, 1, 1, 0, -1, 0][n] if clip == 'idle' else 0
    lunge = [-1, -2, -4, 1, 4, 3, 1, 0][n] if clip == 'attack' else 0
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    fall = [0, .06, .19, .36, .57, .78, .94, 1][n] if clip == 'die' else 0
    return stride, bob, lunge, recoil, fall


def crab(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    a = Painter(cx=43+lunge+recoil, lift=fall*3)
    cy = 27
    # Eight legs: each has a knee and a foot. Carapace radii never change.
    def legs(far):
        for k in range(4):
            x = -18+k*11+(-2 if far else 0)
            direction = -1 if k < 2 else 1
            step = stride*(-1 if (k+far)%2 else 1)
            hip = (x, cy-5)
            knee = (x+direction*(8-5*fall), cy-9+fall*13)
            foot = (x+direction*(12-9*fall)+step*(1-fall),
                    5+abs(step)*(1-fall)+fall*(25+k%2*3)+(5 if far else 0))
            a.limb([hip, knee, foot], ICE if far else SHELL, 3)
    legs(True)
    open_claw = ([4, 6, 8, 1, 0, 0, 2, 4][n] if clip == 'attack'
                 else 3+bob if not fall else max(0, 3-n))
    def claw(x, y, far=False):
        ramp = ICE if far else SHELL
        a.limb([(12, cy), (x-5, y-5), (x, y)], ramp, 4)
        a.ball(x+1, y, 7, 6, ramp)
        a.limb([(x+3, y+2), (x+9, y+5+open_claw)], ramp, 3)
        a.limb([(x+4, y-2), (x+10, y+1-open_claw)], ramp, 3)
    claw(23-fall*8, 37+max(0, lunge)*2-fall*7, True)
    for x, h in [(-15, 12), (-5, 16), (6, 11)]:
        a.crystal(x, cy+10, h, 4, -2)
    a.ball(-2, cy, 23, 15, SHELL)
    a.line([(-20, cy-5), (-10, cy-10), (4, cy-11), (16, cy-6)], 6, 2)
    a.ellipse(-10, cy+7, 6, 2, 9)
    for x in (-11, -2, 6):
        a.ellipse(x, cy+3+(x%3), 1, 1, 9)
    legs(False)
    for x, y in [(14, cy+17), (25, cy+15)]:
        a.limb([(x-4, cy+7), (x, y-4)], SHELL, 3)
        a.eye(x, y, clip, n, .88)
    if not fall:
        a.ellipse(24, cy+4, 2, 1, 4)
    claw(26-fall*10, 15+max(0, -lunge)*2+fall*15)
    if clip == 'die':
        if n >= 2:
            a.line([(-13, cy+8), (-8, cy+3), (-11, cy-2), (-5, cy-7)], 5, 2)
        # Roll onto the rigid shell while every leg curls in toward it.
        a.im = a.im.rotate(-[0, 6, 19, 35, 54, 76, 98, 108][n],
            resample=Image.Resampling.NEAREST, center=a.pos(0, cy))
    return a


def wolf(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    a = Painter(cx=44+lunge+recoil, lift=(1 if clip=='walk' and n%2 else 0)+fall*14)
    cy = 28-fall*9
    tail_wave = math.sin(n*math.pi/3)*3 if clip in ('idle', 'walk') else 0
    a.limb([(-19, cy), (-28, cy+5+tail_wave*(1-fall)), (-34, cy+11-fall*10)], FUR, 7)
    a.ball(-34, cy+10-fall*10, 5, 5, ICE)
    for far in (True, False):
        for k, x in enumerate((-14, 11)):
            step = stride*(-1 if (k+far)%2 else 1)
            hip = (x, cy-3)
            knee = (x+2+step*.5+fall*6, 15-fall*3)
            foot = (x+4+step*(1-fall)+fall*12, 5+abs(step)*.6+fall*3)
            a.limb([hip, knee, foot], ICE if far else FUR, 5)
            a.ball(*foot, 6, 3, FUR)
        if far:
            a.ball(-5, cy, 22, 14, FUR)
            a.ball(-3, cy-6, 15, 6, [11, 12, 13, 14])
            for x, h in [(-17, 7), (-8, 10), (0, 8)]:
                a.crystal(x, cy+12, h, 3, -3)
            a.ball(13, cy+2, 12, 14, FUR)
    hx, hy = 19+max(0,lunge), cy+16-fall*7+bob*(1-fall)
    for x, tilt in [(hx-7, -2), (hx+3, 3)]:
        a.poly([(x-5, hy+5), (x+tilt, hy+22), (x+6, hy+6)], 10)
        a.poly([(x-2, hy+8), (x+tilt, hy+18), (x+3, hy+8)], 22)
    a.ball(hx, hy, 14, 12, FUR)
    jaw = max(0,lunge)*.65 if clip=='attack' else 0
    a.ball(hx+9, hy-7-jaw, 10, 4, [11, 12, 13, 14])
    if jaw:
        a.ball(hx+10, hy-5, 7, 3+jaw, MOUTH)
    a.ball(hx+8, hy-3, 10, 5, FUR)
    a.ellipse(hx+16, hy-2, 3, 2, 1)
    a.eye(hx-3, hy+2, clip, n, 1)
    a.eye(hx+7, hy+2, clip, n, .8)
    if fall < .2:
        a.ellipse(hx-8, hy-6, 2, 1, 4)
    a.line([(hx+5,hy-8),(hx+12,hy-9)], 1)
    if clip == 'die':
        # A furred animal rolls onto its side, legs folding at the joints.
        a.im = a.im.rotate(-[0, 2, 7, 13, 22, 32, 39, 42][n],
            resample=Image.Resampling.NEAREST, center=a.pos(0, 21))
    return a


def yeti(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    a = Painter(cx=45+lunge*.5+recoil, lift=fall*20)
    torso = 36-fall*18
    # Knees flex while the fixed-size torso and head fall to one side.
    for sign in (-1, 1):
        step = stride*sign
        a.limb([(sign*10, torso-9), (sign*(10+fall*5), 13-fall*2),
                (sign*(12+fall*8), 5+max(0,step)*(1-fall))], FUR, 9)
        a.ball(sign*(12+fall*8), 5+max(0,step)*(1-fall), 10, 5, FUR)
    arm_up = [0, 10, 22, 30, 3, -5, -2, 0][n] if clip=='attack' else bob
    left_hand = (-29-fall*3, 19-fall*10+stride*.4)
    a.limb([(-17, torso+6), (-25, torso-1), left_hand], FUR, 11)
    a.ball(*left_hand, 10, 10, FUR)
    a.ball(0, torso, 23, 21, FUR)
    a.ball(-3, torso-5, 13, 11, [11, 12, 13, 14])
    for x in (-16, -8, 0, 8, 16):
        a.poly([(x-4,torso-12),(x,torso-23),(x+5,torso-12)], 11)
    hy = 61-fall*26+bob*(1-fall)
    hx = -fall*10
    for x, tilt in [(-9, -4), (8, 4)]:
        a.crystal(hx+x, hy+10, 12, 4, tilt)
    a.ball(hx, hy, 16, 15, FUR)
    a.ball(hx+1, hy-2, 13, 10, FACE)
    a.face(hx+1, hy, clip, n, .9)
    # Tusks remain attached to the blue face during the fall.
    for x in (hx-5, hx+8):
        a.poly([(x-2,hy-8),(x,hy-15),(x+2,hy-8)], 3)
    right_hand = (29+max(0,lunge), 20+arm_up*(1-fall)-fall*12)
    a.limb([(17,torso+6),(27,torso+2+arm_up*.3),right_hand], FUR, 11)
    a.ball(*right_hand, 11, 10, FUR)
    for sign in (-1,1):
        a.ball(sign*18,torso+11,9,9,FUR)
        a.crystal(sign*18,torso+17,9,3,sign*2)
    if clip == 'die':
        # Knees buckle first; the heavy furred body topples, rather than crumbling.
        a.im = a.im.rotate([0, 1, 4, 9, 17, 27, 36, 40][n],
            resample=Image.Resampling.NEAREST, center=a.pos(0, 22))
    return a


def wyrm(clip, n):
    stride, bob, lunge, recoil, fall = motion(clip, n)
    a = Painter(cx=43+recoil)
    wave = (math.sin(n*math.pi/4)*3 if clip=='walk' else
            math.sin(n*math.pi/3)*2 if clip=='idle' else 0)
    # Coils spread apart at death instead of shrinking into flattened ellipses.
    a.limb([(15,12), (28,10), (34,18+wave*(1-fall))], SHELL, 6)
    a.crystal(34,18+wave*(1-fall),7,3,2)
    for k, (x,y,rx,ry) in enumerate([(0,12,26,10),(1,26,22,10),(-2,39,17,10)]):
        xx = x-fall*k*8+wave*(1-fall)*k*.4
        yy = y-fall*k*12
        a.ball(xx, yy, rx, ry, SHELL)
        a.ball(xx+2, yy-3, rx*.7, 4, FACE)
        for j in range(3):
            a.crystal(xx-rx*.6+j*7, yy+7, 6+j%2*3, 2.5, -2)
    hx = 6+wave+max(0,lunge)*2+fall*15
    hy = 61+bob-lunge*.8-fall*45
    # Curved, articulated neck follows the head down and lies across the coils.
    a.limb([(-2-fall*8,40-fall*25), (1,51-fall*36), (hx-3,hy-5)], SHELL, 12)
    a.line([(1-fall*8,37-fall*25),(4,49-fall*34),(hx,hy-8)], 18, 4)
    for x,h,tilt in [(-12,12,-4),(-5,17,-1),(3,13,3)]:
        a.crystal(hx+x,hy+8,h,3,tilt)
    jaw = max(0,lunge) if clip=='attack' else max(0,1-fall*2)
    a.ball(hx+8,hy-8-jaw,10,4,FACE)
    if jaw > 1:
        a.ball(hx+9,hy-5,8,jaw+1,MOUTH)
    a.ball(hx,hy,15,12,SHELL)
    a.ball(hx+9,hy-3,11,6,SHELL)
    a.ellipse(hx+17,hy-2,2,1,1)
    a.face(hx+1,hy+2,clip,n,.8)
    if clip=='attack' and n in (3,4,5):
        for k in range(3):
            # Breath effects stay inside the established canvas.
            x=min(40,hx+20+k*4)
            a.crystal(x,hy-8+(k%2)*3,5,2,1)
    if clip=='die' and n>=4:
        for k in range(3):
            a.ellipse(-24+k*13+(n-4)*(k-1),7+k%2,1,1,23)
    return a


DRAW = dict(crab=crab, wolf=wolf, yeti=yeti, wyrm=wyrm)


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
        np.savez_compressed(ROOT/f'scripts/rime_slime_{kind}_raw.npz',**data[kind])
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
        dest=ASSETS/f'rime_{kind}.png';atlas.save(dest,optimize=True)
        proof[kind]['atlasSha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'rime.txt').write_text(json.dumps(meta,indent=2)+'\n')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('Exported 136 saved PixelFlow frames and derived health-bar tops.',flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames, not drawers."""
    meta=json.loads((ASSETS/'rime.txt').read_text())
    saved=json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind]==saved[kind]
        sp=old.api('get?sprite_id='+saved[kind])['sprite']
        atlas=Image.open(ASSETS/f'rime_{kind}.png').convert('RGBA');offset=0
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
    overview=Image.new('RGB',(4*240,5*218),'#344b40');d=ImageDraw.Draw(overview)
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
