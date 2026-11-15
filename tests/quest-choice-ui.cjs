const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');

// The journal markup and the scripts quests.js needs are taken from the real client, so the
// fixture follows the page (quest-guidance, locale, money and inventory are loaded before quests.js).
const index = fs.readFileSync(path.join(root, 'client/index.html'), 'utf8');
const journalStart = index.indexOf('<div class="pause" id="quest-journal"');
const journalEnd = index.indexOf('<div class="pause" id="npc-dialogue"');
assert.ok(journalStart > 0 && journalEnd > journalStart, 'quest journal markup found in index.html');
const journal = index.slice(journalStart, journalEnd);
const scripts = ['locale.js', 'money.js', 'inventory.js', 'quest-sources.js', 'quest-guidance.js'];

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<div id="quest-tracker"></div>' + journal + '<div id="pause" hidden></div><div id="equipment" hidden></div>');
    await page.addScriptTag({ path: path.join(root, 'client/world.js') });
    await page.addScriptTag({ path: path.join(root, 'client/items.js') });
    await page.evaluate(() => {
      window.Online = { connected: true, send: message => { window.claimed = message; return true; } };
      window.Field = { hero: { dead: false, look: { class: 'warrior' } }, zone: 13, setPaused: () => {} };
      window.City = { open: false };
    });
    for (const name of scripts) await page.addScriptTag({ path: path.join(root, 'client', name) });
    // MUTATE=drop serves a quests.js that hides the last class choice; the count assertion must fail.
    if (process.env.MUTATE === 'drop') {
      const src = fs.readFileSync(path.join(root, 'client/quests.js'), 'utf8').replace('return (quest.rewardChoices || {})[Field.hero?.look?.class] || [];', 'return ((quest.rewardChoices || {})[Field.hero?.look?.class] || []).slice(0, -1);');
      assert.notEqual(src, fs.readFileSync(path.join(root, 'client/quests.js'), 'utf8'), 'mutation applied');
      await page.addScriptTag({ content: src });
    } else await page.addScriptTag({ path: path.join(root, 'client/quests.js') });
    await page.evaluate(() => {
      const q = WORLD_MAP.zones[12].quests.find(q => q.id === 'astral_welcome');
      window.quest = q;
      const panel = document.createElement('div'); panel.id = 'npc-choice'; document.body.append(panel);
      Quests.update([{ id: q.id, counts: q.objectives.map(o => o.count), claimed: false, completions: 0 }]);
      Quests.detail(q, panel, () => {});
    });
    const buttons = page.locator('#npc-choice [data-action="claim"]');
    // One button per class reward in the data (the warrior's list grew a class-neutral cloak).
    const choices = await page.evaluate(() => quest.rewardChoices.warrior.length);
    assert.equal(await buttons.count(), choices);
    assert.equal(await page.locator('#npc-choice [data-action="claim"]:not([data-item])').count(), 0);
    await buttons.nth(2).click();
    assert.equal(await page.evaluate(() => claimed.offer), await page.evaluate(() => `quest:claim:${quest.id}:${quest.rewardChoices.warrior[2]}`));
    console.log('3 quest choice UI checks passed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
