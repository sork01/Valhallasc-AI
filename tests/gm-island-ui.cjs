// Private GM island controls and scenery. Fake local SSO, real GM authorization;
// no test flags. Run controls with stub class sprites, then GMI_ART_ONLY=1
// REAL_SPRITES=1 separately to avoid accumulating three class banks in 1.5 GiB.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const timeout = (promise, ms, label) => Promise.race([promise, new Promise((_, reject) => { const timer = setTimeout(() => reject(Error(label)), ms); timer.unref(); })]);
let server, fake, browser, url, logs = '', checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
const SORK = 'sorksession1234567890', OTHER = 'othersession1234567890';
async function startFakeSso() {
  fake = http.createServer((req, res) => {
    const cookie = req.headers.cookie || '', user = cookie.includes('sso_session=' + SORK) ? 'Sork' : cookie.includes('sso_session=' + OTHER) ? 'Other_User' : null;
    res.writeHead(user ? 200 : 401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(user ? { authenticated: true, username: user, email: '' } : { authenticated: false }));
  });
  await new Promise(resolve => fake.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${fake.address().port}/sso/kriswe-session.php`;
}
async function startServer(ssoUrl, db) {
  const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
  const env = { ...process.env, VALHALLA_BIND: '127.0.0.1:0', VALHALLA_DB: db, RUST_LOG: 'valhalla_server=info', VALHALLA_LEVEL_SPREAD: '0', VALHALLA_SSO_URL: ssoUrl };
  for (const name of ['VALHALLA_ORIGIN', 'VALHALLA_SSO_RESOLVE', 'VALHALLA_GOD_MODE', 'VALHALLA_TEST_COMMANDS']) delete env[name];
  server = spawn(binary, [], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stderr.on('data', data => { logs += data.toString().replace(/\x1b\[[0-9;]*m/g, ''); });
  await timeout(new Promise((resolve, reject) => {
    server.stdout.on('data', data => { logs += data.toString().replace(/\x1b\[[0-9;]*m/g, ''); const match = logs.match(/address=(127\.0\.0\.1:\d+)/); if (match) { url = 'http://' + match[1] + '/'; resolve(); } });
    server.once('error', reject); server.once('exit', code => reject(Error(`Server exited ${code}: ${logs}`)));
  }), 15000, 'Server did not start');
}
async function newPlayer(cookie) {
  const context = await browser.newContext({ viewport: process.env.GMI_PHONE ? {width:740,height:360} : { width: 1440, height: 900 }, hasTouch:!!process.env.GMI_PHONE, reducedMotion: 'reduce' });
  await context.addInitScript(() => { window.__valhallaTestSprites = !location.search.includes('real'); if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await context.addCookies([{ name: 'sso_session', value: cookie, url }]);
  const page = await context.newPage(); page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(url + (process.env.REAL_SPRITES ? '?real=1' : ''));
  return page;
}
const signIn = async page => {
  await page.locator('#start').click(); await page.locator('#login-title').waitFor({ state: 'visible', timeout: 10000 });
  await page.locator('#login-sso').click(); await page.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
};
const connected = page => page.waitForFunction(() => Online.connected && !!Field.hero, null, { timeout: 60000 });

(async () => {
  const dir = fs.mkdtempSync(path.join(root,'test-results/gm-island-ui-'));
  await startServer(await startFakeSso(),path.join(dir,'test.sqlite'));
  browser=await chromium.launch({headless:true});
  let page;
  try {
    page=await newPlayer(SORK); await signIn(page);await page.locator('#chars-gm').click();await connected(page);
    await page.evaluate(()=>GM.request({op:'set_time',hour:12,freeze:true}));
    await page.locator('#gmtest-open').click();await page.getByRole('button',{name:'Visit GM Island',exact:true}).click();
    await page.waitForFunction(()=>Field.zone===47&&Field.hero?.gm);
    check(await page.evaluate(()=>Field.zoneTheme)==='gm_island','island theme active');
    async function at(npc) {
      await page.evaluate(async id=>{City.close();const n=WORLD_MAP.zones[46].npcs.find(n=>n.id===id);const r=await GM.request({op:'teleport',zone:47,x:n.x+1,y:n.y});if(!r.ok)throw Error(r.error);},npc);
      await page.waitForTimeout(650);
      await page.evaluate(id=>Online.send({type:'interact',npc:id}),npc);
      await page.locator('.gmi-controls').waitFor();
    }
    if (!process.env.GMI_ART_ONLY) {
    await at('gmi_quartermaster');
    check(await page.locator('.gmi-controls p').first().evaluate(p=>getComputedStyle(p).color)==='rgb(245, 232, 201)','service instructions have readable text');
    check(await page.locator('.gmi-controls').evaluate(p=>p.scrollWidth<=p.clientWidth+1),'service controls fit the panel width');
    await page.locator('#gmi-class').selectOption('mage');await page.locator('#gmi-level').fill('60');await page.locator('#gmi-gear').selectOption('rare');
    await page.locator('[data-gmi=setup]').click();await page.waitForFunction(()=>Field.hero.look.class==='mage'&&Field.hero.level===60);
    check(/10 pieces/.test(await page.locator('.gmi-status').innerText()),'NPC applies full class loadout');
    await at('gmi_summoner');await page.locator('#gmi-search').fill('Hollow King');
    check(await page.locator('#gmi-enemy option').count()>0,'boss searchable by rendered name');
    await page.locator('#gmi-enemy').selectOption('hollowking');await page.locator('#gmi-level').fill('60');await page.locator('#gmi-count').fill('2');
    await page.locator('[data-gmi=summon]').click();await page.waitForFunction(()=>document.querySelector('.gmi-status').textContent==='Done.');
    await page.waitForFunction(()=>Field.slimes.filter(s=>s.kind==='hollowking'&&!s.dead).length===2);
    check((await page.evaluate(()=>Field.slimes.filter(s=>s.kind==='hollowking'&&!s.dead).length))===2,'two bosses appear in arena');
    await page.waitForTimeout(600);await page.locator('[data-gmi=clear]').click();
    await at('gmi_recruiter');await page.locator('#gmi-class').selectOption('priest');await page.locator('#gmi-count').fill('1');
    await page.locator('[data-gmi=mercs]').click();await page.waitForFunction(()=>document.querySelector('.gmi-status').textContent==='Done.');
    check(true,'mercenary NPC accepts chosen class');
    await at('gmi_trainer');await page.locator('[data-gmi=reset_dps]').click();await page.waitForFunction(()=>document.querySelector('.gmi-status').textContent==='Done.');
    await page.waitForTimeout(600);await page.locator('[data-gmi=refresh]').click();await page.waitForFunction(()=>document.querySelector('.gmi-status').textContent==='Done.');
    await page.screenshot({path:path.join(dir,'training-controls.png')});
    await page.evaluate(()=>City.close());
    } else {
      await page.evaluate(()=>Tutorial.disable());
      await page.waitForFunction(()=>!!Field.warriorSprites&&NpcArt.readyFor(City.npcs),null,{timeout:60000});
      check(true,'real GM sprite and all island NPC atlases finish loading');
      check((await page.locator('#world-weather').innerText()).includes('Clear'),'island weather HUD reports clear outdoor weather');
      check(await page.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=96;return Field.drawTargetPortrait({kind:'gmi_dummy'},c);}), 'dummy target portrait finishes drawing');
      await page.evaluate(()=>GM.request({op:'teleport',zone:47,x:209,y:265}));
      await page.waitForTimeout(6000);
    }
    await page.screenshot({path:path.join(dir,'training-yard.png')});
    if (process.env.GMI_ART_ONLY) {
    await page.evaluate(()=>GM.request({op:'teleport',zone:47,x:212,y:220}));
    await page.waitForTimeout(1200);await page.screenshot({path:path.join(dir,'arena.png')});
    for(const town of ['christmas','halloween','easter','solstice','valentine','newyear']) {
      await page.evaluate(async season=>{const n=WORLD_MAP.zones[46].gmIsland.towns.find(t=>t.id===season);await GM.request({op:'teleport',zone:47,x:n.x+4,y:n.y-6});},town);
      await page.waitForTimeout(1200);await page.screenshot({path:path.join(dir,town+'.png')});
      check(true,`${town} village renders`);
    }
    await page.locator('#wm-open').click();check(await page.locator('#worldmap').isVisible(),'island detailed map opens');
    await page.screenshot({path:path.join(dir,'island-map.png')});await page.locator('#wm-close').click();
    }
    await at('gmi_ferryman');await page.locator('[data-gmi=leave]').click();await page.waitForFunction(()=>Field.zone===0&&Field.hero.level===1&&Field.hero.look.class==='warrior');
    check(true,'leaving restores original GM class and level');
    check(page.errors.length===0,`no browser errors: ${page.errors.join('; ')}`);
    await page.context().close();page=null;
    console.log(`gm-island-ui: ${checks} checks passed; screenshots ${dir}`);
  } catch(error) {
    if(page){console.error('Browser errors:',page.errors);await page.screenshot({path:path.join(dir,'failure.png')}).catch(()=>{});console.error('Connection:',await page.locator('#connection-overlay').innerText().catch(()=>''));}
    throw error;
  } finally {
    await page?.context().close().catch(()=>{});await browser?.close().catch(()=>{});server?.kill();fake?.close();
  }
})().catch(error=>{console.error(error);console.error(logs.slice(-2000));process.exit(1);});
