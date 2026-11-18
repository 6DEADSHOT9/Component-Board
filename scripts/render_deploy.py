"""Render operations; credentials and sensitive API responses remain under .secrets/."""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import urllib.request
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.secrets'
PRIVATE.mkdir(exist_ok=True)

def env(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line and not line.startswith('#'))

def save(name,value):
    path=PRIVATE/name;path.write_text(json.dumps(value,indent=2));path.chmod(0o600)


def api(path,data=None,method=None):
    key=env(ROOT/'.env')['RENDERAPIKEY'].strip().strip('"').strip("'")
    req=urllib.request.Request('https://api.render.com/v1/'+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        # API validation errors contain request context; keep them out of terminal output.
        save('render-error.json',{'status':e.code,'path':path,'body':e.read().decode()})
        raise SystemExit(f'Render returned HTTP {e.code}; details saved privately in .secrets/render-error.json')


def main():
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['list','create-db','db-status','create-web','web-status','deploy']);a=p.parse_args()
    if a.operation=='list':
        for x in api('postgres?ownerId=tea-dbuq00uk1f9s73b14k30&limit=100'):
            d=x.get('postgres',x);print('db',d.get('id'),d.get('name'),d.get('plan'),d.get('status'))
        for x in api('services?ownerId=tea-dbuq00uk1f9s73b14k30&limit=100'):
            d=x.get('service',x);print('web',d.get('id'),d.get('name'),d.get('type'))
    elif a.operation=='create-db':
        if (PRIVATE/'render-db.json').exists():raise SystemExit('Database receipt already exists; use db-status')
        result=api('postgres',{'name':'component-board-db','ownerId':'tea-dbuq00uk1f9s73b14k30','plan':'free','region':'oregon','version':'17','databaseName':'board','databaseUser':'board','ipAllowList':[]})
        save('render-db.json',result);print('Created database',result['id'],result.get('status'))
    elif a.operation=='db-status':
        receipt=json.loads((PRIVATE/'render-db.json').read_text());result=api('postgres/'+receipt['id']);save('render-db.json',result)
        print('Database',result['id'],result.get('status'),'expires',result.get('expiresAt'))
        if result.get('status')=='available':save('render-db-connection.json',api('postgres/'+result['id']+'/connection-info'))
    elif a.operation=='create-web':
        if (PRIVATE/'render-web.json').exists():raise SystemExit('Web receipt already exists; use web-status')
        database=json.loads((PRIVATE/'render-db.json').read_text());connection=json.loads((PRIVATE/'render-db-connection.json').read_text());secrets=env(PRIVATE/'deployment.env')
        expires=(database.get('expiresAt') or (datetime.now(timezone.utc)+timedelta(days=30)).isoformat())[:10]
        values={**secrets,'DATABASE_URL':connection['internalConnectionString'],'DATABASE_EXPIRES_AT':expires,'COOKIE_SECURE':'true'}
        result=api('services',{'type':'web_service','name':'component-board','ownerId':'tea-dbuq00uk1f9s73b14k30','repo':'https://github.com/6DEADSHOT9/Component-Board','branch':'main','autoDeployTrigger':'off','envVars':[{'key':k,'value':v} for k,v in values.items()],'serviceDetails':{'runtime':'docker','plan':'free','region':'oregon','healthCheckPath':'/health','envSpecificDetails':{'dockerfilePath':'./Dockerfile','dockerContext':'.'}}})
        save('render-web.json',result);service=result.get('service',result);print('Created service',service['id'],service.get('serviceDetails',{}).get('url'))
    else:
        receipt=json.loads((PRIVATE/'render-web.json').read_text());service=receipt.get('service',receipt);sid=service['id']
        if a.operation=='deploy':
            d=api('services/'+sid+'/deploys',{'clearCache':'do_not_clear'});save('render-deploy.json',d);print('Deploy requested',d['id'],d.get('status'))
        else:
            result=api('services/'+sid);save('render-web-status.json',result)
            print('Service',sid,result.get('serviceDetails',{}).get('url'))
            for x in api('services/'+sid+'/deploys?limit=3'):
                d=x.get('deploy',x);print('Deploy',d.get('id'),d.get('status'),d.get('commit',{}).get('id'))

if __name__=='__main__':main()
