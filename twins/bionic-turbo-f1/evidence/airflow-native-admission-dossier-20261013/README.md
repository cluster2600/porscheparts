# Dossier d'admission : preuves héritées et contrôles natifs ouverts

Ce dossier relie **16 obligations** aux preuves existantes et à six membres de
l'archive officielle OpenFOAM v2406. Il ne calcule aucune géométrie nouvelle,
ne choisit aucun ratio et n'admet aucun candidat. Douze manifestes sont ancrés
au commit PR243 `ed462661ca94c843b0f8c1379d88258595f552a4`; leurs 284 entrées
sont vérifiées. Les anciens parcours ne sont pas rejoués.

## Ce qui est hérité

| Obligation | Périmètre et preuve | Limite |
|---|---|---|
| Critères constants | PR231/232 au point source, dépendances PR233 sur u=q_m : 2304 cellules, 4224 angles dont 384 MRF, 46080 paires de plans | Constante mathématique dans ce seul périmètre; aucune exécution native nouvelle |
| Critères variables nécessaires | PR238/239, 113 boîtes 1816–1928 | Aucun certificat complet d'admission; garder toutes les 153 boîtes et les deux déterminants de bord indécis |
| Partage et fermetures | PR240, enveloppe fermée des 153 boîtes | Pas une preuve de conservation après sérialisation |
| Volume signé | PR241, éventail partagé triangles/quads | Pas égalité des premiers moments ou centres natifs |
| Frontière et couverture | PR243, indice un et intérieurs disjoints de la représentation partagée | Pas classification de tous les contacts internes de dimension inférieure |

Le domaine fermé reste exactement
`[18685771944522017155/18446744073709551616,
9345323731508729405/9223372036854775808]`, u=q_m source.
Les 153 reçus de boîtes sont joints structurellement; les nombres 113 et 153
ne résultent pas de nouveaux calculs d'angles ou de volumes.

## Sources natives : écarts à qualifier

`source-audit.json` contient les chemins de membres, tailles, SHA256 et lignes
des 15 expressions citées. L'archive officielle est celle déjà épinglée par
PR236, SHA256 `8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a`.
Les membres sont conservés dans l'archive du dossier, sans modification.

- La garde de face compare la somme des normes des vecteurs triangles doubles
  à `ROOTVSMALL`. Une borne seulement strictement positive ne prouve pas qu'elle
  dépasse cette constante en exécution.
- La garde de cellule compare à `VSMALL` l'accumulation des **triples volumes**,
  avant multiplication par 1/3. Les pyramides restent signées.
- La garde du déterminant teste le nombre de faces internes/couplées et leur
  somme de normes **avant** division par ce nombre. Aucun mur non couplé ne
  doit être ajouté pour la satisfaire.
- L'orthogonalité utilise `D/(|delta|*|S|+ROOTVSMALL)`. Les termes additifs ne
  disparaissent pas simplement parce qu'aucune garde n'est déclenchée.
- La planéité native construit l'éventail autour de `fCtrs`, le centre natif
  pondéré, et compare la norme de la somme des aires à la somme des normes,
  avec terme additif. Le polynôme de coplanarité PR241 et les tétraèdres de
  preuve ne sont pas ce contrôle.
- La fermeture cellulaire native normalise les sommes signées par composante.
  L'annulation rationnelle de la chaîne ne borne pas les erreurs d'accumulation
  flottantes et ne qualifie pas un bilan de débit ou le MRF physique.
- `doubleScalar.H` donne 1e-300 et 1e-150; `scalar.H` les sélectionne sous
  `WM_DP`. Ce sont des faits de source conditionnels, pas une inspection d'un
  futur binaire. Précision de construction, `solveScalar`, binaire et reçus
  d'exécution doivent rester liés.
- `OSstream` transmet le double et sa précision au flux C++. Garder
  **writePrecision 16**; cette option seule ne prouve pas l'identité entre
  coordonnées rationnelles, texte écrit et valeurs binary64 relues. La chaîne
  entière d'entrée/sortie devra être contrôlée, sans augmenter la précision
  pour contourner la consigne.

## Contrôles natifs supplémentaires

`checkGeometry.C` appelle notamment `polyMeshTetDecomposition::checkFaceTets` :
cette décomposition native n'est pas identifiée aux tétraèdres de preuve à
moyenne arithmétique. Leurs volumes positifs ne peuvent pas lui être transférés
sans justification. Les appels de planéité 0.8, poids de face 0.05 et rapport
de volumes 0.01 sont relevés dans la source; aucun seuil n'est changé ici.
Skewness, poids, rapports, qualité tétraédrique et topologie native restent
ouverts. Ce relevé n'est pas un audit exhaustif du graphe d'appels natif.

Certains contrôles sous `allGeometry`, notamment planéité et angles concaves
de faces, produisent des ensembles signalés alors que l'incrément du compteur
de contrôles échoués est commenté dans cette source. Une future décision ne
devra donc pas se fonder seulement sur le code de sortie ou une ligne de bilan :
conserver et examiner les ensembles et avertissements selon les critères
prescrits, sans les ignorer ni assouplir les seuils.

## Lecture et portée

`build_dossier.py` construit inventaire, matrice et reçus. `verify_dossier.py`
relit indépendamment les objets Git, les membres de l'archive et les 153 reçus,
sans importer le constructeur. Il vérifie les positions des expressions et
rejoint les résultats cellulaires/angulaires hérités. C'est une vérification
**structurelle et de provenance**, pas une nouvelle reconstruction géométrique,
un prouveur automatique ou une certification d'exécution OpenFOAM.

Aucun ratio, candidat, dictionnaire, conteneur ou solveur. Les trois intervalles
synthétiques ne qualifient pas toute la couronne, les surfaces physiques,
les faces gauchies 086/091, les couches ou le repos. 084 reste incomplet et ne
sera pas relancé. Aucun débit, puissance ou calibration validé.
