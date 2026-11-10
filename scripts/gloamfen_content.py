"""Gloamfen's outposts, people and quests. Data for scripts/gloamfen_design.py (shaped coordinates).

Every old `fen_*` / `es_*` quest id stays (saved progress, tests, quest_gear_rewards): their text, giver and targets are rewritten so the chain walks the
whole fen instead of sitting in Lanternmere. New ids and people start with `fen_`. Every quest is level 15-20, rewardXp = levels.txt[level-1] / 10.
Rule for elites (owner): three per zone, two with a quest, one without: the Gloomroot Colossus (old) and `bellowmaw` with, `rustmarshal` without.
Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(15, 21)}
GOLD = {15: 320, 16: 380, 17: 440, 18: 520, 19: 600, 20: 700}

ELITES = [('gloomroot', 231.8, 180.8), ('bellowmaw', 46, 62), ('rustmarshal', 198, 128)]

HUT = dict(r=0, width=3.4, depth=3.2)

# (kind, dx, dy, extra) around each outpost's plaza
DRESSING = {
    'reedhallow': [
        ('house', -9, -6, dict(HUT, label='Bank Hall', color='#5f7f6a')), ('house', 9, -8, dict(HUT, label='Eel House', color='#6b6f5a')),
        ('tent', -10, 6, dict(r=1.5, width=3, depth=2.4, color='#6f8f6a', label='Bunks')),
        ('stall', -5, 3, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Peat & Provisions')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Reedhallow')),
        ('campfire', 4, -3, dict(r=.65)), ('bench', 6, -5, dict(r=0, width=1.5, depth=.45)),
        ('barrels', -3, 6, dict(r=0, width=.6, depth=.6, color='', label='')), ('barrels', -2, 7, dict(r=0, width=.6, depth=.6, color='', label='')),
        ('lamp', -4, -3, dict(r=.18)), ('lamp', 6, -2, dict(r=.18)),
    ],
    'dikewatch': [
        ('house', -8, -5, dict(HUT, label='Dike Hall', color='#5f7a8f')), ('house', 8, -5, dict(HUT, label='Salvage Shed', color='#7a6f5a')),
        ('tent', 8, 5, dict(r=1.5, width=3, depth=2.4, color='#6f8aa0', label='Crews')),
        ('stall', -5, 4, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Tar & Rope')),
        ('noticeboard', 2, -5, dict(r=.4, width=1.3, depth=.4, label='Dikewatch')),
        ('campfire', 3, 3, dict(r=.65)), ('brazier', -2, 0, dict(r=.4)),
        ('lamp', -4, 0, dict(r=.18)), ('lamp', 5, 1, dict(r=.18)),
        ('barrels', -9, 4, dict(r=0, width=.6, depth=.6, color='', label='')),
    ],
    'lastlight': [
        ('house', 9, -6, dict(HUT, label='Garrison Hall', color='#5a6f8a')), ('house', 10, 6, dict(HUT, label='Gravekeeper', color='#6a6a7a')),
        ('tent', -10, 7, dict(r=1.5, width=3, depth=2.4, color='#6f7f9a', label='Watch')),
        ('stall', -6, 5, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Lamp Oil & Rations')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label="Garrison's Rest")),
        ('brazier', -2, -1, dict(r=.4)), ('brazier', 2, 3, dict(r=.4)), ('lamp', -5, 2, dict(r=.18)), ('lamp', 5, 1, dict(r=.18)),
    ],
}

NPCS = [
    dict(id='fen_rh_brid', hamlet='reedhallow', dx=-3, dy=-1, name='Warden Brid Reedhall', role='Bank warden', color='#6f9a78',
         look=dict(skin='#c99b7a', hair='#3a4a3a', style='long', hat='hood', hatColor='#4f6f58'),
         dialogue='The toads were a nuisance when I was a girl. Now they sing so loud the wicks gutter, and the biggest of them sings loudest, out in the wet ground at the north end of the bank.'),
    dict(id='fen_rh_sten', hamlet='reedhallow', dx=5, dy=3, name='Sten Mudfoot', role='Angler', color='#8a7a5a',
         look=dict(skin='#d9b08c', hair='#7a6a4a', style='short', hat='hood', hatColor='#6a5a4a'),
         dialogue='I fish the Shorewalk from a punt. A crocodile took the punt, so now I fish from the bank and I have opinions about crocodiles.'),
    dict(id='fen_rh_trader', hamlet='reedhallow', dx=-5, dy=4.6, name='Gudrun Peatbarrow', role='Outpost trader', color='#a87a45', trader=True,
         look=dict(skin='#edc5a1', hair='#b89a6a', style='long', hat='none', hatColor='#a87a45'),
         dialogue='Tonics, stew and a fair count. Everything on my shelf has been carried the length of the Pilgrim Plank, so wipe your boots.'),
    dict(id='fen_dk_magnus', hamlet='dikewatch', dx=-3, dy=-1, name='Dikereeve Magnus Saltbrow', role='Dikereeve', color='#6f8aa8',
         look=dict(skin='#c99b7a', hair='#d8d8d8', style='short', hat='hood', hatColor='#4f6f8f'),
         dialogue='My grandfather raised this dike, and the crocodiles undo it a stone at a time. Hold the shore and I keep the water on the other side of the stones.'),
    dict(id='fen_dk_linnea', hamlet='dikewatch', dx=5, dy=3, name='Linnea Wrackhand', role='Salvager', color='#8a7a6a',
         look=dict(skin='#b98a6a', hair='#3a3028', style='long', hat='none', hatColor='#6a5a4a'),
         dialogue='The Mere keeps everything it swallows, but the shore gives some of it back. Armour, mostly, and sometimes the person who was wearing it.'),
    dict(id='fen_dk_trader', hamlet='dikewatch', dx=-6, dy=5.6, name='Ingeborg Tarpot', role='Outpost trader', color='#7a8aa0', trader=True,
         look=dict(skin='#edc5a1', hair='#8a4a2a', style='long', hat='none', hatColor='#7a8aa0'),
         dialogue='Tar, rope, salt fish and tonics. If it floats, I sell it. If it sinks, I sell the rope you will need to get it back.'),
    dict(id='fen_gr_ysolde', hamlet='lastlight', dx=-4, dy=1, name='Captain Ysolde Ironwake', role='Garrison captain', color='#6a7a9a',
         look=dict(skin='#d9b08c', hair='#aaaaaa', style='short', hat='hood', hatColor='#4a5a7a'),
         dialogue='The fort north of here was mine before the Mere rose. My soldiers did not leave when it did. I would like them to rest. I would like it more if I did not have to be the one to ask.'),
    dict(id='fen_gr_per', hamlet='lastlight', dx=4, dy=2, name='Per Fenmark', role='Surveyor', color='#8a8a7a',
         look=dict(skin='#edc5a1', hair='#2a2a3a', style='short', hat='hood', hatColor='#6a6a5a'),
         dialogue='I have mapped every bank of the Mere but the island, because the island has heads. I would like to stand on it with my instruments, and I would like someone to stand beside me while I do.',
         escort=dict(quest='fen_gr_chart', **{'class': 'hunter'}, female=False, hairColor=2, skin=1, level=19, speed=2.5,
                     route=[[214, 152], [205, 141], [190, 134], [178, 128], [178, 140], [178, 155], [178, 170], [163, 170], [150, 172], [146, 182]],
                     ambush=[dict(at=[180, 146], r=11, tag='fen_gr_per#road')])),
    dict(id='fen_gr_trader', hamlet='lastlight', dx=-6, dy=6.6, name='Alvar Graveroot', role='Gravekeeper & trader', color='#6a6a8a', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#6a6a8a'),
         dialogue='Lamp oil, stew, a blessing for the road. I bury what the fen gives up and sell what it does not need. Both of those are honest work.'),
]

PLACES = [
    dict(id='fen_ford', name='The Plank Ford', x=178, y=104, r=4),
    dict(id='fen_reedford', name='The Reed Ford', x=210, y=105, r=4),
    dict(id='fen_mouth', name='The Mere Mouth', x=153, y=126, r=4),
    dict(id='fen_garrison', name='The Drowned Garrison', x=206, y=126, r=7),
    dict(id='fen_isle', name='Hydra Isle', x=148, y=166, r=6),
    dict(id='fen_wick_m', name='The Failing Wicks', x=86, y=128, r=2.1, waves=[dict(at=1, tag='fen_wick_m#a'), dict(at=11, tag='fen_wick_m#b')]),
    dict(id='fen_breach_m', name='The Dike Breach', x=176, y=240, r=2.1, waves=[dict(at=1, tag='fen_breach_m#a'), dict(at=11, tag='fen_breach_m#b')]),
    dict(id='fen_quarter', name='The Old Quarter', x=118, y=62, r=6),
    dict(id='fen_culvert', name='The Dry Culvert', x=238, y=100, r=4),
    dict(id='fen_wreck', name='The Ferry Wreck', x=150, y=270, r=5),
]

# Sleepers woken by a wave or an escort ambush
AMBUSH = [('toad', 80, 122, 'fen_wick_m#a'), ('toad', 92, 134, 'fen_wick_m#a'), ('croc', 80, 134, 'fen_wick_m#b'), ('croc', 92, 124, 'fen_wick_m#b'),
          ('croc', 170, 236, 'fen_breach_m#a'), ('croc', 182, 244, 'fen_breach_m#a'), ('knight', 170, 245, 'fen_breach_m#b'), ('toad', 182, 236, 'fen_breach_m#b'),
          ('knight', 186, 140, 'fen_gr_per#road'), ('croc', 188, 152, 'fen_gr_per#road')]


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
    # Reedhallow, on the west bank
    Q('fen_rh_gland', 'Glands for the Wicks', 'fen_rh_brid', 15,
      'Toad gland oil burns slow and bright, and the bank lanterns burn nothing else. Bring Brid four glands.',
      [('bring', 'toad_gland', 'Bring toad glands', 4)], requires='fen_welcome'),
    Q('fen_rh_wicks', 'The Failing Wicks', 'fen_rh_brid', 16,
      'The lanterns along the plank south of Reedhallow have gone dark one after another. Stand by the last of them for twenty seconds while Brid relights it, and keep whatever rises out of the reeds off her.',
      [('hold', 'fen_wick_m', 'Guard the failing wicks', 20)], requires='fen_rh_gland'),
    Q('fen_rh_pike', 'Pike Without Teeth', 'fen_rh_sten', 17,
      'Crocodiles have driven every pike off the Shorewalk, and nobody can eat a crocodile. Defeat six along the shore between the coast and the Mere.',
      [('kill', 'croc', 'Defeat crocodiles on the Shorewalk', 6)], requires='fen_crocs'),
    Q('fen_rh_bellow', 'Bellowmaw', 'fen_rh_brid', 20,
      'A toad the size of a boat has been bellowing in the wet ground north of Reedhallow since the spring rains, and every toad on the bank sings back. Brid wants it quiet, and she says nobody should try this alone.',
      [('kill', 'bellowmaw', 'Defeat Bellowmaw', 1)], requires='fen_rh_wicks', recommendedPlayers=3),
    # Dikewatch, on the south shore
    Q('fen_dk_hides', 'Hides for the Dike', 'fen_dk_magnus', 17,
      'A dike laced with crocodile hide holds ten years longer than one without. Bring Magnus four hides.',
      [('bring', 'croc_hide', 'Bring crocodile hides', 4)], requires='fen_crocs'),
    Q('fen_dk_breach', 'The Dike Breach', 'fen_dk_magnus', 18,
      'The dike has broken east of the village, and the Mere is coming through. Stand in the breach for twenty seconds while the crews drive the stakes, and let nothing from the water or the mud stop them.',
      [('hold', 'fen_breach_m', 'Guard the dike breach', 20)], requires='fen_dk_hides'),
    Q('fen_dk_wreck', 'The Ferry Wreck', 'fen_dk_linnea', 18,
      'The old ferry lies on the strand at the south tip, half in the sand, and the crocodiles nest in her hold. Walk down and see what is left, and defeat five crocodiles on the way.',
      [('visit', 'fen_wreck', 'Reach the Ferry Wreck', 1), ('kill', 'croc', 'Defeat crocodiles on the dikes', 5)], requires='fen_dk_hides'),
    Q('fen_dk_salvage', 'Armour from the Silt', 'fen_dk_linnea', 19,
      'Linnea pays well for drowned gauntlets: the steel is good and the leather is rotten, so she only wants the steel. Bring her three.',
      [('bring', 'drowned_gauntlet', 'Bring drowned gauntlets', 3)], requires='fen_knights'),
    # Garrison's Rest, east of the Mere
    Q('fen_gr_fort', 'The Fort North of Here', 'fen_gr_ysolde', 18,
      "Captain Ysolde's old fort stands to the north, on the ground between the stream and the Rest, and her drowned soldiers still keep its walls. Walk into the Drowned Garrison and defeat four of them.",
      [('visit', 'fen_garrison', 'Enter the Drowned Garrison', 1), ('kill', 'knight', 'Defeat drowned knights', 4)], requires='fen_crocs'),
    Q('fen_gr_gauntlets', 'Gauntlets for the Gravekeeper', 'fen_gr_trader', 18,
      'Alvar buries what the fen gives up, but a fallen knight leaves his gauntlets behind and he cannot bury those. Bring him four.',
      [('bring', 'drowned_gauntlet', 'Bring drowned gauntlets', 4)], requires='fen_knights'),
    Q('fen_gr_chart', 'Charting Hydra Isle', 'fen_gr_per', 19,
      'Per wants to stand on the island in the Mere and draw it. Speak to him at the Rest and walk with him along the east shore and over the causeway to the isle. If he falls, or you do, start again.',
      [('escort', 'fen_gr_per', 'Walk Per to Hydra Isle', 1)], requires='fen_gr_fort'),
    Q('fen_gr_fangs', 'Fangs for the Surveyor', 'fen_gr_per', 20,
      'A hydra fang holds a drafting pen steady better than anything else Per has tried, which says more about hydras than it does about pens. Walk out to Hydra Isle and bring him three.',
      [('visit', 'fen_isle', 'Reach Hydra Isle', 1), ('bring', 'hydra_fang', 'Bring hydra fangs', 3)], requires='fen_hydra'),
    # Lanternmere
    Q('fen_runs', 'Three Lantern Runs', 'fen_reeve', 16,
      'Osric has lantern oil for all three outposts. Carry it to Brid at Reedhallow, Magnus at Dikewatch and Ysolde at Garrison\'s Rest. Each outpost has a Travel Master: speak to them and you can fly back.',
      [('talk', 'fen_rh_brid', 'Deliver to Brid at Reedhallow', 1), ('talk', 'fen_dk_magnus', 'Deliver to Magnus at Dikewatch', 1), ('talk', 'fen_gr_ysolde', "Deliver to Ysolde at Garrison's Rest", 1)],
      requires='fen_welcome'),
    Q('fen_walk', 'The Long Plank', 'fen_ranger', 17,
      'Two fords carry the roads over the stream, with the Mere Mouth between them, and Tilda wants to know that all three still hold. Walk to the Plank Ford, the Mere Mouth and the Reed Ford, in that order.',
      [('visit', 'fen_ford', 'Cross the Plank Ford', 1), ('visit', 'fen_mouth', 'Reach the Mere Mouth', 1), ('visit', 'fen_reedford', 'Cross the Reed Ford', 1)], requires='fen_toads'),
    Q('fen_quarter', 'The Old Quarter', 'fen_lamplighter', 16,
      'West of the town, on the brown clay, stood the first Lanternmere, and its lamps were never put out, only left. Walk to the Old Quarter and thin the toads that live in its foundations.',
      [('visit', 'fen_quarter', 'Reach the Old Quarter', 1), ('kill', 'toad', 'Defeat toads in the Old Quarter', 5)], requires='fen_relight'),
    Q('fen_culvert', 'Where the Stream Went', 'fen_scholar', 18,
      'The stream that runs under Lanternmere stops at an old culvert in the east and does not come out the other side. Walk to the Dry Culvert and tell Pell what you see.',
      [('visit', 'fen_culvert', 'Reach the Dry Culvert', 1)], requires='fen_toads'),
]

# Old ids, new meaning: (fields to replace)
REWRITES = {
    'fen_welcome': dict(description='Meet Lamplighter Wren, Sister Maren, Trader Torvald, Ranger Tilda, Scholar Pell and Ferryman Odd, then report to Reeve Osric. The fen is bigger than it looks: a black stream, a Mere shaped like a C round a green isle, three outposts and a thicket nobody has crossed.'),
    'fen_toads': dict(description='Follow the Pilgrim Plank west out of town and defeat five Fen Toads on the Singing Bank. Return to Tilda.'),
    'fen_toad_sweep': dict(npc='fen_rh_brid', description='The toads sing louder every night, all the way up the west bank. Defeat ten Fen Toads so the lanterns survive until dawn.'),
    'fen_relight': dict(description='Wren cannot keep the lanterns on the Commons lit through the fog the toads breed. Defeat six Fen Toads for her.'),
    'fen_crocs': dict(description='Where the stream falls into the Mere, and along the Shorewalk beyond it, the Mire Crocodiles patrol the shallows. Defeat four and tell Tilda what you saw.'),
    'fen_croc_hunt': dict(npc='fen_dk_magnus', description='The south shore must be safe before the dike crews can mend the dike. Defeat eight Mire Crocodiles on the Southern Dikes.'),
    'fen_ferry': dict(description='Odd needs the west bank and the Mere Mouth quiet before he will pole a boat again. Clear five Fen Toads and three Mire Crocodiles.'),
    'fen_knights': dict(description='East of the Mere the old fort\'s garrison still keeps watch, drowned and rusted. Defeat three Drowned Knights in the Drowned Garrison and bring Pell their number.'),
    'fen_rest': dict(description='Sister Maren will say the words if you can give the dead their peace. Defeat six Drowned Knights in the Garrison and the mire beyond it.'),
    'fen_drowned_watch': dict(description='Crocodiles in the shallows, knights in the ruins: Wren wants both thinned before she lights the eastern lamps. Defeat four of each.'),
    'fen_hydra': dict(description='Cross the causeway to Hydra Isle in the middle of the Mere and defeat two Mire Hydras. Pell must know what lives there.'),
    'fen_hydra_hunt': dict(description='Osric wants the isle cleared for good. Defeat four Mire Hydras on Hydra Isle and in the mire, and report back.'),
    'fen_vanguard': dict(description='Prove you can hold the whole fen: defeat two of every Gloamfen monster and report to Osric.'),
    'fen_gloomroot': dict(description='In the south-eastern corner of the fen, in the Gloomroot Mire past Garrison\'s Rest, a drowned willow has grown into a giant: the Gloomroot Colossus, its heart burning cyan. It crushes a lone hero in a few blows, and two do not do much better. Bring four companions, five adventurers of level 20 with someone to hold it, someone to heal and the rest to hit hard. All five accept this quest and damage the Colossus; stay alive and close when it falls. Return to Reeve Osric for a guaranteed blue Celestial Amber Ring, usable by every class.'),
    'fen_bounty': dict(description='Defeat ten enemies anywhere in Gloamfen and return to Torvald. This patrol can be repeated.'),
    'fen_supplies': dict(description='Clear three Fen Toads and three Mire Crocodiles for the next supply cart. Torvald offers this contract again after each turn-in.'),
    'fen_deep_patrol': dict(description='Odd pays for every Drowned Knight and every hydra that stays down. Defeat four Drowned Knights and one Mire Hydra. Repeatable.'),
    'fen_onward': dict(description='Something has started to glow at the heart of the glacier. Cross the Rimeveil border at the north of Gloamfen, walk down to Lanternmere and report to Reeve Osric.'),
}

NPC_UPDATES = {
    'fen_reeve': 'Lanternmere keeps its lanterns lit all night, and every night the dark fen takes a few more. Toads on the west bank, crocodiles along the Mere, drowned knights in the garrison to the east, and something with many heads out on the isle. Three outposts hold the far edges: Reedhallow, Dikewatch and Garrison\'s Rest. Speak to everyone in town, then report to me. The Gloomroot Colossus waits in the south-eastern mire for five heroes together.',
    'fen_ranger': 'Follow the planks and stay on them. The west bank is toad country, the Mere\'s shore belongs to the crocodiles, and the black water takes anyone who steps off the boards. Every stream has a ford: find it.',
    'fen_scholar': 'There was a fort east of the Mere before the water rose. Its garrison still stands watch, knee-deep in the shallows. And the isle in the middle: nobody who went to see it has come back to say what lives there. Nobody has told me where the stream goes, either.',
    'fen_ferryman': 'I ran the ferry across the Mere for forty years, until the isle woke up. Now the causeway on the east shore is the only way across, and I will not walk it. Clear the road and I will owe you a ride.',
}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    master = next(n for n in zone['npcs'] if n['id'] == 'travel_lanternmere')
    healer = next(n for n in zone['npcs'] if n['id'] == 'fen_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'fen_trader')['offers']
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
    spots = {'reedhallow': (-1, 2), 'dikewatch': (-1, 5), 'lastlight': (1, -2)}
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(master)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=['travel_lanternmere'])
        out.append(t)
        if t['id'] not in master['travelLinks']:
            master['travelLinks'].append(t['id'])
    # every hub has a mailbox (scripts/mailboxes.py ran on the old square, before the outposts exist)
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_3_lanternmere')
    for key, (dx, dy) in {'reedhallow': (3, 1), 'dikewatch': (2, 1), 'lastlight': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_3_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square, where the outposts do not exist yet."""
    directory = [d for d in json.loads(path.read_text()) if not (d['zone'] == 3 and d['hub'] in {h['name'] for h in hamlets.values()})]
    for key, h in hamlets.items():
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_3_{key}')
        master = next(n for n in zone['npcs'] if n['id'] == f'travel_{key}')
        directory.append(dict(id=box['id'], zone=3, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=master['x'], y=master['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(zone, hamlets):
    # idempotent, so `plan` also works on a map that already carries the design
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
    zone['camps'] = camps(hamlets)
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
