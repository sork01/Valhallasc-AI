// Loot & XP floating text UI verification in a real client:
// 1. Gold and item pickups never cover each other, even with slightly offset magnet tiles.
// 2. Mob kills (slimeDie) and shared party kills (partyXp) draw distinct XP floaters for the player only.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-loot-xp-floaters-ui', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'no-preference' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false }));
    window.__draws = [];
    window.__frame = 0;
    const stepFrame = () => { window.__frame++; requestAnimationFrame(stepFrame); };
    requestAnimationFrame(stepFrame);
    const proto = CanvasRenderingContext2D.prototype, fill = proto.fillText;
    proto.fillText = function (text, x, y) {
      if (/Lilita/.test(this.font) && /^(?:\+\d+\s|\+[\d,.]+(?:[kM])?\s(?:gold|XP)|\+[\d,]+[gsc])/.test(String(text))) {
        const w = this.measureText(text).width, h = parseFloat(this.font);
        window.__draws.push({ frame: window.__frame, text: String(text), x, y, w, h, color: String(this.fillStyle), alpha: this.globalAlpha });
      }
      return fill.apply(this, arguments);
    };
  });
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('LootXp'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });

  // Scenario 1: other player's kill and zero-XP kill must stay silent.
  await page.evaluate(() => {
    window.__draws.length = 0;
    const { x, y } = Field.hero;
    Field._debug.event({ kind: 'slimeDie', actor: 'other-player', x, y, enemy: 'green', level: 1, xp: 999 });
    Field._debug.event({ kind: 'slimeDie', actor: Online.id, x, y, enemy: 'green', level: 1, xp: 0 });
    Field._debug.event({ kind: 'partyXp', actor: 'other-player', x, y, enemy: 'green', level: 1, xp: 888 });
  });
  await page.waitForTimeout(350);
  const filteredDraws = await page.evaluate(() => window.__draws.filter(d => d.text.includes('XP')));
  assert.equal(filteredDraws.length, 0, 'other-player and zero-XP kills must not draw XP floaters');

  // Scenario 2: simultaneous itemPickup + gold pickup (offset magnet drops) + slimeDie XP.
  await page.evaluate(() => {
    window.__draws.length = 0;
    const { x, y } = Field.hero;
    Field._debug.event({ kind: 'itemPickup', actor: Online.id, x: x + 0.3, y: y - 0.1, item: 'warrior_weapon_royal', name: 'Golden Test Sword', quantity: 1, rarity: 'rare' });
    Field._debug.event({ kind: 'pickup', actor: Online.id, x: x - 0.25, y: y + 0.2, value: 42 });
    Field._debug.event({ kind: 'slimeDie', actor: Online.id, x, y, enemy: 'green', level: 2, xp: 150 });
  });
  await page.waitForFunction(() => {
    const texts = new Set(window.__draws.map(d => d.text));
    return texts.has('+1 Golden Test Sword') && texts.has('+42c') && texts.has('+150 XP');
  }, null, { timeout: 10000 });
  await page.waitForTimeout(900);

  const report = await page.evaluate(() => {
    const byFrame = new Map();
    for (const d of window.__draws) {
      if (!byFrame.has(d.frame)) byFrame.set(d.frame, []);
      byFrame.get(d.frame).push(d);
    }
    const overlaps = [];
    for (const [frame, items] of byFrame) {
      for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) {
        const a = items[i], b = items[j];
        const ax0 = a.x - a.w / 2, ax1 = a.x + a.w / 2, ay0 = a.y - a.h, ay1 = a.y;
        const bx0 = b.x - b.w / 2, bx1 = b.x + b.w / 2, by0 = b.y - b.h, by1 = b.y;
        if (ax0 < bx1 && bx0 < ax1 && ay0 < by1 && by0 < ay1) overlaps.push({ frame, a: a.text, b: b.text });
      }
    }
    const xpDraw = window.__draws.find(d => d.text === '+150 XP');
    const goldDraw = window.__draws.find(d => d.text === '+42c');
    return { total: window.__draws.length, overlaps, xpColor: xpDraw?.color, goldColor: goldDraw?.color };
  });
  assert.equal(report.overlaps.length, 0, `expected zero frame overlaps, got ${JSON.stringify(report.overlaps.slice(0, 5))}`);
  assert.ok(report.xpColor && report.goldColor && report.xpColor !== report.goldColor, `XP color (${report.xpColor}) should differ from gold (${report.goldColor})`);

  // Scenario 3: shared partyXp also shows an XP floater for the recipient.
  await page.evaluate(() => {
    window.__draws.length = 0;
    const { x, y } = Field.hero;
    Field._debug.event({ kind: 'partyXp', actor: Online.id, x, y, enemy: 'green', level: 3, xp: 65 });
  });
  await page.waitForFunction(() => window.__draws.some(d => d.text === '+65 XP'), null, { timeout: 10000 });

  assert.deepEqual(errors, []);
  console.log(`loot-xp-floaters-ui: passed (${report.total} draws checked, 0 overlaps, xp=${report.xpColor}, gold=${report.goldColor})`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
