# Scan de culasse billet Wolfe Classics pour Porsche 935

## Statut

- Niveau actuel : `F0_reference`.
- Acquisition : OBJ acheté et téléchargé le 31 août 2026.
- Usage : référence géométrique locale pour rétroconception et préparation de
  simulations.
- Compatibilité 993 : non démontrée.
- Publication du maillage brut : bloquée tant que le droit de redistribution
  n'est pas documenté explicitement.

Le vendeur présente la culasse comme conçue spécifiquement pour une Porsche 935
de compétition et comme potentiellement adaptable à d'autres 911 des années
1970 ou 1980. Cette description ne couvre pas la 993 et ne remplace pas une
comparaison des interfaces.

## Actif local

Le fichier original reste hors Git conformément à la politique du dépôt :

```text
raw-scans/wolfe-classics-935-cylinder-head/original/935-xtreme-cylinder-head.obj
```

Empreinte de contrôle :

```text
SHA-256 4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486
```

Cette empreinte doit rester identique pour toute analyse du fichier source. Une
copie nettoyée, recalée ou simplifiée doit recevoir une nouvelle empreinte et ne
doit jamais remplacer l'original.

## Inspection initiale

| Propriété | Résultat |
|---|---:|
| Sommets | 1 281 608 |
| Triangles | 2 466 040 |
| Enveloppe X | 197,899 unités OBJ |
| Enveloppe Y | 198,796 unités OBJ |
| Enveloppe Z | 227,098 unités OBJ |
| Arêtes uniques | 3 748 998 |
| Arêtes ouvertes | 99 876 |
| Arêtes non-manifold | 0 |
| Faces dupliquées | 0 |
| Triangles de surface nulle | 8 |
| Groupes, matériaux, normales, UV | absents |

Les dimensions sont cohérentes avec des millimètres, mais le format OBJ ne
déclare aucune unité. Le maillage n'est pas étanche ; son volume signé ne doit
donc pas être interprété comme une mesure de volume ou de masse.

## Valeur pour le jumeau

Le scan apporte une enveloppe détaillée des ailettes, des bossages, des
ouvertures et des goujons visibles. Il peut servir à :

1. repérer les interfaces à mesurer sur une culasse réelle ;
2. construire des plans de coupe et des enveloppes de collision ;
3. préparer la segmentation admission, échappement et chambre ;
4. comparer des architectures de conduits ;
5. produire un solide paramétrique indépendant après contrôle des cotes.

Il ne permet pas encore de calcul CFD fiable. Une simulation de flux exige des
surfaces internes complètes, un domaine fluide fermé, des conditions aux limites
et une géométrie représentative de la culasse étudiée. Les trous du maillage ne
doivent pas être rebouchés automatiquement sans distinguer une ouverture
fonctionnelle d'un défaut de scan.

## Conditions de passage au niveau suivant

Pour atteindre `F1_envelope` :

- confirmer l'unité au moyen d'au moins une cote physique connue ;
- définir un repère et une orientation stables ;
- séparer les goujons et éléments rapportés de la culasse ;
- produire un proxy allégé sans déplacer les interfaces visibles ;
- documenter l'incertitude ou une carte d'écart du scan.

Pour étudier une interface avec une 993 :

- mesurer l'alésage et la chambre ;
- mesurer le motif, le diamètre et la hauteur utile des goujons ;
- mesurer les plans de joint et entraxes admission/échappement ;
- caractériser les conduits, sièges, guides et angles de soupapes ;
- identifier la matière et la masse de la culasse ;
- comparer ces valeurs à une culasse 993 de variante moteur connue.

Tant que ces contrôles manquent, le scan reste une référence 935 et ne rejoint
pas le graphe actif des composants 993.

## Provenance

- [Page produit Wolfe Classics](https://www.wolfeclassics.com/shop/p/p-car-billet-cylinder-head-scan)
- Fiche structurée :
  `catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json`
