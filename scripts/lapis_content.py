"""The Lapis Erg's hubs, people, quests and places. Data for scripts/lapis_design.py (shaped coordinates, zone 25).

Owner request 2026-11-09: "for pilot. reshape lapis erg. and remake the zone and quests to fit the new shape. no fillers. put a wall towards yearwheel". Owner answers: keep the
Sunward Vale, Veyrroot Canopy and Sunken Astrolabe crossings; **the Yearwheel gets no portal at all from here, just a wall covering it up** (no gate in the wall); keep both
elites (the Dune Colossus and the Mirage Roc) and add one with no quest (the Cobalt Basilisk); three outposts (Wallwatch Post, Saltpan Post, Eastwell Post) besides Azure Wells and
the Astrolabe Rest at the Sunken Astrolabe's door.

Every old `lapis_*`, `entry_astro` and `es_21`/`es_go_21` id stays (saved progress, tests, quest_gear_rewards): texts are rewritten only where the geography changed. Fourteen quests
are new. New ids and people start `lapis_` / `lp_` and stay within 19 characters (the accept string is capped at 32). Levels 80-85, rewardXp = levels.txt[level-1] / 10.
Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(80, 86)}
GOLD = {80: 8200, 81: 9000, 82: 9800, 83: 10600, 84: 11400, 85: 12200}

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is Azure Wells (the old city's own 40 x 40 rectangle, built round the south-western oasis); the
# Astrolabe Rest is built round the Sunken Astrolabe's door. There is no seam, so nothing here has to keep away from a border; the Yearwheel wall is kept clear by the design.
HAMLETS = {
    'wells':     dict(name='Azure Wells', x=60, y=190, hw=20, hh=20, city=True),
    'wallwatch': dict(name='Wallwatch Post', x=95, y=70, hw=12, hh=11),
    'eastwell':  dict(name='Eastwell Post', x=186, y=172, hw=12, hh=11),
    'saltpan':   dict(name='Saltpan Post', x=150, y=205, hw=12, hh=11),
    'astro':     dict(name='Astrolabe Rest', x=130, y=78, hw=14, hh=14, block=True),
}
# the Sunken Astrolabe's lens and the block round it move whole to the north-eastern brass terraces
DOOR = (130.0, 64.0)
OLD_DOOR = (140.0, 23.0)
D_DOOR = (DOOR[0] - OLD_DOOR[0], DOOR[1] - OLD_DOOR[1])

# the three oases (the old lapis_oasis art plus its solid water disc): the south-western one lies inside Azure Wells, the Mirrored Oasis in the middle, the Eastern Oasis in the east
OASES = [(61, 201), (118, 134), (209, 168)]
MIRROR = (112.0, 128.0)           # the huge brass mirror beside the middle oasis (old lapis_mirror)

# kind, x, y: the Dune Colossus on the Walking Dune in the north-west, the Mirage Roc on the Roc Crag in the east, the Cobalt Basilisk (no quest) in the Glass Dunes in the south-east.
ELITES = [('dunecolossus', 58, 96), ('mirageroc', 203, 130), ('cobaltbasilisk', 246, 226)]
AWARENESS = {'dunecolossus': 16., 'mirageroc': 18., 'cobaltbasilisk': 15.}

TENT = dict(r=0, width=4, depth=3)

DRESSING = {
    # the old city's three caravan tents and its well, round the plaza (old plaza (29, 128))
    'wells': [
        ('lapis_caravan_tent', -7, -9, dict(TENT, v=0)), ('lapis_caravan_tent', 7, 9, dict(TENT, v=1)), ('lapis_caravan_tent', 14, -4, dict(TENT, v=2)),
        ('lapis_caravan_tent', -14, 8, dict(TENT, v=0)), ('lapis_well', 0, -2, dict(r=1, v=0)),
        ('lapis_silk_flag', -4, 6, dict(r=.13, v=0)), ('lapis_silk_flag', 5, -8, dict(r=.13, v=1)),
    ],
    'astro': [
        ('lapis_caravan_tent', -10, 2, dict(TENT, v=1)),
        ('lapis_silk_flag', -7, -10, dict(r=.13, v=0)), ('lapis_silk_flag', 8, -10, dict(r=.13, v=1)),
        ('campfire', 3, 5, dict(r=.65)), ('bench', 3, 10, dict(r=0, width=1.5, depth=.45)),
        ('noticeboard', -3, -7, dict(r=.4, width=1.3, depth=.4, label='Astrolabe Rest')),
    ],
    'wallwatch': [
        ('lapis_caravan_tent', 0, -6.5, dict(TENT, v=0)), ('lapis_caravan_tent', -6, 1, dict(TENT, v=1)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Wallwatch Post')),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
    'eastwell': [
        ('lapis_caravan_tent', 0, -6.5, dict(TENT, v=2)), ('lapis_caravan_tent', -6, 1, dict(TENT, v=0)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Eastwell Post')),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
    'saltpan': [
        ('lapis_caravan_tent', 0, -6.5, dict(TENT, v=1)), ('lapis_caravan_tent', -6, 1, dict(TENT, v=2)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Saltpan Post')),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy) from the plaza
HUB_NPCS = {'lapis_keeper': ('wells', -3, -4), 'lapis_healer': ('wells', -11, 4), 'lapis_cartographer': ('wells', 9, -10), 'lapis_trader': ('wells', -9, -12),
            'lapis_scout': ('wells', 14, 0), 'lapis_wrangler': ('wells', 12, 7), 'lapis_warden': ('wallwatch', 3, -3),
            'lapis_seer': ('astro', -5, -4), 'lapis_stone': ('astro', 6, 2)}
WELLS_PEOPLE = {'travel_azure_wells': (14, 10), 'mailbox_25_azure_wells': (15.5, 12.5)}

NPCS = [
    dict(id='lp_ww_hesper', hamlet='wallwatch', dx=-3, dy=-1, name='Wallwarden Hesper Quill', role='Wall warden', color='#b7e5dc',
         look=dict(skin='#a77250', hair='#3b4156', style='short', hat='hood', hatColor='#228c98'),
         dialogue='North-west of the post the Wheel Wall runs from the dunes down to the sand, and nothing on the far side is ours to open. The old road to the Yearwheel was closed when the seasons began to blow through it. I keep the wall.'),
    dict(id='lp_ww_yeva', hamlet='wallwatch', dx=5, dy=3, name='Furrier Yeva Tansy', role='Furrier', color='#b7e5dc',
         look=dict(skin='#c99b7a', hair='#5a3a2a', style='long', hat='none', hatColor='#228c98'),
         dialogue='Nothing keeps the wind off a watchman like dune-fennec fur. Bring me five and the Post will have a cloak for every night on the wall.'),
    dict(id='lp_ww_trader', hamlet='wallwatch', dx=-6, dy=4.6, name='Idris Datepalm', role='Outpost trader', color='#b7e5dc', trader=True,
         look=dict(skin='#8a6248', hair='#2a2a32', style='short', hat='none', hatColor='#228c98'),
         dialogue='Dates, tonics and stew for the wall watch. Everything is sold at cost: the wall pays in other ways.'),
    dict(id='lp_sp_soraya', hamlet='saltpan', dx=-3, dy=-1, name='Pan-Warden Soraya Brine', role='Pan warden', color='#b7e5dc',
         look=dict(skin='#d9b08c', hair='#1a1a22', style='long', hat='hood', hatColor='#2e6a8a'),
         dialogue='The Blue Salt Pans lie just east of the post, and every scorpion on them has grown a lens for a tail. The Veyrroot road comes in from the south. I keep the pans.'),
    dict(id='lp_sp_tomas', hamlet='saltpan', dx=5, dy=3, name='Glassblower Tomas Kiln', role='Glassblower', color='#b7e5dc',
         look=dict(skin='#edc5a1', hair='#4a5a4a', style='short', hat='none', hatColor='#2e6a8a'),
         dialogue='A scorpion\'s shard is clearer than anything I can melt from the sand. Bring me five and the Post will have a lantern for every tent.'),
    dict(id='lp_sp_trader', hamlet='saltpan', dx=-6, dy=5.6, name='Mirra Saltwick', role='Outpost trader', color='#b7e5dc', trader=True,
         look=dict(skin='#c99b7a', hair='#3a2a2a', style='long', hat='none', hatColor='#2e6a8a'),
         dialogue='Bread, tonics and stew for the pan crews. If the pans glitter, look away and draw your blade.'),
    dict(id='lp_ew_karim', hamlet='eastwell', dx=-3, dy=-1, name='Basin-Warden Karim Tidewell', role='Basin warden', color='#b7e5dc',
         look=dict(skin='#a87a5a', hair='#1a1a22', style='short', hat='hood', hatColor='#c9a35a'),
         dialogue='The Eastern Oasis is the last water before the coast, and the sun vultures know it. North of the post the Roc Crag rises, and nothing that nests there takes kindly to company. I keep the basin.'),
    dict(id='lp_ew_lunet', hamlet='eastwell', dx=5, dy=3, name='Fletcher Lunet Featherly', role='Fletcher', color='#b7e5dc',
         look=dict(skin='#e0b89a', hair='#6a4a3a', style='long', hat='none', hatColor='#c9a35a'),
         dialogue='A sun vulture\'s quill flies truer than a goose\'s ever did. Bring me five and the Post will have a quiver for every watcher.'),
    dict(id='lp_ew_trader', hamlet='eastwell', dx=-6, dy=5.6, name='Dalia Sunfig', role='Outpost trader', color='#b7e5dc', trader=True,
         look=dict(skin='#8a6248', hair='#2a2a32', style='short', hat='none', hatColor='#c9a35a'),
         dialogue='Figs, tonics and stew. Drink at the oasis only when the vultures are not circling it.'),
]

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each)
PLACES = [
    dict(id='lp_salt_arch', name='The Salt Arch', x=100, y=50, r=6),
    dict(id='lp_salt_pans', name='The Blue Salt Pans', x=176, y=222, r=6),
    dict(id='lp_glass_dunes', name='The Glass Dunes', x=236, y=206, r=6),
    dict(id='lp_roc_foot', name='The Foot of the Roc Crag', x=190, y=152, r=6),
    dict(id='lp_wl_m', name='The Well Lanterns', x=92, y=218, r=2.1, waves=[dict(at=1, tag='lp_wl_m#a'), dict(at=11, tag='lp_wl_m#b')]),
    dict(id='lp_ww_m', name='The Wallwatch Circle', x=118, y=58, r=2.1, waves=[dict(at=1, tag='lp_ww_m#a'), dict(at=11, tag='lp_ww_m#b')]),
    dict(id='lp_sp_m', name='The Saltpan Circle', x=178, y=194, r=2.1, waves=[dict(at=1, tag='lp_sp_m#a'), dict(at=11, tag='lp_sp_m#b')]),
    dict(id='lp_ew_m', name='The Eastwell Circle', x=166, y=150, r=2.1, waves=[dict(at=1, tag='lp_ew_m#a'), dict(at=11, tag='lp_ew_m#b')]),
]
BELLS = [(125, 176), (133, 170), (145, 173)]          # the Empty Seat's three oath bells, moved rigidly (old (57, 60), (65, 54), (77, 57))

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('sandhopper', 86, 212, 'lp_wl_m#a'), ('sandhopper', 98, 224, 'lp_wl_m#a'), ('sandhopper', 86, 224, 'lp_wl_m#b'), ('sandhopper', 98, 212, 'lp_wl_m#b'),
    ('dunefennec', 112, 52, 'lp_ww_m#a'), ('dunefennec', 124, 64, 'lp_ww_m#a'), ('dunefennec', 112, 64, 'lp_ww_m#b'), ('dunefennec', 124, 52, 'lp_ww_m#b'),
    ('glassscorpion', 172, 188, 'lp_sp_m#a'), ('glassscorpion', 184, 200, 'lp_sp_m#a'), ('glassscorpion', 172, 200, 'lp_sp_m#b'), ('glassscorpion', 184, 188, 'lp_sp_m#b'),
    ('sunvulture', 160, 144, 'lp_ew_m#a'), ('sunvulture', 172, 156, 'lp_ew_m#a'), ('sunvulture', 160, 156, 'lp_ew_m#b'), ('sunvulture', 172, 144, 'lp_ew_m#b'),
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
    # Azure Wells, in the south-west
    Q('lapis_wl_hold', 'Keep the Well Lanterns Lit', 'lapis_keeper', 80,
      'The lanterns on the track east of Azure Wells gutter whenever the sandhoppers gather, and then the caravans lose the road. Stand in the circle there for twenty seconds while Sahra relights them, and let nothing reach her.',
      [('hold', 'lp_wl_m', 'Keep the Well Lanterns Lit', 20)], requires='lapis_welcome'),
    Q('lapis_rounds', 'Posts of the Erg', 'lapis_keeper', 81,
      'Three posts watch the Erg beyond the Wells: Wallwatch Post by the wall in the north, Saltpan Post in the south and Eastwell Post by the eastern water. Sahra wants their wardens told that the wells hold. Speak with Hesper, Soraya and Karim, and use the Travel Masters if the dunes are long.',
      [('talk', 'lp_ww_hesper', 'Speak with Wallwarden Hesper Quill at Wallwatch Post', 1), ('talk', 'lp_sp_soraya', 'Speak with Pan-Warden Soraya Brine at Saltpan Post', 1),
       ('talk', 'lp_ew_karim', 'Speak with Basin-Warden Karim Tidewell at Eastwell Post', 1)], requires='lapis_welcome'),
    # Wallwatch Post, by the Wheel Wall in the north
    Q('lapis_ww_walk', 'Up to the Salt Arch', 'lp_ww_hesper', 80,
      'North of Wallwatch Post the old Salt Arch still stands over the track, and the dune fennecs have made their dens under it. Hesper wants a count. Walk up to the Salt Arch and defeat four Dune Fennecs on the way.',
      [('visit', 'lp_salt_arch', 'Reach the Salt Arch', 1), ('kill', 'dunefennec', 'Defeat Dune Fennecs on the way', 4)], requires='lapis_welcome'),
    Q('lapis_ww_fur', 'Fur for the Wall Watch', 'lp_ww_yeva', 81,
      'Yeva sews the watch\'s night cloaks from dune-fennec fur, which keeps out the wind that comes over the wall. Bring her five Dune Fennec Fur.',
      [('bring', 'fennec_fur', 'Bring Dune Fennec Fur', 5)], requires='lapis_ww_walk'),
    Q('lapis_ww_hold', 'Hold the Wallwatch Circle', 'lp_ww_hesper', 81,
      'The signal brazier east of the post gutters whenever the fennecs gather, and then every fang on the northern dunes comes to answer it. Stand in the circle beside it for twenty seconds while Hesper trims the wick, and keep them off him.',
      [('hold', 'lp_ww_m', 'Hold the Wallwatch Circle', 20)], requires='lapis_ww_walk'),
    Q('lapis_ww_dune', 'Round the Walking Dune', 'lp_ww_hesper', 82,
      'South-west of the post the Walking Dune rolls slowly across the sand, and the dune fennecs run in its lee. Walk down to the Mirrored Oasis by the middle track and defeat five Dune Fennecs on the way.',
      [('visit', 'lapis_mirror', 'Reach the Mirrored Oasis', 1), ('kill', 'dunefennec', 'Defeat Dune Fennecs on the way', 5)], requires='lapis_ww_hold'),
    # Saltpan Post, in the south
    Q('lapis_sp_walk', 'Out to the Blue Salt Pans', 'lp_sp_soraya', 82,
      'East of Saltpan Post the Blue Salt Pans glitter under the sun, and the glass scorpions lie along every crust. Soraya wants a count. Walk out to the Blue Salt Pans and defeat four Glass Scorpions on the way.',
      [('visit', 'lp_salt_pans', 'Reach the Blue Salt Pans', 1), ('kill', 'glassscorpion', 'Defeat Glass Scorpions on the way', 4)], requires='lapis_hoppers'),
    Q('lapis_sp_glass', 'Shards for the Glassblower', 'lp_sp_tomas', 82,
      'Tomas blows lanterns from scorpion glass, which is clearer than anything he can melt from the sand. Bring him five Glass Scorpion Shards.',
      [('bring', 'scorpion_glass', 'Bring Glass Scorpion Shards', 5)], requires='lapis_sp_walk'),
    Q('lapis_sp_hold', 'Hold the Saltpan Circle', 'lp_sp_soraya', 83,
      'The tally post at the north end of the pans groans whenever the scorpions gather, and then every claw on the crust comes to answer it. Stand in the circle beside it for twenty seconds while Soraya braces it, and keep the pans off her.',
      [('hold', 'lp_sp_m', 'Hold the Saltpan Circle', 20)], requires='lapis_sp_walk'),
    Q('lapis_sp_glare', 'Into the Glass Dunes', 'lp_sp_soraya', 83,
      'Beyond the pans the sand has been fused to green glass by old lightning, and the scorpions there are the biggest on the Erg. Walk out to the Glass Dunes and defeat five Glass Scorpions there.',
      [('visit', 'lp_glass_dunes', 'Reach the Glass Dunes', 1), ('kill', 'glassscorpion', 'Defeat Glass Scorpions in the dunes', 5)], requires='lapis_sp_hold'),
    # Eastwell Post, by the eastern water
    Q('lapis_ew_walk', 'Down to the Eastern Oasis', 'lp_ew_karim', 83,
      'East of Eastwell Post the Eastern Oasis lies in its basin, and the sun vultures have taken the shore for a roost. Karim wants a count. Walk down to the Eastern Oasis and defeat four Sun Vultures on the way.',
      [('visit', 'lapis_east', 'Reach the Eastern Oasis', 1), ('kill', 'sunvulture', 'Defeat Sun Vultures on the way', 4)], requires='lapis_fennecs'),
    Q('lapis_ew_quill', 'Quills for the Fletcher', 'lp_ew_lunet', 84,
      'Lunet fletches the watch\'s arrows from sun-vulture quills, which fly truer than any goose\'s. Bring her five Sun Vulture Quills.',
      [('bring', 'vulture_quill', 'Bring Sun Vulture Quills', 5)], requires='lapis_ew_walk'),
    Q('lapis_ew_hold', 'Hold the Eastwell Circle', 'lp_ew_karim', 84,
      'The old signal drum west of the post splits its skin whenever the vultures gather, and then every wing on the basin comes to answer it. Stand in the circle beside it for twenty seconds while Karim stretches a new skin, and keep the flock off him.',
      [('hold', 'lp_ew_m', 'Hold the Eastwell Circle', 20)], requires='lapis_ew_walk'),
    Q('lapis_ew_crag', 'Beneath the Roc Crag', 'lp_ew_karim', 85,
      'North of the post the Roc Crag rises over the basin, and the vultures wheel beneath its nest. Walk up to the foot of the Roc Crag and defeat five Sun Vultures there, and do not go higher alone.',
      [('visit', 'lp_roc_foot', 'Reach the foot of the Roc Crag', 1), ('kill', 'sunvulture', 'Defeat Sun Vultures under the crag', 5)], requires='lapis_ew_hold'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'lapis_colossus': dict(description='Three companions should confront the dune colossus on the Walking Dune, north-west of the Wells and west of the north road.'),
    'lapis_roc': dict(description='Five companions must face the roc on the Roc Crag, north of the Eastern Oasis.'),
    'lapis_scorpions': dict(description='Clear glass scorpions from the track to the Mirrored Oasis.'),
    'lapis_vultures': dict(description='Keep sun vultures from the Eastern Oasis.'),
    'lapis_onward': dict(description='Leave Veyrroot for the Lapis Erg and report to Sahra Bluewell at Azure Wells.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {
    'lapis_keeper': dict(dialogue='The Lapis Erg has three waters: these wells, the Mirrored Oasis in the middle and the Eastern Oasis by the coast. Follow the brass markers; the dunes move, but the wells do not. The road north ends at the Wheel Wall, and nobody has opened it since the seasons began to blow through.'),
    'lapis_warden': dict(dialogue='The Walking Dune is west of this post and nothing walks it twice. Hire a spear if you are going, and bring friends.'),
    'lapis_seer': dict(dialogue='The Sunken Astrolabe is open beneath its turning lenses. Bring five travelers.'),
}
TAGLINE = 'Ochre dunes, turquoise oases, date palms, a sunken brass astrolabe and a wall against the turning seasons'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['lapis_healer']['offers']
    supplier = by['lapis_trader']['offers']
    hub = by['travel_azure_wells']
    box = by['mailbox_25_azure_wells']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = [k for k in hamlets if k != 'wells']
    spots = {'wallwatch': (-1, 3.5), 'eastwell': (-1, 3.5), 'saltpan': (-1, 3.5), 'astro': (-8, 6)}
    for key in keys:
        dx, dy = spots[key]
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[])
        out.append(t)
    boxes = {'wallwatch': (2, 1), 'eastwell': (3, 1), 'saltpan': (-2, 3), 'astro': (7, -6)}
    for key in keys:
        dx, dy = boxes[key]
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_25_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Lapis Erg entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 25]
    for key, h in hamlets.items():
        box_id = 'mailbox_25_azure_wells' if key == 'wells' else f'mailbox_25_{key}'
        box = next(n for n in zone['npcs'] if n['id'] == box_id)
        m = next(n for n in zone['npcs'] if n['id'] == ('travel_azure_wells' if key == 'wells' else f'travel_{key}'))
        directory.append(dict(id=box['id'], zone=25, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
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
    # Azure Wells' master links to every new master (the neighbours' links are added by lapis_design.link_travel)
    keys = [k for k in hamlets if k != 'wells']
    for n in zone['npcs']:
        if n['id'] == 'travel_azure_wells':
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + [f'travel_{k}' for k in keys]))
        elif n['id'].startswith('travel_') and n.get('travelStop') in {h['name'] for h in hamlets.values()}:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + ['travel_azure_wells'] + [f'travel_{k}' for k in keys if f'travel_{k}' != n['id']]))
    ids = {p['id'] for p in PLACES}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    ids = {q['id'] for q in QUESTS}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids]
    zone['city'], zone['camps'] = city_and_camps(hamlets)
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    zone['tagline'] = TAGLINE
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
