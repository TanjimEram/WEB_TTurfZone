"""Turn the owner's original photos and logo into web images (M7.1).

    python scripts/build_images.py

Reads assets_raw/ (originals, NOT in git) and writes resized WebP/PNG/JPEG files into
static/ (committed). Re-run after adding or replacing a photo. Needs Pillow, which is a
dev-only dependency (requirements-dev.txt): production only serves the output files.
Pillow writes no EXIF here, so phone metadata (GPS, device) never reaches the site.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "assets_raw"
PHOTOS_OUT = ROOT / "static" / "images" / "photos"
IMAGES_OUT = ROOT / "static" / "images"
ICONS_OUT = ROOT / "static" / "icons"

# Raw file -> web name. Alt text and order live in routes/public.py (PHOTOS).
PHOTOS = {
    "WhatsApp Image 2026-10-07 at 12.17.43.jpeg": "night-floodlights",
    "WhatsApp Image 2026-10-07 at 12.17.47.jpeg": "night-goal",
    "WhatsApp Image 2026-10-07 at 12.17.40.jpeg": "night-wide",
    "WhatsApp Image 2026-10-07 at 12.17.57.jpeg": "day-palms",
    "WhatsApp Image 2026-10-07 at 12.17.29.jpeg": "day-netting",
    "WhatsApp Image 2026-10-07 at 12.17.31.jpeg": "day-pitch",
}
WIDTHS = (400, 800, 1280)  # gallery thumb, gallery/about 2x, lightbox (originals are 1280 wide)

# CR-7: the hero uses the supplied hero.jpg (an AI-generated aerial pitch, not the ground itself).
HERO_RAW, HERO_NAME, HERO_WIDTHS = "hero.jpg", "hero-aerial", (800, 1280, 1920)
HERO_OUT = ROOT / "static" / "images" / "hero"

LOGO = "Logo.jpeg"
EMBLEM_CENTER, EMBLEM_RADIUS = (512, 497), 268  # the round badge in the 1024px logo
LOGO_BOX = (150, 135, 874, 859)                  # badge + "T TURF ZONE", clear of the corner sparkle
SITE_BG = (11, 15, 13)                           # --bg in main.css


def load(name: str) -> Image.Image:
    """Open a raw file, apply the phone's rotation flag, drop alpha/EXIF."""
    return ImageOps.exif_transpose(Image.open(RAW / name)).convert("RGB")


def build_photos() -> None:
    PHOTOS_OUT.mkdir(parents=True, exist_ok=True)
    for raw, name in PHOTOS.items():
        im = load(raw)
        for width in WIDTHS:
            if width > im.width:
                continue  # never upscale
            out = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            out.save(PHOTOS_OUT / f"{name}-{width}.webp", "WEBP", quality=80, method=6)
        print(f"photo  {name:18} {im.size}")


def build_hero() -> None:
    HERO_OUT.mkdir(parents=True, exist_ok=True)
    im = load(HERO_RAW)
    for width in HERO_WIDTHS:
        if width <= im.width:
            out = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            out.save(HERO_OUT / f"{HERO_NAME}-{width}.webp", "WEBP", quality=80, method=6)
    print(f"hero   {HERO_NAME:18} {im.size}")


def emblem(size: int) -> Image.Image:
    """The round badge on a transparent background, `size` px square."""
    (cx, cy), r = EMBLEM_CENTER, EMBLEM_RADIUS
    big = load(LOGO).crop((cx - r, cy - r, cx + r, cy + r))
    mask = Image.new("L", big.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    big.putalpha(mask)
    return big.resize((size, size), Image.LANCZOS)


def on_background(im: Image.Image, color=SITE_BG) -> Image.Image:
    canvas = Image.new("RGB", im.size, color)
    canvas.paste(im, mask=im.getchannel("A"))
    return canvas


def build_logo() -> None:
    ICONS_OUT.mkdir(parents=True, exist_ok=True)
    emblem(96).save(IMAGES_OUT / "logo-emblem-96.webp", "WEBP", quality=90, method=6)  # nav, 48px at 2x
    emblem(32).save(ICONS_OUT / "favicon-32.png", optimize=True)
    on_background(emblem(180)).save(ICONS_OUT / "apple-touch-icon.png", optimize=True)  # iOS wants no alpha
    print("logo   emblem (nav), favicon-32, apple-touch-icon")


def build_share_image() -> None:
    """1200x630 og:image: the night photo on the right, the full logo blended in on the left."""
    w, h = 1200, 630
    logo = load(LOGO).crop(LOGO_BOX).resize((h, h), Image.LANCZOS)
    bg_color = logo.getpixel((8, 8))  # the logo's own dark background
    canvas = Image.new("RGB", (w, h), bg_color)

    photo = load("WhatsApp Image 2026-10-07 at 12.17.43.jpeg")
    photo = ImageOps.fit(photo, (w - 360, h), Image.LANCZOS)
    fade = Image.linear_gradient("L").rotate(90).resize(photo.size)  # transparent at left edge
    canvas.paste(photo, (360, 0), mask=fade.point(lambda v: min(255, v * 2)))

    edge = Image.new("L", (h, h), 0)  # feather the logo square into the background
    ImageDraw.Draw(edge).ellipse((40, 40, h - 40, h - 40), fill=255)
    canvas.paste(logo, (30, 0), mask=edge.filter(ImageFilter.GaussianBlur(28)))
    canvas.save(IMAGES_OUT / "og-image.jpg", "JPEG", quality=85, optimize=True, progressive=True)
    print("share  og-image.jpg 1200x630")


if __name__ == "__main__":
    build_photos()
    build_hero()
    build_logo()
    build_share_image()
