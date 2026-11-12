#!/usr/bin/env python3
"""Local before/after boards and clips for picture approval; no publication side effects."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw
import shared_slime_redraw as R
BACKUP=Path('/media/raid/valhallasc-data/shared-slime-original-20261112')
OUT=R.OUT


def source(base,kind):
 bank=R.BANKS[kind];meta=json.loads((base/f'client/assets/{bank}.txt').read_text())
 art='cf_eldmarr' if kind=='ember_firelord' and not meta.get('atlases',{}).get(kind) else kind
 image=Image.open(base/f'client/assets/{bank}_{art}.png').convert('RGBA')
 return image,R.kindframe.frame_of(meta,kind)


def cell(base,kind,clip,n):
 image,(w,h,ax,ay)=source(base,kind);row=list(R.CLIPS).index(clip)
 return image.crop((n*w,row*h,(n+1)*w,(row+1)*h)),ax,ay


def paste(im,base,kind,clip,n,cx,gy,scale=3):
 picture,ax,ay=cell(base,kind,clip,n);bbox=picture.getbbox()
 assert bbox and cx+(bbox[0]-ax)*scale>=0 and cx+(bbox[2]-ax)*scale<=im.width and gy+(bbox[1]-ay)*scale>=0 and gy+(bbox[3]-ay)*scale<=im.height,(kind,clip,n,'review clipping')
 im.alpha_composite(picture.resize((picture.width*scale,picture.height*scale),Image.Resampling.NEAREST),(cx-ax*scale,gy-ay*scale))


def board():
 cols=[('idle',0),('attack',2),('attack',4),('attack',7),('die',4),('die',7)]
 im=Image.new('RGBA',(200+len(cols)*500,len(R.KINDS)*310+50),'#202a3a');d=ImageDraw.Draw(im)
 d.text((10,10),'Shared and seasonal enemies: original (left) / candidate (right)',fill='white')
 for row,k in enumerate(R.KINDS):
  gy=50+row*310+265;d.text((8,gy-50),R.NAMES[k],fill='white')
  for col,(clip,n) in enumerate(cols):
   x=200+col*500;d.text((x+40,gy-250),f'{clip} {n}: old / new',fill='#c4d4e2')
   d.line([(x,gy),(x+498,gy)],fill='#48556a')
   paste(im,BACKUP,k,clip,n,x+100,gy,2);paste(im,R.ROOT,k,clip,n,x+320,gy,2)
 im.save(OUT/'shared-before-after.png')
 # A small idle roster is easy to review in chat; frames retain native scale.
 roster=Image.new('RGBA',(7*225,330),'#202a3a');d=ImageDraw.Draw(roster)
 for col,k in enumerate(R.KINDS):
  paste(roster,R.ROOT,k,'idle',0,col*225+112,285,3);d.text((col*225+8,306),R.NAMES[k],fill='white')
 roster.save(OUT/'shared-roster.png')


def clips():
 for clip in ('attack','die'):
  frames=[]
  for n in range(8):
   im=Image.new('RGBA',(len(R.KINDS)*460,350),'#202a3a');d=ImageDraw.Draw(im)
   for col,k in enumerate(R.KINDS):
    d.text((col*460+8,12),R.NAMES[k],fill='white');paste(im,R.ROOT,k,clip,n,col*460+150,315,3)
   frames.append(im.convert('RGB'))
  frames[0].save(OUT/f'shared-{clip}.gif',save_all=True,append_images=frames[1:]+[frames[-1]]*5,duration=125 if clip=='die' else 100,loop=0,disposal=2)
 for k in R.KINDS:
  im=Image.new('RGBA',(8*460,5*350),'#202a3a');d=ImageDraw.Draw(im)
  for row,(clip,(_,count)) in enumerate(R.CLIPS.items()):
   for n in range(count):paste(im,R.ROOT,k,clip,n,n*460+150,row*350+320,3);d.text((n*460+5,row*350+332),f'{clip} {n}',fill='white')
  im.save(OUT/f'shared-{k}-frames.png')


def review():
 OUT.mkdir(parents=True,exist_ok=True);board();clips();print('Review pictures:',OUT)


if __name__=='__main__':review()
