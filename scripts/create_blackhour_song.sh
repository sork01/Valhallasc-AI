#!/bin/sh
# The Foundry's own editable dark industrial techno score, via dybase2 MCP.
set -eu
cd "${DYBASE2_ROOT:-/home/serveperry/webserver/www/dybase2}"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module - "$@" <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
const c=new Client({name:'valhallasc-blackhour-song',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const call=async(name,args)=>{console.error('[blackhour score] '+name);const r=await c.callTool({name,arguments:args},undefined,{timeout:name==='render_audio'?1200000:300000});if(r.isError)throw Error(name+': '+r.content.map(v=>v.text).join('\n'));return JSON.parse(r.content[0].text);};
try {
 if(process.argv.includes('--inspect')) {
  for(const [instrument,query] of [['sork60','lead'],['sork303','bass'],['axiom8','techno'],['dexed','metal']])console.log(instrument,JSON.stringify(await call('list_presets',{instrument,query})));
 } else {
  let project;
  if(fs.existsSync('/tmp/blackhour-music-project.json')){project=JSON.parse(fs.readFileSync('/tmp/blackhour-music-project.json'));await call('open_project',{project_id:project.project_id});}
  else {project=await call('create_project',{name:'Valhalla Black Hour Foundry - The Shift That Never Ends',bpm:132,time_signature:'4/4',key:'D minor'});fs.writeFileSync('/tmp/blackhour-music-project.json',JSON.stringify(project,null,2));}
  const A={project_id:project.project_id};
  if(!process.argv.includes('--render')&&!process.argv.includes('--mix')) {
   for(const [name,instrument,preset,volume_db] of [['Machine signal','sork60','Hardstyle Stab',-12],['Induction bass','sork303','Classic Acid',-14],['Midnight furnace','sork60','Mellow Pad',-24],['Steel impacts','dexed','TUB BELLS',-24],['Press drums','axiom8','Techno',-6],['Coil hats','axiom8','Chillhop',-22]])await call('add_track',{...A,name,instrument,preset,volume_db});
   const parts=Object.fromEntries(['Machine signal','Induction bass','Midnight furnace','Steel impacts','Press drums','Coil hats'].map(k=>[k,[]]));
   const n=(pitch,beat,beats,velocity)=>({pitch,beat,beats,velocity});
   const grid=['Dm','Dm','Bb','Dm','Dm','C','A','A'];
   const tones={Dm:['D3','F3','A3','D4'],Bb:['Bb2','D3','F3','Bb3'],C:['C3','E3','G3','C4'],A:['A2','C#3','E3','A3']};
   const audit=[];
   for(let bar=0;bar<64;bar++) {
    const chord=bar===63?'Dm':grid[bar%8],t=tones[chord],b=bar*4,section=Math.floor(bar/16),last=bar===63;
    audit.push({bar:bar+1,chord});
    // Every bass attack is anchored by the press kick; offbeats are deliberate hats.
    for(let beat=0;beat<(last?1:4);beat++) {
     parts['Induction bass'].push(n(t[0].replace('3','2'),b+beat,last?3.5:.34,beat%2?70:85));
     parts['Press drums'].push(n(36,b+beat,.18,beat===0?100:88));
     if(!last&&beat%2)parts['Press drums'].push(n(38,b+beat,.16,67));
     if(!last){parts['Coil hats'].push(n(42,b+beat+.5,.10,section===2?43:31));if(section===1||section===3)parts['Coil hats'].push(n(42,b+beat+.75,.08,23));}
    }
    for(const pitch of t.slice(0,3))parts['Midnight furnace'].push(n(pitch,b,3.65,34));
    const motif=section===2?[3,2,1,2]:section===3?[0,2,3,1]:[0,0,2,1];
    const beats=section===2?[0,1.5,2.5,3.5]:[0,.5,2,2.5];
    for(let k=0;k<(last?1:4);k++)parts['Machine signal'].push(n(t[motif[k]].replace(/(\d)/,v=>String(+v+1)),b+beats[k],last?1.5:.28,k===0?70:58));
    if(bar%4===3&&!last)parts['Steel impacts'].push(n(t[2],b+3,.35,46));
    if(section>0&&bar%8===6)parts['Press drums'].push(n(45,b+3.5,.15,53),n(48,b+3.75,.12,45));
   }
   for(const [track,notes]of Object.entries(parts))await call('write_notes',{...A,track,start_bar:1,bars:64,notes,name:track});
   for(const [track,values] of [['Machine signal',[['env.attack',.005],['env.release',.08]]],['Midnight furnace',[['env.attack',.07],['env.release',.15]]]])for(const [parameter,value]of values)await call('automate',{...A,track,parameter,points:[{bar:1,value},{bar:65,value}]});
   await call('add_fx_return',{...A,name:'Iron hall',effect:'sorkverb'});
   for(const track of ['Steel impacts','Midnight furnace'])await call('set_send',{...A,track,fx_return:'Iron hall',level_db:-28});
   for(const [at_bar,name]of [[1,'Clock rim: ignition'],[17,'Twelve-ton press'],[33,'Dead-current breakdown'],[49,'The thirteenth hour']])await call('add_marker',{...A,at_bar,name});
   fs.writeFileSync('/tmp/blackhour-chord-grid.json',JSON.stringify(audit,null,2));
  }
  if(process.argv.includes('--mix')) {
   for(const [track,volume_db]of [['Machine signal',-4],['Induction bass',-18],['Midnight furnace',-26],['Steel impacts',-18],['Press drums',-9],['Coil hats',-3]])await call('set_mix',{...A,track,volume_db});
   const hats=[],bass=[],grid=['D2','D2','Bb1','D2','D2','C2','A1','A1'];
   for(let bar=0;bar<64;bar++)for(let beat=0;beat<(bar===63?1:4);beat++) {
    bass.push({pitch:bar===63?'D2':grid[bar%8],beat:bar*4+beat,beats:bar===63?3.5:.34,velocity:beat%2?70:85});
    if(bar<63)hats.push({pitch:42,beat:bar*4+beat+.5,beats:.10,velocity:82+(beat%2)*12});
   }
   await call('write_notes',{...A,track:'Coil hats',start_bar:1,bars:64,notes:hats,name:'Offbeat factory vents'});
   await call('write_notes',{...A,track:'Induction bass',start_bar:1,bars:64,notes:bass,name:'Locked induction pulse'});
   await call('clear_bars',{...A,track:'Press drums',from_bar:33,bars:4});
   await call('clear_bars',{...A,track:'Coil hats',from_bar:33,bars:2});
   await call('add_effect',{...A,track:'Press drums',effect:'sorkcrush',slot:0});
  }
  fs.writeFileSync('/tmp/blackhour-music-analysis.json',JSON.stringify(await call('analyse_song',A),null,2));
  const render=await call('render_audio',{...A,path:'/tmp/valhallasc-blackhour-dybase2.wav',per_track:true,tail_seconds:3});
  fs.writeFileSync('/tmp/blackhour-music-render.json',JSON.stringify(render,null,2));console.log(JSON.stringify({project,render}));
 }
} finally {await c.close();}
JS
