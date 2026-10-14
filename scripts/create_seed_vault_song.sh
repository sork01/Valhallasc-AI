#!/bin/sh
# Compose the Seed Vault - The First Heartbeat editable score through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-seed_vault-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args},undefined,{timeout:240000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,260));return data;}
const project=await call('create_project',{name:'Valhalla Seed Vault - The First Heartbeat',bpm:84,time_signature:'4/4',key:'G minor'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
 ['Root pulse','dexed','MARIMBA',-17],
 ['Seed voice','dexed','WHISTLE FLUTE',-19],
 ['Amber bells','dexed','GLASS VIBES',-26],
 ['Heartwood air','dexed','GLASS PAD',-27],
 ['Pith bass','dexed','WOOD BASS',-17],
 ['Root drums','dexed','LOG DRUM',-22],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const chords='Gm Eb Cm D7 Gm Eb Cm D7 Gm Eb Cm D7 Gm Eb Cm D7 Gm Eb Cm D7 Gm Eb Cm D7 Gm Eb Cm D7 Gm Eb Cm D7';
await call('write_chords',{track:'Pith bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Root pulse',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:62,rate:1,velocity:65,...A});
await call('write_chords',{track:'Heartwood air',start_bar:1,bars:32,progression:chords,style:'block',register:53,velocity:38,...A});
await call('write_chords',{track:'Amber bells',start_bar:9,bars:16,progression:chords.split(' ').slice(8,24).join(' '),style:'arp_updown',register:78,rate:1,velocity:38,...A});
const tune=[
 [['G4',0,1.5],['D5',2,.5],['Bb4',3,.75]],
 [['Eb5',0,.5],['D5',1,.75],['Bb4',2.25,.75],['C5',3.25,.5]],
 [['C5',0,1],['G4',1.5,.5],['Eb4',2.25,1],['G4',3.5,.5]],
 [['F4',0,.75],['A4',1,.5],['D5',2,.75],['C5',3,.75]],
 [['Bb4',0,1.25],['G4',1.5,.5],['D5',2.5,.75],['Eb5',3.5,.5]],
 [['D5',0,.5],['Bb4',1,.75],['G4',2,.75],['F4',3,.75]],
 [['Eb4',0,1],['G4',1.5,.5],['C5',2.5,.75],['Bb4',3.5,.5]],
 [['A4',0,.75],['F4',1.25,.75],['D5',2.5,.5],['G4',3.25,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?55:section===2?75:section===3?62:67});
 await call('write_notes',{track:'Seed voice',start_bar:start,bars:8,notes,name:['The seed stirs','The root gallery','The amber vault','The worldseed wakes'][section],...A});
}
const knocks=[];for(let bar=0;bar<32;bar++){
 knocks.push({pitch:'A2',beat:bar*4,beats:.25,velocity:bar%8===0?75:57});
 knocks.push({pitch:'C3',beat:bar*4+2,beats:.2,velocity:bar>=8&&bar<28?52:39});
 if(bar>=16&&bar<28)knocks.push({pitch:'E3',beat:bar*4+3.5,beats:.15,velocity:34});
}
await call('write_notes',{track:'Root drums',start_bar:1,bars:32,notes:knocks,name:'Root heartbeat',...A});
for(const [name,at_bar] of [['The seed stirs',1],['The root gallery',9],['The amber vault',17],['The worldseed wakes',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Hollow chamber',effect:'sorkverb',...A});
for(const [track,level_db] of [['Seed voice',-22],['Amber bells',-29],['Heartwood air',-27]])await call('set_send',{track,fx_return:'Hollow chamber',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_seed_vault_song.sh '+project.project_id);
await client.close();
JS
