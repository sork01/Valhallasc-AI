'use strict';
// Prismatic marble arches, golden Bifrost ribs and rainbow shard-braziers beneath Heimdall's Perch.
(() => {
  const {iso,poly,prism} = City.kit, TAU=Math.PI*2;
  const stroke=(g,points,color,width=2)=>{g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=color;g.lineWidth=width;g.stroke();};
  const ellipse=(g,x,y,rx,ry,color)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=color;g.fill();};
  City.art.span_wall={box:[440,430,220,330],draw(g,o){
    const w=o.width,d=o.depth;
    prism(g,w,d,88,'#b6c8dc','#6782a4','#3b4e6b');
    prism(g,w*1.04,d*1.04,10,'#d4e4f4','#849ebe','#526888',88);
    for(let i=-1;i<=1;i++){
      const x=i*w*.28;
      stroke(g,[iso(x,d/2,8),iso(x,d/2,77)],'#deb464',5);
      stroke(g,[iso(x-.1,d/2,16),iso(x+.1,d/2,68)],'#8ef0ff',1.5);
    }
    for(const h of [26,57])stroke(g,[iso(-w/2,d/2,h),iso(w/2,d/2,h)],'#364966',2);
    const p=iso(0,d/2,45);
    poly(g,[[p[0]-12,p[1]],[p[0],p[1]-14],[p[0]+12,p[1]],[p[0],p[1]+14]],'#62c8ec','#f4d58c',2);
  }};
  City.art.span_brazier={box:[170,230,85,200],draw(g){
    prism(g,.55,.55,38,'#b8c8da','#6a7f9e','#3e4e68');
    ellipse(g,0,-60,18,7,'#dfb464');ellipse(g,0,-80,8,25,'#7ce8ff');
    ellipse(g,-2,-84,3.5,17,'#fff6d2');
  },animate(g,o,t){g.save();g.shadowColor='#7eeeff';g.shadowBlur=20+4*Math.sin(t*2.2+o.x);ellipse(g,0,-80,5,16,'#ccf8ff');g.restore();}};
  City.art.span_prism={box:[190,205,95,180],draw(g){
    prism(g,.8,.8,15,'#bccde0','#6e84a3','#41526e');
    stroke(g,[[0,-15],[0,-122]],'#deb668',8);
    ellipse(g,0,-42,21,8,'#c6964e');ellipse(g,0,-94,21,8,'#84e4ff');
    for(let j=0;j<7;j++)stroke(g,[[-15,-44-j*7],[15,-48-j*7]],j%2?'#88e8ff':'#d8a4f8',3);
    poly(g,[[-10,-120],[0,-143],[10,-120],[0,-106]],'#92f2ff','#465b78',2);
  }};
  City.art.span_obelisk={box:[270,210,135,170],draw(g){
    prism(g,1,2,34,'#bed0e2','#7389a8','#465975');
    prism(g,1.1,2.1,8,'#dceaf8','#8fa6c4','#5e7494',34);
    stroke(g,[[0,-58],[0,-92]],'#88ecff',4);ellipse(g,0,-100,10,8,'#dfb668');
  }};
  City.art.span_arch={box:[390,340,195,300],draw(g){
    for(const s of [-1,1]){g.save();g.translate(s*108,0);prism(g,.48,.48,166,'#c8d8ea','#7890b0','#465a78');g.restore();}
    stroke(g,[[-108,-166],[108,-166]],'#dfb668',14);
    stroke(g,[[-104,-53],[104,-53]],'#7ec8e8',10);
    const rays=['#ff8a8a','#ffc46b','#f6f088','#82ec9e','#7ce8ff','#9caeff','#df9cff'];
    for(let i=-3;i<=3;i++)stroke(g,[[i*26,-159],[i*18,-57]],rays[i+3],3);
    poly(g,[[-54,-115],[0,-154],[54,-115],[0,-76]],'#5478a4','#f6da92',4);
    ellipse(g,0,-114,14,14,'#98f4ff');
  }};
  function room(x,y,z){return (z.rooms||[]).findIndex(([x0,y0,x1,y1])=>x>=x0&&x<x1&&y>=y0&&y<y1);}
  function ground(x,y,tone,alt,z){
    const i=room(x,y,z),r=z.rooms?.[i];
    if(!r)return '#1b2438';
    const big=i<6, dx=x+.5-(r[0]+r[2])/2,dy=y+.5-(r[1]+r[3])/2;
    const edge=Math.min(x-r[0],y-r[1],r[2]-1-x,r[3]-1-y)<1;
    const inlay=big&&(Math.abs(dx-dy)<.8||Math.abs(dx+dy)<.8||Math.abs(dx)<.7);
    if(edge)return '#c8a86c';
    if(inlay)return i===5?'#7cd8f0':'#9ab4d4';
    return `hsl(${202+(i%3)*6},${22+tone*5}%,${(big?40:31)+tone*5+((x+y)%2)*2}%)`;
  }
  function detail(g,px,py,x,y,tw,th,z){
    if(room(x,y,z)<0)return;
    stroke(g,[[px-tw/2,py+th/2],[px,py],[px+tw/2,py+th/2]],'rgba(28,44,68,.28)',1.3);
    if((x*7+y*11)%17===0){
      stroke(g,[[px-13,py+th/2],[px,py+th/2-6],[px+13,py+th/2],[px,py+th/2+6],[px-13,py+th/2]],'#82def8',1.3);
      stroke(g,[[px,py+th/2-10],[px,py+th/2+10]],'#e6c882',1);
    }
  }
  function portal(g,p,sx,sy,t){
    g.save();g.translate(sx,sy);
    for(const s of [-1,1])poly(g,[[s*48,0],[s*43,-100],[s*25,-133],[s*18,-118],[s*29,-82],[s*31,0]],'#627a9a','#e0bc74',3);
    poly(g,[[-46,-103],[-32,-140],[32,-140],[46,-103]],'#748eae','#f0d088',3);
    const gr=g.createRadialGradient(0,-56,1,0,-56,57);gr.addColorStop(0,'#9ef6ff');gr.addColorStop(.5,'#7a96d8');gr.addColorStop(1,'#1e2b44');
    ellipse(g,0,-57,31,53,gr);
    for(let i=-2;i<=2;i++)stroke(g,[[i*9,-101],[i*9+Math.sin(t+i)*2,-14]],'rgba(180,248,255,.65)',1.2);
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.lineWidth=4;g.strokeStyle='#182338';g.fillStyle='#e8fbff';
    const name=window.Locale?.translate(p.name)||p.name;g.strokeText(name,0,-154);g.fillText(name,0,-154);g.restore();
  }
  window.SkybridgeArt={ground,detail,portal};
})();
