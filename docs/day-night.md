# World day and night

One shared clock advances **24 game hours in 1,200 real seconds** (50 real
seconds per game hour). A new world starts at 00:00 once; the epoch is stored in
SQLite as `world_meta.daynight_epoch_ms`, so service restarts continue the same
clock. The server sends the fractional hour and speed in the welcome snapshot
and every subsequent zone snapshot. Clients interpolate between snapshots and
resync on each one. All zones share the clock.

| Game hour | Phase | Light |
| --- | --- | --- |
| 05:00–06:59 | Dawn | Blue night fades into warm sunrise. |
| 07:00–17:59 | Day | Clear daytime, bright around noon. |
| 18:00–19:59 | Dusk | Orange sunset fades into blue night. |
| 20:00–04:59 | Night | Stars, moon, lamps and a readable blue tint. |

The first version is cosmetic. Monster behavior, damage, shops, quests, loot,
regeneration and rests do not depend on the hour. Weather and music follow the
outdoor cycle. The HUD shows the world hour and phase. The
Settings slider can reduce night darkening all the way to zero; dusk colour and
the clock remain visible.

The map data marks every private dungeon with `players`/`copies`; those maps
ignore the cycle. The Obsidian Orrery, Rán's Deep, Veyrroot Heartwood and arena
are enclosed by their themes and also keep their existing fixed lighting. No
enterable building interior exists in the current maps. Other public zones are
outdoors, including the cities, Crags, glaciers, fen, forest, sky, desert and
Yearwheel. Outdoor themes choose a blue, green, icy or ember palette, with
Frostwake aurora, Crags ember glow and fen/canopy flora accents. Crossing into
or out of an enclosed zone fades the effect over about a second. Daylight
contact shadows shift gently with the sun; night darkness is capped so actors
and effects remain readable.

The dybase2 score **Lanterns After Sundown** is the shared outdoor night theme.
Its 72 BPM arrangement uses a quiet flute, marimba, bells, pad and bass; the
editable project is `4b1e25ee6a92913f`. During dusk (18:00–20:00), the zone
score fades down while the nocturne fades in. Dawn (05:00–07:00) reverses the
mix. The mix follows the same server clock as the lighting, including GM time
changes. Enclosed zones and the title screens keep their own scores. The
night score is loaded only when dusk begins, and the saved music
volume and mute setting apply to both tracks.
The editable score can be rebuilt with `scripts/create_night_song.sh`, rendered
with `scripts/render_night_song.sh <project-id>`, and looped into the game MP3
with `python3 scripts/finish_night_music.py`.

Game masters can use `/time <0–23.99>`, `/time <hour> freeze` and `/time resume`.
An ordinary `/time` change saves the new epoch. Freeze is transient and resumes
from the frozen hour; private test worlds can use the same `set_time` debug
command without a GM account. A restart removes a transient freeze.
