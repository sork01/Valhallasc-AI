#!/bin/sh
# Compose the Thunderheart Gate - Storm in the Stone editable score through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-thunderheart-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args},undefined,{timeout:240000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,260));return data;}
const project=await call('create_project',{name:'Valhalla Thunderheart Gate - Storm in the Stone',bpm:132,time_signature:'4/4',key:'D minor'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
 ['Storm brass','dexed','BRASS',-19],
 ['Storm voice','dexed','WHISTLE FLUTE',-18],
 ['Copper bells','dexed','GLASS VIBES',-25],
 ['Thunder air','dexed','GLASS PAD',-28],
 ['Gate bass','dexed','WOOD BASS',-17],
 ['Storm drums','dexed','LOG DRUM',-20],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const chords=Array(8).fill('Dm Bb F C').join(' ');
await call('write_chords',{track:'Gate bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Storm brass',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:62,rate:1,velocity:65,...A});
await call('write_chords',{track:'Thunder air',start_bar:1,bars:32,progression:chords,style:'block',register:53,velocity:38,...A});
await call('write_chords',{track:'Copper bells',start_bar:9,bars:16,progression:chords.split(' ').slice(8,24).join(' '),style:'arp_updown',register:78,rate:1,velocity:38,...A});
const tune=[
 [['D4',0,.75],['A4',1,.5],['F5',2,.5],['E5',3,.75]],
 [['Bb4',0,.5],['F5',.75,.5],['D5',1.5,1],['A4',3,.5]],
 [['C5',0,.75],['F5',1,.75],['A5',2.25,.5],['G5',3.25,.5]],
 [['G4',0,1],['C5',1.5,.5],['E5',2.25,.75],['D5',3.5,.5]],
 [['F4',0,.5],['A4',.75,.5],['D5',1.5,.75],['F5',2.75,1]],
 [['Bb4',0,.75],['D5',1,.5],['F5',2,.5],['E5',3,.75]],
 [['C5',0,.5],['E5',.75,.5],['G5',1.5,1],['F5',3,.5]],
 [['A4',0,.5],['D5',1,.75],['C5',2.25,.5],['D5',3.25,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?55:section===2?75:section===3?62:67});
 await call('write_notes',{track:'Storm voice',start_bar:start,bars:8,notes,name:['The mountain wakes','The ring conducts','Strike the bastion','The heart answers'][section],...A});
}
const knocks=[];for(let bar=0;bar<32;bar++){
 knocks.push({pitch:'D2',beat:bar*4,beats:.25,velocity:bar%8===0?75:57});
 knocks.push({pitch:'A2',beat:bar*4+2,beats:.2,velocity:bar>=8&&bar<28?52:39});
 if(bar>=16&&bar<28)knocks.push({pitch:'F2',beat:bar*4+3.5,beats:.15,velocity:34});
}
await call('write_notes',{track:'Storm drums',start_bar:1,bars:32,notes:knocks,name:'Clock heartbeat',...A});
for(const [name,at_bar] of [['The mountain wakes',1],['The ring conducts',9],['Strike the bastion',17],['The heart answers',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Stone chamber',effect:'sorkverb',...A});
for(const [track,level_db] of [['Storm voice',-22],['Copper bells',-29],['Thunder air',-27]])await call('set_send',{track,fx_return:'Stone chamber',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_thunderheart_song.sh '+project.project_id);
await client.close();
JS
