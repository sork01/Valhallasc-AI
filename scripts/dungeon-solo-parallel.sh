#!/usr/bin/env bash
# Dungeon rules: a pack kills a lone player, a boss kills a lone player (a single mob is only reported). One process per class.
# Example: DUNGEON_SOLO_SEEDS=2 bash scripts/dungeon-solo-parallel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test-results
run_dir="$(realpath "$(mktemp -d test-results/dungeon-solo-XXXXXX)")"
binary="$(bash scripts/cargo.sh test --no-run --message-format=json 2>/dev/null |
  python3 -c 'import sys,json
for line in sys.stdin:
    try: m = json.loads(line)
    except ValueError: continue
    if m.get("profile", {}).get("test") and m.get("executable"): print(m["executable"])' | tail -1)"
[[ -x "$binary" ]] || { echo "no test binary found" >&2; exit 1; }
classes=(warrior mage assassin priest hunter)
pids=()
for class in "${classes[@]}"; do
  DUNGEON_SOLO_CLASS="$class" "$binary" dungeon_solo_tests:: --ignored --nocapture >"$run_dir/$class.log" 2>&1 &
  pids+=("$!")
done
failed=0
for index in "${!pids[@]}"; do
  wait "${pids[$index]}" || { echo "${classes[$index]}: a rule failed; see $run_dir/${classes[$index]}.log" >&2; failed=1; }
done
echo "Logs: $run_dir"
for marker in "LONE PLAYER SURVIVED A PACK" "LONE PLAYER SURVIVED A BOSS"; do
  echo "$marker: $(grep -h "$marker" "$run_dir"/*.log | wc -l)"
done
exit "$failed"
