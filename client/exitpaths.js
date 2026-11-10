'use strict';
// Clear, static road markings and readable destinations at every outdoor crossing.
(() => {
  function stroke(g,pts,color,width){g.strokeStyle=color;g.lineWidth=width;g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();}
  function floor(g,z,w2s,hero){
    g.save();g.lineCap='round';g.lineJoin='round';
    for(const r of z.exitRoutes||[]){const p=z.portals.find(p=>p.id===r.portal);if(!p||p.vault||!p.walk||Math.hypot(p.x-hero.x,p.y-hero.y)>32)continue;      // a gate in the open (Asterion's, on the compass rose) has no side to mark
      const points=r.points.map(([x,y])=>w2s(x,y));
      stroke(g,points,'#302e35',42);stroke(g,points,z.sky?'#f1dfb9':'#d8c395',34);stroke(g,points,'#a28d69',2);
      const [x,y]=w2s(p.x,p.y),[a,b]=w2s(p.x-p.walk[0],p.y-p.walk[1]),len=Math.hypot(x-a,y-b)||1,ux=(x-a)/len,uy=(y-b)/len;
      for(let i=1;i<4;i++){const cx=x-ux*i*39,cy=y-uy*i*39;stroke(g,[[cx-ux*9-uy*9,cy-uy*9+ux*9],[cx,cy],[cx-ux*9+uy*9,cy-uy*9-ux*9]],'#fff0b7',3);}
    }g.restore();
  }
  function arch(g,a,w2s){
    const P=(u,v,h=0)=>w2s(a.x+(a.vertical?v:u),a.y+(a.vertical?u:v),h);
    const poly=(pts,color)=>{g.fillStyle=color;g.strokeStyle='#6e6756';g.lineWidth=1.5;g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fill();g.stroke();};
    g.save();g.lineJoin='round';
    // Each pier is a complete prism in world axes, so both wall orientations
    // show the correct front face rather than an exposed rear face.
    const inner=a.halfWidth||4.5,outer=inner+1.2;
    if(!a.towers)for(const side of [-1,1]){const [x,y]=P(side*(inner+.6),0);g.save();g.translate(x,y);City.kit.prism(g,a.vertical?1.8:1.2,a.vertical?1.2:1.8,108,'#eee8d4','#d4ccb2','#a9a38c');g.restore();}
    const point=(angle,outside,v)=>P(Math.cos(angle)*(outside?outer:inner),v,108+Math.sin(angle)*(outside?192:148));
    // Finish each continuous surface before the next. Painting one complete
    // wedge at a time let later roof faces slice triangles out of its neighbour.
    for(const surface of ['inner','roof','front'])for(let i=0;i<13;i++){
      const a0=Math.PI*i/13,a1=Math.PI*(i+1)/13;
      if(surface==='inner')poly([point(a0,false,-.9),point(a1,false,-.9),point(a1,false,.9),point(a0,false,.9)],'#aaa18b');
      if(surface==='roof')poly([point(a0,true,-.9),point(a1,true,-.9),point(a1,true,.9),point(a0,true,.9)],'#eee8d4');
      if(surface==='front')poly([point(a0,true,.9),point(a1,true,.9),point(a1,false,.9),point(a0,false,.9)],i%2?'#e6dfc9':'#dcd3b9');
    }
    g.restore();
  }
  function gate(g,p,z,dest,w2s,t,still){
    window.ZoneJourney?.approach(g,p,z,dest,w2s,t,still);
    const [x,y]=w2s(p.x-p.walk[1]*1.8,p.y+p.walk[0]*1.8);
    g.save();g.lineCap='round';stroke(g,[[x,y],[x,y-105]],'#322f38',10);stroke(g,[[x-2,y-3],[x-2,y-107]],'#ddc38a',4);
    g.fillStyle='#cc8d35';g.strokeStyle='#332b31';g.lineWidth=3;g.beginPath();g.moveTo(x,y-104);g.lineTo(x+50,y-104);g.lineTo(x+38,y-88);g.lineTo(x+50,y-72);g.lineTo(x,y-72);g.closePath();g.fill();g.stroke();
    const [ax,ay]=w2s(p.x,p.y),[bx,by]=w2s(p.x+p.walk[0],p.y+p.walk[1]),length=Math.hypot(bx-ax,by-ay),ux=(bx-ax)/length,uy=(by-ay)/length;
    const cx=x+25,cy=y-88,tip=[cx+ux*12,cy+uy*12];
    stroke(g,[[cx-ux*12,cy-uy*12],tip,[tip[0]-ux*9-uy*6,tip[1]-uy*9+ux*6],tip,[tip[0]-ux*9+uy*6,tip[1]-uy*9-ux*6]],'#fff0c9',3);g.restore();
  }
  function plaque(g,p,zones,w2s,zoom){
    const size=Math.max(19,13/Math.max(.35,zoom)),[x,y]=w2s(p.x,p.y,132),dest=zones[p.to];
    const name=window.Locale?.translate(dest?.name||p.name)||dest?.name||p.name;
    const level=dest?.levels?.join('–'),label=name+(level?` · ${level}`:'');
    g.font=`${size}px "Jua",sans-serif`;
    return {x,y,size,label,width:g.measureText(label).width+34};
  }
  function hit(g,p,zones,w2s,mx,my,zoom){
    if(!p.walk)return false;g.save();const b=plaque(g,p,zones,w2s,zoom);g.restore();
    return Math.abs(mx-b.x)<=b.width/2&&Math.abs(my-b.y)<=b.size;
  }
  function labels(g,z,zones,w2s,hero,zoom){
    const size=Math.max(19,13/Math.max(.35,zoom));g.save();g.font=`${size}px "Jua",sans-serif`;g.textAlign='center';g.textBaseline='middle';
    for(const p of z.portals){if(!p.walk||p.vault||Math.hypot(p.x-hero.x,p.y-hero.y)>28)continue;
      const {x,y,size,label,width}=plaque(g,p,zones,w2s,zoom);g.fillStyle='#18232ef0';g.strokeStyle='#f3d595';g.lineWidth=2;
      g.beginPath();g.roundRect(x-width/2,y-size,width,size*2,7);g.fill();g.stroke();g.fillStyle='#fff0c9';g.fillText(label,x,y);
    }g.restore();
  }
  window.ExitPaths={floor,arch,gate,labels,hit};
})();
