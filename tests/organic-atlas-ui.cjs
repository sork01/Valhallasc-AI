// The owner's organic world reference, city containment and walking boundaries only.
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const {requireMemoryLimit}=require('./lib/touch.cjs');requireMemoryLimit();
const {chromium}=require('./lib/playwright.cjs');const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..');
(async()=>{
 const world=new TestWorld();world.startLevel=99;let browser,checks=0;
 const check=(v,m)=>{assert.ok(v,m);checks++;};
 try {
  await world.start();
  for(const [width,height,touch] of [[1280,800,false],[844,390,true],[1024,768,true]]) {
   console.log(`organic atlas ${width}x${height}`);browser=await chromium.launch({headless:true});
   const page=await browser.newPage({viewport:{width,height},isMobile:touch,hasTouch:touch,reducedMotion:'reduce'});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{window.__valhallaTestSprites=true;window.AudioContext=undefined;window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null}));});
   if(process.env.MUTATE) {
    const source=fs.readFileSync(path.join(root,'client/worldmap.js'),'utf8');let changed=source;
    if(process.env.MUTATE==='entrance')changed=source.replace("renderZone(p.to);setView('zone');$('wm-back').focus();","renderZone(parent);setView('zone');$('wm-back').focus();");
    if(process.env.MUTATE==='layout')changed=source.replace('for (const r of ATLAS.regions) {',"for (const r of ATLAS.regions) { if(r.zone===0){const [x,y,w,h]=r.box;r.polygon=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]];}");
    assert.notEqual(changed,source,'mutation target exists');await page.route('**/worldmap.js',r=>r.fulfill({contentType:'text/javascript',body:changed}));
   }
   await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('OrganicAtlas');await page.locator('#go').click({timeout:60000});
   await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
   if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
   const debug=c=>page.evaluate(c=>Online.send({type:'debug',command:c}),c);
   await page.evaluate(()=>WorldMap.show());
   check(await page.locator('.wm-tile').count()===23,'23 organic provinces; Asterion has no separate territory');
   check(await page.locator('.wm-entrance:visible').count()===0,'Undiscovered dungeon entrances remain hidden');
   await page.locator('#wm-close').click();
   await debug({op:'teleport',zone:9,x:84,y:34});await page.waitForFunction(()=>Field.zone===9&&Field.explored?.[9]>0);
   await page.evaluate(()=>WorldMap.show());await page.locator('.wm-entrance[data-to="10"]').click();
   check(await page.evaluate(()=>WorldMap.view==='zone'&&WorldMap.zone===10&&!(Field.explored?.[10])),'Known entrance previews the right unvisited dungeon');
   check(await page.evaluate(()=>!document.querySelector('.wm-person-button,.wm-kind')&&document.querySelector('#wm-fog').getContext('2d').getImageData(384,384,1,1).data[3]>0),'Dungeon preview preserves fog and hides unknown people/enemies');
   await page.locator('#wm-close').click();await debug({op:'explore_all'});await page.waitForFunction(()=>Field.explored?.[46]===511);
   await page.evaluate(()=>WorldMap.show());await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>document.querySelector('.wm-sea')?.hidden===false);
   const audit=await page.evaluate(async()=>{
    const a=WORLD_MAP.atlas,stage=document.querySelector('#wm-world'),errors=[],g=stage.querySelector('.wm-sea').getContext('2d');
    const inside=(poly,x,y)=>{let hit=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const p=poly[i],q=poly[j];if((p[1]>y)!==(q[1]>y)&&x<(q[0]-p[0])*(y-p[1])/(q[1]-p[1])+p[0])hit=!hit;}return hit;};
    for(const r of a.regions) {
     if(r.polygon.length<=8)errors.push('rectangular province '+r.zone);
     if(!document.querySelector(`.wm-name[data-zone="${r.zone}"]`)?.textContent.includes(r.name.replace(/^The /,'')))errors.push('missing printed name '+r.zone);
     const colors=new Set(),[x,y,w,h]=r.box;
     for(let yy=y+5;yy<y+h;yy+=13)for(let xx=x+5;xx<x+w;xx+=13)if(inside(r.polygon,xx,yy)){const p=g.getImageData(xx,yy,1,1).data;colors.add(`${p[0]>>4},${p[1]>>4},${p[2]>>4}`);}
     if(colors.size<5)errors.push('missing terrain detail '+r.zone);
    }
    for(const c of a.cities) {
     const parent=a.regions.find(r=>r.zone===c.parent);
     if(!inside(parent.polygon,...c.at))errors.push('city outside parent '+c.zone);
     const b=document.querySelector(`.wm-city[data-zone="${c.zone}"]`).getBoundingClientRect();if(b.width<43||b.height<43)errors.push('small city '+c.zone);
    }
    const buttons=[...stage.querySelectorAll('.wm-entrance')],labels=[...stage.querySelectorAll('.wm-name,.wm-city')];
    for(const b of buttons) {
     const box=b.getBoundingClientRect(),size=touch=>touch?44:32;
     if(box.width<size(matchMedia('(pointer:coarse)').matches)-1||box.height<size(matchMedia('(pointer:coarse)').matches)-1)errors.push('small entrance '+b.dataset.to);
     for(const c of buttons)if(b!==c&&+b.dataset.to<+c.dataset.to){const r=c.getBoundingClientRect();if(Math.min(box.right,r.right)-Math.max(box.left,r.left)>2&&Math.min(box.bottom,r.bottom)-Math.max(box.top,r.top)>2)errors.push('overlapping entrances '+b.dataset.to+','+c.dataset.to);}
     for(const label of labels){const r=label.getBoundingClientRect();if(Math.min(box.right,r.right)-Math.max(box.left,r.left)>2&&Math.min(box.bottom,r.bottom)-Math.max(box.top,r.top)>2)errors.push('entrance covers label '+b.dataset.to+','+label.dataset.zone);}
    }
    if(a.background!=='assets/world-atlas-painted.png')errors.push('supplied painted artwork is missing');
    const art=new Image();art.src=a.background;await art.decode();
    const expected=document.createElement('canvas');expected.width=a.width;expected.height=a.height;const eg=expected.getContext('2d');eg.drawImage(art,0,0,a.width,a.height);
    for(const [x,y] of [[50,50],[350,300],[1750,550]])if([...g.getImageData(x,y,1,1).data].join()!==[...eg.getImageData(x,y,1,1).data].join())errors.push('painted background changed at '+x+','+y);
    expected.width=expected.height=0;
    const frame=document.querySelector('.wm-panel').getBoundingClientRect(),sr=stage.getBoundingClientRect();
    return{errors,roads:stage.querySelectorAll('[data-road]').length,entrances:buttons.length,cities:stage.querySelectorAll('.wm-city').length,ratio:sr.width/sr.height,fit:frame.left>=-1&&frame.top>=-1&&frame.right<=innerWidth+1&&frame.bottom<=innerHeight+1};
   });
   check(audit.errors.length===0,`${width}x${height}: organic terrain, printed names and separated controls: ${audit.errors.join('; ')}`);
   check(audit.roads===47&&audit.entrances===22&&audit.cities===2,'All outdoor borders, interior doors and nested cities are represented');
   check(audit.fit&&Math.abs(audit.ratio-2048/1041)<.01,'The landscape atlas fits its window with the reference proportions');
   for(const c of [17,23]){await page.locator(`.wm-city[data-zone="${c}"]`).click();check(await page.evaluate(c=>WorldMap.view==='zone'&&WorldMap.zone===c,c),`City ${c} opens its own detailed map`);await page.locator('#wm-back').click();}
   for(const to of await page.locator('.wm-entrance').evaluateAll(bs=>bs.map(b=>+b.dataset.to))){await page.locator(`.wm-entrance[data-to="${to}"]`).click();check(await page.evaluate(to=>WorldMap.zone===to&&WorldMap.view==='zone',to),`Entrance ${to} opens the matching interior`);await page.locator('#wm-back').click();}
   await page.locator('.wm-name[data-zone="19"]').click();check(await page.locator('.wm-path-gate').count()>0,'Detailed outdoor routes are walking-path markers');await page.locator('#wm-back').click();
   await page.locator('#wm-close').click();await debug({op:'teleport',zone:17,x:90,y:114});await page.waitForFunction(()=>Field.zone===17);await page.evaluate(()=>WorldMap.show());
   check(await page.evaluate(()=>document.querySelector('.wm-tile[data-zone="19"]').dataset.here==='true'&&document.querySelector('.wm-city[data-zone="17"]').dataset.here==='true'),'Asterion highlights its own city within Stormglass');
   await page.locator('.wm-city[data-zone="17"]').focus();await page.keyboard.press('Enter');check(await page.evaluate(()=>WorldMap.zone===17),'Keyboard opens the city map');await page.keyboard.press('Escape');check(await page.evaluate(()=>WorldMap.view==='world'),'Escape returns to the organic atlas');
   await page.screenshot({path:path.join(world.runDir,`organic-${width}x${height}.png`)});
   if(!touch){
    await page.locator('#wm-close').click();
    for(const [from,to] of [[0,1],[1,0],[6,7],[7,6],[17,19],[19,17],[23,25],[25,23]]) {
     const p=await page.evaluate(([from,to])=>[WORLD_MAP,...WORLD_MAP.zones][from].portals.find(p=>p.to===to),[from,to]);assert.ok(p?.walk,'walking route exists');
     await page.evaluate(()=>{Field.clearInput();Online.send({type:'stop'});});await debug({op:'teleport',zone:from,x:p.x-p.walk[0]*6,y:p.y-p.walk[1]*6});
     await page.waitForFunction(from=>Field.zone===from,from);await page.waitForTimeout(1300);
     await page.evaluate(p=>Field.setTouchDirection(p.walk[0]-p.walk[1],p.walk[0]+p.walk[1]),p);
     await page.waitForFunction(to=>Field.zone===to,to,{timeout:20000});const before=await page.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));await page.waitForTimeout(400);
     const after=await page.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));await page.evaluate(()=>{Field.clearInput();Online.send({type:'stop'});});
     check((after.x-before.x)*p.walk[0]+(after.y-before.y)*p.walk[1]>.3,`Held movement continues through actual path ${from}->${to}`);
    }
   }
   check(errors.length===0,`No browser errors: ${errors.join('; ')}`);await browser.close();browser=null;
  }
  console.log(`organic-atlas-ui: ${checks} checks passed; artifacts: ${world.runDir}`);
 }finally{await browser?.close();await world.stop();}
})().catch(e=>{console.error(e);process.exitCode=1});
