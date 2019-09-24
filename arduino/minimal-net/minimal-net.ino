#include <WiFi.h>

// WiFi stuff
const char* ssid = "Cityscape";
const char* pwd = "applejuice500";

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);

  WiFi.setHostname("minimalnet");
  WiFi.begin(ssid, pwd);
  WiFi.setSleep(false);  // lower latency
}

void loop() {
  static int x;
  x++;
  if (x % 10000000 == 0) {
    Serial.print(WiFi.localIP());
    Serial.print("  ");
    Serial.println(WiFi.RSSI());
  }
}
