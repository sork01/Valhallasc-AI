'use strict';
// A broken clock suspended over a midnight furnace; floor mask is authoritative.
(()=>{
 const {iso,poly}=City.kit,TAU=Math.PI*2;
 const C={ink:'#151522',iron:'#424859',edge:'#8a93ac',dark:'#272938',violet:'#7943a6',hot:'#a47ae2',cyan:'#76dcd6',pale:'#d0fff0',warning:'#c7c56c'};
 const line=(g,p,c,w=2)=>{g.beginPath();p.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.lineCap='round';g.stroke();};
 const oval=(g,x,y,rx,ry,c,edge=C.ink,w=2)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);if(c){g.fillStyle=c;g.fill();}if(edge){g.strokeStyle=edge;g.lineWidth=w;g.stroke();}};
 const beam=(g,p,w=13,c=C.iron)=>{line(g,p,C.ink,w+5);line(g,p,c,w);line(g,p.map(([x,y])=>[x-2,y-2]),C.edge,2);};
 function gear(g,x,y,r,flat=.5){
  const p=[];for(let k=0;k<48;k++){const t=k*TAU/48,rad=r*(k%4===1||k%4===2?1:.85);p.push([x+Math.cos(t)*rad,y+Math.sin(t)*rad*flat]);}
  poly(g,p,C.iron,C.ink,4);oval(g,x,y,r*.66,r*.66*flat,C.dark,C.edge,3);
  for(let j=0;j<8;j++){const t=j*TAU/8;beam(g,[[x+Math.cos(t)*r*.19,y+Math.sin(t)*r*.19*flat],[x+Math.cos(t)*r*.63,y+Math.sin(t)*r*.63*flat]],7,C.violet);}
  oval(g,x,y,r*.18,r*.18*flat,C.cyan,C.ink,3);
 }
 City.art.null_wall={box:[620,240,310,155],draw(g,o){
  const w=o.width,d=o.depth,f=(x,h)=>iso(x,d/2,h),b=(x,h)=>iso(x,-d/2,h);
  poly(g,[f(-w/2,0),f(w/2,0),f(w/2,45),f(-w/2,45)],C.dark,C.ink,3);
  poly(g,[f(w/2,0),b(w/2,0),b(w/2,45),f(w/2,45)],'#1e2230',C.ink,3);
  poly(g,[f(-w/2,45),f(w/2,45),b(w/2,45),b(-w/2,45)],C.iron,C.edge,2);
  line(g,[f(-w/2,28),f(w/2,28)],C.violet,4);
  for(let x=-w/2+.4;x<w/2;x+=1.6){const p=f(x,14);oval(g,p[0],p[1],3,3,C.cyan,null);}
 }};
 City.art.null_lamp={box:[180,260,90,220],draw(g){
  beam(g,[[0,3],[0,-149],[24,-164]],13);beam(g,[[24,-164],[24,-99]],8,C.violet);
  for(let n=0;n<4;n++){oval(g,24,-105-n*12,21,7,C.violet,C.ink,2);line(g,[[8,-109-n*12],[40,-109-n*12]],C.cyan,3);}
  oval(g,24,-157,13,6,C.pale,C.ink,2);
 },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.07+.02*Math.sin(t*2+o.x);oval(g,sx+24,sy-130,39,58,C.cyan,null);g.restore();}};
 City.art.null_furnace={box:[380,420,190,350],draw(g){
  poly(g,[[-73,2],[-76,-181],[-43,-227],[48,-227],[78,-181],[73,2],[0,30]],C.iron,C.ink,5);
  poly(g,[[-58,-170],[-43,-205],[42,-205],[60,-170],[51,-49],[-51,-49]],C.dark,C.violet,7);
  const gr=g.createLinearGradient(0,-180,0,-50);gr.addColorStop(0,C.violet);gr.addColorStop(.7,C.cyan);gr.addColorStop(1,C.pale);
  poly(g,[[-42,-164],[-30,-193],[31,-193],[44,-164],[37,-64],[-37,-64]],gr,C.ink,2);
  for(let x=-30;x<=30;x+=15)beam(g,[[x,-191],[x,-64]],5,C.dark);
  for(let s of [-1,1]){beam(g,[[s*61,-37],[s*79,-94],[s*67,-183]],13,C.violet);beam(g,[[s*30,-229],[s*30,-290]],17);oval(g,s*30,-293,12,5,C.cyan,C.ink,2);}
  for(let n=0;n<4;n++)line(g,[[-44+n*24,8],[-31+n*24,-13]],C.warning,8);
 }};
 City.art.null_bellframe={box:[680,610,340,520],draw(g){
  for(let s of [-1,1]){beam(g,[[s*193,10],[s*177,-354],[s*124,-438]],29);beam(g,[[s*164,-18],[s*152,-335]],8,C.violet);}
  beam(g,[[-175,-355],[175,-355]],28);gear(g,0,-368,92,1);
  line(g,[[-21,-288],[-21,-228],[0,-203],[21,-228],[21,-288]],C.cyan,5);
  poly(g,[[-99,-88],[-74,-172],[-40,-216],[40,-216],[74,-172],[99,-88],[59,-66],[-59,-66]],C.violet,C.ink,5);
  oval(g,0,-86,101,27,C.dark,C.edge,5);oval(g,0,-83,20,20,C.cyan,C.ink,3);
  for(let n=-2;n<=2;n++)line(g,[[n*25,-109],[n*19,-182]],C.edge,3);
 }};
 City.art.null_turbine={box:[680,530,340,440],draw(g){
  for(let s of [-1,1])beam(g,[[s*160,4],[s*146,-237],[s*84,-312]],24);
  gear(g,0,-184,135,1);oval(g,0,-184,67,67,C.dark,C.cyan,8);
  for(let j=0;j<12;j++){const t=j*TAU/12;line(g,[[Math.cos(t)*77,-184+Math.sin(t)*77],[Math.cos(t)*111,-184+Math.sin(t)*111]],j%3?C.violet:C.cyan,7);}
  for(let s of [-1,1])for(let n=0;n<3;n++){const x=s*(182+n*26);beam(g,[[x,4],[x,-80-n*45]],12);oval(g,x,-82-n*45,14,6,C.cyan,C.ink,2);}
 }};
 City.art.null_clock={box:[830,780,415,660],draw(g){
  for(let s of [-1,1])beam(g,[[s*210,20],[s*192,-446],[s*107,-557]],32);
  gear(g,0,-310,205,1);oval(g,0,-310,145,145,C.dark,C.hot,5);
  for(let n=0;n<12;n++){const t=n*TAU/12;beam(g,[[Math.sin(t)*115,-310+Math.cos(t)*115],[Math.sin(t)*134,-310+Math.cos(t)*134]],8,C.warning);}
  beam(g,[[0,-310],[-74,-407]],8,C.cyan);beam(g,[[0,-310],[105,-343]],7,C.cyan);oval(g,0,-310,19,19,C.pale,C.ink,3);
  for(let s of [-1,1]){beam(g,[[s*92,-111],[s*92,-28]],9,C.violet);poly(g,[[s*92-24,-29],[s*92+24,-29],[s*92+30,12],[s*92-30,12]],C.iron,C.ink,3);}
 }};
 City.art.null_gateway={box:[420,450,210,370],draw(g){
  for(let s of [-1,1])beam(g,[[s*113,5],[s*94,-204],[s*52,-267]],23);gear(g,0,-257,68,1);
  for(let s of [-1,1])line(g,[[s*84,-12],[s*70,-183],[s*36,-221]],C.cyan,4);
 }};
 City.art.null_seal={box:[220,160,110,90],draw(g,o){
  const colors=['#688468','#a39256','#9b6948','#6a9ba7'];
  gear(g,0,-7,75,.42);oval(g,0,-8,42,18,colors[o.v%4],C.ink,3);
  // Four seasonal supply seals, weathered into the same black iron as the foundry.
  if(o.v===0){poly(g,[[-22,-7],[-3,-26],[22,-15],[4,1]],'#a1b795',C.ink,2);line(g,[[-16,-5],[16,-21]],C.dark,2);}
  else if(o.v===1){oval(g,0,-10,13,8,C.warning,C.ink,2);for(let j=0;j<8;j++){const a=j*TAU/8;line(g,[[Math.cos(a)*20,-10+Math.sin(a)*11],[Math.cos(a)*29,-10+Math.sin(a)*15]],C.warning,3);}}
  else if(o.v===2){oval(g,0,-8,14,11,'#b18a5f',C.ink,2);oval(g,0,-17,19,7,'#514638',C.ink,2);line(g,[[0,-20],[3,-29]],C.warning,3);}
  else{for(let j=0;j<3;j++){const a=j*TAU/6;line(g,[[-Math.cos(a)*27,-10-Math.sin(a)*14],[Math.cos(a)*27,-10+Math.sin(a)*14]],'#b6d7de',3);}}
 }};
 City.art.null_sump={box:[1000,560,500,370],draw(g){
  oval(g,0,-20,380,145,'#171321',C.iron,30);oval(g,0,-15,330,116,'#302140',C.violet,8);
  for(let j=0;j<8;j++){const x=-240+j*68;beam(g,[[x,-30],[x+30,-163]],14,C.dark);line(g,[[x+4,-39],[x+26,-139]],C.cyan,3);}
 }};
 const floor=(z,x,y)=>z.blackhourFloor?.[y]?.[x]==='=';
 function ground(x,y,tone,alt,z){if(!floor(z,x,y))return '#151421';const r=Math.hypot(x-80,y-83);return r>61?'#646373':`hsl(${238+(x%3)*2},12%,${31+tone*7+(x+y)%2}%)`;}
 function detail(g,px,py,x,y,tw,th,z){
  if(!floor(z,x,y))return;const at=(u,v)=>[px+(u-v)*tw/2,py+th/2+(u+v)*th/2];
  line(g,[at(-.48,-.48),at(.48,-.48),at(.48,.48)],'#292c3c',1.5);
  const r=Math.hypot(x+.5-80,y+.5-83),angle=Math.atan2(y-83,x-80);
  if((r>47&&r<49)||(r>58&&r<60))line(g,[at(-.48,-.1),at(.48,.1)],C.violet,4);
  if(r>43&&r<64&&Math.abs(Math.sin(angle*12))<.1)line(g,[at(-.35,-.35),at(.35,.35)],C.warning,3);
  if((x+y)%7===0){oval(g,px-12,py+th/2,2.5,1.5,C.edge,null);oval(g,px+12,py+th/2,2.5,1.5,C.edge,null);}
  if(!floor(z,x-1,y)||!floor(z,x,y-1))line(g,[at(-.48,.48),at(-.48,-.48),at(.48,-.48)],C.cyan,2);
 }
 function background(g,w,h,t){
  const gr=g.createLinearGradient(0,0,0,h);gr.addColorStop(0,'#13131f');gr.addColorStop(1,'#35223f');g.fillStyle=gr;g.fillRect(0,0,w,h);
  g.save();g.globalAlpha=.10;for(let j=0;j<7;j++)gear(g,j*310-100,260+(j%2)*280,180,1);
  g.globalAlpha=.18;for(let j=0;j<32;j++){const x=(j*173.7)%w,y=h-(t*16+j*79)%(h+60);line(g,[[x,y],[x+2,y-8]],j%3?C.hot:C.cyan,1.5);}g.restore();
 }
 function portal(g,p,sx,sy,t){
  g.save();g.translate(sx,sy);gear(g,0,-95,96,1);oval(g,0,-95,65,65,'#21172e',C.violet,6);
  const gr=g.createRadialGradient(0,-95,4,0,-95,61);gr.addColorStop(0,C.pale);gr.addColorStop(.35,C.cyan);gr.addColorStop(1,'#33234c');oval(g,0,-95,55,55,gr,null);
  for(let j=0;j<4;j++){const a=t*.2+j*TAU/4;line(g,[[Math.sin(a)*68,-95+Math.cos(a)*68],[Math.sin(a)*88,-95+Math.cos(a)*88]],C.warning,5);}
  for(let s of [-1,1])beam(g,[[s*87,10],[s*74,-36]],19);
  g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle=C.ink;g.lineWidth=4;g.fillStyle=C.pale;const name=window.Locale?.translate(p.name)||p.name;g.strokeText(name,0,-211);g.fillText(name,0,-211);g.restore();
 }
 window.BlackhourArt={floor,ground,detail,background,portal};
})();
