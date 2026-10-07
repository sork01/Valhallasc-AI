"""People, buildings and quests of Ran's Deep's one hub: Keelhaven, the camp of overturned longships on the sea floor where the
Maelstrom lands you (levels 35-40).

Imported by generate_deep.py. NPC positions sit beside the buildings drawn here; the generator checks that every one of them is
reachable and clear of scenery. Quest ids are `deep_*`, NPC ids `deep_*`.

The zone's new mechanic is the `chime` objective ("ring the tidebells"): a chain of bronze bells stands about the zone, each one
rings for a few seconds after a hero walks into its circle, and the objective is done when every bell of the chain rings at
the same moment. Three quests use it (the harbour bells, the bells of the Net, the bells of Ran); everything else is the
familiar mix of talk tours, hunts, hand-ins (`bring`) and visits, plus one group quest against the Kraken.
"""
import json
from pathlib import Path

import mercenary_offers as mo
import progression_quests
from quest_gear_rewards import add_reward
from skaldholm_content import look

ROOT = Path(__file__).resolve().parents[1]
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth
P = 'deep_'
DY = 19                                                          # Keelhaven stands 19 tiles south of where Bifrost's Perch does

HEALER_OFFERS = [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
                 dict(id='buy_mana_potion', label='Buy Mana Potion · 100 mana instantly', cost=30, item='mana_potion', tiered=True),
                 dict(id='buy_health_potion', label='Buy Health Potion · 100 HP instantly', cost=30, item='health_potion', tiered=True)]
TRADER_OFFERS = [dict(id='buy_traveler_stew', label="Buy Traveler's Stew · 100 HP and mana over 8 s", cost=12, item='traveler_stew', tiered=True),
                 dict(id='satchel', label='Buy Linen Satchel · 6 extra bag slots', cost=500, bag='linen_satchel')]

HUB = dict(name='Keelhaven', x0=62, x1=98, y0=143, y1=172, plaza=dict(x=80, y=136 + DY), radius=3.5, entry=dict(x=80, y=141 + DY))


def npc(id, name, role, x, y, color, dialogue, offers=None, buys=False, look_=None):
    n = dict(id=P + id, name=name, role=role, x=x, y=round(y + DY, 2), color=color, dialogue=dialogue, offers=offers or [], buys=buys)
    if look_:
        n['look'] = look_
    return n


def house(x, y, color, label, w=3.4, d=3.2, kind='house'):
    return dict(kind=kind, x=x, y=round(y + DY, 2), r=0, v=0, width=w, depth=d, color=color, label=label)


def lamp(x, y):
    return dict(kind='lamp', x=x, y=round(y + DY, 2), r=.18, v=0)


def kill(kind, count, label):
    return dict(kind='kill', target=kind, label=label, count=count)


def talk(id, name):
    return dict(kind='talk', target=P + id, label='Speak to ' + name, count=1)


def bring(item, count, label):
    return dict(kind='bring', target=item, label=label, count=count)


def visit(place, label):
    return dict(kind='visit', target=place, label=label, count=1)


def chime(chain, bells, label):
    """Every bell of a chain must ring at the same moment: the count is the number of bells ringing (client/quests.js shows `2/4 lit`)."""
    return dict(kind='chime', target=chain, label=label, count=bells)


def quest(id, title, giver, description, objectives, level, gold, requires=None, repeatable=False, **extra):
    # Recommended level; the XP reward is 10% of what that level needs (a server test enforces it).
    return add_reward(dict(id=P + id, title=title, npc=P + giver, description=description, objectives=objectives, level=level,
                rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold, requires=P + requires if requires else None,
                repeatable=repeatable, **extra))


def keelhaven():
    npcs = [
        npc('warden', 'Skipper Ylva Saltbeard', 'Harbourmistress of Keelhaven', 80, 131.6, '#6aa8c8',
            'You rode the Maelstrom down and arrived with your lungs still your own: Ran does not take everyone, and she must like you. Welcome to Keelhaven, hero. '
            'We are what is left of the fleet that sailed out under the Bifrost the day it broke: forty hulls came down, and we turned them over to make roofs. The air under them is borrowed, so do not shout. '
            'Meet my people, then come to me, and I will find work for every level you have. The Kraken in Ran\'s Court I cannot ask you to face alone: take the quest and I will hire you the fighters you lack, 250 gold each.',
            mo.offers(), look_=look('#d8a07a', '#c8863a', 'long', 'helm', None, '#c8863a', 1.0, '#6a8aa0')),
        npc('healer', 'Brynja the Tidehealer', 'Healer of Keelhaven', 67, 133.2, '#7ad0b8',
            'Sit down and breathe. My blessing is free and my potions cheap: down here a hero is hurt more by pressure than by teeth, and it is the teeth that get the sympathy. '
            'If a siren sings to you, do not walk towards the song. Walk the other way and let somebody else be charmed.',
            HEALER_OFFERS, look_=look('#edc5a1', '#5a7a9a', 'long', None, None, None, 1.0)),
        npc('trader', 'Ottar Netmender', 'Net-trader', 93, 132.8, '#c4a060',
            'Teeth, lures, pearls and plates: I buy everything the Net lets go of, and I sell stew to anyone who can still hold a spoon. '
            'I mend nets for a living, and Ran\'s is the only one I have never managed to mend. It is mending me instead, one knot at a time.',
            TRADER_OFFERS, buys=True, look_=look('#c89a72', '#6a5a4a', 'short', 'cap', '#8a7a5a', None, 1.0, '#3a6a8a')),
        npc('halla', 'Halla Deepdiver', 'Keeper of the dive-bells', 89, 143.2, '#9ac0d8',
            'I have walked the Shallows every day for thirty years, and the dead have started walking back. Draugr, they call them: our own drowned, up out of the Naglfar with their coins still in their pockets. '
            'Some of them I knew. Thin them out, bring me what they carry, and walk out to the old wreck for me; I would like to know the Naglfar is empty, even if it is not.',
            mo.offers(), look_=look('#edc5a1', '#d8d2c4', 'bun', 'hood', None, None, 1.0, '#4a8aa0')),
        npc('ketil', 'Ketil Rustbane', 'Wreck-smith', 94, 141.4, '#c8885a',
            'Forty hulls, and not one of them stayed a ship. I take the iron out of the wrecks and make it into things that keep people alive. '
            'The anglers of the Net are another matter: they carry little lamps on a stalk to draw you in, and the lamps are the best brass anywhere. Break the fish, bring me the lamps, and I will tell you what a light costs.',
            [dict(id='fitting', label='Replace and fit starter gear', cost=0, gear=True)],
            look_=look('#c89a72', '#8a3a1a', 'bald', None, '#4a4543', '#8a3a1a', 1.05)),
        npc('thora', 'Thora Drownedspeaker', 'Reader of the tides', 66, 141.6, '#8a8ac8',
            'Ran keeps a net, and the Net keeps what it catches: sailors, ships, monsters, the bones of whales. The coral grew it a house, and the house grew corridors, and the corridors grew teeth. '
            'In the middle of it, behind two doors, sits something old that Ran herself is afraid of. I read the tides, and the tides say it is waking. Learn the Net, hero, and do not go to the Court before you are ready. And if you meet a pale eel the length of a longship in the deep corridors, do not count on a quest to tell you what it is: it is the Ghostmaw, and it was old when the Net was young.',
            look_=look('#edc5a1', '#7a6a9a', 'long', 'hood', None, None, 1.0, '#6a5a9a')),
        npc('sigmund', 'Old Sigmund Bellwright', 'Founder of the tidebells', 70, 143.4, '#d0a860',
            'I cast bronze for the Bifrost once, and when it fell I kept the metal. Tidebells, I call them: you strike one and it rings for a time, and then it goes quiet. '
            'The old harbour had a chain of them, and when every bell rang at once, the whole sea heard it and every ship knew where home was. Ring them again. Hurry, though: the first bell is silent before the last is struck, if you dawdle.',
            look_=look('#c89a72', '#d8d2c4', 'short', None, '#6a6a72', '#d8d2c4', 1.05)),
    ]
    quests = [
        quest('welcome', 'Beneath the Maelstrom', 'warden',
              'Meet Brynja the Tidehealer, Ottar Netmender, Halla Deepdiver, Ketil Rustbane, Thora Drownedspeaker and Old Sigmund Bellwright, then report to Skipper Ylva.',
              [talk('healer', 'Brynja the Tidehealer'), talk('trader', 'Ottar Netmender'), talk('halla', 'Halla Deepdiver'),
               talk('ketil', 'Ketil Rustbane'), talk('thora', 'Thora Drownedspeaker'), talk('sigmund', 'Old Sigmund Bellwright')], 35, 1200),
        quest('draugr', "Dead Men's Boots", 'halla',
              'On the open sea floor round Keelhaven, the Wreck of Naglfar to the west and the Drowned Chapel to the east, the drowned dead have got up. Defeat six draugr and tell Halla.',
              [kill('draugr', 6, 'Defeat Drowned Draugr')], 35, 1250, 'welcome'),
        quest('coins', 'Coins for the Ferryman', 'halla',
              'Every draugr carries the coin it was buried with, green and furred. Halla wants eight Drowned Coins to put back on the right eyes.',
              [bring('drowned_coin', 8, 'Bring Drowned Coins')], 35, 1300, 'draugr'),
        quest('longship', 'The Wreck of Naglfar', 'halla',
              'West of Keelhaven lies the Naglfar, the ship of the dead, made of the nails of the unburied. Walk to the wreck, see whether anything is left aboard, and put three draugr to rest on the way.',
              [visit('deep_longship', 'Reach the Wreck of Naglfar'), kill('draugr', 3, 'Defeat Drowned Draugr')], 36, 1350, 'draugr'),
        quest('harbour', 'Ring in the Harbour', 'sigmund',
              'Three tidebells still stand on the sea floor round Keelhaven: one west of the camp, one at the Pearl Gate in front of the Net, one east. Each bell rings for thirty-five seconds after you walk into its circle. '
              'Ring all three so that they sound together, and the harbour will sing again. Walk to a bell and the count starts; a bell that falls silent takes its share of the count with it.',
              [chime('deep_harbour', 3, 'Ring the Harbour Bells')], 36, 1450, 'longship'),
        quest('anglers', 'Lights in the Dark', 'ketil',
              'The first rooms of the Net, the maze of coral north of the Pearl Gate, are home to the lantern anglers: fish that shoot beads of light. Go through the Pearl Gate and defeat six of them.',
              [kill('angler', 6, 'Defeat Lantern Anglers')], 36, 1400, 'welcome'),
        quest('lures', 'Brass from the Deep', 'ketil',
              'Ketil needs eight Angler Lures: the lamps on their stalks, still glowing and still warm.',
              [bring('angler_lure', 8, 'Bring Angler Lures')], 37, 1450, 'anglers'),
        quest('morays', 'Teeth in the Coral', 'trader',
              'Deeper in the Net, past the first turns, live the gnashing morays, eels as long as a longship that strike from the coral without warning. Defeat six of them.',
              [kill('moray', 6, 'Defeat Gnashing Morays')], 37, 1500, 'harbour'),
        quest('teeth', 'A Net Full of Teeth', 'trader',
              'Ottar wants eight Moray Teeth to make into needles. Mending a net takes a very large needle.',
              [bring('moray_tooth', 8, 'Bring Moray Teeth')], 37, 1550, 'morays'),
        quest('chapel', 'The Drowned Chapel', 'trader',
              'East of Keelhaven the old harbour chapel still stands under the water, and nobody has been inside since the draugr came. Walk to the chapel and put three draugr to rest on the way.',
              [visit('deep_chapel', 'Reach the Drowned Chapel'), kill('draugr', 3, 'Defeat Drowned Draugr')], 37, 1550, 'coins'),
        dict(quest('captain', 'Three Against the Drowned Captain', 'halla',
                   'Hvitserk Black-Coat captained the Naglfar when she sank, and he never left the deck: he stands in the west Shallows, north of the wreck, with his axe in his fist and his whole crew behind him in the mud. '
                   'He swings like a ship coming about. Do not go alone: bring two friends, or take the quest and I will hire you the fighters you lack, 250 gold each. Return to me for a guaranteed blue Celestial Amber Ring, usable by every class.',
                   [kill('hvitserk', 1, 'Defeat Hvitserk the Drowned (Group · 3 players)')], 37, 3000, 'longship'),
             group=True, rewardItem='accessory_amber_l20_blue', recommendedPlayers=3),
        dict(quest('net', 'The Bells of the Net', 'sigmund',
                   'Sigmund hung four bells inside the Net when it was young and the corridors were short, and the coral has grown round them since. Find them: they stand in the middle rooms, where the morays and the sirens live. '
                   'Each rings for forty-five seconds once you reach its circle, and all four must ring together. Learn the way between them first, and then run it. Sigmund gives a guaranteed blue Verdigris Ring.',
                   [chime('deep_net', 4, 'Ring the Bells of the Net')], 38, 2000, 'teeth'),
             rewardItem='accessory_amber_l20_vault'),
        quest('sirens', 'Songs Without Words', 'healer',
              'Deeper in the Net sing the sirens, Ran\'s handmaidens, and the song hurts. They shoot it, in three bolts, from a distance. Defeat six of them before they sing the Net into your head.',
              [kill('siren', 6, 'Defeat Sirens')], 38, 1600, 'teeth'),
        quest('pearls', 'Pearls for the Tidehealer', 'healer',
              'A siren\'s pearl calms a fever and a panic alike. Brynja wants eight Siren Pearls for her stores.',
              [bring('siren_pearl', 8, 'Bring Siren Pearls')], 39, 1650, 'sirens'),
        quest('door', 'The Court Door', 'thora',
              'Ran\'s Court, the room at the heart of the Net, has exactly two doors. Find one, stand in front of it and see what is looking back: then walk away from it and defeat two sirens on the way.',
              [visit('deep_courtdoor', 'Reach the Court Door'), kill('siren', 2, 'Defeat Sirens')], 39, 1700, 'sirens'),
        quest('shellbacks', 'Shells of the Deep', 'thora',
              'In the deepest corridors of the Net live the shellbacks, turtles the size of a house with plates like a drowned hull. Their slam is felt through the floor. Defeat six of them.',
              [kill('shellback', 6, 'Defeat Shellbacks')], 39, 1750, 'door'),
        quest('plates', 'Plates of the Shellback', 'thora',
              'Thora reads the tides in the grain of a shellback\'s plate. Bring her eight of them.',
              [bring('shellback_plate', 8, 'Bring Shellback Plates')], 40, 1800, 'shellbacks'),
        quest('garden', 'The Abyssal Garden', 'thora',
              'At the bottom of the Net, in a dead end that no current reaches, grows a garden of glowing anemones. Walk there, look at what Ran has been feeding, and defeat three shellbacks on the way.',
              [visit('deep_garden', 'Reach the Abyssal Garden'), kill('shellback', 3, 'Defeat Shellbacks')], 40, 1850, 'shellbacks'),
        dict(quest('rans', 'The Bells of Ran', 'sigmund',
                   'The last chain is the greatest: five bells round Ran\'s Court itself, hung where the Kraken\'s long arms can hear them. Each rings for fifty seconds, and the corridors between them are the longest and the most crowded in the Net. '
                   'Walk to one, then run the ring. Sigmund gives a guaranteed pair of Vaultwalker Pants, usable by every class.',
                   [chime('deep_rans', 5, 'Ring the Bells of Ran')], 40, 2600, 'garden'),
             rewardItem='pants_wayfarer_l20_vault'),
        dict(quest('kraken', 'Five Against the Kraken', 'warden',
                   'Behind two doors in the heart of the Net sleeps the Kraken, and the five bells have woken it. It throws ink from a distance and slams anything that comes close, and the whole sea shakes. '
                   'Do not go alone. Bring four friends, or take the quest and I will hire you the fighters you lack. Return to Ylva for a guaranteed epic Mythic Moonstone Necklace, usable by every class.',
                   [kill('kraken', 1, 'Defeat the Kraken (Group · 5 players)')], 40, 5000, 'rans'),
             group=True, rewardItem='necklace_moonstone_l20_purple', recommendedPlayers=5),
        quest('patrol', 'Net Patrol', 'trader',
              'Ottar pays for every beast that is taken out of the Net. Defeat fourteen enemies anywhere in Ran\'s Deep and return to him. This patrol can be repeated.',
              [kill('any', 14, "Defeat Ran's Deep enemies")], 36, 1350, 'welcome', True),
        quest('bounty', 'The Deep Bounty', 'warden',
              'Ylva posts a standing bounty: three draugr, three lantern anglers, three morays and three sirens. Collect it as often as you like.',
              [kill('draugr', 3, 'Defeat Drowned Draugr'), kill('angler', 3, 'Defeat Lantern Anglers'), kill('moray', 3, 'Defeat Gnashing Morays'), kill('siren', 3, 'Defeat Sirens')],
              38, 1700, 'sirens', True),
        quest('vanguard', "Warden of Ran's Deep", 'warden',
              "Prove you hold the whole of the deep: defeat two of every monster that lives here, from the draugr of the Shallows to the shellbacks at the bottom of the Net, and report to Ylva.",
              [kill(kind, 2, 'Defeat ' + label) for kind, label in
               [('draugr', 'Drowned Draugr'), ('angler', 'Lantern Anglers'), ('moray', 'Gnashing Morays'), ('siren', 'Sirens'), ('shellback', 'Shellbacks')]],
              40, 2400, 'kraken'),
    ]
    quests += progression_quests.for_zone(NAME)
    objects = [
        house(80, 127.4, '#4f8fb0', 'Harbour Hall', 6.4, 4.0, 'chapel'),
        house(66, 129.4, '#5ec0a8', 'Tide Infirmary'),
        dict(kind='stall', x=93, y=129.6 + DY, r=0, v=0, width=2.2, depth=1.4, color='#c4a060', label='Stores'),
        house(65, 138, '#7a6ab8', 'Tide Library', 4.0, 3.4, 'chapel'),
        house(94, 138, '#b0703a', 'Wreck Forge', 3.8, 3.2),
        house(69.5, 147.2, '#c8a050', 'Bell Foundry', 3.8, 3.2),
        house(89, 147.2, '#6a98b8', 'Dive Lodge', 3.6, 3.2),
        dict(kind='fountain', x=80, y=136 + DY, r=1.1, v=0),
        dict(kind='noticeboard', x=74, y=133 + DY, r=.4, width=1.3, depth=.4, label='Keelhaven'),
        dict(kind='bench', x=75.5, y=138.8 + DY, r=0, v=0, width=1.5, depth=.45),
        dict(kind='bench', x=84.5, y=138.8 + DY, r=0, v=0, width=1.5, depth=.45),
    ]
    for x, y in [(72, 126), (88, 126), (63.5, 133), (96, 133), (63.5, 144), (96.5, 144), (76, 142), (84, 142), (77.5, 149.2), (70, 135), (90, 135)]:
        objects.append(lamp(x, y))
    return npcs, quests, objects, dict(HUB)


NAME = "Rán's Deep"
