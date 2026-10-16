#!/usr/bin/env bash
# ELITE-SOLO-TEST party control in shards, one per core: every group elite must die to a party of its recommended size.
# Example: ELITE_SOLO_SEEDS=2 ELITE_PARTY_RARITY=epic bash scripts/elite-party-parallel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p test-results
run_dir="$(realpath "$(mktemp -d test-results/elite-party-XXXXXX)")"
binary="$(bash scripts/cargo.sh test --no-run --message-format=json 2>/dev/null |
  python3 -c 'import sys,json
for line in sys.stdin:
    try: m = json.loads(line)
    except ValueError: continue
    if m.get("profile", {}).get("test") and m.get("executable"): print(m["executable"])' | tail -1)"
[[ -x "$binary" ]] || { echo "no test binary found" >&2; exit 1; }
shards="${ELITE_PARTY_SHARDS:-$(nproc)}"
pids=()
for ((i = 0; i < shards; i++)); do
  ELITE_PARTY_SHARD="$i/$shards" "$binary" solo_elite_tests::a_party --ignored --nocapture >"$run_dir/shard$i.log" 2>&1 &
  pids+=("$!")
done
failed=0
for index in "${!pids[@]}"; do
  wait "${pids[$index]}" || failed=1
done
echo "Logs: $run_dir"
grep -h "PARTY CANNOT WIN" "$run_dir"/shard*.log || echo "Every group elite died to a party of its recommended size."
exit "$failed"
