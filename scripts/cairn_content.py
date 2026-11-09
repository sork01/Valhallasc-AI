"""Cairnspine's hubs, people, quests and places. Data for scripts/cairn_design.py (shaped coordinates, zone 27).

Owner request 2026-11-09: "for pilot. reshape cairnspine. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the Prismwaste ONLY (the
Frostwake Shelf crossing stays a gate until Frostwake is shaped), keep all three elites (Cairn Behemoth, Whitebark Titan, Storm Condor) and add a fourth with no quest (the Avalanche
Bear), keep the Thunderheart Gate door and rebuild the hub, plus three outposts.

The old Cairnspine people stay (their ids are saved progress and the Spark network): the warden, healer, surveyor, trader and peak scout in Boulderwatch, the stone singer at the Singing
Cairn Post, the grove keeper at the Whitebark Post, the windseer and the Meeting Stone at the Stormgate Camp. Every old `cairn_*` and `es_23` id stays; texts are rewritten only where the
geography changed. Fourteen quests are new: new ids start `crn_`, new people `cn_` and stay within 19 characters (the accept string is capped at 32). Levels 90-95, rewardXp =
levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(90, 97)}
GOLD = {90: 10200, 91: 11200, 92: 12200, 93: 13300, 94: 14300, 95: 15300}

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is Boulderwatch; the three outposts are camps.
HAMLETS = {
    'boulderwatch': dict(name='Boulderwatch', x=156, y=170, hw=21, hh=18, city=True),
    'singing':   dict(name='Singing Cairn Post', x=96, y=92, hw=12, hh=11),
    'whitebark': dict(name='Whitebark Post', x=140, y=112, hw=12, hh=11),
    'stormgate': dict(name='Stormgate Camp', x=176, y=58, hw=12, hh=11),
}
THUNDER = (160.0, 30.0)            # the Thunderheart Gate door (a dungeon portal, id kept)
THUNDER_ARRIVAL = (160.0, 37.0)    # where the dungeon's way home puts a hero
CROSS = (97.88, 178.0)             # the Prismwaste seam: the crossing the Prismwaste's own road ends at (its gate stood at (225.88, 150.0))

# kind, x, y: the Cairn Behemoth in the southern toe, the Whitebark Titan in the north-western wood, the Storm Condor on the north-eastern spires (all three with a quest),
# the Avalanche Bear in the north-west hollows (no quest)
ELITES = [('cairnbehemoth', 160, 244), ('whitebarktitan', 130, 48), ('stormcondor', 212, 30), ('avalanchebear', 62, 52)]
AWARENESS = {'cairnbehemoth': 17., 'whitebarktitan': 18., 'stormcondor': 19., 'avalanchebear': 17.}

HALL = dict(r=0, width=4, depth=3)       # the Cairnspine watchhall (isometric City.art): a slate hall with a hip roof
BOARD = dict(r=.4, width=1.3, depth=.4)
BENCH = dict(r=0, width=1.5, depth=.45)

DRESSING = {
    'boulderwatch': [
        ('cairn_watchhall', -16, -3, dict(HALL, v=0)), ('cairn_watchhall', 4, -10, dict(HALL, v=1)), ('cairn_watchhall', -3, 13, dict(HALL, v=2)),
        ('cairn_signal', 5, -4, dict(r=.8, v=0)), ('campfire', -4, 6, dict(r=.65)), ('bench', 9, 2, BENCH),
        ('noticeboard', 3, 4, dict(BOARD, label='Boulderwatch')), ('cairn_windbanner', 14, -5, dict(r=.15, v=0)), ('cairn_windbanner', -14, 8, dict(r=.15, v=1)),
    ],
    'singing': [
        ('cairn_watchhall', 0, -6.5, dict(HALL, v=0)), ('cairn_watchhall', -6, 1, dict(HALL, v=1)),
        ('noticeboard', 5, -7, dict(BOARD, label='Singing Cairn Post')), ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, BENCH), ('cairn_signal', -9, 6, dict(r=.8, v=0)),
    ],
    'whitebark': [
        ('cairn_watchhall', 0, -6.5, dict(HALL, v=1)), ('cairn_watchhall', -6, 1, dict(HALL, v=2)),
        ('noticeboard', 5, -7, dict(BOARD, label='Whitebark Post')), ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, BENCH), ('cairn_signal', -9, 6, dict(r=.8, v=0)),
    ],
    'stormgate': [
        ('cairn_watchhall', 0, -6.5, dict(HALL, v=2)), ('cairn_watchhall', -6, 1, dict(HALL, v=0)),
        ('noticeboard', 5, -7, dict(BOARD, label='Stormgate Camp')), ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, BENCH), ('cairn_signal', -9, 6, dict(r=.8, v=0)),
        ('meetingstone', 7.8, 3.8, dict(r=1.7, v=0)),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy) from the plaza
HUB_NPCS = {'cairn_warden': ('boulderwatch', -2, 1), 'cairn_healer': ('boulderwatch', -12, 5), 'cairn_surveyor': ('boulderwatch', 12, -9), 'cairn_trader': ('boulderwatch', 7, 9),
            'cairn_scout': ('boulderwatch', -10, -8), 'cairn_stonesinger': ('singing', -3, -1), 'cairn_grovekeeper': ('whitebark', -3, -1), 'cairn_windseer': ('stormgate', -3, -1),
            'cairn_stone': ('stormgate', 9.5, 5.5)}
BOULDERWATCH_PEOPLE = {'travel_boulderwatch': (15, 6), 'mailbox_27_boulderwatch': (17.5, 8.5)}

NPCS = [
    dict(id='cn_sc_halvar', hamlet='singing', dx=5, dy=3, name='Rune-Keeper Halvar Greyslate', role='Rune keeper', color='#d4b8aa',
         look=dict(skin='#a77250', hair='#d9d0c2', style='short', hat='hood', hatColor='#786b7c'),
         dialogue='Every singing stone on this height was cut by a keeper who is long dead, and they ring a little flat when the wind turns north. I tune them. The Hollow Peaks are above us, in the north-west, and the Avalanche Bear sleeps there.'),
    dict(id='cn_sc_trader', hamlet='singing', dx=-6, dy=5.6, name='Maren Slateweave', role='Outpost trader', color='#d4b8aa', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a2a', style='long', hat='none', hatColor='#786b7c'),
         dialogue='Tonics, stew and warm wool for the height crews. I sell at cost: the mountain keeps the rest.'),
    dict(id='cn_wb_ingrid', hamlet='whitebark', dx=5, dy=3, name='Wood-Reeve Ingrid Palebark', role='Wood reeve', color='#d4b8aa',
         look=dict(skin='#d9b08c', hair='#1a1a22', style='long', hat='hood', hatColor='#786b7c'),
         dialogue='The Whitebark Wood stands north of the post and nothing in it has a leaf. The ibex graze its edge and the Titan walks its middle. I keep the edge.'),
    dict(id='cn_wb_trader', hamlet='whitebark', dx=-6, dy=5.6, name='Sunniva Ashbark', role='Outpost trader', color='#d4b8aa', trader=True,
         look=dict(skin='#8a6248', hair='#2a2a32', style='short', hat='none', hatColor='#786b7c'),
         dialogue='Bread, tonics and stew for the wood crews. Never sit down under a white tree: ask the reeve why.'),
    dict(id='cn_sg_ragna', hamlet='stormgate', dx=5, dy=3, name='Stormwarden Ragna Thunderhand', role='Storm warden', color='#d4b8aa',
         look=dict(skin='#a87a5a', hair='#c9c2b4', style='short', hat='hood', hatColor='#786b7c'),
         dialogue='The Thunderheart Gate stands at the head of the ridge, north-west of the camp, and the stormlight in its ring does not stay in the ring. The Storm Condor hunts the spires north-east of us. I keep the camp.'),
    dict(id='cn_sg_trader', hamlet='stormgate', dx=-6, dy=5.6, name='Fenrik Coilwire', role='Outpost trader', color='#d4b8aa', trader=True,
         look=dict(skin='#e0b89a', hair='#6a4a3a', style='short', hat='none', hatColor='#786b7c'),
         dialogue='Tonics, stew and rubber boots. Nothing here is sold above cost, and nothing metal should be worn into the ring.'),
]

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each); the old Cairnspine places keep their ids
PLACES = [
    dict(id='cairn_thunder', name='The Thunderheart Gate', x=160, y=36.5, r=5),
    dict(id='cairn_stones', name='Singing Cairn', x=96, y=71, r=5),
    dict(id='cairn_grove', name='Whitebark Grove', x=125, y=88, r=5),
    dict(id='crn_four_turns', name='The Four Turns', x=160, y=136, r=6),
    dict(id='crn_adder_stones', name='The Adder Stones', x=196, y=172, r=6),
    dict(id='crn_wood_edge', name='The Edge of the Whitebark Wood', x=124, y=70, r=6),
    dict(id='crn_spires', name='The Condor Spires', x=192, y=46, r=6),
    dict(id='crn_bw_m', name='The Boulderwatch Brazier', x=120, y=148, r=2.1, waves=[dict(at=1, tag='crn_bw_m#a'), dict(at=11, tag='crn_bw_m#b')]),
    dict(id='crn_sc_m', name='The Singing Circle', x=76, y=78, r=2.1, waves=[dict(at=1, tag='crn_sc_m#a'), dict(at=11, tag='crn_sc_m#b')]),
    dict(id='crn_wb_m', name='The Whitebark Circle', x=118, y=124, r=2.1, waves=[dict(at=1, tag='crn_wb_m#a'), dict(at=11, tag='crn_wb_m#b')]),
    dict(id='crn_sg_m', name='The Stormgate Circle', x=200, y=70, r=2.1, waves=[dict(at=1, tag='crn_sg_m#a'), dict(at=11, tag='crn_sg_m#b')]),
]
BELLS_SHIFT = (40.0, -3.0)         # the Empty Seat's three oath bells move rigidly with the Singing Cairn (old circle (56, 69), new (96, 66)); old bells (52..66, 62)

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('ridgeadder', 114, 144, 'crn_bw_m#a'), ('ridgeadder', 126, 152, 'crn_bw_m#a'), ('screeferret', 114, 152, 'crn_bw_m#b'), ('screeferret', 126, 144, 'crn_bw_m#b'),
    ('slateraven', 70, 72, 'crn_sc_m#a'), ('slateraven', 82, 84, 'crn_sc_m#a'), ('stoneibex', 70, 84, 'crn_sc_m#b'), ('stoneibex', 82, 72, 'crn_sc_m#b'),
    ('stoneibex', 112, 120, 'crn_wb_m#a'), ('stoneibex', 124, 128, 'crn_wb_m#a'), ('ridgeadder', 112, 128, 'crn_wb_m#b'), ('ridgeadder', 124, 120, 'crn_wb_m#b'),
    ('slateraven', 194, 66, 'crn_sg_m#a'), ('slateraven', 206, 74, 'crn_sg_m#a'), ('screeferret', 194, 74, 'crn_sg_m#b'), ('screeferret', 206, 66, 'crn_sg_m#b'),
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
    # Boulderwatch
    Q('crn_bw_hold', 'Keep the Boulderwatch Brazier Lit', 'cairn_warden', 90,
      'The signal brazier on the terrace north-west of Boulderwatch gutters whenever the adders gather, and then the caravans lose the pass in the dark. Stand in the circle beside it for twenty seconds while Mira relights it, and let nothing reach her.',
      [('hold', 'crn_bw_m', 'Keep the Boulderwatch Brazier Lit', 20)], requires='cairn_welcome'),
    Q('crn_rounds', 'Posts of the Cairnspine', 'cairn_warden', 91,
      'Three posts watch the mountain beyond Boulderwatch: the Singing Cairn Post in the west, the Whitebark Post in the middle heights and the Stormgate Camp in the north. Mira wants their keepers told that the pass is open. Speak with Halvar, Ingrid and Ragna, and use the Travel Masters if the climb is long.',
      [('talk', 'cn_sc_halvar', 'Speak with Rune-Keeper Halvar Greyslate at the Singing Cairn Post', 1), ('talk', 'cn_wb_ingrid', 'Speak with Wood-Reeve Ingrid Palebark at the Whitebark Post', 1),
       ('talk', 'cn_sg_ragna', 'Speak with Stormwarden Ragna Thunderhand at the Stormgate Camp', 1)], requires='cairn_welcome'),
    # Singing Cairn Post, on the western height
    Q('crn_sc_walk', 'Up to the Singing Cairn', 'cn_sc_halvar', 91,
      'North of the post the singing stones stand in their ring, and the slate ravens have taken to roosting on them, which spoils the tuning. Walk up to the Singing Cairn and defeat four Slate Ravens on the way.',
      [('visit', 'cairn_stones', 'Reach the Singing Cairn', 1), ('kill', 'slateraven', 'Defeat Slate Ravens on the way', 4)], requires='cairn_welcome'),
    Q('crn_sc_feathers', 'Feathers for the Stone Singer', 'cairn_stonesinger', 91,
      'Edda dusts the singing stones with raven feather, which lifts the dust without scratching the slate. Bring her five Slate Raven Feathers.',
      [('bring', 'slate_raven_feather', 'Bring Slate Raven Feathers', 5)], requires='crn_sc_walk'),
    Q('crn_sc_hold', 'Hold the Singing Circle', 'cn_sc_halvar', 92,
      'The signal horn west of the post cracks whenever the ibex herd comes down, and then every hoof on the height answers it. Stand in the circle beside it for twenty seconds while Halvar binds the horn, and keep them off him.',
      [('hold', 'crn_sc_m', 'Hold the Singing Circle', 20)], requires='crn_sc_walk'),
    Q('crn_sc_adders', 'Down to the Adder Stones', 'cn_sc_halvar', 93,
      'Far south-east, above the pass, the boulders hold the day\'s heat into the night and the ridge adders lie along them in rows. Walk down to the Adder Stones and defeat five Ridge Adders there.',
      [('visit', 'crn_adder_stones', 'Reach the Adder Stones', 1), ('kill', 'ridgeadder', 'Defeat Ridge Adders on the stones', 5)], requires='crn_sc_hold'),
    # Whitebark Post, in the middle heights
    Q('crn_wb_walk', 'Up to the Whitebark Grove', 'cn_wb_ingrid', 92,
      'North-west of the post the Whitebark Grove stands on its pale slope, and the ibex come down from it at dusk. Ingrid wants a count. Walk up to the grove and defeat four Stone Ibex on the way.',
      [('visit', 'cairn_grove', 'Reach the Whitebark Grove', 1), ('kill', 'stoneibex', 'Defeat Stone Ibex on the way', 4)], requires='cairn_welcome'),
    Q('crn_wb_horn', 'Horns for the Wood Reeve', 'cn_wb_ingrid', 92,
      'Ingrid cuts the post\'s tool handles from ibex horn, which never splinters in the frost. Bring her five Stone Ibex Horns.',
      [('bring', 'ibex_horn', 'Bring Stone Ibex Horns', 5)], requires='crn_wb_walk'),
    Q('crn_wb_hold', 'Hold the Whitebark Circle', 'cn_wb_ingrid', 93,
      'The old warning stone south-west of the post rings itself whenever the adders gather, and then every scale on the heights comes to answer it. Stand in the circle beside it for twenty seconds while Ingrid muffles the stone, and keep them off her.',
      [('hold', 'crn_wb_m', 'Hold the Whitebark Circle', 20)], requires='crn_wb_walk'),
    Q('crn_wb_wood', 'The Edge of the Whitebark Wood', 'cn_wb_ingrid', 94,
      'North of the grove the wood closes in, and the ravens nest in every white crown along its edge. Walk to the edge of the Whitebark Wood and defeat five Slate Ravens there, and go no further alone.',
      [('visit', 'crn_wood_edge', 'Reach the edge of the Whitebark Wood', 1), ('kill', 'slateraven', 'Defeat Slate Ravens at the wood edge', 5)], requires='crn_wb_hold'),
    # Stormgate Camp, on the northern ridge
    Q('crn_sg_gate', 'Up to the Thunderheart Gate', 'cn_sg_ragna', 93,
      'North-west of the camp the ridge climbs to the Thunderheart Gate, and the scree ferrets have dug under the stair. Ragna wants a count. Walk up to the gate and defeat four Scree Ferrets on the way.',
      [('visit', 'cairn_thunder', 'Reach the Thunderheart Gate', 1), ('kill', 'screeferret', 'Defeat Scree Ferrets on the way', 4)], requires='cairn_welcome'),
    Q('crn_sg_pelts', 'Pelts for the Camp', 'cn_sg_ragna', 94,
      'The camp\'s cloaks are lined with ferret pelt, which does not conduct the stormlight. Bring Ragna five Scree Ferret Pelts.',
      [('bring', 'screeferret_pelt', 'Bring Scree Ferret Pelts', 5)], requires='crn_sg_gate'),
    Q('crn_sg_hold', 'Hold the Stormgate Circle', 'cn_sg_ragna', 94,
      'The lightning rod east of the camp rings whenever the ravens gather, and then every wing on the ridge comes down to it. Stand in the circle beside it for twenty seconds while Ragna grounds the rod, and keep the flock off her.',
      [('hold', 'crn_sg_m', 'Hold the Stormgate Circle', 20)], requires='crn_sg_gate'),
    Q('crn_sg_spires', 'Under the Condor Spires', 'cn_sg_ragna', 95,
      'North-east of the camp the spires rise out of the ridge, and the ravens that circle them are the Storm Condor\'s own scouts. Walk to the foot of the Condor Spires and defeat five Slate Ravens there, and do not climb higher alone.',
      [('visit', 'crn_spires', 'Reach the foot of the Condor Spires', 1), ('kill', 'slateraven', 'Defeat Slate Ravens under the spires', 5)], requires='crn_sg_hold'),
]

# Old ids, new meaning (only where the geography changed): the texts that named no place stay as they were
REWRITES = {
    'cairn_welcome': dict(description='Meet the healer, the surveyor and the peak scout at Boulderwatch, the hub at the middle of the pass.'),
    'cairn_ferrets': dict(description='Ferrets have burrowed beneath the lower cairn road between Boulderwatch and the Prismwaste.'),
    'cairn_behemoth': dict(description='Three companions should face the Cairn Behemoth where the pass ends in the southern toe, a long walk south of Boulderwatch.'),
    'cairn_titan': dict(description='Four companions should confront the Whitebark Titan in the heart of the Whitebark Wood, north of the grove and west of the Stormgate road.'),
    'cairn_condor': dict(description='Five companions must bring down the Storm Condor where it hunts the Condor Spires in the north-east, beyond the Stormgate Camp.'),
    'cairn_gate': dict(description='Survey the Thunderheart Gate at the head of the northern ridge and consult the Meeting Stone at the Stormgate Camp before descending.'),
    'cairn_patrol': dict(description='Patrol the switchbacks between Boulderwatch and the Whitebark Post.'),
    'cairn_onward': dict(description='Climb from the Frostwake Shelf over the eastern rim into the Cairnspine and report to Warden Mira Cairn at Boulderwatch.'),
    'es_23': dict(description='Edda asks you to ring the three oath bells above the Singing Cairn. You have learned why Eldmarr hates the hall. Now listen to the stones that will fall with it.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {
    'cairn_warden': dict(dialogue='The mountain road bends four times between here and the Whitebark Post. Keep the stone markers in sight, and the Stormgate Camp lies a long climb beyond.'),
    'cairn_surveyor': dict(dialogue='Every boulder on this pass has a name. The biggest one sometimes walks: it keeps to the southern toe, below the city.'),
    'cairn_scout': dict(dialogue='From the terraces I can see the whole pass: the Prismwaste behind us, the Frostwake rim to the east and the Thunderheart ridge to the north.'),
    'cairn_stonesinger': dict(dialogue='The stones on this height sing when the wind comes from the north. Ring the three oath bells above the Singing Cairn together and the whole mountain remembers a name.'),
    'cairn_grovekeeper': dict(dialogue='The white trees stand bare in every season. North of the post the wood is older than the pass, and what walks in it is older still.'),
    'cairn_windseer': dict(dialogue='The Thunderheart Gate hums in the north-west and the Storm Condor answers it from the north-east. I read the wind between them.'),
    'cairn_stone': dict(dialogue='Meet your companions here before the Thunderheart Gate opens.'),
}
TAGLINE = 'A mountain pass of slate switchbacks, giant boulders and leafless white trees: four elites, a hub in the middle of the pass and the Thunderheart Gate'

# elite quest texts that name a number of companions keep the old numbers; no quest is added for the Avalanche Bear


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['cairn_healer']['offers']
    supplier = by['cairn_trader']['offers']
    hub = by['travel_boulderwatch']
    box = by['mailbox_27_boulderwatch']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = [k for k in hamlets if k != 'boulderwatch']
    spots = {'singing': (-1, 3.5), 'whitebark': (-1, 3.5), 'stormgate': (-1, 3.5)}
    for key in keys:
        dx, dy = spots[key]
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[], name={'singing': 'Travel Master Bodil', 'whitebark': 'Travel Master Gunnar', 'stormgate': 'Travel Master Ingeborg'}[key])
        out.append(t)
    boxes = {'singing': (2, 1), 'whitebark': (3, 1), 'stormgate': (-2, 3)}
    for key in keys:
        dx, dy = boxes[key]
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_27_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Cairnspine entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 27]
    for key, h in hamlets.items():
        box_id = 'mailbox_27_boulderwatch' if key == 'boulderwatch' else f'mailbox_27_{key}'
        box = next(n for n in zone['npcs'] if n['id'] == box_id)
        m = next(n for n in zone['npcs'] if n['id'] == ('travel_boulderwatch' if key == 'boulderwatch' else f'travel_{key}'))
        directory.append(dict(id=box['id'], zone=27, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
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
    keys = [k for k in hamlets if k != 'boulderwatch']
    for n in zone['npcs']:
        if n['id'] == 'travel_boulderwatch':
            n['travelStop'] = hamlets['boulderwatch']['name']
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + [f'travel_{k}' for k in keys]))
        elif n['id'].startswith('travel_') and n.get('travelStop') in {h['name'] for h in hamlets.values()}:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + ['travel_boulderwatch'] + [f'travel_{k}' for k in keys if f'travel_{k}' != n['id']]))
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
