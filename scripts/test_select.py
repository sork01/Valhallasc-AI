#!/usr/bin/env python3
"""Which test suites a run needs. The design, artwork and seasonal suites (tests/suite-groups.txt) run only when something
they cover changed; every suite that is not listed there always runs.

    python3 scripts/test_select.py py|browser [--results FILE]

Prints the suite names to run. A listed suite runs when one of its group's trigger files or its own file differs from BASE
(default origin/main; committed, uncommitted and untracked files all count). ALL=1 runs everything, which is also what
happens when the comparison cannot be made. --results appends a "skip" row to FILE for every suite left out.
"""
import json
import os
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ROOT / 'tests/suite-groups.txt'
EXTENSION = {'py': '.py', 'browser': '.cjs'}


def matches(path, patterns):
    return any(fnmatchcase(path, pattern) for pattern in patterns)


def select(suites, changed, groups, extension):
    """(names to run, {skipped name: its groups}) for the suites of one tier, given the changed repository paths."""
    relevant = {name for name, group in groups.items()
                if any(matches(path, group['triggers']) and not matches(path, group['ignore']) for path in changed)}
    run, skipped = [], {}
    for suite in suites:
        listed = [name for name, group in groups.items() if suite in group['suites']]
        if not listed or relevant.intersection(listed) or f'tests/{suite}{extension}' in changed:
            run.append(suite)
        else:
            skipped[suite] = listed
    return run, skipped


def changed_files(base, root=ROOT):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.PIPE).splitlines()
    fork = git('merge-base', base, 'HEAD')[0]
    # --no-renames: a moved file counts under its old name as well as its new one.
    return set(git('diff', '--name-only', '--no-renames', fork)) | set(git('ls-files', '--others', '--exclude-standard'))


def main(argv):
    if len(argv) not in (1, 3) or argv[0] not in EXTENSION or (len(argv) == 3 and argv[1] != '--results'):
        sys.exit(__doc__)
    tier, extension = argv[0], EXTENSION[argv[0]]
    suites = sorted(path.stem for path in (ROOT / 'tests').glob('*' + extension))
    groups = json.loads(GROUPS.read_text())
    base = os.environ.get('BASE', 'origin/main')
    changed = None
    if os.environ.get('ALL') != '1':
        try:
            changed = changed_files(base)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f'Cannot compare with {base} ({error}): running every suite.', file=sys.stderr)
    run, skipped = (suites, {}) if changed is None else select(suites, changed, groups, extension)
    print('\n'.join(run))
    if skipped:
        names = sorted({name for listed in skipped.values() for name in listed})
        print(f'Skipping {len(skipped)} of {len(suites)} {tier} suites ({", ".join(names)}): nothing they cover differs '
              f'from {base}. ALL=1 runs them.\n  ' + ' '.join(sorted(skipped)), file=sys.stderr)
    if len(argv) == 3:
        with open(argv[2], 'a') as results:
            results.writelines(f'{suite}\tskip\t0\n' for suite in sorted(skipped))


if __name__ == '__main__':
    main(sys.argv[1:])
