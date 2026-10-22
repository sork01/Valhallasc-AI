// Cloaks only: real compositor, five shapes, ten rigs, every facing and animation.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'test-results/cloaks');fs.mkdirSync(out,{recursive:true});
const stems={warrior:'warrior_layered',mage:'mage',assassin:'assassin',priest:'priest',hunter:'hunter'};
const styles=['travel','hooded','mantle','clasp','ember'];
const html=fs.readFileSync(path.join(root,'client/index.html'),'utf8');
const panel=html.slice(html.indexOf('<section class="rpg-window character-window"'),html.indexOf('<section class="rpg-window bag-window"'));
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost');
 if(u.pathname==='/'){
  res.setHeader('Content-Type','text/html');return res.end(`<!doctype html><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="online.css"><style>body{margin:0;background:#293d45;color:#f2d79b}#fixture{container-type:inline-size;width:100vw}#evidence{display:block}</style><div id="fixture"><div class="equipment-workspace">${panel}</div></div><canvas id="evidence" width="1440" height="740"></canvas><script>window.Online={connected:true,saveBagLayout(){},send(v){window.sent=v;return true;}};window.Field={hero:{level:99},equipSlot(slot,item){window.sent={slot,item};}};</script><script src="items.js"></script><script src="itemicons.js"></script><script src="setbonuses.js"></script><script src="magesprite.js"></script><script src="warriorsprite.js"></script><script src="assassinsprite.js"></script><script src="priestsprite.js"></script><script src="huntersprite.js"></script><script src="mountart.js"></script><script src="inventory.js"></script>`);
 }
 const match=u.pathname.match(/^\/preview-(warrior|mage|assassin|priest|hunter)-(male|female)\.txt$/);
 if(match){
  const [,cls,gender]=match,meta=JSON.parse(fs.readFileSync(path.join(root,'client/assets',stems[cls]+(gender==='female'?'_f':'')+'_sprites.txt')));
  meta.parts=Object.fromEntries(Object.entries(meta.parts).filter(([key])=>key==='body'||key.startsWith('cloak_')||key==='armor_regearl95'||/^(armor|weapon)_/.test(key)&&!key.includes('regear')&&!key.includes('l20')&&!key.includes('gm')));
  meta.lazyParts=Object.keys(meta.parts).filter(key=>key!=='body');
  if(process.argv.includes('--mutation-missing'))for(const style of styles)delete meta.parts['cloak_'+style];
  res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(meta));
 }
 const file=path.resolve(root,'client','.'+decodeURIComponent(u.pathname));
 if(!file.startsWith(path.join(root,'client')+path.sep)||!fs.existsSync(file)){res.writeHead(404);return res.end();}
 res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.png')?'image/png':'text/plain');fs.createReadStream(file).pipe(res);
});
(async()=>{
 let browser;const evidence=[];let checks=0;
 try{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));browser=await chromium.launch({headless:true});
  for(const cls of Object.keys(stems))for(const gender of ['male','female']){
   const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto('http://127.0.0.1:'+server.address().port);
   const result=await page.evaluate(async({cls,gender,styles})=>{
    if(window.__valhallaTestSprites)throw Error('real sprites required');
    const Base={warrior:WarriorSprite,mage:MageSprite,assassin:AssassinSprite,priest:PriestSprite,hunter:HunterSprite}[cls];
    const C=gender==='female'?Base.Female:Base;C.METADATA=`preview-${cls}-${gender}.txt`;
    const armor=Object.keys(C.ARMOR).find(k=>k!=='none'),weapon=Object.keys(C.WEAPON).find(k=>k!=='none');
    const bare={class:cls,gender,skin:0,hairColor:0,[cls+'Armor']:armor,[cls+'Weapon']:weapon,head:'none',shoulders:'none',gloves:'none',pants:'none',necklace:'none',accessory:'none',cloak:'none'};
    const sprite=await C.load(bare);window.cloakSprite=sprite;
    const set=async look=>{sprite.set(look);await Promise.all(Object.entries(sprite.equipment).filter(([,v])=>v&&v!=='none').map(([slot,v])=>sprite.source.ensure(slot+'_'+v)));sprite.cache.clear();};
    await set(bare);
    const baseline={};
    for(const [clip,M] of Object.entries(sprite.meta.clips))for(let dir=0;dir<8;dir++)for(let k=0;k<M.n;k++)baseline[`${clip}/${dir}/${k}`]=sprite.frame(clip,dir,k)._px.slice();
    const delta=(a,b)=>{let n=0;for(let p=0;p<a.length;p+=4)if(a[p]!==b[p]||a[p+1]!==b[p+1]||a[p+2]!==b[p+2]||a[p+3]!==b[p+3])n++;return n;};
    const report=[];let count=0;
    const canvas=document.getElementById('evidence'),g=canvas.getContext('2d');g.fillStyle='#293d45';g.fillRect(0,0,canvas.width,canvas.height);g.font='18px sans-serif';g.fillStyle='#f2d79b';g.fillText(`${cls} ${gender}: cloak silhouettes and movement`,20,25);g.imageSmoothingEnabled=false;
    for(const [si,style] of styles.entries()){
     const item=WORLD_ITEMS.find(i=>i.kind==='cloak'&&i.art===style&&!i.source&&i.rarity==='rare');
     await set({...bare,cloak:item.variant});
     if(sprite.equipment.cloak!==style)throw Error('cloak did not resolve '+item.id);
     let minimum=1e9;const walkHashes=new Set();
     for(const [clip,M] of Object.entries(sprite.meta.clips))for(let dir=0;dir<8;dir++)for(let k=0;k<M.n;k++){
      const key=`${clip}/${dir}/${k}`,frame=sprite.frame(clip,dir,k),changed=delta(frame._px,baseline[key]);minimum=Math.min(minimum,changed);
      const f=sprite.source.parts['cloak_'+style]?.[key];if(!f||f.pixels.length<20)throw Error(`missing cloak cel ${style}/${key}`);
      if(!changed)throw Error(`invisible equipped cloak ${cls}/${gender}/${style}/${key}`);
      if(clip==='walk'&&dir===1){let h=0;for(const v of f.pixels)h=(h*31+v)>>>0;walkHashes.add(h+'/'+f.x+'/'+f.y);}
      count++;
     }
     if(walkHashes.size<6)throw Error('cloth has frozen walk frames '+style);
     report.push({cls,gender,style,minimumVisiblePixels:minimum,distinctWalkFrames:walkHashes.size});
     for(const [col,[clip,dir,k]] of [['idle',0,0],['idle',4,0],['walk',1,1],['walk',1,5],['attack',6,4],['die',3,7]].entries()){
      g.drawImage(sprite.frame(clip,dir,k),col*230,32+si*120,176,176);g.fillText(style,180+col*230,75+si*120);
     }
     // The later armours have their own built-in drapes: the cloak must still read on top of them.
     const late=WORLD_ITEMS.find(i=>i.class===cls&&i.kind==='armor'&&!i.source&&i.rarity==='rare'&&i.requiredLevel===95);
     for(const variant of [Object.keys(C.ARMOR).filter(k=>k!=='none')[1],late.variant]){
      await set({...bare,[cls+'Armor']:variant,cloak:'none'});
      const before=Array.from({length:8},(_,dir)=>sprite.frame('walk',dir,2)._px.slice());
      await set({...bare,[cls+'Armor']:variant,cloak:item.variant});
      for(let dir=0;dir<8;dir++){if(delta(before[dir],sprite.frame('walk',dir,2)._px)<8)throw Error(`cloak hidden by armour ${cls}/${gender}/${style}/${variant}/${dir}`);count++;}
     }
     await set({...bare,cloak:item.variant});
     // A recolour changes pixels while it retains the same construction.
     const other=WORLD_ITEMS.find(i=>i.kind==='cloak'&&i.art===style&&!i.source&&i.rarity==='uncommon');
     const blue=sprite.frame('idle',4,0)._px.slice();await set({...bare,cloak:other.variant});if(!delta(blue,sprite.frame('idle',4,0)._px))throw Error('rarity did not recolour '+style);
     await set(bare);if(delta(baseline['idle/4/0'],sprite.frame('idle',4,0)._px))throw Error('unequip left cloak pixels');
    }
    // Mounted cloth breathes with the rider while the horse runs, rather than being frozen at frame zero.
    MountArt.preload('horse');for(let n=0;n<200&&!MountArt.ready('horse');n++)await new Promise(r=>setTimeout(r,25));
    if(!MountArt.ready('horse'))throw Error('real mount art missing');
    const top=WORLD_ITEMS.find(i=>i.id==='orange_cloak_10');await set({...bare,cloak:top.variant});
    const output=document.createElement('canvas');output.width=output.height=500;const ctx=output.getContext('2d',{willReadFrequently:true});
    const draw=walk=>{ctx.clearRect(0,0,500,500);ctx.save();ctx.translate(250,350);sprite.draw(ctx,{mounted:true,mount:'horse',moving:true,walk,fx:-1,fy:-1},0,1.3);ctx.restore();return ctx.getImageData(0,0,500,500).data;};
    const mounted=draw(0);if(!delta(mounted,draw(8)))throw Error('mounted cloak frozen while the same horse frame repeats');
    await set(bare);if(delta(draw(0),draw(8)))throw Error('mount comparison must keep the same horse/body pose');
    await set({...bare,cloak:top.variant});
    window.cloakLook={...bare,cloak:top.variant};
    Inventory.update([{item:top.id,quantity:1}],window.cloakLook,{cloak:top.id});Inventory.renderEquipped(document.getElementById('equipped-slots'));
    return {report,count};
   },{cls,gender,styles});
   checks+=result.count;evidence.push(...result.report);assert.deepEqual(errors,[]);
   await page.locator('#evidence').screenshot({path:path.join(out,`${cls}-${gender}-equipped.png`)});
   if(cls==='warrior'&&gender==='male')for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
    await page.setViewportSize(viewport);const layout=await page.evaluate(()=>{const cards=[...document.querySelectorAll('.equipped-slot')];const rect=e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};return {cards:cards.map(e=>({slot:e.dataset.slot,...rect(e)})),paper:rect(document.querySelector('.paper-doll')),icons:[...document.querySelectorAll('[data-slot="cloak"] .item-art')].length};});
    assert.equal(layout.cards.length,10);assert.equal(layout.icons,1);
    for(const card of layout.cards){assert.ok(card.x>=layout.paper.x-1&&card.right<=layout.paper.right+1&&card.y>=layout.paper.y-1&&card.bottom<=layout.paper.bottom+1,`${viewport.width}: clipped ${card.slot}`);}
    for(let i=0;i<10;i++)for(let j=i+1;j<10;j++){const a=layout.cards[i],b=layout.cards[j];assert.ok(a.right<=b.x+1||b.right<=a.x+1||a.bottom<=b.y+1||b.bottom<=a.y+1,`overlap ${a.slot}/${b.slot}`);}
    await page.locator('.character-window').screenshot({path:path.join(out,`equipment-${viewport.width}.png`)});
   }
   console.log(cls,gender,result.count,'pose checks');await page.close();
  }
  fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({checks,evidence},null,2));console.log('PASS',checks,'real equipped cloak poses; ten slots fit desktop and mobile');
 }finally{await browser?.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
