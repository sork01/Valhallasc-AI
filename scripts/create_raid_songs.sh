#!/bin/sh
# Chained Forge / Eldmarr editable scores, created through the dybase2 MCP.
set -eu
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node "$(dirname "$0")/raid_songs.mjs" "$@"
