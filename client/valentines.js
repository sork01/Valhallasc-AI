
'use strict';
// Valentine scenery is cached native canvas art; all availability comes from snapshots.
(() => {
 const {ellipse,line,prism,poly}=City.kit;
 const heart=(g,x,y,r,color='#ed769c')=>{g.save();g.translate(x,y);g.fillStyle=color;g.strokeStyle='#813953';g.lineWidth=1.5;g.beginPath();g.moveTo(0,r);g.bezierCurveTo(-r*2,-r*.2,-r,-r*1.6,0,-r*.5);g.bezierCurveTo(r,-r*1.6,r*2,-r*.2,0,r);g.fill();g.stroke();g.restore();};
 const rose=(g,x,y,r=9)=>{for(let i=0;i<6;i++){const a=i*Math.PI/3;ellipse(g,x+Math.cos(a)*r*.4,y+Math.sin(a)*r*.4,r*.65,r*.6,i%2?'#ef7797':'#b63863');}ellipse(g,x,y,r*.4,r*.4,'#ffd0cc');};
 const wall=(g,o)=>{if(o.z>0)g.transform(Math.sqrt(.8),Math.sqrt(.2),0,1,0,0);};
 City.art.valentineRoses={box:[145,120,72,98],draw(g){
  ellipse(g,0,1,37,13,'#43263e40');prism(g,1.3,.7,22,'#c79189','#936674','#65445b');
  for(let i=0;i<7;i++){const x=(i-3)*9,y=-31-(i%3)*9;line(g,[[x*.7,-17],[x,y]],'#568266',3);ellipse(g,x-4,y+10,6,3,'#83b18b');rose(g,x,y,9);}
 }};
 City.art.valentineBouquet={...City.art.valentineRoses,draw(g,o){g.save();g.scale(1.2,1.2);City.art.valentineRoses.draw(g,o);g.restore();}};
 City.art.valentineHeart={box:[160,240,80,205],draw(g){
  ellipse(g,0,1,35,12,'#61395344');prism(g,.8,.8,23,'#f4d3bc','#ca9c97','#9d7484');line(g,[[0,-20],[0,-145]],'#a87866',6);heart(g,0,-137,40);heart(g,0,-137,27,'#ffd3d9');
  for(const side of [-1,1]){line(g,[[side*3,-85],[side*22,-54],[side*16,-27]],'#e792af',6);rose(g,side*19,-33,12);}
 }};
 City.art.valentineGrandHeart={box:[250,340,125,290],occludes:true,draw(g,o){g.save();g.scale(1.45,1.45);City.art.valentineHeart.draw(g,o);g.restore();}};
 City.art.roseheartShrine={box:[340,420,170,355],occludes:true,draw(g,o){g.save();g.scale(1.8,1.8);City.art.valentineHeart.draw(g,o);for(const side of [-1,1]){line(g,[[side*57,-5],[side*57,-93],[side*36,-112]],'#709270',8);rose(g,side*52,-70,13);heart(g,side*38,-108,12,'#f8d796');}g.restore();}};
 City.art.valentineWreath={box:[115,130,57,85],wallMounted:true,draw(g,o){g.save();wall(g,o);heart(g,0,-15,31,'#7a9a73');for(let i=0;i<8;i++){const a=i*Math.PI/4;rose(g,Math.cos(a)*24,-16+Math.sin(a)*22,7);}heart(g,0,13,10);g.restore();}};
 City.art.valentineGarland={box:[166,115,83,80],wallMounted:true,draw(g,o){g.save();wall(g,o);line(g,[[-67,-22],[-35,-9],[0,-4],[35,-9],[67,-22]],'#608761',8);for(let i=0;i<9;i++){const x=-60+i*15,y=-20+17*(1-(x/65)**2);i%2?rose(g,x,y,7):heart(g,x,y+4,7);}g.restore();}};
 City.art.valentineLights={box:[200,175,100,150],draw(g){for(const x of [-72,72]){line(g,[[x,0],[x,-133]],'#996d74',6);rose(g,x,-137,8);}line(g,[[-72,-125],[-36,-107],[0,-101],[36,-107],[72,-125]],'#9c7480',3);for(let i=0;i<9;i++){const x=-64+i*16,y=-122+21*(1-(x/72)**2);line(g,[[x,y],[x,y+9]],'#9b7582',2);heart(g,x,y+14,6,i%2?'#ffc6d5':'#ffe0a3');}}};
 City.art.valentineLantern={...City.art.festivalLantern,draw(g){ellipse(g,0,1,23,8,'#43283c44');line(g,[[0,0],[0,-138],[26,-138],[26,-120]],'#9d6b7d',7);heart(g,26,-95,26,'#ffbbd1');heart(g,26,-96,16,'#ffe4b8');rose(g,0,-44,10);}};
 City.art.valentineCandles={box:[116,120,58,103],draw(g){for(const[x,h]of[[-22,40],[0,66],[23,47]]){g.fillStyle='#edb3c1';g.fillRect(x-8,-h,16,h);ellipse(g,x,-h-7,4,10,'#ffc78b');heart(g,x,-h*.5,5,'#c84670');}for(const x of [-25,0,25])rose(g,x,-5,8);}};
 let state=null,claims={},day=0,source=null,loading=null;
 window.Valentines={
  sync(next,nextClaims,seasons){state=next;claims=nextClaims||{};day=seasons?.find(s=>s.id==='valentine')?.day||0;},
  get source(){return source;},
  load(){if(source)return Promise.resolve();if(loading)return loading;
   if(window.__valhallaTestSprites){const c=document.createElement('canvas');c.width=768;c.height=480;const g=c.getContext('2d');g.fillStyle='#90b94e';for(let y=0;y<5;y++)for(let x=0;x<8;x++)g.fillRect(x*96+28,y*96+15,40,75);source={meta:{frame:[96,96],anchor:[48,90],clips:{idle:{fps:6,n:6,row:0},walk:{fps:10,n:8,row:1},attack:{fps:12,n:8,row:2},hurt:{fps:10,n:4,row:3},die:{fps:8,n:8,row:4}}},img:{briarheart:c}};return Promise.resolve();}
   loading=fetch('assets/valentines.txt').then(r=>r.json()).then(async meta=>{const img=new Image();img.src='assets/valentines_briarheart.png';await img.decode();source={meta,img:{briarheart:img}};}).catch(()=>{}).finally(()=>{loading=null;});return loading;
  },
  objects(zone){return state&&zone===2?[{kind:'roseheartShrine',x:state.summonX,y:state.summonY,r:0,color:'#e55755'}]:[];},
  drawFloor(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y);g.save();g.strokeStyle=state.active?'#ee7770':'#9ad6b9';g.fillStyle='#b1e9e329';g.lineWidth=4;g.beginPath();g.ellipse(x,y,state.radius*62.225,state.radius*31.112,0,0,Math.PI*2);g.fill();g.stroke();g.restore();},
  drawLabel(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y,130);g.save();g.font='20px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#193a3d';g.lineWidth=5;g.fillStyle='#fff0b2';
   const lines=[state.active?`The Briarheart · Level ${state.level}`:'Five fighters · highest party level',claims.valentine_hunt===day?'Daily quest claimed · resets at Stockholm midnight':'Claim the daily quest: guaranteed Roseheart Unicorn'];
   for(const[i,t]of lines.entries()){const text=window.Locale?.translate(t)||t;g.strokeText(text,x,y+i*25);g.fillText(text,x,y+i*25);}g.restore();
  },
  head(n,t,talk=false){return window.Christmas.head(n,t,talk);},
  headTop(n,t=0){const h=this.head(n,t);return -h.y+12*h.width/17;},
  drawNpc(g,n,t,top,talk=false){
   const h=this.head(n,t,talk),s=h.width/17;g.save();g.translate(h.x,0);
   line(g,[[-10*s,h.collar],[10*s,h.collar],[7*s,h.collar+15*s]],'#e16c96',5*s);
   heart(g,0,h.collar+1,5*s,'#ffbacb');
   for(const side of [-1,1]){line(g,[[side*9*s,h.y+3*s],[side*8*s,h.y-5*s]],'#4f8b68',3*s);rose(g,side*8*s,h.y-4*s,5*s);}
   g.restore();
  }
 };
})();
