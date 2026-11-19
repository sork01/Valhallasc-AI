#!/bin/sh
# Seven short editable cues, through the same dybase2 MCP/exporter as boss cues.
# --render preserves edits to the saved project. No zone music is changed.
set -eu
export FISHING_REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd /home/serveperry/webserver/www/dybase2
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module - "$@" <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
const c=new Client({name:'valhalla-fishing-sounds',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
const call=async(name,args)=>{
  const r=await c.callTool({name,arguments:args},undefined,{timeout:300000});
  if(r.isError)throw Error(r.content.map(x=>x.text).join('\n'));
  return JSON.parse(r.content[0].text);
};
try {
  const cache='/tmp/valhalla-fishing-sound-project.json',meta=process.env.FISHING_REPO+'/client/assets/fishing-sounds.txt';
  let project=fs.existsSync(cache)?JSON.parse(fs.readFileSync(cache)):fs.existsSync(meta)?{project_id:JSON.parse(fs.readFileSync(meta)).project}:null;
  const fresh=!project;
  if(fresh)project=await call('create_project',{name:'Valhalla Fishing - cast, water, reel and catch cues',bpm:120,time_signature:'4/4',key:'C major'});
  else await call('open_project',{project_id:project.project_id});
  fs.writeFileSync(cache,JSON.stringify(project,null,2));
  const A={project_id:project.project_id};
  if(fresh){
    // One cue every two bars leaves silence between exports. Exact source below.
    const cues=[
      ['cast','sork60','Surf',[[60,0,.38,95]],{'env.attack':.25,'env.release':.3,'env.sustain':5,'vcf.freq':6,'vcf.lfo':0}],
      ['plop','sork60','Init Patch',[[55,0,.08,100],[43,.12,.10,75]],{'dco.saw':0,'dco.pulse':1,'vcf.freq':2.1,'vcf.reso':8,'vcf.env':5,'env.decay':1.1,'env.sustain':0,'env.release':.2}],
      ['bite','sork60','Surf',[[67,0,.08,110],[64,.16,.12,90],[60,.4,.1,65]],{'env.attack':0,'env.release':.1,'env.sustain':7,'vcf.freq':7,'vcf.lfo':0}],
      ['reel','dexed','MARIMBA',[[76,0,.04,95],[72,.12,.04,85],[76,.24,.04,80],[72,.36,.04,70],[76,.48,.04,60]],{}],
      ['catch','sork60','Init Patch',[[72,0,.13,90],[76,.22,.13,85],[79,.44,.22,90]],{'dco.saw':0,'dco.pulse':1,'vcf.freq':5,'vcf.env':2,'env.attack':0,'env.decay':1.8,'env.sustain':1,'env.release':.6}],
      ['legendary','sork60','Init Patch',[[72,0,.18,90],[76,.3,.18,90],[79,.6,.18,95],[84,.9,.22,100],[79,1.3,.18,85],[84,1.6,.65,100]],{'dco.saw':0,'dco.pulse':1,'vcf.freq':6,'vcf.env':2,'env.attack':0,'env.decay':2,'env.sustain':2,'env.release':.8}],
      ['lava','sork60','Init Patch',[[40,0,.08,100],[47,.28,.08,80],[36,.6,.12,95],[43,.9,.08,70]],{'dco.saw':0,'dco.pulse':1,'dco.noise':2,'vcf.freq':1.7,'vcf.reso':8,'vcf.env':6,'env.decay':1.5,'env.sustain':0,'env.release':.3}],
    ];
    for(const [index,[name,instrument,preset,notes,parameters]] of cues.entries()){
      await call('add_track',{...A,name,instrument,preset,volume_db:-14});
      for(const [parameter,value] of Object.entries(parameters))await call('automate',{...A,track:name,parameter,points:[{bar:1,value},{bar:15,value}]});
      await call('write_notes',{...A,track:name,start_bar:index*2+1,bars:2,notes:notes.map(([pitch,beat,beats,velocity])=>({pitch,beat,beats,velocity}))});
      await call('add_marker',{...A,at_bar:index*2+1,name});
    }
  }
  const rendered=await call('render_audio',{...A,from_bar:1,bars:14,path:'/tmp/valhalla-fishing-cues.wav',per_track:false,tail_seconds:.2});
  fs.writeFileSync('/tmp/valhalla-fishing-cues-render.json',JSON.stringify(rendered,null,2));
  console.log(JSON.stringify({project,rendered}));
} finally {await c.close();}
JS
