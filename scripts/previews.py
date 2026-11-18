"""Install and render each untrusted registry item only inside resource-limited Docker."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]

def run(args,timeout=300):
    return subprocess.run(args,cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout).stdout.decode()

def preview(c):
    name='component-preview-'+c['id'];scratch=ROOT/'.scratch'/c['id'];scratch.mkdir(parents=True,exist_ok=True)
    log=[]
    try:
        run(['docker','run','-d','--name',name,'--cpus','2','--memory','3g','--pids-limit','512','--cap-drop','ALL','--security-opt','no-new-privileges','component-board-preview'])
        run(['docker','exec',name,'sh','-c','cp style-base.css src/style.css'])
        run(['docker','cp',str(ROOT/'data/evidence'/(c['id']+'.json')),name+':/preview/item.json'])
        log.append(run(['docker','exec',name,'npx','shadcn','add','/preview/item.json','--yes','--overwrite'],timeout=360))
        # The network is physically disconnected before executing source or starting the browser.
        run(['docker','network','disconnect','bridge',name])
        log.append(run(['docker','exec',name,'node','prepare.mjs',c['id']],timeout=30))
        run(['docker','exec','-d',name,'sh','-c','npx vite > /output/vite.log 2>&1'])
        log.append(run(['docker','exec',name,'node','capture.mjs',c['id']],timeout=120))
        log.append(run(['docker','exec',name,'node','measure.mjs'],timeout=260))
        for filename in ['light.png','dark.png','interaction.png','clip.webm','capture.json','installed.json','size.json']:
            try:run(['docker','cp',name+':/output/'+filename,str(scratch/filename)],timeout=20)
            except subprocess.CalledProcessError:
                if filename in ('light.png','dark.png','capture.json'):raise
        out=ROOT/'public/previews'/c['id'];out.mkdir(exist_ok=True)
        c['previews']={}
        for key,filename in [('light','light.png'),('dark','dark.png'),('interaction','interaction.png'),('clip','clip.webm')]:
            if (scratch/filename).is_file() and not (scratch/filename).is_symlink():
                shutil.copyfile(scratch/filename,out/filename);c['previews'][key]=f'/previews/{c["id"]}/{filename}'
        shutil.copyfile(scratch/'capture.json',ROOT/'data/evidence'/(c['id']+'-capture.json'))
        if (scratch/'size.json').exists():
            size=json.loads((scratch/'size.json').read_text())
            c['addedSize']=f"{size['incrementalGzipBytes']/1024:.1f} KB gzip over empty React harness (upstream preview); Implicity port unmeasured"
            shutil.copyfile(scratch/'size.json',ROOT/'data/evidence'/(c['id']+'-size.json'))
        print('PASS',c['id'],flush=True)
        return True
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
        
        try: log.append(run(['docker','exec',name,'cat','/output/vite.log'],timeout=10))
        except Exception: pass
        log.append(str(error));log.append(getattr(error,'stdout',b'').decode(errors='replace') if isinstance(getattr(error,'stdout',None),bytes) else str(getattr(error,'stdout','')))
        print('FAIL',c['id'],str(error)[-200:],flush=True);return False
    finally:
        (scratch/'run.log').write_text('\n'.join(log))
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--id');parser.add_argument('--build',action='store_true');args=parser.parse_args()
    if args.build:print(run(['docker','build','-t','component-board-preview','-f','scripts/preview/Dockerfile','.'],timeout=600)[-2000:])
    path=ROOT/'data/candidates.json';candidates=json.loads(path.read_text());failed=[]
    for c in candidates:
        if args.id and c['id']!=args.id:continue
        if c['previews'] and (ROOT/'data/evidence'/(c['id']+'-size.json')).exists() and not args.id:continue
        if not preview(c):failed.append(c['id'])
        path.write_text(json.dumps(candidates,indent=2))
    if failed:raise SystemExit('Preview failures: '+', '.join(failed))

if __name__=='__main__':main()
