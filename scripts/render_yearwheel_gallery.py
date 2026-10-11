#!/usr/bin/env python3
"""Share cards from real private Yearwheel captures and editable PixelFlow atlases."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/yearwheel-share';OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def label(d,xy,s,size=24,fill='#f8f4e8',bold=False):d.text(xy,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=fill)
def cover(path,size):
 im=Image.open(path).convert('RGB')
 im=im.crop((0,44,im.width,im.height-120))
 return ImageOps.fit(im,size,Image.Resampling.LANCZOS)
def panel(im,path,box,title,colour):
 x,y,w,h=box;im.paste(cover(path,(w,h)),(x,y));d=ImageDraw.Draw(im);d.rectangle((x,y+h-55,x+w,y+h),fill=colour);label(d,(x+18,y+h-43),title,20)
def zone_card(folder):
 im=Image.new('RGB',(2600,2040),'#e9e8df');d=ImageDraw.Draw(im)
 d.rectangle((0,0,2600,170),fill='#234d59');label(d,(58,24),'THE YEARWHEEL  ·  FOUR SEASONS, ONE WORLD',54,'#fff4d8',True)
 label(d,(64,108),'LEVELS 95–99  ·  400 × 400  ·  FOUR QUEST HUBS  ·  TWELVE ELITES  ·  FOUR SEALED THRESHOLDS',22,'#bfe8da')
 specs=[('springmere','SPRINGMERE  ·  BLOOMING GROVES','#447e63'),('solhaven','SOLHAVEN  ·  SUMMER ORCHARDS','#a7773b'),('harvestwatch','HARVESTWATCH  ·  AMBER FOREST','#8f5341'),('rimehold','RIMEHOLD  ·  WINTER BIRCHES','#547b91'),('blooming-labyrinth','BLOOMING LABYRINTH  ·  SEALED','#447e63'),('solar-crucible','SOLAR CRUCIBLE  ·  SEALED','#a7773b'),('amber-archive','AMBER ARCHIVE  ·  SEALED','#8f5341'),('silent-solstice','SILENT SOLSTICE  ·  SEALED','#547b91')]
 for i,(slug,title,col) in enumerate(specs):
  x=40+(i%4)*640;y=200+(i//4)*770;panel(im,folder/f'yearwheel-{slug}.png',(x,y,600,700),title,col)
 d=ImageDraw.Draw(im);label(d,(60,1780),'Equinox Crossing joins all four regions · each hub has a unique travel master · all instance doors remain sealed',27,'#315e61',True)
 label(d,(62,1840),'Real private browser captures · original editable PixelFlow cast · dybase2 score “Four Horizons”',22,'#4d7576')
 target=OUT/'Valhalla_Yearwheel_Zone_Overview.png';im.save(target,optimize=True);print(target)
def cast_card():
 names=[('brooknewt','Brook Newt','95'),('sundarter','Sun Darter','96'),('acornmimic','Acorn Mimic','97'),('snowstoat','Snow Stoat','98'),('bloomtortoise','Bloom Tortoise','95 ELITE'),('petalchimera','Petal Chimera','96 ELITE'),('rainseraph','Rain Seraph','97 ELITE'),('glasslion','Glass Lion','96 ELITE'),('sunwheel','Sunwheel','97 ELITE'),('firephoenix','Fire Phoenix','98 ELITE'),('lanternowl','Lantern Owl','97 ELITE'),('harvestreaper','Harvest Reaper','98 ELITE'),('ambermantis','Amber Mantis','99 ELITE'),('rimesaber','Rime Saber','97 ELITE'),('snowgiant','Snow Giant','98 ELITE'),('longnightwyrm','Longnight Wyrm','99 ELITE')]
 im=Image.new('RGB',(2240,2350),'#e9e8df');d=ImageDraw.Draw(im);d.rectangle((0,0,2240,150),fill='#234d59');label(d,(52,23),'CREATURES OF THE YEARWHEEL',53,'#fff4d8',True);label(d,(56,102),'Sixteen original PixelFlow designs · twelve outdoor elites · four distinct seasonal palettes',22,'#bfe8da')
 colours=['#86bd8f','#e4b566','#bf805c','#a8d6e9']
 for i,(kind,name,level) in enumerate(names):
  x=24+(i%4)*551;y=174+(i//4)*536;season=0 if i in [0,4,5,6] else 1 if i in [1,7,8,9] else 2 if i in [2,10,11,12] else 3
  d.rounded_rectangle((x,y,x+522,y+514),radius=19,fill='#f9faf3',outline=colours[season],width=6)
  atlas=Image.open(ROOT/f'client/assets/yearwheel_{kind}.png').convert('RGBA')
  idle=atlas.crop((0,0,96,96)).resize((376,376),Image.Resampling.NEAREST)
  im.paste(idle,(x+73,y+25),idle);label(d,(x+25,y+409),name,28,'#2e4953',True);label(d,(x+25,y+459),'LEVEL '+level,22,'#99554d' if 'ELITE' in level else '#42796d',True)
 target=OUT/'Valhalla_Yearwheel_Monsters.png';im.save(target,optimize=True);print(target)
if __name__=='__main__':zone_card(Path(sys.argv[1]));cast_card()
