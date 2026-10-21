#!/bin/bash
# Build the Windows installer on Linux. Heavy files live on the RAID (the root SSD is small):
#   bash build.sh        -> /media/raid/valhallasc-data/windows-client-build/Valhalla-Rumble-Setup-<ver>.exe
# electron-builder packs win-unpacked; its NSIS target needs wine, so installer.nsi is compiled by hand.
set -e
export PATH=/home/serveperry/.nvm/versions/node/v20.20.2/bin:$PATH
HERE=$(cd "$(dirname "$0")" && pwd)
B=/media/raid/valhallasc-data/windows-client-build
export npm_config_cache=$B/cache/npm ELECTRON_CACHE=$B/cache/electron ELECTRON_BUILDER_CACHE=$B/cache/builder
mkdir -p "$B/src"; cp -a "$HERE"/. "$B/src/"; cd "$B/src"
[ -d node_modules ] || npm install --no-audit --no-fund
rm -rf dist; npx electron-builder --win dir --x64
VER=$(node -p "require('./package.json').version")
N=$ELECTRON_BUILDER_CACHE/nsis/nsis-3.0.4.1
NSISDIR=$N "$N/linux/makensis" -V2 -DVERSION="$VER" -DSRC="$B/src/dist/win-unpacked" -DICON="$B/src/build/icon.ico" -DOUT="$B/Valhalla-Rumble-Setup-$VER.exe" installer.nsi
ls -l "$B/Valhalla-Rumble-Setup-$VER.exe"
