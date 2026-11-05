# PicoGK station: OpenClaw commands on Kali2

Add this block to the `TOOLS.md` of the OpenClaw workspace; keep the
instructions already there. Install `openclaw-tools.py` as `~/.local/bin/station-task`
with mode `0755`. The CLI uses Python 3 and the `ssh` / `rsync` of Kali2.

Configuration supplied by the operator in
`~/.config/picogk-station/endpoint.json`:

```json
{"host": "ssh.example.invalid", "port": 22222}
```

Replace these values with the SSH endpoint actually assigned to the station.
The remote user is always `station-worker` (UID 10002). The dedicated key
is `~/.ssh/id_picogk_station_worker`; its public part must be installed
for that account and the host identity must be verified in `known_hosts`.
The CLI does not read the key: only OpenSSH uses it. `StrictHostKeyChecking=yes`,
`BatchMode=yes` and no agent forwarding are enforced. An authentication
failure remains blocking; do not try another account or secret.

## Usage

```sh
station-task status
station-task demo coupon-001 --span-mm 30 --voxel-mm 0.25
station-task status
station-task render coupon-001
station-task collect coupon-001
```

- An identifier starts with a lowercase letter and contains at most
  48 characters from `a-z`, `0-9`, `-`. Each demonstration requires a new
  identifier. Existing jobs are not overwritten.
- `demo` launches the existing `station-demo` chain: PicoGK **2.3.0**, **.NET
  9.0.317**, metal geometry checks, EOS M 290 / AlSi10Mg 30 µm maps and
  USD assembly. `span-mm` lies between 20 and 80; `voxel-mm` between 0.1
  and 0.5. Other CAD operations remain those of the repository; the CLI accepts
  no script, shell command or arbitrary path.
- `demo` and `render` return an acceptance acknowledgement immediately. Jobs
  continue after SSH disconnection, in a single compute queue. An
  acknowledgement does not prove success: wait for `status: complete` in `status`.
- `render` requires the demonstration's `completed.json` file and calls
  `station-render` on GPU 3. The result is `render.png`. Each render
  requires a new filename; a second render of the same job is refused.
- Each compute command is limited to 30 minutes after it is picked up.
  `failed` or `interrupted_or_unknown` requires reading the log before
  proposing a new job. Do not relaunch automatically in a loop.
- `collect` copies results and logs into `~/stations/JOB/` on Kali2,
  without symbolic links, special files, deletion or access outside the job.

Remote files are under `/workspace/jobs/JOB/`: `demo.json`,
`demo.log`, `render.json`, `render.log`, `render.png`, and `output/` for
geometries, reports, digests and `station-assembly.usda`.

Printing is never authorised by these numerical results. Do not
present the part as fitted, printed, physically tested or homologated.
The CLI does not rent, extend or destroy any Vast instance; cost limits
and the external guard remain controlled separately.

## CPU compute on Kali1

Kali1 has a PicoGK runtime extracted and verified from the station image,
with the C# sources kept. From Kali2, use the native launcher:

```sh
kali1-picogk coupon-kali1-001 --span-mm 50 --voxel-mm 0.25
```

The computation blocks until its result: volume/offset/STL round-trip witness,
then parametric witness and two coupons. It uses at most **two CPUs,
2 GiB, zero swap and 300 seconds**, with priority `nice 10`. A lock refuses
a second simultaneous computation on Kali1; there is no new queue.
Each identifier must be new, with the same allowed characters as
`station-task`. Parameters remain bounded to 20–80 mm and 0.1–0.5 mm.

The command uses SSH exclusively via `127.0.0.1:2221` on Kali2,
`HostKeyAlias=kali1-cpu`, a dedicated identity used by OpenSSH and no
agent forwarding. This port is connected to Kali1 by the Mac controller: the
controller and its tunnel must remain available. The direct IP link
Kali2 → Kali1 timed out before authentication; do not disable host
verification or look for another secret to work around a tunnel failure.

After the computation, `rsync` copies only the job into
`~/stations/kali1/JOB/` on Kali2, without links, special files or deletion.
The launcher verifies the eight digests of the `execution.json` receipt. The sources
and the first three trials are also kept in
`~/stations/kali1-compute-20260928-r8kj70sz/`.
This route runs the CPU PicoGK geometry; the metal checks, CAD and USD
remain available through the full `station-task` chain on Vast.
Do not restart the OpenClaw gateway to launch or collect a Kali1 computation.
