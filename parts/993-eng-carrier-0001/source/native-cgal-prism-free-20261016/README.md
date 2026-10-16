# Volume libre par unions binaires exactes de prismes positifs

Ce parcours utilise les API binaires du commit expérimental CGAL
`b4e8c1887ce6a0abeb618634125e5cfcd301ce16`, [PR9363](https://github.com/CGAL/cgal/pull/9363).
Il n'appelle pas `compute_self_union`, dont les témoins ont échoué.
La chaîne winding-sum potentiellement auto-intersectante n'est jamais envoyée
à une API qui exige des entrées sans auto-intersection.

Chaque triangle de toit crée un prisme positif fermé, de fond commun Z0.
Les unions binaires sont équilibrées par médiane spatiale, sur l'axe de plus
grande étendue des centres ; cet ordre change seulement le coût du calcul.
Chaque intermédiaire est vérifié en exact : absence de triangle collinéaire,
cycle fermé/orienté et absence d'auto-intersection. Les contacts non manifold
peuvent subsister comme frontière intermédiaire ; le résultat final reste
soumis au contrôle manifold strict après snap.

L'expression finale est `(union(prismes) ∩ mask) \ (part ∩ B)`. La boîte B
contient strictement tous les prismes : les six bornes sont les valeurs IEEE
adjacentes vers l'extérieur ; une borne exactement nulle utilise un ulp de
la valeur absolue maximale de cet axe pour éviter les rationnels subnormaux.
Cette boîte sert uniquement à limiter le cutter. L'identité ensembliste est
exacte dès que la boîte contient l'union : aucune marge ne modifie la pièce
ou le volume libre demandé. Aucun booléen intermédiaire n'est converti en
doubles ; les coordonnées rationnelles exactes finales sont conservées.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-prism-free-20261016/setup.py \
  /chemin/neuf/cgal-prism --archive CGAL-b4e8c188.tar.gz \
  --support-runtime /chemin/cgal-6.1.3 --audit-python /chemin/audit/bin/python
python3 /chemin/neuf/cgal-prism/run.py prism_free ROOFS.npz \
  /chemin/neuf/cgal-prism/jobs/essai-001 --second-input MASK.npz \
  --part-input PART.npz --timeout-seconds 1200
```

L'archive amont de167177612 octets porte le SHA256
`1a5c2e9e3aa2b5e699536135ea7c1b0c46cde3343da9347720ad068632019a7f`.
Son URL est `https://codeload.github.com/sloriot/cgal/tar.gz/b4e8c1887ce6a0abeb618634125e5cfcd301ce16`.
Le support-runtime existant fournit explicitement les seuls en-têtes MPFR et
bibliothèques déjà vérifiés, sans modification. Le nouveau CGAL est extrait
séparément. Sources, dépendances réellement compilées, bibliothèques et
Python d'audit sont empreintés. GPLv3 ou ultérieure/commercial pour le paquet
CGAL ; licence et copyright amont copiés. La PR ouverte reste expérimentale.
Les calculs ont deux CPU,4 Gio, zéro swap, réseau nul et600/1200 s explicites.

`prism-face-schema.json` donne les six sommets, les huit faces et leur ordre
exact, y compris l'inversion éventuelle q/r. La parenté est géométrique : les
trois sommets enfant doivent appartenir en exact à un même triangle parent
convexe d'origine. AABB ne sert qu'à chercher des candidats. Le CSR conserve
**tous** les parents ; le minimum primaire n'est pas une décision de contact.
L'adaptateur d'interface doit examiner tous les rôles et signes, et les côtés
matière. Le fichier exact pré-snap et le lien `autorefine_input_face` permettent
de garder ces ambiguïtés après le snap51/5.

Le témoin composé a été exécuté : deux prismes10/20 mm, masque englobant,
soustraction Z8–Z12, volume rationnel exact3200 mm³. L'export float initial
a quatre triangles aplatis, conservés comme refus brut. Après snap51/5 :
topologie stricte et contrôle global exact passent ; les23alertes libigl sont
des contacts ponctuels déjà partagés, tous adjugés en rationnel. Les22faces
à parents multiples conservent98correspondances, aucune vers la boîte.

`audit_composed_drift.py` lie le résultat rationnel, son export float et le
snap sans changer la borne initiale. Il recalcule indépendamment, avec
`Fraction`, chaque erreur de sommet exact→float et toute la connectivité.
La convexité donne une correspondance continue de ces triangles à≤E.
Les distances V3 exactes fournissent D pour chaque échantillon float↔snap.
Le test `sqrt(D²)+sqrt(E²)≤L` est effectué par comparaisons rationnelles,
sous la borne gelée L. Il couvre tous les sommets et barycentres rationnels
exacts natifs et finaux ; il ne revendique pas une borne Hausdorff continue
sur la réparation complète. Les contacts gardent leur gate indépendant.

```sh
AUDIT_PYTHON make_witness_inputs.py /chemin/neuf/inputs
AUDIT_PYTHON -m unittest discover -s parts/993-eng-carrier-0001/source/native-cgal-prism-free-20261016 -p test_composed_drift.py
AUDIT_PYTHON audit_composed_drift.py NATIVE_JOB SNAP_JOB DISTANCE_V3_JOB \
  ORIGINAL_SNAP5_JOB /chemin/neuf/composed --plan FROZEN_PLAN.json
```

Les témoins et reçus réels sont référencés par `reproduction-results.json`.
Ils ne valent pas admission d'une sortie réelle. Chaque essai réel conserve
son plan, tous les contrôles et les refus antérieurs.
