#!/usr/bin/env python3
"""Shareable Ribbonwild map and cast cards from live browser captures and PixelFlow atlases."""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/ribbonwild-share'; OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
COLORS=['#f3a6c4','#f8d57d','#82d6d1','#bda7e7']
def label(d,xy,s,size=24,fill='#392d56',bold=False):d.text(xy,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=fill)
def cover(path,size):return ImageOps.fit(Image.open(path).convert('RGB'),size,Image.Resampling.LANCZOS)
def chart(image,zone):
 d=ImageDraw.Draw(image);d.rounded_rectangle((55,210,770,1125),radius=25,fill='#fff7e8',outline='#d9b879',width=5)
 x0,y0,k=77,260,4.8
 for i,c in enumerate(COLORS):
  d.pieslice((x0,y0,x0+136*k,y0+136*k),i*90-45,(i+1)*90-45,fill=c)
 def pt(x,y):return(x0+x*k,y0+y*k)
 for path in zone['paths']:
  line=[pt(x,y) for x,y in path]
  if len(line)>1:
   d.line(line,fill='#bc779f',width=18,joint='curve');d.line(line,fill='#ffe9b2',width=12,joint='curve')
 for obj in zone['objects']:
  x,y=pt(obj['x'],obj['y']);kind=obj['kind']
  if kind=='festival_bloom':d.ellipse((x-3,y-3,x+3,y+3),fill='#eb5d8f')
  elif kind=='fan_topiary':d.ellipse((x-6,y-6,x+6,y+6),fill='#3daaa4',outline='#fff1c2',width=2)
  elif kind=='pinwheel':d.ellipse((x-5,y-5,x+5,y+5),fill='#f8df66')
  elif kind=='grand_pavilion_gate':d.rounded_rectangle((x-30,y-35,x+30,y+25),radius=12,fill='#dc5790',outline='#f7de78',width=5)
  elif kind=='silk_pavilion':d.ellipse((x-12,y-8,x+12,y+8),fill='#fff1ab',outline='#bd5a9b',width=2)
 for enemy in zone['slimes']:
  if enemy['kind'] in ('paradegryphon','maskcolossus'):
   x,y=pt(enemy['x'],enemy['y']);d.ellipse((x-11,y-11,x+11,y+11),fill='#573e78',outline='#ffe79b',width=3)
 label(d,(89,946),'JUBILEE CROSSROADS',22,'#573f69',True)
 label(d,(512,555),'THOUSANDFOLD',17,'#573f69',True)
 label(d,(516,581),'PAVILION',17,'#573f69',True)
 label(d,(82,1070),'Four garden courts · one parade ring · six creatures',16,'#655075')

def zone_card(hub,gate):
 zone=json.loads((ROOT/'world/map.txt').read_text())['zones'][20]
 im=Image.new('RGB',(1920,1220),'#fff7e8');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1920,175),fill='#62427f')
 label(d,(62,20),'THE RIBBONWILD',69,'#fff1b8',True)
 label(d,(67,114),'LEVELS 70–75  ·  JUBILEE CROSSROADS  ·  THE THOUSANDFOLD PAVILION',22,'#f6c9e0')
 chart(im,zone);d=ImageDraw.Draw(im)
 gx,gy,gw,gh=810,210,1040,504;im.paste(cover(gate,(gw,gh)),(gx,gy))
 d.rectangle((gx,gy+gh-60,gx+gw,gy+gh),fill='#62427f');label(d,(gx+27,gy+gh-50),'THOUSANDFOLD PAVILION  ·  SEALED INSTANCE ENTRANCE',22,'#fff1b8',True)
 hx,hy,hw,hh=810,747,1040,370;im.paste(cover(hub,(hw,hh)),(hx,hy))
 d.rectangle((hx,hy+hh-57,hx+hw,hy+hh),fill='#62427f');label(d,(hx+27,hy+hh-48),'JUBILEE CROSSROADS  ·  QUESTS, SERVICES AND TRAVEL',22,'#fff1b8',True)
 label(d,(78,1148),'Real game captures · original PixelFlow creatures · dybase2 soundtrack',18,'#64507a')
 dest=OUT/'Valhalla_Ribbonwild_Zone_Overview.png';im.save(dest,optimize=True);print(dest)

def cast_card():
 names=[('ribbongecko','Ribbon Gecko','70'),('balloonbeetle','Balloon Beetle','71'),('paintedmacaw','Painted Macaw','72'),('jesterling','Jesterling','73'),('paradegryphon','Parade Gryphon','74 · ELITE'),('maskcolossus','Mask Colossus','75 · ELITE')]
 im=Image.new('RGB',(1880,760),'#fff6e4');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1880,140),fill='#62427f');label(d,(54,20),'THE RIBBONWILD CAST',54,'#fff1b8',True)
 label(d,(58,99),'Six original PixelFlow designs · 34 animation frames each · two outdoor elites',20,'#f5c6dd')
 for i,(kind,name,level) in enumerate(names):
  x=35+i*308;d.rounded_rectangle((x,164,x+291,695),radius=18,fill='#fffdf1',outline=COLORS[i%4],width=6)
  atlas=Image.open(ROOT/f'client/assets/ribbonwild_{kind}.png').convert('RGBA')
  idle=atlas.crop((0,0,96,96)).resize((255,255),Image.Resampling.NEAREST)
  attack=atlas.crop((4*96,2*96,5*96,3*96)).resize((195,195),Image.Resampling.NEAREST)
  im.paste(idle,(x+18,204),idle);im.paste(attack,(x+49,423),attack)
  label(d,(x+16,616),name,19,'#4e3a69',True);label(d,(x+17,650),'LEVEL '+level,16,'#af4c80' if 'ELITE' in level else '#69826f',True)
 dest=OUT/'Valhalla_Ribbonwild_Monsters.png';im.save(dest,optimize=True);print(dest)
if __name__=='__main__':zone_card(Path(sys.argv[1]),Path(sys.argv[2]));cast_card()
