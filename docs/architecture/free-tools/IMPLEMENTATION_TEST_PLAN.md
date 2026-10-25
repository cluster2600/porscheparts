# Implementation, tests and recovery

## Ordered delivery and traceability

| Requirement | Component | Increment | Test | Execution receipt |
|---|---|---|---|---|
| FT-BASELINE: preserve carrier authority | A-GATE, D-CAT | P0 | Registered SHA-256 manifest and blocked admission replay | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) |
| FT-RESTORE: independent recoverable copies | A-DVC, D-PRIMARY, D-COPY | P1 | Fresh-cache restores from both actual hosts | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) (Kali pending) |
| FT-SOURCES: referenced local context | A-SEARCH, A-QWEN | P2 | Frozen 30-case retrieval evaluation; separate inference receipt | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) |
| FT-DISTANCE: bounded diagnostic distances | A-METRO | P3 | Identity, 1 mm offset and rigid-transform native controls | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) |
| FT-MESH: unchanged boundary and conversion | A-MESH | P4 | Cube/bore NETGEN controls, exact determinant/boundary checks and INP readback | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) |
| FT-SENSITIVITY: known sensitivity recovered | A-UQ | P5 | Fixed-seed analytical indices within 0.03 | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) |
| FT-OPTIMIZATION: independently replayed optimum | A-OPT | P6 | External beam worker, closed-form comparison and independent replay | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) |
| FT-GATES: no automatic carrier promotion | A-GATE, B-REVIEW | P0–P6 | Missing interfaces and convergence keep optimization disabled | [Published receipts](../../../benchmarks/free-tools/results/mac-20261025.json) |

The [source manifest](../../../benchmarks/free-tools/baseline.json) freezes
the catalogue record, independent assembly contract, R2 study parameters,
auxiliary surface and convergence report at the recorded source revision.
Its public inputs are already published study data. Existing private archives
are not migrated. A different baseline requires a separate reviewed change.

## Environment and commands

Use the isolated Python environment from the [quick start](README.md).
Below, `work/free-tools-env/bin/python` is the tool interpreter; it is not the
Qwen/MLX interpreter. The CLI entrypoints live in
[`benchmarks/free-tools`](../../../benchmarks/free-tools/).

### P1: private DVC storage and Mac recovery

Set a **new**, private artifact root outside every Git checkout:

```sh
FREE_TOOLS_STORE="$HOME/Developer/PorschePartsArtifacts/free-tools-new"
work/free-tools-env/bin/python benchmarks/free-tools/storage.py archive \
  --manifest benchmarks/free-tools/baseline.json --root "$PWD" \
  --workspace "$FREE_TOOLS_STORE/source" --store "$FREE_TOOLS_STORE/store-mac"
work/free-tools-env/bin/python benchmarks/free-tools/storage.py restore \
  --metadata "$FREE_TOOLS_STORE/source" \
  --workspace "$FREE_TOOLS_STORE/restore-mac" --store "$FREE_TOOLS_STORE/store-mac"
```

Metadata, DVC configuration, logs and object paths stay private. Restore creates
an empty new DVC workspace/cache, pulls artifacts, then verifies each registered
SHA-256. Existing outputs are rejected. No archive deletion or DVC garbage
collection is performed.

### P1: independent Kali copy and recovery

First establish the actual SSH user, host, port and trusted host key. Use the
existing identity and a native Linux filesystem; do not use `/mnt/c`. Verify
hostname, architecture, available space and the destination. Do not accept an
unknown or changed key automatically.

For an established identity, substitute its actual values below:

```sh
work/free-tools-env/bin/python benchmarks/free-tools/storage.py replicate \
  --metadata "$FREE_TOOLS_STORE/source" \
  --store 'ssh://USER@HOST:22/home/USER/PorschePartsArtifacts/free-tools-new/store'
work/free-tools-env/bin/python benchmarks/free-tools/storage.py restore \
  --metadata "$FREE_TOOLS_STORE/source" \
  --workspace "$FREE_TOOLS_STORE/restored-from-kali" \
  --store 'ssh://USER@HOST:22/home/USER/PorschePartsArtifacts/free-tools-new/store'
```

DVC manages local content objects; the SSH adapter transfers them using native
OpenSSH/rsync with `BatchMode=yes`, `StrictHostKeyChecking=yes` and no agent
forwarding. It deliberately avoids the installed DVC SSH backend: its sshfs
transport defaults to disabling known-host verification. No password or private
key is read by our code. Use an rsync version supporting `--protect-args`.

A successful replication command reports `replicated_restore_required`.
Only the second command provides recovery evidence. Two directories on the
same Mac are a software control, not a Kali backup. Retain incoming/export
staging stores until the accepted recovery has been independently recorded.

### P2: documentary context and optional Qwen draft

```sh
python3 benchmarks/free-tools/knowledge.py build --output work/free-tools-index-new
python3 benchmarks/free-tools/knowledge.py evaluate \
  --database work/free-tools-index-new/index.sqlite \
  --output work/free-tools-retrieval-new.json
python3 benchmarks/free-tools/knowledge.py context \
  --database work/free-tools-index-new/index.sqlite \
  --question 'Quels perçages du support 993 sont mesurés ?' \
  --output work/free-tools-context-new.json
```

An authorized snapshot is JSON with `authorization` set to
`owner_authored_or_approved_export` and a `documents` list. Each document has
unique `id`, `title`, bounded `text`, `source`, `rights` and `scope` strings;
`conflict_group` is optional. This declaration is an operator-reviewed input,
not a licence grant. The sample corpus is authored paraphrase plus explicitly
synthetic adversarial controls. Preserve source rights and evidence levels.

FTS5 queries normalize spaced/dotted/hyphenated OEM references. The snapshot
digest is checked before every query; rebuilding is mandatory after any change.
Queries are parameterized and excerpts are never executed.

To include our actual PorscheFanatics catalogue, export only the carrier's
identity metadata from the local source checkout (read-only), then build a
production snapshot:

```sh
python3 benchmarks/free-tools/knowledge.py export-porschefanatics \
  --catalogue-root /path/to/porschefanatics.com \
  --output "$FREE_TOOLS_STORE/porschefanatics-metadata.json"
python3 benchmarks/free-tools/knowledge.py snapshot --root "$PWD" \
  --porschefanatics-export "$FREE_TOOLS_STORE/porschefanatics-metadata.json" \
  --output "$FREE_TOOLS_STORE/production-snapshot.json"
python3 benchmarks/free-tools/knowledge.py build \
  --snapshot "$FREE_TOOLS_STORE/production-snapshot.json" \
  --output work/free-tools-production-index-new
```

The exporter records the source-file hash, Git revision and working-tree state.
It imports only identifiers, names and generation: no PET excerpts, notes,
dimensions, prices, material claims or supplier content. It does not assert that
the local checkout matches the live website. Production snapshots exclude the
synthetic conflict/injection corpus entries. Add `--porschefanatics-export` to
`acceptance.py` to include that export in an integrated local replay.

Optional documentary inference uses explicit existing local directories:

```sh
work/free-tools-env/bin/python benchmarks/free-tools/knowledge.py draft \
  --brief work/free-tools-context-new.json \
  --runtime "$HOME/Developer/Qwen993/venv/bin/python" \
  --model "$HOME/Developer/Qwen993/model" \
  --adapter "$HOME/Developer/Qwen993/qualified-20261014-r3/adapters/paired" \
  --output work/free-tools-draft-new
```

This example selects a local experimental documentary adapter explicitly; it
does not assert documentary qualification. Offline mode prevents model downloads.
Model/adapter files are hashed before and after inference. The 120-second
deadline includes load and generation; the owned process group is killed on
timeout. Raw drafts remain private and are never executed.

Strict output requires `answer`, retrieved `source_ids` and nonempty `unknowns`.
Malformed output or invented references is retained and rejected (exit 2).
Passing format/citation checks still requires semantic human review. The
qualified geometry command, request schema, model defaults and native geometry
gate are unchanged. Unsupported carrier recipes remain unsupported.

### P3/P4: native CPU geometry controls

On a working Linux/amd64 Docker host, from a clean checkout:

```sh
docker build --platform linux/amd64 \
  -f containers/free-tools-cloudcompare.Dockerfile -t free-tools-cloudcompare:local .
python3 benchmarks/free-tools/native_container.py cloudcompare \
  --image free-tools-cloudcompare:local --output work/free-tools-cloudcompare-new
docker build --platform linux/amd64 \
  --build-arg "CONTROL_UID=$(id -u)" --build-arg "CONTROL_GID=$(id -g)" \
  -f containers/free-tools-salome.Dockerfile -t free-tools-salome:local .
python3 benchmarks/free-tools/native_container.py salome \
  --image free-tools-salome:local --output work/free-tools-salome-new
```

The runner checks image OS/architecture and executes the image ID it inspected.
It permits one owned container with two CPU equivalents, 4 GiB RAM, 256 PIDs,
no network, read-only root and a 600-second deadline. It removes only its own
container ID on exit. SALOME's base is a large third-party maintained distribution
pinned by digest. Only the free NETGEN algorithm is invoked; no commercial
meshing plugin is selected.

For a CloudCompare diagnostic, call `cloudcompare.py compare` with `--cloud`
(XYZ-only points), `--mesh` (triangular OBJ or published mesh64 surface),
`--configuration` and fresh `--output`. The configuration declares `units: mm`
and a finite proper rigid 4×4 `cloud_to_reference` matrix. No scale fitting,
ICP alignment or automatic repair is performed. Preserve the independent
registration evidence. Outputs are distances, a diagnostic SVG and a receipt.

For a carrier volume comparison, call `salome_worker.py mesh` in the SALOME
runtime with `--surface`, `--groups`, `--units mm`, `--max-size` and a fresh
`--output`. Groups are a reviewed JSON mapping from names to zero-based input
triangle indices. Missing groups must be resolved from the independent case
definition; never guess support faces. The worker retains input node coordinates
and face connectivity, checks exact positive tetrahedral determinants and whole
boundary identity, then round-trips a C3D4 INP export and node sets.
The fixed SALOME-to-C3D4 node permutation is `[0, 2, 1, 3]`, following the
outward bottom-face convention in
[SMDS 9.16](https://github.com/SalomePlatform/smesh/blob/V9_16_0/src/SMDS/SMDS_VolumeTool.cxx).
It applies uniformly; cells are never individually flipped to hide inversions.
The native MED mesh and raw connectivity are retained before verification.

These checks do not prove force transfer, mechanical convergence or process
qualification. Before any new carrier FEM solve, rerun the existing interface,
equilibrium and stress-energy gates with unchanged criteria. The registered
carrier remains blocked; this integration does not silently rebuild its load case.

### P5/P6: native analytical studies and carrier admission

```sh
OPENMDAO_REPORTS=0 work/free-tools-env/bin/python benchmarks/free-tools/studies.py \
  sensitivity --output work/free-tools-sensitivity-new
OPENMDAO_REPORTS=0 work/free-tools-env/bin/python benchmarks/free-tools/studies.py \
  optimization --output work/free-tools-optimization-new
OPENMDAO_REPORTS=0 work/free-tools-env/bin/python benchmarks/free-tools/studies.py \
  carrier --root "$FREE_TOOLS_STORE/restore-mac/payload" \
  --output work/free-tools-external-carrier-new
```

OpenTURNS uses seed 2600, 8,192 base samples and the analytical model
`x1 + 2*x2` with independent uniform inputs. Expected first-order sensitivity
indices are 0.2/0.8, each within an absolute 0.03. Failed/nonfinite samples reject
the run; no sample is silently dropped. Carrier ranges and probability models
are not synthesized from a single nominal study value.

OpenMDAO runs a separate analytical beam process for each evaluation. It
minimizes mass subject to tip deflection, in explicit SI units. The optimum
thickness must match an independent closed form within 0.5%; a separate replay
checks mass and feasibility. The carrier external component instead replays
the independent admission contract and records its blockers. It does not claim
to have rerun or optimized the carrier's native FEM model.

## Test matrix and execution levels

| Area | Cases | Acceptance |
|---|---|---|
| Common boundary | Nonfinite/bool values, path escape, symlink, stale hashes, existing outputs, owned-child timeout | Reject; previous artifacts remain intact |
| DVC | Empty-cache restores from independent stores, corrupt/missing object, simulated interrupted transfer | SHA-256 matches or no success receipt |
| Retrieval | 10 English/French references, 10 unknowns, 5 conflicts, 5 hostile cases | ≥9/10 top-five references; all authority/refusal boundaries pass |
| Qwen draft | Malformed JSON, invented citations, dropped unknowns, extra authority field | Reject draft; never execute it |
| CloudCompare | Identity, 1 mm offset, rigid transform, invalid units/coordinates | Absolute error ≤0.0001 mm on synthetic controls |
| SALOME | Cube/bore, open shell, inverted tet, changed boundary, group/INP readback | Exact registered topology/coordinate checks |
| OpenTURNS | Known indices, failed sample, NaN sample | Fixed tolerance without discarded evaluations |
| OpenMDAO | Known optimum, independent replay, infeasible target, wrong units/NaN, process timeout | Fail or pass explicitly; carrier remains blocked |

Run `make free-tools-check` with a bare interpreter for boundary tests. Optional
native dependencies produce named skips. Repeat with the isolated tool
interpreter for DVC/OpenTURNS/OpenMDAO native tests. Native CloudCompare/SALOME
containers have a dedicated GitHub Actions workflow; its receipts bind actual
source revision and image IDs. CI execution is not a Kali deployment receipt.

Before proposing a merge, run full `make check`, strict documentation links and
Mermaid rendering. Render each Mermaid block in `ARCHITECTURE.md` with
`@mermaid-js/mermaid-cli@11.12.0`, storing generated SVGs under ignored `work/`.
Inspect each rendered view. Do not translate or modify historical evidence.

## Failure handling and rollback

- **Unreachable Kali/changed key:** record unexecuted status; retain Mac evidence.
  Do not change SSH services or bypass host-key checking.
- **Missing/corrupt artifact:** stop restoration; retain private diagnostics and
  the other independent copy. Never run DVC garbage collection as recovery.
- **Stale corpus or source:** rebuild the derivative in a new directory. Do not
  re-label old receipts as current.
- **Tool timeout/missing output/NaN:** preserve the failed attempt; no acceptance
  follows from process exit alone.
- **Missing physical inputs/convergence:** retain `blocked_engineering` and
  identify required measurements or numerical evidence.
- **Rollback:** stop using the new entrypoints and restore prior configuration.
  Existing catalogue, qualified planner, geometry and solver recipes remain
  unchanged. Retain private DVC objects and receipts until recovery is verified.
