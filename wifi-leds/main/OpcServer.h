#include "Display.h"

#include <WiFi.h>
#include <WiFiServer.h>
#include <WiFiClient.h>
#include <AsyncUDP.h>

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
//  uint32_t timestampNs;  // network byte order
} OpcHeader;

constexpr uint16_t OPC_PORT = 7890;

class UdpOpcServer {
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
      } else if (lastSequence_ == oldSeq) {
        Serial << "=";
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

class TcpOpcServer {
 private:
  WiFiServer server_;
  WiFiClient client_;

  OpcHeader currentHeader_;
  bool headerReceived_ = false;

  long lastPacketTimestamp_;
  uint16_t lastSequence_;

  long slowPackets_ = 0;
  long droppedPackets_ = 0;

  void close_() {
    Serial << "Error; Closing connection" << endl;
    client_.stop();

    headerReceived_ = false;
  }

  bool checkedReadBytes_(char *buf, int size) {
//    int read = -1;
    int read = client_.read((uint8_t *) buf, size);
    while (read < 0) {
      Serial << "!";
      read = client_.read((uint8_t *) buf, size);
    }
    if (read != size) {
      Serial << "checkedReadBytes: req " << size << " got " << read << endl;
    }
    return read == size;
  }

 public:
  TcpOpcServer(): server_(OPC_PORT) {
  }

  void begin() {
    server_.begin();
  }

  int loop() {
    WiFiClient newClient = server_.available();
    if (newClient) {
      Serial << "New client" << endl;
      if (client_) {
        close_();
      }
      client_ = newClient;
    }

    int received = 0;
    if (client_) {
      do {
        if (!headerReceived_) {
          if (client_.available() < sizeof(currentHeader_)) {
            // wait for more data to be received
            break;
          }

          if (!checkedReadBytes_((char *) &currentHeader_, sizeof(currentHeader_))) {
            Serial << "Failed to read header" << endl;
            close_();
            break;
          }
          headerReceived_ = true;

//          Serial << " Ch: " << currentHeader_.channel
//                 << " ; Cmd: "  << currentHeader_.command
//                 << " ; " << ntohs(currentHeader_.lengthNs) << endl;
        }
        if (headerReceived_) {
          uint16_t len = ntohs(currentHeader_.lengthNs);
          uint16_t maxLen = gDisplay.raw().size() * 3;
          if (len > maxLen) {
            Serial << "Length " << len << " exceeds " << maxLen << endl;
            close_();
          }

          // XXX: Only works when full message fits in rx buffer
          if (client_.available() < len) {
            // wait for more data to be received
            break;
          }

          if (currentHeader_.command == 0) {  // Show RGB pixel string
            if (!checkedReadBytes_((char *) gDisplay.raw().leds, len)) {
              Serial << "Failed to read content" << endl;
              close_();
              break;
            }

            lastPacketTimestamp_ = millis();
            received++;
          } else {
            Serial << "Ignoring invalid command " << _HEX(currentHeader_.command) << endl;

//              for (int i = 0; i < len; ++i) {
//                client_.read();
//              }
            close_();
          }

          headerReceived_ = false;
        }
      } while (client_.available());
    }

    return received;
  }

  long lastPacketMillis() {
    return lastPacketTimestamp_;
  }
};

class AsyncUdpOpcServer {
 private:
  AsyncUDP udp_;

  long lastPacketTimestamp_;
  uint16_t lastSequence_;

  long slowPackets_ = 0;
  long droppedPackets_ = 0;
  int got_ = 0;

 public:
  void begin() {
    udp_.listen(OPC_PORT);
    udp_.onPacket([this](AsyncUDPPacket packet) {
      got_++;

      long nowTS = millis();
      long elapsedMs = nowTS - lastPacketTimestamp_;
      lastPacketTimestamp_ = nowTS;

      gFpsGovernor.endFrame(false);
      gFpsGovernor.startFrame();
      Serial << elapsedMs << " ";
    });
  }

  int loop() {
    int received = got_;
    got_ = 0;
    return received;

//    int received = 0;
//    while (true) {
////      long a = micros();
//      long packetSize = udp_.parsePacket();
////      Serial << " parsePacket " << micros()-a << endl;
////      a = micros();
//
//      if (!packetSize) {
//        break;
//      }
//
//      OpcHeader h;
//      if (!checkedReadBytes_((char*) &h, sizeof(h))) {
//        discard_();
//        continue;
//      }
//
//      uint16_t len = ntohs(h.lengthNs);
//      uint16_t oldSeq = lastSequence_;
//      lastSequence_ = ntohs(h.sequenceNs);
////      Serial << seq << endl;
//      if (lastSequence_ > oldSeq + 1) {
//        droppedPackets_++;
//        Serial << "-";
//      } else if (lastSequence_ == oldSeq) {
//        Serial << "=";
//      } else if (lastSequence_ < oldSeq) {
//        slowPackets_++;
//        Serial << "+";
//        discard_();
//        continue;
//      }
////      received++;discard_();continue;
//
////      Serial << " Ch: " << h.channel << " ; Cmd: "  << h.command << " ; " << len << endl;
//
//      if (h.command == 0) {  // Show RGB pixel string
//        uint16_t maxLen = gDisplay.raw().size() * 3;
//
//        if (!checkedReadBytes_((char*) gDisplay.raw().leds, min(len, maxLen))) {
//          discard_();
//          continue;
//        }
//
//        lastPacketTimestamp_ = millis();
//        received++;
//
//        if (len > maxLen) {
//          Serial << "Invalid length " << len << " exceeds " << maxLen << endl;
//          discard_();
//          continue;
//        }
//
////        Serial << " finish parse " << micros()-a << endl;
//      } else if (h.command == 0xff) {  // device command
//        // TODO
//
//      } else {
//        Serial << "Invalid command " << _HEX(h.command) << endl;
//      }
//
//      if (udp_.available()) {
//        discard_();
//      }
//    }
//
//    return received;
  }

  long lastPacketMillis() {
    return lastPacketTimestamp_;
  }
};