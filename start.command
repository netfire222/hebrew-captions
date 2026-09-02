#!/bin/bash
# הפעלת כלי הכתוביות בעברית.
# לחיצה כפולה. בפעם הראשונה מתקין, אחר כך פשוט פותח.
# הכל דרך pip, בלי Homebrew ובלי סיסמת מנהל.

cd "$(dirname "$0")" || exit 1
clear
echo ""
echo "  כלי כתוביות בעברית"
echo "  ─────────────────────"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "  ✗ אין python3 במחשב."
  echo "    הורד מ-python.org"
  echo ""; read -r -p "  Enter לסגירה "; exit 1
fi

# ── התקנה בפעם הראשונה ───────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "  התקנה ראשונה. כמה דקות, רק הפעם."
  echo "  לא צריך Homebrew ולא סיסמה."
  echo ""

  echo "  [1/3] יוצר סביבה מבודדת..."
  python3 -m venv .venv || { echo "  ✗ יצירת הסביבה נכשלה"; read -r -p "  Enter "; exit 1; }
  source .venv/bin/activate
  pip install --quiet --upgrade pip

  echo "  [2/3] מתקין ספריות (Pillow, Flask, ffmpeg)..."
  pip install --quiet flask Pillow imageio-ffmpeg || {
    echo "  ✗ ההתקנה נכשלה"; read -r -p "  Enter "; exit 1; }

  echo "  [3/3] מתקין מנוע תמלול (הגדול מביניהם, קצת סבלנות)..."
  pip install --quiet faster-whisper || {
    echo "  ✗ התקנת faster-whisper נכשלה"; read -r -p "  Enter "; exit 1; }

  # דיווח בלבד. ב-macOS ה-wheel של Pillow לא כולל RAQM (נבדק מול ה-wheel
  # עצמו, גם ב-11 וגם ב-12), ולכן הכלי משתמש במסלול סידור ויזואלי משלו.
  # התוצאה זהה, ההבדל היחיד הוא קרנינג עדין במילים באנגלית.
  if python3 -c "from PIL import features; import sys; sys.exit(0 if features.check('raqm') else 1)" 2>/dev/null; then
    echo "      עיצוב טקסט: RAQM ✓"
  else
    echo "      עיצוב טקסט: מסלול פנימי (תקין לעברית)"
  fi

  echo ""
  echo "  ההתקנה הסתיימה ✓"
  echo ""
else
  source .venv/bin/activate
fi

# ── הרצה ─────────────────────────────────────────────────────────────────
echo "  פותח בדפדפן..."
echo "  לעצירה: סגור את החלון או Ctrl+C"
echo ""

( sleep 3 && open "http://localhost:8769" ) &
python3 app.py
