# Station PicoGK sur Vast

Le profil ajoute cinq opérations au wrapper OpenBao existant, par deux hooks
dans sa fonction `run`. Il conserve son authentification, ses variantes, son
verrou de lancement et sa réconciliation après une réponse de création perdue.
Le wrapper installé n'est jamais remplacé par la copie historique du dépôt.

## Accès depuis Kali2

Le tableau de bord OpenClaw répond sur **http://127.0.0.1:18789/** sur Kali2
(HTTP 200 observé le 28 septembre 2026). Depuis un autre poste, transférer ce
port par la connexion SSH approuvée vers Kali2, puis ouvrir la même adresse
locale. La station **53246885** a été déployée le 28 septembre 2026. Une réponse
Qwen et une génération PicoGK commandée par `m64-coordinator`, avec récupération
et vérification des fichiers, sont prouvées dans le
[rapport de qualification](../../../twins/picogk-station-demo/qualification/README.md).
Ce rapport distingue chaque essai, les corrections runtime et l'endurance.
La publication réutilise le jeton éphémère GitHub
Actions, doté de `packages: write`, sur un runner Kali2 limité à un seul job.

Le client Omniverse est accessible sur **http://127.0.0.1:8088/** par le tunnel.
La signalisation **TCP 49100** reste privée. Le passage UDP public de cette
location n'a pas reçu les sondes émises depuis notre réseau ; un relais média
local, transporté par SSH, fournit le flux vidéo.
Utiliser `127.0.0.1` et le port média `47998` avec ce relais. TCP 49100 et 47999
ne sont pas publiés sur Vast. Suivre les commandes et limites du
[protocole Kit](../../../containers/picogk-station-kit/README.md).

Sur Kali2, les commandes de travail sont :

```sh
~/.local/bin/station-task status
~/.local/bin/station-task demo coupon-001 --span-mm 30 --voxel-mm 0.25
~/.local/bin/station-task status
~/.local/bin/station-task render coupon-001
~/.local/bin/station-task collect coupon-001
```

Attendre l'état `complete` avant le rendu et utiliser un nouvel identifiant
pour chaque pièce. Les résultats sont récupérés dans `~/stations/coupon-001/`.
Le 28 septembre à 21 h 36 UTC, l'utilisateur a demandé de conserver la location
après ajout de crédit. La garde de suppression a été désactivée et retirée,
sans appeler la destruction. **La station reste en marche sans coupure
automatique**, à environ **6,24 USD/h**, soit **149,69 USD/jour hors transferts**.
Le manifeste initial est conservé comme historique ; ne pas réarmer sa garde
ni appeler `reconcile-station` sur cette location en cours. La surveillance
OpenClaw contrôle les erreurs et l'avancement sans interrompre les tâches.

La synchronisation vers `~/stations/qualification-53246885/` fonctionne toutes
les 60 secondes via le service utilisateur `station-results-sync.service` de
Kali2. Chaque transfert reste limité à 180 secondes, sans suppression des
fichiers déjà collectés. Le service persiste après déconnexion SSH.

## Profil borné pour une nouvelle qualification

Les commandes ci-dessous décrivent la procédure initiale pour une nouvelle
location. Elles ne doivent pas être rejouées sur la station active dont la
coupure a été révoquée.

La qualification privée contient `image_ref` avec digest dans le namespace
`ghcr.io/cluster2600/3dprinting993-picogk-m64`, `platform: linux/amd64`,
`anonymous_registry_verified: true`, `gated_read_access_verified: true`, le
modèle et sa révision fixés dans `station_profile.py`, les tailles mesurées
`image_download_bytes` et `model_download_bytes`, et
`published_ports: ["22/tcp", "47998/udp"]`. Ces déclarations nécessitent des
vérifications réelles ; le script ne les invente pas.

```sh
python3 deploy/vast/station/prepare.py render \
  --qualification /absolute/private/qualification.json \
  --session-directory /absolute/private/session \
  --output /absolute/private/openbao-vastai-candidate
# Revoir le diff du candidat, puis l'installer sur le wrapper courant.
python3 deploy/vast/station/prepare.py manifest --offer-id 49181720
python3 deploy/vast/station/prepare.py arm /absolute/private/session/station-ID.json
openbao-vastai launch-station 49181720 /absolute/private/session/station-ID.json
openbao-vastai station-show /absolute/private/session/station-ID.json
openbao-vastai reconcile-station /absolute/private/session/station-ID.json
```

Le dossier de session doit déjà exister en mode 0700. Sa fenêtre maximale est
de six heures et son budget cumulé de 50 USD. La durée est raccourcie selon le
tarif comprenant 1 To, 500 Go entrants, 100 Go sortants et 2 USD de marge pour
le nettoyage. Chaque tentative payante réserve son coût complet, même après
échec : aucune nouvelle tentative ne récupère un montant non facturé supposé.
Le budget du manifeste couvre seulement sa tentative, arrondi au cent supérieur
et borné par le budget de session restant, tandis que le plafond cumulé reste 50 USD.

La garde LaunchAgent reste extérieure à Vast, maintient le Mac éveillé avec
`caffeinate` et détruit uniquement l'identité exacte. Elle vérifie les compteurs
réseau de toutes les interfaces sauf loopback, toutes les dix secondes quand
SSH répond ; deux téléchargements de l'image sont réservés séparément. Attendre
un reçu `<job>.network-ready.json` frais, lié au manifeste et à l'instance,
**avant** de télécharger les poids ou démarrer les services. Une perte de
métrage après activation, une régression des compteurs ou un dépassement
entraîne le nettoyage. Avant le premier relevé, le délai maximal est de 15 minutes.

La garde commence la destruction cinq minutes avant l'échéance et la vérifie
jusqu'à l'absence. Le calcul est conservateur, pas une facture Vast : une panne
du fournisseur ou des connexions peut retarder la destruction et sa facturation.
Un arrêt du conteneur ne constitue jamais une preuve de fin de facturation.

Vérification locale, sans secret ni location :
`python3 -m unittest discover -s tests -p test_station_profile.py -v`.

## Image et répartition

La recette [picogk-station.Dockerfile](../../../containers/picogk-station.Dockerfile)
réunit les images Qwen et PicoGK déjà fixées par digest, avec quatre environnements :
Qwen, `/opt/cad`, `/opt/geometry-qa` et `/opt/ovrtx-runtime`. Kit possède son runtime
autonome. Aucun socket Docker ni moteur Docker imbriqué n'est nécessaire sur Vast.

| Ressource | Usage |
|---|---|
| GPU CUDA 0–1 | Qwen, TP 2, contexte 262 144, quatre séquences |
| GPU Vulkan 2 | Éditeur Kit 110.2.0 ; confirmer l'identifiant PCI dans ses logs |
| GPU CUDA 3 | Rendus OVRTX automatisés |
| CPU et RAM | PicoGK 2.3.0 / .NET 9.0.317, FreeCAD, build123d, Gmsh, CalculiX |

Sur Kali2, depuis un checkout dédié, après acceptation des conditions NVIDIA :

```sh
docker build -f containers/picogk-station.Dockerfile \
  --build-arg NVIDIA_EULA_ACCEPTED=yes --target station -t picogk-station:raw .
mkdir -p /home/lolman/station-image-tmp
TMPDIR=/home/lolman/station-image-tmp python3 containers/picogk-station/normalize-image.py \
  picogk-station:raw picogk-station:qualified
```

Le normaliseur retire le port 8000 hérité de l'image Qwen sans modifier les
couches. Il compare l'ensemble de la configuration avant/après. Publier ensuite
le tag qualifié avec le [workflow de publication](../../../.github/workflows/picogk-station-publish.yml).
Le hook GitHub de [station_credentials.py](../../openbao/station_credentials.py)
enregistre un runner JIT sur Kali2 via l'identité OpenBao existante ; il ne
reconstruit pas l'image. L'image finale qualifiée est
`ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:6548a22795a01bf6b4a1d79a4bf9415d839ef5f445773d19d3df81bec2bef154`.
Le tag `station-20260928-persistent-4f58a4e28ab7` utilise le dépôt
PicoGK déjà public sans modifier ses anciens tags ni ses digests de base. Le job utilise son propre jeton de publication, dans
un dossier Docker temporaire supprimé à sa fin. Vérifier ensuite
anonymement le digest, sa plateforme et ses ports. Aucun poids ni secret n'entre
dans l'image. Les licences des composants restent applicables ; NVIDIA décrit
le régime courant sur sa [page de licence Omniverse](https://docs.omniverse.nvidia.com/avp/latest/common/NVIDIA_Omniverse_License_Agreement.html).
L'archive intermédiaire exige un disque avec suffisamment d'espace ; `/tmp`
sur Kali2 est un tmpfs de 7,7 Go et ne convient pas à cette exportation.

## Ordre de qualification

1. Vérifier l'accès au modèle fixé, sa taille et le digest public de l'image.
2. Actualiser l'offre, produire le manifeste, armer la garde persistante, louer.
3. Attendre le reçu réseau frais ; exécuter [preflight.py](preflight.py) par SSH.
   Il mesure les quotas CPU/RAM, l'espace disponible, Vulkan et un véritable
   encodage H.264 NVENC sur le GPU 2 avant le chargement des poids.
4. Exécuter `station-demo /workspace/jobs/qualification` comme `station-worker`.
   Les sources C# restent dans `/opt/station-repo/twins/picogk-station-demo`.
   Les fichiers USD/STL sont dérivés ; le témoin FreeCAD paramétrique conserve
   séparément son source Python, son document FCStd et son STEP.
5. Initialiser les services avec `STATION_SCENE` pointant vers une copie USD de
   travail et `station-onstart`, puis démarrer Kit avec
   `supervisorctl -c /opt/station/supervisord.conf start kit`.
6. Utiliser le hook HF `start-station` lié au manifeste. Il revalide l'instance,
   le processus de garde et le métrage avant de transmettre le token par stdin
   SSH. Le fichier runtime est accessible uniquement à root ; seul Qwen le lit.
7. Remplacer la destination du tunnel Kali2 tout en conservant
   `127.0.0.1:18000/v1`. Prouver `/health`, `/v1/models`, une réponse Qwen,
   puis un appel d'outil réel OpenClaw. `agents.defaults.maxConcurrent=4` borne
   le nombre de tours simultanés ; la file OpenClaw attend les créneaux libres.
8. Qualifier le [client WebRTC](../../../containers/picogk-station-kit/README.md), sélectionner et
   déplacer une pièce dans Kit, sauvegarder puis reconnecter. Mesurer trente
   minutes de fonctionnement simultané avec générations, requêtes et rendus.
9. Récupérer régulièrement les sorties et journaux sur Kali2 et comparer leurs
   empreintes. Dans le profil borné, la garde détruit la location à son échéance ; pour une fin
   anticipée, utiliser `reconcile-station`. Une destruction n'est confirmée
   qu'après vérification de l'absence dans l'inventaire Vast.

La machine documentaire est l'EOS M 290, laser 400 W, enveloppe nominale
250 × 250 × 325 mm, avec la carte AlSi10Mg à 30 µm déjà présente au dépôt.
Les contrôles donnent des écrans géométriques d'orientation, de parois, de
supports et de dépoudrage. Ils ne constituent ni une simulation thermique
calibrée, ni une qualification d'impression, ni une autorisation de fabrication.

La persistance OpenClaw utilise le service systemd utilisateur de Kali2 et
`loginctl enable-linger lolman`. Dans le profil borné, la garde Mac survit à la fermeture du terminal
et maintient la machine éveillée, mais nécessite que le Mac reste allumé et sa
session ouverte. La limite fournisseur est vérifiée par suppression effective,
jamais déduite d'un simple arrêt de processus.
