#!/usr/bin/env bash
# Run the private kill-time harness once per class, then merge the five reports.
# Example: TTK_RUNS=9 bash scripts/ttk-parallel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test-results
run_dir="$(realpath "$(mktemp -d test-results/ttk-parallel-XXXXXX)")"
classes=(warrior mage assassin priest hunter)
pids=()
reports=()
for class in "${classes[@]}"; do
  TTK_CLASSES="$class" TTK_OUT="$run_dir/$class.json" bash scripts/ttk.sh >"$run_dir/$class.log" 2>&1 &
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
python3 scripts/merge_ttk.py --out docs/ttk-report.md "${reports[@]}"
echo "Merged class reports in docs/ttk-report.md (raw files: $run_dir)"
