'use strict';
// Separate garden props: no baked backdrop, so each is independently placed and animated.
(() => {
  const {line,ellipse,poly}=City.kit;
  City.art.moonlily={
    box:[110,110,55,90],
    draw(g,o){
      ellipse(g,0,0,39,16,'#245d69','#102f48',3);
      for(let i=0;i<(o.petals||6);i++){
        const a=i*6.283/(o.petals||6),x=Math.cos(a)*19,y=Math.sin(a)*8-16;
        g.save();g.translate(x,y);g.rotate(a*.38);
        ellipse(g,0,-9,10,20,i%2?'#c7e5d1':'#e2d8ec','#6a799e',2);g.restore();
      }
      ellipse(g,0,-19,9,8,'#f8e8ad','#b3a27a',2);
    },
    animate(g,o,sx,sy,t){g.save();g.globalAlpha=.25+.12*Math.sin(t*1.6+o.x);g.fillStyle='#dcfff1';
      g.shadowColor='#9af2d7';g.shadowBlur=26;g.beginPath();g.ellipse(sx,sy-18,13,10,0,0,6.283);g.fill();g.restore();}
  };
  City.art.moonreed={
    box:[85,180,42,150],
    draw(g){for(let i=-2;i<=2;i++){
      line(g,[[i*8,0],[i*9+4,-55-Math.abs(i)*8],[i*10,-101-Math.abs(i)*9]],i%2?'#79b8b2':'#a8d5cf',3);
      ellipse(g,i*10,-102-Math.abs(i)*9,5,12,'#f8e8ad','#637895',1);
    }},
    animate(g,o,sx,sy,t){g.save();g.globalAlpha=.22+.1*Math.sin(t*2+o.y);g.fillStyle='#f8e8ad';g.shadowColor='#f8e8ad';g.shadowBlur=18;g.beginPath();g.arc(sx,sy-109,6,0,6.283);g.fill();g.restore();}
  };
  City.art.moonmirror={
    box:[185,120,92,95],
    draw(g){ellipse(g,0,2,76,30,'#214f65','#0b2f4a',4);ellipse(g,0,-2,60,20,'#8cb8c4','#4c779b',2);
      poly(g,[[-35,-4],[-10,-13],[20,-7],[47,0],[10,8]],'rgba(244,238,208,.5)');
      for(let i=-2;i<=2;i++)ellipse(g,i*17,10+(i%2)*3,5,2,'#a8e5d9');},
    animate(g,o,sx,sy,t){g.save();g.strokeStyle=`rgba(218,253,239,${.3+.15*Math.sin(t*2+o.x)})`;g.lineWidth=2;
      g.beginPath();g.ellipse(sx,sy,61+4*Math.sin(t*1.3),21,0,0,6.283);g.stroke();g.restore();}
  };
  const COURTS={
    tideglass_heron:[191,40,64],
    hourpetal_stag:[45,44,68],
    moonskein_weaver:[275,33,65],
    moonwell_echo:[165,43,63],
  };
  function surface(x,y,glass,zone) {
    if(glass) return {kind:'glass'};
    const row=zone?.moonwellFloor,shore=row&&[[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>row[y+dy]?.[x+dx]===' '||!row[y+dy]?.[x+dx]);
    let boss=null,radius=Infinity;
    for(const e of zone?.slimes||[]) if(COURTS[e.kind]) {
      const r=Math.hypot(x+.5-e.x,y+.5-e.y);
      if(r<radius){radius=r;boss=e.kind;}
    }
    if(radius<5.5) return {kind:'heart',boss,radius};
    if(radius<10.5) return {kind:'petal',boss,radius};
    return {kind:shore?'shore':'leaf',boss,radius};
  }
  function ground(x,y,tone,glass,alt,zone) {
    const s=surface(x,y,glass,zone),v=((x+y)&1)?1.4:-1.4;
    if(s.kind==='glass') return `hsl(${184+tone*7},34%,${69+tone*5+alt*.5+v}%)`;
    if(s.kind==='heart') {
      const [h,sat,l]=COURTS[s.boss];return `hsl(${h+tone*5},${sat}%,${l+tone*4+alt*.5+v}%)`;
    }
    if(s.kind==='petal') {
      const [h,sat,l]=COURTS[s.boss];return `hsl(${h+tone*5},${sat-5}%,${l-12+tone*4+alt*.5+v}%)`;
    }
    if(s.kind==='shore') return `hsl(${185+tone*8},34%,${37+tone*7+alt*.5+v}%)`;
    return `hsl(${169+tone*7},28%,${44+tone*6+alt*.5+v}%)`;
  }
  function detail(g,px,py,x,y,tw,th,glass,zone) {
    const s=surface(x,y,glass,zone),cy=py+th/2;
    if(s.kind==='glass') {
      g.strokeStyle='rgba(83,160,177,.7)';g.lineWidth=1.6;
      g.beginPath();g.moveTo(px-tw/2,cy);g.lineTo(px,py);g.lineTo(px+tw/2,cy);g.stroke();
      g.strokeStyle='rgba(255,245,203,.58)';g.lineWidth=2;
      g.beginPath();g.moveTo(px-15,cy+6);g.lineTo(px,cy-3);g.lineTo(px+15,cy+6);g.stroke();
      if((x*3+y)%7===0) ellipse(g,px,cy,3,2,'rgba(255,255,238,.8)');
      return;
    }
    g.strokeStyle=s.kind==='shore'?'rgba(188,251,232,.54)':'rgba(51,123,125,.33)';g.lineWidth=s.kind==='shore'?2:1;
    g.beginPath();g.moveTo(px-tw/2+2,cy);g.lineTo(px,py+2);g.lineTo(px+tw/2-2,cy);g.stroke();
    if(s.kind==='heart') {
      if((x+y)%3===0) {
        g.strokeStyle='rgba(255,251,222,.53)';g.lineWidth=2;
        g.beginPath();g.moveTo(px-10,cy);g.lineTo(px+10,cy);g.moveTo(px,cy-7);g.lineTo(px,cy+7);g.stroke();
      }
    } else if(s.kind==='petal') {
      if((x*7+y*3)%3===0) {
        g.fillStyle='rgba(247,234,248,.3)';g.beginPath();g.ellipse(px,cy,12,4,((x+y)&1)?.3:-.3,0,6.283);g.fill();
        g.strokeStyle='rgba(255,241,224,.46)';g.lineWidth=1.4;
        g.beginPath();g.moveTo(px-11,cy+3);g.lineTo(px+11,cy-3);g.stroke();
      }
    } else if(s.kind==='shore' && (x*5+y)%4===0) {
      g.strokeStyle='rgba(203,255,239,.57)';g.lineWidth=1.4;
      g.beginPath();g.ellipse(px,cy+4,14,4,0,0,6.283);g.stroke();
    } else if(s.kind==='leaf' && (x*7+y*3)%11===0) {
      g.strokeStyle='rgba(194,226,200,.48)';g.lineWidth=1.6;
      g.beginPath();g.moveTo(px-7,cy+5);g.lineTo(px,cy-5);g.lineTo(px+8,cy+4);g.stroke();
    }
  }
  function minimap(x,y,glass,zone) {
    const s=surface(x,y,glass,zone);
    if(s.kind==='glass') return '#d7f3e9';
    if(s.kind==='heart') return s.boss==='hourpetal_stag'?'#efe4b5':s.boss==='moonskein_weaver'?'#c9b8dc':'#afe7d8';
    if(s.kind==='petal') return '#a7c8c0';
    return s.kind==='shore'?'#5b9a9f':'#70aba2';
  }
  window.MoonwellArt={ground,detail,minimap};
})();
