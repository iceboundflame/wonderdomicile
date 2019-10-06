#include "Display.h"

StatusLed gStatusLed;
Display gDisplay;
FpsGovernor gFpsGovernor;

void Display::begin() {
  FastLED.addLeds<WS2812B, DATA_PIN_0, GRB>(getStrand(0), N_PER_STRAND);
  FastLED.addLeds<WS2812B, DATA_PIN_1, GRB>(getStrand(1), N_PER_STRAND);

  setGamma(2.2, 255);
  raw().fill_solid(CRGB::Black);
  show();
}
