'use strict';
// Native festive scenery; encounter availability and rewards come from the server.
(() => {
 const {ellipse,line,prism,poly}=City.kit;
 const star=(g,x,y,r)=>{const p=[];for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,k=i%2?r*.45:r;p.push([x+Math.cos(a)*k,y+Math.sin(a)*k]);}poly(g,p,'#ffe49a','#856334',2);};
 City.art.christmasTree={box:[220,320,110,280],occludes:true,draw(g,o){
  ellipse(g,0,3,76,22,'#203e3844');prism(g,.55,.55,38,'#b78858','#886043','#634737');
  for(const [top,bottom,w]of[[-142,-31,78],[-188,-87,59],[-232,-145,39]]){
   const pts=[[0,top],[-w*.52,top+31],[-w*.34,top+34],[-w,bottom-12],[-w*.6,bottom-10],[-w*.8,bottom],[0,bottom+12],[w*.8,bottom],[w*.6,bottom-10],[w,bottom-12],[w*.34,top+34],[w*.52,top+31]];
   poly(g,pts,'#2f7951','#234337',2);poly(g,[[0,top],[w*.52,top+31],[w*.34,top+34],[w,bottom-12],[w*.6,bottom-10],[w*.8,bottom],[0,bottom+12]],'#286344',null);
   line(g,[[-w*.7,bottom-15],[0,bottom-2],[w*.7,bottom-15]],'#e6c46e',3);
  }
  for(const [i,[x,y]]of[[-47,-60],[-22,-81],[17,-63],[49,-73],[-27,-119],[20,-129],[-12,-173],[16,-185],[2,-210]].entries()){
   ellipse(g,x,y,6,7,[o.color||'#df5751','#f2d580','#a3d9e7'][i%3]);ellipse(g,x-2,y-2,1.5,2,'#fff4c2');
  }
  star(g,0,-242,17);line(g,[[-44,-47],[-37,-38],[-30,-47]],'#e76d63',6);
 }};
 City.art.christmasGrandTree={box:[320,440,160,390],occludes:true,draw(g,o){g.save();g.scale(1.35,1.35);City.art.christmasTree.draw(g,o);g.restore();}};
 City.art.greatChristmasTree={box:[480,620,240,560],occludes:true,draw(g,o){g.save();g.scale(2,2);City.art.christmasTree.draw(g,o);g.restore();}};
 City.art.christmasGifts={box:[145,120,72,98],draw(g){
  for(const [x,y,h,color]of[[-23,-8,29,'#be4352'],[20,4,38,'#389674'],[-8,17,23,'#d0a34f']]){g.save();g.translate(x,y);prism(g,.72,.65,h,color,color,'#79536a');line(g,[[0,0],[0,-h]],'#ffe4a0',5);line(g,[[-12,-h+1],[0,-h-7],[12,-h+1]],'#fbe4b6',3);g.restore();}
 }};
 City.art.christmasWreath={box:[110,120,55,80],draw(g,o){
  g.strokeStyle='#244d3c';g.lineWidth=16;g.beginPath();g.ellipse(0,-12,27,28,0,0,Math.PI*2);g.stroke();
  for(let i=0;i<14;i++){const a=i*Math.PI/7;ellipse(g,Math.cos(a)*27,-12+Math.sin(a)*28,8,6,i%2?'#42815a':'#619d69');if(i%3===0)ellipse(g,Math.cos(a)*26,-12+Math.sin(a)*27,4,4,'#e85555');}
  poly(g,[[-2,12],[-20,5],[-17,25],[0,18],[17,25],[20,5]],'#d84f58','#72374b',2);ellipse(g,0,16,6,6,'#f1d88e');
 }};
 City.art.christmasGarland={box:[166,115,83,80],draw(g,o){
  line(g,[[-67,-22],[-35,-9],[0,-4],[35,-9],[67,-22]],'#2e6247',14);
  for(let i=0;i<15;i++){const x=-65+i*9.3,y=-22+18*(1-(x/70)**2);line(g,[[x-7,y-6],[x,y+3],[x+6,y-4]],i%2?'#518e60':'#75a371',4);if(i%3===0)ellipse(g,x,y+5,4,5,o.color||'#d95352');}
  poly(g,[[-2,-4],[-18,-15],[-16,7],[0,0],[16,7],[18,-15]],'#dd535d','#793b49',2);
 }};
 City.art.christmasLights={box:[200,175,100,150],draw(g,o){
  for(const x of [-72,72]){line(g,[[x,0],[x,-133]],'#426454',7);star(g,x,-135,8);}
  line(g,[[-72,-125],[-36,-107],[0,-101],[36,-107],[72,-125]],'#435940',3);
  for(let i=0;i<9;i++){const x=-64+i*16,y=-123+21*(1-(x/72)**2);line(g,[[x,y],[x,y+9]],'#31513d',2);ellipse(g,x,y+12,5,7,['#ffe3a2','#eb6862','#83c9b9'][i%3]);}
 }};
 City.art.christmasSnowman={box:[145,180,72,155],draw(g){
  ellipse(g,0,0,36,12,'#285b6255');ellipse(g,0,-25,29,25,'#e2f0df','#6b8e8b',2);ellipse(g,0,-61,22,24,'#f2f8e8','#6b8e8b',2);ellipse(g,0,-93,17,18,'#f3f8e9','#6b8e8b',2);
  for(const x of [-6,6])ellipse(g,x,-96,2.2,3,'#364854');poly(g,[[0,-92],[19,-87],[0,-85]],'#ed9857','#a36a40',1);
  for(const y of [-48,-61,-73])ellipse(g,0,y,2.5,3,'#405763');line(g,[[-18,-78],[18,-78],[12,-50]],'#c94e5a',8);
  for(const side of [-1,1])line(g,[[side*20,-60],[side*39,-80],[side*40,-91]],'#80604c',4);
  ellipse(g,0,-110,23,5,'#9d3b51');poly(g,[[-15,-111],[-12,-140],[12,-132],[16,-111]],'#d15b61','#763945',2);ellipse(g,14,-132,6,6,'#f6f2d8');
 }};
 City.art.christmasLantern={...City.art.festivalLantern,draw(g,o){City.art.festivalLantern.draw(g,o);line(g,[[-9,-42],[0,-47],[10,-41]],'#4e8b60',9);ellipse(g,0,-44,5,6,'#e85a55');}};
 City.art.christmasCandles={...City.art.festivalCandles,draw(g,o){City.art.festivalCandles.draw(g,o);line(g,[[-32,-5],[0,-9],[32,-5]],'#41805a',9);for(const x of [-20,0,20])ellipse(g,x,-7,4,4,'#d95459');}};
 let state=null,rolls={},day=0,source=null,loading=null;
 window.Christmas={
  sync(next,nextRolls,seasons){state=next;rolls=nextRolls||{};day=seasons?.find(s=>s.id==='christmas')?.day||0;},
  get source(){return source;},
  load(){if(source)return Promise.resolve();if(loading)return loading;
   if(window.__valhallaTestSprites){const c=document.createElement('canvas');c.width=768;c.height=480;const g=c.getContext('2d');g.fillStyle='#90b94e';for(let y=0;y<5;y++)for(let x=0;x<8;x++)g.fillRect(x*96+28,y*96+15,40,75);source={meta:{frame:[96,96],anchor:[48,90],clips:{idle:{fps:6,n:6,row:0},walk:{fps:10,n:8,row:1},attack:{fps:12,n:8,row:2},hurt:{fps:10,n:4,row:3},die:{fps:8,n:8,row:4}}},img:{grinch:c}};return Promise.resolve();}
   loading=fetch('assets/christmas.txt').then(r=>r.json()).then(async meta=>{const img=new Image();img.src='assets/christmas_grinch.png';await img.decode();source={meta,img:{grinch:img}};}).catch(()=>{}).finally(()=>{loading=null;});return loading;
  },
  objects(zone){return state&&zone===2?[{kind:'greatChristmasTree',x:state.summonX,y:state.summonY,r:0,color:'#e55755'}]:[];},
  drawFloor(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y);g.save();g.strokeStyle=state.active?'#ee7770':'#9ad6b9';g.fillStyle='#b1e9e329';g.lineWidth=4;g.beginPath();g.ellipse(x,y,state.radius*62.225,state.radius*31.112,0,0,Math.PI*2);g.fill();g.stroke();g.restore();},
  drawLabel(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y,130);g.save();g.font='20px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#193a3d';g.lineWidth=5;g.fillStyle='#fff0b2';
   const lines=[state.active?`The Grinch · Level ${state.level}`:'Five fighters · highest party level',rolls.christmas_hunt===day?'Daily mount roll used · resets at Stockholm midnight':'Daily Red-nosed Reindeer chance: 5% per hero'];
   for(const[i,t]of lines.entries()){const text=window.Locale?.translate(t)||t;g.strokeText(text,x,y+i*25);g.fillText(text,x,y+i*25);}g.restore();
  },
  drawNpc(g,n,t,top){const scale=n.look?.scale||1,pose=window.NpcArt?.frame(n,t),bob=pose?.clip==='walk'?Math.abs(Math.sin(pose.step*Math.PI/4))*1.4:0;g.save();
   const hy=-top+7-bob,y=-top*.58;line(g,[[-11*scale,y],[12*scale,y],[8*scale,y+22*scale]],'#cc4c58',7*scale);ellipse(g,0,y,4*scale,4*scale,'#edcf87');
   poly(g,[[-17*scale,hy],[-12*scale,hy-29*scale],[8*scale,hy-23*scale],[19*scale,hy-10*scale],[5*scale,hy-17*scale],[16*scale,hy]],'#d85761','#783c4b',1.5);line(g,[[-17*scale,hy],[16*scale,hy]],'#f1f1da',7*scale);ellipse(g,19*scale,hy-10*scale,5*scale,5*scale,'#faf2d8');g.restore();
  }
 };
})();
