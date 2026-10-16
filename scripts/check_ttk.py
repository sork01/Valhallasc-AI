#!/usr/bin/env python3
"""Check a completed nine-seed ordinary-fight report against shared target bands."""
import argparse
import json
from pathlib import Path

CLASSES = {'warrior', 'mage', 'assassin', 'priest', 'hunter'}
LEVELS = [*range(5, 100, 5), 99]
TARGETS = json.loads((Path(__file__).resolve().parent.parent / 'world/ttk-targets.txt').read_text())


def check(paths):
    rows = [row for path in paths for row in json.loads(Path(path).read_text())]
    cases = {(row['level'], row['class']): row for row in rows}
    if len(rows) != len(cases) or set(cases) != {(level, cls) for level in LEVELS for cls in CLASSES}:
        raise ValueError('expected one case for every class at levels 5, 10, …, 95 and 99')
    if any(row['runs'] != 9 or row['spread'] != 'even' or row['rotation'] != 'skills'
           or row['foe'] != 'ordinary' or row['consumables'] or row['harmless'] for row in rows):
        raise ValueError('expected nine normal seeded fights per case')
    errors = []
    maximum_spread = 0.
    lowest_hp = 1.
    for level in LEVELS:
        band = next(b for b in TARGETS if b['minLevel'] <= level <= b['maxLevel'])
        group = [cases[level, cls] for cls in sorted(CLASSES)]
        times = [row['seconds']['median'] for row in group]
        spread = max(times) / min(times)
        maximum_spread = max(maximum_spread, spread)
        if spread > 1.3:
            errors.append(f'level {level}: class spread {spread:.3f}×')
        for row in group:
            lowest_hp = min(lowest_hp, row['lowestHpFraction'])
            if row['failures']:
                errors.append(f"{row['class']} {level}: {row['failures']} failed seed(s)")
            if not band['minSeconds'] <= row['seconds']['median'] <= band['maxSeconds']:
                errors.append(f"{row['class']} {level}: median {row['seconds']['median']} s outside band")
            if row['lowestHpFraction'] < 0.2:
                errors.append(f"{row['class']} {level}: only {row['lowestHpFraction']:.0%} HP left")
    if errors:
        raise ValueError('\n'.join(errors))
    print(f'{len(rows)} cases, {sum(row["runs"] for row in rows)} fights, '
          f'0 failed seeds, maximum class spread {maximum_spread:.3f}×, '
          f'lowest median HP {lowest_hp:.0%}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', nargs=5, help='one nine-seed JSON report per class')
    args = parser.parse_args()
    check(args.reports)


if __name__ == '__main__':
    main()
