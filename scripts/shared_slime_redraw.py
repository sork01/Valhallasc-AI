#!/usr/bin/env python3
"""Shared/event enemy PixelFlow pipeline. Build preserves sources; export preserves editor edits."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import make_crag_sprites as old
import kindframe
from astral_slime_redraw import Painter as BasePainter,PALETTE,OUTLINE,EYE_WHITE
from lapis_slime_redraw import Rig
import shared_slime_models as models
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
OUT=ROOT/'test-results/shared-slime'
REGISTRY=ROOT/'scripts/shared_slime_sources.txt'
BANKS=dict(ember_firelord='cathedral',hollow_rider='halloween',grinch='christmas',bloomwarden='easter',birchcrown='solstice',briarheart='valentines',starrocketeer='newyear')
# Dedicated materials keep basalt, pale birch and sack cloth visually separate.
PALETTE=PALETTE[:]
for name,colors in dict(BASALT=['#161a20','#30363d','#515b63','#78868a','#a7b2ab'],BIRCH=['#4e5146','#858878','#b9bcaa','#e0e1ce','#fff3d4'],SACK=['#34312c','#555041','#7b7056','#a1916c','#c6b48c']).items():
    start=len(PALETTE);PALETTE.extend(colors);setattr(models,name,list(range(start,start+5)))
assert len(PALETTE)<=256 and len(set(PALETTE))==len(PALETTE)
KINDS=list(BANKS)
NAMES=dict(ember_firelord='Firelord',hollow_rider='Hollow Rider',grinch='Grinch',bloomwarden='Bloomwarden',birchcrown='Birchcrown',briarheart='Briarheart',starrocketeer='Starfire Rocketeer')
CLIPS={'idle':(6,6),'walk':(10,8),'attack':(12,8),'hurt':(10,4),'die':(8,8)}
KIND_FRAMES={k:(176,172,64,164) for k in KINDS}
# Native art retains each original idle size; frames add room for the arcs/falls.
SCALE=dict(ember_firelord=(.87,.74),hollow_rider=(.58,.66),grinch=(.68,.78),bloomwarden=(.63,.86),birchcrown=(.54,.71),briarheart=(.80,.80),starrocketeer=(.92,.73))

class Painter(BasePainter):
    def __init__(self,kind):
        self.w,self.h,self.ax,self.ay=KIND_FRAMES[kind]
        self.sx,self.sy=SCALE[kind];self.cx=self.ax;self.base=125
        self.im=Image.new('P',(self.w,self.h),0);self.d=ImageDraw.Draw(self.im)
    def pos(self,x,y):return round(self.cx+x*self.sx),round(self.base-y*self.sy)
    def ellipse(self,x,y,rx,ry,col):super().ellipse(x,y,rx*self.sx,ry*self.sy,col)
    def line(self,pts,col,width=1):super().line(pts,col,max(1,round(width*(self.sx+self.sy)/2)))
    def ball(self,x,y,rx,ry,ramp,ang=0):
        px,py=self.pos(x,y);rx*=self.sx;ry*=self.sy;radius=max(rx,ry);c,s=math.cos(ang),math.sin(ang)
        for yy in range(max(0,math.floor(py-radius)),min(self.h,math.ceil(py+radius)+1)):
            for xx in range(max(0,math.floor(px-radius)),min(self.w,math.ceil(px+radius)+1)):
                dx,dy=xx-px,yy-py;u,v=(dx*c-dy*s)/rx,(dx*s+dy*c)/ry;rr=u*u+v*v
                if rr>1:continue
                nx,ny=u*c+v*s,-u*s+v*c
                value=max(0,min(.999,.23+.71*(-.4*nx-.54*ny+.74*math.sqrt(max(0,1-rr)))))
                shade=min(len(ramp)-1,round(value*(len(ramp)-1)))
                if rr>.93 and nx+ny>.2:shade=0
                self.im.putpixel((xx,yy),ramp[shade])


def setup(kind,clip,n,pivot,angle=0):
    w=(.025,.55,1.,.30,0,0,0,0)[n] if clip=='attack' else 0
    s=(0,0,0,.68,1.,.45,.13,.005)[n] if clip=='attack' else 0
    d=(0,.055,.17,.34,.54,.75,.91,1.)[n] if clip=='die' else 0
    ph=n*math.pi/4+.31
    b=(1-math.cos(n*math.pi/3+.3))*.65 if clip=='idle' else math.sin(ph)*1.3 if clip=='walk' else 0
    a=Painter(kind);r=Rig(a,*pivot,angle*d+((-.09,-.03,.035,.01)[n] if clip=='hurt' else 0))
    return a,r,w,s,d,ph,b


def frame(kind,clip,n):
    a=getattr(models,kind)(setup,clip,n);grid=np.array(a.im)
    # Guard raw canvas BEFORE grounding; rolling may otherwise conceal clipping.
    assert grid.any() and not(grid[0].any() or grid[-1].any() or grid[:,0].any() or grid[:,-1].any()),(kind,clip,n,'raw clipping')
    low=np.nonzero(grid.any(axis=1))[0].max();shift=KIND_FRAMES[kind][3]-low
    assert not grid[max(0,len(grid)-shift):].any() if shift>0 else True
    grid=np.roll(grid,shift,axis=0)
    if clip=='hurt' and n==0:grid[grid>0]=EYE_WHITE
    kindframe.check_bounds(old.rgba(grid,PALETTE).getbbox(),*KIND_FRAMES[kind][:2])
    return grid


def frames(kind):
    data={c:np.array([frame(kind,c,n) for n in range(count)]) for c,(_,count) in CLIPS.items()}
    for c,grids in data.items():
        distinct=len({g.tobytes() for g in grids})
        assert distinct>=min(4,len(grids)),(kind,c,'static clip',distinct)
        if c in ('attack','die'):assert distinct==8,(kind,c,'eight different poses',distinct)
    return data


def registry():return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
def manifest_path(kind):return ASSETS/f'{BANKS[kind]}.txt'
def atlas_path(kind):return ASSETS/f'{BANKS[kind]}_{kind}.png'
def kind_frame(kind):return KIND_FRAMES[kind]
def rgba(grid,palette=PALETTE):return old.rgba(grid,palette)
def cel_grid(cel,w,h):
    if 'rle' in cel:
        r=cel['rle'];return np.repeat(np.array(r[1::2],dtype=np.uint8),r[0::2]).reshape(h,w)
    return np.array(cel['grid'],dtype=np.uint8)


def write_frames(sid,data):
    offset=0
    for c,(_,count) in CLIPS.items():
        for n in range(count):old.api('draw',dict(sprite_id=sid,frame=offset+n,ops=[dict(op='grid',rows=data[c][n].tolist(),x=0,y=0,layer=0)]))
        offset+=count


def build(kinds=None):
    assert '--replace' not in sys.argv,'Use refresh KIND to overwrite candidate editor frames'
    saved=registry()
    for k in kinds or KINDS:
        if k in saved:
            sp=old.api('get?sprite_id='+saved[k])['sprite'];assert (sp['width'],sp['height'],len(sp['frames']))==(*KIND_FRAMES[k][:2],34)
            print(k,'preserved existing source',saved[k],flush=True);continue
        data=frames(k);np.savez_compressed(ROOT/f'scripts/shared_slime_{k}_raw.npz',**data)
        sid=old.api('create',dict(name=f'valhallasc_shared_slime_{k}_all',width=KIND_FRAMES[k][0],height=KIND_FRAMES[k][1],frames=34,layers=1,fps=10,palette=PALETTE,persist=True))['sprite_id']
        # Persist provenance immediately; a failed draw can be recovered with explicit refresh.
        saved[k]=sid;REGISTRY.write_text(json.dumps(saved,indent=2)+'\n')
        write_frames(sid,data);print(k,sid,'34 native frames saved',flush=True)


def refresh(kinds):
    assert kinds and all(k in KINDS for k in kinds),'Name candidate kinds explicitly'
    for k in kinds:
        data=frames(k);write_frames(registry()[k],data)
        np.savez_compressed(ROOT/f'scripts/shared_slime_{k}_raw.npz',**data)
        print('Refreshed',k,flush=True)


def export():
    saved=registry();assert set(saved)==set(KINDS)
    proof={}
    for k in KINDS:
        path=manifest_path(k);meta=json.loads(path.read_text());before=json.loads(json.dumps(meta))
        w,h,ax,ay=KIND_FRAMES[k];sp=old.api('get?sprite_id='+saved[k])['sprite'];assert (sp['width'],sp['height'],len(sp['frames']))==(w,h,34)
        atlas=Image.new('RGBA',(w*8,h*5));rows=[];offset=0
        for row,(clip,(fps,count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip]==dict(fps=fps,n=count,row=row,editorStart=offset)
            for n in range(count):
                cell=rgba(cel_grid(sp['frames'][offset+n]['cels'][0],w,h),sp['palette']);bounds=cell.getbbox();kindframe.check_bounds(bounds,w,h)
                atlas.alpha_composite(cell,(n*w,row*h));rows.append(dict(clip=clip,n=n,sha256=hashlib.sha256(cell.tobytes()).hexdigest(),bounds=bounds))
            offset+=count
        meta['sprites'][k]=saved[k];meta.setdefault('tops',{})[k]=kindframe.top_of([r['bounds'] for r in rows if r['clip']=='idle'],ay)
        kindframe.set_kind_frame(meta,k,w,h,ax,ay)
        # Manifest override detaches Firelord from its legacy Eldmarr borrower without changing world rules.
        if k=='ember_firelord':meta.setdefault('atlases',{})[k]=f'cathedral_{k}.png'
        for key in ('sprites','tops','kindFrames','atlases'):
            a={x:v for x,v in before.get(key,{}).items() if x!=k};b={x:v for x,v in meta.get(key,{}).items() if x!=k};assert a==b,(k,key,'unrelated records')
        atlas.save(atlas_path(k),optimize=True);path.write_text(json.dumps(meta,indent=2)+'\n')
        proof[k]=dict(source=saved[k],frames=rows,atlasSha256=hashlib.sha256(atlas_path(k).read_bytes()).hexdigest())
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'editor-export-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('Exported 238 saved editor frames; unrelated manifest records preserved')


def verify():
    for k in KINDS:
        meta=json.loads(manifest_path(k).read_text());w,h,ax,ay=KIND_FRAMES[k];assert kindframe.frame_of(meta,k)==(w,h,ax,ay)
        sp=old.api('get?sprite_id='+registry()[k])['sprite'];atlas=Image.open(atlas_path(k)).convert('RGBA');assert atlas.size==(w*8,h*5)
        offset=0
        for row,(clip,(_,count)) in enumerate(CLIPS.items()):
            for n in range(count):assert np.array_equal(np.array(rgba(cel_grid(sp['frames'][offset+n]['cels'][0],w,h),sp['palette'])),np.array(atlas.crop((n*w,row*h,(n+1)*w,(row+1)*h)))),(k,clip,n)
            offset+=count
        print(k,'34 saved editor/export frames match')


def preview():
    OUT.mkdir(parents=True,exist_ok=True);im=Image.new('RGBA',(6*192,len(KINDS)*184),'#202a3a');d=ImageDraw.Draw(im)
    for row,k in enumerate(KINDS):
        data=frames(k)
        for col,(c,n) in enumerate([('idle',0),('attack',2),('attack',4),('attack',7),('die',4),('die',7)]):
            im.alpha_composite(rgba(data[c][n]),(col*192,row*184))
        d.text((4,row*184+170),NAMES[k],fill='white')
    im.save(OUT/'poses.png');print(OUT/'poses.png')


if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    if cmd=='refresh':refresh(sys.argv[2:])
    else:dict(preview=preview,build=build,export=export,verify=verify)[cmd]()
