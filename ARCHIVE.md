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
