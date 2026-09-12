# Exécution des lecteurs M64 — 12 septembre 2026

## Portée

À la demande de l'utilisateur, le travail de lecture est organisé en **24 missions
indépendantes, quatre simultanées sur un seul serveur LLM Vast**. Les catégories
sont CAO/scan, CFD/thermique, matériau/huile/LPBF et vérification/mathématiques/IA.
GitHub est le dossier public de synthèse ; les corpus et réponses brutes restent
privés, sans réplication dans Obsidian.

Ces lecteurs travaillent sur des extraits fournis : ils ne naviguent pas de façon
autonome, n'exécutent aucun code proposé par une publication et ne disposent
d'aucun secret. Les propositions sont revues avant de devenir des décisions.
Une lecture, un test logiciel et une validation physique ont des statuts séparés.

## Entrées et reproduction

- [24 missions versionnées](m64-research-missions-20260912.json).
- 42 sources collectées : 28 extraits de documents/pages, cinq résumés, neuf
  notices éditeur seulement ; ce n'est pas la lecture intégrale de 42 articles.
- SHA-256 du corpus privé :
  `b98f050a44eb8ad0c74ffb94595038e0a4ca19312f5e35702dd1df52b6e53446`.
- SHA-256 du registre privé de récupération :
  `f8ab7fa9c104a58a4b7d982e39bc93f4e9013e4538c2fa8e612b57041cbdf884`.
- Chaque entrée conserve URL, URL finale, date de récupération, empreinte du
  téléchargement et du texte, niveau de lecture et limitation d'accès.
- Le répartiteur transmet au plus 8 000 caractères par source, trois sources par
  mission ; la troncature et les empreintes des extraits sont conservées.
- Pilote : `cad_01`, `cfd_01`, `am_01`, `vv_01` ; les vingt autres missions sont
  dans une file distincte pour éviter de refaire les quatre premières.

Pour l'installation, les contrôles SSH, le format du corpus et les commandes,
voir le [mode d'emploi](../../deploy/vast/research/README.md).

## Qualification avant location

Image publique `vllm/vllm-openai:v0.19.0`, manifeste `linux/amd64` vérifié :
`sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90`.
Les 27 couches compressées représentent **9 577 304 117 octets** ; aucune image
complète n'a été téléchargée sur le Mac.

Modèle public non restreint `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`, révision
`dcaee4d4dfc5ee71ad501f01f530e5652438fde0` ; tous les fichiers du dépôt représentent
**31 195 132 826 octets**. Ce n'est pas Flash Next. La recette limite le contexte
à 16 384 tokens et la concurrence à quatre ; cette configuration doit être
confirmée par une réponse réelle, pas déduite de la taille de la VRAM.

L'offre L40S finlandaise `27979081` indique un GPU 46 068 MB, 16 CPU effectifs,
128 965 MB de RAM attribuée et 100 GB de stockage demandé : **0,779630 USD/h**
stockage compris. Les champs RAM d'une réponse d'instance peuvent désigner
l'hôte entier : ne pas annoncer son téraoctet comme RAM attribuée au conteneur.

Crédit initial relu : **38,275118 USD**. Le budget visé pour l'ensemble du pilote
et des corrections de démarrage reste **4 USD**, sans recharge ; les dernières
tentatives sont chacune bornées à 2 USD incluant une réserve de nettoyage.
Les contrôles de coût ne garantissent pas une limite bancaire en cas de panne
du fournisseur ou de perte durable du poste de supervision.

## Vérification logicielle et incidents corrigés

- Le filtre `gpu_frac=1` exigeait tout le serveur : corrigé uniquement pour ce
  profil, avec un GPU complet et sa VRAM vérifiés séparément.
- Vast peut indiquer `cur_state=running` avant l'apparition des ports SSH.
  L'absence transitoire attend ; les violations déjà connues restent refusées.
- Le chargement réel de l'image dépasse deux minutes. La fenêtre de démarrage
  est désormais `min(maintenant + 900 s, échéance globale − 300 s)`, coût inclus.
- L'horloge de l'hôte est en avance de **11 480 secondes** sur le Mac : le
  lancement comparant leurs epochs expirait avant toute inférence. Après
  vérification SSH, absence de serveur existant et temps restant côté Mac,
  le serveur a été lancé avec un délai relatif de 1 800 secondes. La garde
  externe conserve son échéance Mac ; aucune horloge système n'a été modifiée.
- Le correctif versionné calcule désormais le délai sur le contrôleur, réserve
  900 secondes de démarrage, 300 de nettoyage et 60 de tolérance. Un délai
  d'inférence inférieur à 60 secondes bloque la création avant l'appel payant.
  Ce correctif n'a pas été substitué au wrapper actif pendant sa garde ; il a
  été installé après destruction et a passé le contrôle local du wrapper.
  Son chemin de lancement automatique corrigé reste testé hors ligne, pas
  présenté comme le chemin ayant exécuté cette instance.
- Un reçu de création durable enregistre l'ID avant le premier contrôle ; un
  diagnostic limité aux métadonnées permises précède tout nettoyage.
- Les instances de mise au point sont supprimées et leur absence vérifiée.
  Une offre turque encore listée a été refusée par Vast avec `no_such_ask` :
  cet appel n'a pas été rejoué.

**245 tests ciblés hors réseau passent** : 233 sur les profils Vast, dont 29
pour la recherche, et 12 sur le répartiteur. Le contrôle global `make check` rencontre une dérive du
fingerprint du rapport historique F46, car le wrapper commun a changé. Ce rapport
n'est pas régénéré pour transformer les anciens essais en nouvelles preuves.

## Résultats du pilote

L'instance de travail `50780391` a passé les contrôles d'identité, association de
clé et connexion SSH. Versions lues : vLLM 0.19.0, PyTorch 2.10.0+cu129, pilote
560.35.03 ; un calcul CUDA réel retourne le résultat attendu sur L40S. Le serveur
est configuré sur `127.0.0.1:8000` et son tunnel local sur `127.0.0.1:18000`.

**Les 24 missions ont été exécutées**, avec quatre lectures simultanées au plus.
Le [registre public des résultats](m64-research-run-summary-20260912.json)
contient leurs états, durées et empreintes, sans reproduire les textes sources.

| Lot | Requêtes | Citations conformes à ce passage | Temps de lot |
|---|---:|---:|---:|
| Pilote initial | 4 | 1 | 44,597 s |
| Reprise unique des trois refusés | 3 | 2 | 36,455 s |
| Vingt missions restantes | 20 | 15 | 130,690 s |

Après remplacement des trois premiers rapports par leur reprise, **18 missions
sur 24 passent le contrôle des citations**. Les six autres restent refusées :
`cad_02`, `cfd_01`, `cfd_04`, `cfd_06`, `am_05`, `vv_06`. Cinq contiennent un
extrait absent du texte transmis ; `am_05` cite une URL hors liste fournie
(cela ne prouve pas que cette URL est inexistante). Il n'y a pas eu de relance
automatique ni d'affaiblissement du contrôle.

La reprise a seulement renforcé la consigne de copie littérale. Les rapports
conformes ont le statut **unreviewed** : correspondance d'URL/extrait, pas
validation sémantique complète. Une relecture du pilote montre notamment :

- une conformité de composition chimique ne qualifie pas la culasse entière ;
- l'absence de preuve M64 dans un extrait ne prouve pas qu'une méthode CAO n'a
  jamais été évaluée sur aucune donnée réelle ;
- un résumé ou une notice sans résultat ne fournit aucune propriété à chaud.

Ces limites confirment l'usage comme **aide au tri documentaire**. Les décisions
restent celles du [dossier scientifique sourcé](../M64_RESEARCH_EXECUTION_20260912.md),
avec tests et inconnues explicites. Aucun rapport LLM n'a modifié automatiquement
la CAO, les cartes matériau, les charges ou les autorisations de fabrication.

Les 27 requêtes ont consommé **85 907 tokens d'entrée + 19 400 de sortie =
105 307 tokens sur le modèle Vast**. Les temps des trois lots totalisent
211,742 secondes, hors préparation, chargement et revue. Aucun taux d'économie
OpenAI n'est calculé : ce n'est pas une comparaison de coût de bout en bout à
qualité égale et la mise au point a nécessité du travail sur le contrôleur.

## Arrêt, coût et conservation

L'instance `50780391` a été **détruite**, puis son absence a été vérifiée par le
wrapper, la garde externe et un nouvel inventaire vide. Le tunnel s'est fermé.
Le modèle et son cache distant ont été supprimés avec l'instance ; les journaux
et réponses utiles ont été rapatriés avant sa disparition.

Le crédit affiché après nettoyage est **38,051516 USD**, contre 38,275118 avant :
**diminution observée de 0,223602 USD**. Ce relevé peut précéder la facture
définitive ; le tarif de l'instance était 0,779630 USD/h, stockage compris.
Aucune recharge, instance laissée allumée ou nouveau compte payant.

Une archive privée persistante conserve corpus, métadonnées, journaux,
manifestes et 27 réponses (y compris refusées), à l'extérieur des fichiers
suivis par Git. SHA-256 :
`8be8d4067eba90c166ea25d95a39407ffdcf93829260b78d78f3324f64fdac59`.
Le registre public contient l'empreinte du dernier rapport de chaque mission.
Ni textes intégraux sous droits ni réponses brutes non relues ne sont publiés.

**Bilan : lecteur GPU opérationnel et documenté ; aucun calcul de résistance,
de combustion, de refroidissement ou d'impression de culasse exécuté par ce lot.**
