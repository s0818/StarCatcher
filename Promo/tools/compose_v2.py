# Star Catcher promo video v2 (business audience, "what AI makes possible").
# Usage: compose_v2.py <work_dir> <out.mp4>    (PREVIEW="t1,t2" env renders stills only)
import os, re, csv, glob, subprocess, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WORK = sys.argv[1]
OUT = sys.argv[2]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PROMO = os.path.join(ROOT, 'Promo')
W, H, FPS = 1920, 1080, 30
PREVIEW = os.environ.get('PREVIEW')

FB = r'C:\Windows\Fonts\YuGothB.ttc'
FM = r'C:\Windows\Fonts\YuGothM.ttc'
MONO = r'C:\Windows\Fonts\consola.ttf'
_fc = {}
def font(path, size):
    if (path, size) not in _fc: _fc[(path, size)] = ImageFont.truetype(path, size)
    return _fc[(path, size)]

CYAN = (90, 216, 255); YEL = (255, 216, 77); RED = (255, 77, 89); GREEN = (120, 230, 150)
WHITE = (240, 242, 250); GRAY = (160, 168, 196); PINK = (255, 120, 190)

# ---------- helpers ----------
def text_img(s, f, fill, shadow=True, spacing=10, align='left'):
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    b = d.multiline_textbbox((0, 0), s, font=f, spacing=spacing, align=align)
    pad = 16
    im = Image.new('RGBA', (b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((pad - b[0] + 2, pad - b[1] + 3), s, font=f, fill=(0, 0, 0, 180), spacing=spacing, align=align)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(4)))
    ImageDraw.Draw(im).multiline_text((pad - b[0], pad - b[1]), s, font=f, fill=fill, spacing=spacing, align=align)
    return im

def panel(w, h, fill=(24, 28, 62, 235), border=(70, 80, 140, 255), r=22, width=2):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=border, width=width)
    return im

def ease(a): return 1 - (1 - max(0, min(1, a))) ** 3

class El:
    def __init__(self, img, x, y, t0, dur=0.45, cx=False, t1=None, slide=26, pop=False):
        self.img, self.x, self.y, self.t0, self.dur, self.t1, self.slide, self.pop = img, x, y, t0, dur, t1, slide, pop
        if cx: self.x = (W - img.width) // 2
    def draw(self, canvas, t):
        if t < self.t0: return
        a = min(1.0, (t - self.t0) / self.dur)
        if self.t1 is not None and t > self.t1: a = min(a, max(0.0, 1 - (t - self.t1) / 0.3))
        if a <= 0: return
        e = ease(a); im = self.img; x, y = self.x, self.y
        if self.pop and e < 1:
            s = 0.6 + 0.4 * e + 0.08 * math.sin(e * math.pi)
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
            x += (self.img.width - im.width) / 2; y += (self.img.height - im.height) / 2
        if a < 1:
            im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
        canvas.alpha_composite(im, (int(x), int(y + (0 if self.pop else (1 - e) * self.slide))))

rng = random.Random(3)
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3.2), rng.uniform(8, 40), rng.uniform(60, 200)) for _ in range(170)]
_g = np.zeros((H, W, 4), np.uint8)
yy = np.linspace(0, 1, H)[:, None]; xx = np.linspace(0, 1, W)[None, :]
glow = np.exp(-(((xx - 0.75) ** 2) / 0.08 + ((yy - 0.2) ** 2) / 0.12))
_g[..., 0] = (13 + 25 * glow); _g[..., 1] = (15 + 18 * glow); _g[..., 2] = (38 + 60 * glow); _g[..., 3] = 255
BG_BASE = Image.fromarray(_g, 'RGBA')

def background(t):
    im = BG_BASE.copy(); d = ImageDraw.Draw(im)
    for x, y, r, sp, al in STARS:
        y2 = (y + sp * t) % H
        d.ellipse((x - r, y2 - r, x + r, y2 + r), fill=(255, 255, 255, int(al * (0.75 + 0.25 * math.sin(t * 2 + x)))))
    return im

def star_shape(size, color):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); c = size / 2
    pts = [(c + c * (0.95 if i % 2 == 0 else 0.45) * math.cos(-math.pi / 2 + i * math.pi / 5),
            c + c * (0.95 if i % 2 == 0 else 0.45) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
    ImageDraw.Draw(im).polygon(pts, fill=color); return im

def dot(size, color):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); ImageDraw.Draw(im).ellipse((0, 0, size - 1, size - 1), fill=color); return im

def caption(s, color=WHITE):
    ti = text_img(s, font(FB, 46), color, shadow=False)
    im = panel(ti.width + 60, 96, fill=(10, 12, 30, 215), border=(255, 255, 255, 60), r=48)
    im.alpha_composite(ti, (30, (96 - ti.height) // 2)); return im

def section_tag(n, title):
    tag = panel(110, 110, fill=(255, 216, 77, 255), border=(0, 0, 0, 0), r=55)
    num = text_img(str(n), font(FB, 64), (20, 20, 40), shadow=False)
    tag.alpha_composite(num, ((110 - num.width) // 2, (110 - num.height) // 2 - 4))
    tt = text_img(title, font(FB, 64), WHITE)
    im = Image.new('RGBA', (140 + tt.width, 120), (0, 0, 0, 0))
    im.alpha_composite(tag, (0, 5)); im.alpha_composite(tt, (130, (120 - tt.height) // 2))
    return im

# ---------- sources ----------
def frame_dir(name):
    d = os.path.join(WORK, name); fs = sorted(f for f in os.listdir(d) if f.endswith('.png')); return d, fs
G3_DIR, G3 = frame_dir('frames3d')
def g3(i): i = max(0, min(len(G3) - 1, i)); return Image.open(os.path.join(G3_DIR, G3[i])).convert('RGBA')
THEMES = [frame_dir(f'theme{t}') for t in range(4)]
def theme_frame(t, i):
    d, fs = THEMES[t]; i = max(0, min(len(fs) - 1, i)); return Image.open(os.path.join(d, fs[i])).convert('RGBA')

MESHY = os.path.join(PROMO, 'meshy')
def thumb(name, size):
    im = Image.open(os.path.join(MESHY, f'{name}_thumb.png')).convert('RGBA').resize((size, size), Image.LANCZOS)
    p = panel(size + 20, size + 20, fill=(0, 0, 0, 255), border=(90, 100, 170, 255), r=18)
    p.alpha_composite(im, (10, 10)); return p

AI_TAG = text_img('※ 映像はAIによる自動プレイです', font(FM, 26), (200, 205, 230, 220))

def card_scene(els, extra=None, bg=None):
    def render(t):
        im = (bg(t) if bg else background(t))
        if extra: extra(im, t)
        for e in els: e.draw(im, t)
        return im
    return render

scenes = []

# S1 Title over blurred gameplay
title_bg = g3(700).filter(ImageFilter.GaussianBlur(6))
title_bg = Image.blend(title_bg.convert('RGB'), Image.new('RGB', (W, H), (8, 10, 30)), 0.55).convert('RGBA')
s1 = [El(star_shape(110, YEL), (W - 110) // 2, 150, 0.1, pop=True),
      El(text_img('STAR CATCHER', font(FB, 150), WHITE), 0, 280, 0.3, dur=0.7, cx=True),
      El(text_img('AIエージェントと共に開発した カジュアルアクションゲーム', font(FB, 54), YEL), 0, 490, 1.0, cx=True)]
for i, n in enumerate(('player', 'good', 'bad')):
    s1.append(El(thumb(n, 200), 600 + i * 250, 640, 1.6 + i * 0.25, pop=True))
scenes.append((6.5, card_scene(s1, bg=lambda t: title_bg.copy())))

# S2 Business request
def bubble(s, user, size=36):
    ti = text_img(s, font(FM, size), (20, 24, 50) if user else WHITE, shadow=False, spacing=12)
    p = panel(ti.width + 56, ti.height + 36, fill=(CYAN + (255,)) if user else (40, 46, 96, 255), border=(0, 0, 0, 0), r=28)
    p.alpha_composite(ti, (28, 18)); return p
req = bubble('新規IP検証用に、短時間で遊べるカジュアルゲームの\nプロトタイプを作成してください。\n社内レビューに使えるデモ版で構いません。', True)
rep = bubble('承知しました。「星を集め、爆弾をかわす」2Dアクションで\n企画・実装・テスト・配布まで一括で進めます。', False)
lab_u = text_img('依頼者', font(FM, 28), GRAY, shadow=False); lab_a = text_img('AI (Claude Code)', font(FM, 28), GRAY, shadow=False)
s2 = [El(text_img('依頼は、チャットでのひと言だけ', font(FB, 64), WHITE), 0, 90, 0.2, cx=True),
      El(lab_u, W - 200 - lab_u.width, 230, 0.7), El(req, W - 200 - req.width, 270, 0.8),
      El(lab_a, 200, 520, 2.6), El(rep, 200, 560, 2.7)]
chips = ['企画', '実装', 'テスト', '配布']
for i, c in enumerate(chips):
    ch = panel(220, 80, fill=(24, 28, 62, 240), border=CYAN + (255,), r=40)
    tx = text_img(c, font(FB, 38), WHITE, shadow=False); ch.alpha_composite(tx, ((220 - tx.width) // 2, (80 - tx.height) // 2))
    s2.append(El(ch, 420 + i * 280, 800, 4.6 + i * 0.35, pop=True))
s2.append(El(text_img('プロジェクト作成から一般公開まで  約25分', font(FB, 44), YEL), 0, 920, 6.4, cx=True))
scenes.append((11.5, card_scene(s2)))

# S3 Gameplay (3D)
def gameplay_scene(f0, caps, src=g3):
    els = [El(c, 0, 90, a, t1=b, cx=True) for (c, a, b) in caps]
    def render(t):
        im = src(f0 + int(round(t * FPS)))
        for e in els: e.draw(im, t)
        im.alpha_composite(AI_TAG, (W - AI_TAG.width - 24, H - AI_TAG.height - 14))
        return im
    return render
scenes.append((9.5, gameplay_scene(120, [(caption('星をキャッチで +10点', YEL), 0.6, 4.6), (caption('爆弾をかわせ（ライフ3）', (255, 150, 160)), 5.0, 9.3)])))

# S4 Intro to AI showcase
s4 = [El(text_img('AIだからできる', font(FB, 120), YEL), 0, 330, 0.15, dur=0.6, cx=True),
      El(text_img('4 つのこと', font(FB, 96), WHITE), 0, 500, 0.6, cx=True)]
scenes.append((4.5, card_scene(s4)))

# S5 (1) Text to 3D
prompt = '"a cute small round light-blue robot character\n holding an open basket, chibi cartoon game hero"'
pp = panel(1500, 150, fill=(14, 16, 34, 245))
pp.alpha_composite(text_img('PROMPT', font(FB, 26), CYAN, shadow=False), (24, 10))
prompt_lines = prompt.split('\n')
pp_el = El(pp, 210, 230, 0.6)
def s5_extra(im, t):
    pp_el.draw(im, t)
    # typewriter effect for the prompt
    if t < 0.9: return
    shown = int((t - 0.9) * 45); left = shown
    for k, ln in enumerate(prompt_lines):
        part = ln[:max(0, left)]; left -= len(ln)
        if part: im.alpha_composite(text_img(part, font(MONO, 36), WHITE, shadow=False), (230, 268 + k * 46))
s5 = [El(section_tag(1, 'テキストから3Dモデルを生成'), 120, 70, 0.1)]
for i, (n, lab) in enumerate((('player', 'キャラクター'), ('good', 'アイテム（星）'), ('bad', '障害物（爆弾）'))):
    s5.append(El(thumb(n, 330), 330 + i * 440, 440, 3.0 + i * 0.4, pop=True))
    lt = text_img(lab, font(FB, 36), WHITE); s5.append(El(lt, 330 + i * 440 + (350 - lt.width) // 2, 800, 3.3 + i * 0.4))
s5.append(El(text_img('Meshy で生成  ·  1体 約2分  ·  無料枠の範囲内', font(FM, 34), GRAY), 0, 900, 4.8, cx=True))
scenes.append((8.5, card_scene(s5, extra=s5_extra)))

# S6 (2) Four themes at once
TN = ['SPACE', 'OCEAN', 'SAKURA', 'NEON']
tlabels = [text_img(n, font(FB, 34), WHITE) for n in TN]
s6_title = section_tag(2, '1つの指示で、4つの世界観')
def s6_render(t):
    im = background(t)
    for k in range(4):
        a = ease((t - 0.6 - k * 0.25) / 0.5)
        if a <= 0: continue
        fr = theme_frame(k, 110 + int(t * FPS)).resize((800, 450))
        x = 150 + (k % 2) * 830 + 20; y = 205 + (k // 2) * 430
        if a < 1:
            fr = fr.copy(); fr.putalpha(int(255 * a))
        im.alpha_composite(fr, (x, int(y + (1 - a) * 30)))
        im.alpha_composite(tlabels[k], (x + 12, y + 8))
    El(s6_title, 120, 60, 0.0).draw(im, t)
    return im
scenes.append((7.5, s6_render))

# S7 (3) 1,000 automated playtests -> difficulty tuning
rates, med = [], []
for path in sorted(glob.glob(os.path.join(PROMO, 'data', 'bomb_*.csv'))):
    rows = list(csv.DictReader(open(path)))
    s = sorted(float(r['survival_s']) for r in rows)
    rates.append(float(rows[0]['bomb'])); med.append(s[len(s) // 2])
CH_X, CH_Y, CH_W, CH_H = 160, 300, 1000, 560
def s7_extra(im, t):
    d = ImageDraw.Draw(im)
    p = panel(CH_W + 80, CH_H + 140, fill=(20, 24, 54, 230)); im.alpha_composite(p, (CH_X - 40, CH_Y - 60))
    im.alpha_composite(text_img('爆弾の出現率と、1プレイの生存時間（中央値）', font(FM, 30), GRAY, shadow=False), (CH_X - 10, CH_Y - 55))
    base = CH_Y + CH_H - 40; maxv = 40.0
    for v in (10, 20, 30, 40):
        yv = base - (v / maxv) * (CH_H - 120)
        d.line((CH_X, yv, CH_X + CH_W - 40, yv), fill=(70, 80, 130, 255), width=1)
        d.text((CH_X + CH_W - 30, yv - 14), f'{v}秒', font=font(FM, 22), fill=GRAY)
    if 30:
        y30 = base - (30 / maxv) * (CH_H - 120)
        d.line((CH_X, y30, CH_X + CH_W - 40, y30), fill=YEL + (200,), width=3)
        d.text((CH_X + 6, y30 - 34), '目標：30秒以上', font=font(FB, 24), fill=YEL)
    bw = 120
    for k, (r, m) in enumerate(zip(rates, med)):
        a = ease((t - 0.8 - k * 0.25) / 0.6)
        x = CH_X + 60 + k * 175; hgt = a * (m / maxv) * (CH_H - 120)
        chosen = abs(r - 0.15) < 1e-6
        col = YEL if (chosen and t > 3.2) else CYAN
        d.rounded_rectangle((x, base - hgt, x + bw, base), 8, fill=col + (255,))
        if a > 0.9: d.text((x + bw / 2, base - hgt - 34), f'{m:.1f}', font=font(FB, 28), fill=WHITE, anchor='mt')
        d.text((x + bw / 2, base + 12), f'{int(round(r * 100))}%', font=font(FB, 30), fill=YEL if chosen and t > 3.2 else WHITE, anchor='mt')
        if chosen and t > 3.2:
            d.text((x + bw / 2, base + 52), '採用', font=font(FB, 28), fill=YEL, anchor='mt')
stat1 = text_img('1,000 回', font(FB, 96), YEL)
stat2 = text_img('自動テストプレイ', font(FB, 40), WHITE)
stat3 = text_img('人が遊ぶと 約8.6時間分', font(FB, 38), WHITE)
stat4 = text_img('→ 実行時間 66秒', font(FB, 48), GREEN)
s7 = [El(section_tag(3, 'AIが1,000回テストして難易度を調整'), 120, 60, 0.1),
      El(stat1, 1300, 300, 0.6), El(stat2, 1310, 420, 0.9), El(stat3, 1310, 540, 1.6), El(stat4, 1310, 620, 2.2),
      El(text_img('爆弾の出現率を\n25% → 15% に調整', font(FB, 40), YEL, spacing=14), 1300, 740, 3.4)]
scenes.append((9.0, card_scene(s7, extra=s7_extra)))

# S8 (4) AI audio
def s8_extra(im, t):
    d = ImageDraw.Draw(im); cx, cy = W // 2, 560
    for k in range(64):
        x = cx - 64 * 13 + k * 26
        amp = (math.sin(t * 6 + k * 0.45) * 0.5 + 0.5) * (math.sin(t * 2.3 + k * 0.17) * 0.5 + 0.5)
        hh = 20 + amp * 220 * ease((t - 0.4) / 0.8)
        col = CYAN if k < 32 else PINK
        d.rounded_rectangle((x, cy - hh / 2, x + 14, cy + hh / 2), 7, fill=col + (230,))
s8 = [El(section_tag(4, '効果音とナレーションもAIが生成'), 120, 60, 0.1),
      El(text_img('効果音 3種', font(FB, 44), CYAN), 380, 760, 1.0), El(text_img('ナレーション 10本', font(FB, 44), PINK), 1100, 760, 1.4),
      El(text_img('ElevenLabs で生成  ·  無料枠の範囲内', font(FM, 34), GRAY), 0, 860, 2.0, cx=True),
      El(caption('いまお聞きの声も、AIの音声です', YEL), 0, 220, 4.2, cx=True)]
scenes.append((9.0, card_scene(s8, extra=s8_extra)))

# S9 Real timeline
steps = [('16:49', 'Unityプロジェクト作成'), ('16:53', '遊べるデモ版が完成'), ('17:12', 'GitHubで一般公開'), ('その後', '3D・音声・テストを追加')]
s9 = [El(text_img('実際の開発タイムライン', font(FB, 72), WHITE), 0, 110, 0.2, cx=True),
      El(text_img('コードの作成・ビルド・テスト・配布まで、AIが自動で実行', font(FM, 38), CYAN), 0, 230, 0.7, cx=True)]
def s9_extra(im, t):
    d = ImageDraw.Draw(im); y = 560; x0, x1 = 260, W - 260
    prog = ease((t - 1.0) / 2.5)
    d.line((x0, y, x0 + (x1 - x0) * prog, y), fill=CYAN + (255,), width=6)
for i, (tm, lab) in enumerate(steps):
    x = 260 + i * (W - 520) / 3
    s9.append(El(dot(46, (YEL if i < 3 else PINK) + (255,)), x - 23, 537, 1.0 + i * 0.8, pop=True))
    tt = text_img(tm, font(FB, 52), YEL if i < 3 else PINK); s9.append(El(tt, x - tt.width / 2, 420, 1.1 + i * 0.8))
    lt = text_img(lab, font(FB, 34), WHITE); s9.append(El(lt, x - lt.width / 2, 620, 1.2 + i * 0.8))
s9.append(El(text_img('作成から最初の動作版まで 約5分', font(FB, 52), GREEN), 0, 790, 4.4, cx=True))
scenes.append((9.0, card_scene(s9, extra=s9_extra)))

# S10 Closing over dimmed gameplay
def s10_bg_factory():
    def bg(t):
        fr = g3(900 + int(t * FPS)).convert('RGB')
        return Image.blend(fr, Image.new('RGB', (W, H), (8, 10, 30)), 0.62).convert('RGBA')
    return bg
s10 = [El(text_img('アイデアを、その日のうちに遊べる形へ。', font(FB, 78), WHITE), 0, 250, 0.3, dur=0.7, cx=True),
       El(text_img('AI × ゲーム開発', font(FB, 60), YEL), 0, 400, 1.2, cx=True),
       El(text_img('Unity 6  /  Claude Code  /  Meshy  /  ElevenLabs', font(FM, 40), WHITE), 0, 560, 2.2, cx=True),
       El(text_img('github.com/s0818/StarCatcher', font(FB, 56), CYAN), 0, 660, 2.8, cx=True),
       El(text_img('3Dモデル: Meshy で生成 (CC BY 4.0)  ·  音声: ElevenLabs で生成  ·  BGM: プログラムで自動作曲', font(FM, 26), GRAY), 0, 960, 3.4, cx=True)]
scenes.append((13.0, card_scene(s10, bg=s10_bg_factory())))

# ---------- timeline ----------
timeline = []; acc = 0.0
for dur, r in scenes: timeline.append((acc, dur, r)); acc += dur
TOTAL = acc
starts = [round(s, 2) for s, _, _ in timeline]
print('total', TOTAL, 'starts', starts, flush=True)

def frame_at(T):
    for idx, (s, dur, r) in enumerate(timeline):
        if T < s + dur or idx == len(timeline) - 1:
            lt = T - s; im = r(lt).convert('RGB')
            fade = min(1.0, lt / 0.25, (dur - lt) / 0.25)
            if idx == 0: fade = min(1.0, lt / 0.8, (dur - lt) / 0.25)
            if idx == len(timeline) - 1: fade = min(1.0, lt / 0.25, (dur - lt) / 1.5)
            if fade < 1: im = Image.blend(Image.new('RGB', im.size), im, max(0, fade))
            return im

if PREVIEW:
    for k, tt in enumerate(PREVIEW.split(',')):
        frame_at(float(tt)).save(os.path.join(WORK, f'pv_{k}.png'))
    sys.exit(0)

# ---------- audio ----------
S = dict(zip(['title', 'req', 'play', 'intro', 'gen3d', 'themes', 'test', 'audio', 'timeline', 'close'], starts))
NAR = os.path.join(PROMO, 'narration')
nar_at = {'n01': S['title'] + 0.8, 'n02': S['req'] + 0.6, 'n03': S['play'] + 0.6, 'n04': S['intro'] + 0.3,
          'n05': S['gen3d'] + 0.4, 'n06': S['themes'] + 0.4, 'n07': S['test'] + 0.4, 'n08': S['audio'] + 0.5,
          'n09': S['timeline'] + 0.4, 'n10': S['close'] + 0.6}
AUD = os.path.join(ROOT, 'Assets', 'Resources', 'Audio')
sfx_at = [('catch', S['play'] + 1.2), ('catch', S['play'] + 3.1), ('hit', S['play'] + 6.4),
          ('catch', S['audio'] + 1.2), ('hit', S['audio'] + 2.2), ('gameover', S['audio'] + 3.0)]
inputs = [os.path.join(WORK, 'bgm.wav')] + [os.path.join(NAR, k + '.mp3') for k in nar_at] + [os.path.join(AUD, n + '.mp3') for n, _ in sfx_at]
args = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
for p in inputs: args += ['-i', p]
fc = []; lab = []
delays = list(nar_at.values()) + [t for _, t in sfx_at]
vols = [1.5] * len(nar_at) + [0.7] * len(sfx_at)
for i, (at, v) in enumerate(zip(delays, vols)):
    ms = int(at * 1000)
    fc.append(f'[{i+2}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume={v}[a{i}]'); lab.append(f'[a{i}]')
nn = len(nar_at)
fc.append(''.join(lab[:nn]) + f'amix=inputs={nn}:normalize=0,asplit=2[nar1][nar2]')
fc.append(''.join(lab[nn:]) + f'amix=inputs={len(sfx_at)}:normalize=0[sfx]')
fc.append('[1:a]volume=0.45[bg]')
fc.append('[bg][nar2]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=500[duck]')
fc.append(f'[duck][nar1][sfx]amix=inputs=3:normalize=0,alimiter=limit=0.95,atrim=0:{TOTAL}[aout]')
args += ['-filter_complex', ';'.join(fc), '-map', '0:v', '-map', '[aout]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
         '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-t', f'{TOTAL}', OUT]
p = subprocess.Popen(args, stdin=subprocess.PIPE)
N = int(round(TOTAL * FPS))
for fi in range(N):
    p.stdin.write(frame_at(fi / FPS).tobytes())
    if fi % 300 == 0: print('frame', fi, '/', N, flush=True)
p.stdin.close(); p.wait()
print('done', p.returncode, OUT)
