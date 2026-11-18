"""Verify existing local review data survives restarting both containers."""
import http.cookiejar
import json
from pathlib import Path
import subprocess
import time
import urllib.request
secrets=dict(line.split('=',1) for line in Path('.secrets/deployment.env').read_text().splitlines() if '=' in line)
c=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def call(path,data=None):
 with c.open(urllib.request.Request('http://127.0.0.1:8088'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'} if data is not None else {}),timeout=5) as r:return json.load(r)
call('/api/access',{'kind':'owner','code':secrets['OWNER_CODE']})
before=call('/api/export/json')
assert before['people'] and before['votes'],'Create a local browser smoke vote first'
subprocess.run(['docker','compose','restart','db','web'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for attempt in range(30):
 try:
  call('/health');break
 except Exception:time.sleep(1)
after=call('/api/export/json');assert before==after
print('PASS Postgres participant/vote/status persistence and session continuity through web and database restart')
