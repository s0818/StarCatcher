# Composes the Star Catcher promo video: cards + gameplay + captions, piped into ffmpeg.
import os, re, subprocess, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(D, 'frames')
OUT = sys.argv[1]
W, H, FPS = 1920, 1080, 30
PREVIEW = os.environ.get('PREVIEW')  # "t1,t2,..." -> write stills instead of video

FB = r'C:\Windows\Fonts\YuGothB.ttc'
FM = r'C:\Windows\Fonts\YuGothM.ttc'
MONO = r'C:\Windows\Fonts\consola.ttf'
MONOJ = r'C:\Windows\Fonts\BIZ-UDGothicR.ttc'
_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

NAVY = (13, 15, 38); CYAN = (90, 216, 255); YEL = (255, 216, 77); RED = (255, 77, 89)
WHITE = (240, 242, 250); GRAY = (160, 168, 196)

# ---------- helpers ----------
def text_img(s, f, fill, shadow=True, spacing=10, align='left'):
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    b = d.multiline_textbbox((0, 0), s, font=f, spacing=spacing, align=align)
    pad = 16
    im = Image.new('RGBA', (b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((pad - b[0] + 2, pad - b[1] + 3), s, font=f, fill=(0, 0, 0, 170), spacing=spacing, align=align)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(4)))
        dr = ImageDraw.Draw(im)
    dr.multiline_text((pad - b[0], pad - b[1]), s, font=f, fill=fill, spacing=spacing, align=align)
    return im

def panel(w, h, fill=(24, 28, 62, 235), border=(70, 80, 140, 255), r=22):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=border, width=2)
    return im

class El:
    def __init__(self, img, x, y, t0, dur=0.45, cx=False, t1=None):
        self.img, self.x, self.y, self.t0, self.dur, self.t1 = img, x, y, t0, dur, t1
        if cx: self.x = (W - img.width) // 2
    def draw(self, canvas, t):
        if t < self.t0: return
        a = min(1.0, (t - self.t0) / self.dur)
        if self.t1 is not None and t > self.t1:
            a = min(a, max(0.0, 1 - (t - self.t1) / 0.3))
        if a <= 0: return
        e = 1 - (1 - a) ** 3
        im = self.img
        if a < 1:
            im = im.copy(); al = im.getchannel('A').point(lambda v: int(v * a)); im.putalpha(al)
        canvas.alpha_composite(im, (int(self.x), int(self.y + (1 - e) * 26)))

# Starfield background (animated drift)
rng = random.Random(3)
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3.2), rng.uniform(8, 40), rng.uniform(60, 200)) for _ in range(170)]
BG_BASE = Image.new('RGBA', (W, H))
_g = np.zeros((H, W, 4), np.uint8)
yy = np.linspace(0, 1, H)[:, None]
xx = np.linspace(0, 1, W)[None, :]
glow = np.exp(-(((xx - 0.75) ** 2) / 0.08 + ((yy - 0.2) ** 2) / 0.12))
_g[..., 0] = (13 + 25 * glow).astype(np.uint8)
_g[..., 1] = (15 + 18 * glow).astype(np.uint8)
_g[..., 2] = (38 + 60 * glow).astype(np.uint8)
_g[..., 3] = 255
BG_BASE = Image.fromarray(_g, 'RGBA')

def background(t):
    im = BG_BASE.copy(); d = ImageDraw.Draw(im)
    for x, y, r, sp, al in STARS:
        yy_ = (y + sp * t) % H
        d.ellipse((x - r, yy_ - r, x + r, yy_ + r), fill=(255, 255, 255, int(al * (0.75 + 0.25 * math.sin(t * 2 + x)))))
    return im

def star_shape(size, color):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = size / 2; pts = []
    for i in range(10):
        r = c * (0.95 if i % 2 == 0 else 0.45); a = -math.pi / 2 + i * math.pi / 5
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=color)
    return im

# ---------- gameplay frames ----------
frame_files = sorted(f for f in os.listdir(FR) if f.endswith('.png'))
NF = len(frame_files)
def gframe(i):
    i = max(0, min(NF - 1, i))
    return Image.open(os.path.join(FR, frame_files[i])).convert('RGBA')

def find_gameover():
    for i in range(int(NF * 0.6), NF):
        a = np.asarray(Image.open(os.path.join(FR, frame_files[i])).convert('L').crop((560, 260, 1360, 440)))
        if (a > 200).sum() > 6000: return i
    return NF - 120
GO = find_gameover()
print('gameover frame', GO, 'of', NF, flush=True)

def caption(s, color=WHITE, icon=None):
    f = font(FB, 46)
    ti = text_img(s, f, color, shadow=False)
    iw = 0 if icon is None else icon.width + 14
    w = ti.width + iw + 60; h = 96
    im = panel(w, h, fill=(10, 12, 30, 215), border=(255, 255, 255, 60), r=48)
    if icon is not None: im.alpha_composite(icon, (34, (h - icon.height) // 2))
    im.alpha_composite(ti, (30 + iw, (h - ti.height) // 2))
    return im

def dot(size, color):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); ImageDraw.Draw(im).ellipse((0, 0, size - 1, size - 1), fill=color); return im

AI_TAG = text_img('※ 映像はAIによる自動プレイです', font(FM, 26), (200, 205, 230, 220))

def gameplay_scene(f0, caps):
    els = [El(c, 0, 90, a, t1=b, cx=True) for (c, a, b) in caps]
    def render(t):
        im = gframe(f0 + int(round(t * FPS)))
        for e in els: e.draw(im, t)
        im.alpha_composite(AI_TAG, (W - AI_TAG.width - 24, H - AI_TAG.height - 14))
        return im
    return render

def card_scene(els, extra=None):
    def render(t):
        im = background(t)
        if extra: extra(im, t)
        for e in els: e.draw(im, t)
        return im
    return render

# ---------- scenes ----------
scenes = []  # (start, dur, render)

# S1 Title
s1 = []
big = text_img('STAR CATCHER', font(FB, 150), WHITE)
s1.append(El(big, 0, 330, 0.3, dur=0.7, cx=True))
s1.append(El(star_shape(110, YEL), (W - 110) // 2, 190, 0.1, dur=0.6))
s1.append(El(text_img('AIエージェントが開発した 2Dアクションゲーム', font(FB, 56), YEL), 0, 540, 1.0, cx=True))
s1.append(El(text_img('Made with  Unity 6  ×  Claude Code', font(FM, 36), GRAY), 0, 650, 1.6, cx=True))
scenes.append((7.5, card_scene(s1)))

# S2 Concept
s2 = [El(text_img('チャットでの指示だけで、企画から公開まで', font(FB, 72), WHITE), 0, 200, 0.2, cx=True),
      El(text_img('AIがUnityを直接操作して制作', font(FM, 44), CYAN), 0, 320, 0.8, cx=True)]
steps = ['企画', 'プログラミング', 'ビルド・テスト', '公開']
cw, ch, gap = 360, 170, 70
x0 = (W - (cw * 4 + gap * 3)) // 2
for i, s in enumerate(steps):
    p = panel(cw, ch, border=(CYAN if i < 3 else YEL) + (255,))
    num = text_img(f'0{i+1}', font(FB, 34), CYAN if i < 3 else YEL, shadow=False)
    lab = text_img(s, font(FB, 48), WHITE, shadow=False)
    p.alpha_composite(num, ((cw - num.width) // 2, 14)); p.alpha_composite(lab, ((cw - lab.width) // 2, 72))
    s2.append(El(p, x0 + i * (cw + gap), 520, 1.6 + i * 0.9))
    if i < 3:
        s2.append(El(text_img('→', font(FB, 60), GRAY, shadow=False), x0 + i * (cw + gap) + cw + 2, 560, 2.0 + i * 0.9))
s2.append(El(text_img('人が行ったのは「作って」「公開して」などの指示と、GitHubへのログインだけ', font(FM, 34), GRAY), 0, 800, 5.6, cx=True))
scenes.append((9.8, card_scene(s2)))

# S3 Gameplay early
star_i = star_shape(52, YEL); bomb_i = dot(44, RED)
scenes.append((19.0, gameplay_scene(45, [
    (caption('星をキャッチで +10点', icon=star_i), 2.5, 8.0),
    (caption('赤い爆弾に当たるとライフ −1', icon=bomb_i), 8.4, 13.4),
    (caption('時間とともにスピードアップ'), 13.8, 18.6)])))

# S4 Development process (4 cards x 6s)
def step_card(n, title, desc, right):
    els = [El(text_img(f'STEP {n}', font(FB, 40), CYAN), 140, 250, 0.1),
           El(text_img(title, font(FB, 80), WHITE), 140, 310, 0.25),
           El(text_img(desc, font(FM, 36), GRAY, spacing=16), 140, 450, 0.5)]
    # progress dots
    for k in range(4):
        els.append(El(dot(22, (CYAN if k + 1 == n else (70, 80, 130)) + (255,)), 150 + k * 40, 800, 0.0, dur=0.01))
    els += right
    return els

def bubble(s, user):
    f = font(FM, 36); ti = text_img(s, f, (20, 24, 50) if user else WHITE, shadow=False, spacing=12)
    p = panel(ti.width + 50, ti.height + 34, fill=(CYAN + (255,)) if user else (40, 46, 96, 255), border=(0, 0, 0, 0), r=28)
    p.alpha_composite(ti, (25, 17)); return p

PX, PW = 900, 880
# 1 chat
b1 = bubble('簡単なゲームを作成して\nデモ版くらいでもいいので', True)
b2 = bubble('了解しました。星を拾って爆弾をよける\n2Dゲーム「Star Catcher」を作ります。', False)
lab_u = text_img('あなた', font(FM, 26), GRAY, shadow=False); lab_a = text_img('AI (Claude Code)', font(FM, 26), GRAY, shadow=False)
c1 = step_card(1, '要件ヒアリング', '作りたいゲームを\nチャットで伝えるだけ。\nAIが内容を具体化します。', [
    El(panel(PW, 560), PX, 230, 0.2),
    El(lab_u, PX + PW - lab_u.width - 40, 270, 0.6), El(b1, PX + PW - b1.width - 40, 310, 0.7),
    El(lab_a, PX + 40, 500, 1.8), El(b2, PX + 40, 540, 1.9)])

# 2 code
code = '''void Spawn(float difficulty)
{
    bool bomb = Random.value < 0.25f + elapsed / 120f;
    var sr = bomb
        ? CreateSprite("Bomb", circleSprite, red)
        : CreateSprite("Star", starSprite, yellow);
    sr.transform.position =
        new Vector3(Random.Range(-4.5f, 4.5f), 5.8f, 0);
    fallers.Add(new Faller {
        t = sr.transform, isBomb = bomb,
        speed = Random.Range(2.5f, 4f) * difficulty
    });
}'''.split('\n')
KW = {'void', 'bool', 'var', 'new', 'float'}
def code_line(s, f):
    im = Image.new('RGBA', (PW - 60, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 0
    for tok in re.findall(r'"[^"]*"|\d+(?:\.\d+)?f?|\w+|\s+|.', s):
        col = (220, 224, 240)
        if tok in KW: col = (110, 160, 255)
        elif tok.startswith('"'): col = (255, 170, 110)
        elif re.match(r'\d', tok): col = (150, 220, 140)
        elif tok in ('Random', 'Vector3', 'Faller'): col = (90, 216, 200)
        d.text((x, 0), tok, font=f, fill=col); x += d.textlength(tok, font=f)
    return im
mf = font(MONO, 25)
code_panel = panel(PW, 600, fill=(14, 16, 34, 245))
fname = text_img('GameManager.cs  —  316 行のC#をAIが生成', font(MONOJ, 24), GRAY, shadow=False)
code_panel.alpha_composite(fname, (20, 10))
code_lines = [code_line(s, mf) for s in code]
def code_extra(im, t):
    if t < 0.4: return
    # typing effect: reveal lines progressively over the card
    n = min(len(code_lines), int((t - 0.4) * 4.5) + 1)
    for k in range(n):
        im.alpha_composite(code_lines[k], (PX + 30, 230 + 70 + k * 38))
c2 = step_card(2, 'コード自動生成', 'ゲームのロジックをC#で生成。\n星・爆弾などのグラフィックも\nコードから作り出します。', [])
c2.insert(0, El(code_panel, PX, 230, 0.1, dur=0.3))

# 3 build
term = panel(PW, 300, fill=(10, 10, 16, 245))
tl = [('PS> Unity.exe -batchmode -quit', (200, 205, 220)),
      ('      -executeMethod BuildScript.BuildWindows', (200, 205, 220)),
      ('Build Finished, Result: Success.', (150, 220, 140)),
      ('BUILD RESULT: Succeeded', (150, 220, 140))]
term_lines = [text_img(s, font(MONO, 27), c, shadow=False) for s, c in tl]
thumb = gframe(700).convert('RGB').resize((464, 261)).convert('RGBA')
tb = panel(484, 281, fill=(255, 255, 255, 40), border=(255, 255, 255, 90), r=10); tb.alpha_composite(thumb, (10, 10))
ok = text_img('✓ 起動して画面を確認', font(FB, 36), (150, 220, 140))
def build_extra(im, t):
    for k, li in enumerate(term_lines):
        if t > 0.5 + k * 0.7: im.alpha_composite(li, (PX + 20, 250 + k * 56))
c3 = step_card(3, 'ビルド＆動作確認', 'Unityをコマンドラインから操作。\nWindows向けのビルドと\n起動確認まで自動で実行。', [
    El(tb, PX, 560, 3.2), El(ok, PX + 510, 660, 3.8)])
c3.insert(0, El(term, PX, 230, 0.1, dur=0.3))

# 4 publish
gp = panel(PW, 560)
gl = [(text_img('s0818 / StarCatcher', font(FB, 44), WHITE, shadow=False), 30),
      (text_img('Public   ·   Unity 6   ·   C#', font(FM, 28), GRAY, shadow=False), 100),
      (text_img('Release  v1.0.0（Windows版）', font(FB, 36), YEL, shadow=False), 190)]
for im_, y in gl: gp.alpha_composite(im_, (40, y))
row = panel(PW - 80, 90, fill=(40, 46, 96, 255), border=(90, 100, 170, 255), r=14)
row.alpha_composite(text_img('⬇  StarCatcher-Windows.zip', font(FB, 34), WHITE, shadow=False), (20, 16))
row.alpha_composite(text_img('34 MB', font(FM, 30), GRAY, shadow=False), (PW - 80 - 150, 20))
gp.alpha_composite(row, (40, 260))
gp.alpha_composite(text_img('ダウンロード → 展開 → StarCatcher.exe をダブルクリック', font(FM, 30), GRAY, shadow=False), (40, 400))
url = text_img('github.com/s0818/StarCatcher', font(FB, 40), CYAN)
c4 = step_card(4, 'GitHubで公開', 'リポジトリ作成から\n配布用リリースの公開まで。\n誰でもダウンロードして遊べます。', [
    El(gp, PX, 230, 0.2), El(url, PX + (PW - url.width) // 2, 810, 1.2)])

def multi_card(cards):
    def render(t):
        k = min(3, int(t // 6)); lt = t - k * 6
        im = background(t)
        extra = [None, code_extra, build_extra, None][k]
        for e in cards[k]:
            e.draw(im, lt)
        if extra: extra(im, lt)
        return im
    return render
scenes.append((24.0, multi_card([c1, c2, c3, c4])))

# S5 Gameplay late (game over at 16s)
s5_f0 = GO - 16 * FPS
scenes.append((20.0, gameplay_scene(s5_f0, [
    (caption('後半は難易度が大幅アップ'), 1.0, 7.5),
    (caption('スコアとハイスコアを記録', color=YEL), 16.6, 19.7)])))

# S6 Closing
s6 = [El(text_img('AI × ゲーム開発', font(FB, 110), WHITE), 0, 150, 0.2, dur=0.7, cx=True)]
pts = ['チャットで指示するだけ', 'コード・ビルド・公開を自動化', 'アイデアをすぐにプロトタイプへ']
for i, s in enumerate(pts):
    row_ = Image.new('RGBA', (900, 80), (0, 0, 0, 0))
    row_.alpha_composite(star_shape(44, YEL), (0, 18))
    row_.alpha_composite(text_img(s, font(FB, 50), WHITE, shadow=False), (64, 0))
    s6.append(El(row_, 560, 360 + i * 100, 1.0 + i * 0.6))
s6.append(El(text_img('Unity 6   /   C#   /   Claude Code   /   GitHub', font(FM, 36), GRAY), 0, 720, 3.0, cx=True))
s6.append(El(text_img('github.com/s0818/StarCatcher', font(FB, 52), CYAN), 0, 810, 3.6, cx=True))
scenes.append((11.5, card_scene(s6)))

# ---------- timeline ----------
timeline = []; acc = 0.0
for dur, r in scenes:
    timeline.append((acc, dur, r)); acc += dur
TOTAL = acc
print('total', TOTAL, 'scene starts', [round(s, 2) for s, _, _ in timeline], 'S5 gameover at', timeline[4][0] + 16, flush=True)

def frame_at(T):
    for s, dur, r in timeline:
        if T < s + dur or (s, dur, r) == timeline[-1]:
            lt = T - s; im = r(lt).convert('RGB')
            fade = min(1.0, lt / 0.3, (dur - lt) / 0.3)
            if s == 0: fade = min(1.0, lt / 0.8, (dur - lt) / 0.3)
            if fade < 1: im = Image.blend(Image.new('RGB', im.size), im, max(0, fade))
            return im

if PREVIEW:
    for k, tt in enumerate(PREVIEW.split(',')):
        frame_at(float(tt)).save(os.path.join(D, f'preview_{k}.png'))
    sys.exit(0)

# ---------- audio + encode ----------
nar_at = {'n01': 0.7, 'n02': 7.9, 'n03': 18.0, 'n04': 25.6, 'n05': 36.8, 'n06': 42.6, 'n07': 48.6,
          'n08': 54.6, 'n09': 61.3, 'n10': timeline[4][0] + 16.5, 'n11': timeline[5][0] + 1.0}
args = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-i', os.path.join(D, 'bgm.wav')]
for k in nar_at: args += ['-i', os.path.join(D, k + '.wav')]
fc = []
for i, (k, at) in enumerate(nar_at.items()):
    ms = int(at * 1000)
    fc.append(f'[{i+2}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume=1.6[n{i}]')
fc.append(''.join(f'[n{i}]' for i in range(len(nar_at))) + f'amix=inputs={len(nar_at)}:normalize=0,asplit=2[nar1][nar2]')
fc.append('[1:a]volume=0.55[bg]')
fc.append('[bg][nar2]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=500[duck]')
fc.append(f'[duck][nar1]amix=inputs=2:normalize=0,alimiter=limit=0.95,atrim=0:{TOTAL}[aout]')
args += ['-filter_complex', ';'.join(fc), '-map', '0:v', '-map', '[aout]',
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-t', f'{TOTAL}', OUT]
p = subprocess.Popen(args, stdin=subprocess.PIPE)
N = int(round(TOTAL * FPS))
for fi in range(N):
    p.stdin.write(frame_at(fi / FPS).tobytes())
    if fi % 300 == 0: print('frame', fi, '/', N, flush=True)
p.stdin.close(); p.wait()
print('done', p.returncode, OUT)
