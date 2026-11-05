# PicoGK station Kit editor

Kit Base Editor **110.2.0** comes from the NVIDIA repository pinned at commit
`3f4b33387f58e5c6694b5479559c945fb80bb625`. The official generator produces
`station.editor.kit`; our layer adds streaming of the full editor.
The application uses Kit's RTX rendering and runs in the Vast container,
without nested Docker. The browser receives a WebRTC video.

## Build and licence

The build requires explicit acceptance of the
[NVIDIA agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)
and of the [Omniverse terms](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-omniverse/).
`install.sh` refuses to continue without `NVIDIA_EULA_ACCEPTED=yes`; this argument
authorises the "Yes" answer to the official generator. Acceptance for this
station was given in the conversation of 28 September 2026. It grants no
additional right to redistribute NVIDIA software.

From the repository root, on Linux x86-64:

```sh
docker build -f containers/picogk-station-kit/Dockerfile \
  --build-arg NVIDIA_EULA_ACCEPTED=yes -t picogk-station:kit-source .
cd deploy/vast/station-client
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run build
```

The standalone runtime is placed in `/opt/station-kit-runtime`. Links to the
build caches are dereferenced. The runtime includes the upstream licences and
the template commit. The final image provides its digest and the extension
versions actually resolved.

## Network and GPU

Publish only **UDP 47998** for WebRTC. Keep **TCP 49100** unpublished on Vast;
access is through a local SSH tunnel. The launcher refuses a configuration
that announces `VAST_TCP_PORT_49100`. Kit documents no setting to bind
signalling to loopback: isolation therefore relies on this port not being
published in the container network.

`station-kit` uses `PUBLIC_IPADDR` (or `VAST_PUBLIC_IP`) and
`VAST_UDP_PORT_47998`. It writes the connection information to
`/workspace/station-runtime/webrtc-connection.json`. The server listens on
**internal UDP port 47998**; the client uses the **mapped external** port.

`STATION_KIT_GPU=2` is the default ordinal. Before launching Qwen in parallel,
check in the `gpu.foundation` table that this ordinal does designate the
third physical GPU reserved for Kit, by comparing the PCI identifier. Correct
the ordinal if necessary. The launcher enforces `renderer.activeGpu`, disables
multi-GPU and removes `CUDA_VISIBLE_DEVICES` from its own process.

`STATION_SCENE` designates a working USD file produced by the demonstration,
never a user source to be preserved. The launcher opens this scene; the native
editor provides selection, moving, properties and saving.

## Client and evidence

Serve `deploy/vast/station-client/dist` on `127.0.0.1:8088`, then forward
ports 8088 and 49100 to the browser machine over SSH. Open
`http://127.0.0.1:8088`, enter the Vast public IPv4 address and the external
UDP port. The official client `@nvidia/ov-web-rtc` **6.7.0** and its integrity
are pinned in `package-lock.json`. No CDN is used at run time.

Qualification requires a non-empty image, moving a selected part, saving the
working USD, then a reconnection. The « Exporter le diagnostic » ("Export
diagnostics") button records the client events and the decoded frames.
Complete this with visual screenshots, evidence of the before/after transform
and the Kit logs. Successful signalling alone does not validate the UDP media
path. Remote GPU and WebRTC validation remains to be run as long as this
evidence is not present.

## SSH media fallback

The qualification of 28 September found a public UDP mapping present in the
Vast API, but none of the six Mac/Kali2 test datagrams reached the server
bound to `0.0.0.0:47998`. The loopback probe succeeded. The public UDP path
therefore remains **failed on this instance**. The fallback below delivered
real Kit frames at 1920 × 1080, a selection, a 10 mm move and a USD save.
A reconnection succeeded after a client recovery of about 34 seconds.
An isolated Chromium browser run on Kali2 then received 132 frames at
1920 × 1080 with the final client files. The services stayed active after
SSH was closed, and the relay reconnected automatically after only the media
tunnel was restarted.
The saved file was also reopened through `File > Open`, after selecting
`My Computer /`; the transform X = 10 mm remains visible after reloading.

`deploy/vast/station/media-relay.py` carries the opaque datagrams in a TCP
stream through SSH. It uses only the Python standard library, fixed loopback
targets and an explicit choice of duration: `--deadline` within the next six
hours, or `--persistent` after authorisation to keep it running.
It preserves datagram boundaries, handles partial reads and EOF, and bounds
the memory queue, the number of peers and fragment inactivity.
It records no media content, no SDP and no ICE authentication parameters.

On Vast, use the Unix deadline from the manifest of the current rental:

```sh
station-media-relay server --deadline "$STATION_DEADLINE_EPOCH"
```

This command listens on **TCP 127.0.0.1:47999** and can only forward to
**UDP 127.0.0.1:47998**. Add to the approved SSH tunnel of the client machine:

```sh
-L 127.0.0.1:47999:127.0.0.1:47999
```

Then, on the machine running the browser:

```sh
python3 ~/bin/station-media-relay client --deadline "$STATION_DEADLINE_EPOCH"
```

Open `http://127.0.0.1:8088/` and enter **127.0.0.1**, port **47998** in the
media fields. Signalling stays in the TCP 49100 tunnel. Only one media machine
may be connected at a time; disconnect the previous browser before changing
machines.

On Kali2, the units `picogk-station-media-tunnel.service` and
`picogk-station-media-relay.service` are separate from
`qwen-vast-tunnel.service`. They use `Restart=always`, an `ExecCondition`
comparing the clock with the manifest deadline and a bounded
`RuntimeMaxSec`. A premature TCP close thus restarts the client; the deadline
and a manual stop prevent a restart loop. The tunnel program also recomputes
the remaining time before each SSH launch under `timeout`, so as not to extend
the deadline during a recovery. The Vast program `media-relay` is added alone
to the supervisor, without restarting Kit or Qwen. The exact fragments
specific to the rental are kept in its evidence; no rental deadline is baked
into the reusable image.

The user then asked to keep the station active, without interruption.
In this authorised mode, the commands become `station-media-relay server
--persistent` on Vast and `python3 ~/bin/station-media-relay client --persistent`
on Kali2. The media units keep `Restart=always`, but no longer have
`ExecCondition`, `RuntimeMaxSec` or a `timeout` wrapper; the tunnel launches
SSH directly. The Qwen service stays independent. This option changes no
rental guard: the controller must record the extension authorisation
separately and adapt its cost policy.

```sh
systemctl --user status picogk-station-media-tunnel picogk-station-media-relay
systemctl --user stop picogk-station-media-relay picogk-station-media-tunnel
```

TCP transport can increase latency and momentarily stall frames during a
retransmission. It allows the interactive work observed, but does not validate
the direct Vast UDP network and does not guarantee a maximum latency.
When reopening the USD from the Mac, the queue reached its 8 MiB limit and the
relay closed that connection. Reconnecting restored the frame and the saved
transform, without restarting Kit or Qwen. A large load may therefore require
a reconnection; the memory limit stays active.

## Native qualification protocol

Run these steps after the GPU pre-check and under the active cost guard.
The `ui-witness` folder must be new. On Vast, the root controller prepares a
working copy, keeping the original result of the generation:

```sh
set -eu
test ! -e /workspace/jobs/ui-witness
install -d -o station-worker -g station-worker /workspace/jobs/ui-witness
runuser -u station-worker -- station-demo /workspace/jobs/ui-witness/output --span-mm 30 --voxel-mm 0.25
cp -p /workspace/jobs/ui-witness/output/station-assembly.usda /workspace/jobs/ui-witness/working.usda
sha256sum /workspace/jobs/ui-witness/output/station-assembly.usda /workspace/jobs/ui-witness/working.usda
```

Before the **first** launch of `station-onstart`, export
`STATION_SCENE=/workspace/jobs/ui-witness/working.usda`. If supervisord already
exists, the shell environment of `supervisorctl` is not passed to it: add
`STATION_SCENE="/workspace/jobs/ui-witness/working.usda"` to the `environment`
setting of the `kit` program only, then apply `reread` and `update` before
`start kit`. The same setting enforces `STATION_KIT_GPU="2"`; if the Vulkan
table reveals another ordinal for the reserved physical GPU, correct it here.
Keep Qwen stopped during this initial GPU check.

1. Start `kit` with `supervisorctl -c /opt/station/supervisord.conf start kit`.
   Keep `/workspace/logs/kit.log` and `kit.err.log`, the `gpu.foundation`
   table and `nvidia-smi --query-gpu=index,pci.bus_id,uuid --format=csv`.
   Check that only one GPU is active in Kit and that its PCI matches the
   intended physical GPU 2. Record the Kit PID.
2. From the browser machine, open an SSH tunnel with
   `-L 127.0.0.1:8088:127.0.0.1:8088 -L 127.0.0.1:49100:127.0.0.1:49100`
   and `-o ExitOnForwardFailure=yes`. Keep the identity and host key
   verification options of the approved connection. The external UDP port is
   not an SSH tunnel port.
3. Open `http://127.0.0.1:8088`, fill in the fields from
   `/workspace/station-runtime/webrtc-connection.json`, then connect.
   A frame must show the native editor and the assembly; capture this state.
4. In Kit's Stage panel, select **`/World/bracket_witness`**, its parent
   Xform. Capture the selection and its initial transform `(0,0,0)`.
   In the native properties, double-click the Translate X value and enter
   **10 mm**, keep Y and Z at zero, then leave the field to confirm.
   Observe the move in the viewport and capture it.
5. Save `working.usda` from File → Save. On the station, read the file back
   with USD to check `xformOp:translate == (10,0,0)`:

   ```sh
   /opt/geometry-qa/bin/python -c 'from pxr import Usd; s=Usd.Stage.Open("/workspace/jobs/ui-witness/working.usda"); v=s.GetPrimAtPath("/World/bracket_witness").GetAttribute("xformOp:translate").Get(); print(tuple(v)); assert tuple(v)==(10.0,0.0,0.0)'
   sha256sum /workspace/jobs/ui-witness/output/station-assembly.usda /workspace/jobs/ui-witness/working.usda
   ```

6. Click Déconnecter (Disconnect) then Connecter (Connect). Check for a new
   decoded frame, the same Kit PID and the preserved transform. Reopen
   `working.usda` through the native File → Open menu to also confirm that the
   saved file can be read. Capture the state and export the client
   diagnostics: at least two connections, decoded frames and non-zero video
   dimensions.
7. Produce the separate render with
   `runuser -u station-worker -- station-render /workspace/jobs/ui-witness/working.usda /workspace/jobs/ui-witness/render-after.png`.
   Check the log, the non-empty PNG and the activity of GPU 3. This command
   uses `/opt/ovrtx-runtime`; it does not replace the Kit interaction evidence.

Collect the folder with `station-task collect ui-witness`, the screenshots,
the WebRTC diagnostics and the Kit logs. The transform read back from disk and
the real frames are the evidence; no result may be declared successful if a
step could not be observed.

Sources: [Kit streaming](https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/docs/streaming.html),
[stream settings](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.livestream.app/latest/Overview.html),
[GPU selection](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/107.3.0/guide/linux_troubleshooting.html).
