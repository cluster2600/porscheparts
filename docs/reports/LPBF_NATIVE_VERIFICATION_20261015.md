# LPBF software verification — 15 October 2026

The selected public solvers now have bounded CPU checks. Adamantine's
stress-export defect has been reproduced and corrected through its compiled
native exporter, and a corrected research-profile solver has completed the
shared thermal-elastic coupon against CalculiX and an independent reference.
This establishes a reusable software verification step. It does not establish manufacturing qualification or a validated rotor.

The portable patch, native regression and synthetic shared-coupon inputs are in
[benchmarks/lpbf-adamantine-export](../../benchmarks/lpbf-adamantine-export/README.md).
No measured part geometry, raw scan, full upstream source tree or private
runtime address is included. The
[public observed-results summary](../../benchmarks/lpbf-adamantine-export/coupon/observed-results.json)
binds the actual synthetic Adamantine exports and CalculiX `.dat` output by
relative-path hashes, with source/binary/profile provenance and unchanged
acceptance limits.

## Executed checks

| Software | Pinned source | Executed scope | Result and limit |
| --- | --- | --- | --- |
| Adamantine | `3990489a10902912889617856f6e2e097d52a412` | Native original/corrected `PostProcessor.cc`, both public export paths | Original rejected; corrected 16/16 direct exported cases and a separate CTest producing another 16/16 correct cases. This tests the exporter, not the full coupled solver. |
| Adamantine author image | Embedded `5aca53eeb1048884be54fb48864e9ff6cb9f9b71` | Earlier analytical uniform-heating witness and 20 coupled thermal/mechanical increments | Thermal witness passed; 21 coupled frames reached 20 ms. Original exported stress remains inadmissible because of the confirmed formula defect. No complete cooling/cutoff or convergence claim. |
| GO-MELT | `7dafdd8593711cf8ac6ccb18a1f475744610ea3d` | Unchanged upstream CPU kernels, 32 discrete diffusion increments, laser-source quadrature | Passed discrete thermal references. This used an isolated compatible CPU JAX environment; the upstream CUDA stack and full multilevel driver were not tested. |
| HERMES | `bfa017b5266fda2c0c576135dc8397b458cd5fe5` | Native CPU configuration/path preprocessing and GPU-runtime probe | Preprocessing passed; **zero thermal solver steps**. CuPy/Numba/NVIDIA runtime was unavailable. A 25 °C conversion to 298.0 K exposes an independent −0.15 K offset, unchanged here. |
| AdditiveFOAM | Existing separate programme evidence | No new execution in this increment | Earlier thermal cases remain separate evidence; no new flow, powder or distortion result is claimed. |

The projects were selected in
[M64_GPU_RESEARCH_20260912.md](M64_GPU_RESEARCH_20260912.md). Adamantine is the
candidate for further global thermo-mechanical verification; GO-MELT and
HERMES remain thermal comparison candidates. No production process solver is
qualified by this selection.

## Adamantine root cause and native fix

The original 3D stress scalar counted yz twice and omitted xz. For a pure
1 Pa shear, the independent complete-tensor invariant is √3 Pa:

| Input | Original native export | Corrected native export |
| --- | ---: | ---: |
| Pure xz shear, 1 Pa | 0 Pa | 1.732050776 Pa |
| Pure yz shear, 1 Pa | 2.449489832 Pa | 1.732050776 Pa |

A second defect ignored `output_dir` in the coupled constructor. The native
harness reproduced this by observing a missing coupled VTU in its requested
directory and returning 1. The two-hunk patch fixes the shared stress getter
and that constructor only. The public API and exported field names stay the
same. Old inputs, erroneous fields and rejected assessments remain unchanged.

The corrected source was compiled on Linux x86_64 using GCC 13.3.0 and deal.II
9.6.2 from the pinned author image. Sixteen cases passed through the actual
exporter, followed by CTest 1/1 and independent verification of CTest's sixteen
VTUs. Both public paths cover xy/xz/yz shear, diagonal stress, hydrostatic
stress, a mixed tensor, negative shear and quadrature averaging. The reference
uses the complete symmetric deviatoric tensor, independent of the patched
component expression. Relative and absolute `2e-7` tolerances account for the
Float32 exported fields.

The native binaries had these SHA-256 values:

- Original: `680323923f4d3b0be9dff75eaff6368ed874acd59db04cf459d511fb9a009ca4`.
- Corrected: `d58de49ce53af5d2420faae95f9c55aa017b421fdc648c3b93e5300c271a9013`.

The [upstream provenance](../../benchmarks/lpbf-adamantine-export/upstream.json)
records the original archive hash, original/corrected source hashes, licence
and dependency image. These binaries are not vendored; compilation of the
portable benchmark produces new binaries with their own runtime provenance.
No new Vast rental was needed for the exporter regression.

## Shared thermal-elastic coupon

The [shared contract](../../benchmarks/lpbf-adamantine-export/coupon/contract.json)
defines a hypothetical 12 × 4 × 6 mm single Q1 hexahedron, bottom face clamped,
other faces traction free, with adiabatic uniform heating from 300 to 301 K.
The independent reference is exact for that discrete element, obtained from
its integrated strain energy. It is not a continuum convergence result.

The native arm64 CalculiX 2.21 run completed both 5 ms increments. Maximum
reported errors against the reference were 0 K in temperature, 2.57 × 10⁻¹⁴ m
in displacement and **below 0.432 Pa** across the six stress components. Final mean von
Mises was 1,199,966.324810 Pa versus 1,199,966.340575 Pa expected. Five degraded
output fixtures were rejected by its assessor.

The corrected **research-profile Adamantine executable** compiled in
335.45 s, then completed the coupon in 0.4068 s with exit 0 and `Simulation
done`. Its profile accepts 3D, exactly one material, constant polynomial
properties, host memory and no ensemble. Other combinations are explicitly
rejected by a CLI guard, itself checked with one accepted and six rejected
cases. Although additional phase families and FE degrees are compiled, this
coupon exercises only solid FE1/Gauss elasticity with constant properties.
This does not verify an unrestricted upstream build.

| Final value at 10 ms | Independent Q1 reference | CalculiX 2.21 | Corrected Adamantine research profile |
| --- | ---: | ---: | ---: |
| Uniform temperature, K | 301 | 301 | 301 |
| Maximum displacement, µm | 0.2404887776 | Within 2.57 × 10⁻⁸ µm component error | 0.2404887732 |
| Cell mean von Mises, Pa | 1,199,966.340575 | 1,199,966.324810 | 1,199,966.375 |

All three Adamantine frames at 0, 5 and 10 ms were checked. Its maximum
stored stress-scalar error is **0.034425 Pa**, and the final intersolver
mean-von-Mises difference is **0.050190 Pa**. These are errors of stored
Float32 values evaluated against Float64 references; subtraction must promote
the stored array to Float64 before computing errors, to avoid rounding away
the reference difference. The native fields do not need rerunning for a
checker-arithmetic correction.

The predeclared absolute limits were 10⁻¹² s for output time, 10⁻⁹ m for
coordinates, 10⁻⁴ K for temperature, 10⁻¹² m for each displacement component,
2 Pa for each stored cell-average von Mises scalar, and 4 Pa between solver
means. Every field is finite, eight output points map uniquely to the reference
nodes, and the one-hexahedron topology is checked. Adamantine exports the
cell-average scalar, not the six stress-tensor components; the tensor-component
check above belongs to CalculiX. The comparison protocol SHA-256 is
`5a9b6f26298c111843507065728e8e52004cd5223b1d9f5d6ae80016cc1f0dfd`.

The profile solver binary SHA-256 is
`e7637a1a3729f82c0b11a9a1864fd96b7fbdee9408ede0aad5b59e573699b959`;
its profile-manifest SHA-256 is
`642a7f8c7928a2bf8171162f4928a02c093fc0677956c3c7023d37a12a1b128f`.
The separately packaged
[research profile patch](../../benchmarks/lpbf-adamantine-export/research-build-profile.patch)
reproduces the reduced instantiation domains and CLI guard after applying the
two-hunk production patch. It changes build coverage, not the coupon equations.

Adamantine's quasistatic mechanical solve and CalculiX's uncoupled transient
mechanics are distinct; agreement with the exact static FE reference was
checked at every output before comparing scalar exports. The coupon has no
plasticity, deposition, phase transition, build supports, cooling cycle or
cutoff. No new Vast rental was needed for this native comparison.

## Earlier rejected coupon remains rejected

The previous CalculiX solid-state macro-layer study is a different experiment.
Its coarse/fine equivalent-plastic-strain difference was **16.255962 %**, above
the unchanged **10 %** admission threshold. The h/4 extension exceeded its
600 s deadline, stopped after 600.703 s and retained partial outputs. Neither
result is promoted to an admissible case by this simpler control or the export
fix. Eligible qualified rotor training cases remain zero.

Next numerical work must establish mesh/time convergence and a bounded,
explicitly stated manufacturing model.
Actual rotor LPBF predictions additionally require verified geometry scale and
interfaces, material/process calibration, build orientation, plate and support
geometry, deposition history, thermal boundaries and treatment/cutoff stages.
Physical stiffness, airflow, fatigue and manufacturing acceptance require
appropriate independent tests and engineering review. All manufacturing and
physical-release gates remain closed.

## 18 October replay of the original corrected control

The retained corrected runtime completed the original direct exporter, CTest
and coupled coupon again, with return code 0 at all three native stages.
A separate local assessment then checked their saved outputs without repeating
the native work. The [native completion](carrier-adamantine-historical-links-20261018/native-replay-root-review.json)
and [local assessment closure](carrier-adamantine-historical-links-20261018/local-assessment-root-review.json)
keep execution, assessment and owned cleanup distinct. Earlier mount-setup
refusals remain unchanged.

Both export paths passed **16/16 cases each: 32 checks**, at the original
relative and absolute `2e-7` tolerances. The coupled control passed all three
frames at **0, 5 and 10 ms**. Its maximum observed errors were:

| Quantity | Maximum observed error | Original absolute limit |
| --- | ---: | ---: |
| Temperature | 0 K | 1e-4 K |
| Node coordinate | 1.8998981e-10 m | 1e-9 m |
| Displacement component | 3.4047304e-15 m | 1e-12 m |
| Stored cell-mean von Mises scalar | 0.034424727 Pa | 2 Pa |
| Adamantine–CalculiX mean von Mises | 0.050189510 Pa | 4 Pa |

The original assessor self-test passed its Float32 quantization and XML/VTU
round-trip checks and rejected all **12 invalid field/path fixtures**. Stored
fields remain Float32; the unchanged assessor promotes them to Float64 for
error arithmetic. The nonzero quantization probe remains explicitly recorded.

The [small replay evidence folder](../../benchmarks/lpbf-adamantine-export/coupon/replay-20261018/archive.json)
preserves the four complete original assessment reports byte for byte.
Its [observed summary](../../benchmarks/lpbf-adamantine-export/coupon/replay-20261018/observed-replay.json)
records the exact errors, unchanged limits and source, binary, profile,
protocol and closure hashes. Current raw fields and full runtime evidence
remain in the linked local work directories; this folder makes no portable
full-replay claim.

This is the original hypothetical single-Q1-element software control described
above. It contains no carrier geometry, powder, deposition, melting,
plasticity, supports, cooling or cutoff stages, and supplies no carrier
print-distortion or manufacturing qualification result.
