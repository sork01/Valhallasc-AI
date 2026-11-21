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
vm.runInContext(moduleText,context,{filename:'blacksmithing.js'});

const Blacksmithing = context.Blacksmithing;
const state = {trainer:true,skill:0,recipes:[]};
const npc = {id:'smith'};
const inventory = [{item:'smith_bar_tin',quantity:3},{item:'smith_leather_strips',quantity:2}];
const packet = {blacksmithing:state,inventory,gold:10};
const render = () => Blacksmithing.render(npc,packet,panel);
const row = id => panel.querySelectorAll('[data-recipe]').find(n => n.dataset.recipe === id);
render();
assert.equal(panel.children[0].textContent,'Smide');
panel.children.at(-1).click();
assert.equal(sent.at(-1).request.op,'train');

Blacksmithing.onPacket({ok:true,npc:'smith',text:'You learned Blacksmithing and received a starter pick.',skill:1,recipes:[],inventory,gold:10});
const recipe = 'smith_gear_tin_banded_gloves';
assert.equal(row(recipe).children[1].children[0].textContent,'Tennbeslagna handskar');
assert.equal(row(recipe).children[1].children[1].textContent,'Preview');
assert(panel.children.some(n => n.textContent === 'Smidesfärdighet 1 / 300'));
assert(panel.children.some(n => /^Träna upp till 30 med Tennmalm/.test(n.textContent)));
row(recipe).children.at(-1).click();
assert.deepEqual(sent.at(-1),{type:'blacksmithing',request:{op:'learn',npc:'smith',recipe}});
Blacksmithing.onPacket({ok:true,npc:'smith',text:'You learned the blueprint.',skill:1,recipes:[recipe],inventory:[],gold:10});
assert.equal(row(recipe).children.at(-1).disabled,true,'forge is disabled without inputs');
Blacksmithing.onPacket({ok:true,npc:'smith',text:'',skill:1,recipes:[recipe],inventory,gold:10});
assert.equal(row(recipe).children.at(-1).disabled,false);
row(recipe).children.at(-1).click();
assert.equal(sent.at(-1).request.op,'craft');
Blacksmithing.onPacket({ok:true,npc:'smith',text:'',skill:150,recipes:[],inventory:[],gold:10});
assert(panel.children.some(n => /Andra gruvområden · .*Rán/.test(n.textContent)));


const vein = {id:11,tier:0,x:100,y:60}, actor = {mining:11,x:90,y:60};
Blacksmithing.sync({miningVeins:[vein],players:[actor]},actor,cue => cues.push(cue));
Blacksmithing.onPacket({ok:true,npc:'smith',text:'You forged equipment.',skill:2,recipes:[recipe],inventory:[],gold:10,output:recipe});
const project = (x,y) => [x,y];
assert.equal(Blacksmithing.pick(95,45,project).id,vein.id);
assert.equal(Blacksmithing.pick(15,15,project),undefined);
Blacksmithing.start(vein);
assert.deepEqual(sent.at(-1),{type:'mine',id:11});
Blacksmithing.mining({state:'started',vein:11,duration:1.8});
assert.equal(status.hidden,false);
Blacksmithing.draw({drawImage:(...args) => calls.push(args),fillRect(){},save(){},restore(){},translate(){},rotate(){}},project,250,100,false);
assert.equal(calls.length,2,'vein and pick draw using packed assets');
Blacksmithing.mining({state:'done',vein:11,item:'smith_ore_tin',quantity:2,skill:2,skillUp:true});
assert.equal(status.textContent,'Bröt 2 × Tennmalm · Smide 2');
assert.deepEqual(cues,['forge','strike']);
Blacksmithing.mining({state:'error',text:'Mining interrupted.'});
assert.deepEqual(errors,['Mining interrupted.']);
Blacksmithing.reset();
assert.equal(Blacksmithing.pick(95,45,project),undefined);
assert.equal(status.hidden,true);
console.log('Blacksmithing client passed Swedish rendering, action gating, canvas hit detection, animated art and cues.');
