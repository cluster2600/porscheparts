export const meta = {
  name: 'k16-rod-improvement-plan',
  description: 'Analyse the K16 compressor/turbine wheels and the Ti rod designs, then prepare a verified work plan to make them measurably better',
  phases: [
    { title: 'Understand', detail: 'readers over dossiers, sources, toolchain and rules; web sweep for OEM data and open methods' },
    { title: 'Design', detail: 'three planners per part with different lenses, then a judge merges' },
    { title: 'Verify', detail: 'every plan claim attacked from three lenses' },
    { title: 'Synthesize', detail: 'completeness critic, then the programme document' },
  ],
}

const PARTS = [
  { id: '993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001', short: 'K16 compressor wheel, Al2139 F1',
    files: 'docs/993/993_K16_COMPRESSOR_WHEEL_AL2139_F1.md, parts/993-eng-k16-compressor-wheel-al2139-f1-0001/source/compressor_wheel_f1.py, parts/993-eng-k16-compressor-wheel-al2139-f1-0001/evidence/engineering-screen.json, parts/993-eng-k16-compressor-wheel-al2139-f1-0001/evidence/lpbf-f0/993-eng-k16-compressor-wheel-al2139-f1-0001-lpbf-geometry-report.json, catalog/parts/993-eng-k16-compressor-wheel-al2139-f1-0001.json, plus its F0 predecessor docs/993/993_K16_COMPRESSOR_WHEEL_ALSI10MG_F0.md, parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/source/compressor_wheel.py, parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/evidence/engineering-screen.json',
    lenses: [
      ['aero-performance', 'Real 3D blade aerodynamics: how to replace the flat radial plates with a designed impeller (meanline sizing, blade angles, splitter, backsweep, shroud contour), and how to prove it on a compressor map with CFD against the OEM K16 operating points.'],
      ['structural-integrity', 'Centrifugal + thermal 3D FEA, HCF, modal/Campbell, burst and overspeed margins for an LPBF Al2139 wheel; what allowables exist and what a screen may honestly claim.'],
      ['provenance-and-baseline', 'Define "better" and "lighter" measurably against the OEM wheel: which OEM numbers exist in published sources, how to reconstruct the OEM envelope from them without a physical part, what gates move the record off concept.'],
    ] },
  { id: '993-ENG-K16-TURBINE-WHEEL-IN718-F0-0001', short: 'K16 turbine wheel, IN718 F0',
    files: 'docs/993/993_K16_TURBINE_WHEEL_IN718_F0.md, parts/993-eng-k16-turbine-wheel-in718-f0-0001/source/turbine_wheel.py, parts/993-eng-k16-turbine-wheel-in718-f0-0001/evidence/engineering-screen.json, parts/993-eng-k16-turbine-wheel-in718-f0-0001/evidence/lpbf-f0/993-eng-k16-turbine-wheel-in718-f0-0001-lpbf-geometry-report.json, catalog/parts/993-eng-k16-turbine-wheel-in718-f0-0001.json',
    lenses: [
      ['aero-performance', 'Real radial-inflow turbine blading (meanline, blade angles, exducer), hot-gas CFD/CHT against the K16 turbine side, and what a turbine map would need.'],
      ['structural-integrity', 'The F0 fails its own blade-root (1.233) and thermal (0.566) screens: how to fix the design (root fillets, blade thickness, hub) and prove it with centrifugal + thermal FEA, creep/HCF at temperature, burst margin, for LPBF IN718.'],
      ['provenance-and-baseline', 'Define "better" against the OEM/Kinugawa turbine wheel with published numbers only; reconstruct the OEM envelope; gates off concept.'],
    ] },
  { id: '993-ENG-CONNECTING-ROD-TI64-F0-0001', short: 'Connecting rod, Ti-6Al-4V F0',
    files: 'docs/993/993_CONNECTING_ROD_TI64_F0.md, parts/993-eng-connecting-rod-ti64-f0-0001/source/connecting_rod.py, parts/993-eng-connecting-rod-ti64-f0-0001/evidence/engineering-screen.json, catalog/parts/993-eng-connecting-rod-ti64-f0-0001.json, catalog/sources/src-tzr-pauter-993-connecting-rod-dimensions.json, catalog/sources/src-cecchel-2022-additive-ti-connecting-rod-fatigue.json, catalog/sources/src-porschefanatics-993-titanium-connecting-rods.json',
    lenses: [
      ['lightweighting-and-stiffness', 'Topology/shape optimisation of the rod under the real load cycle (gas force, inertia, buckling), single-body redesign so the LPBF screen stops failing closed, mass target vs the 535 g steel rod and the −33 % titanium offer.'],
      ['fatigue-and-manufacturing', 'LPBF Ti-6Al-4V fatigue route: HIP, machining of bores and bolt faces, surface finish, notch factors, the Cecchel 2022 findings, what allowables exist, what proof is possible in software only.'],
      ['provenance-and-baseline', 'Define "better" against the steel rod and commercial Ti rods with published numbers only (masses, dimensions, load data from the M64 engine), gates off concept.'],
    ] },
]

const RULES = `Hard rules for every proposal (from the repository, not negotiable):
- No step may require buying, borrowing or physically measuring a part; the project works from published sources, licensed scans and its own records (a licensed scan MAY be listed as an optional unlock, never as a prerequisite for the software work).
- Sources are reference-only: numbers may be cited with their source id; no third-party geometry, photo or map image is copied into the repository. Sites closed to robots are not queried (decision 0003).
- SAFETY.md: a screening or simulation never authorises manufacturing; both wheels and the rod stay prohibited_pending_engineering; a plan may move a record from concept only through the ladder in docs/QUALITY_GATES.md.
- Heavy compute runs in the repository's containers, memory-capped, one job at a time (WSL host has 15 GB RAM, 16 CPUs; a GPU is only available via paid Vast.ai runs).
- Evidence files (evidence/**) are pinned by SHA-256 and never edited; new evidence is added in new dated folders.
- Docs are in English; diagrams in Mermaid; every number in a doc carries its origin (source id, script, or "hypothesis").`

const FACTS = { type: 'object', properties: {
  summary: { type: 'string' },
  facts: { type: 'array', items: { type: 'object', properties: {
    fact: { type: 'string' }, where: { type: 'string' },
    kind: { type: 'string', enum: ['sourced_number', 'hypothesis', 'method', 'result', 'gap', 'constraint', 'capability', 'planned_step'] } },
    required: ['fact', 'where', 'kind'] } },
  gaps: { type: 'array', items: { type: 'string' } },
}, required: ['summary', 'facts', 'gaps'] }

const SOURCES = { type: 'object', properties: {
  summary: { type: 'string' },
  sources: { type: 'array', items: { type: 'object', properties: {
    title: { type: 'string' }, url: { type: 'string' }, what_it_provides: { type: 'string' },
    numbers: { type: 'array', items: { type: 'string' } },
    access: { type: 'string', enum: ['open', 'reference_only', 'paywalled', 'robots_closed', 'unknown'] },
    already_in_catalog: { type: 'boolean' } },
    required: ['title', 'url', 'what_it_provides', 'numbers', 'access', 'already_in_catalog'] } },
  not_found: { type: 'array', items: { type: 'string' } },
}, required: ['summary', 'sources', 'not_found'] }

const STEP = { type: 'object', properties: {
  id: { type: 'string' }, title: { type: 'string' }, goal: { type: 'string' },
  inputs: { type: 'array', items: { type: 'string' } },
  tools: { type: 'array', items: { type: 'string' } },
  outputs: { type: 'array', items: { type: 'string' } },
  gate: { type: 'string' },
  depends_on: { type: 'array', items: { type: 'string' } },
  can_run_now: { type: 'boolean' },
  blocked_by: { type: 'string' },
  effort: { type: 'string' },
  claims: { type: 'array', items: { type: 'string' } } },
  required: ['id', 'title', 'goal', 'inputs', 'tools', 'outputs', 'gate', 'depends_on', 'can_run_now', 'blocked_by', 'effort', 'claims'] }

const PLAN = { type: 'object', properties: {
  part_id: { type: 'string' }, lens: { type: 'string' },
  what_better_means: { type: 'string' },
  diagnosis: { type: 'string' },
  steps: { type: 'array', items: STEP },
  needs_from_owner: { type: 'array', items: { type: 'string' } },
  risks: { type: 'array', items: { type: 'string' } },
}, required: ['part_id', 'lens', 'what_better_means', 'diagnosis', 'steps', 'needs_from_owner', 'risks'] }

const JUDGED = { type: 'object', properties: {
  scores: { type: 'array', items: { type: 'object', properties: {
    lens: { type: 'string' }, score: { type: 'number' }, strengths: { type: 'string' }, weaknesses: { type: 'string' } },
    required: ['lens', 'score', 'strengths', 'weaknesses'] } },
  merged: PLAN,
  rationale: { type: 'string' },
}, required: ['scores', 'merged', 'rationale'] }

const VERDICT = { type: 'object', properties: {
  refuted: { type: 'boolean' },
  confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
  reason: { type: 'string' },
  correction: { type: 'string' },
}, required: ['refuted', 'confidence', 'reason', 'correction'] }

const CRITIC = { type: 'object', properties: {
  missing: { type: 'array', items: { type: 'object', properties: {
    item: { type: 'string' }, why_it_matters: { type: 'string' }, part_ids: { type: 'array', items: { type: 'string' } } },
    required: ['item', 'why_it_matters', 'part_ids'] } },
  contradictions: { type: 'array', items: { type: 'string' } },
  first_week: { type: 'array', items: { type: 'string' } },
}, required: ['missing', 'contradictions', 'first_week'] }

const DOC = { type: 'object', properties: {
  path: { type: 'string' }, summary: { type: 'string' },
  open_questions_for_owner: { type: 'array', items: { type: 'string' } },
  mermaid_blocks: { type: 'number' },
}, required: ['path', 'summary', 'open_questions_for_owner', 'mermaid_blocks'] }

// ---------------------------------------------------------------- Understand
phase('Understand')
log('Reading the three designs, the source records, the toolchain and the rules; sweeping the web for OEM data and open methods')

const readerPrompt = (p) => `Repository /home/maxime/3dprinting993. Read, fully, these files about ${p.short} (${p.id}): ${p.files}.
Extract, as facts with a file:line or source-id "where": every sourced number and its source id; every hypothesis (dimension or load the project invented); each screening method (the equations, what they compute, at what temperature, with which material values and from which data sheet); every result and verdict (pass/fail ratios); what the geometry actually is (describe the blade or strut shapes concretely: e.g. flat radial plates vs curved blades, counts, thicknesses, hub/backplate, split bodies); what the LPBF print screen did and found; the dossier's own stated next steps; and every reason the design cannot today be called "better", "lighter" or "more performant" than the OEM part. List gaps: which numbers about the OEM part are absent (mass, blade geometry, map, speed, loads).`

const understanding = await parallel([
  ...PARTS.map(p => () => agent(readerPrompt(p), { label: `read:${p.short}`, phase: 'Understand', schema: FACTS, effort: 'high' })),
  () => agent(`Repository /home/maxime/3dprinting993. Read every catalogue source record relevant to the K16 turbocharger and the 993 connecting rod: run \`ls catalog/sources | grep -iE "k16|turbo|borgwarner|pauter|tzr|rod|kinugawa|turbomaster|invasion|cargraphic|elferwelt|fvd-993-k16|matchbot|turbomap|cecchel|rennlist-993-k16|christophorus-993|design911-993-k16"\` and read each JSON. Also read catalog/reference/993-declared-part-data.json (turbo entries), catalog/specifications/porschefanatics-993-technical-data.json and porschefanatics-993-torques.json (engine data: bore, stroke, compression, redline, boost, power), simulation/993-turbo-dyno/dyno-reference.json and derived-dyno-curves.json, simulation/993-turbo-variants/variants.json, simulation/993-k16-cold-side-baseline/parameters.json and README.md.
For each source: what data it holds (dimensions, inducer/exducer, trim, blade counts, maps, masses, speeds, part numbers, materials, boost/power), its access/licence field, its confidence level, and whether the data is already used by a part record. State plainly which OEM numbers exist and which do not (wheel masses, blade geometry, maps, max speed).`, { label: 'read:sources', phase: 'Understand', schema: FACTS, effort: 'high' }),
  () => agent(`Repository /home/maxime/3dprinting993. Establish what analysis capability the repository REALLY has for turbomachinery and rotating/loaded parts. Inspect containers/*.Dockerfile and containers/README.md for what each image installs (OpenFOAM: version and which solvers/utilities, MRF/SRF support, snappyHexMesh/cfMesh; CalculiX ccx/cgx versions; gmsh; build123d/OCP/cadquery; cantera; PhysicsNeMo; pyvista/trimesh). Confirm with quick checks only: \`docker run --rm --memory=1g 3dprinting993-cadsim:dev sh -c 'which ccx cgx gmsh simpleFoam rhoSimpleFoam rhoPimpleFoam MRFSimpleFoam SRFSimpleFoam snappyHexMesh cfMesh cartesianMesh; ccx -v; python3 -c "import build123d, cantera" '\` and the same on 3dprinting993-mesh-cfd (\`docker images\` lists the local tags; ghcr.io/cluster2600/3dprinting993-mesh-cfd:latest exists locally). Never launch a solver.
Then read the reusable pipelines: twins/reference-917-engine/source/build_cfd_cases_f49.py, build_cfd_cases_f50_steady.py, build_cfd_domains_f48.py, build_cae_load_transfer_f47.py, the F46 cantera cycle and F50 thermomechanical scripts (find them with ls), twins/993-m64-60-piston-gallery-f0/ (CalculiX thermomechanical), twins/engine-simulation-contracts/README.md, simulation/993-k16-cold-side-baseline/ (OpenFOAM case: which solver, BCs, what it modelled), Makefile targets touching CFD/FEA (grep -n "openfoam\\|calculix\\|ccx\\|cfd" Makefile). Report capabilities as facts: available? in which image? proven by which prior run (evidence folder)? limits (steady only, incompressible only, no rotating frame, no contact, etc.).`, { label: 'read:toolchain', phase: 'Understand', schema: FACTS, effort: 'high' }),
  () => agent(`Repository /home/maxime/3dprinting993. Read SAFETY.md, docs/QUALITY_GATES.md, docs/AM_VALIDATION_PIPELINE.md, docs/TITANIUM.md, docs/TURBO_DIGITAL_TWIN_PLAN.md, docs/TURBO_AIRFLOW_SIMULATION_DATA.md, docs/DIGITAL_TWIN.md, docs/decisions/0003-no-vendor-harvesting.md, docs/decisions/0011-printable-display-mockups-of-prohibited-parts.md, docs/research/M64_CFD_TWINS_REVIEW_20260912.md, docs/research/M64_MATERIAL_REVIEW_20260912.md, docs/research/M64_LPBF_OIL_REVIEW_20260912.md, catalog/sources/src-turbomap-compressor-map-methodology.json, catalog/sources/src-cecchel-2022-additive-ti-connecting-rod-fatigue.json, catalog/schemas/part.schema.json (validation.status enum and what each level means per QUALITY_GATES).
Extract as facts: every rule that constrains improvement work on prohibited engine parts (what a screen may claim; what evidence moves a record concept -> dimensionally_reviewed -> engineering_reviewed; the AM pipeline's mandatory stages; titanium/superalloy documentation requirements; evidence pinning; no vendor harvesting); every step the turbo twin plan or airflow data doc ALREADY schedules for the K16 (stages, data needed, cases planned) so a new plan extends rather than contradicts them; and material-data facts already reviewed (Al2139, IN718, Ti-6Al-4V allowables, temperature limits, fatigue knockdowns for LPBF).`, { label: 'read:rules', phase: 'Understand', schema: FACTS, effort: 'high' }),
  () => agent(`Web research (use WebSearch/WebFetch; load them with ToolSearch if needed). Goal: openly published data on the BorgWarner K16 turbochargers of the Porsche 993 Turbo (part numbers 5316-988-6735, 5316-970-6735, K16 8055011W; turbine wheel/shaft 5316-120-5000; compressor wheel part numbers) usable as a baseline to judge a redesigned wheel: compressor wheel inducer and exducer diameters, trim, main/splitter blade counts, blade height, backsweep; turbine wheel inducer/exducer, blade count, material; published compressor or turbine maps (BorgWarner MatchBot, BorgWarner performance catalogue, dyno-derived maps), rated and max speed, CHRA or wheel masses; aftermarket replacement wheels (Kinugawa, Turbomaster, Melett, others) that publish dimensions or masses; any CT-scan or CAD dataset of a K16 published openly.
Rules: report only what a page actually states, with the URL; classify access (open / reference_only / paywalled / robots_closed / unknown); do NOT fetch pages that return 403 or forbid robots (e.g. rennlist.com) — record them as robots_closed with what the search snippet said; never propose buying or measuring a part. First read /home/maxime/3dprinting993/catalog/sources (ls | grep -i "k16\\|borgwarner\\|turbo\\|kinugawa\\|turbomaster\\|invasion") so you can mark which sources are already recorded. Finish with a not_found list of the numbers you looked for and could not find published.`, { label: 'web:K16 OEM data', phase: 'Understand', schema: SOURCES, effort: 'high' }),
  () => agent(`Web research (use WebSearch/WebFetch; load them with ToolSearch if needed). Goal: openly published baseline data for the Porsche 993 / M64 connecting rod and for LPBF titanium rods: OEM steel rod mass and dimensions (center distance 127 mm, pin 23 mm, big end 58 mm are known); commercial rods for 993/964 (PAUTER via TZR, Carrillo, Pankl, Arrow, others) that publish mass, material, dimensions; the M64/60 Turbo engine data needed for rod loads (bore, stroke, rod length, peak cylinder pressure if any published, redline, piston mass if any); peer-reviewed or open-access papers on additively manufactured Ti-6Al-4V connecting rods (Cecchel et al. 2022 and others: fatigue results, HIP, surface treatment, knockdown factors), and open fatigue allowable datasets for LPBF Ti-6Al-4V.
Rules: report only what a page states, with URL and access class; do not fetch robots-closed sites (rennlist etc.); never propose buying or measuring a part. First read /home/maxime/3dprinting993/catalog/sources (ls | grep -i "rod\\|pauter\\|tzr\\|cecchel\\|porschefanatics-993-titanium") to mark what is already recorded. Finish with a not_found list.`, { label: 'web:rod baseline', phase: 'Understand', schema: SOURCES, effort: 'high' }),
  () => agent(`Web research (use WebSearch/WebFetch; load them with ToolSearch if needed). Goal: real, installable, open-source tools and validated open methods the project could use to design and prove turbo wheels and a connecting rod in software: (a) radial compressor / radial-inflow turbine design tools — meanline sizing and 3D blade generation (e.g. open GitHub projects; check each exists, its licence, language, last activity); (b) OpenFOAM rotating machinery: MRF/SRF, rhoSimpleFoam/rhoPimpleFoam for compressible impellers, cyclic/periodic single-passage setups, official tutorial names, the OpenFOAM version they need; (c) CalculiX for rotors: centrifugal loading (*DLOAD with CENTRIF), thermal loading, modal analysis with prestress, cyclic symmetry; (d) fatigue and burst screening methods for AM Al2139 / IN718 / Ti-6Al-4V rotors and rods (open allowables sources such as NASA, MMPDS availability, EOS data sheets, published knockdown factors); (e) topology optimisation tools usable with CalculiX or Python (e.g. open TO codes) for a connecting rod.
For each: URL, licence, what it does, evidence it works (paper, tutorial, users), and whether it is already present in the repository's container images (grep /home/maxime/3dprinting993/containers/*.Dockerfile). Report only what pages state; classify access; do not fetch robots-closed sites.`, { label: 'web:open tools', phase: 'Understand', schema: SOURCES, effort: 'high' }),
])
const [uComp, uTurb, uRod, uSources, uTools, uRules, wK16, wRod, wTools] = understanding
const partU = { [PARTS[0].id]: uComp, [PARTS[1].id]: uTurb, [PARTS[2].id]: uRod }
const shared = JSON.stringify({ catalog_sources: uSources, toolchain: uTools, rules: uRules, web_k16: wK16, web_rod: wRod, web_tools: wTools })
log(`Understanding done: ${understanding.filter(Boolean).length}/9 readers returned`)

// ---------------------------------------------------------------- Design + Verify, pipelined per part
const plannerPrompt = (p, lens, brief) => `You are planning how to make ${p.short} (${p.id}) of repository /home/maxime/3dprinting993 measurably BETTER than it is today, through the lens "${lens}": ${brief}
${RULES}

What the readers found about this part (facts with locations):
${JSON.stringify(partU[p.id])}

Shared context — catalogue sources, toolchain capabilities, repository rules, and web research on OEM data and open tools:
${shared}

Produce a concrete work plan: 5–10 steps, each with inputs (file paths / source ids / numbers), tools (name the image and program), outputs (files the step will create, under a new dated evidence folder or a new twin folder), a gate (the measurable pass/fail criterion), dependencies, whether it can run now on the WSL host or the containers, what blocks it otherwise, an effort estimate, and the CLAIMS it relies on (e.g. "CalculiX in cadsim supports *DLOAD CENTRIF", "BorgWarner MatchBot publishes the K16 compressor map", "the OEM wheel mass is published") — list every factual claim so it can be checked. Define what "better" means for this part in numbers (mass, stress ratio, efficiency, pressure ratio, fatigue margin) and against which baseline. Do not invent OEM numbers: if a baseline number does not exist, the plan must say how it will be bounded or reconstructed from published data. Read any repository file you need to be precise.`

const judgePrompt = (p, plans) => `Three independent plans propose how to make ${p.short} (${p.id}) measurably better. Judge them and merge the best into ONE plan.
${RULES}
Plans:
${JSON.stringify(plans)}
Score each plan 0–10 on: measurability of "better", honesty about what is unknown, use of the repository's real toolchain, respect of the rules, feasibility on the WSL host/containers, and value per effort. Then produce the merged plan: ordered steps (keep the ids traceable, e.g. C1..Cn / T1..Tn / R1..Rn), dependencies, gates, and for every step the factual claims it relies on. Merge duplicates; drop steps that break a rule; keep an explicit "cannot be done in software" list in needs_from_owner or risks. Prefer steps that produce a number comparable to a published baseline.`

const verifyPrompt = (p, claim, lens) => {
  const lensText = {
    tooling: 'TOOLING lens. Check the claim against the actual repository and containers at /home/maxime/3dprinting993: read Dockerfiles, scripts, Makefile, evidence folders; you may run quick checks (`docker run --rm --memory=1g <image> sh -c "which X; X --version"` or a python import) — never a solver or mesher run, never anything heavier than a version check. If the tool, solver, keyword or script does not exist where the claim says, refute.',
    sources: 'SOURCES-AND-LICENCE lens. Check whether the data or document the claim relies on really exists and is usable: read catalog/sources/*.json, LICENSES.md, docs/decisions/0003-no-vendor-harvesting.md; fetch the URL with WebFetch only if it is not robots-closed (never rennlist). If the number is not actually published, is behind a paywall, would require copying third-party geometry/maps into the repo, or requires a physical part, refute or correct.',
    physics: 'PHYSICS-AND-METHOD lens. Is the method sound for this part and correctly scoped? Does the claim overreach (calls a screen a validation, uses room-temperature allowables for a hot part, ignores fatigue/creep/burst, wrong load case, wrong boundary conditions, single-passage assumptions that do not hold)? Would the proposed gate actually demonstrate "better"? Refute if the claim is wrong or misleading as stated; if it is right but incomplete, do not refute — give the correction.',
  }[lens]
  return `Try to REFUTE this claim from a work plan for ${p.short} (${p.id}):
"${claim}"
${lensText}
Default to refuted=true if you cannot confirm it. Give the concrete evidence (file path, command output, URL, equation) in reason, and in correction the wording the plan should use instead (empty if none).`
}

const results = await pipeline(PARTS,
  async (p) => {
    const plans = (await parallel(p.lenses.map(([lens, brief]) => () =>
      agent(plannerPrompt(p, lens, brief), { label: `plan:${p.short}:${lens}`, phase: 'Design', schema: PLAN, effort: 'high' })))).filter(Boolean)
    log(`${p.short}: ${plans.length}/3 plans in, judging`)
    return { p, plans }
  },
  async ({ p, plans }) => {
    const judged = await agent(judgePrompt(p, plans), { label: `judge:${p.short}`, phase: 'Design', schema: JUDGED, effort: 'xhigh' })
    return { p, plans, judged }
  },
  async ({ p, plans, judged }) => {
    if (!judged) return { p, plans, judged: null, verified: [] }
    const seen = new Set()
    const claims = []
    for (const s of judged.merged.steps) for (const c of s.claims) {
      const k = c.trim().toLowerCase()
      if (k && !seen.has(k)) { seen.add(k); claims.push({ step: s.id, claim: c.trim() }) }
    }
    log(`${p.short}: ${claims.length} distinct claims to verify`)
    const verified = await parallel(claims.map(c => () =>
      parallel(['tooling', 'sources', 'physics'].map(lens => () =>
        agent(verifyPrompt(p, c.claim, lens), { label: `verify:${lens}:${c.step}`, phase: 'Verify', schema: VERDICT, effort: 'high' })
          .then(v => v && { lens, ...v })))
        .then(votes => {
          const vs = votes.filter(Boolean)
          const refuted = vs.filter(v => v.refuted).length
          return { ...c, votes: vs, survives: refuted < 2, refuted_votes: refuted, corrections: vs.map(v => v.correction).filter(Boolean) }
        })))
    const dead = verified.filter(v => !v.survives).length
    log(`${p.short}: ${verified.length - dead} claims survive, ${dead} refuted`)
    return { p, plans, judged, verified }
  })

// ---------------------------------------------------------------- Synthesize
phase('Synthesize')
const bundle = results.filter(Boolean).map(r => ({
  part_id: r.p.id, short: r.p.short,
  scores: r.judged && r.judged.scores, merged: r.judged && r.judged.merged, rationale: r.judged && r.judged.rationale,
  claims: r.verified,
}))

const critic = await agent(`You are the completeness critic for a programme to make three prohibited engine part designs measurably better, in software, in repository /home/maxime/3dprinting993.
${RULES}
Merged plans with every claim's adversarial verdicts (survives=false means at least 2 of 3 lenses refuted it; corrections say how to reword):
${JSON.stringify(bundle)}
Shared understanding (sources, toolchain, rules, web research):
${shared}
Ask: what is missing? A baseline never established; a step whose gate cannot actually be measured; a tool assumed but refuted; a dependency between parts (the two wheels share the same shaft, speed and operating point — is there one common "K16 operating point" step?); a rule not respected (physical parts, harvesting, evidence editing, safety class); reuse of the 917 line's pipelines or the M64 twin that the plans ignored; compute that will not fit the WSL host; a refuted claim the plan still depends on. Also list contradictions between the three plans (different operating points, different allowables for the same material, different definitions of "better"). Finally propose the first week of work: the 3–5 steps that can start today, in order, with the files they produce.`,
  { label: 'critic', phase: 'Synthesize', schema: CRITIC, effort: 'xhigh' })

const doc = await agent(`Write the programme document for repository /home/maxime/3dprinting993: docs/993/993_K16_ROD_IMPROVEMENT_PROGRAMME.md — "Making the K16 wheels and the Ti rod measurably better".
Read first: docs/TRANSLATION.md (style, glossary, diagram conventions), docs/993/993_K16_COMPRESSOR_WHEEL_AL2139_F1.md (to match the dossier voice), docs/QUALITY_GATES.md.
${RULES}
Material (use ONLY this; do not invent numbers; every number carries its origin: source id, file path, or "hypothesis"):
- Merged plans per part with adversarial verdicts on every claim (drop or reword any claim with survives=false, using its corrections): ${JSON.stringify(bundle)}
- Completeness critic: ${JSON.stringify(critic)}
- Shared understanding: ${shared}

Structure:
1. Title, one-paragraph answer to the owner's question "are those more performant and lighter, did you do the math?" — honest status today per part (what the repo computed, what it did not, what is unknown about the OEM baseline).
2. "What better means" — a table per part: metric, today's value (with origin), baseline (published value with source id, or "not published — how it will be bounded"), target, how it will be measured.
3. A Mermaid flowchart of the shared K16 operating-point step feeding both wheels, and the rod's load-case step; stop nodes for what stays prohibited.
4. Per part: diagnosis; the ordered work plan as a table (id, step, inputs, tools, outputs, gate, can run now / blocked by, effort); the claims that were refuted and how the plan changed because of them.
5. Reuse: which existing pipelines (917 line F46–F50, M64 twin, simulation/993-*) each step builds on, with paths.
6. First week: the steps that can start today, in order, with the files they will create.
7. What this programme will NOT do: no manufacturing, no physical parts, no map copying; the records stay prohibited_pending_engineering until the QUALITY_GATES ladder says otherwise.
8. Open questions for the owner.
The document must mention the three part ids verbatim (993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001, 993-ENG-K16-TURBINE-WHEEL-IN718-F0-0001, 993-ENG-CONNECTING-ROD-TI64-F0-0001) so the generated part pages link to it. Validate every Mermaid block with /tmp/claude-1000/-home-maxime-3dprinting993/4a4a5bd4-035d-477a-8c16-e9a65add601e/scratchpad/mmdcheck.sh docs/993/993_K16_ROD_IMPROVEMENT_PROGRAMME.md (must print OK per block; fix on FAIL). Do not edit any other file. Return the path, a summary, the open questions and the number of Mermaid blocks.`,
  { label: 'write:programme', phase: 'Synthesize', schema: DOC, effort: 'xhigh' })

return { bundle, critic, doc }