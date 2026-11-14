# Money: gold, silver and copper (`COIN-DENOMINATIONS`)

100 copper = 1 silver, 100 silver = 1 gold. **Every stored amount is whole copper.** Nothing was converted when this arrived: a number that used to
be called "gold" is the same number now, read as copper. The field is still called `gold` everywhere in the code, the saves, the packets and the
tests (a level-1 drop of 5 is `gold: 5`, shown as 5 copper; the horse at 500,000 is shown as 50 gold).

- **Client:** `client/money.js` (`Money.parts`, `Money.text`, `Money.short`, `Money.html`, `Money.set`, `Money.preview`) and `client/money.css`. Prices, purses,
  quest rewards, repair and bank balances show numbers with small coin icons (`Money.html`); notices, titles and tooltips use `Money.text`
  ("12 gold 34 silver 5 copper", zero parts left out, "0 copper" for nothing); the canvas uses `Money.short` ("12g 34s 5c"). The icons carry an
  `aria-label` with the words. Number fields (mail attachment, trade offer, bank deposit) take copper and show what it comes to beside them.
- **Server:** `model::money_text(copper)` makes the same words for messages (`"Items sold for 1 silver 20 copper."`). Swedish pieces are translated through
  the phrases `{0} gold`, `{0} copper` in `scripts/sv-phrase-translations.txt` (silver is the same word).
- Swedish: guld / silver / koppar (`docs/swedish-glossary.md`).
- Prices quoted in older docs (`mounts.md`, `zone-travel.md`, `shop-selling.md`, `durability.md`, `rebirth.md`, `bank.md`, `mailboxes.md`) are in the old
  unit: read "gold" there as copper, so "500,000 gold" is 50 gold, "20 gold per Spark leg" is 20 copper, a six-slot satchel (500) is 5 silver.
