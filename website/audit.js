/* Browser-local reliability analysis. No remote calls or model fitting. */
(function(global){'use strict';
function parseCSV(text){
  text=text.replace(/^\uFEFF/,'');const rows=[];let row=[],cell='',quoted=false;
  for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else if(quoted||cell==='')quoted=!quoted;else throw Error('Unexpected quote in CSV cell.');}
    else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(x=>x.trim()!==''))rows.push(row);row=[];cell='';}else cell+=c;}
  if(quoted)throw Error('Unclosed quote in CSV.');row.push(cell);if(row.some(x=>x.trim()!==''))rows.push(row);
  if(rows.length<2)throw Error('CSV needs a header and at least one data row.');
  const headers=rows.shift().map(x=>x.trim());if(headers.some(x=>!x)||new Set(headers).size!==headers.length)throw Error('Column names must be unique and nonempty.');
  if(rows.some(r=>r.length!==headers.length))throw Error('Each row must have the same number of columns as the header.');
  return {headers,rows:rows.map(r=>Object.fromEntries(headers.map((h,i)=>[h,r[i]])))};
}
function normalise(parsed,map,independent=true){
  const errors=[],warnings=[],records=[],ids=new Map(),roleGroups={calibration:new Set(),evaluation:new Set(),training:new Set()};let highDose=0;
  parsed.rows.forEach((r,i)=>{
    const source=String(r[map.study]??'').trim(),ys=String(r[map.y]??'').trim(),ps=String(r[map.p]??'').trim();
    const y=Number(ys),p=Number(ps),rawRole=String(r[map.role]??'').trim().toLowerCase();
    const role=({cal:'calibration',calibrate:'calibration',calibration:'calibration',test:'evaluation',evaluation:'evaluation',eval:'evaluation',train:'training',fit:'training',training:'training'})[rawRole];
    const id=map.row_id?String(r[map.row_id]??'').trim():'row-'+(i+2);
    if(!source||!id||!role||ys===''||ps===''||![0,1].includes(y)||!Number.isFinite(p)||p<0||p>1){errors.push('Row '+(i+2)+': check nonempty ID/source, role, binary label and probability in [0,1].');return;}
    if(ids.has(id))errors.push('Row '+(i+2)+': repeated row ID '+id+'.');ids.set(id,role);roleGroups[role].add(source);
    if(r.dose_ug_ml!==undefined&&String(r.dose_ug_ml).trim()!==''&&Number(r.dose_ug_ml)>10000)highDose++;
    records.push({row_id:id,study:source,y,p,role});
  });
  for(const role of ['calibration','evaluation'])if(!records.some(x=>x.role===role))errors.push('At least one '+role+' observation is required.');
  const pairs=[['calibration','evaluation'],['training','calibration'],['training','evaluation']];let overlap=0;
  for(const [a,b]of pairs){const shared=[...roleGroups[a]].filter(x=>roleGroups[b].has(x));overlap+=shared.length;if(shared.length){const msg=shared.length+' source group(s) appear in both '+a+' and '+b+'.';(independent?errors:warnings).push(msg);}}
  if(!map.row_id)warnings.push('No row ID supplied. Generated row IDs cannot detect repeated experiments.');
  if(!roleGroups.training.size)warnings.push('Fitting-source provenance was not supplied. Confirm that uploaded probabilities were generated without using calibration or evaluation labels.');
  if(highDose)warnings.push(highDose+' reported doses exceed 10,000 µg/mL. Check original units; a large value is not automatically an error.');
  const cal=records.filter(x=>x.role==='calibration');if(new Set(cal.map(x=>x.y)).size<2)warnings.push('Only one label appears in calibration. The absent class receives an infinite label-conditional threshold.');
  return {records,errors,warnings,overlap,groups:Object.fromEntries(Object.entries(roleGroups).map(([k,s])=>[k,s.size]))};
}
function quantile(scores,alpha){const k=Math.ceil((scores.length+1)*(1-alpha));if(k>scores.length||!scores.length)return Infinity;return [...scores].sort((a,b)=>a-b)[k-1];}
function rng(seed){let state=seed>>>0;return()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};}
function calibrate(cal,method,alpha,seed){
  const scored=cal.map(r=>({...r,score:r.y===1?1-r.p:r.p}));
  if(method==='label_conditional'){const groups=[0,1].map(c=>scored.filter(r=>r.y===c));return {q:groups.map(x=>quantile(x.map(r=>r.score),alpha)),units:groups.map(x=>x.length),selected:[]};}
  const groups=new Map();scored.forEach(r=>{if(!groups.has(r.study))groups.set(r.study,[]);groups.get(r.study).push(r);});
  let scores=[],selected=[];
  if(method==='pooled')scores=scored.map(r=>r.score);
  else if(method==='study_max')scores=[...groups.values()].map(x=>Math.max(...x.map(r=>r.score)));
  else if(method==='one_per_study'){const random=rng(seed);for(const source of [...groups.keys()].sort()){const g=groups.get(source);const row=g[Math.floor(random()*g.length)];scores.push(row.score);selected.push(row.row_id);}}
  else throw Error('Unknown calibration rule.');
  const q=quantile(scores,alpha);return {q:[q,q],units:[scores.length,scores.length],selected};
}
function code(p,q){return (p<=q[0]?1:0)+(1-p<=q[1]?2:0);}
function metrics(rows,codes){
  const groups=new Map();let covered=0,single=0,errors=0,empty=0,size=0,fn=0,brier=0,positive=0;
  const cn=[0,0],ch=[0,0],cs=[0,0];
  rows.forEach((r,i)=>{const c=codes[i],hit=Boolean(c&(1<<r.y)),one=c===1||c===2;covered+=hit;single+=one;errors+=one&&!hit;empty+=c===0;size+=(c&1)+((c>>1)&1);fn+=c===1&&r.y===1;brier+=(r.p-r.y)**2;positive+=r.y;cn[r.y]++;ch[r.y]+=hit;cs[r.y]+=one;
    if(!groups.has(r.study))groups.set(r.study,{study:r.study,n:0,covered:0,singletons:0,errors:0});const g=groups.get(r.study);g.n++;g.covered+=hit;g.singletons+=one;g.errors+=one&&!hit;});
  const sources=[...groups.values()].map(g=>({...g,coverage:g.covered/g.n,singleton_rate:g.singletons/g.n,error:g.singletons?g.errors/g.singletons:null}));
  return {n:rows.length,sources:sources.length,positive,row_coverage:covered/rows.length,whole_source_coverage:sources.filter(g=>g.covered===g.n).length/sources.length,
    source_balanced_coverage:sources.reduce((s,g)=>s+g.coverage,0)/sources.length,singleton_rate:single/rows.length,singletons:single,singleton_errors:errors,
    singleton_error:single?errors/single:null,empty_rate:empty/rows.length,mean_set_size:size/rows.length,false_negative_count:fn,false_negative_fraction:positive?fn/positive:null,
    brier:brier/rows.length,class_counts:cn,class_coverage:cn.map((n,c)=>n?ch[c]/n:null),class_singletons:cs,per_source:sources.sort((a,b)=>b.n-a.n||a.study.localeCompare(b.study))};
}
function run(records,alpha,seed){
  if(!(alpha>0&&alpha<1))throw Error('Alpha must lie strictly between zero and one.');
  const calibration=records.filter(r=>r.role==='calibration'),evaluation=records.filter(r=>r.role==='evaluation');
  const results={};for(const method of ['pooled','one_per_study','study_max','label_conditional']){const q=calibrate(calibration,method,alpha,seed);const codes=evaluation.map(r=>code(r.p,q.q));results[method]={method,...q,codes,...metrics(evaluation,codes)};}
  const curve=[];for(const t of [.5,.55,.6,.65,.7,.75,.8,.85,.9,.95,.975,.99]){const accepted=evaluation.filter(r=>Math.max(r.p,1-r.p)>=t);curve.push({threshold:t,accepted_fraction:accepted.length/evaluation.length,error:accepted.length?accepted.filter(r=>Number(r.p>=.5)!==r.y).length/accepted.length:null});}
  return {alpha,seed,calibration_n:calibration.length,calibration_sources:new Set(calibration.map(r=>r.study)).size,evaluation,results,confidence_curve:curve};
}
function csv(rows){if(!rows.length)return '';const headers=Object.keys(rows[0]),escape=x=>'"'+String(x??'').replace(/"/g,'""')+'"';return [headers,...rows.map(r=>headers.map(h=>r[h]))].map(r=>r.map(escape).join(',')).join('\r\n');}
global.ReliabilityAudit={parseCSV,normalise,quantile,calibrate,code,metrics,run,csv};if(typeof module!=='undefined')module.exports=global.ReliabilityAudit;
})(typeof window!=='undefined'?window:globalThis);
