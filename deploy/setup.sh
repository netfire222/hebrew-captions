#!/usr/bin/env bash
# הקמת כלי הכתוביות על שרת אובונטו נקי.
#
# נבדק על Oracle Cloud Ampere A1 עם Ubuntu 24.04, אבל עובד על כל
# אובונטו עם ארכיטקטורת ARM או x86.
#
# הרצה על השרת:
#   curl -fsSL <הכתובת של הקובץ> -o setup.sh && bash setup.sh
#
# או אחרי שיבוט המאגר:  bash deploy/setup.sh

set -euo pipefail

REPO="${REPO:-https://github.com/netfire222/hebrew-captions.git}"
DIR="${DIR:-$HOME/hebrew-captions}"

say() { printf "\n\033[1;36m==> %s\033[0m\n" "$1"; }
die() { printf "\n\033[1;31m✗ %s\033[0m\n" "$1"; exit 1; }

[ "$(id -u)" -eq 0 ] && die "אל תריץ כ-root. הרץ כמשתמש רגיל, הסקריפט ישתמש ב-sudo לפי הצורך."

# ── 1. פרטים ─────────────────────────────────────────────────────────────
say "פרטי ההתקנה"
read -r -p "  דומיין שמצביע לשרת הזה (למשל netanel-captions.duckdns.org): " DOMAIN
[ -n "$DOMAIN" ] || die "בלי דומיין אי אפשר להוציא תעודת HTTPS."

read -r -s -p "  סיסמה לכניסה לכלי: " APP_PASSWORD; echo
[ ${#APP_PASSWORD} -ge 8 ] || die "סיסמה קצרה מ-8 תווים. הכלי יהיה באינטרנט הפתוח."

# מודל התמלול לפי כמות הזיכרון. large-v3 צורך בערך 2 ג'יגה ב-int8,
# אבל יחד עם הרינדור כדאי מרווח. מתחת ל-6 ג'יגה עוברים ל-medium.
MEM_GB=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
if [ "$MEM_GB" -ge 8 ]; then WHISPER_MODEL=large-v3
elif [ "$MEM_GB" -ge 4 ]; then WHISPER_MODEL=medium
else WHISPER_MODEL=small; fi
echo "  זיכרון בשרת: ${MEM_GB}GB  ->  מודל תמלול: $WHISPER_MODEL"

# ── 2. דוקר ──────────────────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  say "מתקין דוקר"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  NEED_RELOGIN=1
else
  echo "דוקר כבר מותקן"
fi

# ── 3. חומת אש ───────────────────────────────────────────────────────────
# זו הנקודה שתוקעת כמעט כל אחד ב-Oracle. פתיחת הפורטים במסך הניהול
# לא מספיקה: לתמונות של אובונטו שם יש חוקי iptables משלהן שחוסמות
# 80 ו-443 מקומית, ולכן האתר נראה "לא נגיש" גם כשהכל אחר תקין.
say "פותח את הפורטים בשרת עצמו"
if command -v iptables >/dev/null 2>&1; then
  for p in 80 443; do
    sudo iptables -C INPUT -p tcp --dport $p -j ACCEPT 2>/dev/null \
      || sudo iptables -I INPUT 6 -p tcp --dport $p -j ACCEPT
  done
  if command -v netfilter-persistent >/dev/null 2>&1; then
    sudo netfilter-persistent save >/dev/null 2>&1 || true
  else
    sudo apt-get install -y iptables-persistent >/dev/null 2>&1 || true
  fi
  echo "  80 ו-443 פתוחים ונשמרו"
fi
echo "  שים לב: צריך לפתוח אותם גם ב-Security List במסך הניהול של הספק."

# ── 4. הקוד ──────────────────────────────────────────────────────────────
say "מוריד את הכלי"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only
else
  sudo apt-get update -qq && sudo apt-get install -y -qq git
  git clone "$REPO" "$DIR"
fi
cd "$DIR"

# ── 5. הגדרות ────────────────────────────────────────────────────────────
umask 077
cat > .env <<EOF
DOMAIN=$DOMAIN
APP_PASSWORD=$APP_PASSWORD
WHISPER_MODEL=$WHISPER_MODEL
EOF
echo "ההגדרות נשמרו ב-$DIR/.env (קריא רק לך)"

# ── 6. הפעלה ─────────────────────────────────────────────────────────────
say "בונה ומפעיל. הבנייה הראשונה לוקחת כמה דקות."
DOCKER="docker"
[ "${NEED_RELOGIN:-0}" = "1" ] && DOCKER="sudo docker"

$DOCKER compose up -d --build

say "בודק"
for i in $(seq 1 30); do
  if curl -fsS "http://localhost:8769/api/health" >/dev/null 2>&1 \
     || $DOCKER compose exec -T app curl -fsS http://localhost:8769/api/health >/dev/null 2>&1; then
    echo "  הכלי עלה ✓"; break
  fi
  [ "$i" = "30" ] && { $DOCKER compose logs --tail 40 app; die "הכלי לא עלה. הלוג למעלה."; }
  sleep 3
done

cat <<EOF

  ──────────────────────────────────────────────
  מוכן.   https://$DOMAIN

  התעודה מונפקת אוטומטית בדקה הראשונה. אם הדפדפן
  מתלונן, חכה דקה ורענן.

  פקודות שימושיות, מתוך $DIR :
    docker compose logs -f app     מה קורה עכשיו
    docker compose restart app     הפעלה מחדש
    docker compose pull && docker compose up -d --build   עדכון לגרסה חדשה

EOF

if [ "${NEED_RELOGIN:-0}" = "1" ]; then
  echo "  התנתק והתחבר שוב לשרת, כדי להריץ docker בלי sudo."
  echo ""
fi
