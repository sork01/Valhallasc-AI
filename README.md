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

- Click ground to walk; click an enemy to chase and keep attacking.
- Players can walk and Shadowstep through other players, NPCs, and enemies. Enemies stop at least one cell away from living players and move aside when a player enters that space; enemies also avoid stacking with each other.
- **Ironhide Beetles** roam the outer meadow: 240 HP, 22 base damage, fast horn charges, 32 XP and 10 gold. Their steel shells and bronze horns distinguish them from slimes.
- **King Slime** has 600 HP, 30 base damage, faster pursuit and charge recovery, and rewards 75 XP and 30 gold. Only one king can be alive at a time. It first appears after a random 5–10 minutes of server uptime, then waits another random 5–10 minutes after each defeat. Its location is randomly chosen from two meadow spawn points, and the world receives an announcement. Dodge its windup or fight together.
- **Enemy levels:** every enemy has a level, shown as `Lv N` beside its name when you are near or targeting it (grey if far below you, orange from three levels above you, red from five). Each kind has a default level (Green Slime 2, Blue and Pink 3, Golden 4, Ironhide 5, King 6, Cinder Wisp 5, Magma Spider 7, Ash Wraith 8, Basalt Golem 10) and every individual enemy rolls a whole level within **±2** of it, never below 1. A new roll happens at each respawn. Per level away from the default an enemy's health and damage change by 12 %, its XP by 15 % and its gold by 10 %, so a level-7 Ironhide (default 5) has 24 % more health and damage, 30 % more XP and 20 % more gold.
- **Emberfall Crags** is a second zone for levels **5–10**, reached through the **Emberfall Gate** at the north end of Greenmeadow's dirt road. Walk between its two stone posts into the glowing plane and the server moves you to the Crags' camp; the Meadow Gate there takes you back. The zone is saved with your character, so you resume where you logged out, and dying in the Crags brings you back at the Crags' camp. You only see and fight enemies, players, drops and combat events in your own zone. The Crags are a 96×96 field of basalt, charred trees and obsidian spires cut by four lava rivers, each with a single ford, so the trail zigzags north through four bands: **Cinder Wisps** (8, level 5, fast fire spirits, 280 HP, 34 damage, 80 XP, 18 gold, Ember Core), **Magma Spiders** (7, level 7, 420 HP, 42 damage, 120 XP, 26 gold, Magma Fang), **Ash Wraiths** (6, level 8, scythe-wielding specters, 520 HP, 52 damage, 170 XP, 36 gold, Ash Veil) and **Basalt Golems** (5, level 10, slow, 1100 HP, 64 damage, 280 XP, 55 gold, Basalt Heart); all numbers are for a default-level monster. They drop rare gear more often than the meadow (8 %, 10 %, 14 % and 20 %) from the same pool of upgrades. Lava blocks movement. Warriors, mages and assassins at level 1 can enter, but the zone is deliberately dangerous.
- Leveling requires `round(160 × level^1.35)` XP per level, four times the original threshold (160 XP for level 1). Existing levels and earned XP are preserved.
- WASD or arrow keys move relative to the screen. Space/J attacks or casts.
- The bottom skillbar has twelve slots, keyed **1–9, 0, - and =**, or click/tap. **K** opens Skills: select a slot and an ability, or drag to assign and swap. Layouts save per guest character in this browser. Each class learns one new skill at every even level up to 20 (ten per class; `world/skills.txt` is the catalogue, `node scripts/sync-world.cjs` generates `client/skills.js`, rebuild Rust). A newly learned skill goes into the first empty slot. Cooldowns, buffs, damage and unlock levels are all decided by the server (`skill {id,fx,fy}`). A level-up shows a pillar of light, rays, rings and sparks, a screen flash and shake, a fanfare and a banner naming the new skill; `prefers-reduced-motion` drops the flash, shake and spin.
- Shift uses Assassin Shadowstep.
- E opens the character and equipment window beside your bags, with Headgear, Shoulders, Chest, Pants, Gloves, Hands, Necklace and two Accessories. Existing armor fills Chest and weapons fill Hands; other slots start empty and accept rare universal loot. Gear bonuses are authoritative, and equipped accessory copies are protected from sale. Esc opens the world menu. These stop your actions, but the shared world continues. Enemies can still hurt you.
- Chest and Hands retain the existing character artwork. The additional equipment slots currently change stats without adding new sprite layers.
- **Attributes:** Every level after level 1 grants three permanent training points in the E character window. Existing characters receive points for their earned levels. Strength adds 0.2 defense and 2 attack for warriors (0.5 for other classes); Agility adds 0.5 percentage points of critical chance and 2 attack for assassins (0.5 otherwise); Intellect adds 1% recovery reduction and 2 attack for mages (0.5 otherwise). Stamina adds 8 maximum/current HP, preserving existing damage. Dexterity adds 0.5 percentage points of dodge chance; Accuracy adds 0.5 percentage points of hit chance, starting at 90%. Crit caps at 60%, dodge at 35%, hit at 100%, and recovery reduction at 30%; attack recovery never undercuts the attack animation. Dodge avoids an entire incoming enemy hit. Missed attacks deal no damage and grant no rewards. Training is validated and saved immediately by Rust; all derived combat values are authoritative. The primary-stat/class choices draw on [Blizzard’s stat overview](https://worldofwarcraft.blizzard.com/en-us/news/1550772) and [WoW’s game manual](https://bnetcmsus-a.akamaihd.net/cms/template_resource/263A8NGR8HLZ1556919642368.pdf); the training budget and numerical effects are tuned for this game.
- The quest tracker on the right lists every active quest with gold titles, indented objective counts and green completed objectives or turn-in prompts. Collapse it with the header toggle; Q or a quest title opens the journal. The journal's Track action places a quest first.
- **B** or **I** opens bags. Items use icon cells with rarity borders, stack counts and hover/focus tooltips. Right-click or double-click gear to equip, drag it onto a matching character slot, and right-click equipped gear or drag it into a bag to unequip. Drag bag cells to reorder, search across all bags, or use Sort. Equipped copies leave the bag grid; extra copies stay stacked. Bag layouts save per guest character in this browser. The server enforces a 16-slot backpack and four expansion-bag slots. Linden sells only six-slot Linen Satchels for 500 gold each, fitted immediately into one of the four expansion slots. Previously owned eight- and sixteen-slot bags retain their capacity. Each loose item stack uses one slot; equipped copies use none. Full bags still accept gold and existing loose stacks, while new item stacks stay on the ground until picked up or their normal 60-second expiry. Unequipping cannot overflow bags. Existing unlimited inventories receive only the expansion packs needed to preserve their loot when first migrated. Merchants use the same item artwork and protect equipped copies.
- **Z** eats food and **X** drinks a health potion from the two quick slots left of the skillbar; the pair moves as one piece in Edit UI. Pip the baker sells Traveler's Stew (12 gold, 100 HP over 8 seconds, one meal at a time, shown in the active-effects bar) and Mira Moonleaf sells Health Potions (30 gold, 100 HP at once, one 60-second cooldown shared by every potion). Bags also offer Use (button, right-click or double-click). Neither is used at full health, so nothing is wasted; the potion cooldown is saved as a wall-clock time, so logging out or a restart cannot skip it, while a meal in progress ends when you leave. The catalog fields are `heal`, `duration` (food) and `cooldown` (potions) in world/items.txt, and an NPC offer sells an item with `item`.
- **Friends and parties:** **O** opens the social panel (Friends, Party and Online tabs) and **P** opens it on the party tab. Add a friend or invite to a party by typing a player's exact name, or press the buttons in the Online list (names are not unique, so the list is the way to pick between two players called the same). The other player gets a prompt with Accept and Decline; requests and invites lapse after 60 seconds or when either player disconnects. Friendship is mutual and saved with both characters (up to 50 friends); the list shows who is online and where, and offline friends stay listed. A party holds **at most 5 players**. Whoever invites first becomes the leader; only the leader invites, promotes or removes members, and when the leader leaves the longest-standing member leads (a party of one ends). A party member who disconnects keeps their seat for 60 seconds. Parties are not saved and end when the server restarts. The party frame under your portrait shows each member's health, party members are green on the minimap and in the world, and `/p message` (or `/party`) talks to the party only. `/friend name`, `/invite name` and `/leave` are chat shortcuts. Nothing in combat, XP, loot or quests depends on a party yet.
- Enter focuses chat; Enter sends; Esc leaves the chat input. M toggles all sound.
- **Settings** (Esc, then Settings): separate Music and Sound effects sliders (0–100%, default 100%, a squared taper so 100% is the original loudness; releasing the effects slider plays a sample) and a Sound on checkbox that mirrors M. **Edit UI** hides the panel and puts a dashed handle over each movable piece: character frame, active effects, party frame, minimap, Visit Alderhaven button, quest tracker, Character, Bags and Social buttons, skillbar, chat and the controls hint. Drag a handle (mouse or touch), or Tab to one and use the arrow keys (Shift for bigger steps). Pieces stay inside the stage, the game receives no keys or clicks while editing, and Esc or Done returns to Settings. Reset layout restores every default. Volumes and the layout are stored per browser (not per character) under `valhallasc.save.v1`; positions are offsets in stage-width percent from each piece's default spot, so they follow the window size. Client only: no server or protocol change.
- New characters receive their class’s starter armor and weapon. Equipment must be owned before it can be equipped. Existing characters keep their equipped gear when their inventory is first migrated.
- **Alderhaven** is south of the meadow. Follow the path through the north gate or click **Visit Alderhaven** to walk there automatically.
- **Q** opens the quest journal. Wren offers a town introduction; Captain Rowan offers a six-slime patrol, which unlocks Bram’s two-Ironhide hunt and Linden’s repeatable eight-enemy bounty. Bram’s quest unlocks Rowan’s King Slime challenge. Accept at the giver, complete the objectives, and return for XP and gold. Every quest has a recommended level, shown on its journal card (orange from three levels above you, red from five, grey from five below), and pays XP equal to a tenth of what that level needs to level up (level 5: 141 XP). Quest progress and completed rewards are saved with your character. The journal can walk you to a giver; gold markers show one-time quests (`!`) and ready turn-ins (`?`); repeatable quests use blue markers. Only kills after acceptance count, and the finishing blow earns credit.
- **Cinderwatch Camp** is the safe quest hub beside the Crags arrival gate. Captain Sera commands the expedition, Scout Kael guides the lower hunts, Sister Iona offers free healing and Health Potions, and Quartermaster Dain buys loot and sells stew and six-slot satchels. Tents, a campfire, a contract board and minimap markers identify the camp. Outside its sanctuary, the travel button walks you back to camp. Update only the camp with `python3 scripts/generate_crags.py --hub-only`, then run `node scripts/sync-world.cjs` and rebuild Rust; the full generator also includes the camp.
- **Twelve Crags quests:** A Foothold in the Ash (meet the crew); Lights Along the Ford (4 wisps); Quench the Cinders (8 wisps); Silk Across the Trail (4 spiders); Break the Brood (7 spiders); Voices in the Ash (3 wraiths); A Quiet Mountain (6 wraiths); Stone Sentinels (2 golems); Crack the Basalt (4 golems); Emberfall Vanguard (2 of each kind); Cinderwatch Patrol (10 Crags enemies, repeatable); Keep the Ash Road Open (3 wisps and 3 spiders, repeatable). The introduction unlocks the first hunt and patrol; claiming the wisp, spider, wraith and golem hunts unlocks successive expedition stages. Quests only credit actions in their own zone. The journal puts the current zone's quests first and routes to local givers.

- Click a townsperson or press **F** nearby to talk. The sanctuary heals for free; the bakery, apothecary, and inn offer healing services for gold. The armorer replaces and fits basic starter equipment for free. Starter gear cannot be sold. Food and tonics are consumed at the counter.
- Every mob drops a sellable material alongside its gold: Slime Gel (3 gold), Blue/Pink Gel (5), Golden Gel (7), Ironhide Shell (15), or Royal Jelly (40). Move within 3 world units to attract your drops; only the living killer can collect them. Uncollected drops disappear after 60 seconds.
- Mobs can also drop rare upgraded armor or weapons for **any class**, or universal Headgear, Shoulders, Pants, Gloves, Necklace and Accessories, with an equal chance for each catalog upgrade. Chance per kill: green slimes **2%**, blue/pink/yellow slimes **5%**, Ironhides **12%**, King Slimes **35%**. These use the existing Azure/Royal, Runic/Crystal and Moon/Moonfang artwork and combat stats. An item for another class stays in your inventory and can be sold.
- Sell loot to **Linden (merchant)** or **Bram (armorer)** in town. Sell one item, a spare stack, or all materials. Rare class gear sells for 30 gold and universal gear for 25 gold. All equipped copies are protected. Inventory, trained attributes and fitted bags persist with your character. `world/items.txt` owns item names, values and the shared UI catalog; run `node scripts/sync-world.cjs` after changing it, then rebuild Rust.
- Slimes stay outside the city walls. NPC conversations stop your actions while the shared world keeps running.
- New Character keeps your earlier character in **Esc → Your Characters**.

## Shared world and saves

The Rust server owns movement speed, map collision, AI, melee range/facing, attack cooldowns, swept projectile hits, damage, critical hits, equipment stats, XP, levels, gold pickups, deaths, and respawns. Clients send actions, never character positions, damage results, or rewards. Slimes are shared: a kill happens once, and the killer receives XP and owns its gold and item drops. This is cooperative PvE; players cannot damage each other.

The simulation runs at 20 ticks per second and sends snapshots at 10 per second. Each connection receives only the players, enemies, projectiles and drops of the zone its character is in, so a second zone adds nothing to the other zone's bandwidth. Clients interpolate positions, draw the original layered sprites, and display everyone on the minimap. Text chat is world-wide. Commands have payload/rate limits, inactive directional input expires, slow connections are dropped, and WebSocket origins are checked. The server allows up to 128 simultaneous connections; this is a guardrail, **not a tested MMO capacity claim**.

Characters are stored in `data/valhalla.sqlite` with SQLite WAL transactions. Saves run every five seconds, on disconnect, and at graceful shutdown. Item pickups, equipment changes, stat training, vendor services and quest acceptance/claims also save immediately. The browser retains a server-issued guest character key. Only the key hash is stored in SQLite; the name is not a credential. Reloading or reconnecting resumes the same character, including position, class, appearance, equipment, inventory, HP, level, XP, gold, kill count, trained attributes, unspent stat points, and quests. Reconnect happens automatically after a network/server interruption.

Keep the browser's site data and the database. Clearing site data loses access to guest characters; these are not SSO accounts and there is no account recovery or cross-device login yet. HTTP is appropriate for local development; put public deployments behind HTTPS so character keys travel over WSS. Different server URLs have separate character-key collections.

An abrupt process/machine failure can lose the last five seconds of progress. Slimes, projectiles, and uncollected drops are transient and reset when the server restarts. Persistent characters remain. Keep SQLite backups outside the public web root; use SQLite's backup command/API or stop the server before copying the database and its WAL files.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `VALHALLA_BIND` | `127.0.0.1:8080` | Listening address |
| `VALHALLA_DB` | `data/valhalla.sqlite` | Character database path |
| `VALHALLA_CLIENT_DIR` | `client` | Static client folder |
| `VALHALLA_ORIGIN` | Same as request host | Exact allowed browser origin behind a reverse proxy, e.g. `https://gunning.se` |
| `VALHALLA_START_LEVEL` | `1` | New characters begin at this level (1–40) so tests can drive learned skills for real; saved characters are untouched. For automated tests only: never set it on the public service. |
| `VALHALLA_GOD_MODE` | unset | `1` makes players take no damage (enemies still fight, levels still roll). For automated tests only: the MCP driver's private worlds and the browser suites set it; never set it on the public service. |
| `VALHALLA_LEVEL_SPREAD` | `2` | Each enemy's level is its kind's default ± this many levels (0 pins every enemy to its default, maximum 5). Browser suites that exercise controls rather than combat set it to 0. |
| `VALHALLA_TEST_COMMANDS` | unset | `1` lets players send `debug` shortcut messages (set level, give items, teleport, finish quests, kill enemies...). For automated tests only: the MCP driver's private worlds set it; never set it on the public service, which otherwise answers every `debug` message with an error. |
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
world/map.txt    Shared collision geometry, slime spawns, city layout and NPC services
scripts/        Local Cargo wrapper and client map sync
tests/          Browser, test driver, and MCP integration tests
deploy/         Compose, Apache and systemd examples
```

`world/map.txt` is the source of truth for spawn/collision geometry, NPCs, and quest definitions. The top level is zone 0 (Greenmeadow with Alderhaven) and its `zones` array holds further zones with the same fields plus `name`, `theme`, `levels`, `paths` and `portals`; a portal's `to`, `tx`, `ty` name the destination zone index and arrival point. `python3 scripts/generate_crags.py` writes zone 1 and both gates (seeded, with a flood-fill check that every spawn is reachable), then `node scripts/sync-world.cjs` and a Rust rebuild apply it. After editing it, run `node scripts/sync-world.cjs`, then rebuild Rust (the map is bundled into the binary). Terrain shading and scenery drawing use the original renderer, with original city artwork in `client/city.js`. Alderhaven takes visual inspiration from [Prontera references](https://www.gameblast.com.br/2015/10/top-10-melhores-cidades-jogos.html): cobblestone plazas, a fountain, timber-framed shops, gardens, and stone gates. Reference images are not shipped as game assets.

The four Emberfall Crags monsters follow the same workflow with `python3 scripts/make_crag_sprites.py preview | build [kind...] [--replace] | export`: shaded ellipsoids and capsules drawn from parameters (never by hand), one 34-frame 96×96 PixelFlow sprite per kind (`valhallasc_crag_<kind>_all`, opened at `/pixelflow/?sprite=<id>` using the ids in `client/assets/crags.txt`), exported to `client/assets/crags_<kind>.png` with the same five clips as the Ironhide. `build --replace` discards editor hand edits; `export` preserves them. PixelFlow caps an owner at 200 saved sprites, so free slots before building more.

The Ironhide Beetle follows the local makesprites/PixelFlow workflow. Run `python3 scripts/make_ironhide_sprites.py preview` to review all five clips, `build` to create its editable sprite, and `export` to read edits back into `client/assets/ironhide.png` and `ironhide.txt`. **`build --replace` discards beetle hand edits.** The original indexed frames are preserved in `scripts/ironhide_raw.npz`. PixelFlow's saved-sprite quota requires one 34-frame editor sprite; `editorStart` in the metadata records each clip's frame range. Open the sprite ID from the metadata at `/pixelflow/?sprite=<id>`.

On WebSocket connection, send `{"type":"join","version":1,"token":null,"look":{"name":"Freya","class":"mage"}}`. The welcome packet returns an ID, a guest key for a newly created character, and a world snapshot. For resume, send the guest key with `look:null`; saved state takes precedence. Keep keys out of URLs and logs.

Subsequent messages: `input {dx,dy}`, `stop`, `move {x,y}`, `target {id}`, `attack {fx,fy}`, `dash {dx,dy}`, `skill {id,fx,fy}`, `equip {armor,weapon}`, `allocate_stat {stat}`, `use_item {item}`, `interact {npc,offer?}`, `chat {text}`, `social {command:{op,...}}`, `ping {nonce}`, and (test servers only) `debug {ref?,command:{op,...}}`; see Test shortcuts below. Direction vectors are normalized on the server. `move` chooses a destination, not a teleport. Quest acceptance and reward collection use `interact` with `offer:"quest:accept:<id>"` or `offer:"quest:claim:<id>"`. The server validates the giver, distance, living player, prerequisite completions, and recorded objectives. Player snapshots and dialogue packets include the character’s `quests` progress. Unknown command fields are refused. Server messages: `welcome`, `snapshot`, `event`, `chat`, `system`, `pong`, `dialogue`, `debug` (the reply to a test shortcut), and `error`. See `server/src/model.rs` for the exact types.

The transport uses [Axum WebSockets](https://docs.rs/axum/0.8.9/axum/extract/ws/) and [Tower HTTP static serving](https://docs.rs/tower-http/0.6.11/tower_http/services/struct.ServeDir.html). Cargo.lock pins the resolved versions.

## Test driver and MCP

The test driver starts a real Rust server on a free loopback port with a fresh SQLite database under `test-results/driver-*`. Bots use the same `/ws` actions as browser players. Combat, movement, NPC services, and rewards are calculated by the server. The driver overrides inherited bind/database settings and has no option to attach to the public world.

Build the server and install the Node 20+ development dependencies first:

```sh
bash scripts/cargo.sh build --locked
npm ci
npm run test:driver
node scripts/test-driver.cjs list
node scripts/test-driver.cjs run movement
node scripts/test-driver.cjs run ironhide
node scripts/test-driver.cjs run city
node scripts/test-via-mcp.cjs run inventory
node scripts/test-via-mcp.cjs run quests
node scripts/test-via-mcp.cjs run crags_quests
node scripts/test-via-mcp.cjs run quest_combat
npm run test:scenarios
```

`npm run test:scenarios` runs every scenario through a real MCP SDK connection and the `run_scenario` tool. Use `node scripts/test-via-mcp.cjs --registered run all` to verify the launch configuration installed in Codex. `movement` checks three classes, overlapping players, authoritative movement, dormant King slots, enemy spacing, and character resume. `ironhide` walks a mage to an actual beetle, defeats it, collects its gold, and checks saved progress. `city` walks into Alderhaven and checks distance restrictions and healer/armorer services. `quests` covers the town introduction, partial progress, NPC/range checks, reward replay protection, and restarting the actual Rust process. `quest_combat` earns the patrol, Ironhide hunt, and repeatable bounty through real combat, checks progression and level-up, accepts the King challenge, resets the bounty, and verifies saved history after restart. `inventory` checks real loot, ownership, equipment, protected sales and persistence. `stats` earns a level through actual combat and quests, trains Intellect/Dexterity/Accuracy, rejects overspending, and verifies saved allocations after restarting Rust. `bags` earns 500 gold through quests and combat, buys a six-slot expansion bag at Linden, checks range and funds restrictions, and verifies capacity and ownership after restarting the private server. This scenario takes about eight minutes; use a request timeout of at least 600 seconds for direct MCP calls. The provided runner already requests that timeout. King Slime defeat and the randomized timer also have Rust tests; the MCP scenario does not wait 5–10 minutes for a king spawn. Every observed snapshot is checked for enemy spacing. Each scenario prints JSON with pass/fail checks and an artifact path; failures produce a nonzero exit status. Reports contain the last snapshot and up to 500 recent events. Test guest keys remain in process memory and never appear in reports or tool results.

On this host, Node is at `/home/serveperry/.nvm/versions/node/v20.20.2/bin/node`. Use that absolute executable for the direct `node` commands above, or add its directory to `PATH` for npm scripts. `VALHALLA_BINARY` can select another locally built server binary; bind, database, and client directory remain controlled by the driver.

On this host, the MCP is registered in `~/.codex/config.toml` as `valhallasc-testing`, with a 20-second startup timeout and a 180-second tool timeout. Restart Codex after registration to load its tools (the list is read from the server, so new tools need no re-registration). To register this checkout or verify an installation again:

```sh
bash scripts/cargo.sh build --locked
python3 scripts/setup-test-mcp.py --verify
```

The setup command checks dependencies, backs up the existing Codex configuration, preserves other settings, registers absolute launch paths, and runs the private driver/MCP integration checks. It requires permission to write user-level Codex settings and open a private test port. Once connected, ask the agent to “Use valhallasc-testing to run the movement, Ironhide, and city scenarios.”

The MCP wrapper uses the official SDK and stdio. Configure your MCP client to launch an **absolute Node executable** with the **absolute script path** as its argument, for example:

```json
{
  "mcpServers": {
    "valhallasc-testing": {
      "command": "/home/serveperry/.nvm/versions/node/v20.20.2/bin/node",
      "args": ["/home/serveperry/webserver/www/Valhallasc/scripts/test-mcp.cjs"]
    }
  }
}
```

This is a launch example; the enclosing settings format depends on your MCP client. Launch the script directly so stdout contains only MCP messages. The script resolves the repository from its own location and does not depend on the client's working directory.

| Tool | Purpose |
| --- | --- |
| `start_world` / `stop_world` | Start/stop a private world; stopping saves an interactive report |
| `connect_bot` / `disconnect_bot` | Create a class or resume a disconnected bot by name |
| `send_action` | Send movement, input, stop, target, attack, dash, skill, equipment, NPC interaction, chat, or ping |
| `inspect_world` | Inspect the latest snapshot or one bot, recent events, and spacing checks |
| `wait_world` | Wait up to 30 seconds of real simulation time and inspect again |
| `list_scenarios` / `run_scenario` | Discover/run a named scenario in a fresh world |
| `describe_world` | Zones, NPCs and offers, portals, quests, items, skills and enemy kinds with default levels, so no world file needs reading |
| `set_level` / `give_xp` / `set_gold` / `set_health` | Level a bot (1-100; 20 unlocks every skill) with the real level-up event, grant XP through the normal rules, set gold, set or restore hp or defeat the bot |
| `give_item` / `take_item` / `drop_item` | Add items (bags are fitted, capacity is honoured unless `force`), remove spare copies (worn ones stay), or drop loot at the bot's feet |
| `teleport` / `walk_to` / `talk_to` | Jump to `{x,y,zone}`, `{npc}`, `{portal}`, `{enemy}`, `{spawn}` or `{bot}`; walk there like a player along a collision-aware route; use an NPC offer, walking into range first |
| `quest` | `accept`, `complete`, `claim`, `finish` (prerequisites, accept, complete and claim in one go) or `reset` any quest |
| `cast_skill` | Cast a class skill, optionally at `nearest`/an enemy/a point, raising the level to unlock it and clearing cooldowns first; reports whether it went off, cooldown, buffs and which enemies lost hp |
| `kill_enemies` / `respawn_enemy` | Defeat enemies through the real kill path (XP, quest credit, gold and loot), revive one, or call the King now |
| `reset_character` / `set_god_mode` | Clear cooldowns, refund stat points, toggle invulnerability mid-test |
| `setup_character` | Reach a state in one call: level, gold, items, finished quests, then a teleport target |
| `wait_for_event` / `restart_world` / `debug_command` | Wait for a new event, restart only the private server (to check persistence), or send a raw shortcut |

For interactive exploration: `start_world`, `connect_bot` with `{"bot":"Mage","class":"mage"}`, then `send_action` with `{"bot":"Mage","action":{"type":"move","x":45,"y":48}}`, `wait_world`, and `inspect_world`. A movement destination is an ordinary server action. The driver supports at most 16 bot identities, validates action schemas, and serializes MCP calls. Stop the interactive world before running a scenario. Allow at least 180 seconds for scenario calls; walking and combat happen in real time. Normal disconnect saves characters, and reusing a bot name resumes the same character and class within that world.

Snapshots refresh while bots are connected; with no connected bots inspection retains the last observed snapshot. Closing MCP stdin or sending SIGINT/SIGTERM disconnects bots and stops the child server. Test databases and reports remain local and gitignored for review. The default `npm test` runs driver/MCP integration checks, all MCP scenarios, then the focused quest, inventory, equipment/skillbar and social Chromium UI passes. The social UI pass runs three browsers: it checks the panel's keys and focus, friend and party prompts, the party frame, party chat, and that a player's name containing markup is shown as text. The quest UI pass checks journal controls, focus, cards, markers, travel buttons, partial progress display, and loaded artwork. The inventory UI pass checks actual browser combat/pickup, equipment ownership, vendor selling and reload, plus isolated display fixtures for rare cross-class gear and blue repeatable markers. The equipment/bags/skillbar pass checks the nine slots, item tooltips, drag-to-equip and unequip, bag tabs, sorting, search, saved cell positions, authoritative skill cooldowns, keyboard and click activation, assignment and dragging, per-character layout persistence, chat input, and small viewport fit. The original three-player browser regression suite remains available as `npm run test:browser:full` when controls or rendering need broader coverage. No public service restart or deployment is needed for these local tools.

### Friends and parties

`{"type":"social","command":{"op":...}}` with `refresh`, `who`, `friend_request {id|name}`, `friend_accept {id}`, `friend_decline {id}`, `friend_remove {id}`, `party_invite {id|name}`, `party_accept {id}`, `party_decline {id}`, `party_leave`, `party_kick {id}`, `party_promote {id}` and `party_chat {text}`. An `id` is a character id from a list or an invite; a `name` must match exactly one other online player. The server answers every command with `{"type":"notice","ok":true|false,"text"}` and pushes `{"type":"social","friends":[...],"incoming":[...],"outgoing":[...],"party":null|{leader,max,members:[...]}}` whenever a list changes, `{"type":"party","party":{...}}` twice a second while in a party (member health), and `{"type":"who","players":[...]}` for the online list. Party chat is `{"type":"chat","channel":"party",...}`. The rules and limits live in `server/src/world/social.rs`; `Character.friends` (character ids) is the only persisted part. In the MCP tools, `social` runs one command as a bot and takes `bot: "Other"` in place of an id.

### Test shortcuts

Private worlds start Rust with `VALHALLA_TEST_COMMANDS=1`, so a bot may send `{"type":"debug","ref":1,"command":{"op":"set_level","level":20}}`. The server answers `{"type":"debug","ref":1,"ok":true,"tick":...,"result":{...}}` or `ok:false` with an error; any server without the variable answers every `debug` message with `ok:false` and changes nothing. The shortcut skips only the time it would take to reach a state: rewards, level-up events and skill unlocks, quest rules, loot, bag capacity, saves and zone filtering still run in the server (`server/src/world/debug.rs`). Operations: `set_level`, `give_xp`, `set_gold`, `set_hp`, `die`, `reset_stats`, `reset_cooldowns`, `set_god_mode`, `teleport`, `give_item`, `take_item`, `drop_item`, `quest` (accept, complete, claim, finish, reset), `kill_enemy`, `respawn_enemy` and `summon_king`. `TestWorld.debug(bot, command)` sends one and resolves once the bot's own snapshot shows the effect. `start_world` accepts `startLevel`, `godMode` and `levelSpread` (0 pins enemy levels). Delayed effects (a meteor landing, projectiles in flight) need a longer `settleMs` on `cast_skill`. The `shortcuts` scenario exercises the lot against a real server.

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

The optional full browser regression suite (`npm run test:browser:full`) starts its own isolated Rust server/database and uses three independent browser clients. It covers character creation, visible remote players, movement replication, player pass-through, enemy spacing in server snapshots and rendered combat, equipment, safe chat, invalid commands/keys, duplicate sessions, slime and Ironhide combat, shared kills, XP pacing, loot, page reload, server restart/reconnect, and switching between saved characters, walking through the city gate, NPC dialogue, sanctuary healing, armorer fitting, and shop affordability. Screenshots and disposable databases are written under gitignored `test-results/`. The existing sibling Playwright installation was used for testing in this workspace via `NODE_PATH`; no runtime dependency on the sibling project is required.

`node tests/public-smoke.cjs` verifies the actual public HTTPS/WSS deployment with two browser clients. It also checks canonical redirects, private-file protection, chat, movement replication, and saved-character reload. It records only the test character IDs in `test-results/public-smoke-results.json`; remove those specific test characters from SQLite after both clients disconnect.

## Current scope

This is a playable **single-zone multiplayer foundation**, not a finished large-scale MMORPG. There are no accounts, player-to-player trading, guilds, PvP, multiple zones, distributed world servers, or native executable client packages yet. Everyone receives the zone's snapshots; interest management and load testing are needed before promising large populations. Movement follows direct goals with collision sliding, as in the original; ordinary ground clicks do not find paths around complex obstacles. The city travel button follows a small grid route through the shared collision geometry. Browser tests here run on Linux Chromium; Windows and Firefox builds have not been exercised in this environment.
