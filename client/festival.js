'use strict';
// Only server snapshots drive the guided dance and buff. All registered seasons share this UI.
(()=>{
 const areas=[WORLD_MAP,...WORLD_MAP.zones];let dance=null,buff=null,events=[];
 const panel=document.createElement('aside');panel.id='festival-dance-progress';panel.hidden=true;panel.setAttribute('role','status');
 const text=document.createElement('span'),cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel dance';
 cancel.addEventListener('click',()=>{window.Online?.send({type:'move',x:Field.hero.x,y:Field.hero.y});});panel.append(text,cancel);document.getElementById('scene-game').append(panel);
 const tr=t=>window.Locale?.translate(t)||t;
 window.Festival={
  sync(next,nextBuff,seasons){if(next&&!dance)window.City?.close();dance=next;buff=nextBuff;events=seasons||[];panel.hidden=!dance;if(!dance)return;const laps=Math.min(2,Math.max(0,dance.laps));text.textContent=tr(dance.approaching?'Joining the festival circle…':`Festival dance: ${laps.toFixed(1)} / 2 laps`);cancel.textContent=tr('Cancel dance');},
  objects(zone){return (areas[zone]?.npcs||[]).filter(n=>n.id.startsWith('festival_dance_')&&events.some(e=>e.id===n.season)).map(n=>({kind:n.festivalArt,x:n.x,y:n.y,r:0}));},
  get dance(){return dance;},get buff(){return buff;}
 };
})();
