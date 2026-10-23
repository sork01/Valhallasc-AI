// RAID-MUSIC only. Real private travel/audio; future Eldmarr snapshots are replayed
// at the WebSocket boundary because RAID-BOSS-FINAL has not built the boss yet.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'raid-music-ui', version: '1' });
let browser, started = false, checks = 0, fixture = 'dormant';
const check = (value, message) => { assert.ok(value, message); checks++; };
const call = async (name, args = {}) => {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, JSON.stringify(r.content)); return r.structuredContent;
};
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...process.env } }));
  const world = await call('start_world', { godMode: true, startLevel: 99, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true,
    executablePath: process.env.CHROME_PATH || '/home/serveperry/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',
    args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [], bad = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if (r.status() >= 400 && /music_(chained_forge|eldmarr)/.test(r.url())) bad.push(r.url()); });
  // Only the test catalog borrows a pack's visual definition for the future boss.
  await page.route('**/cathedral.js', async route => {
    const r = await route.fetch();
    await route.fulfill({ response: r, body: (await r.text()) + '\nCATHEDRAL_ENEMIES.push({...CATHEDRAL_ENEMIES.find(e=>e.kind==="cf_brute"),kind:"cf_eldmarr",boss:true,name:"Eldmarr music fixture"});' });
  });
  if (process.env.MUTATE) await page.route('**/game.js', async route => {
    const r = await route.fetch(), original = await r.text();
    const body = original.replace('raidFinalFight ? eldmarrMusic : raidMusic', 'raidMusic');
    assert.notEqual(body, original, 'Music mutation must actually change the selection');
    await route.fulfill({ response: r, body });
  });
  await page.routeWebSocket('**/*', socket => {
    const server = socket.connectToServer();
    server.onMessage(message => {
      if (typeof message !== 'string') return socket.send(message);
      const packet = JSON.parse(message);
      if (packet.type === 'snapshot' && packet.players?.some(p => p.zone === 46)) {
        const own = packet.players[0], source = packet.slimes.find(s => s.kind === 'cf_brute');
        if (source) {
          const boss = { ...source, id: 2147480000, kind: 'cf_eldmarr', x: own.x + 4, y: own.y,
            hp: fixture === 'dead' ? 0 : source.maxHp, dead: fixture === 'dead', state: 'idle' };
          packet.slimes.push(boss);
          const fighting = ['engaged', 'fallen'].includes(fixture);
          packet.bossMech = fighting || fixture === 'warden' ? [{
            boss: fighting ? boss.id : source.id, clock: 1, tele: [], marked: [], frozen: [], downed: [],
            cast: null, break: null, shield: null, stunned: 0, banner: null,
          }] : [];
          if (fixture === 'fallen') { own.fallen = true; own.hp = 0; own.dead = true; }
        }
      }
      socket.send(JSON.stringify(packet));
    });
    socket.onMessage(message => server.send(message));
  });
  await page.addInitScript(() => {
    if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: .45, sfxVol: 0 }));
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Forge Listener'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero && valhalla.fmusic?.running, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  const travel = async (zone, x, y) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(z => Field.zone === z, zone, { timeout: 20000 });
  };
  const selected = async boss => {
    try {
      await page.waitForFunction(boss => (boss ? valhalla.eldmarrMusic : valhalla.raidMusic)?.running &&
        (boss ? valhalla.eldmarrMusic : valhalla.raidMusic).loaded &&
        !(boss ? valhalla.raidMusic : valhalla.eldmarrMusic).running, boss, { timeout: 20000 });
    } catch (error) {
      console.error(JSON.stringify({ boss, fixture, errors, bad, state: await page.evaluate(() => ({
        zone: Field.zone, audio: valhalla.ctx?.state,
        raid: valhalla.raidMusic && { running: valhalla.raidMusic.running, loaded: valhalla.raidMusic.loaded },
        finale: valhalla.eldmarrMusic && { running: valhalla.eldmarrMusic.running, loaded: valhalla.eldmarrMusic.loaded },
        finalKind: WORLD_MAP.zones[45].final_boss, fights: BossMech.fights,
      })) }));
      throw error;
    }
  };
  const audible = async key => {
    await page.waitForTimeout(2800);
    return page.evaluate(async key => {
      const a = valhalla.ctx.createAnalyser(); a.fftSize = 4096; valhalla[key].output.connect(a);
      await new Promise(resolve => setTimeout(resolve, 200));
      const samples = new Float32Array(a.fftSize); a.getFloatTimeDomainData(samples);
      valhalla[key].output.disconnect(a);
      return Math.sqrt(samples.reduce((n, x) => n + x * x, 0) / samples.length);
    }, key);
  };
  await debug({ op: 'set_time', hour: 23, freeze: true });
  await travel(46, 35, 303); await selected(false);
  check(await page.evaluate(() => Field.slimes.some(s => s.kind === 'cf_eldmarr' && !s.dead)), 'Dormant final boss is present in the replay');
  check(await page.evaluate(() => !valhalla.eldmarrMusic.running), 'Proximity to the dormant final boss keeps the dungeon score');
  check(await page.evaluate(() => Math.abs(valhalla.raidMusic.duration - 64 * 4 * 60 / 152) < .04), 'Forge loop decodes at 152 BPM / 64 bars');
  check(await audible('raidMusic') > .0001, 'Forge score produces actual audio');
  check(await page.evaluate(() => DayNight.nightMix === 0 && !valhalla.nightMusic.running && !valhalla.emberwakeNightMusic.running), 'The indoor raid keeps its score at night');
  fixture = 'warden'; await page.waitForFunction(() => BossMech.active); await selected(false);
  check(await page.evaluate(() => !valhalla.eldmarrMusic.running), 'An ordinary Warden fight keeps the dungeon score');
  fixture = 'engaged'; await selected(true);
  check(await page.evaluate(() => Math.abs(valhalla.eldmarrMusic.duration - 96) < .04), 'Eldmarr loop decodes at 160 BPM / 64 bars');
  check(await audible('eldmarrMusic') > .0001, 'Final-boss score produces actual audio');
  fixture = 'fallen'; await page.waitForFunction(() => !!Field.hero.fallen); await selected(true);
  check(await page.evaluate(() => valhalla.eldmarrMusic.running), 'A fallen fighter keeps hearing the ongoing boss fight');
  fixture = 'dormant'; await page.waitForFunction(() => !BossMech.active); await selected(false);
  check(await page.evaluate(() => !valhalla.eldmarrMusic.running), 'A wipe or evade returns to the Forge score');
  fixture = 'engaged'; await selected(true); fixture = 'dead'; await selected(false);
  check(await page.evaluate(() => Field.slimes.some(s => s.kind === 'cf_eldmarr' && s.dead)), 'Boss death returns to the Forge score');
  await page.evaluate(() => Prefs.set({ musicVol: .3, sound: true }));
  await page.waitForFunction(() => Math.abs(valhalla.raidMusic.output.gain.value - .09) < .002);
  check(true, 'Saved volume reaches the dungeon player');
  fixture = 'engaged'; await selected(true);
  await page.waitForFunction(() => Math.abs(valhalla.eldmarrMusic.output.gain.value - .09) < .002);
  check(true, 'Saved volume reaches the boss player');
  await page.evaluate(() => Prefs.set({ sound: false }));
  await page.waitForFunction(() => valhalla.raidMusic.output.gain.value < .001 && valhalla.eldmarrMusic.output.gain.value < .001);
  check(true, 'Mute reaches both raid players');
  fixture = 'dormant'; await selected(false);
  check(await page.evaluate(() => valhalla.raidMusic.output.gain.value < .001), 'A track switch remains muted');
  await travel(45, 22, 137);
  await page.waitForFunction(() => valhalla.emberwakeNightMusic.running && !valhalla.raidMusic.running && !valhalla.eldmarrMusic.running);
  check(true, 'Leaving the raid restores the outdoor night music and stops both raid players');
  await page.evaluate(() => Prefs.set({ sound: true }));
  await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.waitForFunction(() => Online.connected && Field.hero, null, { timeout: 60000 });
  await page.keyboard.press('Shift'); await travel(46, 35, 303); await selected(false);
  await page.waitForFunction(() => Math.abs(valhalla.raidMusic.output.gain.value - .09) < .002);
  check(true, 'Reload preserves the saved volume');
  check(await page.evaluate(() => !WORLD_MAP.zones[45].sealedTemplate), 'The public raid entrance is open');
  check(errors.length === 0, 'No browser errors: ' + JSON.stringify(errors));
  check(bad.length === 0, 'No missing raid audio assets');
  const result = { passed: true, checks, artifacts: world.artifacts,
    bossFixture: 'Replayed future cf_eldmarr snapshots, not a live boss-mechanics test' };
  fs.writeFileSync(path.join(world.artifacts, 'raid-music-result.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) try { await call('stop_world'); } catch {}
  await client.close();
});
