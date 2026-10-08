import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

LOGO_SIZE = (220, 56)
HERO_SIZE = (1280, 340)

BRAND_NAME = "Corvane Trust"


def _font(size):
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_logo(path):
    img = Image.new("RGBA", LOGO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
   
    draw.ellipse((4, 8, 44, 48), fill=(30, 90, 140, 255))
    draw.ellipse((14, 18, 34, 38), fill=(255, 255, 255, 255))
    draw.text((54, 14), BRAND_NAME, fill=(20, 40, 60, 255), font=_font(22))
    img.save(path)


def make_hero(path):
    w, h = HERO_SIZE
    base = Image.new("RGB", (w, h), (18, 42, 66))
    draw = ImageDraw.Draw(base)

    for x in range(w):
        t = x / w
        r = int(18 + t * 40)
        g = int(42 + t * 60)
        b = int(66 + t * 90)
        draw.line([(x, 0), (x, h)], fill=(r, g, b))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for i in range(-2, 14):
        x0 = i * 110
        odraw.polygon(
            [(x0, h), (x0 + 60, h), (x0 + 160, 0), (x0 + 100, 0)],
            fill=(255, 255, 255, 60) if i % 2 == 0 else (0, 0, 0, 45),
            outline=(255, 255, 255, 90),
        )
    
    for gx in range(0, w, 70):
        for gy in range(20, h, 70):
            odraw.ellipse((gx - 5, gy - 5, gx + 5, gy + 5), fill=(255, 255, 255, 50))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(base)
    draw.text((60, 110), BRAND_NAME, fill=(255, 255, 255), font=_font(44))
    draw.text((60, 175), "Online banking, built on trust.", fill=(220, 230, 235), font=_font(20))
    base.save(path)


def main():
    for sub in ("real", "copy"):
        d = os.path.join(HERE, sub)
        os.makedirs(d, exist_ok=True)
        make_logo(os.path.join(d, "logo.png"))
        make_hero(os.path.join(d, "hero.png"))
    print("Saved logo.png and hero.png into real/ and copy/ (identical in both, on purpose).")


if __name__ == "__main__":
    main()
