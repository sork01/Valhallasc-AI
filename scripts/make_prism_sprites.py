#!/usr/bin/env python3
"""Makesprites workflow for six Prismwaste enemies.

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
KINDS=['miragejackal','shardscarab','glassharrier','prismsentinel','mirrorqueen','sunshard']
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
W=H=96
# Indexed, shaded drawings are the source for the editable PixelFlow frames.
RAMPS={
 'miragejackal':('#342745','#715275','#b4879d','#f2c9a0','#ffe5ad'),
 'shardscarab':('#1d3442','#34717d','#72b7b4','#c6eee0','#fff0b0'),
 'glassharrier':('#302a4c','#645489','#ab98cd','#ead8eb','#ffd899'),
 'prismsentinel':('#303d50','#63849b','#a1beca','#e4edf0','#ffe2a1'),
 'mirrorqueen':('#311d49','#754083','#b875b8','#edb8e6','#fff0bb'),
 'sunshard':('#402c32','#9d604c','#dfa46c','#ffe3a3','#ffffcd'),
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
def _jackal(f,x,y,s,strike):
    # A lithe desert predator: purple mirror hide, long ears, and two split tails.
    step=s*.6
    for near in (False,True):
        for xx in (-17,17):
            px=x+xx+(2 if near else -2)
            ankle=px+(-step if xx<0 else step)
            _line(f,(px,y+52),(ankle,y+74),'shadow' if not near else 'body',5)
            _line(f,(ankle,y+74),(ankle+5,y+85),'body',3)
            f.line((ankle+3,y+85),(ankle+10,y+85),'light',2)
    for side in (-1,1):
        tail=[(x-24,y+40),(x-33,y+31+side*5),(x-40,y+17+side*4)]
        for a,b in zip(tail,tail[1:]):_line(f,a,b,'shadow',5)
        _plate(f,[(x-41,y+19+side*4),(x-45,y+12+side*4),(x-34,y+13+side*4),(x-37,y+25+side*4)])
        f.line((x-43,y+14+side*4),(x-37,y+17+side*4),'glow',1)
    _metal(f,ellipsoid(x-4,y+44,28,15))
    _plate(f,[(x-28,y+38),(x-13,y+28),(x+12,y+31),(x+24,y+43),
              (x+14,y+53),(x-19,y+53)])
    for j in range(4):
        px=x-15+j*8
        _plate(f,[(px-5,y+33),(px,y+27),(px+5,y+34),(px,y+43)])
        f.dots([(px,y+31)],'white')
    hx=x+20-(5 if strike else 0)
    _line(f,(x+14,y+39),(hx-5,y+28),'body',12)
    _metal(f,ellipsoid(hx,y+26,13,10))
    _plate(f,[(hx-8,y+23),(hx+4,y+15),(hx+16,y+25),(hx+9,y+33),(hx-10,y+32)])
    _plate(f,[(hx-8,y+21),(hx-9,y+2),(hx-2,y+8),(hx+1,y+21)])
    _plate(f,[(hx+2,y+18),(hx+7,y+1),(hx+13,y+7),(hx+11,y+22)])
    _eye(f,hx+7,y+25,2)
    _plate(f,[(hx+11,y+29),(hx+23,y+31),(hx+14,y+35)])
    f.dots([(hx+20,y+30)],'dark')
    if strike:
        for j in range(3):f.line((hx+23+j*4,y+31+j*3),(hx+27+j*4,y+30+j*3),'glow',1)


def _scarab(f,x,y,s,strike):
    for side in (-1,1):
        for j in range(3):
            root=(x+side*(8+j*7),y+52+j*2)
            knee=(root[0]+side*(10+j*3),y+67+(j%2)*4)
            foot=(knee[0]+side*(3+s/2),y+84)
            _line(f,root,knee,'shadow',4);_line(f,knee,foot,'body',2)
    _dark(f,ellipsoid(x,y+49,29,24))
    for side in (-1,1):
        _plate(f,[(x+side*2,y+24),(x+side*17,y+27),(x+side*28,y+47),
                  (x+side*19,y+67),(x+side*3,y+71)])
        f.line((x+side*7,y+29),(x+side*19,y+58),'light',2)
        _plate(f,[(x+side*10,y+34),(x+side*17,y+35),(x+side*22,y+48),(x+side*14,y+44)])
    f.line((x,y+27),(x,y+70),'glow',3)
    _metal(f,ellipsoid(x,y+25,12,10))
    _plate(f,[(x-8,y+20),(x,y+6),(x+8,y+20),(x,y+33)])
    for side in (-1,1):_eye(f,x+side*7,y+27,2)
    if strike:
        _plate(f,[(x+26,y+46),(x+43,y+36),(x+39,y+55)])
        f.line((x+34,y+47),(x+42,y+41),'white',1)


def _harrier(f,x,y,s,strike):
    cy=y+45;flap=s*1.2
    # Wings are tiled crystal panes with dark gaps, not a single flat triangle.
    for side in (-1,1):
        reach=39 if side>0 else 34
        tip=(x+side*reach,cy-29+side*flap)
        _plate(f,[(x+side*5,cy-3),tip,(x+side*(reach-4),cy+5),
                  (x+side*17,cy+16)])
        for j in range(3):
            px=x+side*(13+j*8)
            _plate(f,[(px,cy-13-j*4+side*flap/2),(px+side*6,cy-22-j*3+side*flap),
                      (px+side*8,cy+1+j),(px+side*3,cy+6+j)])
            f.line((px+side*2,cy-9-j*3),(px+side*5,cy-2-j),'glow',1)
    for side in (-1,1):
        _line(f,(x+side*5,cy+18),(x+side*(9+s/3),y+83),'shadow',3)
        f.line((x+side*(9+s/3),y+83),(x+side*(15+s/3),y+84),'light',2)
    for j in range(3):
        _plate(f,[(x-7+j*5,cy+17),(x-15+j*5,cy+34),(x-1+j*5,cy+27)])
    _metal(f,ellipsoid(x,cy+1,13,20))
    _plate(f,[(x-8,cy-13),(x+6,cy-15),(x+13,cy+2),(x,cy+19),(x-10,cy+5)])
    hx=x+13+(6 if strike else 0)
    _plate(f,[(hx-4,cy-19),(hx+10,cy-24),(hx+14,cy-12),(hx+5,cy+2),(hx-8,cy-4)])
    _eye(f,hx+5,cy-13,2)
    _plate(f,[(hx+11,cy-10),(hx+27,cy-4),(hx+10,cy+1)])
    if strike:f.line((hx+24,cy-4),(hx+36,cy-9),'glow',2)


def _sentinel(f,x,y,s,strike):
    for side in (-1,1):
        _dark(f,ellipsoid(x+side*11+s/4,y+75,10,13))
        _plate(f,[(x+side*3,y+66),(x+side*18,y+65),
                  (x+side*(20+s/3),y+85),(x+side*(3+s/3),y+85)])
    _metal(f,ellipsoid(x,y+44,22,20))
    _plate(f,[(x-17,y+27),(x+16,y+27),(x+21,y+59),(x+5,y+70),(x-20,y+58)])
    for side in (-1,1):
        _plate(f,[(x+side*4,y+30),(x+side*16,y+33),(x+side*12,y+52),(x+side*3,y+46)])
        f.line((x+side*5,y+34),(x+side*11,y+44),'light',2)
    _eye(f,x,y+49,4)
    _plate(f,[(x-14,y+12),(x-6,y+3),(x+9,y+7),(x+15,y+21),(x+6,y+30),(x-12,y+27)])
    _dark(f,ellipsoid(x,y+21,10,7));_eye(f,x,y+19,4)
    # Detached mirror shield panes, luminous spear, and separated shoulder shards.
    for side in (-1,1):
        _plate(f,[(x+side*15,y+28),(x+side*25,y+18),(x+side*28,y+40),(x+side*19,y+47)])
        f.line((x+side*20,y+25),(x+side*23,y+39),'glow',1)
    _plate(f,[(x-26,y+38),(x-37,y+35),(x-35,y+67),(x-25,y+73),(x-20,y+60)])
    f.line((x-33,y+42),(x-28,y+63),'light',2)
    sx=x+(35 if strike else 29)
    _line(f,(x+21,y+44),(sx,y+37),'body',6)
    _line(f,(sx,y+76),(sx,y+9),'light',3)
    _plate(f,[(sx-6,y+17),(sx,y+1),(sx+6,y+17)])


def _queen(f,x,y,s,strike):
    cy=y+45
    # Four separated mirror panels form the cape; a narrow dark body floats inside.
    for side in (-1,1):
        for row in (0,1):
            top=cy-23+row*27
            spread=29+row*6
            _plate(f,[(x+side*11,top),(x+side*spread,top-10),
                      (x+side*(spread+4),top+19),(x+side*16,top+23)])
            f.line((x+side*15,top+2),(x+side*(spread-1),top+12),'glow',2)
    _dark(f,ellipsoid(x,cy+12,17,30))
    _plate(f,[(x-14,cy-11),(x+14,cy-11),(x+20,cy+26),(x,cy+40),(x-20,cy+26)])
    for side in (-1,1):
        f.line((x+side*9,cy+2),(x+side*12,cy+26),'light',2)
    _eye(f,x,cy+15,5)
    _metal(f,ellipsoid(x,cy-21,11,12))
    _dark(f,ellipsoid(x,cy-19,8,7))
    for side in (-1,1):_eye(f,x+side*4,cy-20,2)
    _plate(f,[(x-17,cy-29),(x-13,cy-40),(x-5,cy-33),(x,cy-43),
              (x+5,cy-33),(x+13,cy-40),(x+17,cy-29)])
    for xx in (-11,0,11):f.dots([(x+xx,cy-34)],'white')
    if strike:
        for j in range(3):
            px=x+27+j*5;py=cy-18+j*12
            _plate(f,[(px,py-8),(px+8,py),(px,py+8),(px-3,py)])


def _sunshard(f,x,y,s,strike):
    cy=y+45
    for j in range(10):
        a=2*math.pi*j/10+s*.009
        px=x+math.cos(a)*35;py=cy+math.sin(a)*30
        _plate(f,[(px-3,py+5),(px,py-9),(px+4,py+5)])
    for side in (-1,1):
        _dark(f,ellipsoid(x+side*13,y+76,10,13))
        _plate(f,[(x+side*5,y+69),(x+side*20,y+70),(x+side*23,y+85),(x+side*4,y+85)])
        _line(f,(x+side*20,cy-8),(x+side*30,cy+18),'shadow',9)
        _plate(f,[(x+side*25,cy+12),(x+side*35,cy+15),(x+side*33,cy+31),(x+side*24,cy+29)])
    _metal(f,ellipsoid(x,cy,25,28))
    _plate(f,[(x,cy-27),(x+22,cy-9),(x+17,cy+22),(x,cy+32),
              (x-18,cy+22),(x-23,cy-9)])
    _gold(f,ellipsoid(x,cy,13,18))
    _eye(f,x,cy-4,7)
    for side in (-1,1):
        f.line((x+side*9,cy-15),(x+side*16,cy+12),'white',2)
    _plate(f,[(x-12,cy-28),(x,cy-40),(x+12,cy-28)])
    sx=x+(34 if strike else 30)
    _line(f,(x+24,cy-10),(sx,cy-26),'shadow',7)
    _plate(f,[(sx-6,cy-29),(sx+1,cy-46),(sx+9,cy-22),(sx+3,cy-15)])
    if strike:
        for j in range(4):
            px=x+25+j*5;py=cy-28+j*8
            f.line((px,py),(px+5,py-4),'glow',2)

DRAWERS={'miragejackal':_jackal,'shardscarab':_scarab,'glassharrier':_harrier,
         'prismsentinel':_sentinel,'mirrorqueen':_queen,'sunshard':_sunshard}

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
    pf=_pf();path=ASSETS/'prism.txt'
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
        np.savez_compressed(ROOT/'scripts'/f'prism_{kind}_raw.npz',
                            **{clip:np.stack(rows) for clip,rows in grids.items()})
        sid=pf.create('valhallasc_prism_'+kind+'_all',W,H,34,PALETTES[kind].hex,fps=10)
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
    pf=_pf();path=ASSETS/'prism.txt'
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
        out.save(ASSETS/f'prism_{kind}.png',optimize=True)
        print('exported',kind,flush=True)
    path.write_text(json.dumps(_metadata(sprites),indent=2)+'\n')

def _verify():
    pf=_pf();sprites=json.loads((ASSETS/'prism.txt').read_text())['sprites']
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
        assert out.tobytes()==Image.open(ASSETS/f'prism_{kind}.png').convert('RGBA').tobytes(),kind
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
        out=ROOT/'test-results/prism-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
if __name__=='__main__':main()
