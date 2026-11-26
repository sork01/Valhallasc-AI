// Pure client behaviour checks; no Chromium or production connection.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root=path.resolve(__dirname,'..');
function fixture() {
  const all=[];
  class Element {
    constructor(tag='div') {this.tagName=tag;this.children=[];this.dataset={};this.style={};this.events={};this.hidden=false;this.attributes={};this.classList={add(){},remove(){},toggle(){}};all.push(this);}
    append(...children) {for(const c of children){this.children.push(c);if(c&&typeof c==='object')c.parentElement=this;}}
    replaceChildren(...children){this.children=[];this.append(...children);}
    addEventListener(name,fn){this.events[name]=fn;}
    setAttribute(k,v){this.attributes[k]=v;}
    removeAttribute(k){delete this.attributes[k];}
    getBoundingClientRect(){return {x:0,y:0,top:0,right:10,width:200,height:100};}
    contains(){return false;}
    querySelectorAll(){return [];}
    querySelector(){return null;}
    before(){} focus(){} close(){} remove(){} showModal(){this.open=true;}
    get textContent(){return this._text||this.children.map(c=>typeof c==='string'?c:c.textContent).join(' ');}
    set textContent(t){this._text=String(t);this.children=[];}
  }
  const body=new Element(),stage=new Element();stage.id='stage';
  const bagHome=new Element(),bag=new Element();bagHome.append(bag);
  for(const id of ['npc-dialogue','npc-name','inventory-list','npc-inventory','bags-close']){const n=new Element();n.id=id;}
  const ctx={document:{body,createElement:tag=>new Element(tag),getElementById:id=>all.find(n=>n.id===id)||null,querySelector:s=>s==='.bag-window'?bag:null,querySelectorAll:()=>[]},
    WORLD_ITEMS:JSON.parse(fs.readFileSync(path.join(root,'world/items.txt'))),
    Online:{connected:true,send:()=>true},Field:{hero:{level:99,maxHp:10000,mealCd:17,potionCd:3},useItem(id){this.used=id;},equipSlot(){throw Error('fish or rod equipped');}},
    Money:{text:n=>`${n} copper`},innerWidth:1600,innerHeight:900,dispatchEvent(){},Event:class{},setTimeout:()=>0,clearTimeout(){}};
  ctx.window=ctx;vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(root,'client/alchemy-data.js'),'utf8'),ctx);
  let inventory=fs.readFileSync(path.join(root,'client/inventory.js'),'utf8');
  if(process.env.MUTATE==='compatible')inventory=execFileSync('git',['show','af607ebd:client/inventory.js'],{cwd:root,encoding:'utf8'});
  vm.runInContext(inventory,ctx);
  let shop=fs.readFileSync(path.join(root,'client/shop.js'),'utf8');
  if(process.env.MUTATE==='flowers') {
    assert(shop.includes('!gatheredFlowers.has(row.item)'));
    shop=shop.replace('!gatheredFlowers.has(row.item)','true');
  }
  if(process.env.MUTATE==='junk')shop=shop.replace("Inventory.definition(row.item)?.kind === 'material'","['material','fish'].includes(Inventory.definition(row.item)?.kind)");
  if(process.env.MUTATE==='warning')shop=shop.replace("(Inventory.definition(row.item)?.kind === 'fish' && row.rarity === 'rare')","false");
  // Expose closures only inside this fixture, to execute the real selection/confirmation paths.
  shop=shop.replace('  window.Shop = {',`  window.fishingTest={isJunk,confirm,prepare(row){npc={id:'merchant'};data={goldPercent:0};basket.set(key(row),row);}};\n  window.Shop = {`);
  vm.runInContext(shop,ctx);
  return {ctx,all,Element};
}
const {ctx,all,Element}=fixture();
const generated={window:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'client/items.js'),'utf8'),generated);
assert.equal(JSON.stringify(generated.window.WORLD_ITEMS),JSON.stringify(ctx.WORLD_ITEMS),'client item catalogue matches generated data');
const fish=ctx.WORLD_ITEMS.find(i=>i.kind==='fish'&&i.rarity==='common');
const rod=ctx.WORLD_ITEMS.find(i=>i.kind==='rod'&&!i.fishing.lava);
const rare=ctx.WORLD_ITEMS.find(i=>i.kind==='fish'&&i.rarity==='rare');
const lava=ctx.WORLD_ITEMS.find(i=>i.kind==='rod'&&i.fishing.lava);
const look={class:'warrior'};
ctx.Inventory.update([{item:fish.id,quantity:12},{item:rod.id,quantity:1}],look);
assert.equal(ctx.Inventory.bagQuantity(fish.id),12);
assert.equal(ctx.Inventory.looseCopies(fish.id).length,0);
assert.equal(ctx.Inventory.cooldownLeft(fish),17);
assert(ctx.Inventory.effect(fish).includes(`up to ${fish.heal.toLocaleString()} HP`));
const anchor=new Element();
for(const [item,text] of [[fish,'Fish'],[rod,'For water fishing'],[lava,'For water and lava fishing']]){
 ctx.Inventory.showTooltip(anchor,item);
 const tooltip=all.find(n=>n.id==='item-tooltip');
 assert(tooltip.textContent.includes(text),tooltip.textContent);
 assert(!tooltip.textContent.includes('Right-click to equip'),tooltip.textContent);
}
const list=new Element();ctx.Inventory.render(list);
const cells=list.children.filter(n=>n.dataset.item);
assert.equal(cells.length,2,'fish stack and rod each occupy one bag cell');
cells.find(n=>n.dataset.item===fish.id).children[0].events.dblclick();
assert.equal(ctx.Field.used,fish.id,'raw fish use the existing meal action');
ctx.Field.used=null;
cells.find(n=>n.dataset.item===rod.id).children[0].events.dblclick();
assert.equal(ctx.Field.used,null,'rod stays in the bag');
const row=i=>({item:i.id,rarity:i.rarity,quantity:1,base:i.sell});
for (const { item: id } of ctx.ALCHEMY_DATA.flowers) {
  const flower = ctx.WORLD_ITEMS.find(i => i.id === id);
  assert.equal(ctx.fishingTest.isJunk(row(flower)), false, `${id} stays in the bags after Sell all junk`);
}
assert.equal(ctx.fishingTest.isJunk(row(fish)),false,'common fish are never sold by Sell all junk');
assert.equal(ctx.fishingTest.isJunk(row(rod)),false);
const junk=ctx.WORLD_ITEMS.find(i=>i.fishing?.loot==='junk');
assert.equal(ctx.fishingTest.isJunk(row(junk)),true);
const treasure=ctx.WORLD_ITEMS.find(i=>i.fishing?.loot==='treasure');
assert.equal(ctx.fishingTest.isJunk(row(treasure)),false);
ctx.fishingTest.prepare(row(rare));ctx.fishingTest.confirm();
assert(all.some(n=>n.id==='sell-warning'&&n.open),'rare fish sale requires confirmation');
console.log('Fishing client data: stacking, tooltips, rod use, raw meal, junk protection and rare-sale confirmation pass');
