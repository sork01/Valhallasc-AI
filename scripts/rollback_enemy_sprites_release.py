#!/usr/bin/env python3
"""Restore the complete accepted-enemy client release after validating every file."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rollback(root, backup, apply=False):
    manifest = json.loads((backup / 'manifest.json').read_text())
    restore = []
    # Validate the complete operation before writing any part of the client.
    for rel, info in manifest['files'].items():
        if not rel.startswith('client/') or '..' in Path(rel).parts:
            raise SystemExit(f'Refusing unsafe backup path: {rel}')
        target = root / rel
        current = target.read_bytes() if target.exists() else None
        if current is None or sha(current) != info['candidateSha256']:
            raise SystemExit(f'Refusing rollback: later or missing client change: {rel}')
        data = None
        if info['originalSha256'] is not None:
            source = backup / rel
            data = source.read_bytes()
            if len(data) != info['originalBytes'] or sha(data) != info['originalSha256']:
                raise SystemExit(f'Refusing rollback: corrupted original: {rel}')
        restore.append((target, data))
    if apply:
        for target, data in restore:
            if data is None:
                target.unlink()
            else:
                temporary = target.with_name(target.name + '.enemy-rollback-tmp')
                temporary.write_bytes(data)
                temporary.replace(target)
    print(f'{"Restored" if apply else "Verified dry run for"} {len(restore)} client files from {backup}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--backup', type=Path, default=Path('/media/raid/valhallasc-data/enemy-sprites-release-original-20261112'))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    rollback(args.root, args.backup, args.apply)
