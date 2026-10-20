#pragma once

#include <stddef.h>
#include <stdint.h>

// Card paths are case-sensitive. Copy the project's sdcard/ folder onto the
// FAT32 card so these land at the card root.
static constexpr const char* SD_ATLAS_PATH = "/sprites/atlas.bin";
static constexpr const char* SD_SAVE_PATH = "/save.json";

// Named tiles inside atlas.bin, in this order.
enum AssetNamed : uint8_t {
    ASSET_TILLED = 0,
    ASSET_WATERED,
    ASSET_CROP0,
    ASSET_CROP1,
    ASSET_CROP2,
    ASSET_CROP3,
    ASSET_PLAYER,
    ASSET_NAMED_COUNT
};

enum AssetBoot : uint8_t {
    ASSET_NO_CARD = 0,
    ASSET_NO_PACK,
    ASSET_BAD_PACK,
    ASSET_OK
};

// Mounts the card and, when /sprites/atlas.bin is present, copies it into RAM.
// The display and touch chip-selects are held high for the whole transfer.
AssetBoot assetsBegin();

bool assetsReady();
// Drop a card pack whose palette/tile counts do not match this firmware.
// The farm then draws from flash instead of mixing two atlases.
void assetsUseFirmwareIfStale(uint16_t expectPal, uint16_t expectArt);
const uint8_t* assetArt(uint8_t id);
const uint8_t* assetNamed(uint8_t slot);
uint16_t assetPalette(uint8_t index);

// Whole-file helpers. Paths must match the card exactly, including case.
bool assetsReadFile(const char* path, uint8_t* dst, size_t cap, size_t* outLen);
bool assetsWriteFile(const char* path, const uint8_t* src, size_t len);
