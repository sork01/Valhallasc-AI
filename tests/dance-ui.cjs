// Command/snapshot checks plus real dressed renders of all eight dances on all five classes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { playGuest } = require('./lib/guest.cjs');
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
    const call = 'const dance = MageSprite.dancePose(h, this.look);';
    const replacement = process.env.MUTATE === 'race'
      ? "const dance = MageSprite.dancePose(h, { ...this.look, race: 'human' });"
      : 'const dance = null;';
    assert.ok(body.includes(call), 'Mutation must replace the dance renderer call');
    await route.fulfill({ body: body.replace(call, replacement), contentType: 'text/javascript' });
  });
}
(async () => {
  await world.start();
  browser = await chromium.launch({ headless: true });
  if (!process.env.DANCE_ART_ONLY) {
    await world.connect({ bot: 'Freya', class: 'hunter', gender: 'female' });
    await world.debug('Freya', { op: 'teleport', zone: 0, x: 36, y: 79 });
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await scripts(page);
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false }));
    });
    await page.goto(world.url); await page.locator('#start').click(); await playGuest(page);
    await page.locator('#cls-warrior').click(); await page.locator('#gender-male').click();
    await page.locator('#create-race').selectOption('tidekin');
    await page.locator('#name').fill('Ulfar'); await page.locator('#go').click({ timeout: 60000 });
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
    await world.waitFor(() => Number.isFinite(world.snapshot.players.find(p => p.id === id)?.danceT), 5000, 'Observer sees Tidekin dance');
    const observerLook = world.snapshot.players.find(p => p.id === id).look;
    check(observerLook.race === 'tidekin' && observerLook.gender === 'male' &&
      await page.evaluate(() => Field.warriorSprites.look.race === 'tidekin' && Field.warriorSprites.look.gender === 'male'),
    'Typing /dance starts a male Tidekin dance with the same appearance for the dancer and observer');
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
    // Chat is rate limited in simulation time, which can lag wall time under the CPU cap.
    await world.waitFor(() => world.snapshot.players.find(p => p.id === id)?.danceT === null);
    const stoppedAt = world.snapshot.time;
    await world.waitFor(() => world.snapshot.time >= stoppedAt + 1);
    await submit('/dance');
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
      '<!doctype html><canvas></canvas>' + ['items', 'magesprite', 'warriorsprite', 'assassinsprite', 'priestsprite', 'huntersprite'].map(s => `<script src="/${s}.js"></script>`).join('') }));
    await art.goto(world.url + 'dance-art-fixture');
    // The normal UI test uses stubs; this isolated page explicitly loads the actual atlas source.
    const result = await art.evaluate(async cls => {
      window.__valhallaTestSprites = false;
      const Base = { warrior: WarriorSprite, mage: MageSprite, assassin: AssassinSprite, priest: PriestSprite, hunter: HunterSprite }[cls];
      const races = ['human', 'mothkin', 'tidekin', 'gnome'], genders = ['female', 'male'];
      const canvas = document.querySelector('canvas');
      canvas.width = 1440; canvas.height = 215 * races.length * genders.length;
      const g = canvas.getContext('2d'), temp = document.createElement('canvas');
      temp.width = 180; temp.height = 190;
      const tg = temp.getContext('2d', { willReadFrequently: true });
      g.fillStyle = '#20313d'; g.fillRect(0, 0, canvas.width, canvas.height);
      g.font = '18px sans-serif'; g.fillStyle = '#ffe3a0';
      const dances = [];
      for (const [body, gender] of genders.entries()) {
        const look = { class: cls, gender, name: cls, head: 'none', shoulders: 'none', gloves: 'none', pants: 'none', necklace: 'none', accessory: 'none', cloak: 'none' };
        const sprite = await Base.variant(look).load(look);
        for (const [slot, value] of Object.entries(sprite.equipment)) if (value && value !== 'none') await sprite.source.ensure(slot + '_' + value);
        const used = ['armor', 'weapon'].every(slot => sprite.source.parts[slot + '_' + sprite.equipment[slot]]);
        for (const [index, race] of races.entries()) {
          const row = index * genders.length + body;
          sprite.set({ ...look, race });
          g.fillText(`${race} ${gender} ${cls}`, 12, row * 215 + 22);
          const samples = new Set(), poses = [];
          const calls = [], original = sprite.frame;
          sprite.frame = function (...args) { calls.push(args.join('/')); return original.apply(this, args); };
          for (let k = 0; k < 24; k++) {
            const danceT = k / 8 + .03125, h = { danceT, fx: 1, fy: 1 };
            calls.length = 0;
            tg.clearRect(0, 0, 180, 190); tg.save(); tg.translate(90, 172); sprite.draw(tg, h, danceT); tg.restore();
            const pixels = tg.getImageData(0, 0, 180, 190).data;
            let opaque = 0, edge = 0, hash = 2166136261;
            for (let i = 0; i < pixels.length; i += 4) {
              for (let channel = 0; channel < 4; channel++) hash = Math.imul(hash ^ pixels[i + channel], 16777619);
              if (!pixels[i + 3]) continue;
              opaque++;
              const x = (i / 4) % 180, y = Math.floor(i / 720);
              if (x === 0 || x === 179 || y === 0 || y === 189) edge++;
            }
            if (opaque < 500 || edge) throw Error(`${cls}/${race}/${gender}/${k}: empty or clipped dance (${opaque}/${edge})`);
            samples.add(hash); poses.push(calls[0]);
            if (k % 3 === 0) g.drawImage(temp, (k / 3) * 180, row * 215 + 25);
          }
          sprite.frame = original;
          dances.push({ label: `${cls}/${race}/${gender}`, poses, renders: samples.size, used });
        }
      }
      const legacy = genders.every(gender => Array.from({ length: 24 }, (_, k) => ({ danceT: k / 8 })).every(h =>
        JSON.stringify(Base.dancePose(h, { gender })) === JSON.stringify(Base.dancePose(h, { race: 'human', gender }))));
      return { dances, legacy, png: canvas.toDataURL() };
    }, cls);
    for (const { label, poses, renders, used } of result.dances) {
      const distinct = new Set(poses).size;
      check(renders >= 8 && distinct >= 4 && poses.every(pose => pose?.startsWith('walk/')),
        `${label}: ${renders} distinct renders and ${distinct} dance poses reach the real compositor`);
      check(used, `${label}: equipped armor and weapon are loaded for the dance`);
    }
    check(new Set(result.dances.map(dance => JSON.stringify(dance.poses))).size === 8,
      `${cls}: all eight race and body combinations use different choreography`);
    check(result.legacy, `${cls}: older appearances use the two Human dances`);
    fs.writeFileSync(path.join(world.runDir, `dance-${cls}.png`), Buffer.from(result.png.split(',')[1], 'base64'));
    await art.close();
  }
  console.log(`dance-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close().catch(() => {}); await world.stop().catch(() => {});
});
