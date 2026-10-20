'use strict';
// Violet burial slabs, amber bindings and woven fate diagrams below the Norn Stones.
(() => {
  const {iso,poly,prism} = City.kit, TAU=Math.PI*2;
  const stroke=(g,points,color,width=2)=>{g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=color;g.lineWidth=width;g.stroke();};
  const ellipse=(g,x,y,rx,ry,color)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=color;g.fill();};
  City.art.norn_wall={box:[440,430,220,330],draw(g,o){
    const w=o.width,d=o.depth;
    prism(g,w,d,88,'#aaa0b0','#655a73','#40384d');
    prism(g,w*1.04,d*1.04,10,'#c5b7bc','#857484','#56465d',88);
    for(let i=-1;i<=1;i++){
      const x=i*w*.28;
      stroke(g,[iso(x,d/2,8),iso(x,d/2,77)],'#cba267',5);
      stroke(g,[iso(x-.1,d/2,16),iso(x+.1,d/2,68)],'#f1d79c',1.5);
    }
    for(const h of [26,57])stroke(g,[iso(-w/2,d/2,h),iso(w/2,d/2,h)],'#43394f',2);
    const p=iso(0,d/2,45);
    poly(g,[[p[0]-12,p[1]],[p[0],p[1]-14],[p[0]+12,p[1]],[p[0],p[1]+14]],'#8d7189','#edca83',2);
  }};
  City.art.norn_lamp={box:[170,230,85,200],draw(g){
    prism(g,.55,.55,38,'#aaa0ae','#66516e','#403448');
    ellipse(g,0,-60,18,7,'#e7bc6b');ellipse(g,0,-80,7,25,'#f4dba0');
    ellipse(g,-2,-84,3,17,'#fff1cc');
  },animate(g,o,t){g.save();g.shadowColor='#f9dc91';g.shadowBlur=20+4*Math.sin(t*2+o.x);ellipse(g,0,-80,5,16,'#ffedb6');g.restore();}};
  City.art.norn_spindle={box:[190,205,95,180],draw(g){
    prism(g,.8,.8,15,'#b0a0ad','#6c566d','#423548');
    stroke(g,[[0,-15],[0,-123]],'#d5ab6b',8);
    ellipse(g,0,-41,21,8,'#b68950');ellipse(g,0,-94,21,8,'#ebc98b');
    for(let j=0;j<7;j++)stroke(g,[[-15,-44-j*7],[15,-48-j*7]],j%2?'#e8c18a':'#b98863',3);
    poly(g,[[-8,-122],[0,-141],[8,-122],[0,-109]],'#f6dfa6','#5b435d',2);
  }};
  City.art.norn_sarcophagus={box:[270,210,135,170],draw(g){
    prism(g,1,2,33,'#b8a5b4','#78637e','#4a3c59');
    prism(g,1.1,2.1,8,'#d5b9c0','#957c94','#6a536f',33);
    stroke(g,[[0,-60],[0,-90]],'#f3d591',4);ellipse(g,0,-98,10,8,'#cda66a');
  }};
  City.art.norn_loom={box:[390,340,195,300],draw(g){
    for(const s of [-1,1]){g.save();g.translate(s*108,0);prism(g,.45,.45,166,'#a98155','#72523f','#443548');g.restore();}
    stroke(g,[[-108,-166],[108,-166]],'#b99863',14);
    stroke(g,[[-104,-53],[104,-53]],'#b99863',10);
    for(let i=-4;i<=4;i++)stroke(g,[[i*21,-159],[i*21+Math.sin(i)*8,-57]],i%2?'#eed29e':'#b9a1c6',2);
    poly(g,[[-56,-115],[0,-153],[56,-115],[0,-77]],'#66517c','#efcc8d',4);
    ellipse(g,0,-114,13,13,'#f9e1a5');
  }};
  function room(x,y,z){return (z.rooms||[]).findIndex(([x0,y0,x1,y1])=>x>=x0&&x<x1&&y>=y0&&y<y1);}
  function ground(x,y,tone,alt,z){
    const i=room(x,y,z),r=z.rooms?.[i];
    if(!r)return '#241f30';
    const big=i<6, dx=x+.5-(r[0]+r[2])/2,dy=y+.5-(r[1]+r[3])/2;
    const edge=Math.min(x-r[0],y-r[1],r[2]-1-x,r[3]-1-y)<1;
    const thread=big&&(Math.abs(dx-dy)<.8||Math.abs(dx+dy)<.8||Math.abs(dx)<.7);
    if(edge)return '#c0a07a';
    if(thread)return i===5?'#d1b57d':'#a69aac';
    return `hsl(${269+(i%3)*6},${15+tone*5}%,${(big?37:29)+tone*5+((x+y)%2)*2}%)`;
  }
  function detail(g,px,py,x,y,tw,th,z){
    if(room(x,y,z)<0)return;
    stroke(g,[[px-tw/2,py+th/2],[px,py],[px+tw/2,py+th/2]],'rgba(43,31,54,.30)',1.3);
    if((x*7+y*11)%17===0){
      stroke(g,[[px-13,py+th/2],[px,py+th/2-6],[px+13,py+th/2],[px,py+th/2+6],[px-13,py+th/2]],'#dcc28c',1.3);
      stroke(g,[[px,py+th/2-10],[px,py+th/2+10]],'#b7a1c2',1);
    }
  }
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);
    for(const s of [-1,1])poly(g,[[s*48,0],[s*43,-100],[s*25,-133],[s*18,-118],[s*29,-82],[s*31,0]],'#6c596e','#c6aa7c',3);
    poly(g,[[-46,-103],[-32,-140],[32,-140],[46,-103]],'#78657d','#d7b980',3);
    const gr=g.createRadialGradient(0,-56,1,0,-56,57);gr.addColorStop(0,'#edcc8b');gr.addColorStop(.5,'#8f719c');gr.addColorStop(1,'#2b263c');
    ellipse(g,0,-57,31,53,gr);
    for(let i=-2;i<=2;i++)stroke(g,[[i*9,-101],[i*9+Math.sin(t+i)*2,-14]],'rgba(255,231,174,.6)',1);
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.lineWidth=4;g.strokeStyle='#241d30';g.fillStyle='#fae5b5';
    const name=window.Locale?.translate(p.name)||p.name;g.strokeText(name,0,-154);g.fillText(name,0,-154);g.restore();
  }
  window.NornrootArt={ground,detail,portal};
})();
