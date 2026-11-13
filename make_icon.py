# -*- coding: utf-8 -*-
"""
אייקון האפליקציה. עיצוב מקורי: שלוש שורות כתובית על רקע כהה,
בצבעי הכלי. השורה האמצעית בולטת, כמו המילה הפעילה בכתובית.

הרצה:  python3 make_icon.py
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
os.makedirs(STATIC, exist_ok=True)

BG = (17, 16, 9)            # רקע הכלי
BAR = (240, 235, 227)       # טקסט רגיל
HOT = (196, 119, 90)        # המילה הפעילה


def draw(size, pad_ratio=0.0):
    """
    pad_ratio הוא שוליים פנימיים. אנדרואיד חותך אייקון maskable לעיגול,
    ולכן גרסת maskable צריכה אוויר מסביב כדי שלא ייחתך התוכן.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * 0.22)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)

    inner = size * (1 - 2 * pad_ratio)
    off = size * pad_ratio
    h = inner * 0.115                      # גובה שורה
    gap = inner * 0.085
    total = h * 3 + gap * 2
    y = off + (inner - total) / 2
    widths = [0.62, 0.78, 0.44]            # אמצע רחב, כמו מילה מודגשת

    for i, w in enumerate(widths):
        bw = inner * w
        x = off + (inner - bw) / 2
        d.rounded_rectangle([x, y, x + bw, y + h],
                            radius=h / 2,
                            fill=HOT if i == 1 else BAR)
        y += h + gap
    return img


if __name__ == "__main__":
    for size in (192, 512):
        draw(size).save(os.path.join(STATIC, f"icon-{size}.png"))
        print(f"  icon-{size}.png")
    # עם שוליים, לאנדרואיד
    draw(512, pad_ratio=0.14).save(os.path.join(STATIC, "icon-maskable.png"))
    print("  icon-maskable.png")
    # iOS מתעלם מ-manifest ולוקח את apple-touch-icon
    draw(180).save(os.path.join(STATIC, "apple-touch-icon.png"))
    print("  apple-touch-icon.png")
