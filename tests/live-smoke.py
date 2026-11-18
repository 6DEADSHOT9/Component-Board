"""Initial deployment acceptance only: refuses to run if the board contains team data."""
import http.cookiejar
import json
from pathlib import Path
import urllib.request

BASE='https://component-board.onrender.com'
SECRETS=dict(line.split('=',1) for line in Path('.secrets/deployment.env').read_text().splitlines() if '=' in line)

def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def call(c,path,data=None):
 req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'} if data is not None else {})
 with c.open(req,timeout=90) as response:return json.load(response)

owner=client();call(owner,'/api/access',{'kind':'owner','code':SECRETS['OWNER_CODE']})
backup=call(owner,'/api/export/json')
assert not backup['people'] and not backup['votes'] and not backup['statuses'],'Real data exists; live mutation smoke refused'
reviewer=client();call(reviewer,'/api/access',{'code':SECRETS['INVITE_CODE']})
call(reviewer,'/api/onboard',{'name':'Deployment smoke','email':'deployment-smoke@example.test'})
rows=call(reviewer,'/api/components')['components'];assert len(rows)==24
assert all(c['previews'].get('light') and c['previews'].get('dark') for c in rows),'Incomplete previews'
c=rows[0];call(reviewer,'/api/vote',{'component':c['id'],'version':c['version'],'choice':'abstain','reason':'Deployment acceptance test'})
assert call(reviewer,'/api/components')['components'][0]['vote']['choice']=='abstain'
export=call(owner,'/api/export/json');assert len(export['people'])==1 and len(export['votes'])==1
call(owner,'/api/delete-all',{'confirm':'DELETE ALL'})
print('PASS live invite exchange, onboarding, 24 complete previews, voting, owner export and acceptance-data cleanup')
