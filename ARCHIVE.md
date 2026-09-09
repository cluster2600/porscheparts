# Ce qui est archivé

Un dépôt qui garde tout finit par ne plus dire ce qu'il fait. Ce document sépare
ce qui est **actif** de ce qui est **conservé sans être poursuivi**, pour que la
distinction ne dépende pas de la mémoire de qui l'a écrit.

Rien ici n'est supprimé. Un travail retiré comme produit reste utile comme
régression numérique, comme cas d'essai et comme trace de ce qui n'a pas marché.

## Archivé — culasse 917 et scan 935

| dossier | fichiers | ce que c'est |
|---|---:|---|
| `twins/reference-917-engine/` | 891 | culasse 917 refroidie par air, itérations F1 à F50 |
| `twins/reference-935-cylinder-head/` | 13 | scan de culasse 935, morphologie de référence |
| `archive/917/docs/` | 112 | les dossiers écrits de ces itérations |
| `media/videos/` | 48 | deux projets de rendu, F38 et F39 |
| `containers/917-*` | ~40 | images de calcul dédiées |

**Statut.** Retiré comme produit, conservé comme régression numérique. La
géométrie rectangulaire F34 réunit CAO paramétrique, OpenFOAM/FluidX3D, CalculiX
et Cantera **sans preuve transférable à une vraie culasse**. F36 conserve la
morphologie du scan 935. F37 ajoute les STEP fonctionnels et leurs preuves
SHA-256, **impression métal et démarrage restant interdits**. L'audit Omniverse
conserve l'avertissement topologique NVIDIA comme blocage.

**Ce qu'on peut en faire** : rejouer les calculs, réutiliser les cas d'essai,
lire ce qui a été tenté. **Ce qu'on ne peut pas en faire** : une pièce.

## Pourquoi ces dossiers n'ont pas été déplacés

La question s'est posée le 2026-09-09, et la réponse est mesurée, pas
esthétique.

Le dossier 917 porte **2 014 empreintes SHA-256 enregistrées dans 275 fichiers**,
vérifiées par 139 fichiers de test. Le déplacer oblige à réécrire les chemins
qu'il contient ; or ces chemins vivent dans des fichiers qui sont eux-mêmes
hachés. L'essai a été fait : **142 tests tombent, dont 40 assertions d'empreinte
dans 31 fichiers**.

Trois issues, et aucune n'est bonne :

- déplacer sans réécrire laisse ~2 260 références mortes et le dossier n'est plus
  exécutable ;
- déplacer et recalculer les empreintes revient à refaire soi-même les preuves
  après avoir modifié les pièces — une empreinte qu'on recalcule après coup ne
  prouve plus rien ;
- ne pas déplacer laisse un rangement imparfait.

**La troisième a été retenue.** Une preuve vaut mieux qu'un dossier bien rangé.
Ce fichier existe pour que le rangement imparfait cesse d'être trompeur.

Ce qui a été déplacé, parce que c'était sans effet sur les preuves : les 112
documents 917, sortis de `docs/` où ils représentaient 60 % des fichiers.

## Ce qui peut être déplacé, et ce qui ne le peut pas

La règle vaut au-delà du dossier 917, et elle a été établie en essayant.

**Ce dépôt lie les chemins aux empreintes.** Des manifestes enregistrent un
chemin et le SHA-256 du fichier qui s'y trouve ; des verrous de conteneur
enregistrent le chemin et l'empreinte des scripts embarqués ; des contrats
enregistrent l'empreinte de leur parent. Déplacer un dossier oblige à réécrire
les chemins **à l'intérieur** de ces fichiers, ce qui change leur empreinte et
casse la chaîne.

Quatre essais, quatre mesures :

| déplacement tenté | résultat |
|---|---|
| `twins/reference-917-engine/` | 142 tests tombent, 40 assertions d'empreinte |
| `containers/` | 11 assertions d'empreinte, verrous d'image invalidés |
| `scripts/` | `parent_sha_mismatch`, contrats F34 invalidés |
| `catalog/` | les 917 y renvoient par `catalog_path` ; l'exclure du remplacement casse la résolution des sources |
| `deploy/` | conforme en apparence, **puis rattrapé** : le rapport de préparation F46 lie l'empreinte des scripts déplacés |
| `outils/benchmarks/` | **conforme**, aucun test perdu |

Seul le dernier a pu bouger, parce qu'aucun fichier haché ne le nomme.

**Le cas de `deploy/` mérite d'être lu**, parce qu'il a failli passer inaperçu.
Les tests étaient conformes après le déplacement — mais `make check` s'arrêtait
alors à la cible `test` et n'atteignait jamais les 37 cibles suivantes. C'est en
rendant la suite verte que la casse est apparue, trois cibles plus loin. Une
suite rouge ne cache pas seulement ses propres échecs : elle cache tout ce qui
vient après elle.

**La règle pratique** : un dossier n'est déplaçable que si son nom n'apparaît
dans aucun fichier dont l'empreinte est enregistrée. Sinon, le rangement se
paierait en preuves, et les preuves valent plus.

Deux pièges accompagnent tout déplacement, qu'une simple recherche de chaînes ne
voit pas : les chemins construits par segments — `ROOT / "deploy" / ...`,
`joinpath("catalog", "sources")` — et les profondeurs `parents[N]`, qui supposent
le nombre de niveaux au-dessus du fichier et désignent silencieusement le mauvais
répertoire dès qu'on le niche d'un cran.

## Actif

| dossier | ce que c'est |
|---|---|
| `twins/964-chassis/` | calcul de structure sur la caisse 964, corpus de plan d'expériences |
| `twins/993-*` | zones fonctionnelles 993 : refroidissement, support d'intercooler, planche de bord |
| `catalog/` | 381 fiches de sources, 31 fiches de pièces, mesures et schémas |
| `parts/` | géométries, plans de mesure et livrables par pièce |
| `docs/993_*_F0.md` | dossiers de conception des pièces fabriquées en fabrication additive |
| `simulation/` | cas de calcul du circuit de suralimentation |

## La règle qui vaut pour les deux

Aucune pièce de ce dépôt n'est déclarée imprimable ni validée. Les 31 fiches sont
toutes au statut `concept`, dont 17 en `prohibited_pending_engineering`. Un rendu
n'est pas une preuve, ni dans l'archive, ni dans l'actif.
