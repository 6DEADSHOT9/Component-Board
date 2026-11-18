import {chromium} from '@playwright/test';
import fs from 'node:fs';
const slug=process.argv[2], fixture=JSON.parse(fs.readFileSync('fixtures.json','utf8'))[slug];
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:960,height:600},recordVideo:{dir:'/output/video',size:{width:960,height:600}}});
await context.grantPermissions(['clipboard-read','clipboard-write'],{origin:'http://127.0.0.1:5173'});
await context.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
for(let i=0;i<100;i++){try{const r=await fetch('http://127.0.0.1:5173');if(r.ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
await page.goto('http://127.0.0.1:5173',{waitUntil:'networkidle',timeout:60000});
await page.waitForTimeout(1500);
if(fixture.setupClick){await page.locator(fixture.setupClick).first().click();await page.waitForTimeout(650);}
if(errors.length) throw Error(errors.join('\n'));
await page.locator('#fixture').waitFor({timeout:10000});
if(!(await page.locator('#fixture').innerHTML()).trim())throw Error('Empty preview');
await page.locator(fixture.captureSelector || '#fixture > *:visible').first().screenshot({path:'/output/light.png'});
await page.evaluate(()=>document.documentElement.classList.add('dark'));
await page.locator(fixture.captureSelector || '#fixture > *:visible').first().screenshot({path:'/output/dark.png'});
await page.evaluate(()=>document.documentElement.classList.remove('dark'));
if(fixture.action){
 const action=fixture.action;
 if(action.upload)await page.locator(action.selector).setInputFiles({name:'review-notes.txt',mimeType:'text/plain',buffer:Buffer.from('Synthetic review attachment')});
 else if(action.drag){ const box=await page.locator(action.selector).last().boundingBox();if(!box)throw Error('Missing draggable item');await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+55,box.y+box.height/2,{steps:12});await page.mouse.up(); }
 else if(action.fill)await page.locator(action.selector).first().fill(action.fill);
 else await page.locator(action.selector).first().click();
 await page.waitForTimeout(650);await page.screenshot({path:'/output/interaction.png'});
}
if(errors.length)throw Error(errors.join('\n'));
await context.close();await browser.close();
const video=fs.readdirSync('/output/video').find(f=>f.endsWith('.webm'));if(fixture.action&&video)fs.renameSync('/output/video/'+video,'/output/clip.webm');
fs.writeFileSync('/output/capture.json',JSON.stringify({slug,viewport:'960x600',offline:true,errors},null,2));
