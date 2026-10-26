// Only the narrow Crags rivers: open molten surface, collision footprint and real-zone view.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { execFileSync } = require('node:child_process');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const root = path.resolve(__dirname, '..'), out = path.join(root, 'test-results/crags-lava');
let browser, checks = 0; const world = new TestWorld();
const check = (ok, label) => { assert.ok(ok, label); checks++; };
(async () => {
  requireMemoryLimit(); fs.mkdirSync(out, { recursive: true });
  world.godMode = true; world.startLevel = 99; await world.start();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1024, height: 768 }, reducedMotion: 'reduce' }), errors = [];
  page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/emberwakeart.js', route => route.fulfill({ contentType: 'text/javascript', body: execFileSync('git', ['show', 'HEAD:client/emberwakeart.js'], { cwd: root, encoding: 'utf8' }) }));
  await page.addInitScript(() => {
    window.AudioContext = window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, lowGraphics: true, lowGraphicsSet: true }));
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Lava View'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero && window.EmberwakeArt);
  const sample = await page.evaluate(() => {
    const z = WORLD_MAP.zones[0], pieces = z.objects.filter(o => o.kind === 'lava');
    let total = 0, hot = 0, crust = 0, green = 0, changed = 0;
    // Sample the actual 269-circle footprint, including its narrow banks.
    for (let y = 10; y < 77; y += .15) for (let x = 1; x < 95; x += .15) {
      let edge = -Infinity;
      for (const o of pieces) if (Math.abs(x-o.x) < o.r && Math.abs(y-o.y) < o.r) edge = Math.max(edge, o.r-Math.hypot(x-o.x,y-o.y));
      if (edge < .25) continue;
      const a = EmberwakeArt.moltenColor(x,y,edge,true), b = EmberwakeArt.moltenColor(x,y,edge);
      total++; if (a[0]>180 && a[0]>a[1]*1.7) hot++; if (a[0]<115) crust++; green+=a[1];
      if (a.some((v,i) => v!==b[i])) changed++;
    }
    // Render a real river segment through both themes. Colour may differ;
    // alpha must still describe the same obstacles and clear fords.
    const ew = { ...z, theme: 'emberwake', objects: pieces.map(o => ({ ...o, kind: 'ew_lava' })) };
    const render = zone => { const c=document.createElement('canvas');c.width=c.height=640;const g=c.getContext('2d');EmberwakeArt.molten(g,{x0:48,y0:48,ox:-320,oy:2056},12,88,44,zone);return g.getImageData(0,0,640,640).data; };
    const a=render(z), b=render(ew); let opaque=0, footprint=0, differences=0;
    for (let i=0;i<a.length;i+=4) { if(a[i+3])opaque++;if(a[i+3]!==b[i+3])footprint++;if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])differences++; }
    return {total,hot:hot/total,crust:crust/total,green:green/total,changed:changed/total,opaque,footprint,differences};
  });
  check(sample.total>10000, 'sample the full Crags river network');
  check(sample.hot>.85 && sample.crust<.05, 'narrow rivers read as continuous molten lava: '+JSON.stringify(sample));
  check(sample.green<100 && sample.changed>.9, 'Crags lava has its own deep red palette');
  check(sample.opaque>10000 && sample.footprint===0 && sample.differences>10000, 'redrawn terrain retains every bank and ford');
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  await debug({ op:'set_time',hour:12,freeze:true }); await debug({ op:'set_weather',kind:'clear' });
  for (const [x,y,name] of [[56,58,'river'],[74,56,'ford']]) {
    await debug({op:'teleport',zone:1,x,y}); await page.waitForFunction(([x,y])=>Field.zone===1&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1,[x,y]);
    await page.waitForTimeout(600); await page.locator('#fieldcv').screenshot({path:path.join(out,name+'.png')});
  }
  check(errors.length===0, 'no renderer errors: '+errors.join('; '));
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({checks,sample},null,2)); console.log(JSON.stringify({checks,sample,out}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
