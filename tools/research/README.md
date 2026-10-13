# Research tools

Scripts used on 2026-10-13 to derive the MA320U VCP map (summarised in the top-level README).
They are not part of the app. No BenQ files are stored in this repository; the
vendor packages must be downloaded from BenQ and extracted locally.

## Static analysis of Display Pilot 2

| Script | Purpose |
|---|---|
| `rccdump.py <binary> <outdir>` | Brute-force dump of the compressed Qt resources (zlib/zstd blobs) embedded in a Qt binary — QML, XML schemas, translations. Needs `python-zstandard`. |
| `vcpcalls.py <objdump.asm>` | For every call to `setVCP`/`getVCP` in an `objdump -d -C` listing, prints the enclosing function and the immediate VCP opcode loaded into `%esi`. |

Workflow used:

1. Extract the Linux AppImage payload without running it: find the `hsqs`
   magic offset, `tail -c +<offset+1>` into a file, then `7z x` the SquashFS.
2. `python3 -I rccdump.py usr/bin/packages/libRDPackage-1.1.4.0.so out/` →
   per-model `<VCPTree>` schemas (picture-mode codes, `*Enable` lock flags)
   and `PackagesInfo.xml` (model → package mapping).
3. `objdump -d -C --no-show-raw-insn libRDPackage-1.1.4.0.so > rd.asm`, then
   `python3 -I vcpcalls.py rd.asm` → feature class → opcode map.
4. Running the AppImage once showed the log line
   `monitor does not support: "MA320U"` and the update-server URL.

## Live tests on the monitor (ddcutil)

All scripts take the I²C bus from `BUS` (default `15`; find it with
`ddcutil detect`). Every write script restores the original value; compare
`snap.sh` output before and after to confirm.

| Script | Writes? | Purpose |
|---|---|---|
| `snap.sh` | no | Terse snapshot of 33 VCP codes. |
| `watch.sh <snap.sh> <log>` | no | Polls `snap.sh` for 20 min and logs changes (for OSD changes). |
| `modesweep.sh` | DC only | Cycles all picture modes reported in the capabilities, reads dependent codes, restores. |
| `codetest.sh` | 19, 81, FD, 5F, 72 | Sets test values, reads back, restores. Uses `--permit-unknown-feature`. |
| `usermode.sh` | DC + above | Runs `codetest.sh` in picture mode User (0x12), where gamma and colour weakness are not locked. |

Captured output is in [`tests/fixtures/ddcutil-2026-10-13/`](../../tests/fixtures/ddcutil-2026-10-13/).
