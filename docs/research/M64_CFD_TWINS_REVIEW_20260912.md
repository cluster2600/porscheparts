# CFD, thermal analysis and learned models for the M64 cylinder head

The defensible path is a chain of verified computations, then correlated with
measurements, on which a learned model can speed up the selection of variants.
The ten publications retained between 2023 and September 12, 2026 demonstrate
neither a four-valve 700 hp M64 cylinder head, nor a universal solver combining
combustion, moving valvetrain and air/oil cooling. The published speedups remain
specific to their problems and hardware.

The [local reference](../reports/M64_700CH_ENGINE_RESEARCH.md) keeps **700 PS at
the crankshaft = 514.849 kW**. A sensitivity case at **700 mechanical hp =
521.990 kW** adds 1.387 %. This unit ambiguity does not change the existing
contract. Engine speed, fuel, actual displacement, duration at full load and
dyno conditions remain to be frozen. A target power provides neither cylinder
pressure, nor heat flux, nor boost pressure.

## What transfers from the publications

Pati et al. simulate 33 motored cycles, without combustion, of the Darmstadt
optical engine: 800 rpm, mean intake 0.95 bar, piston wall resolved to 25 µm
and `y+ < 1`. Near-wall velocities are compared with measurements. The absence
of a logarithmic region and the cyclic fluctuations signal the limits of
equilibrium wall laws; these results do not validate a turbocharged combustion
heat flux.[^1]

Caramia et al. show the value of WENO schemes for compressible jets, but their
case is **axisymmetric, non-reacting, hydrogen/air**, with pressure ratios of
8.5–30. Jet width can be overestimated by 30 %. Good shock capture therefore
does not guarantee mixing, still less gasoline combustion in a four-valve
chamber.[^2] Gärtner et al. address another bottleneck: MPI load balancing of
the chemistry cost, with announced speedups of up to 6 for standard chemistry
and 5 for TDAC. This is a parallel CPU result, not evidence of GPU speedup nor
of the correctness of a fuel mechanism.[^3]

For cooling, Lei Jilin et al. combine engine measurements, a 1D model and a
thermal/mechanical computation on an air-cooled aero engine. The joint effect of
fin length and thickness is relevant, but their gains are not factors that
apply to the M64.[^4] Tandis et al. compare CHT couplings on natural-convection
enclosures with properties built to vary the coupling. Their monolithic solver
is numerically interesting; its performance does not prove compatibility with
compressible combustion, oil, or seat/guide contacts.[^5]

CFDverify makes it easier to estimate discretization errors and even reveals
copying/rounding errors in published examples. Its scope is **solution
verification**, without comparison to the physical system. The precision of
exported data must be preserved and the Richardson/GCI assumptions examined;
three arbitrary meshes do not make every extrapolation valid.[^6]

GINO and DoMINO mainly learn aerodynamic CFD results on automotive
families.[^7][^8] Their value is to amortize a repetitive campaign over a known
domain. Convergence of a learned operator with respect to discretization is not
evidence of convergence to the real physics. A model trained on OpenFOAM also
reproduces its biases. It is neither an independent second solver nor an
experimental validation.

## Published metrics: comparisons to keep separate

The rows below concern different tasks; they do not form a cross-cutting
accuracy ranking.

| Publication and case | Metric actually published | Reading limit |
| --- | --- | --- |
| GINO, Ahmed/ShapeNet [7] | Announced speedup of up to 26,000× for drag; Ahmed pressure error 8.31 % in the abstract | Inference after training; neither total acquisition cost nor combustion |
| DoMINO v1, DrivAerML [8], tables 1–2 | Drag `R²` 0.96; surface pressure relative L2 error 15.05 %, area-weighted 11.81 %; volume pressure 21.93 % | Good global ranking compatible with local errors; datasets and metrics differ from GINO |
| CFDLLMBench v1 [9], table 2, Foam-Agent/Sonnet 3.5 | Basic: execution 83.6 %, overall success 33.6 %; Advanced: 62.5 % and 25 % | Field and configuration criteria lower the success rate; no industrial cylinder head |
| Xiao et al. [10], §4.1 | 9/9 near-tutorial cases executed with an adapted prompt; 7/9 with `NMSE < 0.1` | Small sample, single-run protocol; not a general guarantee |

The agent results justify retrieving verified cases, minimal changes and
log-guided repair.[^9][^10] They do not demonstrate that an LLM "understands
physics". The controller must forbid a repair from quietly changing fuel,
boundaries, duration, geometry or acceptance criteria to obtain a zero exit
code.

## Proposed execution plan

1. **Contract and geometry.** Take up the interfaces and the
   [multiphysics checkpoint](../reports/M64_MULTIPHYSICS_EXECUTION.md), then build
   separate gas, solid, air and possibly oil domains. Fix normals, units,
   contacts and exchange surfaces. The documented mesh rejection remains a
   blocker before CFD labeling; research does not lift it.
2. **Quasi-steady intake.** At imposed lifts and defined flow-bench boundaries,
   compare 2V/4V by flow rate, discharge coefficient, total pressure loss and
   swirl/tumble structures. Use compressibility if the pressure/Mach ratios
   require it. Each point represents a flow bench; it does not predict
   transient filling, combustion or power.
3. **Moving cycle before combustion.** First reproduce an
   [ICengines/AATE](https://github.com/OpenFOAM/ICengines) tutorial, with a
   pinned solver/case pair. The commands provided are `./Allmesh` then
   `./Allrun`; add the `checkMesh` check suited to the regions and moving
   positions. Check volumes, valve closure, geometric conservation and transfer
   errors between meshes, then periodicity and multi-cycle statistics. The
   [official method](https://cfd.direct/openfoam/free-software/ic-engines/)
   combines motion, mesh change and non-conformal coupling; it does not
   establish that our full CHT assembly is already available.
4. **Chemistry and loads.** Keep the
   [existing Cantera computation](../reports/M64_700PS_VARIABLE_THERMO_20260908.md) as a
   thermodynamic control with prescribed combustion. Then choose a documented
   surrogate and mechanism for the fuel, test ignition delays and flame speeds,
   then integrate the compatible turbulence/chemistry closure. The
   [Cantera engine example](https://cantera.org/stable/examples/python/reactors/ic_engine.html)
   is illustrative, with gaseous n-dodecane: it is not an M64 model to copy.
   Compare `p(θ)`, heat release, CA10/50/90, work `∮p dV`, pumping, wall flux
   and variability against the available measurements. Knock requires specific
   validation; a mean cycle is not enough.
5. **CHT and mechanics.** Start with fins/shroud under explicitly assumed
   thermal loads, then iterate gas–solid with cycle-averaged loads if the
   separation of time scales is justified. Resolve the transients relevant to
   fatigue separately. Compare air only and air/oil at traceable flow rate,
   temperature, pressure and auxiliary power, including viscosity and contacts.
   Transfer the fields conservatively to
   [CalculiX](https://www.calculix.de/) or
   [Elmer](https://www.nic.funet.fi/pub/sci/physics/elmer/doc/ElmerModelsManual.pdf)
   for expansion, preload and contacts, after checking the required functions.
   No automatic assembly of these codes is demonstrated here.
6. **Reduced model and twin.** Start with a KPI regression, then test
   DoMINO/GINO if the fields and the number of variants justify it. Separate
   training, calibration and test by geometric families and operating regimes.
   Active learning chooses new cases, notably uncertain ones; finalists go back
   through CFD/FEA. A correlated twin requires physical measurements reserved
   for checking, distinct from those used for calibration.

## Shared verification and compute decision

| Level | Criteria to fix before the campaign |
| --- | --- |
| Conservation | Mass and species; gas/solid/air/oil energy; flux continuity at interfaces; FEA force and moment balance |
| Discretization | Three consistent levels in space and time, observed order/error interval if applicable; converged statistics for LES |
| Physical reality | Bench flow rate/pressure, phased cylinder pressure, thermocouples at the bridges/seats and inlets/outlets, oil and air flow rates; sensor uncertainty |
| Learned model | Local and maximum absolute error, weighted L2, KPI error, ranking errors, coverage of calibrated intervals, out-of-domain detection |
| Cost | Measured time and memory, CPU/GPU-hours, data + training + recomputations, tokens and repairs per accepted case |

For conduction alone, also compare against an analytical plate/fin solution or
an FEM computation using the same properties and boundaries. This
cross-computation can detect an implementation error; sharing the same assumed
loads does not validate their reality. No universal 1 % threshold replaces an
uncertainty budget suited to the decision.

The recommended initial path is CPU/MPI for CFD/CHT and GPU for the learned
model once its dataset exists. The
[PhysicsNeMo recipes](https://docs.nvidia.com/physicsnemo/latest/physicsnemo/examples/cfd/external_aerodynamics/domino/README.html)
document the latter path. A GPU CFD backend is retained only after measured
equivalence and gain on the same case, with its full physical model. OpenFOAM
forks are incompatible by default: the cited chemistry library targets
v2212/v2306/v2312, while the ICengines README consulted states OpenFOAM-14.
Bringing them together requires a verified adaptation, not a mere change of
image name.

The LLM is used for preparation, diagnostics and compact reports; deterministic
scripts and physical checks drive the computations. The
[coupon capped at 3,300 K](../reports/M64_QUADRATURE_EXECUTION_20260912.md) is excluded
from training ground truth. No computation, training or resource purchase is
carried out by this review.

## Sources and access level

"Text consulted" means reading the relevant methods/results/limitations
sections, not numerical reproduction. Preprints are identified by version; the
`main`, `master`, `latest` URLs are documentation pointers to be pinned before
use. No result later than September 12, 2026 is used.

[^1]: Andrea Pati, Max Hasenzahl, Suad Jakirlic, Christian Hasse.
    [Large Eddy Simulation of the Piston Boundary Layer Evolution During the Compression Stroke in a Motored Internal Combustion Engine](https://doi.org/10.1007/s10494-025-00649-4).
    *Flow, Turbulence and Combustion* 114, 1269–1295; April 14, 2025.
    Peer-reviewed article, HTML text consulted, §2–4. OpenFOAM 2.4.x + in-house
    TFMotion; data on request, no complete reproduction package identified.

[^2]: Giovanni Caramia, Riccardo Amirante, Pietro De Palma.
    [Unsteady RANS simulations of under-expanded hydrogen jets for internal combustion engines](https://doi.org/10.1016/j.ijhydene.2024.11.242).
    *International Journal of Hydrogen Energy* 96, 849–859; online
    November 28, 2024. Peer-reviewed article, institutional PDF consulted, §2–5;
    OpenFOAM with a WENO extension, exact case repository not identified.

[^3]: Jan Wilhelm Gärtner, Ali Shamooni, Thorsten Zirwes, Andreas Kronenburg.
    [A chemistry load balancing model for OpenFOAM](https://doi.org/10.1016/j.cpc.2024.109322).
    *Computer Physics Communications* 305, 109322; December 2024.
    Peer-reviewed article; publisher abstract and
    [GPL-3.0 code](https://github.com/ITV-Stuttgart/loadBalancedChemistryModel)
    consulted, full text not obtained. Tests on up to 8,000 cores announced;
    public tutorial `counterFlowFlame2D`, not a gasoline engine validation.

[^4]: Lei Jilin et al.
    [Multi-objective optimisation of heat transfer and structural strength of aero-piston air-cooled engine cylinder based on orthogonal test](https://doi.org/10.1016/j.tsep.2024.102500).
    *Thermal Science and Engineering Progress* 50, 102500; May 2024.
    Peer-reviewed article; abstract and publisher presentation consulted only.
    Four parameters at five levels; experimental temperatures/pressures
    announced. No public code identified; detailed results not re-audited.

[^5]: Emad Tandis, Philip Cardiff, Ali Ashrafizadeh.
    [Analysis of Coupling Strategies for Conjugate Heat Transfer Problems](https://doi.org/10.51560/ofj.v5.92).
    *OpenFOAM Journal* 5, 38–58; March 7, 2025.
    Peer-reviewed article, PDF consulted, §2–4 and conclusions.
    [Code and cases](https://github.com/tandise/ConjugateHeatTransfer-OpenFOAM)
    on foam-extend-4.0; reuse license of the repository not established here.
    Enclosure benchmarks, not forced-convection engine fins, nor oil.

[^6]: Justin Weinmeister, Devina P. Sanjaya.
    [An Open-Source Python Package for CFD Solution Verification](https://doi.org/10.1115/VVUQ2025-151463).
    ASME VVUQ conference, April 9–10, 2025; proceedings contribution,
    [full manuscript](https://www.osti.gov/servlets/purl/3002740) consulted,
    §1–6. [CFDverify, MIT](https://github.com/ORNL/cfd-verify).
    Reattachment/velocity example drawn from published data; a verification
    tool, with no certification nor automatic physical validation.

[^7]: Zongyi Li et al.
    [Geometry-Informed Neural Operator for Large-Scale 3D PDEs](https://arxiv.org/abs/2309.00583).
    *NeurIPS 2023*, preprint of September 1, 2023; peer-reviewed conference
    paper, proceedings PDF consulted, §1–4.
    [Maintained implementation](https://github.com/neuraloperator/neuraloperator/blob/main/neuralop/models/gino.py).
    Ahmed/ShapeNet, surface pressure; versions, weights and licenses of each
    dataset to be locked separately before reproduction.

[^8]: Rishikesh Ranade et al.
    [DoMINO: A Decomposable Multi-scale Iterative Neural Operator for Modeling Large Scale Engineering Simulations](https://arxiv.org/html/2501.13350v1).
    arXiv preprint v1, January 23, 2025; text consulted, §2–4.
    [PhysicsNeMo code](https://github.com/NVIDIA/physicsnemo/tree/main/examples/cfd/external_aerodynamics/domino).
    DrivAerML: 500 variants, 10 % held out for test, about 150 million volume
    cells per source case; time-averaged fields, not a moving cycle.

[^9]: Nithin Somasekharan et al.
    [CFDLLMBench: A Benchmark Suite for Evaluating Large Language Models in Computational Fluid Dynamics](https://arxiv.org/html/2509.20374v1).
    arXiv preprint v1, September 19, 2025; text consulted, §3–6,
    tables 1–4. [Code/data](https://github.com/NLR-Theseus/cfdllmbench).
    108 questions, 24 Python problems, 126 OpenFOAM cases; synthetic/tutorial
    benchmarks, with no industrial cylinder head geometry.

[^10]: Ke Xiao et al.
    [A Preliminary Assessment of Coding Agents for CFD Workflows](https://arxiv.org/html/2602.11689v1).
    arXiv preprint v1, February 12, 2026; text consulted, §3–5.
    OpenCode/OpenFOAM, prompt in the appendix; dedicated reproduction repository
    not identified. Near-tutorial cases and 2D planar obstacles; run-to-run
    variation and industrial validation not established.
