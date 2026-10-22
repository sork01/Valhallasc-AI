"""Builds the level 1–85 gear ladder and exclusive Undervault/Cathedral sets in world/items.txt.

Run `python3 scripts/gear_levels.py`, then `node scripts/sync-world.cjs` and rebuild Rust. It is idempotent: it keeps
every non-gear item and every original piece (an entry with no `art` key) and regenerates the rest.

SETS. Required levels come in steps of five (1, 5, ... 85). Every level has a gray, a green and a blue set; purple
exists at every multiple of ten. A set holds, per class, a chest, headgear, shoulders,
gloves and weapon, plus the shared (class-independent) pants, necklace and ring.

ART. No new art is drawn. A generated piece names the original piece it recolours (`art`: the original's variant) and
a `tint` (CSS-filter terms: hue-rotate degrees, saturate, brightness) that the client applies to the worn layers and
the inventory icon. Gray and blue sets use the class's first drawing, green and purple the second.
The originals sit in the cells they already had: starters are the level 1 gray set, the second drawings the level 1
green set, and the three shared pants/necklace/ring pieces keep their level-5-green / level-20-blue / level-20-purple
cells. The three shared headgear/shoulders/gloves pieces are extras outside the sets.

STATS follow WoW's tiers. Gray has no stat budget: only base armor (defense) or weapon damage (attack). Green keeps
that base and adds a secondary stat; blue is 17.5% over green, purple 17.5% over blue, orange 17.5% over purple. Each
level factor follows the existing linear ladder (0.16 per level after level 5).
"""
import json
import hashlib
import pathlib
from cathedral_content import WINGS

ROOT = pathlib.Path(__file__).resolve().parents[1]
ITEMS = ROOT / 'world' / 'items.txt'

LEVELS = (1, *range(5, 96, 5))
RARITIES = ['common', 'uncommon', 'rare', 'epic']       # gray, green, blue, purple
COLOUR = {'common': 'gray', 'uncommon': 'green', 'rare': 'blue', 'epic': 'purple'}
SETS = [(level, rarity) for level in LEVELS for rarity in RARITIES if rarity != 'epic' or level % 10 == 0]
LEVEL_FACTOR = {level: 1.0 if level == 1 else round(0.16 * level + 0.8, 1) for level in LEVELS}
TIER_STEP = 1.175
GREEN_BUDGET = 1.25
SECONDARY_SHARE = 0.2
RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary']
USEFUL_STATS = {
    'warrior': ('strength', 'stamina', 'agility', 'accuracy', 'dexterity'),
    'mage': ('intellect', 'stamina', 'agility', 'accuracy', 'dexterity'),
    'assassin': ('agility', 'stamina', 'strength', 'accuracy', 'dexterity'),
    'priest': ('intellect', 'stamina', 'agility', 'accuracy', 'dexterity'),
    'hunter': ('agility', 'stamina', 'strength', 'accuracy', 'dexterity'),
    None: ('stamina', 'accuracy', 'dexterity'),
}
# Item levels arrive in five-level steps. The levels after 50 extend the requested
# 50→90 rise linearly (rounded to whole points).
ATTRIBUTE_BONUS = {
    5: 1, 10: 3, 15: 5, 20: 7, 25: 10, 30: 15, 35: 20,
    40: 30, 45: 35, 50: 40, 55: 48, 60: 55, 65: 63,
    70: 70, 75: 78, 80: 85, 85: 93, 90: 100, 95: 108,
}


def bonus_choices(cls, amount):
    """Keep large rolls off hit/dodge attributes once a single item would exceed their caps."""
    choices = [stat for stat in USEFUL_STATS[cls]
               if (stat != 'accuracy' or amount <= 20) and (stat != 'dexterity' or amount <= 70)]
    if cls is None and amount > 70:
        choices.extend(('strength', 'agility'))   # useful to every class, unlike capped hit/dodge
    return choices
SELL_BASE = {'common': 4, 'uncommon': 25, 'rare': 60, 'epic': 120}

# (primary stat, base budget at level 1) per slot kind; the secondary stat is the other one.
SLOT_BASE = {
    'weapon': ('attack', 4.0),
    'headgear': ('defense', 1.0),
    'shoulders': ('defense', 1.0),
    'gloves': ('defense', 1.0),
    'pants': ('defense', 1.0),
    'necklace': ('attack', 2.0),
    'accessory': ('attack', 1.5),
}
CHEST_BASE = {'warrior': 3.0, 'mage': 2.0, 'assassin': 2.0, 'priest': 3.0, 'hunter': 3.0}
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
CLASS_KINDS = ('armor', 'headgear', 'shoulders', 'gloves', 'weapon')
SHARED_KINDS = ('pants', 'necklace', 'accessory')

# Where the original shared pieces sit, and the extras that belong to no set.
SHARED_CELLS = {'pants_upgrade': (5, 'uncommon'), 'necklace_upgrade': (20, 'rare'), 'accessory_upgrade': (20, 'epic')}
EXTRAS = {'headgear_upgrade': (15, 'rare'), 'shoulders_upgrade': (15, 'uncommon'), 'gloves_upgrade': (10, 'uncommon')}

# A name word per set; the two original cells keep their own names.
WORDS = {
    (1, 'rare'): 'Tempered',
    (5, 'common'): 'Weathered', (5, 'uncommon'): 'Hardened', (5, 'rare'): 'Gilded',
    (10, 'common'): 'Battered', (10, 'uncommon'): 'Reinforced', (10, 'rare'): 'Runed', (10, 'epic'): 'Exalted',
    (15, 'common'): 'Faded', (15, 'uncommon'): 'Veteran', (15, 'rare'): 'Radiant',
    (20, 'common'): 'Ancient', (20, 'uncommon'): 'Heroic', (20, 'rare'): 'Celestial', (20, 'epic'): 'Mythic',
    (25, 'common'): 'Brambleworn', (25, 'uncommon'): 'Thornforged', (25, 'rare'): 'Wyrdbound',
    (30, 'common'): 'Windworn', (30, 'uncommon'): 'Galesworn', (30, 'rare'): 'Prismatic', (30, 'epic'): 'Stormcrowned',
    (35, 'common'): 'Saltworn', (35, 'uncommon'): 'Tideforged', (35, 'rare'): 'Maelstrom',
    (40, 'common'): 'Drowned', (40, 'uncommon'): 'Pearlbound', (40, 'rare'): 'Nacreous', (40, 'epic'): 'Tidesovereign',
    (45, 'common'): 'Coralworn', (45, 'uncommon'): 'Reefguard', (45, 'rare'): 'Abyssal',
    (50, 'common'): 'Timeworn', (50, 'uncommon'): 'Starforged', (50, 'rare'): 'Empyrean', (50, 'epic'): 'Ascendant',
    (55, 'common'): 'Clockworn', (55, 'uncommon'): 'Hourforged', (55, 'rare'): 'Epochbound',
    (60, 'common'): 'Sporeworn', (60, 'uncommon'): 'Moonwoven', (60, 'rare'): 'Nightbloom', (60, 'epic'): 'Mooncrowned',
    (65, 'common'): 'Saltworn', (65, 'uncommon'): 'Stormforged', (65, 'rare'): 'Eye-bound',
    (70, 'common'): 'Fieldworn', (70, 'uncommon'): 'Oakbound', (70, 'rare'): 'Sunward', (70, 'epic'): 'Elder-crowned',
    (75, 'common'): 'Paradeworn', (75, 'uncommon'): 'Ribbonbound', (75, 'rare'): 'Jubilee',
    (80, 'common'): 'Rootworn', (80, 'uncommon'): 'Canopybound', (80, 'rare'): 'Raincrowned', (80, 'epic'): 'Jade Sovereign',
    (85, 'common'): 'Sandworn', (85, 'uncommon'): 'Oasisbound', (85, 'rare'): 'Astrolabe',
    (90, 'common'): 'Snowworn', (90, 'uncommon'): 'Riftforged', (90, 'rare'): 'Aurorabound', (90, 'epic'): 'Glacier Sovereign',
    (95, 'common'): 'Stoneworn', (95, 'uncommon'): 'Cairnforged', (95, 'rare'): 'Thunderbound',
}
LEVEL_HUE = {level: (index * 70) % 360 for index, level in enumerate(LEVELS)}
RARITY_TINT = {   # hue offset, saturate, brightness
    'common': (0, 0.5, 0.9), 'uncommon': (0, 1.0, 1.0), 'rare': (30, 1.15, 1.1), 'epic': (60, 1.2, 1.15),
}


def tint(level, rarity, shared=False):
    """Hue turns with the level and the tier. Shared pieces turn 20 more degrees, so none is the untouched original
    (the level 1 green set would be, and the original shared pieces sit in other cells)."""
    offset, saturate, brightness = RARITY_TINT[rarity]
    hue = (LEVEL_HUE[level] + offset + (20 if shared else 0)) % 360
    # The hue wheel wraps at level 50 for shared green pieces; keep every generated piece distinct from its base.
    if hue == 0 and saturate == brightness == 1:
        hue = 5
    return {'hue': hue, 'saturate': saturate, 'brightness': brightness}


def budget(kind, cls, rarity, level):
    """(attack, defense) for a piece; the formula the Rust test checks the catalog against."""
    stat, base = SLOT_BASE.get(kind, ('defense', CHEST_BASE.get(cls, 3.0)))
    total = base * LEVEL_FACTOR[level]
    tier = RARITY_ORDER.index(rarity)
    if tier == 0:
        values = {'attack': 0.0, 'defense': 0.0}
        values[stat] = total
    else:
        total *= GREEN_BUDGET * TIER_STEP ** (tier - 1)
        other = 'defense' if stat == 'attack' else 'attack'
        values = {stat: total * (1 - SECONDARY_SHARE), other: total * SECONDARY_SHARE}
    return round(values['attack'], 1), round(values['defense'], 1)


def bonus_stats(i):
    """One useful attribute on blue, two different ones on purple, fixed by item ID.

    Attribute amounts follow the requested level ladder, while the existing
    17.5% attack/defense tier increase remains intact. Shared gear only rolls
    universally useful stats.
    """
    count = {'rare': 1, 'epic': 2}.get(i['rarity'], 0)
    digest = hashlib.sha256(i['id'].encode()).digest()
    step = min(95, max(5, i.get('requiredLevel', 1) // 5 * 5))
    amount = ATTRIBUTE_BONUS[step]
    choices = bonus_choices(i.get('class'), amount)
    return {choices.pop(digest[n] % len(choices)): amount for n in range(count)}


def ordered(i):
    keys = ['id', 'name', 'kind', 'rarity', 'requiredLevel']
    return {**{k: i[k] for k in keys if k in i}, **{k: v for k, v in i.items() if k not in keys}}


def finish(i, level, rarity):
    i['rarity'] = rarity
    i['requiredLevel'] = level
    i['sell'] = 0 if i.get('starter') else round(SELL_BASE[rarity] * LEVEL_FACTOR[level])
    i['attack'], i['defense'] = budget(i['kind'], i.get('class'), rarity, level)
    i.pop('bonusStats', None)
    if bonus := bonus_stats(i):
        i['bonusStats'] = bonus
    return ordered(i)


def main():
    existing = json.loads(ITEMS.read_text())
    items = [i for i in existing if 'art' not in i or i.get('source') in ('orange_pool', 'chained_forge_packs')]
    gear = {'armor', 'weapon', 'headgear', 'shoulders', 'gloves', 'pants', 'necklace', 'accessory'}
    out, bases = [], {}
    for i in items:
        if i['kind'] not in gear or i['rarity'] == 'gm' or i.get('source') in ('orange_pool', 'chained_forge_packs'):
            out.append(i)
            continue
        if i.get('starter'):
            cell = (1, 'common')
        elif i['id'] in SHARED_CELLS:
            cell = SHARED_CELLS[i['id']]
        elif i['id'] in EXTRAS:
            cell = EXTRAS[i['id']]
        else:
            cell = (1, 'uncommon')       # the second drawing of a class slot
        out.append(finish(i, *cell))
        bases[(i.get('class'), i['kind'], cell)] = i
    for level, rarity in SETS:
        for cls in CLASSES:
            for kind in CLASS_KINDS:
                add(out, bases, cls, kind, level, rarity)
        for kind in SHARED_KINDS:
            add(out, bases, None, kind, level, rarity)
    out = [i for i in out if i['kind'] != 'cloak' or i.get('source') == 'orange_pool']
    out.extend(vault_pieces(out))
    out.extend(cathedral_pieces(out))
    out.extend(moonwell_pieces(out))
    out.extend(eye_below_pieces(out))
    out.extend(nornroot_pieces(out))
    out.extend(longship_pieces(out))
    out.extend(blackhour_pieces(out))
    out.extend(skybridge_pieces(out))
    out.extend(elder_hollow_pieces(out))
    out.extend(thousandfold_pieces(out))
    out.extend(rain_crown_pieces(out))
    out.extend(seed_vault_pieces(out))
    out.extend(sunken_astrolabe_pieces(out))
    out.extend(dungeon_pieces(out, 'thunderheart_gate', 'thunder', 'Stormbound', {'hue':205,'saturate':1.3,'brightness':1.2}))
    out.extend(dungeon_pieces(out, 'blooming_labyrinth', 'bloom', 'Glassbloom', {'hue':315,'saturate':1.28,'brightness':1.18}))
    out.extend(dungeon_pieces(out, 'solar_crucible', 'solar', 'Sunforged', {'hue':34,'saturate':1.35,'brightness':1.22}))
    out.extend(dungeon_pieces(out, 'amber_archive', 'amber', 'Archivist', {'hue':42,'saturate':1.22,'brightness':1.18}))
    out.extend(dungeon_pieces(out, 'silent_solstice', 'solstice', 'Nightglass', {'hue':207,'saturate':1.2,'brightness':1.23}))
    import cloak_catalog
    out = cloak_catalog.apply(out)
    # Keep existing catalog order stable: migrations, item-icon cells and reviews need no reshuffle.
    order = {i['id']: n for n, i in enumerate(existing)}
    out.sort(key=lambda i: order.get(i['id'], len(order)))
    # Redesigned pieces are wired one at a time; rarity recolors the new base for that level.
    import gear_art_catalog
    gear_art_catalog.apply(out)
    ITEMS.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(len(out), 'items,', len(SETS), 'sets')


# Cathedral rewards use the wing's exact level, with the Undervault's 15% dungeon bonus.
# A source locks each set to its own wing's bosses; every slot (including necklaces) has a reward.
CATHEDRAL_BONUS = 1.15
CATHEDRAL_TINTS = {
    'cloister': {'hue': 175, 'saturate': 0.85, 'brightness': 1.18},
    'reliquary': {'hue': 325, 'saturate': 1.1, 'brightness': 1.23},
    'nave': {'hue': 245, 'saturate': 1.35, 'brightness': 1.05},
}
CATHEDRAL_NAMES = {
    'cloister': ('Stillwater', 'Kelpweaver', 'Drowned Whisper', 'Bound Choir', 'Tidereed'),
    'reliquary': ('Coralguard', 'Pearlweaver', 'Glassveil', 'Pearl Cantor', 'Reefstalker'),
    'nave': ('Abyssal Oath', 'Drowned Star', 'Nighttide', 'Freed Choir', 'Voidwatcher'),
}
CATHEDRAL_WEAPONS = {
    'cloister': ('Bellkeeper Sword & Shield', 'Stillwater Staff', 'Kelpglass Daggers', 'Bound Choir Mace', 'Tidereed Bow'),
    'reliquary': ('Coral Regent Sword & Shield', 'Shattered Pearl Staff', 'Pearl Widow Fangs', 'Reliquary Mace', 'Coralspine Bow'),
    'nave': ('Judicator Sword & Shield', 'Drowned Star Staff', 'Nighttide Daggers', 'Heart of the Tide Mace', 'Seraph Bow'),
}
CATHEDRAL_SHARED = {
    'cloister': ('Stillwater Waders', 'Bellkeeper Pendant', 'Bound Choir Signet'),
    'reliquary': ('Coralguard Leggings', 'Pearl Widow Pendant', 'Coral Regent Signet'),
    'nave': ('Abyssal Procession Leggings', 'Heart of the Tide Pendant', 'Hierophant Signet'),
}
SLOT_NAMES = {'armor': 'Vestments', 'headgear': 'Crown', 'shoulders': 'Mantle', 'gloves': 'Grips'}


def cathedral_pieces(out):
    pieces = []
    for wing in WINGS:
        level, name = wing['level'], wing['id']
        for i in out:
            if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != level:
                continue
            if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
                continue
            v = dict(i)
            suffix = f'_l{level}_blue'
            assert i['id'].endswith(suffix), i['id']
            v['id'] = i['id'][:-len(suffix)] + f'_l{level}_{name}'
            v['variant'] = i['variant'][:-len(suffix)] + f'_l{level}_{name}'
            if i.get('class'):
                c = CLASSES.index(i['class'])
                v['name'] = (CATHEDRAL_WEAPONS[name][c] if i['kind'] == 'weapon'
                             else f"{CATHEDRAL_NAMES[name][c]} {SLOT_NAMES[i['kind']]}")
            else:
                v['name'] = CATHEDRAL_SHARED[name][SHARED_KINDS.index(i['kind'])]
            v['tint'] = dict(CATHEDRAL_TINTS[name])
            v['attack'] = round(i['attack'] * CATHEDRAL_BONUS, 1)
            v['defense'] = round(i['defense'] * CATHEDRAL_BONUS, 1)
            v['sell'] = round(i['sell'] * CATHEDRAL_BONUS)
            v['source'] = f'cathedral_{name}'
            v['bonusStats'] = bonus_stats(v)
            pieces.append(ordered(v))
    return pieces


# Moonwell's exclusive blue catalog is defined here; its new worn art and the
# boss-source switch are separate tasks. The placeholder uses level-60 base art.
MOONWELL_BONUS = 1.15
MOONWELL_NAMES = {
    'warrior': 'Tideglass', 'mage': 'Hourpetal', 'assassin': 'Moonskein',
    'priest': 'Stillwater', 'hunter': 'Silvercurrent',
}
MOONWELL_WEAPONS = {
    'warrior': 'Tideglass Sword', 'mage': 'Hourpetal Staff',
    'assassin': 'Moonskein Daggers', 'priest': 'Stillwater Mace',
    'hunter': 'Silvercurrent Bow',
}
MOONWELL_SHARED = {'pants': 'Moonwell Waders', 'necklace': 'Lunar Tide Pendant',
                   'accessory': 'Echo Signet'}


def moonwell_pieces(out):
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 60:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l60_blue'
        assert i['id'].endswith(suffix), i['id']
        v['id'] = i['id'][:-len(suffix)] + '_l60_moonwell'
        v['variant'] = i['variant'][:-len(suffix)] + '_l60_moonwell'
        cls = i.get('class')
        v['name'] = (MOONWELL_WEAPONS[cls] if i['kind'] == 'weapon' else
                     f"{MOONWELL_NAMES[cls]} {SLOT_NAMES[i['kind']]}") if cls else MOONWELL_SHARED[i['kind']]
        v['attack'] = round(i['attack'] * MOONWELL_BONUS, 1)
        v['defense'] = round(i['defense'] * MOONWELL_BONUS, 1)
        v['sell'] = round(i['sell'] * MOONWELL_BONUS)
        v['source'] = 'moonwell'
        v['tint'] = {'hue': 165, 'saturate': 1.15, 'brightness': 1.17}
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def blackhour_pieces(out):
    """Original level-99 epic set, using the existing rarity curve and dungeon bonus."""
    pieces=[]
    titles={'warrior':'Shiftbreaker','mage':'Voidcoil','assassin':'Ratchetshade','priest':'Deadlight','hunter':'Induction'}
    weapons={'warrior':'Nullforged Split-Tooth Greatblade','mage':'Nullforged Open-Coil Staff',
             'assassin':'Nullforged Twin Ratchet Sickles','priest':'Nullforged Black Censer',
             'hunter':'Nullforged Forked Induction Bow'}
    shared={'pants':'Nullforged Furnace Greaves','necklace':'Nullforged Missing-Hour Pendant','accessory':'Nullforged Hollow-Axle Signet'}
    for i in out:
        if i.get('source') or i['rarity']!='rare' or i.get('requiredLevel')!=95 or i['kind'] not in CLASS_KINDS+SHARED_KINDS:continue
        cls,kind=i.get('class'),i['kind'];v=dict(i)
        v.update(id='null_'+(cls+'_' if cls else '')+kind,variant=i['variant'][:-len('_l95_blue')]+'_l99_null',
                 requiredLevel=99,rarity='epic',source='blackhour',art='regearnull',starter=False)
        v['name']=(weapons[cls] if kind=='weapon' else 'Nullforged '+titles[cls]+' '+SLOT_NAMES[kind]) if cls else shared[kind]
        # Blue L95 -> purple, then L99's same linear budget and the 15% dungeon bonus.
        scale=TIER_STEP*((.16*99+.8)/LEVEL_FACTOR[95])*1.15
        for key in ('attack','defense'):v[key]=round(i[key]*scale,1)
        v['sell']=round(i['sell']*2*1.15);v.pop('tint',None);v['bonusStats']=bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces)==28
    return pieces


def longship_pieces(out):
    """28 bespoke Keelbound pieces, original geometry/palette, existing L35 blue budgets +15%."""
    pieces=[]
    prefixes={'warrior':'Copperwake','mage':'Wheelkeeper','assassin':'Brinehook','priest':'Bellwatch','hunter':'Harpooner'}
    weapons={'warrior':'Keelbound Boarding Cutlass','mage':'Keelbound Wheelstaff','assassin':'Keelbound Boarding Hooks','priest':'Keelbound Diving Bell','hunter':'Keelbound Harpoon Bow'}
    shared={'pants':'Keelbound Rope Gaiters','necklace':'Keelbound Anchor Pendant','accessory':'Keelbound Porthole Ring'}
    for i in out:
        if i.get('source') or i['rarity']!='rare' or i.get('requiredLevel')!=35 or i['kind'] not in CLASS_KINDS+SHARED_KINDS: continue
        v=dict(i);suffix='_l35_blue'
        for key in ('id','variant'):
            assert v[key].endswith(suffix);v[key]=v[key][:-len(suffix)]+'_l35_keel'
        cls=i.get('class');kind=i['kind']
        v['name']=(weapons[cls] if kind=='weapon' else 'Keelbound '+prefixes[cls]+' '+SLOT_NAMES[kind]) if cls else shared[kind]
        for key in ('attack','defense'):v[key]=round(i[key]*1.15,1)
        v['sell']=round(i['sell']*1.15);v['source']='longship';v['art']='regearkeel';v.pop('tint',None);v['bonusStats']=bonus_stats(v);pieces.append(ordered(v))
    assert len(pieces)==28
    return pieces


def nornroot_pieces(out):
    """Exclusive 28-piece level-25 blue set, 15% above the ordinary ladder."""
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 25:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l25_blue'
        assert v['id'].endswith(suffix), v['id']
        for key in ['id', 'variant']:
            v[key] = v[key][:-len(suffix)] + '_l25_norn'
        v['name'] = 'Fatewoven ' + i['name'].split(' ', 1)[-1]
        v['attack'] = round(i['attack'] * 1.15, 1)
        v['defense'] = round(i['defense'] * 1.15, 1)
        v['sell'] = round(i['sell'] * 1.15)
        v['source'] = 'nornroot'
        # Fatewoven has original fitted geometry and its own painted palette.
        # Keep existing item IDs, variants and combat budgets for saved gear.
        v['art'] = 'fatewoven'
        v.pop('tint', None)
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def skybridge_pieces(out):
    """Exclusive 28-piece level-30 blue set, 15% above the ordinary ladder."""
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 30:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l30_blue'
        assert v['id'].endswith(suffix), v['id']
        for key in ['id', 'variant']:
            v[key] = v[key][:-len(suffix)] + '_l30_span'
        v['name'] = 'Bridgeward ' + i['name'].split(' ', 1)[-1]
        v['attack'] = round(i['attack'] * 1.15, 1)
        v['defense'] = round(i['defense'] * 1.15, 1)
        v['sell'] = round(i['sell'] * 1.15)
        v['source'] = 'skybridge'
        v['tint'] = {'hue': 195, 'saturate': 1.24, 'brightness': 1.15}
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def eye_below_pieces(out):
    """A level-65 blue set reserved for the three Eye Below bosses."""
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 65:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l65_blue'
        assert i['id'].endswith(suffix), i['id']
        v['id'] = i['id'][:-len(suffix)] + '_l65_eye'
        v['variant'] = i['variant'][:-len(suffix)] + '_l65_eye'
        v['name'] = 'Deepglass ' + i['name'].split(' ', 1)[-1]
        v['attack'] = round(i['attack'] * 1.15, 1)
        v['defense'] = round(i['defense'] * 1.15, 1)
        v['sell'] = round(i['sell'] * 1.15)
        v['source'] = 'eye_below'
        v['tint'] = {'hue': 190, 'saturate': 1.25, 'brightness': 1.12}
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def elder_hollow_pieces(out):
    """A level-70 rare set reserved for the Elder Hollow bosses."""
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 70:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l70_blue'
        assert i['id'].endswith(suffix), i['id']
        v['id'] = i['id'][:-len(suffix)] + '_l70_elder'
        v['variant'] = i['variant'][:-len(suffix)] + '_l70_elder'
        v['name'] = 'Oakheart ' + i['name'].split(' ', 1)[-1]
        v['attack'] = round(i['attack'] * 1.15, 1)
        v['defense'] = round(i['defense'] * 1.15, 1)
        v['sell'] = round(i['sell'] * 1.15)
        v['source'] = 'elder_hollow'
        v['tint'] = {'hue': 105, 'saturate': 1.17, 'brightness': 1.12}
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def thousandfold_pieces(out):
    """A level-75 rare set reserved for the Pavilion bosses."""
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 75:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l75_blue'
        assert i['id'].endswith(suffix), i['id']
        v['id'] = i['id'][:-len(suffix)] + '_l75_pavilion'
        v['variant'] = i['variant'][:-len(suffix)] + '_l75_pavilion'
        v['name'] = 'Thousandfold ' + i['name'].split(' ', 1)[-1]
        v['attack'] = round(i['attack'] * 1.15, 1)
        v['defense'] = round(i['defense'] * 1.15, 1)
        v['sell'] = round(i['sell'] * 1.15)
        v['source'] = 'thousandfold'
        v['tint'] = {'hue': 305, 'saturate': 1.18, 'brightness': 1.12}
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def rain_crown_pieces(out):
    """A level-80 rare set reserved for the Rain Crown's three bosses."""
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 80:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l80_blue'
        assert i['id'].endswith(suffix), i['id']
        v['id'] = i['id'][:-len(suffix)] + '_l80_rain'
        v['variant'] = i['variant'][:-len(suffix)] + '_l80_rain'
        v['name'] = 'Rainbound ' + i['name'].split(' ', 1)[-1]
        v['attack'] = round(i['attack'] * 1.15, 1)
        v['defense'] = round(i['defense'] * 1.15, 1)
        v['sell'] = round(i['sell'] * 1.15)
        v['source'] = 'rain_crown'
        v['tint'] = {'hue': 145, 'saturate': 1.22, 'brightness': 1.15}
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def seed_vault_pieces(out):
    """A level-80 rare set reserved for the Seed Vault bosses."""
    pieces = []
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 80:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v = dict(i)
        suffix = '_l80_blue'
        assert i['id'].endswith(suffix), i['id']
        v['id'] = i['id'][:-len(suffix)] + '_l80_seed'
        v['variant'] = i['variant'][:-len(suffix)] + '_l80_seed'
        v['name'] = 'Worldseed ' + i['name'].split(' ', 1)[-1]
        v['attack'] = round(i['attack'] * 1.15, 1)
        v['defense'] = round(i['defense'] * 1.15, 1)
        v['sell'] = round(i['sell'] * 1.15)
        v['source'] = 'seed_vault'
        v['tint'] = {'hue': 85, 'saturate': 1.25, 'brightness': 1.16}
        v['bonusStats'] = bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces) == 28
    return pieces


def sunken_astrolabe_pieces(out):
    # Level-85 rare gear reserved for the Sunken Astrolabe bosses.
    pieces=[]
    for i in out:
        if i.get('source') or i['rarity'] != 'rare' or i.get('requiredLevel') != 85:
            continue
        if i['kind'] not in CLASS_KINDS + SHARED_KINDS:
            continue
        v=dict(i);suffix='_l85_blue'
        assert i['id'].endswith(suffix),i['id']
        v['id']=i['id'][:-len(suffix)]+'_l85_astro'
        v['variant']=i['variant'][:-len(suffix)]+'_l85_astro'
        v['name']='Meridian '+i['name'].split(' ',1)[-1]
        v['attack']=round(i['attack']*1.15,1)
        v['defense']=round(i['defense']*1.15,1)
        v['sell']=round(i['sell']*1.15)
        v['source']='sunken_astrolabe'
        v['tint']={'hue':202,'saturate':1.27,'brightness':1.17}
        v['bonusStats']=bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces)==28
    return pieces


def dungeon_pieces(out, source, suffix_name, prefix, tint):
    """Exclusive level-95 set for the late private dungeons."""
    pieces=[]
    for i in out:
        if i.get('source') or i['rarity']!='rare' or i.get('requiredLevel')!=95:
            continue
        if i['kind'] not in CLASS_KINDS+SHARED_KINDS:
            continue
        v=dict(i);suffix='_l95_blue'
        assert i['id'].endswith(suffix),i['id']
        v['id']=i['id'][:-len(suffix)]+'_l95_'+suffix_name
        v['variant']=i['variant'][:-len(suffix)]+'_l95_'+suffix_name
        v['name']=prefix+' '+i['name'].split(' ',1)[-1]
        v['attack']=round(i['attack']*1.15,1)
        v['defense']=round(i['defense']*1.15,1)
        v['sell']=round(i['sell']*1.15)
        v['source']=source;v['tint']=tint;v['bonusStats']=bonus_stats(v)
        pieces.append(ordered(v))
    assert len(pieces)==28,(source,len(pieces))
    return pieces


# The Undervault's own gear: a recolour of every level-20 blue piece the dungeon's bosses can drop (see items::boss_slots),
# 15% stronger, never part of the ordinary drop pool (`source` marks it; only the bosses hand it out).
VAULT_BONUS = 1.15
VAULT_SLOTS = ('armor', 'headgear', 'shoulders', 'gloves', 'weapon', 'pants', 'accessory')
VAULT_TINT = {'hue': 150, 'saturate': 1.3, 'brightness': 1.2}
# The recolour is a different piece, so it has its own name (the verdigris-green look, the vault's bones and wardens).
VAULT_NAMES = {
    'warrior_armor': 'Hollowsteel Cuirass', 'warrior_headgear': 'Hollowsteel Plumed Helm', 'warrior_shoulders': 'Hollowsteel Pauldrons',
    'warrior_gloves': 'Hollowsteel Gauntlets', 'warrior_weapon': 'Verdigris Greatsword',
    'mage_armor': 'Wardweaver Robes', 'mage_headgear': "Wardweaver's Hat", 'mage_shoulders': "Wardweaver's Capelet",
    'mage_gloves': "Wardweaver's Gloves", 'mage_weapon': 'Wraithwood Staff',
    'assassin_armor': 'Gravewalker Armor', 'assassin_headgear': 'Gravewalker Brow Band', 'assassin_shoulders': 'Gravewalker Spaulders',
    'assassin_gloves': 'Gravewalker Claws', 'assassin_weapon': 'Boneglass Daggers',
    'priest_armor': 'Choirbound Robes', 'priest_headgear': "Choirbound Hood", 'priest_shoulders': 'Choirbound Mantle',
    'priest_gloves': 'Choirbound Mitts', 'priest_weapon': 'Choirbound Mace',
    'hunter_armor': 'Boneshot Jerkin', 'hunter_headgear': 'Boneshot Headband', 'hunter_shoulders': 'Boneshot Mantle',
    'hunter_gloves': 'Boneshot Bracers', 'hunter_weapon': 'Boneshot Shortbow',
    'pants': 'Vaultwalker Pants', 'accessory': 'Verdigris Ring',
}


def vault_pieces(out):
    pieces = []
    for i in out:
        if i.get('rarity') == 'rare' and i.get('requiredLevel') == 20 and i['id'].endswith('_l20_blue') and i['kind'] in VAULT_SLOTS:
            v = dict(i)
            v['id'] = i['id'][:-len('_l20_blue')] + '_l20_vault'
            v['name'] = VAULT_NAMES[f"{i['class']}_{i['kind']}" if i.get('class') else i['kind']]
            v['variant'] = i['variant'][:-len('_l20_blue')] + '_l20_vault'
            v['tint'] = dict(VAULT_TINT)
            v['attack'] = round(i['attack'] * VAULT_BONUS, 1)
            v['defense'] = round(i['defense'] * VAULT_BONUS, 1)
            v['sell'] = round(i['sell'] * VAULT_BONUS)
            v['source'] = 'undervault'
            v['bonusStats'] = bonus_stats(v)
            pieces.append(ordered(v))
    # The original level-20 blue necklace has no generated _l20_blue ID. Give
    # Undervault a real eighth kind while reusing the Moonstone worn art/icon.
    base = next(i for i in out if i['id'] == 'necklace_upgrade')
    pendant = dict(base)
    pendant.update(id='necklace_moonstone_l20_vault', name='Choirbone Pendant',
                   variant='moonstone_l20_vault', art=base['variant'], tint=dict(VAULT_TINT),
                   attack=round(base['attack'] * VAULT_BONUS, 1),
                   defense=round(base['defense'] * VAULT_BONUS, 1),
                   sell=round(base['sell'] * VAULT_BONUS), source='undervault')
    pendant['bonusStats'] = bonus_stats(pendant)
    pieces.append(ordered(pendant))
    return pieces


def add(out, bases, cls, kind, level, rarity):
    cell = (level, rarity)
    if (cls, kind, cell) in bases:
        return
    if cls is None:
        base = next(b for (c, k, _), b in bases.items() if c is None and k == kind)
    else:
        # Gray and blue wear the class's first drawing (the starter); green and purple the second.
        first = rarity in ('common', 'rare')
        base = bases[(cls, kind, (1, 'common') if first else (1, 'uncommon'))]
    art = base['variant']
    variant = f"{art}_l{level}_{COLOUR[rarity]}"
    prefix = f"{cls}_" if cls else ''
    words = {**WORDS, (1, 'common'): 'Plain', (1, 'uncommon'): 'Sturdy'} if cls is None else WORDS
    name = f"{words[cell]} {base['name']}" if cell in words else base['name']
    i = {'id': f"{prefix}{kind}_{variant}", 'name': name, 'kind': kind, 'rarity': rarity, 'sell': 0}
    if cls:
        i['class'] = cls
    i['variant'] = variant
    i['art'] = art
    i['tint'] = tint(level, rarity, cls is None)
    i['starter'] = False
    out.append(finish(i, level, rarity))


def vault_only():
    """Regenerates just the Undervault pieces in the existing catalog (leaves every other item untouched, byte for byte)."""
    existing = json.loads(ITEMS.read_text())
    items = [i for i in existing if i.get('source') != 'undervault']
    items.extend(vault_pieces(items))
    import cloak_catalog
    items = cloak_catalog.apply(items)
    order = {i['id']: n for n, i in enumerate(existing)}
    items.sort(key=lambda i: order.get(i['id'], len(order)))
    import gear_art_catalog
    gear_art_catalog.apply(items)
    ITEMS.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    print(len(items), 'items')


def nornroot_only():
    """Refresh Nornroot art without regenerating unrelated equipment budgets."""
    existing = json.loads(ITEMS.read_text())
    replacements = {i['id']: i for i in nornroot_pieces(existing)}
    assert len(replacements) == 28
    items = [replacements.get(i['id'], i) for i in existing]
    ITEMS.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    print('28 Nornroot pieces refreshed; other equipment preserved')


if __name__ == '__main__':
    import sys
    if '--blackhour-only' in sys.argv:
        existing=json.loads(ITEMS.read_text());new={i['id']:i for i in blackhour_pieces(existing)}
        out=[new.pop(i['id'],i) for i in existing];out.extend(new.values());ITEMS.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
        print('28 Nullforged epic pieces refreshed')
    elif '--longship-only' in sys.argv:
        existing=json.loads(ITEMS.read_text());new={i['id']:i for i in longship_pieces(existing)}
        out=[new.pop(i['id'],i) for i in existing];out.extend(new.values());ITEMS.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
        print('28 Keelbound pieces refreshed')
    elif '--nornroot-only' in sys.argv:
        nornroot_only()
    else:
        vault_only() if '--vault-only' in sys.argv else main()
