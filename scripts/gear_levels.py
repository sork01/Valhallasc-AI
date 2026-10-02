"""Builds every piece of gear in world/items.txt: 17 sets by required level and rarity, with their stats.

Run `python3 scripts/gear_levels.py`, then `node scripts/sync-world.cjs` and rebuild Rust. It is idempotent: it keeps
every non-gear item and every original piece (an entry with no `art` key) and regenerates the rest.

SETS. Required levels come in steps of five (1, 5, 10, 15, 20). Every level has a gray, a green and a blue set; purple
exists only at 10 and 20 (every other step). That is 17 sets. A set holds, per class, a chest, headgear, shoulders,
gloves and weapon, plus the shared (class-independent) pants, necklace and ring.

ART. No new art is drawn. A generated piece names the original piece it recolours (`art`: the original's variant) and
a `tint` (CSS-filter terms: hue-rotate degrees, saturate, brightness) that the client applies to the worn layers and
the inventory icon. Gray and blue sets use the class's first drawing, green and purple the second.
The originals sit in the cells they already had: starters are the level 1 gray set, the second drawings the level 1
green set, and the three shared pants/necklace/ring pieces keep their level-5-green / level-20-blue / level-20-purple
cells. The three shared headgear/shoulders/gloves pieces are extras outside the sets.

STATS follow WoW's tiers. Gray has no stat budget: only base armor (defense) or weapon damage (attack). Green keeps
that base and adds a secondary stat; blue is 17.5% over green, purple 17.5% over blue, orange 17.5% over purple. Each
five-level step is worth more than a tier.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ITEMS = ROOT / 'world' / 'items.txt'

LEVELS = (1, 5, 10, 15, 20)
RARITIES = ['common', 'uncommon', 'rare', 'epic']       # gray, green, blue, purple
COLOUR = {'common': 'gray', 'uncommon': 'green', 'rare': 'blue', 'epic': 'purple'}
SETS = [(level, rarity) for level in LEVELS for rarity in RARITIES if rarity != 'epic' or level in (10, 20)]
LEVEL_FACTOR = {1: 1.0, 5: 1.6, 10: 2.4, 15: 3.2, 20: 4.0}
TIER_STEP = 1.175
GREEN_BUDGET = 1.25
SECONDARY_SHARE = 0.2
RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary']
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
}
LEVEL_HUE = {1: 0, 5: 70, 10: 140, 15: 210, 20: 280}
RARITY_TINT = {   # hue offset, saturate, brightness
    'common': (0, 0.5, 0.9), 'uncommon': (0, 1.0, 1.0), 'rare': (30, 1.15, 1.1), 'epic': (60, 1.2, 1.15),
}


def tint(level, rarity, shared=False):
    """Hue turns with the level and the tier. Shared pieces turn 20 more degrees, so none is the untouched original
    (the level 1 green set would be, and the original shared pieces sit in other cells)."""
    offset, saturate, brightness = RARITY_TINT[rarity]
    return {'hue': (LEVEL_HUE[level] + offset + (20 if shared else 0)) % 360, 'saturate': saturate, 'brightness': brightness}


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


def ordered(i):
    keys = ['id', 'name', 'kind', 'rarity', 'requiredLevel']
    return {**{k: i[k] for k in keys if k in i}, **{k: v for k, v in i.items() if k not in keys}}


def finish(i, level, rarity):
    i['rarity'] = rarity
    i['requiredLevel'] = level
    i['sell'] = 0 if i.get('starter') else round(SELL_BASE[rarity] * LEVEL_FACTOR[level])
    i['attack'], i['defense'] = budget(i['kind'], i.get('class'), rarity, level)
    return ordered(i)


def main():
    items = [i for i in json.loads(ITEMS.read_text()) if 'art' not in i]
    gear = {'armor', 'weapon', 'headgear', 'shoulders', 'gloves', 'pants', 'necklace', 'accessory'}
    out, bases = [], {}
    for i in items:
        if i['kind'] not in gear:
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
    ITEMS.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(len(out), 'items,', len(SETS), 'sets')


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


if __name__ == '__main__':
    main()
