#!/bin/sh
# Two original dub-techno scores through dybase2 MCP. MODE=inspect|render|build.
set -eu
EMBERWAKE_ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
export EMBERWAKE_ROOT
export DYB2_CHROME="${DYB2_CHROME:-/home/serveperry/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome}"
cd /home/serveperry/webserver/www/dybase2
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
const out=process.env.EMBERWAKE_ROOT+'/test-results/emberwake';fs.mkdirSync(out,{recursive:true});
const c=new Client({name:'emberwake-dub-techno',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args={}){const r=await c.callTool({name,arguments:args},undefined,{timeout:900000});if(r.isError)throw Error(name+': '+JSON.stringify(r.content));return JSON.parse(r.content[0].text);}
try{
 if(process.env.MODE==='inspect'){
  for(const [instrument,query] of [['sork60','chord'],['sork60','pad'],['sorkbass2','sub'],['axiom8','techno'],['axiom8','chillhop']])
   console.log(instrument,query,JSON.stringify(await call('list_presets',{instrument,query})));
 }else for(const night of [false,true]){
  const key=night?'night':'day',file=out+'/music-'+key+'-project.json';
  let project=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):await call('create_project',{name:'Valhalla Emberwake - '+(night?'The Chains Dream':'Heat Beneath the Stones'),bpm:night?96:110,time_signature:'4/4',key:'F minor'});
  fs.writeFileSync(file,JSON.stringify(project,null,2));const A={project_id:project.project_id};
  await call('open_project',A);
  if(!['render','mix'].includes(process.env.MODE)){
   const before=await call('get_project',A);
   for(const t of before.tracks||[])await call('remove_track',{...A,track:t.name});
   const tracks=[['Chain chords','sork60','Hiphop Chorus Keys',night?-18:-12],['Heat haze','sork60','Mellow Pad',night?-24:-28],['Deep pulse','sorkbass2','Sub Weight',night?-13:-12],['Stone drums','axiom8','Techno',-17],['Ash hats','axiom8','Chillhop',8]];
   for(const [name,instrument,preset,volume_db]of tracks)await call('add_track',{...A,name,instrument,preset,volume_db});
   await call('automate',{...A,track:'Ash hats',parameter:'hatLevel',points:[{bar:1,value:6},{bar:33,value:6}]});
   await call('add_fx_return',{...A,name:'Caldera air',effect:'sorkverb'});
   for(const [track,level_db] of [['Chain chords',-16],['Heat haze',-26]])await call('set_send',{...A,track,fx_return:'Caldera air',level_db});
   for(const [track,attack,release] of [['Chain chords',.008,.16],['Heat haze',.14,.24]])for(const [parameter,value] of [['env.attack',attack],['env.release',release]])await call('automate',{...A,track,parameter,points:[{bar:1,value},{bar:33,value}]});
   const voicings={Fm:['F2','Ab3','C4','Eb4'],Db:['Db2','F3','Ab3','C4'],Ab:['Ab1','G3','Bb3','C4'],Eb:['Eb2','G3','Bb3','F4'],Bbm:['Bb1','Db4','F4','Ab4']};
   const harmony=night?['Fm','Fm','Bbm','Db','Fm','Ab','Eb','Fm']:['Fm','Db','Ab','Eb','Fm','Db','Bbm','Eb'];
   const parts=Object.fromEntries(tracks.map(t=>[t[0],[]])),audit=[];
   const n=(track,pitch,beat,beats,velocity)=>parts[track].push({pitch,beat,beats,velocity});
   for(let bar=0;bar<32;bar++){
    const chord=bar===31?'Fm':harmony[bar%8],t=voicings[chord],b=bar*4,section=Math.floor(bar/8);audit.push({bar:bar+1,chord});
    const bass=night?[0,2.5]:[0,1,2,3];
    for(const beat of bass){n('Deep pulse',t[0],b+beat,.42,night?67:78);n('Stone drums',36,b+beat,.15,night?71:87);}
    n('Stone drums',38,b+2,.14,night?43:66);
    for(const beat of (night?[.5,1.5,3.5]:[.5,1.5,2.5,3.5]))n('Ash hats',42,b+beat,.10,night?49:67);
    if(section===2&&bar%2===1)n('Ash hats',42,b+3.75,.08,40);
    // A descending three-chord response is harmony, not a foreground lead.
    // Deliberate diminishing echoes are discrete quantized notes, no tape drift.
    const rhythm=night?[[0,.8,49],[2.5,.32,42],[3.5,.18,28]]:[[.5,.5,62],[1.5,.28,47],[2.5,.22,34]];
    for(const [beat,length,velocity]of rhythm)for(const pitch of t.slice(1))n('Chain chords',pitch,b+beat,length,velocity+(section===1?3:0));
    if(section!==0||bar%2===0)for(const pitch of t.slice(1))n('Heat haze',pitch,b,3.5,night?26:32);
   }
   for(const [track,notes]of Object.entries(parts))await call('write_notes',{...A,track,start_bar:1,bars:32,notes,name:night?'Distant chain response':'Three-link chord signal'});
   fs.writeFileSync(out+'/music-'+key+'-grid.json',JSON.stringify({audit,parts},null,2));
   for(const [at_bar,name]of [[1,'Warm stones'],[9,'The first shackle'],[17,'Across the molten river'],[25,'Nine chains below']])await call('add_marker',{...A,at_bar,name});
  }
  if(process.env.MODE==='mix'){
   for(const [track,volume_db]of [['Chain chords',night?-18:-12],['Heat haze',night?-24:-28],['Deep pulse',night?-13:-12],['Stone drums',-17],['Ash hats',8]])await call('set_mix',{...A,track,volume_db});
   await call('automate',{...A,track:'Ash hats',parameter:'hatLevel',points:[{bar:1,value:6},{bar:33,value:6}]});
  }
  fs.writeFileSync(out+'/music-'+key+'-analysis.json',JSON.stringify(await call('analyse_song',A),null,2));
  const render=await call('render_audio',{...A,path:'/tmp/valhallasc-emberwake-'+key+'.wav',per_track:true,tail_seconds:3});
  fs.writeFileSync(out+'/music-'+key+'-render.json',JSON.stringify(render,null,2));console.log(key,project.project_id,'rendered');
 }
}finally{await c.close();}
JS
