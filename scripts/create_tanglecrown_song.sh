#!/bin/sh
# Compose editable jungle music through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-tanglecrown-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,220));return data;}
const project=await call('create_project',{name:'Valhalla Tanglecrown - Beneath the Rain Crown',bpm:104,time_signature:'4/4',key:'A minor'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
 ['Canopy marimba','dexed','MARIMBA',-16],
 ['River flute','dexed','WHISTLE FLUTE',-20],
 ['Leaf glints','dexed','GLASS VIBES',-25],
 ['Rain mist','dexed','GLASS PAD',-27],
 ['Root bass','dexed','WOOD BASS',-18],
 ['Basin drums','dexed','LOG DRUM',-20],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const chords='Am F C G Am Dm F G Am F C G Dm Am G Am Am F C G Am Dm F G Dm F C G Am F G Am';
await call('write_chords',{track:'Root bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Canopy marimba',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:65,rate:1,velocity:68,...A});
await call('write_chords',{track:'Rain mist',start_bar:1,bars:32,progression:chords,style:'block',register:55,velocity:43,...A});
await call('write_chords',{track:'Leaf glints',start_bar:9,bars:24,progression:chords.split(' ').slice(8).join(' '),style:'arp_updown',register:83,rate:1,velocity:43,...A});
const tune=[
 [['A5',0,.75],['C6',1, .5],['D6',1.75,.5],['E6',2.5,.75]],
 [['C6',0,.5],['A5',.75,.5],['G5',1.5,.5],['A5',2.5,1]],
 [['E6',0,.75],['G6',1,.5],['E6',2,1],['D6',3,.5]],
 [['D6',0,.5],['C6',.75,.5],['A5',1.5,.75],['G5',2.75,.75]],
 [['A5',0,.5],['C6',.75,.5],['E6',1.5,.5],['G6',2.5,1]],
 [['F6',0,.75],['E6',1,.5],['D6',2,1],['A5',3,.5]],
 [['C6',0,.5],['D6',.75,.5],['E6',1.5,.5],['C6',2.5,1]],
 [['B5',0,.5],['G5',.75,.5],['A5',1.5,1],['A5',3,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?57:section===3?83:72});
 await call('write_notes',{track:'River flute',start_bar:start,bars:8,notes,name:['Green dawn','Braided waters','Eyes in the canopy','Rain Crown ascent'][section],...A});
}
const beats=[];for(let bar=0;bar<32;bar++){
 beats.push({pitch:'A2',beat:bar*4,beats:.25,velocity:bar%8===0?77:61});
 beats.push({pitch:'E3',beat:bar*4+.75,beats:.15,velocity:36});
 beats.push({pitch:'C3',beat:bar*4+2,beats:.25,velocity:58});
 beats.push({pitch:'G3',beat:bar*4+3.5,beats:.15,velocity:40});
}
await call('write_notes',{track:'Basin drums',start_bar:1,bars:32,notes:beats,name:'Rain on broad leaves',...A});
for(const [name,at_bar] of [['Banyan Landing',1],['Braided water',9],['Jade predators',17],['Temple stairs',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Canopy air',effect:'sorkverb',...A});
for(const [track,level_db] of [['River flute',-22],['Leaf glints',-27],['Rain mist',-25]])await call('set_send',{track,fx_return:'Canopy air',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_tanglecrown_song.sh '+project.project_id);
await client.close();
JS
