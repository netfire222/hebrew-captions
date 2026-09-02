# -*- coding: utf-8 -*-
"""
תמלול עברית עם חותמות זמן ברמת מילה.

שני מצבים:
  1. auto  - faster-whisper מתמלל את הווידאו ומחזיר מילים עם זמנים
  2. paste - אתה מדביק את הטקסט המדויק, ואנחנו מיישרים אותו לזמנים
             שנמדדו מהאודיו. ככה מקבלים גם דיוק מוחלט בטקסט וגם תזמון אמיתי.

למה מצב paste קיים: whisper בעברית טועה בשמות מותגים ובמונחי AI
("קלוד קוד" הופך ל"קלאוד קוד", "/fork" נעלם). כשיש לך את התסריט ממילא,
עדיף להשתמש בו ולתת ל-whisper רק את התזמון.
"""
import os, shutil, subprocess, tempfile, difflib, re

MODEL_SIZE = os.environ.get("HEBCAP_MODEL", "large-v3")
_model = None


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # int8 על CPU נותן איזון טוב בין מהירות לדיוק במאק
        _model = WhisperModel(MODEL_SIZE, device="auto", compute_type="int8")
    return _model


def _ffmpeg():
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio(video_path):
    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        [_ffmpeg(), "-v", "error", "-i", video_path, "-vn",
         "-ac", "1", "-ar", "16000", "-f", "wav", wav, "-y"],
        check=True)
    return wav


def transcribe_words(video_path, language="he"):
    """
    מחזיר [{'w':str,'s':float,'e':float}] בסדר לוגי.

    language:
      "he"   - כופה עברית
      "en"   - כופה אנגלית
      "auto" - זיהוי אוטומטי. חשוב כשמדברים אנגלית, אחרת whisper
               כפוי-לעברית מתעתק "Claude Code" לאותיות עבריות.
    """
    model = _load()
    wav = extract_audio(video_path)
    lang = None if language in (None, "", "auto") else language
    try:
        segments, info = model.transcribe(
            wav, language=lang, word_timestamps=True,
            vad_filter=True, vad_parameters={"min_silence_duration_ms": 320},
            beam_size=5)
        words = []
        detected = getattr(info, "language", None)
        for seg in segments:
            for w in (seg.words or []):
                t = w.word.strip()
                if t:
                    words.append({"w": t, "s": round(w.start, 3), "e": round(w.end, 3)})
        return words, detected
    finally:
        try: os.remove(wav)
        except OSError: pass


# ── בחירת מנוע תמלול ─────────────────────────────────────────────────────
# מנוע ענן הוא תוסף אופציונלי שיושב ב-transcribe_el.py. אם הקובץ לא קיים,
# כמו בגרסה הציבורית, הכל ממשיך לעבוד מקומית בלי שום שינוי.
def _el():
    try:
        import transcribe_el
        return transcribe_el
    except ImportError:
        return None


def engines():
    """
    רשימת מנועי התמלול הזמינים, לבניית הבורר בממשק. המנוע החיצוני מופיע
    רק אם המודול קיים וגם יש מפתח תקין, ולכן בגרסה הציבורית תמיד יחזור
    פריט אחד בלבד ולא יהיה בממשק שום אזכור לענן.
    """
    out = [{"id": "local", "label": "מקומי (whisper)",
            "hint": "רץ על המחשב שלך, שום דבר לא נשלח החוצה."}]
    m = _el()
    if m and m.key():
        out.append(dict(m.INFO))
    return out


def transcribe_any(video_path, language="he", engine="local", model="scribe_v1"):
    """נקודת כניסה אחת. engine הוא local, או שם של מנוע ענן אם הותקן."""
    if engine != "local":
        m = _el()
        if not m:
            raise RuntimeError("מנוע ענן לא מותקן בעותק הזה")
        return m.transcribe(video_path, language, model)
    return transcribe_words(video_path, language)


def _norm(s):
    return re.sub(r"[^\w%]+", "", s, flags=re.UNICODE).lower()


def align_pasted(pasted_text, heard_words):
    """
    מיישר טקסט שהודבק ידנית אל הזמנים שנמדדו מהאודיו.

    משתמש בהתאמת רצפים כדי לקשור מילה-למילה איפה שאפשר, ומפזר
    את הזמנים באופן יחסי איפה שאין התאמה (למשל כשתיקנת ניסוח).
    """
    target = [w for w in re.split(r"\s+", pasted_text.strip()) if w]
    if not heard_words:
        return [{"w": w, "s": i * 0.4, "e": i * 0.4 + 0.38} for i, w in enumerate(target)]
    if not target:
        return heard_words

    a = [_norm(w["w"]) for w in heard_words]
    b = [_norm(w) for w in target]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)

    out = [None] * len(target)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(j2 - j1):
                hw = heard_words[i1 + k]
                out[j1 + k] = {"w": target[j1 + k], "s": hw["s"], "e": hw["e"]}
        else:
            # פורסים את חלון הזמן של הקטע הלא-מותאם באופן שווה
            if i1 < len(heard_words):
                t0 = heard_words[i1]["s"]
                t1 = heard_words[min(i2, len(heard_words)) - 1]["e"] if i2 > i1 else heard_words[i1]["e"]
            else:
                t0 = heard_words[-1]["e"]; t1 = t0 + 0.4 * max(1, j2 - j1)
            n = max(1, j2 - j1)
            step = (t1 - t0) / n
            for k in range(j2 - j1):
                out[j1 + k] = {"w": target[j1 + k],
                               "s": round(t0 + k * step, 3),
                               "e": round(t0 + (k + 1) * step, 3)}

    # השלמת חורים והבטחת מונוטוניות
    last = 0.0
    for i, o in enumerate(out):
        if o is None:
            out[i] = {"w": target[i], "s": last, "e": last + 0.3}
        out[i]["s"] = max(out[i]["s"], last)
        out[i]["e"] = max(out[i]["e"], out[i]["s"] + 0.08)
        last = out[i]["e"]
    return out


def group_into_captions(words, max_words=4, max_gap=0.65, max_dur=3.2):
    """
    מקבץ מילים לכתוביות. שובר על שתיקה ארוכה, על אורך מרבי,
    ועל סימני פיסוק, כדי שהקבוצות יישמעו טבעיות.
    """
    caps, cur = [], []
    for i, w in enumerate(words):
        if cur:
            gap = w["s"] - cur[-1]["e"]
            dur = w["e"] - cur[0]["s"]
            ends_clause = bool(re.search(r"[.,!?:;]$", cur[-1]["w"]))
            if gap > max_gap or len(cur) >= max_words or dur > max_dur or ends_clause:
                caps.append(cur); cur = []
        cur.append(w)
    if cur:
        caps.append(cur)
    return [{"words": [x["w"] for x in c],
             "times": [[x["s"], x["e"]] for x in c],
             "emph": [bool(x.get("emph")) for x in c],
             "s": c[0]["s"], "e": c[-1]["e"]} for c in caps]


# ── תכונות בסגנון Captions ───────────────────────────────────────────────

# מילות מילוי בעברית. שמרני בכוונה: מילים כמו "אז" ו"בעצם" נושאות משמעות
# ולכן לא ברשימה, כדי לא לקצץ תוכן אמיתי.
FILLERS = {"אה", "אהה", "אההה", "אמ", "אמם", "אממ", "ממ", "אהם",
           "כאילו", "יעני", "הא", "עמ"}


def strip_fillers(words, enabled=True):
    """מסיר מילות מילוי מהכתוביות. האודיו לא משתנה, רק הטקסט מתנקה."""
    if not enabled:
        return words, 0
    out = [w for w in words if _norm(w["w"]) not in FILLERS]
    return out, len(words) - len(out)


# מילים שראוי להדגיש אוטומטית: מספרים, אחוזים, מונחים באנגלית ופקודות.
# בתוכן שלך אלה כמעט תמיד המילים שנושאות את הערך.
_EMPH = re.compile(r"^(/[\w-]+|[\w.]*\d[\w.%]*|[A-Za-z][A-Za-z0-9.\-]{1,})$")


def mark_emphasis(words):
    """מסמן מילות מפתח להדגשה קבועה, בנוסף להדגשת המילה הנוכחית."""
    n = 0
    for w in words:
        t = w["w"].strip(".,!?:;\"'")
        w["emph"] = bool(_EMPH.match(t))
        n += w["emph"]
    return words, n


def find_silences(words, min_gap=0.8):
    """מאתר שתיקות ארוכות. מוחזר לדיווח, לא חותך את הווידאו."""
    out = []
    for a, b in zip(words, words[1:]):
        gap = b["s"] - a["e"]
        if gap >= min_gap:
            out.append({"s": round(a["e"], 2), "e": round(b["s"], 2), "gap": round(gap, 2)})
    return out
