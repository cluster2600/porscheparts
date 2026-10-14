# PicoGK and Qwen on the project Mac

**Verified on 12 October 2026.** This page documents the installed software,
the repaired Qwen runtime, the checks performed and their limits. The
[recovery results](../training/qwen-picogk-20261012/recovery-results.json)
contain versions, hashes and measured outputs. Weights, private run packages,
native binaries and editor downloads remain outside Git.

## Use the installed environment

```sh
picogk check
picogk viewer
picogk simulation
code ~/Developer/PicoGK/PicoGK.code-workspace
```

`check` exercises five bounded native recipes and voxel VDB roundtrips.
`viewer` opens a real interactive window; close it to exit. `simulation`
exports and reloads synthetic fields. It does not run a CFD solver. The
editable C# entry point is `~/Developer/PicoGK/Workbench/Program.cs`.
VS Code loads `PicoGK.sln`: **F5** builds and launches the viewer, while
**Cmd+Shift+B** builds the project.

The repaired Qwen command proposes a bounded parameter plan:

```sh
qwen-picogk \
  --prompt 'ShapeKernel pipe: length 18 mm, outer diameter 14 mm, bore diameter 6 mm.' \
  --output ~/Developer/Qwen993/output/my-pipe.json
```

Use a new output filename in an existing directory. Previous outputs are
rejected. The command loads the retained experimental adapter, uses greedy
decoding, requires EOS and checks the literal JSON schema. It generates no C#
and executes no geometry. A structurally valid response still requires a
separate authored dimensions contract and independent geometry inspection.

## Installed software

| Component | Installed version / pinned source | Verification |
|---|---|---|
| VS Code | 1.141.0, Apple Silicon | Official archive checksum and deep/strict application signature |
| Microsoft C# extension | 2.160.4 | Solution and project loaded |
| .NET Install Tool extension | 3.2.0 | C# language-server dependency installed |
| Editor language-server runtime | 10.0.12, arm64 | Acquired by Microsoft's extension |
| Project .NET SDK / runtime | 9.0.317 / 9.0.19 | Build and native execution |
| PicoGK | 2.3.0, native 26.2 ARM64 | Native recipes, exports and viewer |
| ShapeKernel | `554bce4791d2676ed00bd6704f6eb010111a7fd3` | Cylinder and pipe |
| LatticeLibrary / ImplicitLibrary | `81c3c7b2064c19e573c38d76ac09bf1cd2f562d5` | BCC cell |
| PicoGK-Fasteners | `7ddcf0e9ca76fdfcbe75b3bae2537199e84e73cf` | Explicit-dimension washer |
| HelixHeatX | `a0a0234eb048b6963fb5787fce8315c7b0110b5c` | Synthetic thread cutter |
| SimulationExample | `9e98c1acacad41ac26609cc873cdae35cb73c2d9` | Four CC0 source files compile; field export/import |
| Qwen Python | 3.12.11 | Separate environment under `~/Developer/Qwen993` |
| MLX / MLX-LM / Transformers | 0.32.3 / 0.31.3 / 5.17.0 | Adapter loading and three model requests |

The workbench compiles 91 upstream C# files and its own entry point, with zero
errors and 55 upstream obsolete-method warnings. The full libraries are
available as source; the witnesses do not establish every API's behaviour or
the model's mastery of them. The original SimulationExample entry point and
large device geometry were not executed.

The [upstream simulation example](https://github.com/leap71/PicoGK_SimulationExample)
prepares domains and fields. Five names/types were checked: fluid and solid
voxel domains, density and viscosity scalar fields, and a velocity vector
field. Both domains survive exactly; 61 probes preserve prescribed scalars
and finite velocities. No pressure-drop, thermal or inlet-performance result
follows from this data roundtrip.

## Failure and repair

The earlier model runtime lived inside a Codex worktree and is now absent.
The older r2 dataset manifest contains 11 unavailable external paths: nine
base-model/tokenizer files and two coding-008 parent checkpoint files. Their
absence was discovered during inventory; the software installation did not
delete them. The cause of their absence is unverified.

The base was restored from the same public repository and immutable revision:

- Repository: [mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit).
- Revision: `b3252a2f97102b1fb1571fec2c9b27219a8536be`.
- Weights SHA-256: `daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58`.
- All nine restored files match their historical hashes byte for byte.
- Retained r3 adapter SHA-256: `2f5da92d4cf9dff0f8b6bac8b28d5c34d26323ca780adf18cdcf11dd88249e1f`.

Downloads used ordinary certificate verification and no authentication. The
completed r3 run was copied to the durable runtime; all 1,130 files match its
original manifest. Its adapter configuration retains the historical training
model path. That receipt was not rewritten: inference supplies the relocated
base explicitly to MLX-LM.

The [inference command](../training/qwen-picogk-20261012/ask.py) accepts
`--runtime-root`. Recovery mode verifies the pinned completed-run manifest,
every file in that run, the nine base files, the selected adapter and three
package versions before loading the model. It then applies the original
validation, retention and test eligibility gates. Changed files and escaping
run paths fail closed. Omitting the option keeps historical verification.
The training verifier and frozen manifests were not changed.

The [recovery profile](../training/qwen-picogk-20261012/recovery-profile.json)
pins this specific retained r3 run; it cannot admit arbitrary adapters. The
two original coding-008 checkpoint files remain unavailable. They are not
needed to load the completed r3 adapter, but their absence prevents claiming
full historical training reproduction. The old native-gate manifest also
references them, so complete historical gate verification was not claimed.

## Durable files and rebuilding

| Path | Purpose |
|---|---|
| `~/Developer/PicoGK/sdk` | Standalone project SDK |
| `~/Developer/PicoGK/runtime` | PicoGK native dependencies and assemblies |
| `~/Developer/PicoGK/libraries` | Public source copies and licence notices |
| `~/Developer/PicoGK/Workbench` | Editable C# project and build/debug settings |
| `~/Developer/PicoGK/output` | Unique export directory for every run |
| `~/Developer/PicoGK/setup` | Inventory, build logs and inspected viewer image |
| `~/Developer/Qwen993/model` | Nine hash-verified base files |
| `~/Developer/Qwen993/run-001` | Verified copy of the retained r3 run |
| `~/Developer/Qwen993/source` | Standalone inference source and existing imports |
| `~/Developer/Qwen993/venv` | Isolated Python 3.12 environment |
| `~/Developer/Qwen993/output` | Responses and recovery witnesses |
| `~/.local/bin` | `dotnet`, `code`, `picogk` and `qwen-picogk` commands |

The executable copies do not depend on an active Codex worktree. No background
service or serving default changed. The existing PATH already included
`~/.local/bin`; no shell profile was edited. Source snapshots and original
licences remain locally. Only this task's verified VS Code staging ZIP was
removed.

Rebuild the existing C# installation:

```sh
cd ~/Developer/PicoGK
dotnet build Workbench/PicoGK.sln -c Release --configfile Workbench/NuGet.Config
```

Rebuild the Qwen environment from a repository checkout while retaining the
existing model and run package, using a new virtual-environment directory:

```sh
uv --no-config venv --python 3.12 ~/Developer/Qwen993/venv-rebuilt
uv --no-config pip sync \
  --python ~/Developer/Qwen993/venv-rebuilt/bin/python \
  --default-index https://pypi.org/simple --keyring-provider disabled \
  training/m64-qwen/requirements.lock
~/Developer/Qwen993/venv-rebuilt/bin/python \
  training/qwen-picogk-20261012/ask.py \
  --work ~/Developer/Qwen993 --runtime-root ~/Developer/Qwen993 \
  --prompt 'Cylindre plein ShapeKernel : longueur 12 mm, diamètre 12 mm.' \
  --output ~/Developer/Qwen993/output/rebuilt-cylinder.json
```

The lock requires Python 3.12 or later: an initial empty Python 3.11 environment
could not satisfy NumPy 2.5.3 and was replaced before installing packages.
Do not loosen hashes, edit historical receipts or replace retained weights to
make checks pass. On a fresh machine, obtain the authorised private retained
run separately and download the public base at the revision above, then verify
the recovery profile before inference. This page is an installation record
and recovery procedure, not a complete fresh-machine installer.

## Recovery evidence and limits

Three pre-authored requests produce their expected plans: an English pipe,
a French cylinder and refusal to infer missing 993 mounting interfaces.
These are availability smokes, not a fresh unseen benchmark or evidence of
improved training quality.

The pipe dimensions were fixed in the protocol before inference. A separate
native-host witness produces 13,688 raw STL triangles and 2,259.9094 mm³ native
volume at 0.5 mm voxels. The existing auditor finds no degenerate faces,
boundary or non-manifold edges, with consistent winding and a closed surface.
The saved VDB contains the original native field, with identical volume and
bounds after reload. No mesh repair or STL-to-VDB reconstruction was applied.
This direct witness verifies 260 historical source/runtime inputs, including
the relocated base; it does not reproduce the full historical gate containing
the unavailable training parent.

Six focused unit checks cover the original inference boundary and recovery
identity/corruption/path checks. The result metadata records full repository
verification status. No new training, serving-default change, CFD solve,
fitment check or manufacturing qualification was performed.

The real native viewer image was inspected. VS Code loaded the solution and
its configured debug launch wrote another frame. The Mac then locked; the
owner requested completion without the last visual debugger inspection. That
inspection remains unchecked.

Vendor references: [VS Code on macOS](https://code.visualstudio.com/docs/setup/mac),
[PicoGK](https://github.com/leap71/PicoGK),
[MLX-LM](https://github.com/ml-explore/mlx-lm).
