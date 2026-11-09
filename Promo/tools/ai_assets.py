# Helper for calling Meshy (3D) and ElevenLabs (audio) APIs. Keys are read from ../../.env
# and never printed.
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def load_env():
    env = {}
    with open(os.path.join(ROOT, '.env'), encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

ENV = load_env()

def req(method, url, headers, body=None, raw=False, timeout=120):
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers = dict(headers, **{'Content-Type': 'application/json'})
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            content = resp.read()
            return resp.status, (content if raw else json.loads(content or b'{}'))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')[:800]

def meshy(method, path, body=None):
    return req(method, 'https://api.meshy.ai' + path, {'Authorization': 'Bearer ' + ENV['MESHY_API_KEY']}, body)

def eleven(method, path, body=None, raw=False):
    return req(method, 'https://api.elevenlabs.io' + path, {'xi-api-key': ENV['ELEVENLABS_API_KEY']}, body, raw=raw)

def download(url, path):
    urllib.request.urlretrieve(url, path)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'status':
        print('meshy balance:', meshy('GET', '/openapi/v1/balance'))
        s, u = eleven('GET', '/v1/user/subscription')
        if s == 200:
            print('elevenlabs:', {k: u.get(k) for k in ('tier', 'character_count', 'character_limit', 'status')})
        else:
            print('elevenlabs:', s, u)
