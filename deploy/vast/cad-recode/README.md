# Culasse 935 : repartir du scan brut

R&D **non commerciale** avec CAD-Recode v1.5 (code et poids CC-BY-NC-4.0).
Aucune géométrie, simplification, coupe, orientation, interface ou matière de
l'ancienne reconstruction n'est réutilisée. Les anciens travaux restent intacts.
Les outils génériques seuls sont réutilisables. La pièce reste une référence
935, sans compatibilité 993 ni autorisation de fabrication.

## État et frontières

La préparation a été exécutée sur une VM Vast dédiée. Voir `verification.md`
pour les contrôles réellement exécutés et leurs limites. Aucune image publique.
`models.lock.json` fixe les révisions publiques ; `fetch.py` écrit les empreintes
réelles des fichiers téléchargés. Les bases Docker sont épinglées par digest.
CAD-Recode GPU, Nemotron et les outils OpenClaw ont été exécutés ; le parcours
SimReady est qualifié séparément.

Une culasse à ailettes et galeries dépasse les formes simples des benchmarks
CAD-Recode. Les 256 points d'entrée peuvent perdre des détails importants : le
premier passage complet est un diagnostic, jamais une preuve de reconstruction
fidèle. `face-components.npy` propose seulement des composants connexes ; leur
identité et toute subdivision anatomique exigent une revue du scan brut.
Aucun trou n'est rebouché automatiquement. Aucun résultat ancien n’alimente les nouveaux rapports.

## Préparation locale

Depuis la racine du dépôt (Python 3.11) :

```bash
uv venv --python 3.11 work/cad-recode-tools-venv
uv pip install --python work/cad-recode-tools-venv/bin/python -r scripts/cad_recode/requirements.txt
uv pip install --python work/cad-recode-tools-venv/bin/python huggingface-hub==0.27.0
PY=work/cad-recode-tools-venv/bin/python
$PY -m unittest discover -s tests -p test_cad_recode_fresh.py -v
$PY scripts/cad_recode/fetch.py work/cad-recode-models --weights all
$PY scripts/cad_recode/pipeline.py prepare \
  raw-scans/wolfe-classics-935-cylinder-head/original/935-xtreme-cylinder-head.obj \
  work/cad-recode-935-fresh/intake
```

Chaque sortie exige un répertoire nouveau, pour préserver les essais et leurs
échecs. Un téléchargement interrompu est conservé ; recommencer dans un autre
répertoire en profitant du cache HF. Aucun jeton HF n'est utilisé. Les scans,
poids, STEP et rapports restent dans les dossiers ignorés par Git.
Le SHA-256 attendu du brut est vérifié avant analyse. Le repère initial reste
XYZ brut : ni PCA interprétée comme datum, ni ancien repère importé.

Le prétraitement échantillonne 8192 points, puis sélectionne 256 points éloignés.
Il conserve centre, facteur de normalisation, graine et transformation inverse.
**Le code CAD-Recode est à l'échelle normalisée ×100** : le worker applique
`xyz_brut = xyz_CAD / 100 / normalization_scale + center`.
Les unités physiques restent inconnues ; le STEP utilise les unités numériques
OBJ pour inspection, sans prétendre que ses unités nominales soient mesurées.

## Machine et images

Cible : VM Vast Linux x86_64 avec Docker, NVIDIA Container Toolkit et accès GPU,
RTX PRO 6000 Blackwell 96 Go, 32 vCPU, 128 Go RAM, 500 Go NVMe. Une instance
conteneur standard n'est pas un substitut automatique à cette VM.
Construire sur la VM ; ne pas copier les identifiants du Mac.

```bash
docker build --platform linux/amd64 --target cad -f containers/cad-recode.Dockerfile -t 3dprinting993-cad-recode-cad:dev .
docker build --platform linux/amd64 --target inference -f containers/cad-recode.Dockerfile -t 3dprinting993-cad-recode-inference:dev .
docker build --platform linux/amd64 -f containers/cad-recode-openclaw.Dockerfile -t 3dprinting993-cad-recode-openclaw:dev .
```

Après tests, publier séparément les images autorisées et utiliser leurs références
`repository@sha256:…` : aucun digest de publication n'est inventé ici.
Pour un essai Docker local sans publication, la référence immuable retournée
par `docker image inspect --format '{{.Id}}' IMAGE` est également acceptée.
Consigner `pip freeze`, version pilote, `nvidia-smi`, inventaire GPU, image et
résultats des smoke tests. Un build Mac émulé ne prouve pas l'inférence Blackwell.

## Inférence et évaluation

Le runtime utilise PyTorch CUDA 12.8 et l'attention eager, sans reprendre
l'ancienne compilation FlashAttention CUDA 12.4. Tester les imports et une
inférence avant un travail long. Aucune bascule CPU silencieuse.

```bash
# MODEL_DIR et RUN_DIR : chemins absolus, hors Git ; images construites ci-dessus.
mkdir -p "$RUN_DIR/inference"
chmod 0777 "$RUN_DIR/inference"  # Seule cette sortie est inscriptible par UID 65534.
docker run --rm --gpus all --network=none --read-only --cap-drop=ALL \
  --security-opt=no-new-privileges --tmpfs /tmp --memory=24g \
  -v "$MODEL_DIR:/models:ro" -v "$RUN_DIR/intake:/input:ro" \
  -v "$RUN_DIR/inference:/output" \
  3dprinting993-cad-recode-inference:dev /input /models /output/proposals --attempts 3

$PY scripts/cad_recode/pipeline.py export \
  "$RUN_DIR/inference/proposals/candidate-1.py" "$RUN_DIR/intake" "$RUN_DIR/export-1" \
  --image "$CAD_IMAGE" --timeout 180
```

Les trois propositions sont des générations distinctes, pas trois succès.
Le code doit définir `r`, un Workplane CadQuery. Le worker est jetable, sans
réseau, sans secret, non privilégié, avec 4 Go RAM, 2 CPU et timeout.
L'évaluation relit le STEP séparément et mesure les distances **surface à
surface, échantillonnées dans les deux sens** ; maximum échantillonné ≠ Hausdorff
exacte. Aucun seuil dimensionnel n'est inventé. Pour les sorties non fiables,
utiliser le dispatcher qui isole aussi le parseur STEP dans un conteneur.

## OpenClaw et Nemotron sur Vast

`compose.yaml` garde vLLM et OpenClaw sur la boucle locale de la VM. Le contexte
initial est 32K, une seule séquence et 50 % de VRAM réservée à vLLM. Adapter cette
réserve uniquement après mesure. La configuration sans authentification du
gateway est limitée à loopback : accès uniquement par SSH sur une VM dédiée.
Ne pas changer le bind pour une interface publique.

Définir des chemins absolus pour `CAD_MODELS`, `CAD_RUN`, `CAD_AGENT_STATE` et
`CAD_AGENT_WORKSPACE`. Créer les dossiers état/workspace avec UID/GID 1000,
puis copier `AGENT.md` vers `$CAD_AGENT_WORKSPACE/AGENTS.md` et créer `requests/`.
Copier les propositions générées dans le workspace, sans anciennes géométries.

```bash
docker compose -f deploy/vast/cad-recode/compose.yaml config --quiet
docker compose -f deploy/vast/cad-recode/compose.yaml build openclaw
docker compose -f deploy/vast/cad-recode/compose.yaml run --rm --no-deps openclaw config validate
docker compose -f deploy/vast/cad-recode/compose.yaml up -d nemotron
python3 deploy/vast/cad-recode/smoke-nemotron.py
docker compose -f deploy/vast/cad-recode/compose.yaml up -d openclaw
```

Le modèle FP8 et son parseur doivent être présents dans le snapshot épinglé.
Le smoke exige un vrai appel d'outil JSON ; `/health` seul ne suffit pas.
OpenClaw dispose uniquement de lecture/écriture/édition du workspace. **Pas de
shell, socket Docker, compte Vast, ancienne mémoire ou secret.** L'opérateur
lance le dispatcher depuis la VM (répéter après chaque demande de l'agent) :

```bash
$PY scripts/cad_recode/dispatch.py "$CAD_AGENT_WORKSPACE" "$CAD_RUN" --cad-image "$CAD_IMAGE"
```

Seuls `export` et `evaluate`, avec tentatives 1 à 3, sont acceptés. Le dossier de
résultats est monté en lecture seule dans OpenClaw. Les requêtes ne permettent
ni de choisir une image, ni de modifier une commande, ni de louer une machine.
Le profil Compose `omniverse` ajoute le VLM local Qwen2.5-VL-7B épinglé, sur
127.0.0.1:8003 avec 23 % de VRAM. Le démarrer après Nemotron ; les deux
réservent environ 72 Go au total sur cette machine. Arrêter les modèles avant
un rendu lourd si la VRAM disponible est insuffisante. Sauvegarder via SSH les seules sorties,
requêtes et conversations nécessaires ; pas de configuration d'authentification.

## Content Agents locaux sur la VM qualifiée

La session utilise Content Agents v0.5.2, le convertisseur `usd-convert-cad`
0.2.0 dans un venv Python 3.12 isolé, et le runtime SimReady épinglé installé
par le preflight. Voir le manifeste sauvegardé pour les versions complètes.
Le VLM se lance après Nemotron :

```bash
docker compose -f deploy/vast/cad-recode/compose.yaml --profile omniverse up -d vlm
python3 deploy/vast/cad-recode/smoke-vlm.py
```

Dans le checkout Content Agents créé par le preflight, appliquer
`content-agents-local.patch` : ports publiés sur loopback et renderer joint
par son nom Docker interne, reconnu comme local par les services amont.
Démarrer OVRTX avec `OVRTX_HOST_PORT=127.0.0.1:8001`, créer le réseau
`content-agents-network`, puis y connecter le conteneur OVRTX avec l'alias
`ovrtx-rendering-api` avant le déploiement Material/Physics.

Les modèles restent sur loopback. Sur cette VM, `docker0` est 172.17.0.1 ;
les services les joignent via deux relais limités à cette interface :

```bash
# socat doit être installé ; vérifier l'adresse docker0 avant réemploi.
for port in 8002 8003; do
  systemd-run --unit=cad-proxy-$port socat TCP-LISTEN:$port,bind=172.17.0.1,reuseaddr,fork TCP:127.0.0.1:$port
done
```

Configurer le preflight avec les backends `openai`, le VLM `cad-vlm` à
`http://host.docker.internal:8003/v1` et le LLM `nemotron-cad` à
`http://host.docker.internal:8002/v1`. Les variables `LOCAL_VLM_API_KEY` et
`LOCAL_LLM_API_KEY` valent littéralement `local-unused` : marqueurs exigés
par le client local, sans compte externe ni secret fournisseur.
Dans `deploy/collection/collection.yaml`, limiter
`dependencies.vlm.max_tokens` à 2048 pour le contexte VLM de 8192 tokens.
Utiliser `USD_CONVERT_CAD_PYTHON` pour le venv du convertisseur, et exécuter
le preflight avec le Python du venv SimReady (+ PyYAML 6.0.2).

La VM avait un conflit après une mise à jour automatique des bibliothèques
NVIDIA ; le pilote a été rechargé sans processus GPU actif. Pour reproduire,
contrôler la cohérence pilote/NVML avant de démarrer les modèles. Ne jamais
recharger un pilote pendant un calcul. Les timers apt ont été suspendus
uniquement dans cet invité éphémère pendant la qualification.

## Calculs physiques : dossier neuf

`engineering-inputs.json` repart vide. La commande suivante fournit les manques
et retourne 3 tant qu'une revue d'ingénierie n'a pas été effectuée :

```bash
$PY scripts/cad_recode/pipeline.py readiness \
  deploy/vast/cad-recode/engineering-inputs.json "$RUN_DIR/physics-readiness"
```

Réutiliser les solveurs de `containers/cadsim.Dockerfile`, mais aucun ancien cas
culasse. Pour OpenFOAM : `benchmarks/openfoam-poiseuille-f25/run_local.sh` vérifie
un problème analytique indépendant. Le script `scripts/cad_recode/ccx_smoke.py OUTPUT --ccx ccx` vérifie une
barre en traction (`u=FL/EA`) et une conduction 1D (`q=kAΔT/L`) en exécutant réellement CalculiX. Les propriétés et
charges de ces fixtures synthétiques ne deviennent jamais celles de la culasse.
PhysicsNeMo reste préparé par l'image isolée existante, sans entraînement.

## Parcours SimReady complet, étapes séparées

Installer le skill `omniverse-cad-to-simready` et son environnement Python 3.12.
`simready-stage.sh` appelle directement ses références, sans runner monolithique.
Définir `SIMREADY_SKILL_ROOT`, `SIMREADY_PYTHON` et un nouveau dossier `OV`.

1. `bash deploy/vast/cad-recode/simready-stage.sh preflight --env-file "$OV/preflight.env" --report "$OV/preflight.json" --markdown-report "$OV/preflight.md"`, puis sourcer le fichier env.
2. Vérifier les services OVRTX, Material et Physics avant inspection/conversion. Utiliser le VLM Qwen2.5-VL-7B déjà prévu par les outils SimReady, et arrêter Nemotron si la VRAM l'exige. Les secrets éventuels doivent venir exclusivement du wrapper OpenBao approuvé ; une absence bloque ce parcours.
3. Appeler `identify-asset-context`, puis `convert-to-usd` séparément sur le scan et le STEP candidat ; conserver les chemins USD rapportés, sans supposer leur nom.
4. Valider chaque USD avec `validate-usd-minimum`. Pour la superposition, appeler `scripts/cad_recode/assemble.py SCAN_USD CAD_USD COMPARISON_USDA --scan-display-scale S --cad-display-scale C` dans l'environnement USD. Déterminer S et C depuis les transformations rapportées par le convertisseur : jamais depuis une dimension Porsche supposée. Ces échelles sont seulement visuelles ; leurs valeurs restent à vérifier au premier run du convertisseur.
5. Sur une copie expérimentale du candidat, appeler `content-agents` avec `--call material --call physics --convert-physics-output-to-usd`, puis `simready-conform-profile --profile Prop-Robotics-Neutral`. Ne jamais modifier le scan ou le STEP maîtres.
6. Appeler dans l'ordre `omni-asset-validate`, `omni-asset-validate-geometry`, `omni-asset-validate-physics`, `simready-validate`, puis `ovrtx-render-service`. Réutiliser à chaque fois le `output_usd_path` réel du rapport précédent.
7. Conserver les demandes de correction FET et leurs preuves. Sans propriétés/échelle/préhensions justifiables : `blocked` ou `needs_rerun`, jamais une conformité forcée. Vérifier que les images ne sont ni vides ni uniformes.

Les flags détaillés restent ceux de `references/commands.md` du skill installé.
Le profil SimReady décrit un objet manipulable, pas un moteur validé. Les
matériaux, densités et collisions expérimentaux ne sont ni des mesures ni une
validation de résistance/fatigue. Pas de texture ou de publication publique.

## Sources

- https://github.com/filaPro/cad-recode — architecture, notebook et licence.
- https://huggingface.co/filapro/cad-recode-v1.5 — poids non commerciaux.
- https://github.com/vllm-project/recipes/blob/main/NVIDIA/Nemotron-3-Nano-30B-A3B.md
- https://docs.openclaw.ai/gateway/config-tools/custom-providers
- https://vast.ai/article/announcing-virtual-machine-rental-on-vast-ai

### Reprise depuis les triangles : profils et surfaces partielles

Après le rejet visuel de la reconstruction globale à 256 points, les commandes
suivantes repartent de l'OBJ brut et de son empreinte. Aucun ancien repère ni
ancienne géométrie de culasse n'est importé. Exécuter dans le runtime CAO qualifié,
avec le dépôt comme répertoire courant :

```sh
python -m scripts.cad_recode.recover_sections SOURCE.obj OUTPUT/profiles --sha256 SHA256
python -m scripts.cad_recode.recover_planes SOURCE.obj OUTPUT/surfaces --sha256 SHA256
```

Les sorties sont des cercles analytiques et des faces planes découpées, en STEP,
avec leurs paramètres JSON. Ce ne sont pas une culasse complète ni un solide.
Les contours ouverts ne sont pas refermés ; les triangles formant des pincements
sont retirés des seules zones candidates, sans modifier le scan original.

Les seuils exploratoires de 0,6 unité OBJ pour les profils et 0,4 pour la projection
plane sont réglables par `--profile-tolerance` et `--projection-tolerance`.
Ils ne constituent pas des tolérances mécaniques. L'échelle physique reste inconnue.
Un arc incomplet, un mauvais ajustement, une surface sans support dans le scan ou
un STEP qui échoue à la relecture est rejeté. Les vérifications vers le scan sont
échantillonnées ; elles ne prouvent ni l'exactitude globale ni l'aptitude à fabriquer.

Vérification ciblée : `python -m unittest tests.test_cad_recode_sections`.

Pour combler les **petites lacunes du scan**, sur une copie conservant exactement
les sommets et triangles originaux :

```sh
python -m scripts.cad_recode.repair_scan_gaps SOURCE.obj OUTPUT/profiles/profiles.json OUTPUT/repaired --sha256 SHA256
```

Le script protège les ouvertures circulaires relevées, impose une frontière fermée,
une continuité des normales avec la surface voisine, une triangulation sans nouvelle
arête non-manifold et une relecture OBJ exacte. Les paramètres `--max-gap` (3 unités
OBJ par défaut) et `--max-planarity` (0,25) sont des limites de réparation exploratoires.
Les grands contours, les frontières branchées et les zones ambiguës restent ouverts.
Le rapport distingue explicitement les surfaces ajoutées par interpolation des surfaces
mesurées. Cette opération ne rend pas automatiquement le maillage étanche.
