#!/usr/bin/env python3
"""Thirteen original editable PixelFlow atlases for The Cairnspine."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import make_moonspore_sprites as m
import cairn_cel_redraw as cel
from make_crag_sprites import Palette,ellipsoid,polygon,gradient
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
KINDS=['screeferret','stoneibex','slateraven','ridgeadder','cairnbehemoth','whitebarktitan','stormcondor','cairn_warden','cairn_surveyor','cairn_stonesinger','cairn_grovekeeper','cairn_windseer','cairn_travel']
RAMPS={
 'screeferret':('#312d3d','#655e65','#9d8c73','#d2c0a0','#f3e3c1','#c7925d'),
 'stoneibex':('#2c3339','#656c65','#978d75','#dbcaa5','#f5ead0','#a77a55'),
 'slateraven':('#1e2936','#3f5064','#657488','#a8adbb','#ddd6ca','#e3a762'),
 'ridgeadder':('#2b3034','#596c65','#8ca085','#d0bd80','#efe1b0','#c67e5d'),
 'cairnbehemoth':('#292c36','#555b63','#828178','#b8aa8d','#e3ca91','#d99a55'),
 'whitebarktitan':('#32343a','#6c6e6c','#aaa79a','#e5dfc8','#fff2d0','#a7bdac'),
 'stormcondor':('#232c43','#465d70','#7b8b8c','#c8c4af','#efe4bb','#85cbcc'),
 'cairn_warden':('#45373e','#765c59','#aa7963','#ddae87','#f0d7ae','#dfa65b'),
 'cairn_surveyor':('#333a40','#69707a','#9e9b8e','#d4c6a7','#eadfc1','#d19862'),
 'cairn_stonesinger':('#3e3743','#776570','#a88d83','#dbc7ac','#eee4c7','#b9a78f'),
 'cairn_grovekeeper':('#343c3c','#67766b','#a2a895','#d6d4bd','#f4ecd1','#b9d0a2'),
 'cairn_windseer':('#293b48','#596d77','#8ca1a2','#d4c5b4','#f0e1bd','#8ac6c7'),
 'cairn_travel':('#3b3b42','#6e7570','#a5a185','#ddd0ad','#fff0c9','#cfac74'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],accent=v[5],dark='#172736',white='#ffffff')) for k,v in RAMPS.items()}
def paint(f,shape,colors=('ink','shadow','body','light')):
 if isinstance(shape,np.ndarray):shape=gradient(shape,12,6,85,84)
 f.paint(shape,f.p.ramp(*colors),dither=.1)
def line(f,a,b,c='body',w=3):f.line(a,b,'ol',w+2);f.line(a,b,c,w)
def eye(f,x,y):paint(f,ellipsoid(x,y,3,3),('dark','ink','shadow'));f.dots([(x-1,y-1)],'white')
def hare(f,x,y,s,hit):
 for side in [-1,1]:
  line(f,(x+side*13,y+62),(x+side*(17+s),y+82),'shadow',6)
  paint(f,polygon([(x+side*14,y+32),(x+side*10,y+4),(x+side*21,y+7),(x+side*23,y+36)]),('ink','body','light'))
 paint(f,ellipsoid(x-8,y+60,23,17));paint(f,ellipsoid(x+17,y+39,16,15),('shadow','body','light','glow'))
 paint(f,ellipsoid(x-30,y+58,9,9),('light','glow'))
 eye(f,x+24,y+38)
 if hit:line(f,(x+24,y+58),(x+37,y+48),'accent',3)
def otter(f,x,y,s,hit):
 line(f,(x-24,y+59),(x-44,y+69+s),'shadow',13)
 for side in [-1,1]:
  line(f,(x+side*16,y+69),(x+side*(23+s),y+82),'shadow',6)
 paint(f,ellipsoid(x,y+59,30,15));paint(f,ellipsoid(x+24,y+47,15,13),('shadow','body','light','glow'))
 for side in [-1,1]:paint(f,ellipsoid(x+19+side*10,y+37,5,6),('ink','shadow','light'))
 eye(f,x+30,y+44)
 for side in [-1,1]:line(f,(x+35,y+52),(x+43,y+50+side*5),'light',1)
def heron(f,x,y,s,hit):
 for side in [-1,1]:line(f,(x+side*7,y+62),(x+side*(9+s),y+84),'shadow',4)
 paint(f,ellipsoid(x,y+53,17,22));paint(f,polygon([(x+2,y+41),(x+1,y+18),(x+7,y+15),(x+13,y+42)]),('shadow','body','light'))
 paint(f,ellipsoid(x+8,y+17,10,11),('body','light','glow'))
 paint(f,polygon([(x+15,y+18),(x+39,y+22),(x+18,y+29)]),('ink','accent','glow'))
 for side in [-1,1]:paint(f,polygon([(x+side*9,y+45),(x+side*30,y+39+s),(x+side*18,y+65)]),('ink','shadow','light'))
 eye(f,x+11,y+16)
def crab(f,x,y,s,hit):
 for side in [-1,1]:
  for j in range(3):line(f,(x+side*(10+j*6),y+59),(x+side*(27+j*5),y+80),'shadow',4)
  line(f,(x+side*15,y+52),(x+side*32,y+42+s),'body',6)
  paint(f,polygon([(x+side*30,y+37+s),(x+side*43,y+29+s),(x+side*38,y+48+s)]),('ink','accent','light'))
 paint(f,ellipsoid(x,y+57,27,19),('ink','shadow','body','light'))
 for j in [-1,0,1]:line(f,(x+j*11,y+49),(x+j*11-5,y+65),'accent',2)
 eye(f,x-10,y+52);eye(f,x+10,y+52)
def mammoth(f,x,y,s,hit):
 for side in [-1,1]:
  line(f,(x+side*16,y+58),(x+side*(18+s),y+82),'shadow',12)
  paint(f,ellipsoid(x+side*27,y+43,14,20),('ink','shadow','body'))
 paint(f,ellipsoid(x,y+47,30,30));paint(f,ellipsoid(x+8,y+31,23,22),('shadow','body','light','glow'))
 line(f,(x+24,y+41),(x+30,y+72+s),'body',11)
 for side in [-1,1]:
  line(f,(x+side*23,y+39),(x+side*34,y+65),'light',7)
  paint(f,ellipsoid(x+side*17,y+61,5,6),('ink','accent','glow'))
 eye(f,x+13,y+29)
def manta(f,x,y,s,hit):
 paint(f,polygon([(x-35,y+57),(x-22,y+27),(x,y+37),(x+22,y+27),(x+35,y+57),(x+9,y+67),(x,y+78),(x-9,y+67)]),('ink','shadow','body','light'))
 for side in [-1,1]:
  paint(f,polygon([(x+side*22,y+27),(x+side*(36+s),y+23),(x+side*33,y+45),(x+side*7,y+61)]),('shadow','body','light','accent'))
  line(f,(x+side*8,y+57),(x+side*16,y+79),'accent',3)
 eye(f,x-8,y+47);eye(f,x+8,y+47)
 for j in range(5):line(f,(x-20+j*10,y+50),(x-15+j*8,y+60),'accent',2)
def leviathan(f,x,y,s,hit):
 line(f,(x-39,y+73),(x-23,y+61+s),'shadow',13)
 line(f,(x-23,y+61+s),(x+3,y+68),'body',17)
 line(f,(x+3,y+68),(x+23,y+49),'shadow',18)
 paint(f,ellipsoid(x+23,y+39,19,17),('shadow','body','light','glow'))
 for j in range(4):
  xx=-24+j*15;paint(f,polygon([(xx,y+58),(xx+5,y+37-j%2*4),(xx+11,y+59)]),('ink','accent','light'))
 for side in [-1,1]:paint(f,polygon([(x+25+side*9,y+32),(x+25+side*11,y+8),(x+31+side*12,y+36)]),('ink','body','light'))
 eye(f,x+31,y+38)
 if hit:line(f,(x+29,y+55),(x+43,y+61),'accent',4)
def person(f,x,y,s,hit,role):
 for side in [-1,1]:line(f,(x+side*9,y+61),(x+side*(10+s),y+84),'shadow',7)
 paint(f,polygon([(x-18,y+33),(x+18,y+33),(x+22,y+74),(x-22,y+74)]))
 for side in [-1,1]:line(f,(x+side*17,y+44),(x+side*25,y+68),'body',8)
 paint(f,ellipsoid(x,y+25,12,14),('shadow','light','glow'));eye(f,x+4,y+24)
 paint(f,polygon([(x-24,y+18),(x-18,y+4),(x+18,y+4),(x+24,y+18)]),('ink','body','light'))
 if role=='captain':
  line(f,(x-30,y+71),(x-30,y+7),'accent',4);paint(f,polygon([(x-30,y+8),(x-5,y+20),(x-30,y+31)]),('shadow','accent','glow'))
 elif role=='surveyor':
  line(f,(x+26,y+72),(x+26,y+8),'accent',3);paint(f,ellipsoid(x+26,y+9,7,7),('accent','glow'))
  paint(f,polygon([(x+10,y+50),(x+35,y+48),(x+29,y+67),(x+12,y+65)]),('shadow','body','glow'))
 elif role=='bellkeeper':
  for side in [-1,1]:paint(f,ellipsoid(x+side*27,y+65,7,8),('ink','accent','glow'))
 elif role=='skywatcher':
  for side in [-1,1]:line(f,(x+side*17,y+35),(x+side*28,y+16),'accent',3)
  paint(f,ellipsoid(x+28,y+16,8,8),('accent','glow'))
 elif role=='ribkeeper':
  line(f,(x-28,y+74),(x-28,y+9),'accent',5)
  for j in range(3):line(f,(x-38+j*9,y+18),(x-28,y+8),'light',2)
 else:
  line(f,(x+29,y+70),(x+29,y+9),'accent',4)
  paint(f,polygon([(x+29,y+9),(x+43,y+23),(x+29,y+37)]),('accent','light','glow'))
def ferret(f,x,y,s,hit):
 line(f,(x-25,y+64),(x-42,y+56+s),'shadow',8)
 for side in [-1,1]:line(f,(x+side*13,y+65),(x+side*(16+s),y+82),'shadow',5)
 paint(f,ellipsoid(x-5,y+57,32,13),('ink','shadow','body','light'))
 paint(f,ellipsoid(x+27,y+48,13,11),('shadow','body','light','glow'))
 for side in [-1,1]:paint(f,ellipsoid(x+23+side*9,y+37,4,5),('ink','shadow','light'))
 eye(f,x+32,y+46)
def raven(f,x,y,s,hit):
 for side in [-1,1]:
  line(f,(x+side*8,y+66),(x+side*(10+s),y+84),'shadow',4)
  paint(f,polygon([(x+side*7,y+43),(x+side*(32+s),y+32),(x+side*24,y+66),(x+side*8,y+68)]),('ink','shadow','body','light'))
 paint(f,ellipsoid(x,y+57,19,23));paint(f,ellipsoid(x+9,y+32,13,14),('shadow','body','light','glow'))
 paint(f,polygon([(x+20,y+29),(x+36,y+36),(x+19,y+39)]),('ink','accent','glow'))
 for j in range(3):line(f,(x-15+j*6,y+70),(x-28+j*6,y+76),'body',3)
 eye(f,x+14,y+31)
def ibex(f,x,y,s,hit):
 for side in [-1,1]:line(f,(x+side*16,y+57),(x+side*(20+s),y+83),'shadow',7)
 paint(f,ellipsoid(x,y+54,31,21));paint(f,ellipsoid(x+22,y+43,15,14),('shadow','body','light','glow'))
 for side in [-1,1]:
  line(f,(x+20+side*9,y+33),(x+20+side*15,y+12),'accent',5)
  line(f,(x+20+side*15,y+12),(x+18+side*17,y+3),'light',4)
 eye(f,x+28,y+40)
def adder(f,x,y,s,hit):
 for j in range(5):paint(f,ellipsoid(x-28+j*13,y+68-abs(j-2)*5,13,9),('ink','shadow','body','light'))
 paint(f,ellipsoid(x+29,y+46,14,12),('shadow','body','light','glow'))
 for side in [-1,1]:paint(f,polygon([(x+26+side*7,y+34),(x+28+side*10,y+18),(x+32+side*5,y+36)]),('ink','accent','light'))
 eye(f,x+33,y+43)
def behemoth(f,x,y,s,hit):
 for side in [-1,1]:
  line(f,(x+side*23,y+58),(x+side*(27+s),y+84),'shadow',13)
  paint(f,polygon([(x+side*30,y+34),(x+side*44,y+14),(x+side*38,y+61),(x+side*16,y+59)]),('ink','shadow','body','light'))
 paint(f,polygon([(x-31,y+28),(x-13,y+17),(x+10,y+21),(x+32,y+35),(x+26,y+67),(x-23,y+67)]),('ink','shadow','body','light'))
 for j in range(4):paint(f,polygon([(x-19+j*11,y+28),(x-15+j*10,y+10-j%2*4),(x-6+j*11,y+27)]),('ink','accent','light'))
 eye(f,x+14,y+39)
def titan(f,x,y,s,hit):
 for side in [-1,1]:
  line(f,(x+side*17,y+57),(x+side*(20+s),y+84),'shadow',12)
  line(f,(x+side*22,y+40),(x+side*29,y+15+s),'body',11)
  for k in range(3):line(f,(x+side*(29+k*3),y+25-k*5),(x+side*(28+k*4),y+11-k*8),'light',4)
 paint(f,ellipsoid(x,y+49,29,29),('ink','shadow','body','light'))
 for j in range(4):line(f,(x-15+j*10,y+34),(x-25+j*12,y+11),'light',5)
 paint(f,ellipsoid(x,y+28,19,17),('shadow','body','light','glow'))
 eye(f,x+8,y+27)
def condor(f,x,y,s,hit):
 paint(f,ellipsoid(x,y+51,18,25));
 for side in [-1,1]:
  paint(f,polygon([(x+side*8,y+42),(x+side*(32+s),y+16),(x+side*29,y+59),(x+side*12,y+66)]),('ink','shadow','body','light'))
  for j in range(3):line(f,(x+side*(20+j*6),y+42),(x+side*(24+j*5),y+61),'accent',3)
 line(f,(x,y+62),(x+2,y+83),'shadow',6)
 paint(f,ellipsoid(x+8,y+28,11,13),('shadow','body','light','glow'))
 paint(f,polygon([(x+17,y+29),(x+34,y+35),(x+16,y+41)]),('ink','accent','glow'))
 eye(f,x+11,y+27)
DRAWERS=dict(screeferret=ferret,stoneibex=ibex,slateraven=raven,ridgeadder=adder,cairnbehemoth=behemoth,whitebarktitan=titan,stormcondor=condor,
             cairn_warden=lambda f,x,y,s,h:person(f,x,y,s,h,'captain'),cairn_surveyor=lambda f,x,y,s,h:person(f,x,y,s,h,'surveyor'),
             cairn_stonesinger=lambda f,x,y,s,h:person(f,x,y,s,h,'bellkeeper'),cairn_grovekeeper=lambda f,x,y,s,h:person(f,x,y,s,h,'skywatcher'),
             cairn_windseer=lambda f,x,y,s,h:person(f,x,y,s,h,'ribkeeper'),cairn_travel=lambda f,x,y,s,h:person(f,x,y,s,h,'travel'))
# The seven enemies are the cel-shaded redraw in cairn_cel_redraw.py (2026-10-18). The NPCs keep the old drawers above, so
# `m._old_draw` (the pre-redraw Frame pipeline) still serves them.
PALETTES.update(cel.PALETTES)
m.KINDS=KINDS;m.PALETTES=PALETTES;m.DRAWERS=DRAWERS;m.ROOT=ROOT;m.ASSETS=ASSETS
from make_crag_sprites import rgba
m.draw=lambda kind,clip,n:rgba(cel.draw(kind,clip,n),PALETTES[kind].hex) if kind in cel.KINDS else m._old_draw(kind,clip,n)
def metadata(sprites):
 meta=m.metadata(sprites);meta['kinds']=KINDS;return meta
def preview():
 for kind in KINDS:m.grids(kind)
 sheet=Image.new('RGB',(len(KINDS)*205+12,4*220+40),'#293e58');d=ImageDraw.Draw(sheet)
 for col,kind in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
   pose=m.draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*205,28+row*220),pose)
   d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#e9f8ff')
 out=ROOT/'test-results/cairn-cast.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
def build(replace=False):
 path=ASSETS/'cairn.txt'
 api=m._pf();sprites={};kinds=KINDS
 if path.exists():
  if not replace:raise SystemExit('Cairnspine sprites already exist; export preserves edits. build --replace redoes the redrawn enemies only.')
  sprites=json.loads(path.read_text())['sprites'];kinds=list(cel.KINDS)
  for kind in kinds:assert api.api('delete',{'sprite_id':sprites.pop(kind)}).get('ok')
 for kind in kinds:
  data=m.grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'cairn_{kind}_raw.npz',**{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_cairn_'+kind+'_all',96,96,34,PALETTES[kind].hex,fps=10)
  frame=0
  try:
   for clip,count in m.CLIPS:
    for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
  print(kind,sid,flush=True)
def export(verify=False):
 api=m._pf();path=ASSETS/'cairn.txt';sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=api.load(sprites[kind]);assert(sp['width'],sp['height'],len(frames))==(96,96,34)
  out=Image.new('RGBA',(96*8,96*len(m.CLIPS)));offset=0
  for row,(clip,count) in enumerate(m.CLIPS):
   for n in range(count):out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*96,row*96))
   offset+=count
  target=ASSETS/f'cairn_{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 if verify:print('Cairnspine PixelFlow atlases verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build('--replace' in sys.argv[2:])
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build [--replace] | export | verify')
