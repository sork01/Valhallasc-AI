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
(24, 'halloween_heart', 'Glow-Fruit for Every Hollow', 'hw_baker', 80, 4200,
     'Olle wants every burl in Heartwood to glow for Halloween. Ask Pim for sap-lamps, Ingrid for amber lanterns, and Edda for a friendly ghost story, then bring Olle their good wishes.',
     [('talk','hw_lamplighter','Ask Pim for sap-lamps'),('talk','hw_glassblower','Ask Ingrid for amber lanterns'),('talk','hw_storyteller','Ask Edda for a friendly ghost story')]),
]


def apply(world):
    levels = json.loads((ROOT/'world/levels.txt').read_text())
    ids = {row[1] for row in SPECS}|{'halloween_hunt'}
    areas = [world, *world['zones']]
    for area in areas:
        area['quests'] = [q for q in area.get('quests', []) if q['id'] not in ids]
        area.pop('seasonDecor', None)
        zone=next(i for i,z in enumerate(areas) if z is area)
        if zone not in [0,4,9,17,24]:continue
        hub=area['city'];cx,cy=hub['plaza']['x'],hub['plaza']['y'];decor=[]
        accent={0:'#d48b45',4:'#b87442',9:'#52b9b4',17:'#a98bd9',24:'#8fc860'}[zone]
        def inside(x,y):return hub['x0']+.8<x<hub['x1']-.8 and hub['y0']+.8<y<hub['y1']-.8
        def safe(x,y):
            if not inside(x,y):return False
            if any((abs(x-o['x'])<o['width']/2+.7 and abs(y-o['y'])<o['depth']/2+.7) if o.get('width') else math.hypot(x-o['x'],y-o['y'])<o.get('r',0)+.7 for o in area['objects']):return False
            if any(math.hypot(x-n['x'],y-n['y'])<1.6 for n in area.get('npcs',[])):return False
            if any(math.hypot(x-p['x'],y-p['y'])<6 for p in area['portals']):return False
            return not any(math.hypot(x-d['x'],y-d['y'])<2.5 for d in decor)
        def add(kind,x,y,z=0):
            decor.append(dict(kind=kind,x=round(x,2),y=round(y,2),z=z,r=0,v=len(decor)%3,hub=hub['name'],color=accent))
        # Decorate building fronts first: wreaths/lanterns sit on facades, doorway clusters outside footprints.
        houses=[o for o in area['objects'] if o.get('width') and o.get('depth') and o['kind'] not in ['rampart','wall','vaultwall','void','bridge']]
        for o in houses:
            x,y=o['x'],o['y']+o['depth']/2+.2
            if inside(x,y) and all(math.hypot(x-p['x'],y-p['y'])>6 for p in area['portals']):
                add('festivalWreath' if len(decor)%2 else 'festivalWeb',x,y,76 if o['kind']!='stall' else 52)
            for side in [-1,1]:
                x,y=o['x']+side*(o['width']/2+.95),o['y']+o['depth']/2+.8
                if safe(x,y):add('festivalPumpkins' if side<0 else 'festivalCandles',x,y)
        # Plaza, markets and every district receive distributed dressing, rather than one small cluster.
        step=3.3 if zone==0 else 6.5
        for row in range(math.ceil((hub['y1']-hub['y0'])/step)):
            for col in range(math.ceil((hub['x1']-hub['x0'])/step)):
                x=hub['x0']+1.5+col*step+(row%2)*1.2;y=hub['y0']+1.5+row*step
                if safe(x,y):
                    kind=['festivalPumpkins','festivalLantern','festivalBunting','festivalCandles','festivalScarecrow'][(row*3+col)%5]
                    add(kind,x,y)
        area['seasonDecor']=decor
    for zone, id_, title, npc, level, gold, description, objectives in SPECS:
        area = areas[zone]
        assert any(n['id']==npc for n in area['npcs'])
        area['quests'].append(dict(id=id_,title=title,npc=npc,description=description,
            objectives=[dict(kind=k,target=t,label=l,count=1) for k,t,l in objectives],
            level=level,minLevel=level,rewardXp=levels[level-1]//10,rewardGold=gold,
            requires=None,repeatable=True,season='halloween'))
    givers=['baker','city_bard','nacre_gardener','asterion_singer','hw_baker']
    for area in areas:
        for npc in area.get('npcs',[]):
            if npc['id'] in givers:
                npc['offers']=[o for o in npc.get('offers',[]) if not o['id'].startswith('halloween:hire:')]
                for cls in ['warrior','mage','assassin','priest','hunter']:
                    npc['offers'].append(dict(id='halloween:hire:'+cls,label='Hire a '+cls.title(),merc=cls,cost=0,season='halloween',quest='halloween_hunt'))
    areas[0]['quests'].append(dict(id='halloween_hunt',title='The Hollow Rider',npc='baker',givers=givers,
        description='Gather five fighters and light the haunted lantern in Gloamfen. Defeat the Hollow Rider, then return to any city festival host. The Rider matches the average party level, rounded up. Each eligible hero has one independent 1% Nightmare Steed roll per day. Hired fighters can help.',
        objectives=[dict(kind='kill',target='hollow_rider',count=1,label='Defeat the summoned Hollow Rider')],
        level=1,minLevel=1,rewardXp=levels[0]//10,rewardGold=250,requires=None,repeatable=True,group=True,
        recommendedPlayers=5,season='halloween',seasonCadence='daily',summonNpc='halloween_lantern',summonZone=3))
    fen=areas[3];centre=(105.,23.);lantern=(105.,32.)
    # A dedicated circle on dry, reachable ground; preserve water, brambles and all ordinary spawns.
    fen['slimes']=[s for s in fen['slimes'] if s['kind']!='hollow_rider']
    fen['npcs']=[n for n in fen['npcs'] if n['id']!='halloween_lantern']
    fen['objects']=[o for o in fen['objects'] if o['kind'] not in ['willow','reeds','rock','column','bush','tree'] or math.hypot(o['x']-centre[0],o['y']-centre[1])>o.get('r',0)+10.5]
    from compact_atlas import clear,connected
    assert clear(fen,centre,centre,9.5),'Ritual circle must be clear'
    assert int(lantern[1])*fen['size']+int(lantern[0]) in connected(fen),'Ritual lantern must be reachable'
    assert all(math.hypot(s['x']-centre[0],s['y']-centre[1])>=16 for s in fen['slimes'])
    fen['slimes'].append(dict(kind='hollow_rider',x=centre[0],y=centre[1],ambush='halloween:hollow-rider'))
    fen['npcs'].append(dict(id='halloween_lantern',name='Haunted Ritual Lantern',role='Halloween summon',art='scenery',
        x=lantern[0],y=lantern[1],r=.4,color='#ed9c45',season='halloween',
        dialogue='Five fighters may light this lantern during Halloween. The Hollow Rider scales to your average party level. Each eligible hero has one independent 1% mount roll per day.',
        offers=[dict(id='halloween:summon',label='Summon the Hollow Rider',cost=0)],buys=False))
    fen['halloweenRitual']=dict(x=centre[0],y=centre[1],radius=9,lantern=list(lantern))
    return world


if __name__=='__main__':
    path=ROOT/'world/map.txt';world=json.loads(path.read_text())
    for area in [world,*world['zones']]:area['npcs']=[n for n in area['npcs'] if not n['id'].startswith('festival_dance_')]
    world=apply(world)
    world['zones'][1]['slimes']=[s for s in world['zones'][1]['slimes'] if s['kind'] not in {'bloomwarden','birchcrown','starrocketeer','briarheart'}]
    import christmas_cities, easter_event, solstice_event, valentines_event, newyear_event
    world=christmas_cities.apply(world,json.loads((ROOT/'world/levels.txt').read_text()))
    world=easter_event.apply(world,json.loads((ROOT/'world/levels.txt').read_text()))
    world=solstice_event.apply(world,json.loads((ROOT/'world/levels.txt').read_text()))
    world=valentines_event.apply(world,json.loads((ROOT/'world/levels.txt').read_text()))
    world=newyear_event.apply(world,json.loads((ROOT/'world/levels.txt').read_text()))
    events=[dict(id='halloween',start=[10,26],endExclusive=[11,10],quests=[r[1] for r in SPECS]+['halloween_hunt'],dailyQuests=['halloween_hunt'],givers={'halloween_hunt':['baker','city_bard','nacre_gardener','asterion_singer','hw_baker']}),christmas_cities.event(),easter_event.event(),solstice_event.event(),valentines_event.event(),newyear_event.event()]
    import season_dance
    world=season_dance.apply(world,events)
    path.write_text(json.dumps(world,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'world/seasons.txt').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
    print('Halloween: city dressing and four annual quests; October 26–November 9, Europe/Stockholm.')
