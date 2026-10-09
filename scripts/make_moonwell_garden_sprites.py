#!/usr/bin/env python3
"""Independent 96px Moonwell atlases: preview | export | verify.

The existing Moonwell Echo editor sprite is deliberately untouched. Each new
creature has its own transparent file and a full five-clip animation cycle.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KINDS=['dew_moth','lumen_eel','rootbell','tideglass_heron','hourpetal_stag','moonskein_weaver']
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
INK='#15263b';SILVER='#a8d5cf';MINT='#9af2d7';LILAC='#8276b5';GOLD='#f8e8ad';CORAL='#f0a6be';WATER='#367d91'


def frame(kind,clip,n):
    im=Image.new('RGBA',(96,96));g=ImageDraw.Draw(im)
    phase=n*math.tau/8
    bob=round(math.sin(phase)*2) if clip in ('idle','walk') else 0
    spread=round(math.sin(phase)*5)
    strike=clip=='attack' and n in (2,3,4,5)
    ox=2 if clip=='walk' and n in (1,2,5) else -2 if clip=='walk' and n in (3,6) else 0
    def ell(box,fill,width=2):g.ellipse(box,fill,INK,width)
    def poly(points,fill,width=2):g.polygon(points,fill);g.line(points+[points[0]],fill=INK,width=width,joint='curve')
    def line(points,fill,width=3):g.line(points,fill=INK,width=width+3,joint='curve');g.line(points,fill=fill,width=width,joint='curve')
    if kind=='dew_moth':
        # Crescent wings around a hanging drop, with antennae like tiny tuning forks.
        poly([(47,42),(16,21+spread),(21,54),(42,63)],SILVER)
        poly([(49,42),(80,21-spread),(75,54),(54,63)],LILAC)
        for x in (29,67):ell((x-6,39,x+6,51),GOLD)
        ell((39,36+bob,57,73+bob),WATER)
        poly([(43,66+bob),(48,84+bob),(53,66+bob)],MINT)
        ell((41,28+bob,55,43+bob),SILVER)
        for s in (-1,1):line([(48+s*4,30+bob),(48+s*12,15+bob),(48+s*17,12+bob)],MINT,2)
        ell((44,34+bob,48,38+bob),GOLD,1);ell((51,34+bob,55,38+bob),GOLD,1)
        if strike:line([(48,57),(48,81)],CORAL,4)
    elif kind=='lumen_eel':
        # S-shaped river ribbon; fins make it read as a living fish, not a snake.
        line([(20,75+bob),(29,82+bob),(45,67+bob),(37,51+bob),(50,38+bob),(68,48+bob)],WATER,15)
        line([(20,75+bob),(29,82+bob),(45,67+bob),(37,51+bob),(50,38+bob),(68,48+bob)],MINT,7)
        poly([(35,61+bob),(18,50+bob),(28,76+bob)],LILAC)
        poly([(45,43+bob),(37,17+bob),(57,34+bob)],SILVER)
        ell((55,34+bob,79,57+bob),SILVER)
        poly([(76,42+bob),(85,49+bob),(76,53+bob)],GOLD)
        ell((68,39+bob,74,45+bob),INK,1)
        if strike:line([(78,47),(88,42)],CORAL,4)
    elif kind=='rootbell':
        # A walking seed bell with four root feet and a luminous clapper.
        for s in (-1,1):
            line([(48+s*10,65),(48+s*(18+spread),83)],WATER,7)
            poly([(48+s*19,78),(48+s*32,86),(48+s*12,86)],LILAC)
            line([(48+s*15,49),(48+s*31,62)],SILVER,5)
        poly([(25,53+bob),(29,35+bob),(39,25+bob),(57,25+bob),(67,35+bob),(71,53+bob),(64,68+bob),(32,68+bob)],SILVER)
        ell((34,52+bob,62,75+bob),WATER)
        ell((42,57+bob,54,70+bob),GOLD)
        line([(48,28+bob),(48,13+bob)],MINT,4)
        ell((43,7+bob,53,17+bob),CORAL)
        for x in (39,57):ell((x-3,39+bob,x+3,45+bob),INK,1)
        if strike:poly([(29,53),(18,46),(24,65),(36,69)],CORAL)
    elif kind=='tideglass_heron':
        # One leg raised, long spearing bill, fan of water-glass feathers.
        for s in (-1,1):
            line([(48+s*9,65+bob),(48+s*(10+spread),84)],LILAC,4)
            line([(48+s*(10+spread),84),(48+s*(21+spread),87)],GOLD,2)
        poly([(24,43+bob),(14,25+bob),(39,32+bob),(48,57+bob)],WATER)
        poly([(72,43+bob),(82,25+bob),(57,32+bob),(48,57+bob)],SILVER)
        ell((35,38+bob,61,68+bob),LILAC)
        line([(50,43+bob),(56,26+bob),(52,16+bob)],SILVER,8)
        ell((44,8+bob,62,25+bob),SILVER)
        poly([(60,14+bob),(86,20+bob),(60,23+bob)],GOLD if not strike else CORAL)
        ell((53,11+bob,58,16+bob),INK,1)
        for s in (-1,1):poly([(48+s*13,46+bob),(48+s*35,36+bob),(48+s*16,59+bob)],MINT)
    elif kind=='hourpetal_stag':
        # Floral antlers wrap a small gold clock face; powerful four-legged body.
        for s in (-1,1):
            for yy in (55,65):line([(48+s*18,yy+bob),(48+s*(24+spread),85)],LILAC,7)
            line([(48+s*13,33+bob),(48+s*24,10+bob),(48+s*34,8+bob)],SILVER,5)
            for j in range(2):ell((48+s*(24+j*7)-5,11+j*9+bob,48+s*(24+j*7)+5,21+j*9+bob),CORAL)
        ell((25,37+bob,71,69+bob),WATER)
        poly([(37,57+bob),(48,78+bob),(59,57+bob)],SILVER)
        ell((35,26+bob,61,49+bob),SILVER)
        ell((42,31+bob,54,43+bob),GOLD)
        line([(48,37+bob),(48+(10 if strike else 4),30+bob)],INK,2)
        ell((37,29+bob,41,34+bob),INK,1);ell((55,29+bob,59,34+bob),INK,1)
    elif kind=='moonskein_weaver':
        # A radial spindle with eight independent legs and a woven halo.
        for j in range(8):
            a=j*math.tau/8+phase*.13
            x=48+math.cos(a)*37;y=48+math.sin(a)*31
            line([(48+math.cos(a)*12,48+math.sin(a)*12),(x,y),(x+math.cos(a)*5,y+math.sin(a)*8)],LILAC,4)
        g.ellipse((15,16,81,78),outline=MINT,width=2)
        for j in range(6):
            a=j*math.tau/6
            ell((46+math.cos(a)*26,45+math.sin(a)*25,51+math.cos(a)*26,50+math.sin(a)*25),GOLD,1)
        ell((27,31+bob,69,71+bob),WATER)
        poly([(48,23+bob),(68,46+bob),(48,70+bob),(28,46+bob)],SILVER)
        ell((40,39+bob,56,55+bob),INK)
        for x,y in ((42,44),(54,44),(48,50)):ell((x-2,y-2+bob,x+2,y+2+bob),CORAL if strike else GOLD,1)
    if clip=='attack' and n:
        ell((13+n*7,72-n%3*5,17+n*7,76-n%3*5),CORAL,1)
    if clip=='hurt' and n:
        ell((18+n*8,75-n*4,22+n*8,79-n*4),MINT,1)
    if clip=='hurt' and n==0:
        flash=Image.new('RGBA',im.size,(245,251,252,0));flash.putalpha(im.getchannel('A'));im=Image.blend(im,flash,.65)
    if clip=='die':
        if n==0:
            flash=Image.new('RGBA',im.size,(255,255,255,0));flash.putalpha(im.getchannel('A'));im=Image.blend(im,flash,.5)
        if n>=2:
            crop=im.crop(im.getbbox());height=max(5,int(crop.height*[1,1,.77,.58,.42,.28,.17,.1][n]));crop=crop.resize((crop.width,height),Image.Resampling.NEAREST)
            im=Image.new('RGBA',(96,96));im.alpha_composite(crop,((96-crop.width)//2,88-height))
    assert im.getbbox() and 0<im.getbbox()[0] and im.getbbox()[2]<96 and im.getbbox()[3]<96,(kind,clip,n,im.getbbox())
    return im


def atlas(kind):
    out=Image.new('RGBA',(96*8,96*5))
    for row,(clip,count) in enumerate(CLIPS):
        poses=[]
        for n in range(count):
            pose=frame(kind,clip,n);out.alpha_composite(pose,(n*96,row*96));poses.append(pose.tobytes())
        assert len(set(poses))>=min(count,3),(kind,clip)
    return out


def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    if cmd not in ('preview','export','verify'):raise SystemExit('preview | export | verify')
    for kind in KINDS:
        out=atlas(kind);path=ASSETS/f'moonwell_{kind}.png'
        if cmd=='verify':assert out.tobytes()==Image.open(path).convert('RGBA').tobytes(),kind
        elif cmd=='export':out.save(path,optimize=True);print(path)
    if cmd=='preview':
        sheet=Image.new('RGB',(6*192,5*205),'#18334c');d=ImageDraw.Draw(sheet)
        for x,kind in enumerate(KINDS):
            for y,clip in enumerate(c for c,_ in CLIPS):
                pose=frame(kind,clip,3 if clip!='hurt' else 1).resize((184,184),Image.Resampling.NEAREST)
                sheet.paste(pose,(x*192+4,y*205+16),pose);d.text((x*192+5,y*205+2),kind+' '+clip,fill=GOLD)
        path=ROOT/'test-results/moonwell-garden-contact.png';sheet.save(path);print(path)
    if cmd=='export':
        path=ASSETS/'moonwell_garden.txt'
        path.write_text(json.dumps(dict(frame=[96,96],anchor=[48,90],kinds=KINDS,
            clips={c:dict(fps=10,n=n,row=i) for i,(c,n) in enumerate(CLIPS)}),indent=2)+'\n')
        print(path)


if __name__=='__main__':main()
