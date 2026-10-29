// Focused command/snapshot checks plus real dressed renders of both dances on all five classes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld();
let browser, checks = 0;
const check = (ok, label) => { assert.ok(ok, label); console.log(`${++checks}: ${label}`); };
const candidate = process.env.DANCE_CANDIDATE;
async function scripts(page) {
  if (candidate) for (const file of ['field.js', 'magesprite.js']) await page.route('**/' + file, route => route.fulfill({
    body: fs.readFileSync(path.join(candidate, file), 'utf8'), contentType: 'text/javascript',
  }));
  if (process.env.MUTATE) await page.route('**/magesprite.js', async route => {
    const body = candidate ? fs.readFileSync(path.join(candidate, 'magesprite.js'), 'utf8') : await (await route.fetch()).text();
    await route.fulfill({ body: body.replace('const dance = MageSprite.dancePose(h, this.look.gender);', 'const dance = null;'), contentType: 'text/javascript' });
  });
}
(async () => {
  await world.start();
  await world.connect({ bot: 'Freya', class: 'hunter', gender: 'female' });
  await world.debug('Freya', { op: 'teleport', zone: 0, x: 36, y: 79 });
  browser = await chromium.launch({ headless: true });
  if (!process.env.DANCE_ART_ONLY) {
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await scripts(page);
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false }));
    });
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Ulfar'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0 && Field.warriorSprites);
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone: 0, x: 36, y: 79 } }));
    await page.waitForFunction(() => Field.hero.x > 35 && Field.hero.y > 78);
    const submit = async text => {
      await page.evaluate(() => Online.focusChat());
      await page.locator('#chat-input').fill(text); await page.locator('#chat-input').press('Enter');
    };
    await submit('/dance');
    await page.waitForFunction(() => Number.isFinite(Field.hero.danceT));
    const id = await page.evaluate(() => Online.id);
    await world.waitFor(() => Number.isFinite(world.snapshot.players.find(p => p.id === id)?.danceT), 5000, 'Observer sees male dance');
    check(true, 'Typing /dance starts the local dance and an observer receives it');
    const start = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, danceT: Field.hero.danceT }));
    await page.waitForFunction(t => Field.hero.danceT > t + 1.1, start.danceT);
    check(await page.evaluate(at => Math.hypot(Field.hero.x - at.x, Field.hero.y - at.y) < .01, start), 'The dance loops in place through idle network input');
    check(await page.evaluate(() => !Field.bubbleText(Online.id) && !document.getElementById('chat-log').textContent.includes('/dance')), 'The command does not become a chat message or bubble');
    await world.action('Freya', { type: 'chat', text: '/dance' });
    await page.waitForFunction(() => Field.remotePlayers.some(p => p.look.name === 'Freya' && Number.isFinite(p.danceT)));
    check(await page.evaluate(() => Field.remotePlayers.find(p => p.look.name === 'Freya').look.gender === 'female'), 'A nearby female character dances in the same view');
    await submit('/DANCE');
    await page.waitForFunction(() => Field.hero.danceT === null);
    check(true, 'Typing /dance again stops, even though focusing chat sends Stop');
    await page.waitForTimeout(1100); await submit('/dance');
    await page.waitForFunction(() => Number.isFinite(Field.hero.danceT));
    await page.keyboard.down('d');
    await page.waitForFunction(() => Field.hero.danceT === null); await page.keyboard.up('d');
    check(true, 'Keyboard movement stops dancing');
    await world.action('Freya', { type: 'move', x: 37, y: 79 });
    await page.waitForFunction(() => Field.remotePlayers.find(p => p.look.name === 'Freya')?.danceT === null);
    check(true, 'Observers see the dance stop when its player moves');
    check(errors.length === 0, 'Command and multiplayer view have no browser errors: ' + errors.join('; '));
    await page.close();
  }

  // A fresh lightweight page per class keeps decoded atlases within the browser resource cap.
  for (const cls of ['warrior', 'mage', 'assassin', 'priest', 'hunter']) {
    const art = await browser.newPage({ viewport: { width: 1440, height: 430 } });
    await scripts(art);
    await art.context().grantPermissions(['local-network-access'], { origin: world.url });
    await art.route('**/dance-art-fixture', route => route.fulfill({ contentType: 'text/html', body:
      '<!doctype html><canvas width="1440" height="430"></canvas>' + ['items', 'magesprite', 'warriorsprite', 'assassinsprite', 'priestsprite', 'huntersprite'].map(s => `<script src="/${s}.js"></script>`).join('') }));
    await art.goto(world.url + 'dance-art-fixture');
    // The normal UI test uses stubs; this isolated page explicitly loads the actual atlas source.
    const result = await art.evaluate(async cls => {
      window.__valhallaTestSprites = false;
      const Base = { warrior: WarriorSprite, mage: MageSprite, assassin: AssassinSprite, priest: PriestSprite, hunter: HunterSprite }[cls];
      const canvas = document.querySelector('canvas'), g = canvas.getContext('2d');
      g.fillStyle = '#20313d'; g.fillRect(0, 0, 1440, 430);
      const hashes = [], changes = [], used = [], choreography = [];
      for (const [row, gender] of ['female', 'male'].entries()) {
        const look = { class: cls, gender, name: cls, head: 'none', shoulders: 'none', gloves: 'none', pants: 'none', necklace: 'none', accessory: 'none', cloak: 'none' };
        const sprite = await Base.variant(look).load(look);
        for (const [slot, value] of Object.entries(sprite.equipment)) if (value && value !== 'none') await sprite.source.ensure(slot + '_' + value);
        g.font = '18px sans-serif'; g.fillStyle = '#ffe3a0'; g.fillText(`${gender} ${cls}`, 12, row * 215 + 22);
        const samples = [], poses = [];
        const temp = document.createElement('canvas'); temp.width = 180; temp.height = 190; const tg = temp.getContext('2d');
        for (let k = 0; k < 16; k++) {
          const danceT = k / 8 + .03125, h = { look, danceT, fx: 1, fy: 1, dead: false, hurtT: 0, atkT: 0, moving: false };
          const calls = [], original = sprite.frame;
          sprite.frame = function (...args) { calls.push(args); return original.apply(this, args); };
          tg.clearRect(0, 0, 180, 190); tg.save(); tg.translate(90, 172); sprite.draw(tg, h, danceT); tg.restore();
          sprite.frame = original;
          const pixels = tg.getImageData(0, 0, 180, 190).data;
          let opaque = 0, edge = 0, hash = 2166136261;
          for (let i = 0; i < pixels.length; i++) { hash = Math.imul(hash ^ pixels[i], 16777619); if (i % 4 === 3 && pixels[i]) { opaque++; const p = (i - 3) / 4, x = p % 180, y = Math.floor(p / 180); if (x === 0 || x === 179 || y === 0 || y === 189) edge++; } }
          if (opaque < 500 || edge) throw Error(`${cls}/${gender}/${k}: empty or clipped dance (${opaque}/${edge})`);
          samples.push(hash); poses.push(calls[0]?.join('/'));
          if (k % 2 === 0) g.drawImage(temp, (k / 2) * 180, row * 215 + 25);
        }
        hashes.push(samples); choreography.push(poses); changes.push(new Set(poses).size); used.push(sprite.equipment.armor !== 'none' && sprite.equipment.weapon !== 'none');
      }
      return { hashes, changes, used, choreography, png: canvas.toDataURL() };
    }, cls);
    for (let body = 0; body < 2; body++) {
      check(new Set(result.hashes[body]).size >= 8 && result.changes[body] >= 4, `${cls}/${body === 0 ? 'female' : 'male'}: ${new Set(result.hashes[body]).size} distinct renders and ${result.changes[body]} dance poses reach the real compositor`);
      check(result.used[body], `${cls}/${body === 0 ? 'female' : 'male'}: equipped armor and weapon remain in the dance`);
    }
    check(JSON.stringify(result.choreography[0]) !== JSON.stringify(result.choreography[1]), `${cls}: the two body types have different dance sequences`);
    fs.writeFileSync(path.join(world.runDir, `dance-${cls}.png`), Buffer.from(result.png.split(',')[1], 'base64'));
    await art.close();
  }
  console.log(`dance-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close().catch(() => {}); await world.stop().catch(() => {});
});
