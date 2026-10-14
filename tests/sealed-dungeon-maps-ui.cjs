// Focused private Chromium check for the open and sealed dungeon scenes.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'sealed-dungeon-maps-ui', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  const transport = new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  transport.stderr?.on('data', chunk => process.stderr.write(chunk));
  await client.connect(transport);
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('SealedMaps');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  if (process.argv.includes('--season-only')) {
    const scene=await page.evaluate(async()=>{
      const z=Field._debug.zones,ctx=new AudioContext(),scores=[];
      for(const name of ['blooming_labyrinth','solar_crucible','amber_archive','silent_solstice']){
        const r=await fetch(`assets/music_${name}.mp3`);
        scores.push([r.status,(await ctx.decodeAudioData(await r.arrayBuffer())).duration]);
      }
      await ctx.close();
      return {scores,gates:z[28].portals.filter(p=>p.id.endsWith('_descent')).map(p=>p.to),
        bloom:[z[36].theme,z[36].sealedTemplate,z[36].slimes.length,z[36].portals.length],
        solar:[z[37].theme,z[37].sealedTemplate,z[37].slimes.length,z[37].portals.length],
        amber:[z[38].theme,z[38].sealedTemplate,z[38].slimes.length,z[38].portals.length],
        solstice:[z[39].theme,z[39].sealedTemplate,z[39].slimes.length,z[39].portals.length],
        art:['bloom_wall','bloom_lamp','bloom_altar','bloom_seal','solar_wall','solar_brazier','solar_forge','solar_seal'].every(k=>!!City.art[k])&&
          ['amber_wall','amber_lantern','amber_lectern','amber_seal','solstice_wall','solstice_lantern','solstice_altar','solstice_seal'].every(k=>!!City.art[k])&&
          ['blooming_labyrinth','solar_crucible','amber_archive','silent_solstice'].every(k=>SeasonDungeonArt.isTheme(k))&&
          [createBloomMusic,createSolarMusic,createAmberMusic,createSolsticeMusic].every(f=>typeof f==='function')};
    });
    assert.ok(scene.art);
    assert.ok(scene.scores[0][0]===200&&scene.scores[0][1]>45&&scene.scores[0][1]<46);
    assert.ok(scene.scores[1][0]===200&&scene.scores[1][1]>34&&scene.scores[1][1]<35);
    assert.ok(scene.scores[2][0]===200&&scene.scores[2][1]>42&&scene.scores[2][1]<44);
    assert.ok(scene.scores[3][0]===200&&scene.scores[3][1]>53&&scene.scores[3][1]<54);
    assert.deepEqual(scene.bloom,['blooming_labyrinth',false,12,2]);
    assert.deepEqual(scene.solar,['solar_crucible',false,12,2]);
    assert.deepEqual(scene.amber,['amber_archive',false,12,2]);
    assert.deepEqual(scene.solstice,['silent_solstice',false,12,2]);
    assert.deepEqual(scene.gates,[36,37,38,39]);
    await page.keyboard.press('m');
    assert.equal(await page.locator('.wm-tile[data-zone="36"]').count(),1);
    assert.equal(await page.locator('.wm-tile[data-zone="37"]').count(),1);
    assert.equal(await page.locator('.wm-tile[data-zone="38"]').count(),1);
    assert.equal(await page.locator('.wm-tile[data-zone="39"]').count(),1);
    await page.keyboard.press('m');
    await page.evaluate(()=>Online.send({type:'debug',ref:911,command:{op:'teleport',zone:36,x:48,y:82}}));
    await page.waitForFunction(()=>Field.zone===36,null,{timeout:15000});
    assert.equal(await page.evaluate(()=>Field.zoneTheme),'blooming_labyrinth');
    for(const [zone,kind,name] of [[36,'bloom_heart','blooming'],[37,'solar_heart','solar'],[38,'amber_memory','amber'],[39,'solstice_heart','solstice']]){
      if(zone!==36)await page.evaluate(zone=>Online.send({type:'debug',ref:912+zone,command:{op:'teleport',zone,x:48,y:82}}),zone);
      await page.waitForFunction(([zone,kind])=>Field.zone===zone&&Field.slimes.length===12&&!!Field.cathedralSprites?.img?.[kind],[zone,kind],{timeout:45000});
      const cast=await page.evaluate(()=>Field.slimes.map(e=>e.kind).filter((v,i,a)=>a.indexOf(v)===i).map(kind=>({kind,width:Field.cathedralSprites.img[kind]?.naturalWidth,height:Field.cathedralSprites.img[kind]?.naturalHeight,frame:Field._debug.enemyFrame(Field.slimes.find(e=>e.kind===kind))})));
      assert.equal(cast.length,6);
      assert.ok(cast.every(e=>(STUB||(e.width===768&&e.height===480))&&e.frame));
      await page.screenshot({path:path.join(root,`test-results/${name}-season-scene.png`)});
    }
    assert.deepEqual(errors,[]);
    console.log('Four Yearwheel dungeon scene browser checks passed');
    return;
  }
  if (process.argv.includes('--thunder-bloom-only')) {
    const scene=await page.evaluate(async()=>{
      const z=Field._debug.zones,context=new AudioContext();
      const r=await fetch('assets/music_thunderheart_gate.mp3');
      const audio=await context.decodeAudioData(await r.arrayBuffer());await context.close();
      return {score:[r.status,audio.duration],art:!!City.art.thunder_wall&&!!City.art.thunder_pylon&&!!City.art.thunder_altar&&
        typeof ThunderArt.portal==='function'&&typeof createThunderMusic==='function',
        gate:z[27].portals.find(p=>p.id==='cairn_thunderheart_gate'),
        thunder:[z[35].theme,z[35].sealedTemplate,z[35].slimes.length,z[35].portals.length],
        bloom:[z[36].sealedTemplate,z[36].slimes.length,z[28].portals.some(p=>p.to===36)]};
    });
    assert.ok(scene.art&&scene.score[0]===200&&scene.score[1]>57&&scene.score[1]<59);
    assert.equal(scene.gate?.to,35);
    assert.deepEqual(scene.thunder,['thunderheart_gate',false,12,2]);
    assert.deepEqual(scene.bloom,[false,12,true]);
    await page.keyboard.press('m');
    assert.equal(await page.locator('.wm-tile[data-zone="35"]').count(),1);
    assert.equal(await page.locator('.wm-tile[data-zone="36"]').count(),1);
    await page.keyboard.press('m');
    await page.evaluate(() => Online.send({type:'debug',ref:795,command:{op:'teleport',zone:27,x:151,y:24}}));
    await page.waitForFunction(()=>Field.zone===27&&Math.hypot(Field.hero.x-151,Field.hero.y-24)<2);
    await page.screenshot({path:path.join(root,'test-results/thunderheart-entrance.png')});
    await page.evaluate(()=>Online.send({type:'debug',ref:796,command:{op:'set_level',level:95}}));
    await page.waitForFunction(()=>Field.hero.level===95,null,{timeout:10000});
    await page.evaluate(p=>Online.send({type:'move',x:p.x,y:p.y}),scene.gate);
    await page.waitForFunction(()=>Field.zone===35,null,{timeout:15000});
    assert.equal(await page.evaluate(()=>Field.zoneTheme),'thunderheart_gate');
    for(const [zone,kind,name] of [[35,'thunder_heart','thunderheart'],[36,'bloom_heart','blooming-foes']]){
      await page.evaluate(zone=>Online.send({type:'debug',ref:800+zone,command:{op:'teleport',zone,x:48,y:82}}),zone);
      await page.waitForFunction(([zone,kind])=>Field.zone===zone&&Field.slimes.length===12&&!!Field.cathedralSprites?.img?.[kind],[zone,kind],{timeout:45000});
      const cast=await page.evaluate(()=>Field.slimes.map(e=>e.kind).filter((v,i,a)=>a.indexOf(v)===i).map(kind=>({kind,width:Field.cathedralSprites.img[kind]?.naturalWidth,height:Field.cathedralSprites.img[kind]?.naturalHeight,frame:Field._debug.enemyFrame(Field.slimes.find(e=>e.kind===kind))})));
      assert.equal(cast.length,6);
      assert.ok(cast.every(e=>(STUB||(e.width===768&&e.height===480))&&e.frame));
      await page.screenshot({path:path.join(root,`test-results/${name}-scene.png`)});
    }
    assert.deepEqual(errors,[]);
    console.log('Thunderheart and Blooming scene browser checks passed');
    return;
  }
  if (process.argv.includes('--astrolabe-only')) {
    const scene=await page.evaluate(async()=>{
      const z=Field._debug.zones,context=new AudioContext();
      const r=await fetch('assets/music_sunken_astrolabe.mp3');
      const audio=await context.decodeAudioData(await r.arrayBuffer());
      await context.close();
      return {score:[r.status,audio.duration],art:!!City.art.astro_wall&&!!City.art.astro_lamp&&!!City.art.astro_orrery&&
        typeof SunkenArt.portal==='function'&&typeof createSunkenMusic==='function',
        gate:z[25].portals.find(p=>p.id==='lapis_astrolabe_gate'),
        floor:[z[34].theme,z[34].sealedTemplate,z[34].slimes.length,z[34].portals.length],
        thunder:[z[35].sealedTemplate,z[35].slimes.length,z[27].portals.some(p=>p.to===35)]};
    });
    assert.ok(scene.art&&scene.score[0]===200&&scene.score[1]>79&&scene.score[1]<81);
    assert.equal(scene.gate?.to,34);
    assert.deepEqual(scene.floor,['sunken_astrolabe',false,12,2]);
    assert.deepEqual(scene.thunder,[false,12,true]);
    await page.keyboard.press('m');
    assert.equal(await page.locator('.wm-tile[data-zone="34"]').count(),1);
    assert.equal(await page.locator('.wm-tile[data-zone="35"]').count(),1);
    await page.keyboard.press('m');
    await page.evaluate(() => Online.send({type:'debug',ref:699,command:{op:'teleport',zone:25,x:135,y:16}}));
    await page.waitForFunction(() => Field.zone===25 && Math.hypot(Field.hero.x-135,Field.hero.y-16)<2);
    await page.waitForTimeout(1200);
    await page.screenshot({path:path.join(root,'test-results/sunken-astrolabe-entrance.png')});
    for(const [zone,kind,name] of [[34,'astro_axis','sunken-astrolabe'],[35,'thunder_heart','thunderheart-foes']]){
      await page.evaluate(zone=>Online.send({type:'debug',ref:700+zone,command:{op:'teleport',zone,x:48,y:82}}),zone);
      await page.waitForFunction(([zone,kind])=>Field.zone===zone&&Field.slimes.length===12&&!!Field.cathedralSprites?.img?.[kind],
        [zone,kind],{timeout:45000});
      const cast=await page.evaluate(()=>Field.slimes.map(e=>e.kind).filter((v,i,a)=>a.indexOf(v)===i).map(kind=>({
        kind,width:Field.cathedralSprites.img[kind]?.naturalWidth,height:Field.cathedralSprites.img[kind]?.naturalHeight,
        frame:Field._debug.enemyFrame(Field.slimes.find(e=>e.kind===kind))})));
      assert.equal(cast.length,6);
      assert.ok(cast.every(e=>(STUB || (e.width===768&&e.height===480))&&e.frame));
      await page.waitForTimeout(1500);
      await page.screenshot({path:path.join(root,`test-results/${name}-scene.png`)});
    }
    assert.deepEqual(errors,[]);
    console.log('Astrolabe scene/music and Thunderheart sprites browser checks passed');
    return;
  }
  if (process.argv.includes('--pavilion-rain-only')) {
    const scene = await page.evaluate(async () => {
      const context = new AudioContext();
      const scores = [];
      for (const file of ['music_pavilion.mp3', 'music_rain_crown.mp3', 'music_seed_vault.mp3']) {
        const response = await fetch(`assets/${file}`);
        const audio = await context.decodeAudioData(await response.arrayBuffer());
        scores.push([response.status, audio.duration]);
      }
      await context.close();
      return { scores, art: !!City.art.pavilion_wall && !!City.art.pavilion_lantern &&
        !!City.art.rain_wall && !!City.art.rain_brazier && !!City.art.seed_wall && !!City.art.seed_lamp &&
        typeof PavilionArt.portal === 'function' && typeof RainCrownArt.portal === 'function' && typeof SeedVaultArt.portal === 'function',
        music: typeof createPavilionMusic === 'function' && typeof createRainCrownMusic === 'function' && typeof createSeedVaultMusic === 'function',
        zones: Field._debug.zones.slice(31,34).map(z => ({ theme: z.theme, sealed: z.sealedTemplate,
          spawns: z.slimes.length, portals: z.portals.length })),
        entrance: Field._debug.zones[21].portals.find(p => p.id === 'ribbon_pavilion_gate')?.to,
        rainEntrance: Field._debug.zones[22].portals.some(p => p.to === 32),
        seedEntrance: Field._debug.zones[24].portals.some(p => p.to === 33) };
    });
    assert.ok(scene.art && scene.music);
    assert.ok(scene.scores.every(([status, seconds]) => status === 200 && seconds > 65));
    assert.deepEqual(scene.zones, [
      { theme: 'thousandfold', sealed: false, spawns: 12, portals: 2 },
      { theme: 'rain_crown', sealed: false, spawns: 12, portals: 2 },
      { theme: 'seed_vault', sealed: false, spawns: 12, portals: 2 },
    ]);
    assert.equal(scene.entrance, 31);
    assert.equal(scene.rainEntrance, true);
    assert.equal(scene.seedEntrance, true);
    await page.keyboard.press('m');
    assert.equal(await page.locator('.wm-tile[data-zone="31"]').count(), 1);
    assert.equal(await page.locator('.wm-tile[data-zone="32"]').count(), 1);
    assert.equal(await page.locator('.wm-tile[data-zone="33"]').count(), 1);
    await page.keyboard.press('m');
    await page.evaluate(() => Online.send({ type: 'debug', ref: 699,
      command: { op: 'teleport', zone: 21, x: 113, y: 65 } }));
    await page.waitForFunction(() => Field.zone === 21 && Math.hypot(Field.hero.x - 113, Field.hero.y - 65) < 2);
    await page.waitForTimeout(2200);
    await page.locator('#area-title').evaluate(el => el.classList.remove('show'));
    await page.screenshot({ path: path.join(root, 'test-results/thousandfold-pavilion-entrance.png') });
    for (const [zone, name] of [[31, 'thousandfold-pavilion'], [32, 'rain-crown-temple'], [33, 'seed-vault']]) {
      await page.evaluate(zone => Online.send({ type: 'debug', ref: 700 + zone,
        command: { op: 'teleport', zone, x: 48, y: 83 } }), zone);
      await page.waitForFunction(zone => Field.zone === zone &&
        Field.slimes.length === 12 && !!Field.cathedralSprites?.img?.[zone === 31 ? 'pavilion_sovereign' : zone === 32 ? 'rain_crown_sovereign' : 'seed_worldseed'],
      zone, { timeout: 45000 });
      await page.waitForTimeout(2200);
      await page.locator('#area-title').evaluate(el => el.classList.remove('show'));
      await page.screenshot({ path: path.join(root, `test-results/${name}-scene.png`) });
    }
    assert.deepEqual(errors, []);
    console.log('Pavilion, Rain Crown and Seed Vault real-scene browser checks passed');
    return;
  }
  if (process.argv.includes('--pavilion-foes-only')) {
    await page.evaluate(() => Online.send({ type: 'debug', ref: 631,
      command: { op: 'teleport', zone: 31, x: 30, y: 73 } }));
    await page.waitForFunction(() => Field.zone === 31 && Field.slimes.length === 12 &&
      !!Field.cathedralSprites?.img?.pavilion_sovereign, null, { timeout: 15000 });
    const cast = await page.evaluate(() => {
      const kinds = ['pavilion_foldling', 'pavilion_inkmoth', 'pavilion_silkguard',
        'pavilion_mirror', 'pavilion_weaver', 'pavilion_sovereign'];
      return kinds.map(kind => ({ kind,
        count: Field.slimes.filter(s => s.kind === kind).length,
        width: Field.cathedralSprites.img[kind]?.naturalWidth,
        height: Field.cathedralSprites.img[kind]?.naturalHeight,
        name: Field.enemyName(kind),
        frame: Field._debug.enemyFrame(Field.slimes.find(s => s.kind === kind)) }));
    });
    assert.deepEqual(cast.map(e => e.count), [3, 3, 3, 1, 1, 1]);
    assert.ok(cast.every(e => e.width === 768 && e.height === 480 && e.name && e.frame));
    assert.deepEqual(errors, []);
    await page.waitForTimeout(6500);
    await page.screenshot({ path: path.join(root, 'test-results/thousandfold-pavilion-foes.png') });
    console.log('Thousandfold real-sprite browser check passed');
    return;
  }
  if (process.argv.includes('--entrance-only')) {
    await page.evaluate(() => Online.send({ type: 'debug', ref: 601,
      command: { op: 'teleport', zone: 20, x: 106, y: 25 } }));
    await page.waitForFunction(() => Field.zone === 20 && Math.hypot(Field.hero.x - 106, Field.hero.y - 25) < 2);
    await page.screenshot({ path: path.join(root, 'test-results/elder-hollow-entrance.png') });
    assert.deepEqual(errors, []);
    console.log('Elder Hollow entrance capture passed');
    return;
  }
  const elderScene = await page.evaluate(async () => {
    const response = await fetch('assets/music_elder_hollow.mp3');
    const context = new AudioContext();
    const score = await context.decodeAudioData(await response.arrayBuffer());
    await context.close();
    return { status: response.status, seconds: score.duration,
      art: !!City.art.elder_wall && !!City.art.elder_lantern && !!City.art.elder_crown &&
        typeof ElderHollowArt.portal === 'function' && typeof window.createElderHollowMusic === 'function' };
  });
  assert.equal(elderScene.status, 200);
  assert.ok(elderScene.art && elderScene.seconds > 90 && elderScene.seconds < 93);
  const maps = await page.evaluate(() => Field._debug.zones.slice(29,40).map(z => ({
    name: z.name, sealed: z.sealedTemplate, copies: z.copies, rooms: z.rooms?.length,
    portals: z.portals.map(p => p.to), theme: z.theme,
  })));
  assert.deepEqual(maps.map(z => z.name), ['The Eye Below', 'The Elder Hollow',
    'The Thousandfold Pavilion', 'Temple of the Rain Crown', 'The Seed Vault',
    'The Sunken Astrolabe', 'The Thunderheart Gate', 'The Blooming Labyrinth',
    'The Solar Crucible', 'The Amber Archive', 'The Silent Solstice']);
  assert.ok(maps.every((z, i) => !z.sealed && z.copies === 4 && z.rooms >= 10 &&
    z.theme === ['eye_below', 'elder_hollow', 'thousandfold', 'rain_crown', 'seed_vault', 'sunken_astrolabe','thunderheart_gate','blooming_labyrinth','solar_crucible','amber_archive','silent_solstice'][i] &&
    z.portals.length === 2 && z.portals[0] === [19, 20, 21, 22, 24, 25, 27, 28, 28, 28, 28][i]));
  await page.keyboard.press('m');
  assert.equal(await page.locator('.wm-tile').count(), 40);
  assert.equal(await page.locator('.wm-tile[data-zone="29"], .wm-tile[data-zone="30"], .wm-tile[data-zone="31"], .wm-tile[data-zone="32"], .wm-tile[data-zone="33" ], .wm-tile[data-zone="34" ]').count(), 6);
  assert.equal(await page.locator('.wm-tile[data-zone="35"]').count(),1);
  assert.equal(await page.locator('.wm-tile[data-zone="36"]').count(),1);
  assert.equal(await page.locator('.wm-tile[data-zone="37"], .wm-tile[data-zone="38"], .wm-tile[data-zone="39"]').count(),3);
  assert.ok(await page.evaluate(() => [...document.querySelectorAll('.wm-roads [data-road]')].every(r =>
    r.dataset.road.split('-').every(n => Number(n) < 40))));
  await page.keyboard.press('m');
  for (let i = 0; i < maps.length; i++) {
    const zone = 29 + i;
    const spot = await page.evaluate(zone => Field._debug.zones[zone].spawn, zone);
    await page.evaluate(([zone, x, y]) => Online.send({ type: 'debug', ref: 520 + zone,
      command: { op: 'teleport', zone, x, y } }), [zone, spot.x, spot.y]);
    await page.waitForFunction(zone => Field.zone === zone, zone, { timeout: 10000 });
    assert.equal(await page.evaluate(() => Field._debug.zones[Field.zone].theme), ['eye_below','elder_hollow','thousandfold','rain_crown','seed_vault','sunken_astrolabe','thunderheart_gate','blooming_labyrinth','solar_crucible','amber_archive','silent_solstice'][i]);
    if (i < 2 && process.env.REAL_SPRITES === '1') {
      await page.screenshot({ path: path.join(root, `test-results/${i ? 'elder-hollow' : 'eye-below'}-walkable.png`) });
    }
    const returnGate = await page.evaluate(zone => Field._debug.zones[zone].portals[0], zone);
    await page.evaluate(p => Online.send({ type: 'move', x: p.x, y: p.y }), returnGate);
    await page.waitForFunction(parent => Field.zone === parent, returnGate.to, { timeout: 15000 });
    assert.equal(await page.evaluate(() => Field.zone), returnGate.to);
  }
  await page.evaluate(() => Online.send({ type: 'debug', ref: 601,
    command: { op: 'teleport', zone: 20, x: 106, y: 25 } }));
  await page.waitForFunction(() => Field.zone === 20 && Math.hypot(Field.hero.x - 106, Field.hero.y - 25) < 2);
  if (process.env.REAL_SPRITES === '1') {
    await page.screenshot({ path: path.join(root, 'test-results/elder-hollow-entrance.png') });
  }
  await page.keyboard.press('m');
  await page.locator('.wm-tile[data-zone="20"]').click();
  assert.equal(await page.locator('.wm-gate[data-portal="sun_elder_gate"]').count(), 1);
  assert.equal(await page.locator('.wm-sealed').filter({ hasText: 'Elder Hollow' }).count(), 0);
  assert.deepEqual(errors, []);
  console.log('Sealed dungeon map UI checks passed for all eleven templates');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
