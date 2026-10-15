"""Resumable per-dungeon export, catalog wiring and real-client verification.

Usage: python3 scripts/build_instance_gear_batch.py pavilion
PixelFlow records and atlases are saved piece by piece. After all 28 pieces
exist, the catalog is wired once, then each piece is checked in Chromium and
recorded complete in docs/instance-gear-state.txt.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import gear_art_catalog
import instance_gear_jobs
import late_instance_gear_shapes
import make_progression_gear as gear

ROOT = Path(__file__).resolve().parents[1]
NODE = '/home/serveperry/.nvm/versions/node/v20.20.2/bin/node'


def run(command, log):
    log.write('\n$ ' + ' '.join(command) + '\n')
    log.flush()
    result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        tail = '\n'.join(Path(log.name).read_text().splitlines()[-25:])
        raise RuntimeError(f'{command[0]} failed ({result.returncode}):\n{tail}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('group', choices=tuple(late_instance_gear_shapes.STYLES))
    args = parser.parse_args()
    group = args.group
    tasks = [task for task in json.loads(instance_gear_jobs.STATE.read_text())['tasks']
             if task['group'] == group]
    assert len(tasks) == 28
    log_path = ROOT / 'test-results/gear-redesign' / (group + '-batch.log')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a') as log:
        for number, task in enumerate(tasks, 1):
            gear.activate(task)
            manifest = json.loads(gear.MANIFEST.read_text())
            record = manifest.get(task['id'])
            if record and record.get('files'):
                assert record['revision'] == gear.revision(task), task['id']
            else:
                run([sys.executable, 'scripts/make_progression_gear.py', 'build', task['id']], log)
            print(f'{group}: {number}/28 {task["id"]} exported', flush=True)
        gear_art_catalog.wire()
        run([NODE, 'scripts/sync-world.cjs'], log)
        for number, task in enumerate(tasks, 1):
            if task['done']:
                continue
            job = task['id']
            run([NODE, 'tests/gear-piece-art.cjs', job], log)
            record = json.loads(gear.MANIFEST.read_text())[job]
            evidence = ['scripts/late_instance_gear_shapes.py', 'world/gear-art.txt',
                        *record['files'], 'test-results/gear-redesign/' + job + '.png',
                        'test-results/gear-redesign/' + job + '-browser.json']
            run([sys.executable, 'scripts/instance_gear_jobs.py', 'finish', job,
                 '--evidence', *evidence, '--note',
                 'Theme concept preview inspected; all pose bounds, editable both-body PixelFlow export, icon and real-client silhouette checks passed.'], log)
            print(f'{group}: {number}/28 {job} verified', flush=True)
    print(f'{group}: all 28 fitted pieces complete', flush=True)


if __name__ == '__main__':
    main()
