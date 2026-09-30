const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const timeout = (promise, ms, label) => Promise.race([promise, new Promise((_, reject) => { const timer = setTimeout(() => reject(Error(label)), ms); timer.unref(); })]);
let server, browser, url, db, logs = '', passed = 0;
const check = (condition, message) => { assert.ok(condition, message); passed++; };
async function startServer(bind = '127.0.0.1:0') {
  logs = '';
  const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
  server = spawn(binary, [], { cwd: root, env: { ...process.env, VALHALLA_BIND: bind, VALHALLA_DB: db, RUST_LOG: 'valhalla_server=info' }, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stderr.on('data', data => { logs += data; });
  await timeout(new Promise((resolve, reject) => {
    server.stdout.on('data', data => { logs += data; const match = logs.match(/address=(127\.0\.0\.1:\d+)/); if (match) { url = 'http://' + match[1] + '/'; resolve(); } });
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
  const page = await context.newPage(); page.errors = [];
  page.on('pageerror', error => page.errors.push(error.message));
  await page.goto(url); await page.locator('#start').click();
  await page.locator('#cls-' + type).click(); await page.locator('#name').fill(name);
  await page.locator('#go').click();
  await page.waitForFunction(() => Online.connected && !!(Field.warriorSprites || Field.mageSprites || Field.assassinSprites), null, { timeout: 60000 });
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
// Find a route through the REAL exported collision geometry, without changing server state.
function route(map, start, goal) {
  const segmentFree = (a,b) => map.objects.every(o => {
    const dx=b.x-a.x,dy=b.y-a.y;
    if(o.width) { const steps=Math.ceil(Math.hypot(dx,dy)/.1);for(let i=0;i<=steps;i++){const t=i/(steps||1);if(Math.abs(a.x+dx*t-o.x)<o.width/2+.4&&Math.abs(a.y+dy*t-o.y)<o.depth/2+.4)return false;}return true; }
    const t=Math.max(0,Math.min(1,((o.x-a.x)*dx+(o.y-a.y)*dy)/(dx*dx+dy*dy || 1)));
    return Math.hypot(o.x-a.x-dx*t,o.y-a.y-dy*t)>o.r+.4;
  });
  const key = p => `${p.x},${p.y}`;
  const source = { x: Math.round(start.x), y: Math.round(start.y) }, end = { x: Math.round(goal.x), y: Math.round(goal.y) };
  const queue = [source], previous = new Map([[key(source), null]]);
  for (let i=0; i<queue.length; i++) {
    const current=queue[i]; if (key(current)===key(end)) break;
    for (const [dx,dy] of [[0,1],[0,-1],[1,0],[-1,0],[1,1],[-1,-1],[1,-1],[-1,1]]) {
      const next={x:current.x+dx,y:current.y+dy};
      if (next.x<1 || next.y<1 || next.x>map.size-2 || next.y>map.size-2 || previous.has(key(next)) || !segmentFree(current,next)) continue;
      previous.set(key(next),current);queue.push(next);
    }
  }
  assert.ok(previous.has(key(end)), 'Destination is reachable through shared collision geometry');
  const points=[]; for(let current=end; current; current=previous.get(key(current))) points.unshift(current);
  const simplified=[];let anchor=start;
  for (let i=0;i<points.length;) {let j=i;while(j+1<points.length && segmentFree(anchor,points[j+1])) j++;simplified.push(points[j]);anchor=points[j];i=j+1;}
  return simplified;
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
  await warrior.waitForFunction(() => Field.remotePlayers.length === 2 && Field.remotePlayers.every(p => p.sprite), null, { timeout: 60000 });
  check(await warrior.evaluate(() => Field.hero.maxHp===120 && Field.remotePlayers.some(p=>p.look.class==='mage'&&p.maxHp===80) && Field.remotePlayers.some(p=>p.look.class==='assassin'&&p.maxHp===90)), 'Three classes see each other');
  check(await warrior.locator('#connection-overlay').isHidden(), 'Connected overlay is visibly hidden');
  check(await warrior.locator('#chat').isVisible(), 'Chat is visible');
  const warriorId=await warrior.evaluate(()=>Online.id);
  const start=await warrior.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));
  await warrior.keyboard.down('d');await delay(500);await warrior.keyboard.up('d');await delay(400);
  const moved=await warrior.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));
  check(Math.hypot(moved.x-start.x,moved.y-start.y)>.8 && Math.hypot(moved.x-start.x,moved.y-start.y)<4, 'Server controlled keyboard movement');
  await mage.waitForFunction(({id,x,y})=>{const p=Field.remotePlayers.find(p=>p.id===id);return p && Math.hypot(p.x-x,p.y-y)<.2;},{id:warriorId,...moved});passed++;
  await warrior.keyboard.press('Escape');check(await warrior.locator('#pause').isVisible(),'World menu opens');
  const before=await (await fetch(url+'health')).json();await delay(300);const after=await (await fetch(url+'health')).json();check(after.tick>before.tick,'World keeps ticking in menu');
  await warrior.locator('#p-resume').click();await warrior.keyboard.press('i');
  await warrior.locator('#field-warriorArmor').selectOption('none');await warrior.locator('#field-warriorWeapon').selectOption('none');
  await warrior.waitForFunction(()=>Field.hero.look.warriorArmor==='none'&&Field.hero.look.warriorWeapon==='none');
  check(await warrior.evaluate(()=>Field.equipmentStats.attack===26&&Field.equipmentStats.defense===0),'Rapid equipment changes preserve both choices');
  await warrior.locator('#field-warriorArmor').selectOption('azure');await warrior.locator('#field-warriorWeapon').selectOption('royal');
  await warrior.waitForFunction(()=>Field.equipmentStats.attack===34&&Field.equipmentStats.defense===5);
  await mage.waitForFunction(id=>Field.remotePlayers.find(p=>p.id===id)?.sprite?.equipment.armor==='azure',warriorId);passed++;
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
  const dashStart=await assassin.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));await assassin.keyboard.press('Shift');await delay(500);
  const dashEnd=await assassin.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));check(Math.hypot(dashEnd.x-dashStart.x,dashEnd.y-dashStart.y)>2,'Assassin dash works through server');
  await warrior.screenshot({path:path.join(root,'test-results/multiplayer.png')});
  // Fight with real network actions; no direct hero/enemy HP manipulation.
  await mage.evaluate(()=>Online.send({type:'equip',armor:'runic',weapon:'crystal'}));
  await mage.waitForFunction(()=>Field.hero.look.mageWeapon==='crystal');
  const state=await mage.evaluate(()=>({start:{x:Field.hero.x,y:Field.hero.y},slimes:Field.slimes.filter(s=>s.kind==='green'&&!s.dead).map(s=>({id:s.id,x:s.x,y:s.y}))}));
  state.slimes.sort((a,b)=>Math.hypot(a.x-state.start.x,a.y-state.start.y)-Math.hypot(b.x-state.start.x,b.y-state.start.y));
  const target=state.slimes[0];const waypoints=route(map,state.start,target);
  for (const point of waypoints) {
    if (Math.hypot(point.x-target.x,point.y-target.y)<3) break;
    await mage.evaluate(p=>Online.send({type:'move',...p}),point);
    await mage.waitForFunction(p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.5,point,{timeout:20000});
  }
  await mage.evaluate(id=>Online.send({type:'target',id}),target.id);
  await mage.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead&&Field.hero.kills>0,target.id,{timeout:30000});
  await warrior.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead,target.id);passed++;
  const killed=await mage.evaluate(id=>{const s=Field.slimes.find(s=>s.id===id);return {x:s.x,y:s.y};},target.id);
  await mage.evaluate(p=>Online.send({type:'move',...p}),killed);
  await mage.waitForFunction(()=>Field.hero.gold>0,null,{timeout:15000});
  const progress=await mage.evaluate(()=>({id:Online.id,gold:Field.hero.gold,kills:Field.hero.kills,xp:Field.hero.xp,level:Field.hero.level}));
  check(progress.kills>0&&progress.gold>0&&(progress.xp>0||progress.level>1),'Server rewards kills, XP, and pickups');
  await mage.reload();await mage.locator('#start').click();
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
  check(await warrior.evaluate(()=>Field.hero.look.warriorWeapon==='royal'),'Saved character picker restores previous gear');
  console.log('Core multiplayer checks passed; checking city travel and NPC services.');
  // Walk into the new city through actual inputs; no server state is changed by tests.
  await warrior.evaluate(()=>Online.send({type:'interact',npc:'healer',offer:'blessing'}));
  await warrior.waitForFunction(()=>document.getElementById('chat-log').textContent.includes('Walk closer'));passed++;
  check(await warrior.locator('#npc-dialogue').isHidden(),'Remote NPC interaction cannot open a shop');
  await warrior.locator('#city-travel').click();
  await warrior.waitForFunction(()=>Field.hero.y>78.6&&Field.hero.y<80&&Math.abs(Field.hero.x-36)<.4,null,{timeout:40000});
  check(await warrior.locator('#city-travel').isHidden(),'Travel button walks through the city gate');
  await warrior.waitForFunction(()=>document.getElementById('network-status').textContent.includes('Alderhaven'));passed++;
  await warrior.screenshot({path:path.join(root,'test-results/city-square.png')});
  await warrior.keyboard.press('e');
  await warrior.locator('#npc-dialogue').waitFor({state:'visible'});
  check(await warrior.locator('#npc-name').textContent()==='Wren','E talks to nearby town guide');
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
  await warrior.waitForFunction(()=>Field.hero.look.warriorWeapon==='royal'&&Field.hero.look.warriorArmor==='azure');
  await mage.waitForFunction(id=>Field.remotePlayers.find(p=>p.id===id)?.look.warriorWeapon==='royal',warriorId);passed++;
  check(await warrior.evaluate(g=>Field.hero.gold===g,cityGold),'Armorer service equips server-owned class gear without charging');
  await warrior.screenshot({path:path.join(root,'test-results/city-armorer.png')});await warrior.locator('#npc-close').click();
  await walkTo(warrior,{x:40,y:79});await delay(400);await clickNpc(warrior,'apothecary');
  check(await warrior.locator('[data-offer="tonic"]').isDisabled(),'Shop shows an unaffordable item without allowing a purchase');
  await warrior.locator('#npc-close').click();
  for(const page of [warrior,mage,assassin]) check(page.errors.length===0,'No browser runtime errors: '+page.errors.join('; '));
  await warrior.screenshot({path:path.join(root,'test-results/multiplayer-final.png')});
  console.log(`${passed} multiplayer checks passed (Chromium; three independent browser clients, combat, chat, reload, server restart, city travel and NPC shops).`);
})().catch(error=>{console.error(error);console.error(logs);process.exitCode=1;}).finally(async()=>{await browser?.close();await stopServer();});
