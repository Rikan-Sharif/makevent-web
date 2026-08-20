#!/usr/bin/env python3
"""Render og-image.png — the card chat apps show for a shared makevent.fi link.

The hero asset (frame*.png) is a TRANSPARENT PNG. Used
directly as og:image it composites onto WHITE in every chat client and gets
cropped against the 1.91:1 preview slot — which is the white block the designer
reported. This bakes the site's own background behind it at the right size.

Background recipe mirrors styles.css exactly:
    base            #25193C                     (--bg-base)
    .bg-glow::before  radial ellipse of #7069E7 (--sweep), 165vw x 80vh,
                      centred at 54%/46% of a 115vh box, rotate(36deg),
                      alpha .30 -> .15 @42% -> 0 @74%, blur(85px)
    .bg-tint        #000 at 55% over it

Run from the repo root:  python3 tools/make-og-image.py
"""

from PIL import Image, ImageFilter
import numpy as np
import pathlib

W, H = 1200, 630                      # the 1.91:1 slot Open Graph expects
BASE = (0x25, 0x19, 0x3C)
SWEEP = (112, 105, 231)
TINT_ALPHA = 0.55
BLUR = 85                             # CSS blur() radius == gaussian sigma

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The LIVE hero asset at its largest, not the older phones-group.png copy of
# the same artwork — so a designer refresh of the hero flows into this card on
# the next run, and 2012px downscales to ~900 with room to spare.
SRC = ROOT / "frame2x.png"
OUT = ROOT / "og-image.png"

# ---- base -----------------------------------------------------------------
img = Image.new("RGB", (W, H), BASE)

# ---- the periwinkle sweep -------------------------------------------------
# vw/vh resolve against the card itself. The glow box is 115vh tall, so its
# centre sits at 46% of that, not of the card.
gw, gh = int(1.65 * W), int(0.80 * H)
cx, cy = int(0.54 * W), int(0.46 * 1.15 * H)

yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
# t == 0 at the centre, 1 at the ellipse edge — the gradient's own 0%..100%.
t = np.sqrt(((xx - gw / 2) / (gw / 2)) ** 2 + ((yy - gh / 2) / (gh / 2)) ** 2)
alpha = np.interp(t, [0.0, 0.42, 0.74], [0.30, 0.15, 0.0], right=0.0)

glow = np.zeros((gh, gw, 4), dtype=np.uint8)
glow[..., 0], glow[..., 1], glow[..., 2] = SWEEP
glow[..., 3] = (alpha * 255).astype(np.uint8)
layer = Image.fromarray(glow, "RGBA")

# CSS rotates clockwise, PIL counter-clockwise. Blur AFTER rotating, the way
# the browser blurs the composited layer.
layer = layer.rotate(-36, expand=True, resample=Image.BICUBIC)
layer = layer.filter(ImageFilter.GaussianBlur(BLUR))

sweep = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sweep.paste(layer, (cx - layer.width // 2, cy - layer.height // 2), layer)
img = Image.alpha_composite(img.convert("RGBA"), sweep)

# ---- the 55% black tint ---------------------------------------------------
img = Image.alpha_composite(
    img, Image.new("RGBA", (W, H), (0, 0, 0, int(TINT_ALPHA * 255)))
)

# ---- the phones, above the tint (page content sits above .bg-tint) --------
# The source is already cropped at its own bottom edge, so it is BLED off the
# card's bottom — the phones rise out of the edge the way they rise into the
# footer on the site. A margin under them reads as a mistake instead.
phones = Image.open(SRC).convert("RGBA")
ph = int(H * 0.92)
pw = round(ph * phones.width / phones.height)
phones = phones.resize((pw, ph), Image.LANCZOS)
img.alpha_composite(phones, ((W - pw) // 2, H - ph))

# Flatten: an og:image must never carry alpha, or we are back to white.
img.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT} ({W}x{H})")
