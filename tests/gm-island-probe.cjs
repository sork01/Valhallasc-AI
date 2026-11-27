'use strict';
// Real SSO GM, no test flags, disposable server/database. Never uses the public service.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {spawn}=require('node:child_process'),WebSocket=require('ws');
const root=path.resolve(__dirname,'..'),delay=ms=>new Promise(r=>setTimeout(r,ms));
const world=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'))),island=world.zones.findIndex(z=>z.gmOnly)+1;
let server,sso,url,logs='',checks=0;
const clients=[];
const check=(condition,message)=>{assert.ok(condition,message);checks++;};
async function until(test,label,ms=10000){const end=Date.now()+ms;while(Date.now()<end){const v=test();if(v)return v;await delay(25);}throw Error(label);}
async function connect(session,character){
  const c={ws:new WebSocket(url.replace('http','ws')+'ws',{origin:new URL(url).origin}),snapshot:null,events:[],snapshots:[],ref:0,id:null};clients.push(c);
  c.ws.on('message',data=>{const p=JSON.parse(data.toString());if(p.type==='welcome'){c.id=p.id;c.snapshot=p.snapshot;}else if(p.type==='snapshot'){c.snapshot=p;c.snapshots.push({tick:p.tick,at:Date.now()});}else c.events.push(p);});
  await new Promise((r,j)=>{c.ws.once('open',r);c.ws.once('error',j);});
  c.ws.send(JSON.stringify({type:'join',version:1,...(session?{session,character,look:character?undefined:{name:'[GM]Sork',class:'warrior'}}:{look:{name:'IslandOutsider',class:'warrior'}})}));
  await until(()=>c.id,'welcome');
  c.player=()=>c.snapshot.players.find(p=>p.id===c.id);
  c.send=msg=>c.ws.send(JSON.stringify(msg));
  c.heartbeat=setInterval(()=>{if(c.ws.readyState===WebSocket.OPEN)c.send({type:'ping',nonce:Date.now()});},1000);
  c.ws.once('close',()=>clearInterval(c.heartbeat));
  c.debug=async command=>{const ref=++c.ref;c.send({type:'debug',ref,command});const answer=await until(()=>c.events.find(p=>p.type==='debug'&&p.ref===ref),'debug reply');if(answer.ok)await until(()=>c.snapshot.tick>answer.tick,'snapshot after command');return answer;};
  c.ok=async command=>{const r=await c.debug(command);assert.ok(r.ok,r.error);return r.result;};
  return c;
}
async function settle(c){const tick=c.snapshot.tick;await until(()=>c.snapshot.tick>=tick+12,'service cooldown in simulation time');}
async function beside(c,npc){const n=world.zones[island-1].npcs.find(n=>n.id===npc);await c.ok({op:'teleport',zone:island,x:n.x+1,y:n.y});await settle(c);}
async function action(c,action,npc,extra={}){return c.ok({op:'gm_island',action,npc,...extra});}
(async()=>{
  const dir=fs.mkdtempSync(path.join(root,'test-results/gm-island-probe-'));
  try{
    sso=http.createServer((req,res)=>{res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({authenticated:true,username:'Sork',email:''}));});
    await new Promise(r=>sso.listen(0,'127.0.0.1',r));
    const env={...process.env,VALHALLA_BIND:'127.0.0.1:0',VALHALLA_DB:path.join(dir,'test.sqlite'),VALHALLA_SSO_URL:`http://127.0.0.1:${sso.address().port}/sso`,VALHALLA_AMBIENT_PLAYERS:'1'};
    for(const key of ['VALHALLA_ORIGIN','VALHALLA_GOD_MODE','VALHALLA_TEST_COMMANDS','VALHALLA_START_LEVEL'])delete env[key];
    server=spawn(process.env.VALHALLA_BINARY,[],{cwd:root,env,stdio:['ignore','pipe','pipe']});
    for(const stream of [server.stdout,server.stderr])stream.on('data',d=>{logs+=d.toString().replace(/\x1b\[[0-9;]*m/g,'');const m=logs.match(/address=(127\.0\.0\.1:\d+)/);if(m)url='http://'+m[1]+'/';});
    await until(()=>url,'private server startup',20000);
    const auth=await (await fetch(url+'api/sso',{method:'POST',headers:{'Content-Type':'application/json',Origin:new URL(url).origin,Cookie:'sso_session=privateislandfixture12345'},body:'{}'})).json();
    assert.ok(auth.ok&&auth.gm,'verified SSO GM');
    let gm=await connect(auth.session),other=await connect();const original={level:gm.player().level,look:gm.player().look,equipment:gm.player().equipment};
    check(!(await other.debug({op:'gm_island',action:'enter'})).ok,'ordinary account denied island services');
    check(!(await other.debug({op:'teleport',zone:island,x:212,y:337})).ok,'forged teleport denied without test flags');
    await action(gm,'enter');check(gm.player().zone===island,'verified GM enters');
    check(gm.snapshot.weather.inside===false&&gm.snapshot.weather.type==='clear','island has clear outdoor weather');
    check(!gm.snapshot.players.some(p=>p.ambient),'ambient adventurers excluded from island');
    check(!(await gm.debug({op:'gm_island',action:'setup',npc:'gmi_quartermaster',class:'mage',level:60,gear:'rare'})).ok,'distant NPC action denied');
    for(const klass of ['warrior','mage','assassin','priest','hunter']){
      await beside(gm,'gmi_quartermaster');const r=await action(gm,'setup','gmi_quartermaster',{class:klass,level:60,gear:'rare'});
      check(r.equipped===10&&gm.player().look.class===klass,'normal full equipment for '+klass);
    }
    await beside(gm,'gmi_summoner');const spawned=await action(gm,'summon','gmi_summoner',{kind:'hollowking',level:60,count:2});
    check(spawned.ids.length===2,'two independent boss slots created');
    check(gm.snapshot.slimes.filter(s=>spawned.ids.includes(s.id)&&!s.dead).length===2,'both summoned bosses visible');
    await gm.ok({op:'set_god_mode',enabled:true});
    await gm.ok({op:'teleport',zone:island,x:212,y:202});gm.send({type:'target',id:spawned.ids[0]});
    await until(()=>gm.snapshot.damageMeter.rows.some(r=>r.id===gm.id&&r.damage>0),'actual attacks engage summoned boss',12000);
    await until(()=>gm.snapshot.bossMech?.length,'summoned boss mechanics start in the arena',10000);
    check(true,'summoned bosses run real combat and boss mechanics');
    await beside(gm,'gmi_summoner');await action(gm,'clear','gmi_summoner');
    check(gm.snapshot.slimes.filter(s=>spawned.ids.includes(s.id)).every(s=>s.dead),'arena cleared');
    check(!(gm.snapshot.bossMech?.length),'clear ends the arena boss mechanics');
    const seasons=JSON.stringify(gm.snapshot.seasons);
    await settle(gm);const holiday=await action(gm,'summon','gmi_summoner',{kind:'grinch',level:60,count:1});
    await gm.ok({op:'kill_enemy',id:holiday.ids[0]});
    check(gm.snapshot.slimes.find(s=>s.id===holiday.ids[0]).dead,'seasonal boss can be defeated outside its calendar');
    check(JSON.stringify(gm.snapshot.seasons)===seasons&&gm.snapshot.drops.length===0,'island seasonal kill changes no public season or loot');
    await settle(gm);await action(gm,'clear','gmi_summoner');
    await beside(gm,'gmi_recruiter');await action(gm,'mercs','gmi_recruiter',{class:'priest',level:60,count:4});
    check(gm.snapshot.players.filter(p=>p.hired).length===4,'four real mercenaries spawned');
    await settle(gm);const fifth=await gm.debug({op:'gm_island',action:'mercs',npc:'gmi_recruiter',class:'mage',level:60,count:1});check(!fifth.ok&&fifth.error.includes('at most four'),'fifth mercenary denied by hire limit');
    await settle(gm);await action(gm,'dismiss','gmi_recruiter');
    await gm.ok({op:'teleport',zone:island,x:183,y:265});
    const dummy=gm.snapshot.slimes.find(s=>s.kind==='gmi_dummy');assert.ok(dummy);
    gm.send({type:'target',id:dummy.id});
    await until(()=>gm.snapshot.damageMeter.rows.some(r=>r.damage>0),'real attacks damage immortal dummy',12000);
    await delay(1600);check(gm.snapshot.slimes.find(s=>s.id===dummy.id).hp===dummy.maxHp,'dummy health stays full during actual attacks');
    check(gm.snapshot.damageMeter.rows.some(r=>r.id===gm.id&&r.damage>0),'server DPS meter records real hits');
    await beside(gm,'gmi_trainer');await action(gm,'reset_dps','gmi_trainer');
    check(gm.snapshot.damageMeter.rows.every(r=>r.damage===0),'DPS reset removes previous totals');
    async function snapshotWindow() {
      const start=gm.snapshots.length;
      await until(()=>gm.snapshots.length>=start+30,'thirty snapshots',5000);
      const samples=gm.snapshots.slice(start,start+30);
      return {elapsed:samples[29].at-samples[0].at,samples,
        intervals:samples.slice(1).map((s,i)=>({tick:s.tick,ms:s.at-samples[i].at,gap:s.tick-samples[i].tick}))};
    }
    const saveInclusive=await snapshotWindow();
    // World::step_inner saves synchronously every 100 ticks. Retain that sample,
    // and benchmark steady combat ticks in a repeatable window just after a save.
    const previous=gm.snapshot.tick;
    await until(()=>gm.snapshot.tick>previous+4&&gm.snapshot.tick%100<=4,'periodic save checkpoint',10000);
    const steady=await snapshotWindow(),elapsed=steady.elapsed;
    fs.writeFileSync(path.join(dir,'snapshot-timing.txt'),JSON.stringify({saveInclusive,steady},null,2));
    check(elapsed<=3000&&steady.intervals.every(s=>s.gap===2),`30 steady snapshots in ${elapsed} ms, tick gaps of 2`);
    const character=gm.id;gm.ws.close();await delay(700);gm=await connect(auth.session,character);
    check(gm.player().zone===island&&gm.player().look.class==='hunter','test loadout survives reconnect');
    await action(gm,'enter'); // reconnect starts hidden; entering makes the lab visible again
    await beside(gm,'gmi_ferryman');await action(gm,'leave','gmi_ferryman');
    check(gm.player().zone===0&&gm.player().level===original.level&&gm.player().look.class===original.look.class,'leaving restores original level/class');
    assert.deepEqual(gm.player().equipment,original.equipment);check(true,'original GM equipment restored after reconnect');
    check(other.player().zone===0&&other.player().level===1,'ordinary player unaffected');
    fs.writeFileSync(path.join(dir,'receipt.txt'),JSON.stringify({checks,snapshots:30,snapshotMs:elapsed,saveInclusiveMs:saveInclusive.elapsed,publicServiceTouched:false},null,2));
    console.log(`gm-island-probe: ${checks} checks passed (${elapsed} ms / 30 snapshots); ${dir}`);
  }finally{
    for(const c of clients)c.ws.close();server?.kill('SIGTERM');sso?.close();
  }
})().catch(e=>{console.error(e);console.error(logs.slice(-1500));process.exitCode=1;});
