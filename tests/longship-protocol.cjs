// Only the new dungeon: real private MCP, real server travel/loot/quest persistence.
const assert=require('node:assert/strict'),path=require('node:path');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport,getDefaultEnvironment}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
(async()=>{
 const c=new Client({name:'longship-protocol',version:'1'});
 try{
  await c.connect(new StdioClientTransport({command:process.execPath,args:['scripts/test-mcp.cjs'],cwd:root,stderr:'pipe',env:{...getDefaultEnvironment(),VALHALLA_BINARY:process.env.VALHALLA_BINARY||path.join(root,'target/debug/valhalla-server')}}));
  const r=await c.callTool({name:'run_scenario',arguments:{name:'longship'}},undefined,{timeout:300000});
  assert.ok(!r.isError,JSON.stringify(r.content));console.log(JSON.stringify(r.structuredContent));assert.equal(r.structuredContent.passed,true);
 }finally{await c.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
