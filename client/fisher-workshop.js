'use strict';
// Quotes and payment belong to the Fisher; the client only displays and requests a recipe.
(() => {
  let open=false;
  const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;};
  function close(){if(open){Online.send({type:'shop_presence',open:false});open=false;}}
  function render(npc,packet,container){
    if(!open){Online.send({type:'shop_presence',open:true});open=true;}
    const owned=id=>(packet.inventory||[]).find(s=>s.item===id)?.quantity||0;
    const recipes=packet.fisherQuote||[];
    const nodes=[make('h4','Fisher workshop'),make('p','Craft rods and cook fish')];
    if(owned('fishing_rod_charm'))nodes.push(make('p','Rod Charm replaces one fish and is used up.'));
    for(const group of ['rod:','cook:']){
      nodes.push(make('h4',group==='rod:'?'Craft rods':'Cook fish'));
      for(const r of recipes.filter(r=>r.id.startsWith(group))){
        const item=Inventory.definition(r.item);if(!item)continue;
        const row=make('div','','fisher-recipe');row.dataset.recipe=r.id;
        const text=make('div');
        text.append(make('strong',Locale.translate(item.name)),make('small',`Requires level ${item.requiredLevel||1}.`));
        for(const [id,count] of r.ingredients){
          const name=Inventory.definition(id)?.name||id;
          const line=make('small',`${Locale.translate(name)}: ${owned(id)} / ${count}`);line.dataset.ingredient=id;text.append(line);
        }
        const b=make('button',`${Locale.translate(group==='rod:'?'Craft rod':'Cook fish')} · ${Money.text(r.cost)}`,'btn');b.type='button';b.dataset.offer=r.id;
        b.disabled=packet.gold<r.cost||(packet.level||1)<(item.requiredLevel||1)||r.ingredients.some(([id,n])=>owned(id)<n);
        b.addEventListener('click',()=>{if(Online.send({type:'interact',npc:npc.id,offer:r.id}))b.disabled=true;});
        row.append(text,b);nodes.push(row);
      }
    }
    container.replaceChildren(...nodes);
  }
  window.FisherWorkshop={render,close};
})();
