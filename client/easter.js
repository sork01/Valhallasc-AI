'use strict';
// Cached native Easter scenery; availability and daily attempts are server-owned.
(() => {
 const {ellipse,line,prism,poly}=City.kit,colors=['#f0bfce','#c8b8e7','#b9dfc2','#f4d99a','#a9d8e1'];
 const egg=(g,x,y,r,color=colors[0])=>{g.save();g.translate(x,y);g.fillStyle=color;g.strokeStyle='#797188';g.lineWidth=1.5;g.beginPath();g.moveTo(0,-r*1.3);g.bezierCurveTo(r*.8,-r*1.3,r*1.2,r*.7,0,r);g.bezierCurveTo(-r*1.2,r*.7,-r*.8,-r*1.3,0,-r*1.3);g.fill();g.stroke();line(g,[[-r*.65,-r*.1],[0,r*.15],[r*.65,-r*.1]],'#fff7dd',r*.18);for(const side of [-1,1])ellipse(g,side*r*.35,r*.5,r*.12,r*.12,'#fff9ee');ellipse(g,-r*.2,-r*.7,r*.13,r*.25,'#fff9ec');g.restore();};
 const flower=(g,x,y,r=8)=>{for(let i=0;i<5;i++){const a=i*Math.PI*2/5;ellipse(g,x+Math.cos(a)*r*.5,y+Math.sin(a)*r*.5,r*.5,r*.55,i%2?'#f7d0dd':'#e9abc5');}ellipse(g,x,y,r*.3,r*.3,'#f5dc8c');};
 const ribbon=(g,x,y,s=1)=>poly(g,[[x,y],[x-15*s,y-8*s],[x-13*s,y+9*s],[x,y+3*s],[x+13*s,y+9*s],[x+15*s,y-8*s]],'#d8b9e7','#8c789d',1.5);
 const wall=(g,o)=>{if(o.z>0)g.transform(Math.sqrt(.8),Math.sqrt(.2),0,1,0,0);};
 City.art.easterFlowers={box:[145,120,72,98],draw(g){ellipse(g,0,1,37,13,'#384f3a40');prism(g,1.3,.7,22,'#e1c39a','#b19478','#887466');for(let i=0;i<7;i++){const x=(i-3)*9,y=-31-(i%3)*9;line(g,[[x*.7,-17],[x,y]],'#60846c',3);ellipse(g,x-4,y+10,6,3,'#9bc29a');flower(g,x,y,9);}}};
 City.art.easterBasket={box:[160,175,80,140],draw(g){ellipse(g,0,1,43,14,'#47603d44');ellipse(g,0,-24,43,28,'#c7a77c','#806a59',2);for(const y of [-30,-18,-7])line(g,[[-36,y],[0,y+5],[36,y]],'#e6cba4',3);for(const x of [-25,-12,0,12,25])line(g,[[x,-46],[x,-2]],'#a78968',2);g.strokeStyle='#ac8b66';g.lineWidth=7;g.beginPath();g.ellipse(0,-43,32,39,0,Math.PI,Math.PI*2);g.stroke();for(let i=0;i<5;i++)egg(g,-28+i*14,-48-(i%2)*8,13,colors[i]);ribbon(g,0,-9,1.2);for(const x of [-35,35])flower(g,x,-18,10);}};
 City.art.easterEgg={box:[160,240,80,205],draw(g){ellipse(g,0,1,37,12,'#48663f44');prism(g,.9,.9,24,'#e6d7b5','#b8ab90','#8f8d7e');line(g,[[0,-22],[0,-128]],'#8baf89',7);egg(g,0,-130,39,colors[1]);ribbon(g,0,-72,1.3);for(const side of [-1,1]){line(g,[[0,-48],[side*29,-38]],'#7b9b72',4);flower(g,side*29,-38,12);}}};
 City.art.easterGrandEgg={box:[250,340,125,290],occludes:true,draw(g,o){g.save();g.scale(1.45,1.45);City.art.easterEgg.draw(g,o);g.restore();}};
 City.art.springtideShrine={box:[340,420,170,355],occludes:true,draw(g,o){g.save();g.scale(2,2);City.art.easterBasket.draw(g,o);for(const side of [-1,1]){line(g,[[side*52,-5],[side*52,-130]],'#7f9c7a',7);egg(g,side*52,-145,19,colors[side+1]);ribbon(g,side*52,-103);flower(g,side*52,-54,12);}g.restore();}};
 City.art.easterWreath={box:[115,130,57,85],wallMounted:true,draw(g,o){g.save();wall(g,o);g.strokeStyle='#789773';g.lineWidth=13;g.beginPath();g.ellipse(0,-12,28,29,0,0,Math.PI*2);g.stroke();for(let i=0;i<8;i++){const a=i*Math.PI/4,x=Math.cos(a)*26,y=-12+Math.sin(a)*26;i%2?flower(g,x,y,8):egg(g,x,y,7,colors[i%5]);}ribbon(g,0,16);g.restore();}};
 City.art.easterGarland={box:[166,115,83,80],wallMounted:true,draw(g,o){g.save();wall(g,o);line(g,[[-67,-22],[-35,-9],[0,-4],[35,-9],[67,-22]],'#86a581',7);for(let i=0;i<9;i++){const x=-60+i*15,y=-20+17*(1-(x/65)**2);i%2?flower(g,x,y,7):egg(g,x,y+4,7,colors[i%5]);}g.restore();}};
 City.art.easterLights={box:[200,175,100,150],draw(g){for(const x of [-72,72]){line(g,[[x,0],[x,-133]],'#9b9e80',6);flower(g,x,-137,8);}line(g,[[-72,-125],[-36,-107],[0,-101],[36,-107],[72,-125]],'#a997aa',3);for(let i=0;i<9;i++){const x=-64+i*16,y=-122+21*(1-(x/72)**2);line(g,[[x,y],[x,y+9]],'#a292a4',2);egg(g,x,y+14,6,colors[i%5]);}}};
 City.art.easterLantern={...City.art.festivalLantern,draw(g){ellipse(g,0,1,23,8,'#43583c44');line(g,[[0,0],[0,-138],[26,-138],[26,-120]],'#90a586',7);egg(g,26,-95,25,'#f6e0a7');ribbon(g,0,-44);}};
 City.art.easterCandles={box:[116,120,58,103],draw(g){for(const[x,h]of[[-22,40],[0,66],[23,47]]){g.fillStyle='#d0bddf';g.fillRect(x-8,-h,16,h);ellipse(g,x,-h-7,4,10,'#ffdfa2');egg(g,x,-h*.5,5,'#f6ddb7');}for(const x of [-25,0,25])flower(g,x,-5,8);}};
 let state=null,rolls={},day=0,source=null,loading=null;
 window.Easter={
  sync(next,nextRolls,seasons){state=next;rolls=nextRolls||{};day=seasons?.find(s=>s.id==='easter')?.day||0;},
  get source(){return source;},
  load(){if(source)return Promise.resolve();if(loading)return loading;loading=fetch('assets/easter.txt').then(r=>r.json()).then(async meta=>{const img=new Image();img.src='assets/easter_bloomwarden.png';await img.decode();source={meta,img:{bloomwarden:img}};}).catch(()=>{}).finally(()=>{loading=null;});return loading;},
  objects(zone){return state&&zone===2?[{kind:'springtideShrine',x:state.summonX,y:state.summonY,r:0,color:'#dbc4e7'}]:[];},
  drawFloor(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y);g.save();g.strokeStyle=state.active?'#f1c3d2':'#abd3ac';g.fillStyle='#c6e6d329';g.lineWidth=4;g.beginPath();g.ellipse(x,y,state.radius*62.225,state.radius*31.112,0,0,Math.PI*2);g.fill();g.stroke();g.restore();},
  drawLabel(g,zone,w2s){if(!state||zone!==2)return;const[x,y]=w2s(state.x,state.y,130);g.save();g.font='20px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#263d38';g.lineWidth=5;g.fillStyle='#fff0cf';const lines=[state.active?`The Bloomwarden · Level ${state.level}`:'Five fighters · highest party level',rolls.easter_hunt===day?'Daily mount roll used · resets at Stockholm midnight':'Daily Springtide Bunny chance: 5% per hero'];for(const[i,t]of lines.entries()){const text=window.Locale?.translate(t)||t;g.strokeText(text,x,y+i*25);g.fillText(text,x,y+i*25);}g.restore();},
  head(n,t,talk=false){return window.Christmas.head(n,t,talk);},
  headTop(n,t=0){const h=this.head(n,t);return -h.y+25*h.width/17;},
  drawNpc(g,n,t,top,talk=false){const h=this.head(n,t,talk),s=h.width/17;g.save();g.translate(h.x,0);ribbon(g,0,h.collar+2,0.65*s);line(g,[[-10*s,h.y+2*s],[0,h.y-2*s],[10*s,h.y+2*s]],'#8fb18c',3*s);for(const side of [-1,1]){ellipse(g,side*6*s,h.y-10*s,3*s,12*s,'#f8f1e8');ellipse(g,side*6*s,h.y-11*s,1.4*s,8*s,'#edbed2');flower(g,side*10*s,h.y+2*s,4*s);}g.restore();}
 };
})();
