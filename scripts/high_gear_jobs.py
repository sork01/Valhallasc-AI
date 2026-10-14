"""Persistent per-piece work list for ordinary level-60–95 equipment art."""
import argparse
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'docs/high-gear-state.txt'
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
CLASS_KINDS = ('armor', 'headgear', 'shoulders', 'gloves', 'weapon')
SHARED_KINDS = ('pants', 'necklace', 'accessory')


def initial():
    items = json.loads((ROOT / 'world/items.txt').read_text())
    tasks = []
    for level in range(60, 100, 5):
        for cls, kinds in [*((c, CLASS_KINDS) for c in CLASSES), (None, SHARED_KINDS)]:
            for kind in kinds:
                matches = [i for i in items if i.get('requiredLevel') == level and i.get('class') == cls
                           and i['kind'] == kind and i['rarity'] == 'common' and not i.get('source')]
                assert len(matches) == 1, (level, cls, kind)
                item = matches[0]
                tasks.append(dict(id=f'L{level}-{cls or "shared"}-{kind}', group=f'L{level}',
                                  className=cls, kind=kind, item=item['id'], name=item['name'],
                                  done=False, phase='not started', note='', evidence=[]))
    assert len(tasks) == 224
    return dict(updated=datetime.now().isoformat(timespec='seconds'), tasks=tasks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'finish', 'summary'))
    parser.add_argument('job', nargs='?')
    parser.add_argument('--evidence', nargs='*', default=[])
    args = parser.parse_args()
    if args.command == 'init' and not STATE.exists():
        STATE.write_text(json.dumps(initial(), indent=2) + '\n')
    state = json.loads(STATE.read_text())
    if args.command == 'finish':
        task = next(t for t in state['tasks'] if t['id'] == args.job)
        assert args.evidence and all((ROOT / file).is_file() for file in args.evidence)
        task.update(done=True, phase='complete', evidence=args.evidence)
        state['updated'] = datetime.now().isoformat(timespec='seconds')
        STATE.write_text(json.dumps(state, indent=2) + '\n')
    done = sum(task['done'] for task in state['tasks'])
    print(f'{done}/{len(state["tasks"])} high-level base pieces complete')


if __name__ == '__main__':
    main()
