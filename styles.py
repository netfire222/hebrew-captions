# -*- coding: utf-8 -*-
"""
פריסטים של סגנונות כתוביות בעברית.

כל פריסט מגדיר גם את הצד של הדפדפן (CSS לתצוגה החיה) וגם את הצד של
הרינדור (PIL, לייצוא הסופי), כדי שמה שרואים בתצוגה יהיה מה שיוצא בייצוא.

הפונטים נבחרו לפי מה שנפוץ בריאלס בעברית ב-2026. כולם חינמיים מ-Google Fonts.
"""

# משפחות פונטים עבריות כבדות, לפי סדר עדיפות לכל פריסט.
# הכלי מחפש אותן במערכת ונופל לחלופה הבאה אם אחת חסרה.
FONT_STACKS = {
    # הפונטים מצורפים בתוך תיקיית fonts/ של הכלי, כך שהוא עובד
    # בלי להתקין כלום במערכת. נלקחו מהמשפחות המלאות שיש לך.
    "rubik_black":   ["Rubik-Black", "Heebo-Black", "Rubik-ExtraBold", "Arial Hebrew"],
    "heebo_black":   ["Heebo-Black", "Rubik-Black", "Heebo-ExtraBold", "Arial Hebrew"],
    "karantina":     ["Karantina-Bold", "Rubik-Black", "Heebo-Black", "Arial Hebrew"],
    "extrabold":     ["Heebo-ExtraBold", "Rubik-ExtraBold", "Heebo-Bold", "Arial Hebrew"],
}



PRESETS = {
    # ── 1. הסגנון הכי נפוץ בריאלס: לבן ענק, קונטור שחור, מילה נוכחית בצהוב
    "pop_yellow": {
        "label": "פופ צהוב",
        "hint": "הסגנון הכי נפוץ בריאלס. לבן עם קונטור, המילה הנוכחית קופצת בצהוב.",
        "font": "rubik_black",
        "size_pct": 7.2,          # אחוז מגובה הפריים
        "line_height": 1.15,
        "color": "#FFFFFF",
        "active_color": "#FFD500",
        "stroke": "#000000",
        "stroke_pct": 0.62,       # אחוז מגודל הפונט
        "shadow": {"color": "#000000", "opacity": 0.55, "blur_pct": 0.35, "dy_pct": 0.12},
        "bg": None,
        "uppercase": False,
        "max_words": 4,
        "y_pct": 74,              # מרכז הכתובית, אחוז מגובה הפריים
        "active_scale": 1.14,     # כמה המילה הנוכחית גדלה
        "pop_ms": 130,
    },

    # ── 2. קלין: בלוק כהה מאחורי הטקסט, קריא על כל רקע
    "block_dark": {
        "label": "בלוק כהה",
        "hint": "רקע כהה מאחורי הטקסט. הכי קריא, טוב לרקעים עמוסים.",
        "font": "rubik_black",
        "size_pct": 6.2,
        "line_height": 1.25,
        "color": "#F5F1EA",
        "active_color": "#D4875A",
        "stroke": None,
        "stroke_pct": 0,
        "shadow": {"color": "#000000", "opacity": 0.35, "blur_pct": 0.4, "dy_pct": 0.1},
        "bg": {"color": "#111009", "opacity": 0.82, "pad_x_pct": 0.42, "pad_y_pct": 0.26, "radius_pct": 0.28},
        "uppercase": False,
        "max_words": 5,
        "y_pct": 76,
        "active_scale": 1.0,
        "pop_ms": 90,
    },

    # ── 3. סגנון המותג שלך: טרקוטה על שחור, מתאים למדריכים
    "brand": {
        "label": "מותג נתנאל",
        "hint": "בצבעי המותג שלך. טרקוטה על שחור, מתאים לתוכן מקצועי.",
        "font": "extrabold",
        "size_pct": 6.0,
        "line_height": 1.25,
        "color": "#F0EBE3",
        "active_color": "#C4775A",
        "stroke": "#111009",
        "stroke_pct": 0.4,
        "shadow": {"color": "#000000", "opacity": 0.5, "blur_pct": 0.3, "dy_pct": 0.1},
        "bg": None,
        "uppercase": False,
        "max_words": 4,
        "y_pct": 75,
        "active_scale": 1.08,
        "pop_ms": 120,
    },

    # ── 4. מילה אחת ענקית בכל פעם, לקצב מהיר
    "one_word": {
        "label": "מילה אחת",
        "hint": "מילה אחת ענקית בכל פעם. אגרסיבי, מתאים להוקים ולקצב מהיר.",
        "font": "rubik_black",
        "size_pct": 11.0,
        "line_height": 1.0,
        "color": "#FFFFFF",
        "active_color": "#FFFFFF",
        "stroke": "#000000",
        "stroke_pct": 0.7,
        "shadow": {"color": "#000000", "opacity": 0.6, "blur_pct": 0.35, "dy_pct": 0.14},
        "bg": None,
        "uppercase": False,
        "max_words": 1,
        "y_pct": 70,
        "active_scale": 1.0,
        "pop_ms": 90,
    },
}

PRESETS["karantina_hook"] = {
    "label": "קרנטינה הוק",
    "hint": "פונט תצוגה צר וחד. אימפקט גבוה, מצוין לשלוש השניות הראשונות.",
    "font": "karantina", "size_pct": 9.6, "line_height": 1.05,
    "color": "#FFFFFF", "active_color": "#FFD500",
    "stroke": "#000000", "stroke_pct": 0.55,
    "shadow": {"color": "#000000", "opacity": 0.6, "blur_pct": 0.32, "dy_pct": 0.13},
    "bg": None, "uppercase": False, "max_words": 3, "y_pct": 72,
    "active_scale": 1.16, "pop_ms": 110,
}

PRESETS["clean_white"] = {
    "label": "לבן נקי",
    "hint": "בלי צהוב. המילה הנוכחית רק גדלה. מינימלי ומקצועי.",
    "font": "rubik_black", "size_pct": 6.6, "line_height": 1.2,
    "color": "#FFFFFF", "active_color": "#FFFFFF",
    "stroke": "#000000", "stroke_pct": 0.5,
    "shadow": {"color": "#000000", "opacity": 0.5, "blur_pct": 0.3, "dy_pct": 0.1},
    "bg": None, "uppercase": False, "max_words": 4, "y_pct": 75,
    "active_scale": 1.18, "pop_ms": 120,
}


# ── מאגר הפונטים ─────────────────────────────────────────────────────────
import os, glob

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# תווית קריאה לכל קובץ, לתצוגה בממשק
FONT_LABELS = {
    "Rubik-Black":        "Rubik Black",
    "Rubik-ExtraBold":    "Rubik ExtraBold",
    "Rubik-Bold":         "Rubik Bold",
    "Heebo-Black":        "Heebo Black",
    "Heebo-ExtraBold":    "Heebo ExtraBold",
    "Heebo-Bold":         "Heebo Bold",
    "Karantina-Bold":     "Karantina Bold",
    "Karantina-Regular":  "Karantina Regular",
}


def list_fonts():
    """כל קובצי הפונט שבמאגר, לבחירה בממשק."""
    out = []
    for p in sorted(glob.glob(os.path.join(FONT_DIR, "*.ttf")) +
                    glob.glob(os.path.join(FONT_DIR, "*.otf"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        out.append({"file": os.path.basename(p),
                    "stem": stem,
                    "label": FONT_LABELS.get(stem, stem.replace("-", " "))})
    return out


# ברירת מחדל לקובץ הפונט של כל פריסט
_PRESET_FONT_FILE = {
    "pop_yellow":     "Rubik-Black.ttf",
    "block_dark":     "Rubik-Black.ttf",
    "brand":          "Heebo-ExtraBold.ttf",
    "one_word":       "Rubik-Black.ttf",
    "karantina_hook": "Karantina-Bold.ttf",
    "clean_white":    "Rubik-Black.ttf",
}

for _k, _p in PRESETS.items():
    _p.setdefault("font_file", _PRESET_FONT_FILE.get(_k, "Rubik-Black.ttf"))
    _p.setdefault("x_pct", 50)          # מרכז אופקי
    _p.setdefault("tracking_pct", 0)    # ריווח בין אותיות, אחוז מגודל הפונט
    _p.setdefault("stroke_on", bool(_p.get("stroke")))
    _p.setdefault("shadow_on", bool(_p.get("shadow")))
    _p.setdefault("stroke_color", _p.get("stroke") or "#000000")
    _p.setdefault("shadow_color", (_p.get("shadow") or {}).get("color", "#000000"))
    _p.setdefault("shadow_opacity", (_p.get("shadow") or {}).get("opacity", 0.5))

DEFAULT_PRESET = "pop_yellow"


# הדפדפן מזהה משפחה + משקל, לא שם קובץ. "Heebo-Black" לא יעבוד ב-CSS,
# ולכן לכל stack יש כאן את שם המשפחה והמשקל המקבילים, כדי שהתצוגה
# החיה תראה בדיוק כמו הייצוא.
CSS_FAMILIES = {
    "rubik_black": (["RubikBlackLocal", "Rubik", "Heebo"], 900),
    "heebo_black": (["HeeboBlackLocal", "Heebo", "Rubik"], 900),
    "karantina":   (["KarantinaLocal", "Rubik", "Heebo"], 700),
    "extrabold":   (["HeeboXBLocal", "Heebo", "Rubik"], 800),
}


def css_font_stack(font_key: str) -> str:
    """מחרוזת font-family לדפדפן."""
    fams, _ = CSS_FAMILIES.get(font_key) or CSS_FAMILIES["rubik_black"]
    return ", ".join(f"'{f}'" for f in fams) + ", sans-serif"


def css_weight(font_key: str) -> int:
    return (CSS_FAMILIES.get(font_key) or CSS_FAMILIES["rubik_black"])[1]


def preset_json():
    """הפריסטים בפורמט שהדפדפן יכול לצרוך."""
    out = {}
    for k, p in PRESETS.items():
        q = dict(p)
        q["css_font"] = css_font_stack(p["font"])
        q["css_weight"] = css_weight(p["font"])
        out[k] = q
    return out
