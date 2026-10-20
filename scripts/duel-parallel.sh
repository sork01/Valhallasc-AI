#!/usr/bin/env bash
# Duel matrix (PVP-DUEL-MATRIX): one process per level, a few at once, then merge into docs/duel-report.md.
# Example: DUEL_RUNS=4 DUEL_JOBS=3 bash scripts/duel-parallel.sh
# Variables: DUEL_LEVELS (default 10,20 ... 90,99), DUEL_RUNS (seeds per order, default 4), DUEL_PAIRS (e.g. warrior-mage),
# DUEL_JOBS (processes at once, default 3), DUEL_TEST_BINARY (a test binary to run instead of building one),
# DUEL_OUT_MD (default docs/duel-report.md). See server/src/world/duel_tests.rs.
# One scratch copy of the test binary is kept (45 copies once filled the root SSD); the build uses target/ttk.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test-results
run_dir="$(realpath "$(mktemp -d test-results/duel-parallel-XXXXXX)")"
if [[ -z "${DUEL_TEST_BINARY:-}" ]]; then
  export CARGO_PROFILE_TEST_OPT_LEVEL=2 CARGO_PROFILE_TEST_DEBUG=0
  export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target/ttk}"
  built="$(bash scripts/cargo.sh test --offline --no-run --message-format=json | python3 -c '
import json, sys
for line in sys.stdin:
    try:
        m = json.loads(line)
    except ValueError:
        continue
    if m.get("reason") == "compiler-artifact" and m.get("executable") and m["target"]["name"] == "valhalla-server" and m["profile"]["test"]:
        print(m["executable"])
')"
  built="$(echo "$built" | tail -1)"
  cp "$built" "$run_dir/test-binary"
  DUEL_TEST_BINARY="$run_dir/test-binary"
fi
IFS=',' read -r -a levels <<< "${DUEL_LEVELS:-10,20,30,40,50,60,70,80,90,99}"
export DUEL_TEST_BINARY run_dir
run_level() {
  local level="$1"
  DUEL_LEVELS="$level" DUEL_OUT="$run_dir/level$level.json" "$DUEL_TEST_BINARY" duel_matrix --ignored --nocapture >"$run_dir/level$level.log" 2>&1
}
export -f run_level
printf '%s\n' "${levels[@]}" | xargs -P "${DUEL_JOBS:-3}" -I{} bash -c 'run_level {} || { echo "level {} failed; see $run_dir/level{}.log" >&2; exit 255; }'
python3 scripts/merge_duel.py --out "${DUEL_OUT_MD:-docs/duel-report.md}" "$run_dir"/level*.json
echo "Merged duel reports in ${DUEL_OUT_MD:-docs/duel-report.md} (raw files: $run_dir)"
