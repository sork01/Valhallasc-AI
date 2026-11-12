"""Greenmeadow's hamlets, people and quests. Data for scripts/greenmeadow_design.py (shaped coordinates).

Quest ids `welcome`, `slime_patrol`, `meadow_bounty`, `ironhide_hunt`, `king_challenge` stay: tests, rolls.rs and saved progress use them.
Every quest is level 1-5, rewardXp = levels.txt[level-1] / 10. Rule for elites (owner): three per zone, two with a quest, one without.
Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json

from quest_gear_rewards import reward_for
from mercenary_offers import offers as mercenary_offers

ELITES = [('oldtusker', 128, 172), ('tidecrusher', 232, 278), ('orchardqueen', 392, 226)]
XP = {1: 10, 2: 20, 3: 40, 4: 60, 5: 80}

COTTAGE = dict(r=0, width=5, depth=4)
# Each hamlet builds its own way (owner, 2026-11-07): Stonefold in fieldstone and slate, Saltby in tarred planks, Applewick in limewash and thatch.
# `v` picks the variant inside a hamlet (size of the gable, roof colour, door side); passing it does not change the rng order (the default is evaluated anyway).
STONE, FISHER, THATCH = (dict(COTTAGE, style=s) for s in ('stone', 'fisher', 'thatch'))

# (kind, dx, dy, extra) around each hamlet's plaza
DRESSING = {
    'stonefold': [
        ('meadow_cottage', -9, -8, dict(STONE, v=0)), ('meadow_cottage', 9, -9, dict(STONE, v=1)), ('meadow_cottage', -10, 8, dict(STONE, v=2)),
        ('house', -1, 9, dict(r=0, width=3.4, depth=3.2, label='Fold Hall', color='#8a6a4a')),
        ('well', -4, -3, dict(r=.7)), ('noticeboard', 2, -5, dict(r=.4, width=1.3, depth=.4, label='Stonefold')),
        ('stall', 6, -2, dict(r=0, width=1.8, depth=1.2, color='#7a9a5a', label='Fold Stores')),
        ('lamp', -5, 3, dict(r=.18)), ('lamp', 5, 4, dict(r=.18)), ('flowers', -7, 3, dict(r=.55)), ('haystack', 12, 2, dict(r=.58)), ('haystack', 13, -3, dict(r=.58)),
    ],
    'saltby': [
        ('meadow_cottage', -12, -4, dict(FISHER, v=0)), ('meadow_cottage', -12, 4, dict(FISHER, v=1)), ('meadow_cottage', 12, 3, dict(FISHER, v=2)),
        ('tent', 12, -5, dict(r=1.5, width=3, depth=2.4, color='#5f8aa0', label='Net Loft')),
        ('stall', 5, 6, dict(r=0, width=1.8, depth=1.2, color='#5f8aa0', label='Fresh Catch')),
        ('barrels', 8, 6, dict(r=0, width=.6, depth=.6, color='', label='')), ('barrels', 9, 7, dict(r=0, width=.6, depth=.6, color='', label='')),
        ('campfire', -4, 4, dict(r=.65)), ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Saltby')),
        ('lamp', -6, -2, dict(r=.18)), ('lamp', 6, -3, dict(r=.18)), ('bench', -2, 6, dict(r=0, width=1.5, depth=.45)),
    ],
    'applewick': [
        ('meadow_cottage', -8, -7, dict(THATCH, v=0)), ('meadow_cottage', 8, -7, dict(THATCH, v=1)), ('meadow_cottage', -8, 7, dict(THATCH, v=2)), ('meadow_cottage', 8, 7, dict(THATCH, v=3)),
        ('well', -4, 0, dict(r=.7)), ('stall', 4, -3, dict(r=0, width=1.8, depth=1.2, color='#b65b4a', label='Cider & Apples')),
        ('noticeboard', -3, -4, dict(r=.4, width=1.3, depth=.4, label='Applewick')),
        ('lamp', 3, 3, dict(r=.18)), ('lamp', -3, 3, dict(r=.18)), ('flowers', 5, 1, dict(r=.55)), ('flowers', -6, 3, dict(r=.55)),
        ('apple_tree', 12, 0, dict(r=.9)), ('apple_tree', -12, 0, dict(r=.9)),
    ],
}

NPCS = [
    dict(id='fold_hild', hamlet='stonefold', dx=-3, dy=3, name='Hild Ewesward', role='Shepherd of the Downs', color='#b9c48a',
         look=dict(skin='#edc5a1', hair='#b08a4a', style='long', hat='straw', hatColor='#c9b070'),
         dialogue='Thirty years on these Downs and I never lost a ewe to anything but winter. Now something in the Oldgrove has a taste for mutton.'),
    dict(id='fold_torvald', hamlet='stonefold', dx=2, dy=-2, name='Torvald Stonereader', role='Keeper of the Sisters', color='#9a9aa8',
         look=dict(skin='#d9b08c', hair='#d8d8d8', style='short', hat='hood', hatColor='#6a6a7a'),
         dialogue='Nine stones stand west of here and nobody living raised them. I read them the way you read weather.'),
    dict(id='fold_trader', hamlet='stonefold', dx=6, dy=-.6, name='Asa Woolgood', role='Hamlet trader', color='#7a9a5a', trader=True,
         look=dict(skin='#edc5a1', hair='#6a4a2a', style='long', hat='none', hatColor='#7a9a5a'),
         dialogue='Salves, tonics and a kind word. Stonefold keeps its doors open to anyone who keeps the road.'),
    dict(id='salt_ragna', hamlet='saltby', dx=-4, dy=-2, name='Ragna Netmender', role='Headwoman of Saltby', color='#7fa8ba',
         look=dict(skin='#c99b7a', hair='#3a2e2a', style='long', hat='none', hatColor='#5f8aa0'),
         dialogue='The sea feeds Saltby and the slimes eat the nets. Pick a side, stranger.'),
    dict(id='salt_odd', hamlet='saltby', dx=4, dy=-1, name='Odd Longline', role='Fisher', color='#5f8aa0',
         look=dict(skin='#b98a6a', hair='#8a8a7a', style='short', hat='hood', hatColor='#44606e'),
         dialogue='Forty winters at sea, and the worst thing I ever met was on the beach. It has one claw bigger than my boat.'),
    dict(id='salt_trader', hamlet='saltby', dx=5, dy=4.6, name='Gudrun Saltcask', role='Hamlet trader', color='#5f8aa0', trader=True,
         look=dict(skin='#edc5a1', hair='#a05a2a', style='long', hat='none', hatColor='#5f8aa0'),
         dialogue='Salt fish, sea-air tonics, and whatever the tide brings in.'),
    dict(id='apple_maren', hamlet='applewick', dx=-2.5, dy=3, name='Maren Applewick', role='Orchard keeper', color='#c47a5a',
         look=dict(skin='#edc5a1', hair='#a0502a', style='long', hat='straw', hatColor='#d4b46a'),
         dialogue='My family planted these rows before Alderhaven had a wall. They will not fall to slimes while I can lift a rake.'),
    dict(id='apple_sten', hamlet='applewick', dx=2.5, dy=3, name='Sten Honeyhand', role='Beekeeper', color='#d4b43a',
         look=dict(skin='#d9b08c', hair='#5a4a3a', style='short', hat='hood', hatColor='#d4b46a'),
         dialogue='Do not swat. Never swat. There is something at the east hives that does not forgive it.'),
    dict(id='apple_trader', hamlet='applewick', dx=4, dy=-1.6, name='Liv Ciderfield', role='Hamlet trader', color='#b65b4a', trader=True,
         look=dict(skin='#edc5a1', hair='#c9a050', style='long', hat='none', hatColor='#b65b4a'),
         dialogue='Cider for the road, tonics for the bruises you pick up on it.'),
    dict(id='apple_lotta', hamlet='applewick', dx=1.5, dy=-7, name='Lotta Millward', role="Miller's daughter", color='#d8c8a0',
         look=dict(skin='#edc5a1', hair='#d8b060', style='long', hat='none', hatColor='#d8c8a0'),
         dialogue="Father's mill is up at the Meres and the lane is crawling. Walk with me and I will keep to the road. Stay close.",
         escort=dict(quest='apple_mill', **{'class': 'priest'}, female=True, hairColor=1, skin=0, level=4, speed=2.5,
                     route=[[345, 218], [345, 210], [350, 196], [352, 186], [352, 172], [350, 163]],
                     ambush=[dict(at=[351, 192], r=11, tag='apple_lotta#lane')])),
]

PLACES = [
    dict(id='fold_sisters', name='The Nine Sisters', x=58, y=222, r=7),
    dict(id='fold_watch_m', name='The Ring at Dusk', x=58, y=222, r=2.1, waves=[dict(at=1, tag='fold_watch_m#a'), dict(at=11, tag='fold_watch_m#b')]),
    dict(id='fold_hoar', name='The Hoar Oak', x=150, y=190, r=7),
    dict(id='salt_wreck', name='The Tidewrack', x=136, y=276, r=7),
    dict(id='apple_hives', name='The Wild Hives', x=384, y=216, r=6),
    dict(id='hollow_chapel', name='Hollowend Chapel', x=352, y=302, r=7),
    dict(id='wall_cairn', name='The Boundary Stone', x=124, y=146, r=5),
]

# Sleepers woken by a wave or an escort ambush
AMBUSH = [('pink', 54, 218, 'fold_watch_m#a'), ('pink', 62, 226, 'fold_watch_m#a'), ('yellow', 53, 226, 'fold_watch_m#b'), ('pink', 63, 218, 'fold_watch_m#b'),
          ('yellow', 357, 190, 'apple_lotta#lane'), ('pink', 345, 194, 'apple_lotta#lane')]


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
    # Alderhaven: the home fields, then the road out
    Q('fields_flour', 'Gel in the Flour', 'baker', 1, 10,
      'Slimes have got into the plots south of town and left their gel on everything Pip grows. Bring Pip four lumps of slime gel, so Pip can prove to the miller what spoiled the flour.',
      [('bring', 'slime_gel', 'Bring slime gel', 4)]),
    Q('wall_stone', 'The Boundary Stone', 'gatekeeper', 2, 20,
      "The Wallside Pasture runs right up to Skaldholm's wall. Captain Rowan wants to know the old boundary stone still stands. Follow the Skaldholm road north-west and find it at the west end of the pasture.",
      [('visit', 'wall_cairn', 'Find the Boundary Stone', 1), ('kill', 'blue', 'Defeat blue slimes in the pasture', 4)], requires='slime_patrol'),
    Q('hamlet_letters', 'Three Letters', 'guide', 2, 30,
      'Wren has letters for the three hamlets of Greenmeadow. Carry them to Hild at Stonefold on the Downs, Ragna at Saltby on the Strand and Maren at Applewick among the orchards. Each hamlet has a Travel Master: speak to them and you can fly back.',
      [('talk', 'fold_hild', 'Give Hild her letter at Stonefold', 1), ('talk', 'salt_ragna', 'Give Ragna her letter at Saltby', 1), ('talk', 'apple_maren', 'Give Maren her letter at Applewick', 1)],
      requires='slime_patrol'),
    # Stonefold, on the Downs
    Q('fold_strays', 'Salt Licks', 'fold_hild', 3, 25,
      'Pink slimes are crawling over the salt licks on the Downs and the ewes will not go near them. Clear six of them off the grazing.',
      [('kill', 'pink', 'Defeat pink slimes on the Downs', 6)]),
    Q('fold_sisters', 'The Nine Sisters', 'fold_torvald', 3, 25,
      'Torvald says the stones west of Stonefold have started to hum. Follow the Downs way to the ring and stand among the Nine Sisters, then come back and tell him what you felt.',
      [('visit', 'fold_sisters', 'Stand among the Nine Sisters', 1)]),
    Q('fold_watch', 'The Ring at Dusk', 'fold_torvald', 4, 35,
      'The humming draws things out of the grass. Stand in the middle of the ring for twenty seconds and keep the slimes from the stones.',
      [('hold', 'fold_watch_m', 'Hold the middle of the ring', 20)], requires='fold_sisters'),
    Q('fold_hoar', 'Under the Hoar Oak', 'fold_torvald', 3, 25,
      'The oldest tree in Greenmeadow stands in a glade in the Oldgrove. Torvald wants to know whether its bark is warm, as the stones are. Find the Hoar Oak.',
      [('visit', 'fold_hoar', 'Find the Hoar Oak in the Oldgrove', 1)], requires='fold_sisters'),
    Q('fold_tusker', 'Old Tusker', 'fold_hild', 5, 60,
      'A boar the size of a hay cart has taken eleven ewes. Its den is in a clearing in the north of the Oldgrove. Hild says nobody should go alone. Kill Old Tusker and she will sleep at night again.',
      [('kill', 'oldtusker', 'Defeat Old Tusker', 1)], requires='fold_strays', group=True, recommendedPlayers=2),
    # Saltby, on the Strand
    Q('salt_nets', 'Tarred and Mended', 'salt_ragna', 2, 20,
      'Blue slime gel makes a fair tar for torn nets. Bring Ragna five lumps from the Strand.',
      [('bring', 'blue_gel', 'Bring blue slime gel', 5)]),
    Q('salt_strand', 'Clean Sand', 'salt_ragna', 3, 25,
      'The boats cannot be hauled up while slimes foul the beach. Clear eight blue slimes from the Saltgrass Strand.',
      [('kill', 'blue', 'Defeat blue slimes on the Strand', 8)], requires='salt_nets'),
    Q('salt_wreck', 'The Tidewrack', 'salt_odd', 3, 25,
      'A trader ran aground at the west end of the Strand before Odd was born. Lately its cargo has been washing up again. Find the Tidewrack and see what is left.',
      [('visit', 'salt_wreck', 'Search the Tidewrack', 1)]),
    Q('salt_claw', 'One Claw Bigger', 'salt_odd', 5, 60,
      "Tidecrusher has come up out of the deep water and taken the east end of the beach. Odd has lost two boats and a good dog to it. Bring friends, go along the shore east of Saltby and put an end to it.",
      [('kill', 'tidecrusher', 'Defeat Tidecrusher', 1)], requires='salt_wreck', recommendedPlayers=3),
    # Applewick, in the orchards
    Q('apple_windfall', 'Windfall', 'apple_maren', 4, 35,
      'Yellow slimes roll down the rows and eat the windfall apples, and whatever they leave turns sour. Clear eight of them out of the orchards.',
      [('kill', 'yellow', 'Defeat yellow slimes in the orchards', 8)]),
    Q('apple_hives', 'Do Not Swat', 'apple_sten', 4, 35,
      "Sten's bees have left the home skeps for the wild hives at the east end of the orchards. Go and look at the hives, quietly, and tell him what you saw.",
      [('visit', 'apple_hives', 'Look at the wild hives', 1)]),
    Q('apple_mill', "The Miller's Lane", 'apple_maren', 5, 45,
      "Lotta must get to her father's watermill at the Three Meres, and the lane north of Applewick is not safe. Speak to Lotta at the north end of the village and walk with her. If she falls, or you do, start again.",
      [('escort', 'apple_lotta', 'Walk Lotta to the watermill', 1)], requires='apple_windfall'),
    Q('hollow_chapel', 'The Chapel at Hollowend', 'apple_sten', 5, 45,
      'South of the orchards the old wood closes in round a chapel nobody remembers building. The beetles have come down from the Scarp and settled there. Reach the chapel, and defeat three Ironhide Beetles on the way.',
      [('visit', 'hollow_chapel', 'Reach Hollowend Chapel', 1), ('kill', 'beetle', 'Defeat Ironhide Beetles', 3)], requires='apple_hives'),
]

REWRITES = {
    'ironhide_hunt': 'Ironhide Beetles shelter among the boulders of the Ironhide Scarp, north of town under the Crags. Defeat two of these charging beasts and report back to Bram.',
    'meadow_bounty': 'Linden pays reliable adventurers to keep the Great Road open. Defeat eight enemies of any kind in Greenmeadow and return to the market. This bounty can be taken again.',
}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, hamlets):
    alder = next(n for n in world['npcs'] if n['id'] == 'travel_alderhaven')
    potion = next(n for n in world['npcs'] if n['id'] == 'apothecary')['offers']
    blessing = next(n for n in world['npcs'] if n['id'] == 'healer')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(blessing + potion) if trader else [], buys=trader, look=s['look'])
        if 'escort' in s:
            n['escort'] = s['escort']
        if n['id'] == 'fold_hild':
            n['offers'] = mercenary_offers()
        out.append(n)
    spots = {'stonefold': (-1, -7), 'saltby': (-2, -5), 'applewick': (-4, -6.5)}
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(alder)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=['travel_alderhaven'])
        out.append(t)
        if t['id'] not in alder['travelLinks']:
            alder['travelLinks'].append(t['id'])
    # every hub has a mailbox (scripts/mailboxes.py ran on the old square, before the hamlets exist)
    box = next(n for n in world['npcs'] if n['id'] == 'mailbox_0_alderhaven')
    for key, (dx, dy) in {'stonefold': (4, 2.5), 'saltby': (-1, 3), 'applewick': (-2, 6)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_0_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(world, hamlets, path):
    """The directory is written by mailboxes.py on the old square, where the hamlets do not exist yet."""
    directory = [d for d in json.loads(path.read_text()) if not (d['zone'] == 0 and d['hub'] in {h['name'] for h in hamlets.values()})]
    for key, h in hamlets.items():
        box = next(n for n in world['npcs'] if n['id'] == f'mailbox_0_{key}')
        master = next(n for n in world['npcs'] if n['id'] == f'travel_{key}')
        directory.append(dict(id=box['id'], zone=0, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=master['x'], y=master['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(world, hamlets):
    # idempotent, so `plan` also works on a map that already carries the design
    new_npcs = people(world, hamlets)
    ids = {n['id'] for n in new_npcs}
    world['npcs'] = [n for n in world['npcs'] if n['id'] not in ids] + new_npcs
    ids = {p['id'] for p in PLACES}
    world['places'] = [p for p in world['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    ids = {q['id'] for q in QUESTS}
    world['quests'] = [q for q in world['quests'] if q['id'] not in ids]
    world['camps'] = camps(hamlets)
    assert not {q['id'] for q in world['quests']} & {q['id'] for q in QUESTS}, 'quest id clash'
    for q in world['quests']:
        if q['id'] in REWRITES:
            q['description'] = REWRITES[q['id']]
    at = next(i for i, q in enumerate(world['quests']) if q['id'].startswith('arena_'))
    world['quests'][at:at] = copy.deepcopy(QUESTS)
    assert all(len('quest:accept:' + q['id']) <= 32 for q in QUESTS)
