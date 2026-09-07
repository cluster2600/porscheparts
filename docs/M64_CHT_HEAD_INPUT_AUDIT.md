# M64 — préparation de la thermique de culasse complète

Audit du 7 septembre 2026. **Aucun calcul thermique de culasse M64 abouti.**
Le prochain calcul doit contenir le solide réel et ses interfaces thermiques,
pas seulement un écoulement dans les conduits ou un disque de contrôle.

## Travail exécuté sur la géométrie disponible

Le script `twins/m64-cylinder-head/inventory_thermal_boundaries.py` a été
exécuté sur Kali avec OCP 7.9.3.1, sur le STEP privé F53 quatre soupapes :
SHA-256 `700baea66bc72cdb6aee529e21b167270ebde11db94b06f8e1e55ee08bdd9bf2`.
Il s'agit toujours d'une référence dérivée du scan 935, **pas d'une culasse
M64 ajustée ou d'une nouvelle forme de substitution**.

- 4 929 faces : 3 051 B-Splines, 1 845 plans et 33 cylindres.
- Aire totale 144 617,7772 unités du scan au carré ; pas une aire physique
  certifiée en m². L'erreur relative entre somme par face et intégrale globale
  est de 3,82 × 10⁻¹⁵.
- Aire, centre, boîte englobante et voisinage topologique consignés pour
  chaque face ; aucune géométrie n'est modifiée ni réparée par cet inventaire.
- **0 face affectée thermiquement** à ce stade. Une face sans affectation
  reste inconnue ; elle ne devient pas automatiquement adiabatique.

Les coordonnées restent privées sous
`/tmp/917-f50/out/m64-thermal-boundary-inventory-20260907c/` sur Kali.
L'inventaire utilise les indices de faces OCCT à partir de 1, liés au hash
du STEP et à la version d'import. Il refuse les affectations provenant d'une
autre empreinte/version, les doubles affectations, les faces inexistantes et
les rôles sans référence de revue. Les 12 tests ciblés sont réussis.

L'intégration d'aire utilise les surfaces B-Rep, non les triangles de rendu.
Cette opération suit l'API [OCCT BRepGProp](https://occt3d.com/dev/doc/refman/html/class_b_rep_g_prop.html).
Elle ne certifie ni la topologie ni l'épaisseur ; les défauts F54 restent
ouverts. Un inventaire complet n'est pas un cas CHT complet.

## Ce que le dépôt peut réellement fournir

| Entrée | Disponible | Limite pour le prochain calcul |
| --- | --- | --- |
| Solide de référence F53 | STEP privé, hash, 4 929 faces inventoriées | Pas encore les interfaces M64 ; parois faibles connues |
| Régions gaz F48/F50 | Patchs `intake`, `exhaust`, `valve`, `chamber`, `deck`, `bore`, `walls` | Domaine fluide distinct ; noms non transférables aux faces F53 |
| Runtime CHT OpenFOAM 14 | Tutoriel gaz/solide exécuté, énergie résolue sur 2 000 + 800 cellules | Ni culasse ni convergence globale ; ne pas relancer ce témoin comme résultat de pièce |
| Pression/flux F46/F50 | Traces historiques du projet 917 | Non applicables au M64 turbo sans cas moteur explicitement redéfini |
| Matériau CP1 | Données fabricant de référence et traitement 400 °C / 4 h | Pas de carte complète k(T), Cp(T), dilatation et mécanique à chaud |

La fiche [Constellium CP1, page 2](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf)
fournit notamment 187 W/(m·K) et des essais de traction à 25 °C pour son état
400 °C / 4 h. La stabilité annoncée à 250–300 °C n'est pas une loi de traction
ou de conductivité à chaud. La fiche
[ECKART A20X, page 5](https://www.eckart.net/en/download/document/view/id/519)
contient des points de traction jusqu'à 250 °C ; elle ne complète pas la carte
thermique CP1 et son traitement est spécifique. Ces sources ont été relues,
mais **aucune propriété n'est assignée au M64 par cet audit**.

## Minimum à préparer avant le premier cas CHT de pièce

1. Affecter les faces réelles : chambre/admission/échappement, ailettes et
   extérieur exposés à l'air, sièges/guides/bougie, portée cylindre,
   porte-arbres et fixations. L'héritage de F43 ne signifie pas à lui seul
   « refroidi par air » : il contient aussi des surfaces fonctionnelles.
2. Construire le volume d'air et son carénage, définir les ouvertures, puis
   raccorder ses frontières aux faces du solide. Vérifier couverture et
   continuité géométrique des interfaces ; ne pas appairer par simple nom.
3. Définir un scénario M64 turbo traçable : régime/charge, carburant,
   suralimentation, entrée d'air de refroidissement et pertes de charge.
   Pour une première étude stationnaire, des charges moyennées déclarées
   comme hypothèses sont possibles ; elles ne deviennent pas des mesures.
4. Fournir les lois thermiques sur la plage calculée et les contacts thermiques.
   Ajouter les propriétés mécaniques à chaud, précharges et serrages pour le
   calcul de résistance. Une bibliothèque de rendu n'est pas cette carte.
5. Résoudre puis vérifier énergie entrante/sortante, flux d'interface opposés,
   températures finies, résidus et stabilité des grandeurs d'intérêt ; ensuite
   raffiner l'espace/le temps et comparer air seul contre air + huile à charges
   identiques. Le circuit huile reste une variante de conception, non un
   refroidissement disponible implicitement.

OpenFOAM distingue modèles thermodynamiques, transport et équation d'état dans
`physicalProperties` ; le choix doit correspondre au fluide/solide et à la
plage thermique. Voir [guide OpenFOAM 14, modèles thermophysiques](https://doc.cfd.direct/openfoam/user-guide-v14/thermophysical).
Le script d'inventaire ne génère aucun dictionnaire incomplet prêt à lancer :
il fournit les identifiants et contrôles nécessaires à son affectation.

## Reproduction du prétraitement

Depuis le conteneur privé disposant d'OCP et des helpers existants :

```sh
python inventory_thermal_boundaries.py \
  --input /f50/out/f53-4v-adaptive-bspline/candidate.step \
  --sha256 700baea66bc72cdb6aee529e21b167270ebde11db94b06f8e1e55ee08bdd9bf2 \
  --helpers /f50 --output /f50/out/new-private-boundary-inventory
```

Le répertoire de sortie doit être neuf. Le JSON d'affectation optionnel contient
`source_sha256`, `ocp_version` et une liste `assignments` ; chaque groupe porte
`role`, `face_ids` et `evidence`. Un découpage complet des faces ne prouve ni la
validité physique de ses conditions aux limites ni la fabricabilité.
