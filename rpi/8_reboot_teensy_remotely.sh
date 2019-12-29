#!/bin/bash -e
cd "$(dirname "$0")"

set -x
ssh pi@columns.local "teensy_loader_cli --mcu=TEENSY31 -bsv"
