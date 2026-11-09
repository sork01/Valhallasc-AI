"""The Stormglass Flats' outposts, people, quests, places and elites. Data for scripts/storm_design.py (shaped coordinates, zone 19).

Owner request 2026-11-08: "for pilot. reshape stormglass shore. probably rename it since its no shore. and remake the zone and quests to fit the new shape.
no fillers." Owner answers: the name is The Stormglass Flats, the zone is seamless against the Prismwaste (north) and the Obsidian Orrery (west), keep the
Maelstrom Heart and add two new elites (one with a quest, one without), three new outposts. Sunward Vale, Emberwake and Frostwake are not shaped, so they stay
rim gates; the Asterion gate stands on the compass rose and the Eye Below keeps its descent.

Every old `stormglass_*`, `arena_stormglass_*` and `es_15`/`es_go_15` id stays (saved progress, tests, quest_gear_rewards): texts are rewritten only where the
geography changed (the sea is gone: black sand, salt and lightning). Fifteen quests are new. New ids and people start `storm_` and stay within 19 characters
(the accept string is capped at 32), except the elite's own `stormglass_hermit`. Levels 60-65, rewardXp = levels.txt[level-1] / 10. Every text here needs its
Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(60, 66)}
GOLD = {60: 3400, 61: 3900, 62: 4300, 63: 4800, 64: 5300, 65: 6000}

# the outposts: plaza, half width/height of the sanctuary rectangle. Nothing art-less may stand within 20 tiles of the Prismwaste or Orrery border.
HAMLETS = {
    'rodstead': dict(name='Rodstead', x=100, y=152, hw=12, hh=11),
    'fulgur':   dict(name='Fulgur Post', x=112, y=64, hw=12, hh=11),
    'bankhold': dict(name='Bankhold', x=272, y=150, hw=12, hh=11),
}

# kind, x, y (the three elites: the Maelstrom Heart and the Lamphouse Hermit have a quest, the Stormtusk none; awareness is the 4th value of the server's attack profile)
ELITES = [('maelstromheart', 178, 50), ('lamphermit', 62, 228), ('stormtusk', 254, 284)]
ELITE_LEVEL = {'maelstromheart': 65, 'lamphermit': 63, 'stormtusk': 62}
AWARENESS = {'maelstromheart': 15., 'lamphermit': 12., 'stormtusk': 12.}

LODGE = dict(r=0, width=4.5, depth=3.5)

DRESSING = {
    'rodstead': [
        ('breakwater_hut', 0, -6.5, dict(LODGE)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#6f8aa0', label='Rod Watch')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#9fc3c9', label='Reedcask')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Rodstead')),
        ('stormlamp', -8, -1, dict(r=.28)), ('stormlamp', 9, -1, dict(r=.28)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -3, -2, dict(r=.4)),
    ],
    'fulgur': [
        ('breakwater_hut', 0, -6.5, dict(LODGE)),
        ('tent', -9, 5, dict(r=1.5, width=3, depth=2.4, color='#7a8ca8', label='Beacon Watch')),
        ('stall', 7, 4, dict(r=0, width=1.8, depth=1.2, color='#b8d0d0', label='Saltsworn')),
        ('noticeboard', -5, -7, dict(r=.4, width=1.3, depth=.4, label='Fulgur Post')),
        ('stormlamp', -8, -1, dict(r=.28)), ('stormlamp', 9, -1, dict(r=.28)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, 0, dict(r=.4)), ('brazier', 6, -2, dict(r=.4)),
    ],
    'bankhold': [
        ('breakwater_hut', 0, -6.5, dict(LODGE)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#6a7a8c', label='Wall Watch')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#a8b4b8', label='Wallbarrow')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Bankhold')),
        ('stormlamp', -8, -1, dict(r=.28)), ('stormlamp', 9, -1, dict(r=.28)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, -1, dict(r=.4)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
}

NPCS = [
    dict(id='storm_rs_edda', hamlet='rodstead', dx=-3, dy=-1, name='Rod-Warden Edda Ironrod', role='Rod warden', color='#8fb4d0',
         look=dict(skin='#e0bca0', hair='#c8d4e0', style='long', hat='hood', hatColor='#4a6a88'),
         dialogue='Every iron rod in the Reed Seeps draws the lightning down before it can reach the reeds, and every reed we save holds a little more water. West of here the Black Dunes run to the edge of the world, and south the Salt Pans glitter with glass rays. I keep the rods standing.'),
    dict(id='storm_rs_jorun', hamlet='rodstead', dx=5, dy=3, name='Jorun Reedweave', role='Reed weaver', color='#88a8a0',
         look=dict(skin='#c99b7a', hair='#3a3a4a', style='short', hat='none', hatColor='#6a7a7a'),
         dialogue='Saltclaw shell makes the only mat the lightning will not run through. Bring me enough and the rod-wardens can sleep on something that does not shock them.'),
    dict(id='storm_rs_trader', hamlet='rodstead', dx=-6, dy=4.6, name='Hild Seepmonger', role='Outpost trader', color='#9fc3c9', trader=True,
         look=dict(skin='#edc5a1', hair='#8a5a3a', style='long', hat='none', hatColor='#9fc3c9'),
         dialogue='Stew, tonics and dry blankets for anyone who stands rod-watch. Everything is sold at cost, because the weather charges enough.'),
    dict(id='storm_fp_halv', hamlet='fulgur', dx=-3, dy=-1, name='Lightkeeper Halv Stormeye', role='Lightkeeper', color='#b4c8e0',
         look=dict(skin='#d9b08c', hair='#e0e4ec', style='short', hat='hood', hatColor='#5a6a88'),
         dialogue='East of the post the Stormspire rises out of the plain, and every storm that crosses the flats ends in it. The gulls circle it as if it were a nest. I keep the beacon lit so the post can be found, and I count how many gulls come back.'),
    dict(id='storm_fp_ingrid', hamlet='fulgur', dx=5, dy=3, name='Ingrid Fulgursmith', role='Rodsmith', color='#a8b8c8',
         look=dict(skin='#c99b7a', hair='#6a3a2a', style='long', hat='none', hatColor='#8a9aa8'),
         dialogue='A gull\'s flight feather balances a lightning rod better than any counterweight. Bring me a handful and the post\'s rods will stand straight in the wind.'),
    dict(id='storm_fp_trader', hamlet='fulgur', dx=-5, dy=6.2, name='Brand Saltsworn', role='Outpost trader', color='#b8d0d0', trader=True,
         look=dict(skin='#edc5a1', hair='#4a4a5a', style='long', hat='none', hatColor='#b8d0d0'),
         dialogue='Bread, tonics and stew for the ones who watch the Stormspire. If the soup crackles, that is the weather, not the cook.'),
    dict(id='storm_bh_torvald', hamlet='bankhold', dx=-3, dy=-1, name='Bank-Warden Torvald Seawall', role='Wall warden', color='#9ab0c0',
         look=dict(skin='#edc5a1', hair='#cfd4dc', style='long', hat='hood', hatColor='#4a5a6a'),
         dialogue='The old sea wall runs along the Sunward Bank, and the breaker sentinels still stand on it, as if the sea might come back. East of here the Eye Basin lies where the whirlpool once turned. The road south-east goes on into Sunward Vale, and I would like it to stay a road.'),
    dict(id='storm_bh_sigrid', hamlet='bankhold', dx=5, dy=3, name='Sigrid Stonewright', role='Stonewright', color='#a8b4b8',
         look=dict(skin='#c99b7a', hair='#2a2a3a', style='short', hat='hood', hatColor='#4a5058'),
         dialogue='A breaker core keeps its warmth for years. Bring me four and I will set them into the wall, and the bank will hold its heat through the night.'),
    dict(id='storm_bh_trader', hamlet='bankhold', dx=-6, dy=5.6, name='Osk Wallbarrow', role='Outpost trader', color='#a8b4b8', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#a8b4b8'),
         dialogue='Thread, wicks and stew. If a sentinel turns its head, do not argue with it: buy a tonic from me.'),
]

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each)
PLACES = [
    dict(id='storm_dunes', name='The Black Dunes', x=58, y=128, r=6),
    dict(id='storm_pans', name='The Salt Pans', x=100, y=230, r=6),
    dict(id='storm_stand', name='The Stormspire', x=180, y=98, r=6),
    dict(id='storm_drift', name='The Northern Drift', x=92, y=40, r=6),
    dict(id='storm_basin', name='The Eye Basin', x=238, y=150, r=6),
    dict(id='storm_shards', name='The Low Shards', x=250, y=266, r=6),
    dict(id='storm_lamp_m', name='The Lamp Circle', x=120, y=244, r=2.1, waves=[dict(at=1, tag='storm_lamp_m#a'), dict(at=11, tag='storm_lamp_m#b')]),
    dict(id='storm_rod_m', name='The Rod Circle', x=128, y=148, r=2.1, waves=[dict(at=1, tag='storm_rod_m#a'), dict(at=11, tag='storm_rod_m#b')]),
    dict(id='storm_beacon_m', name='The Beacon Circle', x=128, y=44, r=2.1, waves=[dict(at=1, tag='storm_beacon_m#a'), dict(at=11, tag='storm_beacon_m#b')]),
    dict(id='storm_wall_m', name='The Wall Circle', x=276, y=112, r=2.1, waves=[dict(at=1, tag='storm_wall_m#a'), dict(at=11, tag='storm_wall_m#b')]),
]

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('saltclaw', 114, 238, 'storm_lamp_m#a'), ('saltclaw', 126, 250, 'storm_lamp_m#a'), ('saltclaw', 114, 250, 'storm_lamp_m#b'), ('saltclaw', 126, 238, 'storm_lamp_m#b'),
    ('glassray', 122, 142, 'storm_rod_m#a'), ('glassray', 134, 154, 'storm_rod_m#a'), ('glassray', 122, 154, 'storm_rod_m#b'), ('glassray', 134, 142, 'storm_rod_m#b'),
    ('stormgull', 122, 38, 'storm_beacon_m#a'), ('stormgull', 134, 50, 'storm_beacon_m#a'), ('stormgull', 122, 50, 'storm_beacon_m#b'), ('stormgull', 134, 38, 'storm_beacon_m#b'),
    ('breakersentinel', 270, 106, 'storm_wall_m#a'), ('breakersentinel', 282, 118, 'storm_wall_m#a'), ('breakersentinel', 270, 118, 'storm_wall_m#b'), ('breakersentinel', 282, 106, 'storm_wall_m#b'),
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
    # Breakwater Camp, in the south-west
    Q('storm_h_hold', 'Light the Lamps', 'stormglass_warden', 60,
      'The blue lamps north-east of Breakwater Camp gutter whenever the claws gather, and then the dark comes down on the camp. Stand in the circle there for twenty seconds while Thora relights them, and let nothing reach her.',
      [('hold', 'storm_lamp_m', 'Light the Lamps', 20)], requires='stormglass_welcome'),
    Q('storm_h_rounds', 'The Watchers of the Flats', 'stormglass_scholar', 64,
      'Three outposts watch the flats beyond Breakwater Camp: Rodstead among the Reed Seeps in the west, Fulgur Post in the north-west and Bankhold beside the Eye Basin in the east. Orrin wants their keepers told that the camp still stands. Speak with Edda, Halv and Torvald, and use the Travel Masters if the road is long.',
      [('talk', 'storm_rs_edda', 'Speak with Rod-Warden Edda Ironrod at Rodstead', 1), ('talk', 'storm_fp_halv', 'Speak with Lightkeeper Halv Stormeye at Fulgur Post', 1),
       ('talk', 'storm_bh_torvald', 'Speak with Bank-Warden Torvald Seawall at Bankhold', 1)], requires='stormglass_rays'),
    Q('stormglass_hermit', 'The Lamp in the Shell', 'stormglass_scout', 63,
      'A hermit as big as a barn has dragged a wrecked lamphouse across the Salt Pans, and the lamp still burns inside its shell, calling every claw on the flats. Find the Lamphouse Hermit among the salt pillars north-west of the camp, far from any road, and bring two companions.',
      [('kill', 'lamphermit', 'Defeat the Lamphouse Hermit', 1)], requires='stormglass_rays', group=True, recommendedPlayers=3),
    # Rodstead, among the Reed Seeps
    Q('storm_rs_walk', 'Out to the Black Dunes', 'storm_rs_edda', 61,
      'The Black Dunes lie west of Rodstead, where the sand piles against the edge of the world, and the claws have buried the rod stakes. Edda wants a count of what lives there. Walk out to the Black Dunes and defeat four Saltclaws on the way.',
      [('visit', 'storm_dunes', 'Reach the Black Dunes', 1), ('kill', 'saltclaw', 'Defeat Saltclaws on the way', 4)], requires='stormglass_crabs'),
    Q('storm_rs_reeds', 'Shells for the Weaver', 'storm_rs_jorun', 61,
      'Jorun weaves saltclaw shell into mats the lightning will not run through. Bring her five Saltclaw Shells.',
      [('bring', 'saltclaw_shell', 'Bring Saltclaw Shells', 5)], requires='storm_rs_walk'),
    Q('storm_rs_hold', 'Hold the Rod Circle', 'storm_rs_edda', 62,
      'The tallest rod east of Rodstead throws sparks whenever a storm gathers, and then every ray in the seeps comes to answer it. Stand in the circle beside it for twenty seconds while Edda grounds it, and keep the rays off her.',
      [('hold', 'storm_rod_m', 'Hold the Rod Circle', 20)], requires='storm_rs_walk'),
    Q('storm_rs_pans', 'Down to the Salt Pans', 'storm_rs_edda', 62,
      'South of Rodstead the Salt Pans glitter, and the glass rays glide across them in the dark. Walk down to the Salt Pans and defeat five Glass Rays there, then tell Edda how many still fly.',
      [('visit', 'storm_pans', 'Reach the Salt Pans', 1), ('kill', 'glassray', 'Defeat Glass Rays on the Salt Pans', 5)], requires='storm_rs_hold'),
    # Fulgur Post, in the north-west
    Q('storm_fp_walk', 'Under the Stormspire', 'storm_fp_halv', 62,
      'East of the post the Stormspire rises out of the plain, and the gulls circle it as if it were a nest. Halv wants to know what lives at its foot. Walk out to the Stormspire and defeat four Stormgulls on the way.',
      [('visit', 'storm_stand', 'Reach the Stormspire', 1), ('kill', 'stormgull', 'Defeat Stormgulls on the way', 4)], requires='stormglass_gulls'),
    Q('storm_fp_feathers', 'Feathers for the Rodsmith', 'storm_fp_ingrid', 62,
      'Ingrid balances her rods with the flight feathers of the gulls that circle the Stormspire. Bring her five Stormgull Feathers.',
      [('bring', 'stormgull_feather', 'Bring Stormgull Feathers', 5)], requires='storm_fp_walk'),
    Q('storm_fp_hold', 'Keep the Beacon Lit', 'storm_fp_halv', 63,
      'The beacon north-east of the post gutters whenever the gulls gather, and then the dark comes down on Fulgur Post. Stand in the circle at the beacon for twenty seconds while Halv feeds the flame, and keep the gulls off him.',
      [('hold', 'storm_beacon_m', 'Keep the Beacon Lit', 20)], requires='storm_fp_walk'),
    Q('storm_fp_drift', 'The Northern Drift', 'storm_fp_halv', 63,
      'North-west of the post the black sand piles in drifts against the Prismwaste, and the gulls roost on the tallest of them. Walk out to the Northern Drift and defeat five Stormgulls there.',
      [('visit', 'storm_drift', 'Reach the Northern Drift', 1), ('kill', 'stormgull', 'Defeat Stormgulls on the Drift', 5)], requires='storm_fp_hold'),
    # Bankhold, beside the Eye Basin (moved inland from the old sea wall, 2026-11-09, when Sunward Vale became a seam: storm_design.late_move_bankhold)
    Q('storm_bh_walk', 'Across the Eye Basin', 'storm_bh_torvald', 63,
      'East of Bankhold the Eye Basin lies where the sea\'s whirlpool once turned, and the breaker sentinels stand in rings round it. Torvald wants a count. Walk out to the Eye Basin and defeat four Breaker Sentinels on the way.',
      [('visit', 'storm_basin', 'Reach the Eye Basin', 1), ('kill', 'breakersentinel', 'Defeat Breaker Sentinels on the way', 4)], requires='stormglass_rays'),
    Q('storm_bh_cores', 'Cores for the Stonewright', 'storm_bh_sigrid', 63,
      'Sigrid sets breaker cores into the sea wall so it keeps its warmth through the night. Bring her four Breaker Cores.',
      [('bring', 'breaker_core', 'Bring Breaker Cores', 4)], requires='storm_bh_walk'),
    Q('storm_bh_hold', 'Hold the Wall Circle', 'storm_bh_torvald', 64,
      'The old sea wall north-east of Bankhold flares whenever the sentinels stir, and then every sentinel in the basin comes to answer it. Stand in the circle on the wall for twenty seconds while Torvald steadies it, and keep the sentinels off him.',
      [('hold', 'storm_wall_m', 'Hold the Wall Circle', 20)], requires='storm_bh_walk'),
    Q('storm_bh_shards', 'Down to the Low Shards', 'storm_bh_torvald', 64,
      'Far to the south, below the end of the road along the wall, the Low Shards stand in the dark and the rays glide between them. Walk down to the Low Shards and defeat five Glass Rays there.',
      [('visit', 'storm_shards', 'Reach the Low Shards', 1), ('kill', 'glassray', 'Defeat Glass Rays at the Low Shards', 5)], requires='storm_bh_hold'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'stormglass_crabs': dict(description='Drive the Saltclaws out of the black sand round Breakwater Camp and the Salt Pans.'),
    'stormglass_gulls': dict(description='Stop the Stormgulls from circling the camp and the lamp-lit roads.'),
    'stormglass_rays': dict(title='Glass in the Sand', description='Bring the fins of the glass rays that glide over the Salt Pans and the Rodfields.'),
    'stormglass_guards': dict(description='Silence the old Breaker Sentinels that stand watch over the roads to the Eye Basin.'),
    'stormglass_heart': dict(description='The living storm has taken shape at the foot of the Stormspire. Gather five companions.'),
}

# People whose words described a sea: changed text only
NPC_UPDATES = {
    'stormglass_warden': dict(dialogue='Asterion sent us to listen to the dry sea bed. The sea left in thunder, and the thunder has never stopped. Meet the crew before you follow its voice.'),
    'stormglass_scout': dict(role='Flats scout', dialogue='Gulls strike from the air, rays glide over the sand. The old sentinels wake whenever the lightning turns.'),
    'stormglass_trader': dict(dialogue='I pay for what the sea left behind. Take provisions before you cross the flats.'),
    'stormglass_watcher': dict(dialogue='The Eye Below has opened. Gather five at the stone, then follow the living lens beneath the basin. All three wardens must fall before the far passage wakes.'),
    'stormglass_stone': dict(dialogue='The runes gather companions for a fee that grows with your level. The Eye Below is open to heroes of level 65 and above. Enter together; each party receives its own descent.'),
}
TAGLINE = 'Black sand, white lightning, and a sealed eye beneath the dry sea bed'
FUTURE = 'An open five-player descent beneath the dry sea bed.'


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    hub = next(n for n in zone['npcs'] if n['id'] == 'travel_breakwater')
    healer = next(n for n in zone['npcs'] if n['id'] == 'stormglass_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'stormglass_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    spots = {'rodstead': (-1, 2), 'fulgur': (-1, 3.5), 'bankhold': (-1, 3.5)}
    keys = list(spots)
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'],
                 travelLinks=['travel_breakwater'] + [f'travel_{k}' for k in keys if k != key])
        out.append(t)
        if t['id'] not in hub['travelLinks']:
            hub['travelLinks'].append(t['id'])
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_19_breakwater_camp')
    for key, (dx, dy) in {'rodstead': (3, 1), 'fulgur': (2, 1), 'bankhold': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_19_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Stormglass entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 19]
    names = {'travel_breakwater': ('Breakwater Camp', 'mailbox_19_breakwater_camp')}
    for key, h in hamlets.items():
        names['travel_' + key] = (h['name'], f'mailbox_19_{key}')
    for master, (hub, boxid) in names.items():
        box = next(n for n in zone['npcs'] if n['id'] == boxid)
        m = next(n for n in zone['npcs'] if n['id'] == master)
        directory.append(dict(id=box['id'], zone=19, hub=hub, x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(zone, hamlets):
    """Idempotent, so `plan` also works on a map that already carries the design."""
    new_npcs = people(zone, hamlets)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        n.update(copy.deepcopy(NPC_UPDATES.get(n['id'], {})))
    ids = {p['id'] for p in PLACES}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    ids = {q['id'] for q in QUESTS}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids]
    zone['camps'] = camps(hamlets)
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    zone['tagline'] = TAGLINE
    zone['futureInstance']['description'] = FUTURE
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
