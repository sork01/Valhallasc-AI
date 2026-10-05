// Private browser checks: three real entries, architecture, animated art, boss bars, maps and wing music.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'cathedral-ui',version:'1.0.0'});
let browser, world, checks=0;
const check=(v,label)=>{assert.ok(v,label);checks++;};
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  world=await call('start_world',{startLevel:50,levelSpread:0});
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,char:null,draft:null})));
  await page.goto(world.url);
  await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();
  await page.locator('#name').fill('CathedralUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&Field.warriorSprites&&Field.cathedralSprites,null,{timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:1,command}),command);
  const stage=async(zone,x,y)=>{
    await page.evaluate(()=>{City.close();Quests.close();WorldMap.close();});
    await debug({op:'teleport',zone,x,y});
    await page.waitForFunction(([zone,x,y])=>Field.zone===zone&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<1,[zone,x,y],{timeout:12000});
    await page.waitForTimeout(700);
  };
  const click=async(x,y)=>{
    const [sx,sy]=await page.evaluate(([x,y])=>Field._debug.w2s(x,y),[x,y]);const box=await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x+sx/1600*box.width,box.y+sy/900*box.height);
  };
  const shot=async name=>page.screenshot({path:path.join(world.artifacts,name+'.png')});
  const zones=await page.evaluate(()=>WORLD_MAP.zones.slice(9));
  check(zones.length===3&&zones.map(z=>z.min_level).join()==='40,45,50','Three Cathedral wings at levels 40/45/50');
  check(await page.evaluate(()=>new Set(CATHEDRAL_ENEMIES.filter(e=>e.boss).map(e=>e.name)).size===12),'Twelve unique named bosses');
  check(new Set(zones.map(z=>JSON.stringify(z.rooms))).size===3,'All three floor plans differ');
  const art=await page.evaluate(()=>{
    const zs=WORLD_MAP.zones.slice(9), kinds=[...new Set(zs.flatMap(z=>z.objects.map(o=>o.kind)).filter(k=>k!=='void'))];
    return kinds.map(kind=>{
      const o=zs.flatMap(z=>z.objects).find(o=>o.kind===kind),def=City.art[kind];
      if(!def)return {kind,missing:true};
      const [w,h,x,y]=def.box,c=document.createElement('canvas');c.width=w;c.height=h;
      const g=c.getContext('2d');g.translate(x,y);def.draw(g,o);const px=g.getImageData(0,0,w,h).data;
      let count=0,edge=0;for(let j=0;j<h;j++)for(let i=0;i<w;i++)if(px[(j*w+i)*4+3]){count++;if(i<2||j<2||i>w-3||j>h-3)edge++;}
      return {kind,count,edge};
    });
  });
  for(const a of art)check(!a.missing&&a.count>100&&a.edge===0,`${a.kind}: visible architecture fits its raster`);
  const frames=await page.evaluate(()=>{
    const src=Field.cathedralSprites, meta=src.meta;
    return CATHEDRAL_ENEMIES.map(e=>{
      const im=src.img[e.kind], c=document.createElement('canvas');c.width=im.width;c.height=im.height;const g=c.getContext('2d');g.drawImage(im,0,0);
      const signatures=[];let border=0,visible=true;
      for(const clip of Object.values(meta.clips))for(let n=0;n<clip.n;n++){
        const d=g.getImageData(n*meta.frame[0],clip.row*meta.frame[1],...meta.frame).data;let pixels=0,hash=2166136261;
        for(let y=0;y<meta.frame[1];y++)for(let x=0;x<meta.frame[0];x++){
          const i=(y*meta.frame[0]+x)*4;if(d[i+3]){pixels++;if(x===0||y===0||x===meta.frame[0]-1||y===meta.frame[1]-1)border++;}
          for(let k=0;k<4;k++){hash^=d[i+k];hash=Math.imul(hash,16777619);}
        }
        visible&&=pixels>20;signatures.push(hash);
      }
      return {kind:e.kind,frames:signatures.length,distinct:new Set(signatures).size,border,visible};
    });
  });
  for(const f of frames)check(f.frames===34&&f.visible&&(STUB||f.distinct>15&&f.border===0),`${f.kind}: all 34 animation frames visible, distinct and unclipped`);
  // Display-only animation fixtures; authoritative combat remains in the MCP scenario.
  const clips=await page.evaluate(()=>CATHEDRAL_ENEMIES.flatMap(e=>{
    const base={kind:e.kind,dead:false,hurtT:0,recT:0,hop:0,hopV:0,landT:0,blink:0,seed:0,state:'idle'};
    return [
      [{state:'windup',st:.5,windupTime:1},['attack',1]],
      [{state:'lunge',st:.15},['attack',4]],
      [{recT:.1},['attack',7]],
      [{hurtT:.2},['hurt',2]],
      [{hop:.1,hopV:1},['walk',2]],
      [{landT:.1},['walk',6]],
      [{dead:true,dieT:.3},['die',2]],
    ].map(([fixture,expected])=>({kind:e.kind,expected,actual:Field._debug.enemyFrame({...base,...fixture})}));
  }));
  for(const c of clips)check(c.actual.join()===c.expected.join(),`${c.kind}: animation ${c.expected.join(':')}`);
  const hues=[];
  for(let i=0;i<zones.length;i++){
    const zone=10+i,z=zones[i],door=await page.evaluate(zone=>WORLD_MAP.zones[8].portals.find(p=>p.to===zone),zone);
    await debug({op:'set_level',level:z.min_level-1});
    await stage(9,door.x,door.y+4);await click(door.x,door.y);await page.waitForTimeout(1800);
    check(await page.evaluate(()=>Field.zone===9),`${z.cathedralWing}: lower-level entry refused`);
    await stage(9,door.x,door.y+4);await debug({op:'set_level',level:50});
    await page.waitForFunction(()=>Field.hero.level===50);
    await click(door.x,door.y);await page.waitForFunction(zone=>Field.zone===zone,zone,{timeout:12000});
    await page.waitForTimeout(800);
    check(await page.evaluate(theme=>Field.zoneTheme===theme,z.theme),`${z.cathedralWing}: real canvas entry switches theme`);
    check((await page.locator('#area-title b').textContent())===z.name&&(await page.locator('#area-title span').textContent()).includes('Dungeon · 5 players'),`${z.cathedralWing}: dungeon banner names wing and party size`);
    check(await page.evaluate(level=>Field.slimes.length===20&&Field.slimes.every(s=>s.level===level),z.min_level),`${z.cathedralWing}: twenty authoritative enemies at wing level`);
    await page.waitForFunction(i=>valhalla.cathedralMusic[i]?.running&&valhalla.cathedralMusic[i]?.loaded,i,{timeout:15000});
    check(await page.evaluate(i=>valhalla.cathedralMusic.every((m,n)=>m.running===(n===i))&&!valhalla.nmusic.running,i),`${z.cathedralWing}: only its unique music loop plays`);
    hues.push(await page.evaluate(theme=>CathedralArt.ground(theme,4,4,.5,0),z.theme));
    await shot('cathedral-'+z.cathedralWing+'-arrival');
    const boss=await page.evaluate(z=>z.slimes.find(s=>CATHEDRAL_ENEMIES.find(e=>e.kind===s.kind)?.boss),z);
    await stage(zone,boss.x-5,boss.y);
    check(await page.evaluate(([kind,stub])=>Field.slimes.some(s=>s.kind===kind&&s.d.boss&&s.d.name&&(stub||s.d.top===Field.cathedralSprites.meta.tops[kind])),[boss.kind,STUB]),`${z.cathedralWing}: unique boss art, name and fitted health label loaded`);
    await shot('cathedral-'+z.cathedralWing+'-boss');
  }
  check(new Set(hues).size===3,'Distinct teal, rose and violet floor palettes');
  check(await page.evaluate(()=>valhalla.cathedralMusic.map(m=>Math.round(m.duration)).join()==='87,69,128'),'All three music loops decode to their own score lengths');
  await page.evaluate(()=>{City.close();Quests.close();WorldMap.show();});
  check(await page.evaluate(()=>WorldMap.open), 'World map opens from the Cathedral');
  check((await page.locator('#worldmap').textContent()).includes('Drowned Cathedral'),'World map includes the Cathedral wings');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`PASS Cathedral UI: ${checks} checks (${STUB?'stub':'real'} sprites), ${world.artifacts}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(world)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});});
