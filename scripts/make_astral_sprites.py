#!/usr/bin/env python3
"""Makesprites workflow for five Astralhollow enemies.

preview checks and displays the procedural design; build uploads 34 editable
frames per kind to PixelFlow. export reads editor frames into game atlases.
Build --replace discards only these five sprites and any editor changes to them.
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
KINDS=['voidmoth','crystalwyrm','orbitbeetle','eclipsedryad','meteorgolem',]
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
W=H=96
# Indexed, shaded drawings are the source for the editable PixelFlow frames.
RAMPS={
 'voidmoth':('#211638','#4a3182','#8d6ac0','#d5baff','#ffecad'),
 'crystalwyrm':('#113044','#1f739d','#5bc0db','#b6eff3','#fff5be'),
 'orbitbeetle':('#34221f','#89502d','#d5863d','#f6c66e','#fff0a6'),
 'eclipsedryad':('#1c3029','#366549','#78a873','#d1df9c','#eaffb7'),
 'meteorgolem':('#28243e','#554b76','#978db9','#d7c9e5','#fff1d5'),
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
def _moth(f,x,y,s,strike):
    cy=y+46
    spread=33+abs(s)*.4+(5 if strike else 0)
    # Four separate velvet wings with starglass veins and bright ocelli.
    for side in (-1,1):
        tip=x+side*spread
        _plate(f,[(x+side*4,cy-9),(x+side*15,cy-30-s/2),
                  (tip,cy-29-s),(tip+side*5,cy-5),(x+side*8,cy+4)])
        _plate(f,[(x+side*10,cy+2),(tip+side*4,cy+2),
                  (tip+side*1,cy+20),(x+side*12,cy+28),(x+side*4,cy+16)])
        _gold(f,ellipsoid(x+side*24,cy-14-s/3,7,9))
        _eye(f,x+side*24,cy-14-s/3,3)
        for j in range(3):
            f.line((x+side*(8+j*6),cy-5-j*4),
                   (x+side*(17+j*6),cy-22-j*3),'light',1)
            f.dots([(x+side*(21+j*4),cy+9+j*2)],'glow')
    _dark(f,ellipsoid(x,cy+8,9,25))
    for j in range(4):
        _metal(f,ellipsoid(x,cy+2+j*9,8-j,5))
    _gold(f,ellipsoid(x,cy-10,10,12))
    _dark(f,ellipsoid(x,cy-11,7,7))
    _eye(f,x,cy-11,4)
    for side in (-1,1):
        _line(f,(x+side*4,cy-21),(x+side*10+s/3,cy-39),'body',2)
        f.dots([(x+side*10+s/3,cy-39)],'glow')
    if strike:
        for j in range(3):
            px=x+27+j*5;py=cy-20+j*8
            _plate(f,[(px,py-5),(px+6,py),(px,py+5),(px-3,py)])


def _wyrm(f,x,y,s,strike):
    # Articulated coiling body with translucent ridge blades and a horned head.
    pts=[]
    for j in range(7):
        px=x-34+j*9+s*j/14
        py=y+70-math.sin(j*1.08+s*.07)*8-j*2.6
        pts.append((px,py))
    for a,b in zip(pts,pts[1:]):_line(f,a,b,'shadow',14)
    for a,b in zip(pts,pts[1:]):f.line(a,b,'body',8)
    for j,(px,py) in enumerate(pts[1:6],1):
        _plate(f,[(px-7,py-6),(px-1,py-19-j%2*3),(px+6,py-7),(px+2,py+1)])
        f.line((px-1,py-17),(px+1,py-8),'glow',1)
        _metal(f,ellipsoid(px,py+7,5,4))
    hx,hy=pts[-1];hx+=4 if strike else 0
    _metal(f,ellipsoid(hx,hy-6,15,11))
    _plate(f,[(hx-11,hy-12),(hx+3,hy-19),(hx+15,hy-12),
              (hx+17,hy-3),(hx+5,hy+4),(hx-11,hy+1)])
    _plate(f,[(hx-7,hy-14),(hx-4,hy-28),(hx+2,hy-17)])
    _plate(f,[(hx+5,hy-16),(hx+10,hy-27),(hx+14,hy-10)])
    _eye(f,hx+7,hy-10,3)
    _plate(f,[(hx+11,hy-3),(hx+23,hy-2),(hx+14,hy+5),(hx+4,hy+4)])
    if strike:
        _plate(f,[(hx+8,hy+5),(hx+21,hy+10),(hx+14,hy+16),(hx+4,hy+8)])
        for j in range(3):f.line((hx+21+j*3,hy+j*3),(hx+25+j*3,hy-2+j*3),'glow',1)


def _beetle(f,x,y,s,strike):
    cy=y+53
    for side in (-1,1):
        for j in range(3):
            root=(x+side*(8+j*7),cy+3)
            knee=(x+side*(19+j*7),cy+13+(j%2)*3)
            foot=(knee[0]+side*(3+s/2),y+85)
            _line(f,root,knee,'shadow',4);_line(f,knee,foot,'body',2)
        _line(f,(x+side*9,cy-14),(x+side*(17+s/3),cy-37),'light',3)
        _eye(f,x+side*(17+s/3),cy-37,3)
    _dark(f,ellipsoid(x,cy-3,28,22))
    for side in (-1,1):
        _plate(f,[(x+side*1,cy-23),(x+side*19,cy-21),(x+side*27,cy-3),
                  (x+side*21,cy+17),(x+side*3,cy+20)])
        _gold(f,ellipsoid(x+side*16,cy-4,7,9))
        f.line((x+side*5,cy-19),(x+side*17,cy+13),'light',2)
    f.line((x,cy-21),(x,cy+17),'glow',2)
    _metal(f,ellipsoid(x,cy-21,12,10))
    _plate(f,[(x-5,cy-23),(x,cy-40),(x+7,cy-23)])
    for side in (-1,1):_eye(f,x+side*6,cy-21,2)
    if strike:
        _plate(f,[(x+23,cy-10),(x+40,cy-18),(x+36,cy+1)])
        f.line((x+30,cy-10),(x+38,cy-15),'white',1)


def _dryad(f,x,y,s,strike):
    # Root feet, bark torso, branch antlers and leaves orbiting an eclipse eye.
    for side in (-1,1):
        _line(f,(x+side*8,y+65),(x+side*(14+s/3),y+83),'shadow',7)
        for j in range(2):
            f.line((x+side*(14+s/3),y+83),(x+side*(21+j*5+s/3),y+86),'body',2)
    _dark(f,ellipsoid(x,y+50,17,23))
    _plate(f,[(x-14,y+28),(x+13,y+26),(x+20,y+61),(x,y+73),(x-20,y+61)])
    for side in (-1,1):
        _line(f,(x+side*14,y+39),(x+side*(27+s/3),y+59),'shadow',7)
        _line(f,(x+side*(27+s/3),y+59),(x+side*34,y+65),'body',3)
        for j in range(3):
            f.line((x+side*34,y+65),(x+side*(37+j*3),y+60+j*4),'light',1)
        _plate(f,[(x+side*17,y+31),(x+side*25,y+27),(x+side*22,y+43)])
    for j in range(-2,3):
        px=x+j*7
        f.line((px,y+35),(px+j*2,y+61),'shadow',2)
    _gold(f,ellipsoid(x,y+42,10,11))
    _dark(f,ellipsoid(x,y+41,7,8));_eye(f,x,y+40,4)
    for side in (-1,1):
        _line(f,(x+side*4,y+31),(x+side*11+s/4,y+8),'body',4)
        _line(f,(x+side*11+s/4,y+8),(x+side*24,y+2),'light',2)
        for j in range(2):
            _plate(f,[(x+side*(12+j*7),y+8-j*3),
                      (x+side*(19+j*7),y-2-j*4),
                      (x+side*(20+j*7),y+10-j*3)])
    if strike:
        for j in range(4):
            px=x+28+j*4;py=y+43+j*6
            _plate(f,[(px,py-5),(px+5,py),(px,py+5)])


def _golem(f,x,y,s,strike):
    # Heavy meteor fragments float around a fissured amethyst core.
    for side in (-1,1):
        _dark(f,ellipsoid(x+side*13+s/5,y+76,11,12))
        _plate(f,[(x+side*5,y+69),(x+side*20,y+68),
                  (x+side*23+s/3,y+85),(x+side*3+s/3,y+85)])
    _dark(f,ellipsoid(x,y+48,24,25))
    _plate(f,[(x-20,y+26),(x-3,y+19),(x+20,y+27),(x+24,y+59),
              (x+5,y+71),(x-21,y+61)])
    for side in (-1,1):
        shoulder=(x+side*20,y+37)
        hand=(x+side*(33 if strike else 30),y+(48 if strike else 58))
        _line(f,shoulder,hand,'shadow',9)
        _plate(f,[(hand[0]-9,hand[1]-8),(hand[0]+9,hand[1]-9),
                  (hand[0]+11,hand[1]+7),(hand[0]-8,hand[1]+9)])
        f.line((hand[0]-4,hand[1]-6),(hand[0]+3,hand[1]+2),'light',1)
        _plate(f,[(x+side*14,y+27),(x+side*22,y+17),(x+side*28,y+33)])
    _plate(f,[(x-14,y+22),(x-8,y+6),(x+5,y+2),(x+17,y+19),(x+11,y+35),(x-11,y+34)])
    _dark(f,ellipsoid(x,y+25,10,8));_eye(f,x+2,y+22,5)
    _plate(f,[(x-11,y+43),(x,y+36),(x+11,y+44),(x+5,y+62),(x-7,y+61)])
    _eye(f,x,y+49,5)
    for side in (-1,1):
        f.line((x+side*7,y+37),(x+side*13,y+57),'glow',2)
    if strike:
        for j in range(3):
            px=x+27+j*5;py=y+52-j*7
            _plate(f,[(px,py-7),(px+6,py),(px,py+5)])

DRAWERS={'voidmoth':_moth,'crystalwyrm':_wyrm,'orbitbeetle':_beetle,
         'eclipsedryad':_dryad,'meteorgolem':_golem}

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
    pf=_pf();path=ASSETS/'astral.txt'
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
        np.savez_compressed(ROOT/'scripts'/f'astral_{kind}_raw.npz',
                            **{clip:np.stack(rows) for clip,rows in grids.items()})
        sid=pf.create('valhallasc_astral_'+kind+'_all',W,H,34,PALETTES[kind].hex,fps=10)
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
    pf=_pf();path=ASSETS/'astral.txt'
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
        out.save(ASSETS/f'astral_{kind}.png',optimize=True)
        print('exported',kind,flush=True)
    path.write_text(json.dumps(_metadata(sprites),indent=2)+'\n')

def _verify():
    pf=_pf();sprites=json.loads((ASSETS/'astral.txt').read_text())['sprites']
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
        assert out.tobytes()==Image.open(ASSETS/f'astral_{kind}.png').convert('RGBA').tobytes(),kind
    print('Five PixelFlow sprites, 170 frames and exported atlases verified')

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
        sheet=Image.new('RGB',(len(KINDS)*205+12,4*220+40),'#211f2d');d=ImageDraw.Draw(sheet)
        for col,kind in enumerate(KINDS):
            for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
                pose=draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
                sheet.paste(pose,(10+col*205,28+row*220),pose)
                d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#f9d99d')
        out=ROOT/'test-results/astralhollow-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
if __name__=='__main__':main()
