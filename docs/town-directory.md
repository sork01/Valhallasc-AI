# People and services on detailed maps

Beta 1.19.0 adds a searchable directory above each zone map's details. It
includes NPCs with offers, buying services, Spark Travel, local quests or talk
objectives. Walking residents and guards with no useful interaction stay out
of the list. Names, roles and service labels are searchable; mount offers,
banks, repairs and people who buy items have explicit labels.

Selecting a row highlights the NPC's authored coordinates with a named gold
pin above fog and quest markers. The directory supplies an address before a
town corner has been explored; it does not uncover terrain or monsters.
Changing zones clears the selection. The list scrolls inside the existing
sidebar and rows retain 44 physical pixels after window scaling. Map keyboard
capture allows typing and editing in the search field, and includes it in
the Tab focus loop.

Implementation: `client/worldmap.js`, `client/online.css`, hand-written Swedish
strings in `scripts/sv-translations.txt`. No server or save changes. Focused
private browser coverage: `tests/town-window-ui.cjs`, run under
`scripts/test-touch-bounded.sh`. Its mutations remove pin selection, backdrop
dismissal or the explanation from a vendor who does not buy items.

Verified on 2026-10-25: 156 assertions at 844×390 and 1024×768, including
Android browser user-agent selling, four town directories, keyboard search,
readable sidebar widths, square map coordinates, real pins, mouse/touch
dismissal, confirmation cancellation, mobile/desktop defaults, saved scaling,
both HUD bars, fullscreen and Swedish merchant labels. Peak 1020 MiB within
the unchanged 1536 MiB cap. Six routed mutations fail their intended guards
(pin selection, outside dismissal, vendor explanation, default size, bar
scaling and the fullscreen button). Native Android device acceptance remains
a manual check; no native Android app package was changed.
