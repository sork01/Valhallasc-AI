// Only height-changing travel: real crossings plus visible direction, motion and reduced-motion checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const root = path.resolve(__dirname, '..'), candidate = process.env.JOURNEY_CANDIDATE;
const world = new TestWorld(); world.godMode = true; world.startLevel = 99;
let browser, checks = 0;
const check = (ok, text) => { assert.ok(ok, text); console.log(`${++checks}: ${text}`); };
(async () => {
  await world.start();
  for (const touch of process.env.JOURNEY_FINAL ? [true] : process.env.MUTATE ? [false] : [false, true]) {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: touch ? { width: 844, height: 390 } : { width: 1280, height: 800 },
      isMobile: touch, hasTouch: touch, reducedMotion: touch ? 'reduce' : 'no-preference' });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    if (candidate) {
      await page.context().grantPermissions(['local-network-access'], { origin: world.url });
      for (const file of ['index.html', 'field.js', 'online.css', 'zonejourney.js']) await page.route(file === 'index.html' ? world.url : '**/' + file,
        r => r.fulfill({ body: fs.readFileSync(path.join(candidate, file)), contentType: file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html' }));
    }
    if (process.env.MUTATE) await page.route('**/zonejourney.js', async r => {
      const source = fs.readFileSync(path.join(candidate || path.join(root, 'client'), 'zonejourney.js'), 'utf8');
      await r.fulfill({ body: source.replace('    if (!active || still || active.up === null) return;', '    return;'), contentType: 'text/javascript' });
    });
    await page.addInitScript(touch => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: touch ? 'sv' : 'en', sound: false, char: null, draft: null }));
    }, touch);
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill('SkyAndSea'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
    const crossings = process.env.MUTATE ? [] : touch ? [[6,7],[13,9]] : [[6,7],[7,8],[7,9],[13,8],[13,9],[8,9]];
    for (const [from,to] of crossings) {
      const p = await page.evaluate(([from,to]) => Field._debug.zones[from].portals.find(p => p.to === to && p.walk), [from,to]);
      assert.ok(p, 'real walking crossing');
      await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
      await debug({ op: 'teleport', zone: from, x: p.x-p.walk[0]*6, y: p.y-p.walk[1]*6 });
      await page.waitForFunction(from => Field.zone === from, from); await page.waitForTimeout(1300);
      // The live approach must paint the label on the actual game canvas.
      if (from !== 8) {
        const labels = await page.evaluate(() => {
          const g = document.getElementById('fieldcv').getContext('2d'), orig = g.fillText, texts = [];
          g.fillText = function (text,...args) { texts.push(text); return orig.call(this,text,...args); };
          try { Field._debug.drawFrame(10); return texts; } finally { g.fillText = orig; }
        });
        check(labels.some(s => s.startsWith(to === 7 ? '↑ ' : '↓ ')), `${from}->${to}: approach paints the vertical direction`);
      }
      await page.evaluate(p => Field.setTouchDirection(p.walk[0]-p.walk[1], p.walk[0]+p.walk[1]), p);
      await page.waitForFunction(to => Field.zone === to, to, { timeout: 20000 });
      await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
      const text = await page.locator('#zone-journey').innerText();
      const expected = touch ? (to === 7 ? 'Stiger upp mot himlen' : 'Sjunker ner till havsbotten') : from === 8 ? 'Along the ocean floor' : to === 7 ? 'Ascending into the sky' : 'Descending to the ocean floor';
      check(text.includes(expected), `${from}->${to}: real crossing announces ${expected}`);
      check(await page.locator('#zone-altitude').isVisible(), 'Destination retains its sky/seabed label');
      const badge = await page.locator('#zone-altitude').boundingBox();
      check(badge.x >= -.5 && badge.x+badge.width <= (touch ? 844 : 1280)+.5, 'Persistent altitude label stays inside the viewport: '+JSON.stringify(badge));
      const box = await page.locator('#zone-journey').boundingBox();
      check(box.x >= 0 && box.y >= 0 && box.x+box.width <= (touch ? 844 : 1280) && box.y+box.height <= (touch ? 390 : 800), 'Arrival caption fits the viewport');
      await page.screenshot({ path: path.join(world.runDir, `journey-${from}-${to}-${touch ? 'sv-touch' : 'en'}.png`) });
    }
    const paint = await page.evaluate(() => {
      const c = document.createElement('canvas'); c.width=1600; c.height=900; const g=c.getContext('2d');
      const now=performance.now.bind(performance), start=now(), zs=Field._debug.zones;
      const sample = (from,to,at,still) => {
        performance.now=()=>start; ZoneJourney.enter(zs[from],zs[to],false);
        performance.now=()=>start+at; g.clearRect(0,0,1600,900);
        const arcs=[], ellipses=[], arc=g.arc, ellipse=g.ellipse;
        g.arc=function(x,y,...args){arcs.push(y);return arc.call(this,x,y,...args);};
        g.ellipse=function(x,y,...args){ellipses.push(y);return ellipse.call(this,x,y,...args);};
        try { ZoneJourney.draw(g,1600,900,still); } finally { g.arc=arc; g.ellipse=ellipse; }
        const data=g.getImageData(0,0,1600,900).data; let visible=0;for(let i=3;i<data.length;i+=4)if(data[i]>30)visible++;
        return {arcs,ellipses,visible};
      };
      try {
        return { skyA:sample(6,7,600,false), skyB:sample(6,7,700,false), seaA:sample(7,8,600,false), seaB:sample(7,8,700,false),
          still:sample(7,8,600,true), expired:sample(7,8,3500,false), flat:sample(8,9,600,false) };
      } finally { performance.now=now; ZoneJourney.clear(); }
    });
    check(paint.skyA.visible > 20000 && paint.seaA.visible > 20000, 'Climb and dive paint substantial visible atmosphere');
    check(paint.skyB.ellipses[0] > paint.skyA.ellipses[0], 'Clouds move downward during ascent');
    check(paint.seaB.arcs[0] < paint.seaA.arcs[0] && paint.seaB.ellipses[0] < paint.seaA.ellipses[0], 'Bubbles and the ocean surface move upward during descent');
    check(paint.still.visible === 0 && paint.expired.visible === 0 && paint.flat.visible === 0, 'Reduced motion, expired travel and seabed-to-seabed travel have no moving overlay');
    const difference = await page.evaluate(() => {
      const g=document.getElementById('fieldcv').getContext('2d'), original=ZoneJourney.draw, now=performance.now.bind(performance), start=now();
      try {
        performance.now=()=>start; ZoneJourney.enter(Field._debug.zones[7],Field._debug.zones[8],false);
        performance.now=()=>start+600;
        // Force the same motion preference for this paired-pixel presentation fixture.
        ZoneJourney.draw=(g,w,h)=>original(g,w,h,false); Field._debug.drawFrame(10);
        const withTrip=g.getImageData(0,0,g.canvas.width,g.canvas.height).data;
        ZoneJourney.draw=()=>{}; Field._debug.drawFrame(10);
        const withoutTrip=g.getImageData(0,0,g.canvas.width,g.canvas.height).data;
        let changed=0;for(let i=0;i<withTrip.length;i+=4)if(Math.abs(withTrip[i]-withoutTrip[i])+Math.abs(withTrip[i+1]-withoutTrip[i+1])+Math.abs(withTrip[i+2]-withoutTrip[i+2])>12)changed++;
        return changed;
      } finally { ZoneJourney.draw=original; performance.now=now; ZoneJourney.clear(); }
    });
    check(difference > 3000, 'The game render paints the travel effect into visible canvas pixels');
    await page.evaluate(() => ZoneJourney.enter(Field._debug.zones[6],Field._debug.zones[7],true));
    check(await page.locator('#zone-journey').isHidden(), 'Joining/reconnecting does not replay a climb');
    await page.evaluate(() => ZoneJourney.enter(Field._debug.zones[7],Field._debug.zones[6],false));
    check(await page.locator('#zone-altitude').isHidden(), 'Returning to land clears the persistent altitude label');
    await page.waitForTimeout(4700);
    check(await page.locator('#zone-journey').isHidden(), 'Arrival caption dismisses itself');
    check(errors.length === 0, 'No browser errors: '+errors.join('; '));
    await browser.close(); browser=null;
  }
  console.log(`zone-journey-ui: ${checks} passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode=1; }).finally(async () => { await browser?.close(); await world.stop(); });
