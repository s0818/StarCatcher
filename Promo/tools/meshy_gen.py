# Usage: meshy_gen.py <name> <outdir> [refine] "<prompt>"
# Creates a Meshy text-to-3D preview (optionally refines it with textures) and downloads the results.
import os, sys, time, json
from ai_assets import meshy, download

name, outdir, *rest = sys.argv[1:]
refine = rest[0] == 'refine'
prompt = rest[-1]
os.makedirs(outdir, exist_ok=True)

def wait(task_id):
    while True:
        s, t = meshy('GET', f'/openapi/v2/text-to-3d/{task_id}')
        if s != 200: print('poll error', s, t); sys.exit(1)
        st = t.get('status')
        print(' ', st, t.get('progress'), flush=True)
        if st in ('SUCCEEDED', 'FAILED', 'CANCELED', 'EXPIRED'): return t
        time.sleep(10)

s, r = meshy('POST', '/openapi/v2/text-to-3d', {'mode': 'preview', 'prompt': prompt, 'should_remesh': True, 'topology': 'triangle', 'target_polycount': 8000})
print('preview create', s, r, flush=True)
if s not in (200, 202): sys.exit(1)
t = wait(r['result'])
if t['status'] != 'SUCCEEDED': print(json.dumps(t)[:800]); sys.exit(1)

if refine:
    s, r = meshy('POST', '/openapi/v2/text-to-3d', {'mode': 'refine', 'preview_task_id': t['id'], 'enable_pbr': False})
    print('refine create', s, r, flush=True)
    if s not in (200, 202): sys.exit(1)
    t = wait(r['result'])
    if t['status'] != 'SUCCEEDED': print(json.dumps(t)[:800]); sys.exit(1)

urls = t.get('model_urls', {})
for fmt in ('glb', 'fbx'):
    if urls.get(fmt):
        download(urls[fmt], os.path.join(outdir, f'{name}.{fmt}'))
if t.get('thumbnail_url'):
    download(t['thumbnail_url'], os.path.join(outdir, f'{name}_thumb.png'))
print('done', name, list(urls.keys()))
print('balance', meshy('GET', '/openapi/v1/balance')[1])
