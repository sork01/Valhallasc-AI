# Login notifications

`NOTIFY-RULES` uses a successful character entry into the world as the login event. Account authentication by itself sends nothing. One Gotify push contains the character's sanitized name, class, level and zone. It never contains the account name, guest key, session or IP address. The title is `🎮 Valhalla login` and priority is 2 (informational).

The GM character, ambient adventurers, mercenaries and private test bots do not send pushes. Ambient adventurers and mercenaries do not enter through `join_as`; GM and test modes are explicitly excluded. A character sends at most one push every 30 minutes, keyed by character ID in memory. There is no digest. Logout, new account creation before character entry and failed logins send nothing. The cooldown resets on server restart.

The server accepts an optional `VALHALLA_GOTIFY_URL` base URL and `VALHALLA_GOTIFY_TOKEN` application token. Both must be set for notifications to start. The token is sent only as the `X-Gotify-Key` header to Gotify's `POST /message` endpoint. Never place it in repository files, URLs or client files. The world uses a bounded, nonblocking queue. A background task posts with a two-second timeout and drops failures without retry. It logs one generic warning per outage, reset after a successful post, without response bodies or URLs.

Test worlds using `VALHALLA_TEST_COMMANDS=1`, `VALHALLA_GOD_MODE=1` or `VALHALLA_START_LEVEL>1` leave notifications off even if they inherit the Gotify variables. Local tests use a fake loopback Gotify endpoint and a dummy token.
