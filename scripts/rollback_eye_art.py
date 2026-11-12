#!/usr/bin/env python3
"""Restore the six Eye Below enemy atlases and the zone manifest from an external hash-verified backup (default: the original cel-shaded art that was live before the slime-style redo).

Dry run by default. --apply makes the requested restore; no server/DB action. The NPC entries share the manifest: the restore refuses if unrelated manifest data has changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import tempfile

DEFAULT_BACKUP = '/media/raid/valhallasc-data/eye-slime-original-20261111'  # the original cel-shaded art, live before the slime-style redo
ENEMIES = ('eye_drifter','eye_adept','eye_lurker','eye_lenswarden','eye_undertide','eye_unblinking')


def restore(target, backup, apply=False):
    target, backup = Path(target).resolve(), Path(backup).resolve()
    manifest = json.loads((backup / 'manifest.txt').read_text())
    expected = {'client/assets/cathedral.txt'} | {f'client/assets/cathedral_{k}.png' for k in ENEMIES}
    assert set(manifest['files']) == expected, 'Unexpected backup file set'
    staged = []
    # Validate every source and destination before touching any file.
    for name, digest in manifest['files'].items():
        source, dest = backup / name, target / name
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, 'Corrupt backup: ' + name
        assert dest.is_file() and not dest.is_symlink(), 'Missing/linked target: ' + name
        staged.append((dest, data, digest))
    old = json.loads((backup / 'client/assets/cathedral.txt').read_text())
    live = json.loads((target / 'client/assets/cathedral.txt').read_text())
    # Restoring the whole manifest must never discard unrelated changes.
    def unrelated(meta):
        meta = json.loads(json.dumps(meta))
        for field in ('sprites', 'tops', 'kindFrames'):
            if field in meta:
                for kind in ENEMIES:
                    meta[field].pop(kind, None)
                if field == 'kindFrames' and not meta[field]:
                    meta.pop(field)
        return meta
    assert unrelated(live) == unrelated(old), 'Unrelated manifest data changed since the backup'
    for dest, data, digest in staged:
        print(('Restore ' if apply else 'Would restore ') + str(dest))
        if apply:
            fd, temp = tempfile.mkstemp(prefix='.eye-restore-', dir=dest.parent)
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
