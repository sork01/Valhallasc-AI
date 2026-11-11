#!/usr/bin/env python3
"""Eye Below: six original native PixelFlow enemies. preview|extents|build|refresh KIND|export|verify.
Preserves all 140 unrelated Cathedral kinds and saved editor changes on export.
"""
import hashlib, json, math, os, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
import lapis_slime_redraw as L
from astral_slime_redraw import Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BONE, PEARL, AZURE, SLATE, GOLD, TEAL, VIOLET, CRIMSON, GREEN, BROWN, PINK, CORAL, AMBER, PURPLE
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
OUT=ROOT/'test-results/eye-slime'
REGISTRY=ROOT/'scripts/eye_slime_sources.txt'
MANIFEST=ASSETS/'cathedral.txt'
PREFIX='valhallasc_eye_slime_'
KINDS=['eye_drifter','eye_adept','eye_lurker','eye_lenswarden','eye_undertide','eye_unblinking']
NAMES=dict(zip(KINDS,['Silt Drifter','Veil Adept','Glassjaw Lurker','The Lenswarden','The Undertide Sibyl','The Unblinking Eye']))
W=H=96
AX,AY=48,90
KIND_FRAMES={k:(176,172,88,164) for k in KINDS}
SCALE=dict(eye_drifter=.86,eye_adept=.85,eye_lurker=.88,eye_lenswarden=.84,eye_undertide=.90,eye_unblinking=.96)
CLIPS={'idle':(6,6),'walk':(10,8),'attack':(12,8),'hurt':(10,4),'die':(8,8)}
FLYING=('eye_drifter','eye_unblinking')
STRICT=True
BAD=[]
LOWEST={}
def kind_frame(kind):return kindframe.check_frame(*KIND_FRAMES[kind])
class Painter(BasePainter):
    def __init__(self,kind):
        self.w,self.h,self.ax,self.ay=kind_frame(kind)
        self.S=SCALE[kind]
        self.im=Image.new('P',(self.w,self.h),0);self.d=ImageDraw.Draw(self.im)
        self.cx=self.ax;self.ay=115
    def pos(self,x,y):return round(self.cx+x*self.S),round(self.ay-y*self.S)
    def ellipse(self,x,y,rx,ry,col):super().ellipse(x,y,rx*self.S,ry*self.S,col)
    def line(self,pts,col,width=1):super().line(pts,col,max(1,round(width*self.S)))
    def ball(self,x,y,rx,ry,ramp,ang=0.):super().ball(x,y,rx*self.S,ry*self.S,ramp,ang)

def beats(clip,n):
    w=(.05,.58,1.,.38,0,0,0,0)[n] if clip=='attack' else 0
    s=(0,0,0,.68,1.,.58,.20,.025)[n] if clip=='attack' else 0
    d=(0,.08,.22,.40,.60,.78,.92,1.)[n] if clip=='die' else 0
    ph=n*math.pi/4+.31
    b=(1-math.cos(n*math.pi/3+.3))*.7 if clip=='idle' else 0
    return w,s,d,ph,b

def setup(kind,clip,n,pivot,angle=0):
    a=Painter(kind);w,s,d,ph,b=beats(clip,n)
    r=L.Rig(a,*pivot,angle*d+((-.10,-.04,.035,.01)[n] if clip=='hurt' else 0))
    return a,r,w,s,d,ph,b

def drifter(clip,n):
    a,r,w,s,d,ph,b=setup('eye_drifter',clip,n,(0,40),-.18)
    x=18*s-7*w;y=63+b+8*w-7*s-35*d
    # Curled, attached tentacles support the drained mantle at the end of death.
    for i in range(6):
        xx=x-17+i*6; wave=math.sin(ph+i*.8)*2*(1-d)
        r.taper([(xx,y-7),(xx-3*w+7*s,y-20+4*d),(xx+wave+13*s,y-33+15*d)],TEAL,4,1.5)
    r.ball(x,y,23*(1+.15*d),18*(1-.65*d),TEAL,-.1)
    r.ball(x-2,y+11-6*d,21,13*(1-.6*d),AZURE,.05)
    r.line([(x-17,y+17-6*d),(x-6,y+19-8*d),(x+7,y+16-8*d)],TEAL[-1],2)
    # A sideways crescent set below a heavy overhang, unlike any other face here.
    if d<.5:
        r.ball(x+6,y+2,10,6,PEARL)
        r.ball(x+3,y+5,10,5,TEAL)
        r.ellipse(x+10,y+1,2,3,OUTLINE);r.ellipse(x+9,y+3,1,1,WHITE)
        r.line([(x-4,y+8),(x+17,y+4)],AZURE[0],3)
    else:r.line([(x-2,y+1),(x+14,y-1)],AZURE[0],2)
    r.poly([(x+5,y-8),(x+15,y-8),(x+10,y-14+5*d)],OUTLINE)
    r.poly([(x+12,y-7),(x+15,y-7),(x+12,y-11)],BONE[-1])
    return a

def lurker(clip,n):
    a,r,w,s,d,ph,b=setup('eye_lurker',clip,n,(0,15),-.16)
    cy=18+b-5*w-8*d
    for i,xx in enumerate((-21,-11,9,18)):
        step=math.sin(ph+i*1.9)*4 if clip=='walk' else 0
        lift=max(0,math.sin(ph+i*1.9))*4 if clip=='walk' else 0
        r.limb([(xx,cy),(xx+3+6*d,9+lift),(xx+step+6*s-9*d,2+lift+4*d)],VIOLET,4)
        r.ball(xx+step+6*s-9*d,2+lift+4*d,5,2,VIOLET)
    r.taper([(-23,cy),(-33,cy+3),(-39,cy+8+math.sin(ph)*(1-d)*2)],VIOLET,7,1)
    r.ball(-4,cy,24,12,VIOLET)
    for i in range(5):
        xx=-22+i*8
        r.poly([(xx,cy+8),(xx+3,cy+18-4*d),(xx+8,cy+10)],AZURE[2],OUTLINE)
        r.line([(xx+3,cy+15-3*d),(xx+6,cy+11)],AZURE[-1],1)
    hx=22+19*s-9*w;hy=cy+5+4*w
    r.limb([(12,cy),(hx-3,hy)],VIOLET,12)
    r.ball(hx,hy,13,10,VIOLET)
    # Unequal stalked pin eyes; glass jaw remains hinged to the cheek through the bite.
    for i,(dx,h) in enumerate(((-6,12),(5,7))):
        r.limb([(hx+dx,hy+5),(hx+dx-2,hy+h)],VIOLET,2)
        r.ball(hx+dx-2,hy+h,4-i,3.5-i,AMBER)
        if d<.4:
            r.ellipse(hx+dx-1,hy+h,1.2,2-i*.4,OUTLINE);r.ellipse(hx+dx-2,hy+h+1,1,1,WHITE)
        else:r.line([(hx+dx-4,hy+h),(hx+dx,hy+h-1)],OUTLINE,1)
    gap=2+10*s+3*w+3*d
    r.poly([(hx,hy-4),(hx+19,hy-4),(hx+16,hy-5-gap),(hx-2,hy-6-gap)],OUTLINE)
    r.limb([(hx-2,hy-3),(hx+7,hy-8-gap),(hx+16,hy-6-gap)],AZURE,3)
    for xx in (hx+3,hx+10,hx+16):r.poly([(xx-1,hy-4),(xx+2,hy-4),(xx,hy-10)],PEARL[-1])
    r.line([(hx+2,hy-6-gap),(hx+13,hy-6-gap)],PEARL[-1],1)
    if d>.4:r.line([(hx+6,hy-4-gap),(hx+9,hy-9-gap),(hx+12,hy-5-gap)],AZURE[0],1)
    return a

def adept(clip,n):
    a,r,w,s,d,ph,b=setup('eye_adept',clip,n,(0,12),-.28)
    cy=27+b-12*d;hx=-2-5*w+7*s;hy=52+b-25*d
    hem=1+2*d
    r.poly([(-14,hem),(-11,cy+11),(4,cy+12),(15+8*d,hem)],TEAL[0],OUTLINE)
    r.ball(0,cy,12+7*d,19*(1-.5*d),TEAL)
    for i,xx in enumerate((-11,-4,4,11)):
        r.limb([(xx*.6,cy+5),(xx+math.sin(ph+i)*1.5,hem+4)],AZURE,3)
    # Long hood, with a black vertical void and two unequal offset pale pinpoints.
    r.poly([(hx-12,hy-10),(hx-12,hy+7),(hx-2,hy+15),(hx+10,hy+6),(hx+14,hy-17)],TEAL[1],OUTLINE)
    r.poly([(hx-10,hy+8),(hx-23,hy-20-4*d),(hx-15,cy-3),(hx-6,hy-6)],TEAL[2],OUTLINE)
    r.line([(hx-13,hy-4),(hx-20,hy-18)],TEAL[-1],1)
    r.ball(hx,hy,10,12,TEAL)
    r.poly([(hx-5,hy+7),(hx+6,hy+4),(hx+5,hy-10),(hx-3,hy-8)],OUTLINE)
    if d<.6:
        r.ellipse(hx+1,hy+1,1,1,WHITE);r.ellipse(hx+4,hy-3,1,1,AZURE[-1])
    # The conjuring lens stays in both hands throughout recovery and drops with the cloth.
    handx=15+23*s-11*w;handy=cy+5+13*w-7*s
    for side in (-1,1):r.limb([(side*9,cy+8),(side*13+7*s,cy+1+8*w),(handx,handy+side*3)],TEAL,4)
    r.ball(handx,handy,7*(1-.3*d),7*(1-.3*d),GOLD)
    r.ball(handx+1,handy+1,4*(1-.3*d),4*(1-.3*d),AZURE)
    r.line([(handx-2,handy+3),(handx+2,handy+4)],PEARL[-1],1)
    if d>.4:r.line([(handx,handy+4),(handx-2,handy),(handx+2,handy-3)],GOLD[0],1)
    return a

def warden(clip,n):
    a,r,w,s,d,ph,b=setup('eye_lenswarden',clip,n,(0,12),-.30)
    cy=25+b+3*w-10*d;hx=-2+8*s-4*w;hy=49+b-20*d
    for i,x in enumerate((-10,11)):
        step=math.sin(ph+i*math.pi)*4 if clip=='walk' else 0
        r.limb([(x,cy),(x+8*d,11),(x+step+8*d,3+3*d)],BROWN,6)
        r.ball(x+step+8*d,3+3*d,8,3.5,GOLD)
    r.ball(0,cy+5,16,18*(1-.3*d),GOLD)
    r.ball(0,cy+7,8,10,BROWN)
    for x in (-17,16):r.ball(x,cy+13,9,7,GOLD)
    r.ball(hx,hy,13,11,GOLD)
    r.poly([(hx-13,hy+4),(hx+14,hy+4),(hx+12,hy-2),(hx-12,hy-2)],GOLD[0],OUTLINE)
    # A single square light aperture, deliberately mechanical and eyeless.
    if d<.8:
        r.poly([(hx+3,hy+3),(hx+7,hy+3),(hx+7,hy),(hx+3,hy)],AZURE[-1] if d<.4 else AZURE[1])
    r.line([(hx-11,hy+7),(hx+10,hy+7)],GOLD[-1],2)
    r.poly([(hx-5,hy+11),(hx-3,hy+17),(hx+2,hy+11)],GOLD[2],OUTLINE)
    # Heavy lens shield tips in death instead of squashing.
    sx=-35+19*s+4*w;sy=cy+2-8*d
    r.limb([(-14,cy+9),(sx,sy)],BROWN,5)
    r.ball(sx,sy,13,16*(1-.7*d),GOLD,.25*d)
    r.ball(sx,sy,9,12*(1-.7*d),AZURE,.25*d)
    r.line([(sx-4,sy+7*(1-d)),(sx,sy+9*(1-d))],PEARL[-1],2)
    handx=29+23*s-8*w;handy=cy+6+19*w-9*s
    r.limb([(14,cy+10),(17+8*s,cy),(handx,handy)],GOLD,5)
    r.limb([(handx-2,handy-17+10*d),(handx+4,handy+10)],GOLD,3)
    r.ball(handx+5,handy+15,7,7,GOLD)
    r.ball(handx+5,handy+15,4,4,AZURE)
    if d>.3:r.line([(-7,cy+13),(0,cy+7),(-4,cy+1)],GOLD[0],2)
    return a

def sibyl(clip,n):
    a,r,w,s,d,ph,b=setup('eye_undertide',clip,n,(0,13),-.16)
    cy=27+b-13*d;hx=1+6*s-5*w;hy=52+b-27*d
    # The water-filled robe spreads into an attached pool, with cloth still visible.
    r.ball(0,3,15+13*d,3+3*d,TEAL)
    r.poly([(-14-7*d,3),(-10,cy+13),(9,cy+13),(16+8*d,3)],TEAL[1],OUTLINE)
    r.ball(0,cy,12+5*d,18*(1-.5*d),TEAL)
    for j in range(4):
        yy=cy-8+j*7
        r.line([(-10,yy),(-3,yy-2),(5,yy),(11,yy+2)],AZURE[2],2)
    for i in range(5):
        r.taper([(hx-5+i*3,hy+6),(hx-15-i*2-7*w,hy+5-i*4),(hx-18-i*2+math.sin(ph+i)*3,hy-14-i*4+8*d)],TEAL,4,1.2)
    r.ball(hx,hy,11,12,PEARL)
    # Three unequal diamond pupils on a diagonal, with a pinched frown.
    for i,(dx,dy,sz) in enumerate(((-5,-1,2.5),(0,4,3.1),(5,8,2))):
        r.ball(hx+dx,hy+dy,sz+1,sz,TEAL)
        if d<.65:
            r.poly([(hx+dx,hy+dy+2),(hx+dx+1,hy+dy),(hx+dx,hy+dy-2),(hx+dx-1,hy+dy)],OUTLINE)
            r.ellipse(hx+dx-1,hy+dy+1,1,1,WHITE)
        else:r.line([(hx+dx-2,hy+dy),(hx+dx+2,hy+dy-1)],TEAL[0],1)
    r.line([(hx-3,hy-8),(hx+2,hy-6),(hx+6,hy-9)],TEAL[0],2)
    for side in (-1,1):
        xx=side*(16+8*w)+23*s;yy=cy+6+11*w-7*s
        r.limb([(side*9,cy+10),(xx-3,yy),(xx+4,yy+4)],TEAL,4)
        r.ball(xx+4,yy+4,3,3,PEARL)
        # Attached crest extends the cast without an orbiting glyph.
        if s>.05:r.taper([(xx+4,yy+4),(xx+9+12*s,yy+7),(xx+12+18*s,yy+3)],AZURE,4*s,1)
    return a

def unblinking(clip,n):
    a,r,w,s,d,ph,b=setup('eye_unblinking',clip,n,(0,40),-.16)
    x=15*s-6*w;y=60+b+7*w-4*s-29*d
    # Cyan blades belong to an amber ring. On death they settle into a broken low ring.
    for i in range(10):
        ang=i*math.tau/10+.12+math.sin(ph)*.025*(1-d)
        bx=x+math.cos(ang)*24;by=y+math.sin(ang)*24
        tx=x+math.cos(ang)*34+10*s;ty=y+math.sin(ang)*34
        ty=ty*(1-d)+(y-16+abs(math.sin(ang))*6)*d
        by=by*(1-d)+(y-14)*d
        r.poly([(bx-5,by-5),(tx,ty),(bx+5,by+5)],AZURE[2],OUTLINE)
        r.line([(bx,by),(tx-1,ty+1)],AZURE[-1],1)
    for i in range(5):
        xx=x-16+i*8
        r.taper([(xx,y-16),(xx+math.sin(ph+i)*(1-d)*2,y-27+5*d),(xx+6*d,y-36+17*d)],BROWN,3,1)
    r.ball(x,y,27,26*(1-.35*d),GOLD)
    r.ball(x,y,22,21*(1-.4*d),PEARL)
    # Round radial iris and small star pupil; this enemy never blinks alive.
    r.ball(x+3,y,12+4*s-3*d,13-4*d,AMBER if d<.65 else SLATE)
    for i in range(14):
        ang=i*math.tau/14
        r.line([(x+3+math.cos(ang)*6,y+math.sin(ang)*6),(x+3+math.cos(ang)*10,y+math.sin(ang)*11*(1-.3*d))],GOLD[1] if d<.65 else SLATE[1],1)
    pts=[]
    for i in range(10):
        ang=i*math.pi/5;rad=(5 if i%2==0 else 2)*(1-.5*d)
        pts.append((x+3+math.cos(ang)*rad,y+math.sin(ang)*rad))
    r.poly(pts,OUTLINE)
    r.ellipse(x,y+5-2*d,2,2,WHITE if d<.7 else SLATE[-1])
    for i in (-1,0,1):r.taper([(x+i*11,y+22-6*d),(x+i*14,y+31-13*d)],BROWN,2,1)
    return a

DRAW=dict(zip(KINDS,[drifter,adept,lurker,warden,sibyl,unblinking]))


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
        np.savez_compressed(ROOT / f'scripts/eye_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/eye_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'cathedral_{kind}.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    live = json.loads(MANIFEST.read_text())
    unrelated = [k for k in live['kinds'] if k not in KINDS]
    assert len(unrelated) == 140
    villagers = {k: (live['sprites'].get(k), live['tops'].get(k), live.get('kindFrames', {}).get(k)) for k in unrelated}
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
    for k in unrelated:
        assert (meta['sprites'].get(k), meta['tops'].get(k), meta.get('kindFrames', {}).get(k)) == villagers[k]
    for kind, atlas in atlases.items():
        dest = atlas_path(kind)
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames and derived health-bar tops.', flush=True)


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
