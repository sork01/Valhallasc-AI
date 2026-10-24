# Login rate-limit countdown

The account screen displays `Try again in m:ss.` when an authentication endpoint
returns HTTP 429 with a known remaining delay. It updates against an absolute
clock deadline, so background-tab throttling does not stretch the countdown.
The deadline alone is kept in namespaced session storage and restored after a
reload. No credentials or account/session identifiers are stored with it.

At expiry the timer clears and the screen says `You can try signing in again.`
It never retries automatically. Existing sign-in choices remain available;
the server remains responsible for accepting or refusing each attempt. Success
or an ordinary non-rate-limit error clears the old countdown. Swedish text is
hand-written, and the timer does not announce every tick to screen readers.

The server adds numeric `retryAfter` seconds and a matching `Retry-After` header
to its existing authentication 429 responses. If both the address and account
limits apply, the longer active wait is returned. Fractional seconds round up;
when concurrent failures exceeded the threshold, the wait lasts until enough
of them expire rather than just the oldest failure. Blocked requests do not
extend the window. The limits are unchanged:

- Failed password logins: five per address per five minutes and ten per account
  per fifteen minutes.
- Registration: five attempts per address per hour.
- Site SSO checks: thirty attempts per address per five minutes.

`Online.api` reads the JSON delay, with the standard header as fallback (seconds
or HTTP date). Without a valid delay it keeps the ordinary error rather than
inventing a duration. This response metadata does not change wire protocol 1.

Focused checks are in `server/src/auth.rs` (`rate_limit_delay...`,
`rate_limit_response...`, `login_rate_limit_reports...` and existing
`bad_credentials_are_refused_and_rate_limited`) and `tests/login-retry-ui.cjs`.
The browser test triggers a real private-server login limit, then uses short
controlled 429 responses to verify expiry without waiting five minutes. It also
checks reload persistence, header fallback, ordinary errors, missing delay,
Swedish and absence of automatic retries. No public login attempts are needed.

Validation (2026-10-24): four focused auth tests pass; 16 private browser checks
pass against the release candidate, including a real five-failure limit,
reload persistence, expiry, header fallback, invalid/missing delay, successful
sign-in cleanup and Swedish. `MUTATE=1` hides the countdown and correctly fails
the visibility check after confirming the real 429 metadata. Artifact:
`test-results/driver-ixBeFV` in the isolated login-retry worktree. Clippy, fmt,
changed JavaScript syntax, Swedish catalog and 21 locale checks pass.
