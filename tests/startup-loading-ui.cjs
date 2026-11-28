// Focused startup regression: real monster art/audio, isolated private character.
const root = require('node:path').resolve(__dirname, '..');
const fs=require('node:fs'), assert=require('node:assert/strict');
const { chromium }=require(root+'/tests/lib/playwright.cjs');
const { requireMemoryLimit, debug, sleep }=require(root+'/tests/lib/touch.cjs');
const { TestWorld }=require(root+'/scripts/testing/driver.cjs');
requireMemoryLimit();
const world=new TestWorld(); world.startLevel=40; world.godMode=true;
// Zone spawns come from the shaped map (the old (32, 32) is void now): zone 2 = Rimeveil, zone 3 = Gloamfen.
const MAP=JSON.parse(fs.readFileSync(root+'/world/map.txt','utf8')),RIME=MAP.zones[1].spawn,FEN=MAP.zones[2].spawn;
// Bifrost Reach (zone 7) has no seam to Rimeveil, so its art must wait until the hero goes there (Rimeveil's seam neighbours, zones 1, 3, 4 and 6, load early).
const SKY=MAP.zones[6].spawn;
assert.ok(!MAP.zones[1].portals.some(p=>(p.seam||p.vault)&&p.to===7),'Bifrost must not be a Rimeveil seam neighbour');
let browser,checks=0;
const check=(v,label)=>{assert.ok(v,label);checks++;};
(async()=>{
  await world.start();await world.connect({bot:'StartupCheck',class:'warrior'});
  await world.debug('StartupCheck',{op:'teleport',zone:2,x:RIME.x,y:RIME.y});
  const look=world.player('StartupCheck').look, token=world.bots.get('StartupCheck').token;
  await world.disconnect('StartupCheck');
  browser=await chromium.launch({headless:true,args:['--autoplay-policy=no-user-gesture-required']});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const requests=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>requests.push(new URL(r.url()).pathname.split('/').at(-1)));
  const candidate=process.env.STARTUP_CANDIDATE||root+'/client';
  for(const file of ['field.js','combat-audio.js']) {
    let source=fs.readFileSync(candidate+'/'+file,'utf8');
    if(file==='field.js' && process.env.MUTATE==='art') source=source.replace('loadBankSprites(); loadChestSprites();','loadBankSprites(); loadChestSprites(); loadVaultSprites();');
    if(file==='field.js' && process.env.MUTATE==='sky'){const before=source;source=source.replace('loadBankSprites(); loadChestSprites();','loadBankSprites(); loadChestSprites(); loadSkySprites();');assert.notEqual(source,before,'MUTATE=sky anchor');}
    if(file==='combat-audio.js' && process.env.MUTATE==='parallel'){const before=source;source=source.replace('if (context === c) await load(c, cues[next++]);','if (context === c) { load(c, cues[next++]); }');assert.notEqual(source,before,'MUTATE=parallel anchor');}
    if(file==='field.js')source=source.replace('const stubOn = () => window.__valhallaTestSprites === true;', 'const stubOn = () => false;');
    await page.route('**/'+file,r=>r.fulfill({body:source,contentType:'text/javascript'}));
  }
  await page.addInitScript(({look,token})=>{
    localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,combatSounds:'recorded',musicVol:0,weatherAudio:0,char:look}));
    const endpoint=new URL('ws',location.href);endpoint.protocol='ws:';
    localStorage.setItem('valhallasc.characters.v1:'+endpoint.href,JSON.stringify({current:token,characters:[{token,look}]}));
    window.__loads={active:0,max:0,decodes:0,idles:0,priorities:[]};
    const realFetch=fetch,recordedBytes=new WeakSet(),demandBytes=new WeakSet();
    window.fetch=async (...args)=>{
      const demand=/at (?:Object\.)?play \(/.test(new Error().stack||'');   // read before the first await: the stack is gone after it
      const response=await realFetch(...args);
      if(String(args[0]).includes('assets/combat/')){
        __loads.priorities.push(args[1]?.priority);
        // A fetch started synchronously inside RecordedCombat.play is an on-demand load, not the background preload.
        const arrayBuffer=response.arrayBuffer.bind(response);
        response.arrayBuffer=async()=>{const data=await arrayBuffer();recordedBytes.add(data);if(demand){demandBytes.add(data);__loads.demand=(__loads.demand||0)+1;}return data;};
      }
      return response;
    };
    const decode=AudioContext.prototype.decodeAudioData;
    AudioContext.prototype.decodeAudioData=async function(data){
      if(!recordedBytes.has(data))return decode.call(this,data);
      __loads.decodes++;
      if(demandBytes.has(data))return decode.call(this,data);
      __loads.active++;__loads.max=Math.max(__loads.max,__loads.active);
      try{return await decode.call(this,data);}finally{__loads.active--;}
    };
    const idle=window.requestIdleCallback;
    window.requestIdleCallback=function(...args){__loads.idles++;return idle.apply(this,args);};
  },{look,token});
  const loginAt=Date.now();
  await page.goto(world.url);await page.locator('#start').click();await require(root+'/tests/lib/guest.cjs').playGuest(page);
  await page.waitForFunction(()=>Online.connected&&Field.zone===2&&!!Field.rimeSprites,null,{timeout:60000});
  // Gloamfen is Rimeveil's seam neighbour in the shaped world: field.js loads a near neighbour's art with its zone context, so it may arrive early.
  // Rimeveil holds a live Empty Seat foe (ember_firelord) drawn from the shared Cathedral bank, so cathedral.txt is expected at login; the dungeon and late-zone banks are not.
  check(!requests.includes('vault.txt')&&!requests.includes('yearwheel.txt'),'unvisited dungeon and late-zone art stays unloaded');
  const atlases=requests.filter(n=>/^(slimes|crags|rime|fen|wyrd|sky|deep|astral|prism|orrery|moonspore|stormglass|sunward|ribbonwild|tanglecrown|worldheart|lapis|frostwake|cairn|yearwheel|moonwell|vault|cathedral)_.*\.png$/.test(n));
  // The shaped Rimeveil also holds Empty Seat and event foes from other banks and borders three seam neighbours, so login pulls about 30 atlas files, not exactly its own four.
  check(!requests.some(n=>/^sky_.*\.png$/.test(n)),'a zone with no seam to Rimeveil (Bifrost) has loaded none of its art');
  check(atlases.filter(n=>n.startsWith('rime_')).length===4&&atlases.length<=40,'Rimeveil login loads its four monster atlases and only a small neighbour/foe set ('+atlases.length+' atlas files)');
  const rimeCount=requests.filter(n=>n==='rime.txt').length;
  await sleep(600);
  check(requests.filter(n=>n==='rime.txt').length===rimeCount,'snapshots reuse the same art request');
  await debug(page,{op:'teleport',zone:3,x:FEN.x,y:FEN.y});
  await page.waitForFunction(()=>Field.zone===3&&!!Field.fenSprites);
  check(requests.filter(n=>/^fen_.*\.png$/.test(n)).length===5,'Gloamfen loads its five monster atlases on arrival');
  const target=await page.evaluate(()=>{const s=Field.slimes.find(s=>!s.dead);return {id:s.id,kind:s.kind};});
  const skyBefore=requests.filter(n=>/^sky_.*\.png$/.test(n)).length;
  check(await page.evaluate(target=>{const canvas=document.createElement('canvas');canvas.width=canvas.height=96;return Field.drawTargetPortrait(target,canvas)&&canvas.getContext('2d').getImageData(0,0,96,96).data.some((v,i)=>i%4===3&&v>0);},target), 'Gloamfen enemy portrait draws real pixels');
  await debug(page,{op:'teleport',zone:2,x:RIME.x,y:RIME.y});
  await page.waitForFunction(()=>Field.zone===2);
  check(requests.filter(n=>n==='rime.txt').length===rimeCount,'returning to Rimeveil reuses loaded art');
  await sleep(600);
  const cathBase=requests.filter(n=>/^cathedral_.*\.png$/.test(n)).length;
  await debug(page,{op:'spawn_enemy',kind:'tidetemplar',x:RIME.x+4,y:RIME.y,level:15});
  await page.waitForFunction(()=>!!Field.cathedralSprites?.img.tidetemplar);
  check(requests.filter(n=>/^cathedral_.*\.png$/.test(n)).length===cathBase+1,'encountering a shared-bank monster loads only its own shared-bank image');
  await debug(page,{op:'spawn_enemy',kind:'reliccrab',x:RIME.x+4,y:RIME.y+4,level:15});
  await page.waitForFunction(()=>!!Field.cathedralSprites?.img.reliccrab);
  check(requests.filter(n=>/^cathedral_.*\.png$/.test(n)).length===cathBase+2,'another shared-bank monster extends the bank without fetching unrelated monsters');
  await debug(page,{op:'teleport',zone:7,x:SKY.x,y:SKY.y});
  await page.waitForFunction(()=>Field.zone===7&&!!Field.skySprites,null,{timeout:60000});
  check(skyBefore===0&&requests.filter(n=>/^sky_.*\.png$/.test(n)).length>0,'Bifrost art loads only once the hero arrives there');
  await debug(page,{op:'teleport',zone:2,x:RIME.x,y:RIME.y});
  const preloadBudgetMs=+(process.env.PRELOAD_BUDGET_MS||90000);   // counted from the start of login
  await page.waitForFunction(()=>RecordedCombat.ready,null,{timeout:Math.max(1000,preloadBudgetMs-(Date.now()-loginAt))}); // idle-yielding preload: 40 s on the 8-vCPU box, so 90 s by default (PRELOAD_BUDGET_MS for a slower host)
  const preloadMs=Date.now()-loginAt;
  const loads=await page.evaluate(()=>__loads);
  check(loads.decodes===68,'all 68 recorded sounds still decode');
  check(loads.idles>=68&&loads.priorities.every(p=>p==='low'),'background sounds yield and use low network priority');
  // The preload itself is sequential; a combat sound that is missing is also loaded on demand (play()), and the guards and enemies around the Rimeveil spawn fight constantly, so a few on-demand decodes may overlap it; a parallel preload would overlap dozens.
  check(loads.max===1,'preloading is sequential, not parallel (max overlapping preload decodes '+loads.max+'; '+(loads.demand||0)+' on-demand loads excluded)');
  check(errors.length===0,'no browser errors: '+errors.join('; '));
  console.log(JSON.stringify({checks,preloadMs,initialMonsterAtlases:atlases.length,recordedLoads:loads,runDir:world.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();await world.stop();});
