#!/usr/bin/env bash
# Dungeon control: a party of five must beat every pack and boss. Sharded by dungeon, one process per core.
# Example: DUNGEON_SOLO_SEEDS=2 DUNGEON_SOLO_FAIL_FAST=0 bash scripts/dungeon-party-parallel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test-results
run_dir="$(realpath "$(mktemp -d test-results/dungeon-party-XXXXXX)")"
binary="$(bash scripts/cargo.sh test --no-run --message-format=json 2>/dev/null |
  python3 -c 'import sys,json
for line in sys.stdin:
    try: m = json.loads(line)
    except ValueError: continue
    if m.get("profile", {}).get("test") and m.get("executable"): print(m["executable"])' | tail -1)"
[[ -x "$binary" ]] || { echo "no test binary found" >&2; exit 1; }
shards="${DUNGEON_PARTY_SHARDS:-$(nproc)}"
pids=()
for ((i = 0; i < shards; i++)); do
  DUNGEON_PARTY_SHARD="$i/$shards" "$binary" dungeon_solo_tests::a_party_of_five --ignored --nocapture >"$run_dir/shard$i.log" 2>&1 &
  pids+=("$!")
done
failed=0
for index in "${!pids[@]}"; do wait "${pids[$index]}" || failed=1; done
echo "Logs: $run_dir"
grep -h "PARTY OF FIVE CANNOT WIN" "$run_dir"/shard*.log || echo "A party of five beat every pack and boss."
exit "$failed"
