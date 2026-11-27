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
    let pending=false;
    const buttons=[];
    const nodes=[make('h4','Fisher workshop'),make('p','Craft rods and cook fish'),make('p','One rod grows with you. Each upgrade replaces the previous rod and keeps its fishing waters.')];
    if(owned('fishing_rod_charm'))nodes.push(make('p','Rod Charm replaces one fish and is used up.'));
    for(const group of ['rod:','cook:']){
      nodes.push(make('h4',group==='rod:'?'Craft rods':'Cook fish'));
      for(const r of recipes.filter(r=>r.id.startsWith(group))){
        const item=Inventory.definition(r.item);if(!item)continue;
        const row=make('div','','fisher-recipe');row.dataset.recipe=r.id;
        const text=make('div');
        text.append(make('strong',Locale.translate(item.name)),make('small',`Requires level ${item.requiredLevel||1}.`));
        if(item.kind==='rod')for(const detail of Inventory.rodDetails(item))text.append(make('small',detail));
        if(item.foodBonus)text.append(make('small',Inventory.foodBonus(item)));
        for(const [id,count] of r.ingredients){
          const name=Inventory.definition(id)?.name||id;
          const line=make('small',`${Locale.translate(name)}: ${owned(id)} / ${count}`);line.dataset.ingredient=id;text.append(line);
        }
        const actions=make('div','','recipe-actions');
        const disabled=packet.gold<r.cost||(packet.level||1)<(item.requiredLevel||1)||r.ingredients.some(([id,n])=>owned(id)<n);
        const addAction=(offer,label)=>{
          const b=make('button',label,'btn');b.type='button';b.dataset.offer=offer;b.disabled=disabled;
          b.addEventListener('click',()=>{
            if(pending||!Online.send({type:'interact',npc:npc.id,offer}))return;
            pending=true;
            for(const button of buttons)button.disabled=true;
          });
          actions.append(b);buttons.push(b);
        };
        addAction(r.id,Locale.translate(group==='rod:'?'Craft rod':'Cook fish')+' · '+Money.text(r.cost));
        if(group==='cook:')addAction('cook_all:'+r.id.slice(group.length),Locale.translate('Cook All'));
        row.append(text,actions);nodes.push(row);
      }
    }
    container.replaceChildren(...nodes);
  }
  window.FisherWorkshop={render,close};
})();
