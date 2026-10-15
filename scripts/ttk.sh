#!/usr/bin/env bash
# Kill-time report (TTK-HARNESS). Optimised test build, because the fights are CPU-bound simulation.
# Example: TTK_LEVELS=5,50 TTK_CLASSES=warrior,mage TTK_RUNS=9 TTK_OUT=/tmp/ttk.json bash scripts/ttk.sh
# Variables: TTK_LEVELS TTK_CLASSES TTK_SPREADS TTK_ROTATIONS TTK_FOES TTK_CONSUMABLES TTK_RUNS TTK_OUT (see server/src/world/ttk.rs).
set -euo pipefail
cd "$(dirname "$0")/.."
export CARGO_PROFILE_TEST_OPT_LEVEL=2 CARGO_PROFILE_TEST_DEBUG=0
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-target/ttk}"
exec bash scripts/cargo.sh test --offline ttk_report -- --ignored --nocapture
