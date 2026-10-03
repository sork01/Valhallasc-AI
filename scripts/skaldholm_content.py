"""People and errands of Skaldholm (zone 4): quest givers, townsfolk who only talk, walkers, and eleven quests.

Imported by generate_skaldholm.py. Positions of the stationary people are chosen to sit beside the buildings the
generator puts down; the generator checks that every one of them is reachable and clear of scenery.
"""
import json
from pathlib import Path

import mercenary_offers
import progression_quests

ROOT = Path(__file__).resolve().parents[1]
LEVEL_XP = json.loads((ROOT / 'world/levels.txt').read_text())  # XP to next level; a quest pays a tenth
P = 'city_'

HEALER_OFFERS = [dict(id='blessing', label='Receive a healing blessing', cost=0, heal=10000),
                 dict(id='buy_mana_potion', label='Buy Mana Potion · 100 mana instantly', cost=30, item='mana_potion', tiered=True),
                 dict(id='buy_health_potion', label='Buy Health Potion · 100 HP instantly', cost=30, item='health_potion', tiered=True)]
GUILD_OFFERS = [dict(id='buy_traveler_stew', label="Buy Traveler's Stew · 100 HP and mana over 8 s", cost=12, item='traveler_stew', tiered=True),
                dict(id='satchel', label='Buy Linen Satchel · 6 extra bag slots', cost=500, bag='linen_satchel')]
SMITH_OFFERS = [dict(id='fitting', label='Replace and fit starter gear', cost=0, gear=True)]
INN_OFFERS = [dict(id='rest', label='Meal & rest · fully restores HP', cost=5, heal=10000)]


def look(skin='#edc5a1', hair='#755841', style='short', hat=None, apron=None, beard=None, scale=1.0, hat_color=None):
    out = dict(skin=skin, hair=hair, style=style)
    if hat:
        out['hat'] = hat
        out['hatColor'] = hat_color or '#7a5a3c'
    if apron:
        out['apron'] = apron
    if beard:
        out['beard'] = beard
    if scale != 1.0:
        out['scale'] = scale
    return out


def person(id, name, role, x, y, color, dialogue, offers=None, buys=False, look_=None, route=None, speed=0.0, pause=0.0, phase=0.0, art=None):
    n = dict(id=P + id, name=name, role=role, x=x, y=y, color=color, dialogue=dialogue, offers=offers or [], buys=buys)
    if art:
        n['art'] = art
    if look_:
        n['look'] = look_
    if route:
        n['route'] = [[round(a, 2), round(b, 2)] for a, b in route]
        n['speed'] = speed
        n['pause'] = pause
        n['phase'] = phase
        n['x'], n['y'] = n['route'][0]
    return n


# ---- the people with work or wares -------------------------------------------------------------------------------
def key_people():
    return [
        person('captain', 'Captain Ingrid Stormwatch', 'Captain of the Watch', 70.5, 133.5, '#58708f',
               'Halt — no, go on through. Nobody who walked the glacier needs to explain themselves to me. Welcome to Skaldholm. No blade is drawn inside these walls and nothing with fangs has crossed the Great Gate in two hundred years. Meet the people who keep the city running, then report back to me.',
               look_=look('#e0b48e', '#c9a24a', 'long', 'helm', None, None, 1.0, '#a9b5c0')),
        person('steward', 'Steward Halden Voss', 'Steward of Skaldholm', 88.5, 64.5, '#7b5aa0',
               'Skaldholm trades with every hearth between the meadow and the fen, and every one of them owes us a letter, a favour or a barrel. I keep the books. Bring me what the four lands send and the city will remember your name.',
               look_=look('#edc5a1', '#8a8a8a', 'short', 'cap', None, '#8a8a8a', 1.0, '#4f3a6a')),
        person('herald', 'Herald Bran Oakenshield', 'City herald', 74.0, 87.5, '#b04a4a',
               'Hear ye! I carry the city’s letters to the four hearths — or I would, if my knees had not given up at the glacier. Walk them for me and every captain, warden and reeve will know Skaldholm still stands.',
               look_=look('#e8b890', '#6a4a30', 'short', 'feather', None, None, 1.0, '#b04a4a')),
        person('alchemist', 'Alchemist Orsolya Quill', 'Alchemist', 57.0, 81.4, '#4f8a7a',
               'Gel for the base, glands for the body, hides for the stubborn stains. Every cure in this city starts with something a monster was not using any more. Bring me the ingredients and I will brew the rest.',
               look_=look('#f0c8a6', '#d8d0c0', 'bun', None, '#d8e8e0')),
        person('smith', 'Master Smith Brunhild', 'Master smith', 33.5, 98.0, '#8a6a52',
               'The forge never goes cold in Skaldholm, but the cinders do run low. If your starter gear has seen better days I will fit you with a fresh set, no charge. If you want something finer, bring me real fire.',
               SMITH_OFFERS, look_=look('#d9a47e', '#3a2a22', 'bun', None, '#6a5040')),
        person('guildmaster', 'Guildmaster Tobias Greaves', 'Trade guildmaster', 99.0, 66.0, '#a08040',
               'Pelts, horns, shells and fangs: the guild buys them all, and pays fairly. I also sell stew and satchels for the road, and my standing order for the guild never runs dry.',
               GUILD_OFFERS, True, look('#edc5a1', '#555555', 'short', 'cap', '#e7d6b4', '#555555', 1.0, '#a08040')),
        person('healer', 'Sister Liv Ashdown', 'Cathedral healer', 62.0, 36.2, '#e4e0d4',
               'The Cathedral of the Hearth is open to everyone, and so are its blessings. I sell Health Potions for the road. Whatever you carried out of the glacier, set it down here for a while.',
               HEALER_OFFERS, look_=look('#f0c8a6', '#eae8df', 'long', 'hood', None, None, 1.0, '#e4e0d4')),
        person('bard', 'Bard Eira Songweaver', 'Court bard', 100.5, 92.5, '#c8683a',
               'Every hearth I have sat at hums a different tune, and I have never managed to write them down. I am too old to walk to them, and you look as if you have strong legs.',
               look_=look('#edc5a1', '#b0502a', 'long', 'feather', None, None, 1.0, '#2f7a6a')),
        person('librarian', 'Archivist Fenwick Dale', 'Keeper of the archive', 98.0, 35.5, '#6a7ab0',
               'The archive holds every map, tally and tall tale the city has ever received. What it lacks is the fen: nobody has ever brought back more than a rumour, a gauntlet and a headache.',
               look_=look('#edc5a1', '#cfcfcf', 'bald', None, None, '#cfcfcf')),
        person('stonewarden', 'Stonewarden Magnus Hale', 'Keeper of the Meeting Stone', 96.0, 125.5, '#5a7a9a',
               'The Meeting Stone has stood here since before the walls. Wanderers who part at the Great Gate find each other again beside it. Gather your friends at the stone — and if you have too few, speak to the Stone itself: it will call fighters to your side for a fee. Mind the stairs beside it. They lead down to the Undervault, where the first Skalds sealed what they could not kill. Take five, and take a healer.',
               look_=look('#e0b48e', '#e8e8e8', 'short', None, None, '#e8e8e8')),
        person('meetingstone', 'The Meeting Stone', 'Gather your party', 101.7, 119.7, '#59d9ff',
               'The runes brighten as you near. A voice that is not a voice offers you company: fighters of every calling answer the Stone for 250 gold apiece, and fight at your side until you dismiss them, leave your party or log out. A party holds five. The stairs beside the Stone lead down to the Undervault, a dungeon made for five heroes of level 20.',
               mercenary_offers.offers(open_=True), art='stone'),
    ]


# ---- townsfolk who only talk (stationary) ---------------------------------------------------------------------------
def talkers():
    return [
        person('gate_guard_w', 'Guardsman Orm', 'Gate guard', 73.0, 136.4, '#58708f',
               'Move along, friend, and keep to the cobbles. The Captain is just inside the gate, to the west.',
               look_=look('#d9a47e', '#3a2a22', 'short', 'helm', None, None, 1.0, '#a9b5c0')),
        person('gate_guard_e', 'Guardswoman Sigrun', 'Gate guard', 87.0, 136.4, '#58708f',
               'Nothing to declare? Good. Mind the carts on the Grand Avenue: the drivers have never learned to stop.',
               look_=look('#f0c8a6', '#8a4a2a', 'bun', 'helm', None, None, 1.0, '#a9b5c0')),
        person('baker', 'Baker Hild', 'Baker', 71.0, 69.0, '#e3c18a',
               'Honey buns, rye loaves and cardamom twists, still warm. The buns cost three coins. The advice is free: do not stand under the fountain jets with a loaf.',
               look_=look('#f0c8a6', '#b08a50', 'bun', None, '#f6ecd2')),
        person('fishmonger', 'Fishmonger Gunnar', 'Fishmonger', 91.0, 80.5, '#6a8fa8',
               'Fresh from the northern lakes, three days ago. All right, five. They do not complain, and neither should you.',
               look_=look('#d9a47e', '#6a4a30', 'short', 'cap', '#c8d6dc', '#6a4a30', 1.0, '#3a5a7a')),
        person('flowers', 'Flower-girl Maja', 'Flower seller', 80.0, 91.5, '#e6a0b4',
               'Roses for your sweetheart, lavender for your pillow, a daisy for the Captain, who never smiles. A coin a bunch!',
               look_=look('#f0c8a6', '#c9a24a', 'long', 'straw', '#f4e8c8', None, 1.0, '#e6c870')),
        person('cobbler', 'Cobbler Wik', 'Cobbler', 54.0, 70.4, '#8a6a4a',
               'You have walked through snow, ash and bog in those boots, I can tell by the smell. Bring them by when you have a month to spare.',
               look_=look('#edc5a1', '#555555', 'short', None, '#8a6a4a', '#555555')),
        person('washer', 'Washerwoman Berta', 'Washerwoman', 38.5, 54.0, '#9ab0c4',
               'Blood, wine, glacier slush — I have got them all out of a tabard. The well water here is the softest in the city.',
               look_=look('#f0c8a6', '#7a5a3c', 'bun', 'bonnet', '#e8e8e0', None, 1.0, '#e8e0d0')),
        person('grandfather', 'Old Sten', 'Retired sailor', 109.0, 83.5, '#7a8a9a',
               'Fifty years at sea, and I never saw a fountain as big as that one. Sit with me. The pigeons are good company, and they do not ask for money.',
               look_=look('#e0b48e', '#e8e8e8', 'bald', 'cap', None, '#e8e8e8', 1.0, '#44546a')),
        person('painter', 'Painter Lisbet', 'Painter', 30.0, 22.5, '#b070a0',
               'I have painted this garden eleven times and the light has never once been the same. Do not stand in front of the easel. Behind it, you may admire.',
               look_=look('#f0c8a6', '#3a2a22', 'long', 'cap', '#d8c8e0', None, 1.0, '#b070a0')),
        person('scribe', 'Scribe Tomas', 'Young scribe', 91.5, 41.5, '#8a8f6a',
               'Forty-one ledgers to copy before dusk, and the Archivist thinks I am slow. You are welcome to try copying a ledger with a pigeon on your head.',
               look_=look('#edc5a1', '#8a5a2a', 'short', None, None, None, 0.92)),
        person('innkeeper', 'Innkeeper Dagny', 'Innkeeper', 107.0, 98.5, '#c0804a',
               'The Gilded Lute has the best stew in Skaldholm and the worst floorboards. Rooms are five coins and fully restore you. Do not sing before the bard has finished.',
               INN_OFFERS, look_=look('#f0c8a6', '#b0502a', 'bun', None, '#e8d8b0')),
        person('acolyte', 'Acolyte Ivar', 'Cathedral acolyte', 67.0, 42.5, '#d8d0c0',
               'The candles are lit at dawn and snuffed at dusk, and in between I hold the ladder. Sister Liv says that is a sacred duty. My arms say otherwise.',
               look_=look('#edc5a1', '#6a4a30', 'short', 'hood', None, None, 1.0, '#d8d0c0')),
        person('apprentice', 'Smith’s apprentice Nils', 'Apprentice', 38.5, 95.0, '#8a7a6a',
               'I have been pumping this bellows since breakfast. The Master says I am learning patience. I am learning to hate bellows.',
               look_=look('#edc5a1', '#3a2a22', 'short', None, '#6a5040', None, 0.95)),
        person('drunk', 'Rolf the Merry', 'Regular at the Lute', 106.0, 105.0, '#a07a5a',
               'I am not drunk. The street is leaning, and I am only leaning back. Hic. Say, are you the one who walked all the way from the meadow? Buy that person an ale!',
               look_=look('#e8b890', '#8a4a2a', 'short', None, None, '#8a4a2a')),
        person('stable', 'Stable-hand Greta', 'Stable-hand', 124.0, 128.0, '#6a8a5a',
               'The horses were here before the city and they will be here after it. This one bites. That one kicks. You can pet the third, if you are fast.',
               look_=look('#edc5a1', '#7a5a2a', 'long', 'straw', None, None, 1.0, '#e6c870')),
        person('weaver', 'Weaver Astrid', 'Weaver', 30.0, 62.0, '#a05a8a',
               'Every house in the Lark Lane wears my wool. Not by choice: they all came back the second winter for more.',
               look_=look('#f0c8a6', '#555555', 'bun', None, '#d8b0c8')),
        person('lamp_boy', 'Lamplighter Kjell', 'Lamplighter', 69.0, 100.0, '#c8a84a',
               'Four hundred lamps in Skaldholm, and I light them every night. It takes till midnight, and by morning the first ones are out again. I should have been a baker.',
               look_=look('#edc5a1', '#8a5a2a', 'short', 'cap', None, None, 1.0, '#7a5a3c')),
    ]


# ---- walkers: each is a closed loop of waypoints ---------------------------------------------------------------------
def walkers(c):
    """`c` maps a few named places to coordinates (fountain centre, ring radius ...) chosen by the generator."""
    fx, fy, rr = c['fountain'][0], c['fountain'][1], c['kids_radius']
    import math
    circle = lambda r, k, a0=0.0: [(fx + r * math.cos(a0 + i * 2 * math.pi / k), fy + r * math.sin(a0 + i * 2 * math.pi / k)) for i in range(k)]
    out = []
    kid_ring = circle(rr, 16)
    kids = [('Lotta', 'Child', '#e6a0b4', look('#f0c8a6', '#c9a24a', 'long', None, None, None, .7)),
            ('Pelle', 'Child', '#7aa0d0', look('#edc5a1', '#8a5a2a', 'short', 'cap', None, None, .7, '#b04a4a')),
            ('Ebba', 'Child', '#d8c070', look('#f0c8a6', '#6a4a30', 'bun', None, None, None, .66)),
            ('Anton', 'Child', '#7ac090', look('#e0b48e', '#3a2a22', 'short', None, None, None, .72))]
    for i, (nm, role, col, lk) in enumerate(kids):
        out.append(person('kid_' + nm.lower(), nm, role, 0, 0, col,
                          ['Catch me if you can! Round and round the fountain!', 'My mum says do not splash. The fountain says otherwise.',
                           'I counted the jets. There are forty. Or thirty-nine. I keep losing count.', 'Have you seen the big stone by the gate? It glows when nobody is looking!'][i],
                          look_=lk, route=kid_ring, speed=3.0, pause=0.0, phase=i * 2.6))
    out.append(person('watch_avenue', 'Watchman Eskil', 'City watch', 0, 0, '#58708f',
                      'Everything quiet on the Grand Avenue. Everything is always quiet. I patrol it anyway, in case it gets ideas.',
                      look_=look('#d9a47e', '#3a2a22', 'short', 'helm', None, '#3a2a22', 1.0, '#a9b5c0'),
                      route=c['watch_avenue'], speed=1.6, pause=4.0, phase=0))
    out.append(person('watch_avenue2', 'Watchwoman Rakel', 'City watch', 0, 0, '#58708f',
                      'Left foot, right foot, look important. That is most of the job. The rest is telling tourists where the Cathedral is.',
                      look_=look('#f0c8a6', '#b0502a', 'bun', 'helm', None, None, 1.0, '#a9b5c0'),
                      route=c['watch_avenue'], speed=1.6, pause=4.0, phase=37))
    out.append(person('watch_trade', 'Watchman Torben', 'City watch', 0, 0, '#58708f',
                      'Pickpockets love market days. I love catching them. We have an understanding.',
                      look_=look('#e0b48e', '#555555', 'short', 'helm', None, '#555555', 1.0, '#a9b5c0'),
                      route=c['watch_trade'], speed=1.5, pause=5.0, phase=10))
    out.append(person('watch_wall', 'Wallwatch Aslak', 'Wall watch', 0, 0, '#58708f',
                      'I walk the wall from the Gate to the Gate, once an hour. The view is the same every time, but it is still a good view.',
                      look_=look('#edc5a1', '#8a5a2a', 'short', 'helm', None, None, 1.0, '#a9b5c0'),
                      route=c['watch_wall'], speed=1.4, pause=6.0, phase=20))
    out.append(person('couple_a', 'Merchant Ragna', 'Strolling merchant', 0, 0, '#b07090',
                      'A turn around the ring road before supper: the best medicine there is. Ask my husband. He is the one panting.',
                      look_=look('#f0c8a6', '#7a5a3c', 'long', 'bonnet', None, None, 1.0, '#c890a8'),
                      route=c['ring'], speed=1.0, pause=0.0, phase=0))
    out.append(person('couple_b', 'Merchant Leif', 'Strolling merchant', 0, 0, '#6a7a98',
                      'Slower, dear, slower. The ring road is not going anywhere. It is round.',
                      look_=look('#edc5a1', '#8a8a8a', 'short', 'cap', None, '#8a8a8a', 1.0, '#44546a'),
                      route=c['ring'], speed=1.0, pause=0.0, phase=1.9))
    out.append(person('courier', 'Courier Fia', 'Guild courier', 0, 0, '#d0a040',
                      'No time to talk, parcels to move! The guildhall to the archive and back, forty times a day.',
                      look_=look('#f0c8a6', '#c9a24a', 'short', 'cap', None, None, 0.95, '#d0a040'),
                      route=c['courier'], speed=2.6, pause=1.5, phase=5))
    out.append(person('peddler', 'Peddler Joss', 'Travelling peddler', 0, 0, '#9a7a52',
                      'Ribbons, buttons, lucky pebbles from the glacier! Everything is half price on days that end in a vowel.',
                      look_=look('#e0b48e', '#6a4a30', 'short', 'straw', None, '#6a4a30', 1.0, '#c8a860'),
                      route=c['trade_long'], speed=1.2, pause=8.0, phase=0))
    out.append(person('pilgrim', 'Pilgrim Ansgar', 'Pilgrim', 0, 0, '#8a7a6a',
                      'Three hundred miles on foot, and the Cathedral is, I am told, just up this road. I have been told that for an hour.',
                      look_=look('#d9a47e', '#cfcfcf', 'bald', 'hood', None, '#cfcfcf', 1.0, '#8a7a6a'),
                      route=c['pilgrim'], speed=1.1, pause=7.0, phase=3))
    out.append(person('apprentice_bard', 'Minstrel Pia', 'Bard’s apprentice', 0, 0, '#2f8a7a',
                      'La la la — oh! You heard that? I am practising. The Bard says I have a voice like a door in a gale.',
                      look_=look('#f0c8a6', '#b0502a', 'long', 'feather', None, None, 0.95, '#2f8a7a'),
                      route=c['minstrel'], speed=1.2, pause=6.0, phase=11))
    out.append(person('gardener', 'Gardener Olle', 'Gardener', 0, 0, '#5f8a62',
                      'The roses want water, the hedges want a trim and the roses want water again. Do not tell the roses I said so.',
                      look_=look('#e0b48e', '#7a5a3c', 'short', 'straw', '#6a8a5a', None, 1.0, '#e6c870'),
                      route=c['garden'], speed=1.0, pause=8.0, phase=0))
    return out


# ---- quests -----------------------------------------------------------------------------------------------------------
def talk_city(id, name):
    return dict(kind='talk', target=P + id, label='Speak to ' + name, count=1)


def talk_far(id, name, where):
    return dict(kind='talk', target=id, label=f'Speak to {name} ({where})', count=1)


def bring(item, count, label):
    return dict(kind='bring', target=item, label='Bring ' + label, count=count)


def quest(id, title, npc, description, objectives, level, gold, requires=None, repeatable=False):
    return dict(id=P + id, title=title, npc=P + npc, description=description, objectives=objectives, level=level,
                rewardXp=LEVEL_XP[level - 1] // 10, rewardGold=gold, requires=P + requires if requires else None,
                repeatable=repeatable)


def quests():
    return [
        quest('welcome', 'The Great Gate Opens', 'captain',
              'Captain Ingrid asks you to meet the people who keep Skaldholm running: Herald Bran, Archivist Fenwick, Guildmaster Tobias, Stonewarden Magnus and Sister Liv at the Cathedral. Then report back to her at the gate.',
              [talk_city('herald', 'Herald Bran'), talk_city('librarian', 'Archivist Fenwick'), talk_city('guildmaster', 'Guildmaster Tobias'),
               talk_city('stonewarden', 'Stonewarden Magnus'), talk_city('healer', 'Sister Liv')], 11, 260),
        quest('seals', 'Letters to the Four Hearths', 'herald',
              'Skaldholm has not written to its neighbours in a year. Bran’s sealed greetings are for four leaders: Captain Rowan in Alderhaven, Captain Sera in Cinderwatch Camp, Warden Halvard in Rimeward Camp and Reeve Osric in Lanternmere. Speak to each of them and return to Bran.',
              [talk_far('gatekeeper', 'Captain Rowan', 'Alderhaven, Greenmeadow'), talk_far('crags_captain', 'Captain Sera', 'Cinderwatch, Emberfall Crags'),
               talk_far('rime_warden', 'Warden Halvard', 'Rimeward Camp, Rimeveil Glacier'), talk_far('fen_reeve', 'Reeve Osric', 'Lanternmere, Gloamfen')],
              12, 520, 'welcome'),
        quest('gel', 'Clear Gel for Clear Heads', 'alchemist',
              'Orsolya’s tonics start with slime gel, and the city’s slimes are long gone. The meadow below the Crags is full of them: bring her eight Slime Gel and four Blue Slime Gel.',
              [bring('slime_gel', 8, 'Slime Gel'), bring('blue_gel', 4, 'Blue Slime Gel')], 12, 480, 'welcome'),
        quest('forge', 'Cinders for the Forge', 'smith',
              'Brunhild’s forge needs real fire. The Emberfall Crags have plenty: bring four Ember Cores from the wisps and three Magma Fangs from the spiders.',
              [bring('ember_core', 4, 'Ember Cores'), bring('magma_fang', 3, 'Magma Fangs')], 13, 560, 'welcome'),
        quest('pelts', 'Winter Cloaks for the Watch', 'guildmaster',
              'The winter watch freezes in their tabards. The glacier next door grows what the guild needs: four Frost Pelts from the wolves and two Yeti Horns for the clasps.',
              [bring('frost_pelt', 4, 'Frost Pelts'), bring('yeti_horn', 2, 'Yeti Horns')], 14, 620, 'welcome'),
        quest('hearths', 'The Song of Four Hearths', 'bard',
              'Eira wants one verse from each hearth: a word with Pip the baker in Alderhaven, Scout Kael in the Crags, Loremaster Ylva on the glacier and Ferryman Odd in the fen. Tell each of them that the bard sent you, then return to her.',
              [talk_far('baker', 'Pip the baker', 'Alderhaven, Greenmeadow'), talk_far('crags_scout', 'Scout Kael', 'Cinderwatch, Emberfall Crags'),
               talk_far('rime_loremaster', 'Loremaster Ylva', 'Rimeward Camp, Rimeveil Glacier'), talk_far('fen_ferryman', 'Ferryman Odd', 'Lanternmere, Gloamfen')],
              15, 640, 'welcome'),
        quest('marsh', 'Marsh Medicine', 'alchemist',
              'Orsolya has run out of gel and moved on to glands: four Fen Toad Glands and three Mire Crocodile Hides from Gloamfen make a salve nothing else can match.',
              [bring('toad_gland', 4, 'Fen Toad Glands'), bring('croc_hide', 3, 'Mire Crocodile Hides')], 17, 760, 'gel'),
        quest('archive', 'The Drowned Archive', 'librarian',
              'Fenwick has heard of a drowned fort in Gloamfen. Speak to Scholar Pell in Lanternmere about it, then bring back three Drowned Gauntlets as proof.',
              [talk_far('fen_scholar', 'Scholar Pell', 'Lanternmere, Gloamfen'), bring('drowned_gauntlet', 3, 'Drowned Gauntlets')], 18, 820, 'welcome'),
        quest('stone', 'Runes for the Meeting Stone', 'stonewarden',
              'Magnus says the stone’s runes are fading. Three rare things can wake them: two Hydra Fangs from the fen island, two Wyrm Scales from the glacier summit and two Basalt Hearts from the golems of the Crags.',
              [bring('hydra_fang', 2, 'Hydra Fangs'), bring('wyrm_scale', 2, 'Wyrm Scales'), bring('basalt_heart', 2, 'Basalt Hearts')], 20, 960, 'archive'),
        quest('tribute', 'Tribute of Four Lands', 'steward',
              'Halden wants the city’s tribute room filled: two Ironhide Shells from the meadow, two Ash Veils from the Crags, two Rime Shells from the glacier and two Mire Crocodile Hides from the fen. Every land, one gift.',
              [bring('ironhide_shell', 2, 'Ironhide Shells'), bring('ash_veil', 2, 'Ash Veils'), bring('rime_shell', 2, 'Rime Shells'), bring('croc_hide', 2, 'Mire Crocodile Hides')],
              20, 1100, 'stone'),
        quest('order', 'The Guild’s Standing Order', 'guildmaster',
              'The guild always needs Magma Fangs and Rime Shells for its export crates. Bring three of each; Tobias will pay again every time you do. Repeatable.',
              [bring('magma_fang', 3, 'Magma Fangs'), bring('rime_shell', 3, 'Rime Shells')], 14, 540, 'welcome', True),
    ] + progression_quests.for_zone('Skaldholm')
