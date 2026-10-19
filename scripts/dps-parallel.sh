#!/usr/bin/env bash
# Damage-per-second report (DPS-RUN): one process per class, five at once, then merge into docs/dps-report.md.
# Example: DPS_RUNS=5 bash scripts/dps-parallel.sh
# Variables: DPS_LEVELS (default 10,20 ... 90,99), DPS_RUNS (seeds per level, default 5), DPS_SECONDS (default 60),
# DPS_TEST_BINARY (a test binary to run instead of building one). See server/src/world/dps_tests.rs.
# One scratch copy of the test binary is kept (45 copies once filled the root SSD); the build uses target/ttk.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test-results
run_dir="$(realpath "$(mktemp -d test-results/dps-parallel-XXXXXX)")"
if [[ -z "${DPS_TEST_BINARY:-}" ]]; then
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
  DPS_TEST_BINARY="$run_dir/test-binary"
fi
classes=(warrior mage assassin priest hunter)
pids=()
reports=()
for class in "${classes[@]}"; do
  DPS_OUT="$run_dir/$class.json" "$DPS_TEST_BINARY" "dps_$class" --ignored --nocapture >"$run_dir/$class.log" 2>&1 &
  pids+=("$!")
  reports+=("$run_dir/$class.json")
done
failed=0
for index in "${!pids[@]}"; do
  if ! wait "${pids[$index]}"; then
    echo "${classes[$index]} failed; see $run_dir/${classes[$index]}.log" >&2
    failed=1
  fi
done
if (( failed )); then exit 1; fi
python3 scripts/merge_dps.py --out docs/dps-report.md "${reports[@]}"
echo "Merged class reports in docs/dps-report.md (raw files: $run_dir)"
