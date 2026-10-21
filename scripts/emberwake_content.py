"""Emberwake's outdoor catalog; ordinary stats follow the Yearwheel tier.

Balance adjustments belong in elite-power.txt, not these baseline records.
"""
SPECS = [
    ('ashback', 'Ashback Salamander', 95, [840000,10500,3.2,1.5], '#e99055', False),
    ('glasswing', 'Obsidian Glasswing', 96, [900000,11200,3.8,1.6], '#a4b9cf', False),
    ('slagjaw', 'Slagjaw Burrower', 97, [970000,12000,2.5,1.7], '#dca16b', False),
    ('cinderhorn', 'Cinderhorn Ram', 98, [1020000,12600,4.0,1.5], '#cd785b', False),
    ('chainmaw', 'Chainmaw, the First Shackle', 97, [5500000,37000,3.0,3.3], '#f2b16a', True),
    ('bellows', 'Yrsa, the Living Bellows', 99, [6900000,43000,2.0,3.7], '#88cbd3', True),
    ('crown', 'The Uncrowned Ember', 99, [8100000,49000,2.9,3.9], '#eab776', True),
]
ENEMIES = [dict(kind='ew_'+k,name=n,level=l,stats=s,color=c,elite=e,outdoor=True,
    profile=[.7,1.4,7,8.5],boss=False,gold=(140000 if e else 28000),
    material='ew_'+k+'_relic',ranged=([12,10,'#f29d54',.7,1,0] if k in ('glasswing','bellows') else None),
    slam=(4.8 if k in ('chainmaw','crown') else 0),melee=1) for k,n,l,s,c,e in SPECS]
