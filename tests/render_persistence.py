"""Deployment acceptance only; refuses to touch a board containing team data."""
import http.cookiejar
import json
from pathlib import Path
import sys
import urllib.request
BASE='https://component-board.onrender.com'
secrets=dict(line.split('=',1) for line in Path('.secrets/deployment.env').read_text().splitlines() if '=' in line)
def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def call(c,path,data=None):
 with c.open(urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'} if data is not None else {}),timeout=90) as r:return json.load(r)
owner=client();call(owner,'/api/access',{'kind':'owner','code':secrets['OWNER_CODE']})
path=Path('.secrets/render-persistence-before.json')
if sys.argv[1]=='prepare':
 before=call(owner,'/api/export/json');assert not any(before[k] for k in ('people','votes','statuses')),'Real data exists; refusing live persistence mutation'
 reviewer=client();call(reviewer,'/api/access',{'code':secrets['INVITE_CODE']})
 call(reviewer,'/api/onboard',{'name':'Redeploy acceptance','email':'redeploy-smoke@example.test'})
 c=call(reviewer,'/api/components')['components'][0]
 call(reviewer,'/api/vote',{'component':c['id'],'version':c['version'],'choice':'abstain','reason':'Synthetic redeploy persistence check'})
 path.write_text(json.dumps(call(owner,'/api/export/json')));path.chmod(0o600)
 print('Prepared one synthetic participant and vote before Render redeploy')
elif sys.argv[1]=='verify':
 before=json.loads(path.read_text());after=call(owner,'/api/export/json')
 assert before==after,'Data changed across deploy; nothing deleted'
 call(owner,'/api/delete-all',{'confirm':'DELETE ALL'})
 print('PASS exact participant/vote snapshot survived Render redeploy; synthetic acceptance data removed')
else:raise SystemExit('Use prepare or verify')
