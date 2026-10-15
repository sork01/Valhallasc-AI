# Paid attribute reset

The service refunds all **trained** attribute points. Gear and passive bonuses,
skills, equipment, and already unspent points stay in place. After the reset,
the Recommended button can spend the resulting pool again, or points can be
trained manually. Current HP and resource are clamped to the new maxima. If a
death lowered the level while earlier trained points remained, the reset keeps
that earned point budget; regaining the old level does not award it twice.

The server charges `min(5, 1 + prior resets) × (5,000 + 50 × level²)` gold.
There is no first reset discount. The multiplier rises for each purchase until
the fifth, then stays at five. Price is calculated again at confirmation, and
the reset count is saved with the character.

| Level | First | Second | Fifth and later |
| ---: | ---: | ---: | ---: |
| 10 | 10,000 | 20,000 | 50,000 |
| 50 | 130,000 | 260,000 | 650,000 |
| 99 | 495,050 | 990,100 | 2,475,250 |

The first level 50 reset costs 130,000 gold, 2.6 times the 50,000 gold mount
and about 50–60 ordinary level 50 enemy payouts before item sales. At level 99,
495,050 gold is about 16 ordinary snowstoat payouts. It is a deliberate choice
even for a developed character. The service
is offered by the existing steward or archivist NPC in the major safe cities
Alderhaven, Skaldholm, Nacrehold, Astralhollow, and Asterion. Their placement
and offers are taken from `world/map.txt`; camps do not get the service. The
sync pass checks the city names and NPC ids after map generation.

The server refuses a reset while defeated, in combat, mounted, without trained
points, or without enough gold. Payment, refund, count, and save happen in one
authoritative action. The UI requires a separate confirmation before sending it.
