"""The Obsidian Orrery's outposts, people, quests, places and elites. Data for scripts/orrery_design.py (shaped coordinates, zone 15).

Owner request 2026-11-08: "for pilot. reshape orrery. and remake the zone and quests to fit the new shape. no fillers." Owner answers: keep both elites
(Pendulum Matron, Epoch Engine) and add one new elite with no quest, three new outposts, and the Orrery is seamless against Astralhollow (north) and the
Moonspore Canopy (south); every other crossing stays a walk-in gate. Every old `orrery_*`, `arena_orrery_*`, `es_12`/`es_go_12` and `banker` id stays
(saved progress, tests, quest_gear_rewards): texts are rewritten only where the geography changed. Fourteen quests are new. New ids and people start
`orrery_` and stay within 19 characters (the accept string is capped at 32). Levels 50-55, rewardXp = levels.txt[level-1] / 10. Every text here needs
its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(50, 56)}
GOLD = {50: 1300, 51: 1450, 52: 1600, 53: 1800, 54: 2000, 55: 2300}

# the outposts: plaza, half width/height of the sanctuary rectangle. Nothing art-less may stand within 20 tiles of the Astralhollow or Moonspore border.
HAMLETS = {
    'bellcourt':   dict(name='Bellcourt', x=84, y=124, hw=12, hh=11),
    'crownwatch':  dict(name='Crownwatch', x=190, y=82, hw=12, hh=11),
    'shardwatch':  dict(name='Shardwatch', x=254, y=128, hw=12, hh=11),
}

# kind, x, y (the three elites: the Matron and the Engine have a quest, the Mainspring Wyrm none; awareness is the 4th value of the server's attack profile)
ELITES = [('pendulummatron', 118, 100), ('epochengine', 192, 34), ('mainspringwyrm', 262, 218)]
ELITE_LEVEL = {'pendulummatron': 54, 'epochengine': 55, 'mainspringwyrm': 53}
AWARENESS = {'pendulummatron': 11., 'epochengine': 13., 'mainspringwyrm': 12.}

PAVILION = dict(r=1.7, width=4, depth=3)

DRESSING = {
    'bellcourt': [
        ('stillpoint', 0, -6.5, dict(PAVILION)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#6a7288', label='Bellringers')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#c8a66b', label='Brass Ladle')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Bellcourt')),
        ('hourpillar', -8, -1, dict(r=.7)), ('hourpillar', 9, -1, dict(r=.7)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -3, -2, dict(r=.4)),
    ],
    'crownwatch': [
        ('stillpoint', 0, -6.5, dict(PAVILION)),
        ('tent', -9, 5, dict(r=1.5, width=3, depth=2.4, color='#8a6f6a', label='Crown Watch')),
        ('stall', 7, 4, dict(r=0, width=1.8, depth=1.2, color='#b0a06a', label='Tickwater')),
        ('noticeboard', -5, -7, dict(r=.4, width=1.3, depth=.4, label='Crownwatch')),
        ('hourpillar', -8, -1, dict(r=.7)), ('hourpillar', 9, -1, dict(r=.7)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, 0, dict(r=.4)), ('brazier', 6, -2, dict(r=.4)),
    ],
    'shardwatch': [
        ('stillpoint', 0, -6.5, dict(PAVILION)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#6a5a8a', label='Surveyors')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#8a8aa8', label='Spindle & Glass')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Shardwatch')),
        ('hourpillar', -8, -1, dict(r=.7)), ('hourpillar', 9, -1, dict(r=.7)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, -1, dict(r=.4)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
}

NPCS = [
    dict(id='orrery_bc_tolla', hamlet='bellcourt', dx=-3, dy=-1, name='Bell-Warden Tolla Brassfall', role='Bell warden', color='#9aa8c8',
         look=dict(skin='#d9b08c', hair='#cfd0d8', style='long', hat='hood', hatColor='#4a5a7a'),
         dialogue='The great bell on the western road rings itself whenever the gears gather, and every gear in the Winding Court comes to answer it. I keep the clapper in hand so the court keeps to its own side of the diamond.'),
    dict(id='orrery_bc_fenn', hamlet='bellcourt', dx=5, dy=3, name='Fenn Ratchet', role='Gearwright', color='#b8946a',
         look=dict(skin='#c99b7a', hair='#3a2a1a', style='short', hat='none', hatColor='#6a5a4a'),
         dialogue='Bronze takes a file better than steel does, and a mantis blade is bronze that someone already shaped for me. Bring me a few and I will make something that cuts a clock-spring clean.'),
    dict(id='orrery_bc_trader', hamlet='bellcourt', dx=-6, dy=4.6, name='Marit of the Brass Ladle', role='Outpost trader', color='#c8a66b', trader=True,
         look=dict(skin='#edc5a1', hair='#a8683a', style='long', hat='none', hatColor='#c8a66b'),
         dialogue='Stew, tonics and a ladle of something warm for the ones who stand in the court and listen to the clocks. Everything hot is sold at cost, because the bell is cold enough.'),
    dict(id='orrery_cn_isolde', hamlet='crownwatch', dx=-3, dy=-1, name='Watch-Captain Isolde Vane', role='Crown watch captain', color='#c8806a',
         look=dict(skin='#d9b08c', hair='#7a3a2a', style='short', hat='hood', hatColor='#7a3a3a'),
         dialogue='The Epoch Engine keeps an hour that should have ended, and the chronoguards still hold the valley under it. I keep this watch so someone always knows how many of them are on their feet.'),
    dict(id='orrery_cn_quill', hamlet='crownwatch', dx=5, dy=3, name='Quill Sandsworn', role='Hourglass scribe', color='#a8a06a',
         look=dict(skin='#c99b7a', hair='#2a2a3a', style='short', hat='none', hatColor='#6a6a4a'),
         dialogue='Every hourglass on the watch is ground from a seer\'s lens, because nothing else is clear enough to count the last grain. I write down what falls through.'),
    dict(id='orrery_cn_trader', hamlet='crownwatch', dx=-5, dy=6.2, name='Pell Tickwater', role='Outpost trader', color='#b0a06a', trader=True,
         look=dict(skin='#edc5a1', hair='#5a4a2a', style='long', hat='none', hatColor='#b0a06a'),
         dialogue='Bread, tonics and stew for the ones who stand under the crown and wait. If the clock ticks faster while you eat, that is only the soup.'),
    dict(id='orrery_sw_kestrel', hamlet='shardwatch', dx=-3, dy=-1, name='Surveyor Kestrel Dross', role='Shard surveyor', color='#8a7ac8',
         look=dict(skin='#edc5a1', hair='#cfcfe8', style='long', hat='hood', hatColor='#5a4a8a'),
         dialogue='East of the second trunk road the land turns to black glass, and the glass keeps growing. I chart the spires, the seers on them and whatever coils through the Reaches at night. I would like the coil off my map.'),
    dict(id='orrery_sw_anselm', hamlet='shardwatch', dx=5, dy=3, name='Anselm Glasscutter', role='Glass-cutter', color='#7a7aa8',
         look=dict(skin='#c99b7a', hair='#2a2a3a', style='short', hat='hood', hatColor='#4a4a6a'),
         dialogue='Obsidian cuts the hand that cuts it unless you cut it with something that bites back. A gearling tooth bites back. Bring me a few and the glass stops fighting.'),
    dict(id='orrery_sw_trader', hamlet='shardwatch', dx=-6, dy=5.6, name='Dunya Spindle', role='Outpost trader', color='#8a8aa8', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#8a8aa8'),
         dialogue='Thread, wicks and stew. If a shard falls near you, do not look at it: look at me, and I will sell you a tonic.'),
]

PLACES = [
    dict(id='orrery_axis', name='The Axis', x=140, y=181, r=6),
    dict(id='orrery_court', name='The Winding Court', x=100, y=128, r=6),
    dict(id='orrery_crown', name='The Epoch Crown', x=192, y=62, r=5),
    dict(id='orrery_reaches', name='The Obsidian Reaches', x=262, y=92, r=6),
    dict(id='orrery_escape', name='The Escapement', x=246, y=252, r=6),
    dict(id='orrery_still_m', name='The Stillpoint Dial', x=96, y=268, r=2.1, waves=[dict(at=1, tag='orrery_still_m#a'), dict(at=11, tag='orrery_still_m#b')]),
    dict(id='orrery_bell_m', name='The Western Bell', x=80, y=96, r=2.1, waves=[dict(at=1, tag='orrery_bell_m#a'), dict(at=11, tag='orrery_bell_m#b')]),
    dict(id='orrery_gate_m', name='The Crown Gate', x=190, y=114, r=2.1, waves=[dict(at=1, tag='orrery_gate_m#a'), dict(at=11, tag='orrery_gate_m#b')]),
    dict(id='orrery_shard_m', name='The Shardfall Ridge', x=268, y=70, r=2.1, waves=[dict(at=1, tag='orrery_shard_m#a'), dict(at=11, tag='orrery_shard_m#b')]),
]

# Sleepers woken by a hold wave: four or two-and-two a wave, round the circle
AMBUSH = [
    ('bronzemantis', 90, 262, 'orrery_still_m#a'), ('bronzemantis', 102, 274, 'orrery_still_m#a'), ('bronzemantis', 90, 274, 'orrery_still_m#b'), ('bronzemantis', 102, 262, 'orrery_still_m#b'),
    ('bronzemantis', 96, 260, 'orrery_still_m#a'), ('bronzemantis', 96, 276, 'orrery_still_m#b'),
    ('gearling', 74, 90, 'orrery_bell_m#a'), ('gearling', 86, 102, 'orrery_bell_m#a'), ('gearling', 74, 102, 'orrery_bell_m#b'), ('gearling', 86, 90, 'orrery_bell_m#b'),
    ('chronoguard', 184, 108, 'orrery_gate_m#a'), ('chronoguard', 196, 120, 'orrery_gate_m#a'), ('chronoguard', 184, 120, 'orrery_gate_m#b'), ('chronoguard', 196, 108, 'orrery_gate_m#b'),
    ('chronoguard', 262, 64, 'orrery_shard_m#a'), ('chronoguard', 274, 76, 'orrery_shard_m#a'), ('orbitseer', 262, 76, 'orrery_shard_m#b'), ('orbitseer', 274, 64, 'orrery_shard_m#b'),
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
    # the Stillpoint, in the far south-west
    Q('orrery_h_hold', 'Wind the Stillpoint', 'orrery_keeper', 50,
      'The refuge\'s dial runs down whenever the mantises gather, and when it stops the Stillpoint stops being still. Stand in the circle north of the refuge for twenty seconds while Ilyra winds it, and let nothing reach her.',
      [('hold', 'orrery_still_m', 'Wind the Stillpoint', 20)], requires='orrery_welcome'),
    Q('orrery_h_rounds', 'The Keepers of the Hours', 'orrery_scholar', 53,
      'Three outposts keep time beyond the Stillpoint: Bellcourt under the Winding Court in the west, Crownwatch in the valley below the crown, Shardwatch in the east. Edda wants their keepers told that the Stillpoint still holds. Speak with Tolla, Isolde and Kestrel, and use their Travel Masters if the road is long.',
      [('talk', 'orrery_bc_tolla', 'Speak with Bell-Warden Tolla Brassfall at Bellcourt', 1), ('talk', 'orrery_cn_isolde', 'Speak with Watch-Captain Isolde Vane at Crownwatch', 1),
       ('talk', 'orrery_sw_kestrel', 'Speak with Surveyor Kestrel Dross at Shardwatch', 1)], requires='orrery_guards'),
    # Bellcourt, under the Winding Court
    Q('orrery_bc_walk', 'Up to the Winding Court', 'orrery_bc_tolla', 51,
      'The Winding Court lies north-east of Bellcourt, inside the western diamond of roads, where the old clock never stopped winding. Tolla wants a count of what lives there. Walk up to the Winding Court and defeat four Gearlings on the way.',
      [('visit', 'orrery_court', 'Reach the Winding Court', 1), ('kill', 'gearling', 'Defeat Gearlings on the way', 4)], requires='orrery_gearlings'),
    Q('orrery_bc_blades', 'Blades for the Gearwright', 'orrery_bc_fenn', 51,
      'Fenn files bronze mantis blades into shears that cut a clock-spring clean. Bring him four Bronze Mantis Blades.',
      [('bring', 'mantis_blade', 'Bring Bronze Mantis Blades', 4)], requires='orrery_bc_walk'),
    Q('orrery_bc_hold', 'Hold the Western Bell', 'orrery_bc_tolla', 52,
      'The bell on the road north of Bellcourt rings itself whenever the gears gather, and then every gear in the court comes to answer it. Stand in the circle beside it for twenty seconds while Tolla steadies the clapper, and keep the court off her.',
      [('hold', 'orrery_bell_m', 'Hold the Western Bell', 20)], requires='orrery_bc_walk'),
    Q('orrery_bc_axis', 'Across the Axis', 'orrery_bc_tolla', 52,
      'South-east of the court the roads cross at the Axis, and the orbit seers fire from the broken rings round it. Walk to the Axis, follow the ring road a little way, and defeat five Orbit Seers on the way.',
      [('visit', 'orrery_axis', 'Reach the Axis', 1), ('kill', 'orbitseer', 'Defeat Orbit Seers round the Axis', 5)], requires='orrery_bc_hold'),
    # Crownwatch, in the valley below the Epoch Crown
    Q('orrery_cn_valley', 'Down the Crown Valley', 'orrery_cn_isolde', 53,
      'Between the two trunk roads the valley runs up to the Epoch Crown, and the chronoguards still stand their old posts in it. Walk up to the Epoch Crown and defeat four Chronoguards on the way.',
      [('visit', 'orrery_crown', 'Reach the Epoch Crown', 1), ('kill', 'chronoguard', 'Defeat Chronoguards in the valley', 4)], requires='orrery_seers'),
    Q('orrery_cn_plates', 'Plates for the Watch', 'orrery_cn_isolde', 53,
      'Isolde mends the watch\'s shields with chronoguard plate, and the plate she has is cracked. Bring her four Chronoguard Plates.',
      [('bring', 'chronoguard_plate', 'Bring Chronoguard Plates', 4)], requires='orrery_cn_valley'),
    Q('orrery_cn_hold', 'Bar the Crown Gate', 'orrery_cn_isolde', 54,
      'The old gate at the south end of the valley rings when the Engine turns, and the guards come down the valley to answer it. Stand in the circle at the gate for twenty seconds while Isolde bars it, and keep the guards off her.',
      [('hold', 'orrery_gate_m', 'Hold the Crown Gate', 20)], requires='orrery_cn_valley'),
    Q('orrery_cn_lens', 'Lenses for the Scribe', 'orrery_cn_quill', 54,
      'Quill grinds orbit seer lenses into the glass of the watch\'s hourglasses, and the last grain has been falling through a cracked one. Bring him four Orbit Seer Lenses.',
      [('bring', 'seer_lens', 'Bring Orbit Seer Lenses', 4)], requires='orrery_cn_plates'),
    # Shardwatch, in the east
    Q('orrery_sw_reaches', 'Into the Obsidian Reaches', 'orrery_sw_kestrel', 52,
      'East of the second trunk road the land turns to black glass and the seers fire from the spires. Walk out to the Obsidian Reaches and defeat four Orbit Seers there, then tell Kestrel how far the glass has grown.',
      [('visit', 'orrery_reaches', 'Reach the Obsidian Reaches', 1), ('kill', 'orbitseer', 'Defeat Orbit Seers in the Reaches', 4)], requires='orrery_seers'),
    Q('orrery_sw_glass', 'Teeth for the Glass', 'orrery_sw_anselm', 52,
      'Anselm cuts obsidian with a gearling tooth, because nothing else bites back. Bring him five Gearling Teeth.',
      [('bring', 'gearling_tooth', 'Bring Gearling Teeth', 5)], requires='orrery_sw_reaches'),
    Q('orrery_sw_hold', 'Hold the Shardfall Ridge', 'orrery_sw_kestrel', 53,
      'Shards come down off the spires in the north-east whenever the Engine turns, and the guards walk out to gather them. Stand in the circle on the ridge for twenty seconds while Kestrel counts the fall, and keep the guards off her.',
      [('hold', 'orrery_shard_m', 'Hold the Shardfall Ridge', 20)], requires='orrery_sw_reaches'),
    Q('orrery_sw_south', 'South to the Escapement', 'orrery_sw_kestrel', 54,
      'Where the south-east road meets the second trunk the mantises have cut a ring through the grass, and Kestrel cannot find the end of it. Walk down to the Escapement and defeat five Bronze Mantises there.',
      [('visit', 'orrery_escape', 'Reach the Escapement', 1), ('kill', 'bronzemantis', 'Defeat Bronze Mantises at the Escapement', 5)], requires='orrery_sw_hold'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'orrery_matron': dict(description='The Winding Court inside the western diamond belongs to the Pendulum Matron, and she has started to wind the clocks of the roads round it. Tolla\'s gearwrights cannot reach her. Find her in the court, far from any road, and end it. Bring allies.'),
    'orrery_engine': dict(description='The Epoch Engine stands under the Epoch Crown at the north end of the valley and keeps an hour that should have ended. Shut it down. Bring a full group.'),
    'orrery_survey': dict(description='Make the ascent safe from the Brass Meadows by the Stillpoint, up the trunk road and the Axis, to the Crown Valley: defeat the guards, seers, gearlings and mantises that hold it.'),
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
    hub = next(n for n in zone['npcs'] if n['id'] == 'travel_stillpoint')
    healer = next(n for n in zone['npcs'] if n['id'] == 'orrery_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'orrery_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    spots = {'bellcourt': (-1, 2), 'crownwatch': (-1, 3.5), 'shardwatch': (-1, 3.5)}
    keys = list(spots)
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'],
                 travelLinks=['travel_stillpoint'] + [f'travel_{k}' for k in keys if k != key])
        out.append(t)
        for link in (hub,):
            if t['id'] not in link['travelLinks']:
                link['travelLinks'].append(t['id'])
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_15_the_stillpoint')
    for key, (dx, dy) in {'bellcourt': (3, 1), 'crownwatch': (2, 1), 'shardwatch': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_15_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Orrery entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 15]
    names = {'travel_stillpoint': ('The Stillpoint', 'mailbox_15_the_stillpoint')}
    for key, h in hamlets.items():
        names['travel_' + key] = (h['name'], f'mailbox_15_{key}')
    for master, (hub, boxid) in names.items():
        box = next(n for n in zone['npcs'] if n['id'] == boxid)
        m = next(n for n in zone['npcs'] if n['id'] == master)
        directory.append(dict(id=box['id'], zone=15, hub=hub, x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
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
