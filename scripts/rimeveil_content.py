"""Rimeveil Glacier's outposts, people and quests. Data for scripts/rimeveil_design.py (shaped coordinates).

Every old `rime_*` / `es_*` quest id stays (saved progress, tests, quest_gear_rewards): their text, giver and targets are rewritten so the chain
walks the glacier instead of sitting in Rimeward Camp. New ids and people start with `rime_` (a Rust test asks for it). Every quest is level 10-15,
rewardXp = levels.txt[level-1] / 10. Rule for elites (owner): three per zone, two with a quest, one without: `hoarhorn` and `whitewail` with,
`shardback` without. Every text here needs its Swedish in scripts/sv-*.txt, written by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: LEVELS[lv - 1] // 10 for lv in range(10, 16)}
GOLD = {10: 200, 11: 250, 12: 300, 13: 380, 14: 450, 15: 550}

ELITES = [('hoarhorn', 46, 102), ('whitewail', 268, 128), ('shardback', 214, 262)]

HUT = dict(r=0, width=3.4, depth=3.2)

# (kind, dx, dy, extra) around each outpost's plaza
DRESSING = {
    'driftwatch': [
        ('house', -9, -6, dict(HUT, label='Border Hall', color='#5f7f9f')), ('house', 9, -8, dict(HUT, label='Sledge Shed', color='#6b6f7f')),
        ('tent', -10, 5, dict(r=1.5, width=3, depth=2.4, color='#7a9ab8', label='Bunks')),
        ('stall', -5, 3, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Pelts & Provisions')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Driftwatch')),
        ('campfire', 4, 3, dict(r=.65)), ('bench', 6, 6, dict(r=0, width=1.5, depth=.45)),
        ('barrels', -3, 6, dict(r=0, width=.6, depth=.6, color='', label='')), ('barrels', -2, 7, dict(r=0, width=.6, depth=.6, color='', label='')),
        ('lamp', -4, -3, dict(r=.18)), ('lamp', 6, -2, dict(r=.18)),
    ],
    'shearwind': [
        ('house', -9, -6, dict(HUT, label='Cliff Lodge', color='#6f7f94')), ('house', 9, -4, dict(HUT, label='Smokehouse', color='#7a6a5a')),
        ('tent', 10, 6, dict(r=1.5, width=3, depth=2.4, color='#8aa0b8', label='Hunters')),
        ('stall', -6, 4, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Furs & Salt')),
        ('noticeboard', -2, -6, dict(r=.4, width=1.3, depth=.4, label='Shearwind Post')),
        ('campfire', 3, 3, dict(r=.65)), ('brazier', -2, 0, dict(r=.4)),
        ('lamp', -4, 0, dict(r=.18)), ('lamp', 5, 1, dict(r=.18)),
        ('barrels', -10, 4, dict(r=0, width=.6, depth=.6, color='', label='')),
    ],
    'peakrest': [
        ('house', 9, -6, dict(HUT, label='Peak Lodge', color='#5a6f9a')), ('house', 10, 6, dict(HUT, label='Survey House', color='#7a7a8a')),
        ('tent', -10, 7, dict(r=1.5, width=3, depth=2.4, color='#6f7fb0', label='Climbers')),
        ('stall', -6, 5, dict(r=0, width=1.8, depth=1.2, color='#a87a45', label='Rope & Rations')),
        ('noticeboard', 2, -6, dict(r=.4, width=1.3, depth=.4, label='Peakrest')),
        ('brazier', -2, -1, dict(r=.4)), ('brazier', 2, 3, dict(r=.4)), ('lamp', -5, 2, dict(r=.18)), ('lamp', 5, 1, dict(r=.18)),
    ],
}

NPCS = [
    dict(id='rime_dw_hild', hamlet='driftwatch', dx=-3, dy=-1, name='Hild Fenwatch', role='Border warden', color='#6f93b8',
         look=dict(skin='#c99b7a', hair='#3a4a5a', style='long', hat='hood', hatColor='#4f6f8f'),
         dialogue='The fen starts where my boots stop sinking in snow. I watch the line so that nothing from the mist walks onto the ice, and nothing from the ice walks into the mist.'),
    dict(id='rime_dw_nils', hamlet='driftwatch', dx=5, dy=3, name='Nils Sledgeman', role='Sledge-driver', color='#8a7a5a',
         look=dict(skin='#d9b08c', hair='#7a6a4a', style='short', hat='hood', hatColor='#6a5a4a'),
         dialogue='Eight dogs, one sledge, and a road that moves in the night. I have lost the road twice and the dogs never.'),
    dict(id='rime_dw_trader', hamlet='driftwatch', dx=-5, dy=4.6, name='Margit Snowcask', role='Outpost trader', color='#a87a45', trader=True,
         look=dict(skin='#edc5a1', hair='#b89a6a', style='long', hat='none', hatColor='#a87a45'),
         dialogue='Tonics, stew and a fair count. Everything here has crossed the whole glacier to reach my shelf, so please do not haggle about the price of the cold.'),
    dict(id='rime_sw_runa', hamlet='shearwind', dx=-3, dy=2, name='Runa Windlass', role='Cliff warden', color='#7a93b0',
         look=dict(skin='#c99b7a', hair='#d8d8d8', style='long', hat='hood', hatColor='#5a7a9a'),
         dialogue='West of us there is only the drop and the sea. Everything dangerous comes from the other side, so I watch the other side.'),
    dict(id='rime_sw_arne', hamlet='shearwind', dx=1, dy=-3, name='Arne Longtooth', role='Hunter', color='#8a7a6a',
         look=dict(skin='#b98a6a', hair='#3a3028', style='short', hat='none', hatColor='#6a5a4a'),
         dialogue='I have hunted these fells for thirty winters. Something with tusks like icicles has been hunting me back for three.'),
    dict(id='rime_sw_trader', hamlet='shearwind', dx=-6, dy=5.6, name='Frida Furlined', role='Outpost trader', color='#9a7a5a', trader=True,
         look=dict(skin='#edc5a1', hair='#8a4a2a', style='long', hat='none', hatColor='#9a7a5a'),
         dialogue='Furs, salt fish and tonics. If you are walking east, buy a second scarf. If you are walking west, buy a rope.'),
    dict(id='rime_pk_gunnar', hamlet='peakrest', dx=-4, dy=1, name='Gunnar Highbrow', role='Peak warden', color='#6a7fb0',
         look=dict(skin='#d9b08c', hair='#aaaaaa', style='short', hat='hood', hatColor='#4a5f8f'),
         dialogue='The peaks here are older than the roads, and they are patient. A thing in white has taken to walking between them. It sings, and the singing is the worst of it.'),
    dict(id='rime_pk_sif', hamlet='peakrest', dx=4, dy=2, name='Sif Whitehand', role='Cartographer', color='#8a8ab0',
         look=dict(skin='#edc5a1', hair='#2a2a3a', style='long', hat='hood', hatColor='#6a6a9a'),
         dialogue='Nobody has drawn the middle of the glacier yet, only the edges. I would like to stand in the Heart with my instruments, and I would like someone to stand beside me while I do.',
         escort=dict(quest='rime_pk_chart', **{'class': 'mage'}, female=True, hairColor=3, skin=0, level=14, speed=2.5,
                     route=[[278, 100], [262, 99], [250, 103], [236, 112], [222, 124], [208, 134], [190, 142], [167, 149]],
                     ambush=[dict(at=[232, 116], r=11, tag='rime_pk_sif#road')])),
    dict(id='rime_pk_trader', hamlet='peakrest', dx=-6, dy=6.6, name='Eydis Rimecask', role='Outpost trader', color='#6a7fb0', trader=True,
         look=dict(skin='#c99b7a', hair='#5a3a4a', style='long', hat='none', hatColor='#6a7fb0'),
         dialogue='Rope, pitons, hot stew. Everything a climber needs, except sense.'),
]

PLACES = [
    dict(id='rime_gap', name='The Fenward Gap', x=188, y=262, r=7),
    dict(id='rime_sledge_m', name='The Stranded Sledge', x=96, y=259, r=2.1, waves=[dict(at=1, tag='rime_sledge_m#a'), dict(at=11, tag='rime_sledge_m#b')]),
    dict(id='rime_whalecairn', name='The Whale Cairn', x=14, y=206, r=7),
    dict(id='rime_signal_m', name='The Shearwind Fire', x=30, y=128, r=2.1, waves=[dict(at=1, tag='rime_signal_m#a'), dict(at=11, tag='rime_signal_m#b')]),
    dict(id='rime_hornspire', name='The Hornspire Ridge', x=254, y=102, r=7),
    dict(id='rime_heart', name='The Heart of the Glacier', x=167, y=149, r=8),
    dict(id='rime_ford_outer', name='The Outer Ford', x=168, y=229, r=6),
    dict(id='rime_ford_mid', name='The Middle Ford', x=168, y=203, r=6),
    dict(id='rime_ford_inner', name='The Inner Ford', x=168, y=180, r=6),
]

# Sleepers woken by a wave or an escort ambush
AMBUSH = [('crab', 90, 255, 'rime_sledge_m#a'), ('crab', 102, 265, 'rime_sledge_m#a'), ('wolf', 90, 265, 'rime_sledge_m#b'), ('wolf', 102, 255, 'rime_sledge_m#b'),
          ('wolf', 24, 123, 'rime_signal_m#a'), ('wolf', 36, 133, 'rime_signal_m#a'), ('yeti', 24, 133, 'rime_signal_m#b'), ('yeti', 36, 123, 'rime_signal_m#b'),
          ('yeti', 228, 112, 'rime_pk_sif#road'), ('wolf', 236, 122, 'rime_pk_sif#road')]


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
    # Driftwatch, where the ice meets the fen
    Q('rime_dw_pelts', 'Pelts for the Watch', 'rime_dw_hild', 11,
      'The border watch sleeps on wolf pelt and nothing else keeps the fen damp out. Bring Hild four frost pelts.',
      [('bring', 'frost_pelt', 'Bring frost pelts', 4)]),
    Q('rime_dw_gap', 'The Fenward Gap', 'rime_dw_hild', 11,
      'Mist crawls up onto the ice through a gap in the drifts east of the post. Go and stand in it, and clear four crabs that nest there.',
      [('visit', 'rime_gap', 'Stand in the Fenward Gap', 1), ('kill', 'crab', 'Defeat crabs in the drifts', 4)], requires='rime_dw_pelts'),
    Q('rime_dw_sledge', 'The Stranded Sledge', 'rime_dw_nils', 12,
      "Nils's second sledge went through the ice and lies half out of it. Stand beside it for twenty seconds while he works the runners free, and keep whatever comes out of the snow off him.",
      [('hold', 'rime_sledge_m', 'Guard the stranded sledge', 20)], requires='rime_dw_gap'),
    Q('rime_dw_shells', 'Shell Plating', 'rime_dw_nils', 12,
      'Rime shell is the one thing that will not crack under a loaded runner. Nils needs six shells for the new sledge.',
      [('bring', 'rime_shell', 'Bring rime shells', 6)], requires='rime_dw_pelts'),
    # Shearwind Post, on the western cliffs
    Q('rime_sw_wolves', 'Wolves on the Cliff Road', 'rime_sw_runa', 12,
      'Frostfang wolves have started using the cliff road as their own. Defeat six before they get used to it.',
      [('kill', 'wolf', 'Defeat wolves on the Strand', 6)]),
    Q('rime_sw_horns', 'Horn for the Hunters', 'rime_sw_arne', 13,
      'Yeti horn makes the best arrowheads in the world, and the worst smell. Bring Arne three.',
      [('bring', 'yeti_horn', 'Bring yeti horns', 3)], requires='rime_sw_wolves'),
    Q('rime_sw_cairn', 'The Whale Cairn', 'rime_sw_runa', 13,
      'On the cliff south of the post the old hunters piled a cairn of whalebone, and nobody has checked it in years. Go and look, and defeat three yetis on the way.',
      [('visit', 'rime_whalecairn', 'Reach the Whale Cairn', 1), ('kill', 'yeti', 'Defeat yetis on the fells', 3)], requires='rime_sw_wolves'),
    Q('rime_sw_signal', 'The Shearwind Fire', 'rime_sw_runa', 14,
      'The signal fire on the north fells has been dark since the autumn. Stand at it for twenty seconds while it catches, and let nothing put it out.',
      [('hold', 'rime_signal_m', 'Hold the signal fire', 20)], requires='rime_sw_cairn'),
    Q('rime_sw_hoarhorn', 'Hoarhorn', 'rime_sw_arne', 15,
      'A mammoth the size of a barn, with tusks grown into a tangle of icicles, has been on the fells since the first frost. It has taken three hunters and a sledge. Arne wants it dead, and he says nobody should try this alone.',
      [('kill', 'hoarhorn', 'Defeat Hoarhorn', 1)], requires='rime_sw_signal', recommendedPlayers=3),
    # Peakrest, among the north-eastern peaks
    Q('rime_pk_scales', 'Scale and Rope', 'rime_pk_gunnar', 14,
      'A wyrm scale is the only thing that will hold a rope against the cold at the top. Gunnar needs three.',
      [('bring', 'wyrm_scale', 'Bring wyrm scales', 3)]),
    Q('rime_pk_ridge', 'The Hornspire Ridge', 'rime_pk_gunnar', 14,
      'Something white keeps walking the ridge east of the lodge. Climb to the Hornspire and defeat four yetis so the way up is open, then see what you can see.',
      [('visit', 'rime_hornspire', 'Climb the Hornspire Ridge', 1), ('kill', 'yeti', 'Defeat yetis on the ridge', 4)]),
    Q('rime_pk_chart', 'Charting the Heart', 'rime_pk_sif', 14,
      'Sif wants to put the middle of the glacier on paper. Speak to her at the lodge and walk with her down through the rings to the Heart. If she falls, or you do, start again.',
      [('escort', 'rime_pk_sif', 'Walk Sif to the Heart of the Glacier', 1)], requires='rime_pk_scales'),
    Q('rime_pk_whitewail', 'Whitewail', 'rime_pk_gunnar', 15,
      'The white thing on the ridge is no animal. It was a climber once, and it has been screaming since the avalanche. Gunnar wants it silenced, and he says nobody should try this alone.',
      [('kill', 'whitewail', 'Defeat Whitewail', 1)], requires='rime_pk_ridge', recommendedPlayers=3),
    # Rimeward Camp: the middle of the glacier
    Q('rime_spiral', 'The Spiral Road', 'rime_loremaster', 13,
      'The old road crosses each ring of blue ice on a ford. Ylva wants the three southern fords walked in order, outer, middle and inner, to see which of them still holds.',
      [('visit', 'rime_ford_outer', 'Cross the Outer Ford', 1), ('visit', 'rime_ford_mid', 'Cross the Middle Ford', 1), ('visit', 'rime_ford_inner', 'Cross the Inner Ford', 1)],
      requires='rime_wolves'),
    Q('rime_ice_salve', 'Salve from Shell', 'rime_healer', 12,
      'Crushed rime shell makes the one salve that works on frostbite. Brother Eirik is out of it and the shelf crabs are not. Bring five shells.',
      [('bring', 'rime_shell', 'Bring rime shells', 5)], requires='rime_crabs'),
    Q('rime_three_runs', 'Three Sledge Runs', 'rime_trader', 12,
      'Skadi has crates for all three outposts. Carry them to Hild at Driftwatch, Runa at Shearwind and Gunnar at Peakrest. Each outpost has a Travel Master: speak to them and you can fly back.',
      [('talk', 'rime_dw_hild', 'Deliver to Hild at Driftwatch', 1), ('talk', 'rime_sw_runa', 'Deliver to Runa at Shearwind', 1), ('talk', 'rime_pk_gunnar', 'Deliver to Gunnar at Peakrest', 1)],
      requires='rime_welcome'),
    Q('rime_heart', 'The Heart of the Glacier', 'rime_loremaster', 15,
      'Whatever coils in the summit breathes out of the very middle of the rings. Go to the Heart of the Glacier, stand where the ice is oldest and tell Ylva what you find.',
      [('visit', 'rime_heart', 'Reach the Heart of the Glacier', 1)], requires='rime_wyrm'),
]

# Old ids, new meaning: (fields to replace)
REWRITES = {
    'rime_welcome': dict(description='Meet Huntress Brynja, Brother Eirik, Trader Skadi and Loremaster Ylva in Rimeward Camp, then report to Warden Halvard. The glacier is bigger than it looks: four rings of blue ice, three outposts and a heart nobody has charted.'),
    'rime_crabs': dict(description='Rime crabs crowd the shelf south of Rimeward Camp. Defeat five of them and return to Brynja.'),
    'rime_crab_sweep': dict(npc='rime_dw_hild', title='Crack the Southern Drifts', description='The crabs breed under the drifts all the way to the fen border. Defeat ten of them so the sledge road to Driftwatch stays open.'),
    'rime_wolves': dict(description='Frostfang wolves hunt in packs on the Rimewalk, the outermost ring of the glacier. Defeat four and report to Brynja.'),
    'rime_wolf_pack': dict(npc='rime_sw_runa', description='The packs on the western strand are the biggest on the glacier. Defeat eight Frostfang Wolves so the Shearwind scouts can cross it alive.'),
    'rime_thaw': dict(description='Lost climbers lie frozen in the Bluewater Walk and along the shelf. Clear six Rime Crabs and four Frostfang Wolves from around them.'),
    'rime_yetis': dict(description='Glacier yetis roam the Bluewater Walk, between the second and third ring. Defeat three and bring Ylva their count.'),
    'rime_yeti_herd': dict(npc='rime_pk_gunnar', description='The yetis have torn up the cairns along the Hornspire Ridge. Defeat six Glacier Yetis so Gunnar can rebuild them.'),
    'rime_wyrm': dict(description='Cross the inner rings into the Whorl and defeat two Rime Wyrms. Ylva needs to know whether the cold stops.'),
    'rime_wyrm_hunt': dict(description='Halvard wants the Whorl cleared for good. Defeat four Rime Wyrms and report back.'),
    'rime_vanguard': dict(description='Prove you can hold the whole glacier: defeat two of every monster, from the shelf to the Heart, and report to Halvard.'),
    'rime_bounty': dict(description='Defeat ten enemies of any kind anywhere on Rimeveil Glacier and return to Skadi. This patrol can be repeated.'),
    'rime_supply_route': dict(title='Keep the Sledge Road Open', description='The road to the outposts crosses crab country and wolf country. Clear three Rime Crabs and three Frostfang Wolves for the next sledge. Skadi offers this contract again after each turn-in.'),
    'rime_onward': dict(description='The Crags have little left to teach you. A walk east of Cinderwatch leads up onto the Rimeveil Glacier: climb it, find Rimeward Camp and report to Warden Halvard.'),
}

NPC_UPDATES = {
    'rime_warden': 'Welcome to Rimeward Camp. The glacier winds up in four rings of blue ice with a heart in the middle, and three outposts hold the far edges: Driftwatch on the fen border, Shearwind on the western cliffs, Peakrest among the peaks. Crabs on the shelf, wolves on the outer ring, yetis on the next, wyrms in the Whorl. Report back here.',
    'rime_tracker': 'The south shelf is crab country and the packed-snow road runs straight through it. I need the crabs thinned and the wolf packs on the outer ring broken before the sledges can climb. Do not stand still on the fords; everything wakes there.',
    'rime_loremaster': 'The ice here is older than the Crags and it is not quiet. I chart every footprint I can reach, and every ring has a ford where the old road still holds. Something coils in the Whorl and breathes the cold out through the rings. Help me learn what it is.',
}


def dress(d, hamlets):
    """Buildings first, so the scenery keeps away from them."""
    for key, items in DRESSING.items():
        h = hamlets[key]
        for kind, dx, dy, extra in items:
            e = dict(extra)
            d.add(kind, h['x'] + dx, h['y'] + dy, r=e.pop('r'), **e)


def people(zone, hamlets):
    master = next(n for n in zone['npcs'] if n['id'] == 'travel_rimeward')
    healer = next(n for n in zone['npcs'] if n['id'] == 'rime_healer')['offers']
    supplier = next(n for n in zone['npcs'] if n['id'] == 'rime_trader')['offers']
    out = []
    for spec in NPCS:
        s = dict(spec)
        h = hamlets[s.pop('hamlet')]
        trader = s.pop('trader', False)
        n = dict(id=s['id'], name=s['name'], role=s['role'], x=h['x'] + s['dx'], y=h['y'] + s['dy'], color=s['color'], dialogue=s['dialogue'],
                 offers=copy.deepcopy(healer + [o for o in supplier if o['id'] == 'buy_traveler_stew']) if trader else [], buys=trader, look=s['look'])
        if 'escort' in s:
            n['escort'] = s['escort']
        out.append(n)
    spots = {'driftwatch': (-1, 2), 'shearwind': (-1, 5), 'peakrest': (1, -2)}
    for key, (dx, dy) in spots.items():
        h = hamlets[key]
        t = copy.deepcopy(master)
        t.update(id=f'travel_{key}', x=h['x'] + dx, y=h['y'] + dy, travelStop=h['name'], travelLinks=['travel_rimeward'])
        out.append(t)
        if t['id'] not in master['travelLinks']:
            master['travelLinks'].append(t['id'])
    # every hub has a mailbox (scripts/mailboxes.py ran on the old square, before the outposts exist)
    box = next(n for n in zone['npcs'] if n['id'] == 'mailbox_2_rimeward_camp')
    for key, (dx, dy) in {'driftwatch': (3, 1), 'shearwind': (2, 1), 'peakrest': (-2, 3)}.items():
        h = hamlets[key]
        m = copy.deepcopy(box)
        m.update(id=f'mailbox_2_{key}', x=h['x'] + dx, y=h['y'] + dy)
        out.append(m)
    return out


def record_mailboxes(zone, hamlets, path):
    """The directory is written by mailboxes.py on the old square, where the outposts do not exist yet."""
    directory = [d for d in json.loads(path.read_text()) if not (d['zone'] == 2 and d['hub'] in {h['name'] for h in hamlets.values()})]
    for key, h in hamlets.items():
        box = next(n for n in zone['npcs'] if n['id'] == f'mailbox_2_{key}')
        master = next(n for n in zone['npcs'] if n['id'] == f'travel_{key}')
        directory.append(dict(id=box['id'], zone=2, hub=h['name'], x=box['x'], y=box['y'], anchor=dict(x=master['x'], y=master['y'])))
    path.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + '\n')


def camps(hamlets):
    return [dict(name=h['name'], x0=h['x'] - h['hw'], x1=h['x'] + h['hw'], y0=h['y'] - h['hh'], y1=h['y'] + h['hh'],
                 plaza=dict(x=h['x'], y=h['y']), radius=3.5, entry=dict(x=h['x'], y=h['y'] + 3)) for h in hamlets.values()]


def install(zone, hamlets):
    # idempotent, so `plan` also works on a map that already carries the design
    new_npcs = people(zone, hamlets)
    ids = {n['id'] for n in new_npcs}
    zone['npcs'] = [n for n in zone['npcs'] if n['id'] not in ids] + new_npcs
    for n in zone['npcs']:
        if n['id'] in NPC_UPDATES:
            n['dialogue'] = NPC_UPDATES[n['id']]
    ids = {p['id'] for p in PLACES}
    zone['places'] = [p for p in zone['places'] if p['id'] not in ids] + [dict(p) for p in PLACES]
    ids = {q['id'] for q in QUESTS}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids]
    zone['camps'] = camps(hamlets)
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
