// Real WebSocket clients with a fresh private database. The normal profession, purchase and trade messages do the work.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const map = read('world/map.txt');
const items = read('world/items.txt');
const npc = map.zones[3].npcs.find(n => n.id === 'city_transmog');
const rare = items.find(i => i.id === 'necklace_moonstone_l1_blue');
const epic = items.find(i => i.id === 'necklace_moonstone_l10_purple');
const green = items.find(i => i.id === 'necklace_moonstone_l1_green');
const recipe = 'enchant_recipe_second_wind';
const scroll = 'enchant_scroll_second_wind';
const world = new TestWorld();
world.levelSpread = 0;
const wait = (predicate, label) => world.waitFor(predicate, 12000, label);
const send = (bot, data) => world.bots.get(bot).socket.send(JSON.stringify(data));
const have = (bot, id) => world.player(bot)?.inventory.find(s => s.item === id)?.quantity || 0;
const findCopies = (bot, id) => world.player(bot)?.gearInstances.filter(g => g.item === id) || [];
const trade = (bot, command) => send(bot, {type:'trade',command});
function packet(bot, type, filter = () => true) {
  const before = new Set(world.events);
  return wait(() => world.events.find(e => !before.has(e) && e.bot === bot && e.type === type && filter(e)), bot + ' ' + type);
}
async function ench(bot, request) {
  const answer = packet(bot, 'enchanting');
  send(bot, {type:'enchanting',request});
  return answer;
}
(async () => {
  await world.start();
  await world.connect({bot:'Crafter',class:'warrior'});
  await world.connect({bot:'Buyer',class:'mage'});
  for (const bot of ['Crafter','Buyer']) await world.debug(bot, {op:'teleport',zone:4,x:npc.x,y:npc.y});
  const cost = npc.offers.find(offer => offer.item === recipe).cost;
  await world.debug('Crafter', {op:'set_gold',gold:cost});
  send('Crafter', {type:'interact',npc:npc.id,offer:'buy_' + recipe});
  await wait(() => have('Crafter',recipe) === 1 && world.player('Crafter').gold === 0, 'vendor charges full recipe price');
  assert.equal((await ench('Crafter',{op:'learn'})).skill,1);
  assert((await ench('Crafter',{op:'study',enchant:'second_wind'})).recipes.includes('second_wind'));

  for (const [item, quantity] of [[green,2],[rare,3],[epic,1]]) {
    await world.debug('Crafter', {op:'give_item',item:item.id,quantity});
  }
  const opened = await ench('Crafter',{op:'open'});
  for (const {gear} of opened.copies.filter(({gear}) => gear.item === green.id).concat(opened.copies.filter(({gear}) => gear.item === rare.id).slice(0,1))) {
    assert((await ench('Crafter',{op:'disenchant',copy:gear.id})).ok);
  }
  assert.equal((await ench('Crafter',{op:'craft',enchant:'second_wind'})).skill,6);
  assert((await ench('Crafter',{op:'apply',enchant:'second_wind',copy:opened.copies.filter(({gear}) => gear.item === rare.id).at(-1).gear.id})).ok);
  await wait(() => findCopies('Crafter',rare.id).some(copy => copy.enchant), 'authoritative enchanted copy');
  const copy = findCopies('Crafter',rare.id).find(g => g.enchant);
  const visible = world.views.get('Buyer').players.find(p => p.id === world.player('Crafter').id);
  assert(!('gearInstances' in visible));
  for (const [bot,id,quantity] of [['Crafter','enchant_dust',4],['Crafter','enchant_essence',2]]) {
    await world.debug(bot,{op:'give_item',item:id,quantity});
  }
  assert((await ench('Crafter',{op:'craft',enchant:'second_wind'})).ok);
  await world.debug('Buyer',{op:'set_gold',gold:50000});
  const invited = packet('Buyer','trade',e => e.state === 'request');
  trade('Crafter',{op:'request',id:world.player('Buyer').id});
  await invited;
  const openedTrade = packet('Crafter','trade',e => e.state === 'open');
  trade('Buyer',{op:'accept',id:world.player('Crafter').id});
  await openedTrade;
  const shown = packet('Buyer','trade',e => e.theirs?.gear?.length === 1);
  trade('Crafter',{op:'offer_copies',items:[{item:rare.id,quantity:1},{item:scroll,quantity:1}],copies:[copy.id],gold:0});
  assert.equal((await shown).theirs.gear[0].enchant,'second_wind');
  const addedGold = packet('Buyer','trade',e => e.mine?.gold === 50000);
  trade('Buyer',{op:'offer',items:[],gold:50000});
  await addedGold;
  const finished = packet('Buyer','trade',e => e.state === 'complete');
  trade('Crafter',{op:'confirm'});
  trade('Buyer',{op:'confirm'});
  await finished;
  await wait(() => have('Buyer',scroll) === 1 && findCopies('Buyer',rare.id).some(g => g.enchant), 'copy and crafted scroll arrive');
  assert.equal(have('Crafter',rare.id),1);
  assert(!findCopies('Crafter',rare.id).some(g => g.enchant));
  await world.debug('Buyer',{op:'give_item',item:epic.id,quantity:1});
  const buyer = await ench('Buyer',{op:'open'});
  assert.equal(buyer.skill,0);
  const target = buyer.copies.find(({gear}) => gear.item === epic.id).gear;
  assert((await ench('Buyer',{op:'apply',enchant:'second_wind',copy:target.id})).ok);
  send('Buyer',{type:'equip',slots:{necklace:rare.id}});
  await wait(() => world.player('Buyer').equipment.necklace === rare.id, 'buyer equips traded gear');
  const inspected = packet('Crafter','inspect',e => e.ok);
  send('Crafter',{type:'inspect',id:world.player('Buyer').id});
  assert.equal((await inspected).slots.find(row => row.slot === 'necklace').enchant,'second_wind');
  await world.restart();
  assert.equal(findCopies('Buyer',rare.id)[0].enchant,'second_wind');
  assert.equal(findCopies('Buyer',epic.id)[0].enchant,'second_wind');
  assert.equal(have('Buyer',scroll),0);
  assert.equal(have('Crafter',recipe),0);
  assert((await ench('Crafter',{op:'open'})).recipes.includes('second_wind'));
  console.log('Enchanting private protocol passed purchase, crafting, copy-specific trade, Inspect and restart (' + world.snapshotsChecked + ' snapshots)');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await world.stop(); });
