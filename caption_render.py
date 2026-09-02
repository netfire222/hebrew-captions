# -*- coding: utf-8 -*-
"""
מנוע רינדור כתוביות בעברית.

הרעיון המרכזי: במקום לתת ל-bidi לסדר שורה שלמה, אנחנו מפרקים למילים
ומניחים אותן ידנית מימין לשמאל. כל מילה עדיין עוברת עיצוב (shaping) נכון
דרך RAQM, אבל אנחנו שולטים במיקום, וכך אפשר:
  1. לצבוע מילה אחת בצבע אחר בלי טריקים
  2. להגדיל את המילה הנוכחית (אפקט פופ)
  3. לדעת בדיוק איפה כל מילה יושבת

זה גם מה שמונע את הבאג הקלאסי שבו מספרים ומילים באנגלית קופצים למקום הלא נכון.
"""
import os, re, glob, functools
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features

# macOS wheels של Pillow לא כוללים RAQM (רק ה-Linux). בדקתי את זה מול
# ה-wheel עצמו, גם ב-Pillow 11 וגם ב-12, אז שדרוג גרסה לא עוזר.
# לכן יש כאן מסלול חלופי: עברית לא דורשת עיצוב הקשרי כמו ערבית, ולכן
# אפשר לסדר אותה ויזואלית בעצמנו ולצייר עם מנוע הפריסה הבסיסי.
HAS_RAQM = features.check("raqm")
_LAYOUT = ImageFont.Layout.RAQM if HAS_RAQM else ImageFont.Layout.BASIC

# ── איתור פונטים ─────────────────────────────────────────────────────────
FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/usr/share/fonts", os.path.expanduser("~/.fonts"),
    os.path.join(os.path.dirname(__file__), "fonts"),
]

@functools.lru_cache(maxsize=None)
def _font_index():
    idx = {}
    for d in FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for ext in ("ttf", "otf", "ttc"):
            for p in glob.glob(os.path.join(d, "**", f"*.{ext}"), recursive=True):
                idx.setdefault(os.path.splitext(os.path.basename(p))[0].lower().replace(" ", ""), p)
    return idx

def find_font(candidates):
    """מחזיר נתיב לפונט הראשון שנמצא, או None."""
    idx = _font_index()
    for name in candidates:
        key = name.lower().replace(" ", "").replace("-", "")
        for k, p in idx.items():
            if k.replace("-", "") == key:
                return p
    for name in candidates:                       # התאמה חלקית
        key = name.lower().replace(" ", "").replace("-", "")
        for k, p in idx.items():
            if key in k.replace("-", ""):
                return p
    return None

def font_by_file(filename, size):
    """טוען פונט לפי שם קובץ מתוך תיקיית fonts/ של הכלי."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", filename)
    if os.path.exists(p):
        return ImageFont.truetype(p, size, layout_engine=_LAYOUT), p
    return None, None


def resolve_font(stack, size):
    path = find_font(stack)
    if path is None:
        for fb in ("/System/Library/Fonts/Supplemental/Arial Hebrew.ttc",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            if os.path.exists(fb):
                path = fb
                break
    if path is None:
        raise RuntimeError("לא נמצא אף פונט עברי במערכת")
    return ImageFont.truetype(path, size, layout_engine=_LAYOUT), path


# ── סידור ויזואלי ────────────────────────────────────────────────────────
def _visual_rtl(t):
    """
    הופך טוקן עברי לסדר ויזואלי, בלי לגעת בריצות של ספרות ואנגלית.
    בלי זה "פי2" היה יוצא הפוך וגם "10" היה מתהפך ל-"01".
    """
    runs = re.findall(r"[\u0590-\u05FF]+|[^\u0590-\u05FF]+", t)
    return "".join((r[::-1] if _HEB.search(r) else r) for r in reversed(runs))


def shape(word):
    """הטקסט שבאמת נמסר ל-PIL."""
    if HAS_RAQM:
        return word
    return _visual_rtl(word) if _HEB.search(word) else word


def _txt_kw(word):
    """פרמטרים ל-draw.text. בלי RAQM אסור להעביר direction."""
    if HAS_RAQM:
        return dict(direction=word_dir(word), language="he")
    return {}


# ── פריסה ────────────────────────────────────────────────────────────────
_HEB = re.compile(r"[\u0590-\u05FF]")

def word_dir(word):
    """
    כיוון לכל מילה בנפרד. טוקן בלי אותיות עבריות (למשל /fork או 30%)
    חייב להיות LTR, אחרת הלוכסן והסימנים קופצים לצד הלא נכון.
    המיקום של הטוקן בשורה נקבע אצלנו ולכן זה לא משפיע על סדר המילים.
    """
    return "rtl" if _HEB.search(word) else "ltr"

def measure(word, font):
    if HAS_RAQM:
        return font.getlength(word, direction=word_dir(word), language="he")
    return font.getlength(shape(word))

def layout_words(words, font, space_w, fonts=None):
    """
    מחזיר [(word, x_left, width)] כשהמילה הראשונה נמצאת הכי ימינה.
    הקואורדינטות יחסיות, 0 = הקצה השמאלי של השורה.

    fonts: פונט לכל מילה. חשוב כשמילה מודגשת מצוירת בגודל גדול יותר,
    אחרת היא תופסת מקום של הגודל הרגיל ודורסת את השכנות.
    """
    fs_ = fonts or [font] * len(words)
    widths = [measure(w, f) for w, f in zip(words, fs_)]
    total = sum(widths) + space_w * (len(words) - 1)
    out, cursor = [], total                       # מתחילים מימין
    for w, ww in zip(words, widths):
        cursor -= ww
        out.append((w, cursor, ww))
        cursor -= space_w
    return out, total

def wrap_words(words, font, space_w, max_w):
    """שובר לשורות לפי רוחב מרבי, שומר על סדר לוגי."""
    lines, cur = [], []
    for w in words:
        trial = cur + [w]
        tw = sum(measure(x, font) for x in trial) + space_w * (len(trial) - 1)
        if tw > max_w and cur:
            lines.append(cur); cur = [w]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# ── ציור ─────────────────────────────────────────────────────────────────
def _hex(c, a=255):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)

def render_caption(size, words, active_idx, preset, font_stack, emph=None):
    """
    מצייר כתובית אחת על שכבה שקופה בגודל הפריים.
    words      : רשימת מילים בסדר לוגי
    active_idx : אינדקס המילה המודגשת, או None
    """
    W, H = size
    fs = int(H * preset["size_pct"] / 100)
    max_w = W * 0.86
    scale = preset.get("active_scale", 1.0)
    ffile = preset.get("font_file")

    def _load(sz):
        if ffile:
            f, p = font_by_file(ffile, sz)
            if f is not None:
                return f, p
        return resolve_font(font_stack, sz)

    # התאמת גודל אוטומטית: מקטינים עד שגם המילה הארוכה ביותר נכנסת ברוחב.
    # בלי זה מילה כמו ultrathink נחתכת בקצה הפריים.
    for _ in range(60):
        font, _ = _load(fs)
        widest = max((measure(w, font) * scale for w in words), default=0)
        if widest <= max_w or fs <= 12:
            break
        fs = int(fs * 0.94)

    big, _ = _load(max(1, int(fs * scale)))
    space_w = max(measure(" ", font), fs * 0.24)   # מינימום, אחרת פונט צר מדביק מילים
    lines = wrap_words(words, font, space_w, max_w)

    lh = fs * preset["line_height"]
    total_h = lh * len(lines)
    cy = H * preset["y_pct"] / 100
    cx = W * preset.get("x_pct", 50) / 100
    top = cy - total_h / 2
    _margin = W * 0.03

    def _ox(tot):
        """
        מרכז את השורה סביב cx, אבל לא נותן לה לצאת מהפריים.
        בלי זה גרירה לצד חותכת את הטקסט.
        """
        o = cx - tot / 2
        return max(_margin, min(o, W - tot - _margin)) if tot < W - 2 * _margin else (W - tot) / 2

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    _stroke_on = preset.get("stroke_on", bool(preset.get("stroke")))
    _stroke_col = preset.get("stroke_color") or preset.get("stroke") or "#000000"
    stroke_w = int(fs * preset.get("stroke_pct", 0) / 10) if _stroke_on else 0
    idx = 0

    # רקע אופציונלי מאחורי כל שורה
    bgc = preset.get("bg")
    if bgc:
        for li, lw in enumerate(lines):
            _, tot = layout_words(lw, font, space_w)
            _o = _ox(tot)
            x0 = _o - fs * bgc["pad_x_pct"]
            x1 = _o + tot + fs * bgc["pad_x_pct"]
            y0 = top + li * lh - fs * bgc["pad_y_pct"]
            y1 = top + li * lh + lh + fs * bgc["pad_y_pct"] * 0.4
            d.rounded_rectangle([x0, y0, x1, y1], radius=int(fs * bgc["radius_pct"]),
                                fill=_hex(bgc["color"], int(255 * bgc["opacity"])))

    # צל: שכבה נפרדת שמטושטשת בסוף
    sh = preset.get("shadow") if preset.get("shadow_on", bool(preset.get("shadow"))) else None
    if sh:
        sh = dict(sh)
        sh["color"] = preset.get("shadow_color", sh.get("color", "#000000"))
        sh["opacity"] = preset.get("shadow_opacity", sh.get("opacity", 0.5))
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if sh else None
    ds = ImageDraw.Draw(shadow_layer) if sh else None

    li_off = 0
    for li, lw in enumerate(lines):
        # איזה פונט כל מילה בשורה הזו תצויר בו
        lfonts = [big if (active_idx is not None and (li_off + j) == active_idx
                          and preset.get("active_scale", 1) != 1) else font
                  for j in range(len(lw))]
        placed, tot = layout_words(lw, font, space_w, fonts=lfonts)
        ox = _ox(tot)
        base_y = top + li * lh
        for j, (word, x, ww) in enumerate(placed):
            is_active = (active_idx is not None and idx == active_idx)
            f = lfonts[j]
            wx = ox + x
            wy = base_y - (f.size - font.size) * 0.5
            is_emph = bool(emph and idx < len(emph) and emph[idx])
            col = _hex(preset["active_color"] if (is_active or is_emph) else preset["color"])

            if sh:
                ds.text((wx + fs * sh["dy_pct"] * 0.4, wy + fs * sh["dy_pct"]), shape(word),
                        font=f, fill=_hex(sh["color"], int(255 * sh["opacity"])),
                        **_txt_kw(word))
            if stroke_w:
                d.text((wx, wy), shape(word), font=f, fill=col, **_txt_kw(word),
                       stroke_width=stroke_w, stroke_fill=_hex(_stroke_col))
            else:
                d.text((wx, wy), shape(word), font=f, fill=col, **_txt_kw(word))
            idx += 1
        li_off += len(lw)

    if sh:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(max(1, fs * sh["blur_pct"] / 4)))
        shadow_layer.alpha_composite(layer)
        return shadow_layer
    return layer
