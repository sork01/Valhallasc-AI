"""The Wyrdwood's outposts, people and quests. Data for scripts/wyrdwood_design.py (shaped coordinates, zone 6).

Every old `wyrd_*`, `barrow_*`, `entry_norn` and `es_*` quest id stays (saved progress, tests, quest_gear_rewards): text is rewritten only
where the geography changed (the glade, the road in, the beacons). Fourteen quests are new, with three new outposts and one new elite.
Rule for elites (owner): three per zone, two with a quest, one without: Oakhorn and Hrungnir (old, quests) and `hangedking` without.
New ids and people start `wyrd_` and stay within 19 characters (the accept string is capped at 32). Levels 21-30, rewardXp =
levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(21, 31)}
GOLD = {21: 460, 22: 500, 23: 540, 24: 590, 25: 650, 26: 750, 27: 880, 28: 940, 29: 990, 30: 1200}

# the hamlets: plaza, half width/height of the sanctuary rectangle
HAMLETS = {
    'gallowsfoot': dict(name='Gallowsfoot', x=255, y=297, hw=14, hh=11),
    'ridgewatch':  dict(name='Ridgewatch', x=180, y=143, hw=14, hh=11),
    'highmoor':    dict(name='Highmoor Hold', x=150, y=112, hw=14, hh=11),
}

ELITES = [('oakhorn', 251, 258), ('hrungnir', 152, 78), ('hangedking', 318, 298)]

HUT = dict(r=0, width=3.4, depth=3.2)

DRESSING = {
    'gallowsfoot': [
        ('house', -9, -6, dict(HUT, label='Rope Hall', color='#6a5a4a')), ('house', 9, -7, dict(HUT, label='Fletcher', color='#7a5a3a')),
        ('tent', 10, 6, dict(r=1.5, width=3, depth=2.4, color='#6f5a4a', label='Watch')),
        ('stall', -5, 3, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Quills & Cord')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Gallowsfoot')),
        ('campfire', 3, 3, dict(r=.65)), ('bench', 5, -4, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -2, 0, dict(r=.4)), ('lamp', -4, -3, dict(r=.18)), ('lamp', 6, 1, dict(r=.18)),
        ('barrels', -8, 6, dict(r=0, width=.6, depth=.6, color='', label='')),
    ],
    'ridgewatch': [
        ('house', -9, -6, dict(HUT, label='Ridge Hall', color='#5a6a7a')), ('house', 9, -6, dict(HUT, label='Ram Barn', color='#7a6a4a')),
        ('tent', -10, 6, dict(r=1.5, width=3, depth=2.4, color='#5f6f8a', label='Watch')),
        ('stall', 8, 5.5, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Horn & Hide')),
        ('noticeboard', -2, -6, dict(r=.4, width=1.3, depth=.4, label='Ridgewatch')),
        ('campfire', 3, 3, dict(r=.65)), ('bench', 5, -4, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -2, 0, dict(r=.4)), ('lamp', -5, 2, dict(r=.18)), ('lamp', 7, -1, dict(r=.18)),
    ],
    'highmoor': [
        ('house', -9, -6, dict(HUT, label='Hold Hall', color='#5a5a72')), ('house', 9, 6, dict(HUT, label='Loom Shed', color='#6a5a6a')),
        ('tent', 10, -6, dict(r=1.5, width=3, depth=2.4, color='#5f5f8a', label='Lookout')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Tinder & Wick')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Highmoor Hold')),
        ('campfire', 3, 3, dict(r=.65)), ('brazier', -2, -1, dict(r=.4)), ('brazier', 6, 1, dict(r=.4)),
        ('lamp', -4, 1, dict(r=.18)), ('lamp', 5, -3, dict(r=.18)),
    ],
}

NPCS = [
    dict(id='wyrd_gf_hild', hamlet='gallowsfoot', dx=-3, dy=-1, name='Gallows-Warden Hild Ropewalker', role='Gallows-warden', color='#7a6a8a',
         look=dict(skin='#c99b7a', hair='#2a2a32', style='long', hat='hood', hatColor='#4a3a5a'),
         dialogue='My mother kept this hill and her mother before her. The rope is old and the crows are older, and the king on the beam does not like to be looked at. Do the work of the hill and he leaves you alone.'),
    dict(id='wyrd_gf_orm', hamlet='gallowsfoot', dx=5, dy=3, name='Orm Crowfriend', role='Crow-keeper', color='#5a5a6a',
         look=dict(skin='#d9b08c', hair='#7a7a7a', style='short', hat='hood', hatColor='#3a3a4a'),
         dialogue='They talk, you know. They are only ever saying the one thing: he is awake. I used to find that funny. Walk out to the old mill and see if the fells agree.'),
    dict(id='wyrd_gf_trader', hamlet='gallowsfoot', dx=-5, dy=4.6, name='Sigrun Stitchwife', role='Outpost trader', color='#a87a45', trader=True,
         look=dict(skin='#edc5a1', hair='#a8683a', style='long', hat='none', hatColor='#a87a45'),
         dialogue='Cord, quills, stew and tonics. Everything on this table was made on the hill, from the hill, and I sleep better than you would think.'),
    dict(id='wyrd_rw_dagny', hamlet='ridgewatch', dx=-3, dy=-1, name='Warder Dagny Stormhand', role='Ridge warder', color='#5a7a9a',
         look=dict(skin='#d9b08c', hair='#b89a6a', style='short', hat='hood', hatColor='#4a5a7a'),
         dialogue='Two ridges, two gaps, and the rams that live between them. I hold the terrace so the fort does not have to. The East Gap is the only way up, so everything that climbs, climbs past me.'),
    dict(id='wyrd_rw_fenn', hamlet='ridgewatch', dx=5, dy=3, name='Fenn Ramsong', role='Ram-herder', color='#8a7a5a',
         look=dict(skin='#c99b7a', hair='#5a3a2a', style='short', hat='none', hatColor='#6a5a4a'),
         dialogue='I sang to those rams from lambs. Now the lightning is in their horns and they butt the beacon in their sleep. They are not wicked. They are loud, and they are lit from the inside.'),
    dict(id='wyrd_rw_trader', hamlet='ridgewatch', dx=-5, dy=6.2, name='Ragna Hornbuyer', role='Outpost trader', color='#7a8aa0', trader=True,
         look=dict(skin='#edc5a1', hair='#8a4a2a', style='long', hat='none', hatColor='#7a8aa0'),
         dialogue='Horn, hide, tonics and stew. A stormram horn hums when the weather turns, so the ones on my shelf are never quite asleep.'),
    dict(id='wyrd_hm_sunniva', hamlet='highmoor', dx=-3, dy=-1, name='Hold-Keeper Sunniva Coldhearth', role='Hold-keeper', color='#7a7aa8',
         look=dict(skin='#edc5a1', hair='#cfcfcf', style='long', hat='hood', hatColor='#5a5a7a'),
         dialogue='This is the last roof before the summit. Past the ring there is only Hrungnir and the weather, and I would like the weather to calm down before I have to hold the hold through another winter.'),
    dict(id='wyrd_hm_loom', hamlet='highmoor', dx=5, dy=3, name='Eirik Loomwatch', role='Thread-watcher', color='#8a6a9a',
         look=dict(skin='#c99b7a', hair='#2a2a3a', style='short', hat='hood', hatColor='#6a4a7a'),
         dialogue='The weavers tied the storm to a loom, and the loom is the reason the sky is wrong. I watch it so someone can say when it starts to unravel. Bring me thread and I will tell you how long we have.'),
    dict(id='wyrd_hm_trader', hamlet='highmoor', dx=-6, dy=5.6, name='Thorgrim Tindertrader', role='Outpost trader', color='#6a6a8a', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#6a6a8a'),
         dialogue='Tinder, wicks, stew and a tonic for the storm. If your hair stands on end, you are standing in the wrong place; I have a stool.'),
]

PLACES = [
    dict(id='wyrd_mill', name='The Ruined Mill', x=318, y=326, r=5),
    dict(id='wyrd_east_gap', name='The East Gap', x=222, y=160, r=5),
    dict(id='wyrd_hrung_ring', name="Hrungnir's Ring", x=152, y=99, r=4),
    dict(id='wyrd_rotwood', name='The Rotfang Wood', x=40, y=316, r=7),
    dict(id='wyrd_vigil_m', name='The Hanged Vigil', x=276, y=311, r=2.1, waves=[dict(at=1, tag='wyrd_vigil_m#a'), dict(at=11, tag='wyrd_vigil_m#b')]),
    dict(id='wyrd_fire_m', name='The Ridge Fire', x=204, y=145, r=2.1, waves=[dict(at=1, tag='wyrd_fire_m#a'), dict(at=11, tag='wyrd_fire_m#b')]),
    dict(id='wyrd_gale_m', name='The Gale Stones', x=122, y=100, r=2.1, waves=[dict(at=1, tag='wyrd_gale_m#a'), dict(at=11, tag='wyrd_gale_m#b')]),
    dict(id='wyrd_bridge_m', name='The Bridgehead', x=166, y=241, r=2.1, waves=[dict(at=1, tag='wyrd_bridge_m#a'), dict(at=11, tag='wyrd_bridge_m#b')]),
]

# Sleepers woken by a wave or an escort ambush (the old Eydis ambushes keep their tags, new positions)
AMBUSH = [
    ('crow', 270, 305, 'wyrd_vigil_m#a'), ('crow', 282, 316, 'wyrd_vigil_m#a'), ('troll', 270, 317, 'wyrd_vigil_m#b'), ('crow', 283, 304, 'wyrd_vigil_m#b'),
    ('ram', 198, 150, 'wyrd_fire_m#a'), ('ram', 210, 140, 'wyrd_fire_m#a'), ('ram', 198, 140, 'wyrd_fire_m#b'), ('ram', 210, 151, 'wyrd_fire_m#b'),
    ('ram', 116, 104, 'wyrd_gale_m#a'), ('ram', 128, 96, 'wyrd_gale_m#a'), ('ram', 116, 95, 'wyrd_gale_m#b'), ('ram', 128, 106, 'wyrd_gale_m#b'),
    ('troll', 160, 247, 'wyrd_bridge_m#a'), ('troll', 172, 247, 'wyrd_bridge_m#a'), ('troll', 160, 236, 'wyrd_bridge_m#b'), ('troll', 172, 237, 'wyrd_bridge_m#b'),
    ('crow', 292, 313, 'wyrd_eydis#crow'), ('crow', 286, 299, 'wyrd_eydis#crow'), ('crow', 297, 303, 'wyrd_eydis#crow'),
    ('troll', 177, 249, 'wyrd_eydis#troll'), ('troll', 189, 243, 'wyrd_eydis#troll'),
]


def Q(id, title, npc, level, desc, objectives, requires=None, repeatable=False, gold=None, **extra):
    q = dict(id=id, title=title, npc=npc, description=desc,
             objectives=[dict(kind=k, target=t, label=l, count=c) for k, t, l, c in objectives],
             level=level, rewardXp=XP[level], rewardGold=gold or GOLD[level], requires=requires, repeatable=repeatable)
    reward = reward_for(id)
    if reward:
        q['rewardItem'] = reward
    q.update(extra)
    return q


QUESTS = [
    # Hollowmoot
    Q('wyrd_h_wood', 'Into the Rotfang Wood', 'wyrd_forester', 21,
      'The blight began in the far south-west, in the oldest part of the wood, and Ulf has not seen it with his own eyes since the spring. Walk down to the Rotfang Wood past the palisade and defeat four boars on the way, then tell him how far it has spread.',
      [('visit', 'wyrd_rotwood', 'Reach the Rotfang Wood', 1), ('kill', 'boar', 'Defeat Rotfang Boars', 4)], requires='wyrd_welcome'),
    # Skuldwatch
    Q('wyrd_s_bridge', 'Hold the Bridgehead', 'wyrd_captain', 26,
      'The trolls on the south bank have started to test the bridge itself. Stand at the south end of the Troll Bridge for twenty seconds while the watch drives fresh stakes, and let nothing from the bank stop them.',
      [('hold', 'wyrd_bridge_m', 'Hold the bridgehead', 20)], requires='wyrd_trolls'),
    # Gallowsfoot, in the south-east
    Q('wyrd_gf_quills', 'Feathers for the Fletcher', 'wyrd_gf_trader', 23,
      'Sigrun fletches with gallows feathers: nothing else flies so true off a bowstring, and nothing else is so easy to come by on this hill. Bring her five.',
      [('bring', 'gallows_feather', 'Bring Gallows Feathers', 5)], requires='wyrd_crows'),
    Q('wyrd_gf_hush', 'A Hush on the Hill', 'wyrd_gf_hild', 24,
      'Hild wants the hill quiet for one night. Walk up to Gallows Rock, where the old rope hangs, and defeat six Gallowcrows on the slope.',
      [('visit', 'wyrd_gallows_rock', 'Stand at Gallows Rock', 1), ('kill', 'crow', 'Defeat Gallowcrows on the hill', 6)], requires='wyrd_crows'),
    Q('wyrd_gf_vigil', 'The Hanged Vigil', 'wyrd_gf_hild', 25,
      'Every year Hild lights the vigil lamps at the foot of the hill, so the Hanged King knows he is remembered and stays on his beam. This year the crows have come for the lamps. Stand in the circle for twenty seconds while she lights them, and keep the hill off her.',
      [('hold', 'wyrd_vigil_m', 'Guard the vigil lamps', 20)], requires='wyrd_gf_hush'),
    Q('wyrd_gf_mill', 'The Mill on the Fells', 'wyrd_gf_orm', 26,
      'The crows say the king is awake, and the crows are usually right. Orm wants to know what the fells make of it. Walk east to the Ruined Mill and defeat four trolls on the way.',
      [('visit', 'wyrd_mill', 'Reach the Ruined Mill', 1), ('kill', 'troll', 'Defeat Mosshide Trolls on the fells', 4)], requires='wyrd_gf_vigil'),
    # Ridgewatch, on the terrace between the ridges
    Q('wyrd_rw_orders', 'Sealed Orders', 'wyrd_rw_fenn', 27,
      'Dagny has sealed orders for the two other posts and no one to spare. Carry one to Sunniva at Highmoor Hold and the other to Hild at Gallowsfoot. Each post has a Travel Master, so you can fly the long way.',
      [('talk', 'wyrd_hm_sunniva', 'Deliver to Sunniva at Highmoor Hold', 1), ('talk', 'wyrd_gf_hild', 'Deliver to Hild at Gallowsfoot', 1)], requires='wyrd_beacons'),
    Q('wyrd_rw_horns', 'Horns for the Hearth', 'wyrd_rw_trader', 28,
      'A stormram horn hums on a shelf and hangs beautifully over a hearth, and every house on the terrace wants one. Bring Ragna four.',
      [('bring', 'stormram_horn', 'Bring Stormram Horns', 4)], requires='wyrd_rams'),
    Q('wyrd_rw_gap', 'Through the East Gap', 'wyrd_rw_dagny', 28,
      'The East Gap is the only way up to the terrace, and the rams have started to use it. Walk through the gap and defeat five Stormrams on the terrace.',
      [('visit', 'wyrd_east_gap', 'Walk through the East Gap', 1), ('kill', 'ram', 'Defeat Stormrams on the terrace', 5)], requires='wyrd_rams'),
    Q('wyrd_rw_fire', 'The Ridge Fire', 'wyrd_rw_dagny', 29,
      'The Ridge Beacon was lit again and the rams came for the flame. Stand in the circle beside it for twenty seconds while Dagny feeds the fire, and keep the terrace off her.',
      [('hold', 'wyrd_fire_m', 'Guard the Ridge Fire', 20)], requires='wyrd_rw_gap'),
    # Highmoor Hold, on the summit
    Q('wyrd_hm_rams', 'Rams on the Rise', 'wyrd_hm_sunniva', 29,
      'Past the second ridge the Highmoor climbs to the summit, and the rams that graze it have grown bold. Defeat eight of them on the heights.',
      [('kill', 'ram', 'Defeat Stormrams on the Highmoor', 8)], requires='wyrd_rams'),
    Q('wyrd_hm_threads', 'Threads for the Storm Loom', 'wyrd_hm_loom', 29,
      'Eirik can tell how long the weavers\' loom will hold by the knots in what falls off it. Bring him six Frayed Fate Threads.',
      [('bring', 'fate_thread', 'Bring Frayed Fate Threads', 6)], requires='wyrd_fate'),
    Q('wyrd_hm_ring', "Hrungnir's Ring", 'wyrd_hm_sunniva', 30,
      "Twelve stones stand round the summit where the storm giant sleeps. Sunniva wants to know whether they still hold. Walk up the slope until Hrungnir's Ring comes into view, no nearer, and defeat three Stormrams on the way.",
      [('visit', 'wyrd_hrung_ring', "Reach Hrungnir's Ring", 1), ('kill', 'ram', 'Defeat Stormrams on the Highmoor', 3)], requires='wyrd_hm_rams'),
    Q('wyrd_hm_gale', 'Hold Against the Gale', 'wyrd_hm_loom', 30,
      'West of the hold the old rift stones still hum, and when the weavers pull, the storm comes down through them. Stand among the stones for twenty seconds while Eirik reads the threads, and let the rams come to you.',
      [('hold', 'wyrd_gale_m', 'Hold the Gale Stones', 20)], requires='wyrd_hm_ring'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'wyrd_moonpetal': dict(description='Groa needs moonpetals for her blight salve, and the only ones still blooming grow in the glade south-east of Hollowmoot. Walk to the Moonpetal Glade, and clear three Rotfang Boars off the herb beds on the way. Then tell Groa what you saw.'),
    'wyrd_onward': dict(description='The Wyrdwood lies beyond the Emberfall Crags and the Rimeveil Glacier, where the forest has begun to go wrong. Cross the border into it, find Hollowmoot beneath the Elder Ash and report to Moot-Warden Bjorn Oakhand.'),
    'wyrd_beacons': dict(description='Hakon gives you a flint and a promise. Climb to the West Beacon on the cliffs below the first ridge, then to the Ridge Beacon in the east above it, then to the Storm Beacon on the Highmoor above the second ridge, and light them by standing beside each.'),
}

NPC_UPDATES = {
    'wyrd_beekeeper': 'My bees still work the Moonpetal Glade, south-east of town. Odd, that. Everything else in the wood has gone wyrd, but the bees only hum louder. I would not put it past them to know something we do not.',
}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    masters = {n['id']: n for n in zone['npcs'] if n['id'] in ('travel_hollowmoot', 'travel_skuldwatch')}
    master = masters['travel_skuldwatch']
    healer = next(n for n in zone['npcs'] if n['id'] == 'wyrd_mender')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'wyrd_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    spots = {'gallowsfoot': (-1, 2), 'ridgewatch': (-1, 3.5), 'highmoor': (-1, 3.5)}
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(master)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=['travel_hollowmoot', 'travel_skuldwatch'])
        out.append(t)
        for m in masters.values():
            if t['id'] not in m['travelLinks']:
                m['travelLinks'].append(t['id'])
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_6_skuldwatch')
    for key, (dx, dy) in {'gallowsfoot': (3, 1), 'ridgewatch': (2, 1), 'highmoor': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_6_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Wyrdwood entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 6]
    names = {'travel_hollowmoot': 'Hollowmoot', 'travel_skuldwatch': 'Skuldwatch'}
    for h in hamlets.values():
        names['travel_' + next(k for k, v in hamlets.items() if v is h)] = h['name']
    for master, hub in names.items():
        key = master.split('travel_')[1]
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_6_{key}')
        m = next(n for n in zone['npcs'] if n['id'] == master)
        directory.append(dict(id=box['id'], zone=6, hub=hub, x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(zone, hamlets, skuldwatch):
    """Idempotent, so `plan` also works on a map that already carries the design. `skuldwatch` is the moved fort camp."""
    new_npcs = people(zone, hamlets)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        if n['id'] in NPC_UPDATES:
            n['dialogue'] = NPC_UPDATES[n['id']]
    ids = {p['id'] for p in PLACES}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    ids = {q['id'] for q in QUESTS}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids]
    zone['camps'] = [skuldwatch] + camps(hamlets)
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
