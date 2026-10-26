'use strict';
// Merchant frame and bag sales. Ownership, prices, payment and buy-back are server decisions.
(() => {
  const $ = id => document.getElementById(id);
  const make = (tag, text = '', cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
  const button = (text, action) => { const b = make('button', text, 'btn ghost'); b.type = 'button'; b.addEventListener('click', action); return b; };
  const key = row => `${row.item}:${row.copy || 0}`;
  const price = row => Math.min(4294967295, Math.floor((row.base * row.quantity * (100 + (data?.goldPercent || 0)) + 50) / 100));
  const rarity = row => row.rarity || row.gear?.[0]?.rarity || Inventory.definition(row.item)?.rarity;
  const isJunk = row => row.rarity === 'common' && (!!row.gear || Inventory.definition(row.item)?.kind === 'material');
  let npc = null, container = null, data = null, basket = new Map(), tab = 'merchant', page = 0, packet = null, pending = false, pendingKind = '', timer = 0, snapshotKey = '', warning = null, zone = null, lastNotice = '';
  const bag = document.querySelector('.bag-window'), bagHome = bag.parentElement, bagNext = bag.nextSibling;
  const dock = make('div'); dock.id = 'merchant-bags'; dock.hidden = true; $('npc-dialogue').append(dock);
  const portrait = document.createElement('canvas'); portrait.id = 'merchant-portrait'; portrait.width = portrait.height = 128; portrait.hidden = true; $('npc-name').before(portrait);
  function settle() { clearTimeout(timer); pending = false; }
  function send(message) {
    if (pending || !npc || !Online.send({ ...message, npc: npc.id })) return false;
    pending = true; pendingKind = message.type;
    timer = setTimeout(() => { settle(); if (container) { data = null; draw(); if(npc.buys)request(); else {data={available:[],buyBack:[],gold:packet.gold};draw();} } }, 4000);
    return true;
  }
  function request() { send({ type: 'shop_open' }); }
  function closeWarning() { if (warning) { warning.close(); warning.remove(); warning = null; } }
  function close() {
    closeWarning(); settle(); npc = null; container = null; data = null; packet = null; basket.clear(); snapshotKey = ''; lastNotice = '';
    $('merchant-service')?.remove();
    $('npc-dialogue').classList.remove('merchant-mode'); portrait.hidden = true; $('npc-dialogue').querySelector('.merchant-tabs')?.remove();
    if (bag.parentElement === dock) { Settings.unregisterWindow('merchant-bags'); bagHome.insertBefore(bag, bagNext); } dock.hidden = true;
  }
  function reconcile() {
    const available = new Map((data?.available || []).map(row => [key(row), row]));
    for (const [id, row] of basket) {
      const next = available.get(id);
      if (!next) basket.delete(id);
      else basket.set(id, { ...next, quantity: Math.min(row.quantity, next.quantity) });
    }
  }
  function submit() {
    closeWarning();
    const items = [...basket.values()].map(({ item, copy, quantity }) => ({ item, ...(copy ? { copy } : {}), quantity }));
    if (send({ type: 'sell_batch', items })) draw();
  }
  function confirm() {
    if (pending || !basket.size) return;
    const precious = [...basket.values()].filter(row => ['epic', 'legendary', 'hierloom'].includes(row.rarity));
    if (!precious.length) { submit(); return; }
    closeWarning();
    warning = make('dialog', '', 'sell-warning panel'); warning.id = 'sell-warning';
    warning.setAttribute('aria-labelledby', 'sell-warning-title');
    const title = make('h3', 'Sell valuable items?'); title.id = 'sell-warning-title'; warning.append(title);
    warning.append(make('p', precious.some(row => row.rarity === 'hierloom') ? 'Really sell these valuable items, including Hierlooms?' : 'Really sell these purple or orange items?'));
    const list = make('ul');
    for (const row of precious) {
      const n = make('li', Inventory.definition(row.item)?.name || row.item); n.dataset.rarity = row.rarity; list.append(n);
    }
    const yes = button('Yes, sell', submit), cancel = button('Cancel', () => { closeWarning(); $('sell-junk')?.focus(); });
    yes.id = 'sell-yes'; cancel.id = 'sell-cancel';
    warning.append(list, make('p', `You receive: ${[...basket.values()].reduce((sum, row) => sum + price(row), 0)} gold`), cancel, yes);
    warning.addEventListener('cancel', event => { event.preventDefault(); closeWarning(); $('sell-junk')?.focus(); });
    warning.addEventListener('keydown', event => event.stopPropagation());
    $('stage').append(warning); warning.showModal();
    window.Settings?.registerWindow('sell-warning', null, 'Sell valuable items?', false);
    (precious.some(row => ['legendary', 'hierloom'].includes(row.rarity)) ? cancel : yes).focus();
  }
  function stock() {
    return (npc?.offers || []).filter(o => o.item || o.bag).map(offer => {
      let item = Inventory.definition(offer.item || offer.bag);
      if (offer.tiered && item?.family) item = WORLD_ITEMS.filter(i => i.family === item.family && (i.requiredLevel || 1) <= (packet?.level || 1)).sort((a,b) => b.requiredLevel-a.requiredLevel)[0] || item;
      return {offer,item,cost:offer.tiered ? item?.price : offer.cost};
    }).filter(({item}) => item && (item.kind !== 'weapon' || !item.class || item.class === Field.hero.look.class));
  }
  function utility(label, glyph, action) {
    const b = button('', action); b.className = 'merchant-tool'; b.setAttribute('aria-label', label); b.title = label;
    b.innerHTML = glyph; const text = make('span',label,'sr-only'); b.append(text); return b;
  }
  const anvil = '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M7 13h34v8l-12 6v7h9v6H10v-6h9v-7L7 22z" fill="#b3b4ad" stroke="#493e29" stroke-width="2"/></svg>';
  const pouch = '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="m15 5 9 4 9-4-4 12c20 18 14 27-5 27S-1 35 19 17z" fill="#bb8b34" stroke="#543c1d" stroke-width="2"/><circle cx="24" cy="29" r="7" fill="#f6d45f"/></svg>';
  function draw() {
    if (!container || !npc) return;
    $('merchant-service')?.remove();
    const service = make('small', npc.buys ? 'Buys items' : 'Does not buy items', 'merchant-service');
    service.id = 'merchant-service'; service.dataset.buys = String(!!npc.buys); $('npc-name').append(service);
    closeWarning(); $('npc-dialogue').querySelector('.merchant-tabs')?.remove(); container.replaceChildren(); container.className = 'merchant-workspace'; container.setAttribute('aria-busy', String(pending));
    const status = $('npc-notice');
    if (status.textContent !== lastNotice) status.textContent = lastNotice;
    if (tab === 'repair') {
      const repair = make('div','','merchant-catalog'); GearServices.render('repair', npc, packet, repair); container.append(repair);
    } else {
      const grid = make('div','','merchant-grid'); grid.id = tab === 'back' ? 'sell-buyback' : 'merchant-stock';
      const rows = tab === 'back' ? [...(data?.buyBack || [])].reverse().map(row => ({row,item:Inventory.definition(row.item),cost:row.paid})) : stock();
      const pages = Math.max(1, Math.ceil(rows.length/10)); page = Math.min(page,pages-1);
      for (const entry of rows.slice(page*10,page*10+10)) {
        const {item, cost, row, offer} = entry;
        const b = button('', () => { if (send(row ? {type:'buy_back',id:row.id} : {type:'interact',offer:offer.id})) draw(); });
        b.className = 'merchant-slot'; b.dataset.item = item.id; b.dataset.rarity = row ? rarity(row) : item.rarity;
        if (offer) b.dataset.offer = offer.id;
        const glyph = make('span','','merchant-item-icon'); glyph.innerHTML = Inventory.icon(item, undefined, row?.gear?.find(g => Inventory.conditionState(g) === 'broken'));
        const detail = make('span','','merchant-item-detail'); detail.append(make('b',item.name),make('small',`${cost} gold${row?.quantity > 1 ? ` ×${row.quantity}` : ''}`));
        b.append(glyph, detail); b.disabled = pending || (data?.gold ?? packet.gold) < cost || (!row && (packet.level || 1) < (item.requiredLevel || 1));
        Inventory.attachTooltip(b, () => item, undefined, row ? () => ({copies:row.gear || [],count:row.quantity,in:'Buyback',hint:`${row.paid} gold`}) : undefined);
        grid.append(b);
      }
      while (grid.childElementCount < 10) grid.append(make('div','','merchant-empty'));
      const nav = make('div','','merchant-pages');
      const prev = button('←',()=>{page--;draw();}),next=button('→',()=>{page++;draw();});
      prev.setAttribute('aria-label','Previous page'); next.setAttribute('aria-label','Next page'); prev.disabled=page===0; next.disabled=page>=pages-1;
      nav.append(prev,make('span',`${page+1} / ${pages}`),next); const catalog=make('div','','merchant-catalog');catalog.append(grid,nav);container.append(catalog);
    }
    const tools = make('div','','merchant-tools');
    if ((npc.offers || []).some(o=>o.id==='repair') && packet.repairQuote) {
      const repair = utility('Repair one piece',anvil,()=>{tab='repair';draw();}); repair.dataset.action='repair-one';
      const all = utility('Repair All Items',anvil,()=>{if(send({type:'interact',offer:'repair_all'}))draw();}); all.dataset.action='repair-all';
      const total=packet.repairQuote.reduce((sum,[,cost])=>sum+cost,0); all.title=`Repair All Items · ${total} gold`; all.disabled=pending||!total||packet.gold<total; tools.append(repair,all);
    }
    const junk = utility('Sell all junk',pouch,()=>{
      basket.clear(); for(const row of data?.available || []) {if(isJunk(row))basket.set(key(row),{...row});} confirm();
    }); junk.id='sell-junk'; junk.disabled=pending||!data?.available?.some(isJunk); tools.append(junk);
    const last=(data?.buyBack || []).at(-1), back=utility('Buyback',last?Inventory.icon(Inventory.definition(last.item)):'',()=>{tab='back';page=0;draw();});
    back.id='merchant-last-buyback'; if(last) {back.dataset.item=last.item;Inventory.attachTooltip(back,()=>Inventory.definition(last.item));} tools.append(back);container.append(tools);
    const tabs=make('div','','merchant-tabs');
    for(const [id,label] of [['merchant','Merchant'],['back','Buyback']]){const b=button(label,()=>{tab=id;page=0;draw();});b.dataset.tab=id;b.setAttribute('aria-pressed',String(tab===id));tabs.append(b);}$('npc-dialogue').querySelector('.gossip-footer').append(tabs);
    Inventory.render($('inventory-list'));
  }
  function selectItem(id) {
    if (!npc.buys) { lastNotice='This person does not buy items. Sell to a merchant or smith.'; draw(); return; }
    if (pending || !data) return;
    const row = data.available.find(row=>row.item===id);
    if (!row) { lastNotice='This item cannot be sold.'; draw(); return; }
    basket.clear(); basket.set(key(row),{...row}); confirm();
  }
  function mount() {
    $('npc-dialogue').classList.add('merchant-mode'); dock.hidden=false; dock.append(bag);
    Settings.registerWindow('merchant-bags','.bag-window','Merchant bags',true);
    portrait.hidden=false; const g=portrait.getContext('2d');g.clearRect(0,0,128,128);g.save();g.beginPath();g.arc(64,64,62,0,Math.PI*2);g.clip();g.fillStyle='#263546';g.fillRect(0,0,128,128);City.drawNpc(g,npc,64,City.nameplateTop(npc)+24,0,false,true);g.restore();
    Settings.applyScale();
  }
  for (const type of ['click','contextmenu','dblclick']) $('inventory-list').addEventListener(type,event=>{
    if(!npc)return; const tile=event.target.closest('.item-tile'); if(!tile)return;
    event.preventDefault();event.stopImmediatePropagation(); if(type!=='dblclick')selectItem(tile.closest('[data-item]').dataset.item);
  },true);
  $('npc-inventory').addEventListener('dragover',event=>{if(npc&&event.dataTransfer.types.includes('application/x-valhallasc-item'))event.preventDefault();});
  $('npc-inventory').addEventListener('drop',event=>{if(!npc)return;event.preventDefault();try{const item=JSON.parse(event.dataTransfer.getData('application/x-valhallasc-item'));if(item.from==='bag')selectItem(item.item);}catch(_){}});
  $('bags-close').addEventListener('click',event=>{if(npc){event.stopImmediatePropagation();City.close();}},true);
  window.Shop = {
    render(merchant, target, dialogue) {
      const opening = npc?.id !== merchant.id || container !== target;
      if (opening) { close(); npc=merchant; zone=Field.zone||0; container=target; tab='merchant'; page=0; packet=dialogue; lastNotice=dialogue.notice || ''; mount(); draw(); if(npc.buys)request(); else {data={available:[],buyBack:[],gold:packet.gold};draw();} }
      else { const answered=packet!==dialogue&&pendingKind==='interact'; packet=dialogue; if(dialogue.notice)lastNotice=dialogue.notice; if(answered){settle();if(npc.buys)request();else data={available:[],buyBack:[],gold:packet.gold};} draw(); }
    }, close,
    bagTooltip(id) { const row=data?.available?.find(row=>row.item===id); return npc&&row?{copies:row.gear?[row.gear]:[],count:row.quantity,in:Locale.translate('Your bags'),hint:Locale.translate(`Sell for ${price(row)} gold`)}:undefined; },
    get open() { return !!npc; },
    onPacket(packet) {
      if (!npc || packet.npc !== npc.id) return;
      settle(); closeWarning();
      if (packet.closed) { close(); City.close(); return; }
      data = packet;
      if (packet.notice) lastNotice=packet.notice;
      if (packet.ok && packet.changed) basket.clear();
      reconcile();
      Inventory.updateBags(packet.inventory, packet.equipment, packet.bags, packet.gearInstances);
      window.City?.shopGold(packet.gold); draw();
    },
    onSnapshot(c) {
      if (!npc) return;
      const merchant = City.npcs.find(n => n.id === npc.id);
      if (!c || c.dead || c.sparkTravel || (c.zone || 0) !== zone || !merchant || Math.hypot(c.x - merchant.x, c.y - merchant.y) > 3.2) { close(); City.close(); return; }
      const nextKey = JSON.stringify([c.inventory, c.gearInstances, c.equipment, c.gold, c.rebirthTiers]);
      if (npc.buys && nextKey !== snapshotKey && !pending && !warning) { snapshotKey = nextKey; request(); }
    },
  };
})();
