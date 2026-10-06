import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {evaluateToolCall,loadPolicy,redactBlocks} from '../../../tools/harness/lib/policy.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const PATH_KEYS=new Set(['path','paths','filePath','file_path','target','destination','dest','source','from','to','oldPath','newPath']);

function audit(value){
  try{
    const directory=path.join(ROOT,'.omp/audit');
    fs.mkdirSync(directory,{recursive:true});
    fs.appendFileSync(path.join(directory,'fadd-policy.jsonl'),JSON.stringify({...value,timestamp:new Date().toISOString()})+'\n');
  }catch{}
}

function inputPaths(input){
  const output=[];
  function visit(value,key=''){
    if(value==null)return;
    if(typeof value==='string'){
      if(PATH_KEYS.has(key))output.push(value);
      return;
    }
    if(Array.isArray(value)){
      value.forEach(item=>visit(item,key));
      return;
    }
    if(typeof value==='object'){
      for(const [childKey,child] of Object.entries(value))visit(child,childKey);
    }
  }
  visit(input);
  return [...new Set(output)];
}

function bootstrapAllowed(raw){
  const absolute=path.isAbsolute(raw)?path.resolve(raw):path.resolve(ROOT,raw);
  const relative=path.relative(ROOT,absolute).split(path.sep).join('/');
  if(relative.startsWith('../')||path.isAbsolute(relative))return false;
  if(['.fadd/bootstrap-result.json','.gitlab-ci.fadd.yml','docs/spec-index.json','tools/gc/policy.json','AGENTS.md'].includes(relative))return true;
  if(/^\.github\/workflows\/fadd-[^/]+\.yml$/.test(relative))return true;
  return ['architecture/','security/threat-model/','quality/','container/'].some(prefix=>relative.startsWith(prefix));
}

function bootstrapProtectedOverride(event,decision){
  if(process.env.FADD_BOOTSTRAP!=='1'||decision.ruleId!=='POLICY-PATH-PROTECTED')return false;
  const candidates=inputPaths(event.input);
  return candidates.length>0&&candidates.every(bootstrapAllowed);
}

export default function(pi){
  pi.on('tool_call',async event=>{
    let policy;
    try{
      policy=loadPolicy(ROOT);
    }catch(error){
      throw new Error(`FADD-POLICY-UNAVAILABLE: ${error.message}`);
    }
    const decision=evaluateToolCall({toolName:event.toolName,input:event.input,cwd:ROOT,policy});
    if(!decision.allow&&!bootstrapProtectedOverride(event,decision)){
      audit({event:'blocked',toolName:event.toolName,ruleId:decision.ruleId});
      return{block:true,reason:`${decision.ruleId}: ${decision.reason}`};
    }
    if(!decision.allow){
      audit({event:'bootstrap-bounded-override',toolName:event.toolName,ruleId:decision.ruleId});
    }
  });
  pi.on('tool_result',async event=>{
    try{
      const policy=loadPolicy(ROOT);
      const content=redactBlocks(event.content,policy);
      const details=redactBlocks(event.details,policy);
      if(JSON.stringify(content)!==JSON.stringify(event.content)||JSON.stringify(details)!==JSON.stringify(event.details)){
        audit({event:'redacted',toolName:event.toolName});
        return{content,details};
      }
    }catch(error){
      audit({event:'redaction-failed',error:String(error)});
      return{content:[{type:'text',text:'[TOOL RESULT WITHHELD: REDACTION POLICY UNAVAILABLE]'}],details:{withheld:true}};
    }
  });
}
