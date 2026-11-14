#!/usr/bin/env bash
# Run every tests/*.cjs through the bounded runner, JOBS at a time (default 4), at low priority.
# Each suite keeps its own 1.5 GiB / 1 CPU cap (scripts/test-touch-bounded.sh); nothing is raised.
# Results: $OUT/browser-results.tsv (name, exit code, seconds), logs in $OUT/browser/. Stop with: pkill -f test-browser-par
set -u
cd "$(dirname "$0")/.."
OUT=${1:-test-results/all-tests}; JOBS=${JOBS:-4}
export OUT PATH=/home/serveperry/.nvm/versions/node/v20.20.2/bin:$PATH
mkdir -p "$OUT/browser" "$OUT/browser-rc"; rm -f "$OUT"/browser-rc/*
run_one() {
  f=$1; b=$(basename "$f" .cjs); start=$(date +%s)
  PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright nice -n 15 bash scripts/test-touch-bounded.sh "$f" > "$OUT/browser/$b.log" 2>&1
  printf '%s\t%s\t%s\n' "$b" "$?" "$(( $(date +%s)-start ))" > "$OUT/browser-rc/$b.tsv"
}
export -f run_one
ls tests/*.cjs | grep -v -E '/(public-smoke|test-driver)\.cjs$' | xargs -P "$JOBS" -I{} bash -c 'run_one {}'
cat "$OUT"/browser-rc/*.tsv > "$OUT/browser-results.tsv"; echo DONE >> "$OUT/browser-results.tsv"
