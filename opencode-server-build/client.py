import os, json, base64, urllib.request, urllib.error, time

base = 'http://opencode-server:4096'
creds = os.environ['OPENCODE_SERVER_USERNAME']+':'+os.environ['OPENCODE_SERVER_PASSWORD']
auth = 'Basic '+base64.b64encode(creds.encode()).decode()

def api(path, data=None):
    req = urllib.request.Request(base+path, data=None if data is None else json.dumps(data).encode(),
          headers={'Authorization':auth,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'{path} returned HTTP {exc.code}: {detail[:2000]}') from None

assert api('/global/health')['healthy']
try:
    urllib.request.urlopen(base+'/session', timeout=10)
    raise RuntimeError('Unauthenticated session access unexpectedly succeeded')
except urllib.error.HTTPError as exc:
    assert exc.code == 401, exc.code

marker = 'opencode-smoke-'+str(int(time.time()))
session = api('/session', {'title':marker})
print(json.dumps({'session_id':session['id'],'marker':marker}), flush=True)
response = api('/session/'+session['id']+'/message',
               {'parts':[{'type':'text','text':'Do not use tools. Reply exactly: '+marker}]})
reply = '\n'.join(p.get('text','') for p in response.get('parts',[]) if p.get('type')=='text')
assert marker in reply, 'Expected model response marker was not returned'
print(json.dumps({'session_id':session['id'],'marker':marker,'reply':reply}), flush=True)
