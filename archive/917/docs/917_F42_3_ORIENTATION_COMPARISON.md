# F42.3 — comparaison exhaustive des orientations +Y et -Y

## Décision

L'orientation `-Y / scan_y_up` a été soumise au même audit géométrique que
l'orientation verrouillée `+Y / scan_y_down` : `4 122` intersections réelles à
`50 µm`, même seuil d'overhang `45°`, même filtre numérique `0,01 mm²` et même
proxy de supports verticaux à pas `0,25 mm`.

![Comparaison F42.3](../twins/reference-917-engine/evidence/f42-3-orientation-comparison/917-head-f42-3-orientation-comparison.png)

`+Y` reste verrouillée. Même si `-Y` améliorait certaines métriques, retourner
la culasse change le côté exposé au plateau. La peau soudée ne porte pas les
labels sémantiques permettant d'écarter le contact d'une interface fonctionnelle
ou la destruction d'une surépaisseur d'usinage. Le jeu recoater après déformation
n'est pas calculé. La condition « aucune nouvelle exposition interface/recoater »
est donc fausse par absence de preuve.

## Méthode de comparaison

Le proxy surfacique cardinal indiquait seulement `-4,80 %` de projection
descendante pour `-Y`. F42.3 ne s'appuie pas sur ce raccourci : elle reconstruit
la pile complète dans le sens opposé et compare :

- couches vides et continuité des index ;
- îlots entièrement nouveaux ;
- aire non soutenue par couche et maximum local ;
- volume et surface latérale de l'enveloppe conservative des supports ;
- aire et nombre de composantes au premier plan médian ;
- volume de matière dans le premier millimètre, comme proxy de contact plateau ;
- enveloppe nominale BLT-S310.

Les valeurs exactes sont dans le rapport JSON. Les deux CSV couche par couche
sont liés par SHA-256, mais seul le CSV `+Y` déjà public reste dans Git. Les
contours, coordonnées et deux piles de supports reconstructibles restent privés.

## Résultats

| Mesure | +Y verrouillée | -Y candidate | Écart -Y |
| --- | ---: | ---: | ---: |
| couches vides | 0 | 0 | 0 |
| nouveaux îlots | 179 | 160 | -10,61 % |
| couches avec région non soutenue | 2 098 | 1 911 | -8,91 % |
| intégrale d'aire non soutenue | 7 688,304 | 7 257,057 | -5,61 % |
| aire non soutenue maximale | 458,464 mm² | 470,560 mm² | +2,64 % |
| volume support conservatif | 265,161 cm³ | 321,688 cm³ | +21,32 % |
| surface latérale support approx. | 216 843,7 mm² | 299 144,6 mm² | +37,95 % |
| matière dans le premier mm | 24,590 mm³ | 83,533 mm³ | +239,70 % |

Le candidat améliore donc le nombre d'îlots et l'intégrale d'aire non soutenue,
mais il échoue au critère combiné : volume de support, surface latérale et pire
overhang local se dégradent. La plus grande matière près du plateau est seulement
un proxy de contact, pas la preuve que cette face peut être sacrifiée ou usinée.

## Portes fermées

Le calcul est un audit de tranchage géométrique. Il ne démontre pas :

- la protection des sièges, plans de joint, guides ou surfaces d'usinage côté
  plateau pour `-Y` ;
- la stabilité de supports optimisés ou leur retrait ;
- la déformation thermo-mécanique LPBF ;
- le jeu de la lame recoater ;
- l'acceptation du placement par le trancheur et le fournisseur BLT ;
- un fichier machine signé.

En conséquence, `orientation_change_authorized`, `manufacturing_release` et
`part_authorized_for_print` restent faux.

## Reproduction

Le trancheur F42.2 est paramétré sans modifier son défaut `+Y` :

```sh
python3 twins/reference-917-engine/source/run_f42_2_full_build_slicing.py \
  --orientation scan_y_up \
  --head /chemin/prive/culasse-soudee.stl \
  --output /chemin/prive/f42-3-minus-y
```

La comparaison est compilée depuis les deux rapports et deux CSV agrégés :

```sh
python3 twins/reference-917-engine/source/compile_f42_3_orientation_comparison.py \
  --reference-report reference-report.json --reference-metrics reference.csv \
  --candidate-report candidate-report.json --candidate-metrics candidate.csv \
  --output 917-head-f42-3-orientation-comparison-report.json
```
