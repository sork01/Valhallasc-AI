const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-weather-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (ok, name) => { assert.ok(ok, name); checks++; };
async function call(name, args = {}) {
  const reply = await client.callTool({ name, arguments: args });
  assert.ok(!reply.isError, `${name}: ${JSON.stringify(reply.content)}`);
  return reply.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang:'en', sound:false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Weatherwatcher'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!window.Weather && !!document.querySelector('#world-weather'), null, { timeout: 60000 });
  check(await page.locator('#world-weather').isVisible(), 'weather is shown in the HUD');
  await page.evaluate(() => Online.send({type:'debug',command:{op:'set_weather',kind:'rain',intensity:'heavy'}}));
  await page.waitForFunction(() => Weather.state.type === 'rain' && Weather.state.intensity === 'heavy', null, {timeout:10000});
  check(await page.locator('#world-weather').textContent().then(s => s.includes('Rain')), 'server-forced rain reaches the HUD');
  check(await page.locator('#world-weather').getAttribute('title').then(s => s.includes('heavy')), 'HUD describes intensity');
  await page.waitForFunction(() => Weather.blend >= .95, null, {timeout:3000});
  await page.screenshot({path:path.join(world.artifacts,'weather-rain.png')});
  const paint = await page.evaluate(() => {
    const sample = (type, setting) => {
      Prefs.set({weather:setting}); Weather.setZone({theme:'meadow'});
      Weather.sync({type,intensity:'heavy',inside:false,ageSeconds:50,endsInSeconds:100,variant:null},36,60);
      Weather.tick(2,36,60);
      const canvas = document.createElement('canvas'); canvas.width=200; canvas.height=120;
      const g=canvas.getContext('2d'); g.fillStyle='#a0b0a0'; g.fillRect(0,0,200,120);
      Weather.draw(g,200,120,0);
      return [...g.getImageData(100,90,1,1).data].slice(0,3);
    };
    return {clear:sample('clear',1),rain:sample('rain',1),snow:sample('snow',1),off:sample('rain',0)};
  });
  check(JSON.stringify(paint.rain) !== JSON.stringify(paint.clear), `rain tints the ground: ${JSON.stringify(paint)}`);
  check(JSON.stringify(paint.snow) !== JSON.stringify(paint.clear), 'snow tints the ground');
  check(JSON.stringify(paint.off) === JSON.stringify(paint.clear), 'weather effects setting removes the paint');
  check(await page.locator('#world-weather').textContent().then(s => s.includes('Rain')), 'the HUD still reports server weather when effects are off');
  const still = await page.evaluate(() => {
    Prefs.set({weather:1}); Weather.sync({type:'rain',intensity:'heavy',inside:false,ageSeconds:50,endsInSeconds:100},36,60); Weather.tick(2,36,60);
    const frame = t => { const c=document.createElement('canvas'); c.width=80; c.height=60; Weather.draw(c.getContext('2d'),80,60,t); return c.toDataURL(); };
    return frame(0) === frame(10);
  });
  check(still, 'reduced motion keeps rain particles still');
  await page.evaluate(() => Prefs.set({weather:0}));
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  check(await page.locator('#set-weather').inputValue() === '0', 'settings reads the saved weather intensity');
  await page.locator('#set-weather').fill('50');
  check(await page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).weather) === .5, 'weather setting persists');
  await page.locator('#set-weather-audio').fill('25');
  check(await page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).weatherAudio) === .25, 'weather sound slider persists independently');
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  await page.evaluate(() => Online.send({type:'debug',command:{op:'teleport',zone:5,x:36,y:52}}));
  await page.waitForFunction(() => Field.zone === 5 && Weather.state.inside, null, {timeout:10000});
  check(await page.locator('#world-weather').textContent().then(s => s.includes('Indoors')), 'dungeon clears weather');
  await page.evaluate(() => Online.send({type:'debug',command:{op:'teleport',zone:0,x:36,y:60}}));
  await page.waitForFunction(() => Field.zone === 0 && Weather.state.type === 'rain', null, {timeout:10000});
  check(true, 'outdoor weather returns on leaving the dungeon');
  check(await page.evaluate(() => [Weather.season(50,300),Weather.season(300,300),Weather.season(300,50),Weather.season(50,50)].join(',')) === 'spring,summer,autumn,winter', 'Yearwheel quadrants select their season');
  const kinds = await page.evaluate(() => {
    const frame = (type, time, variant = null) => {
      Prefs.set({weather:1}); Weather.setZone({theme:'meadow'});
      Weather.sync({type,intensity:'heavy',variant,inside:false,ageSeconds:50,endsInSeconds:100},36,60); Weather.tick(2,36,60);
      const c=document.createElement('canvas');c.width=240;c.height=140;
      const g=c.getContext('2d');g.fillStyle='#a0b0a0';g.fillRect(0,0,c.width,c.height);Weather.draw(g,c.width,c.height,time);
      return c.toDataURL();
    };
    return {clear:frame('clear',1),fog:frame('fog',1),wind:frame('wind',1,'leaves'),ash:frame('wind',1,'ash'),sandstorm:frame('sandstorm',1),storm:frame('thunderstorm',1),flash:frame('thunderstorm',0)};
  });
  for (const type of ['fog','wind','sandstorm','storm']) check(kinds[type] !== kinds.clear, `${type} paints a distinct weather effect`);
  check(kinds.wind !== kinds.ash, 'wind follows its zone variant');
  check(kinds.storm !== kinds.flash, 'thunderstorm adds a short lightning flash');
  const nightWeather = await page.evaluate(() => {
    const frame = type => {
      DayNight.setZone({theme:'meadow'});DayNight.sync({hour:0,hoursPerSecond:0});DayNight.tick(20);
      Weather.setZone({theme:'meadow'});Weather.sync({type,intensity:'heavy',inside:false,ageSeconds:50,endsInSeconds:100},36,60);Weather.tick(2,36,60);
      const c=document.createElement('canvas');c.width=240;c.height=140;const g=c.getContext('2d');
      g.fillStyle='#a0b0a0';g.fillRect(0,0,c.width,c.height);DayNight.draw(g,c.width,c.height,[],()=>[0,0]);Weather.draw(g,c.width,c.height,1);
      return c.toDataURL();
    };
    return [frame('clear'),frame('rain'),frame('snow')];
  });
  check(nightWeather[1] !== nightWeather[0] && nightWeather[2] !== nightWeather[0], 'rain and snow remain visible over midnight tint');

  // The private server rejects forbidden combinations and shares the chosen state.
  for (const [zone,x,y,type] of [[0,36,60,'rain'],[0,36,60,'fog'],[0,36,60,'thunderstorm'],[0,36,60,'wind'],[2,64,118.5,'snow'],[14,64,116,'sandstorm']]) {
    await page.evaluate(({zone,x,y}) => Online.send({type:'debug',command:{op:'teleport',zone,x,y}}),{zone,x,y});
    await page.waitForFunction(zone => Field.zone === zone,zone,{timeout:10000});
    await page.evaluate(type => Online.send({type:'debug',command:{op:'set_weather',kind:type,intensity:'heavy'}}),type);
    await page.waitForFunction(type => Weather.state.type === type,type,{timeout:10000});
    check(true, `private zone ${zone} accepts ${type}`);
  }
  await page.evaluate(() => Online.send({type:'debug',command:{op:'teleport',zone:0,x:36,y:60}}));
  await page.waitForFunction(() => Field.zone === 0,null,{timeout:10000});
  await page.evaluate(() => Online.send({type:'debug',command:{op:'set_weather',kind:'snow',intensity:'heavy'}}));
  await page.waitForTimeout(300);
  check(await page.evaluate(() => Weather.state.type !== 'snow'), 'a forbidden snow override does not change the meadow');
  await page.evaluate(() => Online.send({type:'debug',command:{op:'set_weather',kind:'rain',intensity:'heavy'}}));
  await page.waitForFunction(() => Weather.state.type === 'rain',null,{timeout:10000});
  const other = await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});
  await other.addInitScript(() => localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
  await other.goto(world.url);await other.locator('#start').click();await other.locator('#login-guest').click();
  await other.locator('#name').fill('SecondWeatherwatcher');await other.locator('#go').click({timeout:60000});
  await other.waitForFunction(() => Online.connected && Weather.state.type === 'rain',null,{timeout:60000});
  check(true, 'two players in one zone receive the same forced weather');await other.close();
  await page.evaluate(() => Prefs.set({sound:true,weatherAudio:1}));
  await page.evaluate(() => Online.send({type:'debug',command:{op:'set_weather',kind:'rain',intensity:'heavy'}}));
  await page.waitForFunction(() => Weather.state.type === 'rain' && WeatherAudio.levels[0] > .005,null,{timeout:10000});
  check(true,'rain has a soft ambient audio bed');
  await page.evaluate(() => Online.send({type:'debug',command:{op:'teleport',zone:5,x:36,y:52}}));
  await page.waitForFunction(() => Field.zone === 5 && Weather.state.inside && WeatherAudio.levels[0] < .001,null,{timeout:10000});
  check(true,'weather audio fades out indoors');
  await page.evaluate(() => Prefs.set({weatherAudio:0}));
  check(await page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).weatherAudio) === 0,'weather sound has its own persisted volume');
  await page.evaluate(() => Online.send({type:'debug',command:{op:'teleport',zone:0,x:36,y:60}}));
  await page.waitForFunction(() => Field.zone === 0,null,{timeout:10000});

  await page.emulateMedia({reducedMotion:'no-preference'});
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
  const budget = await page.evaluate(() => {
    const c=document.createElement('canvas');c.width=320;c.height=180;const g=c.getContext('2d');
    const measure = type => {
      Prefs.set({weather:1});Weather.sync({type,intensity:'heavy',inside:false,ageSeconds:50,endsInSeconds:100},36,60);Weather.tick(2,36,60);
      const start=performance.now();for(let i=0;i<100;i++)Weather.draw(g,320,180,i/60);
      return (performance.now()-start)/100;
    };
    return {clear:measure('clear'),storm:measure('thunderstorm'),sand:measure('sandstorm')};
  });
  await cdp.send('Emulation.setCPUThrottlingRate',{rate:1});
  check(Math.max(budget.storm,budget.sand)-budget.clear < 8, `weather paint uses under 8 ms on a 4× slower CPU: ${JSON.stringify(budget)}`);
  check(!errors.length, `no browser errors: ${errors.join('; ')}`);
  await page.close();
  await call('connect_bot',{bot:'WeatherSchedule',class:'warrior',gender:'male'});
  await call('teleport',{bot:'WeatherSchedule',to:{spawn:20}});
  const before=(await call('inspect_world',{events:0})).snapshot.weather;
  await call('restart_world');
  const after=(await call('inspect_world',{events:0})).snapshot.weather;
  check(before.type===after.type && before.intensity===after.intensity && before.variant===after.variant,`private server restart preserves the seeded weather schedule: ${JSON.stringify({before,after})}`);
  console.log(`${checks} weather UI checks passed; screenshot: ${path.join(world.artifacts,'weather-rain.png')}`);
})().catch(e => { console.error(e); process.exitCode=1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
