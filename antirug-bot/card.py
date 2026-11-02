# card.py
# the picture that goes with the day's X post: a dark 1600x900 card with the post's real numbers and tokens.
# a post with an image is seen far more than text alone. Pillow only (pip3 install pillow); no Pillow, no card.
import os

W, H = 1600, 900
BG, FG, DIM, RED, GREEN = (11, 13, 18), (240, 242, 245), (140, 146, 158), (255, 77, 77), (60, 214, 140)
FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc",
         "/Library/Fonts/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font(size: int):
    from PIL import ImageFont
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def render(card: dict, path: str) -> str | None:
    """card: {"kicker", "title", "big", "big_note", "rows": [(left, right)], "footer"}. Returns the path or None."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=RED)
    x, y = 90, 80
    d.text((x, y), card.get("kicker", "ANTI-RUG SCANNER"), font=_font(34), fill=RED)
    y += 70
    for line in card["title"].split("\n"):
        d.text((x, y), line, font=_font(64), fill=FG)
        y += 80
    if card.get("big"):
        y += 20
        d.text((x, y), card["big"], font=_font(150), fill=RED)
        bw = d.textlength(card["big"], font=_font(150))
        d.text((x + bw + 40, y + 70), card.get("big_note", ""), font=_font(44), fill=DIM)
        y += 190
    elif card.get("rows"):
        y += 30
    for left, right in card.get("rows", [])[:4]:          # the reason right after the token, never on top of it
        d.text((x, y), left, font=_font(48), fill=FG)
        lw = d.textlength(left, font=_font(48))
        d.text((x + lw + 36, y + 6), right, font=_font(40), fill=DIM)
        y += 74
    d.text((x, H - 80), card.get("footer", ""), font=_font(36), fill=GREEN)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    im.save(path, "PNG")
    return path
