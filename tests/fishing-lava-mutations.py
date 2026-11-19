#!/usr/bin/env python3
"""Mutation-check lava fishing in a private checkout, then restore the source.

Run with the normal Cargo environment: python3 tests/fishing-lava-mutations.py.
Requires exclusive access to this worktree (no builds, sync-world or commits).
One temporary instrumented test build exercises eight independent mutations.
"""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'server/src/world/fishing.rs'
CASES = {
    'shore': 'fishing_lava_cast_requires_the_whole_hero_on_clear_shore',
    'rods': 'fishing_lava_rods_surfaces_zone_and_level_are_enforced',
    'surfaces': 'fishing_lava_rods_surfaces_zone_and_level_are_enforced',
    'species': 'fishing_lava_catches_use_local_species_junk_tiers_and_legendaries',
    'loot': 'fishing_lava_catches_use_local_species_junk_tiers_and_legendaries',
    'snapshot': 'fishing_lava_all_real_shores_cast_without_moving_or_crossing_lava',
    'spot': 'fishing_lava_active_spots_spend_one_fish_and_damage_cancels',
    'damage': 'fishing_lava_active_spots_spend_one_fish_and_damage_cancels',
}


def main():
    original = SOURCE.read_text()
    changed = original
    edits = [
        ('if shore.distance(p) > 1e-8 {', 'if shore.distance(p) > 1e-8 && !lava_mutant("shore") {'),
        ('r.lava == lava', '(r.lava == lava || lava_mutant("rods"))'),
        ('    use FishingSurface::*;\n', '    use FishingSurface::*;\n'
         '    if lava_mutant("surfaces") && matches!(o.surface, Water | Lava | EwLava) { return Some(o.r); }\n'),
        ('&& s.min_tier <= line.tier', '&& (s.min_tier <= line.tier || lava_mutant("species"))'),
        ('&& s.zone.is_none_or(|z| z == line.zone)', '&& (s.zone.is_none_or(|z| z == line.zone) || lava_mutant("species"))'),
        ('if line.habitat == "Lava" {', 'if line.habitat == "Lava" && !lava_mutant("loot") {'),
        ('"lava":self.habitat=="Lava"', '"lava":self.habitat=="Lava" && !lava_mutant("snapshot")'),
        ('spots[index].remaining -= 1;', 'spots[index].remaining -= if lava_mutant("spot") { 2 } else { 1 };'),
        ('|| p.last_hurt != line.hurt_at', '|| (p.last_hurt != line.hurt_at && !lava_mutant("damage"))'),
    ]
    for old, new in edits:
        assert changed.count(old) == 1, old
        changed = changed.replace(old, new)
    changed += '\nfn lava_mutant(mode: &str) -> bool { std::env::var("FISH_LAVA_MUTATION").as_deref() == Ok(mode) }\n'
    reports = ROOT / 'test-results/fishing-lava-mutations'
    reports.mkdir(parents=True, exist_ok=True)
    try:
        SOURCE.write_text(changed)
        build = subprocess.run(['bash', 'scripts/cargo.sh', 'test', '--no-run', '--message-format=json'],
                               cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True)
        binary = None
        for line in build.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get('reason') == 'compiler-artifact' and event.get('profile', {}).get('test') and event.get('executable'):
                binary = event['executable']
        assert binary, 'No test executable'
        env = dict(os.environ)
        env.pop('FISH_LAVA_MUTATION', None)
        subprocess.run([binary, 'world::fishing::lava_tests::', '--test-threads=1'], env=env, cwd=ROOT, check=True)
        for mode, test in CASES.items():
            name = 'world::fishing::lava_tests::' + test
            run = subprocess.run([binary, name, '--exact', '--test-threads=1'], cwd=ROOT,
                                 env={**env, 'FISH_LAVA_MUTATION': mode},
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (reports / f'{mode}.txt').write_text(run.stdout)
            assert run.returncode == 101 and f'{name} ... FAILED' in run.stdout, (mode, run.returncode, run.stdout)
            print(f'{mode}: caught by {test}', flush=True)
    finally:
        SOURCE.write_text(original)
        assert SOURCE.read_text() == original


if __name__ == '__main__':
    main()
