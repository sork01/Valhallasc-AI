#!/bin/sh
# Compose editable glacier music through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-frostwake-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,220));return data;}
const project=await call('create_project',{name:'Valhalla Frostwake Shelf - Lanterns in the Blue Ice',bpm:88,time_signature:'4/4',key:'G minor'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
 ['Ice marimba','dexed','MARIMBA',-16],
 ['Aurora flute','dexed','WHISTLE FLUTE',-20],
 ['Glacial bells','dexed','GLASS VIBES',-25],
 ['Snow air','dexed','GLASS PAD',-27],
 ['Deep ice bass','dexed','WOOD BASS',-18],
 ['Snow pulse','dexed','LOG DRUM',-20],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const chords='Gm Eb Bb F Gm Eb Cm D Gm Bb Eb D Cm Gm Eb D Gm Eb Bb F Gm Bb Cm D Cm Eb Bb D Gm Eb D Gm';
await call('write_chords',{track:'Deep ice bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Ice marimba',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:65,rate:1,velocity:68,...A});
await call('write_chords',{track:'Snow air',start_bar:1,bars:32,progression:chords,style:'block',register:55,velocity:43,...A});
await call('write_chords',{track:'Glacial bells',start_bar:9,bars:24,progression:chords.split(' ').slice(8).join(' '),style:'arp_updown',register:83,rate:1,velocity:43,...A});
const tune=[
 [['G5',0,.75],['Bb5',1,.5],['D6',1.75,.5],['C6',2.5,.75]],
 [['Bb5',0,.5],['G5',.75,.5],['F5',1.5,.5],['G5',2.5,1]],
 [['D6',0,.75],['Eb6',1,.5],['D6',2,1],['Bb5',3,.5]],
 [['C6',0,.5],['Bb5',.75,.5],['G5',1.5,.75],['F#5',2.75,.75]],
 [['G5',0,.5],['Bb5',.75,.5],['D6',1.5,.5],['Eb6',2.5,1]],
 [['Eb6',0,.75],['D6',1,.5],['Bb5',2,1],['G5',3,.5]],
 [['Bb5',0,.5],['C6',.75,.5],['D6',1.5,.5],['Bb5',2.5,1]],
 [['A5',0,.5],['F#5',.75,.5],['G5',1.5,1],['G5',3,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?57:section===3?83:72});
 await call('write_notes',{track:'Aurora flute',start_bar:start,bars:8,notes,name:['Snowline','Lantern camp','Aurora shelf','Deep ice'][section],...A});
}
const beats=[];for(let bar=0;bar<32;bar++){
 beats.push({pitch:'A2',beat:bar*4,beats:.25,velocity:bar%8===0?77:61});
 beats.push({pitch:'E3',beat:bar*4+.75,beats:.15,velocity:36});
 beats.push({pitch:'C3',beat:bar*4+2,beats:.25,velocity:58});
 beats.push({pitch:'G3',beat:bar*4+3.5,beats:.15,velocity:40});
}
await call('write_notes',{track:'Snow pulse',start_bar:1,bars:32,notes:beats,name:'Heartbeat in snow',...A});
for(const [name,at_bar] of [['Frostwake Station',1],['Frozen Pool',9],['Aurora Court',17],['Leviathan Rib',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Glacial air',effect:'sorkverb',...A});
for(const [track,level_db] of [['Aurora flute',-22],['Glacial bells',-27],['Snow air',-25]])await call('set_send',{track,fx_return:'Glacial air',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_frostwake_song.sh '+project.project_id);
await client.close();
JS
