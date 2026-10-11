#!/bin/sh
# Compose Veyrroot's editable city score through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-worldheart-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args},undefined,{timeout:180000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,190));return data;}
const project=await call('create_project',{name:'Valhalla Veyrroot - Rooms in the Canopy',bpm:92,time_signature:'4/4',key:'F major'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,preset,volume_db] of [
 ['Branch kalimba','MARIMBA',-16],['Amber bells','GLASS VIBES',-23],
 ['Canopy flute','WHISTLE FLUTE',-19],['Heartwood air','GLASS PAD',-28],
 ['Living root bass','WOOD BASS',-18],['Leaf drums','LOG DRUM',-23],
])await call('add_track',{name,instrument:'dexed',preset,volume_db,...A});
const chords='F C Dm Bb F Gm C F Bb F Dm C Gm Bb C F F C Dm Bb F Gm C F Dm Bb F C Gm C F F';
await call('write_chords',{track:'Living root bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:67,...A});
await call('write_chords',{track:'Branch kalimba',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:68,rate:1,velocity:65,...A});
await call('write_chords',{track:'Heartwood air',start_bar:1,bars:32,progression:chords,style:'block',register:53,velocity:42,...A});
await call('write_chords',{track:'Amber bells',start_bar:9,bars:24,progression:chords.split(' ').slice(8).join(' '),style:'arp_updown',register:84,rate:1,velocity:39,...A});
const tune=[
 [['F5',0,.75],['A5',1,.5],['C6',1.75,.75],['D6',3,.5]],
 [['E6',0,.5],['C6',.75,.75],['G5',2,.5],['A5',3,.75]],
 [['D6',0,.75],['F6',1,.5],['E6',2,.75],['C6',3,.5]],
 [['Bb5',0,.75],['A5',1,.5],['F5',2,1],['G5',3.25,.5]],
 [['A5',0,.5],['C6',.75,.75],['F6',2,.75],['E6',3,.5]],
 [['D6',0,.75],['Bb5',1,.5],['G5',2,.75],['A5',3,.5]],
 [['G5',0,.5],['C6',.75,.75],['E6',2,.5],['G6',2.75,.75]],
 [['F6',0,.75],['E6',1,.5],['C6',2,.75],['F5',3,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?55:section===3?77:67});
 await call('write_notes',{track:'Canopy flute',start_bar:start,bars:8,notes,name:['First light','The outer ring','Inside the heart','The sealed seed'][section],...A});
}
const beats=[];for(let bar=0;bar<32;bar++){
 beats.push({pitch:'F2',beat:bar*4,beats:.22,velocity:bar%8===0?68:53});
 beats.push({pitch:'C3',beat:bar*4+1.5,beats:.15,velocity:31});
 beats.push({pitch:'A2',beat:bar*4+2,beats:.22,velocity:47});
 beats.push({pitch:'G3',beat:bar*4+3.5,beats:.14,velocity:34});
}
await call('write_notes',{track:'Leaf drums',start_bar:1,bars:32,notes:beats,name:'Soft living pulse',...A});
for(const [name,at_bar] of [['The Living Root',1],['Outer ring',9],['Heartwood halls',17],['Seed Vault',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Crown air',effect:'sorkverb',...A});
for(const [track,level_db] of [['Canopy flute',-22],['Amber bells',-28],['Heartwood air',-24]])await call('set_send',{track,fx_return:'Crown air',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_worldheart_song.sh '+project.project_id);
await client.close();
JS
