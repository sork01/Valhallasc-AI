#!/usr/bin/env python3
"""Restore the Flooded Cloister art (eight atlases) from an external hash-verified backup.

Dry run by default; --apply restores. The shared `client/assets/cathedral.txt` is NOT replaced as a file (138 other kinds
live in it, and the Reliquary/Nave work edits it too): only the eight `sprites` and `tops` entries of this zone's kinds
are put back, everything else in the manifest is kept exactly as it is. No server/DB action.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

DEFAULT_BACKUP = '/media/raid/valhallasc-data/cloister-slime-original-20261103'
MANIFEST = 'client/assets/cathedral.txt'


def atomic_write(dest, data):
    fd, temp = tempfile.mkstemp(prefix='.cloister-restore-', dir=dest.parent)
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


def restore(target, backup, apply=False):
    target, backup = Path(target).resolve(), Path(backup).resolve()
    info = json.loads((backup/'manifest.txt').read_text())
    kinds = info['kinds']
    assert set(info['files']) == {f'client/assets/cathedral_{k}.png' for k in kinds}, 'backup file list does not match its kinds'
    staged = []
    # Validate every source, destination and the shared manifest before touching any file.
    for name, digest in info['files'].items():
        data = (backup/name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, 'Corrupt backup: '+name
        dest = target/name
        assert dest.is_file() and not dest.is_symlink(), 'Missing/linked target: '+name
        staged.append((dest, data, digest))
    live_path = target/MANIFEST
    assert live_path.is_file() and not live_path.is_symlink(), 'Missing/linked target: '+MANIFEST
    live = json.loads(live_path.read_text())
    for k in kinds:
        assert k in live['sprites'] and k in live['tops'], 'Target manifest lacks '+k
        assert k in info['oldSprites'] and k in info['oldTops'], 'Backup lacks old entries for '+k
    merged = json.loads(json.dumps(live))
    for k in kinds:
        merged['sprites'][k] = info['oldSprites'][k]
        merged['tops'][k] = info['oldTops'][k]
    for dest, data, digest in staged:
        print(('Restore ' if apply else 'Would restore ')+str(dest))
    print(('Merge ' if apply else 'Would merge ')+f'{len(kinds)} sprites/tops entries into {live_path} (all other entries kept)')
    if apply:
        for dest, data, digest in staged:
            atomic_write(dest, data)
            assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest
        atomic_write(live_path, (json.dumps(merged, indent=2)+'\n').encode())
        check = json.loads(live_path.read_text())
        assert all(check['sprites'][k] == info['oldSprites'][k] and check['tops'][k] == info['oldTops'][k] for k in kinds)
    print('Restored and verified eight atlases plus their manifest entries.' if apply else 'Backup verified. Add --apply to restore.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--backup', type=Path, default=Path(DEFAULT_BACKUP))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    restore(args.target, args.backup, args.apply)
