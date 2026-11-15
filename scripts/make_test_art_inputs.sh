#!/usr/bin/env bash
# Generates the git-ignored inputs read by tests/character-hair-art.cjs and tests/female-torso-art.cjs.
#
#   bash scripts/make_test_art_inputs.sh            # both sets, into <repo>/test-results/
#   PYTHON=~/valhalla-py/bin/python3 bash scripts/make_test_art_inputs.sh hair
#   bash scripts/make_test_art_inputs.sh torso
#   MEASURE_ONLY=1 bash scripts/make_test_art_inputs.sh hair   # re-measure existing candidates (fast)
#
# Needs the Python rig modules (make_warrior_sprites.py and the rest) from VALHALLA_TOOLS, plus
# numpy, Pillow and scipy. Without VALHALLA_TOOLS the exporters fall back to ../Valhalla/tools or
# /media/raid/valhallasc-data/valhalla-tools. Nothing here writes into client/ (the exporters only
# write candidates; --write is never passed).
#
# Layout produced:
#   test-results/turning-hair/assets/<stem>_hair-check.txt (+ candidate PNGs), 10 rigs
#   test-results/turning-hair/before/                       pre-crown body/depth PNGs from git (f30c7004^)
#   test-results/female-torso/assets/                       candidate female body/outfit sheets
#   test-results/female-torso/before/                       body/outfit files from git at c5fb4749^ (pre-change)
set -euo pipefail
TORSO_BASE_REV=${TORSO_BASE_REV:-c5fb4749^}

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
PY=${PYTHON:-python3}
what=${1:-all}
classes=(warrior mage assassin priest hunter)
stem_of() { if [ "$1" = warrior ]; then echo warrior_layered; else echo "$1"; fi; }

# The crown test compares each new crown against the body it replaced. Beta 1.31.1 (f30c7004) installed the
# crowns, so the baseline is that commit's parent. Seeding it here matters: the exporter's own before/ copy
# comes from client/assets, which already holds the crowns, and the depth check then sees no change.
BASE_REV=${HAIR_BASE_REV:-f30c7004^}
if [ "$what" = all ] || [ "$what" = hair ]; then
  before="$ROOT/test-results/turning-hair/before"; mkdir -p "$before"
  for cls in "${classes[@]}"; do
    for female in "" "--female"; do
      stem=$(stem_of "$cls")
      if [ -n "$female" ]; then stem=${stem}_f; fi
      for name in "$stem"_body.png "$stem"_body_depth.png; do
        git show "$BASE_REV:client/assets/$name" > "$before/$name"
      done
    done
  done
  for cls in "${classes[@]}"; do
    for female in "" "--female"; do
      if [ -n "${MEASURE_ONLY:-}" ]; then
        echo "== hair measure: $cls ${female:-male}" >&2
        "$PY" scripts/export_character_body.py "$cls" $female --measure-only --out "$ROOT/test-results/turning-hair/assets"
      else
        echo "== hair: $cls ${female:-male}" >&2
        "$PY" scripts/export_character_body.py "$cls" $female --out "$ROOT/test-results/turning-hair/assets"
      fi
    done
  done
fi

if [ "$what" = all ] || [ "$what" = torso ]; then
  out=${TORSO_ART_DIR:-$ROOT/test-results/female-torso}
  mkdir -p "$out/assets" "$out/before"
  for cls in "${classes[@]}"; do
    echo "== torso: $cls" >&2
    "$PY" scripts/export_character_torso.py "$cls" --out "$out/assets"
    # The exporter writes only the rig's own body/armor sheets. The same metadata also lists progression-gear
    # armor (warrior_f_progression_armor_*.png) that it never produces; the suite loads every armor tier and
    # serves /after/ from this folder. Those files are not part of the torso change, so the candidate keeps
    # the current ones.
    stem=$(stem_of "$cls")_f
    "$PY" - "$stem" "$out/assets" <<'PYEOF'
import json, shutil, sys
from pathlib import Path
stem, dest = sys.argv[1], Path(sys.argv[2])
assets = Path('client/assets')
meta = json.loads((dest / f'{stem}_sprites.txt').read_text())
for part, files in meta['parts'].items():
    if part == 'body' or part.startswith('armor_'):
        for key in ('png', 'depth'):
            if not (dest / files[key]).exists():
                shutil.copyfile(assets / files[key], dest / files[key])
PYEOF
  done
  # The suite compares the candidate with /before/. The candidate equals client/assets now, so the baseline is the
  # female body/outfit as it was before the latest female chest change (c5fb4749, 30 percent reduction).
  # Taken from git, not client/assets, which already holds the change.
  "$PY" - "$TORSO_BASE_REV" "$out/before" <<'PYEOF'
import json, subprocess, sys
from pathlib import Path
rev, dest = sys.argv[1], Path(sys.argv[2])
def git(path):
    return subprocess.check_output(['git', 'show', f'{rev}:{path}'])
for cls in ['warrior_layered', 'mage', 'assassin', 'priest', 'hunter']:
    stem = cls + '_f'
    meta_bytes = git(f'client/assets/{stem}_sprites.txt')
    (dest / f'{stem}_sprites.txt').write_bytes(meta_bytes)
    (dest / f'{stem}_bounds.txt').write_bytes(git(f'client/assets/{stem}_bounds.txt'))
    for part, files in json.loads(meta_bytes)['parts'].items():
        if part == 'body' or part.startswith('armor_'):
            for key in ('png', 'depth'):
                (dest / files[key]).write_bytes(git(f'client/assets/{files[key]}'))
PYEOF
fi

echo "done: ${what} inputs under $ROOT/test-results" >&2
