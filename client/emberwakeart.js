'use strict';
// Basalt terraces and molten river: every lava footprint matches map collision.
(() => {
  const {iso,poly}=City.kit,TAU=Math.PI*2;
  const C={ink:'#201e2b',rock:'#484552',light:'#77717a',iron:'#3b4350',hot:'#f1803c',pale:'#ffdc8d',cyan:'#8fc6d0'};
  const line=(g,p,c,w=2)=>{g.beginPath();p.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.stroke();};
  const oval=(g,x,y,rx,ry,c,edge=C.ink)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();if(edge){g.strokeStyle=edge;g.lineWidth=3;g.stroke();}};
  const beam=(g,p,w=12,c=C.iron)=>{line(g,p,C.ink,w+5);line(g,p,c,w);};
  const chain=(g,x,y,n)=>{for(let j=0;j<n;j++){oval(g,x+Math.sin(j)*3,y+j*19,10,15,C.light);oval(g,x+Math.sin(j)*3,y+j*19,4,8,C.ink,null);}};
  City.art.ew_basalt={box:[240,280,120,230],draw(g,o){
    const h=70+(Math.floor(o.x*7)%4)*23;
    for(const [x,y,k]of [[-32,7,.7],[26,12,.9],[0,0,1]]){
      poly(g,[[x-23,y],[x-23,y-h*k],[x,y-h*k-14],[x+24,y-h*k],[x+24,y],[x,y+12]],C.rock,C.ink,3);
      poly(g,[[x,y+12],[x,y-h*k-14],[x+24,y-h*k],[x+24,y]],'#393843',C.ink,2);
      line(g,[[x-17,y-h*k+4],[x,y-h*k-7],[x+17,y-h*k+3]],C.light,2);
    }
  }};
  // Lava is painted once as continuous terrain, never as repeated object stamps.
  City.art.ew_lava={box:[1,1,0,0],draw(){}};
  const moltenCache=new WeakMap();
  const hash=(x,y)=>{let n=Math.imul(x|0,374761393)^Math.imul(y|0,668265263);n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967295;};
  const smooth=t=>t*t*(3-2*t),mix=(a,b,t)=>a+(b-a)*t;
  function noise(x,y){
    const ix=Math.floor(x),iy=Math.floor(y),u=smooth(x-ix),v=smooth(y-iy);
    return mix(mix(hash(ix,iy),hash(ix+1,iy),u),mix(hash(ix,iy+1),hash(ix+1,iy+1),u),v);
  }
  function moltenTexture(z){
    if(moltenCache.has(z))return moltenCache.get(z);
    const pieces=z.objects.filter(o=>o.kind==='ew_lava'),resolution=12;
    const ymin=Math.floor(Math.min(...pieces.map(o=>o.y-o.r)))-1;
    const ymax=Math.ceil(Math.max(...pieces.map(o=>o.y+o.r)))+1;
    const c=document.createElement('canvas');c.width=z.size*resolution;c.height=(ymax-ymin)*resolution;
    const ctx=c.getContext('2d'),pixels=ctx.createImageData(c.width,c.height);
    // Raster columns sample the actual collision footprint. The wide causeway
    // remains clear; the cooled broken banks belong to the impassable channel.
    const columns=Array.from({length:c.width},(_,px)=>pieces.filter(o=>Math.abs((px+.5)/resolution-o.x)<=o.r));
    for(let py=0;py<c.height;py++)for(let px=0;px<c.width;px++){
      const nearby=columns[px];if(!nearby.length)continue;
      const x=(px+.5)/resolution,y=ymin+(py+.5)/resolution;
      let edge=-Infinity;
      for(const o of nearby)edge=Math.max(edge,o.r-Math.hypot(x-o.x,y-o.y));
      if(edge<=0)continue;
      const drift=noise(x*.31,y*.47),warp=noise(x*.74+19,y*.49-31);
      const u=(x+warp*2.6+noise(x*1.1,y*1.3)*.7)/1.8,v=(y+drift*2.5+noise(x*1.4+9,y*.9)*.7)/1.4;
      const ix=Math.floor(u),iy=Math.floor(v);
      let first=1e9,second=1e9,seed=0;
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
        const gx=ix+dx,gy=iy+dy,h=hash(gx,gy);
        const sx=gx+.16+h*.68,sy=gy+.16+hash(gx+83,gy-29)*.68;
        const d=(u-sx)**2+(v-sy)**2;
        if(d<first){second=first;first=d;seed=h;}else if(d<second)second=d;
      }
      const gap=Math.sqrt(second)-Math.sqrt(first);
      const crust=seed>.22&&gap>.105+warp*.075;
      const bank=Math.max(0,Math.min(1,(.72+noise(x*2,y*2)*.65-edge)*1.8));
      let r,g,b;
      if(crust){
        const rim=Math.exp(-gap*9),grain=noise(x*8,y*8);
        r=34+grain*22+rim*145;g=29+grain*16+rim*32;b=31+grain*14;
      }else{
        const heat=Math.max(0,Math.min(1,.28+drift*.55+Math.exp(-gap*18)*.32));
        r=239+heat*16;g=71+heat*155;b=7+heat*91;
      }
      const grain=noise(x*6+80,y*6-21);
      const k=(py*c.width+px)*4;
      pixels.data[k]=mix(r,29+grain*19,bank);
      pixels.data[k+1]=mix(g,27+grain*15,bank);
      pixels.data[k+2]=mix(b,30+grain*13,bank);
      pixels.data[k+3]=Math.round(255*smooth(Math.max(0,Math.min(1,edge*2.4))));
    }
    ctx.putImageData(pixels,0,0);const result={canvas:c,ymin,height:ymax-ymin};moltenCache.set(z,result);return result;
  }
  function molten(g,G,CH,TW,TH,z){
    const texture=moltenTexture(z),point=(x,y)=>[(x-y)*TW/2-G.ox,(x+y)*TH/2-G.oy];
    const corners=[point(G.x0-.06,G.y0-.06),point(G.x0+CH+.06,G.y0-.06),point(G.x0+CH+.06,G.y0+CH+.06),point(G.x0-.06,G.y0+CH+.06)];
    g.save();g.beginPath();corners.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.clip();
    g.transform(TW/2,TH/2,-TW/2,TH/2,-G.ox,-G.oy);g.imageSmoothingEnabled=true;
    g.drawImage(texture.canvas,0,texture.ymin,z.size,texture.height);g.restore();
  }
  City.art.ew_lantern={box:[150,260,75,220],draw(g){
    beam(g,[[0,6],[0,-145],[20,-155]],10);
    poly(g,[[8,-153],[31,-153],[34,-105],[5,-105]],C.iron,C.ink,3);
    oval(g,19,-127,9,18,C.pale);line(g,[[19,-152],[19,-104]],C.iron,4);
  }};
  City.art.ew_shackle={box:[380,390,190,320],draw(g){
    for(let s of [-1,1]){beam(g,[[s*75,6],[s*67,-151]],22,C.rock);chain(g,s*61,-132,6);}
    oval(g,0,-135,72,37,C.iron);oval(g,0,-138,48,23,C.ink);
    line(g,[[-14,-168],[4,-135],[-9,-117]],C.hot,5);
  }};
  City.art.ew_vent={box:[300,270,150,180],draw(g){
    oval(g,0,0,91,39,C.rock);oval(g,0,-8,58,24,C.ink);oval(g,0,-11,39,15,C.hot);
    for(let x of [-26,0,26])beam(g,[[x,-31],[x+17,-7]],8);
  },animate(g,o,sx,sy,t){
    g.save();for(let j=0;j<4;j++){const k=(t*.16+j*.25)%1;g.globalAlpha=(1-k)*.12;oval(g,sx+Math.sin(j+t*.2)*12,sy-30-k*80,13+k*14,8+k*12,'#d7b7a4',null);}g.restore();
  }};
  City.art.ew_door={box:[720,660,360,555],draw(g){
    for(let s of [-1,1]){
      poly(g,[[s*168,18],[s*154,-298],[s*99,-391],[s*83,-266],[s*111,10]],C.rock,C.ink,7);
      line(g,[[s*139,-15],[s*123,-272],[s*95,-321]],C.hot,6);
    }
    poly(g,[[-110,5],[-106,-271],[-65,-331],[65,-331],[106,-271],[110,5]],'#292731',C.ink,6);
    line(g,[[0,4],[0,-321]],'#ad6743',5);
    for(let n=0;n<9;n++){
      const x=-84+n*21;chain(g,x,-290+Math.abs(n-4)*12,6);
    }
    oval(g,0,-164,29,36,C.iron);oval(g,0,-165,11,14,C.hot);
    for(let s of [-1,1])for(let j=0;j<3;j++){
      const x=s*(132+j*29);beam(g,[[x,15],[x,-59-j*23]],17,C.rock);oval(g,x,-60-j*23,8,4,C.pale);
    }
  }};
  City.art.ew_well={box:[260,230,130,155],draw(g){
    oval(g,0,0,67,31,C.rock);oval(g,0,-29,64,28,C.light);oval(g,0,-31,41,17,C.ink);
    line(g,[[31,-48],[20,-26],[33,-14],[24,13]],C.hot,4);
  }};
  City.art.ew_warmstone={box:[160,80,80,40],draw(g){poly(g,[[-41,0],[-5,-22],[42,0],[2,22]],C.rock,C.ink,2);line(g,[[-26,0],[-2,-8],[10,4],[26,1]],C.hot,3);}};
  City.art.ew_tablet={box:[190,190,95,140],draw(g){
    poly(g,[[-36,5],[-31,-80],[0,-97],[31,-80],[36,5]],C.rock,C.ink,4);
    for(let j=0;j<3;j++){const x=-18+j*18;line(g,[[x,-22],[x,-67],[x+8,-56]],C.pale,2);}
  }};
  City.art.ew_echo={box:[220,210,110,145],draw(g){
    poly(g,[[-51,8],[-33,-43],[-12,-71],[22,-54],[49,-12],[38,13]],C.rock,C.ink,4);
    line(g,[[-5,-62],[4,-39],[-8,-23],[6,4]],C.hot,7);
    oval(g,2,-27,11,15,C.pale,C.hot);
  }};
  function ground(x,y,tone,alt,z,dirt){return dirt?`hsl(28,17%,${40+tone*5+alt*.08}%)`:`hsl(${22+tone*8},8%,${25+tone*8+alt*.12}%)`;}
  function detail(g,px,py,x,y,tw,th){
    const h=Math.abs(Math.sin(x*127.1+y*311.7)*43758.5453)%1;
    if(h<.15){
      const q=h/.15,hot=h<.022,xx=px-22+q*35,yy=py+th*(.3+q*.3);
      line(g,[[xx-17,yy-6],[xx-3,yy],[xx+6,yy-3],[xx+24,yy+5]],hot?'#a9643a':'#352f31',hot?1.8:1.3);
      line(g,[[xx-3,yy],[xx-8,yy+9],[xx+1,yy+13]],hot?'#8d5236':'#3c3435',1);
    }
    if(h>.65){g.fillStyle=h>.85?'#80746b':'#544b48';g.fillRect(px-15+h*24,py+th*.5,2+h*2,1.4);}
  }
  function background(g,w,h,t){
    const gr=g.createLinearGradient(0,0,0,h);gr.addColorStop(0,'#292533');gr.addColorStop(1,'#713b36');g.fillStyle=gr;g.fillRect(0,0,w,h);
    g.save();g.globalAlpha=.12;for(let j=0;j<25;j++){const x=(j*173.7)%w,y=h-(t*10+j*97)%(h+30);oval(g,x,y,1.5,3,C.pale,null);}g.restore();
  }
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);
    for(let s of [-1,1])beam(g,[[s*61,4],[s*56,-118],[s*22,-160]],18,C.rock);
    const gr=g.createRadialGradient(0,-75,4,0,-75,59);gr.addColorStop(0,'#f6dca3');gr.addColorStop(.45,'#d47641');gr.addColorStop(1,'#4b2e38');oval(g,0,-75,45,64,gr);
    for(let s of [-1,1])chain(g,s*60,-115,5);
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle=C.ink;g.lineWidth=4;g.fillStyle=C.pale;const name=window.Locale?.translate(p.name)||p.name;g.strokeText(name,0,-192);g.fillText(name,0,-192);g.restore();
  }
  window.EmberwakeArt={ground,detail,background,portal,molten};
})();
