# Native Kit application review

The RTX capture adapter produces rendered images and video. The requested
application screenshots additionally need the native Kit editor. The proposed
`simready-local-ai` compute image supplies standalone OVRTX, but its retained
recipe does not install that editor. This preparation supplies the missing
application without changing the approved wrapper or its image contract.

## Prepared and checked locally

The [Kit retention receipt](kit-preflight/retention.json) records two public,
digest-pinned layers from the existing station image. Their compressed hashes
and uncompressed OCI hashes were checked before safe extraction. The selected
layers total **3,181,777,407 bytes**; they contain the standalone Kit runtime
and launcher. The runtime includes its upstream licence files and the fixed
`kit-app-template` revision `3f4b33387f58e5c6694b5479559c945fb80bb625`.
The binaries remain in the local runtime cache; they are not committed here.
Fetching these layers does not prove that Kit executes on the proposed GPU host.

The existing official browser client, `@nvidia/ov-web-rtc` 6.7.0, was installed
from the repository lock with scripts disabled, tested and built in an isolated
directory. Its two configuration tests, the launcher test and five bounded
media-relay tests passed. These tests do not prove delivery of native frames.

[kit-review.usda](kit-review.usda) is a separate editable root layer. It
references the retained bundle and explicitly preserves millimetres, Z-up,
the default prim and the 0–119 timeline at 24 frames/s. An initial trial that
only added a sublayer failed the unit check; the final layer declares stage
metadata explicitly. Native tests compare all four meshes with the retained
bundle, including every point and face index. Strict `usdchecker` validation
is also required. No geometry or material property is changed by this layer.

The [local check receipt](kit-preflight/checks.json) identifies the checked
sources, working layer and client files. The original rendering bundle and its
receipts remain unchanged.

## Execute only within the approved session

The USD 5 / 90-minute proposal was approved for the
[29 October attempt](native-review-20261029/README.md), which ended with verified
cleanup before this protocol completed. Coordinate the shared account and
obtain a fresh bounded authorization before another paid attempt. Recheck the
offer, driver and deadline guard before launch; this document does not renew
the previous approval.
The compute image plus these Kit layers total **37.806 GB compressed**, within
the proposed 40 GB download allowance, with about 2.19 GB remaining for other
transfers. Check that remaining allowance before installing missing libraries
or fetching anything else; do not assume that startup downloads are free.

1. Start the qualified compute profile under its external deadline guard.
   Run the GPU/driver preflight and standalone OVRTX witness first. Run OVRTX
   captures and Kit sequentially so their results and GPU observations remain
   attributable. Use the fresh manifest deadline for every child process.
2. Transfer the two retained Kit archives through the verified SSH connection.
   Recheck their compressed and uncompressed hashes against the receipt. Use a
   fresh extraction directory with the same path and link restrictions used
   locally. Preserve the licences. Set `KIT_RUNTIME_DIR` to the extracted
   `opt/station-kit-runtime`; never overwrite an existing runtime. Verify ELF
   dependencies on this actual Linux host before launching Kit. Missing host
   libraries or native startup failures are still possible.
3. Copy the complete `bundle-001` directory and `kit-review.usda` into a new
   review directory. Check their hashes. Use only this copied root layer for
   UI saves, and retain the bundle's before/after hashes. Set `STATION_SCENE`
   to the absolute copied `kit-review.usda` path.
4. Reuse the application and flags from
   [the existing launcher](../../../../containers/picogk-station-kit/launch.py).
   Select the GPU ordinal confirmed by Kit's `gpu.foundation` PCI identity.
   The compute profile exposes SSH only: do not invent a public UDP mapping
   or publish TCP 49100/47999. For the private relay path, launch the runtime
   directly with `primaryStream/publicIp=127.0.0.1`, signal port 49100 and
   stream port 47998, keeping the existing no-window, single-GPU and
   `--exec open_scene.py` arguments. This private-only adaptation still needs
   native verification; the station launcher's public-port prerequisite must
   not be satisfied with fabricated provider metadata.
5. Reuse [the bounded SSH media relay](../../../../containers/picogk-station-kit/README.md#repli-média-par-ssh)
   with the current manifest deadline, without its persistent mode. Forward
   TCP 49100 and 47999 to local loopback through the approved SSH connection.
   Serve the built client on local loopback, and connect it to loopback media
   port 47998. No additional public service is required.

## Required native evidence

Capture the actual decoded Kit viewport and stage tree after opening the
working USD. Frame the whole monocoque and record an exterior view. Select the
closed sections, then hide `OuterSkin` in the working layer for a tunnel and
interior view. Save and reopen that working layer, reconnect the browser and
verify that native frames resume. Check the retained bundle hashes again.

Keep screenshots, sanitized frame counters/resolution, Kit version and logs,
GPU/driver identity, the saved working layer, and hashes of all collected
media. Visually inspect the geometry; a connected socket or non-empty UI alone
does not prove that the correct scene was displayed. Do not publish raw ICE
credentials, SDP or private transport diagnostics. The standalone RTX stills
and turntable must retain their own execution receipts as well.

Collect and verify the outputs on the Mac, destroy the exact rented instance
under its guard and verify its absence. A stalled editor, failed stream or
failed collection must not extend the approved duration.

**Observed on 29 October:** Kit startup, scene-open notification and 26 decoded
loading-editor frames through the private relay; standalone RTX media were
collected and hash-verified. **Still pending:** full native model viewport,
selection, save/reopen, reconnection, complete logs and corrected RTX framing.
See the [partial execution receipt](native-review-20261029/session.json).
These observations close no engineering or manufacturing approval gate.
