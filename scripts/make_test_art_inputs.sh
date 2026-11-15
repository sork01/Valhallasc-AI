#!/usr/bin/env bash
# Generates the git-ignored inputs read by tests/character-hair-art.cjs and tests/female-torso-art.cjs.
#
#   bash scripts/make_test_art_inputs.sh            # both sets, into <repo>/test-results/
#   PYTHON=~/valhalla-py/bin/python3 bash scripts/make_test_art_inputs.sh hair
#   bash scripts/make_test_art_inputs.sh torso
#
# Needs the Python rig modules (make_warrior_sprites.py and the rest) from VALHALLA_TOOLS, plus
# numpy, Pillow and scipy. Without VALHALLA_TOOLS the exporters fall back to ../Valhalla/tools or
# /media/raid/valhallasc-data/valhalla-tools. Nothing here writes into client/ (the exporters only
# write candidates; --write is never passed).
#
# Layout produced:
#   test-results/turning-hair/assets/<stem>_hair-check.txt (+ candidate PNGs), 10 rigs
#   test-results/turning-hair/before/                       prior PNGs, written by the exporter
#   test-results/female-torso/assets/                       candidate female body/outfit sheets
#   test-results/female-torso/before/                       copy of client/assets/<class>_f_* (current files)
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
PY=${PYTHON:-python3}
what=${1:-all}
classes=(warrior mage assassin priest hunter)
stem_of() { if [ "$1" = warrior ]; then echo warrior_layered; else echo "$1"; fi; }

if [ "$what" = all ] || [ "$what" = hair ]; then
  for cls in "${classes[@]}"; do
    for female in "" "--female"; do
      echo "== hair: $cls ${female:-male}" >&2
      "$PY" scripts/export_character_body.py "$cls" $female --out "$ROOT/test-results/turning-hair/assets"
    done
  done
fi

if [ "$what" = all ] || [ "$what" = torso ]; then
  out="$ROOT/test-results/female-torso"
  mkdir -p "$out/assets" "$out/before"
  for cls in "${classes[@]}"; do
    echo "== torso: $cls" >&2
    "$PY" scripts/export_character_torso.py "$cls" --out "$out/assets"
    # Prior female files, exactly as client/assets holds them now (the suite serves them as /before/).
    stem=$(stem_of "$cls")_f
    "$PY" - "$stem" "$out/before" <<'PYEOF'
import json, shutil, sys
from pathlib import Path
stem, dest = sys.argv[1], Path(sys.argv[2])
assets = Path('client/assets')
meta = json.loads((assets / f'{stem}_sprites.txt').read_text())
names = [f'{stem}_sprites.txt', f'{stem}_bounds.txt']
for part, files in meta['parts'].items():
    if part == 'body' or part.startswith('armor_'):
        names += [files['png'], files['depth']]
for name in names:
    shutil.copyfile(assets / name, dest / name)
PYEOF
  done
fi

echo "done: ${what} inputs under $ROOT/test-results" >&2
