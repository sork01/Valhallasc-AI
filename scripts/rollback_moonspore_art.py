#!/usr/bin/env python3
"""Restore the eight Moonspore Canopy art files from an external hash-verified backup (default: the original cel-shaded art that was live before this redo).

Dry run by default. --apply makes the requested restore; no server/DB action.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import tempfile

DEFAULT_BACKUP = '/media/raid/valhallasc-data/moonspore-slime-original-20261104'  # the original cel-shaded art, live before the slime-style redo


def restore(target, backup, apply=False):
    target, backup = Path(target).resolve(), Path(backup).resolve()
    manifest = json.loads((backup / 'manifest.txt').read_text())
    expected = {'client/assets/moonspore.txt'} | {
        f'client/assets/moonspore_{k}.png' for k in ('glowcapgrazer', 'silkwing', 'rootlurker', 'lanternwraith', 'mireheart', 'silverwidow', 'nightbloom')
    }
    assert set(manifest['files']) == expected, 'Unexpected backup file set'
    staged = []
    # Validate every source and destination before touching any file.
    for name, digest in manifest['files'].items():
        source, dest = backup / name, target / name
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, 'Corrupt backup: ' + name
        assert dest.is_file() and not dest.is_symlink(), 'Missing/linked target: ' + name
        staged.append((dest, data, digest))
    for dest, data, digest in staged:
        print(('Restore ' if apply else 'Would restore ') + str(dest))
        if apply:
            fd, temp = tempfile.mkstemp(prefix='.moonspore-restore-', dir=dest.parent)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                os.chmod(temp, dest.stat().st_mode & 0o777)
                os.replace(temp, dest)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest
    print('Restored and verified eight files.' if apply else 'Backup verified. Add --apply to restore.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--backup', type=Path, default=Path(DEFAULT_BACKUP))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    restore(args.target, args.backup, args.apply)
