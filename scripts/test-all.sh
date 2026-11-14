#!/usr/bin/env bash
# Run every test tier and collect logs under $OUT (default test-results/all-tests). Then: python3 scripts/testfail_report.py $OUT
#   tier=py      tests/*.py                      (light)
#   tier=cargo   cargo test --no-fail-fast       (~15 min, heavy: never during a browser tier)
#   tier=browser tests/*.cjs, one at a time through the 1.5 GiB bounded runner (hours; never raise the cap)
# Usage: bash scripts/test-all.sh py|cargo|browser [OUT]
set -u
cd "$(dirname "$0")/.."
tier=${1:?tier: py|cargo|browser}; OUT=${2:-test-results/all-tests}; mkdir -p "$OUT"
export PATH=/home/serveperry/.nvm/versions/node/v20.20.2/bin:$PATH
case $tier in
  py)
    : > "$OUT/py-results.tsv"
    for t in tests/*.py; do
      b=$(basename "$t" .py); timeout 1500 python3 "$t" > "$OUT/py-$b.log" 2>&1; printf '%s\t%s\n' "$b" "$?" >> "$OUT/py-results.tsv"
    done ;;
  cargo)
    bash scripts/cargo.sh test --no-fail-fast > "$OUT/cargo-test.log" 2>&1; echo "EXIT $?" >> "$OUT/cargo-test.log" ;;
  browser)
    mkdir -p "$OUT/browser"; : > "$OUT/browser-results.tsv"
    for f in tests/*.cjs; do
      b=$(basename "$f" .cjs)
      case $b in public-smoke) continue;; esac   # creates guest ids on the public service
      start=$(date +%s)
      if [ "$b" = test-driver ]; then timeout 600 node --test "$f" > "$OUT/browser/$b.log" 2>&1
      else PLAYWRIGHT_BROWSERS_PATH=/home/serveperry/.cache/ms-playwright bash scripts/test-touch-bounded.sh "$f" > "$OUT/browser/$b.log" 2>&1; fi
      printf '%s\t%s\t%s\n' "$b" "$?" "$(( $(date +%s)-start ))" >> "$OUT/browser-results.tsv"
    done; echo DONE >> "$OUT/browser-results.tsv" ;;
esac
