"""People, buildings and quests of Bifrost Reach's one hub: Heimdall's Perch, the Valkyrie outpost on the island where
the Stormrift lands you (levels 30-35).

Imported by generate_bifrost.py. NPC positions sit beside the buildings drawn here; the generator checks that every one of
them is reachable and clear of scenery. Quest ids are `sky_*`, NPC ids `sky_*`.

The zone's new mechanic is the `hold` objective ("hold the ward"): stand inside a ward circle for a number of seconds
while waves of storm-spawn wake and hunt you. Three quests use it (the first ward, the vigil, the last ward); everything
else is the familiar mix of talk tours, hunts, hand-ins (`bring`) and visits.
"""
import json
from pathlib import Path

import mercenary_offers as mo
import progression_quests
from skaldholm_content import look

ROOT = Path(__file__).resolve().parents[1]
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth
P = 'sky_'

HEALER_OFFERS = [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
                 dict(id='buy_mana_potion', label='Buy Mana Potion · 100 mana instantly', cost=30, item='mana_potion', tiered=True),
                 dict(id='buy_health_potion', label='Buy Health Potion · 100 HP instantly', cost=30, item='health_potion', tiered=True)]
TRADER_OFFERS = [dict(id='buy_traveler_stew', label="Buy Traveler's Stew · 100 HP and mana over 8 s", cost=12, item='traveler_stew', tiered=True),
                 dict(id='satchel', label='Buy Linen Satchel · 6 extra bag slots', cost=500, bag='linen_satchel')]

HUB = dict(name="Heimdall's Perch", x0=62, x1=98, y0=124, y1=153, plaza=dict(x=80, y=136), radius=3.5, entry=dict(x=80, y=141))


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


def hold(place, seconds, label):
    """Channel inside a ward circle: the count is seconds (client/quests.js shows it as `34/60 s`)."""
    return dict(kind='hold', target=place, label=label, count=seconds)


def quest(id, title, giver, description, objectives, level, gold, requires=None, repeatable=False, **extra):
    # Recommended level; the XP reward is 10% of what that level needs (a server test enforces it).
    return dict(id=P + id, title=title, npc=P + giver, description=description, objectives=objectives, level=level,
                rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold, requires=P + requires if requires else None,
                repeatable=repeatable, **extra)


def perch():
    npcs = [
        npc('warden', 'Shieldmaiden Sigrun Cloudwatcher', 'Warden of the Perch', 80, 131.6, '#9ab4d8',
            'You came up through the Stormrift on your own two feet, which is more than the last three did. Welcome to Heimdall\'s Perch, hero. '
            'Heimdall watched the Bifrost from this rock until the bridge shattered, and the shards have been falling upward ever since: they float, they glow, and everything that lives among them has gone strange. '
            'Meet my people, then come to me, and I will find work for every level you have. The last ward I cannot ask you to hold alone: take the quest and I will hire you the fighters you lack, 250 gold each.',
            mo.offers(), look_=look('#e0b48e', '#d8c070', 'long', 'helm', None, None, 1.0, '#c0d0e8')),
        npc('healer', 'Eira the Windhealer', 'Healer of the Perch', 67, 133.2, '#8ad0c0',
            'Sit down before the wind takes you. My blessing is free and my potions cheap: up here a hero is hurt more by falling than by fighting, and nobody has yet fallen twice. '
            'If a ward goes wrong and the storm-spawn come, do not run for the edge. The edge is that way, and it is a very long walk.',
            HEALER_OFFERS, look_=look('#edc5a1', '#e8e4dc', 'bun', 'hood', None, None, 1.0, '#8ad0c0')),
        npc('trader', 'Hrafn Skyfarer', 'Cloud-trader', 93, 132.8, '#c4a060',
            'Fangs, shards, wings and quills: I buy everything that falls out of the sky, and I sell stew to anyone who can still stand. '
            'I used to run the Bifrost to Asgard and back before it broke. Now I run a stall on a rock. I do not complain; I am not that sort of raven.',
            TRADER_OFFERS, buys=True, look_=look('#c89a72', '#2a2a32', 'short', 'cap', '#3a5a8a', None, 1.0, '#3a5a8a')),
        npc('skadi', 'Gale-Mistress Skadi', 'Keeper of the cloud-wolves', 89, 143.2, '#b8c8e0',
            'They were my hounds once. I raised them on the Windward Meadow and they hunted the wind itself, and then the Bifrost broke and the storm got into them. '
            'Now the galehounds hunt anything that moves, and they move faster than anything that has ever hunted them. Thin the pack and bring me their fangs: I would rather remember them as they were.',
            look_=look('#edc5a1', '#d8d2c4', 'long', None, None, None, 1.0)),
        npc('brokk', 'Prism-smith Brokk', 'Smith of the shards', 94, 141.4, '#d08a5a',
            'Every dwarf dreams of Bifrost metal, and here it lies in the grass, falling apart and getting up to hit people. '
            'The prism golems on the Shardfields are the bridge itself, walking. Break them, bring me the shards, and I will tell you what a rainbow weighs.',
            [dict(id='fitting', label='Replace and fit starter gear', cost=0, gear=True)],
            look_=look('#c89a72', '#8a3a1a', 'bald', None, '#4a4543', '#8a3a1a', 1.05)),
        npc('veleda', 'Stormseer Veleda', 'Reader of the lightning', 66, 141.6, '#a88ac0',
            'The lightning here does not fall; it rises, and it has a pattern. Four wards the Valkyries built hold the storm down, and the storm-spawn have been unpicking them. '
            'A ward holds as long as someone stands in it and means it. Stand inside the circle and do not leave: the storm will send everything it has, and the circle is the only place the storm cannot go.',
            look_=look('#edc5a1', '#8a8a8a', 'long', 'hood', None, None, 1.0, '#7a5a9a')),
        npc('thorgrim', 'Thorgrim Hallskald', 'Keeper of the Fallen', 70, 143.4, '#7a8a9a',
            'Some of the heroes who died in the great wars never reached Valhalla: the Bifrost broke under them. They wander the Hall of the Fallen with their swords still sharp and their names gone. '
            'I keep a book of the names I have found. Put them to rest, bring me the tokens they carried, and when the Hall is quiet, stand a vigil for them.',
            look_=look('#c89a72', '#d8d2c4', 'short', None, '#6a6a72', '#d8d2c4', 1.05)),
    ]
    quests = [
        quest('welcome', 'Above the Storm', 'warden',
              'Meet Eira the Windhealer, Hrafn Skyfarer, Gale-Mistress Skadi, Prism-smith Brokk, Stormseer Veleda and Thorgrim Hallskald, then report to Shieldmaiden Sigrun.',
              [talk('healer', 'Eira the Windhealer'), talk('trader', 'Hrafn Skyfarer'), talk('skadi', 'Gale-Mistress Skadi'),
               talk('brokk', 'Prism-smith Brokk'), talk('veleda', 'Stormseer Veleda'), talk('thorgrim', 'Thorgrim Hallskald')], 30, 800),
        quest('hounds', 'Cloud-Wolves of the Meadow', 'skadi',
              'On Windward Meadow, the island west of the Perch across the long bridge, the galehounds have gone wild. Defeat six of them and tell Skadi.',
              [kill('galehound', 6, 'Defeat Galehounds')], 30, 850, 'welcome'),
        quest('fangs', 'Fangs for the Windcatchers', 'skadi',
              'Skadi wants eight Gale Fangs: she will thread them into windcatchers to warn the Perch when a pack comes.',
              [bring('gale_fang', 8, 'Bring Gale Fangs')], 30, 880, 'hounds'),
        quest('cairn', 'The Windcairn Signal', 'skadi',
              'The old Windcairn on Windward Meadow is how the Perch used to hear the hounds. Walk to the cairn, light it, and clear three galehounds off the meadow while you are there.',
              [visit('sky_windcairn', 'Reach the Windcairn'), kill('galehound', 3, 'Defeat Galehounds')], 31, 920, 'hounds'),
        quest('ward_wind', 'Kindle the Windward Ward', 'veleda',
              'North of Windward Meadow, on a small island of its own, stands the first Valkyrie ward. Veleda says it will take sixty seconds of a hero standing in the circle to re-light it, and that the storm will send hounds to stop you. '
              'Walk to the ward, stand inside the circle and hold it. Leaving the circle only pauses the count; falling loses it all.',
              [hold('sky_ward_wind', 60, 'Hold the Windward Ward')], 31, 1100, 'cairn'),
        quest('golems', 'Shards in the Fields', 'brokk',
              'The Shardfields east of the Perch are crawling with prism golems, pieces of the broken bridge that have decided to be people. Defeat six of them.',
              [kill('prismgolem', 6, 'Defeat Prism Golems')], 31, 950, 'welcome'),
        quest('shards', 'Bring Me Bifrost', 'brokk',
              'Brokk needs eight Prism Shards, still warm from the golems, to make something he refuses to describe.',
              [bring('prism_shard', 8, 'Bring Prism Shards')], 32, 980, 'golems'),
        quest('spire', 'Eyes on the Spire', 'veleda',
              'On a small island north of the Shardfields stands the Lightning Spire, where the storm rises. Walk to the spire, read what the lightning is doing, and clear three prism golems from the fields on the way.',
              [visit('sky_spire', 'Reach the Lightning Spire'), kill('prismgolem', 3, 'Defeat Prism Golems')], 32, 1000, 'golems'),
        quest('rays', 'Lightning Eaters', 'veleda',
              'The skyrays of the Stormcrown, the island at the heart of the Reach, feed on the rising lightning and shoot it back. Cross either bridge and defeat six of them.',
              [kill('skyray', 6, 'Defeat Skyrays')], 32, 1050, 'spire'),
        quest('wings', 'Wings for the Weathervane', 'veleda',
              'Veleda wants eight Stormray Wings to rebuild the Perch\'s weathervane, which has been reading the wind backwards since the bridge broke.',
              [bring('stormray_wing', 8, 'Bring Stormray Wings')], 33, 1100, 'rays'),
        quest('pylon', 'The Bifrost Pylon', 'warden',
              'At the centre of the Stormcrown stands the last pylon of the old bridge. Walk to it and defeat two skyrays that circle it, then tell Sigrun if it still hums.',
              [visit('sky_pylon', 'Reach the Bifrost Pylon'), kill('skyray', 2, 'Defeat Skyrays')], 33, 1150, 'rays'),
        quest('dead', 'The Restless Dead', 'thorgrim',
              'North-west of the Stormcrown, past the bridge, lies the Hall of the Fallen. The einherjar there have forgotten they are dead. Defeat six of them.',
              [kill('einherjar', 6, 'Defeat Hollow Einherjar')], 33, 1200, 'pylon'),
        quest('tokens', 'Tokens of the Fallen', 'thorgrim',
              'Each of the dead carries a rune token with their name worn off. Thorgrim will read them one by one. Bring him eight.',
              [bring('rune_token', 8, 'Bring Rune Tokens')], 34, 1250, 'dead'),
        quest('hallgate', 'Knock at the Hall Gate', 'thorgrim',
              'The Hall Gate on the east side of the Hall of the Fallen has not opened since the bridge broke. Walk to it, and put three einherjar to rest on the way.',
              [visit('sky_hallgate', 'Reach the Hall Gate'), kill('einherjar', 3, 'Defeat Hollow Einherjar')], 34, 1300, 'dead'),
        dict(quest('ward_vigil', "The Fallen's Vigil", 'thorgrim',
                   'In the Hall of the Fallen stands the second ward: the vigil lamp. Stand inside its circle for seventy-five seconds and the dead will know they are remembered. '
                   'They will not take it quietly: first the einherjar, then the skyrays that nest in the rafters. Leaving the circle pauses the count; falling loses it all. Thorgrim gives a guaranteed blue Amber Ring.',
                   [hold('sky_ward_vigil', 75, "Hold the Fallen's Vigil")], 34, 1500, 'hallgate'),
             rewardItem='accessory_amber_l20_blue'),
        quest('rocs', 'Thunder Over the Eyrie', 'warden',
              'Across the long bridge from the Hall of the Fallen lies the Roc\'s Eyrie, and the thunderrocs there dive on anything that crosses. Defeat five of them.',
              [kill('thunderroc', 5, 'Defeat Thunderrocs')], 35, 1400, 'ward_vigil'),
        quest('quills', 'Quills of the Storm Roc', 'warden',
              'A thunderroc quill still crackles a day after it falls. Bring Sigrun eight of them: she will build the lightning rod the Perch needs.',
              [bring('thunderroc_quill', 8, 'Bring Thunderroc Quills')], 35, 1450, 'rocs'),
        dict(quest('ward_last', 'The Last Ward', 'warden',
                   'Under the Eyrie\'s great nest stands the last ward, the one that holds the whole storm down. If it falls, the Reach falls. It needs a hero in the circle for two full minutes, and the storm will send everything it has: thunderrocs first, then prism golems, then thunderrocs again. '
                   'Stay inside the circle and bring friends: three heroes can take turns to heal and hold. Leaving the circle pauses the count; falling loses it all. Return to Sigrun for a guaranteed epic pair of Mythic Wayfarer Pants, usable by every class.',
                   [hold('sky_ward_last', 120, 'Hold the Last Ward (Group · 3 players)')], 35, 3000, 'quills'),
             group=True, rewardItem='pants_wayfarer_l20_purple', recommendedPlayers=3),
        quest('patrol', 'Skywatch Patrol', 'trader',
              'Hrafn pays for every beast that falls off the edge of the Perch\'s peace. Defeat fourteen enemies anywhere in Bifrost Reach and return to him. This patrol can be repeated.',
              [kill('any', 14, 'Defeat Bifrost Reach enemies')], 31, 900, 'welcome', True),
        quest('bounty', 'The Reach Bounty', 'warden',
              'Sigrun posts a standing bounty: three galehounds, three prism golems and three skyrays. Collect it as often as you like.',
              [kill('galehound', 3, 'Defeat Galehounds'), kill('prismgolem', 3, 'Defeat Prism Golems'), kill('skyray', 3, 'Defeat Skyrays')], 33, 1150, 'rays', True),
        quest('vanguard', 'Warden of the Reach', 'warden',
              'Prove you hold the whole Reach: defeat two of every monster that lives here, from the hounds of the meadow to the rocs of the Eyrie, and report to Sigrun.',
              [kill(kind, 2, 'Defeat ' + label) for kind, label in
               [('galehound', 'Galehounds'), ('prismgolem', 'Prism Golems'), ('skyray', 'Skyrays'), ('einherjar', 'Hollow Einherjar'), ('thunderroc', 'Thunderrocs')]],
              35, 1600, 'quills'),
    ]
    quests += progression_quests.for_zone(NAME)
    objects = [
        house(80, 127.4, '#7a8fb8', 'Valkyrie Hall', 6.4, 4.0, 'chapel'),
        house(66, 129.4, '#8ad0c0', 'Sky Infirmary'),
        dict(kind='stall', x=93, y=129.6, r=0, v=0, width=2.2, depth=1.4, color='#c4a060', label='Stores'),
        house(65, 138, '#8a6ab0', 'Storm Observatory', 4.0, 3.4, 'chapel'),
        house(94, 138, '#b0703a', 'Prism Forge', 3.8, 3.2),
        house(69.5, 147.2, '#6a7a8c', 'Archive of the Fallen', 3.8, 3.2),
        house(89, 147.2, '#b8c8e0', 'Windcatcher Loft', 3.6, 3.2),
        dict(kind='fountain', x=80, y=136, r=1.1, v=0),
        dict(kind='noticeboard', x=74, y=133, r=.4, width=1.3, depth=.4, label="Heimdall's Perch"),
        dict(kind='bench', x=75.5, y=138.8, r=0, v=0, width=1.5, depth=.45),
        dict(kind='bench', x=84.5, y=138.8, r=0, v=0, width=1.5, depth=.45),
    ]
    for x, y in [(72, 126), (88, 126), (63.5, 133), (96, 133), (63.5, 144), (96.5, 144), (76, 142), (84, 142), (77.5, 149.2), (70, 135), (90, 135)]:
        objects.append(lamp(x, y))
    return npcs, quests, objects, dict(HUB)


NAME = 'Bifrost Reach'
