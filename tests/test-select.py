#!/usr/bin/env python3
"""Which suites scripts/test_select.py leaves out, and when. MUTATE=no-trigger|always-skip must fail."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import test_select as S

groups = json.loads(S.GROUPS.read_text())
if os.getenv('MUTATE') == 'no-trigger':
    groups['design']['triggers'].remove('world/map.txt')
if os.getenv('MUTATE') == 'always-skip':
    S.select = lambda suites, changed, groups, extension: ([s for s in suites if not any(s in g['suites'] for g in groups.values())],
                                                           {s: [] for s in suites if any(s in g['suites'] for g in groups.values())})
files = {S.EXTENSION[tier]: sorted(p.stem for p in (ROOT / 'tests').glob('*' + S.EXTENSION[tier])) for tier in S.EXTENSION}
every = set(files['.py']) | set(files['.cjs'])
for name, group in groups.items():
    gone = [s for s in group['suites'] if s not in every]
    assert not gone, f'{name} lists suites that do not exist: {gone}'
assert {name: len(group['suites']) >= floor for (name, group), floor in zip(sorted(groups.items()), (70, 20, 15))} == {name: True for name in groups}


def skipped(changed):
    out = set()
    for extension, suites in files.items():
        run, left = S.select(suites, set(changed), groups, extension)
        assert set(run) | set(left) == set(suites) and not set(run) & set(left)
        out |= set(left)
    return out


listed = {name: set(group['suites']) for name, group in groups.items()}
everything = set().union(*listed.values())
# A change none of the groups cover leaves all three out, and nothing else.
assert skipped(['server/src/bank.rs', 'client/assets/music_field.mp3', 'client/assets/sfx_boss_roar.mp3', 'client/field.js']) == everything
assert skipped([]) == everything
# A map change brings the design suites, and only them.
assert skipped(['world/map.txt']) == everything - listed['design']
assert not skipped(['scripts/orrery_design.py']) & listed['design']
# Artwork: any picture or drawing script.
for path in ('client/assets/orrery.txt', 'client/magesprite.js', 'scripts/shared_slime_redraw.py'):
    assert not skipped([path]) & listed['art'], path
    assert listed['seasonal'] - listed['art'] <= skipped([path]), path
# A holiday file brings every holiday suite, including the artwork ones that belong to a holiday.
for path in ('client/christmas.js', 'server/src/festival.rs', 'server/src/world/seasonal_hunt.rs'):
    assert not skipped([path]) & listed['seasonal'], path
    assert listed['design'] <= skipped([path]), path
# A suite whose own file changed always runs.
assert skipped(['tests/orrery-design-ui.cjs']) == everything - {'orrery-design-ui'}
assert skipped(['tests/seam-roads.py']) == everything - {'seam-roads'}
# Suites outside the groups are never left out, even look-alikes (world map, cloak rules, holiday protocol).
assert not everything & {'zones-ui', 'organic-atlas-ui', 'gear-cloak-ui', 'festival-protocol', 'todo-art-ui', 'npc-art', 'multiplayer'}
# The real comparison: against a throwaway repository, committed, uncommitted and untracked changes all count.
with tempfile.TemporaryDirectory() as directory:
    repo = Path(directory)
    git = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@localhost', *a], cwd=repo, check=True, capture_output=True)
    git('init', '-q')
    (repo / 'a').write_text('1'); (repo / 'b').write_text('1'); git('add', '.'); git('commit', '-qm', 'base'); git('branch', 'base')
    (repo / 'a').write_text('2'); git('commit', '-qam', 'work'); (repo / 'b').write_text('2'); (repo / 'c').write_text('1')
    assert S.changed_files('base', repo) == {'a', 'b', 'c'}
print('test selection: groups, triggers and comparison pass')
