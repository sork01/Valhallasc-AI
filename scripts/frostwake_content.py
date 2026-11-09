"""The Frostwake Shelf's hubs, people, quests and places. Data for scripts/frostwake_design.py (shaped coordinates, zone 26).

Owner request 2026-11-09: "for pilot. reshape frostwake shelf. and remake the zone and quests to fit the new shape. no fillers. a wall towards yearwheel". Owner answers: seamless against
Cairnspine ONLY (Stormglass Flats and Sunward Vale stay rim gates), a solid wall and NO portal towards the Yearwheel (as on the Lapis Erg), keep the three elites (Bell Mammoth, Aurora Manta,
Crevasse Leviathan) and add no new one, rebuild the hub and add three outposts.

The old Frostwake people stay (their ids are saved progress and the Spark network): the captain, healer, surveyor, trader and snow scout in the Station, the bellkeeper at the Bellward Post, the
aurora watcher at the Aurora Post, the leviathan watcher and the Meeting Stone at the Ribwatch Camp. Every old `frostwake_*` and `es_22` id stays; texts are rewritten only where the geography
changed. Fourteen quests are new: new ids start `fws_`, new people `fw_` and stay within 19 characters (the accept string is capped at 32). Levels 85-90, rewardXp =
levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(85, 92)}
GOLD = {85: 9400, 86: 10300, 87: 11200, 88: 12100, 89: 13000, 90: 13900}

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is the Station; the three outposts are camps.
HAMLETS = {
    'station':  dict(name='Frostwake Station', x=124, y=268, hw=22, hh=17, city=True),
    'bellward': dict(name='Bellward Post', x=168, y=186, hw=12, hh=11),
    'aurora':   dict(name='Aurora Post', x=226, y=62, hw=12, hh=11),
    'ribwatch': dict(name='Ribwatch Camp', x=168, y=40, hw=12, hh=11),
}

# kind, x, y: the Bell Mammoth on the western shelf, the Aurora Manta under the eastern cliff, the Crevasse Leviathan in the far north-east (all three with a quest, as before)
ELITES = [('bellmammoth', 112, 206), ('auroramanta', 252, 108), ('crevasseleviathan', 240, 20)]
AWARENESS = {'bellmammoth': 16., 'auroramanta': 18., 'crevasseleviathan': 19.}

LODGE = dict(r=0, width=4, depth=3)       # the Frostwake lodge (isometric City.art): a timber hall with a snow-laden hip roof
BOARD = dict(r=.4, width=1.3, depth=.4)
BENCH = dict(r=0, width=1.5, depth=.45)

DRESSING = {
    'station': [
        ('frostwake_lodge', -16, -3, dict(LODGE, v=0)), ('frostwake_lodge', 4, -10, dict(LODGE, v=1)), ('frostwake_lodge', -3, 13, dict(LODGE, v=2)),
        ('frostwake_signal', 5, -4, dict(r=.7, v=0)), ('frostwake_hearth', -5.5, 6.5, dict(r=.8, v=0)), ('bench', 9, 2, BENCH),
        ('noticeboard', 3, 4, dict(BOARD, label='Frostwake Station')), ('frostwake_lantern', 14, -5, dict(r=.17, v=0)), ('frostwake_lantern', -14, 8, dict(r=.17, v=1)),
    ],
    'bellward': [
        ('frostwake_lodge', 0, -6.5, dict(LODGE, v=0)), ('frostwake_lodge', -6, 1, dict(LODGE, v=1)),
        ('noticeboard', 5, -7, dict(BOARD, label='Bellward Post')), ('frostwake_hearth', 3.2, 5.4, dict(r=.8, v=0)), ('bench', 6, -3, BENCH), ('frostwake_signal', -9, 6, dict(r=.7, v=0)),
    ],
    'aurora': [
        ('frostwake_lodge', 0, -6.5, dict(LODGE, v=1)), ('frostwake_lodge', -6, 1, dict(LODGE, v=2)),
        ('noticeboard', 5, -7, dict(BOARD, label='Aurora Post')), ('frostwake_hearth', 3.2, 5.4, dict(r=.8, v=0)), ('bench', 6, -3, BENCH), ('frostwake_signal', -9, 6, dict(r=.7, v=0)),
    ],
    'ribwatch': [
        ('frostwake_lodge', 0, -6.5, dict(LODGE, v=2)), ('frostwake_lodge', -6, 1, dict(LODGE, v=0)),
        ('noticeboard', 5, -7, dict(BOARD, label='Ribwatch Camp')), ('frostwake_hearth', 3.2, 5.4, dict(r=.8, v=0)), ('bench', 6, -3, BENCH), ('frostwake_signal', -9, 6, dict(r=.7, v=0)),
        ('meetingstone', 7.8, 3.8, dict(r=1.7, v=0)),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy) from the plaza
HUB_NPCS = {'frostwake_captain': ('station', -2, 1), 'frostwake_healer': ('station', -12, 5), 'frostwake_surveyor': ('station', 12, -9), 'frostwake_trader': ('station', 7, 9),
            'frostwake_scout': ('station', -10, -8), 'frostwake_bellkeeper': ('bellward', -3, -1), 'frostwake_skywatcher': ('aurora', -3, -1), 'frostwake_ribkeeper': ('ribwatch', -3, -1),
            'frostwake_stone': ('ribwatch', 9.5, 5.5)}
STATION_PEOPLE = {'travel_frostwake': (15, 6), 'mailbox_26_frostwake_station': (17.5, 8.5)}

NPCS = [
    dict(id='fw_bw_brynja', hamlet='bellward', dx=5, dy=3, name='Sled-Reeve Brynja Coldmark', role='Sled reeve', color='#b5daef',
         look=dict(skin='#c99b7a', hair='#d9e9ee', style='long', hat='hood', hatColor='#4680a1'),
         dialogue='The sled teams walk the Lantern Road between the Station and this post, and every hare and heron on the slopes wants their feed. The Mammoth Bells hang south-west of here. Do not ring them.'),
    dict(id='fw_bw_trader', hamlet='bellward', dx=-6, dy=5.6, name='Hakon Frostpeddler', role='Outpost trader', color='#b5daef', trader=True,
         look=dict(skin='#a77250', hair='#8a8f98', style='short', hat='none', hatColor='#4680a1'),
         dialogue='Tonics, stew and warm wool for the sled crews. I sell at cost: the shelf keeps the rest.'),
    dict(id='fw_au_sigrun', hamlet='aurora', dx=5, dy=3, name='Lamp-Warden Sigrun Glimmer', role='Lamp warden', color='#b5daef',
         look=dict(skin='#e0b89a', hair='#2a2a32', style='long', hat='hood', hatColor='#4680a1'),
         dialogue='The aurora lamps along the eastern cliff burn blue when the manta passes over them. Beyond the cliff stands the wall, and it has no gate on our side: whoever raised it wanted the Yearwheel left alone.'),
    dict(id='fw_au_trader', hamlet='aurora', dx=-6, dy=5.6, name='Ola Rimecoat', role='Outpost trader', color='#b5daef', trader=True,
         look=dict(skin='#d9b08c', hair='#5a3a2a', style='short', hat='none', hatColor='#4680a1'),
         dialogue='Hot stew, tonics and wool-lined boots. Nothing here is sold above cost, and the aurora is free.'),
    dict(id='fw_rw_leif', hamlet='ribwatch', dx=5, dy=3, name='Rope-Master Leif Deepline', role='Rope master', color='#b5daef',
         look=dict(skin='#8a6248', hair='#c9c2b4', style='short', hat='hood', hatColor='#4680a1'),
         dialogue='Every crack in the north is roped and numbered by this camp. The Deep Ice Rib stands east of us and the Leviathan sleeps beyond it. I mark the cracks. I do not climb them.'),
    dict(id='fw_rw_trader', hamlet='ribwatch', dx=-6, dy=5.6, name='Solvei Snowpack', role='Outpost trader', color='#b5daef', trader=True,
         look=dict(skin='#e0b89a', hair='#6a4a3a', style='long', hat='none', hatColor='#4680a1'),
         dialogue='Tonics, stew and spare rope for the crack crews. I sell at cost: the north keeps the rest.'),
]
TRAVEL_NAMES = {'bellward': 'Travel Master Birgit', 'aurora': 'Travel Master Torvald', 'ribwatch': 'Travel Master Maja'}

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each); the old Frostwake places keep their ids
PLACES = [
    dict(id='frostwake_pool', name='Pool Beneath the Ice', x=208, y=84, r=5),
    dict(id='frostwake_obelisk', name='Aurora Obelisk', x=244, y=46, r=5),
    dict(id='frostwake_rib', name='Deep Ice Rib', x=198, y=26, r=5),
    dict(id='fw_bells', name='The Mammoth Bells', x=146, y=207, r=6),
    dict(id='fw_fissures', name='The Blue Fissures', x=216, y=240, r=6),
    dict(id='fw_cliff', name='The Eastern Cliff', x=230, y=130, r=6),
    dict(id='fw_crack', name='The Northern Crack', x=176, y=16, r=6),
    dict(id='fws_st_m', name='The Station Lantern', x=88, y=262, r=2.1, waves=[dict(at=1, tag='fws_st_m#a'), dict(at=11, tag='fws_st_m#b')]),
    dict(id='fws_bw_m', name='The Bellward Circle', x=140, y=176, r=2.1, waves=[dict(at=1, tag='fws_bw_m#a'), dict(at=11, tag='fws_bw_m#b')]),
    dict(id='fws_au_m', name='The Aurora Circle', x=203, y=72, r=2.1, waves=[dict(at=1, tag='fws_au_m#a'), dict(at=11, tag='fws_au_m#b')]),
    dict(id='fws_rw_m', name='The Ribwatch Circle', x=150, y=66, r=2.1, waves=[dict(at=1, tag='fws_rw_m#a'), dict(at=11, tag='fws_rw_m#b')]),
]
ES22 = (208.0, 194.0)             # the Empty Seat's echo circle (chapter 22): east of the Bellward Post; the foe stands two tiles east of it

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('snowhare', 82, 258, 'fws_st_m#a'), ('snowhare', 94, 266, 'fws_st_m#a'), ('glaciercrab', 82, 266, 'fws_st_m#b'), ('glaciercrab', 94, 258, 'fws_st_m#b'),
    ('frostheron', 134, 172, 'fws_bw_m#a'), ('frostheron', 146, 180, 'fws_bw_m#a'), ('snowhare', 134, 180, 'fws_bw_m#b'), ('snowhare', 146, 172, 'fws_bw_m#b'),
    ('frostheron', 197, 68, 'fws_au_m#a'), ('frostheron', 209, 76, 'fws_au_m#a'), ('iceotter', 197, 76, 'fws_au_m#b'), ('iceotter', 209, 68, 'fws_au_m#b'),
    ('glaciercrab', 144, 62, 'fws_rw_m#a'), ('glaciercrab', 156, 70, 'fws_rw_m#a'), ('iceotter', 144, 70, 'fws_rw_m#b'), ('iceotter', 156, 62, 'fws_rw_m#b'),
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
    # the Station
    Q('fws_st_hold', 'Keep the Station Lantern Lit', 'frostwake_captain', 85,
      'The great lantern on the ice west of the Station gutters whenever the hares come down from the flats, and then the sleds lose the road in the white. Stand in the circle beside it for twenty seconds while Svala relights it, and let nothing reach her.',
      [('hold', 'fws_st_m', 'Keep the Station Lantern Lit', 20)], requires='frostwake_welcome'),
    Q('fws_rounds', 'Posts of the Shelf', 'frostwake_captain', 86,
      'Three posts watch the shelf beyond the Station: the Bellward Post on the western slopes, the Aurora Post in the north-east and the Ribwatch Camp on the northern rim. Svala wants their keepers told that the Lantern Road is open. Speak with Ylva, Vessa and Irik, and use the Travel Masters if the walk is long.',
      [('talk', 'frostwake_bellkeeper', 'Speak with Ylva Bellward at the Bellward Post', 1), ('talk', 'frostwake_skywatcher', 'Speak with Vessa Aurora at the Aurora Post', 1),
       ('talk', 'frostwake_ribkeeper', 'Speak with Irik Deepice at the Ribwatch Camp', 1)], requires='frostwake_welcome'),
    # Bellward Post, on the western slopes
    Q('fws_bw_bells', 'Out to the Mammoth Bells', 'fw_bw_brynja', 86,
      'South-west of the post the bronze bells hang in their frame, and the snow hares have started nesting beneath them, which rings them at the wrong hour. Walk out to the Mammoth Bells and defeat four Snow Hares on the way.',
      [('visit', 'fw_bells', 'Reach the Mammoth Bells', 1), ('kill', 'snowhare', 'Defeat Snow Hares on the way', 4)], requires='frostwake_welcome'),
    Q('fws_bw_fur', 'Fur for the Sled Teams', 'frostwake_bellkeeper', 86,
      'Ylva lines the harnesses of the sled teams with hare fur, which stays soft in the hardest frost. Bring her five Snow Hare Furs.',
      [('bring', 'snowhare_fur', 'Bring Snow Hare Furs', 5)], requires='fws_bw_bells'),
    Q('fws_bw_hold', 'Hold the Bellward Circle', 'fw_bw_brynja', 87,
      'The warning bell west of the post rings itself whenever the herons gather, and then every wing on the slopes comes to answer it. Stand in the circle beside it for twenty seconds while Brynja muffles the bell, and keep them off her.',
      [('hold', 'fws_bw_m', 'Hold the Bellward Circle', 20)], requires='fws_bw_bells'),
    Q('fws_bw_fissures', 'Down to the Blue Fissures', 'fw_bw_brynja', 88,
      'South-east of the post the glacier splits into long blue fissures, and the crabs that live in them have started to climb out. Walk down to the Blue Fissures and defeat five Glacier Crabs there.',
      [('visit', 'fw_fissures', 'Reach the Blue Fissures', 1), ('kill', 'glaciercrab', 'Defeat Glacier Crabs in the fissures', 5)], requires='fws_bw_hold'),
    # Aurora Post, in the north-east
    Q('fws_au_cliff', 'Under the Eastern Cliff', 'fw_au_sigrun', 87,
      'South of the post the Eastern Cliff drops to the wall, and the frost herons nest along its foot. Sigrun wants a count. Walk down to the Eastern Cliff and defeat four Frost Herons on the way.',
      [('visit', 'fw_cliff', 'Reach the Eastern Cliff', 1), ('kill', 'frostheron', 'Defeat Frost Herons on the way', 4)], requires='frostwake_welcome'),
    Q('fws_au_feathers', 'Feathers for the Aurora Lamps', 'frostwake_skywatcher', 88,
      'Vessa trims the aurora lamps with heron feather, which scatters the light into colours. Bring her five Frost Heron Feathers.',
      [('bring', 'heron_feather', 'Bring Frost Heron Feathers', 5)], requires='fws_au_cliff'),
    Q('fws_au_hold', 'Hold the Aurora Circle', 'fw_au_sigrun', 88,
      'The signal chime west of the post rings whenever the herons gather, and then every wing on the cliff comes down to it. Stand in the circle beside it for twenty seconds while Sigrun grounds the chime, and keep the flock off her.',
      [('hold', 'fws_au_m', 'Hold the Aurora Circle', 20)], requires='fws_au_cliff'),
    Q('fws_au_pools', 'Round the Frozen Pool', 'fw_au_sigrun', 89,
      'South-west of the post the Pool Beneath the Ice stays clear all winter, and the otters that live under it have grown bold. Walk down to the pool and defeat five Ice Otters there.',
      [('visit', 'frostwake_pool', 'Reach the Pool Beneath the Ice', 1), ('kill', 'iceotter', 'Defeat Ice Otters at the pool', 5)], requires='fws_au_hold'),
    # Ribwatch Camp, on the northern rim
    Q('fws_rw_rib', 'Up to the Deep Ice Rib', 'fw_rw_leif', 88,
      'East of the camp the Deep Ice Rib stands out of the snow, and the otters have dug in around it. Leif wants a count. Walk up to the rib and defeat four Ice Otters on the way.',
      [('visit', 'frostwake_rib', 'Reach the Deep Ice Rib', 1), ('kill', 'iceotter', 'Defeat Ice Otters on the way', 4)], requires='frostwake_welcome'),
    Q('fws_rw_pelts', 'Pelts for the Rope Crews', 'frostwake_ribkeeper', 89,
      'The crews wrap their rope handles in otter pelt, which does not freeze to the hand. Bring Irik five Ice Otter Pelts.',
      [('bring', 'iceotter_pelt', 'Bring Ice Otter Pelts', 5)], requires='fws_rw_rib'),
    Q('fws_rw_hold', 'Hold the Ribwatch Circle', 'fw_rw_leif', 89,
      'The rope winch south-west of the camp screams whenever the crabs gather, and then every shell in the north comes to it. Stand in the circle beside it for twenty seconds while Leif frees the winch, and keep them off him.',
      [('hold', 'fws_rw_m', 'Hold the Ribwatch Circle', 20)], requires='fws_rw_rib'),
    Q('fws_rw_crabs', 'The Northern Crack', 'fw_rw_leif', 90,
      'North of the camp the shelf cracks open along the coast, and the glacier crabs crowd its lip. Walk to the Northern Crack and defeat five Glacier Crabs there, and go no closer to the edge alone.',
      [('visit', 'fw_crack', 'Reach the Northern Crack', 1), ('kill', 'glaciercrab', 'Defeat Glacier Crabs at the crack', 5)], requires='fws_rw_hold'),
]

# Old ids, new meaning (only where the geography changed): the texts that named no place stay as they were
REWRITES = {
    'frostwake_mammoth': dict(description='Three companions should face the Bell Mammoth on the western shelf, west of the Mammoth Bells.'),
    'frostwake_manta': dict(description='Four companions must bring down the Aurora Manta beneath the Eastern Cliff, south-east of the Aurora Post.'),
    'frostwake_leviathan': dict(description='Five companions must silence the Crevasse Leviathan beyond the Deep Ice Rib, far along the northern shelf.'),
    'frostwake_patrol': dict(description='Patrol the Lantern Road between Frostwake Station and the Bellward Post.'),
    'frostwake_onward': dict(description='Cross into the Frostwake Shelf from Sunward Vale or the Stormglass Flats and report to Captain Svala Northlight at Frostwake Station.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {
    'frostwake_captain': dict(dialogue='The blue fissures change with the snow. Follow our lantern road north from the Station, and keep your eyes on the aurora.'),
    'frostwake_surveyor': dict(dialogue='The glass-blue breaks mark old pressure lines. The Blue Fissures lie south-east of the Bellward Post, and the Deep Ice Rib in the north belongs to something still awake.'),
    'frostwake_bellkeeper': dict(dialogue='When the old mammoth moves, every bronze bell on the western shelf answers. The Mammoth Bells hang south-west of this post.'),
    'frostwake_skywatcher': dict(dialogue='The manta swims through curtains of light above the Eastern Cliff, south-east of this post.'),
    'frostwake_ribkeeper': dict(dialogue='The shape below the crevasse can swallow a whole caravan. The Deep Ice Rib is east of this camp and the Leviathan lies beyond it. Bring five companions.'),
}
TAGLINE = 'Pale glaciers, blue crevasses and aurora lanterns: three elites, a station in the south, three outposts and a wall against the Yearwheel'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['frostwake_healer']['offers']
    supplier = by['frostwake_trader']['offers']
    hub = by['travel_frostwake']
    box = by['mailbox_26_frostwake_station']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = [k for k in hamlets if k != 'station']
    spots = {'bellward': (-1, 3.5), 'aurora': (-1, 3.5), 'ribwatch': (-1, 3.5)}
    for key in keys:
        dx, dy = spots[key]
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[], name=TRAVEL_NAMES[key])
        out.append(t)
    boxes = {'bellward': (-3.5, 5.2), 'aurora': (-3.5, 5.2), 'ribwatch': (-2, 3)}
    for key in keys:
        dx, dy = boxes[key]
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_26_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Frostwake entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 26]
    for key, h in hamlets.items():
        box_id = 'mailbox_26_frostwake_station' if key == 'station' else f'mailbox_26_{key}'
        box = next(n for n in zone['npcs'] if n['id'] == box_id)
        m = next(n for n in zone['npcs'] if n['id'] == ('travel_frostwake' if key == 'station' else f'travel_{key}'))
        directory.append(dict(id=box['id'], zone=26, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
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
    keys = [k for k in hamlets if k != 'station']
    for n in zone['npcs']:
        if n['id'] == 'travel_frostwake':
            n['travelStop'] = hamlets['station']['name']
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + [f'travel_{k}' for k in keys]))
        elif n['id'].startswith('travel_') and n.get('travelStop') in {h['name'] for h in hamlets.values()}:
            n['travelLinks'] = list(dict.fromkeys(n['travelLinks'] + ['travel_frostwake'] + [f'travel_{k}' for k in keys if f'travel_{k}' != n['id']]))
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
