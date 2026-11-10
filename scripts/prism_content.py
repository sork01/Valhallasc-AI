"""The Prismwaste's outposts, people, quests, places and elites. Data for scripts/prism_design.py (shaped coordinates, zone 14).

Owner request 2026-11-08: "for pilot. reshape prism waste and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against
Astralhollow (its whole west side) and the Obsidian Orrery (the short south-west corner), keep the Mirror Queen and the Sunshard and add one new elite with no
quest, three new outposts. Stormglass and Cairnspine stay walk-in gates. Every old `prism_*`, `arena_prism_*`, `es_11`/`es_go_11` and `banker` id stays (saved
progress, tests, quest_gear_rewards): texts are rewritten only where the geography changed. Fourteen quests are new. New ids and people start `prism_` and
stay within 19 characters (the accept string is capped at 32). Levels 45-50, rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in
scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(45, 51)}
GOLD = {45: 1100, 46: 1250, 47: 1400, 48: 1600, 49: 1800, 50: 2100}

# the outposts: plaza, half width/height of the sanctuary rectangle. Nothing art-less may stand within 20 tiles of the Astralhollow or Orrery border.
HAMLETS = {
    'mirrorfall': dict(name='Mirrorfall', x=106, y=98, hw=12, hh=11),
    'whitesun':   dict(name='Whitesun Post', x=150, y=70, hw=12, hh=11),
    'cairnfoot':  dict(name='Cairnfoot', x=198, y=162, hw=12, hh=11),
}

# kind, x, y (the three elites: the Mirror Queen and the Sunshard have a quest, the Shatterhorn none; awareness is the 4th value of the server's attack profile)
ELITES = [('mirrorqueen', 50, 84), ('sunshard', 92, 46), ('shatterhorn', 238, 212)]
ELITE_LEVEL = {'mirrorqueen': 49, 'sunshard': 50, 'shatterhorn': 48}
AWARENESS = {'mirrorqueen': 10., 'sunshard': 13., 'shatterhorn': 11.}

PAVILION = dict(r=2.0, width=5, depth=4)

DRESSING = {
    'mirrorfall': [
        ('shade_tent', 0, -6.5, dict(PAVILION)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#a8809a', label='Court Watch')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#e0b48a', label='Brinecask')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Mirrorfall')),
        ('lens_pillar', -8, -1, dict(r=.5)), ('lens_pillar', 9, -1, dict(r=.5)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -3, -2, dict(r=.4)),
    ],
    'whitesun': [
        ('shade_tent', 0, -6.5, dict(PAVILION)),
        ('tent', -9, 5, dict(r=1.5, width=3, depth=2.4, color='#c8a888', label='Beacon Watch')),
        ('stall', 7, 4, dict(r=0, width=1.8, depth=1.2, color='#f0d8a0', label='Saltwick')),
        ('noticeboard', -5, -7, dict(r=.4, width=1.3, depth=.4, label='Whitesun Post')),
        ('lens_pillar', -8, -1, dict(r=.5)), ('lens_pillar', 9, -1, dict(r=.5)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, 0, dict(r=.4)), ('brazier', 6, -2, dict(r=.4)),
    ],
    'cairnfoot': [
        ('shade_tent', 0, -6.5, dict(PAVILION)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#8c8a9a', label='Cairn Watch')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#b8a090', label='Cragsalt')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Cairnfoot')),
        ('lens_pillar', -8, -1, dict(r=.5)), ('lens_pillar', 9, -1, dict(r=.5)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, -1, dict(r=.4)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
}

NPCS = [
    dict(id='prism_mf_ilsa', hamlet='mirrorfall', dx=-3, dy=-1, name='Court-Warden Ilsa Mirrorwell', role='Court warden', color='#d8a0c8',
         look=dict(skin='#e0bca0', hair='#d8c8e0', style='long', hat='hood', hatColor='#7a5a8a'),
         dialogue='The Mirror Court lies west of here, between the great crystals, and every pane in it shows a queen who is not standing there. I keep the watch so someone counts the reflections that walk out of it.'),
    dict(id='prism_mf_dov', hamlet='mirrorfall', dx=5, dy=3, name='Dov Glintwright', role='Lens-grinder', color='#c8a8b8',
         look=dict(skin='#c99b7a', hair='#3a2a3a', style='short', hat='none', hatColor='#6a5a6a'),
         dialogue='A scarab carapace grinds to a better lens than any quartz. Bring me a few and I will give the watch eyes that do not lie.'),
    dict(id='prism_mf_trader', hamlet='mirrorfall', dx=-6, dy=4.6, name='Hester Brinecask', role='Outpost trader', color='#e0b48a', trader=True,
         look=dict(skin='#edc5a1', hair='#a8683a', style='long', hat='none', hatColor='#e0b48a'),
         dialogue='Stew, tonics and a mug of something warm for the ones who stand watch over the mirrors. Everything hot is sold at cost, because the glass is cold enough.'),
    dict(id='prism_ws_marek', hamlet='whitesun', dx=-3, dy=-1, name='Beacon-Keeper Marek Dawnholt', role='Beacon keeper', color='#f0d890',
         look=dict(skin='#d9b08c', hair='#e8e0c8', style='short', hat='hood', hatColor='#a88a5a'),
         dialogue='Below the Broken Crown the Sunshard burns the sky white, and the sentinels still stand their watch in its light. I keep the beacon lit so the post can be found, and I wear dark glass when I look north.'),
    dict(id='prism_ws_ottilie', hamlet='whitesun', dx=5, dy=3, name='Ottilie Sunveil', role='Veil-weaver', color='#e8c0a0',
         look=dict(skin='#c99b7a', hair='#7a3a2a', style='long', hat='none', hatColor='#b08a6a'),
         dialogue='A sentinel\'s heart still glows after it falls, and I weave the glow into veils that keep the white sun off the eyes. Bring me a few and the post can look north without squinting.'),
    dict(id='prism_ws_trader', hamlet='whitesun', dx=-5, dy=6.2, name='Bram Saltwick', role='Outpost trader', color='#f0d8a0', trader=True,
         look=dict(skin='#edc5a1', hair='#5a4a2a', style='long', hat='none', hatColor='#f0d8a0'),
         dialogue='Bread, tonics and stew for the ones who stand under the crown and squint. If the soup tastes of salt, that is the waste, not the cook.'),
    dict(id='prism_cf_runa', hamlet='cairnfoot', dx=-3, dy=-1, name='Cairn-Warden Runa Greyflint', role='Cairn warden', color='#a8a8c8',
         look=dict(skin='#edc5a1', hair='#cfcfe8', style='long', hat='hood', hatColor='#5a5a7a'),
         dialogue='The mountains come down to the waste here, and the road east goes through the Cairnspine. The harriers nest in the cairns and hunt the east spires, and a horned thing of glass roams the Sunspire Reaches below them. I would like the road to stay a road.'),
    dict(id='prism_cf_teo', hamlet='cairnfoot', dx=5, dy=3, name='Teo Fangmaker', role='Fang-carver', color='#a89888',
         look=dict(skin='#c99b7a', hair='#2a2a3a', style='short', hat='hood', hatColor='#4a4a5a'),
         dialogue='A mirage fang holds an edge that stone will not, and a carved fang makes a fine cairn marker. Bring me a handful and the road will have its markers back.'),
    dict(id='prism_cf_trader', hamlet='cairnfoot', dx=-6, dy=5.6, name='Odile Cragsalt', role='Outpost trader', color='#b8a090', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#b8a090'),
         dialogue='Thread, wicks and stew. If a spire falls near you, do not look at it: look at me, and I will sell you a tonic.'),
]

PLACES = [
    dict(id='prism_flats', name='The Salt Flats', x=70, y=226, r=6),
    dict(id='prism_court', name='The Mirror Court', x=72, y=88, r=6),
    dict(id='prism_crown', name='The Broken Crown', x=118, y=30, r=5),
    dict(id='prism_watch', name='The Broken Watch', x=184, y=100, r=6),
    dict(id='prism_spires', name='The Sunspire Reaches', x=230, y=196, r=6),
    dict(id='prism_brine', name='The Brine Road', x=172, y=242, r=6),
    dict(id='prism_awning_m', name='The Awning Circle', x=98, y=146, r=2.1, waves=[dict(at=1, tag='prism_awning_m#a'), dict(at=11, tag='prism_awning_m#b')]),
    dict(id='prism_glass_m', name='The Court Mirror', x=88, y=74, r=2.1, waves=[dict(at=1, tag='prism_glass_m#a'), dict(at=11, tag='prism_glass_m#b')]),
    dict(id='prism_beacon_m', name='The Beacon Circle', x=142, y=44, r=2.1, waves=[dict(at=1, tag='prism_beacon_m#a'), dict(at=11, tag='prism_beacon_m#b')]),
    dict(id='prism_cairn_m', name='The Cairn Circle', x=200, y=142, r=2.1, waves=[dict(at=1, tag='prism_cairn_m#a'), dict(at=11, tag='prism_cairn_m#b')]),
]

# Sleepers woken by a hold wave: four or two-and-two a wave, round the circle
AMBUSH = [
    ('miragejackal', 92, 140, 'prism_awning_m#a'), ('miragejackal', 104, 152, 'prism_awning_m#a'), ('miragejackal', 92, 152, 'prism_awning_m#b'), ('miragejackal', 104, 140, 'prism_awning_m#b'),
    ('shardscarab', 82, 68, 'prism_glass_m#a'), ('shardscarab', 94, 80, 'prism_glass_m#a'), ('shardscarab', 82, 80, 'prism_glass_m#b'), ('shardscarab', 94, 68, 'prism_glass_m#b'),
    ('prismsentinel', 136, 38, 'prism_beacon_m#a'), ('prismsentinel', 148, 50, 'prism_beacon_m#a'), ('prismsentinel', 136, 50, 'prism_beacon_m#b'), ('prismsentinel', 148, 38, 'prism_beacon_m#b'),
    ('glassharrier', 194, 136, 'prism_cairn_m#a'), ('glassharrier', 206, 148, 'prism_cairn_m#a'), ('glassharrier', 194, 148, 'prism_cairn_m#b'), ('glassharrier', 206, 136, 'prism_cairn_m#b'),
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
    # the Last Shade, in the west
    Q('prism_h_hold', 'Raise the Awning', 'prism_keeper', 45,
      'The refuge\'s awning slips whenever the jackals gather, and when it falls the Last Shade is a patch of bare glass. Stand in the circle north of the refuge for twenty seconds while Mara hauls it back up, and let nothing reach her.',
      [('hold', 'prism_awning_m', 'Raise the Awning', 20)], requires='prism_welcome'),
    Q('prism_h_rounds', 'The Watchers of the Waste', 'prism_scholar', 50,
      'Three outposts watch the waste beyond the Last Shade: Mirrorfall under the Mirror Court in the north-west, Whitesun Post below the Broken Crown in the north, Cairnfoot by the mountains in the east. Asha wants their keepers told that the Last Shade still stands. Speak with Ilsa, Marek and Runa, and use their Travel Masters if the road is long.',
      [('talk', 'prism_mf_ilsa', 'Speak with Court-Warden Ilsa Mirrorwell at Mirrorfall', 1), ('talk', 'prism_ws_marek', 'Speak with Beacon-Keeper Marek Dawnholt at Whitesun Post', 1),
       ('talk', 'prism_cf_runa', 'Speak with Cairn-Warden Runa Greyflint at Cairnfoot', 1)], requires='prism_sentinels'),
    # Mirrorfall, under the Mirror Court
    Q('prism_mf_walk', 'Up to the Mirror Court', 'prism_mf_ilsa', 46,
      'The Mirror Court lies west of Mirrorfall, between the great crystals, where every pane shows a queen who is not there. Ilsa wants a count of what lives in it. Walk up to the Mirror Court and defeat four Shard Scarabs on the way.',
      [('visit', 'prism_court', 'Reach the Mirror Court', 1), ('kill', 'shardscarab', 'Defeat Shard Scarabs on the way', 4)], requires='prism_scarabs'),
    Q('prism_mf_lenses', 'Carapace for the Grinder', 'prism_mf_dov', 46,
      'Dov grinds scarab carapace into lenses that show the watch what is really standing in the court. Bring him four Shard Carapaces.',
      [('bring', 'shard_carapace', 'Bring Shard Carapaces', 4)], requires='prism_mf_walk'),
    Q('prism_mf_hold', 'Hold the Court Mirror', 'prism_mf_ilsa', 47,
      'The tall mirror on the road above Mirrorfall flares whenever the scarabs gather, and then every scarab in the court comes to answer it. Stand in the circle beside it for twenty seconds while Ilsa covers the glass, and keep the court off her.',
      [('hold', 'prism_glass_m', 'Hold the Court Mirror', 20)], requires='prism_mf_walk'),
    Q('prism_mf_glass', 'Down from the Spires', 'prism_mf_ilsa', 47,
      'Glass harriers roost on the great crystals above the court and dive at the watch whenever the light turns. Defeat five Glass Harriers on the north-western spires.',
      [('kill', 'glassharrier', 'Defeat Glass Harriers over the Mirror Court', 5)], requires='prism_mf_hold'),
    # Whitesun Post, below the Broken Crown
    Q('prism_ws_walk', 'Under the Broken Crown', 'prism_ws_marek', 48,
      'North-west of the post the road climbs to the Broken Crown, and the sentinels still stand their old posts below it. Walk up to the Broken Crown and defeat four Prism Sentinels on the way.',
      [('visit', 'prism_crown', 'Reach the Broken Crown', 1), ('kill', 'prismsentinel', 'Defeat Prism Sentinels below the Crown', 4)], requires='prism_sentinels'),
    Q('prism_ws_hearts', 'Hearts for the Veils', 'prism_ws_ottilie', 48,
      'Ottilie weaves the glow of a sentinel\'s heart into veils that keep the white sun off the eyes. Bring her three Prism Hearts.',
      [('bring', 'prism_heart', 'Bring Prism Hearts', 3)], requires='prism_ws_walk'),
    Q('prism_ws_hold', 'Keep the Beacon Lit', 'prism_ws_marek', 49,
      'The beacon on the north road gutters whenever the Sunshard flares, and then the sentinels come down to put it out. Stand in the circle at the beacon for twenty seconds while Marek feeds the flame, and keep the guards off him.',
      [('hold', 'prism_beacon_m', 'Keep the Beacon Lit', 20)], requires='prism_ws_walk'),
    Q('prism_ws_watch', 'The Broken Watch', 'prism_ws_marek', 49,
      'South-east of the post, between the north road and the mountains, the sentinels guard a watch that fell long ago. Walk out to the Broken Watch and defeat five Prism Sentinels there, then tell Marek how many still stand.',
      [('visit', 'prism_watch', 'Reach the Broken Watch', 1), ('kill', 'prismsentinel', 'Defeat Prism Sentinels at the Watch', 5)], requires='prism_ws_hold'),
    # Cairnfoot, by the mountains
    Q('prism_cf_walk', 'Out to the Sunspire Reaches', 'prism_cf_runa', 47,
      'South-east of Cairnfoot the biggest crystals of the waste stand in the road, and the scarabs have made nests round their feet. Walk out to the Sunspire Reaches and defeat four Shard Scarabs there.',
      [('visit', 'prism_spires', 'Reach the Sunspire Reaches', 1), ('kill', 'shardscarab', 'Defeat Shard Scarabs in the Reaches', 4)], requires='prism_harriers'),
    Q('prism_cf_fangs', 'Fangs for the Carver', 'prism_cf_teo', 47,
      'Teo carves mirage fangs into the markers that keep the east road a road. Bring him five Mirage Fangs.',
      [('bring', 'mirage_fang', 'Bring Mirage Fangs', 5)], requires='prism_cf_walk'),
    Q('prism_cf_hold', 'Hold the Cairn Circle', 'prism_cf_runa', 48,
      'Harriers drop on the cairns north of Cairnfoot whenever the wind turns, and scatter the markers. Stand in the circle on the ridge for twenty seconds while Runa rebuilds the cairn, and keep the harriers off her.',
      [('hold', 'prism_cairn_m', 'Hold the Cairn Circle', 20)], requires='prism_cf_walk'),
    Q('prism_cf_south', 'Along the Brine Road', 'prism_cf_runa', 49,
      'The road along the south coast carries brine to the east, and the scarabs have started to cut it. Walk down to the Brine Road and defeat five Shard Scarabs there.',
      [('visit', 'prism_brine', 'Reach the Brine Road', 1), ('kill', 'shardscarab', 'Defeat Shard Scarabs on the Brine Road', 5)], requires='prism_cf_hold'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'prism_jackals': dict(description='Thin the packs that hunt travellers on the Salt Flats and the first ridge around the Last Shade.'),
    'prism_scarabs': dict(description='The glass scarabs are eating the trail markers on the roads out of the Last Shade. Clear them from the ridge and the lens fields.'),
    'prism_harriers': dict(description='Drive the glass harriers off the roads between the Lens Fields and the mountains.'),
    'prism_sentinels': dict(description='The old prism sentinels still guard a watch that no longer exists, in the north and the north-east. Break their posts.'),
    'prism_queen': dict(description='A reflected queen leads the jackals from the Mirror Court in the north-west, between the great crystals. Find her far from any road, and bring a group.'),
    'prism_sunshard': dict(description='Below the Broken Crown in the north, the Sunshard is burning the sky white. Bring a full group.'),
    'prism_survey': dict(description='Prove the long road from the Last Shade through the Lens Fields to the Broken Crown is safe.'),
}

NPC_UPDATES = {}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    hub = next(n for n in zone['npcs'] if n['id'] == 'travel_last_shade')
    healer = next(n for n in zone['npcs'] if n['id'] == 'prism_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'prism_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    spots = {'mirrorfall': (-1, 2), 'whitesun': (-1, 3.5), 'cairnfoot': (-1, 3.5)}
    keys = list(spots)
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'],
                 travelLinks=['travel_last_shade'] + [f'travel_{k}' for k in keys if k != key])
        out.append(t)
        for link in (hub,):
            if t['id'] not in link['travelLinks']:
                link['travelLinks'].append(t['id'])
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_14_the_last_shade')
    for key, (dx, dy) in {'mirrorfall': (3, 1), 'whitesun': (2, 1), 'cairnfoot': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_14_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Prismwaste entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 14]
    names = {'travel_last_shade': ('The Last Shade', 'mailbox_14_the_last_shade')}
    for key, h in hamlets.items():
        names['travel_' + key] = (h['name'], f'mailbox_14_{key}')
    for master, (hub, boxid) in names.items():
        box = next(n for n in zone['npcs'] if n['id'] == boxid)
        m = next(n for n in zone['npcs'] if n['id'] == master)
        directory.append(dict(id=box['id'], zone=14, hub=hub, x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(zone, hamlets):
    """Idempotent, so `plan` also works on a map that already carries the design."""
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
