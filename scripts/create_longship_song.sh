#!/bin/sh
# Original 6/8 rowing shanty; deliberately no foreground lead.
set -eu
cd "${DYBASE2_ROOT:-/home/serveperry/webserver/www/dybase2}"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';import fs from 'node:fs';
const c=new Client({name:'valhallasc-longship-song',version:'1'});await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const call=async(name,args)=>{const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});if(r.isError)throw Error(`${name}: ${r.content.map(v=>v.text).join('\n')}`);return JSON.parse(r.content[0].text);};
try{
 const project=await call('create_project',{name:'Valhalla Drowned Longship - Below the Last Sail',bpm:78,time_signature:'6/8',key:'E dorian'});const A={project_id:project.project_id};fs.writeFileSync('/tmp/longship-music-project.json',JSON.stringify(project,null,2));
 for(const [name,instrument,preset,volume_db]of [['Rope work','dexed','MARIMBA',-12],['Keel bass','dexed','WOOD BASS',-14],['Crew hum','sork60','Mellow Pad',-20],['Distant bell','dexed','TUB BELLS',-25],['Oarlocks','axiom8','Chillhop',-8]])await call('add_track',{name,instrument,preset,volume_db,...A});
 const chords=['Em','D','A','Em','G','D','Bm','Em','Em','A','D','Em','Cs','Bm','A','Em','G','D','A','Em','G','A','Bm','Bm','Em','D','A','G','Bm','A','D','Em'];
 const tones={Em:['E3','G3','B3','D4'],D:['D3','F#3','A3','D4'],A:['A2','C#3','E3','A3'],G:['G2','B2','D3','G3'],Bm:['B2','D3','F#3','B3'],Cs:['C#3','E3','G3','C#4']};
 const parts={'Rope work':[],'Keel bass':[],'Crew hum':[],'Distant bell':[],'Oarlocks':[]};const n=(pitch,beat,beats,velocity)=>({pitch,beat,beats,velocity});
 chords.forEach((chord,i)=>{const b=i*3,t=tones[chord],end=i===31;
  const root=t[0].replace('3','2');parts['Keel bass'].push(n(root,b,end?2.65:1.2,63));if(!end)parts['Keel bass'].push(n(root,b+1.5,1.15,55));
  for(const pitch of t.slice(0,3))parts['Crew hum'].push(n(pitch,b,2.68,38));
  const contour=i>=16&&i<24?[2,1,0,1,2,3]:[0,2,1,0,1,2];
  for(let k=0;k<(end?3:6);k++)parts['Rope work'].push(n(t[contour[k]],b+k*.5,.33,k===0||k===3?57:43));
  if([6,14,22,30].includes(i))parts['Distant bell'].push(n(t[2],b,1.1,39));
  parts.Oarlocks.push(n(36,b,.18,56));if(!end)parts.Oarlocks.push(n(45,b+1,.13,31),n(36,b+1.5,.18,48),n(38,b+1.5,.13,34),n(48,b+2.5,.13,28));
 });
 for(const [track,notes]of Object.entries(parts))await call('write_notes',{...A,track,start_bar:1,bars:32,notes,name:track});
 await call('add_fx_return',{...A,name:'Under the hull',effect:'sorkverb'});
 for(const track of ['Crew hum','Distant bell'])await call('set_send',{...A,track,fx_return:'Under the hull',level_db:-30});
 for(const [parameter,value]of [['env.attack',.08],['env.release',.22]])await call('automate',{...A,track:'Crew hum',parameter,points:[{bar:1,value},{bar:33,value}]});
 for(const [at_bar,name]of [[1,'The broken stern'],[9,'Cargo beneath the water'],[17,'The capstan turns'],[25,'The final crossing']])await call('add_marker',{...A,at_bar,name});
 const analysis=await call('analyse_song',A);fs.writeFileSync('/tmp/longship-music-analysis.json',JSON.stringify(analysis,null,2));
 const render=await call('render_audio',{...A,path:'/tmp/valhallasc-longship-dybase2.wav',per_track:true,tail_seconds:3});fs.writeFileSync('/tmp/longship-music-render.json',JSON.stringify(render,null,2));console.log(JSON.stringify({project,render}));
}finally{await c.close();}
JS
