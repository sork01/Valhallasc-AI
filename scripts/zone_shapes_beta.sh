#!/usr/bin/env bash
# Publish or withdraw the zone-shape pilot at https://gunning.se/Valhalla/ (docs/zone-shapes.md). It used /Valhallasc-shapes/ until
# 2026-11-07 (owner: run it in /Valhalla; the old single-player Valhalla was removed); that path redirects here.
#   bash scripts/zone_shapes_beta.sh on|off|status
# `on` appends a marked block to the LIVE checkout's deploy/apache.conf (Apache includes it), checks the configuration with
# configtest and only then reloads gracefully; `off` removes the block the same way. The pilot server itself (port 8081, own
# database copy) is a separate process; the live game on 8080 is never touched.
set -euo pipefail
CONF=/home/serveperry/webserver/www/Valhallasc/deploy/apache.conf
BEGIN='# BEGIN zone-shapes-pilot'
END='# END zone-shapes-pilot'
block() { cat <<'EOF'
# BEGIN zone-shapes-pilot
# Zone-shape pilot (feat/zone-shapes): second game server on the Docker bridge, port 8081, own database copy.
RedirectMatch 302 ^/Valhalla$ /Valhalla/
RedirectMatch 301 ^/Valhallasc-shapes(/.*)?$ /Valhalla/
ProxyPass /Valhalla/ws ws://172.18.0.1:8081/ws disablereuse=on
ProxyPassReverse /Valhalla/ws ws://172.18.0.1:8081/ws
ProxyPass /Valhalla/ http://172.18.0.1:8081/ disablereuse=on
ProxyPassReverse /Valhalla/ http://172.18.0.1:8081/

<Location /Valhalla/>
  Header always set Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' wss://gunning.se; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
</Location>
# END zone-shapes-pilot
EOF
}
reload() { docker exec php8site apache2ctl configtest && docker exec php8site apache2ctl graceful; }
case "${1:-status}" in
  on)
    cp "$CONF" "$CONF.pre-shapes"
    if grep -qF "$BEGIN" "$CONF"; then sed -i "/^$BEGIN\$/,/^$END\$/d" "$CONF"; sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CONF"; fi     # re-publish: the current block replaces an older one
    { echo; block; } >> "$CONF"
    if ! reload; then cp "$CONF.pre-shapes" "$CONF"; reload || true; echo "configtest failed: restored" >&2; exit 1; fi
    echo "on: https://gunning.se/Valhalla/" ;;
  off)
    grep -qF "$BEGIN" "$CONF" || { echo "already off"; exit 0; }
    cp "$CONF" "$CONF.pre-shapes"
    sed -i "/^$BEGIN\$/,/^$END\$/d" "$CONF"
    sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CONF"
    reload; echo off ;;
  status)
    grep -qF "$BEGIN" "$CONF" && echo on || echo off
    curl -s -o /dev/null -w "pilot server: %{http_code}\n" http://172.18.0.1:8081/health || true ;;
esac
