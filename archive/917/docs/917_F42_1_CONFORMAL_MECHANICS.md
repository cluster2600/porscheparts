# F42.1 — écran mécanique tétra conforme de la culasse

## Verdict

F42.1 remplace l'ancien volume voxel non convergent par trois maillages
volumiques C3D4 conformes à une peau privée réparée et résolus avec CalculiX.
Le résultat est un **écran linéaire thermo-mécanique**, pas une validation de
conception. L'autorisation d'imprimer et l'autorisation de démarrer un moteur
restent fermées.

![Convergence F42.1](../twins/reference-917-engine/evidence/f42-1-conformal-mechanics/917-head-f42-1-conformal-mechanics.png)

La cause principale est indépendante de la convergence numérique : aucune
carte AlSi10Mg dépendante de la température, qualifiée par coupons dans le sens
et l'état thermique de la fabrication, n'est disponible. Les pressions et
températures ne sont pas non plus corrélées à un moteur instrumenté.

## Géométrie privée et tétraédrisation

Le STL F41 soudé n'est jamais copié dans le dépôt. Le rapport public conserve
seulement son SHA-256, sa taille et des agrégats. Après soudage exact des
sommets il est fermé et monocomposant, mais il contient des auto-intersections
locales. Gmsh 4.15.2 a donc été refusé après `classifySurfaces` :
`createGeometry` ne pouvait pas paramétrer la topologie de frontière.

La chaîne retenue est volontairement explicite :

1. suppression privée des faces auto-intersectées par PyMeshLab ;
2. fermeture des trous résiduels par MeshFix ;
3. rejet si la variation globale de volume ou d'aire dépasse `0,5 %` ;
4. tétraédrisation PLC par TetGen 0.8.4, sans bissection de la peau réparée ;
5. vérification indépendante de la propriété de toutes les faces : une face
   externe appartient à un tétraèdre, une face interne à deux, jamais plus ;
6. rejet des volumes nuls et publication des qualités `mean-ratio` minimale et
   au percentile 1 %.

Il s'agit donc d'une conformité à la **peau réparée bornée**, pas d'une preuve
que le STL privé brut était un domaine volumique exploitable tel quel.

## Groupes de surfaces stables

Les groupes ne reposent ni sur des identifiants Gmsh, ni sur des listes de
nœuds propres à une maille. Ils sont reconstruits à chaque résolution par les
surfaces analytiques déjà publiées dans le modèle F41 :

- chambre : distance à la sphère nominale à `±1,0 mm` et normale sortante
  alignée à au moins `0,80`, utilisée par `*DLOAD` ;
- quatre alésages de goujons : distance radiale au cylindre nominal à
  `±0,50 mm` et alignement de normale à au moins `0,60`, utilisés comme appuis
  distribués ;
- thermique : champ continu décroissant exponentiellement avec la distance à
  la chambre, et non une sélection discontinue de nœuds.

L'appui cinématique est un montage 3-2-1 distribué sur les alésages : le premier
goujon bloque U1/U2/U3, le deuxième U2/U3 et les deux autres U3. Ce montage
supprime les mouvements rigides, mais ce n'est ni un contact goujon/culasse, ni
un serrage de rondelle et d'écrou.

## Charges et matériau de dépistage

| Entrée | Valeur F42.1 | Statut |
| --- | ---: | --- |
| pression chambre | 10 MPa | hypothèse de dépistage |
| température de fond | 120 °C | hypothèse |
| température de chambre | 260 °C | hypothèse |
| longueur de décroissance thermique | 12 mm | hypothèse |
| module d'Young | 70 000 MPa | constant, non qualifié à chaud |
| coefficient de Poisson | 0,33 | constant |
| dilatation | 21,5 µm/m/K | constante |

Le calcul superpose pression et dilatation dans une étape statique linéaire. Il
n'inclut ni plasticité, ni fluage, ni fatigue thermo-mécanique, ni contact des
sièges/guides/goujons, ni précharge, ni historique de combustion.

## Traitement des singularités d'appui

Les maxima bruts sont conservés. La métrique primaire de convergence est le
percentile 95 des contraintes de von Mises après exclusion des tétraèdres dont
le centroïde se trouve à moins de `15,0 mm` d'un des quatre axes de goujon.
Cette distance physique est fixée avant les calculs et identique aux trois
mailles. Elle ne peut donc pas être élargie après lecture des résultats pour
faire baisser la contrainte.

Le passage numérique exige simultanément : trois résolutions terminées,
frontières conformes, groupes présents, percentile 1 % de qualité `mean-ratio`
au moins égal à `0,05`, volume maximal observé au plus égal à `1,05` fois la
cible, écart fin/avant-fin inférieur ou égal à `10 %` sur le p95 nettoyé et à
`5 %` sur le déplacement maximal. Même si ces portes passent, la porte matériau
à chaud reste fermée.

## Résultats publiés

| cible | C3D4 | p95 brut | p95 hors appuis | déplacement max | qualité p01 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 7 mm | 209 855 | 100,42 MPa | 99,35 MPa | 0,1419 mm | 0,00113 |
| 5 mm | 215 981 | 100,58 MPa | 98,40 MPa | 0,1430 mm | 0,00129 |
| 3 mm | 269 559 | 101,29 MPa | 100,79 MPa | 0,1415 mm | 0,00138 |

L'écart entre les deux mailles les plus fines est `2,37 %` sur le p95 hors
appuis et `1,05 %` sur le déplacement. Ces deux métriques convergent. En
revanche, la qualité p01 reste très inférieure au seuil de `0,05` et le volume
maximal de certains tétraèdres dépasse la cible de taille. Le **passage
numérique global est donc refusé**, même avant la porte matériau. Les maxima
bruts, compris entre `14,27` et `14,59 GPa`, confirment aussi que les
singularités et tétraèdres très dégradés ne peuvent pas servir à dimensionner la
pièce.

Les valeurs exactes, comptes d'éléments, aires de groupes, métriques brutes et
hors appuis sont dans le
[rapport JSON public](../twins/reference-917-engine/evidence/f42-1-conformal-mechanics/917-head-f42-1-conformal-mechanics-public-report.json).
Le graphique ne représente volontairement pas la géométrie privée.

## Reproduction contrôlée

L'exécution doit se faire sur une machine autorisée à lire le STL privé. Aucun
maillage, deck CalculiX ou champ de résultat ne doit être rapatrié :

```sh
python3 twins/reference-917-engine/source/run_f42_1_conformal_calculix.py \
  --head "$PRIVATE_HEAD_STL" \
  --output "$PRIVATE_RUN_DIRECTORY" \
  --mesh-sizes-mm 7 5 3
```

Seul `917-head-f42-1-conformal-mechanics-public-report.json` est ensuite soumis
au dépôt. Le graphique agrégé est régénéré localement :

```sh
python3 twins/reference-917-engine/source/render_f42_1_conformal_mechanics.py \
  --report twins/reference-917-engine/evidence/f42-1-conformal-mechanics/917-head-f42-1-conformal-mechanics-public-report.json \
  --output twins/reference-917-engine/evidence/f42-1-conformal-mechanics/917-head-f42-1-conformal-mechanics.png
```

Les tests unitaires contrôlent la propriété des faces C3D4, l'échec sur face
non-manifold, les groupes analytiques, le rayon d'exclusion fixe, la fermeture
des portes matériau/fabrication et l'absence de géométrie dans les preuves
publiées.

## Travaux nécessaires avant décision de conception

- carte matériau AlSi10Mg dépendante de la température et qualifiée par coupons
  représentatifs du procédé, de l'orientation et du traitement thermique ;
- contacts, jeux et précharges réels des quatre goujons, sièges, guides et
  porte-axes ;
- champs pression/température corrélés CFD/CHT puis moteur instrumenté ;
- mailles quadratiques et étude locale des congés fonctionnels ;
- fatigue thermo-mécanique, contrôle dimensionnel, CT/CND et essais physiques.

Jusqu'à leur clôture, le statut reste : **non autorisé à imprimer et non
autorisé à utiliser dans un moteur**.
