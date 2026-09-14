# F41 — simulation d'impression LPBF de la culasse 917/935

## Verdict immédiat

La chaîne d'impression virtuelle est exécutée, mais la culasse n'est pas
libérée pour fabrication. F41 est un B-Rep monobloc à enveloppe extérieure
scan-conforme, sans ovalisation globale ajoutée. Les calculs établissent une
base reproductible et identifient trois blocages : épaisseur continue non
démontrée, bain de fusion borné à `3 300 K` et convergence de contrainte
insuffisante.

Une image ou une simulation numérique ne remplace pas une carte fournisseur,
des coupons à chaud, un tranchage machine, un CT ni une épreuve de première
pièce.

## Géométrie soumise au procédé

Le STEP F41 se réimporte dans OCCT comme un solide valide unique. Son enveloppe
reste celle de la reconstruction locale du scan 935 : ailettes et bossages ne
sont ni remplacés par une boîte, ni par une ellipse. Les modifications sont
fonctionnelles et internes : quatre soupapes inclinées de `18°`, deux bougies,
deux Y d'admission/échappement et une baie de distribution ouverte.

Le STEP et le STL sont verrouillés par empreinte mais restent dans `work/` :
ils dérivent du scan et ses droits de redistribution ne sont pas établis. Le
dépôt publie le générateur, les métriques et les vues, pas la géométrie source
ni ses dérivés complets.

| Contrôle | Résultat |
| --- | ---: |
| STEP | 1 solide, 1 coque, valide |
| STL de calcul | étanche, 1 composante, 262 554 triangles |
| Encombrement brut conditionnel | 119,11 × 206,09 × 82,00 mm |
| Masse AlSi10Mg conditionnelle | 2,913 kg |
| Cavités fermées, pas 2,0 / 1,25 mm | 0 / 0 mm³ |
| Orientation retenue | `scan_y_down` |
| Encombrement orienté | 119,112 × 82,000 × 206,089 mm |
| Couches à 40 µm | 5 153 |

Les galeries d'huile restent pleines dans le brut. Elles sont définies comme
perçages droits post-LPBF afin d'éviter une poche de poudre fermée et de rendre
leur étanchéité contrôlable. Les sièges, guides, filetages et portées conservent
des pilotes et des surépaisseurs d'usinage ; ils ne sont pas imprimés à leur
cote finie.

## Machine chinoise de référence

La ZRapid iSLM420DN est retenue comme machine fournisseur moderne : volume
annoncé `420 × 420 × 450 mm`, deux lasers fibre de `500 W`, couches annoncées
de `20 à 150 µm`. L'enveloppe F41 orientée tient géométriquement dans ce volume,
avant ajout de la plaque, des supports et des marges recoater.

Une étude primaire AlSi10Mg sur iSLM420DN publie le point suivant :

| Paramètre | Valeur |
| --- | ---: |
| puissance | 500 W |
| vitesse | 1 300 mm/s |
| hatch | 0,10 mm |
| couche | 0,040 mm |
| spot publié | 0,080 mm |
| plateau | 30 °C |
| densité volumique d'énergie `P/(vht)` | 96,154 J/mm³ |

La très faible porosité annoncée dans l'étude concerne ses coupons. Elle ne
qualifie ni notre lot de poudre, ni cette géométrie, ni les raccords entre les
deux lasers.

## AdditiveFOAM — bain de fusion local

OpenFOAM Foundation 14 (`7b05503f…`) et ORNL AdditiveFOAM 2.0.0
(`9c05c5eb…`) ont été compilés sur l'instance Vast. Chaque cas utilise deux
couches de `40 µm`, 16 rangs MPI, la carte thermophysique AlSi10Mg fournie par
AdditiveFOAM et le même spot de `80 µm` transformé en rayon de `40 µm`.

| Puissance | VED (J/mm³) | T P99 (K) | Bain à 870 K, L × l × p (mm) |
| ---: | ---: | ---: | ---: |
| 400 W | 76,923 | 1 284,18 | 0,7482 × 0,2329 × 0,2541 |
| 450 W | 86,538 | 1 377,24 | 0,7959 × 0,2377 × 0,2738 |
| 500 W | 96,154 | 1 457,99 | 0,8377 × 0,2443 × 0,2845 |

Les champs restent finis, les trois cas dépassent le liquidus `870 K` et le
P99 augmente strictement avec la puissance. Mais les trois maxima atteignent
la borne `Tmax = 3 300 K` du solveur. Le calcul local échoue donc volontairement
la porte `local_process_screen_passes`. La suite doit identifier si la cause
est la carte d'absorption, le profil de faisceau, la convection de gaz, la
température de plateau ou une fenêtre puissance/vitesse trop énergétique, puis
caler ces paramètres sur des coupes métallographiques de coupons.

La simulation locale ne maille pas une culasse de 206 mm à 20–40 µm : ce serait
un calcul de plusieurs milliards de cellules sans données de calibration. Elle
sert à qualifier le voisinage du bain de fusion ; les échelles supérieures sont
traitées séparément.

## Thermique macroscopique de la pièce complète

La méthode voxel active successivement la matière et résout conduction,
convection et rayonnement avec la carte AlSi10Mg dépendante de la température.
Au pas `1,5 mm`, elle donne :

- température maximale : `1 099,93 K` ;
- gradient maximal : `646 400 K/m` ;
- dose thermique maximale au-dessus du plateau : `4 797,66 K·s` ;
- déformation thermique libre maximale : `1,3479 %`.

Le maximum thermique est stable entre les pas testés, mais le gradient ne
converge pas. Le temps inter-couche est comprimé et le chemin laser n'est pas
résolu : ce résultat reste un écran comparatif, pas une prédiction de machine.

## Distorsion et résistance du brut

CalculiX applique une déformation inhérente isotrope non calibrée de `0,25 %`
sur une plaque bloquée. Au maillage le plus fin (`3 mm`) :

| Grandeur | Résultat |
| --- | ---: |
| déplacement maximal | 0,5436 mm |
| von Mises P95 | 30,83 MPa |
| von Mises P99 | 91,20 MPa |
| maximum local | 934,92 MPa |
| écart de déplacement 4 → 3 mm | 1,17 % — passe |
| écart de contrainte P95 4 → 3 mm | 22,28 % — échoue |

Le maximum local est une singularité de plaque bloquée et dépasse la portée du
modèle élastique. Les contacts de supports, leur retrait, la détente, l'HIP et
la carte mécanique à chaud ne sont pas modélisés. F41 ne possède donc pas de
valeur admissible de contrainte ni de compensation dimensionnelle libérée.

## Épaisseur et supports

Le contrôle de corde normale couvre `262 554` facettes et en résout `99,884 %`.
Il signale `9,003 %` de surface résolue sous `1,5 mm`, mais la peau tessellée
contient aussi des intersections de facettes et des coutures qui produisent des
cordes quasi nulles. Le résultat est fail-closed : il impose une carte
d'épaisseur médiale sur le B-Rep réparé, puis un nouveau maillage et un CT ; il
ne justifie pas de gonfler aveuglément toute l'enveloppe Porsche.

L'orientation choisie minimise l'écran de support parmi les orientations
testées, avec `7,35 %` de surface descendante et `11 947 mm²` de projection de
support. La géométrie réelle des supports et le fichier machine ne sont pas
générés. Cette étape appartient au fournisseur après réparation des zones
minces et calibration de sa stratégie.

## Matière

AlSi10Mg est utilisé ici parce qu'une carte AdditiveFOAM et une recette exacte
sur iSLM420DN sont publiées. Cela en fait le meilleur candidat **traçable pour
ce calcul**, pas encore le meilleur alliage de culasse. Le CP1 Al-Fe-Zr reste
une piste pour la tenue à chaud, mais aucune carte iSLM420DN ni campagne de
coupons comparable ne permet aujourd'hui une décision honnête. La sélection
finale exige conductivité, traction, LCF/HCF, fluage, dilatation, densité et CT
sur coupons XY/Z issus de la machine et du lot de poudre choisis.

## Reproduction

Après compilation d'OpenFOAM 14 et AdditiveFOAM 2.0.0 :

```sh
python twins/reference-917-engine/source/run_additivefoam_f41.py \
  --openfoam /opt/openfoam/OpenFOAM-14 \
  --additivefoam /opt/openfoam/AdditiveFOAM \
  --geometry work/917-f41-lpbf/917-head-lpbf-candidate-f41.step \
  --output work/917-f41-lpbf/additivefoam-run

python twins/reference-917-engine/source/summarize_additivefoam_f41.py \
  --run-report work/917-f41-lpbf/additivefoam-run/917-head-lpbf-additivefoam-f41-run-report.json \
  --output work/917-f41-lpbf/additivefoam-final
```

Les journaux de solveur ne sont pas versionnés, mais leurs tailles, empreintes
SHA-256, temps finaux et temps d'exécution sont enregistrés dans le rapport.

## Livrables visibles

- [géométrie et coupe](../twins/reference-917-engine/evidence/f41-lpbf-process/917-head-lpbf-candidate-f41.png) ;
- [carte AdditiveFOAM](../twins/reference-917-engine/evidence/f41-lpbf-process/917-head-lpbf-additivefoam-f41.png) ;
- [animation AdditiveFOAM](../twins/reference-917-engine/evidence/f41-lpbf-process/917-head-lpbf-additivefoam-f41.mp4) ;
- [thermique globale](../twins/reference-917-engine/evidence/f41-lpbf-process/917-head-lpbf-macro-f41.png) ;
- [distorsion CalculiX](../twins/reference-917-engine/evidence/f41-lpbf-process/917-head-lpbf-calculix-f41.png).

Références :

- [ZRapid iSLM420DN — caractéristiques machine](https://www.zero-tek.com/cn/slm420dn.html) ;
- [recette AlSi10Mg publiée sur iSLM420DN](https://www.sciencedirect.com/science/article/pii/S2352492826011013) ;
- [ORNL AdditiveFOAM — dépôt](https://github.com/ORNL/AdditiveFOAM) ;
- [ORNL AdditiveFOAM — installation](https://ornl.github.io/AdditiveFOAM/docs/installation/).
