'use strict';
// Server weather is cosmetic on this client. The map and combat state never depend on this setting.
(() => {
  const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
  const names = {clear:'Clear',rain:'Rain',snow:'Snow',fog:'Fog',thunderstorm:'Thunderstorm',wind:'Wind',sandstorm:'Sandstorm'};
  const icons = {clear:'☀',rain:'☂',snow:'❄',fog:'≋',thunderstorm:'⚡',wind:'➶',sandstorm:'◌'};
  let zone = null, packet = null, own = {x:0,y:0,inside:false};
  let shown = {type:'clear',intensity:'none',inside:true}, previous = shown, fade = 1, fadeTime = 1;
  let packetAt = performance.now(), lastLabel = '';
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const season = (x,y) => x < 200 ? (y >= 200 ? 'spring' : 'winter') : (y >= 200 ? 'summer' : 'autumn');
  const choice = () => {
    if (own.inside || !packet || packet.inside) return {type:'clear',intensity:'none',inside:true};
    return zone?.theme === 'yearwheel' && packet.seasons ? {...packet.seasons[season(own.x,own.y)],inside:false} : packet;
  };
  const strength = state => {
    if (!state || state.inside || state.type === 'clear') return 0;
    const age = (state.ageSeconds || 0) + (performance.now() - packetAt) / 1000;
    const left = state.endsInSeconds == null ? 20 : state.endsInSeconds - (performance.now() - packetAt) / 1000;
    return clamp(Math.min(age / 20, left / 20)) * ({light:.42,medium:.7,heavy:1}[state.intensity] || .7) * (window.Prefs?.weather ?? 1);
  };
  function sync(value, x, y, inside = false) {
    packet = value || {type:'clear',intensity:'none',inside:true}; packetAt = performance.now();
    own = {x,y,inside}; choose();
  }
  function setZone(value) { zone = value; choose(); }
  function choose() {
    const next = choice();
    if (next.type === shown.type && next.intensity === shown.intensity && !!next.inside === !!shown.inside && next.variant === shown.variant) {
      shown = next; return;
    }
    previous = shown; shown = next; fade = 0;
    fadeTime = zone?.theme === 'yearwheel' && !previous.inside && !shown.inside ? 3 : 1;
    updateLabel(true);
  }
  function updateLabel(force = false) {
    const local = value => window.Locale?.translate(value) || value;
    const label = shown.inside ? `⌂ ${local('Indoors')}` : `${icons[shown.type] || '◌'} ${local(names[shown.type] || shown.type)}`;
    if (!force && label === lastLabel) return;
    lastLabel = label;
    const node = document.getElementById('world-weather'); if (!node) return;
    node.textContent = label;
    node.title = shown.inside ? local('Weather is outdoors only') : `${local(names[shown.type] || shown.type)} · ${local(shown.intensity || 'none')} ${local('intensity')}${shown.endsInSeconds == null ? '' : ` · ${Math.ceil(shown.endsInSeconds / 60)} ${local('min remaining')}`}`;
  }
  function tick(dt, x = own.x, y = own.y, inside = own.inside) {
    own = {x,y,inside}; choose(); fade = Math.min(1,fade + dt / fadeTime); updateLabel();
  }
  // Fixed hashes keep particle positions stable across frames without allocations or randomness.
  const hash = n => { const v = Math.sin(n * 127.1 + 53.7) * 43758.5453; return v - Math.floor(v); };
  function paint(g, width, height, state, opacity, time) {
    const a = strength(state) * opacity;
    if (a < .002) return;
    const moving = !reduced(), type = state.type;
    g.save();
    if (type === 'rain' || type === 'thunderstorm') {
      g.fillStyle = `rgba(17,37,70,${.12*a})`; g.fillRect(0,0,width,height);
      g.fillStyle = `rgba(55,96,135,${.07*a})`; g.fillRect(0,height*.72,width,height*.28);
      const count = window.Prefs?.lowGraphics ? 16 : moving ? Math.round(45 + a*105) : 40;
      g.lineWidth = a > .7 ? 1.8 : 1.2; g.strokeStyle = `rgba(183,220,255,${.36*a})`;
      for (let i=0;i<count;i++) {
        const x = (hash(i+7)*width + (moving ? time*115 : 0)) % width;
        const y = (hash(i+871)*height + (moving ? time*(260+i%7*18) : 0)) % height;
        g.beginPath(); g.moveTo(x,y); g.lineTo(x-5-a*3,y+14+a*11); g.stroke();
        if (i%9===0 && y>height*.6) { g.beginPath(); g.ellipse(x,y+14,4+a*4,1.3,0,0,Math.PI*2); g.stroke(); }
      }
    } else if (type === 'snow') {
      g.fillStyle = `rgba(202,228,248,${.055*a})`; g.fillRect(0,0,width,height);
      g.fillStyle = `rgba(234,246,255,${.05*a})`; g.fillRect(0,height*.68,width,height*.32);
      const count = window.Prefs?.lowGraphics ? 12 : moving ? Math.round(35 + a*70) : 35;
      g.fillStyle = `rgba(242,250,255,${.72*a})`;
      for (let i=0;i<count;i++) {
        const x = (hash(i+11)*width + (moving ? time*(11+i%5*4)+Math.sin(time+i)*13 : 0)) % width;
        const y = (hash(i+514)*height + (moving ? time*(25+i%9*4) : 0)) % height;
        g.beginPath(); g.arc(x,y,1.4+(i%5)*.48,0,Math.PI*2); g.fill();
      }
    } else if (type === 'fog') {
      // A soft horizon and edge veil leave the hero and the HUD legible.
      const horizon = g.createLinearGradient(0,0,0,height);
      horizon.addColorStop(0,`rgba(166,181,191,${.18*a})`);
      horizon.addColorStop(.65,`rgba(184,193,199,${.1*a})`);
      horizon.addColorStop(1,`rgba(176,189,195,${.035*a})`);
      g.fillStyle=horizon; g.fillRect(0,0,width,height);
      const veil=g.createRadialGradient(width*.5,height*.58,height*.12,width*.5,height*.58,Math.max(width,height)*.72);
      veil.addColorStop(0,'rgba(206,215,217,0)');
      veil.addColorStop(1,`rgba(185,195,199,${.28*a})`);
      g.fillStyle=veil;g.fillRect(0,0,width,height);
    } else if (type === 'wind' || type === 'sandstorm') {
      const sand=type==='sandstorm', variant=state.variant || 'leaves';
      g.fillStyle=sand?`rgba(155,116,62,${.17*a})`:`rgba(119,131,143,${.035*a})`;
      g.fillRect(0,0,width,height);
      const colors={leaves:['#af8237','#d7a649','#865b32'],ash:['#aaa49a','#d3c8b5','#6e6a68'],dust:['#d0aa71','#c39a60','#e6c593'],cloud:['#dce4e9','#acbecb','#eee'],stardust:['#e8dcac','#a7c9d9','#fff4c8'],shards:['#9bdbdb','#c5edeb','#7fb9c5'],petals:['#e7a1b1','#f4c4ce','#d98caa'],snow:['#e9f5ff','#bfdbe9','#fff']};
      const palette=sand?colors.dust:(colors[variant]||colors.leaves);
      const count=moving?Math.round(24+a*(sand?80:40)):28;
      for(let i=0;i<count;i++){
        const x=(hash(i+19)*width+(moving?time*(sand?130:75)*(1+i%4*.2):0))%width;
        const y=(hash(i+633)*height+(moving?Math.sin(time*2+i)*9:0)+height)%height;
        const s=1.5+(i%4)*.65;
        g.globalAlpha=(.3+(i%3)*.16)*a;g.fillStyle=palette[i%3];
        g.beginPath();g.ellipse(x,y,s*(sand?1.3:1),sand?1:s*.55,-.25,0,Math.PI*2);g.fill();
      }
      g.globalAlpha=1;
    }
    if(type==='thunderstorm') {
      // Deterministic brief flashes, tied to world time rather than random frames.
      const pulse=time%13.7;
      const flash= pulse<.12 ? 1-pulse/.12 : pulse>.22&&pulse<.32 ? (.32-pulse)/.1*.45 : 0;
      if(flash>0){g.fillStyle=`rgba(221,235,255,${.32*a*flash})`;g.fillRect(0,0,width,height);}
    }
    g.restore();
  }
  function draw(g,width,height,time) {
    paint(g,width,height,previous,1-fade,time);
    paint(g,width,height,shown,fade,time);
  }
  window.Weather = {sync,setZone,tick,draw,get state(){return shown;},get blend(){return fade;},season};
})();
