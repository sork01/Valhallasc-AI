'use strict';
// The Ribbonwild's silk architecture, painted gardens and colossal sealed big top.
(() => {
  const {poly,iso,prism,wallPlane}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineJoin='round';g.lineCap='round';g.stroke();};
  const COLORS=['#ef6998','#f4c65e','#58c5d0','#aa7dda'];
  const shade=(i)=>COLORS[(i+4)%4];
  const shadow=(g,r)=>oval(g,0,6,r,r*.23,'rgba(40,31,57,.23)');

  City.art.fan_topiary={box:[300,310,150,275],draw(g,o){
    shadow(g,55);poly(g,[[-9,0],[-10,-109],[10,-109],[9,0]],'#9b6c5c','#694a51');
    for(let j=-3;j<=3;j++){
      const a=j*.34,x=Math.sin(a)*81,y=-134-Math.cos(a)*32;
      oval(g,x,y,38,49,shade(o.v+j));oval(g,x-8,y-13,17,13,'rgba(255,248,215,.28)');
    }
    oval(g,0,-158,25,29,'#f9db7e');oval(g,-5,-166,8,7,'#fff2cb');
  }};
  City.art.ribbon_pole={box:[170,330,85,290],draw(g,o){
    shadow(g,25);line(g,[[0,0],[0,-210]],'#f3d49b',9);
    oval(g,0,-219,13,13,'#f9df86');
    for(let j=0;j<3;j++){
      const y=-185+j*56,s=j%2?1:-1;
      poly(g,[[0,y],[s*65,y-17],[s*46,y+9],[s*74,y+22],[0,y+13]],shade(o.v+j),'#fbeac0',2);
    }
  },animate(g,o,sx,sy,t){
    g.save();g.globalAlpha=.42;g.strokeStyle=shade(o.v);g.lineWidth=2;
    g.beginPath();g.moveTo(sx,sy-144);g.quadraticCurveTo(sx+20+Math.sin(t*2+o.x)*12,sy-150,sx+48,sy-136);g.stroke();g.restore();
  }};
  City.art.pinwheel={box:[135,180,67,150],draw(g,o){
    shadow(g,20);line(g,[[0,0],[0,-105]],'#f4d696',6);
    for(let j=0;j<4;j++){const a=j*TAU/4;
      const x=Math.cos(a)*35,y=-111+Math.sin(a)*35;
      poly(g,[[0,-111],[x,y],[x-Math.sin(a)*20,y+Math.cos(a)*20]],shade(o.v+j),'#fff0ce',2);
    }
    oval(g,0,-111,8,8,'#fff3c8');
  }};
  City.art.festival_bloom={box:[120,100,60,75],draw(g,o){
    for(let j=0;j<7;j++){const x=(j*31+o.v*9)%76-38,y=(j*17+o.v*11)%27;
      line(g,[[x,y],[x+2,y-16-j%3*4]],'#4f9c6d',2);
      for(let k=0;k<5;k++){const a=k*TAU/5;oval(g,x+2+Math.cos(a)*5,y-18-j%3*4+Math.sin(a)*4,3,2,shade(o.v+j));}
      oval(g,x+2,y-18-j%3*4,2,2,'#ffeb9e');
    }
  }};
  City.art.confetti_lantern={box:[150,250,75,220],draw(g,o){
    shadow(g,24);line(g,[[0,0],[0,-160]],'#98716c',6);line(g,[[-38,-145],[38,-145]],'#98716c',5);
    for(const s of [-1,1]){
      oval(g,s*34,-134,16,22,shade(o.v+(s+1)/2));
      oval(g,s*34,-134,9,14,'rgba(255,248,212,.56)');
      line(g,[[s*34,-112],[s*34,-100]],'#f7e4a2',2);
    }
  }};
  // The pavilion and the stall stand on their w x d footprint in the same 2:1 projection as every house (City.kit.iso), so each sits on the tiles it blocks.
  const lerp=(p,q,t)=>[p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t];
  City.art.silk_pavilion={box:[560,430,280,300],draw(g,o){
    const w=o.width||5,d=o.depth||4,v=o.v||0,z0=10,zt=z0+100;
    oval(g,0,8,(w+d)*30,(w+d)*13,'rgba(40,31,57,.23)');
    prism(g,w+.35,d+.35,z0,'#ece0c2','#d6c39e','#bba883');
    prism(g,w,d,zt-z0,'#f7dfaf','#f7dfaf','#dcc18f',z0);
    const wall={y:(t,z)=>iso(t,d/2+.02,z),x:(t,z)=>iso(w/2+.02,t,z)};
    // Door and windows on the two walls that face the camera.
    poly(g,[wall.y(-.55,z0),wall.y(.55,z0),wall.y(.55,z0+72),wall.y(-.55,z0+72)],'#665078','#e5c9a4',3);
    line(g,[wall.y(-.62,z0+76),wall.y(.62,z0+76)],'#ecd297',5);
    for(const t of [-1.65,1.65])poly(g,[wall.y(t-.38,z0+36),wall.y(t+.38,z0+36),wall.y(t+.38,z0+76),wall.y(t-.38,z0+76)],'#9ad9e0','#e5c9a4',3);
    for(const t of [-1,1])poly(g,[wall.x(t-.38,z0+36),wall.x(t+.38,z0+36),wall.x(t+.38,z0+76),wall.x(t-.38,z0+76)],'#7fbfd0','#e5c9a4',3);
    // Bunting along the eaves of both walls.
    for(const [side,span] of [['y',w],['x',d]]){
      const n=Math.round(span*2);
      for(let i=0;i<n;i++){
        const t0=-span/2+i*span/n,t1=t0+span/n,c=shade(v+i);
        poly(g,[wall[side](t0,zt),wall[side](t1,zt),wall[side](t1,zt-20),wall[side]((t0+t1)/2,zt-32),wall[side](t0,zt-20)],c,'#6f496f',1.5);
      }
    }
    for(const [x,y] of [[-1,1],[1,1],[1,-1]])line(g,[iso(x*w/2,y*d/2,z0),iso(x*w/2,y*d/2,zt)],'#ecd297',7);
    // A four-sided tent roof striped in the court colours, with the +x slope in shade.
    const rw=w+1,rd=d+1,ze=zt+6,rise=130;
    const a=iso(rw/2,-rd/2,ze),c=iso(rw/2,rd/2,ze),e=iso(-rw/2,rd/2,ze),top=iso(0,0,ze+rise);
    const ny=Math.round(rw*1.4),nx=Math.round(rd*1.4);
    for(let i=0;i<ny;i++)poly(g,[top,lerp(e,c,i/ny),lerp(e,c,(i+1)/ny)],i%2?'#f7d36f':shade(v+(i>>1)),'#754d67',2);
    for(let i=0;i<nx;i++)poly(g,[top,lerp(c,a,i/nx),lerp(c,a,(i+1)/nx)],i%2?'#e3bd5c':shade(v+(i>>1)+1),'#754d67',2);
    poly(g,[top,c,a],'rgba(70,35,90,.16)',null);
    line(g,[e,c,a],'#754d67',4);
    line(g,[top,[top[0],top[1]-30]],'#f1d69d',5);
    oval(g,top[0],top[1]-34,10,10,'#fff0ac');
  }};
  City.art.painted_stall={box:[340,330,170,250],draw(g,o){
    const w=o.width||3,d=o.depth||2,v=o.v||0,hc=38,zb=122,zf=100;
    oval(g,0,6,(w+d)*22,(w+d)*10,'rgba(40,31,57,.23)');
    for(const x of [-1,1])line(g,[iso(x*w/2,-d/2,hc),iso(x*w/2,-d/2,zb)],'#f1d69d',5);
    prism(g,w,d,hc,'#f2dfb5','#e6cf9d','#c3a97a');
    line(g,[iso(-w/2+.05,d/2+.02,hc*.5),iso(w/2-.05,d/2+.02,hc*.5)],'#9a6a74',3);
    for(let j=-2;j<=2;j++){const [x,y]=iso(j*(w-.7)/4,d/2-.45,hc);oval(g,x,y-5,10,6,['#ffe189','#9ad9e0','#f2a0bc'][((j+2)+v)%3]);}
    for(const x of [-1,1])line(g,[iso(x*w/2,d/2,hc),iso(x*w/2,d/2,zf)],'#f1d69d',5);
    // The awning slopes down to the front; its stripes run front to back.
    const ex=w/2+.15,yf=d/2+.35,n=6;
    const P=(x,front)=>front?iso(x,yf,zf-8):iso(x,-d/2,zb);
    for(let i=0;i<n;i++){
      const x0=-ex+i*2*ex/n,x1=x0+2*ex/n,c=i%2?'#fff0c4':shade(v+(i>>1));
      poly(g,[P(x0,0),P(x1,0),P(x1,1),P(x0,1)],c,'#694c6e',2);
      const f0=P(x0,1),f1=P(x1,1);
      poly(g,[f0,f1,[(f0[0]+f1[0])/2,f0[1]+10]],c,'#694c6e',1.5);
    }
  }};
  City.art.parade_standard={box:[240,390,120,350],draw(g){
    shadow(g,41);line(g,[[0,0],[0,-273]],'#f1d69d',12);
    poly(g,[[-87,-219],[-8,-259],[72,-219],[47,-162],[-6,-183],[-53,-162]],'#ec77a5','#653f74',4);
    for(let j=-2;j<=2;j++)line(g,[[j*22,-219],[j*16,-176]],['#ffe589','#68cbd2','#b89aeb'][((j+2)%3)],6);
    oval(g,0,-281,18,18,'#fff2a8');
  }};
  City.art.mask_dais={box:[340,330,170,235],draw(g){
    oval(g,0,8,135,52,'rgba(40,31,57,.25)');
    prism(g,3.4,3.4,10,'#ecd7aa','#d1b783','#b79d6f');
    prism(g,2.6,2.6,24,'#a685b9','#9877ad','#76609a',10);
    prism(g,2,2,6,'#ddbc89','#c9a574','#a98a5e',34);
    g.save();g.translate(...iso(0,1.95));prism(g,1.6,.6,5,'#ecd7aa','#d1b783','#b79d6f');g.restore();
    line(g,[[0,-40],[0,-92]],'#8c6a8f',9);
    for(let j=-2;j<=2;j++)line(g,[[j*14,-166],[j*19,-196]],shade(j),5);
    oval(g,0,-128,34,41,'#f6d88e','#795f77');
    oval(g,-14,-131,8,11,'#5d4770');oval(g,14,-131,8,11,'#5d4770');
    line(g,[[-15,-107],[0,-99],[15,-107]],'#8c4c77',4);
  }};
  City.art.mosaic_disc={box:[530,240,265,195],draw(g){
    oval(g,0,0,190,91,'rgba(81,74,128,.20)');
    for(let j=0;j<12;j++){const a=j*TAU/12;
      oval(g,Math.cos(a)*150,Math.sin(a)*66,21,10,shade(j));}
    oval(g,0,0,31,15,'#fff0b9');
  }};
  City.art.grand_pavilion_gate={box:[720,690,360,520],draw(g,o){
    // A hall of silk on a 8 x 5 footprint; the mask door is on the +y wall like every house door. Wall art is drawn in the wall's own plane (City.kit.wallPlane).
    const w=8,d=5,z0=14,h=230,zt=z0+h,v=o.v||0;
    oval(g,0,10,300,100,'rgba(40,31,57,.25)');
    prism(g,w+.6,d+.6,z0,'#ece0c2','#d6c39e','#bba883');
    prism(g,w,d,h,'#f5dba8','#f5dba8','#d9bd8c',z0);
    const wallArt=(side,u,fn)=>{g.save();wallPlane(g,...(side==='y'?iso(0,d/2+.02,z0):iso(w/2+.02,0,z0)),side);fn(u);g.restore();};
    for(const [side,span] of [['y',w*44],['x',d*44]])wallArt(side,span/2,half=>{
      const n=Math.round(span/35);
      for(let i=0;i<n;i++){
        const x0=-half+i*span/n,x1=x0+span/n;
        poly(g,[[x0,0],[x1,0],[x1,-h],[x0,-h]],shade(v+i),null);
        poly(g,[[x0,0],[x1,0],[(x0+x1)/2,-h*.42]],'#f5dba8',null);
        poly(g,[[x0,-h],[x1,-h],[(x0+x1)/2,-h+30]],shade(v+i+2),'#6f496f',1.5);
      }
      if(side==='x')poly(g,[[-half,0],[half,0],[half,-h],[-half,-h]],'rgba(70,35,90,.2)',null);
      line(g,[[-half,-h],[half,-h]],'#6f496f',3);
    });
    wallArt('y',0,()=>{
      const arch=(s,c)=>{g.beginPath();g.moveTo(-96*s,0);g.lineTo(-96*s,-125*s);g.quadraticCurveTo(-96*s,-178*s,0,-180*s);g.quadraticCurveTo(96*s,-178*s,96*s,-125*s);g.lineTo(96*s,0);g.closePath();g.fillStyle=c;g.fill();};
      arch(1,o.open?'#251d48':'#4a315e');g.strokeStyle='#fbe7ac';g.lineWidth=7;g.lineJoin='round';g.stroke();
      if(o.open){arch(.8,'#edb0d1');arch(.68,'#50365d');}
      else{
        oval(g,0,-94,52,66,'#ffe9ab');oval(g,-20,-108,13,19,'#503957');oval(g,20,-108,13,19,'#503957');
        poly(g,[[-11,-72],[0,-64],[11,-72]],'#dc799b','#8b5b82',3);
        line(g,[[-40,-20],[40,-20]],'#87537c',10);
      }
    });
    for(const [x,y] of [[-1,1],[1,1],[1,-1]])line(g,[iso(x*w/2,y*d/2,z0),iso(x*w/2,y*d/2,zt)],'#fce1a1',16);
    g.save();g.translate(...iso(0,d/2+.45));prism(g,3.2,.9,6,'#e9d6b0','#d1bd96','#b6a27c');g.restore();
    g.save();g.translate(...iso(0,d/2+.2));prism(g,2.6,.45,12,'#efdfbd','#d9c6a0','#bfab85');g.restore();
    // The tent roof: eight-pointed court colours, a flagpole on the crest.
    const rw=w+1.2,rd=d+1.2,ze=zt+6,rise=185;
    const a=iso(rw/2,-rd/2,ze),c=iso(rw/2,rd/2,ze),e=iso(-rw/2,rd/2,ze),top=iso(0,0,ze+rise);
    const ny=Math.round(rw*1.3),nx=Math.round(rd*1.3);
    for(let i=0;i<ny;i++)poly(g,[top,lerp(e,c,i/ny),lerp(e,c,(i+1)/ny)],i%2?'#f7c96c':shade(v+(i>>1)),'#70466b',2.5);
    for(let i=0;i<nx;i++)poly(g,[top,lerp(c,a,i/nx),lerp(c,a,(i+1)/nx)],i%2?'#dfb259':shade(v+(i>>1)+1),'#70466b',2.5);
    poly(g,[top,c,a],'rgba(70,35,90,.16)',null);
    line(g,[e,c,a],'#70466b',5);
    for(const p of [e,c,a])oval(g,p[0],p[1],10,10,'#ffe5a3');
    line(g,[top,[top[0],top[1]-70]],'#f4d891',8);
    poly(g,[[top[0],top[1]-71],[top[0]+107,top[1]-43],[top[0],top[1]-18]],'#f77ca3','#ffe5ab',4);
    oval(g,top[0],top[1],14,14,'#fff1b5');
  },animate(g,o,sx,sy,t){
    g.save();g.globalAlpha=.22+.13*Math.sin(t*1.2);g.fillStyle='#fff2be';
    for(let i=0;i<26;i++){
      const x=sx+Math.sin(i*9.7+t*.8)*265,y=sy-165-((i*79+t*(21+i%4*3))%410);
      oval(g,x,y,2.5,4,'#fff0bd');
    }
    g.restore();
  }};
})();
