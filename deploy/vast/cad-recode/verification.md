# Vérification de la préparation — 26 septembre 2026

## Session GPU réelle du 26 septembre 2026

VM Vast 52810563, RTX PRO 6000 Blackwell 96 Go, 32 vCPU, disque 500 Go,
1,924074 USD/h annoncé (transferts en supplément). Session plafonnée à trois
heures par le wrapper local ; extinction invitée programmée séparément.
Les essais conteneurs 52809699 et 52810056 ont été détruits et leur absence
vérifiée avant la VM finale.

- Brut 935 original vérifié par SHA-256, sans réemploi des anciennes géométries.
- Trois inférences GPU CAD-Recode : 7,33 / 6,14 / 5,81 s hors chargement.
  Pic mémoire PyTorch voisin de 3,34 Go. Candidat 1 rejeté : solide invalide.
  Candidats 2 et 3 exportés en STEP dans le worker Docker isolé.
- Distances p95 scan → CAO / CAO → scan : candidat 2 **27,321 / 23,414** ;
  candidat 3 **48,200 / 20,204**, en unités OBJ inconnues. Aucune acceptation
  dimensionnelle ni validation de fabrication.
- Nemotron Nano FP8 servi par vLLM 0.12.0 : appel d'outil réel réussi.
- OpenClaw 2026.9.6 connecté à Nemotron : écriture réelle du fichier demandé,
  puis lecture des rapports et rédaction d'une revue. Aucun accès Docker/shell
  fourni à l'agent ; résultats montés en lecture seule.
- Mise à jour NVIDIA automatique ayant provoqué une divergence NVML corrigée
  par rechargement du pilote invité 580.178.04, GPU inutilisé à cet instant.
- Neuf tests ciblés Python passent. `make check` exécute 912 tests, trois
  skips, puis échoue sur le PET préexistant absent `/tmp/kat517-993.txt`.
- Qwen2.5-VL-7B local répond aux requêtes image : rouge et bleu reconnus sur
  des mires 256 × 256. Une mire 64 × 64 a été décrite comme blanche ; ce test
  n'est pas une qualification de reconnaissance des détails de culasse.
- La revue OpenClaw a nécessité une correction : elle affirmait initialement
  dépasser des critères pourtant absents. La version corrigée conserve les
  quatre p95 exacts et ne prétend plus appliquer un seuil. Les sorties de
  l'agent restent des propositions soumises aux contrôles déterministes.
- OVRTX, Material et Physics sains. Scan et STEP convertis avec NVIDIA
  `usd-convert-cad` 0.2.0, minimum USD validé, composition relative rapatriée.
  Le premier rendu composé était uniforme (références non embarquées) ; le
  rendu diagnostic aplati passe, puis les rendus séparés scan/candidat passent.
- Inspection visuelle : le candidat 2 est rejeté comme reconstruction de
  culasse (ailettes, ouvertures et détails perdus au profit de blocs/cylindres).
- Fixture aluminium 20 × 40 × 60 mm : Material avait d'abord choisi du plastique.
  La consigne matière corrigée produit Aluminum_Matte. Physics écrit 0,1296 kg,
  densité 2700 kg/m³ et gravité 9,81 m/s² après normalisation d'unités.
  `check_simready_fixture.py` rejette la version plastique et accepte la
  version corrigée. Les quatre validateurs, dont Prop-Robotics-Neutral, passent
  sur la fixture finale après ajout documenté de sa ligne de préhension.
  Aucun de ces résultats n'est une validation physique de culasse.
- La mémoire réellement visible dans l'invité est de 101139 MiB, inférieure
  aux 128 Go visés. La configuration tient pour ces essais ; ce n'est pas une
  preuve de capacité pour un calcul CAE de culasse.

Preuves rapatriées hors Git : `work/cad-recode-935-fresh/vm-results/`.
Le rapport complet est `work/cad-recode-935-fresh/vm-results/RESULTATS.md`.
La réussite SimReady concerne uniquement la fixture synthétique.

## Préparation locale antérieure au déploiement

- Nouveau parcours indépendant, sans import des modules ou des résultats des
  anciennes culasses. Original 935 inchangé ; empreinte vérifiée avant analyse.
- Brut analysé : 1 281 608 sommets, 2 466 040 triangles, quatre composants connexes.
  Les unités demeurent inconnues ; la segmentation anatomique reste à revoir.
- Poids CAD-Recode v1.5 et tokenizer téléchargés par révision, empreintes locales
  conservées. Une vraie inférence CPU produit une proposition non tronquée en
  62,39 secondes. Ce temps exclut chargement et vérification des poids.
- Première proposition exécutée dans le conteneur CAD confiné ; export STEP
  réussi. Cette proposition n'est pas une géométrie acceptée.
- Fixture synthétique 20 × 40 × 60 : export isolé, réimport STEP et distances
  bidirectionnelles p95 inférieures à 1e-12 unité ; transformation inverse ×100
  vérifiée séparément, y compris avec centre non nul.
- Sept tests ciblés passent dans le venv dédié : intégrité, transformations,
  STEP, erreurs, timeout, contrat de requête et composition USD synthétique.
- CalculiX exécuté sur deux problèmes analytiques synthétiques : déplacement
  de traction 0,05 et flux thermique -1000, conformes aux valeurs attendues.
- Benchmark OpenFOAM F25 exécuté : trois maillages, deux répétitions,
  vérification du solveur réussie et ordre de convergence proche de 2.
- Image CAD Linux amd64 construite sur le Mac par émulation, avec dépendances
  verrouillées par version et empreinte. Image OpenClaw construite pour le
  contrôle local ; `openclaw config validate` réussit avec la version 2026.9.6.
- Configuration Compose, syntaxe shell et compilation Python vérifiées.

## Limites constatées avant la session VM (historique)

- Kali inaccessible lors des essais ; pas de build GPU ni d'exécution Blackwell.
- Nemotron : modèle/révision/configuration et smoke d'appel d'outil préparés,
  serveur non démarré. Aucun succès d'appel d'outil Nemotron n'est revendiqué.
- Omniverse : commandes par étape et composition USD préparées ; seuls les
  tests USD synthétiques ont été exécutés. Aucun service RTX, rendu de culasse,
  appel Material/Physics ou résultat SimReady GPU n'est revendiqué.
- La CAO générée peut être très éloignée du scan malgré son export valide.
  Aucun seuil d'écart, unité physique, matériau ou chargement réel n'est inventé.
- Le dossier neuf d'entrées physiques reste volontairement incomplet : six
  familles de données manquantes, solveurs culasse et entraînement bloqués.
- `make check` a passé sa suite de 907 tests (deux skips à cet instant), puis
  échoué sur le fichier PET préexistant absent `/tmp/kat517-993.txt`.
  Les sept tests ciblés définitifs ont ensuite été exécutés sans skip.
- Aucun achat, push, location Vast ou changement des anciens travaux.

## Preuves locales, hors Git

Dans `work/cad-recode-935-fresh/` : `intake/intake.json`,
`proposals-cpu/candidate-1.json`, `export-1/execution.json`, le STEP candidat,
`physics-readiness/readiness.json` et `runtime-verification.json`.
Les rapports CalculiX et OpenFOAM sont respectivement dans
`work/cad-recode-ccx-smoke/checks.json` et
`work/cad-recode-poiseuille-smoke/report.json`.

Les tentatives techniques échouées sont conservées séparément (dépendance SciPy
macOS puis montage Docker corrigés), sans écraser les résultats précédents.

## Qualité de la première proposition

L'évaluation native du STEP exporté depuis le code inspecté donne, sur 8192
échantillons dans chaque sens :

| Sens | Médiane | p95 | Maximum échantillonné |
|---|---:|---:|---:|
| Scan → CAO | 10,531 | 38,568 | 60,200 |
| CAO → scan | 6,186 | 29,438 | 69,397 |

Toutes ces valeurs sont en **unités OBJ inconnues**, jamais en mm vérifiés.
La proposition reste `needs_review`, `geometry_accepted=false`. Le solide valide
ne restitue pas suffisamment les détails pour être promu en définition CAO.
La suite utile est une revue de segmentation et des repères depuis le brut.

Le calcul a signalé un avertissement numérique de proximité sur le maillage
source ; toutes les statistiques finales sont finies. La tessellation candidate
utilise une déflexion de 0,01 unité OBJ et un angle de 0,1 radian. Cela ne
constitue pas une incertitude métrologique ni un seuil d'acceptation.

Le doublon de cette évaluation sous émulation Docker a été arrêté après
l'obtention du résultat natif ; son statut d'exécution reste `failed`, pas
`passed`. Le test du parcours isolé utilise une fixture synthétique séparée.
Preuve géométrique locale :
`work/cad-recode-935-fresh/evaluate-native/deviation.json`.

Le dispatcher isolé a terminé sur la fixture synthétique : STEP valide et
p95 bidirectionnels inférieurs à 1e-6 unité. Preuve :
`work/cad-recode-fixture/evaluate-1/report/deviation.json`.

## Précontrôle Vast du 26 septembre 2026

Le wrapper installé `/Users/maxime/.local/bin/openbao-vastai` passe `--check`
et `--auth-check`. `instances` retourne une liste vide. Le crédit disponible
annoncé par `account-balance` est de 46,178 USD ; aucune recharge n'a été demandée.

Blocage de déploiement : les opérations de création du wrapper installé utilisent
des images et profils conteneurs fixes (`runtype=ssh_direct`). Aucun profil VM
CAD-Recode/Nemotron ne couvre la cible Docker/NVIDIA décrite dans le README.
Les offres `cad-specialist-offers` concernent l'ancien profil conteneur et ne
prouvent pas une disponibilité VM. Le wrapper installé diffère de la copie du
dépôt : ne pas l'écraser avec cette dernière.

Aucune machine n'a été louée, aucun test GPU n'a démarré. La reprise nécessite
une VM accessible en SSH avec Docker/NVIDIA, ou un profil de lancement VM
explicitement disponible dans le wrapper OpenBao autorisé. Ne pas contourner
cette frontière en récupérant la clé API Vast directement.

### Recherche VM après autorisation d'adapter le lanceur

L'extension `deploy/openbao/cad_recode_vm_profile.py` est intégrée au lanceur
installé sous la commande `cad-recode-vm-offers`. Elle réutilise son accès
OpenBao existant, sans changer les fonctions d'authentification ni les anciens
profils. Sa portée actuelle est la recherche ; aucune opération de location
VM n'est encore implémentée ou qualifiée.

La recherche Vast renvoie **zéro offre côté fournisseur** pour les variantes
RTX PRO 6000 WS / Blackwell Max-Q / S : une carte, au moins 95 000 Mo de VRAM,
32 vCPU, 128 000 Mo de RAM, 500 Go, VM activée, hôte vérifié, fiabilité ≥ 99 %,
prix ≤ 2,50 USD/h et transferts ≤ 0,05 USD/Go. Cette observation ponctuelle ne
prouve pas une indisponibilité générale des VM Vast.

Le test `tests/test_cad_recode_vm_profile.py` valide les limites matérielles,
VM et prix. La recherche semblait alors bloquée par l'absence d'offre conforme.
Aucune instance créée et aucune dépense engagée par cette tentative.

### Correction du filtre et offre disponible

La conclusion d'indisponibilité était trop large : `gpu_frac=1` imposait
tous les GPU du serveur. Ce champ est le rapport entre GPU de l'offre et GPU
du serveur, pas une fraction de la VRAM d'une carte. Le profil accepte désormais
`0 < gpu_frac <= 1`, en conservant une carte et la VRAM complète. Le test couvre
explicitement une carte sur un serveur à deux GPU.

Offre **49400940**, Bulgarie : RTX PRO 6000 WS, 97 887 Mo VRAM, 32 vCPU,
128 713 Mo RAM, VM activée, hôte vérifié, fiabilité annoncée 99,2834 %.
Tarif pour **500 Go : 1,924074 USD/h**, stockage inclus ; transferts entrants
0,002604 USD/Go, sortants 0,003906 USD/Go. Trois heures : environ 5,77 USD
hors transferts. Relire disponibilité et prix avant location.
Preuve : `work/cad-recode-935-fresh/vast-vm-offers-corrected.json`.

La commande de recherche `cad-recode-vm-alternatives` accepte aussi L40S et
RTX 6000 Ada, au moins 48 Go nominaux, 12 vCPU, 64 Go RAM et 300 Go, avec
le même plafond horaire. Aucun lancement ni test GPU effectué.

Source : https://docs.vast.ai/cli/reference/search-instances (`gpu_frac`).

### Lancement effectif

Le profil `launch-cad-recode-vm OFFER_ID` est installé et testé hors ligne.
Il refuse les instances déjà présentes, exige 15 USD de crédit sans recharge,
relit les offres admissibles et crée un état exclusif avant location.
Le LaunchAgent local `com.3dprinting993.cad-recode-vm-expiry` appelle toutes les
60 secondes le nettoyage limité au label de cette session après trois heures.
Il dépend du Mac et de son accès OpenBao ; `shutdown -h +180` dans la VM est
une seconde limite de fonctionnement, pas une preuve de fin de facturation.

Les essais 52809699 et 52810056 avec une image KVM par digest ont abouti
à un lancement conteneur inutilisable en SSH. Ils ont été détruits et leur
absence vérifiée. Le paramètre `vm=true` seul n'a pas suffi avec cette image.
Le profil utilise maintenant le modèle VM officiellement recommandé
`fc393e1a4058a2f2b88e0c0e1a92e540`, observé avec `vm=true`. Il résout
`docker.io/vastai/kvm:cuda-12.9.1-auto` : cette image de démarrage est choisie
par Vast, les images applicatives restent épinglées séparément.
L'instance 52810563 a été créée à 1,924074 USD/h ; les journaux montrent
le démarrage libvirt/QEMU. Cela ne prouve pas encore SSH, CUDA ou la stack.

Le chemin de requête des journaux du wrapper installé a également reçu
son slash final requis par le fournisseur, corrigeant son HTTP 400.
