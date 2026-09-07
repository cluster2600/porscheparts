# Exécution M64 dans Omniverse : étapes séparées et traçables

Ce dossier prépare la **conversion et l'inspection du sous-assemblage 4V V2**,
pas une simulation moteur ni une autorisation de fabrication. Le
[STEP et ses contrôles géométriques](../../../docs/M64_FOUR_VALVE_DISTRIBUTION_MODULE_20260907.md)
ne contiennent pas encore le corps de culasse, le piston, les ressorts ou les
arbres. Aucun scan privé n'est transféré par ce paquet.

## État vérifié au 7 septembre 2026

- Dépendances et vrai précontrôle NVIDIA `conversion,validation` : `ready`
  sur Kali CPU ; [reçu](../../../tests/manual/m64_simready_pinned_runtime_cpu_receipt.json).
- Douze références NVIDIA : chargement de leurs CLI confirmé. Cela ne signifie
  pas que leurs opérations ou les services GPU ont été exécutés.
- L'image dérivée est publiée publiquement et associée au dépôt `porscheparts` :
  `ghcr.io/cluster2600/3dprinting993-simready-m64-runtime@sha256:a07ee46d5dbfe73193cfd0d3829c0dc3e69aed95ab82841a89c18828cea85f44`.
  La [qualification séparée](https://github.com/cluster2600/porscheparts/actions/runs/34123205685)
  s'est terminée avec succès à 13:01 UTC : `linux/amd64`, limites des couches,
  téléchargement anonyme et smoke M64 passent. Le premier workflow de
  construction a été arrêté pendant son export de cache, après publication ;
  il n'est pas cité comme une CI réussie. Le test SSH de cette qualification
  vérifie l'initialisation concurrente de `sshd`, **pas une authentification
  client**, ni l'injection des clés par Vast. Le
  [reçu de qualification](../evidence/runtime-image-qualification-20260907.json)
  conserve cette distinction et les commits de construction et de contrôle.
- Le wrapper approuvé a été installé avec le code M64 épinglé à
  `f841e5e572103acda304e62a3a7fe7dc3c0dce128defa301d2c5373fcd76c805`.
  Son contrôle local et son authentification OpenBao passent ; l'inventaire
  Vast était vide au contrôle préalable. Le code source fixe désormais le
  digest M64 qualifié dans `M64_SIMREADY_IMAGE`, séparé du digest historique
  `SIMREADY_IMAGE` de F42b. La première installation séparant ces profils
  portait le SHA256 `84c90cdc5bcaa04d43594305feb9648ddde317b4dbccd1898c5f92b0c6775ee8` ;
  la version courante est indiquée ci-dessous.
- Le [vrai test SSH isolé sur l'image M64 complète](../evidence/ssh-auth-m64-image-20260907.json)
  passe sur Kali à 13:24 UTC : connexion client/serveur, injection retardée
  d'une clé synthétique, refus de mauvaise identité, de permissions dangereuses
  et de mauvaise clé d'hôte. L'identité de l'image et l'isolation ont été
  inspectées hors du conteneur ; le conteneur de test a été supprimé.
  **Cela ne prouve pas l'ordre d'initialisation réel de Vast.**
- `make check` passe sur le lot local après régénération de l'empreinte de
  préparation F46. Cette régénération ne modifie aucun résultat de simulation.
- L'essai final a maintenant produit de vraies preuves de services GPU et de
  conversion NVIDIA, décrites ci-dessous ; aucune validation complète SimReady
  ou simulation moteur n'est acquise.
- Le [premier essai distant M64](../evidence/vast-m64-proxy-attempt-20260907.json)
  a chargé l'image et atteint l'état fournisseur `running`, mais son relais
  SSH échouait à ouvrir le port distant. Aucun paquet de calcul n'a été
  transféré. L'instance a été supprimée explicitement et son absence vérifiée
  indépendamment ; l'échec ultérieur de réconciliation du lanceur est conservé
  séparément. Le garde indique honnêtement une absence vérifiée **sans
  collecte**, et non une récupération de résultats inexistants. Le coût
  contractuel était de 1,36556 USD/h ; aucune facture finale n'est encore liée.
- Le [deuxième essai distant M64](../evidence/vast-m64-direct-attempt-20260907.json),
  instance `50165737`, a été fermé après rejet local des métadonnées d'accès
  direct, avant toute authentification SSH, transfert ou phase de travail.
  Le nettoyage automatique a confirmé cinq observations d'absence, puis un
  inventaire indépendant vide. Les mappings rejetés n'ont pas été conservés :
  leur cause précise reste **inconnue**. Des bindings multiples ou des ports
  non encore alloués sont des hypothèses, pas des faits établis pour cet essai.

La documentation [SSH de Vast](https://docs.vast.ai/guides/instances/connect/ssh)
distingue accès direct et proxy. Un point d'accès direct était annoncé pour
le premier essai, mais son wrapper conservait le proxy lorsqu'il était publié.
Le correctif M64 privilégie maintenant la paire directe exacte publiée par le
fournisseur, avec IP globale unicast et port valides ; un mapping malformé est
refusé, pas remplacé silencieusement par le proxy. Le profil historique reste
inchangé. Le même choix s'applique au précontrôle, au transfert et à la collecte.
Les bindings Docker multiples sont examinés par famille IPv4/IPv6, puis doivent
conduire à un seul port distinct ; des doublons normalisés identiques sont
admis. `HostIp` absent n'est admis que pour un binding unique après déduplication.
Un champ `22/tcp` publié mais `null` ou vide fait attendre le délai déjà fixé,
sans connexion ni repli proxy. Les erreurs produisent un diagnostic expurgé
`OPENBAO_VASTAI_M64_ENDPOINT_DIAGNOSTIC` avec types, compte, ports normalisés,
familles et provenance d'indices, jamais le dictionnaire brut du fournisseur.
Le reçu de lancement identifie l'endpoint réellement vérifié après `READY`,
sans prétendre vérifier la clé d'hôte par un canal indépendant.

Le wrapper source et installé portent désormais le SHA256
`da8023143fe7f6867d55839a6d0e1cfd2cb8845e85f4ad43761188c50261b6f9`.
Ses 175 tests wrapper/transport, les 31 tests F42b (un ignoré) et `make check`
passent. Les contrôles OpenBao et de paire de clés passent également ; aucune
instance ne restait active au contrôle précédant cette réinstallation.
Cela ne remplace pas l'authentification réelle sur une nouvelle instance.

Le [dernier essai distant](../evidence/vast-m64-gpu-attempt-20260907.json),
instance `50167152`, est **fermé après échec de Material Agent**, avec
suppression confirmée et inventaire indépendant vide. Le transfert SSH et les
phases NVIDIA `preflight`, `context`, `convert`, `minimum` ont réussi. Le
précontrôle rapporte OVRTX initialisé sur GPU et un smoke de rendu PNG réussi.
Ces preuves réelles restent distinctes du **contrat `READY` complet du lanceur,
non confirmé** ; aucune réussite de ce contrat n'est déduite des phases.

L'[USD converti](../evidence/omniverse-static-v2-20260907/converted-assembly.usd)
`04c501a3…` est récupéré et ajouté au dossier public : 12 meshes et 12 prototypes, Z-up,
`metersPerUnit=0.001`, boîte de 82,285663 × 88 × 85,888367 mm selon le contrôle
minimal NVIDIA. Cela concerne le sous-assemblage soupapes/sièges/guides, pas
une culasse complète ou un moteur validé.

Le contre-audit local parcourt les instances, leurs transformations composées
et les 6 656 points : les 12 composants nommés restent distincts, avec un
écart maximal de boîte par pièce de `1,803422e-6 mm` par rapport au STEP source.
Le premier vérificateur rejetait une référence interne USD valide ; ce
contre-audit séparé ne modifie pas l'asset. Ses empreintes figurent dans le
reçu de l'essai. Une concordance de boîtes ne prouve ni les contacts
soupapes/sièges, ni les interfaces moteur ou la résistance.

Material Agent a échoué avec `material_pipeline_failed`, étape précise
`unknown`, sans USD matériau produit. Son rapport annonce **60 aperçus pour
12 prims**, puis la préparation du dataset ; **aucune de ces images n'a été
rapatriée ni inspectée**. Ces aperçus éphémères n'ont pas été récupérés avant
la suppression de l'instance et ne sont pas des livrables certifiés. Aucune
phase Physics, conformance, validation de profil ou rendu final n'a suivi.

La collecte opérateur a récupéré **29 fichiers privés, 266 299 octets**, tous
revérifiés par taille et SHA256 ; le reçu porte `d2811fec…`. Elle reste
partielle : huit racines de sorties correspondent aux phases jamais exécutées.
Le garde conserve `absence_verified=true` mais `collection_verified=false`
avec `unexpected_absence_collection_unverified` ; son constat n'est pas
réécrit pour lui attribuer la collecte opérateur. Le superviseur confirme les
sorties du lanceur et du garde avec code **1**, et de `caffeinate` avec code
130 ; aucun processus ni instance de cet essai ne reste actif. Après la
suppression externe, le lanceur signale un rollback non vérifié et des
métadonnées SSH invalides : cette erreur est conservée, distincte des reçus
de suppression et d'inventaire vide. Le marqueur d'arrêt du garde a été créé
trop tard pour changer son constat. Les journaux bruts restent privés ; seul
l'USD converti indépendant est publié séparément.

L'allocation conservatrice était de **4 USD et 30 minutes**, du 7 septembre
2026 à 14:23:45 UTC jusqu'à 14:53:45 UTC, avec réserve de récupération. Les
allocations précédentes réservées étaient de 16 USD, soit le plafond cumulé
de 20 USD ; **ces réservations ne sont pas une facture finale**. Aucune
nouvelle relance n'est autorisée par cette note de clôture.

Limites restantes du sélecteur, constatées sur fixtures locales seulement :

- La concordance de famille d'un `HostIp` ne prouve ni sa joignabilité publique
  ni l'état du listener : un bind loopback de même famille est encore accepté
  comme métadonnée. L'adresse effectivement contactée reste l'IP publique
  validée, et l'authentification reste obligatoire.
- Si le champ `22/tcp` n'est pas publié du tout, le contrat permet toujours le
  proxy ; ce cas est distinct d'un champ publié `null` ou vide, qui attend.
- Un port JSON numérique pathologiquement grand peut lever `OverflowError`
  avant le diagnostic expurgé. Le lanceur intercepte encore cette exception
  pour son nettoyage ; cela n'autorise aucune connexion. Ce cas n'a pas été
  observé dans les essais réels et ne justifie pas d'en inventer la cause.

Le runtime historique ne correspondait pas aux versions requises par le skill
NVIDIA installé. La couche dérivée conserve les services existants et ajoute
des environnements distincts :

| Rôle | Chemin isolé |
|---|---|
| Python de validation, versions du verrou NVIDIA | `/opt/m64-simready-validate` |
| Spécifications Foundation au commit `a1e9dd6…` | `/opt/m64-simready-foundation` |
| Guide du convertisseur au commit `208fe2c…` | `/opt/m64-usd-convert-cad-guide` |
| Convertisseur natif NVIDIA 0.2.0, inchangé | `/opt/usd-convert-cad/bin/python` |

Le précontrôle a aussi révélé l'absence de `PyYAML` et un faux répertoire de
checkout du convertisseur. Les correctifs sont explicitement testés ; le
verrou du skill n'est pas modifié pour faire passer un ancien environnement.

## Préparer sans louer

`prepare_bundle.py prepare` prend un STEP, son contexte et les deux prompts,
ainsi que le dossier complet du skill installé. Il crée un nouveau dossier
privé `m64-…`, copie les références sans caches Python et calcule leurs
SHA256. Il n'ouvre aucune connexion. La présence des fixtures STL du skill
ne fait pas de ces fixtures une source du modèle de culasse.

Le contexte doit identifier exactement le SHA256 du STEP et garder
`manufacturing_authorized=false`. Le code des phases **et tous les fichiers
du skill** sont couverts par `code-manifest.json`. Son empreinte doit ensuite
être épinglée dans le wrapper approuvé, après revue et tests.

`prepare_bundle.py bind` lie ce paquet à l'identifiant réellement retourné
par une location, son label, le digest GHCR vérifié, le début du budget,
une échéance absolue et l'allocation restante. Il ne loue pas. La durée de
travail est bornée à deux heures ; le plafond utilisateur reste **20 USD
sans recharge**. Réserver aussi l'import de l'image, la collecte et la
suppression : le calcul de transfert du manifeste ne couvre que le paquet
de travail, pas le téléchargement de l'image ni une facture globale Vast.
Pour ce premier essai, réserver au maximum **8 USD**, dont jusqu'à 5 USD
de calcul et 2,25 USD d'import (45 Go à 0,05 USD/Go), puis la récupération.
Si l'API ne fournit pas l'heure de création, `created_epoch` est capturé
**avant** l'appel de location : c'est une borne conservatrice opérateur,
pas une date de création déclarée par Vast. Le chargement de l'image et
l'initialisation consomment donc le délai, sans le repousser.

## Transport approuvé

Après vérification de la CI, du digest `linux/amd64`, des clés SSH, de
l'inventaire et du coût réel :

```text
openbao-vastai launch-m64-heavy OFFER --attempt-label LABEL_UNIQUE
openbao-vastai m64-transfer INSTANCE /chemin/prive/m64-job/job-manifest.json
openbao-vastai m64-phase INSTANCE /chemin/prive/m64-job/job-manifest.json preflight
openbao-vastai m64-collect INSTANCE /chemin/prive/m64-job/job-manifest.json /nouveau/dossier/prive
```

Remplacer les valeurs descriptives par celles vérifiées, jamais par un ancien
identifiant d'instance. Lier le manifeste et armer le garde dès que le lancement
retourne l'identité vérifiée, avant le transfert. La route historique
`launch-simready-heavy` ne sélectionne pas l'image M64. Le verrou singleton
reste commun aux deux profils pour éviter une deuxième location.
Aucun appel SSH manuel ou accès direct aux secrets
n'est nécessaire. Le wrapper n'accepte pas de commande distante arbitraire.

Ordre d'exécution : `preflight`, `context`, `convert`, `minimum`, `material`,
`physics`, `profile-initial`, `render`, `conform`, `asset-validation`,
`geometry-validation`, `physics-validation`, `profile-validation`.
Chaque appel exécute une seule référence NVIDIA et produit un reçu lié au
manifeste. Le précontrôle complet exige cette fois les services Content
Agents et OVRTX GPU prêts, contrairement au seul essai CPU préparatoire.

La conformance part du premier rapport de profil, jamais d'une déclaration
de réussite anticipée. Des exigences de préhension ou d'articulation peuvent
être inadaptées à ce module : les signaler, ne pas inventer des points de
préhension ou une cinématique pour satisfaire le profil robotique.

La phase `render` est une **inspection complémentaire pré-conformance** de
l'USD produit par Physics Agent. Elle exige son reçu réussi et ses dépendances
intactes, ainsi que le rapport `profile-initial`, même échoué. Elle produit
`results/render/inspection.png` via OVRTX avant `conform`, afin de disposer
d'une image même si FET005/GSP.001 bloque ensuite la préhension robotique.
`results/render/inspection.json` enregistre les empreintes de la source, du
manifeste et du premier rapport de profil, ainsi que les avertissements.
Ce fichier décrit la portée de l'inspection ; seul le rapport NVIDIA et le
reçu commun établissent si le rendu a réussi.

Cette image **n'est pas le rendu final d'un USD conforme** et ne remplace
aucune validation. Les constats du profil restent inchangés ; un blocage de
conformance reste bloquant pour les étapes qui exigent son succès. Si une
conformance ultérieure produit un autre USD, son rendu final devra être une
étape distincte, revue et autorisée par le manifeste de code, sans réutiliser
cette image comme preuve du nouvel état.

## Échecs et collecte

- Ne pas relancer aveuglément une phase dans son dossier existant.
- Un code retour nul ne suffit pas : contrôler le rapport structuré.
- Contrôler également les empreintes du STEP, du contexte, des rapports,
  de l'environnement de précontrôle et de **toutes les dépendances USD**.
- Les références USD restent non aplaties ; dépendances externes, manquantes,
  liens symboliques et USDZ non pris en charge sont refusés.
- Une validation échouée reste échouée ; les validations diagnostiques
  suivantes peuvent continuer. Un échec de création d'asset n'est pas une
  autorisation de passer à l'étape d'auteur suivante.
- Collecter les rapports et journaux même en cas d'échec. La collecte reste
  permise après échéance ; les fichiers sont privés et leurs SHA256 vérifiés.
- Armer le [garde d'échéance](../../../deploy/vast/simready/m64-deadline-guard.py)
  après la création vérifiée. Il ne lance aucune phase. À l'échéance il tente
  la collecte puis la suppression ciblée et vérifie l'absence de l'instance.
  Prévoir la réserve de coût pendant cette récupération ; aucun garde local
  ne peut garantir l'arrêt de facturation si l'API Vast est indisponible.

L'image d'inspection de cette chaîne vient du service OVRTX sur l'USD Physics
Agent réellement produit, pas sur un hypothétique USD final conforme.
Les images CAO locales du module sont utiles mais ne constituent pas
une exécution Omniverse. Les couleurs de matériaux visuels ne fournissent ni
alliage sélectionné ni courbe de résistance à chaud. CFD/CHT, fatigue,
interférences à chaud et LPBF exigent leurs propres géométries, données,
solveurs et preuves.
