# Défaut d'équilibre du gaz au passage entre repères MRF

## Résultat vérifié

Quatre cas natifs OpenCFD 2406 utilisent le même cube fermé de 8 000 cellules, l'air initialement à 101 325 Pa et 298,15 K, une vitesse absolue nulle, des parois physiques toutes fixes et un modèle laminaire. Aucun rotor, apport de chaleur ou écart de pression n'est imposé. La solution physique attendue reste le gaz au repos.

Chaque cas se termine avec un code nul, `Mesh OK.`, `End` et **200 pas de 0,1 µs**. Les fichiers natifs ont été relus par empreinte. Les seuils ont été définis avant calcul : écart maximal de pression 0,001 Pa, température 1e-6 K, vitesse 1e-8 m/s.

| Cas | Interface interne entre repères | Écart maximal de pression | Écart maximal de température | Vitesse maximale | Équilibre reproduit |
|---|---|---:|---:|---:|---|
| Témoin inertiel, Ω = 0 | Sélection cylindrique inactive en vitesse | 0* Pa | 0* K | 1,24e-11 m/s | Oui |
| MRF cylindrique en escalier | 800 faces non tangentes à la rotation | 42 769,45 Pa | 40,029 K | 66,857 m/s | **Non** |
| Même rotation sur tout le domaine | Aucune interface interne | 0* Pa | 0* K | 4,38e-12 m/s | Oui |
| MRF dans une tranche axiale | 800 faces exactement tangentes à la rotation | 0* Pa | 0* K | 1,14e-11 m/s | Oui |

`*` Nul à la précision d'écriture native ; ce n'est pas une assertion de zéro réel infini. Les contrôles avec rotation sur tout le domaine et interface axiale atteignent respectivement 391 et 398 fois la limite de 1 000 itérations du solveur linéaire de pression. Les champs restent dans les seuils du témoin, mais ces contrôles ne constituent pas une qualification de convergence du solveur. Les journaux sont conservés.

Les empreintes prouvent que le témoin inertiel et le cas en escalier ne diffèrent que par `MRFProperties`. Entre le cas en escalier et chacun des deux contrôles tournants, seul `topoSetDict` diffère. Les tolérances, pas de temps, propriétés, maillage et conditions physiques restent identiques.

Cela isole une défaillance de conservation de l'état de repos liée à la représentation de l'interface dans cette configuration. Ce résultat **ne prouve pas la cause unique de tous les échecs du turbo**, ni qu'un maillage de remplacement est qualifié.

## Mesure géométrique indépendante

`interface_flux_geometry_v2.py` lit les faces, propriétaires, voisins et cellules MRF. Pour chaque face interne séparant les repères, il calcule `(Ω × Cf) · Sf`. La somme des valeurs absolues est un indicateur géométrique, **pas une fuite physique à travers les parois**.

- Témoin MRF en escalier : 1,34041 m³/s de flux géométrique total absolu et composante normale maximale de 188,50 m/s.
- Interface axiale : exactement zéro sur ses 800 faces, avec 4 000 cellules dans la zone.
- Turbo référence 010, rayon 32 mm : 0,36131 m³/s sur 10 961 faces.
- Turbo référence 015, rayon 38 mm : 0,51769 m³/s sur 11 940 faces.

Déplacer simplement le rayon ne supprime donc pas ce défaut géométrique. Les valeurs proviennent des entrées natives épinglées dans les rapports `geometry-v2-*`.

## Conséquence pour les essais du turbo

La candidate 014 est rejetée : son historique contient p_min = −230 959,25 Pa et T_min = −46,98996 K à l'itération locale 267. À son dernier champ sauvegardé, itération 200, le point froid était au contact du stator, vers (29,868 ; −0,035 ; 9,583) mm. Sa localisation à 267 n'est pas connue : aucun champ complet n'y a été sauvegardé.

La référence 015 termine ses 20,0239 µs, avec 253 échantillons et des p/T positives. Au dernier pas, le débit de sortie reste −0,042196 kg/s, p_min = 6 268,92 Pa et T_min = 154,278 K. À 10 µs, son minimum de température était inférieur à celui de 010 ; l'augmentation du minimum terminal ne démontre donc aucune correction robuste. Au champ intermédiaire à 14,3292 µs, le nouveau point froid se situe à environ 38,41 mm de l'axe, près de la nouvelle interface.

L'audit MPI exige la fin native, le reçu zéro et une reconstruction terminée. Il accepte le suffixe OpenFOAM `Finalising parallel run` après `End`, tout en rejetant les erreurs natives et reconstructions incomplètes ; l'auditeur série historique reste inchangé. Le flux physique total absolu aux parois fixes vaut 3,21e-11 kg/s au champ reconstruit à 19,0154 µs. Ce contrôle ne corrige pas les interfaces internes. Aucun régime établi ou gain de performances n'est validé.

## Suite nécessaire

Avant une nouvelle série de solveurs complets, construire une interface tournante dont les faces représentent correctement une surface de révolution et vérifier l'équilibre du gaz sur cette interface. Le contrôle axial démontre l'intérêt de faces tangentes à la rotation ; déplacer la zone ou faire tourner tout le domaine ne constitue pas une recette validée pour le turbo.

Il faut ensuite préserver les interfaces géométriques et les jeux, obtenir l'admission native du maillage conforme, quantifier les couches de paroi et l'indépendance au maillage, puis comparer les variantes avec la même recette. La calibration physique et la carte débit/pression/régime restent à établir.

## Reproduction et conservation

Le préparateur est `../../cfd/static_mrf_witness.py`. Les deux contrôles complémentaires sont les scripts de ce dossier. Ils refusent un dossier de sortie existant ; leurs chemins `work/...` décrivent cette campagne. Les rapports contiennent les empreintes des entrées et sorties natives. `comparison.json` conserve les différences d'entrées et les limites du solveur linéaire.

L'archive des quatre témoins contient 140 fichiers ; SHA-256 `de916bac60c27cdf3233de5e3555e5a8c0202019a841c2a3c95e84342059e720`. Les données de 015 sont archivées séparément. Les fichiers identiques du TAR sont liés physiquement : extraire dans un dossier neuf et copier indépendamment avant modification.
