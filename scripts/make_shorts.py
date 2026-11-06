#!/usr/bin/env python3
"""
make_shorts.py - turn a clip plan (JSON) into ready-to-upload YouTube Shorts.

For every clip in the plan it:
  1. downloads the source episode and its Spanish auto-captions once (yt-dlp),
     or uses local files given with --source / --subs
  2. snaps the cut points to word boundaries and cuts the clip
     (a clip may have several segments; they are joined with a jump cut)
  3. reframes 16:9 to 9:16 (1080x1920):
       face   - full-screen crop that follows the speaker's face (default, needs opencv)
       center - plain centre crop
       blur   - the episode in the middle over a blurred copy
  4. burns the style that top Spanish podcast Shorts use (docs/shorts-style-research.md):
     1-2 word captions with the spoken word highlighted, a big headline for the
     first seconds, a brand tag and a credit line; optional quiet background music
  5. writes the YouTube title, description, hashtags and pinned comment

Examples:
  python scripts/make_shorts.py clips/roca-project-114.json
  python scripts/make_shorts.py clips/roca-project-114.json --only 01 04
  python scripts/make_shorts.py clips/roca-project-114.json --reframe face
  python scripts/make_shorts.py clips/roca-project-114.json --source ep.mp4 --subs ep.es.json3
  python scripts/make_shorts.py --selftest
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
W, H = 1080, 1920

FONT_CAPTION = "Montserrat Black"
FONT_HOOK = "Montserrat ExtraBold"
FONT_CREDIT = "Montserrat SemiBold"
FONT_HEADLINE = "Anton"

VERBOSE = False


# --------------------------------------------------------------------------- utils

def die(msg):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, cwd=None):
    if VERBOSE:
        print("   $", " ".join(str(c) for c in cmd))
    res = subprocess.run([str(c) for c in cmd], cwd=cwd,
                         stdout=None if VERBOSE else subprocess.PIPE,
                         stderr=None if VERBOSE else subprocess.PIPE, text=True)
    if res.returncode != 0:
        tail = (res.stderr or "")[-3000:]
        die(f"command failed ({res.returncode}): {cmd[0]} ...\n{tail}")
    return res


def parse_time(value):
    """'56:32.0' / '1:02:03.5' / 75.2 -> seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    total = 0.0
    for part in str(value).strip().split(":"):
        total = total * 60 + float(part)
    return total


def fmt_clock(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:04.1f}"


def ass_time(t):
    cs = int(round(max(0.0, t) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_color(hex_rgb):
    """'#FFE500' -> '&H00E5FF&' (inline ASS colours are &HBBGGRR&)."""
    h = hex_rgb.lstrip("#").upper()
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&"


def ass_text(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def even(x):
    return int(round(x / 2.0)) * 2


def video_id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


# --------------------------------------------------------------------------- tools

def ytdlp_cmd():
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        exe = shutil.which("yt-dlp")
        if exe:
            return [exe]
    die("yt-dlp is not installed. Run:  pip install -U yt-dlp")


def check_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        die("ffmpeg/ffprobe not found. Install ffmpeg (see README).")
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                         capture_output=True, text=True).stdout
    if not re.search(r"^\s*\S+\s+ass\s", out, re.M):
        die("this ffmpeg was built without libass, so it cannot burn captions.\n"
            "macOS: brew install ffmpeg-full   Windows: use the 'full' build from gyan.dev")


def probe_size(src):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "json", src]).stdout
    st = json.loads(out)["streams"][0]
    return int(st["width"]), int(st["height"])


# --------------------------------------------------------------------------- download

VIDEO_FORMAT = (
    # many episodes carry YouTube AI-dubbed audio tracks (English, Portuguese...):
    # always take the ORIGINAL-language audio; prefer H.264 video (fast to decode)
    "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a][format_note*=original]/"
    "bv*[height<=1080][vcodec^=avc1]+ba[format_note*=original]/"
    "bv*[height<=1080]+ba[format_note*=original]/"
    "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b")

def ytdlp_base(extra_args):
    base = ytdlp_cmd()
    if not shutil.which("deno") and shutil.which("node") and "--js-runtimes" not in extra_args:
        base += ["--js-runtimes", "node"]     # yt-dlp needs a JS runtime for YouTube
    return base


def ytdlp_try(args, extra_args):
    res = subprocess.run(ytdlp_base(extra_args) + extra_args + args, capture_output=True, text=True)
    if res.returncode != 0 and "not a bot" in res.stderr:
        print("   YouTube asked to confirm you are not a bot. Run this on your own computer, or pass your\n"
              "   browser login:  --ytdlp-arg=--cookies-from-browser --ytdlp-arg=chrome")
    return res


def download_source(url, work, extra_args):
    vid = video_id(url)
    if not vid:
        die(f"cannot read a YouTube video id from {url}")
    work.mkdir(parents=True, exist_ok=True)
    outtmpl = str(work / "%(id)s.%(ext)s")

    video = work / f"{vid}.mp4"
    if not video.exists():
        print(f"-> downloading episode {vid} (once, then cached in {work})")
        res = ytdlp_try(["-f", VIDEO_FORMAT, "--merge-output-format", "mp4", "-o", outtmpl, url], extra_args)
        if res.returncode != 0:
            die("yt-dlp could not download the episode:\n" + res.stderr[-1500:])
    subs = find_subs(work, vid)
    if subs is None:
        print("-> downloading Spanish auto-captions (word timings)")
        res = ytdlp_try(["--skip-download", "--write-auto-subs", "--sub-langs", "es-orig,es",
                         "--sub-format", "json3", "-o", outtmpl, url], extra_args)
        if res.returncode != 0:
            print("   (captions download failed - use --whisper for captions)\n" + res.stderr[-800:])
        subs = find_subs(work, vid)
    if not video.exists():
        die(f"download finished but {video} is missing")
    return video, subs


def find_subs(work, vid):
    for name in (f"{vid}.es-orig.json3", f"{vid}.es.json3"):
        if (work / name).exists():
            return work / name
    return None


# --------------------------------------------------------------------------- words

@dataclass
class Word:
    start: float
    end: float
    text: str


BRACKETS = re.compile(r"\[[^\]]*\]")


def load_json3_words(path):
    """YouTube json3 captions -> list of Word on the episode timeline.
    Auto-generated (ASR) tracks carry a time offset for every word."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = []  # (start, token, event_end)
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        t0 = ev.get("tStartMs", 0) / 1000.0
        ev_end = t0 + ev.get("dDurationMs", 0) / 1000.0
        items = []
        for sg in segs:
            toks = BRACKETS.sub(" ", sg.get("utf8", "")).split()
            if toks:
                items.append((t0 + sg.get("tOffsetMs", 0) / 1000.0, toks))
        for i, (st, toks) in enumerate(items):
            nxt = items[i + 1][0] if i + 1 < len(items) else max(ev_end, st + 0.3 * len(toks))
            span = max(nxt - st, 0.05)
            for k, tok in enumerate(toks):
                raw.append((st + span * k / len(toks), tok, ev_end))
    raw.sort(key=lambda r: r[0])
    words = []
    for i, (st, tok, ev_end) in enumerate(raw):
        nxt = raw[i + 1][0] if i + 1 < len(raw) else st + 1.0
        natural = st + max(0.3, 0.085 * len(tok)) + 0.25
        end = max(st + 0.08, min(nxt, natural))
        words.append(Word(st, end, tok))
    return words


def whisper_words(audio_path, model_name):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("--whisper needs faster-whisper:  pip install faster-whisper")
    print(f"   transcribing with faster-whisper '{model_name}' ...")
    model = WhisperModel(model_name, device="auto", compute_type="int8")
    segments, _ = model.transcribe(str(audio_path), language="es", word_timestamps=True,
                                   vad_filter=True, condition_on_previous_text=False)
    words = []
    for seg in segments:
        for w in seg.words or []:
            txt = BRACKETS.sub(" ", w.word).strip()
            if txt:
                words.append(Word(float(w.start), float(w.end), txt))
    return words


def norm(token):
    t = unicodedata.normalize("NFKD", token.lower())
    return "".join(ch for ch in t if ch.isalnum())


def find_word(words, token, near, before, after):
    """Index of the word equal to `token` whose start is closest to `near`."""
    key = norm(token)
    best = None
    for i, w in enumerate(words):
        if near - before <= w.start <= near + after and norm(w.text) == key:
            if best is None or abs(w.start - near) < abs(words[best].start - near):
                best = i
    return best


def snap_segment(seg, words):
    """Turn a plan segment into (start, end) seconds.

    A segment is ["56:32.0", "57:24.0"] or
    {"start": "56:32.0", "end": "57:24.0", "start_at": "yo", "end_after": "sea"}.
    With word timings, start_at/end_after move the cut exactly onto that word
    (the occurrence closest to the given time), and a cut that would fall in
    the middle of a word is moved so the word stays whole."""
    if isinstance(seg, dict):
        a, b = parse_time(seg["start"]), parse_time(seg["end"])
        start_at, end_after = seg.get("start_at"), seg.get("end_after")
    else:
        a, b = parse_time(seg[0]), parse_time(seg[1])
        start_at = end_after = None
    if not words:
        return a, b

    if start_at:
        i = find_word(words, start_at, a, 2.5, 3.0)
        if i is None:
            print(f"   note: start word '{start_at}' not found near {fmt_clock(a)}")
        else:
            prev_end = words[i - 1].end if i > 0 else 0.0
            a = max(words[i].start - 0.10, min(prev_end, words[i].start - 0.02))
    else:
        for i, w in enumerate(words):
            if w.start < a < w.end:          # cut inside a word
                if a - w.start <= 0.25:
                    prev_end = words[i - 1].end if i > 0 else 0.0
                    a = max(w.start - 0.08, min(prev_end, w.start - 0.02))
                elif i + 1 < len(words):
                    a = words[i + 1].start - 0.08
                break

    if end_after:
        i = find_word(words, end_after, b, 4.0, 2.0)
        if i is None:
            print(f"   note: end word '{end_after}' not found near {fmt_clock(b)}")
        else:
            nxt = words[i + 1].start if i + 1 < len(words) else words[i].end + 1.0
            b = min(words[i].end + 0.15, nxt - 0.02)
    else:
        for i, w in enumerate(words):
            if w.start < b < w.end:          # cut inside a word: finish it
                nxt = words[i + 1].start if i + 1 < len(words) else w.end + 1.0
                b = min(w.end + 0.12, nxt - 0.02)
                break
    if b - a < 1.0:
        die(f"segment {seg} is shorter than 1 s after snapping - check its words/times")
    return a, b


def localize(words, segments):
    """Episode-timeline words -> clip-timeline words for the joined segments."""
    out, offset = [], 0.0
    for a, b in segments:
        for w in words:
            if a - 0.05 <= w.start < b - 0.05:
                out.append(Word(w.start - a + offset, min(w.end, b) - a + offset, w.text))
        offset += b - a
    return out


# --------------------------------------------------------------------------- face tracking

def face_crop_expr(src, segments, scaled_w, step=0.25):
    """Piecewise-constant crop x (in the scaled 1920-high frame) that follows the
    largest face. Returns an ffmpeg expression of t, or None if opencv is missing."""
    try:
        import cv2
    except ImportError:
        print("   (opencv not installed - using centre crop; pip install opencv-python-headless)")
        return None
    names = ["haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"]
    cascades = [cv2.CascadeClassifier(cv2.data.haarcascades + n) for n in names]
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    every = max(1, int(round(fps * step)))
    samples, offset = [], 0.0
    for a, b in segments:
        cap.set(cv2.CAP_PROP_POS_MSEC, a * 1000.0)
        n = int((b - a) * fps)
        for i in range(n):
            if i % every:
                if not cap.grab():
                    break
                continue
            ok, frame = cap.read()
            if not ok:
                break
            samples.append((offset + i / fps, largest_face_cx(cv2, cascades, frame)))
        offset += b - a
    cap.release()
    if not samples or all(c is None for _, c in samples):
        return None

    xs = [c for _, c in samples]
    last = next(c for c in xs if c is not None)
    for i, c in enumerate(xs):          # fill gaps with the previous position
        xs[i] = last = c if c is not None else last
    smooth = []
    for i in range(len(xs)):            # median of 5 removes single false detections
        win = sorted(xs[max(0, i - 2): i + 3])
        smooth.append(win[len(win) // 2])

    cuts = [(0.0, smooth[0])]
    pending = None
    for i in range(1, len(smooth)):
        if abs(smooth[i] - cuts[-1][1]) > 0.07:
            if pending is None:
                pending = i
            elif i - pending >= 1:
                vals = sorted(smooth[pending:i + 1])
                cuts.append((samples[pending][0], vals[len(vals) // 2]))
                pending = None
        else:
            pending = None

    def px(cx):
        return int(min(max(cx * scaled_w - W / 2, 0), scaled_w - W))

    expr = str(px(cuts[-1][1]))
    for i in range(len(cuts) - 2, -1, -1):
        expr = f"if(lt(t,{cuts[i + 1][0]:.2f}),{px(cuts[i][1])},{expr})"
    return expr


def largest_face_cx(cv2, cascades, frame):
    h, w = frame.shape[:2]
    sw = 960
    small = cv2.resize(frame, (sw, int(h * sw / w)))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    min_side = max(30, gray.shape[0] // 16)
    found = []
    for k, c in enumerate(cascades):
        for x, y, fw, fh in c.detectMultiScale(gray, 1.1, 6, minSize=(min_side, min_side)):
            found.append((x, fw, fh))
        if k == 1:  # profile cascade only sees one side: run it mirrored too
            for x, y, fw, fh in c.detectMultiScale(cv2.flip(gray, 1), 1.1, 6, minSize=(min_side, min_side)):
                found.append((sw - x - fw, fw, fh))
    if not found:
        return None
    x, fw, fh = max(found, key=lambda f: f[1] * f[2])
    return (x + fw / 2) / sw


# --------------------------------------------------------------------------- captions (ASS)

def paginate(words, max_words, max_chars, max_gap=0.6):
    pages, cur = [], []
    for w in words:
        if cur:
            length = sum(len(x.text) + 1 for x in cur) + len(w.text)
            prev = cur[-1].text
            if (len(cur) >= max_words or length > max_chars or w.start - cur[-1].end > max_gap
                    or re.search(r"[.?!…]$", prev) or (prev.endswith(",") and len(cur) >= 2)):
                pages.append(cur)
                cur = []
        cur.append(w)
    if cur:
        pages.append(cur)
    return pages


def style_color(hex_rgb, alpha=0):
    """'#FFE500' -> '&H0000E5FF' for the [V4+ Styles] section (&HAABBGGRR)."""
    h = hex_rgb.lstrip("#").upper()
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}"


def headline_text(text, accent):
    """'LE CRECIÓ | UNA *PLANTA*' -> ASS text: *marked* words in the accent colour, | = new line."""
    out, on = [], False
    text = ass_text(text).replace(" | ", "|").replace("|", "\\N")   # "|" = line break
    for part in re.split(r"(\*)", text):
        if part == "*":
            on = not on
            out.append(f"{{\\1c{accent}}}" if on else "{\\1c&HFFFFFF&}")
        else:
            out.append(part)
    return "".join(out)


def build_ass(words, duration, hook, credit, brand, layout, style):
    """Captions + headline + brand tag + credit, in the style of the Spanish podcast Shorts
    that perform best (see docs/shorts-style-research.md):
      - captions: 1-2 words at a time, big heavy uppercase, a small pop when a new group
        appears, the spoken word in the accent colour, placed on the chest (~62% of the height)
      - headline: huge condensed text with an accent keyword for the first seconds (it is
        also what the feed shows as the first frame)
      - small brand tag top-left and a credit line to the original podcast"""
    upper = style.get("caption_uppercase", True)
    accent = style.get("highlight", "#FFE500")
    hi = ass_color(accent) if accent else None
    white = ass_color("#FFFFFF")
    cap_font = style.get("caption_font", FONT_CAPTION)
    cap_size = style.get("caption_size", 100)
    head_font = style.get("headline_font", FONT_HEADLINE)
    head_size = style.get("headline_size", 170)
    head_secs = float(style.get("headline_seconds", 3.0))
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Caption,{cap_font},{cap_size},&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H64000000,0,0,0,0,100,100,1,0,1,7,4,5,80,80,0,1",
        f"Style: Headline,{head_font},{head_size},&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H50000000,0,0,0,0,100,100,1,0,1,8,6,5,70,70,0,1",
        f"Style: Brand,{FONT_HOOK},34,&H00101010,&H00101010,{style_color(accent or '#FFE500')},"
        "&H00000000,0,0,0,0,100,100,1,0,3,10,0,7,0,0,0,1",
        f"Style: Credit,{FONT_CREDIT},32,&H30FFFFFF,&H30FFFFFF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,1,0,1,2,1,7,0,0,0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    end_all = ass_time(duration)
    if brand:
        lines.append(f"Dialogue: 3,0:00:00.00,{end_all},Brand,,0,0,0,,"
                     f"{{\\an7\\pos(64,{layout['brand_y']})}}{ass_text(brand.upper())}")
    if credit:
        lines.append(f"Dialogue: 3,0:00:00.00,{end_all},Credit,,0,0,0,,"
                     f"{{\\an7\\pos(64,{layout['credit_y']})}}{ass_text(credit)}")
    if hook:
        text = headline_text(hook.upper(), ass_color(accent or "#FFE500"))
        if layout["headline_always"]:
            lines.append(f"Dialogue: 2,0:00:00.00,{end_all},Headline,,0,0,0,,"
                         f"{{\\an2\\pos(540,{layout['headline_y']})\\fs{int(head_size * 0.72)}}}{text}")
        else:
            lines.append(f"Dialogue: 2,0:00:00.00,{ass_time(min(head_secs, duration))},Headline,,0,0,0,,"
                         f"{{\\an5\\pos(540,{layout['headline_y']})\\fad(0,200)}}{text}")

    pages = paginate(words, style.get("caption_max_words", 2), style.get("caption_max_chars", 16))
    for p, page in enumerate(pages):
        nxt = pages[p + 1][0].start if p + 1 < len(pages) else duration
        page_end = min(page[-1].end + 0.25, nxt, duration)
        toks = [ass_text(w.text.upper() if upper else w.text) for w in page]
        for i, w in enumerate(page):
            s = w.start
            e = page[i + 1].start if i + 1 < len(page) else page_end
            if e - s < 0.02:
                continue
            if hi:
                body = " ".join(f"{{\\1c{hi}}}{t}{{\\1c{white}}}" if j == i else t
                                for j, t in enumerate(toks))
            else:
                body = " ".join(toks)
            pop = "\\fscx88\\fscy88\\t(0,90,\\fscx100\\fscy100)" if i == 0 else ""
            lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Caption,,0,0,0,,"
                         f"{{\\an5\\pos(540,{layout['caption_y']}){pop}}}{body}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- render

def layout_for(reframe, src_w, src_h, zoom):
    if reframe == "blur":
        fg_w = even(W * zoom)
        fg_h = min(H, even(fg_w * src_h / src_w))
        top = (H - fg_h) // 2
        bottom = top + fg_h
        return dict(fg_w=fg_w, fg_h=fg_h, headline_always=True, headline_y=top - 40,
                    brand_y=150, credit_y=bottom + 18, caption_y=min(bottom + 200, 1560))
    # full-screen 9:16, like every top-performing Short we looked at
    return dict(headline_always=False, headline_y=600, brand_y=150, credit_y=212, caption_y=1190)


def render_clip(src, segments, ass_path, out_path, reframe, layout, crop_expr, fonts_rel, fast,
                music=None, music_volume=0.12):
    n = len(segments)
    duration = sum(b - a for a, b in segments)
    inputs = []
    for a, b in segments:
        inputs += ["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(src)]
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
    fg = []
    if n > 1:
        fg.append("".join(f"[{i}:v:0][{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=1:a=1[cv][ca]")
    else:
        fg.append("[0:v:0]null[cv]")
        fg.append("[0:a:0]anull[ca]")
    if reframe == "blur":
        fg.append("[cv]split=2[bgsrc][fgsrc]")
        fg.append(f"[bgsrc]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
                  f"boxblur=10:2,scale={W}:{H},eq=brightness=-0.12:saturation=1.1[bg]")
        crop = f",crop={W}:ih" if layout["fg_w"] > W else ""
        fg.append(f"[fgsrc]scale={layout['fg_w']}:{layout['fg_h']}{crop}[fg]")
        fg.append("[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[rv]")
    elif reframe == "face" and crop_expr:
        fg.append(f"[cv]scale=-2:{H},crop={W}:{H}:x='{crop_expr}':y=0,setsar=1[rv]")
    else:
        fg.append(f"[cv]scale=-2:{H},crop={W}:{H},setsar=1[rv]")
    sub = f"ass=filename={ass_path.name}" + (f":fontsdir={fonts_rel}" if fonts_rel else "")
    fg.append(f"[rv]{sub}[vout]")
    voice = "[ca]"
    if music:   # quiet emotional bed under the voice, as CastClips and others do
        fg.append(f"[{n}:a:0]atrim=0:{duration:.3f},volume={music_volume},afade=t=in:d=1,"
                  f"afade=t=out:st={max(0.0, duration - 1.5):.3f}:d=1.5[mus]")
        fg.append("[ca][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]")
        voice = "[mix]"
    fg.append(f"{voice}afade=t=in:d=0.06,afade=t=out:st={max(0.0, duration - 0.2):.3f}:d=0.2,"
              "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    preset, crf = ("ultrafast", "26") if fast else ("medium", "18")
    cmd = ["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex", ";".join(fg),
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out_path.name]
    run(cmd, cwd=out_path.parent)


def extract_audio(src, segments, wav):
    inputs = []
    for a, b in segments:
        inputs += ["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(src)]
    n = len(segments)
    graph = "".join(f"[{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    run(["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex", graph, "-map", "[a]",
         "-ac", "1", "-ar", "16000", str(wav)])


# --------------------------------------------------------------------------- metadata

def write_metadata(plan, clip, folder):
    tags = []
    for t in clip.get("hashtags", []) + plan.get("default_hashtags", []):
        if t not in tags:
            tags.append(t)
    title = clip["title"]
    if len(title) > 100:
        print(f"   WARNING: title is {len(title)} chars (YouTube max 100)")
    desc = clip.get("description", "").strip()
    if clip.get("pinned_comment"):          # the question for the comments goes in the description too
        desc += "\n\n" + clip["pinned_comment"].strip()
    if plan.get("description_footer"):
        desc += "\n\n" + plan["description_footer"].strip()
    if tags:
        desc += "\n\n" + " ".join(tags)
    text = (f"TÍTULO ({len(title)}/100):\n{title}\n\nDESCRIPCIÓN:\n{desc}\n\n"
            f"COMENTARIO FIJADO:\n{clip.get('pinned_comment', '')}\n")
    (folder / "youtube.txt").write_text(text, encoding="utf-8")
    return title, desc


# --------------------------------------------------------------------------- main flow

def process_plan(plan, args):
    style = plan.get("style", {})
    out_root = Path(args.out).resolve() / plan.get("name", "plan")
    out_root.mkdir(parents=True, exist_ok=True)

    if args.source:
        src = Path(args.source).resolve()
        subs = Path(args.subs).resolve() if args.subs else None
    else:
        url = plan.get("source", {}).get("url")
        if not url:
            die("plan has no source.url - pass --source")
        src, subs = download_source(url, Path(args.work).resolve(), args.ytdlp_arg or [])

    words = load_json3_words(subs) if subs and subs.exists() else []
    if not words and not args.whisper and not args.no_captions:
        print("   WARNING: no captions with word timings - clips will have no subtitles (try --whisper)")
    src_w, src_h = probe_size(src)

    fonts_rel = None
    if FONTS_DIR.is_dir() and any(FONTS_DIR.glob("*.ttf")):
        dst = out_root / "_fonts"
        dst.mkdir(exist_ok=True)
        for f in FONTS_DIR.glob("*.ttf"):
            shutil.copy2(f, dst / f.name)
        fonts_rel = "../_fonts"

    clips = plan["clips"]
    if args.only:
        clips = [c for c in clips if any(c["id"].startswith(o) for o in args.only)]
        if not clips:
            die(f"no clip id starts with {args.only}")

    sheet = [f"# {plan.get('name')} - upload sheet\n"]
    for idx, clip in enumerate(clips, 1):
        cid = clip["id"]
        print(f"\n[{idx}/{len(clips)}] {cid}")
        folder = out_root / cid
        folder.mkdir(parents=True, exist_ok=True)

        segments = [snap_segment(seg, [] if args.no_snap else words) for seg in clip["segments"]]
        duration = sum(b - a for a, b in segments)
        print("   cut:", ", ".join(f"{fmt_clock(a)}-{fmt_clock(b)}" for a, b in segments),
              f"({duration:.1f}s)")
        if duration > 60:
            print("   note: longer than 60 s (Shorts allow up to 3 min)")

        ass = folder / f"{cid}.ass"
        reuse = args.keep_subs and ass.exists()
        local = []
        if not args.no_captions and not reuse:
            if args.whisper:
                with tempfile.TemporaryDirectory() as tmp:
                    wav = Path(tmp) / "a.wav"
                    extract_audio(src, segments, wav)
                    local = whisper_words(wav, args.whisper)
            else:
                local = localize(words, segments)

        reframe = args.reframe or clip.get("reframe") or plan.get("reframe") or "face"
        zoom = float(args.zoom or clip.get("zoom") or plan.get("zoom") or 1.0)
        layout = layout_for(reframe, src_w, src_h, zoom)
        crop_expr = None
        if reframe == "face":
            crop_expr = face_crop_expr(src, segments, even(H * src_w / src_h))

        if reuse:
            print(f"   using your edited {ass.name}")
        else:
            hook = None if args.no_hook else clip.get("hook")
            ass.write_text(build_ass(local, duration, hook, plan.get("credit"), plan.get("brand"),
                                     layout, style), encoding="utf-8")

        out = folder / f"{cid}.mp4"
        music = args.music or clip.get("music") or plan.get("music")
        if music:
            music = Path(music)
            if not music.exists() and args.plan:      # plan paths are relative to the plan file
                music = Path(args.plan).resolve().parent / music
            if not music.exists():
                die(f"music file not found: {music}")
        render_clip(src, segments, ass, out, reframe, layout, crop_expr, fonts_rel, args.fast,
                    music, float(args.music_volume or plan.get("music_volume") or 0.12))
        title, desc = write_metadata(plan, clip, folder)
        print(f"   OK -> {out}")
        sheet.append(f"## {cid}\n\n- file: `{cid}/{cid}.mp4` ({duration:.0f} s)\n"
                     f"- cut: {', '.join(f'{fmt_clock(a)}-{fmt_clock(b)}' for a, b in segments)}\n\n"
                     f"**Title:** {title}\n\n**Description:**\n\n```\n{desc}\n```\n\n"
                     f"**Pinned comment:** {clip.get('pinned_comment', '')}\n")
    (out_root / "UPLOAD_SHEET.md").write_text("\n".join(sheet), encoding="utf-8")
    print(f"\nDone. Videos and texts are in {out_root}")


def selftest(args):
    """Render a synthetic clip in every layout to check ffmpeg, libass and fonts."""
    tmp = Path(tempfile.mkdtemp(prefix="shorts-selftest-"))
    src = tmp / "episode.mp4"
    print(f"-> building a 20 s test episode in {tmp}")
    run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30:duration=20",
         "-f", "lavfi", "-i", "sine=frequency=330:duration=20", "-c:v", "libx264", "-preset", "ultrafast",
         "-c:a", "aac", "-shortest", str(src)])
    text = ("¿Qué hace un médico forense? Somos polvo de estrellas, eso nos tiene que quedar claro. "
            "Al que tengáis que besar, besarle hoy, porque ahora es el momento.").split()
    events, t = [], 2000
    for i in range(0, len(text), 4):
        chunk = text[i:i + 4]
        events.append({"tStartMs": t, "dDurationMs": 1800,
                       "segs": [{"utf8": (" " if k else "") + wd, "tOffsetMs": k * 420}
                                for k, wd in enumerate(chunk)]})
        t += 1800
    subs = tmp / "episode.es.json3"
    subs.write_text(json.dumps({"events": events}, ensure_ascii=False), encoding="utf-8")
    plan = {"name": "selftest", "credit": "ROCA PROJECT #114 · Borja Moreno", "brand": "Momentos Podcast",
            "clips": [{"id": f"t-{m}", "title": "Prueba #shorts", "hook": "No quiere que le *incineren*",
                       "reframe": m, "segments": [{"start": "0:01.5", "end": "0:08", "start_at": "qué"},
                                                  {"start": "0:10", "end": "0:16", "end_after": "momento"}]}
                      for m in ("blur", "face", "center")]}
    args.source, args.subs = str(src), str(subs)
    args.out = args.out if args.out != "output" else str(tmp / "out")
    process_plan(plan, args)


def main():
    global VERBOSE
    p = argparse.ArgumentParser(description="Clip plan (JSON) -> YouTube Shorts")
    p.add_argument("plan", nargs="?", help="clip plan, e.g. clips/roca-project-114.json")
    p.add_argument("--only", nargs="+", help="render only clips whose id starts with these (e.g. 01 04)")
    p.add_argument("--source", help="local episode video instead of downloading")
    p.add_argument("--subs", help="local YouTube json3 captions for --source")
    p.add_argument("--reframe", choices=["face", "center", "blur"],
                   help="9:16 layout (default: face = full screen following the speaker)")
    p.add_argument("--zoom", type=float, help="blur layout: enlarge the episode (1.0-1.6, crops the sides)")
    p.add_argument("--whisper", nargs="?", const="small", metavar="MODEL",
                   help="make captions with faster-whisper instead of YouTube captions (default model: small)")
    p.add_argument("--music", help="background music file mixed quietly under the voice")
    p.add_argument("--music-volume", type=float, help="music level, 0.05-0.25 (default 0.12)")
    p.add_argument("--no-captions", action="store_true", help="do not burn captions")
    p.add_argument("--no-hook", action="store_true", help="do not burn the hook title")
    p.add_argument("--no-snap", action="store_true", help="use the plan times exactly")
    p.add_argument("--keep-subs", action="store_true",
                   help="re-render with the existing <id>.ass (after you fixed typos in it)")
    p.add_argument("--fast", action="store_true", help="quick low-quality render for checking cuts")
    p.add_argument("--out", default="output", help="output folder (default: output)")
    p.add_argument("--work", default="work", help="download cache folder (default: work)")
    p.add_argument("--ytdlp-arg", action="append",
                   help="extra yt-dlp argument, repeatable (e.g. --ytdlp-arg=--cookies-from-browser --ytdlp-arg=chrome)")
    p.add_argument("--selftest", action="store_true", help="render a synthetic test clip and exit")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    VERBOSE = args.verbose

    check_ffmpeg()
    if args.selftest:
        selftest(args)
        return
    if not args.plan:
        p.error("give a clip plan JSON (or --selftest)")
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    process_plan(plan, args)


if __name__ == "__main__":
    main()
