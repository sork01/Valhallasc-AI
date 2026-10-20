// Black Hour Foundry only: actual equipped compositor, ten rigs, all eight slots; guard against recolours.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'test-results/blackhour-redesign');fs.mkdirSync(out,{recursive:true});
const stems={warrior:'warrior_layered',mage:'mage',assassin:'assassin',priest:'priest',hunter:'hunter'};
const items=JSON.parse(fs.readFileSync(path.join(root,'world/items.txt'))).filter(i=>i.source==='blackhour');
assert.equal(items.length,28);assert.ok(items.every(i=>i.art==='regearnull'&&!i.tint));
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost');
 if(u.pathname==='/'){res.setHeader('Content-Type','text/html');return res.end('<!doctype html><style>body{background:#23352f;color:#f2d79b;font-family:sans-serif}canvas{display:block}</style><script src="items.js"></script><script src="magesprite.js"></script><script src="warriorsprite.js"></script><script src="assassinsprite.js"></script><script src="priestsprite.js"></script><script src="huntersprite.js"></script>');}
 const match=u.pathname.match(/^\/preview-(warrior|mage|assassin|priest|hunter)-(male|female)\.txt$/);
 if(match){
  const [,cls,gender]=match,meta=JSON.parse(fs.readFileSync(path.join(root,'client/assets',stems[cls]+(gender==='female'?'_f':'')+'_sprites.txt')));
  const selected=items.filter(i=>!i.class||i.class===cls),needed=new Set(['body']);
  for(const i of selected){const slot=i.kind==='headgear'?'head':i.kind;needed.add(slot+'_regearnull');needed.add(slot+'_'+i.variant.split('_l')[0]);}
  meta.parts=Object.fromEntries(Object.entries(meta.parts).filter(([k])=>needed.has(k)));
  // Fail the shape guard if a future export accidentally reuses the original silhouettes.
  if(process.argv.includes('--mutation-original'))for(const i of selected){const slot=i.kind==='headgear'?'head':i.kind;meta.parts[slot+'_regearnull']=meta.parts[slot+'_'+i.variant.split('_l')[0]];}
  res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(meta));
 }
 const file=path.resolve(root,'client','.'+decodeURIComponent(u.pathname));
 if(!file.startsWith(path.join(root,'client')+path.sep)||!fs.existsSync(file)){res.writeHead(404);return res.end();}
 res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.png')?'image/png':'text/plain');fs.createReadStream(file).pipe(res);
});
(async()=>{
 let browser;const evidence=[];
 try{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));browser=await chromium.launch({headless:true});
  for(const cls of Object.keys(stems)){
   const page=await browser.newPage({viewport:{width:1200,height:560}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto('http://127.0.0.1:'+server.address().port);
   const results=await page.evaluate(async({cls,items})=>{
    const Base={warrior:WarriorSprite,mage:MageSprite,assassin:AssassinSprite,priest:PriestSprite,hunter:HunterSprite}[cls];
    const selected=items.filter(i=>!i.class||i.class===cls),values=[];
    const canvas=document.createElement('canvas');canvas.width=1120;canvas.height=520;document.body.appendChild(canvas);const g=canvas.getContext('2d');g.fillStyle='#23352f';g.fillRect(0,0,1120,520);g.font='18px sans-serif';g.fillStyle='#f2d79b';g.fillText('Nullforged Black Hour Foundry — '+cls,20,28);
    const hash=frame=>{let h=0;for(const v of frame._px)h=(h*31+v)>>>0;return h;};
    for(const [row,gender] of ['male','female'].entries()){
     const C=gender==='female'?Base.Female:Base;C.METADATA=`preview-${cls}-${gender}.txt`;
     const bare={class:cls,gender,skin:0,hair:0,[cls+'Armor']:'none',[cls+'Weapon']:'none',head:'none',shoulders:'none',gloves:'none',pants:'none',necklace:'none',accessory:'none'};
     const sprite=await C.load(bare);
     const set=async look=>{sprite.set(look);await Promise.all(Object.entries(sprite.equipment).filter(([,a])=>a&&a!=='none').map(([s,a])=>sprite.source.ensure(s+'_'+a)));sprite.cache.clear();};
     const naked=hash(sprite.frame('idle',0,0));
     const mask=part=>{const f=sprite.source.parts[part]?.['idle/0/0'];if(!f)throw Error('missing layer '+part);const a=new Uint8Array(160*160);for(let y=0;y<f.h;y++)for(let x=0;x<f.w;x++)a[(f.y+y)*160+f.x+x]=f.pixels[(y*f.w+x)*4+3];return a;};
     for(const item of selected){
      const slot=item.kind==='headgear'?'head':item.kind,key=slot==='armor'?cls+'Armor':slot==='weapon'?cls+'Weapon':slot;
      await set({...bare,[key]:item.variant});if(sprite.equipment[slot]!=='regearnull')throw Error('catalogue did not resolve original art '+item.id);
      const newMask=mask(slot+'_regearnull'),visible=hash(sprite.frame('idle',0,0));if(visible===naked)throw Error('equipping invisible '+item.id);
      await sprite.source.ensure(slot+'_'+item.variant.split('_l')[0]);
      const oldMask=mask(slot+'_'+item.variant.split('_l')[0]),delta=newMask.filter((a,i)=>a!==oldMask[i]).length;
      if(delta<6)throw Error('recolour / unchanged silhouette '+item.id+' '+gender+' delta='+delta);
      const colours=part=>{const p=sprite.source.parts[part]['idle/0/0'].pixels,seen=new Set();for(let k=0;k<p.length;k+=4)if(p[k+3])seen.add(p[k]+','+p[k+1]+','+p[k+2]);return seen;};
      const oldColours=colours(slot+'_'+item.variant.split('_l')[0]),newColours=colours(slot+'_regearnull');
      const originalColours=[...newColours].filter(c=>!oldColours.has(c)).length;
      if(originalColours<2)throw Error('equipment lacks its own palette '+item.id+' '+gender);
      values.push({cls,gender,item:item.id,slot,changedMaskPixels:delta,originalColours});
     }
     const full={...bare};for(const item of selected){const slot=item.kind==='headgear'?'head':item.kind;full[slot==='armor'?cls+'Armor':slot==='weapon'?cls+'Weapon':slot]=item.variant;}
     await set(full);
     for(const clip of ['idle','walk','attack','hurt','die'])for(let dir=0;dir<8;dir++){
      const frame=sprite.frame(clip,dir,Math.min(3,sprite.meta.clips[clip].n-1));if(!frame._px.some((v,i)=>i%4===3&&v))throw Error('blank equipped frame');
     }
     g.fillText(gender,20,65+row*225);
     const poses=[['idle',0,0],['idle',4,0],['walk',1,2],['attack',0,4],['die',0,7]];
     for(const [col,[clip,dir,k]]of poses.entries()){
      g.imageSmoothingEnabled=false;g.drawImage(sprite.frame(clip,dir,k),90+col*200,42+row*225,208,208);g.fillText(clip,135+col*200,253+row*225);
     }
    }
    return values;
   },{cls,items});
   evidence.push(...results);assert.equal(results.length,16);assert.deepEqual(errors,[]);
   await page.locator('canvas').screenshot({path:path.join(out,`blackhour-${cls}-equipped.png`)});await page.close();console.log(cls+': 16 visible, newly shaped pieces; all facings/clips composite');
  }
  fs.writeFileSync(path.join(out,'gear-browser.json'),JSON.stringify({passed:true,pieces:28,fittedLayers:80,evidence},null,2));console.log('PASS: all 28 pieces, 80 fitted layers, ten rigs');
 }finally{if(browser)await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
