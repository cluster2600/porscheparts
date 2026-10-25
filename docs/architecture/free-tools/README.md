# Free engineering tools: 993 Turbo carrier pilot

This optional integration adds **CloudCompare, SQLite FTS5, DVC, SALOME/SMESH,
OpenTURNS and OpenMDAO** to the existing engineering chain. It does not replace
the catalogue, the qualified Qwen geometry command, the CAD masters or the
CalculiX solver.

Start with the [architecture](ARCHITECTURE.md), then follow the
[implementation, tests and recovery runbook](IMPLEMENTATION_TEST_PLAN.md).
The pilot concerns **993-ENG-CARRIER-0001**, OEM **993 115 021 53**, with the
[existing carrier study](../../reports/carrier-resume-20261020/README.md) as
context. The catalogue-selected geometry remains unchanged. R2 and its
auxiliary FEA surface are unadopted comparison studies.

## What each integration does

| Tool | Implemented interface | Authority and current boundary |
|---|---|---|
| SQLite FTS5 | Build a local authorized snapshot index; retrieve five referenced excerpts | Documentary retrieval, never a measured interface or engineering decision |
| Our Qwen | Optional offline MLX documentary draft from the retrieved context | Unqualified draft requiring review; existing synthetic recipe planner remains separate |
| DVC | Archive, replicate and restore private artifacts, verifying SHA-256 after restoration | Transfer/versioning only; a push is not a verified backup |
| CloudCompare | CPU CLI point-to-surface diagnostics, explicit mm and rigid transform, numerical output and SVG | Sampled diagnostics cannot replace the existing whole-surface certificate |
| SALOME/SMESH | NETGEN volume meshing with exact input-boundary and CalculiX-format checks | Separate mesher comparison; missing carrier boundary groups block the mechanical route |
| OpenTURNS | Fixed-seed analytical sensitivity control; failed samples reject the calculation | No carrier probability distribution is invented |
| OpenMDAO | External analytical solver, constrained beam optimization and carrier admission replay | Carrier optimization remains disabled by the frozen independent contract |

## Implementation order and status

| Increment | Current execution status |
|---|---|
| P0: baseline and contracts | Five registered input hashes verified; carrier admission blocked |
| P1: private DVC storage | Mac recovery and failure controls passed; independent Kali recovery pending |
| P2: FTS5 and Qwen | Retrieval controls and actual PorscheFanatics metadata import passed; generated Qwen draft rejected |
| P3: CloudCompare | Native Linux analytical controls passed; no measured carrier scan registered |
| P4: SALOME/SMESH | Native cube/bore controls passed; carrier comparison blocked pending reviewed face groups |
| P5: OpenTURNS | Analytical control passed; carrier sensitivity requires verified solver responses and reviewed ranges |
| P6: OpenMDAO and replay | Beam optimum and carrier admission replay executed; native carrier FEM replay unexecuted |

The [execution report](RESULTS.md) records the accepted scope and remaining
deployment work. Software controls do not close the carrier's engineering gates.

## Quick start: small offline software tests

From the repository root, using Python 3.10 or newer:

```sh
make free-tools-check
python3 benchmarks/free-tools/knowledge.py build --output work/free-tools-index-new
python3 benchmarks/free-tools/knowledge.py context \
  --database work/free-tools-index-new/index.sqlite \
  --question 'Which interfaces of 993 115 021 53 have been measured?' \
  --output work/free-tools-context-new.json
python3 benchmarks/free-tools/pilot.py replay --output work/free-tools-carrier-new
```

The last command verifies the registered artifact hashes and writes
`blocked_engineering`. That is the expected carrier admission result. It is
not a completed FEM replay. Always use new output names.

The supplied benchmark corpus consists of owner-authored source summaries and explicitly
synthetic conflict/injection fixtures. It is **not a live PorscheFanatics
export**. [PorscheFanatics.com](https://porschefanatics.com/) remains our Porsche
information catalogue. An authorized, reviewed export can replace this snapshot
through the documented metadata exporter/importer contract; there is no crawler or automatic
publication. Do not put restricted manuals or private scans in the corpus.

## Runtime and execution evidence

Install optional Python tools into a new environment, separate from Qwen/MLX:

```sh
uv venv --python 3.12 work/free-tools-env
uv pip install --python work/free-tools-env/bin/python \
  -r benchmarks/free-tools/requirements.lock.txt
OPENMDAO_REPORTS=0 work/free-tools-env/bin/python \
  benchmarks/free-tools/acceptance.py \
  --private-root "$HOME/Developer/PorschePartsArtifacts/free-tools-new" \
  --output work/free-tools-acceptance-new
```

The acceptance command restores real registered carrier inputs and runs the
native Python controls. It explicitly reports CloudCompare, SALOME and Kali
restoration as unexecuted by that command. Their separate receipts are required
before calling the full deployment accepted. It creates no paid infrastructure.

See [the execution report](RESULTS.md) for measured results and remaining
blockers. Dependency versions are frozen in the
[isolated Python lock](../../../benchmarks/free-tools/requirements.lock.txt).
The native geometry images use separate immutable base digests; the SALOME
distribution is maintained by Simvia, not built from source by this project.

## Boundaries that remain unchanged

- `catalog/parts/*.json` is the part source of truth.
- Missing exact-variant hole centres, axes, mating faces, datums, tolerances
  and load evidence remain unknown.
- Existing certificates and reaction/stress-energy limits remain authoritative
  for their own revisions. These tools cannot weaken or replace them.
- No new training, model-default change, mesh repair, historical archive
  migration, manufacturing release or automatic website publication occurs.
- No daemon, public API or new cluster scheduler is introduced.
