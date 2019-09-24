#include "wifi-ledserver.h"


#define __ASSERT_USE_STDERR

#include <assert.h>

#include <Arduino.h>
#include <memory>

#include <WiFi.h>
#include <ESPmDNS.h>
//#include <ArtnetWifi.h>

#include "Display.h"
#include "OpcServer.h"
#include "Streaming.h"

#include "esp_wifi.h"

// WiFi stuff
const char* ssid = "Cityscape";
const char* pwd = "applejuice500";

//ArtnetWifi gArtnet;
UdpOpcServer gOpc;

namespace {
  void handleSerial();
  bool handleSerialLine(const char *line);
}

////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////
// Main

char instance_name[255];
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
//  delay(100);
  Serial << "wifi-ledserver starting; Compiled " __DATE__ "  " __TIME__ << endl;

  gStatusLed.begin();
  gDisplay.begin();

  // WiFi stuff

  uint64_t chipid = ESP.getEfuseMac();
  snprintf(instance_name, sizeof(instance_name), "wifi-led-%04X%08X", (uint16_t)(chipid>>32), (uint32_t)chipid);
  Serial << "Hostname: " << instance_name << endl;

  WiFi.setHostname(instance_name);
  WiFi.begin(ssid, pwd);
  WiFi.setSleep(false);  // lower latency

//  gArtnet.begin();
  gOpc.begin();

  MDNS.begin(instance_name);
//  MDNS.setInstanceName(instance_name);
  MDNS.addService("_openpixelcontrol", "_udp", OPC_PORT);
  MDNS.enableWorkstation();

  gFpsGovernor.setShowFps(true);
}

void loop() {
//  gFpsGovernor.startFrame();
  {
//    handleSerial();

    int received = gOpc.loop();
    if (received) {
      if (received > 1)
        Serial << received << " ";
      gFpsGovernor.endFrame(false);
      gFpsGovernor.startFrame();
    }
    if (WiFi.status() != WL_CONNECTED || millis() - gOpc.lastPacketMillis() > 100) {
      static uint8_t hue = 0;
      gDisplay.raw().fill_rainbow(hue++, 5);
      gDisplay.show();
    } else {
      if (received)
        gDisplay.show();
    }

    EVERY_N_MILLISECONDS(500) {
      gStatusLed.blink();
    }

    EVERY_N_SECONDS(5) {
      Serial << "wifi: " << WiFi.status() << " - " << WiFi.localIP() << " - " << WiFi.RSSI() << endl;
    }
  }
//  gFpsGovernor.endFrame(false);
}

namespace {
  void handleSerial() {
    const int kBufSize = 128;
    static char buf[kBufSize];
    static int next = 0;

    while (Serial.available()) {
      int c = Serial.read();
      if (c == '\r') {
        continue;
      }

      if (next < kBufSize) {
        buf[next] = c;
        next++;
      }

      if (c == '\n') {
        if (next >= kBufSize) {
          Serial << "Line too long; exceeds " << kBufSize << endl;
          next = 0;

        } else {
          buf[next - 1] = '\0';  // remove newline, add null terminator
          next = 0;

          if (!handleSerialLine(buf)) {
            Serial << "Parse error: '" << buf << "'" << endl;
          }
        }
      }
    }
  }

  bool handleSerialLine(const char *line) {
    {
      float gamma;
      int maxValue0;
      if (sscanf(line, "gamma %f %d", &gamma, &maxValue0) == 2) {
        gDisplay.setGamma(gamma, maxValue0);
        return true;
      }
    }

    {
      int r,g,b;
      if (sscanf(line, "tr %d %d %d", &r, &g, &b) == 3) {
        gDisplay.raw().fill_solid(CRGB(r,g,b));
        FastLED.show();
        // block
        while (!Serial.available());
        return true;
      }
    }

    {
      int v;
      if (sscanf(line, "sleep %d", &v) == 1) {
        Serial.println("ok...");
        delay(v);
        Serial.println("ok");
        return true;
      }
    }

    return false;
  }
}


// misc utils

// handle diagnostic informations given by assertion and abort program execution:
void __assert(const char *__func, const char *__file, int __lineno, const char *__sexp) {
  // transmit diagnostic informations through serial link.
  Serial.println(__func);
  Serial.println(__file);
  Serial.println(__lineno, DEC);
  Serial.println(__sexp);
  Serial.flush();

  // abort program execution.
  abort();
}

// not sure why needed: https://forum.pjrc.com/threads/49802-STL-and-undefined-reference-to-std-__throw_bad_alloc()
namespace std {
  void __throw_bad_alloc() {
    Serial.println("Unable to allocate memory");
    abort();
  }
  void __throw_length_error( char const*e ) {
    Serial.print("Length Error :"); Serial.println(e);
    abort();
  }
}
