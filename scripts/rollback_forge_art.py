#!/usr/bin/env python3
"""Guarded rollback for The Chained Forge enemy art remake.
Default is a dry run; pass --apply to restore the backed-up atlases and manifest.
Refuses corrupt backups and refuses to overwrite unrelated Cathedral manifest changes.
"""
import argparse, hashlib, json, shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP = Path('/media/raid/valhallasc-data/forge-slime-original-20261111')
KINDS = ['cf_brute', 'cf_sentry', 'cf_crawler', 'cf_caster', 'cf_kettil', 'cf_ysolt', 'cf_hallgrim', 'cf_sigrun', 'cf_dagfinn', 'cf_thorbjorg', 'cf_ragnhild', 'cf_orm', 'cf_hildr', 'cf_eldmarr', 'cf_ingot']
ALIASES = ['es_foe_02', 'es_foe_04', 'es_foe_06', 'es_foe_08', 'es_foe_11', 'es_foe_15', 'es_foe_17', 'es_foe_18', 'es_foe_22', 'es_foe_25', 'ember_firelord']
OWNED = KINDS + ALIASES
EXPECTED_REL = ['client/assets/cathedral.txt'] + [f'client/assets/cathedral_{k}.png' for k in KINDS]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def without_forge(manifest: dict) -> dict:
    out = json.loads(json.dumps(manifest))
    out['kinds'] = [k for k in out.get('kinds', []) if k not in OWNED]
    for key in ('sprites', 'tops', 'frames', 'kindFrames'):
        if key in out:
            for k in OWNED:
                out[key].pop(k, None)
            if not out[key]:
                out.pop(key, None)
    return out


def verify_backup(backup_dir: Path) -> dict:
    manifest_path = backup_dir / 'manifest.txt'
    if not manifest_path.is_file():
        raise SystemExit(f'Refusing rollback: missing {manifest_path}')
    info = json.loads(manifest_path.read_text())
    files = info.get('files', {})
    if sorted(files) != sorted(EXPECTED_REL):
        raise SystemExit(f'Refusing rollback: expected 16 tracked files in backup, got {sorted(files)}')
    for rel, meta in files.items():
        src = backup_dir / rel
        if not src.is_file():
            raise SystemExit(f'Refusing rollback: missing backup file {src}')
        expected_sha = meta if isinstance(meta, str) else meta.get('sha256')
        if sha256(src) != expected_sha:
            raise SystemExit(f'Refusing rollback: checksum mismatch for {src}')
        if isinstance(meta, dict) and src.stat().st_size != meta.get('bytes'):
            raise SystemExit(f'Refusing rollback: size mismatch for {src}')
        if rel.endswith('.png'):
            with Image.open(src) as im:
                expected_size = [768, 480] if isinstance(meta, str) else meta.get('size')
                if list(im.size) != expected_size:
                    raise SystemExit(f'Refusing rollback: dimension mismatch for {src}')
    cat_manifest = json.loads((backup_dir / 'client/assets/cathedral.txt').read_text())
    for k in KINDS:
        if k not in cat_manifest.get('kinds', []) or k not in cat_manifest.get('sprites', {}):
            raise SystemExit(f'Refusing rollback: backup cathedral.txt missing {k}')
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--backup', type=Path, default=DEFAULT_BACKUP)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    info = verify_backup(args.backup)
    backup_cat = json.loads((args.backup / 'client/assets/cathedral.txt').read_text())
    live_cat_path = args.root / 'client/assets/cathedral.txt'
    if not live_cat_path.is_file():
        raise SystemExit(f'Refusing rollback: missing live manifest {live_cat_path}')
    live_cat = json.loads(live_cat_path.read_text())
    if without_forge(backup_cat) != without_forge(live_cat):
        raise SystemExit('Refusing rollback: unrelated Cathedral kinds changed in client/assets/cathedral.txt')

    for rel, meta in info['files'].items():
        expected_sha = meta if isinstance(meta, str) else meta['sha256']
        dst = args.root / rel
        status = 'match' if dst.is_file() and sha256(dst) == expected_sha else 'restore'
        print(f'{"APPLY" if args.apply else "DRY-RUN"} {status}: {rel} ({expected_sha[:12]})')
        if args.apply:
            shutil.copy2(args.backup / rel, dst)
    print('Rollback complete.' if args.apply else 'Dry run verified; pass --apply to restore.')


if __name__ == '__main__':
    main()
