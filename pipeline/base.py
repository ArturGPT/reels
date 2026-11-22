"""Reel v4 — style of the reference: dark grid + neon paths, top word-by-word captions,
glowing UI windows, gamified 'mission' story, step counters, banners. Voice drives timing."""
import subprocess, sys, wave, random, math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
F = "/usr/share/fonts/opentype/inter/"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
import json, os
EP = json.load(open(os.environ["EPISODE"]))
WORK = os.environ.get("WORK", "/tmp/reelwork"); os.makedirs(WORK, exist_ok=True)
TTS = WORK
BG = (14, 15, 18); GRIDC = (27, 29, 34); WIN = (17, 19, 23); BAR = (24, 26, 31)
WHITE = (246, 246, 248); GREY = (128, 130, 138); LIME = (198, 255, 61); RED = (255, 70, 70)
ORANGE = (230, 120, 70); BLUE = (120, 170, 255); DIM = (90, 92, 100)


@lru_cache(None)
def fnt(path, size):
    return ImageFont.truetype(path if path.startswith("/") else F + path, size)


def ease(x): x = max(0., min(1., x)); return 1 - (1 - x) ** 3
def back(x): x = max(0., min(1., x)); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def mix(a, b, p): return tuple(int(a[i] * p + b[i] * (1 - p)) for i in range(3))


# ---------------- background: grid + neon route with glow ----------------
def make_bg():
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    for x in range(0, W, 120): d.line((x, 0, x, H), fill=GRIDC, width=3)
    for y in range(0, H, 120): d.line((0, y, W, y), fill=GRIDC, width=3)
    for x, y0, y1 in [(240, 0, 700), (840, 1100, 1920)]: d.line((x, y0, x, y1), fill=(22, 24, 28), width=26)
    route = [(-20, 1560), (360, 1560), (360, 1320), (720, 1320), (720, 1000), (1100, 1000)]
    glow = Image.new("RGB", (W // 4, H // 4), (0, 0, 0)); g = ImageDraw.Draw(glow)
    g.line([(x / 4, y / 4) for x, y in route], fill=(90, 120, 20), width=6)
    glow = glow.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
    im = Image.fromarray(__import__("numpy").clip(__import__("numpy").asarray(im, dtype="int16") +
                                                 __import__("numpy").asarray(glow, dtype="int16"), 0, 255).astype("uint8"))
    d = ImageDraw.Draw(im)
    d.line(route, fill=(120, 150, 40), width=8, joint="curve")
    # vignette top/bottom so captions & UI pop
    v = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(v)
    for i in range(300): vd.line((0, i, W, i), fill=int(170 * (1 - i / 300)))
    im.paste(Image.new("RGB", (W, H), BG), (0, 0), v)
    return im, route


BGIMG, ROUTE = make_bg()


def glow_box(im, box, col, r=40, strength=1.0):
    """additive soft glow behind a rounded box (computed at 1/4 res)."""
    import numpy as np
    x0, y0, x1, y1 = [int(v) for v in box]
    pad = r * 2
    gx0, gy0 = max(0, x0 - pad), max(0, y0 - pad); gx1, gy1 = min(W, x1 + pad), min(H, y1 + pad)
    sw, sh = max(1, (gx1 - gx0) // 4), max(1, (gy1 - gy0) // 4)
    g = Image.new("RGB", (sw, sh)); gd = ImageDraw.Draw(g)
    gd.rounded_rectangle(((x0 - gx0) / 4, (y0 - gy0) / 4, (x1 - gx0) / 4, (y1 - gy0) / 4), 8,
                         outline=tuple(int(c * 0.55 * strength) for c in col), width=5)
    g = g.filter(ImageFilter.GaussianBlur(r / 6)).resize((gx1 - gx0, gy1 - gy0), Image.BILINEAR)
    region = im.crop((gx0, gy0, gx1, gy1))
    out = np.clip(np.asarray(region, dtype="int16") + np.asarray(g, dtype="int16"), 0, 255).astype("uint8")
    im.paste(Image.fromarray(out), (gx0, gy0))


def window(im, box, title, accent=ORANGE, glow=True):
    if glow: glow_box(im, box, accent)
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 22, fill=WIN, outline=(40, 42, 48), width=2)
    d.rounded_rectangle((x0, y0, x1, y0 + 64), 22, fill=BAR); d.rectangle((x0, y0 + 40, x1, y0 + 64), fill=BAR)
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse((x0 + 26 + i * 30, y0 + 24, x0 + 44 + i * 30, y0 + 42), fill=c)
    f = fnt("Inter-Medium.otf", 30); tw = d.textlength(title, font=f)
    d.text(((x0 + x1 - tw) / 2, y0 + 16), title, font=f, fill=accent)
    return d


def step_badge(d, x, y, n, total, p=1.0):
    f = fnt(MONO_B, 54)
    txt = f"ШАГ {n}/{total}"
    d.text((x, y), txt, font=f, fill=mix(LIME, WIN, p))


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: out.append(cur); cur = w
    return out + [cur]


def type_text(d, x, y, text, f, maxw, n, hl_from=None, col=WHITE, lh=None):
    lh = lh or int(f.size * 1.35); idx = 0; cx, cy = x, y
    for ln in wrap(d, text, f, maxw):
        cx = x
        for ch in ln:
            if idx >= n: return cx, cy
            d.text((cx, cy), ch, font=f, fill=LIME if hl_from is not None and idx >= hl_from else col)
            cx += d.textlength(ch, font=f); idx += 1
        idx += 1; cy += lh
    return cx, cy - lh


# ---------------- captions (karaoke, 1–3 words, boxed keywords) ----------------
def draw_caption(im, words, cur):
    """words: list of (word, boxed). cur: index of current word inside this chunk."""
    d = ImageDraw.Draw(im)
    fb, fr = fnt("InterDisplay-Bold.otf", 74), fnt("InterDisplay-Medium.otf", 74)
    items = [(w, b, i == cur, i < cur) for i, (w, b) in enumerate(words[:cur + 1])]
    # layout into ≤2 lines centred
    lines, line, lw = [], [], 0
    for it in items:
        ww = d.textlength(it[0] + " ", font=fb)
        if lw + ww > 900 and line: lines.append(line); line, lw = [], 0
        line.append(it); lw += ww
    lines.append(line)
    y = 360 - (len(lines) - 1) * 50
    for ln in lines:
        tot = sum(d.textlength(w + " ", font=fb if c or b else fr) for w, b, c, _ in ln) - d.textlength(" ", font=fb)
        x = (W - tot) / 2 + (14 if ln[0][1] else 0)
        for w, boxed, current, past in ln:
            f = fb if (current or boxed) else fr
            tw = d.textlength(w, font=f)
            if boxed:
                d.rectangle((x - 14, y + 2, x + tw + 14, y + 92), fill=(22, 26, 40), outline=BLUE, width=3)
                for hx, hy in [(x - 14, y + 2), (x + tw + 14, y + 92)]:
                    d.ellipse((hx - 9, hy - 9, hx + 9, hy + 9), fill=BLUE)
            col = RED if w == "***" else (WHITE if (current or boxed) else GREY)
            d.text((x, y), w, font=f, fill=col)
            x += tw + d.textlength(" ", font=fb) + (14 if boxed else 0)
        y += 100


# ---------------- script ----------------
# (scene, caption text with *boxed* words, spoken text)
SCRIPT = [tuple(x) for x in EP["lines"]]
GAP = 0.12
BAD_USER = EP["bad_prompt"]
GOOD_USER = EP["good_prompt"]


EL_VOICE = "nPczCjzI2devNBz1zQrb"  # Brian


def el_tts(text, out_wav):
    import json, urllib.request
    key = os.environ["ELEVENLABS_API_KEY"].strip()
    body = json.dumps({"text": text, "model_id": "eleven_multilingual_v2", "language_code": "ru",
                       "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.35,
                                          "use_speaker_boost": True}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{EL_VOICE}?output_format=mp3_44100_128",
                                 data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    mp3 = out_wav[:-4] + ".mp3"
    open(mp3, "wb").write(urllib.request.urlopen(req, timeout=60).read())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "44100",
                    "-af", "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                    out_wav], check=True)


def beep_pcm(rate, dur=0.42):
    import numpy as np
    t = np.arange(int(rate * dur)) / rate
    env = np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.01)
    return (np.sin(2 * np.pi * 1000 * t) * env * 0.5 * 32767).astype("<i2").tobytes()


def synth():
    import os
    os.makedirs(f"{TTS}/el", exist_ok=True)
    starts, durs, chunks = [], [], []
    t, rate = 0.2, 44100
    for i, (_, _, spoken) in enumerate(SCRIPT):
        pcm = b""
        for j, piece in enumerate(spoken.split("[пип]")):
            if j > 0: pcm += beep_pcm(rate) + b"\0\0" * int(rate * 0.12)
            piece = piece.strip(" .")
            if not piece: continue
            fn = f"{TTS}/el/l{i}_{j}.wav"
            if not os.path.exists(fn): el_tts(piece + ".", fn)
            with wave.open(fn) as w: pcm += w.readframes(w.getnframes())
        d = len(pcm) / 2 / rate
        chunks.append(pcm); starts.append(t); durs.append(d); t += d + GAP
    total = t + 0.5
    buf = bytearray(int(total * rate) * 2)
    for s0, data in zip(starts, chunks):
        o = int(s0 * rate) * 2; buf[o:o + len(data)] = data
    with wave.open(f"{TTS}/voice.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(buf))
    return starts, durs, total


def word_timeline(starts, durs):
    """per caption word: (t_start, chunk_words, index_in_chunk). Timing ∝ word length."""
    out = []
    for (_, cap, _), s, d in zip(SCRIPT, starts, durs):
        raw = cap.split(" ")
        words = [("***", False) if w == "ПИП!" else (w.replace("*", ""), "*" in w) for w in raw]
        weights = [len(w) + 3 for w, _ in words]; tot = sum(weights)
        # chunk: ≤3 words, ≤18 chars, break after sentence punctuation
        chunks, cur = [], []
        for w in words:
            cur.append(w)
            if len(cur) == 3 or sum(len(x[0]) for x in cur) > 16 or w[0][-1] in ".:—,": chunks.append(cur); cur = []
        if cur: chunks.append(cur)
        acc, k = 0, 0
        for ch in chunks:
            for j in range(len(ch)):
                out.append((s + d * 0.92 * acc / tot, ch, j)); acc += weights[k]; k += 1
    return out


def scenes_from(starts, durs, total):
    sc = []
    for (k, _, _), s, d in zip(SCRIPT, starts, durs):
        if sc and sc[-1][0] == k: sc[-1][2] = s + d
        else: sc.append([k, s - 0.08, s + d])
    for i in range(len(sc) - 1): sc[i][2] = sc[i + 1][1]
    sc[0][1] = 0.0; sc[-1][2] = total
    return sc


# ---------------- scene painters (lt = local time in scene) ----------------
def sc_hook(im, lt):
    p = back(lt / 0.35)
    bw, bh = 860 * p, 520 * p
    box = ((W - bw) / 2, 620 + (520 - bh) / 2, (W + bw) / 2, 620 + (520 + bh) / 2)
    if p < 0.2: return
    d = window(im, box, "Новая миссия", LIME)
    if lt > 0.3:
        f = fnt("InterDisplay-Black.otf", 92); d.text((150, 760), "МИССИЯ:", font=f, fill=LIME)
        f2 = fnt("InterDisplay-Bold.otf", 60)
        for i, l in enumerate(EP["mission"]):
            d.text((150, 880 + i * 76), l, font=f2, fill=WHITE)
    if lt > 0.9:  # reward tag
        q = back((lt - 0.9) / 0.3); f3 = fnt("InterDisplay-Black.otf", int(64 * q) + 1)
        d.rounded_rectangle((700, 1060, 700 + 230 * q, 1060 + 90 * q), 18, fill=LIME)
        d.text((722, 1068), "0/3", font=f3, fill=BG)


def chat_window(im, lt, user, hl, step, ai=None, ai_col=WHITE, ai_at=99):
    d = window(im, (70, 560, W - 70, 1500), "ChatGPT — новый чат", ORANGE)
    step_badge(d, 120, 640, step, 3, ease(lt / 0.3))
    f = fnt("Inter-Regular.otf", 44)
    n = int(len(user) * ease((lt - 0.2) / max(0.8, len(user) / 34)))
    lines = wrap(d, user, f, 700); bh = len(lines) * 60 + 56
    d.rounded_rectangle((W - 120 - 760, 760, W - 120, 760 + bh), 30, fill=(44, 46, 54))
    cx, cy = type_text(d, W - 120 - 730, 788, user, f, 700, n, hl, lh=60)
    if n < len(user) and int(lt * 5) % 2 == 0: d.rectangle((cx + 3, cy + 6, cx + 8, cy + 54), fill=WHITE)
    if ai and lt > ai_at:
        q = ease((lt - ai_at) / 0.35); y = 760 + bh + 60 + 30 * (1 - q)
        d.ellipse((120, y, 176, y + 56), fill=mix(ai_col, WIN, q))
        fa = fnt("Inter-Regular.otf", 40)
        for i, l in enumerate(wrap(d, ai, fa, 760)[: 1 + int(6 * ease((lt - ai_at) / 0.9))]):
            d.text((200, y + 6 + i * 56), l, font=fa, fill=mix(ai_col, WIN, q))
    return d


def banner(im, lt, text, sub, col):
    q = ease(lt / 0.25)
    y0 = 1230
    glow_box(im, (0, y0 - 40, W, y0 + 200), col, r=60)
    d = ImageDraw.Draw(im)
    d.rectangle((0, y0 - 40, W * q, y0 + 200), fill=(18, 20, 16) if col == LIME else (30, 12, 12))
    d.line((0, y0 - 40, W * q, y0 - 40), fill=col, width=4); d.line((0, y0 + 200, W * q, y0 + 200), fill=col, width=4)
    if lt > 0.12:
        s = back((lt - 0.12) / 0.3); f = fnt("InterDisplay-Black.otf", max(8, int(84 * s)))
        ox = oy = 0
        if col == RED and lt < 0.6: random.seed(int(lt * 60)); ox, oy = random.randint(-10, 10), random.randint(-8, 8)
        tw = d.textlength(text, font=f); d.text(((W - tw) / 2 + ox, y0 + 20 + oy), text, font=f, fill=col)
        f2 = fnt(MONO, 34); tw2 = d.textlength(sub, font=f2)
        d.text(((W - tw2) / 2, y0 + 140), sub, font=f2, fill=WHITE)


def sc_q(im, lt):
    d = window(im, (70, 560, W - 70, 1500), "ChatGPT — допрос", LIME)
    qs = [("Аудитория", "Кто будет читать пост?"), ("Цель", "Продажа, охват или подписки?"),
          ("Тон", "Дерзкий или экспертный?")]
    for i, (h, s) in enumerate(qs):
        q = back((lt - 0.15 - i * 0.55) / 0.35)
        if q <= 0: continue
        y = 680 + i * 250
        x0 = 120 + 400 * (1 - min(1, q))
        glow_box(im, (x0, y, x0 + 840, y + 200), LIME, r=26, strength=0.6); d = ImageDraw.Draw(im)
        d.rounded_rectangle((x0, y, x0 + 840, y + 200), 26, fill=(22, 26, 18), outline=LIME, width=3)
        d.ellipse((x0 + 34, y + 54, x0 + 126, y + 146), outline=LIME, width=5)
        fn = fnt("InterDisplay-Black.otf", 54); d.text((x0 + 64, y + 66), str(i + 1), font=fn, fill=LIME)
        d.text((x0 + 160, y + 40), h, font=fnt("InterDisplay-Bold.otf", 56), fill=WHITE)
        d.text((x0 + 160, y + 112), s, font=fnt("Inter-Regular.otf", 38), fill=GREY)


def sc_s3(im, lt):
    d = window(im, (70, 560, W - 70, 1500), EP.get("result_title", "Готовый результат"), LIME)
    step_badge(d, 120, 640, 3, 3)
    rows = EP["result_rows"]
    for i, r in enumerate(rows):
        q = ease((lt - 0.3 - i * 0.35) / 0.3)
        if q <= 0: continue
        y = 780 + i * 150
        d.rounded_rectangle((120, y, 120 + 840, y + 116), 20, fill=mix((26, 30, 20), WIN, q))
        d.line((160, y + 62, 180, y + 82), fill=mix(LIME, WIN, q), width=8)
        d.line((180, y + 82, 216, y + 38), fill=mix(LIME, WIN, q), width=8)
        d.text((250, y + 34), r, font=fnt("Inter-Medium.otf", 40), fill=mix(WHITE, WIN, q))


def sc_cta(im, lt):
    p = back(lt / 0.35)
    if p < 0.1: return
    x0, y0 = 120, 640; w, h = 840, 760 * min(1, p)
    glow_box(im, (x0, y0, x0 + w, y0 + h), LIME, r=50); d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), 40, fill=WIN, outline=LIME, width=4)
    if p < 0.9: return
    d.ellipse((W / 2 - 110, y0 + 70, W / 2 + 110, y0 + 290), fill=LIME)
    fa = fnt("InterDisplay-Black.otf", 120); tw = d.textlength("A", font=fa)
    d.text((W / 2 - tw / 2, y0 + 108), "A", font=fa, fill=BG)
    for txt, fz, col, yy in [("ArturGPT", ("InterDisplay-Bold.otf", 70), WHITE, 330),
                             ("Telegram-канал про нейросети", ("Inter-Regular.otf", 36), GREY, 430),
                             ("t.me/ArturGPT", (MONO_B, 46), LIME, 500)]:
        f = fnt(*fz); tw = d.textlength(txt, font=f); d.text(((W - tw) / 2, y0 + yy), txt, font=f, fill=col)
    pulse = 1 + 0.04 * math.sin(lt * 8)
    bw, bh = 600 * pulse, 110 * pulse; cx, cy = W / 2, y0 + 640
    d.rounded_rectangle((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), 55, fill=LIME)
    f = fnt("InterDisplay-Black.otf", 48); t = "ЗАБРАТЬ ШАБЛОН"; tw = d.textlength(t, font=f)
    d.text((cx - tw / 2, cy - 30), t, font=f, fill=BG)
    # cursor click
    k = ease((lt - 0.6) / 0.6); mx, my = 980 - 180 * k, 1500 - 160 * k
    d.polygon([(mx, my), (mx, my + 70), (mx + 18, my + 52), (mx + 32, my + 84), (mx + 44, my + 78),
               (mx + 30, my + 48), (mx + 54, my + 48)], fill=WHITE, outline=BG)


def make_frame(t, scenes, words, total):
    im = BGIMG.copy()
    # slow drifting dot along the route for constant motion
    d = ImageDraw.Draw(im)
    seg = (t * 0.35) % (len(ROUTE) - 1); i = int(seg); f = seg - i
    (ax, ay), (bx, by) = ROUTE[i], ROUTE[i + 1]; px, py = ax + (bx - ax) * f, ay + (by - ay) * f
    d.ellipse((px - 14, py - 14, px + 14, py + 14), fill=LIME)
    k, s0, s1 = next((s for s in scenes if s[1] <= t < s[2]), scenes[-1]); lt = t - s0
    if k == "hook": sc_hook(im, lt)
    elif k == "s1": chat_window(im, lt, BAD_USER, None, 1)
    elif k == "fail":
        chat_window(im, lt + 5, BAD_USER, None, 1,
                    "Конечно! Откройте для себя мир безграничных возможностей! Каждый день — это шанс стать лучше...", DIM, 4.9)
        if lt > 0.9: banner(im, lt - 0.9, "МИССИЯ ПРОВАЛЕНА", "--- ответ — вода ---", RED)
    elif k == "s2": chat_window(im, lt, GOOD_USER, len("Напиши пост для Instagram. "), 2)
    elif k == "q": sc_q(im, lt)
    elif k == "s3": sc_s3(im, lt)
    elif k == "win":
        sc_s3(im, lt + 5); banner(im, lt, "МИССИЯ ВЫПОЛНЕНА", "--- охренеть ---", LIME)
    else: sc_cta(im, lt)
    # caption
    cur = None
    for w in words:
        if w[0] <= t: cur = w
        else: break
    if cur and t - cur[0] < 2.5: draw_caption(im, cur[1], cur[2])
    # punch-in + flash on cuts
    z = 1 + 0.06 * (1 - ease(lt / 0.3))
    if s0 > 0 and z > 1.002:
        nw, nh = int(W * z), int(H * z)
        im = im.resize((nw, nh), Image.BILINEAR).crop(((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H))
    if s0 > 0 and lt < 0.06: im = Image.blend(im, Image.new("RGB", (W, H), WHITE), 0.22)
    ImageDraw.Draw(im).rectangle((0, H - 10, int(W * t / total), H), fill=LIME)
    return im


def audio_graph(scenes):
    parts, labels = [], []
    for i, (k, s0, _) in enumerate(scenes[1:]):
        ms = int(max(0, s0 - 0.1) * 1000)
        parts.append(f"anoisesrc=d=0.3:c=pink:a=0.5,highpass=f=500,lowpass=f=6000,afade=t=in:d=0.12,afade=t=out:st=0.12:d=0.18,volume=0.28,adelay={ms}|{ms}[w{i}]")
        labels.append(f"[w{i}]")
    for k, s0, _ in scenes:
        if k in ("fail", "win"):
            ms = int((s0 + (0.9 if k == "fail" else 0.1)) * 1000)
            snd = ("sine=f=110:d=0.45,volume=0.5" if k == "fail" else
                   "sine=f=880:d=0.5,volume=0.22[x];sine=f=1320:d=0.5,volume=0.18,adelay=120|120[y];[x][y]amix=2:normalize=0")
            if k == "fail": parts.append(f"{snd},afade=t=out:st=0.2:d=0.25,adelay={ms}|{ms}[b{k}]")
            else: parts.append(f"{snd},afade=t=out:st=0.2:d=0.3,adelay={ms}|{ms}[b{k}]")
            labels.append(f"[b{k}]")
    return ";".join(parts) + (";[1:a]aformat=channel_layouts=stereo,highpass=f=90,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=3,"
        "acompressor=threshold=0.12:ratio=3:attack=5:release=80,aecho=0.8:0.5:28:0.1,volume=1.5,asplit=2[v][vs];"
        "[2:a]volume=0.16[m0];[m0][vs]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[m];"
        "[v][m]") + "".join(labels) + f"amix=inputs={len(labels) + 2}:normalize=0,alimiter=limit=0.95[a]"


if __name__ == "__main__":
    out = sys.argv[1]
    starts, durs, total = synth()
    subprocess.run(["python3", "/home/claude/reel2/music.py", "/home/claude/reel2/bed.wav", str(total + 1)], check=True)
    scenes = scenes_from(starts, durs, total); words = word_timeline(starts, durs)
    print("total", round(total, 2), [(k, round(a, 1)) for k, a, _ in scenes])
    if len(sys.argv) > 2:
        for tt in map(float, sys.argv[2:]): make_frame(tt, scenes, words, total).save(f"/home/claude/reel2/v6_{tt:05.2f}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", f"{TTS}/voice.wav", "-i", "/home/claude/reel2/bed.wav", "-filter_complex", audio_graph(scenes),
                          "-map", "0:v", "-map", "[a]", "-t", str(total), "-c:v", "libx264", "-crf", "18",
                          "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(total * FPS)): p.stdin.write(make_frame(i / FPS, scenes, words, total).tobytes())
    p.stdin.close(); sys.exit(p.wait())
