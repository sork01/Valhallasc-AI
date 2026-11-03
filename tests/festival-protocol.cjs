// Exercise the advertised scenario through the actual MCP transport and private Rust world.
const assert=require('node:assert/strict'),path=require('node:path');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
(async()=>{
 const client=new Client({name:'festival-private-check',version:'1.0.0'});
 try{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.resolve(__dirname,'../scripts/test-mcp.cjs')],cwd:path.resolve(__dirname,'..'),env:{...process.env},stderr:'pipe'}));
  const result=await client.callTool({name:'run_scenario',arguments:{name:'festival'}},undefined,{timeout:120000});
  assert.ok(!result.isError,JSON.stringify(result.content));
  const report=result.structuredContent;
  assert.equal(report.passed,true,JSON.stringify(report));
  console.log(JSON.stringify(report,null,2));
 }finally{await client.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
