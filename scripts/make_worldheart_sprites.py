#!/usr/bin/env python3
"""Editable PixelFlow actors for Veyrroot's canopy city and hollow heartwood."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import make_moonspore_sprites as m
from make_crag_sprites import Palette,ellipsoid,polygon,gradient

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
KINDS=['sapbeetle','lanternhornet','mosslemur','barkmimic','heart_matriarch','heart_archivist','heart_oracle','heart_travel']
RAMPS={
 'sapbeetle':('#302f36','#664838','#a6713c','#e3ae59','#ffe2a5','#45b98c'),
 'lanternhornet':('#283947','#426775','#7da869','#d7cf74','#fff2ad','#e59b61'),
 'mosslemur':('#263f3b','#49725a','#82a872','#c8d68a','#f8eab6','#e2a177'),
 'barkmimic':('#253b40','#55544a','#8b7758','#c5a479','#f1d7a0','#79ca95'),
 'heart_matriarch':('#31423e','#4c8062','#79b47b','#bddb91','#f5e4ae','#dd9a68'),
 'heart_archivist':('#303c4c','#497881','#82b5ab','#d4dbb3','#ffedba','#dfaa60'),
 'heart_oracle':('#313b51','#4a7282','#6fa9a6','#b9e1c1','#f9e9a3','#e0a5bd'),
 'heart_travel':('#2c4052','#478985','#7ac8a5','#d3e5a7','#fff1bd','#efa96e'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],accent=v[5],dark='#19282b',white='#fffcef')) for k,v in RAMPS.items()}
def paint(f,shape,colors=('ink','shadow','body','light')):
 if isinstance(shape,np.ndarray):shape=gradient(shape,12,6,85,84)
 f.paint(shape,f.p.ramp(*colors),dither=.1)
def line(f,a,b,color='body',width=3):f.line(a,b,'ol',width+2);f.line(a,b,color,width)
def eye(f,x,y):paint(f,ellipsoid(x,y,3,3),('dark','ink','shadow'));f.dots([(x-1,y-1)],'white')
def beetle(f,x,y,s,hit):
 # Flattened amber scarab with transparent resin shell and tree-tap mandibles.
 for side in [-1,1]:
  for yy in [56,69,78]:line(f,(x+side*17,y+yy-5),(x+side*(30+s),y+yy+6),'shadow',4)
 paint(f,ellipsoid(x,y+60,28,19))
 for side in [-1,1]:
  paint(f,ellipsoid(x+side*13,y+52,13,15),('ink','shadow','accent','glow'))
  line(f,(x+side*4,y+43),(x+side*12,y+22),'accent',3)
 paint(f,ellipsoid(x,y+39,10,9),('shadow','body','light','glow'))
 for side in [-1,1]:line(f,(x+side*8,y+37),(x+side*(20 if hit else 13),y+30),'accent',3)
 eye(f,x+5,y+38)
def hornet(f,x,y,s,hit):
 # Needle-winged wasp carrying an amber lantern beneath its segmented waist.
 for side in [-1,1]:
  paint(f,polygon([(x+side*5,y+47),(x+side*(27+s),y+14),(x+side*35,y+34),(x+side*13,y+55)]),('ink','shadow','body','glow'))
  line(f,(x+side*9,y+61),(x+side*19,y+77),'shadow',3)
 paint(f,ellipsoid(x,y+48,13,21));paint(f,ellipsoid(x,y+73,10,9),('shadow','accent','glow'))
 paint(f,polygon([(x-3,y+79),(x,y+88),(x+4,y+78)]),('ink','accent','glow'))
 paint(f,ellipsoid(x,y+23,11,11),('shadow','body','light','glow'))
 for side in [-1,1]:line(f,(x+side*7,y+17),(x+side*16,y+5),'accent',2)
 eye(f,x+6,y+23)
def lemur(f,x,y,s,hit):
 # Gripping paws, round ears, moss crest and a high striped ring tail.
 line(f,(x-14,y+64),(x-32,y+47+s),'shadow',10);line(f,(x-32,y+47+s),(x-35,y+18+s),'body',9)
 for yy in [24,35,46]:line(f,(x-39,y+yy+s),(x-31,y+yy+s),'accent',3)
 for side in [-1,1]:line(f,(x+side*9,y+64),(x+side*(10+s),y+84),'shadow',6)
 paint(f,ellipsoid(x,y+55,17,21));paint(f,ellipsoid(x,y+26,16,15),('shadow','body','light','glow'))
 for side in [-1,1]:
  paint(f,ellipsoid(x+side*15,y+17,7,9),('ink','accent','light'))
  paint(f,ellipsoid(x+side*7,y+26,5,6),('ink','shadow','glow'))
 eye(f,x+7,y+26)
 for j in range(3):line(f,(x+j*5-5,y+11),(x+j*6-5,y+4),'accent',3)
def mimic(f,x,y,s,hit):
 # A four-legged hollow-bark cabinet with an eye and a hinged jaw in its grain.
 for side in [-1,1]:line(f,(x+side*14,y+61),(x+side*(19+s),y+84),'shadow',7)
 paint(f,polygon([(x-23,y+29),(x+23,y+29),(x+29,y+67),(x-27,y+67)]))
 for xx in [-16,15]:line(f,(x+xx,y+35),(x+xx+2,y+59),'light',3)
 paint(f,polygon([(x-16,y+40),(x+16,y+39),(x+11,y+53),(x-12,y+53)]),('ink','shadow','accent'))
 if hit:line(f,(x-18,y+53),(x+19,y+58),'accent',4)
 eye(f,x+2,y+45)
 for side in [-1,1]:
  line(f,(x+side*24,y+44),(x+side*(35 if hit else 29),y+61),'body',6)
  paint(f,polygon([(x+side*14,y+30),(x+side*23,y+10),(x+side*10,y+20)]),('shadow','accent','light'))
def person(f,x,y,s,hit,role):
 for side in [-1,1]:line(f,(x+side*7,y+64),(x+side*(9+s),y+84),'shadow',6)
 paint(f,polygon([(x-18,y+35),(x+18,y+35),(x+22,y+75),(x-22,y+75)]))
 paint(f,ellipsoid(x,y+23,12,13),('shadow','body','glow'));eye(f,x+4,y+22)
 if role=='matriarch':
  for side in [-1,1]:paint(f,polygon([(x+side*17,y+45),(x+side*31,y+50),(x+side*28,y+76)]),('shadow','body','light'))
  paint(f,polygon([(x-25,y+15),(x-13,y+5),(x,y+12),(x+13,y+5),(x+25,y+15)]),('ink','accent','light'))
  line(f,(x-28,y+75),(x-28,y+12),'accent',4);paint(f,ellipsoid(x-28,y+11,7,9),('accent','glow'))
 elif role=='archivist':
  paint(f,polygon([(x-16,y+12),(x,y+2),(x+16,y+12)]),('shadow','body','accent'))
  paint(f,polygon([(x+15,y+43),(x+36,y+37),(x+35,y+64),(x+14,y+65)]),('ink','accent','glow'))
  for j in range(3):line(f,(x+19,y+45+j*6),(x+31,y+44+j*6),'shadow',2)
 elif role=='oracle':
  for side in [-1,1]:
   paint(f,polygon([(x+side*8,y+13),(x+side*20,y+1),(x+side*25,y+13)]),('shadow','accent','glow'))
  paint(f,ellipsoid(x,y+5,10,6),('accent','glow','white'))
  line(f,(x+26,y+71),(x+26,y+17),'accent',4);paint(f,ellipsoid(x+26,y+15,8,8),('accent','glow','white'))
 else:
  for side in [-1,1]:paint(f,polygon([(x+side*13,y+40),(x+side*39,y+20),(x+side*32,y+61)]),('ink','body','light','glow'))
  paint(f,polygon([(x-22,y+14),(x+22,y+14),(x+13,y+3),(x-13,y+3)]),('shadow','accent','glow'))
  line(f,(x-26,y+74),(x-26,y+10),'accent',4)
DRAWERS=dict(sapbeetle=beetle,lanternhornet=hornet,mosslemur=lemur,barkmimic=mimic,
             heart_matriarch=lambda f,x,y,s,h:person(f,x,y,s,h,'matriarch'),
             heart_archivist=lambda f,x,y,s,h:person(f,x,y,s,h,'archivist'),
             heart_oracle=lambda f,x,y,s,h:person(f,x,y,s,h,'oracle'),
             heart_travel=lambda f,x,y,s,h:person(f,x,y,s,h,'travel'))
m.KINDS=KINDS;m.PALETTES=PALETTES;m.DRAWERS=DRAWERS;m.ROOT=ROOT;m.ASSETS=ASSETS
def metadata(sprites):
 meta=m.metadata(sprites);meta['kinds']=KINDS;return meta
def preview():
 for kind in KINDS:m.grids(kind)
 sheet=Image.new('RGB',(8*205+12,4*220+40),'#203f3a');d=ImageDraw.Draw(sheet)
 for col,kind in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
   pose=m.draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*205,28+row*220),pose)
   d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#fff2d3')
 out=ROOT/'test-results/worldheart-cast.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
def build():
 path=ASSETS/'worldheart.txt'
 if path.exists():raise SystemExit('Worldheart sprites already exist; export preserves edits.')
 api=m._pf();sprites={}
 for kind in KINDS:
  data=m.grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'worldheart_{kind}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_worldheart_'+kind+'_all',96,96,34,PALETTES[kind].hex,fps=10)
  frame=0
  try:
   for clip,count in m.CLIPS:
    for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n');print(kind,sid,flush=True)
def export(verify=False):
 api=m._pf();path=ASSETS/'worldheart.txt';sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=api.load(sprites[kind]);assert(sp['width'],sp['height'],len(frames))==(96,96,34)
  out=Image.new('RGBA',(96*8,96*len(m.CLIPS)));offset=0
  for row,(clip,count) in enumerate(m.CLIPS):
   for n in range(count):out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*96,row*96))
   offset+=count
  target=ASSETS/f'worldheart_{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 if verify:print('Eight PixelFlow sprites and 272 frames verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build()
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build | export | verify')
