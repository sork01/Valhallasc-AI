#!/bin/sh
# Compose editable jungle music through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-lapis-erg-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,220));return data;}
const project=await call('create_project',{name:'Valhalla Lapis Erg - Wells of Blue Glass',bpm:96,time_signature:'4/4',key:'D minor'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
 ['Caravan pluck','dexed','MARIMBA',-16],
 ['Desert flute','dexed','WHISTLE FLUTE',-20],
 ['Blue-glass bells','dexed','GLASS VIBES',-25],
 ['Oasis air','dexed','GLASS PAD',-27],
 ['Caravan bass','dexed','WOOD BASS',-18],
 ['Sand drums','dexed','LOG DRUM',-20],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const chords='Dm Bb Gm A Dm Bb Gm A Dm F Bb A Gm Dm Bb A Dm Bb Gm A Dm F Gm A Gm Bb F A Dm Bb A Dm';
await call('write_chords',{track:'Caravan bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Caravan pluck',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:65,rate:1,velocity:68,...A});
await call('write_chords',{track:'Oasis air',start_bar:1,bars:32,progression:chords,style:'block',register:55,velocity:43,...A});
await call('write_chords',{track:'Blue-glass bells',start_bar:9,bars:24,progression:chords.split(' ').slice(8).join(' '),style:'arp_updown',register:83,rate:1,velocity:43,...A});
const tune=[
 [['D5',0,.75],['F5',1,.5],['G5',1.75,.5],['A5',2.5,.75]],
 [['F5',0,.5],['D5',.75,.5],['C5',1.5,.5],['D5',2.5,1]],
 [['A5',0,.75],['Bb5',1,.5],['A5',2,1],['G5',3,.5]],
 [['G5',0,.5],['F5',.75,.5],['D5',1.5,.75],['C#5',2.75,.75]],
 [['D5',0,.5],['F5',.75,.5],['A5',1.5,.5],['Bb5',2.5,1]],
 [['Bb5',0,.75],['A5',1,.5],['G5',2,1],['D5',3,.5]],
 [['F5',0,.5],['G5',.75,.5],['A5',1.5,.5],['F5',2.5,1]],
 [['E5',0,.5],['C#5',.75,.5],['D5',1.5,1],['D5',3,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?57:section===3?83:72});
 await call('write_notes',{track:'Desert flute',start_bar:start,bars:8,notes,name:['Morning caravan','Blue wells','Salt mirage','Buried stars'][section],...A});
}
const beats=[];for(let bar=0;bar<32;bar++){
 beats.push({pitch:'A2',beat:bar*4,beats:.25,velocity:bar%8===0?77:61});
 beats.push({pitch:'E3',beat:bar*4+.75,beats:.15,velocity:36});
 beats.push({pitch:'C3',beat:bar*4+2,beats:.25,velocity:58});
 beats.push({pitch:'G3',beat:bar*4+3.5,beats:.15,velocity:40});
}
await call('write_notes',{track:'Sand drums',start_bar:1,bars:32,notes:beats,name:'Footsteps in sand',...A});
for(const [name,at_bar] of [['Azure Wells',1],['Mirrored oasis',9],['High dunes',17],['Sunken Astrolabe',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Desert air',effect:'sorkverb',...A});
for(const [track,level_db] of [['Desert flute',-22],['Blue-glass bells',-27],['Oasis air',-25]])await call('set_send',{track,fx_return:'Desert air',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_lapis_song.sh '+project.project_id);
await client.close();
JS
