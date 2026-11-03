'use strict';
// Native Midsummer scenery. Calendar and daily allowances arrive from the server.
(() => {
 const {ellipse,line,prism,poly}=City.kit,TAU=Math.PI*2;
 const flower=(g,x,y,r=8,c='#faf1d9')=>{for(let i=0;i<6;i++){const a=i*TAU/6;ellipse(g,x+Math.cos(a)*r*.55,y+Math.sin(a)*r*.55,r*.45,r*.45,c);}ellipse(g,x,y,r*.3,r*.3,'#f3c746');};
 const ribbon=(g,x,y,s=1)=>{for(const [side,c]of[[-1,'#388ed6'],[1,'#f3cd48']])poly(g,[[x,y],[x+side*18*s,y-9*s],[x+side*14*s,y+7*s],[x+side*5*s,y+4*s],[x+side*9*s,y+30*s],[x+side*2*s,y+24*s]],c,'#485e45',1);};
 const wreath=(g,x,y,r)=>{g.strokeStyle='#3f7240';g.lineWidth=r*.34;g.beginPath();g.ellipse(x,y,r,r*1.05,0,0,TAU);g.stroke();for(let i=0;i<14;i++){const a=i*TAU/14;ellipse(g,x+Math.cos(a)*r,y+Math.sin(a)*r,5,3,i%2?'#8cb855':'#5c934a');if(i%3===0)flower(g,x+Math.cos(a)*r,y+Math.sin(a)*r,5,i%2?'#8fb9ed':'#fff4d9');}};
 const wall=(g,o)=>{if(o.z>0)g.transform(Math.sqrt(.8),Math.sqrt(.2),0,1,0,0);};
 City.art.solsticePole={box:[300,400,150,350],occludes:true,draw(g){
  ellipse(g,0,1,105,40,'#6b9c4928');g.strokeStyle='#b2c46b';g.lineWidth=2;g.setLineDash([5,9]);g.beginPath();g.ellipse(0,0,104,39,0,0,TAU);g.stroke();g.setLineDash([]);
  line(g,[[0,0],[0,-300]],'#73593c',12);line(g,[[-4,0],[-4,-298]],'#c5d69a',3);
  line(g,[[-78,-242],[78,-242]],'#3d693c',12);
  for(let i=0;i<19;i++){const y=-8-i*16;ellipse(g,(i%2?1:-1)*6,y,11,6,i%2?'#82a94e':'#517f40');}
  for(let i=0;i<15;i++)ellipse(g,-77+i*11,-242,9,7,i%2?'#9abe62':'#548745');
  for(const x of [-65,65]){line(g,[[x,-242],[x,-208]],'#8cad50',5);wreath(g,x,-176,30);ribbon(g,x,-145,.7);}
  wreath(g,0,-294,15);ribbon(g,0,-239,1.1);for(const y of [-88,-152,-216])flower(g,2,y,8);
 }};
 City.art.solsticeBirch={box:[145,235,72,209],draw(g){ellipse(g,0,0,34,10,'#425c3f33');for(const side of [-1,1]){line(g,[[side*5,0],[side*13,-94],[side*33,-174]],'#e8e4c8',6);for(let i=0;i<5;i++){const y=-34-i*29;line(g,[[side*7,y],[side*14,y-2]],'#4d5843',2);line(g,[[side*16,y-30],[side*(38+i*3),y-50]],'#a3a87b',2);ellipse(g,side*(35+i*3),y-47,17,10,i%2?'#86ac50':'#b0c66c');}}ribbon(g,0,-38);}};
 City.art.solsticeFlowers={box:[145,120,72,98],draw(g){ellipse(g,0,1,37,13,'#384f3a40');prism(g,1.3,.7,22,'#dac39a','#a58d64','#817450');for(let i=0;i<7;i++){const x=(i-3)*9,y=-31-(i%3)*9;line(g,[[x*.7,-17],[x,y]],'#60846c',3);ellipse(g,x-4,y+10,6,3,'#9bc26c');flower(g,x,y,8,['#fff3da','#99b4ed','#edbdcd'][i%3]);}}};
 City.art.solsticeTable={box:[220,170,110,130],draw(g){ellipse(g,0,6,80,24,'#40533944');for(const x of [-48,48])line(g,[[x,-37],[x,0]],'#785a3d',9);prism(g,2.4,1.2,48,'#cfb18a','#a47f56','#7c6045');poly(g,[[-74,-72],[0,-104],[74,-72],[0,-37]],'#f9eed4');line(g,[[-30,-91],[45,-58]],'#4590c0',7);line(g,[[-45,-84],[30,-51]],'#efcf4e',7);for(const x of [-33,28]){ellipse(g,x,-73,15,6,'#ebe4ce');for(let i=0;i<5;i++)ellipse(g,x-9+i*4,-77-i%2*2,3,3,'#d35d4d');}flower(g,0,-86,10);}};
 City.art.solsticeWreath={box:[115,130,57,85],wallMounted:true,draw(g,o){g.save();wall(g,o);wreath(g,0,-12,29);ribbon(g,0,18);g.restore();}};
 City.art.solsticeGarland={box:[166,115,83,80],wallMounted:true,draw(g,o){g.save();wall(g,o);line(g,[[-67,-22],[-35,-9],[0,-4],[35,-9],[67,-22]],'#63904b',9);for(let i=0;i<9;i++){const x=-60+i*15,y=-20+17*(1-(x/65)**2);i%2?flower(g,x,y,7,'#fff1d2'):ribbon(g,x,y,.35);}g.restore();}};
 City.art.solsticeLights={box:[200,175,100,150],draw(g){for(const x of [-72,72])line(g,[[x,0],[x,-133]],'#c5c9a3',6);line(g,[[-72,-125],[-36,-107],[0,-101],[36,-107],[72,-125]],'#6f8b4b',4);for(let i=0;i<9;i++){const x=-64+i*16,y=-122+21*(1-(x/72)**2);poly(g,[[x-6,y],[x+6,y],[x,y+20]],i%2?'#edcc4c':'#418dc7');flower(g,x,y,4);}}};
 City.art.solsticeLantern={box:[128,190,64,174],draw(g){line(g,[[0,0],[0,-138],[26,-138],[26,-120]],'#738651',7);ellipse(g,26,-98,21,24,'#e2ba5c');ellipse(g,26,-98,14,21,'#fff0b9');ribbon(g,0,-49,.8);flower(g,0,-137,9);}};
 City.art.sunwovenPole={box:[390,520,195,455],occludes:true,draw(g,o){g.save();g.scale(1.3,1.3);City.art.solsticePole.draw(g,o);g.restore();}};
 let state=null,rolls={},day=0,source=null,loading=null;
 window.Solstice={
  sync(next,nextRolls,seasons){state=next;rolls=nextRolls||{};day=seasons?.find(s=>s.id==='solstice')?.day||0;},
  get source(){return source;},
  load(){if(source)return Promise.resolve();if(loading)return loading;loading=fetch('assets/solstice.txt').then(r=>r.json()).then(async meta=>{const img=new Image();img.src='assets/solstice_birchcrown.png';await img.decode();source={meta,img:{birchcrown:img}};}).catch(()=>{}).finally(()=>{loading=null;});return loading;},
  objects(zone){return state&&zone===2?[{kind:'sunwovenPole',x:state.summonX,y:state.summonY,r:0,color:'#e4cf67'}]:[];},
  drawFloor(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y);g.save();g.strokeStyle=state.active?'#f4ce68':'#aacb68';g.fillStyle='#c6e6a329';g.lineWidth=4;g.beginPath();g.ellipse(x,y,state.radius*62.225,state.radius*31.112,0,0,TAU);g.fill();g.stroke();g.restore();},
  drawLabel(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y,130);g.save();g.font='20px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#263d38';g.lineWidth=5;g.fillStyle='#fff0cf';const lines=[state.active?`The Birchcrown Guardian · Level ${state.level}`:'Five fighters · highest party level',rolls.solstice_hunt===day?'Daily mount roll used · resets at Stockholm midnight':'Daily Sunwoven Stag chance: 5% per hero'];for(const[i,t]of lines.entries()){const text=window.Locale?.translate(t)||t;g.strokeText(text,x,y+i*25);g.fillText(text,x,y+i*25);}g.restore();},
  head(n,t,talk=false){return window.Christmas.head(n,t,talk);},
  headTop(n,t=0){const h=this.head(n,t);return -h.y+7*h.width/17;},
  drawNpc(g,n,t,top,talk=false){const h=this.head(n,t,talk),s=h.width/17;g.save();g.translate(h.x,0);ribbon(g,0,h.collar+2,.45*s);for(const[x,y,r,c]of[[3,3,4,'#fff0cf'],[8,5,3.8,'#9cb8ec'],[7,0,3,'#fff3d7']]){ellipse(g,(x-1)*s,h.y+(y+1)*s,4*s,2*s,'#6d9849');flower(g,x*s,h.y+y*s,r*s,c);}g.restore();}
 };
})();
