#!/bin/sh
# Compose the Sunken Astrolabe - Meridian of Dust editable score through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-sunken_astrolabe-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args},undefined,{timeout:240000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,260));return data;}
const project=await call('create_project',{name:'Valhalla Sunken Astrolabe - Meridian of Dust',bpm:96,time_signature:'4/4',key:'F# minor'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
 ['Brass pulse','dexed','MARIMBA',-17],
 ['Meridian voice','dexed','WHISTLE FLUTE',-19],
 ['Star bells','dexed','GLASS VIBES',-26],
 ['Buried air','dexed','GLASS PAD',-27],
 ['Hour bass','dexed','WOOD BASS',-17],
 ['Clock drums','dexed','LOG DRUM',-22],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const chords=Array(8).fill('F#m D A E').join(' ');
await call('write_chords',{track:'Hour bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Brass pulse',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:62,rate:1,velocity:65,...A});
await call('write_chords',{track:'Buried air',start_bar:1,bars:32,progression:chords,style:'block',register:53,velocity:38,...A});
await call('write_chords',{track:'Star bells',start_bar:9,bars:16,progression:chords.split(' ').slice(8,24).join(' '),style:'arp_updown',register:78,rate:1,velocity:38,...A});
const tune=[
 [['F#4',0,.5],['C#5',.75,.5],['A4',1.5,1],['E5',3,.75]],
 [['D5',0,1],['A4',1.25,.5],['F#4',2,.75],['C#5',3.25,.5]],
 [['C#5',0,.75],['E5',1,.5],['A5',2,.5],['G#5',3,.75]],
 [['B4',0,.5],['G#4',1,.75],['E4',2.25,.5],['F#4',3.25,.75]],
 [['A4',0,1],['C#5',1.5,.5],['F#5',2.25,.75],['E5',3.5,.5]],
 [['D5',0,.5],['F#5',.75,.5],['E5',1.5,.75],['C#5',2.75,1]],
 [['B4',0,.75],['C#5',1,.5],['E5',2,.75],['A4',3.25,.5]],
 [['G#4',0,.5],['B4',.75,.5],['C#5',1.5,.5],['F#4',2.5,1.25]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?55:section===2?75:section===3?62:67});
 await call('write_notes',{track:'Meridian voice',start_bar:start,bars:8,notes,name:['The iris turns','Below the dunes','Chart the lost sky','The axis awakens'][section],...A});
}
const knocks=[];for(let bar=0;bar<32;bar++){
 knocks.push({pitch:'F#2',beat:bar*4,beats:.25,velocity:bar%8===0?75:57});
 knocks.push({pitch:'C#3',beat:bar*4+2,beats:.2,velocity:bar>=8&&bar<28?52:39});
 if(bar>=16&&bar<28)knocks.push({pitch:'A2',beat:bar*4+3.5,beats:.15,velocity:34});
}
await call('write_notes',{track:'Clock drums',start_bar:1,bars:32,notes:knocks,name:'Clock heartbeat',...A});
for(const [name,at_bar] of [['The iris turns',1],['Below the dunes',9],['Chart the lost sky',17],['The axis awakens',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Bronze chamber',effect:'sorkverb',...A});
for(const [track,level_db] of [['Meridian voice',-22],['Star bells',-29],['Buried air',-27]])await call('set_send',{track,fx_return:'Bronze chamber',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_sunken_astrolabe_song.sh '+project.project_id);
await client.close();
JS
