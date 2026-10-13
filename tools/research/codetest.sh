#!/bin/bash
# Set each approved code to test values, read back, then restore original.
rd() { ddcutil --bus "${BUS:-15}" --terse getvcp DC 10 14 19 5F 72 81 E5 FD | awk '{printf "%s=%s ", $2, ($3=="C")?$4:($3=="SNC")?$4:$7}'; echo; }
t() { code=$1; shift
  orig=$(ddcutil --bus "${BUS:-15}" --terse getvcp $code | awk '{print ($3=="C")?$4:($3=="SNC")?$4:$7}')
  echo "### $code orig=$orig"
  for v in "$@"; do
    r=$(ddcutil --bus "${BUS:-15}" --permit-unknown-feature setvcp $code $v 2>&1 | tr '\n' ' '); sleep 4
    echo "  $(date +%T) set $v ${r:+[$r]}-> $(rd)"
  done
  ddcutil --bus "${BUS:-15}" --permit-unknown-feature setvcp $code 0x$(echo $orig | tr -d x); sleep 2
  echo "  restored -> $(rd)"
}
echo "base: $(rd)"
t 19 0x01 0x03 0x05
t 81 0x01 0x02
t FD 0x01 0x02 0x03 0x04
t 5F 0x00 0x03
t 72 0x50 0x64 0x77 0x8c 0xa0
