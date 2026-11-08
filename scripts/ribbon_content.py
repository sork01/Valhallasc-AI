"""The Ribbonwild's hubs, people, quests and places. Data for scripts/ribbon_design.py (shaped coordinates, zone 21).

Owner request 2026-11-08: "for pilot. reshape ribbonwild. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against Emberwake
Caldera only (Sunward Vale, the Tanglecrown and the Thousandfold Pavilion stay gates), keep both elites (the Parade Gryphon and the Masquerade Colossus) and add one
with no quest (the Whorlshell), three outposts (Bunting Post, Tassel Post, Garland Rest).

Every old `ribbon_*` and `es_17` id stays (saved progress, tests, quest_gear_rewards): texts are rewritten only where the geography changed. Fourteen quests are new.
New ids and people start `ribbon_` / `rw_` and stay within 19 characters (the accept string is capped at 32). Levels 70-75, rewardXp = levels.txt[level-1] / 10.
Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(70, 76)}
GOLD = {70: 7200, 71: 7800, 72: 8400, 73: 9000, 74: 9600, 75: 10200}

# The wheel: the plaza of Jubilee Crossroads is the hub of eight spokes and a ring road (the painted golden wheel).
CENTRE = (195.0, 190.0)

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is Jubilee Crossroads (the old city's own 40 x 52 rectangle, moved whole to the wheel's hub);
# the Pavilion camp is a camp built round the moved door block. Nothing art-less may stand within 20 tiles of the Emberwake seam.
HAMLETS = {
    'jubilee':  dict(name='Jubilee Crossroads', x=195, y=190, hw=20, hh=26, city=True),
    'pavilion': dict(name='Pavilion Steps', x=293, y=192, hw=14, hh=12, block=True),
    'bunting':  dict(name='Bunting Post', x=196, y=82, hw=12, hh=11),
    'tassel':   dict(name='Tassel Post', x=120, y=214, hw=12, hh=11),
    'garland':  dict(name='Garland Rest', x=305, y=290, hw=12, hh=11),
}
# the Pavilion door and the block round it move whole: old (120, 65) -> here
DOOR = (300.0, 190.0)
D_DOOR = (DOOR[0] - 120, DOOR[1] - 65)

# kind, x, y: the Parade Gryphon on the Northern Dance Floor, the Masquerade Colossus on the Mask Court, the Whorlshell (no quest) in the middle of the Ribbon Whorl.
ELITES = [('paradegryphon', 165, 88), ('maskcolossus', 300, 232), ('whorlshell', 70, 198)]
AWARENESS = {'paradegryphon': 14., 'maskcolossus': 16., 'whorlshell': 14.}

LODGE = dict(r=0, width=5, depth=4)

DRESSING = {
    # the old city's four silk pavilions and four stalls, round the plaza (old plaza (30, 70))
    'jubilee': [
        ('silk_pavilion', -13, -16, dict(r=0, width=5, depth=4, v=0)), ('silk_pavilion', 12, -16, dict(r=0, width=5, depth=4, v=1)),
        ('silk_pavilion', -13, 18, dict(r=0, width=5, depth=4, v=2)), ('silk_pavilion', 12, 18, dict(r=0, width=5, depth=4, v=3)),
        ('painted_stall', -8, -20, dict(r=0, width=3, depth=2, v=0)), ('painted_stall', 7, -22, dict(r=0, width=3, depth=2, v=1)),
        ('painted_stall', -9, 21, dict(r=0, width=3, depth=2, v=2)), ('painted_stall', 5, 22, dict(r=0, width=3, depth=2, v=3)),
        ('mosaic_disc', 0, 0, dict(r=0, v=0)),
    ],
    'pavilion': [
        ('painted_stall', -12, -8, dict(r=0, width=3, depth=2, v=1)), ('painted_stall', -11, 6, dict(r=0, width=3, depth=2, v=2)),
        ('confetti_lantern', -12, 0, dict(r=.3, v=1)), ('confetti_lantern', 9, -9, dict(r=.3, v=3)),
        ('bench', -4, 10, dict(r=0, width=1.5, depth=.45)),
    ],
    'bunting': [
        ('silk_pavilion', 0, -6.5, dict(LODGE, v=0)),
        ('painted_stall', -6, 3, dict(r=0, width=3, depth=2, v=0)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Bunting Post')),
        ('confetti_lantern', -8, -1, dict(r=.3, v=0)), ('confetti_lantern', 9, -1, dict(r=.3, v=1)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
    'tassel': [
        ('silk_pavilion', 0, -6.5, dict(LODGE, v=3)),
        ('painted_stall', -7, 2, dict(r=0, width=3, depth=2, v=3)),
        ('noticeboard', -5, -7, dict(r=.4, width=1.3, depth=.4, label='Tassel Post')),
        ('confetti_lantern', -8, -1, dict(r=.3, v=3)), ('confetti_lantern', 9, -1, dict(r=.3, v=2)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', -6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
    'garland': [
        ('silk_pavilion', 0, -6.5, dict(LODGE, v=1)),
        ('painted_stall', -6, 3, dict(r=0, width=3, depth=2, v=1)),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Garland Rest')),
        ('confetti_lantern', -8, -1, dict(r=.3, v=1)), ('confetti_lantern', 9, -1, dict(r=.3, v=2)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy) from the plaza, or the Pavilion block (moved by D_DOOR)
HUB_NPCS = {'ribbon_host': ('jubilee', 2, -6), 'ribbon_medic': ('jubilee', -8, 11), 'ribbon_tailor': ('jubilee', 8, 9), 'ribbon_naturalist': ('jubilee', 1, -16),
            'ribbon_merchant': ('jubilee', -6, -10)}
DOOR_NPCS = ('ribbon_keeper', 'ribbon_stone')

NPCS = [
    dict(id='rw_bp_aldis', hamlet='bunting', dx=-3, dy=-1, name='Gate-Warden Aldis Fray', role='Gate warden', color='#d98aa8',
         look=dict(skin='#e0b89a', hair='#8a4a5a', style='long', hat='hood', hatColor='#c4607e'),
         dialogue='The vale road from Sunward comes in at the north end of the Bunting Meadow, and the first thing every guest meets is a ribbon gecko with sticky fingers. South of us lies the Rose Court and, beyond it, the whole wheel. I keep this gate.'),
    dict(id='rw_bp_pernille', hamlet='bunting', dx=5, dy=3, name='Pernille Spoolwright', role='Spoolwright', color='#c47a96',
         look=dict(skin='#edc5a1', hair='#5a3a4a', style='long', hat='none', hatColor='#c4607e'),
         dialogue='Gecko tails take dye better than any thread. Bring me five and the Post will have bunting for every pole on the road.'),
    dict(id='rw_bp_trader', hamlet='bunting', dx=-6, dy=4.6, name='Olle Tasselmonger', role='Outpost trader', color='#d8a0b4', trader=True,
         look=dict(skin='#d9b08c', hair='#3a3238', style='short', hat='none', hatColor='#d8a0b4'),
         dialogue='Stew, tonics and tassels for anyone who walks the Rose Court. Everything is sold at cost, because the dancers are generous enough.'),
    dict(id='rw_tp_ysolde', hamlet='tassel', dx=-3, dy=-1, name='Whorl-Warden Ysolde Fringe', role='Whorl warden', color='#9a82c8',
         look=dict(skin='#edc5a1', hair='#d8d4e8', style='long', hat='hood', hatColor='#6a52a0'),
         dialogue='West of the post the grass curls into the Ribbon Whorl, and in its heart something slow and shelled keeps the beat. Further south the Great Rosette blooms in rings. Beyond all of it the mountain\'s border begins. I keep the west.'),
    dict(id='rw_tp_calder', hamlet='tassel', dx=5, dy=3, name='Calder Plumebinder', role='Plume binder', color='#8a72b8',
         look=dict(skin='#c99b7a', hair='#2a2a32', style='short', hat='none', hatColor='#6a52a0'),
         dialogue='A macaw\'s plume stays bright when everything else fades. Bring me five and the Post will have a crest for every guest.'),
    dict(id='rw_tp_trader', hamlet='tassel', dx=-5, dy=6.2, name='Wilma Sequin', role='Outpost trader', color='#a894d0', trader=True,
         look=dict(skin='#edc5a1', hair='#4a4a58', style='long', hat='none', hatColor='#a894d0'),
         dialogue='Thread, sequins and stew. If a macaw takes your hat, that is the price of a good view.'),
    dict(id='rw_gr_ruben', hamlet='garland', dx=-3, dy=-1, name='Rest-Warden Ruben Marigold', role='Rest warden', color='#d8a64e',
         look=dict(skin='#c99b7a', hair='#d8c89a', style='short', hat='hood', hatColor='#b8842e'),
         dialogue='The road from the Tanglecrown comes in just south-east of the rest, and the jesterlings meet every traveller with a bell and a bad idea. North of us the Mask Court holds its giant. West along the coast the Sunset Stair climbs in marigold steps. I keep the rest.'),
    dict(id='rw_gr_lisbet', hamlet='garland', dx=5, dy=3, name='Lisbet Jinglewright', role='Bellfounder', color='#c8943e',
         look=dict(skin='#e0bca0', hair='#6a4a3a', style='long', hat='none', hatColor='#b8842e'),
         dialogue='A jesterling\'s bell rings truer than anything I can cast. Bring me five and the Rest will have a carillon.'),
    dict(id='rw_gr_trader', hamlet='garland', dx=-6, dy=5.6, name='Hugo Rosehip', role='Outpost trader', color='#d8b870', trader=True,
         look=dict(skin='#d9b08c', hair='#5a2a2a', style='short', hat='none', hatColor='#d8b870'),
         dialogue='Bread, tonics and stew for the ones who guard the south-east. If a bell rings behind you, do not turn round: buy a tonic.'),
]

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each)
PLACES = [
    dict(id='rw_terraces', name='The Marigold Terraces', x=140, y=72, r=6),
    dict(id='rw_whorl', name='The Ribbon Whorl', x=98, y=196, r=6),
    dict(id='rw_rosette', name='The Great Rosette', x=112, y=268, r=6),
    dict(id='rw_banks', name='The Petal Banks', x=296, y=260, r=6),
    dict(id='rw_stair', name='The Sunset Stair', x=262, y=306, r=6),
    dict(id='rw_jc_m', name='The Jubilee Circle', x=232, y=170, r=2.1, waves=[dict(at=1, tag='rw_jc_m#a'), dict(at=11, tag='rw_jc_m#b')]),
    dict(id='rw_bp_m', name='The Bunting Circle', x=226, y=70, r=2.1, waves=[dict(at=1, tag='rw_bp_m#a'), dict(at=11, tag='rw_bp_m#b')]),
    dict(id='rw_tp_m', name='The Tassel Circle', x=100, y=250, r=2.1, waves=[dict(at=1, tag='rw_tp_m#a'), dict(at=11, tag='rw_tp_m#b')]),
    dict(id='rw_gr_m', name='The Garland Circle', x=258, y=288, r=2.1, waves=[dict(at=1, tag='rw_gr_m#a'), dict(at=11, tag='rw_gr_m#b')]),
]

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('ribbongecko', 226, 164, 'rw_jc_m#a'), ('ribbongecko', 238, 176, 'rw_jc_m#a'), ('balloonbeetle', 226, 176, 'rw_jc_m#b'), ('balloonbeetle', 238, 164, 'rw_jc_m#b'),
    ('ribbongecko', 220, 64, 'rw_bp_m#a'), ('ribbongecko', 232, 76, 'rw_bp_m#a'), ('ribbongecko', 220, 76, 'rw_bp_m#b'), ('balloonbeetle', 232, 64, 'rw_bp_m#b'),
    ('paintedmacaw', 94, 244, 'rw_tp_m#a'), ('paintedmacaw', 106, 256, 'rw_tp_m#a'), ('jesterling', 94, 256, 'rw_tp_m#b'), ('jesterling', 106, 244, 'rw_tp_m#b'),
    ('jesterling', 252, 282, 'rw_gr_m#a'), ('jesterling', 264, 294, 'rw_gr_m#a'), ('paintedmacaw', 252, 294, 'rw_gr_m#b'), ('paintedmacaw', 264, 282, 'rw_gr_m#b'),
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
    # Jubilee Crossroads, at the hub of the wheel
    Q('ribbon_jc_hold', 'Keep the Jubilee Lanterns Lit', 'ribbon_host', 71,
      'The lanterns on the ring road north-east of the crossroads gutter whenever the geckos gather, and then the procession loses its way. Stand in the circle there for twenty seconds while Mira relights them, and let nothing reach her.',
      [('hold', 'rw_jc_m', 'Keep the Jubilee Lanterns Lit', 20)], requires='ribbon_welcome'),
    Q('ribbon_rounds', 'The Wardens of the Wheel', 'ribbon_host', 72,
      'Three posts watch the wheel beyond the crossroads: Bunting Post on the northern road, Tassel Post in the west and Garland Rest in the south-east. Mira wants their wardens told that the procession holds. Speak with Aldis, Ysolde and Ruben, and use the Travel Masters if the road is long.',
      [('talk', 'rw_bp_aldis', 'Speak with Gate-Warden Aldis Fray at Bunting Post', 1), ('talk', 'rw_tp_ysolde', 'Speak with Whorl-Warden Ysolde Fringe at Tassel Post', 1),
       ('talk', 'rw_gr_ruben', 'Speak with Rest-Warden Ruben Marigold at Garland Rest', 1)], requires='ribbon_welcome'),
    # Bunting Post, on the northern road
    Q('ribbon_bp_walk', 'Across the Marigold Terraces', 'rw_bp_aldis', 70,
      'West of Bunting Post the Marigold Terraces step down from the northern edge, and the ribbon geckos have taken them for a stage. Aldis wants a count. Walk out to the Marigold Terraces and defeat four Ribbon Geckos on the way.',
      [('visit', 'rw_terraces', 'Reach the Marigold Terraces', 1), ('kill', 'ribbongecko', 'Defeat Ribbon Geckos on the way', 4)], requires='ribbon_welcome'),
    Q('ribbon_bp_tails', 'Tails for the Spoolwright', 'rw_bp_pernille', 70,
      'Pernille dyes her bunting with the tails of ribbon geckos, which take colour better than any thread. Bring her five Ribbon Gecko Tails.',
      [('bring', 'ribbon_tail', 'Bring Ribbon Gecko Tails', 5)], requires='ribbon_bp_walk'),
    Q('ribbon_bp_hold', 'Hold the Bunting Circle', 'rw_bp_aldis', 71,
      'The tallest bunting pole east of the post throws its streamers whenever the geckos gather, and then every claw and silk-spinner on the meadow comes to answer it. Stand in the circle beside it for twenty seconds while Aldis ties it down, and keep them off him.',
      [('hold', 'rw_bp_m', 'Hold the Bunting Circle', 20)], requires='ribbon_bp_walk'),
    Q('ribbon_bp_dance', 'Toward the Dance Floor', 'rw_bp_aldis', 72,
      'West of the post the Northern Dance Floor lies bare, and the Balloon Beetles drift over it in a slow crowd. Walk down to the Dance Floor\'s edge and defeat five Balloon Beetles there. Do not step onto the floor itself: the gryphon is not a guest.',
      [('visit', 'ribbon_gryphon_court', 'Reach the Northern Dance Floor', 1), ('kill', 'balloonbeetle', 'Defeat Balloon Beetles at the Dance Floor', 5)], requires='ribbon_bp_hold'),
    # Tassel Post, in the west
    Q('ribbon_tp_walk', 'Out to the Ribbon Whorl', 'rw_tp_ysolde', 72,
      'West of Tassel Post the grass curls into a great spiral of poles and pinwheels, and the Painted Macaws roost along its arms. Ysolde wants a count. Walk out to the Ribbon Whorl and defeat four Painted Macaws on the way.',
      [('visit', 'rw_whorl', 'Reach the Ribbon Whorl', 1), ('kill', 'paintedmacaw', 'Defeat Painted Macaws on the way', 4)], requires='ribbon_welcome'),
    Q('ribbon_tp_plumes', 'Plumes for the Binder', 'rw_tp_calder', 72,
      'Calder binds crests from macaw plumes, which stay bright when everything else fades. Bring him five Painted Macaw Plumes.',
      [('bring', 'macaw_plume', 'Bring Painted Macaw Plumes', 5)], requires='ribbon_tp_walk'),
    Q('ribbon_tp_hold', 'Hold the Tassel Circle', 'rw_tp_ysolde', 73,
      'The tasselled mast south-west of the post rings whenever the macaws wheel, and then every beak and bell on the lawns comes to answer it. Stand in the circle beside it for twenty seconds while Ysolde mutes it, and keep the flock off her.',
      [('hold', 'rw_tp_m', 'Hold the Tassel Circle', 20)], requires='ribbon_tp_walk'),
    Q('ribbon_tp_rosette', 'Down to the Great Rosette', 'rw_tp_ysolde', 73,
      'South of the post the Great Rosette blooms in rings of topiary, and the Jesterlings have made its heart their stage. Walk down to the Great Rosette and defeat five Jesterlings there.',
      [('visit', 'rw_rosette', 'Reach the Great Rosette', 1), ('kill', 'jesterling', 'Defeat Jesterlings at the Rosette', 5)], requires='ribbon_tp_hold'),
    # Garland Rest, in the south-east
    Q('ribbon_gr_walk', 'Along the Petal Banks', 'rw_gr_ruben', 73,
      'North of Garland Rest the Petal Banks run down the eastern edge, and the Jesterlings dance along them with their bells. Ruben wants a count. Walk up to the Petal Banks and defeat four Jesterlings on the way.',
      [('visit', 'rw_banks', 'Reach the Petal Banks', 1), ('kill', 'jesterling', 'Defeat Jesterlings on the way', 4)], requires='ribbon_beetles'),
    Q('ribbon_gr_bells', 'Bells for the Bellfounder', 'rw_gr_lisbet', 74,
      'Lisbet hangs jesterling bells in the Rest\'s bell frame, because they ring truer than any she can cast. Bring her five Jesterling Bells.',
      [('bring', 'jester_bell', 'Bring Jesterling Bells', 5)], requires='ribbon_gr_walk'),
    Q('ribbon_gr_hold', 'Hold the Garland Circle', 'rw_gr_ruben', 74,
      'The garland arch west of the rest flares whenever the jesterlings gather, and then every bell and beak in the south comes to answer it. Stand in the circle at the arch for twenty seconds while Ruben steadies it, and keep the crowd off him.',
      [('hold', 'rw_gr_m', 'Hold the Garland Circle', 20)], requires='ribbon_gr_walk'),
    Q('ribbon_gr_stair', 'Up the Sunset Stair', 'rw_gr_ruben', 75,
      'West of the rest the Sunset Stair climbs the coast in marigold steps, and the Painted Macaws crowd its landings. Walk along to the Sunset Stair and defeat five Painted Macaws there.',
      [('visit', 'rw_stair', 'Reach the Sunset Stair', 1), ('kill', 'paintedmacaw', 'Defeat Painted Macaws at the Stair', 5)], requires='ribbon_gr_hold'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'ribbon_geckos': dict(description='The ribbon geckos have stolen spools from the Rose Court, north of the wheel.'),
    'ribbon_macaws': dict(description='Calm the fierce macaws circling the Teal Court in the south.'),
    'ribbon_jesters': dict(description='The tiny jesterlings have turned the ring road in the south-east into a trap.'),
    'ribbon_gryphon': dict(description='A feather-crowned gryphon has claimed the Northern Dance Floor, west of Bunting Post. Bring three friends.'),
    'ribbon_colossus': dict(description='The masked giant holds the Mask Court on the east spoke, south of the Pavilion. Gather five companions.'),
    'ribbon_onward': dict(description='Follow the vale road into the Ribbonwild and meet Mira Vell at the crossroads in the middle of the wheel.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {
    'ribbon_naturalist': dict(dialogue='The macaws know each petal court by heart. Watch where the gold court meets the teal.'),
    'ribbon_host': dict(dialogue='Four color courts and one great procession, all turning round this crossroads. The Pavilion waits at the end of the east road, but its curtain is bound shut.'),
}
TAGLINE = 'A great golden wheel of color courts, silk pavilions and painted lawns'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['ribbon_medic']['offers']
    supplier = by['ribbon_merchant']['offers']
    hub = by['travel_jubilee']
    box = by['mailbox_21_jubilee_crossroads']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = list(hamlets)
    spots = {'bunting': (-1, 3.5), 'tassel': (-1, 3.5), 'garland': (-1, 3.5), 'pavilion': (6, 9)}
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[f'travel_{k}' for k in keys if k != key])
        out.append(t)
    boxes = {'bunting': (2, 1), 'tassel': (3, 1), 'garland': (-2, 3), 'pavilion': (4, -9)}
    for key, (dx, dy) in boxes.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_21_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Ribbonwild entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 21]
    for key, h in hamlets.items():
        box_id = 'mailbox_21_jubilee_crossroads' if key == 'jubilee' else f'mailbox_21_{key}'
        box = next(n for n in zone['npcs'] if n['id'] == box_id)
        m = next(n for n in zone['npcs'] if n['id'] == ('travel_jubilee' if key == 'jubilee' else f'travel_{key}'))
        directory.append(dict(id=box['id'], zone=21, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def city_and_camps(hamlets):
    def rect(h):
        return dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                    plaza=dict(x=h['x'], y=h['y']), radius=7 if h.get('city') else 3.5, entry=dict(x=h['x'], y=h['y'] + h['hh'] - 3))
    city = rect(next(h for h in hamlets.values() if h.get('city')))
    return city, [rect(h) for h in hamlets.values() if not h.get('city')]


def install(world, zone, hamlets, old):
    """Idempotent, so `plan` also works on a map that already carries the design."""
    new_npcs = people(world, zone, hamlets, old)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        n.update(copy.deepcopy(NPC_UPDATES.get(n['id'], {})))
    # the Jubilee master and mailbox stay, and link to every new master as well as to Sunward's and the Tanglecrown's
    keys = [k for k in hamlets if k != 'jubilee']
    for n in zone['npcs']:
        if n['id'] == 'travel_jubilee':
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + [f'travel_{k}' for k in keys]))
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
