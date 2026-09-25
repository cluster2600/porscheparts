# Editable CAD and verifiable agents for the M64 cylinder head

The recommended priority is a local chain that keeps the reference geometry, proposes limited parametric operations and checks every result with the CAD kernel. The publications available up to **September 12, 2026** justify a targeted trial of assisted reconstruction; they do not demonstrate the automatic reconstruction of a four-valve M64 cylinder head, nor its durability at the announced 700 hp target. The power convention and the thermomechanical loads remain separate inputs.

## Usable results

**CAD-Recode** turns a point cloud into a CadQuery program, with a 1.5-billion-parameter Qwen2 decoder. The model learns from one million synthetic programs, mainly based on sketches and extrusions. The authors publish inference code, weights and data; their table reaches a mean IoU of 92.0 % on DeepCAD and 87.8 % on Fusion360 with their synthetic training. This result concerns the similarity of benchmark volumes, not machining errors in millimeters. Its value for the M64 is proposing an editable history for a sub-geometry that is already documented.[^1]

**cadrille** extends this approach to points, images and text with Qwen2-VL-2B and reinforcement learning. Its table 9 announces 2.0 seconds for points or images on an H100, batch size one; this time is neither a measurement on a Mac nor an estimate for the cylinder head. The SFT/RL weights, inference and evaluation are available, but the repository consulted states that the RL training code is absent. The authors acknowledge the loss of detail on complex surfaces. It is the first candidate to compare locally on a few known zones, subject to the licenses of the weights and data.[^2]

**Point2CAD** provides an alternative for fitting analytic or freeform surfaces and then reconstructing their intersections. Its implementation expects points already associated with a surface identifier: segmentation therefore remains a prior task. A reconstructed B-Rep does not automatically restore the design history. The approach is relevant for comparing a surface fit with a program proposal; it does not allow inventing invisible internal geometry.[^3]

**BrepGaussian**, published at CVPR 2026, maps multi-view photographs to a B-Rep through Gaussian Splatting, segmentation and geometric fitting. The text studied notably uses planes, cylinders and spheres; its SAM masks are corrected manually on the benchmark, about three minutes per object. The official code is now public, whereas the initial arXiv abstract only promised its release. For the M64, the value is the secondary use of photographs and visible contours; thin fins, hidden surfaces and complex passages exceed the demonstration presented.[^4]

## Drawings and technical drafting

**Drawing-Recode**, a July 2026 preprint, separates annotation recognition from geometry and then links them explicitly. Its rate of invalid models drops to 0.97 % on its own protocol. The "scanned" drawing tests use synthetic degradations of the drawings, not a metrological validation campaign on old industrial drawings. The transferable recommendation is to keep, for each dimension, the recognized text, its view, its attachments and its status; a number read correctly but associated with the wrong bore is still an error.[^5]

**Ortho2CAD** shows why the article version matters. The v2 of August 11, 2026 adds four sets of 100 trials and manually dimensioned drawings. Its RL model produces 100 % valid code, but the IoU falls from 0.5601 on Fusion360 to 0.2997 on the manually dimensioned drawings. A GPT-5.5 loop reaches 0.8165 and 0.7495 respectively in this protocol. These results therefore do not demonstrate a general superiority of small local models. Rather, they justify trying them on a narrow domain, then reserving expensive calls for verifiable failures. The authors also report errors in the intersection computation used for the IoU.[^6]

The **CAD-Coder of Guan et al.**, published at NeurIPS 2025, combines CadQuery generation with format/geometry rewards. It must not be confused with the visual CAD-Coder of Doris et al., used as another baseline by Ortho2CAD. Guan's ablation shows that a reward based solely on the Chamfer distance destabilizes training. For the project, the lesson is to use several explicit checks rather than a single visual or volumetric score.[^7]

## Agents, constraints and mathematics

**Embodied CAD** separates LLM planning, deterministic parameter solving and FreeCAD execution. This architecture fits an agent that chooses "fit a surface" or "check an interface", while coordinates and Booleans are computed by the tools. But the 100 % execution in the main table concerns the best deterministic workflows per family; it is not an autonomous success rate on arbitrary industrial requests. The text notably excludes tolerance stack-ups and manufacturing simulation.[^8]

**AADvark** illustrates the value of solver error messages and stable identifiers in renders. Its scissors demonstration nonetheless takes 20 iterations, 4.14 hours, 468 LLM calls and 18.2 million input tokens, according to the authors. The primitives and joints remain limited to rectangular prisms and pivots. Adopting the checkers and the intermediate representation is relevant; taking over this loop as the main workflow would be poorly aligned with the goal of frugality.[^9]

**AlphaGeometry2**, published in JMLR, demonstrates an effective combination of neural proposals and symbolic deduction on olympiad plane-geometry problems. The public repository contains the DDAR symbolic engine and examples, not the full neural system. This proof of principle solves neither Navier–Stokes, nor heat transfer, nor the fatigue of a cylinder head. The useful analogy is limited: let the LLM propose, then have a tool suited to the requested property accept or reject.[^10]

## Recommended program for the project

The following steps are an engineering recommendation, not experimental results already obtained.

1. **Freeze the known references and interfaces.** Keep the master files, units, reference frames and provenance. Distinguish the surfaces actually observed from the unknown regions. No generative infill becomes a measurement. The exterior stays unchanged as long as no documented benefit motivates a modification.
2. **Compare a local reconstruction.** Choose, within the existing data, a small zone whose geometry is known. Compare the deterministic fit, cadrille and possibly CAD-Recode, without retraining any model. Produce code, B-Rep/STEP and fit residuals; reject new details that have no source.
3. **Limit the action language.** Use allowed operations and named parameters in build123d/OCP: import, select by stable reference, fit, measure, intersect, export. Keep the parametric source and the STEP; the CadQuery programs from the papers require adaptation, they do not automatically become build123d programs.
4. **Use PicoGK in its proper role.** Its voxelized distance fields are useful for volumetric operations and implicit geometry; the chosen resolution can lose detail. Keep the reference B-Rep for the interfaces, then compare any voxelized representation. A mesh export is not a parametric CAD history.[^11]
5. **Have the relevant property checked.** Check B-Rep validity, connectivity, volumes, surface deviations, local sections and preservation of interfaces. `BRepCheck_Analyzer` checks geometric/topological validity according to its own checks; it does not check assembly, manufacturability or physics.[^12] For equations, use explicit units, symbolic/numerical computations and conservation balances; CFD/thermal criteria belong to the solver and its validation.
6. **Bound the LLM calls.** Prepare views and metrics locally; transmit only the useful zone and error. Cache the references and impose a limited number of corrections. Measure time, calls, tokens and rejection rate before generalizing. No massive training, GPU rental or new measurement campaign is needed to decide on this first trial.

## Sources and reading level

"Sections" means that the indicated passages of the full text were consulted, without claiming an exhaustive reading. "Abstract" forbids attributing to the paper methodological details that were not read. The repositories were inspected as documentary sources; their execution was not validated here. The figures from the articles are results declared by their authors.

| Ref. | Date, status and identifier | Access actually used | Code and documentary limit |
|---|---|---|---|
| 1. CAD-Recode | 2024-12-18; ICCV 2025; arXiv:2412.14042 | Abstract, author page, benchmark table, repository | [filaPro/cad-recode](https://github.com/filaPro/cad-recode); inference and weights; CC-BY-NC 4.0 license for the repository |
| 2. cadrille | 2025-05-28; v3 2026-02-17; arXiv:2505.22914 | Architecture, results, limitations, inference-time sections; repository | [col14m/cadrille](https://github.com/col14m/cadrille), Apache-2.0 code; RL training absent according to the README. ICLR 2026 entry indexed, final publication status not confirmed on OpenReview |
| 3. Point2CAD | 2023-12-07; CVPR, June 2024; arXiv:2312.04962 | arXiv/CVF abstracts and implementation documentation | [prs-eth/point2cad](https://github.com/prs-eth/point2cad); contradiction between a CC-BY-NC README and an Apache-2.0 LICENSE file, to be resolved before reuse |
| 4. BrepGaussian | 2026-02-24; CVPR, June 2026; arXiv:2602.21105 | Fitting, protocol and results sections; CVF proceedings; repository | [yjx2851/BrepGaussian](https://github.com/yjx2851/BrepGaussian); reconstruction code visible; component licenses not audited |
| 5. Drawing-Recode | 2026-07-30; preprint; arXiv:2607.27558 | Annotation sections, tables 1–4, scan-simulating noise | Official repository not identified in the text or in targeted searches |
| 6. Ortho2CAD | 2026-07-09; v2 2026-08-11; preprint; arXiv:2607.08891 | v1 then v2, protocol, tables, limitations; repository | [AdityaJoglekar/Ortho2CAD](https://github.com/AdityaJoglekar/Ortho2CAD); projection generator, training/evaluation visible; weights and license not established |
| 7. CAD-Coder — Guan | 2025-05-26; NeurIPS 2025; DOI:10.52202/085713-1999 | Proceedings abstract, reward and training-cost sections/appendices | [gudo7208/CAD-Coder](https://github.com/gudo7208/CAD-Coder); inference, weights and data; Apache-2.0 announced |
| 8. Embodied CAD | 2026-06-30; preprint; arXiv:2606.31252 | Sections 4–7, tables and limitations | Official repository not identified; proxy comparisons explicitly limited by the authors |
| 9. AADvark | 2026-04-16; arXiv:2604.15184; demonstration manuscript | Sections 3–5, costs, limitations | FreeCAD/OndselSolver modifications described; full reproducibility not established; manuscript DOI replaced by a placeholder |
| 10. AlphaGeometry2 | 2025-02-05; JMLR 26(241), October 2025; arXiv:2502.03544 | JMLR abstract, PDF metadata, engine README | [google-deepmind/alphageometry2](https://github.com/google-deepmind/alphageometry2); DDAR released, full system not provided |

[^1]: Rukhovich, D. et al. [CAD-Recode: Reverse Engineering CAD Code from Point Clouds](https://arxiv.org/abs/2412.14042), 2024/2025; [authors' results](https://cad-recode.github.io/).
[^2]: Kolodiazhnyi, M. et al. [cadrille: Multimodal CAD Reconstruction with Reinforcement Learning](https://arxiv.org/html/2505.22914v3), February 17, 2026, appendices A–C; [indexed ICLR entry](https://iclr.cc/virtual/2026/poster/10006759). The final [OpenReview](https://openreview.net/forum?id=w2tnhhMbXv) decision was not accessible; do not treat an old program entry as a verified final publication.
[^3]: Liu, Y., Obukhov, A., Wegner, J. D. and Schindler, K. [Point2CAD: Reverse Engineering CAD Models from 3D Point Clouds](https://openaccess.thecvf.com/content/CVPR2024/html/Liu_Point2CAD_Reverse_Engineering_CAD_Models_from_3D_Point_Clouds_CVPR_2024_paper.html), CVPR 2024, pp. 3763–3772.
[^4]: Yu, J. et al. [BrepGaussian: CAD reconstruction from Multi-View Images with Gaussian Splatting](https://openaccess.thecvf.com/content/CVPR2026/html/Yu_BrepGaussian_CAD_reconstruction_from_Multi-View_Images_with_Gaussian_Splatting_CVPR_2026_paper.html), CVPR 2026, pp. 26104–26113; [text studied](https://arxiv.org/html/2602.21105v1), sections 3.4 and 4.
[^5]: Kim, M., Kim, Y. and Kim, H. [Drawing-Recode: Annotation Grounding for Parametric CAD Code Generation from Raster 2D CAD Drawings](https://arxiv.org/html/2607.27558v1), July 30, 2026.
[^6]: Joglekar, A. et al. [Ortho2CAD: 3D CAD generation from orthographic drawings using vision language models](https://arxiv.org/html/2607.08891v2), August 11, 2026, sections 3.4–5.
[^7]: Guan, Y. et al. [CAD-Coder: Text-to-CAD Generation with Chain-of-Thought and Geometric Reward](https://proceedings.neurips.cc/paper_files/paper/2025/hash/564a224e88f2490f3c1deaae877d37e3-Abstract-Conference.html), NeurIPS 2025; [appendix B](https://arxiv.org/html/2505.19713v3).
[^8]: Liu, F., Zhou, H., Hao, F. and Yang, L. [Embodied CAD: Solver-Grounded LLM Agents for Parametric B-Rep Assembly Modeling](https://arxiv.org/html/2606.31252v1), June 30, 2026.
[^9]: Adler, M., Russo, M. and Cafarella, M. [Agent-Aided Design for Dynamic CAD Models](https://arxiv.org/html/2604.15184v1), April 16, 2026, sections 4–5.
[^10]: Chervonyi, Y. et al. [Gold-medalist Performance in Solving Olympiad Geometry with AlphaGeometry2](https://www.jmlr.org/beta/papers/v26/25-1654.html), JMLR 26(241), 2025, pp. 1–39.
[^11]: LEAP 71. [First steps in PicoGK](https://picogk.org/coding-for-engineers/8-first-steps-in-picogk.html) and [implicit geometry](https://picogk.org/coding-for-engineers/19-computational-geometry-part7.html), official documentation consulted on September 12, 2026.
[^12]: Open CASCADE. [BRepCheck_Analyzer Class Reference](https://occt3d.com/dev/doc/refman/html/class_b_rep_check___analyzer.html), official documentation consulted on September 12, 2026.
