# Swedish glossary and rules

The Swedish catalog is written by hand (no translation service, tool or library). This is the word list behind it, so the next
string gets the same word as the last 6,000 did. The text lives in `scripts/sv-*.txt`; `python3 scripts/build_swedish.py`
assembles `client/sv-data.js` from them and fails on anything missing or wrong. `tests/swedish-catalog.py` is the gate.

## Files

| File | What it holds |
|---|---|
| `sv-translations.txt` | exact English text -> Swedish (JSON) |
| `sv-template-translations.txt` | English template with `{0}`, `{1}` -> Swedish template |
| `sv-phrase-translations.txt` | short phrases with numbers (`Rank {0}:`, `{0}s cooldown.`) replaced inside longer composed lines |
| `sv-keep.txt` | texts that stay as written: people, places, dungeon names, loanwords |
| `sv-ignore.txt` | harvested strings that are not text (ids, css, event names, Korean, debug) |

`{0:t}` in a Swedish template means "translate this piece too" (a quest title, a class, a portal name). A plain `{0}` is left
alone, because it may be a player's name. A template may leave out a placeholder only where English builds a plural ending
(the list is `MAY_DROP` in the build script). New strings go in these files, never in `sv-data.js`.

## What stays English

People, towns, zones, dungeon names, streets and house numbers (`Cooper Walk 3`), pub names, Korean given names, and the
words `PvP`, `Online`, `Bank`, `Arena`, `Material`, `System`. Titles are translated and the name is kept: `Captain Rowan` is
`Kapten Rowan`. Gate, bridge and stair names keep their proper part (`Crags-porten`, `Skaldholmsporten`).
Typed confirmations stay as the code compares them (`Skriv REBIRTH för att bekräfta`).

## Words

Always the same word, in every window:

| English | Swedish | English | Swedish |
|---|---|---|---|
| Warrior / Mage / Assassin / Priest / Hunter | Krigare / Magiker / Lönnmördare / Präst / Jägare | party | grupp |
| Health / Mana / Rage / Energy | Hälsa / Mana / Raseri / Energi | quest | uppdrag |
| Strength / Agility / Intellect | Styrka / Smidighet / Intelligens | bounty | prisjakt |
| Stamina / Dexterity / Accuracy | Uthållighet / Fingerfärdighet / Precision | elite / boss | elit / boss |
| Attack / Defense | Attack / Försvar | dungeon | dungeon |
| Headgear / Shoulders / Chest | Huvudbonad / Axlar / Bröst | mercenary | legosoldat |
| Gloves / Hands / Pants | Handskar / Händer / Byxor | Meeting Stone | Mötesstenen |
| Necklace / Accessory | Halsband / Smycke | Sanctuary | Fristad |
| Common / Uncommon / Rare / Epic / Legendary | Vanlig / Ovanlig / Sällsynt / Episk / Legendarisk | Spark Travel | Gnistresa |
| skill / passive / skillbar | färdighet / passiv / färdighetsfält | Rebirth / Reborn | Pånyttfödelse / Pånyttfödd |
| cooldown | nedkylning | mount / mount licence | riddjur / riddjurslicens |
| bag / backpack | väska / ryggsäck | bank | bank |
| gold / level / XP | guld / nivå / XP | Need / Greed / Pass | Behov / Girighet / Passa |
| raid (a party of ten) | raid | | |

Rules that came up:

- `Staff` is `stav`, `Mace` is `klubba`, `Daggers` are `dolkar`, `Robes` are `dräkt`, `Vestments` are `skrud`.
- A pair of gloves, pants and shoulder plates is plural (`handskar`, `byxor`, `axelplåtar`), so its adjectives are too
  (`Härdade lärlingshandskar`); a ring, helm or staff is `en` and a necklace, headband or sword is `ett`.
- A boss or elite epithet is translated and the name is kept (`Hvitserk den dränkte`); a creature is a compound
  (`Frosthäger`, `Rimfrostdrake`); its plural drops the article (`Besegra frosthägrar`).
- Gear names: `[rank or zone adjective] [style] [piece]`, the adjective agreeing with the piece. Set pieces are
  `[the set's] [piece]` (`Tångvävarens skrud`). The adjectives are `-sliten` (worn), `-smidd` (forged), `-bunden` (bound),
  `-krönt` (crowned).
- Numbers: `40 %` with a space, `1 poäng`, `0,5` in the hand-written lines; metric only (`meter`, never miles).
- Wording over word-for-word: `Gå in i`, `Tala med`, `Möt`, `Hämta`, `Besegra`, `Rapportera till`, `Kom tillbaka till`.
  Dialogue is spoken Swedish with `du`. Keep a line as short as the English where it sits in a button or the skillbar
  (`Sword Strike` is `Hugg`, `Weather effects` is `Väder`): a single long word cannot wrap.

## Checking

- `python3 scripts/build_swedish.py --check`: harvest the English the player can see and check the files.
- `python3 tests/swedish-catalog.py`: complete, placeholders, no English function words, `sv-data.js` in step.
- `node tests/swedish-locale.cjs`: `Locale.translate` on composed lines, no browser.
- `node tests/swedish-ui.cjs` and `node tests/swedish-layout-ui.cjs` (`SHOT_DIR=<dir>` saves a screenshot of every window):
  the language switch, then nine windows at 1440x900 and on an 844x390 touch phone, in English and Swedish, failing on a
  box that overflows only in Swedish and on English words left on screen.
