# Unique character names

Names are reserved by the authoritative character store across guests, game
accounts, SSO accounts, online and offline characters. Creation uses a database
unique index, so simultaneous requests cannot reserve the same name. Comparison
trims outer whitespace, lowercases Unicode, and folds sharp-s and final sigma.
Existing length, appearance and reserved-name validation still applies.

At the first startup with this version, one SQLite transaction adds `name_key`
and `rename_required`, scans characters in insertion (`rowid`) order, reserves
each oldest name and flags later duplicates. It changes no stored character
JSON, IDs, tokens, account ownership, friends or progress. The inspected live
save has 36 characters and 14 later duplicates across nine names. These later
characters must choose a new name before entry, as selected by the owner.

A resumed guest key or authenticated account/character still establishes
ownership. A flagged character receives a name-required error and an accessible
input in the existing connection panel. Submitting a new name retries that same
identity. The server validates and reserves the name atomically, edits only the
character's look.name, clears its flag, and enters with the same character ID.
A taken name leaves the old state/flag unchanged and the input available. A new
character that chooses a taken name uses the same refusal/input without creating
an orphan character or consuming a slot. Reconnecting an unflagged character
cannot rename it through the join payload.

The migration runs automatically once at server startup; deploy only with a
backup of the live executable and consistent/stopped SQLite as usual. No manual
live backfill is required. Rollback after this migration keeps compatible extra
columns; restore the backed-up database only if intentionally undoing reserved
names/rename decisions. Normal account deletion releases that character's name.

Focused tests cover guest/account/offline case collisions, simultaneous
creation with one winner, oldest-name migration and exact save preservation
through refused/successful rename. Browser checks cover creation errors and a
flagged-character rename/reconnect. No credentials are logged or placed in URLs.
