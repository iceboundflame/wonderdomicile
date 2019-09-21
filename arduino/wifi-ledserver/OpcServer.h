#include "Display.h"

#include <WiFi.h>
#include <WiFiServer.h>
#include <WiFiClient.h>

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
    int read = client_.read((uint8_t*) buf, size);
    if (read != size) {
      Serial << " req " << size << " got " << read << endl;
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
      if (client_) {
        close_();
      }
      Serial << "New client" << endl;
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

          // XXX: Only works when full message fits in rx buffer
          if (client_.available() < len) {
            // wait for more data to be received
            break;
          }

          if (currentHeader_.command == 0) {  // Show RGB pixel string
            uint16_t maxLen = gDisplay.raw().size() * 3;

            if (!checkedReadBytes_((char *) gDisplay.raw().leds, min(len, maxLen))) {
              Serial << "Failed to read content" << endl;
              close_();
              break;
            }

            lastPacketTimestamp_ = millis();
            received++;

            if (len > maxLen) {
              Serial << "Ignore extra data: length " << len << " exceeds " << maxLen << endl;
              for (int i = 0; i < len - maxLen; ++i) {
                client_.read();
              }
            }
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
