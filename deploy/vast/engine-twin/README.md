# Session GPU du 2026-09-15 : jumeau moteur M64 par agents

Deux instances Vast.ai, pilotées depuis le Mac, bornées à **60 USD et 6 h**.
Manifeste : [`twins/m64-engine-twin/session-20260915.json`](../../../twins/m64-engine-twin/session-20260915.json).
Rien de ce qui sort ce soir n'est une géométrie maître ni une pièce fabricable :
tout composant accepté l'est au statut `accepted_unreviewed`.

## Architecture

| noeud | rôle | matériel | plafond |
|---|---|---|---|
| LLM | vLLM, `Qwen3-Coder-30B-A3B-Instruct-FP8` à révision épinglée, 64 séquences simultanées | 1 × H100 80 GB (ou RTX PRO 6000) | 2,60 USD/h |
| calcul | orchestrateur, 32 agents, exécution CadQuery sans réseau, CFD/FEA GPU, USD | ≥ 64 cœurs, ≥ 256 GB RAM, 1 GPU ≥ 48 GB, 500 GB | 2,60 USD/h |

Budget au pire : (2,60 + 2,60) × 6 h + 5 USD de réserve = 36,20 USD, sous le plafond.

Le modèle est celui déjà qualifié par le profil `research-qwen-v1`. Un 30B MoE
(3B actifs) sert plusieurs dizaines d'agents sur une seule carte ; un modèle plus
gros exigerait 4 à 8 GPU et ferait sortir du budget.

L'API vLLM n'écoute que sur `127.0.0.1`. Le noeud calcul l'atteint par tunnel SSH
avec une clé de session éphémère, autorisée seulement sur le noeud LLM et
détruite avec les instances.

## Boucle d'un agent

1. Fiche composant (brief, enveloppe, rapports des dépendances acceptées) et
   paramètres résolus de G1 (`parameters-resolved.json`).
2. Le LLM renvoie un module `build(p)` CadQuery. Filtre statique : pas d'`os`,
   `subprocess`, réseau, `open`, `eval`.
3. `cad_harness.py` l'exécute dans `docker run --network none --memory 6g`.
   Contrôles : BRep valide, solide fermé, volume > 0, boîte englobante dans
   l'enveloppe, export STEP.
4. En cas d'échec, l'erreur revient à l'agent (6 itérations au plus), sinon
   `failed_closed`. Les dépendants d'un composant échoué passent en
   `blocked_dependency`.
5. Aucun nouveau travail dans la dernière heure : elle sert à l'assemblage, à la
   collecte et à la destruction.

## Déjà vérifié le 2026-09-15

- `tests/test_m64_engine_twin_session.py` : budget, digests, ordre topologique,
  filtre, enveloppe, reprise sur erreur, blocage des dépendants, échéance.
- `cad_harness.py` dans `3dprinting993-cadsim:dev` sans réseau : cylindre valide,
  STEP exporté.
- `cad-author-f28` et `mesh-cfd` **n'ont pas CadQuery** ; l'image CAO retenue
  est `simready-local-ai`, qui l'installe dans `/opt/venv`.

## FEA (CPU, image `cadsim`)

`twins/m64-engine-twin/source/fea_screens.py` : maillage Gmsh C3D10, CalculiX,
deux tailles de maille et écart de convergence, sortie `screen_unreviewed`.

- `--kind modal` : modes élastiques libre-libre. Des ressorts de sol à 0,5 Hz
  isolent les six modes rigides ; le script refuse le résultat s'il n'en trouve
  pas exactement six sous 5 Hz. Le libre-libre pur rendait des parasites
  (valeurs quasi nulles en surnombre, 0,6 Hz et 18 Hz).
- `--kind static` : encastrement d'une tranche, force totale sur une autre ;
  la force est une hypothèse déclarée.
- Auto-contrôle (`--self-check`), poutre acier L 400 r 10 :
  f1 = 571,8 Hz contre 575,5 Hz analytique (0,65 %) ; flèche 1,2917 mm contre
  1,2934 mm (0,14 %). Preuve : `twins/m64-engine-twin/evidence/fea-self-check-20260915.json`.

`ccx` est absent de `simready-local-ai` : les FEA tournent sur les STEP
collectés, dans `cadsim`, une pièce à la fois avec mémoire plafonnée.

```sh
docker run --rm --network none --memory 10g -v "$PWD:/repo:ro" -v "$OUT:/out" \
  --entrypoint python3 3dprinting993-cadsim:dev /repo/twins/m64-engine-twin/source/fea_screens.py \
  --kind modal --component crankshaft --material steel_42crmo4_hypothesis \
  --step /out/agents/crankshaft/iter-NN/out/part.step --out /out/fea/crankshaft --mesh-sizes 8 5
```

## Profil `engine-twin-v1` du wrapper

Deux locations **appariées mais indépendantes**, une par rôle, chacune avec son
manifeste, son label, sa tentative payante unique et **sa propre garde** :

| | llm | compute |
|---|---|---|
| label | `3dprinting993-engine-twin-llm-<hex20>` | `3dprinting993-engine-twin-compute-<hex20>` (même hex) |
| image | `vllm/vllm-openai@sha256:7a0f0f…` | `simready-local-ai@sha256:5a69a6…` |
| matériel | 1 GPU ≥ 80 GB, 16 cœurs, 64 GB, 150 GB | 1 GPU ≥ 48 GB, 64 cœurs, 256 GB, 500 GB |
| onstart | vLLM `127.0.0.1:8000`, `timeout` relatif | `sleep` borné ; jobs par SSH |

Plafonds communs : 2,60 USD/h, 6 h, 30 USD par rôle (donc 60 USD pour la paire),
transferts ≤ 0,01 USD/GB, fiabilité ≥ 0,99, machine vérifiée.

Le contrôle d'unicité tolère **uniquement le label sœur exact** de la même
session ; toute autre location sur le compte bloque le lancement. La garde
`deploy/vast/engine-twin/deadline_guard.py` (SHA épinglé dans le wrapper) est une
politique au-dessus du moteur PicoGK inchangé : elle masque la sœur exacte dans
sa vue d'inventaire, pour que les deux gardes ne se détruisent pas mutuellement,
et reste sensible à tout le reste.

Tests : `tests/test_openbao_vastai_engine_twin.py` ; non-régression wrapper,
recherche et gardes (205 tests) au vert.

## Reste à faire avant de louer

1. **Réinstaller le wrapper sur le Mac** (`install -m 0755 …`) puis
   `openbao-vastai --check` : l'empreinte change, aucune garde d'une autre
   session ne doit être armée à ce moment.
2. **Qualifications** `llm-qualification.json` et `compute-qualification.json` :
   digest relu anonymement, tailles d'image et de poids mesurées.
3. **Exécution réelle de `cad_harness.py` dans `simready-local-ai`** sur le
   noeud calcul, avant de lancer les agents (`--executor local`).

## Déroulé du soir

```sh
# Mac, avant tout appel payant
openbao-vastai --auth-check
openbao-vastai account-balance
openbao-vastai engine-twin-offers llm
openbao-vastai engine-twin-offers compute

# une fois par role : manifeste 0600, puis garde armee AVANT la location
python3 deploy/vast/engine-twin/deadline_guard.py /abs/engine-twin-llm-20260915.json &
openbao-vastai launch-engine-twin LLM_OFFER /abs/engine-twin-llm-20260915.json
python3 deploy/vast/engine-twin/deadline_guard.py /abs/engine-twin-compute-20260915.json &
openbao-vastai launch-engine-twin COMPUTE_OFFER /abs/engine-twin-compute-20260915.json
# en cas d'echec incertain : openbao-vastai reconcile-engine-twin /abs/<manifeste>.json

# noeud LLM : onstart = deploy/vast/engine-twin/llm-onstart.sh ; attendre /workspace/READY

# noeud calcul : répétition du harnais, puis agents
python3 twins/m64-engine-twin/source/orchestrate_agents.py --help
deploy/vast/engine-twin/compute-run.sh root@LLM_HOST:LLM_PORT DEADLINE_EPOCH

# en parallèle sur le GPU du noeud calcul, jobs existants
make turbo-cold-side
twins/m64-cylinder-head/run_cht_runtime_smoke.sh

# fin : collecte de /workspace/out, puis destruction et vérification d'absence
```

Répétition locale sans GPU, avec l'image `cadsim` :

```sh
python3 twins/m64-engine-twin/source/orchestrate_agents.py \
  --params twins/m64-cylinder-head/evidence/g1-four-valve-20260914/parameters-resolved.json \
  --out work/m64-engine-twin-rehearsal --deadline-epoch $(( $(date +%s) + 7200 )) \
  --llm-base-url http://127.0.0.1:8000/v1 --cad-image 3dprinting993-cadsim:dev --cad-python python3
```
