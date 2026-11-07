"""Rán's Deep's outposts, people, places and quests on the shaped map (pilot). Data for scripts/deep_design.py (zone 8, shaped coordinates).

Every old `deep_*`, `keel_*` and `es_*` quest id stays (saved progress, tests, quest_gear_rewards): text is rewritten only where the geography changed.
Fourteen quests are new, with three new outposts. The three elites are the old three (Hvitserk and the Ghostmaw with a quest, the Kraken with a quest;
owner, 2026-11-07: "keep the three"). New ids and people start `deep_` and stay within 19 characters (the accept string is capped at 32). Levels 35-40,
rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, written by hand.

Geography (shaped frame, north up): the Net, the coral labyrinth, fills the north and the middle, 15 x 10 cells with one door, the Pearl Gate, in its
south wall. Below it lie the Shallows: Keelhaven (south-west, a camp of overturned longships), the Maelstrom's landing on the west rim, the wreck of
the Naglfar and the open water of the middle, the Drowned Chapel and Drownwatch in the east. Two camps stand INSIDE the Net: Lanternrest in the west,
Gatewatch on the east rim beside the way up to Astralhollow.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(35, 41)}
GOLD = {35: 1250, 36: 1350, 37: 1500, 38: 1650, 39: 1750, 40: 1900}

# the outposts. `room`: the camp fills a 2 x 2 room of the Net (the design puts its centre in the room); otherwise (x, y) is fixed.
HAMLETS = {
    'lanternrest': dict(name='Lanternrest', room='lantern', hw=14, hh=11),
    'gatewatch': dict(name='Gatewatch', room='gatewatch', hw=14, hh=11),
    'drownwatch': dict(name='Drownwatch', room=None, x=184, y=205, hw=14, hh=11),
}

HUT = dict(r=0, width=3.4, depth=3.2)
DRESSING = {
    'lanternrest': [
        ('house', -8, -6.5, dict(HUT, label='Lamp Hall', color='#c8a458')), ('house', 8.5, -6.5, dict(HUT, label='Brass Loft', color='#b8945a')),
        ('stall', 6, 5.5, dict(r=0, width=1.8, depth=1.2, color='#c4a060', label='Brine & Brass')),
        ('noticeboard', 0, -8.5, dict(r=.4, width=1.3, depth=.4, label='Lanternrest')),
        ('campfire', 0, 1, dict(r=.65)), ('bench', -3, 3, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -5.5, 3.5, dict(r=.4)), ('lamp', -4, -4.5, dict(r=.18)), ('lamp', 4, -4.5, dict(r=.18)),
    ],
    'gatewatch': [
        ('house', -8, -6.5, dict(HUT, label='Gate Hall', color='#5a9ab0')), ('house', 8.5, 6, dict(HUT, label='Reef Forge', color='#6aa8b8')),
        ('tent', -8.5, 6, dict(r=1.5, width=3, depth=2.4, color='#4a8aa0', label='Watch')),
        ('stall', 6, -6.5, dict(r=0, width=1.8, depth=1.2, color='#c4a060', label='Plates & Pearls')),
        ('noticeboard', 0, -8.5, dict(r=.4, width=1.3, depth=.4, label='Gatewatch')),
        ('campfire', 0, 1, dict(r=.65)), ('bench', 3, 3, dict(r=0, width=1.5, depth=.45)),
        ('brazier', 5.5, 3.5, dict(r=.4)), ('lamp', -4, -4.5, dict(r=.18)), ('lamp', 4, -4.5, dict(r=.18)),
    ],
    'drownwatch': [
        ('house', -9, -6.5, dict(HUT, label='Chapel Warden', color='#7a8ab8')), ('house', 9, -6.5, dict(HUT, label='Gravekeeper', color='#8a7ab0')),
        ('tent', 10, 6, dict(r=1.5, width=3, depth=2.4, color='#6a7aa0', label='Watch')),
        ('stall', -6, 3.0, dict(r=0, width=1.8, depth=1.2, color='#c4a060', label='Salt & Coin')),
        ('noticeboard', 0, -8.5, dict(r=.4, width=1.3, depth=.4, label='Drownwatch')),
        ('campfire', 0, 1, dict(r=.65)), ('bench', 3.5, 3, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -4, 0, dict(r=.4)), ('lamp', -5, -3, dict(r=.18)), ('lamp', 5, 0, dict(r=.18)),
    ],
}

NPCS = [
    dict(id='deep_lr_solveig', hamlet='lanternrest', dx=-3, dy=-1.5, name='Lamp-Warden Solveig Brasslamp', role='Keeper of Lanternrest', color='#c8a458',
         look=dict(skin='#edc5a1', hair='#a8683a', style='long', hat='none', hatColor='#c8a458'),
         dialogue='A room of the Net with a roof of coral and a lamp that never goes out: that is Lanternrest, and the morays hate it. They come up the west corridors to put the light out. I keep it lit, and I pay for every moray that stops coming.'),
    dict(id='deep_lr_torvald', hamlet='lanternrest', dx=4, dy=2.5, name='Torvald Netspool', role='Maze-runner', color='#b8945a',
         look=dict(skin='#d9b08c', hair='#6a5a4a', style='short', hat='cap', hatColor='#7a6a4a'),
         dialogue='I have run the west wing of the Net two hundred times and I have never run it the same way twice. The corridors move when you are not looking. The Great Lantern in the next room is the one fixed point, and a hero who has seen it does not get lost.'),
    dict(id='deep_lr_trader', hamlet='lanternrest', dx=7, dy=3.4, name='Eira Brinemonger', role='Outpost trader', color='#c4a060', trader=True,
         look=dict(skin='#c99b7a', hair='#2a2a32', style='short', hat='none', hatColor='#c4a060'),
         dialogue='Teeth, brass, stew and tonics. Everything on my table came out of the Net, and so far the Net has not asked for it back.'),
    dict(id='deep_gw_bergljot', hamlet='gatewatch', dx=-3, dy=-1.5, name='Gate-Warden Bergljot Tidecaller', role='Keeper of Gatewatch', color='#5a9ab0',
         look=dict(skin='#edc5a1', hair='#cfcfcf', style='long', hat='hood', hatColor='#3a7a90'),
         dialogue='Beyond this east wall the water turns to starlight, and the way up to Astralhollow opens here. The shellbacks sit in the corridors outside and think the gate is theirs. I hold the camp so that heroes can rest before they climb.'),
    dict(id='deep_gw_hallbjorn', hamlet='gatewatch', dx=4.5, dy=2.5, name='Hallbjorn Reefsmith', role='Reef-smith', color='#6aa8b8',
         look=dict(skin='#c99b7a', hair='#5a3a2a', style='bald', hat='none', hatColor='#6aa8b8'),
         dialogue='The reef grows where the vents breathe, and I cut it into plate. The vents west of the camp are the best, and the sirens like them too. Every hero who has cleared the Vent Garden has bought me a week of quiet.'),
    dict(id='deep_gw_trader', hamlet='gatewatch', dx=7, dy=-4.8, name='Gunnhild Weedwife', role='Outpost trader', color='#a0b8c8', trader=True,
         look=dict(skin='#edc5a1', hair='#8a4a2a', style='long', hat='none', hatColor='#a0b8c8'),
         dialogue='Plates, pearls, stew and tonics. A shellback plate is the one thing in the Net that is exactly as strong as it looks. I pay for it that way.'),
    dict(id='deep_dw_ottilia', hamlet='drownwatch', dx=-3, dy=-1.5, name='Chapel-Warden Ottilia Drownedsong', role='Keeper of Drownwatch', color='#7a8ab8',
         look=dict(skin='#edc5a1', hair='#2a2a3a', style='long', hat='hood', hatColor='#5a6a98'),
         dialogue='The Chapel stands east of here and its dead keep getting up for the service. We built Drownwatch in sight of its door, so somebody would always be looking. Thin the draugr, bring back their coins, and we keep the Shallows safe for Keelhaven.'),
    dict(id='deep_dw_skuli', hamlet='drownwatch', dx=5, dy=3, name='Skuli Gravedigger', role='Gravekeeper', color='#8a7ab0',
         look=dict(skin='#d9b08c', hair='#7a7a7a', style='short', hat='none', hatColor='#8a7ab0'),
         dialogue='Down here there is no earth to dig, so I stack the stones. The Salt Stones south of the camp are my work: one for every sailor the Net let go. I would like somebody to count them, and I would like the draugr to stop knocking them over.'),
    dict(id='deep_dw_trader', hamlet='drownwatch', dx=-7, dy=5.6, name='Rannveig Saltwife', role='Outpost trader', color='#c4a060', trader=True,
         look=dict(skin='#c99b7a', hair='#8a3a1a', style='short', hat='none', hatColor='#c4a060'),
         dialogue='Salt, coin, stew and tonics. The draugr carry the coins they were buried with, green and furred, and I buy every one.'),
]

# names for the places this design adds: (id, name, where, hint, radius); `where` is a cell (c, r) of the Net, an (x, y) in the Shallows or a
# crossing ('gate:<portal id>': the place stands between the gate and its arrival)
PLACES = [
    dict(id='deep_lr_lamp', name='the Great Lantern', where=('cell', (3, 5)), r=3.2),
    dict(id='deep_gw_vents', name='the Vent Garden', where=('cell', (12, 6)), r=4.0),
    dict(id='deep_dw_stones', name='the Salt Stones', where=('xy', (188, 226)), r=4.0),
    dict(id='deep_pad_maelstrom', name='the Maelstrom Landing', where=('gate', 'maelstrom_up'), r=3.0),
    dict(id='deep_pad_tideway', name="the Tideway to Nacrehold", where=('gate', 'nacre_gate'), r=3.0),
    dict(id='deep_pad_astral', name='the Way to Astralhollow', where=('gate', 'path_8_13'), r=3.0),
    dict(id='deep_pad_longship', name='the Longship Door', where=('door', 'deep_longship'), r=3.0),
]


def Q(id, title, npc, level, desc, objectives, requires=None, repeatable=False, **extra):
    q = dict(id=id, title=title, npc=npc, description=desc,
             objectives=[dict(kind=k, target=t, label=l, count=c) for k, t, l, c in objectives],
             level=level, rewardXp=XP[level], rewardGold=GOLD[level], requires=requires, repeatable=repeatable)
    reward = reward_for(id)
    if reward:
        q['rewardItem'] = reward
    q.update(extra)
    return q


QUESTS = [
    # Keelhaven: the ledger of the four ways in and out of the Deep
    Q('deep_kh_ledger', 'The Harbour Ledger', 'deep_warden', 36,
      'Four ways lead in and out of the Deep: the Maelstrom that dropped you in the south-west, the Tideway south to Nacrehold, the Longship door beside the camp and the way up to Astralhollow on the east wall of the Net. '
      'Skipper Ylva keeps a ledger of every one and wants each walked. Stand at all four.',
      [('visit', 'deep_pad_maelstrom', 'Stand at the Maelstrom Landing', 1), ('visit', 'deep_pad_tideway', 'Stand at the Tideway', 1),
       ('visit', 'deep_pad_longship', 'Stand at the Longship Door', 1), ('visit', 'deep_pad_astral', 'Stand at the Way to Astralhollow', 1)], requires='deep_welcome'),
    # Lanternrest, a camp inside the west of the Net
    Q('deep_lr_glow', 'Lights Out in the West Wing', 'deep_lr_solveig', 36,
      'The morays come to Lanternrest to put its lamp out, one dark corridor at a time. Defeat six gnashing morays in the corridors round the camp, and Solveig will keep the light.',
      [('kill', 'moray', 'Defeat Gnashing Morays', 6)], requires='deep_anglers'),
    Q('deep_lr_teeth', 'Teeth for the Brine Stall', 'deep_lr_trader', 37,
      'Eira grinds moray teeth into needles and sells the needles to every net-mender in Keelhaven. She is short. Bring her five Moray Teeth.',
      [('bring', 'moray_tooth', 'Bring Moray Teeth', 5)], requires='deep_lr_glow'),
    Q('deep_lr_lamp', 'The Great Lantern', 'deep_lr_torvald', 37,
      'In the room east of Lanternrest hangs the Great Lantern, the one fixed point of the west wing. Walk to it, look at what it shows you, and put three lantern anglers down on the way: they hang round the light like moths.',
      [('visit', 'deep_lr_lamp', 'Reach the Great Lantern', 1), ('kill', 'angler', 'Defeat Lantern Anglers', 3)], requires='deep_lr_glow'),
    Q('deep_lr_sirens', 'The Siren Row', 'deep_lr_torvald', 38,
      'Beyond the Great Lantern the corridors fill with sirens, and Torvald loses runners there. Defeat four of them and he will run the row again.',
      [('kill', 'siren', 'Defeat Sirens', 4)], requires='deep_lr_lamp'),
    # Gatewatch, a camp on the east rim of the Net
    Q('deep_gw_shells', 'Shells at the Gate', 'deep_gw_bergljot', 39,
      'The shellbacks in the corridors round Gatewatch have started to sit on the way up to Astralhollow. Defeat five of them so the gate is clear.',
      [('kill', 'shellback', 'Defeat Shellbacks', 5)], requires='deep_shellbacks'),
    Q('deep_gw_plates', 'Plate for the Reef-Smith', 'deep_gw_trader', 39,
      'Hallbjorn cuts shellback plate into bars and Gunnhild sells the bars to the whole Deep. Bring her five Shellback Plates.',
      [('bring', 'shellback_plate', 'Bring Shellback Plates', 5)], requires='deep_gw_shells'),
    Q('deep_gw_vents', 'The Vent Garden', 'deep_gw_hallbjorn', 40,
      'West of the camp the vents breathe warm water into a garden of reef, and the sirens sing over it. Walk to the Vent Garden, look at what Hallbjorn can use, and defeat three sirens on the way.',
      [('visit', 'deep_gw_vents', 'Reach the Vent Garden', 1), ('kill', 'siren', 'Defeat Sirens', 3)], requires='deep_gw_shells'),
    Q('deep_gw_gate', 'The Way to Astralhollow', 'deep_gw_bergljot', 40,
      'The way up to Astralhollow opens on the east wall, ten steps from the camp. Bergljot wants a hero to walk to it and see what stands on the far side: stand at the gate and defeat two shellbacks on the way.',
      [('visit', 'deep_pad_astral', 'Stand at the Way to Astralhollow', 1), ('kill', 'shellback', 'Defeat Shellbacks', 2)], requires='deep_gw_vents'),
    # Drownwatch, a camp in the open Shallows
    Q('deep_dw_draugr', 'The Chapel Dead', 'deep_dw_ottilia', 35,
      'The Drowned Chapel is east of Drownwatch, and its dead have got up for the service. Defeat six draugr in the Shallows round the camp.',
      [('kill', 'draugr', 'Defeat Drowned Draugr near Drownwatch', 6)], requires='deep_welcome'),
    Q('deep_dw_coins', 'Coins for the Salt Stall', 'deep_dw_trader', 36,
      'Rannveig buys the green, furred coins the draugr were buried with, and sells them back to the families. Bring her five Drowned Coins.',
      [('bring', 'drowned_coin', 'Bring Drowned Coins', 5)], requires='deep_dw_draugr'),
    Q('deep_dw_stones', 'Counting the Salt Stones', 'deep_dw_skuli', 36,
      'South of Drownwatch stand the Salt Stones, one for every sailor the Net let go. Walk to them, count what the draugr have knocked down, and put three of the dead to rest while you are there.',
      [('visit', 'deep_dw_stones', 'Reach the Salt Stones', 1), ('kill', 'draugr', 'Defeat Drowned Draugr', 3)], requires='deep_dw_draugr'),
    Q('deep_dw_bounty', 'The Drownwatch Bounty', 'deep_dw_ottilia', 37,
      'Ottilia pays for every beast that is put down in the Shallows. Defeat ten enemies anywhere in Rán\'s Deep and return to her. This bounty can be repeated.',
      [('kill', 'any', "Defeat Rán's Deep enemies", 10)], requires='deep_dw_stones', repeatable=True),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'deep_draugr': dict(description='On the open sea floor round Keelhaven, the Wreck of Naglfar to the east and the Drowned Chapel beyond it, the drowned dead have got up. Defeat six draugr and tell Halla.'),
    'deep_longship': dict(description='East of Keelhaven, across the open Shallows, lies the Naglfar, the ship of the dead, made of the nails of the unburied. Walk to the wreck, see whether anything is left aboard, and put three draugr to rest on the way.'),
    'deep_harbour': dict(description='Three tidebells still stand in the Shallows round Keelhaven: one west of the camp, one at the Pearl Gate in front of the Net, one east. Each bell rings for thirty-five seconds after you walk into its circle. '
                                     'Ring all three so that they sound together, and the harbour will sing again. Walk to a bell and the count starts; a bell that falls silent takes its share of the count with it.'),
    'deep_chapel': dict(description='At the east end of the Shallows the old harbour chapel still stands under the water, and nobody has been inside since the draugr came. Walk to the chapel and put three draugr to rest on the way.'),
    'deep_captain': dict(description='Hvitserk Black-Coat captained the Naglfar when she sank, and he never left the deck: he stands in the open Shallows east of the wreck with his axe in his fist and his whole crew behind him in the mud. '
                                     'He swings like a ship coming about. Do not go alone: bring two friends, or take the quest and I will hire you the fighters you lack, for a fee that grows with your level. Return to me for a level-35 blue Amber Ring, usable by every class.'),
    'deep_anglers': dict(description='The first rooms of the Net, the maze of coral north of the Pearl Gate, are home to the lantern anglers: fish that shoot beads of light. Go through the Pearl Gate and defeat six of them.'),
    'deep_morays': dict(description='Deeper in the Net, past the first turns and Lanternrest, live the gnashing morays, eels as long as a longship that strike from the coral without warning. Defeat six of them.'),
    'deep_sirens': dict(description='Deeper in the Net sing the sirens, Rán\'s handmaidens, and the song hurts. They shoot it, in three bolts, from a distance. Defeat six of them before they sing the Net into your head.'),
    'deep_net': dict(description='Sigmund hung four bells inside the Net when it was young and the corridors were short, and the coral has grown round them since. Find them: they stand in the middle rooms, where the morays and the sirens live. '
                                 'Each rings for forty-five seconds once you reach its circle, and all four must ring together. Learn the way between them first, and then run it. Sigmund gives a level-35 blue pair of Wayfarer Pants.'),
    'deep_shellbacks': dict(description='In the deepest corridors of the Net, and round Gatewatch on its east rim, live the shellbacks, turtles the size of a house with plates like a drowned hull. Their slam is felt through the floor. Defeat six of them.'),
    'deep_ghostmaw': dict(description='The Ghostmaw prowls the deep corridors of the Net: a pale moray older than the Net. Take two friends, or hire the fighters you need from me for a fee that grows with your level. Defeat it and return with word that the passage is safe. I will give you a blue Nacreous Moonstone Necklace.'),
}

NPC_UPDATES = {
    'deep_halla': 'I have walked the Shallows every day for thirty years, and the dead have started walking back. Draugr, they call them: our own drowned, up out of the Naglfar with their coins still in their pockets. '
                  'Some of them I knew. Thin them out, bring me what they carry, and walk east to the old wreck for me; I would like to know the Naglfar is empty, even if it is not.',
}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    master = next(n for n in zone['npcs'] if n['id'] == 'travel_keelhaven')
    healer = next(n for n in zone['npcs'] if n['id'] == 'deep_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'deep_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        out.append(dict(id=s['id'], name=s['name'], role=s['role'], x=round(h['x'] + s['dx'], 2), y=round(h['y'] + s['dy'], 2), color=s['color'], dialogue=s['dialogue'],
                        offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look']))
    keys = list(hamlets)
    for key in keys:
        h = hamlets[key]
        t = copy.deepcopy(master)
        t.update(id=f'travel_{key}', x=round(h['x'] - 1, 2), y=round(h['y'] + 3.5, 2), travelStop=h['name'],
                 travelLinks=['travel_keelhaven'] + [f'travel_{k}' for k in keys if k != key])
        out.append(t)
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_8_keelhaven')
    for key, (dx, dy) in {'lanternrest': (2.5, 2), 'gatewatch': (-2.5, 2), 'drownwatch': (6.5, 2)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_8_{key}', x=round(h['x'] + dx, 2), y=round(h['y'] + dy, 2))
        out.append(m)
    links = [l for l in master['travelLinks'] if l not in {f'travel_{k}' for k in keys}]
    master['travelLinks'] = links + [f'travel_{k}' for k in keys]
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Rán's Deep entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 8]
    names = {'travel_keelhaven': 'Keelhaven'}
    for key, h in hamlets.items():
        names[f'travel_{key}'] = h['name']
    for master, hub in names.items():
        key = master.split('travel_')[1]
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_8_{key}')
        m = next(n for n in zone['npcs'] if n['id'] == master)
        directory.append(dict(id=box['id'], zone=8, hub=hub, x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
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
