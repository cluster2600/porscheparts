# Porsche 917 — contrôleur Vast CFD/CAE F46

## Verdict actuel

Le contrôleur est préparé, mais **aucune location n'a été lancée et aucune
dépense n'a été engagée**. Il bloque aujourd'hui pour trois raisons factuelles :

- aucun digest de l'image unifiée `3dprinting993-cfd-cae-f46` n'est publié et
  verrouillé dans le contrat ;
- les domaines 2V/4V et les cartes matériau nécessaires aux jobs F46 ne sont
  pas complets ;
- les commandes de calcul et leurs manifestes d'entrée n'ont donc pas de
  SHA-256 qualifié.

Les images déjà présentes ne sont pas substituables : l'image cycle F33 couvre
Cantera, l'image CAE F33 locale couvre OpenFOAM/CalculiX mais sa preuve publiée
est `arm64`, et l'image SimReady couvre CUDA/PhysicsNeMo sans prouver la chaîne
CFD/CAE complète.

L'[autorité solveurs F46](../twins/reference-917-engine/engine-solver-authority-f46.json)
est liée par SHA-256 au contrôleur et au manifeste. Les sources officielles
retenues ne prouvent aucun exécutable autonome portant le nom demandé. Le champ
`exact_ICEEngineFoam_executable_found` reste donc obligatoirement `false` et un
alias fabriqué bloque la préparation comme l'exécution.

## Architecture fail-closed

```text
instantané offres ─┐
preuve GHCR/amd64 ─┼─> plan F46 ─> lancement wrapper GHCR→Vast
inventaire vide ───┤      |                    |
ledger antérieur ──┘      |                    +─ rollback post-création
                           |
                           +─ deadline locale = deadline distante
                           +─ calcul coût conservatif chaque minute
                           +─ STOP distant puis destruction locale
                           +─ inventaire paginé final vide
```

Le code de décision
[`_f46_controller.py`](../deploy/vast/f46/_f46_controller.py) ne connaît aucun
secret et ne contacte aucun service. Il relit des instantanés JSON non secrets.
Les accès GHCR et Vast passent uniquement par les wrappers OpenBao approuvés.

Le lanceur [`run-controller.sh`](../deploy/vast/f46/run-controller.sh) est en
mode plan par défaut. Le mode mutateur nécessite `--execute`, un plan dont
`launch_authorized=true`, et des copies locales des wrappers strictement
identiques aux versions suivies dans Git. Un tag d'image, une plateforme
`arm64`, un smoke incomplet, une offre périmée ou un inventaire F46 non vide
bloquent avant l'appel de location.

Cette transplantation est basée sur le HEAD d'intégration `18b389b`. Elle
conserve les labels de tentative aléatoires, l'inventaire strict paginé, le
verrou de lancement partagé, la réconciliation d'une création ambiguë et la
preuve d'absence stable déjà imposés par les wrappers actuels. Le label payé
est de la forme `3dprinting993-f46-cfd-cae-<20 hex>` ; le préfixe seul n'est
jamais utilisé comme identifiant d'une tentative.

## Machine admissible et sélection

La sélection porte sur une offre `on-demand`, vérifiée, disponible, avec un GPU
entier et un coût total disque inclus inférieur ou égal à 2,50 USD/h. Les noms
acceptés sont, dans l'ordre :

1. `RTX PRO 6000 WS` ;
2. `RTX PRO 6000 Blackwell Max-Q` ;
3. `RTX A6000`.

Le minimum commun est 48 Go de VRAM, 24 cœurs CPU effectifs, 128 Go de RAM et
500 Go de disque. OpenFOAM et CalculiX restent souvent limités par le CPU et la
mémoire ; le contrôleur départage donc ensuite par cœurs CPU, RAM, coût et
identifiant stable. Il ne code aucun identifiant d'offre, car une offre Vast
est temporaire.

Les tarifs `inet_up_cost` et `inet_down_cost` doivent être présents et égaux à
zéro. Une offre dont le transfert est facturable est rejetée : sans volume de
transfert borné, elle serait incompatible avec un plafond total de 23 USD.

Le wrapper expose seulement des métadonnées sûres avec :

```sh
"${OPENBAO_VASTAI_BIN}" f46-offers > work/f46-offers.json
"${OPENBAO_VASTAI_BIN}" instances > work/f46-instances.json
```

Ces commandes ne sont pas exécutées par la validation du dépôt.

## Image obligatoire

L'image doit appartenir exactement à
`ghcr.io/cluster2600/3dprinting993-cfd-cae-f46` et être appelée par digest. Le
wrapper GHCR futur vérifie l'index puis l'unique manifeste `linux/amd64` :

```sh
"${OPENBAO_GHCR_BIN}" verify-f46 \
  'ghcr.io/cluster2600/3dprinting993-cfd-cae-f46@sha256:<64-hex>' \
  > work/f46-registry-proof.json
```

Cette preuve de registre conserve volontairement
`runtime_smoke_verified=false`. Une preuve CI séparée doit montrer les versions
épinglées et les smokes minimaux de `foamRun`, du framework AATE/OpenFOAM
ICengines verrouillé à la révision officielle, de Cantera 3.2.0, du solveur CHT,
de CalculiX, de CUDA et de `f46-run-manifest`. Le solveur historique OpenFOAM
3.0.x `engineFoam` n'est contrôlé et fumé que s'il est réellement construit
depuis sa révision verrouillée ; son absence doit être déclarée `not_built`.

Avant toute location, la preuve combinée doit être commitée ; son chemin, son
SHA-256 et le digest de l'image doivent remplacer les trois valeurs `null` de
`image_policy`. Le contrôleur relit alors le fichier commit-é et refuse un JSON
fourni différent. Le wrapper GHCR revalide encore le registre juste avant de
déléguer le lancement au wrapper Vast ; aucun credential GitHub n'est transmis
à Vast.

## Budget et TTL

Le plafond dur est 23 USD : 20 USD maximum sont planifiés pour la fenêtre
d'instance et 3 USD restent réservés au cleanup et aux arrondis de facturation.
Les transferts facturables sont interdits avant lancement. Le débit horaire de
l'instance créée est relu, et non déduit du prix public de l'offre.

À chaque contrôle :

```text
charge courante = max(charge fournisseur disponible,
                      durée écoulée × dph_total / 3600)
coût cumulé      = somme immuable des charges finalisées + charge courante
```

La fenêtre ne dépasse jamais huit heures. La deadline locale et celle passée
au `f46-vast-onstart` distant avant même la réponse du lancement sont le même
entier Unix. Le calcul s'arrête trente minutes avant la fin afin de laisser la
collecte et la destruction. Si le coût
atteint 20 USD, si le prix change, si l'identité dérive ou si une valeur de coût
manque, le calcul est arrêté et le cleanup devient obligatoire. Un dépassement
constaté ne désactive jamais la destruction.

## Jobs prévus

Le [manifeste F46](../twins/reference-917-engine/f46-vast-job-manifest.json)
réserve 26 cas :

| Famille | Cas | Fenêtre maximale | Blocage actuel principal |
|---|---:|---:|---|
| OpenFOAM G3 | 6 | 60 min | domaines 2V/4V étanches |
| AATE/OpenFOAM ICengines G4 | 6 | 90 min | application construite, domaines mobiles et lois de soupapes |
| Cantera 3.2.0 G4 | 2 | 15 min | modèle angle-vilebrequin commun |
| CHT G5 | 6 | 120 min | air installé, solide et carte chaude |
| FEA thermomécanique | 6 | 135 min | champ CHT accepté et carte chaude |

Chaque commande reste `null`. Lorsqu'un domaine recevable apparaîtra, chaque
job devra contenir une liste d'arguments sans shell, le chemin d'un manifeste
d'entrée local et son SHA-256, les bilans masse/énergie et les trois maillages
prévus par F43. Le contrôleur relit le manifeste d'entrée et refuse toute forme
nommée ovale/elliptique ou tout alias géométrique F39/F42. Les sections
fonctionnelles doivent rester circulaires et justifiées. Le
contrôleur ne peut autoriser le lancement que lorsque les cinq familles sont
prêtes ; il ne dépense pas 23 USD pour un sous-ensemble incohérent.

## Destruction et preuve finale

Le trap est armé avant le lancement. Il couvre sortie normale, erreur, `INT`,
`TERM`, deadline, plafond de coût et dérive de contrat. Le wrapper de lancement
fait aussi un rollback si la réponse de création est ambiguë ou si les
postconditions singleton/image/machine/coût échouent.

Le cleanup tente jusqu'à cinq destructions via le superviseur existant, puis
relit toutes les pages d'instances. Une création ambiguë est réconciliée avec
le label aléatoire exact préenregistré, jamais avec une recherche destructive
large. Le rapport final n'est recevable que si l'identifiant a disparu et si
l'inventaire de toute la famille F46 est vide. Si les
résultats ne sont pas récupérables, la dérogation explicite
`NO-RETRIEVAL:<job>:<instance>:<digest>` privilégie la fin de facturation et
rabaisse toute prétention de simulation.

Un arrêt brutal du poste de contrôle (`SIGKILL`, panne réseau ou électrique)
ne peut pas appeler l'API Vast. Le runner distant arrête les solveurs à sa TTL,
mais il ne reçoit volontairement aucun secret permettant de détruire
l'instance. Cette limite interdit une affirmation de cleanup garanti face à la
perte totale du contrôleur ; une automation externe indépendante sera requise
avant une campagne sans surveillance.

## Vérification locale sans dépense

```sh
python3 deploy/vast/f46/_f46_controller.py \
  --contract twins/reference-917-engine/f46-vast-cfd-cae-controller.json \
  --jobs twins/reference-917-engine/f46-vast-job-manifest.json \
  --root . check
python3 twins/reference-917-engine/source/validate_engine_solver_authority_f46.py \
  --project-root .
python3 tests/test_917_engine_solver_authority_f46.py -v
python3 tests/test_917_f46_vast_controller.py -v
make 917-f46-vast-controller-check
```

La fixture associée est artificielle et le contrôleur la refuse sans
`--allow-synthetic-fixture`. Elle ne constitue ni une offre, ni une image, ni
une instance, ni une dépense réelle.
