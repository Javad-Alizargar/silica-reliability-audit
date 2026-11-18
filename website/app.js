'use strict';
const A=window.ReliabilityAudit,$=id=>document.getElementById(id);
const titles={pooled:'Pooled rows',one_per_study:'One per study',study_max:'Study maximum',label_conditional:'Label conditional'};
const state={parsed:null,validation:null,result:null,name:'',hash:null};
const percent=x=>x==null?'n.a.':(100*x).toFixed(1)+'%',number=x=>Number(x).toLocaleString('en');
const fields=[['study','Source / study',['study','source','source_id','study_id','publication_id']],['y','Measured label',['y','label','target','outcome']],['p','Probability of label 1',['p','probability','prob','y_prob','prediction']],['role','Partition role',['role','split','partition']],['row_id','Observation ID (optional)',['row_id','id','sample_id','observation_id']]];
function error(message){$('error').textContent=message;$('error').hidden=false;}
function clearError(){$('error').hidden=true;$('error').textContent='';}
async function load(text,name){
  clearError();$('output').hidden=true;$('mapping').hidden=true;state.result=null;state.hash=null;
  try{state.parsed=A.parseCSV(text);if(state.parsed.rows.length>100000)throw Error('This browser workbench supports at most 100,000 observations per audit.');state.name=name;
    if(globalThis.crypto?.subtle){const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));state.hash=[...new Uint8Array(hash)].map(x=>x.toString(16).padStart(2,'0')).join('');}
    $('file-name').textContent=name+' · '+number(state.parsed.rows.length)+' rows';$('map-controls').replaceChildren();
    fields.forEach(([key,label,aliases])=>{const wrap=document.createElement('label');wrap.textContent=label;const select=document.createElement('select');select.id='map-'+key;
      const blank=document.createElement('option');blank.value='';blank.textContent=key==='row_id'?'Generate IDs':'Choose column';select.appendChild(blank);
      state.parsed.headers.forEach(h=>{const option=document.createElement('option');option.value=h;option.textContent=h;select.appendChild(option);});
      select.value=state.parsed.headers.find(h=>aliases.includes(h.toLowerCase()))||'';select.addEventListener('change',validate);wrap.appendChild(select);$('map-controls').appendChild(wrap);});
    $('mapping').hidden=false;validate();
  }catch(e){error(e.message);state.parsed=null;}
}
function validate(){
  if(!state.parsed)return false;clearError();const map=Object.fromEntries(fields.map(([key])=>[key,$('map-'+key).value]));
  const missing=fields.filter(([key])=>key!=='row_id'&&!map[key]);const v=missing.length?{errors:['Map all four required fields.'],warnings:[],records:[],groups:{}}:A.normalise(state.parsed,map,$('independent').checked);
  state.validation=v;state.map=map;const node=$('validation');node.replaceChildren();node.classList.toggle('error',v.errors.length>0);
  const heading=document.createElement('strong');heading.textContent=v.errors.length?v.errors.length+' validation issue(s)':'Data structure checked';node.appendChild(heading);
  const items=v.errors.length?v.errors.slice(0,12):v.warnings;
  if(items.length){const ul=document.createElement('ul');items.forEach(s=>{const li=document.createElement('li');li.textContent=s;ul.appendChild(li);});node.appendChild(ul);}
  if(!v.errors.length){const p=document.createElement('p');p.textContent=number(v.records.filter(x=>x.role==='calibration').length)+' calibration rows; '+number(v.records.filter(x=>x.role==='evaluation').length)+' evaluation rows. Source independence is a design assumption, not something this file alone can establish.';node.appendChild(p);}
  $('run').disabled=v.errors.length>0;$('output').hidden=true;state.result=null;return !v.errors.length;
}
function run(){if(!state.validation||state.validation.errors.length)return;clearError();const seed=Number($('seed').value);if(!Number.isInteger(seed)||seed<0||seed>4294967295){state.result=null;$('output').hidden=true;error('Sampling seed must be an integer from 0 to 4294967295. Set the seed after re-running the audit.');$('seed').value='20261118';return;}
  try{state.result=A.run(state.validation.records,Number($('alpha').value),seed);$('output').hidden=false;render();}catch(e){error(e.message);}}
function svgNode(svg,tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;svg.appendChild(n);return n;}
function classChart(r){const svg=$('class-chart');svg.replaceChildren();const add=(t,a,s)=>svgNode(svg,t,a,s);const y0=200,h=150;
  [0,.5,1].forEach(f=>{const y=y0-f*h;add('line',{x1:50,x2:510,y1:y,y2:y,stroke:'#dce6e1'});add('text',{x:40,y:y+4,'text-anchor':'end','font-size':11,fill:'#5a7074'},percent(f));});
  const ref=y0-(1-state.result.alpha)*h;add('line',{x1:50,x2:510,y1:ref,y2:ref,stroke:'#a9804d','stroke-dasharray':'5 4'});add('text',{x:510,y:ref-7,'text-anchor':'end','font-size':10,fill:'#82663b'},'1 − α reference');
  r.class_coverage.forEach((value,c)=>{const x=170+c*210;if(value!=null)add('rect',{x:x-43,y:y0-value*h,width:86,height:value*h,rx:3,fill:c?'#c17d37':'#1e7a83'});add('text',{x,y:222,'text-anchor':'middle','font-size':12,fill:'#173c43'},'Label '+c+' (n='+r.class_counts[c]+')');add('text',{x,y:Math.max(25,y0-(value??0)*h-10),'text-anchor':'middle','font-size':13,fill:'#173c43'},percent(value));});
  $('class-text').textContent='Accepted false negatives: '+r.false_negative_count+' / '+r.positive+' recorded positives ('+percent(r.false_negative_fraction)+').';}
function riskChart(curve){const svg=$('risk-chart');svg.replaceChildren();const add=(t,a,s)=>svgNode(svg,t,a,s),x0=55,y0=200,w=450,h=150;const ymax=Math.max(.2,...curve.filter(x=>x.error!=null).map(x=>x.error))*1.15;
  [0,.5,1].forEach(f=>{add('line',{x1:x0,x2:x0+w,y1:y0-f*h,y2:y0-f*h,stroke:'#dce6e1'});add('text',{x:46,y:y0-f*h+4,'text-anchor':'end','font-size':11,fill:'#5a7074'},percent(f*ymax));add('text',{x:x0+f*w,y:219,'text-anchor':'middle','font-size':11,fill:'#5a7074'},percent(f));});
  const points=curve.filter(x=>x.error!=null).sort((a,b)=>a.accepted_fraction-b.accepted_fraction);add('polyline',{points:points.map(p=>(x0+p.accepted_fraction*w)+','+(y0-p.error/ymax*h)).join(' '),fill:'none',stroke:'#1e7a83','stroke-width':2});
  points.forEach(p=>{const circle=add('circle',{cx:x0+p.accepted_fraction*w,cy:y0-p.error/ymax*h,r:3.5,fill:'#1e7a83'});svgNode(circle,'title',{},'Threshold '+p.threshold+': '+percent(p.accepted_fraction)+' accepted; '+percent(p.error)+' error');});add('text',{x:280,y:243,'text-anchor':'middle','font-size':11,fill:'#5a7074'},'Fraction of observations accepted');add('text',{x:55,y:23,'font-size':11,fill:'#5a7074'},'Error among accepted predictions');}
function row(table,values,active=false){const tr=document.createElement('tr');if(active)tr.className='active-row';values.forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.appendChild(td);});table.appendChild(tr);}
function renderSources(){if(!state.result)return;const r=state.result.results[$('method').value],query=$('source-filter').value.trim().toLowerCase(),filtered=r.per_source.filter(x=>x.study.toLowerCase().includes(query));$('sources').replaceChildren();filtered.slice(0,100).forEach(s=>row($('sources'),[s.study,s.n,percent(s.coverage),s.singletons,s.errors]));$('source-limit').textContent='Showing '+Math.min(100,filtered.length)+' of '+filtered.length+' matching sources. The CSV includes all sources.';}
function render(){const audit=state.result;if(!audit)return;const selected=$('method').value,r=audit.results[selected];
  $('counts').textContent=number(audit.calibration_n)+' calibration rows / '+audit.calibration_sources+' sources → '+number(r.n)+' evaluation rows / '+r.sources+' sources';
  $('coverage').textContent=percent(r.row_coverage);$('whole').textContent=percent(r.whole_source_coverage);$('single').textContent=percent(r.singleton_rate);$('risk').textContent=percent(r.singleton_error);
  $('single-count').textContent=r.singletons+' / '+r.n+' observations';$('risk-count').textContent=r.singleton_errors+' / '+r.singletons+' single-label outputs';
  let note=titles[selected]+': '+r.singletons+' observations receive one label; '+Math.round(r.empty_rate*r.n)+' receive an empty set. '+(r.singletons?'The observed singleton error is '+percent(r.singleton_error)+'.':'There are no singleton predictions, so their error rate is undefined.');
  if(r.q.some(x=>!Number.isFinite(x)))note+=' At least one threshold is infinite because there are too few calibration units at this α. This correctly preserves the finite-sample rule.';
  if(state.validation.overlap)note+=' Sources overlap: interpret these outputs only as a within-source audit.';
  note+=' These observed percentages are not population guarantees; the browser report does not compute confidence intervals.';$('interpretation').textContent=note;
  $('comparison').replaceChildren();Object.entries(audit.results).forEach(([method,s])=>row($('comparison'),[titles[method],percent(s.row_coverage),percent(s.class_coverage[0]),percent(s.class_coverage[1]),percent(s.whole_source_coverage),s.singletons+' / '+s.n,s.singleton_errors+' / '+s.singletons],method===selected));
  $('threshold-note').textContent='Selected thresholds q₀='+formatQ(r.q[0])+', q₁='+formatQ(r.q[1])+'. Calibration units: '+r.units.join(' / ')+'. One-per-study sampling uses recorded input order, sorted source IDs and an LCG32 seed; selected row IDs are retained in the JSON report.';
  classChart(r);riskChart(audit.confidence_curve);renderSources();}
function formatQ(q){return Number.isFinite(q)?q.toFixed(4):'∞';}
function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function summaryRows(){return Object.entries(state.result.results).map(([method,r])=>({method,n:r.n,sources:r.sources,row_coverage:r.row_coverage,coverage_0:r.class_coverage[0],coverage_1:r.class_coverage[1],whole_source_coverage:r.whole_source_coverage,singletons:r.singletons,singleton_errors:r.singleton_errors,singleton_error:r.singleton_error,empty_rate:r.empty_rate,q0:Number.isFinite(r.q[0])?r.q[0]:'Infinity',q1:Number.isFinite(r.q[1])?r.q[1]:'Infinity'}));}
$('file').addEventListener('change',async e=>{const file=e.target.files[0];if(file){if(file.size>20*1024*1024)return error('File exceeds the 20 MB local-audit limit.');await load(await file.text(),file.name);}});
$('demo').addEventListener('click',()=>load(window.EXAMPLE_CSV,'silica_example.csv'));
$('independent').addEventListener('change',validate);$('run').addEventListener('click',()=>{run();if(state.result)$('output').scrollIntoView({behavior:'smooth',block:'start'});});
['alpha','seed'].forEach(id=>$(id).addEventListener('change',run));$('method').addEventListener('change',render);$('source-filter').addEventListener('input',renderSources);
$('dropzone').addEventListener('dragover',e=>{e.preventDefault();$('dropzone').classList.add('drag');});$('dropzone').addEventListener('dragleave',()=> $('dropzone').classList.remove('drag'));
$('dropzone').addEventListener('drop',async e=>{e.preventDefault();$('dropzone').classList.remove('drag');const file=e.dataTransfer.files[0];if(file){if(file.size>20*1024*1024)return error('File exceeds 20 MB.');await load(await file.text(),file.name);}});
$('template').addEventListener('click',()=>download('reliability_input_template.csv','row_id,study,y,p,role\r\ncal_01,source_A,0,0.12,calibration\r\ncal_02,source_B,1,0.81,calibration\r\neval_01,source_C,0,0.25,evaluation\r\neval_02,source_D,1,0.71,evaluation\r\n','text/csv'));
$('export-csv').addEventListener('click',()=>{const method=$('method').value,r=state.result.results[method];const labels=['empty','0','1','0|1'];download('prediction_sets.csv',A.csv(state.result.evaluation.map((x,i)=>({...x,method,alpha:state.result.alpha,prediction_set:labels[r.codes[i]],singleton:[1,2].includes(r.codes[i]),contains_true_label:Boolean(r.codes[i]&(1<<x.y))}))),'text/csv');});
$('export-summary').addEventListener('click',()=>download('calibration_summary.csv',A.csv(summaryRows()),'text/csv'));
$('export-sources').addEventListener('click',()=>download('source_diagnostics.csv',A.csv(state.result.results[$('method').value].per_source),'text/csv'));
$('export-json').addEventListener('click',()=>{const results=Object.fromEntries(Object.entries(state.result.results).map(([k,v])=>{const {codes,...rest}=v;return [k,rest];}));const report={software:'NanoReliability',version:'0.2.0-draft',generated_at:new Date().toISOString(),input_file:state.name,input_sha256:state.hash,column_mapping:state.map,alpha:state.result.alpha,seed:state.result.seed,sampling_algorithm:'LCG32 (1664525, 1013904223), sorted source IDs, input row order',require_disjoint_sources:$('independent').checked,source_overlap:state.validation.overlap,warnings:state.validation.warnings,calibration_n:state.result.calibration_n,calibration_sources:state.result.calibration_sources,results,confidence_curve:state.result.confidence_curve,limitations:['Observed metrics only; no confidence intervals computed','Independence and exchangeability cannot be proven from the file','Uploaded probabilities must have been generated without evaluation-label access','Prediction-set coverage does not bound singleton error']};download('reliability_audit.json',JSON.stringify(report,(_,v)=>typeof v==='number'&&!Number.isFinite(v)?'Infinity':v,2),'application/json');});
