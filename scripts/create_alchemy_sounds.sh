#!/bin/sh
# Create the editable short sound effects via dybase2 MCP, or render the saved project.
set -eu
export ALCHEMY_REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export ALCHEMY_EXPORT="${1:-/tmp/valhalla-alchemy-cues}"
mkdir -p "$ALCHEMY_EXPORT"
ALCHEMY_EXPORT="$(CDPATH= cd -- "$ALCHEMY_EXPORT" && pwd)"
cd /home/serveperry/webserver/www/dybase2
/home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module - <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import fs from 'node:fs';
import path from 'node:path';

const client = new Client({name:'valhalla-alchemy-sounds', version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath, args:['--import','tsx','mcp/server.mjs'],
  cwd:process.cwd(), stderr:'inherit', env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name, args) {
  const result = await client.callTool({name,arguments:args}, undefined, {timeout:300000});
  if (result.isError) throw Error(result.content.map(x => x.text).join('\n'));
  return JSON.parse(result.content[0].text);
}
try {
  const manifest = path.join(process.env.ALCHEMY_REPO,'client/assets/alchemy-sounds.txt');
  const marker = path.join(process.env.ALCHEMY_EXPORT,'project');
  let id = fs.existsSync(manifest) ? JSON.parse(fs.readFileSync(manifest)).project : null;
  if (!id && fs.existsSync(marker)) id = fs.readFileSync(marker,'utf8').trim();
  const fresh = !id;
  if (fresh) {
    const project = await call('create_project', {name:'Valhalla Alchemy - flowers, brewing and drinking',bpm:120,time_signature:'4/4',key:'C major'});
    id = project.project_id;
  } else {
    await call('open_project',{project_id:id});
  }
  const A = {project_id:id};
  if (fresh) {
    const cues = [
      ['pick','dexed','MARIMBA',[[76,0,.12,72],[83,.07,.14,82]],{}],
      ['brew','sork60','Init Patch',[[48,0,.12,83],[57,.18,.14,90],[63,.36,.16,73]],
        {'dco.saw':0,'dco.pulse':1,'dco.noise':.5,'vcf.freq':2.2,'vcf.reso':5,'vcf.env':5,'env.decay':2,'env.sustain':0,'env.release':1.1}],
      ['drink','dexed','MARIMBA',[[66,0,.17,80],[59,.15,.18,94],[73,.4,.15,60]],{}],
    ];
    for (const [index,[name,instrument,preset,notes,parameters]] of cues.entries()) {
      const start = index*2+1;
      await call('add_track',{...A,name,instrument,preset,volume_db:-13});
      for (const [parameter,value] of Object.entries(parameters))
        await call('automate',{...A,track:name,parameter,points:[{bar:1,value},{bar:7,value}]});
      await call('write_notes',{...A,track:name,start_bar:start,bars:2,
        notes:notes.map(([pitch,beat,beats,velocity]) => ({pitch,beat,beats,velocity}))});
      await call('add_marker',{...A,at_bar:start,name});
    }
  }
  fs.writeFileSync(marker,id+'\n');
  await call('render_audio',{...A,from_bar:1,bars:6,path:path.join(process.env.ALCHEMY_EXPORT,'cues.wav'),per_track:false,tail_seconds:.2});
} finally {
  await client.close();
}
JS
cd "$ALCHEMY_REPO"
python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess

scratch = Path(os.environ['ALCHEMY_EXPORT'])
assets = Path('client/assets')
metadata = dict(project=(scratch / 'project').read_text().strip(), bpm=120, clips={})
for index, (cue, duration) in enumerate([('pick', .5), ('brew', .8), ('drink', .75)]):
    target = assets / f'sfx_alchemy_{cue}.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(index * 4), '-i', str(scratch / 'cues.wav'),
                    '-t', str(duration), '-ac', '1', '-ar', '44100',
                    '-af', f'highpass=f=25,volume=2,alimiter=limit=0.65:level=false,afade=t=in:d=0.005,afade=t=out:st={duration-.07}:d=0.07',
                    '-map_metadata', '-1', '-c:a', 'libmp3lame', '-b:a', '96k', str(target)], check=True)
    metadata['clips'][cue] = dict(file=target.name, bar=index * 2 + 1, duration=duration,
                                  sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(assets / 'alchemy-sounds.txt').write_text(json.dumps(metadata, indent=2) + '\n')
PY
