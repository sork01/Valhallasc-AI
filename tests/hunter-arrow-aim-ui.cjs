// BUG-HUNTER-ARROW-AIM: the arrow's drawn shaft must point along the projected flight direction, in 16 directions.
// The ground is isometric, so a world step (fx, fy) is drawn as ((fx - fy) * 44, (fx + fy) * 22); the shaft is the 2-point
// '#342519' stroke of drawHunterArrow.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-hunter-arrow-aim', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
const SKILLS = ['powershot', 'multishot', 'piercingarrow', 'explosivearrow'];
const angleDiff = (a, b) => Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b))) * 180 / Math.PI;

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 99, godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false }));
    // Record every shaft drawn: beginPath resets, moveTo/lineTo collect, a stroke in the shaft's dark outline colour emits.
    window.__shafts = []; let path = [];
    const proto = CanvasRenderingContext2D.prototype, begin = proto.beginPath, move = proto.moveTo, line = proto.lineTo, stroke = proto.stroke;
    proto.beginPath = function () { path = []; return begin.call(this); };
    proto.moveTo = function (x, y) { path.push([x, y]); return move.call(this, x, y); };
    proto.lineTo = function (x, y) { path.push([x, y]); return line.call(this, x, y); };
    proto.stroke = function () {
      if (this.strokeStyle === '#342519' && path.length === 2) window.__shafts.push({ dx: path[1][0] - path[0][0], dy: path[1][1] - path[0][1] });
      return stroke.call(this);
    };
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-hunter').click(); await page.locator('#name').fill('ArrowAim');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99, null, { timeout: 60000 });
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 12).map(s => s.id));
  for (const id of nearby) await debug({ op: 'kill_enemy', id });
  await page.waitForFunction(() => Field.slimes.every(s => s.dead || Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) >= 12));
  fs.mkdirSync(path.join(world.artifacts, 'arrow-aim'), { recursive: true });

  let checked = 0;
  for (const skill of SKILLS) for (let k = 0; k < 16; k++) {
    const angle = k * Math.PI / 8, fx = Math.cos(angle), fy = Math.sin(angle);
    await debug({ op: 'reset_cooldowns' }); await debug({ op: 'set_resource', amount: 1000 });
    await page.waitForFunction(() => Field._debug.bolts.length === 0 && Field.hero.resource >= 60);
    await page.evaluate(() => { window.__shafts.length = 0; });
    const seen = await page.evaluate(({ skill, fx, fy }) => new Promise((resolve, reject) => {
      const deadline = performance.now() + 4000, mine = [];
      function sample() {
        for (const b of Field._debug.bolts) if (b.skill === skill && !mine.some(m => m.id === b.id)) mine.push({ id: b.id, fx: b.fx, fy: b.fy });
        if (mine.length && window.__shafts.length >= 3) { resolve({ bolts: mine, shafts: window.__shafts.slice(), image: document.querySelector('#fieldcv').toDataURL('image/png') }); return; }
        if (performance.now() > deadline) { reject(new Error(`${skill}/${fx.toFixed(2)},${fy.toFixed(2)}: no arrow drawn`)); return; }
        requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
      Online.send({ type: 'skill', id: skill, fx, fy });
    }), { skill, fx, fy });
    // Flight direction as the server sent it: the middle bolt of the fan flies exactly where the player aimed.
    const middle = seen.bolts[Math.floor(seen.bolts.length / 2)];
    assert.ok(Math.hypot(middle.fx - fx, middle.fy - fy) < 1e-6 || skill === 'multishot', `${skill} #${k}: flies (${middle.fx}, ${middle.fy}), aimed (${fx}, ${fy})`);
    // The drawn shaft of each bolt in flight: at least one shaft must match a bolt's projected direction.
    for (const bolt of seen.bolts) {
      const expected = Math.atan2((bolt.fx + bolt.fy) * 22, (bolt.fx - bolt.fy) * 44);
      const match = seen.shafts.some(s => angleDiff(Math.atan2(s.dy, s.dx), expected) < 4);
      assert.ok(match, `${skill} #${k}: no drawn shaft within 4 degrees of ${(expected * 180 / Math.PI).toFixed(1)} (drawn: ${seen.shafts.slice(0, 4).map(s => (Math.atan2(s.dy, s.dx) * 180 / Math.PI).toFixed(1))})`);
    }
    if (skill === 'powershot') fs.writeFileSync(path.join(world.artifacts, 'arrow-aim', `powershot-${String(k).padStart(2, '0')}.png`), Buffer.from(seen.image.split(',')[1], 'base64'));
    checked++;
  }
  assert.equal(checked, SKILLS.length * 16);
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`${checked} arrows drawn along their flight direction in a private real client: ${path.join(world.artifacts, 'arrow-aim')}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
