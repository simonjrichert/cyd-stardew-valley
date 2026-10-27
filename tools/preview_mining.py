"""Full-screen HTML preview of cave mining: rocks, pickaxe hotbar, pickup toast."""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_pack as ip
import build_hotbar as hb

ROOT = ip.ROOT
MINE_PNG = ROOT / "tools" / "_mine_preview.png"
OUT_PNG = ROOT / "tools" / "_mining_preview.png"
OUT_HTML = ROOT / "tools" / "_mining_preview.html"

SCREEN_W, SCREEN_H = 320, 240
HUD_H, HOTBAR_Y, HOTBAR_H = 16, 208, 32
SLOTS, SLOT, GAP = 8, 32, 2
BAR_W = SLOTS * SLOT + (SLOTS - 1) * GAP
BAR_X = (SCREEN_W - BAR_W) // 2
PICK_SLOT = 4


def fill(pix, x0, y0, w, h, c):
    for yy in range(y0, y0 + h):
        row = yy * SCREEN_W
        for xx in range(x0, x0 + w):
            pix[row + xx] = c


def blit_toast(pix, text):
    # 5x7 glyphs, 6px cells, same size as the firmware toast.
    glyphs = {
        " ": [0, 0, 0, 0, 0, 0, 0],
        "+": [0, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0],
        "1": [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
        "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
        "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
        "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
        "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
        "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
        "S": [0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110],
        "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
        "N": [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
        "I": [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        "e": [0, 0b01110, 0b10001, 0b11111, 0b10000, 0b10001, 0b01110],
        "o": [0, 0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        "p": [0, 0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000],
        "r": [0, 0b10110, 0b11001, 0b10000, 0b10000, 0b10000, 0b10000],
        "a": [0, 0b01110, 0b00001, 0b01111, 0b10001, 0b10001, 0b01111],
        "l": [0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        "s": [0, 0b01111, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
        "t": [0b00100, 0b00100, 0b01110, 0b00100, 0b00100, 0b00101, 0b00010],
        "n": [0, 0b10110, 0b11001, 0b10001, 0b10001, 0b10001, 0b10001],
        "i": [0b00100, 0, 0b01100, 0b00100, 0b00100, 0b00100, 0b01110],
        "u": [0, 0b10001, 0b10001, 0b10001, 0b10001, 0b10011, 0b01101],
        "m": [0, 0b11010, 0b10101, 0b10101, 0b10101, 0b10101, 0b10101],
        "c": [0, 0b01110, 0b10001, 0b10000, 0b10000, 0b10001, 0b01110],
    }
    cream, box = (248, 236, 210), (48, 32, 18)
    chars = 6
    w = len(text) * chars + 8
    x = (SCREEN_W - w) // 2
    y = HUD_H + 2
    fill(pix, x, y, w, 12, box)
    ox = x + 4
    oy = y + 2
    for ch in text:
        rows = glyphs.get(ch, glyphs[" "])
        for gy, bits in enumerate(rows):
            for gx in range(5):
                if bits & (1 << (4 - gx)):
                    pix[(oy + gy) * SCREEN_W + ox + gx] = cream
        ox += chars


def main():
    w, h, bpp, rows = ip.load_png(MINE_PNG)
    pix = [ip.pix(rows, bpp, x, y)[:3] for y in range(h) for x in range(w)]

    _w2, _h2, mbpp, misc = ip.load_png(hb.MISC)
    _w3, _h3, tbpp, tools = ip.load_png(hb.TOOLS)
    hoe = hb.grab(tools, tbpp, 0, 29, key=True)
    bucket = hb.grab(tools, tbpp, 6 * 16, 0, key=True)
    seed = hb.grab(misc, mbpp, 24 * 16, 11 * 16, key=True)
    scythe = hb.grab(tools, tbpp, 0, 300, key=True)
    pickaxe = hb.grab(tools, tbpp, 2 * 16, 90, key=True)
    icons = [hoe, bucket, seed, scythe, pickaxe]

    gold, cream = (236, 196, 56), (248, 236, 210)
    bar, well, rim = (62, 40, 22), (40, 24, 12), (140, 88, 40)
    fill(pix, 0, HOTBAR_Y, SCREEN_W, HOTBAR_H, bar)
    fill(pix, 0, HOTBAR_Y, SCREEN_W, 1, gold)
    for i in range(SLOTS):
        x = BAR_X + i * (SLOT + GAP)
        y = HOTBAR_Y
        selected = i == PICK_SLOT
        fill(pix, x, y, SLOT, SLOT, gold if selected else rim)
        fill(pix, x + 2, y + 2, SLOT - 4, SLOT - 4, well)
        if i < len(icons):
            hb.blit_tile_2x(pix, x, y, icons[i], SCREEN_W)
        if selected:
            fill(pix, x, y, SLOT, 2, cream)
            fill(pix, x, y + SLOT - 2, SLOT, 2, cream)
            fill(pix, x, y, 2, SLOT, cream)
            fill(pix, x + SLOT - 2, y, 2, SLOT, cream)

    blit_toast(pix, "Copper Ore +1")
    hb.write_png(OUT_PNG, pix, SCREEN_W, SCREEN_H)

    b64 = base64.b64encode(OUT_PNG.read_bytes()).decode("ascii")
    OUT_HTML.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Mining preview</title>
<style>
  body {{ margin: 0; background: #120c08; color: #e8d2b0; font-family: Georgia, serif; text-align: center; }}
  main {{ padding: 28px 20px 48px; }}
  h1 {{ font-size: 22px; font-weight: normal; margin: 0 0 8px; }}
  p {{ margin: 0 0 10px; color: #b89a72; font-size: 14px; }}
  ul {{ list-style: none; padding: 0; margin: 0 0 22px; color: #b89a72; font-size: 14px; line-height: 1.55; }}
  .row {{ display: flex; gap: 32px; justify-content: center; align-items: flex-start; flex-wrap: wrap; }}
  figure {{ margin: 0; }}
  figcaption {{ font-size: 13px; color: #b89a72; margin-top: 8px; }}
  img {{ display: block; image-rendering: pixelated; border: 3px solid #8a5a28; }}
</style>
</head>
<body>
<main>
  <h1>Cave mining</h1>
  <p>320&times;240 CYD &middot; pickaxe selected &middot; no extra HUD counter</p>
  <ul>
    <li>Gray rocks drop mostly Stone, sometimes Coal or Copper Ore</li>
    <li>Copper and iron nodes always drop their ore</li>
    <li>Two taps, 8 stamina each &middot; rocks return after sleep</li>
  </ul>
  <div class="row">
    <figure><img alt="Mine 2x" width="640" height="480" src="data:image/png;base64,{b64}"><figcaption>2&times;</figcaption></figure>
    <figure><img alt="Mine 1x" width="320" height="240" src="data:image/png;base64,{b64}"><figcaption>Actual pixels</figcaption></figure>
  </div>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(f"preview {OUT_PNG}")
    print(f"html {OUT_HTML}")


if __name__ == "__main__":
    main()
