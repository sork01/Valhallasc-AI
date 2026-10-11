#!/usr/bin/env python3
"""Make Tanglecrown zone and cast cards from real browser captures and PixelFlow atlases."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/tanglecrown-share';OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def label(d,xy,s,size=24,fill='#eaf5d3',bold=False):d.text(xy,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=fill)
def cover(path,size):return ImageOps.fit(Image.open(path).convert('RGB'),size,Image.Resampling.LANCZOS)
def chart(im,zone):
 d=ImageDraw.Draw(im);d.rounded_rectangle((53,207,770,1127),radius=28,fill='#d9efc4',outline='#8da768',width=6)
 x0,y0,k=78,258,4.45
 d.rounded_rectangle((x0,y0,x0+144*k,y0+144*k),radius=21,fill='#4e9b6e')
 def pt(x,y):return x0+x*k,y0+y*k
 for o in zone['objects']:
  x,y=pt(o['x'],o['y']);kind=o['kind']
  if kind=='jungle_water':d.ellipse((x-7,y-7,x+7,y+7),fill='#48b9bd')
  elif kind=='jade_pool':d.ellipse((x-17,y-17,x+17,y+17),fill='#2e999f',outline='#a6dfb1',width=3)
  elif kind in ('kapok_tree','strangler_fig','banana_palm'):
   r={'kapok_tree':7,'strangler_fig':6,'banana_palm':4}[kind];c={'kapok_tree':'#1d5f43','strangler_fig':'#2b754d','banana_palm':'#78c767'}[kind]
   d.ellipse((x-r,y-r,x+r,y+r),fill=c,outline='#a2d47b',width=1)
 for path in zone['paths']:
  line=[pt(x,y) for x,y in path]
  if len(line)>1:d.line(line,fill='#53684b',width=22,joint='curve');d.line(line,fill='#d8c88e',width=14,joint='curve')
 for o in zone['objects']:
  if o['kind'] in ('rain_crown_temple','banyan_lodge'):
   x,y=pt(o['x'],o['y']);r=25 if o['kind']=='rain_crown_temple' else 10
   d.rounded_rectangle((x-r,y-r,x+r,y+r),radius=6,fill='#e4d89f' if r==25 else '#a77e53',outline='#294d40',width=4)
 for e in zone['slimes']:
  if e['kind'] in ('jadeanaconda','crownjaguar'):
   x,y=pt(e['x'],e['y']);d.ellipse((x-11,y-11,x+11,y+11),fill='#e8bd71',outline='#203e3e',width=4)
 label(d,(91,931),'BANYAN LANDING',22,'#274f3d',True)
 label(d,(79,1072),'Braided channels · reconnecting trails · giant canopy',16,'#4c7553')
def zone_card(landing,temple):
 zone=json.loads((ROOT/'world/map.txt').read_text())['zones'][21]
 im=Image.new('RGB',(1920,1220),'#ecf5d9');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1920,176),fill='#255b4e');label(d,(61,20),'THE TANGLECROWN',69,'#f2e5a9',True)
 label(d,(67,114),'LEVELS 75–80  ·  BANYAN LANDING  ·  TEMPLE OF THE RAIN CROWN',22,'#b7e1b8')
 chart(im,zone);d=ImageDraw.Draw(im)
 gx,gy,gw,gh=810,207,1040,511;im.paste(cover(temple,(gw,gh)),(gx,gy));d.rectangle((gx,gy+gh-62,gx+gw,gy+gh),fill='#255b4e');label(d,(gx+26,gy+gh-51),'RAIN CROWN TEMPLE  ·  SEALED INSTANCE ENTRANCE',22,'#f2e5a9',True)
 hx,hy,hw,hh=810,752,1040,367;im.paste(cover(landing,(hw,hh)),(hx,hy));d.rectangle((hx,hy+hh-60,hx+hw,hy+hh),fill='#255b4e');label(d,(hx+27,hy+hh-49),'BANYAN LANDING  ·  QUESTS, SUPPLIES AND TRAVEL',22,'#f2e5a9',True)
 label(d,(78,1150),'Real game captures · original PixelFlow creatures · dybase2 soundtrack',18,'#54735b')
 target=OUT/'Valhalla_Tanglecrown_Zone_Overview.png';im.save(target,optimize=True);print(target)
def cast_card():
 names=[('orchidmantis','Orchid Mantis','75'),('canopyglider','Canopy Glider','76'),('poolcaiman','Blackwater Caiman','77'),('drumgorilla','Drum Gorilla','78'),('jadeanaconda','Jade Anaconda','79 · ELITE'),('crownjaguar','Crown Jaguar','80 · ELITE')]
 im=Image.new('RGB',(1880,760),'#e8f4d8');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1880,140),fill='#255b4e');label(d,(52,20),'CREATURES OF THE TANGLECROWN',52,'#f2e5a9',True)
 label(d,(57,99),'Six original PixelFlow designs · 34 animation frames each · two outdoor elites',20,'#b7e1b8')
 for i,(kind,name,level) in enumerate(names):
  x=35+i*308;d.rounded_rectangle((x,164,x+291,695),radius=18,fill='#fafbea',outline=['#84c978','#78c8bd','#6da98b','#c6a375'][i%4],width=5)
  atlas=Image.open(ROOT/f'client/assets/tanglecrown_{kind}.png').convert('RGBA')
  idle=atlas.crop((0,0,96,96)).resize((255,255),Image.Resampling.NEAREST)
  attack=atlas.crop((4*96,2*96,5*96,3*96)).resize((195,195),Image.Resampling.NEAREST)
  im.paste(idle,(x+18,204),idle);im.paste(attack,(x+49,423),attack)
  label(d,(x+16,616),name,18,'#28503f',True);label(d,(x+17,650),'LEVEL '+level,16,'#b3773f' if 'ELITE' in level else '#628166',True)
 target=OUT/'Valhalla_Tanglecrown_Monsters.png';im.save(target,optimize=True);print(target)
if __name__=='__main__':zone_card(Path(sys.argv[1]),Path(sys.argv[2]));cast_card()
