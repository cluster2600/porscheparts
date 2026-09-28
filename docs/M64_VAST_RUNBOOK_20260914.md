# Playbook d’exécution Vast pour la suite culasse 993/964 (M64)

## Objectif

- Lancer un lot 2V/4V avec OpenFOAM + Cantera + PhysicsNemo sans sortir du budget.
- Obtenir :
  1) maillage CFD et checks OpenFOAM,
  2) prévision thermique couplée (air + métal),
  3) comparaison 2V vs 4V sur un même cas moteur cible (`700 hp` cible d’usage),
  4) rapport JSON lisible.

## Stack cible

- **Image de base**: `ghcr.io/cluster2600/3dprinting993-mesh-cfd` (comme le pipeline existant).
- **Dépendances Python**: `trimesh`, `pymeshlab`, `build123d`, `gmsh`, `numpy`,
  `scipy`, `cantera`, `openfoam`.
- **Préférer** `openfoam-dev` uniquement si la stabilité OpenFOAM 13 du lot
  est confirmée par l’instance.

Le script `check_openfoam_mesh.sh` requiert un environnement OpenFOAM présent
(`source /opt/openfoam13/etc/bashrc`).
Sur la machine locale, exécuter depuis le conteneur si ce chemin n’existe pas.

## Job 1 — Readiness + géométrie

### Mode court (sans scan 993 encore disponible)

```bash
cd /workspace/3dprinting993
PIPELINE=work/993-cylinder-head-fast
PYTHON=/opt/venv/bin/python \
twins/reference-993-cylinder-head/source/verify_outputs.py "${PIPELINE}"
python3 twins/reference-993-cylinder-head/source/build_physics_readiness.py \
  --pipeline "${PIPELINE}" \
  --contract twins/reference-993-cylinder-head/reengineering-contract.json \
  --inputs twins/reference-993-cylinder-head/engineering-inputs.template.json \
  --output "${PIPELINE}/reports/physics-readiness.json"
```

Quand le scan 993 réel sera disponible, basculer vers :

```bash
cd /workspace/3dprinting993
SCAN_OBJ=/Users/maxime/projects/3dprinting993/raw-scans/993-cylinder-head/original/scan.obj
PIPELINE=work/993-cylinder-head/pipeline
PYTHON=/opt/venv/bin/python \
twins/reference-993-cylinder-head/run_pipeline.sh "${SCAN_OBJ}" "${PIPELINE}"
```

## Job 2 — OpenFOAM + checks

```bash
cd /workspace/3dprinting993
twins/reference-993-cylinder-head/source/check_openfoam_mesh.sh \
  work/993-cylinder-head/pipeline/cfd/high_B/fluid-domain.msh \
  work/993-cylinder-head/pipeline/openfoam/high_B
```

Ou proxy local déjà prêt :

```bash
cd /workspace/3dprinting993
twins/reference-993-cylinder-head/source/check_openfoam_mesh.sh \
  work/993-cylinder-head-fast/cfd/high_B/fluid-domain.msh \
  work/993-cylinder-head-fast/openfoam/high_B
```

Avec optimisations `build_cfd_stubs.py` (option locale) :

```bash
cd /workspace/3dprinting993
twins/reference-993-cylinder-head/source/check_openfoam_mesh.sh \
  work/993-cylinder-head-fast/cfd-improved/high_B/fluid-domain.msh \
  work/993-cylinder-head-fast/openfoam-improved/high_B
```

## Job 3 — Rapport de readiness à partir de cas injectés

```bash
cd /workspace/3dprinting993
python3 twins/reference-993-cylinder-head/source/build_physics_readiness.py \
  --pipeline work/993-cylinder-head/pipeline \
  --contract twins/reference-993-cylinder-head/reengineering-contract.json \
  --inputs twins/reference-993-cylinder-head/engineering-inputs.template.json \
  --output work/993-cylinder-head/pipeline/reports/physics-readiness.json
```

Pour le lot proxy (si pas de scan 993):

```bash
cd /workspace/3dprinting993
python3 twins/reference-993-cylinder-head/source/build_physics_readiness.py \
  --pipeline work/993-cylinder-head-fast \
  --contract twins/reference-993-cylinder-head/reengineering-contract.json \
  --inputs twins/reference-993-cylinder-head/engineering-inputs.template.json \
  --output work/993-cylinder-head-fast/reports/physics-readiness.json
```

## Gouvernance des sorties

- `physics-readiness.json`: garde-fou sur les niveaux F0→F6.
- `derived/*/mesh_metadata.json` : suivi numérique.
- `work/993-cylinder-head/pipeline/reports` : centraliser ici pour push de preuve.
- Les fichiers de scan lourds restent hors Git, comme le contrat de gouvernance.

## Coût et durée

- Lancer sur instance 16 vCPU + 64 Go RAM + 1x A100/H100 si dispo (ou équivalent).
- Garder l’instance 6–12 h en continuation, arrêter après sortie `physics-readiness`.
- Ne pas faire de validation "moteur" tant que les cotes physique/CT/temps ne sont pas
  fermées.
