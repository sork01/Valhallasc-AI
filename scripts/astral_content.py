"""Astralhollow's outposts, people, quests, places and elites. Data for scripts/astral_design.py (shaped coordinates, zone 13).

Owner request 2026-11-07: "reshape astralhollow, and remake the zone and quests to fit the new shape, no fillers". Owner answers: three new
elites (two with a quest, one without; the zone had none), three new outposts. Every old `astral_*`, `arena_astral_*`, `es_10`/`es_go_10` and
`banker_astralhollow` id stays (saved progress, tests, quest_gear_rewards): texts are rewritten only where the geography changed. Fourteen
quests are new (two of them for the elites). New ids and people start `astral_` and stay within 19 characters (the accept string is capped
at 32). Levels 40-45, rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(40, 46)}
GOLD = {40: 520, 41: 560, 42: 620, 43: 680, 44: 760, 45: 860}

# the outposts: plaza, half width/height of the sanctuary rectangle. Nothing art-less may stand within 20 tiles of the Prismwaste or Orrery border.
HAMLETS = {
    'choirrest':   dict(name='Choir Rest', x=120, y=192, hw=14, hh=11),
    'cometwatch':  dict(name='Cometwatch', x=222, y=176, hw=12, hh=11),
    'fallstone':   dict(name='Fallstone Hold', x=172, y=48, hw=14, hh=11),
}

# kind, x, y (the three elites: two quests, one none; awareness is the 4th value of the server's attack profile)
ELITES = [('cometmaw', 246, 142), ('eclipsequeen', 112, 76), ('orbitwarden', 178, 150)]
ELITE_LEVEL = {'cometmaw': 42, 'eclipsequeen': 44, 'orbitwarden': 45}
AWARENESS = {'cometmaw': 10., 'eclipsequeen': 9., 'orbitwarden': 11.}

HOUSE = dict(r=1.8, width=3.2, depth=3.0)

DRESSING = {
    'choirrest': [
        ('astralhouse', -9, -6, dict(HOUSE)), ('astralhouse', 9, -6, dict(HOUSE)),
        ('tent', 10, 6, dict(r=1.5, width=3, depth=2.4, color='#5f7a9a', label='Listeners')),
        ('stall', -5, 3, dict(r=0, width=1.8, depth=1.2, color='#7a9fb0', label='Hollow Lanterns')),
        ('noticeboard', 2, -7, dict(r=.4, width=1.3, depth=.4, label='Choir Rest')),
        ('starwell', 1, -3.5, dict(r=.9)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
        ('astrolamp', -4, -3, dict(r=.35)), ('astrolamp', 7, 1, dict(r=.35)),
    ],
    'cometwatch': [
        ('astralhouse', -8, -6, dict(HOUSE)), ('astralhouse', 8, -6, dict(HOUSE)),
        ('tent', -9, 6, dict(r=1.5, width=3, depth=2.4, color='#8a6f6a', label='Watch')),
        ('stall', 7, 4, dict(r=0, width=1.8, depth=1.2, color='#b08a6a', label='Ash & Ember')),
        ('noticeboard', -2, -7, dict(r=.4, width=1.3, depth=.4, label='Cometwatch')),
        ('starwell', 1, -3.5, dict(r=.9)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -2, 0, dict(r=.4)), ('brazier', 6, -2, dict(r=.4)),
        ('astrolamp', -5, 2, dict(r=.35)), ('astrolamp', 6, 1, dict(r=.35)),
    ],
    'fallstone': [
        ('astralhouse', -9, -6, dict(HOUSE)), ('astralhouse', 9, 6, dict(HOUSE)),
        ('tent', 10, -6, dict(r=1.5, width=3, depth=2.4, color='#6a6a8a', label='Masons')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#8a8aa8', label='Soot & Silver')),
        ('noticeboard', 2, -7, dict(r=.4, width=1.3, depth=.4, label='Fallstone Hold')),
        ('starwell', 1, -3.5, dict(r=.9)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -2, -1, dict(r=.4)), ('brazier', 6, 1, dict(r=.4)),
        ('astrolamp', -4, 1, dict(r=.35)), ('astrolamp', 5, -3, dict(r=.35)),
    ],
}

NPCS = [
    dict(id='astral_cr_mael', hamlet='choirrest', dx=-3, dy=-1, name='Chorister Mael Glasswright', role='Choir warden', color='#8aa8d8',
         look=dict(skin='#d9b08c', hair='#cfd8f0', style='long', hat='hood', hatColor='#4a5a8a'),
         dialogue='The crystals in these hollows sing when the wind finds the right chord, and the wyrms sing back. I keep the choir in tune so the hollows stay a song and do not turn into a scream.'),
    dict(id='astral_cr_ide', hamlet='choirrest', dx=5, dy=3, name='Ide Fallwatcher', role='Star surveyor', color='#7a9a8a',
         look=dict(skin='#c99b7a', hair='#2a3a4a', style='short', hat='none', hatColor='#4a6a7a'),
         dialogue='I chart where the stars came down. The ring is the first line of the map: the hollows, the heart, the east field and the north fall. Walk it with me and I will show you where the sky still has a hole in it.'),
    dict(id='astral_cr_trader', hamlet='choirrest', dx=-5, dy=4.6, name='Orla of the Hollow Lanterns', role='Outpost trader', color='#7aa0b0', trader=True,
         look=dict(skin='#edc5a1', hair='#8a6aa8', style='long', hat='none', hatColor='#7aa0b0'),
         dialogue='Lanterns, stew and tonics. A lantern lit here burns blue and hums, so if yours hums, you are in the right place.'),
    dict(id='astral_cw_brisa', hamlet='cometwatch', dx=-3, dy=-1, name='Watchwarden Brisa Tailfire', role='Cometwatch warden', color='#c8806a',
         look=dict(skin='#d9b08c', hair='#b8503a', style='short', hat='hood', hatColor='#7a3a3a'),
         dialogue='Something with a burning tail runs the east field at night. We call it the Cometmaw, because it is mostly mouth. I keep this watch so someone is always counting the nights it comes closer.'),
    dict(id='astral_cw_oren', hamlet='cometwatch', dx=5, dy=3, name='Oren Cindersmith', role='Shell-smith', color='#9a7a6a',
         look=dict(skin='#c99b7a', hair='#5a3a2a', style='short', hat='none', hatColor='#6a5a4a'),
         dialogue='A beetle shell takes a hammer better than anything I have ever beaten flat. Bring me a few and I will make something that turns a claw.'),
    dict(id='astral_cw_trader', hamlet='cometwatch', dx=-5, dy=6.2, name='Tavi Ashmeal', role='Outpost trader', color='#b08a6a', trader=True,
         look=dict(skin='#edc5a1', hair='#a8683a', style='long', hat='none', hatColor='#b08a6a'),
         dialogue='Hot bread, tonics and stew for the people who stand in the dark and wait. Everything warm is sold at cost, because the watch should never be cold.'),
    dict(id='astral_fh_aurel', hamlet='fallstone', dx=-3, dy=-1, name='Hold-Keeper Aurel Starhearth', role='Hold-keeper', color='#8a8ac8',
         look=dict(skin='#edc5a1', hair='#cfcfe8', style='long', hat='hood', hatColor='#5a5a8a'),
         dialogue='This is where the first stone fell, and the field is still full of what came after. I keep this hold so the golems do not walk south and the queen does not walk out of her wood.'),
    dict(id='astral_fh_dov', hamlet='fallstone', dx=5, dy=3, name='Dov Nightmason', role='Line mason', color='#7a7aa8',
         look=dict(skin='#c99b7a', hair='#2a2a3a', style='short', hat='hood', hatColor='#4a4a6a'),
         dialogue='Every stone that falls leaves a line in the ground, and the lines point at what fell next. I mend the lines so the field keeps its shape. The black queen in the west wood is not on my map, and I would like her to stay off it.'),
    dict(id='astral_fh_trader', hamlet='fallstone', dx=-6, dy=5.6, name='Merrin Soot-and-Silver', role='Outpost trader', color='#8a8aa8', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#8a8aa8'),
         dialogue='Soot and silver, wicks and stew. If a stone falls near you, do not look at it: look at me, and I will sell you a tonic.'),
]

PLACES = [
    dict(id='astral_choir', name='The Choir Stones', x=102, y=178, r=5),
    dict(id='astral_ringwest', name='The Broken Ring', x=118, y=125, r=5),
    dict(id='astral_heart', name='The Heart of the Fall', x=152, y=150, r=5),
    dict(id='astral_cometfield', name='The Cometfield', x=236, y=160, r=6),
    dict(id='astral_fall_line', name='The Falling Line', x=196, y=30, r=5),
    dict(id='astral_lamps_m', name='The Hearth Lamps', x=203, y=270, r=2.1, waves=[dict(at=1, tag='astral_lamps_m#a'), dict(at=11, tag='astral_lamps_m#b')]),
    dict(id='astral_chord_m', name='The Choir Chord', x=100, y=166, r=2.1, waves=[dict(at=1, tag='astral_chord_m#a'), dict(at=11, tag='astral_chord_m#b')]),
    dict(id='astral_fire_m', name='The Watchfire', x=206, y=168, r=2.1, waves=[dict(at=1, tag='astral_fire_m#a'), dict(at=11, tag='astral_fire_m#b')]),
    dict(id='astral_line_m', name='The Mended Line', x=200, y=54, r=2.1, waves=[dict(at=1, tag='astral_line_m#a'), dict(at=11, tag='astral_line_m#b')]),
]

# Sleepers woken by a hold wave: four a wave, round the circle
AMBUSH = [
    ('voidmoth', 197, 264, 'astral_lamps_m#a'), ('voidmoth', 209, 276, 'astral_lamps_m#a'), ('voidmoth', 197, 276, 'astral_lamps_m#b'), ('voidmoth', 209, 264, 'astral_lamps_m#b'),
    ('voidmoth', 203, 262, 'astral_lamps_m#a'), ('voidmoth', 203, 278, 'astral_lamps_m#b'),
    ('crystalwyrm', 94, 160, 'astral_chord_m#a'), ('crystalwyrm', 106, 172, 'astral_chord_m#a'), ('crystalwyrm', 94, 172, 'astral_chord_m#b'), ('crystalwyrm', 106, 160, 'astral_chord_m#b'),
    ('orbitbeetle', 200, 162, 'astral_fire_m#a'), ('orbitbeetle', 212, 174, 'astral_fire_m#a'), ('orbitbeetle', 200, 174, 'astral_fire_m#b'), ('orbitbeetle', 212, 162, 'astral_fire_m#b'),
    ('eclipsedryad', 194, 48, 'astral_line_m#a'), ('eclipsedryad', 206, 60, 'astral_line_m#a'), ('eclipsedryad', 194, 60, 'astral_line_m#b'), ('eclipsedryad', 206, 48, 'astral_line_m#b'),
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
    # the Observatory Court, in the far south
    Q('astral_h_lamps', 'Light the Hearth Lamps', 'astral_warden', 40,
      'The lamps on the Lantern Meadows go out whenever the moths gather, and then the whole southern trail is dark. Stand in the lamp circle north-east of the Court for twenty seconds while Orun lights them, and let nothing reach him.',
      [('hold', 'astral_lamps_m', 'Hold the Hearth Lamps', 20)], requires='astral_welcome'),
    Q('astral_h_rounds', 'The Keepers of the Ring', 'astral_steward', 43,
      'Three outposts keep the Starway: Choir Rest on the west of the Impact Ring, Cometwatch on the east, Fallstone Hold at the north end. Seren wants their keepers told that the Court is still lit. Speak with Mael, Brisa and Aurel, and use their Travel Masters if the road is long.',
      [('talk', 'astral_cr_mael', 'Speak with Chorister Mael Glasswright at Choir Rest', 1), ('talk', 'astral_cw_brisa', 'Speak with Watchwarden Brisa Tailfire at Cometwatch', 1),
       ('talk', 'astral_fh_aurel', 'Speak with Hold-Keeper Aurel Starhearth at Fallstone Hold', 1)], requires='astral_dryads'),
    # Choir Rest, on the west side of the Impact Ring
    Q('astral_cr_hollows', 'Down to the Hollows', 'astral_cr_ide', 41,
      'The Choir Hollows lie on the west side of the ring, where the crystal forest begins. Ide wants the first line of her map drawn from the ground. Walk to the Choir Stones and defeat four Crystalwyrms on the way.',
      [('visit', 'astral_choir', 'Reach the Choir Stones', 1), ('kill', 'crystalwyrm', 'Defeat Crystalwyrms in the hollows', 4)], requires='astral_moths'),
    Q('astral_cr_lanterns', 'Shades for the Lanterns', 'astral_cr_trader', 41,
      'A lantern hums blue in the hollows and flares white when a moth comes near, and the moths are drawn to the flare. Orla wants five Void Wings to shade them with.',
      [('bring', 'voidwing', 'Bring Void Wings', 5)], requires='astral_cr_hollows'),
    Q('astral_cr_chord', 'The Choir Chord', 'astral_cr_mael', 42,
      'Once a night the whole forest sounds one chord, and the wyrms gather north of the Choir Stones to sing it back. Stand in the circle there for twenty seconds while Mael tunes it, and keep the wyrms off him.',
      [('hold', 'astral_chord_m', 'Hold the Choir Chord', 20)], requires='astral_cr_hollows'),
    Q('astral_cr_ring', 'Along the Broken Ring', 'astral_cr_ide', 42,
      'North of the Choir Stones the ring road climbs the west side of the crater and the orbit beetles nest in the broken crystals along it. Walk up to the Broken Ring, follow the trunk road into the Heart of the Fall, and defeat five Orbit Beetles on the way.',
      [('visit', 'astral_ringwest', 'Reach the Broken Ring', 1), ('visit', 'astral_heart', 'Reach the Heart of the Fall', 1), ('kill', 'orbitbeetle', 'Defeat Orbit Beetles on the ring', 5)], requires='astral_cr_chord'),
    # Cometwatch, on the east side
    Q('astral_cw_scout', 'Smoke on the East Ring', 'astral_cw_brisa', 42,
      'The east side of the ring is the beetles\' ground, and at night something with a burning tail runs it. Walk out to the Cometfield, defeat four Orbit Beetles there, and tell Brisa how close the tail came.',
      [('visit', 'astral_cometfield', 'Reach the Cometfield', 1), ('kill', 'orbitbeetle', 'Defeat Orbit Beetles on the east field', 4)], requires='astral_beetles'),
    Q('astral_cw_shells', 'Shells for the Smithy', 'astral_cw_oren', 43,
      'Oren shapes beetle shell into plates that turn a claw. Bring him four Orbit Shells and he will tell you what the Cometmaw leaves in the ash.',
      [('bring', 'orbit_shell', 'Bring Orbit Shells', 4)], requires='astral_cw_scout'),
    Q('astral_cw_fire', 'The Watchfire', 'astral_cw_brisa', 43,
      'The watchfire inside the east ring keeps the field in sight, and the beetles come for the flame. Stand in the circle beside it for twenty seconds while Brisa feeds the fire, and keep the field off her.',
      [('hold', 'astral_fire_m', 'Guard the Watchfire', 20)], requires='astral_cw_scout'),
    Q('astral_cometmaw', 'The Cometmaw', 'astral_cw_brisa', 42,
      'It runs the outer east field at night, a hound of burning ice that is mostly mouth, and it has started to come inside the ring. Brisa wants it ended before it learns the way to the Court. Find the Cometmaw on the east field, beyond the ring road, and defeat it. Bring friends.',
      [('kill', 'cometmaw', 'Defeat the Cometmaw', 1)], requires='astral_cw_shells', recommendedPlayers=3),
    # Fallstone Hold, at the north end of the Starway
    Q('astral_fh_walk', 'Along the Falling Line', 'astral_fh_aurel', 44,
      'The first stone fell where the Starway ends, and the field north of the ring is still full of golems made from what came after. Walk north-east to the Falling Line and defeat four Meteor Golems on the way.',
      [('visit', 'astral_fall_line', 'Reach the Falling Line', 1), ('kill', 'meteorgolem', 'Defeat Meteor Golems on the field', 4)], requires='astral_survey'),
    Q('astral_fh_cores', 'Cores for the Masonry', 'astral_fh_dov', 45,
      'Dov mends the fall lines with core-stone, the red-hot heart of a golem when it cools. Bring him four Meteor Cores.',
      [('bring', 'meteor_core', 'Bring Meteor Cores', 4)], requires='astral_fh_walk'),
    Q('astral_fh_line', 'Hold the Mended Line', 'astral_fh_dov', 44,
      'Where Dov has laid a new line the eclipse wood leans in, because the queen\'s dryads want the field for their shade. Stand in the circle on the east of the Hold for twenty seconds while he sets the stones, and keep the dryads off him.',
      [('hold', 'astral_line_m', 'Hold the Mended Line', 20)], requires='astral_fh_walk'),
    Q('astral_eclipsequeen', 'The Black Sun Queen', 'astral_fh_dov', 44,
      'In the north-west wood, beyond the ring and far from any road, a crowned dryad has hung a black sun in the branches and the whole wood leans toward it. Dov calls her the Eclipse Queen. Find her in the western wood and end it. Bring friends.',
      [('kill', 'eclipsequeen', 'Defeat the Eclipse Queen', 1)], requires='astral_fh_line', recommendedPlayers=3),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {}

NPC_UPDATES = {}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    hub = next(n for n in zone['npcs'] if n['id'] == 'travel_astralhollow')
    healer = next(n for n in zone['npcs'] if n['id'] == 'astral_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'astral_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    spots = {'choirrest': (-1, 2), 'cometwatch': (-1, 3.5), 'fallstone': (-1, 3.5)}
    keys = list(spots)
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'],
                 travelLinks=['travel_astralhollow'] + [f'travel_{k}' for k in keys if k != key])
        out.append(t)
        for link in (hub,):
            if t['id'] not in link['travelLinks']:
                link['travelLinks'].append(t['id'])
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_13_astralhollow')
    for key, (dx, dy) in {'choirrest': (3, 1), 'cometwatch': (2, 1), 'fallstone': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_13_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Astralhollow entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 13]
    names = {'travel_astralhollow': 'Astralhollow'}
    for key, h in hamlets.items():
        names['travel_' + key] = h['name']
    for master, hub in names.items():
        key = master.split('travel_')[1]
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_13_{key}')
        m = next(n for n in zone['npcs'] if n['id'] == master)
        directory.append(dict(id=box['id'], zone=13, hub=hub, x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
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
