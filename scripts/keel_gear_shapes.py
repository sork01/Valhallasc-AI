"""Original Keelbound geometry: copper hull plates, navy sails, rope and coral.

Uses only the shared joint rig and drawing primitives; no starter/progression
armor or weapon builder is called. Every slot follows every pose and facing.
"""
import math
import numpy as np
import cel_common as cc
import gear_shapes as rig
from cel_common import V,unit
MATS={
 'keel_copper':['#193b3a','#2b716c','#53aa99','#a1d9bb'],
 'keel_sail':['#172437','#2c3f57','#455e78','#8899ad'],
 'keel_rope':['#5c4d3d','#9b8461','#d2bd8e','#f4e1b3'],
 'keel_coral':['#632e3b','#ad4b4f','#e77e69','#ffc1a1'],
 'keel_bronze':['#473b35','#866747','#bd925b','#e6c991'],
 'keel_steel':['#242d36','#404955','#647383','#a1acb4'],
}
PALETTE,COLOR=cc.palette_of({**rig.MATS,**MATS})
C,S,R,B,K,T='keel_copper','keel_sail','keel_rope','keel_bronze','keel_coral','keel_steel'

def disk(ink,c,a,u,rad,mat,tone=2):
 ink.plate([c+a*math.cos(t)*rad+u*math.sin(t)*rad for t in np.linspace(0,2*math.pi,13)[:-1]],mat,tone)

def rim(ink,c,a,u,rad,thick=1.5,mat=C):
 for j in range(12):
  t,jj=j*math.pi/6,(j+1)*math.pi/6
  ink.plate([c+(a*math.cos(t)+u*math.sin(t))*rad,c+(a*math.cos(jj)+u*math.sin(jj))*rad,c+(a*math.cos(jj)+u*math.sin(jj))*(rad-thick),c+(a*math.cos(t)+u*math.sin(t))*(rad-thick)],mat,2)

def anchor(ink,c,a,u,size=5):
 ink.bone(c-u*size,c+u*size,.9,.9,B,-2,2)
 ink.bone(c-a*size*.7+u*size*.35,c+a*size*.7+u*size*.35,.8,.8,R,-2,3)
 for s in (-1,1):ink.plate([c-u*size,c+a*s*size-u*size*.45,c+a*s*size+u*.5,c+a*s*size*.45-u*size*.2],C,3)
 disk(ink,c+u*size,a,u,1.5,K,2)

def render(cls,theme,kind,gender,clip,facing,k):
 _,ink,p,Q,xf,j,h=rig.pose(cls,gender,clip,facing,k);ink.color=COLOR
 u,a=Q@V(0,0,1),Q@V(1,0,0)
 plate=lambda pts,mat=C,tone=2:ink.plate([xf(q) for q in pts],mat,tone)
 if kind=='armor':
  caster=cls in ('mage','priest');w=9.2 if cls=='warrior' else 7.5
  cc.torso(ink,xf,S,w,5.7,37,70)
  # Hull strakes overlap diagonally on each side of a canvas chest.
  for s in (-1,1):
   for n in range(3):
    z=65-n*8
    plate([(s*.8,6.2,z+4),(s*(w+.5),5.8,z+1),(s*(w-1),6,z-6),(s*2,6.4,z-4)],C,2 if n%2 else 3)
   hem=18 if caster else 32
   plate([(s*2,-5,44),(s*10,-6,48),(s*(17+p['sway']*.3),-10,hem+5),(s*5,-8,hem)],S,1)
   # A torn sail collar folds sideways, rather than sprouting a generic crest.
   if caster:plate([(s*4,-3,70),(s*13,-6,78),(s*19,-10,70),(s*10,-7,58)],R if cls=='priest' else S,2)
   elif cls=='hunter':plate([(s*4,-5,72),(s*16,-8,70),(s*21,-13,46),(s*8,-9,37)],S,2)
  ink.ribbon([xf((-7,7,69)),xf((0,8,58)),xf((7,7,43))],1.5,1.3,R,3,-2)
  disk(ink,xf((0,8.5,56)),a,u,3.5,K,2)
  for key in 'LR':
   ink.bone(j[key]['shoulder'],j[key]['elbow'],3.7,2.7,S,-.8)
   if caster:ink.bone(j[key]['elbow'],j[key]['hand']+(j[key]['elbow']-j[key]['hand'])*.45,4.4,3.9,R if cls=='priest' else S,-.7)
 elif kind=='headgear':
  H,hd=h['H'],h['hd']-8
  def f(pts,mat=C,tone=2,z=0):ink.poly([H(*q) for q in pts],COLOR[mat][tone],hd+z)
  if cls=='warrior':
   # Rounded diving cowling and open porthole visor; no plumed starter helm.
   f([(-15,-6),(-17,9),(-13,20),(-6,25),(6,25),(13,20),(17,9),(15,-6),(10,-4),(11,9),(6,15),(-6,15),(-11,9),(-10,-4)])
   f([(-17,5),(-11,7),(-10,2),(-16,0)],B,2,-.2);f([(17,5),(11,7),(10,2),(16,0)],B,2,-.2)
   f([(-5,22),(0,29),(5,22),(0,20)],K,2,-.4)
  elif cls=='mage':
   # A broad nautical cap, with a half wheel above its flat brim.
   f([(-21,8),(-15,12),(-12,20),(10,23),(15,13),(22,9),(10,6),(-12,5)],S)
   f([(-21,8),(-12,5),(10,6),(22,9),(12,11),(-13,10)],R,2,-.2)
   for s in (-1,1):f([(s*4,20),(s*9,31),(s*12,29),(s*7,18)],C,2,-.3)
   f([(-3,19),(-2,31),(2,31),(3,19)],C,2,-.3)
  elif cls=='priest':
   f([(-16,2),(-17,14),(-11,24),(0,28),(11,24),(17,14),(16,2),(11,2),(10,12),(-10,12),(-11,2)],R)
   for x in (-9,0,9):f([(x-1,15),(x-1,24),(x+1,24),(x+1,15)],C,2,-.2)
   f([(-5,11),(0,17),(5,11),(0,6)],K,2,-.4)
  elif cls=='assassin':
   f([(-17,1),(-15,13),(-7,18),(0,12),(7,18),(15,13),(17,1),(8,4),(-8,4)],S)
   for s in (-1,1):f([(s*10,7),(s*17,18),(s*24,15),(s*20,8),(s*13,4)],C,2,-.2)
   f([(-4,12),(0,21),(4,12),(0,9)],K,2,-.3)
  else:
   f([(-16,5),(-12,15),(-4,19),(5,17),(14,12),(19,4),(9,5),(-7,3)],S)
   f([(0,17),(7,28),(15,30),(12,24),(17,18),(8,17)],C,2,-.3)
   f([(-13,13),(-20,23),(-23,20),(-18,8)],K,2,-.3)
 elif kind=='shoulders':
  for s,key in ((-1,'L'),(1,'R')):
   c=j[key]['shoulder'];out=a*s;reach={'warrior':18,'mage':13,'assassin':12,'priest':15,'hunter':16}[cls]
   # Quarter-circle ship ribs make hooked crescents on every shoulder.
   pts=[c+out*(3+math.cos(t)*reach)+u*(math.sin(t)*8) for t in np.linspace(-.6,1.7,7)]
   inner=[c+out*(3+math.cos(t)*(reach-4))+u*(math.sin(t)*5-2) for t in np.linspace(1.7,-.6,7)]
   ink.plate(pts+inner,C,2)
   ink.ribbon([c+out*3+u*5,c+out*(reach*.65)+u*8,c+out*(reach+1)+u*2],1,1,R,3,-2)
   disk(ink,c+out*(reach-1)-u*3+Q@V(0,3,0),out,u,2.8,K,2)
 elif kind=='gloves':
  for key in 'LR':
   c=j[key]['hand'];v=unit(j[key]['elbow']-c)
   ink.bone(c+v*.5,c+v*12,3.3,4.7,C,-1)
   ink.bone(c+v*10,c+v*14,4.9,4.9,R,-1.5,3)
   ink.plate([c-a*4,c+v*10-a*5,c+v*13+a*5,c+v*2+a*4],C,2)
   for n in range(2):ink.bone(c+v*(3+n*5)-a*3,c+v*(5+n*5)+a*3,.8,.8,R,-2,3)
   disk(ink,c+v*7+Q@V(0,4,0),a,v,2.2,K,2)
 elif kind=='pants':
  for key in 'LR':
   knee,ankle=j[key]['knee'],j[key]['ankle'];v=unit(ankle-knee)
   ink.bone(j[key]['hip'],knee,4.7,4,S,-.8);ink.bone(knee,ankle,4.1,3.6,T,-.8)
   disk(ink,knee+Q@V(0,4,0),a,u,5,C,2)
   for n in range(3):ink.bone(knee+v*(4+n*4),knee+v*(5+n*4),4.3,4.3,R,-1.5,2)
   ink.bone(ankle+V(0,-2,-1),ankle+V(0,6,-2),4,3.1,C,-1.4)
 elif kind=='necklace':
  ink.ribbon([xf(q) for q in [(-6,3,71),(-5,7,64),(0,8,52),(5,7,64),(6,3,71)]],1,1,R,3,-2)
  anchor(ink,xf((0,8.5,52)),a,u,5)
 elif kind=='accessory':
  c=j['L']['hand']+Q@V(0,3.5,1)
  ink.bone(c-u,c+u*2,3.5,3.5,R,-2,2)
  disk(ink,c+a*1.5+Q@V(0,1,0),a,u,3.6,K,2)
  rim(ink,c+a*1.5+Q@V(0,1.3,0),a,u,4.5,1.3,C)
 elif kind=='weapon':weapon(ink,cls,p,Q,xf,j)
 else:raise ValueError(kind)
 return ink.resolve(clip in ('hurt','die') and k==0)

def weapon(ink,cls,p,Q,xf,j):
 if cls=='hunter':
  c=j['L']['hand'];axis=Q@unit(V(*p['bow']));face=unit(c-j['R']['hand']) if p['draw'] else Q@unit(V(*p['aim']))
  if p['dropped']:c,axis,face=V(-21,8,3),unit(V(.3,1,0)),V(0,0,1)
  axis=unit(axis-face*(axis@face))
  # Harpoon stock with twin fluked limbs, crossbow outline on the bow rig.
  ink.bone(c-face*13,c+face*15,2.5,1.6,T,-.5)
  for s in (-1,1):
   pts=[c+axis*s*3+face*2,c+axis*s*13+face*7,c+axis*s*22+face*2]
   ink.ribbon(pts,2.6,1.8,C,2,-.6)
   end=pts[-1];ink.plate([end-face*2,end+axis*s*4,end+face*5],K,2)
   nock=j['R']['hand'] if p['draw'] and not p['dropped'] else c-face*7
   ink.ribbon([end,nock],.6,.6,R,3,-1,False)
  if p['arrow'] and not p['dropped']:
   tip=c+face*28;ink.bone(c-face*9,tip,.7,.7,B,-1)
   for s in (-1,1):ink.plate([tip+face*5,tip-face*3+axis*s*4,tip+axis*s*2],C,3)
  return
 keys='LR' if cls=='assassin' else 'R' if cls in ('warrior','priest') else 'L'
 for n,key in enumerate(keys):
  hand=j[key]['hand'];direction=p['blade'+key] if cls=='assassin' else p[{'warrior':'blade','priest':'mace','mage':'staff'}[cls]]
  v,a=Q@unit(V(*direction)),Q@V(1,0,0)
  if p['dropped']:hand,v=V((n*2-1)*21,-8,3),unit(V(.4,1,0));a=unit(V(v[1],-v[0],0))
  at=lambda x,y:hand+a*x+v*y
  ink.bone(at(0,-18 if cls=='mage' else -4),at(0,8),1.7,1.7,R,-.4)
  if cls=='mage':
   ink.bone(at(0,5),at(0,25),1.7,1.7,C,-.4);c=at(0,26)
   rim(ink,c,a,v,8,2,C)
   for n in range(8):
    t=n*math.pi/4;d=a*math.cos(t)+v*math.sin(t);ink.bone(c,c+d*10,1,1,B,-1)
   disk(ink,c+Q@V(0,2,0),a,v,3.2,K,2)
  elif cls=='priest':
   ink.bone(at(0,5),at(0,21),2,2,C,-.5)
   ink.plate([at(-8,19),at(-6,28),at(0,32),at(6,28),at(8,19),at(6,17),at(-6,17)],C,2)
   ink.bone(at(-9,18),at(9,18),1.8,1.8,B,-1)
   disk(ink,at(0,23)+Q@V(0,3,0),a,v,3,K,2)
  elif cls=='assassin':
   # A deep open hook; transparent inner curve changes the outline, not just paint.
   pts=[(-2,6),(-3,17),(0,25),(7,27),(11,22),(10,17),(6,19),(5,23),(2,21),(1,16),(2,6)]
   ink.plate([at(x,y) for x,y in pts],C,2);ink.bone(at(-4,5),at(4,5),1.2,1.2,B,-1)
  else:
   pts=[(-2,6),(-4,16),(-1,27),(5,35),(10,38),(6,30),(4,20),(4,7)]
   ink.plate([at(x,y) for x,y in pts],T,3);ink.ribbon([at(1,9),at(2,23),at(7,34)],.8,.7,C,3,-1)
   ink.plate([at(-6,5),at(-8,9),at(-4,14),at(2,11),at(4,5)],B,2)
 if cls=='warrior':
  c=(j['L']['hand']+j['L']['elbow'])/2+Q@V(0,4,0);a,v=Q@V(1,0,0),Q@V(0,0,1)
  if p['dropped']:c,a,v=V(-21,8,2),V(1,0,0),V(0,1,0)
  disk(ink,c,a,v,13,S,1);rim(ink,c+Q@V(0,1,0),a,v,13,3,C)
  anchor(ink,c+Q@V(0,3,0),a,v,6)
