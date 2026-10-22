"""RAID-PACKS catalog and encounters. Tuning belongs in elite-power.txt.

Four dungeon elite silhouettes: hammer brute, furnace crawler, suspended
crucible caster and shield sentry. Bosses are separate tasks.
"""
SPECS = [
    ('brute', 'Slaghammer Brute', [1280000,16300,2.2,1.8], '#c8895c', True, None, 3.8, 0),
    ('crawler', 'Ventspitter Crawler', [960000,13500,2.5,1.5], '#df9659', True, [17,11,'#ffb969',1,3,.24], 0, 0),
    ('caster', 'Crucible Channeler', [1110000,13900,2,1.6], '#e48b6b', True, [18,10,'#ff9971',1.1,5,.22], 0, 0),
    ('sentry', 'Obsidian Bulwark', [1280000,16300,2.2,1.8], '#87b6bd', True, None, 0, 1),
]
ENEMIES = [dict(kind='cf_'+k,name=n,level=99,stats=s,color=c,elite=e,outdoor=False,
    profile=[.9,1.8,8,13],boss=False,gold=12000,
    material='cf_'+k+'_relic',raidPack=True,ranged=r,slam=slam,melee=melee)
    for k,n,s,c,e,r,slam,melee in SPECS]

# All compositions remain four enemies. Each has a ranged threat, a heavy
# melee threat and a reason for the ten fighters to move off a narrow bridge.
COMPOSITION = ['brute','sentry','crawler','caster']
def install(zone):
    """Replace pack spawns only. Preserve encounters from later boss tasks."""
    kinds={e['kind'] for e in ENEMIES}
    zone['slimes']=[s for s in zone['slimes'] if s['kind'] not in kinds]
    for pack in zone['forgePacks']:
        pack['kinds']=['cf_'+k for k in COMPOSITION]
        offsets=[(-1.5,-1.5),(1.5,-1.5),(-1.5,1.5),(1.5,1.5)]
        # Longitudinal lines keep all four threats usable on the narrow bridges.
        lines={2:(13,-26,.75),5:(10,-44,.9),6:(0,-1,1)}
        if pack['id'] in lines:
            import math
            dx,dy,scale=lines[pack['id']]
            length=math.hypot(dx,dy)
            offsets=[(dx/length*(n*4-6)*scale,dy/length*(n*4-6)*scale) for n in range(4)]
        for kind,(dx,dy) in zip(pack['kinds'],offsets):
            zone['slimes'].append(dict(kind=kind,x=pack['x']+dx,y=pack['y']+dy))

def gear_items():
    """Three unique shared pieces; the level-99 purple budget, no set bonus."""
    import json
    from pathlib import Path
    from gear_levels import bonus_stats
    root=Path(__file__).resolve().parents[1]
    # Follow the existing level-99 purple budget while drawing original shapes.
    items=json.loads((root/'world/items.txt').read_text())
    names={'pants':'Cinderwork Kiln Gaiters','necklace':'Cinderwork Crucible Pendant','accessory':'Cinderwork Clamp Ring'}
    result=[]
    for kind,name in names.items():
        baseline=next(i for i in items if i.get('source')=='blackhour' and i['kind']==kind and not i.get('class'))
        i=dict(id='cfpack_'+kind,name=name,kind=kind,rarity='epic',requiredLevel=99,
            sell=baseline['sell'],attack=baseline['attack'],defense=baseline['defense'],
            source='chained_forge_packs',**{'class':None},variant='regearcfpack',art='regearcfpack')
        i['bonusStats']=bonus_stats(i)
        result.append(i)
    return result
