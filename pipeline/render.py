"""Reel v7 = v6 (mission style, Brian voice, karaoke captions) + best of reference 2:
colour-switching backgrounds, blur-in captions, messenger-bubble scenes, toggle with cursor, purple CTA."""
import subprocess, sys, math, os
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base as R
from base import (W, H, FPS, fnt, ease, back, mix, wrap, type_text, window, glow_box, banner,
                     chat_window, sc_hook, sc_s3, sc_cta, BAD_USER, LIME, RED, WHITE, GREY, BG, MONO_B)

EP = R.EP

INK = (17, 17, 20); SOFT = (156, 160, 170); BLUE = (10, 132, 255); BUBBLE_G = (233, 233, 236)
PURPLE_A, PURPLE_B = (88, 28, 200), (140, 60, 255)
THEME = {"hook": "dark", "s1": "dark", "fail": "dark", "toggle": "white", "type": "white", "q": "white",
         "s3": "dark", "win": "dark", "cta": "dark"}


def make_white():
    im = Image.new("RGB", (W, H), (250, 250, 251)); d = ImageDraw.Draw(im)
    for x in range(0, W, 120): d.line((x, 0, x, H), fill=(238, 239, 242), width=2)
    for y in range(0, H, 120): d.line((0, y, W, y), fill=(238, 239, 242), width=2)
    return im


def make_purple():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H): d.line((0, y, W, y), fill=mix(PURPLE_B, PURPLE_A, y / H))
    g = Image.new("RGB", (W, H), (0, 0, 0)); gd = ImageDraw.Draw(g)
    gd.ellipse((200, 500, 900, 1300), fill=(70, 30, 90))
    import numpy as np
    return Image.fromarray(np.clip(np.asarray(im, "int16") + np.asarray(g.filter(ImageFilter.GaussianBlur(160)), "int16"), 0, 255).astype("uint8"))


BGS = {"dark": R.BGIMG, "white": make_white(), "purple": make_purple()}


# ---------- captions: karaoke + blur-in, theme aware ----------
def draw_caption(im, words, cur, theme, since):
    layer = Image.new("RGBA", (W, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    fb, fr = fnt("InterDisplay-Bold.otf", 76), fnt("InterDisplay-Medium.otf", 76)
    light = theme == "white"
    c_cur = INK if light else WHITE; c_past = SOFT if light else ((205, 200, 235) if theme == "purple" else GREY)
    items = [(w, b, i == cur) for i, (w, b) in enumerate(words[:cur + 1])]
    lines, line, lw = [], [], 0
    for it in items:
        ww = d.textlength(it[0] + " ", font=fb)
        if lw + ww > 900 and line: lines.append(line); line, lw = [], 0
        line.append(it); lw += ww
    lines.append(line)
    y = 300 - (len(lines) - 1) * 52
    for ln in lines:
        tot = sum(d.textlength(w + " ", font=fb if c or b else fr) for w, b, c in ln) 
        x = (W - tot) / 2
        for w, boxed, current in ln:
            f = fb if (current or boxed) else fr; tw = d.textlength(w, font=f)
            if w == "***":
                d.rounded_rectangle((x - 18, y + 8, x + tw + 18, y + 96), 22, fill=(17, 17, 20, 255))
            col = RED if w == "***" else (c_cur if (current or boxed) else c_past)
            d.text((x, y), w, font=f, fill=col + (255,))
            x += tw + d.textlength(" ", font=fb)
        y += 104
    # blur-in when a new chunk starts (reference-2 style)
    if cur == 0 and since < 0.18:
        layer = layer.filter(ImageFilter.GaussianBlur(14 * (1 - since / 0.18)))
    im.paste(layer, (0, 80), layer)


# ---------- new white scenes ----------
def avatar(d, x, y, r, col, letter, tc):
    d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    f = fnt("InterDisplay-Bold.otf", int(r * 1.1)); tw = d.textlength(letter, font=f)
    d.text((x - tw / 2, y - r * 0.68), letter, font=f, fill=tc)


def bubble(d, text, y, mine, p=1.0, hl_from=None, n=None, f=None):
    f = f or fnt("Inter-Medium.otf", 54)
    lines = wrap(d, text, f, 680); lh = 70
    bw = max(d.textlength(l, font=f) for l in lines) + 70; bh = len(lines) * lh + 44
    q = back(p); bw2, bh2 = bw * q, bh * q
    if mine: x1 = W - 150; x0 = x1 - bw2; col, tc = BLUE, WHITE
    else: x0 = 150; x1 = x0 + bw2; col, tc = BUBBLE_G, INK
    if q < 0.15: return bh
    d.rounded_rectangle((x0, y, x1, y + bh2), 40, fill=col)
    if p >= 1:
        n = len(text) if n is None else n; idx = 0; cy = y + 20
        for l in lines:
            cx = x0 + 35
            for ch in l:
                if idx >= n: break
                d.text((cx, cy), ch, font=f, fill=((255, 240, 120) if mine else BLUE) if hl_from is not None and idx >= hl_from else tc)
                cx += d.textlength(ch, font=f); idx += 1
            idx += 1; cy += lh
    if mine: avatar(d, W - 95, y + bh - 40, 38, (60, 60, 70), "Я", WHITE)
    else: avatar(d, 95, y + bh - 40, 38, INK, "AI", LIME)
    return bh


def sc_toggle(im, lt):
    d = ImageDraw.Draw(im)
    f = fnt("InterDisplay-Bold.otf", 48)
    on = ease((lt - 0.95) / 0.25)
    cx, cy = W / 2, 980; tw_, th_ = 300, 150
    d.text((cx - tw_ / 2 - 40 - d.textlength(EP["toggle"][0], font=f), cy - 30), EP["toggle"][0], font=f, fill=mix(SOFT, INK, on))
    d.text((cx + tw_ / 2 + 40, cy - 30), EP["toggle"][1], font=f, fill=mix(INK, SOFT, on))
    d.rounded_rectangle((cx - tw_ / 2, cy - th_ / 2, cx + tw_ / 2, cy + th_ / 2), th_ / 2,
                        fill=mix(BLUE, (225, 226, 230), on))
    kx = cx - tw_ / 2 + th_ / 2 + (tw_ - th_) * on
    d.ellipse((kx - 64, cy - 64, kx + 64, cy + 64), fill=WHITE, outline=(215, 216, 220), width=2)
    # cursor flies in, clicks the knob
    k = ease(lt / 0.9); mx, my = 900 - (900 - (cx + 40)) * k, 1500 - (1500 - (cy + 20)) * k
    s = 0.85 if 0.9 < lt < 1.05 else 1.0
    pts = [(0, 0), (0, 70), (18, 52), (32, 84), (44, 78), (30, 48), (54, 48)]
    d.polygon([(mx + x * s, my + y * s) for x, y in pts], fill=INK, outline=WHITE)
    if lt > 1.2:  # sub label under toggle
        p = ease((lt - 1.2) / 0.3); f2 = fnt("Inter-Medium.otf", 40); t = EP["toggle"][2]
        tw = d.textlength(t, font=f2); d.text(((W - tw) / 2, 1160 + 20 * (1 - p)), t, font=f2, fill=mix(SOFT, (250, 250, 251), p))


GOOD = EP["good_prompt"]


def sc_type(im, lt, dur):
    d = ImageDraw.Draw(im)
    n = int(len(GOOD) * ease(lt / max(1.0, dur * 0.85)))
    bubble(d, GOOD, 640, True, 1.0, len(EP["bad_prompt"]) + 1 if GOOD.startswith(EP["bad_prompt"]) else None, n)


def sc_q(im, lt):
    d = ImageDraw.Draw(im)
    y = 600
    y += bubble(d, EP["q_user"], y, True, 1.0) + 40
    qs = EP["q_replies"]
    for i, q in enumerate(qs):
        st = 0.3 + i * 0.75
        if lt < st:
            if lt > st - 0.45:  # typing dots
                d.rounded_rectangle((150, y, 330, y + 90), 40, fill=BUBBLE_G)
                for j in range(3):
                    a = 0.5 + 0.5 * math.sin(lt * 12 - j)
                    d.ellipse((190 + j * 40, y + 35, 210 + j * 40, y + 55), fill=mix(SOFT, BUBBLE_G, a))
            break
        y += bubble(d, q, y, False, (lt - st) / 0.3) + 30
    if lt > 2.6:  # 'допрос' stamp
        s = back((lt - 2.6) / 0.3); f = fnt("InterDisplay-Black.otf", max(8, int(110 * s)))
        t = EP["q_stamp"]; tw = d.textlength(t, font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 40, 1370, W / 2 + tw / 2 + 40, 1370 + 150 * s), 28, outline=RED, width=9)
        d.text((W / 2 - tw / 2, 1390), t, font=f, fill=RED)


def sc_profile(im, lt):
    p = back(lt / 0.35)
    if p < 0.1: return
    x0, y0, w = 110, 600, 860; h = 700 * min(1, p)
    glow_box(im, (x0, y0, x0 + w, y0 + h), LIME, r=50); d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), 44, fill=(17, 17, 20), outline=(60, 60, 70), width=3)
    if p < 0.9: return
    # avatar + name + bio
    d.ellipse((x0 + 50, y0 + 60, x0 + 230, y0 + 240), fill=LIME)
    fa = fnt("InterDisplay-Black.otf", 100); tw = d.textlength("A", font=fa)
    d.text((x0 + 140 - tw / 2, y0 + 88), "A", font=fa, fill=BG)
    d.text((x0 + 270, y0 + 85), "arturgpt", font=fnt("InterDisplay-Bold.otf", 64), fill=WHITE)
    d.text((x0 + 270, y0 + 168), EP.get("bio", "нейросети без воды"), font=fnt("Inter-Regular.otf", 40), fill=GREY)
    # link chip (the 'шапка' link) — highlighted, clicked by cursor
    pulse = 0.5 + 0.5 * math.sin(lt * 7)
    cy = y0 + 320; chip = (x0 + 50, cy, x0 + w - 50, cy + 110)
    d.rounded_rectangle(chip, 55, fill=(30, 36, 20), outline=mix(LIME, (80, 100, 30), pulse), width=5)
    # chain-link icon
    for dx in (0, 34):
        d.rounded_rectangle((x0 + 95 + dx, cy + 38, x0 + 145 + dx, cy + 72), 17, outline=LIME, width=6)
    d.text((x0 + 210, cy + 28), "шаблоны и промпты", font=fnt("InterDisplay-Bold.otf", 50), fill=LIME)
    # subscribe button
    bx = (x0 + 50, y0 + 500, x0 + w - 50, y0 + 610)
    d.rounded_rectangle(bx, 30, fill=(0, 149, 246))
    f = fnt("InterDisplay-Bold.otf", 50); t = "Подписаться"; tw = d.textlength(t, font=f)
    d.text(((bx[0] + bx[2] - tw) / 2, bx[1] + 26), t, font=f, fill=WHITE)
    # arrow label above card
    if lt > 0.5:
        q = ease((lt - 0.5) / 0.3); f2 = fnt("InterDisplay-Bold.otf", 46); t2 = "ссылка в шапке профиля"
        tw2 = d.textlength(t2, font=f2); yy = y0 - 90 + 20 * (1 - q)
        d.text(((W - tw2) / 2, yy), t2, font=f2, fill=mix(WHITE, (100, 60, 200), q))
    # cursor moves to the link chip and taps it
    k = ease((lt - 0.4) / 0.7); mx, my = 980 - (980 - 640) * k, 1600 - (1600 - (cy + 70)) * k
    s_ = 0.85 if 1.1 < lt < 1.25 else 1.0
    pts = [(0, 0), (0, 70), (18, 52), (32, 84), (44, 78), (30, 48), (54, 48)]
    d.polygon([(mx + x * s_, my + y * s_) for x, y in pts], fill=WHITE, outline=BG)
    if 1.1 < lt < 1.5:
        r = 30 + 120 * (lt - 1.1); d.ellipse((mx - r, my - r, mx + r, my + r), outline=mix(LIME, (17, 17, 20), 1 - (lt - 1.1) / 0.4), width=4)


def sc_final(im, lt):
    """Ending like the reference screenshot: MISSION COMPLETE banner + glowing profile card with link + resource rows."""
    # banner
    q = ease(lt / 0.25); y0 = 560
    glow_box(im, (0, y0, W, y0 + 190), LIME, r=50); d = ImageDraw.Draw(im)
    d.rectangle((0, y0, W * q, y0 + 190), fill=(18, 20, 14))
    d.line((0, y0, W * q, y0), fill=LIME, width=4); d.line((0, y0 + 190, W * q, y0 + 190), fill=LIME, width=4)
    if lt > 0.1:
        sc = back((lt - 0.1) / 0.3); f = fnt("InterDisplay-Black.otf", max(8, int(82 * sc)))
        t = "МИССИЯ ВЫПОЛНЕНА"; tw = d.textlength(t, font=f); d.text(((W - tw) / 2, y0 + 26), t, font=f, fill=LIME)
        f2 = fnt(MONO_B, 32); t2 = EP["final_sub"]; tw2 = d.textlength(t2, font=f2)
        d.text(((W - tw2) / 2, y0 + 136), t2, font=f2, fill=WHITE)
    # card
    p = back((lt - 0.25) / 0.35)
    if p < 0.1: return
    x0, cy0, w = 90, 830, 900; h = 720 * min(1, p)
    glow_box(im, (x0, cy0, x0 + w, cy0 + h), LIME, r=55); d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0, cy0, x0 + w, cy0 + h), 40, fill=(17, 18, 22), outline=LIME, width=4)
    if p < 0.95: return
    d.ellipse((x0 + 40, cy0 + 36, x0 + 160, cy0 + 156), fill=LIME, outline=(40, 60, 20), width=6)
    fa = fnt("InterDisplay-Black.otf", 70); tw = d.textlength("A", font=fa)
    d.text((x0 + 100 - tw / 2, cy0 + 54), "A", font=fa, fill=BG)
    d.text((x0 + 190, cy0 + 48), "arturgpt", font=fnt("InterDisplay-Bold.otf", 56), fill=WHITE)
    d.text((x0 + 190, cy0 + 112), EP.get("bio", "нейросети без воды"), font=fnt("Inter-Regular.otf", 34), fill=GREY)
    d.rounded_rectangle((x0 + w - 190, cy0 + 70, x0 + w - 40, cy0 + 130), 30, fill=LIME)
    d.text((x0 + w - 162, cy0 + 76), "3/3", font=fnt("InterDisplay-Black.otf", 44), fill=BG)
    # link chip
    ly = cy0 + 190; pulse = 0.5 + 0.5 * math.sin(lt * 7)
    d.rounded_rectangle((x0 + 40, ly, x0 + 720, ly + 84), 42, fill=(26, 30, 18), outline=mix(LIME, (90, 110, 40), pulse), width=4)
    for dx in (0, 30):
        d.rounded_rectangle((x0 + 74 + dx, ly + 26, x0 + 118 + dx, ly + 58), 16, outline=LIME, width=5)
    d.text((x0 + 175, ly + 18), "ссылка в шапке профиля", font=fnt("InterDisplay-Bold.otf", 40), fill=(150, 190, 255))
    d.line((x0 + 175, ly + 66, x0 + 690, ly + 66), fill=(150, 190, 255), width=3)
    # resource rows
    rows = [tuple(x) for x in EP["final_rows"]]
    for i, (t1, t2, tag, hl) in enumerate(rows):
        rq = ease((lt - 0.7 - i * 0.25) / 0.3)
        if rq <= 0: continue
        ry = ly + 120 + i * 135 + 20 * (1 - rq)
        col = mix(WHITE, (17, 18, 22), rq)
        d.rounded_rectangle((x0 + 40, ry, x0 + w - 40, ry + 118), 22, fill=(23, 25, 30),
                            outline=LIME if hl else (45, 48, 55), width=4 if hl else 2)
        d.rounded_rectangle((x0 + 64, ry + 22, x0 + 138, ry + 96), 16, fill=(12, 13, 16))
        d.rectangle((x0 + 84, ry + 40, x0 + 118, ry + 78), outline=col, width=4)
        d.line((x0 + 92, ry + 52, x0 + 110, ry + 52), fill=col, width=3); d.line((x0 + 92, ry + 64, x0 + 110, ry + 64), fill=col, width=3)
        ft = fnt("InterDisplay-Bold.otf", 28); tw = d.textlength(tag, font=ft)
        avail = (x0 + w - 80 - tw - 30) - (x0 + 165) - 20
        fs = 42
        while fs > 28 and d.textlength(t1, font=fnt("InterDisplay-Bold.otf", fs)) > avail: fs -= 2
        d.text((x0 + 165, ry + 18 + (42 - fs) / 2), t1, font=fnt("InterDisplay-Bold.otf", fs), fill=col)
        d.text((x0 + 165, ry + 70), t2, font=fnt("Inter-Regular.otf", 30), fill=mix(GREY, (17, 18, 22), rq))
        ft = fnt("InterDisplay-Bold.otf", 28); tw = d.textlength(tag, font=ft)
        d.rounded_rectangle((x0 + w - 80 - tw - 30, ry + 22, x0 + w - 70, ry + 66), 22,
                            fill=LIME if tag == "бесплатно" else None, outline=None if tag == "бесплатно" else (80, 84, 92), width=2)
        d.text((x0 + w - 80 - tw - 15, ry + 28), tag, font=ft, fill=BG if tag == "бесплатно" else WHITE)
    # cursor to the link
    k = ease((lt - 0.6) / 0.7); mx, my = 1000 - (1000 - (x0 + 520)) * k, 1700 - (1700 - (ly + 50)) * k
    s_ = 0.85 if 1.3 < lt < 1.45 else 1.0
    pts = [(0, 0), (0, 70), (18, 52), (32, 84), (44, 78), (30, 48), (54, 48)]
    d.polygon([(mx + x * s_, my + y * s_) for x, y in pts], fill=WHITE, outline=BG)


def make_frame(t, scenes, words, total):
    k, s0, s1 = next((s for s in scenes if s[1] <= t < s[2]), scenes[-1]); lt = t - s0
    theme = THEME[k]
    im = BGS[theme].copy()
    if theme == "dark":
        d = ImageDraw.Draw(im); seg = (t * 0.35) % (len(R.ROUTE) - 1); i = int(seg); fr = seg - i
        (ax, ay), (bx, by) = R.ROUTE[i], R.ROUTE[i + 1]; px, py = ax + (bx - ax) * fr, ay + (by - ay) * fr
        d.ellipse((px - 14, py - 14, px + 14, py + 14), fill=LIME)
    if k == "hook": sc_hook(im, lt)
    elif k == "s1": chat_window(im, lt, BAD_USER, None, 1)
    elif k == "fail":
        chat_window(im, lt + 5, BAD_USER, None, 1,
                    EP["bad_answer"], (90, 92, 100), 4.9)
        if lt > 0.9: banner(im, lt - 0.9, "МИССИЯ ПРОВАЛЕНА", EP["fail_sub"], RED)
    elif k == "toggle": sc_toggle(im, lt)
    elif k == "type": sc_type(im, lt, s1 - s0)
    elif k == "q": sc_q(im, lt)
    elif k == "s3": sc_s3(im, lt)
    elif k == "win": sc_s3(im, lt + 5); banner(im, lt, "МИССИЯ ВЫПОЛНЕНА", EP["win_sub"], LIME)
    else: sc_final(im, lt)
    cur = None
    for w in words:
        if w[0] <= t: cur = w
        else: break
    if cur and t - cur[0] < 2.5:
        chunk_start = next(w[0] for w in words if w[1] is cur[1])
        draw_caption(im, cur[1], cur[2], theme, t - chunk_start)
    z = 1 + 0.06 * (1 - ease(lt / 0.3))
    if s0 > 0 and z > 1.002:
        nw, nh = int(W * z), int(H * z)
        im = im.resize((nw, nh), Image.BILINEAR).crop(((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H))
    if s0 > 0 and lt < 0.06: im = Image.blend(im, Image.new("RGB", (W, H), WHITE), 0.22)
    ImageDraw.Draw(im).rectangle((0, H - 10, int(W * t / total), H), fill=BLUE if theme == "white" else LIME)
    return im


if __name__ == "__main__":
    out = sys.argv[1]
    starts, durs, total = R.synth()
    subprocess.run(["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.py"), f"{R.WORK}/bed.wav", str(total + 1)], check=True)
    scenes = R.scenes_from(starts, durs, total); words = R.word_timeline(starts, durs)
    print("total", round(total, 2), [(k, round(a, 1)) for k, a, _ in scenes])
    if len(sys.argv) > 2:
        for tt in map(float, sys.argv[2:]): make_frame(tt, scenes, words, total).save(f"{R.WORK}/frame_{tt:05.2f}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", f"{R.TTS}/voice.wav", "-i", f"{R.WORK}/bed.wav",
                          "-filter_complex", R.audio_graph(scenes), "-map", "0:v", "-map", "[a]", "-t", str(total),
                          "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                          "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(total * FPS)): p.stdin.write(make_frame(i / FPS, scenes, words, total).tobytes())
    p.stdin.close(); sys.exit(p.wait())
