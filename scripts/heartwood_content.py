"""Heartwood's people, places and quests (zone 24, the main city inside the world-tree). Data for scripts/heartwood_design.py.

Owner request 2026-11-09: "remake and reshape heartwood. it should be the main city in the big tree. like a main city like skaldholm. people live in there." and "the buildings in heartwood
should be buildings that could be found inside a big tree": every building is grown or carved wood (burl-pod homes, a carved hall, a forge round a vent of glowing pith, a loom on root posts).

The four old people (the archivist, carver, oracle and custodian), the mailbox, the Seed Vault door and every old quest id stay (saved progress, the Empty Seat's `es_20`). The services are what a
main city has: a bank, a steward (stat reset and the Arena), a smith (repair), a healer, a trader, an inn, a Meeting Stone, a Spark master and a mailbox. New ids and people start `hw_`
(quest ids stay within 19 characters: the accept string is capped at 32). Levels 80-82, rewardXp = levels.txt[level-1] / 10. Every text here needs its Swedish in scripts/sv-*.txt, by hand.
"""
import copy
import json
from pathlib import Path

from quest_gear_rewards import reward_for

ROOT = Path(__file__).resolve().parents[1]
LEVELS = json.loads((ROOT / 'world/levels.txt').read_text())
XP = {lv: (LEVELS[lv - 1] if lv <= len(LEVELS) else LEVELS[-1] + 2300 * (lv - len(LEVELS))) // 10 for lv in range(80, 83)}
GOLD = {80: 8200, 81: 9000, 82: 9800}

NAME = 'Veyrroot Heartwood'
TAGLINE = 'The main city inside the world-tree: burl homes, amber libraries and a forge round the living pith, and the door of the Seed Vault'

# the six districts (the HUD names them) and the Living Pith: (name, place id, plaza x, y)
DISTRICTS = [
    ('Seed Court', 'hw_d_seed', 104, 40),
    ('Amberleaf Hollows', 'hw_d_amber', 146, 70),
    ('Sap Market', 'hw_d_sap', 166, 108),
    ('Loomrow', 'hw_d_loom', 146, 148),
    ('Hollowgate', 'hw_d_gate', 104, 168),
    ('Greenrow', 'hw_d_green', 54, 112),
]

LOOKS = [
    dict(skin='#ad7857', hair='#28574b', style='long', hat='hood', hatColor='#569e66'),
    dict(skin='#c99b7a', hair='#5a3a2a', style='short', hat='none', hatColor='#569e66'),
    dict(skin='#8a6248', hair='#2a2a32', style='short', hat='hood', hatColor='#a8864a'),
    dict(skin='#edc5a1', hair='#7a4a2a', style='long', hat='none', hatColor='#a8864a'),
    dict(skin='#a77250', hair='#3b4156', style='bun', hat='bonnet', hatColor='#8a6a2a'),
    dict(skin='#d9b08c', hair='#1a1a22', style='short', hat='none', hatColor='#569e66'),
]


def person(i, id_, name, role, dialogue, **extra):
    d = dict(id=id_, name=name, role=role, color='#e4f7ae', dialogue=dialogue, offers=[], buys=False, look=copy.deepcopy(LOOKS[i % len(LOOKS)]))
    d.update(extra)
    return d


# (person dict, where): where is a named spot in heartwood_design.SPOTS
PEOPLE = [
    (person(0, 'hw_steward', 'Steward Brannoc Veinwood', 'Steward of Heartwood',
            'Heartwood is the whole city inside the tree: six hollows round the Living Pith, and every burl in it was grown by hand. Ask me about trained attributes, or about the Arena.'), 'steward'),
    (person(1, 'banker_heartwood', 'Keeper Odalys Hollowvault', 'Vault keeper',
            'Gold in your pocket is gold on the road. Leave what you cannot carry in the hollow vault, and it keeps like seed in dry wood. Mind that a quest counts only what you carry, not what is in the bank.',
            art=None), 'banker'),
    (person(2, 'hw_smith', 'Master Smith Torvald Pithfire', 'Pith smith',
            'The forge burns on a vent of the living pith: green at the edge, gold at the heart, and it never smokes the hall. Bring me your worn gear and I will mend it.'), 'smith'),
    (person(3, 'hw_healer', 'Sister Wynn Dewleaf', 'Heartwood healer',
            'Rest here. The tree carries cool water up into every hollow, and the pith is warm through the winter.'), 'healer'),
    (person(4, 'hw_trader', 'Tilda Nutmeg', 'Sap-market trader',
            'Linen satchels, packs, cloaks and green blades: everything travels well in a leaf basket. Sold at the sap-market rate.'), 'trader'),
    (person(5, 'hw_innkeeper', 'Innkeeper Marit Sapwell', 'Innkeeper',
            'The Amber Cup has a bunk in every burl and a bowl on every table. Rest costs five gold, and the stew is free if you tell a good story.'), 'inn'),
    (person(0, 'hw_stone', 'Heartwood Meeting Stone', 'Gather a party · hire fighters',
            'Meet your companions here before the Seed Vault opens.', art='stone'), 'stone'),
    (person(1, 'hw_captain', 'Captain Elva Barkshield', 'Captain of the Watch',
            'The Watch walks the Rim Walk and the three rings every night. Nothing wild has ever come in by the Hollow Arch, and I mean to keep it so.'), 'captain'),
    (person(2, 'hw_watch_a', 'Rune Oakhand', 'Gate watch', 'The Hollow Arch is the only way in from the jungle. Wipe your boots on the root mat.'), 'gate_a'),
    (person(3, 'hw_watch_b', 'Iska Knotwood', 'Gate watch', 'Steady on the stair. The roots are slick after rain.'), 'gate_b'),
    (person(4, 'hw_lamplighter', 'Lamplighter Pim Glowby', 'Lamplighter', 'Three rings, six hundred lamps, one ladder. I light the sap-lamps at dusk and the glow-fruit at midnight.'), 'lamplighter'),
    (person(5, 'hw_weaver', 'Weaver Saga Threadroot', 'Loom weaver', 'The loom stands on four root posts and will not tangle. Moss-lemur fur makes the warmest blankets in the tree.'), 'weaver'),
    (person(0, 'hw_logwarden', 'Old Gorm Ringcount', 'Retired logwarden', 'I counted the rings of every beam in this city. Not one of them is younger than the oldest story.'), 'logwarden'),
    (person(1, 'hw_bellringer', 'Bellringer Tuva Dewdrop', 'Bellringer', 'The Dew Bell hangs in the Seed Court and rings once at dawn. It is the only bell we have, and everybody knows its note.'), 'bellringer'),
    (person(2, 'hw_sorter', 'Seed sorter Nils Kernel', 'Seed sorter', 'Every seed has a place in the Seed Court. These are the ones that will not wait for spring.'), 'sorter'),
    (person(3, 'hw_storyteller', 'Storyteller Edda Hollowsong', 'Storyteller', 'Come to the Living Pith at dusk. The core hums a little louder when a story is true.'), 'storyteller'),
    (person(4, 'hw_baker', 'Baker Olle Barkloaf', 'Bark baker', 'Bark loaf, fungus rolls and amber cakes. Nothing here is baked in a stone oven: ours are grown.'), 'baker'),
    (person(5, 'hw_tapper', 'Sap tapper Freja Ambersap', 'Sap tapper', 'I tap the north wall at first light. A good sap runs gold and sets in the bucket before I reach the stair.'), 'tapper'),
    (person(0, 'hw_gardener', 'Gardener Lars Mossfield', 'Fungus gardener', 'Glow-caps on the shady walls, sweet moss on the sunny ones. Mind the green beds.'), 'gardener'),
    (person(1, 'hw_glassblower', 'Glassblower Ingrid Amberpane', 'Amber glassblower', 'Hornet amber melts into the clearest window you will ever see. Every round pane in the city is mine.'), 'glassblower'),
    (person(2, 'hw_courier', 'Courier Bo Branchwing', 'Courier', 'Letters to Rootfoot, parcels to the Lookout. I take the Hollow Arch twice a day.'), 'courier'),
    (person(3, 'hw_pilgrim', 'Pilgrim Anselm Treewalker', 'Pilgrim', 'I walked here from the Tanglecrown to see the pith glow. It was worth every root.'), 'pilgrim'),
    (person(4, 'hw_kid_pip', 'Pip Acorn', 'Child', 'I can climb the whole Rim Walk without touching the floor!'), 'kid_a'),
    (person(5, 'hw_kid_mina', 'Mina Fernlet', 'Child', 'The Living Pith sings when I put my ear on it. Tove says it does not.'), 'kid_b'),
    (person(0, 'hw_kid_tove', 'Tove Burl', 'Child', 'Pip cheats at hide-and-seek. There are only a thousand hollows to hide in.'), 'kid_c'),
    (person(1, 'hw_kid_ake', 'Åke Twig', 'Child', 'I am going to be a logwarden when I am big. I am already counting.'), 'kid_d'),
]

# old people: id -> spot name
OLD_PEOPLE = {'heart_archivist': 'archivist', 'heart_carver': 'carver', 'heart_oracle': 'oracle', 'heart_custodian': 'custodian', 'mailbox_24_veyrroot_heartwood': 'mailbox'}
SPARK = dict(id='travel_heartwood', spot='spark')

# places a quest walks to (r 5): the six districts, the Living Pith and the Seed Vault door (old ids), the rings and a few landmarks
PLACES = [dict(id=pid, name=name, x=x, y=y, r=6) for name, pid, x, y in DISTRICTS] + [
    dict(id='heart_core', name='The Living Pith', x=104, y=104, r=7),
    dict(id='heart_seed_door', name='The Seed Vault', x=104, y=26, r=5),
    dict(id='hw_rim_walk', name='The Rim Walk', x=104, y=186, r=5),
    dict(id='hw_ring_inner', name='The Inner Ring', x=104, y=72, r=4),
    dict(id='hw_ring_mid', name='The Middle Ring', x=104, y=44 + 100, r=4),
    dict(id='hw_ring_outer', name='The Outer Ring', x=20, y=104, r=4),
    dict(id='hw_founders', name="The Founders' Burl", x=70, y=66, r=4),
    dict(id='hw_bell', name='The Dew Bell', x=118, y=42, r=4),
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
    Q('hw_welcome', 'Inside the Great Tree', 'hw_steward', 80,
      'Heartwood keeps a bank, a forge and an infirmary, and a newcomer should know where they are. Meet the vault keeper, the smith and the healer.',
      [('talk', 'banker_heartwood', 'Meet Keeper Odalys Hollowvault', 1), ('talk', 'hw_smith', 'Meet Master Smith Torvald Pithfire', 1), ('talk', 'hw_healer', 'Meet Sister Wynn Dewleaf', 1)]),
    Q('hw_hollows', 'The Six Hollows', 'hw_steward', 80,
      'The city is six hollows round the Living Pith. Walk through each of them: the Seed Court, Amberleaf Hollows, the Sap Market, Loomrow, Hollowgate and Greenrow.',
      [('visit', 'hw_d_seed', 'Visit the Seed Court', 1), ('visit', 'hw_d_amber', 'Visit Amberleaf Hollows', 1), ('visit', 'hw_d_sap', 'Visit the Sap Market', 1),
       ('visit', 'hw_d_loom', 'Visit Loomrow', 1), ('visit', 'hw_d_gate', 'Visit Hollowgate', 1), ('visit', 'hw_d_green', 'Visit Greenrow', 1)], requires='hw_welcome'),
    Q('hw_resin', 'Resin for the Pith Forge', 'hw_smith', 81,
      'The forge vent runs best on sap-beetle resin, which burns clean and never fouls the pith. Bring Torvald five Sap Beetle Resin from the jungle.',
      [('bring', 'sapbeetle_resin', 'Bring Sap Beetle Resin', 5)], requires='hw_welcome'),
    Q('hw_panes', 'Amber for the Windows', 'heart_archivist', 81,
      'Oli wants every window of the library mended before the dry season, and Ingrid cannot blow a pane without hornet amber. Bring five Lantern Hornet Amber.',
      [('bring', 'hornet_amber', 'Bring Lantern Hornet Amber', 5)], requires='heart_rings'),
    Q('hw_blankets', 'Fur for the Loomrow', 'hw_weaver', 81,
      'Saga is weaving winter blankets for the whole of Greenrow, and she is out of moss-lemur fur. Bring her five Moss Lemur Fur.',
      [('bring', 'mosslemur_fur', 'Bring Moss Lemur Fur', 5)], requires='hw_hollows'),
    Q('hw_stools', 'Chips for the Rootwright', 'heart_carver', 82,
      'Ruva carves the stools for the Amber Cup from bark-mimic chips, which cut like nothing else and never split. Bring five Bark Mimic Chips.',
      [('bring', 'barkmimic_chip', 'Bring Bark Mimic Chips', 5)], requires='hw_hollows'),
    Q('hw_rumours', 'Rumours at the Amber Cup', 'hw_innkeeper', 81,
      'A good innkeeper hears everything. Marit wants the Captain, the healer and the trader to tell her what the city is saying.',
      [('talk', 'hw_captain', 'Speak with Captain Elva Barkshield', 1), ('talk', 'hw_healer', 'Speak with Sister Wynn Dewleaf', 1), ('talk', 'hw_trader', 'Speak with Tilda Nutmeg', 1)], requires='hw_welcome'),
    Q('hw_watch', 'Round the Rim Walk', 'hw_captain', 81,
      'The Watch needs a pair of fresh legs. Walk from Hollowgate along the Rim Walk and report to the gate watch that all is quiet.',
      [('visit', 'hw_rim_walk', 'Walk the Rim Walk', 1), ('talk', 'hw_watch_a', 'Report to Rune Oakhand', 1)], requires='hw_hollows'),
    Q('hw_lamps', 'Light the Rings', 'hw_lamplighter', 80,
      'Three rings, six hundred lamps, and one lamplighter with a sore knee. Walk the Inner, the Middle and the Outer Ring so Pim knows where the dark patches are.',
      [('visit', 'hw_ring_inner', 'Walk the Inner Ring', 1), ('visit', 'hw_ring_mid', 'Walk the Middle Ring', 1), ('visit', 'hw_ring_outer', 'Walk the Outer Ring', 1)], requires='hw_welcome'),
    Q('hw_founders', "The Founders' Burl", 'hw_logwarden', 82,
      "Gorm swears the first burl of Heartwood still stands in Greenrow, with the founders' names cut into its bark. Find it, then ask Oli what the library has to say.",
      [('visit', 'hw_founders', "Find the Founders' Burl", 1), ('talk', 'heart_archivist', 'Speak with Oli Amberleaf', 1)], requires='hw_hollows'),
    Q('hw_bell', 'The Dew Bell', 'hw_bellringer', 82,
      'Tuva rings the Dew Bell at every dawn, and the rope is wearing thin. Look at the bell in the Seed Court and tell the Steward the rope must be changed.',
      [('visit', 'hw_bell', 'Look at the Dew Bell', 1), ('talk', 'hw_steward', 'Speak with Steward Brannoc Veinwood', 1)], requires='hw_hollows'),
    Q('hw_seed_court', 'Seeds for the Court', 'heart_custodian', 82,
      'Mosslet wants the seed sorter told that the Court is ready for the new crop. Walk to Nils in the Seed Court, then go to the Seed Court proper.',
      [('talk', 'hw_sorter', 'Speak with Nils Kernel', 1), ('visit', 'hw_d_seed', 'Visit the Seed Court', 1)], requires='hw_hollows'),
    Q('hw_children', 'Games at the Pith', 'hw_kid_pip', 80,
      'Pip and the others cannot agree who won hide-and-seek. Find Mina, Tove and Åke and settle it.',
      [('talk', 'hw_kid_mina', 'Speak with Mina Fernlet', 1), ('talk', 'hw_kid_tove', 'Speak with Tove Burl', 1), ('talk', 'hw_kid_ake', 'Speak with Åke Twig', 1)], requires='hw_welcome'),
    Q('hw_pith_tales', 'Stories at the Living Pith', 'heart_oracle', 81,
      'Veya says the pith hums louder when a story is true. Visit the Living Pith, then listen to Edda tell one.',
      [('visit', 'heart_core', 'Visit the Living Pith', 1), ('talk', 'hw_storyteller', 'Listen to Edda Hollowsong', 1)], requires='heart_rings'),
]

# Old ids, new meaning
REWRITES = {
    'heart_rings': dict(description='Visit the Living Pith at the heart of the city and speak with the oracle.'),
    'heart_seed_vault': dict(description='Climb to the Seed Court, inspect the Seed Vault door and speak with its custodian.'),
}
NPC_UPDATES = {
    'heart_archivist': dict(dialogue='The tree remembers every season in amber rings, and the library keeps them. The Seed Vault is older than the city.'),
    'heart_carver': dict(dialogue='We coax halls from the wood. We never cut the pith. A new burl takes ten winters to grow, and I have grown forty.'),
    'heart_oracle': dict(dialogue='I hear a second heartbeat behind the Seed Vault door. It answers only to the old crown. Sit at the Living Pith at dusk and you may hear it too.'),
    'heart_custodian': dict(dialogue='The Seed Vault is open. Gather your companions before entering its oldest chambers.'),
}


def install_quests(zone, arena):
    ids = {q['id'] for q in QUESTS}
    zone['quests'] = [q for q in zone['quests'] if q['id'] not in ids and not q['id'].startswith('arena_heart_')]
    for q in zone['quests']:
        q.update(copy.deepcopy(REWRITES.get(q['id'], {})))
    zone['quests'] += copy.deepcopy(QUESTS)
    zone['quests'] += arena
    assert all(len('quest:accept:' + q['id']) <= 32 for q in zone['quests'])
