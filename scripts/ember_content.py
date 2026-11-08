"""Emberwake Caldera's hubs, people, quests and places. Data for scripts/ember_design.py (shaped coordinates, zone 45).

Owner request 2026-11-08: "for pilot. reshape emberwake caldera. and remake the zone and quests to fit the new shape. no fillers." Owner answers: seamless against the
Stormglass Flats (north) and the Moonspore Canopy (west), keep the three elites (Chainmaw, Yrsa, the Uncrowned Ember), three outposts. The Obsidian Orrery and the
Ribbonwild stay rim gates; the Nine-Chain Door and its camp move whole.

Every old `ew_*`, `raid_key` and `es_25`..`es_27` id stays (saved progress, the raid, tests, quest_gear_rewards): texts are rewritten only where the geography changed
(the road no longer starts from Asterion, the caldera is a real crater with a lava lake). Fourteen quests are new. New ids and people start `ew_` and stay within 19
characters (the accept string is capped at 32). Levels 95-99, rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(95, 100)}      # past the table each level adds 2300
GOLD = {95: 22000, 96: 22000, 97: 22000, 98: 26000, 99: 35000}

# the hubs: plaza and half width/height of the sanctuary rectangle. `city` is Chainrest (Svala's camp, the spawn); the Door camp is a camp built round the moved
# Nine-Chain Door block. Nothing art-less may stand within 20 tiles of the Flats or Canopy seam.
HAMLETS = {
    'chainrest':    dict(name='Chainrest', x=228, y=84, hw=12, hh=11, city=True),
    'door':         dict(name='Nine-Chain Hold', x=316, y=90, hw=18, hh=18, block=True),
    'craterwatch':  dict(name='Craterwatch', x=100, y=128, hw=12, hh=11),
    'cinderquay':   dict(name='Cinderquay', x=186, y=312, hw=12, hh=11),
    'glasshold':    dict(name='Glasshold', x=292, y=226, hw=12, hh=11),
}
D_DOOR = (189, 56)          # old door (133,20) -> (322,76): the road's end in the north-east, the Nine-Chain Door block moves whole

# kind, x, y (Chainmaw and Yrsa have quests, the Uncrowned Ember none; awareness is the 4th value of the server's attack profile, 8.5, kept generous)
ELITES = [('ew_chainmaw', 136, 206), ('ew_bellows', 163, 111), ('ew_crown', 253, 277)]
AWARENESS = {'ew_chainmaw': 12., 'ew_bellows': 12., 'ew_crown': 12.}

LODGE = dict(r=0, width=4.5, depth=3.5)

DRESSING = {
    'chainrest': [
        ('ew_hut', 0, -6.5, dict(LODGE)),
        ('tent', -9, 5, dict(r=1.5, width=3, depth=2.4, color='#6b5f66', label='Chain Watch')),
        ('stall', 7, 4, dict(r=0, width=1.8, depth=1.2, color='#9b6a4c', label='Linkwright')),
        ('noticeboard', -5, -7, dict(r=.4, width=1.3, depth=.4, label='Chainrest')),
        ('ew_lantern', -8, -1, dict(r=.3)), ('ew_lantern', 9, -1, dict(r=.3)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
        ('brazier', -3, -2, dict(r=.4)), ('ew_warmstone', -1, 7, dict(r=.6)), ('ew_warmstone', 2, 7, dict(r=.6)),
    ],
    'door': [
        ('tent', -13, 8, dict(r=1.5, width=3, depth=2.4, color='#6b5f66', label='Door Watch')),
        ('tent', 13, 9, dict(r=1.5, width=3, depth=2.4, color='#7a5648', label='Muster')),
        ('stall', -13, -3, dict(r=0, width=1.8, depth=1.2, color='#9b6a4c', label='Chainforge')),
        ('brazier', -5, 3, dict(r=.4)), ('brazier', 6, 5, dict(r=.4)),
        ('campfire', 0, 11, dict(r=.65)), ('bench', 8, 11, dict(r=0, width=1.5, depth=.45)),
        ('ew_lantern', -10, -6, dict(r=.3)), ('ew_lantern', 11, -6, dict(r=.3)),
    ],
    'craterwatch': [
        ('ew_hut', 0, -6.5, dict(LODGE)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#69606c', label='Rim Watch')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#a8744f', label='Ashsmith')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Craterwatch')),
        ('ew_lantern', -8, -1, dict(r=.3)), ('ew_lantern', 9, -1, dict(r=.3)),
        ('campfire', 4, 4, dict(r=.65)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)), ('brazier', -3, -2, dict(r=.4)),
    ],
    'cinderquay': [
        ('ew_hut', 0, -6.5, dict(LODGE)),
        ('tent', -9, 5, dict(r=1.5, width=3, depth=2.4, color='#5f6670', label='Quay Watch')),
        ('stall', 7, 4, dict(r=0, width=1.8, depth=1.2, color='#9a7455', label='Kilnwright')),
        ('noticeboard', -5, -7, dict(r=.4, width=1.3, depth=.4, label='Cinderquay')),
        ('ew_lantern', -8, -1, dict(r=.3)), ('ew_lantern', 9, -1, dict(r=.3)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, 0, dict(r=.4)), ('brazier', 6, -2, dict(r=.4)),
    ],
    'glasshold': [
        ('ew_hut', 0, -6.5, dict(LODGE)),
        ('tent', 9, 5, dict(r=1.5, width=3, depth=2.4, color='#6a5d6a', label='Bank Watch')),
        ('stall', -6, 3, dict(r=0, width=1.8, depth=1.2, color='#a06f52', label='Slagwright')),
        ('noticeboard', 5, -7, dict(r=.4, width=1.3, depth=.4, label='Glasshold')),
        ('ew_lantern', -8, -1, dict(r=.3)), ('ew_lantern', 9, -1, dict(r=.3)),
        ('campfire', 4, 4, dict(r=.65)), ('brazier', -3, -1, dict(r=.4)), ('bench', 6, -3, dict(r=0, width=1.5, depth=.45)),
    ],
}

# the old people move with their hub: id -> (hamlet, dx, dy), or the Door block (moved by D_DOOR)
HUB_NPCS = {'ew_guide': ('chainrest', -1, 2), 'ew_keeper': ('chainrest', 4, 0), 'raid_key_keeper': ('chainrest', -4, -3)}
DOOR_NPCS = ('ew_smith', 'ew_stone', 'ew_seal', 'ew_echo')

NPCS = [
    dict(id='ew_cw_ragna', hamlet='craterwatch', dx=-3, dy=-1, name='Rim-Warden Ragna Calderaeye', role='Rim warden', color='#9a8f98',
         look=dict(skin='#c69a7b', hair='#8a8e98', style='long', hat='hood', hatColor='#5a4a50'),
         dialogue='From here you can see the whole caldera breathe. East of the post the mountain\'s great bowl glows, and the Living Bellows stands on its floor. West of us the Cinder Slopes run down to the edge of the world. I keep the rim.'),
    dict(id='ew_cw_sten', hamlet='craterwatch', dx=5, dy=3, name='Sten Ashsmith', role='Ashsmith', color='#a8744f',
         look=dict(skin='#bd8c6f', hair='#3a3238', style='short', hat='none', hatColor='#6a5a5a'),
         dialogue='An ashback\'s relic holds heat longer than any coal. Bring me five and the rim-watch will keep its hands warm through the long dark.'),
    dict(id='ew_cw_trader', hamlet='craterwatch', dx=-6, dy=4.6, name='Mold Brimstead', role='Outpost trader', color='#a89aa0', trader=True,
         look=dict(skin='#e0bca0', hair='#6a4a3a', style='long', hat='none', hatColor='#a89aa0'),
         dialogue='Stew, tonics and dry boots for anyone who stands rim-watch. Everything is sold at cost, because the mountain charges enough.'),
    dict(id='ew_cq_brage', hamlet='cinderquay', dx=-3, dy=-1, name='Quay-Warden Brage Slagwater', role='Quay warden', color='#8a96a8',
         look=dict(skin='#d9b08c', hair='#d8d4cc', style='short', hat='hood', hatColor='#4a5260'),
         dialogue='The black shore lies south of us and the cold sea beyond it. North, the Quenched Basin steams where a crater once boiled and now only sighs. Glasswings wheel over all of it. I keep the lamps lit so the quay can be found.'),
    dict(id='ew_cq_tove', hamlet='cinderquay', dx=5, dy=3, name='Tove Kilnwright', role='Kilnwright', color='#9a7455',
         look=dict(skin='#c99b7a', hair='#5a2a2a', style='long', hat='none', hatColor='#8a8f98'),
         dialogue='A glasswing\'s relic fires clearer than any sand. Bring me five and the quay will have windows again.'),
    dict(id='ew_cq_trader', hamlet='cinderquay', dx=-5, dy=6.2, name='Hedvig Quaymonger', role='Outpost trader', color='#a0a8b0', trader=True,
         look=dict(skin='#edc5a1', hair='#4a4a58', style='long', hat='none', hatColor='#a0a8b0'),
         dialogue='Bread, tonics and stew for the ones who watch the shore. If the soup hisses, that is the sea, not the cook.'),
    dict(id='ew_gh_sunniva', hamlet='glasshold', dx=-3, dy=-1, name='Bank-Warden Sunniva Glassbank', role='Bank warden', color='#9a8aa0',
         look=dict(skin='#edc5a1', hair='#cfc4d0', style='long', hat='hood', hatColor='#564a60'),
         dialogue='The river runs hot along the north of the Slagfold, and the cinderhorns graze its cooled banks as if the ground were not alive. East of the hold the mountain stops and the Ribbonwild begins. I would like that border to stay quiet.'),
    dict(id='ew_gh_ivar', hamlet='glasshold', dx=5, dy=3, name='Ivar Slagwright', role='Slagwright', color='#a06f52',
         look=dict(skin='#c99b7a', hair='#2a2a32', style='short', hat='hood', hatColor='#5a4a46'),
         dialogue='A cinderhorn\'s relic keeps its heat for years. Bring me four and I will set them into the hold\'s walls, and the bank will keep its warmth through the night.'),
    dict(id='ew_gh_trader', hamlet='glasshold', dx=-6, dy=5.6, name='Dagny Foldmonger', role='Outpost trader', color='#a89aa8', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='short', hat='none', hatColor='#a89aa8'),
         dialogue='Thread, wicks and stew. If a ram lowers its horns at you, do not argue with it: buy a tonic from me.'),
]

# places a quest walks to (r 6) and the hold circles (r 2.1, two waves of sleepers each)
PLACES = [
    dict(id='ew_slopes', name='The Cinder Slopes', x=78, y=152, r=6),
    dict(id='ew_links', name='The Broken Links', x=122, y=194, r=6),
    dict(id='ew_shore', name='The Black Shore', x=152, y=346, r=6),
    dict(id='ew_quench', name='The Quenched Basin', x=140, y=278, r=6),
    dict(id='ew_fold', name='The Slagfold', x=292, y=262, r=6),
    dict(id='ew_crater', name='The Ember Crater', x=253, y=246, r=6),
    dict(id='ew_warm_m', name='The Chain Lamps', x=254, y=104, r=2.1, waves=[dict(at=1, tag='ew_warm_m#a'), dict(at=11, tag='ew_warm_m#b')]),
    dict(id='ew_rim_m', name='The Rim Circle', x=114, y=152, r=2.1, waves=[dict(at=1, tag='ew_rim_m#a'), dict(at=11, tag='ew_rim_m#b')]),
    dict(id='ew_quay_m', name='The Quay Circle', x=216, y=320, r=2.1, waves=[dict(at=1, tag='ew_quay_m#a'), dict(at=11, tag='ew_quay_m#b')]),
    dict(id='ew_glass_m', name='The Glass Circle', x=276, y=216, r=2.1, waves=[dict(at=1, tag='ew_glass_m#a'), dict(at=11, tag='ew_glass_m#b')]),
]

# Sleepers woken by a hold wave: two and two a wave, round the circle
AMBUSH = [
    ('ew_ashback', 248, 98, 'ew_warm_m#a'), ('ew_ashback', 260, 110, 'ew_warm_m#a'), ('ew_glasswing', 248, 110, 'ew_warm_m#b'), ('ew_glasswing', 260, 98, 'ew_warm_m#b'),
    ('ew_glasswing', 108, 146, 'ew_rim_m#a'), ('ew_glasswing', 120, 158, 'ew_rim_m#a'), ('ew_slagjaw', 108, 158, 'ew_rim_m#b'), ('ew_slagjaw', 120, 146, 'ew_rim_m#b'),
    ('ew_glasswing', 210, 314, 'ew_quay_m#a'), ('ew_glasswing', 222, 326, 'ew_quay_m#a'), ('ew_slagjaw', 210, 326, 'ew_quay_m#b'), ('ew_slagjaw', 222, 314, 'ew_quay_m#b'),
    ('ew_cinderhorn', 270, 210, 'ew_glass_m#a'), ('ew_cinderhorn', 282, 222, 'ew_glass_m#a'), ('ew_cinderhorn', 270, 222, 'ew_glass_m#b'), ('ew_cinderhorn', 282, 210, 'ew_glass_m#b'),
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
    # Chainrest, in the north
    Q('ew_h_hold', 'Relight the Chain Lamps', 'ew_guide', 96,
      'The chain lamps east of Chainrest gutter whenever the ashbacks gather, and then the dark comes down on the road. Stand in the circle there for twenty seconds while Svala relights them, and let nothing reach her.',
      [('hold', 'ew_warm_m', 'Relight the Chain Lamps', 20)], requires='ew_warm'),
    Q('ew_h_rounds', 'The Watchers of the Caldera', 'ew_keeper', 98,
      'Three outposts watch the mountain beyond Chainrest: Craterwatch on the western rim, Cinderquay on the black shore in the south and Glasshold on the river\'s southern bank. Hedda wants their keepers told that the Chain Road holds. Speak with Ragna, Brage and Sunniva, and use the Travel Masters if the road is long.',
      [('talk', 'ew_cw_ragna', 'Speak with Rim-Warden Ragna Calderaeye at Craterwatch', 1), ('talk', 'ew_cq_brage', 'Speak with Quay-Warden Brage Slagwater at Cinderquay', 1),
       ('talk', 'ew_gh_sunniva', 'Speak with Bank-Warden Sunniva Glassbank at Glasshold', 1)], requires='ew_road'),
    # Craterwatch, on the western rim
    Q('ew_cw_walk', 'Along the Cinder Slopes', 'ew_cw_ragna', 96,
      'The Cinder Slopes run down west of Craterwatch to the edge of the world, and the ashbacks have buried the rim stakes there. Ragna wants a count of what lives on them. Walk out to the Cinder Slopes and defeat four Ashback Salamanders on the way.',
      [('visit', 'ew_slopes', 'Reach the Cinder Slopes', 1), ('kill', 'ew_ashback', 'Defeat Ashback Salamanders on the way', 4)], requires='ew_road'),
    Q('ew_cw_scales', 'Relics for the Ashsmith', 'ew_cw_sten', 96,
      'Sten banks the rim-watch\'s fires with ashback relics, which hold heat longer than coal. Bring him five Ashback Salamander Relics.',
      [('bring', 'ew_ashback_relic', 'Bring Ashback Salamander Relics', 5)], requires='ew_cw_walk'),
    Q('ew_cw_hold', 'Hold the Rim Circle', 'ew_cw_ragna', 97,
      'The tallest stake on the rim throws sparks whenever the mountain stirs, and then every wing and jaw on the slopes comes to answer it. Stand in the circle beside it for twenty seconds while Ragna grounds it, and keep them off her.',
      [('hold', 'ew_rim_m', 'Hold the Rim Circle', 20)], requires='ew_cw_walk'),
    Q('ew_cw_links', 'Down to the Broken Links', 'ew_cw_ragna', 98,
      'South of the rim the chain road breaks into links the size of houses, and the Slagjaw Burrowers have tunnelled under all of them. Walk down to the Broken Links and defeat five Slagjaw Burrowers there, then tell Ragna how many still dig.',
      [('visit', 'ew_links', 'Reach the Broken Links', 1), ('kill', 'ew_slagjaw', 'Defeat Slagjaw Burrowers at the Broken Links', 5)], requires='ew_cw_hold'),
    # Cinderquay, on the black shore
    Q('ew_cq_walk', 'Out to the Black Shore', 'ew_cq_brage', 97,
      'South of Cinderquay the black sand runs down to the cold sea, and the glasswings roost on the wrecked quays there. Brage wants to know how many. Walk out to the Black Shore and defeat four Obsidian Glasswings on the way.',
      [('visit', 'ew_shore', 'Reach the Black Shore', 1), ('kill', 'ew_glasswing', 'Defeat Obsidian Glasswings on the way', 4)], requires='ew_road'),
    Q('ew_cq_wings', 'Relics for the Kilnwright', 'ew_cq_tove', 97,
      'Tove fires her glass with glasswing relics, which melt clearer than any sand. Bring her five Obsidian Glasswing Relics.',
      [('bring', 'ew_glasswing_relic', 'Bring Obsidian Glasswing Relics', 5)], requires='ew_cq_walk'),
    Q('ew_cq_hold', 'Hold the Quay Circle', 'ew_cq_brage', 98,
      'The quay lamp east of Cinderquay flares whenever the glasswings gather, and then the whole shore comes to answer it. Stand in the circle beside it for twenty seconds while Brage steadies it, and keep the flock off him.',
      [('hold', 'ew_quay_m', 'Hold the Quay Circle', 20)], requires='ew_cq_walk'),
    Q('ew_cq_quench', 'The Quenched Basin', 'ew_cq_brage', 98,
      'North of the quay a crater once boiled and now only sighs, and the Slagjaw Burrowers have made it their warren. Walk up to the Quenched Basin and defeat five Slagjaw Burrowers there.',
      [('visit', 'ew_quench', 'Reach the Quenched Basin', 1), ('kill', 'ew_slagjaw', 'Defeat Slagjaw Burrowers in the Basin', 5)], requires='ew_cq_hold'),
    # Glasshold, on the river's southern bank
    Q('ew_gh_walk', 'Across the Slagfold', 'ew_gh_sunniva', 98,
      'South of Glasshold the cooled slag lies in folds, and the Cinderhorn Rams graze it as if it were grass. Sunniva wants a count. Walk out to the Slagfold and defeat four Cinderhorn Rams on the way.',
      [('visit', 'ew_fold', 'Reach the Slagfold', 1), ('kill', 'ew_cinderhorn', 'Defeat Cinderhorn Rams on the way', 4)], requires='ew_road'),
    Q('ew_gh_horns', 'Relics for the Slagwright', 'ew_gh_ivar', 98,
      'Ivar sets cinderhorn relics into the hold\'s walls, so the bank keeps its warmth through the night. Bring him four Cinderhorn Ram Relics.',
      [('bring', 'ew_cinderhorn_relic', 'Bring Cinderhorn Ram Relics', 4)], requires='ew_gh_walk'),
    Q('ew_gh_hold', 'Hold the Glass Circle', 'ew_gh_sunniva', 99,
      'The glass post north of Glasshold flares whenever the rams stampede, and then every horn on the bank comes to answer it. Stand in the circle at the post for twenty seconds while Sunniva steadies it, and keep the herd off her.',
      [('hold', 'ew_glass_m', 'Hold the Glass Circle', 20)], requires='ew_gh_walk'),
    Q('ew_gh_crater', 'To the Ember Crater', 'ew_gh_sunniva', 99,
      'South-west of the hold the Ember Crater glows at night, and the Cinderhorn Rams crowd its rim. Walk up to the Ember Crater and defeat five Cinderhorn Rams there. Do not go down into it alone.',
      [('visit', 'ew_crater', 'Reach the Ember Crater', 1), ('kill', 'ew_cinderhorn', 'Defeat Cinderhorn Rams at the Crater', 5)], requires='ew_gh_hold'),
]

# Old ids, new meaning (only where the geography changed)
REWRITES = {
    'ew_warm': dict(description='Svala keeps the lamps of the old chain road. Speak to Hedda Linkkeeper in Chainrest.'),
    'ew_road': dict(description='Drive the ashbacks and glasswings from the Chain Road between Chainrest and the river. The mountain is waking.'),
    'ew_link': dict(description='Gather companions and defeat Chainmaw at the First Shackle among the Broken Links, north of the river.'),
    'ew_breath': dict(description='Gather companions and silence Yrsa, the Living Bellows, on the floor of the caldera.'),
    'ew_voice': dict(description='Follow the Chain Road across the basalt causeway to the Nine-Chain Door. Hear the voice below and bring its words to Svala.'),
}

# People whose words described the old arrival camp or the old map: changed text only
NPC_UPDATES = {
    'ew_guide': dict(role='Chain Road pathfinder', dialogue='The flagstones in Asterion are warm because the first forge never went out. Follow the Chain Road south and east, across the basalt causeway, to the sealed door. Leave the glowing river to the stones.'),
    'ew_keeper': dict(dialogue='Chainmaw carries a broken link from the first chain. Bring companions and end its watch among the Broken Links.'),
    'ew_smith': dict(dialogue='Yrsa feeds air into the mountain from the floor of the caldera. Silence the living bellows before the last chain cracks.'),
}
TAGLINE = 'Nine chains hold a fire that remembers, under a caldera that breathes'


def dress(d, hamlets, d_door=D_DOOR):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(world, zone, hamlets):
    flats = world['zones'][18]
    hub = next(n for n in flats['npcs'] if n['id'] == 'travel_breakwater')
    box = next(n for n in flats['npcs'] if n['id'] == 'mailbox_19_breakwater_camp')
    wheel = world['zones'][27]
    healer = next(n for n in wheel['npcs'] if n['id'] == 'yr_sp_heal')['offers']
    supplier = next(n for n in wheel['npcs'] if n['id'] == 'yr_sp_trade')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'stew']) if trader else [], buys=trader, look=s['look'])
        out.append(n)
    keys = list(hamlets)
    spots = {'chainrest': (-1, 5), 'door': (-9, 8), 'craterwatch': (-1, 2), 'cinderquay': (-1, 3.5), 'glasshold': (-1, 3.5)}
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(hub)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=[f'travel_{k}' for k in keys if k != key])
        out.append(t)
    boxes = {'chainrest': (7, 6), 'door': (-4, 12), 'craterwatch': (3, 1), 'cinderquay': (2, 1), 'glasshold': (-2, 3)}
    for key, (dx, dy) in boxes.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_45_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square. Rewrite every Emberwake entry in the shaped frame."""
    directory = [d for d in json.loads(path.read_text()) if d['zone'] != 45]
    for key, h in hamlets.items():
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_45_{key}')
        m = next(n for n in zone['npcs'] if n['id'] == f'travel_{key}')
        directory.append(dict(id=box['id'], zone=45, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=m['x'], y=m['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def city_and_camps(hamlets):
    def rect(h):
        return dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                    plaza=dict(x=h['x'], y=h['y']), radius=6 if h.get('city') else 3.5, entry=dict(x=h['x'], y=h['y'] + h['hh'] - 3))
    city = rect(next(h for h in hamlets.values() if h.get('city')))
    return city, [rect(h) for h in hamlets.values() if not h.get('city')]


def install(world, zone, hamlets):
    """Idempotent, so `plan` also works on a map that already carries the design."""
    new_npcs = people(world, zone, hamlets)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        n.update(copy.deepcopy(NPC_UPDATES.get(n['id'], {})))
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
