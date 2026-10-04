# Après D1 : causes possibles et essai discriminant proposé

Les [champs natifs privés vérifiés](results/cfd/D1-local-field-diagnostic.json)
permettent cette analyse légère, sans nouveau solveur. Elle complète le
[résultat D1](D1_EXECUTION.md). Le témoin reste non admis sur la pression ;
la branche stricte reste incomplète. Les différences de champs ne localisent
pas le résidu algébrique de l'équation de pression.

## Hypothèses hiérarchisées

| Priorité | Hypothèse | Indices quantifiés et portée |
| --- | --- | --- |
| 1 | Mise à jour non linéaire vitesse–pression dans le sillage de bout de pale | À 901–920, le solveur strict divise le résidu final par 96,97 et l'erreur de continuité locale moyenne par 19,40, mais le maximum initial change de +0,174 %. Sur les 60 itérations du témoin, la troisième correction commence en moyenne à 21,27 % du résidu initial de la première ; des premières corrections dépassent encore le seuil lors des mises à jour suivantes. La linéarisation/correction globale mérite une sensibilité, sans conclure qu'elle est la cause. |
| 2 | Influence de la sortie proche dans une zone de reflux | À 960, débit net 1,15229968 m³/s et reflux brut 0,12399009 m³/s, soit 10,76 % du net ; 35,15 % de la surface de sortie a un flux entrant. Les dix variations de pression maximales restent à 31,7–34,1 mm de cette sortie, environ 0,12 D. Cette proximité et le reflux rendent la sensibilité de longueur plausible ; ils ne prouvent pas une condition incorrecte. |
| 3 | Conditionnement ou résolution locale du maillage | Les métriques reproduites correspondent au contrôle indépendant : non-orthogonalité 71,0857°, skewness 1,09927, déterminant minimal 0,00515090. Les 1 448 cellules avec \|Δp\| > 1 Pa ont une non-orthogonalité maximale 55,05°, skewness maximale 0,80398 et déterminant minimal 0,02393. Aucune ne recouvre les 69 cellules à >65°. Les dix maxima ont des angles 14,9–32,8°. La cause « pires cellules seules » est affaiblie ; la résolution du sillage et l'absence de couches restent non qualifiées. |

L'ordre ci-dessus représente la priorité d'un test, pas une probabilité de cause.
Le coarse V2 converge malgré une non-orthogonalité maximale supérieure à celle
du fin ; une métrique globale seule ne justifie donc pas de remesher.

Entre 900 et 960, RMS Δp pondéré par volume = 0,291515 Pa, maximum = 131,776 Pa ;
RMS ΔU = 0,0221393 m/s. Les cellules au-delà de 1 Pa occupent 0,240615 % du
volume. Les maxima sont aux rayons 129,3–137,0 mm, z = −15,4 à −17,9 mm,
à 0,51–2,43 mm du centroïde de face de rotor le plus proche. Ces distances
sont des proxies géométriques, pas des distances de paroi. La corrélation
cellulaire \|Δp\| / \|ΔU\| est 0,487 ; elle ne prouve aucune causalité.

## Cohérence des conditions et des flux

Les types de conditions sont identiques à 900 et 960 : rotor `MRFnoSlip` /
pression `zeroGradient`, carter `noSlip` / pression `zeroGradient`, entrée et
sortie `pressureInletOutletVelocity`, pression totale d'entrée nulle et
pression statique de sortie nulle. Cette configuration autorise effectivement
le reflux observé. Elle représente un ventilateur isolé, pas une résistance
thermique ou hydraulique de moteur mesurée. La turbulence imposée en reflux,
les interfaces moteur et la sensibilité compressible restent à qualifier.

La somme de divergence discrète du `phi` MRF relatif à 960 est
1,78165×10⁻⁷ m³/s et correspond à la somme des **quatre** patches. Le déséquilibre
des deux ports seuls vaut 1,64016×10⁻⁵ m³/s ; les flux de faces tournantes
relatifs expliquent la différence. Cette somme ne se lit pas comme une fuite
de paroi absolue. Le diagnostic n'accède ni à la matrice de pression ni à son
champ de résidu cellulaire ; il ne prétend pas identifier les cellules de
résidu initial maximal.

Le [code officiel de correction](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/applications/modules/incompressibleFluid/correctPressure.C)
montre que `consistent yes` modifie le coefficient inverse de la diagonale et
les corrections du flux et de la vitesse. Le [code des contrôles géométriques](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C)
fonde les trois métriques locales reproduites ; leurs extrema sont comparés
aux résultats indépendants avant acceptation de ce rapport.

## Plus petit essai proposé : une seule branche, non lancée

Le [protocole fixé](parameters/D1-coupling-proposed-protocol.json) et le
[dictionnaire candidat](parameters/D1-coupling-candidate/fvSolution) changent
**uniquement `SIMPLE.consistent no` en `yes`**. On réutilise les 60 itérations
complètes du témoin D1 au lieu de recalculer ce témoin. La branche candidate
partirait du même checkpoint 900 et de la même partition MPI, pour 901–960.
Grille, champs initiaux, physique, conditions, schémas, relaxation p = 0,15,
relTol = 0,01, tolérance absolue = 10⁻⁸ et tous les critères sont identiques.
La vérification de chaque empreinte et des liens `uniform` précède le solveur.

Coût proposé : 4 CPU / 5 GiB RAM **et mémoire+swap**, une seule branche ;
environ 112 s de solveur d'après le témoin natif, environ 180 s au total,
plafond global **300 s préparation/reconstruction/audit inclus**, plafond MPI
180 s. Aucun service tiers, installation ou accès nouveau. Lancement bloqué
jusqu'à la coordination d'une fenêtre ; l'erreur ou le dépassement arrête le
lot et préserve son reçu, sans reprise automatique.

Les trois fenêtres 901–920 / 921–940 / 941–960 sont fixées avant le calcul ;
télémétrie chaque itération et checkpoint à 960. Les critères originaux restent
obligatoires sur 941–960 : p ≤10⁻⁴, U ≤10⁻⁵, k/ω ≤10⁻⁴, déséquilibre ≤0,5 %, CV
débit ≤1 %, CV couple ≤2 %, direction et champs finis complets.

- Un maximum p réduit d'au moins 30 % par rapport au témoin **et** tous les
  critères originaux satisfaits étayeraient une sensibilité au couplage.
- Un changement de moins de 10 % sur une fenêtre complète ne l'étayerait pas.
- Entre ces bornes ou en cas d'incomplétude : résultat descriptif, aucune
  conclusion de cause, prolongation ou admission inventée.

Ces règles sont des critères prospectifs de discrimination, pas des seuils
assouplis d'admission. Même un succès numérique ne qualifierait pas le débit
installé, le refroidissement, le rendement ou une oscillation physique.
Si cet essai n'est pas discriminant, la préparation suivante porterait sur
une longueur de sortie commune, avec gates CAD/maillage et transfert de champs
documentés avant toute nouvelle autorisation de calcul.

Pour reproduire l'analyse légère depuis les archives locales privées :

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python source/analyze_d1_local_fields.py PRIVATE_OLD_INPUTS PRIVATE_960_INPUTS PRIVATE_D1_LOGS work/D1-local-field-diagnostic.json
python source/verify_study.py
```

Le script ne lance ni solveur ni modification de maillage et ne publie aucun
champ natif complet. Les archives et le scan restent privés.
