"""Track individually exported Undervault and Moonwell set art."""
import argparse
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'docs/dungeon-gear-state.txt'
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
CLASS_KINDS = ('armor', 'headgear', 'shoulders', 'gloves', 'weapon')
SOURCES = {'vault': ('undervault', ('pants', 'accessory')),
           'moonwell': ('moonwell', ('pants', 'necklace', 'accessory'))}


def initial():
    items = json.loads((ROOT / 'world/items.txt').read_text())
    tasks = []
    for group, (source, shared) in SOURCES.items():
        for cls, kinds in [*((c, CLASS_KINDS) for c in CLASSES), (None, shared)]:
            for kind in kinds:
                matches = [i for i in items if i.get('source') == source and i.get('class') == cls and i['kind'] == kind]
                assert len(matches) == 1, (group, cls, kind)
                item = matches[0]
                tasks.append(dict(id=f'{group}-{cls or "shared"}-{kind}', group=group,
                                  className=cls, kind=kind, item=item['id'], name=item['name'],
                                  done=False, phase='not started', note='', evidence=[]))
    assert len(tasks) == 55
    return dict(updated=datetime.now().isoformat(timespec='seconds'), tasks=tasks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'update', 'reopen', 'finish', 'summary'))
    parser.add_argument('job', nargs='?')
    parser.add_argument('--phase', default='in progress')
    parser.add_argument('--note', default='')
    parser.add_argument('--evidence', nargs='*', default=[])
    args = parser.parse_args()
    if args.command == 'init' and not STATE.exists():
        STATE.write_text(json.dumps(initial(), indent=2) + '\n')
    state = json.loads(STATE.read_text())
    if args.command in ('update', 'reopen', 'finish'):
        task = next(t for t in state['tasks'] if t['id'] == args.job)
        if args.command == 'finish':
            assert args.evidence and all((ROOT / file).is_file() for file in args.evidence)
            task.update(done=True, phase='complete', evidence=args.evidence, note=args.note)
        elif args.command == 'reopen':
            assert task['done']
            task.update(done=False, phase=args.phase, evidence=[], note=args.note)
        else:
            assert not task['done']
            task.update(phase=args.phase, note=args.note)
        state['updated'] = datetime.now().isoformat(timespec='seconds')
        STATE.write_text(json.dumps(state, indent=2) + '\n')
    print(f'{sum(t["done"] for t in state["tasks"])}/{len(state["tasks"])} dungeon pieces complete')


if __name__ == '__main__':
    main()
