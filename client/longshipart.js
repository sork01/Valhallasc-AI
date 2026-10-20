'use strict';
// The ship is built from its authoritative curved deck mask, not dungeon tiles.
(()=>{
 const {iso,poly}=City.kit,TAU=Math.PI*2;
 const C={ink:'#203036',wood:'#8f7355',light:'#b59a71',dark:'#4b4840',navy:'#284554',copper:'#68ad9b',bronze:'#b99460',rope:'#e7d4a6',coral:'#d68269',glass:'#90dfd0'};
 const line=(g,p,c,w=2)=>{g.beginPath();p.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
 const oval=(g,x,y,rx,ry,c,edge=C.ink,w=2)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);if(c){g.fillStyle=c;g.fill();}if(edge){g.strokeStyle=edge;g.lineWidth=w;g.stroke();}};
 function beam(g,p,w=14,c=C.wood){line(g,p,C.ink,w+5);line(g,p,c,w);line(g,p.map(([x,y])=>[x-2,y-2]),C.light,2);}
 function rope(g,p,w=4){line(g,p,C.dark,w+2);line(g,p,C.rope,w);}
 function wheel(g,x,y,r){
  oval(g,x,y,r,r,null,C.copper,8);oval(g,x,y,r-5,r-5,null,C.bronze,2);
  for(let j=0;j<8;j++){const a=j*TAU/8;beam(g,[[x,y],[x+Math.cos(a)*(r+10),y+Math.sin(a)*(r+10)]],5,C.bronze);}
  oval(g,x,y,7,7,C.coral);
 }
 City.art.keel_hull={box:[500,370,250,245],draw(g,o){
  const w=o.width,d=o.depth,f=(x,h)=>iso(x,d/2,h),b=(x,h)=>iso(x,-d/2,h);
  // Layered strakes flare outward at the gunwale; no straight stone cap.
  poly(g,[f(-w/2,0),f(w/2,0),f(w*.58,63),f(w*.38,71),f(-w*.48,65)],C.dark,C.ink,3);
  poly(g,[f(w/2,0),b(w/2,0),b(w*.57,61),f(w*.58,63)],'#354348',C.ink,3);
  for(let j=0;j<3;j++){
   const h=7+j*19;
   poly(g,[f(-w*.5,h),f(w*.51,h-2),f(w*.55,h+16),f(-w*.52,h+19)],j%2?C.wood:'#75654f',C.ink,2);
   for(let k=-1;k<=1;k++){const p=f(k*w*.31,h+8);oval(g,p[0],p[1],2.5,2.5,C.bronze,null);}
  }
  for(let s of [-1,1])beam(g,[f(s*w*.32,0),f(s*w*.4,23),f(s*w*.43,51),f(s*w*.37,79)],9,C.copper);
  rope(g,[f(-w*.52,67),f(0,65),f(w*.53,71)],3);
 }};
 City.art.keel_rib={box:[440,490,220,380],draw(g,o){
  const s=o.v?1:-1;
  beam(g,[[s*20,5],[s*52,-38],[s*65,-113],[s*51,-195],[s*12,-252],[-s*41,-285]],22,C.dark);
  beam(g,[[s*18,5],[s*43,-40],[s*55,-112],[s*41,-184],[s*5,-239]],8,C.copper);
  for(let y of [-58,-113,-173]){oval(g,s*49,y,5,7,C.bronze);rope(g,[[s*38,y-6],[s*61,y+6]],3);}
  rope(g,[[-s*36,-284],[-s*25,-222],[-s*17,-177]],3);
 }};
 City.art.keel_lamp={box:[190,230,95,195],draw(g){
  beam(g,[[-22,0],[-25,-66],[-12,-132],[14,-141]],12,C.copper);
  rope(g,[[14,-141],[14,-115]],3);
  oval(g,14,-88,25,29,C.bronze);oval(g,14,-88,18,22,C.glass);oval(g,14,-88,10,15,'#cfedd3',null);
  for(let s of [-1,1])line(g,[[14+s*11,-108],[14+s*11,-69]],C.dark,3);
  oval(g,14,-88,28,32,null,C.copper,4);
 },animate(g,o,sx,sy,t){g.save();g.translate(sx,sy);g.globalAlpha=.1+.03*Math.sin(t*2+o.y);oval(g,14,-88,36,43,C.glass,null);g.restore();}};
 City.art.keel_capstan={box:[410,390,205,310],draw(g){
  oval(g,0,2,102,42,C.dark);oval(g,0,-12,80,32,C.wood);oval(g,0,-117,53,21,C.copper);
  poly(g,[[-48,-29],[-45,-117],[45,-117],[48,-29],[0,-10]],C.wood,C.ink,4);
  for(let j=0;j<9;j++)rope(g,[[-43,-33-j*8],[0,-20-j*8],[43,-35-j*8]],5);
  oval(g,0,-121,52,20,C.copper);oval(g,0,-126,19,9,C.bronze);
  for(let j=0;j<6;j++){const a=j*TAU/6;beam(g,[[0,-125],[Math.cos(a)*100,-125+Math.sin(a)*39]],9,C.wood);}
  rope(g,[[35,-57],[105,-10],[160,8]],5);
 }};
 City.art.keel_bell={box:[230,320,115,280],draw(g){
  for(let s of [-1,1])beam(g,[[s*62,0],[s*53,-212],[s*18,-240]],15,C.copper);
  beam(g,[[-62,-219],[62,-219]],13,C.wood);
  rope(g,[[0,-214],[0,-167]],4);
  poly(g,[[-48,-79],[-39,-137],[-20,-164],[20,-164],[39,-137],[48,-79],[32,-65],[-32,-65]],C.bronze,C.ink,4);
  oval(g,0,-77,49,15,'#73634d');oval(g,0,-78,14,13,C.coral);
  rope(g,[[8,-75],[16,-29],[7,2]],4);oval(g,7,-7,8,11,null,C.rope,3);
 }};
 City.art.keel_cargo={box:[310,260,155,210],draw(g){
  for(let n=0;n<3;n++){
   const x=(n-1)*47,y=-n%2*27;
   poly(g,[[x-37,y-3],[x-39,y-62],[x,y-83],[x+38,y-61],[x+36,y-4],[x,y+17]],C.wood,C.ink,3);
   line(g,[[x-38,y-62],[x,y-41],[x+38,y-61]],C.dark,3);line(g,[[x,y-41],[x,y+17]],C.dark,3);
   rope(g,[[x-18,y-73],[x+21,y-52],[x+21,y+5]],4);
   rope(g,[[x-23,y+3],[x-23,y-51],[x+13,y-75]],4);
  }
  poly(g,[[-62,-35],[-36,-60],[-8,-33],[-19,-8],[-51,-10]],C.navy,C.copper,2);
 }};
 City.art.keel_mast={box:[740,720,370,615],draw(g){
  beam(g,[[-24,10],[0,-490],[21,-507]],27,C.wood);
  beam(g,[[-238,-345],[220,-390]],17,C.copper);
  // Asymmetrical torn sail, with open tears in its contour.
  poly(g,[[-225,-343],[207,-389],[196,-248],[167,-197],[178,-151],[138,-113],[109,-153],[83,-115],[59,-137],[31,-88],[-5,-130],[-41,-112],[-78,-155],[-123,-143],[-171,-193]],'#b1c2ad',C.ink,4);
  for(let j=-3;j<=3;j++)line(g,[[j*48,-344-j*5],[j*37,-157]],'#7d958b',2);
  for(let j=0;j<4;j++)line(g,[[-190+j*16,-302+j*47],[155-j*13,-335+j*48]],'#536f6a',2);
  poly(g,[[-22,-305],[13,-285],[28,-211],[-9,-226],[-25,-191],[-45,-240]],C.navy,null);
  for(let s of [-1,1])rope(g,[[s*217,-355-s*23],[s*131,-109],[s*97,10]],4);
  beam(g,[[0,-487],[49,-451]],12,C.wood);
 }};
 City.art.keel_prow={box:[580,600,290,500],draw(g){
  // A copper dragon figurehead carved from the pointed prow.
  beam(g,[[-123,8],[-82,-79],[-28,-151],[15,-242],[0,-313],[-52,-361]],35,C.wood);
  beam(g,[[-115,8],[-71,-76],[-16,-148],[29,-244]],12,C.copper);
  poly(g,[[-54,-361],[-90,-399],[-67,-429],[-16,-421],[9,-390],[42,-383],[43,-355],[9,-348],[-14,-326]],C.copper,C.ink,5);
  poly(g,[[-77,-398],[-64,-422],[-11,-419],[-8,-402]],C.bronze,C.ink,2);
  oval(g,-26,-390,8,7,C.coral);oval(g,-24,-391,3,4,C.ink,null);
  for(let x of [1,13,25])poly(g,[[x,-354],[x+6,-370],[x+10,-353]],C.rope,C.ink,1);
  rope(g,[[-93,-46],[-53,-84],[-10,-182],[21,-252]],8);
  for(let s of [-1,1])beam(g,[[s*65,6],[s*99,-63],[s*89,-116]],16,C.dark);
 }};
 function deck(z,x,y){return z.longshipFloor?.[y]?.[x]==='=';}
 function ground(x,y,tone,alt,z){
  if(!deck(z,x,y))return '#123b46';
  if(Math.abs(x+.5-64)<2)return '#668c80';
  const pl=(x%4+4)%4;
  return `hsl(${31+pl},${22+pl}%,${37+tone*3+(pl%2)*2}%)`;
 }
 function detail(g,px,py,x,y,tw,th,z){
  if(!deck(z,x,y))return;const at=(u,v)=>[px+(u-v)*tw/2,py+th/2+(u+v)*th/2];
  // Long fore-and-aft planks, staggered end joints, sparse grain and rope seams.
  for(let u of [-.48,0,.48])line(g,[at(u,-.5),at(u,.5)],'#4c5146',1.5);
  if((y+x*2)%5===0)line(g,[at(-.48,-.2),at(.48,-.2)],'#4b4a3e',2);
  if((x*3+y)%7===0)line(g,[at(.22,-.3),at(.14,0),at(.24,.3)],'#afa079',1.4);
  if(!deck(z,x-1,y))rope(g,[at(-.47,-.5),at(-.47,.5)],2);
  if(!deck(z,x+1,y))rope(g,[at(.47,-.5),at(.47,.5)],2);
  if(!deck(z,x,y-1))rope(g,[at(-.5,-.47),at(.5,-.47)],2);
  if(!deck(z,x,y+1))rope(g,[at(-.5,.47),at(.5,.47)],2);
  if(Math.hypot(x+.5-64,y+.5-57)<8 && (x+y)%4===0){
   line(g,[at(-.35,0),at(.35,0)],C.copper,3);oval(g,px,py+th/2,3,2,C.bronze,null);
  }
 }
 function background(g,w,h,t){
  const gr=g.createLinearGradient(0,0,w,h);gr.addColorStop(0,'#194b57');gr.addColorStop(1,'#092a36');g.fillStyle=gr;g.fillRect(0,0,w,h);
  g.save();g.globalAlpha=.08;
  for(let j=-2;j<12;j++){
   const x=j*170+Math.sin(t*.16+j)*25;poly(g,[[x,-20],[x+29,-20],[x+260,h],[x+110,h]],'#9fd6bf',null);
  }
  g.globalAlpha=.14;
  for(let j=0;j<20;j++){const x=(j*139.7+w*.17)%w,y=(h+40-(t*11+j*83)%(h+80));oval(g,x,y,2+j%3,3+j%3,null,'#b0ded2',1);}
  g.restore();
 }
 function portal(g,p,sx,sy,t){
  g.save();g.translate(sx,sy);
  for(let s of [-1,1])beam(g,[[s*83,6],[s*66,-91],[s*40,-160],[0,-187]],21,C.wood);
  const gr=g.createRadialGradient(0,-78,2,0,-78,68);gr.addColorStop(0,'#9bd9c1');gr.addColorStop(.65,'#3f827f');gr.addColorStop(1,'#163c4a');oval(g,0,-78,44,74,gr,C.copper,4);
  rope(g,[[-68,3],[-53,-115],[0,-176],[53,-115],[68,3]],5);
  wheel(g,0,-178,25);
  for(let j=0;j<4;j++)oval(g,Math.sin(j*3+t*.4)*25,-25-(j*29+t*11)%115,3,5,null,C.rope,1);
  g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle=C.ink;g.lineWidth=4;g.fillStyle=C.rope;
  const name=window.Locale?.translate(p.name)||p.name;g.strokeText(name,0,-224);g.fillText(name,0,-224);g.restore();
 }
 window.LongshipArt={deck,ground,detail,background,portal};
})();
