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
      if (process.env.MUTATE === 'atlas') source = source.replace(/const LAYOUT = .*?;/, line => line + ' LAYOUT[1].y = LAYOUT[0].y + 10;');
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
    if (!process.env.CHECK_ONLY || process.env.CHECK_ONLY === 'atlas') {
      await debug({ op: 'explore_all' });
      await page.waitForFunction(() => Field.explored?.[28] === 511);
      await page.evaluate(() => { document.activeElement?.blur?.(); WorldMap.show(); });
      const atlas = await page.evaluate(() => {
        const zones = Field._debug.zones, layout = WorldMap._layout;
        const shown = zones.map((z, i) => ({ z, i })).filter(({z}) => !z.sealedTemplate && z.theme !== 'arena');
        const errors = [], pairs = new Set();
        const side = (z, p) => { const dx = p.x-z.size/2, dy = p.y-z.size/2; return Math.abs(dx)>=Math.abs(dy) ? [Math.sign(dx),0] : [0,Math.sign(dy)]; };
        const center = i => { const p=layout[i]; return [p.x+p.s/2,p.y+p.s/2]; };
        for (const { z, i } of shown) {
          if (!layout[i] || layout[i].x < 0 || layout[i].y < 0 || layout[i].x+layout[i].s > 160 || layout[i].y+layout[i].s > 99) errors.push(`bounds ${i}`);
          for (const p of z.portals) {
            if (p.to===i || !shown.some(n=>n.i===p.to)) continue;
            const pair=[i,p.to].sort((a,b)=>a-b).join('-'); pairs.add(pair);
            const other=zones[p.to], back=other.portals.filter(q=>q.to===i).sort((a,b)=>Math.hypot(a.x-p.tx,a.y-p.ty)-Math.hypot(b.x-p.tx,b.y-p.ty))[0];
            if (!back) { errors.push(`return ${pair}`); continue; }
            const road=document.querySelector(`[data-road="${pair}"]`);
            if (!road) { errors.push(`road ${pair}`); continue; }
            const land=document.querySelector(`[data-link="${pair}"]`);
            if ((road.dataset.kind==='path')!==!!land) errors.push(`land ${pair}`);
            if (road.dataset.kind==='path') {
              const a=center(i),b=center(p.to),delta=[b[0]-a[0],b[1]-a[1]],out=side(z,p),incoming=side(other,back);
              if (delta[0]*out[0]+delta[1]*out[1] <= 0 || delta[0]*incoming[0]+delta[1]*incoming[1] >= 0) errors.push(`direction ${i}->${p.to}`);
            }
            // Roads terminate at the actual gate's side of each tile, including the return entrance nearest the arrival.
            if (i<p.to) {
              const nums=road.querySelector('.wm-road').getAttribute('d').match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/g).map(Number);
              const a=center(i), b=center(p.to);
              if ((nums[0]-a[0])*side(z,p)[0]+(nums[1]-a[1])*side(z,p)[1] <= 0 || (nums.at(-2)-b[0])*side(other,back)[0]+(nums.at(-1)-b[1])*side(other,back)[1] <= 0) errors.push(`endpoint ${pair}`);
            }
          }
        }
        for (const a of shown) for (const b of shown) if(a.i<b.i) {
          const ac=center(a.i),bc=center(b.i);
          if(Math.hypot(ac[0]-bc[0],ac[1]-bc[1]) < (layout[a.i].s+layout[b.i].s)/2) errors.push(`overlap ${a.i},${b.i}`);
        }
        const graph=WorldMap._graph, seen=new Set([0]),queue=[0];
        for(const i of queue) for(const e of graph[i]) if(!seen.has(e.to)) {seen.add(e.to);queue.push(e.to);}
        const body=document.querySelector('#wm-body'),tile=document.querySelector(`.wm-tile[data-zone="${Field.zone}"]`);
        const br=body.getBoundingClientRect(),tr=tile.getBoundingClientRect();
        return { errors, roads:document.querySelectorAll('[data-road]').length, pairs:pairs.size, reachable:shown.every(n=>seen.has(n.i)), centered:tr.left>=br.left&&tr.right<=br.right&&tr.top>=br.top&&tr.bottom<=br.bottom };
      });
      check(atlas.errors.length === 0, `Atlas geography matches every authoritative portal: ${atlas.errors.join('; ')}`);
      check(atlas.roads === atlas.pairs && atlas.reachable, 'Every open zone is connected by exactly the real links; internal raid lifts are omitted');
      check(atlas.centered, 'The scrollable atlas opens centered on the current zone');
      await page.locator('.wm-tile[data-zone="4"]').click();
      check(await page.evaluate(() => WorldMap.view === 'zone' && document.querySelector('#wm-body').scrollTop === 0), 'Opening a zone resets the atlas scroll');
      await page.locator('#wm-back').click();
      check(await page.evaluate(() => WorldMap.view === 'world' && document.querySelector('#wm-body').scrollTop > 0), 'Returning restores the atlas scroll');
      await page.locator('#wm-body').screenshot({ path:path.join(world.runDir,'geographic-atlas.png'), timeout:30000 });
      await page.locator('#wm-close').click();
      // Real gate travel in both directions: north/south, east/west and a causeway whose return faces south.
      for (const [from, to] of [[0,1],[1,0],[4,6],[6,4],[16,17],[17,16]]) {
        const p=await page.evaluate(([from,to])=>Field._debug.zones[from].portals.find(p=>p.to===to),[from,to]);
        const size=await page.evaluate(from=>Field._debug.zones[from].size,from);
        const dx=size/2-p.x,dy=size/2-p.y,n=Math.hypot(dx,dy);
        await stand(from,p.x+dx/n*5,p.y+dy/n*5);
        await page.evaluate(p=>Online.send({type:'move',x:p.x,y:p.y}),p);
        await page.waitForFunction(to=>Field.zone===to,to,{timeout:15000});
        check(await page.evaluate(p=>Math.hypot(Field.hero.x-p.tx,Field.hero.y-p.ty)<3,p),`Actual gate ${from}->${to} reaches its documented arrival`);
      }
    }
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
