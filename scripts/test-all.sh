#!/usr/bin/env bash
# Run every test tier and collect logs under $OUT (default test-results/all-tests). Then: python3 scripts/testfail_report.py $OUT
#   tier=py      tests/*.py                      (light)
#   tier=cargo   cargo test --no-fail-fast       (~15 min, heavy: never during a browser tier)
#   tier=browser tests/*.cjs, one at a time through the 1.5 GiB bounded runner (hours; never raise the cap)
# Usage: bash scripts/test-all.sh py|cargo|browser [OUT]
# py and browser leave out the design, artwork and seasonal suites when nothing they cover differs from BASE (origin/main):
# tests/suite-groups.txt, scripts/test_select.py. ALL=1 runs everything (do that before a release).
set -u
cd "$(dirname "$0")/.."
tier=${1:?tier: py|cargo|browser}; OUT=${2:-test-results/all-tests}; mkdir -p "$OUT"
export PATH=/home/serveperry/.nvm/versions/node/v20.20.2/bin:$PATH
case $tier in
  py)
    : > "$OUT/py-results.tsv"
    suites=$(python3 scripts/test_select.py py --results "$OUT/py-results.tsv") || exit 1
    for b in $suites; do
      t=tests/$b.py; timeout 1500 python3 "$t" > "$OUT/py-$b.log" 2>&1; printf '%s\t%s\n' "$b" "$?" >> "$OUT/py-results.tsv"
    done ;;
  cargo)
    bash scripts/cargo.sh test --no-fail-fast > "$OUT/cargo-test.log" 2>&1; echo "EXIT $?" >> "$OUT/cargo-test.log" ;;
  browser)
    mkdir -p "$OUT/browser"; : > "$OUT/browser-results.tsv"
    suites=$(python3 scripts/test_select.py browser --results "$OUT/browser-results.tsv") || exit 1
    for b in $suites; do
      f=tests/$b.cjs
      start=$(date +%s)
      if [ "$b" = test-driver ]; then timeout 600 node --test "$f" > "$OUT/browser/$b.log" 2>&1
      else PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright bash scripts/test-touch-bounded.sh "$f" > "$OUT/browser/$b.log" 2>&1; fi
      printf '%s\t%s\t%s\n' "$b" "$?" "$(( $(date +%s)-start ))" >> "$OUT/browser-results.tsv"
    done; echo DONE >> "$OUT/browser-results.tsv" ;;
esac
