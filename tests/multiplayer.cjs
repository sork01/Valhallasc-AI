const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium, STUB } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const timeout = (promise, ms, label) => Promise.race([promise, new Promise((_, reject) => { const timer = setTimeout(() => reject(Error(label)), ms); timer.unref(); })]);
let server, browser, url, db, logs = '', passed = 0;
const check = (condition, message) => { assert.ok(condition, message); passed++; };
async function startServer(bind = '127.0.0.1:0') {
  logs = '';
  const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
  // This suite exercises controls, rendering and multiplayer around real fights, not combat difficulty: pin every enemy to its default level.
  const testEnvironment = { ...process.env, VALHALLA_BIND: bind, VALHALLA_DB: db, RUST_LOG: 'valhalla_server=info', VALHALLA_LEVEL_SPREAD: '0', VALHALLA_GOD_MODE: '1', VALHALLA_TEST_COMMANDS: '1' };
  delete testEnvironment.VALHALLA_ORIGIN;
  server = spawn(binary, [], { cwd: root, env: testEnvironment, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stderr.on('data', data => { logs += data; });
  await timeout(new Promise((resolve, reject) => {
    server.stdout.on('data', data => { logs += data.toString().replace(/\x1b\[[0-9;]*m/g, ''); const match = logs.match(/address=(127\.0\.0\.1:\d+)/); if (match) { url = 'http://' + match[1] + '/'; resolve(); } });
    server.once('error', reject); server.once('exit', code => reject(Error(`Server exited ${code}: ${logs}`)));
  }), 15000, 'Server did not start');
}
async function stopServer() {
  if (!server || server.exitCode !== null) return;
  const child = server;
  const exited = new Promise(resolve => child.once('exit', resolve));
  child.kill('SIGTERM'); await timeout(exited, 7000, 'Graceful shutdown timed out'); server = null;
}
async function makePlayer(type, name) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  await context.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  const page = await context.newPage(); page.errors = []; page.pickups = []; page.actorCollision = null; page.renderCollision = null;
  await page.exposeFunction('reportRenderedActorCollision', collision => { page.renderCollision ||= collision; });
  page.on('pageerror', error => page.errors.push(error.message));
  page.debugReplies = new Map();
  page.on('websocket', socket => socket.on('framereceived', ({payload}) => {
    const packet=JSON.parse(payload.toString());
    if(packet.type==='debug') page.debugReplies.set(packet.ref,packet);
    if(packet.type==='event' && packet.kind==='pickup') page.pickups.push(packet);
    const snapshot=packet.type==='snapshot'?packet:packet.type==='welcome'?packet.snapshot:null;
    if(snapshot && !page.actorCollision) {
      const actors=[...snapshot.players,...snapshot.slimes].filter(actor=>!actor.dead);
      for(let i=0;i<actors.length;i++) for(let j=i+1;j<actors.length;j++) {
        const a=actors[i],b=actors[j];
        if(!a.kind && !b.kind)continue;
        const gap=a.kind && b.kind?(a.r||.3)+(b.r||.3):1;
        if((Math.floor(a.x)===Math.floor(b.x)&&Math.floor(a.y)===Math.floor(b.y)) || Math.hypot(a.x-b.x,a.y-b.y)<gap-1e-6) {
          page.actorCollision={tick:snapshot.tick,a:{id:a.id,x:a.x,y:a.y},b:{id:b.id,x:b.x,y:b.y}};
        }
      }
    }
  }));
  await page.goto(url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-' + type).click(); await page.locator('#name').fill(name);
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && !!(Field.warriorSprites || Field.mageSprites || Field.assassinSprites), null, { timeout: 60000 });
  await page.evaluate(() => {
    let reported = false;
    const observe = () => {
      if (Online.connected && !reported) {
        const actors = [Field.hero, ...Field.remotePlayers, ...Field.slimes].filter(a => !a.dead);
        for (let i = 0; i < actors.length; i++) for (let j = i + 1; j < actors.length; j++) {
          const a = actors[i], b = actors[j];
          if (!a.kind && !b.kind) continue;
          const gap = a.kind && b.kind ? (a.r || .3) + (b.r || .3) : 1;
          if ((Math.floor(a.x) === Math.floor(b.x) && Math.floor(a.y) === Math.floor(b.y)) || Math.hypot(a.x - b.x, a.y - b.y) < gap - 1e-6) {
            reported = true;
            window.reportRenderedActorCollision({a:{id:a.id,x:a.x,y:a.y},b:{id:b.id,x:b.x,y:b.y}}).catch(() => {});
          }
        }
      }
      requestAnimationFrame(observe);
    };
    requestAnimationFrame(observe);
  });
  return page;
}
async function probe(page, message) {
  return page.evaluate(message => new Promise((resolve, reject) => {
    const ws = new WebSocket(new URL('ws', location.href).href.replace(/^http/, 'ws'));
    const timer = setTimeout(() => { ws.close(); reject(Error('Probe timed out')); }, 5000);
    ws.onopen = () => ws.send(JSON.stringify(message));
    ws.onmessage = event => { const packet = JSON.parse(event.data); if (packet.type === 'welcome' || packet.type === 'error') { clearTimeout(timer); ws.close(); resolve(packet); } };
    ws.onerror = () => { clearTimeout(timer); reject(Error('Probe failed')); };
  }), message);
}
const { route } = require('../scripts/testing/route.cjs');
// Test shortcuts (VALHALLA_TEST_COMMANDS) for staging only: teleports and spawns get a player to the thing under test.
// Everything under test (combat, rewards, pickups, travel through the gate, shops) still runs for real.
let debugRef = 0;
async function shortcut(page, command) {
  const ref = ++debugRef;
  await page.evaluate(([ref, command]) => Online.send({ type: 'debug', ref, command }), [ref, command]);
  for (const stop = Date.now() + 5000; !page.debugReplies.has(ref); await delay(20)) if (Date.now() > stop) throw Error('No reply to ' + command.op);
  const reply = page.debugReplies.get(ref);
  if (!reply.ok) throw Error(`${command.op}: ${reply.error}`);
  return reply.result;
}
async function stageAt(page, point) {
  await shortcut(page, { op: 'teleport', zone: 0, x: point.x, y: point.y });
  await page.waitForFunction(p => Math.hypot(Field.hero.x - p.x, Field.hero.y - p.y) < 1.5, point, { timeout: 10000 });
}

(async () => {
  fs.mkdirSync(path.join(root, 'test-results'), { recursive: true });
  const runDir = fs.mkdtempSync(path.join(root, 'test-results/world-')); db = path.join(runDir, 'test.sqlite');
  await startServer();
  const health = await (await fetch(url + 'health')).json(); check(health.status === 'ok' && health.online === 0, 'Health endpoint');
  for (const file of ['server/src/main.rs','data/valhalla.sqlite','world/map.txt','.env','.git/config','Cargo.toml']) check((await fetch(url+file)).status===404, 'Private files must not be served: '+file);
  const map=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'),'utf8'));
  check(fs.readFileSync(path.join(root,'client/world.js'),'utf8').includes(JSON.stringify(map)), 'Map is identical on client and server');
  browser = await chromium.launch({ headless: true });
  const warrior = await makePlayer('warrior','TestWarrior');
  const mage = await makePlayer('mage','TestMage');
  const assassin = await makePlayer('assassin','TestAssassin');
  await warrior.waitForFunction(() => !!Field.beetleSprites);
  check(await warrior.evaluate(() => Field.slimes.filter(s=>s.kind==='beetle').length===5 && Field.slimes.filter(s=>s.kind==='beetle').every(s=>s.level===5 && s.maxHp===240 && s.windupTime===.4)), 'Five tougher beetles arrive from authoritative snapshots, each at its default level 5 (the suite pins VALHALLA_LEVEL_SPREAD=0)');
  check(await warrior.evaluate(() => Field.slimes.filter(s=>s.kind==='big').every(s=>s.level===6 && s.maxHp===600 && s.windupTime===.35)), 'King Slime has stronger health and faster windup');
  check(await warrior.evaluate(() => {const kings=Field.slimes.filter(s=>s.kind==='big');return kings.length===2 && kings.every(s=>s.dead && s.hp===0 && s.state==='waiting' && s.dieT>=2);}), 'Kings start hidden while waiting for the rare spawn timer');
  check(await warrior.evaluate(() => Field.hero.xpNeed===100), 'Server sends the level table threshold');
  check(STUB || await warrior.evaluate(() => {const src=Field.beetleSprites;return src.img.beetle.complete && src.img.beetle.naturalWidth===576 && src.img.beetle.naturalHeight===320 && Object.keys(src.meta.clips).length===5;}), 'PixelFlow beetle atlas and all five clips load in browser');
  await warrior.waitForFunction(() => Field.remotePlayers.length === 2 && Field.remotePlayers.every(p => p.sprite), null, { timeout: 60000 });
  check(await warrior.evaluate(() => Field.hero.maxHp===120 && Field.remotePlayers.some(p=>p.look.class==='mage'&&p.maxHp===80) && Field.remotePlayers.some(p=>p.look.class==='assassin'&&p.maxHp===90)), 'Three classes see each other');
  check(await warrior.locator('#connection-overlay').isHidden(), 'Connected overlay is visibly hidden');
  check(await warrior.locator('#chat').isVisible(), 'Chat is visible');
  const warriorId=await warrior.evaluate(()=>Online.id);
  const start=await warrior.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));
  await warrior.keyboard.down('d');await delay(500);await warrior.keyboard.up('d');await delay(400);
  await warrior.waitForFunction(()=>!Field.hero.moving && Math.hypot(Field.hero.x-Field.hero.nx,Field.hero.y-Field.hero.ny)<.05);
  const moved=await warrior.evaluate(()=>({x:Field.hero.nx,y:Field.hero.ny}));
  check(Math.hypot(moved.x-start.x,moved.y-start.y)>.8 && Math.hypot(moved.x-start.x,moved.y-start.y)<4, 'Server controlled keyboard movement');
  await mage.waitForFunction(({id,x,y})=>{const p=Field.remotePlayers.find(p=>p.id===id);return p && Math.hypot(p.x-x,p.y-y)<.2;},{id:warriorId,...moved});passed++;
  const blocker=await warrior.evaluate(()=>{const p=Field.remotePlayers.find(p=>p.look.class==='assassin');return {x:p.x,y:p.y};});
  await warrior.evaluate(p=>Online.send({type:'move',...p}),blocker);
  await warrior.waitForFunction(p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.15,blocker,{timeout:10000});
  await delay(500);
  check(await warrior.evaluate(p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.15,blocker),'Players can move into another player without being blocked');
  await warrior.evaluate(p=>Online.send({type:'move',...p}),moved);
  await warrior.waitForFunction(p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.4,moved,{timeout:10000});
  await warrior.evaluate(()=>Online.send({type:'stop'}));
  await warrior.keyboard.press('Escape');check(await warrior.locator('#pause').isVisible(),'World menu opens');
  const before=await (await fetch(url+'health')).json();await delay(300);const after=await (await fetch(url+'health')).json();check(after.tick>before.tick,'World keeps ticking in menu');
  await warrior.locator('#p-resume').click();await warrior.keyboard.press('e');
  await warrior.locator('#field-warriorArmor').selectOption('none');await warrior.locator('#field-warriorWeapon').selectOption('none');
  await warrior.waitForFunction(()=>Field.hero.look.warriorArmor==='none'&&Field.hero.look.warriorWeapon==='none');
  check(await warrior.evaluate(()=>Field.equipmentStats.attack===26&&Field.equipmentStats.defense===0),'Rapid equipment changes preserve both choices');
  await warrior.locator('#field-warriorArmor').selectOption('crimson');await warrior.locator('#field-warriorWeapon').selectOption('sword');
  await warrior.waitForFunction(()=>Field.equipmentStats.attack===30&&Field.equipmentStats.defense===3);
  await mage.waitForFunction(id=>Field.remotePlayers.find(p=>p.id===id)?.sprite?.equipment.armor==='crimson',warriorId);passed++;
  await warrior.locator('#equipment-close').click();
  const text='<img src=x onerror=window.chatInjected=true> hello world';
  await warrior.locator('#chat-input').fill(text);await warrior.locator('#chat-input').press('Enter');
  await mage.waitForFunction(text=>document.getElementById('chat-log').textContent.includes(text),text);
  check(await mage.evaluate(()=>!window.chatInjected&&!document.querySelector('#chat-log img')),'Chat broadcasts literal text safely');
  const token=await warrior.evaluate(()=>Online.currentToken);
  const duplicate=await probe(mage,{type:'join',version:1,token});check(duplicate.type==='error'&&duplicate.text.includes('already online'),'Duplicate session rejected');
  const invalid=await probe(mage,{type:'join',version:1,token:'a'.repeat(64)});check(invalid.type==='error'&&invalid.text.includes('invalid'),'Invalid resume key rejected');
  const version=await probe(mage,{type:'join',version:999,look:{name:'BadVersion'}});check(version.type==='error','Protocol mismatch rejected');
  await warrior.evaluate(()=>Online.send({type:'attack',fx:1,fy:0,damage:99999}));
  await warrior.waitForFunction(()=>document.getElementById('chat-log').textContent.includes('Invalid command.'));passed++;
  const dashStart=await assassin.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));await assassin.keyboard.press('Shift');
  await assassin.waitForFunction(start=>Math.hypot(Field.hero.x-start.x,Field.hero.y-start.y)>2,dashStart,{timeout:10000});
  const dashEnd=await assassin.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));check(Math.hypot(dashEnd.x-dashStart.x,dashEnd.y-dashStart.y)>2,'Assassin dash works through server');
  await warrior.screenshot({path:path.join(root,'test-results/multiplayer.png')});
  // Fight with real network actions; no direct hero/enemy HP manipulation.
  const state=await mage.evaluate(()=>({start:{x:Field.hero.x,y:Field.hero.y},slimes:Field.slimes.filter(s=>s.kind==='green'&&!s.dead&&s.hx>59&&s.hy>59).map(s=>({id:s.id,x:s.x,y:s.y}))}));
  state.slimes.sort((a,b)=>Math.hypot(a.x-state.start.x,a.y-state.start.y)-Math.hypot(b.x-state.start.x,b.y-state.start.y));
  const target=state.slimes[0];
  await stageAt(mage,{x:target.x-4,y:target.y});
  await mage.evaluate(id=>Online.send({type:'target',id}),target.id);
  await mage.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead&&Field.hero.kills>0,target.id,{timeout:30000});
  await warrior.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead,target.id);passed++;
  const killed=await mage.evaluate(id=>{const s=Field.slimes.find(s=>s.id===id);return {x:s.x,y:s.y};},target.id);
  await mage.evaluate(p=>Online.send({type:'move',...p}),killed);
  await mage.waitForFunction(()=>Field.hero.gold>0,null,{timeout:15000});
  // Recover through the real town service, then meet an Ironhide a few steps away (spawned, not hunted across the map).
  const healer=map.npcs.find(n => n.id === 'healer');
  await stageAt(mage,{x:healer.x+1.2,y:healer.y});
  await mage.evaluate(() => Online.send({ type: 'interact', npc: 'healer', offer: 'blessing' }));
  await mage.waitForFunction(() => Field.hero.hp === Field.hero.maxHp);
  await mage.locator('#npc-dialogue').waitFor({ state: 'visible' });
  await mage.locator('#npc-close').click();
  await stageAt(mage,{x:7,y:64});
  const spawned=await shortcut(mage,{op:'spawn_enemy',kind:'beetle',x:13,y:64});
  await mage.waitForFunction(id=>{const s=Field.slimes.find(s=>s.id===id);return s&&!s.dead&&s.kind==='beetle'&&Math.abs(s.x-13)<2;},spawned.id,{timeout:10000});
  const beetleState=await mage.evaluate(id=>({start:{x:Field.hero.x,y:Field.hero.y},enemy:Field.slimes.find(s=>s.id===id),kills:Field.hero.kills,xp:Field.hero.xp,level:Field.hero.level,xpNeed:Field.hero.xpNeed,gold:Field.hero.gold}),spawned.id);
  const pickupStart=mage.pickups.length, mageId=await mage.evaluate(()=>Online.id);
  const beetle=beetleState.enemy;
  await mage.evaluate(id=>Online.send({type:'target',id}),beetle.id);
  await mage.waitForFunction(id=>{const s=Field.slimes.find(s=>s.id===id);return s&&s.hp<s.maxHp;},beetle.id,{timeout:30000});
  await mage.screenshot({path:path.join(root,'test-results/ironhide-combat.png')});
  check(await mage.evaluate(id=>{const s=Field.slimes.find(s=>s.id===id);return Math.hypot(Field.hero.x-s.x,Field.hero.y-s.y)<9;},beetle.id),'Ironhide is visible in real browser combat');
  await mage.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead,beetle.id,{timeout:30000});
  await warrior.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead,beetle.id);passed++;
  check(await mage.evaluate(before=>Field.hero.kills===before.kills+1&&(()=>{const total=before.xp+45+5*before.enemy.level;return before.level===Field.hero.level&&Field.hero.xp===total||Field.hero.level===before.level+1&&Field.hero.xp===total-before.xpNeed;})()&&Field.hero.hp>0,beetleState),'Beetle combat awards 45 + 5 per enemy level once, carrying any overflow into the next level');
  const beetleDrop=await mage.evaluate(id=>{const s=Field.slimes.find(s=>s.id===id);return {x:s.x,y:s.y};},beetle.id);
  await mage.evaluate(p=>Online.send({type:'move',...p}),beetleDrop);
  const beetleGold=Math.round(10*(1+.1*(beetle.level-5)));
  await mage.waitForFunction(({gold,value})=>Field.hero.gold>=gold+value,{gold:beetleState.gold,value:beetleGold},{timeout:15000});
  check(mage.pickups.slice(pickupStart).some(event=>event.actor===mageId && event.value===beetleGold), 'Server awards the level-scaled beetle gold pickup to its killer');
  const progress=await mage.evaluate(()=>({id:Online.id,gold:Field.hero.gold,kills:Field.hero.kills,xp:Field.hero.xp,level:Field.hero.level}));
  check(progress.kills>0&&progress.gold>0&&(progress.xp>0||progress.level>1),'Server rewards kills, XP, and pickups');
  await mage.reload();await mage.locator('#start').click(); await mage.locator('#login-guest').click();
  await mage.waitForFunction(()=>Online.connected&&!!Field.mageSprites,null,{timeout:60000});
  check(await mage.evaluate(p=>Online.id===p.id&&Field.hero.gold===p.gold&&Field.hero.kills===p.kills,progress),'Character resumes after page reload');
  // Restart the actual Rust process and resume from SQLite through automatic reconnect.
  const bind=new URL(url).host;await stopServer();
  await warrior.waitForFunction(()=>!Online.connected);
  check(await warrior.locator('#connection-overlay').isVisible(),'Disconnect overlay visible');
  await startServer(bind);
  await Promise.all([warrior,mage,assassin].map(page=>page.waitForFunction(()=>Online.connected,null,{timeout:20000})));
  check(await mage.evaluate(p=>Online.id===p.id&&Field.hero.gold===p.gold&&Field.hero.kills===p.kills,progress),'Persistence survives server restart');
  // New characters keep a selectable saved slot for the previous character.
  await warrior.keyboard.press('Escape');await warrior.locator('#p-new').click();
  await warrior.locator('#name').fill('SecondWarrior');await warrior.locator('#go').click();
  await warrior.waitForFunction(()=>Online.connected&&Field.hero.look.name==='SecondWarrior');
  await warrior.keyboard.press('Escape');await warrior.locator('#p-characters').click();
  await warrior.locator('#character-list button').filter({hasText:'TestWarrior'}).click();
  await warrior.waitForFunction(id=>Online.connected&&Online.id===id,warriorId);
  check(await warrior.evaluate(()=>Field.hero.look.warriorWeapon==='sword'),'Saved character picker restores previous gear');
  console.log('Core multiplayer checks passed; checking city travel and NPC services.');
  // Walk into the new city through actual inputs; no server state is changed by tests.
  await warrior.evaluate(()=>Online.send({type:'interact',npc:'healer',offer:'blessing'}));
  await warrior.waitForFunction(()=>document.getElementById('chat-log').textContent.includes('Walk closer'));passed++;
  check(await warrior.locator('#npc-dialogue').isHidden(),'Remote NPC interaction cannot open a shop');
  await warrior.locator('#city-travel').click();
  try {
    await warrior.waitForFunction(()=>Field.hero.y>78.6&&Field.hero.y<80&&Math.abs(Field.hero.x-36)<.4,null,{timeout:40000});
  } catch(error) {
    console.error('City travel stalled:',await warrior.evaluate(()=>({hero:{x:Field.hero.x,y:Field.hero.y},nearby:[...Field.remotePlayers,...Field.slimes].filter(a=>!a.dead&&Math.hypot(a.x-Field.hero.x,a.y-Field.hero.y)<4).map(a=>({id:a.id,x:a.x,y:a.y}))})));
    throw error;
  }
  check(await warrior.locator('#city-travel').isHidden(),'Travel button walks through the city gate');
  await warrior.waitForFunction(()=>document.getElementById('network-status').textContent.includes('Alderhaven'));passed++;
  await warrior.screenshot({path:path.join(root,'test-results/city-square.png')});
  await warrior.keyboard.press('f');
  await warrior.locator('#npc-dialogue').waitFor({state:'visible'});
  check(await warrior.locator('#npc-name').textContent()==='Wren','F talks to nearby town guide');
  const cityTick=(await (await fetch(url+'health')).json()).tick;await delay(300);
  check((await (await fetch(url+'health')).json()).tick>cityTick,'NPC conversations keep the shared world running');
  await warrior.keyboard.press('Escape');check(await warrior.locator('#npc-dialogue').isHidden(),'Escape closes NPC conversation');
  async function walkTo(page,goal) {
    const start=await page.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));
    for(const point of route(map,start,goal)){await page.evaluate(p=>Online.send({type:'move',...p}),point);await page.waitForFunction(p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.4,point,{timeout:20000});}
  }
  async function clickNpc(page,id) {
    const point=await page.evaluate(id=>{const n=City.npcs.find(n=>n.id===id),[x,y]=Field._debug.w2s(n.x,n.y),r=document.getElementById('fieldcv').getBoundingClientRect();return {x:r.left+x/1600*r.width,y:r.top+(y-60)/900*r.height};},id);
    await page.mouse.click(point.x,point.y);await page.locator('#npc-dialogue').waitFor({state:'visible'});
  }
  await walkTo(warrior,{x:32,y:80});await delay(400);await clickNpc(warrior,'healer');
  check(await warrior.locator('#npc-name').textContent()==='Sister Elara','Clicking an NPC opens the correct dialogue');
  const cityGold=await warrior.evaluate(()=>Field.hero.gold);
  await warrior.locator('[data-offer="blessing"]').click();
  await warrior.waitForFunction(()=>document.getElementById('npc-notice').textContent.includes('full health'));
  check(await warrior.evaluate(g=>Field.hero.gold===g,cityGold),'Sanctuary blessing is free and does not charge full-health players');
  await warrior.locator('#npc-close').click();
  await walkTo(warrior,{x:33,y:88});await delay(400);
  await warrior.evaluate(()=>Online.send({type:'equip',armor:'none',weapon:'none'}));
  await warrior.waitForFunction(()=>Field.hero.look.warriorWeapon==='none');
  await clickNpc(warrior,'smith');await warrior.locator('[data-offer="fitting"]').click();
  await warrior.waitForFunction(()=>Field.hero.look.warriorWeapon==='sword'&&Field.hero.look.warriorArmor==='crimson');
  await mage.waitForFunction(id=>Field.remotePlayers.find(p=>p.id===id)?.look.warriorWeapon==='sword',warriorId);passed++;
  check(await warrior.evaluate(g=>Field.hero.gold===g,cityGold),'Armorer service equips server-owned class gear without charging');
  await warrior.screenshot({path:path.join(root,'test-results/city-armorer.png')});await warrior.locator('#npc-close').click();
  await walkTo(warrior,{x:40,y:79});await delay(400);await clickNpc(warrior,'apothecary');
  check(await warrior.locator('[data-offer="tonic"]').isDisabled(),'Shop shows an unaffordable item without allowing a purchase');
  await warrior.locator('#npc-close').click();
  for(const page of [warrior,mage,assassin]) check(page.errors.length===0,'No browser runtime errors: '+page.errors.join('; '));
  for(const page of [warrior,mage,assassin]) check(!page.actorCollision,'Every received authoritative snapshot keeps enemies a cell away from players: '+JSON.stringify(page.actorCollision));
  for(const page of [warrior,mage,assassin]) check(!page.renderCollision,'Rendered enemies remain a cell away from players during movement and combat: '+JSON.stringify(page.renderCollision));
  await warrior.screenshot({path:path.join(root,'test-results/multiplayer-final.png')});
  console.log(`${passed} multiplayer checks passed (Chromium; three independent browser clients, combat, chat, reload, server restart, city travel and NPC shops).`);
})().catch(error=>{console.error(error);console.error(logs);process.exitCode=1;}).finally(async()=>{await browser?.close();await stopServer();});
