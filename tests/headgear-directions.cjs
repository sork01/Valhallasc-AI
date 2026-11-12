// Real saved head layers, bounded to one class at a time. No sprite generation.
const assert = require('node:assert/strict');
const fs = require('node:fs'), http = require('node:http'), path = require('node:path');
const { chromium } = require('playwright');
require('./lib/touch.cjs').requireMemoryLimit();
const root = path.resolve(__dirname, '../client'), out = path.resolve(__dirname, '../test-results/headgear-directions');
fs.mkdirSync(out, { recursive: true });
const cls = process.env.HAT_CLASS || 'mage';
const server = http.createServer((req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname;
  if (name === '/') { res.setHeader('Content-Type','text/html'); return res.end('<!doctype html><canvas id="sheet" width="1280" height="1800"></canvas>' + ['items','magesprite','warriorsprite','assassinsprite','priestsprite','huntersprite'].map(s=>`<script src="/${s}.js"></script>`).join('')); }
  const file = path.resolve(root, '.' + name);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  if (name.endsWith('_sprites.txt')) {
    const meta = JSON.parse(fs.readFileSync(file));
    meta.parts = Object.fromEntries(Object.entries(meta.parts).filter(([k]) => k === 'body' || k.startsWith('head_')));
    meta.lazyParts = Object.keys(meta.parts).filter(k=>k.startsWith('head_'));
    if (process.env.MUTATE === 'head') delete meta.headFrames;
    res.setHeader('Content-Type','application/json'); return res.end(JSON.stringify(meta));
  }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});
(async()=>{
  let browser; const results=[];
  try {
    await new Promise(r=>server.listen(0,'127.0.0.1',r));
    browser = await chromium.launch({ headless:true, args:['--disable-gpu'] });
    for (const gender of ['male','female']) {
      const page=await browser.newPage({viewport:{width:1280,height:900}}), errors=[];
      page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);}); await page.goto(`http://127.0.0.1:${server.address().port}/`);
      const result=await page.evaluate(async({cls,gender})=>{
        const Base={mage:MageSprite,warrior:WarriorSprite,assassin:AssassinSprite,priest:PriestSprite,hunter:HunterSprite}[cls], C=Base.variant({gender});
        const look={class:cls,gender,[cls+'Armor']:'none',[cls+'Weapon']:'none',head:'none',shoulders:'none',gloves:'none',pants:'none',necklace:'none',accessory:'none',cloak:'none'};
        const sprite=await C.load(look), meta=sprite.meta, dirs=[1,2,6,7];
        const sheet=document.getElementById('sheet'), g=sheet.getContext('2d');
        g.fillStyle='#293840';g.fillRect(0,0,sheet.width,sheet.height); g.font='14px sans-serif';g.fillStyle='#fff';
        const variants=Object.keys(meta.parts).filter(k=>k.startsWith('head_'));
        let frames=0, minimumVisible=Infinity, audited=0, row=0;
        const bareFrames = {};
        for (const [clip,spec] of Object.entries(meta.clips)) for(const dir of dirs) for(let k=0;k<spec.n;k++) bareFrames[`${clip}/${dir}/${k}`]=sprite.frame(clip,dir,k);
        for (const part of variants) {
          await sprite.source.ensure(part);sprite.set({...look,head:part.slice(5)});
          const image=await createImageBitmap(await (await fetch('/assets/'+meta.parts[part].png)).blob());
          const raw=document.createElement('canvas'); raw.width=160;raw.height=160;const r=raw.getContext('2d',{willReadFrequently:true});
          for (const [clip,spec] of Object.entries(meta.clips)) for (const dir of dirs) for(let k=0;k<spec.n;k++) {
            const bare=bareFrames[`${clip}/${dir}/${k}`], worn=sprite.frame(clip,dir,k);
            let visible=0; for(let p=0;p<bare._px.length;p+=4) if(worn._px[p]!==bare._px[p]||worn._px[p+1]!==bare._px[p+1]||worn._px[p+2]!==bare._px[p+2]||worn._px[p+3]!==bare._px[p+3]) visible++;
            if(visible<3) throw Error(`Hidden hat ${cls}/${gender}/${part}/${clip}/${dir}/${k}: ${visible}`);
            minimumVisible=Math.min(minimumVisible,visible);frames++;
            const f=sprite.source.parts[part][`${clip}/${dir}/${k}`];
            for(let yy=0;yy<f.h;yy++)for(let xx=0;xx<f.w;xx++)if(f.pixels[(yy*f.w+xx)*4+3]&&(f.x+xx===0||f.y+yy===0||f.x+xx===159||f.y+yy===159))throw Error(`Hat clipped at atlas edge ${part}/${clip}/${dir}/${k}`);
            if(clip==='idle' && k===0) {
              r.clearRect(0,0,160,160);r.drawImage(image,0,(spec.row0+dir)*160,160,160,0,0,160,160);
              const original=r.getImageData(0,0,160,160).data;
              let changes=0;for(let y=0;y<160;y++)for(let x=0;x<160;x++){
                const a=original[(y*160+x)*4+3];const b=x>=f.x&&x<f.x+f.w&&y>=f.y&&y<f.y+f.h?f.pixels[((y-f.y)*f.w+x-f.x)*4+3]:0;
                if(a!==b)changes++;
              }
              if(changes<8)throw Error(`Stationary camera-facing hat ${part}/${dir}: ${changes}`);
              audited++;
              if(row<10) {
                const col=dirs.indexOf(dir), x=col*320;
                const before=new Uint8ClampedArray(bare._px);const depth=bare._z.slice();
                const zd=await createImageBitmap(await (await fetch('/assets/'+meta.parts[part].depth)).blob());
                r.clearRect(0,0,160,160);r.drawImage(zd,0,(spec.row0+dir)*160,160,160,0,0,160,160);const zz=r.getImageData(0,0,160,160).data;zd.close();
                for(let p=0;p<160*160;p++)if(original[p*4+3]&&zz[p*4]*256+zz[p*4+1]<=depth[p]){const lut=sprite.tintLut.get(part);before.set(lut?[...lut.paint(original[p*4],original[p*4+1],original[p*4+2]),255]:original.subarray(p*4,p*4+4),p*4);}
                r.putImageData(new ImageData(before,160,160),0,0);
                g.imageSmoothingEnabled=false;g.drawImage(raw,35,0,90,95,x,row*180+22,160,150);g.drawImage(worn,35,0,90,95,x+160,row*180+22,160,150);
                g.fillText(`${part.slice(5)} ${meta.dirs[dir]}: old / fixed`,x+4,row*180+17);
              }
            }
          }
          row++; image.close(); delete sprite.source.parts[part]; sprite.cache.clear();
        }
        return {cls,gender,variants:variants.length,frames,audited,minimumVisible,png:sheet.toDataURL()};
      },{cls,gender});
      assert.deepEqual(errors,[]); fs.writeFileSync(path.join(out,`${cls}-${gender}.png`),Buffer.from(result.png.split(',')[1],'base64'));delete result.png;
      results.push(result);console.log(JSON.stringify(result)); await page.close();
    }
    fs.writeFileSync(path.join(out,`${cls}.json`),JSON.stringify(results,null,2));
  } finally {await browser?.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
