"""Run inside the web container with its normal local environment."""
import os
from datetime import date,timedelta
from app import app
with app.test_client() as client:
 assert client.post('/api/access',json={'kind':'owner','code':os.environ['OWNER_CODE']}).status_code==200
 os.environ['DATABASE_EXPIRES_AT']=(date.today()+timedelta(days=6)).isoformat()
 assert os.environ['DATABASE_EXPIRES_AT'] in client.get('/api/me').json['expiryWarning']
 os.environ['DATABASE_EXPIRES_AT']=(date.today()+timedelta(days=30)).isoformat()
 assert client.get('/api/me').json['expiryWarning'] is None
print('PASS owner expiry reminder at day 23')
