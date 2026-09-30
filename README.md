# Valhalla Rumble — multiplayer

A Rust multiplayer server and a browser client for Windows and Linux, built from [Valhalla](https://github.com/sork01/valhalla-ai) (`../Valhalla` in the original workspace). The existing splash art, animated character creation, Warrior/Mage/Assassin sprites, equipment layers, isometric meadow, minimap, sound effects, and synthesised music are reused. This project is self-contained; the original game is unchanged.

Public repository: [sork01/Valhallasc-AI](https://github.com/sork01/Valhallasc-AI).

The client runs in current Firefox, Chrome, or Edge on either OS. There is no client build step and players do not need Rust. Open the server's URL in a browser. The server serves the client and accepts WebSocket connections on the same origin.

## Start

**Public client: [https://gunning.se/Valhallasc/](https://gunning.se/Valhallasc/)**. Open it from Windows or Linux, click the title, create a character, and join. You can play from outside the server's network; no VPN, downloads, or local server are needed.

The public game is managed by the `valhalla.service` user service. Apache handles HTTPS and proxies the client and WSS connection to Rust on the private Docker bridge address `172.18.0.1:8080`. The Rust port is not bound to the public interface.

```sh
systemctl --user status valhalla.service
systemctl --user restart valhalla.service
journalctl --user -u valhalla.service -n 50
```

For a **separate local/development installation**, use the instructions below. Do not start another world against the public service's database; use a separate `VALHALLA_DB` and port when developing alongside it.

Install stable Rust (1.88 or later), then run **from this folder**:

```sh
cargo run --release --locked
```

Open **http://localhost:8080/**. Create a character and join the world. Open another browser profile or private window to join as another player. A normal tab in the same profile resumes the same character and is refused while that character is already online.

On this machine a project-local Rust toolchain is installed under `.tools/`. Use:

```sh
bash scripts/cargo.sh run --release --locked
```

For friends on the same LAN, listen on all interfaces:

```sh
VALHALLA_BIND=0.0.0.0:8080 cargo run --release --locked
```

Players open `http://<server-LAN-address>:8080/`. Allow that port in the server's firewall. On PowerShell, set `$env:VALHALLA_BIND = '0.0.0.0:8080'` before running Cargo. The Rust server's bundled SQLite build needs a C compiler; the Linux build tools or Windows Visual Studio Build Tools provide it.

## Play

- Click ground to walk; click a slime to chase and keep attacking.
- WASD or arrow keys move relative to the screen. Space/J attacks or casts.
- Shift uses Assassin Shadowstep.
- I opens equipment; Esc opens the world menu. These stop your actions, but the shared world continues. Enemies can still hurt you.
- Enter focuses chat; Enter sends; Esc leaves the chat input. M toggles music.
- All equipment choices from the prototype are available as starter gear.
- New Character keeps your earlier character in **Esc → Your Characters**.

## Shared world and saves

The Rust server owns movement speed, map collision, AI, melee range/facing, attack cooldowns, swept projectile hits, damage, critical hits, equipment stats, XP, levels, gold pickups, deaths, and respawns. Clients send actions, never character positions, damage results, or rewards. Slimes are shared: a kill happens once, and the killer receives XP and owns its gold drop. This is cooperative PvE; players cannot damage each other.

The simulation runs at 20 ticks per second and sends snapshots at 10 per second. Clients interpolate positions, draw the original layered sprites, and display everyone on the minimap. Text chat is world-wide. Commands have payload/rate limits, inactive directional input expires, slow connections are dropped, and WebSocket origins are checked. The server allows up to 128 simultaneous connections; this is a guardrail, **not a tested MMO capacity claim**.

Characters are stored in `data/valhalla.sqlite` with SQLite WAL transactions. Saves run every five seconds, on disconnect, and at graceful shutdown. The browser retains a server-issued guest character key. Only the key hash is stored in SQLite; the name is not a credential. Reloading or reconnecting resumes the same character, including position, class, appearance, equipment, HP, level, XP, gold, and kill count. Reconnect happens automatically after a network/server interruption.

Keep the browser's site data and the database. Clearing site data loses access to guest characters; these are not SSO accounts and there is no account recovery or cross-device login yet. HTTP is appropriate for local development; put public deployments behind HTTPS so character keys travel over WSS. Different server URLs have separate character-key collections.

An abrupt process/machine failure can lose the last five seconds of progress. Slimes, projectiles, and uncollected drops are transient and reset when the server restarts. Persistent characters remain. Keep SQLite backups outside the public web root; use SQLite's backup command/API or stop the server before copying the database and its WAL files.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `VALHALLA_BIND` | `127.0.0.1:8080` | Listening address |
| `VALHALLA_DB` | `data/valhalla.sqlite` | Character database path |
| `VALHALLA_CLIENT_DIR` | `client` | Static client folder |
| `VALHALLA_ORIGIN` | Same as request host | Exact allowed browser origin behind a reverse proxy, e.g. `https://gunning.se` |
| `RUST_LOG` | `valhalla_server=info` | Logging filter |

`GET /health` reports status, protocol version, tick, online players, and connection capacity. `/ws` is the game connection. All other HTTP routes serve **only `client/`**, never server source or character data. Opening `client/index.html` directly or serving just static files does not start multiplayer.

## Deploy

`Dockerfile` builds the Rust server and packages the browser client. `deploy/compose.yaml` persists saves in a Docker volume:

```sh
docker compose -f deploy/compose.yaml up -d --build
```

This alternative Docker deployment binds port 8080 to loopback by default. It is separate from the installed host user service; stop the host service before using Docker with the same database. Adjust `deploy/apache.conf` to the Docker backend's reachable address if changing deployment method. The client derives its WebSocket URL from its page URL, so both root and subpath hosting work when the whole path is proxied with the prefix stripped.

The installed deployment uses `deploy/valhalla.service` under `~/.config/systemd/user/`, and includes `deploy/apache.conf` inside the main HTTPS virtual host in `/home/serveperry/webserver/000-default.conf` and the `php8site` container. `www.gunning.se/Valhallasc/` redirects to the canonical `gunning.se` origin. Apache and WebSocket configuration are scoped to this game. `deploy/install-public.py` performed the installation with a baseline check, backup, syntax validation, and graceful Apache reload; configuration backups live in gitignored `deploy/backups/`. Do not rerun that first-install script on an existing installation.

## Code and protocol

```text
client/          Browser UI, renderer, sprites, music, connection/reconnect layer
server/src/      Rust HTTP/WebSocket transport, world simulation, SQLite storage
world/map.txt    Shared obstacle and slime-spawn geometry exported from Valhalla
scripts/        Local Cargo wrapper and client map sync
tests/          Browser multiplayer integration test
deploy/         Compose, Apache and systemd examples
```

`world/map.txt` is the source of truth for spawn/collision geometry. After editing it, run `node scripts/sync-world.cjs`, then rebuild Rust (the map is bundled into the binary). Terrain shading and scenery drawing remain in the original renderer.

On WebSocket connection, send `{"type":"join","version":1,"token":null,"look":{"name":"Freya","class":"mage"}}`. The welcome packet returns an ID, a guest key for a newly created character, and a world snapshot. For resume, send the guest key with `look:null`; saved state takes precedence. Keep keys out of URLs and logs.

Subsequent messages: `input {dx,dy}`, `stop`, `move {x,y}`, `target {id}`, `attack {fx,fy}`, `dash {dx,dy}`, `equip {armor,weapon}`, `chat {text}`, `ping {nonce}`. Direction vectors are normalized on the server. `move` chooses a destination, not a teleport. Unknown command fields are refused. Server messages: `welcome`, `snapshot`, `event`, `chat`, `system`, `pong`, and `error`. See `server/src/model.rs` for the exact types.

The transport uses [Axum WebSockets](https://docs.rs/axum/0.8.9/axum/extract/ws/) and [Tower HTTP static serving](https://docs.rs/tower-http/0.6.11/tower_http/services/struct.ServeDir.html). Cargo.lock pins the resolved versions.

## Checks

```sh
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked
npm ci
npx playwright install chromium
npm run check
npm test
```

The integration test starts its own isolated Rust server/database and uses three independent browser clients. It covers character creation, visible remote players, movement replication, equipment, safe chat, invalid commands/keys, duplicate sessions, combat, loot, page reload, server restart/reconnect, and switching between saved characters. Screenshots and disposable databases are written under gitignored `test-results/`. The existing sibling Playwright installation was used for testing in this workspace via `NODE_PATH`; no runtime dependency on the sibling project is required.

`node tests/public-smoke.cjs` verifies the actual public HTTPS/WSS deployment with two browser clients. It also checks canonical redirects, private-file protection, chat, movement replication, and saved-character reload. It records only the test character IDs in `test-results/public-smoke-results.json`; remove those specific test characters from SQLite after both clients disconnect.

## Current scope

This is a playable **single-zone multiplayer foundation**, not a finished large-scale MMORPG. There are no accounts, quests, inventories beyond starter gear, trading, guilds, parties, PvP, multiple zones, distributed world servers, or native executable client packages yet. Everyone receives the zone's snapshots; interest management and load testing are needed before promising large populations. Movement follows direct goals with collision sliding, as in the original; there is no pathfinding around complex obstacles. Browser tests here run on Linux Chromium; Windows and Firefox builds have not been exercised in this environment.
