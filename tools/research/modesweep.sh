#!/bin/bash
# Cycle picture mode (VCP DC) through reported values, read back dependent codes, restore.
orig=$(ddcutil --bus "${BUS:-15}" --terse getvcp DC | awk '{print $4}')
echo "orig DC=$orig"
for v in 0x0a 0x12 0x22 0x23 0x27 0x28 0x32 0x0f; do
  ddcutil --bus "${BUS:-15}" setvcp DC $v || echo "set $v FAILED"
  sleep 5
  echo "== $(date +%T) DC set $v"
  ddcutil --bus "${BUS:-15}" --terse getvcp DC 10 12 13 14 19 5F 72 87 81 FD 16 18 1A | awk '{printf "%s=%s ", $2, ($3=="C")?$4"/"$5:($3=="SNC")?$4:$7}'; echo
done
ddcutil --bus "${BUS:-15}" setvcp DC "$orig"; sleep 2
echo "restored DC=$(ddcutil --bus "${BUS:-15}" --terse getvcp DC | awk '{print $4}')"
