#!/usr/bin/env python3
"""Bifrost slime-style native PixelFlow sources; preview | build | export | verify.

Art components keep their dimensions: jointed legs, crystal fragments, manta
fins, separate armour and hinged feathers. Export preserves saved editor edits.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
from wyrd_slime_v1_redraw import Painter, motion, mix, PALETTE as BASE_PALETTE

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
OUT=ROOT/'test-results/bifrost-slime'
REGISTRY=ROOT/'scripts/bifrost_slime_sources.txt'
PREFIX='valhallasc_bifrost_slime_style_'
KINDS=['galehound','prismgolem','skyray','einherjar','thunderroc']
NAMES=dict(galehound='Galehound',prismgolem='Prism Golem',skyray='Skyray',einherjar='Hollow Einherjar',thunderroc='Thunderroc')
W=H=96
AX,AY=48,90
CLIPS=old.CLIPS
PALETTE=BASE_PALETTE[:]+['#223d73','#426cc1','#78a8ee','#badcff','#edf7ff',
                       '#6a3318','#a85c29','#da9347','#f5c878','#fff0c3']
FUR=list(range(45,50));PLATE=list(range(10,15));PURPLE=list(range(15,20))
TEAL=list(range(20,25));GOLD=list(range(25,30));BONE=list(range(5,10))
BLUE=list(range(55,60));BROWN=list(range(60,65))


def bolt(a,x,y,s=1):
    a.poly([(x-2*s,y+7*s),(x+2*s,y+7*s),(x,y+1*s),(x+4*s,y+2*s),(x-1*s,y-7*s),(x,y-1*s),(x-4*s,y-2*s)],28)
    a.line([(x,y+5*s),(x-1*s,y),(x+1*s,y)],29,1)


def galehound(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=45+recoil+lunge*.5)
    y=32+bob*.5-fall*18
    # Hind legs have a bent stifle/hock; far legs land higher and are narrower.
    for far in (True,False):
        ramp=FUR[:3] if far else FUR
        depth=7 if far else 0
        for front in (False,True):
            phase=(0 if front else math.pi)+(math.pi if far else 0)
            swing=math.sin(n*math.pi/4+phase) if clip=='walk' else 0
            step=swing*3; lift=max(0,swing)*3
            if front:
                points=[(9+depth,y-4),(8+depth+step*.2,y-12),(12+depth+step,10+lift),(13+depth+step,5+3*far+lift)]
                folded=[(9+depth,12),(15+depth,9),(10+depth,7),(17+depth,5+3*far)]
            else:
                points=[(-21+depth,y-2),(-14+depth+step*.2,y-12),(-24+depth+step,11+lift),(-23+depth+step,5+3*far+lift)]
                folded=[(-21+depth,12),(-13+depth,9),(-24+depth,7),(-20+depth,5+3*far)]
            points=[(mix(x,fx,fall),mix(yy,fy,fall)) for (x,yy),(fx,fy) in zip(points,folded)]
            a.limb(points[:3],ramp,2 if far else 4)
            a.limb(points[2:],ramp,2 if far else 3)
            a.ball(*points[-1],2.5 if far else 3.5,1.7 if far else 2,FUR)
    # Flowing tapered cloud tail, separate from the solid animal anatomy.
    for j in range(3):
        tx=-24-j*4;ty=y+5+j*4+math.sin(n*.8+j)*1.5-fall*j*3
        a.ball(tx,ty,7-j,4-j*.7,FUR)
        a.poly([(tx-2,ty+3),(tx-9,ty+2+j),(tx-4,ty-2)],47+j%2)
    a.ball(-5,y,23,14,FUR);a.ball(-12,y+7,10,4,FUR[1:])
    for j in range(4):
        x=-23+j*9
        a.poly([(x,y+10),(x+2,y+21-j%2*3),(x+11,y+11)],46+j%3)
        a.ball(x+4,y+12,6,4,FUR)
    hx=21+fall*4;hy=y+10-fall*4
    a.ball(11,y+5,11,12,FUR);a.ball(hx,hy,14,13,FUR)
    a.poly([(hx-11,hy+7),(hx-12,hy+25),(hx-1,hy+12)],46)
    a.poly([(hx+3,hy+10),(hx+9,hy+22),(hx+11,hy+5)],47)
    a.poly([(hx-9,hy+11),(hx-10,hy+20),(hx-5,hy+12)],48)
    a.face(hx,hy,clip,n,.78)
    a.ball(hx+7,hy-7,8,4,FUR);a.ellipse(hx+11,hy-5,2,1.5,10)
    if clip!='die' or n<4:
        bolt(a,-12,y+5,.65);bolt(a,3,y+7,.5)
    return a


def shard(a,x,y,rx,ry,ramp):
    # Facets preserve a crystal silhouette, with the slime's rounded glossy core.
    a.poly([(x-rx,y),(x-rx*.55,y+ry),(x+rx*.4,y+ry*.9),(x+rx,y-ry*.15),(x+rx*.35,y-ry),(x-rx*.55,y-ry*.8)],ramp[0])
    a.ball(x,y,rx*.78,ry*.77,ramp)
    a.poly([(x-rx*.55,y+ry*.6),(x-rx*.15,y+ry*.8),(x+rx*.25,y+ry*.5),(x-rx*.15,y+ry*.35)],ramp[-1])


def prismgolem(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    slump=fall
    y=37+bob*.35-slump*19
    for sg in (-1,1):
        foot=(sg*(12+slump*9)+stride*sg,5+max(0,stride*sg)*(1-slump))
        a.limb([(sg*10,y-7),(sg*(14+slump*5),17-slump*7),foot],PURPLE,8)
        shard(a,*foot,9,5,PURPLE)
    shard(a,0,y,21,20,PURPLE)
    for j,ramp in enumerate((GOLD,TEAL,BLUE)):
        shard(a,-10+j*10,y+2-j%2*6,5,8,ramp)
    for sg in (-1,1):
        hand=(sg*(29+slump*6),25+(max(0,lunge)*2 if sg>0 else bob)-slump*15)
        a.limb([(sg*18,y+10),(sg*(25+slump*5),y-2),hand],PURPLE,7)
        shard(a,*hand,9,9,TEAL if sg>0 else BLUE)
        shard(a,sg*(18+slump*5),y+15-slump*7,10,9,PURPLE)
        a.poly([(sg*20-4,y+20),(sg*20,y+31),(sg*20+4,y+20)],23 if sg>0 else 58)
    hx=slump*11;hy=63+bob*.35-slump*43
    shard(a,hx,hy,16,15,PURPLE)
    a.face(hx,hy,clip,n,.9)
    for j,ramp in enumerate((GOLD,TEAL,BLUE)):
        shard(a,hx-9+j*9,hy+14+4*(j%2),3,7,ramp)
    if clip=='die':
        a.line([(-9,y+13),(-3,y+7),(-7,y+1),(4,y-9)],15,2)
        if n>=2:
            for j,ramp in enumerate((TEAL,GOLD,BLUE,PURPLE)):
                shard(a,-26+j*17+(n-2)*(.5 if j%2 else -.5),max(5,40-j%2*7-(n-2)*6),4,5,ramp)
        if n>=4:a.line([(hx-10,hy+8),(hx-3,hy+2),(hx-7,hy-7)],15,2)
    return a


def skyray(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=46+recoil)
    y=45+bob-fall*30
    flap=math.sin(n*math.pi/4)*10 if clip=='walk' else bob*1.5
    if clip=='attack':flap=[2,8,12,3,-8,-5,-2,0][n]
    # A true manta: smooth triangular pectoral fins, no feather/bird silhouette.
    for far in (True,False):
        sg=1 if far else -1
        tipx=sg*(38-fall*13);tipy=y+9+(flap if far else -flap)*(1-fall)-fall*12
        a.poly([(sg*6,y+12),(sg*20,y+15),(tipx,tipy),(tipx-sg*4,tipy-4),(sg*24,y-12+fall*6),(sg*5,y-10)],55 if far else 56)
        a.poly([(sg*7,y+9),(sg*21,y+11),(tipx-sg*4,tipy-1),(sg*22,y-6),(sg*7,y-7)],56 if far else 57)
        a.line([(sg*10,y+5),(sg*21,y+1),(tipx-sg*5,tipy-2)],58,1)
    # Long whipping tail tapers to a single point; it coils down as fins settle.
    tail=[(-9,y-7),(-21,y-16),(-30-fall*4,y-14-fall*3),(-35,y-5-fall*11),(-31,y+1-fall*18)]
    a.line(tail,55,4);a.line(tail[:-1],57,2)
    a.poly([(tail[-2][0]-1,tail[-2][1]),tail[-1],(tail[-2][0]+1,tail[-2][1])],58)
    a.poly([(-12,y+7),(0,y+18),(15,y+8),(12,y-10),(0,y-16),(-12,y-9)],55)
    a.ball(0,y+2,13,13,BLUE);a.ball(-4,y+8,6,3,BLUE[1:])
    a.face(1,y+3,clip,n,.75)
    for sg in (-1,1):
        a.poly([(sg*7,y+9),(sg*10,y+24-fall*10),(sg*15,y+21-fall*10),(sg*13,y+8)],57)
        a.line([(sg*9,y-8),(sg*10,y-12)],58,1)
    for x,dy in [(-5,12),(5,13),(0,-7)]:a.ellipse(x,y+dy,1.4,1,59)
    if clip!='die' or n<4:bolt(a,0,y-7,.45)
    return a


def einherjar(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=44+recoil)
    y=37+bob*.35-fall*24
    # Falling empty plates retain their size while the inner spirit departs.
    for sg in (-1,1):
        foot=(sg*(10+fall*8)+stride*sg,5+max(0,stride*sg)*(1-fall))
        a.limb([(sg*8,y-6),(sg*(10+fall*6),17-fall*9),foot],PLATE,6)
        a.ball(*foot,8,4,PLATE)
    a.poly([(-13,y+9),(13,y+9),(20+fall*4,7),(-20-fall*4,7)],16)
    a.ball(0,y,16,17,PLATE);a.ball(-5,y+9,7,3,PLATE[1:])
    a.line([(-9,y-6),(9,y-6)],27,3)
    a.poly([(-4,y+5),(0,y+10),(4,y+5),(0,y-1)],22 if clip!='die' or n<4 else 11)
    for sg in (-1,1):a.ball(sg*(15+fall*5),y+12-fall*5,9,6,PLATE)
    # Far arm and round shield settle outward, the sword rotates flat.
    shield=(-23-fall*6,29+bob*.4-fall*18)
    a.limb([(-13,y+10),(-22,y),shield],PLATE,5)
    a.ball(*shield,11,14,PLATE);a.ball(*shield,8,11,GOLD)
    a.line([(shield[0],shield[1]-9),(shield[0],shield[1]+9)],13,2)
    a.line([(shield[0]-6,shield[1]),(shield[0]+6,shield[1])],13,2)
    hand=(23+fall*7,29+max(0,lunge)*2-fall*18)
    a.limb([(13,y+10),(21,y),hand],PLATE,5);a.ball(*hand,5,4,PLATE)
    angle=1.4-lunge*.19-fall*1.4
    dx,dy=math.cos(angle),math.sin(angle)
    end=(hand[0]+dx*13,hand[1]+dy*22)
    a.line([(hand[0]-dy*5,hand[1]+dx*5),(hand[0]+dy*5,hand[1]-dx*5)],28,3)
    a.limb([hand,end],PLATE,3)
    hx=fall*10;hy=61+bob*.35-fall*44
    a.ball(hx,hy,15,14,PLATE)
    a.ball(hx,hy-2,11,10,TEAL if clip!='die' or n<4 else PLATE[:2])
    if clip!='die' or n<5:a.face(hx,hy-1,clip,n,.85)
    a.poly([(hx-14,hy+2),(hx-13,hy+13),(hx+12,hy+13),(hx+14,hy+2),(hx+5,hy+5),(hx,hy+9),(hx-5,hy+5)],12)
    a.line([(hx,hy+12),(hx,hy-4)],14,2)
    for sg in (-1,1):
        a.poly([(hx+sg*10,hy+10),(hx+sg*20,hy+19),(hx+sg*19,hy+8),(hx+sg*12,hy+5)],7)
        a.line([(hx+sg*12,hy+10),(hx+sg*18,hy+16)],9,2)
    if clip!='die':
        a.poly([(hx-5,hy+14),(hx-3,hy+22+bob),(hx+2,hy+18),(hx+6,hy+14)],22)
        a.poly([(hx-2,hy+15),(hx-1,hy+20+bob),(hx+3,hy+15)],24)
    elif n<6:
        for j in range(3):
            xx=hx-10+j*9+math.sin(n+j)*2;yy=min(80,hy+18+n*6+j*3)
            a.poly([(xx-2,yy-3),(xx,yy+5),(xx+3,yy),(xx+1,yy-3)],22+j%3)
    return a


def thunderroc(clip,n):
    stride,bob,lunge,recoil,fall=motion(clip,n)
    a=Painter(cx=45+recoil)
    y=41+bob*.8-fall*24
    flap=math.sin(n*math.pi/4)*13 if clip=='walk' else bob*2
    if clip=='attack':flap=[4,12,16,-9,-12,-5,0,2][n]
    # Separate feather fingers hinge at wing roots, then fold over the fallen bird.
    for far in (True,False):
        root=(-10,y+6) if far else (3,y)
        tx=(-34 if far else -29)+fall*19
        ty=y+22+(flap if far else -flap)*(1-fall)-fall*20
        for j in range(5):
            a.poly([root,(tx+j*3,ty-j*6*(1-fall*.65)),(tx+5+j*3,ty-5-j*6*(1-fall*.65)),(root[0]+6,root[1]-7)],55+j%3)
            a.line([(tx+j*3+1,ty-j*6*(1-fall*.65)-1),(root[0],root[1])],57+j%2,1)
        a.ball(root[0]-3,root[1]+1,10,8,BLUE)
        if far:
            for j in range(3):a.poly([(-9,y-7),(-28+j*6,y-22+fall*10),(-17+j*6,y-23+fall*10),(4,y-7)],61+j%2)
            a.ball(0,y,18,16,BROWN);a.ball(-5,y+9,9,4,BROWN[1:])
    for sg in (-1,1):
        foot=(sg*7+fall*sg*5,11+max(0,stride*sg)*(1-fall))
        a.limb([(sg*5,y-10),(sg*(7+fall*4),19-fall*5),foot],GOLD,3)
        for j in range(3):
            a.line([(foot[0],foot[1]),(foot[0]-4+j*4,foot[1]-4+fall*3)],27+j%2,2)
    hx=16+max(0,lunge)*.6;hy=y+16-fall*8
    a.ball(hx,hy,14,13,FUR);a.ball(hx-4,hy+7,7,3,FUR[1:])
    for j in range(3):
        a.poly([(hx-11+j*5,hy+8),(hx-18+j*6,hy+24-j*2),(hx-3+j*5,hy+10)],55+j%3)
    a.eye(hx+2,hy,clip,n,1.05);a.ellipse(hx-5,hy-5,2.5,1.5,4)
    gap=max(0,lunge)*.5
    a.poly([(hx+8,hy-1),(hx+22,hy-5),(hx+18,hy-11),(hx+14,hy-6),(hx+8,hy-6)],27)
    a.poly([(hx+9,hy-7-gap),(hx+17,hy-9-gap),(hx+9,hy-10-gap)],28)
    if clip!='die' or n<4:
        bolt(a,-26+fall*7,y+13,.65);bolt(a,2,y+2,.65)
    if clip=='die' and n>=1:
        for j in range(3):
            xx=-24+j*16+n*.5;yy=max(5,48-j*4-n*5)
            a.poly([(xx-2,yy),(xx+1,yy+6),(xx+3,yy+2),(xx,yy-3)],57+j%2)
    return a


DRAW=dict(galehound=galehound,prismgolem=prismgolem,skyray=skyray,einherjar=einherjar,thunderroc=thunderroc)
def frame(kind,clip,n):
    grid=np.array(DRAW[kind](clip,n).im)
    if clip=='hurt' and n==0:grid[grid>0]=3
    assert grid.any(),(kind,clip,n,'empty')
    assert not(grid[0].any() or grid[-1].any() or grid[:,0].any() or grid[:,-1].any()),(kind,clip,n,'border')
    return grid


def rgba(grid,palette=PALETTE):return old.rgba(grid,palette)
def frames(kind):
    return {clip:np.array([frame(kind,clip,n) for n in range(count)]) for clip,(_,count) in CLIPS.items()}


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
        np.savez_compressed(ROOT/f'scripts/bifrost_slime_{kind}_raw.npz',**data[kind])
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
        dest=ASSETS/f'sky_{kind}.png';atlas.save(dest,optimize=True)
        proof[kind]['atlasSha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
    (ASSETS/'sky.txt').write_text(json.dumps(meta,indent=2)+'\n')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('Exported 170 saved PixelFlow frames and derived health-bar tops.',flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames, not drawers."""
    meta=json.loads((ASSETS/'sky.txt').read_text())
    saved=json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind]==saved[kind]
        sp=old.api('get?sprite_id='+saved[kind])['sprite']
        atlas=Image.open(ASSETS/f'sky_{kind}.png').convert('RGBA');offset=0
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
