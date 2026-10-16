#!/usr/bin/env bash
# ELITE-SOLO-TEST, one process per class at the same time. The party control has its own script, elite-party-parallel.sh.
# Example: ELITE_SOLO_SEEDS=2 bash scripts/elite-solo-parallel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test-results
run_dir="$(realpath "$(mktemp -d test-results/elite-solo-XXXXXX)")"
binary="$(bash scripts/cargo.sh test --no-run --message-format=json 2>/dev/null |
  python3 -c 'import sys,json
for line in sys.stdin:
    try: m = json.loads(line)
    except ValueError: continue
    if m.get("profile", {}).get("test") and m.get("executable"): print(m["executable"])' | tail -1)"
[[ -x "$binary" ]] || { echo "no test binary found" >&2; exit 1; }
classes=(warrior mage assassin priest hunter)
pids=()
names=()
for class in "${classes[@]}"; do
  ELITE_SOLO_CLASS="$class" "$binary" solo_elite_tests::no_lone --ignored --nocapture >"$run_dir/$class.log" 2>&1 &
  pids+=("$!"); names+=("$class")
done
failed=0
for index in "${!pids[@]}"; do
  if ! wait "${pids[$index]}"; then
    echo "${names[$index]} FAILED; see $run_dir/${names[$index]}.log" >&2
    failed=1
  else
    echo "${names[$index]} passed"
  fi
done
echo "Logs: $run_dir"
exit "$failed"
