# Ce qui reste à instruire — les 70 désignations du catalogue d'usine

Réponse à une objection juste : « une seule pièce en titane sur toute la
voiture ? ». Non. Ce chiffre portait sur les fiches du dépôt, pas sur
l'automobile. Voici le balayage large, et son résultat.

## Tout le catalogue est disposé — plus une seule perte silencieuse

Les criblages publiaient ce qu'ils retenaient, et **956 désignations sur 1 026
tombaient sans motif**. C'est ainsi que `oil pipe`, puis `pulley`, puis `muffler`
se sont perdus. Chaque désignation repart désormais avec une catégorie et une
raison écrite.

| catégorie | désignations | références |
|---|---:|---:|
| visserie, étanchéité, matière souple | 394 | 3 126 |
| **instruites, avec un verdict** | **373** | **1 245** |
| domaine présumé critique | 139 | 598 |
| ni métal ni pièce à refabriquer | 70 | 539 |
| **désignation générique** — voir plus bas | **50** | **751** |
| reste à instruire | **0** | 0 |

| étage | porte sur | retient |
|---|---:|---:|
| disposition du catalogue d'usine | 1 026 désignations, 6 259 références | 373 instruites |
| verdict sur les désignations instruites | 373 | **9 méritent une fiche** |
| criblage des fiches écrites | 34 fiches | 1 éligible aujourd'hui |

Les trois ne disent pas la même chose et ne doivent jamais être cités l'un pour
l'autre. Le premier balaie la voiture. Le dernier mesure l'état du dépôt.

## Ce qui reste ouvert, et qu'il ne faut pas maquiller

**50 désignations, 751 références, sont « génériques ».** `support` couvre
142 références, `cover` 118, `lid` 69. Ce ne sont pas des pièces, ce sont des
mots : les juger à ce niveau serait un faux, parce qu'ils recouvrent des pièces
qui n'ont rien à voir entre elles.

Pour celles-là, l'unité de jugement n'est pas la désignation mais **la
référence**, et il y en a 6 259. C'est un travail d'un autre ordre, qui n'est pas
fait. Il est compté ici plutôt que masqué.

## Les sept désignations à instruire

| réf. | désignation | planche | matière présumée |
|---:|---|---|---|
| 21 | `tail pipe` | 202-00, 202-15 | acier inoxydable — **fiche ouverte** |
| 12 | `muffler` | 202-00, 202-15 | acier inoxydable |
| 5 | `hot-air manifold` | 108-10 | tôle d'acier |
| 4 | `air tube` | 108-05, 108-07 | tôle d'acier |
| 4 | `heating tube` | 202-05, 202-10, 202-20 | tôle d'acier |
| 3 | `distributor housing` | 108-05, 302-05 | tôle d'acier |
| 2 | `heat control box` | 202-20 | tôle d'acier |
| 2 | `y-piece` | 108-07, 107-14 | tôle d'acier |
| 1 | `air distributor tube` | 202-05 | tôle d'acier |

**Elles forment une seule famille.** Sept des neuf sont des pièces de tôle du
circuit d'air chaud et d'air secondaire autour des échangeurs d'échappement ;
les deux autres, l'embout et le silencieux, sont la sortie d'échappement.
Toutes partagent le même profil, et c'est ce profil qui les fait passer :

- **chaudes, mais pas à la température des gaz** — l'air chauffé par les
  échangeurs reste sous le plafond de fluage du titane, là où l'échangeur
  lui-même, à 900 °C, est un cas nickel ;
- **en tôle d'acier aujourd'hui** — le titane y gagne vraiment, en masse et en
  tenue à la corrosion de condensat, ce qu'il ne gagne jamais contre de
  l'aluminium ;
- **minces et consolidables** — tubes, collecteurs, boîtiers à volets ;
- **bénignes à la rupture** — on perd du chauffage ou une conformité
  d'émissions, pas le contrôle du véhicule.

C'est le premier gisement titane cohérent que ce dépôt ait trouvé, et il ne
ressemble pas à ce qu'on aurait deviné : ni le moteur, ni le train, ni la
carrosserie. Le chauffage.

## Pourquoi les 63 autres tombent

Les motifs sont mécaniques, dérivés et non déclarés — le script recalcule chaque
verdict et **refuse de tourner si un verdict écrit ne découle plus de ses
raisons**. C'est la garde qui manquait aux criblages précédents.

| motif | exemples |
|---|---|
| le titane n'améliore pas la matière d'origine | admission et refroidisseurs en aluminium, habillages en polymère |
| domaine présumé critique | conduites de frein, d'embrayage, de carburant, tubes d'absorption de pare-chocs |
| aucune des trois familles additives | écrans thermiques plans, supports, guides |
| impossibilité physique | radiateur d'huile et dissipateur électronique : leur fonction est de conduire la chaleur |

Le cas le plus instructif reste `heat exchanger`, meilleur score brut du triage :
il tombe sur la température. Et `oil pipe`, deuxième meilleur cas de
consolidation de la voiture, tombe sur l'incendie et sur le grippage des
raccords — instruit séparément dans
[`993_CIRCUIT_HUILE_TURBO_202-16.md`](993_CIRCUIT_HUILE_TURBO_202-16.md).

## Ce que ce document n'est pas

Un verdict `open_a_fiche` ne dit pas qu'une pièce est bonne. Il dit qu'elle
mérite une fiche, et que la fiche tranchera — avec des mesures, une matière
identifiée et un cas de charge. Tout ce qui précède est déduit d'une désignation
de trois mots et de sa planche.

Huit fiches à écrire, donc. C'est le prochain chantier, et il est borné.

Le silencieux mérite une mention : il n'était pas dans les 70 du triage lexical,
parce que le mot `muffler` ne contenait aucun terme de mon vocabulaire. Il a
fallu la disposition complète pour le voir. C'est pourtant, avec l'embout, le
meilleur candidat titane de la voiture — chambres internes, aval du moteur,
rupture bénigne, et un produit de série chez les équipementiers.

## Reproduction

```bash
make pet-part-triage PET_LISTING=<chemin>/oem-listed.json
make pet-disposition PET_LISTING=<chemin>/oem-listed.json
make pet-verdict
make pet-verdict-check
make pet-explain PET_LISTING=<chemin>/oem-listed.json REF="993 105 011 05"
```
