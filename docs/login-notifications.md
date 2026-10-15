# Login notifications

`NOTIFY-RULES` uses a successful character entry into the world as the login event. Account authentication by itself sends nothing. One Gotify push contains the character's sanitized name, class, level and zone. It never contains the account name, guest key, session or IP address. The title is `🎮 Valhalla login` and priority is 2 (informational).

The GM character, ambient adventurers, mercenaries and private test bots do not send pushes. Ambient adventurers and mercenaries do not enter through `join_as`; GM and test modes are explicitly excluded. A character sends at most one push every 30 minutes, keyed by character ID in memory. There is no digest. Logout, new account creation before character entry and failed logins send nothing. The cooldown resets on server restart.

The server accepts an optional `VALHALLA_GOTIFY_URL` base URL and `VALHALLA_GOTIFY_TOKEN` application token. Both must be set for notifications to start. The token is sent only as the `X-Gotify-Key` header to Gotify's `POST /message` endpoint. Never place it in repository files, URLs or client files. The world uses a bounded, nonblocking queue. A background task posts with a two-second timeout and drops failures without retry. It logs one generic warning per outage, reset after a successful post, without response bodies or URLs.

Test worlds using `VALHALLA_TEST_COMMANDS=1`, `VALHALLA_GOD_MODE=1` or `VALHALLA_START_LEVEL>1` leave notifications off even if they inherit the Gotify variables. Local tests use a fake loopback Gotify endpoint and a dummy token.

## Deployment (`NOTIFY-DEPLOY`, 2026-10-15)

The live service sends through Surv rather than straight to Gotify, so a login push also appears in Surv's alarm log (Surv's shared alarm bus is filled only by pushes that pass through its PHP `sendGotify()`, and a direct Gotify post would never show there). The service has `VALHALLA_SURV_NOTIFY_URL=https://gunning.se/surv/api.php?action=notify` and `VALHALLA_SURV_NOTIFY_ADDR=127.0.0.1:443` (`deploy/valhalla.service`, and a drop-in `~/.config/systemd/user/valhalla.service.d/notify.conf`). Surv's `notify` action answers only local callers, so the address pin sends the request to the local Apache; the host name stays `gunning.se`, so the certificate is verified (a plain `https://localhost` call fails with a hostname mismatch). The body is the same title, message and priority 2, plus `send_gotify: true`. Surv answers HTTP 200 with `{"success": false}` when it refuses, which counts as a failure (logged once, later failures suppressed until recovery). No token is stored for the game: Gotify has one application, `surv-alarms`, and Surv holds its token.

Checked with a private game instance (own port and database, the same variables) and one guest login: Surv's alarm log got `[🎮 Valhalla login] NotifyTest · Warrior · level 1 · Greenmeadow` and Gotify stored the message at priority 2.
