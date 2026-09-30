# Documentation index

Every document in `docs/`, grouped by what you are trying to do. Progress of the translation: [TRANSLATION.md](TRANSLATION.md).

```mermaid
flowchart LR
    A["Rules<br/><sub>charter · safety · gates</sub>"] --> B["Sources<br/><sub>policy · inventory · research</sub>"]
    B --> C["Design<br/><sub>993 dossiers · part pages</sub>"]
    C --> D["Digital twin<br/><sub>twin · stack · compute</sub>"]
    D --> E["Analysis<br/><sub>FEA · CFD · AM pipeline</sub>"]
    E --> F["Decisions & reports<br/><sub>ADRs · dated reports</sub>"]
```

## Start here

| document | what it answers |
|---|---|
| [../README.md](../README.md) | what the repository is, and what it has found |
| [PROJECT_CHARTER.md](PROJECT_CHARTER.md) | why the project exists and what it will not do |
| [../SAFETY.md](../SAFETY.md) | what may be built, what may not, and why |
| [QUALITY_GATES.md](QUALITY_GATES.md) | what a part must prove at each level |
| [WORKFLOW.md](WORKFLOW.md) | how a part goes from idea to record |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | how to contribute a part, a source or a fix |
| [TRANSLATION.md](TRANSLATION.md) | the French-to-English translation: scope, glossary, progress |
| [GALLERY.md](GALLERY.md) | every figure, render and print screen on one page |
| [../twins/README.md](../twins/README.md) | the digital twins, zone by zone |

## Sources and measurement

| document | what it answers |
|---|---|
| [SOURCE_POLICY.md](SOURCE_POLICY.md) | which sources are admissible, and how rights are recorded |
| [PHASE1_SOURCE_INVENTORY.md](PHASE1_SOURCE_INVENTORY.md) | the phase 1 source inventory |
| [MEASUREMENT_CAMPAIGN.md](MEASUREMENT_CAMPAIGN.md) | the phase 2 measurement campaign |
| [PORSCHEFANATICS_993_TURBO_AUDIT.md](PORSCHEFANATICS_993_TURBO_AUDIT.md) | local audit of a 993 Turbo source |
| [research/](research/) | source research by topic (German-language sources, carbon panels, M64 reviews, scans) |

## Parts and design

| document | what it answers |
|---|---|
| [pieces/](pieces/) | one generated page per part record: status, material, sources, evidence |
| [993/](993/) | the design dossiers of the 993 parts (`*_F0`, `*_F1`) |
| [TITANIUM.md](TITANIUM.md) | when titanium is justified, and when it is not |
| [COMPONENT_INVENTORY.md](COMPONENT_INVENTORY.md) | the twin's physical components |
| [AM_VALIDATION_PIPELINE.md](AM_VALIDATION_PIPELINE.md) | the mandatory metal printing and Omniverse pipeline |

## 964/993 monocoque

| document | what it answers |
|---|---|
| [MONOCOQUE_964_993_PROGRAMME.md](MONOCOQUE_964_993_PROGRAMME.md) | the carbon monocoque program and what it must establish |
| [MONOCOQUE_964_993_ARCHITECTURE.md](MONOCOQUE_964_993_ARCHITECTURE.md) | architecture concept and layup strategy |
| [MONOCOQUE_964_993_CHAINE_CALCUL.md](MONOCOQUE_964_993_CHAINE_CALCUL.md) | the analysis chain: who does what, and where something else is needed |

## Digital twin and compute

Start with the [M64 architecture](architecture/README.md), its
[workflow](architecture/engineering-workflow.md) and
[migration/verification plan](architecture/migration-verification.md).
The [local Qwen pilot](../training/m64-qwen/README.md) implements the first AI increment.

| document | what it answers |
|---|---|
| [DIGITAL_TWIN.md](DIGITAL_TWIN.md) | the 993 digital twin, its zones and levels |
| [SOFTWARE_STACK.md](SOFTWARE_STACK.md) | the twin's software stack |
| [AI_DIGITAL_TWIN_STACK.md](AI_DIGITAL_TWIN_STACK.md) | the open-source suite for building the twin |
| [TOOLCHAIN.md](TOOLCHAIN.md) | the local CAD and analysis toolchain |
| [COMPUTE_ENVIRONMENT.md](COMPUTE_ENVIRONMENT.md) | compute environment and images |
| [GITHUB_OPENBAO_WRAPPER.md](GITHUB_OPENBAO_WRAPPER.md) | the GitHub wrapper bounded by OpenBao |

## 993 Turbo and forced induction

| document | what it answers |
|---|---|
| [TURBO_DIGITAL_TWIN_PLAN.md](TURBO_DIGITAL_TWIN_PLAN.md) | data plan for the 993 Turbo twin |
| [TURBO_AIRFLOW_SIMULATION_DATA.md](TURBO_AIRFLOW_SIMULATION_DATA.md) | airflow simulation data |
| [OPENFOAM_POISEUILLE_VERIFICATION_F25.md](OPENFOAM_POISEUILLE_VERIFICATION_F25.md) | OpenFOAM verification against Poiseuille flow |

## Decisions and reports

| document | what it answers |
|---|---|
| [decisions/](decisions/) | numbered architecture decisions (ADR 0001–0011) |
| [reports/](reports/README.md) | dated execution and audit reports, indexed by day |
| [media/](media/) | diagrams and video projects |
