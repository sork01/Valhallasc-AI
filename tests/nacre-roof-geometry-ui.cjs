// Native Nacre roof/pillar geometry and Alderhaven's misplaced doorstep. Private server only.
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 await w.start();browser=await chromium.launch({headless:true});const p=await browser.newPage({viewport:{width:1280,height:800}});p.on('pageerror',e=>errors.push(e.message));await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;});await p.goto(w.url);
 const result=await p.evaluate(only=>{
  const zone=WORLD_MAP.zones[8],kinds=['nacrehouse','nacreinn','nacrepalace','nacrearchive','nacrecathedral','nacrestall','nacregarden','nacrefountain','nacrememorial'],all=zone.objects.filter(o=>kinds.includes(o.kind)),variants=new Map();
  for(const o of all){const key=JSON.stringify([o.kind,o.width,o.depth,o.color,o.v]);if(!variants.has(key)&&(!only||only.includes(o.kind)))variants.set(key,o);}
  const orig={},ellipses=new WeakMap(),paths=new WeakMap(),proto=CanvasRenderingContext2D.prototype,bad=[],stats={};let active=null;
  for(const name of ['beginPath','moveTo','lineTo','closePath']){orig[name]=proto[name];proto[name]=function(...a){if(name==='beginPath')paths.set(this,[]);else if(name!=='closePath'){const m=this.getTransform();paths.get(this)?.push([m.a*a[0]+m.c*a[1]+m.e,m.b*a[0]+m.d*a[1]+m.f]);}return orig[name].apply(this,a);};}
  orig.ellipse=proto.ellipse;proto.ellipse=function(x,y,...args){const m=this.getTransform();ellipses.set(this,[m.a*x+m.c*y+m.e,m.b*x+m.d*y+m.f]);return orig.ellipse.call(this,x,y,...args);};
  orig.fill=proto.fill;proto.fill=function(...args){if(active){const pts=paths.get(this)||[],color=this.fillStyle;
   if(color==='#a3bfc0')active.rims.push(pts);
   if(color==='#e0eee4')active.caps.push(pts);
   if(color==='#e2d4ba')active.steps.push(pts);
   if(color==='#21446b')active.rose.push(ellipses.get(this));
   if(color==='#e3fff4')active.pearls.push(ellipses.get(this));
  }return orig.fill.apply(this,args);};
  const canvas=document.createElement('canvas');canvas.width=1500;canvas.height=1300;const g=canvas.getContext('2d');
  try{
   for(const [index,o]of[...variants.values()].entries()){
    active={rims:[],caps:[],steps:[],rose:[],pearls:[]};City.drawObject(g,{...o,label:'roof-check-'+index},700,1050);
    const box=City.art[o.kind].box,point=(x,y,z)=>{const p=City.kit.iso(x,y,z);return[(p[0]+box[2])*2,(p[1]+box[3])*2];};
    if(['nacrehouse','nacreinn','nacrearchive','nacrepalace','nacrecathedral','nacrestall'].includes(o.kind)){
     const wall=o.kind==='nacrehouse'?100:o.kind==='nacrecathedral'?193:o.kind==='nacrestall'?130:160;
     const extra=o.kind==='nacrecathedral'?.3:o.kind==='nacrestall'?.45:.28;
     const a=point(-(o.width+extra)/2,(o.depth+extra)/2,wall),b=point((o.width+extra)/2,(o.depth+extra)/2,wall);
     if(!active.rims.some(r=>r.some(p=>Math.hypot(p[0]-a[0],p[1]-a[1])<.01)&&r.some(p=>Math.hypot(p[0]-b[0],p[1]-b[1])<.01)))bad.push({kind:o.kind,error:'Roof does not rest on its authored wall-top/eaves'});
    }
    if(['nacrepalace','nacrecathedral'].includes(o.kind)){
     const z=o.kind==='nacrepalace'?10:18;
     for(const x of[-o.width/2+.15,o.width/2-.15]){
      const expected=point(x,o.depth/2+.12,z+9);
      if(!active.caps.some(pts=>{const mean=pts.reduce((m,p)=>[m[0]+p[0]/pts.length,m[1]+p[1]/pts.length],[0,0]);return Math.hypot(mean[0]-expected[0],mean[1]-expected[1])<.1;}))bad.push({kind:o.kind,error:'Pillar plinth is not anchored to the front floor plane'});
     }
    }
    if(o.kind==='nacrecathedral'){
     const expect=point(0,(o.depth+.3)/2,193+165*.58);if(!active.rose.some(p=>Math.hypot(p[0]-expect[0],p[1]-expect[1])<.01))bad.push({kind:'rose',error:'Rose window is detached from the shell fan face'});
    }
    if(o.kind==='nacrepalace'){
     const expect=point(0,0,316);if(!active.pearls.some(p=>Math.hypot(p[0]-expect[0],p[1]-expect[1])<.01))bad.push({kind:'pearl',error:'Palace pearl does not rest on the roof ridge'});
    }
    for(const cap of active.caps){const xs=cap.map(p=>p[0]),ys=cap.map(p=>p[1]);if(Math.abs((Math.max(...xs)-Math.min(...xs))/(Math.max(...ys)-Math.min(...ys))-2)>.01)bad.push({kind:o.kind,error:'Column capital ignores 2:1 world-ground projection'});}
    stats[o.kind]=(stats[o.kind]||0)+1;
   }
   // The old centre-origin doorstep painted a ledge on the wall. Its rear edge belongs to the doorway.
   for(const [index,o]of WORLD_MAP.objects.filter(o=>['house','chapel'].includes(o.kind)).entries()){
    active={rims:[],caps:[],steps:[],rose:[],pearls:[]};City.drawObject(g,{...o,label:'alder-step-'+index},700,1000);const box=City.spriteBox(o),corners=[[-.625,o.depth/2,8],[.625,o.depth/2+.5,8]].map(p=>{const q=City.kit.iso(...p);return[(q[0]+box[2])*2,(q[1]+box[3])*2];});
    if(!active.steps.some(pts=>corners.every(q=>pts.some(p=>Math.hypot(p[0]-q[0],p[1]-q[1])<.01))))bad.push({kind:'alderhaven',error:'Doorstep/ledge remains at the house centre'});
   }
  }finally{active=null;for(const[name,fn]of Object.entries(orig))proto[name]=fn;}
  const sheet=document.createElement('canvas');sheet.width=2200;sheet.height=1800;const sg=sheet.getContext('2d');sg.fillStyle='#203a42';sg.fillRect(0,0,sheet.width,sheet.height);
  for(const [i,kind]of kinds.entries()){
   const o=all.find(o=>o.kind===kind),box=City.art[kind].box,s=Math.min(.9,490/box[0],500/box[1]),x=i%4*550+275,y=Math.floor(i/4)*600+530;
   sg.save();sg.translate(x,y);sg.scale(s,s);City.drawObject(sg,o,0,0);sg.restore();sg.fillStyle='#ffedc0';sg.font='18px sans-serif';sg.textAlign='center';sg.fillText(kind,x,y+35);
  }
  // Actual cached alpha at the box border catches larger rotated roofs/caps clipping.
  const edges=[];
  for(const o of variants.values()){
   const box=City.art[o.kind].box,c=document.createElement('canvas');c.width=box[0];c.height=box[1];const cg=c.getContext('2d');City.drawObject(cg,o,box[2],box[3]);const data=cg.getImageData(0,0,c.width,c.height).data;let hit=0;
   for(let x=0;x<c.width;x++)hit+=!!data[x*4+3]+!!data[((c.height-1)*c.width+x)*4+3];for(let y=0;y<c.height;y++)hit+=!!data[y*c.width*4+3]+!!data[(y*c.width+c.width-1)*4+3];if(hit)edges.push({kind:o.kind,hit});c.width=c.height=0;
  }
  return{bad,stats,edges,placed:all.length,variants:variants.size,sheet:sheet.toDataURL()};
 },process.env.ONLY?.split(',')||null);
 for(const [kind,n]of Object.entries(result.stats))check(result.bad.every(b=>b.kind!==kind),`${kind}: ${n} variants have seated shell roofs and world-aligned columns`);
 check(!result.bad.some(b=>b.kind==='rose'),'Cathedral rose window follows the shell’s actual fan face');
 check(!result.bad.some(b=>b.kind==='pearl'),'Palace pearl rests on the shell ridge');
 check(!result.bad.some(b=>b.kind==='alderhaven'),'All four Alderhaven doorsteps/ledges are anchored at their doors');
 check(result.edges.length===0,'No roof or pillar is clipped by its cached sprite box: '+JSON.stringify(result.edges));check(errors.length===0,'No browser errors: '+errors.join('; '));
 fs.writeFileSync(path.join(w.runDir,'nacre-shells-pillars-fixed.png'),Buffer.from(result.sheet.split(',')[1],'base64'));fs.writeFileSync(path.join(w.runDir,'geometry-summary.json'),JSON.stringify({...result,sheet:undefined},null,2));console.log(`nacre-roof-geometry-ui: ${checks} checks / ${result.variants} variants / ${result.placed} objects; ${w.runDir}`);
 }finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
