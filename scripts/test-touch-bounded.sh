#!/usr/bin/env bash
set -euo pipefail
# Never remove these limits on the shared production host. A failed run stays
# failed; do not automatically retry it with a larger or unlimited allowance.
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
node_binary=/home/serveperry/.nvm/versions/node/v20.20.2/bin/node
test_file=${1:-tests/touch-ui.cjs}
if (( $# )); then shift; fi
cd -- "$repo_dir"
exec systemd-run --user --scope --quiet \
  --property=MemoryMax=1536M --property=MemorySwapMax=0 \
  --property=CPUQuota=100% --property=TasksMax=128 \
  env NODE_PATH="${NODE_PATH:-$repo_dir/node_modules:/home/serveperry/webserver/www/dybase2/node_modules}" \
  VALHALLA_BINARY="${VALHALLA_BINARY:-$repo_dir/target/release/valhalla-server}" \
  timeout --signal=TERM --kill-after=10s 10m "$node_binary" "$test_file" "$@"
