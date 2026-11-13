# כלי הכתוביות כשרת.
#
# ffmpeg מגיע כאן מהמערכת ולא מחבילת פייתון, ולכן כל בעיות החתימה של
# macOS לא קיימות בכלל. אותה תמונה רצה על מק ועל שרת ARM, כי שניהם arm64.

FROM python:3.11-slim

# ffmpeg נותן גם ffprobe, שהכלי מעדיף לקריאת מטא-דאטה.
# fonts-dejavu נחוץ רק כגיבוי, הפונטים האמיתיים מגיעים מהמאגר.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# שכבת התלויות נפרדת מהקוד, כדי ששינוי קוד לא יבנה הכל מחדש
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# work, output ו-audio מגיעים מ-volume ולכן נשארים בין עדכונים
RUN mkdir -p work output audio

# המודל של whisper יורד פעם אחת לתוך volume, אחרת כל הפעלה מורידה 3 ג'יגה
ENV HF_HOME=/data/hf \
    HEBCAP_MODEL=large-v3 \
    PYTHONUNBUFFERED=1

EXPOSE 8769

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD curl -fsS http://localhost:8769/api/health || exit 1

# עובד אחד עם הרבה threads, וזה לא שרירותי: מצב העבודות יושב בזיכרון
# התהליך (JOBS), ולכן שני עובדים היו מאבדים זה את העבודות של זה.
# timeout 0 כי ייצוא ארוך הוא המצב הרגיל כאן, לא תקלה.
CMD ["gunicorn", "--bind", "0.0.0.0:8769", \
     "--workers", "1", "--threads", "16", "--timeout", "0", \
     "--access-logfile", "-", "app:app"]
