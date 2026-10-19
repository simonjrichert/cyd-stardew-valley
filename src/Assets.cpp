#include "Assets.h"

#include "Config.h"

#include <SD.h>
#include <SPI.h>

#include <stdlib.h>
#include <string.h>

static bool sdMounted = false;
static bool packReady = false;
static uint8_t* pack = nullptr;
static uint16_t* palette = nullptr;
static uint8_t* artBase = nullptr;
static uint8_t* namedBase = nullptr;
static uint16_t palCount = 0;
static uint16_t artCount = 0;
static uint16_t namedCount = 0;

// The ILI9341 and XPT2046 share this bus. Their chip-selects have to stay
// high while the card is clocked, and the card's select has to stay high
// before the next display write.
static void claimSdBus() {
    digitalWrite(PIN_TFT_CS, HIGH);
    digitalWrite(PIN_TOUCH_CS, HIGH);
    digitalWrite(PIN_SD_CS, HIGH);
    SPI.begin(PIN_TFT_SCLK, PIN_TFT_MISO, PIN_TFT_MOSI);
}

static void releaseSdBus() {
    digitalWrite(PIN_SD_CS, HIGH);
    digitalWrite(PIN_TOUCH_CS, HIGH);
    digitalWrite(PIN_TFT_CS, HIGH);
    SPI.begin(PIN_TFT_SCLK, PIN_TFT_MISO, PIN_TFT_MOSI);
}

static bool readU16(File& file, uint16_t* out) {
    uint8_t bytes[2];
    if (file.readBytes((char*)bytes, 2) != 2) return false;
    *out = (uint16_t)bytes[0] | ((uint16_t)bytes[1] << 8);
    return true;
}

static AssetBoot failPack(File& file, AssetBoot why) {
    file.close();
    releaseSdBus();
    Serial.println("Bad /sprites/atlas.bin");
    return why;
}

AssetBoot assetsBegin() {
    claimSdBus();
    sdMounted = SD.begin(PIN_SD_CS, SPI, 4000000);
    releaseSdBus();
    if (!sdMounted) {
        Serial.println("SD Card Mount Failed!");
        return ASSET_NO_CARD;
    }
    Serial.println("SD Card Mounted Successfully!");

    claimSdBus();
    File file = SD.open(SD_ATLAS_PATH, FILE_READ);
    if (!file) {
        releaseSdBus();
        Serial.printf("Missing %s\n", SD_ATLAS_PATH);
        return ASSET_NO_PACK;
    }

    char magic[4];
    if (file.readBytes(magic, 4) != 4 || memcmp(magic, "CYD1", 4) != 0) {
        return failPack(file, ASSET_BAD_PACK);
    }
    if (!readU16(file, &palCount) || !readU16(file, &artCount) || !readU16(file, &namedCount)) {
        return failPack(file, ASSET_BAD_PACK);
    }
    if (palCount == 0 || palCount > 256 || artCount == 0 || artCount > 128 || namedCount != ASSET_NAMED_COUNT) {
        return failPack(file, ASSET_BAD_PACK);
    }

    size_t bytes = (size_t)palCount * 2u + (size_t)artCount * 256u + (size_t)namedCount * 256u;
    pack = (uint8_t*)malloc(bytes);
    if (pack == nullptr || file.readBytes((char*)pack, bytes) != bytes) {
        free(pack);
        pack = nullptr;
        return failPack(file, ASSET_BAD_PACK);
    }
    file.close();
    releaseSdBus();

    palette = (uint16_t*)pack;
    artBase = pack + (size_t)palCount * 2u;
    namedBase = artBase + (size_t)artCount * 256u;
    packReady = true;
    Serial.printf("SD sprites: %u tiles, %u palette colors\n", artCount, palCount);
    return ASSET_OK;
}

bool assetsReady() {
    return packReady;
}

const uint8_t* assetArt(uint8_t id) {
    if (!packReady || id >= artCount) return nullptr;
    return artBase + (size_t)id * 256u;
}

const uint8_t* assetNamed(uint8_t slot) {
    if (!packReady || slot >= namedCount) return nullptr;
    return namedBase + (size_t)slot * 256u;
}

uint16_t assetPalette(uint8_t index) {
    if (!packReady || index >= palCount) return 0;
    return palette[index];
}

bool assetsReadFile(const char* path, uint8_t* dst, size_t cap, size_t* outLen) {
    if (!sdMounted || dst == nullptr || cap == 0) return false;
    claimSdBus();
    File file = SD.open(path, FILE_READ);
    if (!file) {
        releaseSdBus();
        return false;
    }
    size_t n = file.readBytes((char*)dst, cap);
    file.close();
    releaseSdBus();
    if (outLen != nullptr) *outLen = n;
    return n > 0;
}

bool assetsWriteFile(const char* path, const uint8_t* src, size_t len) {
    if (!sdMounted || src == nullptr) return false;
    claimSdBus();
    if (SD.exists(path)) SD.remove(path);
    File file = SD.open(path, FILE_WRITE);
    if (!file) {
        releaseSdBus();
        Serial.printf("Cannot write %s\n", path);
        return false;
    }
    size_t n = file.write(src, len);
    file.close();
    releaseSdBus();
    return n == len;
}
