#!/usr/bin/env bash
# Phase B of the 1.0.0 move (2026-11-16): the dev repo (server source, world data, scripts, tests, docs, raw art, tooling, .git, build output)
# moves from www/Valhallasc to the RAID; www/Valhalla keeps the released client AND the game database (data/), because the Apache container
# can only see www/ and vronline/inspect.php reads the database from there.
#
#   bash deploy/move-dev-to-raid.sh --check    changes nothing: prints the plan and every precondition
#   bash deploy/move-dev-to-raid.sh            does it (needs nobody online; stops the game for a few minutes; ~15 GB copy)
# Nothing is deleted: the old folder is renamed to Valhallasc.moved-<date> and removed by hand once you are happy.
# Rollback (before you delete the old folder): see the last lines this script prints.
set -euo pipefail
OLD=/media/raid/valhallasc-data/valhalla-dev
NEW=${NEW:-/media/raid/valhallasc-data/valhalla-dev}      # /media/raid itself is root-owned; valhallasc-data is ours
WWW=/home/serveperry/webserver/www
DATA=$WWW/Valhalla/data
UNIT=$HOME/.config/systemd/user/valhalla.service
MEM_OLD=/media/raid/claude-projects/-home-serveperry-webserver-www-Valhallasc
MEM_NEW=/media/raid/claude-projects/$(echo "$NEW" | sed 's#/#-#g')
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
say()  { printf '== %s\n' "$*"; }
fail() { printf 'ABORT: %s\n' "$*" >&2; exit 1; }

# ---- preconditions ------------------------------------------------------------------------------------------------
[ -d "$OLD/.git" ] || fail "$OLD is not the repo"
[ ! -e "$NEW" ] || fail "$NEW already exists"
[ -d /media/raid/valhallasc-data ] && mountpoint -q /media/raid || fail "the RAID is not mounted"
[ -d "$WWW/Valhalla/current" ] || fail "no released client yet: run scripts/release_client.sh first"
avail=$(df --output=avail -k /media/raid | tail -1); [ "$avail" -gt 40000000 ] || fail "less than 40 GB free on the RAID"
online=$(curl -s --max-time 5 http://172.18.0.1:8080/health | python3 -c 'import sys,json;print(json.load(sys.stdin)["online"])') || fail "health check failed"
[ "$online" = 0 ] || fail "$online real players are online"
pgrep -f "[c]argo (build|test)" >/dev/null && fail "cargo is running"
pgrep -f "[s]ync-world.cjs" >/dev/null && fail "sync-world is running"
[ -z "$(git -C "$OLD" status --porcelain -- client server world scripts tests deploy windows-client)" ] || fail "uncommitted changes in the repo: commit or stash them first"
say "worktrees to repair afterwards: $(git -C "$OLD" worktree list | wc -l)"
say "tracked files with the old path inside: $(git -C "$OLD" grep -l 'webserver/www/Valhallasc' | wc -l)"
cat <<EOF
== plan
 0. copy $OLD -> $NEW while the game runs (cp -a, then diff -rq without target and .git; git status must be clean in the copy)
 4. (still running) in the copy: replace the old path in tracked files, git worktree repair for every worktree, commit
 1. stop valhalla.service, back up the database (online + stopped copies), copy it to $DATA
 5. valhalla.service: WorkingDirectory, ExecStart and VALHALLA_DB follow the move; RequiresMountsFor=/media/raid
 6. vronline/inspect.php reads $DATA
 7. start the game, verify (health, binary path, database, client, public URLs)
 8. copy the Claude project memory to $MEM_NEW; rename $OLD to $OLD.moved-$STAMP (nothing is deleted)
EOF
[ "$CHECK" = 1 ] && { say "check only: nothing was changed"; exit 0; }

# ---- 0. copy the repo while the game still runs (it takes minutes; the database is copied again after the stop) ------
say "copying the repo to $NEW (a few minutes)"
cp -a "$OLD" "$NEW"
OLDHEAD=$(git -C "$OLD" rev-parse HEAD)
diff -rq --exclude=target --exclude=.git --exclude=data "$OLD" "$NEW" && say "copy verified (everything except target, .git and data)"
[ "$OLDHEAD" = "$(git -C "$NEW" rev-parse HEAD)" ] || fail "HEAD differs in the copy"
[ -z "$(git -C "$NEW" status --porcelain --untracked-files=no)" ] || fail "the copy is not clean"

# ---- 4. fix the copy -----------------------------------------------------------------------------------------------
say "replacing the old path in tracked files"
git -C "$NEW" grep -l 'webserver/www/Valhallasc' | grep -v '^deploy/apache.conf$' | while read -r f; do sed -i "s#/media/raid/valhallasc-data/valhalla-dev#$NEW#g" "$NEW/$f"; done
git -C "$NEW" commit -qam "The dev repo lives on the RAID ($NEW): paths follow the move

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" || true
say "repairing the worktrees"
wts=$(git -C "$NEW" worktree list --porcelain | awk '/^worktree /{print $2}' | grep -v "^$OLD\$" | grep -v "^$NEW\$" || true)
[ -z "$wts" ] || git -C "$NEW" worktree repair $wts
git -C "$NEW" worktree prune

# ---- 1. stop and back up -------------------------------------------------------------------------------------------
B=$OLD/deploy/backups/move-to-raid-$STAMP; mkdir -p "$B/stopped"
python3 - <<PY
import sqlite3
s=sqlite3.connect('file:$OLD/data/valhalla.sqlite?mode=ro',uri=True); d=sqlite3.connect('$B/valhalla.online.sqlite'); s.backup(d); d.close()
print('online backup', sqlite3.connect('$B/valhalla.online.sqlite').execute('pragma quick_check').fetchone())
PY
say "stopping the game"
systemctl --user stop valhalla.service
sleep 2
cp -a "$OLD"/data/valhalla.sqlite* "$B/stopped/"
mkdir -p "$DATA"
cp -a "$OLD"/data/. "$DATA"/
[ "$(git -C "$OLD" rev-parse HEAD)" = "$OLDHEAD" ] || fail "HEAD moved while copying"
python3 - <<PY
import sqlite3,sys
c=sqlite3.connect('$DATA/valhalla.sqlite'); r=c.execute('pragma quick_check').fetchone(); n=c.execute('select count(*) from characters').fetchone()
print('database in the new place', r, 'characters', n); sys.exit(0 if r==('ok',) else 1)
PY

# ---- 5. unit -------------------------------------------------------------------------------------------------------
say "updating valhalla.service"
cp "$UNIT" "$B/valhalla.service.before"
sed -i "s#^WorkingDirectory=.*#WorkingDirectory=$NEW#; s#^ExecStart=.*#ExecStart=$NEW/target/release/valhalla-server#; s#^Environment=VALHALLA_DB=.*#Environment=VALHALLA_DB=$DATA/valhalla.sqlite#" "$UNIT"
grep -q '^RequiresMountsFor=' "$UNIT" || sed -i 's#^After=network.target#After=network.target\nRequiresMountsFor=/media/raid#' "$UNIT"
systemctl --user daemon-reload

# ---- 6. vronline ---------------------------------------------------------------------------------------------------
say "vronline reads the database from $DATA"
cp "$WWW/vronline/inspect.php" "$B/inspect.php.before"
sed -i "s#\$game = dirname(__DIR__) . '/Valhallasc';#\$game = dirname(__DIR__) . '/Valhalla';#" "$WWW/vronline/inspect.php"
grep -n 'game = ' "$WWW/vronline/inspect.php"

# ---- 7. start and verify -------------------------------------------------------------------------------------------
say "starting the game"
systemctl --user start valhalla.service; sleep 8
PID=$(systemctl --user show valhalla.service -p MainPID --value)
echo "pid $PID  exe $(readlink /proc/$PID/exe)"
cmp "/proc/$PID/exe" "$NEW/target/release/valhalla-server" && echo "OK binary equals the one in the new place"
echo "health: $(curl -s --max-time 5 http://172.18.0.1:8080/health)"
echo "public: $(curl -s --max-time 8 https://gunning.se/Valhalla/health)"
echo "label : $(curl -s https://gunning.se/Valhalla/ | grep -o '<p class="version">[^<]*</p>')"
echo "vronline: $(curl -s -o /dev/null -w '%{http_code}' https://gunning.se/vronline/)"
journalctl --user -u valhalla.service --since "-2min" --no-pager | tail -4

# ---- 8. memory and the old folder ----------------------------------------------------------------------------------
if [ -d "$MEM_OLD" ] && [ ! -e "$MEM_NEW" ]; then cp -a "$MEM_OLD" "$MEM_NEW" && say "Claude project memory copied to $MEM_NEW"; fi
mv "$OLD" "$OLD.moved-$STAMP"
say "the old folder is now $OLD.moved-$STAMP (delete it by hand once you are happy)"
cat <<EOF
Rollback (only while the old folder exists):
  systemctl --user stop valhalla.service
  mv $OLD.moved-$STAMP $OLD
  git -C $OLD worktree repair \$(git -C $OLD worktree list --porcelain | awk '/^worktree /{print \$2}' | grep -v "^$OLD\$")
  cp $B/valhalla.service.before $UNIT && systemctl --user daemon-reload
  cp $B/inspect.php.before $WWW/vronline/inspect.php
  systemctl --user start valhalla.service
Work from now on in: cd $NEW   (start Claude Code there; its memory is in $MEM_NEW)
EOF
