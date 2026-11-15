#!/usr/bin/env bash
set -euo pipefail
# Never remove these limits on the shared production host. A failed run stays
# failed; do not automatically retry it with a larger or unlimited allowance.
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
node_binary=/home/serveperry/.nvm/versions/node/v20.20.2/bin/node
test_file=${1:-tests/touch-ui.cjs}
if (( $# )); then shift; fi
cd -- "$repo_dir"
# The default cap is 1.5 GiB. The real-art zone sprite suites (zones*-sprites-ui) need about 4 GiB for one renderer (verified: at 1.5 GiB even
# ZONES=1 dies with "Target crashed"; they pass at 4 GiB), so they get 4 GiB. BOUNDED_MEMORY_MAX overrides it for one run.
memory_max=${BOUNDED_MEMORY_MAX:-1536M}
case "$test_file" in *zones*-sprites-ui*) memory_max=${BOUNDED_MEMORY_MAX:-4096M} ;; esac
exec systemd-run --user --scope --quiet \
  --property=MemoryMax="$memory_max" --property=MemorySwapMax=0 \
  --property=CPUQuota=100% --property=TasksMax=128 \
  env NODE_PATH="${NODE_PATH:-$repo_dir/node_modules:/home/serveperry/webserver/www/dybase2/node_modules}" \
  VALHALLA_BINARY="${VALHALLA_BINARY:-$repo_dir/target/release/valhalla-server}" \
  timeout --signal=TERM --kill-after=10s 10m "$node_binary" "$test_file" "$@"
