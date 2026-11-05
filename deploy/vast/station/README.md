# PicoGK station on Vast

The profile adds five operations to the existing OpenBao wrapper, through two
hooks in its `run` function. It keeps its authentication, its variants, its
launch lock and its reconciliation after a lost creation response.
The installed wrapper is never replaced by the repository's historical copy.

## Access from Kali2

The OpenClaw dashboard answers on **http://127.0.0.1:18789/** on Kali2
(HTTP 200 observed on 28 September 2026). From another workstation, forward this
port over the approved SSH connection to Kali2, then open the same local
address. Station **53246885** was deployed on 28 September 2026. A Qwen
response and a PicoGK generation commanded by `m64-coordinator`, with retrieval
and verification of the files, are proven in the
[qualification report](../../../twins/picogk-station-demo/qualification/README.md).
That report distinguishes each trial, the runtime fixes and the endurance run.
Publication reuses the ephemeral GitHub Actions token, granted
`packages: write`, on a Kali2 runner limited to a single job.

The Omniverse client is reachable on **http://127.0.0.1:8088/** through the tunnel.
Signalling on **TCP 49100** stays private. The public UDP path of this
rental did not receive the probes sent from our network; a local media
relay, carried over SSH, provides the video stream.
Use `127.0.0.1` and media port `47998` with this relay. TCP 49100 and 47999
are not published on Vast. Follow the commands and limits of the
[Kit protocol](../../../containers/picogk-station-kit/README.md).

On Kali2, the working commands are:

```sh
~/.local/bin/station-task status
~/.local/bin/station-task demo coupon-001 --span-mm 30 --voxel-mm 0.25
~/.local/bin/station-task status
~/.local/bin/station-task render coupon-001
~/.local/bin/station-task collect coupon-001
```

Wait for the `complete` state before rendering and use a new identifier
for each part. Results are retrieved into `~/stations/coupon-001/`.
On 28 September at 21:36 UTC, the user asked to keep the rental
after adding credit. The deletion guard was disabled and removed,
without calling destruction. **The station keeps running with no automatic
shutdown**, at about **6.24 USD/h**, i.e. **149.69 USD/day excluding transfers**.
The initial manifest is kept as history; do not re-arm its guard
or call `reconcile-station` on this running rental. OpenClaw monitoring
checks errors and progress without interrupting tasks.

Synchronisation to `~/stations/qualification-53246885/` runs every
60 seconds through the Kali2 user service `station-results-sync.service`.
Each transfer is limited to 180 seconds, without deleting files
already collected. The service persists after SSH disconnection.

## Bounded profile for a new qualification

The commands below describe the initial procedure for a new
rental. They must not be replayed on the active station whose
shutdown has been revoked.

The private qualification contains `image_ref` with digest in the namespace
`ghcr.io/cluster2600/3dprinting993-picogk-m64`, `platform: linux/amd64`,
`anonymous_registry_verified: true`, `gated_read_access_verified: true`, the
model and its revision fixed in `station_profile.py`, the measured sizes
`image_download_bytes` and `model_download_bytes`, and
`published_ports: ["22/tcp", "47998/udp"]`. These declarations require real
checks; the script does not invent them.

```sh
python3 deploy/vast/station/prepare.py render \
  --qualification /absolute/private/qualification.json \
  --session-directory /absolute/private/session \
  --output /absolute/private/openbao-vastai-candidate
# Revoir le diff du candidat, puis l'installer sur le wrapper courant.
python3 deploy/vast/station/prepare.py manifest --offer-id 49181720
python3 deploy/vast/station/prepare.py arm /absolute/private/session/station-ID.json
openbao-vastai launch-station 49181720 /absolute/private/session/station-ID.json
openbao-vastai station-show /absolute/private/session/station-ID.json
openbao-vastai reconcile-station /absolute/private/session/station-ID.json
```

(The comment in the block reads: review the candidate's diff, then install it on
the current wrapper.)

The session directory must already exist in mode 0700. Its maximum window is
six hours and its cumulative budget 50 USD. The duration is shortened according to
the rate including 1 TB, 500 GB inbound, 100 GB outbound and a 2 USD margin for
cleanup. Each paid attempt reserves its full cost, even after
failure: no new attempt recovers an amount assumed not to have been billed.
The manifest budget covers only its own attempt, rounded up to the next cent
and bounded by the remaining session budget, while the cumulative ceiling stays 50 USD.

The LaunchAgent guard stays outside Vast, keeps the Mac awake with
`caffeinate` and destroys only the exact identity. It checks the network
counters of all interfaces except loopback, every ten seconds when
SSH answers; two downloads of the image are reserved separately. Wait for
a fresh `<job>.network-ready.json` receipt, bound to the manifest and the instance,
**before** downloading the weights or starting the services. A loss of
metering after activation, a counter regression or an overrun
triggers cleanup. Before the first reading, the maximum delay is 15 minutes.

The guard starts destruction five minutes before the deadline and checks it
until absence. The calculation is conservative, not a Vast invoice: a provider
or connection outage can delay destruction and its billing.
A container stop is never evidence that billing has ended.

Local check, with no secret and no rental:
`python3 -m unittest discover -s tests -p test_station_profile.py -v`.

## Image and allocation

The [picogk-station.Dockerfile](../../../containers/picogk-station.Dockerfile) recipe
combines the Qwen and PicoGK images already pinned by digest, with four environments:
Qwen, `/opt/cad`, `/opt/geometry-qa` and `/opt/ovrtx-runtime`. Kit has its own
standalone runtime. No Docker socket or nested Docker engine is needed on Vast.

| Resource | Use |
|---|---|
| CUDA GPU 0–1 | Qwen, TP 2, context 262,144, four sequences |
| Vulkan GPU 2 | Kit 110.2.0 editor; confirm the PCI identifier in its logs |
| CUDA GPU 3 | Automated OVRTX renders |
| CPU and RAM | PicoGK 2.3.0 / .NET 9.0.317, FreeCAD, build123d, Gmsh, CalculiX |

On Kali2, from a dedicated checkout, after accepting the NVIDIA terms:

```sh
docker build -f containers/picogk-station.Dockerfile \
  --build-arg NVIDIA_EULA_ACCEPTED=yes --target station -t picogk-station:raw .
mkdir -p /home/lolman/station-image-tmp
TMPDIR=/home/lolman/station-image-tmp python3 containers/picogk-station/normalize-image.py \
  picogk-station:raw picogk-station:qualified
```

The normaliser removes port 8000 inherited from the Qwen image without modifying the
layers. It compares the whole configuration before/after. Then publish
the qualified tag with the [publication workflow](../../../.github/workflows/picogk-station-publish.yml).
The GitHub hook of [station_credentials.py](../../openbao/station_credentials.py)
registers a JIT runner on Kali2 through the existing OpenBao identity; it does not
rebuild the image. The final qualified image is
`ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:6548a22795a01bf6b4a1d79a4bf9415d839ef5f445773d19d3df81bec2bef154`.
The tag `station-20260928-persistent-4f58a4e28ab7` uses the already public PicoGK
repository without modifying its older tags or its base digests. The job uses its own publication token, in
a temporary Docker directory deleted when it ends. Then verify
the digest, its platform and its ports anonymously. No weights or secrets enter
the image. The component licences remain applicable; NVIDIA describes
the current terms on its [Omniverse licence page](https://docs.omniverse.nvidia.com/avp/latest/common/NVIDIA_Omniverse_License_Agreement.html).
The intermediate archive requires a disk with enough space; `/tmp`
on Kali2 is a 7.7 GB tmpfs and is not suitable for this export.

## Qualification order

1. Verify access to the fixed model, its size and the image's public digest.
2. Refresh the offer, produce the manifest, arm the persistent guard, rent.
3. Wait for the fresh network receipt; run [preflight.py](preflight.py) over SSH.
   It measures the CPU/RAM quotas, available space, Vulkan and a real
   NVENC H.264 encode on GPU 2 before the weights are loaded.
4. Run `station-demo /workspace/jobs/qualification` as `station-worker`.
   The C# sources stay in `/opt/station-repo/twins/picogk-station-demo`.
   The USD/STL files are derived; the parametric FreeCAD witness keeps
   its Python source, its FCStd document and its STEP separately.
5. Initialise the services with `STATION_SCENE` pointing to a working USD copy
   and `station-onstart`, then start Kit with
   `supervisorctl -c /opt/station/supervisord.conf start kit`.
6. Use the HF hook `start-station` bound to the manifest. It revalidates the instance,
   the guard process and the metering before passing the token over SSH
   stdin. The runtime file is accessible only to root; only Qwen reads it.
7. Replace the Kali2 tunnel destination while keeping
   `127.0.0.1:18000/v1`. Prove `/health`, `/v1/models`, a Qwen response,
   then a real OpenClaw tool call. `agents.defaults.maxConcurrent=4` bounds
   the number of simultaneous turns; the OpenClaw queue waits for free slots.
8. Qualify the [WebRTC client](../../../containers/picogk-station-kit/README.md), select and
   move a part in Kit, save then reconnect. Measure thirty
   minutes of simultaneous operation with generations, requests and renders.
9. Regularly retrieve outputs and logs onto Kali2 and compare their
   digests. In the bounded profile, the guard destroys the rental at its deadline; for an early
   end, use `reconcile-station`. A destruction is confirmed only
   after checking its absence from the Vast inventory.

The reference machine is the EOS M 290, 400 W laser, nominal envelope
250 × 250 × 325 mm, with the AlSi10Mg 30 µm map already in the repository.
The checks give geometric screens for orientation, walls,
supports and depowdering. They are neither a calibrated thermal
simulation, nor a print qualification, nor a manufacturing authorisation.

OpenClaw persistence uses the Kali2 systemd user service and
`loginctl enable-linger lolman`. In the bounded profile, the Mac guard survives closing the terminal
and keeps the machine awake, but requires the Mac to stay powered on and its
session open. The provider limit is verified by actual deletion,
never inferred from a mere process stop.
