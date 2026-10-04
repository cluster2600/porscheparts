# Pression non convergée et prochain objectif commun

La correction de cadence retire l'admission R0 fine et les moyennes fines
présentées comme vingt itérations. Les [39 tables natives](results/cfd/measurement-cadence-audit.json)
restent identiques à leurs empreintes originales ; les helpers historiques
écrivaient seulement deux mesures par phase. Le code corrigé conserve les
checkpoints à 150 et les mesures à chaque itération. Le résumeur refuse désormais
une fenêtre incomplète ou désalignée. Les deux cas communs conservent leur
admission numérique. Cette correction ne modifie ni les résultats FEM, ni les
cas de contraction/débridage, ni les exports USD.

## Diagnostic des données déjà calculées

Le [rapport reproductible](results/cfd/pressure-followup-diagnostic.json) utilise
les logs natifs, les champs 600/750/900 et le même maillage V2 fin. Les
[empreintes des entrées](results/cfd/pressure-diagnostic-input-manifest.json)
sont recoupées avec l'archive privée vérifiée. Aucun nouveau solveur n'est lancé.

Sur les cent dernières itérations V2 à 900, le résidu initial maximal de
pression est 1,5667×10⁻⁴ ; sa moyenne est 9,9766×10⁻⁵ et son écart type relatif
16,2 %. La relaxation 0,15 n'a pas supprimé le dépassement. Les résidus finaux
linéaires maximaux sont environ 1,11×10⁻⁶ ; le solveur peut s'arrêter au critère
relatif 0,01 avant d'atteindre sa tolérance absolue 10⁻⁸. R0 apparié atteint
6,0216×10⁻⁵ pour le résidu initial maximal, mais sa fenêtre débit/couple reste
insuffisante. La structure temporelle du résidu est celle d'itérations
stationnaires ; aucune fréquence physique ou instabilité de rotation n'est
établie. Le [code OpenFOAM de normalisation](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/OpenFOAM/matrices/lduMatrix/lduMatrix/lduMatrixSolver.C)
justifie de distinguer le résidu algébrique normalisé d'une variation physique
de pression.

De 600 à 750 puis de 750 à 900, le changement de pression pondéré par volume
est respectivement 0,283 et 0,566 Pa RMS. Les maxima locaux atteignent environ
209 et 187 Pa, près du bord de fuite et du bout de pale : rayon 127–137 mm,
z ≈ −16 mm, distance au centroïde de la face de rotor la plus proche 0,5–2,5 mm.
Ces distances sont des proxies géométriques ; ces cellules ne sont pas
identifiées comme cellules de résidu algébrique maximal. Les deux contrôles de
maillage passent ; la non-orthogonalité maximale reste 71,09° et le déterminant
minimal 0,00515. Le reflux brut à la sortie atteint environ 10,8 % du débit net,
et les variations sont à seulement 31–34 mm de la sortie, environ 0,12 D.

Ces observations rendent plausible une sensibilité locale du couplage numérique,
du sillage et de la condition de sortie. Elles ne distinguent pas encore
conditionnement, effet de bord et écoulement instationnaire. La priorité est
une discrimination courte, pas une prolongation destinée à franchir un seuil.

## Objectif fixé avant les prochains calculs

Le [protocole préparé, non exécuté](parameters/matched-cooling-objective-protocol.json)
retient R0 et une seule variante V2 : pitch racine 42° contre 36°, twist −8°
inchangé. V2 réduit la charge nominale ; le résultat commun actuel échange
−26,98 % de puissance contre −7,14 % de débit et −21,39 % de pression totale.
Il ne démontre pas un meilleur refroidissement installé et ne sélectionne pas
un pitch optimal. Aucun nouveau balayage géométrique n'est prévu avant une
comparaison à objectif hydraulique commun.

L'objectif comparatif hypothétique est Q net = 1,00 m³/s, élévation de pression
statique moyenne aux ports = 600 Pa, plafond de screening P = 3300 W. Ce sont
des hypothèses d'analyste, pas des exigences Porsche, thermiques mesurées ou
normatives. Les scénarios de résistance sont Δp statique = K Q² avec
K = 200 / 600 / 1000 Pa/(m³/s)². Ils sont explicitement bornés et hypothétiques.

Le banc commun prescrit Q à l'entrée avec
[flowRateInletVelocity](https://cpp.openfoam.org/v13/classFoam_1_1flowRateInletVelocityFvPatchVectorField.html),
même profil uniforme déclaré pour R0 et V2 ;
[fixedFluxPressure](https://cpp.openfoam.org/v13/classFoam_1_1fixedFluxPressureFvPatchScalarField.html)
adapte le gradient de pression au flux prescrit. La sortie impose une pression
statique de jauge nulle et autorise le reflux. Les échantillons prévus sont
Q = 0,85 / 1,00 / 1,10 m³/s. Les anciens points à pression totale d'entrée
imposée ne sont pas ajoutés à cette nouvelle courbe à profil différent.
Pression statique moyenne, pression totale pondérée par flux, couple, P,
reflux, Mach et bilan d'énergie restent des quantités séparées. Les intersections
avec les résistances s'interpolent seulement entre points admis ; aucune
extrapolation ni efficacité qualifiée n'est annoncée.

## Lots proposés à la coordination, aucun lancé

| Lot | Calculs et arrêt | Ressources par cas, séquentiels | Estimation / plafond total |
| --- | --- | --- | --- |
| D1 | Deux branches de 60 itérations depuis le même V2/900 : relTol pression 0,01 / 0, tolérance absolue 10⁻⁸ et physique inchangées ; télémétrie à chaque itération | 4 CPU, 5 GiB, plafond externe 300 s et solveur 270 s | 4–6 min / 10 min |
| D2a | Après diagnostic et nouvelle fenêtre : R0 et V2 à Q = 1,00 sur leurs grilles communes ; au plus deux phases de 150 par cas | 4 CPU, 5 GiB, 300 s par phase | 8–12 min / 20 min |
| D2b | Après admission D2a et nouvelle fenêtre : quatre points Q = 0,85 / 1,10 pour R0 et V2 | 4 CPU, 5 GiB, au plus deux phases de 150 par cas | 16–24 min / 40 min |

Tous les seuils originaux restent exigés, ainsi qu'au moins vingt mesures
consécutives. Si D1 ne distingue pas l'effet du solveur linéaire, une sensibilité
commune de longueur de sortie doit être préparée avec ses propres gates CAD et
maillage avant toute conclusion fine. Aucun de ces lots n'est lancé en arrière-plan.
Les fenêtres Kali2 doivent être coordonnées avec les travaux FEM indépendants.
Les [configurations exactes D1 et la politique de fenêtres prospectives](D1_PREPARATION.md)
sont préparées séparément, sans lancement.
Les [configurations exactes D1 et la politique de fenêtres prospectives](D1_PREPARATION.md)
sont préparées séparément, sans lancement.
Les [configurations exactes D1 et la politique de fenêtres prospectives](D1_PREPARATION.md)
sont préparées séparément, sans lancement.

Pour reproduire le diagnostic léger depuis les entrées natives privées :

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python source/diagnose_pressure_followup.py PRIVATE_NATIVE_INPUTS work/pressure-diagnostic.json --source-directory source
python source/audit_measurement_cadence.py . PRIVATE_NATIVE_TABLES work/measurement-cadence-audit.json
python source/compare_matched_flow.py . work/matched-grid-comparison.json
python source/verify_study.py
```
