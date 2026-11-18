"""Runs against a disposable local board; deletes its data before and after the test."""
import http.cookiejar
import json
import os
import time
from pathlib import Path
import urllib.error
import urllib.request

BASE=os.getenv('BOARD_URL','http://127.0.0.1:8088')
assert BASE.startswith(('http://localhost:', 'http://127.0.0.1:')), 'Destructive smoke is local-only'
SECRETS=dict(line.strip().split('=',1) for line in Path('.secrets/deployment.env').read_text().splitlines() if '=' in line)

def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def call(c,path,data=None,status=200):
    request=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'} if data is not None else {})
    try:r=c.open(request)
    except urllib.error.HTTPError as e:r=e
    body=r.read();assert r.status==status,(path,r.status,body[:200])
    return json.loads(body) if r.headers.get('Content-Type','').startswith('application/json') else body

for attempt in range(30):
 try:
  urllib.request.urlopen(BASE+'/health',timeout=2);break
 except (urllib.error.URLError,ConnectionResetError):time.sleep(.5)

owner=client(); call(owner,'/api/access',{'kind':'owner','code':SECRETS['OWNER_CODE']})
call(owner,'/api/delete-all',{'confirm':'DELETE ALL'})
call(owner,'/api/access',{'kind':'owner','code':SECRETS['OWNER_CODE']})
a=client();b=client(); outsider=client()
call(outsider,'/api/components',status=401)
for c,name,email in [(a,'=1+2','a@example.test'),(b,'Reviewer B','b@example.test')]:
 call(c,'/api/access',{'code':SECRETS['INVITE_CODE']});call(c,'/api/onboard',{'name':name,'email':email})
rows=call(a,'/api/components')['components'];assert len(rows)==24
assert all('totals' not in c and c['vote'] is None for c in rows)
c=rows[0]
call(a,'/api/vote',[],status=400)
call(a,'/api/vote',{'component':c['id'],'version':c['version'],'choice':'maybe'},status=400)
v={'component':c['id'],'version':c['version'],'choice':'yes','reason':'Clear interaction'}
call(a,'/api/vote',v)
call(a,'/api/vote',dict(v,choice='no',reason='Too much detail'))
rows=call(a,'/api/components')['components'];assert rows[0]['totals']=={'yes':0,'no':1,'abstain':0};assert rows[0]['participation']==1
assert 'totals' not in call(b,'/api/components')['components'][0]
call(b,'/api/export/json',status=403)
call(a,'/api/vote',dict(v,version='old'),status=409)
call(a,'/api/status',{'component':c['id'],'version':c['version'],'status':'approved'},status=403)
call(owner,'/api/status',{'component':c['id'],'version':'old','status':'approved'},status=409)
call(owner,'/api/status',{'component':c['id'],'version':c['version'],'status':'approved'})
assert call(a,'/api/components')['components'][0]['status']=='approved'
backup=call(owner,'/api/export/json');assert len(backup['people'])==2 and len(backup['votes'])==1
csv=call(owner,'/api/export/csv');assert b'a@example.test' in csv and b'vote' in csv and b"'=1+2" in csv
call(owner,'/api/import',backup,status=409)
call(owner,'/api/delete-all',{'confirm':'wrong'},status=400)
call(owner,'/api/delete-all',{'confirm':'DELETE ALL'})
call(a,'/api/components',status=401)
call(owner,'/api/access',{'kind':'owner','code':SECRETS['OWNER_CODE']})
call(owner,'/api/import',backup)
assert call(owner,'/api/export/json')['votes']==backup['votes']
# Full restore with the same signing secret restores original reviewer cookies too.
assert call(a,'/api/components')['components'][0]['vote']['choice']=='no'
call(owner,'/api/delete-all',{'confirm':'DELETE ALL'})
call(owner,'/api/access',{'kind':'owner','code':SECRETS['OWNER_CODE']})
backup['statuses'][0]['version']='previous-version'
call(owner,'/api/import',backup)
assert call(owner,'/api/components')['components'][0]['status']=='review'
call(owner,'/api/delete-all',{'confirm':'DELETE ALL'})
print('PASS onboarding, access isolation, editable vote uniqueness, hidden totals, version gate, owner status, JSON/CSV, atomic restore, cookie revocation')
