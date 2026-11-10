"""Bifrost Reach's outposts, people, places and quests. Data for scripts/bifrost_design.py (shaped coordinates, zone 7).

Every old `sky_*`, `span_*` and `es_*` quest id stays (saved progress, tests, quest_gear_rewards): text is rewritten only where the geography
changed. Fourteen quests are new, with three new outposts and three new elites. Owner rule for elites: three per zone, two with a quest, one
without: `skoll` and `shardking` (quests) and `heimdallr` (none). New ids and people start `sky_` and stay within 19 characters (the accept
string is capped at 32). Levels 30-35, rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.

Geography (the painted atlas, north up): Heimdall's Perch on the central island; the Stormrift pad south-west of it with Windward Meadow
rising to its north-west; the pylon pad due north across a long bridge; the Hall of the Fallen north of that; the Roc's Eyrie north-east; the
Shardfields south; the Stormcrown south-east, with the Rán's Deep pad on its north side and the Nacrehold pad on its south-east tip.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(30, 36)}
GOLD = {30: 850, 31: 950, 32: 1050, 33: 1150, 34: 1300, 35: 1450}

# the outposts: plaza and half width/height of the sanctuary rectangle (sky islands: x, y in the shaped frame)
HAMLETS = {
    'roost':   dict(name='Windward Roost', x=112, y=124, hw=14, hh=11),
    'station': dict(name='Stormcrown Station', x=296, y=254, hw=14, hh=11),
    'landing': dict(name='Eyrie Landing', x=256, y=100, hw=14, hh=11),
}

# elite kind, a hint for where it stands (the design moves it to the best clear spot on that island), island
ELITES = [('skoll', 'nw'), ('shardking', 'south'), ('heimdallr', 'ne')]

HUT = dict(r=0, width=3.4, depth=3.2)
DRESSING = {
    'roost': [
        ('house', -9, -6, dict(HUT, label='Kennel Hall', color='#8aa0c0')), ('house', 9, -7, dict(HUT, label='Windcatcher Loft', color='#9ab0c8')),
        ('tent', 10, 6, dict(r=1.5, width=3, depth=2.4, color='#7a90b0', label='Watch')),
        ('stall', -5, 3, dict(r=0, width=1.8, depth=1.2, color='#c4a060', label='Fangs & Cord')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Windward Roost')),
        ('campfire', 3, 3, dict(r=.65)), ('bench', 5, -4, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -2, 0, dict(r=.4)), ('lamp', -4, -3, dict(r=.18)), ('lamp', 6, 1, dict(r=.18)),
    ],
    'station': [
        ('house', -9, -6, dict(HUT, label='Rod Hall', color='#7a7ab0')), ('house', 9, -6, dict(HUT, label='Ray Loft', color='#8a8ac0')),
        ('tent', -10, 6, dict(r=1.5, width=3, depth=2.4, color='#6a6aa0', label='Watch')),
        ('stall', 8, 5.5, dict(r=0, width=1.8, depth=1.2, color='#c4a060', label='Wings & Wire')),
        ('noticeboard', -2, -6, dict(r=.4, width=1.3, depth=.4, label='Stormcrown Station')),
        ('campfire', 3, 3, dict(r=.65)), ('bench', 5, -4, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -2, 0, dict(r=.4)), ('lamp', -5, 2, dict(r=.18)), ('lamp', 7, -1, dict(r=.18)),
    ],
    'landing': [
        ('house', -9, -6, dict(HUT, label='Landing Hall', color='#9a8ab0')), ('house', 9, 6, dict(HUT, label='Quill Store', color='#a89ac0')),
        ('tent', 10, -6, dict(r=1.5, width=3, depth=2.4, color='#8a7aa8', label='Lookout')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#c4a060', label='Quills & Fletching')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Eyrie Landing')),
        ('campfire', 3, 3, dict(r=.65)), ('brazier', -2, -1, dict(r=.4)), ('brazier', 6, 1, dict(r=.4)),
        ('lamp', -4, 1, dict(r=.18)), ('lamp', 5, -3, dict(r=.18)),
    ],
}

NPCS = [
    dict(id='sky_wr_vigdis', hamlet='roost', dx=-3, dy=-1, name='Kennel-Warden Vigdis Hounddaughter', role='Kennel-warden', color='#8aa0c8',
         look=dict(skin='#edc5a1', hair='#a8683a', style='long', hat='none', hatColor='#8aa0c8'),
         dialogue='Skadi taught me the pack and the pack taught me the wind. Every hound on this meadow came out of my kennel, and one of them came out of it bigger than the rest. Sköll hunts the meadow now, and the pack runs where he runs.'),
    dict(id='sky_wr_leif', hamlet='roost', dx=5, dy=3, name='Leif Windcatcher', role='Beacon-keeper', color='#9ab0c8',
         look=dict(skin='#d9b08c', hair='#7a7a7a', style='short', hat='hood', hatColor='#5a7090'),
         dialogue='I hang cloth on poles and the wind tells me what it is thinking. Lately it has been thinking about hounds. The beacon on the western rise is how this roost sees them coming, and somebody has to stand by it when it burns.'),
    dict(id='sky_wr_trader', hamlet='roost', dx=-5, dy=4.6, name='Asa Fangmonger', role='Outpost trader', color='#c4a060', trader=True,
         look=dict(skin='#c99b7a', hair='#2a2a32', style='short', hat='none', hatColor='#c4a060'),
         dialogue='Fangs, cord, stew and tonics. A galehound fang is the sharpest thing in the Reach that nobody has bothered to sharpen, and I pay well for them.'),
    dict(id='sky_ss_ingrid', hamlet='station', dx=-3, dy=-1, name='Rod-Warden Ingrid Lightningwife', role='Rod-warden', color='#7a7ab0',
         look=dict(skin='#edc5a1', hair='#cfcfcf', style='long', hat='hood', hatColor='#5a5a90'),
         dialogue='Every bolt that rises off the storm finds my rods first, and every skyray on this island is trying to eat the bolt before it gets there. I did not choose this posting. I am, however, very good at it.'),
    dict(id='sky_ss_bjorn', hamlet='station', dx=5, dy=3, name='Bjorn Stormtally', role='Tally-keeper', color='#8a8ac0',
         look=dict(skin='#c99b7a', hair='#5a3a2a', style='short', hat='none', hatColor='#8a8ac0'),
         dialogue='Valkyries count the dead. I count the storm: how many bolts, how many skyrays, how many times the pylon hums. The numbers have been climbing since the bridge broke, and I do not enjoy where they are going.'),
    dict(id='sky_ss_trader', hamlet='station', dx=-5, dy=6.2, name='Yrsa Wingmonger', role='Outpost trader', color='#a0a0d0', trader=True,
         look=dict(skin='#edc5a1', hair='#8a4a2a', style='long', hat='none', hatColor='#a0a0d0'),
         dialogue='Stormray wings by the dozen, copper wire, stew and a tonic or two. A wing is mostly lightning that has forgotten it was ever a creature. It makes very good kites.'),
    dict(id='sky_el_gunnar', hamlet='landing', dx=-3, dy=-1, name='Landing-Warden Gunnar Nestbreaker', role='Landing-warden', color='#9a8ab0',
         look=dict(skin='#d9b08c', hair='#b89a6a', style='short', hat='hood', hatColor='#6a5a90'),
         dialogue='This is the last landing before the Eyrie. Past the ridge the thunderrocs nest, and a thunderroc does not like to be looked at from underneath. I hold the landing so the Perch does not have to hold the whole Reach.'),
    dict(id='sky_el_hallveig', hamlet='landing', dx=5, dy=3, name='Hallveig Quillsinger', role='Rod-singer', color='#a89ac0',
         look=dict(skin='#edc5a1', hair='#2a2a3a', style='long', hat='hood', hatColor='#7a6aa0'),
         dialogue='A roc quill hums when it is about to be struck, and I have learned to sing the note back. Stand by the rod at the nest while I sing, and the storm will come for you instead of for the landing.'),
    dict(id='sky_el_trader', hamlet='landing', dx=-6, dy=5.6, name='Ketil Featherfence', role='Outpost trader', color='#8a7aa8', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#8a7aa8'),
         dialogue='Quills, fletching, stew and tonics. Everything on my table fell out of the sky, and I have only been struck twice.'),
]

PADS = [  # (id, name, which pad) places for the updraft ledger: the design puts each in the middle of its pad
    ('sky_pad_stormrift', 'the Stormrift Pad', 'stormrift'),
    ('sky_pad_maelstrom', 'the Maelstrom Pad', 'maelstrom'),
    ('sky_pad_nacre', 'the Nacrehold Pad', 'nacre'),
    ('sky_pad_crags', 'the Cragsfall Updraft', 'crags'),
]

# name, hint island, hint (x, y), radius, hold waves
PLACES = [
    dict(id='sky_shardfield', name='the Shardfield', island='south', hint=(232, 306), r=4.5),
    dict(id='sky_tally', name='the Tally Stones', island='se', hint=(262, 270), r=4.0),
    dict(id='sky_bell', name='the Silent Bell', island='north', hint=(150, 72), r=4.0),
    dict(id='sky_beacon_m', name='the Western Beacon', island='nw', hint=(62, 118), r=2.1, hold=True),
    dict(id='sky_rod_m', name='the Station Rod', island='se', hint=(322, 252), r=2.1, hold=True),
    dict(id='sky_nest_m', name='the Nest Rod', island='ne', hint=(266, 66), r=2.1, hold=True),
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
    # Heimdall's Perch
    Q('sky_h_shardfield', 'A Walk in the Shardfield', 'sky_brokk', 31,
      'The prism golems have gathered in the Shardfield, the glass-strewn island south of the Perch across the long bridge. Walk down to the Shardfield and defeat four of them there, then tell Brokk what the glass looks like in daylight.',
      [('visit', 'sky_shardfield', 'Reach the Shardfield', 1), ('kill', 'prismgolem', 'Defeat Prism Golems', 4)], requires='sky_welcome'),
    Q('sky_h_shardking', 'The Shard-King', 'sky_brokk', 33,
      'A golem the size of a house has taken the Shardfield for its own, built from every shard the others dropped. Brokk calls it the Shard-King and wants it broken before it learns to walk to the Perch. Defeat it.',
      [('kill', 'shardking', 'Defeat the Shard-King', 1)], requires='sky_shards', recommendedPlayers=3),
    Q('sky_h_ledger', 'The Updraft Ledger', 'sky_warden', 32,
      'Four winds carry heroes in and out of the Reach: the Stormrift to the Wyrdwood, the Maelstrom to Rán\'s Deep, the Nacrehold pad in the south-east and the Cragsfall updraft at the end of the Shardfield. Sigrun keeps a ledger of every pad and wants each one walked. Stand on all four.',
      [('visit', 'sky_pad_stormrift', 'Stand on the Stormrift Pad', 1), ('visit', 'sky_pad_crags', 'Stand on the Cragsfall Updraft', 1),
       ('visit', 'sky_pad_maelstrom', 'Stand on the Maelstrom Pad', 1), ('visit', 'sky_pad_nacre', 'Stand on the Nacrehold Pad', 1)], requires='sky_welcome'),
    # Windward Roost, on Windward Meadow
    Q('sky_wr_pelts', 'Fangs for the Roost', 'sky_wr_trader', 30,
      'Asa threads galehound fangs onto cord and sells the cord to every post in the Reach. The Roost is short, and the meadow is full. Bring her six Gale Fangs.',
      [('bring', 'gale_fang', 'Bring Gale Fangs', 6)], requires='sky_hounds'),
    Q('sky_wr_alpha', 'The Alpha of the Meadow', 'sky_wr_vigdis', 31,
      'The pack runs where Sköll runs, and Sköll has begun to run at the Roost. Vigdis raised him from a pup and will not do it herself. Find the Gale-Alpha on the meadow, away from the roads, and put him down.',
      [('kill', 'skoll', 'Defeat Sköll the Gale-Alpha', 1)], requires='sky_hounds', recommendedPlayers=3),
    Q('sky_wr_beacon', 'Light the Western Beacon', 'sky_wr_leif', 32,
      'West of the Roost the old beacon still stands, and when it burns the whole meadow sees it. Stand in the circle beside it for twenty seconds while Leif lights it, and keep the hounds off him.',
      [('hold', 'sky_beacon_m', 'Hold the Western Beacon', 20)], requires='sky_wr_alpha'),
    # Stormcrown Station, on the south-eastern island
    Q('sky_ss_rays', 'Rays Over the Station', 'sky_ss_ingrid', 32,
      'The skyrays have discovered the Station\'s rods and think of them as a larder. Defeat eight of them on the Stormcrown before they strip the wire.',
      [('kill', 'skyray', 'Defeat Skyrays over the Stormcrown', 8)], requires='sky_welcome'),
    Q('sky_ss_wings', 'Wings for the Wire', 'sky_ss_trader', 33,
      'Yrsa dries stormray wings over the Station fire and sells them to anyone with a kite. Bring her five.',
      [('bring', 'stormray_wing', 'Bring Stormray Wings', 5)], requires='sky_ss_rays'),
    Q('sky_ss_tally', 'The Tally Stones', 'sky_ss_bjorn', 33,
      'Bjorn counts the storm on a ring of stones west of the Station. Walk to the Tally Stones, read how high the count has run, and defeat three skyrays on the way.',
      [('visit', 'sky_tally', 'Reach the Tally Stones', 1), ('kill', 'skyray', 'Defeat Skyrays over the Stormcrown', 3)], requires='sky_ss_rays'),
    Q('sky_ss_rod', 'Hold the Station Rod', 'sky_ss_ingrid', 34,
      'Ingrid has to ground the big rod at the island\'s eastern rim before the next surge. Stand in the circle beside it for twenty seconds while she works, and let the skyrays come to you.',
      [('hold', 'sky_rod_m', 'Hold the Station Rod', 20)], requires='sky_ss_tally'),
    # The Hall of the Fallen, on the island north of the pylon
    Q('sky_hl_bell', 'The Silent Bell', 'sky_thorgrim', 34,
      'In the Hall of the Fallen hangs a bell that has not rung since the bridge broke, and Thorgrim believes the dead will rest when it does. Walk to the Silent Bell, past the hall gate, and put four einherjar to rest on the way.',
      [('visit', 'sky_bell', 'Reach the Silent Bell', 1), ('kill', 'einherjar', 'Defeat Hollow Einherjar', 4)], requires='sky_hallgate'),
    # Eyrie Landing, on the north-eastern island
    Q('sky_el_nests', 'Nests Above the Landing', 'sky_el_gunnar', 35,
      'The thunderrocs nest on the ridge above the Landing and dive at anything that moves. Defeat six of them and the Landing can breathe.',
      [('kill', 'thunderroc', 'Defeat Thunderrocs', 6)], requires='sky_rocs'),
    Q('sky_el_quills', 'Quills for the Fletcher', 'sky_el_trader', 35,
      'Ketil fletches arrows with thunderroc quills: nothing else flies so far or so loud. Bring him five.',
      [('bring', 'thunderroc_quill', 'Bring Thunderroc Quills', 5)], requires='sky_rocs'),
    Q('sky_el_rod', 'Hold the Nest Rod', 'sky_el_hallveig', 35,
      'Hallveig wants the rod at the edge of the great nest struck by lightning on purpose, once, so the storm spends itself there. Stand in the circle beside it for twenty seconds while she sings, and keep the thunderrocs off her.',
      [('hold', 'sky_nest_m', 'Hold the Nest Rod', 20)], requires='sky_el_nests'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'sky_hounds': dict(description='On Windward Meadow, the big island north-west of the Perch, the galehounds have gone wild. Cross the little bridge north of the Stormrift Pad (or the long one from the pylon), defeat six of them and tell Skadi.'),
    'sky_cairn': dict(description='The old Windcairn on the west of Windward Meadow is how the Perch used to hear the hounds. Walk to the cairn, light it, and clear three galehounds off the meadow while you are there.'),
    'sky_ward_wind': dict(description='In the north-west of Windward Meadow stands the first Valkyrie ward. Veleda says it will take sixty seconds of a hero standing in the circle to re-light it, and that the storm will send hounds to stop you. '
                                       'Walk to the ward, stand inside the circle and hold it. Leaving the circle only pauses the count; falling loses it all.'),
    'sky_golems': dict(description='The Shardfields south of the Perch are crawling with prism golems, pieces of the broken bridge that have decided to be people. Take the long bridge south and defeat six of them.'),
    'sky_spire': dict(description='On the Shardfields stands the Lightning Spire, where the storm rises. Walk to the spire, read what the lightning is doing, and clear three prism golems from the fields on the way.'),
    'sky_rays': dict(description='The skyrays of the Stormcrown, the island south-east of the Perch, feed on the rising lightning and shoot it back. Cross the painted bridge from the Perch and defeat six of them.'),
    'sky_pylon': dict(description='In the heart of the Reach, where the bridges meet, stands the last pylon of the old Bifrost. Walk to it, defeat two skyrays that circle it, then tell Sigrun if it still hums.'),
    'sky_dead': dict(description='North of the pylon, across the bridge, lies the Hall of the Fallen. The einherjar there have forgotten they are dead. Defeat six of them.'),
    'sky_hallgate': dict(description='The Hall Gate on the south-west side of the Hall of the Fallen has not opened since the bridge broke. Walk to it, and put three einherjar to rest on the way.'),
    'sky_ward_vigil': dict(description='In the Hall of the Fallen stands the second ward: the vigil lamp. Stand inside its circle for seventy-five seconds and the dead will know they are remembered. '
                                       'They will not take it quietly: first the einherjar, then the skyrays that nest in the rafters. Leaving the circle pauses the count; falling loses it all. Thorgrim gives a guaranteed blue Amber Ring.'),
    'sky_rocs': dict(description='Across the long ribbon bridge from the Hall of the Fallen, or along the east bar from the pylon, lies the Roc\'s Eyrie, and the thunderrocs there dive on anything that crosses. Defeat five of them.'),
}

NPC_UPDATES = {
    'sky_brokk': 'Every dwarf dreams of Bifrost metal, and here it lies in the grass, falling apart and getting up to hit people. '
                 'The prism golems on the Shardfields, the long way south, are the bridge itself, walking, and something there has been collecting the pieces. Break them, bring me the shards, and I will tell you what a rainbow weighs.',
    'sky_veleda': 'The lightning here does not fall; it rises, and it has a pattern. Six wards and rods the Valkyries built hold the storm down, and the storm-spawn have been unpicking them. '
                  'A ward holds as long as someone stands in it and means it. Stand inside the circle and do not leave: the storm will send everything it has, and the circle is the only place the storm cannot go.',
    'sky_skadi': 'They were my hounds once. I raised them on Windward Meadow, the big island north-west of here, and they hunted the wind itself, and then the Bifrost broke and the storm got into them. '
                 'Now the galehounds hunt anything that moves, and they move faster than anything that has ever hunted them. Thin the pack and bring me their fangs: I would rather remember them as they were.',
}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    master = next(n for n in zone['npcs'] if n['id'] == 'travel_perch')
    healer = next(n for n in zone['npcs'] if n['id'] == 'sky_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'sky_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        out.append(dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                        offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look']))
    links = list(master['travelLinks'])
    keys = list(hamlets)
    for key in keys:
        h = hamlets[key]
        t = copy.deepcopy(master)
        t.update(id=f'travel_{key}', x=h['x'] - 1, y=h['y'] + 3.5, travelStop=h['name'], travelLinks=['travel_perch'] + [f'travel_{k}' for k in keys if k != key])
        out.append(t)
    box = next(n for n in zone['npcs'] if n['id'].startswith('mailbox_7_'))
    for key, (dx, dy) in {'roost': (2, 1), 'station': (3, 1), 'landing': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_7_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    master['travelLinks'] = links + [f'travel_{k}' for k in keys]
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Bifrost entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 7]
    names = {'travel_perch': "Heimdall's Perch"}
    for key, h in hamlets.items():
        names[f'travel_{key}'] = h['name']
    for master, hub in names.items():
        key = master.split('travel_')[1]
        box = next(n for n in zone['npcs'] if n['id'] == ('mailbox_7_heimdall_s_perch' if key == 'perch' else f'mailbox_7_{key}'))
        m = next(n for n in zone['npcs'] if n['id'] == master)
        directory.append(dict(id=box['id'], zone=7, hub=hub, x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(zone, hamlets, places):
    """Idempotent, so `plan` also works on a map that already carries the design. `places` are the finished place records (new ones)."""
    new_npcs = people(zone, hamlets)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        if n['id'] in NPC_UPDATES:
            n['dialogue'] = NPC_UPDATES[n['id']]
    ids = {p['id'] for p in places}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in places]
    ids = {q['id'] for q in QUESTS}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids]
    zone['camps'] = camps(hamlets)
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
