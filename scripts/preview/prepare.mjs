import fs from 'node:fs';
import path from 'node:path';
const slug=process.argv[2];
const fixtures=JSON.parse(fs.readFileSync('fixtures.json','utf8'));
const fixture=fixtures[slug];
if(!fixture) throw Error('Missing fixture '+slug);
function files(dir) {return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name)):[path.join(dir,e.name)]);}
const candidates=files('src').filter(p=>/\.(t|j)sx?$/.test(p));
const target=candidates.find(p=>new RegExp(`(?:function|const|class) ${fixture.symbol}\\b`).test(fs.readFileSync(p,'utf8')));
if(!target) throw Error('Cannot locate '+fixture.symbol+' in '+candidates.join(','));
fs.writeFileSync('src/main.tsx',`import React,{useState} from 'react';import{createRoot}from'react-dom/client';import * as C from './${target.slice(4).replace(/\.tsx?$/,'')}';import './style.css';function Demo(){const [open,setOpen]=useState(false);const [value,setValue]=useState('');const [active,setActive]=useState('open');const [files,setFiles]=useState<File[]>([]);return <div id="fixture">${fixture.jsx}</div>}createRoot(document.getElementById('root')!).render(<Demo/>);`);
fs.writeFileSync('/output/installed.json',JSON.stringify({target,slug,files:candidates},null,2));
