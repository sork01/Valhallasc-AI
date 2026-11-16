#!/usr/bin/env bash
# Client release (1.0.0 and later): validate, copy client/ into www/Valhalla/releases/<version>-<commit>, then point
# www/Valhalla/current at it. The server serves www/Valhalla/current (VALHALLA_CLIENT_DIR), so a client edit in this repo is
# NOT live until it is released with this script. Rollback: `bash scripts/release_client.sh --rollback <release folder name>`.
#   bash scripts/release_client.sh            validate, copy, verify, swap
#   bash scripts/release_client.sh --dry-run  validate only
#   bash scripts/release_client.sh --list     show the releases and which is current
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
root=${VALHALLA_RELEASE_ROOT:-/home/serveperry/webserver/www/Valhalla}
node=${NODE:-/home/serveperry/.nvm/versions/node/v20.20.2/bin/node}
cd -- "$repo"

swap() {   # atomic: a new link next to `current`, renamed over it
  ln -sfn "releases/$1" "$root/current.tmp" && mv -T "$root/current.tmp" "$root/current"
}
current() { readlink "$root/current" 2>/dev/null | sed 's#^releases/##' || true; }

case "${1:-}" in
  --list)
    echo "current: $(current)"; ls -1t "$root/releases" 2>/dev/null; exit 0 ;;
  --rollback)
    name=${2:?release folder name (see --list)}
    [ -d "$root/releases/$name" ] || { echo "no such release: $name" >&2; exit 1; }
    swap "$name"; echo "current is now $name (the running server serves it at once; no restart needed)"; exit 0 ;;
esac

version=$(sed -n 's#.*<p class="version">\([^<]*\)</p>.*#\1#p' client/index.html | head -1)
[ -n "$version" ] || { echo "no version label in client/index.html" >&2; exit 1; }
commit=$(git rev-parse --short=8 HEAD)
dirty=""; [ -z "$(git status --porcelain client)" ] || dirty="-dirty"
name="${version// /-}-${commit}${dirty}"

echo "== validating $version ($commit${dirty:+, uncommitted client changes})"
"$node" tests/whats-new-notes.cjs | tail -1
python3 scripts/build_swedish.py --check | tail -1
for f in client/*.js; do "$node" --check "$f"; done
[ "${1:-}" != "--dry-run" ] || { echo "dry run: ok"; exit 0; }
[ -z "$dirty" ] || { echo "client/ has uncommitted changes: commit them first (a release must be reproducible from a commit)" >&2; exit 1; }

mkdir -p "$root/releases"
dest="$root/releases/$name"
[ ! -e "$dest" ] || { echo "release $name already exists" >&2; exit 1; }
echo "== copying client/ -> $dest"
cp -a client "$dest.tmp"
diff -rq client "$dest.tmp" && echo "copy verified byte-for-byte"
mv "$dest.tmp" "$dest"
cp deploy/apache.conf "$root/apache.conf"       # Apache (in the container) includes this file; it needs a graceful reload when it changes
printf '%s\n' "$version" > "$root/VERSION"
git rev-parse HEAD > "$dest/.release-commit"
prev=$(current)
swap "$name"
echo "== released $name (previous: ${prev:-none}); rollback: bash scripts/release_client.sh --rollback ${prev:-<name>}"
echo "   old releases stay until you delete them (each is the size of client/)"
