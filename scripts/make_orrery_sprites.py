#!/usr/bin/env python3
"""Original 34-frame pixel atlases for the Obsidian Orrery."""
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KINDS=['bronzemantis','gearling','orbitseer','chronoguard','pendulummatron','epochengine']
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
W=H=96
PAL={
 'bronzemantis':('#2b252a','#846548','#c8a66b','#e9e0a8'),
 'gearling':('#202739','#587886','#9bc2be','#f7d385'),
 'orbitseer':('#202c46','#53708d','#a3dce4','#f4e7ae'),
 'chronoguard':('#272536','#665d77','#b4a7ba','#f4ca85'),
 'pendulummatron':('#2f213b','#89617f','#e1b5a9','#fce0a2'),
 'epochengine':('#282033','#86634f','#dab47d','#fff1b2'),
}

def poly(d,pts,fill,outline='#171923'):
    pts=[(round(x),round(y)) for x,y in pts];d.polygon(pts,fill=fill)
    if outline:d.line(pts+[pts[0]],fill=outline,width=2,joint='curve')
def ell(d,box,fill,outline='#171923'):
    d.ellipse(tuple(round(v) for v in box),fill=fill,outline=outline,width=2 if outline else 1)
def line(d,pts,fill,width=3):
    d.line([(round(x),round(y)) for x,y in pts],fill=fill,width=width,joint='curve')

def draw(kind,clip,n):
    im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
    dark,mid,light,glow=PAL[kind]
    shift={'idle':[0,1,0,-1,0,1],'walk':[0,2,4,2,0,-2,-4,-2],
           'attack':[0,-1,-3,0,5,6,3,0],'hurt':[-3,-1,2,0],
           'die':[0,1,2,3,4,4,4,4]}[clip][n]
    bob={'idle':[0,1,2,1,0,1],'walk':[0,2,4,7,4,2,1,0],
         'attack':[0,0,1,3,5,3,1,0],'hurt':[0,2,1,0],
         'die':[0,0,0,0,0,0,0,0]}[clip][n]
    cx=48+shift;foot=86-bob;strike=clip=='attack' and n in (3,4,5)
    if kind=='bronzemantis':
        # Triangular head, segmented thorax and two scythe forearms.
        for side in (-1,1):
            for j in range(2):line(d,[(cx+side*(9+j*7),foot-20),(cx+side*(20+j*5),foot-8),(cx+side*(24+j*5),foot)],dark,4)
        ell(d,(cx-19,foot-43,cx+19,foot-17),mid)
        poly(d,[(cx-10,foot-37),(cx,foot-61),(cx+10,foot-37),(cx,foot-29)],light)
        poly(d,[(cx-15,foot-58),(cx,foot-66),(cx+15,foot-58),(cx,foot-47)],mid)
        for side in (-1,1):
            ell(d,(cx+side*8-3,foot-58,cx+side*8+3,foot-53),glow,None)
            elbow=(cx+side*(25 if strike else 22),foot-34 if strike else foot-45)
            line(d,[(cx+side*12,foot-40),elbow],dark,6)
            poly(d,[elbow,(elbow[0]+side*13,elbow[1]-12),(elbow[0]+side*6,elbow[1]+13)],light)
    elif kind=='gearling':
        # Low walking cog with eight square teeth, an eccentric eye and spring feet.
        for j in range(8):
            a=j*math.pi/4+n*.035;r=27
            x=cx+math.cos(a)*r;y=foot-26+math.sin(a)*r*.72
            poly(d,[(x-5,y-5),(x+5,y-5),(x+5,y+5),(x-5,y+5)],mid)
        ell(d,(cx-22,foot-46,cx+22,foot-7),dark)
        ell(d,(cx-16,foot-40,cx+16,foot-13),light)
        ell(d,(cx-8,foot-34,cx+8,foot-20),mid)
        ell(d,(cx+2,foot-32,cx+7,foot-27),glow,None)
        for side in (-1,1):line(d,[(cx+side*11,foot-11),(cx+side*19,foot-1)],dark,5)
        if strike:poly(d,[(cx+20,foot-27),(cx+34,foot-35),(cx+32,foot-17)],glow)
    elif kind=='orbitseer':
        # A suspended telescope eye between two offset orbital hoops.
        for r in (27,34):
            d.arc((cx-r,foot-57,cx+r,foot-57+r*1.5),25+n*2,310+n*2,fill=mid if r==27 else dark,width=5)
        poly(d,[(cx-14,foot-45),(cx,foot-61),(cx+14,foot-45),(cx+12,foot-23),(cx,foot-12),(cx-12,foot-23)],mid)
        ell(d,(cx-10,foot-46,cx+10,foot-27),light)
        ell(d,(cx-5,foot-42,cx+5,foot-31),dark)
        ell(d,(cx-2,foot-40,cx+2,foot-36),glow,None)
        for side in (-1,1):
            x=cx+side*28;y=foot-40+(n%3)*2
            poly(d,[(x,y-7),(x+side*7,y),(x,y+7),(x-side*5,y)],glow)
        if strike:line(d,[(cx,foot-35),(cx+30,foot-31)],glow,3)
    elif kind=='chronoguard':
        # Tower shield and crown gears around a broad stone body.
        for side in (-1,1):poly(d,[(cx+side*7,foot-18),(cx+side*18,foot-18),(cx+side*20,foot),(cx+side*5,foot)],dark)
        poly(d,[(cx-21,foot-63),(cx+21,foot-63),(cx+26,foot-20),(cx-26,foot-20)],mid)
        poly(d,[(cx-16,foot-58),(cx+15,foot-58),(cx+12,foot-23),(cx-12,foot-23)],light)
        poly(d,[(cx-15,foot-69),(cx+15,foot-69),(cx+11,foot-55),(cx-11,foot-55)],dark)
        for x in (-10,0,10):poly(d,[(cx+x-3,foot-69),(cx+x,foot-76),(cx+x+3,foot-69)],glow)
        ell(d,(cx-8,foot-66,cx-3,foot-61),glow,None);ell(d,(cx+3,foot-66,cx+8,foot-61),glow,None)
        poly(d,[(cx-31,foot-59),(cx-18,foot-62),(cx-17,foot-23),(cx-32,foot-15)],dark)
        line(d,[(cx+22,foot-57),(cx+30,foot-22 if strike else foot-52)],light,7)
    elif kind=='pendulummatron':
        # Tall bell skirt and a separate swinging pendulum arm.
        poly(d,[(cx-18,foot-48),(cx+18,foot-48),(cx+31,foot-2),(cx-31,foot-2)],dark)
        for j in range(-2,3):line(d,[(cx+j*9,foot-16),(cx+j*11,foot-2)],mid,3)
        poly(d,[(cx-18,foot-66),(cx+18,foot-66),(cx+22,foot-43),(cx-22,foot-43)],mid)
        ell(d,(cx-12,foot-78,cx+12,foot-56),light)
        poly(d,[(cx-19,foot-73),(cx-8,foot-76),(cx,foot-73),(cx+8,foot-76),(cx+19,foot-73)],glow)
        for side in (-1,1):ell(d,(cx+side*6-2,foot-70,cx+side*6+2,foot-66),dark,None)
        px=cx+24+(8 if strike else (n%3-1)*3)
        line(d,[(cx+18,foot-55),(px,foot-30)],light,5)
        ell(d,(px-7,foot-34,px+7,foot-15),glow)
    else:
        # The Epoch Engine: an open mechanism with four hands, a floating central clock and a crown.
        for j in range(8):
            a=j*math.pi/4+n*.025;x=cx+math.cos(a)*31;y=foot-43+math.sin(a)*24
            poly(d,[(x-5,y-5),(x+5,y-5),(x+5,y+5),(x-5,y+5)],mid)
        ell(d,(cx-27,foot-71,cx+27,foot-16),dark)
        ell(d,(cx-21,foot-65,cx+21,foot-22),mid)
        ell(d,(cx-16,foot-60,cx+16,foot-27),light)
        for j in range(12):
            a=j*math.pi/6;x=cx+math.cos(a)*12;y=foot-43+math.sin(a)*12
            ell(d,(x-1,y-1,x+1,y+1),dark,None)
        line(d,[(cx,foot-43),(cx+11,foot-51 if strike else foot-45)],dark,3)
        line(d,[(cx,foot-43),(cx-3,foot-55)],dark,2)
        ell(d,(cx-3,foot-46,cx+3,foot-40),glow,None)
        for side in (-1,1):
            line(d,[(cx+side*23,foot-53),(cx+side*34,foot-28)],dark,6)
            poly(d,[(cx+side*34,foot-35),(cx+side*38,foot-25),(cx+side*27,foot-23)],glow)
        poly(d,[(cx-16,foot-68),(cx,foot-76),(cx+16,foot-68)],glow)
    if clip in ('idle','walk','attack'):
        # A small moving glint makes the mechanical idle and windup frames distinct.
        gx=37+(n*7)%23;gy=42+(n*5)%13
        line(d,[(gx,gy-2),(gx,gy+2)],glow,1)
        line(d,[(gx-2,gy),(gx+2,gy)],glow,1)
    if clip=='hurt' and n<2:
        overlay=Image.new('RGBA',(W,H));overlay.paste('#ffffff',(0,0,W,H),im.getchannel('A'))
        im=Image.blend(im,overlay,.5 if n==0 else .23)
    if clip=='die' and n>=2:
        box=im.getbbox();part=im.crop(box)
        h=max(7,round(part.height*(1-(n-1)*.11)));w=max(7,round(part.width*(1+(n-1)*.02)))
        part=part.resize((w,h),Image.Resampling.NEAREST)
        im=Image.new('RGBA',(W,H));im.alpha_composite(part,(max(1,min(W-w-1,round(48-w/2))),H-h-5))
        d=ImageDraw.Draw(im)
        for j in range(3):poly(d,[(32+j*13,85),(35+j*13,78),(38+j*13,85)],glow,None)
    return im

def atlas(kind):
    out=Image.new('RGBA',(W*8,H*5))
    for row,(clip,count) in enumerate(CLIPS):
        for n in range(count):out.alpha_composite(draw(kind,clip,n),(n*W,row*H))
    return out

def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'build'
    ASSETS.mkdir(exist_ok=True)
    if cmd in ('build','export'):
        for kind in KINDS:atlas(kind).save(ASSETS/f'orrery_{kind}.png',optimize=True)
        meta=dict(frame=[W,H],anchor=[48,90],kinds=KINDS,
                  clips={clip:dict(fps=10,n=count,row=row) for row,(clip,count) in enumerate(CLIPS)})
        (ASSETS/'orrery.txt').write_text(json.dumps(meta,indent=2)+'\n')
    elif cmd=='verify':
        for kind in KINDS:
            assert atlas(kind).tobytes()==Image.open(ASSETS/f'orrery_{kind}.png').convert('RGBA').tobytes()
            for clip,count in CLIPS:
                frames=[draw(kind,clip,n) for n in range(count)]
                assert len({im.tobytes() for im in frames})>=count-1,(kind,clip)
                for n,im in enumerate(frames):
                    box=im.getbbox();assert box and box[0]>0 and box[1]>0 and box[2]<W and box[3]<H,(kind,clip,n,box)
        print('Six atlases and all 204 frames verified')
    elif cmd=='contact':
        sheet=Image.new('RGB',(6*205+12,4*220+40),'#211f2d');d=ImageDraw.Draw(sheet)
        for col,kind in enumerate(KINDS):
            for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
                pose=draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
                sheet.paste(pose,(10+col*205,28+row*220),pose)
                d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#f9d99d')
        out=ROOT/'test-results/orrery-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
    else:raise SystemExit('build | export | verify | contact')
if __name__=='__main__':main()
