#!/usr/bin/env python3
"""Generate the 50-piece orange design manifest, not runtime drops or art."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = (
    ('Ember Sovereign', 'flame-forged brass and black coal'),
    ('Verdant Crown', 'living root and emerald leaf'),
    ('Storm Oracle', 'forked lightning and cloud silver'),
    ('Abyss Singer', 'deep blue shell and singing pearl'),
    ('Starforged', 'dark iron with moving constellations'),
    ('Solar Regent', 'white gold and sunburst rays'),
    ('Ash Phoenix', 'charred feather and glowing cinder'),
    ('Moonlit Sentinel', 'pale glass and crescent silver'),
    ('Chronometer', 'bronze gears and amber hourglass'),
    ('Worldheart', 'ancient bark and sap crystal'),
)
# One level per family (all five slots share it): the ladder's purple levels 10..90 and the top step 99.
FAMILY_LEVELS = (10, 20, 30, 40, 50, 60, 70, 80, 90, 99)
SLOTS = (('armor', 'Cuirass'), ('weapon', 'Edge'), ('headgear', 'Crown'), ('shoulders', 'Mantle'), ('gloves', 'Grasp'))
# gear_levels.py: orange is 17.5% over purple, which is 17.5% over blue, which is 25% over green.
# A roll spans +-4% of the nominal value, so a piece beats the purple of its level and the next family's
# pieces stay above it (the Rust and Python checks both assert that).
ORANGE_OVER_PURPLE = 1.175
SPREAD = 0.04
# gear_levels.ATTRIBUTE_BONUS continued to 99 at the same slope as 90..95.
ATTRIBUTE_BONUS = {10: 3, 20: 7, 30: 15, 40: 30, 50: 40, 60: 55, 70: 70, 80: 85, 90: 100, 99: 114}
ACCURACY_CAP = 20   # 20 points = 100% hit
DEXTERITY_CAP = 70  # 70 points = 35% dodge


def level_factor(level):
    return round(0.16 * level + 0.8, 1)


def span(nominal, cap=None):
    """Inclusive integer roll range around a nominal value; never a single value, never above `cap`."""
    low = round(nominal * (1 - SPREAD))
    high = max(low + 1, round(nominal * (1 + SPREAD)))
    if cap is not None:
        high = min(high, cap)
        low = min(low, high - 1)
    return [low, high]


def purple_budget(slot, level):
    """(attack, defense) of the ordinary purple piece of this slot and level (gear_levels.budget)."""
    stat, base = {'weapon': ('attack', 4.0), 'armor': ('defense', 3.0)}.get(slot, ('defense', 1.0))
    total = base * level_factor(level) * 1.25 * 1.175 ** 2
    return (total * 0.8, total * 0.2) if stat == 'attack' else (total * 0.2, total * 0.8)


def rolls(slot, level):
    attack, defense = purple_budget(slot, level)
    bonus = ATTRIBUTE_BONUS[level] * ORANGE_OVER_PURPLE
    return dict(attack=span(attack * ORANGE_OVER_PURPLE), defense=span(defense * ORANGE_OVER_PURPLE),
                stamina=span(bonus), accuracy=span(min(bonus, ACCURACY_CAP), ACCURACY_CAP),
                dexterity=span(min(bonus, DEXTERITY_CAP), DEXTERITY_CAP))


def check_ladder(pieces):
    """Every piece beats the purple of its level; no piece's best roll reaches the next family's nominal value."""
    by_slot = {}
    for piece in pieces:
        level = piece['requiredLevel']
        attack, defense = purple_budget(piece['slot'], level)
        assert piece['rolls']['attack'][0] >= round(attack, 1) and piece['rolls']['defense'][0] >= round(defense, 1), piece['id']
        assert piece['rolls']['accuracy'][1] <= ACCURACY_CAP and piece['rolls']['dexterity'][1] <= DEXTERITY_CAP
        by_slot.setdefault(piece['slot'], []).append(piece)
    for slot, run in by_slot.items():
        for low, high in zip(run, run[1:]):
            nominal = purple_budget(slot, high['requiredLevel'])
            for index, key in enumerate(('attack', 'defense')):
                if nominal[index] * ORANGE_OVER_PURPLE < 10:
                    continue   # whole-number rolls cannot separate values this small
                assert low['rolls'][key][1] < nominal[index] * ORANGE_OVER_PURPLE, (low['id'], key)
            assert low['rolls']['stamina'][1] < ATTRIBUTE_BONUS[high['requiredLevel']] * ORANGE_OVER_PURPLE, low['id']


def build():
    pieces = []
    for family, (name, motif) in enumerate(FAMILIES):
        level = FAMILY_LEVELS[family]
        for slot, suffix in SLOTS:
            number = len(pieces) + 1
            pieces.append(dict(id=f'orange_{number:02}', name=f'{name} {suffix}',
                               slot=slot, rarity='legendary', requiredLevel=level, **{'class': None},
                               motif=motif, rolls=rolls(slot, level)))
    assert len(pieces) == 50
    check_ladder(pieces)
    assert len({p['name'] for p in pieces}) == 50
    return dict(version=1, drop=dict(chancePerKill=0.001, eligible='every mob; a piece is found only by a player at most 5 levels below its requiredLevel',
                                     levelWindow=5,
                                     selection='uniform across all 50 pieces; one success awards one copy'),
                distribution=dict(method='independent inclusive uniform integer for each listed stat range',
                                  correlations='none', reroll='never; values are owned by the saved copy'),
                equip=dict(classes='all five', minLevel='the piece requiredLevel'), pieces=pieces)


if __name__ == '__main__':
    path = ROOT / 'world/orange_rules.txt'
    path.write_text(json.dumps(build(), indent=2) + '\n')
    print(path, '50 pieces')
