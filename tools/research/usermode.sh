#!/bin/bash
# Switch to picture mode User (0x12), run codetest.sh there, then return to M-Book (0x0F).
ddcutil --bus "${BUS:-15}" setvcp DC 0x12; sleep 4
"$(dirname "$0")/codetest.sh"
ddcutil --bus "${BUS:-15}" setvcp DC 0x0f; sleep 3
