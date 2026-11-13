// Service worker מינימלי בכוונה.
//
// הוא קיים כדי שאפשר יהיה להתקין את הכלי כאפליקציה, לא כדי להאיץ.
// הכלי עובד מול שרת אמיתי: סרטונים, תמלול וייצוא. קאש של תשובות API
// היה מראה מצב ישן ושובר יותר ממה שמועיל, ולכן אין כאן קאש בכלל.

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  // רשת בלבד. כשאין רשת, הדפדפן יראה את שגיאת הרשת שלו, וזה נכון יותר
  // מלהעמיד פנים שהכלי עובד בלי שרת.
  return;
});
