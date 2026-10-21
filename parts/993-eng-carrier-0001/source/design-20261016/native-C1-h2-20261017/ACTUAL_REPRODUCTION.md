# Closed C1 h/2 capsule and actual analysis reproduction

This is the current reproduction companion. All thirteen captured capsule files, including `README.md` and the manifest, retain their original bytes. The closed verification and replay below are additional evidence, rather than edits to those captured sources.

The three H2 ZIPs add 234 files to the sibling `native-C1-20261017` capsule's 186 files. They contain complete new INP/NPZ/DAT/FRD outputs and the refinement, paired-volume, qualification and two-case records. Existing coarse fields and the 577f surface are inherited without another ZIP copy. The new ZIPs are 16,550,574, 68,544,991 and 69,008,962 bytes; each is strictly below 100 MB. The combined restoration is 420 files and 817,671,713 raw bytes. Runtimes are not included.

The actual owned verification closed RC0 in 6.256 s and streamed every original member without creating a restored raw tree. The separately approved replay closed RC0 in 25.547 s, with one combined restoration, all four complete reports identical both as JSON objects and serialized bytes, all 420 original hashes unchanged and all 500 runtime files unchanged. Its owned child was reaped, its group was empty and stderr was empty. The root independently closed both stages. This was extraction and analysis of existing native outputs: no CCX, Gmsh, CAD kernel or refinement was rerun.

The retained collector-only refusal concerns an over-strict symlink check on the already pinned venv Python executable. It occurred after the successful numerical replay. The subsequent stdlib collection completed without repeating that analysis or editing a frozen source.

| H2 case | Maximum displacement, mm | Global IP von Mises, MPa | Relative energy error |
|---|---:|---:|---:|
| Rigid | 2.794565820 | 996.757555 | 8.555242736e-9 |
| K1000 per eye and axis | 18.174421153 | 2996.496111 | 2.509120423e-8 |

The same-master coarse-to-H2 stress peaks rise by 9.86% and 12.52%; stress convergence is not established. Energy retains its 1e-4 threshold and all global peaks are retained, including C2. The common H2 maximum is element90371/IP2, at reference XYZ [82.162332198, -14.460778140, 12.883191321] mm. The material, Fz=-4000 N and My=850000 Nmm, six BC rosters, total1000 N/mm per eye and axis, and protected entities remain those of the actual coarse C1 comparisons.

The existing mesh qualified under the separately closed same-operator serialized-volume comparison and full size measurement. The earlier float-volume refusal remains unchanged. The full measured local h is 0.46689542695319447 mm, below the fixed target0.4668954269534402 mm. The native BREP remains the CAD master; refused STEP exchanges are not promoted.

## Check the durable publication and archives

From the repository root, with the existing sibling C1 capsule present:

```sh
python3 -I -B parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017/check_publication.py
python3 -I -B parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017/test_publication.py
python3 -I -B parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017/restore.py verify --manifest-sha256 3e61c6a688a80e8bf7062a7e2d6090921fdc87007d7e8865799951494b97f5d6
```

The first command checks complete publication files and closed proof links without decompression. The third verifies decompressed original bytes without extracting a raw tree. `archive.json` accounts for every durable file except itself. `evidence/` contains actual GO files, plans, logs, supervision, terminal collections, root closeouts and the four reproduced reports. `sources/supervise.py` is the exact historical4d18 source snapshot for provenance; its captured workspace-relative launch plans are historical evidence, not a new portable runtime.

## Repeat analysis only, using the documented installed runtime

Set absolute paths to the relocated repository, its existing Python/NumPy and a fresh output. The executable must match the inherited runtime descriptor; a different NumPy/runtime is refused. At least818,733,127 free bytes are checked before restoration and four-report output.

```sh
repo=/absolute/path/to/3dprinting993
capsule="$repo/parts/993-eng-carrier-0001/source/design-20261016/native-C1-h2-20261017"
python="$repo/work/part-workflow/runtimes/geometry-standalone/bin/python"
numpy="$repo/work/part-workflow/runtimes/cad-base/lib/python3.10/site-packages"
fresh="$repo/work/C1-h2-ANALYSIS-NEW"
(cd / && /usr/bin/nice -n 10 /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$python" -I -B "$capsule/replay_analysis.py" "$fresh" \
  --manifest-sha256 3e61c6a688a80e8bf7062a7e2d6090921fdc87007d7e8865799951494b97f5d6 \
  --numpy-site "$numpy")
```

The replay itself retains150 seconds and CPU140/141 seconds. The actual closed execution additionally used supervisor4d18 with180 seconds total, including10+10 seconds cleanup, one BLAS thread and zero workers. A local reanalysis does not establish stress convergence, a strength allowable, physical fit or manufacturing release.
