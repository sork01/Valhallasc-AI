'use strict';
// Nornroot is a burial loom inside a fossil root: end grain, amber sap and woven walkways.
(() => {
  const {iso,poly}=City.kit, TAU=Math.PI*2;
  const C={ink:'#252321',bark:'#63432f',shadow:'#342e28',wood:'#a27948',cut:'#c39a5c',amber:'#efa746',light:'#ffe4a0',thread:'#d1ded0',moss:'#465b4d'};
  const stroke=(g,points,color,width=2)=>{g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=color;g.lineWidth=width;g.lineJoin='round';g.lineCap='round';g.stroke();};
  const ellipse=(g,x,y,rx,ry,color,edge=null,width=2)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);if(color){g.fillStyle=color;g.fill();}if(edge){g.strokeStyle=edge;g.lineWidth=width;g.stroke();}};
  const sap=(g,x,y,rx,ry)=>{ellipse(g,x,y,rx,ry,'#88542e',C.ink,3);poly(g,[[x-rx*.8,y],[x-rx*.32,y-ry*.85],[x+rx*.55,y-ry*.52],[x+rx*.8,y+ry*.25],[x,y+ry*.85]],C.amber,null);stroke(g,[[x-rx*.3,y+ry*.1],[x-rx*.25,y-ry*.55],[x+rx*.2,y-ry*.65]],C.light,2);};
  function strand(g,points,width=14){stroke(g,points,C.ink,width+5);stroke(g,points,C.bark,width);stroke(g,points.map(([x,y])=>[x-2,y-2]),C.wood,Math.max(2,width*.22));}
  City.art.norn_wall={box:[500,470,250,340],draw(g,o){
    const w=o.width,d=o.depth, f=(x,h)=>iso(x,d/2,h), b=(x,h)=>iso(x,-d/2,h);
    // Broken root crust, with no continuous stone parapet or regular cap.
    poly(g,[f(-w/2,0),f(w/2,0),f(w/2,54),f(w*.25,67),f(0,57),f(-w*.29,74),f(-w/2,61)],C.shadow,C.ink,3);
    poly(g,[f(w/2,0),b(w/2,0),b(w/2,62),f(w/2,54)],'#282c25',C.ink,3);
    for(let j=0;j<5;j++){
      const u=-w*.48+j*w*.24, tip=83+(j%3)*15+10*Math.sin(w*.7+d+j*2);
      strand(g,[f(u,3),f(u+w*.12,28),f(u-w*.06,59),f(u+w*.07,tip)],12+(j%2)*7);
      strand(g,[f(u+w*.08,44),f(u+w*.22,70),b(Math.min(w/2,u+w*.3),tip-13)],8);
      if(j%2===0){const p=f(u,42);sap(g,p[0],p[1],7,15);}
    }
    // Bronze weaving pegs and hanging funeral cords live between the roots.
    for(let j=0;j<4;j++){
      const u=-w*.36+j*w*.24, a=f(u,68),z=f(u,18+(j%2)*12);
      stroke(g,[a,z],C.thread,1.5);ellipse(g,z[0],z[1],3,5,C.amber,C.ink,1);
    }
    for(let j=0;j<3;j++){const p=f(-w*.3+j*w*.3,7);ellipse(g,p[0],p[1],15,5,C.moss);}
  }};
  City.art.norn_lamp={box:[200,270,100,235],draw(g){
    strand(g,[[-19,0],[-27,-36],[-17,-88],[-24,-145],[0,-176],[25,-151],[27,-126]],15);
    stroke(g,[[17,-161],[17,-118]],C.thread,3);
    sap(g,17,-92,18,31);
    for(let j=-1;j<=1;j++)stroke(g,[[j*10+17,-119],[j*8+17,-63]],'#5f523b',2);
    ellipse(g,0,0,29,8,C.moss);
  },animate(g,o,sx,sy,t){g.save();g.translate(sx,sy);g.globalAlpha=.1+.025*Math.sin(t*2+o.x);ellipse(g,17,-92,29,43,C.light);g.restore();}};
  City.art.norn_spindle={box:[250,270,125,230],draw(g){
    ellipse(g,0,0,44,16,C.shadow,C.ink,3);
    for(const s of [-1,1])strand(g,[[s*29,0],[s*39,-32],[s*33,-94],[s*20,-147]],13);
    stroke(g,[[0,-20],[0,-172]],C.cut,8);
    ellipse(g,0,-43,35,13,C.wood,C.ink,3);ellipse(g,0,-129,35,13,C.cut,C.ink,3);
    for(let j=0;j<12;j++)stroke(g,[[-27,-48-j*6],[27,-57-j*6]],j%3?C.thread:C.amber,3);
    sap(g,0,-156,12,21);
    for(const s of [-1,1])stroke(g,[[s*26,-117],[s*48,-56],[s*33,-12]],C.thread,2);
  }};
  City.art.norn_sarcophagus={box:[310,270,155,220],draw(g){
    // A body-shaped amber cocoon in a split root cradle, rather than a stone coffin.
    for(const s of [-1,1])strand(g,[[s*52,-8],[s*69,-54],[s*51,-104],[s*23,-134]],18);
    poly(g,[[-23,-16],[-45,-48],[-39,-91],[-18,-125],[18,-125],[39,-91],[45,-48],[23,-16]],'#7f5837',C.ink,4);
    sap(g,0,-70,32,51);
    for(let j=0;j<5;j++)stroke(g,[[-32+j*2,-31-j*18],[31-j*2,-51-j*16]],C.thread,3);
    ellipse(g,0,-96,8,9,'#65482c');stroke(g,[[0,-85],[0,-47]],'#65482c',6);
  }};
  City.art.norn_loom={box:[650,520,325,450],draw(g){
    // A great hollow stump supporting a three-weight funeral loom.
    for(const s of [-1,1]){
      strand(g,[[s*155,8],[s*131,-55],[s*161,-143],[s*133,-242],[s*80,-312],[0,-333]],32);
      strand(g,[[s*133,-194],[s*206,-238],[s*224,-278]],18);
    }
    stroke(g,[[-133,-240],[133,-240]],C.cut,15);stroke(g,[[-117,-66],[117,-66]],C.cut,16);
    for(let i=-7;i<=7;i++)stroke(g,[[i*16,-237],[i*15,-68]],i%3?C.thread:C.amber,2.5);
    for(let j=0;j<10;j++)stroke(g,[[-98,-75-j*10],[98,-84-j*10]],j%2?'#9c7149':C.wood,6);
    for(let i=-1;i<=1;i++){
      stroke(g,[[i*62,-252],[i*62,-294]],C.thread,3);sap(g,i*62,-277,15,21);
    }
    ellipse(g,0,-151,44,55,C.shadow,C.amber,5);
    for(let i=-1;i<=1;i++)stroke(g,[[i*16,-188],[i*16,-114]],C.thread,3);
    stroke(g,[[-31,-148],[0,-172],[31,-148],[0,-125],[-31,-148]],C.amber,5);
    for(const s of [-1,1])sap(g,s*128,-55,16,28);
  }};
  function room(x,y,z){return (z.rooms||[]).findIndex(([x0,y0,x1,y1])=>x>=x0&&x<x1&&y>=y0&&y<y1);}
  function ground(x,y,tone,alt,z){
    const i=room(x,y,z),r=z.rooms?.[i];if(!r)return '#202b28';
    const dx=x+.5-(r[0]+r[2])/2,dy=y+.5-(r[1]+r[3])/2;
    const lane=Math.abs(dx)<2||Math.abs(dy)<1.3;
    if(i===2)return '#795936';
    if(i===3)return lane?'#80958a':`hsl(167,17%,${27+tone*3}%)`;
    if(i===5)return Math.abs(dx)<3?'#a58a56':'#705b3e';
    if(i>=6)return (Math.abs(dx)<1.6||Math.abs(dy)<1.6)?'#897956':'#47564b';
    return lane?'#aa9363':`hsl(155,16%,${25+tone*3}%)`;
  }
  function detail(g,px,py,x,y,tw,th,z){
    const i=room(x,y,z);if(i<0)return;
    const r=z.rooms[i],cx=(r[0]+r[2])/2,cy=(r[1]+r[3])/2;
    const at=(u,v)=>[px+(u-v)*tw/2,py+th/2+(u+v)*th/2];
    // Irregular continuous growth rings cross cell boundaries; there is no tile grid.
    if(i===2||i===5){
      g.save();g.beginPath();g.moveTo(px,py);g.lineTo(px+tw/2,py+th/2);g.lineTo(px,py+th);g.lineTo(px-tw/2,py+th/2);g.closePath();g.clip();
      for(let radius=2;radius<24;radius+=2.4){
        g.beginPath();for(let k=0;k<=48;k++){
          const a=k*TAU/48,rr=radius+.25*Math.sin(a*5)+.12*Math.cos(a*9);
          const p=at(cx-x-.5+Math.cos(a)*rr,cy-y-.5+Math.sin(a)*rr);
          k?g.lineTo(...p):g.moveTo(...p);
        }g.strokeStyle=radius%4.8<2.4?'#d1a05c':'#66492e';g.lineWidth=1.7;g.stroke();
      }
      g.restore();
    }
    if(i===3||i>=6||Math.abs(x+.5-cx)<2){
      for(let j=-2;j<=2;j++){
        const a=at(-.5,j*.18),b=at(.5,j*.18);stroke(g,[a,b],i===3?'#afc6b7':'#d4bd85',1.4);
      }
      if((x+y)%2===0)stroke(g,[at(-.32,-.5),at(-.32,.5)],'#433e2d',3);
    }else if((x*3+y*7)%5===0){
      stroke(g,[at(-.5,.12),at(-.1,.04),at(.25,.23),at(.5,.17)],'#71816a',3);
      ellipse(g,px-8,py+th/2,5,2,'#b2b994');
    }
  }
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);
    ellipse(g,0,3,94,24,C.moss,C.ink,3);
    for(const s of [-1,1]){
      strand(g,[[s*85,10],[s*59,-26],[s*67,-97],[s*43,-162],[0,-181]],24);
      strand(g,[[s*58,-97],[s*93,-117],[s*98,-144]],12);
    }
    const gr=g.createRadialGradient(0,-75,2,0,-75,70);gr.addColorStop(0,'#e8bd75');gr.addColorStop(.5,'#715a40');gr.addColorStop(1,'#26382f');
    ellipse(g,0,-76,39,71,gr,C.amber,3);
    for(let i=-3;i<=3;i++)stroke(g,[[i*10,-135],[i*10+Math.sin(t+i)*2,-17]],C.thread,1.5);
    sap(g,0,-173,14,23);
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.lineWidth=4;g.strokeStyle=C.ink;g.fillStyle=C.light;
    const name=window.Locale?.translate(p.name)||p.name;g.strokeText(name,0,-210);g.fillText(name,0,-210);g.restore();
  }
  window.NornrootArt={ground,detail,portal};
})();
