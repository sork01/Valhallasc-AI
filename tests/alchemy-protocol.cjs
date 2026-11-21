// Two players exercise normal Alchemy messages on a disposable private world.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {TestWorld} = require('../scripts/testing/driver.cjs');

const map = JSON.parse(fs.readFileSync(require.resolve('../world/map.txt')));
const trainer = map.npcs.find(n => n.id === 'alchemy_alderhaven');
const [first, second] = ['HerbGatherer', 'FlowerBrewer'];
const potion = 'alchemy_meadowgold_potion', flask = 'alchemy_cinderheart_flask';
const meadow = 'alchemy_meadowgold', vial = 'alchemy_empty_vial';
const w = new TestWorld();
w.startLevel = 5;
w.levelSpread = 0;
const wait = (predicate, label) => w.waitFor(predicate, 12000, label);
const send = (who, packet) => w.bots.get(who).socket.send(JSON.stringify(packet));
const qty = (who, id) => w.player(who)?.inventory.find(stack => stack.item === id)?.quantity || 0;
const buffs = who => (w.player(who)?.buffs || []).filter(buff => buff.kind === 'alchemy').map(buff => buff.id);

function next(who, type, match = () => true) {
  const prior = new Set(w.events);
  return wait(() => w.events.find(e => !prior.has(e) && e.bot === who && e.type === type && match(e)), who + ' ' + type);
}
function request(who, type, data, match) {
  const reply = next(who, type, match);
  send(who,data);
  return reply;
}
const workshop = (who, op, fields = {}) => request(who, 'alchemy', {type:'alchemy', request:{op,npc:trainer.id,...fields}});
const talk = who => request(who, 'dialogue', {type:'interact',npc:trainer.id}, p => p.npc?.id === trainer.id);
const warp = (who, point) => w.debug(who,{op:'teleport',zone:0,x:point.x,y:point.y});

(async () => {
  await w.start();
  for (const who of [first, second]) {
    await w.connect({bot:who,class:'warrior'});
    assert.equal((await workshop(who,'train')).ok,false,'Alderhaven trainer is required');
    await warp(who,trainer);
    assert((await talk(who)).alchemy.trainer);
    assert.equal((await workshop(who,'train')).skill,1);
  }

  const patches = w.views.get(first).flowerPatches;
  assert.equal(patches.length,4);
  const city = map.city;
  const garden = patches.find(p => city.x0 < p.x && p.x < city.x1 && city.y0 < p.y && p.y < city.y1);
  assert(garden, 'Alderhaven has an active garden patch');
  const start = who => request(who,'picking',{type:'pick_flower',id:garden.id}, p => p.state === 'started');
  await warp(first,garden);
  await start(first);
  const interrupted = next(first,'picking',p => p.state === 'error');
  send(first,{type:'input',dx:1,dy:0});
  assert.equal((await interrupted).text,'Picking interrupted.');
  await warp(first,garden);
  await warp(second,garden);
  const pulls = await Promise.all([first,second].map(async who => {
    const done = next(who,'picking',p => p.state === 'done');
    await start(who);
    return done;
  }));
  assert(pulls.every(p => p.patch === garden.id && p.item === meadow && p.quantity >= 1 && p.quantity <= 2));

  await warp(first,trainer);
  const learned = await workshop(first,'learn',{recipe:potion});
  assert(learned.ok && learned.recipes.includes(potion));
  assert.equal((await workshop(first,'brew',{recipe:potion})).ok,false);
  await w.debug(first,{op:'give_item',item:meadow,quantity:2});
  await w.debug(first,{op:'set_gold',gold:60});
  send(first,{type:'interact',npc:trainer.id,offer:'buy_alchemy_empty_vial'});
  await wait(() => qty(first,vial) === 1,'buy a normal shop vial');
  const brewed = await workshop(first,'brew',{recipe:potion});
  assert(brewed.ok && brewed.output === potion);
  send(first,{type:'use_item',item:potion});
  await wait(() => buffs(first).includes(potion),'actual potion buff');
  assert(w.player(first).potionCd > 58);

  // Exercise the drinker's paths without leveling a second profession band.
  await w.debug(first,{op:'give_item',item:flask,quantity:1});
  send(first,{type:'use_item',item:flask});
  await wait(() => buffs(first).includes(flask),'independent flask slot during potion cooldown');
  assert.deepEqual(new Set(buffs(first)),new Set([flask,potion]));
  assert.deepEqual(buffs(second),[]);

  await w.restart();
  assert.deepEqual(buffs(first),[flask]);
  assert(w.player(first).potionCd > 0,'shared cooldown survived restart');
  assert.equal(qty(first,potion),0);
  assert.equal(qty(first,flask),0);
  await warp(first,trainer);
  const saved = await talk(first);
  assert.equal(saved.alchemy.skill,brewed.skill);
  assert(saved.alchemy.recipes.includes(potion));
  assert.equal(saved.gold,35);
  console.log('Alchemy protocol passed two players, interrupted and shared gathering, shop, brew, both buff slots and restart persistence.');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => w.stop());
