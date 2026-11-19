#!/usr/bin/env python3
"""Check fishing achievement regressions with one temporary instrumented build.

Requires exclusive worktree access. Restores source in finally; run a clean Cargo
test afterward to replace the temporary executable. Uses only private unit worlds.
"""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ACHIEVEMENTS = ROOT / 'server/src/achievements.rs'
FISHING = ROOT / 'server/src/world/fishing.rs'
CASES = {
    'disabled': 'achievements::fishing_tests::fishing_achievements_total_boundaries_clamp_and_award_once',
    'wrap': 'achievements::fishing_tests::fishing_achievements_total_boundaries_clamp_and_award_once',
    'duplicates': 'achievements::fishing_tests::fishing_achievements_collections_require_each_positive_species_record',
    'zero': 'achievements::fishing_tests::fishing_achievements_collections_require_each_positive_species_record',
    'foreign': 'achievements::fishing_tests::fishing_achievements_collections_require_each_positive_species_record',
    'legendary': 'achievements::fishing_tests::fishing_achievements_legendary_and_weight_require_catch_evidence',
    'weight': 'achievements::fishing_tests::fishing_achievements_legendary_and_weight_require_catch_evidence',
    'copies': 'world::fishing_tests::fishing_achievements_real_hook_ignores_copies_junk_and_misses',
}


def main():
    originals = {p: p.read_text() for p in [ACHIEVEMENTS, FISHING]}
    changed = originals[ACHIEVEMENTS]
    anchor = '        let p = &self.achievements;'
    assert changed.count(anchor) == 1
    changed = changed.replace(anchor, '''        if a.category == "Fishing" {
            let mutant = std::env::var("FISH_META_MUTATION").unwrap_or_default();
            match mutant.as_str() {
                "disabled" => return 0,
                "wrap" if a.metric == "fish_catches" => return (self.fishing.total as u32).min(a.target),
                "duplicates" if a.metric == "fish_set" => return a.members.iter()
                    .filter_map(|id| self.fishing.species.get(id))
                    .map(|r| r.count.min(u64::from(a.target)) as u32).sum::<u32>().min(a.target),
                "zero" if a.metric == "fish_set" => return a.members.iter()
                    .filter(|id| self.fishing.species.contains_key(*id)).count() as u32,
                "foreign" if a.metric == "fish_set" => return self.fishing.species.values()
                    .filter(|r| r.count > 0).count().min(a.target as usize) as u32,
                "legendary" if a.metric == "fish_legendary" => return 0,
                "weight" if a.metric == "fish_weight" => return self.fishing.species.values()
                    .map(|r| r.best_kg).max().unwrap_or(0).min(a.target),
                _ => (),
            }
        }
''' + anchor)
    fish = originals[FISHING]
    anchor = '        c.fishing.total += 1;'
    assert fish.count(anchor) == 1
    fish = fish.replace(anchor, '''        c.fishing.total += if std::env::var("FISH_META_MUTATION").as_deref() == Ok("copies") {
            u64::from(quantity)
        } else { 1 };''')
    reports = ROOT / 'test-results/fishing-meta-mutations'
    reports.mkdir(parents=True, exist_ok=True)
    try:
        ACHIEVEMENTS.write_text(changed)
        FISHING.write_text(fish)
        built = subprocess.run(['bash', 'scripts/cargo.sh', 'test', '--no-run', '--message-format=json'],
                               cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True)
        binaries = []
        for line in built.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get('reason') == 'compiler-artifact' and event.get('profile', {}).get('test') and event.get('executable'):
                binaries.append(event['executable'])
        assert len(binaries) == 1, binaries
        binary = binaries[0]
        env = dict(os.environ)
        env.pop('FISH_META_MUTATION', None)
        for suite in ['achievements::', 'world::fishing']:
            run = subprocess.run([binary, suite, '--test-threads=1'], cwd=ROOT, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (reports / (suite.replace(':', '-') + 'control.txt')).write_text(run.stdout)
            print(run.stdout, flush=True)
            assert run.returncode == 0, suite
        for mode, test in CASES.items():
            run = subprocess.run([binary, test, '--exact', '--test-threads=1'], cwd=ROOT,
                                 env={**env, 'FISH_META_MUTATION': mode},
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (reports / f'{mode}.txt').write_text(run.stdout)
            assert run.returncode == 101 and f'{test} ... FAILED' in run.stdout, (mode, run.stdout)
            print(f'{mode}: caught by {test}', flush=True)
    finally:
        for path, original in originals.items():
            path.write_text(original)
            assert path.read_text() == original


if __name__ == '__main__':
    main()
