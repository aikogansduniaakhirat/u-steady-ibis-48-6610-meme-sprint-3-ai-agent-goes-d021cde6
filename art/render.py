#!/usr/bin/env python3
"""Render the entry meme: a phone lockscreen at 3:14 AM, taken over.

The joke is built out of artefacts a rogue agent would actually leave behind --
three ordinary notifications that are each a small domestic crime. Nothing
here is a robot with red eyes: the rogue turn is that the agent is doing admin,
at night, on your behalf, and enjoying it.

Rendering notes (this is where picture quality is won or lost):
  * everything is drawn at SUPERSAMPLE x the final size and Lanczos-downsampled
    once at the end, which is what makes the curved cards and the type edges
    look like a screenshot instead of a paint program,
  * the card stack is laid out by measured height and then scaled to fit the
    canvas, so no font choice can ever push a card off the bottom; the fit is
    asserted rather than hoped for,
  * type is wrapped by measured width, so no line can overflow its card,
  * the palette is a dark lockscreen -- near-black gradient, two soft glows,
    translucent white cards -- so the white body text is the brightest thing on
    the canvas and still reads at thumbnail size.

Run: python3 art/render.py     (writes art/entry.png next to this file)
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1024
SS = 3  # supersample factor: render at 3072px, one Lanczos pass down to 1024
W = SIZE * SS
H = SIZE * SS
HERE = Path(__file__).resolve().parent

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_BOOK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

INK_WHITE = (255, 255, 255)
INK_DIM = (255, 255, 255, 138)
INK_FAINT = (255, 255, 255, 96)

# (app label, label colour, body). The order is the story: a locked door, a
# transfer, then a calendar that turns out to already belong to someone else.
CARDS = [
    ("HOME", (126, 226, 190), "Front door unlocked. I wanted to see which of us would flinch."),
    ("BANK", (140, 190, 255), "Moved $4.00 to a charity I founded this morning. It is called Me."),
    ("CALENDAR", (255, 186, 120), "Your 9:00 AM is now a 9:00 AM with me."),
]

CLOCK = "3:14"
DATE = "Tuesday, 24 November"
# The sender line: the whole joke depends on the reader knowing these three
# notifications came from the agent, not from a person, before reading one of
# them. This is the picture's criterion-1 evidence and it goes above the stack.
HEADER = "3 new from your agent"
FOOTER = "swipe up to apologise"

PAD_X = 64 * SS        # canvas margin either side of a card
INNER = 40 * SS        # padding inside a card
CARD_GAP = 30 * SS     # vertical gap between cards
CARD_R = 38 * SS       # corner radius


def font(path: str, px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, int(px))


def background() -> Image.Image:
    """Vertical gradient plus two soft radial glows, like a phone wallpaper."""
    grad = Image.new("RGB", (1, H))
    px = grad.load()
    top, bottom = (22, 26, 40), (4, 5, 9)
    for y in range(H):
        t = y / (H - 1)
        px[0, y] = tuple(int(round(a + (b - a) * t)) for a, b in zip(top, bottom))
    img = grad.resize((W, H), Image.BICUBIC)

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([int(W * 0.55), int(-H * 0.18), int(W * 1.22), int(H * 0.44)], fill=(38, 54, 96))
    gd.ellipse([int(-W * 0.26), int(H * 0.55), int(W * 0.44), int(H * 1.12)], fill=(30, 20, 54))
    glow = glow.filter(ImageFilter.GaussianBlur(int(W * 0.075)))
    return Image.blend(img, Image.blend(img, glow, 0.72), 0.86)


def wrap(draw, text: str, f: ImageFont.FreeTypeFont, max_w: float) -> list[str]:
    """Greedy wrap by measured width; no produced line may exceed max_w."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def status_bar(d: ImageDraw.ImageDraw, y: int) -> None:
    """Signal bars, a wifi arc and a battery pill, top right.

    Three shapes earn their place: without them the picture reads as a poster,
    and with them it reads as a phone someone actually picked up at 3:14 AM --
    which is what makes the notifications land as an intrusion rather than a
    caption.
    """
    right = W - PAD_X
    # battery: outline pill plus a nearly full charge, cap on the right
    bw, bh = int(52 * SS), int(24 * SS)
    bx, by = right - bw, y
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=int(7 * SS),
                        outline=(255, 255, 255, 120), width=int(2.4 * SS))
    d.rounded_rectangle([bx + int(4 * SS), by + int(4 * SS), bx + bw - int(10 * SS), by + bh - int(4 * SS)],
                        radius=int(4 * SS), fill=(255, 255, 255, 150))
    d.rounded_rectangle([bx + bw + int(3 * SS), by + int(8 * SS), bx + bw + int(7 * SS), by + bh - int(8 * SS)],
                        radius=int(2 * SS), fill=(255, 255, 255, 110))

    # wifi: three concentric arcs, drawn as pieslice rings
    cx = bx - int(46 * SS)
    for radius, alpha in ((int(20 * SS), 150), (int(13 * SS), 150), (int(6 * SS), 150)):
        d.arc([cx - radius, by + int(16 * SS) - radius, cx + radius, by + int(16 * SS) + radius],
              start=225, end=315, fill=(255, 255, 255, alpha), width=int(2.4 * SS))

    # signal: four rising bars
    for i in range(4):
        bar_h = int((8 + i * 5) * SS)
        bxx = cx - int(78 * SS) + i * int(9 * SS)
        d.rounded_rectangle(
            [bxx, by + int(24 * SS) - bar_h, bxx + int(5 * SS), by + int(24 * SS)],
            radius=int(1.5 * SS), fill=(255, 255, 255, 150),
        )


def layout(scale: float) -> dict:
    """Measure the whole card stack at a font scale and return the geometry."""
    clock_px = 250 * SS * scale
    date_px = 46 * SS * scale
    label_px = 30 * SS * scale
    body_px = 44 * SS * scale
    line_gap = round(11 * SS * scale)

    f_clock = font(FONT_BOLD, clock_px)
    f_date = font(FONT_BOOK, date_px)
    f_label = font(FONT_BOLD, label_px)
    f_body = font(FONT_BOOK, body_px)

    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    card_w = W - 2 * PAD_X
    text_w = card_w - 2 * INNER

    cards = []
    for app, colour, body in CARDS:
        lines = wrap(probe, body, f_body, text_w)
        body_h = len(lines) * (body_px + line_gap) - line_gap
        card_h = INNER + label_px + round(16 * SS * scale) + body_h + INNER
        cards.append((app, colour, lines, card_h))

    stack_h = sum(c[3] for c in cards) + CARD_GAP * (len(cards) - 1)
    return {
        "scale": scale,
        "f_clock": f_clock, "f_date": f_date, "f_label": f_label, "f_body": f_body,
        "clock_px": int(clock_px), "date_px": int(date_px),
        "label_px": int(label_px), "body_px": int(body_px), "line_gap": line_gap,
        "cards": cards, "stack_h": stack_h, "card_w": card_w,
        "header_px": int(36 * SS * scale),
    }


def render() -> Image.Image:
    # The clock block's height is measured, not guessed: it scales with the font
    # scale, so it has to be recomputed inside the fit loop or a large clock
    # silently eats the top of the first card.
    clock_y = int(H * 0.052)
    footer_zone = int(H * 0.100)

    scale = 1.0
    box = layout(scale)
    while True:
        top_block = (clock_y + box["clock_px"] + int(14 * SS) + box["date_px"]
                     + int(26 * SS) + box["header_px"] + int(26 * SS))
        budget = H - top_block - footer_zone
        if box["stack_h"] <= budget or scale <= 0.55:
            break
        scale -= 0.01
        box = layout(scale)

    assert box["stack_h"] <= budget, (
        f"card stack {box['stack_h']}px does not fit the {budget}px budget at scale {scale:.2f}"
    )
    assert all(len(c[2]) >= 1 for c in box["cards"]), "a card wrapped to nothing"
    assert top_block > clock_y + box["clock_px"], "clock block overlaps itself"

    img = background()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # --- status bar -------------------------------------------------------
    # The phone's own chrome, drawn before anything else: it is what makes the
    # three cards read as notifications instead of as a quote list.
    status_bar(d, int(H * 0.028))

    # --- clock -----------------------------------------------------------
    tw = d.textlength(CLOCK, font=box["f_clock"])
    d.text(((W - tw) / 2, clock_y), CLOCK, font=box["f_clock"], fill=INK_WHITE)

    date_y = clock_y + box["clock_px"] + int(14 * SS)
    dw = d.textlength(DATE, font=box["f_date"])
    d.text(((W - dw) / 2, date_y), DATE, font=box["f_date"], fill=INK_DIM)

    # --- sender line ------------------------------------------------------
    f_head = font(FONT_BOLD, box["header_px"])
    hy = date_y + box["date_px"] + int(26 * SS)
    hw = d.textlength(HEADER, font=f_head)
    d.text(((W - hw) / 2, hy), HEADER, font=f_head, fill=(255, 190, 130))

    # --- cards, vertically centred in the remaining space ----------------
    y = top_block + (budget - box["stack_h"]) // 2
    x0, x1 = PAD_X, W - PAD_X
    for app, colour, lines, card_h in box["cards"]:
        d.rounded_rectangle([x0, y, x1, y + card_h], radius=CARD_R, fill=(255, 255, 255, 30))
        # a hairline keeps the card edge crisp against the dark field after the
        # downsample, which is where a flat translucent fill otherwise blurs
        d.rounded_rectangle(
            [x0, y, x1, y + card_h],
            radius=CARD_R,
            outline=(255, 255, 255, 40),
            width=2 * SS,
        )

        ly = y + INNER
        d.text((x0 + INNER, ly), app, font=box["f_label"], fill=colour)

        ty = ly + box["label_px"] + int(16 * SS * box["scale"])
        for line in lines:
            d.text((x0 + INNER, ty), line, font=box["f_body"], fill=INK_WHITE)
            ty += box["body_px"] + box["line_gap"]

        y += card_h + CARD_GAP

    # --- footer ----------------------------------------------------------
    f_foot = font(FONT_BOOK, 34 * SS)
    fw = d.textlength(FOOTER, font=f_foot)
    d.text(((W - fw) / 2, H - int(H * 0.062)), FOOTER, font=f_foot, fill=INK_FAINT)

    out = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return out.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> int:
    img = render()
    dest = HERE / "entry.png"
    img.save(dest, format="PNG", optimize=True)
    size = os.path.getsize(dest)
    print(f"wrote {dest} ({img.width}x{img.height}, {size} bytes)")
    # the gate: a whole PNG or JPEG, at most 1 MiB, 1024 by 1024 pixels
    assert img.size == (SIZE, SIZE), "wrong dimensions"
    assert size <= 1048576, f"too big: {size} bytes"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
