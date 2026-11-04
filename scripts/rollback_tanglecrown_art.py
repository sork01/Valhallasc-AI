#!/usr/bin/env python3
"""Restore the six Tanglecrown enemy atlases and the zone manifest from an external hash-verified backup (default: the original cel-shaded art that was live before the slime-style redo).

Dry run by default. --apply makes the requested restore; no server/DB action. The three NPC entries (`tangle_warden`,
`tangle_scholar`, `tangle_travel`) share the manifest: the restore refuses if the live manifest's NPC entries differ from the backup's.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import tempfile

DEFAULT_BACKUP = '/media/raid/valhallasc-data/tanglecrown-slime-original-20261104'  # the original cel-shaded art, live before the slime-style redo
ENEMIES = ('jadeanaconda', 'crownjaguar', 'orchidmantis', 'canopyglider', 'poolcaiman', 'drumgorilla')
VILLAGERS = ('tangle_warden', 'tangle_scholar', 'tangle_travel')


def restore(target, backup, apply=False):
    target, backup = Path(target).resolve(), Path(backup).resolve()
    manifest = json.loads((backup / 'manifest.txt').read_text())
    expected = {'client/assets/tanglecrown.txt'} | {f'client/assets/tanglecrown_{k}.png' for k in ENEMIES}
    assert set(manifest['files']) == expected, 'Unexpected backup file set'
    staged = []
    # Validate every source and destination before touching any file.
    for name, digest in manifest['files'].items():
        source, dest = backup / name, target / name
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, 'Corrupt backup: ' + name
        assert dest.is_file() and not dest.is_symlink(), 'Missing/linked target: ' + name
        staged.append((dest, data, digest))
    old = json.loads((backup / 'client/assets/tanglecrown.txt').read_text())
    live = json.loads((target / 'client/assets/tanglecrown.txt').read_text())
    for k in VILLAGERS:
        assert live['sprites'].get(k) == old['sprites'].get(k) and live['tops'].get(k) == old['tops'].get(k), 'NPC entry changed since the backup: ' + k
    for dest, data, digest in staged:
        print(('Restore ' if apply else 'Would restore ') + str(dest))
        if apply:
            fd, temp = tempfile.mkstemp(prefix='.tanglecrown-restore-', dir=dest.parent)
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
    print('Restored and verified seven files.' if apply else 'Backup verified. Add --apply to restore.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--backup', type=Path, default=Path(DEFAULT_BACKUP))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    restore(args.target, args.backup, args.apply)
