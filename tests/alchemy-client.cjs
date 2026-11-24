// Exercise production workshop, translations, canvas and packet handling without a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname,'../client');
const read = name => fs.readFileSync(path.join(root,name),'utf8');

class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.classList = {add() {}, remove() {}};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(event, handler) { this[event] = handler; }
  setAttribute() {}
  closest() { return null; }
  querySelectorAll(selector) {
    const matches = node => selector === 'button' ? node.tagName === 'button' : !!node.dataset.recipe;
    return this.children.flatMap(node => [...(matches(node) ? [node] : []), ...node.querySelectorAll(selector)]);
  }
}

const packets = [], drawCalls = [], cues = [];
const status = new Element('div'), panel = new Element('div');
const context = vm.createContext({
  document:{documentElement:{}, body:{nodeType:0}, getElementById:() => status, createElement:tag => new Element(tag)},
  Node:{TEXT_NODE:3,ELEMENT_NODE:1}, MutationObserver:class {observe() {}},
  localStorage:{getItem:() => '{"lang":"sv"}'},
  performance:{now:() => 300}, Image:class {complete = true; naturalWidth = 288;},
  setTimeout:() => 1, clearTimeout() {},
  Online:{send:payload => { packets.push(JSON.parse(JSON.stringify(payload))); return true; }},
  Field:{zone:6},
});
context.window = context;
for (const name of ['sv-data.js','locale.js','world.js','items.js','alchemy-data.js','alchemy-art.js']) {
  vm.runInContext(read(name),context,{filename:name});
}
const definitions = new Map(context.WORLD_ITEMS.map(item => [item.id,item]));
context.Inventory = {definition:id => definitions.get(id), icon:item => item.id, attachTooltip() {}};

let source = read('alchemy.js');
const replacements = {
  'allow-missing': ['!enough || skill < recipe.skill','skill < recipe.skill'],
  'no-click': ["Online.send({type:'pick_flower', id:patch.id});", 'void patch;'],
  'bulk': ['all:true','all:false'],
  'no-overlap': ['Math.floor((skill + GATHERING_OVERLAP) / SKILL_BAND)', 'band'],
};
if (process.env.MUTATE) {
  const [before, after] = replacements[process.env.MUTATE];
  assert(source.includes(before));
  source = source.replace(before, after);
}
vm.runInContext(source,context,{filename:'alchemy.js'});

const Alchemy = context.Alchemy;
const npc = {id:'alchemy_alderhaven'};
const potion = 'alchemy_meadowgold_potion';
const mixed = 'alchemy_deepbloom_flask';
const skill = () => panel.children[1].textContent;
const row = id => panel.querySelectorAll('[data-recipe]').find(n => n.dataset.recipe === id);
const action = (id, bulk = false) => row(id).querySelectorAll('button')
  .find(n => n.dataset.alchemyAction === (bulk ? 'all:' + id : id));
const tab = id => panel.querySelectorAll('button').find(n => n.dataset.alchemyAction === id);
const reply = (level, known, inventory = [], output) => Alchemy.onPacket({
  ok:true, skill:level, npc:npc.id, recipes:known, inventory, output, text:'You learned the recipe.',
});

Alchemy.render(npc,{alchemy:{trainer:true,skill:0,recipes:[]}},panel);
panel.children[2].click();
assert.deepEqual(packets.at(-1),{type:'alchemy',request:{op:'train',npc:npc.id}});
reply(1,[]);
assert.equal(skill(),'Alkemifärdighet 1 / 600');
assert.equal(row(potion).children[1].children[0].textContent,'Ängsguldsdryck');
assert.match(Alchemy.effect(definitions.get(potion)),/4 % skada i 15 s/);
action(potion).click();
assert.deepEqual(packets.at(-1),{type:'alchemy',request:{op:'learn',npc:npc.id,recipe:potion}});
reply(1,[potion]);
assert.equal(action(potion).disabled,true,'missing containers and flowers prevent brewing');
assert.equal(action(potion,true).disabled,true,'Brew All also needs ingredients');

tab('flowers').click();
assert.match(panel.children.at(-1).children.map(n => n.textContent).join('\n'),/Wyrdklöver.*105\n.*Månslöjeorkidé.*135/);
tab('recipes').click();
reply(44,[]);
assert(!panel.children.some(n => /Plocka de här blommorna.*90/.test(n.textContent)));
reply(45,[]);
assert(panel.children.some(n => /Nå 60 genom att plocka eller brygga/.test(n.textContent)));
assert(panel.children.some(n => /Plocka de här blommorna.*90/.test(n.textContent)));
const supplies = [
  {item:'alchemy_heartvine_bloom',quantity:2},{item:'alchemy_dune_lotus',quantity:2},
  {item:'alchemy_thornsilk_blossom',quantity:1},{item:'alchemy_empty_flask',quantity:1},
];
reply(480,[mixed],supplies);
assert.equal(action(mixed).disabled,false,'alternates combine to fill one requirement');
action(mixed).click();
assert.deepEqual(packets.at(-1).request,{op:'brew',npc:npc.id,recipe:mixed});
reply(480,[mixed],supplies);
assert.equal(action(mixed,true).textContent,'Brygg alla');
action(mixed,true).click();
assert.deepEqual(packets.at(-1).request,{op:'brew',npc:npc.id,recipe:mixed,all:true},'Brew All sends a single batch request');

const patch = {id:47,flower:0,x:100,y:60};
const project = (x,y) => [x,y];
Alchemy.sync({flowerPatches:[patch]},cue => cues.push(cue));
reply(481,[mixed],[],mixed);
assert.equal(Alchemy.hit(100,48,project).id,47);
Alchemy.start(patch);
assert.deepEqual(packets.at(-1),{type:'pick_flower',id:47});
Alchemy.picking({state:'started',patch:47,duration:1.5});
assert.equal(status.textContent,'Plockar blommor…');
Alchemy.drawPatch({drawImage:(...args) => drawCalls.push(args),save(){},restore(){},fillRect(){}},patch,patch.x,patch.y);
assert.equal(drawCalls.length,1);
assert.deepEqual(drawCalls[0].slice(-4),[77,17,46,46],'flowers retain their size and ground anchor');
Alchemy.picking({state:'done',patch:47,item:'alchemy_meadowgold',quantity:2,skill:2,skillUp:true});
assert.equal(status.textContent,'+2 Ängsguld · Alkemi 2');
assert.deepEqual(cues,['brew','pick']);
Alchemy.sync({},()=>{});
assert.equal(Alchemy.hit(100,48,project),undefined,'map change clears old patches');
Alchemy.reset();
assert.equal(status.hidden,true);
console.log('Alchemy client passed Swedish, training, recipe gating, mixed flowers, zone guidance and active patch controls.');
