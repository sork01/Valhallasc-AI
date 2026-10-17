'use strict';
// Room-aware surface language for the eleven later private dungeons. The map's
// existing room rectangles remain the only source of playable floor and collision.
(() => {
  const styles = {
    eye_below:          {h:194,s:34,l:36, hall:27, edge:'#8ddedc', ink:'#183b4e', accent:'#b7f8eb', motif:'lens'},
    elder_hollow:       {h:37,s:32,l:39, hall:27, edge:'#b6d38d', ink:'#4b3e2e', accent:'#f0dfa4', motif:'rings'},
    thousandfold:       {h:314,s:28,l:48, hall:36, edge:'#f6d3a8', ink:'#5a3766', accent:'#fff0cf', motif:'fan'},
    rain_crown:         {h:171,s:27,l:41, hall:30, edge:'#b6e5ce', ink:'#245263', accent:'#e0f8da', motif:'channels'},
    seed_vault:         {h:75,s:32,l:43, hall:30, edge:'#d5cb89', ink:'#375039', accent:'#e6f3ab', motif:'seed'},
    sunken_astrolabe:   {h:203,s:30,l:39, hall:29, edge:'#e7c789', ink:'#285066', accent:'#d4f7ed', motif:'stars'},
    thunderheart_gate:  {h:214,s:29,l:39, hall:28, edge:'#b6dff0', ink:'#32475d', accent:'#fff0ba', motif:'circuit'},
    blooming_labyrinth: {h:142,s:31,l:44, hall:31, edge:'#eebbd6', ink:'#476453', accent:'#fff1c9', motif:'flower'},
    solar_crucible:     {h:27,s:43,l:43, hall:29, edge:'#f9c678', ink:'#62382c', accent:'#fff0a6', motif:'forge'},
    amber_archive:      {h:36,s:42,l:47, hall:32, edge:'#f2d495', ink:'#6c442f', accent:'#fff0c4', motif:'archive'},
    silent_solstice:    {h:202,s:31,l:58, hall:39, edge:'#d5f0f2', ink:'#4c647b', accent:'#d9ffe9', motif:'ice'},
  };
  const TAU = Math.PI * 2;
  function roomAt(x,y,zone) {
    return (zone?.rooms || []).findIndex(([x0,y0,x1,y1]) => x>=x0 && x<x1 && y>=y0 && y<y1);
  }
  function chamber(x,y,zone) {
    const i=roomAt(x,y,zone), r=zone?.rooms?.[i];
    return {i,r, main:!!r && r[2]-r[0]>=12 && r[3]-r[1]>=12,
      border:!!r && (x===r[0] || y===r[1] || x===r[2]-1 || y===r[3]-1)};
  }
  function ground(theme,x,y,tone,alt,zone) {
    const c=styles[theme], a=chamber(x,y,zone), court=a.main, room=a.i;
    let inlay=0, shift=0;
    if(court){
      const [x0,y0,x1,y1]=a.r, dx=(x+.5-(x0+x1)/2)/((x1-x0)/2), dy=(y+.5-(y0+y1)/2)/((y1-y0)/2);
      const radius=Math.hypot(dx,dy), angle=Math.atan2(dy,dx);
      switch(c.motif){
      case 'lens': inlay=Math.abs(radius-.58)<.13?12:radius<.24?18:0;shift=radius<.24?-12:0;break;
      case 'rings': inlay=Math.abs(radius-.42)<.1||Math.abs(radius-.73)<.08?10:0;shift=radius<.42?12:0;break;
      case 'fan': inlay=(Math.floor((dx+1)*4)+Math.floor((dy+1)*3))%2?9:1;break;
      case 'channels': inlay=Math.abs(dy)<.14||Math.abs(dx)<.12?12:Math.abs(dy-.55)<.08?7:0;break;
      case 'seed': inlay=radius<.3?14:Math.abs(Math.max(Math.abs(dx),Math.abs(dy)*1.2)-.66)<.1?9:0;break;
      case 'stars': inlay=Math.abs(radius-.67)<.1||Math.abs(dx)<.09||Math.abs(dy)<.09?13:0;break;
      case 'circuit': inlay=Math.abs(dx)<.13||Math.abs(dy)<.13||Math.abs(Math.abs(dx)-.65)<.08?12:0;break;
      case 'flower': inlay=radius<.2||Math.abs(radius-.65-.1*Math.cos(angle*5))<.15?13:0;shift=inlay?18:0;break;
      case 'forge': inlay=radius<.33?17:Math.abs(radius-.68)<.12?12:0;shift=inlay?-9:0;break;
      case 'archive': inlay=Math.abs(dx)<.1||Math.abs((dy+1)*4-Math.round((dy+1)*4))<.2?10:0;break;
      case 'ice': inlay=radius<.34?14:Math.abs(Math.sin(angle*6))*radius>.68?8:0;shift=inlay?-7:0;break;
      }
    }
    const organic=['rings','seed','flower','ice'].includes(c.motif);
    const hue=c.h+shift+(court ? (room%3-1)*5 : 0)+tone*(organic?2:5);
    const sat=c.s+(court?3:0)+tone*2;
    const light=(court?c.l:c.hall)+inlay+tone*(organic?2:5)+(organic?0:alt*.45+(((x+y)&1)?1.3:-1.3))+(a.border?5:0);
    return `hsl(${hue},${sat}%,${light}%)`;
  }
  const stroke=(g,color,width,points)=>{
    g.strokeStyle=color;g.lineWidth=width;g.beginPath();
    points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();
  };
  const oval=(g,x,y,rx,ry,color,width)=>{
    g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);
    if(width){g.strokeStyle=color;g.lineWidth=width;g.stroke();}
    else{g.fillStyle=color;g.fill();}
  };
  function detail(g,theme,px,py,x,y,tw,th,zone) {
    const c=styles[theme], a=chamber(x,y,zone), cy=py+th/2;
    // A continuous bright threshold shows the true edge of each playable room.
    if(!['rings','seed','flower','ice'].includes(c.motif))
      stroke(g,c.ink,1.5,[[px-tw/2,cy],[px,py],[px+tw/2,cy]]);
    if(a.border && !['rings','seed','flower','ice'].includes(c.motif))
      stroke(g,c.edge,2.1,[[px-tw*.23,cy],[px,py+th*.28],[px+tw*.23,cy]]);
    if(!a.main || (x*13+y*17)%(c.motif==='rings'||c.motif==='seed'||c.motif==='flower'?11:5)!==0) return;
    const k=(x*7+y*11)%3;
    switch(c.motif) {
    case 'lens':
      oval(g,px,cy,18,7,c.edge,2);oval(g,px,cy,8,5,c.accent,1.6);
      stroke(g,c.ink,2,[[px-21,cy],[px-30,cy-6]]);break;
    case 'rings':
      oval(g,px,cy,16,6,c.ink,2);oval(g,px,cy,10,3,c.edge,1.5);
      stroke(g,c.edge,1.7,[[px-17,cy+2],[px-27,cy-5],[px-35,cy-4]]);break;
    case 'fan':
      stroke(g,c.edge,2,[[px-22,cy+6],[px,cy-8],[px+22,cy+6]]);
      for(let j=-1;j<=1;j++)stroke(g,c.accent,1.5,[[px,cy-8],[px+j*14,cy+6]]);break;
    case 'channels':
      stroke(g,c.ink,5,[[px-27,cy-6],[px+27,cy+6]]);
      stroke(g,c.edge,2.5,[[px-27,cy-7],[px+27,cy+5]]);
      if(k===0)oval(g,px,cy,5,3,c.accent);break;
    case 'seed':
      oval(g,px,cy,17,8,c.edge,1.7);oval(g,px,cy,5,3,c.accent);
      stroke(g,c.ink,2,[[px-22,cy+4],[px-7,cy+1],[px,cy-6],[px+9,cy+1],[px+23,cy+4]]);break;
    case 'stars':
      oval(g,px,cy,16,8,c.edge,1.7);
      stroke(g,c.accent,1.7,[[px-19,cy],[px+19,cy]]);
      stroke(g,c.accent,1.7,[[px,cy-10],[px,cy+10]]);
      for(let j=0;j<3;j++)oval(g,px+9*j-10,cy+(j%2?6:-4),1.5,1.5,c.accent);break;
    case 'circuit':
      stroke(g,c.edge,2.5,[[px-25,cy-5],[px-8,cy-5],[px,cy+3],[px+19,cy+3]]);
      oval(g,px+20,cy+3,3,3,c.accent);break;
    case 'flower':
      for(let j=0;j<5;j++){const t=j*TAU/5;oval(g,px+Math.cos(t)*12,cy+Math.sin(t)*5,7,3,c.edge,1.5);}
      oval(g,px,cy,5,3,c.accent);break;
    case 'forge':
      oval(g,px,cy,15,7,c.edge,2.5);
      for(let j=0;j<6;j++){const t=j*TAU/6;oval(g,px+Math.cos(t)*19,cy+Math.sin(t)*10,3,2,c.accent);}
      break;
    case 'archive':
      for(let j=-1;j<=1;j++)stroke(g,j===0?c.accent:c.edge,2.4,[[px-24,cy+j*5],[px+24,cy+j*5]]);
      oval(g,px,cy,4,3,c.ink);break;
    case 'ice':
      stroke(g,c.edge,2,[[px-25,cy+4],[px-5,cy-5],[px+20,cy+6]]);
      stroke(g,c.accent,1.4,[[px-5,cy-5],[px-15,cy-9]]);
      oval(g,px+20,cy+6,4,2,c.accent);break;
    }
  }
  // Each wall is still drawn at the authoritative obstacle, but the silhouette
  // and the material change with the place. Long identical stone prisms were
  // making every dungeon look like the same buried cistern.
  function structure(g,o,theme) {
    const {iso,poly,prism}=City.kit, w=o.width, d=o.depth;
    const f=(u,h)=>iso(u,d/2,h), back=(u,h)=>iso(u,-d/2,h);
    const drawLine=(points,color,width)=>stroke(g,color,width,points);
    const face=(coords,color,edge=null,width=2)=>poly(g,coords.map(([u,h])=>f(u,h)),color,edge,width);
    if(theme==='elder_hollow'||theme==='seed_vault'||theme==='blooming_labyrinth'){
      const elder=theme==='elder_hollow',seed=theme==='seed_vault';
      const bark=elder?'#775235':seed?'#695943':'#335a3c';
      const shade=elder?'#3d3029':seed?'#394638':'#204434';
      const leaf=elder?'#67934d':seed?'#7a9e58':'#5baf69';
      const light=elder?'#e9ca87':seed?'#e5d787':'#f5add5';
      poly(g,[f(w/2,0),back(w/2,0),back(w/2,106),f(w/2,112)],shade,'#24382d',2);
      face([[-w/2,0],[w/2,0],[w/2,107],[w*.3,119],[0,103],[-w*.32,122],[-w/2,106]],bark,shade,3);
      if(!elder){
        for(let j=-2;j<=2;j++){
          const a=f(j*w*.23,12),b=f(j*w*.23,84+(j%2)*11);
          drawLine([a,b],seed?'#b1a46d':'#80bb69',seed?7:5);
          drawLine([a,b],seed?'#e4ca82':'#b6df88',2);
        }
      }else for(let j=-2;j<=2;j++){
        const a=f(j*w*.2,5),b=f((j+.2)*w*.2,96);
        drawLine([a,b],j%2?'#a6784e':'#4d392d',4);
        drawLine([f(j*w*.2,25),f((j-.3)*w*.2,53)],'#4c3c2e',3);
      }
      for(let j=-2;j<=2;j++){
        const p=f(j*w*.23,112+(j%2)*5);
        oval(g,p[0],p[1],elder?18:seed?15:25,elder?12:seed?10:17,leaf);
        if(seed && j%2===0){oval(g,p[0],p[1]+21,8,15,'#e7c989');oval(g,p[0],p[1]+21,3,7,'#f7edb1');}
        if(!elder&&!seed && j%2===0){oval(g,p[0],p[1],6,6,light);oval(g,p[0],p[1],10,9,'#f6d7e6',2);}
      }
      if(elder){
        const p=f(0,50);oval(g,p[0],p[1],16,26,'#463629');oval(g,p[0],p[1],10,20,'#ba945d',2);
      }
      return;
    }
    if(theme==='thousandfold'){
      prism(g,w,d,94,'#deafb3','#eddbb9','#824d70');
      for(let j=0;j<4;j++){
        const u0=-w/2+j*w/4+.03,u1=u0+w/4-.06;
        face([[u0,12],[u1,12],[u1,82],[u0,82]],j%2?'#f7e8c6':'#f3c6c5','#8d4d74',2);
        const p=f((u0+u1)/2,47);
        drawLine([[p[0]-14,p[1]+13],[p[0],p[1]-19],[p[0]+14,p[1]+13]],j%2?'#b36e95':'#6d8b73',3);
      }
      face([[-w*.57,91],[w*.57,91],[w*.5,111],[0,126],[-w*.5,111]],'#7c3c64','#e4b37e',4);
      drawLine([f(-w*.47,96),f(w*.47,96)],'#ffd5a0',4);
      return;
    }
    if(theme==='amber_archive'){
      prism(g,w,d,118,'#9d7746','#70462e','#372d29');
      for(let level=0;level<3;level++){
        const lo=12+level*31,hi=lo+26;
        face([[-w*.47,lo],[w*.47,lo],[w*.47,hi],[-w*.47,hi]],'#342b2c','#b8894f',2.5);
        for(let j=-3;j<=3;j++){
          const u=j*w*.13,p=f(u,lo+14);
          face([[u-w*.045,lo+3],[u+w*.045,lo+3],[u+w*.045,hi-3],[u-w*.045,hi-3]],j%3===0?'#edba63':j%2?'#bd7545':'#a66c50','#f2d797',1.2);
          if(j%3===0)oval(g,p[0],p[1],3,10,'#f7e2a8');
        }
      }
      face([[-w*.52,109],[w*.52,109],[w*.52,125],[-w*.52,125]],'#b78a53','#e8c88b',3);
      return;
    }
    if(theme==='silent_solstice'){
      poly(g,[f(w/2,0),back(w/2,0),back(w/2,100),f(w/2,115)],'#51748d','#a6d8e8',2);
      face([[-w/2,0],[w/2,0],[w/2,110],[w*.3,141],[w*.05,111],[-w*.25,129],[-w/2,104]],'#8bc1d2','#d7f7f3',3);
      for(let j=-2;j<=2;j++){
        const u=j*w*.2,a=f(u,2),b=f(u+w*.1,102+(j%2)*19);
        drawLine([a,b],j%2?'#c9f3ee':'#5086a7',3);
        drawLine([b,f(u+w*.16,61)],'#dffafa',2);
      }
      face([[-w*.53,111],[-w*.33,126],[-w*.1,113],[w*.18,134],[w*.42,122],[w*.53,110]],'#e7f8f2','#c6eafa',2);
      return;
    }
    if(theme==='eye_below'){
      prism(g,w,d,108,'#778d94','#264b5d','#102d42');
      face([[-w*.49,8],[w*.49,8],[w*.49,96],[-w*.49,96]],'#315969','#9ccac4',2.5);
      for(let j=-1;j<=1;j++){
        const p=f(j*w*.3,54);oval(g,p[0],p[1],19,27,'#0b344b',4);
        oval(g,p[0],p[1],12,20,j===0?'#72d4d4':'#397e95');
        oval(g,p[0]-3,p[1]-6,4,7,'#c8faf0');
      }
      for(let j=-2;j<=2;j++)drawLine([f(j*w*.22,4),f(j*w*.22,104)],'#afaa83',j%2?2:4);
      return;
    }
    if(theme==='rain_crown'){
      prism(g,w,d,91,'#93aa8d','#456b67','#225465');
      prism(g,w*.94,d*.78,19,'#aec39a','#496d61','#266e74',91);
      for(let j=-1;j<=1;j++){
        const p=f(j*w*.31,82);
        drawLine([[p[0],p[1]],[p[0]-4,p[1]+75]],'#66c6c6',9);
        drawLine([[p[0]-2,p[1]],[p[0]-6,p[1]+75]],'#b2edf0',3);
      }
      drawLine([f(-w*.45,58),f(w*.45,58)],'#c4d9a6',4);
      return;
    }
    if(theme==='sunken_astrolabe'){
      prism(g,w,d,112,'#b69965','#53596b','#26394f');
      for(let j=-1;j<=1;j++){
        const p=f(j*w*.31,56);oval(g,p[0],p[1],22,29,'#1c5269',4);
        oval(g,p[0],p[1],14,22,'#d3b674',3);
        drawLine([[p[0]-17,p[1]],[p[0]+17,p[1]]],'#cce9e4',2);
        drawLine([[p[0],p[1]-24],[p[0],p[1]+24]],'#cce9e4',2);
      }
      drawLine([f(-w*.48,104),f(w*.48,104)],'#f3d697',6);
      return;
    }
    if(theme==='thunderheart_gate'){
      prism(g,w,d,110,'#87929a','#344f6a','#223d58');
      for(let j=-2;j<=2;j++){
        const a=f(j*w*.22,8),b=f(j*w*.22,105);
        drawLine([a,b],j%2?'#c7a66e':'#8acbec',7);
        drawLine([f(j*w*.22,31),f((j+.35)*w*.22,55),f(j*w*.22,78)],'#e8f5ef',3);
      }
      drawLine([f(-w*.48,108),f(w*.48,108)],'#d8c18d',5);
      return;
    }
    if(theme==='solar_crucible'){
      prism(g,w,d,110,'#986346','#593b35','#302d35');
      for(let j=-1;j<=1;j++){
        const p=f(j*w*.31,53);oval(g,p[0],p[1],21,31,'#2a2630',4);
        oval(g,p[0],p[1]+8,14,19,'#ff8b38');
        oval(g,p[0],p[1]-1,7,11,'#ffdfa0');
      }
      drawLine([f(-w*.49,103),f(w*.49,103)],'#ffc46b',7);
      return;
    }
  }
  function backdrop(g,theme,w,h,t) {
    const {poly}=City.kit;
    const ramps={
      eye_below:['#061527','#174056'], elder_hollow:['#1a3027','#6a5238'],
      thousandfold:['#30223f','#855a77'], rain_crown:['#0b2932','#386d67'],
      seed_vault:['#1e3528','#6a5940'], sunken_astrolabe:['#0b2537','#34576a'],
      thunderheart_gate:['#0c1c36','#355579'], blooming_labyrinth:['#193527','#4c7757'],
      solar_crucible:['#301a1b','#7b3f2d'], amber_archive:['#2c201d','#684b36'],
      silent_solstice:['#112536','#53788a'],
    };
    const [top,bottom]=ramps[theme],gr=g.createLinearGradient(0,0,0,h);
    gr.addColorStop(0,top);gr.addColorStop(1,bottom);g.fillStyle=gr;g.fillRect(0,0,w,h);
    g.save();
    if(theme==='elder_hollow'||theme==='seed_vault'||theme==='blooming_labyrinth'){
      g.strokeStyle=theme==='elder_hollow'?'rgba(115,73,43,.44)':theme==='seed_vault'?'rgba(172,136,70,.33)':'rgba(30,93,50,.38)';
      g.lineWidth=25;
      for(let i=0;i<6;i++){
        const x=i*w/5-90;
        g.beginPath();g.moveTo(x,-30);g.bezierCurveTo(x+70,80,x-45,160,x+120,270);g.stroke();
      }
      g.fillStyle=theme==='blooming_labyrinth'?'rgba(95,170,95,.29)':'rgba(74,127,70,.23)';
      for(let i=0;i<19;i++){
        const x=(i*163)%w,y=(i*89)%260;
        oval(g,x,y,58,24,g.fillStyle);
      }
    }else if(theme==='thousandfold'){
      for(let i=0;i<7;i++){
        const x=i*w/6-75;
        poly(g,[[x,-20],[x+105,-20],[x+87,200],[x+10,185]],i%2?'rgba(242,190,203,.12)':'rgba(237,212,174,.11)',null);
      }
    }else if(theme==='silent_solstice'){
      for(let i=0;i<4;i++){
        const x=i*w/3-120+Math.sin(t*.3+i)*40;
        g.strokeStyle=i%2?'rgba(123,231,194,.17)':'rgba(155,195,241,.17)';g.lineWidth=80;
        g.beginPath();g.moveTo(x,-20);g.bezierCurveTo(x+80,100,x-65,190,x+120,310);g.stroke();
      }
    }else if(theme==='solar_crucible'){
      for(let i=0;i<7;i++){
        const x=i*w/6-20;
        g.fillStyle='rgba(255,129,57,.12)';g.beginPath();g.ellipse(x,h*.75,90,230,0,0,TAU);g.fill();
      }
    }else if(theme==='sunken_astrolabe'||theme==='eye_below'){
      for(let i=0;i<12;i++){
        const x=i*173%w,y=i*101%h;
        oval(g,x,y,theme==='eye_below'?42:25,theme==='eye_below'?42:25,'rgba(140,212,223,.07)',2);
      }
    }
    g.restore();
  }
  const minimap=(theme,x,y,zone)=>{
    const c=styles[theme], a=chamber(x,y,zone);
    return a.main?c.edge:a.border?c.accent:c.ink;
  };
  window.DungeonVisual={styles,roomAt,ground,detail,structure,backdrop,minimap};
})();
