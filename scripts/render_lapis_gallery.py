#!/usr/bin/env python3
"""Share cards from private Lapis Erg game captures and editable PixelFlow creatures."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/lapis-share';OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def label(d,xy,s,size=24,fill='#f8ebc7',bold=False):d.text(xy,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=fill)
def cover(path,size):return ImageOps.fit(Image.open(path).convert('RGB'),size,Image.Resampling.LANCZOS)
def panel(im,path,box,title):
 x,y,w,h=box;im.paste(cover(path,(w,h)),(x,y));d=ImageDraw.Draw(im)
 d.rectangle((x,y+h-58,x+w,y+h),fill='#385d61');label(d,(x+22,y+h-46),title,22,'#ffe3a3',True)
def zone_card(folder):
 im=Image.new('RGB',(1920,1300),'#f6e7c3');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1920,164),fill='#365b62');label(d,(55,18),'THE LAPIS ERG  ·  THREE WATERS IN THE DUNES',53,'#ffdf99',True)
 label(d,(62,105),'LEVELS 80–85  ·  AZURE WELLS  ·  TURQUOISE OASES  ·  SUNKEN ASTROLABE',21,'#bfe6dc')
 panel(im,folder/'lapis-mirror-oasis-clean.png',(55,205,885,510),'MIRRORED OASIS  ·  BLUE WATER AND DATE PALMS')
 panel(im,folder/'lapis-astrolabe-clean.png',(980,205,885,510),'THE SUNKEN ASTROLABE  ·  SEALED INSTANCE ENTRANCE')
 panel(im,folder/'lapis-hub-clean.png',(55,750,885,370),'AZURE WELLS  ·  QUESTS, TRAVEL AND SUPPLIES')
 panel(im,folder/'lapis-east-oasis-clean.png',(980,750,885,370),'EASTERN OASIS  ·  THE MIRAGE ROC')
 d=ImageDraw.Draw(im);label(d,(64,1160),'The Sunroad from Veyrroot → Azure Wells → three oasis loops → the buried brass lens',23,'#3b6664',True)
 label(d,(64,1210),'Real private game captures · original PixelFlow creatures · original dybase2 desert score',19,'#678178')
 target=OUT/'Valhalla_Lapis_Erg_Zone_Overview.png';im.save(target,optimize=True);print(target)
def cast_card():
 folk=[('sandhopper','Sandhopper','80'),('dunefennec','Dune Fennec','81'),('glassscorpion','Glass Scorpion','82'),('sunvulture','Sun Vulture','83'),('dunecolossus','Dune Colossus','84 · ELITE'),('mirageroc','Mirage Roc','85 · ELITE')]
 im=Image.new('RGB',(1880,760),'#f6e7c3');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1880,140),fill='#365b62');label(d,(52,20),'CREATURES OF THE LAPIS ERG',52,'#ffdf99',True)
 label(d,(57,99),'Six original editable PixelFlow designs · 34 animation frames each · two outdoor elites',20,'#bfe6dc')
 for i,(kind,name,level) in enumerate(folk):
  x=35+i*308;d.rounded_rectangle((x,164,x+291,695),radius=18,fill='#fff9e9',outline=['#d9ad70','#e5bc8f','#7fc3c6','#c49c83'][i%4],width=5)
  atlas=Image.open(ROOT/f'client/assets/lapis_{kind}.png').convert('RGBA')
  idle=atlas.crop((0,0,96,96)).resize((255,255),Image.Resampling.NEAREST)
  attack=atlas.crop((4*96,2*96,5*96,3*96)).resize((195,195),Image.Resampling.NEAREST)
  im.paste(idle,(x+18,204),idle);im.paste(attack,(x+49,423),attack)
  label(d,(x+16,616),name,18,'#365b62',True);label(d,(x+17,650),'LEVEL '+level,16,'#a87346' if 'ELITE' in level else '#638d8b',True)
 target=OUT/'Valhalla_Lapis_Erg_Monsters.png';im.save(target,optimize=True);print(target)
if __name__=='__main__':zone_card(Path(sys.argv[1]));cast_card()
