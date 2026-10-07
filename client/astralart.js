'use strict';
// Astralhollow: living starglass, dusk trees, an impact observatory and its lamps.
// Cached architecture and plants use the same ground anchor as every other zone.
(() => {
  const { iso, poly, prism } = City.kit;
  const OL = '#102638', TAU = Math.PI * 2;
  const rngf = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  function ellipse(g,x,y,rx,ry,fill,stroke=OL,w=2) {
    g.beginPath(); g.ellipse(x,y,rx,ry,0,0,TAU); g.fillStyle=fill; g.fill();
    if(stroke){g.strokeStyle=stroke;g.lineWidth=w;g.stroke();}
  }
  function line(g,pts,col,w=2){g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=col;g.lineWidth=w;g.lineJoin='round';g.lineCap='round';g.stroke();}
  function shard(g,x,y,w,h,pal,lean=0){
    poly(g,[[x-w,y],[x-w*.8+lean*.3,y-h*.68],[x+lean,y-h],[x+w*.75+lean*.3,y-h*.59],[x+w,y]],pal[1],OL,3);
    poly(g,[[x-w,y],[x-w*.8+lean*.3,y-h*.68],[x+lean,y-h],[x,y]],pal[0],null);
    poly(g,[[x+lean,y-h],[x+w*.75+lean*.3,y-h*.59],[x+w,y],[x,y]],pal[2],null);
    line(g,[[x+lean,y-h],[x,y]],'rgba(241,255,255,.75)',2);
  }
  const CRYSTAL = [
    ['#aff9eb','#5fc0d6','#386391'],['#f0c8ff','#ae83dc','#584d9a'],
    ['#ffdcaa','#e6ab8a','#895576'],['#c9daff','#829ee0','#435c91']
  ];
  City.art.crystal = {box:[260,325,130,275],draw(g,o){
    const v=o.v%4,p=CRYSTAL[v],h=105+v*11;
    ellipse(g,2,3,52,14,'rgba(7,20,36,.4)',null);
    shard(g,-26,-3,17,h*.58,p,-9);shard(g,25,-4,16,h*.72,p,10);shard(g,1,-5,21,h,p,4);
    for(let k=0;k<5;k++)ellipse(g,-35+k*17,-4-k%2*3,4,2,k%2?p[0]:p[1],null);
  },animate(g,o,sx,sy,t){const a=.27+.18*Math.sin(t*1.35+o.x*.4);g.save();g.globalAlpha=a;g.shadowColor=CRYSTAL[o.v%4][0];g.shadowBlur=21;g.fillStyle=CRYSTAL[o.v%4][0];g.beginPath();g.ellipse(sx,sy-81,9,16,0,0,TAU);g.fill();g.restore();}};
  City.art.starstone = {box:[220,200,110,162],draw(g,o){
    const v=o.v%4,r=rngf(400+v*31),p=CRYSTAL[(v+2)%4];
    ellipse(g,4,2,38,10,'rgba(7,20,36,.35)',null);
    poly(g,[[-36,-3],[-40,-22],[-22,-44],[11,-48],[37,-27],[34,-5],[12,2]],'#53626f',OL,3);
    poly(g,[[-36,-3],[-40,-22],[-22,-44],[-8,-25],[0,0]],'#8999a1',null);
    for(let i=0;i<6;i++){const x=-21+i*8,y=-13-r()*20;line(g,[[x,y],[x+4,y-4],[x+8,y-2]],i%2?p[0]:p[1],1.5);}
    shard(g,19,-22,7,28,p,5);
  }};
  City.art.astraltree = {box:[370,490,185,432],draw(g,o){
    const v=o.v%4,r=rngf(700+v*47),can=[['#a6ebd4','#52959b','#214e65'],['#d2bef4','#866ab0','#3e477e'],['#f9bed9','#b56e9b','#54476f'],['#bee6ed','#70a2bd','#355477']][v];
    ellipse(g,4,4,54,15,'rgba(2,17,29,.4)',null);
    line(g,[[-25,0],[-9,-23],[-8,-84],[-28,-124]],OL,25);line(g,[[-25,0],[-9,-23],[-8,-84],[-28,-124]],'#b9d5c8',18);
    line(g,[[20,0],[10,-26],[-8,-80],[7,-153]],OL,24);line(g,[[20,0],[10,-26],[-8,-80],[7,-153]],'#d8e5d0',17);
    for(const [x,y,rx,ry] of [[-41,-157,42,35],[32,-159,42,37],[-4,-192,55,48],[-51,-191,29,27],[42,-193,31,28]]){
      const gr=g.createRadialGradient(x-rx*.3,y-ry*.4,2,x,y,rx*1.1);gr.addColorStop(0,can[0]);gr.addColorStop(.58,can[1]);gr.addColorStop(1,can[2]);ellipse(g,x,y,rx,ry,gr,OL,3.5);
    }
    for(let i=0;i<24;i++){const x=(r()-.5)*113,y=-147-r()*75;if((x/66)**2+((y+181)/66)**2<1)ellipse(g,x,y,2+r()*3,1.4, i%4===0?'#fff3cb':'rgba(226,255,238,.58)',null);}
    line(g,[[-9,-67],[-12,-95]],'#718a85',3);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.25+.2*Math.sin(t*1.8+o.y);g.fillStyle='#f4f0c5';g.shadowColor='#dcfaff';g.shadowBlur=12;for(let i=0;i<3;i++){const x=sx+Math.sin(t*.7+i*2+o.x)*27+(i-1)*21,y=sy-130-i*27+Math.cos(t*.6+i)*7;ellipse(g,x,y,2.2,2.2,'#e5f9e5',null);}g.restore();}};
  City.art.astralshrub = {box:[210,190,105,154],draw(g,o){
    const v=o.v%4,r=rngf(900+v*29),p=['#60b79b','#80b6b2','#9d91c4','#96c89e'][v];
    ellipse(g,0,2,29,9,'rgba(4,28,30,.35)',null);
    for(let i=0;i<15;i++){const x=-25+i*3.5,h=18+r()*22,b=(r()-.5)*18;
      line(g,[[x,0],[x+b*.5,-h*.55],[x+b,-h]],OL,4);
      line(g,[[x,0],[x+b*.5,-h*.55],[x+b,-h]],p,2.2);
      ellipse(g,x+b,-h,2.5,4.2,i%4===0?'#f5c5df':'#b7e7d7',null);
    }
  }};
  City.art.starbloom = {box:[150,165,75,140],draw(g,o){
    const v=o.v%4,p=CRYSTAL[v];ellipse(g,0,1,18,6,'rgba(4,28,30,.25)',null);
    for(let i=0;i<7;i++){const x=(i-3)*4.8,h=12+(i*17+v*13)%17;
      line(g,[[x,0],[x+((i%3)-1)*4,-h]],'#397d69',2);
      ellipse(g,x+((i%3)-1)*4,-h,4,2.8,p[i%3],null);
    }
  }};
  City.art.obelisk = {box:[250,390,125,335],draw(g,o){
    const v=o.v%4,p=CRYSTAL[v],h=155+v*12;
    ellipse(g,3,3,48,14,'rgba(4,18,32,.45)',null);
    prism(g,1.7,1.7,15,'#87989a','#516a75','#334f66');
    shard(g,0,-12,23,h,p,v%2?9:-7);
    for(let i=0;i<3;i++){const y=-45-i*38;line(g,[[-8,y],[0,y-8],[8,y],[0,y+7]],'#f2e6b8',2);}
  },animate(g,o,sx,sy,t){const a=.22+.15*Math.sin(t*1.4+o.x);g.save();g.globalAlpha=a;g.shadowColor='#b5efff';g.shadowBlur=20;g.fillStyle='#b9eaf1';g.fillRect(sx-5,sy-130,10,22);g.restore();}};
  City.art.astrolamp = {box:[180,320,90,273],draw(g,o){
    ellipse(g,0,2,27,8,'rgba(3,17,29,.37)',null);
    prism(g,.7,.7,13,'#8ea6ad','#64798c','#435668');
    line(g,[[0,-10],[0,-124]],OL,12);line(g,[[0,-10],[0,-124]],'#c5d6cf',8);
    poly(g,[[-16,-121],[0,-146],[16,-121],[11,-106],[-11,-106]],'#94dee5',OL,3);
    poly(g,[[-9,-120],[0,-137],[9,-120],[6,-111],[-6,-111]],'#fff3c1',null);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.38+.24*Math.sin(t*2+o.x);g.shadowColor='#f5dca2';g.shadowBlur=28;ellipse(g,sx,sy-123,7,12,'#f8e9b4',null);g.restore();}};
  City.art.starwell = {box:[320,290,160,225],draw(g){
    ellipse(g,0,5,90,37,'rgba(6,19,31,.4)',null);
    ellipse(g,0,0,75,31,'#627888',OL,4);ellipse(g,0,-12,70,28,'#a1b7bd',OL,3);
    ellipse(g,0,-14,59,22,'#244d68','#b5cbd1',2);
    for(let i=0;i<8;i++){const a=i*TAU/8;ellipse(g,Math.cos(a)*56,Math.sin(a)*21-17,5,3.3,'#dddfc2',null);}
    shard(g,0,-14,15,63,CRYSTAL[0]);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.22+.14*Math.sin(t*2);g.shadowColor='#a6eaff';g.shadowBlur=25;ellipse(g,sx,sy-43,16,24,'#b6f7f1',null);g.restore();}};
  function building(g,o,high=false){
    const w=o.width,d=o.depth,h=high?175:108;
    ellipse(g,0,10,(w+d)*26,(w+d)*9,'rgba(3,15,31,.35)',null);
    prism(g,w+.4,d+.4,12,'#8fa1a7','#64788b','#40566e');
    prism(g,w,d,h,'#c4d8d5','#71889b','#4f6481',12);
    for(let i=-1;i<=1;i++){const p=iso(i*w/3,d/2+.02,h*.45);poly(g,[[p[0]-9,p[1]-20],[p[0]+9,p[1]-20],[p[0]+9,p[1]+18],[p[0]-9,p[1]+18]],'#fae4af','#20354a',3);line(g,[[p[0],p[1]-18],[p[0],p[1]+18]],'#658b9b',2);}
    const a=iso(-w/2,-d/2,h+12),b=iso(w/2,-d/2,h+12),c=iso(w/2,d/2,h+12),e=iso(-w/2,d/2,h+12);
    const peak=iso(0,0,h+(high?116:70));
    poly(g,[a,b,peak],'#a8ccd0',OL,3);poly(g,[b,c,peak],'#5c85aa',OL,3);poly(g,[c,e,peak],'#354d78',OL,3);poly(g,[e,a,peak],'#7597b2',OL,3);
    line(g,[peak,iso(0,0,h+12)],'#ddf2e8',3);
    if(high){for(let i=0;i<6;i++){const a=i*TAU/6;const p=iso(Math.cos(a)*2.5,Math.sin(a)*2.5,h+55);shard(g,p[0],p[1],9,44,CRYSTAL[i%4]);}}
  }
  City.art.astralhouse={box:[620,560,310,455],draw(g,o){building(g,o);}};
  City.art.observatory={box:[850,750,425,615],draw(g,o){building(g,o,true);
    ellipse(g,0,-214,59,27,'#829db3',OL,4);ellipse(g,0,-221,44,18,'#142e51','#d1e5dc',3);
    for(let i=0;i<8;i++){const a=i*TAU/8;ellipse(g,Math.cos(a)*38,Math.sin(a)*15-221,3.2,3.2,i%2?'#ffe4ad':'#baf4ef',null);}
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.2+.12*Math.sin(t*.8);g.shadowColor='#a5eff6';g.shadowBlur=40;ellipse(g,sx,sy-390,28,16,'#c5edf4',null);g.restore();}};
})();
