#!/usr/bin/env python3
"""A pointed, split-deck wreck in Ran's Deep. Seed-free and byte-stable.

The hull contour and broken cargo hatches define actual collision and art,
not a cosmetic ship painted over the six-room dungeon layout.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
import generate_gloamfen as fen
import generate_undervault as vault
from mercenary_offers import offers
from skaldholm_content import look
from longship_content import ENEMIES
ROOT=Path(__file__).resolve().parents[1]
NAME,THEME,ZONE,PARENT,SIZE='The Drowned Longship','longship',43,8,128
GATE,LANDING,ARRIVAL=(54,146),(54,151),(64,110)

def obj(kind,x,y,**kw):return {**dict(kind=kind,x=x,y=y,r=0,v=0),**kw}

def half_width(y):
 if y<8 or y>=119:return 0
 t=(y-8)/111
 return 5+27*math.sin(math.pi*t)**.65

def hull_floor():
 floor=np.zeros((SIZE,SIZE),bool)
 for y in range(8,119):
  for x in range(SIZE):floor[y,x]=abs(x+.5-64)<half_width(y+.5)
 # Split hatches expose water. The main centre gangplank remains intact.
 floor[65:74,52:61]=False;floor[65:74,67:76]=False
 # Two physical bulkheads, both with wide central doors. They divide holds,
 # not identical side rooms, and preserve clear party movement.
 floor[88:90,30:60]=False;floor[88:90,68:98]=False
 floor[46:48,30:59]=False;floor[46:48,69:98]=False
 return floor

def build():
 floor=hull_floor();vault.SIZE=SIZE;walls,_=vault.wall_pieces(floor)
 objects=[obj('keel_hull',round(x,2),round(y,2),width=round(w,2),depth=round(d,2)) for x,y,w,d in walls]
 used=floor.copy()
 for y in range(SIZE):
  for x in range(SIZE):
   if used[y,x]:continue
   x1=x
   while x1<min(x+8,SIZE) and not used[y,x1]:x1+=1
   y1=y+1
   while y1<min(y+8,SIZE) and not used[y1:y1+1,x:x1].any():y1+=1
   used[y:y1,x:x1]=True;objects.append(obj('void',(x+x1)/2,(y+y1)/2,width=x1-x,depth=y1-y))
 # Nonblocking landmarks sit on genuine deck and do not invent collision.
 objects+=[obj('keel_prow',64,10),obj('keel_capstan',64,54),obj('keel_mast',86,78),obj('keel_bell',46,54)]
 for y in [28,39,57,80,101,111]:
  hw=half_width(y)-3
  for s in (-1,1):objects.append(obj('keel_rib',round(64+s*hw,2),y,v=1 if s>0 else 0))
 for x,y in [(43,77),(85,94),(46,57),(81,37)]:objects.append(obj('keel_cargo',x,y))
 for x,y in [(58,109),(70,100),(48,82),(80,57),(51,37),(77,22)]:objects.append(obj('keel_lamp',x,y))
 spawns=[]
 for cx,cy in [(64,98),(48,77),(81,61),(64,43)]:
  for kind,dx,dy in [('keel_crab',-3,1),('keel_deckhand',3,1),('keel_lantern',0,-2)]:spawns.append(dict(kind=kind,x=cx+dx,y=cy+dy))
 spawns += [dict(kind='keel_cargomaw',x=64,y=80),dict(kind='keel_bosun',x=64,y=57),dict(kind='keel_captain',x=64,y=26)]
 return dict(name=NAME,theme=THEME,tagline='Her last voyage never reached the surface.',size=SIZE,levels=[35,35],min_level=35,players=5,copies=4,interior=True,sealedTemplate=True,final_boss='keel_captain',spawn=dict(x=64,y=110),objects=objects,slimes=spawns,
  npcs=[dict(id='keel_witness',name='Edda, the Last Lookout',role='Witness of the last voyage',x=71,y=111,color='#86bfa9',offers=[],dialogue='The hold has teeth, the bosun has his hook, and Captain Svala still steers the dead. Read the bow tablet before you face her anchor.',look=look('#e6c1a1','#759c94','braid','hood',hat_color='#43666b'))],quests=[],city=None,
  # An explicit bounded encounter rectangle is strictly inside the hull.
  longshipFloor=[''.join('=' if v else ' ' for v in row) for row in floor],
  rooms=[[70,41,76,45],[44,13,84,40],[41,50,87,64],[42,76,86,86],[46,97,82,116]],
  paths=[[[64,110],[64,98],[64,80],[64,70],[64,57],[64,43],[64,26]]],
  places=[dict(id='keel_stern',name='The Broken Stern',x=64,y=110,r=4),dict(id='keel_hold',name='The Copper Cargo Hold',x=64,y=80,r=4),dict(id='keel_gap',name='The Split Hatch',x=64,y=70,r=3),dict(id='keel_capstan',name='The Drowned Capstan',x=64,y=57,r=4),dict(id='keel_prow',name="The Captain's Prow",x=64,y=26,r=4)],
  portals=[dict(id='keel_return',name="Rán's Deep",x=56,y=110,r=1.2,to=PARENT,tx=54,ty=151,look=THEME),dict(id='keel_clear',name='The Last Mooring',x=64,y=13,r=1.2,to=PARENT,tx=54,ty=151,look=THEME,after_clear=True)])

def install_parent(world):
 if not any(z['name']==NAME for z in world['zones']):return
 z=world['zones'][PARENT-1];assert z['name']=="Rán's Deep"
 line=[[66,154],[60,154],[54,151],[54,146]]
 z['paths']=[p for p in z['paths'] if p!=line]+[line]
 # Keep authored ships, buildings, bells and the living maze. Clear only small
 # loose sea-floor scenery from the safe L35 approach west of Keelhaven.
 loose={'kelp','searock','coral','coral_fan','shell','anemone','bubbles','deep_rock','deep_kelp'}
 clear=[GATE,LANDING,(58,146),(58,150)]
 z['objects']=[o for o in z['objects'] if not(o['kind'] in loose and (fen.dist_to_trail(line,o['x'],o['y'])<2.8+o.get('r',0) or any(math.hypot(o['x']-x,o['y']-y)<2.5+o.get('r',0) for x,y in clear)))]
 z['portals']=[p for p in z['portals'] if p['id']!='deep_longship']+[dict(id='deep_longship',name=NAME,x=54,y=146,r=1.3,to=ZONE,tx=64,ty=110,look=THEME)]
 z['npcs']=[n for n in z['npcs'] if not n['id'].startswith('keel_')]+[
 dict(id='keel_guide',name='Ragna Copperwake',role='Keeper of the last mooring',x=58,y=146,color='#88bca6',offers=offers(open_=True),dialogue='Svala sailed into Ran\'s net to save her crew. The debt kept them all below. Follow the mooring west of Keelhaven, take a party and free Gullveig from the hold.',look=look('#d4a483','#71988f','braid','hood',hat_color='#496970')),
 dict(id='keel_rigger',name='Orri Ropemender',role='Rigger of Keelhaven',x=58,y=150,color='#cba777',offers=[],dialogue='Brinehook lashed the ship to the deep. Break his hold on the capstan. Then go to the prow and watch where the captain drops her anchor.',look=look('#e4bf9b','#bb895a','short',None,None,'#5e7d77'))]
 xp=json.loads((ROOT/'world/levels.txt').read_text())[34]//10
 quests=[dict(id='keel_entry',title='A Mooring Below the Sea',npc='keel_guide',description='Board the Drowned Longship and speak to Edda, the Last Lookout. Bring her words back to Ragna.',objectives=[dict(kind='talk',target='keel_witness',label='Speak to Edda, the Last Lookout',count=1)],rewardGold=500),
 dict(id='keel_cargo',title='The Hold Has Teeth',npc='keel_guide',description='Defeat Gullveig, the Cargo Maw, with your party and free the longship\'s stolen cargo.',objectives=[dict(kind='kill',target='keel_cargomaw',label='Defeat Gullveig, the Cargo Maw',count=1)],group=True,recommendedPlayers=5,rewardGold=1700,rewardItem='pants_wayfarer_l35_keel',rewardCount=1),
 dict(id='keel_rigging',title='Cut the Last Knot',npc='keel_rigger',description='Defeat Bosun Brinehook at the capstan. Take his mooring token and free the prow for the last crossing.',objectives=[dict(kind='kill',target='keel_bosun',label='Defeat Bosun Brinehook',count=1)],group=True,recommendedPlayers=5,rewardGold=1700,rewardItem='accessory_amber_l35_keel',rewardCount=1)]
 for q in quests:q.update(level=35,rewardXp=xp,repeatable=False,requires=None)
 z['quests']=[q for q in z['quests'] if not q['id'].startswith('keel_')]+quests

def check(world):
 for index,start in [(ZONE,ARRIVAL),(PARENT,(80,165))]:
  z=world['zones'][index-1];seen,_=fen.flood(z,start)
  for p in z['portals']+z['npcs']+z['slimes']:
   assert seen[int(p['y']/.5),int(p['x']/.5)],(index,p.get('id',p.get('kind')),p['x'],p['y'])
 for index in (PARENT,ZONE):
  for p in world['zones'][index-1]['portals']:
   if p['id'] not in ('deep_longship','keel_return','keel_clear'):continue
   z=world['zones'][p['to']-1]
   assert all(math.hypot(s['x']-p['tx'],s['y']-p['ty'])>8 for s in z['slimes']),p
   assert all(math.hypot(q['x']-p['tx'],q['y']-p['ty'])>q['r']+1 for q in z['portals']),p

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--open',action='store_true',help='Compatibility flag: finished dungeon is open by default');p.add_argument('--sealed',action='store_true',help='Keep the entrance sealed while changing content');a=p.parse_args();path=ROOT/'world/map.txt';w=json.loads(path.read_text())
 if not a.check:
  old=next((i for i,z in enumerate(w['zones'],1) if z['name']==NAME),None);assert old in (None,ZONE)
  z=build();z['sealedTemplate']=a.sealed
  if old is None:assert len(w['zones'])==ZONE-1;w['zones'].append(z)
  else:w['zones'][ZONE-1]=z
  install_parent(w)
 check(w)
 if not a.check:
  path.write_text(json.dumps(w,indent=2,ensure_ascii=False)+'\n');(ROOT/'world/longship.txt').write_text(json.dumps(ENEMIES,indent=2,ensure_ascii=False)+'\n')
  ip=ROOT/'world/items.txt';items=json.loads(ip.read_text());have={i['id'] for i in items}
  for e in ENEMIES:
   if e['material'] not in have:items.append(dict(id=e['material'],name=e['name']+' Relic',kind='material',rarity='common',sell=620 if e['boss'] else 140))
  ip.write_text(json.dumps(items,indent=2,ensure_ascii=False)+'\n')
 print('Drowned Longship: curved hull, split hatch, safe Keelhaven approach; all spawns/NPCs/portals reachable')
if __name__=='__main__':main()
