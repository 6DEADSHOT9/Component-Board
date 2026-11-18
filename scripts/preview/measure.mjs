import fs from 'node:fs';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
function build(dir){execFileSync('npx',['vite','build','--outDir',dir],{stdio:'pipe',timeout:120000});return walk(dir).filter(f=>/\.(js|css)$/.test(f)).reduce((n,f)=>n+gzipSync(fs.readFileSync(f)).length,0);}
const total=build('dist');
const main=fs.readFileSync('src/main.tsx','utf8');fs.cpSync('src/components','/tmp/installed-components',{recursive:true});fs.rmSync('src/components',{recursive:true});
try{
 fs.writeFileSync('src/main.tsx',`import React from 'react';import{createRoot}from'react-dom/client';import './style.css';createRoot(document.getElementById('root')).render(<div/>);`);
 const baseline=build('baseline');fs.writeFileSync('/output/size.json',JSON.stringify({previewGzipBytes:total,baselineGzipBytes:baseline,incrementalGzipBytes:Math.max(0,total-baseline),method:'Production Vite JS+CSS gzip sum, minus empty React+theme harness; preview fixture overhead included; actual Implicity port unmeasured'},null,2));
}finally{fs.writeFileSync('src/main.tsx',main);fs.cpSync('/tmp/installed-components','src/components',{recursive:true});fs.rmSync('/tmp/installed-components',{recursive:true});}
