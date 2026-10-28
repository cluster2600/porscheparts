# R1 local geometry at d64 reference stress locations

These are observations on R1 CAD `240109ca…`. The integration points and four corner probes come from the two closed d64 meshes. This is not R1 stress, a global minimum-thickness proof, a singularity conclusion or strength/convergence admission. Every source assessment retains all 243 face and 738 edge distances per probe, all nearest supports, native D2 values, every normal-line hit and every unresolved qualifier.

| Reference | Probe | First sorted fresh R1 face | Distance (mm) | Local chord to face (mm) | D2/support status |
| --- | --- | ---: | ---: | --- | --- |
| coarse_spring | case_IP | 60 | 0.10933070823016507 | 0.31256727553046826 to 62 | native_D2_at_reported_UV |
| coarse_spring | corner_0 | 62 | 5.6954332954295945e-14 | 1.1941251886501321 to 11 | native_D2_at_reported_UV |
| coarse_spring | corner_1 | 11 | 4.7853945490253771e-13 | unresolved | closest_support_not_face_interior |
| coarse_spring | corner_2 | 62 | 0 | unresolved | closest_support_not_face_interior |
| coarse_spring | corner_3 | 11 | 2.9851252545540781e-13 | 1.5416676484724898 to 62 | native_D2_at_reported_UV |
| refined_common | case_IP | 62 | 0.033699866265840456 | 0.23056240699762537 to 60 | native_D2_at_reported_UV |
| refined_common | corner_0 | 62 | 4.4089448717458563e-13 | 0.01899191203146347 to 60 | native_D2_at_reported_UV |
| refined_common | corner_1 | 62 | 0 | unresolved | closest_support_not_face_interior |
| refined_common | corner_2 | 62 | 3.8402599978290234e-13 | 0.59763507493400581 to 11 | native_D2_at_reported_UV |
| refined_common | corner_3 | 60 | 0.019228687245384839 | 0.37205393967536071 to 62 | native_D2_at_reported_UV |

Face IDs in this table are native zero-based IDs from these R1 queries only. “First sorted” follows the retained distance/index order; it does not manufacture uniqueness at an edge or vertex. A chord is reported only when the original first-in/out normal-intersection qualifier passed. Native resolution is 0.0000446679483124578 mm; no threshold changed.

The refined-reference integration point has a 0.23056240699762537 mm local chord from planar face 62 to curved face 60. Its corner 0 has a 0.01899191203146347 mm local chord between the same two fresh supports. This demonstrates a locally thin region in R1 at those probes; it does not establish where a future R1 stress maximum lies.

All qualified nearest-support chords are retained below (including additional supports; none is removed to improve the interpretation):

| Reference | Probe | Fresh R1 face → target | Local chord (mm) |
| --- | --- | --- | ---: |
| coarse_spring | case_IP | 60 → 62 | 0.31256727553046826 |
| coarse_spring | case_IP | 62 → 60 | 0.30163861323217178 |
| coarse_spring | case_IP | 68 → 149 | 2.1883823960059767 |
| coarse_spring | case_IP | 149 → 68 | 2.1883658270915003 |
| coarse_spring | corner_0 | 62 → 11 | 1.1941251886501321 |
| coarse_spring | corner_0 | 11 → 62 | 0.75543729478544641 |
| coarse_spring | corner_0 | 68 → 149 | 2.1873601993912715 |
| coarse_spring | corner_0 | 149 → 68 | 2.1873538902346059 |
| coarse_spring | corner_1 | 68 → 149 | 2.1872021036195206 |
| coarse_spring | corner_1 | 149 → 68 | 2.1871976085291762 |
| coarse_spring | corner_3 | 11 → 62 | 1.5416676484724898 |
| coarse_spring | corner_3 | 62 → 11 | 0.97541809250801503 |
| coarse_spring | corner_3 | 68 → 149 | 2.188870114284613 |
| coarse_spring | corner_3 | 149 → 68 | 2.1888308201559248 |
| refined_common | case_IP | 62 → 60 | 0.23056240699762537 |
| refined_common | case_IP | 60 → 62 | 0.18916726119551508 |
| refined_common | case_IP | 68 → 149 | 2.1886930857872131 |
| refined_common | case_IP | 149 → 68 | 2.1886768410959108 |
| refined_common | corner_0 | 62 → 60 | 0.01899191203146347 |
| refined_common | corner_0 | 60 → 62 | 0.012947982194481428 |
| refined_common | corner_0 | 68 → 149 | 2.1879109000957455 |
| refined_common | corner_0 | 149 → 68 | 2.1878996509529967 |
| refined_common | corner_2 | 62 → 11 | 0.59763507493400581 |
| refined_common | corner_2 | 60 → 62 | 0.37961440200031532 |
| refined_common | corner_2 | 68 → 149 | 2.1880425363775298 |
| refined_common | corner_2 | 149 → 68 | 2.188030366891716 |
| refined_common | corner_3 | 60 → 62 | 0.37205393967536071 |
| refined_common | corner_3 | 62 → 60 | 0.27170835445012209 |
| refined_common | corner_3 | 68 → 149 | 2.1889834970641995 |
| refined_common | corner_3 | 149 → 68 | 2.188960925283574 |

Exact X-plane section observations contain 33 and 41 edge records respectively (native type, length, parameter domain and optional native radius). They do not contain sampled curve coordinates or full curve coefficients. A section-outline drawing cannot be reconstructed from these records alone. Any later drawing must either use the saved native normal-line points as clearly labelled local chords, or obtain separately reviewed fresh section geometry; no section shape is invented here.

The original two native jobs are closed; no further CAD operation, mesh, FEA or plotting is performed by this summary. The combined ROOT closure is pending at the time of this frozen summary.
