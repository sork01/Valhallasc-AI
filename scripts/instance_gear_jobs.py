"""Track fitted art for the eleven later dungeon equipment sets."""
import argparse
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'docs/instance-gear-state.txt'
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
CLASS_KINDS = ('armor', 'headgear', 'shoulders', 'gloves', 'weapon')
SHARED_KINDS = ('pants', 'necklace', 'accessory')
SOURCES = {
    'eye': 'eye_below', 'elder': 'elder_hollow', 'pavilion': 'thousandfold',
    'rain': 'rain_crown', 'seed': 'seed_vault', 'astro': 'sunken_astrolabe',
    'thunder': 'thunderheart_gate', 'bloom': 'blooming_labyrinth',
    'solar': 'solar_crucible', 'amber': 'amber_archive',
    'solstice': 'silent_solstice',
}


def initial():
    items = json.loads((ROOT / 'world/items.txt').read_text())
    tasks = []
    for group, source in SOURCES.items():
        for cls, kinds in [*((c, CLASS_KINDS) for c in CLASSES), (None, SHARED_KINDS)]:
            for kind in kinds:
                matches = [i for i in items if i.get('source') == source
                           and i.get('class') == cls and i['kind'] == kind]
                assert len(matches) == 1, (group, cls, kind)
                item = matches[0]
                tasks.append(dict(id=f'{group}-{cls or "shared"}-{kind}', group=group,
                                  className=cls, kind=kind, item=item['id'], name=item['name'],
                                  done=False, phase='not started', note='', evidence=[]))
    assert len(tasks) == 308
    return dict(updated=datetime.now().isoformat(timespec='seconds'), tasks=tasks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'sync', 'update', 'reopen', 'finish', 'summary'))
    parser.add_argument('job', nargs='?')
    parser.add_argument('--phase', default='in progress')
    parser.add_argument('--note', default='')
    parser.add_argument('--evidence', nargs='*', default=[])
    args = parser.parse_args()
    if args.command == 'init' and not STATE.exists():
        STATE.write_text(json.dumps(initial(), indent=2) + '\n')
    state = json.loads(STATE.read_text())
    if args.command == 'sync':
        existing = {task['id'] for task in state['tasks']}
        additions = [task for task in initial()['tasks'] if task['id'] not in existing]
        state['tasks'].extend(additions)
        if additions:
            state['updated'] = datetime.now().isoformat(timespec='seconds')
            STATE.write_text(json.dumps(state, indent=2) + '\n')
        print(f'added {len(additions)} instance jobs')
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
    print(f'{sum(t["done"] for t in state["tasks"])}/{len(state["tasks"])} instance pieces complete')


if __name__ == '__main__':
    main()
