# Terminal-taper native evidence capsule

The three fixed archives preserve the terminal-taper BREP construction and its separate closed checks, surface and T10 meshes, and complete rigid and spring static cases. The member inventory records 495 original paths: 432 common paths, 32 paths in the rigid archive and 31 in the spring archive. The rigid archive stores its 31 complete case paths plus the authenticated shared surface STL at its original destination path. This placement addresses archive capacity; it does not make the shared surface a case-specific geometry. All three archives are required for a complete restoration. Each archive has a strict 100,000,000-byte compressed size limit. Actual archive identities are recorded in `manifest.json`; `archive.json` inventories the complete capsule while excluding itself.

The master is BREP `dde710a2…`. Its exact construction sources, original inputs and complete provenance are retained under their original relative paths. The successful native Build and its post-Build law-gate refusal remain distinct. Native containment, positive addition, sampled surface distances, topology/intersection checks, protected regions and T10 meshing each have their own closed evidence. The independent strict STEP roundtrip is a retained refusal. The protected-stage metadata correction records 11,562 merged pin-map entries and 14 outputs while preserving the original terminal's count discrepancy. The BREP is never disguised as a STEP file.

Both static cases use the retained assumed loads and material model: Fz −4,000 N, My 850,000 Nmm, E 107,000 MPa and ν 0.31. The spring case uses total 1,000 N/mm per eye and axis. Recorded rigid Umax is 2.7940146926593012 mm and VMmax 697.3125042834432 MPa; spring values are 18.17020118428633 mm and 1,977.809950603409 MPa. Independent energy errors are 4.351436988514479e−9 and 1.988860853785468e−9 against the unchanged 1e−4 criterion. Complete global peak ties are retained. No allowable stress, stress convergence, manufacturing qualification or physical validation is established by these calculations.

Stored-byte verification, analysis replay and native reproduction are separate operations. Their execution status belongs to their actual receipts; the existence of the capsule alone supplies no execution claim.

For stored-byte verification, run:

```sh
python3 -I -B restore.py verify --manifest-sha256 <reviewed-manifest-sha256>
```

This stdlib command verifies archive and utility identities, decompresses and hashes every preserved original byte stream, and checks the complete final file inventory. To restore the originals without reanalysis, use `restore.py restore <fresh-absolute-output> --manifest-sha256 <reviewed-manifest-sha256>`. The output and its ancestors must have no symbolic links, and the output must not exist.

For the four-report analysis replay, use the pinned external Python/NumPy runtime with the owned command's reviewed limits:

```sh
<pinned-python> -I -B replay_analysis.py <fresh-absolute-output> \
  --manifest-sha256 <reviewed-manifest-sha256> --numpy-site <pinned-numpy-site>
```

The execution contract requires cwd `/`, nice 10, BLAS 1, zero workers, an outer 180-second owned supervisor, the actual 150-second child alarm and CPU 140/141. It restores the 495 original paths once, recomputes the two complete independent energy reports and two global-peak reports, and requires whole-object equality and byte-identical serialized JSON for all four. It checks every restored original afterwards, plus the interpreter and 499 NumPy files before and after. The disk guard reserves the complete raw archive total plus 72 MiB. It invokes no CAD kernel, mesher or CCX. Its actual result is recorded separately in `reanalysis-receipt.json` and the owned supervisor/collector evidence.

Native reproduction uses the retained editable geometry, solver/mesh sources and historical command records. `preservation-sources/commands-proposal.json` identifies those exact historical commands and authorities. Their old output paths are immutable. A fresh reviewed rebinding of outputs, runtime paths and owned container names is required for a new native calculation; this capsule supplies neither a new native-run authorization nor a claim that such a run occurred. Runtime installations, raw scans and proprietary material are excluded.

Figure 26 is a separate dependency described by its byte-exact archive descriptor under `dependencies/`; its 39 payloads are not duplicated. The four-report analysis is standalone and restores no unrelated C1/H2 case or figure payload. The preparation-only fixture source under `preservation-sources/selfcheck.py` is historical worktree material, not a portable verification entry point. `restore.py` and `replay_analysis.py` are the portable entry points. `source-derivation.json` preserves exact inverses to the established capsule utilities; the energy, peak, BREP-binding and solver sources remain byte-identical.
