# Usage: meshy_rig.py <input_task_id> <outdir> [height_meters]
# Auto-rigs a humanoid Meshy model and downloads the rigged character + basic walk/run animations.
import os, sys, time, json
from ai_assets import req, ENV, download

task_id, outdir = sys.argv[1], sys.argv[2]
height = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
os.makedirs(outdir, exist_ok=True)
H = {'Authorization': 'Bearer ' + ENV['MESHY_API_KEY']}
API = 'https://api.meshy.ai/openapi/v1/rigging'

s, r = req('POST', API, H, {'input_task_id': task_id, 'height_meters': height})
print('create', s, r, flush=True)
if s not in (200, 202): sys.exit(1)
rid = r['result']
while True:
    s, t = req('GET', f'{API}/{rid}', H)
    if s != 200: print('poll error', s, t); sys.exit(1)
    print(' ', t.get('status'), t.get('progress'), flush=True)
    if t.get('status') in ('SUCCEEDED', 'FAILED', 'CANCELED'): break
    time.sleep(8)
if t['status'] != 'SUCCEEDED':
    print(json.dumps(t, ensure_ascii=False)[:800]); sys.exit(1)
res = t['result']
files = {'player_rigged.fbx': res.get('rigged_character_fbx_url'), 'player_rigged.glb': res.get('rigged_character_glb_url')}
ba = res.get('basic_animations') or {}
files.update({'player_walk.fbx': ba.get('walking_fbx_url'), 'player_run.fbx': ba.get('running_fbx_url'),
              'player_walk.glb': ba.get('walking_glb_url'), 'player_run.glb': ba.get('running_glb_url')})
for name, url in files.items():
    if url:
        download(url, os.path.join(outdir, name)); print('downloaded', name)
print('credits used', t.get('consumed_credits'))
s, b = req('GET', 'https://api.meshy.ai/openapi/v1/balance', H); print('balance', b)
