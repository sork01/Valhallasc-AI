'use strict';
// Alderhaven gearwright: explicit copy IDs, server previews and a separate confirmation.
(() => {
  const chosen={mergeA:null,mergeB:null,refine:null};
  const make=(tag,text,className)=>{const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;};
  const item=id=>WORLD_ITEMS.find(i=>i.id===id);
  const names=['strength','agility','intellect','stamina','dexterity','accuracy'];
  const stats=g=>{
    const factor=1+(g.rank||0)*.04;
    const one=n=>Math.round(n*factor*10)/10;
    return [g.attack?`${one(g.attack)} attack`:'',g.defense?`${one(g.defense)} defense`:'',
      ...names.filter(k=>(g.bonusStats?.[k]||0)+(g.rolledStats?.[k]||0)).map(k=>`${Math.round(((g.bonusStats?.[k]||0)+(g.rolledStats?.[k]||0))*factor)} ${k}`)]
      .filter(Boolean).join(' · ')||'No stat bonus';
  };
  function equippedIds(packet){
    const counts=new Map();
    for(const id of Object.values(packet.equipment||{}))counts.set(id,(counts.get(id)||0)+1);
    const look=packet.look||{};
    for(const kind of ['armor','weapon']){
      const variant=look[look.class+(kind==='armor'?'Armor':'Weapon')];
      const gear=WORLD_ITEMS.find(i=>i.kind===kind&&(i.class===look.class||i.source==='orange_pool')&&i.variant===variant);
      if(gear)counts.set(gear.id,(counts.get(gear.id)||0)+1);
    }
    const worn=new Set();
    for(const copy of packet.gearInstances||[]){
      const left=counts.get(copy.item)||0;
      if(left){worn.add(copy.id);counts.set(copy.item,left-1);}
    }
    return worn;
  }
  const label=(g,worn)=>`${item(g.item)?.name||g.item} · ${g.rarity} · rank ${g.rank} · #${g.id}${worn.has(g.id)?' · equipped':''}`;
  function select(copies,value,worn){
    const control=make('select','','gear-service-select');
    for(const copy of copies){const option=make('option',label(copy,worn));option.value=String(copy.id);control.append(option);}
    if(copies.some(g=>String(g.id)===String(value)))control.value=String(value);
    return control;
  }
  // Smith's window: every damaged copy with its condition and server-quoted price, one Repair button each and Repair all.
  function renderRepair(npc,packet,container){
    const quote=new Map((packet.repairQuote||[]).map(([id,price])=>[id,price]));
    const copies=(packet.gearInstances||[]).filter(g=>quote.has(g.id)),worn=equippedIds(packet);
    const total=[...quote.values()].reduce((sum,price)=>sum+price,0);
    const elements=[make('h4','Repair gear'),make('p','Dying wears every piece you wear down by a tenth. A broken piece gives no stats until it is repaired. A smith charges a quarter of the piece\'s sale value for a full repair.')];
    if(packet.repairMultiplier===4)elements.push(make('p','Dungeon repairs cost four times the town price.'));
    if(!copies.length){elements.push(make('p','Nothing needs repair.'));container.replaceChildren(...elements);return;}
    const send=offer=>Online.send({type:'interact',npc:npc.id,offer});
    for(const g of copies){
      const left=Math.max(0,100-(g.wear||0)),price=quote.get(g.id);
      const row=make('div','','repair-row');row.dataset.copy=String(g.id);row.dataset.state=left<=0?'broken':left<=30?'low':'worn';
      const state=left<=0?'Broken':`Durability ${left}%`;
      const name=make('span',`${item(g.item)?.name||g.item} · ${g.rarity}${worn.has(g.id)?' · equipped':''} · ${state}`,'repair-name');
      const button=make('button',`Repair · ${price.toLocaleString()} gold`,'btn ghost');button.type='button';button.dataset.action='repair';
      button.disabled=packet.gold<price;
      button.addEventListener('click',()=>{button.disabled=true;send(`repair:${g.id}`);});
      row.append(name,button);elements.push(row);
    }
    const all=make('button',`Repair all · ${total.toLocaleString()} gold`,'btn');all.type='button';all.dataset.action='repair_all';
    all.disabled=packet.gold<total;
    all.addEventListener('click',()=>{all.disabled=true;send('repair_all');});
    elements.push(all);
    if(packet.gold<total)elements.push(make('p',`You need ${(total-packet.gold).toLocaleString()} more gold to repair everything.`));
    container.replaceChildren(...elements);
  }
  function render(kind,npc,packet,container){
    if(kind==='repair')return renderRepair(npc,packet,container);
    const copies=packet.gearInstances||[],worn=equippedIds(packet),preview=packet.gearPreview||{};
    const heading=make('h4',kind==='merge'?'Merge equipment':'Refine equipment');
    const intro=make('p',kind==='merge'?'Choose two spare copies with the same item and rarity. The output keeps the lower rank. Epic and orange copies cannot merge.':'Choose any owned copy, including one you wear. Each rank adds 4% of its rank-zero stats, up to rank 5.');
    const elements=[heading,intro];
    const send=offer=>Online.send({type:'interact',npc:npc.id,offer});
    if(kind==='merge'){
      const available=copies.filter(g=>!worn.has(g.id)&&['common','uncommon','rare'].includes(g.rarity));
      const firsts=available.filter(g=>available.some(other=>other.id!==g.id&&other.item===g.item&&other.rarity===g.rarity));
      if(!firsts.length){elements.push(make('p','You need two matching unequipped copies.'));container.replaceChildren(...elements);return;}
      const first=select(firsts,chosen.mergeA,worn);chosen.mergeA=Number(first.value);
      const seconds=()=>available.filter(g=>g.id!==chosen.mergeA&&g.item===copies.find(x=>x.id===chosen.mergeA)?.item&&g.rarity===copies.find(x=>x.id===chosen.mergeA)?.rarity);
      const second=select(seconds(),chosen.mergeB,worn);chosen.mergeB=Number(second.value);
      first.addEventListener('change',()=>{chosen.mergeA=Number(first.value);chosen.mergeB=null;render(kind,npc,packet,container);});
      second.addEventListener('change',()=>{chosen.mergeB=Number(second.value);render(kind,npc,packet,container);});
      elements.push(make('label','First copy'),first,make('p',stats(copies.find(g=>g.id===chosen.mergeA))));
      elements.push(make('label','Second copy'),second,make('p',stats(copies.find(g=>g.id===chosen.mergeB))));
      const inspect=make('button','Preview merge','btn ghost');inspect.type='button';inspect.addEventListener('click',()=>send(`merge_preview:${chosen.mergeA}:${chosen.mergeB}`));elements.push(inspect);
      if(preview.kind==='merge'&&preview.first===chosen.mergeA&&preview.second===chosen.mergeB){
        elements.push(make('p',`Output: ${preview.result.rarity} · rank ${preview.result.rank} · ${stats(preview.result)}`));
        const confirm=make('button','Confirm merge','btn');confirm.type='button';confirm.addEventListener('click',()=>{confirm.disabled=true;send(`merge_confirm:${chosen.mergeA}:${chosen.mergeB}`);});elements.push(confirm);
      }
    }else{
      if(!copies.length){elements.push(make('p','You do not own any equipment.'));container.replaceChildren(...elements);return;}
      const choice=select(copies,chosen.refine,worn);chosen.refine=Number(choice.value);
      choice.addEventListener('change',()=>{chosen.refine=Number(choice.value);render(kind,npc,packet,container);});
      const current=copies.find(g=>g.id===chosen.refine);
      elements.push(make('label','Equipment copy'),choice,make('p',`Current rank ${current.rank} · ${stats(current)}`));
      const prefer=make('button','Use this copy when equipped','btn ghost');prefer.type='button';prefer.disabled=worn.has(current.id);
      prefer.addEventListener('click',()=>{prefer.disabled=true;send(`prefer_copy:${chosen.refine}`);});elements.push(prefer);
      const inspect=make('button','Preview refinement','btn ghost');inspect.type='button';inspect.disabled=current.rank>=5;
      inspect.addEventListener('click',()=>send(`refine_preview:${chosen.refine}`));elements.push(inspect);
      if(preview.kind==='refine'&&preview.id===chosen.refine){
        const crystal=item(preview.material),owned=(packet.inventory||[]).find(s=>s.item===preview.material)?.quantity||0;
        elements.push(make('p',`Rank ${preview.result.rank}: ${stats(preview.result)}`),
          make('p',`Cost: ${preview.gold} gold and ${preview.crystals} ${crystal?.name||preview.material} (owned: ${owned}).`));
        const confirm=make('button','Confirm refinement','btn');confirm.type='button';
        confirm.disabled=packet.gold<preview.gold||owned<preview.crystals;
        confirm.addEventListener('click',()=>{confirm.disabled=true;send(`refine_confirm:${chosen.refine}`);});elements.push(confirm);
      }
    }
    container.replaceChildren(...elements);
  }
  window.GearServices={render};
})();
