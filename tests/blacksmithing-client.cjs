// Exercise the real client module in a lightweight DOM fixture.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname,'..');
const read = file => fs.readFileSync(path.join(root,'client',file),'utf8');
class Node {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {};
    this.textContent = ''; this.scrollTop = 0; this.classList = {add: () => {}};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, handler) { if (type === 'click') this.click = handler; }
  setAttribute(key, value) { this.attributes[key] = value; }
  querySelectorAll(selector) {
    const matches = node => selector === '.smith-recipes' ? node.className === 'smith-recipes'
      : selector === '[data-recipe]' ? !!node.dataset.recipe : !!node.dataset.smithAction;
    return this.children.flatMap(node => (matches(node) ? [node] : []).concat(node.querySelectorAll(selector)));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
}

const sent = [], cues = [], errors = [], calls = [];
const status = new Node('div'), panel = new Node('div');
const context = vm.createContext({
  document:{documentElement:{},body:{nodeType:0},getElementById:() => status, createElement:tag => new Node(tag)},
  Node:{TEXT_NODE:3,ELEMENT_NODE:1}, MutationObserver:class {observe() {}},
  localStorage:{getItem:() => '{"lang":"sv"}'},
  performance:{now:() => 300}, Image:class { naturalWidth = 300; },
  setTimeout:() => 1, clearTimeout() {},
  Online:{send:payload => { sent.push(JSON.parse(JSON.stringify(payload))); return true; }, log:() => {}},
  Field:{error:text => errors.push(text)},
  Money:{html:amount => String(amount)},
});
context.window = context;
for (const file of ['sv-data.js','locale.js','world.js','items.js','blacksmithing-data.js','blacksmithing-art.js'])
  vm.runInContext(read(file),context,{filename:file});
const items = new Map(context.WORLD_ITEMS.map(item => [item.id,item]));
context.Inventory = {definition:id => items.get(id), icon:item => item.id, attachTooltip() {}, gearPreview:() => 'Preview'};
let moduleText = read('blacksmithing.js');
if (process.env.MUTATE === 'allow-missing') {
  assert(moduleText.includes('|| !supplies'));
  moduleText = moduleText.replace('|| !supplies','');
}
if (process.env.MUTATE === 'no-click') {
  assert(moduleText.includes("return Online.send({type:'mine', id:vein.id});"));
  moduleText = moduleText.replace("return Online.send({type:'mine', id:vein.id});","return false;");
}
if (process.env.MUTATE === 'mine-range') {
  assert(moduleText.includes('let best = 2.6;'));
  moduleText = moduleText.replace('let best = 2.6;', 'let best = Infinity;');
}
if (process.env.MUTATE === 'small-vein') {
  assert(moduleText.includes('VEIN_SIZE = 92'));
  moduleText = moduleText.replace('VEIN_SIZE = 92', 'VEIN_SIZE = 46');
}
if (process.env.MUTATE === 'expert-cap') {
  const before = "format('Blacksmithing skill {0} / {1}', skill, maxSkill)";
  assert.ok(moduleText.includes(before));
  moduleText = moduleText.replace(before, before.replace('maxSkill', '300'));
}
if (process.env.MUTATE === 'bulk') moduleText = moduleText.replace('all:true', 'all:false');
if (process.env.MUTATE === 'expert-pick-hint') {
  const line = "if (pick) target.append(element('small', pickHint(pick)));";
  assert(moduleText.includes(line));
  moduleText = moduleText.replace(line, '');
}
if (process.env.MUTATE === 'expert-plan-source') moduleText = moduleText.replace('recipe.dropZone != null', 'false');
vm.runInContext(moduleText,context,{filename:'blacksmithing.js'});

const Blacksmithing = context.Blacksmithing;
const state = {trainer:true,skill:0,maxSkill:600,training:null,recipes:[]};
const npc = {id:'smith'};
const inventory = [{item:'smith_bar_tin',quantity:3},{item:'smith_leather_strips',quantity:2}];
const packet = {blacksmithing:state,inventory,gold:10};
const render = () => Blacksmithing.render(npc,packet,panel);
const answer = fields => Blacksmithing.onPacket({
  maxSkill:600, training:{cap:30,ore:'smith_ore_tin',zones:[0]}, ...fields,
});
const row = id => panel.querySelectorAll('[data-recipe]').find(n => n.dataset.recipe === id);
const action = (id, bulk = false) => row(id).querySelectorAll('[data-smith-action]')
  .find(node => node.dataset.smithAction === (bulk ? 'all:' + id : id));
render();
assert.equal(panel.children[0].textContent,'Smide');
panel.children.at(-1).click();
assert.equal(sent.at(-1).request.op,'train');

answer({ok:true,npc:'smith',text:'You learned Blacksmithing and received a starter pick.',skill:1,recipes:[],inventory,gold:10});
const recipe = 'smith_gear_tin_banded_gloves';
assert.equal(row(recipe).children[1].children[0].textContent,'Tennbeslagna handskar');
assert.equal(row(recipe).children[1].children[1].textContent,'Preview');
assert(panel.children.some(n => n.textContent === 'Smidesfärdighet 1 / 600'));
assert(panel.children.some(n => /^Träna upp till 30 med Tennmalm/.test(n.textContent)));
action(recipe).click();
assert.deepEqual(sent.at(-1),{type:'blacksmithing',request:{op:'learn',npc:'smith',recipe}});
answer({ok:true,npc:'smith',text:'You learned the blueprint.',skill:1,recipes:[recipe],inventory:[],gold:10});
assert.equal(action(recipe).disabled,true,'forge is disabled without inputs');
assert.equal(action(recipe,true).disabled,true,'Forge All also needs ingredients');
answer({ok:true,npc:'smith',text:'',skill:1,recipes:[recipe],inventory,gold:10});
assert.equal(action(recipe).disabled,false);
action(recipe).click();
assert.deepEqual(sent.at(-1).request,{op:'craft',npc:'smith',recipe});
answer({ok:true,npc:'smith',text:'',skill:1,recipes:[recipe],inventory,gold:10});
assert.equal(action(recipe,true).textContent,'Smid alla');
action(recipe,true).click();
assert.deepEqual(sent.at(-1).request,{op:'craft',npc:'smith',recipe,all:true},'Forge All sends a single batch request');
answer({ok:true,npc:'smith',text:'',skill:1,recipes:[],inventory:[{item:'smith_ore_tin',quantity:6}],gold:10});
panel.querySelectorAll('[data-smith-action]').find(n => n.dataset.smithAction === 'smelt').click();
const smelt = action('smith_bar_tin',true);
assert.equal(smelt.textContent,'Smält alla');
smelt.click();
assert.deepEqual(sent.at(-1).request,{op:'craft',npc:'smith',recipe:'smith_bar_tin',all:true});
answer({ok:true,npc:'smith',text:'',skill:150,training:{cap:180,ore:'smith_ore_cobalt',zones:[7,8]},recipes:[],inventory:[],gold:10});
assert(panel.children.some(n => /Andra gruvområden · .*Rán/.test(n.textContent)));
const saved = {skill:300, maxSkill:600, training:{cap:330, ore:'smith_ore_stormsilver', zones:[16],pick:'smith_pick_6'}};
Blacksmithing.render(npc, {...packet, blacksmithing:{...state, ...saved}}, panel);
assert(panel.children.some(n => n.textContent === 'Smidesfärdighet 300 / 600'));
assert(panel.children.some(n => n.textContent.includes('330') && n.textContent.includes('Moonspore')));
assert(panel.children.some(n => n.textContent.includes('Använd Moonsporehacka eller en bättre hacka')));
const tab = value => panel.querySelectorAll('[data-smith-action]').find(n => n.dataset.smithAction === value);
tab('staple').click();
assert.equal(row('smith_gear_stormglass_mantle').children.at(-1).textContent,
  'Fiender i The Stormglass Flats kan tappa ritningen.');
tab('upgrade').click();
assert.equal(panel.querySelectorAll('[data-recipe]').length,10);
assert.match(row('smith_pick_6').children[1].children[1].textContent,/till 360/);
assert.match(Blacksmithing.pickDetails(items.get('smith_pick_11')),/Ger 1 extra malm per brytning/);
const lastPick = context.BLACKSMITHING_DATA.recipes.find(r => r.item === 'smith_pick_11');
const pickInputs = lastPick.ingredients.map(([item,quantity]) => ({item,quantity}));
answer({ok:true,npc:'smith',text:'',skill:599,training:{cap:600,ore:'smith_ore_stariron',zones:[45],pick:'smith_pick_10'},recipes:[],inventory:pickInputs,gold:lastPick.cost});
assert(panel.children.some(n => /^Träna upp till 600/.test(n.textContent)));
assert.equal(action(lastPick.item).disabled,true);
answer({ok:true,npc:'smith',text:'',skill:600,training:null,recipes:[],inventory:pickInputs,gold:lastPick.cost});
assert(panel.children.some(n => n.textContent === 'Smidesfärdighet 600 / 600'));
assert(!panel.children.some(n => /^Träna upp till/.test(n.textContent)));
assert.equal(action(lastPick.item).disabled,false);
action(lastPick.item).click();
assert.deepEqual(sent.at(-1).request,{op:'craft',npc:'smith',recipe:lastPick.item});
answer({ok:true,npc:'smith',text:'',skill:600,training:null,recipes:[],inventory:[],gold:0});
tab('staple').click();
const masterPlan = row('smith_gear_equinox_crown_ring');
assert(masterPlan.children[1].children.some(n => n.textContent.includes('600')));
assert.equal(masterPlan.children.at(-1).textContent,'Slutbossar kan tappa ritningen.');

const vein = {id:11,tier:0,x:100,y:60}, actor = {mining:11,x:90,y:60};
Blacksmithing.sync({miningVeins:[vein],players:[actor]},actor,cue => cues.push(cue));
answer({ok:true,npc:'smith',text:'You forged equipment.',skill:2,recipes:[recipe],inventory:[],gold:10,output:recipe});
const project = (x,y) => [x,y];
assert.equal(Blacksmithing.pick(95,45,project).id,vein.id);
assert.equal(Blacksmithing.pick(145,0,project)?.id,vein.id,'the enlarged vein can be selected beyond its old bounds');
assert.equal(Blacksmithing.pick(147,0,project),undefined,'a point outside the enlarged vein misses');
assert.equal(Blacksmithing.pick(15,15,project),undefined);
Blacksmithing.start(vein);
assert.deepEqual(sent.at(-1),{type:'mine',id:11});
Blacksmithing.mining({state:'started',vein:11,duration:1.8});
assert.equal(status.hidden,false);
const canvas = {drawImage:(...args) => calls.push(args),fillRect(){},save(){},restore(){},translate(){},rotate(){}};
Blacksmithing.drawVein(canvas,vein,vein.x,vein.y);
Blacksmithing.drawMiners(canvas,project,250,100,false);
assert.equal(calls.length,2,'vein and pick draw using packed assets');
assert.deepEqual(calls[0].slice(-4),[54,-29,92,92],'ore doubles in both dimensions around the same ground anchor');
assert.deepEqual(calls[1].slice(-2),[31,31],'the mining pick retains its original size');
Blacksmithing.mining({state:'done',vein:11,item:'smith_ore_tin',quantity:2,skill:2,skillUp:true});
assert.equal(status.textContent,'Bröt 2 × Tennmalm · Smide 2');
assert.deepEqual(cues,['forge','strike']);
Blacksmithing.mining({state:'done',item:'smith_ore_stormsilver',quantity:2,skill:300,requiredPick:'smith_pick_6'});
assert.match(status.textContent,/Bröt 2 × Stormsilvermalm · Använd Moonsporehacka/);
Blacksmithing.mining({state:'error',text:'Mining interrupted.'});
assert.deepEqual(errors,['Mining interrupted.']);
Blacksmithing.reset();
assert.equal(Blacksmithing.pick(95,45,project),undefined);
assert.equal(status.hidden,true);

const fieldSource = read('field.js');
const touchSource = read('touch.js');
const hero = {x:100,y:60};
const stop = () => sent.push({type:'stop'});
Object.assign(context, { hero, npcTarget:null, Field:{canAct:true, hero, stopMoving:stop}, emitHud() {} });
vm.runInContext('function startGathering'+fieldSource.split('  function startGathering')[1].split('  function onPointerDown')[0]
  +'\nField.action = function('+fieldSource.split('    action(')[1].split('\n    clearInput()')[0].replace(/},\s*$/, '}'), context);
const controls = { fish:new Node('button'), mine:new Node('button'), coarse:{matches:true}, tr:context.Locale.translate };
Object.assign(context, controls);
vm.runInContext('function updateProfessionButtons() {'+touchSource.split('  function update() {')[1].split('    const ids = assignments()')[0]+'}', context);
const syncVeins = (x, mining) => Blacksmithing.sync({
  miningVeins:[{id:12,x:102,y:60},vein,{id:13,x:110,y:60}],players:[],
},{x,y:60,mining},() => {});
syncVeins(113);
context.updateProfessionButtons();
assert.equal(controls.mine.hidden,true,'Mine ore is hidden outside mining reach');
assert.equal(context.Field.action('mine'),false,'out-of-range mining sends nothing');
syncVeins(100.5);
context.updateProfessionButtons();
assert.equal(controls.mine.hidden,false);
assert.equal(controls.mine.textContent,'Bryt malm');
assert.equal(context.Field.action('mine'),true);
assert.deepEqual(sent.slice(-2),[{type:'stop'},{type:'mine',id:11}],'touch uses the nearest active vein and stops movement');
syncVeins(100.5,11);
context.updateProfessionButtons();
assert.equal(controls.mine.disabled,true,'an active pull disables the button');
assert.equal(controls.mine.textContent,'Bryter malm …');
assert.equal(context.Field.action('mine'),false,'an active pull ignores repeated input');
Blacksmithing.reset();
assert.equal(Blacksmithing.nearbyVein,null);
console.log('Blacksmithing client passed Swedish rendering, action gating, canvas hit detection, animated art and cues.');
