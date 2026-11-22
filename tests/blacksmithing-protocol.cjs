// Two normal WebSocket guests on a private world and disposable SQLite database.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {TestWorld} = require('../scripts/testing/driver.cjs');

const root = path.resolve(__dirname, '..');
const map = JSON.parse(fs.readFileSync(path.join(root,'world/map.txt')));
const smith = map.npcs.find(n => n.id === 'smith');
const w = new TestWorld();
w.levelSpread = 0;
const wait = (predicate, label) => w.waitFor(predicate, 30000, label);
const send = (bot, packet) => w.bots.get(bot).socket.send(JSON.stringify(packet));
const have = (bot, id) => w.player(bot)?.inventory.find(stack => stack.item === id)?.quantity || 0;

function next(bot, type, match = () => true) {
  const prior = new Set(w.events);
  return wait(() => w.events.find(e => !prior.has(e) && e.bot === bot && e.type === type && match(e)), bot + ' ' + type);
}
function request(bot, type, data, match) {
  const reply = next(bot, type, match);
  send(bot,data);
  return reply;
}
const smithing = (bot, op, fields = {}) => request(bot, 'blacksmithing', {type:'blacksmithing',request:{op,npc:smith.id,...fields}});
const dialogue = bot => request(bot, 'dialogue', {type:'interact',npc:smith.id}, e => e.npc?.id === smith.id);
const warp = (bot, point) => w.debug(bot,{op:'teleport',zone:0,x:point.x,y:point.y});

(async () => {
  await w.start();
  for (const bot of ['Minerone','Minertwo']) {
    await w.connect({bot,class:'warrior'});
    assert.equal(w.player(bot).gathering,undefined,'an untrained character has no gathering flags');
    assert.equal((await smithing(bot,'train')).ok,false,'training requires the real nearby smith');
    await warp(bot,smith);
    assert.equal((await dialogue(bot)).blacksmithing.trainer,true);
    assert.equal((await smithing(bot,'train')).skill,1);
    assert.equal((await smithing(bot,'train')).ok,false,'starter pick cannot be granted twice');
    await wait(() => have(bot,'smith_pick_1') === 1,'starter pick in bags');
    assert.deepEqual(w.player(bot).gathering,{ore:true,flowers:false},'training exposes ore tracking to the owner');
  }
  const other = w.bots.get('Minertwo').id;
  await wait(() => w.views.get('Minerone').players.some(p => p.id === other),'the second miner is visible');
  assert.equal(w.views.get('Minerone').players.find(p => p.id === other).gathering,undefined,'gathering flags stay private');

  const view = w.views.get('Minerone');
  const safe = v => Math.min(...map.slimes.map(s => Math.hypot(s.x-v.x,s.y-v.y)));
  const vein = [...view.miningVeins].sort((a,b) => safe(b)-safe(a))[0];
  const start = bot => request(bot,'mining',{type:'mine',id:vein.id},p => p.state === 'started');
  await warp('Minerone',vein);
  await start('Minerone');
  const interrupted = next('Minerone','mining',e => e.state === 'error');
  send('Minerone',{type:'input',dx:1,dy:0});
  assert.equal((await interrupted).text,'Mining interrupted.');
  await warp('Minerone',vein);
  await warp('Minertwo',vein);
  const pulls = await Promise.all(['Minerone','Minertwo'].map(async bot => {
    const done = next(bot,'mining',p => p.state === 'done');
    await start(bot);
    return done;
  }));
  assert(pulls.every(p => p.item === 'smith_ore_tin' && p.quantity >= 1 && p.quantity <= 2));
  assert.equal(pulls[0].vein,pulls[1].vein);
  assert(w.views.get('Minerone').miningVeins.some(v => v.id === vein.id), 'two pulls cannot exhaust a fresh vein');

  const staple = 'smith_gear_tin_banded_gloves';
  await warp('Minerone',smith);
  const learned = await smithing('Minerone','learn',{recipe:staple});
  assert(learned.ok && learned.recipes.includes(staple));
  const forgedTooEarly = await smithing('Minerone','craft',{recipe:staple});
  assert.equal(forgedTooEarly.ok,false);
  // Only the guaranteed item inputs and level are supplied by the fixture.
  await w.debug('Minerone',{op:'give_item',item:'smith_ore_tin',quantity:6});
  await w.debug('Minerone',{op:'set_gold',gold:100});
  await w.debug('Minerone',{op:'set_level',level:4});
  for (let n = 0; n < 2; n++) {
    send('Minerone',{type:'interact',npc:smith.id,offer:'buy_smith_leather_strips'});
    await wait(() => have('Minerone','smith_leather_strips') === n+1,'shop purchase');
    if (!n) await new Promise(resolve => setTimeout(resolve, 525));
  }
  for (let n = 0; n < 3; n++) {
    const bar = await smithing('Minerone','craft',{recipe:'smith_bar_tin'});
    assert(bar.ok && bar.output === 'smith_bar_tin');
    assert.equal(bar.skill,learned.skill,'smelting grants no skill');
  }
  const made = await smithing('Minerone','craft',{recipe:staple});
  assert(made.ok && made.output === staple);
  send('Minerone',{type:'equip',slots:{gloves:staple}});
  await wait(() => w.player('Minerone')?.equipment.gloves === staple,'wearing the forged gloves');
  const copy = w.player('Minerone').gearInstances.find(g => g.item === staple);
  assert(copy && copy.rarity === 'uncommon');
  await w.restart();
  assert.deepEqual(w.player('Minerone').gathering,{ore:true,flowers:false},'saved training enables tracking after reconnect');
  assert.equal(w.player('Minerone').gearInstances.find(g => g.item === staple).id,copy.id);
  assert.equal(w.player('Minerone').equipment.gloves,staple);
  assert.equal(have('Minerone','smith_pick_1'),1);
  await warp('Minerone',smith);
  const saved = await dialogue('Minerone');
  assert.equal(saved.blacksmithing.skill,made.skill);
  assert(saved.blacksmithing.recipes.includes(staple));
  assert.equal(saved.gold,76);
  console.log('Blacksmithing protocol passed two miners, interruption, ordinary shop stock, smelting, forging, equipping and restart persistence.');
})().catch(error => {
  console.error(error); process.exitCode = 1;
}).finally(() => w.stop());
