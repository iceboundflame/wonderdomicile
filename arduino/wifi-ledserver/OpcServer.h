#include "Display.h"

#include <WiFi.h>

#include "Streaming.h"

#ifndef htons
#define htons(x) ( ((x)<< 8 & 0xFF00) | \
                   ((x)>> 8 & 0x00FF) )
#endif

#ifndef ntohs
#define ntohs(x) htons(x)
#endif

typedef struct {
  uint8_t channel;
  uint8_t command;
  uint16_t lengthNs;  // network byte order
  uint16_t sequenceNs;  // network byte order
} OpcHeader;

constexpr int OPC_PORT = 7890;

class OpcServer {
 private:
  WiFiUDP udp_;

  long lastPacketTimestamp_;
  uint16_t lastSequence_;

  long slowPackets_ = 0;
  long droppedPackets_ = 0;

  void discard_() {
//    Serial << "Error; Discarding packet rx buffer" << endl;
    udp_.flush();
  }

  bool checkedReadBytes_(char *buf, int size) {
    int read = udp_.read(buf, size);
    return read == size;
  }

 public:
  void begin() {
    udp_.begin(OPC_PORT);
  }

  int loop() {
    int received = 0;
    while (true) {
//      long a = micros();
      long packetSize = udp_.parsePacket();
//      Serial << " parsePacket " << micros()-a << endl;
//      a = micros();

      if (!packetSize) {
        break;
      }

      OpcHeader h;
      if (!checkedReadBytes_((char*) &h, sizeof(h))) {
        discard_();
        continue;
      }

      uint16_t len = ntohs(h.lengthNs);
      uint16_t oldSeq = lastSequence_;
      lastSequence_ = ntohs(h.sequenceNs);
//      Serial << seq << endl;
      if (lastSequence_ > oldSeq + 1) {
        droppedPackets_++;
        Serial << "-";
      } else if (lastSequence_ < oldSeq) {
        slowPackets_++;
        Serial << "+";
        discard_();
        continue;
      }
//      received++;discard_();continue;

//      Serial << " Ch: " << h.channel << " ; Cmd: "  << h.command << " ; " << len << endl;

      if (h.command == 0) {  // Show RGB pixel string
        uint16_t maxLen = gDisplay.raw().size() * 3;

        if (!checkedReadBytes_((char*) gDisplay.raw().leds, min(len, maxLen))) {
          discard_();
          continue;
        }

        lastPacketTimestamp_ = millis();
        received++;

        if (len > maxLen) {
          Serial << "Invalid length " << len << " exceeds " << maxLen << endl;
          discard_();
          continue;
        }

//        Serial << " finish parse " << micros()-a << endl;
      } else if (h.command == 0xff) {  // device command
        // TODO

      } else {
        Serial << "Invalid command " << _HEX(h.command) << endl;
      }

      if (udp_.available()) {
        discard_();
      }
    }

    return received;
  }

  long lastPacketMillis() {
    return lastPacketTimestamp_;
  }
};
