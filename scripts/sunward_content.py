"""Sunward Vale's hubs, people, quests and places. Data for scripts/sunward_design.py (shaped coordinates, zone 20).

Owner request 2026-11-09: "for pilot. reshape sunward vale. and remake the zone and quests to fit the new shape. no fillers. a wall with a vault opening towards yearwheel". Owner answers
(AskUserQuestion): EVERY shaped neighbour is a seam (the Stormglass Flats, the Ribbonwild, the Tanglecrown, the Veyrroot Canopy, the Lapis Erg and the Frostwake Shelf; the Stormglass outpost
Bankhold moves inland for it), keep Old Honeyjaw and the Wicker Warden and add one new elite with no quest (the Harrow Ox), a wall with a vault opening towards the Yearwheel, rebuild the town
and add three outposts.

The old Sunward people stay (their ids are saved progress and the Spark network): the miller, herbalist, bridge carpenter, orchard guide and provisioner in Millbridge, the Elder Hollow keeper
and the Meeting Stone in Elderroot Camp. Every old `sun_*` id and `es_16` stays; texts are rewritten only where the geography changed. Fourteen quests are new: new ids start `svs_`, new
people `sv_` and stay within 19 characters (the accept string is capped at 32). Levels 65-70, rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(65, 72)}
GOLD = {65: 5800, 66: 6200, 67: 6600, 68: 7000, 69: 7400, 70: 7800}

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is Millbridge; the three outposts are camps. Nothing art-less and nobody may stand within 20 tiles of a seam.
HAMLETS = {
    'millbridge':  dict(name='Millbridge', x=126, y=201, hw=22, hh=17, city=True),
    'honeywood':   dict(name='Honeywood Steading', x=92, y=72, hw=12, hh=11),
    'wickerfield': dict(name='Wickerfield Post', x=236, y=94, hw=12, hh=11),
    'elderroot':   dict(name='Elderroot Camp', x=176, y=66, hw=12, hh=11),
}

# kind, x, y: Old Honeyjaw in the north-western oakwood and the Wicker Warden in the north-eastern fields (both with a quest, as before), the Harrow Ox on the southern pastures (no quest)
ELITES = [('honeyjaw', 62, 50), ('wickerwarden', 290, 78), ('harrowox', 208, 282)]
AWARENESS = {'honeyjaw': 13., 'wickerwarden': 15., 'harrowox': 16.}

LODGE = dict(r=0, width=5, depth=4)       # the vale house: Greenmeadow's isometric `meadow_cottage` (client/meadowart.js) in the 'thatch' (limewash, timber, thatch) or 'stone' style
BOARD = dict(r=.4, width=1.3, depth=.4)
BENCH = dict(r=0, width=1.5, depth=.45)

# offsets from the plaza
DRESSING = {
    'millbridge': [
        ('meadow_mill', -4, -13.5, dict(r=0, width=6, depth=4)),
        ('meadow_cottage', -17, -5, dict(LODGE, style='thatch', v=0)), ('meadow_cottage', -17, 6.5, dict(LODGE, style='stone', v=1)), ('meadow_cottage', 9, -9, dict(LODGE, style='thatch', v=2)),
        ('meadow_cottage', 16.5, 7, dict(LODGE, style='stone', v=0)), ('meadow_cottage', -6, 11.5, dict(LODGE, style='thatch', v=1)),
        ('noticeboard', 4, 4, dict(BOARD, label='Millbridge')), ('bench', 8, 3.4, BENCH), ('bench', -9, -3.5, BENCH),
        ('stall', 11, -3.5, dict(r=0, width=1.8, depth=1.2, color='#e3b66a', label='Millbridge Market')),
        ('apple_tree', -11.5, -10, dict(r=.9, v=1)), ('apple_tree', 17.5, -10.5, dict(r=.9, v=2)), ('haystack', 20, 11, dict(r=.58, v=1)),
    ],
    'honeywood': [
        ('meadow_cottage', 0, -6.5, dict(LODGE, style='thatch', v=0)), ('meadow_cottage', -6.5, 1, dict(LODGE, style='thatch', v=2)),
        ('noticeboard', 5, -7, dict(BOARD, label='Honeywood Steading')), ('campfire', 3.2, 5.4, dict(r=.65, v=0)), ('bench', 6, -3, BENCH), ('haystack', -9, 6, dict(r=.58, v=0)),
    ],
    'wickerfield': [
        ('meadow_cottage', 0, -6.5, dict(LODGE, style='thatch', v=1)), ('meadow_cottage', -6.5, 1, dict(LODGE, style='thatch', v=0)),
        ('noticeboard', 5, -7, dict(BOARD, label='Wickerfield Post')), ('campfire', 3.2, 5.4, dict(r=.65, v=0)), ('bench', 6, -3, BENCH), ('haystack', -9, 6, dict(r=.58, v=1)),
    ],
    'elderroot': [
        ('meadow_cottage', 0, -6.5, dict(LODGE, style='stone', v=2)), ('meadow_cottage', -6.5, 1, dict(LODGE, style='stone', v=1)),
        ('noticeboard', 5, -7, dict(BOARD, label='Elderroot Camp')), ('campfire', 3.2, 5.4, dict(r=.65, v=0)), ('bench', 6, -3, BENCH), ('apple_tree', -9, 6, dict(r=.9, v=0)),
        ('meetingstone', 7.8, 3.8, dict(r=1.7, v=0)),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy) from the plaza
HUB_NPCS = {'sun_miller': ('millbridge', -4, -9), 'sun_medic': ('millbridge', -14, 4), 'sun_carpenter': ('millbridge', 13, -6), 'sun_guide': ('millbridge', 12, 5.5),
            'sun_trader': ('millbridge', 5, 9), 'sun_keeper': ('elderroot', -3, -1), 'sun_stone': ('elderroot', 9.5, 5.5)}
STATION_PEOPLE = {'travel_millbridge': (-8, 7.5), 'mailbox_20_millbridge': (-10.5, 9.5)}

NPCS = [
    dict(id='sv_hw_marit', hamlet='honeywood', dx=5, dy=3, name='Beekeeper Marit Honeybrook', role='Beekeeper', color='#ffe6a5',
         look=dict(skin='#c99b7a', hair='#7a4a2c', style='long', hat='straw', hatColor='#e2c67e'),
         dialogue='The hives stand along the western oakwood, and the old bear has the whole north of it. Keep your voice low among the hawthorn: the bees mind a stranger less than the bear does.'),
    dict(id='sv_hw_ansgar', hamlet='honeywood', dx=-3, dy=5.6, name='Hive-Warden Ansgar Waxwing', role='Hive warden', color='#ffe6a5',
         look=dict(skin='#a77250', hair='#3f342a', style='short', hat='hood', hatColor='#568054'),
         dialogue='A fox that has tasted honey will chew through any fence. I mend what they break and count what they take.'),
    dict(id='sv_hw_trader', hamlet='honeywood', dx=-6, dy=-3, name='Tolle Combwright', role='Outpost trader', color='#ffe6a5', trader=True,
         look=dict(skin='#d9b08c', hair='#8a8f98', style='short', hat='straw', hatColor='#d6bb70'),
         dialogue='Tonics, stew and a honeycomb for the road. I sell at cost: the Steading keeps the rest.'),
    dict(id='sv_wf_greta', hamlet='wickerfield', dx=5, dy=3, name='Field-Warden Greta Strawmark', role='Field warden', color='#ffe6a5',
         look=dict(skin='#e0b89a', hair='#a84e39', style='long', hat='straw', hatColor='#caa65f'),
         dialogue='Every row has its scarecrow, and one of them has been walking at night. The big wicker one in the north-east fields is not ours. Do not go near it alone.'),
    dict(id='sv_wf_ottar', hamlet='wickerfield', dx=-3, dy=5.6, name='Thresher Ottar Flailsong', role='Thresher', color='#ffe6a5',
         look=dict(skin='#8a6248', hair='#c9c2b4', style='short', hat='straw', hatColor='#aa8659'),
         dialogue='The hares eat the seed corn and the snails eat what the hares leave. I thresh what is left and sing while I do it.'),
    dict(id='sv_wf_trader', hamlet='wickerfield', dx=-6, dy=-3, name='Brita Sheafwife', role='Outpost trader', color='#ffe6a5', trader=True,
         look=dict(skin='#e0b89a', hair='#6a4a3a', style='long', hat='straw', hatColor='#d6bb70'),
         dialogue='Tonics, stew and warm bread for the field crews. I sell at cost: the harvest keeps the rest.'),
    dict(id='sv_er_ingrid', hamlet='elderroot', dx=5, dy=3, name='Rootwalker Ingrid Oakstair', role='Rootwalker', color='#ffe6a5',
         look=dict(skin='#b78865', hair='#d2c39b', style='long', hat='hood', hatColor='#568054'),
         dialogue='The oak above the Hollow door drinks from springs under this camp. I walk the roots every morning and listen. Lately they have been listening back.'),
    dict(id='sv_er_trader', hamlet='elderroot', dx=-6, dy=-3, name='Leif Acornpurse', role='Outpost trader', color='#ffe6a5', trader=True,
         look=dict(skin='#a77250', hair='#5a3a2a', style='short', hat='hood', hatColor='#568054'),
         dialogue='Tonics, stew and spare rope for the root stair. I sell at cost: the oak keeps the rest.'),
]
TRAVEL_NAMES = {'honeywood': 'Travel Master Sunniva', 'wickerfield': 'Travel Master Haldor', 'elderroot': 'Travel Master Embla'}

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each); the old Sunward places keep their ids
PLACES = [
    dict(id='sun_elder_hollow', name='The Elder Hollow', x=176, y=40, r=6),
    dict(id='sun_honeywood', name='Honeywood Clearing', x=96, y=42, r=4),
    dict(id='sun_wicker_field', name='The Wicker Field', x=264, y=62, r=4),
    dict(id='sv_hives', name='The Hawthorn Hives', x=62, y=104, r=6),
    dict(id='sv_ridge', name='Thornback Ridge', x=120, y=116, r=6),
    dict(id='sv_rows', name='The Scarecrow Rows', x=210, y=130, r=6),
    dict(id='sv_barrow', name='The Long Barrow', x=274, y=138, r=6),
    dict(id='sv_orchard', name='The Elder Orchard', x=138, y=96, r=6),
    dict(id='sv_springs', name='The Root Springs', x=208, y=96, r=6),
    dict(id='svs_mb_m', name='The Millbridge Weir', x=84, y=160, r=2.1, waves=[dict(at=1, tag='svs_mb_m#a'), dict(at=11, tag='svs_mb_m#b')]),
    dict(id='svs_hw_m', name='The Honeywood Circle', x=116, y=48, r=2.1, waves=[dict(at=1, tag='svs_hw_m#a'), dict(at=11, tag='svs_hw_m#b')]),
    dict(id='svs_wf_m', name='The Wickerfield Circle', x=262, y=116, r=2.1, waves=[dict(at=1, tag='svs_wf_m#a'), dict(at=11, tag='svs_wf_m#b')]),
    dict(id='svs_er_m', name='The Elderroot Circle', x=208, y=52, r=2.1, waves=[dict(at=1, tag='svs_er_m#a'), dict(at=11, tag='svs_er_m#b')]),
]
ES16 = (190.0, 210.0)             # the Empty Seat's echo circle (chapter 16): east of Millbridge; the foe stands two tiles east of it

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('spadebadger', 78, 154, 'svs_mb_m#a'), ('spadebadger', 90, 166, 'svs_mb_m#a'), ('meadowhare', 78, 166, 'svs_mb_m#b'), ('meadowhare', 90, 154, 'svs_mb_m#b'),
    ('brushfox', 110, 42, 'svs_hw_m#a'), ('brushfox', 122, 54, 'svs_hw_m#a'), ('spadebadger', 110, 54, 'svs_hw_m#b'), ('spadebadger', 122, 42, 'svs_hw_m#b'),
    ('meadowhare', 256, 110, 'svs_wf_m#a'), ('meadowhare', 268, 122, 'svs_wf_m#a'), ('sunbacksnail', 256, 122, 'svs_wf_m#b'), ('sunbacksnail', 268, 110, 'svs_wf_m#b'),
    ('sunbacksnail', 202, 46, 'svs_er_m#a'), ('sunbacksnail', 214, 58, 'svs_er_m#a'), ('spadebadger', 202, 58, 'svs_er_m#b'), ('spadebadger', 214, 46, 'svs_er_m#b'),
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
    # Millbridge
    Q('svs_mb_hold', 'Keep the Weir Clear', 'sun_miller', 66,
      'The old weir across the river west of the mill backs the water up for the wheel, and whenever the badgers dig under it the water drops and the wheel stops. Stand in the circle beside the weir for twenty seconds while Ada clears the sluice, and let nothing reach her.',
      [('hold', 'svs_mb_m', 'Keep the Millbridge Weir Clear', 20)], requires='sun_welcome'),
    Q('svs_rounds', 'The Three Posts', 'sun_miller', 67,
      'Three posts keep the vale beyond Millbridge: the Honeywood Steading in the north-west, the Wickerfield Post in the north-east and Elderroot Camp by the Hollow door in the north. Ada wants their keepers told that the mill is turning again. Speak with Marit, Greta and Rowan, and use the Travel Masters if the road is long.',
      [('talk', 'sv_hw_marit', 'Speak with Marit Honeybrook at the Honeywood Steading', 1), ('talk', 'sv_wf_greta', 'Speak with Greta Strawmark at the Wickerfield Post', 1),
       ('talk', 'sun_keeper', 'Speak with Rowan Alder at Elderroot Camp', 1)], requires='sun_welcome'),
    # Honeywood Steading, in the north-west
    Q('svs_hw_hives', 'Out to the Hawthorn Hives', 'sv_hw_marit', 66,
      'South-west of the Steading the hives stand in a ring of hawthorn, and the foxes have started to prowl round them at dusk. Walk out to the Hawthorn Hives and defeat four Brush Foxes on the way.',
      [('visit', 'sv_hives', 'Reach the Hawthorn Hives', 1), ('kill', 'brushfox', 'Defeat Brush Foxes on the way', 4)], requires='sun_welcome'),
    Q('svs_hw_tufts', 'Tails for the Hive Straps', 'sv_hw_ansgar', 67,
      'Ansgar binds the hive straps with brush-fox tail tuft, which the bees will not sting through. Bring him five Brush Fox Tail Tufts.',
      [('bring', 'fox_tail_tuft', 'Bring Brush Fox Tail Tufts', 5)], requires='svs_hw_hives'),
    Q('svs_hw_hold', 'Hold the Honeywood Circle', 'sv_hw_marit', 67,
      'The smoke pot north-east of the Steading goes out whenever the foxes gather, and then every badger in the oakwood comes to the hives. Stand in the circle beside it for twenty seconds while Marit relights it, and keep them off her.',
      [('hold', 'svs_hw_m', 'Hold the Honeywood Circle', 20)], requires='svs_hw_hives'),
    Q('svs_hw_ridge', 'Along Thornback Ridge', 'sv_hw_marit', 68,
      'South-east of the Steading the ground rises into Thornback Ridge, and the badgers have burrowed it hollow. Walk down to the ridge and defeat five Spadeclaw Badgers there.',
      [('visit', 'sv_ridge', 'Reach Thornback Ridge', 1), ('kill', 'spadebadger', 'Defeat Spadeclaw Badgers on the ridge', 5)], requires='svs_hw_hold'),
    # Wickerfield Post, in the north-east
    Q('svs_wf_rows', 'Down the Scarecrow Rows', 'sv_wf_greta', 67,
      'South-west of the post the scarecrow rows run down to the river, and the hares have been eating them bare. Greta wants a count. Walk down to the Scarecrow Rows and defeat four Meadow Hares on the way.',
      [('visit', 'sv_rows', 'Reach the Scarecrow Rows', 1), ('kill', 'meadowhare', 'Defeat Meadow Hares on the way', 4)], requires='sun_welcome'),
    Q('svs_wf_whiskers', 'Whiskers for the Straw Brushes', 'sv_wf_ottar', 68,
      'Ottar sweeps the threshing floor with a brush of meadow-hare whisker, which gathers every last grain. Bring him five Meadow Hare Whiskers.',
      [('bring', 'hare_whisker', 'Bring Meadow Hare Whiskers', 5)], requires='svs_wf_rows'),
    Q('svs_wf_hold', 'Hold the Wickerfield Circle', 'sv_wf_greta', 68,
      'The harvest bell south-east of the post rings itself whenever the hares gather, and then every snail in the rows crawls towards it. Stand in the circle beside it for twenty seconds while Greta stills the bell, and keep them off her.',
      [('hold', 'svs_wf_m', 'Hold the Wickerfield Circle', 20)], requires='svs_wf_rows'),
    Q('svs_wf_barrow', 'To the Long Barrow', 'sv_wf_greta', 69,
      'South-east of the post the Long Barrow rises out of the fields, and the snails have covered its slope with their shells. Walk to the barrow and defeat five Sunback Snails there.',
      [('visit', 'sv_barrow', 'Reach the Long Barrow', 1), ('kill', 'sunbacksnail', 'Defeat Sunback Snails on the barrow', 5)], requires='svs_wf_hold'),
    # Elderroot Camp, in the north
    Q('svs_er_orchard', 'Into the Elder Orchard', 'sv_er_ingrid', 68,
      'South-west of the camp the old apple rows lean over the road to the mill, and the snails have eaten the windfalls. Walk into the Elder Orchard and defeat four Sunback Snails on the way.',
      [('visit', 'sv_orchard', 'Reach the Elder Orchard', 1), ('kill', 'sunbacksnail', 'Defeat Sunback Snails on the way', 4)], requires='sun_welcome'),
    Q('svs_er_shells', 'Shells for the Root Stair', 'sun_keeper', 69,
      'Rowan crushes the striped snail shells into the mortar between the root stair steps, where nothing else will hold. Bring him five Sunback Shells.',
      [('bring', 'sunback_shell', 'Bring Sunback Shells', 5)], requires='svs_er_orchard'),
    Q('svs_er_hold', 'Hold the Elderroot Circle', 'sv_er_ingrid', 69,
      'The root-bell north-east of the camp rings whenever the badgers dig, and then every claw under the oak comes to it. Stand in the circle beside it for twenty seconds while Ingrid muffles the bell, and keep them off her.',
      [('hold', 'svs_er_m', 'Hold the Elderroot Circle', 20)], requires='svs_er_orchard'),
    Q('svs_er_springs', 'The Root Springs', 'sv_er_ingrid', 70,
      'South-east of the camp the springs that feed the great oak well up through the roots, and the badgers have dug into them. Walk to the Root Springs and defeat five Spadeclaw Badgers there.',
      [('visit', 'sv_springs', 'Reach the Root Springs', 1), ('kill', 'spadebadger', 'Defeat Spadeclaw Badgers at the springs', 5)], requires='svs_er_hold'),
]

# Old ids, new meaning (only where the geography changed): the texts that named no place stay as they were
REWRITES = {
    'sun_hares': dict(description='The unusually bold meadow hares are chewing through the fields beyond the river, east of Millbridge.'),
    'sun_badgers': dict(description='Keep the badgers from undermining the old bridge over the river.'),
    'sun_honeyjaw': dict(description='A bear with a wild hive on its back has claimed the north-western oakwood, beyond the Honeywood Steading. Bring friends.'),
    'sun_warden': dict(description='A towering scarecrow stalks the north-eastern fields, beyond the Wickerfield Post. Gather five companions.'),
    'sun_roots': dict(description='Study the root stair at Elderroot Camp and consult the Meeting Stone before descending.'),
    'sun_hollow_trials': dict(description='Clear the creatures that have taken shelter beneath the elder oak.'),
    'sun_onward': dict(description='Cross into Sunward Vale from the Stormglass Flats or the Ribbonwild and report to Ada Bell at Millbridge.'),
    'es_go_16': dict(description='Speak to Ada Bell in Millbridge at level 68 to continue The Empty Seat: The Harvest of Tomorrow. This direction stays in your journal until you accept that chapter.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {
    'sun_miller': dict(dialogue='The Stormglass road ends west of my wheat. Come in from the wind and follow the river, where the oaks begin. The three posts keep the rest of the vale.'),
    'sun_guide': dict(dialogue='There is a quick path through the western oakwood and a gentle one past the apple rows. Both reach the old crown at the north end of the trunk road.'),
    'sun_carpenter': dict(dialogue='I repair the bridges each spring. I cannot work while badgers are digging beneath their posts.'),
    'sun_keeper': dict(dialogue='The roots have opened. Gather five companions before descending: the heart below has awakened. The Hollow door stands north of this camp.'),
}
TAGLINE = 'A green river valley of old oaks, apple rows and a door beneath the roots: three elites, a mill town, three outposts, six open borders and a wall with a vault towards the Yearwheel'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['sun_medic']['offers']
    supplier = by['sun_trader']['offers']
    hub = by['travel_millbridge']
    box = by['mailbox_20_millbridge']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = [k for k in hamlets if k != 'millbridge']
    spots = {'honeywood': (-1, 3.5), 'wickerfield': (-1, 3.5), 'elderroot': (-1, 3.5)}
    for key in keys:
        dx, dy = spots[key]
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[], name=TRAVEL_NAMES[key])
        out.append(t)
    boxes = {'honeywood': (-3.5, 5.2), 'wickerfield': (-3.5, 5.2), 'elderroot': (-3.5, 5.2)}
    for key in keys:
        dx, dy = boxes[key]
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_20_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Sunward entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 20]
    for key, h in hamlets.items():
        box_id = 'mailbox_20_millbridge' if key == 'millbridge' else f'mailbox_20_{key}'
        box = next(n for n in zone['npcs'] if n['id'] == box_id)
        m = next(n for n in zone['npcs'] if n['id'] == ('travel_millbridge' if key == 'millbridge' else f'travel_{key}'))
        directory.append(dict(id=box['id'], zone=20, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def city_and_camps(hamlets):
    def rect(h):
        return dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                    plaza=dict(x=h['x'], y=h['y']), radius=7 if h.get('city') else 3.5, entry=dict(x=h['x'] - h['hw'] + 4, y=h['y']) if h.get('city') else dict(x=h['x'], y=h['y'] + h['hh'] - 3))
    city = rect(next(h for h in hamlets.values() if h.get('city')))
    return city, [rect(h) for h in hamlets.values() if not h.get('city')]


def install(world, zone, hamlets, old):
    """Idempotent, so `plan` also works on a map that already carries the design."""
    new_npcs = people(world, zone, hamlets, old)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        n.update(copy.deepcopy(NPC_UPDATES.get(n['id'], {})))
    keys = [k for k in hamlets if k != 'millbridge']
    for n in zone['npcs']:
        if n['id'] == 'travel_millbridge':
            n['travelStop'] = hamlets['millbridge']['name']
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + [f'travel_{k}' for k in keys]))
        elif n['id'].startswith('travel_') and n.get('travelStop') in {h['name'] for h in hamlets.values()}:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + ['travel_millbridge'] + [f'travel_{k}' for k in keys if f'travel_{k}' != n['id']]))
    ids = {p['id'] for p in PLACES}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    new = copy.deepcopy(QUESTS)
    ids = {q['id'] for q in new}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids] + new
    zone['city'], zone['camps'] = city_and_camps(hamlets)
    zone['tagline'] = TAGLINE
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
