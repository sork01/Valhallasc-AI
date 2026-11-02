// Audit actual painted opening pixels across every authored city building variant.
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 await w.start();browser=await chromium.launch({headless:true});const p=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;});await p.goto(w.url);
 const result=await p.evaluate(()=>{
  const kinds=['aetherhouse','nacrehouse','nacreinn','nacrepalace','nacrearchive','nacrecathedral','astralhouse','observatory','house','chapel','tower'];
  const objects=[WORLD_MAP,...WORLD_MAP.zones].flatMap(z=>z.objects.filter(o=>kinds.includes(o.kind))),variants=new Map();
  for(const o of objects){const k=JSON.stringify([o.kind,o.width,o.depth,o.color,o.v,o.big]);if(!variants.has(k))variants.set(k,o);}
  const states=new WeakMap(),proto=CanvasRenderingContext2D.prototype,original={},bad=[],counts={};let active=null,panes=0;
  const operations=['beginPath','moveTo','lineTo','closePath','ellipse','arc','rect','quadraticCurveTo','bezierCurveTo'];
  for(const name of operations){original[name]=proto[name];proto[name]=function(...args){
   if(name==='beginPath')states.set(this,{path:new Path2D(),points:[]});
   else{const state=states.get(this);if(state){state.path[name](...args);
    const pair=(x,y)=>state.points.push([x,y]);
    if(name==='ellipse'||name==='arc'){const [x,y,r,ry]=args,extent=name==='arc'?r:r+ry;for(const a of [-1,1])for(const b of [-1,1])pair(x+a*extent,y+b*extent);}
    else if(name==='rect'){const[x,y,w,h]=args;pair(x,y);pair(x+w,y+h);}
    else for(let i=0;i+1<args.length;i+=2)pair(args[i],args[i+1]);
   }}return original[name].apply(this,args);
  };}
  const mask=document.createElement('canvas'),cg=mask.getContext('2d',{willReadFrequently:true});
  const moments=(g,state,stroke)=>{
   const m=g.getTransform(),points=state.points.map(([x,y])=>[m.a*x+m.c*y+m.e,m.b*x+m.d*y+m.f]);
   const pad=Math.ceil(g.lineWidth*Math.max(Math.abs(m.a)+Math.abs(m.c),Math.abs(m.b)+Math.abs(m.d)))+3;
   const left=Math.floor(Math.min(...points.map(p=>p[0])))-pad,top=Math.floor(Math.min(...points.map(p=>p[1])))-pad;
   mask.width=Math.ceil(Math.max(...points.map(p=>p[0])))-left+pad;mask.height=Math.ceil(Math.max(...points.map(p=>p[1])))-top+pad;
   cg.setTransform(m.a,m.b,m.c,m.d,m.e-left,m.f-top);cg.fillStyle=cg.strokeStyle='#ffffff';cg.lineWidth=g.lineWidth;
   if(stroke)original.stroke.call(cg,state.path);else original.fill.call(cg,state.path);
   const pixels=cg.getImageData(0,0,mask.width,mask.height).data;let n=0,xs=0,ys=0,xx=0,xy=0,edge=0;
   for(let y=0;y<mask.height;y++)for(let x=0;x<mask.width;x++)if(pixels[(y*mask.width+x)*4+3]>128){n++;xs+=x;ys+=y;xx+=x*x;xy+=x*y;if(!x||!y||x===mask.width-1||y===mask.height-1)edge++;}
   return{n,slope:(xy-xs*ys/n)/(xx-xs*xs/n),edge};
  };
  const expected=(color,o)=>{
   if(['aetherhouse'].includes(o.kind))return ['#6c9da8','#433e5f'].includes(color)?.5:null;
   if(['astralhouse','observatory'].includes(o.kind))return color==='#fae4af'?.5:null;
   if(o.kind.startsWith('nacre')){
    if(color==='#194958'||color==='#09192f'||color==='#1a465e'||color==='#a0fff1')return .5;
    if(color==='#256781')return active.windows++===0?.5:-.5;
   }
   if(['house','chapel'].includes(o.kind)){
    if(color==='#77513b')return .5;
    if(color==='#537787'){const front=o.width>5?Math.floor(o.width/2.2):2;return active.windows++<front?.5:-.5;}
   }
   if(o.kind==='tower')return color==='#2f3438'?.5:color==='#232a2e'?-.5:null;
   return null;
  };
  for(const op of ['fill','stroke']){original[op]=proto[op];proto[op]=function(...args){
   if(active){const color=op==='fill'?this.fillStyle:this.strokeStyle,target=expected(color,active.o);
    if(target!==null&&(op==='fill'||color==='#a0fff1')){const measure=moments(this,states.get(this),op==='stroke');panes++;active.count++;if(measure.n<15||measure.edge||Math.abs(measure.slope-target)>.09)bad.push({kind:active.o.kind,color,target,...measure});}
   }
   return original[op].apply(this,args);
  };}
  const c=document.createElement('canvas');c.width=1800;c.height=1500;const g=c.getContext('2d');let index=0;
  try{
   for(const o of variants.values()){
    active={o,windows:0,count:0};City.drawObject(g,{...o,label:'projection-check-'+index++},850,1000);if(o.kind==='nacrecathedral')City.animateObject(g,o,850,1000,2);
    if(!active.count)bad.push({kind:o.kind,error:'No painted openings checked'});counts[o.kind]=(counts[o.kind]||0)+active.count;
   }
  }finally{active=null;for(const [name,fn]of Object.entries(original))proto[name]=fn;}
  const sheet=document.createElement('canvas');sheet.width=2200;sheet.height=1800;const sg=sheet.getContext('2d');sg.fillStyle='#223c45';sg.fillRect(0,0,sheet.width,sheet.height);
  for(const [i,kind]of['house','tower','aetherhouse','nacrehouse','nacreinn','nacrepalace','nacrearchive','nacrecathedral','astralhouse','observatory'].entries()){
   const o=objects.find(o=>o.kind===kind),def=City.art[kind],box=def?.box||City.spriteBox(o),scale=Math.min(1,490/box[0],520/box[1]),x=(i%4)*550+275,y=Math.floor(i/4)*600+520;
   sg.save();sg.translate(x,y);sg.scale(scale,scale);City.drawObject(sg,o,0,0);if(kind==='nacrecathedral')City.animateObject(sg,o,0,0,2);sg.restore();sg.font='18px sans-serif';sg.fillStyle='#fff0c0';sg.textAlign='center';sg.fillText(kind,x,y+50);
  }
  return{bad:bad.slice(0,20),counts,panes,instances:objects.length,variants:variants.size,sheet:sheet.toDataURL()};
 });
 for(const kind of ['aetherhouse','nacrehouse','nacreinn','nacrepalace','nacrearchive','nacrecathedral','astralhouse','observatory','house','chapel','tower'])check(result.counts[kind]>0&&result.bad.every(b=>b.kind!==kind),`${kind}: opening pixels match their own wall’s slope; ${result.counts[kind]} openings; ${JSON.stringify(result.bad.filter(b=>b.kind===kind))}`);
 check(errors.length===0,'No browser errors: '+errors.join('; '));fs.writeFileSync(path.join(w.runDir,'building-openings-contact.png'),Buffer.from(result.sheet.split(',')[1],'base64'));fs.writeFileSync(path.join(w.runDir,'opening-projection-summary.json'),JSON.stringify({...result,sheet:undefined},null,2));console.log(`building-openings-ui: ${checks} checks, ${result.panes} openings / ${result.variants} variants / ${result.instances} placed buildings; ${w.runDir}`);
 }finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
