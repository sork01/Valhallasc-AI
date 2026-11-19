#!/usr/bin/env python3
"""Temporary protocol mutations. Requires exclusive worktree access; restores source in finally.

Run a clean Cargo build afterwards to replace instrumented artifacts. No live service or DB is used.
"""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / 'server/src/world.rs', ROOT / 'server/src/world/fishing.rs']
CASES = {
    'clock': 'world::fishing_tests::fishing_client_shared_clock_is_unix_time',
    'announcement': 'world::fishing::lava_tests::fishing_lava_catches_use_local_species_junk_tiers_and_legendaries',
    'ordinary': 'world::fishing::lava_tests::fishing_lava_catches_use_local_species_junk_tiers_and_legendaries',
    'scope': 'world::fishing::lava_tests::fishing_client_legendary_announcement_is_zone_scoped_and_respects_hidden_actors',
}

def main():
    originals = {p: p.read_text() for p in FILES}
    changed = dict(originals)
    old = 'view["fishingTime"] = json!(fishing::now());'
    assert changed[FILES[0]].count(old) == 1
    changed[FILES[0]] = changed[FILES[0]].replace(old, 'view["fishingTime"] = json!(if std::env::var("FISH_CLIENT_MUTATION").as_deref() == Ok("clock") { 0. } else { fishing::now() });')
    old = '        if band == 3 {'
    assert changed[FILES[1]].count(old) == 1
    changed[FILES[1]] = changed[FILES[1]].replace(old, '''        if (band == 3 && std::env::var("FISH_CLIENT_MUTATION").as_deref() != Ok("announcement"))
            || std::env::var("FISH_CLIENT_MUTATION").as_deref() == Ok("ordinary") {''')
    old = 'self.emit_zone(line.zone, json!({"type":"announce","kind":"treasure","actor":actor,"text":text}));'
    assert changed[FILES[1]].count(old) == 1
    changed[FILES[1]] = changed[FILES[1]].replace(old, '''if std::env::var("FISH_CLIENT_MUTATION").as_deref() == Ok("scope") {
                self.emit_zone(0, json!({"type":"announce","kind":"treasure","text":text}));
            } else { ''' + old + ' }')
    reports = ROOT / 'test-results/fishing-client-mutations'
    reports.mkdir(parents=True, exist_ok=True)
    try:
        for p, text in changed.items(): p.write_text(text)
        build = subprocess.run(['bash', 'scripts/cargo.sh', 'test', '--no-run', '--message-format=json'], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True)
        artifacts = [json.loads(line) for line in build.stdout.splitlines() if line.startswith('{')]
        binaries = [x['executable'] for x in artifacts if x.get('reason') == 'compiler-artifact' and x.get('profile', {}).get('test') and x.get('executable')]
        assert len(binaries) == 1, binaries
        env = dict(os.environ); env.pop('FISH_CLIENT_MUTATION', None)
        for name in sorted(set(CASES.values())):
            subprocess.run([binaries[0], name, '--exact', '--test-threads=1'], cwd=ROOT, env=env, check=True)
        for mode, name in CASES.items():
            run = subprocess.run([binaries[0], name, '--exact', '--test-threads=1'], cwd=ROOT, env={**env, 'FISH_CLIENT_MUTATION': mode}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (reports / (mode + '.txt')).write_text(run.stdout)
            assert run.returncode == 101 and f'{name} ... FAILED' in run.stdout, (mode, run.stdout)
            print(mode + ': caught', flush=True)
    finally:
        for p, text in originals.items():
            p.write_text(text)
            assert p.read_text() == text

if __name__ == '__main__': main()
