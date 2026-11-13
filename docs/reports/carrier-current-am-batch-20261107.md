# Current carrier AM: nine-layer outcome — 2026-11-07

Nine distinct layers of the current H8 exterior passed native PySLM slicing and hatching, independent section-area checks, and strict scan-path containment checks. This is **9 of 1,034 calendar layers**, including three empty layers. One additional leading calculation reproduced the previously admitted layer 517 byte for byte; the worker therefore made **10 calls**.

The [source intake and actual layer image](carrier-current-am-intake-20261106.md)
and [software coverage ledger](carrier-toolchain-coverage-20261106.md) provide
the surrounding workflow.


The source was the float64 surface with **2,882,300 vertices and 5,764,688 ordered triangles**. Its meshbin SHA-256 is `801e989e4e41d2c6cfc1da828e36726cded7584a9f7c1b321687d2ec538b50bd`; the source `.mesh64` SHA-256 is `c424988e6d946aeb985874929bd163439c04b72d21e2a97f3891f6de7a28611a`. Full import bits, face order, pose, runtime package identities and study parameters were checked again. The 45° Z rotation, 10 mm plate gap and 0.06 mm calendar were unchanged.

| Layer | Z (mm) | Independent area (mm²) | Rings / holes | Hatch segments | Contour segments | Absolute area difference (mm²) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.03 | 0 | 0 / 0 | 0 | 0 | 0 |
| 166 | 9.99 | 0 | 0 / 0 | 0 | 0 | 0 |
| 167 | 10.05 | 11537.16712246544 | 8 / 6 | 6,825 | 38,559 | 1.27e-11 |
| 344 | 20.67 | 4612.121603724234 | 6 / 2 | 9,516 | 26,000 | 2.00e-11 |
| 516 | 30.99 | 12363.242363232335 | 24 / 21 | 13,792 | 69,671 | 1.04e-9 |
| 517 | 31.05 | 12353.793496440707 | 23 / 20 | 13,813 | 70,340 | 1.13e-10 |
| 780 | 46.83 | 4306.184265132884 | 4 / 1 | 13,954 | 33,812 | 1.06e-10 |
| 1032 | 61.95 | 736.33055372726 | 2 / 0 | 3,346 | 11,431 | 4.43e-12 |
| 1033 | 62.01 | 0 | 0 / 0 | 0 | 0 | 0 |

All **61,246 hatch segments and 249,813 contour segments** passed both the original scan-path audit and containment in the independently reconstructed domains. Outside, duplicate and zero-length segment counts were all zero. The independent oracle retains oriented holes and closes cycles by exact source-edge identities; it uses neither tolerance welding nor an enlarged acceptance domain. The original relative area tolerance remains `1e-10`.

The all-plane preflight checked all 1,034 unshifted planes and found no exact coplanar vertex, edge or face. Layer 516 is the only plane within the native `1e-8` proximity threshold of a source vertex: vertex 746245 is `9.536744727256519e-9` mm from the plane. Its local-star analytical controls passed; the actual batch also checked all three crossing edges incident to that vertex against exact rational interpolation. The largest endpoint error was `5.584339743568296e-15` mm, below its derived rounding bound. The plane and native tolerance were unchanged.

The actual run completed with return code 0 in **54.99 seconds**, peaking at **4,402,757,632 bytes aggregate RSS**. One spawned worker was initialized once, with at most two pending layers and one BLAS thread. The limits were 300 seconds, 8 GiB aggregate RSS and an 8 GiB free-space reserve. All workers were reaped and the exact owned process group was independently confirmed absent.

Before the batch, cube/bore, empty-layer, direct-versus-spawned-worker and interrupted-prefix/resume controls passed. Eight negative controls refused altered hashes, source context, calendar, duplicate publication, raw arrays, missing receipts, and changed or missing source-edge archives. Cleanup controls covered a crashed leader with a surviving TERM-resistant descendant, a live group and an already completed child; an unrelated sentinel remained untouched.

The raw arrays remain private. The complete scientific output is **46 explicitly named files, 5,745,085 bytes**; every byte count and hash matched the original inventory during independent readback. The original tree inventory also captured macOS `.DS_Store`, which subsequently changed. That metadata discrepancy is recorded, the original manifest is preserved, and no numerical file was changed or excused. The new scientific readback permits only the exact expected 46 paths plus that explicitly identified Finder metadata file.

The full 1,034-layer calendar, supports and a machine job have not been executed by this batch. The source bundle is not yet runnable from a public clone: the actual commands use preserved local AM011 packages, ignored adapters and private input/reference arrays. Runtime reconstruction and a retained entrypoint remain explicit follow-up work.

## Receipts

| Artifact | SHA-256 |
|---|---|
| [Public scalar summary](carrier-current-am-batch-20261107/batch-public-summary.json) | `fd045dbd9cc8630fc31a1b0d6a3a7b2fa07343659eb246eabd8455819fe432bf` |
| [Exact scientific readback](carrier-current-am-batch-20261107/batch-scientific-readback.json) | `243ab8bec499003c922505133390a30dc89b04e01989e4449898bafb70fd1791` |
| Native/independent result | `898a284a47d62cd2b832eaa9503b5f9d026ab397942b02b33c3ecabbcaa4483f` |
| Terminal and exact-group closure | `be33d67f5ab62d76fc815249454d24bec63b6668b42f0a76395490d12aba80db` |
| Original private-tree inventory | `1cfdc041fbb87d55f57fb3e69585779096f73c6a4116d03b13526159b62a118c` |
| Leading layer-517 byte parity | `46d982710e27cd6cc8f85229811c4ecd2e611d07468912e0a2a6f461b2148098` |

## Actual command

Run from the original calculation checkout; paths are local evidence dependencies, not a portable installation recipe.

```sh
/opt/homebrew/Cellar/python@3.11/3.11.18/bin/python3.11 -I -B -S work/carrier-current-am-intake-20261106-001/supervise_current_batch_v2.py --phase batch
```

This exclusive run has completed. Reusing the command refuses its existing start intent; it must not overwrite the receipts.
