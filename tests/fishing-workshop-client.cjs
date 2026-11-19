// Quote rendering runs the real module in a small DOM; service rules are checked with Rust/browser integration.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
class Node {
  constructor(){this.children=[];this.dataset={};this.events={};this.textContent='';}
  append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}
  addEventListener(type,fn){this.events[type]=fn;}
}
const items=JSON.parse(fs.readFileSync(path.join(root,'world/items.txt')));
const sent=[],ctx={document:{createElement:()=>new Node()},Online:{send:p=>{sent.push(p);return true;}},Inventory:{definition:id=>items.find(i=>i.id===id),rodDetails:i=>['Keeps every earlier fishing unlock. Upgrading consumes the previous rod.'],foodBonus:i=>'Food bonus'},Locale:{translate:t=>t},Money:{text:n=>`${n} copper`}};
ctx.window=ctx;vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(root,'client/fisher-workshop.js'),'utf8'),ctx);
const holder=new Node(),recipe={id:'rod:2',item:'rod_willow_rod',cost:250,ingredients:[['rod_twig_rod',1],['fish_pier_sprat',4],['slime_gel',1],['fishing_rod_charm',1]]};
const packet={gold:250,level:10,inventory:recipe.ingredients.map(([item,quantity])=>({item,quantity})),fisherQuote:[recipe]};
ctx.FisherWorkshop.render({id:'fisher_meadow_0'},packet,holder);
const flatten=n=>[n,...n.children.flatMap(flatten)];
let nodes=flatten(holder),button=nodes.find(n=>n.dataset.offer==='rod:2');
assert(button&&!button.disabled);assert(nodes.some(n=>n.textContent.includes('Upgrading consumes the previous rod.')));assert(nodes.some(n=>n.textContent==='Rod Charm replaces one fish and is used up.'));
assert(nodes.some(n=>n.dataset.ingredient==='fish_pier_sprat'&&n.textContent.endsWith('4 / 4')));
button.events.click();assert(button.disabled);assert.equal(sent.at(-1).offer,'rod:2');
for(const field of ['gold','level','fish']){
 const p=JSON.parse(JSON.stringify(packet));if(field==='gold')p.gold=249;if(field==='level')p.level=9;if(field==='fish')p.inventory.find(s=>s.item==='fish_pier_sprat').quantity=3;
 ctx.FisherWorkshop.render({id:'fisher_meadow_0'},p,holder);button=flatten(holder).find(n=>n.dataset.offer==='rod:2');assert(button.disabled,field);
}
assert.equal(sent.filter(p=>p.type==='shop_presence'&&p.open).length,1);
ctx.FisherWorkshop.close();assert.equal(sent.at(-1).open,false);ctx.FisherWorkshop.close();assert.equal(sent.filter(p=>p.type==='shop_presence'&&!p.open).length,1);
console.log('Fisher quote client: explicit charm/ingredient costs, level/gold/input checks, pending action and shop presence pass');
