# -*- coding: utf-8 -*-
"""
כלי כתוביות בעברית - שרת מקומי.

הרצה:  python3 app.py    ואז   http://localhost:8769

התצוגה החיה רצה בדפדפן (מהיר, בלי רינדור), והייצוא הסופי רץ ב-PIL
עם אותם פריסטים בדיוק, כדי שמה שרואים הוא מה שמקבלים.
"""
import os, json, uuid, subprocess, shutil, tempfile, threading
from flask import Flask, request, jsonify, send_from_directory, Response

import styles
from caption_render import render_caption
import transcribe as tx

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "work")
OUT = os.path.join(ROOT, "output")
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

BUILD = "2026-08-27e"      # מזהה גרסה, כדי לזהות שרת שרץ עם קוד ישן
THEMES_FILE = os.path.join(ROOT, "themes.json")

app = Flask(__name__, static_folder=None)
JOBS = {}


# ── ffmpeg ───────────────────────────────────────────────────────────────
# מעדיפים ffmpeg של המערכת אם יש, אחרת משתמשים בבינארי הסטטי
# ש-imageio-ffmpeg מביא איתו. ככה אין צורך ב-Homebrew בכלל.
def _ffmpeg():
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


FFMPEG = _ffmpeg()


def probe(path):
    """
    מטא-דאטה של הווידאו. אם יש ffprobe במערכת משתמשים בו,
    ואחרת קוראים את זה דרך imageio-ffmpeg, שלא דורש ffprobe.
    """
    if shutil.which("ffprobe"):
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate",
             "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True, text=True, check=True)
        j = json.loads(r.stdout)
        st = j["streams"][0]
        num, den = st["r_frame_rate"].split("/")
        return {"w": st["width"], "h": st["height"],
                "fps": float(num) / float(den),
                "dur": float(j["format"]["duration"])}

    import imageio_ffmpeg
    gen = imageio_ffmpeg.read_frames(path)
    try:
        m = next(gen)
    finally:
        gen.close()
    w, h = m["size"]
    return {"w": int(w), "h": int(h),
            "fps": float(m["fps"]),
            "dur": float(m["duration"])}


# ── עמודים ───────────────────────────────────────────────────────────────
@app.get("/")
def index():
    with open(os.path.join(ROOT, "ui.html"), encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")


@app.get("/media/<path:name>")
def media(name):
    return send_from_directory(WORK, name)


@app.get("/out/<path:name>")
def outfile(name):
    return send_from_directory(OUT, name, as_attachment=True)


@app.get("/fonts/<path:name>")
def fontfile(name):
    return send_from_directory(os.path.join(ROOT, "fonts"), name)


@app.get("/api/version")
def version():
    return jsonify({"build": BUILD})


@app.get("/api/fonts")
def fonts_list():
    return jsonify(styles.list_fonts())


@app.get("/api/presets")
def presets():
    return jsonify(styles.preset_json())


# ── ערכות נושא שמורות ────────────────────────────────────────────────────
# פריסט הוא נקודת פתיחה קבועה שמגיעה עם הכלי. ערכה היא מה שאתה שומר
# בעצמך אחרי שעיצבת. נשמר ל-themes.json ליד הכלי, כך שזה שורד הפעלה מחדש
# ועובר איתך אם תעתיק את התיקייה למחשב אחר.
def _read_themes():
    try:
        with open(THEMES_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_themes(d):
    tmp = THEMES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, THEMES_FILE)      # כתיבה אטומית, לא משאירה קובץ חצי


@app.get("/api/themes")
def themes_get():
    return jsonify(_read_themes())


@app.post("/api/themes")
def themes_save():
    d = request.json or {}
    name = (d.get("name") or "").strip()
    style = d.get("style")
    if not name:
        return jsonify({"error": "חסר שם לערכה"}), 400
    if not isinstance(style, dict):
        return jsonify({"error": "חסר סגנון לשמירה"}), 400

    all_ = _read_themes()
    existed = name in all_
    style = dict(style)
    style["label"] = name
    style["hint"] = d.get("hint") or "ערכה שלך"
    style["saved"] = True
    all_[name] = style
    _write_themes(all_)
    return jsonify({"ok": True, "name": name, "overwritten": existed,
                    "themes": all_})


@app.post("/api/themes/delete")
def themes_delete():
    name = (request.json or {}).get("name")
    all_ = _read_themes()
    if name in all_:
        del all_[name]
        _write_themes(all_)
    return jsonify({"ok": True, "themes": all_})


# ── ניהול שטח ────────────────────────────────────────────────────────────
# work/ מחזיקה את הסרטונים שהעלית, output/ את הסרטונים המיוצאים.
# אלה לא קבצי קאש: אם תמחק אותם הכלי לא יאט, פשוט לא תוכל
# להוריד שוב ייצוא ישן או לחזור לסרטון שהעלית קודם.
def _scan(folder):
    items = []
    for n in os.listdir(folder):
        p = os.path.join(folder, n)
        if os.path.isfile(p) and not n.startswith("."):
            st = os.stat(p)
            items.append({"name": n, "bytes": st.st_size, "mtime": st.st_mtime})
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


@app.get("/api/storage")
def storage():
    w, o = _scan(WORK), _scan(OUT)
    return jsonify({
        "work": {"n": len(w), "bytes": sum(x["bytes"] for x in w), "files": w},
        "output": {"n": len(o), "bytes": sum(x["bytes"] for x in o), "files": o},
        "total_bytes": sum(x["bytes"] for x in w) + sum(x["bytes"] for x in o),
    })


@app.post("/api/cleanup")
def cleanup():
    """
    scope="old"  מוחק הכל חוץ מהסרטון שפתוח כרגע (keep) ומהייצוא האחרון
    scope="all"  מוחק את שתי התיקיות במלואן
    """
    d = request.json or {}
    scope = d.get("scope", "old")
    keep = d.get("keep")
    freed = n = 0

    work = _scan(WORK)
    out = _scan(OUT)
    doomed = []

    if scope == "all":
        doomed = [(WORK, f) for f in work] + [(OUT, f) for f in out]
    else:
        doomed = [(WORK, f) for f in work if f["name"] != keep]
        doomed += [(OUT, f) for f in out[1:]]      # שומרים את הייצוא האחרון

    for folder, f in doomed:
        try:
            os.remove(os.path.join(folder, f["name"]))
            freed += f["bytes"]
            n += 1
        except OSError:
            pass
    return jsonify({"deleted": n, "freed": freed})


# ── העלאה ────────────────────────────────────────────────────────────────
@app.post("/api/upload")
def upload():
    f = request.files.get("video")
    if not f:
        return jsonify({"error": "לא הועלה קובץ"}), 400
    vid = uuid.uuid4().hex[:10]
    ext = os.path.splitext(f.filename)[1] or ".mp4"
    path = os.path.join(WORK, vid + ext)
    f.save(path)
    try:
        meta = probe(path)
    except Exception as e:
        return jsonify({"error": f"קובץ וידאו לא תקין: {e}"}), 400
    meta.update({"id": vid, "file": os.path.basename(path)})
    return jsonify(meta)


# ── תמלול ────────────────────────────────────────────────────────────────
@app.post("/api/transcribe")
def do_transcribe():
    d = request.json
    path = os.path.join(WORK, d["file"])
    mode = d.get("mode", "auto")
    try:
        heard, detected = tx.transcribe_words(path, d.get("language", "he"))
    except ImportError:
        return jsonify({"error": "faster-whisper לא מותקן. הרץ: pip install faster-whisper"}), 500
    except Exception as e:
        return jsonify({"error": f"התמלול נכשל: {e}"}), 500

    words = tx.align_pasted(d["text"], heard) if (mode == "paste" and d.get("text", "").strip()) else heard
    words, removed = tx.strip_fillers(words, enabled=bool(d.get("strip_fillers", True)))
    words, marked = tx.mark_emphasis(words)
    sil = tx.find_silences(words)
    caps = tx.group_into_captions(words, max_words=int(d.get("max_words", 4)))
    return jsonify({"words": words, "captions": caps,
                    "removed_fillers": removed, "marked": marked,
                    "silences": sil, "detected": detected})


# ── ייצוא ────────────────────────────────────────────────────────────────
def build_states(captions, fps, dur):
    """
    ממיר את הכתוביות לרצף מצבים: (רשימת מילים, אינדקס מילה פעילה, פריים התחלה, פריים סוף).
    מצב = כתובית מסוימת עם מילה מודגשת מסוימת.
    """
    states = []
    for c in captions:
        for i, (s, e) in enumerate(c["times"]):
            f0, f1 = int(round(s * fps)), int(round(e * fps))
            if f1 <= f0:
                f1 = f0 + 1
            states.append((c["words"], i, f0, f1, tuple(c.get("emph") or [])))
    return states


def export_job(job, file, captions, style, meta):
    try:
        preset = style
        stack = styles.FONT_STACKS.get(preset.get("font"), styles.FONT_STACKS["rubik_black"])
        W, H, fps = meta["w"], meta["h"], meta["fps"]
        total = int(round(meta["dur"] * fps))
        tmp = tempfile.mkdtemp(prefix="hebcap_")
        JOBS[job]["stage"] = "מרנדר כתוביות"

        blank = None
        cache = {}
        states = build_states(captions, fps, meta["dur"])
        # מפה מפריים -> מצב
        frame_state = {}
        for words, ai, f0, f1, em in states:
            for f in range(max(0, f0), min(total, f1)):
                frame_state[f] = (tuple(words), ai, em)

        for f in range(total):
            key = frame_state.get(f)
            if key is None:
                if blank is None:
                    from PIL import Image
                    blank = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    blank.save(os.path.join(tmp, "_blank.png"))
                shutil.copyfile(os.path.join(tmp, "_blank.png"), os.path.join(tmp, f"{f:06d}.png"))
            else:
                if key not in cache:
                    img = render_caption((W, H), list(key[0]), key[1], preset, stack, emph=list(key[2]))
                    cpath = os.path.join(tmp, f"s_{len(cache):05d}.png")
                    img.save(cpath)
                    cache[key] = cpath
                shutil.copyfile(cache[key], os.path.join(tmp, f"{f:06d}.png"))
            if f % 60 == 0:
                JOBS[job]["pct"] = int(f / max(1, total) * 70)

        JOBS[job]["stage"] = "צורב לווידאו"
        JOBS[job]["pct"] = 75
        outname = f"captioned_{job}.mp4"
        outpath = os.path.join(OUT, outname)
        subprocess.run(
            [FFMPEG, "-v", "error", "-i", os.path.join(WORK, file),
             "-framerate", str(fps), "-i", os.path.join(tmp, "%06d.png"),
             "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1,format=yuv420p",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-c:a", "copy", outpath, "-y"], check=True)
        shutil.rmtree(tmp, ignore_errors=True)
        JOBS[job].update({"pct": 100, "stage": "מוכן", "done": True, "url": f"/out/{outname}"})
    except Exception as e:
        JOBS[job].update({"error": str(e), "done": True})


@app.post("/api/export")
def export():
    d = request.json
    job = uuid.uuid4().hex[:8]
    JOBS[job] = {"pct": 0, "stage": "מתחיל", "done": False}
    meta = probe(os.path.join(WORK, d["file"]))
    threading.Thread(target=export_job,
                     args=(job, d["file"], d["captions"], d["style"], meta),
                     daemon=True).start()
    return jsonify({"job": job})


@app.get("/api/export/<job>")
def export_status(job):
    return jsonify(JOBS.get(job, {"error": "לא נמצא"}))


if __name__ == "__main__":
    print("\n  כלי כתוביות בעברית")
    print("  http://localhost:8769\n")
    app.run(port=8769, debug=False, threaded=True)
