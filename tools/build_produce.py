"""Emit 16x16 RGB565 icons for egg, milk, wool, apple, and forage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_pack as ip

ROOT = ip.ROOT
SHEET = (
    ROOT
    / "assets"
    / "stardew"
    / "Miscellaneous"
    / (
        "PC _ Computer - Stardew Valley - Miscellaneous - Harvested Crops, "
        "Seed Packets, Minerals, Food, Equipment, & Miscellaneous Objects.png"
    )
)
OUT = ROOT / "include" / "Produce.h"

FORAGE_SHEET = (
    ROOT / "assets" / "stardew" / "Environment" / "PC _ Computer - Stardew Valley - Environment - Forage.png"
)

# 16x16 cells. Apple is objects index 613; forage uses wild horseradish.
ICON_BOXES = {
    "EGG": (SHEET, 128, 112),
    "MILK": (SHEET, 272, 112),
    "WOOL": (SHEET, 128, 288),
    "APPLE": (SHEET, 208, 400),
    "FORAGE": (FORAGE_SHEET, 7, 6),
}


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def main():
    cache = {}
    lines = [
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "#include <stdint.h>",
        "",
        "// 16x16 RGB565 icons from the Stardew miscellaneous / forage sheets.",
        "// 0x0000 is transparent.",
        "",
    ]
    for name, (path, x0, y0) in ICON_BOXES.items():
        if path not in cache:
            cache[path] = ip.load_png(path)
        w, h, bpp, rows = cache[path]
        vals = []
        for y in range(16):
            for x in range(16):
                r, g, b, a = ip.pix(rows, bpp, x0 + x, y0 + y)
                skip = a < 40 or (r > 248 and g > 248 and b > 248) or (r + g + b < 24)
                vals.append("0x0000" if skip else f"0x{rgb565(r, g, b):04X}")
        lines.append(f"static const uint16_t ICON_{name}[256] PROGMEM = {{")
        lines.append("    " + ", ".join(vals) + ",")
        lines.append("};")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
