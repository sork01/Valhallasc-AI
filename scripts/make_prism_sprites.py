#!/usr/bin/env python3
"""Six original 34-frame enemy atlases for the Prismwaste."""
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
KINDS = ['miragejackal', 'shardscarab', 'glassharrier', 'prismsentinel', 'mirrorqueen', 'sunshard']
CLIPS = [('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
W = H = 96
INK = '#171525'
PAL = {
    'miragejackal': ('#332744','#8c5fa0','#e7b990','#fff1c8'),
    'shardscarab': ('#192c3b','#377b8b','#99e6dc','#fff3cf'),
    'glassharrier': ('#30254d','#8771bf','#d5c5ff','#ffde99'),
    'prismsentinel': ('#30344e','#778ba6','#d5e9ed','#ffe2a1'),
    'mirrorqueen': ('#2a173f','#814c9d','#e7b8ff','#fff2c1'),
    'sunshard': ('#402828','#c0724c','#ffd58a','#ffffd4'),
}


def poly(d, pts, fill, outline=INK, width=2):
    pts=[(round(x),round(y)) for x,y in pts]
    d.polygon(pts,fill=fill)
    if outline:d.line(pts+[pts[0]],fill=outline,width=width,joint='curve')


def ellipse(d, box, fill, outline=INK, width=2):
    d.ellipse(tuple(round(v) for v in box),fill=fill,outline=outline,width=width)


def line(d, pts, fill, width=3):
    d.line([(round(x),round(y)) for x,y in pts],fill=fill,width=width,joint='curve')


def draw(kind, clip, n):
    im=Image.new('RGBA',(W,H)); d=ImageDraw.Draw(im)
    dark,mid,light,glow=PAL[kind]
    dx={'idle':[0,1,0,-1,0,1],'walk':[0,3,5,2,-2,-4,-2,0],
        'attack':[0,-2,-5,0,6,7,3,0],'hurt':[-3,-1,2,0],
        'die':[0,1,2,3,4,5,5,5]}[clip][n]
    rise={'idle':[0,1,2,1,0,1],'walk':[0,2,6,9,5,2,1,0],
          'attack':[0,0,0,3,6,3,1,0],'hurt':[0,2,1,0],
          'die':[0,0,0,0,0,0,0,0]}[clip][n]
    wind=clip=='attack' and n in (1,2)
    strike=clip=='attack' and n in (3,4,5)
    cx=46+dx; foot=87-rise
    if kind=='miragejackal':
        # Long ears, high chest, four thin legs and two mirror-tipped tails.
        stride=[0,3,7,5,-2,-6,-3,0][n] if clip=='walk' else 0
        for x in (31,41,57,64):
            line(d,[(x,foot-23),(x+stride*(1 if x%2 else -1),foot-7),(x+stride*.4,foot)],dark,6)
            line(d,[(x+stride*.4-3,foot),(x+stride*.4+4,foot)],light,2)
        poly(d,[(cx-27,foot-29),(cx-18,foot-42),(cx+10,foot-43),(cx+24,foot-29),(cx+17,foot-20),(cx-17,foot-19)],mid)
        poly(d,[(cx-22,foot-37),(cx-10,foot-43),(cx+8,foot-40),(cx-4,foot-26)],light,None)
        for j in (-1,1):
            tail=[(cx-24,foot-30),(cx-32,foot-40+j*3),(cx-36,foot-58+j*3)]
            line(d,tail,dark,7);line(d,tail,mid,4)
            poly(d,[(cx-38,foot-61+j*3),(cx-32,foot-62+j*3),(cx-34,foot-52+j*3)],glow)
        hx=cx+23+(2 if strike else -4 if wind else 0)
        poly(d,[(hx-8,foot-45),(hx+8,foot-44),(hx+15,foot-34),(hx+5,foot-29),(hx-8,foot-31)],light)
        for j in (-1,1):poly(d,[(hx+j*6,foot-44),(hx+j*10,foot-68),(hx+j*15,foot-47)],mid)
        ellipse(d,(hx+3,foot-42,hx+7,foot-38),glow,None)
        if strike:poly(d,[(hx+11,foot-32),(hx+15,foot-27),(hx+10,foot-27)],INK,None)
    elif kind=='shardscarab':
        # Segmented six-legged beetle with a split faceted dome.
        for side in (-1,1):
            for k in range(3):
                x=cx+side*(8+k*7); step=(n%4-1.5)*3 if clip=='walk' else 0
                line(d,[(x,foot-19),(x+side*13,foot-10),(x+side*(15+step),foot)],dark,5)
                line(d,[(x,foot-19),(x+side*13,foot-10)],light,2)
        ellipse(d,(cx-27,foot-43,cx+27,foot-10),dark)
        poly(d,[(cx-24,foot-30),(cx-17,foot-44),(cx-2,foot-47),(cx-1,foot-10),(cx-20,foot-14)],mid)
        poly(d,[(cx+1,foot-47),(cx+18,foot-44),(cx+25,foot-30),(cx+20,foot-14),(cx+1,foot-10)],light)
        line(d,[(cx,foot-44),(cx,foot-12)],glow,2)
        poly(d,[(cx-5,foot-39),(cx-13,foot-52),(cx-2,foot-60),(cx+5,foot-50)],glow)
        ellipse(d,(cx+13,foot-28,cx+18,foot-23),glow,None)
        if strike:poly(d,[(cx+23,foot-23),(cx+39,foot-28),(cx+33,foot-13)],glow)
    elif kind=='glassharrier':
        # Unequal shard wings keep the silhouette distinct from the moth and roc.
        flap=math.sin(n*1.1)*8 if clip in ('walk','idle') else 0
        cy=foot-35
        poly(d,[(cx-5,cy+6),(cx-34,cy-9-flap),(cx-38,cy-27-flap),(cx-16,cy-20-flap),(cx+1,cy-4)],mid)
        poly(d,[(cx+3,cy+6),(cx+24,cy-24+flap),(cx+39,cy-31+flap),(cx+30,cy+4),(cx+9,cy+13)],light)
        for j in range(4):
            line(d,[(cx-7-j*6,cy-3-j*2),(cx-13-j*7,cy-19-flap)],glow,2)
        ellipse(d,(cx-10,cy-10,cx+12,cy+20),dark)
        poly(d,[(cx-1,cy-8),(cx+15,cy-16),(cx+22,cy-8),(cx+12,cy+2)],light)
        poly(d,[(cx+17,cy-7),(cx+30+(8 if strike else 0),cy),(cx+16,cy+2)],glow)
        ellipse(d,(cx+9,cy-8,cx+13,cy-4),INK,None)
        for j in (-1,1):line(d,[(cx+j*4,cy+13),(cx+j*8,foot-2)],mid,3)
    elif kind=='prismsentinel':
        # Stone biped, broad shield shoulder and long luminous spear.
        stride=[0,3,6,4,-3,-6,-3,0][n] if clip=='walk' else 0
        for side in (-1,1):
            poly(d,[(cx+side*5,foot-29),(cx+side*12,foot-28),(cx+side*(12+stride),foot-2),(cx+side*(2+stride),foot-2)],dark)
        poly(d,[(cx-17,foot-68),(cx+16,foot-68),(cx+22,foot-34),(cx-19,foot-34)],mid)
        poly(d,[(cx-14,foot-64),(cx,foot-71),(cx+16,foot-64),(cx+5,foot-41),(cx-8,foot-43)],light)
        poly(d,[(cx-12,foot-75),(cx+13,foot-75),(cx+9,foot-60),(cx-9,foot-60)],dark)
        poly(d,[(cx-4,foot-75),(cx+7,foot-75),(cx+2,foot-64)],glow,None)
        poly(d,[(cx-25,foot-56),(cx-15,foot-67),(cx-15,foot-29),(cx-29,foot-32)],light)
        line(d,[(cx+20,foot-55),(cx+31+(8 if strike else 0),foot-69)],dark,8)
        line(d,[(cx+31+(8 if strike else 0),foot-18),(cx+31+(8 if strike else 0),foot-72)],glow,4)
        poly(d,[(cx+26,foot-72),(cx+31,foot-74),(cx+36,foot-72)],light)
    elif kind=='mirrorqueen':
        # A crowned figure whose wide mirrored mantle fractures in motion.
        cy=foot-35
        for side in (-1,1):
            poly(d,[(cx+side*8,cy-16),(cx+side*29,cy-33),(cx+side*36,cy+17),(cx+side*13,cy+36)],mid)
            poly(d,[(cx+side*13,cy-13),(cx+side*28,cy-26),(cx+side*31,cy+13),(cx+side*10,cy+22)],light,None)
        poly(d,[(cx-13,cy-16),(cx+13,cy-16),(cx+20,cy+29),(cx+9,foot-2),(cx-11,foot-2),(cx-20,cy+29)],dark)
        poly(d,[(cx-9,cy-13),(cx+8,cy-13),(cx+13,cy+25),(cx,cy+34),(cx-13,cy+25)],mid)
        ellipse(d,(cx-11,cy-37,cx+11,cy-13),light)
        poly(d,[(cx-17,cy-27),(cx-20,cy-35),(cx-9,cy-30),(cx,cy-36),(cx+9,cy-30),(cx+20,cy-35),(cx+17,cy-27)],glow)
        for j in (-1,1):ellipse(d,(cx+j*5-2,cy-29,cx+j*5+2,cy-25),dark,None)
        if strike:
            for k in range(3):poly(d,[(cx+20+k*4,cy-20+k*8),(cx+26+k*4,cy-27+k*8),(cx+31+k*4,cy-13+k*8)],glow)
    else:
        # Radiant heavy giant with a broken solar halo and an overhand blade.
        cy=foot-28
        for side in (-1,1):
            poly(d,[(cx+side*7,cy+17),(cx+side*19,cy+15),(cx+side*22,foot-1),(cx+side*4,foot-1)],dark)
        poly(d,[(cx-23,cy-27),(cx+22,cy-27),(cx+27,cy+20),(cx-26,cy+20)],mid)
        poly(d,[(cx-17,cy-24),(cx+10,cy-26),(cx+18,cy+16),(cx-16,cy+13)],light)
        for side in (-1,1):
            poly(d,[(cx+side*20,cy-27),(cx+side*29,cy-10),(cx+side*26,cy+16),(cx+side*17,cy+12)],dark)
        ellipse(d,(cx-13,cy-44,cx+13,cy-26),dark)
        poly(d,[(cx-8,cy-45),(cx+8,cy-45),(cx+11,cy-32),(cx,cy-29),(cx-11,cy-32)],glow)
        for k in range(7):
            a=(k+.15)*math.pi/4
            x,y=cx+math.cos(a)*25,cy-25+math.sin(a)*10
            poly(d,[(x-3,y+3),(x,y-8),(x+3,y+3)],glow,None)
        line(d,[(cx+23,cy-18),(cx+32,cy-42+(9 if strike else 0))],dark,8)
        poly(d,[(cx+28,cy-38),(cx+36,cy-39+(13 if strike else 0)),(cx+39,cy-30)],light)
    # A travelling facet glint makes quiet poses visibly alive without changing
    # the silhouette or the attack timing.
    if clip in ('idle','walk','attack'):
        gx=37+(n*7)%23; gy=42+(n*5)%13
        line(d,[(gx,gy-2),(gx,gy+2)],glow,1)
        line(d,[(gx-2,gy),(gx+2,gy)],glow,1)
    if clip=='hurt' and n<2:
        overlay=Image.new('RGBA',(W,H)); overlay.putalpha(im.getchannel('A'))
        overlay.paste('#ffffff' if n==0 else '#f4e6ff',(0,0,W,H),im.getchannel('A'))
        im=Image.blend(im,overlay,.55 if n==0 else .25)
    if clip=='die' and n>=2:
        box=im.getbbox()
        if box:
            part=im.crop(box)
            h=max(8,round(part.height*(1-(n-1)*.115)))
            w=max(8,round(part.width*(1+(n-1)*.025)))
            part=part.resize((w,h),Image.Resampling.NEAREST)
            im=Image.new('RGBA',(W,H))
            im.alpha_composite(part,(max(1,min(W-w-1,round(48-w/2))),H-h-5))
        d=ImageDraw.Draw(im)
        for j in range(4):
            x=26+j*13+(n-2); y=85-(j%2)*5
            poly(d,[(x-2,y),(x,y-5),(x+3,y)],glow,None)
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
        for kind in KINDS:atlas(kind).save(ASSETS/f'prism_{kind}.png',optimize=True)
        meta=dict(frame=[W,H],anchor=[48,90],kinds=KINDS,
                  clips={clip:dict(fps=10,n=count,row=row) for row,(clip,count) in enumerate(CLIPS)})
        (ASSETS/'prism.txt').write_text(json.dumps(meta,indent=2)+'\n')
    elif cmd=='verify':
        for kind in KINDS:
            assert atlas(kind).tobytes()==Image.open(ASSETS/f'prism_{kind}.png').convert('RGBA').tobytes()
            for clip,count in CLIPS:
                frames=[draw(kind,clip,n) for n in range(count)]
                assert len({im.tobytes() for im in frames})>=count-1,(kind,clip,'repeated')
                for n,im in enumerate(frames):
                    box=im.getbbox()
                    assert box and box[0]>0 and box[1]>0 and box[2]<W and box[3]<H,(kind,clip,n,box)
        print('Six atlases and all 204 frames verified')
    elif cmd=='contact':
        sheet=Image.new('RGB',(6*205+12,4*220+40),'#2b263b');d=ImageDraw.Draw(sheet)
        for col,kind in enumerate(KINDS):
            for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
                pose=draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
                sheet.paste(pose,(10+col*205,28+row*220),pose)
                d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#ffe7c7')
        out=ROOT/'test-results/prism-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
    else:raise SystemExit('build | export | verify | contact')


if __name__=='__main__':main()
