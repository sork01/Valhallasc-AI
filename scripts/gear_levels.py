"""Builds the level 1–65 gear ladder and exclusive Undervault/Cathedral sets in world/items.txt.

Run `python3 scripts/gear_levels.py`, then `node scripts/sync-world.cjs` and rebuild Rust. It is idempotent: it keeps
every non-gear item and every original piece (an entry with no `art` key) and regenerates the rest.

SETS. Required levels come in steps of five (1, 5, ... 65). Every level has a gray, a green and a blue set; purple
exists at every multiple of ten. That is 48 sets. A set holds, per class, a chest, headgear, shoulders,
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

LEVELS = (1, *range(5, 66, 5))
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
    70: 70, 75: 78, 80: 85, 85: 93, 90: 100,
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
    step = min(90, max(5, i.get('requiredLevel', 1) // 5 * 5))
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
    items = [i for i in existing if 'art' not in i]
    gear = {'armor', 'weapon', 'headgear', 'shoulders', 'gloves', 'pants', 'necklace', 'accessory'}
    out, bases = [], {}
    for i in items:
        if i['kind'] not in gear or i['rarity'] == 'gm':
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
    out.extend(vault_pieces(out))
    out.extend(cathedral_pieces(out))
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
    order = {i['id']: n for n, i in enumerate(existing)}
    items.sort(key=lambda i: order.get(i['id'], len(order)))
    ITEMS.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    print(len(items), 'items')


if __name__ == '__main__':
    import sys
    vault_only() if '--vault-only' in sys.argv else main()
