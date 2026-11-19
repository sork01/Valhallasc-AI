#!/usr/bin/env python3
"""Fisher overlay after shaped geography and fishing waters. Never move existing content."""
import argparse
import json
import math
from pathlib import Path
from fishing_spots import HABITATS, walkable, segment_distance, SURFACES, radius
from spirit_guides import clear

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = {0:'meadow',1:'crags',2:'rime',3:'fen',6:'wyrd',19:'storm',20:'sun',22:'tangle',25:'lapis',26:'fws',28:'yr',45:'ew'}
ELITES = set(json.loads((ROOT/'world/enrage.txt').read_text()))
DIALOGUE = 'Bring me fish and I can cook a meal or make a stronger rod. Each upgrade replaces your old rod. Platinum line fishes water and Crags lava; tempered platinum also reaches Emberwake. Cooked fish grant one food bonus for ten minutes.'


def safe(area, reach, x, y):
    if not (0 <= int(y*2) < reach.shape[0] and 0 <= int(x*2) < reach.shape[1] and reach[int(y*2), int(x*2)]):
        return False
    if not clear(area, x, y, .7):
        return False
    if any(math.hypot(x-n['x'], y-n['y']) < 2 for n in area.get('npcs', [])):
        return False
    if any(math.hypot(x-p['x'], y-p['y']) < p.get('r', 1.5)+3 for p in area.get('portals', [])):
        return False
    # Use full seam polylines: people are not rendered across seams.
    for p in area.get('portals', []):
        if p.get('seam') and any(segment_distance(x,y,a,b)<21 for a,b in zip(p['seam']['points'],p['seam']['points'][1:])):
            return False
    return not any(not s.get('ambush') and math.hypot(x-s['x'],y-s['y']) < (24 if s['kind'] in ELITES else 12) for s in area.get('slimes', []))


def location(area, reach, zone, anchor):
    if zone == 0 and anchor == 'Saltby':
        # The tutorial pier is already a sanctuary and joins Saltby's reachable land.
        candidates = [(200.5, y) for y in (284, 286, 288, 290, 292)]
        return next((p for p in candidates if safe(area, reach, *p)), None)
    hub = area['city']; center = ((hub['x0']+hub['x1'])/2, (hub['y0']+hub['y1'])/2)
    if zone == 0:
        candidates = [(x+.25,y+.25) for x in range(hub['x0']+1,hub['x1']) for y in range(hub['y0']+1,hub['y1'])]
    else:
        candidates = [(o['x']+(radius(o)+gap)*math.cos(k*math.tau/32),
                       o['y']+(radius(o)+gap)*math.sin(k*math.tau/32))
                      for o in area['objects'] if o['kind'] in SURFACES
                      and (o['kind'] in ('lava','ew_lava')) == (zone in (1,45))
                      for gap in (1.4,3,5) for k in range(32)]
    candidates.sort(key=lambda p:math.hypot(p[0]-center[0],p[1]-center[1]))
    return next((p for p in candidates if safe(area,reach,*p)), None)


def install(world, recipes, fish, levels):
    for area in [world,*world['zones']]:
        area['npcs'] = [n for n in area.get('npcs',[]) if not n['id'].startswith('fisher_')]
        area['quests'] = [q for q in area.get('quests',[]) if not q['id'].startswith('fisher_')]
    for zone, habitat in HABITATS.items():
        area = [world,*world['zones']][zone]
        reach = walkable(area)
        anchors = ['Alderhaven','Saltby'] if zone == 0 else [area['city']['name']]
        for slot, anchor in enumerate(anchors):
            pos = location(area, reach, zone, anchor)
            if pos is None:
                raise ValueError(f'No safe reachable Fisher shore for {anchor} ({zone})')
            key = f'fisher_{PREFIXES[zone]}_{slot}'
            offers = [dict(id='fishing_workshop',label='Fisher workshop',cost=0)]
            if zone == 0:
                offers.append(dict(id='buy_twig_rod',label='Buy a Twig Rod',cost=50,item='rod_twig_rod'))
            for recipe in recipes:
                if zone in recipe['zones']:
                    offers.append(dict(id=recipe['id'],label='Craft rod' if recipe['id'].startswith('rod:') else 'Cook fish',cost=recipe['cost']))
            area['npcs'].append(dict(id=key,name='Fisher',role='Fishing and cooking',x=pos[0],y=pos[1],
                dialogue=DIALOGUE,offers=offers,buys=True,color='#527e89',
                look=dict(skin='#dca480',hair='#694737',style='short',hat='straw')))
            pool = [f for f in fish if f['habitat']==habitat and (not f.get('zone') or f['zone']==zone)]
            previous = None
            for stage, rarity, count in [(1,'common',5),(2,'uncommon',3),(3,'rare',1),(4,'common',5)]:
                f = next(f for f in pool if f['rarity']==rarity)
                # Region entry tiers constrain where a species can actually be caught.
                rod_level = {0:1,1:5,2:10,3:15,6:25,19:40,20:40,22:70,25:80,26:90,28:95,45:95}[zone]
                level = max(f['level'],rod_level, 25 if rarity=='rare' and habitat!='Lava' else 1,
                            45 if rarity=='rare' and habitat=='Lava' else 1)
                qid = f'{key}_{stage}'
                title = ('Fresh Fish for ' if stage==1 else 'A Finer Catch for ' if stage==2 else 'A Trophy for ' if stage==3 else 'The Daily Creel at ') + anchor
                description = 'Catch fish in the local waters and bring them to the Fisher. Ordinary fish from your bags count.'
                area['quests'].append(dict(id=qid,title=title,npc=key,requires=previous if stage<4 else f'{key}_1',
                    repeatable=stage==4,level=level,rewardXp=levels[level-1]//10,rewardGold=max(5,level*3),
                    description=description,objectives=[dict(kind='bring',target=f['item'],count=count,what=f['name'])]))
                previous = qid


def assign_art(manifest, world):
    manifest['npcs'] = {key: value for key, value in manifest['npcs'].items() if not key.startswith('fisher_')}
    for area in [world, *world['zones']]:
        for n in area['npcs']:
            if n['id'].startswith('fisher_'):
                manifest['npcs'][n['id']] = dict(art='fisher_rod',identity=dict(n['look']),color=n['color'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=ROOT/'world/map.txt';world=json.loads(path.read_text())
    levels=json.loads((ROOT/'world/levels.txt').read_text());levels.append(levels[-1]+2300)
    install(world,json.loads((ROOT/'world/fishing-workshop.txt').read_text()),json.loads((ROOT/'world/fish.txt').read_text()),levels)
    text=json.dumps(world,ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if path.read_text()!=text:raise SystemExit('Fisher overlay is stale')
    else:path.write_text(text)
    art_path=ROOT/'client/assets/npc.txt'
    art=json.loads(art_path.read_text());assign_art(art,world)
    art_text=json.dumps(art,ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if art_path.read_text()!=art_text:raise SystemExit('Fisher art assignment is stale')
    else:art_path.write_text(art_text)
    print('Fisher overlay:',sum(n['id'].startswith('fisher_') for a in [world,*world['zones']] for n in a['npcs']),'Fishers')

if __name__=='__main__': main()
