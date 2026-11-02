// Pixel checks for costume contact and decorations following actual isometric walls.
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 const p=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;window.__valhallaTestSprites=true;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,lowGraphics:true,lowGraphicsSet:true,touchGraphicsSuggested:true}));});
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('Christmas Fit');await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.hero.hp>0);
 await p.evaluate(()=>Online.send({type:'debug',command:{op:'season_time',unix:1797289200}}));await p.waitForFunction(()=>Seasonal.isActive('christmas'));
 const walls=await p.evaluate(()=>{
  const result=[];
  for(const kind of ['christmasWreath','christmasGarland']){
   const images=[];
   for(const z of [0,76,0,76]){
    const c=document.createElement('canvas');c.width=400;c.height=320;const g=c.getContext('2d');City.drawObject(g,{kind,z,v:0,color:'#d74848'},200,180);
    const px=g.getImageData(0,0,400,320).data,side=[[],[]];let hash=7,edge=0;
    for(let y=0;y<320;y++)for(let x=0;x<400;x++){
     const i=(y*400+x)*4;hash=(Math.imul(hash,31)+px[i]+px[i+1]+px[i+2]+px[i+3])>>>0;
     if(px[i+3]>200&&px[i+1]>px[i]*1.2&&px[i+1]>px[i+2]*1.15){if(x<185)side[0].push([x,y]);if(x>215)side[1].push([x,y]);}
     if(px[i+3]&&(x===0||y===0||x===399||y===319))edge++;
    }
    const mean=a=>a.reduce((s,p)=>[s[0]+p[0]/a.length,s[1]+p[1]/a.length],[0,0]),l=mean(side[0]),r=mean(side[1]);images.push({z,hash,slope:(r[1]-l[1])/(r[0]-l[0]),edge});
   }
   result.push({kind,images});
  }
  return result;
 });
 for(const {kind,images}of walls){check(images.filter(i=>i.z).every(i=>Math.abs(i.slope-.5)<.13),`${kind}: painted foliage follows the house wall’s 1:2 isometric slope`);check(images[0].hash===images[2].hash&&images[1].hash===images[3].hash&&images[0].hash!==images[1].hash,`${kind}: warmed sprite cache keeps wall-mounted and free-standing art distinct`);}
 let frameCount=0,oldFloating=0,total=0;
 for(const zone of [0,4,9,17]){
  const q=await p.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z].quests.find(q=>q.id.startsWith('christmas_')&&q.id!=='christmas_hunt'),zone);
  const host=await p.evaluate(([z,id])=>[WORLD_MAP,...WORLD_MAP.zones][z].npcs.find(n=>n.id===id),[zone,q.npc]);
  await p.evaluate(([zone,x,y])=>{Field.clearInput();Online.send({type:'stop'});Online.send({type:'debug',command:{op:'teleport',zone,x,y}});},[zone,host.x,host.y]);await p.waitForFunction(z=>Field.zone===z,zone);await p.waitForFunction(()=>NpcArt.readyFor(City.npcs),null,{timeout:20000});await p.waitForTimeout(300);await p.evaluate(()=>ZoneJourney.clear());
  const result=await p.evaluate(()=>{
   const people=City.npcs.filter(n=>Seasonal.hat(n)||(!n.travelStop&&!['stone','scenery'].includes(n.art)&&n.id.indexOf('meetingstone')<0));
   const c=document.createElement('canvas');c.width=320;c.height=320;const g=c.getContext('2d',{willReadFrequently:true}),bad=[];
   const contact=(n,t,talk,legacy=false)=>{
    g.clearRect(0,0,320,320);g.save();g.translate(160,260);g.scale(n.look?.scale||1,n.look?.scale||1);NpcArt.draw(g,n,t,talk);g.restore();
    let brim=null,points=[];const stroke=g.stroke,move=g.moveTo,line=g.lineTo,begin=g.beginPath;
    g.beginPath=function(){points=[];return begin.call(this);};g.moveTo=function(x,y){points.push([x,y]);return move.call(this,x,y);};g.lineTo=function(x,y){points.push([x,y]);return line.call(this,x,y);};g.stroke=function(){if(this.strokeStyle==='#f1f1da'){const m=this.getTransform();brim={points:points.map(([x,y])=>({x:m.a*x+m.c*y+m.e,y:m.b*x+m.d*y+m.f})),width:this.lineWidth};}return stroke.call(this);};
    g.save();g.translate(160,260);
    // Capture the actual production brim stroke, without covering the underlying pixels.
    const oldDraw=g.drawImage,oldFill=g.fill;g.fill=()=>{};g.stroke=function(){if(this.strokeStyle==='#f1f1da'){const m=this.getTransform();brim={points:points.map(([x,y])=>({x:m.a*x+m.c*y+m.e,y:m.b*x+m.d*y+m.f})),width:this.lineWidth};}};
    Christmas.drawNpc(g,n,t,NpcArt.top(n),talk);g.restore();g.stroke=stroke;g.moveTo=move;g.lineTo=line;g.beginPath=begin;g.fill=oldFill;g.drawImage=oldDraw;
    if(legacy){const y=260-NpcArt.top(n)+7;for(const p of brim.points)p.y=y;}
    const a=brim.points[0],b=brim.points[1],y=Math.round((a.y+b.y)/2),left=Math.max(0,Math.ceil(a.x)),right=Math.min(319,Math.floor(b.x));let count=0,minGap=320;
    for(let x=left;x<=right;x++)for(let k=-Math.ceil(brim.width/2)-2;k<=Math.ceil(brim.width/2)+2;k++){if(y+k<0||y+k>=320)continue;if(g.getImageData(x,y+k,1,1).data[3]){count++;minGap=Math.min(minGap,Math.abs(k));}}
    return{count,minGap,brim,top:NpcArt.top(n)};
   };
   let frames=0,oldFloating=0;
   const sheet=document.createElement('canvas');sheet.width=8*180;sheet.height=Math.ceil(people.length/8)*220;const sg=sheet.getContext('2d');sg.fillStyle='#20383e';sg.fillRect(0,0,sheet.width,sheet.height);
   for(const [index,base]of people.entries()){
    if(!NpcArt.manifest.npcs[base.id])continue;
    const phase=[...base.id].reduce((sum,ch)=>sum+ch.charCodeAt(0),0);
    for(const clip of ['idle','walk','talk'])for(const mirrored of clip==='walk'?[false,true]:[false])for(let step=0;step<NpcArt.manifest.clips[clip].n;step++){
     const n={...base,moving:clip==='walk',fx:mirrored?0:1,fy:mirrored?1:0},spec=NpcArt.manifest.clips[clip],t=(step-phase+spec.n*200)/spec.fps;
     const hit=contact(n,t,clip==='talk');frames++;if(hit.count<10||hit.minGap>4)bad.push({id:n.id,clip,step,mirrored,...hit});
     if(step===0&&!mirrored&&contact(n,t,clip==='talk',true).count===0)oldFloating++;
    }
    const x=(index%8)*180+90,y=Math.floor(index/8)*220+175;
    sg.save();sg.translate(x,y);sg.save();sg.scale(base.look?.scale||1,base.look?.scale||1);NpcArt.draw(sg,base,0);sg.restore();Christmas.drawNpc(sg,base,0,NpcArt.top(base));sg.restore();sg.font='11px sans-serif';sg.textAlign='center';sg.fillStyle='#fff2c7';sg.fillText(base.name,x,y+23,172);
   }
   return{people:people.length,frames,bad:bad.slice(0,10),oldFloating,sheet:sheet.toDataURL()};
  });
  check(result.bad.length===0,`City ${zone}: Santa brims touch the real head/headwear across idle, talk and both walking directions (${result.frames} frames): ${JSON.stringify(result.bad)}`);
  check(result.people>0&&result.frames>0,`City ${zone}: all eligible city NPC designs are covered`);
  frameCount+=result.frames;oldFloating+=result.oldFloating;total+=result.people;
  fs.writeFileSync(path.join(w.runDir,`christmas-npc-fit-${zone}.png`),Buffer.from(result.sheet.split(',')[1],'base64'));
  await p.screenshot({path:path.join(w.runDir,`christmas-fit-city-${zone}.png`)});
 }
 check(oldFloating>5,`The prior nameplate-height placement is visibly detached in ${oldFloating} sampled poses`);
 check(errors.length===0,'No browser errors: '+errors.join('; '));console.log(`christmas-attachments-ui: ${checks} checks, ${total} NPCs / ${frameCount} poses; ${w.runDir}`);
 }finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
