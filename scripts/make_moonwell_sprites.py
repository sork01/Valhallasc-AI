#!/usr/bin/env python3
"""Moonwell Echo sprite: makesprites workflow, 34 frames in one editable PixelFlow sprite.

preview | build [--replace] | export | verify. build --replace discards only this sprite's editor changes;
export reads the editor sprite back and preserves them.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from make_crag_sprites import Frame, Palette, ellipsoid, polygon, gradient

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KIND='moonwell_echo'
W=H=96
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
PAL=Palette(dict(ink='#1c2141',shadow='#415579',body='#7796ae',light='#d0e6df',
                 glow='#91f6e2',dark='#10152b',white='#fff9df',accent='#eb9bd6'))


def edge(f,a,b,color='body',width=3):
    f.line(a,b,'ol',width+2)
    f.line(a,b,color,width)


def shape(f,mask,steps=('ink','shadow','body','light'),dither=.15):
    if isinstance(mask,np.ndarray):mask=gradient(mask,8,8,85,87)
    f.paint(mask,f.p.ramp(*steps),dither=dither)


def draw(clip,n):
    f=Frame(PAL)
    pulse=math.sin(n*.9)
    lift=(0,1,2,1,0,1)[n] if clip=='idle' else (0,2,4,3,1,0,-1,0)[n] if clip=='walk' else 0
    x,y=48,45-lift
    opened=clip=='attack' and n in (2,3,4,5)
    hurt=clip=='hurt' and n in (0,1)
    # A hollow three-faced mirror body: its sharp hovering fragments never read as a plant.
    for side in (-1,1):
        sway=4*pulse*side
        edge(f,(x+side*13,y+9),(x+side*(29+sway),y+32),'shadow',5)
        shape(f,polygon([(x+side*(30+sway),y+27),(x+side*(40+sway),y+43),
                         (x+side*(24+sway),y+56),(x+side*(19+sway),y+42)]))
        edge(f,(x+side*8,y+25),(x+side*(19+sway),y+77),'body',3)
        shape(f,polygon([(x+side*(19+sway),y+76),(x+side*(24+sway),y+87),
                         (x+side*(13+sway),y+84)]),('ink','shadow','glow','white'))
    shape(f,ellipsoid(x,y,20,23),('dark','ink','shadow','body'))
    shape(f,polygon([(x-14,y-15),(x-3,y-30),(x+2,y-15),(x-6,y+8)]),('ink','body','light','white'))
    shape(f,polygon([(x+14,y-15),(x+3,y-30),(x-2,y-15),(x+6,y+8)]),('ink','body','light','white'))
    shape(f,polygon([(x-14,y+8),(x,y+25),(x+14,y+8),(x,y-3)]),('shadow','body','glow','white'))
    # Three separate eyes look outward through the mirrored mask.
    for xx,yy in [(x-8,y-6),(x+8,y-6),(x,y+12)]:
        shape(f,ellipsoid(xx,yy,4,5),('shadow','glow','white','white'))
        f.dots([(xx+1,yy)],'dark')
    for side in (-1,1):
        edge(f,(x+side*13,y-10),(x+side*27,y-32),'light',4)
        shape(f,polygon([(x+side*27,y-32),(x+side*34,y-35),
                         (x+side*31,y-21),(x+side*22,y-21)]),('shadow','body','glow','white'))
    for j in range(5):
        xx=x+(j-2)*8+2*math.sin(n+j)
        shape(f,polygon([(xx,y+29),(xx+3,y+33),(xx+1,y+42)]),('shadow','body','glow','white'))
    if opened:
        for side in (-1,1):
            edge(f,(x+side*22,y+1),(x+side*43,y-7),'accent',3)
            shape(f,ellipsoid(x+side*39,y-8,4,5),('shadow','accent','white','white'))
    if hurt and n==0:f.whiten()
    if clip=='die':
        if n==0:f.whiten()
        if n>=2:
            ys,xs=np.nonzero(f.a)
            part=f.a[ys.min():ys.max()+1,xs.min():xs.max()+1]
            height=max(4,round(part.shape[0]*[1,1,.8,.6,.4,.26,.16,.1][n]))
            part=np.asarray(Image.fromarray(part).resize((part.shape[1],height),Image.Resampling.NEAREST))
            f.a[:]=0
            px=min(W-part.shape[1]-3,max(3,int(xs.min())))
            py=min(H-height-4,89-height)
            f.a[py:py+height,px:px+part.shape[1]]=part
            for j in range(4):f.dots([(21+j*15+n%3,87-j%2)],'glow')
    colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255]
                     for j,c in enumerate(f.p.hex)],dtype=np.uint8)
    image=Image.fromarray(colors[f.a],'RGBA').resize((88,88),Image.Resampling.NEAREST)
    out=Image.new('RGBA',(W,H));out.alpha_composite(image,(4,7))
    return out


def pf_client():
    sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'))
    import pf
    return pf


def meta(sid):
    start=0;clips={}
    for row,(name,count) in enumerate(CLIPS):
        clips[name]=dict(fps=10,n=count,row=row,editorStart=start);start+=count
    return dict(frame=[W,H],anchor=[48,90],kinds=[KIND],clips=clips,sprites={KIND:sid})


def grids():
    colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255]
                     for j,c in enumerate(PAL.hex)],dtype=np.uint8)
    out={}
    for clip,count in CLIPS:
        rows=[]
        for n in range(count):
            rgba=np.array(draw(clip,n));grid=np.zeros((H,W),dtype=np.uint8)
            for j,color in enumerate(colors[1:],1):grid[np.all(rgba==color,axis=2)]=j
            assert np.array_equal(colors[grid],rgba),(clip,n,'palette mismatch')
            ys,xs=np.nonzero(grid)
            assert xs.min()>0 and xs.max()<W-1 and ys.min()>0 and ys.max()<H-1,(clip,n,'frame edge')
            rows.append(grid)
        assert len({g.tobytes() for g in rows})>=count-1,clip
        out[clip]=rows
    return out


def contact():
    sheet=Image.new('RGB',(5*205+12,4*220+35),'#19333a');g=ImageDraw.Draw(sheet)
    for col,(clip,n) in enumerate([('idle',2),('walk',3),('attack',4),('hurt',1),('die',6)]):
        for row,index in enumerate([0,n,max(0,n-1),min(dict(CLIPS)[clip]-1,n+1)]):
            pose=draw(clip,index).resize((192,192),Image.Resampling.NEAREST)
            sheet.paste(pose,(8+col*205,24+row*220),pose)
            g.text((8+col*205,7+row*220),f'{clip} {index}',fill='#d2f5e5')
    path=ROOT/'test-results/moonwell-echo.png';path.parent.mkdir(exist_ok=True);sheet.save(path);print(path)


def build(replace=False):
    pf=pf_client();path=ASSETS/'moonwell.txt'
    old=json.loads(path.read_text())['sprites'][KIND] if path.exists() else None
    if old and not replace:raise SystemExit('Sprite exists: export preserves editor edits; build --replace discards them.')
    if old:assert pf.api('delete',{'sprite_id':old}).get('ok')
    data=grids()
    np.savez_compressed(ROOT/'scripts/moonwell_echo_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
    sid=pf.create('valhallasc_moonwell_echo_all',W,H,34,PAL.hex,fps=10)
    frame=0
    try:
        for clip,count in CLIPS:
            for grid in data[clip]:pf.draw_grid(sid,frame,0,grid);frame+=1
    except Exception:
        pf.api('delete',{'sprite_id':sid});raise
    path.write_text(json.dumps(meta(sid),indent=2)+'\n');print(sid)


def export(verify=False):
    pf=pf_client();path=ASSETS/'moonwell.txt';sid=json.loads(path.read_text())['sprites'][KIND]
    sp,frames=pf.load(sid)
    assert (sp['width'],sp['height'],len(frames))==(W,H,34)
    out=Image.new('RGBA',(W*8,H*len(CLIPS)))
    offset=0
    for row,(clip,count) in enumerate(CLIPS):
        for n in range(count):out.alpha_composite(Image.fromarray(pf.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*W,row*H))
        offset+=count
    target=ASSETS/'moonwell_echo.png'
    if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes()
    else:out.save(target,optimize=True);print(target)


if __name__=='__main__':
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    if cmd=='preview':grids();contact()
    elif cmd=='build':build('--replace' in sys.argv[2:])
    elif cmd=='export':export()
    elif cmd=='verify':export(True)
    else:raise SystemExit('preview | build [--replace] | export | verify')
