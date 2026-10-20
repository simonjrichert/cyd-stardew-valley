# cyd-stardew-valley

A Stardew-style farm that runs on a Cheap Yellow Display. Tap to walk, hoe, water, plant, harvest, pet animals, and pick fruit.

## Hardware

- **Board:** ESP32-2432S028R (Cheap Yellow Display / CYD)
- **MCU:** ESP32 at 240 MHz, 320 KB RAM, 4 MB flash
- **Display:** 320×240 ILI9341 TFT (rotation 1)
- **Touch:** XPT2046 resistive panel
- **Storage:** microSD slot (FAT32) for `save.json` and an optional sprite atlas

Display, touch, and the SD card sit on separate SPI buses. Pin map is in `include/Config.h` and `platformio.ini`.

## Software

The game is written in **C++** on the Arduino framework, built with PlatformIO.

| Piece | Role |
| --- | --- |
| `src/`, `include/` | Game loop, farm/house maps, HUD, save/load |
| TFT_eSPI | Panel drawing |
| XPT2046_Touchscreen | Tap input |
| Python scripts in `tools/` | Pack tiles, sprites, and interior art |

Flash from the repo root:

```
python -m platformio run -t upload
```

Optional: copy `sdcard/` onto the card so `/sprites/atlas.bin` and saves live on the SD. Firmware still runs from flash if the atlas is missing or out of date.

## Tickets

Work items and bugs are tracked in **Linear**.
