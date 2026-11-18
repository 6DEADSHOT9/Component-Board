import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import time
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from flask import Flask, abort, jsonify, request, send_from_directory, session, render_template

app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ['SESSION_SECRET'], MAX_CONTENT_LENGTH=4 * 1024 * 1024,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                  SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'true') == 'true')
CATALOG = json.loads(Path('data/candidates.json').read_text())
BY_ID = {c['id']: c for c in CATALOG}
STATUSES = ('review', 'approved', 'ported', 'in the app')


def db():
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row)


def initialize():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS people (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE);
          CREATE TABLE IF NOT EXISTS votes (
          person TEXT REFERENCES people(id) ON DELETE CASCADE,
          component TEXT NOT NULL, version TEXT NOT NULL, choice TEXT NOT NULL CHECK(choice IN ('yes','no','abstain')),
          reason TEXT NOT NULL DEFAULT '', updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY(person,component,version));
          CREATE TABLE IF NOT EXISTS statuses (component TEXT PRIMARY KEY, status TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);''')
        con.execute("INSERT INTO settings VALUES ('generation', %s) ON CONFLICT DO NOTHING", (secrets.token_hex(16),))


initialize()


def authenticated(owner=False):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            with db() as con:
                generation = con.execute("SELECT value FROM settings WHERE key='generation'").fetchone()['value']
                if session.get('generation') != generation:
                    abort(401, 'Open your invite link again.')
                if owner:
                    if not session.get('owner'):
                        abort(403, 'Owner access required.')
                elif not session.get('invite'):
                    abort(401, 'Open your invite link first.')
            return fn(*args, **kwargs)
        return wrapped
    return decorate


@app.before_request
def boundary():
    if request.method != 'GET':
        # Fetch Metadata also covers browsers that omit Origin on same-origin requests.
        if request.headers.get('Sec-Fetch-Site') in ('cross-site', 'same-site'):
            abort(403, 'Open this page directly before saving.')
        origin = request.headers.get('Origin')
        if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
            abort(403, 'Cross-origin request rejected.')
        if not request.is_json:
            abort(415, 'JSON required.')
        if not isinstance(request.get_json(), dict):
            abort(400, 'A JSON object is required.')


@app.after_request
def headers(response):
    response.headers.update({'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
      'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
      'Content-Security-Policy': "default-src 'self'; img-src 'self'; media-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"})
    return response


@app.errorhandler(Exception)
def errors(error):
    from werkzeug.exceptions import HTTPException
    if isinstance(error, HTTPException):
        return jsonify(error=error.description), error.code
    app.logger.error('Request failed: %s', type(error).__name__)
    return jsonify(error='The database is unavailable. Wait a moment and try again; your last saved vote is retained.'), 503


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/health')
def health():
    with db() as con:
        con.execute('SELECT 1')
    return {'ok': True}


@app.get('/previews/<path:name>')
def preview(name):
    return send_from_directory('public/previews', name)


# shortcut: login throttles are per process, use a shared limiter if invitation traffic grows.
attempts = {}


@app.post('/api/access')
def access():
    key = request.remote_addr
    now = time.time()
    count, start = attempts.get(key, (0, now))
    if now - start > 60:
        count, start = 0, now
    if count >= 20:
        abort(429, 'Too many attempts. Wait one minute.')
    attempts[key] = (count + 1, start)
    payload = request.get_json()
    owner = payload.get('kind') == 'owner'
    code = payload.get('code', '')
    expected = os.environ['OWNER_CODE' if owner else 'INVITE_CODE']
    if not isinstance(code, str) or not hmac.compare_digest(code, expected):
        abort(403, 'This access code is not valid. Ask the owner for a current link.')
    with db() as con:
        generation = con.execute("SELECT value FROM settings WHERE key='generation'").fetchone()['value']
    person = session.get('person') if session.get('generation') == generation else None
    session.clear()
    session.update(invite=True, owner=owner, generation=generation)
    if person: session['person'] = person
    return {'ok': True}


@app.get('/api/me')
@authenticated()
def me():
    with db() as con:
        person = con.execute('SELECT name,email FROM people WHERE id=%s', (session.get('person'),)).fetchone()
    expires = os.getenv('DATABASE_EXPIRES_AT')
    warning = None
    if session.get('owner') and expires:
        expiry = date.fromisoformat(expires)
        if date.today() >= expiry - timedelta(days=7):
            warning = f'Free database expires {expiry.isoformat()}. Export all data now, then restore into a new database.'
    return {'person': person, 'owner': bool(session.get('owner')), 'expiryWarning': warning}


@app.post('/api/onboard')
@authenticated()
def onboard():
    p = request.get_json()
    name, email = p.get('name', ''), p.get('email', '')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        abort(400, 'Enter a name of 1–80 characters.')
    if not isinstance(email, str) or len(email) > 254 or '@' not in email or '\n' in email:
        abort(400, 'Enter a valid email address.')
    email = email.strip().lower()
    with db() as con:
        existing = con.execute('SELECT id FROM people WHERE email=%s', (email,)).fetchone()
        if existing and session.get('person') != existing['id']:
            abort(409, 'This email already has a review session. Use the original browser or ask the owner to delete that participant before starting again.')
        person = existing['id'] if existing else secrets.token_urlsafe(24)
        con.execute('INSERT INTO people VALUES (%s,%s,%s) ON CONFLICT(id) DO UPDATE SET name=excluded.name', (person, name.strip(), email))
    session['person'] = person
    return {'ok': True}


@app.get('/api/components')
@authenticated()
def components():
    with db() as con:
        votes = con.execute('SELECT * FROM votes').fetchall()
        statuses = {r['component']: r['status'] for r in con.execute('SELECT * FROM statuses')}
        participants = con.execute('SELECT count(*) AS n FROM people').fetchone()['n']
    result = []
    for c in CATALOG:
        current = [v for v in votes if v['component'] == c['id'] and v['version'] == c['version']]
        own = next((v for v in current if v['person'] == session.get('person')), None)
        item = dict(c, status=statuses.get(c['id'], 'review'), vote=own and {'choice': own['choice'], 'reason': own['reason']}, participation=len(current))
        if own or session.get('owner'):
            item['totals'] = {choice: sum(v['choice'] == choice for v in current) for choice in ('yes', 'no', 'abstain')}
        result.append(item)
    return {'components': result, 'participants': participants}


@app.post('/api/vote')
@authenticated()
def vote():
    if not session.get('person'):
        abort(403, 'Enter your name and email first.')
    p = request.get_json()
    c = BY_ID.get(p.get('component'))
    if not c or p.get('version') != c['version']:
        abort(409, 'Component version changed. Refresh before voting.')
    if p.get('choice') not in ('yes', 'no', 'abstain'):
        abort(400, 'Choose Yes, No or Abstain.')
    reason = p.get('reason', '')
    if not isinstance(reason, str) or len(reason) > 240 or '\n' in reason:
        abort(400, 'Keep your reason to one line, at most 240 characters.')
    with db() as con:
        con.execute('''INSERT INTO votes(person,component,version,choice,reason) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT(person,component,version) DO UPDATE SET choice=excluded.choice,reason=excluded.reason,updated_at=now()''',
        (session['person'], c['id'], c['version'], p['choice'], reason))
    return {'ok': True}


@app.post('/api/status')
@authenticated(owner=True)
def status():
    p = request.get_json()
    if p.get('component') not in BY_ID or p.get('status') not in STATUSES:
        abort(400, 'Choose a listed component and status.')
    c = BY_ID[p['component']]
    if p['status'] != 'review' and c['license']['verified'] is not True:
        abort(400, 'Verify the source licence before approval.')
    with db() as con:
        con.execute('INSERT INTO statuses VALUES (%s,%s) ON CONFLICT(component) DO UPDATE SET status=excluded.status', (c['id'], p['status']))
    return {'ok': True}


def snapshot():
    with db() as con:
        return {'format': 1, 'generation': con.execute("SELECT value FROM settings WHERE key='generation'").fetchone()['value'], 'people': con.execute('SELECT * FROM people ORDER BY id').fetchall(),
          'votes': con.execute('SELECT * FROM votes ORDER BY person,component,version').fetchall(),
          'statuses': con.execute('SELECT * FROM statuses ORDER BY component').fetchall()}


@app.get('/api/export/<kind>')
@authenticated(owner=True)
def export(kind):
    data = snapshot()
    if kind == 'json':
        response = app.response_class(json.dumps(data, default=str, indent=2), mimetype='application/json')
    elif kind == 'csv':
        out = io.StringIO()
        fields = ['record_type','person','name','email','component','version','choice','reason','updated_at','status']
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for table, record in [('people','person'),('votes','vote'),('statuses','status')]:
            for row in data[table]:
                row = dict(row)
                if table == 'people': row['person'] = row.pop('id')
                # Neutralize spreadsheet formula execution in owner-supplied and publisher text.
                writer.writerow({'record_type':record, **{k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()}})
        response = app.response_class(out.getvalue(), mimetype='text/csv')
    else:
        abort(404)
    response.headers['Content-Disposition'] = f'attachment; filename="component-board.{kind}"'
    return response


@app.post('/api/import')
@authenticated(owner=True)
def restore():
    data = request.get_json()
    if data.get('format') != 1 or not all(isinstance(data.get(k), list) for k in ('people','votes','statuses')):
        abort(400, 'Use a full JSON export from this board.')
    people, votes, statuses = data['people'], data['votes'], data['statuses']
    try:
        assert isinstance(data.get('generation'), str) and len(data['generation']) == 32
        assert len(people) <= 10000 and len(votes) <= 100000
        ids = {p['id'] for p in people}
        assert len(ids) == len(people)
        for p in people:
            assert all(isinstance(p[k],str) and 0 < len(p[k]) <= limit for k,limit in [('id',100),('name',80),('email',254)])
        for v in votes:
            assert v['person'] in ids and v['component'] in BY_ID and v['choice'] in ('yes','no','abstain')
            assert isinstance(v['version'],str) and len(v['version']) <= 128
            assert isinstance(v['reason'],str) and len(v['reason']) <= 240 and '\n' not in v['reason']
        for s in statuses:
            assert s['component'] in BY_ID and s['status'] in STATUSES
            assert s['status'] == 'review' or BY_ID[s['component']]['license']['verified']
    except (AssertionError,KeyError,TypeError):
        abort(400, 'The export has invalid or unknown records. Nothing was imported.')
    with db() as con:
        if con.execute('SELECT count(*) AS n FROM people').fetchone()['n'] or con.execute('SELECT count(*) AS n FROM statuses').fetchone()['n']:
            abort(409, 'Restore requires an empty board. Export existing data before deleting it.')
        for p in people:
            con.execute('INSERT INTO people VALUES (%s,%s,%s)', (p['id'],p['name'],p['email']))
        for v in votes:
            con.execute('INSERT INTO votes(person,component,version,choice,reason,updated_at) VALUES (%s,%s,%s,%s,%s,%s)', tuple(v[k] for k in ('person','component','version','choice','reason','updated_at')))
        for s in statuses:
            con.execute('INSERT INTO statuses VALUES (%s,%s)', (s['component'],s['status']))
        con.execute("UPDATE settings SET value=%s WHERE key='generation'", (data['generation'],))
    session['generation'] = data['generation']
    return {'ok':True}


@app.post('/api/delete-all')
@authenticated(owner=True)
def delete_all():
    if request.get_json().get('confirm') != 'DELETE ALL':
        abort(400, 'Type DELETE ALL to confirm.')
    with db() as con:
        con.execute('DELETE FROM votes; DELETE FROM people; DELETE FROM statuses')
        generation = secrets.token_hex(16)
        con.execute("UPDATE settings SET value=%s WHERE key='generation'", (generation,))
    session.clear()
    return {'ok':True}
