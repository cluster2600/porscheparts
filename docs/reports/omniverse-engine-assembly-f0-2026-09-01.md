# Rapport Omniverse moteur F0 — 2026-09-01

## Résultat

Trois scènes OpenUSD ont été générées sans publier les scans sources :

- `917-engine-assembly-f0.usda` : référence extérieure du moteur 917 ;
- `993-935-valvetrain-test-rig-f0.usda` : culasse 935 de comparaison et trois
  soupapes paramétriques 993 ;
- `engine-research-overview-f0.usda` : vue côte à côte des deux recherches,
  sans prétendre qu'elles constituent le même moteur.

Le contrat de composition a réussi avec une unité de 0,001 m, un axe Z vertical
et aucun corps rigide ajouté sans revue. Le banc contient quatre maillages
chargés, dont trois prototypes de soupapes ; la vue d'ensemble en contient cinq.
Les soupapes exposent des levées de 0, 2, 5 et 10 mm. L'admission sélectionne
par défaut l'étude Ti-6Al-4V et les deux échappements l'étude INCONEL 751.

Ce résultat est une composition de recherche F0, pas une conformité SimReady,
une preuve d'ajustement, ni un modèle mécanique ou thermique validé.

## Preuves de rendu OVRTX

Le rendu a été exécuté sur une NVIDIA L40S avec l'image :

`ghcr.io/cluster2600/3dprinting993-simready@sha256:3947ea34d5101065c97103cc2176f395cb9753cb1d7807acb3cfd095796a4e1a`

Le premier essai a révélé que Pillow manquait dans l'environnement de
validation : le PNG noir n'était donc pas détecté. Un second essai avec
inspection de pixels et lumières de diagnostic a prouvé que les références USD
n'étaient pas embarquées dans le paquet du renderer. Les scènes sources sont
restées composées ; seules leurs copies temporaires de rendu ont été aplaties.

Les rendus finaux ont réussi `--fail-on-uniform` :

| Preuve locale hors Git | Taille | Triangles inspectés | Couleurs réduites | SHA-256 |
|---|---:|---:|---:|---|
| `valvetrain-rig-final.png` | 1024 × 1024 | 2 466 032 | 117 | `9960952fa086a88a381fc86948324f93560c4016b2cec9b0eb37b9395485539c` |
| `engine-overview-final.png` | 1280 × 720 | 4 931 909 | 64 | `a0b629f75815c7a4bf1e002a0a6eb31f7dd35aeab06f96665b89fc2dc812c4ef` |

Les images, USD dérivés et scans restent sous `work/`, hors Git. Les rapports,
empreintes, configurations et scripts permettent de rejouer et d'auditer le
travail sans redistribuer les actifs tiers.

## Validation et limites

- La validation minimale OpenUSD a réussi sur les trois scènes.
- Le validateur de composition du dépôt a réussi sur les variantes, instances,
  unités, axes, maillages et absence de corps rigides.
- Les validateurs NVIDIA génériques `asset` et `geometry` ont dépassé 120 s sous
  émulation amd64 sur macOS ; ce timeout n'est pas déclaré comme un succès.
- Material Agent et Physics Agent n'ont pas été utilisés : aucune attribution
  physique n'est justifiée à ce stade et l'accès NIM contrôlé avait refusé
  l'authentification.
- PhysicsNeMo n'a pas été lancé. Il nécessite d'abord une segmentation propre,
  des interfaces mesurées, des lois matériau dépendantes de la température et
  des cas de charge vérifiables.

## Infrastructure

L'instance Vast.ai `49498499` a été détruite après récupération et contrôle des
preuves ; la liste des instances était vide. La correction du conteneur ajoute
Pillow à l'environnement de validation et rend son import obligatoire dans le
smoke test, afin qu'un futur rendu uniforme bloque la chaîne.
