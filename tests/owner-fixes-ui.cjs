// Seven owner reports: focused private integration, presentation fixtures, no combat grind.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const candidate = process.env.OWNER_FIXES_CLIENT;
const world = new TestWorld(); world.godMode = true;
let browser, checks = 0;
const errors = [];
const check = (ok, label) => { assert.ok(ok, label); console.log(`${++checks}: ${label}`); };
const wait = (page, fn, arg) => page.waitForFunction(fn, arg, { timeout: 15000 });
const send = (page, packet) => page.evaluate(packet => Online.send(packet), packet);
async function debug(page, command) { await send(page, { type: 'debug', command }); await page.waitForTimeout(180); }
async function player(touch = false) {
  const page = await browser.newPage({ viewport: touch ? { width: 844, height: 390 } : { width: 1280, height: 800 }, hasTouch: touch, isMobile: touch, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  if (candidate) {
    await page.context().grantPermissions(['local-network-access'], { origin: world.url });
    for (const name of ['index.html', 'quests.js', 'quest-sources.js', 'field.js', 'city.js', 'shop.js', 'online.css', 'sv-data.js']) {
      let body = fs.readFileSync(path.join(candidate, name), 'utf8');
      if (process.env.MUTATE === 'ready' && name === 'quests.js') body = body.replace("if (s === 'ready') for (const n of turnIns(q))", "if (false) for (const n of turnIns(q))");
      await page.route(name === 'index.html' ? world.url : '**/' + name, r => r.fulfill({ body, contentType: name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : 'text/html' }));
    }
  }
  await page.addInitScript(({ touch, version }) => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({lang:touch?'sv':'en', sound:false, dpsMeter:false, uiSet:true,ui:{},panelSizeSet:true,panelSize:{}}));
    localStorage.setItem('valhallasc.whats-new.v1', version);
  }, { touch, version: fs.readFileSync(path.join(candidate || 'client', 'index.html'),'utf8').match(/class="version">([^<]+)/)[1] });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill(touch ? 'FixTouch' : 'FixDesktop'); await page.locator('#go').click({timeout:60000});
  await wait(page, () => Online.connected && Field.hero?.hp > 0);
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  return page;
}
async function nearNpc(page, id) {
  const location = await page.evaluate(id => [WORLD_MAP,...WORLD_MAP.zones].flatMap((a,zone)=>(a.npcs||[]).filter(n=>n.id===id).map(n=>({zone,x:n.x,y:n.y}))).find(Boolean), id);
  await debug(page, {op:'teleport',...location});
  await wait(page, zone => Field.zone === zone, location.zone);
  await page.evaluate(id => Field.visitNpc(id), id);
  await page.locator('#npc-dialogue').waitFor({state:'visible'});
}
async function portalTest(page, touch) {
  await page.evaluate(() => { City.close(); Quests.close(); WorldMap.close(); Field.clearInput(); });
  const p = await page.evaluate(() => WORLD_MAP.portals.find(p=>p.to===1));
  const length = Math.hypot(...p.walk), back = 5;
  await debug(page,{op:'teleport',zone:0,x:p.x-p.walk[0]/length*back,y:p.y-p.walk[1]/length*back});
  await page.waitForTimeout(500);
  // Click beside the opening, outside its old trigger circle. The shared picker
  // must build a route that actually carries the authoritative hero across.
  const hit = await page.evaluate(p => {
    const [x,y] = Field._debug.w2s(p.x,p.y), cv=document.getElementById('fieldcv'), b=cv.getBoundingClientRect();
    return { x:b.x+(x+60)/1600*b.width, y:b.y+y/(b.height/b.width*1600)*b.height };
  },p);
  if (!touch) {
    await page.mouse.move(hit.x,hit.y);
    check(await page.locator('#fieldcv').evaluate(n=>n.style.cursor==='pointer'),'Hover near a gate shows an actionable cursor');
    await page.mouse.click(hit.x,hit.y);
  } else await page.touchscreen.tap(hit.x,hit.y);
  await wait(page, () => Field.zone === 1).catch(async e => { console.error('Portal failure', {touch,hit,p}, await page.evaluate(() => ({zone:Field.zone,hero:{x:Field.hero.x,y:Field.hero.y},route:Field._debug.cityRoute,paused:document.getElementById('pause').hidden,hitElement:document.elementFromPoint(innerWidth*.6,innerHeight*.5)?.outerHTML.slice(0,150)}))); await page.screenshot({path:path.join(world.runDir,'portal-failure.png')}); throw e; });
  check(true, `${touch?'Touch':'Mouse'} near the opening follows a route and crosses the gate`);
  await page.waitForTimeout(800);
  check(await page.evaluate(()=>Field.zone===1),'Arrival remains in the destination after the portal cooldown');
}
(async () => {
  await world.start(); browser = await chromium.launch({headless:true});
  if (!process.env.OWNER_FIXES_ONLY) {
  const page = await player();
  await debug(page,{op:'set_level',level:99});
  // Real multi-objective bring transitions, cross-zone marker and Arrow target.
  await debug(page,{op:'quest',id:'city_welcome',action:'finish'});
  await debug(page,{op:'quest',id:'city_gel',action:'accept'});
  await wait(page,()=>document.querySelector('.tracker-quest[data-quest="city_gel"]'));
  await page.evaluate(()=>Quests.track('city_gel'));
  const gathering = await page.evaluate(()=>({markers:Quests.mapMarkers(0).filter(m=>m.quest==='city_gel'),target:Quests.navigationTarget(4,80,80)}));
  check(gathering.markers.length>=2 && gathering.markers.every(m=>!m.npc),'Bring quest marks real green and blue slime sources instead of the giver');
  check(gathering.target?.viaPortal && gathering.target.destinationZone===0,'Arrow routes from Skaldholm to the gathering zone');
  await debug(page,{op:'give_item',item:'slime_gel',quantity:8});
  await wait(page,()=>Quests.mapMarkers(0).filter(m=>m.quest==='city_gel').length===1);
  check(await page.evaluate(()=>Quests.mapMarkers(0).filter(m=>m.quest==='city_gel').length===1),'A finished individual bring objective removes only its own gathering marker');
  await debug(page,{op:'give_item',item:'blue_gel',quantity:4});
  await wait(page,()=>document.querySelector('.tracker-quest[data-quest="city_gel"]')?.dataset.status==='ready');
  const ready = await page.evaluate(()=>({
    text:document.querySelector('.tracker-quest[data-quest="city_gel"]').textContent,
    local:Quests.mapMarkers(0).filter(m=>m.quest==='city_gel'), remote:Quests.mapMarkers(4).filter(m=>m.quest==='city_gel'),
    target:Quests.navigationTarget(0,36,35),
  }));
  check(ready.text.includes('Complete · Ready to turn in') && !ready.text.includes('/8'),'Tracker replaces objective counters with a complete state and hand-in destination');
  check(ready.local.length===0 && ready.remote.length===1 && ready.remote[0].x===WORLD_GEL_NPC_X(),'Final objective switches all guidance to the remote hand-in NPC');
  check(ready.target?.viaPortal && ready.target.destinationZone===4,'Ready quest Arrow routes to the hand-in zone');
  await page.evaluate(()=>Quests.show());
  check((await page.locator('.quest-entry[data-quest="city_gel"] > summary').textContent()).includes('Complete · Ready to turn in'),'Folded journal exposes the ready state without opening the quest');
  await page.evaluate(()=>Quests.close());
  // The same final-count transition for each supported objective kind, without grinding.
  const kinds = await page.evaluate(()=>{
    const areas=[WORLD_MAP,...WORLD_MAP.zones], kinds=['kill','talk','bring','escort','visit','hold','chime','memory','echo'];
    return kinds.map(kind=>{
      const q=areas.flatMap(a=>a.quests||[]).find(q=>q.objectives.some(o=>o.kind===kind));
      if(!q)return {kind,ok:false};
      const counts=q.objectives.map(o=>o.count), last=q.objectives.findIndex(o=>o.kind===kind); counts[last]--;
      Quests.update([{id:q.id,counts:[...counts],claimed:false,completions:0}]);Quests.track(q.id);
      counts[last]++; Quests.update([{id:q.id,counts,claimed:false,completions:0}]);
      return {kind,ok:document.querySelector(`.tracker-quest[data-quest="${q.id}"]`)?.dataset.status==='ready' && areas.some((a,z)=>Quests.mapMarkers(z).some(m=>m.quest===q.id && m.state==='tracked' && (a.npcs||[]).some(n=>n.id===q.npc && n.x===m.x && n.y===m.y)))};
    });
  });
  check(kinds.every(k=>k.ok),'Final counts produce ready state and hand-in markers for '+kinds.map(k=>k.kind).join(', '));
  // Next snapshot restores real progress after synchronous presentation fixtures.
  await page.waitForTimeout(220);
  // Arena: source acceptance, duplicate hiding, other-giver entry/return/claim.
  await nearNpc(page,'city_steward');
  await send(page,{type:'interact',npc:'city_steward',offer:'quest:accept:arena_skald_20'});
  await wait(page,()=>document.querySelector('.tracker-quest[data-quest="arena_skald_20"]'));
  await page.evaluate(()=>City.close());
  await nearNpc(page,'nacre_archivist');
  check(await page.locator('.gossip-row[data-quest="arena_nacre_20"]').count()===0,'Second arena giver hides the level already taken elsewhere');
  await page.locator('[data-offer="gauntlet"]').click();
  await wait(page,()=>Pvp.state.gauntlet?.fight===1);
  check(true,'A second arena giver starts the accepted trial');
  await send(page,{type:'pvp',command:{op:'arena_leave'}});
  await wait(page,()=>Field.zone===9 && !Pvp.state.gauntlet);
  check(await page.evaluate(()=>Math.hypot(Field.hero.x-City.npcs.find(n=>n.id==='nacre_archivist').x,Field.hero.y-City.npcs.find(n=>n.id==='nacre_archivist').y)<3),'Leaving returns to the entering giver');
  await debug(page,{op:'quest',id:'arena_skald_20',action:'complete'});
  await nearNpc(page,'nacre_archivist');
  await page.locator('.gossip-row[data-quest="arena_skald_20"]').click();
  await page.locator('[data-action="claim"][data-item="warrior_weapon_sword_l20_blue"]').click();
  await wait(page,()=>document.getElementById('npc-notice').textContent.includes('Quest complete:'));
  check(true,'A second giver hands in the original trial and pays its class weapon');
  // Merchant cleanup protects active materials, then exposes abandoned leftovers.
  await page.evaluate(()=>City.close());
  await nearNpc(page,'merchant');
  await page.locator('[data-view="buy"]').click();
  await wait(page,()=>Shop.open);
  check(await page.locator('[data-tab="leftovers"]').count()===1,'Merchant exposes quest leftovers separately from Sell all junk');
  await page.locator('[data-tab="leftovers"]').click();
  check(await page.locator('[data-action="discard-leftovers"][data-item="slime_gel"]').count()===0,'Active ready-to-hand-in materials are excluded from discard');
  await page.evaluate(()=>City.close());
  await send(page,{type:'quest_abandon',id:'city_gel'}); await page.waitForTimeout(220);
  await nearNpc(page,'merchant'); await page.locator('[data-view="buy"]').click(); await wait(page,()=>Shop.open);
  await page.locator('[data-tab="leftovers"]').click();
  await page.locator('[data-action="discard-leftovers"][data-item="slime_gel"]').click();
  check(await page.locator('#sell-warning').isVisible() && (await page.locator('#sell-warning').innerText()).includes('No gold or buyback'),'Discard requires an explicit confirmation explaining permanent removal');
  await page.locator('#sell-warning [data-action="discard"]').click();
  await wait(page,()=>document.getElementById('npc-notice').textContent.includes('Quest leftovers discarded'));
  check(await page.locator('[data-action="discard-leftovers"][data-item="slime_gel"]').count()===0,'Confirmed discard removes the leftover stack');
  await page.evaluate(()=>City.close());
  // A real dropped bag remains at a fixed world position while the hero walks.
  for(let n=0;n<4;n++) await debug(page,{op:'give_item',item:'linen_satchel',quantity:1});
  await debug(page,{op:'teleport',zone:0,x:15,y:15});
  await debug(page,{op:'drop_item',item:'linen_satchel',quantity:1});
  await wait(page,()=>Field._debug.drops.some(d=>d.item==='linen_satchel' && d.t>.6));
  const pile = await page.evaluate(()=>Field._debug.drops.find(d=>d.item==='linen_satchel'));
  await send(page,{type:'move',x:18,y:15});
  await wait(page,()=>Field.hero.x>17.5);
  check(await page.evaluate(p=>{const d=Field._debug.drops.find(d=>d.id===p.id);return d && d.x===p.x && d.y===p.y;},pile),'Refused bag pickup stays at its original coordinates as the hero walks away');
  await send(page,{type:'stop'});
  await portalTest(page,false);
  await page.close();
  }
  const phone = await player(true);
  await debug(phone,{op:'set_level',level:99});
  if (process.env.OWNER_FIXES_ONLY !== 'locale') await portalTest(phone,true);
  // Swedish ready presentation remains explicit on the short touch layout.
  await debug(phone,{op:'quest',id:'welcome',action:'accept'});
  await debug(phone,{op:'quest',id:'welcome',action:'complete'});
  await wait(phone,()=>document.querySelector('.tracker-quest[data-quest="welcome"]')?.dataset.status==='ready');
  check((await phone.locator('.tracker-quest[data-quest="welcome"]').textContent()).includes('Klar'),'Swedish touch tracker exposes the complete state');
  const destination = await phone.locator('.tracker-quest[data-quest="welcome"] .tracker-destination').boundingBox();
  check(destination.height >= 43.9,'Ready hand-in control keeps a physical 44 px touch target');
  check(errors.length===0,'No browser errors: '+errors.join('; '));
  await phone.screenshot({path:path.join(world.runDir,'owner-fixes-touch.png')});
  console.log(`owner-fixes-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
// Authored coordinate, read independently from the source map rather than the marker helper.
function WORLD_GEL_NPC_X() { const m=JSON.parse(fs.readFileSync('world/map.txt','utf8'));return m.zones[3].npcs.find(n=>n.id==='city_alchemist').x; }
