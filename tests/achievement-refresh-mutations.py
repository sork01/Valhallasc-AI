#!/usr/bin/env python3
"""Prove the post-launch catalog assertions reject six independent data regressions.

Exclusive worktree use: compile one temporary catalog with selectable faults,
run the new tests as a control, then require each fault to fail its focused test.
Always restore source; rebuild clean artifacts afterwards.
"""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'server/src/achievements.rs'
PREFIX = 'achievements::refresh_tests::'
CASES = {
    'early': 'achievements_refresh_numeric_goals_award_at_the_exact_boundary_once',
    'species': 'achievements_refresh_collections_match_real_fish_and_distinct_fisher_quests',
    'fisher': 'achievements_refresh_collections_match_real_fish_and_distinct_fisher_quests',
    'seahorse': 'achievements_refresh_fisher_circuits_require_each_claim_across_lifetimes',
    'title': 'achievements_refresh_new_titles_unlock_and_survive_rebirth_and_legacy_saves',
    'legacy': 'achievements_refresh_preserves_the_entire_old_catalog',
}


def main():
    original = SOURCE.read_text()
    changed = original.replace('let rows: Vec<Achievement> =', 'let mut rows: Vec<Achievement> =', 1)
    anchor = '        let mut ids = BTreeSet::new();'
    assert changed.count(anchor) == 1
    changed = changed.replace(anchor, '''        // Temporary mutation harness only; removed before release.
        match std::env::var("ACHIEVEMENT_REFRESH_MUTATION").unwrap_or_default().as_str() {
            "early" => rows.iter_mut().find(|a| a.id == "kills_10000").unwrap().target = 9999,
            "species" => {
                let a = rows.iter_mut().find(|a| a.id == "fish_log_all").unwrap();
                a.members.pop(); a.target -= 1;
            },
            "fisher" => {
                let a = rows.iter_mut().find(|a| a.id == "fisher_circuit_1").unwrap();
                a.members[0] = "fisher_meadow_0_2".into();
            },
            "seahorse" => {
                let a = rows.iter_mut().find(|a| a.id == "seahorse_friend").unwrap();
                a.metric = "mounts".into(); a.members.clear();
            },
            "title" => rows.iter_mut().find(|a| a.id == "quests_500").unwrap().title.clear(),
            "legacy" => rows[0].points += 1,
            _ => (),
        }
''' + anchor)
    reports = ROOT / 'test-results/achievement-refresh-mutations'
    reports.mkdir(parents=True, exist_ok=True)
    try:
        SOURCE.write_text(changed)
        built = subprocess.run(['bash', 'scripts/cargo.sh', 'test', '--no-run', '--message-format=json'],
                               cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True)
        binaries = [event['executable'] for line in built.stdout.splitlines()
                    if (event := json.loads(line)).get('reason') == 'compiler-artifact'
                    and event.get('profile', {}).get('test') and event.get('executable')]
        assert len(binaries) == 1, binaries
        binary = binaries[0]
        env = dict(os.environ)
        env.pop('ACHIEVEMENT_REFRESH_MUTATION', None)
        control = subprocess.run([binary, PREFIX, '--test-threads=1'], cwd=ROOT, env=env,
                                 capture_output=True, text=True)
        (reports / 'control.txt').write_text(control.stdout + control.stderr)
        assert control.returncode == 0, control.stdout + control.stderr
        print('All six new tests pass without mutations.', flush=True)
        for mode, test in CASES.items():
            full = PREFIX + test
            result = subprocess.run([binary, full, '--exact', '--test-threads=1'], cwd=ROOT,
                                    env={**env, 'ACHIEVEMENT_REFRESH_MUTATION': mode},
                                    capture_output=True, text=True)
            (reports / f'{mode}.txt').write_text(result.stdout + result.stderr)
            assert result.returncode == 101 and f'{full} ... FAILED' in result.stdout, (mode, result.stdout, result.stderr)
            print(f'{mode}: caught by {test}', flush=True)
    finally:
        SOURCE.write_text(original)
        assert SOURCE.read_text() == original


if __name__ == '__main__':
    main()
