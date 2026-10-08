#!/usr/bin/env python3
"""Makesprites workflow for six Obsidian Orrery enemies.

preview checks and displays the procedural design; build uploads 34 editable
frames per kind to PixelFlow. export reads editor frames into game atlases.
Build --replace discards only these six sprites and any editor changes to them.
"""
import json
import math
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from make_crag_sprites import AY, Frame, Palette, ellipsoid, polygon, gradient

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KINDS=['bronzemantis','gearling','orbitseer','chronoguard','pendulummatron','epochengine']
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
W=H=96
# Indexed, shaded drawings are the source for the editable PixelFlow frames.
RAMPS={
 'bronzemantis':('#332d32','#76523e','#bd8c5e','#ebc78b','#88ead7'),
 'gearling':('#253340','#3f6973','#85adb0','#e3d4a5','#ffe49b'),
 'orbitseer':('#283247','#476b93','#9ac8d3','#eee1ac','#a9f7f1'),
 'chronoguard':('#302f3c','#59596d','#a39eaa','#e5c89a','#99e8e9'),
 'pendulummatron':('#34283e','#754966','#c28c94','#f1cfaa','#ffe0a3'),
 'epochengine':('#2b2a39','#715346','#c3945f','#f3d79a','#9ff2e8'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],
                         dark='#181a27',white='#fff8e5',accent='#f5ad68'))
          for k,v in RAMPS.items()}

def _metal(f,shape):
    f.paint(shape,f.p.ramp('ink','shadow','body','light'),dither=.22)
def _dark(f,shape):
    f.paint(shape,f.p.ramp('dark','ink','shadow'),dither=.2)
def _gold(f,shape):
    f.paint(shape,f.p.ramp('shadow','body','light','white'),dither=.16)
def _plate(f,points):
    sh=polygon(points)
    f.paint(gradient(sh,min(x for x,y in points),max(y for x,y in points),
                     max(x for x,y in points),min(y for x,y in points)),
            f.p.ramp('ink','shadow','body','light'),dither=.18)
def _line(f,a,b,color='body',width=2):
    f.line(a,b,'ol',width+2);f.line(a,b,color,width)
def _eye(f,x,y,r=3):
    f.flat(ellipsoid(x,y,r+1,r+1)[0],'dark',outline=True)
    f.flat(ellipsoid(x,y,r,r)[0],'glow')
    f.dots([(x-1,y-1)],'white')
def _gear(f,x,y,r,teeth=10,phase=0):
    for j in range(teeth):
        a=2*math.pi*j/teeth+phase
        _metal(f,ellipsoid(x+math.cos(a)*r,y+math.sin(a)*r,3.6,3.6))
    _metal(f,ellipsoid(x,y,r-2,r-2))
    _dark(f,ellipsoid(x,y,r-8,r-8))
    _gold(f,ellipsoid(x,y,r-11,r-11))

def _mantis(f,x,y,s,strike):
    for side in (-1,1):
        for j in range(3):
            a=(x+side*(7+j*6),y+57+j*2)
            b=(a[0]+side*(7+j*2),y+66+j%2*3)
            c=(b[0]+side*5+s*(1 if j%2 else -1),y+83)
            _line(f,a,b,'shadow',3);_line(f,b,c,'body',2)
            f.line((c[0]-3,c[1]),(c[0]+3,c[1]),'light',1)
        elbow=(x+side*(23+s/2),y+(36 if strike else 43))
        tip=(x+side*(39 if strike else 34),y+(17 if strike else 30))
        _line(f,(x+side*11,y+44),elbow,'body',6)
        _plate(f,[(elbow[0]-side*3,elbow[1]-3),(elbow[0]+side*7,elbow[1]-7),
                  tip,(elbow[0]+side*11,elbow[1]+9)])
        _gold(f,ellipsoid(*elbow,4,4))
    _metal(f,ellipsoid(x,y+57,17,12))
    for j in range(3):
        _plate(f,[(x-8+j,y+47-j*8),(x+8-j,y+47-j*8),
                  (x+6-j,y+39-j*8),(x-6+j,y+39-j*8)])
    _metal(f,ellipsoid(x,y+24,15,10))
    _plate(f,[(x-15,y+20),(x,y+11),(x+15,y+20),(x+11,y+29),(x-11,y+29)])
    for side in (-1,1):
        _line(f,(x+side*6,y+17),(x+side*13,y+4-s/3),'body',2)
        _eye(f,x+side*7,y+23,2)
        _plate(f,[(x+side*3,y+31),(x+side*8,y+32),(x+side*4,y+39)])
    f.line((x-7,y+52),(x+7,y+54),'light',1)

def _gearling(f,x,y,s,strike):
    for side in (-1,1):
        _line(f,(x+side*13,y+55),(x+side*(17+s/2),y+77),'shadow',4)
        _line(f,(x+side*(17+s/2),y+77),(x+side*(24+s),y+83),'body',3)
        _line(f,(x+side*17,y+45),(x+side*(31 if strike else 27),y+38),'body',5)
        _plate(f,[(x+side*26,y+34),(x+side*38,y+30),(x+side*34,y+44),(x+side*27,y+47)])
    _gear(f,x,y+47,27,phase=s*.025)
    _dark(f,ellipsoid(x,y+46,9,9))
    _eye(f,x+2,y+43,5)
    for side in (-1,1):
        f.line((x+side*9,y+61),(x+side*13,y+64),'light',2)
    if strike:
        for j in range(3):
            f.line((x+28+j*3,y+27-j*3),(x+32+j*3,y+23-j*3),'glow',1)

def _seer(f,x,y,s,strike):
    cy=y+45
    for r,w in ((31,3),(37,2)):
        for j in range(17):
            a=.18+j/18*math.pi*1.75+s*.01;b=a+.09
            f.line((x+math.cos(a)*r,cy+math.sin(a)*r*.73),
                   (x+math.cos(b)*r,cy+math.sin(b)*r*.73),
                   'light' if j%4==0 else 'body',w)
    for side in (-1,1):
        ex=x+side*(31+s/3)
        _gold(f,ellipsoid(ex,cy-2,5,7));_eye(f,ex,cy-2,2)
    _plate(f,[(x,cy-33),(x+18,cy-12),(x+14,cy+19),(x,cy+29),
              (x-14,cy+19),(x-18,cy-12)])
    for side in (-1,1):
        f.line((x+side*4,cy-25),(x+side*12,cy-10),'light',1)
        f.line((x+side*12,cy+3),(x+side*5,cy+20),'shadow',2)
    _dark(f,ellipsoid(x,cy-1,13,12))
    _gold(f,ellipsoid(x,cy-2,9,8))
    _eye(f,x+1,cy-3,5)
    if strike:
        _line(f,(x+9,cy-3),(x+38,cy-10),'glow',2)

def _guard(f,x,y,s,strike):
    for side in (-1,1):
        _dark(f,ellipsoid(x+side*12+s/4,y+76,10,12))
        _plate(f,[(x+side*5,y+70),(x+side*18,y+70),
                  (x+side*21+s/3,y+84),(x+side*4+s/3,y+84)])
    _metal(f,ellipsoid(x,y+46,24,21))
    _plate(f,[(x-19,y+32),(x+19,y+32),(x+17,y+64),(x,y+71),(x-17,y+64)])
    f.line((x,y+37),(x,y+64),'light',2);_eye(f,x,y+51,3)
    _metal(f,ellipsoid(x,y+22,17,16))
    _plate(f,[(x-16,y+21),(x-13,y+9),(x+13,y+9),(x+16,y+21),
              (x+8,y+33),(x-8,y+33)])
    for j in (-1,0,1):
        _plate(f,[(x+j*10-4,y+11),(x+j*10,y+1-(j==0)*3),(x+j*10+4,y+11)])
    for side in (-1,1):_eye(f,x+side*7,y+22,2)
    _plate(f,[(x-22,y+35),(x-36,y+31),(x-35,y+67),(x-25,y+76),(x-19,y+64)])
    f.line((x-31,y+40),(x-27,y+65),'light',2)
    _line(f,(x+16,y+40),(x+25,y+45),'body',7)
    blade=(x+(35 if strike else 28),y+(18 if strike else 13))
    _line(f,(x+25,y+45),blade,'light',4)
    _plate(f,[(blade[0]-5,blade[1]+3),(blade[0],blade[1]-13),(blade[0]+5,blade[1]+3)])

def _matron(f,x,y,s,strike):
    _plate(f,[(x-20,y+39),(x+20,y+39),(x+32,y+81),
              (x+26,y+85),(x-27,y+85),(x-32,y+81)])
    for j in range(-2,3):
        f.line((x+j*8,y+51),(x+j*11,y+82),'body',2)
        f.dots([(x+j*11,y+80)],'light')
    _metal(f,ellipsoid(x,y+40,20,17))
    _plate(f,[(x-21,y+25),(x-10,y+20),(x,y+34),(x+10,y+20),
              (x+21,y+25),(x+16,y+49),(x-16,y+49)])
    for side in (-1,1):
        _plate(f,[(x+side*14,y+26),(x+side*24,y+15),
                  (x+side*29,y+33),(x+side*17,y+39)])
    _gold(f,ellipsoid(x,y+15,12,13));_dark(f,ellipsoid(x,y+15,8,8))
    for side in (-1,1):_eye(f,x+side*4,y+13,2)
    _plate(f,[(x-17,y+5),(x-7,y+1),(x,y+5),(x+7,y+1),
              (x+17,y+5),(x+11,y+11),(x-11,y+11)])
    _eye(f,x,y+37,4)
    px=x+(39 if strike else 33)+s/2;py=y+(66 if strike else 53)
    _line(f,(x+19,y+36),(px,py-10),'light',3)
    _gold(f,ellipsoid(px,py,8,12))
    f.line((px-3,py-3),(px+2,py+7),'white',1)
    if strike:f.line((px-10,py+11),(px+3,py+15),'glow',2)

def _engine(f,x,y,s,strike):
    cy=y+44
    for j in range(12):
        a=2*math.pi*j/12+s*.006
        px,py=x+math.cos(a)*34,cy+math.sin(a)*31
        _plate(f,[(px-4,py-5),(px+4,py-5),(px+5,py+5),(px-5,py+5)])
    for side in (-1,1):
        _line(f,(x+side*27,cy-9),(x+side*35,cy-26),'body',6)
        _plate(f,[(x+side*35,cy-31),(x+side*42,cy-25),(x+side*35,cy-18)])
        _line(f,(x+side*26,cy+12),(x+side*36,cy+29),'body',5)
        _gold(f,ellipsoid(x+side*36,cy+29,5,5))
    _metal(f,ellipsoid(x,cy,30,30));_dark(f,ellipsoid(x,cy,25,25))
    _gold(f,ellipsoid(x,cy,21,21))
    f.flat(ellipsoid(x,cy,17,17)[0],'light')
    for j in range(12):
        a=j*math.pi/6;xx=x+math.sin(a)*16;yy=cy-math.cos(a)*16
        f.line((xx,yy),(xx+math.sin(a)*3,yy-math.cos(a)*3),'ink',2)
    f.line((x,cy),(x+(14 if strike else 8),cy-(7 if strike else 12)),'ink',3)
    f.line((x,cy),(x-3,cy-10),'shadow',2)
    _eye(f,x,cy,3)
    _plate(f,[(x-17,cy-31),(x,cy-41),(x+17,cy-31)])
    if strike:
        for j in range(5):
            a=-.9+j*.45;px=x+math.cos(a)*42;py=cy+math.sin(a)*37
            f.line((px,py),(px+5,py-4),'glow',2)

DRAWERS={'bronzemantis':_mantis,'gearling':_gearling,'orbitseer':_seer,
         'chronoguard':_guard,'pendulummatron':_matron,'epochengine':_engine}
def _pose(clip,n):
    if clip=='idle':return 0,[0,1,2,1,0,1][n],[0,1,2,1,0,-1][n]
    if clip=='walk':return [0,-1,1,3,2,0,-1,0][n],[0,1,4,7,5,1,0,0][n],[0,-2,3,5,2,-3,-2,0][n]
    if clip=='attack':return [-3,-5,-6,2,7,5,2,0][n],[0,0,1,3,2,1,0,0][n],[-2,-4,-6,5,8,5,2,0][n]
    if clip=='hurt':return [-5,-3,1,0][n],[2,1,0,0][n],[-5,-3,2,0][n]
    return [0,0,1,1,1,1,1,1][n],[0,1,0,0,0,0,0,0][n],[0,2,4,5,5,5,5,5][n]
def draw(kind,clip,n):
    f=Frame(PALETTES[kind])
    dx,lift,sway=_pose(clip,n)
    DRAWERS[kind](f,48+dx,-lift,sway,clip=='attack' and n in (3,4,5))
    if clip=='idle':
        f.dots([(33+n*4,38+n%3),(34+n*4,38+n%3)],'glow')
    if clip=='hurt' and n==0:f.whiten()
    if clip=='hurt' and n==1:
        yy,xx=np.indices(f.a.shape)
        f.a[(f.a>0)&(f.a!=f.p['ol'])&((xx+yy)%3==0)]=f.p['flash']
    if clip=='die':
        if n==0:f.whiten()
        if n>=2:
            ys,xs=np.nonzero(f.a)
            body=f.a[ys.min():ys.max()+1,xs.min():xs.max()+1]
            height=max(5,round(body.shape[0]*[1,1,.72,.49,.31,.18,.11,.07][n]))
            image=Image.fromarray(body).resize((body.shape[1],height),Image.Resampling.NEAREST)
            f.a[:]=0
            px=max(1,min(W-body.shape[1]-1,xs.min()))
            py=min(H-height-5,AY-height)
            f.a[py:py+height,px:px+body.shape[1]]=np.array(image)
            for j in range(3):
                f.line((27+j*17+n%4,85),(31+j*17+n%4,81-n%3),'light',1)
    colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255]
                     for j,c in enumerate(f.p.hex)],dtype=np.uint8)
    image=Image.fromarray(colors[f.a],'RGBA').resize((88,88),Image.Resampling.NEAREST)
    framed=Image.new('RGBA',(W,H))
    framed.alpha_composite(image,(4,7))
    return framed

def atlas(kind):
    out=Image.new('RGBA',(W*8,H*5))
    for row,(clip,count) in enumerate(CLIPS):
        for n in range(count):out.alpha_composite(draw(kind,clip,n),(n*W,row*H))
    return out

def _pf():
    sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'))
    import pf
    return pf

def _metadata(sprites):
    start=0;clips={}
    for row,(clip,count) in enumerate(CLIPS):
        clips[clip]=dict(fps=10,n=count,row=row,editorStart=start)
        start+=count
    return dict(frame=[W,H],anchor=[48,90],kinds=KINDS,clips=clips,sprites=sprites)

def _grids(kind):
    palette=PALETTES[kind].hex
    colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255]
                     for j,c in enumerate(palette)],dtype=np.uint8)
    out={}
    for clip,count in CLIPS:
        out[clip]=[]
        for n in range(count):
            image=np.array(draw(kind,clip,n))
            grid=np.zeros((H,W),dtype=np.uint8)
            for j,rgba in enumerate(colors[1:],1):
                grid[np.all(image==rgba,axis=2)]=j
            assert np.array_equal(colors[grid],image),(kind,clip,n,'palette mismatch')
            ys,xs=np.nonzero(grid)
            assert len(xs) and xs.min()>0 and xs.max()<W-1 and ys.min()>0 and ys.max()<H-1,(kind,clip,n,'edge')
            out[clip].append(grid)
        assert len({g.tobytes() for g in out[clip]})>=count-1,(kind,clip,'static')
    return out

def _build(replace=False):
    pf=_pf();path=ASSETS/'orrery.txt'
    meta=json.loads(path.read_text()) if path.exists() else {}
    sprites=meta.get('sprites',{})
    if sprites and not replace:
        raise SystemExit('PixelFlow sprites already exist. Use export to preserve editor edits; build --replace discards them.')
    if replace:
        for sid in sprites.values():
            result=pf.api('delete',{'sprite_id':sid})
            assert result.get('ok'),result
        sprites={}
    for kind in KINDS:
        grids=_grids(kind)
        np.savez_compressed(ROOT/'scripts'/f'orrery_{kind}_raw.npz',
                            **{clip:np.stack(rows) for clip,rows in grids.items()})
        sid=pf.create('valhallasc_orrery_'+kind+'_all',W,H,34,PALETTES[kind].hex,fps=10)
        frame=0
        try:
            for clip,count in CLIPS:
                for grid in grids[clip]:
                    pf.draw_grid(sid,frame,0,grid)
                    frame+=1
        except Exception:
            pf.api('delete',{'sprite_id':sid})
            raise
        sprites[kind]=sid
        path.write_text(json.dumps(_metadata(sprites),indent=2)+'\n')
        print(kind,sid,'34 frames',flush=True)

def _export():
    pf=_pf();path=ASSETS/'orrery.txt'
    sprites=json.loads(path.read_text())['sprites']
    for kind in KINDS:
        sp,frames=pf.load(sprites[kind])
        assert (sp['width'],sp['height'],len(frames))==(W,H,34),(kind,'editor dimensions')
        out=Image.new('RGBA',(W*8,H*len(CLIPS)))
        offset=0
        for row,(clip,count) in enumerate(CLIPS):
            for n in range(count):
                image=Image.fromarray(pf.to_rgba(frames[offset+n][0],sp['palette']),'RGBA')
                out.alpha_composite(image,(n*W,row*H))
            offset+=count
        out.save(ASSETS/f'orrery_{kind}.png',optimize=True)
        print('exported',kind,flush=True)
    path.write_text(json.dumps(_metadata(sprites),indent=2)+'\n')

def _verify():
    pf=_pf();sprites=json.loads((ASSETS/'orrery.txt').read_text())['sprites']
    for kind in KINDS:
        sp,frames=pf.load(sprites[kind])
        assert len(frames)==34
        out=Image.new('RGBA',(W*8,H*len(CLIPS)))
        offset=0
        for row,(clip,count) in enumerate(CLIPS):
            for n in range(count):
                out.alpha_composite(Image.fromarray(pf.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),
                                    (n*W,row*H))
            offset+=count
        assert out.tobytes()==Image.open(ASSETS/f'orrery_{kind}.png').convert('RGBA').tobytes(),kind
    print('Six PixelFlow sprites, 204 frames and exported atlases verified')

def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    ASSETS.mkdir(exist_ok=True)
    if cmd=='build':_build('--replace' in sys.argv[2:])
    elif cmd=='export':_export()
    elif cmd=='verify':_verify()
    elif cmd=='preview':
        for kind in KINDS:_grids(kind)
        main_contact()
    elif cmd=='contact':main_contact()
    else:raise SystemExit('preview | build [--replace] | export | verify | contact')

def main_contact():
        sheet=Image.new('RGB',(6*205+12,4*220+40),'#211f2d');d=ImageDraw.Draw(sheet)
        for col,kind in enumerate(KINDS):
            for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
                pose=draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
                sheet.paste(pose,(10+col*205,28+row*220),pose)
                d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#f9d99d')
        out=ROOT/'test-results/orrery-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
if __name__=='__main__':main()
