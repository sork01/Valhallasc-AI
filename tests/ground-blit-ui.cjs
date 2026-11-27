'use strict';
// Run only through scripts/test-touch-bounded.sh. BROWSER=firefox (default) or
// chromium; MUTATE=padding serves the old source rectangle without editing disk.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { firefox, chromium } = require('playwright');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld(), root = path.resolve(__dirname, '..');
const engine = process.env.BROWSER === 'chromium' ? chromium : firefox;
const reports = [];
let browser, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
(async () => {
  await world.start();
  const cases=[[1280,800,1,true],[960,600,2,false],[1440,900,2,false]];
  for (const [width, height, deviceScaleFactor, lowGraphics] of (process.env.GROUND_CASE ? [cases[Number(process.env.GROUND_CASE)-1]] : cases)) {
    console.log(`${engine.name()}: ${width}x${height}, DPR ${deviceScaleFactor}, low graphics ${lowGraphics}`);
    // Reduce idle background processes to fit the existing 128-task cap.
    browser = await engine.launch({ headless: true, ...(engine === firefox ? { firefoxUserPrefs: {
      'dom.ipc.processCount': 1, 'dom.ipc.processCount.webIsolated': 1,
      'dom.ipc.processPrelaunch.enabled': false, 'fission.autostart': false,
      'network.process.enabled': false, 'media.rdd-process.enabled': false,
      'media.utility-process.enabled': false,
    } } : {}) });
    const page = await browser.newPage({viewport:{width,height},deviceScaleFactor,reducedMotion:'reduce'});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const version = fs.readFileSync(path.join(root, 'client/index.html'), 'utf8').match(/class="version">([^<]+)</)[1];
    await page.addInitScript(({lowGraphics,version}) => {
      window.AudioContext = window.webkitAudioContext = undefined;
      window.__valhallaTestSprites = true;
      window.confirm = () => true;
      localStorage.setItem('valhallasc.whats-new.v1', version);
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({lang:'en',sound:false,lowGraphics}));
      window.__groundCalls = [];
      const drawImage = CanvasRenderingContext2D.prototype.drawImage;
      CanvasRenderingContext2D.prototype.drawImage = function(image,...args) {
        if (image.__ground && __groundCalls.length < 4000) {
          const { a, d } = this.getTransform();
          __groundCalls.push({ raster:image.__ground, size:[image.width,image.height], args, backing:[a,d] });
        }
        return drawImage.call(this,image,...args);
      };
    }, {lowGraphics,version});
    let field = fs.readFileSync(path.join(root, 'client/field.js'), 'utf8');
    const tag = 'return { c, G, standIn: stand_in.size ? [...stand_in] : null };';
    assert.ok(field.includes(tag));
    field = field.replace(tag, 'c.__ground={zone,scale:chunkScale,w:G.w,h:G.h};'+tag);
    field = field.replace('  window.Field = Field;', `
      window.__groundPixelTest=(g,c,scale,G)=>{const keep=chunkScale;chunkScale=scale;
        try{drawGroundChunk(g,c,8/scale,8/scale,G);}finally{chunkScale=keep;}};
      window.Field=Field;
    `);
    if (process.env.MUTATE === 'padding') field = field.replace(
      'g.drawImage(c, 0, 0, G.w * chunkScale, G.h * chunkScale, dx, dy, G.w, G.h);',
      'g.drawImage(c, dx, dy, G.w, G.h);');
    await page.route('**/field.js*', route => route.fulfill({contentType:'text/javascript',body:field}));
    await page.goto(world.url);
    await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill(`Ground${width}`);
    await page.locator('#go').click({timeout:60000});
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, {timeout:60000});
    await page.evaluate(() => Tutorial.disable());
    await page.locator('#connection-overlay').waitFor({state:'hidden',timeout:60000});
    const pixels = await page.evaluate(() => [.6,.8,1.2,1.5].map(scale => {
      const G={w:812,h:556},source=document.createElement('canvas');
      source.width=Math.ceil(G.w*scale);source.height=Math.ceil(G.h*scale);
      const sg=source.getContext('2d'),image=sg.createImageData(source.width,source.height);
      for(let y=0;y<source.height;y++)for(let x=0;x<source.width;x++){
        const i=(y*source.width+x)*4;image.data.set([x%256,y%256,(x*17+y*13)%256,255],i);
      }
      sg.putImageData(image,0,0);
      const result=document.createElement('canvas');result.width=source.width+16;result.height=source.height+16;
      const g=result.getContext('2d');g.setTransform(scale,0,0,scale,0,0);g.imageSmoothingEnabled=false;
      __groundPixelTest(g,source,scale,G);
      const w=source.width-2,h=source.height-2,actual=g.getImageData(8,8,w,h).data,expected=sg.getImageData(0,0,w,h).data;
      let changed=0;for(let i=0;i<actual.length;i++)if(actual[i]!==expected[i])changed++;
      return {scale,changed};
    }));
    for(const result of pixels)check(result.changed===0, `1:1 ground pixels stay exact at scale ${result.scale}: ${result.changed} differences`);
    for (const [zone,x,y] of [[0,250,235],[9,40,24]]) {
      await page.evaluate(command => GM.request(command), {op:'teleport',zone,x,y});
      await page.waitForFunction(zone => Field.zone === zone, zone);
      await page.waitForTimeout(1500);
      await page.waitForFunction(()=>Field.canAct,null,{timeout:15000});
      const start = await page.evaluate(() => { document.activeElement?.blur();__groundCalls=[]; return [Field.hero.x,Field.hero.y]; });
      await page.keyboard.down('ArrowRight'); await page.keyboard.down('ArrowDown');
      await page.waitForFunction(start=>Math.hypot(Field.hero.x-start[0],Field.hero.y-start[1])>2,start,{timeout:15000});
      await page.waitForTimeout(1000);
      await page.keyboard.up('ArrowRight'); await page.keyboard.up('ArrowDown');
      const sample = await page.evaluate(() => ({calls:__groundCalls,pos:[Field.hero.x,Field.hero.y],low:Prefs.lowGraphics}));
      check(sample.low === lowGraphics, 'the requested graphics mode is active');
      check(Math.hypot(sample.pos[0]-start[0],sample.pos[1]-start[1]) > 1, `the world scrolls during real walking: ${JSON.stringify({start,pos:sample.pos})}`);
      check(sample.calls.length > 20, 'multiple frames draw cached ground');
      check(sample.calls.some(c => c.raster.zone === zone), 'current-zone ground is drawn');
      if (zone === 9) check(sample.calls.some(c => c.raster.zone !== zone), 'seam-neighbour ground uses the same drawing path');
      for (const {raster:r,size,args,backing} of sample.calls) {
        assert.equal(args.length,8,'cached tiles exclude their rounded canvas padding');
        const [sx,sy,sw,sh,dx,dy,dw,dh] = args;
        assert.equal(sx,0);assert.equal(sy,0);assert.equal(dw,r.w);assert.equal(dh,r.h);
        assert.ok(Number.isFinite(dx)&&Number.isFinite(dy));
        assert.ok(Math.abs(sw-r.w*r.scale)<1e-8&&Math.abs(sh-r.h*r.scale)<1e-8);
        assert.ok(sw<=size[0]&&sh<=size[1]);
        assert.ok(Math.abs(dw*backing[0]/sw-backing[0]/r.scale)<1e-8);
        assert.ok(Math.abs(dh*backing[1]/sh-backing[1]/r.scale)<1e-8);
      }
      checks++;
      reports.push({browser:engine.name(),width,height,deviceScaleFactor,lowGraphics,zone,draws:sample.calls.length,groundZones:[...new Set(sample.calls.map(c=>c.raster.zone))]});
    }
    check(errors.length===0, `no page errors: ${errors.join('; ')}`);
    await browser.close();browser=null;
  }
  fs.writeFileSync(path.join(world.runDir,`ground-blit-${engine.name()}.json`),JSON.stringify({checks,reports},null,2));
  console.log(`Ground drawing: ${checks} checks passed; ${world.runDir}`);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{
  const cg=fs.readFileSync('/proc/self/cgroup','utf8').trim().split('::')[1];
  for(const name of ['memory.peak','memory.events','pids.events'])console.log(name,fs.readFileSync('/sys/fs/cgroup'+cg+'/'+name,'utf8').trim());
  await browser?.close();await world.stop();
});
