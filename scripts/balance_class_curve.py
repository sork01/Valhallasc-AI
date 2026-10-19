#!/usr/bin/env python3
"""Class attack curve from replayed best rotations (owner, 2026-10-19).

Reads `REPLAY <level> <class> <dps>` lines (from `cargo test replay_best_rotations -- --ignored --nocapture`, one log per
class), takes the mean DPS of the five classes at each level as the benchmark, and prints the CLASS_ATTACK_CURVE rows
with every class's entry multiplied by benchmark / its DPS. Run it on the output of the CURRENT curve; run the replay
again on the new curve, and again through this script (it prints the remaining spread), until every class is near 1.00.

    python3 scripts/balance_class_curve.py LOG... [--curve server/src/items.rs] [--write]
"""
import argparse
import re
import statistics
from pathlib import Path

CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
ROW = re.compile(r'^(\s*)\((\d+), \[([^\]]*)\]\),$')


def read_replay(paths):
    dps = {}
    for path in paths:
        for line in Path(path).read_text().splitlines():
            m = re.match(r'REPLAY (\d+) (\w+) (\d+)', line)
            if m:
                dps[(int(m[1]), m[2])] = float(m[3])
    levels = sorted({level for level, _ in dps})
    for level in levels:
        for c in CLASSES:
            if (level, c) not in dps:
                raise SystemExit(f'missing {c} at level {level}')
    return dps, levels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logs', nargs='+')
    parser.add_argument('--curve', default='server/src/items.rs')
    parser.add_argument('--write', action='store_true', help='rewrite the rows of the replayed levels in the curve file')
    args = parser.parse_args()
    dps, levels = read_replay(args.logs)
    source = Path(args.curve).read_text().splitlines()
    out = []
    print('level  benchmark  ' + '  '.join(f'{c:>9}' for c in CLASSES) + '   spread (best/worst)')
    for line in source:
        m = ROW.match(line)
        if m and int(m[2]) in levels:
            level = int(m[2])
            values = [float(v) for v in m[3].split(',')]
            benchmark = statistics.mean(dps[(level, c)] for c in CLASSES)
            ratios = [dps[(level, c)] / benchmark for c in CLASSES]
            spread = max(ratios) / min(ratios)
            print(f'{level:>5}  {benchmark:>9,.0f}  ' + '  '.join(f'{r:>9.3f}' for r in ratios) + f'   {spread:.3f}')
            new = [v * benchmark / dps[(level, c)] for v, c in zip(values, CLASSES)]
            line = f'{m[1]}({level}, [' + ', '.join(f'{v:.3f}' for v in new) + ']),'
        out.append(line)
    if args.write:
        Path(args.curve).write_text('\n'.join(out) + '\n')
        print(f'rewrote {args.curve}')
    else:
        print('\n'.join(l for l in out if ROW.match(l) and int(ROW.match(l)[2]) in levels))


if __name__ == '__main__':
    main()
