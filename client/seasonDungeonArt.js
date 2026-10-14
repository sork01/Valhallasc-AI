'use strict';
// Four Yearwheel halls, each with its own stone, light and weather.
(() => {
  const {iso, poly, line, prism} = City.kit;
  const TAU = Math.PI * 2;
  const themes = {
    blooming_labyrinth: {wall:'#526a57',edge:'#9ec8a0',glow:'#f4b5d6',floor:142,veil:'#182b23'},
    solar_crucible: {wall:'#775443',edge:'#e8b97b',glow:'#ffdc7d',floor:34,veil:'#392117'},
    amber_archive: {wall:'#66503d',edge:'#dbad70',glow:'#f3d993',floor:37,veil:'#2c2019'},
    silent_solstice: {wall:'#415467',edge:'#b8d2e4',glow:'#e5f5ff',floor:205,veil:'#15212e'}
  };
  const ellipse=(g,x,y,rx,ry,fill,stroke,width=2)=>{
    g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);
    if(fill){g.fillStyle=fill;g.fill();}
    if(stroke){g.strokeStyle=stroke;g.lineWidth=width;g.stroke();}
  };
  function wall(theme) {const c=themes[theme];return {box:[440,520,220,410],draw(g,o){
    prism(g,o.width,o.depth,100,c.edge,c.wall,c.veil);
    for(let h=17;h<100;h+=20){const a=iso(-o.width/2,o.depth/2,h),b=iso(o.width/2,o.depth/2,h),d=iso(o.width/2,-o.depth/2,h);line(g,[a,b,d],h===57?c.glow:c.veil,2);}
    const p=iso(0,o.depth/2,50);ellipse(g,p[0],p[1],12,19,c.veil,c.glow,3);
    if(theme==='solar_crucible')for(let i=-1;i<=1;i++)line(g,[[p[0]+i*9,p[1]-14],[p[0]+i*9,p[1]+13]],c.edge,2);
    if(theme==='amber_archive')for(let i=-2;i<=2;i++)line(g,[[p[0]+i*4,p[1]-13],[p[0]+i*4,p[1]+13]],c.edge,1);
    if(theme==='silent_solstice')for(let i=-1;i<=1;i++)line(g,[[p[0]+i*8,p[1]-15],[p[0]-i*8,p[1]+15]],c.glow,2);
  }};}
  function lamp(theme){const c=themes[theme];return {box:[160,250,80,210],draw(g,o){
    prism(g,.7,.7,70,c.edge,c.wall,c.veil);
    if(theme==='blooming_labyrinth'){
      for(let i=0;i<6;i++){const a=i*TAU/6;ellipse(g,Math.cos(a)*16,-93+Math.sin(a)*14,10,15,i%2?c.glow:c.edge);}
      ellipse(g,0,-93,9,13,'#fff3dc');
    }else if(theme==='solar_crucible'){
      poly(g,[[-20,-67],[-29,-102],[0,-125],[29,-102],[20,-67]],c.wall,c.edge,3);
      ellipse(g,0,-91,10,20,c.glow);
    }else if(theme==='amber_archive'){
      poly(g,[[-21,-72],[-22,-119],[22,-119],[21,-72]],c.wall,c.edge,3);
      for(let i=-1;i<=1;i++)line(g,[[i*9,-112],[i*9,-80]],c.glow,2);
    }else{
      poly(g,[[-21,-71],[0,-128],[21,-71]],c.glow,c.edge,3);
      for(let i=-1;i<=1;i++)line(g,[[0,-110],[i*18,-84]],c.veil,2);
    }
  },animate(g,o,t){g.save();g.shadowColor=c.glow;g.shadowBlur=13+5*Math.sin(t*3+o.x);ellipse(g,0,-93,7,12,c.glow);g.restore();}};}
  function altar(theme){const c=themes[theme];return {box:[340,340,170,270],draw(g){
    prism(g,2.2,1.7,25,c.edge,c.wall,c.veil);
    if(theme==='blooming_labyrinth'){
      for(let i=0;i<8;i++){const a=i*TAU/8;ellipse(g,Math.cos(a)*50,-86+Math.sin(a)*40,24,12,i%2?c.glow:c.edge);}
      ellipse(g,0,-86,27,27,'#fff1c7',c.glow,4);
    }else if(theme==='solar_crucible'){
      ellipse(g,0,-86,56,44,c.wall,c.edge,6);
      for(let i=0;i<8;i++){const a=i*TAU/8;line(g,[[Math.cos(a)*37,-86+Math.sin(a)*31],[Math.cos(a)*67,-86+Math.sin(a)*57]],c.glow,5);}
      ellipse(g,0,-86,23,23,c.glow,'#fff0bb',4);
    }else if(theme==='amber_archive'){
      poly(g,[[-45,-135],[0,-119],[45,-135],[45,-53],[0,-37],[-45,-53]],c.edge,c.glow,4);
      line(g,[[0,-119],[0,-37]],c.veil,4);
      for(let y=-103;y<-53;y+=14)for(let side of [-1,1])line(g,[[side*8,y],[side*35,y-7]],c.veil,2);
    }else{
      for(let i=0;i<8;i++){const a=i*TAU/8;line(g,[[0,-87],[Math.cos(a)*52,-87+Math.sin(a)*52]],c.glow,5);}
      ellipse(g,0,-87,24,24,c.wall,c.glow,5);
    }
  }};}
  function seal(theme){const c=themes[theme];return {box:[210,100,105,80],draw(g){
    ellipse(g,0,0,80,27,c.wall,c.edge,3);
    ellipse(g,0,0,45,16,c.veil,c.glow,2);
    ellipse(g,0,0,13,11,c.glow);
  }};}
  function ground(theme,x,y,tone,alt){const c=themes[theme];return `hsl(${c.floor+tone*9}, ${theme==='blooming_labyrinth'?30:43}%, ${20+tone*8+alt*.6+((x+y)&1)*2}%)`;}
  function detail(g,theme,px,py,x,y,TW,TH){const c=themes[theme];
    g.strokeStyle=theme==='blooming_labyrinth'?'rgba(215,244,211,.22)':theme==='silent_solstice'?'rgba(200,230,255,.23)':'rgba(255,202,119,.2)';g.lineWidth=1;
    g.beginPath();g.moveTo(px-TW/2,py+TH/2);g.lineTo(px,py);g.lineTo(px+TW/2,py+TH/2);g.stroke();
    if((x*11+y*7)%11===0){ellipse(g,px,py+TH/2,12,4,c.veil,c.edge,1);ellipse(g,px,py+TH/2,3,3,c.glow);}
  }
  function weather(g,theme,t,w,h){const c=themes[theme];g.save();
    for(let i=0;i<36;i++){
      const x=(i*173+Math.sin(t*.3+i)*18+w)%w,y=(i*89-t*(theme==='blooming_labyrinth'?2:theme==='silent_solstice'?3:5)+h*20)%h;
      g.globalAlpha=.17+.14*Math.sin(t+i)**2;ellipse(g,x,y,theme==='blooming_labyrinth'?4:2,theme==='blooming_labyrinth'?2:3,c.glow);
    }
    g.restore();
  }
  function portal(g,p,sx,sy,t,theme){const c=themes[theme];g.save();g.translate(sx,sy);
    poly(g,[[-55,0],[-52,-83],[-33,-143],[0,-158],[33,-143],[52,-83],[55,0]],c.wall,c.edge,6);
    const glow=g.createRadialGradient(0,-73,3,0,-73,66);
    glow.addColorStop(0,'#fff7db');glow.addColorStop(.48,c.glow);glow.addColorStop(1,c.veil);
    ellipse(g,0,-73,40+Math.sin(t*2)*2,63,glow,c.edge,3);
    if(theme==='blooming_labyrinth')for(let i=0;i<6;i++){const a=i*TAU/6;ellipse(g,Math.cos(a)*34,-73+Math.sin(a)*52,9,14,c.glow);}
    else for(let i=0;i<(theme==='silent_solstice'?6:9);i++){const a=i*TAU/(theme==='silent_solstice'?6:9);line(g,[[Math.cos(a)*39,-73+Math.sin(a)*53],[Math.cos(a)*49,-73+Math.sin(a)*68]],c.edge,3);}
    g.font='15px "Jua",sans-serif';g.textAlign='center';g.lineWidth=4;g.strokeStyle=c.veil;g.fillStyle='#fff2cc';g.strokeText(p.name,0,-171);g.fillText(p.name,0,-171);g.restore();
  }
  for(const [theme,prefix] of [['blooming_labyrinth','bloom'],['solar_crucible','solar'],['amber_archive','amber'],['silent_solstice','solstice']]){
    City.art[prefix+'_wall']=wall(theme);
    City.art[prefix+(prefix==='bloom'?'_lamp':prefix==='solar'?'_brazier':'_lantern')]=lamp(theme);
    City.art[prefix+(prefix==='solar'?'_forge':prefix==='amber'?'_lectern':'_altar')]=altar(theme);
    City.art[prefix+'_seal']=seal(theme);
  }
  window.SeasonDungeonArt={isTheme:theme=>theme in themes,ground,detail,weather,portal};
})();
