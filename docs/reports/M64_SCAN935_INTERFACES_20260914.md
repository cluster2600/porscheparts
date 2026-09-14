# M64 — interfaces mesurées sur le scan de culasse 935 (niveau C)

14 septembre 2026. Source : scan OBJ Wolfe Classics d'une **culasse billet 935**
([fiche](../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json)),
SHA-256 `4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`, vérifié
avant lecture. Ce n'est **pas** une M64. Toutes les valeurs ont le statut
`measured_on_935_scan_evidence_C` et entrent au
[contrat](../../twins/m64-cylinder-head/interface-contract.json) comme faits
candidats, jamais comme valeurs nominales M64.

Le brut et tous les dérivés géométriques (maillages, coupes, rendus) restent
locaux, hors Git, conformément à l'instruction du propriétaire. Le dépôt ne
contient que des nombres, des méthodes et des scripts :

- [`measure_interfaces.py`](../../twins/m64-cylinder-head/source/scan935/measure_interfaces.py) (chemin du scan en argument) ;
- [`fit_primitives.py`](../../twins/m64-cylinder-head/source/scan935/fit_primitives.py) (plan, cercle, cylindre ; numpy seul) ;
- [résultats JSON](../../twins/m64-cylinder-head/evidence/scan935-interfaces-20260914.json) ;
- [tests synthétiques](../../tests/test_m64_scan935_fit_primitives.py).

## Méthode

1. Lecture de l'OBJ, contrôle d'empreinte, normales aux sommets. Repère provisoire
   A/B/C repris de `twins/reference-935-cylinder-head/source/scan_frame.py`.
2. Plan d'étanchéité : RANSAC (seuil 0,15 ; hypothèses à moins de 5° de C), puis
   moindres carrés sur les inliers de la couronne plane extérieure.
3. **Repère culasse** : z = normale du plan d'étanchéité, orientée vers le
   cylindre (matière de culasse en z < 0) ; origine = axe du cercle de centrage
   sur ce plan ; x = A projeté ; y = z × x.
4. Cercles : RANSAC puis Gauss-Newton géométrique. Cylindres : RANSAC sur
   sous-échantillons, puis Gauss-Newton (axe, point, rayon) sur les sommets dont
   la normale est perpendiculaire à l'axe. Un axe inconnu est initialisé par la
   plus petite direction propre des normales locales.
5. Incertitude k = 1 : √(σ bootstrap² + (étendue de sensibilité / 2)²). La
   sensibilité est évaluée sur 3 fenêtres, seuils ou boules. Elle **exclut**
   l'échelle OBJ et l'erreur propre du scanner.

Les graines de région (où chercher) sont écrites dans le JSON. Elles viennent
d'une exploration par coupes, conservée seulement en local.

## Échelle

| Contrôle | Scan (u) | Référence documentée | Rapport |
|---|---:|---|---:|
| Arête intérieure du fond de lamage | 94,28 ± 0,09 | alésage 95 (bas de la plage Swindon 95–102,7) | 0,992 |
| Même arête | 94,28 | alésage M64 100 (P3) | 0,943 |
| Lèvre de chambre | 91,19 ± 0,21 | 95 | 0,960 |
| Alésage Ø13 au fond des logements de soupape | 13,15 / 13,09 (± 0,4 / 0,2) | logement de guide 993 2V 13,000–13,018 (WM993 p.154) | ≈ 1,01 |

**Conclusion : les unités OBJ sont cohérentes avec des millimètres, à quelques
pour cent près.** Elles restent **non étalonnées** : aucune cote physique connue
de cette pièce ne permet de fixer le facteur. Les recoupements portent sur
d'autres moteurs (M64, 993 2V, plage Swindon). Le dépôt ne contient aucune
source d'alésage 930/935 ; la valeur de 95 vient seulement de la plage Swindon.
Le Ø94,3 est donc compatible avec un alésage d'environ 95, et moins avec 100.
Cela concorde avec une culasse 935, pas M64.

## Tableau des mesures (unités OBJ ≈ mm)

| Interface | Grandeur | Valeur | u (k=1) | Qualité / région |
|---|---|---:|---:|---|
| Plan d'étanchéité | planéité apparente RMS / p95 / crête-creux | 0,047 / 0,105 / 0,30 | normale ± 0,19° | 25 120 inliers (85 %), couronne r 58,5–75 ; décalage entre 4 secteurs ≤ 0,005 |
| Centrage cylindre | Ø paroi de centrage | 113,42 | 0,02 | 3 066 pts, couverture 360°, p95 0,13 |
| | profondeur (plan → fond de lamage) | 2,21 | 0,02 | fond parallèle à 0,04° ; 11 288 pts |
| | Ø arête intérieure du fond | 94,28 | 0,09 | 1 097 pts, p95 0,19 |
| | Ø lèvre de chambre (z −2,7 à −5) | 91,19 | 0,21 | inliers 24 % : bande mêlée au congé |
| | inclinaison de l'axe du centrage | 5,9° | non fiable | paroi haute de 1,2 u, angle non contraint ; **ne pas utiliser** |
| Goujons de culasse | nombre | 4 | — | trous fermés ; aucun autre sur l'emprise |
| | positions (x, y) au plan | (−43,38 ; 42,87) (43,16 ; 42,99) (43,20 ; −42,77) (−42,87 ; −42,84) | 0,06–0,08 | cylindres de 1 800 à 2 200 pts, p95 ≤ 0,23 |
| | entraxes côtés / diagonales | 85,71 · 85,75 · 86,07 · 86,54 / 121,52 · 121,78 | 0,1 | centroïde du motif à 0,07 de l'axe du centrage |
| | Ø trous | 10,47 · 10,56 · 10,71 · 10,88 | ≤ 0,02 | axes à 0,5–1,3° de la normale |
| Bougies (double allumage) | nombre | 2 | — | symétriques en x (±20,3 au plan) |
| | Ø alésage lisse apparent | 11,23 · 11,37 | 0,07 · 0,01 | filetage non résolu |
| | angle axe / plan d'étanchéité | 61,7 · 60,3° | 3,7 · 0,1° | la bougie 1 est sensible à la taille de boule |
| Soupapes | nombre d'axes | 2 (culasse 2 soupapes) | — | côté B haut = 1, côté B bas = 2 |
| | angle à la normale | 26,6 · 29,2° | 1,0 · 1,4° | axe de l'alésage comparé à la droite des centres de 21–22 cercles |
| | angle inclus | 55,7° | 1,4° | |
| | entraxe des axes au plan | 33,0 | 1,0 | extrapolation d'environ 85 u |
| | Ø alésage de poussoir / ressort | 39,26 · 39,15 | 0,14 · 0,03 | 5 800–7 100 pts, p95 0,24 |
| | Ø gorge apparente (z −25 à −5) | 45,8 · 38,8 (plateau 45,7 · 38,3) | 1,0 · 2,1 | médiane de 10–11 tranches ; l'incertitude inclut le chanfrein de sortie |
| | Ø13 au fond du logement | 13,15 · 13,09 | 0,4 · 0,2 | 2 à 4 tranches ; guide ou bossage, non tranché |
| Bride B basse (Ø40) | plan | normale à 89,47° de z | 0,2° | 15 590 pts, RMS 0,057 |
| | Ø conduit à 6 u sous la face | 39,99 | 0,5 | couverture 360° |
| | fixations | 4 (2 goujons Ø7,04/7,68 et 2 trous Ø7,06/6,92) | Ø ± 0,01 | carré 46,2–46,9 ; diagonales 65,8 / 66,1 (± 0,3) |
| Bride B haute | plan | normale à 89,35° de z | 0,2° | 12 026 pts, RMS 0,049 |
| | fixations | 2 goujons Ø6,34 / 6,75 visibles | — | entraxe 66,13 ± 0,3 ; les deux autres positions n'apparaissent pas |
| | contour de conduit | **non mesurable** | — | contour non circulaire ou ouvert |
| Porte-arbre | face d'appui : hauteur au plan d'étanchéité | 86,46 | 0,1 | parallélisme 0,59° ; 25 848 pts, RMS 0,042 |
| | trous de fixation fermés | 7 (Ø7,0 à 8,3) | 0,3 | liste non exhaustive, positions dans le JSON |

Le côté admission ou échappement n'est pas attribué : le scan ne l'indique pas.
Le côté 1 porte la plus grande gorge (≈ 45,7) et le côté 2 la bride carrée à 4
fixations avec un conduit Ø40.

## Non mesurable sur ce scan

- **Axes d'arbres à cames** : la culasse ne porte pas de palier. Les arbres
  sont dans un carter séparé, absent du scan. Seules la face d'appui et ses
  trous sont mesurés.
- **Passages d'huile** (alimentation et retour) : aucun passage identifiable
  sans ambiguïté ; surfaces internes ouvertes, pas de coupe ni de tomographie.
- **Sièges** : portée, angle, largeur et logement de bague ne se séparent pas
  sur une surface ouverte, sans soupape.
- **Filetages** (bougie, goujons) : non résolus. Les diamètres sont des alésages
  lisses apparents.
- **Joint** : la gorge de joint documentée est côté cylindre (T1), donc hors de
  cette pièce.
- **Planéité métrologique** : la valeur p95 de 0,105 inclut le bruit du scan.

## Comparaison aux références M64 et écarts

| Grandeur | Scan 935 | Référence | Écart / lecture |
|---|---:|---|---|
| Alésage (arête du lamage) | 94,3 | M64 100 (P3) ; Swindon 95–102,7 | −5,7 % par rapport à 100 : non transférable à une M64 |
| Centrage | 113,4 | aucune cote M64 | la surface de 145 (T1) est une cote de réparation, pas un centrage |
| Goujons | 4, carré de 86 | M64 : désignations BM 8×20 / 8×50 (P1), sans coordonnées | trous Ø10,5–10,9 ; motif non comparable faute de référence |
| Soupapes | 2 par cylindre, Ø gorge 45,7 / 38,3 | Swindon 4V : 40 / 33 ; 993 2V : têtes 49 / 42,5 | architecture 2 soupapes, comme la 993 de série ; ni axes ni angles M64 documentés |
| Logement Ø13 | 13,1 | logement de guide 993 : 13,000–13,018 | cohérent à environ 1 %, à confirmer (feature non identifiée) |
| Bougie | 2 par cylindre, Ø11,2–11,4, environ 61° au plan | M64 : M14 × 1,25 (M1), une bougie | Ø lisse inférieur au mineur M14 (≈ 12,6) : taraudage réel non déterminé |

## Reste à mesurer sur une vraie culasse M64

Les mesures du tableau du [rapport G0](M64_G0_INTERFACE_CONTRACT_20260914.md)
restent entièrement requises (MMT, 20 °C, référentiel A/B/C). Le scan 935
permet seulement de préparer la gamme :

1. Ø et profondeur du centrage, axe par rapport au plan A (le scan donne un
   ordre de grandeur de 113 × 2,2 pour une 935).
2. Positions et diamètres des goujons, et entraxes entre cylindres (le scan ne
   couvre qu'un cylindre).
3. Axes, angles et entraxe des soupapes ; logements de siège et de guide
   (serrages).
4. Axe, angle et profondeur de la bougie M14 × 1,25.
5. Plans de brides, motif des goujons et contour des conduits à la face.
6. Plan d'appui du porte-arbre, trous M8 et axe de palier (sur le carter).
7. Passages d'huile (endoscope ou tomographie).

Reproduction : `python twins/m64-cylinder-head/source/scan935/measure_interfaces.py
<chemin local du scan> --output <json>` (Python 3.12.3, numpy 2.2.6 ;
graine RANSAC 935).
