"""People, buildings and quests of the Wyrdwood's two hubs: Hollowmoot (a root-town beneath the Elder Ash, levels 20-25)
and Skuldwatch (the hill-fort at the north end of the Troll Bridge, levels 25-30).

Imported by generate_wyrdwood.py. Positions of the people sit beside the buildings drawn here; the generator checks that
every one of them is reachable and clear of scenery. Quest ids are `wyrd_*`, NPC ids `wyrd_*`.

Thirty objectives of eight kinds keep the questline from repeating itself: talk tours, hunts, hand-ins (`bring`), visits
to named places (`visit`: the herb glade, the gallows, three beacons, the standing stones), a message to the other hub,
a mixed hunt, two group quests against the elites, and an escort.
"""
import json
from pathlib import Path

import mercenary_offers as mo
import progression_quests
from quest_gear_rewards import add_reward
from skaldholm_content import look

ROOT = Path(__file__).resolve().parents[1]
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth
P = 'wyrd_'

HEALER_OFFERS = [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
                 dict(id='buy_mana_potion', label='Buy Mana Potion · 100 mana instantly', cost=30, item='mana_potion', tiered=True),
                 dict(id='buy_health_potion', label='Buy Health Potion · 100 HP instantly', cost=30, item='health_potion', tiered=True)]
TRADER_OFFERS = [dict(id='buy_traveler_stew', label="Buy Traveler's Stew · 100 HP and mana over 8 s", cost=12, item='traveler_stew', tiered=True),
                 dict(id='satchel', label='Buy Linen Satchel · 6 extra bag slots', cost=500, bag='linen_satchel')]


def npc(id, name, role, x, y, color, dialogue, offers=None, buys=False, look_=None):
    n = dict(id=P + id, name=name, role=role, x=x, y=y, color=color, dialogue=dialogue, offers=offers or [], buys=buys)
    if look_:
        n['look'] = look_
    return n


def house(x, y, color, label, w=3.4, d=3.2, kind='house'):
    return dict(kind=kind, x=x, y=y, r=0, v=0, width=w, depth=d, color=color, label=label)


def lamp(x, y):
    return dict(kind='lamp', x=x, y=y, r=.18, v=0)


def kill(kind, count, label):
    return dict(kind='kill', target=kind, label=label, count=count)


def talk(id, name):
    return dict(kind='talk', target=P + id, label='Speak to ' + name, count=1)


def bring(item, count, label):
    return dict(kind='bring', target=item, label=label, count=count)


def visit(place, label):
    return dict(kind='visit', target=place, label=label, count=1)


def quest(id, title, giver, description, objectives, level, gold, requires=None, repeatable=False, **extra):
    # Recommended level; the XP reward is 10% of what that level needs (a server test enforces it).
    return add_reward(dict(id=P + id, title=title, npc=P + giver, description=description, objectives=objectives, level=level,
                rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold, requires=P + requires if requires else None,
                repeatable=repeatable, **extra))


# ======================================================================================================================
# Hollowmoot
# ======================================================================================================================
def hollowmoot():
    npcs = [
        npc('warden', 'Moot-Warden Bjorn Oakhand', 'Warden of the Moot', 33, 140.2, '#8a6a3a',
            'Welcome to Hollowmoot, friend. We live in the roots of the Elder Ash because the Ash has always looked after us, and now it is the Ash that needs looking after. '
            'The boars are rotten with red blight, the crows have crowded Gallows Hill, and the great Oakhorn, the grove\'s own guardian, has gone mad with a thread through its heart. '
            'Meet my people, then come to me: there is work for every level you have. For the Oakhorn itself I can hire you the fighters you lack, 250 gold each.',
            mo.offers(), look_=look('#e0b48e', '#8a5a34', 'short', None, None, '#8a5a34', 1.05)),
        npc('healer', 'Hedgewife Groa', 'Healer of Hollowmoot', 16, 143.2, '#5f8a62',
            'Sit, sit. My blessing costs nothing and my potions little. If you go into the boarwood, wear something you do not mind losing: the red blight comes out of their tusks and it does not wash.',
            HEALER_OFFERS, look_=look('#edc5a1', '#d8d2c4', 'bun', 'bonnet', None, None, 1.0, '#6a9a6a')),
        npc('trader', 'Gunnhild Gearwright', 'Trader & tinker', 50, 142.2, '#9a7a52',
            'Tusks, feathers, hides and threads: I buy them all. The Moot pays me in honey, so I pay you in gold. Stew and satchels too, and a patrol contract never runs dry for a hero with legs.',
            TRADER_OFFERS, buys=True, look_=look('#e0b48e', '#755841', 'short', 'cap', '#b07a3c', None, 1.0, '#7a5a3c')),
        npc('forester', 'Forester Ulf Longstride', 'Chief forester', 49, 163, '#667c91',
            'There are four things in the south wood. Boars in the west, where the blight began. Crows on Gallows Hill in the east. Trolls under the river bank, and between them, in his grove, the Oakhorn. Keep to the trail and you will count the days you keep your hide.',
            look_=look('#c89a72', '#4a3a2a', 'short', 'feather', None, '#4a3a2a', 1.0, '#5f7f48')),
        npc('wright', 'Ash-wright Hallveig', 'Palisade builder', 17, 162, '#b8744e',
            'The palisade is only as good as its stakes, and the best stakes are boar tusks, if you can stand the smell. Bring me some, and when I run short of them I will find you something to hit.',
            look_=look('#e0b48e', '#a4623c', 'long', None, '#8a6a4a', None, 1.0)),
        npc('bard', 'Starkad the Songbreaker', 'Bard of the Singing Stag', 31, 167.3, '#a8606a',
            'I once sang the Hanged King down from his gallows, and his crows sing back at me every night. A good feather makes a good quill. A good quill makes a better ballad. Bring me feathers and I will put your name in one.',
            look_=look('#edc5a1', '#c9a24a', 'short', 'feather', None, None, 1.0, '#a8606a')),
        npc('beekeeper', 'Beekeeper Torunn', 'Keeper of the Apiary', 42, 169.4, '#c4a060',
            'My bees still work the Moonpetal Glade, south of town. Odd, that. Everything else in the wood has gone wyrd, but the bees only hum louder. I would not put it past them to know something we do not.',
            look_=look('#edc5a1', '#d8d2c4', 'bun', 'straw', '#d8c89a', None, 1.0, '#d8c070')),
    ]
    quests = [
        quest('welcome', 'Under the Elder Ash', 'warden',
              'Meet Hedgewife Groa, Gunnhild Gearwright, Forester Ulf, Ash-wright Hallveig, Starkad the Songbreaker and Beekeeper Torunn, then report to Moot-Warden Bjorn.',
              [talk('healer', 'Hedgewife Groa'), talk('trader', 'Gunnhild Gearwright'), talk('forester', 'Forester Ulf Longstride'),
               talk('wright', 'Ash-wright Hallveig'), talk('bard', 'Starkad the Songbreaker'), talk('beekeeper', 'Beekeeper Torunn')], 20, 420),
        quest('boars', 'Rot in the Roots', 'forester',
              'West and south of Hollowmoot the Rotfang Boars have gone mad with the red blight. Defeat six of them before it reaches the palisade. Report to Ulf.',
              [kill('boar', 6, 'Defeat Rotfang Boars')], 21, 460, 'welcome'),
        quest('tusks', 'Tusks for the Palisade', 'wright',
              'Hallveig needs eight Rotfang Tusks to rebuild the palisade stakes. Bring them to her.',
              [bring('rotfang_tusk', 8, 'Bring Rotfang Tusks')], 21, 470, 'welcome'),
        quest('moonpetal', 'Moonpetals at Midnight', 'healer',
              'Groa needs moonpetals for her blight salve, and the only ones still blooming grow in the glade south of Hollowmoot. Walk to the Moonpetal Glade, and clear three Rotfang Boars off the herb beds on the way. Then tell Groa what you saw.',
              [visit('wyrd_glade', 'Find the Moonpetal Glade'), kill('boar', 3, 'Defeat Rotfang Boars')], 22, 500, 'boars'),
        quest('crows', 'Murder on Gallows Hill', 'forester',
              'The Hanged King\'s gallows in the south-east draw every crow in the Wyrdwood, and they shoot feathers like arrows. Defeat six Gallowcrows and tell Ulf they are not coming back.',
              [kill('crow', 6, 'Defeat Gallowcrows')], 23, 540, 'boars'),
        quest('feathers', 'Quills for the Songbreaker', 'bard',
              'Starkad swears a ballad needs a Gallows Feather for every verse. Bring him ten.',
              [bring('gallows_feather', 10, 'Bring Gallows Feathers')], 23, 560, 'crows'),
        quest('gallows', 'A Song at the Gallows', 'bard',
              'Starkad wants someone to stand at Gallows Rock, at the top of the hill in the south-east, and listen: the old verses say the Hanged King answers a visitor. Walk to Gallows Rock and come back to tell him what you heard.',
              [visit('wyrd_gallows_rock', 'Stand at Gallows Rock')], 24, 590, 'feathers'),
        dict(quest('oakhorn', 'Three Against the Oakhorn', 'warden',
                   'In the grove south-east of the bridge the Oakhorn, the Wyrdwood\'s oldest stag, thrashes at a shining thread that no knife will cut. It stampedes with its antlers lowered and cannot be outrun for long: one hero meets a quick end, two a quicker one. '
                   'Bring two companions, three heroes of level 25 with someone to heal. All three accept this quest and strike the Oakhorn; stay close and alive when it falls. '
                   'Return to Bjorn for a guaranteed blue pair of Celestial Wayfarer Pants, usable by every class.',
                   [kill('oakhorn', 1, 'Defeat the Oakhorn (Elite · 3 players)')], 25, 1800, 'crows'),
             group=True, rewardItem='pants_wayfarer_l20_blue', recommendedPlayers=3),
        quest('seal', "The Warden's Seal", 'warden',
              'Bjorn has written to the Warder-Captain at Skuldwatch, the hill-fort beyond the Troll Bridge, and the letter needs a hero to carry it. Cross the bridge, speak to Warder-Captain Thyra Ironbrow, and hurry back to the Warden. While you are at Skuldwatch, speak to its travel master: afterwards the trip back is a flight of twenty gold.',
              [talk('captain', 'Warder-Captain Thyra Ironbrow')], 25, 600, 'crows'),
        quest('patrol', 'Moot Patrol', 'forester',
              'Ulf pays for every beast that does not make it to the palisade. Defeat twelve enemies anywhere in the Wyrdwood and return to him. This patrol can be repeated.',
              [kill('any', 12, 'Defeat Wyrdwood enemies')], 21, 440, 'welcome', True),
        quest('bounty', 'The Hollow Bounty', 'warden',
              'Bjorn offers a standing bounty: four Rotfang Boars and four Gallowcrows. Collect it as often as you like.',
              [kill('boar', 4, 'Defeat Rotfang Boars'), kill('crow', 4, 'Defeat Gallowcrows')], 23, 540, 'boars', True),
    ]
    quests += progression_quests.for_zone('Wyrdwood')
    objects = [
        dict(kind='elderash', x=33, y=150, r=3.6, v=0),
        house(33, 136.2, '#6a8a5a', 'Moot Hall', 4.4, 3.6, 'chapel'),
        house(16, 140, '#5f8a62', "Hedgewife's Hut"),
        house(50, 139, '#8a6a4a', "Gearwright's"),
        house(49, 160, '#667c91', "Forester's Lodge"),
        house(17, 159, '#b8744e', "Ash-wright's"),
        house(31, 164, '#a8606a', 'The Singing Stag', 4.0, 3.4),
        house(42, 167, '#c4a060', 'Apiary', 3.0, 2.9),
        dict(kind='stall', x=44, y=143.4, r=0, v=0, width=1.8, depth=1.2, color='#b6864d', label='Market'),
        dict(kind='stall', x=22, y=156, r=0, v=0, width=1.8, depth=1.2, color='#c4a060', label='Honey'),
        dict(kind='noticeboard', x=25, y=146, r=.4, width=1.3, depth=.4, label='Hollowmoot'),
        dict(kind='bench', x=27.5, y=154.6, r=0, v=0, width=1.5, depth=.45),
        dict(kind='bench', x=38.5, y=154.6, r=0, v=0, width=1.5, depth=.45),
    ]
    for x, y in [(33, 132.5), (25, 138), (41, 138), (12, 147), (54, 148), (12, 153), (54, 154), (24, 160), (40, 160), (20, 167), (52, 168),
                 (26, 150), (40, 150), (33, 157.5), (33, 142.5)]:
        objects.append(lamp(x, y))
    return npcs, quests, objects, dict(HOLLOW_CITY)


HOLLOW_CITY = dict(name='Hollowmoot', x0=9, x1=57, y0=131, y1=172, plaza=dict(x=33, y=150), radius=3.5, entry=dict(x=33, y=157.5))


# ======================================================================================================================
# Skuldwatch
# ======================================================================================================================
def skuldwatch():
    npcs = [
        npc('captain', 'Warder-Captain Thyra Ironbrow', 'Captain of the Skuld Watch', 79, 84.9, '#58708f',
            'You crossed the bridge with your toes still on? Good. Skuldwatch is the last light between the Wyrdwood and the Highmoor, and the light is going out: our beacons are dark, the trolls take their toll in kind and the storm has begun to answer to something. '
            'Meet my officers and I will find work for every level you have. The giant on the summit I cannot ask you to face alone: take the quest, and I will hire the fighters you lack, 250 gold each.',
            mo.offers(), look_=look('#e0b48e', '#7a3a2a', 'long', 'helm', None, None, 1.0, '#8a97a6')),
        npc('beacon', 'Beaconkeeper Hakon', 'Keeper of the three fires', 101, 89.2, '#d9833a',
            'Three beacons, three fires: the West, the Ridge and the Storm. They have been dark since the first thread snapped, and a dark beacon is a lie told to every ship and every farm for a day\'s ride. Light them and the Watch can see again.',
            look_=look('#c89a72', '#6a6a6a', 'short', None, None, '#6a6a6a', 1.0)),
        npc('mender', 'Mother Sigrid', 'Mender of Skuldwatch', 73, 94.2, '#e4e0d4',
            'Storm-struck, thread-sick or just tired, I mend them all. My blessing costs nothing, the potions little. If you hear a hum in your teeth up on the Highmoor, come down: that is the storm gathering.',
            HEALER_OFFERS, look_=look('#edc5a1', '#e8e4dc', 'bun', 'hood', None, None, 1.0, '#e4e0d4')),
        npc('quartermaster', 'Quartermaster Ketil', 'Stores & contracts', 118, 93.4, '#9a7a52',
            'Mosshide, thread, horn: anything the Highmoor drops I will pay for. I sell stew and satchels, and I keep a standing contract for anyone who wants to go on killing things for money, which is everyone I have met.',
            TRADER_OFFERS, buys=True, look_=look('#c89a72', '#4a3a2a', 'short', 'cap', '#58708f', None, 1.05, '#58708f')),
        npc('loremaster', 'Loremaster Vigdis Runecaller', 'Keeper of the rune hall', 112, 84.8, '#a88ac0',
            'The Norns spin and the Wyrdweavers pull: that is what the runes say, and runes do not lie, only warn. My apprentice Eydis went to chart the Gallows Hill and has not come back. I have counted the days. Find her, and bring her home alive.',
            look_=look('#edc5a1', '#8a8a8a', 'long', 'hood', None, None, 1.0, '#7a5a9a')),
        npc('windspeaker', 'Windspeaker Aud', 'Reader of the storm', 108.5, 91.2, '#6a8fa8',
            'My ram-herders used to bring in the Stormrams for shearing. Now the rams are lit from the inside, and the cloud over the ridge is the colour of a bruise. Something up there is pulling the lightning down on purpose.',
            look_=look('#c89a72', '#d8d2c4', 'short', None, None, '#d8d2c4', 1.0)),
        npc('smith', 'Bolli Anvilbreaker', 'Smith of the Watch', 83, 95.6, '#8a8a92',
            'No, I will not fit you for blue steel. I fit starter steel, and only starter steel, and I will do it for free if you promise to bring it back dented. A dented blade is a happy blade.',
            [dict(id='fitting', label='Replace and fit starter gear', cost=0, gear=True)],
            look_=look('#c89a72', '#3a3a3a', 'bald', None, '#4a4543', '#3a3a3a', 1.1)),
    ]
    quests = [
        quest('watch_welcome', 'Beacons and Banners', 'captain',
              'Meet Beaconkeeper Hakon, Mother Sigrid, Quartermaster Ketil, Loremaster Vigdis and Windspeaker Aud, then report to Warder-Captain Thyra.',
              [talk('beacon', 'Beaconkeeper Hakon'), talk('mender', 'Mother Sigrid'), talk('quartermaster', 'Quartermaster Ketil'),
               talk('loremaster', 'Loremaster Vigdis'), talk('windspeaker', 'Windspeaker Aud')], 25, 650, 'seal'),
        quest('trolls', 'The Toll Is Due', 'captain',
              'The Mosshide Trolls on the south bank have started to demand a toll from every cart, paid in blood. Thyra has a different payment in mind. Defeat six trolls along the river bank.',
              [kill('troll', 6, 'Defeat Mosshide Trolls')], 25, 700, 'watch_welcome'),
        quest('scrap', 'Mosshide for the Mantlets', 'quartermaster',
              'The fort\'s siege mantlets are patched with troll hide. Ketil wants eight pieces of Mosshide Scrap.',
              [bring('mosshide_scrap', 8, 'Bring Mosshide Scrap')], 26, 730, 'trolls'),
        quest('escort', 'Safe Passage', 'loremaster',
              'Vigdis\'s apprentice Eydis Mapwright went to chart Gallows Hill and was cut off at the ruined mill in the far south-east. Find Eydis there, speak to her and walk her back to Skuldwatch along the river and across the Troll Bridge. '
              'She will follow the path at her own pace and wait for you if you lag. Crows and trolls will try to stop you: if Eydis falls, or you do, the quest fails and you must start again at the mill.',
              [dict(kind='escort', target=P + 'eydis', label='Escort Eydis Mapwright to Skuldwatch', count=1)], 26, 1000, 'watch_welcome'),
        quest('beacons', 'Three Fires on the Heights', 'beacon',
              'Hakon gives you a flint and a promise. Climb to the West Beacon on the lower terrace, then to the Ridge Beacon in the east above the first ridge, then to the Storm Beacon in the west of the upper terrace, and light them by standing beside each.',
              [visit('wyrd_beacon_west', 'Light the West Beacon'), visit('wyrd_beacon_ridge', 'Light the Ridge Beacon'), visit('wyrd_beacon_storm', 'Light the Storm Beacon')], 27, 880, 'watch_welcome'),
        quest('weavers', 'Cut the Threads', 'loremaster',
              'The Wyrdweavers sit on the terrace above the fort and pull the fate of the forest into a knot. Defeat six of them.',
              [kill('weaver', 6, 'Defeat Wyrdweavers')], 27, 900, 'watch_welcome'),
        quest('fate', 'Frayed Fate', 'loremaster',
              'Every Wyrdweaver carries a hank of frayed fate. Vigdis can read the knots and unpick the spell, if you bring her eight Frayed Fate Threads.',
              [bring('fate_thread', 8, 'Bring Frayed Fate Threads')], 28, 940, 'weavers'),
        quest('rams', 'Thunder on the Ridge', 'windspeaker',
              'Aud wants the Stormrams on the upper terrace put down before they burn the whole slope. Climb through the ridge gap in the east and defeat six of them.',
              [kill('ram', 6, 'Defeat Stormrams')], 28, 960, 'beacons'),
        quest('stones', 'The Cracked Stones', 'windspeaker',
              'The Norn Stones above the fort are cracking, and the weavers and the rams are camped on them. Walk to the Norn Stones, then defeat three Wyrdweavers and three Stormrams.',
              [visit('wyrd_norn_stones', 'Reach the Norn Stones'), kill('weaver', 3, 'Defeat Wyrdweavers'), kill('ram', 3, 'Defeat Stormrams')], 29, 1000, 'rams'),
        dict(quest('hrungnir', 'Five Against the Stormheart', 'captain',
                   'On the summit of the Highmoor, behind the second ridge, a stone giant called Hrungnir has woken with a storm in his chest, and the Wyrdweavers have tied it to a loom. '
                   'He throws lightning from afar and breaks the ground beneath you when you come near. This is a fight for five heroes of level 30 with someone to heal, someone to hold him and the rest to hit hard. '
                   'All five accept this quest and strike Hrungnir; stay close and alive when he falls. Return to Thyra for a guaranteed epic Mythic Moonstone Necklace, usable by every class.',
                   [kill('hrungnir', 1, 'Defeat Hrungnir (Elite · 5 players)')], 30, 3000, 'stones'),
             group=True, rewardItem='necklace_moonstone_l20_purple', recommendedPlayers=5),
        quest('watch_patrol', 'Watchfire Patrol', 'quartermaster',
              'Ketil pays for every beast that dies on the slopes. Defeat fourteen enemies anywhere in the Wyrdwood and return to him. This patrol can be repeated.',
              [kill('any', 14, 'Defeat Wyrdwood enemies')], 26, 760, 'watch_welcome', True),
        quest('storm_bounty', 'The Storm Bounty', 'windspeaker',
              'Aud posts a standing bounty on the heights: three Wyrdweavers and three Stormrams. Claim it as often as you like.',
              [kill('weaver', 3, 'Defeat Wyrdweavers'), kill('ram', 3, 'Defeat Stormrams')], 29, 990, 'rams', True),
        quest('vanguard', 'Warden of the Wyrdwood', 'captain',
              'Prove you hold the whole Wyrdwood: defeat two of every monster that lives here, from the boars of the south wood to the rams of the ridge, and report to Thyra.',
              [kill(kind, 2, 'Defeat ' + label) for kind, label in
               [('boar', 'Rotfang Boars'), ('crow', 'Gallowcrows'), ('troll', 'Mosshide Trolls'), ('weaver', 'Wyrdweavers'), ('ram', 'Stormrams')]],
              30, 1200, 'stones'),
    ]
    objects = [
        house(79, 80.8, '#6a7480', "Warder's Keep", 6.2, 4.0, 'chapel'),
        house(112, 81, '#7a5a8c', 'Rune Hall', 4.0, 3.4, 'chapel'),
        house(73, 91, '#e0d8c8', 'Infirmary'),
        house(83, 92, '#5a5a62', 'Forge', 3.6, 3.2),
        dict(kind='stall', x=118, y=91, r=0, v=0, width=2.2, depth=1.4, color='#9a7a52', label='Stores'),
        dict(kind='beacon', x=96, y=86, r=1.3, v=0, place='', great=True),
        dict(kind='post', x=107.2, y=89.4, r=.3, v=0),
        dict(kind='noticeboard', x=103, y=77.5, r=.4, width=1.3, depth=.4, label='Skuldwatch'),
        dict(kind='bench', x=88.5, y=84.6, r=0, v=0, width=1.5, depth=.45),
        dict(kind='bench', x=103.5, y=84.6, r=0, v=0, width=1.5, depth=.45),
    ]
    for x, y in [(90, 77), (102, 77), (90, 94), (102, 94), (70, 78), (122, 78), (70, 95), (122, 95), (96, 79), (96, 93.5), (88, 87), (104, 87)]:
        objects.append(lamp(x, y))
    return npcs, quests, objects, dict(SKULD_CITY)


SKULD_CITY = dict(name='Skuldwatch', x0=67, x1=125, y0=75, y1=97, plaza=dict(x=96, y=86), radius=3.5, entry=dict(x=96, y=92))

# The stranded person of the escort quest. Her definition (route, ambushes) is added by the generator, which owns the geometry.
EYDIS = dict(id=P + 'eydis', name='Eydis Mapwright', role='Cartographer, cut off', color='#a88ac0',
             dialogue='Thank the Allfather. The crows cut me off from the road and I have been hiding in this mill for three days with nothing but a quill. If Vigdis sent you, take me to Skuldwatch: I will follow the path at my own pace and I will wait where you tell me. '
                      'And please, stay between me and the claws.',
             offers=[], buys=False,
             look=look('#edc5a1', '#8a4a2a', 'long', 'hood', None, None, 1.0, '#7a5a9a'))
