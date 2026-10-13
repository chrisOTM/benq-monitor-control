# ddcutil output — BenQ MA320U, 2026-10-13

Real output captured with ddcutil 3.0.2 on `/dev/i2c-15` (DRM `card0-DP-1`,
monitor on USB-C, picture mode M-Book unless noted). Used as parser fixtures
and as the evidence behind the MA320U model (`src/benq_monitor_control/models/ma320u.py`).

| File | Produced by | Content |
|---|---|---|
| `caps.txt` | `ddcutil --bus 15 capabilities` | Parsed capabilities incl. the raw capability string. |
| `snap0.txt` | `tools/research/snap.sh` | Baseline terse snapshot of 33 codes (M-Book). Every later run was compared against it and matched. |
| `modesweep.log` | `tools/research/modesweep.sh` | Picture-mode sweep; 0x23 and 0x27 rejected (`DDCRC_VERIFY`) without HDR signal. |
| `codetest.log` | first `codetest.sh` run, M-Book, **without** `--permit-unknown-feature` | Shows ddcutil refusing 0x19/0x5F/0x81 ("Unrecognized VCP feature") and the monitor rejecting 0x72/0xFD in M-Book. |
| `usermode.log` | `tools/research/usermode.sh` (picture mode User, with `--permit-unknown-feature`) | All tested codes accepted except 0xFD with 8-bit values. |
| `detect.txt` | `ddcutil detect --terse` | Laptop panel (invalid display) and the MA320U on bus 15. |

Not captured in a file: a follow-up 0xFD test in User mode — `0x0501` and
`0x0502` rejected, `0x0104` accepted (read back `x01 x04`), then reset to 0.

The monitor's serial number has been replaced by `SN0000000001`.
