// Real private WebSocket persistence checks. No combat, grinding or public characters.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const boxes = JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../world/mailboxes.txt')));
const items = JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../world/items.txt')));
let checks=0;
const ok = (condition,label) => { assert.ok(condition,label); checks++; };
(async()=>{
  const w=new TestWorld();
  try {
    await w.start(); await w.connect({bot:'PostAlice'}); await w.connect({bot:'PostBob'});
    const ask=async(bot,request,npc=boxes[0].id)=>{
      const prior=new Set(w.events);
      w.bots.get(bot).socket.send(JSON.stringify({type:'mail',npc,request}));
      return w.waitFor(()=>w.events.find(e=>!prior.has(e)&&e.bot===bot&&e.type==='mail'),5000,request.op);
    };
    const at=async(bot,b)=>{await w.debug(bot,{op:'teleport',zone:b.zone,x:b.x,y:b.y});await w.waitFor(()=>{const p=w.player(bot);return (p.zone||0)===b.zone&&Math.hypot(p.x-b.x,p.y-b.y)<.5;});};
    for(const b of boxes){await at('PostAlice',b);const p=await ask('PostAlice',{op:'open'},b.id);ok(p.ok,`${b.hub} mailbox opens`);}
    await at('PostAlice',boxes[0]);await at('PostBob',boxes[0]);
    await w.debug('PostAlice',{op:'set_gold',gold:500});await w.debug('PostAlice',{op:'give_item',item:'slime_gel',quantity:5});
    let p=await ask('PostAlice',{op:'lookup',name:'postbob'});ok(p.found==='PostBob','canonical lookup');
    const send={op:'send',request:'network-receipt-mail-0001',recipient:'PostBob',subject:'Offline gift',body:'Hello\n<b>plain text</b>',gold:100,attachments:[{item:'slime_gel',quantity:2}]};
    await w.disconnect('PostBob');
    p=await ask('PostAlice',send);ok(p.ok&&p.gold===400,'offline send deducted once');const id=p.sent;
    p=await ask('PostAlice',send);ok(p.ok&&p.gold===400&&p.sent===id,'duplicate send receipt');
    await w.connect({bot:'PostBob'});await at('PostBob',boxes[0]);
    p=await ask('PostBob',{op:'open'});ok(p.letters.length===1&&p.letters[0].body===send.body,'offline inbox on reconnect');
    p=await ask('PostAlice',{op:'collect',id});ok(!p.ok,'sender cannot collect');
    p=await ask('PostBob',{op:'delete',id});ok(!p.ok,'pending attachments cannot be deleted');
    p=await ask('PostBob',{op:'read',id});ok(p.ok&&p.letters[0].read,'mark read');
    p=await ask('PostBob',{op:'collect',id});ok(p.ok&&p.gold===100&&p.inventory.some(s=>s.item==='slime_gel'&&s.quantity===2),'collect whole escrow');
    p=await ask('PostBob',{op:'collect',id});ok(p.ok&&p.gold===100,'duplicate collection');
    const neutral=items.find(i=>['necklace','cloak','accessory','headgear'].includes(i.kind)&&!i.class&&!i.starter&&i.rarity!=='gm');assert.ok(neutral);
    await w.debug('PostAlice',{op:'give_item',item:neutral.id,quantity:1});
    p=await ask('PostAlice',{op:'open'});const copy=p.choices.find(a=>a.item===neutral.id&&!a.reason);assert.ok(copy);
    p=await ask('PostAlice',{...send,request:'network-receipt-mail-0002',subject:'Copy to return',gold:10,attachments:[{item:neutral.id,quantity:1,copy:copy.copy}]});ok(p.ok,'unbound selected gear sent');const returned=p.sent;
    p=await ask('PostBob',{op:'return',id:returned});ok(p.ok,'return preserves escrow');
    p=await ask('PostAlice',{op:'collect',id:returned});ok(p.ok&&p.gearInstances.some(g=>g.item===neutral.id),'sender collects returned gear');
    const bound=items.find(i=>i.class==='warrior'&&!i.starter&&i.kind==='weapon');
    await w.debug('PostAlice',{op:'give_item',item:bound.id,quantity:1});p=await ask('PostAlice',{op:'open'});const boundCopy=p.choices.find(a=>a.item===bound.id);
    p=await ask('PostAlice',{...send,request:'network-receipt-mail-0003',gold:0,attachments:[{item:bound.id,quantity:1,copy:boundCopy.copy}]});ok(!p.ok&&/Bound/.test(p.notice),'forged bound attachment refused');
    await w.restart();await at('PostBob',boxes[0]);p=await ask('PostBob',{op:'collect',id});ok(p.ok&&p.gold===100,'restart cannot duplicate claimed gold');
    p=await ask('PostBob',{op:'delete',id});ok(p.ok&&p.letters.length===0,'delete after collection');
    await at('PostAlice',boxes[0]);p=await ask('PostAlice',send);ok(p.ok&&p.gold===400&&p.sent===id,'deleted receipt survives restart');
    fs.writeFileSync(require('node:path').join(w.runDir,'mail-check.json'),JSON.stringify({checks,mailboxes:boxes.length,passed:true},null,2));
    console.log(`mail-check: ${checks} checks, ${boxes.length} mailboxes; private online/offline/restart escrow passed`);
  }finally{await w.stop();}
})().catch(e=>{console.error(e);process.exitCode=1;});
