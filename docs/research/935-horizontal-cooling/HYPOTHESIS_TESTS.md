# Essais sous hypothèses — système horizontal 935

Campagne exécutée le 7 octobre 2026 sur Kali2/ext4, sans Vast. Elle complète
les [27 scénarios cinématiques initiaux](HYPOTHESES.md) par **160 scénarios
du système réduit** et **neuf calculs CalculiX** sur un anneau idéal.
Les six groupes du [calculateur existant](../../../twins/935-horizontal-cooling-system-f0/source/build_system_twin.py)
sont exécutés : régimes, cinématique, inertie/balourd, réseau d'air, budget
de transmission et thermique. Aucun scan, ancienne géométrie proxy ni
interface de montage supposée n'est utilisé comme géométrie de référence.

## Paramètres choisis et moyens de les remplacer

Tous les paramètres physiques suivants sont des hypothèses de campagne.
Les incertitudes nulles décrivent des points fixés, pas une précision mesurée.

| Domaine | Hypothèses | Confrontation nécessaire |
|---|---|---|
| Rotor réduit | Anneau Ø 275 mm, alésage Ø 40 mm, épaisseur 4 mm ; neuf masses de pales équivalentes à 6 cm³ chacune, au rayon de 100 mm. | Volume et inertie de la reconstruction calibrée ; masse et équilibrage mesurés. Les masses ponctuelles ignorent l'inertie propre des pales. |
| Régimes | 3 000, 6 000, 8 500, 11 000 tr/min ; rapport total 1 et glissement nul. | Régimes simultanés moteur/rotor. 11 000 tr/min est un point d'exploration, pas un régime autorisé. |
| Freinage | Décélération constante jusqu'à zéro en 0,1 ou 1 seconde. | Trace tachymétrique, inerties de toute la transmission, comportement du coupleur et de la courroie. |
| Transmission | Rendement stationnaire 95 %, rayon primitif de poulie 50 mm, diamètre primitif d'engrenage 40 mm, arbre plein Ø 16 mm. | Mesures du mécanisme démonté et définition des dentures, arbres, appuis et pertes. |
| Air | Courbe choisie à 6 000 tr/min : `(Q,Δp,η)` = `(0,1200,0.4)`, `(0.6,1050,0.65)`, `(1.2,650,0.55)`, `(1.8,0,0.2)` ; unités m³/s, Pa, 1, décimales avec point. | Courbes CFD acceptées puis banc, aux mêmes stations de pression totale. Aucune courbe Porsche n'est revendiquée. |
| Réseau | Six branches égales de 15 000 Pa·s²/m⁶, une fuite de 50 000, résistance commune de 100 ; deux multiplicateurs globaux : 0,5 et 2. | Géométrie des passages et mesures de pertes. Les six branches sont des zones fictives, pas les six cylindres identifiés. |
| Thermique | Air : 1,15 kg/m³, 1 005 J/(kg·K), entrée à 25 °C. Chaque zone : 3 kW, UA = 150 W/K, capacité 8 kJ/K, initialement 100 °C ; pas de 60 s. | Charges moteur, résistances thermiques et mesures de température. Aucun échange avec l'huile ni gradient dans le rotor n'est simulé. |

Les cartes existantes couvrent AlSi10Mg, AlF357, Ti‑6Al‑4V, WE43, 316L,
17‑4PH, IN718, CoCr MP1, M300 et CuCrZr. Densité et module sont repris
comme valeurs de comparaison, avec leurs sources et empreintes dans les
sorties. L'isotropie et ν = 0,33 sont supposées pour tous les métaux.
**Aucune limite élastique, marge de sécurité, durée de fatigue ou vitesse
admissible n'est calculée.** Les données WE43 restent des substituts non
qualifiés pour la pièce imprimée. La [fiche EOS Ti64](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-titanium-ti64)
montre pourquoi machine, orientation et traitement doivent accompagner une
propriété matière ; les cartes ne constituent pas un dossier de production.

## Vérification centrifuge indépendante

Le témoin est **uniquement l'anneau**, sans les neuf masses de pales. Ses
bords radiaux sont libres. La demi-épaisseur est modélisée en CAX8, avec
symétrie axiale au plan médian, et trois maillages de 16, 32, 64 éléments
radiaux, chacun avec deux éléments dans la demi-épaisseur. Les neuf calculs
sont des résolutions fraîches pour AlSi10Mg, WE43 et Ti64 à 8 500 tr/min.

Les conventions CAX8 (`x` radial, `y` axial) et la charge `CENTRIF = ω²`
suivent la documentation de l'auteur de CalculiX, [éléments axisymétriques](https://web.mit.edu/calculix_v2.7/CalculiX/ccx_2.7/doc/ccx/node51.html)
et [charge centrifuge](https://web.mit.edu/calculix_v2.7/CalculiX/ccx_2.7/doc/ccx/node148.html).
Le jeu de calcul utilise mm, N, s, tonne ; les calculs système utilisent SI.
La densité en g/cm³ est multipliée par 10⁻⁹ pour le jeu CalculiX.

La solution plane à épaisseur constante vérifie :

\[
\sigma_r=\frac{3+\nu}{8}\rho\omega^2
\left(a^2+b^2-r^2-\frac{a^2b^2}{r^2}\right),\qquad
\sigma_\theta=\frac{3+\nu}{8}\rho\omega^2
\left(a^2+b^2+\frac{a^2b^2}{r^2}-\frac{1+3\nu}{3+\nu}r^2\right).
\]

Le contrôle logiciel indépendant vérifie les tractions radiales nulles aux
deux bords et l'équilibre `dσr/dr + (σr−σθ)/r + ρω²r = 0`.
La [méthode NASA pour les disques tournants](https://ntrs.nasa.gov/api/citations/19960021252/downloads/19960021252.pdf)
documente cet équilibre et les hypothèses de contraintes planes ; elle
distingue les charges du disque, celles des pales et les effets thermiques.
Ces derniers sont exclus de notre témoin.

| Matière hypothétique | Pic analytique de von Mises de l'anneau | CalculiX, maillage fin | Déplacement radial analytique maximal |
|---|---:|---:|---:|
| WE43 | 22,92 MPa | 22,56 MPa | 0,01608 mm |
| AlSi10Mg | 33,44 MPa | 32,92 MPa | 0,01478 mm |
| Ti64 | 55,10 MPa | 54,25 MPa | 0,01550 mm |

L'écart final de contrainte est 1,54 % ; la variation entre les deux
maillages fins est 1,55 %. L'écart de déplacement est inférieur à 0,004 %.
Les seuils du témoin sont : écart analytique inférieur à 2 % en contrainte
et 1 % en déplacement, variation des deux maillages fins inférieure à 5 %.
Les trois matières satisfont ces critères. Le premier essai 8/16/32 éléments
atteignait encore 3,04 % d'écart de pic ; il est conservé séparément et a
motivé le raffinement. Le pic aux points d'intégration converge vers le
pic du bord libre ; aucune extrapolation nodale de contrainte n'est utilisée.
Cette vérification ne qualifie pas les pieds de pales ou le montage du rotor.

## Charges de transmission : premier résultat utile

À 8 500 tr/min, avec le réseau à multiplicateur 2 et un arrêt en 0,1 s :

| Matière du rotor réduit | Masse supposée | Énergie de rotation | Couple inertiel de freinage, valeur absolue | Enveloppe de couple incluant la charge d'air |
|---|---:|---:|---:|---:|
| WE43 | 0,524 kg | 2,02 kJ | 45,36 N·m | 49,56 N·m |
| AlSi10Mg | 0,765 kg | 2,95 kJ | 66,19 N·m | 70,38 N·m |
| Ti64 | 1,261 kg | 4,85 kJ | 109,07 N·m | 113,26 N·m |

Le couple inertiel est divisé par dix lorsque l'arrêt prend une seconde.
L'enveloppe est la **somme des valeurs absolues** inertielle et aérodynamique ;
ce n'est pas leur somme signée lors du freinage. Elle sert à préparer les
cas de charge, sans simuler l'élasticité, le jeu ou les chocs du mécanisme.
Pour le scénario AlSi10Mg, elle donne 3,52 kN de force tangentielle sur
l'engrenage supposé Ø 40 mm et 87,51 MPa de cisaillement en torsion sur
l'arbre plein supposé Ø 16 mm. Aucun matériau ni admissible d'arbre n'est
attribué. Le couple stationnaire du rotor dans ce même scénario est 4,19 N·m.
Le dimensionnement devra donc couvrir les transitoires de toute la chaîne.

Le débit du **réseau fictif** dans ce scénario est 1,349 m³/s, dont 1,236
dans les zones refroidies et 0,113 dans la fuite. La puissance à l'arbre
rotor est 3,732 kW et celle à l'entrée du renvoi 3,928 kW. Une zone fictive
atteint 72,81 °C après 60 s, avec une limite stationnaire de 51,96 °C.
Ce sont des conséquences de la courbe et des charges choisies, sans valeur
prédictive pour le spécimen. Changer le métal seul conserve ici la courbe
d'air et les zones thermiques : les déformations des pales ne sont pas couplées.

## Reproduction et contrôles

Depuis la racine du dépôt, sur Linux avec CalculiX déjà installé :

```sh
OMP_NUM_THREADS=1 PYTHONNOUSERSITE=1 python3 twins/935-horizontal-cooling-system-f0/source/run_hypothesis_tests.py --ccx --output work/935-hypothesis-tests-new
python3 -m unittest discover -s tests -p test_935_hypothesis_tests.py -v
```

Sans `--ccx`, les 160 scénarios réduits sont exécutés seuls. Utiliser une
nouvelle destination privée. Chaque cas conserve ses entrées et sorties ;
les jeux CalculiX, journaux, résultats, empreintes source et manifeste sont
sauvegardés. Les bilans de débit, pression, puissance et travail de freinage
ont des résidus relatifs inférieurs à 5×10⁻¹⁶ dans la campagne finale.
Les contrôles du témoin et du système sont enregistrés dans `results.json`.
Les seuils sont des contrôles numériques, sans validation physique du jumeau.
