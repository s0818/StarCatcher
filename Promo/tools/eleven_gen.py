# Generates sound effects, BGM (if the plan allows) and Japanese narration with ElevenLabs.
import os, sys
from ai_assets import eleven

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
AUDIO = os.path.join(ROOT, 'Assets', 'Resources', 'Audio')
NAR = os.path.join(ROOT, 'Promo', 'narration')
os.makedirs(AUDIO, exist_ok=True); os.makedirs(NAR, exist_ok=True)
VOICE = 'XrExE9yKIg1WjnnlVkGX'  # Matilda - professional, informative

def save(path, s, data):
    if s == 200:
        open(path, 'wb').write(data); print('ok', os.path.basename(path), len(data))
    else:
        print('FAIL', os.path.basename(path), s, data)

what = sys.argv[1]
if what == 'sfx':
    sfx = {
        'catch': ('bright sparkly magical chime pickup sound, cute casual mobile game, short', 0.6),
        'hit': ('cartoon bomb explosion pop with a little crunch, casual game, short', 0.9),
        'gameover': ('short descending playful game over jingle, cute casual game', 2.0),
    }
    for name, (text, dur) in sfx.items():
        s, d = eleven('POST', '/v1/sound-generation', {'text': text, 'duration_seconds': dur, 'prompt_influence': 0.5}, raw=True)
        save(os.path.join(AUDIO, name + '.mp3'), s, d)
elif what == 'music':
    s, d = eleven('POST', '/v1/music', {'prompt': 'upbeat bright synth-pop instrumental for a cute casual space arcade game, catchy, loopable, no vocals', 'music_length_ms': 60000}, raw=True)
    save(os.path.join(NAR, 'bgm.mp3'), s, d)
elif what == 'narration':
    for line in open(sys.argv[2], encoding='utf-8'):
        if '|' not in line: continue
        key, text = line.strip().split('|', 1)
        s, d = eleven('POST', f'/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128',
                      {'text': text, 'model_id': 'eleven_multilingual_v2',
                       'voice_settings': {'stability': 0.55, 'similarity_boost': 0.75, 'style': 0.15}}, raw=True)
        save(os.path.join(NAR, key + '.mp3'), s, d)
s, u = eleven('GET', '/v1/user/subscription')
if s == 200: print('characters used', u['character_count'], '/', u['character_limit'])
