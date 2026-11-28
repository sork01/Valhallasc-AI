'use strict';
// Rewards as the server pays them, for scenario checks.

// Quest gold for the unreborn Humans these scenarios join as (+5%, rounded half up).
const humanGold = gold => Math.floor((gold * 105 + 50) / 100);

// Kill and quest XP scale with the rewarding level relative to the hero. The server sends the curve at login.
function scaledXp(world, base, heroLevel, rewardLevel) {
  if (!base) return 0;
  const { minGap, rates } = world.xpCurve;
  const index = Math.min(Math.max(rewardLevel - heroLevel - minGap, 0), rates.length - 1);
  return Math.max(1, Math.floor((base * rates[index] + 50) / 100));
}

module.exports = { humanGold, scaledXp };
