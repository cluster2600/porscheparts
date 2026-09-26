# Reprise de la culasse — 27 septembre 2026

**Reconstruction partielle à partir du scan brut 935. Les photos FVD servent de comparaison visuelle, sans transfert de cotes ni assimilation à une culasse 993.**

## Résultats sauvegardés

- **285 petites lacunes comblées**, 3620 triangles ajoutés. Tous les sommets et triangles originaux sont conservés exactement après relecture OBJ.
- Arêtes ouvertes : 99876 → 95686. Aucune nouvelle arête non-manifold. **Le maillage reste ouvert** : grands contours, frontières branchées et zones ambiguës non comblés.
- **22 profils circulaires analytiques**, parfois plusieurs sections du même perçage ; ce ne sont pas 22 perçages distincts. 198 contours fermés rejetés ; les arcs incomplets ne deviennent pas des cercles complets.
- **14 faces planes CAO découpées**, reconstruites depuis la copie réparée. STEP relu, faces valides ; ce ne sont pas un solide ni une culasse complète.

## Fichiers

- [Scan réparé, OBJ](run/fresh-v2/repaired-checked/scan-repaired.obj)
- [Faces CAO, STEP](run/fresh-v2/surfaces-repaired/planar-faces.step)
- [Profils circulaires, STEP](run/fresh-v2/recovered/circular-profiles.step)
- [Scène USD de contrôle](run/fresh-v2/repair-inspection.usda)
- [USD des surfaces CAO](run/fresh-v2/usd-surfaces-repaired/planar-faces.usd)
- [Vue générale](run/fresh-v2/repair-inspection.png) — gris : scan ; vert : profils analytiques ; orange : bouchons interpolés, parfois trop petits pour être visibles à cette échelle.
- [Détail d'une réparation](run/fresh-v2/repair-detail.png) — orange : surface ajoutée ; les lacunes voisines plus grandes restent visibles.
- [Faces CAO seules](run/fresh-v2/surface-inspection-repaired.png) — cette vue montre explicitement le caractère partiel de la reconstruction.
- [Rapport de réparation](run/fresh-v2/repaired-checked/repair.json), [profils](run/fresh-v2/recovered/profiles.json), [surfaces](run/fresh-v2/surfaces-repaired/surfaces.json).

## Contrôles géométriques et limites

L'échelle physique de l'OBJ n'est pas vérifiée. Tous les écarts ci-dessous sont en unités OBJ, **pas des millimètres certifiés**.

La réparation est limitée à des lacunes de diamètre majoré ≤ 3 unités et de défaut de planéité ≤ 0,25. Les normales doivent prolonger la surface voisine. Les ouvertures repérées sont protégées ; un fragment isolé ne reçoit pas un faux fond. Les nouvelles diagonales ne doivent pas recouvrir des arêtes existantes.

Pour les profils retenus, le plus grand P95 des écarts des points de contrôle est 0.480. Chaque cercle est aussi contrôlé par 512 échantillons vers les triangles du scan brut. Les points de contrôle proviennent du même scan, pas d'une mesure indépendante.

Pour les faces retenues, le plus grand P95 vers le **scan réparé** est 0.350, et le maximum échantillonné est 0.395. Ces résultats concernent uniquement les faces reconstruites ; ils ne mesurent pas la fidélité globale d'une culasse complète.

Les bouchons sont des surfaces interpolées, pas des observations retrouvées. Aucune validation thermique, mécanique, de fabrication ou de compatibilité 993 n'est revendiquée.

## Référence visuelle transmise

Les deux photos montrent une [FVD 99310401188BF](https://www.fvd.net/fr-ch/shop/culasse-usinee-dans-la-masse-993-gt2-evo-3-8l-double-allumage-99310401188bf~p304036), annoncée pour 993 GT2 Evo 3,8 L à double allumage. Elles aident à conserver la chambre, les emplacements des soupapes, les passages de bougies, les fixations et les espaces entre ailettes. Les soupapes, ressorts et goujons restent des éléments distincts du corps de culasse. Aucune image commerciale n'a été copiée dans le catalogue et aucune licence de réutilisation géométrique n'est présumée.

## Vérifications logicielles

Les tests ciblés couvrent le cercle contre l'arc incomplet, la conservation d'un trou dans une face, la triangulation concave, la réparation d'une lacune, la protection d'une ouverture fonctionnelle et le rejet du faux bouchon au dos d'un fragment isolé. Le contrôle USD refuse un fichier ne contenant que des transformations vides.

- Runtime CAO : 11 tests exécutés, 10 réussis et 1 test USD réservé à son runtime.
- Runtime USD : test d'assemblage et rejet d'un USD vide réussis.
- Profil VM : 2 tests locaux réussis.
- `make check` : 916 tests, 7 ignorés pour dépendances optionnelles ; étape ultérieure bloquée par le fichier préexistant absent `/tmp/kat517-993.txt`.
- USD du scan réparé et des nouvelles faces : contrôle minimum réussi ; rendus RTX générés et examinés.

Le convertisseur NVIDIA a omis la géométrie des cercles STEP isolés. Ils sont donc représentés explicitement par des courbes USD pour l'inspection ; leur STEP analytique reste livré. Le USD vide de cette tentative n'est pas présenté comme une reconstruction.

## Traçabilité

- Scan brut : `4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
- Copie réparée : `def359fcec353b1faf99409006a05a4fa870cd41f1f1dd098cc73e558c519a11`.
- STEP des faces réparées : `f9b62089384d4f169557b519d65519b099b8fff0b6cce2a431e062b19c57e728`.
- Aucun ancien repère ou modèle de culasse utilisé.
- Scripts : `recover_sections.py`, `recover_planes.py`, `repair_scan_gaps.py` dans `scripts/cad_recode/`.
- Le candidat global CAD-Recode antérieur demeure rejeté.

## Recherche documentaire complémentaire

[Recherche OpenClaw sur la culasse 935](research/SYNTHESE.md) : 24 agents exécutés, sources contrôlées et conclusions retenues séparées des rapports bruts. Aucune nouvelle cote physique validée ; la cible reste le scan 935.
