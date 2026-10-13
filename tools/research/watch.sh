#!/bin/bash
# Poll VCP snapshot (read-only) and log changes with timestamps.
snap="$1"; out="$2"; prev=$("$snap")
echo "$(date +%T) START" > "$out"
end=$((SECONDS+1200))
while [ $SECONDS -lt $end ]; do
  sleep 1
  cur=$("$snap")
  [ -z "$cur" ] && continue
  d=$(diff <(echo "$prev") <(echo "$cur") | grep '^[<>]')
  if [ -n "$d" ]; then echo "$(date +%T)" >> "$out"; echo "$d" >> "$out"; prev="$cur"; fi
done
echo "$(date +%T) END" >> "$out"
