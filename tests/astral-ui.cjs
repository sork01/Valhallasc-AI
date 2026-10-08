// Real browser and private Rust server: Astralhollow's two gates, arrival view,
// loaded art, world-map entry and decoded original score.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-astral-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world', { startLevel: 42, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('AstralUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites && !!Field.astralSprites, null, { timeout: 60000 });
  const data = await page.evaluate(() => {
    const z = Field._debug.zones[13], p = z.portals[0], kinds = Field.astralSprites.meta.kinds;
    return { count: Field._debug.zones.length, name: z.name, objects: z.objects.length, kinds,
      npcs: z.npcs.length, quests: z.quests.length, gate: [p.x,p.y], arrival: [z.spawn.x,z.spawn.y],
      oldGate: Field._debug.zones[9].portals.find(g => g.id === 'nacre_astral_gate'),
      art: ['crystal','starstone','astraltree','astralshrub','starbloom','astrolamp','observatory','starwell'].every(k => !!City.art[k]),
      map: WorldMap._layout.length, legend: kinds.every(k => WorldMap._kinds[k]?.[1] >= 40),
      imageSizes: kinds.map(k => [Field.astralSprites.img[k].naturalWidth,Field.astralSprites.img[k].naturalHeight]) };
  });
  check(data.count === 17 && data.name === 'Astralhollow' && data.objects >= 400 && data.npcs === 7 && data.quests === 12, 'The complete zone, hub and quest catalog are loaded');
  check(data.gate[1] > data.arrival[1] && Math.hypot(data.gate[0]-data.arrival[0],data.gate[1]-data.arrival[1]) <= 4.5, 'The return gate stands in front of the arrival plaza');
  check(data.oldGate?.to === 13 && data.art && data.map === 17 && data.legend, 'Nacrehold gate, original scenery art and world-map legend are present');
  check(STUB || data.imageSizes.every(([w,h]) => w === 768 && h === 480), 'All five real 34-frame enemy atlases loaded');
  const music = await page.evaluate(async () => { const bytes=await fetch('assets/music_astral.mp3').then(r => r.arrayBuffer());const size=bytes.byteLength;const c=new AudioContext();const b=await c.decodeAudioData(bytes);await c.close();return { seconds:b.duration, bytes:size }; });
  check(music.seconds > 88 && music.seconds < 90 && music.bytes > 1000000, `The browser decodes the full original score (${JSON.stringify(music)})`);

  const debug = command => page.evaluate(command => Online.send({ type:'debug',ref:17,command }), command);
  await debug({ op:'teleport',zone:9,x:166,y:30 });
  await page.waitForFunction(() => Field.zone===9 && Math.hypot(Field.hero.x-166,Field.hero.y-30)<2,null,{timeout:10000});
  await page.evaluate(() => Online.send({type:'move',x:166,y:24}));
  await page.waitForFunction(() => Field.zone===13,null,{timeout:30000});
  await page.evaluate(() => Online.send({type:'stop'}));
  await page.waitForTimeout(700);
  const arrival = await page.evaluate(() => {
    const g=Field._debug.zones[13].portals[0],screen=Field._debug.w2s(g.x,g.y);
    return {zone:Field.zone,near:Math.hypot(Field.hero.x-64,Field.hero.y-116),screen,theme:Field.zoneTheme,objects:Field._debug.objects.length,npcs:City.npcs.length};
  });
  check(arrival.zone===13 && arrival.near<2 && arrival.theme==='astral' && arrival.objects>=400 && arrival.npcs===7,'The real Nacrehold gate arrives inside the inhabited Astralhollow sanctuary');
  check(arrival.screen[0]>100 && arrival.screen[0]<1500 && arrival.screen[1]>70 && arrival.screen[1]<830,'The return portal is visible on arrival');
  await page.screenshot({path:path.join(world.artifacts,'astral-arrival.png')});
  await debug({ op:'teleport',zone:13,x:64,y:89 });
  await page.waitForFunction(() => Field.zone===13 && Math.abs(Field.hero.y-89)<2,null,{timeout:10000});
  await page.waitForTimeout(500);
  await page.screenshot({path:path.join(world.artifacts,'astral-grove.png')});
  await debug({ op:'teleport',zone:13,x:64,y:116 });
  await page.waitForFunction(() => Field.zone===13 && Math.abs(Field.hero.y-116)<2,null,{timeout:10000});
  await page.evaluate(() => Online.send({type:'move',x:64,y:120}));
  await page.waitForFunction(() => Field.zone===9,null,{timeout:30000});
  check(await page.evaluate(() => Field.zone===9 && Math.hypot(Field.hero.x-166,Field.hero.y-32)<2), 'The visible return portal walks back to Nacrehold without bouncing');
  check(errors.length===0, `No browser errors (${errors.join('; ')})`);
  console.log(`Astralhollow UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(error => { console.error(error.stack); process.exitCode=1; }).finally(async () => {
  await browser?.close(); if(started) await call('stop_world').catch(()=>{}); await client.close();
});
