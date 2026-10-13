#!/bin/bash
# Read-only snapshot of MA320U VCP values (terse: code type cur/max or SL/SH)
codes="10 12 13 14 16 18 19 1A 5F 60 62 67 68 69 6A 72 81 86 87 8D 94 AA BE C1 CA CC DC E5 EE EF F0 F6 FD"
ddcutil --bus "${BUS:-15}" --terse getvcp $codes 2>&1
