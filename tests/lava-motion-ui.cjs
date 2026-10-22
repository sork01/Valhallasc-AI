// Only RAID-LAVA-ANIMATE: real private client, paired terrain pixels and motion guards.
process.env.REAL_SPRITES='1';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..'),client=new Client({name:'lava-motion',version:'1'});
let browser,started=false,checks=0;
const check=(ok,message)=>{assert.ok(ok,message);checks++;};
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',env:{...process.env}}));
  const world=await call('start_world',{godMode:true,startLevel:99,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/home/serveperry/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'no-preference'}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  if(process.env.MUTATE)await page.route('**/emberwakeart.js',async route=>{
    const r=await route.fetch();await route.fulfill({response:r,body:(await r.text())+'\nEmberwakeArt.moltenMotion=()=>{};'});
  });
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#name').fill('Lava Artist');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&Field.hero&&window.EmberwakeArt,null,{timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
  await debug({op:'set_time',hour:12,freeze:true});await debug({op:'set_weather',kind:'clear'});
  const results=[];
  for(const [zone,x,y,name]of [[45,104,92,'emberwake'],[46,30,303,'chained-forge']]){
    await debug({op:'teleport',zone,x,y});
    await page.waitForFunction(([zone,x,y])=>Field.zone===zone&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<1.5,[zone,x,y],{timeout:20000});
    await page.waitForTimeout(800);
    await page.waitForFunction(()=>Number(getComputedStyle(document.getElementById('area-title')).opacity)<.05);
    await page.waitForFunction(()=>Field.cathedralSprites?.meta.kinds.some(k=>k.startsWith('ew_')||k.startsWith('cf_')));
    for(const reduced of [false,true]){
      await page.emulateMedia({reducedMotion:reduced?'reduce':'no-preference'});
      const paired=await page.evaluate(()=>{
        const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),original=EmberwakeArt.moltenMotion;
        const render=(t,on)=>{EmberwakeArt.moltenMotion=on?original:()=>{};Field._debug.drawFrame(t);return g.getImageData(0,0,cv.width,cv.height).data;};
        try{
          const deltas=[];
          for(const t of [1,7]){
            const a=render(t,false),b=render(t,true),delta=new Int16Array(a.length);
            let pixels=0,max=0;for(let i=0;i<a.length;i+=4){let changed=false;for(let j=0;j<3;j++){delta[i+j]=b[i+j]-a[i+j];max=Math.max(max,Math.abs(delta[i+j]));changed ||= delta[i+j]!==0;}if(changed)pixels++;}
            deltas.push({pixels,max,delta});
          }
          let temporal=0;for(let i=0;i<deltas[0].delta.length;i++)if(deltas[0].delta[i]!==deltas[1].delta[i])temporal++;
          return {pixels:deltas.map(d=>d.pixels),max:Math.max(...deltas.map(d=>d.max)),temporal};
        }finally{EmberwakeArt.moltenMotion=original;}
      });
      if(reduced)check(paired.pixels.every(n=>n===0),'Reduced motion disables the actual field overlay in '+name+': '+JSON.stringify(paired));
      else{
        check(paired.pixels.every(n=>n>50),'Motion reaches the actual rendered lava in '+name+': '+JSON.stringify(paired));
        check(paired.temporal>100,'Lava changes with the shared frame clock in '+name);
        check(paired.max<100,'Motion remains a subtle overlay in '+name);
        await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,name+'-lava-motion.png')});
      }
      results.push({name,reduced,paired});
    }
    const isolated=await page.evaluate(({zone,x,y})=>{
      const z=WORLD_MAP.zones[zone-1],c=document.createElement('canvas');c.width=800;c.height=500;
      const g=c.getContext('2d'),cx=(x-y)*44,cy=(x+y)*22,motion=EmberwakeArt.moltenMotion;
      const render=(t,offset=0,calm=false)=>{g.clearRect(0,0,800,500);motion(g,800,500,t,z,cx+offset,cy,88,44,calm);return g.getImageData(0,0,800,500).data;};
      let painted=0,leaks=0,bubbleFrames=0,maxBubbles=0;
      const ellipse=g.ellipse.bind(g);let bubbles=0;g.ellipse=(...args)=>{bubbles++;ellipse(...args);};
      for(let t=0;t<30;t+=.5){
        bubbles=0;const p=render(t);if(bubbles)bubbleFrames++;maxBubbles=Math.max(maxBubbles,bubbles);
        for(let py=0;py<500;py++)for(let px=0;px<800;px++){
          if(!p[(py*800+px)*4+3])continue;painted++;
          const wx=(px-400+cx)/88+(py-250+cy)/44,wy=(py-250+cy)/44-(px-400+cx)/88;
          if(z.theme==='chained_forge'?z.forgeFloor?.[Math.floor(wy)]?.[Math.floor(wx)]==='=':
            !z.objects.some(o=>o.kind==='ew_lava'&&o.r-Math.hypot(wx-o.x,wy-o.y)>.3))leaks++;
        }
      }
      const a=render(7),b=render(7,88);let anchorDifferences=0,anchorPainted=0;
      for(let py=20;py<480;py++)for(let px=120;px<760;px++){
        const ka=(py*800+px)*4,kb=(py*800+px-88)*4;
        if(a[ka+3])anchorPainted++;
        for(let j=0;j<4;j++)if(Math.abs(a[ka+j]-b[kb+j])>1)anchorDifferences++;
      }
      const calmA=render(1,0,true),calmB=render(7,0,true);
      const calm=calmA.every((n,i)=>n===calmB[i]&&n===0);
      const start=performance.now();for(let i=0;i<300;i++)motion(g,800,500,i/60,z,cx,cy);const msPerFrame=(performance.now()-start)/300;
      return {painted,leaks,bubbleFrames,maxBubbles,anchorPainted,anchorDifferences,calm,msPerFrame};
    },{zone,x:zone===46?18:x,y});
    check(isolated.painted>1000&&isolated.leaks===0,'Overlay stays inside the lava footprint in '+name+': '+JSON.stringify(isolated));
    check(isolated.bubbleFrames>0&&isolated.bubbleFrames<60&&isolated.maxBubbles<=8,'Small bubbles appear occasionally in '+name+': '+JSON.stringify(isolated));
    check(isolated.anchorPainted>10&&isolated.anchorDifferences===0,'Motion stays anchored when the camera moves in '+name+': '+JSON.stringify(isolated));
    check(isolated.calm,'Reduced motion is static across clocks in '+name);
    results.push({name,isolated});
  }
  const idle=await page.evaluate(()=>{
    const z=WORLD_MAP.zones[44],g=new Proxy({},{get(){throw Error('No visible lava must not touch the canvas');}});
    EmberwakeArt.moltenMotion(g,200,100,7,z,(22-137)*44,(22+137)*22);
    EmberwakeArt.moltenMotion(g,800,500,7,z,0,0,88,44,true);
    return true;
  });check(idle,'No canvas work when lava is absent or reduced motion is enabled');
  check(errors.length===0,'No browser errors: '+JSON.stringify(errors));
  fs.writeFileSync(path.join(world.artifacts,'lava-motion-result.txt'),JSON.stringify({passed:true,checks,results,errors},null,2));
  console.log(JSON.stringify({passed:true,checks,artifacts:world.artifacts,results}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(started)try{await call('stop_world');}catch{}await client.close();
});
