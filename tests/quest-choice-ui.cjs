const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<div id="quest-tracker"></div><div id="quest-journal" hidden><div id="quest-list"></div><button id="quest-close"></button></div><div id="pause" hidden></div><div id="equipment" hidden></div>');
    await page.addScriptTag({ path: path.join(root, 'client/world.js') });
    await page.addScriptTag({ path: path.join(root, 'client/items.js') });
    await page.evaluate(() => {
      window.Online = { connected: true, send: message => { window.claimed = message; return true; } };
      window.Field = { hero: { dead: false, look: { class: 'warrior' } }, zone: 13, setPaused: () => {} };
      window.City = { open: false };
    });
    await page.addScriptTag({ path: path.join(root, 'client/quests.js') });
    await page.evaluate(() => {
      const q = WORLD_MAP.zones[12].quests.find(q => q.id === 'astral_welcome');
      window.quest = q;
      const panel = document.createElement('div'); panel.id = 'npc-choice'; document.body.append(panel);
      Quests.update([{ id: q.id, counts: q.objectives.map(o => o.count), claimed: false, completions: 0 }]);
      Quests.detail(q, panel, () => {});
    });
    const buttons = page.locator('#npc-choice [data-action="claim"]');
    assert.equal(await buttons.count(), 5);
    assert.equal(await page.locator('#npc-choice [data-action="claim"]:not([data-item])').count(), 0);
    await buttons.nth(2).click();
    assert.equal(await page.evaluate(() => claimed.offer), await page.evaluate(() => `quest:claim:${quest.id}:${quest.rewardChoices.warrior[2]}`));
    console.log('3 quest choice UI checks passed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
