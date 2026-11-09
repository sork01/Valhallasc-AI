"""The Veyrroot Canopy's hubs, people, quests and places. Data for scripts/veyrroot_design.py (shaped coordinates, zone 23).

Owner request 2026-11-09: "for pilot. reshape veyroot. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the Tanglecrown AND the Lapis Erg
(Sunward Vale stays a gate); **Veyrroot is wild, with enemies** (it was a peaceful city), **Heartwood becomes the main city** inside the big tree (a later step); three outposts; keep the old
quests and their ids. The Hollow Arch at the foot of the Great Tree leads to Heartwood.

The old Canopy people stay (their ids are saved progress and the Spark network): the matriarch, ranger, healer, trader and the Meeting Stone at Rootfoot, the lookout at the Sunleaf Lookout,
the nectar keeper at Rootstair Post. Every old `heart_*` and `es_19` id stays; texts are rewritten only where the geography changed. Sixteen quests are new: new ids and people start `veyr_` /
`ve_` and stay within 19 characters (the accept string is capped at 32). Levels 80-84, rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(80, 86)}
GOLD = {80: 8200, 81: 9000, 82: 9800, 83: 10600, 84: 11400, 85: 12200}

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is Rootfoot, at the foot of the Great Tree; the three outposts and the Sunleaf Lookout are camps.
HAMLETS = {
    'rootfoot':  dict(name='Rootfoot', x=210, y=241, hw=22, hh=20, city=True),
    'gladewatch': dict(name='Gladewatch Post', x=100, y=192, hw=12, hh=11),
    'rootstair': dict(name='Rootstair Post', x=206, y=98, hw=12, hh=11),
    'eastbark':  dict(name='Eastbark Post', x=296, y=198, hw=12, hh=11),
    'lookout':   dict(name='Sunleaf Lookout', x=252, y=146, hw=10, hh=9),
}
TREE = (210.0, 207.0)             # the Great Tree: a solid trunk r 9
ARCH = (210.0, 222.0)             # the Hollow Arch at its foot (the portal to Heartwood)
ARCH_ARRIVAL = (210.0, 229.0)     # where Heartwood's way back puts a hero

# kind, x, y: the Lantern Queen in the north-western canopy, the Heartbark Colossus in the eastern roots (both with a quest), the Amber Sap Golem (no quest) on the southern sap flats
ELITES = [('lanternqueen', 132, 104), ('barkcolossus', 312, 118), ('ambergolem', 262, 266)]
AWARENESS = {'lanternqueen': 16., 'barkcolossus': 17., 'ambergolem': 15.}

LODGE = dict(r=0, width=5, depth=4)      # the Tanglecrown's banyan lodge (isometric City.art): a jungle post is built of living wood, not desert tents
BOARD = dict(r=.4, width=1.3, depth=.4)
BENCH = dict(r=0, width=1.5, depth=.45)

DRESSING = {
    # the Rootfoot market stalls either side of the Hollow Arch's road, a well-lit plaza
    'rootfoot': [
        ('canopy_market', -16, -3, dict(r=1.1, v=0)), ('canopy_market', 16, -3, dict(r=1.1, v=1)),
        ('suspended_garden', -17, 12, dict(r=1.2, v=0)), ('suspended_garden', 17, 13, dict(r=1.2, v=1)),
        ('leaf_lantern', -6, -8, dict(r=.12, v=0)), ('leaf_lantern', 6, -8, dict(r=.12, v=1)),
        ('campfire', 3, 7, dict(r=.65)), ('bench', 3, 12, BENCH),
        ('noticeboard', -4, -13, dict(BOARD, label='Rootfoot')),
        ('meetingstone', 10.3, 2.3, dict(r=1.7, v=0)),
    ],
    'lookout': [
        ('sunleaf_observatory', 0, -4, dict(r=0, v=0, place='heart_observatory')),
        ('leaf_lantern', -6, 4, dict(r=.12, v=0)), ('leaf_lantern', 6, 4, dict(r=.12, v=1)),
        ('campfire', 4, 5, dict(r=.65)), ('bench', -4, 7, BENCH),
        ('noticeboard', 6, -3, dict(BOARD, label='Sunleaf Lookout')),
    ],
    'gladewatch': [
        ('banyan_lodge', 0, -6.5, dict(LODGE, v=0)), ('banyan_lodge', -6, 1, dict(LODGE, v=1)),
        ('noticeboard', 5, -7, dict(BOARD, label='Gladewatch Post')), ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, BENCH),
    ],
    'rootstair': [
        ('banyan_lodge', 0, -6.5, dict(LODGE, v=1)), ('banyan_lodge', -6, 1, dict(LODGE, v=2)),
        ('noticeboard', 5, -7, dict(BOARD, label='Rootstair Post')), ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, BENCH),
        ('leaf_lantern', -9, -5, dict(r=.12, v=0)), ('leaf_lantern', -10, 5, dict(r=.12, v=1)),
    ],
    'eastbark': [
        ('banyan_lodge', 0, -6.5, dict(LODGE, v=2)), ('banyan_lodge', -6, 1, dict(LODGE, v=0)),
        ('noticeboard', 5, -7, dict(BOARD, label='Eastbark Post')), ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, BENCH),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy) from the plaza
HUB_NPCS = {'heart_matriarch': ('rootfoot', -3, -6), 'heart_ranger': ('rootfoot', 8, -7), 'heart_healer': ('rootfoot', -12, 2), 'heart_trader': ('rootfoot', -9, 9),
            'heart_stone': ('rootfoot', 12, 4), 'heart_lookout': ('lookout', 0, 0.5), 'heart_apiarist': ('rootstair', 5, 3)}
ROOTFOOT_PEOPLE = {'travel_veyrroot': (15, 12), 'mailbox_23_veyrroot_canopy': (16.5, 14.5)}

NPCS = [
    dict(id='ve_gw_ilsa', hamlet='gladewatch', dx=-3, dy=-1, name='Glade-Warden Ilsa Tarn', role='Glade warden', color='#e4f7ae',
         look=dict(skin='#a77250', hair='#28574b', style='short', hat='hood', hatColor='#569e66'),
         dialogue='The Sunlit Glade is the one open sky in the whole Veyrroot, and every sap beetle and moss lemur in the jungle comes to it for the light. The Sunward road comes in from the west, the Tanglecrown road from the south. I keep the glade.'),
    dict(id='ve_gw_nuri', hamlet='gladewatch', dx=5, dy=3, name='Weaver Nuri Fennlow', role='Moss weaver', color='#e4f7ae',
         look=dict(skin='#c99b7a', hair='#5a3a2a', style='long', hat='none', hatColor='#569e66'),
         dialogue='Moss-lemur fur is warmer than wool and it never mats. Bring me five and the Post will have a blanket for every bunk.'),
    dict(id='ve_gw_trader', hamlet='gladewatch', dx=-6, dy=4.6, name='Pell Honeyfig', role='Outpost trader', color='#e4f7ae', trader=True,
         look=dict(skin='#8a6248', hair='#2a2a32', style='short', hat='none', hatColor='#569e66'),
         dialogue='Figs, tonics and stew for the glade crews. Everything is sold at cost: the jungle pays in other ways.'),
    dict(id='ve_rs_corvin', hamlet='rootstair', dx=-3, dy=-1, name='Stair-Warden Corvin Ashby', role='Stair warden', color='#e4f7ae',
         look=dict(skin='#d9b08c', hair='#1a1a22', style='short', hat='hood', hatColor='#569e66'),
         dialogue='North of the post the Twin Roots climb out of the canopy, and above them the Lantern Queen keeps her hive. The Lapis road leaves the Veyrroot at the top of this stair. I keep the stair.'),
    dict(id='ve_rs_trader', hamlet='rootstair', dx=-6, dy=5.6, name='Mirra Dewberry', role='Outpost trader', color='#e4f7ae', trader=True,
         look=dict(skin='#c99b7a', hair='#3a2a2a', style='long', hat='none', hatColor='#569e66'),
         dialogue='Bread, tonics and stew for the stair crews. If a lantern hums, put it down and draw your blade.'),
    dict(id='ve_eb_dessa', hamlet='eastbark', dx=-3, dy=-1, name='Bark-Warden Dessa Orme', role='Bark warden', color='#e4f7ae',
         look=dict(skin='#a87a5a', hair='#1a1a22', style='short', hat='hood', hatColor='#569e66'),
         dialogue='The Eastern Roots run down to the coast, and half of what stands among them is not a tree. The Heartbark Colossus walks there. I keep the coast.'),
    dict(id='ve_eb_taro', hamlet='eastbark', dx=5, dy=3, name='Carver Taro Splinter', role='Bark carver', color='#e4f7ae',
         look=dict(skin='#e0b89a', hair='#6a4a3a', style='long', hat='none', hatColor='#569e66'),
         dialogue='A bark mimic\'s chip carves like nothing else and never splits. Bring me five and the Post will have a stool for every watcher.'),
    dict(id='ve_eb_trader', hamlet='eastbark', dx=-6, dy=5.6, name='Dalia Sunfig', role='Outpost trader', color='#e4f7ae', trader=True,
         look=dict(skin='#8a6248', hair='#2a2a32', style='short', hat='none', hatColor='#569e66'),
         dialogue='Figs, tonics and stew. Never sit with your back to a stump on the coast: ask the carver why.'),
]

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each); the old Canopy places keep their ids
PLACES = [
    dict(id='heart_hollow', name='Hollow Arch', x=210, y=219, r=4),
    dict(id='heart_observatory', name='Sunleaf Observatory', x=252, y=141, r=4),
    dict(id='heart_lantern_walk', name='Lantern Walk', x=222, y=112, r=4),
    dict(id='heart_garden_walk', name='Hanging Gardens', x=118, y=150, r=4),
    dict(id='heart_market_walk', name='Canopy Market', x=210, y=232, r=4),
    dict(id='ve_twin_roots', name='The Twin Roots', x=240, y=84, r=6),
    dict(id='ve_sap_flats', name='The Amber Sap Flats', x=204, y=272, r=6),
    dict(id='ve_east_roots', name='The Eastern Roots', x=304, y=150, r=6),
    dict(id='ve_hive_foot', name='The Foot of the Hive Crown', x=152, y=122, r=6),
    dict(id='ve_rf_m', name='The Rootfoot Lanterns', x=180, y=262, r=2.1, waves=[dict(at=1, tag='ve_rf_m#a'), dict(at=11, tag='ve_rf_m#b')]),
    dict(id='ve_gw_m', name='The Glade Circle', x=136, y=196, r=2.1, waves=[dict(at=1, tag='ve_gw_m#a'), dict(at=11, tag='ve_gw_m#b')]),
    dict(id='ve_rs_m', name='The Rootstair Circle', x=176, y=84, r=2.1, waves=[dict(at=1, tag='ve_rs_m#a'), dict(at=11, tag='ve_rs_m#b')]),
    dict(id='ve_eb_m', name='The Eastbark Circle', x=262, y=182, r=2.1, waves=[dict(at=1, tag='ve_eb_m#a'), dict(at=11, tag='ve_eb_m#b')]),
]
MEMORY = (196.0, 236.0)           # the Empty Seat's memory (old es_19_m): where the canopy homes meet the great root

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('barkmimic', 174, 256, 've_rf_m#a'), ('barkmimic', 186, 268, 've_rf_m#a'), ('barkmimic', 174, 268, 've_rf_m#b'), ('barkmimic', 186, 256, 've_rf_m#b'),
    ('sapbeetle', 130, 190, 've_gw_m#a'), ('sapbeetle', 142, 202, 've_gw_m#a'), ('mosslemur', 130, 202, 've_gw_m#b'), ('mosslemur', 142, 190, 've_gw_m#b'),
    ('lanternhornet', 170, 78, 've_rs_m#a'), ('lanternhornet', 182, 90, 've_rs_m#a'), ('lanternhornet', 170, 90, 've_rs_m#b'), ('lanternhornet', 182, 78, 've_rs_m#b'),
    ('barkmimic', 256, 176, 've_eb_m#a'), ('barkmimic', 268, 188, 've_eb_m#a'), ('barkmimic', 256, 188, 've_eb_m#b'), ('barkmimic', 268, 176, 've_eb_m#b'),
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
    # Rootfoot, at the foot of the Great Tree
    Q('veyr_rf_hold', 'Keep the Rootfoot Lanterns Lit', 'heart_matriarch', 80,
      'The lanterns on the track south-west of Rootfoot gutter whenever the bark mimics gather, and then the carriers lose the road to the Hollow Arch. Stand in the circle there for twenty seconds while Iria relights them, and let nothing reach her.',
      [('hold', 've_rf_m', 'Keep the Rootfoot Lanterns Lit', 20)], requires='heart_welcome'),
    Q('veyr_rounds', 'Posts of the Veyrroot', 'heart_matriarch', 81,
      'Three posts watch the jungle beyond Rootfoot: Gladewatch Post in the western glade, Rootstair Post in the north and Eastbark Post on the eastern coast. Iria wants their wardens told that the Great Tree stands. Speak with Ilsa, Corvin and Dessa, and use the Travel Masters if the roots are long.',
      [('talk', 've_gw_ilsa', 'Speak with Glade-Warden Ilsa Tarn at Gladewatch Post', 1), ('talk', 've_rs_corvin', 'Speak with Stair-Warden Corvin Ashby at Rootstair Post', 1),
       ('talk', 've_eb_dessa', 'Speak with Bark-Warden Dessa Orme at Eastbark Post', 1)], requires='heart_welcome'),
    # Gladewatch Post, in the Sunlit Glade
    Q('veyr_gw_walk', 'Up to the Hanging Gardens', 've_gw_ilsa', 80,
      'North of Gladewatch Post the Hanging Gardens spill down from the canopy, and the moss lemurs have made their dens in them. Ilsa wants a count. Walk up to the Hanging Gardens and defeat four Moss Lemurs on the way.',
      [('visit', 'heart_garden_walk', 'Reach the Hanging Gardens', 1), ('kill', 'mosslemur', 'Defeat Moss Lemurs on the way', 4)], requires='heart_welcome'),
    Q('veyr_gw_fur', 'Fur for the Glade Bunks', 've_gw_nuri', 81,
      'Nuri weaves the glade crews\' blankets from moss-lemur fur, which is warmer than wool and never mats. Bring her five Moss Lemur Fur.',
      [('bring', 'mosslemur_fur', 'Bring Moss Lemur Fur', 5)], requires='veyr_gw_walk'),
    Q('veyr_gw_hold', 'Hold the Glade Circle', 've_gw_ilsa', 81,
      'The signal horn east of the post cracks whenever the beetles gather, and then every shell in the glade comes to answer it. Stand in the circle beside it for twenty seconds while Ilsa binds the horn, and keep them off her.',
      [('hold', 've_gw_m', 'Hold the Glade Circle', 20)], requires='veyr_gw_walk'),
    Q('veyr_gw_flats', 'Down to the Amber Sap Flats', 've_gw_ilsa', 82,
      'South of the glade the sap runs out of the roots and sets in amber pans, and the sap beetles feed on it in rows. Walk down to the Amber Sap Flats and defeat five Sap Beetles there.',
      [('visit', 've_sap_flats', 'Reach the Amber Sap Flats', 1), ('kill', 'sapbeetle', 'Defeat Sap Beetles on the flats', 5)], requires='veyr_gw_hold'),
    # Rootstair Post, below the Twin Roots in the north
    Q('veyr_rs_walk', 'Up to the Twin Roots', 've_rs_corvin', 82,
      'North-east of Rootstair Post the Twin Roots climb out of the canopy, and the lantern hornets have started to nest in the lamps that hang from them. Corvin wants a count. Walk up to the Twin Roots and defeat four Lantern Hornets on the way.',
      [('visit', 've_twin_roots', 'Reach the Twin Roots', 1), ('kill', 'lanternhornet', 'Defeat Lantern Hornets on the way', 4)], requires='heart_welcome'),
    Q('veyr_rs_amber', 'Amber for the Nectar Keeper', 'heart_apiarist', 82,
      'Miri pours the stair\'s lantern vessels from hornet amber, which holds the light for a month. Bring her five Lantern Hornet Amber.',
      [('bring', 'hornet_amber', 'Bring Lantern Hornet Amber', 5)], requires='veyr_rs_walk'),
    Q('veyr_rs_hold', 'Hold the Rootstair Circle', 've_rs_corvin', 83,
      'The warning bell west of the post rings itself whenever the hornets gather, and then every wing on the stair comes to answer it. Stand in the circle beside it for twenty seconds while Corvin muffles the clapper, and keep the swarm off him.',
      [('hold', 've_rs_m', 'Hold the Rootstair Circle', 20)], requires='veyr_rs_walk'),
    Q('veyr_rs_hive', 'Under the Hive Crown', 've_rs_corvin', 83,
      'West of the stair the canopy bulges into a great paper hive, and the hornets circle it day and night. Walk up to the foot of the Hive Crown and defeat five Lantern Hornets there, and do not go higher alone.',
      [('visit', 've_hive_foot', 'Reach the foot of the Hive Crown', 1), ('kill', 'lanternhornet', 'Defeat Lantern Hornets under the hive', 5)], requires='veyr_rs_hold'),
    # Eastbark Post, on the eastern coast
    Q('veyr_eb_walk', 'Out to the Eastern Roots', 've_eb_dessa', 83,
      'North of Eastbark Post the Eastern Roots come down to the coast like the knuckles of a fist, and a great many of the stumps among them are not stumps. Dessa wants a count. Walk out to the Eastern Roots and defeat four Bark Mimics on the way.',
      [('visit', 've_east_roots', 'Reach the Eastern Roots', 1), ('kill', 'barkmimic', 'Defeat Bark Mimics on the way', 4)], requires='veyr_rounds'),
    Q('veyr_eb_chip', 'Chips for the Carver', 've_eb_taro', 84,
      'Taro carves the post\'s stools from bark-mimic chips, which cut like nothing else and never split. Bring him five Bark Mimic Chips.',
      [('bring', 'barkmimic_chip', 'Bring Bark Mimic Chips', 5)], requires='veyr_eb_walk'),
    Q('veyr_eb_hold', 'Hold the Eastbark Circle', 've_eb_dessa', 84,
      'The old signal drum north-west of the post splits its skin whenever the mimics gather, and then every stump on the coast comes to answer it. Stand in the circle beside it for twenty seconds while Dessa stretches a new skin, and keep them off her.',
      [('hold', 've_eb_m', 'Hold the Eastbark Circle', 20)], requires='veyr_eb_walk'),
    Q('veyr_eb_grove', 'Into the Heartbark Grove', 've_eb_dessa', 84,
      'Past the Eastern Roots the bark is thickest, and the mimics there are the biggest in the Veyrroot. Walk to the Eastern Roots again and defeat five Bark Mimics in the grove.',
      [('visit', 've_east_roots', 'Reach the Eastern Roots', 1), ('kill', 'barkmimic', 'Defeat Bark Mimics in the grove', 5)], requires='veyr_eb_hold'),
]
# The two elite quests (class choices are added by the design from late_quests.gear)
ELITE_QUESTS = [
    Q('veyr_queen', 'The Lantern Queen', 've_rs_corvin', 83,
      'Three companions should face the Lantern Queen where she keeps her hive in the north-western canopy, west of the stair and north of the Hanging Gardens.',
      [('kill', 'lanternqueen', 'Defeat the Lantern Queen', 1)], requires='veyr_rs_hold', gold=16500, group=True, recommendedPlayers=3, rewardItem='accessory_amber_l80_blue'),
    Q('veyr_colossus', 'The Heartbark Colossus', 've_eb_dessa', 84,
      'Five companions are needed against the walking grove in the Eastern Roots, north of Eastbark Post and east of the Lookout.',
      [('kill', 'barkcolossus', 'Defeat the Heartbark Colossus', 1)], requires='veyr_eb_hold', gold=21500, group=True, recommendedPlayers=5, rewardItem='necklace_moonstone_l80_blue'),
]

# Old ids, new meaning (only where the geography changed): the Canopy was a city of ring decks, the Veyrroot is now the jungle round the Great Tree
REWRITES = {
    'heart_welcome': dict(title='A Jungle Under the Tree', description='Meet the healer, the path keeper and the nectar keeper at the foot of the Great Tree and on the Rootstair road.'),
    'heart_walkways': dict(title='The Living Walk', description='Follow the north road to the Sunleaf Lookout and meet the lookout who watches the whole jungle from it.'),
    'heart_lanterns': dict(title='Light in the Leaves', description='Walk the Lantern Walk below Rootstair Post and speak with the trader who sells the lanterns\' light.'),
    'heart_gardens': dict(title='The High Gardens', description='Find the Hanging Gardens above the Sunlit Glade, then ask Ena how their cool water reaches Rootfoot.'),
    'heart_market': dict(title='A Market at the Root', description='Cross the Rootfoot market under the Great Tree and meet the traders at its foot.'),
    'heart_circuits': dict(title='The Crown Circuit', description='Visit the Sunleaf Observatory and the Hollow Arch before entering the heartwood.'),
    'heart_patrol': dict(description='Make another circuit from the Sunleaf Observatory to the Hollow Arch.'),
    'es_19': dict(description='Iria asks you to listen where the Rootfoot homes meet the great root. You have learned why Eldmarr hates the hall. Now listen to the people who will fall with it.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {
    'heart_matriarch': dict(dialogue='Veyrroot is a jungle grown round one living tree. Its roots circle the crown; its oldest halls lie within the trunk, behind the Hollow Arch, and the city that lives there is Heartwood.'),
    'heart_ranger': dict(role='Path keeper', dialogue='The roads carry travelers between the glade, the lookout and the coast. I keep every road clear, as far as the Tanglecrown and the Lapis Erg.'),
    'heart_apiarist': dict(role='Nectar keeper', dialogue='Our lanterns gather daylight in their amber vessels. Follow the Lantern Walk down from the stair to the lookout.'),
    'heart_healer': dict(dialogue='Rest here. The Great Tree carries cool water down to every root.'),
    'heart_lookout': dict(role='Lookout', dialogue='From the lookout you can see the whole jungle: the glade to the west, the hive to the north-west, the roots to the east, and the heart of it all, the Great Tree.'),
    'heart_stone': dict(dialogue='Meet your companions here before the Seed Vault opens.'),
}
TAGLINE = 'A colossal jungle round one living tree: hive canopies, amber sap, bark that walks, and the Hollow Arch into Heartwood'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['heart_healer']['offers']
    supplier = by['heart_trader']['offers']
    hub = by['travel_veyrroot']
    box = by['mailbox_23_veyrroot_canopy']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = [k for k in hamlets if k != 'rootfoot']
    spots = {'gladewatch': (-1, 3.5), 'rootstair': (-1, 3.5), 'eastbark': (-1, 3.5), 'lookout': (-6, 4)}
    for key in keys:
        dx, dy = spots[key]
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[], name={'gladewatch': 'Travel Master Odo', 'rootstair': 'Travel Master Wren', 'eastbark': 'Travel Master Kade', 'lookout': 'Travel Master Sol'}[key])
        out.append(t)
    boxes = {'gladewatch': (2, 1), 'rootstair': (3, 1), 'eastbark': (-2, 3), 'lookout': (5, 3)}
    for key in keys:
        dx, dy = boxes[key]
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_23_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Veyrroot entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 23]
    for key, h in hamlets.items():
        box_id = 'mailbox_23_veyrroot_canopy' if key == 'rootfoot' else f'mailbox_23_{key}'
        box = next(n for n in zone['npcs'] if n['id'] == box_id)
        m = next(n for n in zone['npcs'] if n['id'] == ('travel_veyrroot' if key == 'rootfoot' else f'travel_{key}'))
        directory.append(dict(id=box['id'], zone=23, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def city_and_camps(hamlets):
    def rect(h):
        return dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                    plaza=dict(x=h['x'], y=h['y']), radius=6 if h.get('city') else 3.5, entry=dict(x=h['x'] - h['hw'] + 4, y=h['y']) if h.get('city') else dict(x=h['x'], y=h['y'] + h['hh'] - 3))
    city = rect(next(h for h in hamlets.values() if h.get('city')))
    return city, [rect(h) for h in hamlets.values() if not h.get('city')]


def install(world, zone, hamlets, old):
    """Idempotent, so `plan` also works on a map that already carries the design."""
    new_npcs = people(world, zone, hamlets, old)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        n.update(copy.deepcopy(NPC_UPDATES.get(n['id'], {})))
    keys = [k for k in hamlets if k != 'rootfoot']
    for n in zone['npcs']:
        if n['id'] == 'travel_veyrroot':
            n['travelStop'] = hamlets['rootfoot']['name']
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + [f'travel_{k}' for k in keys]))
        elif n['id'].startswith('travel_') and n.get('travelStop') in {h['name'] for h in hamlets.values()}:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + ['travel_veyrroot'] + [f'travel_{k}' for k in keys if f'travel_{k}' != n['id']]))
    ids = {p['id'] for p in PLACES}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    new = copy.deepcopy(QUESTS + ELITE_QUESTS)
    ids = {q['id'] for q in new}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids] + new
    zone['city'], zone['camps'] = city_and_camps(hamlets)
    zone['tagline'] = TAGLINE
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
