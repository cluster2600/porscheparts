# Calcul natif froid par région

Une commande calcule **une région** dans un dossier neuf, avec ses vraies entrées
`prepare_exact_envelopes_v2.py` et un manifeste de runtimes non secret explicite :

```sh
AM_PYTHON -B parts/993-eng-carrier-0001/source/process-skins-20261016/run_native_envelope_case.py INPUTS/inputs-v2.json OUTPUT/source-000 --source-index 0 --runtime NATIVE_RUNTIME.json
```

Les sept indices autorisés sont `0,1,2,3,8,9,10`. Le programme refuse plusieurs
polygones pour un même indice. Il ne cherche aucun ancien résultat à réutiliser.
Les SHA des entrées, des sources copiées et du manifeste runtime sont vérifiés
avant et après les calculs. La communication SSH ne sert qu'au transfert et au
pilotage ; les noyaux géométriques s'exécutent sans réseau, avec deux CPU, 4 Gio
et zéro swap. Chaque scope systemd a son nom propre, ses limites et son reçu.
Une annulation vise uniquement les scopes des nouveaux jobs créés par ce cas.

| Indice | Construction exacte | Budget CSG |
|---|---|---:|
| 0 | Union équilibrée des vrais prismes positifs, puis masque et soustraction de la pièce localement coupée | 1200 s |
| 2 | Même noyau, puis le plan local de réparation explicitement épinglé | 600 s |
| 8 | PyMesh CSGTree `(chain ∩ mask) \ part` | 600 s |
| 1,3,9,10 | PyMesh CSGTree `(chain \ part) ∩ mask` | 600 s |

Le snap reste `gs=51,n=5`. Les distances exactes contrôlent tous les sommets et
barycentres rationnels, dans les deux sens, sous la borne 5δ gelée. Pour les deux
cas prismes, la conversion rationnel→IEEE est mesurée indépendamment puis
composée exactement avec la distance finale. Ce dernier contrôle porte sur
l'ensemble fini déclaré ; il ne constitue pas une distance de Hausdorff
continue. La topologie stricte et les intersections/contacts restent des
conditions séparées. Un refus du vieux mesureur IGL est conservé et ne peut être
dépassé que par les gardes natives/topologiques et le nouveau mesureur exact.

Le premier snap gauche, refusé topologiquement, reste un intermédiaire conservé.
`left-repair-template-v2.json` contient le plan historique et le digest canonique
de **tous** les tableaux RAW et du premier snap : noms, dtypes, dimensions et
octets C. Seul l'ordre/encodage des membres ZIP peut différer. Le binder écrit
les nouvelles identités de fichiers après cette égalité stricte, sans recherche
de voisin, réindexation ni adaptation du plan. Si le calcul froid donne d'autres
tableaux, il refuse. Les neuf faces modifiées conservent une filiation positive
vide ; elles ne deviennent jamais des ancrages par héritage.

## Sorties stables

`OUTPUT/source-NNN/case.json` n'est publié qu'après succès de toutes les gardes :

- `schema: native-envelope-case-v2`, `status: executed`, `source_index`,
  `backend`, `profile`, SHA du runtime et du manifeste d'entrée ;
- pour 0/2 : `native_audit.path = result/sealed/native_audit.json` et son SHA ;
- pour les cinq autres : `legacy_case_directory.path = result/legacy`.

Les volumes historiques restent donc à
`source-NNN/result/legacy/snap/result.npz`, avec le reçu frère
`source-NNN/result/legacy/csg/receipt.json`. Les paquets prismes sont portables :
leurs destinations de preuves sont relatives et le lecteur strict les vérifie
avant/après utilisation. `execution-receipt.json` conserve un échec ou une
annulation ; l'absence de `case.json` interdit de promouvoir ce cas.

## Installation des noyaux

Le bootstrap Linux de base est `../native-toolchain-20261016/bootstrap.py`.
Il installe réellement PyMesh, CGAL6.1.3, distance exacte V3 et Python/libigl,
avec archives et roues épinglées. Aucun secret n'est requis. Ajouter l'adaptateur
des deux ordres, qui ne modifie pas le rootfs de base :

```sh
python3 parts/993-eng-carrier-0001/source/native-pymesh-orders-20261016/setup.py ORDERS_PREFIX --pymesh-runtime BASE_PREFIX/pymesh
```

Pour les prismes, `../native-cgal-self-union-20261016/setup.py` installe les
en-têtes expérimentaux au commit complet `b4e8c1887ce6a0abeb618634125e5cfcd301ce16`
depuis leur archive épinglée. L'API self-union, refusée par ses témoins, n'est pas
utilisée. Le noyau binaire est construit séparément par :

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-self-union-20261016/setup.py BOOLEAN_BASE --archive CGAL_PINNED_ARCHIVE --support-runtime BASE_PREFIX/snap --audit-python BASE_PREFIX/audit/venv/bin/python
python3 parts/993-eng-carrier-0001/source/native-cgal-prism-free-20261016-v4/setup.py PRISM_PREFIX --boolean-runtime BOOLEAN_BASE
```

Le nouveau pilote copie lui-même le schéma prisme et les scripts de composition
et de réaudit nécessaires. Ils ne doivent pas être ajoutés à un ancien runtime
gelé. Le manifeste JSON accepte exactement les clés `schema,host,remote_parent,
python,audit_python,pymesh_orders,prism_csg,snap,distance`, avec le schéma
`carrier-native-case-runtime-v2`. Tous les chemins sont absolus et explicites ;
les adresses privées restent dans le manifeste local, hors documentation publique.

## Vérifications effectuées

Les tests du contrat vérifient notamment le refus d'une modification d'un seul
tableau de filiation, d'un dtype, d'une coordonnée ou d'une entrée. Le parcours
natif complet a été exécuté sur deux **témoins miniatures**, prismes0 et chaîne8,
avec volume attendu 3200 mm³. Les deux ordres PyMesh ont aussi leurs témoins
natifs distincts. Aucun des sept gros cas n'a été rejoué pour tester ce pilote.
La réparation froide gauche reste conditionnelle à l'identité stricte de ses
tableaux ; son chemin réel historique et ses preuves sont conservés séparément.
