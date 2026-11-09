"""Annual New Year: exactly one daily hunt, using the retired Rimeveil Christmas clearing."""
import math
GIVERS=['baker','city_bard','nacre_gardener','asterion_singer','hw_baker']
def event():
    return dict(id='newyear',start=[12,29],endExclusive=[1,3],quests=['newyear_hunt'],dailyQuests=['newyear_hunt'],givers={'newyear_hunt':GIVERS})
def remove_encounter(world):
    # Called before Christmas validates its clearing; the seasons never overlap.
    rime=world['zones'][1]
    rime['slimes']=[s for s in rime['slimes'] if s['kind']!='starrocketeer']
    rime['npcs']=[n for n in rime['npcs'] if n['id']!='newyear_launchpad']
def apply(world,levels):
    from compact_atlas import clear,connected
    areas=[world,*world['zones']]
    for area in areas:
        area['quests']=[q for q in area.get('quests',[]) if q['id']!='newyear_hunt']
        for npc in area.get('npcs',[]):
            npc['offers']=[o for o in npc.get('offers',[]) if not o['id'].startswith('newyear:hire:')]
            if npc['id'] in GIVERS:
                for cls in ['warrior','mage','assassin','priest','hunter']:
                    npc['offers'].append(dict(id='newyear:hire:'+cls,label='Hire '+('an ' if cls=='assassin' else 'a ')+cls.title(),merc=cls,cost=0,season='newyear',quest='newyear_hunt'))
    world['quests'].append(dict(id='newyear_hunt',title='The Starfire Rocketeer',npc='baker',givers=GIVERS,
        description='Gather five fighters at the Festival Launchpad in Rimeveil Glacier. Press it to summon the Starfire Rocketeer at the highest level in your party. Hired fighters can help. Each eligible hero has one independent 5% Starflight Rocket roll per Stockholm day. Return to any city festival host to claim the quest and the Ring in the New Year achievement.',
        objectives=[dict(kind='kill',target='starrocketeer',count=1,label='Defeat the summoned Starfire Rocketeer')],level=1,minLevel=1,rewardXp=levels[0]//10,rewardGold=300,requires=None,repeatable=True,group=True,recommendedPlayers=5,season='newyear',seasonCadence='daily',summonNpc='newyear_launchpad',summonZone=2))
    remove_encounter(world)
    rime=areas[2];centre=(103.,100.);pad=(112.,100.)
    assert clear(rime,centre,centre,9.5),'New Year clearing must be clear'
    assert clear(rime,centre,pad,1.2),'Launchpad must connect to the arena'
    assert int(pad[1])*rime['size']+int(pad[0]) in connected(rime),'Launchpad must be reachable'
    assert all(math.hypot(s['x']-centre[0],s['y']-centre[1])>=16 for s in rime['slimes'] if s['kind'] not in {'grinch','bloomwarden','birchcrown','briarheart','starrocketeer'})
    assert all(math.hypot(p['x']-centre[0],p['y']-centre[1])>=18 for p in rime['portals'])
    rime['slimes'].append(dict(kind='starrocketeer',x=centre[0],y=centre[1],ambush='newyear:rocketeer'))
    rime['npcs'].append(dict(id='newyear_launchpad',name='Festival Launchpad',role='New Year summon',art='scenery',x=pad[0],y=pad[1],r=.4,color='#e7bc64',season='newyear',
        dialogue='Press the launchpad while on The Starfire Rocketeer daily quest. Gather five living fighters, including hires, nearby. The Rocketeer matches the highest party level. Each eligible hero has one independent 5% Starflight Rocket chance per Stockholm day. Claim the quest in any city to earn Ring in the New Year.',
        offers=[dict(id='newyear:summon',label='Summon the Starfire Rocketeer',cost=0)],buys=False))
    return world
