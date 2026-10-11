#!/usr/bin/env python3
"""Share cards from real Veyrroot browser captures and editable PixelFlow art."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'test-results/worldheart-share';OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def label(d,xy,s,size=24,fill='#f2eccd',bold=False):d.text(xy,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=fill)
def cover(path,size):return ImageOps.fit(Image.open(path).convert('RGB'),size,Image.Resampling.LANCZOS)
def panel(im,path,box,title):
 x,y,w,h=box;im.paste(cover(path,(w,h)),(x,y));d=ImageDraw.Draw(im)
 d.rectangle((x,y+h-58,x+w,y+h),fill='#25554a');label(d,(x+22,y+h-46),title,22,'#f7e5a4',True)
def city_card(folder):
 im=Image.new('RGB',(1920,1300),'#ecf3d8');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1920,164),fill='#235a4a');label(d,(55,18),'VEYRROOT  ·  THE CITY IN A LIVING TREE',55,'#f8e8aa',True)
 label(d,(62,105),'LEVEL 80  ·  OUTER CANOPY  ⇄  HOLLOW HEARTWOOD  ·  THE SEALED SEED VAULT',21,'#c4e6ba')
 panel(im,folder/'worldheart-great-tree-clean.png',(55,205,885,510),'OUTSIDE  ·  THE GIANT TRUNK AND BRANCH RINGS')
 panel(im,folder/'worldheart-seed-vault-clean.png',(980,205,885,510),'INSIDE  ·  THE SEALED SEED VAULT')
 panel(im,folder/'worldheart-market-clean.png',(55,750,885,370),'CANOPY MARKET  ·  QUESTS, TRAVEL AND SUPPLIES')
 panel(im,folder/'worldheart-heartwood-clean.png',(980,750,885,370),'HOLLOW HALLS  ·  THE LIVING PITH')
 d=ImageDraw.Draw(im);label(d,(64,1160),'The Living Root from the Tanglecrown → open branch city → Hollow Arch → rooms within the trunk',24,'#315d4a',True)
 label(d,(64,1210),'Real private game captures · original PixelFlow actors · original dybase2 city score',19,'#5a7962')
 target=OUT/'Valhalla_Veyrroot_City_Outside_Inside.png';im.save(target,optimize=True);print(target)
def npc_card():
 folk=[('heart_matriarch','Iria Sunbark','Canopy matriarch'),('heart_archivist','Oli Amberleaf','Heartwood archivist'),
       ('heart_oracle','Veya of the Pith','Pith oracle'),('heart_travel','Travel Master Lio','Branchwing courier')]
 im=Image.new('RGB',(1640,830),'#e8f1d9');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1640,145),fill='#235a4a');label(d,(48,19),'THE PEOPLE OF VEYRROOT',59,'#f8e8aa',True)
 label(d,(52,99),'Four original editable PixelFlow designs · city life inside and outside the great tree',20,'#c4e6ba')
 for i,(kind,name,role) in enumerate(folk):
  x=30+i*402;d.rounded_rectangle((x,170,x+384,775),radius=20,fill='#fbf9e9',outline=['#70b987','#d4ae6d','#a0c2bb','#8dcba8'][i],width=5)
  atlas=Image.open(ROOT/f'client/assets/worldheart_{kind}.png').convert('RGBA')
  idle=atlas.crop((0,0,96,96)).resize((320,320),Image.Resampling.NEAREST)
  gesture=atlas.crop((4*96,2*96,5*96,3*96)).resize((222,222),Image.Resampling.NEAREST)
  im.paste(idle,(x+31,205),idle);im.paste(gesture,(x+81,480),gesture)
  label(d,(x+20,701),name,23,'#2e5948',True);label(d,(x+20,742),role,17,'#6c8666')
 target=OUT/'Valhalla_Veyrroot_NPCs.png';im.save(target,optimize=True);print(target)
if __name__=='__main__':city_card(Path(sys.argv[1]));npc_card()
