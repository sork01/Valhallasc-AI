#!/usr/bin/env python3
"""Build share images from private real-game Frostwake captures and PixelFlow atlases."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/frostwake-share';OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def label(d,xy,s,size=24,fill='#e9f8f6',bold=False):d.text(xy,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=fill)
def cover(path,size):return ImageOps.fit(Image.open(path).convert('RGB'),size,Image.Resampling.LANCZOS)
def panel(im,path,box,title):
 x,y,w,h=box;im.paste(cover(path,(w,h)),(x,y));d=ImageDraw.Draw(im)
 d.rectangle((x,y+h-58,x+w,y+h),fill='#244868');label(d,(x+22,y+h-45),title,21,'#c6f4ed',True)
def zone_card(folder):
 im=Image.new('RGB',(1920,1300),'#d7edf1');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1920,164),fill='#244668');label(d,(55,18),'FROSTWAKE SHELF  ·  LANTERNS IN THE BLUE ICE',49,'#e4faf7',True)
 label(d,(62,106),'LEVELS 85–90  ·  FROSTWAKE STATION  ·  AURORA  ·  THREE ELITE TERRITORIES',21,'#9adfd9')
 panel(im,folder/'frostwake-leviathan-rib-clean.png',(55,205,885,510),'BLUE CREVASSES  ·  THE DEEP ICE RIB')
 panel(im,folder/'frostwake-aurora-obelisk-clean.png',(980,205,885,510),'AURORA OBELISK  ·  NORTHERN SHELF')
 panel(im,folder/'frostwake-hub-clean.png',(55,750,885,370),'FROSTWAKE STATION  ·  QUESTS AND TRAVEL')
 panel(im,folder/'frostwake-frozen-pool-clean.png',(980,750,885,370),'FROZEN POOL  ·  SNOWFIELD CIRCUIT')
 d=ImageDraw.Draw(im);label(d,(64,1160),'The Snowline from the Lapis Erg → lantern camp → fissure roads → aurora courts',23,'#315f7b',True)
 label(d,(64,1210),'Real private game captures · original PixelFlow cast · original dybase2 glacier score',19,'#5b8294')
 target=OUT/'Valhalla_Frostwake_Zone_Overview.png';im.save(target,optimize=True);print(target)
def cast_card():
 folk=[('snowhare','Snow Hare','85'),('iceotter','Ice Otter','86'),('frostheron','Frost Heron','87'),('glaciercrab','Glacier Crab','88'),('bellmammoth','Bell Mammoth','88 · ELITE'),('auroramanta','Aurora Manta','89 · ELITE'),('crevasseleviathan','Crevasse Leviathan','90 · ELITE')]
 im=Image.new('RGB',(2040,760),'#d7edf1');d=ImageDraw.Draw(im)
 d.rectangle((0,0,2040,140),fill='#244668');label(d,(52,20),'CREATURES OF FROSTWAKE SHELF',52,'#e4faf7',True)
 label(d,(57,99),'Seven original editable PixelFlow designs · 34 animation frames each · three outdoor elites',20,'#9adfd9')
 for i,(kind,name,level) in enumerate(folk):
  x=25+i*287;d.rounded_rectangle((x,164,x+273,695),radius=18,fill='#eef8f8',outline=['#8fc6d3','#7ab9c5','#a6dae0','#729fbf'][i%4],width=5)
  atlas=Image.open(ROOT/f'client/assets/frostwake_{kind}.png').convert('RGBA')
  idle=atlas.crop((0,0,96,96)).resize((242,242),Image.Resampling.NEAREST)
  attack=atlas.crop((4*96,2*96,5*96,3*96)).resize((187,187),Image.Resampling.NEAREST)
  im.paste(idle,(x+16,206),idle);im.paste(attack,(x+43,424),attack)
  label(d,(x+14,618),name,17,'#244668',True);label(d,(x+15,651),'LEVEL '+level,15,'#8b6680' if 'ELITE' in level else '#497b96',True)
 target=OUT/'Valhalla_Frostwake_Monsters.png';im.save(target,optimize=True);print(target)
if __name__=='__main__':zone_card(Path(sys.argv[1]));cast_card()
