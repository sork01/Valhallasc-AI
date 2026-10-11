#!/usr/bin/env python3
"""Nine editable 34-frame PixelFlow sprites for The Tanglecrown."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import make_moonspore_sprites as m
from make_crag_sprites import Palette,ellipsoid,polygon,gradient
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'client/assets'
KINDS=['orchidmantis','canopyglider','poolcaiman','drumgorilla','jadeanaconda','crownjaguar','tangle_warden','tangle_scholar','tangle_travel']
RAMPS={
 'orchidmantis':('#263d39','#407b58','#80c76c','#d5ef83','#ffe6bb','#ec73aa'),
 'canopyglider':('#263d55','#327d85','#59c0b5','#c9e5a4','#fff1ce','#eea35d'),
 'poolcaiman':('#283f37','#3d7962','#6ea58c','#b9d5a1','#f5e9b4','#d78462'),
 'drumgorilla':('#3b3540','#6d4d58','#9d6e5d','#c69a70','#ffe4ac','#50b599'),
 'jadeanaconda':('#253c40','#267b6b','#4dc098','#a9e3a6','#e8f5c5','#e6a95b'),
 'crownjaguar':('#343d39','#80583d','#ce9852','#f1ce73','#fff0c3','#2c9a73'),
 'tangle_warden':('#273c3e','#357b60','#57ae7b','#bada91','#f6e7b8','#e7a264'),
 'tangle_scholar':('#333d4d','#527889','#8ab2a7','#d6dbc1','#fff0ca','#d8a76f'),
 'tangle_travel':('#283f48','#3f8f8a','#75c8a7','#d4e0aa','#fff2ca','#e8b965'),
}
PALETTES={k:Palette(dict(ink=v[0],shadow=v[1],body=v[2],light=v[3],glow=v[4],accent=v[5],dark='#1c292b',white='#fffcdf')) for k,v in RAMPS.items()}
def paint(f,shape,colors=('ink','shadow','body','light')):
 if isinstance(shape,np.ndarray):shape=gradient(shape,12,6,85,84)
 f.paint(shape,f.p.ramp(*colors),dither=.1)
def line(f,a,b,color='body',width=3):f.line(a,b,'ol',width+2);f.line(a,b,color,width)
def eye(f,x,y):paint(f,ellipsoid(x,y,3,3),('dark','ink','shadow'));f.dots([(x-1,y-1)],'white')
def mantis(f,x,y,s,hit):
 # Thin insect torso, folded orchid petals and two long sickle forearms.
 for side in [-1,1]:
  paint(f,polygon([(x+side*6,y+52),(x+side*32,y+25),(x+side*40,y+50),(x+side*16,y+68)]),('shadow','accent','light','glow'))
  line(f,(x+side*12,y+64),(x+side*(17+s),y+84),'shadow',4)
  line(f,(x+side*16,y+40),(x+side*(30 if hit else 28),y+18),'body',5)
  line(f,(x+side*(30 if hit else 28),y+18),(x+side*(38 if hit else 27),y+39),'accent',5)
 paint(f,ellipsoid(x,y+52,13,20));paint(f,ellipsoid(x,y+25,17,10),('shadow','body','light','glow'))
 for side in [-1,1]:eye(f,x+side*8,y+24);line(f,(x+side*9,y+19),(x+side*16,y+6),'accent',2)
def glider(f,x,y,s,hit):
 # Flying squirrel with broad translucent membranes, tiny paws and curled tail.
 line(f,(x-20,y+61),(x-35,y+43+s),'accent',8);line(f,(x-35,y+43+s),(x-33,y+27+s),'accent',6)
 for side in [-1,1]:
  paint(f,polygon([(x+side*9,y+38),(x+side*(36+s),y+21),(x+side*32,y+66),(x+side*12,y+64)]),('ink','shadow','body','light'))
  line(f,(x+side*34,y+62),(x+side*33,y+78),'shadow',3)
 paint(f,ellipsoid(x,y+52,14,19));paint(f,ellipsoid(x+3,y+28,13,13),('shadow','body','light','glow'))
 for side in [-1,1]:paint(f,ellipsoid(x+side*12,y+19,8,8),('ink','body','light'))
 eye(f,x+8,y+27)
def caiman(f,x,y,s,hit):
 # Low crocodilian wedge with segmented back, armored tail and a split jaw.
 line(f,(x-22,y+65),(x-41,y+57+s),'body',12)
 paint(f,polygon([(x-34,y+52),(x+17,y+49),(x+31,y+62),(x+16,y+76),(x-29,y+74)]))
 for j in range(5):paint(f,polygon([(x-27+j*11,y+52),(x-22+j*11,y+43),(x-17+j*11,y+52)]),('ink','shadow','light'))
 for xx in [-22,-7,15]:line(f,(x+xx,y+70),(x+xx+s,y+83),'shadow',5)
 paint(f,polygon([(x+16,y+54),(x+41,y+56),(x+42,y+65),(x+16,y+67)]),('ink','body','light'))
 line(f,(x+22,y+65),(x+41,y+68 if hit else y+65),'accent',2);eye(f,x+26,y+52)
def gorilla(f,x,y,s,hit):
 # Broad-shouldered ape with knuckle arms and two resonant chest patches.
 for side in [-1,1]:
  line(f,(x+side*24,y+42),(x+side*(36 if hit else 31),y+76),'shadow',12)
  paint(f,ellipsoid(x+side*(37 if hit else 31),y+77,8,7),('ink','shadow','light'))
  line(f,(x+side*12,y+68),(x+side*(13+s),y+84),'shadow',9)
 paint(f,ellipsoid(x,y+56,27,24));paint(f,ellipsoid(x,y+28,16,16),('ink','shadow','body','light'))
 for side in [-1,1]:paint(f,ellipsoid(x+side*11,y+52,9,12),('shadow','accent','glow'))
 eye(f,x-5,y+25);eye(f,x+5,y+25);line(f,(x-6,y+36),(x+7,y+36),'accent',2)
def anaconda(f,x,y,s,hit):
 # Huge emerald coil rising into a hooded serpent head.
 paint(f,ellipsoid(x,y+68,35,17));paint(f,ellipsoid(x+7,y+65,20,9),('shadow','light','glow'))
 line(f,(x-22,y+68),(x-39,y+51+s),'body',10)
 line(f,(x+7,y+60),(x+5,y+21),'body',15)
 paint(f,polygon([(x+4,y+44),(x-19,y+32),(x-13,y+12),(x+6,y+24),(x+25,y+12),(x+29,y+35)]),('ink','shadow','body','light'))
 paint(f,ellipsoid(x+9,y+23,14,10),('shadow','body','light','glow'))
 paint(f,polygon([(x+14,y+28),(x+37,y+32),(x+23,y+39)]),('ink','body','light'))
 eye(f,x+15,y+20)
 if hit:line(f,(x+29,y+35),(x+40,y+48),'accent',2)
def jaguar(f,x,y,s,hit):
 # Powerful cat with leaf crown, spotted flanks and a long curling tail.
 line(f,(x-27,y+57),(x-42,y+38+s),'shadow',9);line(f,(x-42,y+38+s),(x-39,y+25+s),'body',8)
 paint(f,ellipsoid(x-2,y+60,30,18))
 for xx in [-23,-11,16,26]:line(f,(x+xx,y+69),(x+xx+s,y+84),'shadow',7)
 for j in range(6):paint(f,ellipsoid(x-22+j*9,y+54+j%2*8,3,3),('ink','shadow','accent'))
 paint(f,ellipsoid(x+24,y+40,15,14),('shadow','body','light','glow'))
 for side in [-1,1]:paint(f,polygon([(x+23+side*9,y+29),(x+24+side*10,y+15),(x+27+side*13,y+28)]),('ink','accent','light'))
 eye(f,x+28,y+39);paint(f,polygon([(x+37,y+47),(x+43,y+52),(x+35,y+54)]),('ink','accent','glow'))
 for j in range(3):line(f,(x+9+j*7,y+26),(x+10+j*9,y+9),'accent',3)
def person(f,x,y,s,hit,role):
 for side in [-1,1]:line(f,(x+side*8,y+65),(x+side*(9+s),y+84),'shadow',6)
 paint(f,polygon([(x-18,y+34),(x+18,y+34),(x+23,y+76),(x-23,y+76)]))
 paint(f,ellipsoid(x,y+23,12,13),('shadow','light','glow'));eye(f,x+4,y+22)
 if role=='warden':
  paint(f,polygon([(x-25,y+13),(x,y+4),(x+25,y+13),(x+18,y+19),(x-18,y+19)]),('shadow','body','accent'))
  line(f,(x-27,y+72),(x-27,y+16),'accent',4);paint(f,ellipsoid(x-27,y+16,7,8),('accent','glow'))
 elif role=='scholar':
  paint(f,polygon([(x-19,y+9),(x,y+1),(x+19,y+9)]),('shadow','body','accent'))
  line(f,(x+22,y+71),(x+22,y+9),'accent',5);paint(f,ellipsoid(x+22,y+7,8,10),('accent','light','glow'))
 else:
  paint(f,polygon([(x-24,y+14),(x+24,y+14),(x+16,y+5),(x-16,y+5)]),('accent','light','glow'))
  paint(f,ellipsoid(x-24,y+56,11,15));line(f,(x+26,y+70),(x+26,y+14),'accent',4)
  paint(f,polygon([(x+25,y+13),(x+42,y+24),(x+25,y+34)]),('accent','light','glow'))
DRAWERS=dict(orchidmantis=mantis,canopyglider=glider,poolcaiman=caiman,drumgorilla=gorilla,jadeanaconda=anaconda,crownjaguar=jaguar,tangle_warden=lambda f,x,y,s,h:person(f,x,y,s,h,'warden'),tangle_scholar=lambda f,x,y,s,h:person(f,x,y,s,h,'scholar'),tangle_travel=lambda f,x,y,s,h:person(f,x,y,s,h,'travel'))
m.KINDS=KINDS;m.PALETTES=PALETTES;m.DRAWERS=DRAWERS;m.ROOT=ROOT;m.ASSETS=ASSETS

def metadata(sprites):
 meta=m.metadata(sprites);meta['kinds']=KINDS;return meta


def preview():
 for kind in KINDS:m.grids(kind)
 sheet=Image.new('RGB',(9*205+12,4*220+40),'#28344a');d=ImageDraw.Draw(sheet)
 for col,kind in enumerate(KINDS):
  for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
   pose=m.draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
   sheet.paste(pose,(10+col*205,28+row*220),pose)
   d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#fff2d3')
 out=ROOT/'test-results/tanglecrown-cast.png';out.parent.mkdir(exist_ok=True)
 sheet.save(out);print(out)


def build():
 path=ASSETS/'tanglecrown.txt'
 if path.exists():raise SystemExit('Tanglecrown sprites already exist; export preserves edits.')
 api=m._pf();sprites={}
 for kind in KINDS:
  data=m.grids(kind)
  np.savez_compressed(ROOT/'scripts'/f'tanglecrown_{kind}_raw.npz',
                      **{clip:np.stack(rows) for clip,rows in data.items()})
  sid=api.create('valhallasc_tanglecrown_'+kind+'_all',96,96,34,
                 PALETTES[kind].hex,fps=10)
  frame=0
  try:
   for clip,count in m.CLIPS:
    for grid in data[clip]:api.draw_grid(sid,frame,0,grid);frame+=1
  except Exception:
   api.api('delete',{'sprite_id':sid});raise
  sprites[kind]=sid;path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')
  print(kind,sid,flush=True)


def export(verify=False):
 api=m._pf();path=ASSETS/'tanglecrown.txt'
 sprites=json.loads(path.read_text())['sprites']
 for kind in KINDS:
  sp,frames=api.load(sprites[kind]);assert(sp['width'],sp['height'],len(frames))==(96,96,34)
  out=Image.new('RGBA',(96*8,96*len(m.CLIPS)));offset=0
  for row,(clip,count) in enumerate(m.CLIPS):
   for n in range(count):
    out.alpha_composite(Image.fromarray(api.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),(n*96,row*96))
   offset+=count
  target=ASSETS/f'tanglecrown_{kind}.png'
  if verify:assert out.tobytes()==Image.open(target).convert('RGBA').tobytes(),kind
  else:out.save(target,optimize=True);print('exported',kind,flush=True)
 if verify:print('Nine PixelFlow sprites and 306 frames verified')
 else:path.write_text(json.dumps(metadata(sprites),indent=2)+'\n')


if __name__=='__main__':
 cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
 if cmd=='preview':preview()
 elif cmd=='build':build()
 elif cmd=='export':export()
 elif cmd=='verify':export(True)
 else:raise SystemExit('preview | build | export | verify')
