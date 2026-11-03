'use strict';
// Server-owned New Year availability; fixed-budget fireworks and the seasonal launchpad.
(() => {
 const areas=[WORLD_MAP,...WORLD_MAP.zones],colors=['#ffd46a','#ff5e99','#42d5ed','#ad81ff','#6adea4'];
 const {ellipse,line,prism,poly}=City.kit;
 let state=null,rolls={},day=0,source=null,loading=null;
 const inCity=(zone,hero)=>{const c=areas[zone]?.city;return [0,4,9,17].includes(zone)&&c&&hero.x>=c.x0&&hero.x<=c.x1&&hero.y>=c.y0&&hero.y<=c.y1;};
 function plan(zone,hero,t,reduced,w,h){
  if(!window.Seasonal?.isActive('newyear'))return [];
  const city=inCity(zone,hero),count=reduced?(city?4:1):(city?10:2);
  return Array.from({length:count},(_,i)=>({x:w*(.08+((i*.61803398875+zone*.173)%1)*.84),y:h*(.09+((i*.371+zone*.071)%1)*.29),r:Math.min(w,h)*(.045+(i%3)*.012),color:colors[i%colors.length],phase:reduced ? .54 : ((t*.3+i*.173)%1+1)%1}));
 }
 City.art.newyearLaunchpad={box:[240,240,120,205],draw(g){
  ellipse(g,0,0,78,27,'#252b454d');prism(g,2.1,1.65,19,'#b39ab9','#645a80','#413750');
  for(const x of [-43,43]){line(g,[[x,-17],[x,-122]],'#c3a262',7);ellipse(g,x,-126,6,6,'#ffe5a6');}
  poly(g,[[0,-53],[-18,-78],[-18,-130],[0,-162],[18,-130],[18,-78]],'#976ba0','#342d51',3);
  poly(g,[[0,-162],[-18,-130],[18,-130]],'#e47b86','#783f62',2);
  ellipse(g,0,-115,8,10,'#b4ece7');line(g,[[-32,-46],[0,-55],[32,-46]],'#edc36e',5);
 }};
 window.NewYear={
  sync(next,nextRolls,seasons){state=next;rolls=nextRolls||{};day=seasons?.find(s=>s.id==='newyear')?.day||0;},
  get source(){return source;},
  load(){if(source)return Promise.resolve();if(loading)return loading;
   if(window.__valhallaTestSprites){const c=document.createElement('canvas');c.width=768;c.height=480;const g=c.getContext('2d');g.fillStyle='#a682b2';for(let y=0;y<5;y++)for(let x=0;x<8;x++)g.fillRect(x*96+28,y*96+15,40,75);source={meta:{frame:[96,96],anchor:[48,90],clips:{idle:{fps:6,n:6,row:0},walk:{fps:10,n:8,row:1},attack:{fps:12,n:8,row:2},hurt:{fps:10,n:4,row:3},die:{fps:8,n:8,row:4}}},img:{starrocketeer:c}};return Promise.resolve();}
   loading=fetch('assets/newyear.txt').then(r=>r.json()).then(async meta=>{const img=new Image();img.src='assets/newyear_starrocketeer.png';await img.decode();source={meta,img:{starrocketeer:img}};}).catch(()=>{}).finally(()=>{loading=null;});return loading;
  },
  objects(zone){return state&&zone===state.zone?[{kind:'newyearLaunchpad',x:state.summonX,y:state.summonY,r:0}]:[];},
  drawFloor(g,zone,w2s){if(!state||zone!==state.zone)return;const[x,y]=w2s(state.x,state.y);g.save();g.strokeStyle=state.active?'#f3a5a6':'#c4b3e8';g.fillStyle='#bea5df20';g.lineWidth=3;g.beginPath();g.ellipse(x,y,state.radius*62.225,state.radius*31.112,0,0,Math.PI*2);g.fill();g.stroke();g.restore();},
  drawLabel(g,zone,w2s){if(!state||zone!==state.zone)return;const[x,y]=w2s(state.summonX,state.summonY,210);g.save();g.font='20px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#27243d';g.lineWidth=5;g.fillStyle='#fff0ba';
   const lines=[state.active?`The Starfire Rocketeer · Level ${state.level}`:'Five fighters · highest party level',rolls.newyear_hunt===day?'Daily mount roll used · resets at Stockholm midnight':'Daily Starflight Rocket chance: 5% per hero'];
   for(const[i,t]of lines.entries()){const text=window.Locale?.translate(t)||t;g.strokeText(text,x,y+i*25);g.fillText(text,x,y+i*25);}g.restore();
  },
  fireworksPlan:plan,
  drawFireworks(g,zone,hero,t,w,h,reduced){
   const bursts=plan(zone,hero,t,reduced,w,h);if(!bursts.length)return {bursts:0,rays:0};
   const rays=reduced?10:window.Prefs?.lowGraphics?12:24;let painted=0;
   g.save();g.globalCompositeOperation='source-over';g.lineCap='round';
   for(const b of bursts){
    const p=b.phase;
    if(!reduced&&p<.23){const y=b.y+(1-p/.23)*h*.19;g.globalAlpha=.5;line(g,[[b.x,y+15],[b.x,y]],b.color,2);continue;}
    const age=reduced?.45:(p-.23)/.77,fade=reduced?.32:Math.max(0,1-age)*.95,r=b.r*(.2+Math.sqrt(age)*1.45);
    g.globalAlpha=fade;
    for(let i=0;i<rays;i++){
     const a=i*Math.PI*2/rays,spread=1+(i%3)*.08,x=b.x+Math.cos(a)*r*spread,y=b.y+Math.sin(a)*r*.85*spread+age*age*22;
     line(g,[[b.x+Math.cos(a)*r*.72*spread,b.y+Math.sin(a)*r*.72*.85*spread+age*age*18],[x,y]],b.color,reduced?1.5:2.8);
     if(!reduced&&!window.Prefs?.lowGraphics){ellipse(g,x,y,1.6,1.6,'#fff1cb');}
    }
    painted++;
   }
   g.restore();return {bursts:painted,rays:painted*rays};
  }
 };
})();
