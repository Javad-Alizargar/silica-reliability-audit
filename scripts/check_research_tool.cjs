/* Real browser flow tests for the isolated researcher-facing website. */
'use strict';
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..'),out=path.join(root,'reports/v2/browser');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1050},acceptDownloads:true});
const errors=[],network=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:8766/')&&!r.url().startsWith('blob:'))network.push(r.url());});
async function upload(name,csv){await page.locator('#file').setInputFiles({name,mimeType:'text/csv',buffer:Buffer.from(csv)});await page.waitForFunction(n=>document.getElementById('file-name').textContent.startsWith(n),name);}
await page.goto('http://127.0.0.1:8766/');await page.screenshot({path:path.join(out,'desktop_start.png'),fullPage:true});
await page.click('#demo');await page.click('#run');await page.locator('#coverage').waitFor();
assert.equal(await page.locator('#single-count').innerText(),'45 / 905 observations');let combinations=0;
for(const method of ['pooled','one_per_study','study_max','label_conditional'])for(const alpha of ['0.01','0.02','0.05','0.10','0.15','0.20','0.30']){
 await page.selectOption('#method',method);await page.selectOption('#alpha',alpha);assert(await page.locator('#output').isVisible());assert.equal(await page.locator('#comparison tr').count(),4);combinations++;}
await page.selectOption('#alpha','0.10');await page.selectOption('#method','label_conditional');assert.equal(await page.locator('#single-count').innerText(),'175 / 905 observations');
await page.fill('#source-filter','jat.3507');assert.equal(await page.locator('#sources tr').count(),1);await page.fill('#source-filter','');
const downloads=[];for(const [id,name]of [['export-json','reliability_audit.json'],['export-csv','prediction_sets.csv'],['export-summary','calibration_summary.csv'],['export-sources','source_diagnostics.csv'],['template','reliability_input_template.csv']]){
 const wait=page.waitForEvent('download');await page.click('#'+id);const dl=await wait;assert.equal(dl.suggestedFilename(),name);await dl.saveAs(path.join(out,name));downloads.push(name);}
const report=JSON.parse(fs.readFileSync(path.join(out,'reliability_audit.json')));assert.equal(report.results.label_conditional.singleton_errors,2);assert.equal(report.input_sha256.length,64);
await page.screenshot({path:path.join(out,'desktop_audit.png'),fullPage:true});
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile_audit.png'),fullPage:true});
assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile page overflow');
const custom='observation_id,source_id,outcome,probability,partition\na,A,0,.1,cal\nb,B,1,.8,cal\nc,C,0,.2,eval\nd,D,1,.9,eval';
await upload('custom.csv',custom);await page.click('#run');assert.equal(await page.locator('#risk').innerText(),'n.a.');assert((await page.locator('#interpretation').innerText()).includes('infinite'));
await upload('overlap.csv',custom.replace('d,D','d,A'));assert(await page.locator('#run').isDisabled());
await page.uncheck('#independent');await page.click('#run');assert((await page.locator('#interpretation').innerText()).includes('within-source'));await page.check('#independent');
await upload('invalid.csv',custom.replace('1,.9','1,1.9'));assert(await page.locator('#run').isDisabled());
await upload('duplicate.csv',custom.replace('d,D','a,D'));assert(await page.locator('#run').isDisabled());
await page.click('#demo');await page.click('#run');await page.fill('#seed','-1');await page.locator('#seed').dispatchEvent('change');assert(await page.locator('#output').isHidden());assert(await page.locator('#error').isVisible());
await page.click('#run');assert(await page.locator('#output').isVisible());
const html=await page.content();assert(!/manuscript|\.pdf|figures\/|Supplementary_Materials/i.test(html),'Private material mentioned');assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
const result={status:'passed',selector_combinations:combinations,downloads,flows:['real example','CSV upload and alias mapping','source filter','JSON fingerprint','small-sample infinity','undefined singleton error','source-overlap block and explicit override','invalid probability','duplicate ID','invalid seed recovery','390px mobile layout','no external network requests','no manuscript asset references'],page_errors:errors,external_requests:network};
fs.writeFileSync(path.join(out,'browser_qa.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
