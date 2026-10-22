'use strict';
// Iron courts suspended over the first forge. The visible banks use the collision floor mask.
(()=>{
  const {iso,poly}=City.kit,TAU=Math.PI*2;
  const C={ink:'#160f18',basalt:'#302b36',edge:'#827c87',iron:'#504852',hot:'#ff9751',lava:'#ed512e',cyan:'#77e5df',pink:'#f281be',pale:'#fff0ce'};
  const line=(g,p,c,w=2)=>{g.beginPath();p.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.lineCap='round';g.stroke();};
  const oval=(g,x,y,rx,ry,c,edge=C.ink,w=2)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();if(edge){g.strokeStyle=edge;g.lineWidth=w;g.stroke();}};
  const beam=(g,p,w=12,c=C.iron)=>{line(g,p,C.ink,w+5);line(g,p,c,w);line(g,p.map(([x,y])=>[x-2,y-2]),C.edge,2);};
  const floor=(z,x,y)=>z.forgeFloor?.[y]?.[x]==='=';
  const hall=(z,x,y)=>z.forgeHalls?.find(h=>((x-h.x)/h.rx)**2+((y-h.y)/h.ry)**2<1);
  function ground(x,y,tone,alt,z){
    const h=hall(z,x,y),edge=!floor(z,x-1,y)||!floor(z,x+1,y)||!floor(z,x,y-1)||!floor(z,x,y+1);
    return edge?'#87716b':h?`hsl(${h.id==='throne'?343:260},${h.id==='rhythm'?16:9}%,${25+tone*9+(x+y)%2}%)`:`hsl(275,8%,${30+tone*8+alt*.4}%)`;
  }
  function detail(g,px,py,x,y,tw,th,z){
    const at=(u,v)=>[px+(u-v)*tw/2,py+th/2+(u+v)*th/2];
    line(g,[at(-.49,-.49),at(.49,-.49),at(.49,.49)],'#211d27',1.5);
    const h=hall(z,x,y);
    if(!h){
      line(g,[at(-.42,-.32),at(.42,-.32)],'#776872',2);
      if((x+y)%3===0)line(g,[at(-.32,-.29),at(-.32,.38)],'#4c4650',3);
    }else if(h.id==='rhythm'&&x%4===0&&y%4===0){
      poly(g,[at(-.45,-.45),at(.45,-.45),at(.45,.45),at(-.45,.45)],'#44384d',C.pink,1);
    }else if((x*17+y*7)%19===0){
      line(g,[at(-.3,-.25),at(.04,.06),at(-.04,.3)],'#c76443',1.5);
    }
    const edges=[[-1,0,[[-.5,.5],[-.5,-.5]]],[0,-1,[[-.5,-.5],[.5,-.5]]],[1,0,[[.5,-.5],[.5,.5]]],[0,1,[[.5,.5],[-.5,.5]]]];
    for(const [dx,dy,points] of edges)if(!floor(z,x+dx,y+dy)){
      const p=points.map(([u,v])=>at(u,v));
      poly(g,[p[0],p[1],[p[1][0],p[1][1]+24],[p[0][0],p[0][1]+24]],'#231b24',C.ink,1);
      line(g,p,'#e19464',3);
      if((x+y)%3===0)line(g,p.map(([u,v])=>[u,v+6]),C.hot,2);
    }
    if((x+y)%7===0){oval(g,px-12,py+th/2,2,1.5,C.edge,null);oval(g,px+12,py+th/2,2,1.5,C.edge,null);}
  }
  City.art.cf_lantern={box:[110,180,55,150],draw(g,o){
    beam(g,[[0,4],[0,-87]],10);poly(g,[[-16,-86],[0,-112],[16,-86],[9,-61],[-9,-61]],C.iron,C.ink,3);
    oval(g,0,-85,7,13,o.v%2?C.pink:C.cyan,C.pale,1);
  }};
  City.art.cf_pylon={box:[250,420,125,350],draw(g,o){
    poly(g,[[-35,12],[-44,-208],[-24,-264],[20,-282],[42,-208],[34,12],[0,30]],C.basalt,C.ink,4);
    line(g,[[-22,-17],[-29,-202],[-12,-242]],o.v%2?C.pink:C.cyan,6);
    for(let k=0;k<5;k++)oval(g,12,-34-k*35,23,10,C.iron,C.edge,2);
    beam(g,[[0,-272],[31,-315],[59,-320]],11);oval(g,59,-306,18,24,C.iron,C.edge,4);
  }};
  City.art.cf_chain={box:[620,350,310,290],draw(g){
    for(let s of [-1,1])beam(g,[[s*205,16],[s*180,-218]],27);
    for(let k=0;k<11;k++){const x=-180+k*36,y=-184+Math.sin(k*Math.PI/10)*65;
      oval(g,x,y,k%2?13:23,k%2?25:13,C.basalt,C.edge,5);}
  }};
  City.art.cf_bellows={box:[520,440,260,360],draw(g){
    for(let s of [-1,1]){poly(g,[[s*14,-30],[s*168,-70],[s*137,-219],[s*36,-234]],C.iron,C.ink,5);
      for(let j=0;j<6;j++)line(g,[[s*(41+j*18),-73-j*2],[s*(33+j*17),-214+j*2]],'#201b25',8);}
    beam(g,[[-28,0],[-28,-256],[28,-256],[28,0]],19);oval(g,0,-179,26,45,C.hot,C.ink,4);
  }};
  City.art.cf_anvil={box:[400,300,200,240],draw(g){
    poly(g,[[-91,-116],[85,-116],[136,-91],[69,-68],[43,-65],[31,-14],[67,4],[-68,4],[-31,-14],[-44,-71],[-91,-82]],C.iron,C.ink,5);
    line(g,[[-88,-109],[77,-109],[121,-92]],C.cyan,4);beam(g,[[-100,9],[99,9]],20);
  }};
  City.art.cf_furnace={box:[440,480,220,400],draw(g){
    poly(g,[[-104,15],[-108,-213],[-62,-278],[62,-278],[108,-213],[104,15]],C.basalt,C.ink,5);
    poly(g,[[-63,-31],[-65,-178],[-41,-211],[41,-211],[65,-178],[63,-31]],C.hot,C.lava,8);
    for(let x=-48;x<=48;x+=24)beam(g,[[x,-198],[x,-35]],8);
    for(let s of [-1,1])beam(g,[[s*58,-276],[s*58,-337]],23);
  }};
  City.art.cf_valve={box:[360,300,180,240],draw(g){
    beam(g,[[0,12],[0,-124]],24);oval(g,0,-142,74,55,C.basalt,C.ink,6);
    for(let i=0;i<6;i++){const a=i*TAU/6;beam(g,[[0,-142],[Math.cos(a)*66,-142+Math.sin(a)*48]],9,C.hot);}
    oval(g,0,-142,17,14,C.cyan,C.ink,3);
  }};
  City.art.cf_quench={box:[460,300,230,230],draw(g){
    oval(g,0,-18,153,64,C.iron,C.ink,6);oval(g,0,-27,130,49,'#33575d',C.cyan,4);
    for(let k=0;k<4;k++){const x=-80+k*55;beam(g,[[x,-63],[x,-126]],9);oval(g,x,-132,11,19,C.cyan,C.ink,2);}
  }};
  City.art.cf_speaker={box:[390,420,195,350],draw(g){
    for(let s of [-1,1]){poly(g,[[s*25,8],[s*139,8],[s*139,-255],[s*25,-255]],C.basalt,C.ink,5);
      for(let k=0;k<2;k++){oval(g,s*82,-64-k*119,43,47,'#211c2b',C.pink,5);oval(g,s*82,-64-k*119,18,20,C.iron,C.edge,3);}}
  }};
  City.art.cf_mirror={box:[400,430,200,360],draw(g){
    beam(g,[[-85,15],[-85,-211],[0,-287],[85,-211],[85,15]],20);
    poly(g,[[-64,-16],[-64,-191],[0,-251],[64,-191],[64,-16]],'#a3bbbf',C.cyan,6);
    line(g,[[-43,-38],[37,-179]],C.pale,7);line(g,[[-38,-110],[20,-212]],'#dce8e4',3);
  }};
  City.art.cf_throne={box:[780,670,390,570],draw(g){
    for(let s of [-1,1]){poly(g,[[s*44,16],[s*220,16],[s*190,-138],[s*113,-150]],C.basalt,C.ink,6);
      beam(g,[[s*113,-151],[s*131,-371],[s*73,-475]],29);line(g,[[s*129,-162],[s*140,-351]],C.hot,6);}
    poly(g,[[-101,-107],[-113,-360],[0,-432],[113,-360],[101,-107]],C.iron,C.ink,7);
    for(let k=0;k<9;k++){const x=-80+k*20;line(g,[[x,-122],[x,-330-Math.abs(x)*.4]],k%2?C.pink:C.cyan,5);}
    oval(g,0,-318,37,53,C.hot,C.ink,5);beam(g,[[-104,-105],[104,-105]],34,C.basalt);
    poly(g,[[-153,47],[153,47],[111,-43],[-111,-43]],C.iron,C.ink,5);
  }};
  City.art.cf_rally={box:[210,130,105,80],draw(g,o){
    oval(g,0,0,64,27,C.iron,C.ink,4);oval(g,0,-4,43,18,C.basalt,C.cyan,3);
    g.font='bold 24px sans-serif';g.textAlign='center';g.fillStyle=C.pale;g.fillText(String(o.v+1),0,-1);
  }};
  City.art.cf_vent={box:[230,150,115,90],draw(g){
    oval(g,0,0,72,29,C.basalt,C.ink,4);oval(g,0,-5,54,21,'#b74733',C.hot,3);
    for(let x=-36;x<=36;x+=18)line(g,[[x-14,-16],[x+14,8]],C.iron,7);
    line(g,[[-53,9],[-27,22],[26,22],[53,9]],C.edge,3);
  }};
  City.art.cf_lavafall={box:[520,620,260,210],draw(g){
    poly(g,[[-115,-54],[-64,-103],[45,-90],[104,-28],[77,24],[-76,30]],C.basalt,C.ink,5);
    const gr=g.createLinearGradient(0,-61,0,338);gr.addColorStop(0,C.pale);gr.addColorStop(.3,C.hot);gr.addColorStop(1,'#ba3b2d');
    poly(g,[[-58,-53],[52,-53],[47,294],[13,343],[-33,308]],gr,C.lava,5);
    for(let k=0;k<6;k++)line(g,[[-42+k*16,-40],[-35+k*14,150],[k*7-15,302]],k%2?C.hot:C.pale,k%2?5:3);
    oval(g,0,-54,62,22,C.hot,C.pale,4);
  }};
  City.art.cf_gateway={box:[420,390,210,320],draw(g){for(let s of [-1,1])beam(g,[[s*104,10],[s*104,-202],[s*45,-263]],25);beam(g,[[-44,-262],[44,-262]],22);}};
  const moltenChunks=new WeakMap(),LAVA_CHUNK=8,LAVA_RES=12;
  function moltenChunk(z,cx,cy){
    let cache=moltenChunks.get(z);if(!cache){cache=new Map();moltenChunks.set(z,cache);}
    const key=cx+','+cy;
    if(cache.has(key)){const c=cache.get(key);cache.delete(key);cache.set(key,c);return c;}
    const x0=cx*LAVA_CHUNK,y0=cy*LAVA_CHUNK,c=document.createElement('canvas');
    c.width=c.height=LAVA_CHUNK*LAVA_RES+2;
    const g=c.getContext('2d'),pixels=g.createImageData(c.width,c.height),banks=[];
    // Match the river's cooled shoreline against the actual floor, including bridges.
    for(let y=y0-2;y<=y0+LAVA_CHUNK+1;y++)for(let x=x0-2;x<=x0+LAVA_CHUNK+1;x++)
      if(floor(z,x,y)&&(!floor(z,x-1,y)||!floor(z,x+1,y)||!floor(z,x,y-1)||!floor(z,x,y+1)))banks.push([x,y]);
    for(let py=0;py<c.height;py++)for(let px=0;px<c.width;px++){
      const x=x0+(px-.5)/LAVA_RES,y=y0+(py-.5)/LAVA_RES;
      let edge=Infinity;
      for(const [bx,by]of banks){
        const dx=Math.max(bx-x,0,x-bx-1),dy=Math.max(by-y,0,y-by-1);
        if(dx<1.5&&dy<1.5)edge=Math.min(edge,Math.hypot(dx,dy));
      }
      pixels.data.set(EmberwakeArt.moltenColor(x,y,edge),(py*c.width+px)*4);
    }
    g.putImageData(pixels,0,0);cache.set(key,c);
    if(cache.size>96)cache.delete(cache.keys().next().value);
    return c;
  }
  function background(g,w,h,t,z,cx,cy,tw=88,th=44){
    g.fillStyle='#292533';g.fillRect(0,0,w,h);
    const corners=[[0,0],[w,0],[w,h],[0,h]].map(([x,y])=>[(x-w/2+cx)/tw+(y-h/2+cy)/th,
      (y-h/2+cy)/th-(x-w/2+cx)/tw]);
    const minX=Math.floor(Math.min(...corners.map(p=>p[0]))/LAVA_CHUNK),maxX=Math.floor(Math.max(...corners.map(p=>p[0]))/LAVA_CHUNK);
    const minY=Math.floor(Math.min(...corners.map(p=>p[1]))/LAVA_CHUNK),maxY=Math.floor(Math.max(...corners.map(p=>p[1]))/LAVA_CHUNK);
    g.save();g.imageSmoothingEnabled=true;
    g.transform(tw/2,th/2,-tw/2,th/2,w/2-cx,h/2-cy);
    for(let y=minY;y<=maxY;y++)for(let x=minX;x<=maxX;x++){
      const left=(x-y-1)*LAVA_CHUNK*tw/2+w/2-cx,top=(x+y)*LAVA_CHUNK*th/2+h/2-cy;
      if(left>w||left+LAVA_CHUNK*tw<0||top>h||top+LAVA_CHUNK*th<0)continue;
      const pad=1/LAVA_RES;
      g.drawImage(moltenChunk(z,x,y),x*LAVA_CHUNK-pad,y*LAVA_CHUNK-pad,LAVA_CHUNK+2*pad,LAVA_CHUNK+2*pad);
    }
    g.restore();
  }
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);for(let s of [-1,1])beam(g,[[s*64,8],[s*65,-127],[s*26,-176]],18);
    const gr=g.createRadialGradient(0,-80,3,0,-80,67);gr.addColorStop(0,C.pale);gr.addColorStop(.4,C.hot);gr.addColorStop(1,'#5b2637');
    oval(g,0,-85,49,72,gr,C.ink,4);line(g,[[-37,-29],[-37,-122],[0,-159],[37,-122],[37,-29]],C.cyan,3);
    for(let k=0;k<3;k++)oval(g,-40+k*40,-181-(k%2)*8,8,12,C.iron,C.edge,3);
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.strokeStyle=C.ink;g.lineWidth=4;g.fillStyle=C.pale;
    const name=window.Locale?.translate(p.name)||p.name;g.strokeText(name,0,-216);g.fillText(name,0,-216);g.restore();
  }
  window.ChainedForgeArt={floor,ground,detail,background,portal};
})();
