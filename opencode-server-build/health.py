import base64, json, os, urllib.request

creds = os.environ['OPENCODE_SERVER_USERNAME']+':'+os.environ['OPENCODE_SERVER_PASSWORD']
req = urllib.request.Request('http://127.0.0.1:4096/global/health',
       headers={'Authorization':'Basic '+base64.b64encode(creds.encode()).decode()})
with urllib.request.urlopen(req, timeout=3) as r:
    assert r.status == 200 and json.load(r).get('healthy') is True
