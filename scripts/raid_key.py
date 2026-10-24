#!/usr/bin/env python3
"""Install the Ember Key tour. Reapply after zone generators and before sync-world."""
import json
import math
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
QUEST = 'raid_key'
KIND = 'ember_firelord'
# Coordinates selected from the actual reachable map, away from enemies and arrivals.
SITES = [
    (0, 'Greenmeadow', 38, 47, '#d48b4b', 'Ashwarden of Greenmeadow'),
    (1, 'Emberfall Crags', 24, 73, '#ef6d3d', 'Cinderthane of Emberfall'),
    (2, 'Rimeveil Glacier', 64, 96, '#88d7ea', 'Frostflame of Rimeveil'),
    (3, 'Gloamfen', 19, 37, '#a6b96c', 'Bogflame of Gloamfen'),
    (6, 'Wyrdwood', 69, 158, '#bda473', 'Rootpyre of Wyrdwood'),
    (7, 'Bifrost Reach', 66, 106, '#b7b3f3', 'Skybrand of Bifrost'),
    (8, "Rán's Deep", 80, 131, '#6fcbd1', "Tidepyre of Rán's Deep"),
    (13, 'Astralhollow', 87, 87, '#b59aef', 'Starpyre of Astralhollow'),
    (14, 'The Prismwaste', 32, 75, '#efa6bc', 'Glassflame of the Prismwaste'),
    (15, 'The Obsidian Orrery', 59, 90, '#e3b660', 'Clockpyre of the Orrery'),
]
DESCRIPTION = ('Ten grave crosses hold the embers of Eldmarr. Find one in each of the ten zones listed below. '
               'Stand beside a cross and commune for three seconds to summon its Firelord. Moving or taking damage breaks the channel. '
               'Defeat each herald and gather its Ember Shard, then return to Iarn to forge the Ember Key. '
               'Every hero must earn this key, including those who have entered the raid before.')

def level99_xp():
    levels=json.loads((ROOT/'world/levels.txt').read_text())
    return levels[98] if len(levels)>98 else levels[-1]+(99-len(levels))*(levels[-1]-levels[-2])

def install(w):
    zones = [w] + w.get('zones', [])
    for zone, name, x, y, color, boss in SITES:
        if zone >= len(zones): continue
        z = zones[zone]
        cross = dict(id=f'raid_cross_{zone}', x=x, y=y, zone=zone, name='Ember Grave Cross',
                     shard=f'ember_shard_{zone}', bossName=boss, color=color)
        z['crosses'] = [c for c in z.get('crosses', []) if not c['id'].startswith('raid_cross_')] + [cross]
        z['slimes'] = [s for s in z['slimes'] if s['kind'] != KIND] + [dict(kind=KIND, x=x-2.5, y=y, ambush=f'raid_key:{zone}')]
    if len(zones) > 45:
        z = zones[45]
        z['npcs'] = [n for n in z['npcs'] if n['id'] != 'raid_key_keeper'] + [dict(
            id='raid_key_keeper', name='Iarn Emberkeeper', role='Keeper of the Ember Key', x=23, y=131,
            color='#eda66c', offers=[], buys=False, look=dict(hair='#d9c7ad', skin='#bd8c6f', style='braid'),
            dialogue='Eldmarr has scattered his embers across the old roads. Gather all ten Ember Shards and I will forge your key. The Chained Forge opens only for a hero who has earned it.')]
        q = dict(id=QUEST, title='The Ember Key', npc='raid_key_keeper', description=DESCRIPTION,
                 objectives=[dict(kind='bring', target=f'ember_shard_{i}', count=1, label=name) for i,name,*_ in SITES],
                 level=99, minLevel=99, rewardXp=level99_xp()//10,
                 rewardGold=0, rewardItem='ember_key', requires=None, repeatable=False)
        z['quests'] = [a for a in z['quests'] if a['id'] != QUEST] + [q]
        for p in z['portals']:
            if p['id'] == 'ew_raid': p['needs_quest'] = QUEST
    return w

def install_file():
    path=ROOT/'world/map.txt';w=json.loads(path.read_text());install(w)
    path.write_text(json.dumps(w, indent=2, ensure_ascii=False)+'\n')

def reapply_after_generator():
    if '--check' not in sys.argv: install_file()

def catalog():
    p=ROOT/'world/items.txt';items=json.loads(p.read_text())
    ids={f'ember_shard_{i}' for i,*_ in SITES}|{'ember_key'}
    items=[i for i in items if i['id'] not in ids]
    items += [dict(id=f'ember_shard_{i}',name=f'{name} Ember Shard',kind='material',rarity='common',sell=0) for i,name,*_ in SITES]
    items.append(dict(id='ember_key',name='Ember Key',kind='material',rarity='common',sell=0))
    p.write_text(json.dumps(items,indent=2,ensure_ascii=False)+'\n')
    enemy=dict(kind=KIND,name='Firelord',level=99,stats=[60000,650,3.2,2.1],profile=[.8,1.7,7,12],
               boss=False,elite=True,outdoor=True,gold=0,material='ember_key',lootSource=None,ranged=None,
               slam=0,melee=1,color='#ed9152',artFrom='cf_eldmarr')
    (ROOT/'world/raid_key.txt').write_text(json.dumps([enemy],indent=2)+'\n')
    for name,value in [('elite-power',[1,1]),('enrage',[240,120])]:
        path=ROOT/f'world/{name}.txt';d=json.loads(path.read_text());d[KIND]=value
        path.write_text(json.dumps(d,indent=2)+'\n')

def check():
    import generate_gloamfen as fen
    w=json.loads((ROOT/'world/map.txt').read_text());zones=[w]+w['zones']
    for i,name,x,y,*_ in SITES:
        z=zones[i];seen,_=fen.flood(z,(z['spawn']['x'],z['spawn']['y']))
        assert seen[int(y/.5),int(x/.5)], (name,'unreachable cross')
        assert seen[int(y/.5),int((x-2.5)/.5)], (name,'unreachable summon')
        assert all(math.hypot(s['x']-x,s['y']-y)>=8 for s in z['slimes'] if s['kind']!=KIND), (name,'enemy too near')
        assert all(math.hypot(p['x']-x,p['y']-y)>p['r']+8 for p in z.get('portals',[]))
        assert all(not(c['x0']-6<x<c['x1']+6 and c['y0']-6<y<c['y1']+6) for c in [z.get('city')]+z.get('camps',[]) if c)
        for source in zones:
            assert all(math.hypot(p['tx']-x,p['ty']-y)>8 for p in source.get('portals',[]) if p['to']==i)
    print('Raid key: ten reachable quiet crosses, clear summons, safe hubs and portal arrivals')

if __name__=='__main__':
    if '--check' not in sys.argv: install_file();catalog()
    check()
