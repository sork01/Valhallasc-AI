if (process.env.CHECK_ONLY === 'atlas') {
  require('./organic-atlas-ui.cjs');
} else {
// Focused checks for held mouse travel, forward horse playback and portal-aligned geography.
// Run with scripts/test-touch-bounded.sh. MUTATE=mouse|horse|atlas must fail the corresponding assertion.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { requireMemoryLimit } = require('./lib/touch.cjs');
requireMemoryLimit();
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
(async () => {
  const world = new TestWorld(); world.startLevel = 99;
  let browser, checks = 0;
  const check = (v, why) => { assert.ok(v, why); checks++; };
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      window.__valhallaTestSprites = true; // isolate input/geography checks from unrelated atlas decoding
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
    });
    if (process.env.MUTATE) {
      const file = { mouse: 'field.js', horse: 'mountart.js', atlas: 'worldmap.js' }[process.env.MUTATE];
      let source = fs.readFileSync(path.join(root, 'client', file), 'utf8');
      if (process.env.MUTATE === 'mouse') source = source.replace('[pointer.x, pointer.y] = pointerWorld(pointer);', '/* stale world destination */');
      if (process.env.MUTATE === 'horse') source = source.replace("if (id === 'horse' && clip === 'run') i = (C.n - i) % C.n;", '/* backwards hooves */');
      if (process.env.MUTATE === 'atlas') source = source.replace('  const GROUND =', '  LAYOUT[1].y = LAYOUT[0].y + 10;\n  const GROUND =');
      await page.route(`**/${file}`, r => r.fulfill({ contentType: 'text/javascript', body: source }));
    }
    await page.goto(world.url);
    await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill('TravelCheck');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    await page.evaluate(() => {
      window.travelSent = [];
      const send = Online.send;
      Online.send = function(m) { travelSent.push({ ...m, at: performance.now() }); return send.call(this, m); };
      Online.send({ type: 'debug', command: { op: 'give_mount', mount: 'horse' } });
    });
    await page.waitForFunction(() => Field.hero.mounts?.includes('horse'));
    const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
    const stand = async (zone, x, y) => {
      await page.mouse.up();
      await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
      await debug({ op: 'teleport', zone, x, y });
      await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.x - x, Field.hero.y - y) < .5, [zone, x, y]);
      await page.waitForTimeout(350); // settle the interpolated camera before projecting the cursor
    };
    if (!process.env.CHECK_ONLY || process.env.CHECK_ONLY === 'mouse') {
      for (const mounted of [false, true]) {
        await stand(4, 80, 145);
        await page.evaluate(mounted => Online.send({ type: 'mount', mounted }), mounted);
        await page.waitForFunction(mounted => Field.hero.mounted === mounted, mounted);
        const point = await page.evaluate(() => {
          const cv = document.querySelector('#fieldcv'), r = cv.getBoundingClientRect();
          const [x, y] = Field._debug.w2s(80, 139);
          return { x: r.left + x / 1600 * r.width, y: r.top + y / 1600 * r.width };
        });
        await page.evaluate(() => { travelSent.length = 0; });
        await page.mouse.move(point.x, point.y); await page.mouse.down();
        await page.waitForTimeout(mounted ? 2000 : 3100);
        const progress = await page.evaluate(() => ({ y: Field.hero.y, mounted: Field.hero.mounted, target: !!Field.hero.target,
          moves: travelSent.filter(m => m.type === 'move'), inputs: travelSent.filter(m => m.type === 'input') }));
        await page.mouse.up();
        console.log(mounted ? 'riding' : 'walking', { y:progress.y, moves:progress.moves.length, first:progress.moves[0]?.y, last:progress.moves.at(-1)?.y });
        check(progress.moves.length >= 5, `${mounted ? 'Riding' : 'Walking'}: held mouse sends movement (${progress.moves.length})`);
        check(Math.min(...progress.moves.map(m => m.y)) < progress.moves[0].y - 6, 'Stationary cursor follows the moving camera instead of the old world point');
        check(progress.y < 136 && progress.mounted === mounted && !progress.target, 'Actual fighter continues beyond the original destination');
        check(progress.moves.length + progress.inputs.length < (mounted ? 160 : 248), 'Held movement stays below the connection rate limit');
        await page.evaluate(() => { travelSent.length = 0; }); await page.waitForTimeout(350);
        check(await page.evaluate(() => travelSent.every(m => m.type !== 'move')), 'Releasing the mouse stops destination refreshes');
      }
      // Cancelling capture or losing focus must not resume a held movement stream.
      for (const event of ['pointercancel', 'lostpointercapture', 'blur']) {
        await stand(4, 80, 145);
        await page.mouse.down();
        await page.evaluate(event => { (event === 'blur' ? window : document.querySelector('#fieldcv')).dispatchEvent(new Event(event)); travelSent.length = 0; }, event);
        await page.waitForTimeout(300); await page.mouse.up();
        check(await page.evaluate(() => travelSent.every(m => m.type !== 'move')), `${event} clears held travel`);
      }
    }
    if (process.env.REAL_SPRITES === '1' && (!process.env.CHECK_ONLY || process.env.CHECK_ONLY === 'horse')) {
      await page.evaluate(() => { window.__valhallaTestSprites = false; MountArt.preload('horse'); });
      await page.waitForFunction(() => MountArt.ready('horse'), null, { timeout: 20000 });
      const gait = await page.evaluate(async () => {
        const m = MountArt.meta('horse'), im = new Image(); im.src = 'assets/' + m.png; await im.decode();
        const atlas = document.createElement('canvas'); atlas.width = im.width; atlas.height = im.height;
        const a = atlas.getContext('2d'); a.drawImage(im, 0, 0);
        const blank = { _px: new Uint8ClampedArray(160 * 160 * 4), _z: new Uint16Array(160 * 160).fill(65535) };
        const results = [];
        const sheet = document.createElement('canvas'); sheet.width = 8 * 160; sheet.height = 8 * 224;
        const g = sheet.getContext('2d');
        for (let d = 0; d < 8; d++) for (let i = 0; i < 8; i++) {
          const composed = MountArt.compose(blank, 'horse', 'run', d, i, 0);
          const actual = composed.getContext('2d').getImageData(0, 64, 160, 160).data;
          const expected = a.getImageData(((8 - i) % 8) * 160, (m.clips.run.row0 + d) * 160, 160, 160).data;
          let diff = 0; for (let p = 0; p < actual.length; p++) if (actual[p] !== expected[p] && (p % 4 === 3 || actual[p - p % 4 + 3] || expected[p - p % 4 + 3])) diff++;
          results.push(diff);
          g.drawImage(composed, i * 160, d * 224);
        }
        // A unique rider pixel above the horse verifies the source frame also drives its saddle height.
        blank._px.set([255, 0, 255, 255], (10 * 160 + 80) * 4); blank._z[10 * 160 + 80] = 32768;
        const bob = [];
        for (let i = 0; i < 8; i++) {
          const c = MountArt.compose(blank, 'horse', 'run', 0, i, 0), p = c.getContext('2d').getImageData(0, 0, 160, 224).data;
          let found = -1; for (let y = 0; y < 224; y++) { const at = (y * 160 + 80) * 4; if (p[at] === 255 && p[at+1] === 0 && p[at+2] === 255) found = y; }
          bob.push(found === 10 + 64 - Math.round((m.raise + m.bob.run[(8-i)%8]) * Math.sqrt(3)/2 * 1.03));
        }
        return { results, bob, sheet: sheet.toDataURL() };
      });
      check(gait.results.length === 64 && gait.results.every(n => n === 0), 'All eight run frames in all eight facings play in the forward gait order');
      check(gait.bob.every(Boolean), 'The rider follows the same remapped saddle frame');
      fs.writeFileSync(path.join(world.runDir, 'horse-forward-cycle.png'), Buffer.from(gait.sheet.split(',')[1], 'base64'));
    }
    // Organic atlas coverage lives in organic-atlas-ui.cjs.
    await browser.close(); browser = null;
    if (!process.env.CHECK_ONLY || process.env.CHECK_ONLY === 'touch') {
      for (const [width, height] of [[844,390],[1024,768]]) {
        browser = await chromium.launch({headless:true});
        const touchPage = await browser.newPage({viewport:{width,height},isMobile:true,hasTouch:true,reducedMotion:'reduce'});
        touchPage.on('pageerror', e => errors.push(e.message));
        await touchPage.addInitScript(() => {
          window.__valhallaTestSprites=true; window.AudioContext=undefined; window.webkitAudioContext=undefined;
          localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null}));
        });
        await touchPage.goto(world.url); await touchPage.locator('#start').click(); await touchPage.locator('#login-guest').click();
        await touchPage.locator('#cls-warrior').click(); await touchPage.locator('#name').fill('AtlasTouch'); await touchPage.locator('#go').click({timeout:60000});
        await touchPage.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
        if (await touchPage.locator('#low-gfx-dismiss').isVisible()) await touchPage.locator('#low-gfx-dismiss').click();
        await touchPage.evaluate(()=>WorldMap.show());
        check(await touchPage.evaluate(()=>{
          const panel=document.querySelector('.wm-panel').getBoundingClientRect(),body=document.querySelector('#wm-body'),r=body.getBoundingClientRect();
          const tile=document.querySelector('.wm-tile[data-zone="0"]').getBoundingClientRect(),legend=document.querySelector('.wm-connection-key').getBoundingClientRect();
          return panel.left>=-1&&panel.top>=-1&&panel.right<=innerWidth+1&&panel.bottom<=innerHeight+1
            &&body.scrollWidth>body.clientWidth&&body.scrollHeight>body.clientHeight
            &&tile.left>=r.left&&tile.right<=r.right&&tile.top>=r.top&&tile.bottom<=r.bottom&&legend.bottom<=panel.bottom;
        }),`${width}x${height}: atlas fits, scrolls, centers the hero and shows the connection key`);
        await touchPage.locator('.wm-tile[data-zone="0"]').tap();
        check(await touchPage.evaluate(()=>WorldMap.view==='zone'),`${width}x${height}: touching a region opens its detail map`);
        await touchPage.locator('#wm-back').tap();
        check(await touchPage.evaluate(()=>WorldMap.view==='world'),`${width}x${height}: returning to the atlas works`);
        await touchPage.screenshot({path:path.join(world.runDir,`atlas-${width}x${height}.png`)});
        await browser.close(); browser=null;
      }
    }
    check(errors.length === 0, `No browser errors: ${errors.join('; ')}`);
    console.log(`travel-fixes-ui: ${checks} focused checks passed; artifacts: ${world.runDir}`);
  } finally { await browser?.close(); await world.stop(); }
})().catch(e=>{console.error(e);process.exitCode=1;});

}
