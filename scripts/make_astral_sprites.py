#!/usr/bin/env python3
"""Procedural Astralhollow enemy sprites.

Five original silhouettes share only the 96x96 / (48,90) atlas contract; their
body language and palettes are intentionally different.  ``build`` creates
the local atlases and ``verify`` rerenders them pixel-for-pixel.
"""
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
KINDS = ['voidmoth', 'crystalwyrm', 'orbitbeetle', 'eclipsedryad', 'meteorgolem']
CLIPS = [('idle', 6), ('walk', 8), ('attack', 8), ('hurt', 4), ('die', 8)]
W = H = 96

PALETTES = {
    'voidmoth': ('#120d2e', '#5e43a6', '#c7a8ff', '#fff0b8'),
    'crystalwyrm': ('#071b2c', '#167caa', '#6de8ff', '#fff7d1'),
    'orbitbeetle': ('#24120a', '#9b4e20', '#f4a43a', '#ffe6a0'),
    'eclipsedryad': ('#101c18', '#37694d', '#9ed17a', '#e5ffc0'),
    'meteorgolem': ('#17131f', '#554c70', '#b39bd1', '#fff4db'),
}


def disc(d, box, fill, border=None, width=2):
    d.ellipse(tuple(round(v) for v in box), fill=fill, outline=border, width=width)


def poly(d, pts, fill, border=None, width=2):
    points = [(round(x), round(y)) for x, y in pts]
    d.polygon(points, fill=fill)
    if border:
        d.line(points + points[:1], fill=border, width=width, joint='curve')


def stroke(d, pts, color, width):
    d.line([(round(x), round(y)) for x, y in pts], fill=color, width=width, joint='curve')


def frame(kind, clip, n):
    """Thirty-four authored poses per family: anticipation, strike, recoil and remains."""
    im = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(im)
    dark, mid, light, glow = PALETTES[kind]
    shift = {'idle': [0, 0, 1, 0, -1, 0],
             'walk': [0, 1, 3, 5, 4, 1, -1, 0],
             'attack': [0, -2, -5, 5, 11, 9, 3, 0],
             'hurt': [-5, -4, -2, 0],
             'die': [0, -2, -3, -2, 0, 1, 1, 1]}[clip][n]
    lift = {'idle': [0, 1, 2, 1, 0, 0],
            'walk': [0, 2, 7, 11, 8, 2, 0, 0],
            'attack': [0, 0, -2, 3, 7, 4, 0, 0],
            'hurt': [0, 2, 0, 0],
            'die': [0, 0, 0, 0, 0, 0, 0, 0]}[clip][n]
    strike = [0, .12, .28, .85, 1, .75, .25, 0][n] if clip == 'attack' else 0
    windup = [0, .35, 1, .5, 0, 0, 0, 0][n] if clip == 'attack' else 0
    walk = clip == 'walk'
    dead = clip == 'die'
    fall = [0, .04, .14, .32, .57, .78, .9, .9][n] if dead else 0
    cx, foot = 47 + shift, 89 - lift

    if kind == 'voidmoth':
        # Four independently moving wings, antennae and a charged star-eye.
        flap = [0, 4, 9, 14, 8, -3, -7, -2][n] if walk else [0, 3, 6, 3, 0, -3][n] if clip == 'idle' else 0
        spread = 19 + flap * .65 + strike * 5 - windup * 9 - fall * 15
        cy = foot - 30 + fall * 22
        for side in (-1, 1):
            tip = (cx + side * (spread + 9), cy - 24 - flap * .45 + fall * 28)
            poly(d, [(cx+side*4,cy-9),(cx+side*14,cy-21),tip,(cx+side*(spread+4),cy+3),(cx+side*6,cy+9)], dark, '#090819')
            poly(d, [(cx+side*8,cy-11),(cx+side*14,cy-18),(tip[0]-side*4,tip[1]+5),(cx+side*(spread-3),cy+1)], mid)
            poly(d, [(cx+side*8,cy-16),(cx+side*17,cy-23),(tip[0]-side*6,tip[1]+3),(cx+side*16,cy-4)], light)
            disc(d,(cx+side*(spread-1)-3,cy-11,cx+side*(spread-1)+3,cy-5),glow)
            poly(d,[(cx+side*5,cy+6),(cx+side*(spread-1),cy+6),(cx+side*(spread-10),cy+19+fall*6),(cx+side*3,cy+13)],mid,dark)
            stroke(d,[(cx+side*3,cy-14),(cx+side*(11+windup*5),cy-31+fall*18),(cx+side*18,cy-33+fall*18)],light,2)
        disc(d,(cx-8,cy-13,cx+8,cy+21),dark)
        disc(d,(cx-5,cy-11,cx+5,cy+15),mid)
        poly(d,[(cx,cy-4),(cx+5,cy+3),(cx,cy+10),(cx-5,cy+3)],glow)
        if clip == 'attack' and n in (3,4,5):
            for k in range(3):
                x=cx+11+k*7;y=cy-14+k*5
                poly(d,[(x,y-5),(x+5,y),(x,y+5),(x-4,y)],glow,light,1)
    elif kind == 'crystalwyrm':
        # A jointed serpentine body: coiled windup, uncoiling lunge, open jaws.
        cx -= shift * .5
        coil = windup * 5 - strike * 6
        pts=[]
        for i in range(7):
            x = cx-29+i*8+(i/6)*strike*6 - (1-i/6)*coil
            y = foot-12-math.sin(i*1.23+n*.8)*4-lift*.25+fall*(i/6)*12
            pts.append((x,y))
        stroke(d,pts,dark,16);stroke(d,pts,mid,12);stroke(d,pts,light,5)
        for i,(x,y) in enumerate(pts[1:6],1):
            poly(d,[(x-5,y-5),(x,y-15+(i%2)*3),(x+6,y-4),(x,y+2)],light,dark)
        hx,hy=pts[-1];jaw=7*strike+2*(walk and n in (2,3,4))
        poly(d,[(hx-7,hy-8),(hx+12,hy-10),(hx+14,hy-3),(hx+8,hy+2),(hx-5,hy+3)],light,dark)
        poly(d,[(hx+6,hy+2),(hx+13,hy+2+jaw),(hx+10,hy+8+jaw),(hx-4,hy+8)],mid,dark)
        disc(d,(hx+6,hy-5,hx+10,hy-1),glow)
        if clip == 'attack' and n in (4,5):
            for k in range(3):
                x=hx+3+k*1.5;y=hy-4+k*3
                poly(d,[(x,y-5),(x+7,y),(x,y+5)],glow,light)
    elif kind == 'orbitbeetle':
        # Six alternating legs, split armour, mobile horn and orbiting satellites.
        cx -= shift * .5
        cy=foot-25+fall*17+windup*6
        for side in (-1,1):
            for i in range(3):
                a=cx+side*(10+i*5);step=(n%4-1.5)*3 if walk else 0
                stroke(d,[(a,cy+8),(a+side*11,cy+14),(a+side*(13+step),foot-1)],dark,5)
                stroke(d,[(a,cy+8),(a+side*13,cy+14)],mid,2)
        disc(d,(cx-25,cy-15,cx+25,cy+17),dark)
        disc(d,(cx-20,cy-13,cx+20,cy+12),mid)
        poly(d,[(cx-2,cy-12),(cx+2,cy-12),(cx+4,cy+12),(cx,cy+14)],light)
        for side in (-1,1):
            poly(d,[(cx+side*3,cy-12),(cx+side*18,cy-9),(cx+side*20,cy+5),(cx+side*3,cy+11)],light,dark)
            stroke(d,[(cx+side*13,cy-12),(cx+side*(22+strike*11),cy-31-windup*7),(cx+side*(25+strike*13),cy-39-windup*6)],light,3)
        disc(d,(cx+9,cy-4,cx+15,cy+1),glow)
        for k in range(3):
            angle=n*(.45+strike*.25)+k*2.094
            x=cx+math.cos(angle)*29;y=cy-3+math.sin(angle)*20-fall*8
            disc(d,(x-5,y-5,x+5,y+5),dark)
            disc(d,(x-3,y-3,x+3,y+3),glow)
        if clip == 'attack' and n in (4,5):
            stroke(d,[(cx+23,cy-14),(cx+36,cy-20),(cx+40,cy-11)],glow,3)
    elif kind == 'eclipsedryad':
        # Walking root legs and two jointed branch arms; the eclipse opens at impact.
        cx -= shift*.55
        cy=foot-35+lift*.9+fall*24+windup*5
        sway=math.sin(n*1.1)*3 if clip == 'idle' else 0
        stride=[0,3,8,9,2,-6,-7,-2][n] if walk else 0
        for side in (-1,1):
            knee=(cx+side*10+stride*side*.6,cy+25)
            end=(cx+side*(13+stride*side),foot-1)
            stroke(d,[(cx+side*7,cy+8),knee,end],dark,10)
            stroke(d,[knee,end],mid,5)
        poly(d,[(cx-13,cy+9),(cx-11,cy-24),(cx-4,cy-33),(cx+9,cy-27),(cx+14,cy+9)],dark)
        poly(d,[(cx-9,cy+6),(cx-8,cy-22),(cx-1,cy-30),(cx+7,cy-22),(cx+10,cy+8)],mid)
        for side in (-1,1):
            shoulder=(cx+side*10,cy-20)
            elbow=(cx+side*(18+windup*3),cy-2-windup*16+fall*12)
            hand=(cx+side*(24+strike*8)+sway,cy+8-strike*18+fall*18+sway*.5)
            stroke(d,[shoulder,elbow,hand],dark,8);stroke(d,[shoulder,elbow,hand],light,4)
            for k in range(3):stroke(d,[hand,(hand[0]+side*(4+k*2),hand[1]+(k-1)*5)],glow,2)
        disc(d,(cx-12,cy-45,cx+12,cy-21),light,dark)
        disc(d,(cx-8,cy-41,cx+8,cy-25),dark)
        disc(d,(cx-4,cy-36,cx+4,cy-30),glow)
        for side in (-1,1):
            stroke(d,[(cx+side*5,cy-43),(cx+side*16,cy-50+fall*16),(cx+side*21,cy-48+fall*16)],light,3)
            stroke(d,[(cx+side*13,cy-46+fall*16),(cx+side*19,cy-43+fall*16)],light,2)
        if clip == 'attack' and n in (3,4,5):
            stroke(d,[(cx+22,cy-12),(cx+30,cy-25),(cx+37,cy-16),(cx+40,cy-22)],glow,3)
    else:
        # Heavy two-step gait and a clear overhand meteor hammer with a shock ring.
        cx -= shift*.5
        cy=foot-32+fall*25+windup*7
        sway=math.sin(n*1.1)*3 if clip == 'idle' else 0
        stride=[0,2,6,8,3,-5,-7,-2][n] if walk else 0
        for side in (-1,1):
            poly(d,[(cx+side*5,cy+18),(cx+side*17,cy+18),(cx+side*(18+stride),foot-1),(cx+side*(5+stride),foot-1)],dark)
            poly(d,[(cx+side*7,cy+20),(cx+side*14,cy+21),(cx+side*(14+stride),foot-4),(cx+side*(8+stride),foot-4)],mid)
        poly(d,[(cx-23,cy+17),(cx-21,cy-16),(cx-8,cy-29),(cx+14,cy-25),(cx+25,cy+16),(cx+12,cy+23),(cx-15,cy+23)],mid,dark,4)
        poly(d,[(cx-21,cy-16),(cx-8,cy-29),(cx+1,cy-19),(cx-6,cy+3),(cx-18,cy+13)],light)
        for side in (-1,1):
            shoulder=(cx+side*21,cy-15)
            hand=(cx+side*(25+strike*3)+sway,cy-4-windup*27+strike*23+fall*12+sway*.7)
            stroke(d,[shoulder,hand],dark,14);stroke(d,[shoulder,hand],mid,9)
            poly(d,[(hand[0]-10,hand[1]-9),(hand[0]+10,hand[1]-8),(hand[0]+12,hand[1]+8),(hand[0]-10,hand[1]+11)],light,dark,3)
        poly(d,[(cx-8,cy-5),(cx+6,cy-5),(cx+9,cy+9),(cx-4,cy+11)],glow,dark,2)
        stroke(d,[(cx-4,cy-21),(cx+2,cy-9),(cx+8,cy+6)],light,3)
        disc(d,(cx+2,cy-21,cx+7,cy-17),glow)
        if clip == 'attack' and n in (4,5):
            stroke(d,[(cx+21,foot-7),(cx+35,foot-11),(cx+40,foot-6)],glow,3)
            for k in range(3):poly(d,[(cx+20+k*6,foot-5-k*4),(cx+24+k*6,foot-15-k*4),(cx+27+k*6,foot-6-k*4)],light)

    if clip == 'hurt':
        # Flash only painted pixels, then fade back through pale recoil poses.
        amount=[.92,.52,.2,0][n]
        px=im.load()
        for y in range(H):
            for x in range(W):
                r,g,b,a=px[x,y]
                if a: px[x,y]=(int(r+(255-r)*amount),int(g+(246-g)*amount),int(b+(255-b)*amount),a)
    if dead:
        if n >= 2:
            # Drop the silhouette toward the foot and leave visible shards/wing dust.
            box=im.getbbox()
            if box:
                part=im.crop(box)
                h=max(7,round(part.height*(1-fall*.84)))
                w=max(10,round(part.width*(1+fall*.16)))
                part=part.resize((w,h),Image.Resampling.NEAREST)
                im=Image.new('RGBA',(W,H))
                im.alpha_composite(part,(max(1,min(W-w-1,round(cx-w/2))),H-h-5))
        d=ImageDraw.Draw(im)
        if n in (3,4,5,6):
            for k in range(5):
                x=cx-20+k*10+(n-3)*2;y=foot-11-(k%3)*5-(6-n)*2
                poly(d,[(x-2,y+2),(x,y-4),(x+3,y+1)],light)
    return im


def atlas(kind):
    out = Image.new('RGBA', (W * 8, H * 5), (0, 0, 0, 0))
    row = 0
    for clip, count in CLIPS:
        for n in range(count): out.alpha_composite(frame(kind, clip, n), (n * W, row * H))
        row += 1
    return out


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else 'build'
    ASSETS.mkdir(exist_ok=True)
    if command in ('build', 'export'):
        for kind in KINDS: atlas(kind).save(ASSETS / f'astral_{kind}.png', optimize=True)
        meta = {'frame': [W, H], 'anchor': [48, 90], 'kinds': KINDS, 'clips': {c: {'fps': fps, 'n': n, 'row': i} for i, (c, n) in enumerate(CLIPS) for fps in [10]}}
        (ASSETS / 'astral.txt').write_text(json.dumps(meta, indent=2) + '\n')
    elif command == 'preview':
        out = ROOT / 'test-results/astral-preview'; out.mkdir(parents=True, exist_ok=True)
        for kind in KINDS:
            for clip, count in CLIPS:
                sheet = Image.new('RGBA', (W * count * 2, H * 2 + 22), '#173f37')
                labels = ImageDraw.Draw(sheet)
                for n in range(count):
                    pose = frame(kind, clip, n).resize((W * 2, H * 2), Image.Resampling.NEAREST)
                    sheet.alpha_composite(pose, (n * W * 2, 22))
                    labels.text((n * W * 2 + 5, 4), f'{clip} {n}', fill='#f7edd2')
                    labels.line((n * W * 2 + 96, H * 2 + 19, n * W * 2 + 96, H * 2 + 22), fill='#ffdf94', width=2)
                sheet.convert('RGB').save(out / f'{kind}_{clip}.png')
    elif command == 'contact':
        sheet = Image.new('RGB', (4 * 208 + 20, 5 * 224 + 42), '#102c30')
        labels = ImageDraw.Draw(sheet)
        labels.text((16, 12), 'ASTRALHOLLOW  /  original enemy animation', fill='#f3e8c7')
        for row, kind in enumerate(KINDS):
            for col, (clip, pose) in enumerate([('idle', 2), ('attack', 4), ('hurt', 0), ('die', 6)]):
                x, y = 12 + col * 208, 42 + row * 224
                labels.rectangle((x, y, x + 199, y + 215), fill='#173f37', outline='#698783', width=1)
                art = frame(kind, clip, pose).resize((192, 192), Image.Resampling.NEAREST)
                sheet.paste(art, (x + 4, y + 21), art)
                labels.text((x + 7, y + 5), f'{kind}  /  {clip}', fill='#fff0c8')
        out = ROOT / 'test-results/astralhollow-enemies.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out)
        print(out)
    elif command == 'verify':
        for kind in KINDS:
            assert atlas(kind).tobytes() == Image.open(ASSETS / f'astral_{kind}.png').convert('RGBA').tobytes(), kind
            for clip, count in CLIPS:
                images = [frame(kind, clip, n) for n in range(count)]
                assert len({im.tobytes() for im in images}) >= count - 1, (kind, clip, 'repeated poses')
                for n, im in enumerate(images):
                    box = im.getbbox()
                    assert box and box[0] > 0 and box[1] > 0 and box[2] < W and box[3] < H, (kind, clip, n, box)
                    assert im.getpixel((0, 0))[3] == 0, (kind, clip, n, 'opaque frame background')
        print('Astralhollow atlases are pixel-identical to the render')
    else: raise SystemExit('preview | contact | build | export | verify')


if __name__ == '__main__': main()
