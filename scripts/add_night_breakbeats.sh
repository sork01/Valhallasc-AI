#!/bin/sh
# Add distinct, restrained Axiom8 Chillhop breaks to the completed night remixes.
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({name:'valhallasc-night-breakbeats',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name,args) {
  const result = await client.callTool({name,arguments:args},undefined,{timeout:300000});
  if (result.isError) throw Error(`${name}: ${result.content.map(x=>x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
const scores = [
  // Positions are sixteenth-note steps across two bars; the meter is in quarter-note beats.
  // The second bar changes at least one of kick, snare or hat in every score.
  {zone:'meadow',id:'6c52c389c99ed898',meter:3,swing:.18,db:-26,
   kick:[0,9,12,20],snare:[6,18,23],hat:[2,5,8,11,14,17,20,22],rim:[10,21]},
  {zone:'crags',id:'90d3be446ee5a58f',meter:4,swing:.23,db:-27,
   kick:[0,7,10,16,22,29],snare:[8,24,31],hat:[2,4,6,10,12,14,18,20,23,26,28,30],rim:[15,27]},
  {zone:'rime',id:'4091d2184af5bf68',meter:3,swing:.06,db:-29,
   kick:[0,12,16],snare:[8,20],hat:[0,3,6,9,12,15,18,21],rim:[11,23]},
  {zone:'fen',id:'631d2ccf54a0ea32',meter:4,swing:.2,db:-27,
   kick:[0,6,15,16,23,28],snare:[8,24,30],hat:[1,3,5,7,10,12,14,17,19,21,23,26,28,30],rim:[12,31]},
  {zone:'city',id:'32550162e477d9e7',meter:3,swing:.14,db:-28,
   kick:[0,11,12,18],snare:[4,16,22],hat:[2,4,7,10,14,16,19,22],rim:[9,21]},
  {zone:'wyrd',id:'a2ac7b7ae8fa8ad8',meter:3,swing:.21,db:-27,
   kick:[0,7,12,17,23],snare:[8,20],hat:[1,4,6,9,11,13,16,19,22],rim:[10,21]},
  {zone:'sky',id:'f8d95f2b7456bee1',meter:4,swing:.1,db:-29,
   kick:[0,11,16,27],snare:[10,26],hat:[0,4,7,12,16,20,23,28],rim:[15,31]},
  {zone:'nacre',id:'f0c6df77cbbaed17',meter:3,swing:.16,db:-28,
   kick:[0,8,12,21],snare:[6,19],hat:[1,3,6,9,13,15,18,22],rim:[11,23]},
  {zone:'astral',id:'c452ba1d09acef9f',meter:5,swing:.12,db:-29,
   kick:[0,11,20,33],snare:[12,27,39],hat:[2,6,9,14,18,22,26,30,34,38],rim:[19,36]},
  {zone:'prism',id:'5f35d1f41f52775f',meter:4,swing:.24,db:-28,
   kick:[0,10,16,21,30],snare:[8,24,31],hat:[1,3,6,9,12,15,17,19,22,25,28,31],rim:[14,29]},
];
function row(length, hits, accent=[]) {
  const result=Array(length).fill('.');
  // Swing delays odd sixteenths; leave the last one empty so no note spills
  // past the eight-bar part boundary in dybase2.
  for(const step of hits.filter(x=>x<length-1)) result[step]=accent.includes(step)?'X':'x';
  return result.join('');
}
function pattern(score,section) {
  const length=score.meter*8;
  const main=section===1||section===2;
  const kick=section===0?score.kick.filter(x=>x<length/2||x===length/2):
    section===3?score.kick.filter(x=>x===0||x===length/2||x===length/2+score.meter*2):score.kick;
  const snare=section===0?score.snare.filter(x=>x<length/2):
    section===3?score.snare.filter(x=>x>=length/2):score.snare;
  const hat=section===0?score.hat.filter((_,i)=>i%2===0):
    section===3?score.hat.filter((_,i)=>i%2===1):score.hat;
  const rim=main?score.rim:[];
  const result={kick:row(length,kick,[0,length/2]),snare:row(length,snare),hat:row(length,hat),clap:row(length,rim)};
  if(section===2) {
    // A small answering fill appears every other bar of the second phrase.
    const fill=length-2;
    result.snare=result.snare.slice(0,fill)+'o'+result.snare.slice(fill+1);
  }
  return result;
}
for(const score of scores) {
  if(process.env.ZONES && !process.env.ZONES.split(',').includes(score.zone)) continue;
  const A={project_id:score.id};
  const opened=await call('open_project',A);
  const tracks=opened.tracks||[];
  console.log(score.zone,JSON.stringify({name:opened.name,tempo:opened.tempo,meter:opened.time_signature,tracks:tracks.map(t=>typeof t==='string'?t:{name:t.name,instrument:t.instrument})}));
  if(process.env.INSPECT_ONLY==='1') continue;
  for(const old of ['Drums','Hand Drum']) {
    if(tracks.some(t=>(typeof t==='string'?t:t.name)===old)) await call('remove_track',{track:old,...A});
  }
  if(process.env.CLEAN_ONLY==='1') continue;
  const track='Night breakbeat';
  const drumDb=score.db+8; // Stems sit about 5 dB below the melodic parts.
  if(process.env.MIX_ONLY==='1') {
    await call('set_mix',{track,volume_db:drumDb,pan:0,...A});
    const rendered=await call('render_audio',{path:`/tmp/valhallasc-${score.zone}-night-dybase2.wav`,per_track:false,tail_seconds:2,...A});
    console.log(score.zone,'rendered',JSON.stringify({wav:rendered.wav,seconds:rendered.seconds,integrated_lufs:rendered.integrated_lufs,peak_dbfs:rendered.peak_dbfs,clipped_samples:rendered.clipped_samples,problems:rendered.problems,warnings:rendered.warnings}));
    continue;
  }
  if(tracks.some(t=>(typeof t==='string'?t:t.name)===track)) {
    await call('clear_bars',{track,...A});
    await call('set_instrument',{track,instrument:'axiom8',preset:'Chillhop',...A});
  } else await call('add_track',{name:track,instrument:'axiom8',preset:'Chillhop',volume_db:drumDb,...A});
  await call('set_mix',{track,volume_db:drumDb,pan:0,...A});
  for(let section=0;section<4;section++) {
    await call('write_drums',{track,start_bar:1+section*8,bars:8,pattern:pattern(score,section),swing:score.swing,velocity:section===0?57:section===3?56:65,name:['First footsteps','Night walk','A second path','Homeward'][section],...A});
  }
  const analysis=await call('analyse_song',A);
  console.log(score.zone,'beat saved',JSON.stringify({length:analysis.length,problems:analysis.problems,warnings:analysis.warnings}));
  if(analysis.problems?.length) throw Error(`${score.zone} has song problems`);
  const rendered=await call('render_audio',{path:`/tmp/valhallasc-${score.zone}-night-dybase2.wav`,per_track:false,tail_seconds:2,...A});
  console.log(score.zone,'rendered',JSON.stringify({wav:rendered.wav,seconds:rendered.seconds,integrated_lufs:rendered.integrated_lufs,peak_dbfs:rendered.peak_dbfs,clipped_samples:rendered.clipped_samples,problems:rendered.problems,warnings:rendered.warnings}));
}
await client.close();
JS
