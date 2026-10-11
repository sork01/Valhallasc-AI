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
SLOTS = (
    ('armor', 'Cuirass', [38, 55], [110, 145]),
    ('weapon', 'Edge', [155, 190], [22, 38]),
    ('headgear', 'Crown', [28, 44], [82, 110]),
    ('shoulders', 'Mantle', [36, 54], [88, 116]),
    ('gloves', 'Grasp', [48, 68], [74, 100]),
)


def build():
    pieces = []
    for family, (name, motif) in enumerate(FAMILIES):
        for slot, suffix, attack, defense in SLOTS:
            number = len(pieces) + 1
            pieces.append(dict(id=f'orange_{number:02}', name=f'{name} {suffix}',
                               slot=slot, rarity='legendary', requiredLevel=1, **{'class': None},
                               motif=motif,
                               rolls=dict(attack=attack, defense=defense,
                                          stamina=[90, 140], accuracy=[8, 20], dexterity=[18, 35])))
    assert len(pieces) == 50
    assert len({p['name'] for p in pieces}) == 50
    return dict(version=1, drop=dict(chancePerKill=0.001, eligible='every mob, regardless of mob or player level',
                                     selection='uniform across all 50 pieces; one success awards one copy'),
                distribution=dict(method='independent inclusive uniform integer for each listed stat range',
                                  correlations='none', reroll='never; values are owned by the saved copy'),
                equip=dict(classes='all five', minLevel=1), pieces=pieces)


if __name__ == '__main__':
    path = ROOT / 'world/orange_rules.txt'
    path.write_text(json.dumps(build(), indent=2) + '\n')
    print(path, '50 pieces')
