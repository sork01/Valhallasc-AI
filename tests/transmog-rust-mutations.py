#!/usr/bin/env python3
"""Mutate the actual implementation, require the targeted test to fail, then restore every byte.

Exclusive worktree use only. Unoptimized test builds keep these bounded state checks quick;
this changes neither production source semantics nor the private executable's build profile.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CARGO_ROOT = Path('/media/raid/valhallasc-data/valhalla-dev/.tools')
CASES = {
    'unlock': ('server/src/items.rs', '        self.unlock_appearance(id);', '', 'transmog_unlock_is_permanent_unique_equipment_only_and_ignores_zero_grants'),
    'empty': ('server/src/transmog.rs', 'worn.iter().any(|(slot, _)| slot == s) && self.appearance_allowed(s, id)', 'self.appearance_allowed(s, id)', 'transmog_persists_across_upgrade_unequip_and_low_level_rebirth'),
    'revert': ('server/src/transmog.rs', 'id != "real" && self.wardrobe.slots.get(slot) != Some(id)', 'self.wardrobe.slots.get(slot) != Some(id)', 'transmog_hide_and_empty_slots_and_free_revert'),
    'atomic': ('server/src/transmog.rs', '        let mut fee = 0u32;', '        self.wardrobe.slots.extend(changes.clone());\n        let mut fee = 0u32;', 'transmog_guards_batch_atomically_and_scales_fees_with_free_noops'),
    'trade': ('server/src/world/trade.rs', '        receiver.unlock_appearance(&s.item);', '', 'transmog_trade_unlocks_appearance_for_recipient_and_keeps_givers_memory'),
    'migration': ('server/src/store.rs', '    character.migrate_wardrobe();', '', 'transmog_store_load_migrates_legacy_equipment_and_bank_and_persists_collection'),
    'privacy': ('server/src/visibility.rs', '    "equippedLook", "transmogs", "wardrobe",', '', 'transmog_world_applies_saves_dialogue_owner_privacy_and_inspect_real_items'),
}


def main():
    env = {**os.environ, 'CARGO_HOME': str(CARGO_ROOT/'cargo'), 'RUSTUP_HOME': str(CARGO_ROOT/'rustup'),
           'CARGO_PROFILE_TEST_OPT_LEVEL': '0', 'CARGO_PROFILE_TEST_DEBUG': '0'}
    modes = sys.argv[1:] or list(CASES)
    directory = ROOT/'test-results/transmog-mutations'
    directory.mkdir(parents=True, exist_ok=True)
    for mode in modes:
        file, old, new, test = CASES[mode]
        path = ROOT/file
        original = path.read_bytes()
        text = original.decode()
        assert text.count(old) == 1, f'{mode}: mutation anchor changed'
        try:
            path.write_text(text.replace(old, new))
            result = subprocess.run([str(CARGO_ROOT/'cargo/bin/cargo'), 'test', test, '--', '--nocapture'],
                                    cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=360)
            log = result.stdout.decode(errors='replace')
            (directory/f'{mode}.log').write_text(log)
            assert result.returncode == 101 and 'test result: FAILED.' in log and f'{test} ... FAILED' in log, log[-6000:]
            print(f'Caught {mode}: {test}', flush=True)
        finally:
            path.write_bytes(original)
    print('All requested Rust mutations caught; source restored. Run cargo test transmog on the restored tree.', flush=True)


if __name__ == '__main__': main()
