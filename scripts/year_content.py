"""The Yearwheel's hubs, people, quests and places. Data for scripts/year_design.py (shaped coordinates, zone 28, k = 2.8).

Owner request 2026-11-09: "for pilot. reshape yearwheel. and remake the zone and quests to fit the new shape. no fillers. Seamless through the vault to sunward vale. This one could keep the
2.8 tiles per pixel. Just have the vault towards sunvale be seamless". Owner answers (AskUserQuestion): keep the four season towns (Springmere, Solhaven, Harvestwatch, Rimehold) round the
Equinox Crossing and add three outposts; keep the 12 seasonal elites and add one with no quest; the same isometric wall on the Yearwheel side of the Lapis and Frostwake borders.

Every old Yearwheel id stays (saved progress, the Spark network, the dungeon doors): the four towns keep their people, their quests and their sealed doors; the people move with their town by the
offset they had from its plaza. Fifteen quests are new: new ids start `yrs_` (at most 19 characters: the accept string is capped at 32), new people `yo_`. Levels 95-99, rewardXp =
levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())


def xp(level):
    return (LEVELS[level - 1] if level <= len(LEVELS) else LEVELS[-1] + (level - len(LEVELS)) * 2300) // 10


GOLD = {95: 11000, 96: 11500, 97: 12000, 98: 12500, 99: 13000}

CENTRE = (440, 480)                 # the Equinox Crossing: the four seasons meet here (client: zdef.yearCentre)
OLD_CENTRE = (200, 200)

# the four towns (plaza, half width/height of the sanctuary rectangle) and the three outposts; `season` 0 spring (south-west), 1 summer (south-east), 2 autumn (north-east), 3 winter (north-west)
HAMLETS = {
    'springmere':   dict(name='Springmere', x=300, y=770, hw=20, hh=19, city=True, season=0, key='sp', old=(76, 324)),
    'solhaven':     dict(name='Solhaven', x=620, y=660, hw=20, hh=19, season=1, key='su', old=(320, 316)),
    'harvestwatch': dict(name='Harvestwatch', x=620, y=300, hw=20, hh=19, season=2, key='au', old=(321, 78)),
    'rimehold':     dict(name='Rimehold', x=320, y=300, hw=20, hh=19, season=3, key='wi', old=(78, 78)),
    'wheelmark':    dict(name='Wheelmark Post', x=336, y=128, hw=12, hh=11, season=3, key='wm'),
    'tidehollow':   dict(name='Tidehollow Camp', x=690, y=470, hw=12, hh=11, season=2, key='th'),
    'lowfall':      dict(name='Lowfall Rest', x=480, y=650, hw=12, hh=11, season=1, key='lf'),
}
OUTPOSTS = ('wheelmark', 'tidehollow', 'lowfall')

# the sealed doors (gate object, portal 8 tiles south of it, place and arrival keep their old offsets from the object); the four doors stand on the outer sides of the quarters
GATES = {
    'sp': dict(x=232, y=598, old=(48, 229), place=(11, 9), portal='year_bloom_descent', arrive=(0, -2)),
    'su': dict(x=702, y=592, old=(352, 248), place=(-10, 10), portal='year_solar_descent', arrive=(-6, -8)),
    'au': dict(x=702, y=402, old=(352, 151), place=(-11, 9), portal='year_amber_descent', arrive=(6, -8)),
    'wi': dict(x=262, y=384, old=(47, 150), place=(11, 9), portal='year_solstice_descent', arrive=(0, -14)),
}
OLD_CROSSING = dict(blackhour=(208, 200), axle=(200, 200), guide=(212, 205), rigger=(218, 205), arrive=(214, 200))

# kind, x, y: three seasonal elites in each quarter (all with their quests, as before) and the new one with no quest
ELITES = [
    ('bloomtortoise', 262, 690), ('petalchimera', 392, 664), ('rainseraph', 430, 790),
    ('glasslion', 492, 577), ('sunwheel', 580, 540), ('firephoenix', 682, 705),
    ('lanternowl', 506, 369), ('harvestreaper', 572, 458), ('ambermantis', 686, 262),
    ('rimesaber', 277, 370), ('snowgiant', 394, 422), ('longnightwyrm', 446, 258),
    ('equinoxstag', 540, 170),
]
AWARENESS = {'bloomtortoise': 17., 'petalchimera': 18., 'rainseraph': 19., 'glasslion': 17., 'sunwheel': 18., 'firephoenix': 19., 'lanternowl': 18., 'harvestreaper': 19., 'ambermantis': 20.,
             'rimesaber': 18., 'snowgiant': 19., 'longnightwyrm': 21., 'equinoxstag': 19.}
ORDINARY = ['brooknewt', 'sundarter', 'acornmimic', 'snowstoat']       # by season: spring, summer, autumn, winter

LODGE = dict(r=0, width=5, depth=4)
BOARD = dict(r=.4, width=1.3, depth=.4)
BENCH = dict(r=0, width=1.5, depth=.45)

# the old people move with their town: they keep the offset from the plaza they had. The outposts and the new people stand beside their plaza
DRESSING = {
    'wheelmark': [
        ('year_lodge', 0, -6.5, dict(LODGE, v=3)), ('year_lodge', -6.5, 1, dict(LODGE, v=3)),
        ('noticeboard', 5, -7, dict(BOARD, label='Wheelmark Post')), ('campfire', 3.2, 5.4, dict(r=.65, v=3)), ('bench', 6, -3, BENCH), ('year_lantern', -9, 6, dict(r=.2, v=3)),
    ],
    'tidehollow': [
        ('year_lodge', 0, -6.5, dict(LODGE, v=2)), ('year_lodge', -6.5, 1, dict(LODGE, v=2)),
        ('noticeboard', 5, -7, dict(BOARD, label='Tidehollow Camp')), ('campfire', 3.2, 5.4, dict(r=.65, v=2)), ('bench', 6, -3, BENCH), ('year_lantern', -9, 6, dict(r=.2, v=2)),
    ],
    'lowfall': [
        ('year_lodge', 0, -6.5, dict(LODGE, v=1)), ('year_lodge', -6.5, 1, dict(LODGE, v=1)),
        ('noticeboard', 5, -7, dict(BOARD, label='Lowfall Rest')), ('campfire', 3.2, 5.4, dict(r=.65, v=1)), ('bench', 6, -3, BENCH), ('year_lantern', -9, 6, dict(r=.2, v=1)),
    ],
}

NPCS = [
    dict(id='yo_wm_ingrid', hamlet='wheelmark', dx=5, dy=3, name='Watcher Ingrid Cairnwatch', role='Northern watcher', color='#9dbbd0',
         look=dict(skin='#c99d78', hair='#cfd8e0', style='long', hat='hood', hatColor='#9dbbd0'),
         dialogue='From here the whole north of the wheel is white, and the stoats come down the pass at dusk. I count the tracks. Lately there are more than there were.'),
    dict(id='yo_wm_orm', hamlet='wheelmark', dx=-3, dy=5.6, name='Furrier Orm Silverpelt', role='Furrier', color='#9dbbd0',
         look=dict(skin='#a77250', hair='#3f342a', style='short', hat='hood', hatColor='#6f8da2'),
         dialogue='A stoat that has gone silver is worth more than a coat. I need furs, and the hunters of the pass bring me too few.'),
    dict(id='yo_wm_trader', hamlet='wheelmark', dx=-6, dy=-3, name='Hedda Frostpurse', role='Outpost trader', color='#9dbbd0', trader=True,
         look=dict(skin='#d9b08c', hair='#8a8f98', style='long', hat='hood', hatColor='#9dbbd0'),
         dialogue='Tonics, stew and a warm blanket for the pass. I sell at cost: the post keeps the rest.'),
    dict(id='yo_th_halvar', hamlet='tidehollow', dx=5, dy=3, name='Tidewarden Halvar Copperwave', role='Coast warden', color='#bb835e',
         look=dict(skin='#8a6248', hair='#c9c2b4', style='short', hat='hood', hatColor='#bb835e'),
         dialogue='The tide pulls back twice a day and the acorn mimics come down to the wet sand to feed. Mind your pockets on the shore. They look like acorns until they bite.'),
    dict(id='yo_th_sunniva', hamlet='tidehollow', dx=-3, dy=5.6, name='Gleaner Sunniva Amberhand', role='Gleaner', color='#bb835e',
         look=dict(skin='#e0b89a', hair='#a84e39', style='long', hat='hood', hatColor='#caa65f'),
         dialogue='I gather what the sea leaves, and every acorn that is not a mimic is mine. Bring me the real ones and I will make something of them.'),
    dict(id='yo_th_trader', hamlet='tidehollow', dx=-6, dy=-3, name='Brage Caskpurse', role='Outpost trader', color='#bb835e', trader=True,
         look=dict(skin='#a77250', hair='#5a3a2a', style='short', hat='hood', hatColor='#bb835e'),
         dialogue='Tonics, stew and dry rope for the shore. I sell at cost: the camp keeps the rest.'),
    dict(id='yo_lf_tove', hamlet='lowfall', dx=5, dy=3, name='Warden Tove Sunwheel', role='Plain warden', color='#e6b45c',
         look=dict(skin='#b78865', hair='#d2c39b', style='long', hat='hood', hatColor='#e6b45c'),
         dialogue='The plain south of the crossing bakes all day and the sundarters hunt in the heat. I keep this rest and I keep count of who walks out and who walks back.'),
    dict(id='yo_lf_arvid', hamlet='lowfall', dx=-3, dy=5.6, name='Potter Arvid Goldkiln', role='Potter', color='#e6b45c',
         look=dict(skin='#d9b08c', hair='#6a4a3a', style='short', hat='hood', hatColor='#caa65f'),
         dialogue='Sundarter scale glazes a pot like nothing else, and the plain has plenty. I fire what I can and sell the rest to the towns.'),
    dict(id='yo_lf_trader', hamlet='lowfall', dx=-6, dy=-3, name='Maja Dustpurse', role='Outpost trader', color='#e6b45c', trader=True,
         look=dict(skin='#e0b89a', hair='#8a8f98', style='long', hat='hood', hatColor='#e6b45c'),
         dialogue='Tonics, stew and water skins for the plain. I sell at cost: the rest keeps the well full.'),
]
TRAVEL_NAMES = {'wheelmark': 'Travel Master Frida', 'tidehollow': 'Travel Master Lars', 'lowfall': 'Travel Master Sigrid'}

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each); the old places keep their ids and offsets
PLACES = [
    dict(id='yw_cairn', name='The Wheelmark Cairn', x=360, y=100, r=6),
    dict(id='yw_pass', name='The Stoat Pass', x=292, y=196, r=6),
    dict(id='yw_shore', name='The Mimic Shore', x=716, y=400, r=6),
    dict(id='yw_tidepool', name='The Amber Tidepools', x=700, y=540, r=6),
    dict(id='yw_kiln', name='The Old Kilns', x=520, y=744, r=6),
    dict(id='yw_dust', name='The Dustwind Flats', x=600, y=760, r=6),
    dict(id='yrs_sp_m', name='The Springmere Weir', x=244, y=730, r=2.1, waves=[dict(at=1, tag='yrs_sp_m#a'), dict(at=11, tag='yrs_sp_m#b')]),
    dict(id='yrs_wm_m', name='The Wheelmark Circle', x=372, y=168, r=2.1, waves=[dict(at=1, tag='yrs_wm_m#a'), dict(at=11, tag='yrs_wm_m#b')]),
    dict(id='yrs_th_m', name='The Tidehollow Circle', x=668, y=420, r=2.1, waves=[dict(at=1, tag='yrs_th_m#a'), dict(at=11, tag='yrs_th_m#b')]),
    dict(id='yrs_lf_m', name='The Lowfall Circle', x=428, y=744, r=2.1, waves=[dict(at=1, tag='yrs_lf_m#a'), dict(at=11, tag='yrs_lf_m#b')]),
]

# Sleepers woken by a hold wave: two and two a wave, round the circle (the season's ordinary kind)
AMBUSH = []
for _pid, _kind in (('yrs_sp_m', 'brooknewt'), ('yrs_wm_m', 'snowstoat'), ('yrs_th_m', 'acornmimic'), ('yrs_lf_m', 'sundarter')):
    _p = next(p for p in PLACES if p['id'] == _pid)
    for _dx, _dy, _w in ((-6, -6, 'a'), (6, 6, 'a'), (-6, 6, 'b'), (6, -6, 'b')):
        AMBUSH.append((_kind, _p['x'] + _dx, _p['y'] + _dy, f'{_pid}#{_w}'))


def Q(id, title, npc, level, desc, objectives, requires=None, repeatable=False, gold=None, **extra):
    q = dict(id=id, title=title, npc=npc, description=desc,
             objectives=[dict(kind=k, target=t, label=l, count=c) for k, t, l, c in objectives],
             level=level, rewardXp=xp(level), rewardGold=gold or GOLD[level], requires=requires, repeatable=repeatable)
    reward = reward_for(id)
    if reward:
        q['rewardItem'] = reward
    q.update(extra)
    return q


QUESTS = [
    # Springmere (spring, south-west)
    Q('yrs_sp_hold', 'Keep the Weir Clear', 'yr_sp_lead', 96,
      'North-west of Springmere the old weir holds the spring water back from the meadows, and whenever the newts crowd the sluice the fields flood. Stand in the circle beside the weir for twenty seconds while Ilya clears it, and let nothing reach her.',
      [('hold', 'yrs_sp_m', 'Keep the Springmere Weir Clear', 20)], requires='yr_sp_intro'),
    Q('yrs_rounds', 'The Three Outposts', 'yr_sp_lead', 97,
      'Three outposts keep the far reaches of the wheel: Wheelmark Post in the north, Tidehollow Camp on the east coast and Lowfall Rest on the southern plain. Ilya wants their wardens told that the spring road is open again. Speak with Ingrid, Halvar and Tove, and use the Travel Masters if the road is long.',
      [('talk', 'yo_wm_ingrid', 'Speak with Ingrid Cairnwatch at Wheelmark Post', 1), ('talk', 'yo_th_halvar', 'Speak with Halvar Copperwave at Tidehollow Camp', 1),
       ('talk', 'yo_lf_tove', 'Speak with Tove Sunwheel at Lowfall Rest', 1)], requires='yr_sp_intro'),
    # Wheelmark Post (winter, north)
    Q('yrs_wm_cairn', 'Up to the Wheelmark Cairn', 'yo_wm_ingrid', 96,
      'North-east of the post the cairn that marks the wheel stands on its ridge, and the snow stoats have started to den under it. Walk up to the Wheelmark Cairn and defeat five Snow Stoats on the way.',
      [('visit', 'yw_cairn', 'Reach the Wheelmark Cairn', 1), ('kill', 'snowstoat', 'Defeat Snow Stoats on the way', 5)], requires='yr_wi_intro'),
    Q('yrs_wm_fur', 'Silver for the Furrier', 'yo_wm_orm', 97,
      'Orm lines the post blankets with silver stoat fur, which keeps out the wind of the pass. Bring him six Silver Stoat Furs.',
      [('bring', 'stoat_silverfur', 'Bring Silver Stoat Furs', 6)], requires='yrs_wm_cairn'),
    Q('yrs_wm_hold', 'Hold the Wheelmark Circle', 'yo_wm_ingrid', 97,
      'The signal horn south-east of the post sounds whenever the stoats gather, and then every claw in the pass comes to it. Stand in the circle beside it for twenty seconds while Ingrid muffles the horn, and keep them off her.',
      [('hold', 'yrs_wm_m', 'Hold the Wheelmark Circle', 20)], requires='yrs_wm_cairn'),
    Q('yrs_wm_pass', 'Down the Stoat Pass', 'yo_wm_ingrid', 98,
      'South-west of the post the pass runs down towards Rimehold, and the stoats have dug it hollow. Walk down to the Stoat Pass and defeat six Snow Stoats there.',
      [('visit', 'yw_pass', 'Reach the Stoat Pass', 1), ('kill', 'snowstoat', 'Defeat Snow Stoats in the pass', 6)], requires='yrs_wm_hold'),
    # Tidehollow Camp (autumn, east coast)
    Q('yrs_th_shore', 'Along the Mimic Shore', 'yo_th_halvar', 97,
      'North of the camp the shore runs out into wet sand, and the acorn mimics feed there at low tide. Walk down to the Mimic Shore and defeat five Acorn Mimics on the way.',
      [('visit', 'yw_shore', 'Reach the Mimic Shore', 1), ('kill', 'acornmimic', 'Defeat Acorn Mimics on the way', 5)], requires='yr_au_intro'),
    Q('yrs_th_acorns', 'Amber from the Sand', 'yo_th_sunniva', 98,
      'Sunniva grinds amber acorn into the resin she seals the camp boats with. Bring her six Amber Acorns.',
      [('bring', 'amber_acorn', 'Bring Amber Acorns', 6)], requires='yrs_th_shore'),
    Q('yrs_th_hold', 'Hold the Tidehollow Circle', 'yo_th_halvar', 98,
      'The tide bell north-west of the camp rings whenever the mimics gather, and then every one on the shore crawls towards it. Stand in the circle beside it for twenty seconds while Halvar stills the bell, and keep them off him.',
      [('hold', 'yrs_th_m', 'Hold the Tidehollow Circle', 20)], requires='yrs_th_shore'),
    Q('yrs_th_pools', 'The Amber Tidepools', 'yo_th_halvar', 99,
      'South of the camp the tidepools glow where the amber washes in, and the mimics have made them their own. Walk to the Amber Tidepools and defeat six Acorn Mimics there.',
      [('visit', 'yw_tidepool', 'Reach the Amber Tidepools', 1), ('kill', 'acornmimic', 'Defeat Acorn Mimics at the pools', 6)], requires='yrs_th_hold'),
    # Lowfall Rest (summer, southern plain)
    Q('yrs_lf_kiln', 'To the Old Kilns', 'yo_lf_tove', 96,
      'South-east of the rest the old kilns stand in a ring on the plain, and the sundarters nest in their ash. Walk out to the Old Kilns and defeat five Sundarters on the way.',
      [('visit', 'yw_kiln', 'Reach the Old Kilns', 1), ('kill', 'sundarter', 'Defeat Sundarters on the way', 5)], requires='yr_su_intro'),
    Q('yrs_lf_scales', 'Scales for the Glaze', 'yo_lf_arvid', 97,
      'Arvid grinds sundarter scale into his glaze, and the pots come out the colour of the plain at noon. Bring him six Sundarter Scales.',
      [('bring', 'sundarter_scale', 'Bring Sundarter Scales', 6)], requires='yrs_lf_kiln'),
    Q('yrs_lf_hold', 'Hold the Lowfall Circle', 'yo_lf_tove', 97,
      'The heat gong south-west of the rest rings by itself when the sundarters gather, and then every one on the plain comes to it. Stand in the circle beside it for twenty seconds while Tove stills the gong, and keep them off her.',
      [('hold', 'yrs_lf_m', 'Hold the Lowfall Circle', 20)], requires='yrs_lf_kiln'),
    Q('yrs_lf_dust', 'Across the Dustwind Flats', 'yo_lf_tove', 98,
      'Far to the south-east of the rest, beyond the kilns, the flats lie open to the dust wind, and the sundarters hunt there in packs. Walk out to the Dustwind Flats and defeat six Sundarters there.',
      [('visit', 'yw_dust', 'Reach the Dustwind Flats', 1), ('kill', 'sundarter', 'Defeat Sundarters on the flats', 6)], requires='yrs_lf_hold'),
    # the Equinox Crossing
    Q('yrs_crossing', 'Stand at the Crossing', 'null_guide', 99,
      'Sigrun says the four roads of the wheel meet at the axle, and that the axle has been turning slower than it should. Walk to the Equinox Crossing and defeat five Brook Newts on the way.',
      [('visit', 'yw_crossing', 'Reach the Equinox Crossing', 1), ('kill', 'brooknewt', 'Defeat Brook Newts on the way', 5)], requires='yr_sp_intro'),
]
PLACES.append(dict(id='yw_crossing', name='The Equinox Crossing', x=CENTRE[0], y=CENTRE[1] + 18, r=6))

# Old ids, new meaning (only where the geography changed): the texts that named no place stay as they were
REWRITES = {
    'yr_onward': dict(description='Cross the vault from Sunward Vale into the Yearwheel and report to Ilya Greenwake in Springmere.'),
}

# People whose words described the old map: changed text only
NPC_UPDATES = {}
TAGLINE = 'Four seasons turn around the Equinox Crossing: four towns, three outposts, thirteen elites, four sealed doors and one vault to Sunward Vale'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets, old):
    by = {n['id']: n for n in old['npcs']}
    healer = by['yr_sp_heal']['offers']
    supplier = by['yr_sp_trade']['offers']
    hub = by['travel_springmere']
    box = by['mailbox_28_springmere']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    for key in OUTPOSTS:
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] - 1, y=h['y'] + 3.5, travelStop=h['name'], travelLinks=[], name=TRAVEL_NAMES[key], art='year_%s_travel' % ['sp', 'su', 'au', 'wi'][h['season']])
        out.append(t)
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_28_{key}', x=h['x'] - 3.5, y=h['y'] + 5.2)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Yearwheel entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 28]
    for key, h in hamlets.items():
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_28_{key}')
        m = next(n for n in zone['npcs'] if n['id'] == f'travel_{key}')
        directory.append(dict(id=box['id'], zone=28, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def city_and_camps(hamlets):
    def rect(h):
        return dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                    plaza=dict(x=h['x'], y=h['y']), radius=8 if h['hw'] > 15 else 3.5, entry=dict(x=h['x'] - 12, y=h['y']) if h['hw'] > 15 else dict(x=h['x'], y=h['y'] + h['hh'] - 3))
    city = rect(hamlets['springmere'])
    return city, [rect(h) for k, h in hamlets.items() if k != 'springmere']


def install(world, zone, hamlets, old):
    """Idempotent, so `plan` also works on a map that already carries the design."""
    new_npcs = people(world, zone, hamlets, old)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        n.update(copy.deepcopy(NPC_UPDATES.get(n['id'], {})))
    # the Spark network: each outpost links to Springmere (the vault's town), to the town of its quarter and to the other two outposts (every link both ways)
    near = {'wheelmark': 'rimehold', 'tidehollow': 'harvestwatch', 'lowfall': 'solhaven'}
    pairs = set()
    for k in OUTPOSTS:
        pairs.add((f'travel_{k}', 'travel_springmere'))
        pairs.add((f'travel_{k}', f'travel_{near[k]}'))
        for o in OUTPOSTS:
            if o != k:
                pairs.add(tuple(sorted((f'travel_{k}', f'travel_{o}'))))
    by_id = {n['id']: n for n in zone['npcs']}
    for a, b in sorted(pairs):
        for x, y in ((a, b), (b, a)):
            if y not in by_id[x]['travelLinks']:
                by_id[x]['travelLinks'].append(y)
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
