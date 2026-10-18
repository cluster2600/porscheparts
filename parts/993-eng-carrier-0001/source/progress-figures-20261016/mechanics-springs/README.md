# Cas à appuis souples

Cette figure relit les champs du vrai calcul élastique
`combined-spring-1000-static`, maillage de 7 mm, du passage `run-001`.
Le solveur n’a pas été relancé. Les dix entrées, dont les cinq fichiers
de calcul et les trois sorties graphiques, sont liées par leurs SHA dans
`provenance.json` ; leurs identités ont été recoupées avec les étapes exécutées
du workflow d’origine.

Les deux vues et leurs légendes ont été inspectées. La déformée est amplifiée
×10 ; les contraintes en MPa et les couleurs de déplacement en mm restent
réelles. Les 1 000 N/mm sont la raideur totale par œillet et par axe, répartie
entre les nœuds, et non une raideur appliquée intégralement à chaque nœud.

Le pic élastique de 1 676,55 MPa et le déplacement de 18,2486 mm décrivent ce cas
de comparaison. La figure ne remplace pas une décision de résistance du matériau.
Le SVG conserve les octets Matplotlib originaux, y compris leurs espaces de fin
de ligne, afin de préserver son identité.
