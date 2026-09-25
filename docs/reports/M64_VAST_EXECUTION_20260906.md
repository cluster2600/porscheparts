# M64 — Vast attempts of September 6, 2026

## Actual result

Two instances were created and then destroyed by the protection controller.
Both deletions were acknowledged and their absence verified over five
successive inventories. No GPU test, cylinder-head computation or Omniverse
render was obtained from these attempts. Do not retry automatically in a loop.

| Instance | Offer | Advertised rate, compute + 500 GB | Result |
| --- | --- | --- | --- |
| 50100733 | 47719142, Utah, RTX PRO 6000 WS, 128 advertised effective cores, 128104 MB RAM | 1.505185 USD/h | Loading, then `offline` state before SSH READY verification; deletion verified |
| 50101149 | 49942717, Hong Kong, RTX PRO 6000 WS, 24 advertised effective cores, 128638 MB RAM | 1.585185 USD/h | Vast API HTTP 429 during the supervised launch; deletion verified |

The `offline` state does not prove the cause of the first machine's failure.
HTTP 429 signals an API refusal, not a solver or CUDA failure.
The downloaded image comprises 34,624,357,174 bytes of compressed layers.
Transfer costs add to the hourly rate. The actual invoice and the balance are
not available through the wrapper operations queried; no total spent is
presented as a billed amount.

## Checks performed before renting

- Approved wrapper `/Users/maxime/.local/bin/openbao-vastai`: reader check
  and authentication succeeded, initial inventory empty.
- Already-approved local SSH key verified and registered, without reading its content.
- GHCR digest re-read:
  `ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699`.
- GitHub workflow 33730827271 re-read: `completed`, `success`, revision
  `009a880b93232f0a43876a98fcc3d2e0740299b4`.
- The F49 folder holds the linux/amd64 build evidence and the CPU tests;
  they are not evidence of GPU execution on these two hosts.
- The first attempt was additionally protected by a local deletion guard
  at 40 minutes, stopped after early deletion was confirmed.
- No secret, scan or cylinder-head file was transferred in these attempts.

## Next steps before any new spending

1. Check the balance and cumulative spending within the authorized limit.
2. Handle the API rate limiting (check cadence/backoff) without blindly
   relaunching creations or weakening the deletion checks.
3. Qualify the NVIDIA runtime; require service logs and a real CUDA
   computation before assigning it any engineering work.
4. Keep CPU development and trials on Kali in the meantime.

The M64 stack is not fully qualified. The complete M64 CAD, the CHT fields,
the stresses and the LPBF simulation of the part remain to be produced.
