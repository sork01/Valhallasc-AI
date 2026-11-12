#!/usr/bin/env python3
"""Frostwake enemy remake. New editable PixelFlow sources; shared NPC entries preserved.
preview | build | refresh KIND... | export | verify
"""
import json, math, os, sys, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
import lapis_slime_redraw as L
from astral_slime_redraw import Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BONE, PEARL, AZURE, FUR, SLATE, GOLD, TEAL, VIOLET, CRIMSON
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
OUT=ROOT/'test-results/frostwake-slime'
REGISTRY=ROOT/'scripts/frostwake_slime_sources.txt'
MANIFEST=ASSETS/'frostwake.txt'
PREFIX='valhallasc_frostwake_slime_'
KINDS=['snowhare','iceotter','frostheron','glaciercrab','bellmammoth','auroramanta','crevasseleviathan']
NAMES=dict(zip(KINDS,['Snow Hare','Ice Otter','Frost Heron','Glacier Crab','Bell Mammoth','Aurora Manta','Crevasse Leviathan']))
VILLAGERS=['frostwake_captain','frostwake_surveyor','frostwake_bellkeeper','frostwake_skywatcher','frostwake_ribkeeper','frostwake_travel']
W=H=96
AX,AY=48,90
KIND_FRAMES={k:(168,180,84,170) for k in KINDS}
CLIPS={'idle':(10,6),'walk':(10,8),'attack':(10,8),'hurt':(10,4),'die':(10,8)}
FLYING=('auroramanta',)
STRICT=True
BAD=[]
LOWEST={}
def kind_frame(kind): return kindframe.check_frame(*KIND_FRAMES[kind])
class Painter(BasePainter):
    def __init__(self,kind):
        self.w,self.h,self.ax,self.ay=kind_frame(kind)
        self.im=Image.new('P',(self.w,self.h),0)
        self.d=ImageDraw.Draw(self.im)
        self.cx=self.ax
        self.ay=110

def beats(clip,n):
    wind=(.12,.55,1,.35,0,0,0,0)[n] if clip=='attack' else 0
    strike=(0,0,0,.65,1,.60,.22,.04)[n] if clip=='attack' else 0
    death=n/7 if clip=='die' else 0
    phase=n*math.pi/4+.31
    bob=(1-math.cos(n*math.pi/3+.3))*.7 if clip=='idle' else 0
    return wind,strike,death,phase,bob

def setup(kind,clip,n,pivot,angle):
    a=Painter(kind); w,s,d,ph,b=beats(clip,n)
    r=L.Rig(a,*pivot,angle*d + ((-.08,-.04,.035,.01)[n] if clip=='hurt' else 0))
    return a,r,w,s,d,ph,b

def eyes(r,x,y,clip,n,sep=6,size=1):
    for dx in (-sep,sep):
        if clip=='die' and n>1:
            r.line([(x+dx-2,y-2),(x+dx+2,y+2)],OUTLINE,2)
            r.line([(x+dx-2,y+2),(x+dx+2,y-2)],OUTLINE,2)
        else:
            r.ball(x+dx,y,4*size,5*size,[OUTLINE,EYE_WHITE,WHITE])
            r.ball(x+dx+1,y,2*size,3*size,AZURE)
            r.ellipse(x+dx,y+2,1,1,WHITE)
            if clip=='attack':r.line([(x+dx-4,y+5),(x+dx+3,y+2)],OUTLINE,2)

def snowhare(clip,n):
    a,r,w,s,d,ph,b=setup('snowhare',clip,n,(0,19),-.28)
    hop=max(0,math.sin(ph))*9 if clip=='walk' else 0
    cy=20+b+hop+3*w-9*d
    r.ball(-21,cy,7,7,PEARL)
    for x in (-9,10):
        if clip=='walk': x+=math.sin(ph+(0 if x<0 else 2))*5
        r.limb([(x,cy-3),(x+6*s,8+hop),(x+10+10*s-9*d,3+hop+6*d)],PEARL,6)
    r.ball(-3,cy,20,15,PEARL)
    r.ball(6,cy+3,10,10,FUR)
    hx,hy=13+13*s-6*w,cy+16
    for x in (hx-5,hx+4):
        r.ball(x-3*d,hy+17,4,17,PEARL,.12+w*.25+d*.5)
        r.ball(x-3*d,hy+17,1.6,12,CRIMSON,.12+w*.25+d*.5)
    r.ball(hx,hy,14,12,PEARL)
    r.ball(hx+8,hy-4,7,5,FUR)
    eyes(r,hx+1,hy+3,clip,n,5,.85)
    r.ball(hx+13,hy-2,2,2,CRIMSON)
    r.poly([(hx+7,hy-8),(hx+12,hy-8),(hx+10,hy-12-3*s)],BONE[-1])
    return a

def iceotter(clip,n):
    a,r,w,s,d,ph,b=setup('iceotter',clip,n,(-3,16),-.18)
    cy=19+b-4*w-10*d
    r.taper([(-22,cy),(-35,cy-2),(-48,8+math.sin(ph)*3*(1-d))],AZURE,9,1)
    for i,x in enumerate((-17,-8,10,20)):
        up=max(0,math.sin(ph+i*1.8))*4 if clip=='walk' else 0
        r.limb([(x,cy),(x+3,10+up),(x+7+8*s-12*d,3+up+7*d)],AZURE,5)
    r.ball(-2,cy,27,13,AZURE)
    r.ball(5,cy-5,17,6,PEARL)
    hx,hy=25+10*s-5*w,cy+10
    for x in (hx-6,hx+5):r.ball(x,hy+10,4,4,AZURE)
    r.ball(hx,hy,14,11,AZURE)
    r.ball(hx+6,hy-4,9,6,PEARL)
    eyes(r,hx,hy+3,clip,n,5,.8)
    r.ball(hx+12,hy,3,2,SLATE)
    for dy in (-3,0,3):r.line([(hx+10,hy-5),(hx+21,hy-5+dy)],WHITE,1)
    r.poly([(hx+6,hy-8),(hx+11,hy-8),(hx+10,hy-12-5*s)],BONE[-1])
    return a

def frostheron(clip,n):
    a,r,w,s,d,ph,b=setup('frostheron',clip,n,(0,24),-1.4)
    cy=43+b
    for i,x in enumerate((-6,6)):
        up=max(0,math.sin(ph+i*math.pi))*6 if clip=='walk' else 0
        r.limb([(x,cy-5),(x-4*d,20),(x+3,3+up)],GOLD,3)
        r.line([(x,3+up),(x+10,3+up)],GOLD[1],2)
    r.ball(-2,cy,16,14,PEARL)
    for side in (-1,1):
        end=(side*(22+15*w+9*s),cy-13+28*w-12*s)
        r.limb([(side*5,cy+4),end],AZURE,9)
        for j in range(3):r.ball(end[0]-side*j*5,end[1]-j*3,4,11,AZURE,-side*.4)
    hx,hy=11+20*s-9*w,cy+28-19*s
    r.limb([(4,cy+7),(-3,cy+21),(hx-3,hy)],PEARL,6)
    r.ball(hx,hy,11,9,PEARL)
    r.poly([(hx+6,hy+1),(hx+32,hy-2-5*s),(hx+8,hy-6)],GOLD[2],OUTLINE)
    eyes(r,hx-1,hy+2,clip,n,0,.8)
    for j in range(3):r.line([(hx-6,hy+6),(hx-19+j*3,hy+13-j*3)],AZURE[2],3)
    return a

def glaciercrab(clip,n):
    a,r,w,s,d,ph,b=setup('glaciercrab',clip,n,(0,22),math.pi)
    cy=24+b
    for side in (-1,1):
        for j in range(3):
            curl=12*d
            up=max(0,math.sin(ph+j+side))*4 if clip=='walk' else 0
            r.limb([(side*(10+j*4),cy-4),(side*(30+j*3-curl),15+curl),(side*(36+j*3-curl),3+up+curl)],AZURE,4)
    r.ball(0,cy,27,18,AZURE)
    for x in (-16,-5,7,17):
        r.poly([(x-4,cy+11),(x,cy+28-abs(x)*.4),(x+5,cy+11)],TEAL[-1],AZURE[0])
    for side in (-1,1):
        x=side*(34+9*s-7*w);y=cy+5+23*w-15*s
        r.limb([(side*19,cy),(side*29,cy+6),(x,y)],TEAL,6)
        r.ball(x,y,10,9,TEAL)
        r.poly([(x,y+3),(x+side*13,y+13-7*s),(x+side*11,y-4)],AZURE[2],OUTLINE)
        r.line([(x,y),(x+side*10,y+4-6*s)],OUTLINE,2)
        r.limb([(side*8,cy+12),(side*10,cy+24)],TEAL,3)
    eyes(r,0,cy+26,clip,n,10,.9)
    if d:
        r.line([(-10,cy+7),(-3,cy+2),(2,cy+6),(8,cy-4),(18,cy-8)],OUTLINE,1+int(d*2))
    return a

def bellmammoth(clip,n):
    a,r,w,s,d,ph,b=setup('bellmammoth',clip,n,(0,30),-.32)
    cy=35+b+5*w-16*d
    for i,x in enumerate((-25,-13,13,24)):
        up=max(0,math.sin(ph+i*1.7))*5 if clip=='walk' else 0
        r.limb([(x,cy),(x+6*s,15+up),(x+7*s-12*d,7+up+7*d)],FUR,12)
        r.ball(x+7*s-12*d,5+up+7*d,8,4,SLATE)
    r.ball(-7,cy+9,35,26,FUR)
    for j in range(7):r.poly([(-32+j*8,cy-3),(-29+j*8,cy-13),(-25+j*8,cy-2)],FUR[1])
    hx,hy=31+8*s-6*w,cy+22
    r.ball(hx-13,hy-2,11,16,SLATE)
    r.ball(hx,hy,19,18,FUR)
    r.taper([(hx+9,hy-5),(hx+14,hy-18),(hx+24+6*s,hy-23+20*w)],FUR,10,4)
    for off in (-3,9):r.taper([(hx+off,hy-7),(hx+off+12,hy-18),(hx+off+18,hy-10)],BONE,5,1)
    eyes(r,hx+1,hy+5,clip,n,6,.95)
    bx=-15+math.sin(ph)*2*(1-d);by=cy-7
    r.line([(-15,cy+18),(bx,by+8)],SLATE[1],3)
    r.poly([(bx-6,by+8),(bx+6,by+8),(bx+10,by-4),(bx-10,by-4)],GOLD[2],GOLD[0])
    r.ball(bx,by-4,10,3,GOLD)
    r.ball(bx+3*(1-d),by-8,3,3,GOLD)
    return a

def auroramanta(clip,n):
    a,r,w,s,d,ph,b=setup('auroramanta',clip,n,(0,34),-.3)
    cy=52+b-25*d
    flap=(math.sin(ph)*9 if clip in ('idle','walk') else 18*w-14*s)*(1-d)
    for side in (-1,1):
        r.poly([(side*4,cy+9),(side*30,cy+22+flap),(side*(56-20*d),cy+7+flap),(side*35,cy-12),(side*5,cy-9)],TEAL[2],TEAL[0])
        r.poly([(side*10,cy+5),(side*30,cy+15+flap),(side*(46-17*d),cy+6+flap),(side*24,cy-5)],VIOLET[2])
        r.line([(side*12,cy+4),(side*30,cy+9+flap),(side*(45-17*d),cy+7+flap)],TEAL[-1],2)
    for i in range(3):r.taper([(-5+i*5,cy-8),(-13+i*10+math.sin(ph+i)*4,cy-24),(-18+i*15,cy-36+10*d)],VIOLET if i==1 else TEAL,4,1)
    r.ball(0,cy,15,16,TEAL)
    r.ball(2,cy-5,9,8,PEARL)
    eyes(r,5+7*s-4*w,cy+10,clip,n,6,.9)
    return a

def crevasseleviathan(clip,n):
    a,r,w,s,d,ph,b=setup('crevasseleviathan',clip,n,(0,25),-1.25)
    r.taper([(-40,7),(-26,12),(-23,26),(-14,42),(-10,58)],AZURE,7,15)
    r.ball(-17,14,24,12,AZURE)
    r.limb([(-14,20),(-20,40),(-10,61)],AZURE,22)
    r.limb([(-8,27),(-11,44),(-3,58)],PEARL,8)
    hx,hy=15+23*s-13*w+(math.sin(ph)*4 if clip=='walk' else b),71-15*s+5*w+b
    r.limb([(-10,58),(hx,hy)],AZURE,19)
    for j in range(4):r.poly([(-27+j*7,23+j*10),(-40+j*8,33+j*10),(-23+j*7,31+j*10)],TEAL[2],AZURE[0])
    r.ball(hx,hy,23,17,AZURE)
    jaw=2+12*s+3*w
    r.ball(hx+10,hy-10-jaw,16,6,AZURE)
    r.ball(hx+12,hy-7-jaw/2,14,3+jaw/2,CRIMSON)
    for j in range(5):r.poly([(hx+j*5,hy-5),(hx+j*5+4,hy-5),(hx+j*5+2,hy-12)],BONE[-1])
    eyes(r,hx+1,hy+7,clip,n,7,.9)
    for x in (hx-12,hx-2,hx+7):r.poly([(x-4,hy+12),(x-7,hy+29),(x+4,hy+14)],TEAL[2],AZURE[0])
    return a
DRAW={k:globals()[k] for k in KINDS}
def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    clipped = bool(grid.any() and (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()))   # BEFORE the roll hides it
    if grid.any():
        LOWEST[kind] = max(LOWEST.get(kind, -999), int(np.nonzero(grid.any(axis=1))[0].max()) - kay)
    if kind in FLYING:
        grid = np.roll(grid, kay - 110, axis=0)
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
        np.savez_compressed(ROOT / f'scripts/frostwake_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/frostwake_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'frostwake_{kind}.png'


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
    sheet=Image.new('RGBA',(len(poses)*168,len(KINDS)*200),'#243346')
    pen=ImageDraw.Draw(sheet)
    for y,k in enumerate(KINDS):
        for x,(clip,n) in enumerate(poses):sheet.alpha_composite(rgba(frame(k,clip,n)),(x*168,y*200))
        pen.text((4,y*200+180),NAMES[k],fill='white')
    sheet.save(OUT/'poses.png')
    print(OUT/'poses.png')
if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    {'preview':preview,'build':build,'refresh':refresh,'export':export,'verify':verify}[cmd]()
