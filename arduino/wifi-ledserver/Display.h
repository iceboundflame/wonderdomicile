#pragma once

#include <Arduino.h>

#include <FastLED.h>

#include "Streaming.h"
#include "util.h"

////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////
// Display

constexpr int N_PER_STRAND = 143;
constexpr int N_STRANDS = 2;
constexpr int N_ALL = (N_PER_STRAND * N_STRANDS);

constexpr int DATA_PIN_0 = 4;
constexpr int DATA_PIN_1 = 5;

class Display {
public:
  void begin();

  // maxValue0 is the largest input value that is allowed to be rendered as 0
  // (full off).
  void setGamma(float gamma, int maxValue0) {
    Serial << "Gamma table:" << endl;
    for (int i = 0; i < 256; ++i) {
      gammaLut[i] = round(pow((float)i / 255, gamma) * 255);

      if (i > maxValue0 && gammaLut[i] == 0) {
        gammaLut[i] = 1;
      }
      Serial << "  " << i << " " << gammaLut[i] << endl;
    }
  }

  inline CRGBSet getStrand(int i) {
    return CRGBSet(leds_ + i * N_PER_STRAND, N_PER_STRAND);
  }

  CRGBSet raw() { return CRGBSet(leds_, N_ALL); }

  void show() {
    // gamma correction
    for (auto& rgb : raw()) {
      rgb.r = gammaLut[rgb.r];
      rgb.g = gammaLut[rgb.g];
      rgb.b = gammaLut[rgb.b];
    }

    FastLED.show();
  }

private:

  CRGB leds_[N_ALL];

  uint8_t gammaLut[256];

  int maxMilliamps_ = 8000;
};

extern Display gDisplay;

////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

constexpr int LED_PIN = 2;

class StatusLed {
public:
  void begin() {
    pinMode(LED_PIN, OUTPUT);
  }

  void blink() {
    set(!ledState_);
  }
  void set(bool ledState) {
    digitalWrite(LED_PIN, ledState ? LOW : HIGH);
    ledState_ = ledState;
  }

private:
  bool ledState_ = false;
};
extern StatusLed gStatusLed;

////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

constexpr float FRAME_RATE = 60;

class FpsGovernor {
  long start_;
  bool showFps_ = false;

  int loopN_ = 0;
  long lastPrint_ = 0;
  long maxElapsed_ = 0;

 public:
  void startFrame() {
    start_ = micros();
  }
  void endFrame(bool enableDelay = true) {
    constexpr long kDesiredLoopMicros = 1000000 / FRAME_RATE;

    long elapsed = micros() - start_;
    maxElapsed_ = max(elapsed, maxElapsed_);
    long delay = kDesiredLoopMicros - elapsed;
    if (enableDelay && delay > 0) {
      delayMicroseconds(delay);
    }

    loopN_++;
    EVERY_N_MILLIS(5000) {
      if (showFps_) {
        long elapsedSinceLastPrint = micros() - lastPrint_;
        Serial << "fps: "
               << (1000000 * loopN_ / (float) elapsedSinceLastPrint)
               << " avg / last = "
               << (1000000 / (float) elapsed)
               << " / maxElapsed = " << maxElapsed_/1000 << "ms"
               << endl;
        loopN_ = 0;
        maxElapsed_ = 0;
        lastPrint_ = micros();
      }
    }
  }

  void setShowFps(bool showFps) {
    showFps_ = showFps;
  }
  bool isShowFps() {
    return showFps_;
  }
};
extern FpsGovernor gFpsGovernor;

