// Contact sheet through the real compositor: one class, chosen gear, chosen directions. Run through test-touch-bounded.sh.
// Env: OUT=<png> LOOKS='[{"head":"warden"},{"cloak":"travel"}]' CLS=hunter GENDER=male CLIP=idle K=0 Z=2 DIRS='[0,1,2,3,4,5,6,7]'; NOHEAD=1 leaves hats unturned; BOX='[x,y,w,h]' picks the part of the frame shown (default the upper body).
const fs=require('node:fs'),http=require('node:http'),path=require('node:path');
const {chromium}=require('playwright');require('./lib/touch.cjs').requireMemoryLimit();
const root=path.resolve(__dirname,'../client'),out=process.env.OUT;
const cls=process.env.CLS||'hunter',gender=process.env.GENDER||'male',looks=JSON.parse(process.env.LOOKS),clip=process.env.CLIP||'idle',K=+process.env.K||0,Z=+process.env.Z||2,DIRS=JSON.parse(process.env.DIRS||'[0,1,2,3,4,5,6,7]'),BOX=JSON.parse(process.env.BOX||'[45,5,70,75]');
const server=http.createServer((req,res)=>{const name=new URL(req.url,'http://localhost').pathname;
 if(name==='/'){res.setHeader('Content-Type','text/html');return res.end('<!doctype html><canvas id="sheet"></canvas>'+['items','magesprite','warriorsprite','assassinsprite','priestsprite','huntersprite'].map(s=>`<script src="/${s}.js"></script>`).join(''));}
 const file=path.resolve(root,'.'+name);if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){res.writeHead(404);return res.end();}
 if(name.endsWith('_sprites.txt')&&process.env.NOHEAD){const m=JSON.parse(fs.readFileSync(file));delete m.headFrames;res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(m));}
 res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.png')?'image/png':'text/plain');fs.createReadStream(file).pipe(res);});
(async()=>{let browser;try{await new Promise(r=>server.listen(0,'127.0.0.1',r));browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage();page.on('pageerror',e=>console.error(e.message));await page.goto(`http://127.0.0.1:${server.address().port}/`);
 const png=await page.evaluate(async({cls,gender,looks,clip,K,Z,DIRS,BOX})=>{
  const Base={mage:MageSprite,warrior:WarriorSprite,assassin:AssassinSprite,priest:PriestSprite,hunter:HunterSprite}[cls],C=Base.variant({gender});
  const none={class:cls,gender,[cls+'Armor']:'none',[cls+'Weapon']:'none',head:'none',shoulders:'none',gloves:'none',pants:'none',necklace:'none',accessory:'none',cloak:'none'};
  const sprite=await C.load(none),meta=sprite.meta,[X0,Y0,W,H]=BOX,sheet=document.getElementById('sheet');sheet.width=DIRS.length*W*Z;sheet.height=looks.length*(H*Z+18);
  const g=sheet.getContext('2d');g.fillStyle='#5a6f78';g.fillRect(0,0,sheet.width,sheet.height);g.font='13px sans-serif';g.imageSmoothingEnabled=false;
  for(const [row,extra] of looks.entries()){
   const look={...none,...extra};for(const [slot,v] of Object.entries(extra)){const part=slot.endsWith('Armor')?'armor_'+v:slot.endsWith('Weapon')?'weapon_'+v:slot+'_'+v;if(meta.parts[part])await sprite.source.ensure(part).catch(()=>{});}
   sprite.set(look);sprite.cache.clear();
   for(const [col,dir] of DIRS.entries()){const f=sprite.frame(clip,dir,K);g.drawImage(f,X0,Y0,W,H,col*W*Z,row*(H*Z+18)+18,W*Z,H*Z);g.fillStyle='#fff';g.fillText(`${Object.values(extra).join('+')} ${meta.dirs[dir]}`,col*W*Z+4,row*(H*Z+18)+13);}
  }
  return sheet.toDataURL();
 },{cls,gender,looks,clip,K,Z,DIRS,BOX});
 fs.writeFileSync(out,Buffer.from(png.split(',')[1],'base64'));console.log(out);
}finally{await browser?.close();await new Promise(r=>server.close(r));}})().catch(e=>{console.error(e);process.exitCode=1;});
