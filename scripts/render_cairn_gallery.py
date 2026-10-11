#!/usr/bin/env python3
"""Build share images from private real-game Cairnspine captures and PixelFlow atlases."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/cairn-share';OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def label(d,xy,s,size=24,fill='#e9f8f6',bold=False):d.text(xy,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=fill)
def cover(path,size):return ImageOps.fit(Image.open(path).convert('RGB'),size,Image.Resampling.LANCZOS)
def panel(im,path,box,title):
 x,y,w,h=box;im.paste(cover(path,(w,h)),(x,y));d=ImageDraw.Draw(im)
 d.rectangle((x,y+h-58,x+w,y+h),fill='#244868');label(d,(x+22,y+h-45),title,21,'#e9d3a8',True)
def zone_card(folder):
 im=Image.new('RGB',(1920,1300),'#ded8cd');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1920,164),fill='#39434f');label(d,(55,18),'THE CAIRNSPINE  ·  THE HIGH PASS RINGS',49,'#f6e8cc',True)
 label(d,(62,106),'LEVELS 90–95  ·  BOULDERWATCH  ·  LEAFLESS GROVES  ·  THREE ELITES',21,'#d8c19a')
 panel(im,folder/'cairn-thunderheart-gate-clean.png',(55,205,885,510),'THE THUNDERHEART GATE  ·  SEALED INSTANCE')
 panel(im,folder/'cairn-whitebark-grove-clean.png',(980,205,885,510),'WHITEBARK GROVE  ·  LEAFLESS TREES')
 panel(im,folder/'cairn-hub-clean.png',(55,750,885,370),'BOULDERWATCH  ·  QUESTS AND TRAVEL')
 panel(im,folder/'cairn-singing-cairn-clean.png',(980,750,885,370),'SINGING CAIRN  ·  BOULDER SWITCHBACK')
 d=ImageDraw.Draw(im);label(d,(64,1160),'The High Pass from Frostwake → Boulderwatch → four switchbacks → Thunderheart Gate',23,'#315f7b',True)
 label(d,(64,1210),'Real private game captures · original PixelFlow cast · original dybase2 mountain score',19,'#5b8294')
 target=OUT/'Valhalla_Cairnspine_Zone_Overview.png';im.save(target,optimize=True);print(target)
def cast_card():
 folk=[('screeferret','Scree Ferret','90'),('stoneibex','Stone Ibex','91'),('slateraven','Slate Raven','92'),('ridgeadder','Ridge Adder','93'),('cairnbehemoth','Cairn Behemoth','93 · ELITE'),('whitebarktitan','Whitebark Titan','94 · ELITE'),('stormcondor','Storm Condor','95 · ELITE')]
 im=Image.new('RGB',(2040,760),'#ded8cd');d=ImageDraw.Draw(im)
 d.rectangle((0,0,2040,140),fill='#39434f');label(d,(52,20),'CREATURES OF THE CAIRNSPINE',52,'#f6e8cc',True)
 label(d,(57,99),'Seven original editable PixelFlow designs · 34 animation frames each · three outdoor elites',20,'#d8c19a')
 for i,(kind,name,level) in enumerate(folk):
  x=25+i*287;d.rounded_rectangle((x,164,x+273,695),radius=18,fill='#eef8f8',outline=['#8fc6d3','#7ab9c5','#a6dae0','#729fbf'][i%4],width=5)
  atlas=Image.open(ROOT/f'client/assets/cairn_{kind}.png').convert('RGBA')
  idle=atlas.crop((0,0,96,96)).resize((242,242),Image.Resampling.NEAREST)
  attack=atlas.crop((4*96,2*96,5*96,3*96)).resize((187,187),Image.Resampling.NEAREST)
  im.paste(idle,(x+16,206),idle);im.paste(attack,(x+43,424),attack)
  label(d,(x+14,618),name,17,'#39434f',True);label(d,(x+15,651),'LEVEL '+level,15,'#8b6680' if 'ELITE' in level else '#497b96',True)
 target=OUT/'Valhalla_Cairnspine_Monsters.png';im.save(target,optimize=True);print(target)
if __name__=='__main__':zone_card(Path(sys.argv[1]));cast_card()
