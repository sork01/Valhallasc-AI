'use strict';
// Layered jungle trunks, rain-bright waterways and the sealed crown temple.
(() => {
  const {poly}=City.kit,TAU=Math.PI*2;
  const oval=(g,x,y,rx,ry,c)=>{g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fillStyle=c;g.fill();};
  const line=(g,pts,c,w=3)=>{g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.strokeStyle=c;g.lineWidth=w;g.lineCap='round';g.lineJoin='round';g.stroke();};
  const shade=(v)=>['#236e55','#328b59','#47a768','#5db875'][((v%4)+4)%4];
  const shadow=(g,r)=>oval(g,0,5,r,r*.24,'rgba(10,48,37,.29)');
  const leaf=(g,x,y,rx,ry,c)=>{oval(g,x,y,rx,ry,c);oval(g,x-rx*.24,y-ry*.25,rx*.45,ry*.25,'rgba(199,236,138,.22)');};
  City.art.kapok_tree={box:[500,600,250,550],draw(g,o){
    shadow(g,112);
    for(const s of [-1,1])poly(g,[[0,-67],[s*18,-129],[s*49,-2],[s*27,0],[s*11,-42]],'#6e6a46','#394d38',3);
    poly(g,[[-29,0],[-22,-205],[-38,-274],[-16,-303],[3,-236],[15,-314],[36,-284],[24,-188],[30,0]],'#8a7750','#45543b',4);
    for(let j=-4;j<=4;j++){const x=j*37,y=-301-Math.cos(j*.35)*50;leaf(g,x,y,81,63,shade(o.v+j));}
    leaf(g,0,-385,102,69,'#3ca66d');
    for(let j=0;j<22;j++){const x=(j*67+o.v*31)%310-155,y=-301-(j*37)%107;oval(g,x,y,5,3,j%3?'#9ed56f':'#e5ce6d');}
    for(let j=-2;j<=2;j++)line(g,[[j*54,-353],[j*56+Math.sin(j)*9,-178]],'#56895d',3);
  }};
  City.art.strangler_fig={box:[440,540,220,490],draw(g,o){
    shadow(g,98);for(let j=-3;j<=3;j++)line(g,[[j*15,0],[j*12,-131],[j*21,-229]],j%2?'#886e4a':'#aa8659',9);
    for(let j=-3;j<=3;j++){const x=j*54,y=-266-Math.cos(j*.45)*43;leaf(g,x,y,81,69,shade(o.v+j+1));}
    leaf(g,0,-345,96,60,'#2f9159');
    for(let j=-3;j<=3;j++){const x=j*40;line(g,[[x,-264],[x+8,-116-j%2*25]],'#7cbf6b',3);}
  }};
  City.art.banana_palm={box:[330,410,165,370],draw(g,o){
    shadow(g,66);line(g,[[0,0],[0,-213]],'#99824e',14);
    for(let j=0;j<7;j++){const a=(j/7)*TAU,x=Math.cos(a)*116,y=-224+Math.sin(a)*47;
      poly(g,[[0,-221],[x*.46,y-38],[x,y],[x*.73,y+28]],j%2?'#51ad60':'#78c46a','#2f7151',2);
      line(g,[[0,-221],[x,y]],'#a5d987',2);
    }
    for(let j=0;j<4;j++)oval(g,15+j*7,-181+j*9,6,13,'#e3bc54');
  }};
  City.art.hanging_vines={box:[165,270,82,250],draw(g,o){
    for(let j=-2;j<=2;j++){const x=j*23;line(g,[[x,-198],[x+Math.sin(j+o.v)*9,-20]],'#4c9455',3);
      for(let i=0;i<5;i++)leaf(g,x+Math.sin(j+i)*8,-46-i*28,9,4,i%2?'#a1d36e':'#73bc5d');}
  }};
  City.art.giant_fern={box:[190,155,95,135],draw(g,o){
    shadow(g,34);for(let side of [-1,1])for(let j=0;j<5;j++){
      const x=side*(22+j*13),y=-25-j*12;line(g,[[0,0],[x,y]],'#34875c',3);
      for(let k=0;k<4;k++)leaf(g,x*(k+1)/5,y*(k+1)/5,10,5,j%2?'#61b774':'#80c66b');}
  }};
  City.art.orchid_cluster={box:[140,120,70,95],draw(g,o){
    for(let j=0;j<7;j++){const x=(j*29+o.v*11)%89-44,y=(j*17)%24;
      line(g,[[x,y],[x+2,y-20-j%3*5]],'#47855d',2);
      const c=['#ff83bb','#f9d57c','#b8a6ed','#fcad88'][j%4];
      for(let k=0;k<5;k++){const a=k*TAU/5;oval(g,x+2+Math.cos(a)*7,y-23-j%3*5+Math.sin(a)*5,4,3,c);}
      oval(g,x+2,y-23-j%3*5,3,3,'#fff2b2');}
  }};
  City.art.glow_mushroom={box:[120,100,60,80],draw(g,o){
    for(let j=0;j<4;j++){const x=j*22-36,y=j%2*9;line(g,[[x,y],[x,-20]],'#d6d3a2',4);oval(g,x,-22,12,7,j%2?'#a8e5ae':'#b7d9ef');oval(g,x-2,-24,4,2,'#f4f8c7');}
  }};
  City.art.jungle_water={box:[155,75,77,55],draw(g,o){
    oval(g,0,0,67,25,'rgba(10,99,116,.45)');oval(g,0,-3,58,19,'#2e9ba8');
    oval(g,-22,-8,23,6,'rgba(153,231,192,.29)');line(g,[[-48,2],[-14,-4],[21,-2],[51,0]],'rgba(194,243,207,.45)',2);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.28+.12*Math.sin(t*2+o.x);g.strokeStyle='#d6f8d8';g.lineWidth=2;g.beginPath();g.ellipse(sx+Math.sin(t+o.y)*14,sy-7,36,10,0,.2,2.8);g.stroke();g.restore();}};
  City.art.jade_pool={box:[335,155,167,135],draw(g){
    shadow(g,112);oval(g,0,-4,129,57,'#136b72');oval(g,0,-11,111,45,'#45b4ac');
    for(let j=0;j<11;j++){const a=j*TAU/11;oval(g,Math.cos(a)*100,Math.sin(a)*41-13,15,8,j%2?'#62b970':'#8acb6c');}
    oval(g,16,-24,29,8,'rgba(198,248,205,.32)');
  }};
  City.art.root_bridge={box:[290,250,145,175],draw(g){
    // A plank deck on roots, running along the +x axis, with a rail on each side.
    const K=City.kit,{iso,prism}=K,L=4,W=1.6,zd=8,zr=56;
    shadow(g,100);
    for(let x=-L/2+.2;x<=L/2-.1;x+=.8)K.line(g,[iso(x,-W/2,zd),iso(x,-W/2,zr)],'#6c7944',5);
    K.line(g,[iso(-L/2+.2,-W/2,zr),iso(L/2-.2,-W/2,zr)],'#a5bd76',5);
    prism(g,L,W,zd,'#9b764a','#6f603c','#574a30');
    for(let i=0;i<10;i++){const x=-L/2+(i+.5)*L/10;K.line(g,[iso(x,-W/2+.05,zd),iso(x,W/2-.05,zd)],i%2?'#b08a58':'#8f6c44',9);}
    for(let x=-L/2+.2;x<=L/2-.1;x+=.8)K.line(g,[iso(x,W/2,zd),iso(x,W/2,zr)],'#6c7944',5);
    K.line(g,[iso(-L/2+.2,W/2,zr),iso(L/2-.2,W/2,zr)],'#a5bd76',5);
  }};
  City.art.banyan_lodge={box:[500,410,250,300],draw(g,o){
    // A stilt house: posts, a plank deck, a stair up the +y side, walls and a leaf-thatch gable.
    const K=City.kit,{iso,poly,prism,wallPlane}=K,w=o.width||5,d=o.depth||4,zs=62,zh=96,zt=zs+zh;
    shadow(g,125);
    for(const [x,y] of [[-1,-1],[1,-1],[-1,1],[1,1]])K.line(g,[iso(x*(w/2-.3),y*(d/2-.3),0),iso(x*(w/2-.3),y*(d/2-.3),zs)],'#806d4d',15);
    poly(g,[iso(-.5,d/2+.1,zs),iso(.5,d/2+.1,zs),iso(.5,d/2+1.9,0),iso(-.5,d/2+1.9,0)],'#a98558','#5e4a30',3);
    for(let i=1;i<6;i++){const t=i/6;K.line(g,[iso(-.5,d/2+.1+1.8*t,zs*(1-t)),iso(.5,d/2+.1+1.8*t,zs*(1-t))],'#7a5f3a',2);}
    prism(g,w+.3,d+.3,8,'#c6a46a','#a98558','#8a6c45',zs-8);
    prism(g,w,zh*0+d,zh,'#b18b5b','#b18b5b','#8f6c44',zs);
    const onWall=(side,fn)=>{g.save();wallPlane(g,...(side==='y'?iso(0,d/2+.02,zs):iso(w/2+.02,0,zs)),side);fn();g.restore();};
    onWall('y',()=>{
      for(const z of [-32,-62])K.line(g,[[-w*22,z],[w*22,z]],'#9a7a4c',2);
      poly(g,[[-26,0],[-26,-74],[26,-74],[26,0]],'#3c694e','#d8be81',4);
      for(const x of [-w*13,w*13]){poly(g,[[x-14,-48],[x+14,-48],[x+14,-78],[x-14,-78]],'#e8d8a0','#4f6449',3);}
    });
    onWall('x',()=>{for(const x of [-d*9]){poly(g,[[x-14,-48],[x+14,-48],[x+14,-78],[x-14,-78]],'#e8d8a0','#4f6449',3);}});
    const rw=w+.9,rd=d+.9,rise=72;
    const a=iso(-rw/2,-rd/2,zt),b=iso(rw/2,-rd/2,zt),c=iso(rw/2,rd/2,zt),e=iso(-rw/2,rd/2,zt),r0=iso(-rw/2,0,zt+rise),r1=iso(rw/2,0,zt+rise);
    poly(g,[a,b,r1,r0],'#42865a','#35543f',4);
    poly(g,[b,c,r1],'#b18b5b','#35543f',4);
    poly(g,[r0,r1,c,e],o.v?'#5aa874':'#4e9d68','#35543f',4);
    for(let j=-2;j<=2;j++){const x=j*rw/5.5;K.line(g,[iso(x,rd/2*.14,zt+rise*.86),iso(x+.05,rd/2*.96,zt+rise*.04)],j%2?'#9dc466':'#84ad60',5);}
    for(let j=-3;j<=3;j++){const x=j*rw/7+(j%2?.1:-.1),t=rd/2;K.line(g,[iso(x,t,zt+rise*.0),iso(x,t+.03,zt-24-(j%3+3)*8)],j%2?'#9dc466':'#84ad60',3);}
    K.line(g,[r0,r1],'#35543f',5);
  }};
  City.art.boardwalk_stall={box:[320,310,160,235],draw(g,o){
    // Plank platform on stubby posts, a counter on the front and a leaf-thatch gable on four poles.
    const K=City.kit,{iso,poly,prism}=K,w=o.width||3,d=o.depth||2,zr=128;
    shadow(g,80);
    for(const [x,y] of [[-1,-1],[1,-1]])K.line(g,[iso(x*(w/2-.1),y*(d/2-.1),8),iso(x*(w/2-.1),y*(d/2-.1),zr)],'#99784d',10);
    prism(g,w+.2,d+.2,8,'#c6a46a','#a98558','#8a6c45');
    g.save();g.translate(...iso(0,d/2-.5));prism(g,w-.2,.6,34,'#d4b57b','#b08a54','#8a6c45',8);g.restore();
    for(let j=-2;j<=2;j++){const [x,y]=iso(j*(w-.7)/4,d/2-.5,42);g.beginPath();g.ellipse(x,y-5,12,7,0,0,6.2832);g.fillStyle=j%2?'#f0ce69':'#e7a17e';g.fill();}
    for(const [x,y] of [[-1,1],[1,1]])K.line(g,[iso(x*(w/2-.1),y*(d/2-.1),8),iso(x*(w/2-.1),y*(d/2-.1),zr)],'#99784d',10);
    const rw=w+.8,rd=d+.8,rise=44,col=o.v?'#7ebc68':'#64ae86';
    const a=iso(-rw/2,-rd/2,zr),b=iso(rw/2,-rd/2,zr),c=iso(rw/2,rd/2,zr),e=iso(-rw/2,rd/2,zr),r0=iso(-rw/2,0,zr+rise),r1=iso(rw/2,0,zr+rise);
    poly(g,[a,b,r1,r0],col,'#456b4a',3);
    poly(g,[b,c,r1],'#b9d68a','#456b4a',3);
    poly(g,[r0,r1,c,e],col,'#456b4a',3);
    for(let j=-2;j<=2;j++)K.line(g,[iso(j*rw/5.5,rd/2*.2,zr+rise*.8),iso(j*rw/5.5,rd/2*.95,zr+rise*.05)],'rgba(222,244,160,.55)',3);
    K.line(g,[r0,r1],'#456b4a',5);
  }};
  City.art.jaguar_totem={box:[290,320,145,290],draw(g){
    shadow(g,65);poly(g,[[-64,0],[-42,-170],[43,-170],[63,0]],'#7b8c6e','#36534b',4);
    oval(g,0,-183,54,63,'#b1a377');oval(g,-20,-193,10,12,'#28544b');oval(g,20,-193,10,12,'#28544b');
    poly(g,[[-10,-166],[0,-156],[10,-166]],'#42776b','#36534b',3);
    for(let j=-3;j<=3;j++)line(g,[[j*14,-235],[j*19,-279]],'#4ea772',7);
  }};
  City.art.rain_crown_temple={box:[960,700,480,470],draw(g,o){
    // A stepped pyramid of five terraces, the first tall enough for the doorway; the door and two waterfalls are on the +y face.
    const K=City.kit,{iso,poly,prism,wallPlane}=K,T=[[10,130],[8.4,60],[6.8,60],[5.2,60],[3.6,60]];
    shadow(g,400);
    let z=0;
    T.forEach(([s,h],i)=>{
      prism(g,s,s,h,i%2?'#a3b784':'#b3c48a',i%2?'#7b9c70':'#94aa78',i%2?'#5f805c':'#7a9566',z);
      for(let j=-3;j<=3;j++){const t=j*s/7.5;K.line(g,[iso(t,s/2,z+8),iso(t,s/2,z+h-6)],'rgba(40,70,60,.45)',2.5);K.line(g,[iso(s/2,t,z+8),iso(s/2,t,z+h-6)],'rgba(30,55,50,.5)',2.5);}
      z+=h;
    });
    const wall=(oy,z0,fn)=>{g.save();wallPlane(g,...iso(0,oy+.02,z0),'y');fn();g.restore();};
    wall(5,0,()=>{
      for(const s of [-1,1]){
        poly(g,[[s*150,-128],[s*196,-128],[s*210,0],[s*140,0]],'#49bcb3','#daefb5',3);
        for(let j=0;j<4;j++)K.line(g,[[s*(158+j*11),-118],[s*(158+j*13),-10]],'rgba(255,255,255,.5)',2);
      }
      const arch=(k,c)=>{g.beginPath();g.moveTo(-70*k,0);g.lineTo(-70*k,-92*k);g.quadraticCurveTo(-70*k,-124*k,0,-126*k);g.quadraticCurveTo(70*k,-124*k,70*k,-92*k);g.lineTo(70*k,0);g.closePath();g.fillStyle=c;g.fill();};
      arch(1,o.open?'#143c48':'#274c4b');g.strokeStyle='#d7ca7b';g.lineWidth=7;g.lineJoin='round';g.stroke();
      if(o.open){arch(.8,'#9edcc0');arch(.68,'#214d54');}
      else{
        g.beginPath();g.ellipse(0,-76,48,52,0,0,6.2832);g.fillStyle='#aab376';g.fill();
        for(const s of [-1,1]){g.beginPath();g.ellipse(s*17,-84,10,12,0,0,6.2832);g.fillStyle='#2a7167';g.fill();}
        K.line(g,[[-30,-36],[30,-36]],'#c7b776',9);
      }
    });
    wall(8.4/2,130,()=>{for(let j=-3;j<=3;j++){g.beginPath();g.ellipse(j*52,-34+Math.sin(j)*6,12,11,0,0,6.2832);g.fillStyle=j%2?'#f4dd88':'#a4e0ad';g.fill();}});
    const top=iso(0,0,z);
    leaf(g,top[0],top[1]-26,105,46,'#419367');leaf(g,top[0]-70,top[1]-6,58,28,'#4e9d6a');leaf(g,top[0]+72,top[1]-4,58,28,'#4e9d6a');
    for(let j=-4;j<=4;j++)K.line(g,[[top[0]+j*30,top[1]-6],[top[0]+j*34,top[1]+30+Math.abs(j)*4]],'#4e9760',4);
  },animate(g,o,sx,sy,t){g.save();g.globalAlpha=.2+.1*Math.sin(t*1.7);for(let j=0;j<17;j++){const x=sx+Math.sin(j*7+t*.3)*340,y=sy-150-((j*63+t*17)%430);oval(g,x,y,2,4,'#d9f9b4');}g.restore();}};
})();
