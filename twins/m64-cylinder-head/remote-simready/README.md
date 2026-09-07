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
  La qualification complète est encore en cours dans
  [la CI](https://github.com/cluster2600/porscheparts/actions/runs/34119750567).
  **Ce lancement n'est pas une preuve de succès de la CI.**
- Le wrapper approuvé a été installé avec le code M64 épinglé à
  `f841e5e572103acda304e62a3a7fe7dc3c0dce128defa301d2c5373fcd76c805`.
  Son contrôle local et son authentification OpenBao passent ; l'inventaire
  Vast est vide. Son image de lancement reste historique tant que la nouvelle
  CI n'est pas entièrement verte : **ne pas lancer ce module avant mise à jour
  et vérification de ce digest dans le wrapper**.
- `make check` passe sur le lot local après régénération de l'empreinte de
  préparation F46. Cette régénération ne modifie aucun résultat de simulation.
- À ce stade, aucun résultat GPU ou validation SimReady de ce module n'est
  produit par ce dossier.

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
par une location, son label, le digest GHCR vérifié, sa date de création,
une échéance absolue et l'allocation restante. Il ne loue pas. La durée de
travail est bornée à deux heures ; le plafond utilisateur reste **20 USD
sans recharge**. Réserver aussi l'import de l'image, la collecte et la
suppression : le calcul de transfert du manifeste ne couvre que le paquet
de travail, pas le téléchargement de l'image ni une facture globale Vast.

## Transport approuvé

Après vérification de la CI, du digest `linux/amd64`, des clés SSH, de
l'inventaire et du coût réel :

```text
openbao-vastai m64-transfer INSTANCE /chemin/prive/m64-job/job-manifest.json
openbao-vastai m64-phase INSTANCE /chemin/prive/m64-job/job-manifest.json preflight
openbao-vastai m64-collect INSTANCE /chemin/prive/m64-job/job-manifest.json /nouveau/dossier/prive
```

Remplacer les valeurs descriptives par celles vérifiées, jamais par un ancien
identifiant d'instance. Aucun appel SSH manuel ou accès direct aux secrets
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
