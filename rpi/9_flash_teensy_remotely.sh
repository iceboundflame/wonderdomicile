#!/bin/bash -ex
cd "$(dirname "$0")"

# Usage: $0 <hex|controller.ino.TEENSY31.hex>
scp "${1:-controller/controller.ino.TEENSY31.hex}" pi@columns.local:controller.hex
ssh pi@columns.local "teensy_loader_cli --mcu=TEENSY31 -wsv controller.hex"
