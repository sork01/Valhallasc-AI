"""The Tanglecrown's hubs, people, quests and places. Data for scripts/tangle_design.py (shaped coordinates, zone 22).

Owner request 2026-11-08: "for pilot. reshape tanglecrown. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the Ribbonwild only
(Sunward Vale, the Veyrroot Canopy and the Temple of the Rain Crown stay gates), keep every portal, keep both elites (the Jade Anaconda and the Crown Jaguar) and add one with
no quest (the Hollowroot Centipede), three outposts (Rootgate Post, Drumroot Post, Stilt Post) besides Banyan Landing and the Rainstep Camp at the temple door.

Every old `tangle_*` and `es_18` id stays (saved progress, tests, quest_gear_rewards): texts are rewritten only where the geography changed. Fourteen quests are new.
New ids and people start `tangle_` / `tg_` and stay within 19 characters (the accept string is capped at 32). Levels 75-80, rewardXp = levels.txt[level-1] / 10.
Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(75, 81)}
GOLD = {75: 7500, 76: 8100, 77: 8700, 78: 9300, 79: 9900, 80: 10500}

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is Banyan Landing (the old city's own 40 x 40 rectangle); the Rainstep Camp is built round the moved
# temple door. Nothing art-less and nobody stands within 20 tiles of the Ribbonwild seam (a seam neighbour draws only scenery with art).
HAMLETS = {
    'landing':  dict(name='Banyan Landing', x=122, y=190, hw=20, hh=20, city=True),
    'rootgate': dict(name='Rootgate Post', x=170, y=120, hw=12, hh=11),
    'drumroot': dict(name='Drumroot Post', x=214, y=128, hw=12, hh=11),
    'stilt':    dict(name='Stilt Post', x=160, y=218, hw=12, hh=11),
    'rainstep': dict(name='Rainstep Camp', x=254, y=146, hw=14, hh=14, block=True),
}
# the temple door and the block round it move whole: old (120, 23) -> here
DOOR = (254.0, 134.0)
OLD_DOOR = (120.0, 23.0)
D_DOOR = (DOOR[0] - OLD_DOOR[0], DOOR[1] - OLD_DOOR[1])

# kind, x, y: the Jade Anaconda in the Jade Basin, the Crown Jaguar on the High Jaguar Terrace, the Hollowroot Centipede (no quest) in the Strangler Maze.
ELITES = [('jadeanaconda', 128, 104), ('crownjaguar', 190, 162), ('rootcentipede', 205, 192)]
AWARENESS = {'jadeanaconda': 15., 'crownjaguar': 17., 'rootcentipede': 15.}

LODGE = dict(r=0, width=5, depth=4)

DRESSING = {
    # the old city's two lodges and two stalls (old plaza (29, 110))
    'landing': [
        ('banyan_lodge', -13, -19, dict(LODGE, v=0)), ('banyan_lodge', 12, 14, dict(LODGE, v=1)),
        ('boardwalk_stall', -14, 11, dict(r=0, width=3, depth=2, v=0)), ('boardwalk_stall', 11, -5, dict(r=0, width=3, depth=2, v=1)),
    ],
    'rainstep': [
        ('boardwalk_stall', -10, 2, dict(r=0, width=3, depth=2, v=1)),
        ('jaguar_totem', -7, -10, dict(r=.9, v=0)), ('jaguar_totem', 8, -10, dict(r=.9, v=0)),
        ('campfire', 3, 5, dict(r=.65)), ('bench', 3, 10, dict(r=0, width=1.5, depth=.45)),
        ('noticeboard', -3, -7, dict(r=.4, width=1.3, depth=.4, label='Rainstep Camp')),
    ],
    'rootgate': [
        ('banyan_lodge', 0, -6.5, dict(LODGE, v=0)), ('boardwalk_stall', -6, 3, dict(r=0, width=3, depth=2, v=0)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Rootgate Post')),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
    'drumroot': [
        ('banyan_lodge', 0, -6.5, dict(LODGE, v=1)), ('boardwalk_stall', -6, 3, dict(r=0, width=3, depth=2, v=1)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Drumroot Post')),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
    'stilt': [
        ('banyan_lodge', 0, -6.5, dict(LODGE, v=0)), ('boardwalk_stall', -6, 3, dict(r=0, width=3, depth=2, v=0)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Stilt Post')),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy) from the plaza
HUB_NPCS = {'tangle_warden': ('landing', 1, -2), 'tangle_medic': ('landing', -7, 10), 'tangle_botanist': ('landing', 11, 6), 'tangle_trader': ('landing', -12, -10),
            'tangle_tracker': ('landing', 13, -14), 'tangle_scholar': ('rainstep', -5, -4), 'tangle_stone': ('rainstep', 6, 2)}

NPCS = [
    dict(id='tg_rg_ixel', hamlet='rootgate', dx=-3, dy=-1, name='Gate-Warden Ixel Marrow', role='Gate warden', color='#d6f1a2',
         look=dict(skin='#c99b7a', hair='#2a3a2a', style='short', hat='hood', hatColor='#3a7a56'),
         dialogue='The trunk road from the Veyrroot Canopy comes down a little north-east of the post, and the first thing every traveller meets is a mantis dressed as an orchid. South-west of us lies the Gliders\' Reach, and east of it the jaguar\'s terrace. I keep the north gate.'),
    dict(id='tg_rg_pomo', hamlet='rootgate', dx=5, dy=3, name='Pomo Barkweaver', role='Bark weaver', color='#d6f1a2',
         look=dict(skin='#e0b89a', hair='#5a3a2a', style='long', hat='none', hatColor='#3a7a56'),
         dialogue='Orchid-mantis petals take the green out of bark cloth and put the sky in. Bring me five and the Post will have an awning for every bench on the road.'),
    dict(id='tg_rg_trader', hamlet='rootgate', dx=-6, dy=4.6, name='Tuli Cassava', role='Outpost trader', color='#d6f1a2', trader=True,
         look=dict(skin='#d9b08c', hair='#3a3238', style='short', hat='none', hatColor='#3a7a56'),
         dialogue='Stew, tonics and cassava for anyone who walks the north road. Everything is sold at cost, because the road pays in other ways.'),
    dict(id='tg_dr_kessa', hamlet='drumroot', dx=-3, dy=-1, name='Drum-Warden Kessa Thrum', role='Drum warden', color='#d6f1a2',
         look=dict(skin='#a87a5a', hair='#1a1a22', style='long', hat='hood', hatColor='#8a5a2e'),
         dialogue='Listen: when the gorillas beat the terraces east of the post, the whole canopy answers, and the camp at the temple door hears it first. The trunk road lies west of us. I keep the middle.'),
    dict(id='tg_dr_yarrow', hamlet='drumroot', dx=5, dy=3, name='Yarrow Skinbinder', role='Skin binder', color='#d6f1a2',
         look=dict(skin='#c99b7a', hair='#6a4a3a', style='short', hat='none', hatColor='#8a5a2e'),
         dialogue='A drumskin that has hung out in the rain sounds better than any new one. Bring me five and the Post will have a signal drum for every watchman.'),
    dict(id='tg_dr_trader', hamlet='drumroot', dx=-6, dy=5.6, name='Nuru Plantain', role='Outpost trader', color='#d6f1a2', trader=True,
         look=dict(skin='#8a6248', hair='#2a2a32', style='short', hat='none', hatColor='#8a5a2e'),
         dialogue='Plantain, tonics and stew. If the drums stop, put down your cup and draw your weapon.'),
    dict(id='tg_sp_marek', hamlet='stilt', dx=-3, dy=-1, name='Stilt-Warden Marek Silt', role='Stilt warden', color='#d6f1a2',
         look=dict(skin='#d9b08c', hair='#4a5a4a', style='short', hat='hood', hatColor='#2e6a6a'),
         dialogue='The blackwater begins just south of the posts, and the caimans have taken every crossing between here and the mangroves. The Landing lies north-west along the road, and the Ribbonwild beyond it. I keep the south.'),
    dict(id='tg_sp_odile', hamlet='stilt', dx=5, dy=3, name='Odile Scalewright', role='Scale smith', color='#d6f1a2',
         look=dict(skin='#edc5a1', hair='#3a2a2a', style='long', hat='none', hatColor='#2e6a6a'),
         dialogue='A caiman\'s scale turns a spear and a rainstorm alike. Bring me five and the Post will have a shield for every watchman.'),
    dict(id='tg_sp_trader', hamlet='stilt', dx=-6, dy=5.6, name='Bao Mangrove', role='Outpost trader', color='#d6f1a2', trader=True,
         look=dict(skin='#c99b7a', hair='#1a1a22', style='short', hat='none', hatColor='#2e6a6a'),
         dialogue='Bread, tonics and stew for those who stand on stilts. If the water rises, buy a tonic first and ask questions later.'),
]

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each)
PLACES = [
    dict(id='tg_orchid_rise', name='The Orchid Rise', x=200, y=112, r=6),
    dict(id='tg_gliders', name='The Gliders\' Reach', x=150, y=150, r=6),
    dict(id='tg_mangrove', name='The Mangrove Stair', x=130, y=252, r=6),
    dict(id='tg_drums', name='The Drum Terraces', x=234, y=124, r=6),
    dict(id='tg_stair', name='The Rainstep Stair', x=250, y=170, r=6),
    dict(id='tg_lh_m', name='The Landing Lamps', x=156, y=172, r=2.1, waves=[dict(at=1, tag='tg_lh_m#a'), dict(at=11, tag='tg_lh_m#b')]),
    dict(id='tg_rg_m', name='The Rootgate Circle', x=198, y=130, r=2.1, waves=[dict(at=1, tag='tg_rg_m#a'), dict(at=11, tag='tg_rg_m#b')]),
    dict(id='tg_dr_m', name='The Drumroot Circle', x=216, y=150, r=2.1, waves=[dict(at=1, tag='tg_dr_m#a'), dict(at=11, tag='tg_dr_m#b')]),
    dict(id='tg_sp_m', name='The Stilt Circle', x=146, y=240, r=2.1, waves=[dict(at=1, tag='tg_sp_m#a'), dict(at=11, tag='tg_sp_m#b')]),
]

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('canopyglider', 150, 166, 'tg_lh_m#a'), ('orchidmantis', 162, 178, 'tg_lh_m#a'), ('canopyglider', 150, 178, 'tg_lh_m#b'), ('orchidmantis', 162, 166, 'tg_lh_m#b'),
    ('orchidmantis', 192, 124, 'tg_rg_m#a'), ('orchidmantis', 204, 136, 'tg_rg_m#a'), ('canopyglider', 192, 136, 'tg_rg_m#b'), ('canopyglider', 204, 124, 'tg_rg_m#b'),
    ('drumgorilla', 210, 144, 'tg_dr_m#a'), ('drumgorilla', 222, 156, 'tg_dr_m#a'), ('drumgorilla', 210, 156, 'tg_dr_m#b'), ('canopyglider', 222, 144, 'tg_dr_m#b'),
    ('poolcaiman', 140, 234, 'tg_sp_m#a'), ('poolcaiman', 152, 246, 'tg_sp_m#a'), ('poolcaiman', 140, 246, 'tg_sp_m#b'), ('poolcaiman', 152, 234, 'tg_sp_m#b'),
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
    # Banyan Landing, in the west-centre of the crown
    Q('tangle_lh_hold', 'Keep the Landing Lamps Lit', 'tangle_warden', 76,
      'The lamps on the boardwalk north-east of the Landing gutter whenever the gliders gather, and then the night watch loses the road. Stand in the circle there for twenty seconds while Asha relights them, and let nothing reach her.',
      [('hold', 'tg_lh_m', 'Keep the Landing Lamps Lit', 20)], requires='tangle_welcome'),
    Q('tangle_rounds', 'Posts of the Crown Road', 'tangle_warden', 77,
      'Three posts watch the crown beyond the Landing: Rootgate Post on the north road, Drumroot Post in the north-east and Stilt Post in the south-east. Asha wants their wardens told that the road holds. Speak with Ixel, Kessa and Marek, and use the Travel Masters if the road is long.',
      [('talk', 'tg_rg_ixel', 'Speak with Gate-Warden Ixel Marrow at Rootgate Post', 1), ('talk', 'tg_dr_kessa', 'Speak with Drum-Warden Kessa Thrum at Drumroot Post', 1),
       ('talk', 'tg_sp_marek', 'Speak with Stilt-Warden Marek Silt at Stilt Post', 1)], requires='tangle_welcome'),
    # Rootgate Post, on the north road
    Q('tangle_rg_walk', 'Up to the Orchid Rise', 'tg_rg_ixel', 75,
      'East of Rootgate Post the Orchid Rise swells under the border trees, and the orchid mantises have taken it for a garden. Ixel wants a count. Walk out to the Orchid Rise and defeat four Orchid Mantises on the way.',
      [('visit', 'tg_orchid_rise', 'Reach the Orchid Rise', 1), ('kill', 'orchidmantis', 'Defeat Orchid Mantises on the way', 4)], requires='tangle_welcome'),
    Q('tangle_rg_petals', 'Petals for the Bark Weaver', 'tg_rg_pomo', 76,
      'Pomo dyes her bark cloth with the petals of orchid mantises, which take the green out and put the sky in. Bring her five Orchid Mantis Petals.',
      [('bring', 'mantis_petals', 'Bring Orchid Mantis Petals', 5)], requires='tangle_rg_walk'),
    Q('tangle_rg_hold', 'Hold the Rootgate Circle', 'tg_rg_ixel', 76,
      'The tallest kapok east of the post sheds its blossom whenever the mantises gather, and then every claw and wing on the north road comes to answer it. Stand in the circle beside it for twenty seconds while Ixel ties the boughs down, and keep them off him.',
      [('hold', 'tg_rg_m', 'Hold the Rootgate Circle', 20)], requires='tangle_rg_walk'),
    Q('tangle_rg_glide', 'Down to the Gliders\' Reach', 'tg_rg_ixel', 77,
      'South-west of the post the Gliders\' Reach opens between the roots, and the canopy gliders hang above it in a slow crowd. Walk down to the Reach and defeat five Canopy Gliders there.',
      [('visit', 'tg_gliders', 'Reach the Gliders\' Reach', 1), ('kill', 'canopyglider', 'Defeat Canopy Gliders at the Reach', 5)], requires='tangle_rg_hold'),
    # Stilt Post, in the south
    Q('tangle_sp_walk', 'Out to the Mangrove Stair', 'tg_sp_marek', 77,
      'South-west of Stilt Post the mangroves step down to the coast in a stair of roots, and the blackwater caimans lie along every landing. Marek wants a count. Walk out to the Mangrove Stair and defeat four Blackwater Caimans on the way.',
      [('visit', 'tg_mangrove', 'Reach the Mangrove Stair', 1), ('kill', 'poolcaiman', 'Defeat Blackwater Caimans on the way', 4)], requires='tangle_gliders'),
    Q('tangle_sp_scales', 'Scales for the Smith', 'tg_sp_odile', 77,
      'Odile beats caiman scale into shields, because it turns a spear and a rainstorm alike. Bring her five Blackwater Caiman Scales.',
      [('bring', 'caiman_scale', 'Bring Blackwater Caiman Scales', 5)], requires='tangle_sp_walk'),
    Q('tangle_sp_hold', 'Hold the Stilt Circle', 'tg_sp_marek', 78,
      'The old mooring post south of the stilts groans whenever the caimans gather, and then every jaw in the blackwater comes to answer it. Stand in the circle at the post for twenty seconds while Marek braces it, and keep the water off him.',
      [('hold', 'tg_sp_m', 'Hold the Stilt Circle', 20)], requires='tangle_sp_walk'),
    Q('tangle_sp_water', 'Along the Blackwater Edge', 'tg_sp_marek', 78,
      'Past the mooring the Blackwater Edge runs along the coast, and the caimans have made every bank of it their own. Walk down to the Mangrove Stair again by the edge and defeat five Blackwater Caimans there.',
      [('visit', 'tg_mangrove', 'Walk the Blackwater Edge to the Mangrove Stair', 1), ('kill', 'poolcaiman', 'Defeat Blackwater Caimans on the edge', 5)], requires='tangle_sp_hold'),
    # Drumroot Post, in the north-east
    Q('tangle_dr_walk', 'Across the Drum Terraces', 'tg_dr_kessa', 78,
      'East of Drumroot Post the Drum Terraces climb toward the border, and the gorillas have taken their ledges for a stage. Kessa wants a count. Walk out to the Drum Terraces and defeat four Drum Gorillas on the way.',
      [('visit', 'tg_drums', 'Reach the Drum Terraces', 1), ('kill', 'drumgorilla', 'Defeat Drum Gorillas on the way', 4)], requires='tangle_caimans'),
    Q('tangle_dr_skins', 'Hides for the Skin Binder', 'tg_dr_yarrow', 78,
      'Yarrow stretches hide over the Post\'s signal drums, because a skin that has hung in the rain sounds better than any new one. Bring him five Drum Gorilla Hides.',
      [('bring', 'gorilla_drumskin', 'Bring Drum Gorilla Hides', 5)], requires='tangle_dr_walk'),
    Q('tangle_dr_hold', 'Hold the Drumroot Circle', 'tg_dr_kessa', 79,
      'The great signal drum south of the post cracks its head whenever the gorillas gather, and then every fist and wing on the terraces comes to answer it. Stand in the circle beside it for twenty seconds while Kessa mends the skin, and keep the troop off her.',
      [('hold', 'tg_dr_m', 'Hold the Drumroot Circle', 20)], requires='tangle_dr_walk'),
    Q('tangle_dr_stair', 'Toward the Rainstep Stair', 'tg_dr_kessa', 79,
      'South of the camp at the temple door the Rainstep Stair climbs from the coast, and the gorillas drum on its landings. Walk along to the Rainstep Stair and defeat five Drum Gorillas there.',
      [('visit', 'tg_stair', 'Reach the Rainstep Stair', 1), ('kill', 'drumgorilla', 'Defeat Drum Gorillas at the Stair', 5)], requires='tangle_dr_hold'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'tangle_anaconda': dict(description='Three companions should confront the giant anaconda in the Jade Basin, north of the Landing.'),
    'tangle_jaguar': dict(description='Five companions are needed against the predator atop the High Jaguar Terrace, east of the trunk road.'),
    'tangle_temple': dict(description='Walk east to the Temple of the Rain Crown, survey its sealed stairs and consult the Meeting Stone at the Rainstep Camp.'),
    'tangle_onward': dict(description='Cross the border from the Ribbonwild and report to Asha Banyan at Banyan Landing.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {
    'tangle_stone': dict(dialogue='Gather companions for the jungle elites. The temple itself remains sealed.'),
}
TAGLINE = 'A rain-bright jungle of giant roots, braided trails and an open crown temple'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['tangle_medic']['offers']
    supplier = by['tangle_trader']['offers']
    hub = by['travel_banyan']
    box = by['mailbox_22_banyan_landing']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = [k for k in hamlets if k != 'landing']
    spots = {'rootgate': (-1, 3.5), 'drumroot': (-1, 3.5), 'stilt': (-1, 3.5), 'rainstep': (-8, 6)}
    for key in keys:
        dx, dy = spots[key]
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[])
        out.append(t)
    boxes = {'rootgate': (2, 1), 'drumroot': (3, 1), 'stilt': (-2, 3), 'rainstep': (7, -6)}
    for key in keys:
        dx, dy = boxes[key]
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_22_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Tanglecrown entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 22]
    for key, h in hamlets.items():
        box_id = 'mailbox_22_banyan_landing' if key == 'landing' else f'mailbox_22_{key}'
        box = next(n for n in zone['npcs'] if n['id'] == box_id)
        m = next(n for n in zone['npcs'] if n['id'] == ('travel_banyan' if key == 'landing' else f'travel_{key}'))
        directory.append(dict(id=box['id'], zone=22, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def city_and_camps(hamlets):
    def rect(h):
        return dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                    plaza=dict(x=h['x'], y=h['y']), radius=5 if h.get('city') else 3.5, entry=dict(x=h['x'], y=h['y'] + h['hh'] - 3))
    city = rect(next(h for h in hamlets.values() if h.get('city')))
    return city, [rect(h) for h in hamlets.values() if not h.get('city')]


def install(world, zone, hamlets, old):
    """Idempotent, so `plan` also works on a map that already carries the design."""
    new_npcs = people(world, zone, hamlets, old)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        n.update(copy.deepcopy(NPC_UPDATES.get(n['id'], {})))
    # the Landing's master links to every new master (the neighbours' links are added by tangle_design.link_travel)
    keys = [k for k in hamlets if k != 'landing']
    for n in zone['npcs']:
        if n['id'] == 'travel_banyan':
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + [f'travel_{k}' for k in keys]))
        elif n['id'].startswith('travel_') and n.get('travelStop') in {h['name'] for h in hamlets.values()}:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + ['travel_banyan'] + [f'travel_{k}' for k in keys if f'travel_{k}' != n['id']]))
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
