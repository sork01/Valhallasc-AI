"""The Emberfall Crags' outposts, people and quests. Data for scripts/crags_design.py (shaped coordinates).

Every old `crags_*` quest id stays (saved progress, tests, world.rs, quest_gear_rewards): their text, giver and targets are rewritten
so the chain walks the map instead of sitting in Cinderwatch Camp. Every quest is level 5-10, rewardXp = levels.txt[level-1] / 10.
Rule for elites (owner): three per zone, two with a quest, one without: `cinderlord` and `slagmaw` with, `ashwing` without.
Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json

from quest_gear_rewards import reward_for

ELITES = [('cinderlord', 246, 160), ('slagmaw', 214, 326), ('ashwing', 112, 32)]
XP = {5: 80, 6: 100, 7: 130, 8: 150, 9: 180, 10: 210}

HUT = dict(r=0, width=3.4, depth=3.2)

# (kind, dx, dy, extra) around each outpost's plaza
DRESSING = {
    'anvilrest': [
        ('house', -9, -6, dict(HUT, label='Bunkhouse', color='#7a5a48')), ('house', 9, -9, dict(HUT, label='Tally Office', color='#6a5a58')),
        ('tent', -10, 5, dict(r=1.5, width=3, depth=2.4, color='#8a6a4a', label='Stores')),
        ('cf_furnace', 11, 5, dict(r=1.2)), ('cf_anvil', 7, 6, dict(r=.6)), ('cf_bellows', 12, 1, dict(r=.8)),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Anvilrest')),
        ('stall', -5, 3, dict(r=0, width=1.8, depth=1.2, color='#8a6a4a', label='Slag & Sundries')),
        ('barrels', -3, 6, dict(r=0, width=.6, depth=.6, color='', label='')), ('barrels', -2, 7, dict(r=0, width=.6, depth=.6, color='', label='')),
        ('lamp', -4, -3, dict(r=.18)), ('lamp', 5, -3, dict(r=.18)), ('brazier', 3, 4, dict(r=.4)),
    ],
    'ashford': [
        ('house', -9, -5, dict(HUT, label='Toll House', color='#6a4a44')), ('house', 9, 8, dict(HUT, label='Ford Inn', color='#7a4a3a')),
        ('tent', 10, -4, dict(r=1.5, width=3, depth=2.4, color='#9a5a3a', label="Carters' Rest")),
        ('stall', -6, 4, dict(r=0, width=1.8, depth=1.2, color='#9a5a3a', label='Ford Supplies')),
        ('noticeboard', -2, -6, dict(r=.4, width=1.3, depth=.4, label='Ashford')),
        ('campfire', 3, 3, dict(r=.65)), ('bench', 4, 7, dict(r=0, width=1.5, depth=.45)),
        ('lamp', -4, 0, dict(r=.18)), ('lamp', 5, -2, dict(r=.18)),
        ('barrels', -10, 4, dict(r=0, width=.6, depth=.6, color='', label='')),
    ],
    'lasthearth': [
        ('house', -9, -4, dict(HUT, label='The Last Hearth', color='#7a4a4a')), ('house', 9, -5, dict(HUT, label='Sky Loft', color='#5a5a7a')),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#6a6a9a', label='Stargazers')),
        ('stall', -6, 5, dict(r=0, width=1.8, depth=1.2, color='#7a4a4a', label='Hearth Goods')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Lasthearth')),
        ('brazier', -2, -1, dict(r=.4)), ('brazier', 2, 3, dict(r=.4)), ('lamp', -5, 2, dict(r=.18)), ('lamp', 5, 1, dict(r=.18)),
    ],
}

NPCS = [
    dict(id='anvil_ingrid', hamlet='anvilrest', dx=-3, dy=-1, name='Ingrid Slagfoot', role='Quarry forewoman', color='#a0704a',
         look=dict(skin='#c99b7a', hair='#3a2e2a', style='long', hat='hood', hatColor='#6a4a3a'),
         dialogue='Skaldholm was built out of this hole. Nobody thanks a quarry, but every wall you ever leaned on started here.'),
    dict(id='anvil_bror', hamlet='anvilrest', dx=5, dy=3, name='Bror Coldhammer', role='Smith', color='#7a7a8a',
         look=dict(skin='#d9b08c', hair='#8a8a7a', style='short', hat='none', hatColor='#5a5a6a'),
         dialogue='The hammer is cold because I am patient. The furnace is cold because the wisps ate my coal.'),
    dict(id='anvil_trader', hamlet='anvilrest', dx=-5, dy=4.6, name='Hedda Tallyhand', role='Outpost trader', color='#8a6a4a', trader=True,
         look=dict(skin='#edc5a1', hair='#6a4a2a', style='long', hat='none', hatColor='#8a6a4a'),
         dialogue='Salves, tonics and an honest count. Whatever the quarry lacks, I have it in the back.'),
    dict(id='ford_tora', hamlet='ashford', dx=-3, dy=2, name='Tora Stepfast', role='Reeve of the Ford', color='#b0603a',
         look=dict(skin='#c99b7a', hair='#a05a2a', style='long', hat='none', hatColor='#b0603a'),
         dialogue='The lava moves the ford a stone a year. I move the stones back. It is a slow argument, and so far I am winning.'),
    dict(id='ford_olaf', hamlet='ashford', dx=1, dy=-3, name='Olaf Longrein', role='Carter', color='#8a7a5a',
         look=dict(skin='#d9b08c', hair='#5a4a3a', style='short', hat='straw', hatColor='#a08a5a'),
         dialogue='Twenty years hauling ore up the Highfire road, and the mules have only tried to kill me twice.'),
    dict(id='ford_trader', hamlet='ashford', dx=-6, dy=5.6, name='Signe Tollpenny', role='Outpost trader', color='#9a5a3a', trader=True,
         look=dict(skin='#edc5a1', hair='#c9a050', style='long', hat='none', hatColor='#9a5a3a'),
         dialogue='Pay the toll or do not, the lava does not mind. Tonics are extra.'),
    dict(id='ford_ulf', hamlet='ashford', dx=4, dy=-8, name='Ulf Greyboots', role='Ore carter', color='#7a6a5a',
         look=dict(skin='#b98a6a', hair='#3a3028', style='short', hat='hood', hatColor='#5a4a3a'),
         dialogue='The cart is loaded and the ford is open. Past the ford is another matter. Walk with me and I will not stop.',
         escort=dict(quest='ford_cart', **{'class': 'warrior'}, female=False, hairColor=1, skin=0, level=8, speed=2.5,
                     route=[[197, 142], [197, 132], [192, 102], [150, 100], [128, 102.13]],
                     ambush=[dict(at=[172, 102], r=11, tag='ford_ulf#road')])),
    dict(id='hearth_sigrid', hamlet='lasthearth', dx=-4, dy=1, name='Sigrid Lastcoal', role='Keeper of the Hearth', color='#a04a4a',
         look=dict(skin='#d9b08c', hair='#d8d8d8', style='long', hat='hood', hatColor='#7a3a3a'),
         dialogue='This fire has burned since before the Orrery stopped. Every traveller going east takes a coal, and every one coming back returns it.'),
    dict(id='hearth_elof', hamlet='lasthearth', dx=4, dy=2, name='Elof Skyward', role='Stargazer', color='#6a6a9a',
         look=dict(skin='#edc5a1', hair='#2a2a3a', style='short', hat='hood', hatColor='#4a4a7a'),
         dialogue='The stars over the Crags are the same as anywhere. It is the ground that keeps looking back at them.'),
    dict(id='hearth_trader', hamlet='lasthearth', dx=-6, dy=6.6, name='Astrid Coalcask', role='Outpost trader', color='#7a4a4a', trader=True,
         look=dict(skin='#c99b7a', hair='#7a3a2a', style='long', hat='none', hatColor='#7a4a4a'),
         dialogue='Last goods before the Orrery. After this you eat starlight, and I am told it is thin.'),
]

PLACES = [
    dict(id='anvil_deep', name='The Deep Cut', x=112, y=312, r=7),
    dict(id='anvil_props_m', name='The Pit Props', x=110, y=324, r=2.1, waves=[dict(at=1, tag='anvil_props_m#a'), dict(at=11, tag='anvil_props_m#b')]),
    dict(id='anvil_rim', name='The Rim of the Sunpit', x=186, y=284, r=7),
    dict(id='ford_beacon', name='The Highfire Beacon', x=122, y=92, r=7),
    dict(id='ford_lit_m', name='The Beacon Lit', x=122, y=92, r=2.1, waves=[dict(at=1, tag='ford_lit_m#a'), dict(at=11, tag='ford_lit_m#b')]),
    dict(id='ford_crown', name='The Ashen Crown', x=64, y=70, r=7),
    dict(id='hearth_glass', name='The Glass Shore', x=304, y=113, r=7),
    dict(id='hearth_horns', name='The Horn Gate', x=232, y=166, r=7),
    dict(id='crags_forge', name='The Giants\' Forge', x=112, y=155, r=7),
    dict(id='crags_vents', name='The Steam Vents', x=36, y=140, r=7),
    dict(id='crags_slopes', name='The Red Stair', x=300, y=282, r=7),
]

# Sleepers woken by a wave or an escort ambush
AMBUSH = [('wisp', 106, 320, 'anvil_props_m#a'), ('wisp', 115, 328, 'anvil_props_m#a'), ('spider', 105, 328, 'anvil_props_m#b'), ('spider', 116, 320, 'anvil_props_m#b'),
          ('golem', 117, 88, 'ford_lit_m#a'), ('wraith', 127, 96, 'ford_lit_m#a'), ('wraith', 116, 96, 'ford_lit_m#b'), ('golem', 128, 88, 'ford_lit_m#b'),
          ('wraith', 176, 107, 'ford_ulf#road'), ('spider', 166, 96, 'ford_ulf#road')]


def Q(id, title, npc, level, gold, desc, objectives, requires=None, repeatable=False, **extra):
    q = dict(id=id, title=title, npc=npc, description=desc,
             objectives=[dict(kind=k, target=t, label=l, count=c) for k, t, l, c in objectives],
             level=level, rewardXp=XP[level], rewardGold=gold, requires=requires, repeatable=repeatable)
    reward = reward_for(id)
    if reward:
        q['rewardItem'] = reward
    q.update(extra)
    return q


QUESTS = [
    # Anvilrest, at the quarries
    Q('anvil_coal', 'Cold Furnace', 'anvil_bror', 5, 60,
      'The wisps have eaten the coal, so Bror will burn the wisps instead. Bring him five ember cores to light the furnace.',
      [('bring', 'ember_core', 'Bring ember cores', 5)]),
    Q('anvil_cut', 'The Deep Cut', 'anvil_ingrid', 6, 75,
      'The night shift came up from the Deep Cut and will not go back down. Go to the quarry floor, see what they saw and clear four wisps on the way.',
      [('visit', 'anvil_deep', 'Go down into the Deep Cut', 1), ('kill', 'wisp', 'Defeat wisps in the quarry', 4)]),
    Q('anvil_props', 'The Pit Props', 'anvil_ingrid', 7, 95,
      'Sparks are eating the timbers that hold up the Deep Cut. Stand at the pit props for twenty seconds and keep everything that burns away from them.',
      [('hold', 'anvil_props_m', 'Guard the pit props', 20)], requires='anvil_cut'),
    Q('anvil_rim', 'Where the Heat Comes From', 'anvil_bror', 6, 75,
      'Bror swears the south of the quarry gets hotter every year. Walk to the Sunpit, the great fire pit on the flats, and stand on its rim. If your boots smoke, he is right.',
      [('visit', 'anvil_rim', 'Stand on the rim of the Sunpit', 1)], requires='anvil_coal'),
    Q('anvil_slagmaw', 'Slagmaw', 'anvil_ingrid', 10, 180,
      'Something crawled out of the Sunpit and made its nest on the south shore. It has eaten two ore carts and the mule. Ingrid wants it dead, and she says nobody should try this alone.',
      [('kill', 'slagmaw', 'Defeat Slagmaw', 1)], requires='anvil_props', recommendedPlayers=3),
    # Ashford, at the lava ford
    Q('ford_veils', 'Toll in Ash', 'ford_tora', 8, 110,
      'Ash veils make the only cloth that will not burn on the ford. Tora pays her stone-setters in it. Bring her four.',
      [('bring', 'ash_veil', 'Bring ash veils', 4)]),
    Q('ford_stones', 'Stepping Stones', 'ford_tora', 9, 130,
      'A golem heart is the one stone the lava will not swallow. Bring Tora three, so the ford stays where it is for another year.',
      [('bring', 'basalt_heart', 'Bring basalt hearts', 3)], requires='ford_veils'),
    Q('ford_cart', 'The Highfire Road', 'ford_olaf', 8, 110,
      "Ulf's ore cart has to get over the ford and up the Highfire road, and the road is not safe. Speak to Ulf at the north end of Ashford and walk with him. If he falls, or you do, start again.",
      [('escort', 'ford_ulf', 'Walk Ulf up the Highfire road', 1)]),
    Q('ford_beacon', 'The Highfire Beacon', 'ford_olaf', 8, 110,
      'The carters steered by a beacon on Highfire Ridge until it went dark. Olaf wants to know if it can be lit again. Find the beacon.',
      [('visit', 'ford_beacon', 'Find the Highfire Beacon', 1)], requires='ford_cart'),
    Q('ford_lit', 'The Beacon Lit', 'ford_tora', 9, 130,
      'Fire draws the things of the ridge. Stand at the beacon for twenty seconds while it catches, and let nothing put it out.',
      [('hold', 'ford_lit_m', 'Hold the beacon while it catches', 20)], requires='ford_beacon'),
    Q('ford_crown', 'The Ashen Crown', 'ford_tora', 10, 150,
      'Nobody has set stones north of the last river since Tora was a girl. Cross it, climb to the Ashen Crown and defeat three golems, so the road can go on to the Wyrdwood.',
      [('visit', 'ford_crown', 'Climb the Ashen Crown', 1), ('kill', 'golem', 'Defeat golems on the Crown', 3)], requires='ford_lit'),
    # Lasthearth, on the Orrery road
    Q('hearth_fangs', 'Needles for the Stars', 'hearth_elof', 7, 95,
      'Elof grinds magma fangs into sighting needles for his brass tubes. Nothing else keeps its edge in this heat. Bring four.',
      [('bring', 'magma_fang', 'Bring magma fangs', 4)]),
    Q('hearth_glass', 'The Glass Shore', 'hearth_elof', 8, 110,
      'North of the second river the lava once met the sea and turned the beach to black glass. Elof wants to know if it still shines at night. Cross the ford and find the Glass Shore.',
      [('visit', 'hearth_glass', 'Find the Glass Shore', 1)], requires='hearth_fangs'),
    Q('hearth_horns', 'The Horn Gate', 'hearth_sigrid', 8, 110,
      'Wraiths walk the Horned Terrace at dusk, and they have come to within sight of the Hearth. Go up to the Horn Gate between the peaks and defeat five of them.',
      [('visit', 'hearth_horns', 'Reach the Horn Gate', 1), ('kill', 'wraith', 'Defeat wraiths on the Terrace', 5)]),
    Q('hearth_stair', 'The Red Stair', 'hearth_sigrid', 7, 95,
      "A coal went out on the Red Slopes, and Sigrid's people do not lose coals. Go down the Red Stair towards the Canopy and bring back word of the traveller who carried it.",
      [('visit', 'crags_slopes', 'Go down the Red Stair', 1), ('kill', 'spider', 'Defeat spiders on the Slopes', 4)]),
    # Cinderwatch: the far corners
    Q('crags_forge_trip', "The Giants' Forge", 'crags_healer', 8, 110,
      "An anvil the size of a house lies on the Long Steps. Nobody knows who forged there, but Sister Iona's ash wraiths seem to know the way. Find the Giants' Forge.",
      [('visit', 'crags_forge', "Find the Giants' Forge", 1)], requires='crags_wraiths'),
    Q('crags_steam', 'Where Fire Meets Frost', 'crags_scout', 9, 130,
      'At the west end of the Crags the glacier comes down onto hot rock and the ground screams. Kael wants a map of the Steam Vents before the Rimeveil patrols ask for one.',
      [('visit', 'crags_vents', 'Reach the Steam Vents', 1)], requires='crags_golems'),
]

# Old ids, new meaning: (fields to replace)
REWRITES = {
    'crags_wisps': dict(title='Sparks on the Flats', description='Cinder wisps have drifted off the Sunpit Flats and up to the south gate. Go down the camp road and defeat four of them before they reach the tents.'),
    'crags_wisp_sweep': dict(npc='anvil_ingrid', title='Sparks in the Timbers', description='Wisps follow the ore carts into the Anvil Quarries and set the scaffolds alight. Clear eight of them from the workings.', requires='crags_welcome'),
    'crags_spiders': dict(title='The Red Slopes', description='Magma spiders nest on the Red Slopes, across the fourth river. Take the ford east of the Terrace road and defeat four before they spin over it.'),
    'crags_spider_sweep': dict(npc='hearth_sigrid', title='Webs on the Road', description="Webs have closed the Orrery road twice this month. Defeat seven magma spiders so Lasthearth's travellers can get through."),
    'crags_wraiths': dict(title='Ash on the Long Steps', description='Ash wraiths have come down the Long Steps, north of the third river, and they are not resting. Cross the north ford and defeat three, then Iona can sleep.'),
    'crags_wraith_sweep': dict(npc='ford_tora', title='Faces in the Ash', description='The stone-setters will not work the ford while wraiths watch them from the far bank. Defeat six.'),
    'crags_golems': dict(title='The Stones of Highfire', description='Cinder golems have woken on Highfire Ridge, north of the second river. Cross at Ashford, climb the ridge and bring down two.'),
    'crags_golem_sweep': dict(npc='ford_olaf', title='Boulders in the Road', description='A golem standing still looks exactly like the rock the carters have to go round. Bring down four on Highfire Ridge before another mule walks into one.'),
    'crags_expedition': dict(description='Captain Sera wants one patrol that has seen all of it. Defeat two of every kind in the Crags, from the Flats to Highfire Ridge, and report back.'),
    'crags_cinderlord': dict(description='The Cinderlord holds the Horned Terrace among the peaks, and his fire is why the river rose. Gather a party, go up past the Horn Gate and bring him down.'),
    'crags_bounty': dict(description='Quartermaster Dain pays for proof that the roads are open. Defeat ten enemies of any kind anywhere in the Crags.'),
    'crags_supply_route': dict(title='Three Supply Runs', description='Dain has crates for all three outposts. Carry them to Ingrid at Anvilrest, Tora at Ashford and Sigrid at Lasthearth. Each outpost has a Travel Master: speak to them and you can fly back.',
                               objectives=[dict(kind='talk', target='anvil_ingrid', label='Deliver to Ingrid at Anvilrest', count=1), dict(kind='talk', target='ford_tora', label='Deliver to Tora at Ashford', count=1),
                                           dict(kind='talk', target='hearth_sigrid', label='Deliver to Sigrid at Lasthearth', count=1)],
                               requires='crags_welcome'),
}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    master = next(n for n in zone['npcs'] if n['id'] == 'travel_cinderwatch')
    healer = next(n for n in zone['npcs'] if n['id'] == 'crags_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'crags_supplier')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look'])
        if 'escort' in s:
            n['escort'] = s['escort']
        out.append(n)
    spots = {'anvilrest': (-1, 2), 'ashford': (-1, 5), 'lasthearth': (1, -2)}
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(master)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=['travel_cinderwatch'])
        out.append(t)
        if t['id'] not in master['travelLinks']:
            master['travelLinks'].append(t['id'])
    # every hub has a mailbox (scripts/mailboxes.py ran on the old square, before the outposts exist)
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_1_cinderwatch_camp')
    for key, (dx, dy) in {'anvilrest': (3, 1), 'ashford': (2, 1), 'lasthearth': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_1_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square, where the outposts do not exist yet."""
    directory = [d for d in json.loads(path.read_text()) if not (d['zone'] == 1 and d['hub'] in {h['name'] for h in hamlets.values()})]
    for key, h in hamlets.items():
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_1_{key}')
        master = next(n for n in zone['npcs'] if n['id'] == f'travel_{key}')
        directory.append(dict(id=box['id'], zone=1, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=master['x'], y=master['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(zone, hamlets):
    # idempotent, so `plan` also works on a map that already carries the design
    new_npcs = people(zone, hamlets)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    ids = {p['id'] for p in PLACES}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    ids = {q['id'] for q in QUESTS}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids]
    zone['camps'] = camps(hamlets)
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
