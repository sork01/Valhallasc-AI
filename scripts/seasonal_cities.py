#!/usr/bin/env python3
"""Idempotent Halloween city dressing and four authored annual city quests."""
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SPECS = [
    (0, 'halloween_alder', 'A Light for Every Door', 'baker', 1, 75,
     'Pip wants every doorstep to glow for Halloween. Ask Linden for ribbons, Mira for lantern oil, and Tessa for warm cider, then bring Pip their good wishes.',
     [('talk','merchant','Ask Linden for ribbons'),('talk','apothecary','Ask Mira about lantern oil'),('talk','innkeeper','Arrange warm cider with Tessa')]),
    (4, 'halloween_skald', 'The Kindly Ghost Parade', 'city_bard', 20, 450,
     'Eira is planning a friendly ghost parade. Find a story with Fenwick, ask Brunhild for a little bell, and invite Captain Ingrid to lead the procession.',
     [('talk','city_librarian','Find a friendly ghost story'),('talk','city_smith','Ask Brunhild for a parade bell'),('talk','city_captain','Invite Captain Ingrid to the parade')]),
    (9, 'halloween_nacre', 'Lanterns for the Lost', 'nacre_gardener', 40, 1400,
     'Pelar tends a gentle Halloween remembrance. Visit the Memorial of the Lost Choir, ask Syllene for a song, and help Ilo plan the lantern lighting.',
     [('visit','nacre_memorial','Visit the Memorial of the Lost Choir'),('talk','nacre_singer','Ask Syllene for a remembrance song'),('talk','nacre_lamplighter','Plan the lantern lighting with Ilo')]),
    (17, 'halloween_aster', 'The Midnight Masquerade', 'asterion_singer', 60, 2600,
     'Vela is arranging a Halloween masquerade beneath the stars. Ask Mora to ring the opening bell, Umi to dress the balconies, and Nim to welcome the masked guests.',
     [('talk','asterion_bellkeeper','Arrange the opening bell with Mora'),('talk','asterion_gardener','Plan the balcony garlands with Umi'),('talk','asterion_merchant','Ask Nim to welcome the guests')]),
]


def apply(world):
    levels = json.loads((ROOT/'world/levels.txt').read_text())
    ids = {row[1] for row in SPECS}
    areas = [world, *world['zones']]
    for area in areas:
        area['quests'] = [q for q in area.get('quests', []) if q['id'] not in ids]
        area.pop('seasonDecor', None)
        hubs = [h for h in [area.get('city'), *area.get('camps', [])] if h]
        decor = []
        for hub in hubs:
            cx, cy = hub['plaza']['x'], hub['plaza']['y']
            candidates = []
            for angle in range(0, 360, 20):
                for radius in [5, 8, 11, 15, 20]:
                    x = round(cx+math.cos(math.radians(angle))*radius, 2)
                    y = round(cy+math.sin(math.radians(angle))*radius, 2)
                    if not (hub['x0']+1<x<hub['x1']-1 and hub['y0']+1<y<hub['y1']-1): continue
                    if any((abs(x-o['x'])<o['width']/2+1.2 and abs(y-o['y'])<o['depth']/2+1.2) if o.get('width') else math.hypot(x-o['x'],y-o['y'])<o.get('r',0)+1.2 for o in area['objects']): continue
                    if any(math.hypot(x-n['x'],y-n['y'])<2.2 for n in area.get('npcs', [])): continue
                    if any(math.hypot(x-p['x'],y-p['y'])<6 for p in area['portals']): continue
                    candidates.append((angle, radius, x, y))
            for angle, radius, x, y in candidates:
                if sum(d.get('hub')==hub['name'] for d in decor)>=14: break
                if any(math.hypot(x-d['x'],y-d['y'])<2.7 for d in decor): continue
                decor.append(dict(kind=['festivalPumpkins','festivalLantern','festivalBunting'][len(decor)%3],x=x,y=y,r=0,v=len(decor)%3,hub=hub['name']))
        if decor: area['seasonDecor'] = decor
    for zone, id_, title, npc, level, gold, description, objectives in SPECS:
        area = areas[zone]
        assert any(n['id']==npc for n in area['npcs'])
        area['quests'].append(dict(id=id_,title=title,npc=npc,description=description,
            objectives=[dict(kind=k,target=t,label=l,count=1) for k,t,l in objectives],
            level=level,minLevel=level,rewardXp=levels[level-1]//10,rewardGold=gold,
            requires=None,repeatable=True,season='halloween'))
    return world


if __name__=='__main__':
    path=ROOT/'world/map.txt';world=apply(json.loads(path.read_text()))
    path.write_text(json.dumps(world,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'world/seasons.txt').write_text(json.dumps([dict(id='halloween',start=[10,26],endExclusive=[11,10],quests=[r[1] for r in SPECS])],ensure_ascii=False,indent=2)+'\n')
    print('Halloween: city dressing and four annual quests; October 26–November 9, Europe/Stockholm.')
