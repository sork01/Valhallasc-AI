# Reconnect recovery

Beta 1.32.2, same-version owner follow-up. An interrupted browser connection can
remain registered until the server's heartbeat notices it (up to roughly
75 seconds). Previously the browser treated the resulting "already online in
another window" refusal as fatal and hid Retry.

`client/online.js` now retries this specific join refusal, keeping the guest key
or account session and character selection. It waits at most 90 seconds, then
shows the refusal with Retry available; it never evicts a genuinely active
second window. Authentication failures still stop immediately and clear expired
credentials. Join timeout starts after the socket opens. Every socket attempt
gets its own generation, so stale messages, close events and timers cannot
disconnect a replacement socket.

Incoming complete snapshots coalesce to the newest one per animation frame.
Other packet kinds first flush pending state, preserving transaction and event
order. Closing or replacing a connection discards its queued snapshot. This
avoids repeatedly rebuilding stale UI state when a busy browser catches up.

`node tests/reconnect-recovery.cjs` passes 21 focused clock/network checks for
guest/account identity retention, slot-release recovery, stale callbacks,
snapshot bursts and ordering, cancellation, a genuine occupied character,
authentication failure and late handshake timing. The original client fails
the recoverable-reconnect assertion.

`bash scripts/test-touch-bounded.sh tests/reconnect-ui.cjs` passes nine checks
against a real private server: an intentionally retained original socket holds
the character, a replacement gets refused, releasing the socket allows automatic
recovery, and a late old close does not interrupt it. It also verifies that the
field supplies a changing camera to weather rendering. No production guest,
database migration, Rust build or service restart is needed.
