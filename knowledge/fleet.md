# Laptop fleet

Last updated: 2026-11-26 (Agent, from the Approver's notes).
Per-laptop status lives in the inventory spreadsheet, not here.

## Classes

| Class | Rule | Typical models |
|---|---|---|
| **Business** | **16 GB RAM** (decided 2026-11-25, Felix) | Dell Pro 16 PC16250 (Core 5 / 16 GB builds), Dell Inspiron 15 3530 (16 GB) |
| **Developer** | 32 GB builds | Dell Pro 16 PC16250 (Core Ultra 7 / 32 GB), Dell Pro Max 16 MC16250, Dell Pro Precision 5 16 PW516261 |
| Older / retiring | Pre-2024 Vostro and Inspiron models | Vostro 7500, Vostro 15 7510, Vostro 16 7620, Vostro 5502, Inspiron 3505 |

## Models and specs (from Dell component lists)

| Model | Typical build | Notes |
|---|---|---|
| Dell Pro 16 PC16250 (business build) | Core 5 120U, 16 GB (1×16, one slot free), 512 GB QLC, non-touch | No IR camera / fingerprint; backlit keyboard; Autopilot from Dell |
| Dell Pro 16 PC16250 (developer build) | Core Ultra 7 255U, 32 GB (1×32), 1 TB QLC, 16" touch | IR camera + fingerprint, backlit, Wi-Fi 6E; the best all-round office build |
| Dell Pro Max 16 MC16250 | Core Ultra 7 255H, 32 GB (2×16), 512 GB, Intel Arc | **No** IR camera / fingerprint, **not** backlit; 100 W charger |
| Dell Pro Precision 5 16 PW516261 | Core Ultra 7 366H vPro, 32 GB LPDDR5X, 512 GB, Wi-Fi 7 | Most powerful; Copilot+ PC; no IR / fingerprint, not backlit |
| Dell Inspiron 15 3530 (consumer line) | i5-1334U, 16 GB (2×8), 512 GB QLC, 720p camera | Fingerprint, backlit; barrel charger; ships with McAfee; **no Autopilot from Dell**; Windows activation issue (see troubleshooting.md); usual reset routes fail (runbooks/reset-inspiron.md) |
| Dell Vostro 16 7620 (~2022) | i7 12th-gen H, NVIDIA RTX, 512 GB | Fingerprint, backlit; barrel charger; no Autopilot from Dell |
| Dell Vostro 15 7510 (~2022) | i5-11400H, 8 GB, 512 GB, RTX | Old; being retired |
| Microsoft Surface Laptop for Business 13.8" (8th Ed) | Intel | Bought direct from Microsoft: hardware hash uploaded to Autopilot by IT |

## Buying patterns

- **2025+ business orders from Dell include Autopilot registration** (the
  laptop appears in Autopilot on its ship date). Older Vostro / Inspiron orders
  did not: they are only in Autopilot if IT uploaded a hardware hash.
- Pro Max and Precision orders came **without** IR camera, fingerprint reader
  and backlit keyboard. Suggested for future orders: add IR camera +
  fingerprint (Windows Hello sign-in).
- Near-identical service tags only mean the same Dell build batch, not the
  same owner.

## Naming

- Device name = `AGY-U-<serial>` (Autopilot template `AGY-U-%SERIAL%`).
- Windows names are limited to 15 characters, so long serials (e.g. Surface)
  use the **last 9 characters**: `AGY-U-RJ26243V9`.
- A device record named only by its serial (no `AGY-U-`) is usually an
  Autopilot placeholder for a laptop that was never set up.

## Where things are

- Stock is kept at the Approver's house until assigned (see the Stock tab).
- Dell component lists (specs) are kept by the Approver; the Agent asks when
  a model's specs aren't listed here.
